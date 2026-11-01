# Değerlendirme #2: Mainframe modelinin uçtan uca incelemesi

> **Değerlendirme #2** · Tarih: 2026-10-31 · Kapsam: yalnızca mainframe tarafı (`src/mainframe_model.py` ve `docs/mainframe_model_documentation_v2.md`), Oturum 1 düzeltmelerinden sonraki hali.
> Önceki değerlendirme: #1 (`2026-10-31_degerlendirme_01.md`). Bu doküman #1'deki 2.2 (crossover hipotezi) ve 2.3 (fiyat kaynakları) maddelerini mainframe özelinde derinleştirir. #1'deki hiçbir tehdit henüz kapanmadı.
> Rakamlar kodu çalıştırarak üretildi. Kendi bilgime dayanan ama kaynakla teyit etmediğim iddialar **(doğrulanmalı)** diye işaretli.

## 0. Özet

Mainframe modeli mimari olarak sağlam: doğru mekanizmalar (LSPR, MSU, R4HA, CoD, M1–M4) yerinde. Ama üç tür eksik var:

1. **Yeni bulunan bir hesap hatası.** Kapasite köprüsü n-way sublinearitesini iki kez sayıyor. Model, z16 kademelerinin TPS'ini yaklaşık **%29 eksik** hesaplıyor ve kendi kalibrasyon noktasını yeniden üretemiyor (Bölüm 1.1). Bu, mainframe'i olduğundan pahalı gösteriyor ve her kararı etkiliyor. İlk düzeltilmesi gereken bu.
2. **Maliyet eğrisini şekillendiren yapılar eksik.** Doğrusal donanım fiyatı, tek bir $/MSU, zIIP ve CBU'nun olmaması. Değerlendirme #1'deki ikinci problem (düz maliyet/TPS eğrisi) tam olarak bunlardan kaynaklanıyor (Bölüm 3).
3. **TCO kalemleri ve girdiler eksik.** CICS, Db2, storage, GDPS, personel ve 8 girdiden 4'ü.

