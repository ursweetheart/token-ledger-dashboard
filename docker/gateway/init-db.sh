#!/bin/sh
# Tao role + database RIENG cho Gateway tren chinh may PostgreSQL cua du an.
#
# Vi sao khong dung thang database so: phep kiem nghiem thu (change
# measure-what-the-gateway-records, task 7.4) doi database so phai co DUNG 0 bang
# ten LiteLLM_*. Cung mot may chu, khac database -- ke hoach GD2 dong 6 van thoa
# ("dung db hien tai"), ma ranh gioi van do duoc bang mot cau SELECT.
#
# Chay lai duoc nhieu lan: da co thi bo qua, khong bao gio DROP thu gi.
set -eu

: "${PGHOST:?thieu PGHOST}"
: "${ADMIN_DB:?thieu ADMIN_DB}"
: "${ADMIN_USER:?thieu ADMIN_USER}"
: "${ADMIN_PASSWORD:?thieu ADMIN_PASSWORD}"
: "${GW_DB:?thieu GW_DB}"
: "${GW_USER:?thieu GW_USER}"
: "${GW_PASSWORD:?thieu GW_PASSWORD}"

# Moi gia tri di vao SQL deu qua bien cua psql: `:'x'` la chuoi da trich dan,
# `:"x"` la dinh danh da trich dan -- chinh psql lo viec trich dan, khong phai ta.
# Noi chuoi bang tay thi mot dau nhay don trong mat khau (hoan toan hop le trong
# .env) se lam vo cau lenh hoac tiem SQL duoi quyen admin cua so.
#
# SQL di qua STDIN chu khong qua `-c`: da do 27/08/2026, psql KHONG noi suy bien
# khi dung `-c`, no gui thang chuoi sang may chu va bao
#     ERROR: syntax error at or near ":"
# Doc tu stdin thi psql xu ly nhu mot tep script va bien duoc noi suy.
admin() {
  PGPASSWORD="$ADMIN_PASSWORD" psql -h "$PGHOST" -U "$ADMIN_USER" -d "$ADMIN_DB" \
    -v ON_ERROR_STOP=1 \
    -v gw_user="$GW_USER" -v gw_pass="$GW_PASSWORD" -v gw_db="$GW_DB" "$@"
}
admin_val() { printf '%s\n' "$1" | admin -tAq; }   # cau hoi, tra ve mot gia tri
admin_run() { printf '%s\n' "$1" | admin -q; }     # cau lenh, khong can ket qua

echo "step 1/3: role $GW_USER"
if [ "$(admin_val "SELECT 1 FROM pg_roles WHERE rolname = :'gw_user';")" = "1" ]; then
  echo "   already exists, left alone (the password is NOT re-synced -- see step 3)"
else
  admin_run "CREATE ROLE :\"gw_user\" LOGIN PASSWORD :'gw_pass';"
  echo "   created"
fi

echo "step 2/3: database $GW_DB"
if [ "$(admin_val "SELECT 1 FROM pg_database WHERE datname = :'gw_db';")" = "1" ]; then
  echo "   already exists, left alone"
else
  admin_run "CREATE DATABASE :\"gw_db\" OWNER :\"gw_user\";"
  echo "   created, owned by $GW_USER"
fi

# --- 3/3 -------------------------------------------------------------------
# DO ranh gioi, khong TIN vao ranh gioi. Role cua Gateway KHONG duoc doc duoc
# bang nao cua database so. Mac dinh PostgreSQL da nhu vay (PUBLIC khong duoc
# cap quyen tren bang), nhung "mac dinh" la mot gia dinh -- day la phep do.
#
# DO TAT CA database so, khong doan mot cai. Hom nay ton tai ca `token_ledger`
# lan `token_ledger_v2`, va `db/connect.py` mac dinh tro vao cai THU HAI trong
# khi docker-compose.yml mac dinh tao cai THU NHAT. Do dung mot cai la co the
# dang do cai khong ai dung toi.
echo "step 3/3: probing the boundary - can $GW_USER read the ledger database?"

