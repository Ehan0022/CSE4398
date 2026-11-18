# Değerlendirme #8 — Açık Sistem Araştırmasının Eleştirel İncelemesi

*Tarih: 2026-11-16 · İncelenen: `docs/acik_sistem_arastirma_plani_v1.md` (plan v1), `docs/benzer_calismalar_v1.md`, `src/common_model.py` (Adım 6), `src/mainframe_model.py` ve `docs/mainframe_model_documentation_v3.md` · Kod değişikliği yok*

Bu değerlendirme x86 modeli kodlanmadan önce yapıldı. Amaç, plan v1'deki kaynakları ve çapaları birincil kaynağa ve mainframe tarafındaki karşılıklarına karşı denetlemek, iki taraf arasındaki köprülerden hangilerinin sonucu **kendi başına belirleyebilecek** kadar tutarsız olduğunu bulmak ve bunlar için seçenek sunmaktır. Orijinal belgeler düzenlenmedi. Kararlardan sonra plan v2 yazılacak.

Önem dereceleri: **Kritik** = düzeltilmezse crossover'ın yerini tek başına belirleyebilir · **Önemli** = sonucu ölçülebilir biçimde kaydırır ya da savunmada zayıf nokta olur · **Küçük** = metin ya da tutarlılık düzeltmesi.

---

## 1. Kısa Sonuç

1. **Personel köprüsü kritik derecede tutarsız.** Mainframe personeli kuruluş düzeyindeki bir "MIPS başına FTE" kuralından, x86 personeli sunucu başına saatten geliyor. 10K TPS'te mainframe 30,8 FTE, x86 ise Eagle saatleriyle 0,4 FTE (taban ekiple 4 FTE) çıkıyor. Bu 7,7 katlık fark aylık ~$360K, yani mainframe toplamının ~%40'ı. Bu haliyle karşılaştırmanın sonucunu teknoloji değil, iki kuralın birbiriyle uyumsuzluğu belirler (§2.1).
2. **Kapasite çapasının tek kaynağı zayıf belgelenmiş bir blog.** Vonng ölçümünde PostgreSQL sürümü, iş parçacığı sayısı, istemcinin aynı makinede olup olmadığı ve ayarlar yazılı değil. Birim (QPS) yalnızca şekil altyazısından çıkarılabiliyor. Çapraz kontroller de SPECint ile normalize edilmemiş bulut ölçümleri. K6 (kendi ölçümümüz) bu yüzden bir iyileştirme değil, çapanın kendisi olmalı (§2.2).
3. **"Aynı bileşim" iddiası tablo düzeyinde doğru, maliyet düzeyinde eksik.** Mainframe profili 14 okumanın hepsine aynı CPU'yu veriyor. Oysa sysbench'te 4 okuma 100 satırlık aralık sorgusu (ORDER BY ve DISTINCT dahil). Vonng'un kendi alt testlerinden aralık sorgusunun nokta sorgusundan 3,4–3,9 kat pahalı olduğu çıkıyor. Bu düzeltmeyle mainframe'de w 9,15'ten ~12,5'e çıkar ve köprü 1 CP ≈ 2,2 çekirdekten ≈ 1,6 çekirdeğe iner (§2.3).
4. **x86 kullanım oranı için önerilen %15–20 alt uç bu modele uymuyor.** IBM'in 10–20 katlık kullanım oranı konsolide edilmemiş, çok uygulamalı sunucu parklarından geliyor. Bizim modelimiz ise tek bir adanmış OLTP iş yükünü tepe yüke göre boyutluyor. Bu alt ucu almak aynı etkiyi iki kez saydırır. Öneri: iki tarafta aynı kural (latency'den gelen tavan ile operasyonel tavanın küçüğü), x86 tavanı aralıklı (§2.4).
5. **Fiyat dönemi varsayılanı x86 aleyhine.** `PRICE_EPOCH` = "2026-Q3" (bellek ve SSD şoku) varsayılan. Mainframe çapaları ise şok öncesinden ve döneme bağlı değil. Ayrıca bellek fiyatı hem dönem tablosunda hem de plan §12.1'de ayrı bir aralık parametresi olarak duruyor, bu da tornado'da iki kez sayılır (§2.5).
6. **Availability ve topoloji eşlemesi sağlam.** Ortak saha olayı denklemi ve ortak elle geçiş karar süresi doğru kurulmuş. Yalnızca küçük eksikler var (§3.4).

Altı köprü kararı §5'te seçeneklerle ve önerimle birlikte.

---

## 2. Kritik ve Önemli Bulgular

### 2.1. Personel köprüsü (Kritik)

**Ne bulduk.** Mainframe personeli `FTE = max(taban, FTE_1000 × (PCI/1000)^b)` ile hesaplanıyor. Kaynaklar IBM Eagle'ın 17 müşterisi ("5 FTE + her 625 MIPS için 1 FTE") ve Gartner IT Key Metrics 2016 (kurulu MIPS/FTE 152–268). Bunların ikisi de **bütün bir mainframe kuruluşunun** personelini ölçer: batch, çok sayıda uygulama, güvenlik, kapasite planlama. Plan v1 §10.3'teki x86 formülü ise sunucu başına 32 saat ve imaj başına 36 saatten çalışır [IBM-EAGLE-LABOR].

Model kodundan hesapladığım değerler (oltp_rw, 10K TPS, M1 / X1):

| | Mainframe | x86 (PostgreSQL, X1) |
|---|---|---|
| Kapasite | 3931-516, 11.743 PCI | 1 birincil + 2 replika, 32 çekirdekli düğüm |
| Formülden FTE | 30,8 (low 17,5 / high 50,2) | (32×3 + 36×3 + 600×1) / 2.080 = **0,39** |
| Taban ekip sonrası | 30,8 | 4,0 (3 / 5) |
| Aylık personel | $416K | $54K |

Fark aylık ~$360K, yani TPS başına ~$36. Bu mainframe'in $93,10/TPS başlığının ~%40'ı. 2K TPS'te oran 2,5 kat, 50K TPS'te ~23 kat.

**Neden sorunlu.** İki kural aynı birimi ölçmüyor:
- Mainframe kuralı kapasiteyle büyüyor, çünkü kaynağındaki kuruluşlarda kapasite büyüdükçe uygulama sayısı da büyüyor. Tek bir iş yükünün kapasitesi büyüyünce aynı hızda personel gerekmez.
- x86 kuralı da kuruluş düzeyinde, ama sunucu başına. Bizim köprümüzle (1 CP ≈ 2,2 çekirdek) eşdeğer x86 kurulumu çok az sunucu olduğu için x86 personeli hep tabanda kalıyor. Sonuçta x86 personeli fiilen taban ekip varsayımından (3 / 4 / 5 FTE, [ASSUME]) ibaret.
- Sonuç IBM'in kendi bulgusunun da tersi: IBM aynı Eagle verileriyle dağıtık tarafın daha çok personel istediğini söylüyor. Bu tersine dönüş, IBM'in mainframe kuralını IBM'in dağıtık kuralıyla ama IBM'in 24–80 çekirdek oranı yerine bizim 2,2 çekirdek oranımızla birleştirmekten doğuyor.

**Akademik değerlendirme.** Personel iki tarafta da en büyük kalem olabileceği için, iki tarafın personelini **aynı sürücüyle** ölçmeyen bir model crossover'ı savunulabilir biçimde veremez. Bağımsız bir dağıtık personel oranı yok (plan §10.4). Bu yüzden en dürüst yol personeli ortak bir yapıya bağlayıp iki platform arasındaki farkı **açık, aralıklı bir oran** olarak göstermek ve sonucu bu oranın fonksiyonu olarak raporlamaktır. Seçenekler §5, Karar P.

### 2.2. Kapasite çapası: Vonng c5d.metal (Önemli)

Birincil kaynağı yeniden okudum (blog.vonng.com, "How Powerful is PostgreSQL Really?"):
- oltp_read_write 519.069 tablo hücresinde birimsiz. Birimin QPS olduğu yalnızca şekil altyazısında yazıyor ("Sysbench 10-item test results (QPS, higher is better)"). Plan v1'in QPS/20 çevirisi bu altyazıyla ve write_only (495.942) ile tutarlı: ikisi TPS olsaydı 4 yazmalı işlemin 20 sorguluk işlemle aynı hızda olması gerekirdi. **Çeviri doğru, ama dayanağı altyazı.**
- Sysbench koşusu için PostgreSQL sürümü yazılı değil (14.5 yalnız pgbench için). İş parçacığı sayısı, süre, istemcinin aynı makinede olup olmadığı ve `synchronous_commit` / `fsync` ayarı yazılı değil. Yalnızca "full production environment configuration" deniyor.
- İstemci aynı makinedeyse 48 çekirdeğin bir kısmı sysbench'e gitti ve çekirdek başına PostgreSQL verimi olduğundan **düşük** çıktı (x86 aleyhine). Commit yolunda bir ayar kapalıysa **yüksek** çıktı (x86 lehine). Yönü bilinmeyen iki hata.
- Plan v1 §3.3'teki "üç değer birbirinin ±%15'i içinde" kontrolü fazla güçlü yazılmış. Rockdata (CPU modeli yok, 32 vCPU = 16 fiziksel çekirdek varsayımı) ve Tencent (4 "çekirdek" büyük ihtimalle vCPU) SPECint ile normalize edilemiyor. Tencent'te "çekirdek" vCPU ise fiziksel çekirdek başına değer ~2 katına çıkar. Bunlar çapraz kontrol değil, büyüklük mertebesi bağlamıdır.

**Öneri.**
- K6 ölçümü çapanın kendisi olsun; Vonng çapraz kontrole insin. K6 yapılana kadar `X86_TPS_PER_SPECINT_CORE` aralığı 70–105'ten **60–120**'ye genişlesin.
- K6 protokolüne bir kısıt eklenmeli: bulut bare-metal CPU'ları (8275CL, 8488C gibi) özel SKU'dur ve SPEC sonucu yoktur. Ya SPEC sonucu yayımlanmış bir perakende SKU'lu laboratuvar sunucusu kullanılmalı, ya da (Vonng'da yapıldığı gibi) perakende kardeş SKU'nun SPEC değeri alınıp bu ayrı bir belirsizlik olarak yazılmalı. Ayrıca istemci ayrı makinede olmalı ve ayarlar raporlanmalı.

### 2.3. İşlem bileşimi: nokta okuma ile aralık okuma (Önemli)

sysbench `oltp_read_write`: 10 nokta SELECT, 4 aralık SELECT (simple, SUM, ORDER BY, DISTINCT; her biri `range_size` = 100 satır), 2 UPDATE, 1 DELETE, 1 INSERT, BEGIN/COMMIT. Mainframe `WorkloadProfile` bunu "14 okuma × 30 µs" olarak alıyor.

Vonng'un kendi alt testlerinden [DERIVED] (makine-µs / işlem, 48 çekirdeğin toplamı):

| Test | QPS | Sorgu / işlem | TPS | µs / işlem |
|---|---|---|---|---|
| point_select | 1.372.654 | 1 | 1.372.654 | 0,73 |
| read_only | 852.440 | 16 | 53.278 | 18,77 |
| write_only | 495.942 | 6 | 82.657 | 12,10 |
| read_write | 519.069 | 20 | 25.953 | 38,53 |

