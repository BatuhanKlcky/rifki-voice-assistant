## 🚀 RIFKI v2.6.4 — Ultra Hızlı & Senkron Siber Touchpad (Ballistics Engine) 🖱️⚡

### ⚡ Neler Yenilendi & Hızlandırıldı?
1. **Dinamik Touchpad İvmelenme Motoru (Ballistics Curve):**
   - Varsayılan hassasiyet `1.6x` yerine `2.4x` olarak optimize edildi.
   - Doğal fizik tabanlı hızlanma algoritması entegre edildi: Yavaş parmak hareketlerinde piksel piksel hassas seçim ve tıklama korunurken; normal ve hızlı parmak kaydırmalarında ivme dinamik olarak `2.8x` katına kadar katlanarak PC ekranını tek bir rahat parmak hareketiyle baştan başa akıcı şekilde kat etmenizi sağlar.
2. **rAF (RequestAnimationFrame) Ağ Senkronizasyonu:**
   - Touchpad mikro hareketleri ekran yenileme hızıyla (60Hz / 120Hz) senkronize edildi (`requestAnimationFrame`).
   - Saniyede 100+ gereksiz paket yerine konsolide edilmiş hareket vektörü iletilir, WebSocket ve WiFi hattındaki gecikme/jitter sıfıra indirildi.
3. **TCP_NODELAY Soket Optimizasyonu:**
   - Mobil köprü WebSocket bağlantısında Nagle algoritması devre dışı bırakıldı (`TCP_NODELAY = 1`). Küçük fare paketleri anında (0 ms bekleme) PC'ye ulaştırılır.
4. **Doğrudan Win32 Donanımsal Fare Girişi (`mouse_event`):**
   - Windows masaüstü çoklu monitör sınırları ve donanımsal imleç olayları tam uyumla, anında tepki verir.

---
### 📦 İndirme & Doğrulama
- **Dosya:** `RIFKI-Setup-2.6.4.exe`
- **SHA-256:** `BE008EEB26ABB7090859AC5DEAE93C01A5D72723AB8B6CCC955987B4B8F729DB`
