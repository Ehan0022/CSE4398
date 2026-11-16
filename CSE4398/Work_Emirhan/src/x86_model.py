"""
================================================================================
CLUSTERED x86 (SCALE-OUT) MODEL — on-prem kumelenmis x86 OLTP yigini
================================================================================
Bu modul, verilen bir is yuku + SLA girdisi icin, onu saglayan minimum maliyetli
on-prem x86 yapilandirmasini (yigin x topoloji x sunucu x dugum sayisi) bulur.
Mainframe modeliyle (mainframe_model.py) ayni disiplinde kuruludur ve iki
platformun paylastigi her kural common_model.py'den okunur.
Teknik dokumantasyon: docs/x86_model_dokumantasyonu_v1.md.
Kopruler (karsilastirmanin arayuzleri): docs/kopruler_v1.md (KB-01 ... KB-18).

Akis:
  1. Is yuku: islem bilesimi iki tarafta ayni (common_model.WORKLOAD_MIXES,
     KB-01). x86 capasi sysbench oltp_read_write'in kendisidir; diger
     profiller ifade agirliklariyla olceklenir.
  2. Kapasite koprusu (KB-03): cekirdek basina TPS =
     X86_TPS_PER_SPECINT_CORE x SPECrate2017_int_base/cekirdek x S(n)
     x (1 - sanallastirma) x (1 - konteyner) x (Oracle carpani).
  3. Kullanim tavani ve latency (KB-05): rho = min(rho_latency, X86_UTIL_CEILING);
     cekirdek basina bagimsiz M/M/1 (mainframe ile ayni kuyruk ailesi) +
     D_ag + D_io + D_repl.
  4. Yigin (v4 §4.8, K7): hipervizor {vSphere, OpenShift Virtualization} x
     yerlesim {VM, VM icinde vanilla Kubernetes, VM icinde OpenShift} x
     veritabani {PostgreSQL + Patroni, Oracle}. Oracle yalnizca VM'de.
  5. Topoloji X1-X4 (KB-08): Oracle MAA Silver/Gold/Platinum ve Patroni
     karsiliklari; X4 PostgreSQL icin infeasible (K4).
  6. Olcekleme (KB-06): Patroni tek yazicidir (birincil dugum tum yuku tasir);
     Oracle RAC dugum ekleyerek olceklenir (N+1).
  7. Storage (KB-09, K1): Patroni -> yerel NVMe x dugum sayisi; RAC -> site
     basina paylasimli all-flash SAN. Fiyat sozlesmesi ortak (ham TB).
  8. Maliyet: sunucu (bilesen fiyati, PRICE_EPOCH), lisans/abonelik (kurulu
     cekirdek ya da dugum; KB-11), uygulama katmani (KB-12), ortak personel
     egrisi x STAFF_RATIO_X86 (KB-13), uretim disi (KB-14), yedek (KB-10).
  9. --range: low/mid/high koseler + tornado; --npv: 5 yillik nakit akisi;
     --compare: mainframe ile ayni girdide karsilastirma, basabas personel
     orani ve personel haric TCO (KB-18).

KAPSAM DISI: bare-metal Kubernetes (v4 §4.8: "her zaman bir sanallastirma
  katmani var"), Citus / sharding (K3), Windows, MQ, PUE / raf / SAN fabrigi
  (KB-17), EDB Postgres Distributed (K4).

KAYNAK ETIKETLERI (tam liste: docs/x86_model_dokumantasyonu_v1.md §12):
  [VONNG-PERF]     = Vonng, "How Powerful is PostgreSQL Really?", c5d.metal sysbench
  [SPEC-8270] [SPEC-R760] [SPEC-DL380G12] = SPEC CPU2017 sonuc sayfalari
  [INTEL-ARK-6548Y]= Xeon Gold 6548Y+ (32 cekirdek, $4.173 RCP, TDP 250 W)
  [SPECPOWER-2025Q1] = SPECpower_ssj2008 sonuclari (bosta / %100 yuk)
  [REDHAT-OCPV-2025] [PT-VSPHERE-OCPV-2024] [EDB-LOCALPV] = sanallastirma / konteyner
  [PATRONI-REPL] [PATRONI-MULTIDC] [PIGSTY-RTO] = Patroni replikasyon, coklu DC, RTO
  [ORACLE-RAC-2024] [ORACLE-MAA-2026] [ORACLE-OTN] [ORACLE-CORE] [ORACLE-PART]
  [REDRESS-PL2026] [REDRESS-GG] [ORACLE-PL2009] = Oracle fiyat ve lisans kurallari
  [ACEMQ-VVF] [ACEMQ-RENEW] = VMware VVF/VCF fiyatlari ve asgarileri
  [RH-OCP-GUIDE]   = Red Hat Self-managed OpenShift Subscription Guide (2024-10)
  [SWEXPRESS-OCP]  = OCP Premium 2 cekirdek / 4 vCPU, 1 yil: 3.872 EUR (bayi listesi)
  [CDW-OVE] [CCSP-RH] [VENDORBENCH-OCP] = OVE, RHEL VDC, OpenShift fiyatlari
  [VENDORBENCH-AFA] = all-flash dizi TB fiyatlari ve destek oranlari (Q1 2026)
  [STORAGEREVIEW-P5520] = yerel NVMe gecikmesi
  [VISHWANATH-2010] [ITIC-2024] [YELLOWBRICKS-HA] [EDB-SYNCREP] = availability, latency
  [PCSP-SERVER] [PCSP-SSD] [CAPCOMP-RAM] [BACLOUD-RAM] = bilesen fiyatlari (common_model §7)
  [ASSUME] = kaynakla daraltilamayan varsayim; [DERIVED] = kaynaktan hesaplanan
================================================================================
"""

import argparse
import json
import math
import sys

import common_model as cm
import mainframe_model as mf

# Parametre sahipligi: x86'ya ozgu parametreler burada; ortak olanlar common_model'de;
# personel egrisinin girdisi (PCI esdegeri) ve yillik profil uretici mainframe
# modulunden okunur. use_values bir adi sahibi olan modulde degistirir.
_PARAM_MODULES = (sys.modules[__name__], cm, mf)


