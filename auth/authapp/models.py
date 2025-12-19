from django.db import models
# Create your models here.


class category(models.Model):
    category=models.CharField(max_length=100)
    def __str__(self):
        return self.category

class product(models.Model):
    name=models.CharField(max_length=150)
    price=models.FloatField(default=0)
    discounted_price=models.FloatField(default=0)
    date=models.DateTimeField(auto_now_add=True)
    description=models.TextField(default='unknown')
    image=models.ImageField(upload_to='images/')
    category=models.ForeignKey(category,on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    prod = models.ForeignKey(product, on_delete=models.CASCADE, related_name="variants")



    # Shopify-style size pairs (Label | Value)
    size = models.CharField(
        max_length=30,
    )

    # Stock for each variant
    # stock = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.prod.name} - {self.size}"



class Customerdetail(models.Model):
    customer_name=models.CharField(max_length=150,default='unknown')
    customer_city=models.CharField(max_length=150,default='unknown')
    customer_province=models.CharField(max_length=150,default='unknown',choices=[
        ('punjab','Punjab'),
        ('sindh','Sindh'),
        ('balochistan','Balochistan'),
        ('kpk','KPK'),
        ('gilgit','Gilgit'),
        ('islamabad','Islamabad'),
    ])
    customer_address=models.CharField(max_length=300,default='unknown')
    customer_number=models.CharField(max_length=14,default='unknown')
    def __str__(self):
        return self.customer_name

class Order(models.Model):
    customer=models.ForeignKey(Customerdetail,on_delete=models.CASCADE,related_name="items")
    created_date=models.DateField(auto_now_add=True)
    grand_total=models.BigIntegerField()
    status=models.CharField(
        max_length=20,
        choices=[    ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),],
                default='PENDING'
    )
    
class Orderitem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE ,default='unknown')
    beads_name=models.CharField(max_length=150,default='unknown',null=True, blank=True)
    product=models.ForeignKey(product,on_delete=models.CASCADE)
    image=models.CharField(max_length=300,default='No image find')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True)
    quantity=models.IntegerField()
    price=models.PositiveIntegerField()
    total=models.IntegerField()
    def __str__(self):
        return self.product.name

class Orderhistory(models.Model):
    order_id=models.ForeignKey(Order,related_name='history',on_delete=models.CASCADE)
    current_status=models.CharField(default='unknown',max_length=20)
    status_change_at=models.DateTimeField(auto_now_add=True)



    







