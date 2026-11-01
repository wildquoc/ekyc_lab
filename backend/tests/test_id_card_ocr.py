"""Unit & integration tests cho module nhận diện, OCR CCCD và kiểm tra trùng lặp danh tính."""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from database import DuplicateUserError, UserRepository
from id_card_ocr import (
    CHIP_ROIS,
    CHIP_ROIS_NEW,
    WARP_H,
    WARP_W,
    assess_quality,
    crop_chip_rois,
    fields_from_roi_texts,
    group_lines,
    is_id_card_text,
    locate_card,
    normalize_dob,
    normalize_gender,
    normalize_id_number,
    name_between_id_and_dob,
    parse_cccd_lines,
    pick_name,
    pretty_name,
    warp_card,
)


def test_parse_cccd_2021_chip_format():
    lines = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập - Tự do - Hạnh phúc",
        "CĂN CƯỚC CÔNG DÂN",
        "Citizen Identity Card",
        "Số / No.: 079203001234",
        "Họ và tên / Full name:",
        "NGUYỄN VĂN AN",
        "Ngày sinh / Date of birth: 15/08/2003",
        "Giới tính / Sex: Nam   Quốc tịch / Nationality: Việt Nam",
        "Quê quán / Place of origin: Quận 1, TP. Hồ Chí Minh",
        "Có giá trị đến / Date of expiry: 15/08/2028",
    ]
    res = parse_cccd_lines(lines)
    assert res == {
        "id_number": "079203001234",
        "full_name": "NGUYEN VAN AN",
        "dob": "15/08/2003",
        "gender": "Nam",
    }
    assert is_id_card_text(lines)


def test_parse_cccd_2024_values_below_dob_sex_labels():
    lines = [
        "Căn cước",
        "Identity card",
        "Số định danh cá nhân / Personal identification number",
        "079203001234",
        "Họ, chữ đệm và tên khai sinh / Full name",
        "NGUYỄN VĂN AN",
        "Ngày, tháng, năm sinh / Date of birth    Giới tính / Sex",
        "15/08/2003    Nữ",
        "Quốc tịch / Nationality: Việt Nam",
    ]
    res = parse_cccd_lines(lines)
    assert res == {
        "id_number": "079203001234",
        "full_name": "NGUYEN VAN AN",
        "dob": "15/08/2003",
        "gender": "Nữ",
    }
    assert is_id_card_text(lines)
    assert name_between_id_and_dob(lines) == "NGUYEN VAN AN"

    male = parse_cccd_lines(
        [
            "Căn cước",
            "Identity card",
            "Số định danh cá nhân / Personal identification number",
            "001198005670",
            "Họ, chữ đệm và tên khai sinh / Full name",
            "TRẦN THỊ BÍCH NGỌC",
            "Ngày tháng năm sinh / Date of birth  Giới tính / Sex",
            "02/11/1998  Nam",
        ]
    )
    assert male["full_name"] == "TRAN THI BICH NGOC"
    assert male["dob"] == "02/11/1998"
    assert male["gender"] == "Nam"

    assert pick_name("Họ, chữ đệm và tên khai sinh / Full name\nNGUYEN VAN AN") == "NGUYEN VAN AN"
    from_roi = fields_from_roi_texts(
        {
            "id_number": "079203001234",
            "full_name": "Họ, chữ đệm và tên khai sinh / Full name\nNGUYEN VAN AN",
            "dob": "Ngày, tháng, năm sinh / Date of birth",
            "sex": "Giới tính / Sex",
            "lower_row": "Ngày, tháng, năm sinh / Date of birth    Giới tính / Sex\n15/08/2003 Nữ",
        }
    )
    assert from_roi["id_number"] == "079203001234"
    assert from_roi["full_name"] == "NGUYEN VAN AN"
    assert from_roi["dob"] == "15/08/2003"
    assert from_roi["gender"] == "Nữ"


