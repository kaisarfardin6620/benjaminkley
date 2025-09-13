from fcm_django.models import FCMDevice
from .models import Notification

def create_and_send_notification(user, title, message):
    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )

    try:
        devices = FCMDevice.objects.filter(user=user, active=True)
        if devices.exists():
            devices.send_message(
                title=title,
                body=message
            )
            print(f"Successfully sent push notification to {devices.count()} devices for user {user.username}.")
        else:
            print(f"No active devices found for user {user.username}. Push notification not sent.")
    except Exception as e:
        print(f"Failed to send push notification for user {user.username}: {e}")