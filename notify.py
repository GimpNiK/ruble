# notify.py
from plyer import notification

ANDROID = False
try:
    from android import mActivity, api_version
    ANDROID = True
except ImportError:
    pass

def init_notifications():
    if not ANDROID:
        return
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.POST_NOTIFICATIONS])
        if api_version >= 26:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            NotificationChannel = autoclass('android.app.NotificationChannel')
            NotificationManager = autoclass('android.app.NotificationManager')
            channel_id = "ruble_channel"
            channel_name = "Ruble напоминания"
            importance = NotificationManager.IMPORTANCE_DEFAULT
            channel = NotificationChannel(channel_id, channel_name, importance)
            nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
            nm.createNotificationChannel(channel)
    except Exception as e:
        print(f"Ошибка инициализации уведомлений: {e}")

def send_notification(title, message, timeout=0):
    if not ANDROID:
        try:
            notification.notify(title=title, message=message, app_name="Ruble", timeout=timeout)
        except Exception as e:
            print(f"Ошибка отправки уведомления (non-Android): {e}")
        return

    # Android: пробуем прямой API через jnius
    try:
        from jnius import autoclass
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')
        # Важно: Notification.Builder — вложенный класс, используем $
        NotificationBuilder = autoclass('android.app.Notification$Builder')
        NotificationManager = autoclass('android.app.NotificationManager')

        # Intent для открытия приложения
        package_name = mActivity.getPackageName()
        intent = Intent(mActivity, mActivity.getClass())
        intent.setAction(Intent.ACTION_MAIN)
        intent.addCategory(Intent.CATEGORY_LAUNCHER)

        # PendingIntent с FLAG_IMMUTABLE
        flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        pending_intent = PendingIntent.getActivity(mActivity, 0, intent, flags)

        # Строим уведомление через Builder
        builder = NotificationBuilder(mActivity, "ruble_channel")
        builder.setContentTitle(title)
        builder.setContentText(message)
        builder.setSmallIcon(mActivity.getApplicationInfo().icon)
        builder.setContentIntent(pending_intent)
        builder.setAutoCancel(True)
        if api_version >= 21:
            big_text = autoclass('android.app.Notification$BigTextStyle')
            builder.setStyle(big_text().bigText(message))

        notification_obj = builder.build()
        nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
        nm.notify(1, notification_obj)  # id = 1
        print(f"Уведомление отправлено (прямой API): {title}")
        return
    except Exception as e:
        print(f"Ошибка отправки уведомления (прямой API): {e}")

    # Запасной вариант: plyer (но добавляем флаг IMMUTABLE вручную? plyer не даёт)
    # Поэтому plyer скорее всего тоже упадёт. Но попробуем.
    try:
        notification.notify(title=title, message=message, app_name="Ruble", timeout=timeout)
        print(f"Уведомление отправлено через plyer (запасной): {title}")
    except Exception as e:
        print(f"Ошибка отправки уведомления через plyer: {e}")