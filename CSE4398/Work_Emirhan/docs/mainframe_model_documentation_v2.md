# Mainframe (Scale-Up) Modelinin Detaylı Dokümantasyonu

*Compute kapasitesi, latency, availability, yıllık simülasyon ve Capacity-on-Demand modüllerini içerir*

Bu doküman, projenin mainframe tarafında geliştirilen modelin tüm bileşenlerini açıklar: hangi referanstan hangi veri çekildi, ne amaçla kullanıldı, modele nasıl entegre edildi. Önceki dokümantasyondan farklı olarak burada yeni eklenen bileşenler — CP-güç köprüsü, M/M/1 dinamik latency modeli, IBM Resiliency 4-model availability çerçevesi, planlı kesinti indirimi, ve yıllık simülasyon (R4HA + On/Off CoD) — tam detayıyla yer alır.

## 1. Modelin Amacı ve Kapsamı

### 1.1. Cevaplanan Soru

Verilen bir iş yükü (throughput, işlem karmaşıklığı, latency hedefi, availability hedefi) için, bu iş yükünü karşılayan minimum maliyetli feasible IBM z16 konfigürasyonu hangisidir, ve aylık/yıllık maliyeti nedir?

### 1.2. Mevcut Kapsam

Model şu anda mainframe altyapısının compute katmanını ve yıllık simülasyon davranışını eksiksiz modeller. İçerdiği bileşenler:
- z16 compute kapasitesi (128 LSPR kademesi temelinde)
- CP-güç köprüsü (TPS hesabı için)
- İşlem karmaşıklığı (RNI) modeli
- M/M/1 kuyruk teorisi ile dinamik latency feasibility
- IBM Z Resiliency 4-model availability framework'ü (M1–M4)
- z/OS yazılım lisansı (MSU bazlı), donanım amortismanı, bakım, enerji
- Yıllık simülasyon: 8.760 saatlik workload profile + aylık R4HA + permanent vs On/Off CoD strateji karşılaştırması

### 1.3. Henüz Modele Eklenmemiş Bileşenler (Phase 2'de eklenecek)
- CICS Transaction Server lisansı
- Db2 for z/OS lisansı
- DS8900F storage modeli (kapasite + IOPS)
- Operasyon personeli (sysprog + DBA)
- Stokastik arıza modeli ve Monte Carlo

## 2. Modelin Girdi ve Çıktıları

### 2.1. Mevcut Girdiler

| **Parametre** | **Açıklama** | **Tipik aralık** |
|---|---|---|
| tps | Saniyedeki işlem sayısı | 1.000 – 500.000 |
| rni | İşlem karmaşıklığı (low/avg/high) | low / average / high |
| latency_ms + percentile | Hedef latency | ör. p99 \< 200 ms |
| availability | Hedef uptime | 0.999 – 0.99999999 |
| \[yıllık\] preset | Workload preset adı | steady_oltp / retail_bursty / batch_heavy |
| \[yıllık\] avg_tps + peak_ratio + peak_days | Custom workload tanımı | ör. 50K TPS, 3.5×, 20 gün |

### 2.2. Çıktılar

Statik mod (tek-nokta sorgu):
- Seçilen z16 model kodu (örn. 3931-608)
- Seçilen availability topolojisi (M1/M2/M3/M4)
- Tam-hız CP eşdeğer sayısı, utilization, gereken frame sayısı
- Aylık maliyet dökümü: yazılım + donanım + bakım + enerji

Yıllık mod (workload simülasyonu):
- Seçilen strateji (Permanent peak vs Base + On/Off CoD)
- Yıllık toplam maliyet + alternatif stratejinin maliyeti (tasarruf yüzdesi)
- Utilization istatistikleri (ortalama, medyan, maksimum)
- CoD aktif gün sayısı
- CSV: 8760 satır saatlik (load, capacity, utilization, cod_active) + 12 satır aylık (R4HA peak, software cost, other cost)

## 3. Kapasite Köprüleri — LSPR'den MIPS ve MSU'ya

IBM'in resmi LSPR (Large System Performance Reference) tablosu z16'nın 128 kademesini System z9 2094-701 = 1.00 baz alarak verir. Ancak bu göreceli oranlar; mutlak MIPS değerlerini doğrudan yayınlamaz. Modelin LSPR oranlarını mutlak MIPS ve MSU'ya çevirmek için iki köprü sabiti türetilmiştir.

