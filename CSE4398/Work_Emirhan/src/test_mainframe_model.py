"""
mainframe_model.py icin hizli tutarlilik testleri (sadece standard library).
Calistirma:  python test_mainframe_model.py
"""
import mainframe_model as m

LATENCIES_MS = [500, 200, 100, 50, 20, 15, 12, 10, 8, 6, 5, 4, 3]


def _cost(r):
    return r[2]["total"] if r else float("inf")


def test_latency_monotonic():
    """Daha siki latency hedefi hicbir zaman daha ucuz sonuc vermemeli."""
    for rni in ["low", "average", "high"]:
        for tps in [2000, 10000, 50000, 120000, 200000]:
            no_lat = _cost(m.solve(tps, 0.999, rni, None, verbose=False))
            prev = None
            for lat in LATENCIES_MS:
                c = _cost(m.solve(tps, 0.999, rni, lat, 99, verbose=False))
                assert c >= no_lat - 1e-6, (rni, tps, lat, "latency'siz durumdan ucuz")
                if prev is not None:
                    assert c >= prev - 1e-6, (rni, tps, lat, "monotonluk ihlali")
                prev = c


def test_latency_binds_when_tight():
    """Latency girdisi etkin olmali: siki hedef kademeyi degistirmeli."""
    loose = m.solve(50000, 0.999, "average", 200, 99, verbose=False)
    tight = m.solve(50000, 0.999, "average", 20, 99, verbose=False)
    assert _cost(tight) > _cost(loose)
    d_io_ms = m.io_delay_seconds("average", m.TOPOLOGIES[0]) * 1000
    assert m.solve(50000, 0.999, "average", d_io_ms * 0.95, 99, verbose=False) is None


def test_tier_table_complete():
    """z16 A01: 317 kademe = 4xx/5xx/6xx x 39 + 7xx x 200 [SG24-8950]."""
    count = {}
    for t in m.Z16_TIERS:
        count[t.series] = count.get(t.series, 0) + 1
    assert count == {"4xx": 39, "5xx": 39, "6xx": 39, "7xx": 200}, count
    for series in count:
        ts = sorted((t for t in m.Z16_TIERS if t.series == series), key=lambda t: t.cps)
        assert [t.cps for t in ts] == list(range(1, len(ts) + 1))
        # kapasite ve MSU, CP sayisiyla kesin artmali
        assert all(a.pci < b.pci and a.msu < b.msu for a, b in zip(ts, ts[1:]))


def test_capacity_bridge_reproduces_anchors():
    """Kopru kendi z13 capalarini %2 icinde uretmeli; 7K0 PCI'si IBM degerine yakin olmali."""
    assert abs(m.TPS_PER_PCI * 21579 - 174000) / 174000 < 0.02
    assert abs(m.TPS_PER_PCI * 29048 - 227000) / 227000 < 0.02
    k0 = next(t for t in m.Z16_TIERS if t.model == "3931-7K0")
    assert abs(k0.pci - 215089) / 215089 < 0.005


def test_subcapacity_billing_capped():
    """Faturalanan MSU kurulu MSU'yu asmamali ve yukle artmali."""
    t = m.Z16_TIERS[-1]
    raw = m.raw_tier_tps(t)
    assert m.consumed_msu(t, raw * 2) == t.msu
    assert m.consumed_msu(t, raw * 0.3) < m.consumed_msu(t, raw * 0.6)


def test_cod_advantage_grows_with_burstiness():
    """peak/avg orani arttikca gecici kapasitenin (B veya C) permanent'a
    gore goreli tasarrufu artmali."""
    def savings(preset):
        s = m.solve_yearly(preset_name=preset, yearly_avg_tps=50000, verbose=False)
        perm = s["by_strategy"]["permanent"]["yearly_total"]
        flex = min(v["yearly_total"] for k, v in s["by_strategy"].items() if k != "permanent")
        return (perm - flex) / perm
    assert savings("retail_bursty") > savings("batch_heavy") > savings("steady_oltp")


