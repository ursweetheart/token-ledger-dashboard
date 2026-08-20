"""Do ty le tien SUY RA tren toan bo du lieu dashboard dang hien."""
import sys, json, urllib.request, collections
sys.stdout.reconfigure(encoding="utf-8")

B = "http://127.0.0.1:8000"
get = lambda p: json.load(urllib.request.urlopen(B + p))
cat = get("/api/catalog")
pr = {m["name"]: m for m in cat["models"]}
h = get("/api/health")
lo, hi = h["ranges"]["usage"]["from"], h["ranges"]["usage"]["to"]
rows = get("/api/usage?start=%s&end=%s" % (lo, hi))["rows"]


def uoc(r):
    p = pr.get(r["model"])
    if not p or p["price_input"] is None:
        return None
    return ((r["input_tokens"] or 0) / 1e6 * p["price_input"]
            + (r["output_tokens"] or 0) / 1e6 * (p["price_output"] or 0)
            + (r["cached_tokens"] or 0) / 1e6 * (p["price_cached"] or 0))


hd = est = 0.0
n_hd = n_est = n_khong = 0
theo_ngay = collections.defaultdict(lambda: [0.0, 0.0])
theo_agent = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows:
    if r["cost_usd"] is not None:
        hd += r["cost_usd"]
        n_hd += 1
        theo_ngay[r["day"]][0] += r["cost_usd"]
        theo_agent[r["agent"]][0] += r["cost_usd"]
    else:
        e = uoc(r)
        if e is None:
            n_khong += 1
            continue
        est += e
        n_est += 1
        theo_ngay[r["day"]][1] += e
        theo_agent[r["agent"]][1] += e

tong = hd + est
print("KY DU LIEU: %s -> %s   (%d dong usage_resolved)" % (lo, hi, len(rows)))
print()
print("TIEN HIEN TREN DASHBOARD, ca ky:")
print("  tu HOA DON        $%10.4f   %5.1f%%   (%d dong)" % (hd, 100 * hd / tong, n_hd))
print("  SUY tu bang gia   $%10.4f   %5.1f%%   (%d dong)" % (est, 100 * est / tong, n_est))
print("  tong              $%10.4f            (%d dong khong tra duoc gia)"
      % (tong, n_khong))
print()
print("THEO AGENT (sap theo %% suy ra):")
kq = []
for k, (a, b) in theo_agent.items():
    kq.append((100 * b / (a + b) if a + b else 0, k, a, b))
for p, k, a, b in sorted(kq, reverse=True):
    print("  %-30s hoa don $%8.4f | suy $%8.4f | %5.1f%% suy ra" % (k, a, b, p))
print()
ngay = [(100 * b / (a + b) if a + b else 0, d, a + b) for d, (a, b) in theo_ngay.items()]
ngay.sort(reverse=True)
print("10 NGAY co ty le suy ra CAO NHAT (trong so ngay co tien > $0,01):")
for p, d, t in [x for x in ngay if x[2] > 0.01][:10]:
    print("  %s   %5.1f%% suy ra   (tong $%.4f)" % (d, p, t))
print()
n30 = [x for x in ngay if x[2] > 0.01][:30]
print("So ngay co tren 50%% tien la suy ra: %d / %d ngay co tien"
      % (sum(1 for x in ngay if x[2] > 0.01 and x[0] > 50),
         sum(1 for x in ngay if x[2] > 0.01)))
