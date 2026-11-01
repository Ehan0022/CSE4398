"""
================================================================================
MAINFRAME (VERTICAL / SCALE-UP) MODEL — IBM z16 A01 (3931)
================================================================================
Bu modul, verilen bir is yuku + SLA girdisi icin, onu saglayan minimum maliyetli
IBM z16 A01 konfigurasyonunu bulur. Degisiklik gecmisi: PROJECT_LOG.md.
Teknik dokumantasyon: docs/mainframe_model_documentation_v3.md.

Akis:
  1. Kademe tablosu (data/z16_a01_capacity.csv, 317 kademe) yuklenir.
  2. Kapasite koprusu: kademe TPS'i = PCI x TPS_PER_PCI / w. TPS_PER_PCI
     REDP-5320 islemi icindir; w, is yuku profilinin (okuma/yazma SQL
     bilesimi) REDP islemine goreli CPU agirligidir.
     TPS_PER_PCI, REDP-5320 z13 benchmark'inin ayni LSPR/PCI olcegindeki
     z13 kapasitesine bolunmesiyle bulunur (nesiller arasi LSPR oranlari
     zaten bu olcege gomulu).
  3. Latency hedefi varsa per-CP M/M/1 + sabit I/O gecikmesinden dinamik
     utilization tavani; operasyonel %90 tavan her zaman gecerli.
  4. Availability hedefini karsilayan topolojiler (M1-M4) filtrelenir
     (ITIC alt siniri + planli kesinti duzeltmesi).
  5. Storage (IBM DS8900F): veri hacmi, IOPS ve topolojiye bagli kopya
     sayisindan boyutlandirma ve maliyet; I/O gecikmesi (D_io) storage
     yolundan (zHyperLink, zHPF/FICON, senkron Metro Mirror) hesaplanir.
  6. Maliyet: yazilim yigini (z/OS + CICS TS + Db2) IBM AWLC kumulatif
     kademeli fiyatla, faturalanan (sub-capacity) MSU uzerinden; zIIP payi
     MSU'ya sayilmaz, zIIP motorlari donanima eklenir.
  7. Tum (kademe x topoloji) kombinasyonlarindan en ucuzu secilir.
  8. Yillik modda 8760 saatlik profil ve uc fiyatlama stratejisi: Permanent,
     Base + On/Off CoD, Tailored Fit Pricing (base + corridor + CoD). Gecici
     kapasite SC28-7025 sinirlarina tabidir (%100 kurali, drawer, alt-kapasite).

KAPSAM DISI: z16 A02 / AGZ (3932, rack-mount) modelleri ve 3931-400 (yalnizca
  CF). Bkz. dokumantasyon, Bolum 3.4.

KAYNAK ETIKETLERI:
  [LSPR]     = IBM Z LSPR ITRRs, ibm.com/support/pages/ibm-z-lspr-itrrs
               (3931 4xx/5xx/6xx 1-39 CP ve 701-703: PCI, MSU, Low/Avg/High)
  [LSPR-z13] = IBM Z LSPR ITR zOSv2r2, ibm.com/support/pages/node/6953815
               (2964-718: 21579 PCI; 2964-726: 29048 PCI)
  [EXHIBIT]  = IBM Mainframe Exhibit, Full Capacity MSUs (5/2/2025),
               3931-701..7K0 resmi MSU degerleri
  [STINE]    = K. Stine, "IBM z16 Technical Overview" (2022): 200-way = 215,089 PCI
  [SG24-8950]= IBM z16 Technical Introduction: A01'de 317 kapasite seviyesi
               (200 tam-hiz + 117 alt-kapasite, ilk 39 CP icin)
  [REDP]     = IBM Redpaper REDP-5320 "CICS TS V5.3 Benchmark on IBM z13"
               (18 CP -> 174000 TPS ; 26 CP -> 227000 TPS)
  [REDBOOK]  = IBM Resiliency Redbook SG24-8446, Table 1-4 + Section 2
  [ITIC]     = ITIC Global Server Reliability Surveys 2020-2024
  [PRECISELY]= Precisely HA Definition: total downtime'in %90'i planned
  [QUEUE]    = Kuyruk teorisi (per-CP M/M/1); WLM/RMF percentile metodolojisiyle uyumlu
  [CFCC]     = Coupling Facility / ICF: specialty engine, yazilim lisansini etkilemez
  [R4HA]     = IBM MLC sub-capacity: aylik en yuksek 4-saatlik kayan ortalama
  [COD]      = IBM SC28-7025 Capacity on Demand User's Guide
  [TFP-HW]   = IBM Tailored Fit Pricing, Hardware Consumption Solution (corridor)
  [TFP-TCO]  = IBM IT Economics, TFP for IBM Z Hardware maliyet calismasi (2021)
  [TFP-SW]   = IBM Tailored Fit Pricing, Software Consumption Solution
  [REDP-5554]= IBM Storage DS8900F Product Guide R9.3.2 (storage, BOLUM 6)
  [ITCANDOR], [TT-2019], [ITJUNGLE-22], [VENDORBENCH] = DS8900F IOPS / fiyat kaynaklari (BOLUM 6)
  [PRICE]    = Mainframe fiyat rehberleri (donanim ~$0.5M-10M+; bakim %10-15/yil)
  [AWLC]     = IBM AWLC kademe sinirlari (zNALC ZSL03508, CMG 2020), kumulatif fiyat
  [IBM-2004] = IBM WLC sunumu (vm.ibm.com 2005-Z24): Db2 kademe fiyatlari ve
               ornek fatura (z/OS, CICS, Db2) -> egri + urun katsayilari
  [LONGPELA] = Longpela: L7 MSU fiyati L6'dan ~%20 dusuk (L4+ dusus varsayimi)
  [REDP-PROFILE] = REDP-5320 sayac tablolari: islem basina 4.76 okuma, 0.047
               guncelleme, 0.062 CF log yazimi, 85.9 us CPU (data/raw/)
  [CATTERALL-2019/2012] = R. Catterall (IBM) Db2 blogu: CICS-Db2 islemi ~1.3 ms
               Db2 CPU; CICS'te tek INSERT ~68 us
  [SYSBENCH], [TPC-B] = profil bilesimleri (oltp_rw, tpcb_like)
  [ZIIP]     = z16 zIIP kurallari (SG24-8950): MSU disi, tam hiz, zIIP:CP <= 2:1
  [PWR]      = Enerji: 20-40 kW/frame
  [ASSUME]   = Kalibre edilmemis varsayim
================================================================================
"""

import csv
import math
import os

# ------------------------------------------------------------------------------
# BOLUM 1-2 — z16 A01 KAPASITE KADEMELERI (data/z16_a01_capacity.csv)
# ------------------------------------------------------------------------------
# 317 kademe [SG24-8950]: 4xx/5xx/6xx serileri 1-39 CP, 7xx serisi 1-200 CP.
# Sutunlar: model, series, cps, pci, msu, lspr_low, lspr_avg, lspr_high,
#           pci_source, msu_source.
#   - 4xx/5xx/6xx ve 701-703: PCI, MSU ve LSPR oranlari dogrudan [LSPR].
#   - 704-7K0: MSU resmi [EXHIBIT]; PCI, MSU/PCI oran egrisinden turetilmis
#     (DERIVED_FROM_MSU). Dogrulama: 7K0 icin turetilen 215,099 PCI,
#     IBM'in yayimladigi 215,089 ile %0.004 fark [STINE]; bilinen satirlarda
#     birini-disarida-birak hatasi maks %1.07. Uretim: src/tools/build_z16_capacity_table.py
# PCI ("Processor Capacity Index") IBM'in "MIPS" icin kullandigi addir;
# kodda tarihsel nedenle tier.mips = tier.pci.
# MSU artik kademe basina resmi degerdir (sabit MSU/MIPS orani kullanilmaz).

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
Z16_CAPACITY_CSV = os.path.join(_DATA_DIR, "z16_a01_capacity.csv")


class Tier:
    """Bir z16 A01 kapasite kademesi."""
    def __init__(self, model, series, cps, pci, msu, lspr_avg, pci_source):
        self.model = model
        self.series = series                   # '4xx' / '5xx' / '6xx' / '7xx'
        self.cps = cps                         # fiziksel CP sayisi
        self.pci = pci                         # [LSPR] ya da turetilmis
        self.mips = pci                        # geriye uyumluluk (PCI = IBM "MIPS")
        self.msu = msu                         # [LSPR] / [EXHIBIT] resmi MSU
        self.lspr = lspr_avg                   # z9 2094-701 = 1.00 olcegi
        self.pci_source = pci_source

    def __repr__(self):
        return (f"{self.model} ({self.cps} CP, "
                f"{self.pci:,.0f} PCI, {self.msu:,.0f} MSU)")


def load_tiers(path=Z16_CAPACITY_CSV):
    tiers = []
    with open(path) as f:
        for r in csv.DictReader(f):
            tiers.append(Tier(r["model"], r["series"], int(r["cps"]),
                              float(r["pci"]), float(r["msu"]),
                              float(r["lspr_avg"]), r["pci_source"]))
    return sorted(tiers, key=lambda t: (t.pci, t.model))


Z16_TIERS = load_tiers()


# ------------------------------------------------------------------------------
# BOLUM 3 — KAPASITE KOPRUSU: z13 BENCHMARK -> PCI BASINA TPS
# ------------------------------------------------------------------------------
# LSPR, tum nesilleri ayni baza (System z9 2094-701 = 1.00) gore olcer; PCI bu
# oranin sabit bir katidir (~559.8 PCI / LSPR birimi). Bu yuzden bir benchmark'in
# TPS'ini, benchmark'in kostugu sistemin PCI'sine bolmek, nesilden bagimsiz bir
# "PCI basina TPS" katsayisi verir. n-way olcekleme kaybi (sublinearite) her
# kademenin PCI'sinde zaten yer alir; ayrica uygulanmaz.
#
# [REDP] z13 benchmark capalari ve [LSPR-z13] ayni sistemlerin PCI'si:
_Z13_718_TPS, _Z13_718_PCI = 174000.0, 21579.0   # 2964-718 (18 CP), LSPR avg 38.55
_Z13_726_TPS, _Z13_726_PCI = 227000.0, 29048.0   # 2964-726 (26 CP), LSPR avg 51.89

_TPS_PER_PCI_718 = _Z13_718_TPS / _Z13_718_PCI     # ~8.06
_TPS_PER_PCI_726 = _Z13_726_TPS / _Z13_726_PCI     # ~7.81
# Iki nokta arasindaki ~%3 fark, benchmark is yukunun LSPR karisimindan biraz
# daha kotu olceklendigini gosterir. Ortalama kullanilir; fark belirsizlik
# araligi olarak raporlanir.
TPS_PER_PCI = (_TPS_PER_PCI_718 + _TPS_PER_PCI_726) / 2.0   # ~7.94 [REDP+LSPR]


def cp_equivalents(tier):
    """Kademenin 'tam-hiz tek CP' (3931-701) cinsinden kapasitesi (bilgi amacli)."""
    return tier.pci / 2253.0   # 3931-701 = 2253 PCI [LSPR]


