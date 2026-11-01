# FKYC – desktop eKYC (PySide6)

Ứng dụng desktop đăng ký / đăng nhập FaceID: quét CCCD, mã vạch thẻ SV, enroll khuôn mặt (FQA, liveness, PAD), lưu embedding ArcFace vào SQLite.

## Chạy

Yêu cầu Python 3.11. Model nằm trong `backend/models/` (`w600k_r50.onnx` cần Git LFS).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt   # pytest

.\run.bat
```

`run.bat` gọi `python -m fkyc`. Nếu camera bị chiếm, đóng Zoom/Teams/tab khác đang mở webcam.

## Đóng gói bấm chạy (Windows)

Máy build cần `.venv` như trên. Máy chạy exe **không** cần Python.

```powershell
.\build.bat
```

Kết quả: `dist\FKYC\FKYC.exe`. Copy **cả thư mục** `dist\FKYC` sang máy khác, bấm `FKYC.exe`. Hồ sơ lưu ở `%LOCALAPPDATA%\FKYC`.

```powershell
python -m pytest backend/tests -q
```

## Cấu trúc

```
ekyc_lab/
├── run.bat
├── assets/                    # logo + icon login
├── fkyc/                      # Qt/QML desktop
└── backend/                   # OCR, barcode, face, SQLite
    ├── data/ekyc.db           # hồ sơ (không commit)
    └── models/                # MiniFASNet, ArcFace, VietOCR ONNX
```

Hồ sơ chỉ được ghi khi Confirm màn face result. Ảnh chân dung mã hóa tại `backend/data/portraits/*.enc`.
