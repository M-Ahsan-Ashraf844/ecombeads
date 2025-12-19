from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from django.contrib.auth import login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin 
from .models import product,category,Orderitem,Order,Customerdetail,Orderhistory,ProductVariant
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Sum,Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.mail import send_mail

# Create your views here


class Cart(View):
    def post(self, request, *args, **kwargs):
        product_id = str(kwargs.get('product_id'))
        cart = request.session.get('cart', {})

        # Get quantity (default 1) and size
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1

        size = request.POST.get('size')
        beads_name = request.POST.get('beads_name')

        # Initialize product in cart if not exists
        if product_id in cart:
            # Ensure it's a dict
            if isinstance(cart[product_id], int):
                cart[product_id] = {"quantity": cart[product_id], "size": None, "beads_name": None}

            cart[product_id]["quantity"] += quantity
            cart[product_id]["size"] = size  # update size if provided
            cart[product_id]["beads_name"] = beads_name  # update beads_name if provided
        else:
            cart[product_id] = {"quantity": quantity, "size": size, "beads_name": beads_name}

        # Save back to session
        request.session['cart'] = cart
        messages.success(request, 'Added to your Cart!')

        # Redirect to category if provided
        category_id = request.POST.get('category_id')
        if category_id:
            return redirect(f"/home/?category_id={category_id}") 
        
        print(cart)
        return redirect('home')


# =========================
# CART DISPLAY VIEW
# =========================
class Cartview(TemplateView):
    template_name = 'mycart.html'

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = request.session.get('cart', {})

        productlist = []
        grand_total = 0
        cart_count = 0

        # Normalize cart: convert old int values to dict
        for pid, details in cart.items():
            if isinstance(details, int):
                cart[pid] = {"quantity": details, "size": None, "beads_name": None}
            else: 
                details.setdefault("size", None)
                details.setdefault("beads_name", None)

        # Process each cart item
        for product_id, details in cart.items():
            try:
                product_obj = product.objects.get(id=product_id)
            except product.DoesNotExist:
                continue  # skip if product was deleted

            qty = details["quantity"]
            size = details["size"]
            beads_name = details["beads_name"]
            totalprice = product_obj.discounted_price * qty
            grand_total += totalprice
            cart_count += qty

            productlist.append({
                'product': product_obj,
                'quantity': qty,
                'size': size,
                'beads_name': beads_name,
                'totalprice': totalprice,
            })

        form = Order()
        context.update({
            'cart_items': productlist,
            'cart_total': grand_total,
            'cart_count': cart_count,
            'order': form,
        })
        return render(request, self.template_name, context)

class RemoveCart(View):
    def post(self,request,product_id):
        cart=self.request.session.get('cart',{})
        product_id = str(product_id) 
        if product_id in cart:
            del cart[product_id]
        request.session['cart']=cart
        messages.success(request,'order deleted successfully!!')
        return redirect('mycart')

