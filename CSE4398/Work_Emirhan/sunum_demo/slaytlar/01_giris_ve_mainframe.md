# Slayt İçeriği — Bölüm 1: Giriş ve Mainframe Katmanları

*Her slayt: başlık, maddeler, kullanılan veri/kaynak, tasarım gerekçesi, konuşmacı notu. Sayılar `main` dalındaki modellerin 2026-11-23 koşusundan; demo case numaraları `sunum_demo/DEMO_SENARYOLARI.md`'ye atıftır. Kaynak etiketleri ([REDP], [LSPR] …) `docs/mainframe_model_documentation_v3.md` §11 ve `docs/kopruler_v1.md` §20'deki listeye karşılık gelir.*

---

## Giriş (3 slayt)

### Slayt G1 — Araştırma sorusu

- Verilen bir OLTP iş yükünü ve SLA'yı karşılayan **en düşük tam yığın TCO** hangisi: on-prem IBM z16 mi, kümelenmiş x86 mı?
- Girdiler: TPS, iş yükü bileşimi, latency, availability, RPO/RTO, veri hacmi ve büyümesi.
- Çıktılar: her iki platform için minimum maliyetli feasible yapılandırma, $/TPS/ay, **crossover bölgesi**, duyarlılık (tornado) ve başabaş personel oranı.
- Kapsam: compute, yazılım lisansı, storage, yedek, DR/availability, personel, üretim dışı ortamlar, enerji, 5 yıllık NPV.

**Veri / kaynak:** `project_justification.md` (araştırma boşluğu), `mainframe_model_documentation_v3.md` §1, `x86_model_dokumantasyonu_v1.md` §1.

**Tasarım gerekçesi:** Literatürdeki karşılaştırmalar çoğunlukla yalnızca compute'u ya da üretici vakalarını kapsıyor; lisans, storage, DR ve personeli birlikte modelleyen parametrik ve tekrar üretilebilir bir araç yok (`benzer_calismalar_v1.md`).

**Konuşmacı notu:** "Tek bir fiyat söylemiyoruz. Her girdi kombinasyonu için iki platformun en ucuz yapılandırmasını kuran ve sonucu bir aralık olarak veren bir araç yaptık. Asıl çıktı 'hangi koşullarda hangisi kazanır' sorusunun haritası."

---

### Slayt G2 — Yöntem: iki optimizasyon modeli, bir ortak modül, 18 köprü

- `mainframe_model.py`: (topoloji M1–M4, kademe 317 seçenek) üzerinde en ucuz feasible çözüm.
- `x86_model.py`: (yığın 8 aday, topoloji X1–X4, sunucu SKU, Oracle RAC düğüm sayısı) üzerinde en ucuz feasible çözüm.
- `common_model.py`: iki tarafın paylaştığı her şey (iş yükü bileşimi, saha olayları, ücret, elektrik, yedek fiyatları, NPV, personel eğrisi, fiyat dönemi).
- `kopruler_v1.md`: iki platformu aynı ölçüye bağlayan 18 köprü (KB-01 – KB-18).
- 54 birim testi; golden snapshot; her değişiklik log'a ve değerlendirmeye bağlı (9 değerlendirme).

**Veri / kaynak:** `src/`, `docs/ortak_modul_dokumantasyonu_v1.md`, `docs/kopruler_v1.md`, `evaluations/`.

**Tasarım gerekçesi:** "Ortak olan ortak kurala bağlanır, yapısal fark eşitlenmez modellenir" ilkesi (x86 dokümanı §1.2). Ortak parametreler tek yerde durduğu için bir tarafın lehine ayrı ayrı ayarlanamaz.

**Konuşmacı notu:** "Adil karşılaştırmanın garantisi kodun yapısında: iki model aynı fonksiyondan okuyorsa aynı varsayımı kullanmak zorunda. Farklı olan yerler bilinçli ve belgeli asimetriler."

---

### Slayt G3 — Kapsam dışı ve sınırlılıklar (baştan söylenir)

- **MQ / mesajlaşma:** iki tarafta da kapsam dışı (proje kararı, 2026-10-31).
- **z16 A02 / AGZ rack-mount (3932):** kapsam dışı. Düşük TPS'te mainframe taban maliyetini düşürebilir; sınırlılık olarak raporlanır.
- **Parallel Sysplex data sharing:** modellenmedi. Tek CEC tavanı oltp_rw'de ~132.700 TPS. x86'da karşılığı Citus/sharding de modellenmedi; iki tavan aynı statüde sınırlama.
- **Bare-metal Kubernetes, PUE, raf alanı, veri merkezi ve SAN ağı:** iki tarafta da dışarıda.
- **Teknoloji yenilemesi (z17, yeni sunucu nesli):** 5 yıllık ufukta iki tarafta da dışarıda.
- **K6 kendi sysbench ölçümümüz:** henüz yapılmadı; x86 kapasite köprüsü 60–120 aralığıyla taşınıyor.

**Veri / kaynak:** v3 §1.3–1.4, §12; x86 dokümanı §1.4, §18; `kopruler_v1.md` §0.3 karar kaydı.

