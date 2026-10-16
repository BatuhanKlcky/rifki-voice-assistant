# Google Play — yayın checklist (RIFKI mobil)

Paket: `com.rifki.assistant` · sürüm `2.1.0`  
AAB: [`mobile-android/RIFKI-mobile-release.aab`](../mobile-android/RIFKI-mobile-release.aab)

## Senin adımların (Play Console)

1. [Google Play Console](https://play.google.com/console) hesabı / geliştirici kaydı.
2. **Uygulama oluştur** → ad: RIFKI → dil: Türkçe → ücretsiz.
3. **Gizlilik politikası URL’si** (zorunlu):
   - [`privacy-tr.md`](privacy-tr.md) dosyasını GitHub Pages / kendi sitenizde yayınlayın.
   - İletişim satırını gerçek e-posta ile doldurun.
4. **Mağaza listesi** — metinler: [`play-listing-tr.md`](play-listing-tr.md)
   - Kısa / uzun açıklama
   - En az 2 telefon ekran görüntüsü (onboarding, QR, panel)
5. **Uygulama içeriği** → içerik derecesi anketi (Herkes; kamera: QR).
6. **Data safety** — özet tablosu `play-listing-tr.md` içinde.
7. **Production** → **Create new release** → AAB yükle → inceleme gönder.

## Teknik hazır (repoda)

- [x] `applicationId` = `com.rifki.assistant`
- [x] `targetSdk` 35, `versionName` 2.1.0
- [x] Release imza (keystore gitignore)
- [x] Kamera izni yalnızca QR
- [x] Gizlilik / listing taslakları

## Yeniden AAB

```powershell
cd mobile-android
.\build-release.ps1
```

## Masaüstü (Play’den ayrı)

Kullanıcılar PC’de RIFKI’yi **Setup.exe** ile kurar (`installer/build-setup.ps1`).
Telefondaki uygulama yalnızca kendi PC köprüsüne QR ile bağlanır.
