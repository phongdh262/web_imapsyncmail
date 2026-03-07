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

---

> _**Lưu ý:** Các test case trên là kịch bản kiểm thử Black-box, tập trung vào kết quả phản hồi của API và UI. Nếu cần thiết lập Autotest, có thể ứng dụng Pytest cho Backend API và Playwright/Cypress cho các kịch bản UI._
