"""
Yazilim yigini (AWLC kademeli MLC + zIIP) duyarlilik analizi, statik mod.
Calistirma (proje kokunden):  python src/tools/software_sensitivity.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

DATA_TB = 20


def run(tps, avail=0.999):
    r = m.solve(tps, avail, "average", None, 99, verbose=False, data_tb=DATA_TB)
    return None if r is None else (r[0], r[1], r[2])


def fmt(tps, res):
    if res is None:
        return "infeasible"
    tier, topo, c = res
    return (f"{topo.code} {tier.model:<9} {tier.msu:>6,.0f} MSU  toplam ${c['total']:>10,.0f}/ay  "
            f"yazilim ${c['software']:>9,.0f} (%{c['software'] / c['total'] * 100:4.1f})  "
            f"${c['total'] / tps:6.2f}/TPS/ay  zIIP {m.ziip_engines(tier)}")


def with_attr(name, value, fn):
    old = getattr(m, name)
    setattr(m, name, value)
    try:
        return fn()
    finally:
        setattr(m, name, old)


def main():
    print("0) Kalibrasyon: urun katsayilari ve ornek MSU noktalari")
    print("   " + ", ".join(f"{k} x{v:.3f}" for k, v in m.SW_PRODUCT_FACTORS.items()))
    for msu in [35, 150, 265, 785, 1524, 3059, 7513]:
        t, parts = m.software_monthly_cost(msu, breakdown=True)
        print(f"   {msu:>5} MSU  ${t:>9,.0f}/ay  ${t / msu:>6,.0f}/MSU  "
              + "  ".join(f"{k} ${v:,.0f}" for k, v in parts.items()))

    print("\n1) TPS -> maliyet/TPS (%99.9, 20 TB): kademeli MLC olcek ekonomisi")
    for tps in [1000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000]:
        print(f"   {tps:>8}  {fmt(tps, run(tps))}")

    print("\n2) Eski dogrusal $40/MSU ile karsilastirma (50K TPS)")
    old_fn = m.software_monthly_cost
    m.software_monthly_cost = lambda msu, breakdown=False: msu * 40.0
    try:
        print(f"   dogrusal $40   {fmt(50000, run(50000))}")
    finally:
        m.software_monthly_cost = old_fn
    print(f"   AWLC kademeli  {fmt(50000, run(50000))}")

    print("\n3) Mutlak fiyat seviyesi SW_PRICE_LEVEL_FACTOR (50K TPS)")
    for v in [0.5, 0.75, 1.0, 1.25, 1.5]:
        print(f"   x{v:<5} {with_attr('SW_PRICE_LEVEL_FACTOR', v, lambda: fmt(50000, run(50000)))}")

    print("\n4) zIIP'e kayan pay ZIIP_OFFLOAD_FRACTION (50K TPS)")
    for v in [0.0, 0.10, 0.25, 0.40]:
        print(f"   f={v:<5} {with_attr('ZIIP_OFFLOAD_FRACTION', v, lambda: fmt(50000, run(50000)))}")

    print("\n5) L4+ kademe dusus orani (50K ve 500K TPS)")
    base_levels = list(m.AWLC_LEVELS)
    for decay in [1.0, 0.8, 0.7]:
        levels = base_levels[:5]
        rate = base_levels[4][1]
        for upper, _ in base_levels[5:]:
            rate *= decay
            levels.append((upper, rate))
        m.AWLC_LEVELS = levels
        try:
            for tps in (50000, 500000):
                print(f"   x{decay:<4} {tps:>7}  {fmt(tps, run(tps))}")
        finally:
            m.AWLC_LEVELS = base_levels

    print("\n6) Availability -> GDPS yazilim premium'u (50K TPS)")
    for av in [0.999, 0.99999, 0.9999999]:
        print(f"   {av:<9} {fmt(50000, run(50000, av))}")


if __name__ == "__main__":
    main()
