import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Output directory
OUT_DIR = Path("docs/play-assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DL_DIR = Path(os.path.expanduser("~")) / "Downloads"

FONT_DIR = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
def get_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()

# Typography
f_mono_xs = get_font("consola.ttf", 16)
f_mono_sm = get_font("consola.ttf", 22)
f_mono_md = get_font("consola.ttf", 30)
f_mono_lg = get_font("consola.ttf", 44)

f_sans_sm = get_font("segoeui.ttf", 26)
f_sans_md = get_font("segoeuib.ttf", 38)
f_sans_lg = get_font("segoeuib.ttf", 56)
f_sans_xl = get_font("segoeuib.ttf", 72)
f_sans_hero = get_font("segoeuib.ttf", 88)

# Palette
C_BG_DEEP = (2, 6, 12)
C_CARD = (10, 19, 30)
C_CARD_LIGHT = (16, 32, 48)
C_LINE = (61, 240, 255, 60)
C_LINE_BRIGHT = (61, 240, 255, 180)
C_CYAN = (61, 240, 255)
C_CYAN_VIVID = (127, 216, 255)
C_CYAN_DIM = (20, 60, 80)
C_GREEN = (61, 255, 176)
C_AMBER = (255, 176, 32)
C_TEXT = (231, 247, 255)
C_MUTED = (109, 143, 163)

RAMP = " .':;=+*#%@"

def draw_corner_brackets(draw, x0, y0, x1, y1, length=24, color=C_CYAN, width=3):
    draw.line([(x0, y0), (x0 + length, y0)], fill=color, width=width)
    draw.line([(x0, y0), (x0, y0 + length)], fill=color, width=width)
    draw.line([(x1, y0), (x1 - length, y0)], fill=color, width=width)
    draw.line([(x1, y0), (x1, y0 + length)], fill=color, width=width)
    draw.line([(x0, y1), (x0 + length, y1)], fill=color, width=width)
    draw.line([(x0, y1), (x0, y1 - length)], fill=color, width=width)
    draw.line([(x1, y1), (x1 - length, y1)], fill=color, width=width)
    draw.line([(x1, y1), (x1, y1 - length)], fill=color, width=width)

def render_ascii_eye(draw, x0, y0, w, h, state="IDLE", morph_weight=0.0, gaze=(0.0, 0.0), phase=1.5, char_size=12):
    char_w = char_size * 0.8
    char_h = char_size * 1.15
    f_char = get_font("consola.ttf", int(char_size))
    cols = int(w / char_w)
    rows = int(h / char_h)

    cx = x0 + w / 2.0
    cy = y0 + h / 2.0
    scale_x = w * 0.40
    scale_y = h * 0.38

    pupil = 0.28 if state != "SPEAKING" else 0.38
    eye_open = 0.90
    main_color = C_CYAN if state == "IDLE" else C_CYAN_VIVID if state == "SPEAKING" else C_GREEN

    for r in range(rows):
        y = y0 + r * char_h
        ny = (y - cy) / scale_y
        for c in range(cols):
            x = x0 + c * char_w
            nx = (x - cx) / scale_x

            ex = nx - gaze[0] * 0.25
            ey = ny - gaze[1] * 0.25

            eyelid = 1.0 - 0.55 * ((nx / 1.6) ** 2)
            inside = abs(ny) < eyelid * eye_open

            intensity = 0.0
            is_eye = False

            if inside:
                is_eye = True
                iris_dist = math.sqrt(ex * ex + ey * ey)
                if iris_dist < pupil * 0.5:
                    intensity = 0.95
                elif iris_dist < pupil:
                    intensity = 0.75 + math.sin(iris_dist * 30 - phase * 3) * 0.2
                elif iris_dist < 0.65:
                    angle = math.atan2(ey, ex)
                    intensity = 0.45 + math.sin(angle * 12 + phase * 2) * 0.25
                else:
                    intensity = 0.15

                edge = abs(abs(ny) - eyelid * eye_open)
                if edge < 0.12:
                    intensity = max(intensity, 0.85)
            else:
                bg_dist = math.sqrt(nx * nx + ny * ny)
                ripple = math.sin(bg_dist * 8.0 - phase * 1.5)
                if ripple > 0.6:
                    intensity = (ripple - 0.6) * 0.35

            if morph_weight > 0.05:
                theta = math.atan2(ny, nx)
                r_morph = math.sqrt(nx * nx + ny * ny)

                hex_mod = abs(math.cos(3 * theta - phase * 2.5))
                hex_edge = 0.55 + 0.25 * hex_mod
                hex_dist = abs(r_morph - hex_edge)
                hex_i = (1.0 - hex_dist / 0.1) * 0.95 if hex_dist < 0.1 else 0.0

                wave_phase = (phase * 2.0) % 1.5
                wave_dist = abs(r_morph - wave_phase)
                wave_i = (1.0 - wave_dist / 0.15) * 0.85 if wave_dist < 0.15 else 0.0

                freq_spikes = abs(math.sin(16 * theta + phase * 3.0))
                eq_i = 0.75 if (0.4 < r_morph < 0.4 + freq_spikes * 0.35) else 0.0

                m_total = max(hex_i, wave_i, eq_i)
                intensity = intensity * (1.0 - morph_weight * 0.7) + m_total * morph_weight
                if m_total > 0.3:
                    is_eye = True

            if intensity > 0.08:
                idx = min(len(RAMP) - 1, int(intensity * len(RAMP)))
                ch = RAMP[idx]
                if ch != " ":
                    col = main_color if (is_eye and intensity > 0.6) else C_CYAN_DIM if is_eye else (25, 45, 65)
                    draw.text((x, y), ch, font=f_char, fill=col)

def create_badge(text="IDLE", color=C_CYAN):
    pass

# ==============================================================================
# 1. APP ICON (512x512)
# ==============================================================================
def generate_icon():
    img = Image.new("RGBA", (512, 512), C_BG_DEEP)
    draw = ImageDraw.Draw(img)

    # Concentric cyber rings & glow
    cx, cy = 256, 256
    for r, width, alpha in [(235, 2, 50), (210, 1, 80), (180, 2, 140)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(61, 240, 255, alpha), width=width)

    # Tick marks around outer ring
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        r0 = 235
        r1 = 222 if deg % 45 == 0 else 228
        x0 = cx + r0 * math.cos(rad)
        y0 = cy + r0 * math.sin(rad)
        x1 = cx + r1 * math.cos(rad)
        y1 = cy + r1 * math.sin(rad)
        w = 3 if deg % 45 == 0 else 1
        draw.line([(x0, y0), (x1, y1)], fill=C_CYAN, width=w)

    # ASCII Eye in center
    render_ascii_eye(draw, 76, 120, 360, 220, state="IDLE", gaze=(0.0, 0.0), phase=2.0, char_size=9)

    # Brackets
    draw_corner_brackets(draw, 80, 110, 432, 350, length=20, color=C_CYAN, width=2)

    # Brand Title
    draw.text((cx, 400), "RIFKI", font=f_sans_md, fill=C_CYAN, anchor="mm")
    draw.text((cx, 436), "SİBER ASİSTAN // v2.3", font=f_mono_xs, fill=C_MUTED, anchor="mm")

    path = OUT_DIR / "rifki-icon-512.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-icon-512.png", "PNG")
    print(f"Generated {path}")