@method_decorator(csrf_exempt, name='dispatch')
class Update(View):
    def post(self, request, product_id):
        import json
        try:
            data = json.loads(request.body)
            new_quantity = int(data.get('quantity', 1))
            cart = request.session.get('cart', {})

            pid = str(product_id)
            existing = cart.get(pid)

            # Normalize / preserve size and beads_name if present
            if isinstance(existing, dict):
                existing_size = existing.get('size')
                existing_beads_name = existing.get('beads_name')
                cart[pid] = {"quantity": new_quantity, "size": existing_size, "beads_name": existing_beads_name}
            else:
                # legacy int or None -> store as dict with size=None
                cart[pid] = {"quantity": new_quantity, "size": None, "beads_name": None}

            request.session['cart'] = cart

            # total items = sum of quantities (works with dict or legacy int)
            cart_count = sum(item['quantity'] if isinstance(item, dict) else int(item) for item in cart.values())
            return JsonResponse({'success': True, 'cart_count': cart_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
class Checkout(View):

    def post(self, request):
        cart = request.session.get('cart', {})

        # Normalize cart items (convert old int values)
        for pid, details in cart.items():
            if isinstance(details, int):
                cart[pid] = {"quantity": details, "size": None, "beads_name": None}
            else:
                details.setdefault("size", None)
                details.setdefault("beads_name", None)

        # Customer details
        full_name = request.POST.get('full_name')
        contact_no = request.POST.get('contact')
        province = request.POST.get('customer_province')
        address = request.POST.get('address')
        customer_city = request.POST.get('customer_city')

        detail = Customerdetail.objects.create(
            customer_name=full_name,
            customer_city=customer_city,
            customer_address=address,
            customer_province=province,
            customer_number=contact_no,
        )

        if not cart:
            messages.info(request, 'Cart is Empty!!')
            return redirect('mycart')

        order = Order.objects.create(
            customer=detail,
            grand_total=0,
        )

        grand_total = 0

        # LOOP — process each item separately
        for prod_id, item in cart.items():

            qty = item.get("quantity", 1)
            size = item.get("size") or ''  # ✔ correct size for THIS product
            beads_name = item.get("beads_name") or ''

            prodt = product.objects.get(id=prod_id)

            # Get variant for THIS product
            variant = None
            if size:
                try:
                    variant = ProductVariant.objects.get(prod=prodt, size=size)
                except ProductVariant.DoesNotExist:
                    variant = None   # avoid crash

            total = prodt.discounted_price * qty

            # Create cart items
            Orderitem.objects.create(
                order=order,
                product=prodt,
                quantity=qty,
                variant=variant,   # NOW works ✔
                price=prodt.discounted_price,
                beads_name=beads_name,
                total=total,
                image=prodt.image.name
            )

            grand_total += total

        order.grand_total = grand_total + 250
        order.save()
        send_order_notification(order)

        # Empty cart
        request.session['cart'] = {}
        messages.success(request, "Order placed successfully!")
        return redirect('mycart')

def send_order_notification(order):
    subject = f"New Order #{order.id} unPaid"
    message = (
        f"Hello Admin,\n\n"
        f"Order #{order.id} unpaid.\n"
        f"Customer: {order.customer.customer_name}\n"
        f"Total: {order.grand_total}\n"
        f"Check your admin panel for details."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],  # your email here
        fail_silently=False,
    )

def signup(request):
    
    if request.method =='POST':
        form=UserCreationForm(request.POST)
        if form.is_valid(): 
            user=form.save()
            login(request,user)
            messages.success(request,'successfully login!')
            return redirect('home')
    else:
        initial_data={'username':'','email':'','password1':'','password2':'','email':''}
        form=UserCreationForm(initial=initial_data)
        
    return render(request,'signup.html',{'form':form})

def login_view(request):
    if request.method=='POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user=form.get_user()
            login(request,user)
            messages.success(request,f'{user} successfully login!')
            return redirect('home')
        else:
            messages.error(request,'Invalid Username or Password')

    else:
        initial_data={'username':'','password':''}
        form=AuthenticationForm(initial=initial_data)
    return render(request,'login.html',{'form':form})

def home(request):
    cart = request.session.get('cart', {})
    
    # Compute cart_count correctly (sum of quantities)
    cart_count = sum(item['quantity'] if isinstance(item, dict) else int(item) for item in cart.values())
    
    categories = category.objects.all()
    category_id = request.GET.get("category_id")
    

    if category_id:
        filter_product = product.objects.filter(category_id=category_id)
        return render(request, "home.html", {
            "categories": categories,
            "products": filter_product,
            "cart_count": cart_count,
        })

    all_products = product.objects.all()
    pro_variant = ProductVariant.objects.values_list('size', flat=True).distinct()

    return render(request, 'home.html', {
        'categories': categories,
        'products': all_products,

        'pro_variant': pro_variant,
        'cart_count': cart_count,
    })

def all_categories(request):
    """Display all categories page"""
    categories = category.objects.all()
    all_products = product.objects.all()
    
    # Get cart count
    cart_count=sum(item['quantity'] if isinstance(item, dict) else int(item) for item in request.session.get('cart', {}).values())

    context = {
        'categories': categories,
        'products': all_products,
        'cart_count': cart_count,
    }
    return render(request, 'home.html', context)

def category_products(request, cat_id):
    """Display products for a specific category"""
    categories = get_object_or_404(category,id=cat_id)
    products = product.objects.filter(
        category=categories,
    )
    
    # Get cart count
    cart_count = 0
    cart_count=sum(item['quantity'] if isinstance(item, dict) else int(item) for item in request.session.get('cart', {}).values())
    context = {
        'category': categories,
        'products': products,
        'cart_count': cart_count,
    }
    return render(request, 'home.html', context)



def logout_view(request):
    logout(request)
    return redirect('login')
def contact(request):
    cart=request.session.get('cart',{})
    cart_count = sum(cart.values())
    return render(request,'contact.html',{'cart_count':cart_count})
def about(request):
    cart=request.session.get('cart',{})
    cart_count = sum(cart.values())
    return render(request,'about.html',{'cart_count':cart_count})
       ############################## customer panel#####################################
class Cust_admin(View):
    def get(self,request):
        order_obj=Order.objects.all()
        order_count=Order.objects.count()
        cust_obj=Customerdetail.objects.all()
        cust_count=Customerdetail.objects.count()
        order_items=Orderitem.objects.all()
        sale_total=Order.objects.aggregate(Sum("grand_total"))["grand_total__sum"] or 0
        Products=product.objects.all()
        return render(request,'cust_admin/base.html',{'product':Products,'order':order_obj,'customer':cust_obj,'all_items':order_items,'order_count':order_count,'cust_count':cust_count,'sales':sale_total})

def ad_dash(request):
    order_obj=Order.objects.all()
    order_count=Order.objects.count()
    cust_obj=Customerdetail.objects.all()
    cust_count=Customerdetail.objects.count()
    order_items=Orderitem.objects.all()
    sale_total=Order.objects.aggregate(Sum("grand_total"))["grand_total__sum"] or 0
    Products=product.objects.all()
    return render(request,'cust_admin/dashboard.html',{'product':Products,'order':order_obj,'customer':cust_obj,'all_items':order_items,'order_count':order_count,'cust_count':cust_count,'sales':sale_total})

def ad_cust(request):
    cust_obj=Customerdetail.objects.all()
    return render(request, "cust_admin/customer.html",{'customer':cust_obj,})

def ad_ord(request):
    order_obj=Order.objects.all()
    order_items=Orderitem.objects.all()
    return render(request, "cust_admin/order.html",{'order':order_obj,'all_items':order_items,})

def ad_prod(request):
    Products=product.objects.all()
    return render(request, "cust_admin/product.html",{'product':Products})

def add_product(request):
    if request.method == 'POST':
        name=request.POST.get('name')
        price=request.POST.get('price')
        description=request.POST.get('description')
        image=request.FILES.get('image')
        category_id=request.POST.get('category')
        if name and price and image and category_id:
            cat = category.objects.get(id=category_id)  
            product.objects.create(
                name=name,
                price=price,
                image=image,
                description=description,
                category=cat,

            )
        return redirect('ad_products')
    else:
        form=product()
    categories = category.objects.all()
    return render(request, "cust_admin/addproduct.html", {"categories": categories})

def add_category(request):
    if request.method == 'POST':
        category_name=request.POST.get('name')
        form=category(category=category_name)
        if form:
            form.save()
            return redirect('addproduct')
        
    else:
        form=category()
    return render(request,'cust_admin/addcategory.html')

def editproduct(request,product_id):
    prod = get_object_or_404(product, id=product_id)
    categories = category.objects.all()

    if request.method == "POST":
        prod.name = request.POST.get("name")
        prod.price = request.POST.get("price")
        prod.category_id = request.POST.get("category")

        if request.FILES.get("image"):  # update image only if a new one uploaded
            prod.image = request.FILES.get("image")
            messages.success(request,'Product updated successfully!!')
        prod.save()
        return redirect("ad_products")

    return render(request, "cust_admin/addproduct.html", {
        "prod": prod,
        "categories": categories
    })

def delproduct(request,product_id):
    productid=product.objects.get(id=product_id)
    productid.delete()
    messages.success(request,'Product deleted successfully!!')
    return redirect('ad_products')

def store(request):
    return redirect('home')

@csrf_exempt   # if you're already using fetch with CSRF, you can remove this
def update_order_status(request, order_id):
    """Update the status of an order"""
    if request.method == "POST":
        new_status = request.POST.get("status")
        try:
            order = Order.objects.get(id=order_id)
            order.status = new_status
            order.save()
            return JsonResponse({"success": True, "status": order.status})
        except Order.DoesNotExist:
            return JsonResponse({"success": False, "error": "Order not found"})
    
    return JsonResponse({"success": False, "error": "Invalid request"})

def get_order_items(request, order_id):
    """Return all order items for a given order in JSON format"""
    items = Orderitem.objects.filter(order_id=order_id).select_related("product")
    
    data = {
        "items": [
            {
                "id": item.id,
                "product_name": item.product.name if item.product else "N/A",
                "quantity": item.quantity,
                "price": str(item.price),   # str() to avoid Decimal serialization issues
            }
            for item in items
        ]
    }
    return JsonResponse(data)



def search_bar(request):
    query=request.POST.get('q')
    category_q=request.POST.get('category_search')
    products=product.objects.all()
    if query:
        products=products.filter(
            Q(name__icontains=query)|
            Q(discounted_price__icontains=query)|
            Q(category__category__icontains=query)
        )
    if category_q:
        products=products.filter(
            Q(category__category__icontains=category_q)
        )
    
    return render(request,'cust_admin/product.html',{'product':products})

def search_bar_home(request):
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())

    query = request.POST.get('q')
    products = product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(discounted_price__icontains=query) |
            Q(category__category__icontains=query)
        )

    return render(request, 'home.html', {
        'products': products,      # 👈 use ONE variable name
        'cart_count': cart_count,
    })

