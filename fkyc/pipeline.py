"""Máy trạng thái giao diện FKYC. Chạy trên luồng camera, không đụng QML."""
from __future__ import annotations

import hmac
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from fkyc.hud_en import to_en

import cv2
import numpy as np

HINT_SEC = 12.0
OCR_INTERVAL_SEC = 0.05
BARCODE_INTERVAL_SEC = 0.28
STABLE_BARCODE = 2
NAME_EXTEND_SEC = 0.35

# Khớp Theme.qml + main.qml: camera well = card 1220×872 trừ pad 32 mỗi cạnh.
_WELL_ASPECT = (1220 - 64) / float(872 - 64)
# Khớp Theme.faceCamW/H và canvas oval 4:5
_FACE_WELL_ASPECT = 480 / 600.0
_FACE_CANVAS = (480, 600)
# Khớp CameraViewport.qml: width = min(parent.width*0.72, parent.height*1.2); height = width/1.586
_GUIDE_W_FRAC = 0.72
_GUIDE_H_CAP = 1.2
_CARD_RATIO = 1.586

def _same_secret(left: str, right: str) -> bool:
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


GUIDE_STEPS = (
    ("device", "Device check", "Resolution and signal"),
    ("face", "Face", "Oval frame"),
    ("turn", "Liveness", "Turn left and right"),
    ("light", "Lighting", "Skin reflection"),
    ("done", "Done", "Portrait and review"),
)


