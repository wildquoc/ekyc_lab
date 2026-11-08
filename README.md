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
    ├── security/accounts.json # tài khoản đăng nhập thủ công cho team test
    ├── data/ekyc.db           # hồ sơ FaceID local, không commit
    ├── data/portraits/        # ảnh mặt local, không commit
    └── models/                # MiniFASNet, ArcFace, VietOCR ONNX
```

`backend/security/accounts.json` đi cùng repo. Máy nào clone về cũng đăng nhập thủ công được bằng **pkq** / **204120** và **lha** / **204130**.

Ảnh mặt và `ekyc.db` không đưa lên GitHub. FaceID đăng ký trên máy nào thì chỉ máy đó nhận ra. Sau khi đăng nhập thủ công, Register FaceID trên máy đó sẽ gắn hồ sơ mới với username vừa nhập.
