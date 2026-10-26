package com.rifki.mobile

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.net.wifi.WifiManager
import android.os.Bundle
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.PopupMenu
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var progress: ProgressBar
    private lateinit var offlineLayout: LinearLayout

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Prefs.isPaired(this)) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        progress = findViewById(R.id.progress)
        offlineLayout = findViewById(R.id.offlineLayout)
        webView.setBackgroundColor(Color.parseColor("#02060C"))

        findViewById<Button>(R.id.btnWakePc).setOnClickListener {
            triggerWakeOnLan()
        }
        findViewById<Button>(R.id.btnRetryConnect).setOnClickListener {
            offlineLayout.visibility = View.GONE
            loadBridge()
        }

        // Request Audio Permission for Voice Input in Web Panel
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                101
            )
        }

        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        settings.mediaPlaybackRequiresUserGesture = false

        // Bridge for Web Panel JavaScript to call native Wake-on-LAN directly
        webView.addJavascriptInterface(AndroidBridge(), "AndroidBridge")

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility =
                    if (newProgress in 1..99) View.VISIBLE else View.GONE
            }

            override fun onPermissionRequest(request: PermissionRequest?) {
                runOnUiThread {
                    request?.grant(request.resources)
                }
            }
        }
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean = false

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                progress.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                progress.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    offlineLayout.visibility = View.VISIBLE
                }
            }
        }

        findViewById<ImageButton>(R.id.btnMenu).setOnClickListener { anchor ->
            val popup = PopupMenu(this, anchor)
            popup.menuInflater.inflate(R.menu.main_menu, popup.menu)
            popup.setOnMenuItemClickListener { item -> handleMenu(item.itemId) }
            popup.show()
        }

        loadBridge()
    }

    private fun loadBridge() {
        val page = Prefs.buildPageUrl(this)
        if (page == null) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        offlineLayout.visibility = View.GONE
        webView.loadUrl(page)
    }

    fun triggerWakeOnLan(macToWake: String? = null) {
        val mac = if (!macToWake.isNullOrBlank()) macToWake else Prefs.getMac(this)
        Toast.makeText(this, "Uyandırma paketi gönderiliyor ($mac)...", Toast.LENGTH_SHORT).show()
        
        thread {
            var lock: WifiManager.MulticastLock? = null
            try {
                val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                lock = wifi?.createMulticastLock("rifki_wol_lock")
                lock?.acquire()

                sendWakeOnLan(mac)

                runOnUiThread {
                    Toast.makeText(
                        this@MainActivity,
                        "⚡ Sihirli Paket gönderildi! Bilgisayar açılıyor...",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(
                        this@MainActivity,
                        "WoL Hatası: ${e.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } finally {
                try {
                    lock?.release()
                } catch (_: Exception) {}
            }
        }
    }

    private fun handleMenu(id: Int): Boolean {
        return when (id) {
            R.id.action_wake -> {
                triggerWakeOnLan()
                true
            }
            R.id.action_reload -> {
                loadBridge()
                true
            }
            R.id.action_repair -> {
                startActivity(Intent(this, ScanActivity::class.java))
                true
            }
            R.id.action_unpair -> {
                AlertDialog.Builder(this)
                    .setTitle(R.string.unpair_title)
                    .setMessage(R.string.unpair_msg)
                    .setPositiveButton(R.string.unpair) { _, _ ->
                        Prefs.clearPairing(this@MainActivity)
                        startActivity(Intent(this@MainActivity, OnboardingActivity::class.java))
                        finish()
                    }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
                true
            }
            else -> false
        }
    }

    inner class AndroidBridge {
        @JavascriptInterface
        fun wakePc(mac: String? = null) {
            runOnUiThread {
                triggerWakeOnLan(mac)
            }
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    companion object {
        fun sendWakeOnLan(macAddress: String) {
            val clean = macAddress.replace(":", "").replace("-", "")
            if (clean.length != 12) {
                throw IllegalArgumentException("Geçersiz MAC adresi: $macAddress")
            }
            val macBytes = ByteArray(6)
            for (i in 0 until 6) {
                macBytes[i] = clean.substring(i * 2, i * 2 + 2).toInt(16).toByte()
            }
            val bytes = ByteArray(6 + 16 * macBytes.size)
            for (i in 0 until 6) {
                bytes[i] = 0xff.toByte()
            }
            var idx = 6
            for (i in 0 until 16) {
                System.arraycopy(macBytes, 0, bytes, idx, macBytes.size)
                idx += macBytes.size
            }

            val socket = DatagramSocket()
            socket.broadcast = true
            val broadcastIp = InetAddress.getByName("255.255.255.255")
            // Send to both standard WoL ports: 9 and 7
            val p9 = DatagramPacket(bytes, bytes.size, broadcastIp, 9)
            val p7 = DatagramPacket(bytes, bytes.size, broadcastIp, 7)
            socket.send(p9)
            socket.send(p7)
            socket.close()
        }
    }
}
