# Benzer Çalışmalar Taraması: Projemize Paralel Yapılmış İşler ve Bulguları (v1)

*Tarih: 2026-11-02 · Durum: literatür taraması; kod yazılmadı · İlgili dokümanlar: `project_justification.md` §2.3 (mevcut kaynaklar neden yetmiyor), `acik_sistem_arastirma_plani_v1.md` (x86 araştırma planı)*

Bu doküman bir soruya cevap arar: **Bizim yaptığımızı (on-prem mainframe ile kümelenmiş x86'yı OLTP için tam yığın maliyetle, ortak bir işlem birimiyle ve aralıklarla karşılaştırmayı) daha önce yapan var mı? Varsa ne bulmuşlar?**

`project_justification.md` §2.3, mevcut kaynak türlerini ve neden yetmediklerini tek satırlık özetlerle verir. Bu doküman o tabloyu çalışma düzeyine indirir: her çalışmanın ne yaptığı, ne bulduğu ve **bizim modelimize ne getirdiği** (doğrulama hedefi, yöntem, uyarı ya da kapsam sınırı).

Etiketler önceki dokümanlarla aynıdır: **[VENDOR]** üretici ya da üreticinin sponsor olduğu kaynak · **[PEER]** hakemli akademik yayın · **[TEZ]** lisansüstü tez · **[ANKET]** sektör anketi · **[RESMİ]** düzenleyici kurum kaydı · **(doğrulanmalı)** yalnızca ikincil özetten okunmuş bilgi.

---

## 0. Kısa Cevap

1. **Doğrudan paralel, bağımsız bir akademik çalışma bulunamadı.** Mainframe ile kümelenmiş x86'yı OLTP için tam yığın TCO'yla, ortak bir işlem birimiyle ve belirsizlik aralıklarıyla karşılaştıran hakemli bir yayın, tez ya da açık bir araç yok. Geniş kapsamlı ek bir arama da (2022–2025 tezleri dahil) sonuç vermedi.
2. **En yakın paralel üretici kaynaklı.** IBM'in Eagle TCO ekibi 2007'den beri 300'ü aşkın müşteri çalışması yapmış. Yayımlanan özetlere göre karşılaştırılan 97 çalışmada dağıtık alternatif ortalama **2,2 kat** pahalı çıkmış, yalnız 4'ünde dağıtık taraf ucuzmuş [IBM-EAGLE-2013]. Yöntem bizimkine çok benziyor (eşdeğer konfigürasyon → edinme maliyeti → personel ve tesis), ama varsayımlar ve girdiler yayımlanmıyor ve sonuç her zaman yayımlayan üreticinin lehine.
3. **Akademik literatür parçaları ayrı ayrı inceliyor.** $/TPS metriğinin kökeni (Anon et al. 1985; TPC), ölçek-büyütme ile ölçek-yaymanın fiyat/performansı (Barroso & Hölzle; Appuswamy 2013), kiralama/satın alma NPV'si (Walker 2009), işlem işleme maliyetinin ölçülmesi (Kossmann 2010) ve göç vakaları (Khadka 2014; Hayretci 2021; Brune & Helbig 2025). Hiçbiri personel, availability/DR, lisans ve storage'ı birlikte almıyor.
4. **Bu durum projenin boşluk iddiasını destekliyor, ama dikkatli söylenmeli.** "Kimse yapmadı" değil, "yayımlanmış, bağımsız ve tekrarlanabilir biçimde yapılmadı" demek doğru (bkz. §7).
5. **Taramanın modele en önemli katkısı bir uyarı.** IBM çalışmalarında bir mainframe işlemcisine karşılık 24–80 x86 çekirdeği gerekiyor; bizim köprümüz ise 1 z16 CP ≈ 2,2 R760 çekirdeği diyor. Farkın büyük kısmı **kullanım oranından** ve **üretim dışı ortamlardan** geliyor, saf işlemci hızından değil. Modelimiz bu iki şeyi açık parametre olarak taşımazsa sonuç, kaynak seçimine göre on kat oynayabilir (bkz. §3.3 ve §8).

---

## 1. Tarama Yöntemi

**Arama alanları:** hakemli yayınlar (SIGMOD, VLDB, SoCC, ICSE, IEEE Computer), lisansüstü tezler (Türkiye dahil), IBM ve diğer üreticilerin TCO yayınları, analist ve anket raporları, düzenleyici kurum kayıtları.

**Dahil etme ölçütü.** Bir çalışma şu üç koşuldan en az birini sağlıyorsa alındı:
- (a) mainframe ile dağıtık/kümelenmiş platformu maliyet ya da performansla doğrudan karşılaştırıyor;
- (b) bizim modelimizin bir bileşeni için yöntem veriyor ya da yöntemimizle karşılaştırılabilir ($/TPS, NPV, ölçeklenme modeli);
- (c) karar sonrasını (göç, modernizasyon) ampirik olarak belgeliyor.

Konuyla yalnızca genel olarak ilgili olanlar (pazarlama yazıları, kaynaksız bloglar) §9.2'deki ret tablosuna gitti.

**Sınırlılık.** Semantic Scholar, OpenAlex ve Crossref API'leri çalışma ortamımızdan erişilemedi. Arama genel web araması ve yayın sayfalarının doğrudan okunmasıyla yapıldı. Sistematik bir literatür taraması (PRISMA tarzı, sayılabilir arama dizgileri ve eleme adımlarıyla) **değildir**. Tezde bu bölüm "hedefli literatür taraması" olarak adlandırılmalı. Ücretli analist raporları (Gartner, Forrester, Avasant) okunamadı.

---

## 2. Akış A: $/TPS Metriğinin Soy Ağacı

Projenin ana çıktısı olan **aylık $/TPS**, 40 yıllık bir metriğin genişletilmiş hâlidir. Bu soy ağacı tezde metriğin meşruiyeti için kullanılmalı.

### 2.1. Anon et al. (1985), "A Measure of Transaction Processing Power" [PEER]
- **Ne yaptı:** DebitCredit (sonradan TPC-A'nın temeli) iş yükünü ve **maliyet/TPS** metriğini tanımladı. Maliyet = 5 yıllık donanım + yazılım + bakım; bölü TPS. Personel ve kesinti maliyeti **dışarıda**.
- **Bulgusu:** 1973'teki bir banka örneğinde minibilgisayar ~$50K/TPS, mainframe ~$250K/TPS. Yani "mainframe mi, daha küçük makineler mi" sorusunun maliyet/TPS ile sorulması 1985'te başladı.
- **Bize getirdiği:** Metriğimiz bu tanımın genişletmesi. Anon et al.'ın dışarıda bıraktığı iki kalem (personel ve kesinti) bizim modelimizde **en büyük iki belirsizlik kaynağı** (10K TPS'te personel ~%50). Bu, genişletmenin neden gerekli olduğunu gösteren iyi bir argüman.

### 2.2. Gray (2005), DebitCredit'in 20 yıl sonrası [PEER]
- **Bulgusu:** İşlem fiyat/performansı 20 yılda yılda yaklaşık **%68** iyileşti.
- **Bize getirdiği:** Fiyat/performansın bu hızla değişmesi, iki tarafın **aynı dönemden** fiyatlanması gerektiğini gösterir. Bu, x86 planındaki `PRICE_EPOCH` kuralının (plan §5, §12) tarihsel gerekçesidir. Farklı yıllardan alınmış iki çapa, platform farkından büyük bir fark üretebilir.

### 2.3. TPC Pricing Specification v2.9.0 [STANDART]
- **Ne yapar:** TPC sonuçlarında fiyatı 3 yıllık sahip olma maliyeti olarak tanımlar: donanım, yazılım, 7/24 bakım. Yazılım, çalışabileceği **tüm** donanım üzerinden lisanslanır; kullanım oranına göre indirim yapılamaz. Personel, enerji ve tesis **dışarıda**.
- **Bize getirdiği:**
  - "Yazılım çalışabileceği tüm donanım için lisanslanır" kuralı, Oracle'ın çekirdek başı lisans mantığıyla ve bizim x86 lisans tabanı köprüsüyle (plan K12) aynı. Mainframe'de ise R4HA faturalaması tam da bu kuralın **istisnası**: yazılım kullanılan kapasite üzerinden ödenir. Bu asimetri TPC'nin bile yakalamadığı bir farktır ve modelimiz bunu iki tarafta ayrı ayrı modelleyerek yakalıyor.
  - TPC'nin 3 yıllık ufku ile bizim 5 yıllık NPV ufkumuz farklı. Tezde neden 5 yıl seçildiği (mainframe nesil döngüsü, IBM Eagle'ın "kısa ufuk yenileme etkisini kaçırır" uyarısı, §3.2) açıkça yazılmalı.

