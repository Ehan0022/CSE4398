"""
data/z16_a01_capacity.csv dosyasini ham IBM verilerinden uretir.
Calistirma (repo kokunden):  python src/tools/build_z16_capacity_table.py

Girdi (data/raw/):
  lspr_itrr_3931.csv                  4xx/5xx/6xx 1-39 CP ve 701-703: PCI, MSU, Low/Avg/High [LSPR]
  mainframe_exhibit_3931_7xx_msu.csv  701-7K0 (1-200 CP) resmi MSU degerleri [EXHIBIT]
  z16_max_pci_anchor.csv              7K0 = 215,089 PCI (bagimsiz dogrulama) [STINE]

Yontem (7xx 704-7K0 icin PCI turetimi):
  IBM bu kademeler icin PCI yayimlamiyor (ITRR sayfasi erisimde 703'te kesiliyor),
  ama MSU degerleri resmi. MSU/PCI orani bilinen 120 satirda PCI'nin duzgun,
  azalan bir fonksiyonu; ~33.000 PCI'dan itibaren 0.11723'te sabitleniyor
  (632: 0.117222, 639: 0.117228). Bu oran egrisi bilinen satirlardan kurulur ve
  PCI = MSU / oran(PCI) sabit nokta iterasyonuyla cozulur.
  Dogrulama: (1) birini-disarida-birak hatasi bilinen satirlarda raporlanir;
  (2) 7K0 icin turetilen PCI, IBM'in yayimladigi 215,089 ile karsilastirilir.
"""
import bisect
import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "z16_a01_capacity.csv")

RATIO_FLOOR = 0.11723        # MSU/PCI, buyuk kademelerde (>= ~33K PCI)
FLOOR_FROM_PCI = 32963.0     # 3931-632 PCI'si; bu noktadan sonra oran sabit


def _read(name):
    with open(os.path.join(RAW, name)) as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def _ratio_curve(points):
    pts = sorted((p, m / p) for p, m in points)
    xs = [p for p, _ in pts]
    ys = [r for _, r in pts]
    sm = []
    for i in range(len(ys)):
        w = ys[max(0, i - 2):i + 3]
        sm.append(sum(w) / len(w))
    return xs, sm


def _ratio(pci, xs, sm):
    if pci >= FLOOR_FROM_PCI:
        return RATIO_FLOOR
    i = bisect.bisect_left(xs, pci)
    if i == 0:
        return sm[0]
    if i >= len(xs):
        return sm[-1]
    x0, x1, y0, y1 = xs[i - 1], xs[i], sm[i - 1], sm[i]
    return y0 + (y1 - y0) * (pci - x0) / (x1 - x0) if x1 > x0 else y0


def pci_from_msu(msu, xs, sm):
    p = msu / 0.12
    for _ in range(100):
        p = msu / _ratio(p, xs, sm)
    return p


def cps_from_code(code):
    """'701'..'799' -> 1..99 ; 'A0'..'K0' -> 100..200 (A=10, B=11, ..., K=20)."""
    s = code[1:]
    if s[0].isdigit():
        return int(s)
    return (ord(s[0]) - ord("A") + 10) * 10 + int(s[1])


def main():
    lspr = _read("lspr_itrr_3931.csv")
    exhibit = {r["model"]: int(r["msu"]) for r in _read("mainframe_exhibit_3931_7xx_msu.csv")}
    known = [(float(r["pci"]), float(r["msu"])) for r in lspr]
    xs, sm = _ratio_curve(known)

    # Dogrulama 1: birini disarida birak
    errs = []
    for i, (p, m) in enumerate(known):
        xi, si = _ratio_curve(known[:i] + known[i + 1:])
        errs.append(abs(pci_from_msu(m, xi, si) - p) / p)
    # Dogrulama 2: 7K0 bagimsiz capa
    anchor = _read("z16_max_pci_anchor.csv")[0]
    est_7k0 = pci_from_msu(exhibit["3931-7K0"], xs, sm)
    pci_per_lspr = sum(float(r["pci"]) / float(r["avg"]) for r in lspr) / len(lspr)

    rows = []
    for r in lspr:
        rows.append({
            "model": r["processor"], "series": r["processor"][5] + "xx",
            "cps": int(r["cp"]), "pci": int(r["pci"]), "msu": int(r["msu"]),
            "lspr_low": r["low"], "lspr_avg": r["avg"], "lspr_high": r["high"],
            "pci_source": "LSPR", "msu_source": "LSPR",
        })
    have = {r["model"] for r in rows}
    for model, msu in exhibit.items():
        if model in have:
            # 701-703: iki kaynagin MSU degeri ayni olmali
            row = next(x for x in rows if x["model"] == model)
            assert row["msu"] == msu, (model, row["msu"], msu)
            continue
        pci = pci_from_msu(msu, xs, sm)
        rows.append({
            "model": model, "series": "7xx", "cps": cps_from_code(model.split("-")[1]),
            "pci": int(round(pci)), "msu": msu,
            "lspr_low": "", "lspr_avg": f"{pci / pci_per_lspr:.2f}", "lspr_high": "",
            "pci_source": "DERIVED_FROM_MSU", "msu_source": "EXHIBIT",
        })
    rows.sort(key=lambda x: (x["series"], x["cps"]))
    assert len(rows) == 317, len(rows)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} kademe yazildi -> {OUT}")
    print(f"PCI/LSPR orani (bilinen satirlar ortalamasi): {pci_per_lspr:.2f}")
    print(f"Birini-disarida-birak PCI hatasi: maks %{100*max(errs):.2f}, ort %{100*sum(errs)/len(errs):.2f}")
    print(f"7K0: turetilen {est_7k0:,.0f} PCI, IBM {int(anchor['pci']):,} PCI, "
          f"fark %{100*(est_7k0-int(anchor['pci']))/int(anchor['pci']):+.3f}")


if __name__ == "__main__":
    main()
