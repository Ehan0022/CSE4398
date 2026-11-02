"""
================================================================================
ORTAK MODUL — IKI PLATFORMUN PAYLASTIGI PARAMETRELER VE KURALLAR (Adim 6)
================================================================================
Mainframe (mainframe_model.py) ve kumelenmis x86 (ileride x86_model.py) ayni
disiplinle karsilastirilabilsin diye, iki tarafta AYNI olmasi gereken her sey
burada ve yalnizca burada tanimlidir. Platform modulleri bu degerleri kendi
kopyalarina almaz; her cagrida `cm.X` olarak okur. Boylece bir aralik senaryosu
ya da kullanici fiyat dosyasi bir degeri degistirdiginde iki taraf ayni anda
etkilenir.

Icerik (docs/ortak_modul_dokumantasyonu_v1.md):
  1. Parametre sahipligi ve gecici degistirme (use_values)
  2. Saha olaylari ve elle gecis karar suresi (availability denkleminin ortak kismi)
  3. Personel ucretleri ve 7/24 taban ekip
  4. Enerji
  5. Nesne depolama ve bulut yedek fiyatlari (on-prem S3 uyumlu, AWS S3 + Direct Connect)
  6. Storage fiyatlama sozlesmesi (ham TB)
  7. Fiyat donemi (PRICE_EPOCH) ve fiyat yaslari
  8. NPV kurallari (iskonto, artis siniflari, kalan deger)
  9. Uretim disi ortamlar (NONPROD) kurali
 10. Iki fiyat modu: kaynakli fiyat seti / kullanici fiyat dosyasi

Kaynak etiketleri mainframe_model.py ile aynidir; buraya tasinan her
parametrenin kaynagi yaninda yazilidir.
================================================================================
"""

import json
import math
import sys

# ==============================================================================
# 1. PARAMETRE SAHIPLIGI VE GECICI DEGISTIRME
# ==============================================================================
# Her parametrenin tek bir sahibi (modulu) vardir. use_values, bir ad kumesini
# sahip modullerinde gecici olarak degistirir; ad birden fazla modulde
# tanimliysa (golgeleme) hata verir, cunku hangi kopyanin okunacagi belirsizdir.


def _owner(name, modules):
    owners = [mod for mod in modules if name in vars(mod)]
    if len(owners) > 1:
        raise KeyError(f"parametre birden fazla modulde tanimli (golgeleme): {name}")
    return owners[0] if owners else None


class use_values:
    """Parametreleri sahip modullerinde gecici olarak degistiren baglam yoneticisi.
    modules: aranacak moduller (platform modulu + bu modul)."""
    def __init__(self, values, modules=None):
        self.values = values
        self.modules = tuple(modules) if modules else (sys.modules[__name__],)
        self.old = []

    def __enter__(self):
        targets = {k: _owner(k, self.modules) for k in self.values}
        missing = [k for k, mod in targets.items() if mod is None]
        if missing:
            raise KeyError(f"bilinmeyen model parametresi: {missing}")
        for k, v in self.values.items():
            mod = targets[k]
            self.old.append((mod, k, getattr(mod, k)))
            setattr(mod, k, v)
        return self

    def __exit__(self, *exc):
        for mod, k, v in reversed(self.old):
            setattr(mod, k, v)
        self.old = []
        return False


RANGE_LEVELS = ("low", "mid", "high")


