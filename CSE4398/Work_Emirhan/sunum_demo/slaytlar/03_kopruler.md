# Slayt İçeriği — Bölüm 3: Köprüler (KB-01 – KB-18)

*18 köprü × 2 slayt. Bir köprü, iki platformun aynı girdiyle beslendiği, aynı ölçüyle ölçüldüğü ya da aynı kuralla fiyatlandığı arayüzdür. Her köprünün ilk slaytı "ne ve nasıl", ikinci slaytı "kanıt, karar ve açık kalan"dır. Kaynak: `docs/kopruler_v1.md`; kodlamada yapılan dört düzeltme `docs/x86_model_dokumantasyonu_v1.md` §17'de.*

**Açılış slaytı önerisi (Slayt K0 — Köprü haritası):** 18 köprü dört grupta toplanır. **Ölçü:** KB-01 işlem birimi, KB-02/03 kapasite köprüleri, KB-04 kontrol, KB-05 kullanım ve latency, KB-06 tavanlar. **Dayanıklılık:** KB-07 availability, KB-08 topoloji, KB-09 storage, KB-10 yedek. **Maliyet:** KB-11 lisans, KB-12 kapsam sınırı, KB-13 personel, KB-14 üretim dışı, KB-15 fiyat dönemi, KB-17 enerji. **Zaman ve belirsizlik:** KB-16 NPV, KB-18 aralık. *Konuşmacı notu:* "Köprü yoksa iki model iki ayrı dünyayı ölçer; köprüler bu tezin metodolojik katkısı."

---

### Slayt KB-01.1 — İşlem birimi ve bileşim: TPS aynı işi ifade etmeli