def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "invoice.html", {"order": order})

@staff_member_required   
def order_history(request):
    histories = Orderhistory.objects.all()
    return render(request, "cust_admin/orderhistory.html", {"histories": histories})



def search_order(request):

    if request.method=='POST':
        q=request.POST.get("q",'').strip()
        if q:
            order=Order.objects.filter(
                Q(id__icontains=q) |
                Q(customer__customer_name__icontains=q) |
                Q(created_date__icontains=q) 
            )
    order_items=Orderitem.objects.all()
    return render(request, "cust_admin/order.html",{'order':order,'all_items':order_items,})

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

def order_pdf(request, order_id):
    order = Order.objects.get(id=order_id)

    # Response settings
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="order_{order.id}.pdf"'

    # PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(1 * inch, height - 1 * inch, f"Order Invoice #{order.id}")

    # Customer details
    p.setFont("Helvetica", 12)
    p.drawString(1 * inch, height - 1.5 * inch, f"Customer: {order.customer.customer_name}")
    p.drawString(1 * inch, height - 1.8 * inch, f"Email: {order.customer.customer_email}")
    p.drawString(1 * inch, height - 2.1 * inch, f"Phone: {order.customer.customer_number}")
    p.drawString(1 * inch, height - 2.4 * inch, f"Date: {order.created_date.strftime('%Y-%m-%d')}")

    # Table header
    y = height - 3 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1 * inch, y, "Item")
    p.drawString(3.5 * inch, y, "Quantity")
    p.drawString(5 * inch, y, "discounted_Price")
    y -= 0.3 * inch

    # Table rows (order items)
    p.setFont("Helvetica", 12)
    for item in order.orderitem_set.all():
        p.drawString(1 * inch, y, str(item.product))
        p.drawString(3.5 * inch, y, str(item.quantity))
        p.drawString(5 * inch, y, f"{item.total} $")
        y -= 0.25 * inch

    # Grand total
    y -= 0.3 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1 * inch, y, f"Grand Total: {order.grand_total} $")

    # Finish
    p.showPage()
    p.save()

    return response



