# Değerlendirme #5: Mainframe modelinin ve kodunun bağımsız denetimi

> **Değerlendirme #5** · Tarih: 2026-11-01 · Kapsam: mainframe tarafının tamamı (`src/mainframe_model.py`, `src/test_mainframe_model.py`, `src/tools/*`, `docs/mainframe_model_documentation_v3.md`), availability adımından (Adım 4) sonra, Adım 5'e (yedekleme + 5 yıllık NPV) geçmeden önce.
> Önceki değerlendirme: #4 (`2026-11-01_degerlendirme_04_mainframe.md`). Kapanan ve açık kalan maddeler Bölüm 6'da.
> Yöntem: Kod ve doküman, önceki oturumların bağlamı olmadan, sıfırdan okunarak denetlendi. Her bulgu kodu çalıştırarak doğrulandı. Düzeltmelerden sonra tüm araç çıktıları ve dokümandaki sayılar yeniden üretildi. Rakamlar statik modda oltp_rw, %99,9, 20 TB veri ve varsayılan parametrelerle üretildi.

## 0. Özet

1. **Sonucu değiştiren üç model hatası bulundu ve düzeltildi:** donanımda kapasiteden bağımsız bir taban yoktu, yıllık profil istenen tepe/ortalama oranını vermiyordu, zIIP motorları geçici kapasite günlerinde bedelsiz sayılıyordu (Bölüm 1).
2. **Altı tutarlılık ve kod hatası düzeltildi:** RPO tanımı, I/O okuma/yazma karışımı, bakımda garanti yılı, CoD gün sayısı, `solve(verbose=True)`'nun dönüş değeri, girdi doğrulaması (Bölüm 2).
3. **Altı nokta hata değil, bilinçli tercih olarak belgelendi:** personelin kurulu kapasiteye bağlı olması, GDPS bedelinin döngüsel çapası, DR makinesinin küçük yazılım faturası, tek CPU çapası, köprü belirsizliğinin aralıkta olmaması, testlerin bir kısmının tautolojik olması (Bölüm 3).
4. **Başlık sonucu az değişti:** 10K TPS'te mid $83,32 → $84,06/TPS/ay (+%0,9). Aralık $26,24–317,58'den $26,67–337,28'e geçti. Düşük TPS'te etki daha büyük: 500 TPS'te mid +%8 (frame tabanı). Yıllık modda kazanan strateji hiçbir presette değişmedi (Bölüm 4).
5. **Model artık Adım 5'e hazır.** Testler 14'ten 20'ye çıktı, hepsi geçiyor.

## 1. Sonucu değiştiren model hataları

| # | Bulgu | Neden hata | Düzeltme | Etki |
|---|---|---|---|---|
| 1.1 | Donanım bedeli yalnızca PCI × $200 idi | En küçük kademe (3931-401) $0,17M çıkıyordu; kaynak aralığının giriş ucu ~$0,5M [PRICE]. Bu, crossover'ın beklendiği düşük TPS bölgesinde mainframe lehine sistematik bir yanlılıktı | `HW_FRAME_BASE_COST` = $500K eklendi (çerçeve, drawer, bellek, I/O, HMC); aralık parametresi, $250K–1M | 500 TPS'te mid +%8; 10K TPS'te +%0,9. Tornado'da yeni bir sürücü |
| 1.2 | Yıllık profilin gerçekleşen tepe/ortalama oranı istenen değerden sapıyordu | Preset'ler (1,5× / 3,5× / 2,5×) R4HA ve kademe seçimini doğrudan belirliyor; oran tutmazsa senaryo tanımı ile hesaplanan senaryo farklı olur | Peak günü çarpanı kapalı formdan çözülüyor; oran desenin kendisinden düşükse genlik ikiye bölmeyle küçültülüyor; ulaşılamayan oran hata veriyor | Üç preset oranı tam veriyor. steady_oltp'nin tepesi 15.000 TPS; seçilen kademeler küçüldü |
| 1.3 | Yıllık modda zIIP motorları yalnızca base kademeye göre boyutlanıyordu | CoD/corridor günlerinde geçici GP kapasitesindeki işin f payı da zIIP ister; bu ihtiyaç bedelsiz kalıyordu (B ve C lehine yanlılık) | zIIP'ler yılın en büyük aktif kademesine göre kalıcı kuruluyor; ek motorların amortismanı ve bakımı donanıma ekleniyor | B/C'nin donanım kalemi biraz arttı; sıralama değişmedi |

## 2. Tutarlılık ve kod hataları

