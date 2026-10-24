/**
 * RIFKI Siber Kokpit — Mobil İstemci & ASCII Siber Göz Motoru
 */
(() => {
  // DOM Elements
  const badge = document.getElementById("badge");
  const meta = document.getElementById("meta");
  const logEl = document.getElementById("log");
  const auth = document.getElementById("auth");
  const tokenInput = document.getElementById("token");
  const saveToken = document.getElementById("saveToken");
  const form = document.getElementById("cmdForm");
  const cmd = document.getElementById("cmd");
  const send = document.getElementById("send");
  const btnMic = document.getElementById("btnMic");
  const btnTtsToggle = document.getElementById("btnTtsToggle");
  const eyeCanvas = document.getElementById("eyeCanvas");
  const eyeStatus = document.getElementById("eyeStatus");
  const fpsTag = document.getElementById("fpsTag");

  // Telemetry elements
  const cpuVal = document.getElementById("cpuVal");
  const cpuBar = document.getElementById("cpuBar");
  const ramVal = document.getElementById("ramVal");
  const ramBar = document.getElementById("ramBar");
  const diskVal = document.getElementById("diskVal");
  const diskBar = document.getElementById("diskBar");
  const batVal = document.getElementById("batVal");
  const clockVal = document.getElementById("clockVal");

  // Remote elements
  const volPill = document.getElementById("volPill");
  const volSlider = document.getElementById("volSlider");
  const volSliderVal = document.getElementById("volSliderVal");
  const btnMuteToggle = document.getElementById("btnMuteToggle");
  const btnShotDirect = document.getElementById("btnShotDirect");
  const clipInput = document.getElementById("clipInput");
  const btnSendClipboard = document.getElementById("btnSendClipboard");
  const btnTypeToPc = document.getElementById("btnTypeToPc");
  const btnGetClipboard = document.getElementById("btnGetClipboard");
  const urlForm = document.getElementById("urlForm");
  const urlInput = document.getElementById("urlInput");
  const btnSearchGoogle = document.getElementById("btnSearchGoogle");
  const btnSearchYoutube = document.getElementById("btnSearchYoutube");

  // Apps & Vision elements
  const appSearch = document.getElementById("appSearch");
  const appsList = document.getElementById("appsList");
  const appsMeta = document.getElementById("appsMeta");
  const liveImg = document.getElementById("liveImg");
  const liveEmpty = document.getElementById("liveEmpty");
  const btnLiveToggle = document.getElementById("btnLiveToggle");
  const btnLiveRefresh = document.getElementById("btnLiveRefresh");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxClose = document.getElementById("lightboxClose");

  // State & Config
  const params = new URLSearchParams(location.search);
  let token = params.get("token") || localStorage.getItem("rifki_bridge_token") || "";
  let currentState = "OFF";
  let ttsEnabled = true;
  let ws = null;
  let wsReconnectTimer = null;
  let telemTimer = null;
  let liveTimer = null;
  let liveOn = false;
  let appsCache = [];
  let isMuted = false;

  // =========================================================================
  // 1. ASCII SİBER GÖZ & MATRİS RENDER MOTORU (HTML5 Canvas)
  // =========================================================================
  const RAMP = " .':;=+*#%@";
  const GLYPHS = "0123456789ABCDEF<>[]{}+*#~-·";
  let ctx = eyeCanvas ? eyeCanvas.getContext("2d") : null;
  let canvasW = 480;
  let canvasH = 260;
  let cols = 48;
  let rows = 22;
  let charW = 10;
  let charH = 12;

  // Eye Animation Physics
  let phase = 0.0;
  let morphWeight = 0.0;
  let eyeOpen = 0.0;
  let eyeOpenTarget = 0.85;
  let pupilSize = 0.28;
  let gazeX = 0.0, gazeY = 0.0;
  let targetGazeX = 0.0, targetGazeY = 0.0;
  let nextBlink = performance.now() + 3000;
  let blinkPhase = -1; // -1: not blinking
  let userTouching = false;
  let lastFrameTime = performance.now();
  let frameCounter = 0;
  let lastFpsTime = performance.now();

  const STATE_PALETTES = {
    OFF: { main: "#445d6e", dim: "#1c2b36", glow: "rgba(68, 93, 110, 0.2)" },
    IDLE: { main: "#3df0ff", dim: "#0d3b48", glow: "rgba(61, 240, 255, 0.4)" },
    LISTENING: { main: "#3dffb0", dim: "#0d4430", glow: "rgba(61, 255, 176, 0.5)" },
    THINKING: { main: "#ffb020", dim: "#443008", glow: "rgba(255, 176, 32, 0.4)" },
    PROCESSING: { main: "#ffb020", dim: "#443008", glow: "rgba(255, 176, 32, 0.4)" },
    SPEAKING: { main: "#7fd8ff", dim: "#144866", glow: "rgba(127, 216, 255, 0.7)" },
  };

  function resizeEyeCanvas() {
    if (!eyeCanvas || !ctx) return;
    const rect = eyeCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasW = rect.width || 480;
    canvasH = rect.height || 260;
    eyeCanvas.width = canvasW * dpr;
    eyeCanvas.height = canvasH * dpr;
    ctx.scale(dpr, dpr);

    charW = 9.5;
    charH = 12;
    cols = Math.floor(canvasW / charW);
    rows = Math.floor(canvasH / charH);
  }
  window.addEventListener("resize", resizeEyeCanvas);

  // Eye Touch / Pointer Tracking
  if (eyeCanvas) {
    const updatePointerGaze = (e) => {
      const rect = eyeCanvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
      const ny = ((clientY - rect.top) / rect.height) * 2 - 1;
      targetGazeX = Math.max(-0.8, Math.min(0.8, nx * 0.9));
      targetGazeY = Math.max(-0.8, Math.min(0.8, ny * 0.9));
      userTouching = true;
    };
    eyeCanvas.addEventListener("pointerdown", (e) => {
      eyeCanvas.setPointerCapture(e.pointerId);
      updatePointerGaze(e);
    });
    eyeCanvas.addEventListener("pointermove", (e) => {
      if (userTouching) updatePointerGaze(e);
    });
    const releasePointer = () => { userTouching = false; };
    eyeCanvas.addEventListener("pointerup", releasePointer);
    eyeCanvas.addEventListener("pointercancel", releasePointer);
  }

  function renderAsciiEye() {
    if (!ctx) return;
    const now = performance.now();
    const dt = Math.min((now - lastFrameTime) / 1000, 0.1);
    lastFrameTime = now;
    phase += dt * (currentState === "SPEAKING" ? 4.2 : currentState === "THINKING" ? 3.0 : 1.6);

    // FPS Counter
    frameCounter++;
    if (now - lastFpsTime >= 1000) {
      if (fpsTag) fpsTag.textContent = `${frameCounter} FPS`;
      frameCounter = 0;
      lastFpsTime = now;
    }

    // State Transitions
    const isSpeaking = currentState === "SPEAKING";
    const targetMorph = isSpeaking ? 0.95 : 0.0;
    morphWeight += (targetMorph - morphWeight) * Math.min(1.0, dt * 5.0);

    // Target Eye Opening & Gaze
    if (currentState === "OFF") {
      eyeOpenTarget = 0.08;
      pupilSize = 0.15;
    } else if (currentState === "SPEAKING") {
      eyeOpenTarget = 0.92;
      pupilSize = 0.36 + Math.sin(phase * 6) * 0.06;
    } else if (currentState === "LISTENING") {
      eyeOpenTarget = 0.95;
      pupilSize = 0.34;
    } else if (currentState === "THINKING") {
      eyeOpenTarget = 0.75;
      pupilSize = 0.22;
    } else { // IDLE
      eyeOpenTarget = 0.85;
      pupilSize = 0.28;
    }

    // Saccadic Eye Wandering (when not touched)
    if (!userTouching) {
      if (Math.random() < 0.015) {
        targetGazeX = (Math.random() - 0.5) * 0.6;
        targetGazeY = (Math.random() - 0.5) * 0.4;
      }
    }
    gazeX += (targetGazeX - gazeX) * Math.min(1.0, dt * 6.0);
    gazeY += (targetGazeY - gazeY) * Math.min(1.0, dt * 6.0);

    // Blinking Engine
    if (blinkPhase < 0 && now >= nextBlink && currentState !== "OFF") {
      blinkPhase = 0.0;
    }
    let blinkFactor = 1.0;
    if (blinkPhase >= 0) {
      blinkPhase += dt * 7.5; // Smooth quick blink
      if (blinkPhase <= 1.0) {
        blinkFactor = 1.0 - Math.sin(blinkPhase * Math.PI);
      } else {
        blinkPhase = -1;
        nextBlink = now + 2500 + Math.random() * 3000;
      }
    }
    eyeOpen += (eyeOpenTarget * blinkFactor - eyeOpen) * Math.min(1.0, dt * 10.0);

    // Clear Canvas
    ctx.fillStyle = "#010307";
    ctx.fillRect(0, 0, canvasW, canvasH);

    // Palette
    const palette = STATE_PALETTES[currentState] || STATE_PALETTES.IDLE;
    ctx.font = `${charH - 1}px "Consolas", "SF Mono", monospace`;
    ctx.textBaseline = "top";

    const cx = canvasW / 2;
    const cy = canvasH / 2;
    const eyeScaleX = canvasW * 0.38;
    const eyeScaleY = canvasH * 0.36;

    // Render Matrix Grid
    for (let r = 0; r < rows; r++) {
      const y = r * charH;
      const ny = (y - cy) / eyeScaleY;

      for (let c = 0; c < cols; c++) {
        const x = c * charW;
        const nx = (x - cx) / eyeScaleX;

        // Eye coordinates
        const ex = nx - gazeX * 0.25;
        const ey = ny - gazeY * 0.25;
        const distCenter = Math.sqrt(ex * ex + ey * ey);

        // Upper & Lower Eyelid boundary
        const eyelidCurve = 1.0 - 0.55 * Math.pow(nx / 1.6, 2);
        const insideEye = Math.abs(ny) < eyelidCurve * Math.max(0.04, eyeOpen);

        let intensity = 0.0;
        let isEyeFeature = false;

        if (insideEye) {
          isEyeFeature = true;
          // Iris circle
          const irisDist = Math.sqrt(Math.pow(ex, 2) + Math.pow(ey, 2));
          if (irisDist < pupilSize * 0.5) {
            // Pupil (dense center)
            intensity = 0.95;
          } else if (irisDist < pupilSize) {
            // Inner Iris
            intensity = 0.75 + Math.sin(irisDist * 30 - phase * 3) * 0.2;
          } else if (irisDist < 0.65) {
            // Iris pattern
            const angle = Math.atan2(ey, ex);
            intensity = 0.45 + Math.sin(angle * 12 + phase * 2) * 0.25;
          } else {
            // Sclera / Whites
            intensity = 0.15;
          }

          // Eyelid edge highlight
          const edgeDist = Math.abs(Math.abs(ny) - eyelidCurve * eyeOpen);
          if (edgeDist < 0.12) {
            intensity = Math.max(intensity, 0.85);
          }
        } else {
          // Cyber Matrix Background Ripple
          const bgDist = Math.sqrt(nx * nx + ny * ny);
          const ripple = Math.sin(bgDist * 8.0 - phase * 1.5);
          if (ripple > 0.6) {
            intensity = (ripple - 0.6) * 0.4;
          }
        }

        // =======================================================
        // DYNAMIC MORPH: Speaking State Geometries
        // =======================================================
        if (morphWeight > 0.05) {
          const theta = Math.atan2(ny, nx);
          const rMorph = Math.sqrt(nx * nx + ny * ny);

          // 1. Rotating Hexagonal Diaphragm
          const hexMod = Math.abs(Math.cos(3 * theta - phase * 2.5));
          const hexEdge = 0.55 + 0.25 * hexMod;
          const hexDist = Math.abs(rMorph - hexEdge);
          let hexIntensity = 0.0;
          if (hexDist < 0.1) hexIntensity = (1.0 - hexDist / 0.1) * 0.95;

          // 2. Expanding Sonar Acoustic Shockwaves
          const wavePhase = (phase * 2.0) % 1.5;
          const waveDist = Math.abs(rMorph - wavePhase);
          let waveIntensity = 0.0;
          if (waveDist < 0.15) waveIntensity = (1.0 - waveDist / 0.15) * 0.85;

          // 3. Frequency Equalizer Spikes
          const freqSpikes = Math.abs(Math.sin(16 * theta + phase * 3.0));
          let eqIntensity = 0.0;
          if (rMorph > 0.4 && rMorph < 0.4 + freqSpikes * 0.35) {
            eqIntensity = 0.75;
          }

          const morphTotal = Math.max(hexIntensity, waveIntensity, eqIntensity);
          intensity = intensity * (1.0 - morphWeight * 0.7) + morphTotal * morphWeight;
          if (morphTotal > 0.3) isEyeFeature = true;
        }

        // Render Character Glyph
        if (intensity > 0.08) {
          const charIndex = Math.min(RAMP.length - 1, Math.floor(intensity * RAMP.length));
          const char = RAMP[charIndex];
          if (char !== " ") {
            if (isEyeFeature) {
              ctx.fillStyle = intensity > 0.7 ? palette.main : palette.dim;
            } else {
              ctx.fillStyle = "rgba(42, 70, 92, 0.45)";
            }
            ctx.fillText(char, x, y);
          }
        }
      }
    }

    requestAnimationFrame(renderAsciiEye);
  }

  // =========================================================================
  // 2. STATE & BADGE MANAGMENT
  // =========================================================================
  function setBadge(state) {
    currentState = (state || "OFF").toUpperCase();
    if (badge) {
      badge.className = "badge " + currentState.toLowerCase();
      badge.querySelector(".label").textContent = currentState;
    }
    if (eyeStatus) {
      const labels = {
        OFF: "DEVRE DIŞI",
        IDLE: "HAZIR // BEKLEMEDE",
        LISTENING: "DİNLİYOR // SES ALGISI",
        THINKING: "DÜŞÜNÜYOR // ANALİZ",
        PROCESSING: "İŞLENİYOR // KOMUT",
        SPEAKING: "KONUŞUYOR // AKTİF MORF",
      };
      eyeStatus.textContent = labels[currentState] || currentState;
      eyeStatus.style.color = (STATE_PALETTES[currentState] || STATE_PALETTES.IDLE).main;
    }
  }

  function appendMsg(role, text) {
    if (!text || !logEl) return;
    const div = document.createElement("div");
    div.className = "msg " + role;

    const head = document.createElement("div");
    head.className = "msg-head";
    const who = document.createElement("span");
    who.textContent = role === "user" ? "KULLANICI" : role === "error" ? "SİSTEM HATASI" : "RIFKI";
    head.appendChild(who);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    const body = document.createElement("div");
    body.className = "body";
    body.textContent = text;
    const time = document.createElement("div");
    time.className = "time";
    const d = new Date();
    time.textContent = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
    bubble.appendChild(body);
    bubble.appendChild(time);

    div.appendChild(head);
    div.appendChild(bubble);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;

    // Speech synthesis playback on mobile if assistant
    if (role === "assistant" && ttsEnabled && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "tr-TR";
        utter.rate = 1.05;
        window.speechSynthesis.speak(utter);
      } catch (_) {}
    }
  }

  // =========================================================================
  // 3. TELEMETRY & HARDWARE SYNC
  // =========================================================================
  async function fetchTelemetry() {
    if (!token) return;
    try {
      const res = await fetch(`/api/telemetry?token=${encodeURIComponent(token)}`);
      if (res.status === 401) { showAuth(); return; }
      if (!res.ok) return;
      const data = await res.json();
      if (cpuVal && cpuBar) {
        cpuVal.textContent = `${data.cpu}%`;
        cpuBar.style.width = `${Math.min(100, data.cpu)}%`;
      }
      if (ramVal && ramBar) {
        ramVal.textContent = `${data.ram}%`;
        ramBar.style.width = `${Math.min(100, data.ram)}%`;
      }
      if (diskVal && diskBar) {
        diskVal.textContent = `${data.disk}%`;
        diskBar.style.width = `${Math.min(100, data.disk)}%`;
      }
      if (batVal) {
        if (data.battery) {
          batVal.textContent = `${data.battery.percent}%${data.battery.plugged ? "⚡" : ""}`;
        } else {
          batVal.textContent = "AC";
        }
      }
      if (clockVal && data.time) {
        clockVal.textContent = data.time.substring(0, 5);
      }
    } catch (_) {}
  }

  async function fetchVolume() {
    if (!token) return;
    try {
      const res = await fetch(`/api/volume?token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (typeof data.level === "number") {
        updateVolumeUI(data.level, data.muted);
      }
    } catch (_) {}
  }

  function updateVolumeUI(level, muted) {
    isMuted = !!muted;
    if (volPill) {
      volPill.textContent = muted ? "Ses: Sessiz" : `Ses: %${level}`;
    }
    if (volSlider) {
      volSlider.value = level;
    }
    if (volSliderVal) {
      volSliderVal.textContent = `${level}%`;
    }
    if (btnMuteToggle) {
      btnMuteToggle.textContent = muted ? "🔈" : "🔇";
    }
  }

  // =========================================================================
  // 4. REMOTE ACTIONS & API CALLS
  // =========================================================================
  async function callRemote(action, params = {}, confirmMsg = null) {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    try {
      const body = { action, confirm: !!confirmMsg, ...params };
      const res = await fetch(`/api/remote?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.volume) {
        updateVolumeUI(data.volume.level, data.volume.muted);
      }
      if (data.telemetry) {
        fetchTelemetry();
      }
      if (data.reply) {
        appendMsg("assistant", data.reply);
      }
      return data;
    } catch (e) {
      appendMsg("error", "Bağlantı hatası: " + e.message);
    }
  }

  // Bind Remote Buttons
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const confirmMsg = btn.dataset.confirm;
      const paramStr = btn.dataset.param || "";
      const params = {};
      if (paramStr) {
        const [k, v] = paramStr.split(":");
        params[k] = isNaN(Number(v)) ? v : Number(v);
      }
      callRemote(action, params, confirmMsg);
    });
  });

  // Volume Slider
  if (volSlider) {
    volSlider.addEventListener("input", () => {
      if (volSliderVal) volSliderVal.textContent = `${volSlider.value}%`;
    });
    volSlider.addEventListener("change", () => {
      callRemote("set_volume", { level: parseInt(volSlider.value, 10) });
    });
  }
  if (btnMuteToggle) {
    btnMuteToggle.addEventListener("click", () => {
      callRemote("toggle_mute");
    });
  }

  // Clipboard Actions
  if (btnSendClipboard && clipInput) {
    btnSendClipboard.addEventListener("click", async () => {
      const text = clipInput.value.trim();
      if (!text) return;
      await callRemote("set_clipboard", { text });
      appendMsg("assistant", "Metin PC panosuna gönderildi.");
    });
  }
  if (btnTypeToPc && clipInput) {
    btnTypeToPc.addEventListener("click", async () => {
      const text = clipInput.value.trim();
      if (!text) return;
      await callRemote("type_text", { text });
      appendMsg("assistant", "Metin PC aktif penceresine yazıldı.");
    });
  }
  if (btnGetClipboard && clipInput) {
    btnGetClipboard.addEventListener("click", async () => {
      const data = await callRemote("get_clipboard");
      if (data && data.clipboard) {
        clipInput.value = data.clipboard;
        appendMsg("assistant", "PC panosu telefona aktarıldı.");
      }
    });
  }

  // URL & Search Form
  if (urlForm && urlInput) {
    urlForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = urlInput.value.trim();
      if (!val) return;
      callRemote("open_url", { url: val });
      urlInput.value = "";
    });
  }
  if (btnSearchGoogle && urlInput) {
    btnSearchGoogle.addEventListener("click", () => {
      const val = urlInput.value.trim();
      if (val) callRemote("search_google", { query: val });
    });
  }
  if (btnSearchYoutube && urlInput) {
    btnSearchYoutube.addEventListener("click", () => {
      const val = urlInput.value.trim();
      if (val) callRemote("search_youtube", { query: val });
    });
  }

  // Screenshot direct
  if (btnShotDirect) {
    btnShotDirect.addEventListener("click", async () => {
      try {
        appendMsg("user", "Ekran görüntüsü al");
        const res = await fetch(`/api/screenshot?token=${encodeURIComponent(token)}`);
        if (!res.ok) throw new Error("Görüntü alınamadı");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        openLightbox(url);
        appendMsg("assistant", "Ekran görüntüsü yakalandı.");
      } catch (err) {
        appendMsg("error", err.message);
      }
    });
  }

  // Quick Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const text = chip.dataset.cmd;
      if (!text) return;
      if (cmd) cmd.value = text;

      if (text.includes("ekran görüntüsü") || text.includes("ekran al")) {
        if (btnShotDirect) {
          btnShotDirect.click();
          return;
        }
      }
      if (text.includes("sesi yüzde elli")) {
        callRemote("set_volume", { level: 50 });
      }
      if (text.includes("kilitle")) {
        callRemote("lock");
        return;
      }
      submitCommand(text);
    });
  });

  // =========================================================================
  // 5. APPS & LIVE SCREEN
  // =========================================================================
  async function loadApps() {
    if (!token) return;
    try {
      if (appsMeta) appsMeta.textContent = "Yükleniyor…";
      const res = await fetch(`/api/apps?limit=250&token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();
      appsCache = data.apps || [];
      renderApps(appsCache);
      if (appsMeta) appsMeta.textContent = `${appsCache.length} uygulama hazır`;
    } catch (_) {
      if (appsMeta) appsMeta.textContent = "Yüklenemedi";
    }
  }

  function renderApps(list) {
    if (!appsList) return;
    appsList.innerHTML = "";
    const items = list.slice(0, 100);
    items.forEach((app) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = `<span>${escapeHtml(app.name)}</span><span class="pill">Başlat</span>`;
      b.addEventListener("click", async () => {
        try {
          await fetch(`/api/apps/launch?token=${encodeURIComponent(token)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: app.path }),
          });
          appendMsg("assistant", `${app.name} başlatıldı.`);
        } catch (e) {
          appendMsg("error", "Uygulama başlatılamadı: " + e.message);
        }
      });
      li.appendChild(b);
      appsList.appendChild(li);
    });
  }

  if (appSearch) {
    appSearch.addEventListener("input", () => {
      const q = appSearch.value.trim().toLowerCase();
      if (!q) {
        renderApps(appsCache);
      } else {
        const filtered = appsCache.filter((a) => a.name.toLowerCase().includes(q));
        renderApps(filtered);
      }
    });
  }

  // Live Screen
  async function refreshLive() {
    if (!token) return;
    try {
      const res = await fetch(`/api/screenshot?token=${encodeURIComponent(token)}&t=${Date.now()}`);
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (liveImg) {
        liveImg.src = url;
        liveImg.hidden = false;
      }
      if (liveEmpty) liveEmpty.hidden = true;
    } catch (_) {}
  }

  if (btnLiveToggle) {
    btnLiveToggle.addEventListener("click", () => {
      liveOn = !liveOn;
      btnLiveToggle.textContent = liveOn ? "Canlı: Açık" : "Canlı: Kapalı";
      btnLiveToggle.style.borderColor = liveOn ? "var(--ok)" : "var(--line)";
      if (liveOn) {
        refreshLive();
        liveTimer = setInterval(refreshLive, 2500);
      } else {
        clearInterval(liveTimer);
      }
    });
  }
  if (btnLiveRefresh) {
    btnLiveRefresh.addEventListener("click", refreshLive);
  }
  if (liveImg) {
    liveImg.addEventListener("click", () => {
      if (liveImg.src) openLightbox(liveImg.src);
    });
  }

  // Lightbox
  function openLightbox(url) {
    if (lightboxImg && lightbox) {
      lightboxImg.src = url;
      lightbox.classList.remove("hidden");
    }
  }
  if (lightboxClose) {
    lightboxClose.addEventListener("click", () => lightbox.classList.add("hidden"));
  }
  if (lightbox) {
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) lightbox.classList.add("hidden");
    });
  }

  // =========================================================================
  // 6. DECK TABS NAVIGATION
  // =========================================================================
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      document.querySelectorAll(".deck-pane").forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const targetId = tab.dataset.tab;
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add("active");

      if (targetId === "appsDeck" && appsCache.length === 0) {
        loadApps();
      }
      if (targetId === "visionDeck" && !liveImg.src) {
        refreshLive();
      }
    });
  });

  // =========================================================================
  // 7. VOICE INPUT (WEB SPEECH RECOGNITION) & COMPOSER
  // =========================================================================
  let recognition = null;
  let isRecording = false;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "tr-TR";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      isRecording = true;
      if (btnMic) btnMic.classList.add("recording");
      setBadge("LISTENING");
    };

    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      if (cmd) cmd.value = text;
      submitCommand(text);
    };

    recognition.onerror = (e) => {
      console.warn("SpeechRecognition error:", e);
      stopRecording();
    };

    recognition.onend = () => {
      stopRecording();
    };
  }

  function stopRecording() {
    isRecording = false;
    if (btnMic) btnMic.classList.remove("recording");
    if (currentState === "LISTENING") setBadge("IDLE");
  }

  if (btnMic) {
    btnMic.addEventListener("click", () => {
      if (!recognition) {
        alert("Tarayıcınız Web Speech ses tanımayı desteklemiyor. Metin kutusunu kullanabilirsiniz.");
        return;
      }
      if (isRecording) {
        recognition.stop();
      } else {
        try {
          recognition.start();
        } catch (_) {}
      }
    });
  }

  // TTS Toggle
  if (btnTtsToggle) {
    btnTtsToggle.addEventListener("click", () => {
      ttsEnabled = !ttsEnabled;
      btnTtsToggle.classList.toggle("active", ttsEnabled);
    });
  }

  // Submit Command
  async function submitCommand(text) {
    text = (text || "").trim();
    if (!text) return;
    if (!token) {
      showAuth();
      return;
    }
    appendMsg("user", text);
    if (cmd) cmd.value = "";
    setBadge("THINKING");

    try {
      const res = await fetch(`/api/command?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, command: text }),
      });
      if (res.status === 401) { showAuth(); return; }
      const data = await res.json();
      if (data.reply) {
        appendMsg("assistant", data.reply);
      }
      setBadge("IDLE");
    } catch (err) {
      appendMsg("error", "Komut iletilemedi: " + err.message);
      setBadge("IDLE");
    }
  }

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      submitCommand(cmd.value);
    });
  }

  // =========================================================================
  // 8. WEBSOCKET REAL-TIME SYNC
  // =========================================================================
  function connectWebSocket() {
    if (!token) return;
    if (ws) {
      try { ws.close(); } catch (_) {}
    }
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws?token=${encodeURIComponent(token)}`;

    try {
      ws = new WebSocket(url);
    } catch (e) {
      reconnectWebSocket();
      return;
    }

    ws.onopen = () => {
      if (meta) meta.textContent = "Bağlandı (Canlı WS)";
      fetchTelemetry();
      fetchVolume();
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "status" || msg.state) {
          setBadge(msg.state);
        }
        if (msg.type === "user" && msg.text) {
          appendMsg("user", msg.text);
        }
        if (msg.type === "assistant" && msg.text) {
          appendMsg("assistant", msg.text);
        }
        if (msg.type === "error" && msg.text) {
          appendMsg("error", msg.text);
        }
      } catch (_) {}
    };

    ws.onclose = () => {
      if (meta) meta.textContent = "Bağlantı koptu, yeniden deneniyor…";
      setBadge("OFF");
      reconnectWebSocket();
    };

    ws.onerror = () => {
      try { ws.close(); } catch (_) {}
    };
  }

  function reconnectWebSocket() {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = setTimeout(connectWebSocket, 3000);
  }

  // =========================================================================
  // 9. AUTHENTICATION & BOOTSTRAP
  // =========================================================================
  function showAuth() {
    if (auth) auth.classList.remove("hidden");
  }

  if (saveToken && tokenInput) {
    saveToken.addEventListener("click", () => {
      const val = tokenInput.value.trim();
      if (!val) return;
      token = val;
      localStorage.setItem("rifki_bridge_token", token);
      if (auth) auth.classList.add("hidden");
      initBridge();
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function initBridge() {
    if (!token) {
      showAuth();
      return;
    }
    connectWebSocket();
    fetchTelemetry();
    fetchVolume();
    clearInterval(telemTimer);
    telemTimer = setInterval(fetchTelemetry, 3500);
  }

  // Start ASCII Engine & Initialize
  resizeEyeCanvas();
  renderAsciiEye();
  initBridge();
})();
