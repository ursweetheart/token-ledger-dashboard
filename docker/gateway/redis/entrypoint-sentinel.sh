#!/bin/sh
# Sinh file cau hinh Sentinel tren VOLUME roi giao lai cho redis-sentinel.
#
# Cung ly do voi docker/gateway/redis/entrypoint.sh:
#   - Sentinel TU VIET LAI file cau hinh cua no moi lan trang thai doi (master
#     moi, cac sentinel khac phat hien duoc...). File `:ro` thi Sentinel bao loi
#     va dung han.
#   - Mat khau khong duoc nam trong repo, ma Sentinel cung khong noi suy bien
#     moi truong trong file cau hinh.
#
# CHI SINH MOT LAN. File da co thi giu nguyen: tu luc do no mang trang thai do
# chinh Sentinel viet, khong con la ban sao cua template.
set -eu

MAU="${SENTINEL_CONF_TEMPLATE:?SENTINEL_CONF_TEMPLATE chua duoc dat}"
DICH="${SENTINEL_CONF_PATH:-/data/sentinel.conf}"

if [ -z "${REDIS_PASSWORD:-}" ]; then
  echo "STOP: REDIS_PASSWORD trong. Sentinel khong giam sat noi mot Redis co" >&2
  echo "      requirepass, va no se hong IM LANG chu khong bao loi." >&2
  exit 1
fi

if [ -f "$DICH" ]; then
  echo "[sentinel-entrypoint] $DICH da co, giu nguyen (mang trang thai Sentinel viet)."
else
  echo "[sentinel-entrypoint] sinh $DICH tu $MAU"
  sed "s|__REDIS_PASSWORD__|${REDIS_PASSWORD}|g" "$MAU" > "$DICH"
  chmod 600 "$DICH"
fi

exec redis-sentinel "$DICH" "$@"
