# Açık Sistem (Clustered x86) Tarafı — Araştırma Bulguları ve Model Planı (v1)

*Tarih: 2026-11-02 · Durum: araştırma ve plan; kod yazılmadı · Kapsam: on-prem, kümelenmiş x86 OLTP yığını (VMware vSphere / OpenShift Virtualization × Kubernetes / OpenShift × PostgreSQL + Patroni / Oracle Database)*

Bu doküman x86 tarafını mainframe tarafıyla aynı derinlikte kurmadan önce **neyi bulmamız gerektiğini, neyi bulduğumuzu ve bulduğumuz her şeyin modele nasıl gireceğini** kaydeder. Kod yazılmadı. Model değişiklikleri kodlandığında güncel x86 model dokümanı ayrıca (mainframe v3'ün karşılığı olarak) yazılacak; bu dosya o dokümanın araştırma temeli ve tasarım planıdır.

**Kaynak seçme ölçütü.** Bir kaynak, konuyla "kabaca ilgili" olduğu için değil, modelin belirli bir parametresini ya da iki tarafı karşılaştıran bir köprüyü doğrudan besleyebildiği için alındı. Her kaynağın yanında hangi parametreye ya da köprüye hizmet ettiği yazılıdır. İncelenip alınmayan kaynaklar ve gerekçeleri Bölüm 15.2'dedir.

Etiketler: **[ASSUME]** kaynakla daraltılamayan varsayım · **[DERIVED]** kaynaktan hesaplanan değer · **(doğrulanmalı)** ikincil kaynaktan gelen, birincil kaynakla teyit edilmemiş bilgi · **[VENDOR]** üretici ya da üreticinin sponsor olduğu kaynak · **[KARAR]** Emirhan'ın onayını bekleyen konu.

---

## 0. Okuma Kılavuzu

- Bölüm 1 en önemli bulguları özetler. Hepsini okumaya vakit yoksa yalnızca 1 ve 13'ü (karar bekleyen konular) okuyun.
- Bölüm 2 iki sistemi karşılaştırmak için gereken **köprüleri** tek tabloda toplar. Planın omurgası budur.
- Bölüm 3–11 her model katmanı için aynı düzendedir: *ne bulmamız gerekiyordu → ne bulduk → modele nasıl girer → açık kalan*.
- Bölüm 12 önerilen aralık parametrelerini, Bölüm 14 yeni geçerlilik tehditlerini, Bölüm 15 kaynakları listeler.

---

## 1. Özet: En Önemli Bulgular

1. **İşlem birimi iki tarafta aynı tanımlanabiliyor.** sysbench `oltp_read_write` işlemi 10 tekil SELECT + 4 aralık SELECT (14 okuma), 2 UPDATE + 1 DELETE + 1 INSERT (4 yazma) ve BEGIN/COMMIT'ten oluşur [TENCENT-METHOD]. Bu, mainframe tarafındaki varsayılan `oltp_rw` profilinin (14 okuma + 4 yazma + 1 commit, w = 9,15) bileşimiyle birebir aynıdır. TPS ortak birimi bu sayede iki tarafta aynı işi ifade eder.

2. **x86'da "PCI"nın karşılığı SPECrate2017_int_base olabilir.** Mainframe köprüsü benchmark TPS'ini PCI'ye bölerek nesilden bağımsız bir katsayı elde ediyor. x86'da aynı işi çekirdek başına SPECrate2017_int_base yapabilir: Xeon Platinum 8270 (Cascade Lake) çekirdek başına 5,94, Dell R760'taki Xeon Gold 6548Y+ 9,81, HPE DL380 Gen12'deki Xeon 6787P 9,13 [SPEC-8270, SPEC-R760, SPEC-DL380G12]. Bu normalizasyonla farklı makinelerde ölçülmüş PostgreSQL sonuçları tutarlı hale geliyor: R760 sınıfı bir fiziksel çekirdek, bellekte tutulan veriyle **~900 oltp_rw TPS** taşıyor (Bölüm 3.3).

3. **Platformlar arası büyüklük kontrolü makul çıkıyor.** Mainframe modelinin kendi köprüsüyle bir z16 tam-hız CP'si oltp_rw'de ~1.955 TPS taşıyor (2.253 PCI × 7,939 / 9,15). Bu, **1 z16 CP ≈ 2,2 R760 çekirdeği** demektir. Değer, iki tarafın birbirinden bağımsız iki zincirle hesaplandığı düşünüldüğünde makul bir büyüklüktür ve tezde "köprü tutarlılık kontrolü" olarak kullanılabilir (Bölüm 3.6).

4. **Oracle için bağımsız performans verisi yayımlanamıyor.** Oracle lisansı, Oracle'ın izni olmadan benchmark sonucu açıklamayı yasaklar ("DeWitt maddesi") [ORACLE-OTN]. Bu yüzden Oracle'ın PostgreSQL'e göre çekirdek başı verimi kaynakla kalibre edilemez; yalnızca geniş bir aralık parametresi olabilir. Oracle'ın maliyeti çekirdek başına lisanslandığı için bu parametre doğrudan maliyeti etkiler. Bu, tezde açıkça bir **yapısal veri sınırı** olarak yazılmalı.

5. **Kümelenmiş x86'nın "ince granülerlik" beklentisi PostgreSQL + Patroni için yalnızca bir noktaya kadar doğru.** Patroni tek yazıcılı (single-primary) bir mimaridir: oltp_rw işlemlerinin her biri yazma içerdiği için bütün yük tek bir birincil düğümde işlenir. Replikalar yazma kapasitesi eklemez. Yani PostgreSQL tarafında kapasite düğüm içi (sunucu boyutu) adımlarla büyür ve tek düğümün tavanı vardır (R760 sınıfı tek düğüm için kabaca 35–55K oltp_rw TPS, Bölüm 4). Yazmayı yatayda ölçekleyen tek seçenek Oracle RAC'tir. Bu, `project_context_restore_v4.md` Bölüm 2'deki "clustered kapasite ince granülerlikte alınır" beklentisini yumuşatır ve tek z16 CEC tavanıyla (~187K TPS) simetrik bir sınırlamadır. **[KARAR]** (Bölüm 13, K3).

6. **2026'da x86 donanım fiyatları bir bileşen fiyat şoku içinde.** 64 GB DDR5 RDIMM ~9 ayda ~$255'ten ~$1.000'e çıktı, Ağustos–Ekim 2026'da perakende $2.245–3.400 aralığında [PCSP-SERVER, BACLOUD-RAM, CAPCOMP-RAM]. Kurumsal NVMe SSD'de 30 TB sınıfı bir sürücü Q3 2025'te ~$115/TB iken Q3 2026'da ~$753/TB [PCSP-SSD]. Mainframe tarafının fiyat çapaları ise bu şoktan önceki dönemden (2004 AWLC, 2019–2022 DS8900F). İki tarafın fiyatları aynı döneme oturtulmazsa sonuç fiyat döneminin bir eseri olur. Bu yüzden **fiyat dönemi** ortak modülde açık bir köprü olmalıdır (Bölüm 2, K9).

7. **Storage fiyatları iki tarafta ~10 kat farklı tabanlarda.** Mainframe modelinde DS8900F'in etkin flash fiyatı ~$2.590/TB ham (2022 liste fiyatı × %30). Açık sistem all-flash dizileri için 2026 Q1 karşılaştırma verisi $65–215/TB kullanılabilir/etkin gösteriyor [VENDORBENCH-AFA]. Fark kısmen gerçektir (mainframe storage'ı FICON, zHyperLink ve Copy Services nedeniyle pahalıdır), kısmen de tanım farkıdır ("etkin" TB veri azaltımı içerir, "ham" içermez). Karşılaştırmada iki taraf **aynı tanımla** (ham TB, aynı indirim yöntemi) fiyatlanmalı; aksi halde storage-ağırlıklı senaryolarda sonuç tanımdan doğar (Bölüm 7.2).

8. **Topolojiler iki tarafta aynı çerçeveye oturuyor.** IBM'in dört dayanıklılık deseni (M1–M4, SG24-8446) ile Oracle'ın MAA katmanları (Bronze, Silver, Gold, Platinum) neredeyse birebir eşleşiyor ve Oracle her katman için RTO/RPO yayımlıyor [ORACLE-MAA-2026]. PostgreSQL + Patroni için RTO, Patroni'nin zamanlama parametrelerinden türetilebiliyor (varsayılan ayarla düğüm kaybında ~27–41 saniye) [PIGSTY-RTO]. Olay tabanlı availability denklemi x86 tarafına yalnızca bir terim değiştirilerek (CPC donanım kesintisi yerine düğüm arızası × yük devretme süresi) uygulanabiliyor (Bölüm 8).