# ==============================================================================
# 2. FEATURE GRAPHIC (1024x500)
# ==============================================================================
def generate_feature():
    img = Image.new("RGBA", (1024, 500), C_BG_DEEP)
    draw = ImageDraw.Draw(img)

    # Subtle tech background grid
    for x in range(0, 1024, 40):
        draw.line([(x, 0), (x, 500)], fill=(12, 28, 42, 60), width=1)
    for y in range(0, 500, 40):
        draw.line([(0, y), (1024, y)], fill=(12, 28, 42, 60), width=1)

    # Corner brackets of entire canvas
    draw_corner_brackets(draw, 16, 16, 1008, 484, length=32, color=C_CYAN, width=3)

    # Left: ASCII Cyber Eye Box
    eye_x, eye_y, eye_w, eye_h = 44, 80, 480, 340
    draw.rectangle([eye_x, eye_y, eye_x + eye_w, eye_y + eye_h], fill=(1, 3, 7), outline=(40, 80, 110), width=2)
    draw_corner_brackets(draw, eye_x, eye_y, eye_x + eye_w, eye_y + eye_h, length=24, color=C_CYAN, width=2)
    draw.text((eye_x + 14, eye_y + 12), "[ OPTIC.MATRIX // CORE.01 ]", font=f_mono_xs, fill=C_CYAN)
    draw.text((eye_x + eye_w - 14, eye_y + 12), "AKTİF", font=f_mono_xs, fill=C_GREEN, anchor="ra")
    render_ascii_eye(draw, eye_x + 10, eye_y + 36, eye_w - 20, eye_h - 60, state="SPEAKING", morph_weight=0.88, gaze=(0.1, -0.05), phase=2.8, char_size=10)
    draw.text((eye_x + 14, eye_y + eye_h - 22), "HAREKETLİ ASCII SİBER GÖZ // 30 FPS", font=f_mono_xs, fill=C_MUTED)

    # Right: Branding & Feature Highlights
    rx = 560
    draw.text((rx, 80), "SYS.2.3 // NEON HUD", font=f_mono_sm, fill=C_CYAN)
    draw.text((rx, 115), "RIFKI", font=f_sans_hero, fill=(255, 255, 255))
    draw.text((rx + 240, 142), "// SİBER ASİSTAN", font=f_mono_md, fill=C_CYAN)
    draw.text((rx, 220), "Masaüstü & Mobil Yapay Zekâ Kokpiti", font=f_sans_md, fill=C_TEXT)
    draw.text((rx, 268), "Türkçe sesli komutlar, hareketli ASCII siber göz,", font=f_sans_sm, fill=C_MUTED)
    draw.text((rx, 300), "gelişmiş uzaktan kontrol ve anlık donanım telemetrisi.", font=f_sans_sm, fill=C_MUTED)

    # Feature badges
    pills = ["👁️ Siber Göz", "🎙️ Sesli Komut", "🎮 Uzaktan Kontrol", "📊 Canlı Telemetri"]
    px = rx
    py = 370
    for p in pills:
        draw.rectangle([px, py, px + 195, py + 46], fill=(12, 28, 42), outline=C_CYAN, width=1)
        draw.text((px + 97, py + 23), p, font=f_mono_xs, fill=C_CYAN_VIVID, anchor="mm")
        px += 205
        if px > 980:
            px = rx
            py += 56

    path = OUT_DIR / "rifki-feature-1024x500.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-feature-1024x500.png", "PNG")
    print(f"Generated {path}")

