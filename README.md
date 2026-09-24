# JARVIS — Kişisel Masaüstü Yapay Zekâ Asistanı (Faz 1 / MVP)

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
- ✅ "Jarvis" wake word döngüsü (bkz. sınırlamalar aşağıda)
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
- ✅ Log sistemi (logs/jarvis.log), her modülde çökme yerine sade hata mesajı

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
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Bağımlılıkları kur:
   ```
   pip install -r requirements.txt
   ```
   Not: `PyAudio` bazı Windows kurulumlarında pip ile derlenemeyebilir.
   Sorun yaşarsan: `pip install pipwin && pipwin install pyaudio`
4. `.env.example` dosyasını `.env` olarak kopyala ve `GEMINI_API_KEY`
   değerini kendi anahtarınla değiştir.
5. Çalıştır:
   ```
   python main.py
   ```
6. Açılan pencerede "Dinlemeyi Başlat" butonuna bas, sonra mikrofona
   "Jarvis" diyerek uyandır ve komutunu söyle.

## Klasör Yapısı

```
JARVIS/
├── main.py                  # Giriş noktası
├── config/settings.py       # .env okuma, merkezi ayarlar
├── core/
│   ├── ai.py                 # Gemini + function-calling döngüsü ("beyin")
│   ├── router.py              # Tool şemaları + gerçek fonksiyonlara yönlendirme
│   ├── memory.py               # Kısa/uzun süreli hafıza
│   ├── security.py             # Kritik işlem onay sistemi
│   └── logger.py               # Ortak loglama
├── voice/
│   ├── speech_to_text.py     # Mikrofon -> metin
│   ├── text_to_speech.py       # Metin -> Türkçe ses
│   └── wake_word.py             # "Jarvis" uyandırma döngüsü
├── tools/                    # Her biri bağımsız, LLM tarafından çağrılabilir
│   ├── applications.py, browser.py, filesystem.py, system.py,
│   │   web.py, notifications.py, media.py, memory_tool.py
├── ui/
│   ├── main_window.py         # PyQt5 ana pencere
│   └── animations.py            # Animasyonlu çekirdek widget'ı
├── database/memory.db        # Çalışma zamanında otomatik oluşur
└── logs/jarvis.log           # Çalışma zamanında otomatik oluşur
```

## Yeni Yetenek Eklemek

1. `tools/` altına yeni bir dosya oluştur (ör. `tools/spotify.py`), fonksiyonunu yaz.
2. `core/router.py` içindeki `TOOL_SCHEMAS` listesine yeni tool'un adını/açıklamasını/parametrelerini ekle.
3. Aynı dosyadaki `TOOL_DISPATCH` sözlüğüne fonksiyonu ekle.
4. Kritik/geri dönüşü zor bir işlemse `core/security.py -> CRITICAL_ACTIONS` kümesine adını ekle.

Ana sistemde (`core/ai.py`, `main.py`) HİÇBİR değişiklik yapmana gerek yok.

## Bilinen Sınırlamalar (dürüst özet)

- Uygulama açma/kapatma ve ses seviyesi kontrolü **sadece Windows**'ta çalışır.
- Wake word tespiti internet bağlantısı gerektirir (Google STT tabanlı).
- Web arama, gerçek zamanlı finans verisi (ör. anlık Bitcoin fiyatı) için
  güvenilir bir kaynak DEĞİLDİR; genel metin arama sonucu döner.
- `KNOWN_APPS` / `PROCESS_NAMES` sözlükleri (tools/applications.py) sınırlı
  sayıda yaygın uygulama içerir; kendi kurulu uygulamalarını eklemen gerekebilir.
