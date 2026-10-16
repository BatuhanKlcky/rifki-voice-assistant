# Google Play — mağaza listesi taslağı (TR)

## Uygulama adı
RIFKI

## Kısa açıklama (80 karakter)
Bilgisayarındaki RIFKI asistanına QR ile bağlan; durum gör, komut yaz.

## Uzun açıklama

RIFKI mobil, masaüstündeki RIFKI sesli asistanına bağlanan companion uygulamadır.

Nasıl çalışır
1. Bilgisayarda RIFKI’yi açın.
2. Tepsi menüsünden «Mobil bağlantı»yı seçin.
3. Telefonda QR kodu tarayın.

Özellikler
- QR ile tek adımda eşleştirme (adres/token elle girilmez)
- Aynı Wi‑Fi veya uzak tünel üzerinden bağlantı
- Durum paneli ve metin komut
- Ses bilgisayardan çıkar; telefon panel görevi görür

Gereksinimler
- Windows’ta çalışan RIFKI masaüstü uygulaması
- Kamera izni (yalnızca QR okuma)

RIFKI bir bulut hesabı değildir; her kullanıcı kendi bilgisayarına bağlanır.

## Kategori
Üretkenlik / Araçlar

## İçerik derecelendirmesi
Herkes (kamera: QR kod)

## Data safety özeti (Play formu)

| Soru | Öneri |
|------|--------|
| Kullanıcı verisi toplanıyor mu? | Hayır (üçüncü tarafa / geliştiriciye toplanmaz) |
| Uygulama veriyi işler mi? | Evet — eşleştirme bilgisi cihazda; komutlar kullanıcının PC’sine |
| Kamera | QR tarama; kaydedilmez |
| Konum / kişiler / mikrofon | Hayır |
| Analitik / reklam | Hayır |
| Veri şifreleme | Transit: HTTPS (tünel); LAN’da HTTP mümkün |
| Hesap silme | «Bağlantıyı kaldır» + uygulamayı kaldır |

## Ekran görüntüsü notları

1. Onboarding: «Bilgisayarındaki RIFKI’ye bağlan» + QR tara
2. QR tarama ekranı
3. Bağlı panel (durum + komut)
4. (İsteğe bağlı) PC’deki Mobil bağlantı penceresi yan yana

Telefon: 1080×1920 veya Play’in istediği telefon boyutları.  
En az 2 telefon ekran görüntüsü zorunlu.

## Paket

- `applicationId`: `com.rifki.assistant`
- `versionName`: `2.1.0`
- Release AAB: `mobile-android/RIFKI-mobile-release.aab`
- Debug APK (yan test): `mobile-android/RIFKI-mobile-debug.apk`

## Gizlilik URL’si

`docs/privacy-tr.md` dosyasını herkese açık bir URL’de yayınlayıp Play’e yapıştırın.
