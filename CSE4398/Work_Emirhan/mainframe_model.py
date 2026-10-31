"""
================================================================================
MAINFRAME (VERTICAL / SCALE-UP) MODEL
================================================================================
Bu modul, verilen bir is yuku + SLA girdisi icin, onu saglayan minimum maliyetli
IBM z16 konfigurasyonunu bulur.

Akis:
  1. CP-guc koprusu (z13 benchmark + LSPR oranlari) ile her z16 kademesinin
     verilen RNI altinda saglayabilecegi max TPS hesaplanir
  2. Latency hedefi varsa M/M/1 kuyruk formulunden DINAMIK utilization tavani
     hesaplanir (her kademe icin ayri); yoksa sabit %90 tavan kullanilir
  3. availability hedefini karsilayan TOPOLOJILER filtrelenir
     (single-frame / multi-frame / GDPS Metro / GDPS CA)
     ITIC bagimsiz alt sinirina karsi kontrol; planned outage indirimi (%90)
     uygulanmis halı kullanilir
  4. her feasible topoloji icin gereken TPS'i karsilayan kademeler aday olur
  5. tum (kademe x topoloji) kombinasyonlarindan en ucuzu secilir

KOPRU MANTIGI: MIPS bazli koprü yerine CP-guc koprüsü kullanildi.
  z13 18 CP gercek TPS -> z13 CP basina TPS -> (LSPR ile guc orani) -> z16 CP TPS

LATENCY MODELI: M/M/1 kuyruk teorisi (Secenek A - dinamik tavan):
  Verilen (latency_target, percentile) icin her kademe icin max_utilization
  hesaplanir:  rho_max = 1 - (E[X] / latency_target) * ln(1/(1-p))
  E[X] = ortalama servis suresi (kademe-ozgu); kademe daha hizliysa daha
  yuksek utilization'i destekler. Bu, %90 sabit tavan basitlestirmesini eler.
  Kuyruk modeli SADECE CPU bekleme + servis suresini kapsar; network/disk
  gibi diger latency kaynaklari ihmal edilir (mainframe'de kucuk).

AVAILABILITY MODELI: IBM Z Resiliency 4-model cercevesi (SG24-8446):
  M1 = Single-frame sysplex (ICF)         - 1 frame, hw 5-6 nine, total 4-5 nine
  M2 = Multi-frame failover               - 2 frame, hw 7-8 nine, total 6-7 nine
  M3 = Fault-tolerant + GDPS Metro/Global - 2 frame, hw 8-9 nine, total 7-8 nine
  M4 = GDPS Continuous Availability       - 2 site,  hw 7-8 nine, total = hw
       (M4 planned outage'i da maskeler, planned indirimi uygulanmaz)

KAYNAK ETIKETLERI:
  [LSPR]     = IBM Z LSPR ITR tablosu, ibm.com/support/pages/node/6953823 (resmi)
  [EPS]      = Chapman, "Exploring z/OS WLM CPU Measurements", EPStrategies +
               IBM ResourceLink (3931-604 capasi: 5511 PCI = 675 MSU)
  [REDP]     = IBM Redpaper REDP-5320 "CICS TS V5.3 Benchmark on IBM z13"
               (18 CP -> 174000 TPS ; 26 CP -> 227000 TPS)
  [REDBOOK]  = IBM Resiliency Redbook SG24-8446, Table 1-4 + Section 2
               (availability tasarim hedefleri, 4-model cercevesi)
  [ITIC]     = ITIC Global Server Reliability Surveys 2020-2024
               (bagimsiz endustri olcumu, gercek musteri raporlari)
  [PRECISELY]= Precisely HA Definition: total downtime'in %90'i planned
               (planned outage indirim kurali)
  [QUEUE]    = M/M/1 kuyruk teorisi - WLM/RMF response time percentile
               metodolojisiyle uyumlu; IBM bunu SMF 72.3 / SMF 110.1 ile olcer
  [CFCC]     = Coupling Facility / ICF aciklamalari (Raften, IBM)
               ICF specialty engine, yazilim lisansini etkilemez
  [PRICE]    = Mainframe fiyat rehberleri
               (donanim ~$0.5M-10M+; bakim %10-15/yil)
  [LIC]      = MSU lisanslama: ~$25-55 / MSU / ay
  [PWR]      = Enerji: 20-40 kW/frame
  [ASSUME]   = Kalibre edilmemis varsayim
================================================================================
"""

# ------------------------------------------------------------------------------
# BOLUM 1 — KAPASITE KOPRUSU SABITLERI
# ------------------------------------------------------------------------------

# [EPS] Resmi IBM cevrim capasi: 3931-604 modeli
#   LSPR orani (Average RNI) = 9.85  [LSPR]
#   mutlak kapasite          = 5511 PCI (= IBM "MIPS")  [EPS]
#   => 1 LSPR birimi kac MIPS eder:
LSPR_TO_MIPS = 5511.0 / 9.85          # ~559.5 MIPS / LSPR birimi   [EPS + LSPR]