# ==============================================================================
# 2. SAHA OLAYLARI VE ELLE GECIS KARAR SURESI
# ==============================================================================
# Availability denkleminin ortak kismi (mainframe v3 §6.3; x86 plani §8.1):
#   D_saha(T_rec) = lam_saha x [(1-p_uzun) x min(d_kisa, T_rec) + p_uzun x min(d_uzun, T_rec)]
# lam_saha, d_kisa, d_uzun, p_uzun veri merkezi duzeyindeki hizmet kesintisini
# (guc, ag/BT, insan hatasi) olcer ve platformdan bagimsizdir: iki taraf ayni
# veri merkezinde durur [UPTIME-2025, UPTIME-2022]. T_rec platforma ve
# topolojiye ozgudur.
SITE_EVENT_SCENARIOS = {
    # rate: olay/yil; d_short_h / d_long_h: saat; p_long: uzun olay payi
    #  [UPTIME-2025] operatorlerin %53'u son 3 yilda kesinti bildirdi -> ~0,25/yil
    #  (ust uc); ciddi/agir pay %9 -> alt uc. [UPTIME-2022] kamuya yansiyan
    #  kesintilerin >24 saat suren payi %8 (2017) -> ~%30 (2021).
    "low":  {"rate": 0.05, "d_short_h": 1.0, "p_long": 0.08, "d_long_h": 24.0},
    "mid":  {"rate": 0.15, "d_short_h": 2.0, "p_long": 0.15, "d_long_h": 48.0},
    "high": {"rate": 0.25, "d_short_h": 4.0, "p_long": 0.30, "d_long_h": 72.0},
}
SITE_EVENT_LEVEL = "mid"     # aralik parametresi

# Elle (otomasyonsuz) site gecisinde kurtarma suresinin buyuk kismi teknoloji
# degil insan karari ve runbook'tur: felaketin ilani, onay zinciri, uygulamalarin
# yonlendirilmesi. Bu pay iki tarafta ayni parametredir; platforma ozgu olan
# yalnizca teknik gecis suresidir (mainframe M2: Metro Mirror'dan IPL; x86 X2:
# Data Guard / Patroni standby terfisi). Boylece M2-X2 karsilastirmasi "hangi
# ekip daha hizli karar verir" sorusuna donusmez (x86 plani §8.2).
# Ayrisim [ASSUME]: onceki M2 kurtarma suresi 60 / 120 / 240 dk =
# karar 45 / 90 / 180 + teknik 15 / 30 / 60 dk (toplam degismedi).
MANUAL_FAILOVER_DECISION_MINUTES = {"low": 45.0, "mid": 90.0, "high": 180.0}

HOURS_PER_YEAR = 8760.0
HOURS_PER_MONTH = 730.0


def site_downtime_hours(t_rec_hours, level=None):
    """Saha olaylarindan yillik beklenen hizmet kesintisi (saat). t_rec_hours:
    topolojinin alternatif siteye kurtarma suresi (alternatif site yoksa inf)."""
    s = SITE_EVENT_SCENARIOS[level or SITE_EVENT_LEVEL]
    return s["rate"] * ((1 - s["p_long"]) * min(s["d_short_h"], t_rec_hours)
                        + s["p_long"] * min(s["d_long_h"], t_rec_hours))


def manual_failover_minutes(technical_minutes, level):
    """Elle gecisin toplam suresi: ortak karar suresi + platforma ozgu teknik sure."""
    return MANUAL_FAILOVER_DECISION_MINUTES[level] + technical_minutes


# ==============================================================================
# 3. PERSONEL UCRETLERI VE TABAN EKIP
# ==============================================================================
# Yuklu yillik maliyet (brut maas x yan hak carpani), iki tarafta ayni ucret
# tablosu. Brut: BLS OEWS Mayis 2025 medyanlari (DBA/mimar $126.760, sistem
# yoneticisi $99.130, guvenlik $129.180) ve ilan/anketler -> karma brut
# $95K / $120K / $150K. Yan hak: IDC %28 [IDC-2016], BLS ECEC'te maas toplamin
# %70'i -> x1.43 [BLS-ECEC]; 1.28 / 1.35 / 1.43.
# FTE egrisi platforma ozgudur (mainframe: IBM Eagle + Gartner; x86: IBM Eagle
# dagitik saatleri); ucret seviyesi ise ortaktir ve ayri bir aralik parametresidir.
LOADED_WAGE_USD = {"low": 122000.0, "mid": 162000.0, "high": 215000.0}
WAGE_LEVEL = "mid"           # aralik parametresi

