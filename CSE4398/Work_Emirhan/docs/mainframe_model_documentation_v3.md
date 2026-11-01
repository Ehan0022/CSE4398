# Mainframe (Scale-Up) Modelinin Detaylı Dokümantasyonu — v3

*IBM z16 A01 (3931) · compute kapasitesi, latency, availability, yıllık simülasyon, Capacity-on-Demand ve Tailored Fit Pricing*

Bu doküman mainframe modelinin **güncel halini** anlatır: hangi veri hangi kaynaktan alındı, nasıl işlendi, modele nasıl girdi. Değişikliklerin tarihçesi ve gerekçeleri `PROJECT_LOG.md` dosyasındadır. Önceki sürüm (`mainframe_model_documentation_v2.md`) tarihsel kayıt olarak değiştirilmeden tutulur.

Etiketler: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** resmî veriden hesaplanmış, doğrulaması belirtilmiş değer · **(doğrulanmalı)** kaynakla henüz teyit edilmemiş bilgi.

## 1. Modelin Amacı ve Kapsamı

### 1.1. Cevaplanan Soru

Verilen bir iş yükü (throughput, işlem karmaşıklığı, latency hedefi, availability hedefi) için, bu iş yükünü karşılayan minimum maliyetli feasible IBM z16 A01 konfigürasyonu hangisidir ve aylık/yıllık maliyeti nedir?

### 1.2. Mevcut Kapsam

- z16 A01'in 317 kapasite kademesinin tamamı (Bölüm 3)
- Benchmark tabanlı kapasite köprüsü: PCI başına TPS (Bölüm 4)
- İşlem karmaşıklığı (RNI) çarpanı
- Per-CP M/M/1 kuyruğu + sabit I/O gecikmesiyle latency feasibility (Bölüm 5)
- IBM Z Resiliency 4-model availability çerçevesi (M1–M4) (Bölüm 6)
- Kademe başına resmî MSU ile sub-capacity yazılım faturası, donanım amortismanı, bakım, enerji (Bölüm 7)
- Yıllık simülasyon: 8.760 saatlik profil ve üç donanım edinim/fiyatlama stratejisi: Permanent, Base + On/Off CoD ve Tailored Fit Pricing (base + capacity corridor + CoD); On/Off CoD'nin resmî sınırları (Bölüm 8)

### 1.3. Kapsam Dışı

- **z16 A02 / AGZ (makine tipi 3932, rack-mount modeller).** A01'den ayrı bir donanım ailesi; 156 kapasite seviyesi ve Max5/16/32/68 özellikleri var (SG24-8952). Model şu an yalnızca A01'i kapsıyor. Düşük TPS bölgesinde mainframe'in taban maliyetini belirleyebilecekleri için tezde ayrıca belirtilmeli; ileride eklenebilir.
- **3931-400:** Yalnızca Coupling Facility (CF) için kullanılan, MSU derecesi olmayan kapasite ayarı.
- **Messaging (IBM MQ):** proje kararıyla iki tarafta da kapsam dışı.

### 1.4. Henüz Modele Eklenmemiş Bileşenler

CICS TS ve Db2 for z/OS lisansları, DS8900F storage, GDPS'in ayrı kalem olarak modellenmesi, operasyon personeli, zIIP, CBU (DR kapasitesi), stokastik arıza modeli. Bkz. Bölüm 11.

## 2. Modelin Girdi ve Çıktıları

### 2.1. Mevcut Girdiler

| **Parametre** | **Açıklama** | **Tipik aralık** |
|---|---|---|
| tps | Saniyedeki işlem sayısı | 1.000 – 1.500.000 |
| rni | İşlem karmaşıklığı (low/average/high) | low / average / high |
| latency_ms + percentile | Hedef latency | ör. p99 < 200 ms |
| availability | Hedef uptime | 0.999 – 0.99999999 |
| [yıllık] preset | Workload preset adı | steady_oltp / retail_bursty / batch_heavy |
| [yıllık] avg_tps + peak_ratio + peak_days | Custom workload tanımı | ör. 50K TPS, 3.5×, 20 gün |

Projenin 8 girdisinden data_volume_tb, data_growth_pct, rpo_seconds ve rto_minutes henüz modele bağlı değil (storage ve DR adımlarıyla gelecek).

### 2.2. Çıktılar

Statik mod (tek nokta sorgu):
- Seçilen z16 kademesi (örn. 3931-436) ve topoloji (M1/M2/M3/M4)
- Tam-hız CP eşdeğeri, utilization, dinamik utilization tavanı, tahmini percentile latency
- Aylık maliyet dökümü: yazılım + donanım + bakım + enerji

Yıllık mod (workload simülasyonu):
- Seçilen strateji (Permanent, Base + On/Off CoD veya Tailored Fit Pricing) ve diğer iki stratejinin en iyi sonuçları
- Base kademe, drawer özelliği, corridor tavanı, CoD tepe kademesi ve CoD gün sayısı
- Yıllık maliyet dökümü: yazılım (R4HA veya consumption), donanım + bakım + enerji, corridor kullanımı, On/Off CoD
- Utilization istatistikleri
- CSV: 8.760 satır saatlik + 12 satır aylık

## 3. Kademe Tablosu — z16 A01'in 317 Kapasite Ayarı

### 3.1. Yapı

IBM z16 A01 317 kapasite seviyesi sunar: 7xx serisinde 1–200 tam-hız CP (200 seviye) ve ilk 39 CP için üç alt-kapasite serisi (4xx, 5xx, 6xx; 3 × 39 = 117 seviye) [SG24-8950]. 99'un üzerindeki CP sayıları iki karakterli kodla yazılır: A0 = 100, B0 = 110, …, I0 = 180, J0 = 190, K0 = 200 [EXHIBIT]. Fiziksel özellikler Max39, Max82, Max125, Max168 ve Max200'dür.

Kademe tablosu kodun içinde değil, ayrı bir veri dosyasındadır: `data/z16_a01_capacity.csv`. Her satır: model, seri, CP sayısı, PCI, MSU, LSPR Low/Average/High ve PCI ile MSU'nun kaynağı. Tablo, ham IBM verilerinden `src/tools/build_z16_capacity_table.py` ile üretilir; ham dosyalar `data/raw/` altındadır. Böylece her değer kaynağıyla satır satır karşılaştırılabilir ve tablo yeniden üretilebilir.

### 3.2. Doğrudan Resmî Kaynaktan Gelen Değerler (120 kademe)

4xx, 5xx ve 6xx serilerinin 1–39 CP'lik tüm satırları ile 3931-701, 702, 703 satırları IBM'in LSPR ITRR tablosundan alındı [LSPR]: PCI, MSU ve Low/Average/High RNI oranları (System z9 2094-701 = 1,00 bazlı, çok imajlı ölçüm; sayfa notu "current as of July 2026").