# [EPS] MSU <-> MIPS orani (ayni 3931-604 capasindan):
#   675 MSU karsilik 5511 PCI
MSU_PER_MIPS = 675.0 / 5511.0         # ~0.1225 MSU / MIPS          [EPS]

# ------------------------------------------------------------------------------
# BOLUM 2 — z16 KAPASITE KADEMELERI (LSPR tablosundan)
# ------------------------------------------------------------------------------
# [LSPR] IBM z16 A01 (3931), System z9 2094-701 = 1.00 bazli, Average RNI sutunu.
# Tam tabloda 128 kademe var (4xx/5xx/6xx/7xx serileri x 32 CP).
# Burada temsil icin her seriden bir alt-kume aldim; tum tablo eklenebilir.
# Format: (model_kodu, CP_sayisi, LSPR_orani)
Z16_TIERS_RAW = [
    # --- 4xx serisi (en dusuk alt-kapasite, 701'in ~%12'si tek CP) [LSPR]
    ("3931-401", 1, 0.50), ("3931-404", 4, 1.85), ("3931-408", 8, 3.50),
    ("3931-412", 12, 5.00), ("3931-418", 18, 7.00), ("3931-426", 26, 9.55),
    ("3931-432", 32, 11.44),
    # --- 5xx serisi (~%41) [LSPR]
    ("3931-501", 1, 1.67), ("3931-504", 4, 6.15), ("3931-508", 8, 11.60),
    ("3931-512", 12, 16.53), ("3931-518", 18, 23.06), ("3931-526", 26, 31.31),
    ("3931-532", 32, 37.38),
    # --- 6xx serisi (~%66) [LSPR]
    ("3931-601", 1, 2.67), ("3931-604", 4, 9.85), ("3931-608", 8, 18.52),
    ("3931-612", 12, 26.27), ("3931-618", 18, 36.44), ("3931-626", 26, 49.30),
    ("3931-632", 32, 58.89),
    # --- 7xx serisi (tam hiz, %100) [LSPR]
    ("3931-701", 1, 4.02), ("3931-704", 4, 14.71), ("3931-708", 8, 27.65),
    ("3931-712", 12, 39.13), ("3931-718", 18, 54.06), ("3931-726", 26, 72.88),
    ("3931-732", 32, 86.89),
]


class Tier:
    """Bir z16 kapasite kademesi."""
    def __init__(self, model, cps, lspr):
        self.model = model
        self.cps = cps
        self.lspr = lspr                       # [LSPR] kapasite orani
        self.mips = lspr * LSPR_TO_MIPS        # mutlak MIPS  [EPS kopru]
        self.msu = self.mips * MSU_PER_MIPS    # yazilim fiyatlama birimi [EPS]

    def __repr__(self):
        return (f"{self.model} ({self.cps} CP, "
                f"{self.mips:,.0f} MIPS, {self.msu:,.0f} MSU)")


Z16_TIERS = sorted([Tier(m, c, l) for (m, c, l) in Z16_TIERS_RAW],
                   key=lambda t: t.mips)


# ------------------------------------------------------------------------------
# BOLUM 3 — CP-GUC KOPRUSU: z13 BENCHMARK -> z16 CP BASINA TPS
# ------------------------------------------------------------------------------
# Yontem: z13'un gercek olculmus TPS'inden CP basina TPS'i bul, sonra z16/z13
# CP guc oranini (LSPR'den) uygulayarak z16 CP basina TPS'i turet.
#
# Neden MIPS koprusu yerine bu? Cunku MIPS nesiller arasi tam normalize degil.
# z16 Telum islemcisi mimari olarak z13'ten farkli (cache, pipeline, bellek
# hiyerarsisi). LSPR ayni baz sisteme gore iki nesli olcuyor, bu yuzden CP-CP
# karsilastirmasi MIPS varsayimindan daha dogrudan.
#
# [REDP] z13 benchmark capalari:
_Z13_18CP_TPS = 174000.0    # [REDP] 2964-718 (18 CP, tam hiz LPAR)
_Z13_26CP_TPS = 227000.0    # [REDP] 2964-726 (26 CP, tam hiz LPAR)

# [LSPR] Karsilik gelen z13 ve z16 7xx kademelerinin LSPR oranlari:
# Benchmark 18 CP'de yapildi -> 18-CP karsilastirmasi:
_Z13_718_LSPR = 38.55       # [LSPR] 2964-718
_Z16_718_LSPR = 54.06       # [LSPR] 3931-718
# Ayni sekilde 26 CP icin:
_Z13_726_LSPR = 51.89       # [LSPR] 2964-726
_Z16_726_LSPR = 72.88       # [LSPR] 3931-726