# 7/24 nobet tutabilmek icin asgari ekip; platformun personel senaryosuyla
# (low / mid / high) secilir. Ayni deger x86'da da taban olarak kullanilir
# (x86 plani §10: aksi halde kucuk x86 kurulumlari Eagle saatleriyle 1 FTE'nin
# altina duser ve yapay olarak ucuz gorunur) [ASSUME].
STAFF_FLOOR_FTE = {"low": 3.0, "mid": 4.0, "high": 5.0}


def loaded_wage(level=None):
    return LOADED_WAGE_USD[level or WAGE_LEVEL]


# ==============================================================================
# 4. ENERJI
# ==============================================================================
ELECTRICITY_USD_PER_KWH = 0.12         # [ASSUME] tipik ticari elektrik


def energy_monthly(kw):
    return kw * ELECTRICITY_USD_PER_KWH * HOURS_PER_MONTH


# ==============================================================================
# 5. NESNE DEPOLAMA VE BULUT YEDEK FIYATLARI
# ==============================================================================
# Yedek hedeflerinden ikisi platformdan bagimsizdir: kurum ici S3 uyumlu nesne
# depolama ve AWS S3 (hibrit). Mainframe'de veri DS8900F TCT ile, x86'da
# yedekleme yazilimi (pgBackRest / RMAN) ile gider; yol ve verim kisiti
# platforma ozgudur, fiyat fonksiyonu ortaktir.
COS_HW_USD_PER_TB = 100.0            # [MINIO-TCO] 60 x 16 TB HDD sistem $70K, 720 TB kullanilabilir
COS_MIN_SITE_CAPEX_USD = 70000.0     # [MINIO-TCO] site basina en kucuk sistem
COS_SW_USD_PER_TB_MONTH = 5.0        # [MINIO-TCO -> ASSUME] yazilim/destek aboneligi; acik kaynak 0,
                                     # ticari abonelik ~$10/TB-ay
COS_KW_PER_PB = 1.5                  # [ASSUME] HDD yogun 2U sistemler
S3_USD_PER_GB_MONTH = 0.0125         # [AWS-S3-2026] Standard-IA
S3_MIN_STORAGE_DAYS = 30             # [AWS-S3-2026] Standard-IA en kisa faturalanan sure
S3_RETRIEVAL_USD_PER_GB = 0.01       # [AWS-S3-2026] Standard-IA geri getirme
S3_PUT_USD_PER_1000 = 0.01           # [AWS-S3-2026] Standard-IA PUT
S3_OBJECT_MB = 256.0                 # [ASSUME] nesne boyutu (istek sayisi icin)
DX_PORT_USD_PER_HOUR = 2.25          # [AWS-DX-2026] 10 Gbps dedicated port
DX_LINK_MB_S = 1000.0                # 10 Gbps x %80 verim [ASSUME]
DX_EGRESS_USD_PER_GB = 0.02          # [AWS-DX-2026] ABD ici DX cikis; giris ucretsiz
WAN_CIRCUIT_USD_PER_MONTH = 2000.0   # [ASSUME] 10 Gbps tasiyici devre + cross-connect; aralik 1-4K


def onprem_object_store(stored_tb_per_site, sites):
    """Kurum ici nesne depolama: donanim capex'i, aylik abonelik, kW."""
    hw = sites * max(COS_MIN_SITE_CAPEX_USD, stored_tb_per_site * COS_HW_USD_PER_TB)
    service = sites * stored_tb_per_site * COS_SW_USD_PER_TB_MONTH
    kw = sites * max(1.0, stored_tb_per_site / 1000.0 * COS_KW_PER_PB)
    return {"hw_capex": hw, "service": service, "power_kw": kw}


