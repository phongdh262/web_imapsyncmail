# Test Cases cho Hệ thống Web ImapsyncMail

Tài liệu này bao gồm các test cases (kịch bản kiểm thử) thủ công cho toàn bộ các tính năng hiện có trên hệ thống Web ImapsyncMail. Các testcase được chia theo từng Module chính của hệ thống.

---

## 1. Module Xác thực (Authentication)
**Mục tiêu:** Đảm bảo hệ thống bảo mật, chỉ người dùng hợp lệ mới có thể truy cập bằng API hoặc giao diện cần xác thực (nếu có form đăng nhập).

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| AUTH-01 | Đăng nhập với thông tin hợp lệ | 1. Gửi request POST đến `/api/login` với username và password đúng. | Trả về HTTP 200, kèm theo `access_token` (JWT Token). |
| AUTH-02 | Đăng nhập với sai mật khẩu | 1. Gửi request POST đến `/api/login` với username đúng, password sai. | Trả về HTTP 401 Unauthorized kèm thông báo lỗi. |
| AUTH-03 | Đăng nhập với tài khoản admin mặc định | 1. Thử đăng nhập lần đầu tiên với `phongdh` và mật khẩu trong biến môi trường. | Hệ thống tự động tạo tài khoản Admin và sinh token đăng nhập thành công. |

---

## 2. Module Dashboard (Trang Chủ / Tổng quan)
**Mục tiêu:** Kiểm tra giao diện Dashboard, các thông số thống kê, và danh sách luồng chuyển đổi.

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| DB-01 | Hiển thị thông số tổng quan | 1. Truy cập `index.html` (Dashboard).<br>2. Xem các chỉ số: Tổng số job, Job đang chạy, Mailbox thành công, Dung lượng đã chuyển. | Các thông số hiển thị chính xác (khớp với `/api/stats`). |
| DB-02 | Hiển thị danh sách Migration Jobs | 1. Kéo xuống phần danh sách Job.<br>2. Kiểm tra tên, source/target, trạng thái, và tiến độ. | Danh sách Job tải lên thành công, sắp xếp từ mới nhất tới cũ nhất. |
| DB-03 | Xoá một Job cụ thể | 1. Bấm nút Xoá trên một Job đã dừng (Completed/Failed).<br>2. Xác nhận xoá. | Hiển thị thông báo xoá thành công, Job biến mất khỏi danh sách. |
| DB-04 | Xoá tất cả lịch sử Jobs (Clear History) | 1. Bấm nút Xoá tất cả lịch sử.<br>2. Xác nhận. | File log và DB bị xoá sạch, danh sách trống rỗng. |
| DB-05 | Xoá Job đang chạy | 1. Tìm một Job đang ở trạng thái `running`.<br>2. Bấm xoá. | Hệ thống báo lỗi "Không thể xoá Job đang chạy, vui lòng dừng trước". |

---

## 3. Module Tạo Job (Create Job)
**Mục tiêu:** Đảm bảo tính năng cấu hình và tạo ra tiến trình di chuyển email (Job) hoạt động đúng đắn.

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CJ-01 | Tạo Job với thông tin hợp lệ | 1. Vào `create-job.html`.<br>2. Nhập các thông tin bắt buộc: Host nguồn/đích, Cổng, Bảo mật, Mật khẩu Job.<br>3. Bấm Tạo Migration Job. | API `/api/jobs` trả về Job ID mới, chuyển hướng sang màn hình thêm Mailbox hoặc Detail. |
| CJ-02 | Bỏ trống các trường bắt buộc | 1. Để trống một trong các trường: Host Nguồn hoặc Host Đích.<br>2. Bấm Tạo. | Form báo lỗi validate yêu cầu nhập đủ thông tin. |
| CJ-03 | Tạo Job bảo mật bằng mật khẩu | 1. Nhập mật khẩu bảo vệ Job.<br>2. Lưu lại. | Backend tiến hành mã hoá mật khẩu (hash), trả cookie xác thực lưu tạm thời. |

---

