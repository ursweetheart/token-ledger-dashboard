"""Kiem MOI con so ghi trong artifact cua change serve-department-metrics-from-database
voi du lieu song. Chay mot lan, khong ghi gi."""
import sys, json, urllib.request, collections, pathlib, statistics
sys.stdout.reconfigure(encoding="utf-8")

B = "http://127.0.0.1:8000"
P = "?start=2026-07-19&end=2026-08-17"
get = lambda p: json.load(urllib.request.urlopen(B + p))

cat = get("/api/catalog")
rows = get("/api/usage-by-account" + P)["rows"]
inv = get("/api/usage" + P)["rows"]
allu = get("/api/usage?start=2026-01-01&end=2026-08-17")["rows"]
price = {m["model_id"]: m for m in cat["models"]}
byname = {m["name"]: m for m in cat["models"]}
src = pathlib.Path("web/js/app.js").read_text(encoding="utf-8")

state = {"ok": 0, "fail": 0}


def check(label, got, want, tol=0):
    good = abs(got - want) <= tol if tol else got == want
    tag = "ok  " if good else "HONG"
    extra = "" if good else "   != mong doi " + str(want)
    print("  [" + tag + "] " + label.ljust(46) + str(got) + extra)
    state["ok" if good else "fail"] += 1


check("dim_unit tong", len(cat["units"]), 130)
check("dim_unit ky thuat", sum(1 for u in cat["units"] if u["is_technical"]), 8)
check("dim_unit that", sum(1 for u in cat["units"] if not u["is_technical"]), 122)
# Dem TRONG KHOI ORG_UNITS, khong dem ca file: app.js:591 con mot `{id:` nua - do la
# don vi TU SINH khi unitOf() gap ten phong ban la, khong thuoc bang go cung.
lines = src.split("\n")
a = next(i for i, l in enumerate(lines) if l.startswith("var ORG_UNITS"))
depth = 0
for b in range(a, len(lines)):
    depth += lines[b].count("[") - lines[b].count("]")
    if depth == 0 and b > a:
        break
check("ORG_UNITS go cung (trong khoi)", sum(l.count("{id:") for l in lines[a:b + 1]), 108)
check("don vi tu sinh ngoai khoi", src.count("{id:") - sum(l.count("{id:") for l in lines[a:b + 1]), 1)
check("usage-by-account so dong", len(rows), 76)
check("dong thieu model_id", sum(1 for r in rows if r.get("model_id") is None), 0)
check("model co gia nguon google", sum(1 for m in cat["models"] if m["price_source"] == "google"), 10)
check("ty le gia pro / flash-lite",
      round(byname["gemini-2.5-pro"]["price_input"] / byname["gemini-2.5-flash-lite"]["price_input"], 1), 12.5)

suy = collections.defaultdict(float)
for r in rows:
    p = price[r["model_id"]]
    suy[r["agent"]] += ((r["input_tokens"] or 0) / 1e6 * (p["price_input"] or 0)
                        + (r["output_tokens"] or 0) / 1e6 * (p["price_output"] or 0))
hd = collections.defaultdict(float)
for r in inv:
    hd[r["agent"]] += r["cost_usd"] or 0

T = sum(hd.values())
HD = suy["Trợ Lý Ảo Hợp Đồng"]
RA = suy["Trợ lý ảo Ralli"]
check("tong hoa don ky", round(T, 4), 62.6442, 0.0001)
check("suy ra Tro Ly Ao Hop Dong", round(HD, 4), 15.1333, 0.0001)
check("suy ra Tro ly ao Ralli", round(RA, 4), 1.2988, 0.0001)
check("hoa don cua Tro ly ao Ralli = 0", round(hd.get("Trợ lý ảo Ralli", 0), 4), 0.0)
check("tong suy ra moi phong ban", round(HD + RA, 4), 16.4321, 0.0001)
check("% hoa don quy duoc", round(100 * HD / T, 1), 24.2, 0.05)
check("% hoa don khong quy duoc", round(100 * (T - HD) / T, 1), 75.8, 0.05)
check("USD khong quy duoc", round(T - HD, 4), 47.5109, 0.0001)
check("tien VND moi phong ban", round((HD + RA) * float(cat["fx_rate"]["vnd_per_usd"])), 414090, 2)

n = 0
se = sr = 0.0
err = []
for r in allu:
    if r["token_source"] != "billing" or r["cost_usd"] is None:
        continue
    p = byname.get(r["model"])
    if not p or p["price_input"] is None:
        continue
    e = ((r["input_tokens"] or 0) / 1e6 * p["price_input"]
         + (r["output_tokens"] or 0) / 1e6 * (p["price_output"] or 0)
         + (r["cached_tokens"] or 0) / 1e6 * (p["price_cached"] or 0))
    n += 1
    se += e
    sr += r["cost_usd"]
    if r["cost_usd"] > 0.01:
        err.append(abs(e - r["cost_usd"]) / r["cost_usd"])

check("so dong doi chieu billing", n, 965)
check("tong suy tu bang gia", round(se, 4), 291.6462, 0.0001)
check("tong hoa don tuong ung", round(sr, 4), 291.9856, 0.0001)
check("lech tong %", round(100 * (se - sr) / sr, 1), -0.1, 0.05)
check("lech trung vi moi dong %", round(100 * statistics.median(err), 1), 0.0, 0.05)
check("dong lech nhieu nhat %", round(100 * max(err), 1), 6.4, 0.05)

print()
print("  " + str(state["ok"]) + " dat | " + str(state["fail"]) + " hong")
sys.exit(1 if state["fail"] else 0)
