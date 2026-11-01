# Mainframe (Scale-Up) Modelinin Detaylı Dokümantasyonu — v3

*IBM z16 A01 (3931) · compute kapasitesi, latency, availability, yazılım yığını (AWLC: z/OS, CICS TS, Db2) ve zIIP, storage (DS8900F), yıllık simülasyon, Capacity-on-Demand ve Tailored Fit Pricing*

Bu doküman mainframe modelinin **güncel halini** anlatır: hangi veri hangi kaynaktan alındı, nasıl işlendi, modele nasıl girdi. Değişikliklerin tarihçesi ve gerekçeleri `PROJECT_LOG.md` dosyasındadır. Önceki sürüm (`mainframe_model_documentation_v2.md`) tarihsel kayıt olarak değiştirilmeden tutulur.

Etiketler: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** resmî veriden hesaplanmış, doğrulaması belirtilmiş değer · **(doğrulanmalı)** kaynakla henüz teyit edilmemiş bilgi.

## 1. Modelin Amacı ve Kapsamı

### 1.1. Cevaplanan Soru

Verilen bir iş yükü (throughput, işlem karmaşıklığı, latency hedefi, availability hedefi) için, bu iş yükünü karşılayan minimum maliyetli feasible IBM z16 A01 konfigürasyonu hangisidir ve aylık/yıllık maliyeti nedir?

### 1.2. Mevcut Kapsam

- z16 A01'in 317 kapasite kademesinin tamamı (Bölüm 3)
- Benchmark tabanlı kapasite köprüsü: PCI başına TPS (Bölüm 4)
- Bileşimli iş yükü profili: okuma/yazma SQL sayısından CPU ağırlığı ve I/O (Bölüm 4.4)
- Per-CP M/M/1 kuyruğu + sabit I/O gecikmesiyle latency feasibility (Bölüm 5)
- IBM Z Resiliency 4-model availability çerçevesi (M1–M4) (Bölüm 6)
- Kademe başına resmî MSU ile sub-capacity yazılım faturası: z/OS + CICS TS + Db2, AWLC kademeli kümülatif fiyat (Bölüm 7.1)
- zIIP: MSU dışı kapasite payı ve zIIP motor donanımı (Bölüm 7.1.5)
- Donanım amortismanı, bakım, enerji (Bölüm 7)
- Storage katmanı: IBM DS8900F boyutlandırması (veri hacmi, IOPS, topolojiye bağlı kopya sayısı), maliyeti ve I/O gecikmesi; zHyperLink, zHPF/FICON, Metro/Global Mirror, Safeguarded Copy (Bölüm 8)
- Yıllık simülasyon: 8.760 saatlik profil ve üç donanım edinim/fiyatlama stratejisi: Permanent, Base + On/Off CoD ve Tailored Fit Pricing (base + capacity corridor + CoD); On/Off CoD'nin resmî sınırları (Bölüm 9)

### 1.3. Kapsam Dışı

- **z16 A02 / AGZ (makine tipi 3932, rack-mount modeller).** A01'den ayrı bir donanım ailesi; 156 kapasite seviyesi ve Max5/16/32/68 özellikleri var (SG24-8952). Model şu an yalnızca A01'i kapsıyor. Düşük TPS bölgesinde mainframe'in taban maliyetini belirleyebilecekleri için tezde ayrıca belirtilmeli; ileride eklenebilir.
- **3931-400:** Yalnızca Coupling Facility (CF) için kullanılan, MSU derecesi olmayan kapasite ayarı.
- **Messaging (IBM MQ):** proje kararıyla iki tarafta da kapsam dışı.

### 1.4. Henüz Modele Eklenmemiş Bileşenler

GDPS'in ayrı kalem olarak modellenmesi, operasyon personeli, CBU (DR kapasitesi), yedekleme için sanal teyp (TS7700), stokastik arıza modeli. Bkz. Bölüm 12.

## 2. Modelin Girdi ve Çıktıları

### 2.1. Mevcut Girdiler

| **Parametre** | **Açıklama** | **Tipik aralık** |
|---|---|---|
| tps | Saniyedeki işlem sayısı | 1.000 – 1.500.000 |
| workload | İş yükü profili: işlemin bileşimi (Bölüm 4.4) | redp_light / tpcb_like / oltp_rw (varsayılan) / oltp_heavy, ya da --sql-reads / --sql-writes |
| latency_ms + percentile | Hedef latency | ör. p99 < 200 ms |
| availability | Hedef uptime | 0.999 – 0.99999999 |
| [yıllık] preset | Workload preset adı | steady_oltp / retail_bursty / batch_heavy |
| [yıllık] avg_tps + peak_ratio + peak_days | Custom workload tanımı | ör. 10K TPS, 3.5×, 20 gün |
| data_tb | Mantıksal Db2 veri hacmi (indeksler dahil), TB | 1 – 5.000 (varsayılan 20) |
| data_growth | Yıllık veri büyümesi | 0 – 0,5 (varsayılan 0,15) |

Projenin 8 girdisinden rpo_seconds ve rto_minutes henüz modele bağlı değil (DR adımıyla gelecek). IOPS kullanıcıya sorulmaz; TPS × iş yükü profilinin bileşiminden türetilir.

### 2.2. Çıktılar

Statik mod (tek nokta sorgu):
- Seçilen z16 kademesi (örn. 3931-436) ve topoloji (M1/M2/M3/M4)
- Tam-hız CP eşdeğeri, utilization, dinamik utilization tavanı, tahmini percentile latency
- Aylık maliyet dökümü: yazılım (z/OS + CICS TS + Db2) + donanım (zIIP dahil) + bakım + enerji + storage

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

**TPS_PER_PCI = 7,939** (iki noktanın ortalaması; birim: REDP-5320 işlemi, Bölüm 4.4).

İki nokta arasındaki %3,1'lik fark, benchmark iş yükünün LSPR karışımından biraz daha kötü ölçeklendiğini gösterir. Model ortalamayı kullanır; fark köprünün belirsizlik aralığı olarak raporlanır.

### 4.3. Kademe Kapasitesi

7,939, **REDP-5320 işlemi** cinsinden bir katsayıdır (Bölüm 4.4). Bir iş yükünün kademe kapasitesi, işlemin bu baza göre CPU ağırlığına (w) bölünerek ve zIIP'e kayan pay (f) düşülerek bulunur:

ham_TPS(kademe, profil) = PCI × 7,939 / w / (1 − f)

| Kademe | PCI | REDP işlemi, ham | oltp_rw (w = 9,15, f = 0,10), ham | oltp_rw, %90 tavanda |
|---|---|---|---|---|
| 3931-401 | 280 | 2.223 | 270 | 243 |
| 3931-604 | 5.511 | 43.752 | 5.314 | 4.782 |
| 3931-701 | 2.253 | 17.887 | 2.172 | 1.955 |
| 3931-718 | 30.241 | 240.084 | 29.157 | 26.242 |
| 3931-739 | 57.733 | 458.344 | 55.664 | 50.098 |
| 3931-7A0 | 123.799 | 982.843 | 119.362 | 107.426 |
| 3931-7K0 | 215.099 | 1.707.676 | 207.390 | 186.651 |

Tam-hız CP eşdeğeri (bilgi amaçlı) = PCI / 2.253 (3931-701).

### 4.4. İş Yükü Profili — "1 İşlem"in Bileşimle Tanımı

#### 4.4.1. Sorun: benchmark işlemi çok hafif

REDP-5320 benchmark'ının işlem profili raporun kendi sayaçlarından çıkarıldı (`data/raw/redp5320_workload_profile.csv`) [REDP-PROFILE]:

| Ölçü (18 CP, 174.624 TPS) | Değer | İşlem başına |
|---|---|---|
| Shared data table okuması | 831.835 /s | 4,76 |
| Read for update + rewrite | 8.257 /s | 0,047 |
| Coupling facility log yazımı | 10.878 /s | 0,062 |
| CICS CPU | 1.499,4 % (bir CP) | 85,9 µs (z13) |

