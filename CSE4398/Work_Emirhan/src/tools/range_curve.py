"""
Maliyet/TPS egrisinin aralik (low / mid / high) hali ve kalem dokumu.
Cikti: ekrana tablo + data/out/range_curve_<profil>.csv (grafik icin).
Calistirma (proje kokunden):  python src/tools/range_curve.py [profil]
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import mainframe_model as m  # noqa: E402

TPS_POINTS = [500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 150000]
DATA_TB = 20


def main():
    workload = sys.argv[1] if len(sys.argv) > 1 else m.DEFAULT_WORKLOAD
    out_dir = os.path.join(HERE, "..", "..", "data", "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"range_curve_{workload}.csv")
    rows = []
    print(f"Profil: {m.get_workload(workload)}  |  %99.9, {DATA_TB} TB")
    print(f"{'TPS':>8} | {'low $/TPS':>10} {'mid $/TPS':>10} {'high $/TPS':>10} | "
          f"mid dokum: yazilim / personel / donanim+bakim+enerji / storage")
    for tps in TPS_POINTS:
        rng = m.solve_range(tps, workload=workload, data_tb=DATA_TB)
        cells, rec = [], {"tps": tps}
        for level in m.RANGE_LEVELS:
            x = rng[level]
            v = None if x is None else x["cost"]["total"] / tps
            rec[f"{level}_usd_per_tps"] = v
            rec[f"{level}_tier"] = None if x is None else x["tier"].model
            cells.append("     infeas" if v is None else f"{v:>10.2f}")
        mid = rng["mid"]
        if mid is not None:
            c = mid["cost"]
            hw = c["hardware_amort"] + c["maintenance"] + c["energy"]
            parts = [c["software"], c["staff"], hw, c["storage"]]
            share = " / ".join(f"%{p / c['total'] * 100:4.1f}" for p in parts)
            rec.update(mid_software=c["software"], mid_staff=c["staff"],
                       mid_hw_maint_energy=hw, mid_storage=c["storage"],
                       mid_total=c["total"])
        else:
            share = "-"
        print(f"{tps:>8} | {' '.join(cells)} | {share}")
        rows.append(rec)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "tps", k))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV: {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
