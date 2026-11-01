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
  4. Availability, RPO ve RTO hedeflerini karsilayan topolojiler (M1-M4)
     filtrelenir. Availability olay tabanlidir: saha olayi sikligi x
     topolojinin kurtarma suresi + planli kesinti. DR frame'i CBU ile,
     GDPS sabit aylik kalem olarak fiyatlanir.
  5. Storage (IBM DS8900F): veri hacmi, IOPS ve topolojiye bagli kopya
     sayisindan boyutlandirma ve maliyet; I/O gecikmesi (D_io) storage
     yolundan (zHyperLink, zHPF/FICON, senkron Metro Mirror) hesaplanir.
  6. Maliyet: yazilim yigini (z/OS + CICS TS + Db2) IBM AWLC kumulatif
     kademeli fiyatla, faturalanan (sub-capacity) MSU uzerinden; zIIP payi
     MSU'ya sayilmaz, zIIP motorlari donanima eklenir.
     Altyapi personeli kapasiteyle alt-dogrusal FTE egrisinden (3 senaryo).
  7. Tum (kademe x topoloji) kombinasyonlarindan en ucuzu secilir. Kesin
     fiyati olmayan parametreler icin --range low/mid/high aralik verir.
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
  [SG24-8446]= IBM Z Resiliency Redbook: desenler, genel RTO/RPO araliklari
  [SG24-6374]= IBM GDPS Redbook, Tablo 1-1 (DR seceneklerinin RPO/RTO'su)
  [GDPS-2026]= S. Cook (IBM GDPS Dev.), VM Workshop 2026: GDPS RPO/RTO degerleri
  [GDPS-CA-2021] = IBM GDPS CA sunumu: planli kesinti 4 saat -> <30 sn
  [CBU]      = SC28-7025 CBU bolumu: test/aktivasyon kurallari, DR yazilim kurali
  [UPTIME-2025], [UPTIME-2022] = Uptime Institute Annual Outage Analysis
  [ITIC-2023]= ITIC sunucu donanim guvenilirligi (yalnizca D_cpc terimi)
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
  [IBM-EAGLE] = IBM Eagle TCO: "5 FTE + her 625 MIPS icin 1 FTE" (17 musteri)
  [GARTNER-ITKMD] = Gartner IT Key Metrics 2016: MIPS/FTE 152 -> 268
  [BLS-OEWS], [BLS-ECEC] = BLS maas medyanlari (2025) ve yan hak payi (%30)
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

    def sync_read_io(self):
        """Senkron okuma I/O'su: buffer pool iskasi. Olculmus profilde 0
        (REDP'nin senkron I/O'su VSAM rewrite, yani yazma)."""
        if self._sync_io is not None:
            return 0.0
        return self.reads * GETPAGES_PER_SQL_READ * (1.0 - BP_HIT_RATIO)

    def sync_write_io(self):
        """Senkron yazma I/O'su: commit'te log yazimi (olculmus profilde rewrite)."""
        if self._sync_io is not None:
            return self._sync_io
        return self.commits * LOG_SYNC_IO_PER_COMMIT

    def sync_io(self):
        return self.sync_read_io() + self.sync_write_io()

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

# I/O servis suresi parametreleri (mainframe storage yolu: z16 <-> DS8900F)
CACHE_HIT_RATIO = 0.90         # [ASSUME] DS8900F onbellek isabet orani (okuma)
ZHYPERLINK_ENABLED = True      # z16 + DS8900F zHyperLink [REDP-5554]
ZHYPERLINK_READ_SHARE = 0.80   # [ASSUME] isabetli okumalarin zHyperLink'e uygun payi
                               #   (Db2 senkron rastgele okumalar; digerleri zHPF/FICON)
T_ZHYPERLINK_S = 20e-6         # [REDP-5554] zHyperLink kucuk blok okuma < 20 us (~18 us)
T_FICON_HIT_S = 90e-6          # [TT-2019] zHPF/FICON, DS8900F onbellek isabeti ~90 us
T_FLASH_MISS_S = 300e-6        # [ASSUME] onbellek iskasi: flash arka uc + FICON
REPLICATION_S_PER_KM = 10e-6   # [FIZIK] fiberde isik ~5 us/km tek yon -> 10 us/km gidis-donus
METRO_DISTANCE_KM = 20.0       # [ASSUME] senkron Metro Mirror siteleri arasi mesafe


def io_read_time_seconds():
    """Senkron okuma I/O'sunun servis suresi (saniye):
    isabet x (zHyperLink payi x t_zHL + kalan x t_FICON) + iska x t_miss."""
    z = ZHYPERLINK_READ_SHARE if ZHYPERLINK_ENABLED else 0.0
    return (CACHE_HIT_RATIO * (z * T_ZHYPERLINK_S + (1.0 - z) * T_FICON_HIT_S) +
            (1.0 - CACHE_HIT_RATIO) * T_FLASH_MISS_S)


def io_write_time_seconds(topology=None):
    """Senkron yazma I/O'sunun servis suresi (saniye): t_FICON (DS8900F NVS'e
    hizli yazma) + topolojide senkron kopya varsa replikasyon gecikmesi."""
    t = T_FICON_HIT_S
    if topology is not None and getattr(topology, "sync_replication", False):
        t += METRO_DISTANCE_KM * REPLICATION_S_PER_KM
    return t


def io_delay_seconds(workload=DEFAULT_WORKLOAD, topology=None):
    """Transaction basina deterministik I/O gecikmesi (saniye): okuma ve yazma
    I/O'lari profilin kendi bilesimiyle ve kendi servis sureleriyle."""
    w = get_workload(workload)
    return (w.sync_read_io() * io_read_time_seconds()
            + w.sync_write_io() * io_write_time_seconds(topology))


def io_service_time_seconds(topology=None, workload=DEFAULT_WORKLOAD):
    """Profilin I/O basina ortalama servis suresi (raporlama icin)."""
    n = get_workload(workload).sync_io()
    return io_delay_seconds(workload, topology) / n if n > 0 else 0.0


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
# AVAILABILITY MODELI — OLAY TABANLI, KURTARMA SURESINE BAGLI
# ------------------------------------------------------------------------------
# Hizmetin yillik kesintisi, kesinti doguran olaylarin sikligi ile topolojinin
# bu olaylardan kurtarma suresinin carpimidir:
#
#   D(topo) = lam_saha x [(1-p_uzun) x min(d_kisa, T_rec) + p_uzun x min(d_uzun, T_rec)]
#           + lam_planli x T_planli(topo)
#           + D_cpc (yalnizca tek CPC'li topolojide)
#   A(topo) = 1 - D / 8760 saat
#
#   lam_saha, d_kisa, d_uzun, p_uzun : veri merkezi duzeyinde hizmet kesintisi
#       (guc, ag/BT, insan hatasi) sikligi ve suresi  [UPTIME-2025, UPTIME-2022]
#   T_rec  : hizmetin alternatif CPC/sitede geri gelme suresi (RTO)
#            [GDPS-2026, SG24-8446, SG24-6374]; M1'de alternatif site yok (T = sonsuz)
#   T_planli: kesinti gerektiren planli islem (POR, nesil gecisi) basina hizmet
#            kesintisi; sysplex icinde rolling IPL z/OS bakimini maskeler [ASSUME]
#   D_cpc  : CPC donaniminin kendi plansiz kesintisi [ITIC-2023]; yilda 0,03-3 sn,
#            pratikte ihmal edilebilir oldugu gostermek icin modelde tutulur.
#
# Onceki surumdeki "ITIC + x10 planli kesinti" yaklasimi birakildi: ITIC
# rakamlari sunucu donaniminin kesintisini olcer (z16: yilda 31,56 ms), hizmetin
# degil; SG24-8446 ise desenlere "nine" degeri atamaz. Her parametre low / mid /
# high aralik olarak tanimlidir; "low" mainframe lehine (az kesinti) uctur.

SITE_EVENT_SCENARIOS = {
    # rate: olay/yil; d_short_h / d_long_h: saat; p_long: uzun olay payi
    #  [UPTIME-2025] operatorlerin %53'u son 3 yilda kesinti bildirdi -> ~0,25/yil
    #  (ust uc); ciddi/agir pay %9 -> alt uc. [UPTIME-2022] kamuya yansiyan
    #  kesintilerin >24 saat suren payi %8 (2017) -> ~%30 (2021).
    "low":  {"rate": 0.05, "d_short_h": 1.0, "p_long": 0.08, "d_long_h": 24.0},
    "mid":  {"rate": 0.15, "d_short_h": 2.0, "p_long": 0.15, "d_long_h": 48.0},
    "high": {"rate": 0.25, "d_short_h": 4.0, "p_long": 0.30, "d_long_h": 72.0},
}
# Saha olayinda hizmetin geri gelme suresi, dakika (M1: alternatif site yok)
RECOVERY_MINUTES = {
    "M2": {"low": 60.0, "mid": 120.0, "high": 240.0},   # [SG24-6374 T1-1: depolama
          # replikasyonuyla "one or more hours"; SG24-8446: <2 saat GDPS ister]
    "M3": {"low": 2.0, "mid": 30.0, "high": 60.0},      # [GDPS-2026] GDPS Metro / MGM:
          # cok-siteli is yukunde ~2 dk, tek siteli is yukunde <1 saat
    "M4": {"low": 20 / 60, "mid": 0.5, "high": 1.0},    # [GDPS-2026] GDPS CA: 20-30 sn;
          # portfoy slaydi <60 sn
}
PLANNED_EVENTS_PER_YEAR = {"low": 0.25, "mid": 0.5, "high": 1.0}   # [ASSUME] kesinti
          # gerektiren CPC duzeyi planli islem (POR, nesil gecisi, kapasite disi upgrade)
PLANNED_OUTAGE_MINUTES = {                                        # olay basina kesinti
    "M1": {"low": 120.0, "mid": 240.0, "high": 480.0},  # [ASSUME] tek CPC durur
    "M2": {"low": 15.0, "mid": 30.0, "high": 60.0},     # [ASSUME] planli, elle gecis
    "M3": {"low": 2.0, "mid": 10.0, "high": 30.0},      # [ASSUME] GDPS planli site gecisi
    "M4": {"low": 20 / 60, "mid": 0.5, "high": 1.0},    # [GDPS-CA-2021] planli kesinti
          # "4 saatten 30 saniyenin altina" (banka ornegi)
}
CPC_HW_DOWNTIME_SECONDS = {"low": 0.0316, "mid": 0.315, "high": 3.15}  # [ITIC-2023]
          # z16 9 nine / IBM ortalamasi 8 nine / z13-z15 7 nine
SITE_EVENT_LEVEL = "mid"    # aralik parametreleri (RANGE_PARAMETERS)
RECOVERY_LEVEL = "mid"
PLANNED_LEVEL = "mid"
HOURS_PER_YEAR = 8760.0


class Topology:
    """Bir mainframe availability topolojisi (IBM Z Resiliency desenlerine eslenir)."""
    def __init__(self, code, name, n_frames, pattern, gdps=None, rpo_seconds=0.0,
                 description="", storage_copies=1, sync_replication=False):
        self.code = code                # 'M1', 'M2', 'M3', 'M4'
        self.name = name
        self.n_frames = n_frames        # birincil + DR (CBU) frame sayisi
        self.pattern = pattern          # SG24-8446 deseni
        self.gdps = gdps                # GDPS teklifi (None, "metro_global", "ca")
        self.rpo_seconds = rpo_seconds  # tek site kaybinda RPO  [GDPS-2026]
        self.description = description
        self.storage_copies = storage_copies      # DS8900F veri kopyasi (dizi) sayisi
        self.sync_replication = sync_replication  # senkron Metro Mirror var mi
        # Yazilim primi yok: DR (CBU) makinesinin IBM yazilim faturasi yalnizca
        # kalici kapasitesine gore kesilir [CBU]; GDPS ayri kalemdir (gdps_monthly_cost).
        self.software_premium = 1.0

    @property
    def cost_multiplier(self):
        """Donanim amortismani ve bakim carpani: birincil frame + DR frame'leri.
        DR frame'i CBU ile alinir: fiziksel donanim kurulu, kapasitenin kucuk bir
        kismi kalici, geri kalani CBU kaydi [CBU]. Bedeli tam frame'in
        DR_FRAME_COST_FRACTION'i kadar [ASSUME]; 1.0 = CBU'suz tam ayna."""
        return 1.0 + (self.n_frames - 1) * DR_FRAME_COST_FRACTION

    def recovery_minutes(self, level=None):
        """Saha olayinda hizmetin geri gelme suresi (dk); M1'de sonsuz."""
        r = RECOVERY_MINUTES.get(self.code)
        return float("inf") if r is None else r[level or RECOVERY_LEVEL]

    @property
    def rto_minutes(self):
        """RTO kisitinda kullanilan deger. M1: alternatif site yok; yedekten geri
        donus SG24-8446'nin GDPS'siz DR araliginin (2-72 saat) ust ucu."""
        r = self.recovery_minutes()
        return 72 * 60.0 if r == float("inf") else r

    def annual_downtime_hours(self, site=None, recovery=None, planned=None):
        """Yillik beklenen hizmet kesintisi (saat), olay tabanli."""
        s = SITE_EVENT_SCENARIOS[site or SITE_EVENT_LEVEL]
        t_rec = self.recovery_minutes(recovery) / 60.0
        unplanned = s["rate"] * ((1 - s["p_long"]) * min(s["d_short_h"], t_rec)
                                 + s["p_long"] * min(s["d_long_h"], t_rec))
        p = planned or PLANNED_LEVEL
        planned_h = PLANNED_EVENTS_PER_YEAR[p] * PLANNED_OUTAGE_MINUTES[self.code][p] / 60.0
        hw = (CPC_HW_DOWNTIME_SECONDS[site or SITE_EVENT_LEVEL] / 3600.0
              if self.n_frames == 1 else 0.0)
        return unplanned + planned_h + hw

    def availability(self, site=None, recovery=None, planned=None):
        return 1.0 - self.annual_downtime_hours(site, recovery, planned) / HOURS_PER_YEAR

    def availability_range(self):
        """(en kotu, en iyi): tum availability parametreleri high / low ucunda."""
        return (self.availability("high", "high", "high"),
                self.availability("low", "low", "low"))

    def __repr__(self):
        return f"{self.code}: {self.name}"


# IBM Z Resiliency desenleri [SG24-8446]: Reliable base / Failover capable /
# Fault tolerant / Adaptive continuity. Saf tek-imaj (sysplex'siz) production
# disinda birakildi; M1 tek CPC uzerinde sysplex'tir (rolling IPL).
TOPOLOGIES = [
    Topology(
        code="M1",
        name="Single-frame sysplex (ICF)",
        n_frames=1,
        pattern="Reliable base",
        gdps=None,
        rpo_seconds=86400.0,      # [ASSUME] uzak kopya yok: gunluk saha disi yedek
        description="Tek mainframe + icindeki ICF ile sysplex. Tek site; saha "
                    "olayinda hizmet olay suresince durur.",
        storage_copies=1, sync_replication=False,   # tek DS8900F
    ),
    Topology(
        code="M2",
        name="Multi-frame failover (peer sysplex)",
        n_frames=2,
        pattern="Failover capable",
        gdps=None,
        rpo_seconds=0.0,          # Metro Mirror senkron
        description="Birincil CPC + metro mesafede DR CPC (CBU), Metro Mirror; "
                    "gecis otomasyonsuz, elle (saatler).",
        storage_copies=2, sync_replication=True,    # Metro Mirror cifti (HyperSwap)
    ),
    Topology(
        code="M3",
        name="Fault-tolerant + GDPS Metro/Global",
        n_frames=2,
        pattern="Fault tolerant",
        gdps="metro_global",
        rpo_seconds=0.0,          # [GDPS-2026] tek site kaybinda Metro Mirror: RPO 0
                                  # (bolgesel felakette Global Mirror bacagi 2-5 sn)
        description="Birincil CPC + DR CPC (CBU) + GDPS Metro Global otomasyonu "
                    "ve HyperSwap. RTO dakikalar - <1 saat.",
        storage_copies=4, sync_replication=True,    # H1+H2 (Metro) + H3+J3 (Global Mirror) [GDPS]
    ),
    Topology(
        code="M4",
        name="GDPS Continuous Availability (geo-redundant)",
        n_frames=2,
        pattern="Adaptive continuity",
        gdps="ca",
        rpo_seconds=5.0,          # [GDPS-2026] GDPS CA: RPO 0-5 sn
        description="Iki cografi site, GDPS Continuous Availability. Plansiz ve "
                    "planli gecis saniyeler (20-60 sn).",
        storage_copies=4, sync_replication=True,    # her sitede Metro Mirror cifti [GDPS]
    ),
]


def find_feasible_topologies(availability_target, rpo_seconds=None, rto_minutes=None):
    """
    Hedef uptime'i ve (verilmisse) RPO / RTO hedeflerini karsilayan topolojiler.
    Feasibility: gecerli senaryo (varsayilan mid) availability'si hedefi
    karsilamali; topolojinin
    saha felaketindeki tutucu RPO / RTO degeri hedefi asmamali.
    """
    feasible = []
    for topo in TOPOLOGIES:
        if topo.availability() < availability_target:
            continue
        if rpo_seconds is not None and topo.rpo_seconds > rpo_seconds:
            continue
        if rto_minutes is not None and topo.rto_minutes > rto_minutes:
            continue
        feasible.append(topo)
    return feasible


# ------------------------------------------------------------------------------
# DR KAPASITESI (CBU) VE GDPS
# ------------------------------------------------------------------------------
# [CBU] SC28-7025: CBU kaydi kurulu ama kapali PU'lari yalnizca LICCC ile acar;
# donanim onceden kurulu olmalidir. Kayit 1-5 yillik, yil basina bir 10 gunluk
# ucretsiz test, tek bir 90 gunluk gercek aktivasyon. "Software charges for the
# designated CBU machine are based on its permanent configuration": DR
# makinesinin yazilim faturasi kalici kapasitesine gore kesilir. CBU fiyati
# yayimlanmaz -> DR frame bedeli tam frame'in orani olarak bir aralik.
DR_FRAME_COST_FRACTION = 0.50   # [ASSUME] aralik 0.30-1.00 (1.00 = CBU'suz tam ayna)

# [GDPS] GDPS, lisansli otomasyon kodu + IBM hizmetlerinden olusan bir tekliftir;
# fiyati MSU'ya degil, otomatiklestirdigi sistem/sysplex/site kapsamina baglidir
# ve yayimlanmaz. Bu yuzden kapasiteden bagimsiz sabit aylik kalem. Orta degerler
# onceki surumdeki yazilim priminin (M3 x1.15, M4 x1.30) 10K TPS referans
# noktasindaki karsiligina esitlendi; seviye GDPS_COST_LEVEL ile taranir.
GDPS_MONTHLY_BASE = {"metro_global": 50000.0, "ca": 100000.0}   # USD/ay [ASSUME]
GDPS_COST_LEVEL = 1.0           # [ASSUME] aralik 0.5-2.0


def gdps_monthly_cost(topology):
    """Topolojinin GDPS teklifinin aylik bedeli (kapasiteden bagimsiz)."""
    return GDPS_MONTHLY_BASE.get(topology.gdps, 0.0) * GDPS_COST_LEVEL

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
AWLC_LEVELS_SOURCED = [                # (kademe ust siniri MSU, marjinal USD/MSU/ay)
    (3,     0.0),                      # Base (sabit ucrete dahil)
    (45,    208.0),                    # L0  [IBM-2004]
    (175,   88.0),                     # L1  [IBM-2004]
    (315,   66.0),                     # L2  [IBM-2004]
    (575,   50.0),                     # L3  [IBM-2004]
]
AWLC_UPPER_BOUNDS = [875, 1315, 1975, float("inf")]   # L4..L7 sinirlari [AWLC]
AWLC_UPPER_DECAY = 0.80                # L4+ kademe basina marjinal fiyat carpani
                                       # [ASSUME, LONGPELA; aralik 0.70-1.00]


def awlc_levels():
    """Tam kademe listesi: kaynakli L0-L3 + L4..L7 icin AWLC_UPPER_DECAY ile
    geometrik dusus (L4 = L3 x decay, ...)."""
    levels = list(AWLC_LEVELS_SOURCED)
    rate = levels[-1][1]
    for upper in AWLC_UPPER_BOUNDS:
        rate *= AWLC_UPPER_DECAY
        levels.append((upper, rate))
    return levels
# IBM ornek faturasi (aylik, sub-capacity): urun -> (USD/ay, faturalanan MSU)
SW_PRODUCT_ANCHORS = {
    "z/OS":    (75459.0, 265),         # [IBM-2004]
    "CICS TS": (32978.0, 210),         # [IBM-2004] CICS ayri LPAR'da 210 MSU
    "Db2":     (31876.0, 265),         # [IBM-2004]
}
SW_PRICE_LEVEL_FACTOR = 1.0            # 2004 nominal = 1.0 [ASSUME, aralik 0.5-1.5]

# [PRICE] Donanim: liste fiyati yayimlanmaz; kaynak araligi ~$0.5M (giris) -
# $10M+ (buyuk yapilandirma). Model: frame basina sabit taban (cerceve, CPC
# drawer, bellek, I/O, HMC) + kapasiteyle dogrusal artis.
#   satin_alma = HW_FRAME_BASE_COST + PCI x HARDWARE_COST_PER_MIPS (+ zIIP)
# Taban, kaynak araliginin giris ucuna esitlendi; egim aralikla taranir.
# Not: 200 CP'lik 7K0 icin ~$44M verir; buyuk uc icin egim muhtemelen yuksektir
# (mainframe aleyhine), bu yuzden low ucu $150/PCI.
HW_FRAME_BASE_COST = 500000.0          # USD/frame [PRICE -> ASSUME, aralik 250K-1M]
HARDWARE_COST_PER_MIPS = 200.0         # USD/PCI (satin alma)  [PRICE -> ASSUME, aralik 150-300]
HARDWARE_AMORTIZATION_YEARS = 5        # [ASSUME] amortisman suresi
MAINTENANCE_RATE_ANNUAL = 0.125        # donanim degerinin %12.5'i/yil [PRICE]
HW_WARRANTY_YEARS = 1                  # [ASSUME] ilk yil garanti; storage ile ayni kural
                                       # (bakim 5 yila ortalanir: x (5-1)/5)


def maintenance_factor():
    """Garanti sonrasi bakimin amortisman suresine ortalanmis payi."""
    y = HARDWARE_AMORTIZATION_YEARS
    return max(0.0, y - HW_WARRANTY_YEARS) / y

# [PWR] Enerji: ~20-40 kW/frame. Orta deger + elektrik fiyati.
POWER_KW_PER_SYSTEM = 30.0             # kW/frame  [PWR, orta deger]
ELECTRICITY_USD_PER_KWH = 0.12         # [ASSUME] tipik ticari elektrik
HOURS_PER_MONTH = 730.0



# ------------------------------------------------------------------------------
# PERSONEL (altyapi ekibi: z/OS ve CICS sistem programcilari, Db2 sistem DBA'lari,
# storage, otomasyon/operasyon, kapasite/performans, guvenlik/RACF)
# ------------------------------------------------------------------------------
# Personel kurulu kapasiteyle ALT-DOGRUSAL olceklenir: kucuk kurulumlarda sabit
# bir cekirdek ekip baskin, buyuk kurulumlarda MIPS/FTE artar [GARTNER-ITKMD].
# Model: FTE = max(TABAN, FTE_1000 x (PCI/1000)^b) x topoloji carpani.
# Capalar (Bolum 7.7):
#   - IBM Eagle TCO ekibi, 17 musteri: "5 FTE + her 625 MIPS icin 1 FTE"
#     (kucuk/orta kurulumlar, ~3.000 MIPS'e kadar) [IBM-EAGLE].
#   - Gartner IT Key Metrics 2016: kurulu MIPS/FTE 152 -> 268 (5 yil, ortalama)
#     [GARTNER-ITKMD]; yillik ~%12 verimlilik artisi.
#   - IBM ornek karsilastirmasi: 3.192 MIPS'i ~4 FTE yonetiyor (~790 MIPS/FTE)
#     [IBM-TPF-2007]; uretici kaynagi, alt sinira yakin.
# Uc senaryo (dusuk / orta / yuksek), 20.000 PCI'da MIPS/FTE: ~830 / ~450 / ~260.
STAFF_SCENARIOS = {
    #            FTE_1000, b,    taban, yuklu maliyet USD/yil
    "low":  dict(fte_1000=4.0, exp=0.60, floor=3.0, loaded=122000.0),
    "mid":  dict(fte_1000=5.5, exp=0.70, floor=4.0, loaded=162000.0),
    "high": dict(fte_1000=7.0, exp=0.80, floor=5.0, loaded=215000.0),
}
# Yuklu maliyet = brut maas x yan hak carpani. Brut maas: BLS OEWS Mayis 2025
# medyanlari (DBA/mimar $126.760, sistem yoneticisi $99.130, guvenlik $129.180)
# ve mainframe ilanlari/anketleri (Payscale ~$90K, Glassdoor Db2 z/OS DBA
# $104-163K) -> karma brut $95K / $120K / $150K. Yan hak carpani: IDC %28
# [IDC-2016], BLS ECEC'te maas toplam maliyetin %70'i -> x1.43 [BLS-ECEC];
# 1.28 / 1.35 / 1.43.
STAFF_SCENARIO = "mid"
# DR ve sysplex karmasikligi: ikinci CEC, GDPS, ikinci site operasyonu [ASSUME]
STAFF_TOPOLOGY_FACTOR = {"M1": 1.00, "M2": 1.05, "M3": 1.15, "M4": 1.25}


def staff_fte(tier, topology=None, scenario=None):
    """Kademeyi (birincil CEC kapasitesi) isletmek icin gereken altyapi FTE'si."""
    p = STAFF_SCENARIOS[scenario or STAFF_SCENARIO]
    fte = max(p["floor"], p["fte_1000"] * (tier.pci / 1000.0) ** p["exp"])
    if topology is not None:
        fte *= STAFF_TOPOLOGY_FACTOR.get(topology.code, 1.0)
    return fte


def staff_monthly_cost(tier, topology=None, scenario=None):
    """Altyapi personelinin AYLIK yuklu maliyeti (USD)."""
    p = STAFF_SCENARIOS[scenario or STAFF_SCENARIO]
    return staff_fte(tier, topology, scenario) * p["loaded"] / 12.0


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
        "io_service_time_s": io_service_time_seconds(topology, workload),
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
    levels = awlc_levels()
    lower = levels[0][0]                # ilk 3 MSU sabit ucrete dahil
    for upper, rate in levels[1:]:
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
      - software:     software_monthly_cost(billed_msu)
                      (AWLC kademeli z/OS + CICS TS + Db2)
                      billed_msu verilmezse kademenin tam kurulu MSU'su
                      (full-capacity fiyatlama) kullanilir. Sub-capacity
                      fiyatlamada billed_msu = aylik R4HA tepesinde tuketilen
                      MSU'dur (bkz. consumed_msu).
                      DR (CBU) frame'inin yazilimi kalici kapasitesine gore
                      faturalanir; bu modelde ihmal edilir [CBU].
      - hardware:     tam fiyat x cost_multiplier (1 + DR frame x DR_FRAME_COST_FRACTION)
      - maintenance:  hardware'a oranli, garanti yili sonrasi
      - energy:       frame sayisi x kW x elektrik
      - gdps:         GDPS teklifinin sabit aylik bedeli (M3, M4)
      - staff:        altyapi personeli, birincil kademenin PCI'sina gore
                      alt-dogrusal (STAFF_SCENARIOS), topoloji carpaniyla
    """
    msu = tier.msu if billed_msu is None else billed_msu
    # Yazilim lisansi: AWLC kademeli  [AWLC, IBM-2004]
    software = software_monthly_cost(msu)
    # Donanim amortismani: frame tabani + kapasite + zIIP  [PRICE/ASSUME]
    hw_purchase = (HW_FRAME_BASE_COST + tier.mips * HARDWARE_COST_PER_MIPS
                   + ziip_hw_purchase(tier, workload))
    hw_monthly = hw_purchase / (HARDWARE_AMORTIZATION_YEARS * 12)
    # Bakim: garanti sonrasi, amortisman suresine ortalanmis  [PRICE]
    maint_monthly = hw_purchase * MAINTENANCE_RATE_ANNUAL * maintenance_factor() / 12
    # Enerji - her frame ayri  [PWR]
    energy = POWER_KW_PER_SYSTEM * ELECTRICITY_USD_PER_KWH * HOURS_PER_MONTH

    mult = topology.cost_multiplier
    staff = staff_monthly_cost(tier, topology)
    gdps = gdps_monthly_cost(topology)
    return {
        "software": software,
        "hardware_amort": hw_monthly * mult,        # birincil + DR (CBU) frame
        "maintenance": maint_monthly * mult,
        "energy": energy * topology.n_frames,       # DR frame de acik
        "gdps": gdps,                               # sabit, kapasiteden bagimsiz
        "staff": staff,                             # birincil CEC kapasitesine gore
        "total": (software + (hw_monthly + maint_monthly) * mult
                  + energy * topology.n_frames + gdps + staff),
    }


def solve(tps, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=None, latency_percentile=99, verbose=True,
          data_tb=None, data_growth=None, rpo_seconds=None, rto_minutes=None):
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
      rpo_seconds, rto_minutes: Saha felaketinde kabul edilen en fazla veri kaybi
                          ve kurtarma suresi (None = kisit yok)

    Akis:
      1. Availability / RPO / RTO hedeflerini karsilayan topolojileri filtrele
      2. Latency hedefini de hesaba katarak her kademe icin max utilization hesapla
      3. Her topoloji icin: kapasiteyi karsilayan kademeleri aday yap
      4. Tum topoloji+kademe kombinasyonlari arasinda EN UCUZ olani sec
    """
    if not tps > 0:
        raise ValueError("tps pozitif olmali")
    if not 0.0 < availability < 1.0:
        raise ValueError("availability 0 ile 1 arasinda olmali")
    # Latency parametrelerini saniyeye ve fraction'a cevir
    latency_target_s = (latency_ms / 1000.0) if latency_ms is not None else None
    percentile_frac = latency_percentile / 100.0

    # 1. Feasible topolojiler (olay tabanli availability >= hedef, RPO/RTO)
    feasible_topos = find_feasible_topologies(availability, rpo_seconds, rto_minutes)

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
        if rpo_seconds is not None or rto_minutes is not None:
            print(f"         RPO hedefi: {rpo_seconds if rpo_seconds is not None else '-'} s | "
                  f"RTO hedefi: {rto_minutes if rto_minutes is not None else '-'} dk")
        print(f"  -> Feasible topolojiler (olay tabanli availability + RPO/RTO):")
        for t in feasible_topos:
            a_worst, a_best = t.availability_range()
            print(f"       {t.code}: availability {t.availability():.5%} "
                  f"(aralik {a_worst:.5%} - {a_best:.5%}) | "
                  f"RPO {t.rpo_seconds:g} s, RTO {t.rto_minutes:g} dk")

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
        a_worst, a_best = topo.availability_range()
        print(f"     availability: {topo.availability():.5%} "
              f"({topo.annual_downtime_hours():.2f} saat/yil kesinti; "
              f"aralik {a_worst:.5%} - {a_best:.5%})")
        print(f"  -> SECILEN KADEME: {tier} (birincil frame)")
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
              f"(z/OS + CICS TS + Db2, AWLC kademeli)")
        dr = (f" + {topo.n_frames - 1} DR frame (CBU, x{DR_FRAME_COST_FRACTION:.2f})"
              if topo.n_frames > 1 else "")
        print(f"       donanim:  ${cost['hardware_amort']:,.0f}  "
              f"(1 frame{dr}; {ziip_engines(tier, workload)} zIIP, "
              f"f={ziip_fraction(workload):.2f})")
        if cost["gdps"]:
            print(f"       GDPS:     ${cost['gdps']:,.0f}  ({topo.gdps})")
        print(f"       bakim:    ${cost['maintenance']:,.0f}")
        print(f"       personel: ${cost['staff']:,.0f}  "
              f"({staff_fte(tier, topo):.1f} FTE, senaryo={STAFF_SCENARIO})")
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