# ------------------------------------------------------------------------------
# IS YUKU PROFILI — "1 islem"in bilesimle tanimi (eski RNI carpanlarinin yerine)
# ------------------------------------------------------------------------------
# Kopru (TPS_PER_PCI) REDP-5320 islemiyle kalibre: 1 STARTBROWSE + 5 READNEXT,
# bellekteki CICS shared data table (VSAM KSDS), ~%4 guncelleme, Db2 yok,
# neredeyse sifir DASD I/O, ~86 us CPU (z13) [REDP-PROFILE]. Bu islem cok hafif.
# Gercekci bir OLTP islemi, bilesimiyle tanimlanir ve CPU agirligi w REDP
# islemine goreli hesaplanir:
#     CPU(us) = CPU_US_TM_BASE + reads x CPU_US_PER_SQL_READ + writes x CPU_US_PER_SQL_WRITE
#     w = CPU / CPU_US_TM_BASE                   (REDP profili: w = 1)
# Ayni bilesim I/O'yu da verir (Db2 buffer pool modeli):
#     sync_io = reads x GETPAGES_PER_SQL_READ x (1 - BP_HIT_RATIO) + LOG_SYNC_IO_PER_COMMIT
#     storage_iops = sync_io + writes x ASYNC_WRITE_IO_PER_SQL_WRITE
# Clustered taraf AYNI bilesimi (reads, writes, commit) kullanir; boylece TPS
# iki tarafta ayni isi ifade eder (Degerlendirme #1, tehdit 1).
CPU_US_TM_BASE = 85.9          # REDP islemi, z13 CP-us (CICS + 5 bellek okumasi) [REDP-PROFILE]
CPU_US_PER_SQL_READ = 30.0     # Db2 tekil/indeksli SELECT, z13-donemi CP-us [ASSUME, aralik 15-60]
CPU_US_PER_SQL_WRITE = 70.0    # Db2 INSERT/UPDATE/DELETE; CICS'te INSERT ~68 us [CATTERALL-2012]
GETPAGES_PER_SQL_READ = 4.0    # indeks seviyeleri + veri sayfasi [ASSUME]
BP_HIT_RATIO = 0.95            # Db2 buffer pool isabet orani, OLTP [ASSUME, aralik 0.90-0.99]
LOG_SYNC_IO_PER_COMMIT = 1.0   # commit'te senkron log yazimi (dual log paralel) [ASSUME]
ASYNC_WRITE_IO_PER_SQL_WRITE = 0.5   # deferred write, sayfa birlestirme [ASSUME]


class WorkloadProfile:
    """Bir islem tipinin bilesimi. Override alanlari (sync_io, storage_iops)
    yalnizca dogrudan olculmus profiller icindir (REDP)."""
    def __init__(self, name, reads, writes, commits, ziip_eligible, label,
                 source, sync_io=None, storage_iops=None):
        self.name, self.reads, self.writes, self.commits = name, reads, writes, commits
        self.ziip_eligible = ziip_eligible   # Db2 isi var mi (zIIP'e kayabilir mi)
        self.label, self.source = label, source
        self._sync_io, self._storage_iops = sync_io, storage_iops

    def cpu_us(self):
        return (CPU_US_TM_BASE + self.reads * CPU_US_PER_SQL_READ
                + self.writes * CPU_US_PER_SQL_WRITE)

    def cpu_weight(self):
        return self.cpu_us() / CPU_US_TM_BASE

    def sync_io(self):
        if self._sync_io is not None:
            return self._sync_io
        return (self.reads * GETPAGES_PER_SQL_READ * (1.0 - BP_HIT_RATIO)
                + self.commits * LOG_SYNC_IO_PER_COMMIT)

    def storage_iops(self):
        if self._storage_iops is not None:
            return self._storage_iops
        return self.sync_io() + self.writes * ASYNC_WRITE_IO_PER_SQL_WRITE

    def __repr__(self):
        return (f"{self.name}: {self.reads:g} okuma + {self.writes:g} yazma SQL, "
                f"w={self.cpu_weight():.2f}, sync I/O={self.sync_io():.2f}, "
                f"IOPS={self.storage_iops():.2f}")


WORKLOAD_PROFILES = {
    # Kopru isleminin kendisi. Db2 yok; DASD: VSAM rewrite 0.047 (senkron) +
    # CF log yazimi 0.062 (sonradan DASD'ye offload) [REDP-PROFILE].
    "redp_light": WorkloadProfile("redp_light", 0, 0, 1, False,
                                  "REDP-5320 islemi (CICS bellek tablosu, Db2 yok)",
                                  "REDP-PROFILE", sync_io=0.047, storage_iops=0.109),
    # TPC-B / debit-credit bileseni: 1 SELECT + 3 UPDATE + 1 INSERT.
    "tpcb_like":  WorkloadProfile("tpcb_like", 1, 4, 1, True,
                                  "Debit-credit (TPC-B bileseni)", "TPC-B"),
    # sysbench oltp_read_write: 10 point + 4 range SELECT, 2 UPDATE, 1 DELETE,
    # 1 INSERT, 1 COMMIT. x86 tarafinda yaygin olculen bilesim -> varsayilan.
    "oltp_rw":    WorkloadProfile("oltp_rw", 14, 4, 1, True,
                                  "Okuma-yazma OLTP (sysbench oltp_read_write bileseni)",
                                  "SYSBENCH"),
    # Agir CICS-Db2 islemi: ~1.3 ms Db2 CPU'luk bir saha olcumunun buyuklugu
    # [CATTERALL-2019]; bilesim bu buyuklugu verecek sekilde secildi [ASSUME].
    "oltp_heavy": WorkloadProfile("oltp_heavy", 30, 6, 1, True,
                                  "Agir CICS-Db2 islemi (~1.3 ms CPU)",
                                  "CATTERALL-2019"),
}
DEFAULT_WORKLOAD = "oltp_rw"


def get_workload(workload):
    """Profil adi veya WorkloadProfile nesnesi -> WorkloadProfile."""
    if isinstance(workload, WorkloadProfile):
        return workload
    return WORKLOAD_PROFILES[workload]


def ziip_fraction(workload=DEFAULT_WORKLOAD):
    """Profilin zIIP'e kayan CPU payi: Db2 isi yoksa 0."""
    return ZIIP_OFFLOAD_FRACTION if get_workload(workload).ziip_eligible else 0.0


# [ZIIP] zIIP (z Integrated Information Processor): Db2 DRDA istekleri, Java,
# XML ve bazi Db2 sistem gorevleri (prefetch, log, utility) zIIP'te calisir.
# zIIP kapasitesi MSU'ya sayilmaz -> MLC faturasina girmez; donanimi GP'den
# ucuzdur; alt-kapasite (4xx/5xx/6xx) modellerde bile tam hizda calisir.
# Uygunluk is yukune baglidir: yerel CICS-COBOL-Db2 OLTP'de dusuk (~%0-10),
# DRDA/Java agirlikli OLTP'de %40'a cikabilir. Varsayilan muhafazakar.
ZIIP_OFFLOAD_FRACTION = 0.10   # CPU isinin zIIP'e kayan payi [ASSUME, aralik 0-0.40]
ZIIP_ENGINE_PCI = 2253.0       # tek tam-hiz motor = 3931-701 PCI [LSPR]
ZIIP_PER_CP_LIMIT = 2          # z16: zIIP sayisi <= 2 x GP CP [ZIIP]
ZIIP_HW_PRICE_FACTOR = 0.25    # zIIP motor fiyati / esdeger GP fiyati [ASSUME]

# ------------------------------------------------------------------------------
# BOLUM 4 — LATENCY MODELI (per-CP M/M/1 kuyrugu + sabit I/O gecikmesi)
# ------------------------------------------------------------------------------
# MODEL:
#   - Sunucu = fiziksel CP. CP basina servis hizi mu = raw_tps / c, yani
#     E[X_cpu] = c / raw_tps. Alt-kapasite (4xx/5xx/6xx) CP'leri LSPR geregi
#     daha yavas oldugu icin E[X] daha buyuk cikar (gercek bir mainframe etkisi:
#     alt-kapasite kademeleri daha uzun CPU suresi = daha kotu yanit suresi).
#   - TUTUCU kuyruk: c adet bagimsiz M/M/1 kuyrugu, her birine lambda/c.
#     Paylasimli kuyruktan (M/M/c) daha kotu yanit verir -> gercek bir ust sinir.
#       R_cpu(p) = E[X_cpu] / (1 - rho) * ln(1/(1-p))
#   - Sabit I/O gecikmesi (kuyruktan bagimsiz, deterministik):
#       D_io = sync_io(profil) * t_io(topoloji)
#     t_io, storage katmanindan gelir (BOLUM 6): okuma/yazma orani, DS8900F
#     onbellek isabeti, zHyperLink / zHPF-FICON servis sureleri ve senkron
#     replikasyonun (Metro Mirror) mesafe gecikmesi.
#     sync_io, is yuku profilinin bilesiminden gelir (BOLUM 3, Db2 buffer pool
#     isabeti + commit log yazimi). Senkron I/O'lar sirali sayilir (tutucu).
#   - Toplam: R(p) = D_io + R_cpu(p)
#   - Cozum:  rho_max = 1 - E[X_cpu] * ln(1/(1-p)) / (latency_target - D_io)
#   - Operasyonel tavan HER ZAMAN gecerli: rho = min(rho_latency, 0.90).
#     Latency hedefi tavani sadece DUSUREBILIR, asla yukseltemez.
#
# Sinirlamalar: network ihmal (mainframe ic fabric), lock/latch beklemesi ve
# Db2 buffer pool isabet orani modellenmez. Clustered taraf ayni yapiyi
# kullanmali (ayni kuyruk ailesi + D_io + ag gecikmesi) ki iki taraf ayni
# disiplinle karsilastirilsin.

# Operasyonel utilization tavani: latency hedefi olsa da olmasa da asilmaz.
# Mainframe kapasite planlama pratiginde %90 uzeri burst ve mikro ariza
# riskini artirir. [ASSUME, pratik dayanak]
DEFAULT_UTILIZATION_CEILING = 0.90
# Geriye uyumluluk icin eski isim; ayni deger.
HARD_UTILIZATION_CAP = DEFAULT_UTILIZATION_CEILING

# I/O servis suresi parametreleri (mainframe storage yolu: z16 <-> DS8900F)
IO_READ_FRACTION = 0.70        # [ASSUME] OLTP okuma/yazma orani ~70/30
CACHE_HIT_RATIO = 0.90         # [ASSUME] DS8900F onbellek isabet orani (okuma)
ZHYPERLINK_ENABLED = True      # z16 + DS8900F zHyperLink [REDP-5554]
ZHYPERLINK_READ_SHARE = 0.80   # [ASSUME] isabetli okumalarin zHyperLink'e uygun payi
                               #   (Db2 senkron rastgele okumalar; digerleri zHPF/FICON)
T_ZHYPERLINK_S = 20e-6         # [REDP-5554] zHyperLink kucuk blok okuma < 20 us (~18 us)
T_FICON_HIT_S = 90e-6          # [TT-2019] zHPF/FICON, DS8900F onbellek isabeti ~90 us
T_FLASH_MISS_S = 300e-6        # [ASSUME] onbellek iskasi: flash arka uc + FICON
REPLICATION_S_PER_KM = 10e-6   # [FIZIK] fiberde isik ~5 us/km tek yon -> 10 us/km gidis-donus
METRO_DISTANCE_KM = 20.0       # [ASSUME] senkron Metro Mirror siteleri arasi mesafe


def io_service_time_seconds(topology=None):
    """Tek bir I/O'nun ortalama servis suresi (saniye).

    okuma = isabet x (zHyperLink payi x t_zHL + kalan x t_FICON) + iska x t_miss
    yazma = t_FICON (DS8900F NVS'e hizli yazma) + senkron replikasyon gecikmesi
    Senkron replikasyon yalnizca topolojide senkron bir kopya varsa eklenir.
    """
    z = ZHYPERLINK_READ_SHARE if ZHYPERLINK_ENABLED else 0.0
    t_read = (CACHE_HIT_RATIO * (z * T_ZHYPERLINK_S + (1.0 - z) * T_FICON_HIT_S) +
              (1.0 - CACHE_HIT_RATIO) * T_FLASH_MISS_S)
    t_write = T_FICON_HIT_S
    if topology is not None and getattr(topology, "sync_replication", False):
        t_write += METRO_DISTANCE_KM * REPLICATION_S_PER_KM
    return IO_READ_FRACTION * t_read + (1.0 - IO_READ_FRACTION) * t_write


def io_delay_seconds(workload=DEFAULT_WORKLOAD, topology=None):
    """Transaction basina deterministik I/O gecikmesi (saniye)."""
    return get_workload(workload).sync_io() * io_service_time_seconds(topology)


def raw_tier_tps(tier, workload=DEFAULT_WORKLOAD):
    """Kademenin %100 utilization'daki ham TPS kapasitesi.

    TPS_PER_PCI REDP islemi icindir; profilin CPU agirligi w'ye bolunur.
    zIIP'e kayan is (ziip_fraction) genel amacli CP'yi tuketmez; bu yuzden
    ayni GP kademesi 1/(1-f) kat daha fazla transaction tasir. zIIP
    motorlarinin donanim maliyeti monthly_cost icinde ayrica eklenir."""
    w = get_workload(workload)
    return tier.pci * TPS_PER_PCI / w.cpu_weight() / (1.0 - ziip_fraction(w))


