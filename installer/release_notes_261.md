## ⚡ RIFKI v2.6.1 — Ultra Canlı Düşük Gecikmeli Ekran Yayını & Gerçek Zamanlı FPS

### 🚀 Yenilikler & İyileştirmeler
1. **Ultra Canlı Ekran Yayını (Minimum Gecikme ~50ms, ~20 FPS):**
   - Eski 2.5 saniyelik sabit gecikmeli HTTP yenileme kaldırıldı.
   - Yerine tarayıcı ile RIFKI arasında sıfır yığılmalı, anlık dinamik ardışık çerçeve motoru (**Adaptive Self-Pacing Frame Loop**) entegre edildi.
   - Resampling algoritması hızlı **Bilinear** motoruna geçirildi, JPEG optimize yükü devre dışı bırakıldı ve görüntü yakalama süresi ~50ms'ye indirildi.
2. **Sıfır Bellek Sızıntısı (Zero Memory Leak):**
   - Mobil tarayıcıda belleğin şişmesini önlemek için her yeni ekran çerçevesi geldikten hemen sonra eski blob nesnesi anında serbest bırakılır (`URL.revokeObjectURL`).
3. **Canlı Akış Modları (Mod Seçici):**
   - ⚡ **Ultra Canlı:** ~20 FPS, 50ms gecikme — Tam canlı gibi akıcı ekran ve fare takibi!
   - 🎯 **Dengeli:** ~12 FPS, 75ms gecikme — Dengeli hız ve çözünürlük
   - 💎 **HD Detay:** ~4 FPS, yüksek çözünürlük — Net ekran okuma
4. **Gerçek Zamanlı Telemetri Rozeti:**
   - Ekranın üzerinde anlık yenileme hızını ve gecikmeyi gösteren canlı rozet eklendi (`⚡ 18 FPS · 52ms`).
5. **Mouse İmleci Overlay:**
   - Canlı ekran akışı üzerinde donanımsal fare imleci yüksek kontrastlı sibernetik ok olarak canlı görüntüye eklenir.

---
### 📦 İndirme & Doğrulama
- **Dosya:** `RIFKI-Setup-2.6.1.exe`
- **SHA-256:** `79E337F79553BECCD3DBA77A170BD73B24D6C806A77D0AE032942548E7B6569A`
