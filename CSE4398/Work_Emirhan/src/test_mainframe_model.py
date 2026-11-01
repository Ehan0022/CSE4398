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
    for workload in ["redp_light", "oltp_rw", "oltp_heavy"]:
        for tps in [2000, 10000, 50000, 120000, 200000]:
            no_lat = _cost(m.solve(tps, 0.999, workload, None, verbose=False))
            prev = None
            for lat in LATENCIES_MS:
                c = _cost(m.solve(tps, 0.999, workload, lat, 99, verbose=False))
                assert c >= no_lat - 1e-6, (workload, tps, lat, "latency'siz durumdan ucuz")
                if prev is not None:
                    assert c >= prev - 1e-6, (workload, tps, lat, "monotonluk ihlali")
                prev = c


def test_latency_binds_when_tight():
    """Latency girdisi etkin olmali: siki hedef kademeyi degistirmeli."""
    loose = m.solve(50000, 0.999, "oltp_rw", 200, 99, verbose=False)
    tight = m.solve(50000, 0.999, "oltp_rw", 20, 99, verbose=False)
    assert _cost(tight) > _cost(loose)
    d_io_ms = m.io_delay_seconds("oltp_rw", m.TOPOLOGIES[0]) * 1000
    assert m.solve(50000, 0.999, "oltp_rw", d_io_ms * 0.95, 99, verbose=False) is None


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
        s = m.solve_yearly(preset_name=preset, yearly_avg_tps=10000, verbose=False)
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
        s = m.solve_yearly(preset_name=preset, yearly_avg_tps=10000, verbose=False)
        for name, sim in s["by_strategy"].items():
            if name == "permanent":
                continue
            for t in (sim["peak_tier"], sim["corridor_tier"]):
                if t is not None:
                    assert m.is_allowed_temporary_target(sim["base_tier"], t), (preset, name, t)


def test_tfp_software_revenue_neutral_and_corridor_monotonic():
    """TFP-SW fiyati permanent konfigurasyonun R4HA faturasini geri uretmeli;
    corridor ucreti CORRIDOR_PREMIUM ile artmali."""
    prof = m.generate_hourly_profile("batch_heavy", 10000)
    perm = next(t for t in m.Z16_TIERS if m.is_capacity_feasible(t, max(prof)))
    topo = m.TOPOLOGIES[0]
    sp = m.simulate_yearly(prof, perm, topo, strategy="permanent")
    price = m.tfp_software_price_per_msu_hour(prof, sp, perm)
    mh = sum(m.consumed_msu(perm, x) for x in prof)
    assert abs(price * mh - sp["yearly_software"]) < 1e-6 * sp["yearly_software"]

    base = next(t for t in m.Z16_TIERS if t.msu >= 0.6 * perm.msu and t.series == perm.series)
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
    p1 = m.storage_plan(50000, "oltp_rw", m1, data_tb=20)
    p3 = m.storage_plan(50000, "oltp_rw", m3, data_tb=20)
    assert p1["copies"] == 1 and p3["copies"] == 4
    assert p3["monthly_total"] > p1["monthly_total"]
    assert m.storage_plan(50000, "oltp_rw", m1, data_tb=200)["capex"] > p1["capex"]
    # 860K IOPS'u asan yuk DS8950F gerektirmeli
    big = m.storage_plan(150000, "oltp_rw", m1, data_tb=20)
    assert big["arrays"][0]["model"].family == "DS8950F"
    assert p1["arrays"][0]["model"].family == "DS8910F"
    # senkron Metro Mirror yazma gecikmesini artirir
    assert m.io_delay_seconds("oltp_rw", m2) > m.io_delay_seconds("oltp_rw", m1)
    old = m.ZHYPERLINK_ENABLED
    try:
        with_zhl = m.io_service_time_seconds(m1)
        m.ZHYPERLINK_ENABLED = False
        assert m.io_service_time_seconds(m1) > with_zhl
    finally:
        m.ZHYPERLINK_ENABLED = old


