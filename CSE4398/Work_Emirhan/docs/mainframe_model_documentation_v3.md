# Mainframe (Scale-Up) Modelinin Detaylı Dokümantasyonu — v3

*IBM z16 A01 (3931) · compute kapasitesi, latency, availability, storage (DS8900F), yıllık simülasyon, Capacity-on-Demand ve Tailored Fit Pricing*

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
- Storage katmanı: IBM DS8900F boyutlandırması (veri hacmi, IOPS, topolojiye bağlı kopya sayısı), maliyeti ve I/O gecikmesi; zHyperLink, zHPF/FICON, Metro/Global Mirror, Safeguarded Copy (Bölüm 8)
- Yıllık simülasyon: 8.760 saatlik profil ve üç donanım edinim/fiyatlama stratejisi: Permanent, Base + On/Off CoD ve Tailored Fit Pricing (base + capacity corridor + CoD); On/Off CoD'nin resmî sınırları (Bölüm 9)

### 1.3. Kapsam Dışı

- **z16 A02 / AGZ (makine tipi 3932, rack-mount modeller).** A01'den ayrı bir donanım ailesi; 156 kapasite seviyesi ve Max5/16/32/68 özellikleri var (SG24-8952). Model şu an yalnızca A01'i kapsıyor. Düşük TPS bölgesinde mainframe'in taban maliyetini belirleyebilecekleri için tezde ayrıca belirtilmeli; ileride eklenebilir.
- **3931-400:** Yalnızca Coupling Facility (CF) için kullanılan, MSU derecesi olmayan kapasite ayarı.
- **Messaging (IBM MQ):** proje kararıyla iki tarafta da kapsam dışı.

### 1.4. Henüz Modele Eklenmemiş Bileşenler

CICS TS ve Db2 for z/OS lisansları, GDPS'in ayrı kalem olarak modellenmesi, operasyon personeli, zIIP, CBU (DR kapasitesi), yedekleme için sanal teyp (TS7700), stokastik arıza modeli. Bkz. Bölüm 12.

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
| data_tb | Mantıksal Db2 veri hacmi (indeksler dahil), TB | 1 – 5.000 (varsayılan 20) |
| data_growth | Yıllık veri büyümesi | 0 – 0,5 (varsayılan 0,15) |

Projenin 8 girdisinden rpo_seconds ve rto_minutes henüz modele bağlı değil (DR adımıyla gelecek). IOPS kullanıcıya sorulmaz; TPS × RNI'ya bağlı IOPS/işlem olarak türetilir.

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

**Kavramsal not:** LSPR'nin Low/High RNI sütunları aynı iş için "nest intensity" (cache/bellek hiyerarşisi yoğunluğu) etkisini ölçer ve etki görece dar bir aralıktadır (ör. 3931-639'da low +%15, high −%10). Modeldeki RNI çarpanı ise buna ek olarak transaction başına iş miktarı farkını da temsil ediyor. İki kavramın ayrılması açık bir iş (Bölüm 12).

### 4.5. Akademik Notlar

- LSPR oranları IBM'in kendi iş yükü karışımında ölçülür. CICS/Db2 OLTP iş yükünün bu karışıma benzediği bir varsayımdır.
- z13 değerleri z/OS 2.2 LSPR tablosundan, z16 değerleri güncel ITRR tablosundan alındı. İkisi de aynı bazı kullanıyor, ama farklı z/OS seviyelerinde ölçülmüş olabilir.
- Köprünün tek kaynağı REDP-5320. Benchmark'ın transaction tanımı (Db2 çağrısı, I/O, transaction başına CPU süresi) henüz modele işlenmedi. Bu, iki taraf arasındaki transaction köprüsünün mainframe yarısıdır (Bölüm 12).

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

Sabit I/O gecikmesi: D_io = IOPS_PER_TX[rni] × t_io (low 5, average 10, high 20 I/O). t_io, storage katmanından gelir (Bölüm 8.6): okuma/yazma oranı, DS8900F önbellek isabeti, zHyperLink ve zHPF/FICON servis süreleri, senkron replikasyonun mesafe gecikmesi. Varsayılanlarla t_io M1'de 69 µs, senkron kopyalı topolojilerde (M2–M4) 129 µs; average RNI'da D_io sırasıyla 0,69 ms ve 1,29 ms.

R(p) = D_io + R_cpu(p)

ρ_max = min( 1 − E[X_cpu] · ln(1/(1−p)) / (hedef − D_io) , 0,90 )

Hedef ≤ D_io ise ya da boş sistemdeki CPU süresi bile bütçeyi aşıyorsa kademe infeasible olur (ρ_max = 0).

### 5.4. Basitleştirmeler ve Sınırlamalar

- Operasyonel tavan (0,90) her zaman geçerli. Latency hedefi tavanı yalnızca düşürebilir; daha sıkı SLA hiçbir zaman daha ucuz sonuç vermez.
- IOPS_PER_TX [ASSUME]; tüm I/O'lar sıralı/senkron sayılır (tutucu). Db2 buffer pool'ları fiziksel I/O sayısını gerçekte çok azaltır; IOPS_PER_TX = 10 büyük olasılıkla yüksek bir değerdir ve hem D_io'yu hem storage IOPS boyutlandırmasını etkiler (REDP-5320 iş yükü profiliyle kalibre edilmeli).
- Network (iç fabric), lock/latch beklemesi ve buffer pool isabet oranı modellenmez. Clustered taraf aynı yapıyı (aynı kuyruk ailesi + D_io + ağ gecikmesi) kullanmalıdır.

### 5.5. Davranış

Latency hedefi 3–500 ms aralığında, 3 RNI × 7 TPS seviyesi (2K–1M) için tarandı. Maliyet hiçbir senaryoda hedef sıkılaştıkça azalmadı. Gözlenen davranış:
- 50 ms ve üstü hedeflerde seçilen kademe latency'siz durumla aynı.
- 20 ms ve altında tavan düşer; model yavaş alt-kapasite CP'lerinden daha hızlı CP'li kademelere kayar. Örnek: 50K TPS avg RNI'da latency'siz 3931-436 (36 yavaş CP, p99 ≈ 27 ms), 20 ms hedefte 3931-509, 5 ms hedefte 3931-510, 2 ms hedefte 3931-704.
- Hedef D_io'ya yaklaştığında infeasible olur (M1'de avg RNI'da 0,69 ms, high RNI'da 1,39 ms; senkron kopyalı topolojilerde daha yüksek).

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

**Not:** Enerji frame başına sabit 30 kW alınıyor. 39 CP'nin üzerindeki kademeler birden fazla CPC drawer'ı, büyük yapılandırmalar birden fazla rack gerektirir (Max82–Max200). Bu yüzden büyük kademelerde enerji eksik sayılıyor; resmî güç değerleri IBM z16 IMPP belgesinden alınmalı (Bölüm 12).

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

25K TPS'in üzerinde eğri neredeyse düz. Sebep: donanım fiyatı PCI ile doğrusal, yazılım tek bir $/MSU ile tüketime orantılı. Ölçek ekonomisini (sabit taban maliyet, azalan birim fiyatlı MLC kademeleri) içeren gerçek maliyet yapısı bir sonraki adımda modellenecek (Bölüm 12).

## 8. Storage Katmanı — IBM DS8900F

### 8.1. Katmanın Savunması

Bu bölüm storage katmanının neden bu şekilde modellendiğini savunur: katmanın TCO'ya neden dahil edildiğini, neden tek alternatif olarak DS8900F'in seçildiğini, her modelleme kararının gerekçesini ve alternatifini, her varsayımın dayanağını ve geçerlilik tehditlerini. Teknik tanım Bölüm 8.2–8.9'dadır.

#### 8.1.1. Storage neden TCO'ya dahil