**Tasarım gerekçesi:** Kapsam dışılar iki tarafa simetrik uygulanır; tek taraflı dışlama sonucu kaydırırdı. Asimetrik kalanlar (A02 yalnızca mainframe'de) açıkça sınırlılık olarak yazılır.

**Konuşmacı notu:** "Bunları sondan değil baştan söylüyorum, çünkü sonuçların geçerli olduğu bölgeyi tanımlıyorlar. Özellikle yüksek hacimde (130K TPS üstü) söyleyeceklerimiz, iki tarafın modellenmeyen ölçekleme seçeneklerine bağlı."

---

## Mainframe Katmanları (14 katman × 2 slayt)

### Slayt M1.1 — Kademe tablosu: z16 A01'in 317 kapasite ayarı

- 7xx: 1–200 tam hızlı CP (200 seviye); 4xx/5xx/6xx: ilk 39 CP için üç alt-kapasite serisi (117 seviye).
- Her kademe: PCI (IBM'in MIPS'i), MSU (yazılım faturası birimi), LSPR oranı.
- 120 kademe doğrudan IBM LSPR'den; 197 kademenin (7xx, 4–200 CP) PCI'si resmî MSU'dan türetildi.
- Fiziksel özellikler Max39 / 82 / 125 / 168 / 200 (drawer sayısı); geçici kapasite sınırlarında kullanılır.

**Veri / kaynak:** [LSPR] IBM Z LSPR ITRR tabloları; [EXHIBIT] 3931 MSU tablosu; [SG24-8950]; `data/z16_a01_capacity.csv`, `data/raw/`, `src/tools/build_z16_capacity_table.py`.

**Tasarım gerekçesi:** Kademe tablosu kodun içinde değil, ham IBM verisinden yeniden üretilebilen ayrı bir dosyada; her değer kaynağıyla satır satır karşılaştırılabilir. Önceki sürüm z/VM tablosunu kullanıyordu ve 32 CP'de kesiliyordu (128 kademe ve yapay tavan); denetimde düzeltildi.

**Konuşmacı notu:** "Mainframe'i tek bir kutu olarak değil, IBM'in sattığı 317 ayrı kapasite seviyesi olarak modelliyoruz. Model bunların hangisinin yettiğini ve en ucuz olduğunu seçiyor."

---

### Slayt M1.2 — Türetilen PCI'lerin doğrulaması

- Bilinen 120 satırda MSU/PCI oranı PCI'nin düzgün, azalan bir fonksiyonu: ~0,125'ten ~33.000 PCI'da 0,11723'e iner.
- Oran eğrisi + sabit nokta iterasyonu: PCI = MSU / oran(PCI).
- Birini dışarıda bırak: maks. hata %1,07, ortalama %0,09.
- Bağımsız kontrol: 3931-7K0 için türetilen 215.099 PCI, bağımsız kaynakta 215.089 (fark **%0,004**).
- Sınırlılık: 7xx 4–200 için LSPR Low/High (RNI) oranları türetilmedi.

**Veri / kaynak:** [LSPR], [EXHIBIT], [STINE]; v3 §3.3.

**Tasarım gerekçesi:** Kamuya açık LSPR sayfası 3931-703'te kesiliyor. Eksik veriyi varsayımla değil, IBM'in kendi MSU derecelendirmesinden türetmek ve iki bağımsız testle doğrulamak.

**Konuşmacı notu:** "Veri eksikti; uydurmadık, IBM'in yayımladığı MSU'dan geri hesapladık ve iki ayrı testle sağlamasını yaptık. 200-way'de bile hata on binde birin altında."

---

### Slayt M2.1 — Kapasite köprüsü: benchmark'tan PCI başına TPS'e

- LSPR bütün nesilleri aynı baza ölçer → "TPS / PCI" nesilden bağımsız bir katsayıdır.
- REDP-5320 (CICS TS 5.3, z13): 2964-718 174.000 TPS / 21.579 PCI = 8,063; 2964-726 227.000 / 29.048 = 7,815.
- **TPS_PER_PCI = 7,939** (iki noktanın ortalaması; %3,1 fark köprünün belirsizliği).
- `ham_TPS(kademe) = PCI × 7,939 / w / (1 − f)`; n-way ölçeklenme kaybı PCI'nin içinde, ayrıca uygulanmaz.

**Veri / kaynak:** [REDP] IBM Redpaper REDP-5320; [LSPR-z13]; v3 §4.1–4.3; KB-02.

**Tasarım gerekçesi:** Mainframe için kamuya açık tek ölçülmüş yüksek hacimli OLTP benchmark'ı bu rapor. PCI üzerinden taşımak, z13 ölçümünü z16'ya nesil farkıyla birlikte aktarır.

**Konuşmacı notu:** "Köprünün mantığı basit: IBM'in kendi ölçeği PCI, benchmark'ın kendi TPS'i belli; ikisinin oranı her z16 kademesine uygulanabilir. Bu katsayı tezin mainframe tarafındaki temel taşı."

---

### Slayt M2.2 — Köprünün sınırları ve makullük kontrolü

- Köprünün ölçtüğü "1 işlem" çok hafif: 1 STARTBROWSE + 5 READNEXT, bellekteki CICS tablosu, Db2 yok, CPU 85,9 µs (z13).
- Gerçek CICS-Db2 işleminin yalnızca Db2 CPU'su 1,25–1,32 ms [CATTERALL-2019], ~15 kat ağır.
- Makullük: IBM z14 "günde 12 milyardan fazla işlem" (~139K TPS) → w ≈ 9; oltp_rw'nin w'si 12,85. Yalnızca büyüklük mertebesi teyidi.
- Tek kaynaklı köprü; LSPR karışımının CICS/Db2 OLTP'ye benzediği bir varsayım.

**Veri / kaynak:** [REDP-PROFILE] (`data/raw/redp5320_workload_profile.csv`), [CATTERALL-2019], [IBM-Z14-PR]; v3 §4.4.1, §4.5.

**Tasarım gerekçesi:** Ham benchmark TPS'iyle hesap yapmak mainframe'i ~9–13 kat ucuz gösterirdi (Değerlendirme #1'in "TPS ortak birim değil" tehdidinin mainframe yarısı). Bu yüzden köprü bir bileşim ağırlığıyla düzeltilir (sonraki katman).

**Konuşmacı notu:** "Burada akademik olarak en hassas nokta şu: benchmark işlemi gerçek bir bankacılık işlemi değil. Bunu fark etmeseydik mainframe'i bir mertebe ucuz gösterecektik."

---

### Slayt M3.1 — İş yükü profili: "1 işlem"in bileşimle tanımı

- Bir işlem = nokta okuma + aralık okuma + yazma SQL + commit.
- `CPU(µs) = 85,9 + (nokta + aralık × 3,65) × 30 + yazma × 70`; `w = CPU / 85,9`.
- I/O bileşimden: senkron okuma = okuma × 4 getpage × (1 − 0,95); + commit log yazımı; IOPS = senkron + yazma × 0,5.
- Hazır profiller: redp_light (w 1,00), tpcb_like (4,61), **oltp_rw (12,85, varsayılan)**, oltp_heavy (16,37); `--sql-reads/--sql-writes` ile özel bileşim.

**Veri / kaynak:** [REDP-PROFILE], [CATTERALL-2012] (INSERT ~68 µs), [SYSBENCH] bileşimi, F kararı (RANGE_READ_WEIGHT 3,4–3,9, Vonng alt testleri); v3 §4.4.2–4.4.3; `common_model.WORKLOAD_MIXES`.

**Tasarım gerekçesi:** oltp_rw = sysbench oltp_read_write, x86 tarafında en yaygın ölçülen OLTP bileşimi. Böylece TPS iki tarafta aynı işi ifade eder (KB-01). w bir oran olduğu için nesilden bağımsızdır.

**Konuşmacı notu:** "Demo Case 6: aynı 10.000 TPS, iş tanımına göre 1 CP'den 32 CP'ye; aylık $265K'dan $1,33M'ye. TPS tek başına anlamsız; bileşimiyle birlikte söylenmeli."

---

### Slayt M3.2 — İş yükü profilinin etkisi ve en kritik varsayım

- 10K TPS'te oltp_rw: 3931-524 (16.380 PCI, 1.971 MSU), 0,62 işlem/s/PCI.
- Tek z16 tavanı: oltp_rw ~132.700 TPS, oltp_heavy ~104K, redp_light ~1,5M.
- **En kritik parametre CPU_US_PER_SQL_READ** (15 / 30 / 60 µs): tornado'da 1. sıra, 10K TPS'te $888K – $1,57M/ay.
- BP_HIT_RATIO (0,90–0,99) yalnızca I/O ve D_io'yu etkiler (M1'de 0,43 – 0,12 ms), maliyeti değil.
- Kalibrasyon yolu: gerçek bir Db2 accounting (SMF 101) örneği.

**Veri / kaynak:** model koşusu (`--range`), v3 §4.4.4, §7.11; Demo Case 6 ve Case 10.

**Tasarım gerekçesi:** Kaynakla daraltılamayan değer tek nokta yerine aralık olarak taşınır ve tornado'da görünür kılınır; okuyucu sonucun neye en duyarlı olduğunu görür.

**Konuşmacı notu:** "Mainframe tarafında en çok neyi bilmiyoruz sorusunun cevabı bu: bir okuma SQL'inin z16'daki CPU maliyeti. Gerçek bir SMF kaydı bu aralığı daraltır."

---

### Slayt M4.1 — Latency modeli: CP başına M/M/1 + sabit I/O gecikmesi

- Sunucu = fiziksel CP; `E[X_cpu] = c / ham_TPS`.
- `R(p) = D_io + E[X] / (1 − ρ) × ln(1/(1 − p))` (c bağımsız M/M/1: paylaşımlı M/M/c'den kötü → tutucu üst sınır).
- `ρ_max = min(1 − E[X]·ln(1/(1−p)) / (hedef − D_io), 0,90)`; %90 operasyonel tavan, latency hedefi tavanı yalnızca düşürebilir.
- D_io storage katmanından: oltp_rw'de M1 0,26 ms, M2–M4 0,46 ms (senkron Metro Mirror).

**Veri / kaynak:** WLM percentile hedefleri ve RMF SMF 72.3 / 110.1 (endüstri pratiği); v3 §5.1–5.4; KB-05.

**Tasarım gerekçesi:** Sabit bir kullanım tavanı kullanıcının latency hedefini yansıtmaz. Percentile tabanlı hedef WLM'in kendi diliyle aynı. Aynı kuyruk ailesi x86'ya da uygulanır (simetri).

**Konuşmacı notu:** "Kuyruk modelini bilerek kötümser seçtik: her CP'nin kendi kuyruğu var. Gerçek sistem daha iyi davranır; yani bulduğumuz kapasite bir üst sınır."

---

### Slayt M4.2 — Latency davranışı: alt-kapasite CP'ler yavaştır

- 10K TPS (Demo Case 3): hedef yok 3931-524 ($1,139M) · 50 ms 3931-614 ($1,141M) · 20 ms 3931-710 ($1,153M) · 10 ms 3931-714 ($1,190M).
- Hedef sıkılaştıkça 5xx → 6xx → 7xx: daha az ama daha hızlı CP.
- oltp_rw'de en düşük feasible p99 hedefi 6–7 ms (6 ms infeasible).
- Personel sabit kalır ($521.333): P kararıyla personel kurulu kapasiteden değil iş yükünden hesaplanır.
- Sınırlılık: ağ, lock/latch beklemesi modellenmez; zIIP'teki işin latency etkisi ayrıca yok.

**Veri / kaynak:** model koşusu; v3 §5.5; `test_latency_monotonic` (maliyet hiçbir senaryoda hedef sıkılaştıkça azalmıyor).

**Tasarım gerekçesi:** Aynı kapasiteyi farklı CP hızıyla satmak mainframe'e özgü bir mekanizma; model bunu ayrı bir kural olarak değil, kuyruk formülünün doğal sonucu olarak yakalar.

**Konuşmacı notu:** "Latency hedefi verilmezse model en ucuz MSU'lu yavaş kademeyi seçer. Sıkı bir SLA verdiğinizde tam hızlı CP'lere geçer; maliyet artışı %1–4."

---

### Slayt M5.1 — Availability: olay tabanlı, kurtarma süresine bağlı

- `D = λ_saha × [(1 − p_uzun)·min(d_kısa, T_rec) + p_uzun·min(d_uzun, T_rec)] + λ_planlı × T_planlı + D_cpc`; `A = 1 − D / 8.760`.
- Saha olayı (veri merkezi düzeyi): 0,15 olay/yıl, kısa 2 sa, %15'i uzun (48 sa).
- Topolojiler (SG24-8446 desenleri): M1 tek CPC sysplex · M2 DR CPC (CBU) + Metro Mirror, elle geçiş · M3 GDPS Metro Global + HyperSwap · M4 GDPS Continuous Availability.
- Sonuçlar: M1 %99,962 · M2 %99,994 · M3 %99,998 · M4 %99,99994.

**Veri / kaynak:** [UPTIME-2025], [UPTIME-2022], [SG24-8446], [SG24-6374], [GDPS-2026], [ITIC-2023]; v3 §6.2–6.5.

**Tasarım gerekçesi:** ITIC'in "9 nine"i sunucu donanımının kesintisidir, hizmetin değil; SG24-8446 desenlere yüzde atamaz. Bu yüzden kesinti, kesinti doğuran olayların sıklığı × topolojinin kurtarma süresi olarak hesaplanır. Aynı denklem x86'ya da uygulanır (KB-07).

**Konuşmacı notu:** "Mainframe'in 9 nine donanımı yılda 0,3 saniye; M1'in yıllık 3,3 saatlik kesintisinin on binde biri. Hizmeti kesen veri merkezi olayları ve planlı bakım; topolojiler bunlara karşı kurulur."

---

### Slayt M5.2 — RPO/RTO kısıtları ve availability'nin maliyeti

- Kullanıcı topoloji seçmez: availability, RPO ve RTO girer, topoloji türetilir.
- RPO 0 → M2 (senkron); RTO ≤ 60 dk → M3; RTO ≤ 1 dk → M4. **RPO 0 + RTO ≤ 1 dk infeasible:** saniyelik kurtarma yalnızca GDPS CA'nın asenkron replikasyonuyla.
- Maliyet (Demo Case 4): %99,9 M1 $113,93 · %99,99 M2 $122,29 · %99,999 M4 $143,97.
- M4'e çıkışta: GDPS $100K/ay, DR frame (CBU, ×0,50), personel ×1,25, 4 storage kopyası; **yazılım değişmez** (CBU kuralı).
- Sınırlılık: bölgesel felaket ve kesintinin dağılımı (stokastik) modellenmedi; planlı kesinti sıklığı kaynaksız.

**Veri / kaynak:** [CBU] "Software charges for the designated CBU machine are based on its permanent configuration."; [GDPS-PRICE] (yayımlanmıyor); v3 §6.6–6.8.

**Tasarım gerekçesi:** GDPS fiyatı yayımlanmadığı için yazılıma oranlı prim yerine sabit aylık kalem (aralık parametresi); böylece hacim arttıkça payı küçülür, bu gerçek fiyatlama yapısına daha yakın.

**Konuşmacı notu:** "Modelin bir infeasible çıktısı aslında bir bulgu: mainframe'de sıfır veri kaybı ile otuz saniyede kurtarma aynı anda alınamıyor."

---

### Slayt M6.1 — Yazılım yığını: z/OS + CICS TS + Db2, AWLC kademeli

- Fatura kümülatif kademeli: Base 1–3 MSU, L0 4–45 … L7 1.976+; her MSU kendi kademesinin marjinal fiyatıyla.
- Referans eğri (Db2, 2004 USD): Base $3.960, L0 $208, L1 $88, L2 $66, L3 $50/MSU; L4+ ×0,80 geometrik düşüş [ASSUME].
- Ürün katsayıları IBM örnek faturasından kalibre: z/OS ×2,509, CICS ×1,247, Db2 ×1,060.
- Faturalanan MSU = R4HA tepesi (sub-capacity); DR (CBU) makinesi faturayı artırmaz.
- 10K TPS'te yazılım $402.932/ay, toplamın %35'i.

**Veri / kaynak:** [IBM-ZNALC], [CMG-2020], [IBM-2004] örnek fatura, [LONGPELA], [VALUE4IT] (150 MSU'da ~£1M/yıl kontrolü); v3 §7.1.

**Tasarım gerekçesi:** Önceki sürümün doğrusal $40/MSU'su hem yapı (ölçek ekonomisini siliyordu) hem seviye (IBM'in kendi örneğinin ~7'de biri) hatasıydı. Kademeli yapı mainframe'in en belirgin ölçek ekonomisidir.

**Konuşmacı notu:** "Mainframe'in pahalı olmasının birinci kaynağı burası, ama aynı zamanda ölçeklendiğinde ucuzlamasının da birinci kaynağı. Eğrinin bükülmesi bu kademelerden geliyor."

---

### Slayt M6.2 — zIIP ve yazılımın belirsizliği

- zIIP: Db2 DRDA, Java, bazı sistem görevleri; MSU'ya sayılmaz (faturaya girmez), alt-kapasite modelde bile tam hızda.
- f = 0,10 [ASSUME, muhafazakâr]; aralık 0 / 0,10 / 0,25; GP kademesi 1/(1 − f) kat fazla iş taşır; zIIP donanımı GP'nin 0,25'i.
- SW_PRICE_LEVEL_FACTOR 0,5 / 1,0 / 1,75 (2004 listesi; üst uç ABD TÜFE ile 2026). Tornado'da 2. sıra: $898K – $1,50M.
- L4+ kademe fiyatları yayımlanmamış: faturalanan MSU 575'i aştığında (oltp_rw'de ~4,5K TPS) devreye girer; yüksek hacimde en kritik yazılım riski (v3 §7.1.6).

**Veri / kaynak:** [ZIIP], [IBM-PRICE-2026]; v3 §7.1.5–7.1.6; model `--range` tornado.

**Tasarım gerekçesi:** Yüksek bir zIIP payı mainframe lehine yanlılık yaratır; bu yüzden varsayılan düşük, aralık geniş. Mutlak fiyat seviyesi eğrinin şeklini değil yerini değiştirir: crossover'ın varlığı değil konumu bu parametreye duyarlı.

**Konuşmacı notu:** "AWLC'nin üst kademe fiyatları kamuya açık değil. Elinde gerçek IBM teklifi olan bir kurum bunu `--prices` dosyasıyla girebilir; model o zaman bu parametreyi belirsiz saymaz."

---

### Slayt M7.1 — Donanım, bakım ve enerji

- `satın_alma = HW_FRAME_BASE_COST ($500K) + PCI × $200 + zIIP bedeli`; 5 yıl amortisman.
- Bakım yıllık %12,5, 1 yıllık garanti sonrası; enerji frame başına 30 kW × $0,12/kWh.
- Topoloji çarpanı: M2–M4'te DR frame `DR_FRAME_COST_FRACTION` = 0,50 (aralık 0,30–1,00); enerji tam.
- 10K TPS'te donanım $64.811 + bakım $32.405 + enerji $2.628: toplamın ~%9'u.

**Veri / kaynak:** [PRICE] fiyat rehberleri ($500K – $10M+), [PWR] 20–40 kW; v3 §7.2–7.4.

**Tasarım gerekçesi:** Frame tabanı olmadan en küçük kademeler gerçek dışı ucuz çıkıyordu ($0,17M), bu da crossover'ın beklendiği düşük TPS bölgesinde mainframe lehine yanlılıktı. Fiyat yayımlanmadığı için iki parametre de aralıkta.

**Konuşmacı notu:** "Mainframe'in donanımı toplamın sadece onda biri. Maliyetin büyük kısmı yazılım ve personel; bu, tezin genel bulgularından biri."

---

### Slayt M7.2 — DR frame, CBU ve GDPS

- DR CPC Capacity BackUp ile: donanım kurulu, kapasite mikrokodla açılır; yılda 1 ücretsiz 10 günlük test, tek 90 günlük gerçek aktivasyon.
- Yazılım faturası DR makinesinin yalnızca küçük kalıcı kapasitesine göre kesilir → model ihmal eder.
- GDPS sabit aylık kalem: M3 $50K, M4 $100K [ASSUME]; MSU'ya değil kapsamına bağlı, yayımlanmıyor.
- Sınırlılık: enerji 39 CP üstünde birden fazla drawer/raf için eksik sayılıyor; drawer maliyeti yok.

**Veri / kaynak:** [CBU] SC28-7025, [GDPS-PRICE], [CFCC]; v3 §6.7.

**Tasarım gerekçesi:** CBU, mainframe'in x86'da karşılığı olmayan yapısal avantajı: DR sitesi tam lisans istemez. Bu asimetri eşitlenmez, modellenir (KB-11).

**Konuşmacı notu:** "x86'da DR sitesindeki her düğüm tam lisans ister; mainframe'de DR yazılımı neredeyse bedava. Bu fark modelde iki taraf için ayrı kurallarla duruyor."

---

### Slayt M8.1 — Storage: IBM DS8900F

- Neden dahil: storage veri hacmiyle büyür, compute sabitken ikinci bir crossover ekseni yaratır; iki tarafta yapısı farklı (shared-disk vs shared-nothing), birbirini götürmez.
- Neden DS8900F: z16 ile aynı nesil; mainframe storage pazarının %40–50'si; zHyperLink yalnızca DS8000'de; açık product guide.
- Katalog: DS8910F-993 (737 TB, z16 çerçevesine monte), 994 (2.949 TB), DS8950F-996 (5.898 TB, 2,32M IOPS).
- `ham_TB = veri × 1,15³ × 1,5 / 1,0 / 0,75`; kopya: M1 1, M2 2, M3/M4 4; dizi sayısı = max(kapasite, IOPS / 0,70 tepe).

**Veri / kaynak:** [REDP-5554], [TT-2019], [ITCANDOR], [ITJUNGLE-22] ($8,62/GB liste); `data/ds8900f_models.csv`; v3 §8.1–8.4.

**Tasarım gerekçesi:** "Tek alternatif" ilkesi (mainframe tarafı tek yığın): rakip diziler kombinasyon sayısını büyütür ama karşılaştırmanın sorusunu değiştirmez. Kopya sayısı kullanıcıya sorulmaz, topolojiden türetilir.

**Konuşmacı notu:** "Demo Case 5: 500 TB'ta storage ve yedek mainframe toplamının %16,5'i. Storage'ı dışarıda bırakan bir çalışma bu ekseni hiç göremez."

---

### Slayt M8.2 — Storage maliyeti ve I/O gecikmesi

- Fiyat: (flash $8.620/TB + kontrolcü) × (1 − 0,70 indirim) + lisans %25 (BF, z-synergy, Copy Services); etkin ~$2.590/ham TB.
- I/O: `t_okuma = h × (z × 20 µs zHyperLink + (1 − z) × 90 µs) + (1 − h) × 300 µs` = 61 µs; yazma M1 90 µs, M2–M4 290 µs (20 km × 10 µs/km).
- Safeguarded Copy için birincilde +%25 kapasite.
- Sonuç: 10K TPS'te 20 TB → $7.496; 500 TB → $153.226 (994).
- Tehdit: indirim oranı (0,50–0,85) mutlak düzeyi ~3 kat oynatır; göreli sonuçlar (hacimle doğrusal büyüme, topolojiyle kopya) bundan bağımsız.

**Veri / kaynak:** [VENDORBENCH], [REDP-5554], [TT-2019]; v3 §8.5–8.6, §8.1.5.

**Tasarım gerekçesi:** Storage gecikmesi latency modelinin D_io'sunu besler: availability topolojisi senkron kopya üzerinden latency'yi de etkiler. Storage'ın host CPU yükü mainframe'de yok (kanal alt sistemi), x86'da açıkça eklenir: bilinçli asimetri.

**Konuşmacı notu:** "zHyperLink 20 mikrosaniyelik okuma veriyor; bu mainframe'e özgü bir avantaj ve modelde ayrı bir parametre olarak duruyor."

---

### Slayt M9.1 — Yedekleme: üç hedef, kısıtlar, en ucuzun seçimi

- Hedefler: TS7770 sanal teyp · on-prem S3 uyumlu nesne depolama (DS8900F TCT yolu) · AWS S3 Standard-IA + Direct Connect (hibrit).
- Hacim (üç hedefte aynı): 4 haftalık tam image copy + günlük artımlı (%3) + arşiv log (yazma × 400 B + commit × 200 B).
- Kısıtlar: 8 saatlik yedek penceresi; M1'de tam geri yükleme ≤ RTO / 2 = 36 saat; nesne hedeflerinde TCT ≤ 5.000 MB/s.
- `auto` = kısıtları karşılayanların en ucuzu; `--backup-target` ile zorlanabilir.

**Veri / kaynak:** [TS7700-2024], [TS7700-2006], [SG24-8381], [MINIO-TCO], [AWS-S3-2026], [AWS-DX-2026], [DB2-BACKUP], [IDUG-2024]; v3 §8.10.1–8.10.4.

**Tasarım gerekçesi:** Replikasyon ve GDPS mantıksal bozulmayı (fidye yazılımı, hatalı güncelleme) bütün kopyalara taşır; yedek ayrı bir katmandır. M1'in 24 sa RPO / 72 sa RTO iddiası yedeğin başka sitede olmasına dayanır.

**Konuşmacı notu:** "Kurumlar mainframe yedeğini gerçekte üç yoldan biriyle alıyor; model üçünü de fiyatlıyor ve kısıtlara göre seçiyor. S3 seçildiğinde çıktı 'hibrit' diye işaretleniyor."

---

### Slayt M9.2 — Yedek sonuçları: topoloji yedek teknolojisini belirler

- Küçük/orta veride nesne depolama TS7770'in yaklaşık yarısı (100 TB: $11.648 vs $20.750; S3 $17.787).
- 500 TB'ta M1'de nesne depolama elenir (geri yükleme 36 saate sığmaz) → TS7770 $75.420 (Demo Case 5, 7).
- Zorlanan hedef kısıtı karşılamazsa model feasible hedefe düşer ve bunu yazar.
- Başlık sonucuna etkisi küçük (20 TB'ta toplamın %0,7'si), veri hacmi ekseninde büyük.
- Sınırlılık: TS7770 ve TCT verimi yayımlanmıyor; çok büyük veride FlashCopy tabanlı yedek modellenmedi.

**Veri / kaynak:** model koşusu; v3 §8.10.5–8.10.6.

**Tasarım gerekçesi:** Fiyatı yayımlanmayan her kalem (TS7770 tabanı, cache, nesne depolama donanımı ve aboneliği) aralık parametresidir.

**Konuşmacı notu:** "Modelin daha önce göstermediği bir etkileşim: tek siteli M1'de RTO kısıtı, büyük veride yedeği teybe geri itiyor."

---

### Slayt M10.1 — Personel: alt-doğrusal FTE eğrisi

- `FTE = max(taban, FTE_1000 × (PCI_eşdeğer / 1000)^b) × topoloji_çarpanı`.
- low / mid / high: FTE_1000 4,0 / 5,5 / 7,0; b 0,60 / 0,70 / 0,80; taban 3 / 4 / 5 FTE.
- Yüklü ücret $122K / $162K / $215K (BLS OEWS × yan hak çarpanı 1,28–1,43).
- Topoloji çarpanı M1 1,00 · M2 1,05 · M3 1,15 · M4 1,25.
- 10K TPS: 38,6 FTE, $521.333/ay, toplamın %46'sı.

**Veri / kaynak:** [IBM-EAGLE] "5 FTE to start + 1 FTE for every 625 MIPS"; [GARTNER-ITKMD] 152 → 268 MIPS/FTE; [IBM-TPF-2007]; [BLS-OEWS], [BLS-ECEC], [IDC-2016]; v3 §7.7.

**Tasarım gerekçesi:** b < 1 → MIPS/FTE kapasiteyle artar (ölçek ekonomisi). Eğriler kaynak çapalarını sarmalayacak şekilde seçildi: high Gartner 2016'yı, low Gartner eğiliminin 2026'ya taşınmasını izler.

**Konuşmacı notu:** "Personel hem mainframe'in en büyük kalemi hem de en belirsiz kalemi. Kesin bir 'doğru FTE' yok; kaynaklar arasında üç kat fark var, biz de bunu aralık olarak taşıyoruz."

---

### Slayt M10.2 — P kararı: personel iş yükünden, iki tarafa aynı eğri

- Girdi kurulu kademe değil, iş yükünün sürekli PCI eşdeğeri: `PCI_eş = TPS × w × (1 − f) / 7,939 / 0,90`.
- Latency için alınan boş kapasite personeli büyütmez; yıllık modda tepe TPS kullanılır.
- Aynı eğri x86'ya: `FTE_x86 = FTE_ortak × STAFF_RATIO_X86`, ana senaryoda 1,0 (nötr).
- Personel hariç TCO her sonuçla birlikte verilir.
- Sınırlılık: ABD ücretleri; Türkiye pazarı için ayrı parametre seti gerekir; outsourcing kapsam dışı.

**Veri / kaynak:** P kararı (Emirhan, 2026-11-16), Değerlendirme #8 §2.1; `common_model.staff_fte`; KB-13.

**Tasarım gerekçesi:** Değ. #8'de bulunan tutarsızlık: aynı 10K TPS'te mainframe 30,8 FTE, x86 sunucu saatlerinden 0,39 FTE çıkıyordu. İki taraf farklı sürücüyle ölçülürse crossover'ı teknoloji değil ölçüm farkı belirler.

**Konuşmacı notu:** "Personel konusunda taraf tutmadık: iki platform aynı eğriyle, sonra 'x86 personeli kaç kat olursa sonuç döner' sorusunu ayrıca cevaplıyoruz. O sayı 2,16."

---

### Slayt M11.1 — Üretim dışı ortamlar (NONPROD)

- `nonprod = NONPROD_FACTOR × birincil site {yazılım + donanım (amortisman + bakım) + enerji + birincil storage}`.
- Mainframe 0 / **0,20** / 0,50; x86 0 / 0,50 / 1,00 (stres 2,0).
- DR, GDPS, yedek ve personel hariç (personel üretimle birlikte sayılıyor).
- 10K TPS'te mainframe $102.054/ay (%9); x86 $3.434.
- Tutucu basitleştirme: mainframe'de dev/test aynı CEC'te LPAR olarak durur ve AWLC'nin düşen marjinal fiyatından yararlanır; model bunu saymaz (mainframe aleyhine).

**Veri / kaynak:** [IBM-EAGLE-2013] "üretim +%20 / dağıtıkta +%200"; v3 §7.9; KB-14.

**Tasarım gerekçesi:** Kalem dışarıda bırakılırsa, IBM'in iddiası doğruysa karşılaştırma x86 lehine kayar. İki tarafa ayrı çarpan (Emirhan, 2026-11-02); üretici kaynağının yanlılığına karşı aralık geniş.

**Konuşmacı notu:** "IBM'in dağıtıkta +%200 iddiasını bile stres senaryosu olarak koşturuyoruz: x86 10K TPS'te sadece %1,9 pahalanıyor, çünkü x86'nın üretim dışı tabanı zaten küçük."

---

### Slayt M11.2 — İki fiyat modu ve fiyat yaşları

- (a) Kaynaklı fiyat seti (varsayılan) · (b) kullanıcı fiyat dosyası: `--prices dosya.json` kayıtlı parametrelerin bir kısmını ya da tamamını geçersiz kılar.
- Verilen fiyat artık belirsiz sayılmaz; bağlı aralık parametresi tornado'dan çıkar.
- `--list-prices`: JSON şablonu; `--price-vintages`: her fiyatın kaynak yılı.
- Mainframe fiyat yaşları: AWLC 2004 · TS7700 2006 · z16 $/PCI, DS8900F 2022 · ücret 2025 · S3/DX/elektrik 2026.
- Mainframe'de 18, ortak modülde 12 kayıtlı fiyat parametresi.

**Veri / kaynak:** v3 §7.10; `ortak_modul_dokumantasyonu_v1.md` §10; KB-15.

**Tasarım gerekçesi:** Kaynaklı fiyatlar akademik tekrar üretilebilirlik için; kullanıcı fiyatları pratik kullanım için (gerçek teklifi olan bir kurum). Fiyat yaşlarını görünür kılmak, 2004 AWLC ile 2026 S3 arasındaki farkın gizlenmemesi için.

**Konuşmacı notu:** "Araç bir kurumun elindeki gerçek teklifle de çalışabiliyor; o zaman aralık o parametre için kapanıyor."

---

### Slayt M12.1 — Yıllık simülasyon: 8.760 saat ve R4HA

- Deterministik saatlik profil: günlük sinüs (tepe ~14:00), hafta sonu ×0,65, yıla dağıtılmış tepe günleri; tepe/ortalama oranı kapalı formla tam tutturulur.
- Presetler: steady_oltp 1,5× / 10 gün · retail_bursty 3,5× / 20 gün · batch_heavy 2,5× / 30 gün.
- Yazılım aylık R4HA tepesinden: `r4ha[i] = ortalama(profil[i−3 : i+1])`, ayın en büyüğü faturalanır.
- CSV çıktısı: 8.760 satır saatlik + 12 satır aylık (grafik-hazır).

**Veri / kaynak:** [IBM-ZNALC] sub-capacity / R4HA; v3 §9.1–9.3, §9.9.

**Tasarım gerekçesi:** Tek bir ortalama TPS, R4HA tepesini ve dolayısıyla yazılım faturasını gizler: bir saatlik patlama bütün ayın faturasını yukarı çeker. Saatlik simülasyon bunun için zorunlu.

**Konuşmacı notu:** "Mainframe yazılımı ortalama yükten değil, ayın en yoğun dört saatinden faturalanıyor. Bu yüzden statik modelin yanında saatlik bir yıl simülasyonu da var."

---

### Slayt M12.2 — Fiyatlama stratejileri A / B / C

- **A Permanent:** yılın tepesine göre kalıcı kademe.
- **B Base + On/Off CoD:** küçük base; tepe günlerde geçici kapasite (24 saatlik dönemler, ×2,5 primli).
- **C Tailored Fit Pricing:** base + her zaman açık corridor (kullanıldıkça) + CoD; yazılım MSU-saat tüketimiyle.
- Resmî sınırlar: geçici kapasite ≤ %100 satın alınan; drawer ekleyemez; alt-kapasite serisi aşağı inemez.
- Sonuç (Demo Case 8, 10K ort.): steady C $17,23M (A'dan %2,1) · batch C $23,51M (%4,8) · retail C $29,28M (B'den %0,1).

**Veri / kaynak:** [TFP-HW], [TFP-SW], [COD] SC28-7025; v3 §9.4–9.8.

**Tasarım gerekçesi:** CoD mainframe ekonomisinin karakteristik özelliği; modellenmezse mainframe haksız pahalı görünür. Corridor ve CoD fiyatları sözleşmeye özel → parametre + duyarlılık. Gelir-nötr TFP kalibrasyonu.

**Konuşmacı notu:** "Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanı. Ama strateji farkı küçük, çünkü donanım toplamın onda biri; stratejiyi asıl belirleyen IBM ile yazılım pazarlığı (TFP_SW_DISCOUNT %5 C'yi her presette öne geçiriyor)."

---

### Slayt M13.1 — 5 yıllık NPV: formül ve büyüme yolu

- `NPV = Σ [capex_y / (1 + r)^(y−1) + opex_y / (1 + r)^y] − kalan değer`; capex yıl başında, opex yıl sonunda.
- r = %7 (Damodaran 2026), yük büyümesi %10/yıl, veri %15/yıl.
- Kademe yalnızca yükselir (PCI, CP sayısı, seri azalamaz); storage/yedek 3 yıllık döngülerle; topoloji 1. yılda sabit.
- Artışlar: yazılım %3, bakım %3, ücret %3,3, enerji %4; TFP büyüme MSU'su %50 fiyat.
- Özet ölçüler: NPV, EAC, **seviyelendirilmiş $/TPS/ay** (LCOE karşılığı).

**Veri / kaynak:** [DAMODARAN-2026], [IBM-PRICE-2026], [BLS-ECI-2026], [EIA-EPM], [TFP-SW-2021], [KYNE-2022]; v3 §9.10; KB-16.

**Tasarım gerekçesi:** Statik amortisman paranın zaman değerini, büyümeyi ve fiyat artışlarını gizler. İskonto oranı köşe senaryolarına girmez: yüksek r mainframe'i hep ucuz gösterir, "low = mainframe lehine" tanımını bozardı; ayrı taranır.

**Konuşmacı notu:** "Tutarlılık testi: r, büyüme ve artışlar sıfırken NPV tam olarak statik aylık toplamın 60 katı çıkıyor. İki model arasında köprü bu test."

---

### Slayt M13.2 — NPV sonuçları

- 10K TPS, 5 yıl: NPV $68,62M, seviyelendirilmiş $115,70/TPS/ay (x86 $32,07M, $54,07).
- Kademe yolu: 524 → 527 → 530 → 534 → 537; 10 yıllık ufukta 6. yılda 6xx serisine geçiş (3931-637, $3,29M capex).
- Ufuk etkisi (Demo Case 10): 3 / 5 / 10 yıl → $121,11 / $115,70 / $111,51 (capex yayıldıkça düşer).
- Yıllık modda üç strateji 5 yılda: TFP büyüme fiyatıyla C kazanır (retail_bursty C $152,8M, B $155,2M, A $161,4M).
- Sınırlılık: kalan değer 0; z17 yenilemesi dışarıda.

**Veri / kaynak:** model koşusu (`--npv`, `--years`); v3 §9.10.6–9.10.8.

**Tasarım gerekçesi:** Seviyelendirilmiş maliyet statik $/TPS/ay ile doğrudan karşılaştırılabilir; okuyucu iki modu aynı birimde görür.

**Konuşmacı notu:** "Seviyelendirilmiş maliyet statik sonuca çok yakın; yani statik başlık sonucu zaman değeri hesaba katıldığında da ayakta kalıyor."

---

### Slayt M14.1 — Aralık çıktısı: low / mid / high

- Kaynakla daraltılamayan her parametre low / mid / high; **low = mainframe lehine** uç.
- Köşe senaryoları (hepsi low / hepsi high) topolojiyi ve kademeyi yeniden seçer.
- 10K TPS: low $31,44 (3931-438) · mid $113,93 (3931-524) · high $565,95 (M2, 3931-635: high'da availability düştüğü için M1 %99,9'u sağlamaz).
- Availability belirsizliği maliyet aralığına bu yolla girer.

**Veri / kaynak:** model `--range`; v3 §7.8; KB-18.

**Tasarım gerekçesi:** Emirhan'ın kararı (2026-11-01): nokta fiyat yerine kaynaklı aralık. Tek bir sayı, yayımlanmamış fiyatlar karşısında yanıltıcı kesinlik verirdi.

**Konuşmacı notu:** "Aralık geniş, ama bu bir zayıflık değil, dürüstlük: IBM'in yazılım ve donanım fiyatlarının önemli kısmı yayımlanmıyor. Önemli olan aralığın içinde sıralamanın nasıl davrandığı."

---

### Slayt M14.2 — Tornado: sonucu en çok ne oynatıyor?

- 10K TPS, diğerleri mid ($/ay):
  1. Okuma SQL CPU (µs): $888K – $1,57M
  2. AWLC mutlak fiyat seviyesi: $898K – $1,50M
  3. Personel FTE eğrisi + taban: $905K – $1,49M
  4. Yüklü personel ücreti (ortak): $1,01M – $1,31M
  5. Üretim dışı ortamlar: $1,04M – $1,29M
  6. Yazma SQL CPU · zIIP payı · L4+ kademe düşüşü · planlı kesinti · donanım $/PCI
- Okuma: ilk iki sıra mainframe'e özgü ve kalibre edilebilir (SMF 101 kaydı, gerçek AWLC teklifi).

**Veri / kaynak:** model `--range` çıktısı (Demo Case 10).

**Tasarım gerekçesi:** Tornado, araştırmanın bir sonraki veri toplama önceliğini belirler: hangi parametre daraltılırsa sonuç en çok netleşir.

**Konuşmacı notu:** "Bir hoca 'en zayıf varsayımınız ne' diye sorarsa cevap bu slaytta: okuma SQL'inin CPU maliyeti ve AWLC fiyat seviyesi. İkisi de gerçek kurum verisiyle kapanabilir."