def s3_hybrid(stored_tb, daily_tb, restore_tb, required_mb_s, retention_weeks,
              restores_per_year):
    """AWS S3 Standard-IA + Direct Connect: aylik hizmet bedeli kalemleri.
    Hat sayisi gereken verimden; S3'te tek kopya (bolge ici dayaniklilik)."""
    links = max(1, math.ceil(required_mb_s / DX_LINK_MB_S))
    min_factor = max(1.0, S3_MIN_STORAGE_DAYS / (7.0 * retention_weeks))
    storage_fee = stored_tb * 1000.0 * S3_USD_PER_GB_MONTH * min_factor
    puts = (daily_tb * 1e6 / S3_OBJECT_MB * (HOURS_PER_MONTH / 24.0)
            * S3_PUT_USD_PER_1000 / 1000.0)
    restore_fee = (restores_per_year * restore_tb * 1000.0
                   * (DX_EGRESS_USD_PER_GB + S3_RETRIEVAL_USD_PER_GB) / 12.0)
    network = links * (DX_PORT_USD_PER_HOUR * HOURS_PER_MONTH + WAN_CIRCUIT_USD_PER_MONTH)
    return {"links": links, "link_mb_s": links * DX_LINK_MB_S,
            "s3_storage": storage_fee, "s3_requests": puts, "s3_restore": restore_fee,
            "network": network, "service": storage_fee + puts + restore_fee + network}


# ==============================================================================
# 6. STORAGE FIYATLAMA SOZLESMESI
# ==============================================================================
# Platformlar arasi storage karsilastirmasinda en buyuk tuzak fiyat tanimidir:
# DS8900F fiyati HAM TB basina listelenir, x86 AFA fiyatlari cogunlukla ETKIN
# TB (veri azaltimi sonrasi) basina verilir (x86 plani §7.2). Sozlesme:
#   1) Boyutlandirma zinciri iki tarafta ayni sirayla ham TB uretir:
#      mantiksal veri -> planlama ufku -> DB ek yuku -> sikistirma/veri azaltimi
#      -> RAID/replika kullanilabilir orani -> ham TB.
#   2) Her fiyat teklifi once ham TB basina LISTE fiyatina cevrilir
#      (price_per_raw_tb), indirim yalnizca bir kez ve listeye uygulanir.
#   3) Veri azaltim orani boyutlandirmada bir kez kullanilir; fiyata ikinci kez
#      gomulmez (etkin TB fiyati geri cevrilir).
STORAGE_PRICE_BASES = ("raw", "usable", "effective")


def price_per_raw_tb(list_price, basis="raw", raid_usable=1.0, data_reduction=1.0):
    """Bir storage liste fiyatini HAM TB basina liste fiyatina cevirir.
      raw       : zaten ham TB basina
      usable    : kullanilabilir TB basina -> x raid_usable
      effective : etkin TB basina (veri azaltimi sonrasi) -> x raid_usable x data_reduction
    Ornek: $200/etkin TB, DRR 2,5, RAID kullanilabilir 0,75 -> $375/ham TB."""
    if basis not in STORAGE_PRICE_BASES:
        raise ValueError(f"bilinmeyen fiyat tabani: {basis}")
    if basis == "raw":
        return list_price
    if basis == "usable":
        return list_price * raid_usable
    return list_price * raid_usable * data_reduction


def net_price(list_price, discount):
    """Liste fiyatina indirimin (0-1) tek kez uygulanmasi."""
    return list_price * (1.0 - discount)


