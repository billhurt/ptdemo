import json
import stripe
from datetime import date, timedelta, datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Booking

stripe.api_key = settings.STRIPE_SECRET_KEY

# ---------------------------------------------------------------------------
# Trainers & availability config — edit this to customise your demo
# ---------------------------------------------------------------------------
TRAINERS = [
    {'id': 'alex', 'name': 'Alex Reid',    'speciality': 'Strength & Conditioning'},
    {'id': 'sara', 'name': 'Sara Okafor',  'speciality': 'HIIT & Fat Loss'},
    {'id': 'tom',  'name': 'Tom Hargreaves','speciality': 'Mobility & Rehab'},
]

# Available time slots (24h format strings)
TIME_SLOTS = ['06:00', '07:00', '08:00', '09:00', '10:00',
              '12:00', '13:00', '17:00', '18:00', '19:00', '20:00']


def _available_dates(days_ahead=28):
    """Return the next `days_ahead` days excluding Sundays."""
    today = date.today()
    return [
        today + timedelta(days=i)
        for i in range(1, days_ahead + 1)
        if (today + timedelta(days=i)).weekday() != 6  # 6 = Sunday
    ]


def _booked_slots(session_date, trainer_id):
    """Return set of time strings already booked for a trainer on a date."""
    bookings = Booking.objects.filter(
        session_date=session_date,
        trainer=trainer_id,
        status__in=['pending', 'confirmed'],
    )
    return {b.session_time.strftime('%H:%M') for b in bookings}


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------
def landing(request):
    return render(request, 'booking/landing.html')


# ---------------------------------------------------------------------------
# Book — step 1: pick trainer, date, time
# ---------------------------------------------------------------------------
def book(request):
    available_dates = _available_dates()
    # Serialise dates for JS
    dates_json = json.dumps([d.isoformat() for d in available_dates])
    dates_display = {d.isoformat(): d.strftime('%a %d %b') for d in available_dates}

    context = {
        'trainers': TRAINERS,
        'time_slots': TIME_SLOTS,
        'available_dates': available_dates,
        'dates_json': dates_json,
        'dates_display': json.dumps(dates_display),
        'session_price': settings.SESSION_PRICE // 100,
        'session_currency': settings.SESSION_CURRENCY.upper(),
    }
    return render(request, 'booking/book.html', context)


# ---------------------------------------------------------------------------
# AJAX: return unavailable slots for a trainer + date
# ---------------------------------------------------------------------------
def availability(request):
    trainer_id = request.GET.get('trainer')
    date_str = request.GET.get('date')
    if not trainer_id or not date_str:
        return JsonResponse({'booked': []})
    try:
        session_date = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'booked': []})
    booked = list(_booked_slots(session_date, trainer_id))
    return JsonResponse({'booked': booked})


# ---------------------------------------------------------------------------
# Create Stripe Checkout Session
# ---------------------------------------------------------------------------
@require_POST
def create_checkout_session(request):
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    trainer_id = request.POST.get('trainer', '').strip()
    session_date_str = request.POST.get('session_date', '').strip()
    session_time_str = request.POST.get('session_time', '').strip()

    # Basic validation
    if not all([name, email, trainer_id, session_date_str, session_time_str]):
        return redirect('book')

    trainer = next((t for t in TRAINERS if t['id'] == trainer_id), None)
    if not trainer:
        return redirect('book')

    try:
        session_date = date.fromisoformat(session_date_str)
        session_time = datetime.strptime(session_time_str, '%H:%M').time()
    except ValueError:
        return redirect('book')

    # Create a pending booking first (confirmed on webhook)
    booking = Booking.objects.create(
        name=name,
        email=email,
        trainer=trainer_id,
        session_date=session_date,
        session_time=session_time,
        status='pending',
    )

    price_pence = settings.SESSION_PRICE
    currency = settings.SESSION_CURRENCY
    session_label = f"{settings.SESSION_NAME} with {trainer['name']}"
    date_label = session_date.strftime('%a %d %b %Y')

    checkout = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': currency,
                'unit_amount': price_pence,
                'product_data': {
                    'name': session_label,
                    'description': f"{date_label} at {session_time_str}",
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        customer_email=email,
        metadata={
            'booking_id': str(booking.id),
            'name': name,
            'trainer': trainer['name'],
            'session_date': session_date_str,
            'session_time': session_time_str,
        },
        success_url=request.build_absolute_uri(f'/success/?booking_id={booking.id}'),
        cancel_url=request.build_absolute_uri('/book/'),
    )

    # Save stripe session id
    booking.stripe_session_id = checkout.id
    booking.save()

    return redirect(checkout.url, code=303)


# ---------------------------------------------------------------------------
# Success page
# ---------------------------------------------------------------------------
def success(request):
    booking_id = request.GET.get('booking_id')
    booking = None
    if booking_id:
        try:
            booking = Booking.objects.get(id=int(booking_id))
        except (Booking.DoesNotExist, ValueError):
            pass
    return render(request, 'booking/success.html', {'booking': booking})


# ---------------------------------------------------------------------------
# Stripe webhook — confirm booking on payment
# ---------------------------------------------------------------------------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        booking_id = session.get('metadata', {}).get('booking_id')
        if booking_id:
            Booking.objects.filter(id=int(booking_id)).update(status='confirmed')

    return HttpResponse(status=200)