9. **Personel için tek kaynak ailesi bulundu ve o da üretici kaynağı.** IBM Eagle TCO ekibi dağıtık sunucular için de oran yayımlamış: fiziksel sunucu başına yılda 32 saat donanım işi, yazılım imajı başına yılda 36 saat; adanmış Intel sunucuda 30,7 sunucu/FTE, sanallaştırılmışta 52,5 VM/FTE [IBM-EAGLE-LABOR]. Mainframe personeli de aynı kaynak ailesinden geldiği için yanlılık iki tarafta aynı yönde olur (IBM'in çıkarı dağıtık personeli yüksek göstermektir). Bağımsız bir dağıtık personel oranı bulunamadı; Avasant/Computer Economics verisi ücretli. Bu, x86 tarafının en zayıf veri noktası (Bölüm 10).

10. **Kullanıcının kendisi ölçebilir.** Mainframe tarafında ölçüm imkânı yoktur, x86 tarafında vardır. sysbench oltp_read_write'ı bilinen bir sunucuda (laboratuvar makinesi ya da bulutta bare-metal) kontrollü bir protokolle koşmak, x86 köprüsünün en güçlü kalibrasyonu olur (Bölüm 3.8). **[KARAR]** (K6).

---

## 2. Köprüler: İki Sistemi Karşılaştırmak İçin Gerekenler

Mainframe ve x86 farklı iç birimlerle çalışır (PCI/MSU ile çekirdek/vCPU). Karşılaştırmanın geçerli olması için her katmanda bir **köprü** gerekir: iki tarafın aynı girdiyle beslendiği, aynı ölçüyle ölçüldüğü ya da aynı kuralla fiyatlandığı bir arayüz. Tablo, her köprünün iki taraftaki karşılığını ve bu araştırmadan sonraki durumunu gösterir.

| # | Köprü | Mainframe tarafı (mevcut) | x86 tarafı (önerilen) | Durum |
|---|---|---|---|---|
| K1 | İşlem birimi | `oltp_rw` bileşimi: 14 okuma + 4 yazma + 1 commit; w = 9,15 (v3 §4.4) | sysbench `oltp_read_write`: aynı bileşim [TENCENT-METHOD]; profil değişince x86 CPU'su da bileşimden ölçeklenir | Tanım hazır. x86 profil ölçeklemesi için kendi ölçüm gerekiyor (3.8) |
| K2 | Kapasite birimi ve nesil normalizasyonu | PCI (LSPR); TPS_PER_PCI = 7,939 (REDP-5320) | Çekirdek başı SPECrate2017_int_base; TPS_PER_SPECINT = ölçülmüş TPS / (çekirdek × SPECint/çekirdek) | Üç veri noktasıyla tutarlı (3.3). SPECint'in OLTP'yi temsil etmesi bir varsayım (14.1) |
| K3 | Kuyruk ve latency | Fiziksel CP başına bağımsız M/M/1; D_io; %90 tavan (v3 §5) | Aynı aile: çekirdek başına bağımsız M/M/1 (tutucu) + D_io + ağ RTT + senkron replikasyon terimi | Tasarım hazır. Ağ ve NVMe gecikme parametreleri aralıklı (Bölüm 9) |
| K4 | Availability denklemi | D = saha olayı × min(olay, T_rec) + planlı + D_cpc (v3 §6.3) | Aynı denklem; saha olayı parametreleri **ortak**; D_cpc yerine N_düğüm × λ_düğüm × T_failover | Tasarım hazır (Bölüm 8) |
| K5 | Topoloji | M1–M4, SG24-8446 desenleri | X1–X4: Oracle MAA Bronze/Silver/Gold/Platinum ve Patroni karşılıkları | Eşleme hazır (8.2). X4'ün PostgreSQL karşılığı ticari ürün gerektiriyor **[KARAR]** |
| K6 | Storage arayüzü | `data_tb`, büyüme, profil IOPS'u, topoloji kopya sayısı (v3 §8.1.6) | Aynı girdiler + DB mimarisine bağlı kopya sayısı | Storage tipi **[KARAR]** (7.1) |
| K7 | Yedek | 4 hafta saklama, %3 günlük değişim, log hacmi; üç hedef (TS7770, on-prem nesne, S3) | Aynı hacim kuralları; hedefler on-prem nesne ve S3 (aynı fiyat fonksiyonu); yazılım pgBackRest/RMAN | Tasarım hazır (Bölüm 11) |
| K8 | Personel | IBM Eagle + Gartner eğrisi, kurulu kapasiteye göre; BLS yüklü ücret (v3 §7.7) | IBM Eagle dağıtık saatleri + rol tabanlı taban ekip; kurulu düğüm/imaja göre; aynı BLS ücretleri | Kaynak zayıf (Bölüm 10) |
| K9 | Fiyat dönemi | 2004 AWLC (nominal, seviye çarpanı), 2022 DS8900F listesi, 2026 maaş | 2026 fiyatları, bellek/SSD şoku ile | **Açık köprü.** Ortak modülde bir "fiyat dönemi" kuralı gerekiyor (12.2) |
| K10 | Zaman ve finansman | 5 yıl NPV, r = %7, g = %10, açgözlü yükseltme, capex yıl başı (v3 §9.10) | Aynı kurallar; yükseltme = düğüm ekleme ya da düğüm büyütme | Değ. #6 tehdit 3.5 (teknoloji yenilemesi) iki tarafta birlikte karara bağlanmalı |
| K11 | Belirsizlik çıktısı | 20 aralık parametresi; low/mid/high + tornado | Aynı yapı; x86'ya özgü ~18 parametre (Bölüm 12) | Tasarım hazır |
| K12 | Lisans tabanı | Sub-capacity: yük (R4HA) üzerinden; DR frame'i CBU ile kalıcı kapasitesinden | Kurulu fiziksel çekirdek üzerinden (Oracle, VMware, OpenShift); DR düğümleri de lisanslanır | Yapısal asimetri; modellenmeli, eşitlenmemeli (6.5) |

Tablo ayrıca Adım 6'daki ortak modülün içeriğini somutlaştırır: K4 (saha olayları), K7 (nesne depolama fiyat fonksiyonu), K8 (BLS ücretleri ve taban ekip kuralı), K9 (fiyat dönemi) ve K10 (NPV kuralları) iki tarafın **aynı fonksiyonu çağırması** gereken yerlerdir.

---

## 3. Kapasite Köprüsü: Benchmark'tan Çekirdek Başına TPS'e

### 3.1. Ne bulmamız gerekiyordu

Mainframe köprüsünün x86 karşılığı: (a) oltp_rw bileşiminde ölçülmüş, (b) donanımı bilinen, (c) PostgreSQL ve Oracle için ayrı, (d) farklı nesil donanımları ortak bir ölçeğe taşınabilen bir "çekirdek başına TPS" katsayısı. Ayrıca sanallaştırma ve konteyner katmanının bu katsayıdan ne kadar götürdüğü.

### 3.2. Ne bulduk: PostgreSQL oltp_read_write ölçümleri

| Kaynak | Ortam | PostgreSQL | Veri | Ölçülen | Not |
|---|---|---|---|---|---|
| [VONNG-PERF] | AWS c5d.metal, bare-metal; 2 × Xeon Platinum 8275CL (48 fiziksel çekirdek, 96 mantıksal), 192 GB, yerel NVMe | 14.5 | 16 × 10M satır (160M) | oltp_read_write 519.069 **QPS** → 25.953 TPS (QPS/20) | Birim makalede "QPS" diye etiketli; oltp_rw işlemi 20 sorgu olduğundan TPS = QPS/20. Makale "96C" diyor; c5d.metal 96 mantıksal = 48 fiziksel çekirdektir |
| [ROCKDATA-2026] | Huawei Cloud c9.8xlarge, 32 vCPU, 128 GB; bellek içi senaryo | 18.6 | 20 × 5M satır (~24 GB) | 15.261 TPS (256 iş parçacığı) | Üretici kaynağı (Redrock), PostgreSQL çizgisi karşılaştırma tabanı. CPU modeli verilmemiş |
| [ROCKDATA-2026] | Aynı, 16 vCPU, karma (12 GB tampon) / I/O-ağırlıklı (2 GB tampon) | 18.6 | aynı | 5.916 / 4.427 TPS | Önbellek isabeti düştükçe verim %25–30 düşüyor |
| [TENCENT-RESULT] | Tencent Cloud, 1 / 4 / 8 / 48 "çekirdek", tam önbellek, birincil + asenkron replika | 14.2 | 64–256 × 25K satır | 864 / 4.032 / 5.777 / 8.675 TPS | Çekirdek başına 864 → 1.008 → 722 → 181. 48 çekirdekte çöküş: ya ölçeklenme sınırı ya da istemci sınırı |
| [TENCENT-RESULT] | Aynı, veri belleğin 2 katı | 14.2 | 64–640 × 10M | 683 / 2.921 / 4.037 / 5.746 TPS | I/O-ağırlıklı rejim |
| [ALIBABA-PG16] | Alibaba Cloud, 8 çekirdek, 64 GB, ESSD PL3 bulut diski | 16.10 | 8 × 8M satır, 128 GB (bellekten büyük) | 649 TPS | Ağ diski ile I/O-sınırlı rejim: çekirdek başına ~81 |

**Okuma:** Tablo iki ayrı rejim gösteriyor. Veri bellekte olduğunda verim CPU-sınırlıdır ve çekirdek başına yüzlerce TPS mertebesindedir. Veri bellekten büyük ve disk ağ üzerindeyken verim storage gecikmesiyle sınırlanır ve 5–10 kat düşebilir. Model bu iki rejimi tek bir katsayıya gömmemeli; mainframe tarafındaki gibi CPU kapasitesi (w üzerinden) ve storage kısıtı (IOPS ve D_io üzerinden) ayrı tutulmalı.

### 3.3. Nesil normalizasyonu ve önerilen orta değer

Bulut ölçümlerinde CPU modeli ve "çekirdek"in fiziksel mi mantıksal mı olduğu çoğu zaman belirsiz. Bu yüzden köprünün çapası, donanımı bilinen tek bare-metal ölçüm olan [VONNG-PERF] olmalı; diğerleri çapraz kontrol olarak kullanılmalı.

SPECrate2017_int_base, çekirdek başına:

| Sistem | CPU | Çekirdek | SPECrate2017_int_base | Çekirdek başına | Kaynak |
|---|---|---|---|---|---|
| Dell PowerEdge M640 | 2 × Xeon Platinum 8270 (Cascade Lake, 8275CL'nin perakende kardeşi) | 52 | 309 | 5,94 | [SPEC-8270] |
| Dell PowerEdge R760 | 2 × Xeon Gold 6548Y+ (Emerald Rapids) | 64 | 628 | 9,81 | [SPEC-R760] |
| HPE ProLiant DL380 Gen12 | 2 × Xeon 6787P (Granite Rapids) | 172 | 1.570 | 9,13 | [SPEC-DL380G12] |

Normalizasyon [DERIVED]:

```
TPS_per_core(c5d.metal)  = 25.953 / 48            = 541   (Cascade Lake, oltp_rw, bellek içi)
TPS_PER_SPECINT          = 541 / 5,94             = 91    (TPS / SPECint birimi, çekirdek başına)
TPS_per_core(R760)       = 91 × 9,81              ≈ 893
TPS_per_core(DL380 Gen12)= 91 × 9,13              ≈ 831
```

Çapraz kontrol: [ROCKDATA-2026] bellek içi senaryoda 32 vCPU (16 fiziksel çekirdek varsayımıyla) çekirdek başına ~954 TPS; [TENCENT-RESULT] 4 çekirdekte ~1.008 TPS/çekirdek. Bu üç değer birbirinin ~±%15'i içinde. 8275CL'nin taban frekansı 8270'ten biraz yüksek olduğu için çapa hafif iyimser olabilir.

**Önerilen parametre:** `X86_TPS_PER_SPECINT_CORE` = 91 oltp_rw TPS / SPECint birimi [DERIVED]; aralık low 70 / high 105 [ASSUME, Tencent ve Rockdata çapraz kontrolünün dağılımı]. R760 sınıfında bu, çekirdek başına ~690 / ~890 / ~1.030 TPS eder.

**Mainframe ile simetri:** Mainframe'de TPS_PER_PCI iki REDP-5320 noktasının ortalamasıdır ve %3,1 farkı belirsizlik olarak raporlanır (v3 §4.2). x86'da çapa tek bir bare-metal noktadır; dağılım daha geniştir ve bu, köprünün belirsizlik aralığı olarak raporlanmalıdır.

### 3.4. Düğüm içi ölçeklenme

LSPR'de n-way ölçeklenme kaybı her kademenin PCI'sinin içindedir. x86'da SPECrate çok çekirdekli verimi ölçer ama bir veritabanının kilit çekişmesini ölçmez. Tencent eğrisi (çekirdek başına 1.008 → 722 → 181) ve PostgreSQL'in yazma yolundaki bilinen darboğazlar (WAL flush, ProcArrayLock, CLOG) [PGCON-2016] düğüm içinde alt-doğrusal ölçeklenme olduğunu gösteriyor. Ancak 48 çekirdekli bulut noktasının bir istemci sınırı mı yoksa gerçek bir tavan mı olduğu belli değil; [VONNG-PERF] 48 fiziksel çekirdekte çekirdek başına 541 TPS (normalize ~890) ile daha iyimser.

**Model önerisi:** `S(n) = (n / n_ref)^(b_x86 − 1)` biçiminde bir düğüm içi verim çarpanı; n_ref = 48 (çapanın çekirdek sayısı), b_x86 aralığı 0,80 / 0,90 / 1,00 [ASSUME]. Bu çarpan, mainframe personel eğrisindeki alt-doğrusal ölçekle aynı biçimdedir. Kendi ölçümümüz (3.8) 16, 32, 64 çekirdekte koşulursa b_x86 doğrudan kalibre edilir.

### 3.5. Oracle

**Bulgu:** Oracle Technology Network lisansı, lisans sahibinin "Oracle'ın önceden izni olmadan herhangi bir Program benchmark testinin sonuçlarını açıklamasını" yasaklar [ORACLE-OTN]. Bu yüzden aynı donanımda Oracle ve PostgreSQL'i karşılaştıran bağımsız, güvenilir bir ölçüm yok. Bulunan tek karşılaştırma (Oracle 19c SE2 vs PostgreSQL 17.4, HammerDB, 8 vCPU'lu Windows VM; PostgreSQL NOPM'de %108 önde) [DZONE-SE2] Standard Edition, Windows ve tek kullanıcılı bir sanal makine üzerinde yapıldığı için temsil edici değil. Oracle'ın resmî TPC-C sonuçları x86'da 2012'de kesiliyor (Cisco UCS C240 M3, 2 × E5-2690, Oracle 11g SE One, 1,6M tpmC, $0,47/tpmC) [FLASHDBA-2012]; farklı iş yükü, farklı sürüm ve 14 yıllık donanım.

**Model önerisi:** `ORACLE_THROUGHPUT_FACTOR` = Oracle'ın aynı çekirdekte PostgreSQL'e göre oltp_rw verimi. low (Oracle lehine) 1,30 / mid 1,00 / high 0,80 [ASSUME, kaynakla daraltılamaz]. `project_context_restore_v4.md` §7'deki "%20–40 fazla" iddiası kaynaksızdı; mid değeri 1,0 seçildi çünkü kaynak olmadan bir yön iddia etmek savunulamaz. Tornado bu parametrenin sonucu ne kadar oynattığını gösterecek. Oracle çekirdek başına lisanslandığı için bu parametre maliyeti verim üzerinden iki kez etkiler (daha az çekirdek = daha az lisans).

**Tezde nasıl yazılmalı:** "Oracle tarafının kapasite katsayısı kalibre edilemez; bu, Oracle'ın lisans şartlarından kaynaklanan yapısal bir veri sınırıdır ve sonuç bu parametrenin aralığıyla birlikte raporlanır." Bu cümle akademik açıdan bir zayıflık değil, literatürdeki boşluğun belgelenmesidir.

### 3.6. Platformlar arası tutarlılık kontrolü (köprü K2)

İki taraf birbirinden bağımsız iki zincirle hesaplanır: mainframe'de REDP-5320 + LSPR + SQL maliyet varsayımları, x86'da sysbench ölçümü + SPECrate. Aynı oltp_rw işlemi için:

| | Mainframe | x86 (R760 sınıfı) |
|---|---|---|
| Kapasite birimi başına TPS | z16 tam-hız CP (3931-701, 2.253 PCI): 2.253 × 7,939 / 9,15 ≈ **1.955** | Fiziksel çekirdek: **~893** |
| İşlem başına CPU süresi | ~0,51 ms (z16 CP) | ~1,12 ms (çekirdek, SMT dahil) |
| Oran | 1 z16 CP ≈ **2,2** R760 çekirdeği (iki tarafın aralık uçlarıyla ~1,2–3,9) | |

Bu değer bir doğrulama değil, **büyüklük mertebesi kontrolüdür**: z16 CP'si 5,2 GHz'te çalışır ve çok büyük önbelleklere sahiptir; x86 çekirdeğinin yarısı kadar iş yapan bir CP beklenmez, on katı da beklenmez. Kontrolün asıl değeri, iki köprüden birinde bir mertebe hatası olsaydı burada görünecek olmasıdır. Asimetri de not edilmeli: x86 değeri ölçülmüş, mainframe değeri bileşimden (CPU_US_PER_SQL_READ = 30 µs varsayımı) hesaplanmıştır. Mainframe'in okuma SQL CPU'su 15–60 µs aralığında taranırken (w = 6,7–14,0) oran ~3,0–1,4 arasında oynar.

### 3.7. Sanallaştırma ve orkestrasyon katmanı

| Kaynak | Bulgu | Not |
|---|---|---|
| [REDHAT-OCPV-2025] | OpenShift Virtualization'da MariaDB, HammerDB; 4 örnekte VM'ler bare-metal (pod) verimin %80'ine ulaşıyor; 8 ve 16 örnekte farkın kapandığı söyleniyor | [VENDOR] Red Hat. Tek düğüm, yerel NVMe |
| [PT-VSPHERE-OCPV-2024] | Aynı Dell R650'de SQL Server, TPROC-C: 10 VM'de vSphere 8 U3, OpenShift Virtualization 4.16'dan %27,6 fazla NOPM | [VENDOR] Broadcom'un blogunda yayımlandı; Principled Technologies çalışması |
| [EDB-LOCALPV] | Kubernetes'te yerel kalıcı birimle sıralı okuma bare-metal'e göre −%3,6, yazma −%0,8; ağ tabanlı paylaşımlı PV'de −%89–95 | Ham storage testi; PostgreSQL değil. Sonuç storage tipi kararını doğrudan destekliyor (7.1) |

**Model önerisi:** iki ayrı çarpan.
- `VIRT_OVERHEAD`: vSphere low 0,03 / mid 0,07 / high 0,15; OpenShift Virtualization low 0,05 / mid 0,12 / high 0,25 [ASSUME, yukarıdaki iki üretici kaynağının arasından]. İki üretici kaynağı birbirine rakip olduğu için iki uç da taraflıdır; aralık bu yüzden geniş.
- `CONTAINER_OVERHEAD`: Kubernetes/OpenShift üzerinde PostgreSQL için 0 / 0,02 / 0,05 [ASSUME]; storage yerel kalıcı birimse ihmal edilebilir [EDB-LOCALPV].

**Mimari not:** v4 yığını "her zaman bir sanallaştırma katmanı var" der (`project_context_restore_v4.md` §4.8). Bu durumda veritabanı ya bir VM'de çalışır (VM üzerinde Patroni ya da Oracle) ya da VM'lerin içindeki bir Kubernetes kümesinde (operatörle). İkinci durumda iki katman üst üste biner ve iki çarpan birlikte uygulanır. OpenShift üzerinde PostgreSQL operatörlerinden Crunchy PGO Patroni kullanır, CloudNativePG kullanmaz; v4'teki "PostgreSQL + Patroni" tanımı operatör seçimini de sabitler (Bölüm 13, K7).

### 3.8. En güçlü kalibrasyon: kendi ölçümümüz (öneri)

Mainframe tarafında ölçüm yapma imkânımız yok; x86 tarafında var. Önerilen protokol:

1. Donanımı bilinen bir sunucu: bir üniversite laboratuvar makinesi ya da bulutta saatlik kiralanan bare-metal bir örnek (CPU modeli ve SPECrate değeri yayımlanmış olmalı).
2. PostgreSQL 17/18, sysbench 1.0.20+, `oltp_read_write`, veri belleğe sığacak boyutta (ör. 16 × 10M satır), sonra bellekten büyük boyutta.
3. 8, 16, 32, (64) çekirdekle (CPU affinity ya da VM boyutu ile) ve iş parçacığı sayısını taramayla; her noktada doygunluk TPS'i, p95/p99 latency ve CPU kullanımı.
4. Aynı koşu `oltp_read_only` ve `oltp_write_only` ile: okuma ve yazma SQL'inin x86 CPU maliyetini ayrıştırmak için (profil ölçeklemesi, K1).
5. Bir koşu senkron replikayla (`synchronous_commit = on`, aynı ağda ikinci düğüm): replikasyonun verim ve latency maliyeti.

Bu, 3.3'teki çapayı, 3.4'teki b_x86'yı, 3.7'deki konteyner çarpanını ve Bölüm 9'daki replikasyon terimini doğrudan kalibre eder. Yayımlanmış verinin işlem alt testlerinden (read_only, write_only) SQL maliyeti ayrıştırma denemesi [VONNG-PERF] negatif bir taban maliyet verdi (doygunlukta çekişme farklı), yani yayımlanmış veriyle bu ayrıştırma güvenilir yapılamıyor. **[KARAR]** (K6).

---

## 4. Ölçekleme Mimarisi ve Kapasite Tavanları

### 4.1. Ne bulmamız gerekiyordu

Clustered tarafta kapasitenin nasıl büyüdüğü: düğüm eklemek yazma kapasitesi ekliyor mu, yoksa yalnızca yedeklilik mi?

### 4.2. Ne bulduk

| DB mimarisi | Yazma ölçeklenmesi | Okuma ölçeklenmesi | Tek yazıcı tavanı | Kaynak |
|---|---|---|---|---|
| PostgreSQL + Patroni | Yok: tek birincil (single-primary); replikalar yazma eklemez | Replikalara yönlendirilirse var (oltp_rw'de her işlem yazdığı için kullanılamaz) | Tek düğümün kapasitesi | [PATRONI-REPL] |
| Oracle RAC (paylaşımlı disk) | Var: tüm düğümler aynı veritabanına yazar; Cache Fusion ile blok taşıma | Var | Uygulama ölçeklenmesi %80'in altındaysa çekişme işareti; 19c'de düğüm kaybında 15 sn altında toparlanma | [ORACLE-RAC-2024] |
| Oracle tek örnek + Data Guard | Yok (Patroni gibi) | Active Data Guard ile okuma | Tek düğüm | [ORACLE-MAA-2026] |
| PostgreSQL + Citus (dağıtık) | Var (sharding) | Var | — | v4 yığınında yok |

**Sonuç [DERIVED]:** R760 sınıfı tek bir düğüm, 3.3'teki katsayıyla ve 3.4'teki ölçeklenme kaybıyla, 64 çekirdekte kabaca 40–55K oltp_rw TPS taşır; sanallaştırma ve %90 tavan sonrası ~35–50K. Xeon 6 / EPYC 9005 sınıfı 128–192 çekirdekli düğümlerde SPECrate kapasitesi 2,5–3 kat büyür, ama PostgreSQL'in tek birincil üzerindeki yazma yolunun bu çekirdek sayılarında nasıl ölçeklendiğine dair güvenilir yayımlanmış veri bulunamadı.

### 4.3. Modele etkisi

- **PostgreSQL tarafında kapasite adımları sunucu boyutlarıdır.** Model, bir sunucu kataloğundan (çekirdek sayısı seçenekleri) birincil düğümün boyutunu seçer; replika sayısı availability ve RPO'dan gelir, kapasiteden değil. Bu, mainframe'in "kademe seç" mantığına beklenenden çok benzer: x86'da da kapasite ayrık adımlarla alınır, yalnızca adımlar daha küçük ve daha ucuzdur.
- **Tek yazıcı tavanı simetrik bir sınırlamadır.** Mainframe'de Parallel Sysplex modellenmediği için tek CEC tavanı (~187K TPS) var (v3 §4.4.4). PostgreSQL'de Citus modellenmezse tek düğüm tavanı (~35–50K TPS) var. Tez iki sınırı yan yana yazmalıdır. Tavanın üstünde x86 tarafında yalnızca Oracle RAC aday kalır.
- **Oracle RAC'ta düğüm sayısı kapasite ekler** ama her düğüm lisans ekler (çekirdek × 0,5 × [EE + RAC]). Ölçeklenme verimi için `RAC_SCALING_EFFICIENCY` = 0,80 / 0,90 / 0,95 [ASSUME; Oracle'ın %80 eşiği alt uç] önerilir.

---

## 5. Donanım Kataloğu ve Fiyatı

### 5.1. Ne bulmamız gerekiyordu

Üç sunucunun (Dell R760, HPE DL380 Gen11, Lenovo SR650 V3) yapılandırma seçenekleri, kapasite (SPECrate), fiyat, güç ve bakım.

### 5.2. Ne bulduk

**Nesil sorunu.** v4 dokümanı R760 / DL380 Gen11 / SR650 V3'ü seçmişti. 2025 başından beri bunların halefleri (Dell R770, HPE DL380 Gen12, Lenovo SR650 V4; Xeon 6 işlemcili) piyasada ve SPEC'te ölçülmüş durumda [SPECPOWER-2025Q1, SPEC-DL380G12]. 2026'da bir kurum yeni alımda büyük ihtimalle yeni nesli alır. Mainframe tarafı da güncel nesil olan z16'yı kullanıyor (z17 2025'te duyuruldu ama model z16'da). **[KARAR]** (K2): öneri, iki tarafta da "modelin referans nesli" kuralını aynı tutmak: z16 ile aynı döneme ait x86 nesli (R760 / Gen11 / V3, 2023–2024) ana senaryo, Gen12 sınıfı bir duyarlılık senaryosu.

**Güç (SPECpower_ssj2008, 2 soketli, %100 yük / boşta):**

| Sistem | CPU | Çekirdek | %100 yükte W | Boşta W | Kaynak |
|---|---|---|---|---|---|
| HPE DL380 Gen12 | 2 × Xeon 6787P | 172 | 924 | 220 | [SPECPOWER-2025Q1] |
| Lenovo SR650 V4 | 2 × Xeon 6787P | 172 | 782 | 218 | [SPECPOWER-2025Q1] |
| Dell R770 | 2 × Xeon 6787P | 172 | 943–960 | 157–164 | [SPECPOWER-2025Q1] |

SPECpower sistemleri az bellek ve az disk ile ölçülür; bir veritabanı düğümü (512 GB+ bellek, 8–24 NVMe) daha fazla çeker. Model önerisi: düğüm gücü = SPECpower %100 değeri × `X86_POWER_CONFIG_UPLIFT` (1,1 / 1,25 / 1,4) [ASSUME]. Mainframe tarafı da tepe güç kullanıyor (tutucu); simetri için x86'da da %100 yük değeri.

**Fiyat.** Sunucunun bütün fiyatı yayımlanmıyor; bileşen fiyatları kısmen yayımlanıyor. Bu yüzden bileşen tabanlı bir fiyat fonksiyonu öneriliyor:

```
düğüm_capex = şasi_ve_platform + 2 × CPU_fiyatı + bellek_GB × $/GB + NVMe_TB × $/TB + NIC/HBA
```

| Bileşen | Değer | Kaynak |
|---|---|---|
| CPU | Xeon Gold 6548Y+ (32 çekirdek) Intel önerilen fiyatı $4.173 | [INTEL-ARK-6548Y] |
| Bellek | 64 GB DDR5 RDIMM: ~$255 (şok öncesi, ~$4/GB) → ~$1.000 (~9 ay sonra) [PCSP-SERVER, Counterpoint aktarımı]; Ağustos–Ekim 2026 perakende $2.245–3.400 [CAPCOMP-RAM, BACLOUD-RAM]. TrendForce sunucu DRAM sözleşme fiyatlarının 2H26–2H27 boyunca çeyreklik artmaya devam edeceğini bekliyor [TRENDFORCE-2026-08] | |
| NVMe | Yeni kurumsal U.2 NVMe $300–1.172/TB (Ağustos 2026) [PCSP-SSD]; 30 TB TLC sınıfı ~$115/TB (Q3 2025) → ~$753/TB (Q3 2026) [PCSP-SSD, VDURA aktarımı] | |
| Bütün sistem | Dell'in açık yapılandırıcısında R760 amiral yapılandırması $53.250 liste; R760xs tabanı $15.957 (Ağustos 2026) [PCSP-SERVER] | Yapılandırıcı fiyatı pazarlıklı fiyatın üstündedir |
| Fiyat davranışı | Dell 1 Ocak 2026'da standart yapılandırmalara zam yaptı, bellek-yoğun yapılandırmalarda %30'a kadar artış uyardı; HPE teklif geçerliliğini 14 güne indirdi [PCSP-SERVER] | |

**Model önerisi:**
- Donanım fiyatı **bellek ve NVMe ayrı kalemler** olarak modellenmeli, çünkü 2026 şoku tam olarak bu iki kalemde. `MEM_USD_PER_GB` low $5 (şok öncesi) / mid $16 (2026 başı sözleşme mertebesi) / high $37 (Ağustos 2026 perakende) [DERIVED, yukarıdaki kaynaklardan]; `NVME_USD_PER_TB` low $120 / mid $400 / high $750.
- Şasi + platform (anakart, güç kaynakları, fanlar, yönetim kartı, temel destek) için `X86_PLATFORM_COST` $8K / $12K / $18K [ASSUME; R760xs taban fiyatından ve yeniden üretilmiş R760 fiyatlarından kaba kestirim, doğrulanmalı].
- `X86_HW_DISCOUNT`: storage indirimiyle aynı mantık; 0,50 / 0,35 / 0,20 [ASSUME].
- Amortisman 5 yıl (mainframe ile aynı); bakım: ilk 3 yıl üretici garantisi/ProSupport fiyata dahil, 4.–5. yıl donanım değerinin %10–15'i [ASSUME, doğrulanmalı]. Mainframe'de garanti 1 yıl; x86'da 3 yıl tipik olduğu için bu, gerçek bir yapısal farktır ve eşitlenmemelidir.

**Kaynak notu:** Sunucu fiyatı x86 tarafının en kaba parametresi olarak kalıyor. Kamu ihale kayıtları (ör. bir üniversitenin ya da kamu kurumunun R760 alımı) en iyi bağımsız kaynak olur; bu araştırmada erişilebilir bir kayıt bulunamadı. Ayrıca donanım x86 toplam maliyetinin küçük bir payı olacağı için (Bölüm 6'daki lisanslar ve personel daha büyük) bu kabalık sonucu sınırlı etkiler; tornado bunu gösterecek.

---

## 6. Yazılım Lisansları

### 6.1. VMware (Broadcom)

| Bulgu | Değer | Kaynak |
|---|---|---|
| Ürünler | vSphere Foundation (VVF) ve Cloud Foundation (VCF), yalnızca abonelik, fiziksel çekirdek başına yıllık | [ACEMQ-VVF] |
| Liste fiyatı | VVF $135, VCF $350 / çekirdek / yıl (Broadcom fiyat listesi yayımlamıyor; iş ortağı listelerinden aktarım) | [ACEMQ-VVF] |
| Gerçek teklifler (Eylül 2025 – Eylül 2026, 37 teklif) | VVF 1 yıl $117–196, 3 yıl $100–160; VCF 1 yıl ~$344, 3 yıl $257–348 | [ACEMQ-RENEW] |
| Asgari | CPU başına en az 16 çekirdek; sipariş başına en az 72 çekirdek (Nisan 2025'ten beri) | [ACEMQ-VVF] |
| vSAN hakkı | VVF çekirdek başına 0,25 TiB, VCF 1 TiB | [ACEMQ-VVF] |

**Model önerisi:** `VSPHERE_USD_PER_CORE_YEAR` low $100 / mid $150 / high $350 (VVF teklifleri → VCF). 16 çekirdek/CPU ve 72 çekirdek/sipariş asgarileri fonksiyona yazılmalı: küçük kurulumda bu asgari, mainframe'in AWLC taban ücretine (aylık $3.960) benzer bir **sabit maliyet tabanı** yaratır ve düşük TPS'te x86'yı da pahalılaştırır. Kaynak tek bir iş ortağının satış hattıdır ([ACEMQ-RENEW] kendisi "şekli gösterir, ondalığı değil" diyor); aralık bu yüzden geniş.

### 6.2. Red Hat (OpenShift, OpenShift Virtualization, RHEL)

| Bulgu | Değer | Kaynak |
|---|---|---|
| Sayım birimi | Çekirdek çifti (2 çekirdek ya da 4 vCPU) veya bare-metal soket çifti (1 Ocak 2025 sonrası yeni fiyatla 128 çekirdeğe kadar; öncesi 64) | [LICENSEWARE-OCP] |
| Sayılmayan | Kontrol düzlemi düğümleri; yalnızca altyapı işi çalıştıran altyapı düğümleri | [LICENSEWARE-OCP] |
| OpenShift Container Platform | Soket çifti başına ~$10–13K/yıl liste; büyük alımlarda $6–9K | [VENDORBENCH-OCP] |
| OpenShift Platform Plus | OCP'den %40–60 fazla (~$22K/soket çifti) | [VENDORBENCH-OCP] |
| OpenShift Kubernetes Engine | OCP listesinin ~%40–50'si | [VENDORBENCH-OCP] |
| OpenShift Virtualization Engine | Yalnızca VM; premium, 1–2 soket, 128 çekirdeğe kadar: $9.880/yıl (CDW); RHEL misafir hakkı dahil değil | [CDW-OVE, LICENSEWARE-OCP] |
| RHEL for Virtual Datacenters | Fiziksel düğüm başına $2.904/yıl (hizmet sağlayıcı sözleşme listesi) | [CCSP-RH] |

**Model önerisi:** OpenShift ve OpenShift Virtualization **düğüm (soket çifti) başına** fiyatlanır, vSphere ve Oracle **çekirdek başına**. Bu fark çekirdek yoğunluğu yüksek düğümlerde OpenShift'i avantajlı yapar ve modelde korunmalıdır. `OCP_USD_PER_SOCKETPAIR_YEAR` low $6K / mid $11K / high $15K; `OVE_USD_PER_NODE_YEAR` $6K / $8K / $10K [aralıklar yukarıdaki kaynaklardan, ASSUME]. "Vanilla Kubernetes" seçeneğinde lisans 0, ama destek ve personel farkı Bölüm 10'da yakalanmalı. Kaynakların hiçbiri Red Hat'in kendi fiyat listesi değil; Red Hat liste fiyatı yayımlamıyor.

### 6.3. Oracle Database

| Bulgu | Değer | Kaynak |
|---|---|---|
| Liste fiyatı (işlemci başına) | EE $47.500 · RAC $23.000 · Multitenant $17.500 · Advanced Security $15.000 · Partitioning $11.500 · Diagnostics $7.500 · Tuning $5.000; 2020'den beri aynı | [REDRESS-PL2026] (Oracle'ın Eylül 2026 listesinin aktarımı; doğrulanmalı) |
| Active Data Guard | 2009 listesinde $10.000; güncel liste aktarımda yok (yaygın kabul $11.500, doğrulanmalı) | [ORACLE-PL2009] |
| Destek | Net lisans bedelinin yıllık %22'si | [REDRESS-PL2026] |
| Çekirdek faktörü | Intel Xeon (Platinum/Gold 8xxx–5xxx, Xeon 6 6xxxP dahil) ve AMD EPYC 9005/9004 için **0,5**; tablo Ocak 2026 tarihli | [ORACLE-CORE] |
| İndirim | Yeni EE alımında anlaşma büyüklüğüne göre %16–31 ($50K–500K), %40–60 ($500K–5M), %60–75 ($5M–25M); ortalama indirim %57'den %44'e düşmüş | [OLE-NET2026, REDRESS-PL2026] (danışman kaynakları; örneklem belirtilmemiş) |
| Sanallaştırma kuralı | VMware "yumuşak bölümleme"dir ve lisans sayısını sınırlamak için kullanılamaz; VM'in çalışabileceği bütün fiziksel çekirdekler lisanslanır | [ORACLE-PART] |
| Destek politikası | Oracle, VMware üzerindeki Oracle'ı destekliyor; RAC için politika yalnızca on-prem; "fiziksel donanımda yeniden üret" şartı 2019'da kaldırıldı | [VMW-249212] |
| Standby lisansı | Data Guard standby'ı tam lisanslanır (aynı sürüm ve seçenekler); "10 gün kuralı" yalnızca paylaşımlı diskli failover kümelerine uygulanır | Danışman kaynakları (doğrulanmalı; Oracle "Licensing Data Recovery Environments" belgesiyle teyit edilmeli) |

**Model önerisi:**
- `oracle_processors = ceil(lisanslanan_fiziksel_çekirdek × 0,5)`; lisanslanan çekirdek, Oracle VM'lerinin çalışabileceği **bütün hostların** çekirdeğidir. Pratikte kurumlar Oracle için ayrı bir vSphere kümesi kurar; model Oracle'ı **adanmış düğümlerde** varsayar (en ucuz uyumlu düzen).
- Lisans capex olarak alınır ve 5 yılda amortize edilir (mainframe donanımıyla aynı kural); destek her yıl net lisansın %22'si, artış sınıfı yazılım (%3).
- `ORACLE_DISCOUNT` low 0,60 / mid 0,45 / high 0,20.
- Yığın: EE + RAC (X1–X3'te RAC'lı varyant) + Diagnostics + Tuning (operasyon için fiilen zorunlu) + Active Data Guard (X3–X4). Partitioning ve Advanced Security isteğe bağlı; ana senaryoda dışarıda [ASSUME].

### 6.4. PostgreSQL

- Lisans: 0. Patroni ve pgBackRest açık kaynak.
- Ticari destek isteğe bağlıdır (EDB, Crunchy, IBM). Fiyatlar yayımlanmıyor; bulunan ikincil sayfalar güvenilir değil. **Model önerisi:** `PG_SUPPORT_USD_PER_CORE_YEAR` low $0 (destek yok, iç ekip) / mid $500 / high $1.500 [ASSUME, kalibre edilemedi]. Akademik gerekçe: destek almayan bir kurum riski personelle taşır; destek alan kurum ücret öder. İki uç aralıkta.
- X4 (iki bölgede aktif-aktif) PostgreSQL'de çekirdek açık kaynakta yok; EDB Postgres Distributed gibi ticari bir ürün gerekir. **[KARAR]** (K4).

### 6.5. Yapısal asimetri: kurulu çekirdek ile tüketim

Mainframe yazılımı (AWLC) tüketilen MSU'nun aylık R4HA tepesine göre faturalanır ve DR frame'i CBU kuralıyla yalnızca kalıcı (küçük) kapasitesinden faturalanır (v3 §6.7). x86'da Oracle, vSphere ve OpenShift **kurulu** çekirdek ya da düğüm üzerinden lisanslanır; Data Guard standby'ı ve DR sitesindeki düğümler tam lisans ister. Bu fark eşitlenmemeli, modellenmelidir: x86'da DR'ın yazılım maliyeti mainframe'den oransal olarak yüksek çıkabilir. Yıllık simülasyonda da x86'nın CoD karşılığı yoktur: on-prem'de alınmış çekirdeğin lisansı boşta da ödenir. Bu, `project_context_restore_v4.md` §7.6'daki "on-prem'de fark CoD kadar keskin değil" beklentisinin somut nedenidir.

**CICS karşılığı yok.** v4 §5'teki tespit geçerli: mainframe'de CICS TS ayrı bir MSU lisansıdır; x86'da işlem yönetimi uygulama sunucusuna ve veritabanının ACID'ine bırakılır. Uygulama sunucusu katmanı (ör. Java uygulama sunucuları) kapsam dışında kalırsa, mainframe'de CICS'in CPU'su ve lisansı modelde, x86'da uygulama katmanının CPU'su ve lisansı modelin dışındadır. Bu bir kapsam asimetrisidir ve tezde açıkça yazılmalı (14.4).

---

## 7. Storage

### 7.1. Storage tipi: DB mimarisine bağlı öneri **[KARAR]**

| DB mimarisi | Önerilen storage | Gerekçe | Kopya sayısı |
|---|---|---|---|
| Oracle RAC | Paylaşımlı SAN, all-flash dizi (Fibre Channel ya da NVMe-oF) | RAC paylaşımlı disk mimarisidir; ASM ile tek bir veritabanı kopyası bütün düğümlere görünür | Site başına 1 kopya (dizi içi RAID) + DR sitesinde Data Guard kopyası |
| PostgreSQL + Patroni | Yerel NVMe (her düğümde), replika sayısı kadar kopya | Paylaşımsız mimari; Kubernetes'te yerel kalıcı birim bare-metal'e yakın (−%1–4), ağ tabanlı paylaşımlı birim çok yavaş (−%89–95) [EDB-LOCALPV] | Düğüm sayısı (X1'de 3: birincil + senkron + asenkron) |
| Oracle tek örnek + Data Guard | Yerel NVMe ya da SAN | Paylaşımsız; ikisi de mümkün | Düğüm sayısı |

Mainframe tarafında DS8900F'in tek alternatif olarak seçilmesinin gerekçesi "o platformda pratikte tek seçenek olması"ydı (v3 §8.1.2). x86'da storage seçimi DB mimarisinin bir sonucudur; bu yüzden DB'ye bağlamak "her katmanda seçenek" ilkesini bozmadan kombinasyon sayısını patlatmaz. vSAN (VVF/VCF'nin çekirdek başına storage hakkıyla) üçüncü bir seçenek olarak düşünülebilir, ama Phase 1 kuralı (katman başına tek storage) gereği ana senaryoda dışarıda öneriliyor.

### 7.2. Fiyat ve iki taraflı tanım sorunu

| Kalem | Değer | Kaynak |
|---|---|---|
| All-flash dizi (Q1 2026, kullanılabilir/etkin TB) | Dell PowerStore $65–170, Pure //X $70–175, NetApp AFF $65–190, HPE Alletra $100–215 (indirimli); liste $140–400 | [VENDORBENCH-AFA] |
| Dizi destek | İlk yıl donanımın %10–20'si; yıllık %10–25 | [VENDORBENCH-AFA] |
| Yerel NVMe | $300–1.172/TB yeni (Ağustos 2026) | [PCSP-SSD] |
| Mainframe karşılığı (mevcut model) | DS8900F etkin ~$2.590/TB ham (2022 liste × 0,30) | v3 §8.5 |

**Sorun:** AFA fiyatları "kullanılabilir/etkin" TB üzerinden (veri azaltımı dahil, Q1 2026, büyük ihtimalle NAND şokunun tam yansımasından önce). DS8900F fiyatı "ham" TB üzerinden ve 2022 listesinden. İkisi doğrudan karşılaştırılırsa x86 storage'ı 10 kattan fazla ucuz görünür.

**Model önerisi:**
- Ortak modülde **tek bir storage fiyatlama sözleşmesi**: fiyat ham TB üzerinden, RAID ve sıkıştırma oranı ayrı parametreler, aynı indirim yöntemi ve aynı fiyat dönemi (K9).
- AFA için ham $/TB = etkin $/TB × varsayılan veri azaltım oranı. Bu oran kaynakta verilmiyor; `AFA_DATA_REDUCTION` 1,5 / 2,5 / 4,0 [ASSUME] ile geri çevrilmeli.
- Mainframe tarafının DS8900F fiyatı da aynı dönem kuralına oturtulmalı (Adım 6'da). Bu, mainframe modeline dokunan bir değişiklik olduğu için ayrı bir karar konusudur.

### 7.3. Gecikme

- Yerel NVMe: sürücüde ortalama tamamlanma süresi ~141 µs (karma iş yükü), %99,99'luk dilim 769 µs [STORAGEREVIEW-P5520, VENDOR sponsorlu]. Mainframe'de t_okuma = 61 µs (zHyperLink + önbellek) ve t_yazma = 90 µs.
- SAN: FC/NVMe-oF ile dizi gecikmesi + fabric; birincil kaynak bulunamadı. `T_SAN_READ` 150 / 250 / 400 µs [ASSUME].
- PostgreSQL WAL yazımı: kapasitör korumalı (PLP) kurumsal NVMe'de fsync çok kısa; değer ölçümle (3.8) belirlenmeli.

### 7.4. Boyutlandırma

Mainframe ile aynı girdiler: `data_tb`, büyüme, planlama ufku (3 yıl), DB ek yükü (WAL/arşiv, geçici alan), IOPS = TPS × profil IOPS'u, aynı %70 IOPS tavanı. Fark yalnızca kopya sayısında (7.1) ve PostgreSQL'de her kopyanın ayrı bir düğümde, ayrı sürücülerle olmasında.

---

## 8. Availability

### 8.1. Denklem (köprü K4)

Mainframe denklemi (v3 §6.3) korunur; saha olayı parametreleri (λ_saha, d_kısa, d_uzun, p_uzun; Uptime kaynaklı) **iki tarafta aynı değerlerle ortak modülden** gelir. Tek değişiklik CPC donanım terimidir:

```
D(topo) = λ_saha × [ (1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec) ]   (ortak)
        + λ_planlı × T_planlı(topo)                                                    (x86'ya özgü değerler)
        + N_düğüm × λ_düğüm × T_failover(DB, topo)                                     (D_cpc'nin yerine)
```

Mainframe'de CPC arızası tek CPC'li M1'de hizmeti keser; M2–M4'te ikinci CPC devralır ama yalnızca DR'a geçişle (saatler/dakikalar). x86'da her topolojide site içinde bir HA kümesi vardır; bir düğüm arızası birkaç saniye ile birkaç dakika arası bir yük devretmeyle maskelenir. Bu terim x86'nın "çok düğüm = çok arıza, ama her biri kısa" karakterini modele taşır.

**λ_düğüm:** Microsoft'un 100.000'den fazla sunucuyu kapsayan çalışmasında sunucuların ~%8'i yılda en az bir donanım onarımı gördü; onarımların %78'i sabit disk kaynaklıydı [VISHWANATH-2010]. NVMe'li bugünkü sunucularda oran daha düşük olmalı. ITIC 2024'te güncel Lenovo x86 sunucuları sunucu başına yılda ~0,3–3 saniye plansız kesinti bildiriyor [ITIC-2024]; bu, onarım değil kesinti süresi ölçüsüdür. Yazılım kaynaklı düğüm düşmesi (işletim sistemi, veritabanı süreci, ağ bölünmesi) için kaynaklı bir oran bulunamadı. **Öneri:** `NODE_EVENTS_PER_YEAR` (donanım + yazılım) 0,03 / 0,10 / 0,30 [low ve mid VISHWANATH'tan aşağı doğru, high ASSUME].

### 8.2. Topoloji eşlemesi (köprü K5)

| Kod | Mainframe karşılığı | Oracle (MAA) | PostgreSQL + Patroni | RPO (tek site kaybı) | Kurtarma süresi T_rec (site) | Yük devretme T_failover (düğüm) |
|---|---|---|---|---|---|---|
| X1 | M1 (Reliable base) | Silver: RAC + Application Continuity, tek site | Tek sitede 3 düğüm, 1 senkron replika; etcd 3 üye | 24 saat (günlük yedek), M1 ile aynı | Alternatif site yok | RAC: 19c'de < 15 sn; Exadata dışı "tek haneli dakika" [ORACLE-RAC-2024, ORACLE-MAA-2026]. Patroni varsayılan: düğüm kaybında 27–41 sn, süreç çökmesinde 2–41 sn [PIGSTY-RTO] |
| X2 | M2 (Failover capable) | X1 + uzak sitede Data Guard standby (Max Availability), elle geçiş | X1 + uzak sitede standby küme (Patroni standby cluster), elle terfi | 0 (senkron) | Elle karar + teknik geçiş: 1 / 2 / 4 saat (M2 ile aynı; aşağıdaki not) | X1 ile aynı |
| X3 | M3 (Fault tolerant) | Gold: RAC + Active Data Guard + Fast-Start Failover (3. sitede gözlemci) | Çok siteli Patroni: senkron replika diğer sitede, DCS (etcd) 3 sitede | 0 | Oracle Gold: "saniyeler – 2 dakika" [ORACLE-MAA-2026]; Patroni: 30–90 sn + istemci yönlendirme. Öneri 1 / 2 / 5 dk | X1 ile aynı |
| X4 | M4 (Adaptive continuity) | Platinum: GoldenGate aktif-aktif (MAA bunu Exadata ile tanımlıyor; ticari x86'da "Gold+GoldenGate") | Çekirdek PostgreSQL'de yok: EDB Postgres Distributed gibi ticari ürün **[KARAR]** | Saniyeler (asenkron) | < 30 sn (Platinum seçenek 2: < 3 sn, Exadata) | X1 ile aynı |

**Elle geçiş süresi ortak bir parametre olmalı.** M2 ve X2'de kurtarma süresinin büyük kısmı teknoloji değil, insan kararı ve runbook'tur (felaketin ilanı, onay zinciri, uygulamaların yönlendirilmesi). Bu yüzden `MANUAL_FAILOVER_DECISION_HOURS` iki tarafta aynı parametre olarak ortak modüle alınmalı; platforma özgü olan yalnızca teknik geçiş süresi (DS8900F Metro Mirror'dan IPL / Data Guard ya da Patroni terfisi) olmalı. Bu, M2–X2 karşılaştırmasının "hangi ekip daha hızlı karar verir" sorusuna dönüşmesini önler.

**Kaynak kalitesi:** Oracle MAA değerleri üreticinin kendi tasarım hedefleridir [VENDOR]; mainframe tarafındaki GDPS değerleriyle aynı statüde. Patroni değerleri parametrelerden türetilen teorik sürelerdir [PIGSTY-RTO]; ölçüm değil. İkisi de aralıkla verilmeli.

**vSphere HA'nın rolü.** vSphere HA bir host arızasında VM'leri başka hosta taşıyıp yeniden başlatır; ikincil host 15–18 saniyede, birincil host ~50 saniyede "ölü" ilan edilir, ardından VM'in açılış ve veritabanı kurtarma süresi gelir [YELLOWBRICKS-HA]. Veritabanı katmanında Patroni ya da RAC zaten daha hızlı yük devrettiği için vSphere HA modelde ikincil bir mekanizmadır: DB katmanının T_failover'ı esas alınır.

### 8.3. Planlı kesinti

| Olay | Oracle | PostgreSQL | Not |
|---|---|---|---|
| İşletim sistemi / hypervisor yaması | RAC'ta rolling: 0 | Patroni switchover: saniyeler | Mainframe'de rolling IPL ile 0 |
| Veritabanı küçük sürüm | RAC rolling ya da Data Guard standby-first: ~0 | Replikaları güncelle + switchover: saniyeler | |
| Veritabanı büyük sürüm | Gold: < 30 sn (Data Guard transient logical) [ORACLE-MAA-2026] | pg_upgrade: dakikalar; mantıksal replikasyonla saniyeler | Model: X1'de `T_planlı` 5 / 15 / 60 dk, X3–X4'te 30 sn / 2 dk / 10 dk [ASSUME] |

λ_planlı mainframe'de yılda 0,25 / 0,5 / 1 kesintili işlemdi. x86'da kesintili işlem büyük sürüm yükseltmesi ve altyapı değişiklikleridir; aynı aralık önerilir.

---

## 9. Latency (köprü K3)

```
R(p) = D_ağ + D_io + D_repl + R_cpu(p)
R_cpu(p) = E[X_cpu] / (1 − ρ) × ln(1/(1−p)),   E[X_cpu] = c / ham_TPS (c = düğümdeki fiziksel çekirdek)
```

- **Aynı kuyruk ailesi.** Mainframe'de "c bağımsız M/M/1" tutucu üst sınırı kullanılıyor (v3 §5.3). `project_context_restore_v4.md` x86 için M/M/c öngörüyordu; bu iki taraf arasında tutuculuk asimetrisi yaratır (M/M/c daha iyimser). Öneri: x86'da da çekirdek başına bağımsız M/M/1. Mainframe günlüğündeki "iki taraf aynı kuyruk ailesiyle modellenmeli" notunun (PROJECT_LOG, 2026-10-31, madde 8) uygulanması budur.
- **D_ağ:** uygulama sunucusundan veritabanına gidiş-dönüş. Mainframe'de ağ terimi yok (CICS ve Db2 aynı sistemde). Bu terim x86'ya özgüdür ve gerçek bir yapısal farktır. `NET_RTT_MS` 0,05 / 0,15 / 0,5 ms (aynı veri merkezi) [ASSUME]; işlem başına gidiş-dönüş sayısı sysbench'te ifade başına birdir (20), saklı yordam kullanılırsa 1'e iner. Bu, x86 latency'sini belirleyen en büyük terim olabilir ve `ROUNDTRIPS_PER_TX` parametresi olarak açıkça görünmeli.
- **D_io:** profilin senkron okuma ve log yazımı sayısı × storage servis süresi (7.3). Mainframe'deki BP_HIT_RATIO ve GETPAGES parametreleri PostgreSQL'in shared_buffers + işletim sistemi önbelleği için aynı biçimde kullanılır.
- **D_repl:** senkron replikasyonda commit başına, replikanın WAL'ı alması için bir ağ gidiş-dönüşü. Fiberde 10 µs/km (mainframe'deki REPLICATION_S_PER_KM ile aynı fizik sabiti, ortak modül). EDB'nin ölçümü: 10 ms yapay gecikmede 40 istemcide `remote_write` yazma gecikmesine ~6,5 ms ekledi ve verimi %40 düşürdü; 3 ms'de etki yük altında ortadan kalktı [EDB-SYNCREP]. Aynı sitede (X1) etki küçük, metro mesafede (X2–X3) ölçülebilir.

---

## 10. Personel (köprü K8)

### 10.1. Ne bulmamız gerekiyordu

x86 altyapı ekibinin (Linux ve sanallaştırma yöneticisi, Kubernetes/OpenShift platform mühendisi, DBA, storage, ağ, güvenlik) düğüm, VM ve veritabanı sayısıyla nasıl ölçeklendiği; mainframe'deki kaynaklarla aynı statüde (bağımsız + üretici ikilisi) veriler.

### 10.2. Ne bulduk

| Kaynak | Bulgu | Statü |
|---|---|---|
| IBM Eagle, büyük bir finans kuruluşu [IBM-EAGLE-LABOR] | Adanmış Intel: 30,7 sunucu/FTE (sunucu başına yılda 67,8 saat); sanallaştırılmış Intel: 52,5 VM/FTE (VM başına 39,6 saat); fiziksel sunucu başına yılda 32 saat donanım işi, yazılım imajı başına 36 saat; yüklü maliyet $159.600/FTE (2.080 saat) | [VENDOR], 2011 |
| IBM Eagle, DR testi, ~200 dağıtık sunucu [IBM-EAGLE-2012] | Yıllık DR testi 14.952 kişi-saat (~75 saat/sunucu/yıl) vs mainframe tahmini 2.051 kişi-saat | [VENDOR], tek müşteri |
| Avasant / Computer Economics [AVASANT-2020] | Sunucu destek personeli BT personelinin %6,7–7,1'i (medyan, 2019–2020); sunucu/yönetici oranları ücretli raporda | Bağımsız ama oran yok |
| VMware topluluğu (2007) | 1:10–1:30 (konsolidasyonsuz), IDC'ye atfen 1:20 → 1:200 (konsolidasyon sonrası) | Eski, ikincil; alınmadı |

### 10.3. Modele nasıl girer

Mainframe personeli bir alt-doğrusal eğri + taban ekip olarak modellendi (v3 §7.7). Simetri için x86'da da **taban ekip + değişken iş** yapısı öneriliyor:

```
FTE_x86 = max( taban_x86 , (32 × N_fiziksel + 36 × N_imaj + h_db × N_db_küme) / 2.080 ) × topoloji_çarpanı × yığın_çarpanı
```

- 32 ve 36 saat [IBM-EAGLE-LABOR]. h_db (veritabanı kümesi başına DBA saati) için kaynak bulunamadı [ASSUME, aralık 300 / 600 / 1.200 saat/yıl].
- **Taban ekip mainframe ile aynı mantıkla:** 7/24 nöbet tutabilmek için asgari ekip. Mainframe'de 3 / 4 / 5 FTE. x86'da roller daha fazla (Linux, sanallaştırma, platform, DBA, storage); aynı 3 / 4 / 5 ile başlanması ve farkın `yığın_çarpanı` ile verilmesi öneriliyor. Bunu yapmazsak küçük x86 kurulumlarında Eagle saatleri 1 FTE'nin altında bir ekip verir ve x86 düşük TPS'te yapay olarak ucuz görünür.
- `yığın_çarpanı`: vanilla Kubernetes (destek yok, iç ekip) 1,2; OpenShift 1,0; Oracle RAC ek DBA uzmanlığı 1,1 [ASSUME]. Red Hat'in IDC/Forrester çalışmaları OpenShift ile operasyon verimliliği iddia ediyor, ama üretici sponsorlu ve yüzde değerleri sunucu oranı vermediği için alınmadı.
- Ücret: mainframe ile aynı BLS OEWS 2025 kaynakları (DBA $126.760, sistem yöneticisi $99.130, güvenlik $129.180 medyan) ve aynı yan hak çarpanları; aynı $122K / $162K / $215K yüklü maliyet. Mainframe uzmanlığının x86'ya göre ücret primi olup olmadığı açık bir sorudur; ana senaryoda iki taraf aynı ücretle, duyarlılıkta ±%15 primle.
- Kurulu kapasiteye göre: mainframe'de personel kurulu PCI'den hesaplanıyor (v3 §7.7.5). x86'da kurulu düğüm ve imaj sayısından; latency için alınan boş kapasite iki tarafta da personel ister görünür.

### 10.4. Açık kalan

Bağımsız bir dağıtık personel oranı x86 tarafının en kritik eksiğidir. Seçenekler: (1) Avasant "Server Support Staffing Ratios" raporuna üniversite kütüphanesi üzerinden erişim; (2) Gartner IT Key Metrics Data'nın dağıtık sunucu bölümüne erişim (mainframe tarafında Gartner 2016 kullanıldı); (3) Türkiye'deki bir bankadan anonim ekip/sunucu sayıları. Bu yapılmazsa personel aralığı geniş tutulmalı ve tezde "personel oranı iki tarafta da üretici kaynaklıdır" diye yazılmalı.

---

## 11. Enerji, Tesis ve Yedekleme

**Enerji.** Düğüm gücü SPECpower %100 değeri × yapılandırma çarpanı (5.2); dizi gücü üretici tepe değeri; elektrik fiyatı ve artış oranı mainframe ile aynı (ortak modül). Mainframe tarafında PUE (soğutma) ve raf alanı yok; x86'da da aynı kapsam (ikisi de dışarıda ya da ikisi de içeride) **[KARAR değil, ortak modül kuralı]**.

**Yedekleme (köprü K7).**
- Hacim kuralları mainframe ile aynı: 4 haftalık tam yedek + günlük artımlı (%3 değişim) + işlem bileşiminden log (PostgreSQL'de WAL, Oracle'da redo) hacmi, iki sitede. İşlem başına WAL baytı PostgreSQL'de Db2 log baytından farklıdır (full-page writes); ölçümle (3.8) belirlenmeli, o zamana kadar mainframe'in 400 B/yazma + 200 B/commit değeri × `WAL_FPW_FACTOR` 1,5 / 2 / 3 [ASSUME].
- Yazılım: pgBackRest (açık kaynak, lisans 0) ve Oracle RMAN (EE'ye dahil). VM düzeyinde Veeam gibi bir ürün veritabanı yedeği için gerekli değil; ana senaryoda dışarıda.
- Hedef: on-prem nesne depolama ve AWS S3, mainframe tarafındaki **aynı fiyat fonksiyonuyla** (v3 §8.10). TS7770 x86'da uygulanmaz. Kısıtlar (8 saatlik pencere, X1'de geri yüklemenin RTO'nun yarısına sığması) aynı.

---

## 12. Önerilen Aralık Parametreleri ve Ortak Modül Kuralları

### 12.1. x86'ya özgü aralık parametreleri (öneri)

**low = x86 lehine uç.**

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| X86_TPS_PER_SPECINT_CORE | 105 | 91 | 70 | 3.3 [DERIVED] |
| B_X86 (düğüm içi ölçek üssü) | 1,00 | 0,90 | 0,80 | 3.4 [ASSUME] |
| ORACLE_THROUGHPUT_FACTOR | 1,30 | 1,00 | 0,80 | 3.5 [ASSUME, kalibre edilemez] |
| VIRT_OVERHEAD (vSphere / OCP-V) | 0,03 / 0,05 | 0,07 / 0,12 | 0,15 / 0,25 | 3.7 [VENDOR × 2] |
| RAC_SCALING_EFFICIENCY | 0,95 | 0,90 | 0,80 | 4.3 |
| MEM_USD_PER_GB | 5 | 16 | 37 | 5.2 |
| NVME_USD_PER_TB | 120 | 400 | 750 | 5.2 |
| X86_PLATFORM_COST | $8K | $12K | $18K | 5.2 [ASSUME] |
| X86_HW_DISCOUNT | 0,50 | 0,35 | 0,20 | 5.2 [ASSUME] |
| VSPHERE_USD_PER_CORE_YEAR | 100 | 150 | 350 | 6.1 |
| OCP_USD_PER_SOCKETPAIR_YEAR | 6K | 11K | 15K | 6.2 |
| ORACLE_DISCOUNT | 0,60 | 0,45 | 0,20 | 6.3 |
| PG_SUPPORT_USD_PER_CORE_YEAR | 0 | 500 | 1.500 | 6.4 [ASSUME] |
| AFA_DATA_REDUCTION (geri çevirme) | 1,5 | 2,5 | 4,0 | 7.2 [ASSUME] |
| NODE_EVENTS_PER_YEAR | 0,03 | 0,10 | 0,30 | 8.1 |
| T_failover (Patroni / RAC) | 15 sn / 5 sn | 35 sn / 15 sn | 90 sn / 5 dk | 8.2 |
| h_db (DBA saati / küme / yıl) | 300 | 600 | 1.200 | 10.3 [ASSUME] |
| NET_RTT_MS | 0,05 | 0,15 | 0,5 | 9 [ASSUME] |

### 12.2. Ortak modüle (Adım 6) taşınacak kurallar

1. **Saha olayı parametreleri ve elle geçiş karar süresi** (K4, 8.2).
2. **Fiyat dönemi:** bütün fiyatlar 2026 USD'ye çevrilir. Mainframe'in 2004 nominal AWLC değerleri zaten `SW_PRICE_LEVEL_FACTOR` ile taranıyor; DS8900F 2022 listesi ve x86 bellek/NVMe fiyatları aynı "dönem" senaryosuna bağlanmalı. Önerilen senaryo anahtarı: `PRICE_EPOCH` = "2025-ortası" (şok öncesi) / "2026-Q3" (şok). Mainframe ve x86 aynı anahtarla çalışır. Bileşen şokunun mainframe fiyatlarına yansıyıp yansımadığına dair kaynak yok; IBM'in z16 fiyatları yayımlanmadığı için bu, tezde açık bir sınırlama olarak yazılmalı (14.2).
3. **Storage fiyatlama sözleşmesi:** ham TB, ayrı RAID ve veri azaltım oranı, aynı indirim yöntemi (7.2).
4. **Personel:** aynı BLS ücretleri, aynı taban ekip mantığı, kurulu kapasite kuralı (10.3).
5. **NPV:** aynı r, g, artış sınıfları, açgözlü genişleme; x86'da genişleme = düğüm büyütme ya da (RAC'ta) düğüm ekleme. Teknoloji yenilemesi (Değ. #6, tehdit 3.5) iki tarafta birlikte ya modellenir ya da birlikte dışarıda bırakılır.
6. **İki fiyat modu** (Emirhan'ın önerisi, 2026-11-02): kaynaklı fiyat seti ile kullanıcının fiyat dosyası; bu dokümandaki her fiyat parametresi bir anahtar adıyla tanımlandığı için kısmi geçersiz kılma doğrudan uygulanabilir.

---

## 13. Emirhan'ın Kararını Bekleyen Konular

| # | Konu | Seçenekler | Öneri |
|---|---|---|---|
| K1 | Storage tipi | (a) DB'ye bağlı: RAC → SAN, Patroni → yerel NVMe × replika; (b) her ikisi SAN; (c) her ikisi vSAN | (a): mimariyle tutarlı, kombinasyon sayısını artırmıyor, kaynakla destekli [EDB-LOCALPV] |
| K2 | Sunucu nesli | (a) R760 / DL380 Gen11 / SR650 V3 (z16 dönemi); (b) R770 / DL380 Gen12 / SR650 V4 (2025+) | (a) ana senaryo + (b) duyarlılık; iki tarafta "aynı dönem" kuralı |
| K3 | Tek yazıcı tavanının üstü | (a) Citus'u PostgreSQL seçeneği olarak eklemek; (b) eklememek ve tavanı sınırlama olarak yazmak (mainframe'de Parallel Sysplex gibi) | (b): v4 yığınını korur, iki taraf simetrik sınırlanır; tavan üstünde x86'da yalnız RAC kalır |
| K4 | X4'ün PostgreSQL karşılığı | (a) EDB Postgres Distributed (ticari, fiyatı yayımlanmıyor); (b) PostgreSQL için X4'ü infeasible saymak | (b): açık kaynak çekirdekte karşılığı olmayan bir topolojiyi uydurmamak (mainframe'de "komik topoloji" kuralı, v4 §4.3) |
| K5 | Üç sunucu üreticisi | (a) üçü ayrı katalog; (b) tek referans sunucu + üretici farkı aralık olarak | (b): fiyatlar zaten üreticiye özel yayımlanmıyor; üç katalog sahte bir hassasiyet verir |
| K6 | Kendi ölçümümüz | (a) sysbench protokolünü (3.8) laboratuvarda ya da bulut bare-metal'de koşmak; (b) yalnız yayımlanmış veriyle devam | (a): x86 köprüsünün en güçlü kalibrasyonu; birkaç saatlik bulut maliyeti |
| K7 | Veritabanı nerede çalışır | (a) VM üzerinde Patroni / Oracle; (b) VM'ler içindeki Kubernetes'te operatörle (PGO/Patroni) | Her ikisi aday stack olarak kalsın (v4 2×2×2); (b)'de iki çarpan üst üste uygulanır |

---

## 14. Yeni Geçerlilik Tehditleri

| # | Tehdit | Etki | Ele alınışı |
|---|---|---|---|
| 14.1 | SPECrate2017_int, OLTP veritabanı verimini temsil etmeyebilir (bellek gecikmesi ve kilit çekişmesi ağırlıklı iş yükü) | Nesiller arası taşımada hata | Mainframe'de LSPR'nin "CICS/Db2'nin LSPR karışımına benzediği" varsayımının karşılığı. Kendi ölçüm (3.8) ile iki nesilde kontrol |
| 14.2 | Fiyat dönemi asimetrisi: x86 2026 şok fiyatları, mainframe şok öncesi çapalar | Sonuç fiyat döneminin eseri olabilir | `PRICE_EPOCH` senaryo anahtarı (12.2); IBM fiyatlarının şoku yansıtıp yansıtmadığı bilinmiyor, sınırlama olarak yazılır |
| 14.3 | Oracle verimi kalibre edilemez (lisans yasağı) | Oracle yığınlarının maliyeti geniş aralıkta | Aralık parametresi; tornado; tezde yapısal veri sınırı olarak |
| 14.4 | Kapsam asimetrisi: mainframe'de CICS (işlem yöneticisi) modelin içinde, x86'da uygulama sunucusu katmanı dışında | Mainframe aleyhine yanlılık | İki seçenek: x86'ya uygulama katmanı CPU'su eklemek ya da mainframe'de CICS'in yalnızca DB'ye denk düşen payını saymak. Adım 6'da karar |
| 14.5 | Personel oranları iki tarafta da IBM kaynaklı | Yanlılık iki tarafta aynı yönde, ama büyüklüğü bilinmiyor | 10.4'teki bağımsız kaynak arayışı; geniş aralık |
| 14.6 | Bulut ölçümlerinde "çekirdek"in fiziksel mi mantıksal mı olduğu belirsiz | Köprüde 2 kata varan hata | Çapa yalnızca bare-metal ölçüm; bulut verisi çapraz kontrol |
| 14.7 | Sanallaştırma ek yükünün iki kaynağı birbirine rakip üreticilerden | Taraflı uçlar | Geniş aralık; mümkünse kendi ölçüm |
| 14.8 | Tek yazıcı tavanı sabit değil; büyük çekirdekli düğümlerde PostgreSQL ölçeklenmesi bilinmiyor | Yüksek TPS'te crossover bölgesinin yeri | b_x86 aralığı; 128+ çekirdek için sonuç "ekstrapolasyon" diye işaretlenir |

---

## 15. Kaynaklar

### 15.1. Kullanılan kaynaklar ve modeldeki yerleri

**Kapasite köprüsü**
- [VONNG-PERF] Feng Ruohang (Vonng), "How Powerful is PostgreSQL Really?" — http://blog.vonng.com/en/pg/pg-performence/ · c5d.metal'de sysbench oltp_read_write çapası (3.2, 3.3)
- [ROCKDATA-2026] Redrock Postgres, "2026 PostgreSQL Performance Benchmark Report" — https://www.rockdata.net/blog/2026-postgres-performance-benchmark-report/ · PostgreSQL 18.6, rejim farkı ve çapraz kontrol (3.2) [VENDOR]
- [TENCENT-METHOD] Tencent Cloud, "Test Methods" — https://tencentcloud.com/document/product/409/62415 · oltp_read_write bileşimi (K1)
- [TENCENT-RESULT] Tencent Cloud, "Test Results" — https://www.tencentcloud.com/document/product/409/62416 · çekirdek sayısıyla ölçeklenme eğrisi (3.2, 3.4)
- [ALIBABA-PG16] Alibaba Cloud, PolarDB vs açık kaynak PostgreSQL 16 — https://help.aliyun.com/en/polardb/polardb-for-postgresql/performance-comparison-with-open-source-postgresql · I/O-sınırlı rejim (3.2)
- [SPEC-8270] SPEC CPU2017, Dell M640, Xeon Platinum 8270 — https://spec.org/cpu2017/results/res2019q3/cpu2017-20190708-15958.html · nesil normalizasyonu (3.3)
- [SPEC-R760] SPEC CPU2017, Dell R760, Xeon Gold 6548Y+ — https://open.spec.org/cpu2017/results/res2024q2/cpu2017-20240422-43001.html (3.3)
- [SPEC-DL380G12] SPEC CPU2017, HPE DL380 Gen12, Xeon 6787P — https://open.spec.org/cpu2017/results/res2025q1/cpu2017-20250210-46265.html (3.3, 5.2)
- [PGCON-2016] PGCon 2016, "PostgreSQL 9.6 scalability and performance improvements" — https://www.pgcon.org/2016/schedule/attachments/399_postgresql-96-scalability-perf-improvements.pdf · yazma yolu darboğazları (3.4)
- [ORACLE-OTN] Oracle Technology Network License Agreement — https://www.oracle.com/downloads/licenses/standard-license.html · benchmark yayın yasağı (3.5)
- [REDHAT-OCPV-2025] Red Hat Developer, "Scalable database performance with OpenShift Virtualization out of the box" (2025-02-25) — https://developers.redhat.com/blog/2025/02/25/scalable-database-performance-openshift-virtualization-out-box (3.7) [VENDOR]
- [PT-VSPHERE-OCPV-2024] VMware/Broadcom blog, Principled Technologies çalışması (2024-12-03) — https://blogs.vmware.com/cloud-foundation/2024/12/03/vmware-vsphere-8-supports-1-5-times-more-vms-and-delivers-62-more-data-transactions-than-red-hat-openshift-virtualization/ (3.7) [VENDOR]
- [EDB-LOCALPV] EDB, "Local Persistent Volumes and PostgreSQL usage in Kubernetes" — https://www.enterprisedb.com/index.php/blog/local-persistent-volumes-and-postgresql-usage-kubernetes (3.7, 7.1)

**Ölçekleme ve availability**
- [PATRONI-REPL] Patroni dokümantasyonu, Replication modes — https://patroni.readthedocs.io/en/latest/replication_modes.html (4.2, 8.2)
- [PIGSTY-RTO] Pigsty, Patroni RTO modeli — https://doc.pigsty.io/docs/concept/ha/rto/ (8.2, 12.1)
- [ORACLE-RAC-2024] Oracle, "The New Generation Oracle RAC" (Ağustos 2024, v1.2) — https://oracle.com/a/otn/docs/database/the-new-generation-oracle-rac.pdf (4.2, 8.2) [VENDOR]
- [ORACLE-MAA-2026] Oracle, MAA Blueprints (Ağustos 2026) — https://oracle.com/a/tech/docs/maa-onpremises-overview.pdf · topoloji eşlemesi ve RTO/RPO (8.2, 8.3) [VENDOR]
- [YELLOWBRICKS-HA] D. Epping, "How long does it take before a host is declared failed" — https://www.yellow-bricks.com/2021/01/26/how-long-does-it-take-before-a-host-is-declared-failed (8.2)
- [VISHWANATH-2010] K. V. Vishwanath, N. Nagappan, "Characterizing Cloud Computing Hardware Reliability", ACM SoCC 2010 — https://www.microsoft.com/en-us/research/wp-content/uploads/2010/06/socc088-vishwanath.pdf · düğüm olay sıklığı (8.1)
- [ITIC-2024] TechChannel, ITIC 2024 Global Server Reliability Survey özeti — https://techchannel.com/industry-news/server-reliability-survey-2024/ (8.1)
- [EDB-SYNCREP] EDB, "The Cost Implications of PostgreSQL Synchronous Replication" — https://enterprisedb.com/blog/the-varying-cost-synchronous-replication (9)

**Donanım**
- [SPECPOWER-2025Q1] SPECpower_ssj2008 Q1 2025 sonuçları — https://spec.cs.miami.edu/power_ssj2008/results/res2025q1 (5.2)
- [INTEL-ARK-6548Y] Intel, Xeon Gold 6548Y+ özellikleri — https://www.intel.com/content/www/us/en/products/sku/237564/intel-xeon-gold-6548y-processor-60m-cache-2-50-ghz/specifications.html (5.2)
- [PCSP-SERVER] PCSP, "How Much Does a Server Cost in 2026?" (2026-08-21) — https://pcserverandparts.com/news/how-much-does-a-server-cost-2026/ (5.2) [satıcı]
- [PCSP-SSD] PCSP, "Enterprise SSD prices 2026" (2026-08-23) — https://pcserverandparts.com/news/enterprise-ssd-prices-2026-server-storage-buying-guide/ (5.2, 7.2) [satıcı]
- [BACLOUD-RAM] BAcloud, "When will RAM prices drop? August 2026 update" — https://www.bacloud.com/en/blog/307/when-will-ram-prices-drop-still-no-good-news--august-2026-update.html (5.2)
- [CAPCOMP-RAM] Capital & Compute, sunucu bellek fiyatları (2026-10-27) — https://capitalandcompute.net/memory-prices/server/ (5.2)
- [TRENDFORCE-2026-08] TrendForce News (2026-08-17) — https://www.trendforce.com/news/2026/08/17/news-germany-ddr5-prices-near-5x-yoy-in-august-china-reportedly-sees-14-wow-jump-as-global-rally-continues/ (5.2)

**Yazılım**
- [ACEMQ-VVF] AceMQ, "VVF vs VCF: Price per Core" (2026-10-27) — https://acemq.com/blogs/vmware-cloud-foundation-vs-vsphere-foundation/ (6.1) [iş ortağı]
- [ACEMQ-RENEW] AceMQ, "VMware Renewal Pricing in 2026: What 37 Quotes Show" — https://acemq.com/research/state-of-vmware-renewals-2026/ (6.1) [iş ortağı]
- [LICENSEWARE-OCP] Licenseware, Red Hat OpenShift editions and node counting — https://wiki.licenseware.io/wiki/red-hat-openshift-editions-and-node-counting/ (6.2)
- [VENDORBENCH-OCP] VendorBenchmark, Red Hat OpenShift Pricing 2026 — https://vendorbenchmark.com/vendors/red-hat-openshift-pricing (6.2)
- [CDW-OVE] CDW, OpenShift Virtualization Engine premium, MW03815 — https://www.cdw.com/product/red-hat-openshift-virtualization-engine-premium-subscription-1-year-1/8238645 (6.2)
- [CCSP-RH] Red Hat hizmet sağlayıcı sözleşme fiyat listesi (Clouding Enuity) — https://www.cloudingenuity.com/contracts/5272/5272_Red_Hat.pdf (6.2)
- [REDRESS-PL2026] Redress Compliance, Oracle price list 2026 analizi — https://redresscompliance.com/oracle-price-list-2026-key-changes-and-analysis.html (6.3) [danışman]
- [ORACLE-PL2009] Oracle Technology Global Price List (2009-10-01) — https://public.dhe.ibm.com/software/websphere/oracle/technology-price-list.pdf (6.3)
- [ORACLE-CORE] Oracle Processor Core Factor Table (güncelleme 2026-01-28) — https://www.oracle.com/contracts/docs/processor-core-factor-table-070634.pdf (6.3)
- [ORACLE-PART] Oracle Partitioning Policy (2022-02-14) — https://oracle.com/a/ocom/docs/it-infrastructure/partitioning-070609.pdf (6.3)
- [OLE-NET2026] Oracle Licensing Experts, net price benchmarks 2026 — https://oraclelicensingexperts.com/blog/oracle-database-net-price-benchmarks-2026/ (6.3) [danışman]
- [VMW-249212] VMware blog, "Oracle on VMware support policy (MOS 249212.1)" — https://blogs.vmware.com/apps/2019/11/oracle-on-vmware-support-policy-metalink-249212-1.html (6.3)

**Storage ve personel**
- [VENDORBENCH-AFA] VendorBenchmark, enterprise storage per-TB pricing benchmark (Şubat 2026) — https://vendorbenchmark.com/blog/enterprise-storage-per-tb-pricing-benchmark (7.2)
- [STORAGEREVIEW-P5520] StorageReview, Solidigm D7-P5520 raporu — https://storagereview.com/wp-content/uploads/2022/07/solidigm-d7-p5520-1.pdf (7.3) [VENDOR sponsorlu]
- [IBM-EAGLE-LABOR] IBM, "Reducing IT labor costs" (2011) — https://public.dhe.ibm.com/software/os/systemz/summit/handouts/Session_3_Reducing_IT_labor_costs_Q2.pdf (10.2) [VENDOR]
- [IBM-EAGLE-2012] IBM, "Tales from the Eagle TCO team" (2012) — https://ftpmirror.your.org/pub/misc/ftp.software.ibm.com/software/os/systemz/2012summit/handouts/Track_1_Session_6_-_Tales_from_the_Eagle_TCO_team_-_final_v4.pdf (10.2) [VENDOR]
- [AVASANT-2020] Avasant, "Server Support Staffing Ratio Stops Freefall" (Aralık 2020) — https://avasant.com/report/server-support-staffing-ratio-stops-freefall/ (10.2)

### 15.2. İncelenip alınmayan ya da yalnızca bağlam olarak kullanılan kaynaklar

| Kaynak | Neden alınmadı |
|---|---|
| HammerDB TPROC-C sonuçları (TPC Council sonuç deposu, Lenovo LP2195, PT R760 MySQL) | Farklı işlem bileşimi (TPC-C türevi); K1 köprüsü oltp_rw üzerine kurulu. Yalnızca PostgreSQL'in diğer motorlarla göreli konumu için bağlam |
| Small Datum (M. Callaghan) sysbench serileri | Değerler yalnızca sürümler arası göreli; mutlak TPS yok. Düğüm içi ölçeklenme için yöntem olarak değerli, sayı olarak değil |
| Percona 2016 "millions of QPS" | PostgreSQL 9.6, 2016 donanımı; grafik değerleri metinde yok |
| PolarDB rakip bulut PG karşılaştırması | Rakip ürün adı gizli; yönetilen bulut servisi (on-prem simetrisi dışında) |
| Oracle SE2 vs PostgreSQL (DZone/SegmentFault, 2025) | Windows VM, 8 vCPU, Standard Edition; mutlak değer yok. Yalnızca 3.5'te "bulunan tek karşılaştırma" olarak anıldı |
| Oracle TPC-C x86 sonuçları (2012) | Farklı iş yükü, 14 yıllık donanım; yalnızca 3.5'te bağlam |
| Red Hat IDC/Forrester iş değeri çalışmaları | Üretici sponsorlu, sunucu/FTE oranı vermiyor, bulut odaklı |
| VMware topluluğu yönetici oranları (2007) | Eski, ikincil, kaynaksız aktarım |
| Satıcı ve eBay sunucu ilanları | Yenilenmiş ürün ya da tekil ilan; fiyat çapası olamaz |

---

## 16. Sonraki Adımlar (önerilen sıra)

1. Emirhan'ın K1–K7 kararları.
2. (K6 onaylanırsa) sysbench ölçüm protokolü; sonuçlar `data/raw/` altına CSV olarak.
3. Adım 6 ortak modül: saha olayları, nesne depolama fiyat fonksiyonu, BLS ücretleri, NPV kuralları, `PRICE_EPOCH`, storage fiyatlama sözleşmesi, iki fiyat modu. Mainframe modeli bu modüle taşınır, sonuçlarının değişmediği testle gösterilir.
4. x86 modeli: katalog → kapasite köprüsü → latency → topoloji X1–X4 → storage → maliyet → aralık ve tornado → NPV.
5. Güncel x86 model dokümanı (mainframe v3'ün karşılığı) ve bir değerlendirme (#7), kapanan tehditlerle.
6. Karşılaştırma katmanı: TPS ve veri hacmi eksenlerinde crossover **bölgesi**.