## 4. Module Chi tiết Job (Job Detail) và Quản lý Mailbox
**Mục tiêu:** Kiểm tra khả năng quản lý danh sách email cần chuyển đổi trong một Job.

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| JD-01 | Truy cập Job yêu cầu mật khẩu | 1. Mở link `/job-detail.html?id=[job_id]` trên trình duyệt ẩn danh.<br>2. Hệ thống hỏi mật khẩu, nhập đúng. | Xác thực thành công thông qua `/api/jobs/{job_id}/verify`, hiển thị chi tiết Job. |
| JD-02 | Truy cập Job với mật khẩu sai | 1. Truy cập link URL của một Job có mật khẩu.<br>2. Nhập mật khẩu sai. | Màn hình tiếp tục khoá, hiện lỗi "Incorrect password". |
| JD-03 | Thêm Mailbox thủ công | 1. Trong phần Thêm Mailbox, nhập Email nguồn/đích, Mật khẩu nguồn/đích.<br>2. Bấm Thêm (Submit). | Báo thành công, hộp thư xuất hiện trong danh sách và bắt đầu chạy (Pending -> Running). |
| JD-04 | Tải lên CSV hàng loạt | 1. Chuẩn bị file CSV đúng định dạng (SourceEmail, SourcePass, TargetEmail, TargetPass).<br>2. Bấm Tải CSV.<br>3. Chọn file tải lên. | Hệ thống ghi nhận các dòng hợp lệ, tiến trình tải vào hệ thống và khởi động Worker thực thi. |
| JD-05 | Xử lý file CSV sai định dạng | 1. Tải lên file txt rỗng hoặc file CSV chỉ có 2 cột.<br>2. Bấm upload. | Hệ thống bỏ qua các dòng không đủ thông tin, không bị crash / hiện thông báo lỗi phù hợp. |

---

## 5. Module Giám sát tiến độ & Thao tác tiến trình
**Mục tiêu:** Theo dõi và can thiệp (dừng, thử lại) các tiến trình đồng bộ dữ liệu imapsync.

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| PR-01 | Cập nhật thống kê Real-time | 1. Ở trang chi tiết job, quan sát thanh tiến độ của Job và của từng Mailbox. | Thanh phần trăm progress bar tự động cập nhật khi API refresh, Data Transferred tăng lên. |
| PR-02 | Xem log trực tiếp của một Mailbox | 1. Bấm nút "Logs" hoặc "Xem Log" của một dòng mailbox đang chạy / đã xong. | Mở ra Modal xem log cập nhật theo thời gian thực hoặc nội dung `.log` file tĩnh. |
| PR-03 | Tải toàn bộ Logs dạng ZIP | 1. Ở thông tin Job, bấm nút "Download All Logs (ZIP)". | Trình duyệt tải về một file `.zip`. Bóc nén ra thấy file `summary.txt` và các file `[email].log`. |
| PR-04 | Dừng (Stop) một Mailbox đang chạy | 1. Ở trang detail, tìm một mailbox `running`.<br>2. Bấm nút Stop/Dừng. | Tiến trình imapsync bị ngắt (kill), trạng thái chuyển sang `Failed / Stopped by user`. |
| PR-05 | Thử lại (Retry) một Mailbox bị lỗi | 1. Tìm một mailbox ở trạng thái `failed` / `stopped`.<br>2. Bấm nút Retry. | Trạng thái chuyển về `pending` và bắt đầu chạy lại, xuất hiện log mới. |
| PR-06 | Huỷ toàn bộ Job (Cancel Job) | 1. Bấm nút "Cancel Job" lúc đang có nhiều mailbox tiến trình `running`. | Hệ thống gửi lệnh dừng toàn bộ, cờ trạng thái Job chuyển sang `Failed`, các Mailbox dừng theo. |

---

## 6. Khác (System & Health)
| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| SYS-01 | Kiểm tra Hệ thống (Health Check) | 1. Gọi API `GET /api/health` | Trả về thông tin: Python version, thư mục, trạng thái DB "connected", thư mục imapsync. |
| SYS-02 | Giao diện Responsive | 1. Mở trang Web trên Điện thoại / màn hình nhỏ (hoặc F12 giả lập di động). | Các Sidebar ẩn hiện đúng, bảng dữ liệu (Table) có thanh cuộn ngang, nút bấm không bị chèn nhau. |
| SYS-03 | Điều hướng thanh Menu | 1. Click từng menu trên Sidebar: Dashboard, Tạo Job Di Chuyển, Hướng Dẫn Sủ dụng. | Nội dung chính chuyển đổi tương ứng, URL cập nhật đúng. |

## 7. Module Kiểm tra Mật khẩu Ứng dụng (Check Credentials)
**Mục tiêu:** Đảm bảo tính năng kiểm tra thông tin đăng nhập IMAP (App Password) hoạt động chính xác cho cả chế độ Single và Bulk.

