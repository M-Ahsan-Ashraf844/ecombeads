from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from .models import category, product, ProductVariant


class CartAjaxTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.cat = category.objects.create(category='Test Category')
		image = SimpleUploadedFile('test.jpg', b'filecontent', content_type='image/jpeg')
		self.prod = product.objects.create(name='Test Product', price=100, image=image, category=self.cat)
		self.variant = ProductVariant.objects.create(prod=self.prod, size='M')

	def test_cart_ajax_saves_beads_name(self):
		url = reverse('cart_ajax')
		payload = {
			'product_id': str(self.prod.id),
			'quantity': 2,
			'size': self.variant.size,
			'beads_name': 'LuckyBead'
		}

		response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertTrue(data.get('success'))

		# Session should contain the cart and the beads_name for the product
		session_cart = self.client.session.get('cart')
		self.assertIsNotNone(session_cart)
		item = session_cart.get(str(self.prod.id))
		self.assertIsNotNone(item)
		self.assertEqual(item.get('beads_name'), 'LuckyBead')
