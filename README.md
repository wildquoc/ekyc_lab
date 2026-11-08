# FKYC

App desktop đăng ký và đăng nhập FaceID: quét căn cước, mã vạch thẻ sinh viên, rồi lưu khuôn mặt trên máy đang chạy.

<img width="1280" height="731" alt="FKYC" src="https://github.com/user-attachments/assets/568e274a-5fea-4b6f-83da-531bbcf4c43b" />

## Cài và chạy

Cần Python 3.11 và [Git LFS](https://git-lfs.com) (file `backend/models/w600k_r50.onnx`).

```powershell
git lfs install
git lfs pull
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
.\run.bat
```

`run.bat` mở app Qt. Nếu hình camera không lên, tắt Zoom, Teams hoặc tab trình duyệt đang dùng webcam rồi chạy lại.

## Đăng nhập

Mọi máy clone về đều dùng chung tài khoản trong `backend/security/accounts.json`:

| Username | Password |
| --- | --- |
| pkq | 204120 |
| lha | 204130 |
| nvt | 190509 |

Trên màn hình đầu, **Log in manually** mở hai ô username và mật khẩu. Đúng tài khoản thì vào Welcome.

**Login with FaceID** chỉ khớp khuôn mặt đã đăng ký trên chính máy đó. Máy mới chưa có hồ sơ sẽ không nhận mặt.

## Đăng ký khuôn mặt

1. Đăng nhập thủ công.
2. Bấm **Register FaceID** (nếu username đã có hồ sơ trên máy này, nút là **Register again** và dòng chữ là **Your FaceID is ready**).
3. Quét căn cước, rồi thẻ sinh viên, rồi khuôn mặt.
4. Bấm Confirm. Hồ sơ gắn với username vừa đăng nhập.

Ảnh mặt và database nằm ở `backend/data/`, không có trên GitHub. Đăng ký trên máy nào thì chỉ máy đó đăng nhập được bằng mặt. Đăng ký lại cùng username sẽ ghi đè hồ sơ cũ của username đó trên máy này.

## Đóng gói

Máy đã cài `.venv` có thể chạy `.\build.bat`. Bản chạy là cả thư mục `dist\FKYC\`, không chỉ mỗi file exe. Bản exe lưu hồ sơ ở `%LOCALAPPDATA%\FKYC`, không dùng `backend/data` của repo.
