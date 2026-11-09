"""Cổng đăng nhập thủ công trước luồng đăng ký FaceID."""
import json

from fkyc.pipeline import SessionEngine


def _login(engine: SessionEngine, username: str, password: str):
    return engine.submit(json.dumps({
        "cmd": "manual_login",
        "username": username,
        "password": password,
    }))


def test_manual_login_opens_welcome_then_existing_register():
    engine = SessionEngine()
    opened = engine.submit("start_manual")
    assert opened["screen"] == "manualLogin"
    assert engine.camera_on is False

    denied = _login(engine, "admin", "admin")
    assert engine.screen == "manualLogin"
    assert "Incorrect" in denied["errorText"]

    allowed = _login(engine, "pkq", "204120")
    assert allowed["screen"] == "welcome"
    assert engine.camera_on is False
    from database import face_user_id
    assert allowed["fields"]["faceReady"] == ("yes" if face_user_id("pkq") else "")

    begun = engine.submit("start_register")
    assert begun["screen"] == "citizen"
    assert engine.camera_on is True
    assert engine.fields["username"] == "pkq"
    assert engine._account == "pkq"


def test_exception_user_skips_cards_then_enters_details():
    engine = SessionEngine()
    _login(engine, "nvt", "190509")
    begun = engine.submit("start_register")
    assert begun["screen"] == "face"
    assert engine._skip_cards is True

    engine.screen = "faceResult"
    opened = engine.submit("confirm")
    assert opened["screen"] == "details"
    assert engine.camera_on is False

    missing = engine.submit(json.dumps({
        "cmd": "profile_details",
        "dob": "",
        "citizenId": "079206000000",
        "fullName": "NGUYEN VAN A",
        "studentId": "SE190509",
    }))
    assert engine.screen == "details"
    assert "every field" in missing["errorText"]


def test_register_steps_can_skip_ahead_until_face():
    engine = SessionEngine()
    _login(engine, "pkq", "204120")
    assert engine.submit("start_register")["screen"] == "citizen"

    skipped = engine.submit("step_next")
    assert skipped["screen"] == "student"
    assert engine.step_blocked is True

    back = engine.submit("step_back")
    assert back["screen"] == "citizen"
    assert engine.step_blocked is False

    engine.fields.update({
        "citizenId": "079206039167",
        "fullName": "PHAM KIEN QUOC",
        "dob": "13/01/2006",
        "gender": "Nam",
    })
    opened = engine.submit("step_next")
    assert opened["screen"] == "student"
    assert engine.step_blocked is False

    blocked_face = engine.submit("step_next")
    assert blocked_face["screen"] == "face"
    assert engine.step_blocked is True
    assert engine.submit("step_next") == {}

    assert engine.submit("step_back")["screen"] == "student"
    engine.fields["studentId"] = "SE204120"
    ready_face = engine.submit("step_next")
    assert ready_face["screen"] == "face"
    assert engine.step_blocked is False


def test_register_without_manual_login_is_blocked():
    engine = SessionEngine()
    blocked = engine.submit("start_register")
    assert engine.screen == "landing"
    assert "Log in manually" in blocked["errorText"]


def test_face_profile_is_found_by_username():
    import numpy as np

    from database import UserRepository

    repo = UserRepository()
    uid = "USR-TEST-LINK-PKQ"
    repo.delete_user(uid)
    try:
        repo.save_user(
            full_name="NGUYEN VAN PKQ",
            embedding=np.ones(512, dtype=np.float32),
            snapshot_b64="data:image/jpeg;base64,AA==",
            user_id=uid,
            metadata={
                "id_number": "079099009999",
                "dob": "02/02/1998",
                "gender": "Nam",
                "student_id": "ZZLINK999",
                "username": "zz-test-link",
            },
        )
        found = repo.find_by_identity(username="ZZ-TEST-LINK")
        assert found is not None
        assert found["user_id"] == uid
        assert found["matched_by"] == "username"
        assert found["username"] == "zz-test-link"
    finally:
        repo.delete_user(uid)


def test_welcome_shows_ready_when_face_exists(monkeypatch):
    monkeypatch.setattr("database.face_user_id", lambda name: "USR-READY" if name == "lha" else "")
    engine = SessionEngine()
    ready = _login(engine, "lha", "204130")
    assert ready["fields"]["faceReady"] == "yes"
    assert engine._replace_id == "USR-READY"
    assert engine._same_saved_profile({"user_id": "USR-READY"}) is True
    assert engine._same_saved_profile({"user_id": "USR-OTHER"}) is False


def test_second_manual_account_also_opens_welcome():
    engine = SessionEngine()
    engine.submit("start_manual")
    allowed = _login(engine, "lha", "204130")
    assert allowed["screen"] == "welcome"
