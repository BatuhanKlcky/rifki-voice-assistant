# RIFKI Mobil — Gizlilik Politikası

**Son güncelleme:** 16 Ekim 2026  
**Uygulama:** RIFKI (`com.rifki.assistant`)  
**İletişim:** Play Console’a koyacağınız e-posta / destek adresini buraya yazın
(ör. `destek@ornek.com`) — yayınlamadan önce güncelleyin.

## Özet

RIFKI mobil uygulaması, sizin bilgisayarınızda çalışan RIFKI masaüstü asistanına bağlanan bir uzaktan paneldir. Komutlar ve durum bilgisi **sizin bilgisayarınıza** gider; RIFKI’nin üçüncü taraf bir bulut hesabına veya merkezi bir sunucuya kullanıcı hesabı açılmaz.

## Toplanan veriler

| Veri | Neden | Nerede tutulur |
|------|--------|----------------|
| Köprü adresi ve eşleştirme jetonu | Telefondan PC köprüsüne bağlanmak | Yalnızca telefonda (uygulama tercihlerinde) |
| Kamera görüntüsü | QR kod okumak | Cihazda anlık işlenir; kaydedilmez, sunucuya gönderilmez |
| Yazdığınız komut metni | Bilgisayardaki RIFKI’ye iletmek | Bilgisayarınızdaki RIFKI’ye gider; mobil uygulama bunu kendi sunucusuna yüklemez |

## Toplanmayanlar

- Üçüncü taraf analitik / reklam SDK’sı yoktur.
- Konum, kişi listesi, mikrofon veya galeri kullanılmaz (kamera yalnızca QR tarama için istenir).
- RIFKI ekibine otomatik telemetri gönderilmez.

## Bağlantı modeli

1. Bilgisayarda RIFKI açılır; «Mobil bağlantı» ile QR üretilir.
2. Telefonda QR taranır; adres ve jeton telefona kaydedilir.
3. Aynı Wi‑Fi’de bağlantı doğrudan bilgisayarınıza (yerel ağ) olabilir.
4. Uzaktan erişimde bilgisayarınızdaki Cloudflare hızlı tüneli kullanılır; trafik yine sizin bilgisayarınızdaki köprüye ulaşır.

## Veri saklama ve silme

- Eşleştirmeyi kaldırmak: uygulamada **Bağlantıyı kaldır**.
- Uygulamayı kaldırmak: telefonda saklanan köprü bilgisi de silinir.
- Bilgisayardaki RIFKI günlükleri ve bellek, masaüstü uygulamanın kendi ayarlarına tabidir.

## Çocuklar

Uygulama genel kitle içindir; 13 yaş altı için özel bir hizmet sunulmaz.

## Değişiklikler

Bu metin güncellenebilir. Play Store’daki gizlilik URL’sini güncel tutun.

## Yayınlama notu

Play Console «Privacy policy» alanı için bu dosyayı GitHub Pages, kendi siteniz veya herkese açık bir URL’de yayınlayın.
