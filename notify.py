# notify.py
from plyer import notification

ANDROID = False
try:
    from android import mActivity, api_version
    ANDROID = True
except ImportError:
    pass

def init_notifications():
    """Инициализация уведомлений: запрос разрешения и создание канала."""
    if not ANDROID:
        return
    try:
        # Запрос разрешения POST_NOTIFICATIONS (Android 13+)
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.POST_NOTIFICATIONS])
        
        # Создание канала для Android 8+ (API 26+)
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
    """Отправка уведомления через прямой Android API (с FLAG_IMMUTABLE)."""
    if ANDROID:
        try:
            from jnius import autoclass
            from android import mActivity, api_version
            
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            Notification = autoclass('android.app.Notification')
            NotificationManager = autoclass('android.app.NotificationManager')
            
            # Intent для открытия приложения при нажатии
            package_name = mActivity.getPackageName()
            intent = Intent(mActivity, mActivity.getClass())
            intent.setAction(Intent.ACTION_MAIN)
            intent.addCategory(Intent.CATEGORY_LAUNCHER)
            
            # Флаг IMMUTABLE обязателен для Android 12+
            flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            pending_intent = PendingIntent.getActivity(mActivity, 0, intent, flags)
            
            # Строим уведомление
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
            nm.notify(1, notification_obj)  # id = 1 (можно увеличить для нескольких)
            print(f"Уведомление отправлено через прямой API: {title}")
            return
        except Exception as e:
            print(f"Ошибка отправки уведомления (прямой API): {e}")
            # Запасной вариант: попробовать через plyer
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Ruble",
                    timeout=timeout,
                )
                print(f"Уведомление отправлено через plyer (запасной): {title}")
            except Exception as e2:
                print(f"Ошибка отправки уведомления через plyer: {e2}")
    else:
        # Не Android – используем plyer
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Ruble",
                timeout=timeout,
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")