# ==============================================================================
# Helper: Base Phone Mockup (1080x1920)
# ==============================================================================
def create_phone_base(headline, subheadline):
    img = Image.new("RGBA", (1080, 1920), C_BG_DEEP)
    draw = ImageDraw.Draw(img)

    # Background ambient glow & grid
    for x in range(0, 1080, 60):
        draw.line([(x, 0), (x, 1920)], fill=(8, 20, 32, 50), width=1)
    for y in range(0, 1920, 60):
        draw.line([(0, y), (1080, y)], fill=(8, 20, 32, 50), width=1)

    draw_corner_brackets(draw, 24, 24, 1056, 1896, length=40, color=C_CYAN, width=3)

    # Kicker
    draw.text((540, 80), "RIFKI SİBER KOKPİT // ANDROID", font=f_mono_sm, fill=C_CYAN, anchor="mm")
    draw.text((540, 140), headline, font=f_sans_xl, fill=(255, 255, 255), anchor="mm")
    draw.text((540, 200), subheadline, font=f_sans_sm, fill=C_MUTED, anchor="mm")

    # Phone Frame
    px0, py0, px1, py1 = 80, 260, 1000, 1840
    draw.rectangle([px0, py0, px1, py1], fill=(4, 9, 16), outline=(40, 80, 110), width=3)
    draw_corner_brackets(draw, px0 + 8, py0 + 8, px1 - 8, py1 - 8, length=24, color=C_CYAN, width=2)

    # Phone Status Bar
    draw.text((px0 + 40, py0 + 30), "12:45", font=f_mono_sm, fill=C_MUTED)
    draw.text((px1 - 40, py0 + 30), "📶 5G  🔋 96%", font=f_mono_sm, fill=C_MUTED, anchor="ra")

    # App Header inside phone
    hy = py0 + 80
    draw.text((px0 + 40, hy), "SYS.2.3", font=f_mono_xs, fill=C_CYAN)
    draw.text((px0 + 40, hy + 24), "RIFKI // SİBER KÖPRÜ", font=f_sans_md, fill=(255, 255, 255))
    # State badge
    draw.rectangle([px1 - 200, hy + 10, px1 - 40, hy + 50], fill=(10, 26, 38), outline=C_CYAN, width=1)
    draw.text((px1 - 120, hy + 30), "• IDLE", font=f_mono_sm, fill=C_CYAN, anchor="mm")

    return img, draw, px0, py0, px1, py1