### 7.1. Single Check

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CC-01 | Kiểm tra với email Gmail hợp lệ | 1. Truy cập `check-credentials.html`.<br>2. Nhập email Gmail + App Password đúng.<br>3. Bấm **Verify Credentials**. | Hiển thị kết quả **SUCCESS ✓**, badge màu xanh, provider = "Gmail", message chứa "imap.gmail.com". |
| CC-02 | Kiểm tra với email Yandex hợp lệ | 1. Nhập email Yandex + mật khẩu đúng.<br>2. Bấm **Verify Credentials**. | Hiển thị **SUCCESS ✓**, provider = "Yandex". |
| CC-03 | Kiểm tra với sai mật khẩu | 1. Nhập email Gmail đúng + mật khẩu sai.<br>2. Bấm **Verify Credentials**. | Hiển thị **FAILED ✗**, message chứa "Authentication failed". |
| CC-04 | Bỏ trống email hoặc mật khẩu | 1. Để trống một trong hai trường.<br>2. Bấm **Verify Credentials**. | Hiển thị toast cảnh báo "Please enter email and password", không gọi API. |
| CC-05 | Kiểm tra với domain không hỗ trợ (không có custom host) | 1. Nhập email `user@custom-domain.vn` + mật khẩu.<br>2. Không nhập Custom IMAP Server.<br>3. Bấm Verify. | Hiển thị **FAILED ✗**, message chứa "Cannot detect IMAP server". |
| CC-06 | Kiểm tra với Custom IMAP Server | 1. Nhập email `user@custom-domain.vn`.<br>2. Mở rộng **Custom IMAP Server**, nhập Host và Port.<br>3. Bấm **Verify Credentials**. | Hệ thống sử dụng host/port tuỳ chỉnh để kiểm tra, trả kết quả phù hợp. |
| CC-07 | Giữ lại thông tin sau khi check | 1. Nhập email + password.<br>2. Bấm Verify Credentials.<br>3. Quan sát các trường nhập. | Sau khi hiển thị kết quả, các trường email và password **vẫn giữ nguyên** giá trị (không bị xoá/reload). |
| CC-08 | Auto-detect provider từ email domain | 1. Nhập lần lượt: `x@gmail.com`, `x@yandex.ru`, `x@outlook.com`, `x@yahoo.com`.<br>2. Bấm Verify cho từng email. | Provider hiển thị đúng: Gmail, Yandex, Outlook, Yahoo tương ứng. |

### 7.2. Bulk Check (CSV)

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CC-09 | Chuyển tab sang Bulk Check | 1. Bấm tab **Bulk Check (CSV)**. | Nội dung chuyển sang phần upload CSV, tab active có highlight. |
| CC-10 | Upload CSV hợp lệ | 1. Chuyển sang tab Bulk Check.<br>2. Bấm vùng upload, chọn file CSV (`email,password` mỗi dòng).<br>3. Quan sát CSV Preview. | Hiển thị tên file, kích thước, bảng preview 5 dòng đầu, mật khẩu hiện •••. |
| CC-11 | Drag & Drop CSV | 1. Kéo thả file CSV vào vùng upload. | Tương tự CC-10, file được nhận và hiển thị preview. |
| CC-12 | Check Bulk với CSV hợp lệ | 1. Upload CSV có 3+ email với mật khẩu.<br>2. Bấm **Check All Credentials**. | Bảng Results hiển thị từng email: Status (✓ Passed / ✗ Failed), Provider, Message. Stats badges hiện đúng số passed/failed/total. |
| CC-13 | CSV rỗng hoặc sai format | 1. Upload file CSV chỉ có 1 cột (thiếu password).<br>2. Bấm Check All. | API trả lỗi 400, toast hiển thị "No valid credentials found in CSV". |
| CC-14 | Upload file không phải CSV | 1. Kéo thả hoặc chọn file `.txt` / `.xlsx`.<br>2. Thao tác. | Hệ thống báo toast lỗi "Please select a CSV file". |
| CC-15 | Export kết quả CSV | 1. Sau khi có kết quả (từ Single hoặc Bulk).<br>2. Bấm **Export CSV**. | Trình duyệt tải file `credential_check_YYYY-MM-DD.csv` chứa cột: Email, Provider, Status, Message. |

