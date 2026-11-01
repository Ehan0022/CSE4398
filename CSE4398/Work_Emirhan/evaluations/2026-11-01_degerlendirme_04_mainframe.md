# Değerlendirme #4: Mainframe modeli, storage katmanı eklendikten sonra

> **Değerlendirme #4** · Tarih: 2026-11-01 · Kapsam: mainframe modelinin güncel hali (`src/mainframe_model.py`, `docs/mainframe_model_documentation_v3.md`): 317 kademe, PCI köprüsü, latency, availability, Permanent / Base + CoD / TFP fiyatlama ve yeni DS8900F storage katmanı.
> Önceki değerlendirme: #3 (`2026-10-31_degerlendirme_03_mainframe_ve_storage.md`). Kapanan ve açık kalan maddeler Bölüm 6'da.
> Rakamlar kodu çalıştırarak üretildi (statik mod, average RNI, %99,9, 20 TB veri, varsayılan parametreler). Kaynakla teyit edilmemiş iddialar **(doğrulanmalı)** diye işaretli.

## 0. Özet

1. **Storage katmanı yerinde ve savunulabilir.** Teknik veriler IBM'in kendi dokümanından, fiyatlar kısmen kaynaklı. Kararlar ve varsayımlar dokümanda tek tek gerekçelendirildi (v3, Bölüm 8.1). Katman iki somut sonuç üretiyor: veri hacmi ekseninde ikinci bir crossover mekanizması ve düşük TPS bölgesinde maliyet/TPS eğrisinin bükülmesi.
2. **Yeni bulunan bir tutarsızlık (orta):** Dizi sayısı üreticinin tepe IOPS'unun %100'üne göre hesaplanıyor. Compute tarafında %90 operasyonel tavan varken storage'da tavan yok (Bölüm 2.1).
3. **IOPS_PER_TX artık modelin en etkili varsayımı.** Aynı sayı latency'yi, storage IOPS boyutlandırmasını ve dolaylı olarak dizi modelini belirliyor. REDP-5320 iş yükü profili (transaction köprüsünün mainframe yarısı) bu yüzden öncelik sırasında yukarı çıkmalı (Bölüm 2.2).
4. **En büyük eksik değişmedi: yazılım yığını.** Yazılım hâlâ tek bir $40/MSU kalemi. Storage eklendi ama düz maliyet/TPS sorunu 50K TPS üstünde sürüyor (Bölüm 3).

## 1. Storage katmanının değerlendirmesi

### 1.1. Güçlü yanlar

- **Kaynak kalitesi:** Kapasite, güç, drive tipleri, zHyperLink gecikmesi ve lisans yapısı IBM Product Guide'ından (REDP-5554). Model kataloğu ayrı bir CSV'de, her değerin kaynağı dosya başlığında. Bu, kademe tablosuyla aynı yeniden üretilebilirlik standardı.
- **Mainframe'e özgü mekanizmalar açıkça temsil ediliyor:** shared-disk (kopya sayısı yalnızca DR'dan), storage tabanlı replikasyon, zHyperLink / zHPF, Safeguarded Copy, I/O'nun SAP'lerde işlenmesi. Her biri modelde bir sayıya bağlı ve testle doğrulanıyor.
- **Availability ile maliyet ve latency arasında yeni bir bağ:** Senkron kopya hem storage maliyetini (M1 → M2'de 2 kat) hem yazma gecikmesini (D_io 0,69 → 1,29 ms) artırıyor. Bu, availability'nin yalnızca "frame sayısı" ile değil, veri yolu üzerinden de bedeli olduğunu gösteren, tezde anlatılabilir bir sonuç.
- **Önceki varsayımın yerine kaynaklı bir değer:** Sabit 0,3 ms/I/O kaldırıldı; I/O süresi artık kaynaklı servis sürelerinden (20 µs, 90 µs) hesaplanıyor.

### 1.2. Ürettiği bulgular

**Veri hacmi ekseni (50K TPS):**

| Veri | Storage / toplam |
|---|---|
| 5 TB | %3,9 |
| 20 TB | %9,4 |
| 100 TB | %30,6 |
| 500 TB | %68,0 |
| 2.000 TB | %89,5 |

Compute sabitken storage veri hacmiyle doğrusal büyüyor. Clustered tarafta kopya sayısı ve $/TB farklı olacağı için iki eğrinin eğimi farklı; bu, TPS'ten bağımsız bir crossover ekseni.

**Maliyet/TPS eğrisi (20 TB sabit veri):**

| TPS | Kademe | Toplam/ay | $/TPS/ay | Storage hariç $/TPS/ay |
|---|---|---|---|---|
| 2.000 | 3931-401 | $12.900 | 6,45 | 2,70 |
| 10.000 | 3931-601 | $24.458 | 2,45 | 1,70 |
| 50.000 | 3931-436 | $79.491 | 1,59 | 1,44 |
| 200.000 | 3931-627 | $284.007 | 1,42 | 1,38 |
| 500.000 | 3931-749 | $691.588 | 1,38 | 1,36 |

Storage TPS'ten çok veri hacmine bağlı olduğu için sabit maliyet gibi davranıyor ve eğriyi düşük TPS bölgesinde bükiyor. Bu, Değerlendirme #1'deki "düz maliyet eğrisi" sorununun düşük TPS ucunu kısmen yumuşatıyor. **Ancak bu bulgu dikkatli yorumlanmalı:** gerçekte veri hacmi ile TPS ilişkilidir; 2.000 TPS'lik bir sistemin 20 TB veri taşıması bir senaryo seçimidir, modelin bir sonucu değil. Tezde bu eğri sabit veri hacmi varsayımıyla birlikte sunulmalı, ya da veri hacmi TPS ile birlikte ölçeklenen senaryolar ayrıca gösterilmeli.

## 2. Yeni bulgular ve tehditler

### 2.1. Storage'da operasyonel tavan yok (orta, kolay)

Compute tarafında kademeler %90 kullanım tavanıyla boyutlanıyor. Storage'da ise dizi sayısı, üreticinin önbellek isabetli küçük blok ölçümüyle verdiği tepe IOPS'un (860K / 2.320K) %100'üne göre hesaplanıyor. Bu iki açıdan iyimser: tepe değer gerçek bir OLTP karışımını temsil etmez ve %100 kullanımda dizi kuyruğu ihmal edilemez. **Öneri:** compute ile tutarlı bir storage IOPS tavanı (ör. tepe IOPS'un %70'i [ASSUME]) ve bunun duyarlılık analizine eklenmesi. Bugünkü etkisi sınırlı (yalnızca 860K/2.320K eşiklerinin yakınındaki TPS'lerde model veya dizi sayısı değişir), ama tutarlılık sorunu tezde sorulabilir.