# ==============================================================================
# 3. SCREENSHOT 1: ONBOARDING / QR PAIRING (1080x1920)
# ==============================================================================
def generate_shot_1_onboarding():
    img, draw, px0, py0, px1, py1 = create_phone_base(
        "KOLAY QR EŞLEŞTİRME",
        "Bilgisayarındaki RIFKI'ye tek tıkla şifresiz bağlan"
    )

    # Onboarding Hero
    card_x0, card_y0 = px0 + 60, py0 + 200
    card_x1, card_y1 = px1 - 60, py1 - 100
    draw.rectangle([card_x0, card_y0, card_x1, card_y1], fill=C_CARD, outline=(40, 80, 110), width=2)
    draw_corner_brackets(draw, card_x0, card_y0, card_x1, card_y1, length=20, color=C_CYAN)

    # Icon / Reactor
    render_ascii_eye(draw, card_x0 + 40, card_y0 + 60, card_x1 - card_x0 - 80, 320, state="IDLE", gaze=(0.0, 0.0), phase=1.0, char_size=12)

    cy = card_y0 + 440
    draw.text((540, cy), "BİLGİSAYARINA BAĞLAN", font=f_sans_lg, fill=(255, 255, 255), anchor="mm")
    draw.text((540, cy + 60), "Masaüstünde çalışan RIFKI'nin sistem tepsisindeki", font=f_sans_sm, fill=C_MUTED, anchor="mm")
    draw.text((540, cy + 96), "«Mobil Bağlantı» QR kodunu telefon kamerasıyla tara.", font=f_sans_sm, fill=C_MUTED, anchor="mm")

    # QR Scan Button
    btn_y = cy + 180
    draw.rectangle([card_x0 + 80, btn_y, card_x1 - 80, btn_y + 90], fill=C_CYAN, outline=None)
    draw.text((540, btn_y + 45), "📷  QR KOD TARA", font=f_sans_md, fill=(2, 6, 12), anchor="mm")

    # Manual connection hint
    draw.text((540, btn_y + 140), "veya erişim tokeni ile elle bağlan", font=f_mono_xs, fill=C_CYAN, anchor="mm")

    # Feature List
    fy = btn_y + 220
    features = [
        "🔒 Uçtan Uca Şifreli Yerel / Tünel Bağlantısı",
        "⚡ Otomatik Ağ Taraması & Hızlı Eşleşme",
        "🖥️ Masaüstüyle Tam Senkronize Siber Göz",
    ]
    for feat in features:
        draw.rectangle([card_x0 + 60, fy, card_x1 - 60, fy + 70], fill=C_CARD_LIGHT, outline=(30, 60, 90), width=1)
        draw.text((540, fy + 35), feat, font=f_sans_sm, fill=C_TEXT, anchor="mm")
        fy += 90

    path = OUT_DIR / "rifki-phone-1-onboarding-1080x1920.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-phone-1-onboarding-1080x1920.png", "PNG")
    print(f"Generated {path}")