# ==============================================================================
# 7. FIYAT DONEMI (PRICE_EPOCH) VE FIYAT YASLARI
# ==============================================================================
# 2026'da bellek ve SSD fiyatlarinda sok yasandi (x86 plani §5.2): 64 GB RDIMM
# ~$255 (2025 ortasi) -> $2.245-3.400 (2026 Q3); kurumsal NVMe ~$115/TB ->
# ~$753/TB. Mainframe capalari sok oncesinden; x86 bilesenleri hangi donemden
# fiyatlanirsa mainframe de o donemle karsilastirilmalidir. Kural:
#   - Emtia bilesen fiyatlari (DRAM, NAND) donem tablosundan okunur; platform
#     modulu kendi sabitini tutmaz.
#   - IBM'in z16 ve DS8900F fiyatlarinin soktan etkilenip etkilenmedigine dair
#     kaynak yok; mainframe fiyatlari donemden bagimsiz tutulur ve bu bir
#     sinirlama olarak raporlanir (x86 plani §14.2).
#   - Her fiyat parametresinin kaynak yili PRICE_REGISTRY'de tutulur ve
#     price_vintage_report ile listelenir; boylece iki taraftaki fiyat yaslari
#     gorunur olur.
#   - 2004 nominal AWLC fiyatlari 2026 USD'ye otomatik cevrilmez: guncel liste
#     fiyati bilinmedigi icin donusum SW_PRICE_LEVEL_FACTOR araliginin isidir
#     (ust uc 1,75, ABD TUFE'nin 2004-2026 artisiyla ayni buyuklukte).
PRICE_EPOCHS = {
    #            DRAM USD/GB, kurumsal NVMe USD/TB  [x86 plani §5.2]
    "2025-mid": {"dram_usd_per_gb": 4.0, "nvme_usd_per_tb": 115.0},
    "2026-Q3":  {"dram_usd_per_gb": 35.0, "nvme_usd_per_tb": 753.0},
}
PRICE_EPOCH = "2026-Q3"


def component_price(name, epoch=None):
    """Emtia bilesen fiyati, secili fiyat donemine gore."""
    return PRICE_EPOCHS[epoch or PRICE_EPOCH][name]


# ==============================================================================
# 8. NPV KURALLARI
# ==============================================================================
# Iki taraf ayni ufuk, iskonto orani, buyume ve fiyat artis siniflariyla
# indirgenir (mainframe v3 §8.10). Satin almalar donem basinda (t = y-1),
# isletme giderleri yil sonunda (t = y). Kalan deger varsayilan 0 (tutucu).
# Teknoloji yenilemesi (z17 / yeni sunucu nesli) iki tarafta birlikte dışarıda.
#   [DAMODARAN-2026] = A. Damodaran, Cost of Capital by Sector (US), Ocak 2026:
#                      toplam piyasa %6,96; bilgisayar hizmetleri %7,83;
#                      yazilim %9,34; bankalar %4,98
#   [IBM-PRICE-2026] = IBM yillik fiyat uyumlamasi: yazilim 2026'da +%6;
#                      bakim 2025'te +%4-6, 2026'da ~+%6
#   [BLS-ECI-2026]   = BLS ECI, Haziran 2026: ozel sektor ucret maliyeti +%3,3
#   [EIA-EPM]        = EIA Tablo 5.3: ticari elektrik 10,59 (2020) -> 13,37
#                      cent/kWh (2025), yillik ~%4,8
NPV_YEARS = 5                    # [ASSUME] amortisman suresiyle ayni ufuk
NPV_DISCOUNT_RATE = 0.07         # [DAMODARAN-2026] nominal; tarama %5 / %7 / %10
NPV_TPS_GROWTH = 0.10            # senaryo girdisi (yillik TPS buyumesi)
SW_PRICE_ESCALATION = 0.03       # [IBM-PRICE-2026 -> ASSUME] aralik 0-0,06
HW_SERVICE_ESCALATION = 0.03     # [IBM-PRICE-2026 -> ASSUME] aralik 0-0,06
WAGE_ESCALATION = 0.033          # [BLS-ECI-2026] aralik 0,025-0,045
ENERGY_ESCALATION = 0.04         # [EIA-EPM] aralik 0,015-0,056
NPV_RESIDUAL_FRACTION = 0.0      # [ASSUME] donem sonu kalan defter degerinin geri kazanilan payi