26 CP noktası aynı profili verir (4,81 okuma, 0,038 güncelleme, 93,3 µs). İşlem 1 STARTBROWSE + 5 READNEXT'tir. Veri, bellekte tutulan bir CICS shared data table'dadır (arkasında VSAM KSDS). Db2, DRDA, Java ve zIIP yoktur. DASD I/O'su neredeyse sıfırdır ve yanıt süresi raporlanmamıştır.

Bu yüzden köprünün ölçtüğü "1 işlem", gerçekçi bir Db2 OLTP işleminden çok daha hafiftir. Gerçek bir CICS-Db2 işleminin yalnızca Db2 içindeki CPU süresi bir sahada 1,25–1,32 ms ölçülmüştür [CATTERALL-2019], yani REDP işleminin ~15 katı. Önceki sürüm bu farkı görmüyordu: kapasiteyi bu hafif işlemle hesaplarken latency ve storage için işlem başına 10 disk I/O varsayıyordu. Bu iki varsayım birbiriyle tutarsızdı ve mainframe kapasitesini olduğundan yüksek gösteriyordu. Değerlendirme #1'deki "TPS iki tarafta ortak bir birim değil" tehdidinin mainframe yarısı budur.

#### 4.4.2. Çözüm: bileşimli profil

Bir işlem, iki tarafın da ölçebileceği bileşenlerle tanımlanır: okuma SQL sayısı, yazma SQL sayısı (INSERT/UPDATE/DELETE) ve commit. CPU ağırlığı ve I/O bu bileşimden hesaplanır:

```
CPU(µs) = 85,9 + okuma × 30 + yazma × 70          (z13 CP-µs)
w       = CPU / 85,9                              (REDP işlemi: w = 1)
sync_io = okuma × 4 × (1 − 0,95) + commit × 1     (Db2 buffer pool kaçağı + commit log yazımı)
IOPS    = sync_io + yazma × 0,5                   (deferred write'lar storage'a)
```

| Parametre | Değer | Dayanak |
|---|---|---|
| CPU_US_TM_BASE | 85,9 µs | REDP işleminin kendisi; transaction yöneticisi + küçük bellek okumaları [REDP-PROFILE] |
| CPU_US_PER_SQL_READ | 30 µs | [ASSUME] tekil/indeksli SELECT; 15–60 taranır |
| CPU_US_PER_SQL_WRITE | 70 µs | CICS programında tek INSERT ~68 µs [CATTERALL-2012] |
| GETPAGES_PER_SQL_READ | 4 | [ASSUME] indeks seviyeleri + veri sayfası |
| BP_HIT_RATIO | 0,95 | [ASSUME] OLTP buffer pool isabeti; 0,90–0,99 taranır |
| LOG_SYNC_IO_PER_COMMIT | 1 | [ASSUME] commit'te senkron log yazımı (dual log paralel) |
| ASYNC_WRITE_IO_PER_SQL_WRITE | 0,5 | [ASSUME] deferred write, sayfa birleştirme |

Bütün CPU değerleri z13 dönemine aittir. w bir **oran** olduğu için nesilden bağımsızdır: hem REDP işlemi hem SQL maliyetleri aynı nesilde ölçülmüş kabul edilir ve z16'ya LSPR/PCI üzerinden taşınır.

#### 4.4.3. Hazır profiller

| Profil | Bileşim | w | sync I/O | IOPS | Tek z16 (7K0) tavanı | Kaynak |
|---|---|---|---|---|---|---|
| redp_light | Benchmark işlemi (Db2 yok, zIIP yok) | 1,00 | 0,047 | 0,109 | 1.536.908 TPS | [REDP-PROFILE], ölçülmüş |
| tpcb_like | 1 SELECT + 4 yazma (debit-credit) | 4,61 | 1,20 | 3,20 | 370.521 TPS | TPC-B bileşimi |
| **oltp_rw** (varsayılan) | 14 SELECT + 4 yazma + 1 commit | 9,15 | 3,80 | 5,80 | 186.651 TPS | sysbench oltp_read_write bileşimi |
| oltp_heavy | 30 SELECT + 6 yazma | 16,37 | 7,00 | 10,00 | 104.338 TPS | ~1,3 ms CPU'luk saha ölçümünün büyüklüğü [CATTERALL-2019] |

Varsayılan profil olarak oltp_rw seçildi, çünkü sysbench oltp_read_write x86 tarafında (MySQL, PostgreSQL) en yaygın ölçülen OLTP bileşimidir. Clustered taraf aynı bileşimi kendi ölçümleriyle karşılayabilir ve böylece TPS iki tarafta aynı işi ifade eder. Kullanıcı `--sql-reads` ve `--sql-writes` ile kendi bileşimini tanımlayabilir.

**Makullük kontrolü:** IBM, 2017'de z14 için "günde 12 milyardan fazla şifreli işlem" (~139K TPS) duyurdu [IBM-Z14-PR]. z14'ün en büyük yapılandırması yaklaşık 160K PCI kabul edilirse (z16 200-way'in z15'e göre +%17 olmasından geriye doğru kaba tahmin, doğrulanmalı), bu kapasite REDP işleminden ~1,27M ham TPS eder. Bu durumda IBM'in işlemi w ≈ 9'a karşılık gelir; varsayılan oltp_rw'ye (9,15) çok yakındır. İşlem tanımı açıklanmadığı ve z14 PCI'si tahmin olduğu için bu yalnızca büyüklük mertebesi teyididir.

#### 4.4.4. Etkisi ve sınırlamalar

- **Etki büyük:** varsayılan profil (w = 9,15) aynı TPS için ~9 kat daha fazla mainframe kapasitesi gerektirir. Örneğin 10K TPS'te faturalanan kademe 185 MSU'dan (REDP işlemi) 1.423 MSU'ya çıkar (Bölüm 7.6). Önceki sürümdeki "50K TPS" sonuçları, bugünkü birimle yaklaşık 5,5K oltp_rw TPS'e karşılık gelir.
- **Tek sistem tavanı:** oltp_rw'de en büyük tek z16 ~187K TPS taşır; oltp_heavy'de ~104K. Gerçek kurulumlar bunun üstüne Parallel Sysplex data sharing ile birden fazla CEC'e ölçeklenir. Model bunu henüz içermez: M2–M4'teki ikinci frame yedek olarak sayılır, kapasite eklemez. Yüksek hacimli crossover analizi için bu bir sınırlamadır (Bölüm 12).
- **En kritik varsayım:** CPU_US_PER_SQL_READ. 15–60 µs aralığı w'yi 6,7–14,0 aralığında, 10K TPS'te maliyeti $34,9–53,3/TPS aralığında oynatır (Bölüm 7.1.6 ve `src/tools/workload_sensitivity.py`). BP_HIT_RATIO yalnızca I/O'yu ve D_io'yu etkiler (0,90 → 0,46 ms; 0,99 → 0,11 ms), maliyeti etkilemez.
- LSPR'nin Low/High RNI sütunları (cache/bellek yoğunluğu, ~±%10–15) ayrı bir etkidir ve modellenmez. Önceki RNI çarpanları (1,25 / 1,00 / 0,70) kaynaksız olduğu için kaldırıldı.

### 4.5. Akademik Notlar

- LSPR oranları IBM'in kendi iş yükü karışımında ölçülür. CICS/Db2 OLTP iş yükünün bu karışıma benzediği bir varsayımdır.
- z13 değerleri z/OS 2.2 LSPR tablosundan, z16 değerleri güncel ITRR tablosundan alındı. İkisi de aynı bazı kullanıyor, ama farklı z/OS seviyelerinde ölçülmüş olabilir.
- Köprünün tek kaynağı REDP-5320. Bileşimli profil, köprüyü gerçekçi Db2 işlemlerine taşıyan SQL maliyetleri için ikincil, tek sahalık kaynaklara dayanır. IBM'in IRWW (Db2 OLTP iş yükü) ölçümleri yalnızca göreli olarak yayımlandığı için mutlak bir ikinci çapa bulunamadı.

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

Sabit I/O gecikmesi: D_io = sync_io(profil) × t_io. sync_io, iş yükü profilinin bileşiminden gelir (Bölüm 4.4: Db2 buffer pool kaçağı + commit log yazımı). t_io, storage katmanından gelir (Bölüm 8.6): okuma/yazma oranı, DS8900F önbellek isabeti, zHyperLink ve zHPF/FICON servis süreleri, senkron replikasyonun mesafe gecikmesi. Varsayılanlarla t_io M1'de 69 µs, senkron kopyalı topolojilerde (M2–M4) 129 µs; oltp_rw profilinde (3,8 senkron I/O) D_io sırasıyla 0,26 ms ve 0,49 ms.

