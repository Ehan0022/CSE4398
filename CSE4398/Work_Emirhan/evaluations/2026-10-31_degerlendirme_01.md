# Bitirme projesi: uçtan uca akademik değerlendirme

> **Değerlendirme #1** · Tarih: 2026-10-31
> Kapsam: projenin bu tarihteki hali. Oturum 1 düzeltmeleri (latency modeli, R4HA faturası) uygulanmış; clustered taraf henüz kodlanmamış. Ayrıntılar için bkz. `PROJECT_LOG.md` → 2026-10-31.
> Rutin değerlendirmeler `evaluations/` klasöründe `YYYY-MM-DD_degerlendirme_NN.md` adıyla tutulur. Bir sonraki değerlendirme bu dokümandaki tehditlerin (2.1–2.11) hangilerinin kapandığını ayrıca raporlamalıdır.

31 Ekim 2026 itibarıyla durum. Kaynaklar: üç tasarım dokümanı, düzeltilmiş `mainframe_model.py` ve bu değerlendirme için yapılan ek çalıştırmalar. Rakamlar kodu çalıştırarak üretildi. Kaynağı doğrulanmamış iddialar "doğrulanmalı" diye işaretli.

## 0. Kısa cevap

Veri toplamaya geçmek doğru, ama bir ön koşulla. Veri toplamadan önce iki kavramsal kararı netleştirmek gerekiyor. Bunlar netleşmezse toplanan verinin bir kısmı boşa gider:

1. **"Transaction" ortak birimi tanımlanmalı.** Şu an TPS ortak birim, ama mainframe tarafı bir CICS benchmark transaction'ına, clustered taraf ise TPC-C/HammerDB transaction'ına kalibre edilecek. Bu ikisi aynı iş miktarı değil. Projenin en büyük geçerlilik tehdidi bu.
2. **Crossover beklentisi yeniden kurulmalı.** Düzeltilmiş modelde mainframe maliyeti TPS'e göre neredeyse doğrusal (yaklaşık $2/TPS/ay, ±%7). Yani "büyük ayrık adımlar" önermesi mevcut varsayımlarla ortaya çıkmıyor (Bölüm 3.2).

Bu ikisi netleşince veri toplama, mainframe'de kullandığınız yapının aynası olarak kurulabilir: bir benchmark çapası + bir ölçekleme tablosu + resmî fiyat listeleri + bağımsız availability verisi. İyi haber şu: clustered tarafta bu kaynakların çoğu mainframe tarafındakinden daha açık ve daha kaliteli.

## 1. Projenin güçlü yanları

- **Soru doğru yerde.** OLTP'ye daraltılmış, on-prem simetrisiyle kontrol değişkenleri sabitlenmiş, ürün değil paradigma karşılaştırması. Bu çerçeve bir jüriye kolay savunulur.
- **Şeffaflık disiplini.** [ASSUME] etiketleri, vendor/bağımsız ikili sınır ve tutucu tarafı seçme ilkesi literatürdeki vendor TCO çalışmalarından gerçekten ayrıştırıcı.
- **Mainframe ekonomisinin gerçek mekanizmaları modelde.** R4HA, sub-capacity MLC, On/Off CoD ve LSPR kademeleri. Akademik kapasite modellerinin çoğu bunları atlar; projenin asıl katkısı burada.
- **Bottom-up yaklaşım ve kullanıcı müdahaleleriyle düzeltilmiş kararlar.** CP-güç köprüsü, planlı kesinti düzeltmesi ve on-prem simetrisi iyi gerekçelendirilmiş düzeltmeler.
- **Yeniden üretilebilirlik.** Tek dosya, sadece standard library, CSV çıktı ve artık test dosyası.

## 2. Geçerlilik tehditleri (önem sırasına göre)

### 2.1. Ortak birim sorunu: "1 TPS" iki tarafta aynı iş değil (kritik)