PCI ("Processor Capacity Index"), IBM'in "MIPS" için kullandığı addır ve LSPR oranının sabit bir katıdır: bilinen satırlarda ortalama **559,8 PCI / LSPR birimi**.

### 3.3. Türetilen Değerler: 7xx, 4–200 CP (197 kademe) [DERIVED]

Bu kademeler için IBM'in resmî MSU değerleri mevcut [EXHIBIT], ancak PCI değerlerine kamuya açık LSPR sayfasından erişilemedi (sayfa erişimde 3931-703 satırında kesiliyor). PCI bu yüzden MSU'dan türetildi:

- Bilinen 120 satırda **MSU/PCI oranı PCI'nin düzgün, azalan bir fonksiyonu**: küçük kademelerde ~0,125'ten başlayıp ~33.000 PCI'dan itibaren **0,11723**'te sabitleniyor (3931-632: 0,117222; 3931-639: 0,117228).
- Bu oran eğrisi bilinen satırlardan kurulur (5 noktalı hareketli ortalama + doğrusal ara değerleme; 33.000 PCI üstünde sabit) ve PCI = MSU / oran(PCI) sabit nokta iterasyonuyla çözülür.

**Doğrulama:**

| Test | Sonuç |
|---|---|
| Birini dışarıda bırak (bilinen 120 satır) | maks. hata %1,07, ortalama %0,09 |
| 3931-7K0 (200-way), bağımsız kaynak [STINE]: 215.089 PCI | Türetilen 215.099 PCI, fark **%0,004** |
| Önceki sürümdeki (z/VM LSPR tablosundan alınmış) 7xx oranları | 704: 14,73 / 14,71 · 718: 54,02 / 54,06 · 726: 72,88 / 72,88 · 732: 86,89 / 86,89 |

Yöntem, IBM'in MSU derecelendirmesinin büyük kademelerde kapasiteyle orantılı olmasına dayanır. 7K0 doğrulaması bunun 200-way'e kadar geçerli olduğunu gösteriyor. 7xx 4–200 için LSPR Low/High oranları türetilmedi (tabloda boş).

### 3.4. Kaynak Sayfalarına İlişkin Notlar

- Önceki sürümde kullanılan LSPR sayfası (node/6953823) **z/VM 7.2** tablosuydu ve 32 CP'de kesiliyordu. "128 kademe" bilgisi ve ~250K TPS'lik yapay tek-sistem tavanı buradan geliyordu. Ortalama oranlar z/OS ITRR tablosuyla aynı çıktığı için önceki sonuçlar oran düzeyinde etkilenmedi; ama kademe sayısı yanlıştı.
- ITRR sayfasında 3931 satırları sayfa dönüştürme sırasında "z17 ME2" başlığı altında görünüyor. Makine tipi 3931 z16 A01'e aittir; değerler A01 değerleridir.

## 4. Kapasite Köprüsü — Benchmark'tan PCI Başına TPS'e

### 4.1. Mantık

LSPR bütün nesilleri aynı baza (System z9 2094-701 = 1,00) göre ölçer ve PCI bu ölçeğin sabit bir katıdır. Bu yüzden bir benchmark'ın TPS'ini, benchmark'ın koştuğu sistemin PCI'sine bölmek, **nesilden bağımsız bir "PCI başına TPS" katsayısı** verir. Hem nesiller arası güç farkı hem de n-way ölçekleme kaybı (sublinearite) her kademenin PCI değerinin içinde zaten vardır; köprüde ayrıca uygulanmaz.

### 4.2. Benchmark Veri Noktaları

IBM Redpaper REDP-5320 (CICS TS V5.3, z13) [REDP] ve aynı sistemlerin PCI'si [LSPR-z13]:

| Sistem | CP | TPS | PCI | LSPR (avg) | TPS / PCI |
|---|---|---|---|---|---|
| 2964-718 | 18 | 174.000 | 21.579 | 38,55 | 8,063 |
| 2964-726 | 26 | 227.000 | 29.048 | 51,89 | 7,815 |

**TPS_PER_PCI = 7,939** (iki noktanın ortalaması, average RNI).

İki nokta arasındaki %3,1'lik fark, benchmark iş yükünün LSPR karışımından biraz daha kötü ölçeklendiğini gösterir. Model ortalamayı kullanır; fark köprünün belirsizlik aralığı olarak raporlanır.

### 4.3. Kademe Kapasitesi

ham_TPS(kademe) = PCI × 7,939 × RNI_çarpanı

| Kademe | PCI | Ham TPS (avg RNI) | %90 tavanda |
|---|---|---|---|
| 3931-401 | 280 | 2.223 | 2.001 |
| 3931-604 | 5.511 | 43.752 | 39.377 |
| 3931-701 | 2.253 | 17.887 | 16.098 |
| 3931-718 | 30.241 | 240.084 | 216.076 |
| 3931-739 | 57.733 | 458.344 | 412.509 |
| 3931-7A0 | 123.799 | 982.843 | 884.559 |
| 3931-7K0 | 215.099 | 1.707.676 | 1.536.908 |

Tam-hız CP eşdeğeri (bilgi amaçlı) = PCI / 2.253 (3931-701).

### 4.4. RNI (İşlem Karmaşıklığı) Çarpanı

- low = 1,25 [ASSUME]
- average = 1,00 (REDP benchmark noktası)
- high = 0,70 [ASSUME]

**Kavramsal not:** LSPR'nin Low/High RNI sütunları aynı iş için "nest intensity" (cache/bellek hiyerarşisi yoğunluğu) etkisini ölçer ve etki görece dar bir aralıktadır (ör. 3931-639'da low +%15, high −%10). Modeldeki RNI çarpanı ise buna ek olarak transaction başına iş miktarı farkını da temsil ediyor. İki kavramın ayrılması açık bir iş (Bölüm 11).

### 4.5. Akademik Notlar

- LSPR oranları IBM'in kendi iş yükü karışımında ölçülür. CICS/Db2 OLTP iş yükünün bu karışıma benzediği bir varsayımdır.
- z13 değerleri z/OS 2.2 LSPR tablosundan, z16 değerleri güncel ITRR tablosundan alındı. İkisi de aynı bazı kullanıyor, ama farklı z/OS seviyelerinde ölçülmüş olabilir.
- Köprünün tek kaynağı REDP-5320. Benchmark'ın transaction tanımı (Db2 çağrısı, I/O, transaction başına CPU süresi) henüz modele işlenmedi. Bu, iki taraf arasındaki transaction köprüsünün mainframe yarısıdır (Bölüm 11).