def __getattr__(name):
    if not name.startswith("_") and name in vars(cm):
        return getattr(cm, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def use_values(values):
    return cm.use_values(values, _PARAM_MODULES)


# ==============================================================================
# BOLUM 1 — IS YUKU (KB-01)
# ==============================================================================
# x86 capasi sysbench oltp_read_write'in kendisidir: bilesim tanim geregi
# ayni, aralik/nokta orani olculmus capanin icindedir. Diger profillerin
# goreli agirligi ifade maliyetlerinden (nokta okuma birimi cinsinden):
#   birim(profil) = nokta + aralik x RANGE_READ_WEIGHT + yazma x X86_WRITE_POINT_RATIO
#                 + (commit + BEGIN) x X86_TXCTL_POINT_RATIO
#   goreli_agirlik = birim(profil) / birim(oltp_rw)        (oltp_rw -> 1)
# Vonng alt testlerinden [DERIVED, kopruler_v1 KB-01]: nokta 0,73 makine-us,
# yazma / nokta 3,65-4,15, BEGIN/COMMIT ~ 1 nokta. K6 olcumuyle kalibre edilir.
X86_WRITE_POINT_RATIO = 3.9        # [DERIVED, VONNG-PERF] 3,65-4,15 araliginin ortasi
X86_TXCTL_POINT_RATIO = 1.0        # [DERIVED, VONNG-PERF] BEGIN/COMMIT ~ bir nokta sorgusu
X86_REFERENCE_MIX = "oltp_rw"      # capanin olculdugu bilesim


class X86Workload:
    """Bir islem tipinin bilesimi (common_model.WORKLOAD_MIXES ile ayni alanlar)."""
    def __init__(self, name, point_reads, range_reads, writes, commits, label="", source=""):
        self.name = name
        self.point_reads, self.range_reads = point_reads, range_reads
        self.writes, self.commits = writes, commits
        self.label, self.source = label, source

    @property
    def reads(self):
        return self.point_reads + self.range_reads

    def statements(self):
        """Ifade sayisi (BEGIN + SQL + COMMIT); sysbench'te ifade basina bir gidis-donus."""
        return self.reads + self.writes + self.commits + 1

    def point_units(self):
        return (self.point_reads + self.range_reads * cm.RANGE_READ_WEIGHT
                + self.writes * X86_WRITE_POINT_RATIO
                + (self.commits + 1) * X86_TXCTL_POINT_RATIO)

    def rel_weight(self):
        return self.point_units() / get_workload(X86_REFERENCE_MIX).point_units()

    def sync_read_io(self):
        return cm.mix_sync_read_io(self.reads)

    def sync_write_io(self):
        return cm.mix_sync_write_io(self.commits)

    def storage_iops(self):
        return cm.mix_storage_iops(self.reads, self.writes, self.commits)

    def mainframe_profile(self):
        """Ayni bilesimin mainframe profili (personel egrisinin girdisi, KB-13;
        islem yoneticisi payi, KB-12)."""
        if self.name in mf.WORKLOAD_PROFILES:
            return mf.WORKLOAD_PROFILES[self.name]
        return mf.WorkloadProfile(self.name, self.point_reads, self.writes, self.commits,
                                  self.reads + self.writes > 0, self.label, self.source,
                                  range_reads=self.range_reads)

    def __repr__(self):
        return (f"{self.name}: {self.point_reads:g} nokta + {self.range_reads:g} aralik okuma + "
                f"{self.writes:g} yazma, x86 goreli agirlik={self.rel_weight():.2f}, "
                f"IOPS={self.storage_iops():.2f}")


def _from_mix(name):
    pr, rr, wr, cmt, _zi, label, src = cm.WORKLOAD_MIXES[name]
    return X86Workload(name, pr, rr, wr, cmt, label, src)


X86_WORKLOADS = {name: _from_mix(name) for name in cm.WORKLOAD_MIXES}
DEFAULT_WORKLOAD = "oltp_rw"


def get_workload(workload):
    if isinstance(workload, X86Workload):
        return workload
    if isinstance(workload, mf.WorkloadProfile):
        if workload.name in X86_WORKLOADS:
            return X86_WORKLOADS[workload.name]
        return X86Workload(workload.name, workload.point_reads, workload.range_reads,
                           workload.writes, workload.commits, workload.label, workload.source)
    if workload not in X86_WORKLOADS:
        raise ValueError(f"x86'da karsiligi olmayan profil: {workload} (redp_light CICS "
                         f"bellek tablosu islemidir, SQL icermez)")
    return X86_WORKLOADS[workload]


# ==============================================================================
# BOLUM 2 — SUNUCU KATALOGU (K2, K5; KB-03, KB-06)
# ==============================================================================
# K5 karari: tek referans sunucu (Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3
# sinifi, 2 soket, Xeon 5. nesil "Emerald Rapids"), uretici farki fiyat
# araliklarinda. K2: z16 donemine ait nesil ana senaryo.
# Cekirdek adimlari ayni ailede farkli SKU'lardir. Kaynakli tek SKU Xeon Gold
# 6548Y+'dir (32 cekirdek): SPECrate2017_int_base 628 / 64 cekirdek = 9,81
# [SPEC-R760], Intel RCP $4.173, TDP 250 W [INTEL-ARK-6548Y]. Diger adimlar
# ayni cekirdek basina SPECint, fiyat ve gucle olceklenir [ASSUME]; ayni ailede
# az cekirdekli SKU'lar daha yuksek frekansta calistigi icin bu, kucuk
# dugumlerde x86 aleyhine tutucudur.
# Ana katalog 2 x 32 = 64 cekirdege kadar (Vonng capasinin ~1,3 kati);
# 96 ve 128 cekirdek "ekstrapolasyon" isaretli duyarliliktir (KB-06).
X86_SPECINT_PER_CORE = 628.0 / 64.0          # [SPEC-R760] 9,81
X86_CPU_LIST_USD_PER_CORE = 4173.0 / 32.0    # [INTEL-ARK-6548Y] -> [ASSUME] cekirdekle dogrusal
X86_CPU_W_PER_CORE = 250.0 / 32.0            # [INTEL-ARK-6548Y] TDP / cekirdek


class ServerSKU:
    def __init__(self, cores_per_socket, sockets=2, extrapolated=False):
        self.cores_per_socket, self.sockets = cores_per_socket, sockets
        self.cores = cores_per_socket * sockets
        self.extrapolated = extrapolated
        self.specint_per_core = X86_SPECINT_PER_CORE
        self.code = f"2x{cores_per_socket}c" + ("*" if extrapolated else "")

    def __repr__(self):
        return f"R760-sinifi {self.code} ({self.cores} cekirdek)"


X86_CATALOG = [ServerSKU(c) for c in (8, 12, 16, 24, 32)]
X86_CATALOG_EXTRAPOLATED = [ServerSKU(c, extrapolated=True) for c in (48, 64)]
ALLOW_EXTRAPOLATION = False


def catalog():
    return X86_CATALOG + (X86_CATALOG_EXTRAPOLATED if ALLOW_EXTRAPOLATION else [])


# --- Sunucu fiyati (KB-15 fiyat tabani kurali) ---------------------------------
# dugum_net = (sasi_platform + CPU + NIC/HBA) x (1 - X86_HW_DISCOUNT)    <- liste kalemleri
#           + bellek_GB x DRAM $/GB + NVMe_TB x NVMe $/TB               <- piyasa fiyati
# Indirim yalnizca liste tabanli kalemlere ve bir kez uygulanir; bellek ve NVMe
# donem tablosundan piyasa fiyatiyla gelir ve OEM indirimiyle birlestirilmez
# (common_model §7).
X86_PLATFORM_COST = 12000.0     # USD liste; sasi, anakart, PSU, fan, iDRAC, temel destek
                                # [ASSUME; R760xs taban $15.957 PCSP-SERVER'dan kaba; aralik 8-18K]
X86_NIC_HBA_LIST_USD = 2000.0   # [ASSUME] 2 x 25 GbE + (SAN dugumunde) FC HBA
X86_HW_DISCOUNT = 0.35          # [ASSUME] OEM liste indirimi; aralik 0,50 / 0,35 / 0,20
X86_MEM_GB_PER_CORE = 8.0       # [ASSUME] veritabani dugumu; 64 cekirdekte 512 GB
X86_MEM_MIN_GB = 128.0          # [ASSUME]
X86_BOOT_NVME_TB = 1.92         # [ASSUME] 2 x 0,96 TB isletim sistemi / hipervizor
X86_AMORTIZATION_YEARS = 5      # mainframe HARDWARE_AMORTIZATION_YEARS ile ayni
X86_WARRANTY_YEARS = 3          # [ASSUME] uretici garantisi / ProSupport; KB-11 (mainframe 1 yil)
X86_MAINT_RATE_ANNUAL = 0.125   # [ASSUME] garanti sonrasi, donanim degerinin %10-15'i

# --- Guc (KB-17): SPECpower %100 yuk mantigi --------------------------------------
X86_PLATFORM_W = 220.0          # [SPECPOWER-2025Q1] DL380 Gen12 bosta 220 W (platform tabani)
X86_POWER_CONFIG_UPLIFT = 1.25  # [ASSUME] 512 GB+ bellek, 8-24 NVMe; aralik 1,1-1,4


def node_memory_gb(sku):
    return max(X86_MEM_MIN_GB, sku.cores * X86_MEM_GB_PER_CORE)


def node_list_items(sku):
    """Liste tabanli kalemler (USD): sasi + CPU + NIC/HBA."""
    return X86_PLATFORM_COST + sku.cores * X86_CPU_LIST_USD_PER_CORE + X86_NIC_HBA_LIST_USD


def node_net_capex(sku):
    """Dugumun net alis bedeli (veri NVMe'si haric; o storage katmanindadir)."""
    return (node_list_items(sku) * (1.0 - X86_HW_DISCOUNT)
            + node_memory_gb(sku) * cm.component_price("dram_usd_per_gb")
            + X86_BOOT_NVME_TB * cm.component_price("nvme_usd_per_tb"))


def node_power_kw(sku):
    return (X86_PLATFORM_W + sku.cores * X86_CPU_W_PER_CORE) * X86_POWER_CONFIG_UPLIFT / 1000.0


def maintenance_factor():
    y = X86_AMORTIZATION_YEARS
    return max(0.0, y - X86_WARRANTY_YEARS) / y


# ==============================================================================
# BOLUM 3 — KAPASITE KOPRUSU VE OLCEKLEME (KB-03, KB-06)
# ==============================================================================
# Capa [VONNG-PERF]: AWS c5d.metal (2 x Xeon Platinum 8275CL, 48 fiziksel
# cekirdek), oltp_read_write 519.069 QPS -> 25.953 TPS (20 ifade/islem).
# Cascade Lake cekirdek basina SPECint 309 / 52 = 5,94 [SPEC-8270].
#   25.953 / 48 / 5,94 = 91 TPS / SPECint birimi / cekirdek       [DERIVED]
# K karari (Emirhan, 2026-11-16): capa K6 kendi olcumumuz olacak; o zamana kadar
# aralik 120 / 91 / 60 (low = x86 lehine).
_VONNG_QPS = 519069.0
_VONNG_TPS = _VONNG_QPS / 20.0
_VONNG_CORES = 48
_CASCADE_SPECINT_PER_CORE = 309.0 / 52.0
X86_TPS_PER_SPECINT_CORE = _VONNG_TPS / _VONNG_CORES / _CASCADE_SPECINT_PER_CORE   # ~91,0
X86_ANCHOR_CORES = _VONNG_CORES     # n_ref: dugum ici olceklenmenin referansi

# Dugum ici olceklenme S(n) = (n / n_ref)^(B_X86 - 1)  [ASSUME; K6/USL ile kalibre]
# Aralik 0,80-1,00 (KB-06). Yon dugum boyutuna baglidir: n > n_ref'te kucuk b x86
# aleyhine, n < n_ref'te x86 lehinedir (capanin altinda dugum basina verim artar).
# Koselerin yon tutarli kalmasi icin aralik bir duzey anahtariyla uygulanir:
# low = iki ucun dugum icin elverisli olani (max S), high = elverissiz olani (min S).
B_X86 = 0.90
B_X86_RANGE = (0.80, 1.00)
X86_SCALING_LEVEL = "mid"

# Sanallastirma ve konteyner ek yuku [plan v1 §3.7; iki rakip VENDOR arasindan ASSUME]
VIRT_OVERHEAD = {
    "vsphere": {"low": 0.03, "mid": 0.07, "high": 0.15},   # [PT-VSPHERE-OCPV-2024]
    "ocpv":    {"low": 0.05, "mid": 0.12, "high": 0.25},   # [REDHAT-OCPV-2025]
}
VIRT_LEVEL = "mid"
CONTAINER_OVERHEAD = 0.02          # [EDB-LOCALPV + ASSUME] yerel kalici birimle; aralik 0-0,05

# Oracle'in ayni cekirdekte PostgreSQL'e gore oltp_rw verimi. Kalibre edilemez:
# OTN lisansi "disclose results of any Program benchmark tests without Oracle's
# prior consent"i yasaklar [ORACLE-OTN]. 1,0 kayitsizlik ilkesidir.
ORACLE_THROUGHPUT_FACTOR = 1.0     # aralik 1,30 / 1,00 / 0,80
# RAC: k dugumun ham verimi = dugum x [1 + (k - 1) x verim]  [ASSUME; Oracle'in
# "%80 alti olceklenme celiskiye isarettir" esigi alt uc, ORACLE-RAC-2024]
RAC_SCALING_EFFICIENCY = 0.90
RAC_MAX_NODES = 8                  # [ASSUME] modellenen en buyuk RAC kumesi


def scaling_factor(cores):
    x = cores / X86_ANCHOR_CORES
    if X86_SCALING_LEVEL == "mid":
        return x ** (B_X86 - 1.0)
    ends = [x ** (b - 1.0) for b in B_X86_RANGE]
    return max(ends) if X86_SCALING_LEVEL == "low" else min(ends)


def tps_per_core(sku, stack, workload=DEFAULT_WORKLOAD):
    """Bir fiziksel cekirdegin %100 kullanimdaki oltp TPS'i (yiginin ek yukleriyle)."""
    wl = get_workload(workload)
    t = (X86_TPS_PER_SPECINT_CORE * sku.specint_per_core * scaling_factor(sku.cores)
         * (1.0 - VIRT_OVERHEAD[stack.hypervisor][VIRT_LEVEL]))
    if stack.containerized:
        t *= 1.0 - CONTAINER_OVERHEAD
    if stack.db == "oracle":
        t *= ORACLE_THROUGHPUT_FACTOR
    return t / wl.rel_weight()


def node_raw_tps(sku, stack, workload=DEFAULT_WORKLOAD):
    return tps_per_core(sku, stack, workload) * sku.cores


def cluster_raw_tps(sku, stack, nodes, workload=DEFAULT_WORKLOAD):
    """Yazmayi tasiyan dugumlerin ham verimi: Patroni'de tek birincil; RAC'ta k dugum."""
    raw = node_raw_tps(sku, stack, workload)
    if stack.db != "oracle" or nodes <= 1:
        return raw
    return raw * (1.0 + (nodes - 1) * RAC_SCALING_EFFICIENCY)


# ==============================================================================
# BOLUM 4 — KULLANIM TAVANI VE LATENCY (KB-05)
# ==============================================================================
# U karari (Emirhan, 2026-11-16): iki tarafta ayni kural
#   rho_max = min(rho_latency, tavan);  x86 tavani 0,90 / 0,70 / 0,50.
# Gerekce: x86'da WLM ve CoD karsiligi yok, veritabani dugumleri tepe yukte
# boslukla isletilir. %15-20 alt uc yalnizca "konsolide edilmemis park"
# uzlastirma senaryosudur (ana aralikta yok; cift sayim).
# Latency (mainframe ile ayni kuyruk ailesi, cekirdek basina bagimsiz M/M/1):
#   R(p) = D_ag + D_io + D_repl + E[X] / (1 - rho) x ln(1/(1-p)),  E[X] = 1 / tps_per_core
X86_UTIL_CEILING = 0.70
X86_NET_RTT_MS = {"low": 0.05, "mid": 0.15, "high": 0.5}   # [ASSUME] ayni veri merkezi
X86_LATENCY_LEVEL = "mid"
X86_STORED_PROCEDURES = False   # True: islem tek gidis-donus (saklı yordam) [KB-05]
T_NVME_READ_S = 141e-6          # [STORAGEREVIEW-P5520, VENDOR sponsorlu] karma ortalama
T_NVME_WAL_FSYNC_S = 60e-6      # [ASSUME] PLP'li kurumsal NVMe'de WAL fsync; K6 ile olculecek
T_SAN_READ_S = 250e-6           # [ASSUME] aralik 150-400 us (FC / NVMe-oF + dizi)
T_SAN_WRITE_S = 150e-6          # [ASSUME] dizi NVRAM onayi + fabric
# "Konsolide edilmemis park" uzlastirma senaryosu (U karari; benzer_calismalar B1):
# dagitik sunucularin tipik %15-20 kullanimi. Ana aralikta yoktur (cift sayim);
# yalnizca IBM'in U_R iddiasiyla uzlastirma icin --compare ciktisinda ayri satir.
X86_UNCONSOLIDATED_CEILING = 0.175


def net_delay_s(workload):
    rtt = X86_NET_RTT_MS[X86_LATENCY_LEVEL] / 1000.0
    trips = 1 if X86_STORED_PROCEDURES else get_workload(workload).statements()
    return trips * rtt


def io_delay_s(workload, db):
    wl = get_workload(workload)
    if db == "postgresql":
        return wl.sync_read_io() * T_NVME_READ_S + wl.sync_write_io() * T_NVME_WAL_FSYNC_S
    return wl.sync_read_io() * T_SAN_READ_S + wl.sync_write_io() * T_SAN_WRITE_S


def repl_delay_s(topology, db, workload):
    """Senkron replikasyonda commit basina bir gidis-donus (+ uzak sitede mesafe)."""
    mode = topology.sync_mode(db)
    if mode is None:
        return 0.0
    rtt = X86_NET_RTT_MS[X86_LATENCY_LEVEL] / 1000.0
    t = rtt + (T_NVME_WAL_FSYNC_S if db == "postgresql" else T_SAN_WRITE_S)
    if mode == "remote":
        t += cm.METRO_DISTANCE_KM * cm.REPLICATION_S_PER_KM
    return get_workload(workload).commits * t


def fixed_delay_s(topology, db, workload):
    return net_delay_s(workload) + io_delay_s(workload, db) + repl_delay_s(topology, db, workload)


def max_utilization(per_core_tps, d_fixed, latency_target_s, percentile):
    if latency_target_s is None:
        return X86_UTIL_CEILING
    ex = 1.0 / per_core_tps
    budget = latency_target_s - d_fixed
    ln_term = math.log(1.0 / (1.0 - percentile))
    if budget <= 0 or ex * ln_term >= budget:
        return 0.0
    return max(0.0, min(1.0 - ex * ln_term / budget, X86_UTIL_CEILING))


def latency_at(per_core_tps, d_fixed, rho, percentile):
    if rho >= 1.0:
        return float("inf")
    return d_fixed + (1.0 / per_core_tps) / (1.0 - rho) * math.log(1.0 / (1.0 - percentile))


# ==============================================================================
# BOLUM 5 — YIGIN (v4 §4.8, K7)
# ==============================================================================
# Her zaman bir sanallastirma katmani var (bare-metal Kubernetes yok, v4 §4.8).
# Veritabani ya VM'de (Patroni / Oracle) ya da VM'lerin icindeki bir Kubernetes
# kumesinde operatorle (Crunchy PGO, Patroni kullanir) calisir. Oracle RAC
# konteynerde uretim icin modellenmez [ASSUME, doğrulanmalı]: Oracle yalnizca
# VM yerlesiminde. OpenShift Virtualization uzerinde Oracle: Oracle'in sertifika
# durumu doğrulanmalı; aday olarak tutulur ve sonucta isaretlenir.
HYPERVISORS = ("vsphere", "ocpv")
PLACEMENTS = ("vm", "k8s", "openshift")
DATABASES = ("postgresql", "oracle")
_LABEL = {"vsphere": "vSphere", "ocpv": "OpenShift Virt", "vm": "VM", "k8s": "K8s",
          "openshift": "OpenShift", "postgresql": "PostgreSQL+Patroni", "oracle": "Oracle"}


class Stack:
    def __init__(self, hypervisor, placement, db):
        self.hypervisor, self.placement, self.db = hypervisor, placement, db
        self.containerized = placement in ("k8s", "openshift")
        self.code = f"{_LABEL[hypervisor]} / {_LABEL[placement]} / {_LABEL[db]}"

    def __repr__(self):
        return self.code


STACKS = [Stack(h, p, d) for d in DATABASES for h in HYPERVISORS for p in PLACEMENTS
          if not (d == "oracle" and p != "vm")]


# ==============================================================================
# BOLUM 6 — TOPOLOJILER X1-X4 (KB-07, KB-08)
# ==============================================================================
# Mainframe M1-M4 ile eslenir (SG24-8446 desenleri <-> Oracle MAA katmanlari).
#  X1 (M1)  Oracle Silver: tek sitede RAC (N+1).  Patroni: tek sitede 3 dugum
#           (birincil + senkron + asenkron replika), etcd 3 uye [PATRONI-REPL].
#  X2 (M2)  Oracle: X1 + uzak sitede Data Guard standby (Max Availability, SYNC),
#           elle gecis. Patroni: X1 + uzak sitede standby kume (2 dugum), elle
#           terfi. Patroni belgeleri iki DC icin standby kumeyi "Asynchronous
#           Replication" basligi altinda onerir [PATRONI-MULTIDC]: RPO > 0.
#           (kopruler_v1 KB-08 X2 icin RPO 0 yaziyordu; Patroni'nin calisma
#           bicimine gore duzeltildi, dokumantasyon §6.2.)
#  X3 (M3)  Oracle Gold: iki sitede RAC + Active Data Guard + Fast-Start Failover,
#           gozlemci 3. sitede. Patroni: iki sitede 2 + 2 dugum, synchronous_mode,
#           synchronous_node_count = 2 (en az bir uzak senkron kopya -> RPO 0),
#           DCS 3 sitede ("a minimum of 3 is required", PATRONI-MULTIDC).
#  X4 (M4)  Oracle Platinum: iki sitede aktif-aktif RAC + GoldenGate (asenkron).
#           PostgreSQL: infeasible (K4; cekirdekte karsiligi yok).
# Availability (KB-07): saha olaylari ortak (common_model §2);
#   D = D_saha(T_rec) + lam_planli x T_planli + yama switchover'lari
#     + N_kesen_dugum x lam_dugum x T_failover
# N_kesen_dugum: arizasi hizmeti kesen dugum sayisi. Patroni'de yalnizca
# birincil (replika arizasi hizmeti kesmez); RAC'ta hizmeti tasiyan her dugum
# (dugum kaybinda kume yeniden yapilandirmasi tum oturumlari kisa sure dondurur).
NODE_EVENTS_PER_YEAR = {"low": 0.03, "mid": 0.10, "high": 0.30}   # [VISHWANATH-2010 asagi; high ASSUME]
NODE_EVENT_LEVEL = "mid"
T_FAILOVER_SECONDS = {
    "postgresql": {"low": 15.0, "mid": 35.0, "high": 90.0},      # [PIGSTY-RTO] 27-41 sn
    "oracle":     {"low": 5.0, "mid": 15.0, "high": 300.0},      # [ORACLE-RAC-2024, ORACLE-MAA-2026]
}
X86_PLANNED_EVENTS_PER_YEAR = {"low": 0.25, "mid": 0.5, "high": 1.0}   # mainframe ile ayni aralik [ASSUME]
X86_PLANNED_OUTAGE_MINUTES = {                                         # olay basina (buyuk surum vb.)
    "single": {"low": 5.0, "mid": 15.0, "high": 60.0},   # X1-X2 [ASSUME]
    "multi":  {"low": 0.5, "mid": 2.0, "high": 10.0},    # X3-X4 [ASSUME]; Oracle Gold < 30 sn
}
X86_PATCH_SWITCHOVERS_PER_YEAR = 12          # aylik OS / hipervizor yamasi [Deg. #8 §3.4, ASSUME]
X86_SWITCHOVER_SECONDS = {
    "postgresql": {"low": 5.0, "mid": 15.0, "high": 30.0},   # Patroni switchover [ASSUME]
    "oracle":     {"low": 0.0, "mid": 5.0, "high": 15.0},    # RAC rolling + Application
}                                                            #  Continuity [ASSUME]
# Saha olayinda teknik gecis suresi (dk). X2'de ortak elle karar suresi eklenir.
X86_RECOVERY_TECH_MINUTES = {
    "X2": {"low": 5.0, "mid": 15.0, "high": 30.0},     # DG failover / Patroni standby terfisi [ASSUME]
    "X3": {"low": 1.0, "mid": 2.0, "high": 5.0},       # Gold "saniyeler - 2 dk"; Patroni 30-90 sn
    "X4": {"low": 0.05, "mid": 0.25, "high": 0.5},     # Platinum < 30 sn (3 / 15 / 30 sn)
}
X86_RECOVERY_LEVEL = "mid"
X86_PLANNED_LEVEL = "mid"
X2_PG_ASYNC_RPO_SECONDS = 5.0                # [ASSUME] standby kume asenkron gecikmesi (M4 ile ayni buyukluk)


class X86Topology:
    def __init__(self, code, name, pattern, oracle_tier, patroni, planned_group,
                 manual_failover=False):
        self.code, self.name, self.pattern = code, name, pattern
        self.oracle_tier, self.patroni = oracle_tier, patroni
        self.planned_group = planned_group
        self.manual_failover = manual_failover

    def supports(self, db):
        return not (db == "postgresql" and self.code == "X4")

    def sites(self):
        return 1 if self.code == "X1" else 2

    def has_witness(self):
        return self.code in ("X3", "X4")

    def db_nodes(self, db, k):
        """Site basina veritabani dugumu sayisi {site: n}."""
        if db == "postgresql":
            return {"X1": {"A": 3}, "X2": {"A": 3, "B": 2}, "X3": {"A": 2, "B": 2}}[self.code]
        return {"X1": {"A": k}, "X2": {"A": k, "B": max(1, k - 1)},
                "X3": {"A": k, "B": k}, "X4": {"A": k, "B": k}}[self.code]

    def sync_mode(self, db):
        """None / 'local' / 'remote': commit'i bekleten senkron kopyanin yeri."""
        if db == "postgresql":
            return "remote" if self.code == "X3" else "local"
        return "remote" if self.code in ("X2", "X3") else None

    def rpo_seconds(self, db):
        if self.code == "X1":
            return 86400.0        # [ASSUME] M1 ile ayni kural: gunluk saha disi yedek
        if self.code == "X2" and db == "postgresql":
            return X2_PG_ASYNC_RPO_SECONDS
        if self.code == "X4":
            return 5.0            # [ASSUME] GoldenGate asenkron; M4 ile ayni buyukluk
        return 0.0

    def recovery_minutes(self, level=None):
        r = X86_RECOVERY_TECH_MINUTES.get(self.code)
        if r is None:
            return float("inf")
        lv = level or X86_RECOVERY_LEVEL
        if self.manual_failover:
            return cm.manual_failover_minutes(r[lv], lv)
        return r[lv]

    @property
    def rto_minutes(self):
        r = self.recovery_minutes()
        return 72 * 60.0 if r == float("inf") else r

    def interrupting_nodes(self, db, k):
        if db == "postgresql":
            return 1
        serving = 2 if self.code == "X4" else 1
        return k * serving

    def annual_downtime_hours(self, db, k=2, site=None, recovery=None, planned=None, node=None):
        t_rec = self.recovery_minutes(recovery) / 60.0
        unplanned = cm.site_downtime_hours(t_rec, site)
        p = planned or X86_PLANNED_LEVEL
        planned_h = (X86_PLANNED_EVENTS_PER_YEAR[p]
                     * X86_PLANNED_OUTAGE_MINUTES[self.planned_group][p] / 60.0)
        rolling = X86_PATCH_SWITCHOVERS_PER_YEAR * X86_SWITCHOVER_SECONDS[db][p] / 3600.0
        nl = node or NODE_EVENT_LEVEL
        node_h = (self.interrupting_nodes(db, k) * NODE_EVENTS_PER_YEAR[nl]
                  * T_FAILOVER_SECONDS[db][nl] / 3600.0)
        return unplanned + planned_h + rolling + node_h

    def availability(self, db, k=2, **kw):
        return 1.0 - self.annual_downtime_hours(db, k, **kw) / cm.HOURS_PER_YEAR

    def availability_range(self, db, k=2):
        return (self.availability(db, k, site="high", recovery="high", planned="high", node="high"),
                self.availability(db, k, site="low", recovery="low", planned="low", node="low"))

    def __repr__(self):
        return f"{self.code}: {self.name}"


X86_TOPOLOGIES = [
    X86Topology("X1", "Tek site HA kumesi", "Reliable base", "Silver (RAC + AC)",
                "3 dugum, 1 senkron replika", "single"),
    X86Topology("X2", "Tek site HA + uzak DR, elle gecis", "Failover capable",
                "Silver + Data Guard (Max Availability)", "standby kume (asenkron)",
                "single", manual_failover=True),
    X86Topology("X3", "Iki site, otomatik gecis", "Fault tolerant",
                "Gold (RAC + ADG + FSFO)", "coklu site, uzak senkron, DCS 3 sitede", "multi"),
    X86Topology("X4", "Iki site aktif-aktif", "Adaptive continuity",
                "Platinum (GoldenGate aktif-aktif)", "infeasible (K4)", "multi"),
]


def get_topology(code):
    return next(t for t in X86_TOPOLOGIES if t.code == code)


# ==============================================================================
# BOLUM 7 — YAZILIM LISANSLARI VE ABONELIKLER (KB-11)
# ==============================================================================
# Fatura tabani kurulu fiziksel cekirdek ya da dugumdur; DR dugumleri de tam
# lisanslanir; CoD karsiligi yoktur. Asimetri esitlenmez, modellenir.
# --- VMware vSphere Foundation (Broadcom) -------------------------------------
VSPHERE_USD_PER_CORE_YEAR = 150.0   # [ACEMQ-VVF, ACEMQ-RENEW] VVF teklifleri $100-196; VCF $350
VSPHERE_MIN_CORES_PER_CPU = 16      # [ACEMQ-VVF] CPU basina en az 16 cekirdek
VSPHERE_MIN_CORES_PER_ORDER = 72    # [ACEMQ-VVF] siparis basina en az 72 cekirdek (Nisan 2025)
# --- Red Hat ---------------------------------------------------------------------
OVE_USD_PER_NODE_YEAR = 8000.0      # [CDW-OVE] OpenShift Virtualization Engine premium, 1-2
                                    #  soket <= 128 cekirdek: $9.880; aralik 6-10K [ASSUME]
RHEL_VDC_USD_PER_NODE_YEAR = 2904.0 # [CCSP-RH] RHEL for Virtual Datacenters, hizmet saglayici
                                    #  sozlesme listesi (kurumsal liste degil; taban notu)
# OpenShift sayim kurali [RH-OCP-GUIDE]: sanal dugumlerde (vSphere ya da OpenShift
# Virtualization uzerindeki VM'ler) "core-based subscriptions", 2 cekirdek / 4 vCPU
# basina; soket cifti aboneligi yalnizca bare-metal dugum icindir ("Each physical,
# bare-metal server using socket-based entitlements can only be used as a single
# OpenShift node"). v4 kurali bare-metal Kubernetes'i dislar, bu yuzden kopruler_v1
# KB-11'deki OCP_USD_PER_SOCKETPAIR_YEAR bu modelde kullanilmaz; yerine cekirdek cifti.
# Kontrol duzlemi dugumleri sayilmaz [RH-OCP-GUIDE]. RHEL, OpenShift dugumlerinde dahil.
OCP_USD_PER_COREPAIR_YEAR = 3000.0  # [SWEXPRESS-OCP] Premium 3.872 EUR ~ $4.200; Standard
                                    #  ~%25-35 asagi [VENDORBENCH-OCP] -> ~$3.000; aralik 2.000-4.200
# --- Oracle Database (islemci basina liste, USD) ---------------------------------
ORACLE_PRICES = {
    "ee": 47500.0,           # [REDRESS-PL2026] (doğrulanmalı)
    "rac": 23000.0,          # [REDRESS-PL2026]
    "diagnostics": 7500.0,   # [REDRESS-PL2026] operasyon icin fiilen zorunlu
    "tuning": 5000.0,        # [REDRESS-PL2026]
    "adg": 11500.0,          # [ORACLE-PL2009 $10.000 -> yaygin kabul $11.500] (doğrulanmalı)
    "goldengate": 17500.0,   # [REDRESS-GG] "GoldenGate costs $17,500 per processor"; ADG'yi icerir
}
ORACLE_CORE_FACTOR = 0.5     # [ORACLE-CORE] Intel Xeon, Ocak 2026 tablosu
ORACLE_DISCOUNT = 0.45       # [OLE-NET2026, REDRESS-PL2026] aralik 0,60 / 0,45 / 0,20
ORACLE_SUPPORT_RATE = 0.22   # [REDRESS-PL2026] net lisansin yillik %22'si
# --- PostgreSQL --------------------------------------------------------------------
PG_SUPPORT_USD_PER_CORE_YEAR = 500.0   # [ASSUME, kalibre edilemedi] 0 / 500 / 1.500


def oracle_options(topology, rac):
    opts = ["ee", "diagnostics", "tuning"]
    if rac:
        opts.append("rac")
    if topology.code == "X3":
        opts.append("adg")
    if topology.code == "X4":
        opts.append("goldengate")          # GoldenGate lisansi ADG'yi icerir [REDRESS-GG]
    return opts


def oracle_license_net(cores, topology, rac):
    """Bir dugumun Oracle net lisans bedeli (capex, USD). VM'in calisabilecegi
    butun fiziksel cekirdekler lisanslanir [ORACLE-PART]: Oracle adanmis
    dugumlerde varsayilir."""
    processors = math.ceil(cores * ORACLE_CORE_FACTOR)
    lst = processors * sum(ORACLE_PRICES[o] for o in oracle_options(topology, rac))
    return lst * (1.0 - ORACLE_DISCOUNT)


def platform_subscriptions(stack, groups):
    """Hipervizor + isletim sistemi + orkestrasyon yillik abonelikleri, grup basina.
    groups: [{'role', 'site', 'sku', 'n'}]. Donus: grup indeksiyle esli liste."""
    out = []
    for g in groups:
        sku, n = g["sku"], g["n"]
        hv = (VSPHERE_USD_PER_CORE_YEAR * max(sku.cores, VSPHERE_MIN_CORES_PER_CPU * sku.sockets)
              if stack.hypervisor == "vsphere" else OVE_USD_PER_NODE_YEAR)
        workers_on_ocp = (stack.placement == "openshift" and g["role"] in ("db", "app"))
        os_ = 0.0 if workers_on_ocp else RHEL_VDC_USD_PER_NODE_YEAR
        orch = OCP_USD_PER_COREPAIR_YEAR * math.ceil(sku.cores / 2) if workers_on_ocp else 0.0
        out.append({"hypervisor": hv * n, "os": os_ * n, "orchestration": orch * n})
    if stack.hypervisor == "vsphere":   # siparis asgarisi: farki gruplara oranla dagit
        licensed = sum(max(g["sku"].cores, VSPHERE_MIN_CORES_PER_CPU * g["sku"].sockets) * g["n"]
                       for g in groups)
        if 0 < licensed < VSPHERE_MIN_CORES_PER_ORDER:
            f = VSPHERE_MIN_CORES_PER_ORDER / licensed
            for o in out:
                o["hypervisor"] *= f
    return out


# ==============================================================================
# BOLUM 8 — UYGULAMA KATMANI (KB-12, C karari)
# ==============================================================================
# Mainframe CPU'su ve lisansi CICS'i (islem yoneticisi) icerir; x86 capasinda
# uygulamanin yerini modelin disindaki sysbench istemcisi tutar. C karari:
#   TM_payi = CPU_US_TM_BASE / CPU(profil)          (oltp_rw, F ile ~%7,8)
#   uygulama_cekirdegi = DB_cekirdegi x TM_payi / (1 - TM_payi)
# Linux VM olarak fiyatlanir (donanim + hipervizor + RHEL / OpenShift); acik
# kaynak uygulama sunucusu, ek lisans yok. Sitede N+1 (en az 2 host), DR
# sitesinde kopya. 4,9 kat [SHEDLETSKY-2008] yalnizca ust uc duyarliligi.
X86_APP_MIN_HOSTS = 2
X86_APP_TM_MULTIPLIER = 1.0     # 4,9 = SHEDLETSKY ust uc duyarliligi


def app_core_need(db_busy_cores, workload):
    """Uygulama katmaninin mesgul fiziksel cekirdegi. db_busy_cores = TPS /
    tps_per_core: sanallastirma ek yukunu zaten icerir; ayni hipervizordeki
    uygulama VM'lerinde ayni oran varsayilir, ikinci kez uygulanmaz."""
    with mf.bridge_reference():
        tm = get_workload(workload).mainframe_profile().tm_share() * X86_APP_TM_MULTIPLIER
    tm = min(tm, 0.95)
    return db_busy_cores * tm / (1.0 - tm)


def app_hosts(db_busy_cores, stack, workload):
    """(sku, host sayisi, mesgul cekirdek) site basina: en ucuz uygun SKU, N+1.
    Tavan (X86_UTIL_CEILING) yalnizca burada, bir kez uygulanir."""
    need = app_core_need(db_busy_cores, workload)
    best = None
    for sku in X86_CATALOG:
        usable = sku.cores * X86_UTIL_CEILING
        n = max(X86_APP_MIN_HOSTS, math.ceil(need / usable) + 1)
        c = n * node_net_capex(sku)
        if best is None or c < best[2]:
            best = (sku, n, c)
    return best[0], best[1], need


# ==============================================================================
# BOLUM 9 — STORAGE (KB-09, K1)
# ==============================================================================
# Patroni: yerel NVMe, her dugumde verinin tam kopyasi (paylasimsiz mimari;
# Kubernetes'te yerel kalici birim bare-metal'e yakin, ag tabanli paylasimli
# birim -%89-95 [EDB-LOCALPV]). Dugum ici RAID 0 / JBOD + replika [ASSUME].
#   ham_TB(dugum) = planli_veri x PG_BLOAT_FACTOR / 1,0 (boyutlandirma DRR) / 1,0
# RAC: site basina paylasimli all-flash dizi, ASM.
#   ham_TB(site)  = planli_veri x ORACLE_DB_OVERHEAD / 1,0 / AFA_RAID_USABLE
#   (birincil dizide degistirilemez anlik kopya rezervi; DS8900F Safeguarded
#    Copy'nin karsiligi, ayni %25)
# Fiyat sozlesmesi (common_model §6): AFA teklifleri etkin TB basinadir; once
# ham TB basina listeye cevrilir: x AFA_RAID_USABLE x AFA_DATA_REDUCTION
# (teklifin icindeki veri azaltim orani, geri cevirme). Boyutlandirmada veri
# azaltimi sayilmaz (1,0; mainframe HOST_COMPRESSION_RATIO ile simetrik).
PG_BLOAT_FACTOR = 1.3           # [ASSUME] MVCC sismesi + WAL tutma + bos alan; aralik 1,1-1,6
X86_NVME_BAYS = 24              # [ASSUME] R760 24 x 2,5" on yuva
X86_NVME_DRIVE_SIZES_TB = (3.84, 7.68, 15.36, 30.72)
X86_NVME_MIN_DRIVES = 4         # [ASSUME]
X86_NVME_DRIVE_IOPS = 500000.0  # [ASSUME] kurumsal NVMe 4K rastgele okuma mertebesi
ORACLE_DB_OVERHEAD = 1.5        # [ASSUME] arsiv redo, FRA, temp; Db2 DB_OVERHEAD_FACTOR ile ayni
AFA_LIST_USD_PER_EFF_TB = 270.0 # [VENDORBENCH-AFA] liste $140-400 / etkin TB; aralik ortasi
AFA_DISCOUNT = 0.50             # [DERIVED, VENDORBENCH-AFA] indirimli $65-215 / liste $140-400
AFA_DATA_REDUCTION = 2.5        # [ASSUME] teklifin icindeki veri azaltim orani; 1,5 / 2,5 / 4,0
AFA_RAID_USABLE = 0.75          # [ASSUME] mainframe RAID_USABLE_FRACTION ile ayni
AFA_SNAPSHOT_RESERVE = 0.25     # [ASSUME] mainframe SAFEGUARDED_RESERVE ile ayni
AFA_MIN_LIST_USD = 100000.0     # [ASSUME] cift kontrolculu giris dizisi (liste)
AFA_MAX_RAW_TB = 3000.0         # [ASSUME] dizi basina
AFA_MAX_IOPS = 1000000.0        # [ASSUME] orta sinif AFA tepe IOPS
AFA_MAINT_RATE_ANNUAL = 0.15    # [VENDORBENCH-AFA] yillik %10-25 (DS8900F ile ayni kaynak)
AFA_WARRANTY_YEARS = 0          # [VENDORBENCH-AFA] "destek ilk yil donanimin %10-20'si"
AFA_KW_BASE = 1.2               # [ASSUME]
AFA_KW_PER_PB = 0.8             # [ASSUME]


def pg_node_raw_tb(data_tb=None, growth=None):
    return cm.planned_data_tb(data_tb, growth) * PG_BLOAT_FACTOR


def nvme_layout(raw_tb, iops):
    """Bir dugumun veri NVMe'si: (surucu adedi, surucu TB, kurulu TB) ya da None."""
    for size in X86_NVME_DRIVE_SIZES_TB:
        n = max(X86_NVME_MIN_DRIVES, math.ceil(raw_tb / size),
                math.ceil(iops / (X86_NVME_DRIVE_IOPS * cm.STORAGE_IOPS_CEILING)))
        if n <= X86_NVME_BAYS:
            return n, size, n * size
    return None


def afa_site_plan(raw_tb, iops, primary):
    raw = raw_tb * (1.0 + AFA_SNAPSHOT_RESERVE) if primary else raw_tb
    arrays = max(1, math.ceil(raw / AFA_MAX_RAW_TB),
                 math.ceil(iops / (AFA_MAX_IOPS * cm.STORAGE_IOPS_CEILING)))
    per_raw = cm.price_per_raw_tb(AFA_LIST_USD_PER_EFF_TB, "effective", AFA_RAID_USABLE,
                                  AFA_DATA_REDUCTION)
    lst = max(arrays * AFA_MIN_LIST_USD, raw * per_raw)
    return {"raw_tb": raw, "arrays": arrays, "hw_capex": cm.net_price(lst, AFA_DISCOUNT),
            "power_kw": arrays * AFA_KW_BASE + raw / 1000.0 * AFA_KW_PER_PB}


def storage_plan(peak_tps, workload, topology, db, k, data_tb=None, growth=None):
    """Veri storage'i: site basina capex ve guc. None = infeasible (yerel NVMe yetmez)."""
    wl = get_workload(workload)
    iops = peak_tps * wl.storage_iops()
    nodes = topology.db_nodes(db, k)
    sites = {}
    if db == "postgresql":
        raw = pg_node_raw_tb(data_tb, growth)
        lay = nvme_layout(raw, iops)
        if lay is None:
            return None
        drives, size, inst = lay
        for s, n in nodes.items():
            sites[s] = {"hw_capex": n * inst * cm.component_price("nvme_usd_per_tb"),
                        "power_kw": 0.0, "raw_tb": n * inst,
                        "desc": f"{n} dugum x {drives} x {size:g} TB NVMe"}
        maint = {"rate": X86_MAINT_RATE_ANNUAL, "warranty": X86_WARRANTY_YEARS}
    else:
        raw = cm.planned_data_tb(data_tb, growth) * ORACLE_DB_OVERHEAD / AFA_RAID_USABLE
        for s in nodes:
            p = afa_site_plan(raw, iops, primary=(s == "A"))
            p["desc"] = f"{p['arrays']} AFA ({p['raw_tb']:,.0f} TB ham)"
            sites[s] = p
        maint = {"rate": AFA_MAINT_RATE_ANNUAL, "warranty": AFA_WARRANTY_YEARS}
    hw = sum(v["hw_capex"] for v in sites.values())
    kw = sum(v["power_kw"] for v in sites.values())
    y = X86_AMORTIZATION_YEARS
    amort = hw / (y * 12)
    mrate = maint["rate"] * max(0, y - maint["warranty"]) / y
    return {"sites": sites, "hw_capex": hw, "power_kw": kw, "iops": iops,
            "maint_rate": maint["rate"], "warranty": maint["warranty"],
            "amortization": amort, "maintenance": hw * mrate / 12,
            "energy": cm.energy_monthly(kw),
            "monthly_total": amort + hw * mrate / 12 + cm.energy_monthly(kw),
            "primary_share": sites["A"]["hw_capex"] / hw if hw > 0 else 1.0,
            "desc": "; ".join(f"site {s}: {v['desc']}" for s, v in sites.items())}


# ==============================================================================
# BOLUM 10 — YEDEKLEME (KB-10)
# ==============================================================================
# Hacim kurali ortak (common_model.backup_volumes); x86 hedefleri on-prem nesne
# depolama ve AWS S3, mainframe ile AYNI fiyat fonksiyonlari (TS7770 uygulanmaz).
# Yazilim: pgBackRest (lisans 0), RMAN (EE'ye dahil; BASIC sikistirma dahil).
# PostgreSQL WAL'inda full-page writes -> log hacmi x WAL_FPW_FACTOR.
# Kisitlar mainframe ile ayni: 8 saatlik pencere; alternatif sitesi olmayan
# topolojide (X1) tam geri yukleme RTO'nun yarisina sigmali.
WAL_FPW_FACTOR = 2.0            # [ASSUME] 1,5 / 2 / 3; K6 ile olculecek
X86_BACKUP_COMPRESSION = 2.0    # [ASSUME] pgBackRest / RMAN BASIC; aralik 1,5-3,0
X86_BACKUP_MAX_MB_S = 5000.0    # [ASSUME] 2 x 25 GbE x %80 (DB dugumunden yedek akisi)
X86_BACKUP_TARGET = "auto"      # "auto" | "cos_onprem" | "aws_s3"


def backup_plan(avg_tps, workload, topology, db, data_tb=None, growth=None, target=None):
    wl = get_workload(workload)
    f = WAL_FPW_FACTOR if db == "postgresql" else 1.0
    ic, logs, daily, restore = cm.backup_volumes(avg_tps, wl.writes, wl.commits, data_tb,
                                                 growth, log_factor=f)
    stored = (ic + logs) / X86_BACKUP_COMPRESSION
    daily_c = daily / X86_BACKUP_COMPRESSION
    restore_c = restore / X86_BACKUP_COMPRESSION
    budget = (topology.rto_minutes / 60.0 * cm.BACKUP_RESTORE_RTO_FRACTION
              if topology.recovery_minutes() == float("inf") else None)
    req = daily_c * 1e6 / (cm.BACKUP_WINDOW_HOURS * 3600.0)
    if budget is not None:
        req = max(req, restore_c * 1e6 / (budget * 3600.0))
    alts = {}
    for t in ("cos_onprem", "aws_s3"):
        a = {"target": t, "stored_tb_per_site": stored, "required_mb_s": req,
             "hybrid": t == "aws_s3"}
        if req > X86_BACKUP_MAX_MB_S:
            a.update(feasible=False, reason="yedek akisi yetmez")
            alts[t] = a
            continue
        if t == "cos_onprem":
            o = cm.onprem_object_store(stored, cm.BACKUP_SITES)
            amort, maint = mf._hw_monthly(o["hw_capex"])     # ayni urun, ayni bakim kurali
            a.update(feasible=True, hw_capex=o["hw_capex"], amortization=amort,
                     maintenance=maint, service=o["service"], power_kw=o["power_kw"],
                     energy=cm.energy_monthly(o["power_kw"]))
        else:
            o = cm.s3_hybrid(stored, daily_c, restore_c, req, cm.BACKUP_RETENTION_WEEKS,
                             cm.BACKUP_RESTORES_PER_YEAR)
            a.update(feasible=True, hw_capex=0.0, amortization=0.0, maintenance=0.0,
                     service=o["service"], power_kw=0.0, energy=0.0, links=o["links"])
        a["monthly_total"] = a["amortization"] + a["maintenance"] + a["energy"] + a["service"]
        alts[t] = a
    want = target or X86_BACKUP_TARGET
    ok = [a for a in alts.values() if a["feasible"]]
    if not ok:
        return None
    best = min(ok, key=lambda a: a["monthly_total"]) if want == "auto" else alts[want]
    if not best.get("feasible"):
        return None
    plan = dict(best)
    plan.update({"image_copy_tb": ic, "log_tb": logs, "restore_tb": restore_c,
                 "restore_hours": cm.transfer_hours(restore_c, X86_BACKUP_MAX_MB_S),
                 "alternatives": alts})
    return plan


# ==============================================================================
# BOLUM 11 — PERSONEL (KB-13) VE URETIM DISI (KB-14)
# ==============================================================================
# P karari: iki tarafta ayni TPS tabanli ortak egri (common_model §12);
# FTE_x86 = FTE_ortak(TPS) x STAFF_RATIO_X86. Ana senaryoda 1,0 (personel
# crossover icin notr); 1,25 ve 2,0 yalnizca duyarlilik (IBM vakalari,
# uretici yanliligi notuyla). STAFF_RATIO_X86 aralik parametresi degildir.
# Personel egrisinin girdisi mainframe kapasite birimidir (PCI esdegeri):
# mf.staff_pci_equivalent ayni bilesim icin cagrilir.
STAFF_RATIO_X86 = 1.0
STAFF_RATIO_SENSITIVITY = (1.25, 2.0)

# N karari: x86 uretim disi 0 / 0,50 / 1,00; 2,0 IBM iddiasi stres senaryosu
# [IBM-EAGLE-2013]. Orta deger: birincil sitede 3 dugum; uretim boyutunda tek
# dugumluk staging ~0,33 + kucuk dev/test ~0,1-0,2 [DERIVED, ASSUME].
NONPROD_FACTOR_X86 = 0.50
X86_NONPROD_STRESS = 2.0        # N karari: IBM iddiasi stres senaryosu (aralikta degil)


def staff_fte(tps, workload, topology):
    pci = mf.staff_pci_equivalent(tps, get_workload(workload).mainframe_profile())
    return cm.staff_fte(pci, topology.code) * STAFF_RATIO_X86


def staff_monthly(tps, workload, topology):
    return staff_fte(tps, workload, topology) * cm.loaded_wage() / 12.0


# ==============================================================================
# BOLUM 12 — BIR YAPILANDIRMANIN DEGERLENDIRILMESI
# ==============================================================================

def _db_capacity_nodes(db, topology, k):
    """Yuku tasimasi gereken dugum sayisi: Patroni 1 (birincil); RAC'ta N+1 ->
    k - 1 dugum tum yuku tasimali (en az 1)."""
    if db == "postgresql":
        return 1
    return max(1, k - 1)


def evaluate(tps, stack, topology, sku, k=1, workload=DEFAULT_WORKLOAD, latency_s=None,
             percentile=0.99, data_tb=None, growth=None, avg_tps=None, availability=None,
             rpo_seconds=None, rto_minutes=None, staff_tps=None):
    """Tek bir (yigin, topoloji, SKU, RAC dugum sayisi) yapilandirmasinin aylik
    maliyeti. Kisitlardan biri saglanmazsa None."""
    db = stack.db
    if not topology.supports(db):
        return None
    if db == "postgresql":
        k = 1
    if availability is not None and topology.availability(db, k) < availability:
        return None
    if rpo_seconds is not None and topology.rpo_seconds(db) > rpo_seconds:
        return None
    if rto_minutes is not None and topology.rto_minutes > rto_minutes:
        return None
    # --- kapasite ve latency ---
    cap_nodes = _db_capacity_nodes(db, topology, k)
    raw = cluster_raw_tps(sku, stack, cap_nodes, workload)
    per_core = raw / (cap_nodes * sku.cores)
    d_fixed = fixed_delay_s(topology, db, workload)
    rho_max = max_utilization(per_core, d_fixed, latency_s, percentile)
    if raw * rho_max < tps:
        return None
    # --- dugum gruplari ---
    nodes = topology.db_nodes(db, k)
    db_busy_cores = tps / tps_per_core(sku, stack, workload)
    app_sku, app_n, app_need = app_hosts(db_busy_cores, stack, workload)
    groups = [{"role": "db", "site": s, "sku": sku, "n": n} for s, n in nodes.items()]
    groups += [{"role": "app", "site": s, "sku": app_sku, "n": app_n} for s in nodes]
    if topology.has_witness():
        groups.append({"role": "witness", "site": "C", "sku": X86_CATALOG[0], "n": 1})
    # --- storage ve yedek ---
    splan = storage_plan(tps, workload, topology, db, k, data_tb, growth)
    if splan is None:
        return None
    avg = tps / cm.STATIC_PEAK_TO_AVG if avg_tps is None else avg_tps
    bplan = backup_plan(avg, workload, topology, db, data_tb, growth)
    if bplan is None:
        return None
    # --- grup basina maliyet ---
    subs = platform_subscriptions(stack, groups)
    y12 = X86_AMORTIZATION_YEARS * 12
    for g, s in zip(groups, subs):
        g["hw_capex"] = g["n"] * node_net_capex(g["sku"])
        g["kw"] = g["n"] * node_power_kw(g["sku"])
        g["sub_year"] = s
        g["oracle_net"] = 0.0
        g["pg_support_year"] = 0.0
        if g["role"] == "db":
            if db == "oracle":
                rac = g["n"] > 1
                g["oracle_net"] = g["n"] * oracle_license_net(g["sku"].cores, topology, rac)
            else:
                g["pg_support_year"] = g["n"] * g["sku"].cores * PG_SUPPORT_USD_PER_CORE_YEAR
        g["software_m"] = ((sum(s.values()) + g["pg_support_year"]) / 12.0
                           + g["oracle_net"] / y12 + g["oracle_net"] * ORACLE_SUPPORT_RATE / 12.0)
        g["hw_m"] = g["hw_capex"] / y12
        g["maint_m"] = g["hw_capex"] * X86_MAINT_RATE_ANNUAL * maintenance_factor() / 12.0
        g["energy_m"] = cm.energy_monthly(g["kw"])
    sum_g = lambda key, pred=lambda g: True: sum(g[key] for g in groups if pred(g))
    software = sum_g("software_m")
    hardware = sum_g("hw_m")
    maintenance = sum_g("maint_m")
    energy = sum_g("energy_m")
    staff = staff_monthly(tps if staff_tps is None else staff_tps, workload, topology)
    prim = lambda g: g["site"] == "A"
    nonprod = cm.nonprod_cost(NONPROD_FACTOR_X86, {
        "software": sum_g("software_m", prim), "compute_hw": sum_g("hw_m", prim),
        "compute_maint": sum_g("maint_m", prim), "compute_energy": sum_g("energy_m", prim),
        "storage_primary": ((splan["amortization"] + splan["maintenance"]) * splan["primary_share"]
                            + cm.energy_monthly(splan["sites"]["A"]["power_kw"]))})
    total = (software + hardware + maintenance + energy + staff + splan["monthly_total"]
             + bplan["monthly_total"] + nonprod)
    site_cost = lambda pred: sum(g["software_m"] + g["hw_m"] + g["maint_m"] + g["energy_m"]
                                 for g in groups if pred(g))
    dr = site_cost(lambda g: g["site"] != "A") + splan["monthly_total"] * (1 - splan["primary_share"])
    app = site_cost(lambda g: g["role"] == "app")
    oracle_m = sum(g["oracle_net"] / y12 + g["oracle_net"] * ORACLE_SUPPORT_RATE / 12.0
                   for g in groups)
    rho = tps / raw
    return {
        "stack": stack, "topology": topology, "sku": sku, "k": k, "groups": groups,
        "software": software, "hardware_amort": hardware, "maintenance": maintenance,
        "energy": energy, "staff": staff, "storage": splan["monthly_total"],
        "backup": bplan["monthly_total"], "nonprod": nonprod, "total": total,
        "storage_plan": splan, "backup_plan": bplan,
        "rho": rho, "rho_max": rho_max, "raw_tps": raw, "per_core_tps": per_core,
        "d_fixed_s": d_fixed, "app_cores": app_need, "app_sku": app_sku, "app_hosts": app_n,
        "dr_share": dr / total if total else 0.0, "app_share": app / total if total else 0.0,
        "oracle_monthly": oracle_m,
        "latency_s": (latency_at(per_core, d_fixed, rho, percentile) if rho < 1 else None),
        "availability": topology.availability(db, k),
        "hosts": sum(g["n"] for g in groups),
        "physical_cores": sum(g["n"] * g["sku"].cores for g in groups),
    }


def _candidates(tps, stack, topology, workload, **kw):
    """Bir (yigin, topoloji) icin en ucuz feasible yapilandirma. Patroni'de
    maliyet SKU ile monoton -> ilk feasible SKU; RAC'ta SKU x dugum sayisi."""
    if not topology.supports(stack.db):
        return None
    best = None
    for sku in catalog():
        ks = [1] if stack.db == "postgresql" else range(2, RAC_MAX_NODES + 1)
        for k in ks:
            r = evaluate(tps, stack, topology, sku, k, workload, **kw)
            if r is None:
                continue
            if best is None or r["total"] < best["total"]:
                best = r
            break       # bu SKU'da daha fazla dugum daha pahali
        if stack.db == "postgresql" and best is not None:
            break
    return best


def solve(tps, availability=0.999, workload=DEFAULT_WORKLOAD, latency_ms=None,
          latency_percentile=99, data_tb=None, data_growth=None, rpo_seconds=None,
          rto_minutes=None, stacks=None, topologies=None, verbose=True, avg_tps=None,
          staff_tps=None):
    """En ucuz feasible x86 yapilandirmasi. Donus: en iyi sonuc sozlugu (ya da
    None); 'by_stack' yigin basina en iyiyi, 'by_topology' topoloji basina tasir."""
    if not tps > 0:
        raise ValueError("tps pozitif olmali")
    if not 0.0 < availability < 1.0:
        raise ValueError("availability 0 ile 1 arasinda olmali")
    lat_s = latency_ms / 1000.0 if latency_ms is not None else None
    kw = dict(latency_s=lat_s, percentile=latency_percentile / 100.0, data_tb=data_tb,
              growth=data_growth, avg_tps=avg_tps, availability=availability,
              rpo_seconds=rpo_seconds, rto_minutes=rto_minutes, staff_tps=staff_tps)
    by_stack, by_topo = {}, {}
    for st in (stacks or STACKS):
        for topo in (topologies or X86_TOPOLOGIES):
            r = _candidates(tps, st, topo, workload, **kw)
            if r is None:
                continue
            if st.code not in by_stack or r["total"] < by_stack[st.code]["total"]:
                by_stack[st.code] = r
            if topo.code not in by_topo or r["total"] < by_topo[topo.code]["total"]:
                by_topo[topo.code] = r
    if not by_stack:
        if verbose:
            print("  -> SONUC: infeasible (hicbir yigin / topoloji kisitlari saglamiyor)\n")
        return None
    best = dict(min(by_stack.values(), key=lambda r: r["total"]))
    best["by_stack"] = by_stack
    best["by_topology"] = by_topo
    best["target_availability"] = availability
    if verbose:
        print_solution(best, tps, workload, latency_ms, latency_percentile)
    return best


def print_solution(r, tps, workload, latency_ms=None, latency_percentile=99):
    wl = get_workload(workload)
    st, topo, sku = r["stack"], r["topology"], r["sku"]
    print(f"  Girdi: {tps:,.0f} TPS | is yuku={wl.name} | uptime hedefi={r['target_availability']:.6%} "
          f"| fiyat donemi={cm.PRICE_EPOCH}")
    print(f"         latency hedefi: " + (f"p{latency_percentile} <= {latency_ms:g} ms"
          if latency_ms is not None else f"yok -> x86 kullanim tavani %{X86_UTIL_CEILING * 100:.0f}"))
    print(f"     is yuku profili: {wl}")
    print(f"     kopru: {X86_TPS_PER_SPECINT_CORE:.1f} TPS / SPECint / cekirdek x "
          f"{X86_SPECINT_PER_CORE:.2f} SPECint/cekirdek")
    print(f"  -> SECILEN YIGIN: {st}")
    a_lo, a_hi = topo.availability_range(st.db, r["k"])
    print(f"  -> SECILEN TOPOLOJI: {topo} [{topo.pattern}; "
          f"{topo.oracle_tier if st.db == 'oracle' else 'Patroni: ' + topo.patroni}]")
    print(f"     availability: {r['availability']:.5%} (aralik {a_lo:.5%} - {a_hi:.5%}) | "
          f"RPO {topo.rpo_seconds(st.db):g} s, RTO {topo.rto_minutes:g} dk")
    nodes = topo.db_nodes(st.db, r["k"])
    extra = " (ekstrapolasyon)" if sku.extrapolated else ""
    print(f"  -> VERITABANI DUGUMU: {sku}{extra}; site basina {nodes}"
          + (f"; RAC {r['k']} dugum (N+1)" if st.db == "oracle" else "; tek yazici (birincil)"))
    print(f"     cekirdek basina {r['per_core_tps']:,.0f} TPS; yuku tasiyan ham verim "
          f"{r['raw_tps']:,.0f} TPS; kullanim %{r['rho'] * 100:.1f} (tavan %{r['rho_max'] * 100:.1f})")
    if r["latency_s"] is not None:
        print(f"     sabit gecikme (ag + I/O + replikasyon) {r['d_fixed_s'] * 1000:.2f} ms; "
              f"p{latency_percentile} ~ {r['latency_s'] * 1000:.2f} ms"
              + (f" (hedef {latency_ms:g} ms)" if latency_ms is not None else ""))
    print(f"     uygulama katmani: {r['app_cores']:.1f} mesgul cekirdek -> site basina "
          f"{r['app_hosts']} x {r['app_sku'].code}")
    print(f"     toplam {r['hosts']} fiziksel sunucu, {r['physical_cores']} cekirdek")
    print(f"     AYLIK maliyet: ${r['total']:,.0f}  (${r['total'] / tps:,.2f}/TPS)")
    print(f"       yazilim/abonelik: ${r['software']:,.0f}"
          + (f"  (Oracle ${r['oracle_monthly']:,.0f})" if st.db == "oracle" else ""))
    print(f"       donanim:  ${r['hardware_amort']:,.0f}   bakim: ${r['maintenance']:,.0f}   "
          f"enerji: ${r['energy']:,.0f}")
    print(f"       personel: ${r['staff']:,.0f}  "
          f"({staff_fte(tps, workload, topo):.1f} FTE, oran {STAFF_RATIO_X86:g})")
    print(f"       storage:  ${r['storage']:,.0f}  ({r['storage_plan']['desc']})")
    b = r["backup_plan"]
    print(f"       yedekleme: ${r['backup']:,.0f}  ({b['target']}, site basina "
          f"{b['stored_tb_per_site']:,.0f} TB)")
    print(f"       uretim disi: ${r['nonprod']:,.0f}  (NONPROD_FACTOR_X86={NONPROD_FACTOR_X86:g})")
    print(f"     DR payi %{r['dr_share'] * 100:.1f}; uygulama katmani payi %{r['app_share'] * 100:.1f}")
    print(f"     fiyat modu: {cm.price_mode_label()}")
    print("  Yigin secim motoru (yigin basina en ucuz):")
    for code, x in sorted(r["by_stack"].items(), key=lambda kv: kv[1]["total"]):
        print(f"     ${x['total']:>11,.0f}  {code:<42} {x['topology'].code} {x['sku'].code}"
              + (f" k={x['k']}" if x["stack"].db == "oracle" else ""))
    print()


# ==============================================================================
# BOLUM 13 — ARALIK VE TORNADO (KB-18)
# ==============================================================================
# low = x86 lehine uc. Ortak parametrelerde low iki tarafi birlikte ucuzlatir.
# Personel orani (STAFF_RATIO_X86) araliga girmez (KB-13). Mainframe'e ozgu
# bilesim parametreleri (CPU_US_PER_SQL_READ ...) x86'da yalnizca personel
# egrisinin girdisini etkiler ve burada mid'de kalir; iki taraf karsilastirma
# katmaninda (compare) ayni degerlerle cozulur.
X86_RANGE_PARAMETERS = [
    ("X86_TPS_PER_SPECINT_CORE", 120.0, X86_TPS_PER_SPECINT_CORE, 60.0,
     "x86 kopru: TPS / SPECint / cekirdek (K)"),
    ("X86_SCALING_LEVEL", "low", "mid", "high", "Dugum ici olceklenme ussu B_X86 (0,80-1,00)"),
    ("VIRT_LEVEL", "low", "mid", "high", "Sanallastirma ek yuku"),
    ("CONTAINER_OVERHEAD", 0.0, 0.02, 0.05, "Konteyner ek yuku"),
    ("ORACLE_THROUGHPUT_FACTOR", 1.30, 1.00, 0.80, "Oracle / PostgreSQL verim (kalibre edilemez)"),
    ("RAC_SCALING_EFFICIENCY", 0.95, 0.90, 0.80, "RAC olceklenme verimi"),
    ("X86_UTIL_CEILING", 0.90, 0.70, 0.50, "x86 kullanim tavani (U)"),
    ("X86_LATENCY_LEVEL", "low", "mid", "high", "Ag gidis-donus suresi (yalnizca latency hedefiyle)"),
    ("X86_STORED_PROCEDURES", True, False, False, "Islem basina gidis-donus: 1 (sakli yordam) / ifade sayisi"),
    ("T_SAN_READ_S", 150e-6, 250e-6, 400e-6, "SAN okuma servis suresi (yalnizca latency hedefiyle)"),
    ("COMPONENT_PRICE_LEVEL", "low", "mid", "high", "DRAM / NVMe fiyati (secili donem, E)"),
    ("X86_PLATFORM_COST", 8000.0, 12000.0, 18000.0, "Sunucu sasi/platform listesi, USD"),
    ("X86_HW_DISCOUNT", 0.50, 0.35, 0.20, "Sunucu liste indirimi"),
    ("X86_POWER_CONFIG_UPLIFT", 1.1, 1.25, 1.4, "Dugum gucu yapilandirma carpani"),
    ("VSPHERE_USD_PER_CORE_YEAR", 100.0, 150.0, 350.0, "vSphere USD/cekirdek/yil"),
    ("OVE_USD_PER_NODE_YEAR", 6000.0, 8000.0, 10000.0, "OpenShift Virt. Engine USD/dugum/yil"),
    ("OCP_USD_PER_COREPAIR_YEAR", 2000.0, 3000.0, 4200.0, "OpenShift USD/cekirdek cifti/yil"),
    ("ORACLE_DISCOUNT", 0.60, 0.45, 0.20, "Oracle liste indirimi"),
    ("PG_SUPPORT_USD_PER_CORE_YEAR", 0.0, 500.0, 1500.0, "PostgreSQL ticari destek USD/cekirdek/yil"),
    ("AFA_LIST_USD_PER_EFF_TB", 140.0, 270.0, 400.0, "AFA liste USD/etkin TB"),
    ("AFA_DATA_REDUCTION", 1.5, 2.5, 4.0, "AFA teklifindeki veri azaltimi (geri cevirme)"),
    ("PG_BLOAT_FACTOR", 1.1, 1.3, 1.6, "PostgreSQL DB ek yuku (MVCC, WAL)"),
    ("NODE_EVENT_LEVEL", "low", "mid", "high", "Dugum arizasi sikligi ve failover"),
    ("SITE_EVENT_LEVEL", "low", "mid", "high", "Saha olayi sikligi ve suresi (ortak)"),
    ("X86_RECOVERY_LEVEL", "low", "mid", "high", "Kurtarma suresi (RTO)"),
    ("X86_PLANNED_LEVEL", "low", "mid", "high", "Planli kesinti ve yama switchover'i"),
    ("STAFF_SCENARIO", "low", "mid", "high", "Personel egrisi + taban ekip (ortak)"),
    ("WAGE_LEVEL", "low", "mid", "high", "Yuklu personel ucreti (ortak)"),
    ("RANGE_READ_WEIGHT", 3.4, 3.65, 3.9, "Aralik / nokta okuma orani (ortak, F)"),
    ("BP_HIT_RATIO", 0.99, 0.95, 0.90, "Tampon havuzu isabeti (ortak; I/O, gecikme)"),
    ("BACKUP_RETENTION_WEEKS", 2, 4, 8, "Yedek saklama suresi, hafta (ortak)"),
    ("X86_BACKUP_COMPRESSION", 3.0, 2.0, 1.5, "Yedek sikistirma (pgBackRest / RMAN)"),
    ("WAL_FPW_FACTOR", 1.5, 2.0, 3.0, "PostgreSQL WAL full-page write carpani"),
    ("COS_HW_USD_PER_TB", 60.0, 100.0, 200.0, "On-prem nesne depolama donanimi (ortak)"),
    ("COS_SW_USD_PER_TB_MONTH", 0.0, 5.0, 10.0, "On-prem nesne depolama aboneligi (ortak)"),
    ("NONPROD_FACTOR_X86", 0.0, 0.50, 1.00, "x86 uretim disi ortamlar (N)"),
]


def scenario_values_for(level, params):
    i = cm.RANGE_LEVELS.index(level)
    return {r[0]: r[1 + i] for r in cm.unpinned(params)}


def solve_range(tps, **kw):
    out = {}
    for level in cm.RANGE_LEVELS:
        with use_values(scenario_values_for(level, X86_RANGE_PARAMETERS)):
            out[level] = solve(tps, verbose=False, **kw)
    return out


def range_tornado(tps, params=None, **kw):
    params = params or X86_RANGE_PARAMETERS
    mid = scenario_values_for("mid", params)
    rows = []
    for name, lo, _m, hi, desc in cm.unpinned(params):
        tot = []
        for v in (lo, hi):
            vals = dict(mid)
            vals[name] = v
            with use_values(vals):
                r = solve(tps, verbose=False, **kw)
            tot.append(None if r is None else r["total"])
        rows.append((name, desc, tot[0], tot[1]))
    rows.sort(key=lambda r: -abs((r[3] or 0) - (r[2] or 0)))
    return rows


def print_range(tps, **kw):
    rng = solve_range(tps, **kw)
    print(f"\nARALIK (x86 aylik toplam, {tps:,.0f} TPS):")
    for level in cm.RANGE_LEVELS:
        x = rng[level]
        if x is None:
            print(f"  {level:<5} infeasible")
            continue
        print(f"  {level:<5} ${x['total']:>12,.0f}  (${x['total'] / tps:,.2f}/TPS)  "
              f"{x['stack']} {x['topology'].code} {x['sku'].code}  personel ${x['staff']:,.0f}")
    print("  Tek-parametre salinimi (digerleri mid):")
    for name, desc, lo, hi in range_tornado(tps, **kw):
        if lo is None or hi is None:
            print(f"    {desc:<46} infeasible ucu var ({lo}, {hi})")
            continue
        print(f"    {desc:<46} ${lo:>12,.0f} .. ${hi:>12,.0f}")


# ==============================================================================
# BOLUM 14 — 5 YILLIK NAKIT AKISI VE NPV (KB-16)
# ==============================================================================
# Kurallar ortak (common_model §8): 5 yil, capex yil basinda, opex yil sonunda,
# kalan deger 0; artis siniflari: abonelik ve Oracle destegi SW_PRICE_ESCALATION,
# bakim HW_SERVICE_ESCALATION, personel WAGE_ESCALATION, enerji ENERGY_ESCALATION.
# Yigin ve topoloji 1. yilda secilir ve sabit kalir. Kapasite yalnizca yukselir:
# x86'da yukseltme = dugum buyutme (ayni platformda CPU degisimi + bellek eki;
# eski CPU'lar geri kazanilmaz) ya da RAC'ta dugum ekleme. Oracle lisansi
# artan islemci sayisi kadar ek alim. Storage ve yedek STORAGE_PLANNING_YEARS'lik
# dongulerle alinir (mainframe ile ayni). Sunucu bakimi her alimin garantisinden
# sonra baslar. Tutarlilik: r = 0, buyume 0, artis 0 iken NPV = 60 x statik aylik.
X86_NPV_RANGE_PARAMETERS = X86_RANGE_PARAMETERS + cm.NPV_COMMON_RANGE_PARAMETERS


def _upgrade_ok(prev, r):
    if prev is None:
        return True
    return r["sku"].cores >= prev["sku"].cores and r["k"] >= prev["k"]


def _year_config(load, stack, topo, workload, prev, kw):
    best = None
    for sku in catalog():
        if prev is not None and sku.cores < prev["sku"].cores:
            continue
        ks = [1] if stack.db == "postgresql" else range(max(2, prev["k"] if prev else 2),
                                                          RAC_MAX_NODES + 1)
        for k in ks:
            r = evaluate(load, stack, topo, sku, k, workload, **kw)
            if r is None:
                continue
            if best is None or r["total"] < best["total"]:
                best = r
            break
        if stack.db == "postgresql" and best is not None:
            break
    return best


def _group_key(g):
    return (g["role"], g["site"])


def solve_npv(tps, availability=0.999, workload=DEFAULT_WORKLOAD, latency_ms=None,
              latency_percentile=99, data_tb=None, data_growth=None, rpo_seconds=None,
              rto_minutes=None, tps_growth=None, years=None, discount_rate=None, stacks=None):
    """En dusuk NPV'li (yigin, topoloji) yolu. Yigin ve topoloji 1. yilda secilir ve
    5 yil sabit kalir; secim, butun yolu feasible tasiyan adaylar arasindan yapilir."""
    g = cm.NPV_TPS_GROWTH if tps_growth is None else tps_growth
    years = cm.NPV_YEARS if years is None else years
    rate = cm.NPV_DISCOUNT_RATE if discount_rate is None else discount_rate
    lat_s = latency_ms / 1000.0 if latency_ms is not None else None
    best = None
    for stack in (stacks or STACKS):
        for topo in X86_TOPOLOGIES:
            if not topo.supports(stack.db):
                continue
            res = _npv_path(tps, stack, topo, workload, lat_s, latency_percentile, data_tb,
                            data_growth, availability, rpo_seconds, rto_minutes, g, years, rate)
            if res is not None and (best is None or res["npv"] < best["npv"]):
                best = res
    return best


def _npv_path(tps, stack, topo, workload, lat_s, latency_percentile, data_tb, data_growth,
              availability, rpo_seconds, rto_minutes, g, years, rate):
    """Sabit (yigin, topoloji) icin 5 yillik yol; herhangi bir yil infeasible ise None.
    Planlayici yigini butun yolu tasiyabilecek adaylar arasindan secer (solve_npv)."""
    data0 = cm.DEFAULT_DATA_VOLUME_TB if data_tb is None else data_tb
    dg = cm.DEFAULT_DATA_GROWTH if data_growth is None else data_growth
    loads = [tps * (1.0 + g) ** (y - 1) for y in range(1, years + 1)]
    kw = dict(latency_s=lat_s, percentile=latency_percentile / 100.0, data_tb=data_tb,
              growth=data_growth, availability=availability, rpo_seconds=rpo_seconds,
              rto_minutes=rto_minutes)
    configs, prev = [], None
    for load in loads:
        c = _year_config(load, stack, topo, workload, prev, kw)
        if c is None:
            return None
        configs.append(c)
        prev = c
    # storage + yedek donguleri
    cycle = max(1, cm.STORAGE_PLANNING_YEARS)
    lay = []
    s_cum = b_cum = 0.0
    cur = None
    for y in range(1, years + 1):
        t = y - 1
        add_s = add_b = 0.0
        if t % cycle == 0:
            h = min(cycle, years - t)
            d_t = data0 * (1.0 + dg) ** t
            c = configs[min(t + h, years) - 1]
            with use_values({"STORAGE_PLANNING_YEARS": h}):
                sp = storage_plan(max(loads[t:t + h]), workload, topo, stack.db, c["k"], d_t, dg)
                bp = backup_plan(max(loads[t:t + h]) / cm.STATIC_PEAK_TO_AVG, workload, topo,
                                 stack.db, d_t, dg, target=cur["bp"]["target"] if cur else None)
            if sp is None or bp is None:
                return None
            add_s = max(0.0, sp["hw_capex"] - s_cum)
            add_b = max(0.0, bp.get("hw_capex", 0.0) - b_cum)
            s_cum += add_s
            b_cum += add_b
            cur = {"sp": sp, "bp": bp}
        with use_values({"STORAGE_PLANNING_YEARS": 0}):
            svc = backup_plan(loads[t] / cm.STATIC_PEAK_TO_AVG, workload, topo, stack.db,
                              data0 * (1.0 + dg) ** t, dg, target=cur["bp"]["target"])["service"]
        lay.append({"storage_capex": add_s, "backup_capex": add_b, "s_hw": s_cum, "b_hw": b_cum,
                    "sp": cur["sp"], "bp": cur["bp"], "svc": svc,
                    "kw": cur["sp"]["power_kw"] + cur["bp"]["power_kw"]})

    rows, capex_events = [], []
    inv = {}            # grup -> {"sku", "n"}
    buys = []           # (yil, net deger) sunucu alimlari (bakim icin)
    s_buys = []         # (yil, deger) storage alimlari
    b_buys = []
    ora_cum = 0.0
    for y, (c, load, ly) in enumerate(zip(configs, loads, lay), start=1):
        hw_capex = 0.0
        ora_add = 0.0
        for gr in c["groups"]:
            key = _group_key(gr)
            old = inv.get(key)
            unit = node_net_capex(gr["sku"])
            if old is None:
                hw_capex += gr["n"] * unit
            else:
                if gr["sku"].cores > old["sku"].cores:      # CPU degisimi + bellek eki
                    cpu = (gr["sku"].cores * X86_CPU_LIST_USD_PER_CORE) * (1.0 - X86_HW_DISCOUNT)
                    mem = max(0.0, node_memory_gb(gr["sku"]) - node_memory_gb(old["sku"])) \
                        * cm.component_price("dram_usd_per_gb")
                    hw_capex += old["n"] * (cpu + mem)
                hw_capex += max(0, gr["n"] - old["n"]) * unit
            inv[key] = {"sku": gr["sku"] if old is None or gr["sku"].cores >= old["sku"].cores
                        else old["sku"], "n": max(gr["n"], old["n"] if old else 0)}
        ora_now = sum(gr["oracle_net"] for gr in c["groups"])
        ora_add = max(0.0, ora_now - ora_cum)
        ora_cum = max(ora_cum, ora_now)
        buys.append((y, hw_capex))
        s_buys.append((y, ly["storage_capex"]))
        b_buys.append((y, ly["backup_capex"]))
        sub_year = sum(sum(gr["sub_year"].values()) + gr["pg_support_year"] for gr in c["groups"])
        maint = sum(v for (t, v) in buys if y > t - 1 + X86_WARRANTY_YEARS) * X86_MAINT_RATE_ANNUAL
        sp = ly["sp"]
        s_maint = sum(v for (t, v) in s_buys if y > t - 1 + sp["warranty"]) * sp["maint_rate"]
        b_maint = sum(v for (t, v) in b_buys if y > t - 1 + mf.STORAGE_WARRANTY_YEARS) \
            * mf.STORAGE_MAINT_RATE_ANNUAL
        kw_tot = sum(gr["kw"] for gr in c["groups"]) + ly["kw"]
        e = cm.ELECTRICITY_USD_PER_KWH * cm.HOURS_PER_YEAR * cm.esc(cm.ENERGY_ESCALATION, y)
        sw_e = cm.esc(cm.SW_PRICE_ESCALATION, y)
        hw_e = cm.esc(cm.HW_SERVICE_ESCALATION, y)
        opex = {
            "software": sub_year * sw_e,
            "oracle_support": ora_cum * ORACLE_SUPPORT_RATE * sw_e,
            "staff": 12 * c["staff"] * cm.esc(cm.WAGE_ESCALATION, y),
            "maintenance": maint * hw_e,
            "storage_maint": (s_maint + b_maint) * hw_e,
            "backup_service": 12 * ly["svc"] * (1.0 if ly["bp"]["target"] == "aws_s3" else hw_e),
            "energy": kw_tot * e,
        }
        capex = {"hardware": hw_capex, "oracle_license": ora_add,
                 "storage": ly["storage_capex"], "backup": ly["backup_capex"]}
        if NONPROD_FACTOR_X86 > 0:   # birincil site payi (KB-14 kurali)
            hw_a = sum(gr["n"] * node_net_capex(gr["sku"]) for gr in c["groups"] if gr["site"] == "A")
            hw_all = sum(gr["n"] * node_net_capex(gr["sku"]) for gr in c["groups"])
            fa = hw_a / hw_all if hw_all else 1.0
            sw_a = sum(sum(gr["sub_year"].values()) + gr["pg_support_year"]
                       for gr in c["groups"] if gr["site"] == "A")
            ora_a = sum(gr["oracle_net"] for gr in c["groups"] if gr["site"] == "A")
            ora_fa = ora_a / ora_now if ora_now else 1.0
            kw_a = sum(gr["kw"] for gr in c["groups"] if gr["site"] == "A")
            ps = sp["primary_share"]
            capex["nonprod"] = cm.nonprod_cost(NONPROD_FACTOR_X86, {
                "software": ora_add * ora_fa, "compute_hw": hw_capex * fa, "compute_maint": 0.0,
                "compute_energy": 0.0, "storage_primary": ly["storage_capex"] * ps})
            opex["nonprod"] = cm.nonprod_cost(NONPROD_FACTOR_X86, {
                "software": sw_a * sw_e + ora_cum * ora_fa * ORACLE_SUPPORT_RATE * sw_e,
                "compute_hw": 0.0, "compute_maint": maint * fa * hw_e,
                "compute_energy": kw_a * e,
                "storage_primary": s_maint * ps * hw_e + sp["sites"]["A"]["power_kw"] * e})
        for v in capex.values():
            if v:
                capex_events.append((y - 1, v))
        rows.append({"year": y, "tps": load, "config": c, "tier": c["sku"],
                     "capex_items": capex, "opex_items": opex,
                     "capex": sum(capex.values()), "opex": sum(opex.values())})
    return cm.finish_npv(rows, rate, years, loads, capex_events, X86_AMORTIZATION_YEARS,
                         {"mode": "static", "stack": stack, "topology": topo, "tps_growth": g})


def solve_npv_range(tps, **kw):
    out = {}
    for level in cm.RANGE_LEVELS:
        with use_values(scenario_values_for(level, X86_NPV_RANGE_PARAMETERS)):
            out[level] = solve_npv(tps, **kw)
    return out


NPV_ITEM_LABELS = {
    "hardware": "sunucu alimi (DB + uygulama + tanik)", "oracle_license": "Oracle lisans alimi",
    "storage": "veri storage alimi (NVMe / AFA)", "backup": "yedek alimi (nesne depolama)",
    "software": "abonelikler (hipervizor, RHEL, OpenShift, PG destek)",
    "oracle_support": "Oracle destegi (%22)", "staff": "personel", "maintenance": "sunucu bakimi",
    "storage_maint": "storage + yedek bakimi", "backup_service": "yedek hizmeti",
    "energy": "enerji", "nonprod": "uretim disi ortamlar", "residual": "kalan deger",
}


def print_npv(res, title=""):
    if res is None:
        print("  NPV: infeasible")
        return
    print(f"\nx86 NPV {title}| {res['stack']} | {res['topology'].code} | iskonto "
          f"%{res['discount_rate'] * 100:.1f} | TPS buyumesi %{res['tps_growth'] * 100:.0f}/yil")
    print("  yil |      TPS | dugum       |      capex |       opex |   bugunku deger")
    for r in res["years"]:
        c = r["config"]
        print(f"  {r['year']:>3} | {r['tps']:>8,.0f} | {c['sku'].code:<6} k={c['k']:<3} | "
              f"${r['capex']:>9,.0f} | ${r['opex']:>9,.0f} | ${r['pv']:>13,.0f}")
    print(f"  NPV: ${res['npv']:,.0f}  (yillik esdeger ${res['eac']:,.0f})")
    if res["levelized_per_tps_month"] is not None:
        print(f"  seviyelendirilmis maliyet: ${res['levelized_per_tps_month']:,.2f} / TPS / ay")
    for k, v in sorted(res["items"].items(), key=lambda kv: -abs(kv[1])):
        if v:
            print(f"    {NPV_ITEM_LABELS.get(k, k):<52} ${v:>13,.0f}  (%{v / res['npv'] * 100:4.1f})")


# ==============================================================================
# BOLUM 15 — YILLIK MOD (CoD karsiligi yok, KB-11)
# ==============================================================================
# On-prem x86'da gecici kapasite / tuketim fiyatlamasi yoktur: kapasite yilin
# tepe saatine gore kurulur, lisans kurulu cekirdekten odenir. Yillik maliyet =
# 12 x (tepe yukte aylik), log hacmi yillik ortalamadan; personel tepe TPS'ten
# (mainframe yillik moduyla ayni kural).

def solve_yearly(preset_name=None, yearly_avg_tps=10000, peak_avg_ratio=None, peak_days=None,
                 verbose=True, **kw):
    prof = mf.generate_hourly_profile(preset_name, yearly_avg_tps, peak_avg_ratio, peak_days)
    peak, avg = max(prof), sum(prof) / len(prof)
    r = solve(peak, verbose=False, avg_tps=avg, **kw)
    if r is None:
        return None
    r = dict(r)
    r.update({"peak_tps": peak, "avg_tps": avg, "yearly_total": 12 * r["total"]})
    if verbose:
        print(f"  Workload: {preset_name or 'custom'} | ortalama {avg:,.0f} TPS | tepe {peak:,.0f} TPS")
        print(f"  {r['stack']} {r['topology'].code} {r['sku'].code} k={r['k']}")
        print(f"  YILLIK TOPLAM: ${r['yearly_total']:,.0f}  (tepeye gore kurulu; CoD yok)")
    return r


# ==============================================================================
# BOLUM 16 — KARSILASTIRMA (KB-13, KB-18)
# ==============================================================================
# Ayni girdi ve ayni parametre degerleriyle iki platform. Basabas personel orani:
# x86 toplamini mainframe toplamina esitleyen STAFF_RATIO_X86 (iki yigin da
# yeniden optimize edilir; ikiye bolme). Personel haric TCO ek gorunumdur.

def compare(tps, availability=0.999, workload=DEFAULT_WORKLOAD, latency_ms=None,
            latency_percentile=99, data_tb=None, data_growth=None, rpo_seconds=None,
            rto_minutes=None, stacks=None):
    wl = get_workload(workload)
    common = dict(availability=availability, latency_ms=latency_ms,
                  latency_percentile=latency_percentile, data_tb=data_tb,
                  data_growth=data_growth, rpo_seconds=rpo_seconds, rto_minutes=rto_minutes)
    m = mf.solve(tps, workload=wl.mainframe_profile(), verbose=False, **common)
    x = solve(tps, workload=wl, verbose=False, stacks=stacks, **common)
    if m is None or x is None:
        return {"mainframe": m, "x86": x}
    m_total = m[2]["total"]

    def x_total(ratio):
        with use_values({"STAFF_RATIO_X86": ratio}):
            r = solve(tps, workload=wl, verbose=False, stacks=stacks, **common)
        return r["total"]

    out = {"mainframe": m, "x86": x, "mf_total": m_total, "x86_total": x["total"],
           "mf_excl_staff": m_total - m[2]["staff"], "x86_excl_staff": x["total"] - x["staff"]}
    out["sensitivity"] = {r: x_total(r) for r in STAFF_RATIO_SENSITIVITY}
    with use_values({"X86_UTIL_CEILING": X86_UNCONSOLIDATED_CEILING}):
        u = solve(tps, workload=wl, verbose=False, stacks=stacks, **common)
    out["unconsolidated"] = u
    with use_values({"NONPROD_FACTOR_X86": X86_NONPROD_STRESS}):
        out["nonprod_stress"] = x_total(STAFF_RATIO_X86)
    if x_total(0.0) >= m_total:
        out["breakeven_ratio"] = 0.0        # personel 0 olsa bile x86 pahali
    else:
        lo, hi = 0.0, 1.0
        while x_total(hi) < m_total and hi < 1000:
            lo, hi = hi, hi * 2
        for _ in range(40):
            mid = (lo + hi) / 2
            if x_total(mid) < m_total:
                lo = mid
            else:
                hi = mid
        out["breakeven_ratio"] = (lo + hi) / 2
    return out


# Eslestirilmis senaryolar: platforma ozgu parametreler zit uclarda, ortak
# parametreler (common_model'in sahip oldugu adlar) iki tarafta AYNI degerde.
# "low" x86 tablosunda x86 lehine, mainframe tablosunda mainframe lehine uctur.
# Iki platformun kendi kose degerlerini birlikte okumak (mainframe low ile x86
# high) ortak parametreleri iki tarafta celisik degerlere koyardi (ornegin
# personel egrisi bir tarafta low, digerinde high); P karariyla bagdasmaz.
COMPARE_SCENARIOS = (
    ("x86_lehine", "x86'ya ozgu low, mainframe'e ozgu high, ortak mid", "low", "high", "mid"),
    ("orta", "hepsi mid", "mid", "mid", "mid"),
    ("mainframe_lehine", "x86'ya ozgu high, mainframe'e ozgu low, ortak mid", "high", "low", "mid"),
    ("ortak_low", "ortak parametreler low (iki taraf birlikte), ozgu mid", "mid", "mid", "low"),
    ("ortak_high", "ortak parametreler high (iki taraf birlikte), ozgu mid", "mid", "mid", "high"),
)


def paired_values(x86_level, mf_level, common_level):
    common = {k for k in vars(cm) if k.isupper()}
    vals = {"CROSS_BRIDGE_WEIGHTS": "reference"}
    for table, own_level in ((X86_RANGE_PARAMETERS, x86_level), (mf.RANGE_PARAMETERS, mf_level)):
        for row in cm.unpinned(table):
            name = row[0]
            lv = common_level if name in common else own_level
            vals[name] = row[1 + cm.RANGE_LEVELS.index(lv)]
    return vals


def compare_range(tps, **kw):
    out = {}
    for key, _desc, xl, ml, cl in COMPARE_SCENARIOS:
        with use_values(paired_values(xl, ml, cl)):
            out[key] = compare(tps, **kw)
    return out


def print_compare_range(res, tps):
    print(f"\nKARSILASTIRMA ARALIGI ({tps:,.0f} TPS; eslestirilmis senaryolar, KB-18)")
    print("  senaryo            mainframe $/TPS   x86 $/TPS   oran   personel haric oran   basabas personel orani")
    for key, desc, *_ in COMPARE_SCENARIOS:
        c = res[key]
        if c.get("mf_total") is None:
            print(f"  {key:<18} mainframe {'infeasible' if c['mainframe'] is None else 'ok'}, "
                  f"x86 {'infeasible' if c['x86'] is None else 'ok'}")
            continue
        print(f"  {key:<18} {c['mf_total'] / tps:>14,.2f}   {c['x86_total'] / tps:>9,.2f}   "
              f"{c['mf_total'] / c['x86_total']:>4.2f}   {c['mf_excl_staff'] / c['x86_excl_staff']:>19.2f}"
              f"   {c['breakeven_ratio']:>8.2f}")
    for key, desc, *_ in COMPARE_SCENARIOS:
        print(f"    {key}: {desc}")


def print_compare(c, tps):
    m, x = c["mainframe"], c["x86"]
    print(f"\nKARSILASTIRMA ({tps:,.0f} TPS, ayni girdiler, fiyat donemi {cm.PRICE_EPOCH})")
    if m is None or x is None:
        print(f"  mainframe: {'infeasible' if m is None else 'ok'} | x86: "
              f"{'infeasible' if x is None else 'ok'}")
        return
    print(f"  mainframe: ${c['mf_total']:>12,.0f}/ay  (${c['mf_total'] / tps:,.2f}/TPS)  "
          f"{m[1].code} {m[0].model}")
    print(f"  x86:       ${c['x86_total']:>12,.0f}/ay  (${c['x86_total'] / tps:,.2f}/TPS)  "
          f"{x['stack']} {x['topology'].code} {x['sku'].code}")
    print(f"  oran (mainframe / x86): {c['mf_total'] / c['x86_total']:.2f}")
    print(f"  personel haric: mainframe ${c['mf_excl_staff']:,.0f} | x86 ${c['x86_excl_staff']:,.0f} "
          f"(oran {c['mf_excl_staff'] / c['x86_excl_staff']:.2f})")
    for r, v in c["sensitivity"].items():
        print(f"  personel orani {r:g}: x86 ${v:,.0f}/ay (${v / tps:,.2f}/TPS)")
    u = c.get("unconsolidated")
    print(f"  konsolide edilmemis park senaryosu (tavan %{X86_UNCONSOLIDATED_CEILING * 100:.1f}, "
          f"ana aralikta degil): " + ("infeasible" if u is None else
          f"x86 ${u['total']:,.0f}/ay (${u['total'] / tps:,.2f}/TPS), personel haric "
          f"${u['total'] - u['staff']:,.0f}; {u['stack']} {u['topology'].code} {u['sku'].code}"
          + (f" k={u['k']}" if u['stack'].db == 'oracle' else '')))
    print(f"  uretim disi stres senaryosu (NONPROD_FACTOR_X86={X86_NONPROD_STRESS:g}, aralikta degil): "
          f"x86 ${c['nonprod_stress']:,.0f}/ay (${c['nonprod_stress'] / tps:,.2f}/TPS)")
    be = c["breakeven_ratio"]
    if be == 0.0:
        print("  basabas personel orani: yok (x86 personel 0 olsa bile pahali)")
    else:
        print(f"  basabas personel orani: {be:.2f}  (x86 personeli, ayni is yuku icin "
              f"mainframe personelinin {be:.2f} katindan azsa x86 ucuz)")


# ==============================================================================
# BOLUM 17 — KALIBRASYON KONTROLU VE CLI
# ==============================================================================
_REG = [
    ("X86_PLATFORM_COST", "USD liste/dugum", "ASSUME (PCSP-SERVER kaba)", 2026, "X86_PLATFORM_COST",
     "Sunucu sasi/platform"),
    ("X86_CPU_LIST_USD_PER_CORE", "USD/cekirdek", "INTEL-ARK-6548Y", 2024, None, "CPU RCP / cekirdek"),
    ("X86_NIC_HBA_LIST_USD", "USD/dugum", "ASSUME", 2026, None, "NIC / HBA"),
    ("X86_HW_DISCOUNT", "oran", "ASSUME", 2026, "X86_HW_DISCOUNT", "Sunucu liste indirimi"),
    ("VSPHERE_USD_PER_CORE_YEAR", "USD/cekirdek-yil", "ACEMQ-VVF, ACEMQ-RENEW", 2026,
     "VSPHERE_USD_PER_CORE_YEAR", "vSphere Foundation"),
    ("OVE_USD_PER_NODE_YEAR", "USD/dugum-yil", "CDW-OVE", 2026, "OVE_USD_PER_NODE_YEAR",
     "OpenShift Virtualization Engine"),
    ("RHEL_VDC_USD_PER_NODE_YEAR", "USD/dugum-yil", "CCSP-RH", 2025, None, "RHEL for Virtual Datacenters"),
    ("OCP_USD_PER_COREPAIR_YEAR", "USD/2 cekirdek-yil", "SWEXPRESS-OCP, VENDORBENCH-OCP", 2026,
     "OCP_USD_PER_COREPAIR_YEAR", "OpenShift Container Platform (sanal dugum)"),
    ("ORACLE_PRICES", "USD/islemci (liste)", "REDRESS-PL2026, REDRESS-GG", 2026, None,
     "Oracle EE ve secenekleri"),
    ("ORACLE_DISCOUNT", "oran", "OLE-NET2026", 2026, "ORACLE_DISCOUNT", "Oracle liste indirimi"),
    ("PG_SUPPORT_USD_PER_CORE_YEAR", "USD/cekirdek-yil", "ASSUME", 2026,
     "PG_SUPPORT_USD_PER_CORE_YEAR", "PostgreSQL ticari destek"),
    ("AFA_LIST_USD_PER_EFF_TB", "USD/etkin TB (liste)", "VENDORBENCH-AFA", 2026,
     "AFA_LIST_USD_PER_EFF_TB", "All-flash dizi"),
    ("AFA_MIN_LIST_USD", "USD/dizi (liste)", "ASSUME", 2026, None, "AFA giris dizisi"),
]
cm.register_prices(__name__, _REG)


def print_calibration():
    print("=" * 70)
    print("x86 KALIBRASYON KONTROLU")
    print("=" * 70)
    print(f"Kopru capasi [VONNG-PERF]: {_VONNG_QPS:,.0f} QPS / 20 = {_VONNG_TPS:,.0f} TPS, "
          f"{_VONNG_CORES} cekirdek, Cascade Lake {_CASCADE_SPECINT_PER_CORE:.2f} SPECint/cekirdek")
    print(f"  X86_TPS_PER_SPECINT_CORE = {X86_TPS_PER_SPECINT_CORE:.2f}")
    ref = next(s for s in X86_CATALOG if s.cores == 64)
    for st in (STACKS[0], STACKS[2]):
        print(f"  {ref.code} {st}: {tps_per_core(ref, st):,.0f} TPS/cekirdek, dugum ham "
              f"{node_raw_tps(ref, st):,.0f}, tavanda {node_raw_tps(ref, st) * X86_UTIL_CEILING:,.0f}")
    bare = X86_TPS_PER_SPECINT_CORE * X86_SPECINT_PER_CORE
    cp = mf.ZIIP_ENGINE_PCI * mf.TPS_PER_PCI / mf.get_workload("oltp_rw").cpu_weight()   # 3931-701
    print(f"Platformlar arasi kontrol (KB-04): 1 z16 CP (oltp_rw) = {cp:,.0f} TPS; "
          f"R760 cekirdegi (ham, S=1) = {bare:,.0f} TPS -> 1 CP ~ {cp / bare:.2f} cekirdek")
    print("Sunucu fiyat fonksiyonu (net, secili donem):")
    for sku in X86_CATALOG + X86_CATALOG_EXTRAPOLATED:
        print(f"  {sku.code:<7} {node_memory_gb(sku):>5.0f} GB  ${node_net_capex(sku):>9,.0f}  "
              f"{node_power_kw(sku) * 1000:,.0f} W")
    # KB-15 kalibrasyon kontrolu: liste-esdegeri yapilandirma [PCSP-SERVER].
    # Kaynak ($53.250 "amiral" R760 liste fiyati) yapilandirmayi vermedigi icin
    # +/-%20 kontrolu yapilamaz; iki donemin olusturdugu bant yalnizca buyukluk
    # mertebesi kontroludur.
    sku = next(s for s in X86_CATALOG if s.cores == 64)
    band = {}
    for ep in cm.PRICE_EPOCHS:
        with use_values({"PRICE_EPOCH": ep}):
            band[ep] = (node_list_items(sku) + 1024 * cm.component_price("dram_usd_per_gb")
                        + 8 * 3.84 * cm.component_price("nvme_usd_per_tb"))
    print("  KB-15 kontrolu: 2 x 32c, 1 TB bellek, 8 x 3,84 TB NVMe, liste-esdegeri: "
          + ", ".join(f"{ep} ${v:,.0f}" for ep, v in band.items())
          + "; Dell yapilandiricisi 'amiral' R760 $53.250 [PCSP-SERVER] (kaynak yapilandirmayi "
            "vermiyor: +/-%20 kontrolu yapilamaz, yalnizca bant icinde mi)")


def _workload_from_args(args):
    if args.sql_reads is not None or args.sql_writes is not None or args.sql_range_reads is not None:
        return X86Workload("custom", args.sql_reads or 0.0, args.sql_range_reads or 0.0,
                           args.sql_writes or 0.0, 1, "Ozel bilesim", "USER")
    return args.workload


def main(argv=None):
    p = argparse.ArgumentParser(description="Kumelenmis x86 (on-prem) minimum maliyet modeli")
    p.add_argument("--tps", type=float)
    p.add_argument("--availability", type=float, default=0.999)
    p.add_argument("--workload", choices=list(X86_WORKLOADS), default=DEFAULT_WORKLOAD)
    p.add_argument("--sql-reads", type=float, default=None)
    p.add_argument("--sql-range-reads", type=float, default=None)
    p.add_argument("--sql-writes", type=float, default=None)
    p.add_argument("--latency-ms", type=float, default=None)
    p.add_argument("--latency-percentile", type=int, default=99, choices=[50, 90, 95, 99])
    p.add_argument("--data-tb", type=float, default=None)
    p.add_argument("--data-growth", type=float, default=None)
    p.add_argument("--rpo-seconds", type=float, default=None)
    p.add_argument("--rto-minutes", type=float, default=None)
    p.add_argument("--db", choices=DATABASES, default=None, help="yalnizca bu veritabani")
    p.add_argument("--hypervisor", choices=HYPERVISORS, default=None)
    p.add_argument("--placement", choices=PLACEMENTS, default=None)
    p.add_argument("--price-epoch", choices=list(cm.PRICE_EPOCHS), default=None)
    p.add_argument("--allow-extrapolation", action="store_true",
                   help="96 / 128 cekirdekli dugumleri de dene (KB-06 duyarliligi)")
    p.add_argument("--staff-ratio", type=float, default=None, help="STAFF_RATIO_X86 (duyarlilik)")
    p.add_argument("--range", action="store_true")
    p.add_argument("--npv", action="store_true")
    p.add_argument("--tps-growth", type=float, default=None)
    p.add_argument("--discount-rate", type=float, default=None)
    p.add_argument("--years", type=int, default=None)
    p.add_argument("--yearly", action="store_true")
    p.add_argument("--preset", choices=list(mf.WORKLOAD_PRESETS), default=None)
    p.add_argument("--avg-tps", type=float, default=10000)
    p.add_argument("--compare", action="store_true", help="mainframe ile karsilastir (KB-18)")
    p.add_argument("--calibration", action="store_true")
    p.add_argument("--prices", type=str, default=None, metavar="DOSYA")
    p.add_argument("--list-prices", action="store_true")
    p.add_argument("--price-vintages", action="store_true")
    a = p.parse_args(argv)
    mod = sys.modules[__name__]
    if a.price_epoch:
        cm.PRICE_EPOCH = a.price_epoch
    if a.allow_extrapolation:
        mod.ALLOW_EXTRAPOLATION = True
    if a.staff_ratio is not None:
        mod.STAFF_RATIO_X86 = a.staff_ratio
    if a.prices:
        try:
            applied = cm.apply_user_prices(cm.load_price_file(a.prices), _PARAM_MODULES)
        except (OSError, ValueError, KeyError) as e:
            p.error(f"--prices: {e}")
        print(f"Fiyat modu: {cm.price_mode_label()}: {', '.join(applied)}")
    if a.list_prices:
        print(json.dumps(cm.current_prices(_PARAM_MODULES), indent=2, ensure_ascii=False))
        return 0
    if a.price_vintages:
        print(f"Fiyat donemi (emtia bilesenleri): {cm.PRICE_EPOCH}")
        for name, m_, year, src in cm.price_vintage_report(_PARAM_MODULES):
            print(f"  {year}  {name:<30} {m_:<16} {src}")
        return 0
    if a.calibration:
        print_calibration()
        return 0
    stacks = [s for s in STACKS if (a.db is None or s.db == a.db)
              and (a.hypervisor is None or s.hypervisor == a.hypervisor)
              and (a.placement is None or s.placement == a.placement)]
    if not stacks:
        p.error("secilen yigin filtresiyle aday yok")
    wl = _workload_from_args(a)
    common = dict(availability=a.availability, workload=wl, latency_ms=a.latency_ms,
                  latency_percentile=a.latency_percentile, data_tb=a.data_tb,
                  data_growth=a.data_growth, rpo_seconds=a.rpo_seconds, rto_minutes=a.rto_minutes)
    if a.yearly:
        r = solve_yearly(a.preset, a.avg_tps, stacks=stacks, **common)
        return 0 if r else 1
    if a.tps is None:
        p.print_help()
        return 1
    print("=" * 70)
    print("x86 FEASIBILITY MODELI (STATIK)")
    print("=" * 70)
    r = solve(a.tps, stacks=stacks, **common)
    if a.range:
        print_range(a.tps, stacks=stacks, **common)
    if a.npv and r is not None:
        npv_kw = dict(tps_growth=a.tps_growth, years=a.years, discount_rate=a.discount_rate)
        print_npv(solve_npv(a.tps, stacks=stacks, **common, **npv_kw))
        if a.range:
            rng = solve_npv_range(a.tps, stacks=stacks, **common, **npv_kw)
            print("\nx86 NPV ARALIGI (low / mid / high):")
            for lv in cm.RANGE_LEVELS:
                x = rng[lv]
                print(f"  {lv:<5} " + ("infeasible" if x is None else
                      f"${x['npv']:>14,.0f}  (${x['levelized_per_tps_month']:,.2f}/TPS/ay, "
                      f"{x['stack']} {x['topology'].code})"))
    if a.compare:
        print_compare(compare(a.tps, stacks=stacks, **common), a.tps)
        if a.range:
            print_compare_range(compare_range(a.tps, stacks=stacks, **common), a.tps)
    return 0 if r is not None else 1


if __name__ == "__main__":
    sys.exit(main())
