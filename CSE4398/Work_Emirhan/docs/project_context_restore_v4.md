# Mainframe vs On-Prem Clustered Altyapı — Project Context Restore v4

> Yeni bir chat'e projeyi tam bağlamıyla aktarmak içindir. İçerik: amaç, yöntem felsefesi, **her kararın gerekçesi ve reddedilen alternatifleri**, karşılaştırmanın güncel mimarisi, açık işler. Mainframe modelinin iç teknik detayı ayrı dosyada: `mainframe_model_documentation_v2.md` (bu dosya o detaya girmez). Çalışan kod: `mainframe_model.py`.
>
> **Terminoloji notu:** Projede "sawtooth / testere dişi" kelimesini kullanmıyoruz (biz uydurduk, literatürde karşılığı yok). Bahsedilen şey bir *beklentidir*: bkz. Bölüm 2.

---

## 1. Amaç

### 1.1. Soru
Bir kurumun BT altyapısının **en alt katmanı** (uygulamaların altında transaction işleyen ve kritik veriyi tutan katman) için "**mainframe mi, on-prem clustered x86 altyapı mı?**" sorusunu, kurumun iş yükü ve SLA gereksinimlerine göre **maliyet temelinde** cevaplayan parametrik bir simülasyon aracı. Girdi: iş yükü + SLA. Çıktı: her iki tarafta bu girdiyi karşılayan **minimum maliyetli feasible konfigürasyon** ve yan yana full-stack TCO.

### 1.2. Neden bir araç
Mevcut karar kaynakları yetersiz:
- **Vendor whitepaper'ları**: tek taraflı, varsayımlar gizli.
- **Migration case study'leri**: gerçek ama tek kurum/tek iş yükü; "workload'ım farklı olsaydı?" sorusuna cevap vermez.
- **Akademik kuyruk/kapasite modelleri**: tek boyutta titiz (latency gibi), ama compute-only; lisans, storage, operasyonu kapsamaz.

Aracımız: gerçek katalog + benchmark kalibrasyonu + parametrik (anekdotal değil) + full-stack TCO.

### 1.3. Meşruiyet verisi
Capgemini 2024: en büyük 100 bankanın 85'i hâlâ mainframe kullanıyor. Accenture (150 banka BT yöneticisi): 4'te 5'i modernizasyon planlıyor. Modernization Intel 2025 (29 migration): %66 başarısız (%31 terk, %24 geri dönüş, %11 zombie), ortalama bütçe aşımı %287. Karar önceden iyi verilirse sonradan kurtarmaya çalışmaktan değerlidir.

---

## 2. Görmeyi Beklediğimiz Desen

Temel yapısal fark: mainframe kapasitesi **büyük, ayrık adımlarla** alınır (128 z16 kademesi, maliyet basamaklı); clustered kapasite **ince granülerlikte** alınır (sunucu/çekirdek ekleyerek, maliyet neredeyse sürekli). Bu yüzden iş yükü büyüdükçe iki tarafın maliyet farkının **işaret değiştirmesini (crossover) ve bunun birden fazla kez olmasını bekliyoruz**: mainframe kademesi doluya yakınken ucuz, iki kademe arasındaki boşlukta clustered ucuz.

Bu bir *beklenti*, ispat hedefi değil. Eğer fark iki uçta ters işaretliyse en az bir crossover mutlaka vardır; **asıl ölçtüğümüz: crossover'lar nerede ve kaç tane, ve hangi girdiye (TPS, latency, availability, RNI...) ne kadar duyarlı.** Sonuç beklentiyi doğrulamayabilir; öyleyse bunu da raporlarız. Desenin görünür kalması için: yıllık/saatlik simülasyon, kademeleri yumuşatmadan 128 tier, tek nokta yerine parametre taraması.

---

## 3. Yöntem Felsefesi ve Gerekçeleri

