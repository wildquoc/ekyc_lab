# FKYC

App desktop đăng ký và đăng nhập FaceID: quét căn cước, mã vạch thẻ sinh viên, rồi lưu khuôn mặt trên máy đang chạy.

<img width="1863" height="1312" alt="image" src="https://github.com/user-attachments/assets/2e39933b-0a22-42a4-96b7-cec473a24f60" />


## Cài và chạy

Cần Python 3.11 và Git LFS (file `backend/models/w600k_r50.onnx`).

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

Tài khoản trong `backend/security/accounts.json`:

Trên màn hình đầu, **Log in manually** mở hai ô username và mật khẩu. Đúng tài khoản thì vào Welcome.

**Login with FaceID** chỉ khớp khuôn mặt đã đăng ký trên chính máy đó. Tạm thời máy mới chưa có hồ sơ sẽ không nhận mặt.

## Đăng ký khuôn mặt

1. Đăng nhập thủ công.
2. Bấm **Register FaceID** (nếu username đã có hồ sơ trên máy này, nút là **Register again** và dòng chữ là **Your FaceID is ready**).
3. Quét căn cước, rồi thẻ sinh viên, rồi khuôn mặt.
4. Bấm Confirm. Hồ sơ gắn với username vừa đăng nhập.

Ảnh mặt và database nằm ở `backend/data/`, không có trên GitHub. Đăng ký trên máy nào thì chỉ máy đó đăng nhập được bằng mặt. Đăng ký lại cùng username sẽ ghi đè hồ sơ cũ của username đó trên máy này.

## Đóng gói

Máy đã cài `.venv` có thể chạy `.\build.bat`. Ngoài ra nếu không muốn cài venv thì test tạm thời bằng bản chạy exe là cả thư mục `dist\FKYC\`, không chỉ mỗi file exe, lưu hồ sơ ở `%LOCALAPPDATA%\FKYC` trên ổ C của máy, không dùng `backend/data` của repo.