### 2.2. IOPS_PER_TX'in üçlü rolü (yüksek)

`IOPS_PER_TX` (average RNI'da 10) artık üç şeyi birden belirliyor: latency'deki D_io, storage'ın IOPS boyutlandırması ve 90K TPS'teki DS8910F → DS8950F geçişi. Db2 buffer pool'ları fiziksel I/O'yu önemli ölçüde azalttığı için 10 büyük olasılıkla yüksek (doğrulanmalı). Ayrıca aynı sayı x86 tarafına da taşınacak. Kalibrasyonun doğal kaynağı REDP-5320'nin iş yükü tanımı; bu adım transaction köprüsünün de mainframe yarısı. Bu yüzden öncelik sırasında yazılım yığınıyla birlikte en üste çıkmalı.

### 2.3. Latency'nin ayırt ediciliği azaldı (düşük, bilgi)

D_io 3 ms'den 0,69 ms'ye inince latency hedefleri daha az bağlayıcı oldu (50K TPS'te 5 ms hedefte 3931-704 yerine 3931-510). Bu bir hata değil, daha doğru bir girdi. Ama clustered tarafla karşılaştırmada latency'nin ayırt edici bir boyut olup olmadığı, ancak x86 tarafının D_io'su (ağ üzerinden storage, replikasyon) modellenince belli olacak. Latency'nin tezde merkezi bir boyut olarak sunulması bu karşılaştırmaya bağlı.

### 2.4. Fiyat belirsizliği tek parametrede toplandı (orta)

İndirim oranı 0,50–0,85 aralığında storage maliyetini yaklaşık 3 kat oynatıyor. Bu, modelin kurgusundan kaynaklanan bir zayıflık değil, kamuya açık veri eksikliği; ama sonuçların sunumunu belirlemeli: storage içeren mutlak TCO rakamları tek nokta yerine aralık olarak verilmeli. Göreli sonuçlar (veri hacmiyle büyüme, kopya sayısı, IOPS eşikleri) indirimden bağımsız.

### 2.5. DR topolojileri olduğundan pahalı görünüyor (orta, mevcut)

M2–M4'te ikinci frame tam kapasite ve tam fiyatla, storage ise 2–4 tam kopya olarak sayılıyor. Gerçekte DR frame'i genellikle CBU (Capacity BackUp) ile çok daha düşük aktif kapasiteyle tutulur. Storage kopyalarının tam sayılması doğru (veri gerçekten çoğaltılıyor), ama compute tarafındaki CBU eksikliği yüksek availability senaryolarında mainframe'i sistematik olarak pahalı gösteriyor. Değerlendirme #2'den beri açık; storage eklenince yüksek availability senaryolarındaki toplam fark daha da büyüdü.

### 2.6. Storage ağının kapsam dışı olması DR'da yeniden düşünülmeli (düşük)

Storage ağı "iki tarafta da paralel" gerekçesiyle kapsam dışı. Yerel ağ için bu doğru. Ancak M3/M4'teki siteler arası replikasyon hattında asimetri olabilir: storage tabanlı replikasyon her blok yazmayı (veri, indeks, log) taşırken DB tabanlı replikasyon yalnızca mantıksal log'u taşır; bant genişliği ihtiyacı farklı olabilir (doğrulanmalı). GDPS adımında yeniden değerlendirilmeli.

## 3. Mainframe tarafının genel durumu

| Katman | Durum | Kalite |
|---|---|---|
| Compute kapasitesi (kademeler, köprü) | Tamam | Resmî veri, doğrulanmış türetme |
| Latency | Tamam | Kuyruk modeli + kaynaklı I/O süreleri; IOPS_PER_TX varsayım |
| Availability | Kısmen | M1–M4 var; CBU, RPO/RTO, M4 etiketleri açık |
| Donanım fiyatlama | Tamam | Permanent / CoD / TFP, resmî sınırlar; fiyatlar varsayım |
| Storage | Tamam (bu oturum) | Teknik veri resmî; fiyat kısmen kaynaklı |
| Yazılım yığını | **Eksik** | Tek $40/MSU; CICS, Db2, kademeli MLC, zIIP yok |
| Personel | **Eksik** | Yok |
| DR (GDPS kalemi, CBU) | **Eksik** | GDPS yazılım primi olarak gömülü |
| Yedekleme (TS7700) | Eksik | Safeguarded Copy var, dış yedek yok |
| Çok yıllık ufuk (NPV) | Eksik | Tek yıl |

**Eşit derinlik açısından:** Mainframe tarafında compute, donanım fiyatlama ve storage derin; yazılım ve personel yok. Bu dengesizlik clustered tarafa geçmeden kapatılmalı, çünkü clustered tarafın yazılım (DB lisansı veya açık kaynak) ve personel maliyetleri onun en ayırt edici kalemleri olacak. Bu kalemler olmadan yapılan bir karşılaştırma mainframe lehine yanlı olur.

**Kod sağlığı:** `mainframe_model.py` yaklaşık 1.500 satıra ulaştı ve tek dosyada kademeler, latency, availability, maliyet, storage, yıllık simülasyon ve CLI'yı barındırıyor. Clustered model eklenmeden önce ortak parçaların (girdi arayüzü, storage arayüzü, yıllık profil üretici) ayrı bir modüle taşınması iki tarafın aynı girdileri kullanmasını garanti eder. 10 test geçiyor; tam paket yaklaşık 13 saniye.

## 4. Önerilen sıra

1. **Storage IOPS tavanı** (küçük; Bölüm 2.1). Tutarlılık düzeltmesi, bir oturumda kapanır.
2. **Yazılım yığını:** z/OS + CICS TS + Db2, kademeli MLC (MSU arttıkça düşen birim fiyat), zIIP. En büyük kalem ve düz eğrinin ana kaynağı.
3. **REDP-5320 iş yükü profili:** IOPS_PER_TX ve transaction köprüsü. 2 ile paralel yürüyebilir.
4. **Personel**, ardından **CBU + GDPS kalemi**.
5. **Ortak modül ayrımı** (clustered tarafa geçmeden hemen önce), **5 yıllık NPV**.

## 5. Akademik sunum notları

- Storage içeren sonuçlar indirim aralığıyla (0,50–0,85) birlikte verilmeli.
- Storage payı tek bir yüzde değil, veri hacmi ekseninde bir eğri olarak sunulmalı.
- Maliyet/TPS eğrisinin düşük TPS'teki bükülmesi, sabit veri hacmi varsayımına bağlı olduğu açıkça belirtilerek sunulmalı.
- Mainframe tarafında storage için CPU yükü eklenmemesi bilinçli bir asimetri olarak (v3, Bölüm 8.1.3) tezde açıklanmalı; aksi halde hakem bunu eksik sanabilir.

## 6. Kapanan / açık kalan tehditler

**Değerlendirme #3'ten kapanan:** 3 (storage, DS8900F) ve storage'ın iki taraf için ortak arayüzle tanımlanması (mainframe yarısı). D_io'nun kaynaklı değerlerle kalibrasyonu (kısmen: I/O süresi kaynaklı, IOPS_PER_TX hâlâ varsayım).

**Açık kalan:** Transaction köprüsü (Değerlendirme #1, tehdit 1), yazılım yığını (#3 madde 2), personel (#3 madde 4), donanım tabanı ve drawer maliyeti (#3 madde 5), zIIP (#3 madde 6), CBU/GDPS/RPO-RTO (#3 madde 7), çok yıllık ufuk (#3 madde 8), enerjinin drawer'la ölçeklenmesi (#3 madde 9), clustered storage tipi kararı (#3 Bölüm 4, karar kartı açık).

**Yeni:** Storage IOPS tavanı (2.1), IOPS_PER_TX'in üçlü rolü (2.2), storage ağının DR'daki asimetrisi (2.6), ortak modül ayrımı (Bölüm 3).