**3.1. Bottom-up.** Eksenleri (kapasite, latency, availability, maliyet) baştan dayatmıyoruz; önce iki gerçek sistemi kendi akışlarıyla inceliyoruz. *Gerekçe:* top-down kurulan ortak eksenler iki sistemde farklı anlama gelen sahte ortaklıklar üretir (örn. MIPS ile vCPU'yu doğrudan eşlemek).

**3.2. Paradigma karşılaştırması, ürün değil.** "Merkezi/ayrık kapasite ekonomisi vs dağıtık/ince kapasite ekonomisi". z16 ve x86 stack bu paradigmaların parametrik temsilcileri. *Gerekçe:* "IBM vs Red Hat" çerçevesi vendor taraftarlığına kayar; paradigma çerçevesi genelleştirilebilir.

**3.3. Tutucu yaklaşım.** M/M/1 (M/M/c değil), ITIC alt sınırı (vendor üst sınır değil), tam yedek maliyeti. *Gerekçe:* tutucu sonuç savunulabilir; iyimser sonuç "vendor gibi" görünür.

**3.4. Vendor + bağımsız ikili.** Her availability rakamı (vendor high, bağımsız low) çifti; feasibility yalnız low'a göre. *Gerekçe:* vendor iddiası tek başına güvenilmez, bağımsız veri tek başına nüanssız. (Aşağıda 4.3'te kullanıcı müdahalesiyle nasıl doğduğu var.)

**3.5. [ASSUME] etiketleme.** Kalibre edilemeyen her parametre açıkça işaretlenir, ayrı listelenir; mümkünse "sektör aralığı X–Y, orta değer Z" biçiminde. *Gerekçe:* varsayımı saklamak vendor whitepaper davranışı; şeffaflık projenin ayrıştırıcı özelliği.

**3.6. OLTP odağı.** Bankacılık core, ödeme, sigorta işlemleri; OLAP/ML/batch dışarıda. *Gerekçe:* OLAP ve ML'de clustered/dağıtık zaten açık ara önde, soru orada kapalı. OLTP'de (yüksek TPS + strong consistency + sıkı SLA) mainframe hâlâ rekabetçi, yani soru gerçekten açık. Ek olarak OLTP, parametreleri sabitler: blok 8–16 KB, ~%70/30 R/W, strong ACID.

**3.7. Eşit derinlik.** İki tarafa aynı kategoriler: compute + yazılım lisansı + storage + backup/DR + operasyon personeli. *Gerekçe:* bir tarafı derin, diğerini yüzeysel modellemek sonucu o tarafın lehine/aleyhine yanlı yapar.

**3.8. TPS ortak birim.** Girdi TPS, çıktı maliyet; iç birimler farklı (MIPS/MSU vs vCPU). *Gerekçe:* karşılaştırılabilirlik için ortak dış birim şart; iç birimleri eşleştirmeye çalışmak hataya açık.

**3.9. On-prem simetrisi.** İki taraf da kurumun kendi veri merkezinde. Bkz. 4.6.

---

## 4. Kararlar ve Gerekçeleri (Projenin Evrimi)

Her karar: **ne** → **neden** → **neyi reddettik**. Yeni chat bu mantığı bozmamalı.

### 4.1. Kapsam: "compute gücü/$" değil, full-stack TCO
- *Orijinal niyet:* hangi altyapının kuruma daha mantıklı/ucuz olduğunu görmek.
- *Sapma:* model bir ara raw compute gücü/$ karşılaştırmasına kaymıştı.
- *Neden yanlış:* mainframe'in değeri ve maliyeti entegre yığında (CICS/Db2 lisansı, I/O alt sistemi, yüksek availability topolojisi, operasyon). MIPS/$ ile vCPU/$ karşılaştırması elma-armut; ayrıca kurum satın alırken çekirdek değil çözüm alır.
- *Karar:* iki tarafın kapsamı genişletilir, "gerçekten muadil iki sistem" karşılaştırılır. Mainframe tarafı da TCO'ya genişleyecek (bugün TCO'nun ~%40–50'sini kapsıyor).

