# Release imza

1. PowerShell: `.\create-keystore.ps1`
2. `keystore.properties` ve `.jks` dosyasını güvenli yere yedekleyin (git’e eklemeyin).
3. `..\gradlew.bat bundleRelease` → AAB: `app/build/outputs/bundle/release/app-release.aab`

Play Console’a yüklerken aynı keystore ile imzalamaya devam edin.
