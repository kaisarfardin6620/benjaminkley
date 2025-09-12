from .models import Notification
from fcm_django.models import FCMDevice

def create_and_send_notification(user, title, message):
    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )

    devices = FCMDevice.objects.filter(user=user, active=True)
    devices.send_message(
        title=title,
        body=message
    )