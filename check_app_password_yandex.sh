#!/bin/bash
# Usage: check_app_password.sh user.csv

file=$1

while IFS=',' read -r Username Password; do
  # Xóa ký tự carriage return nếu có trong các trường
  Username=$(echo "$Username" | tr -d '\r')
  Password=$(echo "$Password" | tr -d '\r')

  # Thực hiện kiểm tra bằng curl với Username và Password
  response=$(curl -u "${Username}:${Password}" --silent "https://mail.google.com/mail/feed/atom" --output /dev/null --write-out "%{http_code}")

  # In kết quả ra màn hình
  echo "Email: $Username - HTTP Status Code: $response"
done < "$file"
[root@imap script_rsync_email]# cat check_app_password_yandex.sh
#!/bin/bash
# Usage: check_yandex_app_password.sh user.csv

file=$1

while IFS=',' read -r Username Password; do
  Username=$(echo "$Username" | tr -d '\r')
  Password=$(echo "$Password" | tr -d '\r')

  result=$(curl --url "imaps://imap.yandex.com" \
                --user "${Username}:${Password}" \
                --silent 2>&1)

  if echo "$result" | grep -qi "OK"; then
      echo "Email: $Username - SUCCESS"
  else
      echo "Email: $Username - FAILED"
  fi

done < "$file"