Önerim: mainframe'i aşağıdaki sırayla, her adımı test ve log'la kapatarak tamamlamak (Bölüm 7). Transaction köprüsünün mainframe tarafındaki yarısı (REDP-5320'nin iş yükü tanımı) bu sürecin içinde yapılabilir. Mainframe'in "1 TPS"i neyi temsil ediyor, sorusu zaten mainframe'in tamamlanmasının bir parçası.

## 1. Kapasite ve throughput

### 1.1. Sublinearite iki kez sayılıyor (hata, kritik)

Model bir kademenin ham TPS'ini `cp_equivalents(tier) × BASE_TPS_PER_CP × RNI` olarak hesaplıyor:

- `BASE_TPS_PER_CP` ≈ 12.909, benchmark TPS'inin **fiziksel CP sayısına** bölünmesiyle elde ediliyor. 18/26-way'deki koordinasyon kaybı bu sayının içinde zaten var.
- `cp_equivalents` = LSPR / 4,02. LSPR oranı da n-way kaybını **ayrıca** içeriyor (18 CP'lik 3931-718 yalnızca 13,45 "tam-hız CP eşdeğeri" sayılıyor).

Sonuç olarak kayıp iki kez uygulanıyor. Model kendi çapasını yeniden üretemiyor:

| Kademe | Modelin hesabı | Köprünün amaçladığı (z13 TPS × z16/z13 oranı) | Fark |
|---|---|---|---|
| 3931-718 | 173.600 TPS | ~244.000 TPS | −%29 |
| 3931-726 | 234.000 TPS | ~319.000 TPS | −%27 |
| 3931-732 | 279.000 TPS | ~392.000 TPS | −%29 |

**Önerilen düzeltme:** LSPR zaten tüm nesilleri aynı baza (z9 2094-701 = 1,00) göre veriyor. Bu yüzden en temiz köprü **LSPR birimi başına TPS**:

TPS_per_LSPR = 174.000 / 38,55 (z13 718) ≈ 4.514  ·  227.000 / 51,89 (z13 726) ≈ 4.375  ·  ortalama ≈ 4.444

Kademe TPS'i = LSPR × 4.444 × RNI çarpanı. Bu formül 3931-718 için ~240K ve 3931-726 için ~324K veriyor, yani köprünün amaçladığı değerlerle %2 içinde.

Bu yaklaşım "MIPS nesiller arası normalize değil" itirazına da takılmıyor. Kullanılan şey MIPS değil, IBM'in nesiller arası ölçtüğü LSPR oranının kendisi. Bu da CP-güç köprüsünün asıl niyetinin daha doğrudan bir ifadesi.

**Akademik not:** LSPR oranları IBM'in kendi iş yükü karışımında ölçülüyor. CICS/Db2 OLTP'nin LSPR karışımına ne kadar benzediği bir varsayım; tezde açıkça belirtilmeli.

**Etki:** Düzeltme sonrası aynı TPS için daha küçük kademeler seçilecek ve mainframe maliyeti kabaca %20–30 düşecek. Değerlendirme #1'deki $2/TPS/ay rakamı ve log'daki CoD rakamları yeniden hesaplanmalı.

### 1.2. Kademe tablosu eksik ve tek frame tavanı yapay olabilir (yüksek)

- Modelde 28 kademe var. Dokümanlar "128 kademe = 4 seri × 32 CP" diyor.
- Benim bilgime göre z16 A01'de 7xx serisi 32 CP'nin çok üstüne çıkıyor (yüzlerce PU destekleniyor), alt-kapasite serileri ise daha düşük bir CP sayısında sınırlanıyor (doğrulanmalı). Doğruysa hem "128" sayısı hem de modelin ~250K TPS'lik tek frame tavanı, tablonun 32 CP'de kesilmesinden kaynaklanan **yapay bir sınır**. Bu sınır yüzünden şu an yüksek TPS'li senaryolar infeasible çıkıyor.
- Küçük yükler için z16 A02 / rack-mount modeller de var (doğrulanmalı). Bunlar düşük TPS bölgesinde mainframe'in taban maliyetini belirler ve crossover açısından kritik.
- **Yapılacak:** Resmî LSPR tablosundan z16 A01 ve A02'nin bütün kademelerini almak. Tabloyu koda gömmek yerine ayrı bir CSV veri dosyasında tutmak, böylece kaynakla satır satır karşılaştırılabilir.

### 1.3. MSU/MIPS oranı sabit varsayılıyor (orta)

`MSU_PER_MIPS` = 0,1225, tek bir modelden (3931-604) alınıp bütün kademelere uygulanıyor. IBM her model için ayrı bir MSU değeri yayımlıyor (doğrulanmalı) ve yüksek n-way'de MIPS başına MSU genellikle düşüyor ("technology dividend"). Yazılım faturası doğrudan MSU olduğu için bu oranın kademeye göre değişmesi maliyet eğrisini **içbükey** yapar. Bu da tam olarak crossover sorusunu ilgilendiren bir şekil etkisi. **Yapılacak:** Kademe tablosuna her model için resmî MSU sütunu eklemek.

### 1.4. RNI çarpanları kalibre edilebilir (orta, kolay)

low = 1,25 ve high = 0,70 şu an [ASSUME]. LSPR tablosu Low/Average/High RNI sütunlarını ayrı ayrı yayımlıyor. Bu sütunlar köprüye doğrudan girebilir; o zaman çarpan sabit olmaktan çıkar ve kademeye göre değişir. Bu, az eforla bir [ASSUME]'u kaldırır.

### 1.5. Tek benchmark çapası ve transaction tanımı (kritik, köprü işinin mainframe yarısı)

Tüm throughput tek bir rapora dayanıyor: REDP-5320, z13, CICS TS 5.3. Modelde bu benchmark'ın transaction'ının ne olduğu yazmıyor (Db2 çağrısı sayısı, transaction başına CPU süresi, I/O, veri boyutu). Bu bilgi:

- transaction köprüsünün mainframe tarafındaki tanımıdır,
- latency modelindeki E[X]'in gerçekçiliğini kontrol etmeyi sağlar,
- IOPS_PER_TX varsayımını kalibre etmeye yarayabilir.

**Yapılacak:** REDP-5320'nin iş yükü bölümünü okuyup transaction profilini çıkarmak. Varsa ikinci bir CICS/Db2 benchmark'ıyla (daha yeni bir nesil ya da CICS sürümü) çapraz kontrol yapmak.

## 2. Latency

Oturum 1'de düzeltildi (per-CP M/M/1 + D_io). Kalanlar:

- D_io parametreleri (0,3 ms ve tüm I/O'nun senkron sayılması) [ASSUME]. REDP-5320'nin ölçtüğü yanıt süreleri varsa D_io + R_cpu bunlarla kıyaslanarak kalibre edilebilir.
- 1.1 düzeltilince E[X] değişecek (CP başına hız artacak). Latency testleri yeniden çalıştırılmalı.
- Clustered tarafla aynı kuyruk ailesinin kullanılması kararı hâlâ açık.

## 3. Maliyet modeli: ikinci problemin kaynağı

Değerlendirme #1'deki düz maliyet/TPS eğrisinin sebepleri ve çözümleri:

| Mevcut | Neden yanlış ya da eksik | Önerilen yapı |
|---|---|---|
| Donanım = MIPS × $200 (doğrusal) | Gerçek fiyatın büyük bir sabit kısmı var (frame, I/O drawer'lar, kurulum). Küçük yüklerde mainframe'in pahalılığı bu sabitten gelir. | Taban (frame/model) + kapasite başına artış. Kaynak: birden çok bağımsız fiyat noktası. |
| Yazılım = tek $40/MSU | IBM MLC (VWLC/AWLC) ürün başına ve MSU kademeleriyle azalan birim fiyatla fiyatlanıyor (doğrulanmalı). z/OS, CICS ve Db2 ayrı faturalanır. | Ürün başına kademeli fiyat tablosu: z/OS + CICS + Db2. |
| zIIP yok | Db2'nin uygun iş yükü, Java ve bazı DRDA işleri zIIP'e kayar; zIIP kapasitesi MLC faturasına girmez (doğrulanmalı). Yazılım maliyetini önemli ölçüde düşürebilir. | zIIP'e kayan oran [ASSUME] aralık; zIIP donanım fiyatı ayrı. |
| DR frame'i tam maliyet | IBM'in CBU (Capacity BackUp) kayıtları, DR sitesindeki frame'in düşük kalıcı kapasiteyle kurulup felakette etkinleştirilmesini sağlıyor (doğrulanmalı). M2–M4'te ikinci frame'i tam fiyatla saymak gerçekçi değil, tutucu ama abartılı. | İkinci frame = küçük kalıcı kademe + CBU ücreti. CoD'nin DR karşılığı. |
| R4HA, CPC toplamı üzerinden | Gerçekte R4HA LPAR bazında hesaplanır; birden çok LPAR'ın tepeleri farklı saatlerde olabilir. | Faz 1 için kabul edilebilir basitleştirme; dokümanda belirtilmeli. |
| Tailored Fit Pricing yok | IBM'in yeni fiyatlama modeli, R4HA yerine toplam tüketime dayanıyor. | Kapsam dışı bırakılabilir, ama bir cümleyle gerekçelendirilmeli. |
| GDPS = %15 / %30 yazılım primi | Gömülü çarpan; GDPS ayrı bir hizmet/lisans. | Ayrı kalem, [ASSUME] aralık. |
| Enerji 30 kW, $0,12 | Kaynak bir satın alma rehberi. | IBM z16 IMPP belgesinden resmî güç değeri. |

Bu tabloda **ilk iki satır ve CBU** maliyet eğrisinin şeklini belirliyor. Sabit taban ve azalan MLC birim fiyatı mainframe'e ölçek ekonomisi verir. Clustered tarafın daha doğrusal maliyetiyle birlikte crossover'ı üreten de bu yapı olur. Yani ikinci problemin çözümü bu üç maddede.

## 4. Availability

- **M4 kaynak etiketleri ters:** hw_low [REDBOOK], hw_high [ITIC] etiketli; diğer topolojilerde tersi. Değerler de muhtemelen yer değiştirmiş. Redbook'un ilgili tablosuyla düzeltilmeli.
- **M3 ve M4 aynı:** effective low değerleri aynı (%99,99999). Bu yüzden M4 hiçbir senaryoda seçilmiyor. M4'ü ayıran şey RTO/RPO (dakikalar, sıfıra yakın RPO). Bu girdiler bağlanmadan M4'ün modelde bir anlamı yok.
- **RPO/RTO bağlı değil:** Redbook her model için RTO/RPO veriyor. Topoloji eleme availability'nin yanında RPO ve RTO'yu da kullanmalı.
- **×10 planlı kesinti kuralı** tek bir sözlük sayfasına dayanıyor. Ya daha güçlü bir kaynak bulunmalı ya da [ASSUME] aralık (%70–90) olarak duyarlılığa girmeli.
- **ITIC rakamları:** "9 nine" bir anket öz-beyanı. "Bağımsız alt sınır" olarak kullanmadan önce ITIC'in yöntemi (yalnızca donanım arızası mı, hangi örneklem) dokümanda açıkça yazılmalı.

## 5. Yıllık simülasyon

- **Peak günler yıla eşit aralıklarla dağıtılıyor.** Gerçekte perakendede tepeler kasım-aralıkta, bankacılıkta ay sonlarında toplanır. Bu dağılım R4HA'yı ve CoD'yi doğrudan etkiler; aylara göre kümelenmiş bir dağılım seçeneği eklenmeli.
- **Aylar 730 saat sayılıyor.** Takvim ayları değil; küçük bir etki, belgelenmeli.
- **Tek yıl.** Veri ve TPS büyümesi ve amortisman için 5 yıllık ufuk gerekiyor (#1, 2.6).
- **CoD:** 2,5 çarpanı ve base için "≥ ortalamanın %120'si" eşiği [ASSUME]. CoD'nin gün bazlı faturalanması (24 saatlik pencere) doğru modellenmiş.
- **Profil sentetik.** Sonuçlar preset'lere duyarlı. Mümkünse gerçek bir OLTP trafik profiliyle (yayımlanmış bir veri seti) bir kontrol yapılmalı.

## 6. Eksik TCO kalemleri ve girdiler

| Kalem | Durum | Not |
|---|---|---|
| z/OS MLC | Var (tek fiyat) | Kademeli tabloya geçmeli (3) |
| CICS TS MLC | Yok | Ayrı ürün, MSU bazlı |
| Db2 for z/OS MLC | Yok | Ayrı ürün; zIIP etkisi burada büyük |
| DS8900F storage | Yok | data_volume_tb, data_growth_pct ve RNI'dan IOPS buraya bağlanır |
| GDPS | Çarpan olarak gömülü | Ayrı kalem |
| Personel | Yok | Sysprog, DBA, kapasite planlamacı; iki tarafta aynı maaş kaynağı |
| Tesis (alan, soğutma) | Yok | İki tarafa eşit uygulanmalı ya da iki taraftan da dışarıda bırakılmalı |
| Girdiler | 4/8 bağlı | data_volume_tb, data_growth_pct, rpo_seconds, rto_minutes bağlı değil |

## 7. Önerilen yol haritası (mainframe'i tamamlamak için)

Her adım: kod + test + doküman güncellemesi + log girdisi. Sıra, etki ve bağımlılığa göre:

| Adım | İş | Neden bu sırada | Kaynak ihtiyacı |
|---|---|---|---|
| M1 | Kapasite köprüsü düzeltmesi (1.1): LSPR başına TPS | Hata; her sonraki rakamı etkiliyor | Yok, mevcut veri yeterli |
| M2 | Tam kademe tablosu (A01 + A02) + model başına MSU + LSPR RNI sütunları, ayrı CSV dosyasında (1.2–1.4) | Kapasite tavanı ve MSU eğrisi buna bağlı | Resmî LSPR tablosu, IBM MSU değerleri |
| M3 | REDP-5320 iş yükü profili (1.5) | Köprünün mainframe yarısı; D_io kalibrasyonu | REDP-5320 |
| M4 | Maliyet yapısı: donanım taban + artış, ürün başına kademeli MLC (z/OS, CICS, Db2), zIIP (3) | İkinci problemi çözen adım | IBM MLC fiyat duyuruları, bağımsız donanım fiyat noktaları |
| M5 | Availability: RPO/RTO bağlama, M4 düzeltmesi, CBU ile DR frame (4, 3) | Topoloji seçimini gerçekçi yapar | Redbook SG24-8446, CBU belgeleri |
| M6 | DS8900F storage (6) | 2 girdiyi daha bağlar | DS8900F Redbook'ları, fiyat aralıkları |
| M7 | Personel ve GDPS ayrı kalem (6) | TCO'nun büyük kalemi | Maaş kaynağı, FTE oranları |
| M8 | 5 yıllık ufuk + NPV + kümelenmiş peak dağılımı (5) | Büyüme girdilerini anlamlı yapar | — |

M1 hemen yapılabilir. M2–M4 kaynak gerektiriyor ama birbirinden bağımsız aranabilir. M4 bittiğinde maliyet eğrisi yeniden çizilir ve "mainframe tarafında ölçek ekonomisi var mı?" sorusu ilk kez gerçek verilerle cevaplanır. Bu, crossover hipotezinin yeniden yazılması için ihtiyaç duyulan ara sonuç.

## 8. Bu değerlendirmede kapanan / açılan tehditler

- **Yeni açılan:** 1.1 (kapasite çift sayımı), 1.2 (yapay tek frame tavanı), 3 (zIIP, CBU).
- **#1'den derinleştirilen:** 2.2 crossover, 2.3 fiyat kaynakları, 2.4 availability.
- **Kapanan:** yok.