def test_temporary_capacity_limits():
    """Gecici hedefler [COD] kurallarina uymali: <= 2 x base MSU, kurulu drawer
    siniri, CP azalmaz, 4xx/5xx'e gecis yok, alt-kapasite seviyesi dusmez."""
    order = {"4xx": 0, "5xx": 1, "6xx": 2, "7xx": 3}
    for base in m.Z16_TIERS[::7]:
        fmax = m.feature_for_cps(base.cps)[1]
        for t in m.temporary_targets(base):
            assert t.msu <= 2 * base.msu + 1e-9
            assert base.cps <= t.cps <= fmax
            if t.series != base.series:
                assert t.series in ("6xx", "7xx") and order[t.series] > order[base.series]
    # drawer siniri baglayici olabilmeli: 735 (Max39) en fazla 739'a cikabilir
    b735 = next(t for t in m.Z16_TIERS if t.model == "3931-735")
    assert m.max_temporary_tier(b735).model == "3931-739"
    # %100 siniri baglayici olabilmeli: 705 icin hedef MSU <= 2 x 1232
    b705 = next(t for t in m.Z16_TIERS if t.model == "3931-705")
    top = m.max_temporary_tier(b705)
    assert top.msu <= 2 * b705.msu and top.cps < 39


def test_yearly_strategies_respect_limits():
    """Secilen B/C stratejilerinin CoD tepe kademesi base'den izinli olmali."""
    for preset in m.WORKLOAD_PRESETS:
        s = m.solve_yearly(preset_name=preset, yearly_avg_tps=50000, verbose=False)
        for name, sim in s["by_strategy"].items():
            if name == "permanent":
                continue
            for t in (sim["peak_tier"], sim["corridor_tier"]):
                if t is not None:
                    assert m.is_allowed_temporary_target(sim["base_tier"], t), (preset, name, t)


def test_tfp_software_revenue_neutral_and_corridor_monotonic():
    """TFP-SW fiyati permanent konfigurasyonun R4HA faturasini geri uretmeli;
    corridor ucreti CORRIDOR_PREMIUM ile artmali."""
    prof = m.generate_hourly_profile("batch_heavy", 50000)
    perm = next(t for t in m.Z16_TIERS if m.is_capacity_feasible(t, max(prof)))
    topo = m.TOPOLOGIES[0]
    sp = m.simulate_yearly(prof, perm, topo, strategy="permanent")
    price = m.tfp_software_price_per_msu_hour(prof, sp, perm)
    mh = sum(m.consumed_msu(perm, x) for x in prof)
    assert abs(price * mh - sp["yearly_software"]) < 1e-6 * sp["yearly_software"]

    base = next(t for t in m.Z16_TIERS if t.model == "3931-512")
    corr = m.corridor_tier_for(base)
    old = m.CORRIDOR_PREMIUM
    try:
        costs = []
        for p in (1.0, 2.0):
            m.CORRIDOR_PREMIUM = p
            s = m.simulate_yearly(prof, base, topo, strategy="tfp", corridor_tier=corr,
                                  sw_price_per_msu_hour=price)
            costs.append(s["corridor_cost_total"])
        assert costs[1] > costs[0] > 0
    finally:
        m.CORRIDOR_PREMIUM = old


def test_storage_sizing_and_mainframe_features():
    """DS8900F boyutlandirmasi: kopya sayisi topolojiden, model IOPS'tan,
    kapasite veri hacminden gelir; zHyperLink ve senkron replikasyon D_io'yu
    beklenen yonde degistirir."""
    m1, m2, m3 = m.TOPOLOGIES[0], m.TOPOLOGIES[1], m.TOPOLOGIES[2]
    p1 = m.storage_plan(50000, "average", m1, data_tb=20)
    p3 = m.storage_plan(50000, "average", m3, data_tb=20)
    assert p1["copies"] == 1 and p3["copies"] == 4
    assert p3["monthly_total"] > p1["monthly_total"]
    assert m.storage_plan(50000, "average", m1, data_tb=200)["capex"] > p1["capex"]
    # 860K IOPS'u asan yuk DS8950F gerektirmeli
    big = m.storage_plan(150000, "average", m1, data_tb=20)
    assert big["arrays"][0]["model"].family == "DS8950F"
    assert p1["arrays"][0]["model"].family == "DS8910F"
    # senkron Metro Mirror yazma gecikmesini artirir
    assert m.io_delay_seconds("average", m2) > m.io_delay_seconds("average", m1)
    old = m.ZHYPERLINK_ENABLED
    try:
        with_zhl = m.io_service_time_seconds(m1)
        m.ZHYPERLINK_ENABLED = False
        assert m.io_service_time_seconds(m1) > with_zhl
    finally:
        m.ZHYPERLINK_ENABLED = old


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK  {name}")
