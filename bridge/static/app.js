/**
 * RIFKI Siber Kokpit — Mobil İstemci & ASCII Siber Göz Motoru
 */
(() => {
  // DOM Elements
  const badge = document.getElementById("badge");
  if (badge) {
    badge.style.cursor = "pointer";
    badge.addEventListener("click", () => {
      fetchStatus();
      connectWebSocket();
    });
  }
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
  const ytMusicForm = document.getElementById("ytMusicForm");
  const ytMusicInput = document.getElementById("ytMusicInput");

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
  const urlToken = params.get("token");
  if (urlToken) {
    localStorage.setItem("rifki_bridge_token", urlToken);
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }
  let token = urlToken || localStorage.getItem("rifki_bridge_token") || "";
  function authHeaders(extra = {}) {
    return Object.assign({ "Authorization": `Bearer ${token}` }, extra);
  }
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

  let activeAudio = null;
  let lastSpokenText = "";
  let lastSpokenTime = 0;
  function fallbackSpeechSynthesis(text) {
    if (!("speechSynthesis" in window) || !ttsEnabled) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "tr-TR";
      u.onstart = () => setBadge("SPEAKING");
      u.onend = () => setBadge("IDLE");
      u.onerror = () => setBadge("IDLE");
      window.speechSynthesis.speak(u);
    } catch (_) {}
  }
  function playPhoneAudio(text) {
    if (!ttsEnabled || !text || !token) return;
    const clean = text.trim();
    if (!clean) return;
    const now = Date.now();
    // 8 saniye i?inde ayn? metnin tekrar oynat?lmas?n? (HTTP + WebSocket ?ift tetikleme) engelle
    if (lastSpokenText === clean && now - lastSpokenTime < 8000) {
      return;
    }
    lastSpokenText = clean;
    lastSpokenTime = now;
    // ?nceki ses/konu?may? temiz durdur (ghost eventleri engellemek i?in callbackleri s?f?rla)
    if (activeAudio) {
      try {
        activeAudio.onended = null;
        activeAudio.onerror = null;
        activeAudio.pause();
        activeAudio.src = "";
      } catch (_) {}
      activeAudio = null;
    }
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
    setBadge("SPEAKING");
    const audioUrl = `/api/tts?token=${encodeURIComponent(token)}&text=${encodeURIComponent(clean)}&t=${Date.now()}`;
    const audio = new Audio(audioUrl);
    activeAudio = audio;
    audio.onended = () => {
      if (activeAudio === audio) {
        setBadge("IDLE");
        activeAudio = null;
      }
    };
    audio.onerror = () => {
      if (activeAudio !== audio || !audio.src) return;
      setBadge("IDLE");
      activeAudio = null;
      fallbackSpeechSynthesis(clean);
    };
    audio.play().catch((err) => {
      // AbortError biz pause() etti?imizde olu?ur, asla fallback tetiklememeli
      if (err && err.name === "AbortError") {
        return;
      }
      if (activeAudio !== audio) return;
      setBadge("IDLE");
      activeAudio = null;
      fallbackSpeechSynthesis(clean);
    });
  }
  // Unlock mobile browser audio context on first touch/click
  const unlockAudio = () => {
    try {
      const silent = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA");
      silent.play().catch(() => {});
    } catch (_) {}
  };
  window.addEventListener("touchstart", unlockAudio, { once: true, passive: true });
  window.addEventListener("click", unlockAudio, { once: true, passive: true });
  const recentMessages = [];
  function isDuplicateMessage(role, text) {
    const now = Date.now();
    while (recentMessages.length && now - recentMessages[0].time > 8000) {
      recentMessages.shift();
    }
    const isDup = recentMessages.some((m) => m.role === role && m.text === text);
    if (!isDup) {
      recentMessages.push({ role, text, time: now });
    }
    return isDup;
  }
  function appendMsg(role, text) {
    if (!text || !logEl) return;
    if (isDuplicateMessage(role, text)) return;
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

    if (role === "assistant") {
      playPhoneAudio(text);
    }
  }

  // =========================================================================
  // 3. TELEMETRY & HARDWARE SYNC
  // =========================================================================
async function fetchStatus() {
    if (!token) return;
    try {
      const res = await fetch("/api/status", { headers: authHeaders() });
      if (res.status === 401) { showAuth(); return; }
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.state) {
        setBadge(data.state);
      }
    } catch (_) {}
  }

  async function fetchTelemetry() {
    if (!token) return;
    try {
      const res = await fetch("/api/telemetry", { headers: authHeaders() });
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
      if (typeof data.game_mode === "boolean") {
        updateGameModeUI(data.game_mode);
      }
    } catch (_) {}
  }

  async function fetchVolume() {
    if (!token) return;
    try {
      const res = await fetch("/api/volume", { headers: authHeaders() });
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
      const res = await fetch("/api/remote", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
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
      if (action === "wake_device" && window.AndroidBridge && typeof window.AndroidBridge.wakePc === "function") {
        window.AndroidBridge.wakePc(params.target || "");
        appendMsg("assistant", "⚡ Telefondan yerel Wake-on-LAN sihirli paketi fırlatıldı.");
        return;
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

  // YouTube Music Form
  if (ytMusicForm && ytMusicInput) {
    ytMusicForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = ytMusicInput.value.trim();
      if (!val) return;
      callRemote("play_youtube_music", { query: val });
      ytMusicInput.value = "";
    });
  }

  // Screenshot direct
  if (btnShotDirect) {
    btnShotDirect.addEventListener("click", async () => {
      try {
        appendMsg("user", "Ekran görüntüsü al");
        const res = await fetch("/api/screenshot", { headers: authHeaders() });
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

      if (text.includes("oyun modu")) {
        callRemote("game_mode_toggle");
        return;
      }
      if (text.includes("ram temizle")) {
        callRemote("optimize_ram");
        return;
      }
      if (text.includes("ekrana bak")) {
        runVisionAnalysis();
        return;
      }
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
  // 4B. OYUN MODU, SİBER TOUCHPAD & KABLOSUZ AIRDROP (v2.6.0)
  // =========================================================================
  const btnGameModeToggle = document.getElementById("btnGameModeToggle");
  const btnRamBoost = document.getElementById("btnRamBoost");
  const gameModePill = document.getElementById("gameModePill");

  function updateGameModeUI(active) {
    if (gameModePill) {
      gameModePill.textContent = active ? "⚡ OYUN MODU AKTİF" : "Standart Mod";
      gameModePill.style.color = active ? "#3dffb0" : "";
      gameModePill.style.borderColor = active ? "#3dffb0" : "";
    }
    if (btnGameModeToggle) {
      btnGameModeToggle.textContent = active ? "🎮 Oyun Modu: AÇIK (Kapat)" : "🎮 Oyun Modunu Aç";
      btnGameModeToggle.classList.toggle("game-btn-active", !!active);
    }
  }

  if (btnGameModeToggle) {
    btnGameModeToggle.addEventListener("click", async () => {
      const data = await callRemote("game_mode_toggle");
      if (data && typeof data.game_mode === "boolean") {
        updateGameModeUI(data.game_mode);
      }
    });
  }

  if (btnRamBoost) {
    btnRamBoost.addEventListener("click", async () => {
      btnRamBoost.disabled = true;
      btnRamBoost.textContent = "🚀 Temizleniyor…";
      await callRemote("optimize_ram");
      btnRamBoost.disabled = false;
      btnRamBoost.textContent = "🚀 RAM Temizle & Hızlandır";
    });
  }

  // Siber Touchpad (Canlı PC Fare Kontrolü)
  const touchpadSurface = document.getElementById("touchpadSurface");
  const touchpadDot = document.getElementById("touchpadDot");
  const touchSensSlider = document.getElementById("touchSensSlider");
  const touchSensLabel = document.getElementById("touchSensLabel");
  let touchSens = 1.6;

  if (touchSensSlider) {
    touchSensSlider.addEventListener("input", () => {
      touchSens = parseInt(touchSensSlider.value, 10) / 10.0;
      if (touchSensLabel) touchSensLabel.textContent = `Hız: ${touchSens.toFixed(1)}x`;
    });
  }

  function sendMouseMove(dx, dy) {
    if (!dx && !dy) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "mouse_move", dx, dy }));
    } else {
      callRemote("mouse_move", { dx, dy });
    }
  }

  function sendMouseClick(button) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "mouse_click", button }));
    } else {
      callRemote("mouse_click", { button });
    }
  }

  if (touchpadSurface) {
    let tpActive = false;
    let lastX = 0;
    let lastY = 0;
    let startTime = 0;
    let totalMove = 0;
    let maxTouches = 1;
    let accumX = 0;
    let accumY = 0;

    const showDot = (clientX, clientY) => {
      if (!touchpadDot) return;
      const rect = touchpadSurface.getBoundingClientRect();
      touchpadDot.style.left = `${clientX - rect.left}px`;
      touchpadDot.style.top = `${clientY - rect.top}px`;
      touchpadDot.style.opacity = "1";
    };

    const hideDot = () => {
      if (touchpadDot) touchpadDot.style.opacity = "0";
      touchpadSurface.classList.remove("active");
    };

    touchpadSurface.addEventListener("touchstart", (e) => {
      e.preventDefault();
      tpActive = true;
      touchpadSurface.classList.add("active");
      const t = e.touches[0];
      lastX = t.clientX;
      lastY = t.clientY;
      startTime = performance.now();
      totalMove = 0;
      maxTouches = Math.max(1, e.touches.length);
      accumX = 0;
      accumY = 0;
      showDot(t.clientX, t.clientY);
    }, { passive: false });

    touchpadSurface.addEventListener("touchmove", (e) => {
      if (!tpActive) return;
      e.preventDefault();
      if (e.touches.length > maxTouches) maxTouches = e.touches.length;
      const t = e.touches[0];
      const rawDx = (t.clientX - lastX) * touchSens;
      const rawDy = (t.clientY - lastY) * touchSens;
      lastX = t.clientX;
      lastY = t.clientY;
      totalMove += Math.abs(rawDx) + Math.abs(rawDy);
      accumX += rawDx;
      accumY += rawDy;
      const sendDx = Math.trunc(accumX);
      const sendDy = Math.trunc(accumY);
      if (sendDx !== 0 || sendDy !== 0) {
        accumX -= sendDx;
        accumY -= sendDy;
        sendMouseMove(sendDx, sendDy);
      }
      showDot(t.clientX, t.clientY);
    }, { passive: false });

    touchpadSurface.addEventListener("touchend", (e) => {
      e.preventDefault();
      if (!tpActive) return;
      if (e.touches.length === 0) {
        tpActive = false;
        hideDot();
        const elapsed = performance.now() - startTime;
        if (elapsed < 240 && totalMove < 12) {
          sendMouseClick(maxTouches >= 2 ? "right" : "left");
        }
      }
    }, { passive: false });

    // Masaüstü fare ile test desteği
    touchpadSurface.addEventListener("mousedown", (e) => {
      tpActive = true;
      touchpadSurface.classList.add("active");
      lastX = e.clientX;
      lastY = e.clientY;
      startTime = performance.now();
      totalMove = 0;
      showDot(e.clientX, e.clientY);
    });
    window.addEventListener("mousemove", (e) => {
      if (!tpActive || e.touches) return;
      const dx = Math.round((e.clientX - lastX) * touchSens);
      const dy = Math.round((e.clientY - lastY) * touchSens);
      lastX = e.clientX;
      lastY = e.clientY;
      totalMove += Math.abs(dx) + Math.abs(dy);
      if (dx !== 0 || dy !== 0) sendMouseMove(dx, dy);
      showDot(e.clientX, e.clientY);
    });
    window.addEventListener("mouseup", () => {
      if (!tpActive) return;
      tpActive = false;
      hideDot();
    });
  }

  // Kablosuz AirDrop (Telefon ⇄ PC Dosya Aktarımı)
  const airdropInput = document.getElementById("airdropInput");
  const btnPickAirdrop = document.getElementById("btnPickAirdrop");
  const btnRefreshAirdrop = document.getElementById("btnRefreshAirdrop");
  const airdropStatus = document.getElementById("airdropStatus");
  const airdropList = document.getElementById("airdropList");

  function formatBytes(bytes) {
    if (!bytes || bytes < 1024) return `${bytes || 0} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function renderAirdropFiles(files) {
    if (!airdropList) return;
    airdropList.innerHTML = "";
    if (!files || files.length === 0) {
      const empty = document.createElement("li");
      empty.className = "card-hint";
      empty.textContent = "Henüz paylaşılan dosya yok.";
      airdropList.appendChild(empty);
      return;
    }
    files.forEach((f) => {
      const li = document.createElement("li");
      li.className = "airdrop-item";
      const dlUrl = `/api/transfer/download?name=${encodeURIComponent(f.name)}&token=${encodeURIComponent(token)}`;
      li.innerHTML = `
        <div class="airdrop-info">
          <span class="airdrop-name">${escapeHtml(f.name)}</span>
          <span class="airdrop-meta">${formatBytes(f.size)} · ${escapeHtml(f.mtime || "")}</span>
        </div>
        <a class="airdrop-dl" href="${dlUrl}" download="${escapeHtml(f.name)}">⬇️ İndir</a>
      `;
      airdropList.appendChild(li);
    });
  }

  async function loadAirdropFiles() {
    if (!token) return;
    try {
      const res = await fetch("/api/transfer/list", { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.ok) {
        renderAirdropFiles(data.files || []);
      }
    } catch (_) {}
  }

  if (btnPickAirdrop && airdropInput) {
    btnPickAirdrop.addEventListener("click", () => airdropInput.click());
    airdropInput.addEventListener("change", async () => {
      const files = airdropInput.files;
      if (!files || files.length === 0) return;
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("file", files[i]);
      }
      if (airdropStatus) {
        airdropStatus.textContent = `⏳ ${files.length} dosya PC'ye gönderiliyor, lütfen bekleyin…`;
        airdropStatus.style.color = "#ffb020";
      }
      btnPickAirdrop.disabled = true;
      try {
        const res = await fetch("/api/transfer/upload", {
          method: "POST",
          headers: authHeaders(),
          body: formData,
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.error || "Dosya gönderilemedi.");
        }
        if (airdropStatus) {
          airdropStatus.textContent = `✅ ${data.saved.length} dosya PC'ye aktarıldı (İndirilenler/RIFKI_AirDrop).`;
          airdropStatus.style.color = "#3dffb0";
        }
        renderAirdropFiles(data.files || []);
      } catch (err) {
        if (airdropStatus) {
          airdropStatus.textContent = `❌ Hata: ${err.message}`;
          airdropStatus.style.color = "#ff6b6b";
        }
        appendMsg("error", "AirDrop Hatası: " + err.message);
      } finally {
        btnPickAirdrop.disabled = false;
        airdropInput.value = "";
      }
    });
  }

  if (btnRefreshAirdrop) {
    btnRefreshAirdrop.addEventListener("click", loadAirdropFiles);
  }

  // =========================================================================
  // VISION AI (Görsel Analiz)
  // =========================================================================
  async function runVisionAnalysis(customQuestion) {
    const qInput = document.getElementById("visionQuestion");
    const q = customQuestion || (qInput ? qInput.value.trim() : "") || "Ekranda ne görüyorsun? Özetle.";
    const resultBox = document.getElementById("visionResult");
    if (resultBox) {
      resultBox.style.display = "block";
      resultBox.textContent = "🔍 Ekran taranıyor ve yapay zekâ multimodal model ile analiz ediyor, lütfen bekleyin...";
    }
    appendMsg("user", `👁️ Ekrana Bak: ${q}`);
    setBadge("THINKING");

    try {
      const res = await fetch("/api/vision", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ question: q }),
      });
      if (res.status === 401) {
        showAuth();
        return;
      }
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "Görsel analiz başarısız oldu.");
      }
      const answer = data.analysis || "Analiz tamamlandı.";
      if (resultBox) {
        resultBox.textContent = answer;
      }
      appendMsg("assistant", answer);
      const cleanAudio = answer
        .replace(/```[\s\S]*?```/g, '')
        .replace(/[*#_~`>\-\[\]]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
      playPhoneAudio(cleanAudio.slice(0, 250));
      setBadge("IDLE");
    } catch (err) {
      if (resultBox) {
        resultBox.textContent = `❌ Hata: ${err.message}`;
      }
      appendMsg("error", "Vision Hatası: " + err.message);
      setBadge("IDLE");
    }
  }

  const btnRunVision = document.getElementById("btnRunVision");
  if (btnRunVision) {
    btnRunVision.addEventListener("click", () => runVisionAnalysis());
  }

  const btnVisionQuick = document.getElementById("btnVisionQuick");
  if (btnVisionQuick) {
    btnVisionQuick.addEventListener("click", () => {
      runVisionAnalysis("Ekranda ne görüyorsun? Önemli detayları özetle.");
    });
  }

  // =========================================================================
  // 5. APPS & LIVE SCREEN
  // =========================================================================
  async function loadApps() {
    if (!token) return;
    try {
      if (appsMeta) appsMeta.textContent = "Yükleniyor…";
      const res = await fetch("/api/apps?limit=250", { headers: authHeaders() });
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
          await fetch("/api/apps/launch", {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ name: app.name }),
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

  // =========================================================================
  // 6. CANLI EKRAN MOTORU (ULTRA-LOW LATENCY STREAM & ADAPTIVE FRAME LOOP)
  // =========================================================================
  let liveMode = "ultra"; // "ultra" | "balanced" | "hd"
  let liveObjectUrl = null;
  let liveFrameCount = 0;
  let liveFpsLastCheck = performance.now();
  let liveCurrentFps = 0;
  let liveLatencyMs = 0;
  let livePendingFetch = false;

  const btnModeUltra = document.getElementById("btnModeUltra");
  const btnModeBalanced = document.getElementById("btnModeBalanced");
  const btnModeHd = document.getElementById("btnModeHd");
  const liveFpsBadge = document.getElementById("liveFpsBadge");

  function setLiveMode(mode) {
    liveMode = mode;
    [btnModeUltra, btnModeBalanced, btnModeHd].forEach((btn) => {
      if (btn) btn.classList.remove("active");
    });
    if (mode === "ultra" && btnModeUltra) btnModeUltra.classList.add("active");
    if (mode === "balanced" && btnModeBalanced) btnModeBalanced.classList.add("active");
    if (mode === "hd" && btnModeHd) btnModeHd.classList.add("active");
  }

  if (btnModeUltra) btnModeUltra.addEventListener("click", () => setLiveMode("ultra"));
  if (btnModeBalanced) btnModeBalanced.addEventListener("click", () => setLiveMode("balanced"));
  if (btnModeHd) btnModeHd.addEventListener("click", () => setLiveMode("hd"));

  function getModeParams() {
    if (liveMode === "ultra") {
      // Ultra Hızlı: 768px, Q48, ~20 FPS, ~45-60ms gecikme
      return { w: 768, q: 48, minDelay: 5 };
    }
    if (liveMode === "balanced") {
      // Dengeli: 960px, Q58, ~12 FPS, ~75ms gecikme
      return { w: 960, q: 58, minDelay: 45 };
    }
    // HD: 1280px, Q72, ~4 FPS (yüksek detay)
    return { w: 1280, q: 72, minDelay: 180 };
  }

  function updateLiveStats(latency) {
    liveFrameCount++;
    const now = performance.now();
    const elapsed = now - liveFpsLastCheck;
    if (elapsed >= 800) {
      liveCurrentFps = Math.round((liveFrameCount * 1000) / elapsed);
      liveFrameCount = 0;
      liveFpsLastCheck = now;
      if (liveFpsBadge && liveOn) {
        liveFpsBadge.textContent = `⚡ ${liveCurrentFps} FPS · ${latency}ms`;
        liveFpsBadge.style.display = "inline-flex";
      }
    }
  }

  async function fetchLiveFrame() {
    if (!token || !liveOn || livePendingFetch) return;
    livePendingFetch = true;
    const { w, q, minDelay } = getModeParams();
    const t0 = performance.now();

    try {
      const res = await fetch(`/api/screenshot?live=1&fast=1&w=${w}&q=${q}&t=${Date.now()}`, {
        headers: authHeaders(),
        cache: "no-store",
      });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const blob = await res.blob();
      const newUrl = URL.createObjectURL(blob);
      const oldUrl = liveObjectUrl;
      liveObjectUrl = newUrl;

      if (liveImg) {
        liveImg.src = newUrl;
        liveImg.hidden = false;
      }
      if (liveEmpty) liveEmpty.hidden = true;

      // Tarayıcı belleğini temiz tut: eski blob nesnesini anında serbest bırak
      if (oldUrl) URL.revokeObjectURL(oldUrl);

      const t1 = performance.now();
      liveLatencyMs = Math.round(t1 - t0);
      updateLiveStats(liveLatencyMs);

      livePendingFetch = false;
      if (liveOn) {
        const fetchDuration = t1 - t0;
        const sleepTime = Math.max(5, minDelay - Math.floor(fetchDuration));
        setTimeout(fetchLiveFrame, sleepTime);
      }
    } catch (err) {
      livePendingFetch = false;
      if (liveOn) {
        setTimeout(fetchLiveFrame, 300);
      }
    }
  }

  async function refreshLive() {
    if (!token) return;
    const { w, q } = getModeParams();
    try {
      const res = await fetch(`/api/screenshot?live=1&fast=1&w=${w}&q=${q}&t=${Date.now()}`, {
        headers: authHeaders(),
        cache: "no-store",
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const newUrl = URL.createObjectURL(blob);
      const oldUrl = liveObjectUrl;
      liveObjectUrl = newUrl;
      if (liveImg) {
        liveImg.src = newUrl;
        liveImg.hidden = false;
      }
      if (liveEmpty) liveEmpty.hidden = true;
      if (oldUrl) URL.revokeObjectURL(oldUrl);
    } catch (_) {}
  }

  if (btnLiveToggle) {
    btnLiveToggle.addEventListener("click", () => {
      liveOn = !liveOn;
      btnLiveToggle.textContent = liveOn ? "Canlı: Açık 🟢" : "Canlı: Kapalı";
      btnLiveToggle.style.borderColor = liveOn ? "var(--ok)" : "var(--line)";
      if (liveFpsBadge) {
        liveFpsBadge.style.display = liveOn ? "inline-flex" : "none";
        if (liveOn) liveFpsBadge.textContent = "⚡ Başlatılıyor…";
      }
      if (liveOn) {
        livePendingFetch = false;
        liveFrameCount = 0;
        liveFpsLastCheck = performance.now();
        fetchLiveFrame();
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
      if (targetId === "remoteDeck") {
        loadAirdropFiles();
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
      const res = await fetch("/api/command", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
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
      fetchStatus();
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
    fetchStatus();
    connectWebSocket();
    fetchTelemetry();
    fetchVolume();
    clearInterval(telemTimer);
    telemTimer = setInterval(() => {
      fetchTelemetry();
      fetchStatus();
    }, 3500);
  }

  // Start ASCII Engine & Initialize
  resizeEyeCanvas();
  renderAsciiEye();
  initBridge();
})();