# ==============================================================================
# 4. SCREENSHOT 2: SİBER GÖZ & TELEMETRİ (1080x1920)
# ==============================================================================
def generate_shot_2_panel():
    img, draw, px0, py0, px1, py1 = create_phone_base(
        "HAREKETLİ SİBER GÖZ & TELEMETRİ",
        "Dokunmatik bakış takibi, canlı CPU/RAM oranları ve terminal"
    )

    # Telemetry Ribbon inside phone
    ty = py0 + 170
    draw.rectangle([px0 + 40, ty, px1 - 40, ty + 90], fill=C_CARD, outline=C_LINE, width=1)
    telems = [("CPU", "24%", 24), ("RAM", "48%", 48), ("DSK", "94%", 94), ("PIL", "96%⚡", 96)]
    tw = (px1 - px0 - 80) / 4
    for i, (k, v, pct) in enumerate(telems):
        tx = px0 + 40 + i * tw + tw / 2
        draw.text((tx, ty + 20), k, font=f_mono_xs, fill=C_MUTED, anchor="mm")
        draw.text((tx, ty + 46), v, font=f_mono_sm, fill=C_CYAN, anchor="mm")
        bx0, bx1 = tx - 36, tx + 36
        draw.rectangle([bx0, ty + 68, bx1, ty + 74], fill=(20, 40, 60))
        draw.rectangle([bx0, ty + 68, bx0 + (bx1 - bx0) * (pct / 100), ty + 74], fill=C_CYAN)

    # ASCII Cyber Eye Reactor
    ey = ty + 110
    ew = px1 - px0 - 80
    eh = 400
    draw.rectangle([px0 + 40, ey, px1 - 40, ey + eh], fill=(1, 3, 7), outline=(40, 80, 110), width=2)
    draw_corner_brackets(draw, px0 + 40, ey, px1 - 40, ey + eh, length=24, color=C_CYAN, width=2)
    draw.text((px0 + 60, ey + 18), "[ OPTIC.MATRIX // CORE.01 ]", font=f_mono_xs, fill=C_CYAN)
    draw.text((px1 - 60, ey + 18), "HAZIR // BEKLEMEDE", font=f_mono_xs, fill=C_CYAN, anchor="ra")
    render_ascii_eye(draw, px0 + 50, ey + 45, ew - 20, eh - 80, state="IDLE", gaze=(0.15, -0.1), phase=1.8, char_size=12)
    draw.text((px0 + 60, ey + eh - 24), "Göz bakışı dokunmayı takip eder", font=f_mono_xs, fill=C_MUTED)
    draw.text((px1 - 60, ey + eh - 24), "30 FPS", font=f_mono_xs, fill=C_CYAN, anchor="ra")

    # Quick prompt chips
    cy = ey + eh + 20
    chips = ["📊 Rapor Ver", "📸 Ekran Al", "🔊 Ses %50", "🎵 Spotify"]
    cx = px0 + 40
    for ch in chips:
        draw.rectangle([cx, cy, cx + 180, cy + 48], fill=C_CARD, outline=C_LINE, width=1)
        draw.text((cx + 90, cy + 24), ch, font=f_mono_xs, fill=C_CYAN_VIVID, anchor="mm")
        cx += 195

    # Terminal Log
    ly = cy + 70
    lh = 360
    draw.rectangle([px0 + 40, ly, px1 - 40, ly + lh], fill=(1, 3, 7), outline=C_LINE, width=1)
    draw.text((px0 + 60, ly + 20), "TERMINAL // LOG", font=f_mono_xs, fill=C_CYAN)
    draw.text((px1 - 60, ly + 20), "CANLI WS", font=f_mono_xs, fill=C_GREEN, anchor="ra")

    # Chat messages
    my = ly + 60
    # User msg
    draw.text((px1 - 60, my), "KULLANICI", font=f_mono_xs, fill=C_CYAN, anchor="ra")
    draw.rectangle([px0 + 160, my + 20, px1 - 60, my + 80], fill=(12, 36, 54), outline=C_CYAN, width=1)
    draw.text((px0 + 180, my + 50), "Rıfkı, durum raporu ver ve siber gözü aç.", font=f_sans_sm, fill=C_TEXT, anchor="lm")

    # Assistant msg
    my += 100
    draw.text((px0 + 60, my), "RIFKI", font=f_mono_xs, fill=C_GREEN)
    draw.rectangle([px0 + 60, my + 20, px1 - 160, my + 100], fill=(8, 30, 24), outline=C_GREEN, width=1)
    draw.text((px0 + 80, my + 45), "Tüm sistemler devrede, Komutanım.", font=f_sans_sm, fill=C_TEXT)
    draw.text((px0 + 80, my + 72), "ASCII Siber Göz aktif ve komutlarını bekliyorum.", font=f_sans_sm, fill=C_TEXT)

    # Bottom Composer Dock
    dock_y = py1 - 130
    draw.rectangle([px0 + 20, dock_y, px1 - 20, py1 - 20], fill=(2, 6, 12), outline=C_LINE, width=1)
    # Mic button
    draw.ellipse([px0 + 40, dock_y + 15, px0 + 110, dock_y + 85], fill=C_CARD_LIGHT, outline=C_CYAN, width=2)
    draw.text((px0 + 75, dock_y + 50), "🎙️", font=f_sans_md, fill=C_CYAN, anchor="mm")
    # Input field
    draw.rectangle([px0 + 130, dock_y + 15, px1 - 120, dock_y + 85], fill=(7, 16, 24), outline=C_LINE, width=1)
    draw.text((px0 + 160, dock_y + 50), "Komut yaz veya mikrofona dokun…", font=f_sans_sm, fill=C_MUTED, anchor="lm")
    # Send button
    draw.ellipse([px1 - 100, dock_y + 15, px1 - 30, dock_y + 85], fill=C_CYAN)
    draw.text((px1 - 65, dock_y + 50), "➤", font=f_sans_md, fill=(2, 6, 12), anchor="mm")

    path = OUT_DIR / "rifki-phone-2-panel-1080x1920.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-phone-2-panel-1080x1920.png", "PNG")
    print(f"Generated {path}")

