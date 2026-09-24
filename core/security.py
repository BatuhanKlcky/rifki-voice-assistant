"""
core/security.py
-----------------
Geri dönüşü zor / riskli işlemler için onay mekanizması.

Tasarım:
- Her tool fonksiyonu, tools/ içinde TOOL_SCHEMAS listesinde
  "requires_confirmation": True/False alanıyla işaretlenir.
- Router bir tool çağırmadan önce bu bayrağa bakar.
- True ise, işlemi hemen yapmaz; kullanıcıya (UI/ses üzerinden) bir onay
  sorusu sorulur ve işlem yalnızca "evet/onaylıyorum" gibi bir yanıt
  geldiğinde gerçekleştirilir.

Bu modül UI'dan bağımsızdır: confirm() fonksiyonuna dışarıdan bir
"soru sorma" callback'i (ör. UI'da bir onay diyaloğu açan fonksiyon) verilir.
Callback verilmezse (ör. saf CLI/test ortamı) terminal input() kullanılır.
"""

from typing import Callable, Optional
from core.logger import get_logger

log = get_logger("security")

CRITICAL_ACTIONS = {
    "shutdown_computer",
    "restart_computer",
    "delete_file",
    "delete_folder",
    "bulk_modify_files",
    "change_system_settings",
    "uninstall_program",
    "send_email",
    "send_message",
}

_YES_WORDS = {"evet", "onaylıyorum", "tamam", "onayla", "yes", "olur"}


def is_critical(action_name: str) -> bool:
    return action_name in CRITICAL_ACTIONS


def confirm(
    prompt: str,
    ask_fn: Optional[Callable[[str], str]] = None,
) -> bool:
    """
    Kullanıcıdan onay ister.

    ask_fn: Dışarıdan (UI veya sesli asistan döngüsünden) verilen,
            bir soruyu kullanıcıya ileten ve cevabını string olarak
            döndüren fonksiyon. Verilmezse konsoldan input() ile sorulur
            (yalnızca geliştirme/test amaçlı fallback).
    """
    log.info(f"Onay isteniyor: {prompt}")
    if ask_fn is not None:
        answer = ask_fn(prompt)
    else:
        answer = input(f"[ONAY GEREKLİ] {prompt} (evet/hayır): ")

    approved = answer.strip().lower() in _YES_WORDS
    log.info(f"Onay sonucu: {approved} (kullanıcı cevabı: {answer!r})")
    return approved