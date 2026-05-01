import stripe
from django.conf import settings
from django.shortcuts import render, redirect

stripe.api_key = settings.STRIPE_SECRET_KEY


def landing(request):
    return render(request, 'booking/landing.html', {
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


def create_checkout_session(request):
    if request.method != 'POST':
        return redirect('landing')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': settings.STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/success/'),
        cancel_url=request.build_absolute_uri('/'),
    )
    return redirect(session.url, code=303)


def success(request):
    return render(request, 'booking/success.html')