### 2.4. Poess & Nambiar (2008), "Energy Cost, the Key Challenge of Today's Data Centers: A Power Consumption Analysis of TPC-C Results", VLDB [PEER]
- **Ne yaptı:** TPC-C sonuçlarının yayımlanmış konfigürasyonlarından güç tüketimini tahmin eden bir model kurdu ve enerji maliyetinin 3 yıllık sahip olma maliyetinde büyüyen bir pay olduğunu gösterdi. Bu çalışma TPC-Energy spesifikasyonuna giden yolu açtı. (Ayrıntılı oranlar özetten okunduğu için doğrulanmalı.)
- **Bize getirdiği:** Enerjinin, TPC'nin dışarıda bıraktığı ama ölçülebilir bir kalem olduğunu belgeler. Modelimizde enerji iki tarafta da var; mainframe'de küçük bir pay. x86 tarafında sunucu sayısı arttıkça payın büyüyüp büyümediği, karşılaştırmanın ilginç bir alt sonucu olabilir.

**Akış A'nın özeti.** $/TPS metriği köklü, ama standart tanımı (Anon et al., TPC) bilerek **personel, kesinti ve tesisi** dışarıda bırakır. Bizim katkımız metrik değil, metriğin tam yığına genişletilmesidir. Tezde bunu "yeni bir metrik" olarak değil, "standart metriğin karar amaçlı genişletmesi" olarak sunmak daha savunulabilir.

---

## 3. Akış B: Mainframe ile Dağıtık Sistemin Maliyet Karşılaştırmaları (Üretici ve Analist)

Doğrudan paralel çalışmaların neredeyse tamamı bu akışta, ve neredeyse tamamı IBM kaynaklı. Bu bölüm o yüzden hem bulguları hem de **yayın yanlılığını** kayda geçirir.

### 3.1. IBM, Shedletsky (2008), "Mainframe versus Distributed TCO Studies and Experiences" [VENDOR]
- **Yöntem:** Yukarıdan aşağı TCO: (1) eşdeğer konfigürasyonu kur, (2) edinme maliyetini (TCA: donanım + yazılım + 3 yıllık yıllık ücretler) hesapla, (3) personel ve tesis maliyetini ekle. Konsolidasyon için formül: `N < P_R × U_R × C_R` (işlemci performans oranı × kullanım oranı × sunucu başına çekirdek). Tipik oranlar: performans 1–3, **kullanım 10–20**, çekirdek 1–64.
- **Bulgular:**
  - Bankacılık benchmark'ı, **2.200 TPS**: z10'da 5 işlemci (dev/QA ile 7); dağıtıkta 280 işlemci (dev/QA ile 560). 3 yıllık TCA $18,2M (z) vs $43,3M (dağıtık), **2,4 kat**. Çekirdek oranı **80:1**.
  - Finans kurumlarında dört vaka: TCA oranları 2,2–3,7 kat; çekirdek oranları **24:1 – 80:1**.
  - Dağıtık sunucu başına yıllık işletim maliyeti (IBM iç çalışması, 3.917 sunucu): $34.447; bunun $20.359'u (%59) sistem yöneticisi emeği. **7,8 sunucu/yönetici**, yönetici başına $159.800.
  - Aynı işlem için x86'da (WebSphere) z'ye (CICS/COBOL) göre **4,9 kat fazla komut, 12,6 kat fazla makine çevrimi**.
  - Hyper-V'de 5 VM ile işlem başına ~%50 CPU ek yükü.
