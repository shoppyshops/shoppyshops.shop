from django.urls import path
from . import views

app_name = 'shoppyshop'

urlpatterns = [
    path('webhooks/shopify/', views.shopify_webhook, name='shopify_webhook'),
    path('orders/', views.orders_list, name='orders_list'),
    path('services/status/', views.service_status, name='service_status'),
    path('events/', views.event_stream, name='event_stream'),
] 