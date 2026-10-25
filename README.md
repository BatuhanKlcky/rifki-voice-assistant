# RIFKI — Hibrit Masaüstü & Mobil Yapay Zekâ Asistanı (v2.4.0)

![RIFKI arayüzü](assets/arayuz.png)

Türkçe konuşan, sesli ve klavye komutlarını anlayan, Google Gemini tabanlı otonom karar mekanizmasıyla Windows işletim sisteminizi yöneten, PyQt5 tabanlı fütüristik masaüstü HUD ve gerçek zamanlı mobil PWA kokpitine sahip kişisel yapay zekâ asistanı.

---

## 🚀 Öne Çıkan Özellikler (v2.4.0)

- ⚡ **Global Spotlight Hızlı Komut Çubuğu (`Ctrl + Space` / `Ctrl + Shift + R`):**
  - Hangi uygulamada olursanız olun anında açılan Mac Spotlight / Raycast benzeri arama ve komut çubuğu.
  - İster yazarak ister bas-konuş (Push-to-Talk) mikrofonu ile fısıldayarak komut verme.
- 🎵 **YouTube Music Doğrudan Parça Entegrasyonu:**
  - *"YouTube Music'te Mor ve Ötesi çal"*, *"Arkaya lo-fi müzik aç"* dediğinizde en iyi parçayı bulup doğrudan tarayıcınızda başlatır.
- 🔌 **Uzaktan PC Açma (Wake-on-LAN) & Ağ Yönetimi:**
  - Bilgisayarın fiziksel Ethernet/Wi-Fi MAC adresini otomatik tespit eder ve yerel ağdaki cihazlara 102 baytlık sihirli paket (Magic Packet) gönderir.
- 🧠 **Derin Anlamsal Hafıza & Not Defteri (Semantic Memory):**
  - Bilinen kullanıcı tercihleri her komutta otomatik olarak sistem promptuna enjekte edilir.
  - Yapılandırılmış notlar ve fikirler saklanır (`save_note`, `search_notes`).
- 🤖 **Gerçek Masaüstü & Dosya Otomasyonu (Agent GUI):**
  - **Akıllı Klasör Düzenleyici:** İndirilenler klasöründeki dağınık dosyaları türlerine göre (`Resimler`, `Belgeler`, `Arşivler`, `Kurulumlar`) tek komutla toparlar.
  - **Çöp Kutusu Boşaltma:** Onay mekanizmasıyla Windows Geri Dönüşüm Kutusunu temizler.
  - **Pencere & Sekme Yönetimi:** Masaüstünü gösterme (Win+D), pencere kapatma (Alt+F4), büyütme/küçültme, sekme açma/kapatma/kurtarma.
- 🎙️ **Akıllı Donanım Mikrofon Tespiti (RMS Auto-Probe):**
  - Windows'un sessiz "Stereo Karışımı" tuzağını aşarak aktif harici kulaklık/mikrofonu otomatik seçer.
- 🔊 **Çevrimdışı Türkçe Nöral Ses (Local Piper ONNX):**
  - Bulut gecikmesi olmadan yerel çalışan ONNX tabanlı Türkçe nöral ses motoru (`tr_TR-fahrettin-medium` / `dfki`).
- 📱 **Siber Kokpit & Mobil Köprü (PWA + WebSockets):**
  - Telefondan dokunmayı takip eden HTML5 Canvas ASCII Siber Göz reaktörü.
  - Anlık CPU, RAM, Disk telemetrisi, canlı ekran görüntüsü akışı ve uzaktan kumanda.

---

## 🛠️ Mimari & Teknoloji Yığını

| Katman | Kullanılan Teknolojiler |
|---|---|
| **Yapay Zekâ Motoru** | Google Gemini 2.5 Flash / OmniRoute, Şema Tabanlı Tool Calling |
| **Ses Hattı** | PyAudio (RMS Probe), SpeechRecognition, Piper ONNX Neural TTS |
| **Masaüstü Arayüzü** | PyQt5 (Şeffaf HUD), Win32 API (`RegisterHotKey`, `user32`, `shell32`), PyCAW |
| **Mobil Köprü** | aiohttp, WebSockets, HTML5 Canvas Matrix Engine, PWA |
| **Veritabanı** | SQLite (İki katmanlı hafıza + not defteri) |
| **Paketleme** | PyInstaller (Early ONNX Hook), Inno Setup 6 |

---

## 📲 Mobil Erişim (PWA & Android)

Her kullanıcı kendi bilgisayarındaki RIFKI’ye bağlanır. Adres ve token elle girilmez; QR ile kolayca eşleştirilir.

**Kullanım:**
1. Bilgisayarda RIFKI’yi açın.
2. Tepsi simgesi → **Mobil bağlantı** → QR kodunu telefonunuzla tarayın:
   - Aynı Wi‑Fi ağı: Yerel LAN bağlantısı
   - Dış ağdan erişim: Dahili Cloudflare Tunnel desteği
3. Mobil arayüzden gerçek zamanlı donanım telemetrisini izleyebilir, sesli/yazılı komut verebilir ve masaüstünüzü yönetebilirsiniz.

---

## 💻 Kurulum (Windows)

### 1. Hazır Kurulum Dosyası (Setup.exe)
En son kararlı sürümü [GitHub Releases](https://github.com/BatuhanKlcky/rifki-voice-assistant/releases) sayfasından indirip tek tıkla kurabilirsiniz.

### 2. Geliştirici Kurulumu (Kaynak Koddan Çalıştırma)
1. Python 3.10+ kurulu olduğundan emin olun.
2. Sanal ortam oluşturun ve bağımlılıkları yükleyin:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. `.env` dosyasını yapılandırın:
   ```env
   OMNIROUTE_API_KEY=your_gemini_key_here
   OMNIROUTE_MODEL=antigravity/gemini-2.5-flash
   WAKE_WORD=rıfkı
   TTS_ENGINE=piper
   PIPER_VOICE=tr_TR-fahrettin-medium
   MOBILE_BRIDGE_ENABLED=true
   MOBILE_BRIDGE_TOKEN=585858
   ```
4. Uygulamayı başlatın:
   ```powershell
   python main.py
   ```

---

## ⌨️ Temel Kısayollar

- **`Ctrl + Space` veya `Ctrl + Shift + R`:** Spotlight Hızlı Komut Çubuğunu açar/kapatır.
- **`Esc`:** Açık olan Spotlight veya diyaloğu gizler.
- **`Enter`:** Komutu çalıştırır.

---

## 📄 Lisans

Bu proje kişisel ve açık kaynaklı geliştirme amacıyla hazırlanmıştır. Katkıda bulunmaktan veya geri bildirim vermekten çekinmeyin!
