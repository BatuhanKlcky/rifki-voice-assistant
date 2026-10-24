(() => {
  const badge = document.getElementById("badge");
  const meta = document.getElementById("meta");
  const logEl = document.getElementById("log");
  const auth = document.getElementById("auth");
  const tokenInput = document.getElementById("token");
  const saveToken = document.getElementById("saveToken");
  const form = document.getElementById("cmdForm");
  const cmd = document.getElementById("cmd");
  const send = document.getElementById("send");
  const btnShot = document.getElementById("btnShot");
  const btnApps = document.getElementById("btnApps");
  const appsPanel = document.getElementById("appsPanel");
  const appsClose = document.getElementById("appsClose");
  const appSearch = document.getElementById("appSearch");
  const appsList = document.getElementById("appsList");
  const appsMeta = document.getElementById("appsMeta");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxClose = document.getElementById("lightboxClose");
  const volPill = document.getElementById("volPill");
  const remoteGrid = document.getElementById("remoteGrid");
  const urlForm = document.getElementById("urlForm");
  const urlInput = document.getElementById("urlInput");
  const liveImg = document.getElementById("liveImg");
  const liveEmpty = document.getElementById("liveEmpty");
  const btnLiveToggle = document.getElementById("btnLiveToggle");
  const btnLiveRefresh = document.getElementById("btnLiveRefresh");

  const params = new URLSearchParams(location.search);
  let token = params.get("token") || localStorage.getItem("rifki_bridge_token") || "";
  let appsCache = [];
  let searchTimer = null;
  let liveTimer = null;
  let liveOn = false;
  let liveBlobUrl = null;
  const shotBlobUrls = [];
  const MAX_SHOT_BLOBS = 5;
  const LIVE_INTERVAL_MS = 2500;

  function trackShotBlob(url) {
    shotBlobUrls.push(url);
    while (shotBlobUrls.length > MAX_SHOT_BLOBS) {
      const old = shotBlobUrls.shift();
      try { URL.revokeObjectURL(old); } catch (_) {}
    }
  }

  function clock() {
    const d = new Date();
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }

  function setBadge(state) {
    const raw = state || "OFF";
    const s = raw.toLowerCase();
    badge.className = "badge " + (s || "off");
    badge.innerHTML = '<span class="dot"></span><span class="label"></span>';
    badge.querySelector(".label").textContent = raw;
  }

  function appendMsg(role, text) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = "msg " + role;

    const head = document.createElement("div");
    head.className = "msg-head";
    if (role === "assistant") {
      const av = document.createElement("span");
      av.className = "avatar";
      av.innerHTML =
        '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="3.5"/><path d="M5 19c1.8-3 4-4.5 7-4.5S17.2 16 19 19"/></svg>';
      head.appendChild(av);
    }
    const who = document.createElement("span");
    who.textContent = role === "user" ? "Sen" : role === "error" ? "Hata" : "Asistan";
    head.appendChild(who);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    const body = document.createElement("div");
    body.className = "body";
    body.textContent = text;
    const time = document.createElement("div");
    time.className = "time";
    time.textContent = clock();
    bubble.appendChild(body);
    bubble.appendChild(time);

    div.appendChild(head);
    div.appendChild(bubble);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function appendImage(blobUrl) {
    const div = document.createElement("div");
    div.className = "msg assistant shot";
    const head = document.createElement("div");
    head.className = "msg-head";
    const av = document.createElement("span");
    av.className = "avatar";
    av.innerHTML =
      '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="3.5"/><path d="M5 19c1.8-3 4-4.5 7-4.5S17.2 16 19 19"/></svg>';
    head.appendChild(av);
    const who = document.createElement("span");
    who.textContent = "Ekran";
    head.appendChild(who);
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    const img = document.createElement("img");
    img.src = blobUrl;
    img.alt = "PC ekran görüntüsü";
    img.loading = "lazy";
    img.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openLightbox(blobUrl);
    });
    const time = document.createElement("div");
    time.className = "time";
    time.textContent = clock();
    bubble.appendChild(img);
    bubble.appendChild(time);
    div.appendChild(head);
    div.appendChild(bubble);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function openLightbox(src) {
    if (!lightbox || !lightboxImg || !src) return;
    lightboxImg.src = src;
    lightbox.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    if (!lightbox || !lightboxImg) return;
    lightbox.classList.add("hidden");
    lightboxImg.removeAttribute("src");
    document.body.style.overflow = "";
  }

  function renderHistory(history) {
    logEl.innerHTML = "";
    (history || []).forEach((row) => appendMsg(row.role, row.text));
  }

  function applyStatus(data, replaceHistory) {
    if (!data) return;
    setBadge(data.state);
    meta.textContent = data.listening
      ? "Ses bağlantısı açık · canlı"
      : "Ses bağlantısı kapalı / bekliyor";
    // Tam geçmiş yalnızca ilk hello / boot'ta — yoksa ekran görüntüsü silinir
    if (replaceHistory && Array.isArray(data.history)) renderHistory(data.history);
  }

  function authHeaders(json) {
    const h = { Authorization: "Bearer " + token };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  function apiUrl(path, extra) {
    const u = new URL(path, location.origin);
    u.searchParams.set("token", token);
    if (extra) {
      Object.keys(extra).forEach((k) => {
        if (extra[k] != null && extra[k] !== "") u.searchParams.set(k, extra[k]);
      });
    }
    return u.toString();
  }

  async function fetchStatus() {
    const res = await fetch(apiUrl("/api/status"), { headers: authHeaders() });
    if (res.status === 401) throw new Error("yetkisiz");
    if (!res.ok) throw new Error("durum alınamadı");
    return res.json();
  }

  let ws;
  function connectWs() {
    if (ws) {
      try { ws.close(); } catch (_) {}
    }
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(
      proto + "//" + location.host + "/ws?token=" + encodeURIComponent(token)
    );
    ws.onopen = () => {
      meta.textContent = "Canlı bağlantı açık";
    };
    ws.onclose = () => {
      meta.textContent = "Canlı bağlantı koptu · yeniden denenecek";
      setTimeout(connectWs, 2500);
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "hello") {
          applyStatus(data, true);
        } else if (data.type === "status") {
          applyStatus(data, false);
        } else if (data.type === "user") {
          appendMsg("user", data.text);
          setBadge(data.state);
        } else if (data.type === "assistant") {
          appendMsg("assistant", data.text);
          setBadge(data.state);
        } else if (data.type === "error") {
          appendMsg("error", data.text);
        }
      } catch (_) {}
    };
  }

  async function takeScreenshot() {
    if (!token) return;
    btnShot.disabled = true;
    const oldLabel = btnShot.innerHTML;
    btnShot.textContent = "Alınıyor…";
    appendMsg("user", "Ekran görüntüsü al");
    try {
      const res = await fetch(apiUrl("/api/screenshot"), {
        headers: authHeaders(),
        cache: "no-store",
      });
      if (res.status === 401) throw new Error("yetkisiz — yeniden eşleştir");
      if (res.status === 404) {
        throw new Error("PC'de eski RIFKI açık. baslat-rifki.bat ile kaynaktan yeniden başlat.");
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || ("sunucu " + res.status));
      }
      const ctype = (res.headers.get("content-type") || "").toLowerCase();
      if (!ctype.includes("image")) {
        throw new Error("beklenmeyen yanıt (PNG gelmedi)");
      }
      const blob = await res.blob();
      if (!blob || blob.size < 100) throw new Error("boş görüntü");
      const url = URL.createObjectURL(blob);
      trackShotBlob(url);
      appendImage(url);
    } catch (e) {
      appendMsg("error", "Ekran görüntüsü: " + (e.message || "hata"));
    } finally {
      btnShot.disabled = false;
      btnShot.innerHTML = oldLabel;
    }
  }

  function renderApps(apps) {
    appsList.innerHTML = "";
    if (!apps.length) {
      appsMeta.textContent = "Uygulama bulunamadı";
      return;
    }
    appsMeta.textContent = apps.length + " uygulama";
    apps.forEach((app) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "app-item";
      btn.textContent = app.name;
      btn.addEventListener("click", () => launchApp(app.name, btn));
      li.appendChild(btn);
      appsList.appendChild(li);
    });
  }

  async function loadApps(q) {
    if (!token) return;
    appsMeta.textContent = "Yükleniyor…";
    try {
      const res = await fetch(apiUrl("/api/apps", { q: q || "", limit: "500" }), {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("liste alınamadı");
      const data = await res.json();
      appsCache = data.apps || [];
      renderApps(appsCache);
    } catch (e) {
      appsMeta.textContent = e.message || "Hata";
    }
  }

  async function launchApp(name, btn) {
    if (!token || !name) return;
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(apiUrl("/api/apps/launch"), {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMsg("error", data.error || "Açılamadı");
      } else {
        // WS genelde ekler; yine de anlık geri bildirim
        if (data.reply) appendMsg("assistant", data.reply);
      }
    } catch (_) {
      appendMsg("error", "Uygulama açılamadı (ağ)");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function openAppsPanel() {
    appsPanel.classList.remove("hidden");
    loadApps(appSearch.value.trim());
    appSearch.focus();
  }

  function closeAppsPanel() {
    appsPanel.classList.add("hidden");
  }

  function setVolPill(volume) {
    if (!volPill || !volume) return;
    if (volume.level == null) {
      volPill.textContent = "Ses —";
      return;
    }
    volPill.textContent = volume.muted
      ? "Sessiz"
      : "Ses %" + volume.level;
  }

  async function refreshVolume() {
    if (!token) return;
    try {
      const res = await fetch(apiUrl("/api/volume"), { headers: authHeaders() });
      if (!res.ok) return;
      setVolPill(await res.json());
    } catch (_) {}
  }

  async function remoteAction(action, extra) {
    if (!token || !action) return;
    const body = Object.assign({ action: action }, extra || {});
    try {
      const res = await fetch(apiUrl("/api/remote"), {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) {
        appendMsg("error", data.error || ("İşlem başarısız: " + action));
        return;
      }
      if (data.volume) setVolPill(data.volume);
      if (data.reply && ["lock", "sleep", "shutdown", "restart", "open_url", "cancel_shutdown"].indexOf(action) >= 0) {
        // sunucu WS ile de basabilir; yine de anında göster
      }
    } catch (_) {
      appendMsg("error", "Uzaktan komut ağ hatası");
    }
  }

  function bindRemoteButtons(root) {
    if (!root) return;
    root.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.getAttribute("data-action");
        const confirmMsg = btn.getAttribute("data-confirm");
        if (confirmMsg && !window.confirm(confirmMsg)) return;
        btn.disabled = true;
        try {
          await remoteAction(action, confirmMsg ? { confirm: true } : {});
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  async function fetchLiveFrame() {
    if (!token) return;
    try {
      const res = await fetch(apiUrl("/api/screenshot", { live: "1", w: "960", q: "55" }), {
        headers: authHeaders(),
        cache: "no-store",
      });
      if (!res.ok) throw new Error("ekran alınamadı");
      const blob = await res.blob();
      if (!blob || blob.size < 100) throw new Error("boş");
      const url = URL.createObjectURL(blob);
      if (liveBlobUrl) {
        try { URL.revokeObjectURL(liveBlobUrl); } catch (_) {}
      }
      liveBlobUrl = url;
      if (liveImg) {
        liveImg.hidden = false;
        liveImg.src = url;
      }
      if (liveEmpty) liveEmpty.classList.add("hidden");
    } catch (e) {
      if (!liveOn && liveEmpty) {
        liveEmpty.classList.remove("hidden");
        liveEmpty.textContent = "Ekran alınamadı";
      }
    }
  }

  function setLive(on) {
    liveOn = !!on;
    if (btnLiveToggle) {
      btnLiveToggle.textContent = liveOn ? "Canlı: açık" : "Canlı: kapalı";
      btnLiveToggle.classList.toggle("active", liveOn);
    }
    if (liveTimer) {
      clearInterval(liveTimer);
      liveTimer = null;
    }
    if (liveOn) {
      fetchLiveFrame();
      liveTimer = setInterval(fetchLiveFrame, LIVE_INTERVAL_MS);
    }
  }

  async function boot() {
    if (!token) {
      auth.classList.remove("hidden");
      meta.textContent = "Token gerekli";
      return;
    }
    auth.classList.add("hidden");
    try {
      const data = await fetchStatus();
      applyStatus(data, true);
      connectWs();
      refreshVolume();
    } catch (e) {
      auth.classList.remove("hidden");
      meta.textContent = "Token reddedildi veya köprü kapalı";
      setBadge("OFF");
    }
  }

  saveToken.addEventListener("click", () => {
    token = (tokenInput.value || "").trim();
    if (!token) return;
    localStorage.setItem("rifki_bridge_token", token);
    boot();
  });

  btnShot.addEventListener("click", takeScreenshot);
  btnApps.addEventListener("click", openAppsPanel);
  appsClose.addEventListener("click", closeAppsPanel);
  bindRemoteButtons(remoteGrid);
  bindRemoteButtons(document.querySelector(".remote-row"));
  if (urlForm) {
    urlForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const url = (urlInput && urlInput.value || "").trim();
      if (!url) return;
      await remoteAction("open_url", { url: url });
      if (urlInput) urlInput.value = "";
    });
  }
  if (btnLiveToggle) {
    btnLiveToggle.addEventListener("click", () => setLive(!liveOn));
  }
  if (btnLiveRefresh) {
    btnLiveRefresh.addEventListener("click", () => fetchLiveFrame());
  }
  if (liveImg) {
    liveImg.addEventListener("click", () => {
      if (liveBlobUrl) openLightbox(liveBlobUrl);
    });
  }
  if (lightboxClose) lightboxClose.addEventListener("click", (e) => {
    e.stopPropagation();
    closeLightbox();
  });
  if (lightbox) lightbox.addEventListener("click", closeLightbox);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });
  appSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadApps(appSearch.value.trim()), 250);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && liveOn) {
      if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
    } else if (!document.hidden && liveOn && !liveTimer) {
      liveTimer = setInterval(fetchLiveFrame, LIVE_INTERVAL_MS);
      fetchLiveFrame();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = (cmd.value || "").trim();
    if (!text || !token) return;
    send.disabled = true;
    appendMsg("user", text);
    cmd.value = "";
    try {
      const res = await fetch(apiUrl("/api/command"), {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMsg("error", data.error || "Komut başarısız");
      } else if (data.reply) {
        if (!data.history) appendMsg("assistant", data.reply);
        applyStatus(data);
      }
    } catch (err) {
      appendMsg("error", "Ağ hatası");
    } finally {
      send.disabled = false;
      cmd.focus();
    }
  });

  if (token) tokenInput.value = token;
  boot();
})();