def avg_service_time_seconds(tier, workload=DEFAULT_WORKLOAD):
    """
    CP basina ortalama CPU servis suresi E[X_cpu] = c / raw_tps (saniye).
    c = fiziksel CP sayisi. Bir transaction tek bir CP'de islenir.
    """
    raw_tps = raw_tier_tps(tier, workload)
    if raw_tps <= 0:
        return float('inf')
    return tier.cps / raw_tps


def max_utilization_for_latency(tier, workload, latency_target_seconds, percentile,
                                topology=None):
    """
    Latency hedefini saglayan maksimum utilization (0 ile 0.90 arasi).
    Latency hedefi yoksa operasyonel tavan (0.90) doner.
    0 donerse kademe bu hedefi hicbir yukte saglayamaz.
    """
    if latency_target_seconds is None:
        return DEFAULT_UTILIZATION_CEILING

    ex = avg_service_time_seconds(tier, workload)
    budget = latency_target_seconds - io_delay_seconds(workload, topology)
    ln_term = math.log(1.0 / (1.0 - percentile))
    if budget <= 0 or ex * ln_term >= budget:
        # I/O gecikmesi ya da bos sistemdeki CPU suresi bile hedefi asiyor
        return 0.0

    rho_max = 1.0 - (ex * ln_term) / budget
    return max(0.0, min(rho_max, DEFAULT_UTILIZATION_CEILING))


def expected_latency_at(tier, workload, tps, percentile, topology=None):
    """
    Verilen TPS yukunde tahmini percentile yanit suresi (saniye):
    D_io + per-CP M/M/1 percentile. Bilgi amacli.
    """
    raw_tps = raw_tier_tps(tier, workload)
    if raw_tps <= 0:
        return float('inf')
    rho = tps / raw_tps
    if rho >= 1.0:
        return float('inf')
    ex = avg_service_time_seconds(tier, workload)
    ln_term = math.log(1.0 / (1.0 - percentile))
    return io_delay_seconds(workload, topology) + ex * (1.0 / (1.0 - rho)) * ln_term

# ------------------------------------------------------------------------------
# AVAILABILITY MODELI — IBM Z Resiliency Models (Redbook SG24-8446)
# ------------------------------------------------------------------------------
# IBM'in resmi 4-model availability cercevesi. Bizim simulasyonumuzda Model 1
# (sysplex'siz tek frame) gercek dunya production'da bulunmadigindan, Model 1'i
# "single-frame sysplex (icinde ICF)" olarak ele aliyoruz - bu hala tek hardware
# frame ama icinde sysplex var (rolling IPL ile planli kesintilerde fayda).
#
# Her topoloji icin iki availability rakami:
#   hw_low:  ITIC bagimsiz endustri olcumu (gercek musteri raporlari)
#            [ITIC] = Information Technology Intelligence Consulting,
#                     2020-2024 Global Server Reliability Surveys
#   hw_high: IBM Redbook resmi tasarim hedefi
#            [REDBOOK] = IBM Resiliency Redbook SG24-8446, Table 1-4 + Sec 2
#
# Bu rakamlar HARDWARE-ONLY (planned outage haric). Gercek end-user
# availability'si planned maintenance nedeniyle daha dusuk olur.
#
# PLANNED OUTAGE INDIRIMI [PRECISELY]:
# Endustri verisi: toplam downtime'in ~%90'i planned outage'lardan kaynaklanir.
# Kaynak: Precisely HA Definition (precisely.com/glossary/high-availability-ha)
# Formul: total_downtime = hardware_downtime / 0.10 = hardware_downtime x 10
#         total_availability = 1 - 10 x (1 - hw_availability)
#
# Istisna: Model 4 (GDPS Continuous Availability) tanim geregi planned outage'i
# da maskeler [REDBOOK], bu yuzden onun rakamlari planned dahil zaten.
# ------------------------------------------------------------------------------

class Topology:
    """Bir mainframe availability topolojisi."""
    def __init__(self, code, name, n_frames, hw_low, hw_high,
                 masks_planned, cost_multiplier, software_premium=1.0,
                 description="", storage_copies=1, sync_replication=False):
        self.code = code                # 'M1', 'M2', 'M3', 'M4'
        self.name = name
        self.n_frames = n_frames        # ana frame sayisi (donanim carpani)
        self.hw_low = hw_low            # ITIC bagimsiz alt sinir (HW-only)
        self.hw_high = hw_high          # Redbook tasarim hedefi (HW-only)
        self.masks_planned = masks_planned  # planned outage'i da maskeler mi?
        self.cost_multiplier = cost_multiplier  # frame sayisi + ek donanim
        self.software_premium = software_premium  # GDPS gibi ek yazilim
        self.description = description
        self.storage_copies = storage_copies      # DS8900F veri kopyasi (dizi) sayisi
        self.sync_replication = sync_replication  # senkron Metro Mirror var mi

    def effective_availability_low(self):
        """%90 planned outage kuralini uygula (Model 4 haric)."""
        if self.masks_planned:
            return self.hw_low  # GDPS CA zaten planned'i de maskeler
        # total_downtime = hardware_downtime / 0.10
        hw_downtime = 1.0 - self.hw_low
        total_downtime = hw_downtime * 10.0
        return max(0.0, 1.0 - total_downtime)

    def effective_availability_high(self):
        """Vendor iddiasinin planned-dahil halı."""
        if self.masks_planned:
            return self.hw_high
        hw_downtime = 1.0 - self.hw_high
        total_downtime = hw_downtime * 10.0
        return max(0.0, 1.0 - total_downtime)

    def __repr__(self):
        return f"{self.code}: {self.name}"


# IBM Z Resiliency Model topolojileri:
TOPOLOGIES = [
    Topology(
        code="M1",
        name="Single-frame sysplex (ICF)",
        n_frames=1,
        # ITIC: 2020'de %83 musteri 5-6 nine basardi (tek-frame deployment'lar
        # bu kategoride agirlikli). Tek-frame icin alt sinir 5 nine.
        hw_low=0.99999,           # [ITIC 2020-2021]
        hw_high=0.999999,         # [REDBOOK] Sec 2: tek frame RAS hedef ~6 nine
        masks_planned=False,
        cost_multiplier=1.0,      # 1 frame
        software_premium=1.0,     # ICF specialty engine, lisans etkisiz [CFCC]
        description="Tek mainframe + icindeki ICF ile sysplex. "
                    "Tek hardware riski; planli kesintide rolling IPL faydasi.",
        storage_copies=1, sync_replication=False,   # tek DS8900F
    ),
    Topology(
        code="M2",
        name="Multi-frame failover (peer sysplex)",
        n_frames=2,
        # ITIC 2023: z13/z14/z15 ortalamasi 7-8 nine; cogu M2/M3 deployment.
        # M2 alt sinirini 7 nine olarak aliyoruz.
        hw_low=0.9999999,         # [ITIC 2023] 7 nine
        hw_high=0.99999999,       # [REDBOOK] Model 2-3 hedef ~8 nine
        masks_planned=False,
        cost_multiplier=2.0,      # 2 frame
        software_premium=1.0,     # ICF her frame'de, lisans etkisiz
        description="Iki ayri mainframe, ICF ile peer coupling, "
                    "sync/async remote copy. Bir frame coker, digeri devralir.",
        storage_copies=2, sync_replication=True,    # Metro Mirror cifti (HyperSwap)
    ),
    Topology(
        code="M3",
        name="Fault-tolerant + GDPS Metro/Global",
        n_frames=2,
        # ITIC 2024 z16: %96 musteri 9 nine basardi. M3/M4 dahil rakam.
        # M3 alt siniri 8 nine.
        hw_low=0.99999999,        # [ITIC 2024 z16] 8 nine
        hw_high=0.999999999,      # [REDBOOK] Model 3 hedef ~9 nine
        masks_planned=False,      # planli outage hala maskelenmiyor
        cost_multiplier=2.0,      # 2 frame
        software_premium=1.15,    # [ASSUME] GDPS Metro/Global lisans +%15
        description="2 frame + GDPS Metro/Global otomasyonu + HyperSwap. "
                    "RTO <1 saat. Planlanmamis outage'a otomatik tepki.",
        storage_copies=4, sync_replication=True,    # H1+H2 (Metro) + H3+J3 (Global Mirror) [GDPS]
    ),
    Topology(
        code="M4",
        name="GDPS Continuous Availability (geo-redundant)",
        n_frames=2,
        # ITIC 2024 z16 en yuksek deployment'lar 9 nine; Redbook M4 tasarim 7 nine
        # NOT: M4 planned outage'i da maskeler, hardware rakamı zaten planned dahil
        hw_low=0.9999999,         # [REDBOOK] Model 4 tasarim 7 nine (planned dahil)
        hw_high=0.99999999,       # [ITIC 2024] z16 ileri deployment 8 nine
        masks_planned=True,       # planned outage'i da maskeler [REDBOOK]
        cost_multiplier=2.0,      # 2 ayri site, ikinci site tam mainframe
        software_premium=1.30,    # [ASSUME] GDPS CA premium lisans +%30
        description="Iki coğrafi site, GDPS Continuous Availability. "
                    "Hem planned hem unplanned outage maskelenir. RTO 1-2 dakika.",
        storage_copies=4, sync_replication=True,    # her sitede Metro Mirror cifti [GDPS]
    ),
]


def find_feasible_topologies(availability_target):
    """
    Hedef uptime'i karsilayan topolojileri dondurur (en ucuzdan en pahaliya).
    Feasibility: low (ITIC bagimsiz) availability hedefi karsilamali.
    """
    feasible = []
    for topo in TOPOLOGIES:
        if topo.effective_availability_low() >= availability_target:
            feasible.append(topo)
    return feasible

# ------------------------------------------------------------------------------
# BOLUM 5 — MALIYET PARAMETRELERI
# ------------------------------------------------------------------------------
# [AWLC] Yazilim yigini: z/OS + CICS TS + Db2 (MQ kapsam disi). IBM Advanced
# Workload License Charges kademeli aylik ucrettir: MSU arttikca marjinal
# MSU fiyati duser. Kademe sinirlari resmidir (IBM AWLC: Base 1-3, L0 4-45,
# L1 46-175, L2 176-315, L3 316-575, L4 576-875, L5 876-1315, L6 1316-1975,
# L7 1976+). Guncel liste fiyati kamuya acik degil; bu yuzden:
#   1) kademe dusus egrisi IBM'in yayimlanmis Db2 liste fiyatindan [IBM-2004]:
#      Base $3,960 (ilk 3 MSU dahil), L0 $208, L1 $88, L2 $66, L3 $50 /MSU/ay;
#      L4+ icin kademe basina x0.80 [ASSUME; Longpela: "L7, L6'dan %20 ucuz"],
#   2) urun katsayilari IBM'in ornek faturasina kalibre [IBM-2004],
#   3) mutlak seviye SW_PRICE_LEVEL_FACTOR ile (1.0 = 2004 nominal liste),
#      duyarlilik analizinde 0.5-1.5 araliginda taranir.
AWLC_BASE_CHARGE = 3960.0              # USD/ay, ilk 3 MSU dahil [IBM-2004]
AWLC_LEVELS = [                        # (kademe ust siniri MSU, marjinal USD/MSU/ay)
    (3,     0.0),                      # Base (sabit ucrete dahil)
    (45,    208.0),                    # L0  [IBM-2004]
    (175,   88.0),                     # L1  [IBM-2004]
    (315,   66.0),                     # L2  [IBM-2004]
    (575,   50.0),                     # L3  [IBM-2004]
    (875,   40.0),                     # L4  [ASSUME x0.80]
    (1315,  32.0),                     # L5  [ASSUME x0.80]
    (1975,  25.6),                     # L6  [ASSUME x0.80]
    (float("inf"), 20.48),             # L7  [ASSUME x0.80, LONGPELA]
]
# IBM ornek faturasi (aylik, sub-capacity): urun -> (USD/ay, faturalanan MSU)
SW_PRODUCT_ANCHORS = {
    "z/OS":    (75459.0, 265),         # [IBM-2004]
    "CICS TS": (32978.0, 210),         # [IBM-2004] CICS ayri LPAR'da 210 MSU
    "Db2":     (31876.0, 265),         # [IBM-2004]
}
SW_PRICE_LEVEL_FACTOR = 1.0            # 2004 nominal = 1.0 [ASSUME, aralik 0.5-1.5]