Projenin araştırma boşluğu iddiası, mevcut karşılaştırmaların "yalnızca compute'u kapsadığı; lisans, storage, DR ve personeli dışarıda bıraktığı"dır (`project_justification.md`). Storage'ı dışarıda bırakmak bu iddiayla doğrudan çelişir. Ancak bir kalemi dahil etmenin akademik gerekçesi yalnızca "tam yığın" iddiası olamaz; kalemin karşılaştırmanın sonucunu değiştirebiliyor olması gerekir. Bir maliyet kalemi iki tarafta aynı büyüklükteyse farkı ve dolayısıyla crossover noktalarını değiştirmez; projenin storage ağını kapsam dışı bırakma gerekçesi budur. Storage için bu koşul sağlanmaz (ayrıntı: Değerlendirme #3, Bölüm 1):

| Boyut | Mainframe | Clustered x86 | Neden birbirini götürmez |
|---|---|---|---|
| Veri kopyası | Shared-disk; site başına tek kopya | Shared-nothing DB'lerde veri DB tarafından 2–3 kez çoğaltılır | Aynı veri için ham kapasite farklı |
| DR replikasyonu | Storage katmanında (Metro/Global Mirror) | Çoğunlukla DB katmanında | Storage yoksa mainframe DR maliyetinin bir kısmı kaybolur, x86'nınki DB'de kalır: asimetrik hata |
| I/O'nun CPU maliyeti | Kanal alt sistemi ve SAP'lerde | Host CPU'sunda (storage yığını, replikasyon) | x86 compute boyutu storage'a bağlı |
| I/O gecikmesi | zHyperLink ~20 µs, zHPF ~90 µs | Yerel NVMe düşük; ağ üzerinden storage daha yüksek | Latency modelindeki D_io storage olmadan kalibre edilemez |

Modelin sonuçları bu öngörüyü doğruluyor: 50K TPS'te storage, 20 TB veride toplamın %9'u iken 500 TB'ta %68'i (Bölüm 8.7). Compute sabit kalırken storage veri hacmiyle büyüdüğü için veri hacmi, TPS'ten bağımsız ikinci bir crossover ekseni oluşturuyor. Bu, Değerlendirme #1'de zayıf bulunan çoklu crossover hipotezini destekleyen ilk somut mekanizmadır.

#### 8.1.2. Neden DS8900F ve neden tek alternatif

- **Nesil uyumu:** DS8900F, z15 ile duyurulan ve z16 ile eşleşen nesildir. Kademe tablosu z16 A01 olduğu için storage da aynı nesilden seçildi.
- **Temsil gücü:** IDC'ye göre IBM mainframe'e bağlı storage pazarının %40–50'sine sahip ve DS8000'i her yeni mainframe teklifine ekliyor [TT-2019]. Model tipik bir z16 kurulumunu temsil etmeli.
- **Mainframe'e özgü yetenekler:** zHyperLink, z16 ile DS8000 arasında tanımlıdır [REDP-5554]; IBM dışı dizilerde bu bağlantının bulunmadığını biliyoruz (doğrulanmalı). Modelin mainframe'e özgü gecikme avantajını temsil edebilmesi için bu dizi gerekli.
- **Veri erişilebilirliği:** IBM'in Product Guide'ı model, kapasite, güç ve lisans yapısını açık yayımlıyor; FICON destekli rakip dizilerin (Dell PowerMax, Hitachi VSP 5000) mainframe yapılandırmaları için karşılaştırılabilir açık veri bulunmadı.
- **Tek alternatif kuralı:** Proje Phase 1'de her katmanda tek alternatif kullanıyor (`project_context_restore_v4.md`, 4.7); mainframe tarafı "tek yığın" olarak tanımlı. Rakip dizileri eklemek kombinasyon sayısını büyütür ama karşılaştırmanın sorusunu (mainframe mi clustered mi) değiştirmez.
- **Kapsam dışı modeller:** DS8980F (998) yayımlanmış IOPS ve fiyatı olmadığı için; ardılı DS8000 G10 z16 ile aynı nesil olmadığı ve veri bulunmadığı için.

#### 8.1.3. Modelleme kararları

