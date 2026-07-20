# notify.py
try:
    from android.permissions import request_permissions, Permission
    from android import api_version, mActivity
    ANDROID = True
except ImportError:
    ANDROID = False

def init_notifications():
    """Запрашивает разрешение и создаёт канал уведомлений (Android 8+)."""
    if ANDROID:
        try:
            request_permissions([Permission.POST_NOTIFICATIONS])
            if api_version >= 26:
                from android.content import Context
                from android.app import NotificationChannel, NotificationManager
                channel_id = "ruble_channel"
                channel_name = "Ruble напоминания"
                importance = NotificationManager.IMPORTANCE_DEFAULT
                channel = NotificationChannel(channel_id, channel_name, importance)
                nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
                nm.createNotificationChannel(channel)
        except Exception as e:
            print(f"Ошибка инициализации уведомлений: {e}")

def send_notification(title, message, timeout=0):
    """
    Отправляет системное уведомление на Android через прямой API.
    На других платформах использует plyer (запасной вариант).
    """
    if ANDROID:
        try:
            from android import mActivity
            from android.content import Context, Intent
            from android.app import Notification, NotificationManager, PendingIntent
            from android.graphics import BitmapFactory
            import os

            # Создаём Intent для открытия приложения при нажатии
            package_name = mActivity.getPackageName()
            intent = Intent(mActivity, mActivity.getClass())
            intent.setAction(Intent.ACTION_MAIN)
            intent.addCategory(Intent.CATEGORY_LAUNCHER)
            # Флаг IMMUTABLE для API 31+
            flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            pending_intent = PendingIntent.getActivity(mActivity, 0, intent, flags)

            # Строим уведомление
            builder = Notification.Builder(mActivity, "ruble_channel")
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(mActivity.getApplicationInfo().icon)
            builder.setContentIntent(pending_intent)
            builder.setAutoCancel(True)

            # Для Android 5+ можно добавить большой текст
            if api_version >= 21:
                builder.setStyle(Notification.BigTextStyle().bigText(message))

            notification = builder.build()
            nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
            nm.notify(1, notification)  # id = 1 (можно увеличивать, если нужно несколько)
            print(f"Уведомление отправлено: {title}")
        except Exception as e:
            print(f"Ошибка отправки уведомления (прямой API): {e}")
            # Запасной вариант через plyer (на случай, если что-то пойдёт не так)
            try:
                from plyer import notification as plyer_notify
                plyer_notify.notify(title=title, message=message, app_name="Ruble", timeout=timeout)
            except Exception as e2:
                print(f"Ошибка отправки уведомления (plyer): {e2}")
    else:
        # Не Android — используем plyer
        try:
            from plyer import notification as plyer_notify
            plyer_notify.notify(title=title, message=message, app_name="Ruble", timeout=timeout)
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")