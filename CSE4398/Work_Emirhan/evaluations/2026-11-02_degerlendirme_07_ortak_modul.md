# Değerlendirme #7: Ortak modül, iki fiyat modu ve üretim dışı ortamlar

> **Değerlendirme #7** · Tarih: 2026-11-02 · Kapsam: Adım 6.
> - İki platformun paylaştığı parametre ve kuralların `src/common_model.py`'ye taşınması.
> - İki fiyat modu (kaynaklı fiyat seti / kullanıcı fiyat dosyası).
> - Üretim dışı ortamlar kalemi (`NONPROD_FACTOR`).
> - Bunların mainframe sonuçlarına etkisi.
>
> Önceki değerlendirme: #6 (`2026-11-02_degerlendirme_06_yedek_ve_npv.md`). Kapanan ve açık kalan maddeler Bölüm 5'te.
>
> Yöntem:
> - Taşıma, taşımadan önce üretilen bir altın sonuç kümesine karşı regresyon testiyle doğrulandı.
> - Yeni kalem önce tutarlılık koşullarına bağlandı (NPV = 60 × statik, yıllık = 12 × statik), sonra etkisi ayrı ölçüldü.
> - Sayılar `src/tools/range_curve.py`, `npv_sensitivity.py` ve doğrudan model çağrılarından yeniden üretildi.
> - Varsayılanlar: oltp_rw, %99,9, 20 TB veri; NPV'de %10 TPS büyümesi ve %7 iskonto.

---

## 0. Özet

1. **Taşıma sonuçları değiştirmedi.** Ortak parametreler (saha olayları, ücretler, enerji, NPV kuralları, nesne depolama ve bulut yedek fiyatları) ortak modüle taşındı. Altın kümenin bütün değerleri 0 farkla yeniden üretildi.
   - Altın küme: 7 statik durum, iki TPS'te aralık köşeleri, 9 yıllık strateji, 3 NPV ölçüsü.
2. **Ortak modül yalnızca bir dosya ayrımı değil, bir sözleşmedir.**
   - Her parametrenin tek sahibi var; iki modülde birden tanımlı bir ad test hatasıdır.
   - Storage fiyatları ham TB'a çevrilir.
   - Emtia bileşen fiyatları dönem tablosundan gelir.
   - Elle geçişin karar süresi iki tarafta aynıdır.
   - Üretim dışı ortamlar aynı kalemlere uygulanır.
3. **Üretim dışı ortamlar 10K TPS'te başlık sonucunu %10 yükseltti:** $84,62 → $93,10/TPS/ay.
   - Aralık $27,06 / $84,62 / $338,09 iken $27,06 / $93,10 / $411,28 oldu.
   - NPV $50,60M iken $55,68M oldu; seviyelendirilmiş maliyet $85,31 iken $93,89 oldu.
   - Kademe, topoloji ve tek yıllık strateji seçimleri değişmedi.
4. **Personel tornado'da ikiye ayrıldı:** ekip büyüklüğü ve ücret. AWLC fiyat seviyesi ile okuma SQL CPU'su en üste çıktı. İki personel satırı birlikte hâlâ en büyük kalemdir.
5. **Bir koşullu sonuç çevrildi.** 5 yıllık NPV'de TFP büyüme indirimi kaldırıldığında steady_oltp'de C (TFP) %0,2 öndeydi; şimdi B (CoD) %0,3 önde. Strateji sonucunun ne kadar ince bir farka dayandığını gösterir.
6. **İki fiyat modu çalışıyor.** Kullanıcı gerçek tekliflerini kısmi bir JSON dosyasıyla verebilir. Verilen fiyatlar aralıktan çıkarılır, aralık daralır.
7. **Testler:** 23 testten 30'a çıktı, hepsi geçiyor. Bütün duyarlılık araçları yeni kodla çalışıyor.

---

## 1. Doğrulama

### 1.1. Taşımanın sonuçları korumasının kanıtı

| Adım | Ne yapıldı |
|---|---|
| Önce | Mevcut kodla `src/tools/golden_snapshot.py --write` çalıştırıldı → `data/test/golden_step5.json` |
| Taşıma | Ortak parametreler `common_model.py`'ye taşındı, mainframe'deki kopyaları silindi, bütün okumalar `cm.X`'e çevrildi |
| Sonra | `test_common_module_preserves_results`, `NONPROD_FACTOR` 0'da ve aralıkta sabitken altın kümeyi yeniden üretir; 10⁻⁹ göreli fark ister |
| Sonuç | **0 fark** |

Bu yöntem, yazılım mühendisliğindeki "karakterizasyon testi" ile aynı fikirdir. Davranış önce dondurulur, sonra yapı değiştirilir. Tezde model doğrulama başlığı altında bir cümleyle anılmalıdır: "Ortak modüle taşıma, taşıma öncesi sonuçlara karşı regresyon testiyle doğrulandı; fark 0."

