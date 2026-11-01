# Proje Logu (CSE4398 Bitirme Projesi)

> Bu dosya projede alınan aksiyonları ve sebeplerini kronolojik olarak tutar. Başlangıç dokümanları (`project_justification.md`, `project_context_restore_v4.md`, `mainframe_model_documentation_v2.md`) projenin *tasarımını* anlatır. Bu log ise *ne zaman, neyi, neden değiştirdiğimizi* kaydeder. Yeni girdiler en alta eklenir.
>
> Biçim: her girdi **Aksiyon → Sebep → Etki/Sonuç → Açık kalanlar**.

---

## 2026-10-31 — Oturum 1: Projenin okunması ve ilk düzeltmeler

### 1. Projenin baştan okunması
- **Aksiyon:** Klasördeki 4 dosya (3 doküman + `mainframe_model.py`) okundu. Kod `--demo`, `--calibration` ve 3 preset için `--yearly` modunda çalıştırıldı.
- **Sebep:** Yeni çalışmaya başlamadan önce amacı, sabit kararları, mevcut kodun gerçekte ne yaptığını ve sıradaki adımları doğrulamak.
- **Sonuç:** Amaç ve kararlar dokümanlarla tutarlı anlaşıldı. Kodda iki model hatası ve dokümanlar arasında birkaç tutarsızlık bulundu (aşağıda).

### 2. Karar: Messaging (IBM MQ) kapsam dışı
- **Aksiyon:** MQ, `project_context_restore_v4.md` ve `mainframe_model_documentation_v2.md` içindeki tüm "yapılacak" ve "yığın" listelerinden çıkarıldı. Karşılaştırma tablosunda Messaging satırı iki taraf için de "Kapsam dışı" yapıldı.
- **Sebep:** Dokümanlar çelişiyordu. `project_justification.md` messaging'i kapsam dışı sayıyordu, diğer iki doküman ise MQ'yu Phase 2'ye koyuyordu. Emirhan kararı netleştirdi: **MQ kapsam dışı**.
- **Etki:** Mainframe TCO genişletmesi artık CICS, Db2, DS8900F, GDPS ve personelden oluşuyor. Clustered tarafta da messaging modellenmeyecek (simetri korunuyor).

### 3. Karar: Proje her zaman akademik bir gözle değerlendirilecek
- **Aksiyon:** Bundan sonraki her adımda, model ve kod değişikliklerinin akademik savunulabilirliği (kuyruk teorisi doğruluğu, tutuculuk iddialarının gerçekten sağlanıp sağlanmadığı, varsayımların etiketlenmesi, iki tarafa eşit disiplin) ayrıca değerlendirilecek.
- **Sebep:** Emirhan'ın isteği.