Mainframe çapası REDP-5320'deki CICS TS benchmark'ı. O benchmark'ın transaction'ı belirli bir CICS/Db2 iş yükü. Clustered tarafın planlanan çapası ise TPC-C veya HammerDB TPROC-C. Bir TPC-C New-Order transaction'ı ~10 satır okuma/yazma ve birden çok tablo içerir; bir CICS benchmark transaction'ı bundan çok daha hafif ya da ağır olabilir. İki taraf farklı iş birimlerine kalibre edilirse karşılaştırma, sonuçta bulunan farkın tamamını bu belirsizlik kadar kaydırabilir. Bu durumda asıl karşılaştırılan şey iki benchmark'ın tanımı olur.

**Öneri:** Bir **referans OLTP transaction'ı** tanımlayın. Örneğin: transaction başına X satır okuma, Y satır yazma, Z commit ve R/W %70/30 (OLTP sabitlerinizle uyumlu). İki benchmark'ı da bu referansa bir dönüşüm katsayısıyla bağlayın. Katsayıyı benchmark raporlarındaki iş yükü tanımlarından türetin; türetilemiyorsa [ASSUME] aralık olarak verip duyarlılık analizine en üstten sokun. RNI zaten bu yönde bir adım, ama RNI "aynı transaction tipinin ağır/hafif hali"ni temsil ediyor, iki benchmark arasındaki tanım farkını değil. Adım 0 olarak REDP-5320'nin iş yükü tanımı (transaction başına Db2 çağrısı, I/O) okunmalı.

### 2.2. Crossover hipotezinin dayanağı zayıfladı (yüksek)

Bu değerlendirme için statik modda 10K–250K TPS taraması yapıldı (0.999, avg RNI). Toplam aylık maliyet / TPS tüm aralıkta $1,92 ile $2,18 arasında kalıyor. Sebepleri:

- Donanım fiyatı $200/MIPS ile **doğrusal** varsayılıyor.
- R4HA düzeltmesinden sonra yazılım faturası tüketilen MSU ile **sürekli** artıyor.
- 28 kademe bile yeterince ince; 128 kademe gelince adımlar daha da küçülecek.

Yani mevcut varsayımlarla mainframe tarafı da "ince taneli" davranıyor. Gerçek dünyada maliyet eğrisini şekillendiren şeyler başka:

- **Sabit maliyetler:** frame taban fiyatı, minimum personel, GDPS ve storage taban maliyeti.
- **Hacim indirimli MLC kademeleri:** IBM VWLC/AWLC fiyatları MSU arttıkça birim fiyatı düşen kademelerle yayımlanıyor (doğrulanmalı). Bu ölçek ekonomisi demek, basamak değil.
- **Clustered tarafta da ayrıklık var:** HA için minimum 3 düğüm (quorum), site başına küme, Oracle'ın minimum lisans kuralları ve sunucu başına çekirdek adımları.

**Sonuç:** Beklenen desen büyük ihtimalle "çok sayıda crossover" değil. Daha muhtemel olan, **sabit-maliyet ağırlıklı (mainframe) ile marjinal-maliyet ağırlıklı (clustered) yapı arasında bir ya da birkaç crossover** ve bunun RNI, availability ve lisans seçimine göre kayması. Bu, tezi zayıflatmaz; hipotezi "maliyet yapısı: sabit vs değişken" üzerine yeniden kurmanızı gerektirir. Dokümandaki "beklenti, ispat değil" çerçevesi bunu zaten kaldırıyor. Bu bulgu şimdiden rapora girebilecek bir ara sonuç.

**Pratik sonuç:** Mainframe donanım fiyatını doğrusal yerine "taban + MIPS başına" yapısında modelleyin. MLC'yi de kademeli fiyat tablosuyla kurun. Bu iki değişiklik eğrinin şeklini doğrudan belirler, o yüzden veri toplamada öncelikli.

### 2.3. Fiyat verilerinin kaynak kalitesi (yüksek)