def test_parse_can_cuoc_2024_female_and_ocr_noise():
    lines = [
        "CĂN CƯỚC / IDENTITY CARD",
        "Số định danh cá nhân / Personal identification number",
        "0011 9800 567O",  # chữ O cuối bị nhầm thay vì 0, có khoảng trắng giữa các cụm số
        "Họ, chữ đệm và tên khai sinh / Full name TRẦN THỊ BÍCH NGỌC",  # mất dấu ':'
        "Ngày, tháng, năm sinh / Date of birth: 02-11-1998",
        "Giới tính / Sex: Nữ   Quốc tịch / Nationality: Việt Nam",
    ]
    res = parse_cccd_lines(lines)
    assert res == {
        "id_number": "001198005670",
        "full_name": "TRAN THI BICH NGOC",
        "dob": "02/11/1998",
        "gender": "Nữ",
    }


def test_locate_and_warp_card_on_synthetic_scene():
    scene = np.full((720, 1280, 3), 25, dtype=np.uint8)
    # Vẽ thẻ trắng tỉ lệ ~1.586 ở giữa khung
    card_w, card_h = 640, 404
    x0, y0 = (1280 - card_w) // 2, (720 - card_h) // 2
    cv2.rectangle(scene, (x0, y0), (x0 + card_w, y0 + card_h), (235, 235, 235), -1)
    cv2.putText(scene, "CAN CUOC CONG DAN", (x0 + 80, y0 + 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
    cv2.putText(scene, "079203001234", (x0 + 80, y0 + 170), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 2)

    quad = locate_card(scene)
    assert quad is not None
    assert quad.shape == (4, 2)

    warped = warp_card(scene, quad)
    assert warped.shape[1] == 1200
    q = assess_quality(warped)
    assert q["ok"] is True


def test_group_lines_reading_order():
    raw = [
        ([[200, 10], [320, 10], [320, 40], [200, 40]], "NGUYỄN", 0.92),
        ([[330, 12], [420, 12], [420, 40], [330, 40]], "VĂN A", 0.90),
        ([[200, 70], [450, 70], [450, 100], [200, 100]], "15/08/2003", 0.95),
    ]
    assert group_lines(raw) == ["NGUYỄN VĂN A", "15/08/2003"]


def test_find_by_identity_and_duplicate_block():
    repo = UserRepository()
    test_uid = "USR-TEST-OCR-DUP"
    test_id = "036198007654"
    test_sid = "TESTSID999"
    repo.delete_user(test_uid)

    emb = np.ones(512, dtype=np.float32)
    try:
        saved = repo.save_user(
            full_name="NGUYỄN VĂN TESTOCR",
            embedding=emb,
            snapshot_b64="data:image/jpeg;base64,AA==",
            user_id=test_uid,
            metadata={
                "id_number": test_id,
                "dob": "09/09/1991",
                "gender": "Nam",
                "student_id": test_sid,
                "identity_source": "cccd_ocr",
            },
        )
        assert saved["full_name"] == "NGUYEN VAN TESTOCR"
        assert saved["user_id"] == test_uid

        with pytest.raises(DuplicateUserError):
            repo.save_user(
                full_name="NGUYEN VAN TESTOCR",
                embedding=emb,
                snapshot_b64="data:image/jpeg;base64,AA==",
                metadata={"id_number": test_id, "dob": "09/09/1991", "gender": "Nam"},
            )

        # 1. Khớp theo Số CCCD
        by_id = repo.find_by_identity(id_number=test_id)
        assert by_id is not None
        assert by_id["user_id"] == saved["user_id"]
        assert by_id["matched_by"] == "id_number"
        by_sid = repo.find_by_identity(student_id=test_sid)
        assert by_sid is not None
        assert by_sid["user_id"] == saved["user_id"]
        assert by_sid["matched_by"] == "student_id"

        # 2. Khớp theo tổ hợp (Họ tên + Ngày sinh + Giới tính)
        by_person = repo.find_by_identity(
            id_number="999999999999",
            full_name="nguyễn văn testocr",
            dob="09/09/1991",
            gender="Nam",
        )
        assert by_person is not None
        assert by_person["user_id"] == saved["user_id"]
        assert by_person["matched_by"] == "name_dob_gender"

        # 3. Không khớp khi khác thông tin
        assert repo.find_by_identity(id_number="000000000000", full_name="LÊ THỊ B", dob="01/01/2000", gender="Nữ") is None
    finally:
        repo.delete_user(test_uid)


def test_delete_all_users_is_blocked():
    repo = UserRepository()
    with pytest.raises(PermissionError, match="Không được xóa toàn bộ"):
        repo.delete_all_users()


def test_phase2_locked_name_id_and_noisy_dob_gender():
    # Khi đã khóa Tên & Số CCCD: giữ nguyên không đổi, kể cả khi ảnh zoom chỉ có phần dưới
    # và dấu '/' trong ngày sinh bị OCR đọc nhầm thành '1' (1510812003) hoặc mất nhãn Giới tính
    known = {
        "id_number": "079203001234",
        "full_name": "NGUYỄN HOÀI NAM",
        "dob": None,
        "gender": None,
    }
    zoomed_lines = [
        "NGUYỄN HOÀI NAM",  # dòng tên (chứa chữ NAM trong tên, không được nhầm sang giới tính)
        "Ngav sinh / Date of birth 1510812003",  # dấu '/' bị đọc nhầm thành '1'
        "G10i tinh / Sex:Nữ Quốc tịch Việt Nam",  # nhãn bị nhiễu, Nữ dính sát dấu ':'
        "Quê quán: Nam Định",
    ]
    parsed = parse_cccd_lines(zoomed_lines, known_fields=known)
    assert parsed == {
        "id_number": "079203001234",
        "full_name": "NGUYEN HOAI NAM",
        "dob": "15/08/2003",
        "gender": "Nữ",
    }


def test_reject_can_cuoc_cong_dan_as_name_and_require_name_below_id():
    # Trường hợp OCR bị nhiễu chữ "Căn Cuoc cong dan" / "CĂN CU0C C0NG OAN" ở phía trên số CCCD,
    # và chưa đọc rõ dòng tên bên dưới -> tuyệt đối không lấy tiêu đề thẻ làm Họ và tên
    noisy_header_only = [
        "C0NG HOA XA HOI CHU NGHIA VIET NAM",
        "Căn Cuoc cong dan",
        "CĂN CU0C C0NG OAN",
        "Số / No.: 079203001234",
        "Họ và tên / Full name:",
    ]
    res_partial = parse_cccd_lines(noisy_header_only)
    assert res_partial["id_number"] == "079203001234"
    assert res_partial["full_name"] is None

    # Khi có dòng Họ và tên hợp lệ nằm BÊN DƯỚI dòng số CCCD -> lấy đúng dòng bên dưới
    with_real_name_below = noisy_header_only + [
        "PHẠM MINH Kiệt",
        "Ngày sinh: 115/08/2003",  # dấu ':' trước ngày sinh bị đọc nhầm thành '1'
        "Giới tính: Nam",
    ]
    res_full = parse_cccd_lines(with_real_name_below)
    assert res_full == {
        "id_number": "079203001234",
        "full_name": "PHAM MINH KIET",
        "dob": "15/08/2003",
        "gender": "Nam",
    }


def test_normalize_id_dob_gender_and_diacritics():
    assert normalize_id_number("07920300l23B") == "079203001238"
    assert normalize_id_number("O79D03001234") == "079003001234"
    assert normalize_id_number("079 203 001 234") == "079203001234"
    assert normalize_id_number("Số / No.: 079203001234") == "079203001234"
    assert normalize_id_number("079203001/234") == "079203001234"
    assert normalize_dob("Ngày sinh 15/08/2003") == "15/08/2003"
    assert normalize_dob("Date of birth 1510812003") == "15/08/2003"
    assert normalize_gender("Nam") == "Nam"
    assert normalize_gender("Sex: Nữ") == "Nữ"
    assert normalize_gender("Giới tính / Sex: Nữ   Quốc tịch / Nationality: Việt Nam") == "Nữ"
    assert normalize_gender("Sex: Nu Quoc tich Viet Nam") == "Nữ"
    assert normalize_gender("Quốc tịch Việt Nam") is None
    assert normalize_gender("Việt Nam") is None
    assert normalize_gender("Quê quán: Nam Định") is None
    assert normalize_gender("Nam Định") is None
    assert normalize_gender("Sex: Nam   Quốc tịch: Việt Nam") == "Nam"
    assert pretty_name("NGUYỄN VĂN AN") == "NGUYEN VAN AN"
    assert pretty_name("CĂN CƯỚC CÔNG DÂN") is None


def test_crop_five_chip_rois():
    warped = np.zeros((WARP_H, WARP_W, 3), dtype=np.uint8)
    rois = crop_chip_rois(warped)
    assert set(rois) == set(CHIP_ROIS)
    assert all(crop.size > 0 for crop in rois.values())
    assert rois["id_number"].shape[0] < rois["lower_row"].shape[0]
    rois_new = crop_chip_rois(warped, layout="new")
    assert set(rois_new) == set(CHIP_ROIS_NEW)
    assert all(crop.size > 0 for crop in rois_new.values())
    assert rois_new["sex"].shape[1] > rois["sex"].shape[1]
    assert rois_new["dob"].shape[0] > rois["dob"].shape[0]


def test_line_strips_splits_two_rows():
    from id_card_ocr import line_strips, word_crops

    img = np.full((80, 240, 3), 245, dtype=np.uint8)
    cv2.rectangle(img, (8, 8), (230, 28), (15, 15, 15), -1)
    cv2.rectangle(img, (8, 48), (200, 70), (15, 15, 15), -1)
    strips = line_strips(img, max_lines=3)
    assert len(strips) >= 2
    line = np.full((36, 300, 3), 245, dtype=np.uint8)
    cv2.rectangle(line, (8, 8), (70, 28), (15, 15, 15), -1)
    cv2.rectangle(line, (90, 8), (160, 28), (15, 15, 15), -1)
    cv2.rectangle(line, (180, 8), (250, 28), (15, 15, 15), -1)
    assert len(word_crops(line)) >= 3


def test_pretty_name_strips_label_prefix():
    assert pretty_name("Họ và tên NGUYỄN VĂN AN") == "NGUYEN VAN AN"
    assert pretty_name("HO VA TEN NGUYEN VAN AN") == "NGUYEN VAN AN"
    assert pick_name("HO VA TEN / Full name", "NGUYEN VAN AN") == "NGUYEN VAN AN"
    assert pick_name("Ho va ten", "NGUYEN THI BICH NGOC") == "NGUYEN THI BICH NGOC"
    assert pretty_name("NGUYEN THI BICH NGOC") == "NGUYEN THI BICH NGOC"
    assert pretty_name("NGUYEN THI") is None  # mới họ+đệm, chưa có tên
    assert pick_name("NGUYEN VAN", "AN") == "NGUYEN VAN AN"
    assert pick_name("LE MINH", "LE MINH TUAN") == "LE MINH TUAN"
    assert pick_name("NGUYEN VAN AN", "AN") == "NGUYEN VAN AN"
    assert pick_name("NGUYEN VAN AN", "TRAN THI BICH NGOC") == "NGUYEN VAN AN"
    from id_card_ocr import draft_person_name, prefer_name, valid_person_name
    assert prefer_name("NGUYEN VAN AN", "NGUYEN QUAN KIEN THUY") == "NGUYEN VAN AN"
    assert prefer_name("NGUYEN VAN AN", "TRAN THI BICH NGOC") == "NGUYEN VAN AN"
    assert prefer_name("LE MINH", "LE MINH TUAN") == "LE MINH TUAN"
    assert valid_person_name("NGUYEN VAN") is None
    assert draft_person_name("NGUYEN VAN") == "NGUYEN VAN"
    assert valid_person_name("LE MINH") == "LE MINH"
    assert valid_person_name("NGUYEN VAN AN") == "NGUYEN VAN AN"
    assert pretty_name("NGUYỄN QUỐC ANH") == "NGUYEN QUOC ANH"
    assert pretty_name("NGUYEN VAN QUOC") == "NGUYEN VAN QUOC"
    assert pretty_name("NGUYỄN QUỐC ANH Quốc tịch Việt Nam") == "NGUYEN QUOC ANH"


def test_name_stops_before_sex_and_dob_junk():
    from id_card_ocr import name_between_id_and_dob, valid_person_name

    garbage = "NGUYÊN THI SAI NAM SCH NGHIE T NHINH"
    taken = pretty_name(garbage) or ""
    assert "SAI" not in taken
    assert "SCH" not in taken
    assert "NHINH" not in taken
    assert pretty_name("NGUYỄN THỊ BÍCH NGỌC SAI NAM") == "NGUYEN THI BICH NGOC"
    layout = name_between_id_and_dob(
        [
            "079203001234",
            "Họ và tên / Full name",
            "NGUYỄN THỊ ANH",
            "Ngày sinh / Date of birth: 15/08/2003",
            "Giới tính / Sex: Nam",
        ]
    )
    assert layout == "NGUYEN THI ANH"


def test_name_not_taken_from_address():
    from id_card_ocr import name_between_id_and_dob, valid_person_name

    assert pretty_name("PHÚ XUÂN NHÀ BÈ") is None
    assert valid_person_name("PHÚ XUÂN NHÀ BÈ") is None
    assert pick_name("NGUYỄN THỊ ANH", "PHÚ XUÂN NHÀ BÈ") == "NGUYEN THI ANH"
    assert pick_name("PHÚ XUÂN NHÀ BÈ", "NGUYỄN THỊ ANH") == "NGUYEN THI ANH"
    layout = name_between_id_and_dob(
        [
            "079203001234",
            "Họ và tên / Full name",
            "NGUYỄN THỊ ANH",
            "Ngày sinh / Date of birth: 15/08/2003",
            "Giới tính / Sex: Nữ",
            "Quê quán / Place of origin: Phú Xuân, Nhà Bè",
            "Nơi thường trú: Phú Xuân, Nhà Bè, TP.HCM",
        ]
    )
    assert layout == "NGUYEN THI ANH"
    no_dob = name_between_id_and_dob(
        [
            "079203001234",
            "Họ và tên / Full name",
            "NGUYỄN THỊ ANH",
            "Giới tính / Sex: Nữ",
            "PHÚ XUÂN NHÀ BÈ",
        ]
    )
    assert no_dob == "NGUYEN THI ANH"
    fields = fields_from_roi_texts(
        {
            "id_number": "079203001234",
            "full_name": "PHÚ XUÂN NHÀ BÈ",
            "dob": "15/08/2003",
            "sex": "Nữ",
            "lower_row": "Phú Xuân, Nhà Bè",
        }
    )
    assert fields["full_name"] is None


def test_name_and_dob_not_taken_from_id_blob():
    fields = fields_from_roi_texts(
        {
            "id_number": "079203001234",
            "full_name": "HO VA TEN / Full name\nNGUYEN VAN AN",
            "dob": "Date of birth: 15/08/2003",
            "sex": "Nam",
            "lower_row": "15/08/2003 Nam",
        }
    )
    assert fields["id_number"] == "079203001234"
    assert fields["full_name"] == "NGUYEN VAN AN"
    assert fields["dob"] == "15/08/2003"
    assert fields["gender"] == "Nam"


def test_gender_not_taken_from_nationality_or_hometown():
    female = fields_from_roi_texts(
        {
            "id_number": "001198005670",
            "full_name": "TRAN THI BICH NGOC",
            "dob": "02/11/1998",
            "sex": "Giới tính / Sex: Nữ Quốc tịch Việt Nam",
            "lower_row": "02/11/1998 Quốc tịch Việt Nam",
        }
    )
    assert female["gender"] == "Nữ"
    assert female["dob"] == "02/11/1998"
    assert female["full_name"] == "TRAN THI BICH NGOC"

    slid = fields_from_roi_texts(
        {
            "id_number": "001198005670",
            "full_name": "TRAN THI BICH NGOC",
            "dob": "02/11/1998",
            "sex": "Quốc tịch Việt Nam",
            "lower_row": "Quê quán: Nam Định",
        }
    )
    assert slid["gender"] is None
    assert slid["full_name"] == "TRAN THI BICH NGOC"
    assert slid["dob"] == "02/11/1998"

    male = fields_from_roi_texts(
        {
            "id_number": "079203001234",
            "full_name": "NGUYEN VAN AN",
            "dob": "15/08/2003",
            "sex": "Sex: Nam Quốc tịch Việt Nam",
            "lower_row": "15/08/2003 Việt Nam",
        }
    )
    assert male["gender"] == "Nam"


def test_reject_garbled_citizen_id():
    from id_card_ocr import accept_id_number, prefer_id

    assert accept_id_number("001000000111") is None
    assert accept_id_number("000000000000") is None
    assert accept_id_number("111111111111") is None
    assert accept_id_number("OOIOOOOOOIII") is None
    assert normalize_id_number("OOIOOOOOOIII") is None
    assert accept_id_number("079203001234") == "079203001234"
    assert accept_id_number("001198005670") == "001198005670"
    assert accept_id_number("07920300l23B") == "079203001238"
    assert accept_id_number("079003001234") == "079003001234"
    assert prefer_id("079203001234", "001000000111") == "079203001234"
    assert prefer_id("001000000111", "079203001234") == "079203001234"
    assert prefer_id(None, "001000000111") is None
    assert prefer_id("001000000111", "001000000111") is None

    garbage = fields_from_roi_texts(
        {
            "id_number": "001000000111",
            "full_name": "NGUYEN VAN AN",
            "dob": "15/08/2003",
            "sex": "Nam",
            "lower_row": "15/08/2003 Nam",
        }
    )
    assert garbage["id_number"] is None
    assert garbage["full_name"] == "NGUYEN VAN AN"
    assert garbage["dob"] == "15/08/2003"
    assert garbage["gender"] == "Nam"

    noisy = parse_cccd_lines(
        [
            "CĂN CƯỚC CÔNG DÂN",
            "001000000111",
            "Số / No.: 079203001234",
            "Họ và tên / Full name: NGUYỄN VĂN AN",
            "Ngày sinh / Date of birth: 15/08/2003",
            "Giới tính / Sex: Nam",
        ]
    )
    assert noisy["id_number"] == "079203001234"
    assert noisy["full_name"] == "NGUYEN VAN AN"
    assert noisy["dob"] == "15/08/2003"
    assert noisy["gender"] == "Nam"


def test_login_and_face_share_portrait_canvas():
    from fkyc.pipeline import _FACE_CANVAS, _FACE_WELL_ASPECT, _face_view

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    view = _face_view(frame)
    assert (view.shape[1], view.shape[0]) == _FACE_CANVAS
    assert abs(_FACE_WELL_ASPECT - 480 / 600) < 1e-6


def test_face_view_matches_qml_portrait_well():
    from fkyc.pipeline import _FACE_CANVAS, _FACE_WELL_ASPECT, _face_view, _visible_in_well

    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    vis = _visible_in_well(frame, _FACE_WELL_ASPECT)
    assert vis.shape[0] == 540
    assert vis.shape[1] < frame.shape[1]
    assert abs(vis.shape[1] / vis.shape[0] - _FACE_WELL_ASPECT) < 0.04
    view = _face_view(frame)
    assert (view.shape[1], view.shape[0]) == _FACE_CANVAS
    assert abs(_FACE_WELL_ASPECT - 480 / 600) < 1e-6


def test_webcam_guide_crop_matches_qml_overlay():
    from fkyc.pipeline import _crop_id_guide, _WELL_ASPECT, _GUIDE_W_FRAC, _CARD_RATIO

    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    crop = _crop_id_guide(frame)
    vis_w = int(round(540 * _WELL_ASPECT))
    expect_w = int(vis_w * _GUIDE_W_FRAC)
    expect_h = int(round(expect_w / _CARD_RATIO))
    # pad 4% mỗi phía
    assert abs(crop.shape[1] - expect_w) <= expect_w * 0.12
    assert abs(crop.shape[0] - expect_h) <= expect_h * 0.12
    assert 1.45 <= crop.shape[1] / crop.shape[0] <= 1.72