- **Bize getirdiği:**
  - **Doğrulama hedefi (2.200 TPS banka).** Bizim modelimiz 2.200 TPS'te iki tarafı çalıştırdığında ortaya çıkan oran bu çalışmanın 2,4 katıyla karşılaştırılabilir. Bu bir "doğru cevap" değil (üretici, 2008 donanımı, edinme maliyeti), ama büyüklük mertebesi kontrolü.
  - **Çekirdek oranı uyarısı:** §3.3'te ayrıntılı.
  - **Komut yolu farkı (4,9×) bizim kapsamımızın dışında kalıyor.** K1 köprümüz iki tarafta aynı SQL bileşimini varsayar ve uygulama katmanını dışarıda bırakır (plan §14.4). IBM'in 4,9× iddiası uygulama sunucusu katmanından (CICS ile WebSphere farkı) geliyor. Bu, kapsam asimetrisinin sayısal bir tahmini olarak tezde anılmalı: "uygulama katmanı dahil edilseydi fark x86 aleyhine büyüyebilirdi; IBM'in iddiası 4,9× ama bağımsız doğrulaması yok."
  - **Sanallaştırma ek yükü:** %50 (Hyper-V, 2008) bizim plandaki %2–15 aralığının (plan §3.6) çok üstünde. Eski hipervizör ve konsolidasyon yoğunluğu farkı; kullanılmamalı, ama aralığımızın neden güncel ölçümlere dayandığı bu kontrastla açıklanabilir.