R(p) = D_io + R_cpu(p)

ρ_max = min( 1 − E[X_cpu] · ln(1/(1−p)) / (hedef − D_io) , 0,90 )

Hedef ≤ D_io ise ya da boş sistemdeki CPU süresi bile bütçeyi aşıyorsa kademe infeasible olur (ρ_max = 0).

### 5.4. Basitleştirmeler ve Sınırlamalar

- Operasyonel tavan (0,90) her zaman geçerli. Latency hedefi tavanı yalnızca düşürebilir; daha sıkı SLA hiçbir zaman daha ucuz sonuç vermez.
- Senkron I/O'lar sıralı sayılır (tutucu). Asenkron yazmalar latency'ye girmez, yalnızca storage IOPS'una girer.
- Network (iç fabric) ve lock/latch beklemesi modellenmez. Clustered taraf aynı yapıyı (aynı kuyruk ailesi + D_io + ağ gecikmesi) kullanmalıdır.

### 5.5. Davranış

Latency hedefi 3–500 ms aralığında, 3 profil (redp_light, oltp_rw, oltp_heavy) × 5 TPS seviyesi için tarandı (test_latency_monotonic). Maliyet hiçbir senaryoda hedef sıkılaştıkça azalmadı. Örnek (oltp_rw, 10K TPS, M1):

| p99 hedefi | Kademe | Aylık toplam |
|---|---|---|
| yok | 3931-516 | $416.750 |
| 50 ms | 3931-706 | $417.811 |
| 10 ms | 3931-708 | $435.955 |
| 5 ms | 3931-714 | $487.048 |
| 2 ms | infeasible | |

Latency'siz durumda model yavaş alt-kapasite CP'li 5xx kademesini seçer. Hedef sıkılaştıkça tam-hız CP'li 7xx kademelerine kayar. oltp_rw'de alt sınır ~2,4 ms'dir: en hızlı tek CP'de işlem başına CPU süresi ~0,46 ms, p99 çarpanı ln(100) ≈ 4,6 ve D_io 0,26 ms. Bu, işlem bileşiminin latency'yi de doğrudan belirlediğini gösterir.

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

### 7.1. Yazılım Yığını (z/OS + CICS TS + Db2, AWLC kademeli)

#### 7.1.1. Katmanın savunması

Bir OLTP iş yükü mainframe'de yalnızca işletim sistemiyle çalışmaz: transaction yöneticisi (CICS TS) ve veritabanı (Db2 for z/OS) da MSU bazlı aylık lisansla (MLC) faturalanır. Clustered tarafta da aynı üç katmanın karşılığı (işletim sistemi, uygulama sunucusu/transaction katmanı, veritabanı) bulunacağından, karşılaştırmanın eşit derinlikte olması için üç ürünün de modellenmesi gerekir. MQ, proje kararıyla iki tarafta da kapsam dışıdır.

Önceki sürüm tek bir $40/MSU/ay fiyatı kullanıyordu. Bu değer, metodolojisi açıklanmamış bir lisans danışmanlığı sitesinden geliyordu ve iki sorunu vardı:

1. **Yapı hatası:** IBM AWLC fiyatı doğrusal değildir. Fatura kümülatif kademelidir: her MSU, düştüğü kademenin marjinal fiyatıyla ücretlenir ve marjinal fiyat MSU arttıkça düşer [IBM-ZNALC]. Doğrusal fiyat, mainframe'in en belirgin ölçek ekonomisini modelden siler. Değerlendirme #1'deki "maliyet/TPS neredeyse düz" tehdidinin ana sebebi buydu.
2. **Seviye hatası:** IBM'in kendi yayımladığı örnek fatura, 265 MSU'luk bir sistemde yalnızca z/OS için aylık $75.459 gösteriyor [IBM-2004]. Bu MSU başına ~$285 eder; $40, bunun yalnızca z/OS için bile ~7'de biridir.

#### 7.1.2. Veri ve kaynaklar

- **Kademe sınırları (resmî, güncel):** Base 1–3 MSU, L0 4–45, L1 46–175, L2 176–315, L3 316–575, L4 576–875, L5 876–1.315, L6 1.316–1.975, L7 1.976+ [CMG-2020], [IBM-ZNALC]. Kademe her ürün için ayrı uygulanır.
- **Kademe düşüş eğrisi:** IBM'in yayımladığı Db2 liste fiyatı (aylık): Base $3.960 (ilk 3 MSU dahil), L0 $208/MSU, L1 $88, L2 $66, L3 $50 [IBM-2004].
- **L4 ve üstü:** Kamuya açık fiyat bulunamadı. Longpela'nın "L7'nin MSU fiyatı L6'dan ~%20 düşük" gözlemi [LONGPELA] esas alınarak kademe başına ×0,80 geometrik düşüş varsayıldı: L4 $40, L5 $32, L6 $25,6, L7 $20,48 [ASSUME].
- **Ürün katsayıları:** IBM'in aynı belgedeki örnek faturası (aylık, sub-capacity): z/OS $75.459 (265 MSU), CICS TS $32.978 (210 MSU, ayrı LPAR), Db2 $31.876 (265 MSU) [IBM-2004]. Katsayı = ürünün örnek bedeli / referans eğrinin aynı MSU'daki değeri. Sonuç: z/OS ×2,509, CICS TS ×1,247, Db2 ×1,060. Kalibrasyon kodda hesaplanır (`_calibrate_products`), elle girilmez.
- **Mutlak seviye:** SW_PRICE_LEVEL_FACTOR = 1,0, 2004 nominal liste fiyatı demektir [ASSUME]. Güncel seviye iki yöne çekilir: IBM'in yeni donanım nesillerinde verdiği Technology Update indirimleri (z17 TU11: kademe bandına göre %12–42) aşağı, 20 yıllık enflasyon ve IBM'in periyodik fiyat artışları yukarı. Bu yüzden 0,5–1,5 aralığı duyarlılık analizinde taranır (Bölüm 7.1.6).

#### 7.1.3. Formül

Referans eğri (Db2, 2004 USD):

```
C_ref(m) = 3.960 + Σ_k  (min(m, üst_k) − alt_k)⁺ × fiyat_k     (k = L0…L7)
```

Yazılım yığını:

```
yazılım(m) = C_ref(m) × SW_PRICE_LEVEL_FACTOR × (k_z/OS + k_CICS + k_Db2) × topology.software_premium
```

m, faturalanan MSU'dur (sub-capacity, R4HA tepesi):

```
faturalanan_MSU = min(R4HA_yük / ham_TPS, 1) × kademe.MSU
```

GDPS primi M3 için ×1,15, M4 için ×1,30 [ASSUME]; ICF ek frame'i lisansı artırmaz [CFCC]. Yıllık moddaki TFP-SW gelir-nötr kalibrasyonu bu fonksiyonla aynen çalışır: efektif MSU-saat fiyatı, Permanent stratejinin kademeli R4HA faturasından türetilir.

#### 7.1.4. Doğrulama

| MSU | Aylık yığın | $/MSU/ay | z/OS | CICS TS | Db2 |
|---|---|---|---|---|---|
| 35 | $51.124 | 1.461 | $26.635 | $13.238 | $11.251 |
| 150 | $105.639 | 704 | $55.036 | $27.354 | $23.249 |
| 265 | $144.840 | 547 | $75.459 | $37.505 | $31.876 |
| 785 | $263.790 | 336 | $137.430 | $68.305 | $58.054 |
| 1.524 | $374.699 | 246 | $195.212 | $97.024 | $82.463 |
| 3.059 | $537.212 | 176 | $279.879 | $139.105 | $118.229 |
| 7.513 | $976.498 | 130 | $508.739 | $252.853 | $214.906 |

