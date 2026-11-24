# Kümelenmiş x86 (Scale-Out) Modelinin Detaylı Dokümantasyonu — v1

*On-prem kümelenmiş x86 OLTP yığını · iş yükü, sunucu kataloğu ve fiyatı, kapasite köprüsü, kullanım tavanı ve latency, yığın (vSphere / OpenShift Virtualization × VM / Kubernetes / OpenShift × PostgreSQL + Patroni / Oracle), topolojiler X1–X4 ve availability, lisanslar, uygulama katmanı, storage, yedek, personel, üretim dışı ortamlar, aralık, NPV, yıllık mod ve mainframe ile karşılaştırma*

Bu doküman `src/x86_model.py`'nin **güncel halini** anlatır: hangi veri hangi kaynaktan alındı, nasıl işlendi, modele nasıl girdi. Mainframe tarafının karşılığı `mainframe_model_documentation_v3.md`'dir. İki platformu bağlayan kurallar (köprüler) `kopruler_v1.md`'de (KB-01 – KB-18), iki platformun paylaştığı parametreler `ortak_modul_dokumantasyonu_v1.md`'de anlatılır. Araştırmanın kendisi `acik_sistem_arastirma_plani_v1.md`'de, benzer çalışmalar `benzer_calismalar_v1.md`'dedir. Değişikliklerin tarihçesi `PROJECT_LOG.md`'dedir.

Etiketler: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** kaynaktan hesaplanmış değer · **[VENDOR]** üretici kaynağı · **(doğrulanmalı)** kaynakla henüz teyit edilmemiş bilgi.