LEDGER_DBS=$(admin_val "SELECT datname FROM pg_database WHERE datname ~ '^token_ledger' ORDER BY datname;")
if [ -z "$LEDGER_DBS" ]; then
  echo "   STOP: found no ledger database matching '^token_ledger'." >&2
  echo "   The boundary probe would be meaningless. Stopping." >&2
  exit 1
fi

for db in $LEDGER_DBS; do
  # Bang moi phai TON TAI thi phep do moi co nghia. psql tra ma thoat 1 cho CA
  #     permission denied for table X       <- dieu ta muon thay
  #     relation "X" does not exist         <- phep do rong tuech
  # Chi nhin ma thoat thi doi ten bang la phep do im lang thanh "dat" ma khong
  # kiem gi ca. Da do 27/08/2026: ca hai deu rc=1.
  probe_table=$(PGPASSWORD="$ADMIN_PASSWORD" psql -h "$PGHOST" -U "$ADMIN_USER" -d "$db" \
    -v ON_ERROR_STOP=1 -tAc \
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename LIMIT 1")

  if [ -z "$probe_table" ]; then
    echo "   $db: no tables yet -- nothing to read, skipped"
    continue
  fi

  # Schema public o day da bi thu hoi HET quyen khoi PUBLIC, ke ca USAGE (chat
  # hon mac dinh PG15, chi con REVOKE CREATE). Khong co USAGE thi $GW_USER
  # khong PHAN GIAI duoc ten bang, va loi tra ve la "relation khong ton tai"
  # -- giong het trieu chung "bang doi ten", nen phep do o duoi khong ket luan
  # duoc gi. Cap USAGE (KHONG cap SELECT) de loi tra ve dung nghia: "permission
  # denied" that vi thieu quyen doc, khong phai vi khong thay ten bang.
  printf '%s\n' 'GRANT USAGE ON SCHEMA public TO :"gw_user";' | \
    PGPASSWORD="$ADMIN_PASSWORD" psql -h "$PGHOST" -U "$ADMIN_USER" -d "$db" \
      -v ON_ERROR_STOP=1 -v gw_user="$GW_USER" -q

  probe_out=$(PGPASSWORD="$GW_PASSWORD" psql -h "$PGHOST" -U "$GW_USER" -d "$db" \
    -tAc "SELECT count(*) FROM \"$probe_table\"" 2>&1) && probe_rc=0 || probe_rc=$?
  probe_msg=$(echo "$probe_out" | tr -d '\r' | head -1)

  if [ "$probe_rc" -eq 0 ]; then
    echo "   FAIL: $GW_USER could read $probe_msg rows from $db.$probe_table." >&2
    echo "   The gateway role has rights on the real ledger. Stopping." >&2
    exit 1
  fi

  # CHI thieu quyen moi chung minh duoc ranh gioi con nguyen.
  #
  # 'authentication failed' va 'no pg_hba.conf entry' KHONG duoc tinh la dat:
  # chung nghia la psql chua he cham toi mot cai bang nao, nen khong chung minh
  # duoc gi ve quyen -- dung loai im lang ma buoc kiem bang o tren sinh ra de
  # chan. Chung con che mot loi that: role da ton tai tu lan chay truoc voi mat
  # khau KHAC, buoc 1 bo qua khong dong bo lai, roi LiteLLM khoi dong voi
  # DATABASE_URL sai mat khau va chet o luc chay migration.
  case "$probe_out" in
    *"permission denied"*|*"must be owner"*)
      echo "   $db.$probe_table: pass -- $probe_msg" ;;
    *"authentication failed"*|*"no pg_hba.conf entry"*)
      echo "   STOP: $GW_USER cannot log in to $db." >&2
      echo "   $probe_msg" >&2
      echo "   The probe never touched a table, so it concludes nothing about rights." >&2
      echo "   Usually the role already exists with a password other than the current GATEWAY_PGPASSWORD." >&2
      exit 1 ;;
    *)
      echo "   STOP: refused, but NOT for lack of rights." >&2
      echo "   $probe_msg" >&2
      echo "   The probe concludes nothing -- it must not be treated as a pass." >&2
      exit 1 ;;
  esac
done

echo
echo "the gateway will connect to: postgresql://$GW_USER@$PGHOST:5432/$GW_DB"
