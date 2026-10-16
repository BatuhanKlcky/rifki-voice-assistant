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

  const params = new URLSearchParams(location.search);
  let token = params.get("token") || localStorage.getItem("rifki_bridge_token") || "";

  function setBadge(state) {
    const s = (state || "OFF").toLowerCase();
    badge.textContent = state || "OFF";
    badge.className = "badge " + (s || "off");
  }

  function appendMsg(role, text) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = "msg " + role;
    const who = document.createElement("div");
    who.className = "who";
    who.textContent = role === "user" ? "Sen" : role === "error" ? "Hata" : "RIFKI";
    const body = document.createElement("div");
    body.textContent = text;
    div.appendChild(who);
    div.appendChild(body);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function renderHistory(history) {
    logEl.innerHTML = "";
    (history || []).forEach((row) => appendMsg(row.role, row.text));
  }

  function applyStatus(data) {
    if (!data) return;
    setBadge(data.state);
    meta.textContent = data.listening
      ? "Ses bağlantısı açık · canlı"
      : "Ses bağlantısı kapalı / bekliyor";
    if (Array.isArray(data.history)) renderHistory(data.history);
  }

  function authHeaders() {
    return { Authorization: "Bearer " + token, "Content-Type": "application/json" };
  }

  async function fetchStatus() {
    const res = await fetch("/api/status?token=" + encodeURIComponent(token), {
      headers: authHeaders(),
    });
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
        if (data.type === "hello" || data.type === "status") {
          applyStatus(data);
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

  async function boot() {
    if (!token) {
      auth.classList.remove("hidden");
      meta.textContent = "Token gerekli";
      return;
    }
    auth.classList.add("hidden");
    try {
      const data = await fetchStatus();
      applyStatus(data);
      connectWs();
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

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = (cmd.value || "").trim();
    if (!text || !token) return;
    send.disabled = true;
    appendMsg("user", text);
    cmd.value = "";
    try {
      const res = await fetch("/api/command?token=" + encodeURIComponent(token), {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMsg("error", data.error || "Komut başarısız");
      } else if (data.reply) {
        // WebSocket genelde zaten ekler; yoksa burada göster
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
