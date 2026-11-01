# Proje Gerekçesi (Project Justification)

**Ders:** CSE4297 Engineering Project I, Marmara Üniversitesi Bilgisayar Mühendisliği
**Ekip:** Emirhan Türkol, Kaan Yavaş, Ahmet Can Akay
**Danışman:** Doç. Dr. Murat Can Ganiz

> Bu doküman projenin ne olduğunu, neden yapıldığını, hangi yöntemle yapıldığını ve her tasarım kararının neden doğru olduğunu savunma diliyle anlatır. Projenin güncel halini anlatır. Mainframe modelinin formül ve sabit düzeyindeki detayı `mainframe_model_documentation_v2.md` dosyasındadır.

---

## 1. Tek Cümlede Proje

Bir kurumun kritik transaction yükünü taşıyan **en alt altyapı katmanı** için, kurumun iş yükü ve SLA gereksinimlerini girdi olarak alan parametrik bir simülasyon aracı geliştiriyoruz. Araç iki tarafta da bu gereksinimleri karşılayan **en düşük maliyetli uygulanabilir (feasible) konfigürasyonu** bulur ve iki tarafı **tam yığın toplam sahip olma maliyeti (full-stack TCO)** üzerinden yan yana koyar. Taraflardan biri kurumun kendi veri merkezindeki **IBM mainframe (z16)**, diğeri yine kurumun kendi veri merkezindeki **kümelenmiş (clustered) x86 altyapıdır**.

---

## 2. Problem

### 2.1. Karar
Bankacılık core sistemleri, ödeme işleme ve sigorta poliçe işlemleri gibi OLTP yükleri için kurumlar şunu seçmek zorundadır: yükü tek bir yüksek kapasiteli, dikey entegre sistemde mi (mainframe) taşıyacaklar, yoksa çok sayıda standart sunucudan oluşan, sanallaştırılmış ve container ile orkestre edilen bir kümede mi (clustered)?

### 2.2. Bu karar neden zor ve pahalı
- **Geri dönüşü zor bir karar.** Altyapı paradigması bir kez seçilince uygulama mimarisi, veri modeli, operasyon ekibi ve lisans sözleşmeleri ona göre şekillenir. Sonradan değiştirmek yıllar ve on milyonlarca dolar sürer.
- **Büyük ölçekli bir karar.** Dünyanın en büyük 100 bankasının 85'i hâlâ kritik yükleri mainframe üzerinde çalıştırıyor (Capgemini, 2024). 150 banka BT yöneticisiyle yapılan bir ankette 5 kişiden 4'ü mainframe yüklerini modernize etmeyi planladığını söylüyor (Accenture).
- **Yanlış yapıldığında sonuçları ağır.** 2020–2025 arasında bütçesi 3–45 milyon dolar olan 29 mainframe migration projesinin %66'sı hedefine ulaşamadı:
  - %31'i yarıda bırakıldı.
  - %24'ü tamamlandıktan sonraki 12 ay içinde mainframe'e geri döndü.
  - %11'i bitmeyen "zombi" projelere dönüştü.
  - Ortalama bütçe aşımı %287, ortalama süre aşımı 22,4 ay oldu (Modernization Intel, 2025).

Bu tablo, kararın baştan doğru verilmesinin sonradan kurtarma çabasından çok daha değerli olduğunu gösteriyor. Doğru kararın ön koşulu da kurumun kendi iş yüküne özgü, nicel ve şeffaf bir karşılaştırmadır.

### 2.3. Mevcut kaynaklar neden yetmiyor
| Kaynak türü | Güçlü yanı | Neden karar için yetersiz |
|---|---|---|
| Vendor whitepaper'ları (IBM, Red Hat, VMware, Oracle) | Ürün hakkında ayrıntılı bilgi verir | Tek taraflıdır, varsayımları gizlidir, sonuç yayınlayan vendor'ı kayırır |
| Migration case study'leri | Gerçek deneyimi yansıtır | Tek kurum ve tek iş yükü anlatır; "benim yüküm farklı olsaydı ne olurdu?" sorusuna cevap vermez |
| Akademik kapasite ve kuyruk modelleri | Tek bir boyutta titizdir (örneğin latency) | Yalnızca compute'u kapsar; lisans, storage, DR ve personel maliyetini dışarıda bırakır |
| Mimari literatürü (Amdahl; Stonebraker, shared-nothing; DeWitt & Gray; "OLTP Through the Looking Glass"; "OLTP on Hardware Islands") | Scale-up ve scale-out arasındaki ödünleşimleri kavramsal ve deneysel olarak açıklar | Belirli bir kurumun girdisiyle maliyet temelli bir karar mekanizması sunmaz |
| Simülatörler (CloudSim, OMNeT++) | Kaynak tahsisini ve ağı simüle eder | Mainframe MSU faturalandırmasını, CoD'yi ve OLTP TCO'sunu modellemez |

