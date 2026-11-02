"""
Yedekleme (TS7770) ve 5 yillik NPV icin duyarlilik tablolari.

  python src/tools/npv_sensitivity.py           # tumu
  python src/tools/npv_sensitivity.py --fast    # yillik strateji bolumu (4) haric

1) Yedekleme: veri hacmi ekseni ve varsayimlar (10K TPS, %99,9)
2) Statik NPV (10K TPS, oltp_rw, 20 TB): yil yil nakit akisi ve kalem dokumu
3) Iskonto orani x TPS buyumesi: NPV ve seviyelendirilmis $/TPS/ay
4) Yillik stratejiler, 5 yillik NPV: preset x strateji; TFP buyume fiyati ve buyume 0
5) Fiyat artislari tek tek (statik NPV)
6) NPV araligi (low / mid / high) ve tornado, uc TPS noktasinda
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

TPS = 10000
DATA_TB = 20
LEVELS = ("low", "mid", "high")


def backup_section():
    print("1) Yedekleme (TS7770), 10K TPS, %99,9")
    print("   veri TB | image copy TB | log TB | site basina cache | kume | aylik yedek | "
          "toplamin %'si | storage")
    for d in (5, 20, 100, 500, 2000):
        r = m.solve(TPS, 0.999, verbose=False, data_tb=d)
        c = r[2]
        b = c["backup_plan"]
        print(f"   {d:>7,} | {b['image_copy_tb']:>13,.0f} | {b['log_tb']:>6,.0f} | "
              f"{b['cache_tb_per_site']:>14,.0f} TB | {b['clusters']:>4} | "
              f"${c['backup']:>10,.0f} | {c['backup'] / c['total']:>12.1%} | ${c['storage']:>9,.0f}")
    print("   Varsayim taramasi (20 TB, aylik yedek maliyeti):")
    for var, vals in (("BACKUP_RETENTION_WEEKS", (2, 4, 8)),
                      ("BACKUP_COMPRESSION", (3.0, 2.0, 1.5)),
                      ("BACKUP_CACHE_LIST_USD_PER_TB", (1000.0, 2000.0, 4000.0)),
                      ("BACKUP_DAILY_CHANGE", (0.01, 0.03, 0.05)),
                      ("LOG_BYTES_PER_SQL_WRITE", (200.0, 400.0, 1000.0)),
                      ("STORAGE_DISCOUNT", (0.85, 0.70, 0.50))):
        cells = []
        for v in vals:
            with m.use_values({var: v}):
                b = m.backup_plan(TPS / m.STATIC_PEAK_TO_AVG, data_tb=DATA_TB)
            cells.append(f"{v:g}: ${b['monthly_total']:,.0f}")
        print(f"     {var:<30} " + " | ".join(cells))


def static_npv_section():
    r = m.solve_npv(TPS, data_tb=DATA_TB)
    st = m.solve(TPS, 0.999, verbose=False, data_tb=DATA_TB)
    print(f"\n2) Statik NPV, {TPS:,} TPS (yil 1), %{m.NPV_TPS_GROWTH*100:.0f}/yil buyume, "
          f"iskonto %{m.NPV_DISCOUNT_RATE*100:.0f}")
    m.print_npv(r)
    print(f"   karsilastirma: statik aylik ${st[2]['total']:,.0f} -> ${st[2]['total']/TPS:,.2f}/TPS/ay; "
          f"60 ay x statik = ${60*st[2]['total']:,.0f}")


def rate_growth_section():
    print("\n3) Iskonto orani x TPS buyumesi (statik NPV, milyon USD | $/TPS/ay)")
    rates = (0.05, 0.07, 0.10)
    print("   buyume | " + " | ".join(f"r = %{x*100:.0f}".ljust(18) for x in rates))
    for g in (0.0, 0.05, 0.10, 0.20):
        cells = []
        for rt in rates:
            r = m.solve_npv(TPS, data_tb=DATA_TB, tps_growth=g, discount_rate=rt)
            cells.append("infeasible".ljust(18) if r is None else
                         f"{r['npv']/1e6:7.2f} | {r['levelized_per_tps_month']:6.2f}".ljust(18))
        print(f"   %{g*100:4.0f}  | " + " | ".join(cells))


def yearly_section():
    print("\n4) Yillik stratejiler, 5 yillik NPV (milyon USD; * = en ucuz)")
    cases = (("varsayilan", {}, None),
             ("TFP buyume fiyati 1,0", {"TFP_GROWTH_PRICE_FACTOR": 1.0}, None),
             ("TPS buyumesi 0", {}, 0.0))
    for label, vals, g in cases:
        print(f"   {label}:")
        for preset in ("steady_oltp", "retail_bursty", "batch_heavy"):
            res = {}
            with m.use_values(vals):
                for s in ("permanent", "base_cod", "tfp"):
                    res[s] = m.solve_npv_yearly(preset, TPS, s, data_tb=DATA_TB, tps_growth=g)
            ok = {k: v["npv"] for k, v in res.items() if v is not None}
            win = min(ok, key=ok.get) if ok else None
            cells = " ".join(f"{k[0].upper()}{'*' if k == win else ' '}{ok[k]/1e6:8.3f}"
                             if k in ok else f"{k[0].upper()}  infeas"
                             for k in ("permanent", "base_cod", "tfp"))
            path = "->".join(r["tier"].model[-3:] for r in res[win]["years"]) if win else ""
            print(f"     {preset:<14} {cells}   kazananin base yolu {path}")


def escalation_section():
    print("\n5) Fiyat artislari tek tek (statik NPV, digerleri varsayilan)")
    base = m.solve_npv(TPS, data_tb=DATA_TB)["npv"]
    for var, vals in (("SW_PRICE_ESCALATION", (0.0, 0.03, 0.06)),
                      ("HW_SERVICE_ESCALATION", (0.0, 0.03, 0.06)),
                      ("WAGE_ESCALATION", (0.025, 0.033, 0.045)),
                      ("ENERGY_ESCALATION", (0.015, 0.04, 0.056)),
                      ("NPV_RESIDUAL_FRACTION", (0.0, 0.5, 1.0))):
        cells = []
        for v in vals:
            with m.use_values({var: v}):
                r = m.solve_npv(TPS, data_tb=DATA_TB)
            cells.append(f"{v:g}: ${r['npv']/1e6:.2f}M ({r['npv']/base - 1:+.1%})")
        print(f"   {var:<24} " + " | ".join(cells))


def range_section():
    print("\n6) NPV araligi (statik, NPV_RANGE_PARAMETERS) ve en buyuk 6 surucu")
    for tps in (1000, 10000, 50000):
        rng = m.solve_npv_range(tps, data_tb=DATA_TB)
        cells = " / ".join("infeas" if rng[k] is None else
                           f"${rng[k]['levelized_per_tps_month']:,.2f}" for k in LEVELS)
        npvs = " / ".join("infeas" if rng[k] is None else f"{rng[k]['npv']/1e6:,.1f}"
                          for k in LEVELS)
        print(f"   {tps:>6,} TPS: $/TPS/ay low/mid/high {cells}   NPV (M$) {npvs}")
    print(f"   Tornado ({TPS:,} TPS, NPV milyon USD):")
    for name, desc, lo, hi in m.npv_tornado(TPS, data_tb=DATA_TB)[:6]:
        print(f"     {desc:<42} {lo/1e6:7.2f} .. {hi/1e6:7.2f}")


def main():
    backup_section()
    static_npv_section()
    rate_growth_section()
    if "--fast" not in sys.argv:
        yearly_section()
    escalation_section()
    range_section()


if __name__ == "__main__":
    main()