# [PRICE] Donanim: kapasiteyle olcekleniyor. Liste fiyati yok; MIPS basina
# kaba bir donanim fiyati turetiyoruz. Aralik ~$0.5M (giris) - $10M+ (tam).
# Tam-hiz tek-frame ust kapasite ~ 7xx 32CP ~ 48637 MIPS. Kaba dogrusal cikarim:
# [ASSUME] donanim ~ $200 / MIPS (0.5M-10M araligina kabaca oturuyor)
HARDWARE_COST_PER_MIPS = 200.0         # USD/MIPS (satin alma)  [PRICE -> ASSUME]
HARDWARE_AMORTIZATION_YEARS = 5        # [ASSUME] amortisman suresi
MAINTENANCE_RATE_ANNUAL = 0.125        # donanim degerinin %12.5'i/yil [PRICE]

# [PWR] Enerji: ~20-40 kW/frame. Orta deger + elektrik fiyati.
POWER_KW_PER_SYSTEM = 30.0             # kW/frame  [PWR, orta deger]
ELECTRICITY_USD_PER_KWH = 0.12         # [ASSUME] tipik ticari elektrik
HOURS_PER_MONTH = 730.0

# [PRICE] Ekonomik alt esik: <150 MIPS altinda mainframe mantikli degil.
MAINFRAME_MIN_VIABLE_MIPS = 150.0      # [PRICE]


# ------------------------------------------------------------------------------
# BOLUM 6 — STORAGE KATMANI (IBM DS8900F)
# ------------------------------------------------------------------------------
# Mainframe tarafinin sabit storage'i DS8900F (z16 ile ayni nesil, all-flash).
# Mainframe'e ozgu yapilar:
#   - Shared-disk: Db2 data sharing uyeleri ayni diske erisir; site basina
#     verinin tek kopyasi vardir. Kopya sayisini topoloji (DR) belirler.
#   - DR replikasyonu storage katmaninda: Metro Mirror (senkron), Global Mirror
#     (asenkron + journal), GDPS yonetir. Senkron kopya yazma gecikmesine
#     mesafe kadar eklenir (BOLUM 4, io_service_time_seconds).
#   - Baglanti: FICON/zHPF (~90 us) ve zHyperLink (< 20 us, 150 m'ye kadar).
#   - I/O islemcisi: I/O, z16'nin kanal alt sistemi ve SAP'lerinde islenir; genel
#     amacli CP'yi (MSU'yu) cok az tuketir. Kapasite koprusu (CICS benchmark'i)
#     z/OS I/O'sunun CPU maliyetini zaten icerir, ek CPU yuku eklenmez.
#     (Clustered tarafta storage yiginin host CPU'su ayrica eklenmeli.)
#   - CKD hacimlerde dizi tarafinda veri azaltma (sikistirma/dedup) yok;
#     sikistirma host'ta (Db2, z16 on-chip hizlandirici) yapilir.
#   - Safeguarded Copy: fidye yazilimina karsi degistirilemez anlik kopyalar;
#     birincil dizide ek kapasite ister.
#   - Lisanslar (TB basina kademeli, fiyat yayimlanmiyor) [REDP-5554]:
#     Base Function (tum kapasite), z-synergy Services (FICON, PAV/HyperPAV/
#     SuperPAV, zHPF, zHyperLink; CKD), Copy Services (FlashCopy, Safeguarded
#     Copy, Metro/Global Mirror).
#
# KAYNAKLAR:
#   [REDP-5554]   IBM Storage DS8900F Product Guide R9.3.2: modeller, kapasite,
#                 guc, zHyperLink, lisans paketleri ve TB kademeleri
#   [ITCANDOR]    DS8900F maks. IOPS: 860K (DS8910F), 2,320K (DS8950F)
#   [TT-2019]     TechTarget: baslangic fiyatlari $134K / $196K; zHPF 90 us
#   [ITJUNGLE-22] IT Jungle (IBM duyurusu 322-396, Mayis 2022): 15.36 TB flash
#                 karti liste fiyati $132,381 = $8.62/GB (kontrolcu haric)
#   [VENDORBENCH] Kurumsal all-flash pazar karsilastirmalari: liste fiyatindan
#                 %35-65 indirim; yillik destek donanimin %10-25'i
#   [IBM-122-037] DS8900F bir yillik garanti teklifi
#   [GDPS]        IBM GDPS mimarisi: Metro Mirror cifti (HyperSwap), Metro/Global
#                 Mirror'da uzak sitede Global Mirror journal (FlashCopy) kopyasi
#                 (doğrulanmalı: kopya sayilari)

DS8900F_CSV = os.path.join(_DATA_DIR, "ds8900f_models.csv")


class StorageModel:
    """Bir DS8900F modeli [REDP-5554, ITCANDOR, TT-2019]."""
    def __init__(self, model, family, max_raw_tb, max_iops, base_price_list_usd,
                 power_kw, expansion_threshold_tb, expansion_power_kw):
        self.model = model
        self.family = family
        self.max_raw_tb = max_raw_tb
        self.max_iops = max_iops
        self.base_price_list_usd = base_price_list_usd
        self.power_kw = power_kw
        self.expansion_threshold_tb = expansion_threshold_tb
        self.expansion_power_kw = expansion_power_kw

    def __repr__(self):
        return f"{self.family}-{self.model}"


def load_storage_models(path=DS8900F_CSV):
    rows = []
    with open(path, newline="") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    for r in csv.DictReader(lines):
        rows.append(StorageModel(
            r["model"], r["family"], float(r["max_raw_tb"]), float(r["max_iops"]),
            float(r["base_price_list_usd"]), float(r["power_kw"]),
            float(r["expansion_threshold_tb"]) if r["expansion_threshold_tb"] else None,
            float(r["expansion_power_kw"]) if r["expansion_power_kw"] else 0.0))
    return rows


DS8900F_MODELS = load_storage_models()

# --- Kapasite zinciri ---------------------------------------------------------
DEFAULT_DATA_VOLUME_TB = 20.0    # [ASSUME] ornek mantiksal Db2 veri hacmi (indeksler dahil)
DEFAULT_DATA_GROWTH = 0.15       # [ASSUME] yillik veri buyumesi
STORAGE_PLANNING_YEARS = 3       # [ASSUME] dizi, bu kadar yillik buyumeye gore boyutlanir
DB_OVERHEAD_FACTOR = 1.5         # [ASSUME] Db2 log/arsiv log, image copy, work alani,
                                 #   z/OS sistem hacimleri ve bos alan
HOST_COMPRESSION_RATIO = 1.0     # [ASSUME] Db2 sikistirmasi (z16 on-chip); 1.0 = yok
SAFEGUARDED_COPY = True          # [REDP-5554] fidye yazilimi korumasi (birincil dizide)
SAFEGUARDED_RESERVE = 0.25       # [ASSUME] Safeguarded Copy icin ek kapasite orani
RAID_USABLE_FRACTION = 0.75      # [ASSUME] RAID 6 (6+P+Q) kullanilabilir/ham (doğrulanmalı)
STORAGE_IOPS_CEILING = 0.70      # [ASSUME] dizi, ureticinin tepe IOPS'unun bu oranina kadar
                                 #   yuklenir (tepe deger onbellek isabetli kucuk blok olcumu;
                                 #   compute'taki %90 operasyonel tavanin storage karsiligi)

# --- Fiyat --------------------------------------------------------------------
DS8900F_FLASH_LIST_USD_PER_TB = 8620.0   # [ITJUNGLE-22] ham TB, liste
STORAGE_DISCOUNT = 0.70          # [ASSUME] liste fiyatindan indirim (pazar %35-65+ [VENDORBENCH])
STORAGE_LICENSE_RATE_BASE = 0.15 # [ASSUME] BF + z-synergy Services, donanima oran
STORAGE_LICENSE_RATE_COPY = 0.10 # [ASSUME] Copy Services (Safeguarded Copy/replikasyon varsa)
STORAGE_MAINT_RATE_ANNUAL = 0.15 # [VENDORBENCH] yillik destek, donanim degerinin %10-25'i
STORAGE_WARRANTY_YEARS = 1       # [IBM-122-037]
STORAGE_AMORTIZATION_YEARS = 5   # [ASSUME] mainframe donanimiyla ayni


def storage_capacity_tb(data_tb=None, growth=None):
    """Bir kopyanin (dizinin) ham kapasite ihtiyaci, Safeguarded rezervi haric.
    mantiksal veri -> planlama ufkundaki veri -> Db2/z/OS ek yuku -> host
    sikistirmasi -> RAID 6 ham kapasitesi."""
    data_tb = DEFAULT_DATA_VOLUME_TB if data_tb is None else data_tb
    growth = DEFAULT_DATA_GROWTH if growth is None else growth
    planned = data_tb * (1.0 + growth) ** STORAGE_PLANNING_YEARS
    usable = planned * DB_OVERHEAD_FACTOR / HOST_COMPRESSION_RATIO
    return usable / RAID_USABLE_FRACTION


def _size_array(raw_tb, iops):
    """Bir kopya icin en ucuz DS8900F konfigurasyonu: (model, adet, liste capex, kW)."""
    best = None
    for sm in DS8900F_MODELS:
        n = max(1, math.ceil(raw_tb / sm.max_raw_tb),
                math.ceil(iops / (sm.max_iops * STORAGE_IOPS_CEILING)))
        per_array_tb = raw_tb / n
        kw = sm.power_kw
        if sm.expansion_threshold_tb and per_array_tb > sm.expansion_threshold_tb:
            kw += sm.expansion_power_kw
        capex_list = n * sm.base_price_list_usd + raw_tb * DS8900F_FLASH_LIST_USD_PER_TB
        cand = (sm, n, capex_list, n * kw)
        if best is None or capex_list < best[2]:
            best = cand
    return best


def storage_plan(peak_tps, workload=DEFAULT_WORKLOAD, topology=None, data_tb=None, growth=None):
    """DS8900F storage boyutlandirmasi ve aylik maliyeti.

    Her kopya ayri bir dizi (veya dizi grubu) olarak boyutlanir; ikincil kopyalar
    failover icin birincille ayni IOPS'u tasiyabilmelidir. Safeguarded Copy
    rezervi yalnizca birincil dizidedir.
    """
    copies = topology.storage_copies if topology is not None else 1
    base_raw = storage_capacity_tb(data_tb, growth)
    iops = peak_tps * get_workload(workload).storage_iops()
    discount = 1.0 - STORAGE_DISCOUNT

    arrays = []
    for i in range(copies):
        raw = base_raw * (1.0 + SAFEGUARDED_RESERVE) if (i == 0 and SAFEGUARDED_COPY) else base_raw
        sm, n, capex_list, kw = _size_array(raw, iops)
        arrays.append({"model": sm, "count": n, "raw_tb": raw,
                       "hw_capex": capex_list * discount, "power_kw": kw})

    hw_capex = sum(a["hw_capex"] for a in arrays)
    lic_rate = STORAGE_LICENSE_RATE_BASE
    if SAFEGUARDED_COPY or copies > 1:
        lic_rate += STORAGE_LICENSE_RATE_COPY
    license_capex = hw_capex * lic_rate
    capex = hw_capex + license_capex
    amort = capex / (STORAGE_AMORTIZATION_YEARS * 12)
    maint_years = max(0, STORAGE_AMORTIZATION_YEARS - STORAGE_WARRANTY_YEARS)
    maint = (hw_capex * STORAGE_MAINT_RATE_ANNUAL * maint_years /
             STORAGE_AMORTIZATION_YEARS / 12)
    power_kw = sum(a["power_kw"] for a in arrays)
    energy = power_kw * ELECTRICITY_USD_PER_KWH * HOURS_PER_MONTH
    return {
        "copies": copies,
        "arrays": arrays,
        "raw_tb_total": sum(a["raw_tb"] for a in arrays),
        "iops_required": iops,
        "hw_capex": hw_capex,
        "license_capex": license_capex,
        "capex": capex,
        "amortization": amort,
        "maintenance": maint,
        "energy": energy,
        "power_kw": power_kw,
        "monthly_total": amort + maint + energy,
        "io_service_time_s": io_service_time_seconds(topology),
        "io_delay_s": io_delay_seconds(workload, topology),
    }


