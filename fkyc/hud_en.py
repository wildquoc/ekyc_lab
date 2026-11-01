"""Desktop HUD copy in English. Backend strings stay Vietnamese."""

from __future__ import annotations

_EXACT = {
    "Login with FaceID": "Login with FaceID",
    "Show your Citizen Card": "Show your Citizen Card",
    "Show your Student Card": "Show your Student Card",
    "Look at the screen.": "Look at the screen.",
    "Looking at the screen.": "Looking at the screen.",
    "Đưa khuôn mặt vào khung oval": "Fit your face in the oval.",
    "Đưa khuôn mặt vào khung Oval": "Fit your face in the oval.",
    "Đưa khuôn mặt vào giữa khung Oval": "Fit your face in the oval.",
    "Đang kiểm tra chất lượng Camera...": "Checking the camera...",
    "Camera đạt chuẩn! Đưa khuôn mặt vào khung Oval": "Camera ready. Fit your face in the oval.",
    "Không tải được mô hình khuôn mặt": "Could not load the face model.",
    "Hãy tiến lại gần camera hơn nữa": "Move closer.",
    "Giữ yên khuôn mặt! Chuẩn bị quét ánh sáng màu...": "Hold still. Light scan next.",
    "Tuyệt vời! Giữ yên khuôn mặt...": "Great. Hold still.",
    "Giữ yên để chụp ảnh chân dung": "Hold still for the photo.",
    "Đã chụp chân dung": "Portrait captured.",
    "Đã nhận diện": "Identity confirmed.",
    "Chưa phát hiện thẻ. Đặt mặt trước CCCD vào khung chữ nhật": "Place the ID front in the frame.",
    "Không nhận ra CCCD. Hãy đưa MẶT TRƯỚC thẻ vào khung chữ nhật": "Show the ID front in the frame.",
    "Giữ thẻ trong khung, đang đọc mặt trước CCCD": "Hold the ID still in the frame.",
    "Đã trích xuất đầy đủ thông tin CCCD!": "ID details captured.",
    "Ảnh quá tối, vui lòng tăng ánh sáng": "Too dark. Add more light.",
    "Ảnh quá sáng, vui lòng giảm ánh sáng": "Too bright. Reduce the light.",
    "Thẻ bị lóa sáng, hãy nghiêng nhẹ thẻ để tránh phản quang": "Glare on the card. Tilt it a little.",
    "Ảnh hơi mờ, giữ yên hoặc đưa gần vùng Ngày sinh & Giới tính": "Image is blurry. Hold still.",
    "Đưa mã vạch ngang trên thẻ sinh viên vào khung": "Place the barcode in the frame.",
    "Xoay thẻ để mã vạch nằm ngang trong khung": "Rotate so the barcode is horizontal.",
    "Đã đọc mã sinh viên": "Student ID read.",
    "Chưa đọc được mã vạch.": "Could not read the barcode.",
    "Chưa đọc đủ thông tin CCCD.": "ID details are incomplete.",
    "Giữ yên. Đang quét ánh sáng màu": "Hold still. Scanning light.",
    "Vui lòng đưa mặt vào khung hình": "Move your face into the frame.",
    "Phát hiện nhiều khuôn mặt – chỉ một người duy nhất trong khung hình": "Only one person in the frame.",
    "Khuôn mặt bị lật ngược – Vui lòng giữ thẳng đầu (mắt ở trên, miệng ở dưới)": "Keep your head upright.",
    "Vui lòng bỏ tay ra khỏi khuôn mặt": "Take your hand off your face.",
    "Vui lòng tháo khẩu trang để tiếp tục": "Remove your mask.",
    "Vui lòng tháo kính râm / kính đen để tiếp tục": "Remove sunglasses.",
    "Nghiêng mặt nhẹ để tránh lóa kính": "Tilt a little to avoid glare.",
    "Không gian quá tối – hãy tăng thêm ánh sáng": "Too dark. Add more light.",
    "Ánh sáng quá mạnh – tránh đèn chiếu thẳng vào mặt": "Light is too strong.",
    "Khuôn mặt bị ngược sáng / thiếu chi tiết": "Backlit face. Face the light.",
    "Hãy tiến lại gần camera hơn": "Move closer.",
    "Hãy lùi ra xa camera một chút": "Move back a little.",
    "Khuôn mặt tràn khung – Hãy lùi ra xa camera một chút và căn vào giữa khung Oval": "Move back. Center in the oval.",
    "Khuôn mặt quá nhỏ – Hãy tiến lại gần camera hơn và căn vào giữa khung Oval": "Move closer. Center in the oval.",
    "Đưa toàn bộ khuôn mặt vào giữa khung Oval": "Fit your whole face in the oval.",
    "Đang nghiêng đầu quá nhiều – Vui lòng giữ thẳng đầu": "Head is tilted. Keep it upright.",
    "Đang ngẩng đầu quá cao – Hãy hạ cằm xuống và nhìn thẳng": "Lower your chin. Look straight.",
    "Đang cúi đầu quá thấp – Hãy nâng cằm lên và nhìn thẳng": "Raise your chin. Look straight.",
    "Hãy nhìn thẳng vào camera": "Look straight at the camera.",
    "Khuôn mặt hợp lệ! Giữ yên...": "Face looks good. Hold still.",
    "Từ từ quay đầu sang Trái": "Slowly turn your head Left.",
    "Từ từ quay đầu sang Phải": "Slowly turn your head Right.",
    "Không mở được camera. Hãy kiểm tra camera.": "Could not open the camera.",
    "Đăng ký khuôn mặt chưa đạt. Bấm Quay lại để làm lại.": "Enrollment failed. Go back to retry.",
    "Hồ sơ này đã tồn tại. Vui lòng đăng nhập.": "This profile already exists. Please log in.",
    "Hồ sơ đã tồn tại. Không thể đăng ký lại.": "This profile already exists.",
    "Thiếu thông tin CCCD. Bấm Redo để quét lại.": "Missing ID details. Tap Redo.",
    "Chưa có mã sinh viên.": "No student ID yet.",
    "Chưa có vector khuôn mặt. Làm lại bước đăng ký mặt.": "No face data. Redo enrollment.",
    "Không còn ảnh chân dung để lưu.": "No portrait to save.",
    "Khuôn mặt chưa đạt. Giữ thẳng và đủ sáng.": "Face not ready. Look straight.",
    "Không tìm thấy khuôn mặt trong hồ sơ.": "No matching face in records.",
}

