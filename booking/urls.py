from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('book/', views.book, name='book'),
    path('book/availability/', views.availability, name='availability'),
    path('book/checkout/', views.create_checkout_session, name='checkout'),
    path('success/', views.success, name='success'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]