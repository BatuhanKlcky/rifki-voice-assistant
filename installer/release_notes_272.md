# RIFKI v2.7.2 — Mobil Bağlantı & QR Penceresi Kapatma Düzeltmesi

## 🛠️ Hata Düzeltmeleri ve Arayüz İyileştirmeleri

1. **Mobil Bağlantı Penceresi Çarpı (X) Kapatma Sorunu Çözüldü:**
   - «Mobil bağlantı» (QR kod) penceresi açıldığında, başlık çubuğundaki Windows standart kapatma (X) butonuna tıklandığında pencerenin kapanmaması sorunu giderildi (`super().closeEvent()` ve doğrudan `self.hide()` entegrasyonu sağlandı).
   - Klavyeden `Esc` tuşuna basıldığında pencerenin anında kapanması için `reject()` metodu eklendi.

2. **Arayüz İçi Hızlı Kapatma Butonları:**
   - Kartın sağ üst köşesine özel `✕` kapatma butonu eklendi.
   - Kartın alt kısmına belirgin `✕ Pencereyi Kapat` butonu yerleştirilerek kullanıcı deneyimi artırıldı.

---

## 📦 Kurulum Dosyası
- **Dosya:** RIFKI-Setup-2.7.2.exe
- **SHA-256:** `0AFF31C7964F74996222FD8400EC91CC7888996A72015BD61CB02B80F8797E9B`