Mainframe maliyet sabitlerinin kaynakları zayıf. $200/MIPS ve 30 kW bir satın alma rehberi serisinden, $40/MSU lisanslama danışmanlığı bloglarından geliyor. Bir jüri ilk buraya bakar. İyileştirme yolları:

- IBM MLC fiyatları (z/OS, CICS, Db2) IBM'in yazılım duyuru mektuplarında ve fiyat sayfalarında MSU kademeli olarak yayımlanıyor olabilir. Bulunursa "A kalite" kaynak olur (doğrulanmalı).
- Donanım için tek bir satın alma rehberi yerine birden çok bağımsız kaynak kullanın (analist raporları, kamu ihale kayıtları, IBM'in yayımladığı TCO çalışmaları) ve üçgen kontrolü yapın.
- Enerji için IBM z16 Installation Manual for Physical Planning (IMPP) belgesi frame başına güç değerlerini resmî olarak verir. Bu, satın alma rehberinden çok daha güçlü bir kaynak.

**Öneri:** Her parametre için bir **kaynak kalite notu** tutun: A = resmî/yayımlanmış, B = bağımsız ölçüm, C = vendor veya blog, D = [ASSUME]. Tezde bir tablo olarak gösterin. Bu, mevcut [ASSUME] disiplininizin doğal uzantısı ve hangi sonucun hangi zayıf veriye dayandığını görünür kılar.

### 2.4. Availability modeli (orta-yüksek)

- **Planlı kesinti ×10 kuralı tek bir sözlük sayfasına dayanıyor.** Kural kritik bir çarpan olduğu için daha güçlü bir kaynakla (Uptime Institute, Gartner, akademik kesinti çalışmaları) desteklenmeli ya da [ASSUME] aralığı (örn. %70–%90 planlı) olarak verilmeli.
- **ITIC "9 nine" rakamları şüpheyle ele alınmalı.** 9 nine yılda ~30 ms kesinti demek; bu bir anket öz-beyanı. "Bağımsız alt sınır" demek için fazla iyimser olabilir.
- **Availability girdisi çok kaba çalışıyor.** M2'nin effective low değeri zaten %99,9999. Yani 0,99999 ve altındaki her hedef M1 ya da M2 ile karşılanıyor. Gerçek dünya SLA'larının çoğu bu aralıkta olduğu için availability girdisi neredeyse yalnızca M1/M2 arasında seçim yapıyor.
- **Simetri fırsatı.** ITIC aynı anketlerde x86 sunucuları (Dell, HPE, Lenovo) da raporluyor (doğrulanmalı). C1–C4 için **aynı kaynak ailesini** kullanırsanız iki tarafın availability rakamları aynı metodolojiden gelir. Bu, "eşit derinlik" ilkesinin en güçlü uygulaması olur. Kaynak ailesi farklı olursa availability karşılaştırması elma-armut olur.
- M4 etiketleri henüz düzeltilmedi (log, madde 8).

### 2.5. Motivasyon ile kapsam arasında boşluk (orta)

Giriş bölümü migration başarısızlıklarıyla motive ediliyor (%66 başarısız, %287 bütçe aşımı). Ama araç migration maliyetini ve riskini kapsam dışı bırakıyor ve kararlı durum TCO'sunu karşılaştırıyor. Bir jüri şunu sorar: "Aracınız clustered'ı %20 ucuz bulsa bile, migration maliyeti bunu yer mi?"

**Öneri:** Ya çerçeveyi netleştirin ("araç kararlı durum TCO farkını verir; migration kararı bu farkın migration maliyetini kaç yılda geri ödeyeceğine bağlıdır"), ya da migration maliyetini tek bir kullanıcı parametresi olarak ekleyip **başa baş süresi** çıktısı verin. İkincisi ucuz ve motivasyonla kapsamı birbirine bağlar.

### 2.6. Zaman ufku ve finansal yöntem (orta)

Simülasyon 1 yıl, amortisman 5 yıl. data_growth_pct girdisi ise ancak çok yıllı bir ufukta anlam taşır. TCO literatüründe standart yöntem 3–5 yıllık ufuk ve iskonto oranıyla bugünkü değer (NPV) hesabı. **Öneri:** 5 yıllık TCO, yıllık büyüme (hem veri hem TPS) ve iskonto oranı [ASSUME] aralığı. Yıllık saatlik simülasyon her yıl için tekrar edilir; model hızlı olduğu için maliyeti düşük.

### 2.7. Stack seçim motorunun girdisi yok (orta)

Daraltma kuralları "regülasyon sıkılığı", "kurumsal destek ihtiyacı" ve "maliyet hassasiyeti"ne dayanıyor, ama bunların hiçbiri 8 kullanıcı girdisi arasında yok. Üstelik 8 kombinasyon hesaplama açısından önemsiz bir sayı.

**Öneri:** Daraltmayı kaldırın, **8 kombinasyonun hepsini hesaplayın** ve en ucuz feasible olanı seçin. Hepsini birden raporlamak (örn. "en ucuz açık kaynak" ve "en ucuz kurumsal" ayrı ayrı) daraltma kuralından daha savunulabilir. Kurumsal destek bir kısıtsa, bunu açık bir dokuzuncu girdi yapın. Bu ayrıca B-planı da sadeleştirir.

### 2.8. Personel maliyeti büyük olasılıkla en büyük kalem (orta)

Enterprise TCO çalışmalarında personel genellikle en büyük tek kalemdir. Bu kalem iki tarafta farklı kaynaklardan ve farklı ölçekleme kurallarıyla (MIPS başına FTE ile düğüm başına FTE) modellenirse sonucu tek başına belirleyebilir. **Öneri:** İki taraf için aynı maaş kaynağını kullanın (örn. ABD BLS OES ya da tek bir maaş anketi) ve oran varsayımlarını duyarlılık analizinde en üste koyun.

### 2.9. Belirsizliğin raporlanması (orta)

Model deterministik, ama parametrelerin önemli bir kısmı [ASSUME] aralık. Tek bir nokta tahmini ("clustered %12 ucuz") bu durumda yanıltıcı. Plandaki Phase 2 stokastik arıza modeli ise sonuç üzerinde daha az etkili. **Öneri:** Önceliği değiştirin. **[ASSUME] aralıkları üzerinde Monte Carlo** (her parametreyi aralığından örnekleme) ve **tornado/Sobol duyarlılık analizi**, arıza modelinden daha öncelikli. Çıktı "clustered'ın daha ucuz olma olasılığı" haritası olur. Bu hem araştırma sorusu 3'ü (duyarlılık) doğrudan cevaplar hem de akademik olarak çok daha güçlü bir sonuç verir.

### 2.10. Dış doğrulama yok (orta)

Modelin çıktıları henüz hiçbir dış referansla karşılaştırılmadı. **Öneri:** En azından büyüklük mertebesi kontrolü yapın. Karşılaştırma için yayımlanmış TCO çalışmaları (IBM ya da vendor destekli Forrester TEI raporları, analist çalışmaları, BMC/Rocket mainframe anketlerindeki "MIPS başına maliyet" rakamları) ve case study'lerdeki raporlanmış yapılandırmalar kullanılabilir. Vendor destekli kaynaklarla karşılaştırmayı ikili sınır mantığıyla sunun: hangi tarafa ve ne kadar sapıyor?

### 2.11. Latency (bugünkü düzeltmeden sonra)

Latency mainframe'de yalnızca tek haneli ms hedeflerde bağlayıcı (log, madde 4). Bu, "sıkı SLA büyük kademe ister" iddiasını yumuşatıyor. Clustered tarafta ağ gecikmesi ve senkron replikasyon (özellikle metro/coğrafi topolojilerde 1–30 ms) latency'yi çok daha bağlayıcı yapabilir. Bu da ilginç ve savunulabilir bir yapısal fark bulgusu olur. İki taraf aynı kuyruk ailesiyle (per-sunucu M/M/1 ya da her iki tarafta M/M/c) ve aynı D_io mantığıyla modellenmeli.

## 3. Veri toplama planı: mainframe yapısının aynası

Mainframe modeli dört veri taşıyıcısı üzerine kurulu: bir benchmark çapası (REDP-5320), bir ölçekleme tablosu (LSPR), mutlak birim köprüsü (EPS 3931-604) ve availability kaynağı (Redbook + ITIC). Clustered taraf için birebir karşılıklar aşağıda. Kaynak adları benim bilgime dayanıyor; her birinin güncel varlığı ve içeriği doğrulanmalı.

### 3.1. Throughput

| Mainframe karşılığı | Clustered kaynağı | Not |
| --- | --- | --- |
| REDP-5320 (benchmark çapası) | TPC-C sonuçları (tpc.org), HammerDB TPROC-C yayımlanmış sonuçları (HammerDB, EDB, Percona, Phoronix) | PostgreSQL için resmî TPC-C yok; HammerDB çapası B kalite. Oracle'ın x86 TPC-C sonuçları eski (2010'lar), nesil köprüsü gerekir. |
| LSPR (kademe ölçekleme) | SPEC CPU2017 rate sonuçları (spec.org) Dell R760 / HPE DL380 Gen11 / Lenovo SR650 V3 için | LSPR'nin tam karşılığı: sunucu ve CPU nesilleri arası göreli güç. Eski bir TPC-C sonucunu bugünün sunucusuna taşıyan köprü, CP-güç köprüsünün aynası olur. |
| CP sublinearitesi (18 vs 26 CP) | Aynı kaynaktan farklı çekirdek/düğüm sayılarında sonuçlar; YugabyteDB/CockroachDB çok düğüm TPC-C raporları | Düğüm içi ve düğümler arası ölçekleme verimi. |
| — | VMware performans raporları (Oracle ve PostgreSQL on vSphere), Red Hat KVM/OpenShift Virtualization performans belgeleri | Sanallaştırma overhead'i. Vendor kaynağı = üst sınır; bağımsız akademik ölçümlerle alt sınır. |

