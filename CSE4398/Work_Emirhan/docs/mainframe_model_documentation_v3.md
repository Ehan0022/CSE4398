# Mainframe (Scale-Up) Modelinin Detaylı Dokümantasyonu — v3

*IBM z16 A01 (3931) · compute kapasitesi, latency, availability, iş yükü profili, yazılım yığını (AWLC: z/OS, CICS TS, Db2) ve zIIP, altyapı personeli, aralık çıktısı, storage (DS8900F), yıllık simülasyon, Capacity-on-Demand ve Tailored Fit Pricing*

Bu doküman mainframe modelinin **güncel halini** anlatır: hangi veri hangi kaynaktan alındı, nasıl işlendi, modele nasıl girdi. İlk kez okuyorsanız Bölüm 0'dan (okuma kılavuzu, baştan sona örnek ve sözlük) başlayın. Değişikliklerin tarihçesi ve gerekçeleri `PROJECT_LOG.md` dosyasındadır. Önceki sürüm (`mainframe_model_documentation_v2.md`) tarihsel kayıt olarak değiştirilmeden tutulur.

Etiketler: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** resmî veriden hesaplanmış, doğrulaması belirtilmiş değer · **(doğrulanmalı)** kaynakla henüz teyit edilmemiş bilgi.

## 0. Okuma Kılavuzu

Bu bölüm dokümanı ilk kez okuyan biri için yazıldı. Önce modelin bir sorguyu baştan sona nasıl işlediğini (0.1), sonra gerçek sayılarla tek bir örneği (0.2), en sonda da dokümanda geçen mainframe terimlerini (0.3) verir. Ayrıntılar ilgili bölümlerdedir.

### 0.1. Model bir sorguyu nasıl işler

Model iki modda çalışır. **Statik mod** tek bir yük noktası için "hangi makine, ayda ne kadar" sorusunu cevaplar. **Yıllık mod** aynı soruyu 8.760 saatlik bir trafik profili üzerinde, üç farklı donanım edinim stratejisiyle sorar (Bölüm 9). İki mod da `--npv` ile 5 yıllık bir ufka taşınabilir: yük her yıl büyür, kademe gerektikçe yükseltilir ve nakit akışları bugüne indirgenir (Bölüm 9.10). Statik moddaki akış:

1. **İş yükünü tanımla (Bölüm 4.4).** Kullanıcı TPS'i ve işlemin bileşimini (okuma ve yazma SQL sayısı) verir. Bileşimden işlemin CPU ağırlığı *w*, işlem başına senkron I/O ve IOPS hesaplanır. *w*, bir işlemin kapasite köprüsündeki benchmark işleminden kaç kat ağır olduğunu söyler.
2. **Kademelerin kapasitesini hesapla (Bölüm 3–4).** z16 A01'in 317 kademesinin her birinin göreli kapasitesi (PCI) IBM tablolarından gelir. Kapasite köprüsü PCI'yi saniyedeki benchmark işlemine çevirir (PCI başına 7,94); *w* ile bölününce o iş yükü için kademenin TPS kapasitesi çıkar.
3. **Availability ve felaket kurtarma hedeflerine göre topolojileri ele (Bölüm 6).** Her topolojinin yıllık beklenen kesintisi olay tabanlı hesaplanır: saha olaylarının sıklığı × topolojinin kurtarma süresi + planlı kesinti. Availability'si hedefi, RPO ve RTO'su kullanıcının girdisini karşılayan topolojiler aday kalır. Topoloji DR frame'ini (CBU), GDPS kalemini, storage kopya sayısını ve personel çarpanını belirler.
4. **Latency'ye göre kademeleri ele (Bölüm 5).** Her kademe için hedef percentile latency'yi karşılayan en yüksek kullanım oranı hesaplanır (en fazla %90). Kademe, yükü bu oranın altında taşıyabiliyorsa feasible'dır. Latency CPU kuyruğundan ve storage'tan gelen sabit I/O gecikmesinden oluşur.
5. **Storage'ı ve yedeği boyutlandır (Bölüm 8).** Veri hacmi ve IOPS ihtiyacından DS8900F dizi modeli ve sayısı seçilir; I/O gecikmesi adım 4'e geri beslenir. Db2 image copy'leri ve arşiv loglarının 4 haftalık hacmi için üç yedek hedefi (TS7770 sanal teyp, on-prem nesne depolama, AWS S3) boyutlandırılır. Yedek penceresini, M1'de geri yükleme süresini ve DS8900F'in bulut aktarım verimini karşılayan hedeflerden en ucuzu seçilir (Bölüm 8.10).
6. **Maliyeti hesapla ve en ucuzu seç (Bölüm 7).** Her feasible (topoloji, kademe) çifti için sekiz kalem toplanır: yazılım (yükün tükettiği MSU üzerinden AWLC), donanım amortismanı, bakım, enerji, GDPS, personel, storage ve yedekleme. En düşük aylık toplam seçilir.
7. **Aralığı ver (Bölüm 7.8).** Kesin değeri olmayan 20 parametre (fiyatlar, işlem maliyeti, personel, availability ve yedek varsayımları) düşük, orta ve yüksek değerlere çekilir; adım 1–6 her biri için yeniden çözülür. Sonuç tek bir sayı değil, low / mid / high aralığı ve her parametrenin bu aralığa katkısıdır.

### 0.2. Baştan sona bir örnek

Sorgu: 10.000 TPS, varsayılan `oltp_rw` profili, availability ≥ %99,9, p99 latency < 200 ms, 20 TB veri.

```
python src/mainframe_model.py --tps 10000 --availability 0.999 --latency-ms 200 --data-tb 20 --range
```