## 5. Latency Modeli — Per-CP M/M/1 + Sabit I/O Gecikmesi

### 5.1. Yaklaşımın Gerekçesi

Sabit bir utilization tavanı kullanıcının latency hedefini modele yansıtmaz. Model her kademe için kuyruk teorisinden bir maksimum utilization türetir: daha sıkı latency hedefi daha düşük utilization, dolayısıyla daha büyük ya da daha hızlı CP'li bir kademe gerektirir.

### 5.2. Endüstri Pratiği ile Uyum

Mainframe dünyasında WLM latency'yi percentile bazında ifade eder (örneğin bir CICS service class hedefi "işlerin %90'ı 0,8 saniye içinde") ve RMF SMF 72.3 / SMF 110.1 kayıtlarıyla ölçer. Model aynı percentile tabanlı yaklaşımı kullanır.

### 5.3. Formül

Sunucu = fiziksel CP. CP başına CPU servis süresi:

E[X_cpu] = c / ham_TPS    (c = kademenin fiziksel CP sayısı)

Alt-kapasite (4xx/5xx/6xx) CP'leri daha yavaş olduğundan E[X_cpu] daha büyüktür. Aynı toplam kapasitede alt-kapasite kademesi daha uzun CPU süresi, dolayısıyla daha kötü yanıt süresi verir.

Tutucu kuyruk: c adet bağımsız M/M/1 kuyruğu, her birine λ/c yük. Paylaşımlı kuyruktan (M/M/c) daha kötü yanıt verir, yani bir üst sınırdır.

R_cpu(p) = E[X_cpu] × 1/(1 − ρ) × ln(1/(1 − p))

Sabit I/O gecikmesi: D_io = IOPS_PER_TX[rni] × IO_SERVICE_TIME (low 5, average 10, high 20 I/O; 0,3 ms/I/O)

R(p) = D_io + R_cpu(p)

ρ_max = min( 1 − E[X_cpu] · ln(1/(1−p)) / (hedef − D_io) , 0,90 )

Hedef ≤ D_io ise ya da boş sistemdeki CPU süresi bile bütçeyi aşıyorsa kademe infeasible olur (ρ_max = 0).

### 5.4. Basitleştirmeler ve Sınırlamalar

- Operasyonel tavan (0,90) her zaman geçerli. Latency hedefi tavanı yalnızca düşürebilir; daha sıkı SLA hiçbir zaman daha ucuz sonuç vermez.
- IOPS_PER_TX ve IO_SERVICE_TIME = 0,3 ms [ASSUME]. DS8900F + FICON/zHPF için sektör aralığı ~0,1–0,5 ms. Tüm I/O'lar sıralı/senkron sayılır (tutucu).
- Network (iç fabric), lock/latch beklemesi ve buffer pool isabet oranı modellenmez. Clustered taraf aynı yapıyı (aynı kuyruk ailesi + D_io + ağ gecikmesi) kullanmalıdır.

### 5.5. Davranış

Latency hedefi 3–500 ms aralığında, 3 RNI × 7 TPS seviyesi (2K–1M) için tarandı. Maliyet hiçbir senaryoda hedef sıkılaştıkça azalmadı. Gözlenen davranış:
- 50 ms ve üstü hedeflerde seçilen kademe latency'siz durumla aynı.
- 20 ms ve altında tavan düşer; model yavaş alt-kapasite CP'lerinden daha hızlı CP'li kademelere kayar. Örnek: 50K TPS avg RNI'da latency'siz 3931-436 (36 yavaş CP, p99 ≈ 29 ms), 20 ms hedefte 3931-509, 5 ms hedefte 3931-704.
- Hedef D_io'ya yaklaştığında infeasible olur (avg RNI'da 3 ms, high RNI'da 6 ms).

## 6. Availability Modeli — IBM Z Resiliency 4-Model

### 6.1. Yaklaşım

Mainframe'de availability tek değişken değil; katmanlı bir mimari karardır. Yeni model bu katmanları doğrudan modeller.

### 6.2. IBM'in 4-Model Resiliency Çerçevesi