### 7.3. UI & Navigation

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CC-16 | Link Check Credentials trên Dashboard | 1. Vào `index.html`.<br>2. Bấm nút **Check Credentials** (màu amber) trên navbar. | Chuyển hướng đến `check-credentials.html`. |
| CC-17 | Link Check Credentials trên Create Job | 1. Vào `create-job.html`.<br>2. Bấm nút **Check Credentials** trên navbar. | Chuyển hướng đến `check-credentials.html`. |
| CC-18 | Link Check Credentials trên Guide | 1. Vào `guide.html`.<br>2. Bấm nút **Check Credentials** trên navbar. | Chuyển hướng đến `check-credentials.html`. |
| CC-19 | Dark Mode hoạt động | 1. Trên trang Check Credentials, bấm nút toggle theme. | Giao diện chuyển Dark/Light mode, tất cả card, bảng, nút hiển thị đúng. |
| CC-20 | Responsive trên mobile | 1. Mở `check-credentials.html` trên điện thoại hoặc F12 giả lập mobile. | Layout co giãn đúng, các card xếp dọc, bảng có thanh cuộn ngang. |

---

## 8. Module Lệnh Imapsync (Imapsync Command)
**Mục tiêu:** Kiểm tra toàn bộ các tham số (flags) của lệnh `imapsync` được cấu hình trong `worker.py`, đảm bảo mỗi flag hoạt động đúng chức năng.

### 8.1. Tham số Kết nối Cơ bản (Connection Parameters)

| ID | Tên Test Case | Lệnh / Flag liên quan | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-01 | Kết nối đúng Host nguồn | `--host1`, `--port1` | 1. Tạo Job với `source_host=imap.gmail.com`, `source_port=993`.<br>2. Thêm mailbox và bắt đầu sync. | Log hiện "Connecting to imap.gmail.com", kết nối thành công. |
| IM-02 | Kết nối đúng Host đích | `--host2`, `--port2` | 1. Tạo Job với `target_host=imap.yandex.com`, `target_port=993`.<br>2. Thêm mailbox và bắt đầu sync. | Log hiện "Connecting to imap.yandex.com", kết nối thành công. |
| IM-03 | Kết nối sai Host nguồn | `--host1` | 1. Tạo Job với `source_host=invalid.server.xyz`.<br>2. Bắt đầu sync. | Log báo lỗi connection refused/timeout, mailbox status = `failed`. |
| IM-04 | Kết nối sai Port nguồn | `--port1` | 1. Tạo Job với `source_port=999` (sai port).<br>2. Bắt đầu sync. | Log báo lỗi connection, mailbox status = `failed`. |
| IM-05 | Xác thực User/Pass nguồn | `--user1`, `--passfile1` | 1. Tạo Job, thêm mailbox với `source_user` và `source_pass` hợp lệ.<br>2. Bắt đầu sync. | Log hiện "Authentication ok on host1", sync tiếp tục. |
| IM-06 | Xác thực User/Pass đích | `--user2`, `--passfile2` | 1. Tạo Job, thêm mailbox với `target_user` và `target_pass` hợp lệ.<br>2. Bắt đầu sync. | Log hiện "Authentication ok on host2", sync tiếp tục. |
| IM-07 | Sai mật khẩu nguồn | `--passfile1` | 1. Thêm mailbox với mật khẩu nguồn sai.<br>2. Bắt đầu sync. | Log báo "AUTHENTICATIONFAILED" hoặc tương đương, mailbox status = `failed`. |
| IM-08 | Sai mật khẩu đích | `--passfile2` | 1. Thêm mailbox với mật khẩu đích sai.<br>2. Bắt đầu sync. | Log báo lỗi xác thực đích, mailbox status = `failed`. |

### 8.2. Tham số Bảo mật (Security Flags)

| ID | Tên Test Case | Lệnh / Flag liên quan | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-09 | SSL/TLS nguồn | `--ssl1` | 1. Tạo Job với `source_security = "SSL/TLS"`.<br>2. Bắt đầu sync. | Lệnh imapsync chứa flag `--ssl1`, kết nối qua SSL port 993 thành công. |
| IM-10 | STARTTLS nguồn | `--tls1` | 1. Tạo Job với `source_security = "STARTTLS"`.<br>2. Bắt đầu sync. | Lệnh imapsync chứa flag `--tls1`, kết nối qua STARTTLS thành công. |
| IM-11 | SSL/TLS đích | `--ssl2` | 1. Tạo Job với `target_security = "SSL/TLS"`.<br>2. Bắt đầu sync. | Lệnh imapsync chứa flag `--ssl2`, kết nối đích qua SSL thành công. |
| IM-12 | STARTTLS đích | `--tls2` | 1. Tạo Job với `target_security = "STARTTLS"`.<br>2. Bắt đầu sync. | Lệnh imapsync chứa flag `--tls2`, kết nối đích qua STARTTLS thành công. |
| IM-13 | Không chọn bảo mật | (không có flag) | 1. Tạo Job với `source_security` và `target_security` khác SSL/TLS và STARTTLS.<br>2. Xem lệnh. | Lệnh imapsync KHÔNG chứa `--ssl1/2` hay `--tls1/2`. |

