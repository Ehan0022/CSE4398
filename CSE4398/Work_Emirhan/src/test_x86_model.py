"""
x86_model.py icin tutarlilik testleri (sadece standard library).
Calistirma:  python test_x86_model.py
Mainframe testleriyle ayni yapida: her test bir kopru kuralini (docs/kopruler_v1.md)
ya da x86'nin kendi calisma bicimine ait bir ozelligi sinar.
"""
import math

import common_model as cm
import mainframe_model as mf
import x86_model as x

ZERO_GROWTH = {"NPV_TPS_GROWTH": 0.0, "DEFAULT_DATA_GROWTH": 0.0, "SW_PRICE_ESCALATION": 0.0,
               "HW_SERVICE_ESCALATION": 0.0, "WAGE_ESCALATION": 0.0, "ENERGY_ESCALATION": 0.0}
PG = [s for s in x.STACKS if s.db == "postgresql"]
ORA = [s for s in x.STACKS if s.db == "oracle"]
VS_VM_PG = x.STACKS[0]


def _total(r):
    return r["total"] if r else float("inf")


def _topo(code):
    return x.get_topology(code)


# ------------------------------------------------------------------------------
# KB-01 / KB-03 / KB-04: is yuku ve kapasite koprusu
# ------------------------------------------------------------------------------
def test_bridge_anchor_and_cross_check():
    """Capa 519.069 QPS / 20 / 48 / 5,94 = 91 TPS/SPECint/cekirdek; R760 ~893
    TPS/cekirdek; KB-04 kontrolu F karariyla 1,52-1,60 cekirdek/CP araliginda."""
    assert abs(x.X86_TPS_PER_SPECINT_CORE - 91.0) < 0.5
    bare = x.X86_TPS_PER_SPECINT_CORE * x.X86_SPECINT_PER_CORE
    assert abs(bare - 893) < 2
    cp = mf.ZIIP_ENGINE_PCI * mf.TPS_PER_PCI / mf.get_workload("oltp_rw").cpu_weight()
    assert 1.52 <= cp / bare <= 1.60, cp / bare
    # 64 cekirdekte S(n) < 1, 16 cekirdekte > 1 (capa 48 cekirdek)
    assert x.scaling_factor(64) < 1.0 < x.scaling_factor(16)


def test_workload_weights():
    """oltp_rw capanin kendisidir (agirlik 1, 20 ifade); agir profil daha pahali,
    TPC-B benzeri daha ucuz; redp_light (SQL'siz CICS islemi) x86'da yoktur."""
    rw = x.get_workload("oltp_rw")
    assert rw.statements() == 20 and abs(rw.rel_weight() - 1.0) < 1e-12
    assert x.get_workload("oltp_heavy").rel_weight() > 1.0 > x.get_workload("tpcb_like").rel_weight()
    try:
        x.get_workload("redp_light")
        assert False
    except ValueError:
        pass
    # RANGE_READ_WEIGHT ortak: x86 goreli agirligi aralik okumasi olan profilde etkiler
    heavy = x.X86Workload("t", 10, 8, 4, 1)
    base = heavy.rel_weight()
    with x.use_values({"RANGE_READ_WEIGHT": 3.9}):
        assert heavy.rel_weight() > base
        assert cm.RANGE_READ_WEIGHT == 3.9
    # ayni bilesimin mainframe profili ayni SQL sayilarini tasir
    mp = rw.mainframe_profile()
    assert (mp.point_reads, mp.range_reads, mp.writes, mp.commits) == (10, 4, 4, 1)


def test_scaling_corners_direction_consistent():
    """B_X86 koseleri dugum boyutundan bagimsiz olarak yon tutarli: low >= mid >= high."""
    for n in (16, 32, 48, 64, 96, 128):
        vals = []
        for lv in ("low", "mid", "high"):
            with x.use_values({"X86_SCALING_LEVEL": lv}):
                vals.append(x.scaling_factor(n))
        assert vals[0] >= vals[1] - 1e-12 and vals[1] >= vals[2] - 1e-12, (n, vals)


