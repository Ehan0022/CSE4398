"""
Storage katmani (DS8900F) duyarlilik analizi, statik mod.
Calistirma (proje kokunden):  python src/tools/storage_sensitivity.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402


def line(tps, avail, data_tb, rni="average", latency_ms=None):
    r = m.solve(tps, avail, rni, latency_ms, 99, verbose=False, data_tb=data_tb)
    if r is None:
        return "infeasible"
    tier, topo, cost = r[0], r[1], r[2]
    sp = cost["storage_plan"]
    share = cost["storage"] / cost["total"]
    return (f"{topo.code} {tier.model:<9} toplam ${cost['total']:>9,.0f}/ay  storage ${cost['storage']:>8,.0f} "
            f"(%{share*100:4.1f})  {sp['raw_tb_total']:>6,.0f} TB ham  D_io {sp['io_delay_s']*1000:.2f} ms  "
            f"[{m.describe_storage(sp)}]")


def main():
    print("1) Veri hacmi (50K TPS, %99.9):")
    for tb in [5, 20, 100, 500, 2000]:
        print(f"   {tb:>5} TB  {line(50000, 0.999, tb)}")
    print("\n2) Availability -> kopya sayisi (50K TPS, 20 TB):")
    for av in [0.999, 0.99999, 0.999999, 0.9999999]:
        print(f"   {av:<9}  {line(50000, av, 20)}")
    print("\n3) TPS -> IOPS -> model (20 TB, %99.9):")
    for tps in [10000, 50000, 90000, 150000, 300000]:
        print(f"   {tps:>7}  {line(tps, 0.999, 20)}")
    print("\n4) Varsayim taramasi (50K TPS, 20 TB, %99.9) - storage aylik maliyeti:")
    sweeps = [("STORAGE_DISCOUNT", [0.5, 0.7, 0.85]),
              ("DB_OVERHEAD_FACTOR", [1.2, 1.5, 2.0]),
              ("HOST_COMPRESSION_RATIO", [1.0, 1.5, 2.5]),
              ("STORAGE_LICENSE_RATE_BASE", [0.05, 0.15, 0.30])]
    for name, vals in sweeps:
        old = getattr(m, name)
        cells = []
        for v in vals:
            setattr(m, name, v)
            p = m.storage_plan(50000, "average", m.TOPOLOGIES[0], data_tb=20)
            cells.append(f"{v}: ${p['monthly_total']:,.0f}")
        setattr(m, name, old)
        print(f"   {name:<26} " + " | ".join(cells))
    print("\n5) I/O gecikmesi (average RNI, islem basina D_io):")
    for zhl in [True, False]:
        m.ZHYPERLINK_ENABLED = zhl
        for t in m.TOPOLOGIES[:2]:
            print(f"   zHyperLink={'acik' if zhl else 'kapali':<6} {t.code}: "
                  f"I/O {m.io_service_time_seconds(t)*1e6:.0f} us, D_io {m.io_delay_seconds('average', t)*1000:.2f} ms")
    m.ZHYPERLINK_ENABLED = True
    for km in [10, 50, 100]:
        m.METRO_DISTANCE_KM = km
        print(f"   Metro Mirror {km:>3} km (M2): D_io {m.io_delay_seconds('average', m.TOPOLOGIES[1])*1000:.2f} ms")
    m.METRO_DISTANCE_KM = 20.0


if __name__ == "__main__":
    main()
