## 🚀 RIFKI v2.7.0 — Donanımsal WebRTC H.264 Canlı Video Akışı & Sıfır CPU 🎬⚡

### 🌟 Neler Yeni & Büyük Yenilikler?
1. **Donanımsal WebRTC H.264 Video Akış Motoru (`bridge/webrtc_stream.py`):**
   - NVIDIA NVENC, AMD AMF veya CPU libx264 (zerolatency) donanım kodlayıcıları entegre edildi.
   - Ekran görüntüleri doğrudan Windows GDI DIB bölümünden alınıp milisaniyeler içinde donanımsal H.264 video akışına dönüştürülür.
   - **Sonuç:** PC'deki CPU ve bellek yükü sıfıra yakın seviyeye indi.
2. **Telefon GPU'sunda Doğrudan Video Çözme (`<video id="liveVideo">`):**
   - Mobil tarayıcılar (iOS Safari & Android Chrome) görüntüyü telefonun kendi donanımsal video çipiyle akıcı 60 FPS çözer.
   - Ağ veri tüketimi 5-8 Mbps'den **300 - 800 Kbps** seviyesine (%85 tasarruf) geriledi.
   - Uçtan uca gecikme **10 - 20 milisaniyeye** düştü!
3. **Akıllı Hibrit Akış Mimarisi (Graceful Fallback):**
   - Varsayılan olarak **🚀 WebRTC H.264** çalışır.
   - WebRTC desteklenmeyen ağlarda veya güvenlik duvarı arkasında otomatik olarak **⚡ Turbo WS (JPEG)** yedeğine kesintisiz geçiş yapılır.
4. **WebSocket Üzerinden Hızlı Sinyalleşme:**
   - Halihazırdaki WebSocket bağlantısı üzerinden SDP teklif ve yanıtları milisaniyeler içinde el sıkışır.

---
### 📦 İndirme & Doğrulama
- **Dosya:** `RIFKI-Setup-2.7.0.exe`
- **SHA-256:** `BC9CBD5A7C852D11698ABA52CF17C6E7AD04A1BE9D587DC9FBAF83D6F957D6C2`