def generate_hourly_profile(preset_name=None, yearly_avg_tps=10000,
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
    if peak_avg_ratio < 1.0:
        raise ValueError("peak_avg_ratio >= 1 olmali")
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

    base = [daily[h % 24] * weekly[(h // 24) % 7] for h in range(HOURS)]
    is_peak = [(h // 24) in peak_day_set for h in range(HOURS)]

    def shaped(alpha, mult):
        """alpha: gunluk/haftalik dalgalanmanin genligi (1 = tam desen);
        mult: peak gunlerin carpani."""
        mean_b = sum(base) / HOURS
        return [(mean_b + alpha * (b - mean_b)) * (mult if pk else 1.0)
                for b, pk in zip(base, is_peak)]

    def ratio_of(prof):
        return max(prof) / (sum(prof) / HOURS)

    # Profilin tepe/ortalama orani istenen degere esitlenir:
    #  1) tam desenle, peak gun carpani m kapali formdan: tepe = max(b) x m,
    #     ortalama = (S_normal + m x S_peak) / 8760  ->  m = r S_n / (8760 max(b) - r S_p)
    #  2) istenen oran desenin kendi oranindan dusukse (orn. steady 1.5x),
    #     peak gun etkisiz kalir ve dalgalanma genligi alpha ile kucultulur.
    b_max = max(b for b, pk in zip(base, is_peak))
    s_peak = sum(b for b, pk in zip(base, is_peak) if pk)
    s_norm = sum(base) - s_peak
    denom = HOURS * b_max - peak_avg_ratio * s_peak
    mult = peak_avg_ratio * s_norm / denom if (peak_day_set and denom > 0) else 0.0
    if mult >= 1.0:
        profile = shaped(1.0, mult)
    else:
        # genlik ust siniri: profil negatife dusmemeli
        mean_b = sum(base) / HOURS
        a_max = mean_b / (mean_b - min(base))
        if ratio_of(shaped(a_max, 1.0)) < peak_avg_ratio:
            raise ValueError("bu peak_avg_ratio peak gunler olmadan elde edilemez; "
                             "peak_days > 0 verin")
        lo, hi = 0.0, a_max
        for _ in range(60):
            mid = (lo + hi) / 2
            if ratio_of(shaped(mid, 1.0)) < peak_avg_ratio:
                lo = mid
            else:
                hi = mid
        profile = shaped((lo + hi) / 2, 1.0)

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
            HARDWARE_COST_PER_MIPS * MAINTENANCE_RATE_ANNUAL * maintenance_factor() / 12)


def consumed_pci(load_tps, workload=DEFAULT_WORKLOAD):
    """Bir yukun tukettigi GENEL AMACLI (GP) kapasite, PCI cinsinden
    (%100 utilization esdegeri). zIIP'e kayan pay dusulur."""
    w = get_workload(workload)
    return load_tps * w.cpu_weight() * (1.0 - ziip_fraction(w)) / TPS_PER_PCI


def simulate_yearly(profile, tier, topology, workload=DEFAULT_WORKLOAD,
                    latency_ms=None, latency_percentile=99,
                    strategy="permanent", corridor_tier=None,
                    feature_max_cps=None, sw_price_per_msu_hour=None,
                    storage_monthly=0.0, staff_monthly=0.0):
    """Bir yillik saat-saat simulasyon ve maliyet.

    strategy:
      "permanent"   : yalnizca `tier` (satin alinan) kapasite.
      "base_cod"    : `tier` + gerektiginde On/Off CoD (gun bazinda).
      "tfp"         : `tier` + her zaman acik `corridor_tier` + gerekirse CoD.
                      Yazilim, sw_price_per_msu_hour x tuketilen MSU-saat.

    Her gun icin, gunun tepe yukunu tasiyan en kucuk izinli gecici kademe
    aktive edilir (CoD 24 saatlik periyotla faturalanir [COD]). Yuk
    izinli en buyuk gecici kademeyi de asarsa None doner (strateji infeasible).

    Gecici kapasite ucretleri birincil frame icin hesaplanir: coklu-frame
    topolojilerde DR frame'i yalnizca failover icindir ve felaketteki
    kapasitesi CBU kaydidir (DR_FRAME_COST_FRACTION).
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
                          base_cost["energy"] + base_cost["gdps"])
    # zIIP motorlari, yilin en buyuk aktif kademesindeki (CoD / corridor) GP
    # kapasitesine eslik edecek sayida kalici kurulur: zIIP payi f, gecici GP
    # kapasitesinde de ayni oranda zIIP ister. Ek motorlarin bedeli donanima.
    top_tier = max(set(day_tier) | {always_on}, key=lambda t: t.pci)
    ziip_extra = max(0.0, ziip_hw_purchase(top_tier, workload) - ziip_hw_purchase(tier, workload))
    base_other_monthly += (ziip_extra / (HARDWARE_AMORTIZATION_YEARS * 12)
                           + ziip_extra * MAINTENANCE_RATE_ANNUAL * maintenance_factor() / 12
                           ) * topology.cost_multiplier
    monthly_other = [base_other_monthly] * 12

    # --- On/Off CoD: gun basina, aktif gecici kapasite (always-on'un ustu) ----
    hw_pci_day = hw_monthly_cost_per_pci() / (HOURS_PER_MONTH / 24.0)
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
            monthly_software.append(mh * (sw_price_per_msu_hour or 0.0))
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
    yearly_staff = 12.0 * staff_monthly
    yearly_total = (yearly_software + yearly_other + yearly_storage + yearly_staff +
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
        "yearly_staff": yearly_staff,
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
    base_sw = reference_sim["yearly_software"]
    return base_sw / msu_hours * (1.0 - TFP_SW_DISCOUNT)


def solve_yearly(preset_name=None, yearly_avg_tps=10000,
                 peak_avg_ratio=None, peak_days=None,
                 availability=0.999, workload=DEFAULT_WORKLOAD,
                 latency_ms=None, latency_percentile=99,
                 strategies=("permanent", "base_cod", "tfp"),
                 verbose=True, data_tb=None, data_growth=None,
                 rpo_seconds=None, rto_minutes=None):
    """Yillik simulasyon + strateji karsilastirmasi. En ucuz strateji, diger
    stratejilerin en iyi sonuclari 'alternatives' listesinde doner."""
    if not yearly_avg_tps > 0:
        raise ValueError("avg_tps pozitif olmali")
    profile = generate_hourly_profile(preset_name=preset_name,
                                      yearly_avg_tps=yearly_avg_tps,
                                      peak_avg_ratio=peak_avg_ratio,
                                      peak_days=peak_days)
    peak_load = max(profile)
    avg_load = sum(profile) / len(profile)

    feasible_topos = find_feasible_topologies(availability, rpo_seconds, rto_minutes)
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
        # personel tepe yuku tasiyan kademeye gore: stratejiden bagimsiz
        stf_m = staff_monthly_cost(perm_tier, topo)
        sim_perm = simulate_yearly(profile, perm_tier, topo, workload, latency_ms,
                                   latency_percentile, strategy="permanent",
                                   storage_monthly=st_m, staff_monthly=stf_m)
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
                                    storage_monthly=st_m, staff_monthly=stf_m)
                if s is not None:
                    candidates.setdefault("base_cod", []).append(s)
            if "tfp" in strategies:
                corr = corridor_tier_for(base)
                if corr is not None:
                    s = simulate_yearly(profile, base, topo, workload, latency_ms,
                                        latency_percentile, strategy="tfp",
                                        corridor_tier=corr,
                                        sw_price_per_msu_hour=sw_price,
                                        storage_monthly=st_m, staff_monthly=stf_m)
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
    if sim.get("yearly_staff"):
        print(f"  Personel ({STAFF_SCENARIO}):".ljust(34) + f"${sim['yearly_staff']:>13,.0f}")
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


# ------------------------------------------------------------------------------
# ARALIK (RANGE) CIKTISI
# ------------------------------------------------------------------------------
# Kamuya acik kesin fiyat olmayan parametreler tek bir deger yerine kaynakli bir
# araliktir. "low" mainframe lehine (dusuk maliyet), "high" aleyhine ucu verir.
#   - solve_range: tum parametreler ayni anda low / mid / high -> toplam
#     maliyetin dis sinirlari (koseler; olasilik araligi DEGIL).
#   - range_tornado: digerleri mid'de iken her parametreyi tek tek low/high'a
#     cekip toplamdaki salinimi olcer -> hangi varsayim sonucu en cok oynatir.
# Her kademe secimi senaryo icinde yeniden optimize edilir.
RANGE_PARAMETERS = [
    # (degisken, low, mid, high, aciklama)
    ("STAFF_SCENARIO", "low", "mid", "high", "Personel FTE egrisi + yuklu maliyet"),
    ("SW_PRICE_LEVEL_FACTOR", 0.5, 1.0, 1.75, "AWLC mutlak fiyat seviyesi (2004 = 1.0)"),
    ("AWLC_UPPER_DECAY", 0.70, 0.80, 1.00, "AWLC L4+ kademe dusus orani"),
    ("CPU_US_PER_SQL_READ", 15.0, 30.0, 60.0, "Okuma SQL CPU, us (is yuku agirligi)"),
    ("CPU_US_PER_SQL_WRITE", 40.0, 70.0, 140.0, "Yazma SQL CPU, us (is yuku agirligi)"),
    ("ZIIP_OFFLOAD_FRACTION", 0.25, 0.10, 0.0, "zIIP'e kayan CPU payi"),
    ("HARDWARE_COST_PER_MIPS", 150.0, 200.0, 300.0, "Donanim USD/PCI"),
    ("HW_FRAME_BASE_COST", 250000.0, 500000.0, 1000000.0, "Donanim frame tabani, USD"),
    ("STORAGE_DISCOUNT", 0.85, 0.70, 0.50, "DS8900F liste fiyati indirimi"),
    ("BP_HIT_RATIO", 0.99, 0.95, 0.90, "Db2 buffer pool isabeti (I/O)"),
    ("DR_FRAME_COST_FRACTION", 0.30, 0.50, 1.00, "DR frame bedeli (CBU; 1 = tam ayna)"),
    ("GDPS_COST_LEVEL", 0.5, 1.0, 2.0, "GDPS sabit bedel seviyesi"),
    ("SITE_EVENT_LEVEL", "low", "mid", "high", "Saha olayi sikligi ve suresi"),
    ("RECOVERY_LEVEL", "low", "mid", "high", "Kurtarma suresi (RTO)"),
    ("PLANNED_LEVEL", "low", "mid", "high", "Planli kesinti sikligi ve suresi"),
]
RANGE_LEVELS = ("low", "mid", "high")


class use_values:
    """Modul degiskenlerini gecici olarak degistiren baglam yoneticisi."""
    def __init__(self, values):
        self.values, self.old = values, {}

    def __enter__(self):
        g = globals()
        missing = [k for k in self.values if k not in g]
        if missing:
            raise KeyError(f"bilinmeyen model parametresi: {missing}")
        for k, v in self.values.items():
            self.old[k] = g[k]
            g[k] = v
        return self

    def __exit__(self, *exc):
        globals().update(self.old)
        return False


def scenario_values(level):
    """RANGE_PARAMETERS'in tumu icin low / mid / high degerleri."""
    i = RANGE_LEVELS.index(level)
    return {name: vals[i] for name, *vals, _desc in
            [(r[0], r[1], r[2], r[3], r[4]) for r in RANGE_PARAMETERS]}


def solve_range(tps, availability=0.999, workload=DEFAULT_WORKLOAD,
                latency_ms=None, latency_percentile=99, data_tb=None, data_growth=None,
                rpo_seconds=None, rto_minutes=None):
    """Toplam aylik maliyetin low / mid / high dis sinirlari. Donus:
    {level: {"tier", "topology", "cost"}} ya da senaryo infeasible ise None."""
    out = {}
    for level in RANGE_LEVELS:
        with use_values(scenario_values(level)):
            r = solve(tps, availability, workload, latency_ms, latency_percentile,
                      verbose=False, data_tb=data_tb, data_growth=data_growth,
                          rpo_seconds=rpo_seconds, rto_minutes=rto_minutes)
        out[level] = None if r is None else {"tier": r[0], "topology": r[1], "cost": r[2]}
    return out


def range_tornado(tps, availability=0.999, workload=DEFAULT_WORKLOAD,
                  latency_ms=None, latency_percentile=99, data_tb=None, data_growth=None,
                  rpo_seconds=None, rto_minutes=None):
    """Tek-parametre salinimi: [(degisken, aciklama, low_toplam, high_toplam)],
    salinim buyuklugune gore sirali. Digerleri mid'de."""
    mid = scenario_values("mid")
    rows = []
    for name, lo, _m, hi, desc in RANGE_PARAMETERS:
        totals = []
        for v in (lo, hi):
            vals = dict(mid)
            vals[name] = v
            with use_values(vals):
                r = solve(tps, availability, workload, latency_ms, latency_percentile,
                          verbose=False, data_tb=data_tb, data_growth=data_growth,
                          rpo_seconds=rpo_seconds, rto_minutes=rto_minutes)
            totals.append(None if r is None else r[2]["total"])
        rows.append((name, desc, totals[0], totals[1]))
    rows.sort(key=lambda r: -abs((r[3] or 0) - (r[2] or 0)))
    return rows


def print_range(tps, **kw):
    rng = solve_range(tps, **kw)
    print(f"\nARALIK (aylik toplam, {tps:,.0f} TPS):")
    for level in RANGE_LEVELS:
        x = rng[level]
        if x is None:
            print(f"  {level:<5} infeasible")
            continue
        c = x["cost"]
        print(f"  {level:<5} ${c['total']:>12,.0f}  (${c['total'] / tps:,.2f}/TPS)  "
              f"{x['topology'].code} {x['tier'].model}  yazilim ${c['software']:,.0f}  "
              f"personel ${c['staff']:,.0f}")
    print("  Tek-parametre salinimi (digerleri mid):")
    for name, desc, lo, hi in range_tornado(tps, **kw):
        if lo is None or hi is None:
            print(f"    {desc:<42} infeasible ucu var")
            continue
        print(f"    {desc:<42} ${lo:>12,.0f} .. ${hi:>12,.0f}")


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
    solve(tps=10000, availability=0.999, workload=DEFAULT_WORKLOAD)
    print("[B] Ayni yuk, p99 < 200 ms latency hedefi:")
    solve(tps=10000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=200, latency_percentile=99)
    print("[C] Ayni yuk, sikilastirilmis p99 < 10 ms:")
    solve(tps=10000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=10, latency_percentile=99)
    print("[D] Yuksek yuk + yuksek uptime + p99 < 500 ms:")
    solve(tps=100000, availability=0.99999, workload=DEFAULT_WORKLOAD,
          latency_ms=500, latency_percentile=99)
    print("[E] Agir islemler (oltp_heavy) + p99 < 200 ms:")
    solve(tps=10000, availability=0.999, workload="oltp_heavy",
          latency_ms=200, latency_percentile=99)
    print("[F] Cok dusuk yuk:")
    solve(tps=2000, availability=0.999, workload=DEFAULT_WORKLOAD,
          latency_ms=200, latency_percentile=99)
    print("[G] Felaket kurtarma hedefi: RPO <= 5 s, RTO <= 60 dk:")
    solve(tps=10000, availability=0.999, workload=DEFAULT_WORKLOAD,
          rpo_seconds=5, rto_minutes=60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mainframe (IBM z16) minimum-cost feasibility modeli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  Statik (tek nokta):
    python mainframe_model.py --tps 10000
    python mainframe_model.py --tps 10000 --availability 0.99999 --latency-ms 200 --range
    python mainframe_model.py --tps 10000 --rpo-seconds 0 --rto-minutes 60
    python mainframe_model.py --tps 10000 --sql-reads 6 --sql-writes 2

  Yillik simulasyon (workload profile + CoD karsilastirmasi):
    python mainframe_model.py --yearly --preset retail_bursty --avg-tps 10000
    python mainframe_model.py --yearly --preset steady_oltp --avg-tps 10000 --availability 0.99999
    python mainframe_model.py --yearly --avg-tps 8000 --peak-ratio 3 --peak-days 25 --csv out

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
    parser.add_argument("--avg-tps", type=float, default=10000,
                        help="(YILLIK) Yillik ortalama TPS (varsayilan: 10000)")
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
    parser.add_argument("--range", action="store_true",
                        help="(STATIK) Kaynakli araliklarla low/mid/high toplam ve "
                             "tek-parametre salinimi")
    parser.add_argument("--sql-reads", type=float, default=None,
                        help="Ozel profil: islem basina okuma SQL sayisi")
    parser.add_argument("--sql-writes", type=float, default=None,
                        help="Ozel profil: islem basina yazma SQL sayisi")
    parser.add_argument("--rpo-seconds", type=float, default=None,
                        help="Saha felaketinde kabul edilen en fazla veri kaybi, saniye")
    parser.add_argument("--rto-minutes", type=float, default=None,
                        help="Saha felaketinde kabul edilen en fazla kurtarma suresi, dakika")
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
    if args.tps is not None and args.tps <= 0:
        parser.error("--tps pozitif olmali")
    if args.avg_tps <= 0:
        parser.error("--avg-tps pozitif olmali")
    if not 0.0 < args.availability < 1.0:
        parser.error("--availability 0 ile 1 arasinda olmali (orn. 0.999)")

    if args.sql_reads is not None or args.sql_writes is not None:
        r, w = args.sql_reads or 0.0, args.sql_writes or 0.0
        if r < 0 or w < 0:
            parser.error("--sql-reads ve --sql-writes negatif olamaz")
        args.workload = WorkloadProfile("custom", r, w, 1, (r + w) > 0,
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
            rpo_seconds=args.rpo_seconds,
            rto_minutes=args.rto_minutes,
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
                   data_growth=args.data_growth,
                   rpo_seconds=args.rpo_seconds,
                   rto_minutes=args.rto_minutes)
    if args.range:
        print_range(args.tps, availability=args.availability, workload=args.workload,
                    latency_ms=args.latency_ms, latency_percentile=args.latency_percentile,
                    data_tb=args.data_tb, data_growth=args.data_growth,
                    rpo_seconds=args.rpo_seconds, rto_minutes=args.rto_minutes)
    if result is None:
        print("Feasible konfigurasyon yok (yukaridaki SONUC satirina bakin).")
        sys.exit(1)