**Boşluk:** Kurumun kendi iş yükü ve SLA'sını girdi olarak alıp iki paradigmayı **aynı disiplinle**, **tam yığın maliyetle** ve **parametrik olarak** karşılaştıran şeffaf bir araç yok. Proje bu boşluğu dolduruyor.

---

## 3. Amaç ve Araştırma Soruları

### 3.1. Ana amaç
Verilen bir OLTP iş yükü ve SLA için, mainframe ve clustered tarafta bu gereksinimi karşılayan minimum maliyetli konfigürasyonları bulmak, ikisini tam yığın TCO üzerinden karşılaştırmak ve tercihin hangi girdi koşullarında değiştiğini göstermek.

### 3.2. Araştırma soruları
1. **Belirli bir girdi için** hangi paradigma daha ucuza feasible bir çözüm sunuyor ve fark hangi maliyet kalemlerinden (compute, lisans, storage, DR, personel) geliyor?
2. **Girdi uzayı boyunca** tercih hangi noktalarda değişiyor? Bu geçiş noktaları nerede ve kaç tane?
3. **Duyarlılık:** Tercihi en çok hangi girdi değiştiriyor (TPS, işlem karmaşıklığı, latency hedefi, availability hedefi, RPO/RTO, veri hacmi)?
4. **Clustered tarafta** iş yüküne göre hangi yazılım yığını (stack) en uygun?

### 3.3. Kullanıcı ve kullanım
Hedef kullanıcı, altyapı kararı veren veya bu kararı değerlendiren kurumsal mimar, BT yöneticisi veya araştırmacıdır. Kullanıcı kendi iş yükü ve SLA değerlerini girer. Araç her iki taraf için önerilen konfigürasyonu, yıllık maliyet dökümünü ve karşılaştırmayı verir. Parametre taraması ile girdi aralıkları üzerinde tercihin nasıl değiştiği görselleştirilir.

---

## 4. Görmeyi Beklediğimiz Desen

İki paradigma arasında maliyet ölçeklenmesi açısından yapısal bir fark var:
- **Mainframe kapasitesi büyük ve ayrık adımlarla alınır.** z16'da 128 kapasite kademesi vardır. Bir kademeyi aşan her talep bir üst kademeye geçmeyi gerektirir. Donanım ve yazılım maliyeti de bu yüzden basamaklı artar.
- **Clustered kapasite ince taneli alınır.** Sunucu veya çekirdek ekleyerek ihtiyaca yakın büyüklükte kapasite alınabilir. Maliyet neredeyse sürekli artar.

Bu farktan dolayı iş yükü büyüdükçe iki taraf arasındaki maliyet farkının **birden fazla kez işaret değiştirmesini bekliyoruz.** Mainframe, bir kademeyi doluya yakın kullandığında görece ucuzdur. İki kademe arasında kalan bir talepte ise ödenip kullanılmayan kapasite yüzünden clustered avantajlı olabilir.

Bu bir **beklentidir**, ispat edilecek bir iddia değildir. Fark aralığın iki ucunda ters işaretliyse en az bir geçiş noktası vardır; ama geçişlerin yeri, sayısı ve girdilere duyarlılığı ancak ölçülerek bulunur. Sonuçlar beklentiyi doğrulamazsa bu da raporlanacak bir bulgudur. Aracın tasarımı bu deseni gizlemeyecek şekilde yapıldı:
- Kademeler yumuşatılmaz; 128 kademe ayrı ayrı tutulur.
- Tek nokta yerine parametre taraması yapılır.
- Tepe yükü ve faturalandırma etkileri yıllık, saatlik bir simülasyonla yakalanır.

---

## 5. Kapsam