### 3.2. IBM CPO, "TCO Lessons Learned from Customer Engagements" (2013, v4) [VENDOR]
- **Bulgular:**
  - 97 müşteri çalışmasında dağıtık alternatif ortalama **2,2 kat** pahalı; yalnız **4/97**'de dağıtık ucuz. İş birimi başına toplam BT maliyeti oranı vakalarda 1,9× ve 3,3×.
  - **DR maliyetinin toplam doğrudan maliyetteki payı:** System z'de %3, dağıtıkta %21 (büyük bir Avrupa sigortacısı); iki kritik dağıtık yükte %40'ın üzerinde.
  - **RTO:** dağıtıkta 48–60 saat vs mainframe ~20 dakika (bir otel zinciri, ~200 sunucu). Yıllık DR testi 14.952 vs 2.051 kişi-saat (plan §10'da zaten kullanılıyor).
  - **Üretim dışı ortamlar:** HA için adanmış yedek 2,5× üretim ya da N+1'de 2×; mainframe'de ≤1×. Geliştirme/test: mainframe'de üretim +%20, dağıtıkta çoğu zaman üretim **+%200**.
  - **Yenileme döngüsü:** dağıtık sunucular 3–5 yılda bir değişiyor; 30 aylık bir kiralama 6 aylık örtüşmeyle yalnız 24 ay üretim verebiliyor. Mainframe yerinde yükseltiliyor.
  - **Göç (offload) sonuçları:** planlanan sürenin ortalama **iki katı**; 3.500 MIPS hedefli bir projede 18 ayda $25M harcanıp yalnız %10 taşınabilmiş; iki kamu vakasında geri ödeme süresi **20 ve 29 yıl**.
  - Ağ üzerinden çağrı, CICS içi çağrıya göre ~2× CPU ve 3×'ten uzun yanıt süresi.
  - Yöntem: 5 yıllık ufuk; "kısa ufuklar yenileme etkisini yakalamaz."
- **Bize getirdiği:**
  - **DR payı bir çıktı kontrolü olabilir.** Modelimiz her topoloji için DR maliyetinin toplam içindeki payını raporlarsa, IBM'in %3 / %21 iddiasıyla karşılaştırılabilir. Bizim mainframe DR'ımız CBU ile ucuz (DR çerçevesi kesri 0,3–1,0); x86'da ikinci sahanın tam kopyası. Bu, iddianın mekanizmasını şeffaf biçimde test eder.
  - **Üretim dışı ortamlar modelimizde yok.** Bu bilinçli bir kapsam kararı olmalı ve iki tarafta simetrik olarak dışarıda olduğu yazılmalı. IBM'in "+%20 vs +%200" iddiası doğruysa bu, x86 aleyhine büyük bir kalem; dışarıda bırakmak sonucu x86 lehine kaydırır. **Karar (Emirhan, 2026-11-02):** iki tarafa ayrı, aralıklı bir `NONPROD_FACTOR` eklenecek (Adım 6 ortak modülünde). Düşük uç 0 alınarak "kapsam dışı" senaryosu da gösterilecek. Mainframe için IBM'in +%20'si, x86 için +%200'ü yüksek uç adayı; orta değerler bağımsız bir kaynakla daraltılmalı.
  - **Yenileme döngüsü** x86 NPV'sinde (5 yıl ufukta bir yenileme olup olmadığı) açık bir varsayım olmalı. Plan §12'deki x86 amortisman süresi (3–5 yıl) bu kaynakla destekleniyor.
  - **Göç maliyeti** kapsam dışında (justification §5.2: uygulama göçü ayrı problem). Ama göç riski, crossover bölgesinin **yorumunu** değiştirir: x86'nın biraz ucuz çıktığı bir bölgede göç maliyeti farkı silebilir. Tezde crossover'ın "yeşil alan (greenfield) ya da kararlı durum" kararı için geçerli olduğu yazılmalı.

### 3.3. Çekirdek oranı çelişkisi: 24–80 çekirdek mi, 2,2 çekirdek mi?

Taramanın modele en önemli katkısı bu. IBM çalışmalarında bir mainframe işlemcisinin yerini 24–80 x86 çekirdeği alıyor. x86 planımızda ise 1 z16 CP ≈ 2,2 R760 çekirdeği bulduk (plan §3.5). On kattan büyük bu fark nereden geliyor?

IBM'in kendi formülü cevabı veriyor: `N < P_R × U_R × C_R`. Oran üç çarpandan oluşuyor:

| Çarpan | IBM varsayımı | Bizim modeldeki karşılığı |
|---|---|---|
| İşlemci performans oranı `P_R` | 1–3 | Kapasite köprüsü (plan K2): z16 CP ile R760 çekirdeği arasında ~2,2. **Uyumlu.** |
| Kullanım oranı `U_R` | **10–20** (dağıtık sunucular %5–12 kullanımda, mainframe %80–90) | Kullanım hedefi. Mainframe'de kuyruk modeli ve kademe seçimiyle belirleniyor; x86'da henüz parametre değil. **Açık nokta.** |
| Üretim dışı ve HA kopyaları | dev/QA ile ×2; HA için 2–2,5× | Modelde yok; HA topolojide (X1–X4) var, dev/test yok. **Kapsam dışı.** |

Yani IBM'in çekirdek oranının büyük kısmı işlemci hızından değil, **dağıtık sunucuların düşük kullanımından** ve **çoğaltılmış ortamlardan** geliyor. Bu bizim kapasite köprümüzü çürütmez; tersine, köprünün yalnız `P_R`'yi ölçtüğünü ve kalanın başka parametrelerde olması gerektiğini gösterir.

**Modele sonuçları:**
1. x86'da **hedef kullanım oranı** açık ve aralıklı bir parametre olmalı. Düşük ucu IBM'in gözlemlediği konsolide edilmemiş dünyaya (%10–20), yüksek ucu iyi işletilen sanallaştırılmış kümeye (%50–70) yakın. Kuyruk modeli zaten bir üst sınır verir; alt sınır işletim pratiğidir. Bu, Adım 6 öncesinde x86 parametre listesine (plan §12) eklenmeli.
2. Bu parametre tornado sıralamasında üst sıralarda çıkarsa, bu raporlanacak bir bulgudur: "karşılaştırmanın sonucu, x86 kümesinin ne kadar iyi işletildiğine çok duyarlı."
3. Literatürdeki "mainframe 2–3 kat ucuz" iddialarıyla bizim sonuçlarımız arasındaki fark, bu parametrenin hangi değerinde kapandığına bakılarak açıklanabilir. Bu tezde güçlü bir analiz bölümü olur.

### 3.4. Rubin Worldwide (2012), "The Real Cost of Mainframe vs Distributed" [ANKET, üretici bağlantılı]
- **Ne yaptı:** 498 kuruluşun BT harcamasını sektör çıktısına (örneğin banka başına işlem) göre normalize etti.
- **Bulgu:** Sunucu ağırlıklı kuruluşların iş birimi başına maliyeti ortalama **%31 yüksek**; mainframe ağırlıklı kuruluşlar altyapıya daha az yatırım yapıyor. (Ayrıntılı oranlar özetten.)
- **Bize getirdiği:** Kuruluş düzeyinde, korelasyona dayalı bir bulgu; nedensellik yok (mainframe kullanan kuruluşlar daha büyük ve olgun). Bizim iş yükü düzeyindeki, mekanizmaya dayalı yaklaşımımızın neden farklı ve tamamlayıcı olduğunu göstermek için kullanılabilir. Model parametresi beslemez.

### 3.5. IDC (2020), z14 yükseltmesi yapan kuruluşlar [ANKET, IBM sponsorlu]
- **Bulgu:** 5 yılda işletim maliyetinde %19 düşüş; personel %16 daha verimli.
- **Bize getirdiği:** Mainframe personel eğrimizin alt eğimini (kapasite arttıkça personel sublineer artar) dolaylı destekler. Sponsorlu ve yalnız mainframe tarafı; karşılaştırma değil.

### 3.6. Kyndryl (2025, n=500) ve BMC (2024) anketleri [ANKET, üretici bağlantılı]
- **Bulgu:** Kyndryl: mainframe modernizasyonunda %288–362 ROI, %70 beceri açığı. BMC: katılımcıların %94'ü mainframe'i uzun vadeli platform görüyor, %69'unda kapasite artıyor.
- **Bize getirdiği:** Bağlam ve motivasyon. **Beceri açığı** önemli: personel ücretlerimiz (BLS) iki tarafta ortalama ücretlere dayanıyor; z/OS uzmanı kıtlığı gerçekse mainframe ücret primi aralığın yüksek ucunda temsil edilmeli. Şu anki aralık (mid $162K, high $215K) bunu kısmen taşıyor; tezde açıkça bağlanmalı.

**Akış B'nin özeti.** Doğrudan paralel çalışmalar var ama **tek taraflı** (neredeyse tamamı IBM ya da IBM ortaklarından). Bağımsız, karşı tarafın (x86 üreticisi ya da göç firması) yayımladığı karşılaştırılabilir bir çalışma bulunamadı; göç firmalarının yayınları sayı içermeyen pazarlama metinleri. Bu bir **yayın yanlılığı** tehdidi (§8).

---

## 4. Akış C: Ölçek-Büyütme ile Ölçek-Yaymanın Fiyat/Performansı (Akademik)

### 4.1. Stonebraker (1986), "The Case for Shared Nothing" [PEER]
- **Ne yaptı:** Paylaşımlı bellek, paylaşımlı disk ve paylaşımsız mimarileri karşılaştırdı; paylaşımsızın ölçeklenme ve maliyet avantajını savundu.
- **Bize getirdiği:** K1 storage kararının (Oracle RAC → paylaşımlı disk/SAN; Patroni → paylaşımsız, yerel NVMe × replika) kavramsal temeli. `project_justification.md` §2.3'te zaten anılıyor; burada bulgusunun storage kararına doğrudan bağlandığını kaydediyoruz.

### 4.2. Barroso, Clidaras & Hölzle, *The Datacenter as a Computer* (2. ve 3. baskı, 2013/2018) [PEER, kitap]
- **Ne yaptı:** Bölüm 3'te 2007 sonundaki en iyi TPC-C sistemi (HP Superdome, ~$12M) ile fiyat/performans birincisini (HP ProLiant ML350, ~$75K) karşılaştırdı. Bölüm 6'da veri merkezi TCO modeli kurdu: sermaye gideri (yapım, kritik watt başına ~$10–20) + işletim gideri.
- **Bulgular:**
  - Küçük sunucunun fiyat/performans üstünlüğü, storage hariç **3×'ten 12×'in üstüne**, indirimler de hariç tutulunca **~20×**.
  - Storage, ProLiant'ın donanım maliyetinin ~¾'ü; Superdome'da ~%40.
  - Basit bir iletişim modeliyle: düğüm sayısı arttıkça uzak erişim oranı artar ve kümenin üstünlüğü erir. Sonuç: düşük sınıf yapı taşı, rekabetçi olmak için yüksek sınıfa karşı "sağlıklı" bir maliyet etkinliği üstünlüğüne sahip olmalı.
- **Bize getirdiği:**
  - **Edinme maliyetinde x86 lehine güçlü bir sonuç**, ama yalnız donanım ve indirimli fiyat üzerinden; personel, lisans, DR yok. Bizim tam yığın modelimiz bu 3–20× donanım avantajının diğer katmanlarda ne kadarının geri alındığını gösterebilir. Tezde bu, iki uç literatürü (Barroso: "küçük sunucu çok ucuz"; IBM: "mainframe 2–3× ucuz") **aynı model içinde uzlaştırma** girişimi olarak sunulabilir.
  - **Storage payı gözlemi** bizim plandaki storage fiyat tanımı sorununu (plan §7: etkin TB ile ham TB) destekler: platformlar arası karşılaştırmada storage kolayca baskın kalem olur ve tanım farkı sonucu çevirebilir.
  - İletişim modeli, Patroni tek yazıcı tavanı ve RAC ölçeklenme kaybı için (plan §4) nitel destek.

### 4.3. Appuswamy et al. (2013), "Scale-up vs Scale-out for Hadoop: Time to Rethink?", SoCC [PEER]
- **Bulgu:** Tek bir büyük sunucu, 16 düğümlü kümeyi performans/dolar açısından incelenen tüm işlerde geçti (çoğu Hadoop işinin girdisi küçük olduğu için).
- **Bize getirdiği:** "Ölçek-yayma her zaman ucuz" varsayımının iş yüküne bağlı olduğunu gösteren hakemli bir örnek. Ancak analitik iş yükü ve yalnız edinme maliyeti. Bizim beklediğimiz desenle (justification §4: birden fazla işaret değişimi) uyumlu bir sezgi verir, sayı vermez.

### 4.4. Gunther, Universal Scalability Law ve PostgreSQL ölçümü [yöntem, PEER + uygulayıcı]
- **Bulgu:** PostgreSQL 9.1, 32 çekirdekte USL uydurması α ≈ 0,00096, β ≈ 0,0025; tepe noktası N ≈ 20–30 civarı. (Eski sürüm; güncel sürümlerde tepe çok daha yüksekte.)
- **Bize getirdiği:** x86 planındaki düğüm içi ölçeklenme fonksiyonu `S(n) = (n/48)^(b−1)` basit bir üstel. Kendi sysbench ölçümümüz (K6) yapıldığında, ölçülen noktalara USL uydurmak hem daha savunulabilir hem de çekişme (α) ve tutarlılık (β) bileşenlerini ayırır. **Öneri:** K6 protokolüne USL uydurmasını eklemek. Mainframe tarafında LSPR kademeleri zaten ölçülmüş ölçeklenme verir; iki tarafın ölçeklenme eğrisini aynı fonksiyon ailesiyle göstermek simetri sağlar.

**Akış C'nin özeti.** Akademik literatür, ölçek-yaymanın donanım fiyat/performansında büyük bir avantajı olduğunu (3–20×), ama bu avantajın iletişim, iş yükü boyutu ve ölçeklenme kaybıyla eridiğini gösteriyor. Hiçbiri bunu tam yığın maliyete taşımıyor.

---

## 5. Akış D: Maliyet Modelleme Yöntemleri (Yöntemsel Paraleller)

Bu çalışmalar mainframe'i incelemiyor, ama bizim yaptığımız türden bir **maliyet modeli** kuruyorlar. Yöntemimizi savunurken referans noktası olarak kullanılabilirler.

### 5.1. Walker (2009), "The Real Cost of a CPU Hour", IEEE Computer 42(4) [PEER]
- **Ne yaptı:** Kiralanan CPU-saatin maliyetini, eşdeğer bir kümeyi satın alıp işletmenin maliyetiyle **NPV** üzerinden karşılaştıran bir modelleme aracı önerdi.
- **Bize getirdiği:** 5 yıllık NPV ufkumuzun ve "levelized" (seviyelendirilmiş) $/TPS hesabımızın (v3 §8.10) yöntemsel bir öncülü. Walker'ın sayısal sonuçları erişilebilen özette yok (doğrulanmalı). Çalışma bulutu kapsam dışı bırakma kararımızı (justification §5.2) etkilemez, ama NPV ile sahiplik/kiralama karşılaştırmasının hakemli literatürde yerleşik olduğunu gösterir.

### 5.2. Kossmann, Kraska & Loesing (2010), "An Evaluation of Alternative Architectures for Transaction Processing in the Cloud", SIGMOD [PEER]
- **Ne yaptı:** TPC-W'nin sipariş karışımıyla (isteklerin ~1/3'ü güncelleme) beş mimariyi ve sekiz servisi karşılaştırdı.
- **Yöntemsel olarak önemli iki tanım:**
  - **WIPS:** yalnız **yanıt süresi sınırını karşılayan** istekler sayılır. Bu, bizim "latency SLA'sını karşılayan kapasite" yaklaşımımızla (M/M/1 ile hedef yanıt süresi altında kalan TPS) aynı fikir: SLA'yı ihlal eden işlem kapasite sayılmaz.
  - **Maliyet öngörülebilirliği:** farklı yük düzeylerinde $/WIPS'in standart sapması.
