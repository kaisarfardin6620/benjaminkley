import firebase_admin
from firebase_admin import messaging
from fcm_django.models import FCMDevice


def create_and_send_notification(user, title: str, message: str):
    """
    Creates and sends a Firebase Cloud Message (FCM) push notification
    to a user's registered devices.

    Args:
        user: The Django User object.
        title: The title of the notification.
        message: The body of the notification message.
    """
    try:
        # Get all active devices for the specified user
        devices = FCMDevice.objects.filter(user=user, active=True)

        if not devices.exists():
            print(f"No active devices found for user {user.username}. Notification not sent.")
            return

        # Create a Message object with the notification payload
        notification_message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message,
            )
        )

        # Send the message to all devices. The 'message' argument is now correct.
        devices.send_message(notification_message)
        print(f"Successfully sent notification to {devices.count()} devices for user {user.username}.")
    except Exception as e:
        print(f"Failed to send notification for user {user.username}: {e}")
