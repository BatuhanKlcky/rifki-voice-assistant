# RIFKI — Kişisel Masaüstü Yapay Zekâ Asistanı (Faz 1 / MVP)

Türkçe konuşan, sesli komutları anlayan, Google Gemini tabanlı bir
karar mekanizmasıyla bilgisayarında güvenli işlemler yapabilen, PyQt5
tabanlı futuristik arayüze sahip bir masaüstü asistanı.

Bu bir demo/prototip değil, gerçekten çalışan bir Python uygulamasıdır.
Ancak dürüstçe belirtmek gerekir: bazı bölümler (aşağıda "Faz 2" olarak
işaretlenenler) bilinçli olarak iskelet/TODO bırakıldı — sahte biçimde
"çalışıyormuş gibi" gösterilmedi.

## Ne Çalışıyor (Faz 1 — bu teslimat)

- ✅ Futuristik PyQt5 arayüzü (animasyonlu çekirdek, durum göstergesi, sohbet paneli, CPU/RAM, saat)
- ✅ Türkçe mikrofon girişi + Google Speech Recognition ile metne çevirme
- ✅ "Rıfkı" wake word döngüsü (bkz. sınırlamalar aşağıda)
- ✅ Gemini API ile tool-calling (function calling) tabanlı karar sistemi (core/ai.py)
- ✅ gTTS / pyttsx3 ile Türkçe sesli yanıt
- ✅ Temel sohbet + bağlam hafızası (kısa süreli)
- ✅ Uzun süreli hafıza (SQLite: "bunu hatırla" / "bunu unut")
- ✅ Uygulama açma/kapatma (bilinen uygulamalar listesi)
- ✅ Web sitesi / YouTube / Google arama açma
- ✅ İnternette bilgi arama (DuckDuckGo metin araması, API anahtarsız)
- ✅ Dosya arama / oluşturma / kopyalama / taşıma / yeniden adlandırma / silme
- ✅ Sistem bilgisi (CPU, RAM, disk), tarih-saat
- ✅ Ekran görüntüsü alma
- ✅ Ses seviyesi ayarlama (Windows + pycaw)
- ✅ Masaüstü bildirimi gönderme (Windows + win10toast)
- ✅ Kritik işlemler (kapatma, yeniden başlatma, dosya silme vb.) için onay sistemi
- ✅ Log sistemi (logs/rifki.log), her modülde çökme yerine sade hata mesajı

## Faz 2'ye Bırakılanlar (şu an İSKELET / TODO — sahte çalışmıyor)

- ⏳ `tools/media.py`: Müzik/video çalma — sadece "henüz desteklenmiyor" mesajı döner.
- ⏳ `tools/notifications.py -> set_reminder`: Gerçek zamanlayıcı yok, sadece loglar.
- ⏳ Gerçek offline wake-word motoru (Porcupine vb.) — şu an Google STT ile
  taklit ediliyor (bkz. `voice/wake_word.py` içindeki not, daha yüksek gecikme).
- ⏳ Eklenti sistemi (spotify.py, discord.py, github.py, calendar.py) — mimari
  buna hazır (`tools/` klasörüne yeni dosya + `core/router.py`'a şema eklemek
  yeterli) ama henüz yazılmadı.

## Gereken API Anahtarları

| Anahtar | Zorunlu mu? | Nereden alınır |
|---|---|---|
| `GEMINI_API_KEY` | **Evet** | https://aistudio.google.com/apikey (ücretsiz kotalı) |

Diğer tüm özellikler (STT, TTS, web arama) API anahtarı gerektirmeyen
ücretsiz servisler/kütüphaneler kullanır (Google Speech Recognition web
servisi, gTTS, DuckDuckGo arama). Bunun karşılığında: production/kurumsal
kullanım için garanti sunmazlar, sadece kişisel/geliştirme amaçlı MVP için
uygundurlar.

## Kurulum (Windows)

1. Python 3.10+ kurulu olduğundan emin ol.
2. Proje klasöründe bir sanal ortam oluştur:
