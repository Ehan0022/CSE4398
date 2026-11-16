# Değerlendirme #9 — x86 Modeli ve F/E/P Kararlarının Uygulanması (Adım 7)

*Tarih: 2026-11-16 · İncelenen: `src/x86_model.py` (yeni), `src/common_model.py` ve `src/mainframe_model.py` (F, E, P değişiklikleri), `docs/x86_model_dokumantasyonu_v1.md` (yeni), `docs/mainframe_model_documentation_v3.md` §7.6–7.11, `docs/ortak_modul_dokumantasyonu_v1.md`, `docs/kopruler_v1.md` ile karşılaştırma · Testler: x86 24/24, mainframe 30/30*

Bu değerlendirme, köprü kararlarından (Değerlendirme #8 §5, `kopruler_v1.md`) sonra yazılan ilk x86 modelini ve kararların mainframe tarafına etkisini inceler. Üç soru soruldu: (1) x86 modeli x86'nın kendi çalışma biçimine sadık mı, ve mainframe modeliyle aynı titizlikte mi? (2) Değerlendirme #8'in tehditlerinden hangileri kapandı? (3) İlk karşılaştırma sonuçları neyi gösteriyor ve neye koşullu? Orijinal tasarım dokümanları ve `kopruler_v1.md` düzenlenmedi.

Önem dereceleri #8 ile aynıdır: **Kritik** = düzeltilmezse crossover'ın yerini tek başına belirleyebilir · **Önemli** = sonucu ölçülebilir biçimde kaydırır ya da savunmada zayıf nokta olur · **Küçük** = metin ya da tutarlılık düzeltmesi.

---

## 1. Kısa Sonuç

1. **Mainframe başlığı yükseldi: 10K TPS'te $93,10'dan $113,93/TPS/ay'a (+%22).** Nedeni F (aralık okumaları w'yi 9,15'ten 12,85'e çıkarır) ve P'dir (personel iş yükünün PCI eşdeğerinden, 38,6 FTE). Aralık $31,44 / $113,93 / $565,95; NPV $68,62M, seviyelendirilmiş $115,70. Tek z16'nın oltp_rw tavanı ~187K'dan ~132,7K TPS'e indi. Yıllık simülasyonda TFP üç ön ayarın üçünde de kazanır; retail_bursty'de fark %0,1'dir, yani pratikte eşitliktir.
2. **x86 modeli kuruldu ve x86'nın kendi mekanizmalarını modelliyor.** Sunucu kataloğu, Linux, vSphere / OpenShift Virtualization, VM / Kubernetes / OpenShift yerleşimi, PostgreSQL Patroni (tek yazıcı) ve Oracle RAC (N+1, marjinal verim), SAN ile yerel NVMe × RF, X1–X4, çekirdek ve düğüm tabanlı lisans minimumları, aylık yama switchover'ları, uygulama katmanı, yedek, üretim dışı ortamlar, aralık, tornado, NPV ve yıllık mod. Sonuç 10K TPS'te $53,66/TPS/ay (PG Patroni X1, 3 × 2×8c + 2 uygulama düğümü). Aralık $22,01 / $53,66 / $124,91; NPV $32,07M.
3. **Mid'de x86 bütün hacimlerde ~2 kat ucuzdur; başabaş personel oranı 2,0–3,6'dır.** Personel nötrken (oran 1,0) x86 kazanır. Mainframe'in kazanması için x86 personelinin mainframe personelinin ~2,2 katını aşması gerekir. IBM'in aynı iş yükü vakalarının FTE geometrik ortalaması 2,0'dır, yani eşik vakaların hemen üstündedir. Başlık sonucu bu yüzden personel oranına **koşullu** yazılmalıdır.
4. **Personel hariç fark 8–42 kattır ve büyük kısmı yazılım lisans modelinden gelir** (10K TPS'te AWLC $402.932/ay, PostgreSQL yığınının abonelikleri $5.210/ay). Bu, araştırmanın en büyük yapısal bulgusudur ve personelden ayrı raporlanmalıdır.
5. **Crossover bölgesi var ama dar ve koşulludur.** Eşleştirilmiş "mainframe lehine" senaryoda (x86'ya özgü bütün belirsizlikler high, mainframe'e özgü olanlar low) 30K ve 50K TPS'te mainframe personel nötrken de ucuzdur (başabaş 0,78 ve 0,68). Mekanizma Patroni tavanıdır: x86 high köşesinde tavan ~15K TPS'e iner, üstü Oracle RAC'ın high fiyatlarıyla karşılanır.
6. **Kodlama sırasında dört köprü düzeltmesi ve dört model hatası bulundu.** Hepsi kodda düzeltildi ve x86 dokümanının §17'sinde gerekçesiyle kaydedildi. `kopruler_v1.md` bu düzeltmeleri alacak bir v2'ye ihtiyaç duyar (§3.3).

---

## 2. Değerlendirme #8'den Kapanan ve Açık Kalan Tehditler

| #8 tehdidi | Durum | Nasıl |
|---|---|---|
| §2.1 Personel köprüsü iki tarafta farklı birim (Kritik) | **Kapandı (P)** | Ortak eğri, girdi iş yükünün PCI eşdeğeri; x86'ya özgü personel değişkeni yok; `STAFF_RATIO_X86` = 1,0; başabaş oranı ve personelsiz TCO başlık çıktısı (ortak modül §12, x86 §12, §16) |
| §2.2 Kapasite çapası belgelenmemiş tek ölçüm | **Kısmen (K).** Ara aralık 60 / 91 / 120 TPS/SPECint aralık parametresi; çapa K6'ya kadar Vonng | K6 ölçümü yapılmadı; x86 §18 tehdit 1 |
| §2.3 Aralık okuması nokta okumayla eşit sayılıyor | **Kapandı (F)** | `RANGE_READ_WEIGHT` 3,4 / 3,65 / 3,9 ortak aralık parametresi; mainframe w 12,85; KB-04 oranı 2,19 → 1,56 (kaynak aralığı 1,52–1,60 içinde) |
| §2.4 x86 kullanım alt ucu %15–20 çift sayım | **Kapandı (U)** | İki tarafta `rho = min(rho_latency, tavan)`; x86 tavanı 0,9 / 0,7 / 0,5; %17,5 yalnızca ayrı "konsolide edilmemiş park" senaryosu |
| §2.5 Fiyat dönemi x86 aleyhine, bellek iki kez aralıklı | **Kapandı (E)** | Ana senaryo `2025-mid`; her dönemde low / mid / high üçlüsü; tek `COMPONENT_PRICE_LEVEL`; 2026-Q3 duyarlılık (10K: $53,66 → $53,99) |
| §2.6 Patroni tavanı SKU'ya bağlı | **Kapandı.** Tavan "katalogdaki en büyük düğüm × S(n) × tavan" olarak türetiliyor: 2×32c'de ~35,9K TPS; 96–128 çekirdek `--allow-extrapolation` ile ~67,1K | Tavan üstü bölge RAC'ın kalibre edilemeyen parametrelerine dayanır; x86 §18 tehdit 2–3 |
| §2.7 CICS ile uygulama katmanı asimetrisi | **Kapandı (C)** | Uygulama katmanı = DB meşgul çekirdekleri × TM / (1 − TM), Linux VM, ek lisans yok; 10K TPS'te personel hariç maliyetin %12'si |
| §3.1 1 CP = 1.955 TPS zIIP'i dışarıda bırakıyor | **Kapandı** | Kalibrasyon çıktısı GP + zIIP motorunu birlikte sayar (`ZIIP_ENGINE_PCI`) |
| §3.1 Cascade Lake → R760 1,65 katının bir kısmı bellek bant genişliği ve derleyiciden | **Sınırlama olarak yazıldı** | x86 §18 tehdit 15; K6 hedef nesilde yapılırsa kapanır |
| §3.2 Bileşen fonksiyonu Dell listesine ±%20 kalibre edilmeli | **Yapılamadı** | Kaynak yapılandırmayı vermiyor; yalnızca dönem bandı kontrolü (x86 §4.3, KB-15 sapması) |
| §3.2 RHEL VDC hizmet sağlayıcı fiyatı | **Kapandı** | Kaynak notu katalogda |
| §3.3 PostgreSQL MVCC şişmesi platforma özgü olmalı | **Kapandı** | `PG_BLOAT_FACTOR` 1,1 / 1,3 / 1,6 |
| §3.3 Yerel NVMe'de RAID düzeyi | **Varsayım olarak yazıldı** | Düğüm içi RAID yok, replika kopyası yeterli (x86 §18 tehdit 11) |
| §3.4 Aylık yama switchover'ları | **Kapandı** | 12 switchover × 5 / 15 / 30 sn (PG), 0 / 5 / 15 sn (Oracle) |
| §3.4 RPO kuralı (WAL arşivi) iki tarafta | **Açık, tutarlı.** X1 ve M1 birlikte 24 saatte | Değişiklik iki tarafta birlikte yapılmalı |
| §3.5 x86 üretim dışı aralığı | **Kapandı (N)** | 0 / 0,5 / 1,0; 2,0 stres senaryosu (10K: +%1,9) |
| #7'den: Üretim dışı orta değer için IBM dışı kaynak | **Açık** | x86 mid değeri yapısal türetme [DERIVED, ASSUME]; mainframe mid hâlâ tek üretici kaynağı |
| #7'den: Fiyat dönemi mainframe fiyatlarına uygulanmıyor | **Kapandı (E) / sınırlama** | Ana senaryoda iki taraf şok öncesi; 2026-Q3'te yalnızca x86 değişir ve bu yazılıdır |
| #7'den: K6 ile justification §5.2 gerilimi | **Açık, görünür** | x86 §5'te açıkça yazıldı; justification düzenlenmedi |
| #7'den: Strateji sonucunun ince farka dayanması | **Açık, yer değiştirdi** | Adım 7'de steady'de C %2,1 önde; ince fark retail_bursty'ye geçti (C, B'den %0,1 ucuz) |
| #8 yeni: tavan üstünde RAC'ın iki kalibre edilemeyen parametresi | **Açık** | Tornado'da görünür; `RAC_MAX_NODES` = 4 duyarlılığı (x86 §18 tehdit 3) |

---

## 3. Yeni Bulgular

### 3.1. Sonucu personel oranı belirliyor (Kritik, bilinçli)

P kararı personeli nötrleştirdi; bu doğru bir metodolojik seçimdir, çünkü bağımsız ve platformlar arası oranlanabilir bir personel verisi yoktur (`kopruler_v1.md` KB-13). Ama bunun sonucu, kararın kendisinin başlık bulgusunu belirlemesidir: personel hariç fark büyük olduğu için oran 1,0'da x86 her yerde kazanır, oran ~2,2'de taraflar eşitlenir. Tez "x86 ucuzdur" demek yerine şunu demelidir: **"x86'nın altyapı personeli mainframe'inkinin ~2,2 katından azsa x86 ucuzdur."** Bu cümle hem IBM'in iddiasıyla (dağıtık ortam daha kalabalık ekip ister) hem de göç literatürüyle (personel tasarrufu sayısal verilmez) çelişmeden savunulabilir. Başabaş oranı bu yüzden tek sayı değil, TPS ve availability'ye göre bir tablodur (x86 §16.2: 2,05–3,62).

**Yapılacak:** Tezin sonuç bölümü başabaş oranını ana çıktı olarak sunmalı; 1,25 ve 2,0 duyarlılıkları IBM'in vaka kaynaklı ve üretici yanlılığı taşıyan değerler olarak etiketlenmeli.

### 3.2. Yazılım lisans modeli yapısal farkın kaynağı (Önemli)

Personel hariç toplamda mainframe 10K TPS'te $617.961/ay, x86 $15.219/ay öder (40,6 kat). Farkın ~%80'i AWLC ve onun üretim dışı payıdır. x86 tarafında Oracle seçildiğinde (> ~36K TPS) fark 8–12 kata iner; PostgreSQL bölgesinde 13–42 kattır (x86 §16.2). Bu bulgu iki şeye duyarlıdır: AWLC'nin mutlak seviyesi (`SW_PRICE_LEVEL_FACTOR`, 2004 nominal fiyatlardan) ve L4+ kademe fiyatları; ikisi de mainframe tarafında zaten en üst sıradaki belirsizliklerdir (v3 §7.8). Gerçek bir IBM teklifi geldiğinde iki fiyat modu ile (`--prices`) bu fark doğrudan daraltılabilir.

**Akademik not:** Bu, "mainframe pahalıdır" iddiasının bir tekrarı değildir; mekanizmayı ayrıştırır. Fark donanımdan (personel hariç maliyetin küçük payı) ya da storage'dan değil, yazılımın MSU başına fiyatlanmasından gelir. Tez bu ayrıştırmayı ayrı bir tabloyla vermelidir.

### 3.3. Köprüler dokümanında dört düzeltme (Önemli)

Kodlama, köprüler dokümanının dört noktasının x86'nın çalışma biçimine ya da kaynağa uymadığını gösterdi (x86 §17):

1. **KB-08:** Patroni'nin iki siteli X2'si asenkron standby kümedir [PATRONI-MULTIDC]; RPO 0 değil 5 sn [ASSUME]. RPO 0 isteyen PostgreSQL kurulumu X3'e gider. Oracle X2 (Data Guard SYNC) RPO 0'da kalır.
2. **KB-11:** OpenShift aboneliği soket çifti değil çekirdek çifti başınadır [RH-OCP-GUIDE]; `OCP_USD_PER_COREPAIR_YEAR` 2.000 / 3.000 / 4.200.
3. **KB-15:** Bileşen toplamının Dell yapılandırıcı fiyatına ±%20 kalibrasyonu yapılamadı; kaynak yapılandırmayı vermiyor. Yalnızca dönem bandı kontrolü var.
4. **KB-06:** `B_X86` köşelerinin yönü n < 48 çekirdekte tersine dönüyordu (küçük düğümde low ucu pahalılaştırıyordu). Yön tutarlı bir düzey anahtarıyla (`X86_SCALING_LEVEL`) düzeltildi.

Ayrıca köprüler dokümanında olmayan iki kural eklendi: eşleştirilmiş karşılaştırma senaryoları ile `CROSS_BRIDGE_WEIGHTS` (§3.5) ve NPV'de yığın seçiminin bütün yolu taşıyabilen adaylar arasından yapılması.

**Yapılacak:** `kopruler_v2.md` (v1 düzenlenmeden) bu altı noktayı almalı.

### 3.4. Kodlamada bulunan model hataları (Önemli, düzeltildi)

| Hata | Etkisi | Düzeltme |
|---|---|---|
| Uygulama katmanı tavanı ve sanallaştırma ek yükünü iki kez uyguluyordu (girdi zaten tavana bölünmüş çekirdek sayısıydı) | Uygulama katmanı ~1,5 kat büyük | Girdi DB'nin meşgul çekirdekleri; tavan bir kez |
| `B_X86` köşe yönü küçük düğümde ters | Aralığın low ucu küçük TPS'te yanlış yönde | `X86_SCALING_LEVEL` (§3.3 madde 4) |
| NPV'de yığın 1. yılın statik seçiminden sabitleniyordu | high köşede NPV infeasible (büyüyen yük yolun sonunda 1. yılın yığınının tavanını aşıyor) | Bütün yolu taşıyan yığın × topoloji adaylarının en küçük NPV'si |
| Eşleştirilmiş senaryoda mainframe CPU parametreleri x86'nın personelini ve uygulama katmanını da kaydırıyordu | "x86 lehine" senaryoda x86 $53,66 → $89,49 | `CROSS_BRIDGE_WEIGHTS` = "reference" (§3.5) |

Dördü de testle korunuyor (`test_app_tier`, `test_scaling_corners_direction_consistent`, `test_npv_consistency_and_direction`, `test_paired_comparison_scenarios`).

### 3.5. Ortak türetmelerin platforma özgü parametreye bağlanması (Önemli, tasarım dersi)

P ve C kararları iki ortak türetme yarattı: personelin PCI eşdeğeri ve uygulama katmanının TM payı. İkisi de mainframe'in CPU ağırlıklarını okur. Tek platform çalıştırmalarında bu doğrudur. Ama karşılaştırmada mainframe'in CPU belirsizliği bir "mainframe'e özgü" parametredir ve x86'nın maliyetini oynatmamalıdır. `CROSS_BRIDGE_WEIGHTS` = "reference" bu bağı yalnızca karşılaştırmada keser ve iki türetmeyi mid ağırlıklarla yapar. Genel ders: **bir köprü bir platformun parametresinden türetiliyorsa, karşılaştırma katmanında o parametre köprü için sabitlenmelidir; aksi halde belirsizlik iki tarafa birden, ters işaretle girer.** Bu kural ortak modül dokümanının §12 ve §14'üne yazıldı.

### 3.6. RAC'ın çok sayıda küçük düğüm seçmesi (Önemli)

RAC ölçeklenmesi `1 + (k − 1) × verim` ile k'ye doğrusal marjinal verimlidir. Model bu yüzden lisans maliyetini azaltmak için çok sayıda küçük düğüm seçer (50K TPS'te k = 7). Gerçek RAC kurulumlarında düğümler arası önbellek tutarlılığı trafiği k ile artar (USL'nin β terimi). `RAC_MAX_NODES` = 4 duyarlılığında 50K'da personel hariç maliyet %10 artar ve 130K TPS infeasible olur. Sonuç yönünü değiştirmez, ama yüksek hacim bölgesinin bir aralık olarak verilmesi gerektiğini güçlendirir. **Yapılacak:** RAC ölçeklenmesi için USL biçiminde bir kaynak aranmalı.

### 3.7. Mainframe'in yüksek hacim tavanı simetrik bir sınırlamadır (Küçük)

F'den sonra mainframe tek CEC tavanı ~132,7K, Patroni ~35,9K, RAC ~231K TPS'tir. Parallel Sysplex (mainframe) ve Citus (PostgreSQL) iki tarafta da modellenmedi. 100K TPS'te eşleştirilmiş senaryoların bir kısmı iki taraftan birinde infeasible'dır. Tez karşılaştırmanın geçerli aralığını tek CEC tavanıyla sınırlamalıdır.

---

## 4. Sağlam Bulunan Noktalar

- **Tek sahip kuralı x86'da da tutuyor.** `test_shared_parameters_single_owner` x86 modülünde hiçbir ortak adın yeniden tanımlanmadığını denetler; ortak ad listesi elle tutulmuyor.
- **Mainframe değişiklikleri izole.** Altın sonuç kümesi F ve P'nin eski kurallarıyla (`RANGE_READ_WEIGHT` = 1, `STAFF_BASIS` = "installed", `NONPROD_FACTOR` = 0) 0 farkla yeniden üretiliyor. Bütün mainframe farkları F ve P'den geliyor.
- **NPV tutarlılığı.** Sıfır büyüme, sıfır artış ve r = 0'da x86 NPV'si de 60 × statik toplama eşittir; büyüme NPV'yi artırır, iskonto azaltır.
- **Fiziksel ve ticari mekanizmalar x86'ya özgü.** Kurulu çekirdek lisansı (vSphere 16 çekirdek/CPU ve 72 çekirdek/sipariş minimumları, Oracle çekirdek faktörü 0,5, standby tam lisans), Patroni'nin tek yazıcı tavanı, RAC'ın N+1'i, NVMe × RF ile SAN ayrımı, 3 yıllık sunucu garantisi. Mainframe'in mekanizmaları x86'ya kopyalanmadı.
- **Eşleştirilmiş senaryo tasarımı.** İki platformun kendi köşelerini (mainframe low ile x86 high) birlikte okumak ortak parametreleri çelişik değerlere koyardı. Eşleştirilmiş tasarım bunu önler ve ortak belirsizliği ayrı iki senaryoda (ortak_low, ortak_high) gösterir.
- **Uzlaştırma senaryoları ana aralıktan ayrı.** IBM'in kullanım oranı (%17,5) ve üretim dışı (+%200) iddiaları ayrı senaryo olarak raporlanır; ikisi de tek başına sıralamayı çevirmez (10K TPS'te $65,19 ve $54,69, mainframe $113,93). Çeviren personel oranıdır.

---

## 5. Akademik Değerlendirme

**İç geçerlilik.** İki model aynı iş yükü tanımını, aynı kuyruk ailesini (çekirdek başına M/M/1), aynı tavan kuralını, aynı saha olayı denklemini, aynı yedek hacmi kuralını, aynı personel eğrisini ve aynı NPV kurallarını kullanıyor; farklar yalnızca platformların kendi mekanizmalarında. Bu, Değerlendirme #1'in "ortak birim yok" tehdidinin artık yapısal olarak kapandığı anlamına gelir.

**Yapı geçerliliği.** En zayıf halka hâlâ x86 kapasite çapasıdır (tek, belgelenmemiş ölçüm). Köprü aralığı (60–120) geniş tutuldu ve tornado'da görünüyor, ama x86'nın personel hariç maliyeti o kadar küçük ki köprü belirsizliği sonucu Oracle bölgesi dışında az etkiler. Yani K6'nın önemi PostgreSQL bölgesinde maliyet değil, **Patroni tavanının yeri** (yani Oracle'a geçiş eşiği) içindir. Eşleştirilmiş "mainframe lehine" senaryodaki crossover tam olarak bu eşiğe bağlıdır.

**Dış geçerlilik.** Sonuç ABD ücretleri, 2025 ortası emtia fiyatları, 2004 nominal AWLC fiyatları (aralıkla) ve tek bir adanmış OLTP iş yükü için geçerlidir. Çok uygulamalı, konsolide bir mainframe kurulumunun ölçek ekonomisi (personel ve yazılımın birden çok iş yüküne paylaştırılması) modelin dışındadır; bu mainframe aleyhine bir sınırlamadır ve tezde açıkça yazılmalıdır.

**Literatürle ilişki.** IBM Eagle (97 çalışma) dağıtık ortamı ortalama 2,2 kat pahalı bulur. Bizim modelimiz nötr personelle ters yönde ~2 kat bulur. İkisini uzlaştıran parametre personel oranıdır: başabaş oranı (~2,2) IBM'in kendi vakalarının aralığındadır. Yani iki sonuç birbiriyle çelişmez; IBM'in sonucu dağıtık tarafta daha kalabalık bir ekip ve daha düşük kullanım varsayar. Bu uzlaştırma tezde ayrı bir paragraf olmalıdır.

---

## 6. Sonraki Adımlar

1. **K6 ölçüm protokolü ve koşusu** (Karar K): SPEC'li perakende SKU, ayrı istemci makinesi, ayarlar raporlanır; senkron replikalı koşu (Patroni X2 RPO ve WAL fsync); `RANGE_READ_WEIGHT` kalibrasyonu.
2. **`kopruler_v2.md`:** §3.3'teki dört düzeltme ve iki yeni kural (v1 düzenlenmeden).
3. RAC ölçeklenmesi için USL biçiminde kaynak; Patroni tavanı üstü bölgenin aralık olarak raporlanması.
4. Sunucu fiyatı için yapılandırması belli bir kamu ihale kaydı (KB-15 kalibrasyonu).
5. Tez sonuç tablosu taslağı: başabaş personel oranı (TPS × availability), personelsiz TCO oranı, eşleştirilmiş senaryolar.
6. Değerlendirme #6'dan açık kalanlar: drawer maliyeti, GDPS Metro, planlı kesinti kalibrasyonu, L4+ AWLC fiyatları, Parallel Sysplex.