### 3.2. Fiyat (bu taraf mainframe'den daha iyi belgelenmiş)

| Kalem | Kaynak | Beklenen kalite |
| --- | --- | --- |
| Sunucu | Dell / HPE / Lenovo çevrimiçi yapılandırıcıları (liste fiyatı) | A/B |
| Oracle | Oracle Technology Global Price List ve Processor Core Factor Table (ikisi de kamuya açık PDF) | A |
| vSphere / VCF | Broadcom çekirdek başına abonelik fiyatları ve 16 çekirdek minimum kuralı | B (fiyatlar sık değişiyor; tarih not edilmeli) |
| OpenShift / OpenShift Virt | Red Hat mağaza ve abonelik sayfaları (2 çekirdek / soket başına) | A/B |
| PostgreSQL desteği | EDB vb. destek abonelikleri (opsiyonel kalem) | B |
| Enerji | Sunucu üreticilerinin güç hesaplayıcıları (Dell EIPT, HPE Power Advisor) | A |

### 3.3. Mainframe TCO genişletmesi için (Hafta 1–2)

| Kalem | Kaynak önerisi |
| --- | --- |
| z/OS, CICS, Db2 MLC | IBM yazılım duyuru mektupları ve VWLC/AWLC fiyat tabloları; Tailored Fit Pricing belgeleri |
| Donanım taban + MIPS fiyatı | Birden çok bağımsız kaynak; kamu ihale kayıtları örnek olarak kullanılabilir |
| Enerji | IBM z16 IMPP (physical planning) belgesi |
| DS8900F | IBM DS8900F Redbook'ları (kapasite, IOPS, gecikme); fiyat için bağımsız aralık |
| GDPS | IBM GDPS belgeleri; fiyat büyük olasılıkla kapalı, [ASSUME] aralık |
| Personel | Aynı maaş kaynağı her iki taraf için (örn. BLS OES); FTE oranları için analist/anket kaynakları |