NPV_COMMON_RANGE_PARAMETERS = [
    ("SW_PRICE_ESCALATION", 0.0, 0.03, 0.06, "Yazilim + GDPS yillik fiyat artisi"),
    ("HW_SERVICE_ESCALATION", 0.0, 0.03, 0.06, "Bakim / CoD yillik fiyat artisi"),
    ("WAGE_ESCALATION", 0.025, 0.033, 0.045, "Personel yillik ucret artisi"),
    ("ENERGY_ESCALATION", 0.015, 0.04, 0.056, "Elektrik yillik fiyat artisi"),
]


def esc(rate, year):
    """Yil y'deki bilesik fiyat carpani (yil 1 = 1,0)."""
    return (1.0 + rate) ** (year - 1)


def discount_and_sum(rows, rate, demand):
    """rows: yil basina {'capex', 'opex', 'capex_items', 'opex_items'}. capex
    t=y-1'de, opex t=y'de indirgenir. demand: yil basina TPS (seviyelendirme)."""
    npv = 0.0
    items = {}
    pv_demand = 0.0
    for y, r in enumerate(rows, start=1):
        dc = (1.0 + rate) ** (y - 1)
        do = (1.0 + rate) ** y
        r["pv"] = r["capex"] / dc + r["opex"] / do
        npv += r["pv"]
        for k in r["capex_items"]:
            items[k] = items.get(k, 0.0) + r["capex_items"][k] / dc
        for k in r["opex_items"]:
            items[k] = items.get(k, 0.0) + r["opex_items"][k] / do
        pv_demand += 12.0 * demand[y - 1] / do
    return npv, items, pv_demand


def residual_value(capex_events, rate, years, life_years):
    """Donem sonu kalan defter degeri x NPV_RESIDUAL_FRACTION (negatif akis)."""
    if NPV_RESIDUAL_FRACTION <= 0:
        return 0.0
    val = sum(c * max(0.0, 1.0 - (years - t) / life_years) for t, c in capex_events)
    return -NPV_RESIDUAL_FRACTION * val / (1.0 + rate) ** years


def finish_npv(rows, rate, years, demand, capex_events, life_years, extra):
    """NPV, EAC ve seviyelendirilmis $/TPS/ay."""
    npv, items, pv_demand = discount_and_sum(rows, rate, demand)
    res = residual_value(capex_events, rate, years, life_years)
    npv += res
    if res:
        items["residual"] = res
    annuity = rate / (1.0 - (1.0 + rate) ** -years) if rate > 0 else 1.0 / years
    out = {
        "years": rows,
        "npv": npv,
        "items": items,
        "undiscounted": sum(r["capex"] + r["opex"] for r in rows),
        "eac": npv * annuity,
        "levelized_per_tps_month": npv / pv_demand if pv_demand > 0 else None,
        "discount_rate": rate,
    }
    out.update(extra)
    return out


# ==============================================================================
# 9. URETIM DISI ORTAMLAR (NONPROD)
# ==============================================================================
# Gelistirme, test, QA ve on-uretim ortamlari. IBM Eagle'a gore mainframe'de
# uretimin ~+%20'si, dagitik sistemlerde cogu zaman +%200'u [IBM-EAGLE-2013;
# benzer_calismalar_v1 §3.2]. Emirhan'in karari (2026-11-02): iki tarafa ayri,
# aralikli bir carpan; dusuk uc 0 = "kapsam disi" senaryosu.
# Kural (iki tarafta ayni):
#   nonprod = NONPROD_FACTOR(platform) x uretim BIRINCIL sitesinin
#             {yazilim + bilgi islem donanimi (amortisman + bakim) + enerji +
#              birincil storage}
# Dahil olmayanlar: DR sitesi, site otomasyonu (GDPS / MAA), yedekleme ve
# personel. Personel kurulu uretim kapasitesine gore boyutlanir ve uretim
# disi ortamlari ayni ekip isletir [ASSUME]. Carpan "kapasite esdegeri"
# maliyettir: uretim disi kapasitenin uretimle ayni birim fiyattan alindigini
# varsayar (mainframe'de AWLC'nin kademeli marjinal fiyatini ve IBM'in
# gelistirme/test fiyatlandirma tekliflerini yok sayar; mainframe aleyhine
# tutucu).
NONPROD_COMPONENTS = ("software", "compute_hw", "compute_maint", "compute_energy",
                      "storage_primary")