| # | Bulgu | Düzeltme |
|---|---|---|
| 2.1 | M3'ün RPO'su 5 sn kabul ediliyordu. Oysa tek site kaybında M3 Metro Mirror ile 0 kaybeder; 2–5 sn, bölgesel felaketteki Global Mirror bacağının değeridir. Modelin geri kalanı RPO'yu tek site kaybı için tanımlıyor | M3 RPO = 0. "RPO 0 ve RTO ≤ 60 dk" artık M3 seçiyor (önceden infeasible). Bölgesel felaket ayrı bir senaryo olarak dokümanda tanımlandı (v3 §6.2, §6.8) |
| 2.2 | D_io sabit bir okuma payıyla (r = 0,70) hesaplanıyordu; profilin kendi okuma/yazma bileşimi yok sayılıyordu (oltp_rw'nin senkron I/O'sunun %74'ü okuma, tpcb_like ve REDP'ninkinin çoğu ya da tamamı yazma) | D_io = senkron okuma × t_okuma + senkron yazma × t_yazma. Senkron replikasyon yalnızca yazmalara ekleniyor. oltp_rw M2–M4'te 0,49 → 0,46 ms |
| 2.3 | Bakım 5 yılın tamamına uygulanıyordu; storage tarafında ise 1 yıllık garanti düşülüyordu | Donanım bakımı da 1 yıllık garantiyle (×4/5) hesaplanıyor; iki kalem tutarlı |
| 2.4 | CoD günlük ücreti ayı 30 gün sayıyordu; modelin geri kalanı 730 saat (30,4 gün) kullanıyor | Gün = 730/24 saat |
| 2.5 | `solve(verbose=True)` üçlü yerine tek bir sayı döndürüyordu (değişken adı çakışması) | Düzeltildi; test eklendi |
| 2.6 | Girdi doğrulaması yoktu: sıfır/negatif TPS, (0, 1) dışı availability, SQL'siz özel profilin zIIP'e uygun sayılması, `use_values`'ta bilinmeyen parametre adının sessizce kabul edilmesi | Hepsi hata veriyor; CLI testleri eklendi. Kullanılmayan `MAINFRAME_MIN_VIABLE_MIPS` ve `HARD_UTILIZATION_CAP` kaldırıldı |

Ayrıca yazılım fiyat seviyesinin üst ucu 1,5'ten 1,75'e çıkarıldı: kademe fiyatları 2004 tarihli ve 2004 → 2026 ABD TÜFE düzeltmesi ~×1,7 ediyor; önceki üst uç bu düzeltmeyi bile kapsamıyordu (v3 §7.1.2).

## 3. Bilinçli tercih olarak belgelenenler

Bunlar hata değil, gerekçesi dokümana yazılan modelleme kararlarıdır. Hakemin "eksik" sanmaması için tezde açıkça anılmalı.

| # | Nokta | Neden bu şekilde | Nerede |
|---|---|---|---|
| 3.1 | Personel kurulu kapasiteye göre hesaplanıyor; sıkı latency hedefi daha büyük kademe seçtirince personel de artıyor | Kaynak çalışmalar ekipleri kurulu MIPS'e göre ölçüyor [IBM-EAGLE, GARTNER-ITKMD]. Alternatif (tüketilen kapasite) kaynaksız olurdu | v3 §7.7.4–7.7.5, §12.2 |
| 3.2 | GDPS sabit bedelinin orta değeri, eski yüzde priminin 10K TPS'teki karşılığından çapalandı (döngüsel) | GDPS fiyatı yayımlanmıyor; çapa yalnızca büyüklük mertebesi içindir ve 0,5–2,0 aralığıyla taranıyor | v3 §6.7 |
| 3.3 | DR makinesinin kalıcı kapasitesinin (küçük) yazılım faturası ihmal ediliyor | CBU kuralı: DR makinesinin yazılımı kalıcı kapasitesine göre faturalanır; kalıcı kapasite küçük olduğu için toplamdaki etki ihmal edilebilir | v3 §12.2 |
| 3.4 | CPU_US_TM_BASE yalnızca 3931-718 çapasından türetiliyor (85,9 µs; 726 çapası 93,3 µs verir, fark %9) | Tek çapa seçimi bir kalibrasyon belirsizliğidir; SQL CPU aralıkları bunu dolaylı kapsar | v3 §12.1 |
| 3.5 | Köprünün (TPS/PCI) belirsizliği aralık parametrelerinde yok | Köprü kaynaklı bir ölçümden geliyor; belirsizlik iş yükü profilinin CPU parametreleriyle taranıyor | v3 §12.1 |
| 3.6 | Testlerin bir kısmı tautolojik (örneğin kademe tablosunun kendi çapalarını üretmesi) | Testler iç tutarlılığı güvenceler; dış geçerlilik kaynak karşılaştırmalarıyla sağlanır (§7.1.4, §7.8 Gartner kontrolü) | v3 §10.4 |

