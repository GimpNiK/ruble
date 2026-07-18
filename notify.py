# notify.py
from plyer import notification

try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False

def init_notifications():
    """Запрашивает разрешение на уведомления для Android 13+."""
    if ANDROID:
        try:
            request_permissions([Permission.POST_NOTIFICATIONS])
        except Exception as e:
            print(f"Ошибка запроса разрешения на уведомления: {e}")

def send_notification(title, message, timeout=0):
    """
    Отправляет системное уведомление.
    
    Args:
        title (str): Заголовок
        message (str): Текст
        timeout (int): Время в секундах, через которое уведомление исчезнет.
                        0 = не исчезает автоматически (остаётся в шторке).
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