def describe_storage(plan):
    parts = []
    for i, a in enumerate(plan["arrays"]):
        role = "birincil" if i == 0 else f"kopya {i}"
        parts.append(f"{role}: {a['count']}x {a['model']} ({a['raw_tb']:,.0f} TB ham)")
    return "; ".join(parts)


# ==============================================================================
# MODEL FONKSIYONLARI
# ==============================================================================

def tier_max_tps(tier, workload=DEFAULT_WORKLOAD, latency_target_seconds=None, percentile=0.99,
                 topology=None):
    """
    Bir kademenin verilen RNI ve latency hedefi altinda saglayabilecegi
    MAKSIMUM TPS (dinamik utilization tavani uygulanmis).

    Latency hedefi None ise sabit DEFAULT_UTILIZATION_CEILING kullanilir.
    Latency hedefi varsa, M/M/1 formulunden o kademenin destekleyebilecegi
    max utilization hesaplanir; gercek tavan budur.
    """
    raw_tps = raw_tier_tps(tier, workload)
    rho_max = max_utilization_for_latency(tier, workload, latency_target_seconds, percentile,
                                          topology)
    return raw_tps * rho_max


def is_capacity_feasible(tier, tps_required, workload=DEFAULT_WORKLOAD,
                          latency_target_seconds=None, percentile=0.99, topology=None):
    """Asama 3: kademe, latency hedefi altinda gereken TPS'i karsilar mi?"""
    return tier_max_tps(tier, workload, latency_target_seconds, percentile,
                        topology) >= tps_required


def consumed_msu(tier, load_tps, workload=DEFAULT_WORKLOAD):
    """
    Sub-capacity MLC icin faturalanan MSU: kademenin kurulu MSU'sunun, verilen
    yukun (R4HA) kullandigi kismi. Kurulu kapasiteyi asamaz.  [R4HA]
    """
    raw = raw_tier_tps(tier, workload)
    if raw <= 0:
        return tier.msu
    return min(load_tps / raw, 1.0) * tier.msu


def ziip_engines(tier, workload=DEFAULT_WORKLOAD):
    """Kademenin GP tam-kapasitesine eslik eden zIIP motor sayisi.
    GP'de calisan is (1-f), zIIP'te calisan f oraninda ise zIIP PCI ihtiyaci
    = GP PCI x f/(1-f). Motor sayisi yukari yuvarlanir, 2:1 sinirina kirpilir."""
    f = ziip_fraction(workload)
    if f <= 0:
        return 0
    need = tier.pci * f / (1.0 - f) / ZIIP_ENGINE_PCI
    return min(math.ceil(need - 1e-9), ZIIP_PER_CP_LIMIT * tier.cps)


def ziip_hw_purchase(tier, workload=DEFAULT_WORKLOAD):
    """zIIP motorlarinin satin alma bedeli (USD)."""
    return (ziip_engines(tier, workload) * ZIIP_ENGINE_PCI * HARDWARE_COST_PER_MIPS
            * ZIIP_HW_PRICE_FACTOR)


# ------------------------------------------------------------------------------
# Yazilim yigini: AWLC kademeli MLC (z/OS + CICS TS + Db2)
# ------------------------------------------------------------------------------
def _awlc_reference_curve(msu):
    """Referans urunun (Db2, IBM 2004 liste fiyati) aylik bedeli, kumulatif
    kademeli: her MSU kendi kademesinin marjinal fiyatiyla ucretlenir."""
    if msu <= 0:
        return 0.0
    cost = AWLC_BASE_CHARGE
    lower = AWLC_LEVELS[0][0]           # ilk 3 MSU sabit ucrete dahil
    for upper, rate in AWLC_LEVELS[1:]:
        if msu <= lower:
            break
        cost += (min(msu, upper) - lower) * rate
        lower = upper
    return cost


def _calibrate_products():
    """Urun olcek katsayilarini IBM'in 2004 ornek faturasina kalibre eder:
    katsayi = urunun ornek aylik bedeli / referans egrinin ayni MSU'daki degeri."""
    return {name: bill / _awlc_reference_curve(msu)
            for name, (bill, msu) in SW_PRODUCT_ANCHORS.items()}


SW_PRODUCT_FACTORS = _calibrate_products()   # z/OS ~2.5, CICS ~1.25, Db2 ~1.06


def software_monthly_cost(msu, breakdown=False):
    """Faturalanan MSU icin yazilim yiginin AYLIK MLC bedeli (GDPS premium haric).
    Her urun ayri kademelenir (IBM AWLC'de kademe urun basinadir)."""
    curve = _awlc_reference_curve(msu) * SW_PRICE_LEVEL_FACTOR
    parts = {name: curve * k for name, k in SW_PRODUCT_FACTORS.items()}
    total = sum(parts.values())
    return (total, parts) if breakdown else total


def monthly_cost(tier, topology, billed_msu=None, workload=DEFAULT_WORKLOAD):
    """Asama 5: bir kademenin topology'ye gore toplam AYLIK maliyeti.

    Maliyet hesaplama mantigi:
      - software:     software_monthly_cost(billed_msu) x software_premium
                      (AWLC kademeli z/OS + CICS TS + Db2; GDPS premium)
                      billed_msu verilmezse kademenin tam kurulu MSU'su
                      (full-capacity fiyatlama) kullanilir. Sub-capacity
                      fiyatlamada billed_msu = aylik R4HA tepesinde tuketilen
                      MSU'dur (bkz. consumed_msu).
                      ICF specialty engine oldugundan ek frame'ler software
                      premium'a girmez; sadece GDPS yazilimi premium ekler.
      - hardware:     tam fiyat x cost_multiplier (frame sayisi)
      - maintenance:  hardware'a oranli
      - energy:       frame sayisi x kW x elektrik
    """
    msu = tier.msu if billed_msu is None else billed_msu
    # Yazilim lisansi - GDPS premium dahil  [LIC + ASSUME premium]
    software = software_monthly_cost(msu) * topology.software_premium
    # Donanim amortismani - frame carpani  [PRICE/ASSUME]; zIIP motorlari dahil
    hw_purchase = tier.mips * HARDWARE_COST_PER_MIPS + ziip_hw_purchase(tier, workload)
    hw_monthly = hw_purchase / (HARDWARE_AMORTIZATION_YEARS * 12)
    # Bakim  [PRICE]
    maint_monthly = hw_purchase * MAINTENANCE_RATE_ANNUAL / 12
    # Enerji - her frame ayri  [PWR]
    energy = POWER_KW_PER_SYSTEM * ELECTRICITY_USD_PER_KWH * HOURS_PER_MONTH

    mult = topology.cost_multiplier
    return {
        "software": software,                       # GDPS premium varsa zaten cikti
        "hardware_amort": hw_monthly * mult,        # frame sayisi kadar
        "maintenance": maint_monthly * mult,
        "energy": energy * mult,
        "total": software + (hw_monthly + maint_monthly + energy) * mult,
    }


def solve(tps, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=None, latency_percentile=99, verbose=True,
          data_tb=None, data_growth=None):
    """
    Verilen girdi icin minimum maliyetli feasible (z16 kademesi + topoloji)
    kombinasyonunu bulur.

    Parametreler:
      tps                 : Hedef throughput (saniyedeki islem)
      availability        : Hedef uptime (0-1 arasi)
      workload            : Is yuku profili adi (WORKLOAD_PROFILES) veya WorkloadProfile
      latency_ms          : Hedef latency milisaniye olarak (None ise %90 sabit tavan)
      latency_percentile  : Hedef percentile (orn. 99 -> p99 latency hedefi)
      data_tb, data_growth: Mantiksal veri hacmi (TB) ve yillik buyume (storage)

    Akis:
      1. Hedef availability'yi karsilayan topolojileri filtrele [ITIC low]
      2. Latency hedefini de hesaba katarak her kademe icin max utilization hesapla
      3. Her topoloji icin: kapasiteyi karsilayan kademeleri aday yap
      4. Tum topoloji+kademe kombinasyonlari arasinda EN UCUZ olani sec
    """
    # Latency parametrelerini saniyeye ve fraction'a cevir
    latency_target_s = (latency_ms / 1000.0) if latency_ms is not None else None
    percentile_frac = latency_percentile / 100.0

    # 1. Feasible topolojiler (effective_availability_low >= hedef)
    feasible_topos = find_feasible_topologies(availability)

    if verbose:
        wp = get_workload(workload)
        print(f"  Girdi: {tps:,.0f} TPS | is yuku={wp.name} | uptime hedefi={availability:.6%}")
        if latency_target_s is not None:
            print(f"         latency hedefi: p{latency_percentile} < {latency_ms:g} ms "
                  f"(M/M/1 kuyruk modeli)")
        else:
            print(f"         latency hedefi: yok -> default %{DEFAULT_UTILIZATION_CEILING*100:.0f} "
                  f"utilization tavani")
        print(f"  -> Kapasite koprusu: ~{TPS_PER_PCI:.2f} REDP-islemi / s / PCI [REDP+LSPR]")
        print(f"     is yuku profili: {wp}")
        print(f"     -> {TPS_PER_PCI / wp.cpu_weight():.2f} islem / s / PCI (zIIP payi "
              f"f={ziip_fraction(wp):.2f} haric)")
        print(f"  -> Feasible topolojiler (ITIC low + planned indirimi):")
        for t in feasible_topos:
            eff_low = t.effective_availability_low()
            eff_high = t.effective_availability_high()
            print(f"       {t.code}: effective availability "
                  f"{eff_low:.6%} (low) - {eff_high:.6%} (high)")

    if not feasible_topos:
        if verbose:
            print("  -> SONUC: hicbir topoloji bu uptime hedefini saglayamiyor\n")
        return None

    # 2. Her topoloji icin feasible kademeler (latency-aware)
    candidates = []  # liste: (tier, topology, cost, util, rho_max)
    for topo in feasible_topos:
        splan = storage_plan(tps, workload, topo, data_tb, data_growth)
        for tier in Z16_TIERS:
            if is_capacity_feasible(tier, tps, workload, latency_target_s, percentile_frac, topo):
                # Sabit yukte R4HA = tps -> sub-capacity faturasi  [R4HA]
                cost = monthly_cost(tier, topo,
                                    billed_msu=consumed_msu(tier, tps, workload),
                                    workload=workload)
                cost["storage"] = splan["monthly_total"]
                cost["storage_plan"] = splan
                cost["total"] += splan["monthly_total"]
                rho_max = max_utilization_for_latency(tier, workload,
                                                      latency_target_s, percentile_frac, topo)
                max_t = tier_max_tps(tier, workload, latency_target_s, percentile_frac, topo)
                util = tps / max_t * rho_max if max_t > 0 else 0
                candidates.append((tier, topo, cost, util, rho_max))

    if not candidates:
        if verbose:
            print("  -> SONUC: infeasible (kapasite + latency birlikte saglanamiyor)\n")
        return None

    # 3. En dusuk toplam maliyetli kombinasyon
    best = min(candidates, key=lambda c: c[2]["total"])
    tier, topo, cost, util, rho_max = best

    if verbose:
        max_tps = tier_max_tps(tier, workload, latency_target_s, percentile_frac, topo)
        cp_eq = cp_equivalents(tier)
        # Gercek latency tahmini bilgi olarak goster
        if latency_target_s is not None:
            actual_lat_s = expected_latency_at(tier, workload, tps, percentile_frac, topo)
        else:
            actual_lat_s = None

        print(f"  -> SECILEN TOPOLOJI: {topo}")
        print(f"     {topo.description}")
        print(f"     effective availability: {topo.effective_availability_low():.6%} "
              f"(low) - {topo.effective_availability_high():.6%} (high)")
        print(f"  -> SECILEN KADEME: {tier} (her frame'de)")
        print(f"     tam-hiz CP esdegeri: {cp_eq:.2f}")
        print(f"     dinamik utilization tavani: %{rho_max*100:.1f} "
              f"(latency hedefinden turetildi)")
        print(f"     bu kademenin max TPS'i (latency altinda): {max_tps:,.0f}")
        if actual_lat_s is not None:
            print(f"     bu yukte tahmini p{latency_percentile} latency: "
                  f"{actual_lat_s*1000:.2f} ms (hedef: {latency_ms:g} ms)")
        print(f"     utilization: {util:.1%}  (x{topo.n_frames} frame)")
        print(f"     AYLIK maliyet: ${cost['total']:,.0f}")
        print(f"       yazilim:  ${cost['software']:,.0f}  "
              f"(z/OS + CICS TS + Db2, AWLC kademeli; premium x{topo.software_premium})")
        print(f"       donanim:  ${cost['hardware_amort']:,.0f}  "
              f"({topo.n_frames} frame; {ziip_engines(tier, workload)} zIIP, "
              f"f={ziip_fraction(workload):.2f})")
        print(f"       bakim:    ${cost['maintenance']:,.0f}")
        print(f"       enerji:   ${cost['energy']:,.0f}")
        sp = cost["storage_plan"]
        print(f"       storage:  ${cost['storage']:,.0f}  ({describe_storage(sp)})")
        print(f"     I/O: {sp['iops_required']:,.0f} IOPS, I/O basina {sp['io_service_time_s']*1e6:.0f} us, "
              f"islem basina D_io = {sp['io_delay_s']*1000:.2f} ms\n")
    return best


