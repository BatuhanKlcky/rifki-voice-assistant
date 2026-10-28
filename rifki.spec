# -*- mode: python ; coding: utf-8 -*-
"""RIFKI masaüstü asistanını klasörlü bir exe olarak paketler."""

import inspect
from pathlib import Path

import PyInstaller.building.build_main as build_main
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# PyInstaller DLL taraması PyQt5'i piper/onnxruntime'dan önce import ediyor.
# Bu sırada onnxruntime Windows'ta access violation ile süreci öldürüyor.
# Piper'ı Qt'tan önce yükleyince hem tarama hem uygulamanın kendi açılışı sağlam.
_src = inspect.getsource(build_main.find_binary_dependencies)
_old = "        import_packages = qt_packages + other_packages"
_new = """        early = [
            p for p in other_packages
            if p == "numpy" or p.startswith("numpy.")
            or p == "onnxruntime" or p.startswith("onnxruntime.")
            or p == "piper" or p.startswith("piper.")
        ]
        other_packages = [p for p in other_packages if p not in early]
        import_packages = early + qt_packages + other_packages"""
if _old not in _src:
    raise SystemExit("PyInstaller import sırası yaması artık uymuyor.")
exec(_src.replace(_old, _new, 1), build_main.__dict__)

datas = collect_data_files("piper")
binaries = collect_dynamic_libs("piper")
datas += [(str(Path(SPECPATH) / "bridge" / "static"), "bridge/static")]
_cf = Path(SPECPATH) / "tools" / "cloudflared.exe"
if _cf.is_file():
    datas += [(str(_cf), "tools")]

hiddenimports = [
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "PyQt5",
    "PyQt5.sip",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "speech_recognition",
    "pyaudio",
    "edge_tts",
    "gtts",
    "pyttsx3",
    "psutil",
    "dotenv",
    "duckduckgo_search",
    "PIL",
    "pyautogui",
    "comtypes",
    "comtypes.client",
    "pycaw",
    "pycaw.pycaw",
    "win10toast",
    "onnxruntime",
    "piper",
    "piper.voice",
    "piper.config",
    "requests",
    "aiohttp",
    "bridge",
    "bridge.service",
    "bridge.pairing",
    "bridge.remote_actions",
    "core.version",
    "core.updater",
    "tools.media",
    "tools.vision",
    "qrcode",
    "qrcode.image.pil",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["hooks/rthook_piper_before_qt.py"],
    excludes=[
        "torch",
        "tensorflow",
        "tensorboard",
        "matplotlib",
        "notebook",
        "IPython",
        "piper.train",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RIFKI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(Path(SPECPATH) / "assets" / "rifki.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="RIFKI",
)

# .env ve Piper modelleri paketin içine gömülmez; exe'nin yanında durur.
import shutil

_root = Path(SPECPATH)
_dest = Path(DISTPATH) / "RIFKI"
_env = _root / ".env"
if _env.is_file():
    shutil.copy2(_env, _dest / ".env")
_models = _root / "voice" / "piper_models"
_model_dest = _dest / "voice" / "piper_models"
_model_dest.mkdir(parents=True, exist_ok=True)
for _pattern in ("*.onnx", "*.onnx.json"):
    for _src in _models.glob(_pattern):
        shutil.copy2(_src, _model_dest / _src.name)
