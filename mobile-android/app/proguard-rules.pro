# RIFKI companion — keep WebView / ML Kit
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**
