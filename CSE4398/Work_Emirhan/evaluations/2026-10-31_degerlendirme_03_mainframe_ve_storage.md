# Değerlendirme #3: Mainframe tarafının eksikleri ve storage katmanı

> **Değerlendirme #3** · Tarih: 2026-10-31 · Kapsam: mainframe modelinin güncel hali (`src/mainframe_model.py`, `docs/mainframe_model_documentation_v3.md`; 317 kademe, PCI köprüsü, Permanent / Base + CoD / TFP fiyatlama) ve storage katmanının projeye dahil edilip edilmeyeceği sorusu.
> Önceki değerlendirme: #2 (`2026-10-31_degerlendirme_02_mainframe.md`). Kapanan ve açık kalan maddeler Bölüm 5'te.
> Kendi bilgime dayanan ama kaynakla teyit etmediğim iddialar **(doğrulanmalı)** diye işaretli.

## 0. Özet

1. **Storage katmanı dahil edilmeli.** "İki tarafta da paralel, birbirini götürür" argümanı yalnızca iki taraf aynı storage'ı aynı miktarda ve aynı maliyetle kullansaydı geçerli olurdu. Gerçekte ikisi de geçerli değil: mainframe paylaşımlı disk (shared-disk) mimarisi kullanıyor, clustered tarafın önemli bir kısmı ise paylaşımsız (shared-nothing) ve verinin birden çok kopyasını tutuyor. Ayrıca DR, latency ve CPU tüketimi storage'a bağlı. Projenin kendi gerekçe dokümanı da literatürü tam olarak "storage'ı dışarıda bıraktığı için" eleştiriyor. Storage'ı çıkarmak projenin araştırma boşluğu iddiasıyla çelişir (Bölüm 1).
2. "Paralel olduğu için ayırt edici değil" argümanı **storage'ın altındaki ağ** için doğru ve proje bu kararı zaten vermiş (justification, Bölüm 4). Storage için değil.
3. Mainframe compute katmanı artık sağlam: kademeler, köprü ve donanım fiyatlama modeli resmî kaynaklara dayanıyor. Eksikler compute dışındaki TCO kalemlerinde ve transaction köprüsünde. En büyük eksik yazılım yığını: şu an tek bir "$40/MSU" kalemi var. CICS ve Db2 yok ve MLC'nin kademeli yapısı yok. Değerlendirme #1'deki düz maliyet/TPS eğrisi sorununun asıl kaynağı burası (Bölüm 3).

## 1. Storage katmanı bir bitirme projesinde dahil olmalı mı?

### 1.1. "Paralel" argümanının doğru olduğu durum

Bir maliyet kalemi iki tarafta da **aynı büyüklükte** ise karşılaştırmanın farkını değiştirmez. Crossover noktaları farkın işaretinin değiştiği yerlerdir, dolayısıyla aynı kalem crossover'ı da değiştirmez, yalnızca mutlak TCO'yu kaydırır. Bu, bir kalemi kapsam dışı bırakmanın meşru bir gerekçesidir. Projede storage altındaki ağ altyapısı bu gerekçeyle zaten dışarıda.

### 1.2. Storage'da bu koşul neden sağlanmıyor

