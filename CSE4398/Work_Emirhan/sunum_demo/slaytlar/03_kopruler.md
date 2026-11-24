# Slayt İçeriği — Bölüm 3: Köprüler (KB-01 – KB-18)

*18 köprü × 2 slayt. Bir köprü, iki platformun aynı girdiyle beslendiği, aynı ölçüyle ölçüldüğü ya da aynı kuralla fiyatlandığı arayüzdür. Her köprünün ilk slaytı **kullanılan veriyi** (kaynaktaki değerlerin kendisiyle) ve **türetmeyi** adım adım verir; ikinci slaytı **küçük bir örnek hesap** (somut girdi → modelin sonucu) ile kararı ve açık kalanı verir. Sayılar `main` dalındaki modellerin 2026-11-24 koşusundan (Değerlendirme #10 sonrası); örnek hesaplar modelin kendi fonksiyonlarıyla yeniden üretildi. Kaynak anahtarları `kaynaklar/KAYNAKCA.md`'dedir. Ayrıntı: `docs/kopruler_v1.md`; kodlamadaki dört düzeltme `docs/x86_model_dokumantasyonu_v1.md` §17.*

**Açılış slaytı önerisi (Slayt K0 — Köprü haritası):** 18 köprü dört grupta toplanır. **Ölçü:** KB-01 işlem birimi, KB-02/03 kapasite köprüleri, KB-04 kontrol, KB-05 kullanım ve latency, KB-06 tavanlar. **Dayanıklılık:** KB-07 availability, KB-08 topoloji, KB-09 storage, KB-10 yedek. **Maliyet:** KB-11 lisans, KB-12 kapsam sınırı, KB-13 personel, KB-14 üretim dışı, KB-15 fiyat dönemi, KB-17 enerji. **Zaman ve belirsizlik:** KB-16 NPV, KB-18 aralık. *Konuşmacı notu:* "Köprü yoksa iki model iki ayrı dünyayı ölçer; köprüler bu tezin metodolojik katkısı."

**Bütün örneklerin ortak girdisi (referans nokta, Demo Case 1):** 10.000 TPS, oltp_rw, %99,9, 20 TB veri, yılda %15 büyüme, fiyat dönemi 2025-mid, personel oranı 1,0. Sonuç: mainframe M1 3931-524 **$117,92/TPS/ay**, x86 X1 vSphere/VM/PostgreSQL+Patroni 3 × 2×8c **$57,65/TPS/ay**.

---

### Slayt KB-01.1 — İşlem birimi: "1 işlem" iki tarafta aynı SQL listesi

**Kullanılan veri**

| Profil | Nokta okuma | Aralık okuma | Yazma | Commit | Kaynak |
|---|---|---|---|---|---|
| tpcb_like | 1 | 0 | 4 | 1 | [TPC1994-TPCB] |
| **oltp_rw** (ana) | **10** | **4** | **4** | **1** | sysbench `oltp_read_write` [Kopytov-sysbench] |
| oltp_heavy | 30 | 0 | 6 | 1 | ~1,3 ms Db2 CPU'luk saha işlemi [Catterall2019] |

Mainframe SQL CPU maliyetleri (z13 ölçeğinde µs): CICS işlem tabanı **85,9 µs** (REDP-5320: CICS CPU %1.499,4 bir CP / 174.624 TPS) [Burgess2016-REDP5320]; okuma SQL **30 µs**; yazma SQL **70 µs** (CICS programında tek INSERT ~68 µs [Catterall2012]).

**Türetme**

```
Mainframe:  CPU(µs) = 85,9 + (nokta + aralık × RANGE_READ_WEIGHT) × 30 + yazma × 70
            w       = CPU / 85,9          (REDP işleminin kaç katı)
x86:        birim   = nokta + aralık × 3,65 + yazma × 3,9 + (commit + BEGIN) × 1,0
            göreli ağırlık = birim(profil) / birim(oltp_rw)
```

`RANGE_READ_WEIGHT` = 3,65 (3,4 / 3,65 / 3,9) iki tarafta **tek ortak parametre**dir.

**Veri / kaynak:** [Kopytov-sysbench], [Tencent-PG-TestMethods] (bileşim), [Burgess2016-REDP5320], [Catterall2012], [Catterall2019]; `common_model.WORKLOAD_MIXES`.

**Tasarım gerekçesi:** Crossover "TPS başına maliyet" üzerinden kurulduğu için birim eşitliği bütün sonuçların ön koşulu. x86'da en yaygın ölçülen bileşimi seçmek, x86 tarafının kendi ölçümüyle karşılanabilmesini sağlar.

**Konuşmacı notu:** "Bu köprü olmasaydı bütün sonuçlar boş olurdu. İki taraf için 'işlem' kelimesini aynı SQL listesiyle tanımladık."

---

### Slayt KB-01.2 — KB-01: örnek hesap, kanıt, karar

**Örnek (oltp_rw):**

```
Mainframe: CPU = 85,9 + (10 + 4 × 3,65) × 30 + 4 × 70 = 85,9 + 738 + 280 = 1.103,9 µs
           w   = 1.103,9 / 85,9 = 12,85
x86:       birim = 10 + 4 × 3,65 + 4 × 3,9 + 2 × 1,0 = 42,2 nokta sorgusu  → göreli ağırlık 1,00
```

| Profil | Mainframe CPU | w | x86 birim | x86 göreli ağırlık |
|---|---|---|---|---|
| tpcb_like | 395,9 µs | 4,61 | 18,6 | 0,44 |
| oltp_rw | 1.103,9 µs | 12,85 | 42,2 | 1,00 |
| oltp_heavy | 1.405,9 µs | 16,37 | 55,4 | 1,31 |

**Oranın kanıtı (Vonng alt testleri, AWS c5d.metal 48 çekirdek)** [Vonng-PGPerf]: point_select 1.372.654 QPS → **0,73 µs**/işlem; read_only 852.440 QPS / 16 sorgu = 53.278 TPS → **18,77 µs**; write_only 495.942 / 6 = 82.657 TPS → 12,10 µs. Aralık/nokta = (18,77 − 10 × 0,73 − 2b) / 4 / 0,73 = **3,44** (b = 0,73) … **3,94** (b = 0).

- **Karar F (b), Emirhan, 2026-11-16:** aralık okumaları nokta okumadan ayrılır. Etki: w 9,15 → 12,85; 10K TPS kademe 3931-516 → 524; mainframe $/TPS +%23 (F mainframe lehine bir yanlılığı düzeltti).
- Açık kalan: K6'da oranın ölçülmesi; Db2'ye özgü aralık sorgusu maliyeti için IBM kaynağı (IRWW).

**Tasarım gerekçesi:** PostgreSQL'deki göreli maliyetin Db2'ye taşınması bir varsayım; açıkça yazıldı ve ortak parametre olarak aralıkta taşınıyor.

**Konuşmacı notu:** "Aynı 10K TPS, iş tanımı tpcb_like'tan oltp_heavy'ye değişince mainframe'de CPU 3,5 kat, x86'da 3 kat artıyor. Bu karar mainframe'i pahalılaştırdı; kendi modelimizin lehine olan bir yanlılığı bulup düzelttik."

---

### Slayt KB-02.1 — Mainframe kapasite köprüsü: PCI başına TPS

**Kullanılan veri**

| Kaynak | Satır | Değer |
|---|---|---|
| REDP-5320 benchmark [Burgess2016-REDP5320] | z13 2964-718 (18 CP) | 174.000 TPS |
| | z13 2964-726 (26 CP) | 227.000 TPS |
| LSPR z/OS 2.2 [IBM-LSPR-zOS22] | 2964-718 | 21.579 PCI, 2.584 MSU |
| | 2964-726 | 29.048 PCI, 3.414 MSU |
| LSPR ITRR, z16 3931 [IBM-LSPR-ITRR] | 3931-401 / 3931-524 / 3931-701 | 280 / 16.380 / 2.253 PCI; 35 / 1.971 / 278 MSU |
| MSU Exhibit [IBM2025-MSU-Exhibit] | 3931-710 / 714 / 759 (7xx'te PCI yok) | 2.253 / 2.953 / 9.609 MSU |
| Stine 2022 [Stine2022] | 3931-7K0 (200 CP) | 215.089 PCI (bağımsız kontrol) |

**Türetme**

```
TPS/PCI   = 174.000 / 21.579 = 8,063   ve   227.000 / 29.048 = 7,815   → ortalama 7,939
ham_TPS   = PCI × 7,939 / w / (1 − f)        f = zIIP payı (0 / 0,10 / 0,25)
taşınan   = ham_TPS × ρ_max                  ρ_max = 0,90 (latency hedefi yoksa)
7xx PCI   = MSU × (PCI/MSU, LSPR'li komşu kademelerden)   → 7K0 türetilen 215.099 vs Stine 215.089
```

- LSPR bütün nesilleri System z9 2094-701 = 1,00 bazında verir; z13 ölçümü z16 kademelerine nesil farkıyla birlikte taşınır.
- n-way ölçekleme kaybı her kademenin PCI'sinde zaten var; köprüde ayrıca uygulanmaz. İki noktanın %3,1 farkı = köprünün belirsizliği.

**Veri / kaynak:** `data/raw/z13_anchors.csv`, `lspr_itrr_3931.csv`, `mainframe_exhibit_3931_7xx_msu.csv`, `z16_max_pci_anchor.csv`; v3 §4.

**Tasarım gerekçesi:** Ham IBM verisi dosyada, erişim tarihiyle; türetilen 317 kademelik tablo bu dosyalardan yeniden üretilir (`tools/build_z16_capacity_table.py`).

**Konuşmacı notu:** "Tek bir sayı, 7,939, bütün mainframe kapasite hesabının temeli. İki IBM ölçüm noktasından geliyor ve 200 CP'lik makinenin bağımsız PCI değerini %0,01 içinde tutturuyor."

---

### Slayt KB-02.2 — KB-02: örnek hesap ve açık kalan

**Örnek (10K TPS oltp_rw, 3931-524: 24 CP, 16.380 PCI, 1.971 MSU):**

```
ham_TPS   = 16.380 × 7,939 / 12,85 / (1 − 0,10) = 11.244 TPS
taşınan   = 11.244 × 0,90                       = 10.119 TPS  ≥ 10.000  ✓  (bir alt kademe 3931-523: 9.764 TPS ✗)
fatura MSU= 1.971 × 10.000 / 11.244             = 1.753 MSU  (R4HA; KB-11'in girdisi)
```

Aynı kural 3931-516'da (11.743 PCI) yalnızca 7.255 TPS taşır; F kararından önce (w = 9,15) 10K TPS için yetiyordu.

- Makullük: IBM z14 "günde 12 milyardan fazla şifreli işlem" (~139K TPS) [AmwalAlGhad2017-z14]; z14 ~160K PCI ile w ≈ 9 → büyüklük mertebesi tutuyor.
- Açık kalan: köprünün tek kaynağı REDP-5320; LSPR karışımının CICS/Db2 OLTP'ye benzediği bir varsayım. x86 karşılığı KB-03, çapraz kontrol KB-04.

**Veri / kaynak:** model `raw_tier_tps`, `tier_max_tps`, `consumed_msu`; v3 §4.4.3, §4.5.

**Tasarım gerekçesi:** Tek kaynaklı bir köprü, bağımsız bir büyüklük kontrolü ve platformlar arası tutarlılık kontrolüyle desteklenir.

**Konuşmacı notu:** "10.000 TPS'i taşıyan en küçük kademe 524; tavanın altında 10.119 TPS'le, yani yüzde bir boşlukla. Kademe seçimi bu kadar sıkı."

---

### Slayt KB-03.1 — x86 kapasite köprüsü: SPECint birimi başına TPS

**Kullanılan veri**

| Kaynak | Değer |
|---|---|
| Vonng, AWS c5d.metal, 2 × Xeon Platinum 8275CL, **48 fiziksel çekirdek**, 16 × 10M tablo [Vonng-PGPerf] | `oltp_read_write` **519.069 QPS** |
| SPECrate2017_int_base, Cascade Lake 8270 [SPEC2019-M640-8270] | 309 / 52 çekirdek = **5,94** / çekirdek |
| SPECrate2017_int_base, Dell R760, 2 × Xeon Gold 6548Y+ [SPEC2024-R760-6548Y] | 628 / 64 çekirdek = **9,81** / çekirdek |
| Intel RCP, 6548Y+ [Intel-Xeon6548Yplus] | $4.173 / 32 çekirdek, 250 W TDP |

**Türetme**

```
TPS              = 519.069 QPS / 20 ifade                 = 25.953 TPS
X86_TPS_PER_SPECINT_CORE = 25.953 / 48 / 5,94             = 91,0
TPS/çekirdek     = 91,0 × SPECint/çekirdek × S(n) × (1 − VIRT) × (1 − CONT) × Oracle çarpanı
S(n)             = (n / 48)^(B − 1),   B = 0,90 (0,80 – 1,00)
VIRT             = vSphere 0,03 / 0,07 / 0,15;  OCP-V 0,05 / 0,12 / 0,25;   CONT (K8s) 0,02
```

- Bu katsayı çekirdek sayısını, dolayısıyla çekirdek başına lisansı (Oracle, vSphere), düğüm sayısını ve Patroni tavanını belirler.
- Bağlam (normalize edilemiyor): [Rockdata2026], [Tencent-PG-TestResults], [Alibaba-PolarDB-PG16].

**Veri / kaynak:** yukarıdaki tablo; x86 dokümanı §5.1, §5.3.

**Tasarım gerekçesi:** PCI köprüsünün simetriği: üretici bağımsız bir performans ölçeği (SPECrate2017) üzerinden ölçümü hedef SKU'ya taşımak.

**Konuşmacı notu:** "Mainframe'de PCI neyse x86'da SPECint o. İkisi de bir ölçümü hedef donanıma taşımak için kullanılan ölçek."

---

### Slayt KB-03.2 — KB-03: örnek hesap, K kararı, K6 protokolü

**Örnek (10K TPS, R760-sınıfı 2×8c = 16 çekirdek, vSphere VM, PostgreSQL):**

```
S(16)         = (16 / 48)^(0,90 − 1)             = 1,116
TPS/çekirdek  = 91,0 × 9,81 × 1,116 × (1 − 0,07)  = 927
düğüm ham TPS = 927 × 16                          = 14.828 TPS
kullanım      = 10.000 / 14.828                   = %67,4  ≤ %70 tavan ✓  (Patroni: yük tek birincilde)
```

Büyük düğümde aynı kural: 2×32c → 807 TPS/çekirdek × 64 = 51.635 ham TPS → × 0,70 = **~36.100 TPS** Patroni tavanı (KB-06).

- **Karar K (b), Emirhan, 2026-11-16:** çapa K6 kendi ölçümümüz; Vonng çapraz kontrol. O zamana kadar **120 / 91 / 60**.
- K6 şartları: SPEC'i yayımlanmış perakende SKU; istemci ayrı makinede; PG sürümü, iş parçacığı, süre, `synchronous_commit`, `fsync`, `shared_buffers` raporlanır; 8/16/32/64 çekirdek taraması (USL); point_select / read_only / write_only da koşulur; bir koşu senkron replikayla.
- Açık kalan: Cascade Lake → Emerald Rapids SPECint artışının bir kısmı bellek bant genişliğinden; OLTP'nin aynı oranda yararlandığı varsayım. Oracle verim çarpanı 1,0 (OTN benchmark yasağı).

**Veri / kaynak:** model `tps_per_core`, `node_raw_tps`; kopruler_v1 KB-03; x86 dokümanı §5.2, §18.

**Tasarım gerekçesi:** Protokol şartları, Vonng ölçümünün belgelenmemiş ayarlarından kaynaklanan belirsizliği tekrarlamamak için.

**Konuşmacı notu:** "Üç düğümlük Patroni kümesinin birincil düğümü 10K TPS'i %67 kullanımla taşıyor. Ölçüm gelince 60–120 aralığı daralacak; yapı aynı kalacak."

---

### Slayt KB-04.1 — Platformlar arası tutarlılık kontrolü

**Kullanılan veri:** KB-02'nin çıktısı (3931-701, tek tam hızlı CP: 2.253 PCI [IBM-LSPR-ITRR]) ve KB-03'ün çıktısı (R760 çekirdeği, ham, S = 1: 91,0 × 9,81).

**Türetme**

```
1 z16 CP   = 2.253 PCI × 7,939 / 12,85         = 1.392 oltp_rw TPS
1 R760 çek.= 91,0 × 9,81                        =   893 oltp_rw TPS
1 CP       ≈ 1.392 / 893                        =  1,56 R760 çekirdeği
```

| Durum | 1 CP = kaç R760 çekirdeği |
|---|---|
| F öncesi (w 9,15) | 2,19 (zIIP payıyla 2,43) |
| **F sonrası (w 12,85), ana** | **1,56** |
| Aralık uçlarıyla (KB-01/02/03 low–high) | ~0,8 – 4,5 |

- Modelde parametre değil; iki bağımsız zincirin (LSPR + REDP ile SPEC + Vonng) aynı mertebede buluştuğunu gösteren kontrol.

**Veri / kaynak:** [DERIVED] KB-02 × KB-03; x86 dokümanı §5.5.

**Tasarım gerekçesi:** Doğrulama değil büyüklük mertebesi kontrolü; bağımsız iki zincirde mertebe hatası olsaydı burada görünürdü.

**Konuşmacı notu:** "Bir mainframe çekirdeği yaklaşık bir buçuk modern x86 çekirdeği ediyor. Literatürdeki '1 CP = 24–80 çekirdek' iddiası nereden geliyor, bir sonraki slayt."

---

### Slayt KB-04.2 — Örnek: "1 CP = 24–80 x86 çekirdeği" iddiasının ayrıştırılması

**Kullanılan veri:** IBM konsolidasyon formülü `N < P_R × U_R × C_R` [Shedletsky2008] [VENDOR]: performans oranı P_R 1–3, kullanım oranı U_R 10–20 (dağıtık %5–12 vs mainframe %80–90), sunucu başına çekirdek C_R.

**Örnek (gösterim):** `P_R 1,56 (bizim KB-04) × U_R 90/12 = 7,5 × C_R 2–7` → 1 CP ≈ **23 – 82** çekirdek. İddianın aralığı yeniden üretiliyor, ama çarpanın **~5 katı U_R'den**, yalnızca 1,56'sı işlemci hızından geliyor.

| Bileşen | Modelde nerede | Değer (mid) |
|---|---|---|
| P_R (işlemci hızı) | KB-02/03/04 | 1,56 |
| U_R (kullanım) | KB-05 tavanı | MF 0,90; x86 0,70 (park senaryosu 0,175) |
| dev/test kopyaları | KB-14 | MF 0,20; x86 0,50 |

- Uzlaştırma: U_R'yi en uç haliyle (%17,5 tavan, "konsolide edilmemiş park") koşturmak bile sıralamayı çevirmiyor: x86 $57,65 → $69,18, mainframe $117,92 (Demo Case 1).

**Veri / kaynak:** [Shedletsky2008]; `benzer_calismalar_v1.md` §3.3; `print_compare` park satırı.

**Tasarım gerekçesi:** Üretici iddiasını reddetmek yerine bileşenlerine ayırıp her bileşeni ayrı, kaynaklı bir katmanda modellemek.

**Konuşmacı notu:** "IBM'in ünlü oranını çürütmüyoruz, parçalıyoruz. Parçaların her biri modelde ayrı bir düğme."

---

### Slayt KB-05.1 — Kullanım oranı, kuyruk ve latency

**Kullanılan veri**

| Parametre | low (x86 lehine) | mid | high | Dayanak |
|---|---|---|---|---|
| Mainframe kullanım tavanı | 0,90 | 0,90 | 0,90 | WLM + CoD (v3 §5.3) |
| X86_UTIL_CEILING | 0,90 | 0,70 | 0,50 | U kararı |
| X86_NET_RTT_MS | 0,05 | 0,15 | 0,5 | [ASSUME] aynı veri merkezi |
| Gidiş-dönüş / işlem | 1 (saklı yordam) | 20 (ifade sayısı) | 20 | KB-05 |
| T_NVME_READ / WAL fsync | — | 141 µs / 60 µs | — | [StorageReview2022-P5520] / [ASSUME] |
| T_SAN_READ | 150 µs | 250 µs | 400 µs | [ASSUME] |
| Senkron replikasyon | — | 20 km × 10 µs/km | — | ortak fizik; [EDB-SyncRep] 10 ms'de `remote_write` +6,5 ms |

**Türetme (iki tarafta aynı kuyruk ailesi: CP/çekirdek başına bağımsız M/M/1, tutucu üst sınır)**

```
E[X]   = 1 / (CP ya da çekirdek başına TPS)
R(p)   = D_sabit + E[X] / (1 − ρ) × ln(1 / (1 − p))          p = 0,99 → ln(100) = 4,605
Mainframe: D_sabit = D_io                       ρ_max = min(ρ_latency, 0,90)
x86:       D_sabit = D_ağ + D_io + D_repl        ρ_max = min(ρ_latency, X86_UTIL_CEILING)
```

**Veri / kaynak:** v3 §5.3; x86 dokümanı §6; [EDB-SyncRep], [StorageReview2022-P5520].

**Tasarım gerekçesi:** Kurulu kapasite donanımı ve çekirdek başına lisansı belirler; iki taraf aynı kurala bağlanmazsa U_R etkisi kontrolsüz biçimde sonuca girer.

**Konuşmacı notu:** "v4 dokümanı x86 için M/M/c öneriyordu; o, x86'yı mainframe'den daha iyimser bir kuyrukla ölçmek olurdu. İkisini aynı aileye bağladık."

---

### Slayt KB-05.2 — KB-05: örnek hesap (10K TPS p99) ve U kararı

**Örnek, x86 (X1, 2×8c, 927 TPS/çekirdek, ρ = 0,674):**

```
D_ağ   = 20 × 0,15 ms                     = 3,000 ms
D_io   = 2,8 senkron okuma × 141 µs + 1 × 60 µs = 0,455 ms
D_repl = yerel senkron replika             = 0,210 ms      → D_sabit = 3,665 ms
R_cpu  = (1 / 927 s) / (1 − 0,674) × 4,605 = 15,26 ms
p99    = 3,665 + 15,26                      ≈ 18,9 ms
```

**Örnek, mainframe (M1, 3931-524, CP başına 11.244 / 24 = 468,5 TPS, ρ = 0,889):**

```
R_cpu = (1 / 468,5 s) / (1 − 0,889) × 4,605 = 88,5 ms;   D_io = 0,26 ms   → p99 ≈ 89 ms
```

- Alt-kapasite (5xx) CP yavaş olduğu için mainframe p99'u yüksek; 20 ms hedefi mainframe'i 3931-710'a (tam hızlı CP) iter, x86'nın seçimini değiştirmez (Demo Case 3).
- **Karar U (b), Emirhan, 2026-11-16:** x86 tavanı 0,90 / 0,70 / 0,50; low ucu mainframe ile eşit. %15–20 alt uç ana aralıkta yok (çift sayım); yalnızca park uzlaştırma senaryosu.

**Veri / kaynak:** model `latency_at`, `fixed_delay_s`; kopruler_v1 KB-05.

**Tasarım gerekçesi:** x86'da WLM ve CoD karşılığı olmadığı için tepe yükte boşluk bırakılır; tavan bunu yansıtır ama literatürün en uç değerini ana senaryoya taşımaz.

**Konuşmacı notu:** "x86'da latency'nin beşte biri ağdan geliyor; mainframe'de neredeyse tamamı yavaş CP kuyruğundan. U kararı x86 aleyhine bir yanlılığı düzeltti: önceki taslakta x86 da %90'a kadar dolduruluyordu."

---

### Slayt KB-06.1 — Ölçekleme mimarisi ve kapasite tavanları

**Kullanılan veri**

| Parametre | Değer | Dayanak |
|---|---|---|
| En büyük z16 A01 kademesi | 3931-7K0, 200 CP, 215.099 PCI | [IBM-LSPR-ITRR], [Stine2022] |
| Patroni yazma modeli | tek yazıcı; replikalar yazma kapasitesi eklemez | [Patroni-ReplModes] |
| En büyük ana katalog düğümü | 2×32c (64 çekirdek) | x86 dokümanı §4.1 |
| RAC_SCALING_EFFICIENCY | 0,95 / 0,90 / 0,80 | Oracle: <%80 çekişme işareti [Oracle2024-RAC] |
| RAC_MAX_NODES | 8 (N+1: k − 1 düğüm yükü taşır) | [ASSUME] |
| B_X86 (S(n) üssü) | 1,00 / 0,90 / 0,80 | [Kapila2016-PGCon]; [ASSUME] |

**Türetme**

```
Mainframe tavanı = 215.099 × 7,939 / 12,85 / 0,9 × 0,90           ≈ 132.900 TPS
Patroni tavanı   = 807 TPS/çek. × 64 × 0,70                         ≈  36.100 TPS
RAC tavanı       = 51.635 × [1 + (7 − 1) × 0,90] × 0,70  (8 düğüm, 7'si yükte) ≈ 231.300 TPS
```

| | Mainframe | x86 |
|---|---|---|
| Modellenen | Tek CEC; M2–M4'teki ikinci frame yedek | Patroni tek yazıcı; Oracle RAC düğüm ekler |
| Modellenmeyen | Parallel Sysplex data sharing | Citus / sharding (K3) |

**Veri / kaynak:** x86 dokümanı §5.4; v3 §4.

**Tasarım gerekçesi:** Yüksek TPS'te crossover'ın yeri iki tarafın tek sistem tavanına bağlı; iki tavan aynı statüde (modellenmeyen ölçekleme seçeneği) yazılmalı.

**Konuşmacı notu:** "Parallel Sysplex'i modellemediğimiz için mainframe 133K'da duruyor; Citus'u modellemediğimiz için PostgreSQL 36K'da. Simetrik bir sınırlama."

---

### Slayt KB-06.2 — KB-06: örnek hesap ve karar

**Örnek (50K TPS, Patroni tavanı aşılır → Oracle RAC):**

```
2×8c düğüm ham = 14.828 TPS;  k = 7 düğüm:  14.828 × [1 + 6 × 0,90]      = 94.902 ham
N+1 (bir düğüm kaybında 6 düğüm) = 14.828 × [1 + 5 × 0,90]                  = 81.556 ham
kullanım       = 50.000 / 81.556 = %61,3  ≤ %70 ✓   (k = 6'da N+1 kapasitesi 68.211 × 0,70 < 50.000 ✗)
sonuç          = vSphere / VM / Oracle X1, 7 × 2×8c, $37,71/TPS (mainframe 3931-759 $71,35)
```

Neden çok küçük düğüm: N+1 yedeği küçüldükçe ucuzlar, S(n) küçük düğümde yüksek, marjinal RAC verimi sabit. `RAC_MAX_NODES` = 4 ile 50K'da personel hariç maliyet +%10; 130K infeasible.

- K3 (b), Emirhan, 2026-11-02: Citus yok, tavan bir sınırlama.
- **Düzeltme (x86 §17, #4):** B_X86 low = 1,00 / high = 0,80 yalnızca n > 48 için x86 lehine; n < 48'de tersine dönüyordu (2×8c'de b = 0,80 S'yi 1,25 yapar) → `X86_SCALING_LEVEL` düğüme göre yön tutarlı uç.
- Okunuş: ~36K'ya kadar MF ↔ PG; 36K–133K MF ↔ RAC; 133K üstü yalnızca RAC. Açık kalan: K6'da USL (Gunther) uyumu; RAC için USL biçiminde kaynak.

**Veri / kaynak:** Demo Case 2 (50K); x86 dokümanı §5.3, §17; `test_scaling_corners_direction_consistent`.

**Tasarım gerekçesi:** "low = x86 lehine" tanımı her koşulda tutmalı; tutmadığı yer test ile korunuyor.

**Konuşmacı notu:** "50K'da x86'nın kendi içinde bir crossover var: açık kaynak tavanı aşılınca ticari veritabanı zorunlu ve personel hariç maliyet 3 katına çıkıyor."

---

### Slayt KB-07.1 — Availability denklemi

**Kullanılan veri (ortak modül, iki tarafta aynı)**

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| Saha olayı sıklığı λ_saha (/yıl) | 0,05 | 0,15 | 0,25 | [Uptime2025-PR], [DCF2022-Uptime] |
| Kısa olay süresi d_kısa | 1 sa | 2 sa | 4 sa | aynı |
| Uzun olay payı p_uzun / süresi d_uzun | 0,08 / 24 sa | 0,15 / 48 sa | 0,30 / 72 sa | aynı |
| Elle geçiş karar süresi | 45 dk | 90 dk | 180 dk | [ASSUME] |
| Maskelenemeyen platform payı u (Değ #10) | 0,05 | 0,10 | 0,20 | [ASSUME]; [Yuan2014], [Gunawi2016] |
| ITIC sunucu kesintisi: z16 | 0,03 sn | 0,32 sn | 3,15 sn | [ITIC2023-IBMZ] |
| ITIC sunucu kesintisi: x86 (Lenovo / Dell / white box) | 0,5 dk | 24 dk | 59 dk | [ITIC2023-IBMZ], [TechChannel2024-ITIC] |

**Türetme**

```
D_saha     = λ × [(1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec)]     ← ortak
D_planlı   = λ_planlı (0,5/yıl) × T_planlı(topoloji)                                    ← platforma özgü
D_platform = N_kesen × ITIC_sunucu × u^katman  (tek CPC'de u = 1; aktif-aktif u²)        ← ortak kural
x86 ek     = 12 yama switchover × T_sw + N_kesen × λ_düğüm × T_failover × (1 − u)
A          = 1 − D / 8.760
```

**Veri / kaynak:** [Uptime2025-PR], [DCF2022-Uptime], [IBM-SG24-8446], [ITIC2023-IBMZ], [TechChannel2024-ITIC], [Vishwanath2010], [Yuan2014], [Gunawi2016]; `common_model.site_downtime_hours`, `platform_downtime_hours`.

**Tasarım gerekçesi:** "Nine" değerleri farklı kaynaklardan gelirse karşılaştırılamaz. İki taraf aynı veri merkezi olaylarına ve aynı platform kesintisi kuralına maruz kalır; fark yalnızca kurtarma, planlı işlem ve sunucunun kendi güvenilirliğinden.

**Konuşmacı notu:** "Availability'yi bir sayı olarak değil bir denklem olarak köprüledik; böylece iki tarafın yüzdeleri aynı kaynaktan geliyor."

---

### Slayt KB-07.2 — KB-07: örnek hesap (M1, X1, M3, X3) ve açık kalan

**Örnek (mid değerler):**

| Terim | M1 (tek frame) | X1 (Patroni, 3 düğüm) | M3 (GDPS Metro) | X3 (Patroni, 2 site) |
|---|---|---|---|---|
| T_rec (site kaybı) | yok (∞) | yok (∞) | 2 dk | 2 dk |
| D_saha | 0,15 × (0,85 × 2 + 0,15 × 48) = **1,335 sa** | 1,335 sa | 0,15 × 2/60 = 0,005 sa | 0,005 sa |
| D_planlı | 0,5 × 240 dk = 2,000 sa | 0,5 × 15 dk = 0,125 sa | 0,5 × 2 dk = 0,017 sa | 0,017 sa |
| Yama switchover | — | 12 × 15 sn = 0,050 sa | — | 0,050 sa |
| D_platform | 1 × 0,32 sn × u=1 ≈ 0 | 1 × 24 dk × 0,10 = 0,040 sa | ≈ 0 | 0,040 sa |
| Düğüm failover | — | 0,1 × 35 sn × 0,9 = 0,001 sa | — | 0,001 sa |
| **Toplam D / A** | 3,335 sa → **%99,962** | 1,551 sa → **%99,982** | 0,022 sa → **%99,9998** | 0,112 sa → **%99,9987** |

- Okunuş: M1 – X1 farkı planlı kesintiden (tek frame'de 4 sa'lik bakım); M3 – X3 farkı platform kesintisinden (x86 sunucusu yılda 24 dk, z16 0,3 sn). Bu yüzden %99,999 + RPO 0'da yalnızca mainframe kurulabiliyor (Demo Case 11).
- Açık kalan: planlı kesinti sıklığı iki tarafta kaynaksız; u kaynakla daraltılamadı (u = 0,05'te x86 Oracle X3 %99,999'u sağlar); bölgesel felaket modellenmedi.

**Veri / kaynak:** model `Topology.availability`; [Pigsty-RTO] (Patroni 27–41 sn), [Oracle2026-MAA], [YellowBricks2021]; v3 §6.4; x86 dokümanı §8.3.

**Tasarım gerekçesi:** Ortak modüldeki parametreler bir tarafın lehine ayrı ayarlanamaz; platforma özgü olanlar kendi kaynaklarıyla.

**Konuşmacı notu:** "Tablonun son satırı tezin availability bulgusu: tek frame mainframe x86 kümesinden düşük, ama iki siteli yapıda mainframe sunucunun kendi güvenilirliği sayesinde öne geçiyor."

---

### Slayt KB-08.1 — Topoloji eşlemesi

**Kullanılan veri:** IBM'in dört dayanıklılık deseni [IBM-SG24-8446]; Oracle MAA Bronze/Silver/Gold/Platinum [Oracle2026-MAA]; Patroni çok veri merkezi önerisi "run Patroni standby cluster in the second data center" [Patroni-MultiDC]; GDPS [Cook2026-GDPS].

| Kod | Mainframe | x86 (Oracle MAA / Patroni) | RPO | T_rec teknik (mid, MF / x86) | Topoloji maliyeti (MF) |
|---|---|---|---|---|---|
| M1 / X1 | Reliable base | Silver / tek site 3 düğüm | 24 sa (aynı kural) | site yok | — |
| M2 / X2 | Failover capable (CBU) | Data Guard SYNC / standby küme | 0 (PG: 5 sn) | 90 dk karar + 30 / 15 dk | DR frame × 0,50 |
| M3 / X3 | Fault tolerant (GDPS Metro) | Gold / çok siteli Patroni | 0 | 2 dk / 2 dk (Değ #10) | + GDPS $50K/ay |
| M4 / X4 | Adaptive continuity (GDPS CA) | Platinum (GoldenGate) / PG yok | 5 sn | 30 sn / 15 sn | + GDPS $100K/ay |

**Türetme:** kullanıcı topoloji seçmez; `--availability`, `--rpo-seconds`, `--rto-minutes` girer. Model her iki tarafta RPO ≤ hedef, T_rec ≤ RTO ve A ≥ hedef koşullarını sağlayan topolojilerin **en ucuzunu** seçer. Topoloji personel çarpanı ortak: 1,00 / 1,05 / 1,15 / 1,25.

**Veri / kaynak:** [IBM-SG24-8446], [Cook2026-GDPS], [MLE-GDPS], [Oracle2026-MAA], [Pigsty-RTO], [Patroni-MultiDC].

**Tasarım gerekçesi:** Desen düzeyinde eşleme: iki taraf aynı dayanıklılık sınıfında karşılaştırılır, aynı ada sahip ama farklı güvence veren yapılar değil.

**Konuşmacı notu:** "M ve X kodları aynı soruya cevap veriyor: bir site kaybolursa ne kadar veri ve ne kadar zaman kaybederim?"

---

### Slayt KB-08.2 — KB-08: örnek hesap ve düzeltme

**Örnek (10K TPS, aynı hedef iki modele):**

| Hedef | Mainframe seçimi | x86 seçimi |
|---|---|---|
| %99,9 | M1 3931-524, $117,92 | X1 PG, $57,65 |
| %99,99 + RPO 0 + RTO ≤ 120 dk | M2 3931-524, $126,48 | X2 **Oracle** + Data Guard, $65,38 (PG X2'nin RPO'su 5 sn) |
| %99,999 | M3 3931-524, $138,35 (GDPS $50K + DR frame + personel × 1,15) | X4 Oracle aktif-aktif, 4 × 2×8c, $79,77 |
| %99,999 + RPO 0 | M3, $138,35 | **kurulamaz** |
| RPO 0 + RTO ≤ 1 dk | **infeasible** (saniyelik kurtarma yalnızca asenkron GDPS CA'da) | — |

- K4 (b), Emirhan, 2026-11-02: X4 PostgreSQL için yok; açık kaynak çekirdekte karşılığı olmayan topoloji uydurulmaz.
- **Düzeltme (x86 §17, #1):** KB-08'de X2 RPO 0 idi (iki DB). Patroni'nin önerdiği standby küme asenkron → X2-PG RPO 5 sn [ASSUME]; Oracle Data Guard Max Availability SYNC ile 0. Sonuç: RPO 0 + elle geçişte veritabanı PostgreSQL'den Oracle'a geçiyor (Demo Case 4).

**Veri / kaynak:** Demo Case 4, 11; x86 dokümanı §8.2; `test_topologies_and_availability`.

**Tasarım gerekçesi:** Topolojinin RPO'su ürünün kendi belgesinden okunur; köprü dokümanındaki genelleme ürüne uymadığında ürün belgesi kazanır.

**Konuşmacı notu:** "Aynı hedef iki tarafta farklı yapı seçtiriyor; tablo, hedef yükseldikçe x86'nın önce açık kaynağı bıraktığını, sonra hiç kuramadığını gösteriyor."

---

### Slayt KB-09.1 — Storage arayüzü ve fiyat sözleşmesi

**Kullanılan veri**

| Girdi / parametre | Değer | Dayanak |
|---|---|---|
| Veri, büyüme, planlama ufku | 20 TB, %15/yıl, 3 yıl | ortak girdi |
| IOPS / işlem (oltp_rw) | 14 okuma × 4 getpage × (1 − 0,95) = 2,8 senkron okuma + 1 log + 4 × 0,5 asenkron = **5,8** | ortak I/O kuralı |
| IOPS tavanı | üreticinin tepe IOPS'unun %70'i | [ASSUME] |
| DS8900F flash liste fiyatı | $8,62/GB ham | [ITJungle2022-Storage] |
| AFA etkin TB fiyatı | $65–215 indirimli / $140–400 liste | [VendorBenchmark2026-Storage] |
| Mainframe: DB yükü / RAID / Safeguarded | × 1,5 / 0,75 / + %25 rezerv | v3 §8 |
| x86 PG: MVCC + WAL şişmesi | × 1,1 / 1,3 / 1,6 | [ASSUME] |

**Türetme**

```
planlanan veri = 20 × 1,15³                               = 30,4 TB
Mainframe ham  = 30,4 × 1,5 / 1,0 / 0,75 × 1,25 (rezerv)  × kopya (M1 1, M2 2, M3/M4 4)
x86 Oracle     = paylaşımlı AFA (site başına 1 + DR kopyası)
x86 Patroni    = yerel NVMe × düğüm sayısı (her replika tam kopya, düğüm içi RAID yok)
fiyat          = her teklif önce ham TB başına listeye çevrilir; indirim bir kez; veri azaltımı yalnızca boyutlandırmada
```

**Veri / kaynak:** [ITJungle2022-Storage], [VendorBenchmark2026-Storage]; `common_model.py` §6; v3 §8; x86 dokümanı §11.

**Tasarım gerekçesi:** Storage veri hacmiyle büyüdüğü için ikinci crossover ekseni; iki taraf aynı girdilerle ve aynı fiyat tanımıyla boyutlanmazsa eksen anlamsızlaşır.

**Konuşmacı notu:** "Etkin TB fiyatı ile ham TB fiyatını karıştırmak storage karşılaştırmalarının en yaygın hatası; sözleşme bunu engelliyor."

---

### Slayt KB-09.2 — KB-09: örnek hesap ve etki

**Örnek (10K TPS, 20 TB):**

| | Mainframe M1 | x86 X1 Patroni |
|---|---|---|
| Ham kapasite | 30,4 × 1,5 / 0,75 × 1,25 = **76 TB** → 1 × DS8910F-993 | 30,4 × 1,3 = 39,5 TB / düğüm → 11 × 3,84 TB NVMe × 3 düğüm |
| IOPS ihtiyacı | 10.000 × 5,8 = 58.000 | 58.000 (sürücü başına 500K, tavan altında) |
| I/O gecikmesi (D_io) | 2,8 okuma × 68 µs (zHyperLink %80 + FICON) + log yazımı ≈ 0,26 ms | 2,8 × 141 µs + 60 µs = 0,46 ms |
| Aylık storage | **$7.496** (donanım net $236.849 + lisans, 5 yıl) | **$304** |

**Veri hacmi ekseni (Demo Case 5):** 500 TB'ta mainframe 1 × DS8910F-994 (1.901 TB ham) $153.226 + yedek $75.420 = toplamın **%16,1**'i; x86'da PG yerel disk sınırı (~373 TB) aşılır → Oracle + AFA, $65,47/TPS.

- K1 (a), Emirhan, 2026-11-02: storage tipi DB mimarisine bağlı. AFA_DATA_REDUCTION 1,5 / 2,5 / 4,0.
- Açık kalan: DS8900F gerçek indirim oranı (0,50–0,85) için teklif veya ihale kaydı.

**Veri / kaynak:** model `storage_plan`; Demo Case 5; x86 dokümanı §11.

**Tasarım gerekçesi:** Platformun kendi storage biçimi (shared-disk vs shared-nothing) korunur; arayüz ortak, mekanizma platforma özgü.

**Konuşmacı notu:** "20 TB'ta storage iki tarafta da önemsiz; 500 TB'ta mainframe toplamının altıda biri oluyor ve x86'da veritabanı seçimini değiştiriyor."

---

### Slayt KB-10.1 — Yedekleme

**Kullanılan veri**

| Parametre | Değer | Dayanak |
|---|---|---|
| Yedek kopyası | her seviyenin 2 kopyası (2 site) | "Make two copies of each level of image copy data sets" [IBM-Db2z12-Backup] |
| Saklama / günlük değişim | 4 hafta (2–8) / %3 | [ASSUME]; haftalık > %10 değişimde tam kopya [Hendley2024-IDUG] |
| Log baytı | yazma × 400 B + commit × 200 B | [ASSUME] |
| PostgreSQL full-page writes | WAL × 1,5 / 2 / 3 | [ASSUME]; K6'da ölçülecek |
| Ortalama / tepe yük | statik modda ort. = tepe / 1,5 | [ASSUME] |
| Pencere / geri yükleme kısıtı | 8 sa / M1–X1'de ≤ RTO / 2 (36 sa) | [ASSUME] |
| Hedef fiyatları | nesne depolama $100/TB donanım + $5/TB-ay; S3 $0,0125/GB-ay | [MinIO-ObjectTCO], [Nubbo2026-S3], [AWS-DXPricing] |

**Türetme**

```
image copy = D_plan × hafta × (1 tam + 6 artımlı × günlük değişim)
log        = ort. TPS × işlem başına log baytı × 86.400 × 7 × hafta          (x86'da × WAL_FPW_FACTOR)
hedef      = kısıtları (pencere, geri yükleme süresi, TCT verimi) karşılayan en ucuz: TS7770 / nesne / S3
```

**Veri / kaynak:** yukarıdaki tablo; `common_model.backup_volumes`; v3 §8.10; x86 dokümanı §11.4.

**Tasarım gerekçesi:** Hacim kuralı iki tarafta aynı, böylece yedek farkı yalnızca platformun gerçek özelliklerinden (WAL FPW, sıkıştırma, TCT verimi) gelir.

**Konuşmacı notu:** "Log hacmi TPS'e bağlı; yedeği iş yüküne bağlayan tek mekanizma bu ve iki tarafta aynı bileşimden hesaplanıyor."

---

### Slayt KB-10.2 — KB-10: örnek hesap ve iki tarafın farkı

**Örnek (10K TPS → ort. 6.667 TPS, 20 TB → 30,4 TB):**

```
image copy  = 30,4 × 4 × (1 + 6 × 0,03)                 = 143,6 TB
log baytı   = 4 × 400 + 1 × 200                         = 1.800 B / işlem
log         = 6.667 × 1.800 × 86.400 × 28 gün / 10¹²   =  29,0 TB          → mainframe site başına 172,6 TB
x86 log     = 29,0 × 2 (FPW)                            =  58,1 TB
x86 saklanan= (143,6 + 58,1) / 2 (sıkıştırma)            = 100,8 TB / site
```

| | Mainframe | x86 |
|---|---|---|
| Seçilen hedef | on-prem nesne depolama (alternatif TS7770 $11.790/ay, S3 $6.069/ay) | on-prem nesne depolama |
| Geri yükleme | ~2,4 sa (bütçe 36 sa) | — |
| Aylık yedek | **$5.635** | **$4.917** |
| Yol ve verim | DS8900F TCT ≤ 5.000 MB/s | pgBackRest / RMAN, 2 × 25 GbE × %80 |
| Sıkıştırma | TS7770 2,0; nesne 1,0 | 3,0 / 2,0 / 1,5 |

- Asimetri (x86'da sıkıştırma var, mainframe nesne hedefinde yok): platform özelliği, küçük etkili, açıkça yazılı. 500 TB'ta mainframe'de nesne depolama geri yükleme kısıtını aşar → TS7770 (~31 sa).

**Veri / kaynak:** model `backup_plan`; Demo Case 5, 7; x86 dokümanı §11.4, §18 (tehdit 13).

**Tasarım gerekçesi:** Ortak olan (hacim, fiyat) ortak modülde; platforma özgü olan (yol, sıkıştırma, WAL) platform modelinde.

**Konuşmacı notu:** "Yedek toplamın %1'inden az, ama tam yığın iddiası için iki tarafta da aynı derinlikte olmak zorundaydı."

---

### Slayt KB-11.1 — Lisans tabanı: yapısal asimetri

**Kullanılan veri, mainframe (AWLC, aylık, MSU başına; kümülatif kademe)** [Adams2005-z9SWPricing], [IBM-zNALC], [Longpela-SWPrice]

| Kademe (MSU) | 1–3 | 4–45 | 46–175 | 176–315 | 316–575 | 576–875 | 876–1.315 | 1.316–1.975 | 1.976+ |
|---|---|---|---|---|---|---|---|---|---|
| $/MSU | $3.960 taban | 208 | 88 | 66 | 50 | 40* | 32* | 25,6* | 20,5* |

\* L4+ yayımlanmıyor: L3 × 0,80^k [ASSUME; aralık 0,70–1,00]. Ürün çarpanları IBM örnek faturasından: z/OS $75.459, CICS $32.978 (210 MSU), Db2 $31.876 (265 MSU) → referans eğriye göre × 2,509 / 1,247 / 1,060.

**Kullanılan veri, x86**

| Kalem | Fiyat | Dayanak |
|---|---|---|
| vSphere Foundation | $150 / çekirdek-yıl (CPU başına en az 16 çekirdek) | [AceMQ-VVFvsVCF], [AceMQ2026-Renewals] |
| RHEL for Virtual Datacenters | $2.904 / düğüm-yıl | [CCSP-RH] |
| PostgreSQL desteği | $500 (destek kademesi: ≥ %99,99 / RPO 0 → $1.600; ≥ %99,999 → $2.400) / çekirdek-yıl | [EDB-Store], [EDB-Plans] |
| Oracle EE + RAC + Diagnostics + Tuning | $47.500 + 23.000 + 7.500 + 5.000 / işlemci; çekirdek faktörü 0,5; indirim %45; destek %22/yıl | [Redress2026-OraclePL], [Oracle2026-CoreFactor] |

| | Mainframe | x86 |
|---|---|---|
| Fatura tabanı | Tüketilen MSU'nun aylık R4HA tepesi | Kurulu fiziksel çekirdek / düğüm |
| DR sitesi | CBU: kalıcı (küçük) kapasiteden | Tam lisans |
| Geçici kapasite | On/Off CoD, TFP | Karşılığı yok |

- Kural: bu fark **eşitlenmez, modellenir**.

**Veri / kaynak:** yukarıdaki tablolar; [IBM-SC28-7025] (CBU, CoD).

**Tasarım gerekçesi:** Lisans modeli farkı platformların gerçek bir özelliği; eşitlemek karşılaştırmanın konusunu silmek olurdu.

**Konuşmacı notu:** "Personel hariç tutulduğunda iki platform arasındaki 40 katlık farkın kaynağı bu köprü."

---

### Slayt KB-11.2 — KB-11: örnek hesap ve düzeltme

**Örnek, mainframe (10K TPS, fatura 1.753 MSU; KB-02):**

```
referans eğri(1.753) = 3.960 + 42×208 + 130×88 + 140×66 + 260×50 + 300×40 + 440×32 + 438×25,6 = $83.669
z/OS  = 83.669 × 2,509 = $209.921
CICS  = 83.669 × 1,247 = $104.335
Db2   = 83.669 × 1,060 = $ 88.677          → yazılım $402.932 / ay  (toplamın %34'ü)
```

**Örnek, x86 (10K TPS, X1: 3 DB düğümü 2×8c + 2 uygulama düğümü 2×8c):**

```
vSphere   = (3 + 2) düğüm × 2 CPU × 16 çekirdek (asgari) × $150 / 12 = $2.000
RHEL VDC  = 5 × $2.904 / 12                                         = $1.210
PG desteği= 48 DB çekirdeği × $500 / 12                             = $2.000   → abonelikler $5.210 / ay
```

**Örnek, Oracle (50K TPS, 7 × 2×8c RAC):** 16 çekirdek × 0,5 = 8 işlemci × $83.000 × (1 − 0,45) = $365.200 / düğüm → 7 düğüm $2,56M; aylık 2,56M / 60 + 2,56M × 0,22 / 12 = **$89.474**.

- **Düzeltme (x86 §17, #2):** KB-11 OpenShift'i soket çifti başına (6K / 11K / 15K) fiyatlıyordu; sanal düğümler çekirdek tabanlı abonelik ister → $2.000 / 3.000 / 4.200 çekirdek çifti başına [RedHat2024-OCPSubGuide].

**Veri / kaynak:** model `software_monthly_cost`, `platform_subscriptions`, `oracle_license_net`; Demo Case 1, 2.

**Tasarım gerekçesi:** Abonelik kuralı ürün belgesinden okunur; her kalem üreticinin kendi abonelik kılavuzundan.

**Konuşmacı notu:** "Aynı 10K TPS için mainframe yazılımı ayda $403 bin, açık kaynak yığın $5 bin. Fark 77 kat ve kaynağı tamamen lisans modeli."

---

### Slayt KB-12.1 — Kapsam sınırı: işlem yöneticisi ve uygulama katmanı

**Kullanılan veri:** REDP-5320 CICS işlem tabanı **85,9 µs** (Db2 yok, yalnızca CICS + VSAM) [Burgess2016-REDP5320]; oltp_rw toplam CPU 1.103,9 µs (KB-01); x86 çapasında uygulama yerine sysbench istemcisi model dışında koşar [Vonng-PGPerf]; IBM'in 4,9 katlık işlem yöneticisi iddiası yalnızca üst uç duyarlılık [Shedletsky2008].

**Türetme (C kararı)**

```
TM_payı              = 85,9 / 1.103,9                         = %7,78
uygulama_çekirdekleri = DB_meşgul_çekirdekleri × TM_payı / (1 − TM_payı)
uygulama düğümleri    = Linux VM, ek lisans yok; sitede N+1 (en az 2), DR'da kopya
```

- Mainframe CPU'su ve lisansı CICS'i zaten içerir; mainframe tarafında değişiklik yok.

**Veri / kaynak:** [Burgess2016-REDP5320], [Shedletsky2008]; x86 dokümanı §10.

**Tasarım gerekçesi:** İki tarafın kapsam sınırı aynı olmalı; aksi halde mainframe faturasındaki CICS'in x86'da karşılığı eksik kalır (mainframe aleyhine kapsam asimetrisi).

**Konuşmacı notu:** "Mainframe'in lehine bir düzeltme: x86'ya, mainframe'in zaten ödediği uygulama katmanını ekledik."

---

### Slayt KB-12.2 — KB-12: örnek hesap ve etki

**Örnek (10K TPS):**

```
DB meşgul çekirdeği = 10.000 / 927 TPS/çek.              = 10,8 çekirdek
uygulama çekirdeği  = 10,8 × 0,0778 / 0,9222              =  0,91 çekirdek
uygulama düğümü     = max(2, ⌈0,91 / (16 × 0,70)⌉ + 1)   =  2 × 2×8c  (N+1)
aylık               = abonelik $1.284 + donanım/bakım/enerji ≈ toplamın %0,3'ü
```

- **Karar C (b), Emirhan, 2026-11-16.** Etki: personel hariç maliyetin ~%12'si; toplamda %0,3.
- Bu katman ağ gidiş-dönüşü terimini (KB-05) doğal kılar. Kendi bulgumuz: tavan ve sanallaştırma ek yükünün çift uygulanması düzeltildi (`test_app_tier`).
- Sınırlılık: bellek ve oturum sayısıyla boyutlanmıyor.

**Veri / kaynak:** model `app_core_need`, `app_hosts`; x86 dokümanı §10.

**Tasarım gerekçesi:** Etkisi küçük olsa da kapsam eşitliği ilkesi gereği zorunlu.

**Konuşmacı notu:** "Sonucu değiştirmeyen ama yapılmaması sonucu şüpheli yapacak bir düzeltme."

---

### Slayt KB-13.1 — Personel: problem ve kanıt

**Kullanılan veri, mainframe personel eğrisinin çapaları**

| Kaynak | Değer |
|---|---|
| IBM Eagle TCO ekibi, 17 müşteri [IBM-CPO2014-Skills] | "5 FTE to start + 1 FTE for every 625 MIPS" |
| Gartner IT Key Metrics 2016 [CA2016-MFEcosystem] | kurulu MIPS / FTE 152 → 268 |
| IBM örnek karşılaştırması [Rhoderick2007-TPFUG] | 3.192 MIPS'i ~4 FTE yönetiyor |
| Yüklü yıllık ücret [BLS-OOH], [BLS2026-ECEC], [IDC2016-ConnectedMF] | $122K / **$162K** / $215K (brüt $95K / 120K / 150K × 1,28 / 1,35 / 1,43) |

**Kullanılan veri, aynı iş yükü vakaları (x86 FTE / mainframe FTE; hepsi IBM kaynaklı)** [IBM-CPO2014-Skills], [Calderon2011-Labor], [Shedletsky2008], [Jones2007-TCO], [Astadia2024-ROI]: **3,28 · 3,00 · 1,23 · 1,32 · 3,10 · 1,50 · 15,4**. Geometrik ortalama: FTE vakaları 2,0; konsolide 1,25; hepsi 2,7.

- Problem (Değ. #8): eski kuralda 10K TPS'te mainframe 30,8 FTE, x86 sunucu saatlerinden 0,39 FTE (tabanla 4) çıkıyordu; fark ~$36/TPS/ay ve sonucu tek başına belirliyordu.
- Doğrudan oranlanamaz: mainframe ortalaması MIPS başına, x86 sunucu başına → aynı iş için ~1.300 kat fark (farklı yoğunlukta parklar). Bağımsız (Gartner, Avasant, IDC) aynı iş yükü karşılaştırması bulunamadı.

**Tasarım gerekçesi:** Personel 10K TPS'te maliyetin ~%48'i; iki tarafın personeli farklı sürücülerle ölçülürse crossover'ı teknoloji değil ölçüm farkı belirler.

**Konuşmacı notu:** "Bütün nicel vakalar IBM kaynaklı ve büyük ihtimalle x86 aleyhine yanlı. O yüzden bunları parametre olarak değil, duyarlılık referansı olarak kullanıyoruz."

---

### Slayt KB-13.2 — KB-13: P kararı, örnek hesap, başabaş oranı

```
PCI_eş(TPS) = TPS × w / 7,939 / 0,90                       (Değ #10: zIIP'e kayan iş de sayılır)
FTE_ortak   = max(taban, FTE_1000 × (PCI_eş / 1000)^b) × topoloji çarpanı
              FTE_1000, b, taban: low 4,0 / 0,6 / 3 · mid 5,5 / 0,7 / 4 · high 7,0 / 0,8 / 5
FTE_x86     = FTE_ortak × STAFF_RATIO_X86                  (ana senaryo 1,0)
```

**Örnek (10K TPS, oltp_rw, M1/X1):**

```
PCI_eş   = 10.000 × 12,85 / 7,939 / 0,90   = 17.985 PCI
FTE (mid)= 5,5 × 17,985^0,7 × 1,00          = 41,6 FTE      (low 22,6 · high 70,6)
aylık    = 41,6 × $162.000 / 12             = $561.236 → iki tarafta aynı (toplamın %48'i)
M3/X3'te × 1,15 = $645.421
```

**Başabaş:** `başabaş = 1 + (MF personel hariç − x86 personel hariç) / personel = 1 + (617.961 − 15.219) / 561.236 ≈ 2,07`. x86 personel oranı 2,07'yi aşarsa mainframe ucuz (oran 3,0'da x86 $169,89 vs MF $117,92; Demo Case 9).

- **Karar P, Emirhan, 2026-11-16:** personel crossover için nötr; duyarlılık 1,25 ve 2,0. Başlık çıktısı başabaş personel oranı.

**Veri / kaynak:** `common_model.staff_fte`, `mainframe_model.staff_pci_equivalent`; kopruler_v1 KB-13.

**Tasarım gerekçesi:** Kaynakla çözülemeyen bir soruyu (platformlar arası personel farkı) bir varsayımla kapatmak yerine soruyu çıktıya çevirmek: "x kat olursa sonuç döner".

**Konuşmacı notu:** "Bu köprü tezin en önemli metodolojik kararı. Okuyucuya bir sayıya inanmasını değil, kendi kurumunun personel oranını 2,07 eşiğiyle karşılaştırmasını söylüyoruz."

---

### Slayt KB-14.1 — Üretim dışı ortamlar

**Kullanılan veri:** IBM: dağıtık ortamda geliştirme/test "+%20 / +%200", HA kopyası üretimin 2–2,5 katı [IBM2013-TCOLessons]; x86 X1'de 3 düğüm → staging ≈ 1/3, dev/test ≈ 0,1–0,2 [DERIVED, ASSUME].

| Çarpan | low | mid | high | stres |
|---|---|---|---|---|
| NONPROD_FACTOR (mainframe) | 0 | **0,20** | 0,50 | — |
| NONPROD_FACTOR_X86 | 0 | **0,50** | 1,00 | 2,0 |

**Türetme (ortak modül §9)**

```
nonprod = çarpan(platform) × birincil site {yazılım + donanım + bakım + enerji + birincil storage}
          DR, site otomasyonu (GDPS), yedek ve personel hariç
```

**Veri / kaynak:** [IBM2013-TCOLessons]; v3 §7.9; x86 dokümanı §12.2.

**Tasarım gerekçesi:** Aynı kural, ayrı çarpan: yapı farklı (mainframe'de LPAR, x86'da ayrı düğüm ve Oracle'da ayrı çekirdek lisansı).

**Konuşmacı notu:** "IBM'in +%200 iddiasını ana senaryoya değil stres senaryosuna koyduk ve etkisini gösterdik."

---

### Slayt KB-14.2 — KB-14: örnek hesap ve tutuculuk yönü

**Örnek (10K TPS):**

```
Mainframe: 0,20 × (402.932 yazılım + 64.811 donanım + 32.405 bakım + 2.628 enerji + 7.496 storage) = $102.054  (%8,7)
x86:       0,50 × (5.210 + 932 + 233 + 189 + 304)                                                  = $  3.434  (%0,6)
x86 stres (2,0): x86 $57,65 → $58,68/TPS (+%1,8)
```

- İki tarafa ayrı çarpan: Emirhan, 2026-11-02; x86 aralığı N (b): 2026-11-16.
- Mainframe kuralı, dev/test'in aynı CEC'te R4HA tepesine az katkısını ve IBM'in geliştirme/test fiyat tekliflerini saymaz → **mainframe aleyhine tutucu**. Üst sınır: kalem sıfırlansa bile oran 2,05'ten ~1,87'ye iner, yön değişmez.
- Açık kalan: x86 orta değeri için bağımsız kaynak.

**Veri / kaynak:** model `cm.nonprod_cost`; Demo Case 1.

**Tasarım gerekçesi:** Tutuculuğun yönü yazılır; okuyucu hangi tarafın lehine yuvarlandığını bilir.

**Konuşmacı notu:** "Mainframe'in burada hafif cezalandırıldığını biliyoruz ve yazıyoruz; kalemin tamamı toplamın %9'u."

---

### Slayt KB-15.1 — Fiyat dönemi ve fiyat modları

**Kullanılan veri**

| Bileşen | 2025-mid (ana) low / mid / high | 2026-Q3 (duyarlılık) low / mid / high | Kaynak |
|---|---|---|---|
| DRAM $/GB | 3,0 / **4,0** / 5,5 (64 GB DDR5 ~$255) | 16 / 35 / 53 (64 GB ~$1.000 sözleşme; $2.245 / $3.400 perakende) | [PCSP2026-Server], [CapCompute-RAM], [Bacloud2026-RAM], [TrendForce2026-DDR5] |
| NVMe $/TB | 80 / **115** / 180 (30 TB sınıfı) | 300 / 753 / 1.172 | [PCSP2026-SSD] |

Mainframe fiyat yaşları (`--price-vintages`): AWLC 2004, TS7700 2006, z16 / DS8900F 2022, ücret 2025, S3 / elektrik 2026.

**Türetme**

```
düğüm_net = (şasi $12.000 + çekirdek × $130,4 + NIC/HBA $2.000) × (1 − 0,35)     ← liste kalemleri, indirim bir kez
          + bellek_GB × DRAM $/GB(dönem) + 1,92 TB boot × NVMe $/TB(dönem)        ← piyasa fiyatı, indirim yok
bellek_GB = max(128, 8 × çekirdek)
```

- Kural (E kararı): ana senaryo `PRICE_EPOCH` = **2025-mid** (şok öncesi, iki tarafın çapaları aynı dönemde); 2026-Q3 duyarlılık. Bellek ve NVMe ayrı aralık parametresi değil (tornado'da çift sayım olmasın).

**Veri / kaynak:** yukarıdaki tablo; `common_model.PRICE_EPOCHS`; [Intel-Xeon6548Yplus]; [Gray2005] (fiyat/performans yılda ~%68).

**Tasarım gerekçesi:** İki tarafın fiyatları farklı dönemlerden gelirse sonuç fiyat döneminin eseri olur.

**Konuşmacı notu:** "Mainframe fiyatları 2022 ve öncesinden. x86'yı 2026 şok fiyatlarıyla ölçseydik karşılaştırma döneme göre yanlı olurdu."

---

### Slayt KB-15.2 — KB-15: örnek hesap, iki fiyat modu, düzeltme

**Örnek (2×8c düğüm):**

```
liste kalemleri = (12.000 + 16 × 130,4 + 2.000) × 0,65   = $10.456
2025-mid        = 10.456 + 128 × 4,0 + 1,92 × 115         = $11.189
2026-Q3         = 10.456 + 128 × 35  + 1,92 × 753         = $16.382   (+%46)
10K TPS etkisi  : x86 $57,65 → $57,98/TPS (+%0,6); mainframe değişmiyor (IBM'in tepkisi bilinmiyor: sınırlılık)
```

- İki fiyat modu (Emirhan'ın önerisi, 2026-11-02): kaynaklı set · `--prices dosya.json` (verilen fiyat aralıktan çıkar, tornado'da sabit).
- **Karar E (b), Emirhan, 2026-11-16.**
- **Düzeltme (x86 §17, #3):** R760'ın Dell fiyatına ±%20 kalibrasyonu yapılamadı (kaynak yapılandırmayı vermiyor, $53.250 "amiral" R760); yalnızca bant kontrolü: 2×32c, 1 TB, 8 × 3,84 TB için liste eşdeğeri 2025-mid $29.975, 2026-Q3 $81.318.

**Veri / kaynak:** model `node_net_capex`; kopruler_v1 KB-15; x86 dokümanı §4.2–4.3, §13.4.

**Tasarım gerekçesi:** E kararı x86 aleyhine bir yanlılığı düzeltir (şok fiyatlarını yalnızca x86'ya yüklememek).

**Konuşmacı notu:** "Düğüm fiyatı %46 artıyor ama toplam yalnızca %0,6; çünkü donanım x86 maliyetinin küçük bir parçası. Şok asıl veri hacmi ekseninde görünür."

---

### Slayt KB-16.1 — Zaman ve finansman (NPV)

**Kullanılan veri**

| Parametre | Değer | Aralık | Dayanak |
|---|---|---|---|
| İskonto oranı r | %7 | %5 / %7 / %10 (ayrı tarama) | piyasa %6,96, bilgisayar hizmetleri %7,83, bankalar %4,98 [Damodaran2026-WACC] |
| NPV_TPS_GROWTH | 0,10 | 0 / 0,05 / 0,10 / 0,20 | senaryo girdisi |
| SW_PRICE_ESCALATION | 0,03 | 0–0,06 | IBM Z yazılımı 2026 +%6 [Schneider2026-IBMPrice] |
| HW_SERVICE_ESCALATION | 0,03 | 0–0,06 | IBM TLS +%4–6 |
| WAGE_ESCALATION | 0,033 | 0,025–0,045 | [BLS2026-ECI] |
| ENERGY_ESCALATION | 0,04 | 0,015–0,056 | [EIA-EPM-5.3] |
| TFP büyüme fiyatı (MF'ye özgü) | 0,5 | — | "IBM mentions 50% discount for growth MSUs" [Kyne2022-TFP] |

**Türetme**

```
NPV = Σ_y [capex_y / (1 + r)^(y−1) + opex_y / (1 + r)^y] − kalan değer / (1 + r)^5
seviyelendirilmiş $/TPS-ay = NPV / Σ_y [12 × TPS_y / (1 + r)^y]
```

- 5 yıl; capex yıl başında, opex yıl sonunda; kalan değer 0; kapasite yalnızca yükselir. Teknoloji yenilemesi (z17 / yeni sunucu nesli) iki tarafta birlikte dışarıda. **r köşe senaryolarına girmez.**

**Veri / kaynak:** yukarıdaki tablo; v3 §9.10; x86 dokümanı §15.

**Tasarım gerekçesi:** Yüksek r mainframe'i hep ucuz gösterir (capex'i önde, opex'i büyük); köşe senaryosuna girseydi "low = mainframe lehine" tanımını bozardı.

**Konuşmacı notu:** "İskonto oranı bir belirsizlik değil, kurumun sermaye maliyeti; iki tarafta aynı olmak zorunda."

---

### Slayt KB-16.2 — KB-16: örnek hesap ve tutarlılık

**Örnek (10K TPS başlangıç, yılda %10 büyüme, r = %7, 5 yıl):**

```
payda = Σ_{y=1..5} 12 × 10.000 × 1,1^(y−1) / 1,07^y         = 593.085 TPS-ay
Mainframe: NPV $71,01M / 593.085 = $119,73 /TPS/ay   (kademe yolu 524 → 527 → 530 → 534 → 537)
x86:       NPV $34,45M / 593.085 = $58,09  /TPS/ay
```

| Ufuk | Mainframe | x86 |
|---|---|---|
| 3 yıl | $125,12 | $58,14 |
| 5 yıl | $119,73 | $58,09 |
| 10 yıl | $115,57 | $58,53 |

- Tutarlılık testi iki modelde: r = 0, büyüme 0 → NPV = 60 × statik aylık.
- Mainframe'in seviyelendirilmiş maliyeti ufuk uzadıkça düşer (1. yıl capex'i yayılır); x86'nınki neredeyse sabit (%97'si personel).

**Veri / kaynak:** Demo Case 10; kopruler_v1 KB-16; v3 §9.10.4; x86 dokümanı §15.

**Tasarım gerekçesi:** Artış oranları belirsiz fiyatlardır, aralığa girer; iki tarafın artış sınıfları aynı (x86 abonelikleri yazılım sınıfında).

**Konuşmacı notu:** "NPV statik sonucu değiştirmiyor; zaman değeri hesaba katıldığında da oran ~2."

---

### Slayt KB-17.1 — Enerji ve tesis

**Kullanılan veri**

| Parametre | Değer | Dayanak |
|---|---|---|
| Elektrik fiyatı (ortak) | $0,12/kWh | [ASSUME]; artış KB-16 |
| Mainframe frame gücü | 30 kW / frame (20–40 kW aralığının ortası) | [Alibaba-MFPrice] |
| DS8910F / nesne depolama | 2,2 kW / 1,5 kW-PB | üretici tepe güçleri |
| x86 platform tabanı | 220 W (DL380 Gen12 boşta) | [SPECpower-2025Q1] (DL380 Gen12 924 / 220 W; SR650 V4 782 / 218 W; R770 943–960 W) |
| x86 CPU | 250 W / 32 çekirdek = 7,8 W / çekirdek | [Intel-Xeon6548Yplus] |
| X86_POWER_CONFIG_UPLIFT | 1,1 / 1,25 / 1,4 | [ASSUME] SPECpower az bellek ve diskle ölçülür |

**Türetme**

```
Mainframe: enerji = frame × 30 kW × $0,12 × 730 sa
x86:       düğüm_kW = (220 W + çekirdek × 7,8 W) × 1,25 / 1000;   enerji = Σ düğüm_kW × $0,12 × 730
```

- PUE, raf alanı ve storage ağı iki tarafta da dışarıda; AWS S3 hattı istisna (seçenek onsuz var olamaz).

**Veri / kaynak:** yukarıdaki tablo; v3 §7.4; x86 dokümanı §4.4.

**Tasarım gerekçesi:** Simetri: mainframe tepe güç kullandığı için x86'da da %100 yük değeri.

**Konuşmacı notu:** "Enerji iki tarafta da toplamın binde birkaçı; ama aynı fiyat ve aynı tepe-güç kuralıyla sayılıyor."

---

### Slayt KB-17.2 — KB-17: örnek hesap ve sınırlılık

**Örnek (10K TPS):**

```
Mainframe M1: 1 frame × 30 kW × 0,12 × 730               = $2.628 / ay   (M3: 2 frame → $5.256)
x86 X1:       2×8c düğüm = (220 + 16 × 7,8) × 1,25 = 431 W
              5 düğüm (3 DB + 2 uygulama) × 0,431 × 0,12 × 730 = $189 / ay
```

- Sınırlılık (mainframe): 39 CP üstü kademeler birden fazla drawer/raf ister; enerji frame başına sabit sayıldığı için büyük kademelerde eksik. IBM z16 IMPP resmî güç değerleri eklenmeli.
- PUE kapsam dışı olduğu için soğutma iki tarafta da yok; oranlar etkilenmez, mutlak düzey hafif düşük.

**Veri / kaynak:** model `monthly_cost` (energy), `node_power_kw`; v3 §7.4; x86 dokümanı §4.4.

**Tasarım gerekçesi:** İki tarafta birlikte dışarıda bırakılan kalem farkı değiştirmez; projenin kapsam kuralı.

**Konuşmacı notu:** "Enerji sonucu etkilemiyor; ama bunu varsaymadık, hesaplayıp gösterdik: toplamın %0,2'si ve %0,03'ü."

---

### Slayt KB-18.1 — Belirsizlik ve çıktı biçimi

**Kullanılan veri:** her kaynakla daraltılamayan parametrenin low / mid / high üçlüsü (mainframe `RANGE_PARAMETERS`, x86 `X86_RANGE_PARAMETERS`); ortak parametreler (personel eğrisi, ücret, saha olayı, u, RANGE_READ_WEIGHT, storage/yedek fiyatları) `common_model`'de tek sahipli.

**Türetme**

```
köşe senaryoları : her parametre aynı uçta (low = o platformun lehine)
tornado          : diğerleri mid iken tek parametre low → high
eşleştirilmiş    : platforma özgü parametreler zıt uçlarda, ortak parametreler iki tarafta AYNI düzeyde
```

| Senaryo (10K TPS) | Mainframe $/TPS | x86 $/TPS | Oran | Başabaş |
|---|---|---|---|---|
| x86 lehine | 387,27 | 56,94 | 6,80 | 6,89 |
| **orta** | **117,92** | **57,65** | **2,05** | **2,07** |
| mainframe lehine | 74,48 | 61,91 | 1,20 | 1,22 |
| ortak low | 83,25 | 24,05 | 3,46 | 3,61 |
| ortak high | 192,23 | 130,99 | 1,47 | 1,47 |

- Sonuç bir **crossover bölgesi**; eksenler TPS, veri hacmi, availability hedefi (`tools/kazanan_haritasi.py`). Ek çıktılar: başabaş personel oranı · personel hariç TCO · personel oranı 1,25 / 2,0.

**Veri / kaynak:** Demo Case 10; kopruler_v1 KB-18; x86 dokümanı §14, §16.3.

**Tasarım gerekçesi:** Yayımlanmamış fiyatlar karşısında tek sayı yanıltıcı kesinlik verir; bölge, okuyucunun kendi koşullarını yerleştirebileceği bir harita.

**Konuşmacı notu:** "Mid'de oran 2,05; mainframe lehine bütün belirsizliklerle 1,20; x86 lehine 6,80. Bu bir nokta değil, bir harita."

---

### Slayt KB-18.2 — Örnek: eşleştirilmiş senaryoda oran tersine dönüyor; önerilerin yönü dengeli

**Örnek (mainframe lehine senaryo, ortak parametreler mid):**

| TPS | Mainframe | x86 | Oran |
|---|---|---|---|
| 10.000 | $74,48 | $61,91 | 1,20 |
| 30.000 | $50,85 | $58,99 (Oracle'a zorlanır) | **0,86** |
| 50.000 | $43,06 | $53,44 | **0,81** |

| Karar | Düzelttiği yanlılık | Yanlılık kimin lehineydi | Düzeltmenin etkisi |
|---|---|---|---|
| F (aralık okumaları) | Mainframe işlemi olduğundan hafif ölçülüyordu | mainframe | mainframe pahalanır (+%23) |
| P (ortak personel eğrisi) | Eski kuralda x86 personeli sunucu saatinden ~0 çıkıyordu | x86 | x86 pahalanır |
| C (uygulama katmanı) | x86'da işlem yöneticisinin karşılığı yoktu | x86 | x86 pahalanır |
| N (x86 üretim dışı) | x86 dev/test aralığı tanımsızdı | x86 | x86 pahalanır |
| U (x86 kullanım tavanı) | Literatürün %15–20 ucu çift sayımla ana senaryoya girecekti | mainframe | x86 ucuzlar |
| E (fiyat dönemi) | 2026 şok fiyatları yalnızca x86'ya yüklenecekti | mainframe | x86 ucuzlar |
| K (x86 köprüsü) | Tek, belgelenmemiş çapa | yönsüz | aralık genişler (60–120) |
| Değ #10 (platform kesintisi, M3 paritesi, PG desteği) | Platform kesintisi yalnızca mainframe'de sayılıyordu; M3'e tek siteli değer veriliyordu | x86 | %99,999 + RPO 0'da yalnızca mainframe kurulur |

- Sonuç: kararlar bir tarafı sistematik olarak kayırmıyor; iki yöndeki yanlılıklar da düzeltildi.

**Veri / kaynak:** Demo Case 12; kopruler_v1 KB-18 son madde; karar kaydı §0.3; Değerlendirme #10.

**Tasarım gerekçesi:** Bir karşılaştırma çalışmasının güvenilirliği, düzeltmelerin yönünün dengeli olmasına bağlı; bunu tablo halinde göstermek iç geçerliliği savunur.

**Konuşmacı notu:** "Hocanın en olası sorusu 'tarafsız mısınız?'. Cevabımız bu tablo: yanlılıkları kimin lehine olduğuna bakmadan düzelttik; F, U ve E mainframe lehine olanları, P, C, N ve Değ #10 x86 lehine olanları kaldırdı."
