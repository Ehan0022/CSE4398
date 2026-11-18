"""
Availability (olay tabanli) ve DR maliyeti icin duyarlilik tablolari.

  python src/tools/availability_sensitivity.py

1) Topoloji basina yillik kesinti dokumu ve availability araligi
2) Availability parametre gruplarinin tek tek salinimi
3) 10K TPS'te availability hedefi -> secilen topoloji ve maliyet (low/mid/high)
4) RPO / RTO kisitlarinin secime etkisi
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

TPS = 10000
DATA_TB = 20
LEVELS = ("low", "mid", "high")


def downtime_parts(t):
    s = m.SITE_EVENT_SCENARIOS[m.SITE_EVENT_LEVEL]
    t_rec = t.recovery_minutes() / 60.0
    site = s["rate"] * ((1 - s["p_long"]) * min(s["d_short_h"], t_rec)
                        + s["p_long"] * min(s["d_long_h"], t_rec))
    planned = (m.PLANNED_EVENTS_PER_YEAR[m.PLANNED_LEVEL]
               * m.PLANNED_OUTAGE_MINUTES[t.code][m.PLANNED_LEVEL] / 60.0)
    hw = m.CPC_HW_DOWNTIME_SECONDS[m.SITE_EVENT_LEVEL] / 3600.0 if t.n_frames == 1 else 0.0
    return site, planned, hw


def main():
    print("1) Yillik kesinti (mid) ve availability araligi")
    print("   topo | saha olayi h | planli h | CPC donanim s | toplam h | A (mid)    | "
          "aralik (en kotu - en iyi)")
    for t in m.TOPOLOGIES:
        site, planned, hw = downtime_parts(t)
        worst, best = t.availability_range()
        print(f"   {t.code}   | {site:12.3f} | {planned:8.3f} | {hw * 3600:13.3f} | "
              f"{t.annual_downtime_hours():8.3f} | {t.availability():.5%} | "
              f"{worst:.5%} - {best:.5%}")

    print("\n2) Tek grup salinimi (digerleri mid), availability")
    groups = [("SITE_EVENT_LEVEL", "saha olayi"), ("RECOVERY_LEVEL", "kurtarma suresi"),
              ("PLANNED_LEVEL", "planli kesinti")]
    for var, label in groups:
        row = []
        for lv in ("low", "high"):
            with m.use_values({var: lv}):
                row.append([t.availability() for t in m.TOPOLOGIES])
        cells = "  ".join(f"{t.code} {lo:.5%}..{hi:.5%}"
                          for t, lo, hi in zip(m.TOPOLOGIES, row[0], row[1]))
        print(f"   {label:<16} {cells}")

    print(f"\n3) {TPS:,} TPS, oltp_rw, {DATA_TB} TB: availability hedefi -> secim ve maliyet")
    print("   hedef     | mid secim       | $/TPS/ay low / mid / high (secilen topoloji)")
    for a in (0.999, 0.9995, 0.9999, 0.99995, 0.99999, 0.999999):
        r = m.solve(TPS, a, verbose=False, data_tb=DATA_TB)
        rng = m.solve_range(TPS, a, data_tb=DATA_TB)
        cells = " / ".join("infeas" if rng[k] is None else
                           f"{rng[k]['cost']['total'] / TPS:.2f} ({rng[k]['topology'].code})"
                           for k in LEVELS)
        sel = "infeasible" if r is None else f"{r[1].code} {r[0].model}"
        print(f"   {a:.4%} | {sel:<15} | {cells}")

    print("\n4) RPO / RTO kisitlari (%99,9)")
    for kw in ({}, {"rpo_seconds": 0}, {"rto_minutes": 60}, {"rto_minutes": 1},
               {"rpo_seconds": 0, "rto_minutes": 60}):
        r = m.solve(TPS, 0.999, verbose=False, data_tb=DATA_TB, **kw)
        res = "infeasible" if r is None else f"{r[1].code}, ${r[2]['total']:,.0f}/ay"
        print(f"   {str(kw):<40} -> {res}")


if __name__ == "__main__":
    main()