### 4.2. Mainframe karşısındaki rakip: gerçek hayatta mainframe'den çıkan kurumlar nereye gidiyor?
- Rakip, soyut "bulut VM" değil, **kurumsal OLTP için gerçekçi hedef mimari** olmalı: yönetilen/kümelenmiş veritabanı + container orkestrasyonu + sanallaştırma + replikasyon. Tek bir VM + tek DB gerçek bir muadil değil (HA, replikasyon, DR, operasyon yok).
- Bu, 4.6'daki on-prem kararıyla birleşip bugünkü rakip tanımına dönüştü.

### 4.3. Availability modeli (kullanıcı müdahaleleriyle şekillendi)
1. *"Tek frame (A) topolojisini modellemeye gerek yok; komik bir topoloji simülasyon sonucu çıkması saçma."* → IBM'in resmi 4-model Resiliency çerçevesi (M1–M4) **olduğu gibi** alındı, kendi topolojimizi icat etmedik. External CF'nin legacy olduğu iddiam yanlıştı: standalone CF hâlâ destekleniyor ama IBM bunu ayrı model değil konfigürasyon detayı sayıyor; ICF/CFCC yazılım faturasını artırmıyor.
2. *"IBM rakamları hâlâ vendor iddiası."* → bağımsız veri arandı; **ITIC** anketleri (1.200–1.950 işletme/yıl) alt sınır, IBM Redbook üst sınır oldu; sabit rakam yerine **aralık**.
3. *"ITIC sadece HW arızasını ölçüyor; IBM'in iddiasına planlı bakım dahil miydi? ITIC'in vendor'dan yüksek çıkması garip."* → İki kaynağın kapsamı farklı olduğunu kabul ettik. Planlı kesintiyi endüstri verisiyle düzeltmek için **Precisely** kuralı (toplam downtime'ın ~%90'ı planlı) → HW availability'ye `1 − 10·(1−hw)` düzeltmesi; M4 (planlı kesintiyi maskeleyen topoloji) istisna. Feasibility alt sınıra göre.

### 4.4. Latency parametresi
- *Neden eklendi:* gerçek SLA'lar availability + yanıt süresi (percentile ile, örn. p99 < 200 ms) olarak yazılır; girdimizde yoktu.
- *Yöntem:* mainframe'de ölçüm WLM/RMF response-time percentile (SMF 72.3/110.1). Modelde M/M/1 kuyruğundan `rho_max = 1 − (E[X]/hedef)·ln(1/(1−p))` ile **latency hedefinden dinamik utilization tavanı** türetilir (sabit %90 tavan yerine). *Neden:* latency bir kapasite kısıtına dönüşür; sıkı SLA → daha düşük izin verilen utilization → daha büyük kademe.
- *Reddedilen:* M/M/c (tutucu olması için M/M/1 tutuldu; clustered tarafta paralel sunucu olduğu için M/M/c orada kullanılacak).

### 4.5. Statik çıktı yerine yıllık (8760 saat) simülasyon + CoD
- *Neden:* mainframe yazılım faturası **aylık R4HA (rolling 4-hour average) tepe** üzerinden kesilir; tek nokta TPS bunu yakalayamaz. Tepe yönetimi kademe seçimini değiştirir. Workload preset'leri: steady_oltp, retail_bursty, batch_heavy.
- *CoD:* kullanıcı, On/Off Capacity-on-Demand ile küçük kademe + geçici kapasitenin bazen üst kademeden ucuz olacağını belirtti. Strateji A (kalıcı tepe boyutu) vs B (taban + CoD); model **her zaman ikisini karşılaştırıp** ucuz feasible olanı çıktı verir. CoD günlük maliyeti = kalıcı günlük eşdeğer × 2.5 [ASSUME]. Doğrulama: retail_bursty'de CoD ~%32 tasarruf (2026-10-31 R4HA düzeltmesinden sonra; önceki %36 Permanent stratejiye R4HA uygulanmadığı için şişkindi).

