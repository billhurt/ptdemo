from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('success/', views.success, name='success'),
]