### 8.3. Tham số Khả năng Chịu lỗi (Resilience Flags)

| ID | Tên Test Case | Lệnh / Flag liên quan | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-14 | Giới hạn lỗi tối đa | `--errorsmax 2000` | 1. Sync mailbox có nhiều email lỗi (corrupted).<br>2. Quan sát log. | Imapsync tiếp tục chạy dù có nhiều lỗi, chỉ dừng khi vượt 2000 lỗi. |
| IM-15 | Tự động kết nối lại nguồn | `--reconnectretry1 10` | 1. Mô phỏng mất kết nối nguồn giữa chừng.<br>2. Quan sát log. | Log hiện thông báo reconnect, imapsync thử kết nối lại tối đa 10 lần. |
| IM-16 | Tự động kết nối lại đích | `--reconnectretry2 10` | 1. Mô phỏng mất kết nối đích giữa chừng.<br>2. Quan sát log. | Log hiện thông báo reconnect đích, thử kết nối lại tối đa 10 lần. |
| IM-17 | Timeout nguồn mở rộng | `--timeout1 180` | 1. Sync với server phản hồi chậm.<br>2. Quan sát. | Imapsync đợi tối đa 180 giây trước khi timeout cho host1. |
| IM-18 | Timeout đích mở rộng | `--timeout2 180` | 1. Sync với server đích phản hồi chậm.<br>2. Quan sát. | Imapsync đợi tối đa 180 giây trước khi timeout cho host2. |

### 8.4. Tham số Hiệu suất (Performance Flags)

| ID | Tên Test Case | Lệnh / Flag liên quan | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-19 | Chia nhỏ batch nguồn | `--split1 50` | 1. Sync folder có >100 email.<br>2. Quan sát log. | Imapsync xử lý theo batch 50 message, log hiện rõ từng batch. |
| IM-20 | Chia nhỏ batch đích | `--split2 50` | 1. Sync folder có >100 email.<br>2. Quan sát log. | Imapsync ghi từng batch 50 message vào đích. |
| IM-21 | Bỏ qua tính kích thước folder | `--nofoldersizes` | 1. Bắt đầu sync.<br>2. Quan sát log. | Log KHÔNG hiện bước "Stripping folder sizes", tiết kiệm thời gian. |
| IM-22 | Fast I/O nguồn | `--fastio1` | 1. Sync mailbox lớn.<br>2. Quan sát hiệu suất. | Sử dụng fast I/O cho host1, tốc độ đọc nhanh hơn. |
| IM-23 | Fast I/O đích | `--fastio2` | 1. Sync mailbox lớn.<br>2. Quan sát hiệu suất. | Sử dụng fast I/O cho host2, tốc độ ghi nhanh hơn. |
| IM-24 | Bỏ qua trùng lặp chéo | `--skipcrossduplicates` | 1. Sync mailbox có email trùng lặp giữa các folder.<br>2. Quan sát log. | Email trùng lặp chỉ được copy 1 lần, log hiện "skipcrossduplicates". |
| IM-25 | Sử dụng Message-Id header | `--useheader Message-Id` | 1. Sync folder lớn có nhiều email.<br>2. Quan sát log. | Imapsync sử dụng Message-Id để nhận diện email, parse nhanh hơn. |
| IM-26 | Tự động ánh xạ folder | `--automap` | 1. Sync giữa 2 provider khác nhau (Gmail → Yandex).<br>2. Quan sát log. | Log hiện mapping tự động (VD: "[Gmail]/Sent Mail" → "Sent"), thư mục được ánh xạ chính xác. |

### 8.5. Tham số Tuỳ chọn Tính năng (Feature Option Flags)

