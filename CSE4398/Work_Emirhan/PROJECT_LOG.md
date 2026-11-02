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
| 4 | 2026-11-01 | `evaluations/2026-11-01_degerlendirme_04_mainframe.md` | Storage katmanı yerinde ve savunulabilir (veri hacmi crossover ekseni, düşük TPS'te eğri bükülmesi); storage'da IOPS tavanı yok; IOPS_PER_TX üçlü rolüyle en etkili varsayım; yazılım yığını ve personel hâlâ eksik |
| 5 | 2026-11-01 | `evaluations/2026-11-01_degerlendirme_05_denetim.md` | Mainframe model ve kodunun bağımsız denetimi; 3 model hatası (frame tabanı, profil oranı, geçici kapasitede zIIP) ve 6 tutarlılık/kod hatası düzeltildi; 6 nokta bilinçli tercih olarak belgelendi; 10K TPS mid $83,32 → $84,06; kazanan stratejiler değişmedi |
| 6 | 2026-11-02 | `evaluations/2026-11-02_degerlendirme_06_yedek_ve_npv.md` | Adım 5: TS7770 yedekleme ve 5 yıllık NPV; NPV, r = 0'da amortismanlı modelle tam örtüşüyor; statik ölçü 5 yıllık sonucun iyi yaklaşığı (+%0,9) ama aralık genişliyor (high $341 → $409); 5 yılda TFP kazanıyor (büyüme fiyatına koşullu); drawer maliyetinin önceliği yükseldi. Ek: yedekte on-prem nesne depolama ve AWS S3 seçenekleri; 10K TPS $84,62, M1 geri yükleme kısıtı ~360 TB üstünde TS7770 seçtiriyor |

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

---

## 2026-11-01 — Oturum 2 (devam): Storage katmanının savunması ve Değerlendirme #4

### 1. Savunma
- **Aksiyon:** v3 dokümanına "8.1. Katmanın Savunması" eklendi (mevcut storage alt bölümleri 8.2–8.9 olarak yeniden numaralandı). İçerik: storage'ın TCO'ya neden dahil olduğu (birbirini götürmeme koşulu ve modelin doğruladığı veri hacmi ekseni), neden tek alternatif olarak DS8900F, her modelleme kararının alternatifi ve gerekçesi, her varsayımın dayanağı, taranan aralığı ve kalibrasyon yolu, geçerlilik tehditleri, clustered tarafla eşleştirme.
- **Sebep:** Emirhan'ın isteği: katmanın detaylı savunması model dokümanında olsun. Önceden gerekçeler Değerlendirme #3 ve v3'ün farklı bölümlerine dağılmıştı.

### 2. Değerlendirme #4
- **Aksiyon:** `evaluations/2026-11-01_degerlendirme_04_mainframe.md` yazıldı.
- **Ana bulgular:**
  - Storage katmanı kaynak kalitesi ve mainframe'e özgü mekanizmalar açısından sağlam. Availability'yi veri yolu üzerinden maliyet ve latency'ye bağlıyor.
  - Storage veri hacmine bağlı sabit bir maliyet gibi davrandığı için maliyet/TPS eğrisi düşük TPS'te büküldü ($6,45/TPS @2K → $1,38 @500K, 20 TB sabit). Bu sabit veri hacmi varsayımına bağlı; tezde böyle sunulmalı.
  - Yeni tutarsızlık: storage dizileri üretici tepe IOPS'unun %100'üne göre boyutlanıyor; compute'taki %90 tavana karşılık storage'da tavan yok.
  - IOPS_PER_TX artık latency'yi, storage IOPS'unu ve dizi modelini birlikte belirliyor; REDP-5320 iş yükü profili öne çekilmeli.
  - Eşit derinlik: yazılım yığını ve personel olmadan clustered tarafa geçmek karşılaştırmayı mainframe lehine yanlı yapar.
  - Kod tek dosyada ~1.500 satır; clustered tarafa geçmeden ortak parçalar ayrı modüle taşınmalı.
- **Önerilen sıra:** storage IOPS tavanı → yazılım yığını (kademeli MLC, CICS, Db2, zIIP) ve paralel REDP-5320 profili → personel → CBU + GDPS → ortak modül ayrımı, 5 yıllık NPV.

---

## 2026-11-01 — Oturum 2 (devam): Plan ve storage IOPS tavanı

- **Plan:** Emirhan'ın isteğiyle kısmen olan ve eksik kalemler için sıralı plan çıkarıldı: (0) storage IOPS tavanı, (1) yazılım yığını (z/OS + CICS + Db2, kademeli MLC, zIIP), (2) REDP-5320 iş yükü profili, (3) personel, (4) availability (CBU, GDPS kalemi, RPO/RTO, M4 etiketleri), (5) yedekleme ve 5 yıllık NPV, (6) ortak modül ayrımı. Sıra Emirhan'a soruldu; 0. adım her seçenekte ilk olduğu için başlandı.
- **Aksiyon (0):** `STORAGE_IOPS_CEILING = 0,70` [ASSUME] eklendi; dizi sayısı tepe IOPS'un %70'ine göre hesaplanıyor.
- **Sebep:** Değerlendirme #4, madde 2.1: compute'ta %90 operasyonel tavan varken storage üretici tepe IOPS'unun %100'üyle boyutlanıyordu.
- **Etki:** DS8910F → DS8950F geçişi 90K yerine ~60K TPS'te. Yıllık modda (50K ort.) steady_oltp 1× DS8950F'e, retail_bursty 2× DS8950F'e geçti; toplamlar +$11K / +$28K. Strateji sıralaması değişmedi. Testler 10/10. v3 Bölüm 8.1.3, 8.1.5, 8.4, 8.7, 9.7, 9.8 güncellendi.

---

## 2026-11-01 — Oturum 2 (devam): Yazılım yığını (AWLC kademeli MLC) ve zIIP — Plan adımı 1

### 1. Veri toplama
- **Aksiyon:** IBM AWLC/MLC fiyatlaması için kaynak tarandı: IBM'in yayımladığı Db2 kademe fiyatları ve örnek sub-capacity faturası (2004), zNALC belgesi ve CMG 2020 (güncel kademe sınırları, kümülatif fiyatlama), Longpela (L7/L6 oranı), value-4it (150 MSU ≈ £1M/yıl), z17 Technology Update indirimleri (TU11), zIIP kuralları.
- **Bulgu:** Modeldeki $40/MSU/ay tek fiyatı hem yapı olarak (AWLC doğrusal değil, kümülatif kademeli) hem seviye olarak yanlıştı: IBM örneğinde yalnızca z/OS 265 MSU'da $75.459/ay (~$285/MSU). Kaynak (atonementlicensing.com) metodolojisizdi.
- **Sebep:** Plan adımı 1; Değerlendirme #4'ün eşit derinlik bulgusu (CICS ve Db2 eksikti).

### 2. Modele ekleme
- **Aksiyon:**
  - `software_monthly_cost(msu)`: Db2 referans eğrisi (Base $3.960, L0 $208, L1 $88, L2 $66, L3 $50; L4+ ×0,80/kademe [ASSUME]) × ürün katsayıları (IBM örneğine kodda kalibre: z/OS ×2,509, CICS TS ×1,247, Db2 ×1,060) × SW_PRICE_LEVEL_FACTOR (1,0 = 2004 nominal [ASSUME]).
  - zIIP: ZIIP_OFFLOAD_FRACTION = 0,10 [ASSUME, muhafazakâr]. GP kademesi 1/(1−f) kat TPS taşıyor, CoD/corridor'da tüketilen PCI (1−f) ile ölçekleniyor; zIIP motor sayısı ⌈PCI·f/(1−f)/2.253⌉ (2:1 sınırlı), bedeli GP fiyatının 0,25'i [ASSUME] olarak donanıma ekleniyor.
  - `SOFTWARE_COST_PER_MSU_MONTH` kaldırıldı. TFP-SW gelir-nötr kalibrasyonu değişmeden çalışıyor.
  - `src/tools/software_sensitivity.py` eklendi; yeni test `test_awlc_software_stack_and_ziip` (11/11 geçiyor).
- **Sebep:** Kademe sınırları ve düşüş eğrisi resmî kaynaktan, mutlak seviye kalibre + taranan parametre; böylece güncel fiyatın gizli olması sonucu tek bir sayıya bağlamıyor.

### 3. Etkileri
- **Maliyet/TPS eğrisi büküldü:** $44,95 (1K TPS) → $5,89 (50K) → $2,28 (1M). Önceden 25K üstünde düzdü (~$1,35–1,44). Değerlendirme #1'in "düz eğri, zayıf crossover hipotezi" tehdidine kaynaklı bir mekanizmayla cevap.
- **50K TPS statik:** $75.655 → $294.278/ay; yazılım payı %37 → %84. Kademe seçimi 3931-436 → 3931-432 (zIIP ve düşük MSU avantajı).
- **Yıllık (50K ort.):** steady C $4,576M, retail **B** $6,618M (C ile fark %0,4), batch C $5,690M. Stratejiler arası fark %10–24'ten %2,5–10'a indi; yazılım %76–86. TFP_SW_DISCOUNT'un %5'i C'yi her presette öne geçiriyor: strateji kararını donanım değil TFP-SW yazılım fiyatı belirliyor.
- **Storage payı:** 20 TB'da %9,4 → %2,5; veri hacmi ekseni ~500 TB'ta belirginleşiyor (%35).
- **Duyarlılık:** mutlak seviye 0,5–1,5 → 50K TPS'te $3,42–8,35/TPS (şekil aynı, crossover yeri kayar); L4+ düşüş oranı 500K TPS'te $/TPS'i 2 kat oynatıyor (2,06–4,12) → yüksek hacimde en kritik yazılım varsayımı.
- **Dokümantasyon:** v3 §7.1 yeniden yazıldı (savunma, veri, formül, doğrulama, zIIP, duyarlılık); §1.2, 1.4, 2.2, 7.2, 7.5, 7.6, 8.1.3, 8.7, 9.7, 9.8, 10, 11.5, 12.1, 12.3 güncellendi.

### 4. Açık noktalar
- L4+ kademe fiyatları ve güncel mutlak seviye için gerçek AWLC tablosu veya teklif.
- zIIP payının REDP-5320 profiliyle daraltılması (benchmark zIIP kullanmıyor).
- Donanım fiyatı ($200/PCI) artık yazılıma göre en kaba kalem; personel eklenmeden yazılım payı olduğundan yüksek görünüyor.
- TFP gelir-nötr kalibrasyonunda kademe MSU/PCI oranı farkından kaynaklanan ~%1'lik artefakt.

---

## 2026-11-01 — Oturum 2 (devam): Bileşimli iş yükü profili — Plan adımı 2

### 1. REDP-5320 profili
- **Aksiyon:** Benchmark raporunun sayaç tablolarından işlem profili çıkarıldı ve `data/raw/redp5320_workload_profile.csv` olarak kaydedildi.
- **Bulgu:** Köprü işlemi çok hafif. İşlem başına 4,76 bellek okuması (CICS shared data table), 0,047 güncelleme, 0,062 CF log yazımı ve 85,9 µs CPU (z13) var. Db2, Java ve zIIP yok; DASD I/O neredeyse sıfır. Model ise kapasiteyi bu işlemle hesaplarken latency ve storage için 10 I/O/işlem varsayıyordu: tutarsızdı ve mainframe kapasitesini olduğundan yüksek gösteriyordu.
- **Ek kanıt:** Bir sahada CICS-Db2 işleminin Db2 CPU'su ~1,3 ms ölçülmüş [CATTERALL-2019], yani REDP işleminin ~15 katı. CICS'te tek INSERT ~68 µs [CATTERALL-2012].
- **Karar (Emirhan, karar kartı):** "1 işlem" bileşimle tanımlanacak (seçenek A: bileşimli profil).

### 2. Modele ekleme
- **Aksiyon:**
  - RNI çarpanları (1,25/1,00/0,70) ve IOPS_PER_TX (5/10/20) kaldırıldı; kaynakları yoktu.
  - `WorkloadProfile`: okuma SQL, yazma SQL, commit. CPU = 85,9 + 30·okuma + 70·yazma µs, w = CPU/85,9. Senkron I/O = okuma·4·(1−0,95) + 1; IOPS = senkron + 0,5·yazma.
  - Profiller: redp_light (ölçülmüş, w = 1), tpcb_like (w = 4,61), **oltp_rw** (sysbench oltp_read_write bileşimi, w = 9,15, varsayılan), oltp_heavy (w = 16,37).
  - zIIP yalnızca Db2'li profillerde. CLI: `--workload`, `--sql-reads`, `--sql-writes`.
  - Yeni araç `src/tools/workload_sensitivity.py` ve yeni test `test_workload_profiles` (12/12 geçiyor). Diğer araçların ve testlerin referans noktası 10K TPS'e indi.
- **Sebep:** Değerlendirme #1'in en kritik tehdidi (TPS iki tarafta ortak birim değil). Clustered taraf aynı bileşimi kendi ölçümleriyle karşılayacak.

### 3. Etkileri
- **Kapasite:** oltp_rw aynı TPS için ~9 kat kapasite istiyor. Önceki "50K TPS", bugünkü birimle ~5,5K oltp_rw TPS. Tek z16 tavanı oltp_rw'de ~187K TPS, oltp_heavy'de ~104K.
- **Makullük:** IBM'in z14 için duyurduğu günde 12 milyar işlem, w ≈ 9'a karşılık geliyor (z14 PCI tahmini, doğrulanmalı).
- **Maliyet (statik, oltp_rw):** 10K TPS'te $416.750/ay ($41,68/TPS); $/TPS 500 TPS'te 174,8'den 180K TPS'te 19,8'e iniyor. Ölçek ekonomisi ~20K TPS'e kadar; L4+ kademe varsayımı artık ~4K TPS'ten itibaren bağlayıcı.
- **I/O:** D_io M1'de 0,26 ms (önceden 0,69); DS8950F geçişi ~104K TPS'e kaydı; storage payı 20 TB'da %1,8.
- **Latency:** oltp_rw'de p99 alt sınırı ~2,4 ms; 5 ms hedef 7xx kademesine kaydırıyor.
- **Yıllık (10K ort.):** steady C $6,435M, retail B $9,534M (C ile fark %0,2), batch C $7,981M; TFP_SW_DISCOUNT %5 → C her presette kazanıyor.
- **Yeni sınırlama:** İkinci frame kapasite eklemediği için Parallel Sysplex ile tek CEC ötesine ölçekleme yok. Yol haritasına eklendi.
- **Dokümantasyon:** v3 §4.3–4.5 (yeni §4.4 İş Yükü Profili, savunmasıyla), §2.1, §5.3–5.5, §7.1.6, §7.6, §8.1, §8.4, §8.6–8.8, §9.5, §9.7–9.8, §10, §11.1, §12 güncellendi.

### 4. Açık noktalar
- CPU_US_PER_SQL_READ (30 µs) en kritik profil varsayımı: 15–60 µs, 10K TPS'te maliyeti $349K–533K arasında oynatıyor. IRWW veya gerçek bir SMF 101 örneği ikinci çapa olur.
- Parallel Sysplex ölçeklemesi (çok CEC, data sharing ek yükü).
- Clustered tarafın oltp_rw bileşimini hangi ölçümle karşılayacağı (sysbench sonuçları).

---

## 2026-11-01 — Oturum 2 (devam): Personel ve aralık çıktısı — Plan adımı 3

### 1. Araştırma
- **Aksiyon:** Mainframe altyapı personeli için FTE oranları ve ücretler toplandı.
- **FTE kaynakları:**
  - IBM Eagle TCO ekibi, 17 müşteri: 5 FTE + her 625 MIPS için 1 FTE.
  - Gartner ITKMD 2016 (CA/Broadcom yayını üzerinden): kurulu MIPS/FTE 152 → 268.
  - Gartner (IBM 2007 sunumunda): ekip sabitken MIPS iki katına çıktı. IBM örneğinde 3.192 MIPS ≈ 4 FTE.
- **Ücret kaynakları:** BLS OEWS Mayıs 2025 medyanları (DBA/mimar $126.760, sistem yöneticisi $99.130, güvenlik $129.180); Payscale ve Glassdoor mainframe aralıkları; yan hak IDC %28 ve BLS ECEC %30 (×1,43).
- **Sebep:** Plan adımı 3. Emirhan'ın yönlendirmesi: kesin rakamlar yerine kaynaklı aralıklara odaklanılsın, çünkü final çıktı bir aralık olacak.

### 2. Modele ekleme
- **Personel:**
  - FTE = max(taban, FTE_1000·(PCI/1000)^b) × topoloji çarpanı.
  - low / mid / high = (4; 0,60; 3) / (5,5; 0,70; 4) / (7; 0,80; 5); yüklü maliyet $122K / $162K / $215K.
  - Eğriler IBM Eagle (küçük kurulum) ile Gartner 2016 ortalamasını ve 2026'ya taşınmış eğilimini sarmalayacak şekilde kalibre edildi.
  - Topoloji çarpanları: M2 1,05, M3 1,15, M4 1,25.
  - Yıllık modda personel, tepe yükü taşıyan kademeye göre hesaplanıyor; stratejiden bağımsız.
- **Aralık çıktısı:**
  - `RANGE_PARAMETERS` 9 parametre içeriyor: personel, AWLC seviyesi, L4+ düşüşü, okuma/yazma SQL CPU, zIIP, donanım $/PCI, storage indirimi, BP isabeti.
  - `solve_range`: tüm parametreler aynı anda low / mid / high; kademe yeniden optimize ediliyor.
  - `range_tornado`: tek-parametre salınımı. CLI `--range`.
  - `src/tools/range_curve.py`: maliyet/TPS aralığı ve `data/out/` CSV'si.
- **Refaktör:** AWLC L4+ kademeleri `AWLC_UPPER_DECAY`'den hesaplanıyor (aralık için).
- **Test:** `test_staff_and_ranges` eklendi (13/13 geçiyor).

### 3. Etkileri
- **10K TPS, oltp_rw:** mid $833K/ay ($83,3/TPS), aralık $26,2–288,5/TPS (köşeler). Mid'de personel 30,8 FTE, toplamın %50'si; yazılım %41.
- **Tornado (10K TPS):** en büyük salınım personelde ($595K–1,32M), sonra okuma SQL CPU ($684K–1,10M), AWLC seviyesi ($663K–1,00M). Storage ve BP isabeti maliyeti neredeyse oynatmıyor.
- **Eğri:** mid $/TPS 500 TPS'te 300,6'dan 150K TPS'te 38,3'e iniyor. Şekil üç senaryoda da aynı; crossover'ın yeri varsayımlara çok duyarlı → tezin çıktısı bir crossover bölgesi olmalı.
- **Çapraz kontrol:** Gartner 2016 MIPS başı yıllık maliyet $3.057, eğilimle 2026'ya taşınınca ~$940. Model 10K TPS'te $553 / $851 / $1.426 / PCI / yıl veriyor (ISV yazılımı ve tesis hariç).
- **Yıllık (10K ort.):** personel %51–56; strateji sıralaması değişmedi (steady C, retail B %0,1 farkla, batch C).
- **Dokümantasyon:** v3 yeni §7.7 (Personel, savunmasıyla) ve §7.8 (Aralık Çıktısı); §1.2, 1.4, 2.2, 4.4.4, 5.5, 7, 7.1.6, 7.5, 7.6, 8.1, 8.7, 9.7, 9.8, 10, 11.5, 12 güncellendi.

### 4. Açık noktalar
- Aralıklar köşe değerleri; olasılıklı aralık için Monte Carlo (dağılım ve korelasyon) gerekli.
- Personel ABD ücretleriyle; farklı pazar (Türkiye) için ayrı set.
- Clustered tarafta aynı kapsam (tüm altyapı ekibi) ve aynı aralık yaklaşımı uygulanmalı.

## 2026-11-01 — Oturum 2 (devam): Dokümantasyonun sıfırdan okunabilirlik denetimi

- **Eylem:** v3 dokümanı, modeli hiç bilmeyen bir okur gözüyle baştan sona okundu. Başa **Bölüm 0 (Okuma Kılavuzu)** eklendi:
  - 0.1: bir sorgunun 7 adımlık akışı (iş yükü → kapasite → availability → latency → storage → maliyet → aralık), her adımın bölüm referansıyla.
  - 0.2: 10K TPS oltp_rw örneğinin her adımdaki gerçek sayıları (w 9,15 → 3931-516 → faturalanan 1.257 MSU → $833K/ay → $26–289/TPS) ve aylık döküm.
  - 0.3: 22 terimlik sözlük (CEC, CP, kademe kodu, PCI, LSPR, MSU, MLC/AWLC, R4HA, zIIP, ICF, sysplex, GDPS, CoD, CBU, TFP, w, f, D_io, FTE, low/mid/high).
- **Eylem:** önceki adımlardan kalan eski ifadeler düzeltildi: §1.1 ("işlem karmaşıklığı" → iş yükü profili), §1.4 (eksik bileşenler listesi), §2.1 (TPS aralığı tek z16 tavanına göre; özel bileşim ve `--range` girdileri), §2.2 (örnek kademe 3931-516; yıllık çıktıda personel ve storage), §4.4.4 (kademe MSU'su ile faturalanan MSU ayrımı), §6.7 (topolojinin dört maliyet kalemine etkisi tek tabloda), §7.1.5 (f yalnızca Db2 profillerinde), §10.2 (yıllık örnek 10K TPS).
- **Gerekçe:** Danışman ve jüri dokümanı tek başına okuyacak; model adım adım büyüdüğü için kavramlar ilk geçtikleri yerde tanımlanmamıştı ve bazı örnekler eski birim ve kademelerle kalmıştı.
- **Etki:** Model ve sonuçlar değişmedi (13/13 test). Doküman artık yukarıdan aşağı okunduğunda tanımsız terim veya eski sayı içermiyor.

---

## 2026-11-01 — Oturum 2 (devam): Olay tabanlı availability, RPO/RTO, CBU ve GDPS — Plan adımı 4

### 1. Araştırma ve bulgular
- **SG24-8446 topolojilere "nine" vermiyor.** Güncel baskıda yalnızca dört desen (Reliable base, Failover capable, Fault tolerant, Adaptive continuity) ve genel RTO/RPO aralıkları var. DR'de RTO 2–72 saat; 2 saatin altı GDPS ister. Önceki sürümdeki "M1 ~6 … M4 ~10 nine" tasarım hedefleri kaynaksızdı.
- **ITIC rakamları sunucu donanımının kesintisi.** z16 için 9 nine, yılda 31,56 ms; Lenovo x86 da 8 nine. Hizmet kesintisini belirlemiyor.
- **GDPS RPO/RTO:** IBM GDPS geliştirme ekibinin VM Workshop Haziran 2026 sunumu:
  - Metro: RPO 0, RTO ~2 dk ile < 1 saat arası.
  - Global ve Metro Global: RPO 2–5 sn, RTO < 1 saat.
  - CA: RPO 0–5 sn, RTO 20–60 sn.
- **CBU (SC28-7025):** Kayıt LICCC ile açılır ve donanım önceden kurulu olmalı. Kayıt 1–5 yıllık; her yıl için bir 10 günlük test hakkı ve tek bir 90 günlük gerçek aktivasyon içerir. DR makinesinin yazılım faturası kalıcı kapasiteye göre kesiliyor. Fiyat yayımlanmıyor.
- **GDPS fiyatı:** MSU'ya değil, otomatikleştirilen kapsama bağlı; rakam yayımlanmıyor.
- **Saha olayları:** Uptime 2025'e göre operatörlerin %53'ü son 3 yılda kesinti yaşadı (yılda ~0,25 olay) ve olayların %9'u ciddi. Uptime 2022'ye göre kamuya yansıyan kesintilerin %8 ile %30'u 24 saatten uzun sürüyor.

### 2. Karar
- Emirhan karar kartında **"Olay tabanlı, RTO'ya bağlı"** seçeneğini seçti.
- Önceki "ITIC + ×10 planlı kesinti" yaklaşımı bırakıldı.

### 3. Aksiyon
- **Availability:** Yıllık kesinti = λ_saha × [(1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec)] + λ_planlı × T_planlı + D_cpc (yalnızca M1).
  - Tüm parametreler low/mid/high.
  - Feasibility geçerli senaryoyla yapılıyor (varsayılan mid). Aralık senaryoları topolojiyi yeniden seçiyor.
- **RPO/RTO:** `--rpo-seconds` ve `--rto-minutes` girdileri eklendi; projenin 8 girdisinin tamamı artık bağlı.
  - RPO: M1 24 saat, M2 0, M3 5 sn, M4 5 sn.
  - RTO: M1 72 saat, M2 2 saat, M3 30 dk, M4 30 sn.
- **CBU:** DR frame'i tam frame'in `DR_FRAME_COST_FRACTION` oranıyla fiyatlanıyor: 0,50, aralık 0,30–1,00. Enerji tam sayılıyor. Yazılım primi kaldırıldı.
- **GDPS:** Kapasiteden bağımsız, sabit aylık kalem: M3 $50K, M4 $100K. Orta değerler eski primin 10K TPS'teki karşılığı. `GDPS_COST_LEVEL` 0,5–2,0.
- **Aralık:** Aralık çıktısına 5 yeni parametre eklendi: DR frame, GDPS, saha olayı, kurtarma süresi, planlı kesinti. Toplam 14 parametre.
- **Araç ve testler:** `src/tools/availability_sensitivity.py` eklendi. `test_availability_rpo_rto_cbu_gdps` testi eklendi; testler 14/14. Demo ve CLI örnekleri 10K TPS'e çekildi; epilog'daki geçersiz `--workload high` düzeltildi.
- **Dokümantasyon (v3):**
  - §6 baştan yazıldı: savunma, topolojiler, formül, parametre tablosu, sonuçlar, RPO/RTO, maliyete etki, geçerlilik tehditleri.
  - §0, 1.2, 1.4, 2.1, 2.2, 7, 7.1.3, 7.5, 7.8, 8, 9.6, 10, 11.2 ve 12 güncellendi.

### 4. Etkiler
- **Availability (mid):**

  | Topoloji | Yıllık kesinti | Availability |
  |---|---|---|
  | M1 | 3,3 saat | %99,962 |
  | M2 | 0,55 saat | %99,994 |
  | M3 | 0,16 saat | %99,998 |
  | M4 | ~20 sn | %99,99994 |

  M1'in kesintisinin çoğu planlı. CPC donanım arızası hiçbir topolojide belirleyici değil.
- **10K TPS, varsayılan (%99,9):** Mid sonuç değişmedi ($83,32/TPS). Aralığın üst ucu $288,52'den $317,58'e çıktı, çünkü high senaryoda M1 %99,84'e düşüyor ve model M2'ye geçiyor.
- **Availability hedefinin maliyeti (10K TPS, mid):**

  | Hedef | Topoloji | $/TPS |
  |---|---|---|
  | %99,99 | M2 | $89,6 |
  | %99,995 | M3 | $100,1 |
  | %99,999 | M4 | $109,2 |

  %99,9'dan %99,999'a çıkış maliyeti +%31 artırıyor: GDPS, personel, DR frame ve storage. Yazılım değişmiyor.
- **RPO/RTO (10K TPS):** RPO 0 → M2; RTO ≤ 60 dk → M3; RTO ≤ 1 dk → M4. RPO 0 ve RTO ≤ 60 dk birlikte infeasible, çünkü GDPS Metro ayrı bir topoloji olarak modellenmedi.
- **Yıllık mod (10K ortalama, %99,9):** Değişmedi. %99,999'da steady_oltp M4 + TFP ile $17,24M.

### 5. Açık noktalar
- Planlı kesinti sıklığı kaynaksız ve M1'i en çok bu parametre belirliyor. Gerçek bir değişiklik kaydıyla kalibre edilmeli.
- CBU ve GDPS fiyatları varsayım.
- GDPS Metro ayrı topoloji olarak eklenmeli.
- Kesinti dağılımı (SLA ihlali olasılığı) yok.
- Clustered taraf aynı denklemi kendi kurtarma süreleriyle kullanmalı; saha olayı parametreleri iki tarafta ortak.

---

## 2026-11-01 — Oturum 2 (devam): Bağımsız denetim — Değerlendirme #5

### 1. Aksiyon
- Adım 5'e geçmeden önce model, kod ve v3 dokümanı önceki bağlamdan bağımsız olarak sıfırdan denetlendi. Her bulgu kodu çalıştırarak doğrulandı. Rapor: `evaluations/2026-11-01_degerlendirme_05_denetim.md` (**Değerlendirme #5**).

### 2. Sebep
- Emirhan'ın isteği: "modeli ve kodu bağımsız olarak denetle, problem varsa düzeltelim devam etmeden".

### 3. Düzeltilenler
- **Model hataları (sonucu değiştiren):**
  - Donanıma kapasiteden bağımsız `HW_FRAME_BASE_COST` = $500K eklendi (aralık $250K–1M). En küçük kademe önceden $0,17M çıkıyordu; düşük TPS'te mainframe lehine yanlılıktı.
  - Yıllık profil istenen tepe/ortalama oranını tam veriyor: peak günü çarpanı kapalı formdan, düşük oranlarda genlik ikiye bölmeyle. Ulaşılamayan oran hata veriyor.
  - Yıllık modda zIIP motorları yılın en büyük aktif kademesine göre boyutlanıyor; geçici kapasitedeki zIIP ihtiyacı artık bedelli.
- **Tutarlılık ve kod hataları:**
  - M3'ün RPO'su 5 sn → 0 (tek site kaybında Metro Mirror). "RPO 0 ve RTO ≤ 60 dk" artık M3 seçiyor.
  - D_io profilin okuma/yazma bileşimiyle hesaplanıyor; sabit okuma payı (0,70) kaldırıldı.
  - Donanım bakımı 1 yıllık garantiyle (storage ile tutarlı).
  - CoD gün = 730/24 saat.
  - `solve(verbose=True)` dönüş değeri, girdi doğrulaması, `use_values` anahtar kontrolü, SQL'siz özel profilin zIIP uygunluğu. Kullanılmayan iki sabit kaldırıldı.
  - SW_PRICE_LEVEL_FACTOR üst ucu 1,5 → 1,75 (2004 → 2026 TÜFE ~×1,7).
- **Testler:** 6 yeni test (verbose dönüşü, profil oranı, statik = yıllık düz yükte, geçici kapasitede zIIP, CLI uç durumları, I/O karışımı). Toplam 20/20.
- **Araçlar:** Duyarlılık araçları `m.use_values` kullanıyor; tüm çıktılar ve `data/out/` CSV'leri yeniden üretildi.

### 4. Bilinçli tercih olarak belgelenenler
- Personelin kurulu kapasiteye bağlı olması, GDPS bedelinin döngüsel çapası, DR makinesinin küçük yazılım faturasının ihmali, CPU_US_TM_BASE'in tek çapadan türetilmesi (718: 85,9 µs; 726: 93,3 µs), köprü belirsizliğinin aralıkta olmaması, testlerin bir kısmının tautolojik olması, DS8910F tepe IOPS'unun drive sayısından bağımsız alınması. Gerekçeleri v3 §6.7, §7.7.5, §10.4, §12.1, §12.2'de.

### 5. Etkiler
- **10K TPS ($/TPS/ay):** low 26,24 → 26,67; mid 83,32 → 84,06; high 317,58 → 337,28. high'daki artışın ~$18'i yazılım seviyesinin yeni üst ucundan, ~$5'i frame tabanından.
- **Maliyet/TPS eğrisi (mid):** 500 TPS'te $300,55 → $324,42 (+%8); 150K TPS'te $38,30 → $37,89. Bükülme 500 → 150K TPS arasında ~7,9 kattan ~8,6 kata çıktı.
- **Yıllık mod (10K ortalama, M1):** steady C $13,49M → $12,75M; retail B $21,75M → $21,31M; batch C $17,88M → $17,23M. Kazanan strateji hiçbir presette değişmedi. Düşüşün ana nedeni profil düzeltmesi (eski profil tepeyi istenenden yüksek üretiyordu).
- **Dokümantasyon (v3):** §0.2, 4.4.4, 5.3, 5.5, 6.2, 6.6–6.8, 7.1.2, 7.1.6, 7.2, 7.3, 7.6, 7.7.4–7.7.5, 7.8, 8.1.1, 8.1.3–8.1.5, 8.6, 8.7, 9.2, 9.6–9.8, 10.3–10.4, 11.5, 12.1–12.2 yeni sayılar ve gerekçelerle güncellendi.

### 6. Açık kalanlar
- Adım 5 (TS7700 yedekleme + 5 yıllık NPV) ve Adım 6 (ortak modül) Emirhan'ın onayını bekliyor.
- Drawer maliyeti, GDPS Metro topolojisi, planlı kesinti kalibrasyonu, L4+ AWLC fiyatları.

---

## 2026-11-02 — Oturum 3: Adım 5 — Yedekleme (TS7770) ve 5 yıllık NPV

### 1. Aksiyon
- **Yedekleme katmanı:** `backup_plan` eklendi (kodda BOLUM 6b, v3 §8.10).
  - Db2 image copy'leri (haftalık tam + günlük artımlı) ve arşiv loglar iki sitelik IBM TS7770 disk-only grid'inde 4 hafta saklanıyor.
  - Cache (image copy + log) / sıkıştırma ile 20 TB adımlarla boyutlanıyor.
  - Küme sayısı hem 3,9 PB cache sınırını hem 8 saatlik penceredeki 4.000 MB/s verimi karşılıyor.
  - Maliyet: küme tabanı $493.080 + cache $2.000/TB, DS8900F ile aynı indirim; 5 yıl amortisman, 1 yıl garanti sonrası %15 bakım, küme başına 4 kW.
  - Statik, yıllık ve aralık moduna bağlandı.
  - Aralığa 3 parametre eklendi (saklama süresi, sıkıştırma, cache fiyatı). Toplam 18 parametre.
- **5 yıllık NPV:** `solve_npv`, `solve_npv_yearly`, `solve_npv_range`, `npv_tornado` ve CLI'da `--npv`, `--tps-growth`, `--discount-rate`, `--years` eklendi (kodda BOLUM 10, v3 §9.10).
  - Yük yılda %10 büyüyor. Kademe yalnızca yükseliyor (`is_permanent_upgrade`); topoloji 1. yılda sabit.
  - Storage ve yedek t = 0 ve t = 3'te alınıyor. Capex yıl başı, opex yıl sonu.
  - Fiyat artışları: yazılım ve GDPS %3, bakım %3, ücret %3,3, enerji %4.
  - TFP'de 1. yılın MSU-saati taban; tabanın üstü 0,5 büyüme fiyatıyla faturalanıyor. Kalan değer 0.
  - Çıktılar: NPV, EAC, seviyelendirilmiş $/TPS/ay.
- **Testler:** `test_backup_layer` ve `test_npv_consistency_and_direction` eklendi; CLI testi `--npv` ve `--years 0` kontrolüyle genişletildi. Toplam 22/22.
- **Araçlar:** `src/tools/npv_sensitivity.py` eklendi (yedek veri ekseni, statik NPV, r × g, yıllık stratejiler, fiyat artışları, NPV aralığı ve tornado). `range_curve.py`'a yedek sütunu eklendi. Bütün araç çıktıları ve `data/out/` CSV'leri yeniden üretildi.
- **Dokümantasyon:**
  - v3'e §8.10 (yedekleme: savunma, hacim, boyutlandırma, maliyet, sonuçlar, tehditler) ve §9.10 (5 yıllık ufuk: gerekçe, formül, büyüme yolu, parametreler, tutarlılık, sonuçlar, tehditler) eklendi.
  - §0–2, 7.5–7.8, 8.1, 8.4, 8.7, 8.9, 9.6–9.8, 10, 11.5–11.6 (yeni referanslar), 12 ve README güncellendi.
- **Değerlendirme #6:** `evaluations/2026-11-02_degerlendirme_06_yedek_ve_npv.md`.

### 2. Sebep
- Emirhan'ın isteği: "adım 5'e geç", sonuçlar detaylı dokümante edilsin.
- Yedekleme projenin maliyet kategorilerinden biri ve M1'in RPO/RTO iddiasının dayanağı. NPV, 5 yıllık bir satın alma kararının (büyüme, yükseltme, fiyat artışı, TFP büyüme fiyatı) karşılaştırma ölçüsü.

### 3. Sonuç
- **Statik, 10K TPS, 20 TB:**
  - Aylık $852.343 = $85,23/TPS (önce $84,06). Fark yedek kalemidir (aylık $11.790, %1,4).
  - Aralık $27,17 / $85,23 / $341,23.
- **Veri ekseni (10K TPS):** Storage + yedek payı 5 TB'ta %1,5, 500 TB'ta %22, 2.000 TB'ta %52.
- **Statik NPV (10K TPS):** $50,98M. EAC $12,43M. Seviyelendirilmiş $85,96/TPS/ay (statikten +%0,9). NPV aralığı $32,07 / $85,96 / $409,24.
- **r ve g:** r %5 → %10'da NPV −%12, seviyelendirilmiş maliyet ±%1. Büyüme %0 → %20'de seviyelendirilmiş maliyet $91,54 → $81,12.
- **Yıllık NPV (10K ortalama, M$):**
  - steady: P 69,40 / B 68,11 / **T 65,86**
  - retail: P 115,54 / B 113,15 / **T 112,49**
  - batch: P 92,25 / B 88,33 / **T 87,20**
  - Büyüme indirimi yoksa ya da büyüme 0 ise retail'de B kazanıyor.
- **Yıllık tek yıl:** Yedek her stratejiye ~$141K/yıl ekliyor. Kazananlar değişmedi (steady C, retail B, batch C).
- **Tutarlılık:** r = 0, büyüme ve artış 0 iken NPV = 60 × statik aylık ve 5 × yıllık toplam (10⁻⁹ içinde).
- **Bulgu:** retail_bursty'de 5. yılda Max39 drawer sınırı base'i 716 → 740'a zorluyor (~$6,5M capex). Drawer maliyeti eksikliğinin somut bir sonucu.

### 4. Açık kalanlar
- Adım 6 (ortak modül). İçeriği Değerlendirme #6 Bölüm 4'te: yedek girdileri, r/g/zamanlama, fiyat artışı sınıfları, genişleme kuralı, teknoloji yenileme kuralı. Emirhan'ın onayını bekliyor.
- Drawer maliyeti (önceliği yükseldi), GDPS Metro topolojisi, planlı kesinti kalibrasyonu, L4+ AWLC fiyatları, gerçek bir TS7770 teklifi.

---

## 2026-11-02 — Oturum 3 (devam): Yedekte nesne depolama seçenekleri

### 1. Aksiyon
- Yedek katmanına S3 uyumlu on-prem nesne depolama ve AWS S3 hedefleri eklendi. Emirhan'ın kararı: "ikisi de, model seçsin".
- Model üç hedefi (TS7770, on-prem nesne, AWS S3) boyutlandırıyor. Kısıtlar:
  - 8 saatlik yedek penceresi;
  - yalnızca M1'de tam geri yüklemenin RTO'nun yarısına (36 saat) sığması;
  - nesne hedefleri için DS8900F Transparent Cloud Tiering verimi (5.000 MB/s, varsayım).
- Kısıtları karşılayanlardan en ucuzu seçiliyor. S3 "hibrit" diye işaretleniyor; `--backup-target` ile hedef zorlanabiliyor.
- NPV'de abonelik, S3 ve hat ücretleri her yıl o yılın hacmiyle işletme gideri; hedef 1. yılda sabit.
- Aralığa 2 parametre eklendi (on-prem donanım ve abonelik). Toplam 20.
- Yeni test `test_backup_targets_and_constraints`; CLI testi genişletildi. 23/23.
- `npv_sensitivity.py` bölüm 1 üç hedefi, kısıt eşiklerini ve varsayım taramasını gösteriyor. Bütün araç çıktıları ve `data/out/` CSV'leri yeniden üretildi.
- v3 §8.10 baştan yazıldı. Etkilenen sayılar §0, 2, 6, 7.6–7.8, 8.1, 8.7, 9.7–9.8, 9.10, 10, 11.5 (yeni referanslar [SG24-8381], [AWS-S3-2026], [AWS-DX-2026], [MINIO-TCO]) ve 12'de güncellendi.
- Değerlendirme #6'ya Bölüm 7 olarak ek yazıldı.

### 2. Sebep
- Emirhan'ın sorusu: yedekte S3 de, kısıtlara göre viable olacak şekilde, seçenek olarak konabilir mi?
- Akademik gerekçe: kurumlar mainframe yedeğini gerçekte bu üç yoldan biriyle alıyor. Clustered taraf da büyük ihtimalle nesne depolama kullanacağı için iki taraf aynı hedef fiyat fonksiyonunu paylaşabilir.

### 3. Sonuç
- **10K TPS, 20 TB:**
  - Seçilen hedef on-prem nesne depolama, aylık $5.635 (TS7770 $11.790, S3 $6.069).
  - Toplam $846.187 = $84,62/TPS (önce $85,23). Aralık $27,06 / $84,62 / $338,09.
  - NPV $50,60M, seviyelendirilmiş $85,31; NPV aralığı $31,98 / $85,31 / $405,44.
- **Hedef seçimi (10K TPS):**
  - 5 TB: S3 (farkı $3).
  - 20–300 TB: on-prem nesne.
  - M1'de ~360 TB'tan itibaren TS7770, çünkü geri yükleme 36 saate sığmıyor.
  - M3'te ~550 TB'tan itibaren TS7770, çünkü günlük verim TCT tavanını aşıyor.
- **Storage + yedek payı:** 20 TB'ta %1,6, 500 TB'ta %22, 2.000 TB'ta %52.
- **Strateji sıralamaları değişmedi:** tek yılda steady C, retail B, batch C; 5 yılda TFP.

### 4. Açık kalanlar
- TCT veriminin gerçek bir ölçümle kalibrasyonu.
- Kurum içi nesne depolama için ikinci bir fiyat kaynağı.
- Mantıksal bozulmadan geri dönüş RTO'su.
- Adım 6 (ortak modül; iki fiyat modu önerisi dahil) Emirhan'ın onayını bekliyor.

---

## 2026-11-02 — Oturum 4: Açık sistem (x86) tarafının araştırılması ve planı

### 1. Aksiyon
- x86 tarafı için kapsamlı bir kaynak araştırması yapıldı ve `docs/acik_sistem_arastirma_plani_v1.md` olarak yazıldı. Kod yazılmadı (Emirhan'ın talimatı: önce yalnızca neyi bulmamız gerektiği, ne bulduğumuz ve bunların nasıl işe yarayacağı).
- Doküman 12 köprü tanımlıyor (işlem birimi, kapasite birimi, kuyruk, availability denklemi, topoloji, storage, yedek, personel, fiyat dönemi, NPV, aralık, lisans tabanı) ve her katman için "ne gerekiyordu → ne bulundu → modele nasıl girer" düzeninde ilerliyor.
- Kaynak seçme ölçütü: yalnızca bir parametreyi ya da köprüyü doğrudan besleyen kaynaklar alındı. İncelenip alınmayanlar gerekçeleriyle ayrı bir tabloda (§15.2).
- 18 x86 aralık parametresi ve Adım 6 ortak modülüne taşınacak 6 kural önerildi. 7 konu Emirhan'ın kararına bırakıldı (§13).

### 2. Sebep
- Emirhan'ın sorusu: "Artık açık sistem tarafı araştırmasına geçebilir miyiz?" ve talimatı: araştırmayı en ayrıntılı biçimde yapmak, iki sistemi karşılaştırmak için köprü ihtiyacını unutmamak, kodlamaya başlamadan bir plan dokümanı yazmak.
- Eşit derinlik ilkesi (v4 §3.7) ve Değerlendirme #6 §4'teki clustered taraf yükümlülükleri.

### 3. Sonuç (en önemli bulgular)
- **İşlem birimi:** sysbench `oltp_read_write` bileşimi (14 okuma + 4 yazma + commit) mainframe `oltp_rw` profiliyle birebir aynı.
- **Kapasite köprüsü:** x86'da PCI'nın karşılığı olarak çekirdek başına SPECrate2017_int_base önerildi. Bare-metal PostgreSQL ölçümü (c5d.metal, 25.953 TPS / 48 çekirdek) SPECint ile normalize edilince R760 sınıfı çekirdek başına ~893 oltp_rw TPS; iki bulut ölçümü ±%15 içinde.
- **Platformlar arası kontrol:** 1 z16 CP (oltp_rw ~1.955 TPS) ≈ 2,2 R760 çekirdeği; büyüklük mertebesi makul.
- **Oracle:** lisansın benchmark yayın yasağı nedeniyle çekirdek başı verim kalibre edilemiyor; geniş aralık parametresi (0,8–1,3, mid 1,0).
- **Mimari:** Patroni tek yazıcılı; PostgreSQL tarafında kapasite sunucu boyutu adımlarıyla büyüyor ve tek düğüm tavanı (~35–50K TPS, R760) var. Mainframe'in tek CEC tavanıyla simetrik bir sınırlama.
- **Fiyat dönemi:** 2026 bellek/SSD fiyat şoku (64 GB RDIMM ~$255 → $2.245–3.400; NVMe ~$115/TB → ~$753/TB) x86 donanımını etkiliyor; mainframe çapaları şok öncesinden. Ortak modülde `PRICE_EPOCH` kuralı önerildi.
- **Storage tanım sorunu:** AFA fiyatları etkin TB ($65–215), DS8900F ham TB (~$2.590); aynı tanımla fiyatlanmalı.
- **Topoloji:** M1–M4 ile Oracle MAA Bronze/Silver/Gold/Platinum birebir eşleşiyor; Patroni RTO'su parametrelerden türetilebiliyor (varsayılanla ~27–41 sn). Availability denklemine düğüm arızası × yük devretme terimi eklendi; saha olayları ve elle geçiş karar süresi ortak parametre.
- **Personel:** tek bulunan oran kaynağı IBM Eagle (dağıtık: 32 saat/fiziksel sunucu, 36 saat/imaj); bağımsız kaynak eksik, x86 tarafının en zayıf noktası.

### 4. Açık kalanlar
- Emirhan'ın kararları (§13): storage tipi, sunucu nesli, tek yazıcı tavanının üstü (Citus), X4'ün PostgreSQL karşılığı, üç üretici mi tek referans mı, kendi sysbench ölçümümüz, DB'nin VM'de mi Kubernetes'te mi çalıştığı.
- Bağımsız dağıtık personel oranı; Oracle standby lisans kuralının birincil kaynakla teyidi; Active Data Guard güncel liste fiyatı; sunucu bütün fiyatı için kamu ihale kaydı.
- Kapsam asimetrisi: mainframe'de CICS modelde, x86'da uygulama sunucusu katmanı dışarıda (§14.4).