def test_stack_overheads():
    """Sanallastirma ve konteyner ek yuku cekirdek verimini dusurur; OpenShift
    Virtualization ek yuku vSphere'den buyuk; Oracle carpani verimi olcekler."""
    sku = x.X86_CATALOG[2]
    by = {s.code: x.tps_per_core(sku, s) for s in x.STACKS}
    vs_vm = by["vSphere / VM / PostgreSQL+Patroni"]
    assert by["vSphere / K8s / PostgreSQL+Patroni"] < vs_vm
    assert by["OpenShift Virt / VM / PostgreSQL+Patroni"] < vs_vm
    with x.use_values({"ORACLE_THROUGHPUT_FACTOR": 1.3}):
        assert x.tps_per_core(sku, ORA[0]) > 1.29 * x.tps_per_core(sku, VS_VM_PG)
    assert len(x.STACKS) == 8 and all(s.placement == "vm" for s in ORA)


# ------------------------------------------------------------------------------
# KB-05 / KB-06: kullanim tavani, latency, olcekleme
# ------------------------------------------------------------------------------
def test_ceiling_rule_and_latency():
    """rho <= tavan; siki latency hicbir zaman ucuz degil; sabit gecikmenin
    altindaki hedef infeasible; tavan yukseldikce maliyet artmaz."""
    for tps in (2000, 10000, 30000):
        r = x.solve(tps, verbose=False)
        assert r["rho"] <= x.X86_UTIL_CEILING + 1e-12
        prev = _total(r)
        for lat in (100, 50, 20, 10, 6):
            c = _total(x.solve(tps, latency_ms=lat, verbose=False))
            assert c >= prev - 1e-6, (tps, lat)
            prev = c
    d = x.fixed_delay_s(_topo("X1"), "postgresql", "oltp_rw") * 1000
    assert x.solve(10000, latency_ms=d * 0.95, stacks=PG, topologies=[_topo("X1")],
                   verbose=False) is None
    costs = []
    for ceil in (0.5, 0.7, 0.9):
        with x.use_values({"X86_UTIL_CEILING": ceil}):
            costs.append(_total(x.solve(30000, verbose=False)))
    assert costs[0] >= costs[1] >= costs[2]
    # sakli yordam ag terimini ifade sayisindan 1 gidis-donuse indirir
    with x.use_values({"X86_STORED_PROCEDURES": True}):
        assert abs(x.net_delay_s("oltp_rw") * 1000 - x.X86_NET_RTT_MS["mid"]) < 1e-9
    # uzak senkron kopya (X3) commit basina mesafe ekler
    assert (x.repl_delay_s(_topo("X3"), "postgresql", "oltp_rw")
            > x.repl_delay_s(_topo("X1"), "postgresql", "oltp_rw"))


def test_patroni_single_writer_ceiling():
    """Patroni tek yazicidir: kapasite yalnizca birincil dugum; ana katalogda
    ~36K TPS'te tavan, ekstrapolasyonla yukselir; Oracle RAC tavanin ustune cikar."""
    sku = x.X86_CATALOG[-1]
    assert x.cluster_raw_tps(sku, VS_VM_PG, 5) == x.node_raw_tps(sku, VS_VM_PG)
    assert x.solve(40000, stacks=PG, verbose=False) is None
    with x.use_values({"ALLOW_EXTRAPOLATION": True}):
        assert x.solve(40000, stacks=PG, verbose=False) is not None
    r = x.solve(60000, verbose=False)
    assert r is not None and r["stack"].db == "oracle"
    # RAC: k dugumun ham verimi = dugum x [1 + (k-1) x verim]
    raw = x.node_raw_tps(sku, ORA[0])
    assert abs(x.cluster_raw_tps(sku, ORA[0], 4) - raw * (1 + 3 * x.RAC_SCALING_EFFICIENCY)) < 1e-6
    # N+1: k dugumlu RAC'ta k-1 dugum butun yuku tasir
    assert x._db_capacity_nodes("oracle", _topo("X1"), 4) == 3


