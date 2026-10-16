"""PyInstaller runtime hook: load Piper before PyQt5.

Windows kills the process (access violation) if onnxruntime is imported
after PyQt5, or for the first time on a background thread. This hook runs
before PyInstaller's Qt hook and before main.py.

İkinci kopya Piper yüklemeden çıkar; aksi halde çift tıklama saniyelerce
sessiz kalır.
"""

import os
import sys

from core.single_instance import acquire_single_instance, notify_already_running

if not acquire_single_instance():
    notify_already_running()
    os._exit(0)

import faulthandler

_log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
os.makedirs(_log_dir, exist_ok=True)
_fault_file = open(os.path.join(_log_dir, "fault.log"), "w", buffering=1)
faulthandler.enable(file=_fault_file, all_threads=True)

import onnxruntime  # noqa: E402,F401
import piper  # noqa: E402,F401
