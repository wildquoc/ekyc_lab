"""Unit tests cho ArcFace feature extractor, UserRepository SQLite và FQA khuôn mặt."""
import base64
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from feature_extractor import get_arcface_extractor
from database import get_user_repository


def make_dummy_face_bgr(color=(128, 128, 128)) -> np.ndarray:
    img = np.full((480, 480, 3), color, dtype=np.uint8)
    # Vẽ mắt, mũi, miệng giả lập để FaceMesh hoặc crop có thể lấy được
    cv2.circle(img, (180, 180), 20, (0, 0, 0), -1)
    cv2.circle(img, (300, 180), 20, (0, 0, 0), -1)
    cv2.circle(img, (240, 260), 15, (50, 50, 50), -1)
    cv2.ellipse(img, (240, 340), (60, 25), 0, 0, 360, (0, 0, 200), -1)
    return img


def img_to_b64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", img_bgr)
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")


def test_arcface_extractor_basic():
    extractor = get_arcface_extractor()
    assert extractor.is_ready is True

    img1 = make_dummy_face_bgr((100, 120, 150))
    img2 = make_dummy_face_bgr((100, 120, 150))  # Giống nhau
    img3 = make_dummy_face_bgr((220, 50, 50))    # Khác nhau

    emb1 = extractor.extract_embedding(img1)
    emb2 = extractor.extract_embedding(img2)
    emb3 = extractor.extract_embedding(img3)

    assert emb1.shape == (512,)
    assert abs(np.linalg.norm(emb1) - 1.0) < 1e-4

    # Vector giống hệt nhau -> Similarity == 1.0
    sim_self = extractor.compute_similarity(emb1, emb2)
    assert sim_self > 0.99

    # Vector khác nhau -> Similarity thấp hơn
    sim_diff = extractor.compute_similarity(emb1, emb3)
    assert sim_diff < sim_self

    res = extractor.verify(emb1, emb2, threshold=0.50)
    assert res["is_match"] is True
    assert res["similarity"] > 0.99


def test_user_repository_crud():
    repo = get_user_repository()
    extractor = get_arcface_extractor()

    # Dọn dẹp nếu có
    repo.delete_user("USR-TEST-01")

    img = make_dummy_face_bgr((120, 140, 160))
    emb = extractor.extract_embedding(img)
    b64 = img_to_b64(img)

    # 1. Save user
    user = repo.save_user(
        full_name="Nguyễn Văn Kiểm Thử",
        embedding=emb,
        snapshot_b64=b64,
        user_id="USR-TEST-01",
        metadata={"department": "Security R&D"},
    )
    assert user["user_id"] == "USR-TEST-01"
    assert user["full_name"] == "Nguyen Van Kiem Thu"
    assert user["embedding_dim"] == 512
    assert len(user["embedding_preview"]) == 5

    # 2. Get user
    fetched = repo.get_user("USR-TEST-01")
    assert fetched is not None
    assert fetched["full_name"] == "Nguyen Van Kiem Thu"
    assert fetched["embedding"].shape == (512,)

    # 3. Match 1:1
    match_1_1 = repo.match_user_1_to_1(emb, "USR-TEST-01", threshold=0.45)
    assert match_1_1["is_match"] is True
    assert match_1_1["similarity"] > 0.99

    # 4. Match 1:N
    match_1_n = repo.match_user_1_to_n(emb, threshold=0.45)
    assert match_1_n["is_match"] is True
    assert match_1_n["top_match"]["user_id"] == "USR-TEST-01"

    # 5. List users
    users = repo.list_users()
    assert any(u["user_id"] == "USR-TEST-01" for u in users)

    # 6. Delete user
    del_ok = repo.delete_user("USR-TEST-01")
    assert del_ok is True
    assert repo.get_user("USR-TEST-01") is None


def test_verify_rejects_no_face_and_invalid_inputs():
    """Ảnh không có mặt thì FaceAnalyzer không detect — login/enroll không được match."""
    import config as C
    from face_analyzer import FaceAnalyzer

    analyzer = FaceAnalyzer()
    black_img = np.zeros((480, 640, 3), dtype=np.uint8)
    black = analyzer.analyze(black_img, oval=C.OVAL_NORMAL, fresh=True)
    assert not black.detected

    noise_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    noise = analyzer.analyze(noise_img, oval=C.OVAL_NORMAL, fresh=True)
    assert not noise.detected
    analyzer.close()