### 4.6. On-prem simetrisi (en kritik kapsam düzeltmesi)
- *Sapma:* mainframe karşısına bulut tabanlı bir yığın konmuştu; mainframe'ler ise on-prem. Kullanıcının tespiti: iki taraf kurumun kendi veri merkezinde karşılaştırılmalı.
- *Neden:* bulut karşılaştırması mimari paradigma farkına **ek değişkenler** katar (kiralama vs sahiplik, OPEX vs CAPEX, gerçek elastisite, fatura modeli). On-prem simetrisi deployment, mülkiyet ve finansal profili (CAPEX ağırlıklı, 5 yıl amortizasyon) sabitler; geriye sadece merkezi-vs-dağıtık kapasite ekonomisi kalır.
- *Sonuç:* clustered = bare metal x86 + sanallaştırma + container orkestrasyonu + veritabanı. On-prem'de "autoscaling" sınırlıdır (fiziksel donanım önceden alınmış); bu kabul edilmiş kısıt.

### 4.7. Girdi seti ve storage
- Kullanıcı storage SLA'larının da girdi olması gerektiğini söyledi. Analiz sonucu: **data consistency girdi değil** (OLTP için zaten strong/ACID, sabit); **replikasyon/RPO** kullanıcı girdisi, replication factor ve DR site sayısı RPO+RTO+availability'den **türetilir**; IOPS ve storage throughput de **türetilir** (TPS × RNI-bağımlı oran × blok boyutu).
- *RNI içine IOPS gömme:* RNI hem CPU hem IOPS yoğunluğunu temsil eder (doğrudan oranlı): low ~5, average ~10, high ~20 IOPS/tx. Kullanıcıya IOPS sorulmaz (kendi IOPS girdisini verecek bilgisi olmayan kullanıcıyı yanlış yönlendirir). Kullanıcı onayladı; "kaybolmasın" uyarısı var: IOPS RNI üzerinden her iki tarafa taşınmalı.
- **8 kullanıcı girdisi:** throughput (TPS), rni, latency_ms + percentile, availability, data_volume_tb, data_growth_pct, rpo_seconds, rto_minutes.
- **Storage her iki tarafa birlikte eklenir** (asimetri karşılaştırmayı bozar).

### 4.8. Clustered stack: neden 2×2×2 ve "stack seçim motoru"
Kullanıcının fikri: mainframe tarafı **sabit/monolitik** (z/OS+CICS+Db2+DS8900F+GDPS); pratikte kuruma özgü varyasyon az, alternatifi yok. Clustered tarafta ise kurum ihtiyacına göre **farklı stack'ler "en iyi" olabilir**. O yüzden clustered'ı tek sabit stack yerine **iş yüküne göre seçilen** stack olarak modelliyoruz: farklı girdiler için en uygun stack eşleştirilir ve mainframe'e rakip topoloji olarak sunulur. Bu asimetri bilinçli: mainframe seçim özgürlüğü sunmaz, clustered sunar, ve bu maliyetin parçasıdır.

Katman kararları ve gerekçeleri:
- **Her zaman virtualization katmanı var; bare-metal Kubernetes yok.** *Neden:* enterprise OLTP pratikte neredeyse her zaman sanallaştırılmış; çıplak K8s atipik ve gerçek dünyadan uzaklaştırır.
- **Hypervisor (2): VMware vSphere ESXi + OpenShift Virtualization (KVM).** Kullanıcı: "en popüler iki, biri ESXi olsun." İkincisi için OpenShift Virtualization seçildi (Red Hat ekosistemiyle OpenShift tarafına uyumlu).
- **Container yönetimi (2): vanilla Kubernetes + Red Hat OpenShift.** Açık kaynak vs enterprise destekli lisanslı ikilisi.
- **Veritabanı (2): PostgreSQL + Patroni (açık kaynak) + Oracle Database (lisanslı).** Her katmanda "açık kaynak + lisanslı" çifti; maliyet farkı büyük (Oracle çekirdek başına ciddi lisans, PostgreSQL lisanssız).
- **Windows Server dışarıda.** Enterprise OLTP'de Linux baskın; kapsam daraltma.
- **Storage: Phase 1'de tek alternatif** (karar bekliyor); aksi halde kombinasyon sayısı patlar.
- **Messaging kapsam dışı** (kullanıcı kararı, 2026-10-31): iki tarafta da modellenmez; mainframe'de IBM MQ yok.
- 2×2×2 = 8 kombinasyon; hepsi mantıklı değil, motor workload profiline göre aday aileyi daraltır, her adayı feasibility+maliyet için ayrı değerlendirip **en ucuzu** seçer (hibrit yaklaşım).

