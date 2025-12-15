from django.urls import path
from . import views
from .views import Cart,Cartview,RemoveCart,Update,Checkout,Cust_admin,CartAjax

urlpatterns = [
    # path('',views.login_view,name='login'),
    # path('signup/',views.signup,name='signup'),
    path('',views.home,name='home'),
    # path('logout/',views.logout_view,name='logout'),
    path('contact/',views.contact,name='contact'),
    path('categories/', views.all_categories, name='all_categories'),
    path('category/<int:cat_id>/', views.category_products, name='category'),
    path('about/',views.about,name='about'),
    path('mycart/',Cartview.as_view(),name='mycart'),
    path('product/<int:category_id>/cart/<int:product_id>/',Cart.as_view(),name='cart'),
    path('removecart/<int:product_id>/',RemoveCart.as_view(),name='removecart'),
    path('update/<int:product_id>/',Update.as_view(),name='update'),
    path('checkout/',Checkout.as_view(),name='checkout'),
    path('customer-admin/',Cust_admin.as_view(),name='cust_admin'),
    path('dashboard/',views.ad_dash,name='ad_dashboard'),
    path('order/',views.ad_ord,name='ad_orders'),
    path('customer/',views.ad_cust,name='ad_customers'),
    path('product/',views.ad_prod,name='ad_products'),
    path('add_category/',views.add_category,name='addcategory'),
    path('add_product/',views.add_product,name='addproduct'),
    path('editproduct/<int:product_id>/',views.editproduct,name='editproduct'),
    path('delproduct/<int:product_id>/',views.delproduct,name='delproduct'),
    path('',views.store,name='store'),
     path("update-order-status/<int:order_id>/", views.update_order_status, name="update-order-status"),
    path("get-order-items/<int:order_id>/", views.get_order_items, name="get-order-items"),
    path('search/',views.search_bar,name='search'),
    path('home-search/',views.search_bar_home,name='search_home'),
     path("invoice/<int:order_id>/", views.invoice_view, name="invoice"),
     path("order-history/", views.order_history, name="orderhistory"),
    path('search-order/',views.search_order,name='search_order'),
    path("order/<int:order_id>/pdf/",views.order_pdf, name="order_pdf"),
    path('cart-ajax/', CartAjax.as_view(), name='cart_ajax'),
    path("product-detail/<int:product_id>/",views.pro_details, name="productdetail"),


]