# ==============================================================================
# 5. SCREENSHOT 3: UZAKTAN KONTROL & DONANIM (1080x1920)
# ==============================================================================
def generate_shot_3_remote():
    img, draw, px0, py0, px1, py1 = create_phone_base(
        "GELİŞMİŞ UZAKTAN KONTROL",
        "Dokunmatik ses slider'ı, medya oynatıcı, kilit ve pano senkronu"
    )

    y = py0 + 170

    # 1. Ses Kontrolü Kartı
    draw.rectangle([px0 + 40, y, px1 - 40, y + 210], fill=C_CARD, outline=C_LINE, width=1)
    draw.text((px0 + 60, y + 20), "🔊 Ses Düzeyi", font=f_sans_md, fill=(255, 255, 255))
    draw.text((px1 - 60, y + 20), "Ses: %65", font=f_mono_sm, fill=C_CYAN, anchor="ra")

    # Slider
    draw.rectangle([px0 + 60, y + 80, px1 - 60, y + 92], fill=(20, 40, 60))
    slider_fill = (px1 - px0 - 120) * 0.65
    draw.rectangle([px0 + 60, y + 80, px0 + 60 + slider_fill, y + 92], fill=C_CYAN)
    draw.ellipse([px0 + 50 + slider_fill, y + 70, px0 + 74 + slider_fill, y + 102], fill=C_CYAN)

    # Nudge buttons
    bx = px0 + 60
    for b_label in ["−10", "%30", "%50", "%80", "+10"]:
        draw.rectangle([bx, y + 130, bx + 140, y + 185], fill=C_CARD_LIGHT, outline=C_LINE, width=1)
        draw.text((bx + 70, y + 158), b_label, font=f_mono_xs, fill=C_TEXT, anchor="mm")
        bx += 155

    # 2. Medya Oynatıcı Kartı
    y += 230
    draw.rectangle([px0 + 40, y, px1 - 40, y + 160], fill=C_CARD, outline=C_LINE, width=1)
    draw.text((px0 + 60, y + 20), "🎵 Medya Oynatıcı", font=f_sans_md, fill=(255, 255, 255))
    m_btns = ["⏮ Önceki", "▶/❚❚ Oynat", "⏭ Sonraki", "⏹ Durdur"]
    mx = px0 + 60
    for mb in m_btns:
        is_pri = "Oynat" in mb
        fill_col = (18, 50, 70) if is_pri else C_CARD_LIGHT
        out_col = C_CYAN if is_pri else C_LINE
        draw.rectangle([mx, y + 70, mx + 180, y + 135], fill=fill_col, outline=out_col, width=1)
        draw.text((mx + 90, y + 102), mb, font=f_mono_xs, fill=C_CYAN_VIVID if is_pri else C_TEXT, anchor="mm")
        mx += 195

    # 3. Ekran & Sistem Güç Kartı
    y += 180
    draw.rectangle([px0 + 40, y, px1 - 40, y + 270], fill=C_CARD, outline=C_LINE, width=1)
    draw.text((px0 + 60, y + 20), "🖥️ Ekran & Sistem Gücü", font=f_sans_md, fill=(255, 255, 255))
    p_grid = [
        ("📸 Ekran Resmi", C_TEXT),
        ("🌙 Monitörü Kapat", C_CYAN),
        ("🔒 Ekranı Kilitle", C_TEXT),
        ("💤 Uyku Modu", C_AMBER),
        ("⛔ Bilgisayarı Kapat", (255, 107, 107)),
        ("🔄 Yeniden Başlat", C_AMBER),
    ]
    gx = px0 + 60
    gy = y + 70
    for i, (p_text, p_col) in enumerate(p_grid):
        draw.rectangle([gx, gy, gx + 245, gy + 75], fill=C_CARD_LIGHT, outline=C_LINE, width=1)
        draw.text((gx + 122, gy + 37), p_text, font=f_mono_xs, fill=p_col, anchor="mm")
        gx += 265
        if (i + 1) % 3 == 0:
            gx = px0 + 60
            gy += 90

    # 4. Kısayol Tuşları Kartı
    y += 290
    draw.rectangle([px0 + 40, y, px1 - 40, y + 210], fill=C_CARD, outline=C_LINE, width=1)
    draw.text((px0 + 60, y + 20), "⌨️ PC Kısayol Tuşları", font=f_sans_md, fill=(255, 255, 255))
    keys = ["🔀 Alt+Tab", "💻 Win+D", "Esc", "Space", "Enter", "⊞ Win"]
    kx = px0 + 60
    ky = y + 70
    for i, k_name in enumerate(keys):
        draw.rectangle([kx, ky, kx + 245, ky + 55], fill=C_CARD_LIGHT, outline=C_LINE, width=1)
        draw.text((kx + 122, ky + 27), k_name, font=f_mono_xs, fill=C_CYAN, anchor="mm")
        kx += 265
        if (i + 1) % 3 == 0:
            kx = px0 + 60
            ky += 68

    # 5. Pano Senkronizasyonu
    y += 230
    draw.rectangle([px0 + 40, y, px1 - 40, y + 200], fill=C_CARD, outline=C_LINE, width=1)
    draw.text((px0 + 60, y + 20), "📋 Pano Senkronizasyonu", font=f_sans_md, fill=(255, 255, 255))
    draw.rectangle([px0 + 60, y + 65, px1 - 60, y + 115], fill=(1, 3, 7), outline=C_LINE, width=1)
    draw.text((px0 + 80, y + 90), "https://github.com/BatuhanKlcky...", font=f_mono_xs, fill=C_MUTED, anchor="lm")

    draw.rectangle([px0 + 60, y + 130, px0 + 380, y + 180], fill=C_CARD_LIGHT, outline=C_CYAN, width=1)
    draw.text((px0 + 220, y + 155), "📋 PC Panosuna Kopyala", font=f_mono_xs, fill=C_CYAN, anchor="mm")
    draw.rectangle([px0 + 400, y + 130, px1 - 60, y + 180], fill=C_CYAN, outline=None)
    draw.text((px0 + 610, y + 155), "⌨️ PC Penceresine Yaz", font=f_mono_xs, fill=(2, 6, 12), anchor="mm")

    path = OUT_DIR / "rifki-phone-3-remote-1080x1920.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-phone-3-remote-1080x1920.png", "PNG")
    print(f"Generated {path}")