# ==============================================================================
# YILLIK SIMULASYON — WORKLOAD PROFILE + FIYATLAMA STRATEJILERI
# ==============================================================================
# 8760 saatlik profil uzerinde uc donanim edinim/fiyatlama stratejisi
# karsilastirilir:
#
#   A) Permanent    : peak'i karsilayan kademe satin alinir. Yazilim: aylik
#                     R4HA sub-capacity MLC.
#   B) Base + CoD   : kucuk base kademe satin alinir; base'in yetmedigi gunlerde
#                     On/Off CoD ile gecici upgrade (24 saatlik periyot, gun
#                     basina aktif kapasite uzerinden ucret). Yazilim: R4HA.
#   C) TFP          : Tailored Fit Pricing for IBM Z. Base kademe satin alinir;
#                     ustune her zaman acik bir "capacity corridor" (Hardware
#                     Consumption Solution) gelir ve corridor yalnizca base'in
#                     ustunde FIILEN tuketilen MSU kadar, saatlik olculerek
#                     ucretlendirilir. Corridor'u asan gunlerde On/Off CoD.
#                     Donanim corridor'u, yazilim tarafinda Software Consumption
#                     Solution'i sart kostugu icin yazilim yillik tuketilen
#                     MSU-saat x efektif fiyat ile faturalanir (R4HA yok).
#
# Gecici kapasite (corridor + CoD) kisitlari [COD]:
#   - Gecici kapasite satin alinan (permanent) kapasitenin %100'unu asamaz
#     (MSU olarak; yani aktif toplam <= 2 x base MSU).
#   - Fiziksel olarak kurulu kapasiteyi asamaz: gecici aktivasyon drawer
#     ekleyemez, yani hedef CP sayisi kurulu ozelligin (Max39/82/125/168/200)
#     sinirinda kalir. Ozellik varsayilan olarak base'i tasiyan en kucuk
#     ozelliktir (bos drawer satin alinmaz); drawer maliyeti modele girene
#     kadar (yol haritasi M4) bu bir parametredir.
#   - Gecici upgrade permanent alt-kapasite seviyesinin altina inemez ve
#     seviyeyi 4xx/5xx'e cekemez; hedef seri, base serisi veya daha yuksek
#     6xx/7xx olabilir. CP sayisi azalamaz.
#
# KAYNAKLAR (mevcut etiketlere ek):
#   [COD]     = IBM SC28-7025 Capacity on Demand User's Guide: On/Off CoD
#               24 saatlik faturalama, %100 siniri, kurulu kapasite siniri,
#               alt-kapasite kurallari, ayni anda tek aktif kayit.
#   [TFP-HW]  = IBM Z Content Solutions, "Tailored Fit Pricing": Hardware
#               Consumption Solution = "always-on, subscription-based corridor
#               of pay-for-use capacity, on top of purchased capacity";
#               z15+, z/OS genel amacli CP, Software Consumption Solution sart.
#   [TFP-TCO] = IBM IT Economics, TFP for IBM Z Hardware maliyet calismasi
#               (Mayis 2021): ornek corridor = yeni is yukunun %20'si.
#   [TFP-SW]  = IBM TFP Software Consumption Solution: gecmis 12 ayin MSU
#               tuketiminden efektif MSU fiyati, yillik MSU taahhudu, buyume
#               icin indirimli fiyat; R4HA/tepe/capping yok.
#   [R4HA]    = IBM MLC sub-capacity: aylik en yuksek 4-saatlik kayan ortalama
# ==============================================================================

# --- On/Off CoD -----------------------------------------------------------------
COD_DAILY_MULTIPLIER = 2.5        # [ASSUME] CoD gunluk ucret / permanent gunluk maliyet
COD_MAX_TEMP_FRACTION = 1.0       # [COD] gecici <= satin alinan kapasitenin %100'u (MSU)

# z16 A01 CPC drawer ozellikleri: (ad, musteri CP'si icin maks. PU) [SG24-8950]
CPC_FEATURES = [("Max39", 39), ("Max82", 82), ("Max125", 125),
                ("Max168", 168), ("Max200", 200)]

# --- TFP donanim corridor'u -----------------------------------------------------
CORRIDOR_FRACTION = 0.20          # [TFP-TCO] corridor genisligi = base MSU'nun %20'si
CORRIDOR_PREMIUM = 1.5            # [ASSUME] corridor MSU-saat fiyati / permanent esdegeri
CORRIDOR_SUBSCRIPTION_RATE = 0.0  # [ASSUME] aylik sabit abonelik, corridor kapasitesinin
                                  #   permanent aylik donanim maliyetine orani

# --- TFP yazilim (consumption) --------------------------------------------------
TFP_SW_DISCOUNT = 0.0             # [ASSUME] 0 = IBM'in gelir-notr baz fiyati [TFP-SW]

# --- Strateji aramasi -----------------------------------------------------------
BASE_MIN_AVG_FACTOR = 1.2         # [ASSUME] base kademe ortalama yukun >= 1.2 katini tasimali

_SERIES_ORDER = {"4xx": 0, "5xx": 1, "6xx": 2, "7xx": 3}

# Workload preset'leri
WORKLOAD_PRESETS = {
    "steady_oltp": {
        "peak_avg_ratio": 1.5,
        "peak_days": 10,
        "description": "Bankacilik core / kurumsal OLTP - duzgun trafik"
    },
    "retail_bursty": {
        "peak_avg_ratio": 3.5,
        "peak_days": 20,
        "description": "Perakende / e-ticaret - Black Friday, Noel"
    },
    "batch_heavy": {
        "peak_avg_ratio": 2.5,
        "peak_days": 30,
        "description": "Batch agirlikli - ay sonu, vergi donemi"
    },
}