def nonprod_cost(factor, components):
    """components: NONPROD_COMPONENTS anahtarlariyla uretim birincil site
    kalemleri (ayni zaman birimiyle). Eksik anahtar hata verir."""
    missing = [k for k in NONPROD_COMPONENTS if k not in components]
    if missing:
        raise KeyError(f"nonprod icin eksik kalem: {missing}")
    return factor * sum(components[k] for k in NONPROD_COMPONENTS)


# ==============================================================================
# 10. IKI FIYAT MODU
# ==============================================================================
# (a) Kaynakli fiyat seti (varsayilan): her fiyat parametresi kaynakli bir
#     degerle ya da aralikla gelir.
# (b) Kullanici fiyatlari: bir JSON dosyasi, PRICE_REGISTRY'deki adlarin
#     bir kismini ya da tamamini gecersiz kilar. Gecersiz kilinan fiyat artik
#     belirsiz sayilmaz: aralik ve tornado analizinde sabit tutulur ("pinned").
#     Duzey sozlugu olan bir parametreye (ornegin LOADED_WAGE_USD) tek sayi
#     verilirse uc duzeye de o sayi yazilir.
# Kayit: ad -> (sahip modul adi, birim, kaynak, kaynak yili, bagli aralik
#        parametresi ya da None, aciklama)
PRICE_REGISTRY = {}
PINNED = set()          # kullanici tarafindan sabitlenen aralik parametreleri
USER_PRICES = {}        # uygulanan kullanici fiyatlari (ad -> deger)


def register_prices(module_name, entries):
    """Platform modulu kendi fiyat parametrelerini kaydeder.
    entries: [(ad, birim, kaynak, yil, aralik_parametresi, aciklama), ...]"""
    for name, unit, source, year, range_param, desc in entries:
        if name in PRICE_REGISTRY and PRICE_REGISTRY[name]["module"] != module_name:
            raise KeyError(f"fiyat parametresi iki kez kayitli: {name}")
        PRICE_REGISTRY[name] = {"module": module_name, "unit": unit, "source": source,
                                "year": year, "range_param": range_param, "desc": desc}


register_prices(__name__, [
    ("LOADED_WAGE_USD", "USD/FTE-yil (low/mid/high)", "BLS-OEWS, BLS-ECEC", 2025,
     "WAGE_LEVEL", "Yuklu personel maliyeti"),
    ("ELECTRICITY_USD_PER_KWH", "USD/kWh", "ASSUME", 2026, None, "Elektrik fiyati"),
    ("COS_HW_USD_PER_TB", "USD/TB", "MINIO-TCO", 2024, "COS_HW_USD_PER_TB",
     "Kurum ici nesne depolama donanimi"),
    ("COS_MIN_SITE_CAPEX_USD", "USD/site", "MINIO-TCO", 2024, None,
     "Kurum ici nesne depolama en kucuk sistem"),
    ("COS_SW_USD_PER_TB_MONTH", "USD/TB-ay", "MINIO-TCO -> ASSUME", 2024,
     "COS_SW_USD_PER_TB_MONTH", "Kurum ici nesne depolama aboneligi"),
    ("S3_USD_PER_GB_MONTH", "USD/GB-ay", "AWS-S3-2026", 2026, None, "S3 Standard-IA saklama"),
    ("S3_RETRIEVAL_USD_PER_GB", "USD/GB", "AWS-S3-2026", 2026, None, "S3 geri getirme"),
    ("S3_PUT_USD_PER_1000", "USD/1000 istek", "AWS-S3-2026", 2026, None, "S3 PUT"),
    ("DX_PORT_USD_PER_HOUR", "USD/saat", "AWS-DX-2026", 2026, None,
     "Direct Connect 10 Gbps port"),
    ("DX_EGRESS_USD_PER_GB", "USD/GB", "AWS-DX-2026", 2026, None, "Direct Connect cikis"),
    ("WAN_CIRCUIT_USD_PER_MONTH", "USD/ay", "ASSUME", 2026, None, "10 Gbps WAN devresi"),
    ("PRICE_EPOCHS", "USD (donem tablosu)", "x86 plani §5.2", 2026, None,
     "Emtia bilesen fiyatlari (DRAM, NVMe) donem basina"),
])