IBM Resiliency Redbook SG24-8446 dört topoloji çerçevesi tanımlar. Saf tek-image (sysplex'siz) gerçek dünyada production'da bulunmadığı için dışarıda bırakıldı. Modellenen dört topoloji:

| **Kod** | **Açıklama** | **Yapısal özellikler** |
|---|---|---|
| M1 | Single-frame sysplex (ICF) | Tek mainframe + içinde ICF LPAR ile sysplex. Tek hardware riski; rolling IPL ile planlı kesintide fayda. |
| M2 | Multi-frame failover (peer sysplex) | 2 ayrı frame, ICF ile peer coupling, sync/async remote copy. Bir frame çökerse diğeri devralır. |
| M3 | Fault-tolerant + GDPS Metro/Global | 2 frame + GDPS otomasyonu + HyperSwap. RTO \< 1 saat. |
| M4 | GDPS Continuous Availability | Coğrafi olarak ayrı 2 site, GDPS CA. Hem planlı hem plansız outage maskelenir. |

### 6.3. İki Kaynaklı Availability Aralığı

Her topoloji için iki availability rakamı atanır: vendor tasarım hedefi (high) ve bağımsız endüstri ölçümü (low). Bu, modelin metodolojik dürüstlüğünün kalbidir.

Vendor tarafı: IBM Resiliency Redbook tasarım hedefleri

Redbook Section 2: Z RAS özellikleri %99.999 application availability hedefler; GDPS Continuous Availability ise %99.99999'a kadar çıkar. Topolojilere göre dağılım:
- M1: ~%99.9999 tasarım hedefi
- M2: ~%99.999999
- M3: ~%99.9999999
- M4: ~%99.99999999

Bağımsız taraf: ITIC Global Server Reliability Surveys

ITIC vendor sponsorluğu kabul etmeyen bağımsız bir analiz şirketidir; yıllık 1.200-1.950 işletmeden anketle gerçek müşteri uptime raporlarını toplar. Bulgular:
- 2020: IBM Z müşterilerinin %83'ü 5-6 nine başardı
- 2023: z13/z14/z15 ortalaması 7-8 nine
- 2024: z16 sahiplerinin %96'sı 9 nine uptime başardı

Bu rakamlar inherent server failure (hardware-only) kategorisindedir. Topoloji-spesifik ayrım vermez, dolayısıyla M1-M4'e dağıtım kısmen interpolasyondur.

### 6.4. Feasibility Tutucu Yaklaşımla

Önemli karar: feasibility kontrolü yalnızca low (ITIC bağımsız) rakamına karşı yapılır. High rakamı bilgi olarak çıktıda gösterilir ama feasibility'yi belirlemez. Bu, modelin vendor iddiasına değil gerçek müşteri verisine güvenmesini sağlar.

### 6.5. Planlı Kesinti İndirimi

Hem IBM hem ITIC rakamları hardware-only (planlı maintenance dahil değil) ölçer. Ancak gerçek son-kullanıcı SLA'sı planlı kesintileri de içerir. Precisely'nin yayınladığı endüstri kuralı: toplam downtime'ın yaklaşık %90'ı planlı outage'lardan kaynaklanır.

total_downtime = hardware_downtime × 10

effective_availability = 1 − total_downtime

Bu kural M1, M2 ve M3 için uygulanır. M4 (GDPS Continuous Availability) tanım gereği planlı outage'ı da maskelediğinden uygulanmaz — Redbook bu özelliği açıkça belirtir.

### 6.6. Effective Availability Aralıkları

Planlı indirim uygulandıktan sonra topolojilerin gerçek son-kullanıcı availability'leri:
- M1: %99.99 – %99.999
- M2: %99.9999 – %99.99999
- M3: %99.99999 – %99.999999
- M4: %99.99999 – %99.999999 (planlı dahil zaten)

### 6.7. Topoloji'nin Maliyete Etkisi
- M1: 1 frame, cost_multiplier = 1.0, software_premium = 1.0
- M2: 2 frame, cost_multiplier = 2.0, software_premium = 1.0 (ICF specialty engine, lisans etkisiz \[CFCC\])
- M3: 2 frame, cost_multiplier = 2.0, software_premium = 1.15 (GDPS Metro/Global) — \[ASSUME\]
- M4: 2 site, cost_multiplier = 2.0, software_premium = 1.30 (GDPS CA) — \[ASSUME\]

## 7. Maliyet Modeli

Aylık maliyet dört kalemden oluşur ve her kalemin veri güvenilirliği farklıdır.

### 7.1. Yazılım Lisansı (z/OS, sub-capacity)

z/OS, MSU bazlı aylık lisanslama (MLC) ile faturalanır. Bağımsız lisanslama kaynakları, tipik kurumsal bir mainframe (600–2.500 MSU) için aylık $15.000–80.000 lisans maliyeti raporluyor. Bu, MSU başına aylık yaklaşık $25–55'e denk geliyor; model orta değeri kullanır:

SOFTWARE_COST_PER_MSU_MONTH = $40 / MSU / ay [LIC]

Fatura sub-capacity kuralıyla kesilir. Faturalanan MSU, o ayın R4HA tepesinde tüketilen MSU'dur ve kurulu kapasiteyi aşamaz:

faturalanan_MSU = min(R4HA_yük / ham_TPS, 1) × kademe.MSU

Kademe MSU'su, kademe başına **resmî IBM değeridir** [LSPR / EXHIBIT]. Statik modda yük sabit olduğundan R4HA = TPS. Aylık yazılım maliyeti = faturalanan_MSU × $40 × topology.software_premium. GDPS primi M3 için ×1,15, M4 için ×1,30 [ASSUME]. ICF specialty engine olduğundan ek frame yazılım lisansını artırmaz [CFCC].

### 7.2. Donanım Amortismanı

Mainframe donanım fiyatları açık liste olarak yayınlanmaz. Birden çok bağımsız fiyat rehberinin verdiği aralık birleşik olarak ~\$500.000 (giriş seviyesi) ile ~\$10.000.000+ (tam kapasite, üretim grade) arasındadır. Modelde MIPS başına kabaca doğrusal kestirim:

HARDWARE_COST_PER_MIPS = \$200 / MIPS — \[PRICE → ASSUME\]

aylık donanım = kademe.PCI × \$200 / (5 yıl × 12 ay)

Doğrusal kestirim kabadır; gerçekte hacim indirimi ve kurulum maliyeti gibi etkenlerle eğri bükülür, ama yayınlanmış veri olmadığı için bu yapılan en savunulabilir basitleştirmedir. Frame sayısı (n_frames) cost multiplier olarak çarpan görür.

### 7.3. Bakım

Aynı fiyat rehberi bakımı yıllık donanım değerinin %10-%15'i olarak verir:

MAINTENANCE_RATE_ANNUAL = 0.125

Donanım amortismanıyla aynı çarpan yapısını izler ve frame sayısıyla çarpılır.

### 7.4. Enerji

Modern z15/z16 sistemleri frame başına 20-40 kW güç çeker. Modelde orta değer kullanılır:

POWER_KW_PER_SYSTEM = 30 kW \| ELECTRICITY_USD_PER_KWH = \$0.12

aylık enerji = 30 × 0.12 × 730 = \$2.628 / ay / frame

Frame sayısıyla çarpılır. Elektrik fiyatı ABD ticari ortalaması; coğrafyaya göre değişir.

**Not:** Enerji frame başına sabit 30 kW alınıyor. 39 CP'nin üzerindeki kademeler birden fazla CPC drawer'ı, büyük yapılandırmalar birden fazla rack gerektirir (Max82–Max200). Bu yüzden büyük kademelerde enerji eksik sayılıyor; resmî güç değerleri IBM z16 IMPP belgesinden alınmalı (Bölüm 11).

### 7.5. Toplam Aylık Maliyet

total = faturalanan_MSU × $40 × software_premium + (hardware_amort + maintenance + energy) × n_frames

Yazılım kalemi kapasite-MSU bazlı olduğu için frame sayısıyla çarpılmaz; donanım, bakım ve enerji çarpılır [CFCC].

### 7.6. Maliyet / TPS Eğrisi (mevcut varsayımlarla)

Statik mod, availability 0.999, average RNI:

| TPS | Kademe | Aylık toplam | $/TPS/ay |
|---|---|---|---|
| 2.000 | 3931-401 | $5.404 | 2,70 |
| 10.000 | 3931-601 | $16.962 | 1,70 |
| 50.000 | 3931-436 | $71.995 | 1,44 |
| 200.000 | 3931-627 | $275.587 | 1,38 |
| 800.000 | 3931-788 | $1.082.520 | 1,35 |
| 1.200.000 | 3931-7E7 | $1.623.183 | 1,35 |

25K TPS'in üzerinde eğri neredeyse düz. Sebep: donanım fiyatı PCI ile doğrusal, yazılım tek bir $/MSU ile tüketime orantılı. Ölçek ekonomisini (sabit taban maliyet, azalan birim fiyatlı MLC kademeleri) içeren gerçek maliyet yapısı bir sonraki adımda modellenecek (Bölüm 11).

## 8. Yıllık Simülasyon — Workload Profile ve Fiyatlama Stratejileri

### 8.1. Yaklaşımın Gerekçesi

Statik tek-nokta sorgusu "şu anda şu yük için ne lazım" sorusunu cevaplar; ama gerçek bir kurumun maliyetini belirleyen şey yılın saatleri arasında değişen trafik desenidir. Tek bir ortalama TPS sayısı R4HA peak'i ve dolayısıyla yazılım faturasını gizler. Bir saatlik patlama tüm ayın yazılım faturasını yukarı çekebilir.

Ayrıca mainframe'in en karakteristik özelliklerinden biri Capacity on Demand'dir (CoD): peak günlerde geçici kapasite ekleme. Bu özellik, mainframe ekonomisini düşünüldüğünden çok daha esnek yapar — ve modelde temsil edilmezse mainframe haksız yere pahalı görünür.

### 8.2. Workload Profile Üretimi

8.760 saatlik deterministik TPS vektörü üretilir. Üç katmanlı desen:
- Günlük desen: sabah-öğlen peak (~14:00), gece dip (~03:00) — sinüs dalgası
- Haftalık desen: iş günleri 1.0×, hafta sonu 0.65×
- Yıllık peak günleri: deterministik dağılım, peak_avg_ratio çarpanıyla

Workload Preset'leri

| **Preset** | **peak/avg oranı** | **Tipik kullanım** |
|---|---|---|
| steady_oltp | 1.5×, 10 peak gün | Bankacılık core / kurumsal OLTP — düzgün trafik |
| retail_bursty | 3.5×, 20 peak gün | Perakende / e-ticaret — Black Friday, Noel |
| batch_heavy | 2.5×, 30 peak gün | Batch ağırlıklı — ay sonu, vergi dönemi |

### 8.3. R4HA (Rolling 4-Hour Average)

IBM MLC sub-capacity fiyatlandırması, her ay için en yüksek kayan 4-saatlik ortalama tüketimi (R4HA) baz alır. Yani kapasite sürekli değil, peak kullanım faturalanır. Model bu mekanizmayı doğrudan uygular:

r4ha\[i\] = mean(profile\[i-3 : i+1\]) \# 4-saatlik kayan ortalama

aylık R4HA peak = max(r4ha\[ay başlangıcı : ay sonu\])

Bu, neden saatlik simülasyon yaptığımızın kalbidir: günlük veya aylık ortalama R4HA'yı kaçırırdı.

### 8.4. Güncel IBM Z Donanım Edinim Modeli

IBM z15 ve sonrası için güncel ticari model üç katmanlıdır:

1. **Base (satın alınan, permanent) kapasite.** Müşterinin sahip olduğu kademe; donanım amortismanı ve bakım bu kapasite üzerinden işler.
2. **Capacity corridor (Tailored Fit Pricing for IBM Z Hardware, "Hardware Consumption Solution").** IBM'in tanımıyla "always-on, subscription-based corridor of pay-for-use capacity, on top of purchased capacity" [TFP-HW]. Corridor kapasitesi her zaman aktiftir; ücret, base'in üstünde **fiilen tüketilen MSU** üzerinden, SCRT ile saatlik ölçülerek kesilir. Boşta duran corridor kapasitesi ücretlendirilmez. Ön koşullar: z15 veya sonrası, z/OS genel amaçlı CP'ler, adanmış (dedicated) CP olmaması ve yazılım tarafında **Software Consumption Solution**. Corridor genişliği IBM'in iş yükü analiziyle belirlenir; IBM'in yayımlanmış maliyet çalışmasındaki örnek corridor, yeni iş yükünün %20'sidir [TFP-TCO].
3. **On/Off Capacity on Demand.** Corridor'u da aşan talep için geçici kapasite kaydı. 24 saatlik periyotlarla, o gün aktif edilen kapasite üzerinden faturalanır [COD].

Corridor fiyatı, corridor büyüklüğü için IBM'in yayımladığı genel bir kural ve corridor ile On/Off CoD'nin tam etkileşimi kamuya açık değildir; bunlar müşteriye özel sözleşmede belirlenir. Bu yüzden modelde parametre olarak durur ve duyarlılık analizine girer (Bölüm 8.8).

### 8.5. Geçici Kapasitenin Resmî Sınırları [COD]

SC28-7025'e göre geçici kapasite üç kısıta tabidir. Model her gün aktive edilen kademeyi (corridor tavanı dahil) bu kısıtlarla sınırlar:

| Kısıt | SC28-7025 | Modeldeki karşılığı |
|---|---|---|
| %100 kuralı | Geçici CP kapasitesi "up to 100% of the purchased capacity (active permanent plus unassigned permanent)" | Hedef kademe MSU ≤ 2 × base MSU |
| Kurulu kapasite | Geçici aktivasyon drawer ekleyemez; makine modeli değişemez | Hedef CP sayısı ≤ kurulu drawer özelliğinin sınırı (Max39/82/125/168/200) |
| Alt-kapasite kuralları | Geçici upgrade permanent alt-kapasite seviyesinin altına inemez, seviyeyi 5xx/4xx'e çekemez; 6xx'ten yalnızca 6xx'e (daha çok CP) veya 7xx'e geçilir | Hedef seri = base serisi ya da daha yüksek 6xx/7xx; CP sayısı azalamaz |

Kurulu drawer özelliği varsayılan olarak base kademeyi taşıyan en küçük özelliktir (boş drawer satın alınmaz). Model henüz drawer başına maliyet içermediği için daha büyük özellik seçimi bir karar değişkeni olarak açılmamıştır; bu, yol haritasındaki maliyet yapısı adımıyla birlikte gelecek.

Pratik sonuç: %100 kuralı küçük base'lerde bağlayıcıdır (ör. 3931-705 → en fazla 2 × 1.232 MSU), drawer sınırı ise drawer'ı dolduran base'lerde bağlayıcıdır (ör. 3931-735, Max39 üzerinde en fazla 3931-739'a, yani %11 ek kapasiteye çıkabilir). Yani "ne kadar geçici kapasite alınabilir" sorusunun gerçek cevabı çoğu durumda 2×'ten azdır ve base kademeye bağlıdır.