def test_cost_nondecreasing_in_tps():
    prev = 0.0
    for tps in (500, 1000, 3000, 10000, 20000, 35000, 50000, 80000, 120000):
        c = _total(x.solve(tps, verbose=False))
        assert c >= prev - 1e-6, tps
        prev = c


# ------------------------------------------------------------------------------
# KB-07 / KB-08: availability ve topoloji
# ------------------------------------------------------------------------------
def test_topologies_and_availability():
    """X4 PostgreSQL icin infeasible (K4); Patroni X2 standby kume asenkrondur
    (RPO > 0, KB-08 duzeltmesi); RPO 0 isteyen PostgreSQL X3'e gider; availability
    X1 < X2 < X3; saha olayi kotulesince availability duser."""
    assert not _topo("X4").supports("postgresql") and _topo("X4").supports("oracle")
    assert _topo("X2").rpo_seconds("postgresql") > 0
    assert _topo("X2").rpo_seconds("oracle") == 0
    r = x.solve(10000, rpo_seconds=0, stacks=PG, verbose=False)
    assert r["topology"].code == "X3"
    a = [_topo(c).availability("postgresql") for c in ("X1", "X2", "X3")]
    assert a[0] < a[1] < a[2]
    assert _topo("X4").availability("oracle", 2) > _topo("X3").availability("oracle", 2)
    base = _topo("X1").availability("postgresql")
    with x.use_values({"SITE_EVENT_LEVEL": "high"}):
        assert _topo("X1").availability("postgresql") < base
    lo, hi = _topo("X3").availability_range("postgresql")
    assert lo < _topo("X3").availability("postgresql") < hi
    # X2 elle gecis: ortak karar suresi + teknik gecis
    assert _topo("X2").recovery_minutes() > x.X86_RECOVERY_TECH_MINUTES["X2"]["mid"]
    # RAC'ta her hizmet dugumu kesintiye yol acar; Patroni'de yalnizca birincil
    assert _topo("X1").interrupting_nodes("oracle", 4) == 4
    assert _topo("X1").interrupting_nodes("postgresql", 1) == 1
    # yuksek availability hedefi daha pahali
    assert _total(x.solve(10000, 0.99999, verbose=False)) > _total(x.solve(10000, 0.999, verbose=False))


# ------------------------------------------------------------------------------
# KB-11: lisans tabani
# ------------------------------------------------------------------------------
def test_oracle_license_math():
    """Islemci = cekirdek x 0,5 (yukari yuvarlanir); EE + Diagnostics + Tuning
    (+ RAC); X3'te ADG, X4'te GoldenGate (ADG'yi icerir); net = liste x (1 - indirim)."""
    p = x.ORACLE_PRICES
    lst = 8 * (p["ee"] + p["diagnostics"] + p["tuning"] + p["rac"])
    assert abs(x.oracle_license_net(16, _topo("X1"), True) - lst * (1 - x.ORACLE_DISCOUNT)) < 1e-6
    assert "adg" in x.oracle_options(_topo("X3"), True)
    o4 = x.oracle_options(_topo("X4"), True)
    assert "goldengate" in o4 and "adg" not in o4
    assert "rac" not in x.oracle_options(_topo("X2"), False)
    assert x.oracle_license_net(15, _topo("X1"), False) == x.oracle_license_net(16, _topo("X1"), False)