def generate_hourly_profile(preset_name=None, yearly_avg_tps=50000,
                             peak_avg_ratio=None, peak_days=None):
    """8760 saatlik deterministik TPS profili."""
    if preset_name is not None:
        preset = WORKLOAD_PRESETS[preset_name]
        if peak_avg_ratio is None:
            peak_avg_ratio = preset["peak_avg_ratio"]
        if peak_days is None:
            peak_days = preset["peak_days"]
    else:
        if peak_avg_ratio is None:
            peak_avg_ratio = 2.0
        if peak_days is None:
            peak_days = 15

    HOURS = 8760
    # Gunluk desen: 14:00 peak, 03:00 dip
    daily = [1.0 + 0.5 * math.cos((h - 14) * 2 * math.pi / 24) for h in range(24)]
    # Haftalik desen: is gunu / hafta sonu
    weekly = [1.0, 1.0, 1.0, 1.0, 1.0, 0.65, 0.65]
    # Peak gunler: 365'i peak_days esit araliklara dagit
    peak_day_set = set()
    if peak_days > 0:
        step = max(1, 365 // peak_days)
        for i in range(peak_days):
            peak_day_set.add(i * step)
    peak_day_multiplier = peak_avg_ratio / 1.5

    profile = [0.0] * HOURS
    for h in range(HOURS):
        d = h // 24
        hod = h % 24
        wd = d % 7
        factor = daily[hod] * weekly[wd]
        if d in peak_day_set:
            factor *= peak_day_multiplier
        profile[h] = factor

    current_avg = sum(profile) / HOURS
    scale = yearly_avg_tps / current_avg
    return [p * scale for p in profile]


def r4ha_rolling(hourly_load):
    """4-saatlik kayan ortalama [R4HA]."""
    n = len(hourly_load)
    out = [0.0] * n
    for i in range(n):
        start = max(0, i - 3)
        window = hourly_load[start:i+1]
        out[i] = sum(window) / len(window)
    return out


def monthly_r4ha_peaks(hourly_load):
    """Her ay icin en yuksek R4HA (12 elemanli list)."""
    r4ha = r4ha_rolling(hourly_load)
    peaks = []
    for m in range(12):
        start = m * 730
        end = min(start + 730, len(r4ha))
        peaks.append(max(r4ha[start:end]))
    return peaks


def feature_for_cps(cps):
    """Verilen CP sayisini tasiyan en kucuk CPC drawer ozelligi -> (ad, maks CP)."""
    for name, max_cps in CPC_FEATURES:
        if cps <= max_cps:
            return name, max_cps
    raise ValueError(f"{cps} CP z16 A01'de kurulamaz")


def is_allowed_temporary_target(base, target, feature_max_cps=None):
    """Base kademeden hedef kademeye gecici (corridor/CoD) upgrade izinli mi? [COD]"""
    if feature_max_cps is None:
        feature_max_cps = feature_for_cps(base.cps)[1]
    if target.pci <= base.pci or target.cps < base.cps:
        return False
    if target.cps > feature_max_cps:                       # drawer eklenemez
        return False
    if target.msu > base.msu * (1.0 + COD_MAX_TEMP_FRACTION) + 1e-9:   # %100 siniri
        return False
    if target.series != base.series:                       # alt-kapasite kurallari
        if target.series not in ("6xx", "7xx"):
            return False
        if _SERIES_ORDER[target.series] < _SERIES_ORDER[base.series]:
            return False
    return True


def temporary_targets(base, feature_max_cps=None):
    """Base'den gecici olarak ulasilabilen kademeler, PCI'ya gore sirali."""
    return [t for t in Z16_TIERS
            if is_allowed_temporary_target(base, t, feature_max_cps)]


def max_temporary_tier(base, feature_max_cps=None):
    """Gecici olarak ulasilabilen en buyuk kademe (yoksa base'in kendisi)."""
    targets = temporary_targets(base, feature_max_cps)
    return targets[-1] if targets else base


def corridor_tier_for(base, fraction=None, feature_max_cps=None):
    """Corridor tavani: base MSU x (1 + fraction)'i karsilayan en kucuk izinli
    kademe. Kisitlar izin vermezse ulasilabilen en buyuk kademe; hic hedef
    yoksa None (corridor kurulamaz)."""
    if fraction is None:
        fraction = CORRIDOR_FRACTION
    targets = temporary_targets(base, feature_max_cps)
    if not targets:
        return None
    want = base.msu * (1.0 + fraction)
    for t in targets:
        if t.msu >= want:
            return t
    return targets[-1]


def hw_monthly_cost_per_pci():
    """Permanent donanimin PCI basina aylik maliyeti (amortisman + bakim)."""
    return (HARDWARE_COST_PER_MIPS / (HARDWARE_AMORTIZATION_YEARS * 12) +
            HARDWARE_COST_PER_MIPS * MAINTENANCE_RATE_ANNUAL / 12)


def consumed_pci(load_tps, workload=DEFAULT_WORKLOAD):
    """Bir yukun tukettigi GENEL AMACLI (GP) kapasite, PCI cinsinden
    (%100 utilization esdegeri). zIIP'e kayan pay dusulur."""
    w = get_workload(workload)
    return load_tps * w.cpu_weight() * (1.0 - ziip_fraction(w)) / TPS_PER_PCI


def simulate_yearly(profile, tier, topology, workload=DEFAULT_WORKLOAD,
                    latency_ms=None, latency_percentile=99,
                    strategy="permanent", corridor_tier=None,
                    feature_max_cps=None, sw_price_per_msu_hour=None,
                    storage_monthly=0.0):
    """Bir yillik saat-saat simulasyon ve maliyet.

    strategy:
      "permanent"   : yalnizca `tier` (satin alinan) kapasite.
      "base_cod"    : `tier` + gerektiginde On/Off CoD (gun bazinda).
      "tfp"         : `tier` + her zaman acik `corridor_tier` + gerekirse CoD.
                      Yazilim, sw_price_per_msu_hour x tuketilen MSU-saat.

    Her gun icin, gunun tepe yukunu tasiyan en kucuk izinli gecici kademe
    aktive edilir (CoD 24 saatlik periyotla faturalanir [COD]). Yuk
    izinli en buyuk gecici kademeyi de asarsa None doner (strateji infeasible).

    Gecici kapasite ucretleri tek frame icin hesaplanir: coklu-frame
    topolojilerde ikinci frame yalnizca failover icindir ve onun gecici
    kapasitesi CBU'nun konusudur (yol haritasi M5).
    """
    latency_target_s = (latency_ms / 1000.0) if latency_ms is not None else None
    pct = latency_percentile / 100.0
    HOURS = len(profile)
    DAYS = HOURS // 24

    def max_tps(t):
        return tier_max_tps(t, workload, latency_target_s, pct, topology)

    if strategy == "tfp":
        if corridor_tier is None:
            return None
        always_on = corridor_tier
    else:
        always_on = tier
    always_on_tps = max_tps(always_on)
    targets = []
    if strategy in ("base_cod", "tfp"):
        targets = [t for t in temporary_targets(tier, feature_max_cps)
                   if t.pci > always_on.pci]

    # --- gun bazinda aktif kademe -------------------------------------------
    day_tier = [always_on] * DAYS
    for d in range(DAYS):
        peak = max(profile[d*24:(d+1)*24])
        if peak <= always_on_tps:
            continue
        chosen = next((t for t in targets if max_tps(t) >= peak), None)
        if chosen is None:
            return None
        day_tier[d] = chosen

    cap_tps = [0.0] * HOURS
    util = [0.0] * HOURS
    cod_active = [False] * HOURS
    for i in range(HOURS):
        t = day_tier[min(i // 24, DAYS - 1)]
        cap_tps[i] = max_tps(t)
        cod_active[i] = t is not always_on
        util[i] = profile[i] / cap_tps[i] if cap_tps[i] > 0 else 0.0
    cod_days = sum(1 for t in day_tier if t is not always_on)

    # --- permanent donanim (her frame) ---------------------------------------
    base_cost = monthly_cost(tier, topology, workload=workload)
    base_other_monthly = (base_cost["hardware_amort"] + base_cost["maintenance"] +
                          base_cost["energy"])
    monthly_other = [base_other_monthly] * 12

    # --- On/Off CoD: gun basina, aktif gecici kapasite (always-on'un ustu) ----
    hw_pci_day = hw_monthly_cost_per_pci() / 30.0
    cod_cost_total = sum((t.pci - always_on.pci) * hw_pci_day * COD_DAILY_MULTIPLIER
                         for t in day_tier if t is not always_on)

    # --- TFP corridor: base'in ustunde tuketilen PCI, saatlik [TFP-HW] -------
    corridor_cost_total = 0.0
    if strategy == "tfp":
        hw_pci_hour = hw_monthly_cost_per_pci() / HOURS_PER_MONTH
        for load in profile:
            used = min(consumed_pci(load, workload), corridor_tier.pci) - tier.pci
            if used > 0:
                corridor_cost_total += used * hw_pci_hour * CORRIDOR_PREMIUM
        corridor_cost_total += ((corridor_tier.pci - tier.pci) * hw_monthly_cost_per_pci()
                                * CORRIDOR_SUBSCRIPTION_RATE * 12)

    # --- yazilim -------------------------------------------------------------
    r4ha_peaks = monthly_r4ha_peaks(profile)
    month_len = HOURS_PER_MONTH_INT
    monthly_software = []
    msu_hours = 0.0
    for m in range(12):
        hours = range(m * month_len, min((m + 1) * month_len, HOURS))
        if strategy == "tfp":
            mh = sum(consumed_msu(day_tier[min(h // 24, DAYS - 1)], profile[h], workload)
                     for h in hours)
            msu_hours += mh
            monthly_software.append(mh * (sw_price_per_msu_hour or 0.0)
                                    * topology.software_premium)
        else:
            # ayin en buyuk aktif kademesi faturalanabilir tavandir
            cap_tier = max((day_tier[min(h // 24, DAYS - 1)] for h in hours),
                           key=lambda t: t.pci)
            billed = consumed_msu(cap_tier, r4ha_peaks[m], workload)
            monthly_software.append(
                monthly_cost(cap_tier, topology, billed_msu=billed,
                             workload=workload)["software"])

    yearly_software = sum(monthly_software)
    yearly_other = sum(monthly_other)
    yearly_storage = 12.0 * storage_monthly
    yearly_total = (yearly_software + yearly_other + yearly_storage +
                    cod_cost_total + corridor_cost_total)

    return {
        "hourly_load": profile,
        "hourly_capacity_tps": cap_tps,
        "hourly_utilization": util,
        "hourly_cod_active": cod_active,
        "monthly_r4ha_peaks": r4ha_peaks,
        "monthly_cost_software": monthly_software,
        "monthly_cost_other": monthly_other,
        "msu_hours": msu_hours,
        "cod_days": cod_days,
        "cod_cost_total": cod_cost_total,
        "corridor_cost_total": corridor_cost_total,
        "yearly_software": yearly_software,
        "yearly_other": yearly_other,
        "yearly_storage": yearly_storage,
        "yearly_total": yearly_total,
        "base_tier": tier,
        "corridor_tier": corridor_tier if strategy == "tfp" else None,
        "peak_tier": max(day_tier, key=lambda t: t.pci) if cod_days else None,
        "feature": feature_for_cps(tier.cps)[0] if feature_max_cps is None
                   else next(n for n, c in CPC_FEATURES if c == feature_max_cps),
        "topology": topology,
        "strategy": strategy,
    }


HOURS_PER_MONTH_INT = 730

STRATEGY_LABELS = {
    "permanent": "Strateji A: Permanent peak kademe",
    "base_cod":  "Strateji B: Base kademe + On/Off CoD",
    "tfp":       "Strateji C: Tailored Fit Pricing (base + corridor + CoD)",
}


def tfp_software_price_per_msu_hour(profile, reference_sim, reference_tier, workload=DEFAULT_WORKLOAD):
    """TFP-SW efektif MSU-saat fiyati [TFP-SW]: IBM fiyati musterinin gecmis
    12 ayindan belirler. Burada 'gecmis yil' = ayni profilin permanent
    konfigurasyondaki R4HA faturasi; fiyat bu faturayi ayni yilin tuketilen
    MSU-saatine bolerek bulunur (gelir-notr), sonra TFP_SW_DISCOUNT uygulanir."""
    msu_hours = sum(consumed_msu(reference_tier, load, workload) for load in profile)
    base_sw = reference_sim["yearly_software"] / reference_sim["topology"].software_premium
    return base_sw / msu_hours * (1.0 - TFP_SW_DISCOUNT)


def solve_yearly(preset_name=None, yearly_avg_tps=50000,
                 peak_avg_ratio=None, peak_days=None,
                 availability=0.999, workload=DEFAULT_WORKLOAD,
                 latency_ms=None, latency_percentile=99,
                 strategies=("permanent", "base_cod", "tfp"),
                 verbose=True, data_tb=None, data_growth=None):
    """Yillik simulasyon + strateji karsilastirmasi. En ucuz strateji, diger
    stratejilerin en iyi sonuclari 'alternatives' listesinde doner."""
    profile = generate_hourly_profile(preset_name=preset_name,
                                      yearly_avg_tps=yearly_avg_tps,
                                      peak_avg_ratio=peak_avg_ratio,
                                      peak_days=peak_days)
    peak_load = max(profile)
    avg_load = sum(profile) / len(profile)

    feasible_topos = find_feasible_topologies(availability)
    if not feasible_topos:
        if verbose:
            print("HATA: hicbir topoloji bu availability hedefini saglayamiyor")
        return None

    latency_target_s = (latency_ms / 1000.0) if latency_ms is not None else None
    pct = latency_percentile / 100.0

    if verbose:
        desc = (WORKLOAD_PRESETS[preset_name]["description"]
                if preset_name else "custom")
        print(f"  Workload: {preset_name or 'custom'} - {desc}")
        print(f"    yillik ortalama: {avg_load:,.0f} TPS  |  peak saat: {peak_load:,.0f} TPS")
        print(f"    peak/avg orani: {peak_load/avg_load:.2f}x")
        print(f"  Availability hedefi: {availability:.6%}  |  is yuku: {get_workload(workload)}")
        if latency_ms is not None:
            print(f"  Latency hedefi: p{latency_percentile} < {latency_ms:g} ms")
        print()

    best_by_strategy = {}
    for topo in feasible_topos:
        perm_tier = next((t for t in Z16_TIERS
                          if is_capacity_feasible(t, peak_load, workload, latency_target_s,
                                                  pct, topo)),
                         None)
        if perm_tier is None:
            continue
        splan = storage_plan(peak_load, workload, topo, data_tb, data_growth)
        st_m = splan["monthly_total"]
        sim_perm = simulate_yearly(profile, perm_tier, topo, workload, latency_ms,
                                   latency_percentile, strategy="permanent",
                                   storage_monthly=st_m)
        sw_price = tfp_software_price_per_msu_hour(profile, sim_perm, perm_tier, workload)

        candidates = {"permanent": [sim_perm]} if "permanent" in strategies else {}
        for base in Z16_TIERS:
            if base.pci >= perm_tier.pci:
                break
            if not is_capacity_feasible(base, avg_load * BASE_MIN_AVG_FACTOR, workload,
                                        latency_target_s, pct, topo):
                continue
            # hizli eleme: izinli en buyuk gecici kademe bile peak'i tasimiyorsa atla
            if tier_max_tps(max_temporary_tier(base), workload, latency_target_s, pct,
                            topo) < peak_load:
                continue
            if "base_cod" in strategies:
                s = simulate_yearly(profile, base, topo, workload, latency_ms,
                                    latency_percentile, strategy="base_cod",
                                    storage_monthly=st_m)
                if s is not None:
                    candidates.setdefault("base_cod", []).append(s)
            if "tfp" in strategies:
                corr = corridor_tier_for(base)
                if corr is not None:
                    s = simulate_yearly(profile, base, topo, workload, latency_ms,
                                        latency_percentile, strategy="tfp",
                                        corridor_tier=corr,
                                        sw_price_per_msu_hour=sw_price,
                                        storage_monthly=st_m)
                    if s is not None:
                        candidates.setdefault("tfp", []).append(s)

        for name, sims in candidates.items():
            best = min(sims, key=lambda s: s["yearly_total"])
            best["storage_plan"] = splan
            if (name not in best_by_strategy or
                    best["yearly_total"] < best_by_strategy[name]["yearly_total"]):
                best_by_strategy[name] = best

    if not best_by_strategy:
        if verbose:
            print("HATA: hicbir feasible kombinasyon bulunamadi")
        return None

    for name, s in best_by_strategy.items():
        s["strategy_label"] = STRATEGY_LABELS[name]
    ranked = sorted(best_by_strategy.values(), key=lambda s: s["yearly_total"])
    best_overall = ranked[0]
    best_overall["alternatives"] = ranked[1:]
    best_overall["alternative"] = ranked[1] if len(ranked) > 1 else None
    best_overall["by_strategy"] = best_by_strategy
    if verbose:
        _print_yearly_summary(best_overall)
    return best_overall


def _print_yearly_summary(sim):
    print("=" * 70)
    print("YILLIK SIMULASYON OZETI")
    print("=" * 70)
    print(f"Secilen strateji: {sim['strategy_label']}")
    _print_strategy_detail(sim)
    for alt in sim.get("alternatives", []):
        diff = alt["yearly_total"] - sim["yearly_total"]
        pct = diff / alt["yearly_total"] * 100 if alt["yearly_total"] > 0 else 0
        print(f"\nAlternatif: {alt['strategy_label']}")
        _print_strategy_detail(alt)
        print(f"  -> secilen strateji bundan ${diff:,.0f} (%{pct:.1f}) ucuz")
    print()


def _print_strategy_detail(sim):
    print(f"  Topoloji:          {sim['topology']}")
    print(f"  Base kademe:       {sim['base_tier']}  [{sim['feature']}]")
    if sim.get("corridor_tier"):
        print(f"  Corridor tavani:   {sim['corridor_tier']}")
    if sim["peak_tier"]:
        print(f"  CoD tepe kademe:   {sim['peak_tier']}  ({sim['cod_days']} gun / 365)")
    util = sim["hourly_utilization"]
    print(f"  Utilization (tavana gore): ort. {sum(util)/len(util):.1%}  maks. {max(util):.1%}")
    sw_label = "consumption, MSU-saat" if sim["strategy"] == "tfp" else "R4HA"
    print(f"  Yazilim ({sw_label}):".ljust(34) + f"${sim['yearly_software']:>13,.0f}")
    print(f"  Donanim + bakim + enerji:".ljust(34) + f"${sim['yearly_other']:>13,.0f}")
    if sim.get("yearly_storage"):
        print(f"  Storage (DS8900F):".ljust(34) + f"${sim['yearly_storage']:>13,.0f}"
              f"  [{describe_storage(sim['storage_plan'])}]")
    if sim["corridor_cost_total"]:
        print(f"  TFP corridor kullanimi:".ljust(34) + f"${sim['corridor_cost_total']:>13,.0f}")
    if sim["cod_cost_total"]:
        print(f"  On/Off CoD:".ljust(34) + f"${sim['cod_cost_total']:>13,.0f}")
    print(f"  TOPLAM:".ljust(34) + f"${sim['yearly_total']:>13,.0f}")


def export_yearly_csv(sim, filepath):
    """Grafik-hazir CSV: <filepath>_hourly.csv + <filepath>_monthly.csv"""
    base = filepath.replace(".csv", "")
    with open(f"{base}_hourly.csv", "w") as f:
        f.write("hour,load_tps,capacity_tps,utilization,cod_active\n")
        for i in range(len(sim["hourly_load"])):
            f.write(f"{i},{sim['hourly_load'][i]:.2f},"
                    f"{sim['hourly_capacity_tps'][i]:.2f},"
                    f"{sim['hourly_utilization'][i]:.4f},"
                    f"{1 if sim['hourly_cod_active'][i] else 0}\n")
    with open(f"{base}_monthly.csv", "w") as f:
        f.write("month,r4ha_peak_tps,software_cost,other_cost\n")
        for m in range(12):
            f.write(f"{m+1},{sim['monthly_r4ha_peaks'][m]:.2f},"
                    f"{sim['monthly_cost_software'][m]:.2f},"
                    f"{sim['monthly_cost_other'][m]:.2f}\n")
    print(f"CSV yazildi: {base}_hourly.csv, {base}_monthly.csv")


# ==============================================================================
# CLI — TERMINAL'DEN GIRDI
# ==============================================================================
# Kullanim ornekleri:
#
#   python mainframe_model.py --tps 50000
#   python mainframe_model.py --tps 80000 --availability 0.9993 --workload high
#   python mainframe_model.py --demo          (5 hazir senaryo)
#   python mainframe_model.py --calibration   (kalibrasyon kontrolu)
#
# Parametreler:
#   --tps           Saniyedeki islem sayisi (zorunlu, --demo yoksa)
#   --availability  Hedef uptime, 0-1 arasi (varsayilan: 0.999 = %99.9)
#   --workload      Is yuku profili: redp_light / tpcb_like / oltp_rw / oltp_heavy
#                   (varsayilan: oltp_rw); --sql-reads/--sql-writes ile ozel bilesim
#   --demo          5 hazir senaryo calistir
#   --calibration   Kalibrasyon sabitlerini yazdir
# ==============================================================================

import argparse
import sys


def print_calibration():
    print("=" * 70)
    print("KALIBRASYON KONTROLU")
    print("=" * 70)
    n = {}
    for t in Z16_TIERS:
        n[t.series] = n.get(t.series, 0) + 1
    derived = sum(1 for t in Z16_TIERS if t.pci_source != "LSPR")
    print(f"Kademe tablosu : {len(Z16_TIERS)} kademe {dict(sorted(n.items()))}")
    print(f"                 PCI kaynagi: {len(Z16_TIERS)-derived} LSPR, {derived} MSU'dan turetilmis")
    print()
    print("KAPASITE KOPRUSU (z13 benchmark -> PCI basina TPS) [REDP + LSPR]:")
    print(f"  2964-718: {_Z13_718_TPS:,.0f} TPS / {_Z13_718_PCI:,.0f} PCI = {_TPS_PER_PCI_718:.3f} TPS/PCI")
    print(f"  2964-726: {_Z13_726_TPS:,.0f} TPS / {_Z13_726_PCI:,.0f} PCI = {_TPS_PER_PCI_726:.3f} TPS/PCI")
    print(f"  TPS_PER_PCI (ortalama): {TPS_PER_PCI:.3f}  "
          f"(iki nokta arasi fark %{100*(_TPS_PER_PCI_718-_TPS_PER_PCI_726)/TPS_PER_PCI:.1f})")
    print()
    print("Ornek z16 kademeleri:")
    for code in ["3931-401", "3931-604", "3931-701", "3931-718", "3931-726",
                 "3931-739", "3931-7A0", "3931-7K0"]:
        t = next(x for x in Z16_TIERS if x.model == code)
        print(f"   {str(t):<45} | ham TPS={raw_tier_tps(t):>10,.0f} | "
              f"%90'da={tier_max_tps(t):>10,.0f} | PCI kaynagi={t.pci_source}")


def run_demo():
    print("=" * 70)
    print("DEMO SENARYOLAR")
    print("=" * 70)
    print("\n[A] Orta yuk OLTP (latency hedefi yok, %90 sabit tavan):")
    solve(tps=50000, availability=0.999, workload=DEFAULT_WORKLOAD)
    print("[B] Ayni yuk, p99 < 200 ms latency hedefi:")
    solve(tps=50000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=200, latency_percentile=99)
    print("[C] Ayni yuk, sikilastirilmis p99 < 50 ms (trading-seviyesi):")
    solve(tps=50000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=50, latency_percentile=99)
    print("[D] Yuksek yuk + yuksek uptime + p99 < 500 ms:")
    solve(tps=150000, availability=0.99999, workload=DEFAULT_WORKLOAD,
          latency_ms=500, latency_percentile=99)
    print("[E] Agir islemler (oltp_heavy) + p99 < 200 ms:")
    solve(tps=50000, availability=0.999, workload="oltp_heavy",
          latency_ms=200, latency_percentile=99)
    print("[F] Cok dusuk yuk:")
    solve(tps=2000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=200, latency_percentile=99)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mainframe (IBM z16) minimum-cost feasibility modeli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  Statik (tek nokta):
    python mainframe_model.py --tps 50000
    python mainframe_model.py --tps 80000 --availability 0.9993 --workload high --latency-ms 200

  Yillik simulasyon (workload profile + CoD karsilastirmasi):
    python mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000
    python mainframe_model.py --yearly --preset steady_oltp --avg-tps 30000 --availability 0.99999
    python mainframe_model.py --yearly --avg-tps 40000 --peak-ratio 3 --peak-days 25 --csv out

  Diger:
    python mainframe_model.py --demo
    python mainframe_model.py --calibration
        """
    )
    # Statik mod parametreleri
    parser.add_argument("--tps", type=float,
                        help="(STATIK MOD) Hedef throughput: saniyedeki islem sayisi")

    # Yillik mod parametreleri
    parser.add_argument("--yearly", action="store_true",
                        help="(YILLIK MOD) Yillik workload simulasyonu calistir")
    parser.add_argument("--preset",
                        choices=list(WORKLOAD_PRESETS.keys()),
                        default=None,
                        help="(YILLIK) Workload preset: steady_oltp / retail_bursty / batch_heavy")
    parser.add_argument("--avg-tps", type=float, default=50000,
                        help="(YILLIK) Yillik ortalama TPS (varsayilan: 50000)")
    parser.add_argument("--peak-ratio", type=float, default=None,
                        help="(YILLIK) Peak/avg orani; preset'i override eder")
    parser.add_argument("--peak-days", type=int, default=None,
                        help="(YILLIK) Yillik peak gun sayisi; preset'i override eder")
    parser.add_argument("--csv", type=str, default=None,
                        help="(YILLIK) Grafik-hazir CSV cikti dosyasi prefix'i "
                             "(orn. 'out' -> out_hourly.csv + out_monthly.csv)")

    # Ortak parametreler
    parser.add_argument("--availability", type=float, default=0.999,
                        help="Hedef uptime, 0-1 arasi (varsayilan: 0.999)")
    parser.add_argument("--workload", choices=list(WORKLOAD_PROFILES),
                        default=DEFAULT_WORKLOAD,
                        help=f"Is yuku profili (varsayilan: {DEFAULT_WORKLOAD})")
    parser.add_argument("--sql-reads", type=float, default=None,
                        help="Ozel profil: islem basina okuma SQL sayisi")
    parser.add_argument("--sql-writes", type=float, default=None,
                        help="Ozel profil: islem basina yazma SQL sayisi")
    parser.add_argument("--latency-ms", type=float, default=None,
                        help="Hedef latency milisaniye (orn: 200)")
    parser.add_argument("--latency-percentile", type=int, default=99,
                        choices=[50, 90, 95, 99],
                        help="Latency percentile hedefi (varsayilan: 99)")

    # Storage
    parser.add_argument("--data-tb", type=float, default=None,
                        help=f"Mantiksal Db2 veri hacmi, TB (varsayilan: {DEFAULT_DATA_VOLUME_TB:g})")
    parser.add_argument("--data-growth", type=float, default=None,
                        help=f"Yillik veri buyumesi, oran (varsayilan: {DEFAULT_DATA_GROWTH:g})")

    # Yardimci moDlar
    parser.add_argument("--demo", action="store_true",
                        help="Hazir demo senaryolar calistir")
    parser.add_argument("--calibration", action="store_true",
                        help="Kalibrasyon sabitlerini yazdir")

    args = parser.parse_args()

    if args.sql_reads is not None or args.sql_writes is not None:
        args.workload = WorkloadProfile("custom", args.sql_reads or 0.0,
                                        args.sql_writes or 0.0, 1, True,
                                        "Ozel bilesim", "USER")

    if args.calibration:
        print_calibration()
        sys.exit(0)

    if args.demo:
        run_demo()
        sys.exit(0)

    # YILLIK MOD
    if args.yearly:
        print("=" * 70)
        print("MAINFRAME YILLIK SIMULASYON MODELI")
        print("=" * 70)
        result = solve_yearly(
            preset_name=args.preset,
            yearly_avg_tps=args.avg_tps,
            peak_avg_ratio=args.peak_ratio,
            peak_days=args.peak_days,
            availability=args.availability,
            workload=args.workload,
            latency_ms=args.latency_ms,
            latency_percentile=args.latency_percentile,
            data_tb=args.data_tb,
            data_growth=args.data_growth,
        )
        if result is None:
            sys.exit(1)
        if args.csv:
            export_yearly_csv(result, args.csv)
        sys.exit(0)

    # STATIK MOD (varsayilan)
    if args.tps is None:
        parser.print_help()
        print("\nHata: --tps (statik) veya --yearly (yillik) modlardan biri gerekli")
        sys.exit(1)

    print("=" * 70)
    print("MAINFRAME FEASIBILITY MODELI (STATIK)")
    print("=" * 70)
    result = solve(tps=args.tps,
                   availability=args.availability,
                   workload=args.workload,
                   latency_ms=args.latency_ms,
                   latency_percentile=args.latency_percentile,
                   data_tb=args.data_tb,
                   data_growth=args.data_growth)
    if result is None:
        print("Tek z16 frame bu is yukunu karsilayamiyor.")
        sys.exit(1)