| Adım | Ne hesaplanır | Sonuç |
|---|---|---|
| 1. İş yükü | CPU = 85,9 + 30 × 14 okuma + 70 × 4 yazma = 785,9 µs; w = 785,9 / 85,9 | w = 9,15; 3,8 senkron I/O ve 5,8 IOPS / işlem |
| 2. Kapasite | 7,939 / 9,15 / (1 − 0,10 zIIP payı) | PCI başına 0,96 işlem/s |
| 3. Availability | M1'in yıllık kesintisi 3,3 saat → %99,962 ≥ %99,9; RPO/RTO girdisi yok | Dört topoloji de aday; en ucuz olan M1 (tek frame) |
| 4. Latency | 3931-516 (16 CP, 11.743 PCI) ham 11.323 TPS, %90 tavanla 10.190 TPS taşır | Kullanım %88,3; tahmini p99 56 ms |
| 5. Storage ve yedek | 20 TB × büyüme × ek yük → 76 TB ham; 10K × 5,8 = 58K IOPS. Yedek: 4 haftalık image copy + arşiv log, iki sitede | 1× DS8910F-993; D_io = 2,8 okuma × 61 µs + 1 log yazımı × 90 µs = 0,26 ms. Yedek: on-prem nesne depolama, 2 site × 173 TB (TS7770 $11.790, S3 $6.069, seçilen $5.635/ay) |
| 6. Maliyet | Faturalanan MSU = 10.000 / 11.323 ham TPS × 1.423 kademe MSU'su = 1.257 (sub-capacity); diğer kalemler | Aylık $846.187 = TPS başına $84,62 |
| 7. Aralık | 20 parametre low / mid / high | TPS başına $27,06 / $84,62 / $338,09 (high senaryoda M1 %99,9'u karşılayamaz, M2 seçilir) |
| 8. 5 yıllık NPV | Yük yılda %10 büyür; kademe yalnızca yükselir; alımlar nakit olarak, işletme giderleri fiyat artışlarıyla; %7 iskonto | NPV $50,60M; seviyelendirilmiş maliyet TPS başına $85,31/ay (Bölüm 9.10) |

Adım 6'nın dökümü (aylık): yazılım $339.968 (z/OS + CICS TS + Db2), personel $416.430 (30,8 FTE), donanım amortismanı $49.354 ($500K frame tabanı + 11.743 PCI × $200 + 1 zIIP = $2,96M, 5 yıl), bakım $24.677 (ilk yıl garantili), yedekleme $5.635 (on-prem nesne depolama), storage $7.496, enerji $2.628. Personel ve yazılım birlikte toplamın %89'udur. Bu yüzden mainframe tarafının sonucunu en çok bu iki kalemin varsayımları belirler. Aralığa en çok katkı yapan parametreler sırasıyla personel eğrisi, okuma SQL'inin CPU maliyeti ve AWLC fiyat seviyesidir (Bölüm 7.8).

### 0.3. Sözlük

| Terim | Anlamı | Modeldeki yeri |
|---|---|---|
| CEC / CPC / frame | Tek bir fiziksel mainframe (Central Electronic Complex) | Topoloji frame sayısını belirler (Bölüm 6.7) |
| CP (GP) | Genel amaçlı işlemci; z/OS işi burada çalışır ve yazılım faturasına sayılır | Kademe = CP sayısı + hız seviyesi (Bölüm 3) |
| Kademe (capacity setting) | Model kodu 3931-*abc*: ilk hane hız seviyesi (4/5/6 alt-kapasite, 7 tam hız), son iki hane CP sayısı (99'un üstü harfle: 7A0 = 100, 7K0 = 200). Örnek: 3931-516 = 16 CP, 5 hız seviyesi | 317 kademe (Bölüm 3) |
| PCI | Processor Capacity Index; IBM'in göreli kapasite ölçüsü. Pratikte MIPS ile aynı anlamda kullanılır | Kapasite köprüsünün girdisi (Bölüm 4) |
| LSPR | Large Systems Performance Reference; IBM'in kademeler arası kapasite oranları | PCI değerlerinin kaynağı (Bölüm 3.2) |
| MSU | Million Service Units; IBM'in yazılım faturası için kullandığı kapasite birimi | Yazılım maliyeti MSU'ya bağlıdır (Bölüm 7.1) |
| MLC / AWLC | Monthly License Charge: z/OS, CICS, Db2 gibi ürünlerin aylık lisans ücreti. AWLC, z16'da kullanılan, MSU arttıkça birim fiyatı kademe kademe düşen MLC türü | Bölüm 7.1 |
| R4HA | Rolling 4-Hour Average; ayın en yüksek 4 saatlik ortalama MSU tüketimi. Sub-capacity fiyatlamada fatura buna göre kesilir | Yıllık mod (Bölüm 9.3) |
| zIIP | Bazı Db2/Java işlerini CP'den alan, yazılım faturasına sayılmayan ve daha ucuz specialty işlemci | f parametresi (Bölüm 7.1.5) |
| ICF / CF | Internal Coupling Facility: sysplex üyelerinin ortak kilit ve önbellek yapısını tutan specialty işlemci | M1–M2 topolojileri (Bölüm 6.2) |
| Sysplex / Parallel Sysplex | Birden çok z/OS sisteminin tek sistem gibi çalıştığı küme yapısı | Topolojiler; çok-frame ölçekleme modellenmedi (Bölüm 12.2) |
| GDPS | IBM'in sysplex ve disk replikasyonunu otomatik yöneten felaket kurtarma çözümü | M3–M4'te sabit aylık kalem ve kurtarma süresi (Bölüm 6) |
| CoD / On/Off CoD | Capacity on Demand: kurulu ama kapalı kapasiteyi günlük ücretle geçici açma | Strateji B (Bölüm 9.6) |
| CBU | Capacity BackUp: DR frame'inde yalnızca felakette ya da testte açılan yedek kapasite; DR makinesinin yazılımı kalıcı kapasitesine göre faturalanır | DR frame bedeli (Bölüm 6.7) |
| RPO / RTO | Recovery Point / Time Objective: felakette kabul edilen en fazla veri kaybı ve hizmetin geri gelme süresi | Topoloji kısıtı (Bölüm 6.6) |
| TFP | Tailored Fit Pricing: donanımda tüketim bazlı corridor (TFP-HW), yazılımda tüketilen MSU-saat fiyatı (TFP-SW) | Strateji C (Bölüm 9.4, 9.6) |
| w | İşlemin CPU ağırlığı, benchmark işlemine göre (REDP = 1) | Bölüm 4.4 |
| f | zIIP'e kayan CPU payı | Bölüm 7.1.5 |
| D_io | İşlem başına toplam senkron I/O gecikmesi | Bölüm 5.3, 8.6 |
| FTE | Tam zamanlı eşdeğer çalışan sayısı | Personel (Bölüm 7.7) |
| low / mid / high | Aralık senaryoları; "low" her parametrenin mainframe lehine ucu | Bölüm 7.8 |

## 1. Modelin Amacı ve Kapsamı

### 1.1. Cevaplanan Soru

Verilen bir iş yükü (throughput, iş yükü profili yani işlemin okuma/yazma bileşimi, latency hedefi, availability hedefi, veri hacmi) için, bu iş yükünü karşılayan minimum maliyetli feasible IBM z16 A01 konfigürasyonu hangisidir ve aylık/yıllık maliyeti nedir?

### 1.2. Mevcut Kapsam

- z16 A01'in 317 kapasite kademesinin tamamı (Bölüm 3)
- Benchmark tabanlı kapasite köprüsü: PCI başına TPS (Bölüm 4)
- Bileşimli iş yükü profili: okuma/yazma SQL sayısından CPU ağırlığı ve I/O (Bölüm 4.4)
- Per-CP M/M/1 kuyruğu + sabit I/O gecikmesiyle latency feasibility (Bölüm 5)
- Olay tabanlı availability: dört topoloji (M1–M4), saha olayı × kurtarma süresi + planlı kesinti; RPO/RTO kısıtı; CBU'lu DR frame'i ve GDPS kalemi (Bölüm 6)
- Kademe başına resmî MSU ile sub-capacity yazılım faturası: z/OS + CICS TS + Db2, AWLC kademeli kümülatif fiyat (Bölüm 7.1)
- zIIP: MSU dışı kapasite payı ve zIIP motor donanımı (Bölüm 7.1.5)
- Donanım amortismanı, bakım, enerji (Bölüm 7)
- Altyapı personeli: kapasiteyle alt-doğrusal FTE eğrisi, düşük/orta/yüksek senaryo (Bölüm 7.7)
- Aralık çıktısı: kaynaklı parametre aralıklarıyla low/mid/high toplam ve tek-parametre salınımı (Bölüm 7.8)
- Storage katmanı: IBM DS8900F boyutlandırması (veri hacmi, IOPS, topolojiye bağlı kopya sayısı), maliyeti ve I/O gecikmesi; zHyperLink, zHPF/FICON, Metro/Global Mirror, Safeguarded Copy (Bölüm 8)
- Yedekleme: Db2 image copy ve arşiv loglarının 4 haftalık saklanması için üç hedef (IBM TS7770 sanal teyp, S3 uyumlu on-prem nesne depolama, AWS S3); yedek penceresi, M1 geri yükleme süresi ve TCT verimi kısıtları; kısıtları karşılayan en ucuzun seçimi (Bölüm 8.10)
- Yıllık simülasyon: 8.760 saatlik profil ve üç donanım edinim/fiyatlama stratejisi: Permanent, Base + On/Off CoD ve Tailored Fit Pricing (base + capacity corridor + CoD); On/Off CoD'nin resmî sınırları (Bölüm 9)
- 5 yıllık ufuk ve NPV: yük büyümesi, yalnızca yükselen kademe yolu, storage ve yedek alım döngüleri, fiyat artışları, TFP büyüme fiyatı; NPV, yıllık eşdeğer maliyet ve seviyelendirilmiş $/TPS/ay (Bölüm 9.10)

### 1.3. Kapsam Dışı

- **z16 A02 / AGZ (makine tipi 3932, rack-mount modeller).** A01'den ayrı bir donanım ailesi; 156 kapasite seviyesi ve Max5/16/32/68 özellikleri var (SG24-8952). Model şu an yalnızca A01'i kapsıyor. Düşük TPS bölgesinde mainframe'in taban maliyetini belirleyebilecekleri için tezde ayrıca belirtilmeli; ileride eklenebilir.
- **3931-400:** Yalnızca Coupling Facility (CF) için kullanılan, MSU derecesi olmayan kapasite ayarı.
- **Messaging (IBM MQ):** proje kararıyla iki tarafta da kapsam dışı.

### 1.4. Henüz Modele Eklenmemiş Bileşenler

Tek CEC'in ötesine Parallel Sysplex ölçeklemesi, stokastik (dağılımlı) kesinti modeli, 5 yıl içinde teknoloji yenilemesi (z17) ve drawer maliyeti. Bkz. Bölüm 12.

## 2. Modelin Girdi ve Çıktıları

### 2.1. Mevcut Girdiler

| **Parametre** | **Açıklama** | **Tipik aralık** |
|---|---|---|
| tps | Saniyedeki işlem sayısı | 500 – ~187.000 (oltp_rw'de tek z16 tavanı; redp_light'ta ~1,5M) |
| workload | İş yükü profili: işlemin bileşimi (Bölüm 4.4) | redp_light / tpcb_like / oltp_rw (varsayılan) / oltp_heavy |
| sql_reads + sql_writes | Özel bileşim: işlem başına okuma ve yazma SQL sayısı (`--sql-reads`, `--sql-writes`); verilirse hazır profilin yerine geçer | ör. 6 + 2 |
| latency_ms + percentile | Hedef latency | ör. p99 < 200 ms |
| availability | Hedef uptime (planlı kesinti dahil, hizmet düzeyinde) | 0,999 – 0,99999 |
| rpo_seconds | Saha felaketinde kabul edilen en fazla veri kaybı, saniye (`--rpo-seconds`) | 0 – 86.400 (varsayılan: kısıt yok) |
| rto_minutes | Saha felaketinde kabul edilen en fazla kurtarma süresi, dakika (`--rto-minutes`) | 1 – 4.320 (varsayılan: kısıt yok) |
| [yıllık] preset | Workload preset adı | steady_oltp / retail_bursty / batch_heavy |
| [yıllık] avg_tps + peak_ratio + peak_days | Custom workload tanımı | ör. 10K TPS, 3.5×, 20 gün |
| data_tb | Mantıksal Db2 veri hacmi (indeksler dahil), TB | 1 – 5.000 (varsayılan 20) |
| data_growth | Yıllık veri büyümesi | 0 – 0,5 (varsayılan 0,15) |
| range | Aralık çıktısı (`--range`): kaynaklı parametre aralıklarıyla low / mid / high (Bölüm 7.8) | açık / kapalı |
| backup_target | Yedek hedefi (`--backup-target`): auto (kısıtları karşılayan en ucuz), ts7770, cos_onprem, aws_s3 (Bölüm 8.10) | varsayılan auto |
| npv | 5 yıllık ufuk (`--npv`); statik ve yıllık modda, `--range` ile birlikte de çalışır (Bölüm 9.10) | açık / kapalı |
| tps_growth | [NPV] Yıllık TPS büyümesi (`--tps-growth`) | 0 – 0,3 (varsayılan 0,10) |
| discount_rate | [NPV] Nominal iskonto oranı (`--discount-rate`) | 0,05 – 0,10 (varsayılan 0,07) |
| years | [NPV] Ufuk, yıl (`--years`) | 1 – 10 (varsayılan 5) |

Projenin 8 girdisinin tamamı modele bağlıdır. IOPS kullanıcıya sorulmaz; TPS × iş yükü profilinin bileşiminden türetilir. Storage replikasyonu da sorulmaz; availability, RPO ve RTO'nun seçtirdiği topolojiden gelir.

### 2.2. Çıktılar

Statik mod (tek nokta sorgu):
- Seçilen z16 kademesi (örn. 10K TPS oltp_rw'de 3931-516) ve topoloji (M1/M2/M3/M4)
- Tam-hız CP eşdeğeri, utilization, dinamik utilization tavanı, tahmini percentile latency
- Topolojinin yıllık beklenen kesintisi, availability'si (mid ve aralık), RPO ve RTO'su
- Aylık maliyet dökümü: yazılım (z/OS + CICS TS + Db2) + donanım (zIIP ve DR frame dahil) + bakım + enerji + GDPS + personel + storage + yedekleme (seçilen hedef, saklanan hacim, tahmini geri yükleme süresi; `--backup-target` ile hedef zorlanabilir)
- `--range` ile: toplamın low / mid / high sınırları ve tek-parametre salınımı (Bölüm 7.8)

Yıllık mod (workload simülasyonu):
- Seçilen strateji (Permanent, Base + On/Off CoD veya Tailored Fit Pricing) ve diğer iki stratejinin en iyi sonuçları
- Base kademe, drawer özelliği, corridor tavanı, CoD tepe kademesi ve CoD gün sayısı
- Yıllık maliyet dökümü: yazılım (R4HA veya consumption), donanım + bakım + enerji, corridor kullanımı, On/Off CoD, personel (tepe kademeye göre, stratejiden bağımsız), storage ve yedekleme
- Utilization istatistikleri
- CSV: 8.760 satır saatlik + 12 satır aylık

5 yıllık mod (`--npv`):
- Yıl yıl yük, kademe yolu, capex ve opex; kalem bazında bugünkü değer dökümü
- NPV, indirgenmemiş toplam, yıllık eşdeğer maliyet (EAC) ve seviyelendirilmiş $/TPS/ay
- Yıllık modda üç stratejinin 5 yıllık NPV'si ve kazanan; `--range` ile NPV'nin low / mid / high aralığı ve tornado

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

- **Etki büyük:** varsayılan profil (w = 9,15) aynı TPS için ~9 kat daha fazla mainframe kapasitesi gerektirir. Örneğin 10K TPS'te seçilen kademenin MSU'su 185'ten (REDP işlemi) 1.423'e çıkar (Bölüm 7.6). Önceki sürümdeki "50K TPS" sonuçları, bugünkü birimle yaklaşık 5,5K oltp_rw TPS'e karşılık gelir.
- **Tek sistem tavanı:** oltp_rw'de en büyük tek z16 ~187K TPS taşır; oltp_heavy'de ~104K. Gerçek kurulumlar bunun üstüne Parallel Sysplex data sharing ile birden fazla CEC'e ölçeklenir. Model bunu henüz içermez: M2–M4'teki ikinci frame yedek olarak sayılır, kapasite eklemez. Yüksek hacimli crossover analizi için bu bir sınırlamadır (Bölüm 12).
- **En kritik varsayım:** CPU_US_PER_SQL_READ. 15–60 µs aralığı w'yi 6,7–14,0 aralığında, 10K TPS'te maliyeti $69,2–110,2/TPS aralığında oynatır (Bölüm 7.1.6 ve `src/tools/workload_sensitivity.py`). BP_HIT_RATIO yalnızca I/O'yu ve D_io'yu etkiler (M1'de 0,90 → 0,43 ms; 0,99 → 0,12 ms), maliyeti etkilemez.
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

Sabit I/O gecikmesi: D_io = senkron okuma I/O × t_okuma + senkron yazma I/O × t_yazma. I/O sayıları iş yükü profilinin bileşiminden gelir (Bölüm 4.4: okumada Db2 buffer pool kaçağı, yazmada commit log yazımı). Servis süreleri storage katmanından gelir (Bölüm 8.6): t_okuma DS8900F önbellek isabeti, zHyperLink ve zHPF/FICON'dan; t_yazma zHPF/FICON'dan ve senkron replikasyonun mesafe gecikmesinden. Varsayılanlarla t_okuma 61 µs, t_yazma M1'de 90 µs, senkron kopyalı topolojilerde (M2–M4) 290 µs. oltp_rw profilinde (2,8 senkron okuma + 1 log yazımı) D_io M1'de 0,26 ms, M2–M4'te 0,46 ms.

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
| yok | 3931-516 | $846.187 |
| 50 ms | 3931-706 | $852.699 |
| 10 ms | 3931-708 | $952.757 |
| 5 ms | 3931-714 | $1.198.120 |
| 4 ms | infeasible | |

Latency'siz durumda model yavaş alt-kapasite CP'li 5xx kademesini seçer. Hedef sıkılaştıkça tam-hız CP'li 7xx kademelerine kayar. oltp_rw'de boş sistemdeki alt sınır ~2,4 ms'dir: en hızlı tek CP'de işlem başına CPU süresi ~0,46 ms, p99 çarpanı ln(100) ≈ 4,6 ve D_io 0,26 ms. 10K TPS yük altında kuyruk payı eklendiği için en düşük feasible p99 hedefi ~4,2 ms'dir (5 ms feasible, 4 ms değil). Bu, işlem bileşiminin latency'yi de doğrudan belirlediğini gösterir.

Latency hedefi sıkılaştıkça kurulan kapasite büyür. Personel kurulu kapasiteye göre hesaplandığı için (Bölüm 7.7.5) 5 ms hedefindeki $352K'lık artışın yaklaşık $287K'sı personeldir.

## 6. Availability Modeli — Olay Tabanlı, Kurtarma Süresine Bağlı

### 6.1. Katmanın savunması

Availability, mainframe'de tek bir sayı değil, katmanlı bir mimari karardır: kaç CPC, kaç site, hangi replikasyon ve hangi otomasyon. Model bu kararı dört topoloji (M1–M4) üzerinden verir ve her topolojinin yıllık beklenen hizmet kesintisini hesaplar.

Önceki sürüm her topolojiye iki "nine" değeri atıyordu: ITIC anketinden bir alt sınır ve IBM Redbook SG24-8446'dan bir tasarım hedefi. Planlı kesinti için ×10 çarpanı uyguluyordu. Bu yaklaşım iki nedenle bırakıldı:

- **ITIC rakamları sunucunun kesintisini ölçer, hizmetin değil.** ITIC 2023'e göre z16 kullanıcılarının %96'sı 9 nine, yani sunucu başına yılda 31,56 ms plansız kesinti bildiriyor. Bu rakamın kapsamı sunucu donanımının kendi arızalarıdır [ITIC-2023]. Lenovo'nun güncel x86 sunucuları da aynı ankette 8 nine alıyor [ITIC-2024]. Hizmeti asıl kesen olaylar ise veri merkezi düzeyindedir: güç, ağ, insan hatası ve planlı bakım [UPTIME-2025]. Topolojiler de tam bu olaylara karşı kurulur.
- **SG24-8446 topolojilere "nine" değeri atamaz.** Güncel baskı dört deseni (Reliable base, Failover capable, Fault tolerant, Adaptive continuity) ve genel RTO/RPO aralıklarını tanımlar; desen başına availability yüzdesi vermez [SG24-8446]. Önceki sürümdeki "M1 ~6 nine … M4 ~10 nine" değerleri kaynakla desteklenmiyordu.

Yeni yöntem kesintiyi, **kesinti doğuran olayların sıklığı ile topolojinin bu olaylardan kurtarma süresinin çarpımı** olarak hesaplar. Bu yöntemin üç avantajı var. Kurtarma süreleri yayımlanmış GDPS değerlerinden gelir. Kullanıcının RTO girdisi doğrudan aynı parametreye bağlanır. Aynı denklem, kendi kurtarma süreleriyle clustered tarafa da uygulanabilir; bu, iki tarafın aynı ölçüyle karşılaştırılmasını sağlar.

### 6.2. Topolojiler

| Kod | SG24-8446 deseni | Yapı | GDPS | Frame (birincil + DR) | Storage kopyası | RPO (tek site kaybı) | Kurtarma süresi (mid, aralık) |
|---|---|---|---|---|---|---|---|
| M1 | Reliable base | Tek CPC üzerinde sysplex (ICF); tek site | yok | 1 | 1 | 24 saat (günlük yedek) [ASSUME] | Alternatif site yok: hizmet olay süresince durur |
| M2 | Failover capable | Birincil CPC + metro mesafede DR CPC (CBU), Metro Mirror; geçiş otomasyonsuz | yok | 1 + 1 | 2 | 0 (senkron) | 2 saat (1–4 saat) [SG24-6374, SG24-8446] |
| M3 | Fault tolerant | M2 + GDPS Metro Global otomasyonu ve HyperSwap; uzak bölgede Global Mirror kopyası | Metro Global | 1 + 1 | 4 | 0 (Metro Mirror); bölgesel felakette 2–5 sn [GDPS-2026] | 30 dk (2–60 dk) [GDPS-2026] |
| M4 | Adaptive continuity | İki coğrafi site, GDPS Continuous Availability, yazılım replikasyonu | CA | 1 + 1 | 4 | 0–5 sn, model 5 sn (yazılım replikasyonu) [GDPS-2026] | 30 sn (20–60 sn) [GDPS-2026] |

RPO, tek bir sitenin (veri merkezinin) kaybı için tanımlıdır; bu, saha olayı parametrelerinin de tanımıdır. Bölgesel felaket (metro mesafedeki iki sitenin birlikte kaybı) ayrı bir senaryodur: M2 buna karşı korumaz (RPO son yedek kadar), M3 Global Mirror bacağıyla 2–5 sn, M4 0–5 sn kaybeder. Model bölgesel felaketi ayrıca hesaplamaz (Bölüm 6.8).

Saf tek-imaj (sysplex'siz) kurulum production'da temsil edici olmadığı için dışarıda bırakıldı. Kurtarma süreleri IBM GDPS geliştirme ekibinin 2026 sunumundan alındı: GDPS Metro'da RTO çok-siteli iş yükünde ~2 dakika, tek siteli iş yükünde 1 saatin altında; GDPS CA'da 20–30 saniye (portföy slaytında 60 saniyenin altı) [GDPS-2026]. GDPS'siz kurtarma için SG24-8446 "2 saatin altı GDPS otomasyonu ve test edilmiş süreç ister" der; SG24-6374 depolama replikasyonlu uzak sitede RTO'yu "bir veya daha fazla saat" olarak verir.

### 6.3. Formül

```
D(topo) = λ_saha × [ (1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec) ]
        + λ_planlı × T_planlı(topo)
        + D_cpc                                    (yalnızca tek CPC'li M1)

A(topo) = 1 − D / 8.760 saat
```

- **Saha olayı (λ_saha, d_kısa, d_uzun, p_uzun):** veri merkezi düzeyinde hizmeti kesen olayın yıllık sıklığı ve süresi. Olaylar iki sınıfa ayrılır: çoğunluk kısa (saatler), küçük bir pay uzun (gün ve üstü).
- **Kurtarma süresi (T_rec):** hizmetin alternatif CPC'de ya da sitede geri gelme süresi. Olay kurtarma süresinden kısa sürerse kesinti olay süresi kadardır, uzun sürerse kurtarma süresi kadar (`min`). M1'de alternatif site olmadığı için T_rec sonsuzdur; kesinti olayın kendisi kadar sürer.
- **Planlı kesinti (λ_planlı, T_planlı):** CPC düzeyinde hizmet durdurmayı gerektiren planlı işlemler: power-on reset, donanım nesil geçişi, kapasite planı dışında kalan bir upgrade. z/OS, CICS ve Db2 bakımı sysplex içinde rolling IPL ile yapılır ve kesinti doğurmaz; bu yüzden M1 bile tek CPC üzerinde sysplex olarak tanımlıdır. M2 ve M3'te planlı işlem önce iş yükünü DR CPC'ye taşır, kesinti geçiş süresi kadardır. M4'te geçiş saniyeler sürer.
- **CPC donanım kesintisi (D_cpc):** ITIC'in ölçtüğü sunucu donanım kesintisi. Yalnızca tek CPC'li M1'de hizmeti keser; diğerlerinde ikinci CPC devralır. Yılda 0,03–3 saniye olduğu için toplamda ihmal edilebilir. Modelde, bu kalemin hizmet availability'sini belirlemediğini açıkça göstermek için tutulur.

Sistem içi yazılım arızaları (bir LPAR'ın, z/OS'un ya da bir Db2 üyesinin çökmesi) Parallel Sysplex ve Db2 data sharing ile diğer üyelere aktarılır ve modelde maskelenmiş sayılır. Bu bir basitleştirmedir (Bölüm 6.8).

### 6.4. Parametreler ve kaynakları

Her parametre low / mid / high aralığıdır. **low** mainframe lehine uçtur, yani daha az kesinti. Parametreler üç grup halinde aralık çıktısına girer (Bölüm 7.8).

| Grup | Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|---|
| Saha olayı | λ_saha (olay/yıl) | 0,05 | 0,15 | 0,25 | Operatörlerin %53'ü son 3 yılda kesinti bildirdi; bu, yılda ~0,25 olaya karşılık gelir (üst uç). Olayların %9'u ciddi veya ağır (alt uç) [UPTIME-2025] |
| | d_kısa (saat) | 1 | 2 | 4 | [ASSUME] |
| | p_uzun | 0,08 | 0,15 | 0,30 | Kamuya yansıyan kesintilerin 24 saatten uzun süren payı: 2017'de %8, 2021'de ~%30 [UPTIME-2022] |
| | d_uzun (saat) | 24 | 48 | 72 | Üst uç SG24-8446'nın GDPS'siz DR aralığının (2–72 saat) üst sınırı |
| | D_cpc (sn/yıl) | 0,03 | 0,32 | 3,15 | z16 9 nine / IBM ortalaması 8 nine / z13–z15 7 nine [ITIC-2023] |
| Kurtarma süresi | T_rec, M2 | 1 saat | 2 saat | 4 saat | [SG24-6374] "bir veya daha fazla saat"; [SG24-8446] GDPS'siz < 2 saat yok |
| | T_rec, M3 | 2 dk | 30 dk | 60 dk | [GDPS-2026] |
| | T_rec, M4 | 20 sn | 30 sn | 60 sn | [GDPS-2026] |
| Planlı kesinti | λ_planlı (olay/yıl) | 0,25 | 0,5 | 1 | [ASSUME] 4 yılda bir nesil geçişi ile yılda bir kesintili işlem arası |
| | T_planlı, M1 | 2 saat | 4 saat | 8 saat | [ASSUME] tek CPC durur |
| | T_planlı, M2 | 15 dk | 30 dk | 60 dk | [ASSUME] planlı, elle geçiş |
| | T_planlı, M3 | 2 dk | 10 dk | 30 dk | [ASSUME] GDPS ile planlı site geçişi |
| | T_planlı, M4 | 20 sn | 30 sn | 60 sn | Bir banka örneğinde planlı kesinti "4 saatten 30 saniyenin altına" indi [GDPS-CA-2021] |

Uptime verisi veri merkezi operatörleri genelindedir; mainframe'e özgü değildir. Mainframe veri merkezlerinin ortalamadan daha iyi işletildiği düşünülebilir. Bu yüzden düşük uç (yalnızca ciddi olaylar) ayrıca taranır.

### 6.5. Sonuçlar

`python src/tools/availability_sensitivity.py`:

| Topoloji | Saha olayı (saat/yıl) | Planlı (saat/yıl) | CPC donanımı (sn/yıl) | Toplam (saat/yıl) | Availability (mid) | Aralık (en kötü – en iyi) |
|---|---|---|---|---|---|---|
| M1 | 1,335 | 2,000 | 0,32 | 3,34 | %99,962 | %99,839 – %99,993 |
| M2 | 0,300 | 0,250 | — | 0,55 | %99,994 | %99,977 – %99,999 |
| M3 | 0,075 | 0,083 | — | 0,16 | %99,998 | %99,991 – %99,9999 |
| M4 | 0,001 | 0,004 | — | 0,005 | %99,99994 | %99,9998 – %99,99998 |

Tek grup salınımı (diğerleri mid):

| Grup | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| Saha olayı | %99,976 – %99,908 | %99,997 – %99,991 | %99,999 – %99,998 | %99,99995 – %99,99993 |
| Kurtarma süresi | etkisiz | %99,995 – %99,993 | %99,999 – %99,997 | %99,99994 – %99,99992 |
| Planlı kesinti | %99,979 – %99,893 | %99,996 – %99,985 | %99,999 – %99,993 | %99,99997 – %99,99980 |

Yorum:

- **Topolojiler arasındaki fark mertebe düzeyindedir.** Yıllık kesinti M1'den M2'ye ~6 kat, M2'den M3'e ~3,5 kat, M3'ten M4'e ~30 kat azalır. M1'de 3,3 saat olan kesinti M4'te ~20 saniyeye iner.
- **M1'de kesintinin çoğu planlıdır** (mid'de 3,3 saatin 2 saati). Bu, Precisely'nin "kesintinin büyük kısmı planlıdır" gözlemiyle aynı yöndedir [PRECISELY]; ancak model bu payı bir çarpanla vermez, olaylardan türetir. M1'in availability'sini en çok planlı kesinti varsayımı oynatır.
- **CPC donanım arızası hiçbir topolojide belirleyici değildir.** Yılda 0,3 saniye, M1'in toplam kesintisinin on binde birinden azdır. Mainframe'in "9 nine" donanım güvenilirliği, hizmet availability'sinin belirleyicisi değildir; belirleyici olan site ve kurtarma mimarisidir.
- **Kurtarma süresi M1'i etkilemez** (alternatif site yok). M2–M4'te etkisi, saha olayı ve planlı kesinti gruplarından küçüktür.

### 6.6. Feasibility, RPO ve RTO kısıtları

Bir topoloji üç koşulu da sağlıyorsa aday olur:

1. Geçerli senaryodaki availability ≥ hedef. Varsayılan senaryo mid'dir. Aralık çıktısında (Bölüm 7.8) low ve high senaryoları kendi availability değerleriyle topolojiyi yeniden seçer. Bu sayede availability belirsizliği maliyet aralığına yansır: high senaryoda M1 %99,9 hedefini karşılayamaz ve model M2'ye geçer.
2. Topolojinin RPO'su ≤ `rpo_seconds` (girdi verilmişse).
3. Topolojinin RTO'su ≤ `rto_minutes` (girdi verilmişse). M2–M4 için RTO, geçerli senaryodaki kurtarma süresidir. M1 için yedekten geri dönüş varsayılır ve SG24-8446'nın GDPS'siz DR aralığının üst ucu olan 72 saat alınır.

10K TPS, %99,9 hedefinde girdilerin etkisi:

| RPO / RTO girdisi | Seçim | Aylık toplam |
|---|---|---|
| yok | M1 | $846.187 |
| RPO = 0 | M2 (yalnızca senkron replikasyon RPO 0 verir) | $912.935 |
| RTO ≤ 60 dk | M3 (GDPS'siz kurtarma 2 saatin altına inmez) | $1.017.144 |
| RPO = 0 ve RTO ≤ 60 dk | M3 | $1.017.144 |
| RTO ≤ 1 dk | M4 | $1.108.787 |
| RPO = 0 ve RTO ≤ 1 dk | infeasible | — |

Son satır gerçek bir sınırı gösterir: saniye düzeyinde kurtarma yalnızca GDPS CA'nın yazılım replikasyonuyla elde edilir ve o da asenkron olduğu için RPO 0 vermez [GDPS-2026].

### 6.7. Topolojinin maliyete etkisi

Topoloji beş maliyet kalemini etkiler:

| Topoloji | Donanım ve bakım çarpanı | Enerji (frame) | GDPS (aylık, sabit) | Storage kopyası (Bölüm 8.4) | Personel çarpanı (Bölüm 7.7) |
|---|---|---|---|---|---|
| M1 | 1 | 1 | — | 1 | ×1,00 |
| M2 | 1 + DR_FRAME_COST_FRACTION | 2 | — | 2 | ×1,05 |
| M3 | 1 + DR_FRAME_COST_FRACTION | 2 | $50.000 | 4 | ×1,15 |
| M4 | 1 + DR_FRAME_COST_FRACTION | 2 | $100.000 | 4 | ×1,25 |

Yedekleme topolojiden bağımsızdır: her topolojide yedeğin iki kopyası iki ayrı sitededir (Bölüm 8.10).

**DR frame'i ve CBU.** DR CPC'si Capacity BackUp (CBU) ile alınır. CBU kaydı, kurulu ama kapalı işlemcileri yalnızca mikrokod (LICCC) ile açar; donanımın (drawer, bellek, I/O) önceden kurulu olması gerekir. Kayıt 1–5 yıllıktır, yıl başına bir ücretsiz 10 günlük test içerir (en fazla 15 test) ve tek bir 90 günlük gerçek aktivasyon hakkı verir [CBU]. Yazılım açısından en önemli kural şudur: *"Software charges for the designated CBU machine are based on its permanent configuration."* DR makinesinin IBM yazılım faturası yalnızca küçük kalıcı kapasitesine göre kesilir. Model bu küçük faturayı ihmal eder ve yazılımı yalnızca birincil frame'in MSU'su üzerinden hesaplar (önceki sürümdeki M3 ×1,15 ve M4 ×1,30 yazılım primi kaldırıldı).

CBU'nun fiyatı yayımlanmaz. DR frame'inin bedeli bu yüzden tam bir frame'in oranı olarak tanımlanır: `DR_FRAME_COST_FRACTION` = 0,50 [ASSUME], aralık 0,30–1,00. Oranın mantığı şudur. DR frame'inde fiziksel donanımın tamamı kuruludur, ama kapasitenin yalnızca küçük bir kısmı kalıcı olarak satın alınır, geri kalanı CBU kaydıdır. 1,00 değeri CBU kullanmayan, tam kapasiteli bir aynayı temsil eder ve aralığın üst ucudur. Enerji tam sayılır, çünkü DR frame'i açık ve replikasyonu çalıştırıyordur (tutucu).

**GDPS ayrı kalem.** GDPS, lisanslı otomasyon kodu ile IBM uygulama ve destek hizmetlerinden oluşan bir tekliftir. Fiyatı MSU'ya değil, otomatikleştirdiği sistem, sysplex ve site kapsamına bağlıdır ve yayımlanmaz [GDPS-PRICE]. Model bu yüzden GDPS'i kapasiteden bağımsız, sabit bir aylık kalem olarak alır: M3 (Metro Global) $50.000, M4 (CA) $100.000 [ASSUME]. Orta değerler, önceki sürümdeki yazılım priminin 10K TPS referans noktasındaki karşılığına (M3: 0,15 × $340K ≈ $51K; M4: 0,30 × $340K ≈ $102K) eşitlendi. Bu bir kalibrasyon değildir: önceki prim de kaynaksız bir varsayımdı ve bağımsız bir GDPS fiyatı bulunamadı. Eşitlemenin tek amacı, yapı değişikliğinin (yazılıma oranlı prim yerine sabit kalem) referans noktadaki maliyet seviyesini kaydırmamasıdır; GDPS'in payı artık hacim arttıkça küçülür. Belirsizlik geniş bir aralıkla temsil edilir. Seviye `GDPS_COST_LEVEL` ile 0,5–2,0 aralığında taranır. GDPS'in gerektirdiği NetView ve System Automation for z/OS MSU tabanlı ürünlerdir ve bu sabit kaleme dahil sayılır (basitleştirme). M2'deki HyperSwap için gereken Copy Services Manager ayrıca fiyatlanmaz.

10K TPS'te availability hedefinin maliyeti (`availability_sensitivity.py`; aralık sütununda parantez içi o senaryoda seçilen topolojidir):

| Hedef | Mid seçim | Aylık toplam (mid) | $/TPS/ay low / mid / high |
|---|---|---|---|
| %99,9 | M1 | $846.187 | 27,06 (M1) / 84,62 (M1) / 338,09 (M2) |
| %99,95 | M1 | $846.187 | 27,06 (M1) / 84,62 (M1) / 338,09 (M2) |
| %99,99 | M2 | $912.935 | 27,06 (M1) / 91,29 (M2) / 366,25 (M3) |
| %99,995 | M3 | $1.017.144 | 29,12 (M2) / 101,71 (M3) / 392,33 (M4) |
| %99,999 | M4 | $1.108.787 | 33,42 (M3) / 110,88 (M4) / 392,33 (M4) |
| %99,9999 | M4 | $1.108.787 | 37,08 (M4) / 110,88 (M4) / infeasible |

%99,9'dan %99,999'a çıkmak mid'de maliyeti %31 artırır. Artışın kaynakları: GDPS $100K, personel +$104K (topoloji çarpanı), DR frame donanım + bakım + enerji +$40K, storage +$19K. Yazılım değişmez (CBU kuralı). Hedef %99,9999'a çıktığında high senaryoda hiçbir topoloji yetmez.

### 6.8. Geçerlilik tehditleri ve sınırlamalar

- **İç geçerlilik (olay verisi):** Saha olayı sıklığı ve süresi tüm veri merkezi operatörlerinin verisidir; mainframe kurulumlarına özgü değildir. Uzun olay payı kamuya yansıyan kesintilerden gelir ve ağır olaylara doğru yanlıdır. İki etki zıt yönlüdür; bu yüzden aralık geniş tutuldu.
- **Planlı kesinti varsayımı:** M1'in sonucunu en çok bu parametre belirler ve kaynakla doğrulanmış bir sıklık bulunamadı. Gerçek bir z16 kurulumunun değişiklik kaydı (POR ve kesintili MCL sayısı) en değerli kalibrasyon olur.
- **RPO tanımı:** RPO tek site kaybı için verilir; bölgesel felakette M2 korumasızdır. Bölgesel felaket senaryosu eklenirse M2'nin RPO avantajı daralır.
- **Yapı geçerliliği:** Model beklenen değeri hesaplar. Kesintinin dağılımı (bir yılda hiç olmaması ya da tek bir uzun olay) yoktur; SLA ihlali olasılığı için stokastik model gerekir. Sistem içi yazılım arızaları sysplex ile tamamen maskelenmiş sayılır. Bölgesel felaket (iki metro sitenin birden kaybı) ayrıca modellenmez; M2'nin RPO 0 değeri yalnızca metro mesafedeki felaket için geçerlidir.
- **Maliyet:** CBU ve GDPS fiyatları yayımlanmıyor. İkisi de aralık parametresidir ve tornado çıktısında görünür.
- **Eşit derinlik:** Clustered taraf aynı denklemi kendi kurtarma süreleriyle kullanmalıdır: düğüm arızasının replikasyonla maskelenmesi, saha olayında başka bir bölgeye geçiş süresi ve planlı yükseltmelerin rolling yapılıp yapılamadığı. Saha olayı parametreleri iki tarafta ortaktır.

## 7. Maliyet Modeli

Aylık maliyet sekiz kalemden oluşur: yazılım, donanım, bakım, enerji, GDPS (Bölüm 6.7), personel, storage (Bölüm 8) ve yedekleme (Bölüm 8.10). Her kalemin veri güvenilirliği farklıdır; kesin fiyatı olmayan parametreler aralık olarak tanımlanır (Bölüm 7.8).

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
- **Mutlak seviye:** SW_PRICE_LEVEL_FACTOR = 1,0, 2004 nominal liste fiyatı demektir [ASSUME]. Güncel seviye iki yöne çekilir: IBM'in yeni donanım nesillerinde verdiği Technology Update indirimleri (z17 TU11: kademe bandına göre %12–42) aşağı, 20 yıllık enflasyon ve IBM'in periyodik fiyat artışları yukarı. Fiyat yılı karışıktır: personel 2025, storage 2019–2022 doları iken yazılım 2004 nominal listesine dayanır. Orta değerin (1,0) güncel seviyeye yakın olduğunu bağımsız bir kontrol destekler: model 150 MSU'da yıllık ~£1,0M veriyor, value-4it'in güncel gözlemi de ~£1M [VALUE4IT] (Bölüm 7.1.4). Aralığın alt ucu (0,5) TU indirimlerinin üst sınırına yakın büyük bir indirimi, üst ucu (1,75) 2004 listesinin ABD TÜFE ile 2026'ya taşınmış halini (2004 → 2026 yaklaşık ×1,7), yani hiç indirim olmamasını temsil eder (Bölüm 7.1.6, 7.8).

#### 7.1.3. Formül

Referans eğri (Db2, 2004 USD):

```
C_ref(m) = 3.960 + Σ_k  (min(m, üst_k) − alt_k)⁺ × fiyat_k     (k = L0…L7)
```

Yazılım yığını:

```
yazılım(m) = C_ref(m) × SW_PRICE_LEVEL_FACTOR × (k_z/OS + k_CICS + k_Db2)
```

m, faturalanan MSU'dur (sub-capacity, R4HA tepesi):

```
faturalanan_MSU = min(R4HA_yük / ham_TPS, 1) × kademe.MSU
```

Topoloji yazılımı değiştirmez: DR (CBU) makinesinin IBM yazılım faturası yalnızca kalıcı kapasitesine göre kesilir ve ihmal edilir [CBU]; ICF lisansı artırmaz [CFCC]. GDPS yazılıma prim olarak değil, ayrı bir sabit kalem olarak eklenir (Bölüm 6.7). Yıllık moddaki TFP-SW gelir-nötr kalibrasyonu bu fonksiyonla aynen çalışır: efektif MSU-saat fiyatı, Permanent stratejinin kademeli R4HA faturasından türetilir.

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
- Kapsam notu: köprü benchmark'ı (REDP-5320, CICS/COBOL) zIIP kullanmaz. Bu yüzden f yalnızca Db2 içeren profillere (tpcb_like, oltp_rw, oltp_heavy ve özel bileşim) uygulanır; redp_light'ta f = 0'dır (Bölüm 4.4). f'nin kendisi hâlâ kaynakla daraltılmamış bir varsayımdır.

#### 7.1.6. Duyarlılık

`python src/tools/software_sensitivity.py` (10K TPS, oltp_rw, %99,9, 20 TB; toplamlara personel, storage ve yedekleme dahil):

| Parametre | Değer → aylık toplam ($/TPS/ay) |
|---|---|
| Eski doğrusal $40/MSU | $556.492 (55,65), yazılım payı %9 |
| SW_PRICE_LEVEL_FACTOR | 0,5 → $676.203 (67,62) · 1,0 → $846.187 (84,62) · 1,5 → $1.016.171 (101,62) · 1,75 → $1.101.163 (110,12) |
| ZIIP_OFFLOAD_FRACTION | 0 → $896.300 (89,63, 3931-518) · 0,10 → $846.187 (84,62, 516) · 0,25 → $761.154 (76,12, 513) · 0,40 → $667.586 (66,76, 510) |
| L4+ düşüş oranı, 10K TPS | ×1,0 → $893.733 (89,37) · ×0,8 → $846.187 (84,62) · ×0,7 → $825.172 (82,52) |
| L4+ düşüş oranı, 100K TPS | ×1,0 → $5.710.257 (57,10) · ×0,8 → $4.132.378 (41,32) · ×0,7 → $3.666.768 (36,67) |

Yorum:

- Yazılım, personelden sonra en büyük ikinci kalemdir: 10K TPS'te toplamın %40'ı (Bölüm 7.8).
- Mutlak seviye toplamı −%20 ile +%30 arasında oynatır, ama maliyet/TPS eğrisinin **şeklini** değiştirmez. Crossover noktasının **yeri** bu parametreye duyarlıdır; varlığı ise değildir.
- L4+ düşüş oranı, faturalanan MSU 575'i aştığında devreye girer. oltp_rw'de bu ~4,5K TPS'e karşılık gelir. 100K TPS'te (kademe 13.603 MSU, faturalanan 12.159 MSU) toplamı $3,67M–5,72M aralığında oynatır. Yüksek hacimde en kritik yazılım varsayımı budur ve gerçek bir AWLC fiyat tablosuyla daraltılmalıdır.
- Ağırlıklı zIIP kullanımı (f = 0,40) 10K TPS'te toplamı %21 düşürür; bu yüzden zIIP payı aralık çıktısına dahildir.

### 7.2. Donanım Amortismanı

Mainframe donanım fiyatları açık liste olarak yayımlanmaz. Bağımsız fiyat rehberlerinin verdiği aralık ~$500.000 (giriş yapılandırması) ile ~$10.000.000+ (büyük yapılandırma) arasındadır [PRICE]. Model satın alma bedelini bir frame tabanı ve kapasiteyle doğrusal bir artış olarak kurar:

```
satın_alma = HW_FRAME_BASE_COST + kademe.PCI × HARDWARE_COST_PER_MIPS + zIIP bedeli
aylık donanım = satın_alma / (5 yıl × 12 ay)
```

- **HW_FRAME_BASE_COST = $500.000** [PRICE → ASSUME], aralık $250K–1M. Kapasiteden bağımsız fiziksel donanımı temsil eder: çerçeve, CPC drawer, bellek, I/O kanalları, HMC. Kaynak aralığının giriş ucuna eşitlendi. Taban olmadan en küçük kademeler gerçekçi olmayan biçimde ucuz çıkıyordu (3931-401 için $0,17M); bu da düşük TPS bölgesinde, yani crossover'ın beklendiği yerde, mainframe lehine bir yanlılık yaratıyordu.
- **HARDWARE_COST_PER_MIPS = $200 / PCI** [PRICE → ASSUME], aralık $150–300. 200 CP'lik 7K0 için toplam ~$44M eder; kaynağın "$10M+" ucunu aşar. Büyük uçta eğim muhtemelen yüksektir (mainframe aleyhine); aralığın alt ucu bu yüzden $150'dir.
- zIIP bedeli Bölüm 7.1.5'te tanımlıdır. DR frame'i bu bedelin DR_FRAME_COST_FRACTION oranıyla sayılır (Bölüm 6.7).

Bu yapı kabadır; gerçekte hacim indirimi ve drawer adımları eğriyi basamaklı yapar. Yayımlanmış veri olmadığı için iki parametre de aralık çıktısına dahildir (Bölüm 7.8). Donanım + bakım + enerji 10K TPS'te toplamın ~%9'udur.

### 7.3. Bakım

Aynı fiyat rehberi bakımı yıllık donanım değerinin %10–15'i olarak verir: MAINTENANCE_RATE_ANNUAL = 0,125. İlk yıl garanti kapsamında sayılır (HW_WARRANTY_YEARS = 1 [ASSUME]); bakım 5 yıllık amortisman süresine ortalanır:

```
aylık bakım = satın_alma × 0,125 × (5 − 1) / 5 / 12
```

Aynı kural storage'a da uygulanır (Bölüm 8.5); böylece iki donanım kalemi tutarlıdır. Bakım, donanım amortismanıyla aynı DR frame çarpanını izler.

### 7.4. Enerji

Modern z15/z16 sistemleri frame başına 20-40 kW güç çeker. Modelde orta değer kullanılır:

POWER_KW_PER_SYSTEM = 30 kW \| ELECTRICITY_USD_PER_KWH = \$0.12

aylık enerji = 30 × 0.12 × 730 = \$2.628 / ay / frame

Frame sayısıyla çarpılır. Elektrik fiyatı ABD ticari ortalaması; coğrafyaya göre değişir.

**Not:** Enerji frame başına sabit 30 kW alınıyor. 39 CP'nin üzerindeki kademeler birden fazla CPC drawer'ı, büyük yapılandırmalar birden fazla rack gerektirir (Max82–Max200). Bu yüzden büyük kademelerde enerji eksik sayılıyor; resmî güç değerleri IBM z16 IMPP belgesinden alınmalı (Bölüm 12).

### 7.5. Toplam Aylık Maliyet

total = yazılım(faturalanan_MSU) + (hardware_amort + maintenance) × (1 + n_DR × DR_FRAME_COST_FRACTION) + enerji × n_frames + GDPS + personel + storage + yedekleme

Yazılım kalemi DR frame'i için artmaz: CBU makinesinin yazılımı kalıcı kapasitesine göre faturalanır [CBU] ve ICF lisansı artırmaz [CFCC]. Donanım ve bakım DR frame oranıyla, enerji frame sayısıyla çarpılır (Bölüm 6.7).

### 7.6. Maliyet / TPS Eğrisi (mevcut varsayımlarla)

Statik mod, availability 0,999 (M1), 20 TB veri, mid senaryo, personel dahil. Ana sütunlar varsayılan oltp_rw profilidir; son sütun karşılaştırma için REDP işlemidir. Aynı eğrinin low/high aralığı Bölüm 7.8'dedir.

| TPS | Kademe (oltp_rw) | Kademe MSU | Aylık toplam | Yazılım payı | Personel payı | $/TPS/ay | $/TPS/ay (redp_light) |
|---|---|---|---|---|---|---|---|
| 500 | 3931-403 | 100 | $167.569 | %42 | %38 | 335,14 | 214,64 |
| 1.000 | 3931-405 | 158 | $221.731 | %44 | %40 | 221,73 | 115,21 |
| 5.000 | 3931-429 | 720 | $551.768 | %43 | %47 | 110,35 | 34,15 |
| 10.000 | 3931-516 | 1.423 | $846.187 | %40 | %49 | 84,62 | 24,20 |
| 50.000 | 3931-739 | 6.768 | $2.431.310 | %34 | %52 | 48,63 | 12,36 |
| 100.000 | 3931-792 | 13.603 | $4.132.378 | %35 | %50 | 41,32 | 9,46 |
| 150.000 | 3931-7F2 | 20.270 | $5.693.739 | %36 | %48 | 37,96 | 8,17 |

- **Eğri bükülüyor.** Dört sabit taban var: AWLC'nin taban ücreti, asgari personel ekibi, donanımın frame tabanı ve yedek hedefinin en küçük birimi (on-prem nesne depolamada site başına en küçük sistem, S3'te bulut hattı, TS7770'te iki küme). MSU arttıkça düşen marjinal yazılım fiyatı ve alt-doğrusal ekip büyümesi de buna ekleniyor. Sonuç olarak oltp_rw'de 500'den 150K TPS'e maliyet/TPS ~8,8 kat düşer. Bu, Değerlendirme #1'in "mainframe maliyet/TPS'i düz, çoklu crossover hipotezi zayıf" tehdidine kaynaklı mekanizmalarla verilen cevaptır.
- **Bükülme bölgesi işlem tanımıyla kayar.** REDP işleminde aynı eğri ~9 kat daha yüksek TPS'e kayar. Crossover noktasının yeri işlem bileşimine doğrudan bağlıdır.
- **Tek sistem tavanı.** oltp_rw'de ~187K TPS'in üstü tek z16 ile karşılanamaz (Bölüm 4.4.4).

Kademe seçimi: aynı kapasiteyi daha düşük MSU ile veren kademe açıkça avantajlıdır (örn. 10K TPS'te alt-kapasite 3931-516). Düşük hızlı CP'lerin latency etkisi yalnızca latency hedefi verildiğinde bağlayıcı olur (Bölüm 5.5).

### 7.7. Personel (Altyapı Ekibi)

#### 7.7.1. Kalemin savunması

Projenin araştırma boşluğu iddiası, mevcut karşılaştırmaların lisans, storage, DR ve **personeli** dışarıda bıraktığıdır (`project_justification.md`). Personel iki tarafta da var, ama ölçeklenme biçimi farklı: mainframe'de ekip kurulu kapasiteyle alt-doğrusal büyür, clustered tarafta sunucu ve düğüm sayısıyla daha doğrusal büyümesi beklenir. Bu fark crossover'ın yerini doğrudan etkileyebileceği için kalem modele girmeli. Uygulama geliştiricileri iki tarafta da aynı iş mantığını yazacağı için kapsam dışıdır. Model yalnızca altyapı ekibini sayar: z/OS ve CICS sistem programcıları, Db2 sistem DBA'ları, storage, otomasyon ve operasyon, kapasite ve performans, güvenlik (RACF).

Kesin bir "doğru FTE sayısı" yoktur. Kaynaklar arasında 3 kata varan fark var. Bu yüzden kalem tek bir değer olarak değil, kaynaklarla sınırlanmış bir **aralık** (düşük / orta / yüksek) olarak modellenir.

#### 7.7.2. Veri ve kaynaklar

**FTE oranları**

| Kaynak | Bulgu | Not |
|---|---|---|
| IBM Eagle TCO ekibi, 17 müşteri [IBM-EAGLE] | 5 FTE + her 625 MIPS için 1 FTE | Küçük/orta kurulumlar (grafik 0–3.000 MIPS); üretici kaynağı |
| Gartner IT Key Metrics Data 2016 [GARTNER-ITKMD] | Kurulu MIPS / mainframe FTE: 152 → 268 (5 yılda) | Bağımsız; ortalama; yıllık ~%12 verimlilik artışı |
| Gartner (IBM sunumunda) [IBM-TPF-2007] | Ekip MIPS iki katına çıkarken sabit kaldı (2001 → 2004) | Ölçek ekonomisinin yönü |
| IBM örnek karşılaştırma [IBM-TPF-2007] | 3.192 MIPS ≈ 4 FTE (~790 MIPS/FTE) | Üretici kaynağı; alt sınıra yakın |

**Ücret (2025 USD)**

| Kaynak | Değer |
|---|---|
| BLS OEWS, Mayıs 2025 medyanları [BLS-OEWS] | DBA/mimar $126.760 · sistem yöneticisi $99.130 · güvenlik analisti $129.180 |
| BLS OEWS, Mayıs 2023, DBA dağılımı | 25. yüzdelik $71.940 · medyan $101.510 · 75. yüzdelik $133.120 |
| Mainframe ilan ve anketleri [MF-PAY] | Payscale sistem programcısı ~$90K (10–90. yüzdelik $49–130K); Glassdoor Db2 z/OS DBA $104–163K |
| Yan hak çarpanı | IDC %28 [IDC-2016]; BLS ECEC'te maaş toplam işveren maliyetinin %70'i → ×1,43 [BLS-ECEC] |

Karma brüt maaş $95K / $120K / $150K, yan hak çarpanı 1,28 / 1,35 / 1,43 alındı. Yüklü maliyet: **$122K / $162K / $215K / FTE / yıl**. Çapraz kontrol: IBM 2007 sunumundaki karşılaştırma ~$175K/FTE ima ediyor. CA'nın uzman danışman saati ($247/saat) dış kaynak fiyatıdır; aralığın dışında tutuldu.

#### 7.7.3. Formül

```
FTE = max(taban, FTE_1000 × (PCI / 1000)^b) × topoloji_çarpanı
aylık personel = FTE × yüklü_maliyet / 12
```

| Senaryo | FTE_1000 | b | Taban | Yüklü maliyet |
|---|---|---|---|---|
| low | 4,0 | 0,60 | 3 | $122K |
| mid | 5,5 | 0,70 | 4 | $162K |
| high | 7,0 | 0,80 | 5 | $215K |

b < 1 olduğu için MIPS/FTE kapasiteyle artar (alt-doğrusal ölçek). Parametreler, eğrilerin kaynak çapalarını sarmalayacağı şekilde seçildi [ASSUME, kalibre]:

| PCI | low FTE (MIPS/FTE) | mid FTE | high FTE | IBM Eagle | Gartner 2016 (268) |
|---|---|---|---|---|---|
| 1.000 | 4,0 (250) | 5,5 (182) | 7,0 (143) | 6,6 | 3,7 |
| 3.000 | 7,7 (388) | 11,9 (253) | 16,9 (178) | 9,8 | 11,2 |
| 11.743 (10K TPS, oltp_rw) | 17,5 (670) | 30,8 (381) | 50,2 (234) | 23,8 | 43,8 |
| 20.000 | 24,1 (829) | 44,8 (447) | 76,9 (260) | 37,0 | 74,6 |
| 57.733 (3931-739) | 45,6 (1.266) | 94,1 (614) | 179,6 (322) | 97,4 | 215,4 |

- high, Gartner 2016 ortalamasını (~260 MIPS/FTE @20K) izler. Bu, 2016'dan beri verimlilik artışı olmadığı varsayımıdır.
- low, Gartner eğilimini (yılda ~%12) 2026'ya taşır (~830 MIPS/FTE @20K) ve IBM'in ~790 MIPS/FTE örneğine yaklaşır.
- mid ikisinin arasındadır ve küçük kurulumlarda IBM Eagle formülüne yakındır.
- Taban (3/4/5 FTE): en küçük kurulumda bile sistem programcısı, DBA ve otomasyon için asgari ekip.

Topoloji çarpanı: M1 1,00 · M2 1,05 (ikinci CEC, sysplex) · M3 1,15 (GDPS, iki site) · M4 1,25 [ASSUME]. Personel, birincil CEC'in kademesine göre hesaplanır; yedek frame'in kapasitesi ekip büyüklüğünü ikiye katlamaz. Yıllık modda personel, tepe yükü taşıyan (Permanent) kademeye göre hesaplanır. Böylece ekip büyüklüğü stratejiden bağımsızdır, çünkü ekip CoD günleri için işe alınıp bırakılmaz.

#### 7.7.4. Etkisi

- 10K TPS'te (oltp_rw, mid) personel 30,8 FTE, aylık $416K; toplamın %49'u. Yazılım %40, donanım + bakım + enerji %9, storage %0,9, yedekleme %0,7.
- Personel küçük hacimde de büyüktür (500 TPS'te %36), çünkü taban ekip sabittir. Bu, mainframe'in düşük TPS'te pahalı olmasının ikinci kaynağıdır (birincisi AWLC taban ücreti).
- Tek-parametre salınımında personel, toplamı en çok oynatan varsayımdır (Bölüm 7.8).

#### 7.7.5. Sınırlamalar

- FTE oranları kurulumun tamamı içindir (birden çok uygulama, batch dahil). Tek bir OLTP iş yüküne atanan pay daha düşük olabilir. Clustered tarafta da aynı kural (tüm altyapı ekibi) uygulanmalı.
- Gartner verisi 2016 tarihli ve bir CA/Broadcom yayını üzerinden aktarıldı. IBM verileri üretici kaynağıdır.
- Ücretler ABD içindir. Türkiye gibi farklı bir pazar için yüklü maliyet ayrı bir parametre seti gerektirir.
- Dış kaynak (outsourcing) ve yönetilen hizmet modelleri kapsam dışıdır.
- **FTE kurulu kapasiteye göre hesaplanır, yüke göre değil.** Bu bilinçli bir seçimdir: kaynak metrikler (IBM Eagle'ın "625 MIPS başına 1 FTE"si, Gartner'ın "FTE başına kurulu MIPS"i) kurulu kapasite üzerinden tanımlıdır. Sonucu, latency hedefi için alınan boş kapasitenin de personel ister görünmesidir: 10K TPS'te p99 hedefi 5 ms'ye sıkılaştığında kademe 3931-714'e çıkar ve personel 30,8'den 52 FTE'ye yükselir (aylık +$287K). Gerçekte boş kapasitenin yönetim yükü daha düşük olabilir; bu durumda sıkı latency hedeflerinde mainframe maliyeti olduğundan yüksek görünür. Clustered tarafta da aynı kural (kurulu düğüm sayısı) uygulanmalıdır.

### 7.8. Aralık Çıktısı ve Tek-Parametre Salınımı

Kamuya açık kesin fiyatı olmayan parametreler tek bir değer yerine kaynaklı bir aralık olarak tanımlıdır (`RANGE_PARAMETERS`). **low** mainframe lehine (düşük maliyet), **high** aleyhine uçtur:

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| Personel senaryosu | low | mid | high | Bölüm 7.7 |
| SW_PRICE_LEVEL_FACTOR | 0,5 | 1,0 | 1,75 | Bölüm 7.1.2 (üst uç: 2004 listesi TÜFE ile 2026'ya) |
| AWLC_UPPER_DECAY | 0,70 | 0,80 | 1,00 | Bölüm 7.1.2 |
| CPU_US_PER_SQL_READ | 15 | 30 | 60 | Bölüm 4.4 |
| CPU_US_PER_SQL_WRITE | 40 | 70 | 140 | Bölüm 4.4 |
| ZIIP_OFFLOAD_FRACTION | 0,25 | 0,10 | 0 | Bölüm 7.1.5 |
| HARDWARE_COST_PER_MIPS | $150 | $200 | $300 | Bölüm 7.2 |
| HW_FRAME_BASE_COST | $250K | $500K | $1M | Bölüm 7.2 |
| STORAGE_DISCOUNT | 0,85 | 0,70 | 0,50 | Bölüm 8.1.4 |
| BP_HIT_RATIO | 0,99 | 0,95 | 0,90 | Bölüm 4.4 |
| DR_FRAME_COST_FRACTION | 0,30 | 0,50 | 1,00 | Bölüm 6.7 (CBU) |
| GDPS_COST_LEVEL | 0,5 | 1,0 | 2,0 | Bölüm 6.7 |
| SITE_EVENT_LEVEL | low | mid | high | Bölüm 6.4 (saha olayı sıklığı ve süresi) |
| RECOVERY_LEVEL | low | mid | high | Bölüm 6.4 (kurtarma süreleri) |
| PLANNED_LEVEL | low | mid | high | Bölüm 6.4 (planlı kesinti) |
| BACKUP_RETENTION_WEEKS | 2 | 4 | 8 | Bölüm 8.10 |
| BACKUP_COMPRESSION | 3,0 | 2,0 | 1,5 | Bölüm 8.10 (IBM nominal 3:1 üst uç) |
| BACKUP_CACHE_LIST_USD_PER_TB | $1.000 | $2.000 | $4.000 | Bölüm 8.10 (fiyat yayımlanmıyor) |
| COS_HW_USD_PER_TB | $60 | $100 | $200 | Bölüm 8.10 (on-prem nesne depolama donanımı) |
| COS_SW_USD_PER_TB_MONTH | $0 | $5 | $10 | Bölüm 8.10 (açık kaynak – ticari abonelik) |

Availability parametreleri maliyeti doğrudan değil, topoloji seçimi üzerinden etkiler: bir senaryoda seçili topoloji hedefi karşılamazsa model daha pahalı topolojiye geçer. Yedek parametreleri de benzer biçimde yedek hedefinin seçimi üzerinden etkiler: seçili olmayan hedefin fiyatı (örneğin 20 TB'ta TS7770'in cache fiyatı) sonucu değiştirmez.

İki çıktı üretilir (`--range` ya da `solve_range` / `range_tornado`):

1. **Dış sınırlar:** tüm parametreler aynı anda low, mid ya da high. Kademe her senaryoda yeniden optimize edilir. Bu köşe değerlerdir, olasılık aralığı **değildir**; bütün varsayımların aynı yöne sapması düşük olasılıklıdır. Olasılıklı aralık (Monte Carlo) yol haritasındadır.
2. **Tek-parametre salınımı (tornado):** diğerleri mid'de iken her parametre tek tek low ve high'a çekilir.

10K TPS, oltp_rw, %99,9, 20 TB:

| Senaryo | Topoloji, kademe | Aylık toplam | $/TPS/ay |
|---|---|---|---|
| low | M1, 3931-428 | $270.612 | 27,06 |
| mid | M1, 3931-516 | $846.187 | 84,62 |
| high | M2, 3931-538 | $3.380.903 | 338,09 |

high senaryoda M1'in availability'si %99,84'e düşer ve %99,9 hedefini karşılayamaz; model M2'ye (DR frame'i, iki storage kopyası, ×1,05 personel) geçer.

| Parametre (diğerleri mid) | low ucu | high ucu |
|---|---|---|
| Personel | $608.039 | $1.329.625 |
| AWLC mutlak seviye | $676.203 | $1.101.163 |
| Okuma SQL CPU | $698.002 | $1.107.382 |
| Yazma SQL CPU | $761.055 | $1.016.175 |
| zIIP payı | $761.154 | $896.300 |
| AWLC L4+ düşüşü | $825.172 | $893.733 |
| Planlı kesinti | $846.187 | $912.935 (M1 → M2) |
| Donanım $/PCI | $830.804 | $876.953 |
| Donanım frame tabanı | $839.937 | $858.687 |
| Storage indirimi | $842.536 | $851.056 |
| Yedek saklama süresi | $845.324 | $847.913 |
| On-prem nesne depolama aboneliği | $844.461 | $846.622 (high ucunda S3'e geçer) |
| Buffer pool isabeti | $846.187 | $846.187 (yalnızca I/O ve latency) |
| Saha olayı, kurtarma süresi, DR frame bedeli, GDPS | $846.187 | $846.187 (M1 seçili kalır ya da kalem M1'de yok) |
| TS7770 sıkıştırması ve cache fiyatı, on-prem donanım fiyatı | $846.187 | $846.187 (20 TB'ta TS7770 seçilmez; on-prem'de en küçük sistem bağlayıcı) |

%99,999 hedefinde (M4) aynı tablo: GDPS seviyesi $1,06M–1,21M, planlı kesinti $1,02M–1,11M (low ucunda M3 yeter), DR frame bedeli $1,09M–1,15M; sıralamanın başı değişmez (personel, okuma SQL CPU, AWLC seviyesi).

Maliyet/TPS eğrisinin aralığı (`python src/tools/range_curve.py`, CSV: `data/out/range_curve_<profil>.csv`):

| TPS | low | mid | high | mid dökümü: yazılım / personel / donanım+bakım+enerji / storage / yedek |
|---|---|---|---|---|
| 500 | 148,04 | 335,14 | 876,20 | %42 / %38 / %13 / %4 / %3 |
| 1.000 | 91,48 | 221,73 | 662,71 | %44 / %40 / %11 / %3 / %2 |
| 5.000 | 36,84 | 110,35 | 391,41 | %43 / %47 / %9 / %1 / %1 |
| 10.000 | 27,06 | 84,62 | 338,09 | %40 / %49 / %9 / %0,9 / %0,7 |
| 50.000 | 13,12 | 48,63 | 271,76 | %34 / %52 / %13 / %0,3 / %0,3 |
| 100.000 | 10,08 | 41,32 | infeasible | %35 / %50 / %15 / %0,2 / %0,2 |
| 150.000 | 8,86 | 37,96 | infeasible | %36 / %48 / %16 / %0,1 / %0,2 |

Yorum:

- **Eğrinin şekli bütün senaryolarda aynıdır.** Maliyet/TPS, hacim arttıkça her senaryoda düşer. Crossover'ın varlığı varsayımlardan bağımsız, yeri ise varsayımlara çok duyarlıdır. Tezin ana çıktısı bu yüzden tek bir crossover noktası değil, bir crossover **bölgesi** olmalıdır.
- **Belirsizliğin iki ana kaynağı** personel ve işlem başına CPU'dur (SQL maliyeti). İkisi de kamuya açık, kesin bir rakamla daraltılamıyor. AWLC mutlak fiyat seviyesi, üst ucu enflasyona göre genişletildiği için (1,75) okuma SQL CPU'su ile birlikte ikinci sıradadır.
- **high sütunu tek bir topolojiye ait değildir.** high senaryoda M1 %99,9 hedefini karşılayamadığı için her TPS'te M2 seçilir. Availability belirsizliği bu yolla maliyet aralığının üst ucunu ~%10 yukarı taşır.
- **high senaryosu 100K TPS'te infeasible'dır:** okuma SQL'i 60 µs olursa tek z16 bu yükü taşıyamaz (Parallel Sysplex ölçeklemesi gerekir, Bölüm 4.4.4).
- **Kurulum başı çapraz kontrol:** Gartner ITKMD 2016'ya göre kurulu MIPS başına yıllık toplam mainframe maliyeti $5.517'den $3.057'ye düşmüş [GARTNER-ITKMD]. Aynı eğilim (yılda ~%11) sürerse 2026 için ~$940 eder. Model 10K TPS'te low/mid/high için $570 / $865 / $1.671 / PCI / yıl veriyor (high M2 ile). Gartner rakamı ISV yazılımlarını ve tesis giderlerini de içerdiği için modelin bu değerin altında kalması beklenir. Bu bir doğrulama değil, büyüklük mertebesi kontrolüdür.

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

Modelin sonuçları bu öngörüyü doğruluyor: 10K TPS'te (oltp_rw, personel dahil) storage ve yedekleme birlikte 20 TB veride toplamın %1,6'sı iken 500 TB'ta %22'si, 2.000 TB'ta %52'si (Bölüm 8.7, 8.10). Compute sabit kalırken storage veri hacmiyle büyüdüğü için veri hacmi, TPS'ten bağımsız ikinci bir crossover ekseni oluşturuyor. Bu, Değerlendirme #1'de zayıf bulunan çoklu crossover hipotezini destekleyen ilk somut mekanizmadır.

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
| Dizi, üretici tepe IOPS'unun %70'ine kadar yüklenir (STORAGE_IOPS_CEILING) | Tepe IOPS'un %100'ü | Tepe değer önbellek isabetli küçük blok ölçümüdür, gerçek OLTP karışımını temsil etmez; compute'taki %90 operasyonel tavanın storage karşılığı | oltp_rw'de DS8910F → DS8950F geçişi tavansız ~148K yerine ~104K TPS'te |
| Mainframe'de storage için ek CPU yükü yok | Host CPU yükü eklemek | I/O kanal alt sistemi ve SAP'lerde işlenir; kapasite köprüsündeki CICS benchmark'ı z/OS I/O'sunun CPU maliyetini zaten içerir. Eklemek çift sayım olur | x86 tarafında aynı kalem açıkça eklenmeli (asimetri bilinçli) |
| Global Mirror ve uzak site replikasyonu latency'ye eklenmez | Eklemek | Asenkron replikasyon yazmanın tamamlanmasını beklemez; etkisi RPO'dadır, latency'de değil | RPO topolojinin girdisidir (Bölüm 6.2) |

#### 8.1.4. Varsayımlar ve dayanakları

| Parametre | Değer | Dayanak | Taranan aralık | Kalibrasyon yolu |
|---|---|---|---|---|
| STORAGE_DISCOUNT | 0,70 | Kurumsal all-flash pazarında liste fiyatından %35–65, büyük anlaşmalarda daha fazla [VENDORBENCH]; IBM liste fiyatlarının yüksekliği (flash $8,62/GB) | 0,50–0,85 | Gerçek DS8900F teklifi veya kamu ihale kaydı |
| Lisans oranları | 0,15 + 0,10 | Yapı resmî, fiyat yok | 0,05–0,30 | IBM teklifi |
| DB_OVERHEAD_FACTOR | 1,5 | Db2 log, image copy, work alanı, sistem hacimleri | 1,2–2,0 | Db2 kapasite planlama kılavuzu |
| RAID_USABLE_FRACTION | 0,75 | RAID 6 (6+P+Q) | sabit | DS8900F Architecture Redbook |
| SAFEGUARDED_RESERVE | 0,25 | Değişim hızına ve saklanan kopya sayısına bağlı | sabit | Safeguarded Copy Redbook |
| HOST_COMPRESSION_RATIO | 1,0 | Tutucu: sıkıştırma yok | 1,0–2,5 | Db2 sıkıştırma oranları |
| Önbellek isabeti / zHyperLink payı | 0,90 / 0,80 | Büyük DS8900F önbelleği; Db2 senkron okumalarının zHyperLink'e uygunluğu. Okuma/yazma oranı ayrı bir parametre değildir, iş yükü profilinden gelir (Bölüm 8.6) | zHyperLink açık/kapalı | RMF/SMF verisi |
| t_miss | 300 µs | Önceki modelin I/O süresi; flash arka uç + FICON | sabit | DS8900F performans raporları |
| Metro Mirror mesafesi | 20 km | Metro mesafe DR için tipik | 10–100 km | Senaryoya bağlı girdi |
| İşlem başına I/O | oltp_rw: 3,8 senkron (2,8 okuma + 1 log yazımı), 5,8 toplam | Bileşimli profil (Bölüm 4.4): BP_HIT_RATIO 0,95, GETPAGES_PER_SQL_READ 4 | BP_HIT_RATIO 0,90–0,99 | Gerçek bir Db2 accounting (SMF 101) örneği |

#### 8.1.5. Geçerlilik tehditleri

- **İç geçerlilik (fiyat):** Storage maliyetinin mutlak düzeyi büyük ölçüde indirim oranına bağlı; 0,50–0,85 aralığında yaklaşık 3 kat değişiyor. Bu yüzden storage'lı sonuçlar tek bir nokta olarak değil, indirim aralığıyla birlikte raporlanmalı. Göreli sonuçlar (veri hacmiyle doğrusal büyüme, topolojiyle kopya sayısı, IOPS ile model geçişi) indirim oranından bağımsızdır.
- **Yapı geçerliliği (işlem başına I/O):** Önceki sabit 10 I/O, bileşimli profille (Bölüm 4.4) değiştirildi. oltp_rw'de 3,8 senkron + 2 asenkron I/O çıkar. Değer buffer pool isabet varsayımına duyarlıdır (0,90 → 8,6 IOPS/işlem; 0,99 → 3,56). Gerçek bir Db2 accounting örneğiyle daraltılmalıdır.
- **Yapı geçerliliği (IOPS tavanı):** Dizi, üretici tepe IOPS'unun %70'iyle boyutlanıyor. Oranın kendisi varsayım; gerçek OLTP karışımında dizinin sürdürülebilir IOPS'u iş yüküne bağlıdır ve IBM bunu yayımlamıyor. Tavan, compute tarafındaki %90 operasyonel tavanla aynı mantığı (tepe değerde çalışmamak) uygular.
- **Dış geçerlilik:** Tek üretici, 2019–2022 fiyatları, ABD liste fiyatları. Mainframe storage pazarının yaklaşık yarısını temsil eder; diğer yarı (PowerMax, VSP) farklı fiyatlanabilir.
- **Sonuç geçerliliği:** Storage'ın toplam içindeki payı varsayılan veri hacmine (20 TB) bağlı. Tezde storage payı tek bir yüzde olarak değil, veri hacmi ekseninde bir eğri olarak sunulmalı.

#### 8.1.6. Clustered tarafla eşleştirme

Storage, iki tarafın da aynı girdileri kullandığı ortak bir arayüzdür: `data_tb`, `data_growth`, iş yükü profilinden IOPS ve availability/RPO/RTO'nun seçtirdiği topoloji. Clustered tarafın aynı arayüze bağlanırken eklemesi gerekenler: DB mimarisine bağlı kopya sayısı (replication factor), storage yığınının host CPU yükü, ağ üzerinden storage gecikmesi, kendi $/TB ve bakım parametreleri. Mainframe tarafında bu kalemlerin olmaması bilinçli bir asimetridir ve yukarıdaki kararlarla gerekçelendirilmiştir; iki taraf aynı derinlikte, farklı mekanizmalarla modellenir (eşit derinlik ilkesi, `project_context_restore_v4.md`, 3.7).

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

- Planlama ufku 3 yıl [ASSUME]. Dizi bu ufkun sonundaki veriye göre boyutlanır. 5 yıllık NPV'de storage iki döngüde (t = 0 ve t = 3) alınır; her döngü kendi sonundaki veriye göre boyutlanır (Bölüm 9.10.3).
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

D_io = senkron okuma I/O × t_okuma + senkron yazma I/O × t_yazma

t_okuma = h × (z × t_zHL + (1 − z) × t_FICON) + (1 − h) × t_miss

t_yazma = t_FICON + senkron replikasyon (yalnızca M2–M4)

Okuma ve yazma I/O sayıları iş yükü profilinden gelir (Bölüm 4.4): okuma, buffer pool kaçağı; yazma, commit'teki log yazımı. Önceki sürüm sabit bir okuma payı (r = 0,70) kullanıyordu; bu, profilin kendi bileşimiyle çelişebiliyordu (örneğin oltp_rw'nin senkron I/O'sunun %74'ü okumadır, tpcb_like'ınkinin çoğu yazmadır). Denetimde kaldırıldı.

| Parametre | Değer | Kaynak |
|---|---|---|
| h: önbellek isabeti | 0,90 | [ASSUME] |
| z: isabetli okumaların zHyperLink'e uygun payı | 0,80 | [ASSUME] Db2 senkron rastgele okumalar |
| t_zHL | 20 µs | [REDP-5554] |
| t_FICON | 90 µs | [TT-2019] (yazmalar DS8900F NVS'ine hızlı yazma) |
| t_miss | 300 µs | [ASSUME] flash arka uç + FICON |
| Senkron replikasyon | mesafe × 10 µs/km, varsayılan 20 km | Fiberde ışık ~5 µs/km tek yön; gidiş-dönüş 10 µs/km |

Sonuç: t_okuma 61 µs; t_yazma M1'de 90 µs, M2–M4'te 290 µs. oltp_rw'de (2,8 okuma + 1 yazma) D_io M1'de 0,26 ms (ortalama 68 µs/I/O), M2–M4'te 0,46 ms (121 µs/I/O). zHyperLink kapalıyken M1'de D_io 0,40 ms. Metro Mirror mesafesi 100 km'ye çıkarsa M2'de D_io 1,26 ms. Böylece availability topolojisi latency'yi de etkiler: daha yüksek availability, senkron kopya nedeniyle daha yüksek yazma gecikmesi demektir.

### 8.7. Doğrulama Örnekleri

Statik mod, oltp_rw, 20 TB veri, varsayılan parametreler (AWLC kademeli yazılım, zIIP ve yedekleme dahil):

| Senaryo | Seçim | Storage | Storage / toplam |
|---|---|---|---|
| 10K TPS, %99,9 | M1, 3931-516 | 1× DS8910F-993, 76 TB ham, 58K IOPS, $7.496/ay | %0,9 |
| 10K TPS, %99,999 | M4, 3931-516 | 4× DS8910F-993, 259 TB ham, $26.344/ay | %2,4 |
| 10K TPS, %99,99999 | infeasible | Hiçbir topoloji mid değerlerle bu hedefe ulaşmıyor (Bölüm 6.5) | – |
| 60K TPS, %99,9 | M1, 3931-749 | 348K IOPS, 1× DS8910F-993, $7.496/ay | %0,3 |
| 150K TPS, %99,9 | M1, 3931-7F2 | 870K IOPS (> 0,7 × 860K) → 1× DS8950F-996, $8.419/ay | %0,1 |

Gerçekçi işlem tanımıyla aynı TPS daha az disk I/O'su (5,8/işlem) ama çok daha fazla CPU ister. Bu yüzden DS8950F'e geçiş ~104K TPS'e kaydı (önceden ~60K) ve storage'ın payı küçüldü.

Veri hacmi ekseni (10K TPS, %99,9, personel dahil):

| Veri | Storage | Yedekleme (seçilen hedef) | İkisinin toplamdaki payı |
|---|---|---|---|
| 5 TB | $2.948 | $4.555 (AWS S3) | %0,9 |
| 20 TB | $7.496 | $5.635 (on-prem nesne) | %1,6 |
| 100 TB | $31.749 | $11.648 (on-prem nesne) | %5,0 |
| 300 TB | $92.593 | $34.040 (on-prem nesne) | %13 |
| 500 TB | $153.226 | $75.420 (TS7770) | %22 |
| 2.000 TB | $611.730 | $290.531 (TS7770) | %52 |

Storage ve yedekleme maliyeti veri hacmiyle neredeyse doğrusal büyürken compute sabit kalır. Değerlendirme #3'te öngörülen ikinci crossover ekseni (veri hacmi) mainframe tarafında oluşuyor. Küçük ve orta veride yedek nesne depolamadadır ve storage'dan ucuzdur. M1'de ~360 TB'ın üstünde tam geri yükleme 36 saate sığmadığı için yedek TS7770'e geçer; bu geçiş toplamın payında ~2 puanlık bir basamak yaratır (Bölüm 8.10.5). Storage ve yedeğin birlikte toplamın onda birini geçmesi ~220 TB'ı, beşte birini geçmesi ~450 TB'ı buluyor. Clustered tarafta kopya sayısı (replication factor) ve $/TB farklı olduğu için iki eğrinin eğimi farklı olacaktır.

Yıllık mod (10K TPS ortalama, 20 TB): 1× DS8910F-993, yıllık ~$90K, toplamın %0,4–0,7'si; strateji sıralaması değişmiyor (storage üç stratejide de aynı).

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
- Safeguarded Copy yalnızca mantıksal bozulmaya karşı korur ve birincil dizinin içindedir; site dışı yedek ayrı bir katmandır (TS7770, Bölüm 8.10).
- Storage ağı (FICON switch'ler, uzun mesafe bağlantı) yok: proje kararıyla iki tarafta da kapsam dışı. Uzun mesafe DR hattının maliyeti bu kararla dışarıda kalıyor; GDPS sabit kalemi (Bölüm 6.7) bu hattı içermez.
- Global Mirror ve M4'ün uzak site replikasyonu asenkron olduğundan latency'ye eklenmiyor; etkisi topolojinin RPO değerindedir (Bölüm 6.2).

### 8.10. Yedekleme — TS7770, On-Prem Nesne Depolama ve AWS S3

#### 8.10.1. Katmanın savunması

- **Neden dahil:** Projenin maliyet kategorileri compute, yazılım, storage, backup/DR ve personeldir (`project_justification.md`). Eşit derinlik ilkesi her kategorinin iki tarafta da modellenmesini ister. Storage replikasyonu (Metro/Global Mirror) ve GDPS yedeğin yerini tutmaz, çünkü mantıksal bir bozulmayı (hatalı toplu güncelleme, fidye yazılımı) anında bütün kopyalara taşırlar. Safeguarded Copy bozulmaya karşı korur ama birincil dizinin içindedir; site kaybında onunla birlikte gider.
- **M1 için zorunlu:** M1'in RPO'su 24 saat, RTO'su 72 saattir (Bölüm 6.2). Bu değerler, son günlük yedeğin başka bir sitede olmasına ve oradan zamanında geri yüklenebilmesine dayanır. Yedek katmanı olmadan M1'in felaket kurtarma iddiası maliyetsiz kalırdı.
- **İki tarafta aynı büyüklükte değil:** Mainframe'de yedek, Db2 image copy'leri ve arşiv loglarıdır. Clustered tarafta yedekleme yazılımı ve çoğunlukla nesne depolama kullanılır. Lisans, kapasite ve sıkıştırma yapısı farklı olduğu için kalem birbirini götürmez ve crossover'ı etkileyebilir.
- **Neden üç hedef:** Bir kurum mainframe yedeğini gerçekte üç yoldan biriyle alır. Model üçünü de aday yapar ve kısıtları karşılayanlar arasından aylık maliyeti en düşük olanı seçer (`BACKUP_TARGET = "auto"`; `--backup-target` ile tek hedef zorlanabilir).
  - **TS7770 sanal teyp:** IBM'in mainframe sanal teyp ürünüdür. FICON ile bağlanır; Db2 image copy, HSM ve arşiv log tipik hedefleridir. Grid replikasyonuyla siteler arası kopya tutar [TS7700-2024]. z16 ile aynı dönemin ürünüdür (R5.x, Power9). Model disk-only yapılandırmayı kullanır.
  - **On-prem nesne depolama (S3 uyumlu):** IBM Cloud Object Storage, Ceph veya MinIO sınıfı kurum içi sistemlerdir. Mainframe'den yol DS8900F'in Transparent Cloud Tiering (TCT) özelliğidir. Image copy'ler önce DASD'ye yazılır, DFSMShsm ile TCT üzerinden nesne depolamaya göç ettirilir. Veri z/OS işlemcilerinden değil, DS8900F'in Ethernet portlarından geçer [SG24-8381].
  - **AWS S3 (hibrit):** Aynı TCT yolu kullanılır; hedef AWS S3'tür (Standard-IA sınıfı) ve bağlantı Direct Connect hattıyla kurulur [SG24-8381, AWS-S3-2026, AWS-DX-2026]. Kamu bulutu olduğu için bu seçenek projenin on-prem çerçevesini hibrite çevirir. Seçildiğinde çıktıda "hibrit" diye işaretlenir.
- **Neden disk:** Model 4 haftalık operasyonel yedeği kapsar. Fiziksel teyp (TS4500 kütüphanesi, TS1160 sürücüler) ve S3 Glacier sınıfları uzun süreli düzenleyici saklama için kullanılır. Arşiv projede kapsam dışıdır (Değerlendirme #3).

#### 8.10.2. Yedek hacmi

Hacim üç hedefte de aynıdır; bir sitede saklanan miktar (sıkıştırma öncesi):

image copy = D_plan × hafta × (1 tam + 6 artımlı × günlük değişim)

arşiv log = ort. TPS × işlem başına log baytı × 86.400 × 7 × hafta

işlem başına log baytı = yazma SQL × 400 B + commit × 200 B

tam geri yükleme = D_plan × (1 + 6 × günlük değişim) + bir haftalık log

| Parametre | Değer | Dayanak | Aralık |
|---|---|---|---|
| D_plan | Veri × (1 + büyüme)³ | Storage ile aynı planlama ufku (Bölüm 8.4) | — |
| Tam kopya sıklığı | Haftada bir; günlük artımlı | IDUG EMEA oturumu: tam kopya "often taken weekly", değişim %10'u aşınca tam kopya; sık güncellenen tablolarda günlük artımlı [IDUG-2024] | sabit |
| BACKUP_RETENTION_WEEKS | 4 | [ASSUME]; IBM saklama süresi vermez, yalnızca eski kopyaların tutulmasını önerir [DB2-BACKUP] | 2–8 (aralık parametresi) |
| BACKUP_DAILY_CHANGE | 0,03 | [ASSUME]; haftada ~%20, tam kopya eşiğinin (%10/hafta) üstünde, yani haftalık tam kopya gerekçeli | 0,01–0,05 |
| LOG_BYTES_PER_SQL_WRITE / COMMIT | 400 B / 200 B | [ASSUME]; Db2 log kaydı satırın önce/sonra görüntüsü ve başlıktan oluşur | 200–1.000 B |
| Ortalama yük | Statik modda TPS / 1,5; yıllık ve NPV modunda profilin ortalaması | [ASSUME] statik TPS tasarım tepesidir; 1,5 steady_oltp oranı | — |
| Kopya sayısı | TS7770 ve on-prem nesne: 2 (iki site). S3: 1 nesne kopyası | IBM: "Make two copies of each level of image copy data sets" [DB2-BACKUP]. S3 nesneyi bölge içinde en az üç erişilebilirlik alanına dağıtır; site dışı kopya odur, ikinci kopya sağlayıcının kendi yedekliliğidir | sabit |
| Sıkıştırma | TS7770: 2,0. Nesne hedefleri: 1,0 | TS7770 nominal 3:1 [TS7700-2024]; Db2 verisi sıkıştırılmamış sayıldığı için (Bölüm 8.4) orta değer düşük tutuldu. TS7700 dışındaki TCT hedeflerinde DS8000 sıkıştırma yapmaz [SG24-8381] | TS7770: 1,5–3,0 (aralık parametresi) |

#### 8.10.3. Kısıtlar

Bir hedef ancak üç kısıtı birden karşılarsa adaydır:

| Kısıt | Formül | Dayanak |
|---|---|---|
| Yedek penceresi | günlük yazma / hedef verimi ≤ 8 saat | Günlük yazma = D_plan / 7 + artımlı kopya + günlük log. Pencere [ASSUME] |
| Geri yükleme (yalnızca M1) | tam geri yükleme / hedef verimi ≤ RTO × 0,5 = 36 saat | M1'de alternatif site yoktur ve yedek DR yolundadır. RTO'nun yarısı geri yüklemeye, yarısı donanım, IPL ve log uygulamaya ayrılır [ASSUME]. M2–M4'te site kaybını replikasyon karşılar; bu yüzden kısıt yalnızca M1'de bağlar |
| TCT verimi (nesne hedefleri) | gereken verim ≤ 5.000 MB/s | Nesne hedefleri DS8900F'in Ethernet portlarından geçer: sunucu başına en fazla altı port, 10 GbE kartlarla [SG24-8381]. Tek DS8900F için ~%40 verim varsayıldı [ASSUME]. IBM TCT verimi yayımlamaz |

TS7770 her zaman feasible'dır, çünkü küme ekleyerek ölçeklenir. Site başına küme sayısı = max(⌈cache / 3.900 TB⌉, pencere kısıtı, geri yükleme kısıtı); küme başına verim 4.000 MB/s'tir [TS7700-2024]. Nesne hedeflerinin verimi ise TCT tavanıyla sınırlıdır. Bu tavanı aşan iş yükünde elenirler. S3'te Direct Connect hattı sayısı (10 Gbps × %80 = 1.000 MB/s) gereken verimden hesaplanır.

#### 8.10.4. Maliyet

**TS7770:**

| Kalem | Formül | Dayanak |
|---|---|---|
| Küme tabanı | $493.080 liste × küme sayısı | TS7700'ün yayımlanmış başlangıç fiyatı (2006, nominal) [TS7700-2006]. TS7770 fiyatı yayımlanmıyor |
| Cache | site başına cache TB × $2.000 liste × 2 site; cache 20 TB adımlarla | [ASSUME]; nearline HDD cache, DS8900F flash liste fiyatının (~$8.620/TB) yaklaşık dörtte biri. Aralık $1.000–4.000. 20 TB adım: Capacity on Demand [TS7700-2024] |
| İndirim | (taban + cache) × (1 − STORAGE_DISCOUNT) | DS8900F ile aynı indirim (Bölüm 8.5) |
| Amortisman ve bakım | capex / 5 yıl; %15 / yıl, 1 yıllık garanti sonrası | Storage ile aynı [VENDORBENCH] |
| Enerji | küme × 4 kW × $0,12 × 730 saat | [ASSUME]; tek fazlı 30 A besleme [TS7700-2024], tüketim yayımlanmıyor |

**On-prem nesne depolama:**

| Kalem | Formül | Dayanak |
|---|---|---|
| Donanım | site başına max($70.000, saklanan TB × $100) × 2 site | MinIO'nun TCO örneği: 60 × 16 TB HDD'li 2U sistem $70K, 720 TB kullanılabilir (silme kodlaması 0,75) [MINIO-TCO]. $70K en küçük site sistemidir. Aralık $60–200/TB |
| Yazılım / destek | saklanan TB × 2 site × $5/TB-ay | [MINIO-TCO → ASSUME]: ticari abonelik listesi ~$10/TB-ay, açık kaynak 0. Aralık 0–10 |
| Amortisman, bakım | storage ile aynı (5 yıl; %15/yıl, 1 yıllık garanti sonrası) | — |
| Enerji | max(1 kW, 1,5 kW / PB) × 2 site | [ASSUME] |

MinIO bir üretici kaynağıdır ve kendi yazılımını satar. Bu yüzden iki fiyat da aralık parametresidir (Bölüm 7.8).

**AWS S3 (us-east-1, 2026 liste):**

| Kalem | Formül | Dayanak |
|---|---|---|
| Depolama | saklanan TB × 1.000 × $0,0125 × max(1, 30 gün / saklama günü) | Standard-IA $0,0125/GB-ay; en kısa faturalanan süre 30 gün. 4 haftalık saklamada 28 gün olduğu için ×1,07 [AWS-S3-2026] |
| İstek | günlük yazma / 256 MB nesne × 30,4 gün × $0,01 / 1.000 PUT | [AWS-S3-2026]; nesne boyutu [ASSUME]. İhmal edilebilir düzeyde |
| Geri yükleme | yılda 1 tam geri yükleme × ($0,02 DX çıkış + $0,01 geri getirme) / GB | [AWS-S3-2026, AWS-DX-2026]; yılda bir geri yükleme testi [ASSUME]. Veri girişi ücretsiz |
| Hat | hat sayısı × ($2,25 × 730 saat DX portu + $2.000 taşıyıcı devre) | 10 Gbps dedicated port $2,25/saat [AWS-DX-2026]. Taşıyıcı devre ve cross-connect [ASSUME], aralık $1.000–4.000 |
| Donanım, enerji | yok | Bütün maliyet işletme gideridir |

Storage ağı proje kararıyla iki tarafta da kapsam dışıdır (Bölüm 8.9). Bulut hattı ise yalnızca S3 seçeneğine özgü olduğu ve onsuz seçenek var olamayacağı için maliyete dahildir. Dışarıda bırakılsaydı S3 haksız biçimde ucuz görünürdü.

**NPV'de (Bölüm 9.10):** TS7770 ve on-prem nesne depolamanın donanımı storage ile aynı döngülerde (t = 0 ve 3) alınır. Abonelik, S3 ve hat ücretleri her yıl o yılın verisi ve yüküyle hesaplanır. Hedef 1. yılda seçilir ve 5 yıl boyunca sabit kalır. On-prem abonelik bakım artışıyla (%3) büyür. S3 ve hat fiyatları sabit tutulur, çünkü S3 fiyatları yıllardır değişmemiştir [MINIO-TCO].

**Örnek (10K TPS, 20 TB, M1):**
- Ortak hacim: D_plan 30,4 TB → image copy 30,4 × 4 × 1,18 = 144 TB; log 6.667 TPS × 1.800 B × 86.400 × 28 = 29 TB. Toplam 173 TB (tam: 172,6 TB).
- **TS7770:** (144 + 29) / 2 = 87 TB → site başına 100 TB cache, birer küme. Capex = (2 × $493.080 + 2 × 100 × $2.000) × 0,30 = $415.848. Aylık: amortisman $6.931 + bakım $4.158 + enerji $701 = **$11.790**.
- **On-prem nesne:** Sıkıştırma yok, site başına 173 TB. 173 × $100 = $17.300 < $70.000, yani en küçük sistem iki site için $140.000. Aylık: amortisman $2.333 + bakım $1.400 + abonelik 2 × 172,6 × $5 = $1.726 + enerji $175 = **$5.635**.
- **AWS S3:** 172,6 TB × $12,5 × 30/28 = $2.312. Hat: 1 × ($1.643 + $2.000) = $3.643. Geri yükleme testi (43,2 TB) $108/ay, istekler $8. Toplam **$6.069**.
- **Seçim:** On-prem nesne depolama, $5.635 (toplamın %0,7'si). Gereken verim 333 MB/s, geri yükleme ~2,4 saat; iki kısıt da rahat karşılanıyor.

#### 8.10.5. Sonuçlar

`python src/tools/npv_sensitivity.py`, bölüm 1. Üç adayın aylık maliyeti, 10K TPS (x = kısıt karşılanmıyor):

| Veri | Topoloji | TS7770 | On-prem nesne | AWS S3 | Gereken verim | Seçilen |
|---|---|---|---|---|---|---|
| 5 TB | M1 / M3 | $9.870 | $4.558 | $4.555 | 125 / 82 MB/s | S3 (farkı $3) |
| 20 TB | M1 / M3 | $11.790 | $5.635 | $6.069 | 333 / 219 MB/s | On-prem nesne |
| 100 TB | M1 | $20.750 | $11.648 | $17.787 | 1.441 MB/s | On-prem nesne |
| 100 TB | M3 | $20.750 | $11.648 | $14.145 | 949 MB/s | On-prem nesne |
| 300 TB | M1 | $52.380 | $34.040 | $48.903 | 4.210 MB/s | On-prem nesne |
| 300 TB | M3 | $43.790 | $34.040 | $41.618 | 2.774 MB/s | On-prem nesne |
| 500 TB | M1 | $75.420 | x | x | 6.980 MB/s | TS7770 |
| 500 TB | M3 | $75.420 | $56.431 | $69.091 | 4.600 MB/s | On-prem nesne |
| 1.000 TB | M1 / M3 | $150.200 / $141.610 | x | x | 13.903 / 9.164 MB/s | TS7770 |
| 2.000 TB | M1 / M3 | $290.531 / $273.350 | x | x | 27.751 / 18.293 MB/s | TS7770 |

Statik modda (%99,9, M1) seçilen hedef ve payı:

| Veri | Seçilen | Aylık yedek | Toplamdaki payı | Storage |
|---|---|---|---|---|
| 5 TB | AWS S3 (hibrit) | $4.555 | %0,5 | $2.948 |
| 20 TB | On-prem nesne | $5.635 | %0,7 | $7.496 |
| 100 TB | On-prem nesne | $11.648 | %1,3 | $31.749 |
| 300 TB | On-prem nesne | $34.040 | %3,5 | $92.593 |
| 500 TB | TS7770 | $75.420 | %7,1 | $153.226 |
| 2.000 TB | TS7770 | $290.531 | %16,7 | $611.730 |

Nesne hedeflerinin elendiği veri hacmi (10K TPS), TCT verimine göre: 2.500 MB/s'te M1 180 TB, M3 270 TB; 5.000 MB/s'te M1 360 TB, M3 550 TB; 10.000 MB/s'te M1 720 TB, M3 1.100 TB.

Varsayım taraması (20 TB, M1; seçilen hedef):
- Saklama 2 / 4 / 8 hafta → $4.772 / $5.635 / $7.361 (hep on-prem nesne).
- On-prem abonelik 0 / 5 / 10 $/TB-ay → $3.909 / $5.635 / $6.069. 10'da S3'e geçer.
- Hat devresi 0 / 2.000 / 4.000 $/ay → 0'da S3 seçilir ($4.069).
- S3 sınıfı: Glacier Instant Retrieval fiyatıyla ($0,004/GB-ay) S3 seçilir ($4.498).
- On-prem donanım fiyatı, TS7770 cache fiyatı ve storage indirimi 20 TB'ta seçimi değiştirmez. On-prem tarafta en küçük sistem bağlayıcıdır; TS7770 seçilmediği için onun fiyatları etkisizdir.

Zorlanan hedefle statik maliyet (10K TPS, 20 TB): auto $84,62/TPS/ay; yalnızca TS7770 $85,23; yalnızca S3 $84,66.

Yorum:

- **Küçük ve orta veride nesne depolama TS7770'in yaklaşık yarısıdır.** Fark, TS7770'in iki küme tabanından gelir. 5 TB'ta on-prem ve S3 neredeyse eşittir; S3'ün maliyetinin çoğu hattır.
- **Büyük veride TS7770'e dönülür, iki farklı nedenle.** M3'te neden günlük yedek verimidir: 1.000 TB'ta günlük yazma TCT tavanını aşar. M1'de neden daha erkendir (360 TB): tam geri yüklemenin 36 saate sığması gerekir. Yani topoloji yedek teknolojisini de belirler. Bu, availability ile yedek arasında modelin daha önce göstermediği bir etkileşimdir.
- **AWS S3 nadiren kazanır.** Yalnızca çok küçük veride ya da hat bedeli yokken (kurumun zaten bir Direct Connect hattı varsa) öne geçer. Bu sonuç, hattın sabit bedelinin dahil edilmesine bağlıdır.
- **Başlık sonucuna etkisi küçüktür.** 10K TPS ve 20 TB'ta yedek $11.790'dan $5.635'e iner; toplam $85,23'ten $84,62/TPS/ay'a düşer (−%0,7). Veri hacmi ekseni ise korunur. Storage ve yedek birlikte 500 TB'ta toplamın %22'si, 2.000 TB'ta %52'sidir (Bölüm 8.7), çünkü büyük veride yedek yine TS7770'dir.
- **Log hacmi TPS'e bağlıdır.** 10K TPS'te 4 haftalık log 29 TB'tır; küçük veride image copy ile aynı mertebededir. Bu, yedeği TPS'e de bağlayan tek mekanizmadır ve clustered tarafta aynı bileşimden (yazma ve commit sayısı) türetilmelidir.

#### 8.10.6. Geçerlilik tehditleri ve sınırlamalar

- **TS7770 fiyatı:** Yayımlanmıyor. Taban, 2006 tarihli TS7700 başlangıç fiyatıdır; enflasyon yukarı, teknoloji fiyatlarının düşüşü aşağı yönde etkiler ve model ikisini birbirini götürmüş sayar. Cache fiyatı kaynaksızdır. İkisi de aralıkla raporlanır.
- **On-prem nesne depolama fiyatı:** Tek kaynak bir üretici örneğidir [MINIO-TCO]. IBM Cloud Object Storage'ın kurum içi fiyatı yayımlanmıyor. Donanım ve abonelik aralık parametresidir.
- **TCT verimi yayımlanmıyor.** 5.000 MB/s, port sayısından türetilmiş bir varsayımdır. Nesne hedeflerinin elendiği veri eşiği bu değerle doğrusal ölçeklenir (yukarıdaki tablo). Birden fazla DS8900F dizisi olan büyük kurulumlarda TCT verimi dizi sayısıyla artar; model tek dizinin tavanını kullanır.
- **Image copy için TCT yolu:** SG24-8381, DFSMShsm göçünü ve DFSMSdss döküm/geri yüklemesini destekler. Db2 image copy'lerini açıkça bir kullanım durumu olarak listelemez. Model, image copy'lerin DASD'ye yazılıp DFSMShsm ile göç ettirildiğini varsayar. DASD'deki geçici alan, storage boyutlandırmasındaki ek yük payının içindedir (Bölüm 8.4). Ayrıca TCT, teybe yazılmış veriyi doğrudan taşıyamaz [SG24-8381].
- **CPU maliyeti:** Image copy (COPY utility) ve arşiv log işlemleri CPU tüketir. Model bu işlerin R4HA tepesinin dışındaki bir pencerede çalıştığını varsayar ve MSU'ya eklemez. TCT veriyi z/OS dışında taşıdığı için nesne hedeflerinde bu varsayım daha da güçlüdür [SG24-8381].
- **Mantıksal bozulmadan geri dönüş:** Geri yükleme kısıtı yalnızca M1'de bağlar. M2–M4'te mantıksal bozulmadan geri dönüşün de bir RTO'su vardır, ama model bunu ayrı bir hedef olarak almaz.
- **Kapsam dışı:** fiziksel teyp ve uzun süreli arşiv, grid ve LAN ağı (Bölüm 8.9), Performance on Demand verim adımlarının fiyatı, TS7770'in kendi bulut katmanı (TS7770 + nesne depolama), IBM Cloud Tape Connector ve FlashCopy tabanlı yedek. Çok büyük veride (yüzlerce TB) kurumlar image copy yerine DS8900F FlashCopy ile yedek alır; model bu durumda yedeği fazla sayabilir.
- **Clustered tarafla eşleştirme:** Aynı girdiler iki tarafta da kullanılmalıdır: veri hacmi, büyüme, saklama süresi, günlük değişim, işlem bileşiminden log hacmi ve aynı üç hedefin fiyatları. Clustered taraf kendi yedekleme yazılımı lisansını ve sıkıştırma/tekilleştirme oranını ekler. On-prem nesne depolama ve S3 fiyat fonksiyonu iki tarafta ortak olabilir; bu, Adım 6'daki ortak modülün doğal bir parçasıdır.

## 9. Yıllık Simülasyon, Fiyatlama Stratejileri ve 5 Yıllık NPV

### 9.1. Yaklaşımın Gerekçesi

Statik tek-nokta sorgusu "şu anda şu yük için ne lazım" sorusunu cevaplar; ama gerçek bir kurumun maliyetini belirleyen şey yılın saatleri arasında değişen trafik desenidir. Tek bir ortalama TPS sayısı R4HA peak'i ve dolayısıyla yazılım faturasını gizler. Bir saatlik patlama tüm ayın yazılım faturasını yukarı çekebilir.

Ayrıca mainframe'in en karakteristik özelliklerinden biri Capacity on Demand'dir (CoD): peak günlerde geçici kapasite ekleme. Bu özellik, mainframe ekonomisini düşünüldüğünden çok daha esnek yapar — ve modelde temsil edilmezse mainframe haksız yere pahalı görünür.

### 9.2. Workload Profile Üretimi

8.760 saatlik deterministik TPS vektörü üretilir. Üç katmanlı desen:
- Günlük desen: sabah-öğlen peak (~14:00), gece dip (~03:00) — sinüs dalgası
- Haftalık desen: iş günleri 1.0×, hafta sonu 0.65×
- Yıllık peak günleri: yıla eşit aralıklarla dağıtılır; peak günlerinin çarpanı m, profilin tepe/ortalama oranı tam olarak peak_avg_ratio olacak şekilde kapalı formdan çözülür: tepe = max(b) × m ve ortalama = (S_normal + m × S_peak) / 8.760 olduğundan m = r × S_normal / (8.760 × max(b) − r × S_peak).

Günlük ve haftalık desenin kendi tepe/ortalama oranı ~1,67'dir. İstenen oran bunun altındaysa (steady_oltp, 1,5×) peak günleri etkisiz kalır ve oran, dalgalanmanın genliği küçültülerek (ikiye bölme ile) tam olarak tutturulur. Peak günü olmadan ulaşılamayan bir oran (örneğin 5× ve 0 gün) hata verir. Önceki sürümde peak çarpanı doğrudan oran olarak uygulanıyordu ve gerçekleşen oran istenenden sapıyordu ; denetimde düzeltildi. Üç preset artık oranı tam olarak verir (1,50 / 3,50 / 2,50).

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

CoD günlük = (aktif kademe PCI − base PCI) × (PCI başına aylık donanım maliyeti / (730 / 24)) × COD_DAILY_MULTIPLIER

PCI başına aylık donanım maliyeti yalnızca kapasiteyle değişen kısmı içerir (PCI × $200'ün amortismanı ve bakımı); frame tabanı geçici kapasiteyle değişmediği için girmez. Ay 730 saat kabul edildiği için gün 730/24 ≈ 30,4'e bölünür (önceki sürümde 30).

COD_DAILY_MULTIPLIER = 2,5 [ASSUME]. IBM gün başına fiyat yayımlamaz; çarpan, CoD'nin primli olması ama sürekli kapasiteden ucuz kalması mantığına dayanır. Yazılım: aylık R4HA (o ayın en büyük aktif kademesiyle sınırlı). zIIP motorları yılın en büyük aktif kademesine (CoD veya corridor tavanı) göre kalıcı olarak kurulur, çünkü geçici GP kapasitesindeki işin de f payı zIIP'e kayar; ek motorların bedeli donanıma eklenir. Önceki sürüm zIIP'i yalnızca base kademeye göre boyutluyordu ve geçici günlerdeki zIIP ihtiyacını bedelsiz sayıyordu; denetimde düzeltildi.

**Strateji C — Tailored Fit Pricing (base + corridor + CoD).** Base kademe satın alınır; corridor tavanı, base MSU × (1 + CORRIDOR_FRACTION) değerini karşılayan en küçük izinli kademedir ve yıl boyunca aktiftir. Corridor'u aşan günlerde On/Off CoD (corridor tavanının üstü için) devreye girer.

Corridor ücreti (saatlik) = max(0, min(tüketilen PCI, corridor PCI) − base PCI) × (PCI başına aylık donanım maliyeti / 730) × CORRIDOR_PREMIUM

Tüketilen GP PCI, yükün %100 kullanım eşdeğeridir (yük × w × (1 − f) / TPS_PER_PCI). Bu, IBM'in "base'in üstünde tüketilen MSU" ölçüsünün modeldeki karşılığıdır: base'in %90 operasyonel tavanı ile %100'ü arasındaki kullanım corridor kapasitesini aktif tutar ama base tüketimini aşmadığı için ücretlendirilmez. İsteğe bağlı sabit abonelik bedeli CORRIDOR_SUBSCRIPTION_RATE ile eklenebilir (varsayılan 0).

Yazılım (Software Consumption Solution) [TFP-SW]: R4HA yerine yıl boyunca tüketilen MSU-saat × efektif MSU-saat fiyatı. IBM efektif fiyatı müşterinin geçmiş 12 ayından belirler; model bunu gelir-nötr olarak kalibre eder: aynı profilin Permanent konfigürasyondaki R4HA faturası, aynı yılın tüketilen MSU-saatine bölünür. TFP_SW_DISCOUNT (varsayılan 0) bu fiyata uygulanan indirimdir. Gelir-nötr kalibrasyon nedeniyle TFP-SW'nin asıl avantajı (büyüme MSU'larının indirimli fiyatı, tepe cezası olmaması) tek yıllık ufukta görünmez; 5 yıllık ufukta büyüme fiyatıyla modellenir (Bölüm 9.10.7).

**Strateji seçimi.** Her availability-feasible topoloji için Strateji A'nın kademesi bulunur; ardından ortalama yükün en az 1,2 katını taşıyan [ASSUME] ve izinli en büyük geçici kademesi peak'i karşılayabilen her base kademe için B ve C simüle edilir. Her strateji için en ucuz sonuç tutulur ve üçü karşılaştırılır. Çok-frame topolojilerde geçici kapasite ücretleri birincil frame için hesaplanır; DR frame'i yalnızca failover içindir ve felaketteki kapasitesi CBU kaydıdır (Bölüm 6.7).

### 9.7. Doğrulama Örneği

10K TPS ortalama yük, oltp_rw profili, availability 0,999 (M1), 20 TB veri, varsayılan parametreler. Toplamlara storage (her presette 1× DS8910F-993, yıllık ~$90K), yedekleme (on-prem nesne depolama, 2 site × 187 TB, yıllık ~$69K) ve mid senaryo personel dahildir. Personel tepe yükü taşıyan kademeye göre hesaplanır ve üç stratejide aynıdır: steady $6,61M, retail $11,95M, batch $9,40M. Referans nokta 50K'dan 10K TPS'e indirildi: gerçekçi işlem tanımıyla 50K ortalama, retail_bursty'nin 3,5× tepesinde (175K) tek z16'nın tavanına (~187K) dayanıyor ve stratejiler arası farkı bu tavan belirliyordu.

| Preset | A: Permanent | B: Base + CoD | C: TFP | Kazanan, A'ya göre |
|---|---|---|---|---|
| steady_oltp | $13,006M (3931-526) | $13,033M (525 → 526, 261 gün CoD) | **$12,816M** (520 + corridor 526) | C, −%1,5 |
| retail_bursty | $22,473M (3931-726) | **$21,382M** (711 → 726, 20 gün) | $21,446M (711 + corridor 714 → 726) | B, −%4,9 (C ile fark %0,3) |
| batch_heavy | $17,915M (3931-717) | $17,387M (616 → 717, 30 gün) | **$17,295M** (612 + corridor 616 → 717) | C, −%3,5 (B ile fark %0,5) |

Denetimden sonra sayılar değişti, çünkü üç düzeltme yıllık modu doğrudan etkiliyor: profil artık istenen tepe/ortalama oranını tam veriyor (steady_oltp'nin tepesi 15.000 TPS), donanıma frame tabanı eklendi ve zIIP motorları geçici kapasiteye göre boyutlanıyor. Kazanan strateji her presette aynı kaldı. Yedekleme katmanı (Bölüm 8.10) her stratejiye aynı tutarı (10K ortalama TPS, 20 TB'ta yılda ~$69K; yalnızca TS7770 ile ~$141K) ekler; sıralamayı değiştirmez.

Yorum:

- **Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanıdır.** steady_oltp'de günlük tepe base'i neredeyse her gün aşar; B bunu 261 gün CoD ile karşılamak zorunda kalır ve A'dan pahalıya gelir, C ise bu tepeleri tüketim bazlı corridor'la ucuza emer. retail_bursty'de maliyeti 20 günlük büyük tepeler belirler; B ve C birbirine yakındır ve kazanan corridor fiyat varsayımlarına göre değişir (Bölüm 9.8).
- **%100 kuralı bağlayıcıdır.** Geçici kapasite, satın alınan MSU'nun en fazla iki katına çıkabilir. Bu yüzden tepe kademesi base'in alt sınırını belirler (örn. retail_bursty'de 3931-726'ya, 4.783 MSU, geçici olarak çıkabilmek için base en az 2.392 MSU olmalı; seçilen 3931-711 2.442 MSU'dur). Sınır uygulanmadığında model resmî kurala göre ulaşılamayan konfigürasyonlar seçiyordu.
- **Personel yıllık toplamın %51–56'sı, yazılım %36–39'udur.** Donanım fiyatlama stratejisi (A/B/C) yalnızca kalan ~%10'u yeniden dağıtır. Bu yüzden stratejiler arası fark küçüktür (%1,5–4,9); doğrusal $40/MSU'lu önceki sürümde %10–24'tü. Strateji seçimini asıl belirleyen, TFP-SW'nin yazılım faturasına getirdiği indirimdir (Bölüm 9.8).
- TFP'nin yazılım kalemi retail_bursty'de Permanent'ten %1,2, batch_heavy'de %1,7 yüksek çıkar (steady_oltp'de eşit). Gelir-nötr kalibrasyon referans kademenin MSU/PCI oranını kullanır; TFP'de base ve corridor kademelerinin oranı biraz farklıdır. Bu bir model artefaktıdır ve sıralamayı yalnızca B ile C'nin birbirine yakın olduğu durumlarda etkiler.

### 9.8. Duyarlılık Analizi (Fiyatlama Varsayımları)

`python src/tools/pricing_sensitivity.py` kalibre edilmemiş fiyat parametrelerini tek tek tarar (10K ortalama TPS, oltp_rw, M1, 20 TB; storage, yedekleme ve mid personel dahil). Yıllık toplamlar, milyon USD; kazanan kalın. Varsayılanlarla değerler Bölüm 9.7'deki tablodur.

| Parametre (varsayılan) | Değer | steady_oltp A / B / C | retail_bursty A / B / C | batch_heavy A / B / C |
|---|---|---|---|---|
| CORRIDOR_PREMIUM (1,5) | 1,0 | 13,006 / 13,033 / **12,810** | 22,473 / **21,382** / 21,443 | 17,915 / 17,387 / **17,285** |
| | 2,5 | 13,006 / 13,033 / **12,827** | 22,473 / **21,382** / 21,452 | 17,915 / 17,387 / **17,315** |
| | 4,0 | 13,006 / 13,033 / **12,845** | 22,473 / **21,382** / 21,461 | 17,915 / 17,387 / **17,345** |
| CORRIDOR_FRACTION (0,20) | 0,10 | 13,006 / 13,033 / **12,897** | 22,473 / **21,382** / 21,481 | 17,915 / **17,387** / 17,389 |
| | 0,35 | 13,006 / 13,033 / **12,810** | 22,473 / 21,382 / **21,354** | 17,915 / 17,387 / **17,280** |
| | 0,50 | 13,006 / 13,033 / **12,837** | 22,473 / 21,382 / **21,321** | 17,915 / 17,387 / **17,229** |
| CORRIDOR_SUBSCRIPTION_RATE (0) | 0,10 | 13,006 / 13,033 / **12,837** | 22,473 / **21,382** / 21,473 | 17,915 / 17,387 / **17,318** |
| | 0,25 | 13,006 / 13,033 / **12,868** | 22,473 / **21,382** / 21,513 | 17,915 / 17,387 / **17,353** |
| | 0,50 | 13,006 / 13,033 / **12,919** | 22,473 / **21,382** / 21,580 | 17,915 / **17,387** / 17,411 |
| COD_DAILY_MULTIPLIER (2,5) | 1,5 | 13,006 / 13,008 / **12,816** | 22,473 / **21,329** / 21,408 | 17,915 / 17,350 / **17,258** |
| | 4,0 | 13,006 / 13,069 / **12,816** | 22,473 / **21,461** / 21,502 | 17,915 / 17,442 / **17,351** |
| TFP_SW_DISCOUNT (0) | 0,05 | 13,006 / 13,033 / **12,568** | 22,473 / 21,382 / **21,060** | 17,915 / 17,387 / **16,971** |
| | 0,10 | 13,006 / 13,033 / **12,319** | 22,473 / 21,382 / **20,673** | 17,915 / 17,387 / **16,646** |

Sonuç: steady_oltp'de TFP'nin üstünlüğü tüm taranan aralıkta korunur. batch_heavy'de dar corridor (0,10) ya da yüksek corridor aboneliği (0,50) B'yi öne geçirir; iki durumda da fark binde birin altındadır. retail_bursty'de varsayılanlarla B kazanır, ama fark %0,3'tür; geniş corridor (0,35 ve üstü) C'yi öne geçirir. Donanım parametreleri (corridor, CoD) toplamları %1'in altında oynatırken, **TFP_SW_DISCOUNT'un %5'i** C'yi her presette açık ara öne geçirir. Yani yazılım gerçekçi fiyatlandığında strateji kararını donanım değil, IBM ile pazarlıkla belirlenen TFP-SW yazılım fiyatı verir. Gerçek sözleşme fiyatı olmadan "bursty iş yükü için TFP mi CoD mu" sorusuna kesin cevap verilemez ve tezde böyle raporlanmalıdır. Permanent strateji, taranan hiçbir noktada kazanmaz.

### 9.9. Grafik-Hazır CSV Çıktısı

İki dosya üretilir, matplotlib/pandas ile doğrudan kullanılabilir:
- \<prefix\>\_hourly.csv — 8760 satır: hour, load_tps, capacity_tps, utilization, cod_active
- \<prefix\>\_monthly.csv — 12 satır: month, r4ha_peak_tps, software_cost, other_cost

### 9.10. 5 Yıllık Ufuk ve NPV

#### 9.10.1. Gerekçe

Statik ve yıllık mod kararlı durumu ölçer: donanım alımı 5 yıla eşit dağıtılır (amortisman), yük ve fiyatlar sabittir. Bu üç şeyi gizler:

1. **Paranın zaman değeri.** Mainframe donanımı ve storage ilk gün nakit olarak ödenir; personel ve yazılım her yıl ödenir. TCO literatüründe standart yöntem, 3–5 yıllık ufukta nakit akışlarını bir iskonto oranıyla bugüne indirgemektir (Değerlendirme #1, madde 2.6).
2. **Büyüme.** Veri büyümesi girdisi ancak çok yıllık ufukta anlam taşır. TPS büyüdükçe kademe yükselir (MES upgrade), yazılım ve personel artar, storage genişletilir.
3. **Zamana bağlı fiyatlar.** IBM yazılım ve bakım fiyatlarını her yıl yeniden belirler, ücretler ve elektrik artar. TFP-SW'nin asıl avantajı olan büyüme MSU'larının indirimli fiyatı da yalnızca çok yıllık ufukta görünür (Bölüm 9.6).

#### 9.10.2. Formül ve zamanlama

NPV = Σ_y [ capex_y / (1 + r)^(y−1) + opex_y / (1 + r)^y ] − kalan değer / (1 + r)^5

- **capex** yılın başında ödenir: 1. yılda z16 (frame tabanı + PCI × $200 + zIIP, DR frame CBU oranıyla), DS8900F ve yedek donanımı (TS7770 ya da on-prem nesne depolama) alımı; sonraki yıllarda yalnızca yükseltme farkı. S3, hat ve abonelik ücretleri işletme gideridir.
- **opex** yıl sonunda ödenir (tutucu): yazılım, GDPS, personel, z16 bakımı (garanti yılından sonra, kurulu değer üzerinden), storage ve yedek bakımı, enerji; yıllık modda ayrıca CoD ve corridor ücretleri.
- Her opex kalemi kendi artış oranıyla bileşik büyür: yıl y'de × (1 + artış)^(y−1).
- **Kalan değer** varsayılan olarak 0'dır: 5 yıl amortisman süresine eşittir ve mainframe kapasitesinin ikinci el değeri kaynaklanamadı. Sonradan alınan yükseltmelerin kalan defter değerinin bir payı NPV_RESIDUAL_FRACTION ile geri kazanılabilir (duyarlılık).

Üç özet ölçü verilir:

- **NPV:** 5 yılın bugünkü değeri. İki taraf aynı r ve aynı büyümeyle karşılaştırılmalıdır.
- **Yıllık eşdeğer maliyet (EAC):** NPV × r / (1 − (1 + r)^−5).
- **Seviyelendirilmiş maliyet:** NPV / Σ_y [12 × TPS_y / (1 + r)^y], yani TPS-ay başına bugünkü değer. Enerji ekonomisindeki LCOE'nin karşılığıdır ve statik moddaki $/TPS/ay ile doğrudan karşılaştırılabilir. Statik NPV'de TPS_y tasarım tepesi, yıllık NPV'de ortalama yüktür.

#### 9.10.3. Büyüme yolu

- **Yük:** TPS_y = TPS_1 × (1 + g)^(y−1). g, NPV_TPS_GROWTH = 0,10 varsayılanıyla bir senaryo girdisidir (`--tps-growth`); kaynaklı bir sektör ortalaması bulunamadı ve kurumdan kuruma değiştiği için aralık parametresi değil, taranan bir girdidir.
- **Veri:** D_t = D_0 × (1 + büyüme)^t (mevcut `data_growth` girdisi).
- **Topoloji** 1. yılda seçilir ve 5 yıl sabit kalır.
- **Kademe yalnızca yükselebilir.** Kalıcı yükseltmede PCI, CP sayısı ve kapasite seviyesi (4xx < 5xx < 6xx < 7xx) azalamaz (`is_permanent_upgrade`). Her yıl, bir önceki yılın kademesinden izinli yükseltmeler arasında o yılın yükünü taşıyan en ucuz kademe seçilir. Yükseltmenin bedeli satın alma değerleri farkıdır; frame tabanı yeniden ödenmez.
- **Storage ve yedek** STORAGE_PLANNING_YEARS (3) yıllık döngülerle alınır: t = 0'da 3 yıllık, t = 3'te kalan 2 yıllık veriye ve döngüdeki en yüksek yüke göre. İkinci döngünün bedeli kurulu değerin üstündeki farktır.
- **Yıllık modda** her yıl profil (1 + g)^(y−1) ile büyütülür ve strateji yeniden optimize edilir; base kademe yine yalnızca yükselebilir. TFP'de yazılım 1. yılda sözleşmelenir: 1. yılın MSU-saati taban kabul edilir, taban her yıl (tüketilmese de) ödenir, tabanın üstündeki MSU-saat TFP_GROWTH_PRICE_FACTOR ile fiyatlanır [TFP-SW-2021, KYNE-2022].

#### 9.10.4. Parametreler

| Parametre | Değer | Dayanak | Aralık |
|---|---|---|---|
| NPV_DISCOUNT_RATE (r, nominal) | 0,07 | Damodaran, ABD sermaye maliyeti, Ocak 2026: toplam piyasa %6,96; bilgisayar hizmetleri %7,83; yazılım %9,34; bankalar %4,98 [DAMODARAN-2026] | Tarama %5 / %7 / %10 (köşe senaryolarına girmez, aşağıya bakınız) |
| NPV_TPS_GROWTH (g) | 0,10 | Senaryo girdisi | Tarama 0 / 0,05 / 0,10 / 0,20 |
| SW_PRICE_ESCALATION (yazılım, GDPS) | 0,03 | IBM yıllık fiyat uyumlaması: IBM Z yazılımı (MLC, S&S) 2026'da +%6 [IBM-PRICE-2026]. Orta değer uzun dönem enflasyonuna yakın tutuldu; sabit fiyatlı sözleşme 0'dır | 0–0,06 |
| HW_SERVICE_ESCALATION (bakım, CoD, corridor, storage bakımı) | 0,03 | IBM TLS 2025'te +%4–6, 2026'da ortalama +%6 [IBM-PRICE-2026] | 0–0,06 |
| WAGE_ESCALATION | 0,033 | BLS ECI, Haziran 2026: özel sektör toplam ücret maliyeti 12 ayda +%3,3 [BLS-ECI-2026] | 0,025–0,045 |
| ENERGY_ESCALATION | 0,04 | EIA: ABD ticari elektrik 10,59 (2020) → 13,37 cent/kWh (2025), yıllık ~%4,8 [EIA-EPM] | 0,015–0,056 |
| TFP_GROWTH_PRICE_FACTOR | 0,5 | IBM: taban üstü MSU'lar "very aggressive Growth Price" [TFP-SW-2021]; Kyne ve Baker: "IBM mentions 50% discount for growth MSUs" [KYNE-2022] | 0,5–1,0 |
| NPV_RESIDUAL_FRACTION | 0 | [ASSUME] tutucu | 0–1 |

**İskonto oranı neden köşe senaryolarına girmez:** r, belirsiz bir fiyat değil, kurumun sermaye maliyetidir ve iki tarafta aynı olmalıdır. Köşe senaryolarına (hepsi aynı yönde) katılsaydı, yüksek r mainframe'i hep ucuz göstereceği için "low = mainframe lehine" tanımını anlamsızlaştırırdı. Bu yüzden ayrı bir tarama olarak verilir. Artış oranları ise belirsiz fiyatlardır ve aralık çıktısına (NPV_RANGE_PARAMETERS: 20 statik + 5 NPV parametresi) dahildir.

#### 9.10.5. Tutarlılık kontrolü

r = 0, TPS ve veri büyümesi 0, bütün artışlar 0 iken NPV, statik aylık toplamın tam 60 katına eşittir (fark 10⁻¹⁶). Yıllık modda aynı koşulda her stratejinin NPV'si, o stratejinin yıllık toplamının 5 katına eşittir. Bu iki eşitlik testlerle güvencelenir (`test_npv_consistency_and_direction`) ve nakit akışı modelinin amortismanlı modelle aynı maliyet tabanını kullandığını gösterir: aradaki bütün fark zamanlama, büyüme ve fiyat artışından gelir.

#### 9.10.6. Sonuçlar: statik NPV

`python src/mainframe_model.py --tps 10000 --npv` (oltp_rw, %99,9, 20 TB, g = %10, r = %7):

| Yıl | TPS | Kademe | Capex | Opex | Bugünkü değer |
|---|---|---|---|---|---|
| 1 | 10.000 | 3931-516 | $3.397.311 | $9.127.534 | $11.927.717 |
| 2 | 11.000 | 3931-518 | $233.600 | $10.450.209 | $9.345.935 |
| 3 | 12.100 | 3931-520 | $232.400 | $11.381.266 | $9.493.490 |
| 4 | 13.310 | 3931-523 | $425.674 | $12.571.663 | $9.938.339 |
| 5 | 14.641 | 3931-525 | $229.600 | $13.626.729 | $9.890.830 |

NPV $50,60M (indirgenmemiş $61,68M, yıllık eşdeğer $12,34M); seviyelendirilmiş maliyet $85,31/TPS/ay. 4. yıldaki capex'in yaklaşık yarısı ikinci storage ve yedek döngüsüdür. Kalem dökümü (bugünkü değer): personel %49,1, yazılım %38,4, donanım alımı %7,6, z16 bakımı %3,0, storage alımı %0,7, storage ve yedek bakımı %0,4, enerji %0,3, yedekleme alımı (on-prem nesne depolama) %0,3, yedek aboneliği %0,2.

İskonto oranı × TPS büyümesi (`npv_sensitivity.py`, bölüm 3; NPV milyon USD, parantezde $/TPS/ay):

| TPS büyümesi | r = %5 | r = %7 | r = %10 |
|---|---|---|---|
| 0 | 47,02 (90,51) | 44,65 (90,75) | 41,45 (91,12) |
| %5 | 50,05 (87,58) | 47,47 (87,87) | 43,99 (88,32) |
| %10 | 53,41 (84,98) | 50,60 (85,31) | 46,81 (85,82) |
| %20 | 60,90 (80,16) | 57,56 (80,55) | 53,08 (81,16) |

Fiyat artışları tek tek (diğerleri varsayılan): yazılım artışı 0 / %3 / %6 → NPV −%2,2 / 0 / +%2,3; ücret artışı %2,5 / %3,3 / %4,5 → −%0,8 / 0 / +%1,2; bakım artışı → ±%0,3; enerji artışı → etkisiz; kalan değer payı 0,5 / 1,0 → −%0,4 / −%0,8.

Aralık (`--npv --range`; NPV_RANGE_PARAMETERS köşeleri, $/TPS/ay seviyelendirilmiş):

| TPS (1. yıl) | low | mid | high | NPV (milyon USD) low / mid / high |
|---|---|---|---|---|
| 1.000 | 83,88 | 219,62 | 689,65 | 5,0 / 13,0 / 40,9 |
| 10.000 | 31,98 | 85,31 | 405,44 | 19,0 / 50,6 / 240,5 |
| 50.000 | 13,93 | 51,01 | 303,73 | 41,3 / 151,3 / 900,7 |

Tornado'nun başı statik moddakiyle aynıdır (10K TPS, NPV milyon USD): personel 36,2–80,5; okuma SQL CPU 42,1–70,3; AWLC seviyesi 40,9–65,2; yazma SQL CPU 45,9–61,5; zIIP payı 45,5–54,1. Fiyat artışlarının en etkilisi (yazılım) 9. sıradadır (49,5–51,8).

Yorum:

- **Kararlı durum ölçüsü 5 yıllık sonuca yakındır.** 10K TPS'te seviyelendirilmiş maliyet ($85,31) statik $/TPS/ay'dan ($84,62) yalnızca %0,8 farklıdır. İki etki birbirini neredeyse götürür: fiyat artışları maliyeti yükseltir (büyüme 0'da seviyelendirilmiş maliyet $90,75, statikten %7 yüksek), büyüme ise ölçek ekonomisiyle düşürür (MSU başına azalan yazılım fiyatı, alt-doğrusal personel). Bu, önceki bölümlerdeki statik sonuçların 5 yıllık bir kararın da iyi bir yaklaşığı olduğunu gösterir.
- **İskonto oranı NPV'yi belirgin, seviyelendirilmiş maliyeti az değiştirir.** r = %5'ten %10'a NPV %12 düşer, ama hem maliyetler hem talep indirgendiği için $/TPS/ay yalnızca %1 oynar. Mainframe tarafında capex payı küçük olduğundan (~%8) r'nin etkisi sınırlıdır. Clustered taraf daha capex ağırlıklıysa, r'nin iki tarafı farklı etkilemesi beklenir; crossover r'ye bu yolla duyarlı olabilir.
- **Büyüme mainframe lehine çalışır.** %20 büyümede seviyelendirilmiş maliyet %0 büyümeye göre %11 düşer. Bu, bükülen maliyet eğrisinin (Bölüm 7.6) zaman boyutundaki karşılığıdır.
- **Belirsizliğin kaynakları değişmez.** Fiyat artışları aralığa eklendiğinde de en büyük sürücüler personel, işlem başına CPU ve AWLC seviyesidir. Artış oranlarının toplam etkisi bunların yanında küçüktür.

#### 9.10.7. Sonuçlar: fiyatlama stratejileri 5 yılda

`python src/mainframe_model.py --yearly --preset <preset> --npv` (10K ortalama TPS, g = %10, r = %7; NPV milyon USD, kazanan kalın):

| Preset | A: Permanent | B: Base + CoD | C: TFP | Kazananın base yolu |
|---|---|---|---|---|
| steady_oltp | 68,994 | 67,710 | **65,461** | 520 → 523 → 525 → 532 → 532 |
| retail_bursty | 115,138 | 112,752 | **112,083** | 711 → 712 → 714 → 716 → 740 |
| batch_heavy | 91,845 | 87,924 | **86,798** | 612 → 614 → 616 → 619 → 620 |

Duyarlılık (`npv_sensitivity.py`, bölüm 4):

| Durum | steady_oltp | retail_bursty | batch_heavy |
|---|---|---|---|
| Varsayılan | C (B'den %3,3 ucuz) | C (%0,6) | C (%1,3) |
| TFP büyüme fiyatı 1,0 (indirim yok) | C 67,603 / B 67,710 | **B** 112,752 / C 115,461 | **B** 87,924 / C 89,663 |
| TPS büyümesi 0 | C 56,289 | **B** 93,749 / C 94,027 | C 75,810 |

Yorum:

- **TFP'nin 5 yıllık avantajı büyüme fiyatından gelir.** Tek yılda retail_bursty'de B kazanıyordu (Bölüm 9.7). Büyüme olduğunda TFP üç presette de kazanır; büyüme MSU'larının indirimi kaldırıldığında ya da yük büyümediğinde retail_bursty'de (ve indirimsiz durumda batch_heavy'de) yeniden B öne geçer. Yani "TFP mi, CoD mi" sorusunun cevabı tepe yapısından çok büyüme beklentisine ve IBM'in büyüme fiyatına bağlıdır. Büyüme fiyatı sözleşmeye özel olduğu için bu sonuç koşullu raporlanmalıdır.
- **Permanent, 5 yılda da hiçbir presette kazanmaz.**
- **Drawer sınırı yükseltme yolunu kırar.** retail_bursty'de 5. yılın tepesi (~51K TPS), Max39 drawer özelliği üzerindeki geçici kapasitenin taşıyabileceğini aşar. Geçici kapasite drawer ekleyemediği için (Bölüm 9.5) base 716'dan 740'a sıçrar ve 5. yılda ~$6,5M capex oluşur. Gerçekte kurum daha büyük drawer özelliğini önceden kurar; drawer maliyeti modelde olmadığı için bu seçenek değerlendirilemiyor (Bölüm 12.2).

#### 9.10.8. Geçerlilik tehditleri ve sınırlamalar

- **Açgözlü yol:** Kademe her yıl, o yılın yüküne göre en ucuz izinli yükseltme olarak seçilir. İleriye bakan bir optimizasyon (örneğin 1. yılda biraz büyük kurup yükseltmeden kaçınmak) yapılmaz; sonuç bir üst sınırdır.
- **Teknoloji yenileme yok:** 5 yıl içinde z17'ye geçiş, yeni nesil fiyat/performansı ve göç maliyeti modellenmez. Yükseltme kapasitesinin PCI fiyatı nominal olarak sabittir.
- **Zamanlama basitleştirmesi:** opex yıl sonunda, capex yıl başında. Aylık ödemeler için yıl ortası konvansiyonu NPV'yi biraz yükseltir.
- **TFP sözleşmesi basitleştirildi:** taban 1. yılın MSU-saatidir; kullanılmayan MSU'ların sonraki yıla devri ve IBM'in taban fiyatı belirleme yöntemi (geçmiş 12 ayın MLC'si artı fiyat artışları) yaklaşık temsil edilir.
- **Storage döngüleri sabittir** (t = 0 ve 3); dizi modeli değiştiğinde (DS8910F → DS8950F) ek alım, kurulu değerin üstündeki fark olarak yaklaşık hesaplanır.
- **Clustered tarafla eşleştirme:** aynı r, g, veri büyümesi, ufuk ve zamanlama kuralları kullanılmalıdır. Clustered taraf kendi donanım yenileme döngüsünü (genellikle 3–5 yıl), lisans ve abonelik artışlarını ekler.

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
  src/tools/range_curve.py             maliyet/TPS eğrisinin low/mid/high aralığı + CSV (data/out/)
  src/tools/availability_sensitivity.py  olay tabanlı availability, hedef → topoloji → maliyet, RPO/RTO
  src/tools/npv_sensitivity.py       yedekleme (üç hedef, kısıtlar) ve 5 yıllık NPV duyarlılık tabloları (--fast: yıllık stratejiler hariç)
  data/raw/redp5320_workload_profile.csv  REDP-5320 benchmark işlem profili (kaynaklı)
  data/ds8900f_models.csv              DS8900F model kataloğu (kaynaklar dosya başlığında)
```

### 10.1. Statik Mod

python src/mainframe_model.py --tps 10000 --availability 0.999 --workload oltp_rw --latency-ms 200 --data-tb 20 --data-growth 0.15

Özel işlem bileşimi: `--sql-reads 6 --sql-writes 2` (w ve I/O bileşimden hesaplanır). Aralık çıktısı: `--range` (low/mid/high toplam ve tek-parametre salınımı, Bölüm 7.8). Felaket kurtarma hedefleri: `--rpo-seconds 0 --rto-minutes 60` (Bölüm 6.6). Yedek hedefini zorlamak: `--backup-target ts7770 | cos_onprem | aws_s3` (Bölüm 8.10). 5 yıllık NPV: `--npv` (isteğe bağlı `--tps-growth 0.10 --discount-rate 0.07 --years 5`); `--npv --range` NPV aralığını ve tornado'yu verir (Bölüm 9.10).

### 10.2. Yıllık Mod

python src/mainframe_model.py --yearly --preset retail_bursty --avg-tps 10000 --availability 0.999 --csv out

`--yearly --npv` üç stratejinin her birini 5 yıl boyunca çözer ve en düşük NPV'liyi kazanan olarak yazar (Bölüm 9.10.7).

### 10.3. Yardımcı Modlar

- --demo: hazır 7 senaryo ([G]: RPO ≤ 5 sn, RTO ≤ 60 dk)
- --calibration: kademe tablosu özeti, köprü katsayıları ve örnek kademeler

### 10.4. Testler

python src/test_mainframe_model.py — 23 test: latency monotonluğu, latency'nin sıkı hedefte bağlayıcı olması, kademe tablosunun bütünlüğü (317 satır, seri başına kesin artan PCI ve MSU), köprünün kendi z13 çapalarını %2 içinde ve 7K0 PCI'sini %0,5 içinde üretmesi, MSU faturasının kurulu kapasiteyle sınırlı olması, geçici kapasitenin (B veya C) avantajının burstiness ile artması, geçici hedeflerin SC28-7025 kurallarına uyması (%100, drawer, alt-kapasite; 735 → 739 ve 705 örnekleri), seçilen B/C konfigürasyonlarının bu kurallara uyması, TFP-SW fiyatının gelir-nötr olması ve corridor ücretinin CORRIDOR_PREMIUM ile artması, storage boyutlandırmasının (topolojiden kopya sayısı, IOPS'tan model, veri hacminden kapasite) ve zHyperLink / senkron replikasyonun D_io'ya etkisinin beklenen yönde olması. Ayrıca AWLC yazılım fonksiyonunun IBM örnek faturasını (265 MSU) ve Db2 referans eğrisini yeniden üretmesi, toplamın artan ama MSU başına fiyatın azalan olması, maliyet/TPS'in 5K → 500K TPS arasında en az 3 kat düşmesi, zIIP payı arttıkça faturalanan MSU'nun düşmesi ve zIIP sayısının 2:1 sınırına uyması test edilir. Ayrıca iş yükü profilleri test edilir: REDP profili köprüyü aynen korur (w = 1, zIIP yok); daha ağır bileşim daha yüksek w, I/O ve maliyet verir; özel bileşim beklenen yönde davranır. Latency testi üç profilde koşar; infeasible eşiği storage'tan gelen D_io'ya göre hesaplanır. Yıllık testler 10K ortalama TPS'te koşar. Personel ve aralık testi: MIPS/FTE kapasiteyle artar, senaryolar sıralıdır, M4 M1'den fazla FTE ister; solve_range low < mid < high verir, mid statik sonuçla aynıdır, parametreler çağrıdan sonra eski değerine döner ve her tornado ucu dış sınırlar içinde kalır. Availability testi: yıllık kesinti M1 > M2 > M3 > M4, her topolojinin mid değeri kendi aralığının içinde, CPC donanım kesintisi toplamın binde birinden az; RPO 0 → M2, RTO ≤ 60 dk → M3, RPO 0 ve RTO ≤ 60 dk → M3, RTO ≤ 1 dk → M4, RPO 0 ve RTO ≤ 1 dk → infeasible; DR frame oranı 1,0'da donanım iki kat, 0,5'te 1,5 kat; GDPS kapasiteden bağımsız ve M1'de sıfır; topoloji yazılımı değiştirmez.

Denetimde eklenen testler: `solve(verbose=True)` sessiz modla aynı üçlüyü döndürür; üretilen profilin tepe/ortalama oranı istenen değere eşittir ve ulaşılamayan oran hata verir; düz yükte yıllık Permanent toplamı, statik aylık toplamın 12 katıyla binde bir içinde aynıdır (statik ve yıllık mod tutarlı); geçici kapasite kullanan B/C konfigürasyonlarında zIIP bedeli en büyük aktif kademeye göredir; CLI sıfır/negatif TPS ve (0, 1) dışı availability'yi reddeder, SQL'siz özel profil zIIP'e uygun sayılmaz, `use_values` bilinmeyen bir parametre adında hiçbir değeri değiştirmeden hata verir; D_io okuma ve yazma I/O'larını profilin kendi bileşimiyle ağırlıklandırır (senkron I/O'su tamamen yazma olan REDP profilinde senkron replikasyon D_io'ya tam olarak eklenir).

Adım 5'te eklenen testler: `test_backup_layer` (TS7770 zorlanarak): iki site ve site başına en az bir küme; cache 20 TB'ın katı; log hacmi TPS ile, alım bedeli veri hacmiyle, image copy saklama süresiyle artar; sıkıştırma cache'i büyütmez; 2.000 TB'ta küme sayısı günlük verim sınırından gelir (> 1); toplam sekiz kalemin toplamına eşittir. `test_backup_targets_and_constraints`: 5–2.000 TB ve M1/M3'te seçilen hedef feasible adayların en ucuzudur; TS7770 her zaman feasible'dır; nesne hedefleri tam olarak gereken verim TCT tavanını aştığında elenir; M1'de geri yükleme süresi bütçeyi aşmaz; 500 TB'ta nesne hedefleri M1'de elenir, M3'te elenmez; zorlanan infeasible hedef (2.000 TB'ta S3) TS7770'e düşer ve bunu işaretler; S3 hibrit işaretli, capex'siz ve en az bir hatlıdır; on-prem donanımı çok pahalılaşınca seçilmez. Düz yükte yıllık toplamın statik aylık toplamın 12 katı olduğu test yedek kalemini de içerir. `test_npv_consistency_and_direction`: r = 0, büyüme ve artış 0 iken statik NPV statik aylık toplamın 60 katına, yıllık NPV (Permanent ve TFP) yıllık toplamın 5 katına 10⁻⁹ içinde eşittir; yüksek iskonto oranı NPV'yi düşürür; %15 büyümede kademe yolu yalnızca yükselir (`is_permanent_upgrade`) ve son kademe ilkinden büyüktür; yıllık capex negatif değildir; TFP büyüme fiyatı 1,0'a çıkınca TFP'nin NPV'si artar ve TFP base yolu monotondur. CLI testi `--npv`'nin ve `--backup-target aws_s3`'ün çalıştığını, `--years 0`'ın ve bilinmeyen yedek hedefinin reddedildiğini doğrular.

Bazı testler tasarım gereği tautolojiktir: örneğin kademe tablosunun kendi çapalarını yeniden üretmesi, tablonun bu çapalardan üretildiğini doğrular, bağımsız bir doğrulama değildir. Testler modelin iç tutarlılığını (yön, sınır, kural uyumu) güvence altına alır; dış geçerlilik kaynak karşılaştırmalarıyla (Bölüm 7.1.4, 7.8 Gartner kontrolü) sağlanır.

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

### 11.2. Availability ve Felaket Kurtarma

- **[SG24-8446] —** IBM Redbooks SG24-8446, "Getting Started with IBM Z Resiliency" (güncel baskı). Dört desen (Reliable base, Failover capable, Fault tolerant, Adaptive continuity) ve genel RTO/RPO aralıkları: HA'da RTO dakikalar–birkaç saat, RPO 0; DR'de RTO 2–72 saat, 2 saatin altı GDPS otomasyonu ve test edilmiş süreç ister. Desen başına availability yüzdesi vermez. M1–M4 eşlemesinin ve M1/M2 kurtarma sürelerinin kaynağı. https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf
- **[SG24-6374] —** IBM Redbooks SG24-6374, "IBM GDPS: An Introduction to Concepts and Capabilities", Tablo 1-1: depolama replikasyonlu uzak sitede RPO "sıfırdan dakikalara", RTO "bir veya daha fazla saat"; yalnızca senkron replikasyon RPO 0 verir. https://www.redbooks.ibm.com/redbooks/pdfs/sg246374.pdf
- **[GDPS-2026] —** S. Cook (IBM GDPS Development), "GDPS Overview: Availability, Disaster Recovery, and Cyber Resiliency for z/OS, z/VM, and Linux on Z", VM Workshop, Haziran 2026: GDPS Metro RPO 0, RTO ~2 dk (çok-siteli iş yükü) / < 1 saat (tek siteli); GDPS Global ve Metro Global RPO "2 saniyeye kadar düşük", RTO < 1 saat; GDPS CA RPO 0–5 sn, RTO 20–30 sn (portföy slaytında < 60 sn). Üretici kaynağı. https://vmworkshop.org/2026/present/gdpsover.pdf
- **[GDPS-CA-2021] —** IBM, "GDPS Continuous Availability" sunumu (2021, New Era aracılığıyla): iş yükü geçişi < 30 sn; bir bankada planlı kesinti 4 saatten 30 saniyenin altına. https://www.newera.com/INFO/GDPS-CA.pdf
- **[CBU] —** IBM SC28-7025, "IBM Z and LinuxONE Capacity on Demand User's Guide", CBU bölümü: LICCC ile etkinleşen, önceden kurulu donanım gerektiren yedek kapasite; yıl başına bir ücretsiz 10 günlük test (en fazla 15), tek 90 günlük gerçek aktivasyon, 1–5 yıllık kayıt; "Software charges for the designated CBU machine are based on its permanent configuration." Fiyat yayımlanmaz. SHARE 2012 oturumu 10869 (IBM): CBU "priced for H/W, no IBM S/W charges". https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf
- **[GDPS-PRICE] —** Mainframe Licensing Experts (bağımsız alıcı tarafı danışmanlık), GDPS ürün ve yenileme sayfaları: GDPS lisanslı otomasyon kodu ile IBM hizmetlerinin birleşimi; fiyat otomatikleştirilen sistem, sysplex ve site kapsamına bağlı, MSU'ya değil. Rakam vermez; yalnızca fiyatlama yapısının dayanağı. https://mainframelicensingexperts.pages.dev/products/ibm/gdps/
- **[UPTIME-2025] —** Uptime Institute, Annual Outage Analysis 2025 (basın bülteni ve Data Center Knowledge haberi): operatörlerin %53'ü son üç yılda kesinti bildirdi (2020'de %78); 2024'te olayların %9'u ciddi/ağır; etkili kesintilerin %54'ü güç kaynaklı, %23'ü BT/ağ; insan hatası tüm kesintilerin üçte ikisi–dörtte üçünde rol oynar. https://www.datacenterknowledge.com/outages/data-center-outages-decline-for-fourth-straight-year-but-issues-persist
- **[UPTIME-2022] —** Uptime Institute, Annual Outage Analysis 2022 (Data Center Frontier haberi): kamuya yansıyan kesintilerin 24 saatten uzun süren payı 2017'de %8, 2021'de ~%30. https://www.datacenterfrontier.com/uptime-longer-data-center-outages-are-becoming-more-common
- **[ITIC-2023] —** ITIC 2023 Global Server Hardware, Server OS Reliability Survey (~1.900 kurum): 200+ z16 kullanıcısının %96'sı 9 nine (sunucu başına yılda 31,56 ms plansız kesinti, sunucu donanımının kendi arızaları); z13–z15 ortalaması 7–8 nine; IBM'e göre IBM Z ortalaması 8 nine. Yalnızca D_cpc terimi için. https://itic-corp.com/?p=3107
- **[ITIC-2024] —** ITIC 2024 anketi (TechChannel haberi): z16 9 nine; Lenovo ThinkSystem'in güncel x86 sunucuları 8 nine (yılda 315 ms). Sunucu güvenilirliğinin iki platformda da hizmet availability'sinin belirleyicisi olmadığının dayanağı. https://techchannel.com/industry-news/server-reliability-survey-2024/
- **[PRECISELY] —** Precisely, High Availability tanımı: toplam kesintinin büyük kısmı (~%90) planlıdır. Artık çarpan olarak kullanılmıyor; yalnızca olay tabanlı sonucun yön kontrolü. https://www.precisely.com/glossary/high-availability-ha/

### 11.3. CoD ve Yıllık Simülasyon
- **\[COD\] —** IBM SC28-7025, "IBM Z and LinuxONE Capacity on Demand User's Guide". On/Off CoD'nin teknik yapısı (gün-bazlı faturalandırma, 24-saatlik aktivasyon periyodu, prepaid/postpaid modelleri) ve geçici kapasite sınırları (satın alınan kapasitenin %100'ü, kurulu kapasite, alt-kapasite seviye kuralları). Gün başına dolar fiyatı kapalı, premium çarpanı 2.5 \[ASSUME\]. https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf
- **\[CFCC\] —** IBM Coupling Facility Configuration Options (Raften), IBM Z Resiliency Redbook ve ilgili IBM dokümanları. ICF (Internal Coupling Facility) specialty engine olduğu için kapasite derecelendirmesini etkilemez ve yazılım lisansını artırmaz. Ek frame'in yazılım lisansını artırmamasının gerekçelerinden biridir (diğeri [CBU]).

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

### 11.5. Yedekleme (TS7770, nesne depolama, AWS S3)

- **[TS7700-2024] —** IBM, "IBM TS7700 Tape Solution Overview" (03/2024) ve IBM Documentation, TS7700 5.4.1 "TS7700 server"; IBM TS7770 cache controller sayfası. TS7770'in yapısı (Power9 sunucu, disk-only veya teyp bağlı), cache'in 20 TB / 100 TB adımlarla Capacity on Demand ile açılması, taban + iki genişleme çerçevesiyle ~3,9 PB üst sınır, küme başına ~4.000 MB/s host verimi, nominal 3:1 sıkıştırma, grid replikasyonu (en fazla 8 küme). https://www.ibm.com/docs/en/ts7700-virtual-tape/5.4.1?topic=components-ts7700-server ; IBM TS7700 R5.3/R5.4 performance white paper'ları (https://www.ibm.com/support/pages/ibm-ts7700-r54-performance).
- **[TS7700-2006] —** Enterprise Storage Forum, "Big Blue Takes Tape to the Next Level" (21.09.2006): TS7700'ün başlangıç fiyatı $493.080. Yayımlanmış tek TS7700 fiyatıdır; küme tabanı olarak nominal değeriyle kullanılır. https://www.enterprisestorageforum.com/backup/big-blue-takes-tape-to-the-next-level/
- **[DB2-BACKUP] —** IBM Db2 12 for z/OS Documentation, "Actions to take to prepare for backup and recovery": image copy'lerin ve arşiv logların ikişer kopyası, kopyalardan birinin site dışında tutulması. https://www.ibm.com/docs/SSEPEK_12.0.0/admin/src/tpc/db2z_actionstakebackupdata.html
- **[IDUG-2024] —** A. Hendley, Planet Mainframe (15.11.2024), A. Svoboda'nın IDUG EMEA oturumunun aktarımı: tam image copy tipik olarak haftada bir, arada artımlı kopya; haftalık değişim %10'u aşan nesnelerde tam kopya önerilir. Uygulayıcı kaynağı; sıklık varsayımının dayanağı.
- **[SG24-8381] —** IBM Redbooks SG24-8381, "IBM DS8000 Transparent Cloud Tiering (DS8000 Release 9.3)": TCT ile DFSMShsm göçü, DFSMShsm tam hacim dökümü ve DFSMSdss veri seti/hacim döküm ve geri yüklemesinin nesne depolamaya taşınması; hedefler OpenStack Swift, IBM Cloud Object Storage (kamu veya kurum içi), Amazon S3 ve nesne hedefi olarak TS7700; en fazla sekiz bulut hedefi; veri DS8000 sunucularının Ethernet portlarından geçer (sunucu başına iki 1 GbE, ek kartlarla 10 GbE, en fazla altı port); TS7700 dışındaki hedeflerde DS8000 sıkıştırma yapmaz; teybe yazılmış veri doğrudan taşınamaz. Verim değeri vermez. https://www.redbooks.ibm.com/redbooks/pdfs/sg248381.pdf
- **[AWS-S3-2026] —** AWS S3 liste fiyatları, us-east-1 (Nubbo, "AWS S3 pricing in 2026" derlemesi üzerinden; ikincil aktarım): Standard $0,023, Standard-IA $0,0125 (en kısa süre 30 gün), Glacier Instant Retrieval $0,004 /GB-ay; Standard-IA PUT $0,01 / 1.000, geri getirme $0,01/GB; veri girişi ücretsiz. https://nubbo.app/blog/aws-s3-pricing-2026
- **[AWS-DX-2026] —** AWS Direct Connect, pay-as-you-go fiyatları: dedicated port 1 Gbps $0,30, 10 Gbps $2,25, 100 Gbps $22,50 /saat; ABD içi DX çıkış $0,02/GB; giriş ücretsiz. https://aws.amazon.com/directconnect/pricing/pay-as-you-go/
- **[MINIO-TCO] —** MinIO, "The Long Term Costs of Object Storage in the Public Cloud" (tarihsiz blog): 1 PB için 60 × 16 TB HDD'li 2U sistem $70K (0,72 PB kullanılabilir, 36 ay amortisman), MinIO Standard abonelik $0,01/GB-ay; S3 fiyatlarının dört yıldır değişmediği gözlemi. Üretici kaynağı; yalnızca aralık olarak kullanılır. https://blog.min.io/the-long-term-costs-of-storage-in-the-cloud

### 11.6. 5 Yıllık Ufuk ve NPV

- **[DAMODARAN-2026] —** A. Damodaran, "Cost of Capital by Sector (US)", Ocak 2026: toplam piyasa %6,96; bilgisayar hizmetleri %7,83; yazılım %9,34; bankalar %4,98. NPV_DISCOUNT_RATE = 0,07 ve %5–%10 taramasının kaynağı. https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html
- **[IBM-PRICE-2026] —** IBM yıllık fiyat uyumlamaları, bayi ve danışman özetleri (Schneider IT Management, "IBM price increases 2025/2026"; Insight, "Decoding IBM's software price surge", 2024): IBM Z yazılımı (MLC, S&S) 2026'da yaklaşık +%6; donanım bakımı (TLS) 2025'te +%4–6. SW ve HW servis artışlarının (orta %3, aralık 0–%6) dayanağı; orta değer, liste artışının sözleşmeli müşterilere tam yansımadığı varsayımıyla düşük tutuldu. https://www.schneider.im/lu/ibm-price-increases-2026/
- **[BLS-ECI-2026] —** BLS, Employment Cost Index, Haziran 2026 (31.07.2026 bülteni): özel sektör toplam ücret maliyeti 12 ayda +%3,3. WAGE_ESCALATION'ın kaynağı. https://www.bls.gov/news.release/archives/eci_07312026.htm
- **[EIA-EPM] —** EIA, Electric Power Monthly, Tablo 5.3: ticari elektrik fiyatı 10,59 (2020) → 13,37 cent/kWh (2025), yıllık ~%4,8. ENERGY_ESCALATION aralığının üst ucu. https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_3
- **[TFP-SW-2021] —** IBM, "Tailored Fit Pricing: A sensible pricing model" (05/2021): tabanın üstündeki MSU'lar için "very aggressive Growth Price". Büyüme fiyatının yapısal dayanağı.
- **[KYNE-2022] —** F. Kyne, J. Baker (Watson & Walker), "How Should I Think About Tailored Fit Pricing?" (2022): "IBM mentions 50% discount for growth MSUs"; taban geçmiş 12 ayın MLC'sidir ve kullanılmasa da ödenir. TFP_GROWTH_PRICE_FACTOR = 0,5'in kaynağı. Bağımsız danışman kaynağı. https://tuningletter.planetmainframe.com/wp-content/uploads/presentations/2022-08-102-How-Should-I-Think-About-Tailored-Fit-Pricing.pdf

### 11.7. Maliyet Verileri (Yarı-Kapalı)
- **\[PRICE\] —** Bağımsız mainframe fiyat rehberleri (electronics.alibaba buying guides serisi). z15/z16 donanım fiyat aralığı (\$0.5M-\$10M+), yıllık bakım donanım değerinin %10-15'i, alt ekonomik eşik ~150 MIPS. HARDWARE_COST_PER_MIPS = \$200, HW_FRAME_BASE_COST = \$500K (aralığın giriş ucu) ve MAINTENANCE_RATE_ANNUAL = 0.125 değerlerinin kaynağıdır. Açık liste fiyatı olmadığı için kestirim.
- **[IBM-2004] —** IBM, "Workload License Charges" sunumu, z/VM sayfası (vm.ibm.com, 2005-Z24, 2004 fiyatları). Db2 PSLC/WLC kademe fiyatları (Base $3.960 ilk 3 MSU dahil; 4–45 $208; 46–175 $88; 176–315 $66; 316+ $50 /MSU/ay) ve örnek sub-capacity faturası (z/OS $75.459 @265 MSU, CICS $32.978 @210 MSU, Db2 $31.876 @265 MSU). AWLC kademe düşüş eğrisinin ve ürün katsayılarının kaynağı. 2004 tarihli olduğu için mutlak seviye SW_PRICE_LEVEL_FACTOR ile taranır.
- **[IBM-ZNALC] —** IBM, "z Systems New Application License Charges (zNALC)", ZSL03508-USEN-01. Kademe sınırları (Base 3, L0 4–45 … L7 1.976+) ve "kümülatif aylık fiyatlama" ilkesi (aynı yapı AWLC'de geçerli).
- **[CMG-2020] —** CMG, "Understanding Z Pricing to Control your Software Costs" (2020). AWLC kademe sınırlarının güncel teyidi; R4HA'nın LPAR bazlı tepeye göre faturalanması.
- **[LONGPELA] —** Longpela Expertise, MLC fiyatlama yazıları. "L7'nin MSU fiyatı L6'dan ~%20 düşük" gözlemi; L4+ için ×0,80 düşüş varsayımının dayanağı.
- **[VALUE4IT] —** value-4it, "Mainframe Software Costs" yazı dizisi. ~150 MSU ≈ yıllık £1M yazılım; büyüklük mertebesi teyidi.
- **[TU11] —** IBM Technology Update Pricing (z17 için TU11): AWLC indirimleri kademe bandına göre %12–42. Mutlak seviyenin aşağı yönlü gerekçesi.
- **[ZIIP] —** IBM z16 zIIP kuralları (SG24-8950): zIIP MSU'ya sayılmaz, alt-kapasite modellerde tam hızda çalışır, zIIP:CP ≤ 2:1. Tipik offload aralığı (%10–25, Redress Compliance) doğrulanmamıştır, yalnızca aralık olarak kullanılır.
- **\[LIC\] (kullanımdan kaldırıldı) —** Önceki sürümdeki $40/MSU/ay değerinin kaynağı (atonementlicensing.com). Metodolojisi açıklanmadığı ve IBM'in kendi örnek faturasıyla ~7–10 kat çeliştiği için bırakıldı.
- **[IBM-EAGLE] —** IBM, "Mainframe skills: The myths and the reality" (v3, IBM Eagle TCO ekibi), slayt 5: 17 müşteri çalışmasından "5 FTE to start + 1 FTE for every 625 MIPS". https://public.dhe.ibm.com/software/os/systemz/pdf/Mainframe_skills_-_The_myths_and_the_reality_v3.pdf. Üretici kaynağı.
- **[GARTNER-ITKMD] —** Gartner IT Key Metrics Data 2016, CA Technologies (Broadcom) "Why the Mainframe Should Be Part of Your Digital Business Ecosystem" üzerinden: kurulu MIPS/mainframe FTE 152 → 268, MIPS başına maliyet $5.517 → $3.057, mainframe FTE'leri BT FTE'lerinin %5,5'i. https://docs.broadcom.com/doc/why-the-mainframe-should-be-part-of-your-digital-business-ecosystem. İkincil aktarım.
- **[IBM-TPF-2007] —** IBM, "A Fresh Look at the Mainframe: Mainframe Total Cost of Ownership Issues" (TPFUG 2007): Gartner'a göre ekip 2001 → 2004 sabitken MIPS iki katından fazla arttı; örnek karşılaştırmada 3.192 MIPS ≈ 4 FTE ($793K). https://public.dhe.ibm.com/software/htp/tpf/tpfug/tgs07/tgs07e.pdf
- **[BLS-OEWS] —** U.S. Bureau of Labor Statistics, Occupational Outlook Handbook / OEWS, Mayıs 2025 medyanları (DBA ve mimarlar $126.760; ağ ve sistem yöneticileri $99.130; bilgi güvenliği analistleri $129.180) ve Mayıs 2023 DBA dağılımı (15-1242). https://www.bls.gov/ooh/computer-and-information-technology/
- **[BLS-ECEC] —** BLS, Employer Costs for Employee Compensation, Haziran 2026: özel sektörde maaş toplam işveren maliyetinin %70,0'ı, yan haklar %30,0'ı. https://www.bls.gov/opub/ted/2026/compensation-costs-for-private-industry-workers-averaged-46-89-per-hour-worked-in-june-2026.htm
- **[IDC-2016] —** IDC, "The Business Value of the Connected Mainframe for Digital Transformation" (2016, CA sponsorlu): yüklü maaş = maaş + %28 yan hak ve genel gider. https://docs.broadcom.com/doc/idc-the-business-value-of-connected-mainframe-for-digital-transformation
- **[MF-PAY] —** Payscale, Mainframe Systems Programmer (23 profil, 2022 güncellemesi, ort. ~$90K, 10–90. yüzdelik $49–130K); Glassdoor, Db2 z/OS DBA (toplam ücret $104–163K, tek kayıt). Küçük örneklem; yalnızca aralık teyidi.
- **\[PWR\] —** Aynı fiyat rehberi (electronics.alibaba) enerji ölçütleri. z15/z16 frame başına 20-40 kW; modelde POWER_KW_PER_SYSTEM = 30 kW (orta).

### 11.8. Teorik Temel

- **[QUEUE]** Kuyruk teorisi (per-CP M/M/1). Mainframe WLM/RMF response-time percentile metodolojisiyle uyumlu (SMF 72.3 / 110.1).

## 12. Modelin Bilinen Eksikleri ve Sonraki Adımlar

### 12.1. Kalibre Edilmemiş Parametreler [ASSUME]

- İş yükü profili: CPU_US_PER_SQL_READ = 30 µs, CPU_US_PER_SQL_WRITE = 70 µs (tek saha), GETPAGES_PER_SQL_READ = 4, BP_HIT_RATIO = 0,95, LOG_SYNC_IO_PER_COMMIT = 1, ASYNC_WRITE_IO_PER_SQL_WRITE = 0,5; oltp_heavy bileşimi (Bölüm 4.4)
- Donanım: HW_FRAME_BASE_COST = $500K + HARDWARE_COST_PER_MIPS = $200/PCI (taban + doğrusal kestirim), 1 yıllık garanti (bakım 2.–5. yıl)
- CPU_US_TM_BASE yalnızca 3931-718 çapasından türetilir (85,9 µs). 3931-726 çapası 93,3 µs verir; fark %9'dur ve tek çapa seçimi bir kalibrasyon belirsizliğidir. Köprünün (TPS/PCI) kendi belirsizliği aralık parametrelerine dahil değildir; CPU_US_PER_SQL_READ/WRITE aralıkları bu belirsizliği dolaylı olarak kapsar
- DS8900F model kataloğundaki tepe IOPS (DS8910F için 860K) drive sayısından bağımsız alınır; az drive'lı küçük bir dizide gerçek tepe daha düşüktür
- Personel: FTE eğrisi (FTE_1000, b, taban) ve yüklü maliyet için üç senaryo; topoloji çarpanları 1,00 / 1,05 / 1,15 / 1,25 (Bölüm 7.7)
- Yazılım: SW_PRICE_LEVEL_FACTOR = 1,0 (2004 nominal), L4+ kademe düşüşü ×0,80, ürün katsayılarının 2004 oranlarını koruduğu varsayımı (Bölüm 7.1.6)
- zIIP: ZIIP_OFFLOAD_FRACTION = 0,10, ZIIP_HW_PRICE_FACTOR = 0,25
- Availability: saha olayı süreleri (d_kısa, d_uzun), planlı kesinti sıklığı ve süreleri, M1'in RPO'su (günlük yedek) (Bölüm 6.4)
- DR_FRAME_COST_FRACTION = 0,50 (CBU fiyatı yayımlanmıyor), GDPS sabit bedeli M3 $50K / M4 $100K aylık (Bölüm 6.7)
- COD_DAILY_MULTIPLIER = 2,5 ve base kademe için "≥ ortalama yükün %120'si" eşiği
- TFP: CORRIDOR_PREMIUM = 1,5, CORRIDOR_FRACTION = 0,20 (IBM örneğinden), CORRIDOR_SUBSCRIPTION_RATE = 0, TFP_SW_DISCOUNT = 0 (Bölüm 9.8'de taranır)
- Storage: STORAGE_DISCOUNT = 0,70, lisans oranları 0,15 + 0,10, DB_OVERHEAD_FACTOR = 1,5, RAID_USABLE_FRACTION = 0,75, SAFEGUARDED_RESERVE = 0,25, planlama ufku 3 yıl; I/O yolu: önbellek isabeti 0,90, zHyperLink payı 0,80, t_miss = 300 µs, Metro Mirror mesafesi 20 km (Bölüm 8)
- ELECTRICITY_USD_PER_KWH = $0,12, POWER_KW_PER_SYSTEM = 30 kW
- Yedekleme: BACKUP_RETENTION_WEEKS = 4, BACKUP_DAILY_CHANGE = 0,03, BACKUP_COMPRESSION = 2,0, cache liste fiyatı $2.000/TB (kaynaksız), küme tabanı 2006 TS7700 fiyatı (nominal), işlem başına log baytı (yazma SQL 400 B, commit 200 B), STATIC_PEAK_TO_AVG = 1,5, yedek penceresi 8 saat, küme başına 4 kW; geri yüklemeye ayrılan RTO payı 0,5, TCT verimi 5.000 MB/s, on-prem nesne depolama $100/TB + $5/TB-ay (en küçük site sistemi $70K), bulut hattı devresi $2.000/ay, yılda bir geri yükleme testi (Bölüm 8.10)
- NPV: iskonto oranı %7, TPS büyümesi %10 (senaryo girdisi), fiyat artışları (yazılım %3, bakım %3, ücret %3,3, enerji %4), TFP büyüme fiyatı 0,5, kalan değer 0 (Bölüm 9.10.4)

### 12.2. Yapısal Basitleştirmeler

- Enerji, büyük kademelerde drawer/rack sayısıyla ölçeklenmiyor (Bölüm 7.4 notu).
- Kurulu drawer özelliği base'i taşıyan en küçük özellik olarak sabit; drawer maliyeti yok, bu yüzden özellik seçimi karar değişkeni değil (Bölüm 9.5).
- Corridor genişliği base MSU'nun sabit bir oranı; IBM'de bu, iş yükü analiziyle müşteriye özel belirlenir.
- On/Off CoD kaydının 180 günlük süresi ve tek-aktif-kayıt kuralı modellenmiyor (simülasyonlarda en fazla 261 gün CoD görülüyor; bu, kayıt yenilemesi gerektirir).
- R4HA LPAR değil CPC toplamı üzerinden hesaplanıyor.
- Peak günler yıla eşit aralıklarla dağıtılıyor (gerçekte mevsimsel kümelenir); tek yıllık ufuk.
- DR frame'i kapasite eklemiyor; tek CEC tavanı (oltp_rw ~187K TPS) aşılamıyor (Bölüm 4.4.4). DR makinesinin kalıcı kapasitesinin küçük yazılım faturası ihmal ediliyor.
- İş yükü profilinde lock/latch çekişmesi, Db2 data sharing'in (coupling facility) ek CPU maliyeti ve zIIP'teki işin latency'si yok.
- Availability beklenen değerdir, dağılım yok; sistem içi yazılım arızaları sysplex ile tamamen maskelenmiş sayılıyor; bölgesel felaket ayrıca modellenmiyor. GDPS Metro (tek bölge, RPO 0, RTO < 1 saat) ayrı topoloji değil; "RPO 0 ve RTO ≤ 60 dk" kısıtı bu yüzden daha pahalı M3'ü seçtiriyor, "RPO 0 ve RTO ≤ 1 dk" ise infeasible (Bölüm 6.6, 6.8).
- 5 yıllık yol açgözlüdür: kademe her yıl o yılın yüküne göre en ucuz izinli yükseltmedir; ileriye bakan optimizasyon yok. 5 yıl içinde z17'ye geçiş modellenmez; yükseltme PCI fiyatı nominal sabittir (Bölüm 9.10.8).
- Drawer maliyeti olmadığı için 5 yıllık yolda geçici kapasitenin drawer sınırına çarpması (retail_bursty, 5. yıl) kalıcı bir yükseltmeye zorlar; önceden büyük drawer kurma seçeneği değerlendirilemiyor (Bölüm 9.10.7).
- Yedekleme işinin CPU'su (image copy, log arşivleme) MSU faturasına eklenmez; zIIP'e kayabilen ve gece penceresinde çalışan bir yük olarak ihmal edilir. Yedek ağı (FICON, grid bağlantısı) ve fiziksel teyp arşivi kapsam dışıdır (Bölüm 8.10.6).
- Personel kurulu kapasiteye göre hesaplanır; aynı yük için daha büyük bir kademe (örneğin sıkı latency hedefi) personeli de büyütür. Bu, ekiplerin kurulu MIPS'e göre boyutlandığı kaynak çalışmalarıyla [IBM-EAGLE, GARTNER-ITKMD] tutarlı bilinçli bir tercihtir (Bölüm 7.7.5).

### 12.3. Yol Haritası (Değerlendirme #2, M3–M8)

- Parallel Sysplex data sharing ile tek CEC'in ötesine ölçekleme (oltp_rw'de ~187K TPS üstü şu an infeasible); SQL CPU maliyetleri için ikinci bir mutlak çapa (IRWW veya gerçek SMF 101 örneği)
- Maliyet yapısı: donanımda taban + drawer + kapasite başına artış (drawer özelliğini karar değişkeni yapar); gerçek bir AWLC fiyat tablosuyla L4+ kademelerin ve mutlak seviyenin kalibrasyonu; TFP-HW zIIP corridor'u
- Availability: GDPS Metro'yu ayrı topoloji olarak eklemek; planlı kesinti sıklığını gerçek bir değişiklik kaydıyla kalibre etmek; kesinti dağılımı ve SLA ihlali olasılığı (stokastik model)
- Storage: gerçek bir DS8900F, TS7770 ve kurum içi nesne depolama teklifiyle indirim, lisans ve cache fiyatı kalibrasyonu; TCT veriminin ölçülmesi; DS8000 G10
- Gerçek bir teklifle CBU ve GDPS fiyatlarının kalibrasyonu; personel için Türkiye gibi farklı pazarlara yüklü maliyet seti
- Aralık çıktısının olasılıklı hali (Monte Carlo: parametre dağılımları ve korelasyon)
- Kümelenmiş (mevsimsel) peak dağılımı; TFP-SW MSU taahhüdünün devri; 5 yıllık yolda ileriye bakan kademe optimizasyonu ve teknoloji yenilemesi
- (Opsiyonel) z16 A02 rack-mount modelleri