read_only = 10 nokta + 4 aralık (+ BEGIN/COMMIT). Buradan aralık sorgusu nokta sorgusunun **3,4–3,9 katı** (BEGIN/COMMIT'e bir nokta sorgusu kadar maliyet verilirse 3,4, hiç verilmezse 3,9). Yazma da nokta okumanın 3,7–4,2 katı. Mainframe'deki 70/30 = 2,3 oranı bunun biraz altında.

**Mainframe'e etkisi (nokta okuma 30 µs sabit, aralık = oran × 30 µs):**

| Aralık / nokta | w | z16 CP başına TPS | CP başına R760 çekirdeği |
|---|---|---|---|
| 1 (şu anki model) | 9,15 | 1.955 | 2,19 |
| 3,4 | 12,5 | 1.431 | 1,60 |
| 3,9 | 13,2 | 1.355 | 1,52 |

Bu değerler mevcut `CPU_US_PER_SQL_READ` taramasının (15–60 µs, w 6,7–14,0) içinde kalıyor, yani aralık sonuçları büyük ölçüde zaten kapsıyor. Ama orta değer, aynı kaynağın x86 için ölçtüğü bileşimle çelişiyor. Bu bir mainframe modeli değişikliği olduğu için Karar F'de.

Ek not: read_write (38,5 µs), read_only ile write_only toplamından (30,9 µs) %25 pahalı. Karma yükte çekişme ek maliyet getiriyor. Çapa zaten karma yükten alındığı için bu x86'da içeride. Mainframe'de böyle bir terim yok, ama REDP-5320 köprüsü de karma bir yük olduğu için orada da kısmen içeride. Tez için yeterli olan, bunu not etmek.

### 2.4. x86 kullanım oranı (Önemli)

`benzer_calismalar_v1.md` B1, x86 hedef kullanım oranını alt ucu %15–20, üst ucu %50–70 olan bir aralık parametresi olarak öneriyordu. IBM'in `U_R` = 10–20 değeri (dağıtık %5–12, mainframe %80–90) konsolide edilmemiş, uygulama başına sunucu kullanan parklardan geliyor. Bizim modelimizde:
- tek bir adanmış OLTP veritabanı var;
- kapasite **tepe** yüke göre boyutlanıyor (ortalama/tepe farkı ayrıca var);
- replikalar ve DR düğümleri topolojiden zaten ekleniyor (IBM'in "HA kopyaları" çarpanı);
- dev/test ayrı bir çarpan (`NONPROD_FACTOR`).

%15'lik bir tavan bu üç etkiyi yeniden ekler. Bu çift sayımdır. Mainframe tarafında da aynı mantık işliyor: `rho = min(rho_latency, 0,90)`.

**Öneri:** x86'da da aynı kural: `rho = min(rho_latency, X86_UTIL_CEILING)`. Tavan aralıklı: 0,90 (x86 lehine, mainframe ile eşit) / 0,70 / 0,50. Gerekçe: x86'da WLM ve CoD karşılığı olmadığı için kurumlar veritabanı düğümlerini tepe yükte boşlukla işletir. Bu gerçek bir platform farkı ve aralıkla temsil edilmeli. %15–20, IBM iddiasıyla uzlaştırma analizinde (B1 madde 3) ayrı bir "konsolide edilmemiş park" senaryosu olarak gösterilsin, ana aralıkta olmasın. Karar U.

### 2.5. Fiyat dönemi (Önemli)

- `common_model.PRICE_EPOCH` varsayılanı "2026-Q3": DRAM $35/GB, NVMe $753/TB. Mainframe fiyatları (z16 $200/PCI, 2022 DS8900F listesi, 2004 AWLC × seviye çarpanı) dönemden bağımsız ve şok öncesi. Varsayılan bu yüzden x86'yı şoklu, mainframe'i şoksuz fiyatlıyor. Değerlendirme #7 tehdit 3.5 bunu "mainframe lehine yanlılık" olarak kaydetmişti, ama varsayılan değişmemişti.
- Plan v1 §12.1'de `MEM_USD_PER_GB` 5 / 16 / 37 ve `NVME_USD_PER_TB` 120 / 400 / 750 ayrı aralık parametreleri. Dönem tablosu da aynı kalemi fiyatlıyor. İkisi birlikte kullanılırsa aynı belirsizlik tornado'da iki kez sayılır.
- $35/GB perakende spot fiyatı (Ağustos 2026). Ortak modülün sözleşmesi ise "liste fiyatı → tek indirim". Perakende spot fiyatına bir de OEM indirimi uygulanırsa fiyat tabanları karışır.

**Öneri:** Ana karşılaştırma "2025-mid" döneminde yapılsın (iki tarafın çapaları aynı dönemde). "2026-Q3" bir duyarlılık senaryosu olsun ve "mainframe fiyatlarının şoka tepkisi bilinmiyor" notuyla raporlansın. Bellek ve NVMe her dönemde kendi low/mid/high üçlüsüyle tanımlansın; dönem anahtarı yalnızca hangi üçlünün kullanılacağını seçsin. Karar E.

### 2.6. Patroni tek yazıcı tavanı (Önemli)

35–50K TPS değeri, katalogda seçilen SKU'nun (2 × 32 çekirdek, 6548Y+) bir sonucu. R760, 2 × 64 çekirdeğe (8592+) kadar çıkıyor. O durumda SPECint'ten tavan ~90–100K çıkar, ama çapa 48 çekirdekte alındı ve PostgreSQL'in 128 çekirdekte tek birincilde nasıl ölçeklendiğine dair veri yok (plan §14.8).

**Öneri:** Tavan sabit bir sayı olarak değil, "katalogdaki en büyük düğüm × S(n)" olarak tanımlansın. Ana katalog 64 çekirdeğe kadar (çapanın ~1,3 katı) olsun, 96–128 çekirdek "ekstrapolasyon" işaretli bir duyarlılık olsun. Tezde şu açıkça yazılmalı: **tavanın üstünde (~50K – ~187K TPS) karşılaştırma mainframe ile Oracle RAC arasındadır ve RAC tarafı kalibre edilemeyen iki parametreye dayanır** (`ORACLE_THROUGHPUT_FACTOR`, `RAC_SCALING_EFFICIENCY`). Bu bölgede sonuç bir aralık olarak verilmeli, nokta olarak değil.

### 2.7. Kapsam asimetrisi: CICS ile uygulama katmanı (Önemli)

Plan v1 §14.4 "Adım 6'da karar" diyordu, ama karar verilmedi. Mainframe CPU'su `CPU_US_TM_BASE` = 85,9 µs (CICS + REDP uygulama mantığı) içeriyor, CICS TS lisansı da modelde. x86 çapasında uygulama sysbench istemcisi ve modelin dışında.

**Öneri:** x86'ya bir uygulama/işlem katmanı eklensin ve köprüyle boyutlansın. Mainframe işlem CPU'sunun TM payı 85,9 / 786 ≈ **%11**. Bu pay x86 çekirdeğine köprü oranıyla çevrilir ve Linux VM'leri olarak fiyatlanır (açık kaynak uygulama sunucusu, RHEL + vSphere/OCP; ek lisans yok). Shedletsky'nin 4,9 kat iddiası bağımsız doğrulaması olmadığı için yalnızca üst uç duyarlılığı olarak kullanılsın. Bu, ağ gidiş-dönüşünü (`ROUNDTRIPS_PER_TX`) de doğal kılar: uygulama katmanı veritabanından ayrı düğümde olur. Karar C.

---

## 3. Küçük Bulgular ve Düzeltmeler

### 3.1. Kapasite ve köprü
- Plan v1 §3.6'daki 1 CP = 1.955 TPS, zIIP payını (f = 0,10) dışarıda bırakıyor. Modelde GP CP başına 2.172 TPS. zIIP motorları ayrı donanım maliyeti olduğu için karşılaştırmada "GP + zIIP motoru" ile çekirdek karşılaştırılmalı. Fark küçük (%10), ama tablo kodla tutarlı olmalı.
- `benzer_calismalar_v1.md` §3.3, 2,2 çekirdek değerine "plan §3.5" diye atıf yapıyor. Doğrusu §3.6.
- SPECrate'in Cascade Lake'ten Emerald Rapids'e çekirdek başına 1,65 katlık artışının bir kısmı bellek bant genişliğinden (DDR4 6 kanal → DDR5 8 kanal) ve derleyici sürümünden geliyor. Tehdit 14.1'e bu iki nedenin adıyla eklenmeli.

### 3.2. Donanım fiyatı
- Bileşen fiyatları üç farklı tabandan geliyor: Intel önerilen fiyatı (CPU), perakende spot (bellek, SSD), Dell yapılandırıcı listesi (bütün sistem). Öneri: bileşen fonksiyonu bir **kalibrasyon kontrolüyle** doğrulansın. Tanımlı bir R760 yapılandırmasının bileşen toplamı Dell yapılandırıcı liste fiyatına ±%20 içinde yaklaşmalı; indirim yalnızca bu liste toplamına bir kez uygulanmalı.
- RHEL for Virtual Datacenters $2.904 bir hizmet sağlayıcı sözleşme fiyatı, kurumsal liste değil. Taban notu eklenmeli.

### 3.3. Storage
- PostgreSQL'de MVCC şişmesi (bloat) ve WAL tutma alanı Db2'den farklı. Boyutlandırma zincirindeki "DB ek yükü" platforma özgü bir parametre olmalı (`PG_BLOAT_FACTOR` 1,1 / 1,3 / 1,6 [ASSUME]).
- Patroni'de her düğümün yerel NVMe'si için RAID düzeyi belirtilmemiş. Öneri: replikalar yedeklilik sağladığı için düğüm içinde RAID 1 değil, RAID 0 ya da JBOD + replika. Bu da açık bir varsayım olarak yazılmalı.

### 3.4. Availability
- x86'da işletim sistemi yamaları aylık ve her biri bir Patroni switchover'ı (birkaç saniye) ve bağlantı kopması demek. Plan v1 bunu planlı kesintide "saniyeler" diye geçiyor, ama λ_planlı'yı mainframe ile aynı (0,25 / 0,5 / 1) alıyor. Öneri: x86'da λ_planlı'ya yılda 12 rolling switchover × 5 / 15 / 30 sn eklensin. Etkisi küçük, ama denklemin dürüstlüğü için gerekli.
- X1 ile M1'in RPO'su iki tarafta da 24 saat. Bu tutarlı, ama x86'da sürekli WAL arşivleme (pgBackRest) standart ve RPO'yu dakikalara indirir. Mainframe'de de log arşivi yedek hedefe gidiyor. İki taraf aynı kuralla (yedek hedefe log gönderim aralığı) birlikte güncellenmeli ya da birlikte 24 saatte bırakılmalı. Karar değil, tutarlılık notu.

### 3.5. Üretim dışı ortamlar
- x86 için `NONPROD_FACTOR` aralığı henüz belirlenmedi. IBM'in dağıtık için "+%200" değeri park düzeyinde. Tek bir veritabanı için en az bir staging kopyası ve küçük dev/test kopyaları gerekir. Öneri 0 / 0,50 / 1,00; 2,0 yalnızca "IBM iddiası" stres senaryosu. Gerekçe yapısal: mainframe'de dev/test aynı CEC'te LPAR olarak durur ve R4HA tepesine az katkı verir; x86'da ayrı düğüm ve (Oracle'da) ayrı çekirdek lisansı ister. Karar N.

---

## 4. Sağlam Bulunan Noktalar

- **Oracle aralığı (0,8–1,3, orta 1,0).** Lisanstaki benchmark yasağı doğru kaynaklanmış. Kaynak yokken yön iddia etmemek (orta 1,0) savunulabilir. Tezde bunun "kayıtsızlık ilkesi" olduğu açıkça yazılmalı.
- **Oracle lisans kuralları** (çekirdek faktörü 0,5, VMware yumuşak bölümleme, standby tam lisans) birincil Oracle belgelerine dayanıyor. Standby kuralı "doğrulanmalı" etiketini koruyor; Oracle'ın "Licensing Data Recovery Environments" belgesiyle teyit edilmeli.
- **Topoloji eşlemesi (M1–M4 ↔ X1–X4).** Ortak modüldeki saha olayı denklemi ve ortak elle geçiş karar süresi iki tarafı aynı çerçeveye oturtuyor. X4'ün PostgreSQL'de infeasible sayılması (K4) mainframe'deki "komik topoloji" kuralıyla tutarlı.
- **Yapısal asimetrilerin eşitlenmeyip modellenmesi** (kurulu çekirdek lisansı ile R4HA, 3 yıl ile 1 yıl garanti, CoD'nin x86 karşılığının olmaması). Doğru yaklaşım.
- **Kuyruk ailesi.** x86'da da çekirdek başına bağımsız M/M/1 seçilmesi iki tarafta aynı tutuculuğu sağlıyor.
- **Storage fiyat sözleşmesi** (`price_per_raw_tb`) kodda ve testte var.

---

## 5. Köprü Kararları (Emirhan'ın onayını bekliyor)

| # | Köprü | Seçenekler | Öneri |
|---|---|---|---|
| **P** | Personel | (a) Plan v1: iki ayrı üretici kuralı (mainframe MIPS/FTE, x86 sunucu saatleri). (b) **Ortak iş yükü eğrisi + aralıklı oran:** mainframe eğrisi TPS'e çevrilir, x86 personeli = aynı TPS'teki mainframe personeli × `STAFF_RATIO_X86` (0,5 / 1,0 / 2,0); ayrıca **başabaş oranı** çıktı olarak raporlanır (iki tarafı eşitleyen personel oranı). (c) Rol tabanlı ekip modeli: iki tarafta 7/24 için gereken roller × kapsama çarpanı + kapasite artışı (sayılar [ASSUME]) | **(b).** Kaynak olmayan yerde farkı gizlemek yerine onu açık bir parametre yapar ve sonucu "personel oranı X'in altındaysa x86 kazanır" biçiminde verir. Aralığın uçları kanıtla bağlanır: 0,5 ≈ Eagle saatlerinin işaret ettiği yön, 2,0 ≈ IBM'in dağıtık iddiası. Mainframe eğrisi aynen kalır |
| **F** | İşlem bileşimi (performans) | (a) 14 okumayı eşit saymaya devam. (b) **Profil 10 nokta + 4 aralık okuma olsun**; aralık ağırlığı `RANGE_READ_WEIGHT` = 3,4 / 3,65 / 3,9 (Vonng alt testlerinden [DERIVED], K6 ile kalibre) iki tarafta ortak | **(b).** "Aynı bileşim" iddiasını maliyet düzeyinde de doğru yapar. Mainframe başlığı yükselir (w ~12,5); bunu mainframe v3 dokümanına ve log'a işleriz |
| **K** | Kapasite çapası | (a) Vonng çapası, aralık 70–105. (b) **K6 ölçümü çapa, Vonng çapraz kontrol**; K6'ya kadar aralık 60–120; K6'da yayımlanmış SPEC'li perakende SKU, ayrı istemci makinesi, ayarlar raporlanır | **(b)** |
| **U** | Kullanım oranı | (a) B1: hedef kullanım %15–20 / … / %50–70. (b) **Aynı kural iki tarafta:** `rho = min(rho_latency, tavan)`; x86 tavanı 0,90 / 0,70 / 0,50; %15–20 yalnızca uzlaştırma analizinde ayrı senaryo | **(b).** Çift sayımı önler, mainframe ile simetrik |
| **E** | Fiyat dönemi | (a) Varsayılan 2026-Q3 (şimdiki). (b) **Ana senaryo 2025-mid, 2026-Q3 duyarlılık**; bellek/NVMe her dönemde kendi üçlüsüyle; ayrı MEM/NVME aralık parametresi yok | **(b).** İki taraf aynı dönemde karşılaştırılır |
| **C** | CICS / uygulama katmanı | (a) Asimetriyi yalnızca sınırlılık olarak yazmak. (b) **x86'ya köprüyle boyutlanmış bir uygulama katmanı eklemek** (mainframe TM payı ≈ %11, Linux VM, ek lisans yok); 4,9 kat yalnızca üst uç duyarlılığı | **(b)** |
| **N** | x86 üretim dışı | (a) Mainframe ile aynı 0 / 0,20 / 0,50. (b) **0 / 0,50 / 1,00**, 2,0 stres senaryosu | **(b).** Fark yapısal (LPAR ile ayrı düğüm/lisans) |

Availability ve storage köprüleri plan v1'deki haliyle kalıyor; §3.3–3.4'teki küçük eklemeler onay gerektirmiyor.

---

## 6. Önceki Değerlendirmeden (#7) Kapanan ve Açık Kalan Tehditler

| #7 tehdidi | Durum |
|---|---|
| 3.1 Üretim dışı çarpanın orta değeri için IBM dışı kaynak | **Açık.** x86 aralığı için Karar N önerildi; bağımsız kaynak hâlâ yok |
| 3.5 Fiyat dönemi mainframe fiyatlarına uygulanmıyor | **Karar E ile kapanacak** (ana senaryo şok öncesi dönem) |
| K6 ile justification §5.2 gerilimi | **Açık.** K6 artık çapa olacağı için güncel x86 model dokümanında daha görünür yazılmalı |
| Steady'de B/C stratejisinin ince farka dayanması | Bu incelemenin kapsamı dışında; açık |

**Yeni tehditler (bu değerlendirme):** personel kuralı uyumsuzluğu (§2.1, Karar P ile ele alınacak); tek çapanın belgelenmemiş ayarları (§2.2); aralık sorgusu ağırlığı (§2.3); tavan üstünde RAC'ın kalibre edilemeyen iki parametreye dayanması (§2.6).

---

## 7. Sonraki Adım

1. Emirhan P, F, K, U, E, C, N kararlarını verir.
2. Kararlarla plan v2 yazılır (`docs/acik_sistem_arastirma_plani_v2.md`; v1 düzenlenmez).
3. F ve E mainframe tarafını etkilediği için bu ikisi önce `mainframe_model.py` ve `common_model.py`'de uygulanır. Başlık değişikliği log'a ve v3 dokümanına işlenir, testler güncellenir.
4. K6 ölçüm protokolü (laboratuvar sunucusu ya da SPEC'li SKU), ardından `x86_model.py`.