def _modules_by_name(modules):
    return {mod.__name__: mod for mod in modules}


def load_price_file(path):
    """JSON fiyat dosyasini okur: {"AD": deger, ...}. '_' ile baslayan anahtarlar
    (aciklama) yok sayilir."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("fiyat dosyasi bir JSON nesnesi olmali")
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _coerce(name, current, value):
    """Kullanici degerini mevcut degerin bicimine uydurur ve dogrular."""
    if isinstance(current, dict):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not all(isinstance(v, (int, float)) for v in current.values()):
                raise ValueError(f"{name}: tek sayi bu tabloya uygulanamaz")
            return {k: float(value) for k in current}
        if not isinstance(value, dict):
            raise ValueError(f"{name}: sayi ya da nesne bekleniyor")
        unknown = [k for k in value if k not in current]
        if unknown:
            raise ValueError(f"{name}: bilinmeyen anahtar {unknown}")
        merged = dict(current)
        for k, v in value.items():
            merged[k] = _coerce(f"{name}.{k}", current[k], v)
        return merged
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: sayi bekleniyor")
    if value < 0:
        raise ValueError(f"{name}: negatif olamaz")
    return float(value)


def apply_user_prices(prices, modules):
    """Kullanici fiyatlarini kalici olarak uygular (calisma boyunca). Bilinmeyen
    ad ya da kayitli olmayan parametre hata verir. Donus: uygulanan adlar."""
    unknown = [k for k in prices if k not in PRICE_REGISTRY]
    if unknown:
        raise KeyError(f"fiyat kaydinda olmayan ad(lar): {unknown} "
                       f"(--list-prices ile gecerli adlar listelenir)")
    mods = _modules_by_name(modules)
    applied = []
    for name, value in prices.items():
        entry = PRICE_REGISTRY[name]
        mod = mods[entry["module"]]
        setattr(mod, name, _coerce(name, getattr(mod, name), value))
        USER_PRICES[name] = getattr(mod, name)
        if entry["range_param"]:
            PINNED.add(entry["range_param"])
        applied.append(name)
    return applied


def reset_user_prices(snapshot, modules):
    """Testler icin: apply_user_prices oncesindeki degerlere don."""
    mods = _modules_by_name(modules)
    for name, value in snapshot.items():
        setattr(mods[PRICE_REGISTRY[name]["module"]], name, value)
    USER_PRICES.clear()
    PINNED.clear()


def current_prices(modules):
    """Kayitli tum fiyatlarin guncel degerleri (fiyat dosyasi sablonu)."""
    mods = _modules_by_name(modules)
    return {name: getattr(mods[e["module"]], name)
            for name, e in sorted(PRICE_REGISTRY.items()) if e["module"] in mods}


def price_mode_label():
    if not USER_PRICES:
        return "kaynakli fiyat seti"
    return f"kullanici fiyatlari ({len(USER_PRICES)} parametre gecersiz kilindi)"


def unpinned(params):
    """Aralik parametre listesinden kullanicinin sabitlediklerini cikarir."""
    return [p for p in params if p[0] not in PINNED]


def price_vintage_report(modules):
    """(ad, modul, kaynak yili, kaynak) satirlari, en eskiden yeniye."""
    mods = _modules_by_name(modules)
    rows = [(n, e["module"], e["year"], e["source"]) for n, e in PRICE_REGISTRY.items()
            if e["module"] in mods]
    return sorted(rows, key=lambda r: (r[2], r[0]))
