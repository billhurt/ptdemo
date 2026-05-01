from django.db import models


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    session_date = models.DateField()
    session_time = models.TimeField()
    trainer = models.CharField(max_length=100)
    stripe_session_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['session_date', 'session_time']

    def __str__(self):
        return f"{self.name} — {self.session_date} {self.session_time} ({self.status})"

    @property
    def session_datetime_display(self):
        return f"{self.session_date.strftime('%A %d %B %Y')} at {self.session_time.strftime('%H:%M')}"