### 4. Düzeltme: Latency modeli (mainframe_model.py, BÖLÜM 4)
- **Sorun:**
  - Eski kod E[X] = 1 / (kademenin **toplam** ham TPS'i) alıyordu. Bu, bütün kademeyi tek bir çok hızlı sunucu sayar.
  - (a) **Akademik hata:** Aynı utilization'da hızı c·μ olan tek sunuculu M/M/1, c sunuculu M/M/c'den *daha düşük* yanıt süresi verir. Dokümanlarda "M/M/1 tutucu üst sınır" deniyordu, ama bu kurulumda model aslında **iyimserdi**.
  - (b) **Davranış hatası:** E[X] mikrosaniye mertebesinde çıktığı için her makul hedefte tavan %95'e (HARD_UTILIZATION_CAP) yapışıyordu. Latency hedefi verilince tavan %90'dan %95'e çıkıyor ve sistem **ucuzluyordu**. 50K TPS, avg RNI örneğinde: latency yokken 3931-608, $109.520/ay; p99 < 200 ms veya p99 < 50 ms ile 3931-512, $98.034/ay. Bu durum "8 girdinin hepsi etkin ve tutarlı olmalı" başarı ölçütünü bozuyordu.
- **Aksiyon (yeni model):**
  - Sunucu = fiziksel CP; E[X_cpu] = c / raw_tps. Alt-kapasite CP'leri yavaş olduğu için E[X] büyür. Bu gerçek bir mainframe etkisidir.
  - Tutucu kuyruk: c adet bağımsız M/M/1 (her birine λ/c). Paylaşımlı M/M/c'den kötü sonuç verdiği için gerçek bir üst sınırdır.
  - Sabit I/O gecikmesi: D_io = IOPS_PER_TX[rni] × 0,3 ms (low 5, avg 10, high 20 I/O/tx). IOPS_PER_TX projenin "IOPS RNI'ya gömülü" kararından gelir. 0,3 ms [ASSUME] (DS8900F + FICON/zHPF için sektör aralığı ~0,1–0,5 ms). Tüm I/O sıralı sayıldı (tutucu).
  - R(p) = D_io + E[X_cpu]/(1−ρ)·ln(1/(1−p)); ρ_max = min(1 − E[X_cpu]·ln(1/(1−p)) / (hedef − D_io), 0,90).
  - %90 operasyonel tavan artık her zaman geçerli; latency hedefi tavanı yalnızca düşürebilir. HARD_UTILIZATION_CAP = 0,95 kaldırıldı (eski isim geriye uyumluluk için 0,90'a eşitlendi).
  - Yardımcı fonksiyonlar eklendi: `raw_tier_tps`, `io_delay_seconds`.
- **Doğrulama:** 3 RNI × 5 TPS × 13 latency hedefi (3–500 ms) tarandı. Hedef sıkılaştıkça maliyet hiçbir senaryoda azalmadı, latency'siz durumdan ucuz sonuç da hiç çıkmadı.
- **Akademik bulgu (önemli):** Düzeltilmiş modelde latency 50 ms ve üstündeki hedeflerde mainframe kademesini değiştirmiyor; yalnızca tek haneli ms hedeflerde bağlayıcı oluyor (ör. 10K TPS avg RNI'da 20 ms hedef 3931-408 yerine 3931-701 seçtiriyor, 3 ms'de ise infeasible). Yani tipik bankacılık SLA'larında (100–500 ms) CPU kuyruğu mainframe için bağlayıcı değil. Dokümanlardaki "sıkı SLA → büyük kademe" iddiası bu bulguya göre yumuşatılmalı. Latency farkının asıl clustered tarafta (ağ gecikmesi + paralel düğümler) görülmesi bekleniyor.
- **Açık kalanlar:** I/O gecikmesi varsayımları (0,3 ms, tüm I/O'ların senkron sayılması) tezde savunulmalı ya da kalibre edilmeli. Clustered taraf aynı kuyruk ailesini ve D_io terimini kullanmalı (eşit derinlik).

### 5. Düzeltme: R4HA sub-capacity faturası (mainframe_model.py)
- **Sorun:** Eski kodda R4HA'ya göre yazılım indirimi yalnızca CoD aktif aylarda uygulanıyordu. Permanent strateji her ay tam kurulu MSU üzerinden faturalanıyordu. Gerçek sub-capacity MLC'de fatura, CoD olsun olmasın, her ay R4HA tepesinde tüketilen MSU'ya göre kesilir. Bu asimetri Base+CoD stratejisini haksız biçimde avantajlı gösteriyordu.
- **Aksiyon:** `consumed_msu(tier, load, rni)` eklendi: faturalanan MSU = min(yük / ham TPS, 1) × kurulu MSU. `monthly_cost` fonksiyonuna `billed_msu` parametresi eklendi. Yıllık simülasyonda her ay, iki strateji için de, o ayın R4HA tepesi faturalanıyor (CoD aktif aylarda kurulu kapasite peak kademe sayılıyor). Statik modda yük sabit olduğundan R4HA = TPS kabul edildi.
- **Sonuç (50K TPS, 0.999, avg RNI):**

  | Preset | Önce | Sonra |
  |---|---|---|
  | retail_bursty | CoD, $3,23M, tasarruf %36 | CoD, $3,04M, tasarruf %31,8 |
  | batch_heavy | — | CoD, $2,53M, tasarruf %19,8 |
  | steady_oltp | Permanent, $2,20M, fark ~$10K | Permanent, $2,01M, fark %5,1 |

  Beklenen sıralama korunuyor: peak/avg oranı arttıkça CoD avantajı artıyor. Artık iki strateji arasındaki fark yalnızca donanım tarafından geliyor.
- **Ek:** Base kademenin "ortalama yükün %120'sini taşıma" eşiği koda [ASSUME] olarak etiketlendi.

### 6. Test dosyası eklendi
- **Aksiyon:** `test_mainframe_model.py` eklendi (yalnızca standard library; `python test_mainframe_model.py` ile çalışır). 4 test var: latency monotonluğu, sıkı latency'nin bağlayıcı olması, MSU faturasının kurulu kapasiteyle sınırlı olması, CoD avantajının burstiness ile artması. 4'ü de geçiyor.
- **Sebep:** Yeniden üretilebilirlik (projenin katkılarından biri) ve ileride yapılacak değişikliklerin bu düzeltmeleri bozmadığını otomatik olarak görmek.

### 7. Dokümanlarda yapılan güncellemeler
- `mainframe_model_documentation_v2.md`: Bölüm 5 (latency) düzeltme notu, yeni formül ve doğrulama ile yeniden yazıldı. Bölüm 7.1 ve 7.5'e sub-capacity faturası eklendi. Bölüm 8.5 ve 8.6 yeni sonuçlarla güncellendi. MQ satırları çıkarıldı, kod satır sayısı düzeltildi.
- `project_context_restore_v4.md`: MQ çıkarıldı, CoD tasarrufu %32 olarak güncellendi.
- `project_justification.md`: CoD tasarrufu %32 olarak güncellendi.
- Değişiklik öncesi orijinal 4 dosyanın yedeği proje dosyalarında `backup_2026-10-31/` klasöründe tutuluyor.

### 8. Fark edilen ama henüz dokunulmayan noktalar
- **M4 kaynak etiketleri ters:** hw_low [REDBOOK], hw_high [ITIC] etiketli; diğer topolojilerde vendor = high, bağımsız = low. M3 ve M4'ün effective low değeri de aynı (%99,99999). Kaynağa bakılarak düzeltilmeli.
- **Bağlanmamış girdiler:** data_volume_tb, data_growth_pct, rpo_seconds ve rto_minutes kodda henüz kullanılmıyor (Phase 2: storage, DR ve topoloji eleme).
- **Tek frame tavanı:** En büyük kademe 3931-732 (~251K TPS @ %90). Daha büyük yükler infeasible dönüyor.
- **Doküman tutarsızlıkları:** Ders kodu justification'da CSE4297, klasör adı CSE4398. Justification'da bahsedilen ayrı etkileşimli görselleştirme aracı klasörde yok.
- **Kuyruk modeli simetrisi:** Clustered tarafta M/M/c planlanıyor. Mainframe'de per-CP M/M/1 kullanılıyor. İki taraf aynı kuyruk ailesiyle modellenmeli.

### Sıradaki adım
Plan Hafta 1–2: Mainframe TCO genişletme (CICS, Db2, DS8900F, GDPS lisansı ayrı kalem, personel, 128 kademenin tamamı).

---

## 2026-10-31 — Oturum 1 (devam): Uçtan uca akademik değerlendirme

- **Aksiyon:** Düzeltmelerden sonra proje uçtan uca değerlendirildi ve "Bitirme projesi: uçtan uca akademik değerlendirme" dokümanına yazıldı. Dosya: `evaluations/2026-10-31_degerlendirme_01.md` (**Değerlendirme #1, tarih 2026-10-31**). Değerlendirme için statik modda 10K–250K TPS taraması yapıldı.
- **Sebep:** Emirhan'ın isteği. Başlangıçtaki belirsizlikler ve hatalar temizlendikten sonra, veri toplamaya geçmeden önce geçerlilik tehditlerini ve sıradaki adımları netleştirmek.
- **Ana bulgular:**
  1. Ortak birim sorunu: TPS iki tarafta farklı benchmark transaction'larına kalibre edilecek (CICS REDP-5320 ve TPC-C/HammerDB). Bir referans transaction tanımı gerekiyor. En büyük geçerlilik tehdidi bu.
  2. Mainframe maliyeti/TPS tarama boyunca neredeyse sabit ($1,92–2,18 /TPS/ay). Doğrusal $/MIPS ve sub-capacity faturası yüzünden "büyük ayrık adım" önermesi mevcut varsayımlarla ortaya çıkmıyor. Hipotez "sabit vs değişken maliyet yapısı" üzerine yeniden kurulmalı. Donanım "taban + MIPS başına" yapısında, MLC kademeli fiyat tablosuyla modellenmeli.
  3. Diğer konular: fiyat kaynaklarının kalitesi (A–D kalite notu önerisi), availability (×10 kuralının tek kaynağa dayanması, ITIC'in x86 için de kullanılması önerisi), migration ile kapsam arasındaki boşluk (başa baş süresi parametresi), 5 yıllık NPV ufku, stack daraltma yerine 8 kombinasyonun hepsini hesaplamak, personel maliyeti simetrisi, arıza modelinden önce Monte Carlo + tornado, dış doğrulama.
- **Önerilen sıra:** (1) Ön koşul kararları, (2) üç kişiye bölünmüş paralel veri toplama ve ortak kaynak kaydı, (3) ortak arayüzlü kod iskeleti, (4) clustered model, (5) tarama + belirsizlik, (6) dış doğrulama, (7) tez.
- **Bekleyen kararlar (Emirhan):** referans transaction, 8 kombinasyonun hepsi, Monte Carlo önceliği, migration parametresi, storage tipi.

---

## 2026-10-31 — Oturum 1 (devam): Klasör düzeni ve değerlendirme rutini

- **Aksiyon:** Dosyalar klasörlere ayrıldı: `docs/` (3 tasarım dokümanı), `src/` (model + test), `evaluations/` (tarihli değerlendirmeler). Kökte `PROJECT_LOG.md` ve yapıyı anlatan kısa bir `README.md` kaldı. Değerlendirme #1 `evaluations/2026-10-31_degerlendirme_01.md` olarak eklendi.
- **Sebep:** Emirhan'ın isteği. Değerlendirmeler tarihli ve numaralı tutulacak ki rutin değerlendirmelerle ilerleme izlenebilsin.
- **Değerlendirme rutini:** Her yeni değerlendirme `YYYY-MM-DD_degerlendirme_NN.md` adıyla eklenir ve bir öncekindeki tehditlerin hangilerinin kapandığını raporlar. Log'a da tarihiyle bir girdi düşülür.

| # | Tarih | Dosya | Durum özeti |
|---|---|---|---|
| 1 | 2026-10-31 | `evaluations/2026-10-31_degerlendirme_01.md` | Mainframe compute modeli düzeltildi; ortak birim ve crossover hipotezi kritik tehdit; clustered taraf yok |
| 2 | 2026-10-31 | `evaluations/2026-10-31_degerlendirme_02_mainframe.md` | Mainframe özel inceleme; kapasite köprüsünde sublinearite çift sayımı bulundu (TPS ~%29 eksik); maliyet eğrisi için taban fiyat + kademeli MLC + zIIP + CBU gerekli; M1–M8 yol haritası |
| 3 | 2026-10-31 | `evaluations/2026-10-31_degerlendirme_03_mainframe_ve_storage.md` | Compute katmanı sağlam (kademeler, köprü, CoD/TFP); storage dahil edilmeli (shared-disk vs shared-nothing, DR, CPU, latency asimetrisi); en büyük eksik yazılım yığını ve kademeli MLC; öncelik sırası |

---

## 2026-10-31 — Oturum 1 (devam): Değerlendirme #2 (mainframe)

- **Aksiyon:** Mainframe modeli uçtan uca incelendi ve `evaluations/2026-10-31_degerlendirme_02_mainframe.md` olarak yazıldı. Kademe TPS'leri, köprünün amaçladığı değerlerle karşılaştırıldı.
- **Sebep:** Emirhan'ın kararı: clustered tarafa ve transaction köprüsüne geçmeden önce mainframe artımlı olarak tamamlanacak. İkinci problem (düz maliyet eğrisi) de mainframe tarafında çözülecek.
- **Ana bulgu:** `cp_equivalents × BASE_TPS_PER_CP` n-way kaybını iki kez sayıyor. 3931-718'de model 173,6K TPS veriyor, köprünün amaçladığı değer ~244K (−%29). Önerilen düzeltme: LSPR birimi başına TPS (~4.444 TPS/LSPR). Henüz uygulanmadı, Emirhan'ın onayını bekliyor.
- **Sonraki adım:** Yol haritası M1–M8. M1 (köprü düzeltmesi) veri gerektirmiyor.

---

## 2026-10-31 — Oturum 1 (devam): Mainframe M1 + M2 (kademe tablosu ve kapasite köprüsü)

### 1. Kademe tablosunun doğrulanması ve tamamlanması (M2)
- **Sorun:** Modelde 28 temsili kademe vardı; dokümanlar "128 kademe = 4 seri × 32 CP" diyordu. Kaynak olarak gösterilen LSPR sayfası (node/6953823) aslında **z/VM 7.2** tablosuydu ve 32 CP'de kesiliyordu. Bu yüzden ~250K TPS'te yapay bir tek-sistem tavanı oluşuyordu.
- **Bulgu:** IBM z16 A01'de **317 kapasite seviyesi** var: 7xx serisinde 1–200 CP, 4xx/5xx/6xx serilerinde 1–39 CP (SG24-8950, z16 Technical Introduction).
- **Aksiyon:**
  - 4xx/5xx/6xx 1–39 ve 701–703 için PCI, MSU ve Low/Avg/High değerleri IBM LSPR ITRRs sayfasından alındı (120 satır).
  - 701–7K0 için resmî MSU değerleri IBM Mainframe Exhibit'ten (5/2/2025) alındı (200 satır).
  - 704–7K0 için PCI'ye kamuya açık sayfadan erişilemedi (sayfa 703'te kesiliyor). Bu yüzden PCI, bilinen satırlardaki MSU/PCI oran eğrisinden türetildi. Oran ~33.000 PCI'dan sonra 0,11723'te sabitleniyor.
  - **Doğrulama:** Birini dışarıda bırak testinde maks. hata %1,07. 3931-7K0 için türetilen 215.099 PCI, IBM'in yayımladığı 215.089 PCI ile %0,004 farkla örtüşüyor (K. Stine, z16 Technical Overview). Önceki sürümdeki 7xx oranları da (704/718/726/732) %0,1 içinde tutuyor.
  - Tablo koddan ayrıldı: `data/z16_a01_capacity.csv`. Ham veriler `data/raw/` altında, üretici script `src/tools/build_z16_capacity_table.py`.
  - Kademe başına **resmî MSU** kullanılıyor; sabit MSU/MIPS oranı (0,1225) kaldırıldı.
- **Kapsam kararı (Emirhan):** z16 A02/AGZ (3932, rack-mount) modelleri kapsam dışı; dokümanda belirtildi. 3931-400 (yalnızca CF) da hariç.
- **Sebep:** Değerlendirme #2, madde 1.2 ve 1.3.

### 2. Kapasite köprüsünde çift sayımın düzeltilmesi (M1)
- **Sorun:** `cp_equivalents × BASE_TPS_PER_CP` hesabı n-way kaybını iki kez sayıyordu. 3931-718 için köprünün amaçladığı ~244K yerine 173,6K TPS çıkıyordu (−%29). Değerlendirme #2, madde 1.1.
- **Aksiyon:** Köprü "PCI başına TPS" olarak yeniden kuruldu. REDP-5320'nin z13 TPS'leri, aynı sistemlerin PCI'sine (LSPR zOSv2r2: 2964-718 = 21.579, 2964-726 = 29.048) bölündü: 8,063 ve 7,815 TPS/PCI, ortalama **7,939**. İki nokta arasındaki %3,1 fark belirsizlik aralığı olarak raporlanıyor.
- **Sonuç:** 3931-718 = 240K TPS ham (köprünün amacıyla %2 içinde). En büyük kademe 3931-7K0 = ~1,7M TPS ham. Önceki 250K tavanı kalktı.

### 3. Etkileri (yeniden hesaplanan sonuçlar)
- **Model daha küçük ve daha yavaş CP'li kademeler seçiyor:** 50K TPS'te 3931-608 ($101K/ay) yerine 3931-436 ($72K/ay). Alt-kapasite serileri 39 CP'ye kadar uzandığı için birçok yük artık 4xx/5xx ile karşılanıyor.
- **Latency daha anlamlı hale geldi:** Yavaş alt-kapasite CP'leri yüzünden 20 ms ve altındaki hedefler kademe seçimini değiştiriyor (ör. 50K TPS'te latency yokken 436, 20 ms'de 509, 5 ms'de 704). Önceki "yalnızca tek haneli ms'de bağlayıcı" bulgusu güncellendi.
- **Maliyet/TPS:** 25K TPS'in üstünde ~$1,35–1,50/TPS/ay ve neredeyse düz. Değerlendirme #2'deki maliyet yapısı (M4) ihtiyacı devam ediyor.
- **Yıllık (50K TPS):** retail_bursty $2,13M (CoD, %27,8 tasarruf), batch_heavy $1,80M (CoD, %17,6), steady_oltp $1,39M (Permanent, %0,9).
- **Testler:** Mevcut latency testi yeni kademelerle güncellendi (50K TPS). İki yeni test eklendi: kademe tablosunun bütünlüğü, köprünün kendi çapalarını ve 7K0'ı üretmesi. 6/6 test geçiyor.

### 4. Dokümantasyon
- `docs/mainframe_model_documentation_v3.md` yazıldı. Modelin güncel halini anlatıyor; düzeltme notu olarak değil, temiz bir tanım olarak. v2 tarihsel kayıt olarak değiştirilmeden duruyor.
- Koddaki "DÜZELTME" yorumları kaldırıldı; kod yalnızca güncel yöntemi anlatıyor, tarihçe bu log'da.

### 5. Yeni fark edilen açık noktalar
- **On/Off CoD üst sınırı (doğrulanmalı):** IBM, geçici kapasiteyi kalıcı kapasiteye göre sınırlıyor (yaygın olarak ~2×). Modelde bu sınır yok; retail_bursty'deki 515 → 624 geçişi ~2,3×. SC28-7025'ten doğrulanmalı.
- **Enerji:** 39 CP üstü kademeler birden fazla drawer/rack gerektiriyor, ama enerji hâlâ frame başına 30 kW. IMPP belgesiyle düzeltilmeli.
- **RNI kavramı:** LSPR'nin Low/High RNI etkisi dar (+%15/−%10), modelin çarpanı geniş (1,25/0,70) ve transaction başına iş miktarını da temsil ediyor. İki kavram ayrılmalı.
- z13 ve z16 LSPR değerleri farklı tablo sürümlerinden (zOSv2r2 ve güncel ITRR).

### Değerlendirme #2 durum güncellemesi
- **Kapanan:** 1.1 (çift sayım), 1.2 (kademe tablosu ve yapay tavan), 1.3 (sabit MSU/MIPS).
- **Kısmen:** 1.4 (LSPR RNI sütunları tabloda var ama modelde kullanılmıyor; kavram ayrımı gerekiyor).
- **Açık:** 1.5 (REDP iş yükü profili), 3 (maliyet yapısı, zIIP, CBU), 4 (availability), 5 ve 6.

---

## 2026-10-31 — Oturum 1 (devam): Güncel IBM Z fiyatlama modeli (base + corridor + On/Off CoD)

### 1. Araştırma
- **Aksiyon:** IBM'in güncel donanım edinim modeli araştırıldı. Kaynaklar: SC28-7025 (Capacity on Demand User's Guide), IBM Z Content Solutions "Tailored Fit Pricing" sayfası, IBM IT Economics TFP for IBM Z Hardware maliyet çalışması (Mayıs 2021), DBTA/NetworkWorld duyuruları, TFP Software Consumption Solution özetleri.
- **Sebep:** Emirhan'ın tespiti: modeldeki fiyatlama güncel değil; güncel model base capacity + hardware corridor + CoD. Ayrıca CoD'nin üst sınırının 2× olmadığını düşünüyordu.
- **Bulgular:**
  - **Corridor (TFP-HW, Hardware Consumption Solution):** satın alınan kapasitenin üstünde her zaman açık, abonelik tabanlı, kullandıkça öde kapasite. Ücret, base'in üstünde fiilen tüketilen MSU üzerinden, SCRT ile saatlik ölçülerek kesiliyor. Ön koşul: z15+, z/OS genel amaçlı CP ve yazılımda Software Consumption Solution. IBM'in örnek corridor'u yeni iş yükünün %20'si. Corridor fiyatı ve boyut kuralı yayımlanmıyor.
  - **On/Off CoD sınırı:** SC28-7025'e göre geçici kapasite "satın alınan kapasitenin %100'üne kadar". Ancak ayrıca kurulu fiziksel kapasiteyle (drawer eklenemez) ve alt-kapasite seviye kurallarıyla sınırlı. Yani resmî tavan 2× olsa da drawer'ı dolduran base'lerde pratik tavan çok daha düşük (ör. 735 → en fazla 739, +%11). Emirhan'ın sezgisi pratikte büyük base'ler için doğru; küçük base'lerde %100 kuralı bağlayıcı.
  - **TFP-SW:** IBM efektif MSU fiyatını geçmiş 12 aydan belirliyor; yıllık MSU taahhüdü, büyüme için indirimli fiyat, R4HA yok.

### 2. Modele uyarlama
- **Aksiyon:** Yıllık simülasyon üç stratejiye genişletildi: A) Permanent, B) Base + On/Off CoD, C) Tailored Fit Pricing (base + her zaman açık corridor + corridor'u aşan günlerde CoD, yazılım MSU-saat tüketimiyle).
  - CoD artık her gün, günün tepesini karşılayan en küçük izinli kademeyi aktive ediyor (sabit tek bir "peak kademe" yerine).
  - Geçici hedefler SC28-7025 kurallarıyla sınırlı: MSU ≤ 2 × base MSU, CP ≤ kurulu drawer özelliği (varsayılan base'i taşıyan en küçük özellik), seri kuralları.
  - Corridor ücreti: base'in üstünde tüketilen PCI × PCI-saat donanım maliyeti × CORRIDOR_PREMIUM (1,5 [ASSUME]). Corridor genişliği base MSU'nun %20'si (IBM örneği).
  - TFP-SW: gelir-nötr kalibrasyon (Permanent konfigürasyonun R4HA faturası / aynı yılın MSU-saati).
  - Çok-frame topolojilerde geçici kapasite ücretleri tek frame için (ikinci frame failover; CBU yol haritasında).
  - `src/tools/pricing_sensitivity.py` eklendi.
- **Sebep:** Modelin güncel IBM ticari modelini temsil etmesi; aksi halde CoD avantajı ya fiziksel olarak imkânsız konfigürasyonlara dayanıyordu ya da corridor seçeneği hiç görünmüyordu.

### 3. Etkileri
- **%100 kuralı önceki sonucu geçersiz kıldı:** retail_bursty'de önceki model base 515 (1.351 MSU) → 624 (3.059 MSU) geçişi kullanıyordu; bu resmî kurala göre mümkün değil. Yeni model base'i 518'e çıkarıyor; B stratejisinin maliyeti $2,13M'den $2,20M'ye yükseldi.
- **Yeni sonuçlar (50K TPS, M1):** steady_oltp C $1,249M (A'ya göre −%10,5); retail_bursty C $2,201M (−%25,3; B ile fark %0,1); batch_heavy C $1,662M (−%23,7).
- **Bulgu:** Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanı. steady_oltp'de B 261 gün CoD gerektirdiği için A'dan pahalı; C bu tepeleri ucuza emiyor.
- **Duyarlılık:** steady ve batch'te TFP'nin üstünlüğü taranan tüm aralıkta korunuyor. retail_bursty'de B ile C arasındaki seçim fiyat varsayımlarına duyarlı (±%2). Permanent hiçbir noktada kazanmıyor.
- Yazılım toplamın %42–57'si; fiyatlama stratejisi yalnızca donanım kalemini yeniden dağıtıyor, maliyet/TPS düzlüğü sorunu devam ediyor (M4).
- **Testler:** 3 yeni test (geçici kapasite kuralları, seçilen konfigürasyonların kurallara uyması, TFP-SW gelir-nötrlüğü ve corridor monotonluğu); burstiness testi üç stratejiye uyarlandı. 9/9 geçiyor.
- **Dokümantasyon:** v3 Bölüm 8 yeniden yazıldı (8.4 edinim modeli, 8.5 resmî sınırlar, 8.6 üç strateji, 8.7 doğrulama, 8.8 duyarlılık); referanslar ve eksikler güncellendi.

### 4. Açık noktalar
- Drawer maliyeti olmadığı için drawer özelliği karar değişkeni değil; maliyet yapısı adımıyla (M4) birlikte açılmalı.
- Corridor fiyatı, abonelik bedeli ve corridor genişliği müşteriye özel; gerçek bir sözleşme/IBM teklifinden kalibrasyon mümkünse yapılmalı.
- On/Off CoD kaydının 180 gün sınırı ve tek-aktif-kayıt kuralı modellenmedi.
- TFP-SW'nin büyüme fiyatı tek yıllık ufukta görünmüyor; 5 yıllık NPV adımında (M8) modellenmeli.

---

## 2026-10-31 — Oturum 1 (devam): Değerlendirme #3 (mainframe eksikleri ve storage)

- **Aksiyon:** Mainframe modelinin güncel hali yeniden değerlendirildi ve storage katmanının projeye dahil edilip edilmeyeceği sorusu incelendi. `evaluations/2026-10-31_degerlendirme_03_mainframe_ve_storage.md` yazıldı.
- **Sebep:** Emirhan'ın sorusu: storage iki tarafta da paralel değil mi, bir bitirme projesinde dahil olmalı mı?
- **Sonuç:**
  - Storage dahil edilmeli. "Paralel" argümanı yalnızca iki taraf aynı storage'ı aynı maliyetle kullansa geçerli olurdu. Gerçekte shared-disk (mainframe) ile shared-nothing (clustered DB'lerin bir kısmı) farklı kopya sayısı, farklı DR katmanı, farklı I/O CPU maliyeti ve farklı I/O gecikmesi demek. Ayrıca veri hacmi ekseninde ikinci bir crossover boyutu açabilir. Projenin kendi gerekçesi de storage'ı tam yığın tanımına dahil ediyor.
  - Storage iki taraf için ortak bir arayüzle (data_volume_tb, data_growth_pct, RNI'dan IOPS, RPO) ve sade tutulacak.
  - En büyük mainframe eksiği yazılım yığını (CICS, Db2, kademeli MLC, zIIP). Önerilen sıra: yazılım yığını, storage arayüzü + DS8900F, personel, donanım tabanı + CBU + GDPS, 5 yıllık NPV. Transaction köprüsü paralel.
  - Açık karar: clustered tarafta storage tipi (öneri: DB mimarisine bağlı; shared-disk → SAN, shared-nothing → yerel NVMe × RF).

---

## 2026-11-01 — Oturum 2: Mainframe storage katmanı (IBM DS8900F)

### 0. Ortam
- Emirhan projeyi yeni bilgisayara GitHub üzerinden klonladı (`Ehan0022/CSE4398`, proje yolu `CSE4398/Work_Emirhan`). Repo, önceki oturumun son hali ile karşılaştırıldı: yalnızca Değerlendirme #3 ve log'daki ilgili girdi eksikti (önceki bilgisayar çevrimdışı olduğu için yazılamamıştı); bu oturumla birlikte eşleniyor.

### 1. Veri toplama
- **Aksiyon:** DS8900F için resmî ve ikincil kaynaklardan teknik ve fiyat verisi toplandı: IBM DS8900F Product Guide (REDP-5554, R9.3.2), IT Candor (IOPS), TechTarget (başlangıç fiyatları, zHPF süresi, pazar payı), IT Jungle (IBM duyurusu 322-396 flash liste fiyatı), kurumsal storage fiyat karşılaştırmaları (indirim ve destek aralıkları).
- **Bulgular:**
  - Modeller: DS8910F-993 (z16 çerçevesine 16U monte, 737 TB ham), DS8910F-994 (2.949 TB), DS8950F-996 (5.898 TB, E96 ile); maks. IOPS 860K / 2.320K; tepe güç 2,2 / 4,6 / 6,2 (+3,9) kW.
  - Fiyat: başlangıç $134K (DS8910F), $196K (DS8950F) [2019]; 15,36 TB flash liste $8,62/GB [2022]. İndirim, lisans ve bakım fiyatları yayımlanmıyor.
  - Lisanslar: Base Function, z-synergy Services (FICON, PAV, zHPF, zHyperLink), Copy Services (FlashCopy, Safeguarded Copy, Metro/Global Mirror); TB başına kademeli.
  - Gecikme: zHyperLink < 20 µs (~18 µs), zHPF/FICON ~90 µs.
- **Sebep:** Emirhan'ın isteği: mainframe storage maliyetleri ve mainframe'e özgü storage özellikleri modele eklensin. Değerlendirme #3'teki öncelik sırası.

### 2. Modele ekleme
- **Aksiyon:**
  - `data/ds8900f_models.csv` (kaynaklı model kataloğu) ve `mainframe_model.py` BÖLÜM 6 (storage) eklendi.
  - Boyutlandırma: veri × büyüme (3 yıl) × Db2/z/OS ek yükü / host sıkıştırma / RAID 6; birincil dizide Safeguarded Copy rezervi; kopya sayısı topolojiden (M1 1, M2 2, M3 4, M4 4); IOPS = tepe TPS × IOPS/işlem; kopya başına en ucuz model ve dizi sayısı.
  - Maliyet: (flash liste + kontrolcü liste) × (1 − indirim) + lisans oranı; 5 yıl amortisman, garanti sonrası bakım, tepe güçle enerji.
  - Latency: sabit 0,3 ms/I/O kaldırıldı. I/O süresi artık storage yolundan hesaplanıyor (okuma/yazma, önbellek isabeti, zHyperLink, zHPF/FICON, senkron Metro Mirror mesafe gecikmesi). Latency fonksiyonları topolojiyi alıyor; senkron kopyalı topolojilerde yazma gecikmesi artıyor.
  - `solve` ve `solve_yearly` storage'ı topoloji başına hesaplayıp toplama ekliyor; CLI'ya `--data-tb` ve `--data-growth` eklendi. `src/tools/storage_sensitivity.py` eklendi.
- **Sebep:** Projenin tam yığın TCO iddiası ve "storage iki tarafa ortak arayüzle" kararı (Değerlendirme #3). Mainframe'e özgü yapılar (shared-disk, storage tabanlı replikasyon, zHyperLink, I/O'nun SAP'lerde işlenmesi, Safeguarded Copy) modelde açıkça temsil edilmeli.

### 3. Etkileri
- **D_io:** average RNI'da 3,0 ms'den M1'de 0,69 ms'ye, M2–M4'te 1,29 ms'ye indi. Latency daha az bağlayıcı: 50K TPS'te 5 ms hedefte 3931-704 yerine 3931-510 seçiliyor; infeasible eşiği 0,69 ms.
- **Storage maliyeti (50K TPS, 20 TB, %99,9):** 1× DS8910F-993, $7.496/ay, toplamın %9,4'ü. M4'te 4 kopya ile $26.344/ay (%17,7).
- **Veri hacmi ekseni:** 500 TB'ta storage toplamın %68'i, 2.000 TB'ta %89,5'i. Compute sabitken storage veri hacmiyle doğrusal büyüyor: veri hacmi ekseninde ikinci bir crossover beklentisi mainframe tarafında doğrulandı.
- **IOPS:** 90K TPS üstünde (900K IOPS) DS8950F gerekiyor; IOPS_PER_TX = 10 varsayımı model seçimini doğrudan etkiliyor ve büyük olasılıkla yüksek.
- **Yıllık:** storage toplamın %3–7'si; strateji sıralaması değişmedi (C: TFP kazanıyor).
- **En büyük belirsizlik:** indirim oranı (0,50–0,85 aralığında storage maliyeti ~3 kat değişiyor).
- **Testler:** storage testi eklendi, latency testinin infeasible eşiği storage'tan gelen D_io'ya bağlandı. 10/10 geçiyor.
- **Dokümantasyon:** v3'e yeni Bölüm 8 (Storage Katmanı) eklendi; sonraki bölümler 9–12 olarak yeniden numaralandı; latency, girdiler, referanslar, eksikler güncellendi.

### 4. Açık noktalar
- Gerçek bir DS8900F teklifiyle indirim ve lisans oranlarının kalibrasyonu.
- GDPS kopya sayılarının GDPS Redbook'tan doğrulanması; uzun mesafe DR hattı maliyeti (storage ağı kapsam dışı kararı GDPS adımında yeniden ele alınmalı).
- IOPS_PER_TX'in REDP-5320 iş yükü profiliyle kalibrasyonu.
- TS7700 yedekleme, drive katmanı (Tier 0/1), DS8000 G10.