# CP guc orani: ayni CP sayisinda z16 z13'ten kac kat guclu.
# Bu oran, ayni "mantiksal CP sayisi" konfigurasyonunda z16'nin z13'e gore
# kapasite katsayisi. Sublinearite zaten her iki nesilde benzer sekilde devrede
# oldugu icin oran 18 ve 26 CP icin yakin cikiyor.
_CP_POWER_RATIO_18 = _Z16_718_LSPR / _Z13_718_LSPR   # ~1.402
_CP_POWER_RATIO_26 = _Z16_726_LSPR / _Z13_726_LSPR   # ~1.405

# z13'te CP basina gercek TPS (benchmark'tan, sublinearite dahil):
_Z13_TPS_PER_CP_18 = _Z13_18CP_TPS / 18.0
_Z13_TPS_PER_CP_26 = _Z13_26CP_TPS / 26.0

# z16'da CP basina TPS = z13 CP TPS x guc orani (ayni CP sayisinda):
_Z16_TPS_PER_CP_18 = _Z13_TPS_PER_CP_18 * _CP_POWER_RATIO_18
_Z16_TPS_PER_CP_26 = _Z13_TPS_PER_CP_26 * _CP_POWER_RATIO_26

# Iki nokta arasi sublinearite z16'da: 18 CP daha verimli, 26 CP daha az verimli.
# Ortalamayi "baz" katsayi olarak aliyoruz (average RNI, full-speed 7xx CP):
BASE_TPS_PER_CP = (_Z16_TPS_PER_CP_18 + _Z16_TPS_PER_CP_26) / 2.0   # [REDP+LSPR]

# UYARI: bu katsayi tam-hiz (7xx) CP icin. Alt-kapasite kademelerinde (4xx/5xx/
# 6xx) CP'nin etkin gucu daha dusuk; bu zaten Tier nesnesinin LSPR oraninda
# ic.eriliyor (3931-501'in 1 CP'si, 3931-701'in 1 CP'sinden farkli LSPR'ye
# sahip). Asagidaki cp_equivalents() bu farki LSPR oraniyla normalize ediyor.

def cp_equivalents(tier):
    """
    Bir kademenin 'tam-hiz 7xx CP esdegerini' verir. Yani alt-kapasite CP'leri
    daha az "etkin CP" sayilir, cunku LSPR oranlarinda zaten az kapasite gozukur.
    Ornek: 3931-501 (1 CP, LSPR=1.67) ile 3931-701 (1 CP, LSPR=4.02) -> 501
    aslinda ~0.42 tam-hiz CP esdegerinde.
    """
    # 1 tam-hiz 7xx CP'nin LSPR'si ~4.02 [LSPR 3931-701]
    LSPR_PER_FULL_CP = 4.02
    return tier.lspr / LSPR_PER_FULL_CP

# [ASSUME] RNI (islem karmasikligi) carpanlari, BASE_TPS_PER_CP'ye uygulanir.
# average=1.0 benchmark noktasi. low/high carpanlari kalibre edilebilir.
RNI_MULTIPLIER = {
    "low":     1.25,   # hafif islem -> daha fazla TPS/CP   [ASSUME]
    "average": 1.00,   # REDP benchmark noktasi             [REDP baz]
    "high":    0.70,   # agir islem -> daha az TPS/CP       [ASSUME]
}
# NOT: MIPS-bazli modelde RNI carpani gereken MIPS'i artiriyordu; CP-bazli
# modelde mantik tersine doner -> RNI carpani CP basina TPS kapasitesini
# ETKILIYOR. low: ayni CP daha cok islem yapar (>1), high: daha az (<1).

# ------------------------------------------------------------------------------
# BOLUM 4 — LATENCY MODELI (M/M/1 kuyrugu, dinamik utilization tavani)
# ------------------------------------------------------------------------------
# Latency hedefi -> dinamik utilization tavani.
# Kuyruk teorisinin klasik M/M/1 sonucu, percentile yanit suresi icin:
#   R(p) = E[X] * (1 / (1 - rho)) * ln(1 / (1 - p))
# Burada:
#   E[X] = ortalama servis suresi = 1 / max_tps_at_full_utilization
#   rho  = utilization (= TPS / max_tps_raw)
#   p    = istenen percentile (orn. 0.99 = p99)
#
# Modelin sertligini koruyan basitlestirmeler:
#   - M/M/1 yaklasimi (tek-sira) -> tutucu bir UST SINIR verir;
#     gercek mainframe c paralel CP'siyle daha iyi davranir (M/M/c daha gevsek).
#   - Sadece CPU kuyrugundan kaynaklanan bekleme + servis modellenir;
#     network/disk I/O gibi diger latency kaynaklari mainframe'de kucuk
#     oldugu icin ihmal edilir (clustered tarafta eklencektir).
#
# Sectigimiz yaklasim (Secenek A):
#   Verilen (TPS, latency_target, percentile) icin, her kademenin
#   destekleyebilecegi MAX_UTILIZATION'i ayri ayri turetiriz.
#   M/M/1 formulundan rho icin cozdugumuzde:
#       rho_max = 1 - (E[X] / latency_target) * ln(1/(1-p))
#   Bu degerin 0-1 arasinda olmasi gerekir; <=0 cikarsa kademe yetersiz.