def test_awlc_software_stack_and_ziip():
    """AWLC: IBM ornek faturasini (265 MSU) yeniden uretmeli, toplam artan ama
    MSU basina azalan olmali; zIIP payi faturalanan MSU'yu dusurmeli."""
    # kalibrasyon capalari: z/OS ve Db2 265 MSU'da ornek faturaya esit
    _, parts = m.software_monthly_cost(265, breakdown=True)
    assert abs(parts["z/OS"] - 75459) < 1 and abs(parts["Db2"] - 31876) < 1
    # Db2 referans egrisi IBM tablosunu kumulatif uretir (265 MSU = $30,076)
    assert abs(m._awlc_reference_curve(265) - 30076) < 1
    msus = [10, 45, 46, 175, 315, 575, 875, 1315, 1975, 5000]
    costs = [m.software_monthly_cost(x) for x in msus]
    assert all(a < b for a, b in zip(costs, costs[1:]))
    per = [c / x for c, x in zip(costs, msus)]
    assert all(a > b for a, b in zip(per, per[1:]))
    # olcek ekonomisi: maliyet/TPS buyuk hacimde belirgin dusmeli
    lo = m.solve(1000, verbose=False, data_tb=20)[2]["total"] / 1000
    hi = m.solve(100000, verbose=False, data_tb=20)[2]["total"] / 100000
    assert hi < lo / 3
    # zIIP: daha fazla offload -> daha az faturalanan MSU, zIIP motoru > 0
    old = m.ZIIP_OFFLOAD_FRACTION
    try:
        m.ZIIP_OFFLOAD_FRACTION = 0.0
        r0 = m.solve(50000, verbose=False)
        assert m.ziip_engines(r0[0]) == 0
        m.ZIIP_OFFLOAD_FRACTION = 0.25
        r1 = m.solve(50000, verbose=False)
        assert r1[0].msu < r0[0].msu and r1[2]["software"] < r0[2]["software"]
        assert 0 < m.ziip_engines(r1[0]) <= m.ZIIP_PER_CP_LIMIT * r1[0].cps
    finally:
        m.ZIIP_OFFLOAD_FRACTION = old


def test_workload_profiles():
    """Is yuku profili: REDP profili kopruyu aynen korur (w = 1); daha agir
    bilesim daha az TPS, daha fazla I/O ve daha yuksek maliyet verir; Db2'siz
    profil zIIP kullanmaz."""
    redp = m.get_workload("redp_light")
    assert abs(redp.cpu_weight() - 1.0) < 1e-12 and m.ziip_fraction(redp) == 0.0
    t = next(x for x in m.Z16_TIERS if x.model == "3931-718")
    assert abs(m.raw_tier_tps(t, redp) - t.pci * m.TPS_PER_PCI) < 1e-6
    names = ["redp_light", "tpcb_like", "oltp_rw", "oltp_heavy"]
    ws = [m.get_workload(n) for n in names]
    assert all(a.cpu_weight() < b.cpu_weight() for a, b in zip(ws, ws[1:]))
    assert all(a.storage_iops() < b.storage_iops() for a, b in zip(ws, ws[1:]))
    costs = [m.solve(10000, verbose=False, workload=n, data_tb=20)[2]["total"] for n in names]
    assert all(a < b for a, b in zip(costs, costs[1:]))
    # ozel bilesim: daha fazla okuma SQL -> daha yuksek agirlik ve senkron I/O
    c1 = m.WorkloadProfile("c1", 5, 1, 1, True, "", "TEST")
    c2 = m.WorkloadProfile("c2", 10, 1, 1, True, "", "TEST")
    assert c2.cpu_weight() > c1.cpu_weight() and c2.sync_io() > c1.sync_io()