### 1.2. Yeni kalemin tutarlılığı

- **Statik ile NPV:** r = 0, büyüme 0, artışlar 0 iken statik NPV = 60 × statik aylık toplam. Fark 10⁻¹⁶ mertebesinde ve üretim dışı kalem dahil. NPV'deki üretim dışı kalem 60 × statik aylık kalemine de eşit ($5.064.552).
- **Yıllık ile NPV:** Aynı koşulda yıllık NPV = 5 × yıllık toplam. Üç stratejide (Permanent, CoD, TFP) ve retail_bursty'de de geçerli; fark 10⁻¹⁶.
- **Düz yük:** Düz yükte yıllık Permanent = 12 × statik. Üretim dışı kalem de binde bir içinde eşit.
- **Doğrusallık ve kapsam:** Çarpanla doğrusal: 0,4'teki kalem, 0,2'dekinin tam iki katı. GDPS, personel, yedek ve yazılım kalemlerini değiştirmez; DR ve GDPS tabana girmez.

### 1.3. Araçlar

`availability_sensitivity`, `npv_sensitivity`, `pricing_sensitivity`, `range_curve` (oltp_rw ve redp_light), `software_sensitivity`, `storage_sensitivity` ve `workload_sensitivity` yeni kodla hatasız çalışıyor. Taşınan adlar eski araçlarda `m.X` olarak okunmaya devam ediyor (modül düzeyi `__getattr__`).

---

## 2. Bulgular

### 2.1. Üretim dışı ortamlar: büyüklüğü ve şekli

| TPS | Önce ($/TPS/ay, mid) | Sonra | Kalemin payı |
|---|---|---|---|
| 1.000 | 221,73 | 247,41 | %10,4 |
| 10.000 | 84,62 | 93,10 | %9,1 |
| 50.000 | 48,63 | 53,25 | %8,7 |
| 150.000 | 37,96 | 41,89 | %9,4 |

- **Eğrinin şeklini değiştirmez.** Pay bütün hacimlerde %9–11'dir. Kalem birincil sitenin maliyetine orantılı eklendiği için eğrinin bükülmesi ve düşük TPS'teki yüksek maliyet aynen korunur.
- **Topolojiler arası farkı daraltır.** %99,999'da (M4) kalem yine $84.825'tir, çünkü DR ve GDPS tabana girmez. Payı %7'ye düşer. Üretim dışı ortamların felaket kurtarma kapsamında olmadığı varsayımının doğrudan sonucudur.
- **Aralığın üst ucunu açar, alt ucunu değiştirmez.** low'da çarpan 0'dır ("kapsam dışı" senaryo). high'da çarpan 0,50'dir ve uygulandığı taban (yazılım, donanım) da büyüktür. Bu yüzden high %21,6 yükselir.

**Akademik anlamı.** Bu kalem asıl olarak x86 tarafı için önemlidir. IBM'in iddiasına göre dağıtıkta üretim dışı ortamlar üretimin ~2 katıdır. Mainframe'de %20'lik bir çarpan başlık sonucunu %10 değiştirdi. x86'da 2,0'lık bir çarpan ise birincil site maliyetinin üç katı demektir. Bu, crossover'ın yerini benzer çalışmalar taramasında bulunan kullanım oranından sonra en çok oynatabilecek ikinci kalem olabilir. Tezde iki senaryo yan yana raporlanmalıdır: kapsam dışı (iki çarpan 0) ve mid.

### 2.2. Personel iki boyuta ayrıldı

Adım 6'dan önce `STAFF_SCENARIO` hem FTE eğrisini hem ücreti birlikte seçiyordu. Şimdi `WAGE_LEVEL` ortak ve ayrı bir parametredir. 10K TPS tornado'su:

| Sıra | Önce | Sonra |
|---|---|---|
| 1 | Personel (eğri + ücret) $608K–$1,33M | AWLC fiyat seviyesi $727K–$1,24M |
| 2 | AWLC fiyat seviyesi | Okuma SQL CPU $770K–$1,22M |
| 3 | Okuma SQL CPU | Personel eğrisi + taban $751K–$1,19M |
| 4 | Yazma SQL CPU | Yazma SQL CPU |
| 5 | zIIP payı | Ücret seviyesi $828K–$1,07M |
| 6 | | Üretim dışı ortamlar $846K–$1,06M |

Köşe senaryolarında ikisi aynı yöne çekildiği için low/mid/high toplamları değişmedi. Ayrımın getirisi şudur: karşılaştırma katmanında ücret iki tarafa aynı değerle uygulanacak ve büyük ölçüde birbirini götürecek. Tarafları ayıran personel belirsizliği ise ekip büyüklüğüdür (FTE eğrisi). Tez bu ayrımı "personel maliyeti belirsiz" demek yerine "ekip büyüklüğü belirsiz, ücret ortak" diye kurabilir.