**Başlangıç daraltma kuralları:**

| Workload profili | Aday stack sınıfı |
|---|---|
| Düşük-orta TPS (<50K), gevşek regülasyon, maliyet hassas | OpenShift Virt + K8s + PostgreSQL (tam açık kaynak) |
| Orta-büyük TPS, sıkı regülasyon, enterprise destek şart | VMware + OpenShift + Oracle (tam enterprise) |
| Karma tolerans | VMware + OpenShift + PostgreSQL veya KVM + K8s + Oracle |

---

## 5. Karşılaştırma Mimarisi

| Katman | Mainframe (sabit) | Clustered (seçilebilir) |
|---|---|---|
| Deployment | On-prem | On-prem |
| Compute | IBM z16 (128 kademe) | Bare metal x86: Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3 |
| OS | z/OS + PR/SM | Linux (RHEL/Ubuntu) |
| Virtualization | PR/SM (dahili) | VMware ESXi **veya** OpenShift Virt (KVM) |
| Orkestrasyon | CICS region yönetimi | Vanilla K8s **veya** OpenShift |
| Transaction mgmt | CICS TS (ayrı MSU lisansı) | Yok; uygulama + DB ACID'ine delege |
| Veritabanı | Db2 for z/OS | PostgreSQL+Patroni **veya** Oracle |
| Messaging | Kapsam dışı | Kapsam dışı |
| Storage | DS8900F | Phase 1 tek alternatif (açık) |
| Backup/DR | GDPS + tape | Veeam veya alternatif (açık) |
| Operasyon | Sysprog + DBA + capacity planner | Linux admin + K8s operator + DBA + storage + network |

**Yapısal fark (CICS):** mainframe'de CICS ayrı MSU-faturalı lisans; clustered'da eşdeğeri yok. Mainframe pahalılığının önemli kaynaklarından biri, model bunu yakalamalı.

**Hesap akışı:** girdi (8 parametre) → clustered için aday stack daralt → availability topolojisi filtrele (M1–M4 / C1–C4) → latency+throughput'tan feasible kapasite → minimum maliyet → yıllık simülasyon → yan yana TCO.

---

## 6. Mainframe Tarafı — Durum (özet)

**Tamam:** z16 katalog (28 temsili / 128 yapısal), LSPR→MIPS→MSU köprüsü, CP-güç köprüsü (z13 benchmark × LSPR oranı), RNI çarpanları, M/M/1 dinamik tavan, M1–M4 + ITIC/Redbook ikili sınır + planlı kesinti düzeltmesi, maliyet (MSU lisans, donanım amortismanı, bakım, enerji), R4HA yıllık simülasyon, On/Off CoD, CLI, CSV.

**Eksik (Phase 2 — TCO genişletme):** CICS lisansı, Db2 lisansı, DS8900F storage (TB+IOPS+maliyet), GDPS yazılım lisansı (şu an çarpan olarak gömülü), operasyon personeli. Bu kalemlerle mainframe TCO'sunun 2–3 kat büyümesi beklenir. Tam 128 tier tablosu da tamamlanacak.

Önemli sabitler ve formüller `mainframe_model_documentation_v2.md` içinde.

---

## 7. Clustered Tarafı — Kurulacaklar (hiçbiri henüz kodlanmadı)

