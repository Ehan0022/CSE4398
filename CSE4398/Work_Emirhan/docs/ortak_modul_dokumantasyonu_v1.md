# Ortak Modül — İki Platformun Paylaştığı Parametreler ve Kurallar (v1)

*Tarih: 2026-11-02 · Kod: `src/common_model.py` · İlgili: `mainframe_model_documentation_v3.md` (mainframe'deki kullanım), `acik_sistem_arastirma_plani_v1.md` §12.2 (bu modülün planı), `benzer_calismalar_v1.md` §8 (üretim dışı ortamlar)*

Bu doküman Adım 6'da kurulan ortak modülün **güncel halini** anlatır. Ortak modül, mainframe ile kümelenmiş x86'nın aynı disiplinle karşılaştırılabilmesi için iki tarafta **aynı olması gereken** her parametreyi ve kuralı tek bir yerde toplar. Değişikliklerin tarihçesi `PROJECT_LOG.md`'dedir.

Etiketler önceki dokümanlarla aynıdır: **[ASSUME]** kalibre edilmemiş varsayım · **[DERIVED]** kaynaktan hesaplanan değer · **[VENDOR]** üretici kaynağı.

---

## 0. Neden bir ortak modül

Bir karşılaştırma ancak iki tarafın aynı varsayımlarla hesaplandığı kadar güvenilirdir. Örnekler:

- Mainframe ile x86 aynı veri merkezinde durur. Elektrik kesintisinin ya da insan hatasının sıklığı platforma göre değişmez.
- Bir Db2 DBA'sı ile bir PostgreSQL DBA'sı aynı iş piyasasından işe alınır. Ücret tablosu iki tarafta farklıysa sonuç ücret farkını ölçer, platform farkını değil.
- 5 yıllık NPV'de iki taraf farklı iskonto oranıyla indirgenirse sermaye maliyetinin kendisi bir taraf lehine çalışır.

Bu parametreler platform modüllerinde ayrı ayrı tanımlansaydı, bir aralık senaryosu ya da kullanıcı fiyat dosyası yalnızca bir tarafı değiştirebilirdi. Ortak modül bunu **yapısal olarak** önler: parametre tek yerde tanımlıdır ve iki taraf da onu oradan okur.

**Platforma özgü kalanlar.** Kurtarma süreleri (GDPS ile Data Guard / Patroni), FTE eğrisi (MIPS başına ile sunucu başına), donanım ve lisans fiyatları, storage ürünleri ve yedek yolu (DS8900F TCT ile pgBackRest / RMAN). Bunlar platform modüllerinde kalır.

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
| λ_saha (olay/yıl) | 0,05 | 0,15 | 0,25 | [UPTIME-2025] |
| d_kısa (saat) | 1 | 2 | 4 | [ASSUME] |
| p_uzun | 0,08 | 0,15 | 0,30 | [UPTIME-2022] |
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
| `LOADED_WAGE_USD` (yüklü maliyet, USD/FTE/yıl) | 122.000 | 162.000 | 215.000 | BLS OEWS Mayıs 2025 medyanlarından karma brüt $95K / $120K / $150K × yan hak çarpanı 1,28 / 1,35 / 1,43 [BLS-OEWS, BLS-ECEC, IDC-2016] |
| `STAFF_FLOOR_FTE` (7/24 asgari ekip) | 3 | 4 | 5 | [ASSUME]; mainframe v3 §7.7 |
| Düzey anahtarı | `WAGE_LEVEL` (aralık parametresi) | | | |

- **Ücret ile ekip büyüklüğü ayrıldı.** Adım 6'dan önce mainframe'in `STAFF_SCENARIO`'su hem FTE eğrisini hem ücreti birlikte seçiyordu. Şimdi `STAFF_SCENARIO` (platforma özgü) eğriyi ve tabanı, `WAGE_LEVEL` (ortak) ücreti seçer. Köşe senaryolarında ikisi aynı yöne çekildiği için low / mid / high toplamları değişmedi. Tornado'da ise personel iki satıra ayrıldı: "ekip ne kadar büyük" ve "bir kişi ne kadar".
- **Taban ekip iki tarafta aynıdır.** x86'da IBM Eagle'ın dağıtık saatleri küçük kurulumlarda 1 FTE'nin altında bir ekip verir. Taban olmasaydı x86 düşük TPS'te yapay olarak ucuz görünürdü (x86 planı §10).

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
| `COS_HW_USD_PER_TB` | 100 (aralık 60–200) | [MINIO-TCO] |
| `COS_MIN_SITE_CAPEX_USD` | 70.000 | [MINIO-TCO] |
| `COS_SW_USD_PER_TB_MONTH` | 5 (aralık 0–10) | [MINIO-TCO → ASSUME] |
| `COS_KW_PER_PB` | 1,5 | [ASSUME] |
| `S3_USD_PER_GB_MONTH` (Standard-IA) | 0,0125 | [AWS-S3-2026] |
| `S3_MIN_STORAGE_DAYS` | 30 | [AWS-S3-2026] |
| `S3_RETRIEVAL_USD_PER_GB` | 0,01 | [AWS-S3-2026] |
| `S3_PUT_USD_PER_1000` | 0,01 | [AWS-S3-2026] |
| `DX_PORT_USD_PER_HOUR` (10 Gbps) | 2,25 | [AWS-DX-2026] |
| `DX_EGRESS_USD_PER_GB` | 0,02 | [AWS-DX-2026] |
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

| Dönem | DRAM USD/GB | Kurumsal NVMe USD/TB |
|---|---|---|
| `2025-mid` (şok öncesi) | 4 | 115 |
| `2026-Q3` (şok, varsayılan) | 35 | 753 |

**Kurallar:**

- Emtia bileşen fiyatları (DRAM, NAND) dönem tablosundan okunur (`component_price`). Platform modülü kendi sabitini tutmaz.
- **Sınırlama:** IBM'in z16 ve DS8900F fiyatlarının şoktan etkilenip etkilenmediğine dair kaynak yok. Mainframe fiyatları dönemden bağımsız tutulur. Dönem 2026-Q3 seçildiğinde x86 şoklu, mainframe şoksuz fiyatlanır. Bu fark sonuçlarda mainframe lehine bir yanlılık olabilir. Tezde açıkça yazılmalı, x86 sonuçları iki dönemle birlikte raporlanmalıdır.
- **Fiyat yaşları görünür olmalı.** Her kayıtlı fiyat parametresinin kaynak yılı tutulur; `--price-vintages` en eskiden yeniye listeler. Mainframe tarafında en eski fiyatlar 2004 (AWLC) ve 2006 (TS7700 küme tabanı) tarihlidir.
- **2004 nominal AWLC fiyatları 2026 USD'ye otomatik çevrilmez.** Güncel liste fiyatı bilinmediği için dönüşüm `SW_PRICE_LEVEL_FACTOR` aralığının işidir. Aralığın üst ucu 1,75, ABD TÜFE'sinin 2004–2026 artışıyla aynı büyüklüktedir. Otomatik TÜFE çarpanı uygulamak "IBM fiyatları enflasyonla arttı" varsayımını gizlice kodlardı.

**Test:** `test_price_epoch`.

---

## 8. NPV kuralları

İki taraf aynı ufuk, iskonto oranı, büyüme ve fiyat artış sınıflarıyla indirgenir (mainframe v3 §9.10).

| Parametre | Değer | Aralık | Dayanak |
|---|---|---|---|
| `NPV_YEARS` | 5 | | [ASSUME] amortisman süresiyle aynı |
| `NPV_DISCOUNT_RATE` (nominal) | 0,07 | tarama %5 / %7 / %10, köşelere girmez | [DAMODARAN-2026] |
| `NPV_TPS_GROWTH` | 0,10 | senaryo girdisi | |
| `SW_PRICE_ESCALATION` | 0,03 | 0–0,06 | [IBM-PRICE-2026 → ASSUME] |
| `HW_SERVICE_ESCALATION` | 0,03 | 0–0,06 | [IBM-PRICE-2026 → ASSUME] |
| `WAGE_ESCALATION` | 0,033 | 0,025–0,045 | [BLS-ECI-2026] |
| `ENERGY_ESCALATION` | 0,04 | 0,015–0,056 | [EIA-EPM] |
| `NPV_RESIDUAL_FRACTION` | 0 | 0–1 (tarama) | [ASSUME] tutucu |

- **Zamanlama:** satın almalar dönem başında (t = y − 1), işletme giderleri yıl sonunda (t = y).
- **Fonksiyonlar:** `esc(oran, yıl)`, `discount_and_sum`, `residual_value(..., ömür)`, `finish_npv(...)`. Sonuç NPV, yıllık eşdeğer maliyet ve seviyelendirilmiş $/TPS/ay'dır. Kalan değerin ömrü platformun amortisman süresidir: mainframe 5 yıl, x86'da 3–5 yıl.
- **Teknoloji yenilemesi** (z17 ya da yeni sunucu nesli) iki tarafta birlikte dışarıdadır. x86'da 5 yıl içinde bir sunucu yenilemesi modellenecekse mainframe'de de nesil geçişi modellenmelidir.
- `NPV_COMMON_RANGE_PARAMETERS` dört artış oranını aralık analizine taşır. Platform kendi NPV parametrelerini (mainframe: `TFP_GROWTH_PRICE_FACTOR`) ekler.

---

## 9. Üretim dışı ortamlar (NONPROD)

Geliştirme, test, QA ve ön-üretim ortamları. Benzer çalışmalar taramasına göre bu kalem iki platformda çok farklı büyüklükte olabilir: IBM Eagle'a göre mainframe'de üretim +%20, dağıtıkta çoğu zaman +%200 [IBM-EAGLE-2013; benzer_calismalar_v1 §3.2]. Emirhan'ın kararı (2026-11-02): iki tarafa ayrı, aralıklı bir çarpan; düşük uç 0, "kapsam dışı" senaryosu.

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
| Birincil storage | Personel | Kurulu üretim kapasitesine göre boyutlanır; üretim dışını aynı ekip işletir [ASSUME] |

**Kapasite eşdeğeri maliyet.** Çarpan, üretim dışı kapasitenin üretimle aynı birim fiyattan alındığını varsayar. Mainframe'de bu, AWLC'nin kademeli marjinal fiyatını ve IBM'in geliştirme/test fiyatlandırma tekliflerini yok sayar; mainframe aleyhine tutucudur. x86'da açık kaynak yazılımın üretim dışı lisansı genellikle sıfırdır, ama Oracle ve VMware lisansları çekirdek başınadır. Bu fark x86 modelinde kalem kalem ele alınmalıdır.

| Platform | low | mid | high |
|---|---|---|---|
| Mainframe | 0 | 0,20 [IBM-EAGLE-2013] | 0,50 [ASSUME] |
| x86 | 0 | bağımsız kaynak aranıyor | 2,0 [IBM-EAGLE-2013] |

**Karşılaştırmada kullanım.** İki platformun çarpanı ayrı aralık parametreleridir. Karşılaştırma katmanında "kapsam dışı" senaryosu iki çarpanın birlikte 0 olduğu durumdur. Tez, sonuçları bu senaryo ile mid senaryo yan yana raporlamalıdır.

**Test:** `test_nonprod_factor`. Mainframe'deki etkisi v3 §7.9'dadır: 10K TPS'te +$84.825/ay, başlık $84,62 → $93,10/TPS/ay.

---

## 10. İki fiyat modu

Emirhan'ın önerisi (2026-11-02). İki mod:

1. **Kaynaklı fiyat seti (varsayılan).** Her fiyat parametresi kaynaklı bir değer ya da aralıkla gelir.
2. **Kullanıcı fiyatları.** Bir JSON dosyası kayıtlı adların bir kısmını ya da tamamını geçersiz kılar.

**Fiyat kaydı (`PRICE_REGISTRY`).** Her fiyat parametresi bir kayıtla tanımlıdır: sahip modül, birim, kaynak, kaynak yılı, bağlı aralık parametresi ve açıklama. Platform modülü kendi fiyatlarını `register_prices` ile kaydeder. Bir ad iki platformda kayıtlıysa hata verilir. Mainframe 18, ortak modül 12 fiyat kaydeder.

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

**CLI (mainframe):**

| Seçenek | İşlev |
|---|---|
| `--prices DOSYA` | Kullanıcı fiyatlarını uygular; geçersiz kılınan ve sabitlenen adları yazar |
| `--list-prices` | Kaynaklı fiyat setini JSON şablonu olarak yazar |
| `--price-vintages` | Fiyatların kaynak yıllarını en eskiden yeniye listeler |

Çıktıda fiyat modu yazılır: "kaynaklı fiyat seti" ya da "kullanıcı fiyatları (N parametre geçersiz kılındı)".

**Test:** `test_two_price_modes` ve CLI testi.

---

## 11. Taşımanın doğrulanması

Adım 6 bir yeniden düzenlemedir (refactoring). Ortak parametreleri taşımak sonuçları değiştirmemelidir. Bunu göstermek için:

1. Taşımadan **önce**, mevcut kodla bir "altın" sonuç kümesi üretildi (`src/tools/golden_snapshot.py --write` → `data/test/golden_step5.json`).
   - 7 statik durum: 1K, 10K, 10K %99,999, 10K 500 TB, 10K RPO 0 / RTO 60 dk, 50K %99,99, 150K. Her biri kademe, topoloji ve dokuz maliyet kalemiyle.
   - 10K ve 50K TPS'te aralık köşeleri.
   - Üç preset × üç stratejide yıllık toplamlar.
   - Statik NPV, NPV aralığı ve TFP yıllık NPV.
2. Taşımadan **sonra** `test_common_module_preserves_results` aynı kümeyi yeniden hesaplar ve 10⁻⁹ göreli farkla eşitlik ister. Bu sırada `NONPROD_FACTOR` 0'da tutulur ve aralıkta sabitlenir.
3. Sonuç: **0 fark**. Taşıma sonuçları birebir korudu. Görülen değişikliklerin hepsi üretim dışı ortamlar kaleminden gelir. Bu kalem ayrı bir model değişikliğidir ve etkisi ayrıca raporlandı (v3 §7.9).

---

## 12. x86 modelinin bu modülü nasıl kullanacağı

x86 modeli (`src/x86_model.py`, sonraki adım) şu sözleşmeye uymalıdır:

| Konu | x86 modelinin yapacağı |
|---|---|
| Saha olayları | `cm.site_downtime_hours(T_rec)`; kendi T_rec tablosu (X1–X4) |
| Elle geçiş | X2'de `cm.manual_failover_minutes(teknik_süre, düzey)` |
| Personel | Kendi FTE eğrisi (IBM Eagle dağıtık saatleri); taban `cm.STAFF_FLOOR_FTE`, ücret `cm.loaded_wage()` |
| Enerji | `cm.energy_monthly(kW)` |
| Yedek | `cm.onprem_object_store`, `cm.s3_hybrid`; kendi verim kısıtı |
| Storage | AFA ve NVMe fiyatlarını `cm.price_per_raw_tb` ile ham TB'a çevir; indirimi `cm.net_price` ile bir kez uygula |
| Bileşen fiyatları | DRAM ve NVMe `cm.component_price` ile; kendi sabiti yok |
| NPV | `cm.esc`, `cm.finish_npv`; kendi amortisman ömrü |
| Üretim dışı | Kendi `NONPROD_FACTOR`'ü (0 / ? / 2,0); `cm.nonprod_cost` ile aynı kalemler |
| Fiyat kaydı | `cm.register_prices("x86_model", ...)`; kendi aralık parametreleri `cm.unpinned` ile süzülür |
| Parametre değiştirme | `cm.use_values(değerler, (x86_modülü, cm))` |

**Karşılaştırma katmanında ortak parametreler.** `SITE_EVENT_LEVEL`, `WAGE_LEVEL` ve dört artış oranı iki tarafı birlikte etkiler. Platform modüllerinde "low" o platformun lehine uç olarak tanımlıdır. Ortak bir parametre ise iki tarafı aynı yönde etkiler ve karşılaştırmada çoğunlukla birbirini götürür. Karşılaştırma katmanı bu yüzden ortak parametreleri iki tarafa aynı değerle uygulamalı, platforma özgü parametreleri ise ayrı ayrı taramalıdır.

---

## 13. Sınırlamalar ve açık kalanlar

- **Üretim dışı çarpanın tek kaynağı üreticidir** (IBM Eagle). Orta değerler bağımsız bir kaynakla daraltılmalıdır.
- **Elle geçiş karar süresi / teknik süre ayrıştırması kaynaksızdır.** Toplam kaynaklıdır, oran değildir.
- **Fiyat dönemi mainframe fiyatlarına uygulanmaz.** IBM fiyatlarının 2026 bileşen şokundan etkilenip etkilenmediği bilinmiyor (§7).
- **Ücretler ABD içindir.** Türkiye gibi farklı bir pazar için ortak ücret tablosunun ayrı bir seti gerekir. İki fiyat modu bunu kullanıcı dosyasıyla mümkün kılar (`LOADED_WAGE_USD`).
- **Kullanıcı fiyatları doğrulanmaz.** Model yalnızca biçimi ve işareti denetler. Bir teklifin hangi kalemleri kapsadığı (örneğin bakım dahil mi) kullanıcının sorumluluğundadır ve dokümanda hangi kalemi temsil ettiği yazılıdır.

---

## 14. Kaynaklar

Bu modüle taşınan parametrelerin kaynakları değişmedi; tam kaynak listesi `mainframe_model_documentation_v3.md` Bölüm 11'dedir: [UPTIME-2025], [UPTIME-2022], [BLS-OEWS], [BLS-ECEC], [IDC-2016], [MINIO-TCO], [AWS-S3-2026], [AWS-DX-2026], [DAMODARAN-2026], [IBM-PRICE-2026], [BLS-ECI-2026], [EIA-EPM]. Yeni kaynak:

- **[IBM-EAGLE-2013] —** IBM CPO, "TCO Lessons Learned From Customer Engagements" v4 (2013): üretim dışı ortamlar mainframe'de üretim +%20, dağıtıkta çoğu zaman +%200. https://public.dhe.ibm.com/software/os/systemz/pdf/TCO_lessons_from_customer_engagements_v4.pdf [VENDOR]
- Fiyat dönemi tablosu: `acik_sistem_arastirma_plani_v1.md` §5.2 ve oradaki kaynaklar.
