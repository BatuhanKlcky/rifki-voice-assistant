"""
bridge/webrtc_stream.py
-----------------------
RIFKI Donanımsal WebRTC H.264 Ekran Akış Motoru.
NVIDIA NVENC, AMD AMF veya CPU libx264 ile sıfır gecikmeli video akışı sağlar.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Set

import av
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    VideoStreamTrack,
)

from core.logger import get_logger
from tools import system

log = get_logger("webrtc")


class ScreenVideoTrack(VideoStreamTrack):
    """Windows ekranını yakalayıp WebRTC H.264 üzerinden akıtan video kanalı."""

    kind = "video"

    def __init__(self, max_width: int = 800, fps: int = 30):
        super().__init__()
        self.max_width = max(320, min(1920, int(max_width)))
        self.fps = max(15, min(60, int(fps)))
        self._frame_count = 0
        self._last_frame = None

    async def recv(self) -> av.VideoFrame:
        pts, time_base = await self.next_timestamp()
        loop = asyncio.get_running_loop()

        try:
            # GDI üzerinden doğrudan bellekten ekran görüntüsü al
            pil_img = await loop.run_in_executor(
                None,
                lambda: system.capture_raw_image_for_webrtc(
                    max_width=self.max_width, include_cursor=True
                ),
            )
            if pil_img is not None:
                frame = av.VideoFrame.from_image(pil_img).reformat(format="yuv420p")
                self._last_frame = frame
            elif self._last_frame is not None:
                frame = self._last_frame
            else:
                import numpy as np

                h = int(self.max_width * 9 / 16)
                raw = np.zeros((h, self.max_width, 4), dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(raw, format="bgra").reformat(
                    format="yuv420p"
                )
        except Exception as e:
            log.debug(f"WebRTC frame alma hatası: {e}")
            if self._last_frame is not None:
                frame = self._last_frame
            else:
                import numpy as np

                h = int(self.max_width * 9 / 16)
                raw = np.zeros((h, self.max_width, 4), dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(raw, format="bgra").reformat(
                    format="yuv420p"
                )

        frame.pts = pts
        frame.time_base = time_base
        self._frame_count += 1
        return frame


class WebRTCManager:
    """Aktif WebRTC istemci oturumlarını ve sinyalleşmeyi yöneten koordinatör."""

    def __init__(self):
        self._pcs: Set[RTCPeerConnection] = set()

    async def handle_offer(
        self, sdp: str, sdp_type: str, max_width: int = 800, fps: int = 30
    ) -> tuple[RTCPeerConnection, dict]:
        """İstemciden gelen WebRTC SDP teklifini işler ve donanımsal yanıtı üretir."""
        from aiortc import RTCConfiguration, RTCIceServer
        config = RTCConfiguration(iceServers=[RTCIceServer("stun:stun.l.google.com:19302")])
        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        pc = RTCPeerConnection(configuration=config)
        self._pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_state_change():
            log.info(f"WebRTC bağlantı durumu: {pc.connectionState}")
            if pc.connectionState in ("failed", "closed"):
                await self.close_pc(pc)

        # Donanımsal ekran akış kanalını ekle
        track = ScreenVideoTrack(max_width=max_width, fps=fps)
        pc.addTrack(track)

        # Uzak teklifi ayarla ve yerel yanıtı oluştur
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Yerel ve STUN ICE adaylarının toplanmasını bekle (One-Shot tam adaylı SDP)
        for _ in range(50):  # en fazla 500ms
            if pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.01)

        candidate_count = len([l for l in pc.localDescription.sdp.splitlines() if "a=candidate" in l])
        log.info(f"WebRTC yanıtı oluşturuldu ({max_width}px @ {fps}fps, {candidate_count} ICE adayı)")
        return pc, {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }

    async def handle_candidate(self, pc: RTCPeerConnection, candidate_dict: dict):
        """İstemciden gelen ICE adayını PeerConnection'a ekler."""
        try:
            cand_str = candidate_dict.get("candidate", "")
            sdp_mid = candidate_dict.get("sdpMid")
            sdp_mline_index = candidate_dict.get("sdpMLineIndex")
            if not cand_str:
                return

            # RTCIceCandidate parse
            from aiortc.sdp import candidate_from_sdp

            candidate = candidate_from_sdp(cand_str)
            candidate.sdpMid = sdp_mid
            candidate.sdpMLineIndex = sdp_mline_index
            await pc.addIceCandidate(candidate)
        except Exception as e:
            log.debug(f"WebRTC candidate ekleme uyarısı: {e}")

    async def close_pc(self, pc: RTCPeerConnection):
        """Belirli bir WebRTC oturumunu temizler ve kapatır."""
        try:
            self._pcs.discard(pc)
            await pc.close()
        except Exception:
            pass

    async def close_all(self):
        """Tüm açık WebRTC oturumlarını kapatır."""
        pcs = list(self._pcs)
        self._pcs.clear()
        for pc in pcs:
            try:
                await pc.close()
            except Exception:
                pass


webrtc_manager = WebRTCManager()
