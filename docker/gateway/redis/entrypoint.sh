#!/bin/sh
# Sinh file cau hinh Redis tren VOLUME roi giao lai cho redis-server.
#
# VI SAO PHAI VONG QUA MOT BUOC SINH FILE
# ---------------------------------------
# Hai rang buoc keo ve hai huong nguoc nhau:
#
#   1. File cau hinh phai GHI DUOC va BEN. Sentinel doi vai bang cach bao Redis
#      chay CONFIG REWRITE; khong co file ghi duoc thi ket qua thang cap bi xoa
#      o lan restart ke tiep. (Da do 07/09/2026 -- xem redis.conf.template.)
#
#   2. Mat khau KHONG duoc nam trong repo. Ma Redis KHONG noi suy bien moi
#      truong trong file cau hinh: viet `requirepass ${REDIS_PASSWORD}` thi mat
#      khau tro thanh dung chuoi do. Va khi CONFIG REWRITE chay, Redis GHI mat
#      khau that vao file -- neu file nam trong repo thi bi mat roi vao git.
#
# Loi giai: repo giu BAN MAU khong co bi mat; file that duoc sinh ra mot lan
# tren volume `/data`, noi da co san de luu appendonly.
#
# CHI SINH MOT LAN. Neu /data/redis.conf da ton tai thi giu nguyen -- vi tu luc
# do tro di no khong con la ban sao cua template nua, no la TRANG THAI do
# Sentinel viet vao. Ghi de moi lan khoi dong la tai lap dung cai loi ma ca
# change nay sinh ra de sua.
set -eu

MAU="${REDIS_CONF_TEMPLATE:?REDIS_CONF_TEMPLATE chua duoc dat}"
DICH="${REDIS_CONF_PATH:-/data/redis.conf}"

if [ -z "${REDIS_PASSWORD:-}" ]; then
  echo "STOP: REDIS_PASSWORD trong. Che do hong phai la 'khong chay', khong bao"
  echo "      gio la 'chay ma khong co mat khau'." >&2
  exit 1
fi

if [ -f "$DICH" ]; then
  echo "[redis-entrypoint] $DICH da co, giu nguyen (co the mang trang thai Sentinel viet)."
else
  echo "[redis-entrypoint] sinh $DICH tu $MAU"
  # Dung `sed` chu khong `envsubst`: anh alpine cua Redis khong co envsubst, va
  # them mot goi chi de thay mot chuoi la khong dang.
  sed "s|__REDIS_PASSWORD__|${REDIS_PASSWORD}|g" "$MAU" > "$DICH"
  chmod 600 "$DICH"
fi

exec redis-server "$DICH" "$@"