def _visible_in_well(frame: np.ndarray, aspect: float | None = None) -> np.ndarray:
    """Phần frame mà QML Image.PreserveAspectCrop thực sự vẽ trong camera well."""
    target = _WELL_ASPECT if aspect is None else aspect
    height, width = frame.shape[:2]
    frame_aspect = width / float(max(1, height))
    if frame_aspect > target:
        new_w = max(1, int(round(height * target)))
        x0 = max(0, (width - new_w) // 2)
        return frame[:, x0 : x0 + new_w]
    new_h = max(1, int(round(width / target)))
    y0 = max(0, (height - new_h) // 2)
    return frame[y0 : y0 + new_h, :]


def _face_view(frame: np.ndarray) -> np.ndarray:
    """Cắt đúng giếng camera dọc của màn đăng ký mặt, rồi về canvas oval 4:5."""
    vis = _visible_in_well(frame, _FACE_WELL_ASPECT)
    if vis.size == 0:
        vis = frame
    return cv2.resize(vis, _FACE_CANVAS, interpolation=cv2.INTER_LINEAR)


def _crop_id_guide(frame: np.ndarray) -> np.ndarray:
    """Cắt đúng khung chữ nhật CCCD trên màn hình (sau PreserveAspectCrop)."""
    vis = _visible_in_well(frame)
    height, width = vis.shape[:2]
    gw = min(int(width * _GUIDE_W_FRAC), int(height * _GUIDE_H_CAP))
    gh = max(1, int(round(gw / _CARD_RATIO)))
    if gh > height:
        gh = height
        gw = max(1, int(round(gh * _CARD_RATIO)))
    gw = min(gw, width)
    x0 = max(0, (width - gw) // 2)
    y0 = max(0, (height - gh) // 2)
    # Nới 4% để khỏi cắt mép thẻ khi người dùng lệch nhẹ
    pad_x = max(2, int(round(gw * 0.04)))
    pad_y = max(2, int(round(gh * 0.04)))
    xa = max(0, x0 - pad_x)
    ya = max(0, y0 - pad_y)
    xb = min(width, x0 + gw + pad_x)
    yb = min(height, y0 + gh + pad_y)
    crop = vis[ya:yb, xa:xb]
    return crop if crop.size else frame


def _unmirror(frame: np.ndarray) -> np.ndarray:
    """Preview camera bị lật gương; CCCD/mã vạch phải đọc ảnh gốc không mirror."""
    return cv2.flip(frame, 1)


def _for_card(frame: np.ndarray, max_w: int = 640, crop_guide: bool = False) -> np.ndarray:
    crop = _crop_id_guide(frame) if crop_guide else frame
    height, width = crop.shape[:2]
    if width <= max_w:
        return crop
    scale = max_w / float(width)
    return cv2.resize(crop, (max_w, max(1, int(round(height * scale)))), interpolation=cv2.INTER_AREA)


def _crop_barcode_guide(frame: np.ndarray) -> np.ndarray:
    """Cắt dải ngang khớp overlay thẻ SV (0.72 × 0.28, giữa camera well)."""
    vis = _visible_in_well(frame)
    height, width = vis.shape[:2]
    gw = min(width, max(1, int(round(width * 0.72))))
    gh = min(height, max(1, int(round(height * 0.28))))
    x0 = max(0, (width - gw) // 2)
    y0 = max(0, (height - gh) // 2)
    pad_x = max(2, int(round(gw * 0.06)))
    pad_y = max(2, int(round(gh * 0.18)))
    xa = max(0, x0 - pad_x)
    ya = max(0, y0 - pad_y)
    xb = min(width, x0 + gw + pad_x)
    yb = min(height, y0 + gh + pad_y)
    crop = vis[ya:yb, xa:xb]
    return crop if crop.size else vis


def _for_barcode(frame: np.ndarray) -> np.ndarray:
    """Ảnh mã vạch: bỏ gương, cắt well người dùng thấy, không INTER_AREA (nhoè vạch)."""
    vis = _visible_in_well(frame)
    height, width = vis.shape[:2]
    if width < 960:
        scale = 960.0 / float(max(1, width))
        return cv2.resize(
            vis,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_CUBIC,
        )
    if width > 1600:
        scale = 1600.0 / float(width)
        return cv2.resize(
            vis,
            (1600, max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_LINEAR,
        )
    return vis


def _guide_index(stage: str) -> int:
    if stage == "face_quality":
        return 1
    if stage in ("turn_left", "turn_right", "recenter"):
        return 2
    if stage in ("zoom_in", "flashing"):
        return 3
    if stage == "capture":
        return 4
    return 0


def _guides(stage: str) -> List[dict]:
    current = _guide_index(stage)
    rows = []
    for index, (key, title, caption) in enumerate(GUIDE_STEPS):
        if index < current:
            state = "done"
        elif index == current:
            state = "current"
        else:
            state = "todo"
        rows.append({
            "key": key,
            "title": title,
            "caption": caption,
            "index": index + 1,
            "state": state,
        })
    return rows


def _jpeg_data_url(frame: np.ndarray) -> str:
    import base64

    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        return ""
    payload = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


class SessionEngine:
    """Một phiên camera: đăng nhập 1:N hoặc đăng ký CCCD, mã vạch, khuôn mặt."""

    def __init__(self) -> None:
        self.screen = "landing"
        self.camera_on = False
        self.fields: Dict[str, str] = {
            "citizenId": "",
            "fullName": "",
            "gender": "",
            "dob": "",
            "studentId": "",
            "username": "",
            "faceReady": "",
        }
        self._account = ""
        self._replace_id = ""
        self._skip_cards = False
        self.step_blocked = False
        self._services = None
        self._session = None
        self._challenge_mgr = None
        self._step_started = time.time()
        self._last_ocr = 0.0
        self._name_hold_t0 = 0.0
        self._last_barcode = 0.0
        self._barcode_streak = ""
        self._barcode_count = 0
        self._fqa_streak = 0
        self._force = False
        self._flash: Optional[dict] = None
        self._capture_sent = False
        self._cache: Dict[str, Any] = {}
        self._latest: Optional[np.ndarray] = None
        self._services_lock = threading.Lock()
        self._ocr_lock = threading.Lock()
        self._ocr_job: Optional[np.ndarray] = None
        self._ocr_result: Optional[Dict[str, Any]] = None
        self._snapshot_pending: Optional[np.ndarray] = None
        self._snapshot_seq = 0
        self._login_analyzer = None
        self._exam_code = "ok"
        self._exam_pending = "ok"
        self._exam_pending_n = 0

    def _stash_shot(self, bgr: Optional[np.ndarray]) -> None:
        if bgr is None or getattr(bgr, "size", 0) == 0:
            return
        self._snapshot_pending = np.ascontiguousarray(bgr.copy())
        self._snapshot_seq += 1

    def take_snapshot(self) -> Optional[np.ndarray]:
        shot = self._snapshot_pending
        self._snapshot_pending = None
        return shot

    def _load(self):
        with self._services_lock:
            if self._services is None:
                import config as C
                import state
                from color_challenge import ChallengeManager
                from id_card_ocr import engine as ocr_engine
                from student_card import decode_student_barcode

                barcode_det = None
                try:
                    barcode_det = cv2.barcode.BarcodeDetector()
                except Exception:
                    barcode_det = None
                self._services = {
                    "C": C,
                    "state": state,
                    "ocr": ocr_engine,
                    "decode_barcode": decode_student_barcode,
                    "barcode": barcode_det,
                }
                self._challenge_mgr = ChallengeManager()
            svc = self._services
        svc["ocr"].warmup_async()
        return svc

    def submit(self, command: str) -> Dict[str, Any]:
        if command == "start_login":
            begun = self._begin("login")
            begun["landingNotice"] = ""
            return begun
        if command == "start_register":
            if not self._account:
                return self._mark(errorText="Log in manually before registering.", cameraActive=False)
            account = self._account
            ready = self.fields.get("faceReady", "")
            self.fields = {key: "" for key in self.fields}
            self.fields["username"] = account
            self.fields["faceReady"] = ready
            self._close_session()
            from manual_accounts import is_exception_user

            self._skip_cards = is_exception_user(account)
            begun = self._begin("face" if self._skip_cards else "citizen")
            begun["landingNotice"] = ""
            begun.update(self._mark(fields=dict(self.fields)))
            return begun
        if command == "start_manual":
            self._account = ""
            self._replace_id = ""
            self._skip_cards = False
            self.fields["username"] = ""
            self.fields["faceReady"] = ""
            self._close_session()
            self.camera_on = False
            self._flash = None
            return self._mark(
                screen="manualLogin",
                cameraActive=False,
                errorText="",
                busy=False,
                captureHint=False,
                flashActive=False,
                prompt="Log in manually",
                fields=dict(self.fields),
            )
        if command.startswith("{"):
            try:
                payload = json.loads(command)
            except json.JSONDecodeError:
                return {}
            if payload.get("cmd") == "manual_login":
                return self._manual_login(
                    str(payload.get("username") or ""),
                    str(payload.get("password") or ""),
                )
            if payload.get("cmd") == "profile_details":
                return self._profile_details(payload)
        if command == "capture_manual":
            self._force = True
            return {}
        if command == "cancel" or command == "go_home":
            self._account = ""
            self._replace_id = ""
            self._skip_cards = False
            self.fields["username"] = ""
            self.fields["faceReady"] = ""
            self._close_session()
            self.camera_on = False
            self._flash = None
            return self._mark(
                screen="landing",
                cameraActive=False,
                flashActive=False,
                errorText="",
                busy=False,
                captureHint=False,
                fields=dict(self.fields),
                stepBlocked=False,
            )
        if command == "confirm":
            return self._confirm()
        if command == "redo":
            return self._redo()
        if command == "step_back":
            return self._step_back()
        if command == "step_next":
            return self._step_next()
        return {}

    def _begin(self, screen: str) -> Dict[str, Any]:
        self.camera_on = True
        self.screen = screen
        self._step_started = time.time()
        self._name_hold_t0 = 0.0
        self._fqa_streak = 0
        self._barcode_count = 0
        self._barcode_streak = ""
        self._force = False
        self._flash = None
        self._capture_sent = False
        with self._ocr_lock:
            self._ocr_job = None
            self._ocr_result = None
        return self._mark(
            screen=screen,
            cameraActive=True,
            errorText="",
            busy=False,
            captureHint=False,
            flashActive=False,
            prompt=self._default_prompt(screen),
            stage="camera_check",
            progress=0.0,
            guides=_guides("camera_check"),
            stepBlocked=False,
        )

    def _manual_login(self, username: str, password: str) -> Dict[str, Any]:
        from manual_accounts import load_manual_accounts

        name = username.strip()
        matched_name = ""
        for saved_user, saved_pass in load_manual_accounts():
            if _same_secret(name, saved_user) and _same_secret(password, saved_pass):
                matched_name = saved_user
                break
        if not matched_name:
            return self._mark(
                screen="manualLogin",
                cameraActive=False,
                errorText="Incorrect username or password.",
                busy=False,
            )
        from database import face_user_id

        self._account = matched_name
        self._replace_id = face_user_id(matched_name)
        self.fields["username"] = matched_name
        self.fields["faceReady"] = "yes" if self._replace_id else ""
        self.camera_on = False
        return self._mark(
            screen="welcome",
            cameraActive=False,
            errorText="",
            busy=False,
            captureHint=False,
            flashActive=False,
            prompt="Welcome",
            fields=dict(self.fields),
        )

    def _default_prompt(self, screen: str) -> str:
        return {
            "login": "Login with FaceID",
            "citizen": "Show your Citizen Card",
            "student": "Show your Student Card",
            "face": "Đưa khuôn mặt vào giữa khung Oval",
            "exam": "Look at the screen.",
        }.get(screen, "")

    def _close_session(self) -> None:
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        if self._login_analyzer is not None:
            try:
                self._login_analyzer.close()
            except Exception:
                pass
            self._login_analyzer = None

    def _ensure_login_analyzer(self):
        if self._login_analyzer is None:
            from face_analyzer import FaceAnalyzer

            self._login_analyzer = FaceAnalyzer(stream=True)
        return self._login_analyzer

    def _mark(self, **kwargs: Any) -> Dict[str, Any]:
        changed: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in ("prompt", "errorText") and isinstance(value, str):
                value = to_en(value)
            if key == "stepBlocked":
                self.step_blocked = bool(value)
            if self._cache.get(key) != value:
                self._cache[key] = value
                changed[key] = value
        if "screen" in changed:
            self.screen = changed["screen"]
        return changed

    def on_frame(self, frame: np.ndarray, fps: float) -> Dict[str, Any]:
        self._latest = frame
        if not self.camera_on or self.step_blocked or self.screen in (
            "landing",
            "manualLogin",
            "welcome",
            "details",
            "loginResult",
            "citizenResult",
            "studentResult",
            "faceResult",
        ):
            return {}
        hint = (time.time() - self._step_started) >= HINT_SEC
        patch: Dict[str, Any] = {}
        try:
            if self.screen == "login":
                patch = self._on_login(frame, force=self._force)
            elif self.screen == "citizen":
                patch = self._on_citizen(frame, force=self._force)
            elif self.screen == "student":
                patch = self._on_student(frame, force=self._force)
            elif self.screen == "face":
                patch = self._on_face(frame, fps, force=self._force)
            elif self.screen == "exam":
                patch = self._on_exam(frame)
        except Exception as exc:
            patch = self._mark(errorText=str(exc), busy=False)
        self._force = False
        merged = self._mark(captureHint=hint and self.screen in ("login", "citizen", "student", "face", "exam"))
        merged.update(patch)
        return merged

    def _on_login(self, frame: np.ndarray, force: bool) -> Dict[str, Any]:
        svc = self._load()
        C = svc["C"]
        state = svc["state"]
        from face_analyzer import evaluate_face
        from id_card_ocr import plain_name

        view = _face_view(frame)
        try:
            analyzer = self._ensure_login_analyzer()
            face = analyzer.analyze(view, C.OVAL_NORMAL)
        except Exception as exc:
            return self._mark(
                prompt="Không tải được mô hình khuôn mặt",
                errorText=str(exc),
                ovalColor="red",
                busy=True,
            )
        verdict = evaluate_face(face, require_oval=True, is_turning=False)
        if verdict.all_ok:
            self._fqa_streak += 1
        else:
            self._fqa_streak = 0
        ready = (force and verdict.all_ok) or self._fqa_streak >= C.FQA_CONSECUTIVE_FRAMES
        patch = self._mark(
            prompt=verdict.message or "Login with FaceID",
            ovalColor="green" if verdict.all_ok else "yellow",
            progress=min(1.0, self._fqa_streak / max(1, C.FQA_CONSECUTIVE_FRAMES)),
            errorText="",
            busy=False,
        )
        if not ready:
            if force and not verdict.all_ok:
                patch.update(self._mark(errorText=verdict.message or "Khuôn mặt chưa đạt. Giữ thẳng và đủ sáng."))
            return patch
        self._fqa_streak = 0
        try:
            embedding = state.arcface_extractor.extract_embedding(
                view, landmarks_5pts=face.arcface_kps, bbox=face.bbox
            )
            match = state.user_repo.match_user_1_to_n(embedding)
        except Exception as exc:
            return self._mark(errorText=f"Không đối sánh được: {exc}", busy=False)
        if not match.get("is_match"):
            patch.update(self._mark(
                errorText=match.get("message") or "Không tìm thấy khuôn mặt trong hồ sơ.",
                prompt="Login with FaceID",
                ovalColor="yellow",
                progress=0.0,
            ))
            return patch
        user = match["matched_user"]
        detail = state.user_repo.get_user(user["user_id"]) or {}
        meta = detail.get("metadata") or {}
        fields = {
            "citizenId": str(meta.get("id_number") or ""),
            "fullName": plain_name(detail.get("full_name") or user.get("full_name") or "").upper(),
            "gender": str(meta.get("gender") or ""),
            "dob": str(meta.get("dob") or ""),
            "studentId": str(meta.get("student_id") or ""),
            "username": str(meta.get("username") or ""),
        }
        self.fields = fields
        self.screen = "loginResult"
        self._step_started = time.time()
        self._stash_shot(view)
        patch.update(self._mark(
            screen="loginResult",
            fields=fields,
            matchScore=float(match.get("similarity") or 0),
            errorText="",
            prompt="Đã nhận diện",
            busy=False,
            captureHint=False,
            snapshotSeq=self._snapshot_seq,
        ))
        return patch

    def _on_exam(self, frame: np.ndarray) -> Dict[str, Any]:
        svc = self._load()
        C = svc["C"]
        from exam_monitor import assess_exam

        view = _face_view(frame)
        try:
            analyzer = self._ensure_login_analyzer()
            face = analyzer.analyze(view, C.OVAL_NORMAL)
        except Exception as exc:
            return self._mark(
                prompt="Could not load the face model.",
                errorText=str(exc),
                ovalColor="red",
                busy=True,
            )
        verdict = assess_exam(face)
        code = verdict.get("code") or "ok"
        if code == self._exam_pending:
            self._exam_pending_n += 1
        else:
            self._exam_pending = code
            self._exam_pending_n = 1
        hold = 4 if code == "ok" else 5
        if self._exam_pending_n >= hold or not hasattr(self, "_exam_verdict"):
            self._exam_code = code
            self._exam_verdict = verdict
        shown = getattr(self, "_exam_verdict", verdict)
        ok = bool(shown.get("ok"))
        level = shown.get("level") or "green"
        oval = "green" if level == "green" else ("yellow" if level == "yellow" else "red")
        message = shown.get("message") or "Look at the screen."
        return self._mark(
            prompt=message,
            errorText="" if ok else message,
            ovalColor=oval,
            busy=False,
            captureHint=False,
        )

    def _ocr(self):
        from id_card_ocr import engine as ocr_engine

        return ocr_engine

    def offer_ocr_job(self, frame: np.ndarray) -> None:
        with self._ocr_lock:
            self._ocr_job = frame

    def take_ocr_job(self) -> Optional[np.ndarray]:
        with self._ocr_lock:
            job = self._ocr_job
            self._ocr_job = None
        return job

    def push_ocr_result(self, result: Dict[str, Any]) -> None:
        with self._ocr_lock:
            self._ocr_result = result

    def peek_ocr_result(self) -> Optional[Dict[str, Any]]:
        with self._ocr_lock:
            return self._ocr_result

    def _on_citizen(self, frame: np.ndarray, force: bool) -> Dict[str, Any]:
        now = time.time()
        if not force and now - self._last_ocr < OCR_INTERVAL_SEC:
            result = self.peek_ocr_result()
            if not result:
                return {}
        else:
            self._last_ocr = now
            self.offer_ocr_job(_for_card(_unmirror(frame), max_w=1000, crop_guide=True).copy())
            result = self.peek_ocr_result()
        ocr = self._ocr()
        if not ocr.ready:
            if ocr._error:
                return self._mark(prompt=ocr._error, ovalColor="red", busy=True)
            ocr.warmup_async()
            return self._mark(
                prompt="Đang tải mô hình OCR, vui lòng giữ thẻ trong khung",
                ovalColor="yellow",
                busy=True,
            )
        if not result:
            return self._mark(prompt="Giữ thẻ trong khung, đang đọc mặt trước CCCD", ovalColor="cyan", busy=False)
        parsed = result.get("fields") or {}
        from id_card_ocr import (
            draft_person_name,
            plain_name,
            prefer_dob,
            prefer_gender,
            prefer_id,
            prefer_name,
            valid_person_name,
        )

        chosen_id = prefer_id(
            self.fields.get("citizenId"),
            parsed.get("id_number"),
            self.fields.get("dob") or parsed.get("dob"),
            self.fields.get("gender") or parsed.get("gender"),
        )
        if chosen_id:
            self.fields["citizenId"] = chosen_id
        incoming_valid = valid_person_name(parsed.get("full_name"))
        incoming_draft = draft_person_name(parsed.get("full_name"))
        chosen_name = prefer_name(self.fields.get("fullName"), incoming_valid)
        if chosen_name:
            self.fields["fullName"] = plain_name(chosen_name).upper()
        elif incoming_draft and not valid_person_name(self.fields.get("fullName")):
            self.fields["fullName"] = plain_name(incoming_draft).upper()
        elif self.fields.get("fullName") and not draft_person_name(self.fields.get("fullName")):
            self.fields["fullName"] = ""
        if parsed.get("dob"):
            self.fields["dob"] = prefer_dob(self.fields.get("dob"), parsed["dob"]) or parsed["dob"]
        if parsed.get("gender"):
            self.fields["gender"] = prefer_gender(self.fields.get("gender"), parsed["gender"])
        prompt = result.get("guidance") or "Show your Citizen Card"
        n_words = len((self.fields.get("fullName") or "").split())
        name_locked = bool(valid_person_name(self.fields.get("fullName")))
        core_ok = all(self.fields.get(key) for key in ("citizenId", "dob", "gender"))
        ready = bool(result.get("complete") or (core_ok and name_locked))
        go_result = False
        if ready and n_words >= 3:
            go_result = True
            self._name_hold_t0 = 0.0
        elif ready and n_words == 2:
            if self._name_hold_t0 <= 0:
                self._name_hold_t0 = now
            if now - self._name_hold_t0 >= NAME_EXTEND_SEC:
                go_result = True
            else:
                prompt = "Đang đọc đủ họ tên. Giữ thẻ trong khung"
        else:
            self._name_hold_t0 = 0.0
            if core_ok and self.fields.get("fullName") and not name_locked:
                prompt = "Đang đọc đủ họ tên. Giữ thẻ trong khung"
        patch = self._mark(
            prompt=prompt,
            ovalColor=result.get("color") or "cyan",
            fields=dict(self.fields),
            busy=False,
        )
        if go_result:
            self.screen = "citizenResult"
            self._step_started = time.time()
            self._stash_shot(_crop_id_guide(_unmirror(frame)))
            dup = self._existing_profile()
            patch.update(self._mark(
                screen="citizenResult",
                errorText="Hồ sơ đã tồn tại. Không thể đăng ký lại." if dup else "",
                captureHint=False,
                busy=False,
                snapshotSeq=self._snapshot_seq,
            ))
        elif force:
            patch.update(self._mark(errorText=result.get("guidance") or "Chưa đọc đủ thông tin CCCD."))
        return patch

    def _on_student(self, frame: np.ndarray, force: bool) -> Dict[str, Any]:
        now = time.time()
        if not force and now - self._last_barcode < BARCODE_INTERVAL_SEC:
            return {}
        self._last_barcode = now
        svc = self._load()
        unmirrored = _unmirror(frame)
        result = svc["decode_barcode"](_crop_barcode_guide(unmirrored))
        if not result.get("found"):
            result = svc["decode_barcode"](_for_barcode(unmirrored))
        if result.get("found"):
            student_id = result["student_id"]
            if student_id == self._barcode_streak:
                self._barcode_count += 1
            else:
                self._barcode_streak = student_id
                self._barcode_count = 1
        else:
            self._barcode_streak = ""
            self._barcode_count = 0
        patch = self._mark(prompt=result.get("guidance") or "Show your Student Card", ovalColor=result.get("color") or "cyan")
        ready = result.get("found") and (force or self._barcode_count >= STABLE_BARCODE)
        if ready:
            self.fields["studentId"] = result["student_id"]
            self.screen = "studentResult"
            self._step_started = time.time()
            self._stash_shot(_crop_barcode_guide(unmirrored))
            dup = self._existing_profile(include_student=True)
            patch.update(self._mark(
                screen="studentResult",
                fields=dict(self.fields),
                errorText="Hồ sơ đã tồn tại. Không thể đăng ký lại." if dup else "",
                captureHint=False,
                snapshotSeq=self._snapshot_seq,
            ))
        elif force:
            patch.update(self._mark(errorText=result.get("guidance") or "Chưa đọc được mã vạch."))
        return patch

    def _on_face(self, frame: np.ndarray, fps: float, force: bool) -> Dict[str, Any]:
        from camera_quality import ClientStats
        from enrollment import EnrollmentSession, Stage

        view = _face_view(frame)
        if self._session is None:
            try:
                self._session = EnrollmentSession(f"FKYC-{uuid.uuid4().hex[:8]}")
                self._session._get_analyzer()
            except Exception as exc:
                self._session = None
                return self._mark(
                    prompt="Không tải được mô hình khuôn mặt",
                    errorText=str(exc),
                    ovalColor="red",
                    busy=True,
                )
            self._capture_sent = False
        if self._flash is not None:
            return self._advance_flash(view)
        if self._session.stage == Stage.FLASHING:
            return self._start_flash()
        if self._session.stage == Stage.CAPTURE and not self._capture_sent:
            return self._finish_capture(view)
        if self._session.stage == Stage.FAILED:
            message = (
                self._session.history.get("optical_liveness", {}).get("message")
                or "Đăng ký khuôn mặt chưa đạt. Bấm Quay lại để làm lại."
            )
            return self._mark(prompt=message, errorText=message, ovalColor="red", guides=_guides("capture"))

        h, w = frame.shape[:2]
        stats = ClientStats(fps=fps, width=w, height=h, frame_advancing=True)
        reply = self._session.process_frame(view, stats)
        oval = reply.get("oval") or {}
        patch = self._mark(
            prompt=reply.get("message") or "",
            stage=reply.get("stage") or "",
            progress=float(reply.get("progress") or 0),
            ovalColor=reply.get("color") or "cyan",
            turnDirection=reply.get("turn_arrow") or "none",
            guides=_guides(reply.get("stage") or ""),
            normCx=float(oval.get("cx", 0.5)),
            normCy=float(oval.get("cy", 0.47)),
            normRx=float(oval.get("rx", 0.33)),
            normRy=float(oval.get("ry", 0.36)),
            errorText="",
        )
        if self._session.stage == Stage.FLASHING:
            patch.update(self._start_flash())
        return patch

    def _start_flash(self) -> Dict[str, Any]:
        svc = self._load()
        C = svc["C"]
        challenge = self._challenge_mgr.create_challenge(self._session.session_id, length=3)
        self._flash = {
            "steps": challenge.sequence,
            "index": 0,
            "started": time.time(),
            "frames": [],
            "held": None,
            "token": challenge.token,
        }
        step = challenge.sequence[0]
        return self._mark(
            flashActive=True,
            flashColor=step.hex,
            prompt="Giữ yên. Đang quét ánh sáng màu",
            stage="flashing",
            guides=_guides("flashing"),
            ovalColor="green",
        )

    def _advance_flash(self, frame: np.ndarray) -> Dict[str, Any]:
        flash = self._flash
        step = flash["steps"][flash["index"]]
        elapsed_ms = (time.time() - flash["started"]) * 1000.0
        if elapsed_ms >= step.duration_ms * 0.7 and flash["held"] is None:
            flash["held"] = frame.copy()
        if elapsed_ms < step.duration_ms:
            return self._mark(flashActive=True, flashColor=step.hex, stage="flashing")
        flash["frames"].append(flash["held"] if flash["held"] is not None else frame.copy())
        flash["index"] += 1
        flash["held"] = None
        flash["started"] = time.time()
        if flash["index"] < len(flash["steps"]):
            nxt = flash["steps"][flash["index"]]
            return self._mark(flashActive=True, flashColor=nxt.hex, stage="flashing")
        return self._finish_flash()

    def _finish_flash(self) -> Dict[str, Any]:
        svc = self._load()
        C = svc["C"]
        state = svc["state"]
        flash = self._flash
        expected = [tuple(step.rgb) for step in flash["steps"]]
        frames = flash["frames"]
        self._flash = None
        try:
            res = state.optical_analyzer.analyze_sequence(frames, expected, awb_gamma=C.FLASH_AWB_GAMMA)
        except Exception as exc:
            self._session.stage = __import__("enrollment").Stage.FAILED
            return self._mark(flashActive=False, errorText=f"Lỗi quét màu: {exc}", ovalColor="red")
        if getattr(C, "FLASH_DEMO_BYPASS", False) and not res.passed:
            res.passed = True
            res.verdict = "LIVENESS_PASS"
            res.message = "Light reflection check passed (demo)."
            if res.correlation_score < C.FLASH_MIN_PEARSON:
                res.correlation_score = float(C.FLASH_MIN_PEARSON)
        self._challenge_mgr.consume_challenge(self._session.session_id)
        self._session.apply_optical_result(
            passed=res.passed,
            correlation=res.correlation_score,
            amplitude=res.amplitude,
            verdict=res.verdict,
            details=res.details,
        )
        if not res.passed:
            return self._mark(flashActive=False, errorText=res.message, prompt=res.message, ovalColor="red", stage="failed")
        return self._mark(flashActive=False, prompt="Giữ yên để chụp ảnh chân dung", stage="capture", ovalColor="green", guides=_guides("capture"))

    def _finish_capture(self, frame: np.ndarray) -> Dict[str, Any]:
        self._capture_sent = True
        result = self._session.verify_final_capture(frame)
        if not result.get("passed"):
            message = result.get("message") or "Portrait not ready."
            return self._mark(errorText=message, prompt=message, ovalColor="red", stage="failed", guides=_guides("capture"))
        self._enrolled_frame = frame.copy()
        self.screen = "faceResult"
        self._step_started = time.time()
        self._stash_shot(self._enrolled_frame)
        return self._mark(
            screen="faceResult",
            fields=dict(self.fields),
            errorText="",
            prompt="Đã chụp chân dung",
            flashActive=False,
            captureHint=False,
            busy=False,
            snapshotSeq=self._snapshot_seq,
        )

    def _existing_profile(self, include_student: bool = False):
        svc = self._load()
        return svc["state"].user_repo.find_by_identity(
            id_number=self.fields.get("citizenId") or None,
            full_name=self.fields.get("fullName") or None,
            dob=self.fields.get("dob") or None,
            gender=self.fields.get("gender") or None,
            student_id=(self.fields.get("studentId") or None) if include_student else None,
            username=self._account or None,
        )

    def _same_saved_profile(self, existing: Any) -> bool:
        if not self._replace_id or not isinstance(existing, dict):
            return False
        return str(existing.get("user_id") or "") == self._replace_id

    def _reject_existing(self, existing=None) -> Dict[str, Any]:
        self._close_session()
        self.camera_on = False
        patch = self._mark(
            screen="landing",
            cameraActive=False,
            busy=False,
            errorText="",
            flashActive=False,
            captureHint=False,
        )
        patch["landingNotice"] = to_en("Hồ sơ này đã tồn tại. Vui lòng đăng nhập.")
        return patch

    def _register_order(self) -> List[str]:
        if self._skip_cards:
            return ["face"]
        return ["citizen", "student", "face"]

    def _register_index(self) -> int:
        screen = self.screen
        if screen in ("citizen", "citizenResult"):
            step = "citizen"
        elif screen in ("student", "studentResult"):
            step = "student"
        elif screen in ("face", "faceResult"):
            step = "face"
        else:
            return -1
        try:
            return self._register_order().index(step)
        except ValueError:
            return -1

    def _citizen_ready(self) -> bool:
        return all(self.fields.get(key) for key in ("citizenId", "fullName", "dob", "gender"))

    def _student_ready(self) -> bool:
        return bool(self.fields.get("studentId"))

    def _step_ready(self, step: str) -> bool:
        if step == "student":
            return self._citizen_ready()
        if step == "face" and not self._skip_cards:
            return self._citizen_ready() and self._student_ready()
        return True

    def _open_step(self, step: str) -> Dict[str, Any]:
        if not self._step_ready(step):
            self._close_session()
            self.camera_on = True
            return self._mark(
                screen=step,
                cameraActive=True,
                errorText="",
                busy=False,
                captureHint=False,
                flashActive=False,
                prompt=self._default_prompt(step),
                stage="camera_check",
                progress=0.0,
                guides=_guides("camera_check") if step == "face" else [],
                stepBlocked=True,
            )
        if step == "face":
            self._close_session()
            self._capture_sent = False
        elif step == "student":
            self._barcode_count = 0
            self._barcode_streak = ""
        return self._begin(step)

    def _step_back(self) -> Dict[str, Any]:
        index = self._register_index()
        if index < 0:
            return {}
        if index == 0:
            return self.submit("cancel")
        return self._open_step(self._register_order()[index - 1])

    def _step_next(self) -> Dict[str, Any]:
        order = self._register_order()
        index = self._register_index()
        if index < 0 or index >= len(order) - 1:
            return {}
        return self._open_step(order[index + 1])

    def _confirm(self) -> Dict[str, Any]:
        if self.screen == "loginResult":
            self.camera_on = True
            self.screen = "exam"
            self._exam_code = "ok"
            self._exam_pending = "ok"
            self._exam_pending_n = 0
            self._exam_verdict = {
                "ok": True,
                "level": "green",
                "code": "ok",
                "message": "Look at the screen.",
            }
            self._step_started = time.time()
            return self._mark(
                screen="exam",
                cameraActive=True,
                errorText="",
                prompt="Look at the screen.",
                ovalColor="green",
                captureHint=False,
                busy=False,
            )
        if self.screen == "citizenResult":
            if not all(self.fields[key] for key in ("citizenId", "fullName", "dob", "gender")):
                return self._mark(errorText="Thiếu thông tin CCCD. Bấm Redo để quét lại.")
            existing = self._existing_profile()
            if existing and not self._same_saved_profile(existing):
                return self._reject_existing(existing)
            self.screen = "student"
            self._step_started = time.time()
            self._barcode_count = 0
            return self._mark(screen="student", errorText="", captureHint=False, prompt="Show your Student Card")
        if self.screen == "studentResult":
            if not self.fields["studentId"]:
                return self._mark(errorText="Chưa có mã sinh viên.")
            existing = self._existing_profile(include_student=True)
            if existing and not self._same_saved_profile(existing):
                return self._reject_existing(existing)
            self._close_session()
            self._capture_sent = False
            self.screen = "face"
            self._step_started = time.time()
            return self._mark(screen="face", errorText="", captureHint=False, prompt="Đưa khuôn mặt vào khung Oval", stage="camera_check", guides=_guides("camera_check"), progress=0)
        if self.screen == "faceResult":
            if self._skip_cards:
                self.camera_on = False
                return self._mark(
                    screen="details",
                    cameraActive=False,
                    errorText="",
                    busy=False,
                    captureHint=False,
                    flashActive=False,
                    prompt="Enter your details",
                )
            return self._save()
        return {}

    def _profile_details(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.screen != "details" or not self._skip_cards:
            return {}
        citizen = str(payload.get("citizenId") or "").strip()
        name = str(payload.get("fullName") or "").strip()
        dob = str(payload.get("dob") or "").strip()
        student = str(payload.get("studentId") or "").strip()
        if not all((citizen, name, dob, student)):
            return self._mark(errorText="Fill in every field.", screen="details")
        self.fields["citizenId"] = citizen
        self.fields["fullName"] = name
        self.fields["dob"] = dob
        self.fields["studentId"] = student
        return self._save()

    def _redo(self) -> Dict[str, Any]:
        if self.screen == "loginResult":
            return self._begin("login")
        if self.screen == "citizenResult":
            account = self._account
            ready = self.fields.get("faceReady", "")
            self.fields = {key: "" for key in self.fields}
            self.fields["username"] = account
            self.fields["faceReady"] = ready
            return self._begin("citizen") | self._mark(fields=dict(self.fields))
        if self.screen == "studentResult":
            self.fields["studentId"] = ""
            self._barcode_count = 0
            self._barcode_streak = ""
            begun = self._begin("student")
            begun.update(self._mark(fields=dict(self.fields)))
            return begun
        if self.screen == "face":
            self._close_session()
            self._flash = None
            self._capture_sent = False
            return self._begin("face")
        if self.screen == "faceResult":
            self._close_session()
            self._capture_sent = False
            return self._begin("face")
        return {}

    def _save(self) -> Dict[str, Any]:
        if self._session is None or self._session.final_embedding is None:
            return self._mark(errorText="Chưa có vector khuôn mặt. Làm lại bước đăng ký mặt.")
        frame = getattr(self, "_enrolled_frame", None)
        if frame is None:
            frame = self._latest
        if frame is None:
            return self._mark(errorText="Không còn ảnh chân dung để lưu.")
        if not self._account:
            return self._mark(errorText="Log in manually before registering.")
        svc = self._load()
        existing = self._existing_profile(include_student=True)
        if existing and not self._same_saved_profile(existing):
            return self._reject_existing(existing)
        try:
            match = svc["state"].user_repo.match_user_1_to_n(self._session.final_embedding)
            matched = match.get("matched_user")
            if match.get("is_match") and not self._same_saved_profile(matched):
                return self._reject_existing(matched)
        except Exception:
            pass
        account = self._account
        meta = {
            "id_number": self.fields["citizenId"],
            "dob": self.fields["dob"],
            "gender": self.fields["gender"],
            "student_id": self.fields["studentId"],
            "username": account,
        }
        try:
            from database import DuplicateUserError

            saved = svc["state"].user_repo.save_user(
                full_name=self.fields["fullName"] or "Sinh vien",
                embedding=self._session.final_embedding,
                snapshot_b64=_jpeg_data_url(frame),
                user_id=self._replace_id or None,
                metadata=meta,
            )
        except DuplicateUserError as exc:
            return self._reject_existing(exc.existing)
        except Exception as exc:
            return self._mark(errorText=f"Không lưu được hồ sơ: {exc}", busy=False)
        self._close_session()
        self.camera_on = False
        self._account = ""
        self._replace_id = ""
        self._skip_cards = False
        self.fields["username"] = ""
        self.fields["faceReady"] = ""
        user_id = saved.get("user_id", "")
        patch = self._mark(
            screen="landing",
            cameraActive=False,
            busy=False,
            errorText="",
            flashActive=False,
            fields=dict(self.fields),
        )
        patch["savedUserId"] = user_id
        patch["landingNotice"] = f"Face profile linked to {account}."
        return patch