| Boyut | Mainframe (z16 + Db2 data sharing + DS8900F) | Clustered x86 | Sonuç |
|---|---|---|---|
| Mimari | Shared-disk: tüm Db2 üyeleri aynı diske erişir, verinin site başına tek kopyası var | Stack'e bağlı: shared-disk (SAN dizisi) veya shared-nothing (yerel NVMe, veri DB tarafından 2–3 kopya halinde çoğaltılır) | Ham kapasite ihtiyacı farklı: replication factor 3 olan bir dağıtık DB aynı veri için yaklaşık 3 kat ham kapasite ister |
| DR replikasyonu | Storage katmanında (Metro/Global Mirror, GDPS yönetir) | Çoğunlukla DB/uygulama katmanında (streaming replication, Raft vb.) | Storage'ı çıkarırsak mainframe'in DR maliyetinin bir kısmı kaybolur, clustered'ın ise DB'ye gömülü kalır. Bu asimetrik bir hata olur |
| I/O'nun CPU maliyeti | I/O kanal alt sistemine ve SAP'lere devredilir, genel amaçlı CP'yi (MSU'yu) çok az tüketir (doğrulanmalı: oranı) | Storage yığını (ör. Ceph OSD, replikasyon, şifreleme) host CPU'su tüketir ve compute boyutlandırmasını büyütür | Mainframe'in klasik savunularından biri; araç bunu test edebilmeli |
| I/O gecikmesi | zHyperLink / FICON + DS8900F önbelleği (çok düşük, doğrulanmalı) | NVMe yerel çok düşük; ağ üzerinden SDS daha yüksek | Latency modelindeki D_io terimi şu an iki tarafta da varsayım (0,3 ms). Storage katmanı olmadan kalibre edilemez |
| Ölçeklenme | Dizi başına sabit maliyet + TB başına artış | Sunucu başına disk; kapasite compute ile birlikte büyür (hiperkonverjede) | Maliyet, veri hacmiyle farklı eğimle büyür. Bu, `data_volume_tb` ekseninde **ikinci bir crossover boyutu** üretebilir |

Bu tabloya göre storage, TPS dışında ayrı bir crossover ekseni (veri hacmi) açabilecek bir katman. Bu, Değerlendirme #1'de zayıf bulunan "çoklu crossover" hipotezini destekleyebilecek bir mekanizma. Yani storage hem tam yığın iddiası için gerekli hem de projenin ana sorusuna doğrudan katkı yapıyor.

### 1.3. Projenin kendi dokümanlarındaki kararlar

- `project_justification.md`: literatürün eksikliği "yalnızca compute'u kapsar; lisans, storage, DR ve personel maliyetini dışarıda bırakır" (satır 38). Araştırma sorusu farkın "compute, lisans, storage, DR, personel" kalemlerinden hangisinden geldiğini soruyor (satır 52). Girdi setinde `data_volume_tb` ve `data_growth_pct` var (satır 160–161).
- `project_context_restore_v4.md`: "Eşit derinlik" ilkesi (3.7) ve "Storage her iki tarafa birlikte eklenir" kararı (4.7). IOPS kullanıcıya sorulmuyor; RNI'dan türetiliyor ve iki tarafa da taşınması zorunlu.

Yani storage'ı çıkarmak yeni bir kapsam kararı olur ve tezin çerçevesini değiştirir. Akademik açıdan savunulabilir tek yol, onu dahil edip **sade** tutmaktır.

### 1.4. Bitirme projesi ölçeğinde nasıl sade tutulur

Storage'ı bir ürün kataloğu olarak değil, iki tarafın da aynı girdileri kullandığı bir **ortak arayüz** olarak modellemek:

- **Girdiler (iki taraf için ortak):** `data_volume_tb`, `data_growth_pct`, IOPS (TPS × RNI'ya bağlı IOPS/tx, zaten kodda var), RPO (replikasyon modunu belirler: senkron / asenkron).
- **Taraf başına parametreler:** kopya sayısı (shared-disk: site başına 1 + DR kopyası; shared-nothing: RF), kullanılabilir/ham kapasite oranı (RAID, sıkıştırma), $/TB, dizi veya sunucu başına sabit maliyet, bakım oranı, I/O servis süresi (D_io), host CPU yükü (yalnızca x86).
- **Çıktılar:** storage maliyeti, latency modeline giden D_io, compute boyutlandırmasına giden CPU yükü, DR maliyetinin storage kısmı.
- **Kapsam dışı (sınırlama olarak yazılır):** storage ağı, katmanlı depolama (tiering), arşiv. Backup, tek bir "yedek kapasite oranı" ile storage katmanına katlanabilir (mainframe'de sanal teyp TS7700, x86'da yedekleme yazılımı + nesne depolama; doğrulanmalı).

Phase 1'de her tarafta tek alternatif kuralı korunur: mainframe için DS8900F. Clustered taraf için açık bir karar var (Bölüm 4).

## 2. Mainframe compute katmanının durumu (kapananlar)

- Kapasite: 317 kademe resmî LSPR/MSU verisinden; 7xx PCI'si MSU'dan türetilmiş ve 7K0'da %0,004 içinde doğrulanmış.
- Köprü: PCI başına TPS (7,94), çift sayım yok.
- Latency: per-CP M/M/1 + D_io, %90 tavan.
- Donanım fiyatlama: Permanent / Base + On/Off CoD / TFP (corridor); SC28-7025 sınırları uygulanıyor.
- Testler: 9/9.

Compute katmanında kalan sorunlar küçük: RNI çarpanının iki kavramı karıştırması (Değerlendirme #2, 1.4), enerjinin drawer/frame sayısıyla ölçeklenmemesi, CoD kaydının 180 gün kuralı.

## 3. Mainframe tarafında eksik katmanlar ve kalemler

Önem sırasına göre. "Etki", karşılaştırmanın sonucunu (crossover yerini) ne kadar değiştirebileceğidir.

| # | Eksik | Şu anki hali | Etki | Neden önemli |
|---|---|---|---|---|
| 1 | **Transaction köprüsü** (REDP-5320 iş yükü profili) | Mainframe "1 TPS"i CICS benchmark işlemi; x86 tarafıyla ortak birim yok | Kritik | İki taraf aynı işi ölçmüyorsa hiçbir crossover anlamlı değil. D_io kalibrasyonu da buradan gelir |
| 2 | **Yazılım yığını:** z/OS + CICS TS + Db2 for z/OS, kademeli MLC (AWLC/TFP), OTC + S&S ürünleri | Tek kalem, $40/MSU, kademesiz | Kritik | Yazılım toplamın yaklaşık yarısı ve tek kalem olduğu için en büyük belirsizlik. MLC'nin MSU arttıkça birim fiyatı düşen kademeli yapısı, eksik olan **ölçek ekonomisinin** kaynağı (düz maliyet/TPS sorunu) |
| 3 | **Storage** (DS8900F) | Yok | Yüksek | Bölüm 1 |
| 4 | **Operasyon personeli** (sysprog, DBA, kapasite planlamacı, operatör) | Yok | Yüksek | Sabit maliyet: düşük TPS bölgesinde mainframe'in taban maliyetini, dolayısıyla alt crossover'ı belirler. Personel her iki tarafta da var ama profil ve maaşlar farklı |
| 5 | **Donanım maliyet yapısı:** sabit taban (frame, drawer, I/O kartları, bellek) + kapasite başına artış | $200/PCI doğrusal, bellek yok, drawer maliyeti yok | Yüksek | Doğrusal fiyat düz eğrinin ikinci kaynağı. Drawer maliyeti olmadan TFP/CoD modelinde drawer seçimi karar değişkeni olamıyor |
| 6 | **zIIP** | Yok | Orta | Db2 DRDA, Java ve bazı CICS işleri zIIP'e kayar ve MSU faturasından düşer. OLTP için yazılım maliyetini anlamlı düşürebilir (oran doğrulanmalı) |
| 7 | **DR ve availability maliyeti:** GDPS ayrı kalem, DR frame için CBU, RPO/RTO girdileri | GDPS yazılım primi (×1,15/×1,30); ikinci frame tam kapasite ve tam fiyat; RPO/RTO bağlı değil; M4 etiketleri ters görünüyor | Orta | İkinci frame'i tam fiyatla saymak M2–M4'ü olduğundan pahalı gösteriyor. CBU kayıtları DR kapasitesini çok daha ucuza sağlar |
| 8 | **Çok yıllık ufuk (5 yıl + NPV), büyüme** | Tek yıl | Orta | Donanım satın alma vs abonelik, TFP-SW büyüme fiyatı, veri büyümesi ancak çok yıllık ufukta görünür |
| 9 | Enerji ve tesis (drawer/frame sayısıyla) | Frame başına sabit 30 kW | Düşük | Büyük kademelerde eksik sayıyor; IMPP belgesiyle düzeltilir |

Not: 2, 4, 5 ve 7 sabit maliyet ile ölçeğe bağlı maliyet arasındaki dengeyi belirliyor. Crossover hipotezinin test edilebilmesi için bu dördünün en azından kaba bir halinin modelde olması gerekiyor.

## 4. Açık karar: clustered tarafta storage tipi

Değerlendirme #1'deki bekleyen kararlardan biri. Clustered taraf iş yüküne göre seçilen stack'lerden oluşuyor ve storage tipi aslında DB mimarisinden geliyor:

- **Öneri: storage'ı DB mimarisine bağlamak.** Shared-disk DB'ler (ör. Oracle RAC) için SAN dizisi, shared-nothing / dağıtık DB'ler (ör. PostgreSQL + Patroni, dağıtık SQL) için yerel NVMe × replication factor. Böylece "tek alternatif" kuralı stack başına korunur, ayrı bir storage seçim ekseni açılmaz ve kopya sayısı farkı modelde doğal olarak ortaya çıkar.
- Alternatif 1: tüm clustered stack'ler için tek bir kurumsal SAN dizisi. En basit ve storage farkını sıfıra yaklaştırır, ama shared-nothing DB'ler için gerçekçi değil.
- Alternatif 2: tek bir yazılım tanımlı storage (ör. Ceph). Bulut-yerel tarafı temsil eder, ama shared-nothing DB'nin kendi replikasyonuyla çift kopyalama sorunu çıkarır.

## 5. Bu değerlendirmede kapanan / açık kalan tehditler

**Değerlendirme #2'den kapanan:** 1.1 (çift sayım), 1.2 (kademe tablosu), 1.3 (sabit MSU/MIPS), On/Off CoD üst sınırı (SC28-7025 ile çözüldü), güncel donanım fiyatlama modeli (TFP corridor eklendi).

**Kısmen:** 3 (maliyet yapısı): fiyatlama stratejileri eklendi, ama kademeli MLC, donanım tabanı ve zIIP yok, düz eğri sorunu devam ediyor. 1.4 (RNI kavramı).

**Açık:** 1.5 / Değerlendirme #1 tehdit 1 (transaction köprüsü), 4 (availability: CBU, RPO/RTO, M4 etiketleri), 6 (storage, personel, CICS/Db2).

**Yeni:** Storage'ın iki taraf için ortak arayüzle tanımlanması (Bölüm 1.4) ve clustered storage tipi kararı (Bölüm 4).

## 6. Önerilen sıra

1. **Yazılım yığını + kademeli MLC + zIIP.** En büyük kalem ve düz eğri sorununun ana kaynağı. Fiyat verisi yarı kapalı, bu yüzden kaynaklı aralıklar ve duyarlılık analizi gerekiyor.
2. **Storage arayüzü (iki taraf için) + DS8900F.** Arayüz bir kez tasarlanır; mainframe tarafı hemen doldurulur, x86 tarafı clustered model gelince aynı arayüze bağlanır. D_io'nun kalibrasyonu da buraya girer.
3. **Personel.** Basit bir FTE × maaş modeli; FTE'nin kapasiteyle nasıl ölçeklendiği kaynaklı olmalı.
4. **Donanım tabanı + drawer + CBU + GDPS kalemi.**
5. **5 yıllık NPV.**

Transaction köprüsü (REDP-5320 iş yükü tanımı) bu sıradan bağımsız olarak paralel yürütülebilir; clustered tarafa geçmeden önce kapanması gerekiyor.
