# Değerlendirme #6: Yedekleme katmanı ve 5 yıllık NPV

> **Değerlendirme #6** · Tarih: 2026-11-02 · Kapsam: Adım 5. Bunlar IBM TS7770 yedekleme katmanı (`backup_plan`, v3 §8.10) ve 5 yıllık ufuk (`solve_npv`, `solve_npv_yearly`, `solve_npv_range`, v3 §9.10) ile bunların statik ve yıllık moda, aralık çıktısına ve araçlara etkisidir.
> Önceki değerlendirme: #5 (`2026-11-01_degerlendirme_05_denetim.md`). Kapanan ve açık kalan maddeler Bölüm 6'da.
> Yöntem:
> - Her yeni mekanizma, önce mevcut modelle sayısal tutarlılık koşuluna bağlandı, sonra yön testleriyle güvencelendi.
> - Sayılar `src/tools/npv_sensitivity.py`, `range_curve.py` ve diğer duyarlılık araçlarının yeniden üretilmiş çıktılarındandır.
> - Varsayılanlar: oltp_rw, %99,9, 20 TB veri, %15 veri büyümesi; NPV'de %10 TPS büyümesi ve %7 iskonto.

## 0. Özet

1. **Yedekleme katmanı eklendi.** Db2 image copy'leri ve arşiv loglar iki sitelik TS7770 grid'inde 4 hafta saklanır.
   - 10K TPS ve 20 TB'ta maliyeti aylık $11.790'dır (toplamın %1,4'ü).
   - 2.000 TB'ta toplamın %15,9'una çıkar. Storage ile birlikte payı %52'dir.
   - Veri hacmi crossover eksenini güçlendirir.
   - Yıllık modda üç stratejiye aynı tutarı ekler, sıralamayı değiştirmez.
2. **5 yıllık NPV eklendi.**
   - Yük büyür, kademe yalnızca yükselir.
   - Storage ve yedek iki döngüde alınır. Fiyat artışları bileşiktir. TFP'nin büyüme fiyatı modellenir.
   - Model, r = 0 ve büyüme ile artış 0 iken amortismanlı modelle **tam** örtüşür: NPV = 60 × statik aylık toplam ve 5 × yıllık toplam (10⁻⁹ içinde).
3. **Statik sonuç 5 yıllık kararın iyi bir yaklaşığıdır.** 10K TPS'te seviyelendirilmiş maliyet $85,96/TPS/ay, statik $85,23'ten yalnızca %0,9 farklıdır. Fiyat artışları ile büyümenin ölçek ekonomisi birbirini neredeyse götürür.
4. **Aralık genişledi.** NPV aralığı (10K TPS) $32,07 / $85,96 / $409,24'tür. Statik aralık $27,17 / $85,23 / $341,23'tür. Genişleme, fiyat artışlarının köşe senaryolarına katılmasından gelir.
5. **5 yılda TFP üç presette de kazanır.** Tek yılda retail_bursty'de B kazanıyordu. Sonuç TFP büyüme fiyatına ve büyüme varsayımına koşulludur: büyüme indirimi kaldırılırsa ya da yük büyümezse retail_bursty'de B yeniden öne geçer.
6. **Testler:** 20 testten 22'ye çıktı, hepsi geçiyor.

## 1. Doğrulama

| # | Kontrol | Sonuç |
|---|---|---|
| 1.1 | r = 0, TPS ve veri büyümesi 0, artışlar 0: statik NPV = 60 × statik aylık toplam | Fark 10⁻¹⁶ (test) |
| 1.2 | Aynı koşulda yıllık NPV (Permanent ve TFP) = 5 × yıllık toplam | 10⁻⁹ içinde (test) |
| 1.3 | Düz yükte yıllık toplam = 12 × statik aylık (yedek kalemi dahil) | Binde bir içinde (test, Değerlendirme #5'ten) |
| 1.4 | Kademe yolu yalnızca yükselir (PCI, CP sayısı ve seri sırası azalamaz) | `is_permanent_upgrade` ile her yıl; %15 büyümede test |
| 1.5 | Yön: iskonto ↑ → NPV ↓; büyüme ↑ → NPV ↑, $/TPS ↓; TFP büyüme fiyatı ↑ → TFP NPV ↑ | Hepsi beklenen yönde (test ve araç bölüm 3, 4) |
| 1.6 | Yedek: hacim veri, saklama ve TPS ile artar; küme sayısı cache ve verim sınırını karşılar; topolojiden bağımsız | Test (`test_backup_layer`) |
| 1.7 | Geri dönüş süresi M1'in 72 saatlik RTO'suyla tutarlı | 20 TB ~1,4 saatte okunur (v3 §8.10.6) |

1.1 ve 1.2 bu adımın en önemli güvencesidir. Nakit akışı modeli ayrı bir maliyet hesabı kurmaz; statik ve yıllık modun maliyet fonksiyonlarını yeniden kullanır. Aradaki bütün fark zamanlama, büyüme ve fiyat artışından gelir. Bu, NPV sonucunun önceki değerlendirmelerde denetlenen maliyet tabanını devraldığını gösterir.

**İlk sürümdeki bir hata düzeltildi.** Yıllık NPV'nin ilk sürümü her yılı bağımsız optimize ediyordu. Bu, base kademenin bir yıl düşüp sonra sıçradığı (714 → 625 → …) fiziksel olarak imkânsız bir yol üretti, çünkü kalıcı kapasite geri satılamaz. Düzeltmeden sonra:

- base kademe bir önceki yılın base'inin izinli bir yükseltmesi olmak zorunda (`base_floor`);
- topoloji 1. yılda sabitleniyor (`only_topology`).

## 2. Bulgular

### 2.1. Yedekleme veri hacmi eksenini güçlendirir, TPS eksenini az etkiler

| Veri (10K TPS) | Yedek / ay | Toplamdaki payı | Storage + yedek payı |
|---|---|---|---|
| 5 TB | $9.870 | %1,2 | %1,5 |
| 20 TB | $11.790 | %1,4 | %2,3 |
| 100 TB | $20.750 | %2,3 | %5,9 |
| 500 TB | $75.420 | %7,1 | %22 |
| 2.000 TB | $273.350 | %15,9 | %52 |

- **Küçük veri:** Maliyet iki kümenin sabit tabanıdır, bu yüzden yedek storage'tan pahalıdır. 500 TPS'te toplamın %6'sıdır ve düşük TPS'teki bükülmeye küçük bir katkı yapar.
- **Büyük veri:** Günlük verim sınırı küme ekletir. Storage ve yedek birlikte 500 TB'ta toplamın beşte birini geçer.
- **Sonuç:** Değerlendirme #4'te önerilen "veri hacmi ikinci crossover ekseni" hipotezi yedekle daha güçlü hale geldi. Clustered tarafta yedekleme yazılımı lisansı genellikle TB veya iş yükü başınadır. Bu iki eğrinin eğimi farklı olabilir; crossover'ı belirleyecek olan budur.

### 2.2. Statik ölçü 5 yıllık sonuca yakındır, ama aralık genişler

- **Seviyelendirilmiş maliyet:** $85,96, statik $85,23'e göre +%0,9.
  - Büyüme 0'da seviyelendirilmiş maliyet $91,54'tür (+%7, yalnızca fiyat artışları).
  - %20 büyümede $81,12'dir.
  - Yani büyüme mainframe lehine çalışır. Bu, bükülen maliyet eğrisinin (v3 §7.6) zaman boyutundaki karşılığıdır.
- **Önceki bulguların geçerliliği:** Değerlendirme #1–#5'teki statik sonuçlar geçerliliğini korur. Statik mod, 5 yıllık bir kararın sistematik olarak yanlı olmayan bir yaklaşığıdır.
- **Aralığın üst ucu açılır:** high $341 → $409 (+%20). Fiyat artışları köşe senaryolarında aynı yöne çekildiğinde aralığın üst ucu belirgin biçimde açılır. Bu yüzden tezde aralık, NPV moduyla raporlanmalıdır. Statik aralık belirsizliği eksik gösterir.
- **Tornado'nun başı değişmez:** personel 36,6–80,9; okuma SQL CPU 42,5–70,7; AWLC seviyesi 41,3–65,6 (NPV, milyon USD). Fiyat artışlarının en etkilisi (yazılım) 10. sıradadır.

### 2.3. İskonto oranı NPV'yi değiştirir, mainframe'in birim maliyetini neredeyse değiştirmez

- r = %5'ten %10'a NPV %12 düşer, ama seviyelendirilmiş maliyet yalnızca %1 oynar.
- Mainframe'in bugünkü değer dökümünde capex payı ~%8'dir: donanım %7,5, storage ve yedek alımı %1,6.
- Clustered taraf daha capex ağırlıklıysa ve 5 yıl içinde donanım yenilemesi varsa, r iki tarafı farklı etkiler.
- Crossover'ın r'ye duyarlılığı ancak x86 tarafı eklendiğinde ölçülebilir. Bu yüzden r köşe senaryolarına değil, ayrı bir taramaya konuldu (v3 §9.10.4).

### 2.4. Fiyatlama stratejisi kararı büyüme beklentisine bağlıdır

| 5 yıllık NPV (M$) | Permanent | Base + CoD | TFP |
|---|---|---|---|
| steady_oltp | 69,396 | 68,113 | **65,863** |
| retail_bursty | 115,540 | 113,154 | **112,485** |
| batch_heavy | 92,247 | 88,326 | **87,201** |

- TFP'nin 5 yıllık avantajı tepe yapısından değil, büyüme MSU'larının indirimli fiyatından gelir.
- TFP_GROWTH_PRICE_FACTOR = 1,0 iken (indirim yok) retail_bursty ve batch_heavy'de B kazanır.
- TPS büyümesi 0 iken retail_bursty'de B kazanır.
- Büyüme fiyatının tek dayanağı bir bağımsız danışmanın aktardığı "%50 indirim"dir [KYNE-2022]. Sözleşmeye özeldir. Strateji sonucu kesin bir öneri değil, koşullu bir bulgudur.
- Permanent hiçbir presette, hiçbir duyarlılık durumunda kazanmaz.

### 2.5. Drawer sınırı 5 yıllık yolu kırar (yapısal bir eksiğin görünür hale gelmesi)

- retail_bursty'de 5. yılın tepesi (~51K TPS), Max39 drawer özelliği üzerindeki geçici kapasiteyi aşar.
- Geçici kapasite drawer ekleyemez (SC28-7025). Bu yüzden base 716'dan 740'a sıçrar ve 5. yılda ~$6,5M capex oluşur.
- Gerçekte kurum büyük drawer özelliğini önceden kurar. Drawer maliyeti modelde olmadığı için bu seçenek değerlendirilemiyor.
- Değerlendirme #5'te açık kalan "drawer maliyeti" maddesinin somut bir sonucu budur ve bu maddenin önceliğini yükseltir.

## 3. Geçerlilik tehditleri (yeni)

| # | Tehdit | Etki | Ele alınışı |
|---|---|---|---|
| 3.1 | TS7770 fiyatı yayımlanmıyor. Küme tabanı 2006 TS7700 başlangıç fiyatıdır (nominal); cache fiyatı kaynaksızdır | Yedek NPV'nin %0,9'u (alım) + bakım payı; 2 PB'ta toplamın %16'sı | Cache fiyatı, sıkıştırma ve saklama aralık parametresi; storage indirimiyle ortak. Büyük veride gerçek bir teklif gerekir |
| 3.2 | Yedek işinin CPU'su (COPY utility, log arşivleme) MSU'ya eklenmez | Yedek penceresi R4HA tepesiyle çakışırsa yazılım eksik sayılır | Varsayım v3 §8.10.6 ve §12.2'de açık |
| 3.3 | Çok büyük veride kurumlar image copy yerine FlashCopy kullanır | Yüzlerce TB'ta yedek fazla sayılabilir (mainframe aleyhine) | Sınırlama olarak yazıldı |
| 3.4 | Kademe yolu açgözlüdür: her yıl o yılın yükü için en ucuz izinli yükseltme seçilir | NPV bir üst sınırdır; ileriye bakan bir plan daha ucuz olabilir | v3 §9.10.8. Aynı kural x86 tarafına uygulanırsa karşılaştırma adil kalır |
| 3.5 | 5 yıl içinde teknoloji yenilemesi (z17) ve göç maliyeti yok | Yükseltme PCI fiyatı nominal sabit; yeni nesil fiyat/performansı dışarıda | x86 tarafında yenileme döngüsü varsa asimetri doğar; ortak modülde açık bir kural gerekir |
| 3.6 | TFP büyüme fiyatı tek kaynaklı (0,5) | Strateji sıralaması bu parametreye duyarlı (2.4) | NPV aralık parametresi (0,5–1,0; low ucu kaynağın kendisi) ve ayrı tarama |
| 3.7 | Fiyat artışlarının orta değerleri kısmen varsayım (yazılım ve bakım %3; IBM liste artışı ~%6) | Yazılım artışı 0 → %6: NPV −%2,2 → +%2,3 | Aralık parametresi; liste artışının sözleşmeli müşteriye tam yansımadığı varsayımı belgelendi |
| 3.8 | Statik NPV'de seviyelendirilmiş maliyetin paydası tasarım tepesi, yıllık NPV'de ortalama yüktür | İki modun $/TPS/ay değerleri doğrudan karşılaştırılamaz | v3 §9.10.2'de tanımlı. Clustered tarafla aynı mod kullanılmalı |
| 3.9 | Kalan değer 0 | Tutucu (mainframe aleyhine); 0,5 ve 1,0'da NPV −%0,4 ve −%0,8 | Duyarlılıkta gösterildi |

## 4. Clustered taraf için eşit derinlik gereksinimleri

Adım 5'in eşit derinlik ilkesi açısından x86 tarafına bıraktığı yükümlülükler:

- **Yedekleme:** Yedek hacmi aynı girdilerden türetilmelidir. Bunlar veri, büyüme, 4 hafta saklama, %3 günlük değişim ve işlem bileşiminden log hacmidir. Clustered taraf yedekleme yazılımı lisansını, hedef depolamasını ve kendi sıkıştırma/tekilleştirme oranını ekler. Yedek iki sitede tutulmalıdır.
- **NPV:**
  - Aynı r, g, veri büyümesi, ufuk ve zamanlama kuralı (capex yıl başı, opex yıl sonu) kullanılmalıdır.
  - Aynı fiyat artışı sınıfları (yazılım, bakım, ücret, enerji) kullanılmalıdır.
  - Aynı açgözlü genişleme kuralı geçerlidir; x86'da kademe yükseltmesi yerine düğüm eklenir.
  - Donanım yenilemesi (genellikle 3–5 yıl) x86 tarafında açıkça modellenecekse, mainframe tarafında z17'ye geçişin neden olmadığı tezde gerekçelendirilmelidir.
- **Bu kuralların yeri:** Bunlar Adım 6'daki ortak modülün (iki tarafın aynı fonksiyonları çağırması) somut içeriğidir.

## 5. Akademik sunum notları

- NPV'nin amortismanlı modelle tam örtüşmesi (1.1–1.2) tezde "model doğrulama" başlığında bir cümleyle anılmalıdır. Bu, iki ayrı maliyet hesabı olmadığının kanıtıdır.
- Ana sonuç tablosu NPV aralığıyla (low / mid / high, seviyelendirilmiş $/TPS/ay) verilmeli, statik aralık ise yardımcı olarak kalmalıdır (2.2).
- Strateji sonucu (TFP) "büyüme beklentisi ve büyüme fiyatı varsayımı altında" diye koşullu yazılmalıdır (2.4).
- İskonto oranının ayrı tarama olması bir tasarım kararıdır. Gerekçesi şudur: r bir fiyat belirsizliği değil, kurumun sermaye maliyetidir ve iki tarafta aynı olmalıdır.

## 6. Kapanan / açık kalan tehditler

**Değerlendirme #5'ten kapanan:**
- Çok yıllık ufuk ve yedekleme (Adım 5): **kapandı.** TS7770 katmanı ve 5 yıllık NPV, aralık ve tornado dahil.
- TFP-SW'nin büyüme fiyatı (v3 §9.6'da "5 yıllık ufukta modellenecek" denmişti): **kapandı.**

**Açık kalan:**
- Ortak modül ayrımı (Adım 6). İçeriği Bölüm 4'te somutlaştı.
- Drawer maliyeti ve enerjinin drawer'la ölçeklenmesi. **Öncelik yükseldi** (2.5).
- Clustered storage tipi kararı.
- Storage ağının DR'daki asimetrisi.
- GDPS Metro'nun ayrı topoloji olması.
- Planlı kesinti kalibrasyonu.
- L4+ AWLC kademe fiyatlarının yayımlanmamış olması.
- Parallel Sysplex ile tek CEC'in ötesine ölçekleme.

**Yeni:** 3.1–3.9.
- 3.4 (açgözlü yol) ve 3.5 (teknoloji yenilemesi) x86 tarafıyla birlikte ele alınmalıdır.
- 3.1 (TS7770 fiyatı) yalnızca büyük veri senaryolarında sonucu etkiler.

## 7. Ek (2026-11-02, aynı gün): Yedekte nesne depolama seçenekleri

Bu değerlendirmeden sonra, Emirhan'ın isteğiyle yedek katmanına iki hedef daha eklendi: S3 uyumlu on-prem nesne depolama ve AWS S3. Seçim Emirhan'ındır: "ikisi de, model seçsin". Yukarıdaki bölümlerdeki sayılar TS7770'in tek hedef olduğu durumu gösterir. Güncel sayılar aşağıdadır; v3 dokümanı güncel hali taşır (§8.10).

**Ne değişti:**
- Üç aday hedef var: TS7770, on-prem nesne depolama, AWS S3. Model kısıtları karşılayanlar arasından en ucuzunu seçer.
- Nesne hedeflerine yol, DS8900F'in Transparent Cloud Tiering özelliğidir [SG24-8381]. Image copy'ler DASD'ye yazılır, DFSMShsm ile göç ettirilir.
- Kısıtlar:
  - **Yedek penceresi:** 8 saat.
  - **M1'de tam geri yükleme:** RTO'nun yarısı, 36 saat. Yalnızca alternatif sitesi olmayan topolojide bağlar.
  - **TCT verimi:** 5.000 MB/s, varsayım. Nesne hedeflerini eler.
- S3, Direct Connect hattının bedeliyle (port + taşıyıcı devre) fiyatlanır. Seçildiğinde çıktıda "hibrit" diye işaretlenir.
- NPV'de S3, hat ve abonelik ücretleri her yıl o yılın hacmiyle işletme gideri olarak sayılır. Hedef 1. yılda sabitlenir.
- Aralığa iki parametre eklendi: on-prem donanım fiyatı ve abonelik. Toplam 20 parametre.
- Testler 23/23.

**Bulgular:**
1. **Küçük ve orta veride nesne depolama TS7770'in yaklaşık yarısıdır.**
   - 10K TPS ve 20 TB'ta yedek $11.790 yerine $5.635 (on-prem nesne).
   - Başlık sonucu $85,23 → $84,62/TPS/ay (−%0,7).
   - Aralık $27,06 / $84,62 / $338,09.
   - NPV $50,60M, seviyelendirilmiş $85,31; NPV aralığı $31,98 / $85,31 / $405,44.
2. **Topoloji yedek teknolojisini belirler.**
   - M1'de tam geri yüklemenin 36 saate sığması gerekir. Bu yüzden nesne hedefleri ~360 TB'ta elenir ve yedek TS7770'e geçer.
   - M3'te elenme, günlük yedek veriminden dolayı ~550 TB'tadır.
   - Bu, availability ile yedek arasında daha önce modellenmemiş bir etkileşimdir.
3. **Veri hacmi ekseni korunur.**
   - Storage ve yedek birlikte 20 TB'ta toplamın %1,6'sı (önce %2,3), 500 TB'ta %22'si, 2.000 TB'ta %52'sidir.
   - Büyük veride yedek yine TS7770'tir. 2.000 TB'ta M1'in geri yükleme kısıtı TS7770'e ek küme ekletir: $290.531/ay (önce $273.350).
4. **AWS S3 nadiren kazanır.**
   - Yalnızca çok küçük veride (5 TB, farkı $3) ya da hat bedeli sıfır sayılırsa öne geçer. Hat bedeli sıfır, kurumda zaten Direct Connect hattı olması demektir.
   - Sonuç, hattın sabit bedelinin dahil edilmesine bağlıdır.
5. **Strateji sıralamaları değişmedi.**
   - Tek yılda kazananlar: steady C 12,816, retail B 21,382, batch C 17,295 (M$).
   - 5 yılda TFP üç presette kazanır: 65,461 / 112,083 / 86,798.

**Yeni geçerlilik tehditleri:**
- **TCT verimi yayımlanmıyor.** 5.000 MB/s, port sayısından türetilmiş bir varsayımdır. Nesne hedeflerinin elendiği veri eşiği bu değerle doğrusal ölçeklenir: 2.500 MB/s'te M1 için 180 TB, 10.000 MB/s'te 720 TB.
- **On-prem nesne depolama fiyatı tek bir üretici örneğine dayanır** [MINIO-TCO]. Değer aralık parametresidir.
- **SG24-8381, Db2 image copy'yi TCT için açık bir kullanım durumu olarak listelemez.** Model, image copy'lerin DASD'ye yazılıp DFSMShsm ile göç ettirildiğini varsayar.
- **Mantıksal bozulmadan geri dönüşün RTO'su ayrı bir hedef değildir.** Geri yükleme kısıtı yalnızca M1'de bağlar.

**Clustered taraf için:** On-prem nesne depolama ve S3'ün fiyat fonksiyonu iki tarafta ortak olabilir. Bu, Adım 6'daki ortak modülün doğal bir parçasıdır.
