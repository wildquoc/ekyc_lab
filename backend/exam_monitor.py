"""Cảnh báo theo dõi ánh mắt / tư thế đầu khi làm bài thi."""
from __future__ import annotations

from typing import Any, Dict, Optional

from face_analyzer import FaceResult

YAW_AWAY = 20.0
PITCH_DOWN = 16.0
PITCH_UP = 22.0
GAZE_X = 0.38
GAZE_Y_DOWN = 0.42
EAR_CLOSED = 0.17


def assess_exam(face: Optional[FaceResult]) -> Dict[str, Any]:
    """Trả về mức cảnh báo và câu hướng dẫn tiếng Anh cho HUD thi."""
    if face is None or face.face_count <= 0 or not face.detected:
        return {
            "ok": False,
            "level": "red",
            "code": "no_face",
            "message": "Face not found. Stay in view.",
        }
    if face.face_count > 1:
        return {
            "ok": False,
            "level": "red",
            "code": "multiple_faces",
            "message": "Only you should be in view.",
        }
    if face.hand_occlusion:
        return {
            "ok": False,
            "level": "red",
            "code": "hand",
            "message": "Keep your hands off your face.",
        }
    if face.sunglasses_detected:
        return {
            "ok": False,
            "level": "red",
            "code": "sunglasses",
            "message": "Remove sunglasses.",
        }
    if face.mask_detected:
        return {
            "ok": False,
            "level": "yellow",
            "code": "mask",
            "message": "Remove your mask.",
        }
    parts = face.parts_status or {}
    if parts.get("left_eye") is False or parts.get("right_eye") is False:
        return {
            "ok": False,
            "level": "red",
            "code": "eyes_hidden",
            "message": "Keep both eyes visible.",
        }
    if face.ear is not None and face.ear < EAR_CLOSED:
        return {
            "ok": False,
            "level": "yellow",
            "code": "eyes_closed",
            "message": "Eyes closed. Look at the screen.",
        }
    if face.yaw is not None and abs(face.yaw) >= YAW_AWAY:
        side = "left" if face.yaw > 0 else "right"
        return {
            "ok": False,
            "level": "red",
            "code": f"head_{side}",
            "message": f"Head turned {side}. Look at the screen.",
        }
    if face.pitch is not None and face.pitch <= -PITCH_DOWN:
        return {
            "ok": False,
            "level": "red",
            "code": "look_down",
            "message": "Look at the screen, not down.",
        }
    if face.pitch is not None and face.pitch >= PITCH_UP:
        return {
            "ok": False,
            "level": "yellow",
            "code": "look_up",
            "message": "Look at the screen, not up.",
        }
    if face.gaze_x is not None and abs(face.gaze_x) >= GAZE_X:
        side = "left" if face.gaze_x < 0 else "right"
        return {
            "ok": False,
            "level": "red",
            "code": f"gaze_{side}",
            "message": f"Eyes looking {side}. Look here.",
        }
    if face.gaze_y is not None and face.gaze_y >= GAZE_Y_DOWN:
        return {
            "ok": False,
            "level": "red",
            "code": "gaze_down",
            "message": "Eyes looking down. Look here.",
        }
    return {
        "ok": True,
        "level": "green",
        "code": "ok",
        "message": "Looking at the screen.",
    }
