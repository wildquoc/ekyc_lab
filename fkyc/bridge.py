"""Đối tượng `bridge` cho QML. Mọi gán thuộc tính chạy trên luồng giao diện."""
from __future__ import annotations

import json

from PySide6.QtCore import Property, QObject, Signal, Slot

from fkyc.camera_worker import CameraWorker


class Bridge(QObject):
    screenChanged = Signal()
    frameTick = Signal(int)
    promptChanged = Signal()
    busyChanged = Signal()
    stageChanged = Signal()
    progressChanged = Signal()
    ovalColorChanged = Signal()
    turnDirectionChanged = Signal()
    flashActiveChanged = Signal()
    flashColorChanged = Signal()
    captureHintChanged = Signal()
    guidesChanged = Signal()
    fieldsChanged = Signal()
    matchScoreChanged = Signal()
    errorChanged = Signal()
    cameraActiveChanged = Signal()
    normChanged = Signal()
    ovalGeomChanged = Signal()
    snapshotSeqChanged = Signal()
    saved = Signal(str)
    notice = Signal(str)

    def __init__(self, worker: CameraWorker) -> None:
        super().__init__()
        self._worker = worker
        self._frame_seq = 0
        self._screen = "landing"
        self._prompt = ""
        self._busy = False
        self._stage = "camera_check"
        self._progress = 0.0
        self._oval_color = "cyan"
        self._turn = "none"
        self._flash_active = False
        self._flash_color = "#000000"
        self._capture_hint = False
        self._guides = []
        self._fields = {
            "citizenId": "",
            "fullName": "",
            "gender": "",
            "dob": "",
            "studentId": "",
            "username": "",
            "faceReady": "",
        }
        self._match_score = 0.0
        self._error = ""
        self._camera_active = False
        self._norm = (0.50, 0.50, 0.41, 0.42)
        self._oval = (0.0, 0.0, 0.0, 0.0)
        self._snapshot_seq = 0
        worker.uiEvent.connect(self.apply_json)
        worker.frameReady.connect(self._on_frame)

    def _on_frame(self) -> None:
        self._frame_seq += 1
        self.frameTick.emit(self._frame_seq)

    @Slot(str)
    def apply_json(self, payload: str) -> None:
        data = json.loads(payload)
        saved_id = data.pop("savedUserId", None)
        landing_notice = data.pop("landingNotice", None)
        setters = {
            "screen": self._set_screen,
            "prompt": self._set_prompt,
            "busy": self._set_busy,
            "stage": self._set_stage,
            "progress": self._set_progress,
            "ovalColor": self._set_oval_color,
            "turnDirection": self._set_turn,
            "flashActive": self._set_flash_active,
            "flashColor": self._set_flash_color,
            "captureHint": self._set_capture_hint,
            "guides": self._set_guides,
            "fields": self._set_fields,
            "matchScore": self._set_match,
            "errorText": self._set_error,
            "cameraActive": self._set_camera,
            "snapshotSeq": self._set_snapshot_seq,
        }
        norm = [self._norm[0], self._norm[1], self._norm[2], self._norm[3]]
        norm_keys = ("normCx", "normCy", "normRx", "normRy")
        norm_changed = False
        for key, value in data.items():
            if key in setters:
                setters[key](value)
            elif key in norm_keys:
                norm[norm_keys.index(key)] = float(value)
                norm_changed = True
        if norm_changed:
            self._norm = tuple(norm)
            self.normChanged.emit()
        if saved_id:
            self.saved.emit(str(saved_id))
        if landing_notice is not None:
            self.notice.emit(str(landing_notice))

    def _set_screen(self, value: str) -> None:
        if value != self._screen:
            self._screen = value
            self.screenChanged.emit()

    def _set_prompt(self, value: str) -> None:
        if value != self._prompt:
            self._prompt = value
            self.promptChanged.emit()

    def _set_busy(self, value: bool) -> None:
        value = bool(value)
        if value != self._busy:
            self._busy = value
            self.busyChanged.emit()

    def _set_stage(self, value: str) -> None:
        if value != self._stage:
            self._stage = value
            self.stageChanged.emit()

    def _set_progress(self, value: float) -> None:
        value = float(value)
        if abs(value - self._progress) > 0.001:
            self._progress = value
            self.progressChanged.emit()

    def _set_oval_color(self, value: str) -> None:
        if value != self._oval_color:
            self._oval_color = value
            self.ovalColorChanged.emit()

    def _set_turn(self, value: str) -> None:
        if not value:
            value = "none"
        if value != self._turn:
            self._turn = value
            self.turnDirectionChanged.emit()

    def _set_flash_active(self, value: bool) -> None:
        value = bool(value)
        if value != self._flash_active:
            self._flash_active = value
            self.flashActiveChanged.emit()

    def _set_flash_color(self, value: str) -> None:
        if value != self._flash_color:
            self._flash_color = value
            self.flashColorChanged.emit()

    def _set_capture_hint(self, value: bool) -> None:
        value = bool(value)
        if value != self._capture_hint:
            self._capture_hint = value
            self.captureHintChanged.emit()

    def _set_guides(self, value) -> None:
        if value != self._guides:
            self._guides = value
            self.guidesChanged.emit()

    def _set_fields(self, value) -> None:
        if value != self._fields:
            self._fields = value
            self.fieldsChanged.emit()

    def _set_match(self, value: float) -> None:
        value = float(value)
        if abs(value - self._match_score) > 0.0001:
            self._match_score = value
            self.matchScoreChanged.emit()

    def _set_error(self, value: str) -> None:
        if value != self._error:
            self._error = value
            self.errorChanged.emit()

    def _set_camera(self, value: bool) -> None:
        value = bool(value)
        if value != self._camera_active:
            self._camera_active = value
            self.cameraActiveChanged.emit()

    def _set_snapshot_seq(self, value) -> None:
        value = int(value or 0)
        if value != self._snapshot_seq:
            self._snapshot_seq = value
            self.snapshotSeqChanged.emit()

    def _submit(self, command: str) -> None:
        self._worker.submit(command)

    @Slot()
    def startLogin(self) -> None:
        self._submit("start_login")

    @Slot()
    def startRegister(self) -> None:
        self._submit("start_register")

    @Slot()
    def startManual(self) -> None:
        self._submit("start_manual")

    @Slot(str, str)
    def submitManual(self, username: str, password: str) -> None:
        self._submit(json.dumps({
            "cmd": "manual_login",
            "username": username,
            "password": password,
        }, ensure_ascii=False))

    @Slot(str, str, str, str)
    def submitDetails(self, dob: str, citizen_id: str, full_name: str, student_id: str) -> None:
        self._submit(json.dumps({
            "cmd": "profile_details",
            "dob": dob,
            "citizenId": citizen_id,
            "fullName": full_name,
            "studentId": student_id,
        }, ensure_ascii=False))

    @Slot()
    def captureManual(self) -> None:
        self._submit("capture_manual")

    @Slot()
    def tapFocus(self) -> None:
        self._worker.request_focus()

    @Slot()
    def cancel(self) -> None:
        self._submit("cancel")

    @Slot()
    def confirm(self) -> None:
        self._submit("confirm")

    @Slot()
    def redo(self) -> None:
        self._submit("redo")

    @Slot()
    def goHome(self) -> None:
        self._submit("go_home")

    @Slot(float, float, float, float)
    def setOval(self, x: float, y: float, w: float, h: float) -> None:
        geom = (float(x), float(y), float(w), float(h))
        if geom != self._oval:
            self._oval = geom
            self.ovalGeomChanged.emit()

    def _frame_seq(self) -> int:
        return self._frame_seq

    def _screen_value(self) -> str:
        return self._screen

    def _prompt_value(self) -> str:
        return self._prompt

    def _busy_value(self) -> bool:
        return self._busy

    def _stage_value(self) -> str:
        return self._stage

    def _progress_value(self) -> float:
        return self._progress

    def _oval_color_value(self) -> str:
        return self._oval_color

    def _turn_value(self) -> str:
        return self._turn

    def _flash_active_value(self) -> bool:
        return self._flash_active

    def _flash_color_value(self) -> str:
        return self._flash_color

    def _capture_hint_value(self) -> bool:
        return self._capture_hint

    def _guides_value(self):
        return self._guides

    def _fields_value(self):
        return self._fields

    def _match_value(self) -> float:
        return self._match_score

    def _error_value(self) -> str:
        return self._error

    def _camera_value(self) -> bool:
        return self._camera_active

    def _snapshot_seq_value(self) -> int:
        return self._snapshot_seq

    def _norm_cx(self) -> float:
        return self._norm[0]

    def _norm_cy(self) -> float:
        return self._norm[1]

    def _norm_rx(self) -> float:
        return self._norm[2]

    def _norm_ry(self) -> float:
        return self._norm[3]

    def _oval_x(self) -> float:
        return self._oval[0]

    def _oval_y(self) -> float:
        return self._oval[1]

    def _oval_w(self) -> float:
        return self._oval[2]

    def _oval_h(self) -> float:
        return self._oval[3]

    frameSeq = Property(int, _frame_seq, notify=frameTick)
    screen = Property(str, _screen_value, notify=screenChanged)
    prompt = Property(str, _prompt_value, notify=promptChanged)
    busy = Property(bool, _busy_value, notify=busyChanged)
    stage = Property(str, _stage_value, notify=stageChanged)
    progress = Property(float, _progress_value, notify=progressChanged)
    ovalColor = Property(str, _oval_color_value, notify=ovalColorChanged)
    turnDirection = Property(str, _turn_value, notify=turnDirectionChanged)
    flashActive = Property(bool, _flash_active_value, notify=flashActiveChanged)
    flashColor = Property(str, _flash_color_value, notify=flashColorChanged)
    captureHint = Property(bool, _capture_hint_value, notify=captureHintChanged)
    guides = Property("QVariantList", _guides_value, notify=guidesChanged)
    fields = Property("QVariantMap", _fields_value, notify=fieldsChanged)
    matchScore = Property(float, _match_value, notify=matchScoreChanged)
    errorText = Property(str, _error_value, notify=errorChanged)
    cameraActive = Property(bool, _camera_value, notify=cameraActiveChanged)
    snapshotSeq = Property(int, _snapshot_seq_value, notify=snapshotSeqChanged)
    normCx = Property(float, _norm_cx, notify=normChanged)
    normCy = Property(float, _norm_cy, notify=normChanged)
    normRx = Property(float, _norm_rx, notify=normChanged)
    normRy = Property(float, _norm_ry, notify=normChanged)
    ovalX = Property(float, _oval_x, notify=ovalGeomChanged)
    ovalY = Property(float, _oval_y, notify=ovalGeomChanged)
    ovalWidth = Property(float, _oval_w, notify=ovalGeomChanged)
    ovalHeight = Property(float, _oval_h, notify=ovalGeomChanged)
