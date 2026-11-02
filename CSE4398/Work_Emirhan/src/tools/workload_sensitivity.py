"""
Is yuku profili ("1 islem"in bilesimi) duyarlilik analizi, statik mod.
Calistirma (proje kokunden):  python src/tools/workload_sensitivity.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

DATA_TB = 20
REF_TPS = 10000


def fmt(tps, workload):
    r = m.solve(tps, 0.999, workload, None, 99, verbose=False, data_tb=DATA_TB)
    if r is None:
        return "infeasible (tek sistem kapasitesi yetmiyor)"
    tier, topo, c = r[0], r[1], r[2]
    sp = c["storage_plan"]
    return (f"{tier.model:<9} {tier.msu:>6,.0f} MSU  ${c['total']:>10,.0f}/ay  "
            f"${c['total'] / tps:7.2f}/TPS  D_io {sp['io_delay_s'] * 1000:.2f} ms  "
            f"{sp['iops_required']:>9,.0f} IOPS")


def with_attr(name, value, fn):
    old = getattr(m, name)
    setattr(m, name, value)
    try:
        return fn()
    finally:
        setattr(m, name, old)


def main():
    print("0) Profiller")
    for w in m.WORKLOAD_PROFILES.values():
        top = m.Z16_TIERS[-1]
        cap = m.tier_max_tps(top, w)
        print(f"   {w}  CPU {w.cpu_us():.0f} us | tek z16 (7K0) tavani {cap:,.0f} TPS")

    print(f"\n1) Profil x TPS (%99.9, {DATA_TB} TB)")
    for name in m.WORKLOAD_PROFILES:
        for tps in [1000, 10000, 50000, 150000]:
            print(f"   {name:<11} {tps:>7}  {fmt(tps, name)}")

    print(f"\n2) CPU varsayimlari ({REF_TPS:,} TPS, oltp_rw)")
    for name, vals in [("CPU_US_PER_SQL_READ", [15.0, 30.0, 60.0]),
                       ("CPU_US_PER_SQL_WRITE", [40.0, 70.0, 140.0])]:
        for v in vals:
            w = with_attr(name, v, lambda: m.get_workload("oltp_rw").cpu_weight())
            print(f"   {name}={v:<6} w={w:5.2f}  "
                  f"{with_attr(name, v, lambda: fmt(REF_TPS, 'oltp_rw'))}")

    print(f"\n3) I/O varsayimlari ({REF_TPS:,} TPS, oltp_rw)")
    for name, vals in [("BP_HIT_RATIO", [0.90, 0.95, 0.99]),
                       ("GETPAGES_PER_SQL_READ", [3.0, 4.0, 6.0])]:
        for v in vals:
            print(f"   {name}={v:<5} {with_attr(name, v, lambda: fmt(REF_TPS, 'oltp_rw'))}")

    print(f"\n4) Latency hedefi p99 (oltp_rw, {REF_TPS:,} TPS)")
    for lat in [None, 50, 10, 5, 2]:
        r = m.solve(REF_TPS, 0.999, "oltp_rw", lat, 99, verbose=False, data_tb=DATA_TB)
        label = "yok" if lat is None else f"{lat} ms"
        if r is None:
            print(f"   {label:<6} infeasible")
        else:
            print(f"   {label:<6} {r[0].model:<9} ${r[2]['total']:>10,.0f}/ay")


if __name__ == "__main__":
    main()
