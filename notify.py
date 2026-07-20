# notify.py
from plyer import notification

ANDROID = False
try:
    from android.permissions import request_permissions, Permission
    from android import mActivity, api_version
    ANDROID = True
except ImportError:
    pass

def init_notifications():
    if ANDROID:
        try:
            # Запрос разрешения для Android 13+
            request_permissions([Permission.POST_NOTIFICATIONS])
            # Создание канала для Android 8+
            if api_version >= 26:
                try:
                    from android.content import Context
                    from android.app import NotificationChannel, NotificationManager
                    channel_id = "ruble_channel"
                    channel_name = "Ruble напоминания"
                    importance = NotificationManager.IMPORTANCE_DEFAULT
                    channel = NotificationChannel(channel_id, channel_name, importance)
                    nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
                    nm.createNotificationChannel(channel)
                except Exception as e:
                    print(f"Ошибка создания канала уведомлений: {e}")
        except Exception as e:
            print(f"Ошибка инициализации уведомлений: {e}")

def send_notification(title, message, timeout=0):
    try:
        # Пробуем отправить через plyer
        notification.notify(
            title=title,
            message=message,
            app_name="Ruble",
            timeout=timeout,
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления через plyer: {e}")
        # Запасной вариант через прямой Android API
        if ANDROID:
            try:
                from android import mActivity
                from android.content import Context, Intent
                from android.app import Notification, NotificationManager, PendingIntent
                
                package_name = mActivity.getPackageName()
                intent = Intent(mActivity, mActivity.getClass())
                intent.setAction(Intent.ACTION_MAIN)
                intent.addCategory(Intent.CATEGORY_LAUNCHER)
                # Флаг IMMUTABLE для Android 12+
                flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                pending_intent = PendingIntent.getActivity(mActivity, 0, intent, flags)

                builder = Notification.Builder(mActivity, "ruble_channel")
                builder.setContentTitle(title)
                builder.setContentText(message)
                builder.setSmallIcon(mActivity.getApplicationInfo().icon)
                builder.setContentIntent(pending_intent)
                builder.setAutoCancel(True)

                if api_version >= 21:
                    builder.setStyle(Notification.BigTextStyle().bigText(message))

                notification_obj = builder.build()
                nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
                nm.notify(1, notification_obj)
                print(f"Уведомление отправлено через прямой API: {title}")
            except Exception as e2:
                print(f"Ошибка отправки уведомления (прямой API): {e2}")