### 2.3. Strateji sonucu ince bir farka dayanıyor

5 yıllık NPV, TFP büyüme indirimi kaldırıldığında (büyüme fiyatı = taban fiyatı):

| Preset | Adım 6 öncesi | Adım 6 sonrası |
|---|---|---|
| steady_oltp | C 67,603 / B 67,710 (C %0,2 önde) | **B** 73,991 / C 74,211 (B %0,3 önde) |
| retail_bursty | B önde | B önde |
| batch_heavy | B önde | B önde |

Üretim dışı kalem yazılım faturasıyla orantılıdır. TFP'nin indirimsiz yazılım faturası CoD'ninkinden biraz büyük olduğu için bu küçük farkı çevirdi. Varsayılan durumda (büyüme indirimi 0,5) TFP üç presette de kazanmaya devam ediyor. **Sonuç:** Değerlendirme #6'nın "strateji sonucu koşullu yazılmalı" önerisi güçlendi. Tezde "TFP, büyüme indirimi altında kazanır; indirimsiz durumda CoD ile fark %1'in altındadır ve kazanan, maliyet tabanındaki küçük değişikliklere duyarlıdır" denmelidir.

### 2.4. Fiyat yaşları görünür hale geldi

`--price-vintages` mainframe fiyatlarının kaynak yıllarını listeler:

- En eskiler 2004 (AWLC taban ücreti ve seviyesi) ve 2006 (TS7700 küme tabanı).
- Çoğu 2022 (z16 ve DS8900F dönemi).
- Ortak fiyatlar 2024–2026 (nesne depolama, S3, Direct Connect, ücretler).

x86 tarafının bileşen fiyatları 2025–2026 tarihli olacak. Bu yaş farkı şimdiye kadar dokümanlarda dağınık duruyordu; artık tek bir listede. 2004 AWLC'nin otomatik TÜFE ile güncellenmemesi bilinçli bir karardır: bu dönüşüm `SW_PRICE_LEVEL_FACTOR` aralığının (0,5–1,75) işidir.

### 2.5. İki fiyat modu aracın kullanım biçimini değiştiriyor

Şimdiye kadar araç yalnızca kaynaklı fiyatlarla, geniş aralıklarla çalışıyordu. Kullanıcı fiyat dosyasıyla bir kurum elindeki teklifleri verebilir. Verilen fiyatlar aralıktan çıkarıldığı için aralık, kurumun gerçekten bilmediği şeylere daralır. Örnek: donanım fiyatı, ücret ve GDPS verilince tornado'dan üç satır düşer.

**Akademik anlamı.** Projenin "kurumun kendi girdileriyle çalışan şeffaf araç" iddiasını (`project_justification.md` §2.3) doğrudan destekler. Literatürdeki üretici TCO çalışmalarının (IBM Eagle) en büyük zayıflığı girdilerinin yayımlanmamasıydı (benzer_calismalar_v1 §3). Bu araçta girdiler hem kaynaklı olarak yayımlanır hem de kullanıcı tarafından değiştirilebilir.

---

## 3. Geçerlilik tehditleri (yeni)

| # | Tehdit | Etki | Ele alınışı |
|---|---|---|---|
| 3.1 | Üretim dışı çarpanın tek kaynağı üretici (IBM Eagle) | 10K'da başlık ±%10 (0 ile 0,50 arası: $84,62–$105,82) | Aralık parametresi, low = kapsam dışı. Bağımsız kaynak aranacak |
| 3.2 | "Kapasite eşdeğeri" varsayımı: üretim dışı kapasite üretimle aynı birim fiyattan | Mainframe'de AWLC'nin marjinal kademe fiyatı ve IBM'in geliştirme/test teklifleri yok sayılıyor (mainframe aleyhine) | v3 §7.9.2'de açık; yol haritasında ayrı modelleme |
| 3.3 | Üretim dışı kalemde personel yok | Üretim dışı ortamları aynı ekip işletir varsayımı; x86'da çok sayıda ortam ekip yükünü artırabilir (x86 aleyhine olmayan bir basitleştirme) | Ortak kural; iki tarafta aynı |
| 3.4 | Elle geçiş karar süresi / teknik süre ayrıştırması kaynaksız | Toplam kaynaklı, oran değil. X2'nin teknik süresi kısaysa bile karar süresi ortak olduğu için M2–X2 farkı küçük kalır | [ASSUME] olarak belgelendi; bu, tasarımın amacı (x86 planı §8.2) |
| 3.5 | Fiyat dönemi mainframe fiyatlarına uygulanmıyor | 2026-Q3 döneminde x86 şoklu, mainframe şoksuz fiyatlanır (mainframe lehine yanlılık) | Ortak modül dokümanı §7; x86 sonuçları iki dönemle raporlanacak |
| 3.6 | Kullanıcı fiyatları yalnızca biçim olarak denetleniyor | Bir teklifin kapsamı (bakım dahil mi) yanlış eşlenirse sonuç sessizce yanlış olur | Her fiyatın birimi ve açıklaması kayıtta; `--list-prices` şablonu |
| 3.7 | Ortak parametrelerin "low" anlamı | Platform modüllerinde low o platformun lehine uçtur; ortak parametre iki tarafı aynı yönde etkiler | Karşılaştırma katmanı ortak parametreleri iki tarafa aynı değerle uygulamalı (ortak modül dokümanı §12) |

