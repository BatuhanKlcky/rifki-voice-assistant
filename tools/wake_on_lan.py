"""
tools/wake_on_lan.py
---------------------
Wake-on-LAN (WoL) sihirli paket (Magic Packet) oluşturucu ve ağ arayüzü yöneticisi.
Ağdaki cihazları uyandırmak ve bu bilgisayarın WoL yapılandırmasını yönetmek için kullanılır.
"""

from __future__ import annotations

import re
import socket
from typing import Optional

import psutil

from core.logger import get_logger

log = get_logger("tools.wol")


def get_primary_mac_and_ip() -> tuple[Optional[str], Optional[str]]:
    """Aktif yerel ağ arayüzünün MAC adresini ve IPv4 adresini bulur."""
    best_mac = None
    best_ip = None

    for iface, addrs in psutil.net_if_addrs().items():
        mac = None
        ipv4 = None
        for a in addrs:
            if a.family == psutil.AF_LINK:
                mac = a.address
            elif getattr(a, "family", None) == socket.AF_INET and not a.address.startswith("127."):
                ipv4 = a.address

        if mac and ipv4 and not ipv4.startswith("169.254."):
            # Geçerli yerel IP (192.168.x.x, 10.x.x.x vb.)
            return mac.upper().replace("-", ":"), ipv4

        if mac and ipv4 and not best_mac:
            best_mac = mac.upper().replace("-", ":")
            best_ip = ipv4

    return best_mac, best_ip


def send_magic_packet(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> bool:
    """
    Belirtilen MAC adresine Wake-on-LAN sihirli paketini (102 byte) UDP yayını olarak gönderir.
    Format: 6 bayt 0xFF + 16 tekrar MAC baytı.
    """
    clean_mac = re.sub(r"[^0-9A-Fa-f]", "", mac_address)
    if len(clean_mac) != 12:
        raise ValueError(f"Geçersiz MAC adresi formatı: '{mac_address}'")

    mac_bytes = bytes.fromhex(clean_mac)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (broadcast_ip, port))

    log.info(f"Wake-on-LAN sihirli paketi gönderildi -> MAC: {mac_address}, Hedef: {broadcast_ip}:{port}")
    return True


def wake_device(target: str = "pc", *args, **kwargs) -> str:
    """
    Ağdaki bir cihazı veya sunucuyu uyandırmak için Wake-on-LAN paketi gönderir.
    Hedef MAC adresi veya 'bu bilgisayar' olabilir.
    """
    target = (target or "").strip()
    mac, ip = get_primary_mac_and_ip()

    target_mac = None
    if re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", target):
        target_mac = target
    elif any(k in target.lower() for k in ("pc", "bilgisayar", "bu", "kendim")):
        target_mac = mac
    else:
        target_mac = target if len(re.sub(r"[^0-9A-Fa-f]", "", target)) == 12 else mac

    if not target_mac:
        return "Uyandırılacak geçerli bir MAC adresi bulunamadı."

    try:
        send_magic_packet(target_mac)
        return f"Wake-on-LAN paketi başarıyla gönderildi (MAC: {target_mac})."
    except Exception as e:
        log.error(f"WoL gönderme hatası: {e}")
        return f"Sihirli paket gönderilemedi: {e}"


def get_wake_on_lan_info(*args, **kwargs) -> str:
    """Bu bilgisayarın Wake-on-LAN için gereken MAC adresini ve ağ bilgilerini döndürür."""
    mac, ip = get_primary_mac_and_ip()
    if not mac:
        return "Aktif bir ağ kartı ve MAC adresi tespit edilemedi."

    return (
        f"Bilgisayar Ağ Bilgisi -> MAC Adresi: {mac}, Yerel IP: {ip}. "
        f"Telefondan veya başka bir cihazdan bu bilgisayarı uzaktan uyandırmak için "
        f"BIOS ve Aygıt Yöneticisi'nde 'Wake on Magic Packet' özelliğinin açık olduğundan emin olun."
    )
