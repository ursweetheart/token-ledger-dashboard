# TLS cho gateway-lb

Thu muc nay chua `apigateway.crt` (fullchain: leaf + intermediate + root) va
`apigateway.key`. KHONG len git (xem `.gitignore`) -- ca hai file deu la du
lieu bi mat/nhay cam thuc su, khac voi ban tu ky truoc do.

## Nguon goc cert hien tai

Wildcard `*.rangdong.com.vn`, cap boi Sectigo (chain: `Sectigo Public Server
Authentication CA DV R36` -> `Sectigo Public Server Authentication Root R46`
-> `USERTrust RSA Certification Authority`). Nhan tu file zip nguoi van hanh
cung cap ngay 18/09/2026:

- `STAR.rangdong.com.vn_cert (1).zip` chua `STAR.rangdong.com.vn.crt` (leaf) va
  `STAR.rangdong.com.vn.ca-bundle` (chain). File `.p7b` di kem khong dung cho
  nginx, chi de tham khao/nhap vao IIS neu can.
- `STAR.rangdong.com.vn_key (1).zip` chua private key dang PEM
  (`-----BEGIN PRIVATE KEY-----`), khong khoa passphrase.

`apigateway.crt` = noi dung `STAR.rangdong.com.vn.crt` roi den
`STAR.rangdong.com.vn.ca-bundle`, GIU DUNG THU TU (leaf truoc, chain sau) va
PHAI co dong trong giua hai phan -- file `.crt` goc thieu newline cuoi, ghep
truc tiep se dinh lien `END CERTIFICATE` va `BEGIN CERTIFICATE` thanh mot dong,
lam nginx tu choi khoi dong. Da xac minh: khop giua cert/key (modulus giong
nhau), chain verify OK (`openssl verify -untrusted ca-bundle crt`), va nginx
thuc su serve dung chuoi nay (`openssl s_client` + `curl` khong can `-k`).

**Het han: 27/11/2026.** Phai gia han truoc moc nay, neu khong Gateway se roi
ve canh bao "khong tin cay" hoac tu choi ket noi TLS hoan toan.

## Gia han / thay cert moi

1. Xin cert wildcard moi cho `*.rangdong.com.vn` (hoac it nhat
   `apigateway.rangdong.com.vn`) tu nha cung cap hien tai.
2. Ghi de `apigateway.crt` bang leaf + chain moi (dung thu tu, co dong trong
   giua cac block PEM) va `apigateway.key` bang key moi tuong ung.
3. Kiem tra khop truoc khi ap dung:

   ```bash
   openssl x509 -in apigateway.crt -noout -pubkey | openssl md5
   openssl pkey -in apigateway.key -pubout | openssl md5
   # Hai gia tri PHAI giong nhau
   ```

4. Ap dung:

   ```powershell
   docker compose --profile gateway up -d --no-deps --force-recreate --wait --wait-timeout 60 gateway-lb
   docker compose --profile gateway exec -T gateway-lb nginx -t
   ```

## Ha bac: quay lai cert tu ky (chi khi khong con cert that dung duoc)

```bash
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout apigateway.key -out apigateway.crt -days 397 \
  -subj "/CN=apigateway.rangdong.com.vn" \
  -addext "subjectAltName=DNS:apigateway.rangdong.com.vn,DNS:localhost,IP:127.0.0.1"
```

Client/trinh duyet se canh bao "khong tin cay" cho toi khi co cert CA that.
