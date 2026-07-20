# notify.py
from plyer import notification

try:
    from android.permissions import request_permissions, Permission
    from android import api_version, mActivity
    ANDROID = True
except ImportError:
    ANDROID = False

def init_notifications():
    """
    Запрашивает разрешение POST_NOTIFICATIONS для Android 13+ и создаёт канал уведомлений для Android 8+.
    """
    if ANDROID:
        try:
            # Запрос разрешения (для Android 13+)
            request_permissions([Permission.POST_NOTIFICATIONS])
            
            # Создание канала для Android 8+ (API 26+)
            if api_version >= 26:
                from android.content import Context
                from android.app import NotificationChannel, NotificationManager
                
                channel_id = "ruble_channel"
                channel_name = "Ruble напоминания"
                importance = NotificationManager.IMPORTANCE_DEFAULT
                
                channel = NotificationChannel(channel_id, channel_name, importance)
                nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
                nm.createNotificationChannel(channel)
                
                # Сохраняем ID канала для использования в send_notification
                # (plyer не умеет передавать канал, поэтому мы будем использовать свой метод отправки)
                # Но для простоты оставим plyer – он будет использовать канал по умолчанию,
                # а мы явно создали канал, чтобы он существовал.
        except Exception as e:
            print(f"Ошибка инициализации уведомлений: {e}")

def send_notification(title, message, timeout=0):
    """
    Отправляет системное уведомление.
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Ruble",
            timeout=timeout,
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")