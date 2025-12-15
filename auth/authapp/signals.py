# authapp/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Order, Orderhistory

@receiver(pre_save, sender=Order)
def save_delivered(sender, instance, **kwargs):
    if instance.pk:  # only if order already exists
        old_order = Order.objects.get(pk=instance.pk)

        if old_order.status != instance.status and instance.status == 'Deliverd':
            Orderhistory.objects.create(
                order_id=instance,
                current_status=instance.status,
            )
            print(f"✅ Order {instance.pk} status changed: {old_order.status} → {instance.status}")
