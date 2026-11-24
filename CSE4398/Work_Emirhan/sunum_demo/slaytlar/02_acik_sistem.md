# Slayt İçeriği — Bölüm 2: Açık Sistem (Kümelenmiş x86) Katmanları ve Opsiyonları

> **Güncelleme notu (2026-11-24, Değerlendirme #10):** Bu dosyadaki sayılar Değ #10 öncesidir (ör. 10K TPS'te $113,93 / $53,66, başabaş 2,16). Güncel değerler: mainframe $117,92, x86 $57,65, başabaş 2,07; %99,999 + RPO 0'da yalnızca mainframe kurulabilir. Ayrıntı: `evaluations/2026-11-24_degerlendirme_10_kazanan_bolgeler.md`, `sunum_demo/DEMO_SENARYOLARI.md` Case 11-12. Slayt sayıları ayrıca yenilenecek.

*14 katman × 2 slayt. Sayılar `src/x86_model.py`'nin 2026-11-23 koşusundan ve `docs/x86_model_dokumantasyonu_v1.md`'den. Ana tasarım ilkesi: x86'nın kendi çalışma biçimine sadakat. Ortak olan ortak kurala bağlanır, yapısal fark eşitlenmez, modellenir.*

---

### Slayt X1.1 — Model ne çözüyor: dört karar değişkeni

- Mainframe'de karar (topoloji, kademe) çifti; x86'da dört değişken:
  1. **Yığın:** hipervizör × yerleşim × veritabanı (8 aday)
  2. **Topoloji:** X1–X4 (M1–M4 karşılıkları)
  3. **Sunucu boyutu:** katalogdan SKU (2×8c – 2×32c)
  4. **Oracle RAC düğüm sayısı** k (≤ 8)
- Her (yığın, topoloji) için en ucuz feasible (SKU, k); sonra hepsinin en ucuzu.
- Eleme nedenleri: topoloji DB'yi desteklemiyor, availability/RPO/RTO, kapasite, NVMe yuvası, yedek akışı.

**Veri / kaynak:** x86 dokümanı §0.1, §13.2.

**Tasarım gerekçesi:** Açık sistemde "tek doğru yığın" yok; bir kurum hipervizörü, orkestrasyonu ve veritabanını birlikte seçer. Model bunları sabitlemek yerine seçim motoruna bırakır, böylece x86'ya en elverişli kombinasyonla karşılaştırılır (mainframe'e karşı adil).

**Konuşmacı notu:** "x86 tarafını bir 'en kötü durum' yığınıyla değil, her girdi için en ucuz yığınla karşılaştırıyoruz. Mainframe'i de aynı şekilde: en ucuz kademe."

---

### Slayt X1.2 — İş yükü: aynı bileşim, göreli ağırlık

- Bileşim iki tarafta tek kaynaktan (`common_model.WORKLOAD_MIXES`): tpcb_like 1+0+4, oltp_rw 10+4+4, oltp_heavy 30+0+6.
- x86 çapası sysbench oltp_read_write'ın kendisi → oltp_rw göreli ağırlığı tanım gereği 1,00.
- Diğer profiller ifade maliyetleriyle: `birim = nokta + aralık × 3,65 + yazma × 3,9 + (commit + BEGIN) × 1,0`.
- Sonuç: tpcb_like 0,44 · oltp_rw 1,00 · oltp_heavy 1,31 (Demo Case 6: $26,95 / $53,66 / $63,45).
- I/O kuralları ortak: 2,8 senkron okuma + 1 WAL yazımı, 5,8 IOPS/işlem.

**Veri / kaynak:** [VONNG-PERF] alt testleri (yazma/nokta 3,65–4,15; BEGIN/COMMIT ≈ 1 nokta), [SYSBENCH]; x86 dokümanı §3.

**Tasarım gerekçesi:** KB-01: TPS iki tarafta aynı işi ifade etmeli. redp_light x86'da tanımsız, çünkü SQL içermiyor (CICS bellek tablosu).

**Konuşmacı notu:** "Mainframe w ile, x86 göreli ağırlıkla; ama ikisi de aynı SQL bileşiminden. Bir tarafta 'işlem' kelimesinin anlamı değişirse karşılaştırma çöker."

---

### Slayt X2.1 — Sunucu kataloğu ve fiyat fonksiyonu

- Tek referans sunucu (K5): Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3 sınıfı, Xeon 5. nesil (K2: z16 dönemi).
- Kaynaklı SKU: Xeon Gold 6548Y+ → SPECrate2017_int_base 628 / 64 çekirdek = 9,81/çekirdek; Intel RCP $4.173 / 32 çekirdek.
- `düğüm_net = (şasi + çekirdek × CPU/çekirdek + NIC/HBA) × (1 − indirim) + bellek × DRAM $/GB + NVMe × $/TB`; bellek = max(128, 8 × çekirdek) GB.
- Net bedel: 2×8c $11.189 · 2×16c $13.057 · 2×32c $16.794; 2×48c / 2×64c ekstrapolasyon.
- 5 yıl amortisman, 3 yıl garanti, sonra %12,5/yıl bakım.

**Veri / kaynak:** [SPEC-R760], [INTEL-ARK-6548Y], [PCSP-SERVER] (R760xs tabanı $15.957); x86 dokümanı §4.1–4.2.