@method_decorator(csrf_exempt, name='dispatch')
class CartAjax(View):
    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            quantity = int(data.get('quantity', 1))
            size = data.get('size')  # may be None
            beads_name = data.get('beads_name') if data.get('beads_name') is not None else None
            cart = request.session.get('cart', {})

            existing = cart.get(product_id)

            if isinstance(existing, dict):
                # add quantity and update size and beads_name only if provided
                existing_qty = int(existing.get('quantity', 0))
                new_qty = existing_qty + quantity
                new_size = size if (size is not None) else existing.get('size')
                new_beads_name = beads_name if (beads_name is not None and beads_name != '') else existing.get('beads_name')
                cart[product_id] = {"quantity": new_qty, "size": new_size, "beads_name": new_beads_name}
            elif existing is None:
                cart[product_id] = {"quantity": quantity, "size": size, "beads_name": beads_name}
            else:
                # legacy int value
                try:
                    existing_qty = int(existing)
                except:
                    existing_qty = 0
                cart[product_id] = {"quantity": existing_qty + quantity, "size": size, "beads_name": beads_name}

            request.session['cart'] = cart

            # Compute total cart count: sum of all quantities
            cart_count = sum(item['quantity'] if isinstance(item, dict) else int(item) for item in cart.values())
            
            return JsonResponse({'success': True, 'cart_count': cart_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


def pro_details(request, product_id):
    # Main Product
    prod = get_object_or_404(product, id=product_id)

    # Related Products: same category & exclude current product
    related = product.objects.filter(category=prod.category).exclude(id=prod.id)[:10]

    # Compute cart_count
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] if isinstance(item, dict) else int(item) for item in cart.values())

    return render(request, 'productdetail.html', {
        'product': prod,
        'related_products': related,
        'cart_count': cart_count,
    })

