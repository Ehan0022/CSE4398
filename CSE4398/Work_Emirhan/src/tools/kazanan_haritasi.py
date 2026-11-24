"""
Kazanan haritasi (Degerlendirme #10): hangi girdide hangi platform kazaniyor?

Izgara: TPS x availability / RPO hedefi x eslestirilmis senaryo (KB-18).
Her hucrede ayni girdiyle iki model cozulur ve sunlar raporlanir:
  - kazanan (personel orani 1,0, ana senaryo), ya da yalnizca birinin
    kurulabildigi durum ("MF tek" / "x86 tek")
  - mainframe / x86 maliyet orani ve basabas personel orani
    (x86 personeli mainframe personelinin bu katini asarsa mainframe ucuz)
Ek tablo: %99,999 sinirinin maskelenemeyen platform payi u'ya hassasiyeti.

Cikti: ekrana tablolar + data/out/kazanan_haritasi.csv
Calistirma (proje kokunden):  python src/tools/kazanan_haritasi.py [--hizli]
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import common_model as cm  # noqa: E402
import x86_model as x  # noqa: E402

TPS_POINTS = [1000, 3000, 10000, 30000, 50000, 100000]
TARGETS = [
    # (etiket, availability, rpo_seconds)
    ("%99,9", 0.999, None),
    ("%99,99", 0.9999, None),
    ("%99,99 RPO0", 0.9999, 0),
    ("%99,995 RPO0", 0.99995, 0),
    ("%99,999", 0.99999, None),
    ("%99,999 RPO0", 0.99999, 0),
    ("%99,9995", 0.999995, None),
]
SCENARIOS = [
    # (etiket, x86 duzeyi, mainframe duzeyi, ortak duzey)
    ("orta", "mid", "mid", "mid"),
    ("mainframe_lehine", "high", "low", "mid"),
    ("x86_lehine", "low", "high", "mid"),
]


def cell(tps, avail, rpo):
    o = x.compare(tps, availability=avail, rpo_seconds=rpo)
    m, xx = o["mainframe"], o["x86"]
    rec = {"mf_topology": m[1].code if m else None,
           "x86_topology": xx["topology"].code if xx else None,
           "x86_db": xx["stack"].db if xx else None,
           "mf_usd_per_tps": o["mf_total"] / tps if m and xx else (m[2]["total"] / tps if m else None),
           "x86_usd_per_tps": o["x86_total"] / tps if m and xx else (xx["total"] / tps if xx else None),
           "ratio": None, "breakeven_staff_ratio": None}
    if m and xx:
        rec["ratio"] = o["mf_total"] / o["x86_total"]
        rec["breakeven_staff_ratio"] = o["breakeven_ratio"]
        rec["winner"] = "x86" if o["x86_total"] < o["mf_total"] else "MF"
    elif m:
        rec["winner"] = "MF tek"
    elif xx:
        rec["winner"] = "x86 tek"
    else:
        rec["winner"] = "yok"
    return rec


def fmt(rec):
    w = rec["winner"]
    if rec["ratio"] is None:
        return f"{w:>13}"
    return f"{w:>3} {rec['ratio']:4.2f}/{rec['breakeven_staff_ratio']:4.2f}"


def main():
    fast = "--hizli" in sys.argv
    tps_points = [1000, 10000, 50000] if fast else TPS_POINTS
    out_dir = os.path.join(HERE, "..", "..", "data", "out")
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    print("KAZANAN HARITASI (personel orani 1,0; hucre: kazanan oran/basabas personel orani)")
    print("  oran = mainframe / x86 aylik maliyet; basabas = x86 personeli bu katin uzerindeyse "
          "mainframe ucuz; 'MF tek' = yalnizca mainframe kurulabiliyor")
    for sc, xl, ml, cl in SCENARIOS:
        print(f"\nSenaryo: {sc}  (x86'ya ozgu {xl}, mainframe'e ozgu {ml}, ortak {cl})")
        print(f"  {'hedef':<14}" + "".join(f"{t:>15,}" for t in tps_points))
        with x.use_values(x.paired_values(xl, ml, cl)):
            for label, avail, rpo in TARGETS:
                line = f"  {label:<14}"
                for tps in tps_points:
                    rec = cell(tps, avail, rpo)
                    line += f"  {fmt(rec)}"
                    rows.append({"scenario": sc, "target": label, "availability": avail,
                                 "rpo_seconds": rpo, "tps": tps, **rec})
                print(line)

    print("\nHASSASIYET: %99,999 sinirinin maskelenemeyen platform payi u'ya bagliligi (10.000 TPS, orta)")
    for u in (0.0, 0.05, 0.10, 0.20):
        with x.use_values({"PLATFORM_UNMASKED_SHARE": u}):
            parts = []
            for label, avail, rpo in TARGETS[4:]:
                rec = cell(10000, avail, rpo)
                xt = f"{rec['x86_topology']} {rec['x86_db']}" if rec["x86_topology"] else "yok"
                parts.append(f"{label}: {rec['winner']} (x86 {xt})")
                rows.append({"scenario": f"u={u}", "target": label, "availability": avail,
                             "rpo_seconds": rpo, "tps": 10000, **rec})
            print(f"  u={u:<5} " + " | ".join(parts))
    print(f"  (ana deger u = {cm.PLATFORM_UNMASKED_SHARE}; aralik 0,05 / 0,10 / 0,20)")

    path = os.path.join(out_dir, "kazanan_haritasi.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV: {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
