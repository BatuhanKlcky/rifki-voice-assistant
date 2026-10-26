package com.rifki.mobile

import android.content.Context
import android.net.Uri

object Prefs {
    private const val NAME = "rifki_mobile"
    private const val KEY_URL = "bridge_url"
    private const val KEY_TOKEN = "bridge_token"
    private const val KEY_ONBOARDED = "onboarded"
    private const val KEY_MAC = "target_mac"

    const val DEFAULT_MAC = "7C:8A:E1:AA:CA:F4"

    fun isPaired(context: Context): Boolean =
        getUrl(context).isNotEmpty() && getToken(context).isNotEmpty()

    fun isOnboarded(context: Context): Boolean =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_ONBOARDED, false)

    fun setOnboarded(context: Context, value: Boolean = true) {
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_ONBOARDED, value).apply()
    }

    fun getUrl(context: Context): String =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getString(KEY_URL, "")?.trim().orEmpty()

    fun getToken(context: Context): String =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getString(KEY_TOKEN, "")?.trim().orEmpty()

    fun getMac(context: Context): String =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getString(KEY_MAC, DEFAULT_MAC)?.trim().orEmpty().ifEmpty { DEFAULT_MAC }

    fun setMac(context: Context, mac: String) {
        if (mac.isBlank()) return
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .edit().putString(KEY_MAC, mac.trim().uppercase()).apply()
    }

    fun save(context: Context, url: String, token: String, mac: String? = null) {
        val editor = context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_URL, url.trim().trimEnd('/'))
            .putString(KEY_TOKEN, token.trim())
            .putBoolean(KEY_ONBOARDED, true)
        if (!mac.isNullOrBlank()) {
            editor.putString(KEY_MAC, mac.trim().uppercase())
        }
        editor.apply()
    }

    fun clearPairing(context: Context) {
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_URL)
            .remove(KEY_TOKEN)
            .apply()
    }

    fun buildPageUrl(context: Context): String? {
        val base = getUrl(context)
        val token = getToken(context)
        if (base.isEmpty() || token.isEmpty()) return null
        val sep = if (base.contains("?")) "&" else "?"
        return "$base$sep" + "token=" + Uri.encode(token)
    }

    /** rifki://pair?u=...&t=...&m=... */
    fun parsePairUri(raw: String, context: Context? = null): Pair<String, String>? {
        val uri = try {
            Uri.parse(raw.trim())
        } catch (_: Exception) {
            return null
        }
        if (uri.scheme != "rifki") return null
        if (uri.host != "pair" && uri.path != "/pair" && uri.path?.contains("pair") != true) {
            if (uri.host != "pair") return null
        }
        val url = uri.getQueryParameter("u")?.trim().orEmpty()
        val token = uri.getQueryParameter("t")?.trim().orEmpty()
        val mac = uri.getQueryParameter("m")?.trim().orEmpty()
        if (url.isEmpty() || token.isEmpty()) return null
        if (!url.startsWith("http://") && !url.startsWith("https://")) return null

        if (context != null && mac.isNotEmpty()) {
            setMac(context, mac)
        }
        return url to token
    }
}