- Sorun (Değ. #1'in en kritik tehdidi): TPS iki tarafta ortak bir birim değildi.
- Kural: oltp_rw = **10 nokta okuma + 4 aralık okuma + 4 yazma + 1 commit** (sysbench oltp_read_write, 20 ifade).
- Mainframe: `CPU = 85,9 + (nokta + aralık × RANGE_READ_WEIGHT) × 30 + yazma × 70`, w = CPU / 85,9.
- x86: sysbench oltp_read_write'ın kendisi ölçülür; aralık/nokta oranı çapanın içinde.
- `RANGE_READ_WEIGHT` iki tarafta ortak parametre (3,4 / 3,65 / 3,9).

**Veri / kaynak:** [Kopytov-sysbench], [Tencent-PG-TestMethods] (bileşim), [Burgess2016-REDP5320], [Catterall2012, Catterall2019].

**Tasarım gerekçesi:** Crossover "TPS başına maliyet" üzerinden kurulduğu için birim eşitliği bütün sonuçların ön koşulu. x86'da en yaygın ölçülen bileşimi seçmek, x86 tarafının kendi ölçümüyle karşılanabilmesini sağlar.

**Konuşmacı notu:** "Bu köprü olmasaydı bütün sonuçlar boş olurdu. İki taraf için 'işlem' kelimesini aynı SQL listesiyle tanımladık."

---

### Slayt KB-01.2 — KB-01: kanıt, karar, etki

- Vonng alt testlerinden türetme [DERIVED]: point_select 0,73 µs/işlem; read_only 18,77; → aralık/nokta = 3,44 (b = 0,73) – 3,94 (b = 0).
- Yazma/nokta 3,65–4,15 (mainframe'in 70/30 = 2,33'ü bunun altında, ayrı parametre).
- **Karar F (b), Emirhan, 2026-11-16:** aralık okumaları nokta okumadan ayrılır.
- Etki: w 9,15 → 12,85; 10K TPS kademe 3931-516 → 524; mainframe $/TPS +%23 (F mainframe lehine bir yanlılığı düzeltti).
- Açık kalan: K6'da oranın ölçülmesi; Db2'ye özgü aralık sorgusu maliyeti için IBM kaynağı (IRWW).

**Veri / kaynak:** [Vonng-PGPerf]; kopruler_v1 KB-01 "Etkisi".

**Tasarım gerekçesi:** PostgreSQL'deki göreli maliyetin Db2'ye taşınması bir varsayım; açıkça yazıldı ve ortak parametre olarak aralıkta taşınıyor.

**Konuşmacı notu:** "Bu karar mainframe'i pahalılaştırdı. Kendi modelimizin lehine olan bir yanlılığı bulup düzelttik; yönü dengeli kararlar KB-18'de özetleniyor."

---

### Slayt KB-02.1 — Mainframe kapasite köprüsü (PCI başına TPS)

- REDP-5320: 2964-718 8,063; 2964-726 7,815 TPS/PCI → **7,939**.
- `ham_TPS = PCI × 7,939 / w / (1 − f)`; f = zIIP payı 0 / 0,10 / 0,25.
- n-way ölçekleme kaybı her kademenin PCI'sinde; köprüde ayrıca uygulanmaz.
- %3,1'lik iki nokta farkı = köprünün belirsizliği.

**Veri / kaynak:** [Burgess2016-REDP5320], [IBM-LSPR-zOS22], [IBM-LSPR-ITRR].

**Tasarım gerekçesi:** LSPR bütün nesilleri System z9 2094-701 = 1,00 bazında verir; PCI bu ölçeğin sabit katı. Böylece z13 ölçümü z16 kademelerine nesil farkıyla birlikte taşınır.

**Konuşmacı notu:** "Tek bir sayı, 7,939, bütün mainframe kapasite hesabının temeli. Nereden geldiğini iki ölçüm noktasıyla gösterebiliyoruz."

---

### Slayt KB-02.2 — KB-02: makullük ve açık kalan

- Makullük: IBM z14 "günde 12 milyardan fazla şifreli işlem" (~139K TPS), z14 ~160K PCI kaba tahminiyle w ≈ 9 → büyüklük mertebesi tutuyor.
- Açık kalan: köprünün tek kaynağı REDP-5320; LSPR karışımının CICS/Db2 OLTP'ye benzediği bir varsayım.
- Durum: kuruldu (v3 §4); x86 karşılığı KB-03, ikisinin çapraz kontrolü KB-04.

**Veri / kaynak:** [AmwalAlGhad2017-z14]; v3 §4.4.3, §4.5.

**Tasarım gerekçesi:** Tek kaynaklı bir köprü, bağımsız bir büyüklük kontrolü ve platformlar arası tutarlılık kontrolüyle desteklenir.

**Konuşmacı notu:** "Daha iyi bir kaynak bulunursa (IBM'in IRWW ya da Db2 performans raporları) bu katsayı daralır; model yapısı değişmez."

---

### Slayt KB-03.1 — x86 kapasite köprüsü (çekirdek başına TPS)

- `X86_TPS_PER_SPECINT_CORE = ölçülen_TPS / (çekirdek × SPECint/çekirdek)` = 25.953 / 48 / 5,94 = **91**.
- `TPS/çekirdek = 91 × SPECint/çekirdek × S(n) × (1 − VIRT) × (1 − CONT) × Oracle çarpanı`.
- R760: 91 × 9,81 ≈ 893 TPS/çekirdek (ham).
- Bu katsayı çekirdek sayısını, dolayısıyla çekirdek başına lisansı (Oracle, vSphere), düğüm sayısını ve Patroni tavanını belirler.

**Veri / kaynak:** [Vonng-PGPerf], [SPEC2019-M640-8270], [SPEC2024-R760-6548Y], [SPEC2025-DL380G12]; bağlam: [Rockdata2026], [Tencent-PG-TestResults], [Alibaba-PolarDB-PG16] (normalize edilemiyor).

**Tasarım gerekçesi:** PCI köprüsünün simetriği: üretici bağımsız bir performans ölçeği (SPECrate2017) üzerinden ölçümü hedef SKU'ya taşımak.

**Konuşmacı notu:** "Mainframe'de PCI neyse x86'da SPECint o. İkisi de ölçümü bir hedef donanıma taşımak için kullanılan ölçek."

---

### Slayt KB-03.2 — KB-03: K kararı ve K6 protokolü

- **Karar K (b), Emirhan, 2026-11-16:** çapa K6 kendi ölçümümüz; Vonng çapraz kontrol. O zamana kadar **120 / 91 / 60**.
- K6 şartları: (1) SPEC'i yayımlanmış perakende SKU, (2) istemci ayrı makinede, (3) PG sürümü, iş parçacığı, süre, `synchronous_commit`, `fsync`, `shared_buffers` raporlanır, (4) 8/16/32/64 çekirdek taraması (USL), (5) point_select / read_only / write_only da koşulur, (6) bir koşu senkron replikayla.
- Sanallaştırma ek yükü ve Oracle verim çarpanı bu köprünün parçası (OTN benchmark yasağı → 1,0).
- Açık kalan: Cascade Lake → Sapphire/Emerald Rapids SPECint artışının bir kısmı bellek bant genişliğinden; OLTP'nin aynı oranda yararlandığı varsayım.

**Veri / kaynak:** kopruler_v1 KB-03; x86 dokümanı §5.2, §18 (tehdit 15).

**Tasarım gerekçesi:** Protokol şartları, Vonng ölçümünün belgelenmemiş ayarlarından kaynaklanan belirsizliği tekrarlamamak için.

**Konuşmacı notu:** "Bir sonraki iş paketimiz bu ölçüm. Ölçüm gelince aralık 60–120'den daralacak; yapı aynı kalacak."

---

### Slayt KB-04.1 — Platformlar arası tutarlılık kontrolü

- İki köprü bağımsız zincirlerden gelir; birinde mertebe hatası varsa burada görünür.
- F kararından sonra: 1 z16 CP ≈ **1,56** R760 çekirdeği (1.392 / 893); aralık uçlarıyla ~0,8 – 4,5.
- F öncesi: 2,19 (zIIP payıyla 2,43).
- Modelde parametre değil; bir kontrol.

**Veri / kaynak:** [DERIVED] KB-02 × KB-03; x86 dokümanı §5.5.

**Tasarım gerekçesi:** Doğrulama değil büyüklük mertebesi kontrolü; bağımsız iki zincirin aynı mertebede buluşması köprülerin güvenilirliğini artırır.

**Konuşmacı notu:** "Bir mainframe çekirdeği yaklaşık bir buçuk modern x86 çekirdeği ediyor. Bu sayı literatürdeki iddialarla nasıl karşılaştırılır, bir sonraki slayt."

---

### Slayt KB-04.2 — "1 CP = 24–80 x86 çekirdeği" iddiasının ayrıştırılması

- IBM konsolidasyon formülü: `N < P_R × U_R × C_R` (performans oranı 1–3, kullanım oranı 10–20, sunucu başına çekirdek).
- İddianın büyük kısmı **U_R**'den (dağıtık %5–12 vs mainframe %80–90 kullanım) ve dev/test kopyalarından gelir, işlemci hızından değil.
- Bizim köprümüz yalnızca P_R'yi ölçer; U_R'nin karşılığı KB-05'te (kullanım tavanı), dev/test KB-14'te.
- Uzlaştırma: U_R'yi en uç haliyle (%17,5 tavan) koşturmak bile sıralamayı çevirmiyor (Demo Case 1).

**Veri / kaynak:** [Shedletsky2008] [VENDOR]; `benzer_calismalar_v1.md` §3.3.

**Tasarım gerekçesi:** Üretici iddiasını reddetmek yerine bileşenlerine ayırıp her bileşeni ayrı, kaynaklı bir katmanda modellemek.

**Konuşmacı notu:** "IBM'in ünlü oranını çürütmüyoruz, parçalıyoruz. Parçaların her biri modelde ayrı bir düğme."

---

### Slayt KB-05.1 — Kullanım oranı, kuyruk ve latency

- Aynı kuyruk ailesi iki tarafta: çekirdek/CP başına bağımsız M/M/1 (tutucu üst sınır).
- Mainframe: `ρ_max = min(ρ_latency, 0,90)`; R = D_io + R_cpu.
- x86 (U kararı): `ρ_max = min(ρ_latency, X86_UTIL_CEILING)`; R = D_ağ + D_io + D_repl + R_cpu.
- D_repl: senkron replikasyonda commit başına gidiş-dönüş (mesafe × 10 µs/km, ortak fizik sabiti).

**Veri / kaynak:** v3 §5.3; [EDB-SyncRep] (10 ms'de `remote_write` +6,5 ms, verim −%40), [StorageReview2022-P5520].

**Tasarım gerekçesi:** Kurulu kapasite donanımı ve çekirdek başına lisansı belirler; iki taraf aynı kurala bağlanmazsa U_R etkisi kontrolsüz biçimde sonuca girer.

**Konuşmacı notu:** "v4 dokümanı x86 için M/M/c öneriyordu; o, x86'yı mainframe'den daha iyimser bir kuyrukla ölçmek olurdu. İkisini aynı aileye bağladık."

---

### Slayt KB-05.2 — KB-05: parametreler ve U kararı

| Parametre | low (x86 lehine) | mid | high |
|---|---|---|---|
| X86_UTIL_CEILING | 0,90 | 0,70 | 0,50 |
| NET_RTT_MS | 0,05 | 0,15 | 0,5 |
| ROUNDTRIPS_PER_TX | 1 (saklı yordam) | 20 | 20 |
| T_SAN_READ (µs) | 150 | 250 | 400 |

- **Karar U (b), Emirhan, 2026-11-16.** Low ucu mainframe ile eşit (0,90).
- %15–20 alt uç ana aralıkta yok (çift sayım); yalnızca "konsolide edilmemiş park" uzlaştırma senaryosu.

**Veri / kaynak:** kopruler_v1 KB-05; x86 dokümanı §6.

**Tasarım gerekçesi:** x86'da WLM ve CoD karşılığı olmadığı için tepe yükte boşluk bırakılır; tavan bu gerçeği yansıtır ama literatürün en uç değerini ana senaryoya taşımaz.

**Konuşmacı notu:** "U kararı x86 aleyhine bir yanlılığı düzeltiyor: önceki taslakta x86 da %90'a kadar dolduruluyordu."

---

### Slayt KB-06.1 — Ölçekleme mimarisi ve kapasite tavanları

| | Mainframe | x86 |
|---|---|---|
| Modellenen | Tek CEC; M2–M4'teki ikinci frame yedek | Patroni tek yazıcı; Oracle RAC düğüm ekler |
| Modellenmeyen | Parallel Sysplex data sharing | Citus / sharding (K3) |
| Tavan (oltp_rw) | ~132.700 TPS | Patroni ~35.900; RAC ~231.000 |

- Düğüm içi ölçeklenme `S(n) = (n / 48)^(b − 1)`, b 1,00 / 0,90 / 0,80; ana katalog 64 çekirdek, 96–128 ekstrapolasyon.
- `RAC_SCALING_EFFICIENCY` 0,95 / 0,90 / 0,80 (Oracle'ın %80 çekişme eşiği alt uç).

**Veri / kaynak:** [Patroni-ReplModes], [Oracle2024-RAC], [Kapila2016-PGCon]; x86 dokümanı §5.4.

**Tasarım gerekçesi:** Yüksek TPS'te crossover'ın yeri iki tarafın tek sistem tavanına bağlı; iki tavan aynı statüde (modellenmeyen ölçekleme seçeneği) yazılmalı.

**Konuşmacı notu:** "Parallel Sysplex'i modellemediğimiz için mainframe 133K'da duruyor; Citus'u modellemediğimiz için PostgreSQL 36K'da. Simetrik bir sınırlama."

---

### Slayt KB-06.2 — KB-06: karar ve kodlamadaki düzeltme

- K3 (b), Emirhan, 2026-11-02: Citus yok, tavan bir sınırlama.
- **Düzeltme (x86 §17, #4):** KB-06'da B_X86 low = 1,00 / high = 0,80; bu yalnızca n > 48 için x86 lehine yön. n < 48'de tersine dönüyordu → `X86_SCALING_LEVEL` düğüme göre yön tutarlı uç.
- Tavanın okunuşu: ~36K'ya kadar MF ↔ PG; 36K–133K MF ↔ RAC; 133K üstü yalnızca RAC (modellenmeyen seçeneklerin sonucu).
- Açık kalan: K6'da USL (Gunther) uyumu; RAC için USL biçiminde kaynak.

**Veri / kaynak:** x86 dokümanı §5.3, §17; `test_scaling_corners_direction_consistent`.

**Tasarım gerekçesi:** "low = x86 lehine" tanımı her koşulda tutmalı; tutmadığı yer test ile korunuyor.

**Konuşmacı notu:** "Köprü dokümanındaki bir aralık yönünün küçük düğümlerde ters çalıştığını kodlarken bulduk; bu, aralık analizinin kendi iç tutarlılığını koruyan bir düzeltme."

---

### Slayt KB-07.1 — Availability denklemi

```
D = λ_saha × [(1 − p_uzun)·min(d_kısa, T_rec) + p_uzun·min(d_uzun, T_rec)]   ← ortak modül
  + λ_planlı × T_planlı(topo)                                                ← platforma özgü
  + D_cpc (mainframe, yalnızca M1)  |  N_düğüm × λ_düğüm × T_failover (x86)
A = 1 − D / 8.760
```

- Elle geçişte `T_rec = MANUAL_FAILOVER_DECISION_MINUTES (ortak) + teknik geçiş (platforma özgü)`.
- Ortak: λ_saha 0,05 / 0,15 / 0,25; d_kısa 1 / 2 / 4 sa; p_uzun 0,08 / 0,15 / 0,30; d_uzun 24 / 48 / 72 sa; karar süresi 45 / 90 / 180 dk.

**Veri / kaynak:** [Uptime2025-PR], [DCF2022-Uptime], [IBM-SG24-8446], [ITIC2023-IBMZ, TechChannel2024-ITIC], [Vishwanath2010].

**Tasarım gerekçesi:** "Nine" değerleri farklı kaynaklardan gelirse karşılaştırılamaz. İki taraf aynı veri merkezi olaylarına maruz kalır; fark yalnızca kurtarma ve planlı işlemlerden.

**Konuşmacı notu:** "Availability'yi bir sayı olarak değil bir denklem olarak köprüledik; böylece iki tarafın yüzdeleri aynı kaynaktan geliyor."

---

### Slayt KB-07.2 — KB-07: platforma özgü parametreler ve açık kalan

- Mainframe: D_cpc 0,03 / 0,32 / 3,15 sn/yıl; T_planlı M1 4 sa, M2 30 dk, M3 2 dk (Değ #10, X3 ile parite), M4 30 sn (mid). Platform kesintisi iki tarafta aynı kural: N_kesen × ITIC_sunucu × u (z16 0,3 sn, x86 24 dk/sunucu/yıl).
- x86: düğüm olayı 0,03 / 0,10 / 0,30 /yıl; Patroni failover 15 / 35 / 90 sn (teorik, ölçüm değil); RAC 5 sn / 15 sn / 5 dk; 12 yama switchover/yıl.
- Sonuç: X1 %99,982 vs M1 %99,962 (fark planlı kesintiden); X3 (PG) %99,9987 vs M3 %99,9998 (fark platform kesintisinden: x86 kümesi daha çok ve daha sık kesilen sunucudan oluşur).
- Açık kalan: planlı kesinti sıklığı iki tarafta da kaynaksız (en etkili availability varsayımı); bölgesel felaket ayrıca modellenmedi.

**Veri / kaynak:** [Pigsty-RTO], [Oracle2026-MAA], [YellowBricks2021]; v3 §6.4; x86 dokümanı §8.3.

**Tasarım gerekçesi:** Ortak modülde duran parametreler bir tarafın lehine ayrı ayarlanamaz; platforma özgü olanlar kendi kaynaklarıyla.

**Konuşmacı notu:** "En zayıf varsayım her iki tarafta da aynı: planlı kesinti sıklığı. Gerçek bir değişiklik kaydı bu belirsizliği kapatır."

---

### Slayt KB-08.1 — Topoloji eşlemesi

| Kod | Mainframe (SG24-8446) | x86 (Oracle MAA / Patroni) | RPO | T_rec (mid) |
|---|---|---|---|---|
| M1 / X1 | Reliable base | Silver / tek site 3 düğüm | 24 sa (aynı kural) | site yok |
| M2 / X2 | Failover capable (CBU) | Data Guard SYNC / standby küme | 0 (PG: 5 sn) | 2 sa / 105 dk |
| M3 / X3 | Fault tolerant (GDPS Metro) | Gold / çok siteli Patroni | 0 | 2 dk / 2 dk (Değ #10) |
| M4 / X4 | Adaptive continuity (GDPS CA) | Platinum / PG infeasible | 5 sn | 30 sn / 15 sn |

- RPO ve RTO kullanıcı girdisi iki tarafta aynı biçimde topolojiyi seçer.
- Topoloji personel çarpanı ortak: 1,00 / 1,05 / 1,15 / 1,25.

**Veri / kaynak:** [IBM-SG24-8446], [Cook2026-GDPS], [Oracle2026-MAA], [Pigsty-RTO].

**Tasarım gerekçesi:** Desen düzeyinde eşleme: iki taraf aynı dayanıklılık sınıfında karşılaştırılır, aynı ada sahip ama farklı güvence veren yapılar değil.

**Konuşmacı notu:** "M ve X kodları aynı soruya cevap veriyor: bir site kaybolursa ne kadar veri ve ne kadar zaman kaybederim?"

---

### Slayt KB-08.2 — KB-08: kararlar ve düzeltme

- K4 (b), Emirhan, 2026-11-02: X4 PostgreSQL için infeasible; açık kaynak çekirdekte karşılığı olmayan topoloji uydurulmaz.
- M1 ve X1'in RPO'su aynı kurala bağlı (yedek hedefe log gönderim aralığı); birlikte değişir.
- **Düzeltme (x86 §17, #1):** KB-08'de X2 RPO 0 (iki DB). Patroni'nin iki veri merkezi önerisi asenkron standby küme → X2-PG RPO 5 sn [ASSUME]; Oracle Data Guard Max Availability SYNC ile 0.
- Sonuç: RPO 0 isteyen PG X3'e gider; %99,99 + RPO 0 + elle geçişte Oracle seçilir (Demo Case 4).

**Veri / kaynak:** [Patroni-MultiDC]; x86 dokümanı §8.2; `test_topologies_and_availability`.

**Tasarım gerekçesi:** Topolojinin RPO'su ürünün kendi belgesinden okunur, köprü dokümanındaki genelleme ürüne uymadığında ürün belgesi kazanır.

**Konuşmacı notu:** "Bu düzeltme bir demo senaryosunun sonucunu doğrudan değiştiriyor: veritabanı PostgreSQL'den Oracle'a geçiyor."

---

### Slayt KB-09.1 — Storage arayüzü ve fiyat sözleşmesi

- Ortak girdiler: `data_tb`, `data_growth`, 3 yıllık planlama ufku, iş yükünden IOPS (oltp_rw 5,8/işlem), %70 IOPS tavanı, topolojinin seçtirdiği kopya sayısı.
- Mainframe: `ham = veri × 1,15³ × 1,5 / 1,0 / 0,75`; kopya M1 1, M2 2, M3/M4 4 (DS8900F).
- x86 (K1): Oracle RAC → paylaşımlı all-flash SAN (site başına 1 + DR kopyası); Patroni → yerel NVMe × düğüm sayısı.
- Fiyat sözleşmesi: aynı sırayla ham TB; her teklif önce **ham TB başına listeye** çevrilir; indirim bir kez; veri azaltımı yalnızca boyutlandırmada bir kez.

**Veri / kaynak:** [ITJungle2022-Storage] ($8,62/GB), [VendorBenchmark2026-Storage] ($65–215 indirimli / $140–400 liste etkin TB); `common_model.py` §6.

**Tasarım gerekçesi:** Storage veri hacmiyle büyüdüğü için ikinci crossover ekseni; iki taraf aynı girdilerle ve aynı fiyat tanımıyla boyutlanmazsa eksen anlamsızlaşır.

**Konuşmacı notu:** "Etkin TB fiyatı ile ham TB fiyatını karıştırmak storage karşılaştırmalarının en yaygın hatası; sözleşme bunu engelliyor."

---

### Slayt KB-09.2 — KB-09: x86'ya özgü eklemeler, karar, etki

- AFA_DATA_REDUCTION (geri çevirme) 1,5 / 2,5 / 4,0; PG_BLOAT_FACTOR 1,1 / 1,3 / 1,6 (MVCC şişmesi + WAL); Patroni düğüm içi RAID yok (replika yeterli, [ASSUME]).
- K1 (a), Emirhan, 2026-11-02: storage tipi DB mimarisine bağlı.
- Etki (Demo Case 5): 500 TB'ta mainframe storage + yedek toplamın %16,1'i; x86'da PG yerel disk sınırı (~373 TB) Oracle + AFA'ya geçirir.
- Açık kalan: DS8900F gerçek indirim oranı (0,50–0,85) için teklif veya ihale kaydı.

**Veri / kaynak:** kopruler_v1 KB-09; x86 dokümanı §11.

**Tasarım gerekçesi:** Platformun kendi storage biçimi (shared-disk vs shared-nothing) korunur; arayüz ortak, mekanizma platforma özgü.

**Konuşmacı notu:** "Aynı veri iki platformda farklı ham kapasite istiyor; köprü bunu eşitlemiyor, aynı kuralla hesaplatıyor."

---

### Slayt KB-10.1 — Yedekleme

```
image copy = D_plan × hafta × (1 tam + 6 artımlı × günlük değişim)
log        = ort. TPS × işlem başına log baytı × 86.400 × 7 × hafta
log baytı  = yazma × 400 B + commit × 200 B         (x86'da × WAL_FPW_FACTOR)
```

- Kısıtlar: 8 saatlik pencere; M1/X1'de tam geri yükleme ≤ RTO / 2.
- Hedefler: mainframe TS7770 / nesne / S3; x86 nesne / S3 (TS7770 uygulanmaz). Fiyat fonksiyonları ortak (`cm.onprem_object_store`, `cm.s3_hybrid`).

**Veri / kaynak:** [IBM-Db2z12-Backup] "Make two copies of each level of image copy data sets", [Hendley2024-IDUG], [MinIO-ObjectTCO], [Nubbo2026-S3], [AWS-DXPricing].

**Tasarım gerekçesi:** Hacim kuralı iki tarafta aynı, böylece yedek farkı yalnızca platformun gerçek özelliklerinden (WAL FPW, sıkıştırma, TCT verimi) gelir.

**Konuşmacı notu:** "Log hacmi TPS'e bağlı; yedeği iş yüküne bağlayan tek mekanizma bu ve iki tarafta aynı bileşimden hesaplanıyor."

---

### Slayt KB-10.2 — KB-10: iki taraf ve x86 parametresi

| | Mainframe | x86 |
|---|---|---|
| Yol ve verim | DS8900F TCT ≤ 5.000 MB/s | pgBackRest / RMAN, 2 × 25 GbE × %80 |
| Yazılım | — | pgBackRest (0), RMAN (EE'ye dahil) |
| Sıkıştırma | TS7770 2,0; nesne 1,0 | 3,0 / 2,0 / 1,5 |

- WAL_FPW_FACTOR 1,5 / 2 / 3 [ASSUME]; K6'da ölçülecek.
- Asimetri (x86'da sıkıştırma var, mainframe nesne hedefinde yok): platform özelliği, küçük etkili, açıkça yazılı.

**Veri / kaynak:** kopruler_v1 KB-10; x86 dokümanı §11.4, §18 (tehdit 13).

**Tasarım gerekçesi:** Ortak olan (hacim, fiyat) ortak modülde; platforma özgü olan (yol, sıkıştırma, WAL) platform modelinde.

**Konuşmacı notu:** "Yedek toplamın küçük bir kısmı, ama tam yığın iddiası için iki tarafta da aynı derinlikte olmak zorundaydı."

---

### Slayt KB-11.1 — Lisans tabanı: yapısal asimetri

| | Mainframe | x86 |
|---|---|---|
| Fatura tabanı | Tüketilen MSU'nun aylık R4HA tepesi (AWLC kümülatif) | Kurulu fiziksel çekirdek / düğüm |
| DR sitesi | CBU: kalıcı (küçük) kapasiteden | Tam lisans |
| Geçici kapasite | On/Off CoD, TFP | Karşılığı yok |
| Garanti | 1 yıl | 3 yıl |

- Kural: bu fark **eşitlenmez, modellenir**.

**Veri / kaynak:** [IBM-SC28-7025], [Oracle2026-CoreFactor] (çekirdek faktörü 0,5), [Oracle-Partitioning], [Redress2026-OraclePL], [AceMQ-VVFvsVCF], [AceMQ2026-Renewals].

**Tasarım gerekçesi:** Lisans modeli farkı platformların gerçek bir özelliği; eşitlemek karşılaştırmanın konusunu silmek olurdu.

**Konuşmacı notu:** "Personel hariç tutulduğunda iki platform arasındaki 40 katlık farkın kaynağı bu köprü. Tezin personelden ayrı yazılması gereken bulgusu."

---

### Slayt KB-11.2 — KB-11: parametreler ve düzeltme

| Parametre | low (x86 lehine) | mid | high |
|---|---|---|---|
| VSPHERE_USD_PER_CORE_YEAR | 100 | 150 | 350 |
| OCP_USD_PER_COREPAIR_YEAR (düzeltilmiş) | 2.000 | 3.000 | 4.200 |
| ORACLE_DISCOUNT | 0,60 | 0,45 | 0,20 |
| PG_SUPPORT_USD_PER_CORE_YEAR | 0 | 500 | 1.500 |

- **Düzeltme (x86 §17, #2):** KB-11 OpenShift'i soket çifti başına (6K / 11K / 15K) fiyatlıyordu; sanal düğümler çekirdek tabanlı abonelik ister → çekirdek çifti başına.
- REDRESS fiyat listesi ikincil kaynak (doğrulanmalı).

**Veri / kaynak:** [RedHat2024-OCPSubGuide] "entitling the virtual compute nodes using core-based subscriptions."; [SWExpress-OCP], [VendorBenchmark2026-OCP].

**Tasarım gerekçesi:** Abonelik kuralı ürün belgesinden okunur; v4'ün "bare-metal Kubernetes yok" kuralıyla birlikte OpenShift düğümleri hep sanal.

**Konuşmacı notu:** "Lisans kurallarının ayrıntısı sonucu değiştiriyor; o yüzden her birini üreticinin kendi abonelik kılavuzundan okuduk."

---

### Slayt KB-12.1 — Kapsam sınırı: işlem yöneticisi ve uygulama katmanı

- Mainframe CPU'su ve lisansı CICS'i içerir; x86 çapasında uygulama yerine model dışındaki sysbench istemcisi → **mainframe aleyhine kapsam asimetrisi**.
- Kural (C kararı): `TM_payı = CPU_US_TM_BASE / CPU(oltp_rw)` (F ile ≈ %7,8); `uygulama_çekirdekleri = DB_çekirdekleri × TM_payı / (1 − TM_payı)`.
- Linux VM olarak fiyatlanır; ek lisans yok; sitede N+1, DR'da kopya.
- Mainframe tarafında değişiklik yok.

**Veri / kaynak:** [Burgess2016-REDP5320] 85,9 µs; [Shedletsky2008] 4,9 kat (yalnızca üst uç duyarlılık).

**Tasarım gerekçesi:** İki tarafın kapsam sınırı aynı olmalı; aksi halde mainframe faturasındaki CICS'in x86'da karşılığı eksik kalır.

**Konuşmacı notu:** "Mainframe'in lehine bir düzeltme: x86'ya, mainframe'in zaten ödediği uygulama katmanını ekledik."

---

### Slayt KB-12.2 — KB-12: karar ve etki

- **Karar C (b), Emirhan, 2026-11-16.**
- Etki: 10K TPS'te 0,9 meşgul çekirdek → 2 × 2×8c host; toplamın %0,3'ü, personel hariç maliyetin %12'si.
- Bu katman ağ gidiş-dönüşü terimini (KB-05) doğal kılar.
- Kendi bulgumuz: tavan ve sanallaştırma ek yükünün çift uygulanması düzeltildi (`test_app_tier`).
- Sınırlılık: bellek ve oturum sayısıyla boyutlanmıyor.

**Veri / kaynak:** x86 dokümanı §10.

**Tasarım gerekçesi:** Etkisi küçük olsa da kapsam eşitliği ilkesi gereği zorunlu.

**Konuşmacı notu:** "Sonucu değiştirmeyen ama yapılmaması sonucu şüpheli yapacak bir düzeltme."

---

### Slayt KB-13.1 — Personel: problem ve kanıt

- Problem (Değ. #8): 10K TPS'te mainframe 30,8 FTE, x86 sunucu saatlerinden 0,39 FTE (tabanla 4); fark ~$36/TPS/ay, sonucu tek başına belirliyordu.
- Doğrudan oranlanamaz: mainframe ortalaması MIPS başına, x86 sunucu başına → aynı iş için ~1.300 kat fark çıkar (farklı yoğunlukta parklar).
- Aynı iş yükü vakaları (x86 / mainframe, hepsi IBM kaynaklı): 3,28 · 3,00 · 1,23 · 1,32 · 3,10 · 1,50 · 15,4. Geometrik ortalama: FTE vakaları 2,0; konsolide 1,25; hepsi 2,7.
- Bağımsız (Gartner, Avasant, IDC) aynı iş yükü karşılaştırması bulunamadı; göç satıcıları sayı vermiyor.

**Veri / kaynak:** [IBM-CPO2014-Skills], [CA2016-MFEcosystem], [Rhoderick2007-TPFUG], [Calderon2011-Labor], [Shedletsky2008], [Jones2007-TCO], [Astadia2024-ROI].

**Tasarım gerekçesi:** Personel 10K TPS'te maliyetin ~%45'i; iki tarafın personeli farklı sürücülerle ölçülürse crossover'ı teknoloji değil ölçüm farkı belirler.

**Konuşmacı notu:** "Bütün nicel vakalar IBM kaynaklı ve büyük ihtimalle x86 aleyhine yanlı. O yüzden bunları parametre olarak değil, duyarlılık referansı olarak kullanıyoruz."

---

### Slayt KB-13.2 — KB-13: P kararı ve başabaş oranı

```
FTE_ortak(TPS)   = max(taban, FTE_1000 × (PCI_eş / 1000)^b) × topoloji_çarpanı
PCI_eş(TPS)      = TPS × w × (1 − f) / 7,939 / 0,90
FTE_x86          = FTE_ortak × STAFF_RATIO_X86    (ana senaryo 1,0)
```

- **Karar P, Emirhan, 2026-11-16:** personel crossover için nötr; duyarlılık 1,25 ve 2,0.
- **Başlık çıktısı: başabaş personel oranı** (10K TPS'te 2,07; Demo Case 9). Ek görünüm: personel hariç TCO.
- Tezde: "Personel düzeyi kuruluş düzeyindeki mainframe verisinden gelir ve iki platforma aynı eğriyle uygulanır… sonucun bu varsayıma duyarlılığı başabaş oranıyla gösterilir."

**Veri / kaynak:** kopruler_v1 KB-13 "Kural" ve "Tezde nasıl yazılır".

**Tasarım gerekçesi:** Kaynakla çözülemeyen bir soruyu (platformlar arası personel farkı) bir varsayımla kapatmak yerine soruyu çıktıya çevirmek: "x kat olursa sonuç döner".

**Konuşmacı notu:** "Bu köprü tezin en önemli metodolojik kararı. Okuyucuya bir sayıya inanmasını değil, kendi kurumunun personel oranını eşikle karşılaştırmasını söylüyoruz."

---

### Slayt KB-14.1 — Üretim dışı ortamlar

- Kural (ortak modül §9): `nonprod = NONPROD_FACTOR(platform) × birincil site {yazılım + donanım + enerji + birincil storage}`.
- DR, site otomasyonu, yedek ve personel hariç.
- Mainframe 0 / 0,20 / 0,50; x86 0 / 0,50 / 1,00; stres 2,0.
- x86 orta değeri: X1'de 3 düğüm → staging ≈ 0,33 + dev/test ≈ 0,1–0,2 ≈ 0,5 [DERIVED, ASSUME].

**Veri / kaynak:** [IBM2013-TCOLessons] "+%20 / +%200", HA kopyası üretimin 2–2,5 katı.

**Tasarım gerekçesi:** Aynı kural, ayrı çarpan: yapı farklı (mainframe'de LPAR, x86'da ayrı düğüm ve Oracle'da ayrı çekirdek lisansı).

**Konuşmacı notu:** "IBM'in +%200 iddiasını ana senaryoya değil stres senaryosuna koyduk ve etkisini gösterdik: %1,9."

---

### Slayt KB-14.2 — KB-14: karar ve tutuculuk yönü

- İki tarafa ayrı çarpan: Emirhan, 2026-11-02; x86 aralığı N (b): 2026-11-16.
- Mainframe kuralı, dev/test'in aynı CEC'te R4HA tepesine az katkısını ve IBM'in geliştirme/test fiyat tekliflerini saymaz → **mainframe aleyhine tutucu**.
- Etki 10K TPS: mainframe $102.054 (%9), x86 $3.434.
- Açık kalan: x86 orta değeri için bağımsız kaynak.

**Veri / kaynak:** v3 §7.9; x86 dokümanı §12.2.

**Tasarım gerekçesi:** Tutuculuğun yönü yazılır; okuyucu hangi tarafın lehine yuvarlandığını bilir.

**Konuşmacı notu:** "Mainframe'in burada hafif cezalandırıldığını biliyoruz ve yazıyoruz. Üst sınırı belli: bu kalemin tamamı 10K TPS'te toplamın %9'u; sıfırlansa bile oran 2,05'ten ~1,87'ye iner, yön değişmez."

---

### Slayt KB-15.1 — Fiyat dönemi ve fiyat modları

- 2026'da bellek ve SSD fiyat şoku: 64 GB DDR5 ~$255 → ~$1.000 (9 ayda); kurumsal NVMe $115 → $753/TB.
- Kural (E kararı): ana senaryo `PRICE_EPOCH` = **2025-mid** (şok öncesi, iki tarafın çapaları aynı dönemde); 2026-Q3 duyarlılık.
- Bellek ve NVMe her dönemde kendi low/mid/high üçlüsüyle; ayrı aralık parametresi yok (tornado'da çift sayım olmasın).
- Fiyat tabanı kuralı: bileşen önce liste karşılığına çevrilir, indirim bir kez; perakende spot fiyatı OEM indirimiyle birleştirilmez.

**Veri / kaynak:** [PCSP2026-Server], [PCSP2026-SSD], [CapCompute-RAM], [Bacloud2026-RAM], [TrendForce2026-DDR5], [Gray2005] (fiyat/performans yılda ~%68).

**Tasarım gerekçesi:** İki tarafın fiyatları farklı dönemlerden gelirse sonuç fiyat döneminin eseri olur.

**Konuşmacı notu:** "Mainframe fiyatları 2022 ve öncesinden. x86'yı 2026 şok fiyatlarıyla ölçseydik karşılaştırma döneme göre yanlı olurdu."

---

### Slayt KB-15.2 — KB-15: iki fiyat modu, karar, düzeltme

- İki fiyat modu (Emirhan'ın önerisi, 2026-11-02): kaynaklı set · `--prices dosya.json` (verilen fiyat aralıktan çıkar).
- **Karar E (b), Emirhan, 2026-11-16.**
- Mainframe fiyat yaşları görünür (`--price-vintages`): AWLC 2004, TS7700 2006, z16/DS8900F 2022, ücret 2025, S3/elektrik 2026.
- **Düzeltme (x86 §17, #3):** R760'ın Dell fiyatına ±%20 kalibrasyonu yapılamadı (kaynak yapılandırmayı vermiyor); yalnızca bant kontrolü.
- Etki: 2026-Q3'te x86 10K TPS $57,65 → $57,98; mainframe değişmiyor (IBM'in tepkisi bilinmiyor: sınırlılık).

**Veri / kaynak:** kopruler_v1 KB-15; x86 dokümanı §4.3, §13.4.

**Tasarım gerekçesi:** E kararı x86 aleyhine bir yanlılığı düzeltir (şok fiyatlarını yalnızca x86'ya yüklememek).

**Konuşmacı notu:** "Şok fiyatları bile x86'yı yalnızca %0,6 pahalılaştırıyor; çünkü bellek ve NVMe x86 maliyetinin küçük bir parçası. Şok asıl veri hacmi ekseninde görünür."

---

### Slayt KB-16.1 — Zaman ve finansman (NPV)

```
NPV = Σ_y [capex_y / (1 + r)^(y−1) + opex_y / (1 + r)^y] − kalan değer / (1 + r)^5
seviyelendirilmiş $/TPS-ay = NPV / Σ_y [12 × TPS_y / (1 + r)^y]
```

- 5 yıl; capex yıl başında, opex yıl sonunda; kalan değer 0; kapasite yalnızca yükselir.
- Teknoloji yenilemesi (z17 / yeni sunucu nesli) iki tarafta birlikte dışarıda.
- **r köşe senaryolarına girmez**, ayrı taranır (%5 / %7 / %10).

**Veri / kaynak:** [Damodaran2026-WACC] (piyasa %6,96, bilgisayar hizmetleri %7,83, bankalar %4,98).

**Tasarım gerekçesi:** Yüksek r mainframe'i hep ucuz gösterir (capex'i önde, opex'i büyük); köşe senaryosuna girseydi "low = mainframe lehine" tanımını bozardı.

**Konuşmacı notu:** "İskonto oranı bir belirsizlik değil, kurumun sermaye maliyeti; iki tarafta aynı olmak zorunda."

---

### Slayt KB-16.2 — KB-16: parametreler ve tutarlılık

| Parametre | Değer | Aralık | Dayanak |
|---|---|---|---|
| NPV_TPS_GROWTH | 0,10 | 0 / 0,05 / 0,10 / 0,20 | senaryo girdisi |
| SW_PRICE_ESCALATION | 0,03 | 0–0,06 | [Schneider2026-IBMPrice] IBM Z yazılımı 2026 +%6 |
| HW_SERVICE_ESCALATION | 0,03 | 0–0,06 | IBM TLS +%4–6 |
| WAGE_ESCALATION | 0,033 | 0,025–0,045 | [BLS2026-ECI] |
| ENERGY_ESCALATION | 0,04 | 0,015–0,056 | [EIA-EPM-5.3] |

- Mainframe'e özgü: TFP büyüme fiyatı 0,5 ("IBM mentions 50% discount for growth MSUs" [Kyne2022-TFP]).
- Tutarlılık testi iki modelde: r = 0, büyüme 0 → NPV = 60 × statik aylık.
- Etki (Demo Case 10): 10K TPS 5 yıl MF $71,01M / x86 $34,45M.

**Veri / kaynak:** kopruler_v1 KB-16; v3 §9.10.4; x86 dokümanı §15.

**Tasarım gerekçesi:** Artış oranları belirsiz fiyatlardır, aralığa girer; iki tarafın artış sınıfları aynı (x86 abonelikleri yazılım sınıfında).

**Konuşmacı notu:** "NPV statik sonucu değiştirmiyor; zaman değeri hesaba katıldığında da oran ~2."

---

### Slayt KB-17.1 — Enerji ve tesis

- Elektrik fiyatı ortak: $0,12/kWh [ASSUME]; artış KB-16.
- Mainframe: frame başına 30 kW (20–40 kW aralığının ortası); storage ve yedek için üretici tepe güçleri.
- x86: SPECpower %100 yük değeri × `X86_POWER_CONFIG_UPLIFT` 1,1 / 1,25 / 1,4 (SPECpower sistemleri az bellek ve diskle ölçülür).
- PUE, raf alanı ve storage ağı iki tarafta da dışarıda; AWS S3 hattı istisna (seçenek onsuz var olamaz).

**Veri / kaynak:** [Alibaba-MFPrice], [SPECpower-2025Q1] (DL380 Gen12 924 / 220 W; SR650 V4 782 / 218 W; R770 943–960 W).

**Tasarım gerekçesi:** Simetri: mainframe tepe güç kullandığı için x86'da da %100 yük değeri.

**Konuşmacı notu:** "Enerji iki tarafta da toplamın binde birkaçı; ama aynı fiyat ve aynı tepe-güç kuralıyla sayılıyor."

---

### Slayt KB-17.2 — KB-17: etki ve sınırlılık

- 10K TPS: mainframe enerji $2.628/ay (1 frame); x86 $189 (5 sunucu).
- Sınırlılık (mainframe): 39 CP üstü kademeler birden fazla drawer/raf ister; enerji frame başına sabit sayıldığı için büyük kademelerde eksik. IBM z16 IMPP resmî güç değerleri eklenmeli.
- PUE kapsam dışı olduğu için soğutma iki tarafta da yok; oranlar etkilenmez, mutlak düzey hafif düşük.

**Veri / kaynak:** v3 §7.4; x86 dokümanı §4.4.

**Tasarım gerekçesi:** İki tarafta birlikte dışarıda bırakılan kalem farkı değiştirmez; projenin kapsam kuralı.

**Konuşmacı notu:** "Enerji sonucu etkilemiyor; ama bunu varsaymadık, hesaplayıp gösterdik."

---

### Slayt KB-18.1 — Belirsizlik ve çıktı biçimi

- İki taraf aynı yapıda aralık verir: her parametre low / mid / high; köşe senaryoları + tek-parametre salınımı (tornado).
- Sonuç bir **crossover bölgesi**; iki eksen: TPS ve veri hacmi.
- Ek başlık çıktıları: başabaş personel oranı · personel hariç TCO · personel oranı 1,25 / 2,0.
- Diğer: DR payı, 2.200 TPS dış tutarlılık kontrolü, x86 donanım avantajının geri alındığı katmanlar, $/TPS testere dişi.
- **Eşleştirilmiş senaryolar:** platforma özgü zıt uçlarda, ortak parametreler aynı (kodlamada eklenen kural).

**Veri / kaynak:** kopruler_v1 KB-18; x86 dokümanı §14, §16.3.

**Tasarım gerekçesi:** Yayımlanmamış fiyatlar karşısında tek sayı yanıltıcı kesinlik verir; bölge, okuyucunun kendi koşullarını yerleştirebileceği bir harita.

**Konuşmacı notu:** "Demo Case 10'daki tablo: mid'de oran 2,05; mainframe lehine bütün belirsizliklerle 1,20; x86 lehine 6,80. Bu bir nokta değil, bir harita."

---

### Slayt KB-18.2 — Önerilerin yönü dengelidir

| Karar | Düzelttiği yanlılık | Yanlılık kimin lehineydi | Düzeltmenin etkisi |
|---|---|---|---|
| F (aralık okumaları) | Mainframe işlemi olduğundan hafif ölçülüyordu | mainframe | mainframe pahalanır (+%23) |
| P (ortak personel eğrisi) | Eski kuralda x86 personeli sunucu saatinden ~0 çıkıyordu | x86 | x86 pahalanır |
| C (uygulama katmanı) | x86'da işlem yöneticisinin karşılığı yoktu | x86 | x86 pahalanır |
| N (x86 üretim dışı) | x86 dev/test aralığı tanımsızdı | x86 | x86 pahalanır |
| U (x86 kullanım tavanı) | Literatürün %15–20 ucu çift sayımla ana senaryoya girecekti | mainframe | x86 ucuzlar |
| E (fiyat dönemi) | 2026 şok fiyatları yalnızca x86'ya yüklenecekti | mainframe | x86 ucuzlar |
| K (x86 köprüsü) | Tek, belgelenmemiş çapa | yönsüz | aralık genişler (60–120) |

- Sonuç: kararlar bir tarafı sistematik olarak kayırmıyor; iki yöndeki yanlılıklar da düzeltildi. Bu denge tezde yazılır.

**Veri / kaynak:** kopruler_v1 KB-18 son madde; karar kaydı §0.3.

**Tasarım gerekçesi:** Bir karşılaştırma çalışmasının güvenilirliği, düzeltmelerin yönünün dengeli olmasına bağlı; bunu tablo halinde göstermek iç geçerliliği savunur.

**Konuşmacı notu:** "Hocanın en olası sorusu 'tarafsız mısınız?'. Cevabımız bu tablo: yanlılıkları kimin lehine olduğuna bakmadan düzelttik; F, U ve E mainframe lehine olanları, P, C ve N x86 lehine olanları kaldırdı."
