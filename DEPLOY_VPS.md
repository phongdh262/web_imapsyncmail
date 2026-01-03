# Hướng dẫn Deploy lên VPS với Docker Compose

Tài liệu này hướng dẫn cách deploy ứng dụng web_imapsyncmail lên VPS Linux.
Thư mục cài đặt: `/opt/apps/imapsyncmail`
Cấu hình: **Kết nối Global MariaDB** + **Nginx Proxy Manager**.

## Yêu cầu

Trên VPS cần cài đặt sẵn:
1. **Docker** & **Docker Compose**.
2. **Nginx Proxy Manager** (đã chạy và nên cùng network `web_network` hoặc có thể kết nối tới nó).

## Các bước thực hiện

### 1. Upload code lên VPS

Chạy lệnh scp từ máy cá nhân của bạn để upload code:

```bash
# Upload từ máy cá nhân lên thư mục /opt/apps/imapsyncmail trên VPS
scp -r /Users/phongdinh/Desktop/Phong-DH/Website/web_imapsyncmail root@<IP_VPS>:/opt/apps/imapsyncmail
```

### 2. Tạo Database

Chạy lệnh sau trên VPS để tạo database `imapsync_db` (nếu chưa có):

```bash
docker exec -it global-mariadb mariadb -uroot -p+_4nw=c7vAHh^gDjf5x? -e "CREATE DATABASE IF NOT EXISTS imapsync_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. Chạy ứng dụng

Kết nối SSH và đi tới thư mục code:

```bash
ssh root@<IP_VPS>
cd /opt/apps/imapsyncmail
```

Chạy lệnh để khởi động:

```bash
docker-compose up -d --build
```

### 4. Cấu hình Nginx Proxy Manager

Truy cập vào trang quản trị Nginx Proxy Manager của bạn và tạo 1 Proxy Host mới:

- **Domain Names**: Tên miền của bạn (ví dụ: `mailsync.yourdomain.com`).
- **Scheme**: `http`
- **Forward Hostname / IP**: `imapsync_app` 
    - *Lưu ý*: Container ứng dụng đã được cấu hình để join vào network `web_network`. Hãy đảm bảo Nginx Proxy Manager cũng đang ở trong network này. Nếu dùng hostname `imapsync_app` không được, hãy thử dùng IP của container (lấy bằng lệnh `docker inspect`).
- **Forward Port**: `8000`
- **Block Common Exploits**: Bật.
- **Websockets Support**: Bật.

### 5. Kiểm tra Logs (Nếu cần)

```bash
cd /opt/apps/imapsyncmail
docker-compose logs -f app
```