Mainframe'in aynı disiplini: gerçek katalog, gerçek benchmark çapası, açık fiyat verisi, [ASSUME] etiketli boşluklar.

1. **Donanım kataloğu** (`X86_SERVERS`): çekirdek, bellek, liste fiyatı, amortizasyon (5 yıl), alan/enerji/soğutma.
2. **Throughput köprüsü:** her stack için `BASE_TPS_PER_VCPU` (HammerDB/TPC-C, YugabyteDB TPC-C çapaları). Virtualization overhead [ASSUME]: vSphere ~%3–8, OpenShift Virt ~%5–10; OpenShift orkestrasyon overhead'i vanilla K8s'ten biraz yüksek; Oracle PostgreSQL'e göre çekirdek başına ~%20–40 fazla throughput [ASSUME]. Ölçekleme verimi: düğüm içi ~%85–95, düğümler arası ~%70–90.
3. **Latency:** M/M/c + ağ baz gecikmesi (rack içi 0.1–0.5 ms; rack arası 0.5–2; metro 1–5; coğrafi 5–30). Mainframe'de ağ terimi yoktu (iç fabric), bu yapısal bir fark.
4. **Availability C1–C4:** tek site (~%99–99.9) / çok rack (~%99.9–99.99) / metro senkron (~%99.99–99.999) / coğrafi (~%99.999–99.9999). Dual-bound disiplini korunur.
5. **Maliyet (hepsi [ASSUME] aralık):** vSphere ~$300–450/çekirdek/yıl (Broadcom sonrası abonelik); OpenShift ~$2.500–5.000/çekirdek/yıl; Oracle EE $47.500/çekirdek liste (x86 çekirdek faktörü 0.5) + %22/yıl destek; PostgreSQL lisanssız (opsiyonel destek sözleşmesi); operasyon personeli (rol × maaş × node sayısına bağlı kişi sayısı).
6. **Yıllık simülasyon karşılığı:** Strateji A statik (tepe için sabit N düğüm), Strateji B dinamik (taban + fazla donanım rezervi, HPA/DRS). On-prem'de fark mainframe CoD kadar keskin değil: donanım alınmış, boşta da amortisman ödenir; lisans kullanıma bağlıysa kısmi fark.
7. **Stack seçim motoru** (Bölüm 4.8).
8. **Storage ve backup tek alternatiflerinin seçimi** (açık karar). Messaging kapsam dışı.

---

## 8. Kritik Kullanıcı Müdahaleleri (saygı gösterilecek)

1. CP-güç köprüsü: MIPS nesiller arası normalize varsayımı yanlıştı.
2. Sysplex her zaman ekstra maliyet değildir; IBM 4-model çerçevesi olduğu gibi.
3. Vendor iddiası tek başına yetmez; ITIC bağımsız alt sınır.
4. Hardware-only availability planlı kesintiyi kaçırır; ×10 düzeltmesi.
5. CoD olmadan mainframe haksız pahalı çıkar; yıllık simülasyon + CoD, hep karşılaştırmalı çıktı.
6. Raw compute/$ değil, full-stack TCO.
7. Consistency girdi değil; replikasyon türetilir; storage iki tarafa birlikte.
8. İki taraf on-prem.
9. Clustered'da stack seçim motoru; mainframe sabit stack.
10. Her katmanda tam iki alternatif; bare-metal K8s yok; Windows yok.
11. Rakibin ne olacağı *kesin netleşmeden* ilerlenmez (önceki sapmaların dersi).

## 9. Yeni Chat'in Kaçınması Gerekenler