import math

# Fallback (latency parametresi verilmediginde kullanilan global tavan):
DEFAULT_UTILIZATION_CEILING = 0.90  # [ASSUME, pratik dayanak]

# Hard upper bound: latency hedefi cok gevsek olsa bile, mainframe
# capacity planning pratiginde %95 utilization uzerinde calistirmak
# operasyonel olarak risklidir (bursts, mikro arizalar). [ASSUME]
HARD_UTILIZATION_CAP = 0.95


def avg_service_time_seconds(tier, rni="average"):
    """
    Ortalama servis suresi E[X] = 1 / max_tps_raw  (saniye).
    max_tps_raw = utilization tavansiz ham kapasite.
    """
    cp_equiv = cp_equivalents(tier)
    raw_tps = cp_equiv * BASE_TPS_PER_CP * RNI_MULTIPLIER[rni]
    if raw_tps <= 0:
        return float('inf')
    return 1.0 / raw_tps


def max_utilization_for_latency(tier, rni, latency_target_seconds, percentile):
    """
    M/M/1 percentile latency formulunden rho'yu cozer.
    Verilen latency hedefini saglayan maksimum utilization'i dondurur.
    Donen deger 0-1 arasi (HARD_UTILIZATION_CAP ile sinirli).
    """
    if latency_target_seconds is None:
        # Latency hedefi verilmediyse default tavan
        return DEFAULT_UTILIZATION_CEILING

    ex = avg_service_time_seconds(tier, rni)
    if ex >= latency_target_seconds:
        # Servis suresi bile hedeften buyukse, hicbir utilization saglamaz
        return 0.0

    # rho_max = 1 - (E[X] / R) * ln(1/(1-p))
    ln_term = math.log(1.0 / (1.0 - percentile))
    rho_max = 1.0 - (ex / latency_target_seconds) * ln_term

    # 0 ile HARD_UTILIZATION_CAP arasinda sinirla
    rho_max = max(0.0, min(rho_max, HARD_UTILIZATION_CAP))
    return rho_max


def expected_latency_at(tier, rni, tps, percentile):
    """
    Verilen TPS yukunde, M/M/1 percentile yanit suresini hesaplar (saniye).
    Bilgi amacli; feasibility yerine raporlama/debug icin.
    """
    ex = avg_service_time_seconds(tier, rni)
    cp_equiv = cp_equivalents(tier)
    raw_tps = cp_equiv * BASE_TPS_PER_CP * RNI_MULTIPLIER[rni]
    if raw_tps <= 0:
        return float('inf')
    rho = tps / raw_tps
    if rho >= 1.0:
        return float('inf')
    ln_term = math.log(1.0 / (1.0 - percentile))
    return ex * (1.0 / (1.0 - rho)) * ln_term

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
                 description=""):
        self.code = code                # 'M1', 'M2', 'M3', 'M4'
        self.name = name
        self.n_frames = n_frames        # ana frame sayisi (donanim carpani)
        self.hw_low = hw_low            # ITIC bagimsiz alt sinir (HW-only)
        self.hw_high = hw_high          # Redbook tasarim hedefi (HW-only)
        self.masks_planned = masks_planned  # planned outage'i da maskeler mi?
        self.cost_multiplier = cost_multiplier  # frame sayisi + ek donanim
        self.software_premium = software_premium  # GDPS gibi ek yazilim
        self.description = description

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
                    "Tek hardware riski; planli kesintide rolling IPL faydasi."
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
                    "sync/async remote copy. Bir frame coker, digeri devralir."
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
                    "RTO <1 saat. Planlanmamis outage'a otomatik tepki."
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
                    "Hem planned hem unplanned outage maskelenir. RTO 1-2 dakika."
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
# [LIC] Yazilim lisansi: ~$25-55 / MSU / ay. Orta deger aliyoruz.
SOFTWARE_COST_PER_MSU_MONTH = 40.0     # USD/MSU/ay  [LIC, orta deger]

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


# ==============================================================================
# MODEL FONKSIYONLARI
# ==============================================================================