---

## 4. x86 tarafı için durum

Değerlendirme #6 Bölüm 4'teki eşit derinlik gereksinimleri artık kodda bir sözleşmedir (ortak modül dokümanı §12):

- **Yedek:** Nesne depolama ve S3 fiyat fonksiyonları ortak. x86 kendi verim kısıtını ve yedekleme yazılımı lisansını ekleyecek.
- **NPV:** r, g, artış sınıfları, zamanlama ve kalan değer kuralı ortak. x86 kendi amortisman ömrünü verecek.
- **Personel:** Ücret ve taban ekip ortak. x86 kendi FTE eğrisini (IBM Eagle dağıtık saatleri) verecek.
- **Availability:** Saha olayları ve elle geçiş karar süresi ortak. x86 kendi T_rec ve düğüm arızası terimini verecek.
- **Storage:** AFA fiyatları `price_per_raw_tb` ile ham TB'a çevrilecek.
- **Üretim dışı:** x86'nın kendi çarpanı (0 / ? / 2,0), aynı kalemlerle.

Benzer çalışmalar taramasının §8 önerilerinden:

- **Kapandı:** B2 (üretim dışı ortamlar) ve B8 (`PRICE_EPOCH`'un tarihsel gerekçesi).
- **x86 modelinde yapılacak:** B1 (x86 hedef kullanım oranı aralık parametresi).
- **Karşılaştırma katmanında yapılacak:** B3 (DR payı çıktısı) ve B6 ($/TPS değişkenliği).

---

## 5. Kapanan / açık kalan tehditler

**Değerlendirme #6'dan kapanan:**

- **Ortak modül ayrımı (Adım 6):** kapandı. 6 kural ortak modülde. Taşıma regresyon testiyle doğrulandı.
- **Clustered storage tipi kararı:** kapandı. Emirhan K1'i onayladı (RAC → SAN, Patroni → yerel NVMe × replika). Fiyatlama sözleşmesi ortak modülde.
- **3.5 Teknoloji yenilemesi:** kural olarak kapandı ("iki tarafta birlikte dışarıda"; ortak modül §8). Model olarak açık.
- **3.8 Seviyelendirilmiş maliyetin paydası:** kural ortak modülde (`finish_npv`). Clustered tarafla aynı mod kullanılacak.

**Açık kalan:**

- Drawer maliyeti ve enerjinin drawer'la ölçeklenmesi (öncelik yüksek, Değerlendirme #6 §2.5)
- Storage ağının DR'daki asimetrisi
- GDPS Metro'nun ayrı topoloji olması
- Planlı kesinti kalibrasyonu
- L4+ AWLC kademe fiyatlarının yayımlanmamış olması
- Parallel Sysplex ile tek CEC'in ötesine ölçekleme
- Değerlendirme #6'daki 3.1–3.4, 3.6, 3.7 ve 3.9

**Yeni:** 3.1–3.7. En önemlisi 3.1'dir (üretim dışı çarpanın tek kaynağı üretici). x86'da bu çarpanın büyüklüğü (IBM'e göre 2,0) karşılaştırmayı belirleyebilir.

---

## 6. Akademik sunum notları

- **Ana sonuç tablosu iki senaryoyla verilmeli:** üretim dışı ortamlar dahil (mid) ve kapsam dışı (iki çarpan 0). İkincisi literatürdeki tipik TCO karşılaştırmalarıyla aynı kapsamdadır. Birincisi IBM'in iddia ettiği asimetriyi test eder.
- **Ortak modül, yöntemin bir parçası olarak sunulmalı.** "İki taraf aynı varsayımlarla" demek kolaydır; bunun kodda yapısal olarak güvence altına alındığını göstermek savunmayı güçlendirir. Parametre başına tek sahip ve gölgeleme testi bu güvencedir.
- **İki fiyat modu aracın katkısı olarak anılmalı.** Kurum teklifleri girildiğinde aralık daralır. Aracın bir "tahmin" değil, bir "karar destek" aracı olduğunu gösterir.
- **Strateji sonucu koşullu yazılmalı (2.3).**