def test_staff_and_ranges():
    """Personel alt-dogrusal (MIPS/FTE kapasiteyle artar), senaryolar sirali;
    aralik ciktisi low <= mid <= high ve parametreler gecici degisir."""
    small = next(t for t in m.Z16_TIERS if t.model == "3931-705")
    big = next(t for t in m.Z16_TIERS if t.model == "3931-7A0")
    for sc in ("low", "mid", "high"):
        assert big.pci / m.staff_fte(big, None, sc) > small.pci / m.staff_fte(small, None, sc)
    assert (m.staff_monthly_cost(small, None, "low") < m.staff_monthly_cost(small, None, "mid")
            < m.staff_monthly_cost(small, None, "high"))
    m1, m4 = m.TOPOLOGIES[0], m.TOPOLOGIES[3]
    assert m.staff_fte(small, m4) > m.staff_fte(small, m1)
    before = m.SW_PRICE_LEVEL_FACTOR
    rng = m.solve_range(10000, data_tb=20)
    assert m.SW_PRICE_LEVEL_FACTOR == before
    t = [rng[k]["cost"]["total"] for k in m.RANGE_LEVELS]
    assert t[0] < t[1] < t[2]
    assert abs(t[1] - m.solve(10000, verbose=False, data_tb=20)[2]["total"]) < 1e-6
    rows = m.range_tornado(10000, data_tb=20)
    assert len(rows) == len(m.RANGE_PARAMETERS)
    assert all(lo <= t[1] + 1e-6 <= hi + 2e-6 for _n, _d, lo, hi in rows)


def test_availability_rpo_rto_cbu_gdps():
    """Olay tabanli availability: daha hizli kurtarma daha az kesinti; senaryolar
    sirali. RPO/RTO kisiti topolojiyi secer. CBU DR frame'i ucuzlatir; GDPS
    kapasiteden bagimsiz sabit kalemdir ve yazilima prim eklenmez."""
    m1, m2, m3, m4 = m.TOPOLOGIES
    d = [t.annual_downtime_hours() for t in m.TOPOLOGIES]
    assert d[0] > d[1] > d[2] > d[3]
    for t in m.TOPOLOGIES:
        worst, best = t.availability_range()
        assert worst < t.availability() < best
    # CPC donanim kesintisi (ITIC) toplamin binde birinden az
    assert m.CPC_HW_DOWNTIME_SECONDS["mid"] / 3600 < 1e-3 * d[0]
    # RPO / RTO kisitlari
    pick = lambda **kw: m.solve(10000, 0.999, verbose=False, data_tb=20, **kw)[1].code
    assert pick() == "M1"
    assert pick(rpo_seconds=0) == "M2"
    assert pick(rto_minutes=60) == "M3"
    assert pick(rto_minutes=1) == "M4"
    assert pick(rpo_seconds=0, rto_minutes=60) == "M3"
    assert m.solve(10000, 0.999, verbose=False, rpo_seconds=0, rto_minutes=1) is None
    # CBU: DR frame bedeli orana bagli; 1.0 = tam ayna
    tier = next(t for t in m.Z16_TIERS if t.model == "3931-516")
    hw1 = m.monthly_cost(tier, m1)["hardware_amort"]
    with m.use_values({"DR_FRAME_COST_FRACTION": 1.0}):
        assert abs(m.monthly_cost(tier, m2)["hardware_amort"] - 2 * hw1) < 1e-6
    with m.use_values({"DR_FRAME_COST_FRACTION": 0.5}):
        assert abs(m.monthly_cost(tier, m2)["hardware_amort"] - 1.5 * hw1) < 1e-6
    # GDPS: sabit kalem, yazilim primi yok
    big = next(t for t in m.Z16_TIERS if t.model == "3931-7A0")
    assert m.monthly_cost(tier, m3)["gdps"] == m.monthly_cost(big, m3)["gdps"] > 0
    assert m.monthly_cost(tier, m1)["gdps"] == 0
    assert m.monthly_cost(tier, m4)["software"] == m.monthly_cost(tier, m1)["software"]


def test_solve_return_value_verbose():
    """solve() verbose=True iken de (kademe, topoloji, maliyet, ...) dondurmeli."""
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        r = m.solve(10000, 0.999, data_tb=20)
    q = m.solve(10000, 0.999, data_tb=20, verbose=False)
    assert isinstance(r, tuple) and r[0] is q[0] and r[1] is q[1]
    assert abs(r[2]["total"] - q[2]["total"]) < 1e-6