def tier_max_tps(tier, rni="average", latency_target_seconds=None, percentile=0.99):
    """
    Bir kademenin verilen RNI ve latency hedefi altinda saglayabilecegi
    MAKSIMUM TPS (dinamik utilization tavani uygulanmis).

    Latency hedefi None ise sabit DEFAULT_UTILIZATION_CEILING kullanilir.
    Latency hedefi varsa, M/M/1 formulunden o kademenin destekleyebilecegi
    max utilization hesaplanir; gercek tavan budur.
    """
    cp_equiv = cp_equivalents(tier)
    raw_tps = cp_equiv * BASE_TPS_PER_CP * RNI_MULTIPLIER[rni]
    rho_max = max_utilization_for_latency(tier, rni, latency_target_seconds, percentile)
    return raw_tps * rho_max


def is_capacity_feasible(tier, tps_required, rni="average",
                          latency_target_seconds=None, percentile=0.99):
    """Asama 3: kademe, latency hedefi altinda gereken TPS'i karsilar mi?"""
    return tier_max_tps(tier, rni, latency_target_seconds, percentile) >= tps_required


def monthly_cost(tier, topology):
    """Asama 5: bir kademenin topology'ye gore toplam AYLIK maliyeti.

    Maliyet hesaplama mantigi:
      - software:     tier.msu x USD/MSU x software_premium (GDPS gibi)
                      ICF specialty engine oldugundan ek frame'ler software
                      premium'a girmez; sadece GDPS yazilimi premium ekler.
      - hardware:     tam fiyat x cost_multiplier (frame sayisi)
      - maintenance:  hardware'a oranli
      - energy:       frame sayisi x kW x elektrik
    """
    # Yazilim lisansi - GDPS premium dahil  [LIC + ASSUME premium]
    software = tier.msu * SOFTWARE_COST_PER_MSU_MONTH * topology.software_premium
    # Donanim amortismani - frame carpani  [PRICE/ASSUME]
    hw_purchase = tier.mips * HARDWARE_COST_PER_MIPS
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