Ek olarak: DS8910F'in 860K tepe IOPS'u drive sayısından bağımsız alınıyor (v3 §12.1).

## 4. Düzeltmelerin etkisi

**Statik mod, 10K TPS ($/TPS/ay):**

| | Önce | Sonra |
|---|---|---|
| low | 26,24 | 26,67 |
| mid | 83,32 | 84,06 |
| high | 317,58 (M2) | 337,28 (M2) |

high'daki artışın ~$18'i yazılım fiyat seviyesinin yeni üst ucundan (1,75), ~$5'i frame tabanının üst ucundan ($1M) gelir; bakımdaki garanti yılı bunu biraz dengeler. mid'de frame tabanı tek başına +$1,25 ekler, garanti yılı ise bir kısmını geri alır.

**Maliyet/TPS eğrisi (mid):** 500 TPS'te $300,55 → $324,42 (+%8); 150K TPS'te $38,30 → $37,89 (bakımdaki garanti yılı nedeniyle hafif düşüş). Eğrinin bükülmesi biraz güçlendi: 500'den 150K TPS'e ~8,6 kat.

**Yıllık mod (10K ortalama, M1, milyon USD, kazanan):**

| Preset | Önce | Sonra | Kazanan |
|---|---|---|---|
| steady_oltp | C 13,493 | C 12,747 | C (değişmedi) |
| retail_bursty | B 21,750 | B 21,312 | B (değişmedi) |
| batch_heavy | C 17,879 | C 17,226 | C (değişmedi) |

Düşüşün ana nedeni profil düzeltmesidir: eski profil tepeyi istenenden yüksek üretiyordu, bu da gereğinden büyük kademe ve personel seçtiriyordu.

**Availability:** M3'ün RPO'su dışında topoloji seçimleri ve kesinti değerleri değişmedi.

## 5. Akademik sunum notları

- Denetim, tezde "model doğrulama" başlığı altında bir paragraf olarak anılabilir: bağımsız okuma, bulguların kodla doğrulanması, düzeltmelerin etkisinin raporlanması.
- Frame tabanı ($500K) yarı-kaynaklıdır (kaynak aralığının giriş ucu). Düşük TPS crossover'ı bu parametreye duyarlı olduğu için x86 tarafıyla kıyasta aralığıyla birlikte verilmeli.
- Yıllık modda stratejiler arası fark %1,5–4,9'dur ve TFP-SW indirimi gibi sözleşmeye bağlı bir parametreyle tersine dönebilir. Strateji sonucu kesin bir öneri olarak değil, koşullu bir bulgu olarak sunulmalı.

## 6. Kapanan / açık kalan tehditler

**Değerlendirme #4'ten kapanan:**
- Yazılım yığını (AWLC kademeli z/OS + CICS + Db2) ve zIIP (Adım 1).
- IOPS_PER_TX'in üçlü rolü: iş yükü profiliyle değiştirildi (Adım 2).
- Personel (Adım 3).
- CBU / GDPS / RPO-RTO (Adım 4).
- Storage IOPS tavanı (Değerlendirme #4'ten hemen sonra).
- Donanım tabanı: **kısmen** (frame tabanı bu denetimde eklendi; drawer maliyeti hâlâ yok).
- Transaction köprüsü: mainframe yarısı kapandı (bileşimli profil, sysbench oltp_read_write). x86 tarafının aynı bileşimi kullanması gerekiyor.

**Açık kalan:**
- Çok yıllık ufuk ve yedekleme (Adım 5).
- Ortak modül ayrımı (Adım 6).
- Drawer maliyeti ve enerjinin drawer'la ölçeklenmesi.
- Clustered storage tipi kararı.
- Storage ağının DR'daki asimetrisi.
- GDPS Metro'nun ayrı topoloji olması.
- Planlı kesinti kalibrasyonu.
- L4+ AWLC kademe fiyatlarının yayımlanmamış olması.
- Parallel Sysplex ile tek CEC'in ötesine ölçekleme.

**Yeni:** yok. Denetimde bulunan bütün hatalar düzeltildi ya da gerekçesiyle belgelendi.