| ID | Tên Test Case | Lệnh / Flag liên quan | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-27 | Đồng bộ ngày nội bộ | `--syncinternaldates` | 1. Tạo Job với `options.sync_internal_dates = true`.<br>2. Sync mailbox.<br>3. Kiểm tra ngày email ở đích. | Email ở đích giữ nguyên ngày gốc (internal date), không phải ngày sync. |
| IM-28 | Bỏ qua thùng rác | `--exclude Trash/Bin/Deleted Items` | 1. Tạo Job với `options.skip_trash = true`.<br>2. Sync mailbox có folder Trash.<br>3. Kiểm tra đích. | Folder Trash, Bin, Deleted Items KHÔNG được sync sang đích. |
| IM-29 | Chạy thử (Dry Run) | `--dry` | 1. Tạo Job với `options.dry_run = true`.<br>2. Bắt đầu sync.<br>3. Kiểm tra đích. | Imapsync chạy mô phỏng, log hiện "[dry run]", KHÔNG có email nào thực sự được copy. |
| IM-30 | Không bật tùy chọn nào | (không có flag tùy chọn) | 1. Tạo Job với `options = {}`.<br>2. Kiểm tra lệnh. | Lệnh KHÔNG chứa `--syncinternaldates`, `--exclude`, `--dry`. |

### 8.6. Xử lý Exit Code & Trạng thái (Exit Codes)

| ID | Tên Test Case | Exit Code | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-31 | Sync thành công hoàn toàn | `exit 0` | 1. Sync mailbox hợp lệ.<br>2. Đợi hoàn tất. | Mailbox status = `success`, progress = 100%, message = "Sync Completed Successfully". |
| IM-32 | Bị dừng bởi user (SIGTERM) | `exit -15` | 1. Sync mailbox.<br>2. Bấm Stop giữa chừng. | Mailbox status = `failed`, message = "Stopped by user". |
| IM-33 | Bị kill (SIGKILL) | `exit -9` | 1. Kill process bằng hệ thống. | Mailbox status = `failed`, message = "Stopped by user". |
| IM-34 | Partial sync - ERR_APPEND | `exit 114` | 1. Sync mailbox có email không thể append.<br>2. Đợi kết thúc. | Mailbox status = `warning`, progress = 100%, message chứa "ERR_APPEND", job.completed +1. |
| IM-35 | Partial sync - ERR_FETCH | `exit 115` | 1. Sync mailbox có email không thể fetch.<br>2. Đợi kết thúc. | Mailbox status = `warning`, message chứa "ERR_FETCH". |
| IM-36 | Partial sync - ERR_OVER_QUOTA | `exit 111` | 1. Sync khi đích hết dung lượng. | Mailbox status = `warning`, message chứa "ERR_OVER_QUOTA". |
| IM-37 | Exit code không xác định | `exit code khác` | 1. Sync gặp lỗi không mong đợi (VD: exit 1). | Mailbox status = `failed`, message = "Exited with code X. Check logs." |
| IM-38 | Exception trong worker | `Exception` | 1. Gây lỗi runtime trong worker (ví dụ: DB disconnect).<br>2. Quan sát. | Mailbox status = `failed`, message chứa nội dung exception, log ghi "CRITICAL ERROR". |

### 8.7. Theo dõi Log & Tiến độ (Log Parsing)

| ID | Tên Test Case | Pattern Parse | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|---|
| IM-39 | Parse Folder progress | `Folder X/Y` | 1. Sync mailbox có nhiều folder.<br>2. Quan sát DB. | `mailbox.progress` cập nhật đúng %, message hiện "Syncing folder X/Y". |
| IM-40 | Parse Message progress | `msg INBOX/N` | 1. Sync folder có nhiều email.<br>2. Quan sát DB. | `mailbox.progress` tính đúng dựa trên folder + message, message hiện "Folder X/Y: msg M/N". |
| IM-41 | Parse Data Transferred | `Total bytes transferred` | 1. Hoàn tất sync.<br>2. Kiểm tra DB. | `mailbox.data_transferred` lưu đúng số bytes, `job.data_transferred` cộng dồn đúng. |
| IM-42 | Cập nhật message trạng thái | `Connecting to, Authentication...` | 1. Bắt đầu sync.<br>2. Quan sát DB nhanh. | `mailbox.message` cập nhật theo các dòng trạng thái quan trọng (Connecting, Calculating...). |
| IM-43 | Pulse DB mỗi 10 giây | DB commit | 1. Sync folder lớn, lâu.<br>2. Quan sát timestamp DB. | DB được commit ít nhất mỗi 10 giây dù không có progress mới. |
| IM-44 | Bảo mật mật khẩu temp file | `tempfile`, `os.unlink` | 1. Sync mailbox.<br>2. Sau khi sync xong, kiểm tra thư mục temp. | File tạm chứa mật khẩu (`passfile1`, `passfile2`) bị xóa sau khi sync hoàn tất. |