### 8.6. Üç Strateji

**Strateji A — Permanent.** Yılın peak saatini karşılayan en küçük feasible kademe satın alınır. Yazılım: aylık R4HA sub-capacity MLC.

**Strateji B — Base + On/Off CoD.** Daha küçük bir base kademe satın alınır. Her gün, günün tepe yükünü base karşılamıyorsa, bu tepeyi karşılayan en küçük izinli geçici kademe o gün için aktive edilir. Ücret:

CoD günlük = (aktif kademe PCI − base PCI) × (PCI başına aylık donanım maliyeti / 30) × COD_DAILY_MULTIPLIER

COD_DAILY_MULTIPLIER = 2,5 [ASSUME]. IBM gün başına fiyat yayımlamaz; çarpan, CoD'nin primli olması ama sürekli kapasiteden ucuz kalması mantığına dayanır. Yazılım: aylık R4HA (o ayın en büyük aktif kademesiyle sınırlı).

**Strateji C — Tailored Fit Pricing (base + corridor + CoD).** Base kademe satın alınır; corridor tavanı, base MSU × (1 + CORRIDOR_FRACTION) değerini karşılayan en küçük izinli kademedir ve yıl boyunca aktiftir. Corridor'u aşan günlerde On/Off CoD (corridor tavanının üstü için) devreye girer.