**Tasarım gerekçesi:** İndirim yalnızca liste kalemlerine bir kez; bellek ve NVMe piyasa fiyatıyla, OEM indirimiyle birleştirilmez (fiyat tabanı kuralı, KB-15). Aynı ailede çekirdek başına SPECint sabit varsayımı küçük düğümlerde x86 aleyhine tutucu (az çekirdekli SKU'lar daha hızlı).

**Konuşmacı notu:** "Tek sunucu sınıfıyla çalışıyoruz; üretici farkı fiyat aralığında taşınıyor. Katalog bilerek 64 çekirdekte kesiliyor, çünkü kapasite çapamız 48 çekirdekte ölçülmüş."

---

### Slayt X2.2 — Güç ve fiyat dönemi; kalibrasyon kontrolü yapılamadı

- Güç: `(220 W platform + çekirdek × TDP/çekirdek) × 1,25`; SPECpower %100 yük değeri (mainframe tepe güç kullandığı için simetri).
- Fiyat dönemi: ana senaryo 2025-mid (DRAM $4/GB, NVMe $115/TB); duyarlılık 2026-Q3 (DRAM $35, NVMe $753: bellek/SSD şoku).
- 2026-Q3 etkisi küçük: 10K TPS $53,66 → $53,99 (bellek/NVMe x86 maliyetinin küçük payı).
- **KB-15 ±%20 kontrolü yapılamadı:** tek kaynak R760 "amiral" yapılandırma için $53.250 veriyor ama yapılandırmayı vermiyor; yalnızca bant kontrolü ($29.975 – $81.318 içinde).

**Veri / kaynak:** [SPECPOWER-2025Q1], [PCSP-SERVER], [PCSP-SSD], [CAPCOMP-RAM], [BACLOUD-RAM], [TRENDFORCE-2026-08]; x86 dokümanı §4.3–4.4, §13.4.

**Tasarım gerekçesi:** E kararı: iki tarafın çapaları aynı dönemde olmalı; şok sonrası fiyat yalnızca x86'da değişirse sonuç fiyat döneminin eseri olur. IBM fiyatlarının şoka tepkisi bilinmiyor → sınırlılık.

**Konuşmacı notu:** "Yapamadığımız bir kontrolü de açıkça yazıyoruz: yapılandırması belli bir kamu ihale kaydı bulunursa sunucu fiyatı ±%20 doğrulanacak."

---

### Slayt X3.1 — Kapasite köprüsü: SPECint başına TPS

- Çapa [VONNG-PERF]: AWS c5d.metal (2 × 8275CL, 48 fiziksel çekirdek), oltp_read_write 519.069 QPS / 20 ifade = 25.953 TPS.
- `25.953 / 48 / 5,94 (Cascade Lake SPECint/çekirdek) = 91,0 TPS / SPECint / çekirdek`.
- R760: 91 × 9,81 = 893 TPS/çekirdek (ham); sanallaştırma ve S(n) sonrası 2×8c'de 927.
- K kararı: çapa K6 kendi ölçümümüz olacak; o zamana kadar **120 / 91 / 60** (low = x86 lehine).
- Kaynakta yazmayanlar: PG sürümü (sysbench için), iş parçacığı, süre, istemci yeri, `synchronous_commit`/`fsync`.

**Veri / kaynak:** [VONNG-PERF], [SPEC-8270], [SPEC-R760]; x86 dokümanı §5.1–5.2; KB-03.

**Tasarım gerekçesi:** Mainframe'deki PCI köprüsünün x86 karşılığı; SPECint nesiller ve SKU'lar arası taşıyıcı. Aralık geniş tutuldu çünkü çapa tek ve ayarları belgelenmemiş.

**Konuşmacı notu:** "Proje gerekçesi 'benchmark koşturma kapsam dışı' diyor; K6 bununla çelişmiyor: model ölçümsüz de çalışıyor (60–120 aralığıyla), ölçüm yalnızca bir katsayıyı daraltacak."

---

### Slayt X3.2 — Düğüm içi ölçeklenme S(n) ve platformlar arası kontrol

- `S(n) = (n / 48)^(B_X86 − 1)`, B = 0,90 (0,80–1,00): 16 çekirdekte 1,116, 64'te 0,972.
- Kendi bulgumuz (köşe yönü düzeltmesi): n < 48'de küçük b x86 lehine → `X86_SCALING_LEVEL` her düğümde yön tutarlı ucu seçer (`test_scaling_corners_direction_consistent`).
- KB-04 kontrolü: 1 z16 CP (3931-701) × 7,939 / 12,85 = 1.392 TPS; R760 çekirdeği 893 → **1 CP ≈ 1,56 R760 çekirdeği**.
- IBM'in "1 CP = 24–80 x86 çekirdeği" iddiasının büyük kısmı kullanım oranından (U_R) ve dev/test kopyalarından; bizim köprümüz yalnızca performans oranını ölçer.

**Veri / kaynak:** [SHEDLETSKY-2008] konsolidasyon formülü; x86 dokümanı §5.3, §5.5; KB-04, KB-06.

**Tasarım gerekçesi:** İki köprü bağımsız zincirlerden (LSPR + REDP, SPEC + Vonng) gelir; bir mertebe hatası burada görünür. Bu doğrulama değil, büyüklük mertebesi kontrolü.

**Konuşmacı notu:** "IBM'in 24–80 çekirdek iddiasını çürütmüyoruz, ayrıştırıyoruz: performans 1,5 kat, gerisi kullanım oranı ve kopyalar. Onları da ayrı katmanlarda modelliyoruz."

---

### Slayt X4.1 — Yığın opsiyonları (8 aday)

| Hipervizör | Yerleşim | Veritabanı |
|---|---|---|
| vSphere Foundation | VM · VM içinde Kubernetes (Crunchy PGO) · VM içinde OpenShift | PostgreSQL + Patroni; Oracle yalnızca VM'de |
| OpenShift Virtualization Engine | VM · Kubernetes · OpenShift | aynı |

- Sanallaştırma ek yükü: vSphere 0,03 / **0,07** / 0,15; OCP-V 0,05 / **0,12** / 0,25; konteyner 0 / 0,02 / 0,05.
- Çekirdek başına TPS (2×8c): vSphere/VM 927 · vSphere/K8s 908 · OCP-V/VM 877 · OCP-V/K8s 859.
- Bare-metal Kubernetes yok (her zaman bir sanallaştırma katmanı, v4 §4.8).

**Veri / kaynak:** [PT-VSPHERE-OCPV-2024] [VENDOR], [REDHAT-OCPV-2025] [VENDOR], [EDB-LOCALPV]; x86 dokümanı §7.

**Tasarım gerekçesi:** İki rakip üreticinin kendi lehine ölçümleri arasından orta değer; ikisi de [VENDOR] olduğu için aralık geniş. Oracle'ın konteynerde RAC çalıştırması modellenmedi (bilinçli kapsam).

**Konuşmacı notu:** "Kurumların gerçekte seçtiği yığınlar bunlar. Demo Case 1'deki seçim motoru tablosu sekizini de sıralıyor; 10K TPS'te fark $536K ile $593K arası."

---

### Slayt X4.2 — Yığın seçiminin sonuçları ve Oracle verim çarpanı

- 10K TPS (%99,9): vSphere/VM/PG $536.552 = vSphere/K8s/PG (K8s'in %2 ek yükü SKU'yu değiştirmez) · OpenShift yerleşimi +%2,5 · OCP-V bir boy büyük SKU ister · Oracle +%7–11.
- 200K TPS'te OCP-V/VM/Oracle seçilir: düğüm başına OVE fiyatı çok büyük düğümde çekirdek başına vSphere'den ucuz.
- `ORACLE_THROUGHPUT_FACTOR` 1,30 / **1,00** / 0,80: kalibre edilemez. Oracle OTN lisansı "disclose results of any Program benchmark tests without Oracle's prior consent"i yasaklar.
- Orta değer 1,0 = kayıtsızlık ilkesi (kaynak yokken yön iddia edilmez).

**Veri / kaynak:** model koşusu (Demo Case 1 seçim motoru tablosu); [ORACLE-OTN]; x86 dokümanı §7, §13.3.

**Tasarım gerekçesi:** Yapısal bir veri sınırını uydurma bir sayıyla kapatmamak; tezde açık bir sınırlılık olarak yazmak.

**Konuşmacı notu:** "Oracle ile PostgreSQL'i aynı donanımda karşılaştıran bağımsız bir ölçüm yok, çünkü Oracle'ın lisansı yayımlanmasını yasaklıyor. Bu yüzden çarpanı 1,0 alıp aralıkta taşıyoruz."

---

### Slayt X5.1 — Ölçekleme mimarisi: Patroni tek yazıcı, RAC düğüm ekler

- **PostgreSQL + Patroni:** oltp_rw'nin her işlemi yazma içerir → bütün yük birincil düğümde; replikalar yazma kapasitesi eklemez. Kapasite yalnızca düğüm büyütülerek artar.
- Patroni tavanı: 2×32c × 807 TPS × 0,70 ≈ **35.900 TPS** (ekstrapolasyonla ~67.100).
- **Oracle RAC:** `ham_TPS(k) = düğüm_TPS × [1 + (k − 1) × 0,90]`, N+1 (k − 1 düğüm bütün yükü taşır), k ≤ 8; tavan ≈ 231.000 TPS.
- Mainframe tek CEC tavanı ≈ 132.700 TPS (F kararından sonra).

**Veri / kaynak:** [PATRONI-REPL], [ORACLE-RAC-2024] (%80 eşiği), [PGCON-2016]; x86 dokümanı §5.4; KB-06.

**Tasarım gerekçesi:** x86'nın kendi çalışma biçimi: paylaşımsız tek yazıcı ile paylaşımlı disk çok yazıcı arasındaki fark eşitlenmez, ayrı mekanizmalarla modellenir.

**Konuşmacı notu:** "Demo Case 2: 30K'da hâlâ PostgreSQL, 50K'da Oracle RAC. x86'nın kendi içinde bir crossover var: açık kaynak tavanı aşılınca ticari veritabanı zorunlu."

---

### Slayt X5.2 — Tavanların okunuşu ve RAC biçim duyarlılığı

- ~36K TPS'e kadar: mainframe ↔ PostgreSQL · ~36K – 133K: mainframe ↔ Oracle RAC · 133K üstü: yalnızca RAC feasible.
- Bu bölge iki modellenmeyen ölçekleme seçeneğinin (Parallel Sysplex data sharing, Citus) dışarıda bırakılmasının sonucu: iki tavan aynı statüde sınırlama.
- En ucuz RAC çoğu zaman çok sayıda küçük düğüm (50K'da 7 × 2×8c); gerçek kümeler 2–4 düğüm.
- `RAC_MAX_NODES` = 4 ile 50K'da personel hariç maliyet +%10; 130K infeasible.
- Açık iş: RAC ölçeklenmesi için USL biçiminde kaynak.

**Veri / kaynak:** x86 dokümanı §5.4, §18 (tehdit 3, 12).

**Tasarım gerekçesi:** Sabit marjinal verimli RAC formu Oracle'ın %80 eşiğiyle tutarlı ama çok düğümü cezalandırmıyor; bu bir biçim varsayımı olarak görünür tutuluyor.

**Konuşmacı notu:** "Yüksek hacim bölgesinde söylediklerimizi aralık olarak veriyoruz, çünkü orada sonuç kalibre edilemeyen iki RAC parametresine dayanıyor."

---

### Slayt X6.1 — Kullanım tavanı (U kararı)

- `ρ_max = min(ρ_latency, X86_UTIL_CEILING)`; tavan 0,90 / **0,70** / 0,50 (low = mainframe ile eşit).
- Gerekçe: x86'da WLM ve CoD karşılığı yok; veritabanı düğümleri tepe yükte boşlukla işletilir.
- %15–20 "konsolide edilmemiş park" ucu **ana aralıkta yok** (tepe boyutlama, HA replikaları ve dev/test zaten ayrı sayıldığı için çift sayım olur).
- Yalnızca karşılaştırmada ayrı bir satır: 10K TPS'te x86 $65,19'a çıkar ve Oracle RAC'a geçer; personel hariç hâlâ mainframe'in beşte biri.

**Veri / kaynak:** U kararı (Emirhan, 2026-11-16); [SHEDLETSKY-2008], `benzer_calismalar_v1` B1; x86 dokümanı §6.1, §16.4; KB-05.

**Tasarım gerekçesi:** IBM'in U_R etkisinin (kullanım oranı farkı) kontrolsüz biçimde sonuca girmesini önlemek; ama tamamen yok saymamak: uzlaştırma senaryosu olarak göstermek.

**Konuşmacı notu:** "IBM'in en güçlü argümanı x86'nın düşük kullanım oranı. Onu bile en uç haliyle koşturduğumuzda sıralama değişmiyor; değiştiren personel oranı."

---

### Slayt X6.2 — Latency: aynı kuyruk ailesi, ek ağ terimi

- `R(p) = D_ağ + D_io + D_repl + E[X] / (1 − ρ) × ln(1/(1 − p))` (çekirdek başına bağımsız M/M/1, mainframe ile aynı).
- D_ağ = 20 ifade × 0,15 ms = 3,0 ms (saklı yordamda 1 gidiş-dönüş).
- D_io: PG 2,8 × 141 µs + 60 µs WAL = 0,45 ms; Oracle SAN 0,85 ms. D_repl: Patroni X1/X2 0,21 ms, X3 0,41 ms.
- 10K TPS p99 ≈ 18,9 ms (mainframe M1 alt-kapasite CP'de ~89 ms); 20 ms hedefi seçimi değiştirmez (Demo Case 3).
- Sabit gecikmenin (~3,7 ms) altındaki hedefler infeasible.

**Veri / kaynak:** [STORAGEREVIEW-P5520] [VENDOR sponsorlu], [EDB-SYNCREP]; x86 dokümanı §6.2–6.3.

**Tasarım gerekçesi:** `project_context_restore_v4` x86 için M/M/c öngörüyordu; bu iki taraf arasında tutuculuk asimetrisi yaratırdı. Ağ terimi x86'ya özgü gerçek bir yapısal fark (CICS ve Db2 aynı sistemde), görünür bir parametre olarak tutulur.

**Konuşmacı notu:** "x86'da gecikmenin baskın terimi CPU değil ağ: uygulama sunucusu ile veritabanı arasındaki yirmi gidiş-dönüş."

---

### Slayt X7.1 — Topolojiler X1–X4

| Kod | Mainframe | Oracle (MAA) | PostgreSQL + Patroni |
|---|---|---|---|
| X1 | M1 | Silver: tek sitede RAC | Tek site 3 düğüm, 1 senkron replika |
| X2 | M2 | + uzak Data Guard (SYNC), elle geçiş | + uzak standby küme (asenkron), elle terfi |
| X3 | M3 | Gold: iki sitede RAC + ADG + FSFO | 2 + 2 düğüm, uzak senkron, DCS 3 sitede |
| X4 | M4 | Platinum: aktif-aktif + GoldenGate | **Infeasible** (K4) |

- X3/X4'te üçüncü sitede tanık düğümü (etcd üyesi / FSFO gözlemcisi).
- **Kendi düzeltmemiz:** Patroni X2'nin RPO'su 0 değil (standby küme asenkron) → 5 sn; RPO 0 isteyen PG X3'e gider (Demo Case 4'te bu yüzden Oracle seçiliyor).

**Veri / kaynak:** [ORACLE-MAA-2026], [PATRONI-MULTIDC] "run Patroni standby cluster in the second data center"; x86 dokümanı §8.1–8.2; KB-08.

**Tasarım gerekçesi:** Açık kaynak çekirdekte karşılığı olmayan bir topoloji uydurulmaz (K4); mainframe'deki "komik topoloji" kuralıyla tutarlı.

**Konuşmacı notu:** "Köprü dokümanında X2'nin RPO'su iki veritabanı için de sıfırdı. Kodlarken Patroni'nin kendi belgesine baktık ve düzelttik; bu düzeltme sonucun kendisini değiştiriyor."

---

### Slayt X7.2 — Availability denklemi ve sonuçlar

- `D = D_saha(T_kurtarma) [ortak] + λ_planlı × T_planlı + 12 yama switchover × T_sw + N_kesen × λ_düğüm × T_failover`.
- N_kesen: Patroni'de yalnızca birincil; RAC'ta hizmeti taşıyan her düğüm.
- Sonuçlar (PG): X1 %99,98275 · X2 %99,99499 · X3 %99,99917 · X4 PG infeasible (Oracle %99,99959).
- X1 M1'den biraz yüksek: tek frame'li M1'de planlı kesinti uzun, Patroni yamaları saniyelik switchover. Baskın terim iki tarafta da ortak saha olayı.

**Veri / kaynak:** [VISHWANATH-2010], [PIGSTY-RTO] (27–41 sn), [ORACLE-RAC-2024], [YELLOWBRICKS-HA]; x86 dokümanı §8.3–8.4; KB-07.

**Tasarım gerekçesi:** Saha olayları ortak modülde: iki platform aynı veri merkezinde, aynı fizikle maruz kalır; fark yalnızca kurtarma süresinden ve planlı işlemlerden gelir.

**Konuşmacı notu:** "'Mainframe daha güvenilir' sezgisi donanım için doğru, ama hizmet availability'sini veri merkezi olayları belirliyor; o yüzden iki taraf aynı topoloji sınıfında benzer sonuç veriyor."

---

### Slayt X8.1 — Lisanslar ve abonelikler

| Kalem | Kural | low / mid / high |
|---|---|---|
| vSphere Foundation | çekirdek/yıl; CPU başına ≥ 16, sipariş ≥ 72 çekirdek | $100 / $150 / $350 |
| OpenShift Virt. Engine | düğüm/yıl | $6K / $8K / $10K |
| RHEL for Virtual DC | düğüm/yıl | $2.904 |
| OpenShift Container Platform | 2 çekirdek/yıl (sanal düğüm) | $2K / $3K / $4,2K |
| Oracle EE + RAC + paketler | işlemci = çekirdek × 0,5; destek %22/yıl | indirim %60 / %45 / %20 |
| PostgreSQL ticari destek | çekirdek/yıl | $0 / $500 / $1.500 |

- vSphere asgarileri küçük düğümde belirleyici: 2×8c sunucu 32 çekirdek olarak lisanslanır.
- 10K TPS PG yığınının bütün abonelikleri $5.210/ay (mainframe AWLC $402.932).

**Veri / kaynak:** [ACEMQ-VVF], [ACEMQ-RENEW], [CDW-OVE], [CCSP-RH], [RH-OCP-GUIDE], [REDRESS-PL2026] (doğrulanmalı), [ORACLE-CORE], [REDRESS-GG]; x86 dokümanı §9.

**Tasarım gerekçesi:** Fatura tabanı farkı (R4HA tüketim vs kurulu çekirdek) gerçek ve yapısal; eşitlenmez, modellenir (KB-11).

**Konuşmacı notu:** "Personel hariç tutulduğunda iki platform arasındaki 40 katlık farkın neredeyse tamamı bu slayttan geliyor: lisans modeli. Tezin en büyük yapısal bulgusu bu."

---

### Slayt X8.2 — Yapısal asimetriler ve kendi düzeltmemiz

- DR sitesi: mainframe CBU (kalıcı küçük kapasite) ↔ x86 tam lisans (`test_dr_sites_fully_licensed`).
- Geçici kapasite: mainframe On/Off CoD, TFP ↔ x86 karşılığı yok, kurulu çekirdeğin lisansı boşta da ödenir.
- Oracle: VMware yumuşak bölümleme → VM'in çalışabileceği bütün çekirdekler lisanslanır; model adanmış düğüm varsayar. GoldenGate ADG'yi içerir (X4'te ayrıca sayılmaz).
- **Düzeltme (KB-11):** OpenShift soket çifti aboneliği yalnızca bare-metal içindir; sanal düğümler çekirdek tabanlı → `OCP_USD_PER_COREPAIR_YEAR`.

**Veri / kaynak:** [CBU], [ORACLE-PART], [RH-OCP-GUIDE] "Each physical, bare-metal server using socket-based entitlements can only be used as a single OpenShift node."; x86 dokümanı §9.1, §9.3.

**Tasarım gerekçesi:** Asimetriler tek tek isimlendirildiği için okuyucu her birinin hangi tarafı nasıl etkilediğini görebilir.

**Konuşmacı notu:** "Köprü dokümanından dört noktada saptık, hepsini gerekçesiyle yazdık. Bu ikisi lisansla ilgili."

---

### Slayt X9.1 — Uygulama katmanı (C kararı)

- Mainframe CPU'su ve lisansı CICS'i (işlem yöneticisi) içerir; x86 çapasında uygulamanın yerini sysbench istemcisi tutar → mainframe aleyhine kapsam asimetrisi.
- `TM_payı = 85,9 / CPU(oltp_rw) = %7,8`; `uygulama_çekirdekleri = DB_çekirdekleri × TM_payı / (1 − TM_payı)`.
- Linux VM olarak fiyatlanır (donanım + hipervizör + RHEL/OpenShift); açık kaynak uygulama sunucusu, ek lisans yok.
- Site başına N+1 (en az 2 host); DR sitesinde kopya.

**Veri / kaynak:** [REDP-PROFILE] CPU_US_TM_BASE 85,9 µs; [SHEDLETSKY-2008] 4,9 kat iddiası (yalnızca üst uç duyarlılık); x86 dokümanı §10; KB-12.

**Tasarım gerekçesi:** İki tarafın kapsam sınırı aynı olmalı. Bu katman ağ gidiş-dönüşü terimini de doğal kılar (uygulama veritabanından ayrı düğümde).

**Konuşmacı notu:** "Mainframe'in faturasında CICS var; x86'nın faturasında uygulama sunucusu yoksa mainframe haksız pahalı görünür. Bu katmanı o yüzden ekledik."

---

### Slayt X9.2 — Uygulama katmanının büyüklüğü ve kendi bulgumuz

- 10K TPS: 0,9 meşgul çekirdek → N+1 gereği 2 × 2×8c host; toplamın %0,3'ü (personel hariç maliyetin %12'si).
- Kendi bulgumuz: ilk sürümde tavan ve sanallaştırma ek yükü uygulama çekirdeğine iki kez uygulanıyordu; düzeltildi, tavan yalnızca host boyutlamasında bir kez (`test_app_tier`).
- Sınırlılık: yalnızca CPU payıyla boyutlanıyor; bellek ve oturum sayısı yok.

**Veri / kaynak:** model koşusu; x86 dokümanı §10, §18 (tehdit 10).

**Tasarım gerekçesi:** Küçük bir kalem ama eksikliği bir kapsam yanlılığı; test ile çift sayıma karşı korunuyor.

**Konuşmacı notu:** "Etkisi küçük, ama 'eşit derinlik' ilkesinin bir örneği: büyüklüğüne bakmadan iki tarafın aynı katmanları içermesini sağladık."

---

### Slayt X10.1 — Storage: tipi veritabanı mimarisine bağlı (K1)

| DB | Storage | Kopya |
|---|---|---|
| PostgreSQL + Patroni (paylaşımsız) | Her düğümde yerel NVMe | Düğüm sayısı kadar tam kopya |
| Oracle RAC (paylaşımlı disk) | Site başına all-flash dizi (ASM) | Site başına bir dizi |

- PG: `ham = planlı_veri × PG_BLOAT_FACTOR (1,3)`; sürücü = max(4, kapasite, IOPS); ≤ 24 yuva → ~373 TB bugünkü veri üstünde PG elenir.
- AFA: etkin TB teklifleri önce ham TB listesine çevrilir (`liste_etkin × 0,75 × DRR 2,5`), indirim bir kez (%50); birincilde %25 değiştirilemez anlık kopya (Safeguarded Copy karşılığı).

**Veri / kaynak:** [EDB-LOCALPV] (yerel PV −%3,6 / −%0,8; ağ PV −%89–95), [VENDORBENCH-AFA]; x86 dokümanı §11.1–11.3; KB-09.

**Tasarım gerekçesi:** Fiyat sözleşmesi iki tarafta aynı (ortak modül §6): veri azaltımı boyutlandırmada bir kez, fiyata ikinci kez gömülmez.

**Konuşmacı notu:** "Demo Case 5: 500 TB'ta PostgreSQL'in yerel diskleri yetmiyor, model Oracle ve paylaşımlı diziye geçiyor. Storage burada veritabanı seçimini değiştiriyor."

---

### Slayt X10.2 — Yedek: aynı hacim kuralı, aynı fiyat fonksiyonları

- Hacim ortak (`common_model.backup_volumes`): 4 haftalık tam + günlük artımlı (%3) + log; iki site.
- Hedefler: on-prem nesne depolama, AWS S3 (TS7770 x86'ya uygulanmaz); fiyat fonksiyonları mainframe ile aynı.
- x86'ya özgü: WAL full-page write `WAL_FPW_FACTOR` 1,5 / 2 / 3; sıkıştırma 3,0 / 2,0 / 1,5 (pgBackRest zstd, RMAN).
- Kısıtlar mainframe ile aynı: 8 saatlik pencere, X1'de geri yükleme ≤ 36 sa, akış 5.000 MB/s.
- 10K TPS / 20 TB: nesne depolama, $4.917/ay; 10 TB'ta S3 ($4.555).

**Veri / kaynak:** [MINIO-TCO], [AWS-S3-2026]; x86 dokümanı §11.4; KB-10.

**Tasarım gerekçesi:** Yedek yazılımı lisans gerektirmez (pgBackRest açık kaynak, RMAN EE'ye dahil). Sıkıştırma asimetrisi bir platform özelliği, küçük etkili ve açıkça yazılı.

**Konuşmacı notu:** "Yedek iki tarafta aynı formülle hesaplanıyor; tek fark platformların kendi araçlarının yaptığı şeyler, WAL'ın full-page write'ı gibi."

---

### Slayt X11.1 — Personel: ortak eğri × oran

- `FTE_x86 = FTE_ortak(TPS) × STAFF_RATIO_X86`; ana senaryoda oran **1,0** (nötr), aralığa girmez.
- 10K TPS: iki tarafta da 38,6 FTE, $521.333/ay.
- Elenen x86 değişkenleri: sunucu başına 32 saat, imaj başına 36 saat, DBA saati, yığın çarpanı.
- Duyarlılık: 1,25 (konsolide x86 vakaları) ve 2,0 (bütün FTE vakaları), IBM kaynaklı ve yanlılık notuyla.

**Veri / kaynak:** [IBM-EAGLE-LABOR], [IBM-TPF-2007], [SHEDLETSKY-2008], [IDC-2007], [AVASANT-2008]; x86 dokümanı §12.1; KB-13.

**Tasarım gerekçesi:** Mainframe ortalaması MIPS başına, x86 ortalaması sunucu başına; doğrudan oranlanırsa ~1.300 katlık anlamsız bir fark çıkar (farklı yoğunlukta parkları ölçüyorlar). Ortak eğri bu ölçüm farkını ortadan kaldırır.

**Konuşmacı notu:** "Personel kaynaklarındaki yüksek oranlar dağınık x86 parklarından geliyor; sunucu sayısını biz zaten modelliyoruz, o oranı almak sunucu yayılmasını iki kez saymak olur."

---

### Slayt X11.2 — Üretim dışı ortamlar (N kararı)

- `nonprod = NONPROD_FACTOR_X86 × birincil site {yazılım + donanım + enerji + birincil storage}`.
- 0 / **0,50** / 1,00; stres 2,0 (IBM "+%200").
- Orta değerin türetmesi: X1'de birincil 3 düğüm; üretim boyutunda tek düğümlük staging ≈ 0,33 + küçük dev/test ≈ 0,1–0,2.
- Oracle'da üretim dışı da çekirdek lisansı ister (OTN geliştirme lisansı yalnızca saf geliştirme).
- 10K TPS: $3.434; stres senaryosunda x86 $54,69 (+%1,9).

**Veri / kaynak:** [IBM-EAGLE-2013]; x86 dokümanı §12.2; KB-14.

**Tasarım gerekçesi:** Mainframe'den ayrı çarpan, çünkü yapı farklı: mainframe'de dev/test aynı CEC'te LPAR, x86'da ayrı düğüm.

**Konuşmacı notu:** "x86'nın üretim dışı oranı mainframe'den yüksek (0,5'e karşı 0,2), ama tabanı küçük olduğu için toplamda önemsiz."

---

### Slayt X12.1 — Toplam maliyet ve seçim motoru

- Düğüm grubu (rol × site) başına: yazılım + donanım (/60 ay) + bakım (garanti sonrası) + enerji; + storage + yedek + personel + üretim dışı.
- Oracle lisansı statik modda 5 yıla amortismanlanır + %22 destek.
- Maliyet/TPS eğrisi (mid): 1K $118,98 · 10K $53,66 · 30K $38,41 · 50K $35,25 (Oracle) · 100K $29,03 · 200K $24,45.
- Personel payı %87–98: x86 aralığını personel eğrisi ve ücret belirler.

**Veri / kaynak:** model koşusu (Demo Case 1, 2); x86 dokümanı §13.1–13.3.

**Tasarım gerekçesi:** Tüm kalemler aynı aylık birimde, mainframe'in kalem yapısıyla eşlenik (karşılaştırma tablosu birebir okunabilir).

**Konuşmacı notu:** "x86'nın personel hariç maliyeti 10K TPS'te ayda 15 bin dolar. Bu yüzden x86 tarafında her şey personele indirgeniyor."

---

### Slayt X12.2 — Personel hariç maliyet Patroni tavanında kırılır

- 30K TPS'e kadar PostgreSQL lisanssız: personel hariç $14,96 (1K) → $0,91/TPS (30K).
- Tavanın üstünde Oracle RAC zorunlu: lisans ve destek personel hariç maliyeti ~3 katına çıkarır ($3,08 @ 50K).
- %99,999 (X3) yığın tablosu, 10K TPS: vSphere/PG $61,83 … OCP-V/Oracle $73,05.
- Bu, mainframe karşılaştırmasından bağımsız, x86'nın kendi yapısal crossover'ı (açık kaynak ↔ ticari).

**Veri / kaynak:** x86 dokümanı §13.3.

**Tasarım gerekçesi:** Seçim motorunun ara çıktıları (yığın tablosu) okuyucunun "neden bu yığın" sorusunu cevaplar.

**Konuşmacı notu:** "Bu grafik x86 tarafının kendi hikâyesi: veritabanı seçimi hacimle değişiyor ve maliyet yapısını değiştiriyor."

---

### Slayt X13.1 — NPV kuralları (x86'ya özgü)

- Ortak kurallar: 5 yıl, %7, yük %10/yıl, capex başta, opex sonda, kalan değer 0.
- Yığın ve topoloji 1. yılda seçilir, **bütün yolu feasible taşıyabilen** adaylar arasından (Patroni tavanını 5. yılda aşacak PG yolu seçilemez).
- Yükseltme: düğüm büyütme (CPU değişimi + bellek; eski CPU geri kazanılmaz) ya da RAC'a düğüm ekleme; Oracle lisansı artan işlemci kadar ek alım.
- Bakım her alımın 3 yıllık garantisi bittikten sonra.
- Tutarlılık: r = 0, büyüme 0 → NPV = 60 × statik aylık (1e-9 hassasiyet, `test_npv_consistency_and_direction`).

**Veri / kaynak:** x86 dokümanı §15.1; KB-16.

**Tasarım gerekçesi:** Mainframe'de topoloji kapasiteyi değiştirmez, x86'da yığın kapasiteyi belirler; bu yüzden yol-feasibility kuralı yalnızca x86'da gerekli (köprü dokümanında olmayan ek kural, gerekçesiyle kaydedildi).

**Konuşmacı notu:** "NPV iki tarafta aynı fonksiyonla indirgeniyor; x86'ya özgü olan yalnızca nasıl büyüdüğü."

---

### Slayt X13.2 — NPV sonuçları ve yıllık mod

- 10K TPS, 5 yıl: x86 NPV $32,07M, seviyelendirilmiş $54,07 (mainframe $68,62M, $115,70).
- Yol: 1. yıl 2×8c; 2. yılda 2×12c'ye CPU değişimi; 4. yılda ikinci storage döngüsü. NPV'nin %97,2'si personel.
- Ufuk 3 / 5 / 10 yıl: $54,14 / $54,07 / $54,47 (neredeyse sabit; Demo Case 10).
- Yıllık mod: CoD karşılığı yok, kapasite tepeye kurulur. retail_bursty (tepe 35K): x86 $15,36M, mainframe (TFP) $29,28M.
- retail_bursty'nin 35K tepesi Patroni tavanına çok yakın; biraz daha dalgalı profil x86'yı Oracle'a iter.

**Veri / kaynak:** model koşusu; x86 dokümanı §15.2–15.3.

**Tasarım gerekçesi:** Mainframe'in CoD/TFP avantajı (dalgalı yükte düşük ortalama fatura) burada görünür: retail_bursty'de x86 statik 10K maliyetinin 2,4 katı, mainframe 2,1 katı. Ama sıralamayı değiştirmez.

**Konuşmacı notu:** "Mainframe'in esneklik avantajı gerçek ve modelde görünüyor; yalnızca x86'nın personel hariç maliyeti o kadar küçük ki farkı kapatmaya yetmiyor."

---

### Slayt X14.1 — Mainframe ile karşılaştırma: mid sonuçlar

| Availability | TPS | Mainframe $/TPS | x86 $/TPS | Başabaş personel oranı |
|---|---|---|---|---|
| %99,9 | 1.000 | 291,89 (M1) | 118,98 (PG X1) | 2,66 |
| %99,9 | 10.000 | 113,93 (M1) | 53,66 (PG X1) | 2,16 |
| %99,9 | 50.000 | 68,89 (M1) | 35,25 (Oracle X1) | 2,05 |
| %99,99 | 10.000 | 122,29 (M2) | 56,78 (PG X2) | 2,20 |
| %99,999 | 10.000 | 143,97 (M4) | 61,83 (PG X3) | 2,37 |

- Mid'de x86 bütün noktalarda ucuz; başabaş oranı 2,0 – 3,6.
- Personel hariç fark 8 – 42 kat; kaynağı neredeyse bütünüyle yazılım lisans modeli.

**Veri / kaynak:** model koşusu (`--compare`); x86 dokümanı §16.2.

**Tasarım gerekçesi:** `compare()` aynı girdiyle iki modeli çözer; başabaş oranı ikiye bölmeyle ve her adımda x86 yığını yeniden optimize edilerek bulunur.

**Konuşmacı notu:** "IBM'in konsolide vakaları (~1,25) eşiğin altında, bütün FTE vakalarının ortalaması (2,0) eşiğin hemen altında. Mainframe'in kazanması için x86 personelinin dağınık parklar kadar kalabalık olması gerekiyor."

---

### Slayt X14.2 — Eşleştirilmiş senaryolar: crossover bölgesi

| TPS | x86 lehine (BE) | orta (BE) | mainframe lehine MF / x86 (BE) |
|---|---|---|---|
| 10.000 | 383,08 / 52,95 (7,33) | 113,93 / 53,66 (2,16) | 70,49 / 57,92 (1,24) |
| 30.000 | 345,99 / 37,78 (9,22) | 78,31 / 38,41 (2,06) | **47,98 / 56,12 (0,78)** |
| 50.000 | 335,72 / 32,37 (10,43) | 68,89 / 35,25 (2,05) | **40,60 / 50,98 (0,68)** |

- Platforma özgü parametreler zıt uçlarda, **ortak parametreler iki tarafta aynı** (`CROSS_BRIDGE_WEIGHTS` = reference).
- 30K–50K'da mainframe lehine senaryoda mainframe personel nötrken de ucuz: x86 high köşesinde Patroni tavanı ~15K'ya iner, Oracle'ın high köşesi lisansı patlatır.

**Veri / kaynak:** model koşusu (`--compare --range`); x86 dokümanı §16.3.

**Tasarım gerekçesi:** İki platformun kendi köşelerini ayrı ayrı okumak personeli bir tarafta low, öbür tarafta high yapardı (P kararıyla çelişir). İlk koşuda tam bu hata görüldü: x86 $53,66'dan $89,49'a çıkmıştı; düzeltildi (`test_paired_comparison_scenarios`).

**Konuşmacı notu:** "Tezin başlık cümlesi: mid varsayımlarla ve nötr personelle x86 ~2 kat ucuz; mainframe'in kazandığı bölge ya x86 personelinin ~2 katı aşması ya da bütün belirsizliklerin mainframe lehine çözülüp yükün 15–36K TPS'lik Patroni tavanını aşması."