def solve(tps, availability=0.999, rni="average",
          latency_ms=None, latency_percentile=99, verbose=True):
    """
    Verilen girdi icin minimum maliyetli feasible (z16 kademesi + topoloji)
    kombinasyonunu bulur.

    Parametreler:
      tps                 : Hedef throughput (saniyedeki islem)
      availability        : Hedef uptime (0-1 arasi)
      rni                 : Islem karmasikligi: 'low' / 'average' / 'high'
      latency_ms          : Hedef latency milisaniye olarak (None ise %90 sabit tavan)
      latency_percentile  : Hedef percentile (orn. 99 -> p99 latency hedefi)

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
        print(f"  Girdi: {tps:,.0f} TPS | RNI={rni} | uptime hedefi={availability:.6%}")
        if latency_target_s is not None:
            print(f"         latency hedefi: p{latency_percentile} < {latency_ms:g} ms "
                  f"(M/M/1 kuyruk modeli)")
        else:
            print(f"         latency hedefi: yok -> default %{DEFAULT_UTILIZATION_CEILING*100:.0f} "
                  f"utilization tavani")
        print(f"  -> CP koprusu: z16 tam-hiz CP basina ~{BASE_TPS_PER_CP:,.0f} TPS "
              f"(average RNI) [REDP+LSPR]")
        print(f"     RNI carpani: x{RNI_MULTIPLIER[rni]}")
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
        for tier in Z16_TIERS:
            if is_capacity_feasible(tier, tps, rni, latency_target_s, percentile_frac):
                cost = monthly_cost(tier, topo)
                rho_max = max_utilization_for_latency(tier, rni,
                                                      latency_target_s, percentile_frac)
                max_t = tier_max_tps(tier, rni, latency_target_s, percentile_frac)
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
        max_tps = tier_max_tps(tier, rni, latency_target_s, percentile_frac)
        cp_eq = cp_equivalents(tier)
        # Gercek latency tahmini bilgi olarak goster
        if latency_target_s is not None:
            actual_lat_s = expected_latency_at(tier, rni, tps, percentile_frac)
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
              f"(premium x{topo.software_premium})")
        print(f"       donanim:  ${cost['hardware_amort']:,.0f}  "
              f"({topo.n_frames} frame)")
        print(f"       bakim:    ${cost['maintenance']:,.0f}")
        print(f"       enerji:   ${cost['energy']:,.0f}\n")
    return best


# ==============================================================================
# YILLIK SIMULASYON — WORKLOAD PROFILE + R4HA + ON/OFF COD
# ==============================================================================
# Bu bolum, statik tek-nokta sorgusunu yillik bir saat-saat simulasyona evrir.
#
# Akis:
#   1. generate_hourly_profile() ile 8760 saatlik TPS vektoru uretilir
#   2. R4HA: aylik kayan 4-saatlik en yuksek ortalama (MLC faturalandirma birimi)
#   3. Iki strateji karsilastirilir:
#      A) Permanent: peak yuku karsilayan kademe surekli acik
#      B) Base+CoD: kucuk base + peak gunlerde On/Off CoD ile gecici upgrade
#   4. En ucuz strateji secilir, grafik-hazir cikti dondurulur
#
# KAYNAKLAR (mevcut etiketlere ek):
#   [COD]   = IBM SC28-7025 "IBM Z and LinuxONE Capacity on Demand User's Guide"
#             On/Off CoD: gun-bazli faturalandirma, 24-saatlik aktivasyon periyodu
#   [R4HA]  = IBM MLC sub-capacity: aylik en yuksek 4-saatlik kayan ortalama
# ==============================================================================

COD_DAILY_MULTIPLIER = 2.5   # [ASSUME] On/Off CoD daily / permanent daily

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


def simulate_yearly(profile, tier, topology, rni="average",
                     latency_ms=None, latency_percentile=99,
                     cod_peak_tier=None):
    """Bir yillik simulasyon: saatlik kapasite/utilization + maliyet."""
    latency_target_s = (latency_ms / 1000.0) if latency_ms is not None else None
    pct = latency_percentile / 100.0

    base_max_tps = tier_max_tps(tier, rni, latency_target_s, pct)
    if cod_peak_tier is not None:
        peak_max_tps = tier_max_tps(cod_peak_tier, rni, latency_target_s, pct)
        peak_cost = monthly_cost(cod_peak_tier, topology)
    else:
        peak_max_tps = base_max_tps
        peak_cost = None

    HOURS = len(profile)
    cap_tps = [0.0] * HOURS
    util = [0.0] * HOURS
    cod_active = [False] * HOURS

    for i in range(HOURS):
        load = profile[i]
        if load <= base_max_tps or cod_peak_tier is None:
            cap_tps[i] = base_max_tps
            cod_active[i] = False
        else:
            cap_tps[i] = peak_max_tps
            cod_active[i] = True
        util[i] = (load / cap_tps[i]) if cap_tps[i] > 0 else 0.0

    cod_days = sum(1 for d in range(365)
                   if any(cod_active[d*24 + h] for h in range(24)))

    r4ha_peaks = monthly_r4ha_peaks(profile)

    base_cost = monthly_cost(tier, topology)
    base_software_monthly = base_cost["software"]
    base_other_monthly = (base_cost["hardware_amort"] +
                          base_cost["maintenance"] +
                          base_cost["energy"])

    monthly_software = []
    monthly_other = []
    for m in range(12):
        month_has_cod = any(cod_active[m*730 + i]
                            for i in range(min(730, HOURS - m*730)))
        if month_has_cod and cod_peak_tier is not None:
            # R4HA tepesi base'i asiyorsa, software faturasi orantili artar
            ratio = r4ha_peaks[m] / base_max_tps if base_max_tps > 0 else 1.0
            if ratio > 1.0 and peak_max_tps > base_max_tps:
                peak_ratio = peak_max_tps / base_max_tps
                alpha = min(max((ratio - 1.0) / (peak_ratio - 1.0), 0.0), 1.0)
                msoft = base_software_monthly + alpha * (
                    peak_cost["software"] - base_software_monthly)
            else:
                msoft = base_software_monthly
        else:
            msoft = base_software_monthly
        monthly_software.append(msoft)
        monthly_other.append(base_other_monthly)

    yearly_software = sum(monthly_software)
    yearly_other = sum(monthly_other)

    if cod_peak_tier is not None and cod_days > 0:
        peak_daily = (peak_cost["hardware_amort"] +
                      peak_cost["maintenance"] +
                      peak_cost["energy"]) / 30.0
        base_daily = base_other_monthly / 30.0
        cod_daily_charge = (peak_daily - base_daily) * COD_DAILY_MULTIPLIER
        cod_cost_total = cod_days * cod_daily_charge
    else:
        cod_cost_total = 0.0

    yearly_total = yearly_software + yearly_other + cod_cost_total

    return {
        "hourly_load": profile,
        "hourly_capacity_tps": cap_tps,
        "hourly_utilization": util,
        "hourly_cod_active": cod_active,
        "monthly_r4ha_peaks": r4ha_peaks,
        "monthly_cost_software": monthly_software,
        "monthly_cost_other": monthly_other,
        "cod_days": cod_days,
        "cod_cost_total": cod_cost_total,
        "yearly_software": yearly_software,
        "yearly_other": yearly_other,
        "yearly_total": yearly_total,
        "base_tier": tier,
        "peak_tier": cod_peak_tier,
        "topology": topology,
    }


def solve_yearly(preset_name=None, yearly_avg_tps=50000,
                  peak_avg_ratio=None, peak_days=None,
                  availability=0.999, rni="average",
                  latency_ms=None, latency_percentile=99,
                  verbose=True):
    """Yillik simulasyon + iki strateji karsilastirmasi."""
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
        print(f"  Availability hedefi: {availability:.6%}  |  RNI: {rni}")
        if latency_ms is not None:
            print(f"  Latency hedefi: p{latency_percentile} < {latency_ms:g} ms")
        print()

    best_overall = None
    alt_overall = None

    for topo in feasible_topos:
        # Strateji A: peak'i karsilayan permanent kademe
        perm_tier = None
        for tier in Z16_TIERS:
            if is_capacity_feasible(tier, peak_load, rni,
                                     latency_target_s, pct):
                perm_tier = tier
                break
        if perm_tier is None:
            continue

        sim_perm = simulate_yearly(profile, perm_tier, topo, rni,
                                    latency_ms, latency_percentile,
                                    cod_peak_tier=None)
        sim_perm["strategy"] = "permanent"
        sim_perm["strategy_label"] = "Strateji A: Permanent peak kademe"

        # Strateji B: base + CoD
        best_base_sim = None
        for base_tier in Z16_TIERS:
            if base_tier.mips >= perm_tier.mips:
                continue
            if not is_capacity_feasible(base_tier, avg_load * 1.2, rni,
                                         latency_target_s, pct):
                continue
            sim_b = simulate_yearly(profile, base_tier, topo, rni,
                                     latency_ms, latency_percentile,
                                     cod_peak_tier=perm_tier)
            if best_base_sim is None or sim_b["yearly_total"] < best_base_sim["yearly_total"]:
                best_base_sim = sim_b
        if best_base_sim is not None:
            best_base_sim["strategy"] = "base_plus_cod"
            best_base_sim["strategy_label"] = "Strateji B: Base kademe + On/Off CoD"

        topo_candidates = [sim_perm]
        if best_base_sim is not None:
            topo_candidates.append(best_base_sim)
        topo_best = min(topo_candidates, key=lambda s: s["yearly_total"])

        if best_overall is None or topo_best["yearly_total"] < best_overall["yearly_total"]:
            alt_overall = best_overall
            best_overall = topo_best
            for c in topo_candidates:
                if c is not topo_best:
                    if alt_overall is None or c["yearly_total"] < alt_overall["yearly_total"]:
                        alt_overall = c

    if best_overall is None:
        if verbose:
            print("HATA: hicbir feasible kombinasyon bulunamadi")
        return None

    best_overall["alternative"] = alt_overall
    if verbose:
        _print_yearly_summary(best_overall)
    return best_overall


def _print_yearly_summary(sim):
    print("=" * 70)
    print("YILLIK SIMULASYON OZETI")
    print("=" * 70)
    print(f"Secilen strateji: {sim['strategy_label']}")
    print(f"Topoloji:         {sim['topology']}")
    print(f"Base kademe:      {sim['base_tier']}")
    if sim['peak_tier']:
        print(f"Peak (CoD) kademe: {sim['peak_tier']}")
        print(f"On/Off CoD aktif: {sim['cod_days']} gun / 365")
    else:
        print(f"On/Off CoD:       yok (permanent peak kademe)")

    util = sim["hourly_utilization"]
    avg_util = sum(util) / len(util)
    p50 = sorted(util)[len(util)//2]
    max_u = max(util)
    print(f"\nUtilization istatistikleri:")
    print(f"  ortalama: {avg_util:.1%}  |  medyan: {p50:.1%}  |  maksimum: {max_u:.1%}")

    print(f"\nYillik maliyet:")
    print(f"  Yazilim (R4HA bazli):      ${sim['yearly_software']:>14,.0f}")
    print(f"  Donanim + bakim + enerji:  ${sim['yearly_other']:>14,.0f}")
    print(f"  On/Off CoD ek maliyeti:    ${sim['cod_cost_total']:>14,.0f}")
    print(f"  {'TOPLAM:':<29} ${sim['yearly_total']:>14,.0f}")

    if sim.get("alternative"):
        alt = sim["alternative"]
        savings = alt["yearly_total"] - sim["yearly_total"]
        pct = (savings / alt["yearly_total"] * 100) if alt["yearly_total"] > 0 else 0
        print(f"\nAlternatif strateji ({alt['strategy_label']}):")
        print(f"  Yillik toplam: ${alt['yearly_total']:,.0f}")
        print(f"  Tasarruf: ${savings:,.0f} ({pct:.1f}%)")
    print()


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
#   python mainframe_model.py --tps 80000 --availability 0.9993 --rni high
#   python mainframe_model.py --demo          (5 hazir senaryo)
#   python mainframe_model.py --calibration   (kalibrasyon kontrolu)
#
# Parametreler:
#   --tps           Saniyedeki islem sayisi (zorunlu, --demo yoksa)
#   --availability  Hedef uptime, 0-1 arasi (varsayilan: 0.999 = %99.9)
#   --rni           Islem karmasikligi: low / average / high (varsayilan: average)
#   --demo          5 hazir senaryo calistir
#   --calibration   Kalibrasyon sabitlerini yazdir
# ==============================================================================

import argparse
import sys


def print_calibration():
    print("=" * 70)
    print("KALIBRASYON KONTROLU")
    print("=" * 70)
    print(f"LSPR -> MIPS katsayisi   : {LSPR_TO_MIPS:.2f} MIPS / LSPR birimi [EPS+LSPR]")
    print(f"MSU / MIPS orani         : {MSU_PER_MIPS:.4f} [EPS]")
    print()
    print("CP-GUC KOPRUSU (z13 -> z16) [REDP + LSPR]:")
    print(f"  z13 18 CP: {_Z13_18CP_TPS:,.0f} TPS -> "
          f"{_Z13_TPS_PER_CP_18:,.1f} TPS/z13-CP")
    print(f"  z16/z13 CP guc orani (718 vs 718) : {_CP_POWER_RATIO_18:.3f}")
    print(f"  -> z16 18 CP TPS/CP esdegeri      : {_Z16_TPS_PER_CP_18:,.1f}")
    print()
    print(f"  z13 26 CP: {_Z13_26CP_TPS:,.0f} TPS -> "
          f"{_Z13_TPS_PER_CP_26:,.1f} TPS/z13-CP")
    print(f"  z16/z13 CP guc orani (726 vs 726) : {_CP_POWER_RATIO_26:.3f}")
    print(f"  -> z16 26 CP TPS/CP esdegeri      : {_Z16_TPS_PER_CP_26:,.1f}")
    print()
    print(f"BASE_TPS_PER_CP (tam-hiz z16, avg RNI): {BASE_TPS_PER_CP:,.0f} TPS/CP")
    print("  (18 ve 26 CP noktalarinin ortalamasi, sublinearite-aware)")
    print()
    print("Ornek z16 kademeleri (kapasite koprusu uygulanmis):")
    for t in Z16_TIERS[:5]:
        cp_eq = cp_equivalents(t)
        max_tps = tier_max_tps(t, "average")
        print(f"   {t}  | CPeq={cp_eq:.2f} | max TPS={max_tps:,.0f}")
    print("   ...")
    t = Z16_TIERS[-1]
    cp_eq = cp_equivalents(t)
    max_tps = tier_max_tps(t, "average")
    print(f"   {t}  | CPeq={cp_eq:.2f} | max TPS={max_tps:,.0f}")


def run_demo():
    print("=" * 70)
    print("DEMO SENARYOLAR")
    print("=" * 70)
    print("\n[A] Orta yuk OLTP (latency hedefi yok, %90 sabit tavan):")
    solve(tps=50000, availability=0.999, rni="average")
    print("[B] Ayni yuk, p99 < 200 ms latency hedefi:")
    solve(tps=50000, availability=0.999, rni="average",
          latency_ms=200, latency_percentile=99)
    print("[C] Ayni yuk, sikilastirilmis p99 < 50 ms (trading-seviyesi):")
    solve(tps=50000, availability=0.999, rni="average",
          latency_ms=50, latency_percentile=99)
    print("[D] Yuksek yuk + yuksek uptime + p99 < 500 ms:")
    solve(tps=150000, availability=0.99999, rni="average",
          latency_ms=500, latency_percentile=99)
    print("[E] Agir islemler (high RNI) + p99 < 200 ms:")
    solve(tps=50000, availability=0.999, rni="high",
          latency_ms=200, latency_percentile=99)
    print("[F] Cok dusuk yuk:")
    solve(tps=2000, availability=0.999, rni="average",
          latency_ms=200, latency_percentile=99)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mainframe (IBM z16) minimum-cost feasibility modeli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  Statik (tek nokta):
    python mainframe_model.py --tps 50000
    python mainframe_model.py --tps 80000 --availability 0.9993 --rni high --latency-ms 200

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
    parser.add_argument("--rni", choices=["low", "average", "high"],
                        default="average",
                        help="Islem karmasikligi (varsayilan: average)")
    parser.add_argument("--latency-ms", type=float, default=None,
                        help="Hedef latency milisaniye (orn: 200)")
    parser.add_argument("--latency-percentile", type=int, default=99,
                        choices=[50, 90, 95, 99],
                        help="Latency percentile hedefi (varsayilan: 99)")

    # Yardimci moDlar
    parser.add_argument("--demo", action="store_true",
                        help="Hazir demo senaryolar calistir")
    parser.add_argument("--calibration", action="store_true",
                        help="Kalibrasyon sabitlerini yazdir")

    args = parser.parse_args()

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
            rni=args.rni,
            latency_ms=args.latency_ms,
            latency_percentile=args.latency_percentile,
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
                   rni=args.rni,
                   latency_ms=args.latency_ms,
                   latency_percentile=args.latency_percentile)
    if result is None:
        print("Tek z16 frame bu is yukunu karsilayamiyor.")
        sys.exit(1)