- **Bulgular:** $/WIPS yük düzeyine göre çok değişiyor; sabit maliyetli seçeneklerde yük arttıkça düşüyor. Maliyet sürücüleri mimariye göre tamamen farklı (ağ trafiği, sorgu CPU'su, istek başına storage ücreti).
- **Bize getirdiği:**
  - SLA'ya bağlı kapasite tanımımız için hakemli bir dayanak.
  - **Öneri:** TPS ekseni boyunca $/TPS'in değişkenliğini bir çıktı olarak raporlamak. Mainframe'in kademeli yapısı (justification §4) $/TPS'i testere dişi biçiminde dalgalandırır; x86'nın ince taneli yapısı daha düz bir eğri verir. "Hangisi ortalamada ucuz" sorusunun yanında "hangisinin maliyeti büyümeye karşı daha öngörülebilir" sorusu da kurumsal karar için anlamlı. Bu, mevcut tornado ve aralık çıktılarına ek, ucuz bir çıktı.

### 5.3. Khajeh-Hosseini et al. (2011), bulut göçü maliyet modelleme araçları [PEER, arXiv 1105.0149]
- **Ne yaptı:** BT altyapısını buluta taşımanın maliyetini UML tabanlı bir modelle hesaplayan bir araç ve vaka çalışmaları sundu.
- **Bize getirdiği:** "Kurumun kendi girdileriyle çalışan parametrik maliyet aracı" fikrinin akademik bir örneği; bizim aracımızın türü için emsal. Bulut odaklı olduğu için sayı beslemez.

---

## 6. Akış E: Göç ve Modernizasyonun Ampirik Kayıtları

Bu akış karar **sonrasını** belgeliyor. Modelimiz göç maliyetini hesaplamıyor (justification §5.2), ama bu çalışmalar crossover sonuçlarının nasıl yorumlanacağını belirliyor.

### 6.1. Khadka et al. (2014), "How Do Professionals Perceive Legacy Systems and Software Modernization?", ICSE [PEER]
- **Ne yaptı:** 26 uygulayıcıyla görüşme ve bir anket.
- **Bulgu:** Eski sistemler uygulayıcılar tarafından güvenilir ve iş için amaca uygun görülüyor; modernizasyon kararı yalnız maliyetle değil, esneklik ve beceri gibi teknik olmayan etkenlerle de veriliyor (ayrıntılı motivasyon sıralaması özetten okunamadı; doğrulanmalı).
- **Bize getirdiği:** Maliyetin kararın tek belirleyeni olmadığını gösterir. Tezde aracın "maliyet boyutunu nesnelleştiren bir girdi" olduğu, kararın tamamı olmadığı yazılmalı.

### 6.2. Hayretci (2021), "Comparative Analysis of Case Studies on Legacy System Migration in Banking Industry", Boğaziçi Üniversitesi [TEZ]
- **Ne yaptı:** 2014–2020 arasında üç büyük perakende bankanın (Türkiye bağlamı) eski sistem göçlerini karşılaştırdı: motivasyon, strateji ve hangi uygulamanın önce taşınacağının önceliklendirilmesi.
- **Bulgu:** Hedef mimariyi mevcut mimari, en acil operasyonel sorunlar ve sektör eğilimleri belirliyor; kurum kültürü ve mimari kurulların yönetişimi planlamayı güçlü biçimde etkiliyor; değer odaklı program yönetimi en iyi önceliklendirmeyi veriyor. Erişilebilen özette maliyet ya da mainframe'e özgü sayı yok.
- **Bize getirdiği:** Türkiye'den, yerel bankacılık bağlamında bir emsal. Tezde "aynı soruya yerel literatür nitel yaklaşmış; nicel ve parametrik bir araç yok" demek için kullanılabilir. Tam metin okunursa banka göçlerinin süre ve kapsam bilgisi bağlam olarak eklenebilir.

### 6.3. Brune & Helbig (2025), "Managed Evolution of a Legacy Core Banking System: Case Study from a European Bank", itAIS [PEER, konferans]
- **Bulgu:** Mainframe tabanlı bir çekirdek bankacılık uygulamasının **kademeli ve yönetilen evrimi**, "olduğu gibi taşıma" (lift-and-shift) ya da tam değiştirmeye göre maliyet, risk ve çözüm kalitesi açısından daha iyi. Sayısal sonuç özette yok.
- **Bize getirdiği:** Güncel (2025) bir akademik kaynağın, "mainframe ya da x86" ikiliğinin pratikte çoğu zaman "mainframe'de kalıp evrilmek" ile "taşımak" arasında olduğunu söylemesi. Aracımızın karşılaştırması bu ikinci seçeneğin kararlı durum maliyetini verir.

### 6.4. TSB (2018), PRA/FCA nihai bildirimleri [RESMİ]
- **Bulgu:** Çekirdek bankacılık göçü sonrası 1,9M müşteri etkilendi, 8 ay süren aksama; PRA cezası £18,9M, FCA ile toplam ~£48,65M. Kök nedenler test yetersizliği ve tedarikçi hazırlığı.
- **Bize getirdiği:** Göç riskinin düzenleyici kayıtla belgelenmiş bir örneği. Availability modelimiz kararlı durum kesintisini ölçer; göç anındaki kesinti riski ayrı bir kategoridir ve kapsam dışıdır. Tezde sınırlılık olarak anılmalı.

### 6.5. Modernization Intel (2025), 29 göç projesi [ANKET]
- Zaten `project_justification.md` §2.2'de kullanılıyor (%66 başarısız, ortalama %287 bütçe aşımı, 22,4 ay gecikme). IBM Eagle'ın "ortalama iki kat süre" bulgusuyla (§3.2) uyumlu; iki bağımsız kaynak aynı yönü gösteriyor.

**Akış E'nin özeti.** Göç literatürü nicel değil, çoğunlukla nitel vaka çalışması. Ortak mesaj: göçün maliyeti ve riski, platformların kararlı durum maliyet farkını kolayca aşabilir. Bizim aracımız bu yüzden "göç edilsin mi" sorusuna değil, "hangi koşullarda hangi platformun kararlı durumda ucuz olduğu" sorusuna cevap verir. Bu ayrım tezde açıkça yazılmalı.

---

## 7. Sentez: Kim Neyi Kapsıyor?

| Çalışma | Tür | OLTP | On-prem iki platform | Ortak işlem birimi | Personel | Availability / DR | Lisans + storage | Aralık / belirsizlik | Crossover | Bağımsız | Girdiler açık |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Anon et al. 1985 | PEER | ✓ | kısmen | ✓ (DebitCredit) | ✗ | ✗ | kısmen | ✗ | ✗ | ✓ | ✓ |
| TPC Pricing | Standart | ✓ | ✗ (tek sistem) | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| IBM Shedletsky 2008 | VENDOR | ✓ | ✓ | kısmen (banka benchmark'ı) | ✓ | kısmen | ✓ | ✗ | ✗ | ✗ | ✗ |
| IBM Eagle 2013 | VENDOR | çoğunlukla | ✓ | ✗ (vaka bazlı) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Rubin 2012 | ANKET | ✗ (kuruluş düzeyi) | ✓ | sektör çıktısı | dolaylı | ✗ | dolaylı | ✗ | ✗ | kısmen | ✗ |
| Barroso & Hölzle | PEER | ✓ (TPC-C) | ✓ (SMP / küme) | ✓ (tpmC) | ✗ | ✗ | kısmen | ✗ | ✗ | ✓ | ✓ |
| Appuswamy 2013 | PEER | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Walker 2009 | PEER | ✗ | ✗ (bulut/sahip) | CPU-saat | kısmen | ✗ | ✗ | kısmen | ✓ (kiralama/satın alma) | ✓ | ✓ |
| Kossmann 2010 | PEER | ✓ (TPC-W) | ✗ (bulut) | ✓ (WIPS) | ✗ | ✗ | ✗ | ✓ (öngörülebilirlik) | ✗ | ✓ | ✓ |
| Hayretci 2021; Brune 2025 | TEZ / PEER | ✓ | ✗ (göç) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | – |
| **Bu proje** | – | ✓ | ✓ | ✓ (oltp_rw, iki tarafta aynı) | ✓ | ✓ (olay tabanlı, M1–M4 / X1–X4) | ✓ | ✓ (20+ aralık, tornado) | ✓ (bölge olarak) | ✓ | ✓ |

**Boşluk ifadesi (tezde kullanılabilecek biçimde).** Mainframe ile kümelenmiş x86 arasında OLTP maliyet karşılaştırması yapan yayımlanmış çalışmalar ya (i) üretici kaynaklı olup varsayımlarını yayımlamıyor, ya (ii) yalnızca donanım ve edinme maliyetini kapsıyor, ya da (iii) kuruluş düzeyinde ve korelasyonel. Bulabildiğimiz kadarıyla hiçbiri iki platformu **aynı işlem birimiyle**, **personel, availability/DR, lisans ve storage dahil tam yığın maliyetle**, **belirsizlik aralıklarıyla** ve **açık, tekrarlanabilir girdilerle** karşılaştırmıyor ve sonucu bir **crossover bölgesi** olarak vermiyor.

**İddianın sınırı.** "Bulabildiğimiz kadarıyla" ifadesi gerekli: tarama sistematik değil (§1), ücretli analist raporları ve kurum içi çalışmalar okunamadı. Bankaların ve danışmanlık firmalarının yayımlanmamış TCO çalışmaları büyük olasılıkla var; boşluk **yayımlanmış ve tekrarlanabilir** çalışma boşluğudur.

---

## 8. Taramadan Modele Çıkan Somut Sonuçlar

Taramanın amacı yalnız kayıt değil; aşağıdakiler model ve tez için önerilen eylemler. Kod yazılmadı; uygulanmaları Adım 6 ve x86 modelinde.

| # | Bulgu | Kaynak | Önerilen eylem | Nereye |
|---|---|---|---|---|
| B1 | Literatürdeki 24–80× çekirdek oranının çoğu kullanım oranı ve çoğaltılmış ortamlardan geliyor | Shedletsky 2008; Eagle 2013 | x86 **hedef kullanım oranını** açık, aralıklı parametre yap (düşük uç %15–20 konsolide edilmemiş, yüksek uç %50–70); tornado'da yerini raporla | x86 parametre listesi (plan §12) |
| B2 | Üretim dışı ortamlar (dev/test, adanmış HA kopyası) IBM'e göre x86'da çok daha büyük | Eagle 2013 | İki tarafta ayrı, aralıklı `NONPROD_FACTOR` ekle; düşük uç 0 (kapsam dışı senaryo). **Emirhan onayladı (2026-11-02)** | Adım 6 / sınırlılıklar |
| B3 | DR payı %3 (z) vs %21 (dağıtık) iddiası | Eagle 2013 | Her topoloji için **DR'ın toplam içindeki payını** çıktı olarak raporla; iddiayla karşılaştır | Karşılaştırma katmanı |
| B4 | 2.200 TPS banka benchmark'ında 2,4× | Shedletsky 2008 | 2.200 TPS'te iki tarafı çalıştırıp oranı dış tutarlılık kontrolü olarak raporla (doğruluk iddiası değil) | Değerlendirme #7 |
| B5 | Barroso: donanım fiyat/performansında küçük sunucu 3–20× önde | Barroso & Hölzle | Maliyet dökümünde x86 donanım avantajının hangi katmanlarda geri alındığını göster (uzlaştırma analizi) | Karşılaştırma katmanı / tez tartışma |
| B6 | $/WIPS'in yük düzeyine göre değişkenliği karar için anlamlı | Kossmann 2010 | TPS ekseni boyunca $/TPS değişkenliğini (testere dişi etkisi) ek çıktı olarak raporla | Karşılaştırma katmanı |
| B7 | USL, ölçeklenme eğrisini çekişme ve tutarlılık olarak ayırıyor | Gunther | K6 sysbench ölçümüne USL uydurmasını ekle; `S(n)` yerine ya da yanında kullan | K6 protokolü (plan §3.8) |
| B8 | Fiyat/performans yılda ~%68 değişmiş | Gray 2005 | `PRICE_EPOCH` kuralının tarihsel gerekçesi olarak tezde an | Plan §12 / tez yöntem |
| B9 | Göç maliyeti ve riski kararlı durum farkını aşabiliyor | Eagle 2013; TSB; Modernization Intel; Brune 2025 | Crossover'ın kararlı durum (greenfield) kararı için geçerli olduğunu yaz; göçün kapsam dışı olduğunu sınırlılıkta tekrar et | Tez sonuç / sınırlılıklar |
| B10 | Uygulama katmanında 4,9× komut farkı iddiası | Shedletsky 2008 | Kapsam asimetrisi tehdidine (plan §14.4) sayısal bir üst tahmin olarak ekle, "bağımsız doğrulaması yok" notuyla | Plan §14.4 / değerlendirme |
| B11 | Personel oranları aynı üreticide bile tutarsız (7,8 sunucu/yönetici 2008; 30,7 sunucu/FTE 2011) | Shedletsky 2008; IBM Eagle labor | x86 personel aralığını bu iki uç arasında geniş tut; tutarsızlığı tezde açıkça raporla | x86 personel (plan §10) |
| B12 | z/OS beceri açığı (%70) | Kyndryl 2025 | Mainframe ücret aralığının yüksek ucunun bu kıtlığı temsil ettiğini belgeye bağla | v3 §7.7 (bir sonraki güncellemede) |

---

## 9. Yeni Geçerlilik Tehditleri

- **9.1. Yayın yanlılığı.** Mainframe ile dağıtık sistemi sayıyla karşılaştıran neredeyse tüm yayımlanmış çalışmalar IBM kaynaklı. Bağımsız ya da karşı taraftan nicel bir karşılaştırma bulunamadı. Bu, dış tutarlılık kontrollerimizin (B3, B4) tek yönlü bir referansla yapılacağı anlamına gelir. Önlem: IBM rakamlarını "doğru cevap" değil, "üretici iddiası" olarak raporlamak; Barroso & Hölzle gibi ters yöndeki akademik bulguyu yan yana koymak.
- **9.2. Tarama sistematik değil.** Akademik veritabanı API'lerine erişilemedi; ücretli raporlar okunamadı. Boşluk iddiası "bulabildiğimiz kadarıyla" biçiminde yazılmalı.
- **9.3. Kapsam ile justification arasındaki gerilim.** `project_justification.md` §5.2 "gerçek sistem kurulumu ve benchmark koşturma"yı kapsam dışı sayıyor; Emirhan K6'da kendi sysbench ölçümümüzü onayladı. Orijinal tasarım dokümanı düzenlenmeyeceği için bu değişiklik log'da ve güncel x86 model dokümanında kayda geçirilmeli: araç hâlâ analitik bir modeldir, K6 ölçümü yalnızca bir kalibrasyon girdisidir.
- **9.4. Eski veriler.** Doğrudan paralel çalışmaların çoğu 2008–2013 donanımına ait (z10/z196, Westmere/Sandy Bridge). Sayıları model parametresi olarak değil, yalnız büyüklük mertebesi kontrolü olarak kullanmak gerekir.

---

## 10. Kaynaklar

### 10.1. Kullanılan kaynaklar ve bu dokümandaki yerleri

- [ANON-1985] Anon et al. (J. Gray ve diğerleri), "A Measure of Transaction Processing Power", *Datamation*, 1985; Microsoft Research teknik raporu olarak yeniden yayımlandı. (§2.1) [PEER]
- [GRAY-2005] J. Gray, "A Measure of Transaction Processing Power" üzerine 20 yıl sonrası değerlendirmesi, Microsoft Research, 2005. (§2.2) (yıllık %68 rakamı ikincil özetten; doğrulanmalı)
- [TPC-PRICING] TPC Pricing Specification v2.9.0 — https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp (§2.3)
- [POESS-2008] M. Poess, R. Nambiar, "Energy Cost, the Key Challenge of Today's Data Centers: A Power Consumption Analysis of TPC-C Results", PVLDB 1(2), 2008 — https://bibtex.github.io/VLDB-2008-PoessN.html (§2.4) [PEER]
- [IBM-SHEDLETSKY-2008] J. Shedletsky, IBM, "Mainframe versus Distributed TCO Studies and Experiences" — https://public.dhe.ibm.com/software/zseries/pdf/sandiego/Mainframe_versus_Distributed_TCO_Studies_and_Experiences_-_John_Shedletsky.pdf (§3.1, §3.3) [VENDOR]
- [IBM-EAGLE-2013] IBM CPO, "TCO Lessons Learned From Customer Engagements" v4, 2013 — https://public.dhe.ibm.com/software/os/systemz/pdf/TCO_lessons_from_customer_engagements_v4.pdf (§3.2, §3.3) [VENDOR]
- [IBM-EAGLE-2012] IBM, "Tales from the Eagle TCO team", 2012 (x86 planında zaten kaynak; DR testi saatleri) [VENDOR]
- [RUBIN-2012] Rubin Worldwide, "The Real Cost of Mainframe vs Distributed", 2012 (§3.4) [ANKET, üretici bağlantılı]
- [IDC-2020] IDC, IBM z14 yükseltmesi iş değeri çalışması, 2020 (§3.5) [ANKET, IBM sponsorlu]
- [KYNDRYL-2025] Kyndryl, State of Mainframe Modernization Survey, 2025 (§3.6) [ANKET]
- [BMC-2024] BMC, Mainframe Survey, 2024 (§3.6) [ANKET]
- [STONEBRAKER-1986] M. Stonebraker, "The Case for Shared Nothing", *IEEE Database Engineering Bulletin* 9(1), 1986 (§4.1) [PEER]
- [BARROSO] L. A. Barroso, J. Clidaras, U. Hölzle, *The Datacenter as a Computer*, Morgan & Claypool, 2. baskı 2013 / 3. baskı 2018, Bölüm 3 ve 6 — özet: https://dirtysalt.github.io/html/the-datacenter-as-a-computer.html (§4.2) [PEER, kitap; sayılar ikincil özetten, birincil metinle doğrulanmalı]
- [APPUSWAMY-2013] R. Appuswamy et al., "Scale-up vs Scale-out for Hadoop: Time to Rethink?", ACM SoCC 2013 (§4.3) [PEER]
- [GUNTHER-USL] N. Gunther, Universal Scalability Law; PostgreSQL 9.1 uygulaması (§4.4)
- [WALKER-2009] E. Walker, "The Real Cost of a CPU Hour", *IEEE Computer* 42(4):35–41, 2009, doi:10.1109/MC.2009.135 (§5.1) [PEER]
- [KOSSMANN-2010] D. Kossmann, T. Kraska, S. Loesing, "An Evaluation of Alternative Architectures for Transaction Processing in the Cloud", ACM SIGMOD 2010 — https://cs.brown.edu/people/tkraska/pub/sigmod10-cloudbench.pdf (§5.2) [PEER]
- [KHAJEH-2011] A. Khajeh-Hosseini et al., bulut göçü maliyet modelleme, arXiv:1105.0149 (§5.3) [PEER ön baskı]
- [KHADKA-2014] R. Khadka et al., "How Do Professionals Perceive Legacy Systems and Software Modernization?", ICSE 2014 (§6.1) [PEER]
- [HAYRETCI-2021] H. E. Hayretci, "Comparative Analysis of Case Studies on Legacy System Migration in Banking Industry", Yüksek Lisans Tezi, Boğaziçi Üniversitesi, 2021 — https://digitalarchive.library.bogazici.edu.tr/items/79e70d59-3bf7-4b36-8be2-a029880a191b (§6.2) [TEZ]
- [BRUNE-2025] P. Brune, K. Helbig, "Managed Evolution of a Legacy Core Banking System: Case Study from a European Bank", itAIS 2025 — https://publications.hnu.de/5954/ (§6.3) [PEER]
- [TSB-2018] PRA ve FCA, TSB Bank plc nihai bildirimleri, 2022 (2018 göç olayı) (§6.4) [RESMİ]
- [MODINTEL-2025] Modernization Intel, Mainframe Migration Challenges, 2025 — `project_justification.md` kaynak listesinde (§6.5) [ANKET]

### 10.2. İncelenip alınmayan kaynaklar

| Kaynak | Neden alınmadı |
|---|---|
| Kalohia, IJRASET 2024 (mainframe ile bulut karşılaştırması) | Sayılar kaynaksız; hakem süreci belirsiz bir dergi |
| IJLRP 2024, "Running Linux on IBM Z" | Linux on Z konsolidasyonu; bizim kapsamımız z/OS üzerinde OLTP, x86 karşılaştırması yok |
| Sunline 2020 (Çin dağıtık çekirdek bankacılık) | Zaman çizelgesi var, maliyet ya da performans sayısı yok |
| Arcati 2024 Strategy Paper, Planet Mainframe yazıları | Mainframe topluluğu yayını; IBM TCO iddialarını kaynak göstermeden aktarıyor |
| Göç firmalarının (rehosting) ROI blogları | Sayılar kaynaksız ve satış amaçlı; karşılaştırılabilir yöntem yok |
| Capgemini 2024, Accenture anketi | `project_justification.md`'de motivasyon olarak zaten var; bu taramaya yeni bulgu eklemiyor |
| IBM "Fresh look at mainframe TCO", "What's wrong with offloading" seminer notları | Eagle 2013 ile aynı vaka havuzu; tekrar |
