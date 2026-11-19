# RIFKI v2.7.1 — WebRTC H.264 Tam Entegrasyon & Mobil Autoplay Düzeltmesi

## 🚀 WebRTC ve Canlı Ekran Güncellemeleri

1. **One-Shot ICE Candidate Gathering (WebRTC Bağlantı Çözümü):**
   - WebRTC SDP el sıkışması sırasında hem sunucu (`aiortc`) hem de istemci tarafında ICE adaylarının toplanması (`iceGatheringState == "complete"`) beklenerek tam aday listeli SDP üretildi.
   - Böylece NAT ve yerel ağ arkasındaki telefonlar ile masaüstü arasında ICE bağlantısı sıfır paket kaybıyla anında kuruluyor.

2. **Mobil Cihazlar için Otomatik Oynatma (Autoplay & Playsinline):**
   - iOS Safari ve Android Chrome tarayıcılarının video akışını duraklatmasını engellemek için `<video>` bileşeni `muted=true`, `playsInline=true` olarak yapılandırıldı ve akış geldiğinde `play()` programatik olarak tetiklendi.

3. **Garantili ve Kesintisiz Canlı Yayın (Turbo WS Varsayılan):**
   - Varsayılan canlı yayın modu **⚡ Turbo WS (Canlı)** olarak ayarlandı. Bu sayede sayfa açıldığı anda sıfır gecikmeli masaüstü akışı hazır bulunur.
   - Dileyen kullanıcılar tek tıkla **🚀 WebRTC H.264** moduna geçiş yapabilir; bağlantı koparsa sistem otomatik olarak Turbo WS moduna geri düşer.

---

## 📦 Kurulum Dosyası
- **Dosya:** RIFKI-Setup-2.7.1.exe
- **SHA-256:** `A5B70A33A86DD94EC6EEEAB8070A5A81D6CBB02266FB88676BFD1CC493CA6B6E`