Corridor ücreti (saatlik) = max(0, min(tüketilen PCI, corridor PCI) − base PCI) × (PCI başına aylık donanım maliyeti / 730) × CORRIDOR_PREMIUM

Tüketilen PCI, yükün %100 kullanım eşdeğeridir (yük / (TPS_PER_PCI × RNI çarpanı)). Bu, IBM'in "base'in üstünde tüketilen MSU" ölçüsünün modeldeki karşılığıdır: base'in %90 operasyonel tavanı ile %100'ü arasındaki kullanım corridor kapasitesini aktif tutar ama base tüketimini aşmadığı için ücretlendirilmez. İsteğe bağlı sabit abonelik bedeli CORRIDOR_SUBSCRIPTION_RATE ile eklenebilir (varsayılan 0).

Yazılım (Software Consumption Solution) [TFP-SW]: R4HA yerine yıl boyunca tüketilen MSU-saat × efektif MSU-saat fiyatı. IBM efektif fiyatı müşterinin geçmiş 12 ayından belirler; model bunu gelir-nötr olarak kalibre eder: aynı profilin Permanent konfigürasyondaki R4HA faturası, aynı yılın tüketilen MSU-saatine bölünür. TFP_SW_DISCOUNT (varsayılan 0) bu fiyata uygulanan indirimdir. Gelir-nötr kalibrasyon nedeniyle TFP-SW'nin asıl avantajı (büyüme MSU'larının indirimli fiyatı, tepe cezası olmaması) tek yıllık ufukta görünmez; 5 yıllık ufuk adımında modellenecektir.

**Strateji seçimi.** Her availability-feasible topoloji için Strateji A'nın kademesi bulunur; ardından ortalama yükün en az 1,2 katını taşıyan [ASSUME] ve izinli en büyük geçici kademesi peak'i karşılayabilen her base kademe için B ve C simüle edilir. Her strateji için en ucuz sonuç tutulur ve üçü karşılaştırılır. Çok-frame topolojilerde geçici kapasite ücretleri tek frame için hesaplanır; ikinci frame yalnızca failover içindir ve onun geçici kapasitesi CBU konusudur (yol haritası).

### 8.7. Doğrulama Örneği

50K TPS ortalama yük, availability 0,999 (M1), average RNI, varsayılan parametreler:

| Preset | A: Permanent | B: Base + CoD | C: TFP | Kazanan, A'ya göre |
|---|---|---|---|---|
| steady_oltp | $1,395M (3931-516) | $1,427M (515, 261 gün CoD) | **$1,249M** (512 + corridor 516) | C, −%10,5 |
| retail_bursty | $2,949M (3931-624) | $2,204M (518 → 624, 20 gün) | **$2,201M** (518 + corridor 523 → 624) | C, −%25,3 (B ile fark %0,1) |
| batch_heavy | $2,178M (3931-616) | $1,770M (515 → 616, 30 gün) | **$1,662M** (512 + corridor 516 → 616) | C, −%23,7 |

Yorum:

- **Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanıdır.** steady_oltp'de günlük tepe base'i neredeyse her gün aşar; B bunu 261 gün CoD ile karşılamak zorunda kalır ve A'dan pahalıya gelir, C ise bu tepeleri tüketim bazlı corridor'la ucuza emer. retail_bursty'de maliyeti 20 günlük büyük tepeler belirler; B ve C neredeyse eşittir ve kazanan corridor fiyat varsayımlarına göre değişir (Bölüm 8.8).
- **%100 kuralı bağlayıcıdır.** retail_bursty'de peak kademe 3931-624 (3.059 MSU); bunu geçici olarak açabilmek için base en az 1.530 MSU olmalıdır. Model base'i 3931-518'e (1.560 MSU) çıkarır. Sınır uygulanmadan model 3931-515 (1.351 MSU) seçiyordu; bu, resmî kurala göre ulaşılamayan bir konfigürasyondu.
- Yazılım, yıllık toplamın %42–57'sidir ve en büyük tek kalemdir; donanım fiyatlama stratejisi yalnızca donanım kalemini yeniden dağıtır. Bu, maliyet/TPS eğrisinin düzlüğü sorununu tek başına çözmez.

### 8.8. Duyarlılık Analizi (Fiyatlama Varsayımları)

`python src/tools/pricing_sensitivity.py` kalibre edilmemiş fiyat parametrelerini tek tek tarar (50K TPS, M1). Yıllık toplamlar, milyon USD; kazanan kalın:

| Parametre (varsayılan) | Değer | steady_oltp A / B / C | retail_bursty A / B / C | batch_heavy A / B / C |
|---|---|---|---|---|
| CORRIDOR_PREMIUM (1,5) | 1,0 | 1,395 / 1,427 / **1,244** | 2,949 / 2,204 / **2,199** | 2,178 / 1,770 / **1,657** |
| | 4,0 | 1,395 / 1,427 / **1,275** | 2,949 / **2,204** / 2,212 | 2,178 / 1,770 / **1,686** |
| CORRIDOR_FRACTION (0,20) | 0,10 | 1,395 / 1,427 / **1,292** | 2,949 / **2,204** / 2,211 | 2,178 / 1,770 / **1,702** |
| | 0,50 | 1,395 / 1,427 / **1,218** | 2,949 / 2,204 / **2,174** | 2,178 / 1,770 / **1,632** |
| CORRIDOR_SUBSCRIPTION_RATE (0) | 0,25 | 1,395 / 1,427 / **1,289** | 2,949 / **2,204** / 2,248 | 2,178 / 1,770 / **1,701** |
| COD_DAILY_MULTIPLIER (2,5) | 1,5 | 1,395 / 1,398 / **1,249** | 2,949 / **2,167** / 2,175 | 2,178 / 1,740 / **1,635** |
| | 4,0 | 1,395 / 1,469 / **1,249** | 2,949 / 2,259 / **2,241** | 2,178 / 1,815 / **1,702** |
| TFP_SW_DISCOUNT (0) | 0,10 | 1,395 / 1,427 / **1,189** | 2,949 / 2,204 / **2,076** | 2,178 / 1,770 / **1,567** |