| Karar | Alternatif | Seçilme gerekçesi | Sonuca etkisi |
|---|---|---|---|
| Kopya sayısı DR topolojisinden türetilir (M1 1, M2 2, M3/M4 4) | Kullanıcı girdisi | Proje kararı: replikasyon kullanıcıya sorulmaz, availability/RPO'dan türetilir (`project_context_restore_v4.md`, 4.7). Kopya sayıları GDPS mimarisinden | Yüksek availability storage maliyetini 2–4 katına çıkarır; availability ile storage maliyeti arasında açık bir bağ kurar |
| Her kopya ayrı dizi ve birincilin IOPS'una göre boyutlanır | İkincil diziyi küçük boyutlamak | HyperSwap ve failover'da ikincil dizi birincilin tüm yükünü devralır; küçük ikincil gerçek bir failover'ı karşılamaz | Tutucu (maliyeti yukarı çeker) |
| IOPS = tepe TPS × IOPS/işlem (RNI'ya bağlı) | Kullanıcı IOPS girdisi | Proje kararı: kullanıcıya IOPS sorulmaz, RNI üzerinden iki tarafa da taşınır | IOPS_PER_TX hem model seçimini hem D_io'yu belirler (Bölüm 8.1.5) |
| Kopya başına en ucuz model; dizi sayısı = max(kapasite, IOPS ihtiyacı) | Sabit model | Kapasite ve IOPS iki ayrı darboğazdır; az veri + yüksek TPS IOPS ile, çok veri + düşük TPS kapasiteyle boyutlanır | ~60K TPS'te (IOPS tavanıyla) IOPS darboğazı DS8950F'e geçişi zorlar |
| Fiyat = (flash + kontrolcü liste fiyatı) × (1 − indirim) | Bileşen başına ayrı indirim | Yayımlanmış tek fiyat noktaları liste fiyatlarıdır; tek indirim oranı varsayımı tek bir parametrede toplar ve duyarlılık analizine açık tutar | Tüm belirsizlik tek parametrede (Bölüm 8.8) |
| Lisans = donanım capex'ine oran | TB başına fiyat | Lisans yapısı (BF, z-synergy, Copy Services; TB kademeli) resmî, fiyatı yayımlanmıyor; TB kademe granülaritesi fiyatın kendisini vermiyor | Varsayılanla storage capex'inin %20'si |
| Enerji tepe güçle | Tipik güç | Yalnızca tepe güç yayımlanıyor [REDP-5554] | Tutucu; storage enerjisi toplamda küçük |
| 3 yıllık planlama ufku | 1 yıl veya amortisman süresi (5 yıl) | Dizi büyümeye göre boyutlanır ama 5 yıl boyunca boş kapasite taşımak gerçekçi değil; kapasite planlamada yaygın orta ufuk | %15 büyümede kapasite ×1,52 |
| I/O başına sabit gecikme (kuyruk yok) | Dizi kuyruğu (M/M/c) | PAV/HyperPAV/SuperPAV aynı hacme paralel I/O sağlar; dizi, tepe IOPS'unun %70'iyle sınırlı yüklendiği için kuyruk etkisi küçük tutulur | Gecikme kuyruk olmadan hesaplanır; tavan bu basitleştirmeyi korur |
| Dizi, üretici tepe IOPS'unun %70'ine kadar yüklenir (STORAGE_IOPS_CEILING) | Tepe IOPS'un %100'ü | Tepe değer önbellek isabetli küçük blok ölçümüdür, gerçek OLTP karışımını temsil etmez; compute'taki %90 operasyonel tavanın storage karşılığı | DS8910F → DS8950F geçişi 90K yerine ~60K TPS'te |
| Mainframe'de storage için ek CPU yükü yok | Host CPU yükü eklemek | I/O kanal alt sistemi ve SAP'lerde işlenir; kapasite köprüsündeki CICS benchmark'ı z/OS I/O'sunun CPU maliyetini zaten içerir. Eklemek çift sayım olur | x86 tarafında aynı kalem açıkça eklenmeli (asimetri bilinçli) |
| Global Mirror ve uzak site replikasyonu latency'ye eklenmez | Eklemek | Asenkron replikasyon yazmanın tamamlanmasını beklemez; etkisi RPO'dadır, latency'de değil | RPO bağlantısı DR adımında |

#### 8.1.4. Varsayımlar ve dayanakları

| Parametre | Değer | Dayanak | Taranan aralık | Kalibrasyon yolu |
|---|---|---|---|---|
| STORAGE_DISCOUNT | 0,70 | Kurumsal all-flash pazarında liste fiyatından %35–65, büyük anlaşmalarda daha fazla [VENDORBENCH]; IBM liste fiyatlarının yüksekliği (flash $8,62/GB) | 0,50–0,85 | Gerçek DS8900F teklifi veya kamu ihale kaydı |
| Lisans oranları | 0,15 + 0,10 | Yapı resmî, fiyat yok | 0,05–0,30 | IBM teklifi |
| DB_OVERHEAD_FACTOR | 1,5 | Db2 log, image copy, work alanı, sistem hacimleri | 1,2–2,0 | Db2 kapasite planlama kılavuzu |
| RAID_USABLE_FRACTION | 0,75 | RAID 6 (6+P+Q) | sabit | DS8900F Architecture Redbook |
| SAFEGUARDED_RESERVE | 0,25 | Değişim hızına ve saklanan kopya sayısına bağlı | sabit | Safeguarded Copy Redbook |
| HOST_COMPRESSION_RATIO | 1,0 | Tutucu: sıkıştırma yok | 1,0–2,5 | Db2 sıkıştırma oranları |
| Okuma payı / önbellek isabeti / zHyperLink payı | 0,70 / 0,90 / 0,80 | Tipik OLTP okuma ağırlığı; büyük DS8900F önbelleği; Db2 senkron okumalarının zHyperLink'e uygunluğu | zHyperLink açık/kapalı | REDP-5320 iş yükü profili, RMF/SMF verisi |
| t_miss | 300 µs | Önceki modelin I/O süresi; flash arka uç + FICON | sabit | DS8900F performans raporları |
| Metro Mirror mesafesi | 20 km | Metro mesafe DR için tipik | 10–100 km | Senaryoya bağlı girdi |
| IOPS_PER_TX | 5 / 10 / 20 | Proje kararı | RNI ile | REDP-5320 iş yükü profili |

#### 8.1.5. Geçerlilik tehditleri

- **İç geçerlilik (fiyat):** Storage maliyetinin mutlak düzeyi büyük ölçüde indirim oranına bağlı; 0,50–0,85 aralığında yaklaşık 3 kat değişiyor. Bu yüzden storage'lı sonuçlar tek bir nokta olarak değil, indirim aralığıyla birlikte raporlanmalı. Göreli sonuçlar (veri hacmiyle doğrusal büyüme, topolojiyle kopya sayısı, IOPS ile model geçişi) indirim oranından bağımsızdır.
- **Yapı geçerliliği (IOPS_PER_TX):** İşlem başına 10 fiziksel I/O, Db2 buffer pool'ları düşünüldüğünde büyük olasılıkla yüksek. Bu hem D_io'yu hem dizi seçimini yukarı çeker. REDP-5320 iş yükü profiliyle kalibre edilene kadar storage'ın IOPS tarafı tutucu kabul edilmeli.
- **Yapı geçerliliği (IOPS tavanı):** Dizi, üretici tepe IOPS'unun %70'iyle boyutlanıyor. Oranın kendisi varsayım; gerçek OLTP karışımında dizinin sürdürülebilir IOPS'u iş yüküne bağlıdır ve IBM bunu yayımlamıyor. Tavan, compute tarafındaki %90 operasyonel tavanla aynı mantığı (tepe değerde çalışmamak) uygular.
- **Dış geçerlilik:** Tek üretici, 2019–2022 fiyatları, ABD liste fiyatları. Mainframe storage pazarının yaklaşık yarısını temsil eder; diğer yarı (PowerMax, VSP) farklı fiyatlanabilir.
- **Sonuç geçerliliği:** Storage'ın toplam içindeki payı varsayılan veri hacmine (20 TB) bağlı. Tezde storage payı tek bir yüzde olarak değil, veri hacmi ekseninde bir eğri olarak sunulmalı.

#### 8.1.6. Clustered tarafla eşleştirme

Storage, iki tarafın da aynı girdileri kullandığı ortak bir arayüzdür: `data_tb`, `data_growth`, RNI'dan IOPS ve (DR adımıyla) RPO. Clustered tarafın aynı arayüze bağlanırken eklemesi gerekenler: DB mimarisine bağlı kopya sayısı (replication factor), storage yığınının host CPU yükü, ağ üzerinden storage gecikmesi, kendi $/TB ve bakım parametreleri. Mainframe tarafında bu kalemlerin olmaması bilinçli bir asimetridir ve yukarıdaki kararlarla gerekçelendirilmiştir; iki taraf aynı derinlikte, farklı mekanizmalarla modellenir (eşit derinlik ilkesi, `project_context_restore_v4.md`, 3.7).

### 8.2. Mainframe'e Özgü Yapı

Mainframe tarafının storage'ı sabittir: IBM DS8900F (z15/z16 ile aynı nesil, tamamen flash). Projenin "mainframe tarafı tek yığın" ilkesine uyar. IDC'ye göre IBM, mainframe'e bağlı storage pazarının %40–50'sine sahip ve DS8000'i her yeni mainframe teklifine ekliyor [TT-2019]. DS8000'in ardılı DS8000 G10 bu modelin kapsamı dışındadır (z16 ile eşleşen nesil DS8900F; doğrulanmalı: G10'un çıkış tarihi).

Modelin yakaladığı mainframe'e özgü özellikler:

| Özellik | Ne yapar | Modeldeki etkisi |
|---|---|---|
| Shared-disk (Db2 data sharing) | Tüm Db2 üyeleri aynı diske erişir; site başına verinin tek kopyası | Kopya sayısını yalnızca DR topolojisi belirler (Bölüm 8.4) |
| Storage tabanlı replikasyon | Metro Mirror (senkron), Global Mirror (asenkron + journal), GDPS yönetir | Kopya başına ayrı dizi; senkron kopya yazma gecikmesine mesafe ekler |
| zHyperLink | z16 ile DS8900F arasında senkron, < 20 µs (~18 µs) küçük blok okuma; 150 m'ye kadar [REDP-5554] | Uygun okumalarda I/O süresi 90 µs yerine 20 µs |
| zHPF / FICON | Mainframe I/O protokolü; DS8900F önbellek isabetinde ~90 µs [TT-2019] | Okuma (zHyperLink dışı) ve yazma servis süresi |
| PAV / HyperPAV / SuperPAV | Aynı hacme paralel I/O | Kuyruk etkisi modellenmez; I/O'ların sabit gecikme sayılmasının gerekçesi |
| Kanal alt sistemi ve SAP'ler | I/O işlemesi genel amaçlı CP'den ayrı | Ek CPU yükü yok: kapasite köprüsündeki CICS benchmark'ı z/OS I/O'sunun CPU maliyetini zaten içeriyor. Clustered tarafta storage yığınının host CPU'su ayrıca eklenmeli |
| Safeguarded Copy | Fidye yazılımına karşı değiştirilemez anlık kopyalar (yüzlerce, 500'e kadar) [REDP-5554, TT-2019] | Birincil dizide ek kapasite + Copy Services lisansı |
| CKD hacimlerde veri azaltma yok | Sıkıştırma/dedup dizide değil, host'ta (Db2, z16 on-chip hızlandırıcı) | HOST_COMPRESSION_RATIO parametresi (varsayılan 1,0 = yok) |
| Lisans paketleri | Base Function (tüm kapasite), z-synergy Services (FICON, PAV, zHPF, zHyperLink; CKD), Copy Services. TB başına kademeli: 100 TB'a kadar 10 TB, 12 PB'a kadar 500 TB adımlarla [REDP-5554] | Fiyat yayımlanmadığı için donanım capex'ine oran [ASSUME] |

### 8.3. Model Kataloğu

`data/ds8900f_models.csv` [REDP-5554, ITCANDOR, TT-2019]:

| Model | Maks. ham kapasite (15,36 TB drive) | Maks. IOPS | Başlangıç liste fiyatı | Tepe güç |
|---|---|---|---|---|
| DS8910F-993 | 737 TB (z16 çerçevesine 16U monte) | 860K | $134.000 | 2,2 kW |
| DS8910F-994 | 2.949 TB (bağımsız raf) | 860K | $134.000 | 4,6 kW |
| DS8950F-996 | 5.898 TB (2.949 TB üstü E96 genişleme, +3,9 kW) | 2.320K | $196.000 | 6,2 kW |

DS8980F (998) kapsam dışı: yayımlanmış IOPS ve fiyatı yok. IOPS değerleri üretici tepe değerleridir (önbellek isabetli küçük blok). 993'ün z16 çerçevesine monte edilebilmesi mainframe'e özgü bir avantajdır (ayrı raf ve zemin alanı gerektirmez); model bunu ayrıca fiyatlamaz.

### 8.4. Boyutlandırma

Kopya başına ham kapasite:

ham_TB = veri_TB × (1 + büyüme)^3 × DB_OVERHEAD_FACTOR / HOST_COMPRESSION_RATIO / RAID_USABLE_FRACTION

- Planlama ufku 3 yıl [ASSUME]. Dizi bu ufkun sonundaki veriye göre boyutlanır; 5 yıllık NPV adımında büyüme yolu ayrıca modellenecek.
- DB_OVERHEAD_FACTOR = 1,5 [ASSUME]: Db2 aktif/arşiv log, image copy, work alanı, z/OS sistem hacimleri ve boş alan.
- RAID_USABLE_FRACTION = 0,75 [ASSUME]: RAID 6 (6+P+Q), yedek drive'lar hariç (doğrulanmalı).
- Safeguarded Copy için birincil dizide +%25 [ASSUME]; gerçek değer değişim hızına ve saklama sayısına bağlıdır.

Kopya sayısı topolojiden gelir [GDPS] (doğrulanmalı):

| Topoloji | Kopya | Gerekçe |
|---|---|---|
| M1 | 1 | Tek dizi |
| M2 | 2 | Metro Mirror çifti (HyperSwap), senkron |
| M3 | 4 | Metro/Global Mirror: H1 + H2 (senkron) + H3 + uzak sitede Global Mirror journal kopyası J3 |
| M4 | 4 | İki aktif site, her birinde Metro Mirror çifti |

IOPS ihtiyacı = tepe TPS × IOPS_PER_TX[rni]. Her kopya için en ucuz model seçilir: dizi sayısı = max(⌈ham_TB / maks_TB⌉, ⌈IOPS / (0,70 × maks_IOPS)⌉). 0,70, STORAGE_IOPS_CEILING'dir [ASSUME]: dizi üretici tepe IOPS'unun %70'ine kadar yüklenir (gerekçe Bölüm 8.1.3). İkincil kopyalar failover'da birincilin yükünü taşıyabilmek için aynı IOPS'a göre boyutlanır.

### 8.5. Maliyet

| Kalem | Formül | Kaynak |
|---|---|---|
| Flash | ham_TB × $8.620/TB (liste) | 15,36 TB flash kartı liste fiyatı $132.381 = $8,62/GB, kontrolcü hariç, Mayıs 2022 [ITJUNGLE-22] |
| Kontrolcü | dizi sayısı × başlangıç liste fiyatı | [TT-2019] |
| İndirim | (flash + kontrolcü) × (1 − 0,70) | [ASSUME]; kurumsal all-flash pazarında liste fiyatından %35–65, büyük anlaşmalarda daha fazla [VENDORBENCH] |
| Lisans | donanım × (0,15 BF + z-synergy, +0,10 Copy Services) | [ASSUME]; yapı [REDP-5554], fiyat yayımlanmıyor |
| Amortisman | (donanım + lisans) / 5 yıl | Mainframe donanımıyla aynı |
| Bakım | donanım × %15/yıl, 1 yıllık garanti sonrası (5 yıla ortalanmış) | [VENDORBENCH] %10–25; [IBM-122-037] garanti |
| Enerji | tepe kW × $0,12 × 730 saat | [REDP-5554] tepe güç (tutucu: tepe değer kullanılıyor) |

Etkin flash fiyatı varsayılanlarla ~$2.590/TB ham. Bu, modelin en belirsiz storage parametresidir: liste fiyatı resmî, ama gerçek indirim müşteriye özeldir (duyarlılık Bölüm 8.8).

### 8.6. I/O Gecikmesi

t_io = r × [h × (z × t_zHL + (1 − z) × t_FICON) + (1 − h) × t_miss] + (1 − r) × (t_FICON + senkron replikasyon)

| Parametre | Değer | Kaynak |
|---|---|---|
| r: okuma payı | 0,70 | [ASSUME] OLTP ~70/30 |
| h: önbellek isabeti | 0,90 | [ASSUME] |
| z: isabetli okumaların zHyperLink'e uygun payı | 0,80 | [ASSUME] Db2 senkron rastgele okumalar |
| t_zHL | 20 µs | [REDP-5554] |
| t_FICON | 90 µs | [TT-2019] (yazmalar DS8900F NVS'ine hızlı yazma) |
| t_miss | 300 µs | [ASSUME] flash arka uç + FICON |
| Senkron replikasyon | mesafe × 10 µs/km, varsayılan 20 km | Fiberde ışık ~5 µs/km tek yön; gidiş-dönüş 10 µs/km |

Sonuç: M1'de 69 µs/I/O (D_io 0,69 ms, average RNI). M2–M4'te 129 µs/I/O (1,29 ms). zHyperLink kapalıyken M1'de 105 µs. Metro Mirror mesafesi 100 km'ye çıkarsa M2'de D_io 3,69 ms. Böylece availability topolojisi latency'yi de etkiler: daha yüksek availability, senkron kopya nedeniyle daha yüksek yazma gecikmesi demektir.

### 8.7. Doğrulama Örnekleri

Statik mod, average RNI, 20 TB veri, varsayılan parametreler:

| Senaryo | Seçim | Storage | Storage / toplam |
|---|---|---|---|
| 50K TPS, %99,9 | M1, 3931-436 | 1× DS8910F-993, 76 TB ham, $7.496/ay | %9,4 |
| 50K TPS, %99,999 | M2, 3931-436 | 2× DS8910F-993, $13.778/ay | %10,9 |
| 50K TPS, %99,99999 | M4, 3931-436 | 4× DS8910F-993, $26.344/ay | %17,7 |
| 90K TPS, %99,9 | M1, 3931-610 | 900K IOPS (> 0,7 × 860K) → 1× DS8950F-996, $8.419/ay | %6,3 |
| 300K TPS, %99,9 | M1, 3931-727 | 3M IOPS → 2× DS8950F-996, $10.776/ay | %2,6 |

Veri hacmi ekseni (50K TPS, %99,9): 5 TB'ta storage toplamın %3,9'u, 100 TB'ta %30,6'sı, 500 TB'ta %68'i, 2.000 TB'ta %89,5'i. Storage maliyeti veri hacmiyle neredeyse doğrusal büyürken compute sabit kalır. Bu, Değerlendirme #3'te öngörülen ikinci crossover ekseninin (veri hacmi) mainframe tarafında gerçekten oluştuğunu gösteriyor; clustered tarafta kopya sayısı (replication factor) ve $/TB farklı olduğu için iki eğrinin eğimi farklı olacaktır.

Yıllık mod (50K TPS ortalama, 20 TB): storage yıllık toplamın %3–7'si; strateji sıralaması değişmiyor (storage üç stratejide de aynı).

### 8.8. Duyarlılık

`python src/tools/storage_sensitivity.py` (50K TPS, 20 TB, M1, storage aylık maliyeti):

| Parametre | Değerler → aylık storage |
|---|---|
| STORAGE_DISCOUNT | 0,50 → $12.364 · 0,70 → $7.496 · 0,85 → $3.844 |
| DB_OVERHEAD_FACTOR | 1,2 → $6.283 · 1,5 → $7.496 · 2,0 → $9.517 |
| HOST_COMPRESSION_RATIO | 1,0 → $7.496 · 1,5 → $5.474 · 2,5 → $3.858 |
| STORAGE_LICENSE_RATE_BASE | 0,05 → $7.101 · 0,15 → $7.496 · 0,30 → $8.088 |

İndirim oranı tek başına storage maliyetini ~3 kat oynatıyor; bu parametre için gerçek bir teklif veya kaynaklı bir pazar aralığı en değerli kalibrasyon olur.

### 8.9. Sınırlamalar

- Fiyatlar: yalnızca flash liste fiyatı (2022) ve başlangıç fiyatları (2019) kaynaklı; indirim, lisans ve tam konfigürasyon fiyatı varsayım.
- Drive katmanı tek: tüm kapasite 15,36 TB Tier 2 flash fiyatıyla. Küçük drive'lar (Tier 0/1) TB başına daha pahalı; yüksek IOPS yoğunluğu gereken küçük veri setlerinde maliyet eksik sayılabilir.
- IOPS kontrolü üretici tepe değerine göre; gerçek kapasite iş yüküne bağlı.
- Yedekleme (TS7700 sanal teyp, dış yedek) yok; Safeguarded Copy yalnızca mantıksal bozulmaya karşı.
- Storage ağı (FICON switch'ler, uzun mesafe bağlantı) yok: proje kararıyla iki tarafta da kapsam dışı. Uzun mesafe DR hattının maliyeti bu kararla dışarıda kalıyor; GDPS adımında yeniden değerlendirilmeli.
- Global Mirror ve M4'ün uzak site replikasyonu asenkron olduğundan latency'ye eklenmiyor; RPO etkisi DR adımında bağlanacak.

## 9. Yıllık Simülasyon — Workload Profile ve Fiyatlama Stratejileri

### 9.1. Yaklaşımın Gerekçesi

Statik tek-nokta sorgusu "şu anda şu yük için ne lazım" sorusunu cevaplar; ama gerçek bir kurumun maliyetini belirleyen şey yılın saatleri arasında değişen trafik desenidir. Tek bir ortalama TPS sayısı R4HA peak'i ve dolayısıyla yazılım faturasını gizler. Bir saatlik patlama tüm ayın yazılım faturasını yukarı çekebilir.

Ayrıca mainframe'in en karakteristik özelliklerinden biri Capacity on Demand'dir (CoD): peak günlerde geçici kapasite ekleme. Bu özellik, mainframe ekonomisini düşünüldüğünden çok daha esnek yapar — ve modelde temsil edilmezse mainframe haksız yere pahalı görünür.

### 9.2. Workload Profile Üretimi

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

### 9.3. R4HA (Rolling 4-Hour Average)

IBM MLC sub-capacity fiyatlandırması, her ay için en yüksek kayan 4-saatlik ortalama tüketimi (R4HA) baz alır. Yani kapasite sürekli değil, peak kullanım faturalanır. Model bu mekanizmayı doğrudan uygular:

r4ha\[i\] = mean(profile\[i-3 : i+1\]) \# 4-saatlik kayan ortalama

aylık R4HA peak = max(r4ha\[ay başlangıcı : ay sonu\])

Bu, neden saatlik simülasyon yaptığımızın kalbidir: günlük veya aylık ortalama R4HA'yı kaçırırdı.

### 9.4. Güncel IBM Z Donanım Edinim Modeli

IBM z15 ve sonrası için güncel ticari model üç katmanlıdır:

1. **Base (satın alınan, permanent) kapasite.** Müşterinin sahip olduğu kademe; donanım amortismanı ve bakım bu kapasite üzerinden işler.
2. **Capacity corridor (Tailored Fit Pricing for IBM Z Hardware, "Hardware Consumption Solution").** IBM'in tanımıyla "always-on, subscription-based corridor of pay-for-use capacity, on top of purchased capacity" [TFP-HW]. Corridor kapasitesi her zaman aktiftir; ücret, base'in üstünde **fiilen tüketilen MSU** üzerinden, SCRT ile saatlik ölçülerek kesilir. Boşta duran corridor kapasitesi ücretlendirilmez. Ön koşullar: z15 veya sonrası, z/OS genel amaçlı CP'ler, adanmış (dedicated) CP olmaması ve yazılım tarafında **Software Consumption Solution**. Corridor genişliği IBM'in iş yükü analiziyle belirlenir; IBM'in yayımlanmış maliyet çalışmasındaki örnek corridor, yeni iş yükünün %20'sidir [TFP-TCO].
3. **On/Off Capacity on Demand.** Corridor'u da aşan talep için geçici kapasite kaydı. 24 saatlik periyotlarla, o gün aktif edilen kapasite üzerinden faturalanır [COD].

Corridor fiyatı, corridor büyüklüğü için IBM'in yayımladığı genel bir kural ve corridor ile On/Off CoD'nin tam etkileşimi kamuya açık değildir; bunlar müşteriye özel sözleşmede belirlenir. Bu yüzden modelde parametre olarak durur ve duyarlılık analizine girer (Bölüm 9.8).

### 9.5. Geçici Kapasitenin Resmî Sınırları [COD]

SC28-7025'e göre geçici kapasite üç kısıta tabidir. Model her gün aktive edilen kademeyi (corridor tavanı dahil) bu kısıtlarla sınırlar:

| Kısıt | SC28-7025 | Modeldeki karşılığı |
|---|---|---|
| %100 kuralı | Geçici CP kapasitesi "up to 100% of the purchased capacity (active permanent plus unassigned permanent)" | Hedef kademe MSU ≤ 2 × base MSU |
| Kurulu kapasite | Geçici aktivasyon drawer ekleyemez; makine modeli değişemez | Hedef CP sayısı ≤ kurulu drawer özelliğinin sınırı (Max39/82/125/168/200) |
| Alt-kapasite kuralları | Geçici upgrade permanent alt-kapasite seviyesinin altına inemez, seviyeyi 5xx/4xx'e çekemez; 6xx'ten yalnızca 6xx'e (daha çok CP) veya 7xx'e geçilir | Hedef seri = base serisi ya da daha yüksek 6xx/7xx; CP sayısı azalamaz |

Kurulu drawer özelliği varsayılan olarak base kademeyi taşıyan en küçük özelliktir (boş drawer satın alınmaz). Model henüz drawer başına maliyet içermediği için daha büyük özellik seçimi bir karar değişkeni olarak açılmamıştır; bu, yol haritasındaki maliyet yapısı adımıyla birlikte gelecek.

Pratik sonuç: %100 kuralı küçük base'lerde bağlayıcıdır (ör. 3931-705 → en fazla 2 × 1.232 MSU), drawer sınırı ise drawer'ı dolduran base'lerde bağlayıcıdır (ör. 3931-735, Max39 üzerinde en fazla 3931-739'a, yani %11 ek kapasiteye çıkabilir). Yani "ne kadar geçici kapasite alınabilir" sorusunun gerçek cevabı çoğu durumda 2×'ten azdır ve base kademeye bağlıdır.

### 9.6. Üç Strateji

**Strateji A — Permanent.** Yılın peak saatini karşılayan en küçük feasible kademe satın alınır. Yazılım: aylık R4HA sub-capacity MLC.

**Strateji B — Base + On/Off CoD.** Daha küçük bir base kademe satın alınır. Her gün, günün tepe yükünü base karşılamıyorsa, bu tepeyi karşılayan en küçük izinli geçici kademe o gün için aktive edilir. Ücret:

CoD günlük = (aktif kademe PCI − base PCI) × (PCI başına aylık donanım maliyeti / 30) × COD_DAILY_MULTIPLIER

COD_DAILY_MULTIPLIER = 2,5 [ASSUME]. IBM gün başına fiyat yayımlamaz; çarpan, CoD'nin primli olması ama sürekli kapasiteden ucuz kalması mantığına dayanır. Yazılım: aylık R4HA (o ayın en büyük aktif kademesiyle sınırlı).

**Strateji C — Tailored Fit Pricing (base + corridor + CoD).** Base kademe satın alınır; corridor tavanı, base MSU × (1 + CORRIDOR_FRACTION) değerini karşılayan en küçük izinli kademedir ve yıl boyunca aktiftir. Corridor'u aşan günlerde On/Off CoD (corridor tavanının üstü için) devreye girer.

Corridor ücreti (saatlik) = max(0, min(tüketilen PCI, corridor PCI) − base PCI) × (PCI başına aylık donanım maliyeti / 730) × CORRIDOR_PREMIUM

Tüketilen PCI, yükün %100 kullanım eşdeğeridir (yük / (TPS_PER_PCI × RNI çarpanı)). Bu, IBM'in "base'in üstünde tüketilen MSU" ölçüsünün modeldeki karşılığıdır: base'in %90 operasyonel tavanı ile %100'ü arasındaki kullanım corridor kapasitesini aktif tutar ama base tüketimini aşmadığı için ücretlendirilmez. İsteğe bağlı sabit abonelik bedeli CORRIDOR_SUBSCRIPTION_RATE ile eklenebilir (varsayılan 0).

Yazılım (Software Consumption Solution) [TFP-SW]: R4HA yerine yıl boyunca tüketilen MSU-saat × efektif MSU-saat fiyatı. IBM efektif fiyatı müşterinin geçmiş 12 ayından belirler; model bunu gelir-nötr olarak kalibre eder: aynı profilin Permanent konfigürasyondaki R4HA faturası, aynı yılın tüketilen MSU-saatine bölünür. TFP_SW_DISCOUNT (varsayılan 0) bu fiyata uygulanan indirimdir. Gelir-nötr kalibrasyon nedeniyle TFP-SW'nin asıl avantajı (büyüme MSU'larının indirimli fiyatı, tepe cezası olmaması) tek yıllık ufukta görünmez; 5 yıllık ufuk adımında modellenecektir.

**Strateji seçimi.** Her availability-feasible topoloji için Strateji A'nın kademesi bulunur; ardından ortalama yükün en az 1,2 katını taşıyan [ASSUME] ve izinli en büyük geçici kademesi peak'i karşılayabilen her base kademe için B ve C simüle edilir. Her strateji için en ucuz sonuç tutulur ve üçü karşılaştırılır. Çok-frame topolojilerde geçici kapasite ücretleri tek frame için hesaplanır; ikinci frame yalnızca failover içindir ve onun geçici kapasitesi CBU konusudur (yol haritası).

### 9.7. Doğrulama Örneği

50K TPS ortalama yük, availability 0,999 (M1), average RNI, 20 TB veri, varsayılan parametreler. Toplamlara storage dahildir (steady_oltp ve batch_heavy'de tepe IOPS DS8910F'in tavanını (0,7 × 860K) aştığı için 1× DS8950F-996, yıllık ~$101K; retail_bursty'de tepe ~1,8M IOPS, DS8950F'in tavanını (0,7 × 2.320K) da aştığı için 2× DS8950F-996, yıllık ~$129K). Storage üç stratejide aynıdır.

| Preset | A: Permanent | B: Base + CoD | C: TFP | Kazanan, A'ya göre |
|---|---|---|---|---|
| steady_oltp | $1,496M (3931-516) | $1,528M (515, 261 gün CoD) | **$1,350M** (512 + corridor 516) | C, −%9,8 |
| retail_bursty | $3,078M (3931-624) | $2,333M (518 → 624, 20 gün) | **$2,331M** (518 + corridor 523 → 624) | C, −%24,3 (B ile fark %0,1) |
| batch_heavy | $2,279M (3931-616) | $1,871M (515 → 616, 30 gün) | **$1,763M** (512 + corridor 516 → 616) | C, −%22,6 |

Yorum:

- **Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanıdır.** steady_oltp'de günlük tepe base'i neredeyse her gün aşar; B bunu 261 gün CoD ile karşılamak zorunda kalır ve A'dan pahalıya gelir, C ise bu tepeleri tüketim bazlı corridor'la ucuza emer. retail_bursty'de maliyeti 20 günlük büyük tepeler belirler; B ve C neredeyse eşittir ve kazanan corridor fiyat varsayımlarına göre değişir (Bölüm 9.8).
- **%100 kuralı bağlayıcıdır.** retail_bursty'de peak kademe 3931-624 (3.059 MSU); bunu geçici olarak açabilmek için base en az 1.530 MSU olmalıdır. Model base'i 3931-518'e (1.560 MSU) çıkarır. Sınır uygulanmadan model 3931-515 (1.351 MSU) seçiyordu; bu, resmî kurala göre ulaşılamayan bir konfigürasyondu.
- Yazılım, yıllık toplamın %42–57'sidir ve en büyük tek kalemdir; donanım fiyatlama stratejisi yalnızca donanım kalemini yeniden dağıtır. Bu, maliyet/TPS eğrisinin düzlüğü sorununu tek başına çözmez.

### 9.8. Duyarlılık Analizi (Fiyatlama Varsayımları)

`python src/tools/pricing_sensitivity.py` kalibre edilmemiş fiyat parametrelerini tek tek tarar (50K TPS, M1, 20 TB; storage dahil). Yıllık toplamlar, milyon USD; kazanan kalın:

| Parametre (varsayılan) | Değer | steady_oltp A / B / C | retail_bursty A / B / C | batch_heavy A / B / C |
|---|---|---|---|---|
| CORRIDOR_PREMIUM (1,5) | 1,0 | 1,496 / 1,528 / **1,345** | 3,078 / 2,333 / **2,329** | 2,279 / 1,871 / **1,758** |
| | 4,0 | 1,496 / 1,528 / **1,376** | 3,078 / **2,333** / 2,341 | 2,279 / 1,871 / **1,787** |
| CORRIDOR_FRACTION (0,20) | 0,10 | 1,496 / 1,528 / **1,393** | 3,078 / **2,333** / 2,340 | 2,279 / 1,871 / **1,803** |
| | 0,50 | 1,496 / 1,528 / **1,319** | 3,078 / 2,333 / **2,303** | 2,279 / 1,871 / **1,733** |
| CORRIDOR_SUBSCRIPTION_RATE (0) | 0,25 | 1,496 / 1,528 / **1,390** | 3,078 / **2,333** / 2,378 | 2,279 / 1,871 / **1,802** |
| COD_DAILY_MULTIPLIER (2,5) | 1,5 | 1,496 / 1,499 / **1,350** | 3,078 / **2,296** / 2,304 | 2,279 / 1,841 / **1,736** |
| | 4,0 | 1,496 / 1,570 / **1,350** | 3,078 / 2,389 / **2,370** | 2,279 / 1,916 / **1,804** |
| TFP_SW_DISCOUNT (0) | 0,10 | 1,496 / 1,528 / **1,290** | 3,078 / 2,333 / **2,205** | 2,279 / 1,871 / **1,668** |

Sonuç: steady_oltp ve batch_heavy'de TFP'nin üstünlüğü tüm taranan aralıkta korunur. retail_bursty'de B ile C arasındaki seçim fiyat varsayımlarına duyarlıdır (fark ±%2 içinde); bu, gerçek sözleşme fiyatları olmadan "bursty iş yükü için TFP mi CoD mu" sorusuna kesin cevap verilemeyeceği anlamına gelir ve tezde böyle raporlanmalıdır. Permanent strateji, taranan hiçbir noktada kazanmaz.

### 9.9. Grafik-Hazır CSV Çıktısı

İki dosya üretilir, matplotlib/pandas ile doğrudan kullanılabilir:
- \<prefix\>\_hourly.csv — 8760 satır: hour, load_tps, capacity_tps, utilization, cod_active
- \<prefix\>\_monthly.csv — 12 satır: month, r4ha_peak_tps, software_cost, other_cost

## 10. Kod Yapısı ve Kullanım

```
Work_Emirhan/
  data/z16_a01_capacity.csv            317 kademe (üretilmiş tablo)
  data/raw/                            ham IBM verileri (kaynak ve erişim tarihi başlıkta)
  src/mainframe_model.py               model + CLI (yalnızca standard library)
  src/test_mainframe_model.py          tutarlılık testleri
  src/tools/build_z16_capacity_table.py  kademe tablosunu ham verilerden üretir
  src/tools/pricing_sensitivity.py     fiyatlama varsayımlarının duyarlılık analizi
  src/tools/storage_sensitivity.py     storage (DS8900F) duyarlılık analizi
  data/ds8900f_models.csv              DS8900F model kataloğu (kaynaklar dosya başlığında)
```

### 10.1. Statik Mod

python src/mainframe_model.py --tps 50000 --availability 0.999 --rni average --latency-ms 200 --data-tb 20 --data-growth 0.15

### 10.2. Yıllık Mod

python src/mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000 --availability 0.999 --csv out

### 10.3. Yardımcı Modlar

- --demo: hazır 6 senaryo
- --calibration: kademe tablosu özeti, köprü katsayıları ve örnek kademeler

### 10.4. Testler

python src/test_mainframe_model.py — 10 test: latency monotonluğu, latency'nin sıkı hedefte bağlayıcı olması, kademe tablosunun bütünlüğü (317 satır, seri başına kesin artan PCI ve MSU), köprünün kendi z13 çapalarını %2 içinde ve 7K0 PCI'sini %0,5 içinde üretmesi, MSU faturasının kurulu kapasiteyle sınırlı olması, geçici kapasitenin (B veya C) avantajının burstiness ile artması, geçici hedeflerin SC28-7025 kurallarına uyması (%100, drawer, alt-kapasite; 735 → 739 ve 705 örnekleri), seçilen B/C konfigürasyonlarının bu kurallara uyması, TFP-SW fiyatının gelir-nötr olması ve corridor ücretinin CORRIDOR_PREMIUM ile artması, storage boyutlandırmasının (topolojiden kopya sayısı, IOPS'tan model, veri hacminden kapasite) ve zHyperLink / senkron replikasyonun D_io'ya etkisinin beklenen yönde olması. Latency testinin infeasible eşiği artık storage'tan gelen D_io'ya göre hesaplanıyor.

## 11. Referanslar ve Kullanım Amaçları

### 11.1. Kapasite Tablosu ve Throughput Köprüsü

- **[LSPR]** IBM Z LSPR ITRRs (çok imajlı tablo, System z9 2094-701 = 1,00). 3931 4xx/5xx/6xx 1–39 CP ve 701–703 için PCI, MSU, Low/Average/High. https://www.ibm.com/support/pages/ibm-z-lspr-itrrs
- **[LSPR-z13]** IBM Z LSPR ITR zOSv2r2. Köprü çapaları: 2964-718 = 21.579 PCI (38,55), 2964-726 = 29.048 PCI (51,89). https://www.ibm.com/support/pages/node/6953815
- **[EXHIBIT]** IBM Mainframe Exhibit, Full Capacity MSUs, IBM z16 (3931), güncelleme 5/2/2025. 3931-701…7K0 resmî MSU değerleri ve A0–K0 kodlaması. https://www.ibm.com/downloads/documents/us-en/10a99803f42fd829
- **[STINE]** K. Stine, "IBM z16 Technical Overview", IBM Z Council, 2022. z16 200-way = 215.089 PCI (z15 190-way'e göre +%17); türetilen PCI değerlerinin bağımsız doğrulaması. https://ibm-zcouncil.com/wp-content/uploads/2022/05/z16-Technical-Overview-50M-KennyStine.pdf
- **[SG24-8950]** IBM Redbooks, "IBM z16 Technical Introduction" (2. baskı, 2023). A01'de 317 kapasite seviyesi (200 tam-hız + 117 alt-kapasite) ve Max39–Max200 özellikleri. https://redbooks.ibm.com/redbooks/pdfs/sg248950.pdf
- **[SG24-8952]** IBM Redbooks, "IBM z16 A02 and IBM z16 AGZ Technical Guide" (2023). Kapsam dışı bırakılan rack-mount modellerin tanımı. https://www.redbooks.ibm.com/redbooks/pdfs/sg248952.pdf
- **[REDP]** IBM Redpaper REDP-5320, "IBM CICS Performance Series: CICS TS V5.3 Benchmark on IBM z13" (Burgess, Mitchell, Moxey). 18 CP → 174.000 TPS, 26 CP → 227.000 TPS. https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf

### 11.2. Availability
- **\[REDBOOK\] —** IBM Redbook SG24-8446, "Getting Started with IBM Z Resiliency" (White, Coq). 4-model availability çerçevesinin (M1-M4) ve her topolojinin tasarım hedefleri/RTO-RPO değerlerinin temelidir. Modelin Topology sınıfının tüm yapısı bu kaynaktan alınmıştır. https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf
- **\[ITIC\] —** ITIC Global Server Reliability Surveys 2020-2024. Bağımsız endüstri anketleri (1.200-1.950 işletme/yıl); mainframe gerçek uptime ölçümleri. Her topolojiye atanan hw_low (alt sınır) rakamının kaynağıdır. Vendor iddiası ile bağımsız ölçümün ikili sunumunu sağlar. https://itic-corp.com/
- **\[PRECISELY\] —** Precisely, High Availability definition. Endüstri kuralı: toplam downtime'ın yaklaşık %90'ı planlı outage'lardan kaynaklanır. effective_availability hesabındaki ×10 çarpanının (planlı kesinti indirimi) kaynağıdır. https://www.precisely.com/glossary/high-availability-ha/

### 11.3. CoD ve Yıllık Simülasyon
- **\[COD\] —** IBM SC28-7025, "IBM Z and LinuxONE Capacity on Demand User's Guide". On/Off CoD'nin teknik yapısı (gün-bazlı faturalandırma, 24-saatlik aktivasyon periyodu, prepaid/postpaid modelleri) ve geçici kapasite sınırları (satın alınan kapasitenin %100'ü, kurulu kapasite, alt-kapasite seviye kuralları). Gün başına dolar fiyatı kapalı, premium çarpanı 2.5 \[ASSUME\]. https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf
- **\[CFCC\] —** IBM Coupling Facility Configuration Options (Raften), IBM Z Resiliency Redbook ve ilgili IBM dokümanları. ICF (Internal Coupling Facility) specialty engine olduğu için kapasite derecelendirmesini etkilemez ve yazılım lisansını artırmaz. M2 topolojisinin software_premium = 1.0 kalmasının (ek frame eklenmesine rağmen) gerekçesidir.

- **[TFP-HW] —** IBM Z Content Solutions, "Tailored Fit Pricing" (https://www.ibm.com/support/z-content-solutions/tailored-fit-pricing/). Hardware Consumption Solution'ın tanımı (always-on, subscription-based, pay-for-use corridor), ön koşulları (z15+, z/OS genel amaçlı CP, Software Consumption Solution, dedicated CP yok, RMF aralığı 1/3/5/15 dk). Ayrıca DBTA ve NetworkWorld duyuru haberleri: corridor kullanımı SCRT ile 1 saatlik çözünürlükte, fiilen tüketilen MSU üzerinden faturalanır.
- **[TFP-TCO] —** IBM IT Economics Consulting & Research, TFP for IBM Z Hardware maliyet çalışması (Mayıs 2021). Örnek corridor: 4.000 MSU'luk yeni iş yükü için %20 (800 MSU). CORRIDOR_FRACTION = 0,20 varsayılanının kaynağı. IBM sponsorlu bir çalışmadır; yalnızca yapı ve büyüklük örneği olarak kullanılır.
- **[TFP-SW] —** IBM TFP Software Consumption Solution fiyatlama özeti ve z/OS TFP dokümantasyonu: geçmiş 12 ayın MSU tüketiminden efektif MSU fiyatı, yıllık MSU taahhüdü (kullanılmayan MSU devreder), büyüme için indirimli fiyat, R4HA/tepe/capping yok. Modeldeki gelir-nötr kalibrasyonun gerekçesi.

### 11.4. Storage (DS8900F)

- **[REDP-5554] —** IBM Storage DS8900F Product Guide, Release 9.3.2 (https://www.redbooks.ibm.com/redpapers/pdfs/redp5554.pdf). Model kataloğu (çekirdek, bellek, HPFE Gen2 çifti, maks. drive ve ham kapasite), drive katmanları (Tier 0: 0,8/1,6/3,2 TB; Tier 1: 3,84 TB; Tier 2: 1,92/7,68/15,36 TB), tepe güç, zHyperLink (< 20 µs, ~18 µs; 150 m), lisans paketleri (Base Function, Copy Services, z-synergy Services) ve TB kademeleri, Safeguarded Copy.
- **[ITCANDOR] —** "IBM launches the DS8900F" (https://www.itcandor.com/ibm-storage-q419/). Maks. IOPS: DS8910F 860K, DS8950F 2.320K.
- **[TT-2019] —** TechTarget, "IBM Storage syncs new DS8900F array to z15 mainframe launch" (https://www.techtarget.com/searchstorage/news/252470647/IBM-Storage-syncs-new-DS8900F-array-to-z15-mainframe-launch). IBM'e göre başlangıç fiyatları ($134.000 DS8910F, $196.000 DS8950F), zHPF yanıt süresi (z13'te 120 → 90 µs), IDC'ye göre mainframe storage pazar payı %40–50.
- **[ITJUNGLE-22] —** IT Jungle, "More Price Hikes From IBM, Now For High End Storage" (https://www.itjungle.com/2022/05/16/more-price-hikes-from-ibm-now-for-high-end-storage/). IBM duyurusu 322-396: 16 adet 15,36 TB flash kartı (özellik 1625) liste fiyatı $2,12M, kart başına $132.381 = $8,62/GB (kontrolcü hariç); flash +%18, FICON +%40 fiyat artışı.
- **[VENDORBENCH] —** Kurumsal storage TB başına fiyat karşılaştırmaları (isvcosell.com / vendorbenchmark.com, 2026): liste fiyatından %35–65 indirim, yıllık destek %10–25. Metodolojisi açıklanmamış; yalnızca aralık olarak kullanılır.
- **[IBM-122-037] —** IBM duyurusu 122-037, DS8900F bir yıllık garanti teklifi.
- **[GDPS] —** IBM GDPS mimarisi (Metro Mirror çifti ve HyperSwap; Metro/Global Mirror'da uzak sitede journal kopyası). Kopya sayıları doğrulanmalı (GDPS Redbook).

### 11.5. Maliyet Verileri (Yarı-Kapalı)
- **\[PRICE\] —** Bağımsız mainframe fiyat rehberleri (electronics.alibaba buying guides serisi). z15/z16 donanım fiyat aralığı (\$0.5M-\$10M+), yıllık bakım donanım değerinin %10-15'i, alt ekonomik eşik ~150 MIPS. HARDWARE_COST_PER_MIPS = \$200 ve MAINTENANCE_RATE_ANNUAL = 0.125 değerlerinin kaynağıdır. Açık liste fiyatı olmadığı için kestirim.
- **\[LIC\] —** MLC/MSU lisanslama kaynakları (atonementlicensing.com, redresscompliance.com). Tipik kurumsal 600-2500 MSU → aylık \$15K-\$80K → ~\$25-55/MSU/ay aralığı. SOFTWARE_COST_PER_MSU_MONTH = \$40 (orta değer) bu kaynaktan.
- **\[PWR\] —** Aynı fiyat rehberi (electronics.alibaba) enerji ölçütleri. z15/z16 frame başına 20-40 kW; modelde POWER_KW_PER_SYSTEM = 30 kW (orta).

### 11.6. Teorik Temel

- **[QUEUE]** Kuyruk teorisi (per-CP M/M/1). Mainframe WLM/RMF response-time percentile metodolojisiyle uyumlu (SMF 72.3 / 110.1).

## 12. Modelin Bilinen Eksikleri ve Sonraki Adımlar

### 12.1. Kalibre Edilmemiş Parametreler [ASSUME]

- RNI çarpanları low 1,25 / high 0,70 (ve LSPR RNI kavramıyla ayrıştırılması)
- HARDWARE_COST_PER_MIPS = $200/PCI (doğrusal kestirim)
- SOFTWARE_COST_PER_MSU_MONTH = $40 (tek fiyat; gerçekte ürün başına kademeli)
- GDPS yazılım primi (M3 ×1,15, M4 ×1,30)
- COD_DAILY_MULTIPLIER = 2,5 ve base kademe için "≥ ortalama yükün %120'si" eşiği
- TFP: CORRIDOR_PREMIUM = 1,5, CORRIDOR_FRACTION = 0,20 (IBM örneğinden), CORRIDOR_SUBSCRIPTION_RATE = 0, TFP_SW_DISCOUNT = 0 (Bölüm 9.8'de taranır)
- Storage: STORAGE_DISCOUNT = 0,70, lisans oranları 0,15 + 0,10, DB_OVERHEAD_FACTOR = 1,5, RAID_USABLE_FRACTION = 0,75, SAFEGUARDED_RESERVE = 0,25, planlama ufku 3 yıl; I/O yolu: okuma payı 0,70, önbellek isabeti 0,90, zHyperLink payı 0,80, t_miss = 300 µs, Metro Mirror mesafesi 20 km (Bölüm 8)
- IOPS_PER_TX (D_io'yu ve storage IOPS boyutlandırmasını birlikte belirler; büyük olasılıkla yüksek)
- ELECTRICITY_USD_PER_KWH = $0,12, POWER_KW_PER_SYSTEM = 30 kW

### 12.2. Yapısal Basitleştirmeler

- Enerji, büyük kademelerde drawer/rack sayısıyla ölçeklenmiyor (Bölüm 7.4 notu).
- Kurulu drawer özelliği base'i taşıyan en küçük özellik olarak sabit; drawer maliyeti yok, bu yüzden özellik seçimi karar değişkeni değil (Bölüm 9.5).
- Corridor genişliği base MSU'nun sabit bir oranı; IBM'de bu, iş yükü analiziyle müşteriye özel belirlenir.
- On/Off CoD kaydının 180 günlük süresi ve tek-aktif-kayıt kuralı modellenmiyor (simülasyonlarda en fazla 261 gün CoD görülüyor; bu, kayıt yenilemesi gerektirir).
- R4HA LPAR değil CPC toplamı üzerinden hesaplanıyor.
- Peak günler yıla eşit aralıklarla dağıtılıyor (gerçekte mevsimsel kümelenir); tek yıllık ufuk.
- Yedek frame tam kapasite ve tam maliyetle sayılıyor (CBU modellenmiyor).
- M4'ün availability kaynak etiketleri ters görünüyor; M3 ve M4'ün effective low değerleri aynı. RPO/RTO girdileri bağlı değil.

### 12.3. Yol Haritası (Değerlendirme #2, M3–M8)

- REDP-5320 iş yükü profilinin çıkarılması (transaction köprüsünün mainframe yarısı; D_io kalibrasyonu)
- Maliyet yapısı: donanımda taban + drawer + kapasite başına artış (drawer özelliğini karar değişkeni yapar), ürün başına kademeli MLC (z/OS, CICS, Db2), zIIP (TFP-HW zIIP corridor'u dahil)
- Availability: RPO/RTO bağlantısı, M4 düzeltmesi, DR frame için CBU
- Storage: gerçek bir DS8900F teklifiyle indirim/lisans kalibrasyonu; TS7700 yedekleme; DS8000 G10
- Personel ve GDPS ayrı kalem
- 5 yıllık ufuk + NPV, kümelenmiş peak dağılımı; TFP-SW büyüme fiyatı ve MSU taahhüdü
- (Opsiyonel) z16 A02 rack-mount modelleri
