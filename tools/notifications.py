j"""
tools/notifications.py
-----------------------
Windows bildirim (toast) gönderme. win10toast kütüphanesi kullanılır.

DURUM: Faz-2 özelliği. Temel fonksiyon çalışır durumda, ancak zamanlayıcı /
hatırlatıcı (belirli bir saatte otomatik bildirim) için ayrı bir arka plan
zamanlayıcısı (ör. APScheduler) main.py'ye entegre edilmelidir — bu MVP'de
YOK, TODO.
"""

from config.settings import settings
from core.logger import get_logger

log = get_logger("tools.notifications")


def send_notification(title: str, message: str, duration: int = 5) -> str:
    if not settings.IS_WINDOWS:
        return "Bildirimler şu an sadece Windows'ta destekleniyor."
    try:
        from win10toast import ToastNotifier

        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=duration, threaded=True)
        log.info(f"Bildirim gönderildi: {title} - {message}")
        return "Bildirim gönderildi."
    except ImportError:
        return "Bildirim kütüphanesi (win10toast) kurulu değil."
    except Exception as e:
        log.error(f"Bildirim hatası: {e}")
        return "Bildirim gönderilirken bir sorun oluştu."


def set_reminder(message: str, when: str) -> str:
    """TODO (Faz 2): Gerçek zamanlayıcı entegrasyonu yok. Şimdilik sadece
    isteği loglar ve dürüstçe henüz desteklenmediğini söyler."""
    log.info(f"Hatırlatıcı isteği (henüz desteklenmiyor): {message} @ {when}")
    return (
        "Zamanlayıcı/hatırlatıcı özelliği henüz eklenmedi (Faz 2 planında). "
        "Şu an bu isteği gerçekten zamanlayamıyorum."
    )