# ==============================================================================
# 6. SCREENSHOT 4: SES İLE DİNAMİK MORF (1080x1920)
# ==============================================================================
def generate_shot_4_speaking():
    img, draw, px0, py0, px1, py1 = create_phone_base(
        "SES İLE ŞEKİL DEĞİŞTİREN MORF",
        "Konuşurken altıgen diyaframa, sonar dalgalarına ve ekolayzıra dönüşür"
    )

    # State Badge in header updated to SPEAKING
    hy = py0 + 80
    draw.rectangle([px1 - 250, hy + 10, px1 - 40, hy + 50], fill=(14, 40, 58), outline=C_CYAN_VIVID, width=2)
    draw.text((px1 - 145, hy + 30), "• SPEAKING", font=f_mono_sm, fill=C_CYAN_VIVID, anchor="mm")

    # Speaking Hero Box
    ey = py0 + 170
    ew = px1 - px0 - 80
    eh = 540
    draw.rectangle([px0 + 40, ey, px1 - 40, ey + eh], fill=(1, 3, 7), outline=C_CYAN_VIVID, width=2)
    draw_corner_brackets(draw, px0 + 40, ey, px1 - 40, ey + eh, length=28, color=C_CYAN_VIVID, width=3)
    draw.text((px0 + 60, ey + 20), "[ OPTIC.MATRIX // MORPH.ACTIVE ]", font=f_mono_xs, fill=C_CYAN_VIVID)
    draw.text((px1 - 60, ey + 20), "KONUŞUYOR // SES MORFU", font=f_mono_xs, fill=C_CYAN_VIVID, anchor="ra")

    # Render Full Speaking Morph
    render_ascii_eye(draw, px0 + 50, ey + 50, ew - 20, eh - 100, state="SPEAKING", morph_weight=0.95, gaze=(0.08, -0.04), phase=3.4, char_size=13)
    draw.text((px0 + 60, ey + eh - 28), "Aperture blades + sonar ripples + equalizer active", font=f_mono_xs, fill=C_MUTED)
    draw.text((px1 - 60, ey + eh - 28), "30 FPS", font=f_mono_xs, fill=C_CYAN_VIVID, anchor="ra")

    # Speaking Subtitle banner
    sy = ey + eh + 25
    draw.rectangle([px0 + 40, sy, px1 - 40, sy + 130], fill=(10, 28, 42), outline=C_CYAN_VIVID, width=1)
    draw.text((540, sy + 38), "🔊 RIFKI SESLİ YANIT VERİYOR", font=f_sans_md, fill=C_CYAN_VIVID, anchor="mm")
    draw.text((540, sy + 85), "«Masaüstü kontrolleri hazır, istediğiniz müziği başlatıyorum.»", font=f_sans_sm, fill=C_TEXT, anchor="mm")

    # Voice Input Feature Card
    vy = sy + 160
    draw.rectangle([px0 + 40, vy, px1 - 40, vy + 400], fill=C_CARD, outline=C_LINE, width=1)
    draw_corner_brackets(draw, px0 + 40, vy, px1 - 40, vy + 400, length=20, color=C_GREEN)
    draw.text((540, vy + 45), "🎙️ TELEFONDAN SESLE KOMUT", font=f_sans_lg, fill=C_GREEN, anchor="mm")
    draw.text((540, vy + 100), "Web Speech entegrasyonu sayesinde telefon mikrofonuna", font=f_sans_sm, fill=C_TEXT, anchor="mm")
    draw.text((540, vy + 135), "dokunup Türkçe konuştuğunuz anda komutunuz PC'ye iletilir.", font=f_sans_sm, fill=C_TEXT, anchor="mm")

    # Big Mic icon with glowing pulse rings
    mcx, mcy = 540, vy + 260
    draw.ellipse([mcx - 70, mcy - 70, mcx + 70, mcy + 70], outline=(61, 255, 176, 80), width=2)
    draw.ellipse([mcx - 55, mcy - 55, mcx + 55, mcy + 55], outline=C_GREEN, width=3)
    draw.ellipse([mcx - 45, mcy - 45, mcx + 45, mcy + 45], fill=(15, 45, 35))
    draw.text((mcx, mcy), "🎙️", font=f_sans_hero, fill=C_GREEN, anchor="mm")
    draw.text((mcx, vy + 360), "DİNLİYOR // TÜRKÇE SES TANIMA AKTİF", font=f_mono_xs, fill=C_GREEN, anchor="mm")

    path = OUT_DIR / "rifki-phone-4-speaking-1080x1920.png"
    img.save(path, "PNG")
    if DL_DIR.exists(): img.save(DL_DIR / "rifki-phone-4-speaking-1080x1920.png", "PNG")
    print(f"Generated {path}")

if __name__ == "__main__":
    generate_icon()
    generate_feature()
    generate_shot_1_onboarding()
    generate_shot_2_panel()
    generate_shot_3_remote()
    generate_shot_4_speaking()
    print("ALL PLAY ASSETS GENERATED SUCCESSFULLY!")
