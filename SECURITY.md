# Güvenlik Politikası (Security Policy)

## Desteklenen Sürümler

Aşağıdaki sürümler aktif olarak güvenlik güncellemeleri almaktadır:

| Sürüm | Destek Durumu |
| ------- | ------------------ |
| 2.5.x   | :white_check_mark: Destekleniyor |
| < 2.5.0 | :x: Desteklenmiyor (`v2.5.0+` sürümüne güncelleyin) |

## Güvenlik Mimarisi Özeti

- **Gizli Anahtarlar (.env):** API anahtarları ve mobil köprü erişim tokenleri yalnızca yerel `.env` dosyasında tutulur; hiçbir koşulda buluta veya depoya gönderilmez.
- **Mobil Köprü Doğrulaması:** Mobil web paneli ve Android uygulaması, 144-bit kriptografik token (`secrets.token_urlsafe(18)`), zamanlama saldırısına dayanıklı karşılaştırma (`secrets.compare_digest`), `Authorization: Bearer` başlığı ve IP bazlı Brute-Force / Rate-Limit koruması kullanır.
- **Dosya Sistemi Koruması:** Yapay zekâ dosya araçları sistem klasörlerine (`Windows`, `Program Files`, `AppData`), gizli anahtar dizinlerine (`.ssh`, `.git`) ve R.I.F.K.I'nin kendi uygulama dosyalarına müdahale edemez; kritik işlemler (silme, taşıma, çöp kutusu boşaltma, kapatma) açık kullanıcı onayı gerektirir.
- **Otomatik Güncelleyici Doğrulaması:** İndirilen güncelleme paketleri (`RIFKI-Setup-x.y.z.exe`) yalnızca resmi GitHub Releases HTTPS kaynağından kabul edilir, PE başlığı ve SHA-256 bütünlük kontrolünden geçirilir.

## Güvenlik Açığı Bildirimi

Bir güvenlik açığı tespit ederseniz lütfen herkese açık bir Issue açmak yerine doğrudan depo sahibiyle ([BatuhanKlcky](https://github.com/BatuhanKlcky)) iletişime geçin. Bildiriminiz en geç 48 saat içinde incelenecektir.