def test_platform_subscriptions():
    """vSphere: CPU basina en az 16, siparis basina en az 72 cekirdek; OVE dugum
    basina; OpenShift sanal dugumde 2 cekirdek basina, RHEL dahil."""
    small = x.X86_CATALOG[0]          # 2 x 8c -> 32 cekirdek lisanslanir
    s = x.platform_subscriptions(VS_VM_PG, [{"role": "db", "site": "A", "sku": small, "n": 1}])
    assert abs(s[0]["hypervisor"] - 72 * x.VSPHERE_USD_PER_CORE_YEAR) < 1e-6
    s = x.platform_subscriptions(VS_VM_PG, [{"role": "db", "site": "A", "sku": small, "n": 3}])
    assert abs(s[0]["hypervisor"] - 96 * x.VSPHERE_USD_PER_CORE_YEAR) < 1e-6
    assert s[0]["os"] == 3 * x.RHEL_VDC_USD_PER_NODE_YEAR and s[0]["orchestration"] == 0
    ocp = next(st for st in x.STACKS if st.placement == "openshift" and st.hypervisor == "vsphere")
    sku = x.X86_CATALOG[2]
    s = x.platform_subscriptions(ocp, [{"role": "db", "site": "A", "sku": sku, "n": 2}])
    assert s[0]["os"] == 0
    assert s[0]["orchestration"] == 2 * (sku.cores // 2) * x.OCP_USD_PER_COREPAIR_YEAR
    ove = next(st for st in x.STACKS if st.hypervisor == "ocpv" and st.placement == "vm")
    s = x.platform_subscriptions(ove, [{"role": "witness", "site": "C", "sku": sku, "n": 1}])
    assert s[0]["hypervisor"] == x.OVE_USD_PER_NODE_YEAR


def test_dr_sites_fully_licensed():
    """CoD/CBU karsiligi yok: DR sitesindeki Oracle dugumleri tam lisanslanir."""
    sku = x.X86_CATALOG[1]
    r1 = x.evaluate(20000, ORA[0], _topo("X1"), sku, 3)
    r3 = x.evaluate(20000, ORA[0], _topo("X3"), sku, 3)
    assert r1 and r3
    lic = lambda r, site: sum(g["oracle_net"] for g in r["groups"] if g["site"] == site)
    assert lic(r3, "B") >= lic(r1, "A") > 0
    assert r3["dr_share"] > 0.0 == r1["dr_share"]


# ------------------------------------------------------------------------------
# KB-12: uygulama katmani
# ------------------------------------------------------------------------------
def test_app_tier():
    """Uygulama cekirdegi = DB mesgul cekirdegi x TM / (1 - TM); TM payi F ile
    ~%7,8; tavan bir kez uygulanir; sitede en az 2 host."""
    tm = mf.get_workload("oltp_rw").tm_share()
    assert 0.07 < tm < 0.09, tm
    assert abs(x.app_core_need(10.0, "oltp_rw") - 10.0 * tm / (1 - tm)) < 1e-9
    sku, n, need = x.app_hosts(10.0, VS_VM_PG, "oltp_rw")
    assert n >= x.X86_APP_MIN_HOSTS and n * sku.cores * x.X86_UTIL_CEILING >= need
    big = x.app_hosts(200.0, VS_VM_PG, "oltp_rw")
    assert (big[1] - 1) * big[0].cores * x.X86_UTIL_CEILING >= big[2]   # N+1
    r = x.solve(10000, verbose=False)
    assert 0 < r["app_share"] < 0.05


# ------------------------------------------------------------------------------
# KB-09 / KB-10: storage ve yedek
# ------------------------------------------------------------------------------
def test_storage_rules():
    """Patroni yerel NVMe x dugum sayisi; 24 yuvaya sigmayan veri infeasible
    (Oracle AFA ile cozulur); RAC'ta birincil dizide anlik kopya rezervi."""
    p = x.storage_plan(10000, "oltp_rw", _topo("X1"), "postgresql", 1, 20)
    assert len(p["sites"]) == 1 and p["sites"]["A"]["raw_tb"] >= 3 * x.pg_node_raw_tb(20)
    p3 = x.storage_plan(10000, "oltp_rw", _topo("X3"), "postgresql", 1, 20)
    assert abs(p3["hw_capex"] / p["hw_capex"] - 4 / 3) < 1e-9          # 2 + 2 dugum vs 3
    assert x.storage_plan(10000, "oltp_rw", _topo("X1"), "postgresql", 1, 900) is None
    assert x.solve(10000, data_tb=900, stacks=PG, verbose=False) is None
    big = x.solve(10000, data_tb=900, verbose=False)
    assert big is not None and big["stack"].db == "oracle"
    o = x.storage_plan(10000, "oltp_rw", _topo("X3"), "oracle", 2, 200)
    assert o["sites"]["A"]["raw_tb"] > o["sites"]["B"]["raw_tb"]
    # fiyat sozlesmesi: etkin TB teklifi ham TB'a geri cevrilir
    per_raw = cm.price_per_raw_tb(x.AFA_LIST_USD_PER_EFF_TB, "effective", x.AFA_RAID_USABLE,
                                  x.AFA_DATA_REDUCTION)
    assert abs(per_raw - x.AFA_LIST_USD_PER_EFF_TB * x.AFA_RAID_USABLE * x.AFA_DATA_REDUCTION) < 1e-9


def test_backup_rules():
    """WAL full-page write carpani PostgreSQL log hacmini buyutur; hedef
    secimi ortak fiyat fonksiyonlariyla; X1'de geri yukleme RTO'nun yarisina sigmali."""
    pg = x.backup_plan(10000, "oltp_rw", _topo("X1"), "postgresql", 20)
    ora = x.backup_plan(10000, "oltp_rw", _topo("X1"), "oracle", 20)
    assert pg["log_tb"] > ora["log_tb"]
    assert set(pg["alternatives"]) == {"cos_onprem", "aws_s3"}
    assert pg["restore_hours"] <= _topo("X1").rto_minutes / 60 * cm.BACKUP_RESTORE_RTO_FRACTION
    with x.use_values({"X86_BACKUP_MAX_MB_S": 10.0}):
        assert x.backup_plan(10000, "oltp_rw", _topo("X1"), "postgresql", 20) is None


# ------------------------------------------------------------------------------
# KB-13 / KB-14: personel ve uretim disi
# ------------------------------------------------------------------------------
def test_staff_neutral_and_breakeven():
    """Oran 1'de x86 personeli ayni TPS ve ayni topoloji duzeyinde mainframe ile
    ayni; basabas orani x86 toplamini mainframe'e esitler; personel haric
    gorunum ve duyarlilik oranlari hesaplanir."""
    m = mf.solve(10000, verbose=False)
    xr = x.solve(10000, verbose=False)
    assert m[1].code == "M1" and xr["topology"].code == "X1"
    assert abs(m[2]["staff"] - xr["staff"]) < 1e-6
    c = x.compare(10000)
    be = c["breakeven_ratio"]
    with x.use_values({"STAFF_RATIO_X86": be}):
        t = x.solve(10000, verbose=False)["total"]
    assert abs(t - c["mf_total"]) / c["mf_total"] < 1e-3
    assert c["sensitivity"][2.0] > c["sensitivity"][1.25] > c["x86_total"]
    assert c["unconsolidated"]["total"] >= c["x86_total"]
    assert c["nonprod_stress"] >= c["x86_total"]
    with x.use_values({"STAFF_RATIO_X86": 2.0}):
        assert abs(x.staff_fte(10000, "oltp_rw", _topo("X1"))
                   - 2 * cm.staff_fte(mf.staff_pci_equivalent(10000, "oltp_rw"), "X1")) < 1e-9


def test_paired_comparison_scenarios():
    """Eslestirilmis senaryolar yon tutarli: x86 lehine senaryoda x86 ucuzlar,
    mainframe pahalilanir (ve tersi); ortak parametreler iki tarafta ayni;
    kopru agirliklari referans tabanda personeli platforma ozgu CPU
    belirsizliginden ayirir."""
    res = x.compare_range(10000)
    xs = [res[k]["x86_total"] for k in ("x86_lehine", "orta", "mainframe_lehine")]
    ms = [res[k]["mf_total"] for k in ("x86_lehine", "orta", "mainframe_lehine")]
    assert xs[0] <= xs[1] <= xs[2] and ms[0] >= ms[1] >= ms[2]
    assert res["ortak_low"]["x86_total"] < xs[1] < res["ortak_high"]["x86_total"]
    v = x.paired_values("low", "high", "mid")
    assert v["STAFF_SCENARIO"] == "mid" and v["X86_UTIL_CEILING"] == 0.90
    assert v["CPU_US_PER_SQL_READ"] == 60.0
    base = mf.staff_pci_equivalent(10000)
    with x.use_values({"CPU_US_PER_SQL_READ": 60.0}):
        assert mf.staff_pci_equivalent(10000) > base
        with x.use_values({"CROSS_BRIDGE_WEIGHTS": "reference"}):
            assert abs(mf.staff_pci_equivalent(10000) - base) < 1e-9
        assert mf.CPU_US_PER_SQL_READ == 60.0
    assert mf.CROSS_BRIDGE_WEIGHTS == "current"


def test_nonprod_x86():
    """Uretim disi: 0'da sifir, carpanla dogrusal; personel ve yedegi etkilemez."""
    out = {}
    for f in (0.0, 0.5, 1.0):
        with x.use_values({"NONPROD_FACTOR_X86": f}):
            out[f] = x.evaluate(10000, VS_VM_PG, _topo("X3"), x.X86_CATALOG[0])
    assert out[0.0]["nonprod"] == 0 and out[0.5]["nonprod"] > 0
    assert abs(out[1.0]["nonprod"] - 2 * out[0.5]["nonprod"]) < 1e-6
    for k in ("staff", "backup", "software"):
        assert out[1.0][k] == out[0.0][k]


# ------------------------------------------------------------------------------
# KB-15 / KB-16 / KB-18: fiyat donemi, NPV, aralik
# ------------------------------------------------------------------------------
def test_price_epoch_x86():
    """2026-Q3 bilesen soku sunucuyu ve NVMe'yi pahalilastirir; ana senaryo 2025-mid."""
    sku = x.X86_CATALOG[-1]
    base = x.node_net_capex(sku)
    with x.use_values({"PRICE_EPOCH": "2026-Q3"}):
        assert x.node_net_capex(sku) > base
        shock = _total(x.solve(10000, verbose=False))
    assert shock > _total(x.solve(10000, verbose=False))


def test_range_ordering():
    """low <= mid <= high (statik ve NPV); tornado her parametre icin iki uc verir."""
    for tps in (10000, 50000):
        r = x.solve_range(tps)
        assert _total(r["low"]) <= _total(r["mid"]) <= _total(r["high"]), tps
    n = x.solve_npv_range(10000)
    assert n["low"]["npv"] <= n["mid"]["npv"] <= n["high"]["npv"]
    rows = x.range_tornado(10000)
    assert len(rows) == len(x.X86_RANGE_PARAMETERS)
    assert rows[0][0] in ("STAFF_SCENARIO", "WAGE_LEVEL")


def test_npv_consistency_and_direction():
    """r = 0, buyume 0, artis 0 iken NPV = 60 x statik aylik toplam (her topoloji
    ve iki veritabani); yuksek iskonto NPV'yi dusurur; dugum yalnizca buyur."""
    with x.use_values(ZERO_GROWTH):
        for st, tps in ((VS_VM_PG, 10000), (ORA[0], 50000)):
            for code in ("X1", "X3"):
                topo = _topo(code)
                s = x.solve(tps, stacks=[st], topologies=[topo], verbose=False, data_tb=20)
                n = x._npv_path(tps, st, topo, "oltp_rw", None, 99, 20, None, 0.999, None, None,
                                0.0, 5, 0.0)
                assert abs(n["npv"] - 60 * s["total"]) / n["npv"] < 1e-9, (st, code)
        s = x.solve(10000, verbose=False, data_tb=20)
        n = x.solve_npv(10000, data_tb=20, discount_rate=0.0)
        assert abs(n["npv"] - 60 * s["total"]) / n["npv"] < 1e-9
    a = x.solve_npv(10000, discount_rate=0.05)
    b = x.solve_npv(10000, discount_rate=0.10)
    assert b["npv"] < a["npv"]
    g = x.solve_npv(10000, tps_growth=0.15)
    cores = [r["config"]["sku"].cores for r in g["years"]]
    assert cores == sorted(cores) and cores[-1] > cores[0]
    assert all(r["capex"] >= 0 for r in g["years"])
    gr = x.solve_npv(50000, tps_growth=0.15)
    ks = [r["config"]["k"] for r in gr["years"]]
    assert ks == sorted(ks)
    # levelized ~ statik (buyume ve iskontonun birlikte etkisi kucuk)
    assert abs(x.solve_npv(10000)["levelized_per_tps_month"] / x.solve(10000, verbose=False)["total"]
               * 10000 - 1) < 0.1


def test_yearly_peak_sizing():
    """CoD karsiligi yok: yillik maliyet tepe yuke gore kurulu kapasitenin 12 ayi."""
    y = x.solve_yearly("retail_bursty", 10000, verbose=False)
    st = x.solve(y["peak_tps"], avg_tps=y["avg_tps"], verbose=False)
    assert abs(y["yearly_total"] - 12 * st["total"]) < 1e-6
    assert y["peak_tps"] > y["avg_tps"]


# ------------------------------------------------------------------------------
# Ortak modul ve fiyat modlari
# ------------------------------------------------------------------------------
def test_shared_parameters_single_owner():
    """x86 modulu ortak bir adi yeniden tanimlamaz; use_values degisikligi
    sahibinde yapar ve geri alir."""
    X = {k for k in vars(x) if k.isupper()}
    assert not (X & {k for k in vars(cm) if k.isupper()})
    assert X & {k for k in vars(mf) if k.isupper()} <= {"DEFAULT_WORKLOAD", "NPV_ITEM_LABELS",
                                                          "_PARAM_MODULES"}
    with x.use_values({"SITE_EVENT_LEVEL": "high", "X86_UTIL_CEILING": 0.5}):
        assert cm.SITE_EVENT_LEVEL == "high" and x.X86_UTIL_CEILING == 0.5
    assert cm.SITE_EVENT_LEVEL == "mid" and x.X86_UTIL_CEILING == 0.70
    assert x.NPV_TPS_GROWTH is cm.NPV_TPS_GROWTH


def test_price_file_mode_x86():
    """Kullanici fiyat dosyasi x86 fiyatlarini kismi gecersiz kilar ve aralikta sabitler."""
    mods = x._PARAM_MODULES
    names = ("VSPHERE_USD_PER_CORE_YEAR", "ORACLE_DISCOUNT")
    before = {n: getattr(x, n) for n in names}
    base = x.solve(10000, verbose=False)["total"]
    try:
        cm.apply_user_prices({"VSPHERE_USD_PER_CORE_YEAR": 350.0}, mods)
        assert "VSPHERE_USD_PER_CORE_YEAR" in cm.PINNED
        assert x.solve(10000, verbose=False)["total"] > base
        assert "VSPHERE_USD_PER_CORE_YEAR" not in x.scenario_values_for("high", x.X86_RANGE_PARAMETERS)
        assert "VSPHERE_USD_PER_CORE_YEAR" in cm.current_prices(mods)
    finally:
        cm.reset_user_prices(before, mods)
    assert not cm.PINNED and abs(x.solve(10000, verbose=False)["total"] - base) < 1e-6


def test_cli_runs():
    """CLI bayraklari calisir; main() tek kosuluk global ayarlari (donem,
    ekstrapolasyon) degistirdigi icin her kosudan sonra geri alinir."""
    import contextlib, io
    for argv, code in ((["--tps", "10000"], 0), (["--tps", "10000", "--compare"], 0),
                       (["--calibration"], 0), (["--tps", "10000", "--db", "oracle"], 0),
                       (["--tps", "20000", "--npv"], 0), (["--yearly", "--preset", "steady_oltp"], 0),
                       (["--list-prices"], 0), (["--price-vintages"], 0),
                       (["--tps", "10000", "--price-epoch", "2026-Q3", "--allow-extrapolation"], 0),
                       (["--tps", "5000", "--sql-reads", "5", "--sql-writes", "2"], 0),
                       (["--tps", "1000000"], 1)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert x.main(argv) == code, argv
        finally:
            cm.PRICE_EPOCH = "2025-mid"
            x.ALLOW_EXTRAPOLATION = False
            x.STAFF_RATIO_X86 = 1.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK  {name}")


# ------------------------------------------------------------------------------
# Degerlendirme #10: availability esitligi, platform kesintisi, destek kurali
# ------------------------------------------------------------------------------
def test_m3_x3_recovery_parity():
    """M3 cok-siteli GDPS Metro olarak X3 ile ayni kurtarma ve planli kesinti araligini alir."""
    for lv in ("low", "mid", "high"):
        assert mf.RECOVERY_MINUTES["M3"][lv] == x.X86_RECOVERY_TECH_MINUTES["X3"][lv]
        assert mf.PLANNED_OUTAGE_MINUTES["M3"][lv] == x.X86_PLANNED_OUTAGE_MINUTES["multi"][lv]


def test_platform_downtime_common_rule():
    """Ortak formul: tek CPC'de maskelenmez; kumede u, aktif-aktifte u^2; u artinca
    availability iki tarafta da duser."""
    assert cm.platform_downtime_hours(1.0, 1, clustered=False) == 1.0
    u = cm.PLATFORM_UNMASKED_SHARE
    assert abs(cm.platform_downtime_hours(1.0, 2, True) - 2 * u) < 1e-12
    assert abs(cm.platform_downtime_hours(1.0, 1, True, layers=2) - u * u) < 1e-12
    m1 = next(t for t in mf.TOPOLOGIES if t.code == "M1")
    base_x3, base_m1 = _topo("X3").availability("postgresql"), m1.availability()
    with x.use_values({"PLATFORM_UNMASKED_SHARE": 0.20}):
        assert _topo("X3").availability("postgresql") < base_x3
        assert m1.availability() == base_m1          # tek CPC: u'dan bagimsiz
    # ITIC: x86 sunucu kesintisi z16 CPC'sinden buyuk (ayni kaynak)
    assert x.X86_ITIC_DOWNTIME_MINUTES["mid"] * 60 > mf.CPC_HW_DOWNTIME_SECONDS["mid"]


def test_pg_support_tiers_and_unsupported_penalty():
    assert x.pg_support_rate(0.999) == x.PG_SUPPORT_USD_PER_CORE_YEAR
    assert x.pg_support_rate(0.9999) == 1600.0
    assert x.pg_support_rate(0.999, rpo_seconds=0) == 1600.0
    assert x.pg_support_rate(0.99999) == 2400.0
    with x.use_values({"PG_SUPPORT_USD_PER_CORE_YEAR": 0.0}):
        assert x.pg_support_rate(0.999) == 0.0           # desteksiz yalniz dusuk hedefte
        assert x.pg_support_rate(0.9999) == 1600.0
        r = x.solve(10000, 0.999, stacks=PG, verbose=False)
        assert r["pg_support_rate"] == 0.0
    t = _topo("X1")
    assert t.availability("postgresql", supported=False) < t.availability("postgresql")
    assert t.availability("oracle", 2, supported=False) == t.availability("oracle", 2)
    hi = x.solve(10000, 0.99995, rpo_seconds=0, stacks=PG, verbose=False)
    assert hi["pg_support_rate"] == 1600.0


def test_staff_input_includes_ziip_work():
    """Ortak personel egrisinin girdisi zIIP payindan bagimsizdir."""
    base = mf.staff_pci_equivalent(10000)
    with x.use_values({"ZIIP_OFFLOAD_FRACTION": 0.40, "CROSS_BRIDGE_WEIGHTS": "current"}):
        assert abs(mf.staff_pci_equivalent(10000) - base) < 1e-9


def test_five_nines_with_rpo0_is_mainframe_only():
    """Ana senaryoda %99,999 + RPO 0: x86 kurulamaz, mainframe M3 kurulur; RPO
    serbestken x86 Oracle X4 (GoldenGate, RPO 5 sn) ile kurulur."""
    o = x.compare(10000, availability=0.99999, rpo_seconds=0)
    assert o["x86"] is None and o["mainframe"] is not None
    assert o["mainframe"][1].code == "M3"
    o2 = x.compare(10000, availability=0.99999)
    assert o2["x86"]["topology"].code == "X4" and o2["x86"]["stack"].db == "oracle"
