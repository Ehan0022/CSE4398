# Sunum Demosu: 10 Senaryo

*Tarih: 2026-11-23 · Kod: `main` (PR #4 sonrası, Adım 7) · Bütün sayılar modellerin gerçek koşusundan alındı.*

Bu doküman hocaya canlı gösterilecek 10 demo girdisini anlatır. Her senaryo çıktının **farklı bir kısmını** oynatır: TPS ölçeği, latency, availability, veri hacmi, iş yükü, yedek hedefi, fiyatlama stratejisi, personel oranı, NPV ufku ve belirsizlik aralığı. Her biri için komut, çıktı özeti ve neyin neden değiştiği yazılıdır.

**Tekrar üretmek için** (`Work_Emirhan` klasöründen):

```
python sunum_demo/demo_calistir.py          # 10 senaryonun hepsi, ~15 saniye
python sunum_demo/demo_calistir.py 4 8      # yalnızca Case 4 ve Case 8
```

Betik 42 komutu koşturur, tam çıktıları `sunum_demo/ciktilar/case_NN_*.txt` dosyalarına yazar ve sonda **42 komutun hepsinin birbirinden farklı çıktı verdiğini** SHA-256 ile doğrular (`ciktilar/demo_ozet.txt`). Aynı çıktıyı verecek tekrarlar (ör. Case 2'deki 10K noktası) bilinçli olarak çıkarıldı ve ilgili case'e atıfla verildi.

**Ortak varsayılanlar:** oltp_rw iş yükü (10 nokta + 4 aralık okuma + 4 yazma), %99,9 availability, 20 TB veri, yılda %15 veri büyümesi, `PRICE_EPOCH` = 2025-mid, `STAFF_RATIO_X86` = 1,0 (personel nötr), mid senaryo. Değerler aylık USD'dir; "$/TPS" aylık TPS başına maliyettir.

## Özet tablo

| # | Oynatılan girdi | Değişen çıktı kısmı | Tek cümlelik bulgu |
|---|---|---|---|
| 1 | Referans: 10K TPS | Hepsi (taban çizgisi) | x86 $53,66, mainframe $113,93; başabaş personel oranı 2,16 |
| 2 | TPS: 1K / 3K / 30K / 50K | Kademe, SKU, yığın (PG → Oracle), $/TPS eğrisi | İki eğri de ölçekle düşer; 50K'da x86 Oracle RAC'a geçer |
| 3 | Latency: yok / 50 / 20 / 10 ms | Mainframe kademe serisi (5xx → 6xx → 7xx), kullanım tavanı | Alt-kapasite CP yavaş; sıkı hedef tam hızlı CP'ye iter |
| 4 | Availability + RPO/RTO | Topoloji (M1→M2→M4, X1→X2→X3), DR, GDPS, DB seçimi | RPO 0 + RTO 30 dk + %99,999 mainframe'de infeasible |
| 5 | Veri hacmi: 10 / 100 / 500 TB | Storage modeli, yedek hedefi, x86'da DB | 500 TB'ta mainframe storage + yedek toplamın %16,5'i |
| 6 | İş yükü profili | w, PCI başına TPS, kademe, IOPS, D_io, x86 SKU | Aynı 10K TPS, iş tanımına göre $26,51 – $132,84 |
| 7 | Yedek hedefi zorlama | Yedek kalemi, geri dönüş süresi, kısıt ihlali | Zorlanan cos_onprem 500 TB'ta kısıtı karşılamaz → TS7770 |
| 8 | Fiyatlama A / B / C (yıllık) | Base kademe, corridor, CoD günleri, yıllık toplam | Üç presette de TFP kazanır; fark %0,1 – %6,2 |
| 9 | Personel oranı | x86 personeli, oran, kazanan platform | 2,16'da eşitlik, 3,0'da mainframe %28 ucuz |
| 10 | NPV ufku + aralık | Yıllık kademe yolu, seviyelendirilmiş maliyet, low/mid/high, eşleştirilmiş senaryolar | Sonuç bir nokta değil bir bölge: oran 1,22 – 7,23 |

---

## Case 1: Referans nokta (10K TPS)

**Komut:** `python src/x86_model.py --tps 10000 --compare`

**Çıktı özeti:**

| | Mainframe | x86 |
|---|---|---|
| Seçim | M1, 3931-524 (24 CP, 16.380 PCI, 1.971 MSU) | vSphere / VM / PostgreSQL + Patroni, X1, 3 × 2×8c |
| Aylık toplam | $1.139.294 ($113,93/TPS) | $536.552 ($53,66/TPS) |
| Personel | $521.333 (38,6 FTE) | $521.333 (38,6 FTE, oran 1,0) |
| Personel hariç | $617.961 | $15.219 (40,6 kat fark) |

Oran 2,12; **başabaş personel oranı 2,16**. Konsolide edilmemiş park senaryosunda (tavan %17,5) x86 $65,19'a çıkar ve Oracle RAC'a geçer.

**Neden böyle:** Personel iki tarafta aynı eğriyle sayıldığı için (P kararı, KB-13) fark neredeyse tamamen yazılım lisans modelinden gelir: mainframe AWLC'ye $402.932 + üretim dışı $102.054 öderken PostgreSQL yığını abonelikler için $5.210 öder. Bu yüzden başlık sonucu "x86 daha ucuz" değil, "x86 personeli mainframe personelinin 2,16 katından azsa x86 daha ucuz" cümlesidir.

**Sunumda vurgulanacak:** başabaş personel oranı tezin başlık çıktısıdır; IBM'in aynı iş yükü vakaları 1,23 – 3,28 arasındadır.

---

## Case 2: TPS ölçeği

**Komutlar:** `python src/x86_model.py --tps {1000, 3000, 30000, 50000} --compare` (10K = Case 1)

| TPS | Mainframe | x86 | Oran | Başabaş |
|---|---|---|---|---|
| 1.000 | $291,89 (M1, 3931-407) | $118,98 (PG, 2×8c) | 2,45 | 2,66 |
| 3.000 | $182,52 (3931-424) | $79,82 (PG, 2×8c) | 2,29 | 2,37 |
| 10.000 | $113,93 (3931-524) | $53,66 (PG, 2×8c) | 2,12 | 2,16 |
| 30.000 | $78,31 (3931-732) | $38,41 (PG, 2×32c) | 2,04 | 2,06 |
| 50.000 | $68,89 (3931-759) | $35,25 (**Oracle RAC**, 2×8c, k = 7) | 1,95 | 2,05 |

**Neden değişiyor:**
- **Mainframe:** kademe 4xx → 5xx → 7xx'e çıkar. $/TPS 1K'dan 50K'ya ~4,2 kat düşer. Kaynakları: AWLC'nin kümülatif kademeli fiyatı (MSU arttıkça marjinal fiyat düşer), taban personel ekibi ve frame tabanı gibi sabit maliyetlerin yayılması.
- **x86:** 30K'ya kadar tek Patroni birincil düğümü büyür (2×8c → 2×32c). ~36K'nın üstünde Patroni tek yazıcı tavanı aşılır ve model Oracle RAC'a geçer: x86'nın kendi açık kaynak ↔ ticari veritabanı crossover'ı.
- Başabaş oranı ölçekle 2,66'dan 2,05'e iner: küçük hacimde mainframe'in sabit tabanı (AWLC taban ücreti) daha ağırdır.

**Sunumda vurgulanacak:** mainframe maliyet eğrisi düz değil, bükülüyor (Değerlendirme #1'deki "düz maliyet" tehdidine cevap). Oran yine de bütün hacimlerde ~2 civarında kalır.

---

## Case 3: Latency hedefi

**Komutlar:** `python src/mainframe_model.py --tps 10000 [--latency-ms 50 | 20 | 10]`, `python src/x86_model.py --tps 10000 --latency-ms 20`

| p99 hedefi | Kademe | Kullanım tavanı | Tahmini p99 | Aylık |
|---|---|---|---|---|
| yok | 3931-**5**24 (24 CP, alt-kapasite) | %90,0 | ~89 ms | $1.139.294 |
| 50 ms | 3931-**6**14 (14 CP) | %88,7 | 44,26 ms | $1.141.120 |
| 20 ms | 3931-**7**10 (10 CP, tam hız) | %81,9 | 16,16 ms | $1.152.860 |
| 10 ms | 3931-714 (14 CP, tam hız) | %61,2 | 9,40 ms | $1.190.268 |
| x86, 20 ms | 2×8c değişmez | %70 → %69,6 | 18,93 ms | $536.552 |

**Neden değişiyor:** Latency hedefi kuyruk modelinden (CP başına bağımsız M/M/1) bir kullanım tavanı türetir: `ρ_max = min(1 − E[X]·ln(1/(1−p)) / (hedef − D_io), 0,90)`. Alt-kapasite (4xx/5xx/6xx) CP'leri yavaştır, yani işlem başına CPU süresi E[X] büyüktür. Hedef sıkılaştıkça model daha az ama daha hızlı CP'li kademeye geçer. Personel değişmez ($521.333), çünkü P kararıyla personel kurulu kapasiteden değil iş yükünden hesaplanır. x86'da sabit gecikme (20 ifade × 0,15 ms ağ gidiş-dönüşü = 3,0 ms) baskındır; 20 ms hedefi seçimi değiştirmez.

**Sunumda vurgulanacak:** aynı kapasitenin farklı CP hızlarıyla satılması mainframe'e özgü bir mekanizmadır ve model bunu latency üzerinden yakalar.

---

## Case 4: Availability, RPO ve RTO

**Komutlar:**
- `python src/x86_model.py --tps 10000 --availability 0.9999 --rpo-seconds 0 --rto-minutes 120 --compare`
- `python src/x86_model.py --tps 10000 --availability 0.99999 --compare`
- `python src/mainframe_model.py --tps 10000 --availability 0.99999 --rpo-seconds 0 --rto-minutes 30`
- `python src/mainframe_model.py --tps 10000 --availability 0.99999`

| Hedef | Mainframe | x86 | Oran |
|---|---|---|---|
| %99,9 (Case 1) | M1, $113,93 | X1 PG, $53,66 | 2,12 |
| %99,99, RPO 0, RTO ≤ 120 dk | M2 (DR frame, CBU), $122,29 | X2 **Oracle** + Data Guard, $61,19 | 2,00 |
| %99,999 | M4 (GDPS CA), $143,97 | X3 PG (2+2 düğüm + tanık), $61,83 | 2,33 |
| %99,999, RPO 0, RTO ≤ 30 dk | **infeasible** | — | — |

**Neden değişiyor:**
- Availability olay tabanlı hesaplanır: saha olayı sıklığı × topolojinin kurtarma süresi + planlı kesinti (KB-07). M1 %99,962, M2 %99,994, M3 %99,998, M4 %99,99994.
- %99,99 + RPO 0'da x86'da **veritabanı değişir**: Patroni'nin iki siteli standby kümesi asenkrondur (RPO 5 sn), bu yüzden RPO 0 + elle geçiş için Oracle Data Guard (SYNC) seçilir.
- %99,999'da mainframe M4'e çıkar: GDPS $100.000/ay ve yarım fiyatlı DR frame'i (CBU) eklenir; yazılım değişmez (CBU kuralı). x86'da X3 iki sitede 2 + 2 düğüm ve bir tanık düğümüdür; DR payı %1.
- Son satır modelin gerçek bir sınırı yakaladığını gösterir: saniye düzeyinde kurtarma yalnızca GDPS CA'nın asenkron yazılım replikasyonuyla gelir, o da RPO 0 vermez; M3 ise %99,999'a yetmez.

**Sunumda vurgulanacak:** kullanıcı topoloji seçmez; availability, RPO ve RTO girer, topoloji ve storage kopya sayısı bunlardan türetilir.

---

## Case 5: Veri hacmi (ikinci crossover ekseni)

**Komutlar:** `python src/mainframe_model.py --tps 10000 --data-tb {10, 100, 500}` ve aynısı `x86_model.py ... --compare`

| Veri | Mainframe storage | Mainframe yedek | Mainframe toplam | x86 storage | x86 yedek | x86 toplam |
|---|---|---|---|---|---|---|
| 10 TB | $4.464 (DS8910F-993, 38 TB ham) | $4.917 (nesne depolama) | $1.134.938 | $166 (NVMe) | $4.555 (S3) | $535.983 |
| 100 TB | $31.749 (993, 380 TB ham) | $11.648 (nesne) | $1.174.412 | $1.435 (NVMe) | $7.788 (nesne) | $541.120 |
| 500 TB | $153.226 (**994**, 1.901 TB ham) | $75.420 (**TS7770**) | $1.383.956 | $14.274 (**AFA**) | $28.216 (nesne) | $614.783 (**Oracle**) |

**Neden değişiyor:**
- Mainframe'de storage + yedek 10 TB'ta toplamın %0,8'i, 500 TB'ta **%16,5**'idir. Compute sabitken storage veriyle büyüdüğü için veri hacmi TPS'ten bağımsız ikinci bir eksendir.
- 500 TB'ta DS8910F-993'ün z16 çerçevesine sığan 737 TB'ı aşılır, ayrı raflı 994'e geçilir.
- Yedek hedefi kendiliğinden değişir: 500 TB'ta tam geri yüklemenin M1'de 36 saate (RTO'nun yarısı) sığması gerekir; nesne depolamanın TCT yolu (5.000 MB/s) buna yetmez, model TS7770'e döner.
- x86'da 500 TB PostgreSQL'in yerel NVMe yuvalarına (24 × 30,72 TB / 1,3 ≈ 567 TB planlı veri) sığmaz; model paylaşımlı all-flash diziyle Oracle RAC'a geçer (K1: storage tipi DB mimarisine bağlı).

**Sunumda vurgulanacak:** "tam yığın" iddiasının somut karşılığı: storage'ı dışarıda bırakan bir karşılaştırma bu ekseni göremez.

---

## Case 6: İş yükü profili (TPS'in tanımı)

**Komutlar:** `python src/mainframe_model.py --tps 10000 --workload {redp_light, tpcb_like, oltp_heavy}` ve `x86_model.py --workload {tpcb_like, oltp_heavy} --compare`

| Profil | Bileşim | w | İşlem/s/PCI | Mainframe kademe | Mainframe aylık | IOPS | x86 |
|---|---|---|---|---|---|---|---|
| redp_light | Benchmark işlemi, Db2 yok | 1,00 | 7,94 | 3931-601 (1 CP) | $265.149 | 1.090 | (SQL yok, x86'da tanımsız) |
| tpcb_like | 1 okuma + 4 yazma | 4,61 | 1,72 | 3931-429 | $608.811 | 32.000 | $26,95 (göreli ağırlık 0,44) |
| oltp_rw | 10 + 4 aralık okuma + 4 yazma | 12,85 | 0,62 | 3931-524 | $1.139.294 | 58.000 | $53,66 (1,00) |
| oltp_heavy | 30 okuma + 6 yazma | 16,37 | 0,49 | 3931-532 | $1.328.424 | 100.000 | $63,45, 2×12c (1,31) |

**Neden değişiyor:** Kapasite köprüsü REDP-5320 işlemi cinsindendir (7,939 işlem/s/PCI). Gerçek bir işlem, bileşiminin CPU ağırlığı w'ye bölünür: `ham_TPS = PCI × 7,939 / w / (1 − f)`. Aynı "10.000 TPS" iş tanımına göre 1 CP'den 32 CP'ye uzanır. I/O da bileşimden gelir (tampon havuzu kaçağı + commit log yazımı), bu yüzden D_io 0'dan 0,45 ms'ye çıkar. x86'da aynı bileşim ifade maliyetleriyle göreli ağırlığa çevrilir.

**Sunumda vurgulanacak:** Değerlendirme #1'in en kritik tehdidi "TPS iki tarafta aynı birim değil"di. Bu case, bileşimin iki tarafa aynı tanımla taşındığını (KB-01) ve sonucu ne kadar oynattığını gösterir.

---

## Case 7: Yedek hedefi

**Komutlar:** `python src/mainframe_model.py --tps 10000 --data-tb 100 --backup-target {ts7770, aws_s3}` ve `--data-tb 500 --backup-target cos_onprem`

| Senaryo | Yedek kalemi | Geri dönüş | Aylık toplam |
|---|---|---|---|
| 100 TB, auto (Case 5) → on-prem nesne | $11.648 | ~10,4 sa | $1.174.412 |
| 100 TB, TS7770 zorla | $20.750 (2 küme, site başına 380 TB cache) | ~13,0 sa | $1.183.514 |
| 100 TB, AWS S3 zorla (hibrit) | $17.787 (747 TB Standard-IA, 2 × 10G DX) | ~25,9 sa | $1.180.551 |
| 500 TB, nesne depolama zorla | $75.420, **TS7770'e düşer** ("cos_onprem kısıtı karşılamadı") | ~31,4 sa | $1.383.956 |

**Neden değişiyor:** Üç hedef aynı hacim kuralıyla (4 haftalık tam + günlük artımlı + log) boyutlanır ve üç kısıta tabidir: 8 saatlik yedek penceresi, M1'de tam geri yüklemenin 36 saate sığması, nesne hedeflerinde TCT verimi (5.000 MB/s). `auto` kısıtları karşılayanların en ucuzunu seçer. Zorlanan hedef kısıtı karşılamazsa model sessizce yanlış bir sonuç vermek yerine feasible hedefe düşer ve bunu çıktıda yazar.

**Sunumda vurgulanacak:** yedek toplamda küçük ama topolojiyle etkileşir: M1'de geri yükleme kısıtı, yedek teknolojisini veri hacmiyle değiştirir.

---

## Case 8: Fiyatlama stratejileri A / B / C (yıllık mod)

**Komutlar:** `python src/mainframe_model.py --yearly --preset {steady_oltp, batch_heavy, retail_bursty} --avg-tps 10000`

| Preset (tepe/ort.) | A: Permanent | B: Base + On/Off CoD | C: TFP (base + corridor + CoD) | Kazanan |
|---|---|---|---|---|
| steady_oltp (1,5×, 10 gün) | $17,60M (3931-539) | $17,62M (538 → 539, **261 gün** CoD) | **$17,23M** (532 + corridor 632) | C, A'dan %2,1 |
| batch_heavy (2,5×, 30 gün) | $24,69M (3931-726) | $23,74M (624 → 726, 30 gün) | **$23,51M** (619 + corridor 625 → 726, 21 gün) | C, A'dan %4,8 |
| retail_bursty (3,5×, 20 gün) | $31,20M (3931-739) | $29,32M (717 → 739, 20 gün) | **$29,28M** (717 + corridor 722 → 739) | C, B'den yalnızca %0,1 |

**Neden değişiyor:** Yıllık mod 8.760 saatlik profil üretir ve yazılımı aylık R4HA tepesinden faturalar. A yılın tepesine göre kalıcı kapasite alır. B küçük bir base alır ve tepe günlerde geçici kapasite açar (resmî sınırlar: %100 kuralı, drawer sınırı, alt-kapasite kuralları). C buna her zaman açık, kullanıldıkça ödenen bir corridor ekler. Günlük dalgalanma corridor'un, seyrek mevsimsel tepeler CoD'nin alanıdır: steady_oltp'de B 261 gün CoD açmak zorunda kalıp A'dan bile pahalıya gelir.

**Sunumda vurgulanacak:** strateji farkı yalnızca %0,1 – %6,2'dir, çünkü donanım toplamın ~%10'u. x86'da bu esnekliğin karşılığı yoktur: kapasite tepe saate göre kurulur ve lisans boşta da ödenir (KB-11).

---

## Case 9: Personel oranı

**Komutlar:** `python src/x86_model.py --tps 10000 --staff-ratio {1.25, 2.16, 3.0} --compare` (1,0 = Case 1)

| STAFF_RATIO_X86 | x86 FTE | x86 personel | x86 toplam | Mainframe | Oran MF/x86 |
|---|---|---|---|---|---|
| 1,00 (ana senaryo) | 38,6 | $521.333 | $53,66 | $113,93 | 2,12 |
| 1,25 (konsolide IBM vakaları) | 48,3 | $651.666 | $66,69 | $113,93 | 1,71 |
| 2,16 (başabaş) | 83,4 | $1.126.079 | $114,13 | $113,93 | **1,00** |
| 3,00 | 115,9 | $1.563.999 | $157,92 | $113,93 | **0,72** |

**Neden değişiyor:** Personel ana senaryoda nötrdür: iki taraf aynı FTE eğrisini (iş yükünün PCI eşdeğeri) kullanır. Platformlar arası personel farkı için bağımsız bir kaynak yoktur; IBM kaynaklı vakalar 1,23 – 15,4 arasında dağılır. Bu yüzden oran bir aralık parametresi değil, duyarlılık eksenidir ve başabaş değeri ikiye bölmeyle bulunur (her adımda x86 yığını yeniden optimize edilir).

**Sunumda vurgulanacak:** mainframe'in kazandığı bölge açıkça tanımlıdır: x86 personeli aynı iş için mainframe personelinin 2,16 katını aşarsa.

---

## Case 10: NPV ufku ve belirsizlik aralığı

**Komutlar:** `python src/{mainframe,x86}_model.py --tps 10000 --npv --years {3, 5, 10}`, `python src/mainframe_model.py --tps 10000 --range`, `python src/x86_model.py --tps 10000 --range --compare`

**NPV (yılda %10 yük büyümesi, %7 iskonto):**

| Ufuk | Mainframe NPV | Mainframe seviyelendirilmiş | x86 NPV | x86 seviyelendirilmiş |
|---|---|---|---|---|
| 3 yıl | $41,90M | $121,11 | $18,73M | $54,14 |
| 5 yıl | $68,62M | $115,70 | $32,07M | $54,07 |
| 10 yıl | $142,07M | $111,51 | $69,40M | $54,47 |

Mainframe kademe yolu yalnızca yükselir: 524 → 527 → 530 → 534 → 537 ve 6. yılda 5xx serisinin en büyük kademesi (539) yükü taşımadığı için 6xx serisine geçiş, 3931-637 ($3,29M capex; kalıcı yükseltmede seri yalnızca yukarı gidebilir). Mainframe'in seviyelendirilmiş maliyeti ufuk uzadıkça düşer (1. yıl capex'i yayılır); x86'nınki neredeyse sabittir, çünkü %97'si personeldir.

**Aralık (10K TPS, $/TPS/ay):**

| | low | mid | high |
|---|---|---|---|
| Mainframe | $31,44 (3931-438) | $113,93 | $565,95 (M2, 3931-635) |
| x86 | $22,01 | $53,66 | $124,91 (OCP-V, 2×24c) |

**Eşleştirilmiş senaryolar** (platforma özgü parametreler zıt uçlarda, ortak parametreler iki tarafta aynı):

| Senaryo | Mainframe | x86 | Oran | Başabaş |
|---|---|---|---|---|
| x86 lehine | 383,08 | 52,95 | 7,23 | 7,33 |
| orta | 113,93 | 53,66 | 2,12 | 2,16 |
| mainframe lehine | 70,49 | 57,92 | 1,22 | 1,24 |
| ortak low | 81,86 | 22,66 | 3,61 | 3,78 |
| ortak high | 181,78 | 120,54 | 1,51 | 1,52 |

Tornado'nun ilk sıraları: mainframe'de okuma SQL CPU maliyeti ($888K – $1,57M), AWLC fiyat seviyesi, personel eğrisi; x86'da personel eğrisi ve ücret (ortak parametreler).

**Neden böyle:** Kaynakla daraltılamayan her parametre low / mid / high olarak taşınır. İki platformun kendi köşelerini ayrı ayrı okumak ortak parametreleri (personel, ücret) iki tarafta çelişik değerlere koyardı; eşleştirilmiş senaryolar bunu engeller (KB-18).

**Sunumda vurgulanacak:** tezin çıktısı bir crossover **noktası** değil **bölgesi**dir. Mid'de x86 ~2 kat ucuz; mainframe lehine bütün belirsizlikler bir arada bile oran 1,22'ye iner ama tersine dönmez (10K TPS'te). 30K – 50K'da mainframe lehine senaryoda oran tersine döner (x86 dokümanı §16.3).

---

## Demo akışı önerisi (15 dakika)

1. Case 1 (2 dk): taban çizgisi ve başabaş oranı.
2. Case 6 (2 dk): TPS'in tanımı neden önemli.
3. Case 2 ve 3 (3 dk): ölçek ve latency, mainframe'e özgü mekanizmalar.
4. Case 4 ve 5 (3 dk): availability ve veri hacmi, tam yığın.
5. Case 8 (2 dk): CoD/TFP, x86'da karşılığı yok.
6. Case 9 ve 10 (3 dk): personel ve belirsizlik → crossover bölgesi.

Case 7 soru gelirse gösterilir.