## 9. Module Kiểm tra Mật khẩu - Backend & API (Check Credentials Backend)
**Mục tiêu:** Kiểm tra chi tiết logic backend của tính năng kiểm tra mật khẩu ứng dụng, bao gồm hàm Python, API endpoints.

### 9.1. Hàm `detect_provider()` — Tự động nhận diện Provider

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CB-01 | Detect Gmail | Gọi `detect_provider("user@gmail.com")`. | Trả về `{"host": "imap.gmail.com", "port": 993, "name": "Gmail"}`. |
| CB-02 | Detect Googlemail | Gọi `detect_provider("user@googlemail.com")`. | Trả về `{"host": "imap.gmail.com", "port": 993, "name": "Gmail"}`. |
| CB-03 | Detect Yandex (.com) | Gọi `detect_provider("user@yandex.com")`. | Trả về `{"host": "imap.yandex.com", "port": 993, "name": "Yandex"}`. |
| CB-04 | Detect Yandex (.ru) | Gọi `detect_provider("user@yandex.ru")`. | Trả về host/name Yandex. |
| CB-05 | Detect Ya.ru | Gọi `detect_provider("user@ya.ru")`. | Trả về host/name Yandex. |
| CB-06 | Detect Outlook | Gọi `detect_provider("user@outlook.com")`. | Trả về `{"host": "outlook.office365.com", "name": "Outlook"}`. |
| CB-07 | Detect Hotmail | Gọi `detect_provider("user@hotmail.com")`. | Trả về host/name Outlook. |
| CB-08 | Detect Live | Gọi `detect_provider("user@live.com")`. | Trả về host/name Outlook. |
| CB-09 | Detect Yahoo | Gọi `detect_provider("user@yahoo.com")`. | Trả về `{"host": "imap.mail.yahoo.com", "name": "Yahoo"}`. |
| CB-10 | Detect Yahoo Japan | Gọi `detect_provider("user@yahoo.co.jp")`. | Trả về `{"host": "imap.mail.yahoo.co.jp", "name": "Yahoo Japan"}`. |
| CB-11 | Detect Zoho | Gọi `detect_provider("user@zoho.com")`. | Trả về `{"host": "imap.zoho.com", "name": "Zoho"}`. |
| CB-12 | Detect iCloud | Gọi `detect_provider("user@icloud.com")`. | Trả về `{"host": "imap.mail.me.com", "name": "iCloud"}`. |
| CB-13 | Detect me.com | Gọi `detect_provider("user@me.com")`. | Trả về host/name iCloud. |
| CB-14 | Detect AOL | Gọi `detect_provider("user@aol.com")`. | Trả về `{"host": "imap.aol.com", "name": "AOL"}`. |
| CB-15 | Detect Mail.ru | Gọi `detect_provider("user@mail.ru")`. | Trả về `{"host": "imap.mail.ru", "name": "Mail.ru"}`. |
| CB-16 | Domain không hỗ trợ | Gọi `detect_provider("user@custom.vn")`. | Trả về `None`. |
| CB-17 | Email không có @ | Gọi `detect_provider("invalid-email")`. | Trả về `None` (domain rỗng). |
| CB-18 | Email có khoảng trắng | Gọi `detect_provider("  user@gmail.com  ")`. | Trả về kết quả Gmail (tự strip). |
| CB-19 | Email viết hoa | Gọi `detect_provider("User@GMAIL.COM")`. | Trả về Gmail (tự lower). |

