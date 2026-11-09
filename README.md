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

<img width="1025" height="694" alt="Screenshot 2026-11-09 132714" src="https://github.com/user-attachments/assets/c2c66cb4-4f30-48a1-95a3-b4e8e6988f80" />
<img width="1045" height="680" alt="Screenshot 2026-11-09 132741" src="https://github.com/user-attachments/assets/f1a4015c-ad44-4487-a55b-0afea2cb509c" />
<img width="1049" height="690" alt="Screenshot 2026-11-09 132801" src="https://github.com/user-attachments/assets/7168add3-7216-4a5a-885e-7ce630caee90" />
<img width="1027" height="676" alt="Screenshot 2026-11-09 132910" src="https://github.com/user-attachments/assets/dcb06d90-adad-4370-9e45-0d3ca7a05151" />
<img width="1010" height="672" alt="Screenshot 2026-11-09 133020" src="https://github.com/user-attachments/assets/63e8c8e6-98be-4198-9e89-bf4993d3233c" />

**Login with FaceID** chỉ khớp khuôn mặt đã đăng ký trên chính máy đó. Tạm thời máy mới chưa có hồ sơ sẽ không nhận mặt.

<img width="1040" height="682" alt="Screenshot 2026-11-09 133043" src="https://github.com/user-attachments/assets/3567f98c-1cbc-4ebd-9a6a-520b1d82459c" />

## Đăng ký khuôn mặt

1. Đăng nhập thủ công.
2. Bấm **Register FaceID** (nếu username đã có hồ sơ trên máy này, nút là **Register again** và dòng chữ là **Your FaceID is ready**).
3. Quét căn cước, rồi thẻ sinh viên, rồi khuôn mặt.
4. Bấm Confirm. Hồ sơ gắn với username vừa đăng nhập.

Username trong `backend/security/exceptions.json` (hiện có **nvt**) bỏ qua căn cước và thẻ sinh viên, đăng ký mặt trước, rồi nhập Date of Birth, Citizen ID, Name và Student ID.

Ảnh mặt và database nằm ở `backend/data/`, không có trên GitHub. Đăng ký trên máy nào thì chỉ máy đó đăng nhập được bằng mặt. Đăng ký lại cùng username sẽ ghi đè hồ sơ cũ của username đó trên máy này.

## Đóng gói

Máy đã cài `.venv` có thể chạy `.\build.bat`. Ngoài ra nếu không muốn cài venv thì test tạm thời bằng bản chạy exe là cả thư mục `dist\FKYC\`, không chỉ mỗi file exe, lưu hồ sơ ở `%LOCALAPPDATA%\FKYC` trên ổ C của máy, không dùng `backend/data` của repo.
