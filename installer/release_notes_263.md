## RIFKI v2.6.3 — Kusursuz Canlı Touchpad & Bağımsız Ultra Düşük Gecikmeli Ekran Akışı 🚀🖱️

### 🖱️ Touchpad & Fare Kontrolü Tamamen Yenilendi
- **Win32 Giriş Masaüstü Entegrasyonu (`_ensure_input_desktop`):** Arka plan iş parçacıkları ve WebSocket olay döngüsü interaktif Windows masaüstüne (`OpenInputDesktop` + `SetThreadDesktop`) otomatik bağlanarak imleç koordinatlarının `(0, 0)`'a kilitlenmesi veya erişim engeli (Access Denied / Error 5) yaşaması kökten çözüldü.
- **W3C Pointer Events & Pointer Capture:** Mobil cihazlarda (iOS Safari & Android Chrome) parmak touchpad sınırının dışına taşsa dahi `setPointerCapture` ile sürükleme ve tıklama kesintisiz şekilde takip ediliyor.
- **Doğrudan Donanım İmleç Konumlandırması (`SetCursorPos`):** Ekran koordinatları sınır kontrolüyle (`max/min`) anlık ve sıfır gecikmeyle donanım seviyesinde güncellenir.
- **Hassas Tıklama & Dokunuş Tespiti:** Hafif tek dokunuşta Sol Tık, iki parmaklı dokunuşta Sağ Tık; kaydırma butonları ve çift tık tam uyumlu çalışır.

### ⚡ Bağımsız Ekran Akış Kuyruğu (Zero-Starvation WebSocket)
- Ekran görüntüsü aktarımı bağımsız bir `asyncio.Queue(maxsize=1)` arka plan çalışanına (`_screen_worker`) devredildi.
- Turbo modda (Ultra Canlı Ekran) ekran kareleri saniyede 35+ FPS hızla akarken; mobil cihazdan gelen fare hareketi (`mouse_move`), tıklama (`mouse_click`) ve kaydırma (`mouse_scroll`) komutları WebSocket mesaj döngüsünde 0 ms gecikmeyle derhal işlenir, fare asla kilitlenmez veya lag yapmaz.

### 📦 Kurulum ve Dağıtım
- `RIFKI-Setup-2.6.3.exe` bağımsız Inno Setup yükleyicisi hazırlandı ve SHA-256 doğrulama özeti sağlandı.
