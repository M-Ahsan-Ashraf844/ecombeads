from django.contrib import admin
from django.contrib.sessions.models import Session
from django.utils.html import format_html
from django.conf import settings
from .models import category,product,Order,Orderitem,Customerdetail,Orderhistory,ProductVariant
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
# Register your models here.
from django.urls import reverse

# admin.site.site_header = "My Shop Dashboard"
# admin.site.site_title = "My Shop Admin"
# admin.site.index_title = "Welcome to My Shop Admin Panel"

# admin.site.register(Orderhistory)

admin.site.register(Session)
@admin.register(category)
class admincat(admin.ModelAdmin):
    list_display=['id','category']



@admin.register(product)
class adminproducts(admin.ModelAdmin):
    list_display=['id','name','price','image','date','category','discounted_price']
    def image_tag(self, obj):
        if obj.image and obj.image != "No image find":
            return format_html(
                '<img src="{}{}" width="60" height="60" style="object-fit:cover; border-radius:5px;" />',
                settings.MEDIA_URL,
                obj.image
            )
        return "No Image"

    image_tag.short_description = "Image"

@admin.register(ProductVariant)
class adminproductsvariant(admin.ModelAdmin):
    list_display=['id','prod','size']

class OrderItemInline(admin.TabularInline):  
    model = Orderitem
    extra = 0 
    fields = ('sr_no',"product","quantity", "total")
    readonly_fields = ('sr_no', "product", "quantity", "total")

    def sr_no(self, obj):
        # Only show number for existing objects
        if obj.pk and obj.order_id:
            # Get all items of this order sorted by pk
            order_items = obj.order.orderitem_set.order_by('id')
            # Find position
            for idx, item in enumerate(order_items, start=1):
                if item.pk == obj.pk:
                    return idx
        return "—"

    sr_no.short_description = "Sr No"


@admin.register(Order)
class adminorder(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display=['customer','grand_total','status','created_date']
    readonly_fields=['sr_no','customer','grand_total']
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'print/<int:order_id>/',
                self.admin_site.admin_view(self.print_order),
                name="print_order"
            ),
        ]
        return custom_urls + urls
    

    def print_order(self, request, order_id):
        order = Order.objects.get(id=order_id)
        html = render_to_string("admin/print_order.html", {"order": order})
        return HttpResponse(html)
    
    def print_order_button(self, obj):
        if obj.pk:  # only for saved orders
            url = reverse("admin:print_order", args=[obj.pk])
            return format_html('<a class="button" href="{}" target="_blank">🖨️ Print</a>', url)
        return "—"
    print_order_button.short_description = "Print"

    
    def sr_no(self, obj):
        # Get all orders sorted by created_date (or id)
        orders = list(Order.objects.order_by('id'))
        return orders.index(obj) + 1
    sr_no.short_description = "Sr No"



@admin.register(Orderitem)
class adminitemsorder(admin.ModelAdmin):
    list_display=['order_id', 'product','image','quantity','price','total','variant','beads_name']
    def image_tag(self, obj):
        if obj.image and obj.image != "No image find":
            return format_html(
                '<img src="{}{}" width="60" height="60" style="object-fit:cover; border-radius:5px;" />',
                settings.MEDIA_URL,   # prefix
                obj.image
            )
        return "No Image"

    image_tag.short_description = "Image"



@admin.register(Customerdetail)
class adminCustomerdetail(admin.ModelAdmin):
    list_display=['id','customer_name','customer_city','customer_province','customer_address','customer_number',]