**Hesap tabanı.** Bütün sayılar güncel varsayılanlarla hesaplandı: `PRICE_EPOCH` = 2025-mid, 20 TB veri, yılda %15 veri büyümesi, 3 yıllık storage planlama ufku, oltp_rw profili, `STAFF_RATIO_X86` = 1,0, `NONPROD_FACTOR_X86` = 0,50. Mainframe sayıları F ve P kararlarının uygulandığı güncel mainframe modelinden gelir (10K TPS'te $113,93/TPS/ay).

---

## 0. Okuma Kılavuzu

### 0.1. Model bir sorguyu nasıl işler

Model mainframe modeliyle aynı soruyu sorar: verilen iş yükünü ve SLA'yı karşılayan en ucuz yapılandırma hangisi, ayda ne kadar? Mainframe'de karar değişkeni (topoloji, kademe) çiftidir. x86'da dört değişken vardır: **yığın** (hipervizör × yerleşim × veritabanı, 8 aday), **topoloji** (X1–X4), **sunucu boyutu** (katalogdan bir SKU) ve Oracle RAC'ta **düğüm sayısı** k. Statik moddaki akış:

1. **İş yükünü tanımla (Bölüm 3).** İşlem bileşimi iki tarafta aynıdır (KB-01). x86 çapası sysbench oltp_read_write'ın kendisidir. Diğer bileşimler ifade maliyetleriyle göreli ağırlığa çevrilir.
2. **Çekirdek başına verimi hesapla (Bölüm 5).** `TPS/çekirdek = 91 × SPECint/çekirdek × S(n) × (1 − sanallaştırma) × (1 − konteyner) × Oracle çarpanı` (KB-03).
3. **Topolojileri availability, RPO ve RTO'ya göre ele (Bölüm 8).** Yıllık kesinti olay tabanlıdır ve saha olayları mainframe ile ortaktır (KB-07).
4. **Kapasiteyi ve latency'yi kontrol et (Bölüm 6).** `ρ_max = min(ρ_latency, X86_UTIL_CEILING)` (U kararı). Patroni'de yükü yalnızca birincil düğüm taşır. RAC'ta N+1 kuralıyla k − 1 düğüm taşır (KB-06).
5. **Düğüm gruplarını kur (Bölüm 9–11).** Site başına veritabanı düğümleri, uygulama katmanı (KB-12), X3/X4'te üçüncü sitede tanık düğümü. Storage DB'ye bağlıdır: Patroni'de yerel NVMe × düğüm, RAC'ta site başına paylaşımlı all-flash dizi (K1). Yedek ortak fiyat fonksiyonlarıyla boyutlanır (KB-10).
6. **Maliyeti hesapla ve en ucuzu seç (Bölüm 13).** Grup başına donanım, bakım, enerji, abonelikler ve Oracle lisansı. Bunlara storage, yedek, personel (KB-13) ve üretim dışı ortamlar (KB-14) eklenir. Her (yığın, topoloji) için en ucuz feasible (SKU, k) bulunur, sonra en ucuz olan seçilir.
7. **Aralığı ver (Bölüm 14).** 36 parametre low / mid / high (low = x86 lehine) ve tornado.
8. **Karşılaştır (Bölüm 16).** Aynı girdiyle mainframe modeli de çözülür. Çıktılar: oran, personel hariç TCO, başabaş personel oranı (P kararı) ve eşleştirilmiş senaryolar.

### 0.2. Baştan sona bir örnek

Sorgu: 10.000 TPS, oltp_rw, availability ≥ %99,9, latency hedefi yok, 20 TB veri.

```
python src/x86_model.py --tps 10000 --compare
```

| Adım | Ne hesaplanır | Sonuç |
|---|---|---|
| 1. İş yükü | oltp_rw: 10 nokta + 4 aralık okuma + 4 yazma + BEGIN/COMMIT = 20 ifade | Göreli ağırlık 1,00; 2,8 senkron okuma + 1 WAL yazımı, 5,8 IOPS / işlem |
| 2. Çekirdek verimi | 91,0 × 9,81 × S(16) = 1,116 × (1 − 0,07 vSphere) | 2 × 8 çekirdekli düğümde 927 TPS/çekirdek; düğüm 14.828 TPS ham |
| 3. Availability | X1 (Patroni 3 düğüm, tek site): saha 1,34 sa + planlı 0,13 sa + 12 yama switchover'ı 0,05 sa + düğüm arızası 0,001 sa | %99,983 ≥ %99,9; RPO 24 sa, RTO 72 sa (M1 ile aynı kural) |
| 4. Kapasite | Birincil düğüm 14.828 × 0,70 = 10.380 TPS ≥ 10.000 | Kullanım %67,4; sabit gecikme 3,66 ms (ağ 3,0 + I/O 0,45 + senkron replika 0,21); p99 ≈ 18,9 ms |
| 5. Gruplar | DB 3 × 2×8c; uygulama 0,9 meşgul çekirdek → 2 × 2×8c (N+1) | 5 sunucu, 80 çekirdek; NVMe düğüm başına 11 × 3,84 TB; yedek 2 site × 101 TB nesne depolama |
| 6. Maliyet | Abonelikler $5.210 · donanım $932 · bakım $233 · enerji $189 · storage $304 · yedek $4.917 · üretim dışı $3.434 · personel $521.333 (38,6 FTE) | **Aylık $536.552 = $53,66/TPS** |
| 7. Aralık | 36 parametre | $22,01 / $53,66 / $124,91 |
| 8. Karşılaştırma | Mainframe aynı girdiyle: M1, 3931-524, $113,93/TPS | Oran 2,12; personel hariç $617.961 vs $15.219 (40,6 kat); **başabaş personel oranı 2,16** |

Okuma: x86'nın personel hariç maliyeti bu noktada mainframe'in kırkta biridir, ama toplamın %97'si personeldir. Personel iki tarafta aynı eğriyle sayıldığı için (P kararı) sonuç şu cümleye indirgenir: x86 personeli aynı iş yükü için mainframe personelinin 2,16 katından azsa x86 ucuzdur. IBM'in aynı iş yükü vakaları 1,23–3,28 arasındadır (KB-13). Bu yüzden sonuç bir nokta değil, personel oranına bağlı bir bölgedir (Bölüm 16).

### 0.3. Sözlük

| Terim | Anlamı | Modeldeki yeri |
|---|---|---|
| SKU | Katalogdaki sunucu boyutu, ör. 2×8c = 2 soket × 8 çekirdek | Bölüm 4 |
| SPECint/çekirdek | SPECrate2017_int_base / fiziksel çekirdek sayısı | Kapasite köprüsü (Bölüm 5) |
| S(n) | Düğüm içi ölçeklenme çarpanı, n = düğümün çekirdek sayısı | Bölüm 5.3 |
| Patroni | PostgreSQL için HA yöneticisi; DCS (etcd) ile tek birincil seçer | Bölüm 7, 8 |
| Standby küme | Patroni'nin ikinci sitede tuttuğu, birincil kümeden akışla beslenen ayrı küme | X2 (Bölüm 8.2) |
| RAC | Oracle Real Application Clusters; paylaşımlı disk üzerinde çok yazıcılı küme | Bölüm 5.4 |
| Data Guard / ADG | Oracle'ın standby veritabanı; Active Data Guard okunabilir standby ve Fast-Start Failover | X2, X3 |
| GoldenGate | Oracle'ın mantıksal (asenkron) replikasyonu; aktif-aktif | X4 |
| MAA | Oracle Maximum Availability Architecture; Bronze / Silver / Gold / Platinum katmanları | Topoloji eşlemesi |
| VVF | VMware vSphere Foundation (Broadcom); çekirdek başına yıllık abonelik | Bölüm 9.1 |
| OVE | Red Hat OpenShift Virtualization Engine; düğüm başına yalnızca VM çalıştırma hakkı | Bölüm 9.2 |
| OCP | Red Hat OpenShift Container Platform | Bölüm 9.2 |
| AFA | All-flash dizi (paylaşımlı SAN storage) | Bölüm 11 |
| N+1 | Bir düğüm kaybında kalan düğümlerin bütün yükü taşıması | Bölüm 5.4, 10 |
| low / mid / high | Aralık senaryoları; "low" her parametrenin x86 lehine ucu | Bölüm 14 |

---

## 1. Modelin Amacı ve Kapsamı

### 1.1. Cevaplanan soru

"Verilen OLTP iş yükünü ve SLA'yı on-prem kümelenmiş x86 ile karşılamanın en düşük toplam sahip olma maliyeti nedir ve hangi yapılandırmayla?" Aynı soru mainframe modelinde z16 A01 için sorulur. Karşılaştırmanın adil olması için iki model aynı birimleri (KB-01), aynı availability denklemini (KB-07), aynı kuyruk ailesini (KB-05), aynı storage fiyat sözleşmesini (KB-09), aynı NPV kurallarını (KB-16) ve aynı personel eğrisini (KB-13) kullanır.

### 1.2. Tasarım ilkesi: x86'nın kendi çalışma biçimine sadakat

Emirhan'ın isteği "açık sistemin kendi fundamentallarına ve çalışma şekline %100 sadık" bir modeldir. Bu, iki ilkeye çevrildi:

1. **Ortak olan ortak kurala bağlanır.** İş birimi, saha olayları, ücret, enerji fiyatı, yedek hacmi, NPV ve personel eğrisi iki tarafta aynı fonksiyondan okunur (`common_model.py`).
2. **Yapısal fark eşitlenmez, modellenir.** x86'nın mainframe'den farklı çalıştığı her yer kendi mekanizmasıyla girer:
   - Patroni tek yazıcıdır: yazma ölçeklenmez, yük birincil düğümdedir (Bölüm 5.4).
   - RAC düğüm ekleyerek ölçeklenir ve N+1 boyutlanır (Bölüm 5.4).
   - Lisans kurulu çekirdekten ya da düğümden alınır; DR düğümleri tam lisanslıdır; CoD ve CBU karşılığı yoktur (Bölüm 9).
   - Uygulama katmanı ayrı düğümlerde çalışır ve ağ gidiş-dönüşü işlemin gecikmesine girer (Bölüm 6, 10).
   - Storage DB mimarisine bağlıdır: paylaşımsız (Patroni, yerel NVMe × kopya) ya da paylaşımlı disk (RAC, SAN) (Bölüm 11).
   - Patroni'nin iki siteli standby kümesi asenkrondur; RPO sıfır değildir (Bölüm 8.2).
   - Sanallaştırma katmanı her zaman vardır (`project_context_restore_v4.md` §4.8) ve kendi ek yükünü taşır (Bölüm 7).

### 1.3. Mevcut kapsam

- Yığın: {vSphere Foundation, OpenShift Virtualization Engine} × {VM, VM içinde vanilla Kubernetes, VM içinde OpenShift} × {PostgreSQL + Patroni, Oracle Database EE}. Oracle yalnızca VM yerleşiminde. Toplam 8 yığın.
- Topolojiler X1–X4 (M1–M4 karşılıkları; X4 PostgreSQL için infeasible).
- Sunucu: Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3 sınıfı, 2 soket, 2 × 8 – 2 × 32 çekirdek (ana katalog), 2 × 48 ve 2 × 64 (ekstrapolasyon, duyarlılık).
- Maliyet kalemleri: sunucu donanımı, bakım, enerji, hipervizör / işletim sistemi / orkestrasyon abonelikleri, Oracle lisansı ve desteği, PostgreSQL ticari desteği, veri storage'ı, yedek, personel, üretim dışı ortamlar.
- Modlar: statik, aralık + tornado, 5 yıllık NPV, yıllık (tepe yüke göre kurulum), mainframe ile karşılaştırma.

### 1.4. Kapsam dışı

- Bare-metal Kubernetes (v4 §4.8: her zaman bir sanallaştırma katmanı var).
- Citus ve sharding (K3), EDB Postgres Distributed (K4), MQ (proje kararı), Windows.
- PUE, raf alanı, veri merkezi ağı ve SAN fabric'i (KB-17; iki tarafta da dışarıda).
- Kendi sysbench ölçümümüz (K6) henüz yapılmadı; köprü değeri ölçüme kadar geniş bir aralıkla taşınır (Bölüm 5.2).

---

## 2. Girdiler ve Çıktılar

### 2.1. Girdiler (CLI)

| Bayrak | Anlamı | Varsayılan |
|---|---|---|
| `--tps` | Tasarım TPS'i (statik mod) | — |
| `--availability` | Availability alt sınırı | 0,999 |
| `--workload` | `tpcb_like`, `oltp_rw`, `oltp_heavy` (redp_light SQL içermediği için yok) | oltp_rw |
| `--sql-reads`, `--sql-range-reads`, `--sql-writes` | Özel bileşim | — |
| `--latency-ms`, `--latency-percentile` | Latency hedefi | yok, p99 |
| `--data-tb`, `--data-growth` | Veri hacmi ve yıllık büyüme (ortak) | 20 TB, %15 |
| `--rpo-seconds`, `--rto-minutes` | Felaket kurtarma kısıtları | yok |
| `--db`, `--hypervisor`, `--placement` | Yığın filtresi | hepsi |
| `--price-epoch` | 2025-mid (ana) ya da 2026-Q3 (duyarlılık) | 2025-mid |
| `--allow-extrapolation` | 2 × 48 ve 2 × 64 çekirdekli düğümleri de dene | kapalı |
| `--staff-ratio` | `STAFF_RATIO_X86` (yalnızca duyarlılık) | 1,0 |
| `--range` | Aralık + tornado; `--compare` ile eşleştirilmiş karşılaştırma aralığı | kapalı |
| `--npv`, `--tps-growth`, `--discount-rate`, `--years` | 5 yıllık NPV | %10, %7, 5 |
| `--yearly`, `--preset`, `--avg-tps` | Yıllık mod (mainframe preset profilleri) | — |
| `--compare` | Mainframe ile aynı girdide karşılaştırma | kapalı |
| `--calibration` | Köprü ve fiyat kontrolleri | — |
| `--prices`, `--list-prices`, `--price-vintages` | İki fiyat modu (ortak modül §10) | kaynaklı set |

### 2.2. Çıktılar

- Seçilen yığın, topoloji, SKU ve (Oracle'da) RAC düğüm sayısı; site başına düğüm dağılımı.
- Çekirdek başına verim, yükü taşıyan ham verim, kullanım ve tavan, sabit gecikme ve percentile latency.
- Aylık maliyet dökümü (8 kalem + personel), DR payı ve uygulama katmanı payı.
- Yığın seçim motoru: her yığının en ucuz yapılandırması.
- `--compare`: mainframe ve x86 toplamları, oran, personel hariç toplamlar, 1,25 ve 2,0 personel oranlarında x86, konsolide edilmemiş park senaryosu, üretim dışı stres senaryosu, başabaş personel oranı.
- **OZET bloğu (her koşunun son satırları, 2026-11-24):** aynı girdilerle iki tarafın en ucuz feasible yapılandırması ve aylık maliyeti, `OZET | taraf | yapılandırma | aylık | $/TPS` biçiminde (`src/ozet.py`). `--compare` verilmese de mainframe tarafı çözülür; kurulamayan taraf `kurulamaz` yazılır. `--range` ve `--npv` koşularında özet mid / 1. yıl statik değerdir; yıllık modda mainframe A / B / C stratejilerinin en ucuzu, x86 tepeye göre kurulu yığındır (aylık = yıllık / 12). Sunum demosu bu satırları toplayıp her case dosyasının sonuna CASE ÖZETİ yazar.

---

## 3. İş Yükü (KB-01)

### 3.1. Bileşim iki tarafta aynı

`common_model.WORKLOAD_MIXES` iki modelin de tek kaynağıdır (F kararıyla nokta ve aralık okumaları ayrıldı):

| Profil | Nokta okuma | Aralık okuma | Yazma | Commit | Tanım |
|---|---|---|---|---|---|
| tpcb_like | 1 | 0 | 4 | 1 | pgbench / TPC-B benzeri |
| oltp_rw | 10 | 4 | 4 | 1 | sysbench oltp_read_write |
| oltp_heavy | 30 | 0 | 6 | 1 | ağır okuma bileşimi |

I/O kuralları da ortaktır: 4 getpage / okuma, tampon havuzu isabeti %95, commit başına 1 senkron log yazımı, yazma başına 0,5 asenkron yazma. oltp_rw'de 14 okuma × 4 × 0,05 = 2,8 senkron okuma, 1 senkron WAL yazımı ve 5,8 IOPS / işlem çıkar. Mainframe'de de aynı değerler kullanılır (Db2 tampon havuzu ve log). PostgreSQL'de karşılıkları `shared_buffers` + işletim sistemi önbelleği ve WAL fsync'tir.

### 3.2. Göreli ağırlık

x86 çapası sysbench oltp_read_write'ın kendisidir (Bölüm 5.1). oltp_rw'nin göreli ağırlığı tanım gereği 1'dir. Diğer profiller ifade maliyetleriyle ölçeklenir, birim nokta sorgusudur:

```
birim(profil)   = nokta + aralık × RANGE_READ_WEIGHT + yazma × X86_WRITE_POINT_RATIO + (commit + BEGIN) × X86_TXCTL_POINT_RATIO
göreli_ağırlık  = birim(profil) / birim(oltp_rw)
TPS/çekirdek(profil) = TPS/çekirdek(oltp_rw) / göreli_ağırlık
```

| Parametre | Değer | Dayanak |
|---|---|---|
| RANGE_READ_WEIGHT | 3,65 (3,4–3,9) | Ortak, F kararı [DERIVED, VONNG-PERF alt testleri] |
| X86_WRITE_POINT_RATIO | 3,9 | [DERIVED, VONNG-PERF] yazma/nokta 3,65–4,15 aralığının ortası |
| X86_TXCTL_POINT_RATIO | 1,0 | [DERIVED, VONNG-PERF] BEGIN/COMMIT ≈ bir nokta sorgusu |

Sonuç: tpcb_like 0,44, oltp_rw 1,00, oltp_heavy 1,31. Aynı bileşimin mainframe profili (`mainframe_profile()`) personel eğrisinin girdisini (KB-13) ve işlem yöneticisi payını (KB-12) verir.

**Sınırlama.** `RANGE_READ_WEIGHT` oltp_rw'nin x86 maliyetini değiştirmez, çünkü ölçülmüş çapanın içindedir. Yalnızca başka bileşimlere taşınan oranı ve personel girdisini etkiler. Oranlar tek bir kaynağın alt testlerinden türetildiği için K6 ölçümüyle yeniden kalibre edilecektir (KB-03 protokol şartı 5).

---

## 4. Sunucu Kataloğu ve Fiyatı (K2, K5; KB-15, KB-17)

### 4.1. Referans sunucu

K5 kararı: tek referans sunucu. Üretici farkı fiyat aralıklarında taşınır. K2 kararı: z16 dönemine ait nesil (Xeon 5. nesil) ana senaryodur, Gen12 duyarlılıktır. Kaynaklı tek SKU Xeon Gold 6548Y+'dir:

- SPECrate2017_int_base 628 / 64 çekirdek = 9,81 / çekirdek [SPEC-R760].
- Intel RCP $4.173 / 32 çekirdek, TDP 250 W [INTEL-ARK-6548Y].

Katalogdaki diğer boyutlar (2 × 8, 12, 16, 24 çekirdek) aynı ailenin farklı SKU'larıdır. Çekirdek başına SPECint, fiyat ve güç aynı alınır [ASSUME]. Aynı ailede az çekirdekli SKU'lar daha yüksek frekansta çalışır. Bu yüzden varsayım küçük düğümlerde x86 aleyhine tutucudur.

Ana katalog 64 çekirdekle sınırlıdır, Vonng çapasının (48 çekirdek) ~1,3 katı. 2 × 48 ve 2 × 64 çekirdek "ekstrapolasyon" işaretlidir ve `--allow-extrapolation` ile denenir (KB-06).

### 4.2. Fiyat fonksiyonu (KB-15 fiyat tabanı kuralı)

```
düğüm_net = (şasi_platform + çekirdek × CPU_RCP/çekirdek + NIC/HBA) × (1 − X86_HW_DISCOUNT)    ← liste kalemleri
          + bellek_GB × DRAM $/GB(dönem) + boot_NVMe_TB × NVMe $/TB(dönem)                     ← piyasa fiyatı
bellek_GB = max(128, 8 × çekirdek)
```

İndirim yalnızca liste tabanlı kalemlere ve bir kez uygulanır. Bellek ve NVMe dönem tablosundan piyasa fiyatıyla gelir ve OEM indirimiyle birleştirilmez (ortak modül §7).

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| X86_PLATFORM_COST (USD liste) | 8.000 | 12.000 | 18.000 | [ASSUME; R760xs tabanı $15.957, PCSP-SERVER'dan kaba] |
| X86_CPU_LIST_USD_PER_CORE | — | 130,4 | — | [INTEL-ARK-6548Y] $4.173 / 32 |
| X86_NIC_HBA_LIST_USD | — | 2.000 | — | [ASSUME] 2 × 25 GbE + FC HBA |
| X86_HW_DISCOUNT | 0,50 | 0,35 | 0,20 | [ASSUME] storage indirimiyle aynı mantık |
| DRAM $/GB (2025-mid) | 3,0 | 4,0 | 5,5 | ortak modül `PRICE_EPOCHS` |
| NVMe $/TB (2025-mid) | 80 | 115 | 180 | ortak modül `PRICE_EPOCHS` |
| X86_AMORTIZATION_YEARS | — | 5 | — | mainframe ile aynı |
| X86_WARRANTY_YEARS | — | 3 | — | [ASSUME] KB-11 (mainframe 1 yıl) |
| X86_MAINT_RATE_ANNUAL | — | %12,5 | — | [ASSUME] garanti sonrası, donanım değerinin %10–15'i |

Sonuç (2025-mid, net):

| SKU | Bellek | Net bedel | Güç (%100 yük × 1,25) |
|---|---|---|---|
| 2×8c | 128 GB | $11.189 | 431 W |
| 2×12c | 192 GB | $12.123 | 509 W |
| 2×16c | 256 GB | $13.057 | 588 W |
| 2×24c | 384 GB | $14.925 | 744 W |
| 2×32c | 512 GB | $16.794 | 900 W |
| 2×48c* | 768 GB | $20.530 | 1.212 W |
| 2×64c* | 1.024 GB | $24.267 | 1.525 W |

### 4.3. Kalibrasyon kontrolü (KB-15): yapılamadı

KB-15, bileşen fonksiyonunun tanımlı bir R760 yapılandırmasının Dell yapılandırıcı fiyatına ±%20 yaklaşmasını istiyordu. Tek kaynak [PCSP-SERVER] "amiral" bir R760 için $53.250 liste fiyatı veriyor, ama **yapılandırmayı vermiyor**. Bu yüzden ±%20 kontrolü yapılamadı. Yapılabilen, büyüklük mertebesi kontrolüdür: 2 × 32 çekirdek, 1 TB bellek, 8 × 3,84 TB NVMe için liste eşdeğeri 2025-mid'de $29.975, 2026-Q3'te $81.318'dir. $53.250 bu bandın içindedir. Kamu ihale kayıtları (yapılandırması belli R760 alımları) bulunursa kontrol tamamlanmalıdır (Bölüm 18).

### 4.4. Güç (KB-17)

```
düğüm_kW = (X86_PLATFORM_W + çekirdek × TDP/çekirdek) × X86_POWER_CONFIG_UPLIFT / 1000
```

`X86_PLATFORM_W` = 220 W: DL380 Gen12'nin boşta SPECpower değeri, platform tabanı [SPECPOWER-2025Q1]. `X86_POWER_CONFIG_UPLIFT` 1,1 / 1,25 / 1,4 [ASSUME]: SPECpower sistemleri az bellek ve az diskle ölçülür. Mainframe tepe güç kullandığı için simetri gereği %100 yük değeri alınır.

---

## 5. Kapasite Köprüsü ve Ölçekleme (KB-03, KB-04, KB-06)

### 5.1. Çapa

[VONNG-PERF]: AWS c5d.metal (2 × Xeon Platinum 8275CL, 48 fiziksel çekirdek), "16 x 10M" tablo, oltp_read_write 519.069 QPS. Cascade Lake'in çekirdek başına SPECint değeri 309 / 52 = 5,94 [SPEC-8270].

```
519.069 QPS / 20 ifade = 25.953 TPS
25.953 / 48 çekirdek / 5,94 = 91,0 TPS / SPECint birimi / çekirdek        [DERIVED]
R760: 91,0 × 9,81 = 893 TPS / çekirdek (ham, S = 1)
```

Kaynakta yazmayanlar (Değ. #8 §2.2): sysbench koşusunun PostgreSQL sürümü, iş parçacığı sayısı, süre, istemcinin yeri, `synchronous_commit` ve `fsync` ayarı.

### 5.2. K kararı ve K6 ölçümü

K kararı (Emirhan, 2026-11-16): çapa K6 kendi ölçümümüz olacak, Vonng çapraz kontrol olacak. K6 tamamlanana kadar `X86_TPS_PER_SPECINT_CORE` aralığı **120 / 91 / 60**'tır (low = 120, x86 lehine).

**`project_justification.md` §5.2 ile gerilim.** Gerekçe dokümanı "benchmark koşturma kapsam dışı" der. K6 bununla çelişiyor gibi görünür. Çözüm, ölçümün rolünü sınırlamaktır: araç analitik bir modeldir, ölçüm yalnızca tek bir köprü katsayısının kalibrasyon girdisidir. Model ölçüm olmadan da çalışır (aralık 60–120 ile). Ölçüm geldiğinde aralık daralır, yapı değişmez. Gerekçe dokümanı düzenlenmedi (orijinal tasarım dokümanı); gerilim burada ve tezde açıkça yazılmalıdır.

### 5.3. Düğüm içi ölçeklenme S(n)

```
S(n) = (n / 48)^(B_X86 − 1),   B_X86 = 0,90 (aralık 0,80 – 1,00)     [ASSUME; K6/USL ile kalibre]
```

| n | 16 | 24 | 32 | 48 | 64 | 96* | 128* |
|---|---|---|---|---|---|---|---|
| S(n), mid | 1,116 | 1,072 | 1,041 | 1,000 | 0,972 | 0,933 | 0,907 |

**Köşe yönü düzeltmesi.** KB-06 tablosu B_X86 için low = 1,00 (x86 lehine), high = 0,80 veriyordu. Bu yalnızca n > 48 için doğrudur. n < 48'de küçük b, S(n)'yi büyütür ve x86 lehine olur: 2 × 8 çekirdekte b = 0,80 S'yi 1,25 yapar. Yani "high" köşesi küçük düğümlerde x86'yı ucuzlatıyordu ve aralık yön tutarsızdı. Model aralığı bir düzey anahtarıyla uygular (`X86_SCALING_LEVEL`): low köşesinde iki ucun o düğüm için elverişli olanı (max S), high köşesinde elverişsiz olanı (min S) kullanılır. Mid değişmez. Test: `test_scaling_corners_direction_consistent`.

### 5.4. Ölçekleme mimarisi (KB-06)

**PostgreSQL + Patroni: tek yazıcı.** oltp_rw'nin her işlemi yazma içerdiği için bütün yük birincil düğümdedir. Replikalar yazma kapasitesi eklemez [PATRONI-REPL]. Kapasite yalnızca düğüm büyütülerek artar. Ana katalogda tavan 2 × 32 çekirdek × 807 TPS × 0,70 ≈ **35.900 TPS**'tir. Ekstrapolasyonla (2 × 64 çekirdek) ≈ 67.100 TPS'e çıkar.

**Oracle RAC: düğüm ekleyerek.**

```
ham_TPS(k düğüm) = düğüm_TPS × [1 + (k − 1) × RAC_SCALING_EFFICIENCY]
N+1: k düğümlük kümede k − 1 düğüm bütün yükü taşımalı (en az 1)
```

`RAC_SCALING_EFFICIENCY` 0,95 / 0,90 / 0,80 [ASSUME]. Alt uç Oracle'ın "uygulama ölçeklenmesi %80'in altındaysa çekişme işaretidir" eşiğidir [ORACLE-RAC-2024]. k ≤ 8 (`RAC_MAX_NODES`). Bu formda toplam verimlilik `(1 + (k−1)·e)/k` 8 düğümde bile 0,8'in üstünde kalır, yani Oracle'ın eşiğiyle tutarlıdır. Ana katalogda RAC tavanı ≈ **231.000 TPS**'tir.

**Mainframe tavanı.** F kararıyla (w 9,15 → 12,85) tek z16 CEC'in oltp_rw tavanı ~187K'dan **~132.700 TPS**'e indi. KB-06'nın "F ile yeniden hesaplanacak" notu bu değerle kapanır.

**Tavanların okunuşu.** ~36K TPS'e kadar karşılaştırma mainframe ile PostgreSQL arasındadır. ~36K ile ~133K arasında mainframe ile Oracle RAC arasındadır. ~133K'nın üstünde yalnızca RAC feasible'dır, ama bu bölge iki modellenmeyen ölçekleme seçeneğinin (Parallel Sysplex data sharing ve Citus) dışarıda bırakılmasının sonucudur. İki tavan aynı statüde sınırlamadır.

**RAC düğüm sayısı duyarlılığı.** En ucuz RAC çoğu zaman çok sayıda küçük düğümdür (50K TPS'te 7 × 2×8c). Bunun üç nedeni var: N+1 yedek düğümü küçüldükçe ucuzlar, S(n) küçük düğümde yüksektir ve marjinal RAC verimi sabittir. Gerçek OLTP RAC kümeleri çoğu zaman 2–4 düğümlüdür. Marjinal verimin k ile düştüğü bir form (USL) çok düğümü cezalandırırdı. `RAC_MAX_NODES` = 4 ile 50K TPS'te personel hariç maliyet $3,08'den $3,39/TPS/ay'a çıkar (+%10). 130K TPS ise infeasible olur. Sonuç bu bölgede RAC'ın biçimine duyarlıdır ve K6'dan sonra RAC ölçeklenmesi için bir kaynak aranmalıdır (Bölüm 18).

### 5.5. Platformlar arası kontrol (KB-04)

```
1 z16 CP (3931-701, 2.253 PCI) × 7,939 / w(12,85) = 1.392 oltp_rw TPS
R760 çekirdeği (ham, S = 1) = 893 TPS
1 CP ≈ 1,56 R760 çekirdeği                      (F öncesi: 2,19)
```

Değer KB-04 tablosunun F satırları arasındadır (1,52–1,60). Bu bir doğrulama değil, büyüklük mertebesi kontrolüdür. İki bağımsız zincirde (LSPR + REDP ile SPEC + Vonng) bir mertebe hatası olmadığını gösterir. IBM'in "1 CP = 24–80 x86 çekirdeği" iddiasının büyük kısmı kullanım oranından (U_R) ve dev/test kopyalarından gelir. Bizim köprümüz yalnızca performans oranını ölçer. U_R'nin karşılığı Bölüm 6'da, dev/test Bölüm 12.2'dedir.

---

## 6. Kullanım Tavanı ve Latency (KB-05)

### 6.1. Kural (U kararı)

```
ρ_max   = min(ρ_latency, X86_UTIL_CEILING)                   X86_UTIL_CEILING = 0,90 / 0,70 / 0,50
E[X]    = 1 / TPS_çekirdek
R(p)    = D_ağ + D_io + D_repl + E[X] / (1 − ρ) × ln(1/(1 − p))       (çekirdek başına bağımsız M/M/1)
ρ_lat   = 1 − E[X] × ln(1/(1−p)) / (hedef − D_ağ − D_io − D_repl)
```

- Kuyruk ailesi mainframe ile aynıdır: çekirdek başına bağımsız M/M/1, paylaşımlı M/M/c'den kötü sonuç verdiği için tutucu üst sınırdır.
- Tavanın mainframe'den (%90) düşük olabilmesinin gerekçesi: x86'da WLM ve CoD karşılığı yoktur, veritabanı düğümleri tepe yükte boşlukla işletilir. Low ucu (0,90) mainframe ile eşittir.
- %15–20 "konsolide edilmemiş park" ucu ana aralıkta yoktur (çift sayım). Yalnızca karşılaştırma çıktısında ayrı bir satır olarak gösterilir (Bölüm 16.4).

### 6.2. Sabit gecikme terimleri

| Terim | Kural | oltp_rw değeri |
|---|---|---|
| D_ağ | ifade sayısı × NET_RTT (saklı yordamda 1 × NET_RTT) | 20 × 0,15 ms = 3,0 ms |
| D_io, PostgreSQL | senkron okuma × T_NVME_READ + WAL yazımı × T_NVME_WAL_FSYNC | 2,8 × 141 µs + 1 × 60 µs = 0,45 ms |
| D_io, Oracle | senkron okuma × T_SAN_READ + redo yazımı × T_SAN_WRITE | 2,8 × 250 µs + 1 × 150 µs = 0,85 ms |
| D_repl | senkron kopya varsa commit başına RTT + uzak fsync (+ uzak sitede 20 km × 10 µs/km) | Patroni X1/X2 0,21 ms; X3 0,41 ms; Oracle X2/X3 0,50 ms |

Toplam sabit gecikme: PostgreSQL X1/X2 3,67 ms, X3 3,87 ms; Oracle X1/X4 3,85 ms, X2/X3 4,35 ms. Mainframe'de D_io 0,26 ms (M1) ve 0,46 ms (M2–M4) idi, ağ terimi yoktur (CICS ve Db2 aynı sistemde). Ağ terimi x86'ya özgü, gerçek bir yapısal farktır ve işlem başına gidiş-dönüş sayısıyla görünür bir parametre olarak tutulur.

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| X86_NET_RTT_MS | 0,05 | 0,15 | 0,5 | [ASSUME] aynı veri merkezi |
| X86_STORED_PROCEDURES (gidiş-dönüş/işlem) | 1 | ifade sayısı (20) | ifade sayısı | KB-05 |
| T_NVME_READ_S | — | 141 µs | — | [STORAGEREVIEW-P5520, VENDOR sponsorlu] |
| T_NVME_WAL_FSYNC_S | — | 60 µs | — | [ASSUME] PLP'li kurumsal NVMe; K6 ile ölçülecek |
| T_SAN_READ_S | 150 µs | 250 µs | 400 µs | [ASSUME] |
| T_SAN_WRITE_S | — | 150 µs | — | [ASSUME] dizi NVRAM onayı + fabric |

### 6.3. Davranış

10K TPS'te latency hedefi yokken p99 ≈ 18,9 ms'dir. 20 ms hedefi tavanı %70'ten %69,6'ya indirir ama seçim değişmez. Sabit gecikmenin (3,67 ms) altındaki hedefler infeasible'dır. Mainframe'de aynı yükte p99 ≈ 89 ms (M1, 3931-524; alt-kapasite CP'leri yavaş olduğu için E[X] büyük). Yani tipik OLTP SLA'larında (10–200 ms) latency iki tarafta da kurulu kapasiteyi bağlamaz; x86'da ağ gidiş-dönüşü baskın terimdir. Test: `test_ceiling_rule_and_latency`.

---

## 7. Yığın (v4 §4.8, K7)

### 7.1. Adaylar

| Hipervizör | Yerleşim | Veritabanı | Ek yük |
|---|---|---|---|
| vSphere Foundation | VM | PostgreSQL + Patroni / Oracle | VIRT vSphere |
| vSphere Foundation | VM içinde Kubernetes (Crunchy PGO, Patroni kullanır) | PostgreSQL | VIRT vSphere + CONT |
| vSphere Foundation | VM içinde OpenShift | PostgreSQL | VIRT vSphere + CONT |
| OpenShift Virtualization Engine | VM | PostgreSQL / Oracle | VIRT OCP-V |
| OpenShift Virtualization Engine | VM içinde Kubernetes | PostgreSQL | VIRT OCP-V + CONT |
| OpenShift Virtualization Engine | VM içinde OpenShift | PostgreSQL | VIRT OCP-V + CONT |

Oracle yalnızca VM yerleşimindedir: RAC'ın üretimde konteynerde çalıştırılması modellenmedi [ASSUME, doğrulanmalı]. OpenShift Virtualization üzerinde Oracle'ın sertifika durumu doğrulanmadı; aday olarak tutulur (Bölüm 18).

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| VIRT_OVERHEAD vSphere | 0,03 | 0,07 | 0,15 | [PT-VSPHERE-OCPV-2024] ile [REDHAT-OCPV-2025] arasından [ASSUME] |
| VIRT_OVERHEAD OCP-V | 0,05 | 0,12 | 0,25 | Aynı |
| CONTAINER_OVERHEAD | 0 | 0,02 | 0,05 | [EDB-LOCALPV] + [ASSUME]; yerel kalıcı birimle |
| ORACLE_THROUGHPUT_FACTOR | 1,30 | 1,00 | 0,80 | Kalibre edilemez (OTN benchmark yasağı) |

Çekirdek başına verim (TPS, oltp_rw, mid):

| Yığın | 2×8c | 2×12c | 2×16c | 2×24c | 2×32c |
|---|---|---|---|---|---|
| vSphere / VM (PG ve Oracle) | 927 | 890 | 865 | 830 | 807 |
| vSphere / K8s ya da OpenShift | 908 | 872 | 847 | 814 | 791 |
| OCP-V / VM | 877 | 842 | 818 | 786 | 763 |
| OCP-V / K8s ya da OpenShift | 859 | 825 | 802 | 770 | 748 |

**Oracle çarpanı neden 1,0.** Oracle'ın OTN lisansı "disclose results of any Program benchmark tests without Oracle's prior consent"i yasaklar [ORACLE-OTN]. Aynı donanımda Oracle ile PostgreSQL'i karşılaştıran bağımsız ölçüm yoktur. Orta değer kayıtsızlık ilkesidir. Oracle çekirdek başına lisanslandığı için çarpan maliyeti iki kez etkiler (daha az çekirdek = daha az lisans); tornado'da 50K TPS'te $34,79–35,66 salınım verir.

---

## 8. Topolojiler ve Availability (KB-07, KB-08)

### 8.1. Eşleme

| Kod | Mainframe | Oracle (MAA) | PostgreSQL + Patroni | Düğümler (site A / B) |
|---|---|---|---|---|
| X1 | M1 | Silver: tek sitede RAC + Application Continuity | Tek sitede 3 düğüm (birincil + senkron + asenkron), etcd 3 üye | PG 3 / – ; Oracle k / – |
| X2 | M2 | X1 + uzak sitede Data Guard (Max Availability, SYNC), elle geçiş | X1 + uzak sitede standby küme (2 düğüm), elle terfi | PG 3 / 2 ; Oracle k / max(1, k−1) |
| X3 | M3 | Gold: iki sitede RAC + Active Data Guard + Fast-Start Failover, gözlemci 3. sitede | İki sitede 2 + 2 düğüm, `synchronous_mode`, en az bir uzak senkron kopya, DCS 3 sitede | PG 2 / 2 ; Oracle k / k (+ tanık) |
| X4 | M4 | Platinum: iki sitede aktif-aktif RAC + GoldenGate (asenkron) | **Infeasible** (K4) | Oracle k / k (+ tanık) |

X3 ve X4'te üçüncü sitede tek bir küçük tanık düğümü (2×8c) fiyatlanır: Patroni için DCS'in üçüncü üyesi ("To have a multi DC cluster that can automatically tolerate a zone drop, a minimum of 3 is required." [PATRONI-MULTIDC]), Oracle için FSFO gözlemcisi.

### 8.2. Düzeltme: Patroni X2'nin RPO'su sıfır değil (KB-08)

KB-08 X2 için iki veritabanında da RPO 0 yazıyordu. Bu, Oracle için doğrudur (Data Guard Maximum Availability, SYNC). Patroni için doğru değildir. Patroni belgeleri iki veri merkezi için standby kümeyi "Asynchronous Replication" başlığı altında önerir: "With only two data centers it would be better to have two independent etcd clusters and run Patroni standby cluster in the second data center." [PATRONI-MULTIDC]. Standby küme birincil kümeden akışla (asenkron) beslenir. Bu yüzden X2-PG'nin RPO'su 0 değildir; model `X2_PG_ASYNC_RPO_SECONDS` = 5 sn alır [ASSUME, M4 ile aynı büyüklük]. Sonuç: RPO = 0 isteyen bir PostgreSQL kurulumu X3'e (uzak senkron kopya) gitmek zorundadır. Test: `test_topologies_and_availability`. Köprüler dokümanı (KB-08) bu düzeltmeyle güncellenmelidir.

### 8.3. Availability denklemi

Saha olayları iki tarafta ortaktır (`common_model` §2). x86'ya özgü terimler:

```
D(yıl) = D_saha(T_kurtarma)                                         ← ortak
       + λ_planlı × T_planlı                                         ← büyük sürüm, bakım
       + X86_PATCH_SWITCHOVERS_PER_YEAR × T_switchover               ← aylık OS / hipervizör yaması
       + N_kesen × λ_düğüm × T_failover × (1 − u)                    ← düğüm arızası, geçişle maskelenen
       + N_kesen × ITIC_sunucu × u^katman                            ← platform kesintisi (ortak formül)
A = 1 − D / 8.760
```

**Platform kesintisi (Değerlendirme #10, A kararı, Emirhan 2026-11-24).** Mainframe tarafı CPC kesintisini ITIC'ten alıyordu; x86 tarafı ise yalnızca donanım arızası × failover süresini sayıyor ve sunucunun kendi (donanım + işletim sistemi) kesintisini, ayrıca geçişin başarısız olduğu durumları hiç saymıyordu. Bu, x86'yı en yüksek hedeflerde iyimser gösteriyordu: X3 Patroni yılda 4,4 dk ile %99,999'u tutturuyordu. Artık iki taraf aynı formülü (`common_model.platform_downtime_hours`) aynı kaynakla kullanır: sunucu başına ITIC yıllık plansız kesintisi × geçişin maskeleyemediği pay u (`PLATFORM_UNMASKED_SHARE`, ortak parametre). Tek CPC'de u = 1, kümede u, aktif-aktif iki sitede (M4 / X4) u². x86 ITIC değerleri [ITIC-2023]: Lenovo ThinkSystem Linux 31,5 sn (low), Dell PowerEdge Linux 24 dk (mid; katalogdaki sunucu R760 sınıfıdır), white box Linux 59 dk (high); düzey `NODE_EVENT_LEVEL` ile birlikte seçilir. z16 için aynı terim yılda 0,03–3 saniyedir.

u kaynakla daraltılamadı [ASSUME]: dağıtık sistemlerde katastrofik hataların %92'si hata işleme yolundan çıkar [YUAN-2014]; bulut kesintilerinde kurtarma mekanizmasının kendisi sık sık hata üretir [GUNAWI-2016]; Uptime 2025'e göre büyük BT/yazılım kesintilerinin %62'sinde konfigürasyon ya da değişiklik yönetimi vardır [UPTIME-2025]. Bu kaynaklar yönü destekler, sayıyı vermez. Sonuç u'ya hassastır (§16.5).

**Desteksiz PostgreSQL (B kararı).** Ticari desteği olmayan bir PostgreSQL yığınında (`PG_SUPPORT_USD_PER_CORE_YEAR` = 0) platform kesintisi ITIC'in high ucundan (59 dk) sayılır [ASSUME]: sürüm hatasında üretici eskalasyonu yoktur. Desteğin SLA'ya bağlı zorunluluğu §9.2'dedir.

N_kesen: arızası hizmeti kesen düğüm sayısı. Patroni'de yalnızca birincildir (replika arızası hizmeti kesmez). RAC'ta hizmeti taşıyan her düğümdür (düğüm kaybında küme yeniden yapılandırması bütün oturumları kısa süre dondurur).

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| NODE_EVENTS_PER_YEAR | 0,03 | 0,10 | 0,30 | [VISHWANATH-2010] aşağı; high [ASSUME] |
| X86_ITIC_DOWNTIME_MINUTES (sunucu başına, dk/yıl) | 0,525 | 24 | 59 | [ITIC-2023] Lenovo / Dell / white box Linux |
| PLATFORM_UNMASKED_SHARE u (ortak) | 0,05 | 0,10 | 0,20 | [ASSUME]; nitel dayanak [YUAN-2014], [GUNAWI-2016] |
| T_FAILOVER PostgreSQL (sn) | 15 | 35 | 90 | [PIGSTY-RTO] 27–41 sn |
| T_FAILOVER Oracle (sn) | 5 | 15 | 300 | [ORACLE-RAC-2024], [ORACLE-MAA-2026] |
| X86_PLANNED_EVENTS_PER_YEAR | 0,25 | 0,5 | 1,0 | mainframe ile aynı aralık [ASSUME] |
| X86_PLANNED_OUTAGE_MINUTES tek site (X1–X2) | 5 | 15 | 60 | [ASSUME] |
| X86_PLANNED_OUTAGE_MINUTES çok site (X3–X4) | 0,5 | 2 | 10 | [ASSUME]; Oracle Gold < 30 sn |
| X86_PATCH_SWITCHOVERS_PER_YEAR | — | 12 | — | [Değ. #8 §3.4, ASSUME] |
| T_switchover PostgreSQL (sn) | 5 | 15 | 30 | [ASSUME] |
| T_switchover Oracle (sn) | 0 | 5 | 15 | [ASSUME] RAC rolling + Application Continuity |
| Teknik geçiş X2 (dk) | 5 | 15 | 30 | [ASSUME]; ortak elle karar süresi eklenir (mid toplam 105 dk) |
| Teknik geçiş X3 (dk) | 1 | 2 | 5 | Gold "saniyeler – 2 dk"; Patroni 30–90 sn |
| Teknik geçiş X4 (dk) | 0,05 | 0,25 | 0,5 | Platinum < 30 sn |

### 8.4. Sonuçlar

| Topoloji | PostgreSQL | Oracle (k = 2) | Mainframe karşılığı | RPO / RTO |
|---|---|---|---|---|
| X1 | %99,98230 (99,91549 – 99,99794); 1,55 sa/yıl | %99,98222 | M1 %99,96193 | 24 sa / 72 sa |
| X2 | %99,99454 (99,97514 – 99,99909) | %99,99446 | M2 %99,99372 | PG 5 sn, Oracle 0 / 105 dk |
| X3 | %99,99872 (99,99440 – 99,99977); 6,7 dk/yıl | %99,99864 (99,99234 – 99,99996) | M3 %99,99975 | 0 / 2 dk |
| X4 | infeasible | %99,99941 (99,99479 – 99,99997) | M4 %99,99994 | 5 sn / 15 sn |

Değerlendirme #10 sonrası değerler. Desteksiz PostgreSQL X1: %99,98163. X3 artık %99,999'un (5,26 dk/yıl) altında kalır: RPO 0 isteyen beş dokuz hedefini x86 sağlayamaz, mainframe M3 sağlar (§16.5).

X1'in M1'den biraz yüksek çıkması planlı kesintiden gelir: tek frame'li M1'de yıllık planlı kesinti daha uzundur; Patroni kümesinde yamalar saniyeler süren switchover'larla yapılır. Kesintinin baskın terimi iki tarafta da ortak saha olayıdır (X1'de 1,34 saatin tamamı). Bu, Bölüm 1.2'deki ilkenin sonucudur: iki taraf aynı saha olayına aynı fizikle maruz kalır, fark yalnızca kurtarma süresinden ve planlı işlemlerden gelir.

---

## 9. Lisanslar ve Abonelikler (KB-11)

### 9.1. Yapısal asimetri

Mainframe yazılımı tüketilen MSU'nun aylık R4HA tepesinden faturalanır ve DR frame'i CBU kuralıyla kalıcı (küçük) kapasitesinden faturalanır. x86'da fatura tabanı kurulu fiziksel çekirdek ya da düğümdür; DR sitesindeki düğümler tam lisans ister; geçici kapasite yoktur. Bu fark eşitlenmez, modellenir. Test: `test_dr_sites_fully_licensed`.

### 9.2. Kalemler

| Kalem | Kural | low | mid | high | Dayanak |
|---|---|---|---|---|---|
| vSphere Foundation | çekirdek başına yıllık; CPU başına en az 16, sipariş başına en az 72 çekirdek | $100 | $150 | $350 | [ACEMQ-VVF], [ACEMQ-RENEW] |
| OpenShift Virtualization Engine | düğüm başına yıllık (1–2 soket, ≤ 128 çekirdek) | $6.000 | $8.000 | $10.000 | [CDW-OVE] premium $9.880 |
| RHEL for Virtual Datacenters | düğüm başına yıllık; sınırsız misafir | — | $2.904 | — | [CCSP-RH] hizmet sağlayıcı listesi |
| OpenShift Container Platform | sanal düğümde 2 çekirdek başına yıllık; RHEL dahil; kontrol düzlemi sayılmaz | $2.000 | $3.000 | $4.200 | [RH-OCP-GUIDE], [SWEXPRESS-OCP], [VENDORBENCH-OCP] |
| Oracle EE + seçenekler | işlemci = çekirdek × 0,5 (yukarı yuvarlanır); net = liste × (1 − indirim); destek net lisansın yıllık %22'si | indirim 0,60 | 0,45 | 0,20 | [ORACLE-CORE], [REDRESS-PL2026], [OLE-NET2026] |
| PostgreSQL ticari destek | çekirdek başına yıllık; SLA tabanı aşağıda | $0 | $500 | $1.500 | [ASSUME]; EDB mağaza fiyatlarıyla aynı mertebe [EDB-STORE-2026] |

**SLA'ya bağlı zorunlu PostgreSQL desteği (Değerlendirme #10, B kararı).** EDB mağaza fiyatları (çekirdek/yıl, en az 8 çekirdek, 1 yıl): Community $400, Business $1.600, Enterprise $2.400 [EDB-STORE-2026]. Destek seviyeleri: Basic 10x5 (yalnız geliştirme/test), Production 7/24, Premium 7/24 + sıkı SLO [EDB-PLANS-2026]. Kural (`pg_support_rate`; eşikler [ASSUME]): hedef < %99,99 ve RPO > 0 ise destek isteğe bağlıdır (aralık parametresi); hedef ≥ %99,99 ya da RPO 0 ise en az $1.600 (7/24 üretim desteği); hedef ≥ %99,999 ise $2.400 (Enterprise). Maliyet etkisi küçüktür (10K TPS'te ayda $5–13K); asıl etkisi, desteksiz yığının yalnız düşük hedeflerde seçilebilmesi ve availability'sinin ITIC'in high ucundan sayılmasıdır (§8.3). Düzenleyici boyut (ör. AB DORA'nın kritik fonksiyonlarda sözleşmeli ICT tedarikçisi beklentisi) modele girmez, tezde nitel olarak yazılır.

vSphere'in asgarileri küçük düğümlerde belirleyicidir: 2 × 8 çekirdekli bir sunucu 32 çekirdek olarak lisanslanır ve tek düğümlük bir sipariş 72 çekirdeğe tamamlanır. Model sipariş asgarisini grupların lisanslı çekirdeklerine oranla dağıtır. Test: `test_platform_subscriptions`.

Oracle seçenekleri topolojiye bağlıdır: her düğümde EE + Diagnostics Pack + Tuning Pack (operasyon için fiilen zorunlu), birden çok düğümlü sitede RAC, X3'te Active Data Guard, X4'te GoldenGate. Liste fiyatları (işlemci başına): EE $47.500, RAC $23.000, Diagnostics $7.500, Tuning $5.000 [REDRESS-PL2026] (doğrulanmalı); ADG $11.500 ([ORACLE-PL2009]'daki $10.000'den yaygın kabul; doğrulanmalı); GoldenGate $17.500: "GoldenGate costs $17,500 per processor on every server that runs it, source and target alike" [REDRESS-GG]. GoldenGate lisansı ADG'yi içerir: "A GoldenGate license includes Oracle Active Data Guard and Oracle XStream, with Database Enterprise Edition as the prerequisite." [REDRESS-GG]. Bu yüzden X4'te ADG ayrıca sayılmaz. VM'in çalışabileceği bütün fiziksel çekirdekler lisanslanır [ORACLE-PART]; model Oracle'ı adanmış düğümlerde varsayar. Test: `test_oracle_license_math`.

Oracle lisansı kalıcıdır (perpetual). Statik modda 5 yıla amortismanlanır ve buna yıllık %22 destek eklenir. NPV'de alım yılında nakit olarak girer (Bölüm 15).

### 9.3. Düzeltme: OpenShift sayım kuralı (KB-11)

KB-11 OpenShift'i soket çifti başına (`OCP_USD_PER_SOCKETPAIR_YEAR` 6K / 11K / 15K) fiyatlıyordu. Red Hat'in abonelik kılavuzu soket çifti aboneliğinin yalnızca bare-metal düğüm için olduğunu söyler: "Each physical, bare-metal server using socket-based entitlements can only be used as a single OpenShift node." Hipervizör üzerindeki sanal düğümler çekirdek tabanlı abonelik ister: "entitling the virtual compute nodes using core-based subscriptions." [RH-OCP-GUIDE]. v4 kuralı bare-metal Kubernetes'i dışladığı için bu modelde OpenShift düğümleri her zaman sanaldır. Bu yüzden soket çifti fiyatı kullanılmaz; yerine `OCP_USD_PER_COREPAIR_YEAR` (2 çekirdek / 4 vCPU başına) gelir. Orta değer: Premium 2 çekirdek 1 yıl 3.872 € ([SWEXPRESS-OCP], "Red Hat OpenShift Container Platform; Premium (2 Cores or 4 vCPUs); Subscription; 1 Jahr", KDV hariç) ≈ $4.200; Standard ~%25–35 aşağı [VENDORBENCH-OCP] ≈ $3.000. Köprüler dokümanı (KB-11) bu düzeltmeyle güncellenmelidir.

---

## 10. Uygulama Katmanı (KB-12, C kararı)

Mainframe CPU'su ve lisansı CICS'i (işlem yöneticisi) içerir. x86 çapasında uygulamanın yerini modelin dışındaki sysbench istemcisi tutar. Bu, mainframe aleyhine bir kapsam asimetrisiydi. C kararı x86'ya köprüyle boyutlanmış bir uygulama katmanı ekler:

```
TM_payı                 = CPU_US_TM_BASE / CPU(profil)                  oltp_rw, F ile 85,9 / 1.103,9 = %7,8
uygulama_meşgul_çekirdek = DB_meşgul_çekirdek × TM_payı / (1 − TM_payı)
DB_meşgul_çekirdek       = TPS / TPS_çekirdek                            (sanallaştırma ek yükü içinde)
host sayısı (site başına) = max(2, ⌈uygulama_meşgul / (SKU_çekirdek × X86_UTIL_CEILING)⌉ + 1)   (N+1)
```

- Linux VM olarak fiyatlanır: donanım + hipervizör + RHEL (ya da OpenShift). Açık kaynak uygulama sunucusu olduğu için ek lisans yoktur.
- Her veritabanı sitesinde bir kopya bulunur (DR sitesinde de).
- Kendi bulgumuz: ilk sürümde tavan (`X86_UTIL_CEILING`) ve sanallaştırma ek yükü uygulama çekirdeğine iki kez uygulanıyordu (DB çekirdek ihtiyacı zaten tavana bölünmüştü). Düzeltildi; tavan yalnızca host boyutlamasında, bir kez uygulanır. Test: `test_app_tier`.
- [SHEDLETSKY-2008]'in uygulama katmanında 4,9 kat komut farkı iddiası yalnızca üst uç duyarlılığıdır (`X86_APP_TM_MULTIPLIER`).

10K TPS'te uygulama katmanı 0,9 meşgul çekirdektir ve N+1 kuralı gereği 2 × 2×8c host ister. Toplam maliyetin %0,3'üdür (personel hariç maliyetin %12'si).

---

## 11. Storage ve Yedek (KB-09, KB-10, K1)

### 11.1. Storage tipi DB'ye bağlı (K1)

| DB mimarisi | Storage | Gerekçe | Kopya |
|---|---|---|---|
| PostgreSQL + Patroni (paylaşımsız) | Her düğümde yerel NVMe | Kubernetes'te yerel kalıcı birim bare-metal'e yakın (okuma −%3,6, yazma −%0,8), ağ tabanlı paylaşımlı birim −%89–95 [EDB-LOCALPV] | Düğüm sayısı kadar tam kopya |
| Oracle RAC (paylaşımlı disk) | Site başına all-flash dizi (ASM) | RAC'ın paylaşımlı disk mimarisi | Site başına bir dizi |

### 11.2. Boyutlandırma

```
planlı_veri = veri × (1 + büyüme)^3                                (ortak; 20 TB → 30,4 TB)
PG düğümü:  ham_TB = planlı_veri × PG_BLOAT_FACTOR                  (MVCC şişmesi, WAL tutma)
            sürücü sayısı = max(4, ⌈ham / sürücü_TB⌉, ⌈IOPS / (500K × 0,70)⌉)  ≤ 24 yuva
Oracle:     ham_TB(site) = planlı_veri × 1,5 / 0,75 (RAID); birincilde + %25 değiştirilemez anlık kopya
            dizi sayısı = max(1, ⌈ham / 3.000 TB⌉, ⌈IOPS / (1M × 0,70)⌉)
```

Patroni'de her düğüm yazma IOPS'unun tamamını taşır (replikalar WAL uygular) ve terfi edebileceği için okuma IOPS'una göre boyutlanır. 24 yuvaya sığmayan veri PostgreSQL için infeasible'dır: 24 × 30,72 TB / 1,3 ≈ 567 TB planlı verinin (bugünkü ~373 TB'ın) üstünde PostgreSQL elenir ve model Oracle'a geçer. Test: `test_storage_rules`.

Birincil dizideki %25 değiştirilemez anlık kopya rezervi DS8900F Safeguarded Copy'nin karşılığıdır (aynı oran).

### 11.3. Fiyat sözleşmesi (ortak modül §6)

AFA teklifleri etkin TB başınadır (veri azaltımı dahil). Önce ham TB başına listeye çevrilir:

```
USD/ham TB (liste) = AFA_LIST_USD_PER_EFF_TB × AFA_RAID_USABLE × AFA_DATA_REDUCTION
net = max(dizi × giriş dizisi listesi, ham_TB × USD/ham TB) × (1 − AFA_DISCOUNT)
```

Boyutlandırmada veri azaltımı sayılmaz (1,0); mainframe'deki `HOST_COMPRESSION_RATIO` ile simetriktir. Yerel NVMe dönem tablosundan piyasa fiyatıyla gelir ve sunucu bakım kuralına bağlıdır.

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| PG_BLOAT_FACTOR | 1,1 | 1,3 | 1,6 | [ASSUME] |
| AFA_LIST_USD_PER_EFF_TB | 140 | 270 | 400 | [VENDORBENCH-AFA] liste aralığı |
| AFA_DISCOUNT | — | 0,50 | — | [DERIVED, VENDORBENCH-AFA] indirimli / liste |
| AFA_DATA_REDUCTION (geri çevirme) | 1,5 | 2,5 | 4,0 | [ASSUME] |
| AFA_RAID_USABLE | — | 0,75 | — | mainframe ile aynı |
| AFA_MIN_LIST_USD | — | 100.000 | — | [ASSUME] çift kontrolcülü giriş dizisi |
| AFA_MAINT_RATE_ANNUAL | — | %15, ilk yıldan | — | [VENDORBENCH-AFA] |

### 11.4. Yedek (KB-10)

Hacim kuralı ortaktır (`common_model.backup_volumes`): 4 haftalık tam yedek + günlük artımlı (%3) + işlem bileşiminden log hacmi, iki sitede. x86 hedefleri mainframe ile aynı fiyat fonksiyonlarını kullanır: on-prem nesne depolama ve AWS S3 (TS7770 x86'ya uygulanmaz). Yazılım lisans gerektirmez: pgBackRest açık kaynaktır, RMAN ve BASIC sıkıştırma EE'ye dahildir.

- PostgreSQL WAL'ında full-page write vardır: log hacmi × `WAL_FPW_FACTOR` 1,5 / 2,0 / 3,0 [ASSUME; K6 ile ölçülecek].
- Sıkıştırma `X86_BACKUP_COMPRESSION` 3,0 / 2,0 / 1,5 [ASSUME]. Mainframe'de nesne depolama hedefine sıkıştırma uygulanmıyor; bu bir asimetridir ama x86 platformunun kendi özelliğidir (pgBackRest zstd/lz4) ve sonucu küçük etkiler.
- Kısıtlar mainframe ile aynı: 8 saatlik yedek penceresi; alternatif sitesi olmayan topolojide (X1) tam geri yükleme RTO'nun yarısına (36 saat) sığmalı; yedek akışı 5.000 MB/s (2 × 25 GbE × %80) [ASSUME].

10K TPS / 20 TB'ta: on-prem nesne depolama, site başına 101 TB, aylık $4.917 (site başına $70K asgari sistem belirleyici). Test: `test_backup_rules`.

---

## 12. Personel ve Üretim Dışı Ortamlar (KB-13, KB-14)

### 12.1. Personel (P kararı)

```
FTE_ortak(TPS) = max(taban, FTE_1000 × (PCI_eşdeğer(TPS) / 1000)^b) × topoloji_çarpanı      (common_model §12)
PCI_eşdeğer(TPS) = TPS × w(profil) × (1 − f) / 7,939 / 0,90                                   (mainframe köprüsü)
FTE_x86 = FTE_ortak(TPS) × STAFF_RATIO_X86                                                     (ana senaryo 1,0)
```

- Personel crossover için nötrdür. x86'ya özgü personel değişkenleri (sunucu başına 32 saat, imaj başına 36 saat, DBA saati, yığın çarpanı) elendi.
- Topoloji çarpanı ortak tablodur: X1 1,00 · X2 1,05 · X3 1,15 · X4 1,25.
- 10K TPS'te iki tarafta da 38,6 FTE, aylık $521.333 (M1/X1). Test: `test_staff_neutral_and_breakeven`.
- `STAFF_RATIO_X86` aralık parametresi değildir. 1,25 ve 2,0 duyarlılık senaryolarıdır ve IBM vakalarına atıfla, üretici yanlılığı notuyla raporlanır.

### 12.2. Üretim dışı ortamlar (N kararı)

```
nonprod = NONPROD_FACTOR_X86 × birincil sitenin {yazılım + compute donanımı (amortisman + bakım) + enerji + birincil storage}
```

`NONPROD_FACTOR_X86` 0 / 0,50 / 1,00, stres 2,0 [IBM-EAGLE-2013]. Orta değerin türetmesi: X1'de birincil sitede 3 düğüm var; üretim boyutunda tek düğümlük staging ≈ 0,33, küçük dev/test ≈ 0,1–0,2 [DERIVED, ASSUME]. Oracle'da üretim dışı ortamlar da çekirdek lisansı ister (OTN geliştirme lisansı yalnızca saf geliştirme içindir); bu yüzden yazılım tabana girer. DR, yedek ve personel tabana girmez. Test: `test_nonprod_x86`.

---

## 13. Toplam Maliyet ve Seçim Motoru

### 13.1. Formül

Her düğüm grubu (rol × site) için:

```
yazılım_ay = (hipervizör + işletim sistemi + orkestrasyon + PG destek)_yıl / 12
           + Oracle_net / 60 + Oracle_net × 0,22 / 12
donanım_ay = n × düğüm_net / 60
bakım_ay   = n × düğüm_net × 0,125 × (5 − 3) / 5 / 12
enerji_ay  = n × düğüm_kW × 8.760 × $0,12 / 12
toplam     = Σ gruplar + storage + yedek + personel + üretim dışı
```

### 13.2. Seçim

Her (yığın, topoloji) için: PostgreSQL'de katalogdaki ilk feasible SKU (maliyet SKU ile monoton), Oracle'da her SKU için ilk feasible k ve SKU'lar arasında en ucuzu. Sonra bütün (yığın, topoloji) çiftlerinin en ucuzu seçilir. Bir yapılandırma şu durumlarda elenir: topoloji DB'yi desteklemiyor (X4-PG), availability/RPO/RTO kısıtı sağlanmıyor, kapasite ρ_max altında yetmiyor, NVMe yuvaları yetmiyor, yedek akışı yetmiyor.

### 13.3. Maliyet / TPS eğrisi (%99,9, mid; low / high aralıkla)

| TPS | low | mid | high | Seçilen (mid) | Topoloji | Düğüm | Sunucu | Personel hariç $/TPS | Personel payı |
|---|---|---|---|---|---|---|---|---|---|
| 1.000 | 60,88 | 118,98 | 222,82 | vSphere / VM / PostgreSQL | X1 | 2×8c | 5 | 14,96 | %87 |
| 5.000 | 29,55 | 67,20 | 144,77 | vSphere / VM / PostgreSQL | X1 | 2×8c | 5 | 3,01 | %96 |
| 10.000 | 22,01 | 53,66 | 124,91 | vSphere / VM / PostgreSQL | X1 | 2×8c | 5 | 1,52 | %97 |
| 20.000 | 16,49 | 43,49 | 122,02 | vSphere / VM / PostgreSQL | X1 | 2×24c | 5 | 1,14 | %97 |
| 30.000 | 13,95 | 38,41 | 114,11 | vSphere / VM / PostgreSQL | X1 | 2×32c | 5 | 0,91 | %98 |
| 50.000 | 11,34 | 35,25 | 105,01 | vSphere / VM / Oracle | X1 | 2×8c, k = 7 | 9 | 3,08 | %91 |
| 100.000 | 9,03 | 29,03 | infeasible | vSphere / VM / Oracle | X1 | 2×16c, k = 7 | 9 | 2,90 | %90 |
| 130.000 | 8,21 | 27,29 | infeasible | vSphere / VM / Oracle | X1 | 2×32c, k = 5 | 7 | 3,14 | %88 |
| 200.000 | 6,97 | 24,45 | infeasible | OCP-V / VM / Oracle | X1 | 2×32c, k = 8 | 10 | 3,23 | %87 |

Okuma:

- **Personel hariç maliyet Patroni tavanında kırılır.** 30K TPS'e kadar PostgreSQL'in lisans maliyeti yoktur ve personel hariç maliyet $0,91/TPS/ay'a kadar düşer. Tavanın (~36K) üstünde Oracle RAC'a geçiş zorunludur ve Oracle lisansı ile desteği personel hariç maliyeti üç katına çıkarır ($3,08). Bu, x86 tarafının kendi yapısal crossover'ıdır (açık kaynak ↔ ticari veritabanı) ve mainframe karşılaştırmasından bağımsızdır.
- **Personel payı %87–98'dir.** Bu yüzden x86 aralığını personel eğrisi ve ücret belirler (Bölüm 14).
- **K8s ile VM eşittir.** 10K TPS'te vanilla Kubernetes'in %2 ek yükü SKU'yu değiştirmez ve lisans eklemez. OpenShift yerleşimi çekirdek başına abonelik ekler ($549.737, +%2,5).
- **OpenShift Virtualization vSphere'den bir boy büyük SKU ister** (ek yük %12'ye karşı %7) ama çok büyük düğümlerde düğüm başına fiyatı (OVE) çekirdek başına vSphere'den ucuza gelir (200K TPS).

Yığın tablosu, 10K TPS, %99,999 (X3):

| Yığın | SKU | $/TPS | Personel hariç | Oracle |
|---|---|---|---|---|
| vSphere / VM / PostgreSQL | 2×8c | 61,83 | 1,88 | — |
| vSphere / K8s / PostgreSQL | 2×8c | 61,83 | 1,88 | — |
| OCP-V / VM / PostgreSQL | 2×12c | 62,31 | 2,35 | — |
| OCP-V / K8s / PostgreSQL | 2×12c | 62,31 | 2,35 | — |
| vSphere / OpenShift / PostgreSQL | 2×8c | 63,59 | 3,64 | — |
| OCP-V / OpenShift / PostgreSQL | 2×12c | 64,56 | 4,61 | — |
| vSphere / VM / Oracle | 2×8c, k = 2 | 69,10 | 9,15 | 5,82 |
| OCP-V / VM / Oracle | 2×12c, k = 2 | 73,05 | 13,09 | 8,73 |

### 13.4. Fiyat dönemi duyarlılığı (E kararı)

2026-Q3 bileşen şoku x86'yı az etkiler: 10K TPS $53,66 → $53,99, 50K $35,25 → $35,28. Mainframe sayıları değişmez (IBM fiyatlarının şoka tepkisi bilinmiyor; sınırlama). Bellek ve NVMe x86 personel hariç maliyetinin küçük bir payıdır; şok asıl veri hacmi ekseninde (NVMe) görünür.

---

## 14. Aralık ve Tornado (KB-18)

36 parametre low / mid / high'a çekilir (low = x86 lehine; ortak parametrelerde low iki tarafı birlikte ucuzlatır). `STAFF_RATIO_X86` aralığa girmez. Mainframe'e özgü bileşim parametreleri (CPU_US_PER_SQL_*) x86'da yalnızca personel girdisini etkiler ve burada mid'de kalır.

| Grup | Parametreler |
|---|---|
| Köprü ve ölçekleme | X86_TPS_PER_SPECINT_CORE (120/91/60), X86_SCALING_LEVEL, VIRT_LEVEL, CONTAINER_OVERHEAD, ORACLE_THROUGHPUT_FACTOR, RAC_SCALING_EFFICIENCY, X86_UTIL_CEILING |
| Latency | X86_LATENCY_LEVEL, X86_STORED_PROCEDURES, T_SAN_READ_S |
| Fiyat | COMPONENT_PRICE_LEVEL, X86_PLATFORM_COST, X86_HW_DISCOUNT, X86_POWER_CONFIG_UPLIFT, VSPHERE, OVE, OCP, ORACLE_DISCOUNT, PG_SUPPORT, AFA_LIST, AFA_DATA_REDUCTION |
| Storage ve yedek | PG_BLOAT_FACTOR, BACKUP_RETENTION_WEEKS, X86_BACKUP_COMPRESSION, WAL_FPW_FACTOR, COS_HW, COS_SW |
| Availability | NODE_EVENT_LEVEL, SITE_EVENT_LEVEL, X86_RECOVERY_LEVEL, X86_PLANNED_LEVEL |
| Ortak | STAFF_SCENARIO, WAGE_LEVEL, RANGE_READ_WEIGHT, BP_HIT_RATIO |
| Üretim dışı | NONPROD_FACTOR_X86 |

**10K TPS: $22,01 / $53,66 / $124,91.** High köşesinde OCP-V / VM / PostgreSQL 2×24c seçilir (köprü 60, tavan 0,50, sanallaştırma high). Tornado'nun ilk sırası (diğerleri mid, $/TPS/ay):

| Parametre | low | high |
|---|---|---|
| Personel eğrisi + taban ekip (ortak) | 30,22 | 89,17 |
| Yüklü personel ücreti (ortak) | 40,78 | 70,71 |
| Aralık / nokta okuma oranı (ortak, F) | 52,66 | 54,64 |
| PostgreSQL ticari destek | 53,36 | 54,26 |
| x86 üretim dışı ortamlar | 53,31 | 54,00 |
| vSphere USD/çekirdek | 53,56 | 54,02 |
| x86 köprü (K) | 53,66 | 53,98 |

**50K TPS: $11,34 / $35,25 / $105,01** (low köşesinde ekstrapolasyonsuz PostgreSQL 2×32c yetiyor; mid ve high Oracle RAC). Tornado: personel eğrisi 18,16–66,61; ücret 27,31–45,78; köprü 34,43–36,60; üretim dışı 34,26–36,25; Oracle indirimi 34,52–36,47; kullanım tavanı 34,79–36,36; aralık okuma oranı 34,64–35,86; Oracle verim çarpanı 34,79–35,66.

Okuma: personel nötr olduğu için x86'nın kendi parametrelerinden hiçbiri, ortak personel parametrelerinin yanında büyük değildir. Köprü belirsizliği (K6'ya kadar 60–120) 10K TPS'te yalnızca bir SKU adımıdır; Oracle bölgesinde (50K) lisanslı çekirdek sayısı üzerinden daha belirgindir.

---

## 15. NPV ve Yıllık Mod (KB-16, KB-11)

### 15.1. NPV kuralları

Kurallar ortaktır (`common_model` §8): 5 yıl, capex yıl başında, opex yıl sonunda, kalan değer 0, %7 iskonto, yük yılda %10 büyür. Artış sınıfları: abonelikler ve Oracle desteği `SW_PRICE_ESCALATION`, bakım `HW_SERVICE_ESCALATION`, personel `WAGE_ESCALATION`, enerji `ENERGY_ESCALATION`.

x86'ya özgü kurallar:

- Yığın ve topoloji 1. yılda seçilir ve 5 yıl sabit kalır. Seçim, **bütün yolu feasible taşıyabilen** adaylar arasında en düşük NPV'li olandır. (Mainframe'de topoloji kapasiteyi değiştirmediği için yıl-1 seçimiyle aynı sonucu verir. x86'da yığın kapasiteyi belirler: Patroni tavanını 5. yılda aşacak bir PostgreSQL yolu seçilemez.)
- Kapasite yalnızca yükselir. Yükseltme ya düğüm büyütmedir (aynı platformda CPU değişimi + bellek eki; eski CPU'lar geri kazanılmaz) ya da RAC'a düğüm eklemektir.
- Oracle lisansı artan işlemci sayısı kadar ek alımdır.
- Storage ve yedek `STORAGE_PLANNING_YEARS`'lık döngülerle alınır (mainframe ile aynı).
- Sunucu bakımı her alımın garantisi (3 yıl) bittikten sonra başlar.

**Tutarlılık testi.** r = 0, büyüme 0 ve artışlar 0 iken NPV = 60 × statik aylık toplamdır; iki veritabanında ve X1/X3'te 1e-9 hassasiyetle sağlanır (`test_npv_consistency_and_direction`).

### 15.2. Sonuçlar (10K TPS)

| | x86 | Mainframe |
|---|---|---|
| NPV | $32,07M | $68,62M |
| Seviyelendirilmiş maliyet | $54,07 / TPS / ay | $115,70 / TPS / ay |
| NPV aralığı (low / mid / high) | $12,67M / $32,07M / $78,30M | — |
| Seviyelendirilmiş aralık | $21,36 / $54,07 / $132,03 | $35,44 / $115,70 / $641,33 |

x86 yolu: 1. yıl 2×8c; 2. yılda 2×12c'ye CPU değişimi ve bellek eki ($6.871, üretim dışı payıyla $10.307); 4. yılda ikinci storage döngüsü ($3.974). NPV'nin %97,2'si personeldir. Seviyelendirilmiş maliyet statik değere çok yakındır ($54,07 / $53,66); mainframe'deki gözlemle aynı.

### 15.3. Yıllık mod: CoD karşılığı yok

On-prem x86'da geçici kapasite yoktur: kapasite yılın tepe saatine göre kurulur, lisans kurulu çekirdekten ödenir. Yıllık maliyet = 12 × (tepe yükte aylık); log hacmi yıllık ortalamadan, personel tepe TPS'ten (mainframe yıllık moduyla aynı kural).

| Preset (ortalama 10K) | Tepe | x86 | Mainframe (en iyi strateji, TFP) |
|---|---|---|---|
| steady_oltp | 15.000 | $8,53M (2×16c) | $17,23M |
| retail_bursty | 35.000 | $15,36M (2×32c) | $29,28M |
| batch_heavy | 25.000 | $12,15M (2×24c) | $23,51M |

Mainframe'in CoD/TFP avantajı (dalgalı yükte düşük ortalama fatura) burada görünür: retail_bursty'de x86 maliyeti 10K statik maliyetin 2,4 katıdır, mainframe'inki 2,1 katı. Ama x86'nın personel hariç maliyeti o kadar küçüktür ki bu avantaj sıralamayı değiştirmez. retail_bursty'de 35K'lık tepe Patroni tavanına çok yakındır; biraz daha dalgalı bir profil x86'yı Oracle RAC'a iter.

---

## 16. Mainframe ile Karşılaştırma (KB-13, KB-18)

### 16.1. Çıktılar

`compare()` aynı girdiyle iki modeli çözer ve şunları verir: iki toplam, oran, personel hariç toplamlar, 1,25 ve 2,0 personel oranlarında x86, konsolide edilmemiş park senaryosu, üretim dışı stres senaryosu ve başabaş personel oranı. Başabaş oranı ikiye bölmeyle bulunur. Her adımda x86 yığını yeniden optimize edilir, yani bir orana göre yalnızca personel kalemi ölçeklenmez. Test: `test_staff_neutral_and_breakeven`.

### 16.2. Mid sonuçlar

| Availability | TPS | Mainframe $/TPS | x86 $/TPS | Başabaş oranı | Personel hariç (MF / x86) | x86, oran 1,25 | x86, oran 2,0 |
|---|---|---|---|---|---|---|---|
| %99,9 | 1.000 | 299,85 (M1, 407) | 126,94 (PG X1) | 2,54 | 187,87 / 14,96 | 154,93 | 238,92 |
| %99,9 | 10.000 | 117,92 (M1, 524) | 57,65 (PG X1) | 2,07 | 61,80 / 1,52 | 71,68 | 113,77 |
| %99,9 | 50.000 | 71,35 (M1, 759) | 37,71 (Oracle X1, k = 7) | 1,97 | 36,72 / 3,08 | 46,37 | 72,35 |
| %99,9 | 100.000 | 61,59 (M1, 7E1) | 31,03 (Oracle X1, k = 7) | 2,09 | 33,46 / 2,90 | 38,06 | 59,15 |
| %99,99 | 10.000 | 126,48 (M2) | 61,92 (PG X2) | 2,10 | 67,55 / 2,99 | 76,66 | 120,85 |
| %99,99 | 50.000 | 77,62 (M2) | 41,16 (Oracle X2) | 2,00 | 41,26 / 4,80 | 50,25 | 77,52 |
| %99,999 | 1.000 | 400,12 (M3) | 235,97 (Oracle X4, k = 2) | 2,17 | 271,34 / 95,99 | 270,96 | 375,94 |
| %99,999 | 10.000 | 138,35 (M3) | 79,77 (Oracle X4, k = 2) | 1,84 | 73,80 / 9,61 | 97,31 | 149,92 |
| %99,999 | 50.000 | 82,34 (M3) | 49,62 (Oracle X4, k = 5) | 1,76 | 42,51 / 6,33 | 60,44 | 92,91 |
| %99,999 + RPO 0 | her TPS | M3 | infeasible | — | — | — | — |

Değerlendirme #10 sonrası (M3 eşitliği, platform terimi, destek kuralı, personel girdisinde zIIP).

**Okuma.**

1. **Mid'de x86 kurulabildiği bütün noktalarda ucuzdur ve başabaş personel oranı 1,8–2,6 arasındadır.** IBM'in konsolide/sanallaştırılmış vakaları (~1,25) bu eşiğin altında, bütün FTE vakalarının geometrik ortalaması (2,0) eşiğin hemen altındadır. Yani mid varsayımlarla mainframe'in kazanması için x86 personelinin, IBM'in kendi vakalarındaki dağınık parklar kadar (≥ 2) kalabalık olması gerekir.
2. **Personel hariç fark 8–42 kattır** (PostgreSQL bölgesinde 13–42, Oracle bölgesinde 8–12). Kaynağı neredeyse bütünüyle yazılım lisans modelidir: mainframe 10K TPS'te AWLC $402.932 + üretim dışı ortamlar $102.054 öderken PostgreSQL yığını abonelikler için $5.210 öder. Bu, araştırmanın en büyük yapısal bulgusudur ve tezde personelden ayrı yazılmalıdır.
3. **%99,999'da x86 Oracle Platinum'a (X4) zorlanır ve fark daralır** (başabaş 1,76–2,17). Platform terimiyle X3 (PG ya da Oracle Gold) beş dokuzu tutturamaz; X4 GoldenGate ile RPO 5 sn verir. RPO 0 da istenirse x86 kurulamaz ve yalnızca mainframe M3 kalır (§16.5).

### 16.3. Eşleştirilmiş senaryolar (`--compare --range`)

İki platformun kendi aralık köşelerini birlikte okumak (mainframe low ile x86 high) ortak parametreleri iki tarafta çelişik değerlere koyardı: personel eğrisi bir tarafta low, öbür tarafta high olurdu. Bu, P kararıyla bağdaşmaz. Eşleştirilmiş senaryolarda platforma özgü parametreler zıt uçlara çekilir, ortak parametreler (ortak modülün sahip olduğu adlar) iki tarafta aynı değerde kalır:

| Senaryo | Tanım |
|---|---|
| x86_lehine | x86'ya özgü low, mainframe'e özgü high, ortak mid |
| orta | hepsi mid |
| mainframe_lehine | x86'ya özgü high, mainframe'e özgü low, ortak mid |
| ortak_low / ortak_high | ortak parametreler low / high (iki taraf birlikte), özgü mid |

**Köprü ağırlıkları referans tabanda.** Personel eğrisinin girdisi (PCI eşdeğeri) ve x86 uygulama katmanının işlem yöneticisi payı mainframe CPU ağırlıklarını (CPU_US_PER_SQL_READ / _WRITE, zIIP payı) okur. Eşleştirilmiş senaryolarda bu ağırlıklar mainframe'e özgü sayılır. Bu iki köprüde de mid değerlerinde tutulmazlarsa mainframe'in "high" CPU maliyeti iki taraftaki personeli birlikte büyütür. O zaman "x86 lehine" senaryoda x86 pahalanırdı. İlk koşuda tam olarak bu görüldü: x86 $53,66'dan $89,49'a çıktı. Bu yüzden `CROSS_BRIDGE_WEIGHTS` = "reference" anahtarı eşleştirilmiş senaryolarda iki köprüyü mid ağırlıklarla hesaplar. Tek platform çalışmaları ve kendi aralıkları P ve C kurallarını değiştirmeden kullanır. Test: `test_paired_comparison_scenarios`.

Sonuçlar (%99,9; $/TPS/ay; BE = başabaş personel oranı; PH = personel hariç oran MF/x86):

| TPS | x86_lehine MF / x86 (BE) | orta (BE) | mainframe_lehine MF / x86 (BE, PH) | ortak_low (BE) | ortak_high (BE) |
|---|---|---|---|---|---|
| 1.000 | 752,95 / 119,98 (6,65) | 299,85 / 126,94 (2,54) | 174,10 / 144,63 (1,26; 1,9) | 241,42 / 70,93 (4,00) | 396,70 / 221,10 (1,86) |
| 5.000 | 439,65 / 70,71 (6,34) | 154,23 / 72,11 (2,19) | 94,55 / 76,91 (1,26; 3,3) | 113,39 / 32,69 (3,70) | 235,43 / 151,82 (1,56) |
| 10.000 | 387,27 / 56,94 (6,89) | 117,92 / 57,65 (2,07) | 74,48 / 61,91 (1,22; 3,2) | 83,25 / 24,05 (3,61) | 192,23 / 130,99 (1,47) |
| 30.000 | 349,01 / 40,65 (8,64) | 81,18 / 41,28 (1,99) | **50,85 / 58,99 (0,80; 0,6)** | 54,52 / 15,44 (3,68) | 145,53 / 104,79 (1,39) |
| 50.000 | 338,31 / 34,83 (9,76) | 71,35 / 37,71 (1,97) | **43,06 / 53,44 (0,70; 0,4)** | 47,67 / 14,95 (3,75) | 131,34 / 96,84 (1,37) |
| 100.000 | MF infeasible | 61,59 / 31,03 (2,09) | x86 infeasible | 41,57 / 11,89 (4,29) | 115,90 / 84,54 (1,38) |

**Okuma (crossover bölgesi).**

1. **Mainframe lehine senaryoda crossover vardır ve Patroni tavanına bağlıdır.** 10K TPS'te mainframe lehine bütün özgü belirsizlikler bile x86'yı ancak 1,22'lik personel oranıyla mainframe'e eşitler. 30K ve 50K'da ise mainframe personel nötrken de ucuzdur (BE < 1). Neden: x86'nın high köşesinde (köprü 60, tavan 0,50, sanallaştırma high) Patroni tavanı ~15K TPS'e iner. Bunun üstünde Oracle RAC zorunlu olur ve Oracle'ın high köşesi (indirim 0,20, verim 0,80, RAC verimi 0,80) lisans maliyetini personel hariç mainframe'in üstüne çıkarır.
2. **Ortak parametreler oranı değiştirir ama yönü değiştirmez.** Ortak low'da (personel ucuz) x86'nın üstünlüğü büyür (BE 3,8–4,5). Ortak high'da (personel pahalı) küçülür (BE 1,4–1,9). Personel nötr olduğu için personel ne kadar pahalıysa personel hariç farkın oranı o kadar sulanır.
3. **Tezin başlık cümlesi:** "Mid varsayımlarla ve nötr personelle kümelenmiş x86 bütün hacimlerde ~2 kat ucuzdur; mainframe'in kazandığı bölge (a) x86 personelinin mainframe personelinin ~2 katını aşması ya da (b) bütün platforma özgü belirsizliklerin mainframe lehine çözülmesi ve yükün ~15–36K TPS'lik Patroni tavanını aşmasıdır."

### 16.4. Uzlaştırma senaryoları (ana aralıkta değil)

(Bu alt bölümdeki rakamlar Değerlendirme #10 öncesine aittir; yön ve sonuç değişmedi.)

- **Konsolide edilmemiş park** (`X86_UNCONSOLIDATED_CEILING` = 0,175; [SHEDLETSKY-2008] ve `benzer_calismalar_v1` B1'deki %15–20 dağıtık kullanım). IBM'in U_R iddiasıyla uzlaştırma içindir. 10K TPS'te x86 $65,19/TPS'e çıkar ve Oracle RAC'a (2×12c, k = 4) geçer, çünkü Patroni düğümü bu kullanımda yükü taşıyamaz. Personel hariç $130.536'dır, mainframe'in $617.961'inin hâlâ beşte biri. 50K'da $44,99; 100K'da infeasible. Yani IBM'in kullanım oranı etkisi bile tek başına sıralamayı çevirmez; çeviren personel oranıdır.
- **Üretim dışı stres** (`NONPROD_FACTOR_X86` = 2,0; IBM'in "dağıtıkta +%200" iddiası): 10K TPS'te $54,69 (+%1,9). x86'nın üretim dışı tabanı küçük olduğu için etkisi de küçüktür.

---

### 16.5. Kim nerede kazanıyor (Değerlendirme #10)

`python src/tools/kazanan_haritasi.py` TPS × availability/RPO hedefi × eşleştirilmiş senaryo ızgarasını çözer ve `data/out/kazanan_haritasi.csv` yazar. Orta senaryo, personel oranı 1,0 (hücre: kazanan, MF/x86 oranı / başabaş personel oranı):

| Hedef | 1K | 10K | 50K | 100K |
|---|---|---|---|---|
| %99,9 | x86 2,36 / 2,54 | x86 2,05 / 2,07 | x86 1,89 / 1,97 | x86 1,99 / 2,09 |
| %99,99 + RPO 0 | x86 2,11 / 2,33 | x86 1,93 / 2,04 | x86 1,89 / 2,00 | x86 1,98 / 2,13 |
| %99,995 + RPO 0 | x86 2,59 / 2,91 | x86 2,06 / 2,10 | x86 1,81 / 1,92 | x86 1,87 / 2,02 |
| %99,999 | x86 1,70 / 2,17 | x86 1,73 / 1,84 | x86 1,66 / 1,76 | x86 1,72 / 1,84 |
| %99,999 + RPO 0 | yalnız MF | yalnız MF | yalnız MF | yalnız MF |
| %99,9995 | yalnız MF | yalnız MF | yalnız MF | yalnız MF |

**u hassasiyeti (10K TPS, %99,999 + RPO 0):** u = 0 ve 0,05'te x86 X3 ile kurulur (0,05'te Oracle Gold, ayda ~$737K); u = 0,10 ve 0,20'de kurulamaz. "Beş dokuz + RPO 0'da yalnız mainframe" sonucu bu yüzden koşulludur ve tezde u aralığıyla birlikte raporlanmalıdır.

**Neden ana senaryoda x86 kazanıyor:** başabaş oranı = 1 + (MF personel dışı − x86 personel dışı) / personel. x86'nın personel dışı maliyeti 10K TPS'te $15K, mainframe'inki $618K; personel $561K olduğundan oran 2,07'dir ve TPS ile pek değişmez. Ayrıntı: mainframe v3 §7.12.

## 17. Köprülerden Sapmalar ve Düzeltmeler

Kodlama sırasında köprüler dokümanının dört noktası x86'nın çalışma biçimine ya da kaynağa uymadı. Hepsi kodda düzeltildi ve burada gerekçesiyle kaydedildi. `kopruler_v1.md` güncel bir sürümle (v2) bu düzeltmeleri almalıdır.

| # | Köprü | Kopruler v1'de | Modelde | Gerekçe |
|---|---|---|---|---|
| 1 | KB-08 | X2 RPO 0 (iki DB) | X2-PG RPO 5 sn [ASSUME]; Oracle 0 | Patroni'nin iki DC önerisi asenkron standby kümedir [PATRONI-MULTIDC] (Bölüm 8.2) |
| 2 | KB-11 | `OCP_USD_PER_SOCKETPAIR_YEAR` 6K / 11K / 15K | `OCP_USD_PER_COREPAIR_YEAR` 2.000 / 3.000 / 4.200 | Sanal düğümler çekirdek tabanlı abonelik ister [RH-OCP-GUIDE] (Bölüm 9.3) |
| 3 | KB-15 | Bileşen fonksiyonu Dell fiyatına ±%20 | Kontrol yapılamadı; yalnızca dönem bandı | Kaynak yapılandırmayı vermiyor (Bölüm 4.3) |
| 4 | KB-06 | B_X86 low 1,00 / high 0,80 | Yön tutarlı düzey anahtarı (`X86_SCALING_LEVEL`) | n < 48'de köşelerin yönü tersine dönüyordu (Bölüm 5.3) |

Ayrıca iki ek kural kodlandı. Köprüler dokümanında yoktular:

- Eşleştirilmiş karşılaştırma senaryoları ve `CROSS_BRIDGE_WEIGHTS` (Bölüm 16.3).
- NPV'de yığın seçiminin bütün yolu taşıyabilen adaylar arasından yapılması (Bölüm 15.1).

---

## 18. Geçerlilik Tehditleri ve Sınırlamalar

| # | Tehdit | Etki | Durum |
|---|---|---|---|
| 1 | Kapasite çapası tek, belgelenmemiş ayarlara dayanan bir ölçüm (Vonng) | Köprü 60–120 aralığında; Oracle bölgesinde lisanslı çekirdek sayısını değiştirir | K6 ölçümüyle kapanacak |
| 2 | Oracle verimi kalibre edilemez (OTN yasağı) | Oracle bölgesinde (> ~36K TPS) maliyet geniş aralıkta | Yapısal veri sınırı; tornado'da görünür |
| 3 | RAC ölçeklenmesi sabit marjinal verimli (k'ye doğrusal) | Çok sayıda küçük RAC düğümü seçiliyor; `RAC_MAX_NODES` = 4 ile 50K'da personel hariç +%10, 130K infeasible | Kaynak aranmalı (USL formu) |
| 4 | Personel nötr (P kararı); bağımsız platformlar arası personel verisi yok | Başlık sonucu personel oranına koşullu | Başabaş oranı başlık çıktısı |
| 5 | Yazılım lisans farkı (AWLC vs açık kaynak) personel hariç farkın neredeyse tamamı | Sonuç AWLC fiyat düzeyine duyarlı (mainframe tarafında `SW_PRICE_LEVEL_FACTOR`) | Mainframe aralığında taşınıyor |
| 6 | Sunucu fiyatı kaba ([ASSUME] platform maliyeti, indirim); KB-15 kalibrasyonu yapılamadı | Donanım personel hariç maliyetin küçük payı; etkisi sınırlı | Yapılandırması belli kamu ihale kaydı aranmalı |
| 7 | Patroni X2'nin RPO'su (5 sn) ve WAL fsync süresi (60 µs) varsayım | RPO 0 isteyen PG kurulumu X3'e gidiyor | K6'da senkron replikalı koşu (protokol şartı 6) |
| 8 | OpenShift Virtualization üzerinde Oracle'ın sertifikası doğrulanmadı | 200K TPS'te seçilen yığın OCP-V / Oracle | Doğrulanmalı; değilse vSphere / Oracle (+%1–2) |
| 9 | RAC'ın konteynerde çalıştırılması dışarıda | Oracle yalnızca VM'de | Bilinçli kapsam |
| 10 | Uygulama katmanı yalnızca CPU payıyla boyutlanıyor (bellek, oturum sayısı yok) | Maliyetin %0,3'ü | Küçük |
| 11 | Yerel NVMe'de düğüm içi RAID yok (replika kopyası yeterli sayıldı) | Storage alt uçta | [ASSUME] |
| 12 | Mainframe tavanı ~133K TPS, Patroni ~36K, RAC ~231K; Parallel Sysplex ve Citus modellenmedi | Yüksek hacim bölgesi aralık olarak verilmeli | İki taraf aynı statüde sınırlama |
| 13 | Yedekte x86 sıkıştırma (2,0) var, mainframe nesne depolama hedefinde yok | x86 yedek maliyeti biraz düşük | Küçük; platform özelliği |
| 14 | Fiyat dönemi: IBM fiyatlarının 2026 şokuna tepkisi bilinmiyor | 2026-Q3 senaryosunda yalnızca x86 değişiyor | Sınırlama olarak yazılır |
| 15 | Çapa (Cascade Lake, 5,94 SPECint/çekirdek) ile R760 SKU'ları (~9,8) arasındaki ~1,65 katlık çekirdek başına SPECrate artışının bir kısmı bellek bant genişliğinden (DDR4 6 kanal → DDR5 8 kanal) ve derleyici sürümünden gelir. OLTP'nin bu artıştan aynı oranda yararlandığı bir varsayımdır (Değ. #8 §3.1) | Köprü SPECint ile doğrusal taşındığı için hedef SKU'da TPS/çekirdek fazla olabilir; düşük köprü ucu (60) bunu kısmen kapsar | K6 ölçümünün hedef nesilde yapılmasıyla kapanır (Karar K) |

---

## 19. Testler

`python src/test_x86_model.py` — 29 test (yalnızca standart kütüphane):

- **Köprü ve iş yükü:** çapa 91 ± 0,5, R760 893 ± 2, KB-04 oranı 1,52–1,60, S(64) < 1 < S(16); oltp_rw 20 ifade ve ağırlık 1, ağır profil > 1 > TPC-B, redp_light reddedilir, `RANGE_READ_WEIGHT` ortak; ölçeklenme köşelerinin yön tutarlılığı; sanallaştırma ve konteyner ek yükü sırası, 8 yığın.
- **Tavan ve latency:** ρ ≤ tavan; sıkı hedef asla daha ucuz değil; sabit gecikmenin altı infeasible; tavan yükseldikçe maliyet artmıyor; saklı yordam ağ terimini 1 gidiş-dönüşe indiriyor; uzak senkron kopya gecikme ekliyor.
- **Ölçekleme:** Patroni yalnızca birincil; 40K TPS ana katalogda PG için infeasible, ekstrapolasyonla feasible; 60K'da Oracle; RAC formülü ve N+1; maliyet TPS ile azalmıyor.
- **Topoloji:** X4-PG infeasible; X2-PG RPO > 0; RPO 0 → PG X3; X1 < X2 < X3; X4 > X3 (Oracle); saha olayı kötüleşince availability düşüyor; aralık mid'i içeriyor; X2 elle geçiş; kesen düğüm sayısı; yüksek hedef daha pahalı.
- **Lisans:** Oracle işlemci ve seçenek kuralları, ADG/GoldenGate; vSphere 16/CPU ve 72/sipariş asgarileri; OpenShift çekirdek çifti ve RHEL dahil; OVE düğüm başına; DR sitesi tam lisanslı.
- **Uygulama katmanı, storage, yedek:** TM payı %7–9, N+1; NVMe kopya sayısı, 900 TB'ta PG infeasible ve Oracle'a geçiş, birincil dizide rezerv, fiyat sözleşmesi; WAL çarpanı, iki hedef, X1 geri yükleme kısıtı, yedek akışı yetmezse infeasible.
- **Personel ve karşılaştırma:** oran 1'de mainframe ile aynı FTE; başabaş oranında toplamlar eşit (< %0,1); 2,0 > 1,25 > ana; uzlaştırma senaryoları ≥ ana; eşleştirilmiş senaryoların yönü ve köprü ağırlıklarının ayrışması.
- **Üretim dışı, fiyat dönemi, aralık, NPV, yıllık:** doğrusal ve personel/yedeği etkilemiyor; 2026-Q3 pahalı; low ≤ mid ≤ high (statik ve NPV); tornado; NPV = 60 × statik (iki DB, X1/X3); iskonto yönü; yalnızca yükselen düğüm; yıllık = 12 × tepe.
- **Ortak modül ve CLI:** ortak adların tek sahibi; fiyat dosyası modu; CLI bayrakları.
- **Değerlendirme #10:** M3 ile X3 kurtarma ve planlı kesinti aralıkları aynı; ortak platform kesintisi formülü (tek CPC'de u'dan bağımsız, u artınca kümede availability düşer, aktif-aktifte u²); SLA'ya bağlı destek tabanı ve desteksiz yığının availability cezası; personel girdisi zIIP payından bağımsız; %99,999 + RPO 0'da yalnızca mainframe, RPO serbestken x86 Oracle X4.

Mainframe testleri (30) F ve P ile birlikte geçer; altın sonuç kümesi eski kurallarla (RANGE_READ_WEIGHT = 1, personel kurulu kademeden, NONPROD = 0) birebir yeniden üretilir.

---

## 20. Kaynaklar

Kaynakların tamamı ve modeldeki yerleri `acik_sistem_arastirma_plani_v1.md` §15 ile `kopruler_v1.md`'dedir. Bu modelde doğrudan kullanılanlar:

**Kapasite ve ölçekleme**
- [VONNG-PERF] Feng Ruohang (Vonng), "How Powerful is PostgreSQL Really?" — http://blog.vonng.com/en/pg/pg-performence/
- [SPEC-8270] SPEC CPU2017, Dell M640, Xeon Platinum 8270 — https://spec.org/cpu2017/results/res2019q3/cpu2017-20190708-15958.html
- [SPEC-R760] SPEC CPU2017, Dell R760, Xeon Gold 6548Y+ — https://open.spec.org/cpu2017/results/res2024q2/cpu2017-20240422-43001.html
- [SPEC-DL380G12] SPEC CPU2017, HPE DL380 Gen12 — https://open.spec.org/cpu2017/results/res2025q1/cpu2017-20250210-46265.html
- [INTEL-ARK-6548Y] Intel Xeon Gold 6548Y+ — https://www.intel.com/content/www/us/en/products/sku/237564/intel-xeon-gold-6548y-processor-60m-cache-2-50-ghz/specifications.html
- [REDHAT-OCPV-2025] [VENDOR] — https://developers.redhat.com/blog/2025/02/25/scalable-database-performance-openshift-virtualization-out-box
- [PT-VSPHERE-OCPV-2024] [VENDOR] — https://blogs.vmware.com/cloud-foundation/2024/12/03/vmware-vsphere-8-supports-1-5-times-more-vms-and-delivers-62-more-data-transactions-than-red-hat-openshift-virtualization/
- [EDB-LOCALPV] — https://www.enterprisedb.com/index.php/blog/local-persistent-volumes-and-postgresql-usage-kubernetes
- [ORACLE-OTN] — https://www.oracle.com/downloads/licenses/standard-license.html
- [ORACLE-RAC-2024] [VENDOR] — https://oracle.com/a/otn/docs/database/the-new-generation-oracle-rac.pdf
- [PGCON-2016] — https://www.pgcon.org/2016/schedule/attachments/399_postgresql-96-scalability-perf-improvements.pdf

**Availability ve topoloji**
- [ITIC-2023] ITIC 2023 Global Server Hardware, Server OS Reliability (IT Jungle özeti): sunucu başına yıllık plansız kesinti, Lenovo ThinkSystem Linux 31,5 sn, Dell PowerEdge Linux 24 dk, HPE ProLiant Linux 39 dk, white box Linux 59 dk; z16 31,56 ms. Kendi seçilen katılımcılarla web anketi. — https://itic-corp.com/?p=3107 · https://itjungle.com/2024/10/21/ibm-nears-the-end-of-the-road-for-server-reliability-improvements
- [YUAN-2014] D. Yuan vd., "Simple Testing Can Prevent Most Critical Failures", OSDI 2014 (katastrofik hataların %92'si hata işleme yolunda).
- [GUNAWI-2016] H. S. Gunawi vd., "Why Does the Cloud Stop Computing? Lessons from Hundreds of Service Outages", SoCC 2016.
- [UPTIME-2025] Uptime Institute Annual Outage Analysis 2025: BT ve ağ kaynaklı kesintiler etkili kesintilerin %23'ü; büyük BT/yazılım kesintilerinin %62'sinde konfigürasyon / değişiklik yönetimi (Network World özeti). — https://www.businesswire.com/news/home/20250506733553/en/Uptime-Announces-Annual-Outage-Analysis-Report-2025 · https://www.networkworld.com/article/3980366/networking-errors-pose-threat-to-data-center-reliability.html
- [EDB-STORE-2026] EDB mağazası: Community $400, Business $1.600, Enterprise $2.400 / çekirdek / yıl; 8 çekirdek alt sınır, 1 yıl. — https://enterprisedb.com/store
- [EDB-PLANS-2026] EDB plan karşılaştırması: Basic 10x5 (geliştirme/test), Production 7/24, Premium 7/24 + sıkı SLO. — https://enterprisedb.com/products/plans-comparison
- [PATRONI-REPL] — https://patroni.readthedocs.io/en/latest/replication_modes.html
- [PATRONI-MULTIDC] Patroni, "Multi DC HA" — https://patroni.readthedocs.io/en/latest/ha_multi_dc.html · "Asynchronous Replication" başlığı; "With only two data centers it would be better to have two independent etcd clusters and run Patroni standby cluster in the second data center."; "To have a multi DC cluster that can automatically tolerate a zone drop, a minimum of 3 is required."
- [PIGSTY-RTO] — https://doc.pigsty.io/docs/concept/ha/rto/
- [ORACLE-MAA-2026] [VENDOR] — https://oracle.com/a/tech/docs/maa-onpremises-overview.pdf
- [VISHWANATH-2010] ACM SoCC 2010 — https://www.microsoft.com/en-us/research/wp-content/uploads/2010/06/socc088-vishwanath.pdf
- [EDB-SYNCREP] — https://enterprisedb.com/blog/the-varying-cost-synchronous-replication

**Donanım ve fiyat**
- [SPECPOWER-2025Q1] — https://spec.cs.miami.edu/power_ssj2008/results/res2025q1
- [PCSP-SERVER] [satıcı] — https://pcserverandparts.com/news/how-much-does-a-server-cost-2026/
- [PCSP-SSD] [satıcı] — https://pcserverandparts.com/news/enterprise-ssd-prices-2026-server-storage-buying-guide/
- [CAPCOMP-RAM] — https://capitalandcompute.net/memory-prices/server/
- [BACLOUD-RAM] — https://www.bacloud.com/en/blog/307/when-will-ram-prices-drop-still-no-good-news--august-2026-update.html
- [VENDORBENCH-AFA] — https://vendorbenchmark.com/blog/enterprise-storage-per-tb-pricing-benchmark
- [STORAGEREVIEW-P5520] [VENDOR sponsorlu] — https://storagereview.com/wp-content/uploads/2022/07/solidigm-d7-p5520-1.pdf

**Yazılım**
- [ACEMQ-VVF] [iş ortağı] — https://acemq.com/blogs/vmware-cloud-foundation-vs-vsphere-foundation/
- [ACEMQ-RENEW] [iş ortağı] — https://acemq.com/research/state-of-vmware-renewals-2026/
- [CDW-OVE] — https://www.cdw.com/product/red-hat-openshift-virtualization-engine-premium-subscription-1-year-1/8238645
- [CCSP-RH] — https://www.cloudingenuity.com/contracts/5272/5272_Red_Hat.pdf
- [RH-OCP-GUIDE] Red Hat, "Self-managed Red Hat OpenShift subscription guide" (2024-10) — https://redhat.com/rhdc/managed-files/cl-self-managed-openshift-subscription-guide-1434155pr-202410-en.pdf · "Each physical, bare-metal server using socket-based entitlements can only be used as a single OpenShift node."; "entitling the virtual compute nodes using core-based subscriptions."
- [SWEXPRESS-OCP] software-express.de, Red Hat fiyat listesi — https://www.software-express.de/preislisten/red-hat/red-hat-21746/ · "Red Hat OpenShift Container Platform; Premium (2 Cores or 4 vCPUs); Subscription; 1 Jahr" 3.872,00 € (KDV hariç) [bayi]
- [VENDORBENCH-OCP] — https://vendorbenchmark.com/vendors/red-hat-openshift-pricing
- [REDRESS-PL2026] [danışman] — https://redresscompliance.com/oracle-price-list-2026-key-changes-and-analysis.html
- [REDRESS-GG] [danışman] Redress Compliance, "Oracle GoldenGate licensing guide" — https://redresscompliance.com/oracle-goldengate-licensing-guide · "GoldenGate costs $17,500 per processor on every server that runs it, source and target alike"; "A GoldenGate license includes Oracle Active Data Guard and Oracle XStream, with Database Enterprise Edition as the prerequisite."
- [ORACLE-PL2009] — https://public.dhe.ibm.com/software/websphere/oracle/technology-price-list.pdf
- [ORACLE-CORE] — https://www.oracle.com/contracts/docs/processor-core-factor-table-070634.pdf
- [ORACLE-PART] — https://oracle.com/a/ocom/docs/it-infrastructure/partitioning-070609.pdf
- [OLE-NET2026] [danışman] — https://oraclelicensingexperts.com/blog/oracle-database-net-price-benchmarks-2026/

**Personel ve üretim dışı** (KB-13, KB-14)
- [IBM-EAGLE], [GARTNER-ITKMD], [IBM-TPF-2007], [IBM-EAGLE-LABOR], [SHEDLETSKY-2008], [IBM-EAGLE-2013] — tam künyeler `kopruler_v1.md` KB-13 / KB-14 ve mainframe v3 §7.7'de.

---

## 21. Çalıştırma

```
cd src
python x86_model.py --tps 10000                       # statik
python x86_model.py --tps 10000 --compare             # mainframe ile karşılaştırma, başabaş personel oranı
python x86_model.py --tps 10000 --compare --range     # + aralık, tornado, eşleştirilmiş senaryolar
python x86_model.py --tps 10000 --npv --range         # 5 yıllık NPV ve aralığı
python x86_model.py --yearly --preset retail_bursty --avg-tps 10000
python x86_model.py --tps 50000 --db oracle --availability 0.99999
python x86_model.py --tps 10000 --price-epoch 2026-Q3 --allow-extrapolation
python x86_model.py --calibration                     # köprü, KB-04 ve KB-15 kontrolleri
python test_x86_model.py
```