### 3.4. Availability ve storage

- **Availability:** ITIC (x86 satırları, aynı anketler), Uptime Institute yıllık kesinti analizleri, Oracle MAA ve Patroni belgeleri (vendor üst sınırı).
- **Storage tek alternatif kararı:** DS8900F ile simetri için bir kurumsal all-flash dizi (örn. Dell PowerMax ya da Pure FlashArray) en savunulabilir seçim. Ceph gibi yazılım tanımlı storage, karşılaştırmaya ikinci bir paradigma farkı ekler. Bu karar veri toplamadan önce verilmeli.

## 4. Önerilen sıradaki adımlar

Planınızla uyumlu, ama sırası ve vurgusu biraz farklı:

1. **Hafta 1: Ön koşul kararlar (kısa ama kritik).**
   - Referans transaction tanımı ve iki benchmark'ın ona bağlanma yöntemi (2.1).
   - Storage tek alternatifi (3.4).
   - Zaman ufku: 5 yıl + NPV (2.6).
   - Stack seçimi: 8 kombinasyonun hepsini hesaplamak (2.7).
   - Crossover hipotezinin yeniden yazılması (2.2).
2. **Hafta 1–4: Paralel veri toplama.** Üç kişilik ekibe doğal bir bölüm:
   - (a) mainframe TCO kalemleri,
   - (b) clustered throughput (TPC-C/HammerDB + SPEC köprüsü + overhead),
   - (c) clustered fiyat + availability + personel.

   Her kişi bulduklarını ortak bir **kaynak kaydına** işler. Kayıt her parametre için değer, aralık, kaynak, tarih ve kalite notu içerir.