### 3.1. LSPR → MIPS Köprüsü

Mutlak çapa, Scott Chapman'ın "Exploring z/OS WLM CPU Measurements" sunumundan alındı. Bu kaynak IBM ResourceLink'e referansla 3931-604 modelinin mutlak kapasitesini verir:
- 3931-604 → 5511 PCI (IBM'in "MIPS"e verdiği isim) = 675 MSU

Aynı modelin LSPR oranı IBM resmi tablosunda 9.85. Bu iki noktadan dönüşüm katsayısı türetilir:

LSPR_TO_MIPS = 5511 / 9.85 ≈ 559.49 MIPS / LSPR birimi

Köprünün doğruluğu bağımsız bir veri noktasıyla doğrulandı: 3931-701 (tek tam-hız CP) için LSPR oranı 4.02 olduğundan, köprü 4.02 × 559.49 ≈ 2249 MIPS verir. IBM z16 Technical Overview bu modeli yaklaşık 2253 PCI olarak listeler — yuvarlama farkı dışında birebir örtüşme.

### 3.2. MIPS → MSU Köprüsü

Aynı 3931-604 çapasından MSU/MIPS oranı türetilir:

MSU_PER_MIPS = 675 / 5511 ≈ 0.1225 MSU / MIPS

Önemli bir kavramsal uyarı: MSU performans değil yazılım lisans birimidir. Kapasite hesabı için MIPS, lisans maliyeti için MSU kullanılır — model bu ayrımı korur.

## 4. CP-Güç Köprüsü — Throughput'a Bağlama

### 4.1. Eski Yaklaşım ve Sorunu

İlk versiyonda model, z13 benchmark'ından "işlem başına MIPS" oranı türetip bunu doğrudan z16'ya uyguluyordu. Bu yaklaşım MIPS'in nesiller arası mükemmel normalize olduğunu örtük olarak varsayar. Ancak z16'nın Telum işlemcisi mimari olarak z13'ten farklıdır (cache hiyerarşisi, pipeline, bellek alt sistemi); aynı MIPS sayısı farklı nesillerde farklı gerçek iş anlamına gelebilir. Bu kırılganlığı gidermek için CP-güç köprüsüne geçildi.

### 4.2. CP-Güç Köprüsü Mantığı

Yeni yaklaşım: z13 benchmark'ından elde edilen TPS önce z13 CP başına TPS'e çevrilir; ardından LSPR'den alınan z16/z13 CP güç oranı ile z16 CP başına TPS'e taşınır. MIPS aracı birim olarak kullanılmaz; doğrudan CP'den CP'ye köprü kurulur.

### 4.3. Benchmark Veri Noktaları

Köprünün temeli IBM Redpaper REDP-5320'de yayınlanan iki CICS TS V5.3 benchmark noktasıdır:
- z13 2964-718 (18 CP, tam hız) → 174.000 TPS
- z13 2964-726 (26 CP, tam hız) → 227.000 TPS

İki nokta arası karşılaştırma sublineariteyi sayısal olarak gösterir: 18 CP'de CP başına 9.667 TPS, 26 CP'de 8.731 TPS. CP sayısı %44 artarken throughput sadece %30 artar — koordinasyon overhead'i nedeniyle. Bu fark modele dahil edilir.

### 4.4. CP Güç Oranları

Aynı CP sayısında z16 ve z13'ün LSPR oranları karşılaştırılır:
- 18 CP: z16 3931-718 LSPR = 54.06 / z13 2964-718 LSPR = 38.55 → oran 1.402
- 26 CP: z16 3931-726 LSPR = 72.88 / z13 2964-726 LSPR = 51.89 → oran 1.405

İki oranın neredeyse aynı çıkması, sublinearitenin iki nesilde benzer biçimde devrede olduğunu ve köprü hesabının tutarlı olduğunu gösterir.

### 4.5. z16 CP Başına TPS

z16 18-CP TPS/CP = 9.667 × 1.402 = 13.556

z16 26-CP TPS/CP = 8.731 × 1.405 = 12.267

Sublineariteyi koruyarak iki noktanın ortalaması:

BASE_TPS_PER_CP ≈ 12.909 TPS / tam-hız z16 CP (average RNI)

### 4.6. Tam-Hız CP Eşdeğeri (Alt-Kapasite Kademeleri)

z16'nın alt-kapasite kademelerinde (4xx, 5xx, 6xx serileri) bir fiziksel CP, tam-hız 7xx CP'sinden daha az kapasite sunar. Bu fark zaten LSPR oranlarına yansımıştır. Her kademenin tam-hız CP eşdeğeri:

cp_equivalents(tier) = tier.lspr / 4.02

4.02 = 3931-701'in (tek tam-hız CP) LSPR oranı. Örnek: 3931-501'in LSPR oranı 1.67 → 1 fiziksel CP'si yaklaşık 0.42 tam-hız CP eşdeğeri.

### 4.7. RNI (İşlem Karmaşıklığı) Çarpanı

Aynı CP, işlem karmaşıklığına göre farklı TPS üretir. IBM bu konsepti Relative Nest Intensity (RNI) olarak adlandırır ve LSPR tablolarında Low/Average/High RNI sütunları yayınlar. Bu modelde RNI etkisi BASE_TPS_PER_CP üzerine çarpan olarak uygulanır:
- low = 1.25 (hafif işlem, aynı CP daha çok TPS) — \[ASSUME\]
- average = 1.00 (REDP benchmark noktası — kalibre)
- high = 0.70 (ağır işlem, aynı CP daha az TPS) — \[ASSUME\]

REDP benchmark IBM'in "average RNI" olarak sınıflandırdığı iş yükünde ölçüldüğünden, average çarpanı 1.00'e sabitlenir. Low ve high çarpanları henüz kalibre edilmemiş varsayımlardır.

## 5. Latency Modeli — M/M/1 Dinamik Utilization Tavanı

### 5.1. Yaklaşımın Gerekçesi

İlk versiyonda latency, sabit %90 utilization tavanı olarak dolaylı modellenmişti. Bu basitleştirme uygulamaya yakın olsa da kullanıcının latency hedefini doğrudan modele yansıtmıyordu. Yeni yaklaşım: kuyruk teorisinden her kademe için ayrı bir maksimum utilization türetir; daha sıkı latency hedefi daha düşük utilization → daha büyük kademe gerekir.

### 5.2. Endüstri Pratiği ile Uyum

Mainframe dünyasında WLM (Workload Manager) zaten latency'yi percentile bazında ifade eder — örneğin bir CICS service class hedefi "işlerin %90'ı 0.8 saniye içinde". RMF SMF 72.3 ve SMF 110.1 kayıtlarıyla ölçülür. Modelimiz aynı percentile-tabanlı yaklaşımı kullanır.

### 5.3. Düzeltme Notu (2026-10-31)

Önceki sürümde ortalama servis süresi E\[X\] = 1 / (kademenin toplam ham TPS'i) alınıyordu. Bu, bütün kademeyi tek bir çok hızlı sunucu sayar ve iki soruna yol açıyordu:
- **Tutucu değil, iyimserdi.** Aynı utilization'da hızı c·μ olan tek sunuculu M/M/1, c sunuculu M/M/c'den *daha düşük* yanıt süresi verir. "M/M/1 tutucu üst sınırdır" iddiası bu kurulumla sağlanmıyordu.
- **Latency girdisi etkisizdi ve ters çalışıyordu.** E\[X\] mikrosaniye mertebesinde çıktığından her makul hedefte tavan %95 sınırına yapışıyordu. Latency hedefi verilince tavan %90'dan %95'e çıkıyor ve sistem *ucuzluyordu* (50K TPS, avg RNI: latency'siz $109.520/ay, p99 < 50 ms ile $98.034/ay).

### 5.4. Formül

Sunucu = fiziksel CP. CP başına CPU servis süresi:

E\[X_cpu\] = c / raw_tps    (c = kademenin fiziksel CP sayısı)

Alt-kapasite (4xx/5xx/6xx) CP'leri LSPR gereği daha yavaş olduğundan E\[X_cpu\] daha büyük çıkar. Bu gerçek bir mainframe etkisidir: aynı toplam kapasitede alt-kapasite kademesi daha uzun CPU süresi, dolayısıyla daha kötü yanıt süresi verir.

Tutucu kuyruk: c adet bağımsız M/M/1 kuyruğu, her birine λ/c yük. Paylaşımlı kuyruktan (M/M/c) daha kötü yanıt verir, yani gerçek bir üst sınırdır.

R_cpu(p) = E\[X_cpu\] × 1/(1 − ρ) × ln(1/(1 − p))

Sabit I/O gecikmesi (kuyruktan bağımsız):

D_io = IOPS_PER_TX\[rni\] × IO_SERVICE_TIME    (low 5, average 10, high 20 I/O; 0.3 ms/I/O)

Toplam ve çözüm:

R(p) = D_io + R_cpu(p)

ρ_max = min( 1 − E\[X_cpu\] · ln(1/(1−p)) / (hedef − D_io) , 0.90 )

Hedef ≤ D_io ise ya da boş sistemdeki CPU süresi bile bütçeyi aşıyorsa kademe infeasible (ρ_max = 0).

### 5.5. Basitleştirmeler ve Sınırlamalar
- **Operasyonel tavan her zaman geçerli (0.90).** Latency hedefi tavanı yalnızca düşürebilir, asla yükseltemez. Daha sıkı SLA hiçbir zaman daha ucuz sonuç vermez. Eski HARD_UTILIZATION_CAP = 0.95 kaldırıldı.
- IOPS_PER_TX ve IO_SERVICE_TIME = 0.3 ms \[ASSUME\]; DS8900F + FICON/zHPF için sektör aralığı ~0.1–0.5 ms (zHyperLink okumalarında ~0.02 ms). Tüm I/O'lar sıralı/senkron sayılır (tutucu; gerçekte bir kısmı paralel ve Db2 buffer pool'dan karşılanır).
- Network (iç fabric), lock/latch beklemesi ve buffer pool isabet oranı modellenmez. Clustered taraf aynı yapıyı (aynı kuyruk ailesi + D_io + ağ gecikmesi) kullanmalıdır.

### 5.6. Davranış (doğrulama)

Latency hedefi 3–500 ms aralığında taranarak 15 senaryoda (3 RNI × 5 TPS) maliyetin hedef sıkılaştıkça hiç azalmadığı doğrulandı. Gözlenen davranış:
- 50 ms ve üstü hedeflerde mainframe kademesi latency'siz durumla aynı. Yani tipik bankacılık SLA'larında (100–500 ms) CPU kuyruğu bağlayıcı değil.
- Tek haneli ms hedeflerde tavan düşer ve model daha hızlı CP'li (7xx) kademelere kayar. Örnek: 10K TPS avg RNI, 20 ms hedefte 3931-408 yerine 3931-701.
- D_io hedefe yaklaşınca infeasible olur (avg RNI'da 3 ms, high RNI'da 6 ms).

## 6. Availability Modeli — IBM Z Resiliency 4-Model

### 6.1. Yaklaşım Değişikliği

İlk versiyonda availability, basit bir "hedef uptime → kaç sistem gerekir" eşlemesiyle modelleniyordu (örn. 4-5 nine için 2 sistem). Bu yaklaşım çok kabaydı ve mainframe'in gerçek availability mimarisini yansıtmıyordu. Mainframe'de availability tek değişken değil; katmanlı bir mimari karardır. Yeni model bu katmanları doğrudan modeller.

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

Aylık maliyet dört kalemden oluşur ve her kalem farklı bir veri güvenirliği seviyesine sahiptir.

### 7.1. Yazılım Lisansı (z/OS)

z/OS MSU bazlı aylık lisanslama (MLC) ile faturalanır. Bağımsız lisanslama kaynaklarına göre tipik kurumsal mainframe (600-2500 MSU) için aylık \$15.000-\$80.000 arası lisans maliyeti raporlanır; bu yaklaşık MSU başına \$25-55/ay aralığına denk gelir. Modelde orta değer:

SOFTWARE_COST_PER_MSU_MONTH = \$40 / MSU / ay

Aylık yazılım maliyeti = faturalanan_MSU × \$40 × topology.software_premium. Sub-capacity fiyatlamada faturalanan MSU, o ayın R4HA tepesinde tüketilen MSU'dur: faturalanan_MSU = min(R4HA_yük / ham_TPS, 1) × tier.msu (kurulu kapasiteyle sınırlı). Statik modda yük sabit olduğundan R4HA = TPS. GDPS premium M3 için ×1.15, M4 için ×1.30. Önemli kural: ICF specialty engine olduğu için ek frame yazılım lisansını artırmaz \[CFCC\].

### 7.2. Donanım Amortismanı

Mainframe donanım fiyatları açık liste olarak yayınlanmaz. Birden çok bağımsız fiyat rehberinin verdiği aralık birleşik olarak ~\$500.000 (giriş seviyesi) ile ~\$10.000.000+ (tam kapasite, üretim grade) arasındadır. Modelde MIPS başına kabaca doğrusal kestirim:

HARDWARE_COST_PER_MIPS = \$200 / MIPS — \[PRICE → ASSUME\]

aylık donanım = tier.mips × \$200 / (5 yıl × 12 ay)

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

### 7.5. Toplam Aylık Maliyet

total = faturalanan_MSU × \$40 × software_premium + (hardware_amort + maintenance + energy) × n_frames

Yazılım kalemi capacity-MSU bazlı olduğu için frame sayısıyla çarpılmaz; donanım/bakım/enerji çarpılır. Bu yapı ICF kuralıyla \[CFCC\] tutarlıdır.

## 8. Yıllık Simülasyon — Workload Profile + R4HA + On/Off CoD

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

### 8.4. İki Strateji Karşılaştırması

Strateji A — Permanent Peak

Yılın peak saatini karşılayacak en küçük feasible kademe sürekli açık. Yıllık maliyet = 12 × aylık maliyet (peak kademe için).

Strateji B — Base + On/Off CoD

Küçük base kademe yılın çoğunu karşılar; peak günlerde On/Off CoD ile peak kademeye geçici upgrade. CoD kullanımı IBM SC28-7025'te tanımlanır: gün-bazlı faturalandırma, 24-saatlik aktivasyon periyodu.

CoD daily charge varsayımı:

CoD daily = (peak günlük donanım maliyeti − base günlük donanım maliyeti) × 2.5

Çarpan 2.5 \[ASSUME\] — IBM gün başına dolar fiyatını açık yayınlamaz. Mantığı: CoD premium'lu olmalı (yoksa kimse permanent almazdı) ama sürekli almaktan ucuz olmalı.

Strateji Seçimi

Model her olası base kademeyi deneyip Strateji B'nin en ucuzunu bulur, sonra Strateji A ile karşılaştırır. Her zaman daha ucuz olanı seçer. Karar yapısal değil, optimizasyondur.

### 8.5. Aylık Yazılım Maliyeti R4HA-Bağımlı

Her ay, iki strateji için de, yazılım faturası o ayın R4HA tepesinde tüketilen MSU'ya göre kesilir (kurulu kapasiteyle sınırlı; CoD aktif aylarda kurulu kapasite peak kademedir). Bu, IBM'in sub-capacity MLC kuralının modeldeki karşılığıdır.

*Düzeltme (2026-10-31):* Önceki sürümde R4HA indirimi yalnızca CoD olan aylarda uygulanıyor, Permanent strateji her ay tam kurulu MSU üzerinden faturalanıyordu. Bu, Base+CoD stratejisini haksız biçimde avantajlı gösteriyordu. Şimdi iki strateji arasındaki fark yalnızca donanım tarafındadır (kalıcı peak donanımı vs base donanımı + CoD günlük ücreti).

### 8.6. Doğrulama Örneği

50K TPS ortalama yük, availability 0.999, average RNI:

| Preset | Seçilen strateji | Yıllık toplam | Alternatife göre tasarruf |
|---|---|---|---|
| retail_bursty | Base + CoD (3931-708 → 3931-726, 20 gün) | ~\$3.04M | %31.8 |
| batch_heavy | Base + CoD (3931-708 → 3931-626) | ~\$2.53M | %19.8 |
| steady_oltp | Permanent (3931-526) | ~\$2.01M | %5.1 |

Önceki sürümde retail_bursty tasarrufu %36 (\$5.08M → \$3.23M) çıkıyordu; farkın bir kısmı Permanent stratejiye R4HA uygulanmamasından geliyordu. Düzeltilmiş modelde de beklenen sıralama korunuyor: peak/avg oranı arttıkça CoD avantajı büyüyor.

### 8.7. Grafik-Hazır CSV Çıktısı

İki dosya üretilir, matplotlib/pandas ile doğrudan kullanılabilir:
- \<prefix\>\_hourly.csv — 8760 satır: hour, load_tps, capacity_tps, utilization, cod_active
- \<prefix\>\_monthly.csv — 12 satır: month, r4ha_peak_tps, software_cost, other_cost

## 9. Kod Yapısı ve Kullanım

Tüm model tek bir Python dosyasında: mainframe_model.py (yaklaşık 1.200 satır, sadece standard library). İki ana kullanım modu var:

### 9.1. Statik Mod

python mainframe_model.py --tps 50000 --availability 0.999 --rni average --latency-ms 200

Tek nokta sorgu — verilen yük için minimum maliyetli kademe + topoloji + aylık maliyet.

### 9.2. Yıllık Mod

python mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000 --availability 0.999 --csv out

Workload profile simülasyonu — yıllık maliyet, strateji karşılaştırması, CSV çıktısı.

### 9.3. Yardımcı Modlar
- --demo: hazır 6 senaryo (latency ile/sız, farklı RNI, farklı uptime)
- --calibration: tüm köprü katsayılarını ve örnek kademeleri yazdırır

## 10. Referanslar ve Kullanım Amaçları

### 10.1. Compute Kapasite ve Throughput Köprüleri
- **\[LSPR\] —** IBM Z LSPR ITR tablosu (resmi). Tüm z16 (128 kademe), z15, z14, z13 kademelerinin baz sistem (z9 2094-701 = 1.00) üzerinden göreceli kapasite oranlarını verir. Modelde LSPR_TO_MIPS köprüsü, CP-güç köprüsü (z16/z13 oranları), tam-hız CP normalizasyonu (4.02) ve tüm Z16_TIERS kademelerinin temelidir. https://www.ibm.com/support/pages/node/6953823
- **\[EPS\] —** Scott Chapman, "Exploring z/OS WLM CPU Measurements", Enterprise Performance Strategies. IBM ResourceLink referansıyla 3931-604 modelinin mutlak kapasite çapasını verir: 5511 PCI = 675 MSU = 70.484 SU/saniye. LSPR oranını mutlak MIPS ve MSU'ya çeviren iki köprünün (LSPR_TO_MIPS ve MSU_PER_MIPS) tek kaynağıdır. Olmadan model çalışmaz. https://www.epstrategies.com/library/content/Chapman_Exploring_CPU_Measurements.pdf
- **\[REDP\] —** IBM Redpaper REDP-5320, "IBM CICS Performance Series: CICS TS V5.3 Benchmark on IBM z13" (Burgess, Mitchell, Moxey). İki noktalı throughput çapası: 18 CP → 174.000 TPS, 26 CP → 227.000 TPS. CP-güç köprüsünün kalibrasyon dayanağıdır; ayrıca iki nokta arası fark sublinearite gözlemini sağlar. https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf

### 10.2. Availability
- **\[REDBOOK\] —** IBM Redbook SG24-8446, "Getting Started with IBM Z Resiliency" (White, Coq). 4-model availability çerçevesinin (M1-M4) ve her topolojinin tasarım hedefleri/RTO-RPO değerlerinin temelidir. Modelin Topology sınıfının tüm yapısı bu kaynaktan alınmıştır. https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf
- **\[ITIC\] —** ITIC Global Server Reliability Surveys 2020-2024. Bağımsız endüstri anketleri (1.200-1.950 işletme/yıl); mainframe gerçek uptime ölçümleri. Her topolojiye atanan hw_low (alt sınır) rakamının kaynağıdır. Vendor iddiası ile bağımsız ölçümün ikili sunumunu sağlar. https://itic-corp.com/
- **\[PRECISELY\] —** Precisely, High Availability definition. Endüstri kuralı: toplam downtime'ın yaklaşık %90'ı planlı outage'lardan kaynaklanır. effective_availability hesabındaki ×10 çarpanının (planlı kesinti indirimi) kaynağıdır. https://www.precisely.com/glossary/high-availability-ha/

### 10.3. CoD ve Yıllık Simülasyon
- **\[COD\] —** IBM SC28-7025, "IBM Z and LinuxONE Capacity on Demand User's Guide". On/Off CoD'nin teknik yapısı (gün-bazlı faturalandırma, 24-saatlik aktivasyon periyodu, prepaid/postpaid modelleri). Yıllık simülasyondaki CoD modülünün temelidir. Gün başına dolar fiyatı kapalı, premium çarpanı 2.5 \[ASSUME\]. https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf
- **\[CFCC\] —** IBM Coupling Facility Configuration Options (Raften), IBM Z Resiliency Redbook ve ilgili IBM dokümanları. ICF (Internal Coupling Facility) specialty engine olduğu için kapasite derecelendirmesini etkilemez ve yazılım lisansını artırmaz. M2 topolojisinin software_premium = 1.0 kalmasının (ek frame eklenmesine rağmen) gerekçesidir.

### 10.4. Maliyet Veriileri (Yarı-Kapalı)
- **\[PRICE\] —** Bağımsız mainframe fiyat rehberleri (electronics.alibaba buying guides serisi). z15/z16 donanım fiyat aralığı (\$0.5M-\$10M+), yıllık bakım donanım değerinin %10-15'i, alt ekonomik eşik ~150 MIPS. HARDWARE_COST_PER_MIPS = \$200 ve MAINTENANCE_RATE_ANNUAL = 0.125 değerlerinin kaynağıdır. Açık liste fiyatı olmadığı için kestirim.
- **\[LIC\] —** MLC/MSU lisanslama kaynakları (atonementlicensing.com, redresscompliance.com). Tipik kurumsal 600-2500 MSU → aylık \$15K-\$80K → ~\$25-55/MSU/ay aralığı. SOFTWARE_COST_PER_MSU_MONTH = \$40 (orta değer) bu kaynaktan.
- **\[PWR\] —** Aynı fiyat rehberi (electronics.alibaba) enerji ölçütleri. z15/z16 frame başına 20-40 kW; modelde POWER_KW_PER_SYSTEM = 30 kW (orta).

### 10.5. Teorik Temel
- **\[QUEUE\] —** M/M/1 kuyruk teorisi (klasik OR). Mainframe WLM/RMF response time percentile metodolojisiyle uyumlu (IBM bunu SMF 72.3 / 110.1 ile ölçer). max_utilization_for_latency() ve expected_latency_at() fonksiyonlarının matematiksel temeli.

## 11. Modelin Bilinen Eksikleri ve Sonraki Geliştirmeler

### 11.1. Kalibre Edilmemiş Parametreler \[ASSUME\]
- RNI low (1.25) ve high (0.70) çarpanları — gerçek IBM LSPR Low/High sütunlarından kalibre edilebilir
- HARDWARE_COST_PER_MIPS (\$200) — doğrusal kestirim, gerçek fiyat eğrisi farklı olabilir
- GDPS software premium (M3: 1.15, M4: 1.30) — IBM premium fiyatı kapalı
- COD_DAILY_MULTIPLIER (2.5) — IBM gün başına dolar fiyatı kapalı
- ELECTRICITY_USD_PER_KWH (\$0.12) — ABD ticari ortalama, coğrafyaya göre değişir

### 11.2. Yapısal Basitleştirmeler
- Per-CP M/M/1 latency modeli M/M/c'ye yükseltilebilir (daha az tutucu); iki tarafta aynı kuyruk ailesi kullanılmalı
- Network ve disk I/O latency ihmal edildi — mainframe'de küçük ama clustered tarafa eklenecek
- Yedek sistemler tam maliyetle sayılıyor (stand-by'da aslında daha az kaynak)
- z16 LSPR tablosunun 128 kademesinden ~28 temsili kademe modele alındı — tamamı eklenebilir

### 11.3. TCO Genişlemesi (Phase 2)

Mevcut model mainframe TCO'sunun yaklaşık %40-50'sini modeller. Phase 2'de eklenecek:
- CICS Transaction Server lisansı (MSU bazlı)
- Db2 for z/OS lisansı (MSU bazlı)
- DS8900F storage modeli (kapasite TB + IOPS + maliyet)
- Operasyon personeli (sysprog + DBA, kişi sayısı kapasiteyle ölçeklenir)

### 11.4. Sonraki Aşamalar
- Phase 2: Stokastik arıza modeli (MTBF/MTTR, downtime istatistikleri)
- Phase 3: Monte Carlo (1000+ yıl-replikasyonu, ortalama + percentile + tail risk)