Sonuç: steady_oltp ve batch_heavy'de TFP'nin üstünlüğü tüm taranan aralıkta korunur. retail_bursty'de B ile C arasındaki seçim fiyat varsayımlarına duyarlıdır (fark ±%2 içinde); bu, gerçek sözleşme fiyatları olmadan "bursty iş yükü için TFP mi CoD mu" sorusuna kesin cevap verilemeyeceği anlamına gelir ve tezde böyle raporlanmalıdır. Permanent strateji, taranan hiçbir noktada kazanmaz.

### 8.9. Grafik-Hazır CSV Çıktısı

İki dosya üretilir, matplotlib/pandas ile doğrudan kullanılabilir:
- \<prefix\>\_hourly.csv — 8760 satır: hour, load_tps, capacity_tps, utilization, cod_active
- \<prefix\>\_monthly.csv — 12 satır: month, r4ha_peak_tps, software_cost, other_cost

## 9. Kod Yapısı ve Kullanım

```
Work_Emirhan/
  data/z16_a01_capacity.csv            317 kademe (üretilmiş tablo)
  data/raw/                            ham IBM verileri (kaynak ve erişim tarihi başlıkta)
  src/mainframe_model.py               model + CLI (yalnızca standard library)
  src/test_mainframe_model.py          tutarlılık testleri
  src/tools/build_z16_capacity_table.py  kademe tablosunu ham verilerden üretir
  src/tools/pricing_sensitivity.py     fiyatlama varsayımlarının duyarlılık analizi
```

### 9.1. Statik Mod

python src/mainframe_model.py --tps 50000 --availability 0.999 --rni average --latency-ms 200

### 9.2. Yıllık Mod

python src/mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000 --availability 0.999 --csv out

### 9.3. Yardımcı Modlar

- --demo: hazır 6 senaryo
- --calibration: kademe tablosu özeti, köprü katsayıları ve örnek kademeler

### 9.4. Testler

python src/test_mainframe_model.py — 9 test: latency monotonluğu, latency'nin sıkı hedefte bağlayıcı olması, kademe tablosunun bütünlüğü (317 satır, seri başına kesin artan PCI ve MSU), köprünün kendi z13 çapalarını %2 içinde ve 7K0 PCI'sini %0,5 içinde üretmesi, MSU faturasının kurulu kapasiteyle sınırlı olması, geçici kapasitenin (B veya C) avantajının burstiness ile artması, geçici hedeflerin SC28-7025 kurallarına uyması (%100, drawer, alt-kapasite; 735 → 739 ve 705 örnekleri), seçilen B/C konfigürasyonlarının bu kurallara uyması, TFP-SW fiyatının gelir-nötr olması ve corridor ücretinin CORRIDOR_PREMIUM ile artması.

## 10. Referanslar ve Kullanım Amaçları

### 10.1. Kapasite Tablosu ve Throughput Köprüsü

- **[LSPR]** IBM Z LSPR ITRRs (çok imajlı tablo, System z9 2094-701 = 1,00). 3931 4xx/5xx/6xx 1–39 CP ve 701–703 için PCI, MSU, Low/Average/High. https://www.ibm.com/support/pages/ibm-z-lspr-itrrs
- **[LSPR-z13]** IBM Z LSPR ITR zOSv2r2. Köprü çapaları: 2964-718 = 21.579 PCI (38,55), 2964-726 = 29.048 PCI (51,89). https://www.ibm.com/support/pages/node/6953815
- **[EXHIBIT]** IBM Mainframe Exhibit, Full Capacity MSUs, IBM z16 (3931), güncelleme 5/2/2025. 3931-701…7K0 resmî MSU değerleri ve A0–K0 kodlaması. https://www.ibm.com/downloads/documents/us-en/10a99803f42fd829
- **[STINE]** K. Stine, "IBM z16 Technical Overview", IBM Z Council, 2022. z16 200-way = 215.089 PCI (z15 190-way'e göre +%17); türetilen PCI değerlerinin bağımsız doğrulaması. https://ibm-zcouncil.com/wp-content/uploads/2022/05/z16-Technical-Overview-50M-KennyStine.pdf
- **[SG24-8950]** IBM Redbooks, "IBM z16 Technical Introduction" (2. baskı, 2023). A01'de 317 kapasite seviyesi (200 tam-hız + 117 alt-kapasite) ve Max39–Max200 özellikleri. https://redbooks.ibm.com/redbooks/pdfs/sg248950.pdf
- **[SG24-8952]** IBM Redbooks, "IBM z16 A02 and IBM z16 AGZ Technical Guide" (2023). Kapsam dışı bırakılan rack-mount modellerin tanımı. https://www.redbooks.ibm.com/redbooks/pdfs/sg248952.pdf
- **[REDP]** IBM Redpaper REDP-5320, "IBM CICS Performance Series: CICS TS V5.3 Benchmark on IBM z13" (Burgess, Mitchell, Moxey). 18 CP → 174.000 TPS, 26 CP → 227.000 TPS. https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf

### 10.2. Availability
- **\[REDBOOK\] —** IBM Redbook SG24-8446, "Getting Started with IBM Z Resiliency" (White, Coq). 4-model availability çerçevesinin (M1-M4) ve her topolojinin tasarım hedefleri/RTO-RPO değerlerinin temelidir. Modelin Topology sınıfının tüm yapısı bu kaynaktan alınmıştır. https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf
- **\[ITIC\] —** ITIC Global Server Reliability Surveys 2020-2024. Bağımsız endüstri anketleri (1.200-1.950 işletme/yıl); mainframe gerçek uptime ölçümleri. Her topolojiye atanan hw_low (alt sınır) rakamının kaynağıdır. Vendor iddiası ile bağımsız ölçümün ikili sunumunu sağlar. https://itic-corp.com/
- **\[PRECISELY\] —** Precisely, High Availability definition. Endüstri kuralı: toplam downtime'ın yaklaşık %90'ı planlı outage'lardan kaynaklanır. effective_availability hesabındaki ×10 çarpanının (planlı kesinti indirimi) kaynağıdır. https://www.precisely.com/glossary/high-availability-ha/

### 10.3. CoD ve Yıllık Simülasyon
- **\[COD\] —** IBM SC28-7025, "IBM Z and LinuxONE Capacity on Demand User's Guide". On/Off CoD'nin teknik yapısı (gün-bazlı faturalandırma, 24-saatlik aktivasyon periyodu, prepaid/postpaid modelleri) ve geçici kapasite sınırları (satın alınan kapasitenin %100'ü, kurulu kapasite, alt-kapasite seviye kuralları). Gün başına dolar fiyatı kapalı, premium çarpanı 2.5 \[ASSUME\]. https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf
- **\[CFCC\] —** IBM Coupling Facility Configuration Options (Raften), IBM Z Resiliency Redbook ve ilgili IBM dokümanları. ICF (Internal Coupling Facility) specialty engine olduğu için kapasite derecelendirmesini etkilemez ve yazılım lisansını artırmaz. M2 topolojisinin software_premium = 1.0 kalmasının (ek frame eklenmesine rağmen) gerekçesidir.