- Compute/$ karşılaştırmasına kaymak.
- OLAP/ML/batch eklemek.
- Bulut/yönetilen servis yığınlarını geri getirmek.
- Mainframe tarafında stack seçimi eklemek; clustered'da seçeneği daraltmak (hypervisor: ESXi+OpenShift Virt; orkestrasyon: K8s+OpenShift; DB: PostgreSQL+Oracle).
- Çalışan mainframe modelini sıfırlamak: üstüne ekle.
- [ASSUME] ve vendor/bağımsız ikili disiplinini bırakmak.
- "Sawtooth/testere dişi" terimini kullanmak (Bölüm 2'deki ifadeyi kullan).
- Kullanıcıya IOPS sormak; consistency'yi girdi yapmak.
- Karar vermeden önce rakibi netleştirmeden kod yazmak.

---

## 10. Plan

**Hafta 1–2:** mainframe TCO genişletme (CICS/Db2/DS8900F/GDPS/personel). **3–4:** clustered kalibrasyon araştırması. **5–6:** clustered model (katalog, 2×2×2, köprü, maliyet). **7:** C1–C4 + M/M/c. **8:** stack seçim motoru. **9:** clustered yıllık simülasyon. **10:** karşılaştırma katmanı + parametre taraması. **11:** crossover görselleştirme + duyarlılık. **12:** (zaman kalırsa) stokastik arıza modeli. **13–14:** dokümantasyon, tez, sunum. Phase 3 (Monte Carlo) opsiyonel.
**B-plan:** kalibrasyon verisi yetersizse yalnız baz stack (PostgreSQL + K8s + VMware) + diğerleri [ASSUME] etiketli.
**Ayrıca:** açık sistem tarafı için araştırma yapılacak (kullanıcı belirtti).

---

## 11. Referanslar

**Mainframe (kalibre):** [LSPR](https://www.ibm.com/support/pages/node/6953823) · [EPS Chapman](https://www.epstrategies.com/library/content/Chapman_Exploring_CPU_Measurements.pdf) · [REDP-5320](https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf) · [SG24-8446](https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf) · [ITIC](https://itic-corp.com/) · [Precisely HA](https://www.precisely.com/glossary/high-availability-ha/) · [IBM SC28-7025 CoD](https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf)
**Mainframe TCO (araştırılacak):** IBM MLC fiyatları (CICS/Db2), DS8900F, mainframe DBA/sysprog maaşları.
**Clustered (araştırılacak):** Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3 spec+fiyat; vSphere 8 (Broadcom) fiyatı; OpenShift/OpenShift Virt fiyat ve overhead; HammerDB TPC-C (PostgreSQL, Oracle); YugabyteDB TPC-C; Oracle çekirdek faktör tablosu; Oracle MAA; Patroni+etcd, CloudNativePG; OpenShift OLTP referans mimarileri.
**Meşruiyet/bağlam:** [Capgemini 2024](https://www.capgemini.com/insights/research-library/mainframe-modernization-patterns-for-financial-services/) · [CNCF Infosys](https://www.cncf.io/case-studies/infosysmainframe/) · [Modernization Intel 2025](https://softwaremodernizationservices.com/insights/mainframe-to-cloud-migration-challenges/) · [SNIA](https://www.snia.org/sites/default/files/PerformanceBenchmarking.Nov2010.pdf) · [Simplyblock OLTP vs OLAP](https://www.simplyblock.io/glossary/oltp-vs-olap-storage-io-patterns/) · [Veeam RTO/RPO](https://www.veeam.com/blog/recovery-time-recovery-point-objectives.html)

---

## 12. Yeni Chat Açılış Prompt'u

> Ekteki `project_context_restore_v4.md` projenin güncel amacını, kararlarını ve gerekçelerini içerir; `mainframe_model_documentation_v2.md` mainframe modelinin iç detayını, `mainframe_model.py` çalışan kodu. Kararlar sabittir (Bölüm 4, 8, 9 özellikle önemli). Karşılaştırma: on-prem z16 yığını vs on-prem clustered x86 (VMware/OpenShift Virt × K8s/OpenShift × PostgreSQL/Oracle, stack seçim motoruyla). Sawtooth terimini kullanma. Şu işten başlamak istiyorum: [mainframe TCO genişletme / clustered kalibrasyon araştırması / clustered kod iskeleti].