3. **Hafta 3–4 (paralel): Kod iskeleti.** Mevcut tek dosyayı bölmeden önce iki taraf için ortak bir arayüz tanımlayın: `girdi → feasible konfigürasyon + yıllık maliyet dökümü (aynı kategorilerle)`. Karşılaştırma katmanı ve tarama bu arayüz üzerine kurulur. Böylece clustered modeli yazılırken mainframe kodu bozulmaz; testler de bunu korur.
4. **Hafta 5–9: Clustered model.** Planınızdaki gibi, sadece daraltmasız 8 kombinasyonla ve mainframe ile aynı kuyruk ailesiyle.
5. **Hafta 10–11: Tarama + belirsizlik.** Parametre taraması, crossover haritaları, Monte Carlo ve tornado. Stokastik arıza modeli ancak zaman kalırsa (2.9).
6. **Hafta 12: Dış doğrulama.** Yayımlanmış TCO rakamlarıyla büyüklük mertebesi kontrolü (2.10).
7. **Hafta 13–14: Tez ve sunum.**

## 5. Senin karar vermen gerekenler

- Referans transaction yaklaşımını benimsiyor musunuz? (Önerim: evet. Tez savunmasında en çok sorgulanacak nokta bu.)
- Stack daraltma yerine 8 kombinasyonun hepsini hesaplamak. (Önerim: evet.)
- Stokastik arıza modeli yerine önce parametre belirsizliği için Monte Carlo. (Önerim: evet.)
- Migration maliyetini başa baş süresi için tek bir parametre olarak eklemek. (Önerim: evet, düşük maliyetli ve motivasyonu kapsama bağlıyor.)
- Storage için kurumsal all-flash dizi mi, yazılım tanımlı storage mı? (Önerim: kurumsal dizi.)

Onay verdiğin maddelerden başlayarak ilk somut adım olarak **kaynak kaydı şablonunu** hazırlayıp mainframe TCO kalemleri için kaynak aramaya başlayabilirim.