- **[TFP-HW] —** IBM Z Content Solutions, "Tailored Fit Pricing" (https://www.ibm.com/support/z-content-solutions/tailored-fit-pricing/). Hardware Consumption Solution'ın tanımı (always-on, subscription-based, pay-for-use corridor), ön koşulları (z15+, z/OS genel amaçlı CP, Software Consumption Solution, dedicated CP yok, RMF aralığı 1/3/5/15 dk). Ayrıca DBTA ve NetworkWorld duyuru haberleri: corridor kullanımı SCRT ile 1 saatlik çözünürlükte, fiilen tüketilen MSU üzerinden faturalanır.
- **[TFP-TCO] —** IBM IT Economics Consulting & Research, TFP for IBM Z Hardware maliyet çalışması (Mayıs 2021). Örnek corridor: 4.000 MSU'luk yeni iş yükü için %20 (800 MSU). CORRIDOR_FRACTION = 0,20 varsayılanının kaynağı. IBM sponsorlu bir çalışmadır; yalnızca yapı ve büyüklük örneği olarak kullanılır.
- **[TFP-SW] —** IBM TFP Software Consumption Solution fiyatlama özeti ve z/OS TFP dokümantasyonu: geçmiş 12 ayın MSU tüketiminden efektif MSU fiyatı, yıllık MSU taahhüdü (kullanılmayan MSU devreder), büyüme için indirimli fiyat, R4HA/tepe/capping yok. Modeldeki gelir-nötr kalibrasyonun gerekçesi.

### 10.4. Maliyet Verileri (Yarı-Kapalı)
- **\[PRICE\] —** Bağımsız mainframe fiyat rehberleri (electronics.alibaba buying guides serisi). z15/z16 donanım fiyat aralığı (\$0.5M-\$10M+), yıllık bakım donanım değerinin %10-15'i, alt ekonomik eşik ~150 MIPS. HARDWARE_COST_PER_MIPS = \$200 ve MAINTENANCE_RATE_ANNUAL = 0.125 değerlerinin kaynağıdır. Açık liste fiyatı olmadığı için kestirim.
- **\[LIC\] —** MLC/MSU lisanslama kaynakları (atonementlicensing.com, redresscompliance.com). Tipik kurumsal 600-2500 MSU → aylık \$15K-\$80K → ~\$25-55/MSU/ay aralığı. SOFTWARE_COST_PER_MSU_MONTH = \$40 (orta değer) bu kaynaktan.
- **\[PWR\] —** Aynı fiyat rehberi (electronics.alibaba) enerji ölçütleri. z15/z16 frame başına 20-40 kW; modelde POWER_KW_PER_SYSTEM = 30 kW (orta).

### 10.5. Teorik Temel

- **[QUEUE]** Kuyruk teorisi (per-CP M/M/1). Mainframe WLM/RMF response-time percentile metodolojisiyle uyumlu (SMF 72.3 / 110.1).

## 11. Modelin Bilinen Eksikleri ve Sonraki Adımlar

### 11.1. Kalibre Edilmemiş Parametreler [ASSUME]

- RNI çarpanları low 1,25 / high 0,70 (ve LSPR RNI kavramıyla ayrıştırılması)
- HARDWARE_COST_PER_MIPS = $200/PCI (doğrusal kestirim)
- SOFTWARE_COST_PER_MSU_MONTH = $40 (tek fiyat; gerçekte ürün başına kademeli)
- GDPS yazılım primi (M3 ×1,15, M4 ×1,30)
- COD_DAILY_MULTIPLIER = 2,5 ve base kademe için "≥ ortalama yükün %120'si" eşiği
- TFP: CORRIDOR_PREMIUM = 1,5, CORRIDOR_FRACTION = 0,20 (IBM örneğinden), CORRIDOR_SUBSCRIPTION_RATE = 0, TFP_SW_DISCOUNT = 0 (Bölüm 8.8'de taranır)
- IOPS_PER_TX ve IO_SERVICE_TIME = 0,3 ms
- ELECTRICITY_USD_PER_KWH = $0,12, POWER_KW_PER_SYSTEM = 30 kW

### 11.2. Yapısal Basitleştirmeler

- Enerji, büyük kademelerde drawer/rack sayısıyla ölçeklenmiyor (Bölüm 7.4 notu).
- Kurulu drawer özelliği base'i taşıyan en küçük özellik olarak sabit; drawer maliyeti yok, bu yüzden özellik seçimi karar değişkeni değil (Bölüm 8.5).
- Corridor genişliği base MSU'nun sabit bir oranı; IBM'de bu, iş yükü analiziyle müşteriye özel belirlenir.
- On/Off CoD kaydının 180 günlük süresi ve tek-aktif-kayıt kuralı modellenmiyor (simülasyonlarda en fazla 261 gün CoD görülüyor; bu, kayıt yenilemesi gerektirir).
- R4HA LPAR değil CPC toplamı üzerinden hesaplanıyor.
- Peak günler yıla eşit aralıklarla dağıtılıyor (gerçekte mevsimsel kümelenir); tek yıllık ufuk.
- Yedek frame tam kapasite ve tam maliyetle sayılıyor (CBU modellenmiyor).
- M4'ün availability kaynak etiketleri ters görünüyor; M3 ve M4'ün effective low değerleri aynı. RPO/RTO girdileri bağlı değil.

### 11.3. Yol Haritası (Değerlendirme #2, M3–M8)

- REDP-5320 iş yükü profilinin çıkarılması (transaction köprüsünün mainframe yarısı; D_io kalibrasyonu)
- Maliyet yapısı: donanımda taban + drawer + kapasite başına artış (drawer özelliğini karar değişkeni yapar), ürün başına kademeli MLC (z/OS, CICS, Db2), zIIP (TFP-HW zIIP corridor'u dahil)
- Availability: RPO/RTO bağlantısı, M4 düzeltmesi, DR frame için CBU
- DS8900F storage (data_volume_tb, data_growth_pct, RNI'dan IOPS)
- Personel ve GDPS ayrı kalem
- 5 yıllık ufuk + NPV, kümelenmiş peak dağılımı; TFP-SW büyüme fiyatı ve MSU taahhüdü
- (Opsiyonel) z16 A02 rack-mount modelleri
