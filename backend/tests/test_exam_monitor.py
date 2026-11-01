from face_analyzer import FaceResult
from exam_monitor import assess_exam


def _face(**kwargs) -> FaceResult:
    data = dict(
        face_count=1,
        bbox=(0.3, 0.2, 0.7, 0.8),
        yaw=0.0,
        pitch=0.0,
        gaze_x=0.0,
        gaze_y=0.0,
        ear=0.28,
        parts_status={"left_eye": True, "right_eye": True},
    )
    data.update(kwargs)
    return FaceResult(**data)


def test_exam_ok_when_looking_straight():
    out = assess_exam(_face())
    assert out["ok"] is True
    assert out["code"] == "ok"


def test_exam_no_face_and_multiple_faces():
    assert assess_exam(FaceResult(face_count=0))["code"] == "no_face"
    assert assess_exam(_face(face_count=2))["code"] == "multiple_faces"


def test_exam_look_away_head_and_gaze():
    assert assess_exam(_face(yaw=28.0))["code"] == "head_left"
    assert assess_exam(_face(yaw=-25.0))["code"] == "head_right"
    assert assess_exam(_face(pitch=-20.0))["code"] == "look_down"
    assert assess_exam(_face(gaze_x=-0.5))["code"] == "gaze_left"
    assert assess_exam(_face(gaze_x=0.5))["code"] == "gaze_right"
    assert assess_exam(_face(gaze_y=0.55))["code"] == "gaze_down"
    assert assess_exam(_face(ear=0.10))["code"] == "eyes_closed"


def test_exam_login_confirm_opens_exam_screen():
    from fkyc.pipeline import SessionEngine

    engine = SessionEngine()
    engine.screen = "loginResult"
    engine.fields["fullName"] = "NGUYEN VAN AN"
    patch = engine.submit("confirm")
    assert patch.get("screen") == "exam"
    assert engine.camera_on is True