### 9.2. Hàm `check_imap_login()` — Kiểm tra đăng nhập IMAP

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CB-20 | Login thành công (auto-detect) | Gọi `check_imap_login("user@gmail.com", "correct_app_pass")` không truyền host. | `status="success"`, `message` chứa "imap.gmail.com", `provider="Gmail"`. |
| CB-21 | Login thất bại (sai pass) | Gọi `check_imap_login("user@gmail.com", "wrong_pass")`. | `status="failed"`, message chứa "Authentication failed". |
| CB-22 | Login với custom host | Gọi `check_imap_login("user@custom.vn", "pass", host="mail.custom.vn", port=993)`. | Sử dụng host custom, `provider` hiện "mail.custom.vn". |
| CB-23 | Domain không hỗ trợ, không có host | Gọi `check_imap_login("user@unknown.xyz", "pass")` không truyền host. | `status="failed"`, message = "Cannot detect IMAP server for domain.", provider = "Unknown". |
| CB-24 | Connection timeout | Gọi với host không phản hồi (ví dụ: IP private). | `status="failed"`, message chứa "Connection timed out". |
| CB-25 | DNS / Network error | Gọi với host không tồn tại. | `status="failed"`, message chứa "Cannot connect to". |
| CB-26 | IMAP server alert | Gọi với tài khoản bị khóa hoặc cần xác thực bổ sung. | `status="failed"`, message chứa "Server alert:". |
| CB-27 | Email/pass có khoảng trắng | Gọi với email và password có khoảng trắng đầu/cuối. | Tự động strip, kết quả chính xác. |

### 9.3. Hàm `check_bulk()` — Kiểm tra hàng loạt

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CB-28 | Bulk check nhiều email | Gọi `check_bulk([{email1,pass1}, {email2,pass2}, {email3,pass3}])`. | Trả về list 3 kết quả, mỗi kết quả có status/message/provider. |
| CB-29 | Bulk giữ đúng thứ tự | Gọi bulk check với 5 email, provider khác nhau. | Kết quả trả về đúng thứ tự gốc (sort by email_order). |
| CB-30 | Bulk xử lý song song | Gọi bulk check với `max_concurrent=3` cho 6 email. | Tối đa 3 request đồng thời, kết quả đủ 6. |
| CB-31 | Bulk xử lý exception | Gọi bulk check với 1 email gây exception trong thread. | Email lỗi trả `status="failed"`, message chứa "Check error:", các email khác vẫn trả kết quả. |
| CB-32 | Bulk với custom host | Gọi `check_bulk(creds, host="mail.custom.vn", port=993)`. | Tất cả email đều check qua host custom thay vì auto-detect. |

### 9.4. API Endpoints — `/api/check-credentials`

| ID | Tên Test Case | Các bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| CB-33 | POST single check hợp lệ | `POST /api/check-credentials` với body `{"email":"x@gmail.com","password":"pass"}`. | HTTP 200, JSON chứa `email, status, message, provider`. |
| CB-34 | POST single check với host tùy chỉnh | `POST /api/check-credentials` với `{"email":"x@custom.vn","password":"pass","host":"mail.vn","port":993}`. | HTTP 200, sử dụng host/port từ body. |
| CB-35 | POST single check thiếu email | `POST /api/check-credentials` với body thiếu `email`. | HTTP 422 Validation Error. |
| CB-36 | POST single check thiếu password | `POST /api/check-credentials` với body thiếu `password`. | HTTP 422 Validation Error. |
| CB-37 | POST bulk check CSV hợp lệ | `POST /api/check-credentials/bulk` upload file CSV `email,password`.<br> | HTTP 200, JSON chứa `results`, `total`, `success_count`, `failed_count`. |
| CB-38 | POST bulk check CSV rỗng | Upload CSV không có dòng hợp lệ. | HTTP 400 "No valid credentials found in CSV". |
| CB-39 | POST bulk check CSV 1 cột | Upload CSV chỉ có cột email, thiếu password. | HTTP 400 "No valid credentials found in CSV". |
| CB-40 | POST bulk check với query host | `POST /api/check-credentials/bulk?host=mail.vn&port=993`. | HTTP 200, tất cả email check qua host từ query param. |
| CB-41 | GET danh sách providers | `GET /api/providers`. | HTTP 200, JSON array chứa các provider (Gmail, Yandex, Outlook...) với domains tương ứng. |
| CB-42 | GET providers không trùng lặp | `GET /api/providers`. | Mỗi provider name xuất hiện 1 lần dù có nhiều domains (gmail.com, googlemail.com → 1 Gmail). |
| RL-01 | Rate Limit Exceeded | Thực hiện 11 requests liên tiếp tới `/api/check-credentials`. | Request thứ 11 trả về HTTP 429 "Rate limit exceeded". |

---

> _**Lưu ý:** Các test case trên là kịch bản kiểm thử Black-box, tập trung vào kết quả phản hồi của API và UI. Nếu cần thiết lập Autotest, có thể ứng dụng Pytest cho Backend API và Playwright/Cypress cho các kịch bản UI. Các Module 8 & 9 bổ sung thêm kiểm thử White-box cho logic nội bộ của hàm và lệnh imapsync._