def test_profile_ratio_honoured():
    """Yillik profilin tepe/ortalama orani istenen degere esit olmali."""
    for preset in m.WORKLOAD_PRESETS:
        pr = m.generate_hourly_profile(preset, 10000)
        want = m.WORKLOAD_PRESETS[preset]["peak_avg_ratio"]
        assert abs(max(pr) / (sum(pr) / len(pr)) - want) < 1e-3, preset
        assert abs(sum(pr) / len(pr) - 10000) < 1e-6
    for ratio, days in [(1.1, 5), (1.8, 0), (4.0, 30)]:
        pr = m.generate_hourly_profile(None, 5000, ratio, days)
        assert abs(max(pr) / (sum(pr) / len(pr)) - ratio) < 1e-3, (ratio, days)
        assert min(pr) >= 0
    try:
        m.generate_hourly_profile(None, 5000, 5.0, 0)
        raise AssertionError("ulasilamaz oran hata vermeliydi")
    except ValueError:
        pass


def test_static_equals_yearly_on_flat_load():
    """Sabit yukte yillik Permanent strateji = 12 x statik aylik maliyet."""
    flat = [10000.0] * 8760
    r = m.solve(10000, 0.999, verbose=False, data_tb=20)
    tier, topo, cost = r[0], r[1], r[2]
    sim = m.simulate_yearly(flat, tier, topo, strategy="permanent",
                            storage_monthly=cost["storage"],
                            staff_monthly=cost["staff"])
    assert abs(sim["yearly_total"] - 12 * cost["total"]) / (12 * cost["total"]) < 1e-3


def test_ziip_sized_for_temporary_capacity():
    """CoD/corridor gunlerinde de zIIP payi karsilanmali: gecici kapasiteli
    strateji, ayni base'in kalici maliyetinden fazla zIIP donanimi tasir."""
    prof = m.generate_hourly_profile("batch_heavy", 10000)
    base = next(t for t in m.Z16_TIERS if t.model == "3931-522")
    m1 = m.TOPOLOGIES[0]
    sim = m.simulate_yearly(prof, base, m1, strategy="base_cod")
    if sim is not None and sim["peak_tier"] is not None:
        perm_other = 12 * (lambda c: c["hardware_amort"] + c["maintenance"] + c["energy"])(
            m.monthly_cost(base, m1))
        assert sim["yearly_other"] >= perm_other - 1e-6
        if m.ziip_engines(sim["peak_tier"]) > m.ziip_engines(base):
            assert sim["yearly_other"] > perm_other


def test_cli_edge_cases():
    """CLI: gecersiz girdiler hata vermeli, uc durumlar cokmemeli."""
    import subprocess, sys, os
    here = os.path.dirname(os.path.abspath(__file__))
    run = lambda *a: subprocess.run([sys.executable, os.path.join(here, "mainframe_model.py"), *a],
                                    capture_output=True, text=True)
    assert run("--tps", "0").returncode != 0
    assert run("--tps", "-5", "--range").returncode != 0
    assert run("--yearly", "--avg-tps", "0").returncode != 0
    assert run("--tps", "1000", "--availability", "1.5").returncode != 0
    assert run("--tps", "1000", "--sql-reads", "0", "--sql-writes", "0").returncode == 0
    custom = m.WorkloadProfile("c", 0, 0, 1, False, "", "")
    assert m.ziip_fraction(custom) == 0
    with_db2 = m.WorkloadProfile("c", 2, 1, 1, True, "", "")
    assert m.ziip_fraction(with_db2) > 0
    try:
        with m.use_values({"SW_PRICE_LEVEL_FACTOR": 9.0, "NO_SUCH_PARAM": 1}):
            pass
    except KeyError:
        pass
    assert m.SW_PRICE_LEVEL_FACTOR == 1.0


def test_io_delay_uses_profile_mix():
    """D_io, profilin okuma ve yazma I/O'larini kendi servis sureleriyle tartar."""
    m1, m2 = m.TOPOLOGIES[0], m.TOPOLOGIES[1]
    for name in ("redp_light", "tpcb_like", "oltp_rw"):
        w = m.get_workload(name)
        expect = (w.sync_read_io() * m.io_read_time_seconds()
                  + w.sync_write_io() * m.io_write_time_seconds(m2))
        assert abs(m.io_delay_seconds(name, m2) - expect) < 1e-12
    # REDP'nin senkron I/O'su yazmadir: senkron replikasyon tamamen eklenir
    redp = m.get_workload("redp_light")
    assert redp.sync_read_io() == 0
    assert m.io_delay_seconds("redp_light", m2) > m.io_delay_seconds("redp_light", m1)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK  {name}")
