# Ortak Modül — İki Platformun Paylaştığı Parametreler ve Kurallar (v1)

*Tarih: 2026-11-02 · Güncelleme: 2026-11-16 (Adım 7: F, E, P kararları ve x86 modeli) · Kod: `src/common_model.py` · İlgili: `mainframe_model_documentation_v3.md` (mainframe'deki kullanım), `acik_sistem_arastirma_plani_v1.md` §12.2 (bu modülün planı), `benzer_calismalar_v1.md` §8 (üretim dışı ortamlar)*

Bu doküman Adım 6'da kurulan ve Adım 7'de genişletilen ortak modülün **güncel halini** anlatır. Adım 7'de ortak modüle üç şey eklendi: işlem bileşimi ve ondan türeyen I/O ve yedek hacmi kuralları (§11, F kararı), iki tarafın aynı personel eğrisi (§12, P kararı) ve fiyat dönemlerinin low / mid / high üçlüleri (§7, E kararı). Köprülerin kendisi `kopruler_v1.md`'de, x86 tarafındaki kullanım `x86_model_dokumantasyonu_v1.md`'dedir. Ortak modül, mainframe ile kümelenmiş x86'nın aynı disiplinle karşılaştırılabilmesi için iki tarafta **aynı olması gereken** her parametreyi ve kuralı tek bir yerde toplar. Değişikliklerin tarihçesi `PROJECT_LOG.md`'dedir.

Etiketler önceki dokümanlarla aynıdır: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** kaynaktan hesaplanan değer · **[VENDOR]** üretici kaynağı.

---

## 0. Neden bir ortak modül

Bir karşılaştırma ancak iki tarafın aynı varsayımlarla hesaplandığı kadar güvenilirdir. Örnekler:

- Mainframe ile x86 aynı veri merkezinde durur. Elektrik kesintisinin ya da insan hatasının sıklığı platforma göre değişmez.
- Bir Db2 DBA'sı ile bir PostgreSQL DBA'sı aynı iş piyasasından işe alınır. Ücret tablosu iki tarafta farklıysa sonuç ücret farkını ölçer, platform farkını değil.
- 5 yıllık NPV'de iki taraf farklı iskonto oranıyla indirgenirse sermaye maliyetinin kendisi bir taraf lehine çalışır.

Bu parametreler platform modüllerinde ayrı ayrı tanımlansaydı, bir aralık senaryosu ya da kullanıcı fiyat dosyası yalnızca bir tarafı değiştirebilirdi. Ortak modül bunu **yapısal olarak** önler: parametre tek yerde tanımlıdır ve iki taraf da onu oradan okur.

**Platforma özgü kalanlar.** Kurtarma süreleri (GDPS ile Data Guard / Patroni), kapasite köprüsü (LSPR + REDP ile SPEC + sysbench), donanım ve lisans fiyatları, storage ürünleri ve yedek yolu (DS8900F TCT ile pgBackRest / RMAN). Bunlar platform modüllerinde kalır. FTE eğrisi Adım 6'da platforma özgüydü; P kararıyla (Adım 7) ortak oldu (§12).

---

## 1. Parametre sahipliği

**Kural:** Her parametrenin tek bir sahibi vardır. Ortak parametreler yalnızca `common_model.py`'de tanımlıdır; platform modülleri onları `cm.X` olarak, her çağrıda okur. Kendi kopyalarını tutmazlar.

**Neden "her çağrıda":** Python'da `from common_model import X` bir kopya bağlar. Aralık analizi ortak modüldeki değeri değiştirdiğinde kopya eski değerde kalırdı. Sonuç sessizce yanlış olurdu.

**Geçici değiştirme (`use_values`).** Aralık ve tornado analizi parametreleri geçici olarak değiştirir. `cm.use_values(değerler, modüller)` her adı sahibi olan modülde bulur, değiştirir ve bağlam sonunda geri alır. Bir ad iki modülde birden tanımlıysa ("gölgeleme") hata verir, çünkü hangi kopyanın okunacağı belirsizdir. Mainframe modülünün `m.use_values(...)` çağrısı bu fonksiyona devreder; mevcut araçlar ve testler değişmeden çalışır.

**Geriye uyumlu okuma.** `mainframe_model` modülü, taşınan bir adı (örneğin `m.NPV_TPS_GROWTH`) okuyan eski kodu ortak modüldeki güncel değere yönlendirir (Python modül düzeyi `__getattr__`). Yazma yalnızca `use_values` ile yapılır.

**Test:** `test_shared_parameters_have_single_owner`. Hiçbir büyük harfli ad iki modülde birden tanımlı değildir. Mainframe'den okunan ortak ad ortak modülün güncel değeridir. `use_values` değişikliği sahibinde yapar ve geri alır.

---

## 2. Saha olayları ve elle geçiş karar süresi

Availability denkleminin ortak kısmı (mainframe v3 §6.3; x86 planı §8.1):

```
D_saha(T_rec) = λ_saha × [ (1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec) ]
```

`site_downtime_hours(T_rec_saat, düzey)` bu terimi verir. T_rec platforma ve topolojiye özgüdür; geri kalan her şey ortaktır.

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| λ_saha (olay/yıl) | 0,05 | 0,15 | 0,25 | [Uptime2025-PR] |
| d_kısa (saat) | 1 | 2 | 4 | [ASSUME] |
| p_uzun | 0,08 | 0,15 | 0,30 | [DCF2022-Uptime] |
| d_uzun (saat) | 24 | 48 | 72 | SG24-8446 GDPS'siz DR aralığının üst ucu |
| Düzey anahtarı | `SITE_EVENT_LEVEL` (aralık parametresi) | | | |

**Elle geçiş karar süresi.** Otomasyonsuz bir site geçişinde (mainframe M2, x86 X2) kurtarma süresinin çoğu teknoloji değil insan kararı ve runbook'tur: felaketin ilanı, onay zinciri, uygulamaların yönlendirilmesi. Bu pay iki tarafta aynı olmalıdır; aksi halde M2–X2 karşılaştırması "hangi ekip daha hızlı karar verir" sorusuna dönüşür (x86 planı §8.2).

```
T_rec(elle) = MANUAL_FAILOVER_DECISION_MINUTES[düzey] + teknik_geçiş(platform, düzey)
```

| | low | mid | high |
|---|---|---|---|
| Karar süresi (ortak) | 45 dk | 90 dk | 180 dk |
| Mainframe M2 teknik geçiş (Metro Mirror'dan IPL, ağ yönlendirme) | 15 dk | 30 dk | 60 dk |
| M2 toplamı | 60 dk | 120 dk | 240 dk |

Toplam, Adım 6'dan önceki M2 kurtarma süresiyle aynıdır; yalnızca iki bileşene ayrıldı. Ayrıştırma oranı kaynaklı değildir [ASSUME]. Karar süresinin düzeyi platformun `RECOVERY_LEVEL`'ı ile birlikte seçilir.

**Test:** `test_manual_failover_split`.

---

## 3. Personel ücretleri ve taban ekip

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| `LOADED_WAGE_USD` (yüklü maliyet, USD/FTE/yıl) | 122.000 | 162.000 | 215.000 | BLS OEWS Mayıs 2025 medyanlarından karma brüt $95K / $120K / $150K × yan hak çarpanı 1,28 / 1,35 / 1,43 [BLS-OOH, BLS2026-ECEC, IDC2016-ConnectedMF] |
| `STAFF_FLOOR_FTE` (7/24 asgari ekip) | 3 | 4 | 5 | [ASSUME]; mainframe v3 §7.7 |
| Düzey anahtarı | `WAGE_LEVEL` (aralık parametresi) | | | |

- **Ücret ile ekip büyüklüğü ayrıldı.** Adım 6'dan önce mainframe'in `STAFF_SCENARIO`'su hem FTE eğrisini hem ücreti birlikte seçiyordu. Şimdi `STAFF_SCENARIO` (platforma özgü) eğriyi ve tabanı, `WAGE_LEVEL` (ortak) ücreti seçer. Köşe senaryolarında ikisi aynı yöne çekildiği için low / mid / high toplamları değişmedi. Tornado'da ise personel iki satıra ayrıldı: "ekip ne kadar büyük" ve "bir kişi ne kadar".
- **Taban ekip iki tarafta aynıdır.** Adım 7'den beri taban, ortak personel eğrisinin (§12) bir parçasıdır ve `STAFF_SCENARIO` ile seçilir.

---

## 4. Enerji

| Parametre | Değer | Dayanak |
|---|---|---|
| `ELECTRICITY_USD_PER_KWH` | 0,12 | [ASSUME] ABD ticari ortalaması |
| `HOURS_PER_MONTH`, `HOURS_PER_YEAR` | 730, 8.760 | |

`energy_monthly(kW)` = kW × fiyat × 730. Güç tüketimi (frame başına 30 kW, sunucu başına W) platforma özgüdür.

---

## 5. Nesne depolama ve bulut yedek fiyatları

Yedek hedeflerinden ikisi platformdan bağımsızdır: kurum içi S3 uyumlu nesne depolama ve AWS S3 (hibrit). Mainframe'de veri DS8900F TCT ile, x86'da yedekleme yazılımıyla gider. Yol ve verim kısıtı platforma özgüdür, fiyat fonksiyonu ortaktır.

| Parametre | Değer | Dayanak |
|---|---|---|
| `COS_HW_USD_PER_TB` | 100 (aralık 60–200) | [MinIO-ObjectTCO] |
| `COS_MIN_SITE_CAPEX_USD` | 70.000 | [MinIO-ObjectTCO] |
| `COS_SW_USD_PER_TB_MONTH` | 5 (aralık 0–10) | [MINIO-TCO → ASSUME] |
| `COS_KW_PER_PB` | 1,5 | [ASSUME] |
| `S3_USD_PER_GB_MONTH` (Standard-IA) | 0,0125 | [Nubbo2026-S3] |
| `S3_MIN_STORAGE_DAYS` | 30 | [Nubbo2026-S3] |
| `S3_RETRIEVAL_USD_PER_GB` | 0,01 | [Nubbo2026-S3] |
| `S3_PUT_USD_PER_1000` | 0,01 | [Nubbo2026-S3] |
| `DX_PORT_USD_PER_HOUR` (10 Gbps) | 2,25 | [AWS-DXPricing] |
| `DX_EGRESS_USD_PER_GB` | 0,02 | [AWS-DXPricing] |
| `WAN_CIRCUIT_USD_PER_MONTH` | 2.000 | [ASSUME] |

Fonksiyonlar:

- `onprem_object_store(TB_site_başına, site_sayısı)`: donanım capex'i, aylık abonelik, kW.
- `s3_hybrid(TB, günlük_TB, geri_yükleme_TB, gereken_MB/s, saklama_haftası, yıllık_geri_yükleme)`: hat sayısı ve aylık hizmet kalemleri.

Amortisman ve bakım oranı platformun storage kuralından gelir. Mainframe'de bunlar `STORAGE_AMORTIZATION_YEARS` ve `STORAGE_MAINT_RATE_ANNUAL`'dır.

---

## 6. Storage fiyatlama sözleşmesi

Platformlar arası storage karşılaştırmasındaki en büyük tuzak fiyatın tanımıdır. DS8900F fiyatı **ham TB** başına listelenir. x86 AFA fiyatları çoğunlukla **etkin TB** (veri azaltımı sonrası) başına verilir (x86 planı §7.2). Aynı kapasite iki tanımla 4–10 kat farklı fiyatlanabilir.

**Sözleşme:**

1. **Boyutlandırma zinciri iki tarafta aynı sırayla ham TB üretir:** mantıksal veri → planlama ufku → DB ek yükü → sıkıştırma/veri azaltımı → RAID ya da replika kullanılabilir oranı → ham TB.
2. **Her fiyat teklifi önce ham TB başına liste fiyatına çevrilir** (`price_per_raw_tb`). İndirim yalnızca bir kez ve listeye uygulanır (`net_price`).
3. **Veri azaltım oranı boyutlandırmada bir kez kullanılır.** Fiyata ikinci kez gömülmez; etkin TB fiyatı geri çevrilir.

| Teklifin tabanı | Ham TB liste fiyatına çevirme |
|---|---|
| ham | olduğu gibi |
| kullanılabilir | × RAID kullanılabilir oranı |
| etkin | × RAID kullanılabilir oranı × veri azaltım oranı |

Örnek: $200/etkin TB, veri azaltımı 2,5, RAID kullanılabilir 0,75 → $375/ham TB. Mainframe tarafında DS8900F fiyatı zaten ham TB tabanındadır ve host sıkıştırması (`HOST_COMPRESSION_RATIO` = 1) boyutlandırmadadır. Sözleşme mainframe sonuçlarını değiştirmez; x86 tarafında AFA fiyatları bu fonksiyondan geçecektir.

**Test:** `test_storage_price_contract`.

---

## 7. Fiyat dönemi (PRICE_EPOCH) ve fiyat yaşları

2026'da bellek ve SSD fiyatlarında bir şok yaşandı (x86 planı §5.2). 64 GB RDIMM 2025 ortasında ~$255 iken 2026 Q3'te $2.245–3.400 oldu. Kurumsal NVMe ~$115/TB'tan ~$753/TB'a çıktı. Mainframe çapaları şok öncesinden; x86 bileşenleri hangi dönemden fiyatlanırsa karşılaştırma o dönemle yapılmalıdır.

**E kararı (Emirhan, 2026-11-16; `kopruler_v1.md` KB-15).** Ana senaryo şok öncesi dönemdir (`PRICE_EPOCH` = `2025-mid`), çünkü iki tarafın çapaları aynı dönemde olmalıdır. `2026-Q3` duyarlılık senaryosudur. Her dönemde emtia fiyatı tek sayı değil, low / mid / high üçlüsüdür; hangi düzeyin okunacağını tek bir aralık parametresi (`COMPONENT_PRICE_LEVEL`) seçer. DRAM ve NVMe için ayrı aralık parametresi yoktur; aksi halde tornado'da aynı belirsizlik iki kez sayılırdı.

| Dönem | DRAM USD/GB (low / mid / high) | Kurumsal NVMe USD/TB (low / mid / high) | Kaynak |
|---|---|---|---|
| `2025-mid` (şok öncesi, **ana senaryo**) | 3 / 4 / 5,5 | 80 / 115 / 180 | 64 GB DDR5 RDIMM ~$255 [PCSP2026-Server]; 30 TB sınıfı NVMe ~$115/TB, Q3 2025 [PCSP2026-SSD]; uçlar [ASSUME] |
| `2026-Q3` (şok, duyarlılık) | 16 / 35 / 53 | 300 / 753 / 1.172 | 64 GB ~$1.000 sözleşme [PCSP2026-Server]; Ağustos–Ekim 2026 perakende $2.245 / $3.400 [CapCompute-RAM, Bacloud2026-RAM]; U.2 $300–1.172/TB [PCSP2026-SSD] |

**Kurallar:**

- Emtia bileşen fiyatları (DRAM, NAND) dönem tablosundan okunur (`component_price(ad, dönem, düzey)`). Platform modülü kendi sabitini tutmaz.
- Bu fiyatlar piyasa (sokak ya da sözleşme) fiyatıdır, liste fiyatı değildir. x86 modelinde bunlara OEM indirimi **uygulanmaz**; indirim yalnızca liste kalemlerine ve bir kez uygulanır.
- **Sınırlama:** IBM'in z16 ve DS8900F fiyatlarının şoktan etkilenip etkilenmediğine dair kaynak yok. Mainframe fiyatları dönemden bağımsız tutulur. Dönem `2026-Q3` seçildiğinde x86 şoklu, mainframe şoksuz fiyatlanır. Bu fark sonuçlarda mainframe lehine bir yanlılık olabilir. Tezde açıkça yazılmalı, x86 sonuçları iki dönemle birlikte raporlanmalıdır. 10K TPS'te x86 mid sonucu `2025-mid`'de $53,66, `2026-Q3`'te $53,99/TPS/ay'dır (x86 dokümanı §4); şokun etkisi bu ölçekte küçüktür, çünkü bellek ve NVMe toplamın küçük bir payıdır.
- **Fiyat yaşları görünür olmalı.** Her kayıtlı fiyat parametresinin kaynak yılı tutulur; `--price-vintages` en eskiden yeniye listeler. Mainframe tarafında en eski fiyatlar 2004 (AWLC) ve 2006 (TS7700 küme tabanı) tarihlidir.
- **2004 nominal AWLC fiyatları 2026 USD'ye otomatik çevrilmez.** Güncel liste fiyatı bilinmediği için dönüşüm `SW_PRICE_LEVEL_FACTOR` aralığının işidir. Aralığın üst ucu 1,75, ABD TÜFE'sinin 2004–2026 artışıyla aynı büyüklüktedir. Otomatik TÜFE çarpanı uygulamak "IBM fiyatları enflasyonla arttı" varsayımını gizlice kodlardı.

**Test:** `test_price_epoch`.

---

## 8. NPV kuralları

İki taraf aynı ufuk, iskonto oranı, büyüme ve fiyat artış sınıflarıyla indirgenir (mainframe v3 §9.10).

| Parametre | Değer | Aralık | Dayanak |
|---|---|---|---|
| `NPV_YEARS` | 5 | | [ASSUME] amortisman süresiyle aynı |
| `NPV_DISCOUNT_RATE` (nominal) | 0,07 | tarama %5 / %7 / %10, köşelere girmez | [Damodaran2026-WACC] |
| `NPV_TPS_GROWTH` | 0,10 | senaryo girdisi | |
| `SW_PRICE_ESCALATION` | 0,03 | 0–0,06 | [IBM-PRICE-2026 → ASSUME] |
| `HW_SERVICE_ESCALATION` | 0,03 | 0–0,06 | [IBM-PRICE-2026 → ASSUME] |
| `WAGE_ESCALATION` | 0,033 | 0,025–0,045 | [BLS2026-ECI] |
| `ENERGY_ESCALATION` | 0,04 | 0,015–0,056 | [EIA-EPM-5.3] |
| `NPV_RESIDUAL_FRACTION` | 0 | 0–1 (tarama) | [ASSUME] tutucu |

- **Zamanlama:** satın almalar dönem başında (t = y − 1), işletme giderleri yıl sonunda (t = y).
- **Fonksiyonlar:** `esc(oran, yıl)`, `discount_and_sum`, `residual_value(..., ömür)`, `finish_npv(...)`. Sonuç NPV, yıllık eşdeğer maliyet ve seviyelendirilmiş $/TPS/ay'dır. Kalan değerin ömrü platformun amortisman süresidir: mainframe 5 yıl, x86'da 3–5 yıl.
- **Teknoloji yenilemesi** (z17 ya da yeni sunucu nesli) iki tarafta birlikte dışarıdadır. x86'da 5 yıl içinde bir sunucu yenilemesi modellenecekse mainframe'de de nesil geçişi modellenmelidir.
- `NPV_COMMON_RANGE_PARAMETERS` dört artış oranını aralık analizine taşır. Platform kendi NPV parametrelerini (mainframe: `TFP_GROWTH_PRICE_FACTOR`) ekler.

---

## 9. Üretim dışı ortamlar (NONPROD)

Geliştirme, test, QA ve ön-üretim ortamları. Benzer çalışmalar taramasına göre bu kalem iki platformda çok farklı büyüklükte olabilir: IBM Eagle'a göre mainframe'de üretim +%20, dağıtıkta çoğu zaman +%200 [IBM2013-TCOLessons; benzer_calismalar_v1 §3.2]. Emirhan'ın kararı (2026-11-02): iki tarafa ayrı, aralıklı bir çarpan; düşük uç 0, "kapsam dışı" senaryosu.

**Kural (iki tarafta aynı):**

```
üretim_dışı = NONPROD_FACTOR(platform) × birincil site {yazılım + bilgi işlem donanımı (amortisman + bakım) + enerji + birincil storage}
```

`nonprod_cost(çarpan, kalemler)`, `NONPROD_COMPONENTS` anahtarlarının hepsini ister. Eksik kalem hata verir, böylece bir platform bir kalemi sessizce atlayamaz.

| Kapsama giren | Kapsama girmeyen | Gerekçe |
|---|---|---|
| Yazılım lisansları | DR sitesi (DR frame, ikincil storage, standby sunucular) | Üretim dışı ortamlar felaket kurtarma kapsamında değildir |
| Bilgi işlem donanımı (amortisman + bakım) | Site otomasyonu (GDPS, Oracle MAA lisansları) | Aynı |
| Enerji | Yedekleme | Üretim dışı veri yedeklenmez ya da ihmal edilir [ASSUME] |
| Birincil storage | Personel | Üretim iş yüküne göre boyutlanır (P, §12); üretim dışını aynı ekip işletir [ASSUME] |

**Kapasite eşdeğeri maliyet.** Çarpan, üretim dışı kapasitenin üretimle aynı birim fiyattan alındığını varsayar. Mainframe'de bu, AWLC'nin kademeli marjinal fiyatını ve IBM'in geliştirme/test fiyatlandırma tekliflerini yok sayar; mainframe aleyhine tutucudur. x86'da açık kaynak yazılımın üretim dışı lisansı genellikle sıfırdır, ama Oracle ve VMware lisansları çekirdek başınadır. Bu fark x86 modelinde kalem kalem ele alınmalıdır.

| Platform | low | mid | high |
|---|---|---|---|
| Mainframe | 0 | 0,20 [IBM2013-TCOLessons] | 0,50 [ASSUME] |
| x86 (`NONPROD_FACTOR_X86`, N kararı) | 0 | 0,50 [DERIVED, ASSUME] | 1,00 [ASSUME]; 2,0 [IBM2013-TCOLessons] yalnızca stres senaryosu, aralıkta değil |

**Karşılaştırmada kullanım.** İki platformun çarpanı ayrı aralık parametreleridir. Karşılaştırma katmanında "kapsam dışı" senaryosu iki çarpanın birlikte 0 olduğu durumdur. Tez, sonuçları bu senaryo ile mid senaryo yan yana raporlamalıdır.

**N kararı (Emirhan, 2026-11-16; `kopruler_v1.md` KB-14).** IBM Eagle'ın "dağıtıkta +%200" değeri üretici kaynağıdır ve konsolide edilmemiş eski dağıtık ortamları anlatır. x86 aralığı bu yüzden 0 / 0,5 / 1,0'dır (orta değer: X1'in 3 düğümlük birincil sitesine karşı tek düğümlük staging ≈ 0,33 + küçük dev/test düğümleri ≈ 0,1–0,2; üst uç staging'in tam küme kopyası olması); 2,0 ayrı bir stres senaryosu olarak raporlanır (10K TPS'te x86 $53,66 → $54,69/TPS/ay; açık kaynak yığında üretim dışı lisans sıfır olduğu için etki küçüktür).

**Test:** `test_nonprod_factor` (mainframe) ve `test_nonprod_x86`. Mainframe'deki etkisi v3 §7.9'dadır: Adım 6'da 10K TPS'te +$84.825/ay (başlık $84,62 → $93,10); Adım 7 varsayılanlarıyla +$102.054/ay.

---

## 10. İki fiyat modu

Emirhan'ın önerisi (2026-11-02). İki mod:

1. **Kaynaklı fiyat seti (varsayılan).** Her fiyat parametresi kaynaklı bir değer ya da aralıkla gelir.
2. **Kullanıcı fiyatları.** Bir JSON dosyası kayıtlı adların bir kısmını ya da tamamını geçersiz kılar.

**Fiyat kaydı (`PRICE_REGISTRY`).** Her fiyat parametresi bir kayıtla tanımlıdır: sahip modül, birim, kaynak, kaynak yılı, bağlı aralık parametresi ve açıklama. Platform modülü kendi fiyatlarını `register_prices` ile kaydeder. Bir ad iki platformda kayıtlıysa hata verilir. Mainframe 18, x86 13, ortak modül 12 fiyat kaydeder.

**Dosya biçimi:**

```json
{
  "_not": "Kurumumuzun 2026 teklifi",
  "HARDWARE_COST_PER_MIPS": 250,
  "LOADED_WAGE_USD": 140000,
  "GDPS_MONTHLY_BASE": {"ca": 80000}
}
```

- `_` ile başlayan anahtarlar açıklamadır, yok sayılır.
- Sayı verilen bir sayı parametresi doğrudan yazılır.
- Düzey tablosu olan bir parametreye (`LOADED_WAGE_USD`) tek sayı verilirse üç düzeye de yazılır. Nesne verilirse yalnızca verilen anahtarlar değişir (`GDPS_MONTHLY_BASE`'de `metro_global` kaynaklı kalır).
- Bilinmeyen ad, negatif değer, sayı olmayan değer ya da tabloda olmayan anahtar reddedilir. Model hiçbir değeri değiştirmeden durur.

**Sabitleme (pinning).** Kullanıcının verdiği bir fiyat artık belirsiz sayılmaz. Bağlı aralık parametresi `PINNED` kümesine eklenir ve aralık ve tornado analizinden çıkarılır (`unpinned`). Örneğin `LOADED_WAGE_USD` verilince `WAGE_LEVEL` taranmaz. Aksi halde aralık analizi kullanıcının gerçek fiyatını kaynaklı aralıkla ezerdi.

**CLI (iki platform modülünde aynı):**

| Seçenek | İşlev |
|---|---|
| `--prices DOSYA` | Kullanıcı fiyatlarını uygular; geçersiz kılınan ve sabitlenen adları yazar |
| `--list-prices` | Kaynaklı fiyat setini JSON şablonu olarak yazar |
| `--price-vintages` | Fiyatların kaynak yıllarını en eskiden yeniye listeler |

Çıktıda fiyat modu yazılır: "kaynaklı fiyat seti" ya da "kullanıcı fiyatları (N parametre geçersiz kılındı)".

**Test:** `test_two_price_modes`, `test_price_file_mode_x86` ve iki CLI testi.

---

## 11. İşlem bileşimi, bileşimden I/O ve yedek hacmi (KB-01, KB-09, KB-10; F kararı)

Crossover TPS başına maliyet üzerinden kurulduğu için "1 işlem" iki tarafta **aynı bileşimle** tanımlanmalıdır. Adım 6'ya kadar bileşim mainframe modülündeydi; x86 modeliyle birlikte ortak modüle taşındı (`WORKLOAD_MIXES`).

| Profil | Nokta okuma | Aralık okuma | Yazma | Commit | Kaynak |
|---|---|---|---|---|---|
| `tpcb_like` | 1 | 0 | 4 | 1 | TPC-B bileşeni |
| `oltp_rw` (varsayılan) | 10 | 4 | 4 | 1 | sysbench oltp_read_write [Kopytov-sysbench, Tencent-PG-TestMethods] |
| `oltp_heavy` | 30 | 0 | 6 | 1 | ~1,3 ms Db2 CPU'luk saha ölçümü [Catterall2019]; bileşim [ASSUME] |

`redp_light` (IBM REDP-5612'nin hafif CICS-Db2 işlemi) yalnızca mainframe'de tanımlıdır. Bileşimi yayımlanmadığı için x86 modeli onu reddeder.

**F kararı (Emirhan, 2026-11-16).** sysbench oltp_rw'nin 4 aralık okuması (her biri 100 satır) Adım 6'ya kadar nokta okuma sayılıyordu. Artık ayrı sayılır ve bir aralık okuması nokta okumanın `RANGE_READ_WEIGHT` katı CPU harcar:

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| `RANGE_READ_WEIGHT` | 3,4 | 3,65 | 3,9 | [DERIVED] Vonng PostgreSQL alt testleri; BEGIN/COMMIT maliyeti b = 0,73 µs iken 3,44, b = 0 iken 3,94 (`kopruler_v1.md` KB-01) |

- **Mainframe'de** w'yi belirler: CPU = taban + (nokta + aralık × ağırlık) × okuma CPU'su + yazma × yazma CPU'su. oltp_rw'de w 9,15'ten 12,85'e çıktı (v3 §4.4, §7.11).
- **x86'da** oltp_rw'nin ölçülmüş çapasının içindedir (sysbench zaten aralık okumalarıyla koşulur); yalnızca diğer profillerin oltp_rw'ye göre ağırlığını belirler.
- **Varsayım:** PostgreSQL'de ölçülen göreli maliyetin Db2 for z/OS'a taşınabildiği. K6 ölçümü yalnızca PostgreSQL tarafını kalibre edebilir.
- Aralık parametresidir; iki tarafı **aynı yönde** etkiler. Karşılaştırma katmanında ortak parametre olarak iki tarafa aynı değerle uygulanır (§14).

**Bileşimden I/O (KB-09).** Senkron okuma I/O'su = okuma × `GETPAGES_PER_SQL_READ` (4) × (1 − `BP_HIT_RATIO`); senkron yazma I/O'su = commit × `LOG_SYNC_IO_PER_COMMIT` (1); IOPS = ikisi + yazma × `ASYNC_WRITE_IO_PER_SQL_WRITE` (0,5). Db2 buffer pool'u ile PostgreSQL `shared_buffers` + OS önbelleği aynı biçimde modellenir; IOPS iki tarafta aynı girdidir. `BP_HIT_RATIO` iki tarafta da aralık parametresidir (0,99 / 0,95 / 0,90). I/O hesabında okuma sayısı ağırlıksızdır (oltp_rw'de 14): bir aralık okuması da 4 getpage sayılır, 100 satırlık aralığın ek sayfaları tampon havuzunda sıcak varsayılır [ASSUME]. F kararı yalnızca CPU'yu değiştirir.

**Senkron kopya gecikmesi.** `REPLICATION_S_PER_KM` = 10 µs/km gidiş-dönüş [FİZİK], `METRO_DISTANCE_KM` = 20 [ASSUME]. Metro Mirror, Data Guard SYNC ve PostgreSQL senkron replika commit başına aynı gidiş-dönüşü ekler.

**Storage boyutlandırmasının ortak girdileri.** `DEFAULT_DATA_VOLUME_TB` 20, `DEFAULT_DATA_GROWTH` %15/yıl, `STORAGE_PLANNING_YEARS` 3, `STORAGE_IOPS_CEILING` 0,70 (tepe IOPS'un en çok %70'i); `planned_data_tb()`.

**Yedek hacmi kuralı (KB-10).** `backup_volumes()`: tam kopya = planlanan veri × hafta × (1 tam + 6 artımlı × günlük değişim) [Hendley2024-IDUG]; log = ortalama TPS × işlem başına log baytı × 86.400 × 7 × hafta. Saklama (`BACKUP_RETENTION_WEEKS` 2 / 4 / 8), günlük değişim (%3), log baytları (yazma 400 B, commit 200 B), pencere (8 saat), geri yüklemeye ayrılan RTO payı (0,5) ve yıllık geri yükleme testi iki tarafta aynıdır. Platforma özgü olan yalnızca bir log çarpanıdır (PostgreSQL full-page writes) ve yedek yolunun verimidir.

**Test:** `test_workload_weights` (x86), mainframe iş yükü testleri.

---

## 12. Ortak personel eğrisi (KB-13; P kararı)

**Karar (Emirhan, 2026-11-16).** Personel verisinin kendisine güven düşüktür ve kaynakların kurulum ortalamaları iki platform arasında oranlanamaz (mainframe MIPS başına, dağıtık sunucu başına verir). Bu yüzden personel **iki tarafta aynı eğriyle** hesaplanır ve crossover için nötrdür. x86'ya özgü bütün personel değişkenleri (IBM Eagle'ın sunucu ve imaj saatleri) kaldırıldı.

```
PCI_eşdeğer(TPS) = TPS × w(profil) × (1 − f_zIIP) / TPS_PER_PCI / 0,90      (platform modülü hesaplar)
FTE_ortak(TPS)   = max(taban, FTE_1000 × (PCI_eşdeğer / 1000)^b) × topoloji_çarpanı
FTE_mainframe    = FTE_ortak
FTE_x86          = FTE_ortak × STAFF_RATIO_X86                               (ana senaryo 1,0)
aylık personel   = FTE × yüklü_ücret(WAGE_LEVEL) / 12
```

| Senaryo (`STAFF_SCENARIO`) | FTE_1000 | b | Taban |
|---|---|---|---|
| low | 4,0 | 0,60 | 3 |
| mid | 5,5 | 0,70 | 4 |
| high | 7,0 | 0,80 | 5 |

Topoloji çarpanı (`STAFF_TOPOLOGY_FACTOR`) iki tarafta aynı tablodur: M1/X1 1,00 · M2/X2 1,05 · M3/X3 1,15 · M4/X4 1,25 [ASSUME]. Çapalar ve kalibrasyon mainframe v3 §7.7'dedir [IBM-CPO2014-Skills, CA2016-MFEcosystem, Rhoderick2007-TPFUG].

- **Girdi iş yüküdür, kurulu kapasite değil.** Latency ya da kullanım tavanı için alınan boş kapasite personel istemez. Böylece x86'nın düşük kullanım oranı (KB-04'teki IBM U_R etkisi) personel üzerinden sonuca girmez.
- **İş yükünün PCI eşdeğeri mainframe köprüsünden hesaplanır** (`mainframe_model.staff_pci_equivalent`), çünkü eğrinin kaynakları MIPS üzerinden tanımlıdır. Eşleştirilmiş karşılaştırmada bu türetme mainframe CPU ağırlıklarının mid değerlerini kullanır (`CROSS_BRIDGE_WEIGHTS` = "reference", v3 §7.11.5); aksi halde mainframe'e özgü bir parametre x86'nın personelini oynatırdı.
- **Başlık çıktıları:** başabaş personel oranı (x86'nın personeli mainframe'in kaç katı olursa iki toplam eşitlenir) ve personelsiz TCO. Duyarlılık: `STAFF_RATIO_X86` 1,25 ve 2,0 (IBM'in aynı iş yükü vakaları; üretici yanlılığı notuyla). 10K TPS'te başabaş oranı 2,16'dır (x86 dokümanı §16).
- **Yıllık modda** tepe TPS kullanılır; ekip CoD günleri için işe alınıp bırakılmaz.

**Test:** `test_staff_neutral_and_breakeven` (x86), mainframe personel testleri.

---

## 13. Taşımanın doğrulanması

Adım 6 bir yeniden düzenlemedir (refactoring). Ortak parametreleri taşımak sonuçları değiştirmemelidir. Bunu göstermek için:

1. Taşımadan **önce**, mevcut kodla bir "altın" sonuç kümesi üretildi (`src/tools/golden_snapshot.py --write` → `data/test/golden_step5.json`).
   - 7 statik durum: 1K, 10K, 10K %99,999, 10K 500 TB, 10K RPO 0 / RTO 60 dk, 50K %99,99, 150K. Her biri kademe, topoloji ve dokuz maliyet kalemiyle.
   - 10K ve 50K TPS'te aralık köşeleri.
   - Üç preset × üç stratejide yıllık toplamlar.
   - Statik NPV, NPV aralığı ve TFP yıllık NPV.
2. Taşımadan **sonra** `test_common_module_preserves_results` aynı kümeyi yeniden hesaplar ve 10⁻⁹ göreli farkla eşitlik ister. Bu sırada `NONPROD_FACTOR` 0'da tutulur ve aralıkta sabitlenir.
3. Sonuç: **0 fark**. Taşıma sonuçları birebir korudu. Görülen değişikliklerin hepsi üretim dışı ortamlar kaleminden gelir. Bu kalem ayrı bir model değişikliğidir ve etkisi ayrıca raporlandı (v3 §7.9).
4. **Adım 7'de** aynı test, F ve P'nin eski kurallarıyla (`RANGE_READ_WEIGHT` = 1, `STAFF_BASIS` = "installed", `NONPROD_FACTOR` = 0) altın kümeyi yine 0 farkla üretir. Bileşimin, I/O kurallarının, yedek hacminin ve personel eğrisinin ortak modüle taşınması sonuçları değiştirmedi; Adım 7'deki bütün mainframe farkları F ve P kararlarından gelir (v3 §7.11).

---

## 14. x86 modeli bu modülü nasıl kullanıyor

Adım 6'da bu bölüm bir sözleşmeydi; Adım 7'de x86 modeli (`src/x86_model.py`) yazıldı ve sözleşmeye uyar. Sözleşme `test_shared_parameters_single_owner` (x86) ile denetlenir: x86 modülünde büyük harfli hiçbir ortak ad yeniden tanımlı değildir.

| Konu | x86 modelinin yaptığı |
|---|---|
| Saha olayları | `cm.site_downtime_hours(T_rec)`; kendi T_rec tablosu (X1–X4) |
| Elle geçiş | X2'de `cm.manual_failover_minutes(teknik_süre, düzey)` |
| İşlem bileşimi ve I/O | `cm.WORKLOAD_MIXES`, `cm.RANGE_READ_WEIGHT`, `cm.mix_sync_read_io`, `cm.mix_sync_write_io`, `cm.mix_storage_iops` |
| Personel | `cm.staff_fte(mf.staff_pci_equivalent(TPS), topoloji)` × `STAFF_RATIO_X86`; ücret `cm.loaded_wage()`. Kendi FTE eğrisi yok |
| Enerji | `cm.energy_monthly(kW)` |
| Yedek | `cm.backup_volumes` (PostgreSQL log çarpanıyla), `cm.onprem_object_store`, `cm.transfer_hours`; kendi verim kısıtı |
| Storage | SAN liste fiyatını `cm.price_per_raw_tb` ile ham TB'a çevirir; indirimi `cm.net_price` ile bir kez uygular; NVMe piyasa fiyatına indirim uygulanmaz |
| Bileşen fiyatları | DRAM ve NVMe `cm.component_price` ile; kendi sabiti yok |
| NPV | `cm.esc`, `cm.finish_npv`; kendi amortisman ömrü (5 yıl) |
| Üretim dışı | `NONPROD_FACTOR_X86` (0 / 0,5 / 1,0; stres 2,0); `cm.nonprod_cost` ile aynı kalemler |
| Fiyat kaydı | `cm.register_prices("x86_model", ...)` (13 fiyat); kendi aralık parametreleri `cm.unpinned` ile süzülür |
| Parametre değiştirme | `cm.use_values(değerler, (x86_modülü, mainframe_modülü, cm))` |

**Karşılaştırma katmanında ortak parametreler.** `SITE_EVENT_LEVEL`, `WAGE_LEVEL`, `STAFF_SCENARIO`, `RANGE_READ_WEIGHT`, `BP_HIT_RATIO`, `BACKUP_RETENTION_WEEKS` ve dört artış oranı iki tarafı birlikte etkiler. Platform modüllerinde "low" o platformun lehine uç olarak tanımlıdır. Ortak bir parametre ise iki tarafı aynı yönde etkiler ve karşılaştırmada çoğunlukla birbirini götürür. Eşleştirilmiş karşılaştırma (`x86_model.compare_range`, x86 dokümanı §16) bu yüzden ortak parametreleri iki tarafa aynı değerle uygular, platforma özgü parametreleri ise ters uçlara çeker. Ortak ad listesi elle tutulmaz: ortak modüldeki büyük harfli adlardan türetilir.

---

## 15. Sınırlamalar ve açık kalanlar

- **Üretim dışı çarpanın tek kaynağı üreticidir** (IBM Eagle). Orta değerler bağımsız bir kaynakla daraltılmalıdır.
- **Elle geçiş karar süresi / teknik süre ayrıştırması kaynaksızdır.** Toplam kaynaklıdır, oran değildir.
- **Fiyat dönemi mainframe fiyatlarına uygulanmaz.** IBM fiyatlarının 2026 bileşen şokundan etkilenip etkilenmediği bilinmiyor (§7).
- **Ücretler ABD içindir.** Türkiye gibi farklı bir pazar için ortak ücret tablosunun ayrı bir seti gerekir. İki fiyat modu bunu kullanıcı dosyasıyla mümkün kılar (`LOADED_WAGE_USD`).
- **`RANGE_READ_WEIGHT` PostgreSQL'den türetildi.** Aynı göreli maliyetin Db2 for z/OS'ta geçerli olduğu doğrulanmadı; K6 ölçümü yalnızca PostgreSQL tarafını kalibre eder (§11).
- **Ortak personel eğrisi mainframe verisinden gelir.** x86 tarafına aynı eğriyi uygulamak bir karardır, bulgu değildir. Bu yüzden başabaş personel oranı başlık çıktısıdır (§12).
- **Kullanıcı fiyatları doğrulanmaz.** Model yalnızca biçimi ve işareti denetler. Bir teklifin hangi kalemleri kapsadığı (örneğin bakım dahil mi) kullanıcının sorumluluğundadır ve dokümanda hangi kalemi temsil ettiği yazılıdır.

---

## 16. Kaynaklar

> Tam künyeler, erişim tarihleri ve yerel kopyalar: [`kaynaklar/KAYNAKCA.md`](../kaynaklar/KAYNAKCA.md). Bu bölümdeki köşeli parantezli anahtarlar oradaki anahtarlardır (2026-11-24 kaynak düzeltmesi).

Bu modüle taşınan parametrelerin kaynakları değişmedi; tam kaynak listesi `mainframe_model_documentation_v3.md` Bölüm 11'dedir: [Uptime2025-PR], [DCF2022-Uptime], [BLS-OOH], [BLS2026-ECEC], [IDC2016-ConnectedMF], [MinIO-ObjectTCO], [Nubbo2026-S3], [AWS-DXPricing], [Damodaran2026-WACC], [Schneider2026-IBMPrice], [BLS2026-ECI], [EIA-EPM-5.3]. Yeni kaynak:

- **[IBM2013-TCOLessons] —** IBM CPO, "TCO Lessons Learned From Customer Engagements" v4 (2013): üretim dışı ortamlar mainframe'de üretim +%20, dağıtıkta çoğu zaman +%200. https://public.dhe.ibm.com/software/os/systemz/pdf/TCO_lessons_from_customer_engagements_v4.pdf [VENDOR]
- Fiyat dönemi tablosu (üçlüler): [PCSP2026-Server], [PCSP2026-SSD], [CapCompute-RAM], [Bacloud2026-RAM]; tam künyeler `x86_model_dokumantasyonu_v1.md` §20 ve `acik_sistem_arastirma_plani_v1.md` §5.2'dedir.
- İşlem bileşimi ve `RANGE_READ_WEIGHT`: [Kopytov-sysbench], [Tencent-PG-TestMethods], [Vonng-PGPerf], [Catterall2019], [Hendley2024-IDUG]; `kopruler_v1.md` KB-01, KB-09, KB-10.