- 265 MSU satırı IBM örneğini yeniden üretir (z/OS ve Db2 birebir; CICS 265 MSU'ya ölçeklendiği için örnektekinden yüksek).
- Bağımsız kontrol: value-4it, ~150 MSU'luk bir sistem için yıllık ~£1M yazılım maliyeti raporluyor [VALUE4IT]. Model 150 MSU'da yıllık ~$1,27M (~£1,0M) veriyor. Kaynak ürün listesini açıklamadığı için bu yalnızca büyüklük mertebesi teyididir.

#### 7.1.5. zIIP (specialty engine)

zIIP, Db2 DRDA istekleri, Java, XML ve bazı Db2 sistem görevlerini (prefetch, log yazımı, utility) genel amaçlı CP'den alan bir specialty engine'dir. zIIP kapasitesi MSU'ya sayılmaz, yani MLC faturasına girmez. Donanımı GP'den ucuzdur ve alt-kapasite (4xx/5xx/6xx) modellerde bile tam hızda çalışır. z16'da zIIP sayısı en fazla 2 × GP CP olabilir.

Modelde:

- ZIIP_OFFLOAD_FRACTION = f = 0,10 [ASSUME]. Uygunluk iş yüküne bağlıdır: yerel CICS-COBOL-Db2 OLTP'de düşüktür (~%0–10), DRDA/Java ağırlıklı OLTP'de %40'a çıkabilir. Varsayılan bilinçli olarak muhafazakâr tutuldu, çünkü yüksek bir değer mainframe lehine bir yanlılık yaratır. 0–0,40 aralığı taranır.
- Kapasite: GP kademesi 1/(1 − f) kat daha fazla transaction taşır (`raw_tier_tps`). Aynı TPS için daha küçük GP kademesi ve daha az faturalanan MSU gerekir. CoD/corridor hesabındaki tüketilen PCI de (1 − f) ile ölçeklenir.
- Donanım: zIIP sayısı = ⌈kademe.PCI × f/(1 − f) / 2.253⌉, en fazla 2 × CP. 2.253, tek tam-hız motorun (3931-701) PCI'sidir. zIIP bedeli = n × 2.253 × HARDWARE_COST_PER_MIPS × ZIIP_HW_PRICE_FACTOR (0,25 [ASSUME]). Bedel donanıma eklenir, amortisman ve bakım ona göre işler.
- Basitleştirme: zIIP'te çalışan payın latency'ye etkisi ayrıca modellenmez; per-CP servis süresi GP'deki işe göre hesaplanır.
- Kapsam notu: köprü benchmark'ı (REDP-5320, CICS/COBOL) zIIP kullanmaz. f, iş yükü profiline özgü bir ek parametredir ve REDP-5320 profil adımında (yol haritası) daraltılmalıdır.

#### 7.1.6. Duyarlılık

`python src/tools/software_sensitivity.py` (10K TPS, oltp_rw, %99,9, 20 TB):

| Parametre | Değer → aylık toplam ($/TPS/ay) |
|---|---|
| Eski doğrusal $40/MSU | $127.055 (12,71), yazılım payı %40 |
| SW_PRICE_LEVEL_FACTOR | 0,5 → $246.766 (24,68) · 1,0 → $416.750 (41,68) · 1,5 → $586.734 (58,67) |
| ZIIP_OFFLOAD_FRACTION | 0 → $438.536 (43,85, 3931-518) · 0,10 → $416.750 (41,68, 516) · 0,25 → $378.142 (37,81, 513) · 0,40 → $337.756 (33,78, 510) |
| L4+ düşüş oranı, 10K TPS | ×1,0 → $464.296 (46,43) · ×0,8 → $416.750 (41,68) · ×0,7 → $395.736 (39,57) |
| L4+ düşüş oranı, 100K TPS | ×1,0 → $3.669.535 (36,70) · ×0,8 → $2.091.656 (20,92) · ×0,7 → $1.626.046 (16,26) |

Yorum:

- Yazılım en büyük kalemdir: 10K TPS'te toplamın %82'si, 180K TPS'te %67'si. Bu yön, mainframe TCO literatüründe yazılımın en büyük kalem olarak raporlanmasıyla tutarlıdır. Ancak oran, donanım fiyatı ve personel henüz kaba ya da eksik olduğu için olduğundan yüksek görünmektedir.
- Mutlak seviye toplamı yaklaşık ±%40 oynatır, ama maliyet/TPS eğrisinin **şeklini** değiştirmez. Crossover noktasının **yeri** bu parametreye duyarlıdır; varlığı ise değildir.
- L4+ düşüş oranı, faturalanan MSU 575'i aştığında devreye girer. oltp_rw'de bu ~4K TPS'e karşılık gelir; yani gerçekçi işlemle bu varsayım çok daha erken bağlayıcı olur. 100K TPS'te (13.603 MSU) $/TPS'i 16,3–36,7 aralığında, yani 2 kattan fazla oynatır. Yüksek hacimli crossover analizinde en kritik yazılım varsayımı budur. Tezde böyle raporlanmalı ve gerçek bir AWLC fiyat tablosuyla daraltılmalıdır.
- İş yükü profilinin CPU varsayımları (Bölüm 4.4.4) faturalanan MSU'yu, dolayısıyla yazılımı doğrudan belirler: CPU_US_PER_SQL_READ 15 → 60 µs, 10K TPS'te maliyeti $349K'dan $533K'ya taşır.

### 7.2. Donanım Amortismanı

Mainframe donanım fiyatları açık liste olarak yayınlanmaz. Birden çok bağımsız fiyat rehberinin verdiği aralık birleşik olarak ~\$500.000 (giriş seviyesi) ile ~\$10.000.000+ (tam kapasite, üretim grade) arasındadır. Modelde MIPS başına kabaca doğrusal kestirim:

HARDWARE_COST_PER_MIPS = \$200 / MIPS — \[PRICE → ASSUME\]

aylık donanım = (kademe.PCI × \$200 + zIIP bedeli) / (5 yıl × 12 ay)

zIIP bedeli Bölüm 7.1.5'te tanımlıdır.

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

total = yazılım(faturalanan_MSU) × software_premium + (hardware_amort + maintenance + energy) × n_frames + storage

Yazılım kalemi kapasite-MSU bazlı olduğu için frame sayısıyla çarpılmaz; donanım, bakım ve enerji çarpılır [CFCC].

### 7.6. Maliyet / TPS Eğrisi (mevcut varsayımlarla)

Statik mod, availability 0,999 (M1), 20 TB veri, f = 0,10. Ana sütunlar varsayılan oltp_rw profilidir; son sütun karşılaştırma için REDP işlemini verir:

| TPS | Kademe (oltp_rw) | Kademe MSU | Aylık toplam | Yazılım payı | $/TPS/ay | $/TPS/ay (redp_light) |
|---|---|---|---|---|---|---|
| 500 | 3931-403 | 100 | $87.373 | %80 | 174,75 | 71,18 |
| 1.000 | 3931-405 | 158 | $116.657 | %83 | 116,66 | 43,48 |
| 2.000 | 3931-410 | 295 | $168.169 | %85 | 84,08 | 29,62 |
| 5.000 | 3931-429 | 720 | $279.981 | %84 | 56,00 | 18,06 |
| 10.000 | 3931-516 | 1.423 | $416.750 | %82 | 41,68 | 12,63 |
| 20.000 | 3931-621 | 2.758 | $621.089 | %77 | 31,05 | 9,26 |
| 50.000 | 3931-739 | 6.768 | $1.167.096 | %72 | 23,34 | 6,20 |
| 100.000 | 3931-792 | 13.603 | $2.091.656 | %69 | 20,92 | 4,61 |
| 180.000 | 3931-7J1 | 24.321 | $3.562.411 | %67 | 19,79 | 3,61 |

- **Eğri bükülüyor.** AWLC'nin sabit taban ücreti ve MSU arttıkça düşen marjinal fiyatı yüzünden, oltp_rw'de 500'den 180K TPS'e maliyet/TPS ~9 kat düşer. Önceki sürümdeki doğrusal fiyatla eğri düzdü ($1,35–1,44/TPS). Bu, Değerlendirme #1'in "mainframe maliyet/TPS'i düz, çoklu crossover hipotezi zayıf" tehdidine kaynaklı bir mekanizmayla verilen cevaptır.
- **Bükülme bölgesi, işlem tanımıyla kayar.** oltp_rw'de ölçek ekonomisinin çoğu ~20K TPS'e kadar gerçekleşir. Bunun üstünde faturalanan MSU L7 kademesine (1.976+) girer, marjinal fiyat sabitlenir ve eğri ~$20/TPS'e yaklaşır. REDP işleminde aynı bölge ~9 kat daha yüksek TPS'e kayar. Crossover noktasının yeri işlem bileşimine doğrudan bağlıdır.
- **Tek sistem tavanı.** oltp_rw'de ~187K TPS'in üstü tek z16 ile karşılanamaz (Bölüm 4.4.4).

Kademe seçimi de değişti: aynı kapasiteyi daha düşük MSU ile veren kademe açıkça avantajlıdır (örn. 10K TPS'te alt-kapasite 3931-516). Bu davranış gerçek kapasite planlamasıyla uyumludur. Düşük hızlı CP'lerin latency etkisi ise yalnızca latency hedefi verildiğinde bağlayıcı olur (Bölüm 5.5).

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

Modelin sonuçları bu öngörüyü doğruluyor: 10K TPS'te (oltp_rw) storage, 20 TB veride toplamın %1,8'i iken 500 TB'ta %27'si, 2.000 TB'ta %60'ı (Bölüm 8.7). Compute sabit kalırken storage veri hacmiyle büyüdüğü için veri hacmi, TPS'ten bağımsız ikinci bir crossover ekseni oluşturuyor. Bu, Değerlendirme #1'de zayıf bulunan çoklu crossover hipotezini destekleyen ilk somut mekanizmadır.

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
| IOPS = tepe TPS × IOPS/işlem (iş yükü profilinden) | Kullanıcı IOPS girdisi | Proje kararı: kullanıcıya IOPS sorulmaz; işlem bileşiminden (okuma/yazma SQL, buffer pool isabeti) türetilir ve iki tarafa da aynı bileşimle taşınır | Profilin I/O parametreleri hem dizi seçimini hem D_io'yu belirler (Bölüm 4.4) |
| Kopya başına en ucuz model; dizi sayısı = max(kapasite, IOPS ihtiyacı) | Sabit model | Kapasite ve IOPS iki ayrı darboğazdır; az veri + yüksek TPS IOPS ile, çok veri + düşük TPS kapasiteyle boyutlanır | oltp_rw'de ~104K TPS'te (IOPS tavanıyla) IOPS darboğazı DS8950F'e geçişi zorlar |
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
| İşlem başına I/O | oltp_rw: 3,8 senkron, 5,8 toplam | Bileşimli profil (Bölüm 4.4): BP_HIT_RATIO 0,95, GETPAGES_PER_SQL_READ 4 | BP_HIT_RATIO 0,90–0,99 | Gerçek bir Db2 accounting (SMF 101) örneği |

#### 8.1.5. Geçerlilik tehditleri

- **İç geçerlilik (fiyat):** Storage maliyetinin mutlak düzeyi büyük ölçüde indirim oranına bağlı; 0,50–0,85 aralığında yaklaşık 3 kat değişiyor. Bu yüzden storage'lı sonuçlar tek bir nokta olarak değil, indirim aralığıyla birlikte raporlanmalı. Göreli sonuçlar (veri hacmiyle doğrusal büyüme, topolojiyle kopya sayısı, IOPS ile model geçişi) indirim oranından bağımsızdır.
- **Yapı geçerliliği (işlem başına I/O):** Önceki sabit 10 I/O, bileşimli profille (Bölüm 4.4) değiştirildi. oltp_rw'de 3,8 senkron + 2 asenkron I/O çıkar. Değer buffer pool isabet varsayımına duyarlıdır (0,90 → 8,6 IOPS/işlem; 0,99 → 3,6). Gerçek bir Db2 accounting örneğiyle daraltılmalıdır.
- **Yapı geçerliliği (IOPS tavanı):** Dizi, üretici tepe IOPS'unun %70'iyle boyutlanıyor. Oranın kendisi varsayım; gerçek OLTP karışımında dizinin sürdürülebilir IOPS'u iş yüküne bağlıdır ve IBM bunu yayımlamıyor. Tavan, compute tarafındaki %90 operasyonel tavanla aynı mantığı (tepe değerde çalışmamak) uygular.
- **Dış geçerlilik:** Tek üretici, 2019–2022 fiyatları, ABD liste fiyatları. Mainframe storage pazarının yaklaşık yarısını temsil eder; diğer yarı (PowerMax, VSP) farklı fiyatlanabilir.
- **Sonuç geçerliliği:** Storage'ın toplam içindeki payı varsayılan veri hacmine (20 TB) bağlı. Tezde storage payı tek bir yüzde olarak değil, veri hacmi ekseninde bir eğri olarak sunulmalı.

#### 8.1.6. Clustered tarafla eşleştirme

Storage, iki tarafın da aynı girdileri kullandığı ortak bir arayüzdür: `data_tb`, `data_growth`, iş yükü profilinden IOPS ve (DR adımıyla) RPO. Clustered tarafın aynı arayüze bağlanırken eklemesi gerekenler: DB mimarisine bağlı kopya sayısı (replication factor), storage yığınının host CPU yükü, ağ üzerinden storage gecikmesi, kendi $/TB ve bakım parametreleri. Mainframe tarafında bu kalemlerin olmaması bilinçli bir asimetridir ve yukarıdaki kararlarla gerekçelendirilmiştir; iki taraf aynı derinlikte, farklı mekanizmalarla modellenir (eşit derinlik ilkesi, `project_context_restore_v4.md`, 3.7).

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

IOPS ihtiyacı = tepe TPS × storage_iops(profil) (Bölüm 4.4; oltp_rw'de 5,8). Her kopya için en ucuz model seçilir: dizi sayısı = max(⌈ham_TB / maks_TB⌉, ⌈IOPS / (0,70 × maks_IOPS)⌉). 0,70, STORAGE_IOPS_CEILING'dir [ASSUME]: dizi üretici tepe IOPS'unun %70'ine kadar yüklenir (gerekçe Bölüm 8.1.3). İkincil kopyalar failover'da birincilin yükünü taşıyabilmek için aynı IOPS'a göre boyutlanır.

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

Sonuç: M1'de 69 µs/I/O. M2–M4'te 129 µs/I/O. oltp_rw'de (3,8 senkron I/O) D_io M1'de 0,26 ms, M2–M4'te 0,49 ms. zHyperLink kapalıyken M1'de 105 µs/I/O (D_io 0,40 ms). Metro Mirror mesafesi 100 km'ye çıkarsa M2'de D_io 1,40 ms. Böylece availability topolojisi latency'yi de etkiler: daha yüksek availability, senkron kopya nedeniyle daha yüksek yazma gecikmesi demektir.

### 8.7. Doğrulama Örnekleri

Statik mod, oltp_rw, 20 TB veri, varsayılan parametreler (AWLC kademeli yazılım ve zIIP dahil):

| Senaryo | Seçim | Storage | Storage / toplam |
|---|---|---|---|
| 10K TPS, %99,9 | M1, 3931-516 | 1× DS8910F-993, 76 TB ham, 58K IOPS, $7.496/ay | %1,8 |
| 10K TPS, %99,999 | M2, 3931-516 | 2× DS8910F-993, $13.778/ay | %2,8 |
| 10K TPS, %99,99999 | M4, 3931-516 | 4× DS8910F-993, $26.344/ay | %4,3 |
| 60K TPS, %99,9 | M1, 3931-749 | 348K IOPS, 1× DS8910F-993, $7.496/ay | %0,6 |
| 150K TPS, %99,9 | M1, 3931-7F2 | 870K IOPS (> 0,7 × 860K) → 1× DS8950F-996, $8.419/ay | %0,3 |

Gerçekçi işlem tanımıyla aynı TPS daha az disk I/O'su (5,8/işlem) ama çok daha fazla CPU ister. Bu yüzden DS8950F'e geçiş ~104K TPS'e kaydı (önceden ~60K) ve storage'ın payı küçüldü.

Veri hacmi ekseni (10K TPS, %99,9): 5 TB'ta storage toplamın %0,7'si, 100 TB'ta %7'si, 500 TB'ta %27'si, 2.000 TB'ta %60'ı. Storage maliyeti veri hacmiyle neredeyse doğrusal büyürken compute sabit kalır. Değerlendirme #3'te öngörülen ikinci crossover ekseni (veri hacmi) mainframe tarafında oluşuyor. Ancak gerçekçi yazılım ve işlem maliyetiyle eksenin belirginleştiği hacim yükseldi: storage'ın toplamın dörtte birini geçmesi artık ~500 TB'ı buluyor. Clustered tarafta kopya sayısı (replication factor) ve $/TB farklı olduğu için iki eğrinin eğimi farklı olacaktır.

Yıllık mod (10K TPS ortalama, 20 TB): 1× DS8910F-993, yıllık ~$90K, toplamın %0,8–1,4'ü; strateji sıralaması değişmiyor (storage üç stratejide de aynı).

### 8.8. Duyarlılık

`python src/tools/storage_sensitivity.py` (10K TPS, oltp_rw, 20 TB, M1, storage aylık maliyeti):

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

Tüketilen GP PCI, yükün %100 kullanım eşdeğeridir (yük × w × (1 − f) / TPS_PER_PCI). Bu, IBM'in "base'in üstünde tüketilen MSU" ölçüsünün modeldeki karşılığıdır: base'in %90 operasyonel tavanı ile %100'ü arasındaki kullanım corridor kapasitesini aktif tutar ama base tüketimini aşmadığı için ücretlendirilmez. İsteğe bağlı sabit abonelik bedeli CORRIDOR_SUBSCRIPTION_RATE ile eklenebilir (varsayılan 0).

Yazılım (Software Consumption Solution) [TFP-SW]: R4HA yerine yıl boyunca tüketilen MSU-saat × efektif MSU-saat fiyatı. IBM efektif fiyatı müşterinin geçmiş 12 ayından belirler; model bunu gelir-nötr olarak kalibre eder: aynı profilin Permanent konfigürasyondaki R4HA faturası, aynı yılın tüketilen MSU-saatine bölünür. TFP_SW_DISCOUNT (varsayılan 0) bu fiyata uygulanan indirimdir. Gelir-nötr kalibrasyon nedeniyle TFP-SW'nin asıl avantajı (büyüme MSU'larının indirimli fiyatı, tepe cezası olmaması) tek yıllık ufukta görünmez; 5 yıllık ufuk adımında modellenecektir.

**Strateji seçimi.** Her availability-feasible topoloji için Strateji A'nın kademesi bulunur; ardından ortalama yükün en az 1,2 katını taşıyan [ASSUME] ve izinli en büyük geçici kademesi peak'i karşılayabilen her base kademe için B ve C simüle edilir. Her strateji için en ucuz sonuç tutulur ve üçü karşılaştırılır. Çok-frame topolojilerde geçici kapasite ücretleri tek frame için hesaplanır; ikinci frame yalnızca failover içindir ve onun geçici kapasitesi CBU konusudur (yol haritası).

### 9.7. Doğrulama Örneği

10K TPS ortalama yük, oltp_rw profili, availability 0,999 (M1), 20 TB veri, varsayılan parametreler. Toplamlara storage dahildir (her presette 1× DS8910F-993, yıllık ~$90K; storage üç stratejide aynıdır). Referans nokta 50K'dan 10K TPS'e indirildi: gerçekçi işlem tanımıyla 50K ortalama, retail_bursty'nin 3,5× tepesinde (175K) tek z16'nın tavanına (~187K) dayanıyor ve stratejiler arası farkı bu tavan belirliyordu.

| Preset | A: Permanent | B: Base + CoD | C: TFP | Kazanan, A'ya göre |
|---|---|---|---|---|
| steady_oltp | $6,645M (3931-529) | $6,675M (528 → 529, 261 gün CoD) | **$6,435M** (613 + corridor 617) | C, −%3,2 |
| retail_bursty | $10,773M (3931-727) | **$9,534M** (619 → 727, 20 gün) | $9,555M (619 + corridor 625 → 727) | B, −%11,5 (C ile fark %0,2) |
| batch_heavy | $8,773M (3931-630) | $8,045M (616 → 630, 30 gün) | **$7,981M** (522 + corridor 528 → 630) | C, −%9,0 |

Yorum:

- **Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanıdır.** steady_oltp'de günlük tepe base'i neredeyse her gün aşar; B bunu 261 gün CoD ile karşılamak zorunda kalır ve A'dan pahalıya gelir, C ise bu tepeleri tüketim bazlı corridor'la ucuza emer. retail_bursty'de maliyeti 20 günlük büyük tepeler belirler; B ve C neredeyse eşittir ve kazanan corridor fiyat varsayımlarına göre değişir (Bölüm 9.8).
- **%100 kuralı bağlayıcıdır.** Geçici kapasite, satın alınan MSU'nun en fazla iki katına çıkabilir. Bu yüzden tepe kademesi base'in alt sınırını belirler (örn. retail_bursty'de 621'e geçici olarak çıkabilmek için base 609). Sınır uygulanmadığında model resmî kurala göre ulaşılamayan konfigürasyonlar seçiyordu.
- **Yazılım yıllık toplamın %72–84'üdür.** Donanım fiyatlama stratejisi (A/B/C) yalnızca kalan ~%15–25'i yeniden dağıtır. Bu yüzden stratejiler arası fark, doğrusal $40/MSU'lu önceki sürüme göre (%10–24) küçüldü (%3–12). Strateji seçimini asıl belirleyen, TFP-SW'nin yazılım faturasına getirdiği indirimdir (Bölüm 9.8). retail_bursty'de B ve C arasındaki fark %0,2'dir; varsayılanlarla B öne geçer.
- TFP'nin yazılım kalemi retail_bursty'de Permanent'ten %1 yüksek çıkar. Gelir-nötr kalibrasyon referans kademenin MSU/PCI oranını kullanır; TFP'de base ve corridor kademelerinin oranı biraz farklıdır. Bu bir model artefaktıdır ve sıralamayı yalnızca B/C neredeyse eşit olduğu bu durumda etkiler.

### 9.8. Duyarlılık Analizi (Fiyatlama Varsayımları)

`python src/tools/pricing_sensitivity.py` kalibre edilmemiş fiyat parametrelerini tek tek tarar (10K ortalama TPS, oltp_rw, M1, 20 TB; storage dahil). Yıllık toplamlar, milyon USD; kazanan kalın:

| Parametre (varsayılan) | Değer | steady_oltp A / B / C | retail_bursty A / B / C | batch_heavy A / B / C |
|---|---|---|---|---|
| CORRIDOR_PREMIUM (1,5) | 1,0 | 6,645 / 6,675 / **6,429** | 10,773 / **9,534** / 9,551 | 8,773 / 8,045 / **7,973** |
| | 4,0 | 6,645 / 6,675 / **6,463** | 10,773 / **9,534** / 9,574 | 8,773 / 8,045 / **8,018** |
| CORRIDOR_FRACTION (0,20) | 0,10 | 6,645 / 6,675 / **6,499** | 10,773 / **9,534** / 9,630 | 8,773 / **8,045** / 8,062 |
| | 0,35 | 6,645 / 6,675 / **6,362** | 10,773 / 9,534 / **9,493** | 8,773 / 8,045 / **7,955** |
| | 0,50 | 6,645 / 6,675 / **6,355** | 10,773 / 9,534 / **9,462** | 8,773 / 8,045 / **7,892** |
| CORRIDOR_SUBSCRIPTION_RATE (0) | 0,25 | 6,645 / 6,675 / **6,494** | 10,773 / **9,534** / 9,642 | 8,773 / 8,045 / **8,036** |
| | 0,50 | 6,645 / 6,675 / **6,550** | 10,773 / **9,534** / 9,730 | 8,773 / **8,045** / 8,092 |
| COD_DAILY_MULTIPLIER (2,5) | 1,5 | 6,645 / 6,649 / **6,435** | 10,773 / **9,475** / 9,515 | 8,773 / 7,994 / **7,931** |
| | 4,0 | 6,645 / 6,716 / **6,435** | 10,773 / 9,623 / **9,614** | 8,773 / 8,120 / **8,054** |
| TFP_SW_DISCOUNT (0) | 0,05 | 6,645 / 6,675 / **6,173** | 10,773 / 9,534 / **9,161** | 8,773 / 8,045 / **7,646** |
| | 0,10 | 6,645 / 6,675 / **5,911** | 10,773 / 9,534 / **8,768** | 8,773 / 8,045 / **7,312** |

Sonuç: steady_oltp'de TFP'nin üstünlüğü tüm taranan aralıkta korunur. batch_heavy'de dar corridor (0,10) ya da yüksek corridor aboneliği (0,50) B'yi öne geçirir. retail_bursty'de varsayılanlarla B kazanır, ama fark %1'in altındadır; geniş corridor veya pahalı CoD C'yi öne geçirir. Donanım parametreleri (corridor, CoD) toplamları yalnızca %1–2 oynatırken, **TFP_SW_DISCOUNT'un %5'i** C'yi her presette açık ara öne geçirir. Yani yazılım gerçekçi fiyatlandığında strateji kararını donanım değil, IBM ile pazarlıkla belirlenen TFP-SW yazılım fiyatı verir. Gerçek sözleşme fiyatı olmadan "bursty iş yükü için TFP mi CoD mu" sorusuna kesin cevap verilemez ve tezde böyle raporlanmalıdır. Permanent strateji, taranan hiçbir noktada kazanmaz.

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
  src/tools/software_sensitivity.py    yazılım yığını (AWLC + zIIP) duyarlılık analizi
  src/tools/workload_sensitivity.py    iş yükü profili (işlem bileşimi) duyarlılık analizi
  data/raw/redp5320_workload_profile.csv  REDP-5320 benchmark işlem profili (kaynaklı)
  data/ds8900f_models.csv              DS8900F model kataloğu (kaynaklar dosya başlığında)
```

### 10.1. Statik Mod

python src/mainframe_model.py --tps 10000 --availability 0.999 --workload oltp_rw --latency-ms 200 --data-tb 20 --data-growth 0.15

Özel işlem bileşimi: `--sql-reads 6 --sql-writes 2` (w ve I/O bileşimden hesaplanır).

### 10.2. Yıllık Mod

python src/mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000 --availability 0.999 --csv out

### 10.3. Yardımcı Modlar

- --demo: hazır 6 senaryo
- --calibration: kademe tablosu özeti, köprü katsayıları ve örnek kademeler

### 10.4. Testler

python src/test_mainframe_model.py — 12 test: latency monotonluğu, latency'nin sıkı hedefte bağlayıcı olması, kademe tablosunun bütünlüğü (317 satır, seri başına kesin artan PCI ve MSU), köprünün kendi z13 çapalarını %2 içinde ve 7K0 PCI'sini %0,5 içinde üretmesi, MSU faturasının kurulu kapasiteyle sınırlı olması, geçici kapasitenin (B veya C) avantajının burstiness ile artması, geçici hedeflerin SC28-7025 kurallarına uyması (%100, drawer, alt-kapasite; 735 → 739 ve 705 örnekleri), seçilen B/C konfigürasyonlarının bu kurallara uyması, TFP-SW fiyatının gelir-nötr olması ve corridor ücretinin CORRIDOR_PREMIUM ile artması, storage boyutlandırmasının (topolojiden kopya sayısı, IOPS'tan model, veri hacminden kapasite) ve zHyperLink / senkron replikasyonun D_io'ya etkisinin beklenen yönde olması. Ayrıca AWLC yazılım fonksiyonunun IBM örnek faturasını (265 MSU) ve Db2 referans eğrisini yeniden üretmesi, toplamın artan ama MSU başına fiyatın azalan olması, maliyet/TPS'in 5K → 500K TPS arasında en az 3 kat düşmesi, zIIP payı arttıkça faturalanan MSU'nun düşmesi ve zIIP sayısının 2:1 sınırına uyması test edilir. Ayrıca iş yükü profilleri test edilir: REDP profili köprüyü aynen korur (w = 1, zIIP yok); daha ağır bileşim daha yüksek w, I/O ve maliyet verir; özel bileşim beklenen yönde davranır. Latency testi üç profilde koşar; infeasible eşiği storage'tan gelen D_io'ya göre hesaplanır. Yıllık testler 10K ortalama TPS'te koşar.

## 11. Referanslar ve Kullanım Amaçları

### 11.1. Kapasite Tablosu ve Throughput Köprüsü

- **[LSPR]** IBM Z LSPR ITRRs (çok imajlı tablo, System z9 2094-701 = 1,00). 3931 4xx/5xx/6xx 1–39 CP ve 701–703 için PCI, MSU, Low/Average/High. https://www.ibm.com/support/pages/ibm-z-lspr-itrrs
- **[LSPR-z13]** IBM Z LSPR ITR zOSv2r2. Köprü çapaları: 2964-718 = 21.579 PCI (38,55), 2964-726 = 29.048 PCI (51,89). https://www.ibm.com/support/pages/node/6953815
- **[EXHIBIT]** IBM Mainframe Exhibit, Full Capacity MSUs, IBM z16 (3931), güncelleme 5/2/2025. 3931-701…7K0 resmî MSU değerleri ve A0–K0 kodlaması. https://www.ibm.com/downloads/documents/us-en/10a99803f42fd829
- **[STINE]** K. Stine, "IBM z16 Technical Overview", IBM Z Council, 2022. z16 200-way = 215.089 PCI (z15 190-way'e göre +%17); türetilen PCI değerlerinin bağımsız doğrulaması. https://ibm-zcouncil.com/wp-content/uploads/2022/05/z16-Technical-Overview-50M-KennyStine.pdf
- **[SG24-8950]** IBM Redbooks, "IBM z16 Technical Introduction" (2. baskı, 2023). A01'de 317 kapasite seviyesi (200 tam-hız + 117 alt-kapasite) ve Max39–Max200 özellikleri. https://redbooks.ibm.com/redbooks/pdfs/sg248950.pdf
- **[SG24-8952]** IBM Redbooks, "IBM z16 A02 and IBM z16 AGZ Technical Guide" (2023). Kapsam dışı bırakılan rack-mount modellerin tanımı. https://www.redbooks.ibm.com/redbooks/pdfs/sg248952.pdf
- **[REDP]** IBM Redpaper REDP-5320, "IBM CICS Performance Series: CICS TS V5.3 Benchmark on IBM z13" (Burgess, Mitchell, Moxey). 18 CP → 174.000 TPS, 26 CP → 227.000 TPS. https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf
- **[REDP-PROFILE]** Aynı raporun sayaç tabloları (18 ve 26 CP): shared data table okumaları, read for update/rewrite, CF log yazımları, bölge bazında CICS CPU. İşlem başına değerler (4,76 okuma, 0,047 güncelleme, 0,062 log yazımı, 85,9 µs CPU) bu çalışmada türetildi: `data/raw/redp5320_workload_profile.csv`.
- **[CATTERALL-2019]** R. Catterall (IBM), "A Case Study: Measuring the Impact of Db2 for z/OS Buffer Pool Changes", Robert's Db2 blog, Ocak 2019. Bir sahada CICS-Db2 işlemi class 2 CPU (GP + zIIP) 1,322 → 1,245 ms; DRDA işlemi 0,392 → 0,259 ms. Donanım belirtilmemiş. https://robertsdb2blog.blogspot.com/2019/01/a-case-study-measuring-impact-of-db2.html
- **[CATTERALL-2012]** R. Catterall, "DB2 for z/OS: What's With DDF CPU Time?", 2012, okur yorumu: CICS programında tek INSERT ~68 µs CPU (stored procedure içinde 139 µs); DDF SRB süresinin %47'si zIIP'te (bazı sahalarda %60). https://robertsdb2blog.blogspot.com/2012/07/db2-for-zos-whats-with-ddf-cpu-time.html
- **[SYSBENCH]** sysbench oltp_read_write betiği: işlem başına 10 point SELECT, 4 aralık SELECT, 2 UPDATE, 1 DELETE, 1 INSERT, 1 COMMIT. Varsayılan oltp_rw profilinin bileşimi; x86 tarafında yaygın ölçülen OLTP bileşimi.
- **[TPC-B]** TPC Benchmark B (debit-credit) işlem bileşimi: 3 UPDATE, 1 SELECT, 1 INSERT. tpcb_like profilinin bileşimi.
- **[IBM-Z14-PR]** IBM IBM Z (z14) duyurusu, Temmuz 2017: "günde 12 milyardan fazla şifreli işlem" (Amwal Al Ghad haberi, https://en.amwalalghad.com/?p=62475). Profil ağırlığı için büyüklük mertebesi kontrolü; işlem tanımı açıklanmamıştır.

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
- **[IBM-2004] —** IBM, "Workload License Charges" sunumu, z/VM sayfası (vm.ibm.com, 2005-Z24, 2004 fiyatları). Db2 PSLC/WLC kademe fiyatları (Base $3.960 ilk 3 MSU dahil; 4–45 $208; 46–175 $88; 176–315 $66; 316+ $50 /MSU/ay) ve örnek sub-capacity faturası (z/OS $75.459 @265 MSU, CICS $32.978 @210 MSU, Db2 $31.876 @265 MSU). AWLC kademe düşüş eğrisinin ve ürün katsayılarının kaynağı. 2004 tarihli olduğu için mutlak seviye SW_PRICE_LEVEL_FACTOR ile taranır.
- **[IBM-ZNALC] —** IBM, "z Systems New Application License Charges (zNALC)", ZSL03508-USEN-01. Kademe sınırları (Base 3, L0 4–45 … L7 1.976+) ve "kümülatif aylık fiyatlama" ilkesi (aynı yapı AWLC'de geçerli).
- **[CMG-2020] —** CMG, "Understanding Z Pricing to Control your Software Costs" (2020). AWLC kademe sınırlarının güncel teyidi; R4HA'nın LPAR bazlı tepeye göre faturalanması.
- **[LONGPELA] —** Longpela Expertise, MLC fiyatlama yazıları. "L7'nin MSU fiyatı L6'dan ~%20 düşük" gözlemi; L4+ için ×0,80 düşüş varsayımının dayanağı.
- **[VALUE4IT] —** value-4it, "Mainframe Software Costs" yazı dizisi. ~150 MSU ≈ yıllık £1M yazılım; büyüklük mertebesi teyidi.
- **[TU11] —** IBM Technology Update Pricing (z17 için TU11): AWLC indirimleri kademe bandına göre %12–42. Mutlak seviyenin aşağı yönlü gerekçesi.
- **[ZIIP] —** IBM z16 zIIP kuralları (SG24-8950): zIIP MSU'ya sayılmaz, alt-kapasite modellerde tam hızda çalışır, zIIP:CP ≤ 2:1. Tipik offload aralığı (%10–25, Redress Compliance) doğrulanmamıştır, yalnızca aralık olarak kullanılır.
- **\[LIC\] (kullanımdan kaldırıldı) —** Önceki sürümdeki $40/MSU/ay değerinin kaynağı (atonementlicensing.com). Metodolojisi açıklanmadığı ve IBM'in kendi örnek faturasıyla ~7–10 kat çeliştiği için bırakıldı.
- **\[PWR\] —** Aynı fiyat rehberi (electronics.alibaba) enerji ölçütleri. z15/z16 frame başına 20-40 kW; modelde POWER_KW_PER_SYSTEM = 30 kW (orta).

### 11.6. Teorik Temel

- **[QUEUE]** Kuyruk teorisi (per-CP M/M/1). Mainframe WLM/RMF response-time percentile metodolojisiyle uyumlu (SMF 72.3 / 110.1).

## 12. Modelin Bilinen Eksikleri ve Sonraki Adımlar

### 12.1. Kalibre Edilmemiş Parametreler [ASSUME]

- İş yükü profili: CPU_US_PER_SQL_READ = 30 µs, CPU_US_PER_SQL_WRITE = 70 µs (tek saha), GETPAGES_PER_SQL_READ = 4, BP_HIT_RATIO = 0,95, LOG_SYNC_IO_PER_COMMIT = 1, ASYNC_WRITE_IO_PER_SQL_WRITE = 0,5; oltp_heavy bileşimi (Bölüm 4.4)
- HARDWARE_COST_PER_MIPS = $200/PCI (doğrusal kestirim)
- Yazılım: SW_PRICE_LEVEL_FACTOR = 1,0 (2004 nominal), L4+ kademe düşüşü ×0,80, ürün katsayılarının 2004 oranlarını koruduğu varsayımı (Bölüm 7.1.6)
- zIIP: ZIIP_OFFLOAD_FRACTION = 0,10, ZIIP_HW_PRICE_FACTOR = 0,25
- GDPS yazılım primi (M3 ×1,15, M4 ×1,30)
- COD_DAILY_MULTIPLIER = 2,5 ve base kademe için "≥ ortalama yükün %120'si" eşiği
- TFP: CORRIDOR_PREMIUM = 1,5, CORRIDOR_FRACTION = 0,20 (IBM örneğinden), CORRIDOR_SUBSCRIPTION_RATE = 0, TFP_SW_DISCOUNT = 0 (Bölüm 9.8'de taranır)
- Storage: STORAGE_DISCOUNT = 0,70, lisans oranları 0,15 + 0,10, DB_OVERHEAD_FACTOR = 1,5, RAID_USABLE_FRACTION = 0,75, SAFEGUARDED_RESERVE = 0,25, planlama ufku 3 yıl; I/O yolu: okuma payı 0,70, önbellek isabeti 0,90, zHyperLink payı 0,80, t_miss = 300 µs, Metro Mirror mesafesi 20 km (Bölüm 8)
- ELECTRICITY_USD_PER_KWH = $0,12, POWER_KW_PER_SYSTEM = 30 kW

### 12.2. Yapısal Basitleştirmeler

- Enerji, büyük kademelerde drawer/rack sayısıyla ölçeklenmiyor (Bölüm 7.4 notu).
- Kurulu drawer özelliği base'i taşıyan en küçük özellik olarak sabit; drawer maliyeti yok, bu yüzden özellik seçimi karar değişkeni değil (Bölüm 9.5).
- Corridor genişliği base MSU'nun sabit bir oranı; IBM'de bu, iş yükü analiziyle müşteriye özel belirlenir.
- On/Off CoD kaydının 180 günlük süresi ve tek-aktif-kayıt kuralı modellenmiyor (simülasyonlarda en fazla 261 gün CoD görülüyor; bu, kayıt yenilemesi gerektirir).
- R4HA LPAR değil CPC toplamı üzerinden hesaplanıyor.
- Peak günler yıla eşit aralıklarla dağıtılıyor (gerçekte mevsimsel kümelenir); tek yıllık ufuk.
- Yedek frame tam kapasite ve tam maliyetle sayılıyor (CBU modellenmiyor). İkinci frame kapasite eklemiyor; tek CEC tavanı (oltp_rw ~187K TPS) aşılamıyor (Bölüm 4.4.4).
- İş yükü profilinde lock/latch çekişmesi, Db2 data sharing'in (coupling facility) ek CPU maliyeti ve zIIP'teki işin latency'si yok.
- M4'ün availability kaynak etiketleri ters görünüyor; M3 ve M4'ün effective low değerleri aynı. RPO/RTO girdileri bağlı değil.

### 12.3. Yol Haritası (Değerlendirme #2, M3–M8)

- Parallel Sysplex data sharing ile tek CEC'in ötesine ölçekleme (oltp_rw'de ~187K TPS üstü şu an infeasible); SQL CPU maliyetleri için ikinci bir mutlak çapa (IRWW veya gerçek SMF 101 örneği)
- Maliyet yapısı: donanımda taban + drawer + kapasite başına artış (drawer özelliğini karar değişkeni yapar); gerçek bir AWLC fiyat tablosuyla L4+ kademelerin ve mutlak seviyenin kalibrasyonu; TFP-HW zIIP corridor'u
- Availability: RPO/RTO bağlantısı, M4 düzeltmesi, DR frame için CBU
- Storage: gerçek bir DS8900F teklifiyle indirim/lisans kalibrasyonu; TS7700 yedekleme; DS8000 G10
- Personel ve GDPS ayrı kalem
- 5 yıllık ufuk + NPV, kümelenmiş peak dağılımı; TFP-SW büyüme fiyatı ve MSU taahhüdü
- (Opsiyonel) z16 A02 rack-mount modelleri