_PHRASES = (
    ("Đã khóa Số CCCD & Họ tên! Đưa gần phần", "ID and name locked. Move"),
    ("Đưa gần phần", "Move"),
    ("vào khung để đọc rõ hơn", "closer to the frame."),
    ("Đang đọc đủ họ tên. Giữ thẻ trong khung", "Hold still. Reading the name."),
    ("Đang đọc, chưa rõ:", "Still missing:"),
    ("Đang đọc... chưa rõ:", "Still missing:"),
    ("Giữ thẻ trong khung", "Keep the card in the frame."),
    ("Ngày sinh", "Date of Birth"),
    ("Giới tính", "Gender"),
    ("Số CCCD", "ID number"),
    ("Họ tên", "Full name"),
    ("Đang tải mô hình OCR, vui lòng giữ thẻ trong khung...", "Loading OCR. Keep the card in the frame."),
    ("Đang tải mô hình OCR, vui lòng giữ thẻ trong khung", "Loading OCR. Keep the card in the frame."),
    ("Không thể nạp EasyOCR", "Could not load OCR"),
    ("Không thể nạp VietOCR", "Could not load OCR"),
    ("OCR lỗi:", "OCR error:"),
    ("Không đối sánh được:", "Could not match face:"),
    ("Không tìm thấy khuôn mặt trong hồ sơ.", "No matching face in records."),
    ("Bản OpenCV này không có bộ đọc mã vạch", "No barcode reader in this OpenCV build."),
    ("Không mở được bộ đọc mã vạch:", "Could not open barcode reader:"),
    ("Lỗi đọc mã vạch:", "Barcode error:"),
    ("Không lưu được hồ sơ:", "Could not save:"),
    ("Hồ sơ đã tồn tại", "This profile already exists"),
    ("CCCD này đã đăng ký", "This ID is already registered"),
    ("Mã sinh viên này đã đăng ký", "This student ID is already registered"),
    ("Khuôn mặt này đã có hồ sơ", "This face is already registered"),
    ("Không thể đăng ký lại.", "Registration is not allowed."),
    ("Vui lòng đăng nhập.", "Please log in."),
    ("Lỗi quét màu:", "Light scan error:"),
)


def to_en(text: str) -> str:
    if not text:
        return text
    raw = text.strip()
    if raw in _EXACT:
        return _EXACT[raw]
    out = raw
    for src, dst in _PHRASES:
        if src in out:
            out = out.replace(src, dst)
    return out