### 5.1. Kapsamda
- **İş yükü:** Yalnızca OLTP (yüksek TPS, kısa transaction'lar, strong/ACID tutarlılık).
- **Katman:** Kurumsal BT'nin en alt katmanı; compute, işletim sistemi, sanallaştırma, orkestrasyon, transaction yönetimi, veritabanı, storage, backup/DR ve operasyon personeli.
- **Deployment:** Her iki taraf da kurumun kendi veri merkezinde (on-prem).
- **Maliyet:** Tam yığın TCO; donanım amortismanı, bakım, enerji, yazılım lisansları, storage, DR ve personel.
- **Zaman:** Bir yıllık, saatlik çözünürlükte (8.760 saat) yük profili.

### 5.2. Kapsam dışında ve gerekçesi
| Kapsam dışı | Gerekçe |
|---|---|
| OLAP, analitik, ML eğitimi, saf batch | Bu alanlarda dağıtık mimari zaten açıkça üstün; soru kapalı. Gerçek rekabet OLTP'de. |
| Uygulama katmanı modernizasyonu (kod dönüşümü, yeniden yazım) | Proje altyapı katmanını karşılaştırıyor; uygulama göçü ayrı bir problem. |
| Messaging katmanı | Karşılaştırma kapsamını sadeleştirmek için iki tarafta da modellenmiyor. |
| Windows Server | Kurumsal OLTP'de Linux baskın; kapsamı daraltır. |
| Bare-metal Kubernetes | Kurumsal OLTP pratikte neredeyse her zaman sanallaştırılmış altyapıda çalışır; çıplak K8s atipik. |
| Bulut ve yönetilen servisler | Mainframe on-prem'dir. Buluta karşı kıyaslamak kiralama/sahiplik ve OPEX/CAPEX gibi paradigma dışı farklar ekler (bkz. 6.3). |
| Lisans pazarlık dinamikleri | Kuruma özgüdür, genellenemez; liste fiyatı ve bağımsız aralıklar kullanılır, duyarlılık analizi yapılır. |
| Storage katmanının altındaki ağ altyapısı | İki tarafta da benzer düzeyde bulunur; ayırt edici değildir. |
| Gerçek sistem kurulumu ve benchmark koşturma | Araç analitik bir modeldir, benchmark aracı değildir; yayınlanmış benchmark'larla kalibre edilir. |

---

## 6. Yöntem Felsefesi: Kararların Arkasındaki İlkeler

Her ilke, sonucun **savunulabilir** olması için seçildi.

### 6.1. Paradigma karşılaştırması, ürün karşılaştırması değil
Karşılaştırılan şey iki kapasite ekonomisidir: **merkezi ve büyük adımlı** ile **dağıtık ve ince taneli**. IBM z16 ve x86 yığını bu paradigmaların ölçülebilir temsilcileridir. "IBM'e karşı Red Hat" çerçevesi vendor tartışmasına kayar ve genellenemez. Paradigma çerçevesi ise sonucu genellenebilir kılar.

### 6.2. Tam yığın TCO, ham compute değil
Ham compute maliyeti (MIPS başına dolar ile vCPU başına dolar) yanıltıcı bir karşılaştırmadır:
- Mainframe'in maliyeti ve değeri entegre yığındadır: CICS ve Db2 lisansları, I/O alt sistemi, yüksek availability topolojisi ve uzman personel.
- Kurum çekirdek satın almaz, işini çalıştıracak bir çözüm satın alır.

Bu yüzden iki tarafa da aynı maliyet kategorileri girer: compute, yazılım lisansı, storage, backup/DR ve operasyon personeli.

### 6.3. On-prem simetrisi
İki taraf da kurumun kendi veri merkezinde çalışır. Böylece deployment modeli, mülkiyet modeli ve finansal profil (CAPEX ağırlıklı, 5 yıllık amortisman) iki tarafta aynı olur ve **tek değişken mimari paradigma** kalır. Bu, deneysel tasarımda kontrol değişkenlerini sabitlemenin karşılığıdır.

### 6.4. Ortak dış birim: TPS
İç birimler farklıdır: mainframe'de MIPS/MSU, clustered'da çekirdek/vCPU. Bunları doğrudan eşlemeye çalışmak hataya açıktır. İki taraf da **TPS'i girdi, maliyeti çıktı** olarak alır. Her taraf TPS'i kendi iç birimine kendi kalibre edilmiş köprüsüyle çevirir.

### 6.5. Bottom-up modelleme
Karşılaştırma eksenleri (kapasite, latency, availability, maliyet) baştan dayatılmaz. Her sistem önce kendi gerçek işleyişiyle modellenir: nasıl kapasite alınır, nasıl faturalanır, nasıl ayakta kalır. Ortak eksenler bu modellerden çıkar. Yukarıdan dayatılan ortak eksenler, iki sistemde farklı anlama gelen sahte eşdeğerlikler üretir.

### 6.6. Eşit derinlik
İki taraf aynı titizlikle ve aynı kategorilerle modellenir. Bir tarafı derin, diğerini yüzeysel modellemek sonucu o yöne kaydırır; bu da vendor çalışmalarının tipik hatasıdır.

### 6.7. Tutucu yaklaşım
Belirsizlik olan her yerde sonucu iyimserleştirmeyen seçenek seçilir. Örnekler:
- M/M/1 kuyruk modeli (daha kötümser latency).
- Availability'de bağımsız alt sınır.
- Yedek kapasitenin tam maliyetiyle sayılması.

Tutucu bir sonuç savunulabilirdir; iyimser bir sonuç ise vendor iddiası gibi görünür.

### 6.8. Vendor ve bağımsız kaynak ikilisi
Vendor rakamları tek başına güvenilir değildir, bağımsız rakamlar da tek başına nüanstan yoksundur. Bu yüzden availability gibi kritik değerler **aralık** olarak tutulur: üst sınır vendor, alt sınır bağımsız ölçüm. Feasibility kararı **alt sınıra göre** verilir.

### 6.9. Şeffaf varsayım: [ASSUME]
Kaynakla kalibre edilemeyen her parametre `[ASSUME]` olarak etiketlenir. Mümkün olduğunda "sektör aralığı X–Y, kullanılan değer Z" biçiminde verilir ve ayrı bir listede toplanır. Varsayımları gizlemek vendor davranışıdır; açıkça göstermek aracın ayırt edici özelliğidir ve duyarlılık analizine zemin hazırlar.

### 6.10. OLTP sabitleri
OLTP odağı bazı parametreleri girdi olmaktan çıkarıp sabitler:
- Blok boyutu 8–16 KB.
- Okuma/yazma oranı yaklaşık %70/30.
- Tutarlılık seviyesi strong (ACID).

Böylece kullanıcıya anlamsız veya iki tarafı farklı yorumlanabilir hale getiren seçimler yaptırılmaz.

---

## 7. Girdiler ve Çıktılar

### 7.1. Kullanıcı girdileri (8 parametre)
| Girdi | Anlamı | Neden kullanıcıdan alınıyor |
|---|---|---|
| `throughput` (TPS) | Saniyedeki transaction sayısı (ortalama ve tepe karakteristiği) | Kapasitenin temel belirleyicisi; ancak kurum bilir |
| `rni` (low/average/high) | İşlem karmaşıklığı: transaction başına CPU ve I/O yoğunluğu | Aynı TPS çok farklı kaynak tüketebilir; kurum iş yükünün niteliğini bilir |
| `latency_ms` + `percentile` | Yanıt süresi hedefi (örn. p99 < 200 ms) | Gerçek SLA'lar percentile ile yazılır; kapasiteyi doğrudan kısıtlar |
| `availability` | Hedef çalışma oranı (örn. 0.9999) | Topoloji seçimini belirler; regülasyona bağlıdır |
| `data_volume_tb` | Başlangıç veri hacmi | Storage maliyetinin temeli |
| `data_growth_pct` | Yıllık veri büyümesi | Çok yıllık storage maliyetini belirler |
| `rpo_seconds` | Kabul edilebilir en fazla veri kaybı (0 = senkron) | Replikasyon tipini ve DR topolojisini belirler |
| `rto_minutes` | Kabul edilebilir en uzun kesinti süresi | DR topolojisini ve otomasyon gereksinimini belirler |

### 7.2. Türetilen (kullanıcıya sorulmayan) büyüklükler ve gerekçesi
- **IOPS:** TPS ve RNI'ya bağlı bir orandan türetilir. RNI hem CPU hem I/O yoğunluğunu temsil eder. Kullanıcı ayrıca IOPS girmez, çünkü çoğu karar verici bu değeri doğru bilmez; yanlış girilen IOPS ise sonucu bozar. IOPS'un RNI üzerinden **iki tarafa da** taşınması zorunludur.
- **Storage throughput:** IOPS × OLTP blok boyutu.
- **Replication factor ve DR site sayısı:** RPO, RTO ve availability'den.
- **Tutarlılık:** OLTP için strong, sabit (girdi değil).
- **Topoloji:** Mainframe'de M1–M4, clustered'da buna paralel bir yapı; availability, RPO ve RTO'dan.
- **Clustered stack seçimi:** İş yükü profilinden (bkz. 9.3).

### 7.3. Çıktılar
- Her iki taraf için önerilen minimum maliyetli feasible konfigürasyon:
  - Mainframe'de kapasite kademesi ve topoloji.
  - Clustered'da donanım, stack ve topoloji.
- Yıllık TCO dökümü: compute, lisans, storage, backup/DR, personel.
- Tepe yönetim stratejileri karşılaştırması ve seçilen strateji.
- Hangi tarafın kazandığı ve farkın kaynağı.
- Parametre taraması sonuçları ve geçiş noktaları.
- Grafik hazır CSV çıktıları ve görselleştirme.

---

## 8. Uçtan Uca Hesap Akışı

1. **Yük profili üretimi.** Ortalama TPS ve tepe karakteristiğinden yılın 8.760 saati için gerçekçi bir TPS vektörü üretilir. Profil gün içi dalgayı (sabah tepesi, gece düşüşü), hafta içi/hafta sonu farkını ve yıl içindeki yoğun günleri içerir. Hazır profiller: dengeli OLTP, perakende tipi ani tepeler, batch ağırlıklı.
2. **Topoloji eleme.** Her iki tarafta availability, RPO ve RTO hedefini karşılayamayan topolojiler elenir. Feasibility kontrolü tutucu alt sınıra göre yapılır.
3. **Kapasite boyutlandırma.** Kalan her topoloji için TPS kalibre edilmiş köprüyle iç kapasite birimine çevrilir, RNI çarpanı uygulanır ve latency hedefinden izin verilen en yüksek kullanım oranı hesaplanır. Tepe saatlik yükü bu tavanın altında taşıyabilen en ucuz kapasite seçilir.
4. **Tepe yönetim stratejisi.** Yıl boyunca maliyet iki stratejiyle hesaplanır:
   - Tepe için kalıcı boyutlandırma.
   - Taban kapasite + geçici kapasite (mainframe'de On/Off CoD, clustered'da on-prem rezerv/dinamik atama).

   Ucuz olan seçilir. Model iki stratejiyi her zaman birlikte raporlar.
5. **Tam yığın TCO.** Compute'a lisans, storage, backup/DR ve personel eklenir.
6. **Karşılaştırma.** İki taraf yan yana konur ve kazanan ile farkın kaynağı raporlanır.
7. **Parametre taraması.** Girdi aralıkları taranır; geçiş noktaları ve duyarlılık görselleştirilir.

---

## 9. Taraflar

### 9.1. Mainframe tarafı: sabit yığın
**Yığın:** IBM z16 + z/OS (PR/SM) + CICS Transaction Server + Db2 for z/OS + DS8900F storage + GDPS (backup/DR) + operasyon personeli (sysprog, DBA, kapasite planlamacı).

**Yığın neden sabit?** Mainframe dikey entegre, kapalı bir ekosistemdir. z/OS'un pratik bir alternatifi yoktur; CICS ve Db2 kurumsal OLTP'de baskındır; GDPS IBM'in DR çözümüdür. Gerçek hayatta kurumdan kuruma değişen şey yazılım yığını değil, **kapasite kademesi** ve **availability topolojisidir**. Model de seçim özgürlüğünü yalnızca bu iki eksende tanır. Bu, gerçek dünyanın modele yansımasıdır.

**Modelin bileşenleri ve her birinin gerekçesi** (formüller ve sabitler `mainframe_model_documentation_v2.md` içinde):

| Bileşen | Ne yapıyor | Neden böyle |
|---|---|---|
| z16 kapasite kataloğu (LSPR) | Her kademenin göreli kapasitesi IBM'in resmî LSPR tablosundan alınır | Resmî, kademe bazlı tek kaynak; ayrık adımları olduğu gibi korur |
| LSPR → MIPS → MSU köprüleri | Göreli kapasiteyi mutlak MIPS'e, MIPS'i fatura birimi MSU'ya çevirir (EPS/Chapman çapası) | Yazılım faturası MSU ile kesildiği için maliyetin doğru birimi MSU'dur |
| CP güç köprüsü | z13 üzerindeki resmî CICS benchmark'ı (REDP-5320) LSPR z16/z13 oranıyla z16 TPS'ine taşınır | MIPS nesiller arası tam normalize değildir; doğrudan MIPS → TPS çevirmek hatalı olurdu. Mainframe için TPC-C yayınlanmadığından en sağlam çapa budur |
| RNI çarpanı | İşlem karmaşıklığını kapasite tüketimine yansıtır | Aynı TPS'in farklı iş yüklerinde farklı kaynak tükettiği gerçeğini modeller |
| M/M/1 dinamik kullanım tavanı | Latency hedefi ve percentile'dan izin verilen en yüksek kullanımı hesaplar | Sabit "%90 kullan" kuralı SLA'dan bağımsızdır. Sıkı SLA'nın daha büyük kademe gerektirmesi ancak bu şekilde yakalanır. Yöntem mainframe'in WLM/RMF percentile ölçümüyle uyumludur |
| IBM Resiliency M1–M4 topolojileri | IBM'in resmî 4 modelli availability çerçevesi olduğu gibi kullanılır | Kendi topolojimizi uydurmak yerine üreticinin tanımladığı gerçek yapılandırmaları kullanırız |
| İkili availability sınırı | Üst sınır IBM Redbook, alt sınır ITIC bağımsız anketleri; feasibility alt sınıra göre | Vendor iddiası tek başına savunulamaz |
| Planlı kesinti düzeltmesi | Donanım-only availability'ye "toplam kesintinin ~%90'ı planlıdır" kuralıyla ×10 düzeltme; planlı kesintiyi maskeleyen topoloji (M4) hariç | Kaynakların raporladığı değerler yalnızca donanım arızasını kapsıyor; kullanıcının yaşadığı gerçek kesinti planlı bakımı da içerir |
| Maliyet modeli | MSU bazlı yazılım lisansı + donanım amortismanı + bakım + enerji | Mainframe maliyetinin yapısal kalemleri |
| Yıllık simülasyon (R4HA) | 8.760 saatlik profil üzerinden aylık 4 saatlik kayan ortalama tepesi hesaplanır | Mainframe yazılım faturası gerçekte aylık R4HA tepesine göre kesilir; tek nokta TPS bunu yakalayamaz |
| On/Off Capacity-on-Demand | Küçük kademe + tepe günlerde geçici kapasite stratejisi, kalıcı tepe stratejisiyle karşılaştırılır | CoD gerçek bir IBM özelliğidir. Hesaba katılmazsa mainframe haksız şekilde pahalı çıkar. Örnek senaryoda (retail_bursty, 50K TPS) yaklaşık %32 tasarruf sağladı |

**Henüz eklenmemiş (tam yığın TCO için zorunlu):** CICS lisansı, Db2 lisansı, DS8900F storage, GDPS lisansı (şu an topoloji çarpanı olarak gömülü), operasyon personeli ve 128 kademenin tamamı (şu an 28 temsili kademe). Bu kalemler eklenmeden mainframe tarafı yalnızca compute katmanını, yani TCO'nun yaklaşık yarısını temsil eder.

**Yapısal fark (CICS):** Mainframe'de transaction yönetimi CICS ile ayrı ve MSU ile faturalanan bir lisanstır. Clustered tarafta bunun doğrudan karşılığı yoktur; transaction yönetimi uygulama katmanı ve veritabanının ACID garantileriyle sağlanır. Model bu farkı maliyet farkının bir kaynağı olarak yakalamalıdır.

### 9.2. Clustered tarafı: seçilebilir yığın
**Yapı:** Bare metal x86 sunucular + **her zaman** bir sanallaştırma katmanı + container orkestrasyonu + veritabanı + storage + backup/DR + operasyon personeli. İşletim sistemi Linux.

**Her katmanda iki alternatif (açık kaynak / kurumsal lisanslı):**

| Katman | Alternatif 1 | Alternatif 2 |
|---|---|---|
| Sanallaştırma | VMware vSphere ESXi | OpenShift Virtualization (KVM) |
| Container orkestrasyonu | Vanilla Kubernetes | Red Hat OpenShift |
| Veritabanı | PostgreSQL + Patroni | Oracle Database |
| Storage | Tek alternatif (seçim açık) | |
| Backup/DR | Tek alternatif (seçim açık) | |

**Bu seçimlerin gerekçesi:**
- **Her zaman sanallaştırma var:** Kurumsal OLTP gerçek hayatta neredeyse her zaman sanallaştırılmış altyapıda çalışır. Bare-metal K8s'i dışarıda bırakmak modeli gerçeğe yaklaştırır.
- **Sanallaştırmada VMware ESXi:** Kurumsal sanallaştırmanın yerleşik standardı.
- **Sanallaştırmada OpenShift Virtualization:** KVM tabanlı, Red Hat ekosistemiyle ve OpenShift orkestrasyonuyla doğal uyumlu; en güçlü ikinci yol.
- **Kubernetes ve OpenShift:** Container orkestrasyonunun açık kaynak standardı ve kurumsal destekli dağıtımı.
- **PostgreSQL ve Oracle:** Kurumsal OLTP'nin baskın açık kaynak ve lisanslı veritabanları. İkisi arasındaki lisans maliyeti farkı TCO'yu belirleyici ölçüde etkiler; bu yüzden ikisi birden modelleniyor.
- **Storage ve backup'ta tek alternatif:** Kombinasyon sayısını yönetilebilir tutmak için.

**Henüz belirlenmeyenler:** Clustered taraf için hiçbir kalibrasyon çapası, benchmark değeri, overhead oranı, fiyat veya availability rakamı henüz belirlenmedi. Bunların hepsi mainframe tarafında uygulanan yöntemle bulunacak:
- Önce resmî ve bağımsız kaynak araştırılır.
- Çapa kaynaktan çıkarılır.
- Kaynak yoksa `[ASSUME]` etiketli aralık kullanılır.
- Vendor/bağımsız ikilisi korunur.
- Tutucu taraf seçilir.

Bu şekilde belirlenecek bileşenler:
1. Donanım kataloğu.
2. TPS'ten çekirdek/sunucu kapasitesine köprü; sanallaştırma, orkestrasyon ve veritabanı farkları ile düğüm içi ve düğümler arası ölçekleme verimi dahil.
3. Latency modeli. Clustered'da paralel sunucu ve ağ gecikmesi bulunduğundan mainframe'den farklı olacağı bekleniyor.
4. Mainframe M1–M4'e paralel availability topolojileri.
5. Lisans, donanım, enerji ve personel maliyetleri.
6. Tepe yönetim stratejisi. On-prem'de donanım önceden satın alındığı için CoD'ye göre daha az esnek olması bekleniyor.

### 9.3. Stack seçim motoru
İki taraf arasındaki asimetri bilinçli olarak modelde tutulur: **mainframe seçim sunmaz, clustered sunar.** Kurumun ihtiyacına göre farklı clustered yığınlar "en iyi" olabilir. Motor şöyle çalışır:
1. İş yükü profili (TPS düzeyi, regülasyon sıkılığı ve kurumsal destek ihtiyacı, maliyet hassasiyeti) ile 8 kombinasyondan (2×2×2) **aday aile daraltılır**:
   - Maliyet hassas, gevşek regülasyonlu yük → tam açık kaynak (OpenShift Virt + K8s + PostgreSQL).
   - Sıkı regülasyonlu, kurumsal destek şart olan yük → tam kurumsal (VMware + OpenShift + Oracle).
   - Arada kalan yük → karma kombinasyonlar.

   Eşikler kalibrasyondan sonra netleşecek.
2. Her aday için topoloji, kapasite ve maliyet ayrı ayrı hesaplanır.
3. **En ucuz feasible aday** mainframe'in rakibi olarak sunulur.

**Neden önemli:** Karşılaştırmayı "mainframe'e karşı rastgele bir x86 yığını" olmaktan çıkarır ve "mainframe'e karşı bu iş yükü için en iyi x86 yığını" haline getirir. Bu, clustered tarafa adil davranmanın tek yoludur. Ayrıca mainframe'in sabit yığın maliyetini görünür kılar.

---

## 10. Geçerlilik, Riskler ve Sınırlamalar

| Risk / sınırlama | Etkisi | Önlem |
|---|---|---|
| IBM donanım ve lisans fiyatlarını yayınlamıyor | Mainframe maliyetinde belirsizlik | Bağımsız sektör aralıkları, `[ASSUME]` etiketi, duyarlılık analizi |
| Mainframe için TPC-C yok | Throughput çapası dolaylı | Resmî CICS benchmark'ı + LSPR oranı (CP güç köprüsü) |
| Vendor availability iddiaları iyimser | Feasibility yanlı olabilir | Bağımsız alt sınır (ITIC) ve planlı kesinti düzeltmesi |
| M/M/1 ve M/M/c basitleştirmeleri | Latency tahmini yaklaşık | Tutucu tercih; ilerleyen fazda stokastik model |
| Clustered kalibrasyon verisinin eksik kalması | Clustered maliyeti belirsiz | B planı: yalnızca temel stack'i (PostgreSQL + K8s + VMware) tam kalibre etmek, diğerlerini `[ASSUME]` etiketli varyasyon olarak vermek |
| Lisans pazarlığı modellenmiyor | Gerçek fiyat liste fiyatından düşük olabilir | Aralık ve duyarlılık analizi; iki tarafa eşit uygulanır |
| Deterministik model (Faz 1) | Arıza rastlantısallığı yok | Faz 2: stokastik arıza (MTBF/MTTR); Faz 3: Monte Carlo |
| Beklenen geçiş deseninin çıkmaması | Hipotez doğrulanmaz | Bu da geçerli bir bulgu olarak raporlanır; girdi uzayı genişletilir |

Aracın ürettiği şey **kesin fiyat tahmini değildir**. Ürettiği şey, şeffaf varsayımlarla kurulmuş, iki tarafa eşit disiplin uygulanmış, **karşılaştırmalı ve duyarlılığı ölçülebilir** bir karar desteğidir. Mutlak değerdeki belirsizlik iki tarafa benzer biçimde yansıdığı için göreli sonuç (hangi taraf, hangi koşulda, neden) mutlak rakamlardan daha sağlamdır.

---

## 11. Katkılar

1. **Tam yığın ve iş yüküne özgü karşılaştırma:** Ham compute değil; lisans, storage, DR ve personel dahil TCO.
2. **Simetrik ve kontrollü deney tasarımı:** İki taraf da on-prem, aynı maliyet kategorileri, ortak birim olarak TPS ve eşit derinlik.
3. **Mainframe'in gerçek ekonomisinin modellenmesi:** MSU faturalandırması, aylık R4HA tepesi, On/Off CoD, LSPR kademeleri ve IBM Resiliency topolojileri.
4. **Kanıta dayalı ve şeffaf kalibrasyon:** Vendor/bağımsız ikili sınır, planlı kesinti düzeltmesi, `[ASSUME]` etiketleme.
5. **Clustered tarafta stack seçim motoru:** Mainframe'i en zayıf değil, iş yüküne göre en iyi x86 rakibiyle karşılaştırma.
6. **Parametre taraması ve geçiş noktalarının görselleştirilmesi:** Tercihin nerede ve neden değiştiğini gösterme.
7. **Yeniden üretilebilirlik:** Açık kod, açık varsayım listesi, grafik hazır çıktılar.

---

## 12. Mevcut Durum

**Tamamlanan:**
- Mainframe compute modeli: kapasite kataloğu, köprüler, RNI, M/M/1 latency, M1–M4 availability, ikili sınır ve planlı kesinti düzeltmesi, maliyet.
- Yıllık simülasyon (R4HA) ve On/Off CoD strateji karşılaştırması.
- CLI aracı ve CSV çıktıları.
- Ayrı bir etkileşimli karşılaştırma ve görselleştirme aracı.
- Mainframe model dokümantasyonu.
- 8 girdilik setin, clustered yığın yapısının ve stack seçim mantığının tasarımı.

**Yapılacak:**
1. Mainframe TCO genişletme: CICS, Db2, DS8900F, GDPS lisansı, personel, 128 kademenin tamamı.
2. Clustered kalibrasyon araştırması (mainframe yöntemiyle).
3. Clustered modelin kurulması: katalog, köprü, latency, topolojiler, maliyet, stack seçim motoru, yıllık simülasyon.
4. Storage ve backup alternatiflerinin seçilmesi.
5. Karşılaştırma katmanı, parametre taraması, geçiş noktası görselleştirmesi ve duyarlılık analizi.
6. Faz 2: stokastik arıza modeli. Faz 3: Monte Carlo (zaman kalırsa).
7. Final rapor ve sunum.

---

## 13. Başarı Ölçütleri

- Tüm 8 girdi modelde etkin olmalı. Her girdinin değişmesi çıktıda tutarlı ve açıklanabilir bir değişim üretmeli.
- Her iki taraf için minimum maliyetli feasible konfigürasyon tutarlı biçimde bulunmalı. Aynı girdi her zaman aynı sonucu vermeli (deterministik faz).
- İki taraf aynı maliyet kategorileriyle ve eşit derinlikte modellenmiş olmalı.
- Her sayısal parametrenin kaynağı ya da `[ASSUME]` etiketi olmalı.
- Parametre taraması geçiş noktalarını ve duyarlılığı yorumlanabilir grafiklerle göstermeli.
- Sonuçlar, hangi tarafın hangi koşulda ve hangi maliyet kalemi nedeniyle kazandığını açıklayabilmeli.

---

## 14. Referanslar

**Mainframe kapasite ve benchmark**
- IBM Z LSPR ITR Table: https://www.ibm.com/support/pages/node/6953823
- S. Chapman, *Exploring z/OS WLM CPU Measurements*, Enterprise Performance Strategies: https://www.epstrategies.com/library/content/Chapman_Exploring_CPU_Measurements.pdf
- Burgess, Mitchell, Moxey, *CICS TS V5.3 Benchmark on IBM z13* (REDP-5320): https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf

**Availability**
- White, Coq, *Getting Started with IBM Z Resiliency* (SG24-8446): https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf
- ITIC Global Server Reliability Surveys 2020–2024: https://itic-corp.com/
- Precisely, *High Availability Definition*: https://www.precisely.com/glossary/high-availability-ha/

**Capacity-on-Demand**
- IBM, *IBM Z and LinuxONE Capacity on Demand User's Guide* (SC28-7025): https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf

**Bağlam ve motivasyon**
- Capgemini, *Mainframe Modernization Patterns for Financial Services* (2024): https://www.capgemini.com/insights/research-library/mainframe-modernization-patterns-for-financial-services/
- CNCF, *Infosys Mainframe Modernization Case Study*: https://www.cncf.io/case-studies/infosysmainframe/
- Modernization Intel, *Mainframe Migration Challenges* (2025): https://softwaremodernizationservices.com/insights/mainframe-to-cloud-migration-challenges/

**OLTP karakteristiği ve RPO/RTO**
- SNIA, *Solid State Storage Performance Test Specification*: https://www.snia.org/sites/default/files/PerformanceBenchmarking.Nov2010.pdf
- Simplyblock, *OLTP vs OLAP Storage I/O Patterns*: https://www.simplyblock.io/glossary/oltp-vs-olap-storage-io-patterns/
- Veeam, *RTO and RPO*: https://www.veeam.com/blog/recovery-time-recovery-point-objectives.html

**Kavramsal temel**
- G. M. Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities," AFIPS, 1967.
- M. Stonebraker, "The case for shared nothing," IEEE Database Eng. Bull., 1986.
- D. J. DeWitt, J. Gray, "Parallel database systems," CACM, 1992.
- S. Harizopoulos, D. Abadi, S. Madden, M. Stonebraker, "OLTP through the looking glass, and what we found there," SIGMOD, 2008.
- D. Porobic et al., "OLTP on hardware islands," PVLDB, 2012.
- Klasik kuyruk teorisi (M/M/1, M/M/c).

**Clustered taraf:** Kaynaklar, mainframe tarafındaki yöntemle yürütülecek kalibrasyon araştırmasında belirlenecek.
