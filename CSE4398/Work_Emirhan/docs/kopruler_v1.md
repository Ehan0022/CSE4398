# Köprüler: Mainframe ile Kümelenmiş x86'yı Aynı Ölçüyle Karşılaştırmak İçin Gerekenler (v1)

*Tarih: 2026-11-16 · Durum: bütün köprüler karara bağlandı; x86 modeli bu dokümana göre kurulacak · Kaynak belgeler: `mainframe_model_documentation_v3.md` (v3), `ortak_modul_dokumantasyonu_v1.md`, `acik_sistem_arastirma_plani_v1.md` (plan v1), `benzer_calismalar_v1.md`, `evaluations/2026-11-16_degerlendirme_08_acik_sistem_incelemesi.md` (Değ. #8)*

Bu doküman iki platform arasındaki **bütün köprüleri** tek yerde toplar. Bir köprü, iki tarafın aynı girdiyle beslendiği, aynı ölçüyle ölçüldüğü ya da aynı kuralla fiyatlandığı bir arayüzdür. Önceki dokümanlarda dağınık duran köprüler (TPS birimi, PCI köprüsü, availability denklemi, storage arayüzü, fiyat dönemi, NPV, üretim dışı) ve 2026-11-16'da karara bağlanan yedi köprü (P, F, K, U, E, C, N) burada aynı düzende yazılıdır. Orijinal tasarım dokümanları ve önceki sürümler değiştirilmedi.

---

## 0. Okuma Kılavuzu ve Kurallar

### 0.1. Her köprünün düzeni

1. **Amaç:** köprü neden gerekli, olmasaydı sonuç neden geçersiz olurdu.
2. **Mainframe tarafı / x86 tarafı:** iki taraftaki karşılık.
3. **Kaynaklardan:** kaynakların söyledikleri. Kurallar aşağıda (0.2).
4. **Kural ve formül:** modelin uygulayacağı biçim.
5. **Parametreler:** değer, aralık (low / mid / high), dayanak.
6. **Karar:** kim, ne zaman, hangi seçenek.
7. **Açık kalan ve tehditler.**

### 0.2. Kaynak aktarım kuralları

- **Tırnak içindeki İngilizce metinler kaynağın kendi cümleleridir**, değiştirilmeden aktarıldı.
- **Sayılar kaynaktaki haliyle verilir.** Bizim hesapladığımız her değer **[DERIVED]** diye işaretlidir ve hesabı yanında yazar.
- Türkçe yazılmış kaynak bilgisi **aktarımdır** (özet ya da çeviri); tırnak içinde değildir.
- Etiketler: **[VENDOR]** üretici ya da üretici sponsorlu · **[ASSUME]** kaynakla daraltılamayan varsayım · **[DERIVED]** kaynaktan hesaplanan · **(doğrulanmalı)** ikincil kaynaktan, birincil kaynakla teyit edilmemiş.
- **low = ilgili platform lehine uç.** x86'ya özgü parametrelerde low = x86 lehine; mainframe'e özgü parametrelerde low = mainframe lehine. Ortak parametrelerde low, iki tarafı birlikte ucuzlatan uçtur.

### 0.3. Karar kaydı

| Tarih | Karar veren | İçerik |
|---|---|---|
| 2026-10-31 | Emirhan | TPS ortak birim; MQ iki tarafta kapsam dışı; rack-mount z16 (A02) kapsam dışı |
| 2026-11-01 | Emirhan | Olay tabanlı availability; aralık çıktısı (nokta fiyat değil) |
| 2026-11-02 | Emirhan | x86 planı K1–K7 (plan v1 §13); iki tarafta ayrı `NONPROD_FACTOR`; iki fiyat modu |
| 2026-11-16 | Emirhan | Değ. #8 köprüleri: F, K, U, E, C, N için önerilen (b) seçenekleri; P için ortak personel eğrisi, ana senaryoda oran 1,0 |

---

## 1. Köprü Haritası

| Kod | Köprü | Mainframe | x86 | Durum |
|---|---|---|---|---|
| KB-01 | İşlem birimi ve bileşim | oltp_rw, w | sysbench oltp_read_write | Karar: F (b), 2026-11-16 |
| KB-02 | Mainframe kapasite köprüsü | REDP-5320 + LSPR: 7,939 TPS/PCI | — | Kuruldu (v3 §4) |
| KB-03 | x86 kapasite köprüsü | — | SPECrate2017_int_base / çekirdek | Karar: K (b), 2026-11-16 |
| KB-04 | Platformlar arası tutarlılık kontrolü | z16 CP | R760 çekirdeği | Kontrol, parametre değil |
| KB-05 | Kullanım oranı ve latency | min(ρ_latency, 0,90), M/M/1, D_io | Aynı kural; x86 tavanı aralıklı | Karar: U (b), 2026-11-16 |
| KB-06 | Ölçekleme mimarisi ve tavanlar | Tek CEC (~187K TPS) | Patroni tek yazıcı; RAC | K3 (2026-11-02) + Değ. #8 §2.6 |
| KB-07 | Availability denklemi | Saha olayı × T_rec + planlı + D_cpc | Aynı; D_cpc yerine düğüm terimi | Kuruldu; ortak modül |
| KB-08 | Topoloji eşlemesi | M1–M4 (SG24-8446) | X1–X4 (Oracle MAA, Patroni) | K4 (2026-11-02) |
| KB-09 | Storage arayüzü ve fiyat sözleşmesi | DS8900F, ham TB | DB'ye bağlı: SAN / yerel NVMe | K1 (2026-11-02) |
| KB-10 | Yedekleme | TS7770 / nesne / S3 | Nesne / S3 | Kuruldu; ortak fiyat fonksiyonu |
| KB-11 | Lisans tabanı | R4HA, CBU | Kurulu çekirdek/düğüm | Asimetri modellenir, eşitlenmez |
| KB-12 | Kapsam sınırı: işlem yöneticisi | CICS dahil | Uygulama katmanı eklenir | Karar: C (b), 2026-11-16 |
| KB-13 | Personel | Ortak eğri | Ortak eğri × oran | Karar: P, 2026-11-16 |
| KB-14 | Üretim dışı ortamlar | 0 / 0,20 / 0,50 | 0 / 0,50 / 1,00 | Karar: N (b), 2026-11-16 |
| KB-15 | Fiyat dönemi ve fiyat modları | Şok öncesi çapalar | Dönem tablosu | Karar: E (b), 2026-11-16 |
| KB-16 | Zaman ve finansman (NPV) | 5 yıl, r, g, artışlar | Aynı | Kuruldu; ortak modül |
| KB-17 | Enerji ve tesis | Ortak elektrik fiyatı | Aynı | Kuruldu |
| KB-18 | Belirsizlik ve çıktı biçimi | Aralık + tornado | Aynı + başabaş çıktıları | Kuruldu + P ekleri |

---

## KB-01. İşlem Birimi ve Bileşim

### Amaç

Crossover "TPS başına maliyet" üzerinden kurulduğu için TPS iki tarafta **aynı işi** ifade etmelidir. Değerlendirme #1'in en kritik tehdidi buydu: TPS iki tarafta ortak bir birim değildi.

### Mainframe tarafı

Bir işlem bileşimle tanımlanır (v3 §4.4.2):

```
CPU(µs) = CPU_US_TM_BASE + nokta_okuma × CPU_US_PER_SQL_READ
        + aralık_okuma × CPU_US_PER_SQL_READ × RANGE_READ_WEIGHT      (F kararıyla yeni)
        + yazma × CPU_US_PER_SQL_WRITE                                  (z13 CP-µs)
w       = CPU / CPU_US_TM_BASE
```

### x86 tarafı

sysbench `oltp_read_write`'ın kendisi ölçülür. Bileşim tanım gereği aynıdır; aralık/nokta oranı ölçülmüş çapanın içindedir.

### Kaynaklardan

**sysbench oltp_read_write bileşimi** [Kopytov-sysbench, Tencent-PG-TestMethods] (aktarım): işlem başına 10 nokta SELECT, 4 aralık SELECT (simple range, SUM, ORDER BY, DISTINCT; `range_size` varsayılanı 100 satır), 2 UPDATE, 1 DELETE, 1 INSERT, BEGIN ve COMMIT. Toplam 20 ifade.

**REDP-5320 işlem profili** [Burgess2016-REDP5320], raporun sayaçlarından (v3 §4.4.1):

| Ölçü (18 CP, 174.624 TPS) | Değer | İşlem başına |
|---|---|---|
| Shared data table okuması | 831.835 /s | 4,76 |
| Read for update + rewrite | 8.257 /s | 0,047 |
| Coupling facility log yazımı | 10.878 /s | 0,062 |
| CICS CPU | 1.499,4 % (bir CP) | 85,9 µs (z13) |

**SQL CPU maliyetleri:**
- [Catterall2012] (aktarım): CICS programında tek INSERT ~68 µs CPU (stored procedure içinde 139 µs).
- [Catterall2019] (aktarım): bir sahada CICS-Db2 işlemi class 2 CPU (GP + zIIP) 1,322 → 1,245 ms.

**Vonng alt testleri** [Vonng-PGPerf], AWS c5d.metal. Şekil altyazısı: "Sysbench 10-item test results (QPS, higher is better)".

| Test | QPS (kaynaktaki değer) |
|---|---|
| oltp_point_select | 1.372.654 |
| oltp_read_only | 852.440 |
| oltp_write_only | 495.942 |
| oltp_read_write | 519.069 |

**Türetme [DERIVED]**, makine-µs / işlem (QPS ÷ işlem başına sorgu):

| Test | Sorgu / işlem | TPS | µs / işlem |
|---|---|---|---|
| point_select | 1 | 1.372.654 | 0,73 |
| read_only | 16 (10 nokta + 4 aralık + BEGIN/COMMIT) | 53.278 | 18,77 |
| write_only | 6 (4 yazma + BEGIN/COMMIT) | 82.657 | 12,10 |
| read_write | 20 | 25.953 | 38,53 |

- Aralık / nokta = (18,77 − 10 × 0,73 − 2 × b) / 4 / 0,73. BEGIN/COMMIT maliyeti b = 0,73 alınırsa **3,44**, b = 0 alınırsa **3,94**.
- Yazma / nokta = 3,65–4,15. Mainframe'deki 70 / 30 = 2,33 oranı bunun altında; ayrı bir parametre olarak korunur.
- Karma yük: read_write (38,5 µs), read_only ile write_only toplamından (30,9 µs) %25 pahalı. Çekişme ek maliyeti çapanın içindedir.

### Kural

- `oltp_rw` profili **10 nokta okuma + 4 aralık okuma + 4 yazma + 1 commit** olur.
- `RANGE_READ_WEIGHT` iki tarafta ortak bir parametredir. Mainframe w'sini belirler. x86'da K6 ölçümüyle kalibre edilir: `oltp_read_only` ve `oltp_point_select` aynı makinede koşulur.
- PostgreSQL'deki göreli maliyetin Db2 for z/OS'a taşınması bir varsayımdır. Db2'ye özgü yayımlanmış bir aralık sorgusu maliyeti bulunamadı.

### Parametreler

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| RANGE_READ_WEIGHT | 3,4 | 3,65 | 3,9 | Vonng alt testleri [DERIVED]; K6 ile kalibre |
| CPU_US_PER_SQL_READ (nokta) | 15 | 30 | 60 | [ASSUME] (v3 §4.4.2) |
| CPU_US_PER_SQL_WRITE | 40 | 70 | 140 | [Catterall2012] |

### Etkisi [DERIVED, model koşusu]

- w, 9,15'ten (85,9 + 14 × 30 + 4 × 70 = 786 µs) **~12,5**'e çıkar (85,9 + 10 × 30 + 4 × 109,5 + 280 ≈ 1.104 µs; 3,65 ağırlıkla 12,85; 3,4 ile 12,5).
- 10K TPS, M1, %99,9'da modelde okuma eşdeğeri 24,6 ile:
  - kademe 3931-516'dan 3931-524'e (16.380 PCI) çıkar;
  - aylık toplam $1.143.635 olur, yani **$114,4/TPS/ay** (önce $93,10; +%23);
  - personel 30,8'den 38,9 FTE'ye çıkar (KB-13'te personelin TPS'e bağlanmasıyla bu kısım yeniden hesaplanacak).

### Karar

**F (b), Emirhan, 2026-11-16.**

### Açık kalan

K6'da oranın ölçülmesi. Db2'de aralık sorgusu maliyeti için bir IBM kaynağı (IRWW ya da Db2 performans raporları) aranmaya devam.

---

## KB-02. Mainframe Kapasite Köprüsü (PCI Başına TPS)

### Amaç

Benchmark'tan nesilden bağımsız bir "kapasite birimi başına TPS" katsayısı elde etmek.

### Kaynaklardan

[Burgess2016-REDP5320] IBM Redpaper REDP-5320, "IBM CICS Performance Series: CICS TS V5.3 Benchmark on IBM z13", ve aynı sistemlerin PCI'si [IBM-LSPR-zOS22]:

| Sistem | CP | TPS | PCI | LSPR (avg) | TPS / PCI |
|---|---|---|---|---|---|
| 2964-718 | 18 | 174.000 | 21.579 | 38,55 | 8,063 |
| 2964-726 | 26 | 227.000 | 29.048 | 51,89 | 7,815 |

[IBM-LSPR-ITRR] (aktarım): IBM Z LSPR ITRR tabloları bütün nesilleri System z9 2094-701 = 1,00 bazında verir. PCI bu ölçeğin sabit bir katıdır. z16 (3931) kademeleri için PCI, MSU ve Low/Average/High değerleri; z16 3931-701 = 2.253 PCI.

### Kural

```
TPS_PER_PCI = (8,063 + 7,815) / 2 = 7,939        (REDP-5320 işlemi cinsinden)
ham_TPS(kademe, profil) = PCI × 7,939 / w / (1 − f)
```

- n-way ölçekleme kaybı her kademenin PCI'sinin içindedir; köprüde ayrıca uygulanmaz.
- f = zIIP'e kayan pay: `ZIIP_OFFLOAD_FRACTION` 0,10 (0 / 0,10 / 0,25) [ASSUME].
- İki nokta arasındaki %3,1 fark köprünün belirsizliği olarak raporlanır.

### Makullük kontrolü (v3 §4.4.3)

IBM'in z14 duyurusundaki "günde 12 milyardan fazla şifreli işlem" (~139K TPS) [AmwalAlGhad2017-z14], z14'ün ~160K PCI olduğu kaba tahminiyle w ≈ 9'a karşılık gelir. Bu yalnızca büyüklük mertebesi teyididir.

### Açık kalan

Köprünün tek kaynağı REDP-5320. LSPR karışımının CICS/Db2 OLTP'ye benzediği bir varsayım (v3 §4.5).

---

## KB-03. x86 Kapasite Köprüsü (Çekirdek Başına TPS)

### Amaç

Mainframe'deki PCI köprüsünün x86 karşılığı. x86'nın çekirdek sayısını, dolayısıyla çekirdek başına lisansı (Oracle, vSphere), düğüm sayısını ve Patroni tavanını bu katsayı belirler.

### Kural

```
X86_TPS_PER_SPECINT_CORE = ölçülen_TPS / (fiziksel_çekirdek × SPECrate2017_int_base_per_core)
TPS_per_core(sunucu)     = X86_TPS_PER_SPECINT_CORE × SPECint_per_core(sunucu) × S(n) × (1 − VIRT) × (1 − CONT)
```

S(n) = düğüm içi ölçeklenme (KB-06); VIRT ve CONT = sanallaştırma ve konteyner ek yükü (aşağıda).

### Kaynaklardan

**Çapa adayı** [Vonng-PGPerf], Feng Ruohang (Vonng), "How Powerful is PostgreSQL Really?":
- Makine: "c5d.metal", "96C 192G". c5d.metal = 2 × Xeon Platinum 8275CL, 48 fiziksel / 96 mantıksal çekirdek.
- Veri: "16 x 10M" tablo, "basically 160M records".
- Ortam: "We still use AWS c5d.metal, but with full production environment configuration."
- oltp_read_write: 519.069. Birim şekil altyazısından: "Sysbench 10-item test results (QPS, higher is better)".
- Yazılı olmayanlar (Değ. #8 §2.2): sysbench koşusunun PostgreSQL sürümü (14.5 yalnızca pgbench için), iş parçacığı sayısı, süre, istemcinin yeri, `synchronous_commit`/`fsync` ayarı.

**SPEC CPU2017** (aktarım; sonuç sayfalarındaki değerler):

| Sistem | CPU | Çekirdek | SPECrate2017_int_base | Çekirdek başına [DERIVED] | Kaynak |
|---|---|---|---|---|---|
| Dell PowerEdge M640 | 2 × Xeon Platinum 8270 | 52 | 309 | 5,94 | [SPEC2019-M640-8270] |
| Dell PowerEdge R760 | 2 × Xeon Gold 6548Y+ | 64 | 628 | 9,81 | [SPEC2024-R760-6548Y] |
| HPE ProLiant DL380 Gen12 | 2 × Xeon 6787P | 172 | 1.570 | 9,13 | [SPEC2025-DL380G12] |

**Bağlam ölçümleri** (normalize edilemiyor; çapraz kontrol değil, büyüklük mertebesi bağlamı):

| Kaynak | Ortam | Ölçülen (kaynaktaki değer) |
|---|---|---|
| [Rockdata2026] [VENDOR] | Huawei Cloud c9.8xlarge, 32 vCPU, PG 18.6, bellek içi | 15.261 TPS (256 iş parçacığı) |
| [Tencent-PG-TestResults] | 1 / 4 / 8 / 48 "çekirdek", tam önbellek | 864 / 4.032 / 5.777 / 8.675 TPS |
| [Alibaba-PolarDB-PG16] | 8 çekirdek, ESSD PL3, bellekten büyük veri | 649 TPS |

### Türetme [DERIVED] (plan v1 §3.3)

```
25.953 TPS / 48 çekirdek = 541 TPS/çekirdek (Cascade Lake)
541 / 5,94 = 91 TPS / SPECint birimi
R760:  91 × 9,81 ≈ 893 TPS/çekirdek
Gen12: 91 × 9,13 ≈ 831 TPS/çekirdek
```

### Sanallaştırma ve konteyner ek yükü (plan v1 §3.7)

| Kaynak | Bulgu (aktarım) |
|---|---|
| [RedHat2025-OCPVDB] [VENDOR] | OpenShift Virtualization'da MariaDB/HammerDB; 4 örnekte VM'ler bare-metal verimin %80'i |
| [VMware2024-vSphereOCPV] [VENDOR] | Dell R650, SQL Server TPROC-C, 10 VM: vSphere 8 U3 OpenShift Virtualization 4.16'dan %27,6 fazla NOPM |
| [EDB-LocalPV] | Kubernetes yerel kalıcı birim: sıralı okuma −%3,6, yazma −%0,8; ağ tabanlı paylaşımlı PV −%89–95 |

### Kural (K kararı)

- **Çapa: K6 kendi ölçümümüz.** Vonng çapraz kontrol olur.
- K6 tamamlanana kadar `X86_TPS_PER_SPECINT_CORE` aralığı **60 / 91 / 120** (low = 120, x86 lehine).
- **K6 protokol şartları:**
  1. SPEC sonucu yayımlanmış perakende bir SKU kullanılır. Bulut bare-metal CPU'ları (8275CL, 8488C) özel SKU'dur; kullanılırsa perakende kardeşin SPEC değeri ayrı bir belirsizlik olarak yazılır.
  2. sysbench istemcisi ayrı makinede çalışır.
  3. PostgreSQL sürümü, iş parçacıkları, süre, `synchronous_commit`, `fsync`, `shared_buffers` raporlanır.
  4. 8 / 16 / 32 / 64 çekirdek taranır (USL uyumu, KB-06).
  5. `oltp_point_select`, `oltp_read_only` ve `oltp_write_only` de koşulur (KB-01).
  6. Bir koşu senkron replikayla yapılır (KB-05, D_repl).
- K6 ile `project_justification.md` §5.2 ("benchmark koşturma kapsam dışı") arasındaki gerilim x86 model dokümanında yazılır: araç analitik bir modeldir, ölçüm yalnızca kalibrasyon girdisidir.

### Parametreler

| Parametre | low (x86 lehine) | mid | high | Dayanak |
|---|---|---|---|---|
| X86_TPS_PER_SPECINT_CORE | 120 | 91 | 60 | [DERIVED]; K6'ya kadar geniş |
| VIRT_OVERHEAD vSphere | 0,03 | 0,07 | 0,15 | İki rakip [VENDOR] arasından [ASSUME] |
| VIRT_OVERHEAD OCP-V | 0,05 | 0,12 | 0,25 | Aynı |
| CONTAINER_OVERHEAD | 0 | 0,02 | 0,05 | [EDB-LocalPV] + [ASSUME] |
| ORACLE_THROUGHPUT_FACTOR | 1,30 | 1,00 | 0,80 | Kalibre edilemez (aşağıda) |

### Oracle

[Oracle-OTNLicense] lisansı lisans sahibinin şunu yapmasını yasaklar: "disclose results of any Program benchmark tests without Oracle's prior consent." Bu yüzden aynı donanımda Oracle ile PostgreSQL'i karşılaştıran bağımsız bir ölçüm yoktur. Orta değer 1,0 kayıtsızlık ilkesidir: kaynak yokken bir yön iddia edilmez. Tezde bu, yapısal bir veri sınırı olarak yazılır.

### Karar

**K (b), Emirhan, 2026-11-16.** Nesil: K2 (2026-11-02), R760 / DL380 Gen11 / SR650 V3 ana senaryo, Gen12 duyarlılık. Tek referans sunucu: K5 (2026-11-02).

---

## KB-04. Platformlar Arası Tutarlılık Kontrolü

### Amaç

İki köprü bağımsız zincirlerden gelir. Birinde bir mertebe hatası varsa burada görünür. Bu bir doğrulama değil, büyüklük mertebesi kontrolüdür ve modelde parametre değildir.

### Değerler [DERIVED]

| Durum | z16 GP CP başına oltp_rw TPS (%90 tavanda) | 1 CP ≈ R760 çekirdeği (893 TPS) |
|---|---|---|
| Eski bileşim (w = 9,15) | 2.253 × 7,939 / 9,15 = 1.955 | 2,19 |
| Eski bileşim, zIIP payıyla (f = 0,10) | 2.172 | 2,43 |
| F kararı (aralık ağırlığı 3,4, w ≈ 12,5) | 1.431 | 1,60 |
| F kararı (ağırlık 3,9, w ≈ 13,2) | 1.355 | 1,52 |

Aralık uçları birlikte (CPU_US_PER_SQL_READ 15–60, X86_TPS_PER_SPECINT_CORE 60–120): yaklaşık 0,8–4,5 çekirdek/CP.

### Kaynaklardan: literatürdeki "24–80 çekirdek" iddiası

[Shedletsky2008] [VENDOR] konsolidasyon formülü (aktarım): `N < P_R × U_R × C_R`. Tipik oranlar: performans oranı P_R 1–3, kullanım oranı U_R 10–20 (dağıtık sunucular %5–12, mainframe %80–90 kullanımda), sunucu başına çekirdek 1–64. IBM'in "1 CP = 24–80 x86 çekirdeği" sonucunun büyük kısmı U_R'den ve dev/test kopyalarından gelir, işlemci hızından değil (`benzer_calismalar_v1.md` §3.3). Bizim köprümüz yalnızca P_R'yi ölçer. U_R'nin karşılığı KB-05'te, dev/test KB-14'te.

---

## KB-05. Kullanım Oranı, Kuyruk ve Latency

### Amaç

Bir düğümün tepe yükte ne kadar doldurulduğu kurulu kapasiteyi belirler. Kurulu kapasite de donanımı ve çekirdek başına lisansı belirler. İki taraf aynı kurala bağlanmazsa IBM'in U_R etkisi (KB-04) kontrolsüz biçimde sonuca girer.

### Mainframe tarafı (v3 §5.3)

```
E[X_cpu] = c / ham_TPS                         (c = fiziksel CP)
R_cpu(p) = E[X_cpu] × 1/(1 − ρ) × ln(1/(1 − p))     (c bağımsız M/M/1; tutucu üst sınır)
R(p)     = D_io + R_cpu(p)
ρ_max    = min( 1 − E[X_cpu] · ln(1/(1−p)) / (hedef − D_io) , 0,90 )
```

- %90 operasyonel tavan [ASSUME, kapasite planlama pratiği]. Latency hedefi tavanı yalnızca düşürebilir.
- D_io: oltp_rw'de M1 0,26 ms, M2–M4 0,46 ms (KB-09).

### x86 tarafı (U kararı)

```
ρ_max(x86) = min( ρ_latency , X86_UTIL_CEILING )
R(p)       = D_ağ + D_io + D_repl + R_cpu(p)
D_ağ       = ROUNDTRIPS_PER_TX × NET_RTT
D_repl     = senkron replikasyonda commit başına bir gidiş-dönüş (mesafe × 10 µs/km, ortak fizik sabiti)
```

- Aynı kuyruk ailesi: çekirdek başına bağımsız M/M/1. `project_context_restore_v4.md` x86 için M/M/c öngörüyordu; bu, iki taraf arasında bir tutuculuk asimetrisi yaratırdı.
- `X86_UTIL_CEILING`'in mainframe'den düşük olabilmesinin gerekçesi: x86'da WLM ve CoD karşılığı olmadığı için veritabanı düğümleri tepe yükte boşlukla işletilir.
- `benzer_calismalar_v1` B1'deki %15–20 alt uç **ana aralıkta yoktur.** Tek adanmış iş yükünde tepe yük boyutlaması, HA replikaları ve dev/test zaten ayrı sayıldığı için bu uç çift sayım olur. Yalnızca tezdeki IBM iddiasıyla uzlaştırma analizinde ayrı bir "konsolide edilmemiş park" senaryosu olarak gösterilir.

### Kaynaklardan

- [EDB-SyncRep] (aktarım): 10 ms yapay gecikmede 40 istemcide `remote_write`, yazma gecikmesine ~6,5 ms ekledi ve verimi %40 düşürdü; 3 ms'de etki yük altında ortadan kalktı.
- [StorageReview2022-P5520] [VENDOR sponsorlu] (aktarım): yerel NVMe ortalama tamamlanma süresi ~141 µs (karma), %99,99'luk dilim 769 µs.

### Parametreler

| Parametre | low (x86 lehine) | mid | high | Dayanak |
|---|---|---|---|---|
| X86_UTIL_CEILING | 0,90 | 0,70 | 0,50 | U kararı [ASSUME]; low = mainframe ile eşit |
| NET_RTT_MS | 0,05 | 0,15 | 0,5 | [ASSUME], aynı veri merkezi |
| ROUNDTRIPS_PER_TX | 1 (saklı yordam) | 20 (sysbench) | 20 | sysbench ifade başına bir gidiş-dönüş |
| T_SAN_READ (µs) | 150 | 250 | 400 | [ASSUME] |

### Karar

**U (b), Emirhan, 2026-11-16.**

---

## KB-06. Ölçekleme Mimarisi ve Kapasite Tavanları

### Amaç

Yüksek TPS'te crossover'ın yeri, iki tarafın tek sistem tavanına bağlıdır. İki tavan aynı statüde (modellenmeyen ölçekleme seçeneği) yazılmalıdır.

### İki taraf

| | Mainframe | x86 |
|---|---|---|
| Modellenen | Tek CEC; M2–M4'teki ikinci frame yedektir, kapasite eklemez | PostgreSQL + Patroni: tek birincil (yazma ölçeklenmez); Oracle RAC: düğüm ekleyerek ölçeklenir |
| Modellenmeyen | Parallel Sysplex data sharing | Citus (sharding) — K3 |
| Tavan | oltp_rw'de ~187K TPS (3931-7K0, w = 9,15); F ile yeniden hesaplanacak | Patroni: "katalogdaki en büyük düğüm × S(n)" |

### Kaynaklardan

- [Patroni-ReplModes] (aktarım): Patroni tek yazıcılı mimaridir; replikalar yazma kapasitesi eklemez.
- [Oracle2024-RAC] [VENDOR] (aktarım): uygulama ölçeklenmesi %80'in altındaysa çekişme işaretidir; 19c'de düğüm kaybında 15 saniyenin altında toparlanma.
- [Kapila2016-PGCon] (aktarım): PostgreSQL yazma yolu darboğazları (WAL flush, ProcArrayLock, CLOG).

### Kural

- Düğüm içi ölçeklenme: `S(n) = (n / n_ref)^(b_x86 − 1)`, n_ref = çapanın çekirdek sayısı. K6'da USL (Gunther) uyumu ile değiştirilir ya da desteklenir (`benzer_calismalar_v1` B7).
- Ana katalog 64 çekirdeğe kadardır (Vonng çapasının ~1,3 katı). 96–128 çekirdek "ekstrapolasyon" işaretli bir duyarlılıktır.
- R760 sınıfı 2 × 32 çekirdekte tavan [DERIVED]: 893 × 64 × S(64) ≈ 54–57K ham; sanallaştırma ve tavan sonrası ~35–50K oltp_rw TPS. U kararıyla tavan X86_UTIL_CEILING'e bağlı olarak düşer.
- **Tavanın üstünde** (~50K TPS'ten mainframe tavanına kadar) karşılaştırma mainframe ile Oracle RAC arasındadır. RAC tarafı kalibre edilemeyen iki parametreye dayanır (`ORACLE_THROUGHPUT_FACTOR`, `RAC_SCALING_EFFICIENCY`). Sonuç bu bölgede aralık olarak verilir.

### Parametreler

| Parametre | low (x86 lehine) | mid | high | Dayanak |
|---|---|---|---|---|
| B_X86 | 1,00 | 0,90 | 0,80 | [ASSUME]; K6/USL ile kalibre |
| RAC_SCALING_EFFICIENCY | 0,95 | 0,90 | 0,80 | [ASSUME]; Oracle'ın %80 eşiği alt uç |

### Karar

K3 (b), Emirhan, 2026-11-02 (Citus yok, tavan bir sınırlama). Tavanın SKU'ya bağlı tanımı Değ. #8 §2.6'dan.

---

## KB-07. Availability Denklemi

### Amaç

İki tarafın availability'si aynı denklemle, aynı veri merkezi olaylarıyla hesaplanmalıdır. Aksi halde "nine" değerleri farklı kaynaklardan gelir ve karşılaştırılamaz.

### Kural (v3 §6.3; plan v1 §8.1)

```
D(topo) = λ_saha × [ (1 − p_uzun) × min(d_kısa, T_rec) + p_uzun × min(d_uzun, T_rec) ]   ← ortak modül
        + λ_planlı × T_planlı(topo)                                                    ← platforma özgü
        + D_cpc                       (mainframe, yalnızca M1)
        + N_düğüm × λ_düğüm × T_failover(DB, topo)    (x86, D_cpc'nin yerine)
A = 1 − D / 8.760
```

Elle geçişte: `T_rec = MANUAL_FAILOVER_DECISION_MINUTES (ortak) + teknik geçiş süresi (platforma özgü)`.

### Kaynaklardan

- [Uptime2025-PR] (aktarım): operatörlerin %53'ü son üç yılda kesinti bildirdi (2020'de %78); 2024'te olayların %9'u ciddi/ağır; etkili kesintilerin %54'ü güç kaynaklı, %23'ü BT/ağ.
- [DCF2022-Uptime] (aktarım): kamuya yansıyan kesintilerin 24 saatten uzun süren payı 2017'de %8, 2021'de ~%30.
- [ITIC2023-IBMZ] (aktarım): 200+ z16 kullanıcısının %96'sı 9 nine, yani sunucu başına yılda 31,56 ms plansız kesinti (sunucu donanımının kendi arızaları).
- [TechChannel2024-ITIC] (aktarım): Lenovo ThinkSystem güncel x86 sunucuları 8 nine (yılda 315 ms).
- [Vishwanath2010] (aktarım): 100.000'den fazla sunucuda sunucuların ~%8'i yılda en az bir donanım onarımı gördü; onarımların %78'i sabit disk kaynaklıydı.
- [IBM-SG24-8446] (aktarım): dört desen (Reliable base, Failover capable, Fault tolerant, Adaptive continuity) ve genel RTO/RPO aralıkları; desen başına availability yüzdesi vermez. DR'de RTO 2–72 saat; 2 saatin altı GDPS otomasyonu ve test edilmiş süreç ister.

### Parametreler

**Ortak (`common_model.py` §2):**

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| λ_saha (olay/yıl) | 0,05 | 0,15 | 0,25 | [Uptime2025-PR] |
| d_kısa (saat) | 1 | 2 | 4 | [ASSUME] |
| p_uzun | 0,08 | 0,15 | 0,30 | [DCF2022-Uptime] |
| d_uzun (saat) | 24 | 48 | 72 | SG24-8446 DR üst sınırı |
| MANUAL_FAILOVER_DECISION_MINUTES | 45 | 90 | 180 | [ASSUME]; önceki M2 toplamı 60 / 120 / 240 dk'nın ayrıştırması |

**Mainframe:** D_cpc 0,03 / 0,32 / 3,15 sn/yıl [ITIC2023-IBMZ]; λ_planlı 0,25 / 0,5 / 1 [ASSUME]; T_planlı M1 2 / 4 / 8 saat, M2 15 / 30 / 60 dk, M3 2 / 10 / 30 dk, M4 20 / 30 / 60 sn (v3 §6.4).

**x86 (plan v1 §8.1, 8.3; Değ. #8 §3.4):**

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| NODE_EVENTS_PER_YEAR | 0,03 | 0,10 | 0,30 | [Vishwanath2010] aşağı doğru; high [ASSUME] |
| T_failover Patroni | 15 sn | 35 sn | 90 sn | [Pigsty-RTO] |
| T_failover RAC | 5 sn | 15 sn | 5 dk | [Oracle2024-RAC, Oracle2026-MAA] |
| λ_planlı | 0,25 | 0,5 | 1 | Mainframe ile aynı aralık |
| Rolling yama switchover'ı | 12/yıl × 5 sn | 12/yıl × 15 sn | 12/yıl × 30 sn | Değ. #8 §3.4 [ASSUME] |
| T_planlı X1 | 5 dk | 15 dk | 60 dk | [ASSUME] |
| T_planlı X3–X4 | 30 sn | 2 dk | 10 dk | [ASSUME]; Oracle Gold < 30 sn [Oracle2026-MAA] |

- [Pigsty-RTO] (aktarım): Patroni varsayılan ayarlarla düğüm kaybında 27–41 sn, süreç çökmesinde 2–41 sn. Bunlar parametrelerden türetilen teorik sürelerdir, ölçüm değil.
- [YellowBricks2021] (aktarım): vSphere HA'da ikincil host 15–18 sn, birincil host ~50 sn içinde "ölü" ilan edilir. DB katmanı daha hızlı devrettiği için vSphere HA ikincil bir mekanizmadır.

### Açık kalan

Planlı kesinti sıklığı iki tarafta da kaynaksız (en etkili availability varsayımı). Bölgesel felaket ayrıca modellenmez.

---

## KB-08. Topoloji Eşlemesi

### Kaynaklardan

**Mainframe** [IBM-SG24-8446, Cook2026-GDPS] (v3 §6.2):

| Kod | Desen | RPO (tek site kaybı) | T_rec (mid, aralık) |
|---|---|---|---|
| M1 | Reliable base: tek CPC'de sysplex, tek site | 24 saat [ASSUME] | Alternatif site yok |
| M2 | Failover capable: DR CPC (CBU), Metro Mirror, otomasyonsuz | 0 | 2 saat (1–4) |
| M3 | Fault tolerant: GDPS Metro Global, HyperSwap | 0 | 30 dk (2–60) |
| M4 | Adaptive continuity: GDPS CA, yazılım replikasyonu | 5 sn (0–5) | 30 sn (20–60) |

[Cook2026-GDPS] [VENDOR] (aktarım): GDPS Metro RPO 0, RTO ~2 dk (çok-siteli iş yükü) / < 1 saat (tek siteli); GDPS CA RPO 0–5 sn, RTO 20–30 sn (portföy slaytında < 60 sn).

**x86** [Oracle2026-MAA] [VENDOR], [Pigsty-RTO] (plan v1 §8.2):

| Kod | Karşılık | Oracle (MAA) | PostgreSQL + Patroni | RPO | T_rec (site) |
|---|---|---|---|---|---|
| X1 | M1 | Silver: RAC + Application Continuity, tek site | Tek sitede 3 düğüm, 1 senkron replika; etcd 3 üye | 24 saat (M1 ile aynı kural) | Alternatif site yok |
| X2 | M2 | X1 + uzak sitede Data Guard (Max Availability), elle geçiş | X1 + uzak sitede standby küme, elle terfi | 0 | Ortak karar süresi + teknik terfi |
| X3 | M3 | Gold: RAC + Active Data Guard + Fast-Start Failover | Çok siteli Patroni; DCS 3 sitede | 0 | 1 / 2 / 5 dk; Oracle Gold "saniyeler – 2 dakika" |
| X4 | M4 | Platinum: GoldenGate aktif-aktif | **Infeasible** (K4) | Saniyeler | < 30 sn |

### Kural

- RPO ve RTO kullanıcı girdisi iki tarafta aynı biçimde topolojiyi seçer.
- M1 ve X1'in RPO'su aynı kurala bağlıdır: yedek hedefe log gönderim aralığı. İkisi birlikte 24 saatte kalır ya da birlikte güncellenir (Değ. #8 §3.4).
- Topoloji personel çarpanı iki tarafta aynı tablodur (KB-13).

### Karar

K4 (b), Emirhan, 2026-11-02: X4, PostgreSQL için infeasible. Açık kaynak çekirdekte karşılığı olmayan bir topoloji uydurulmaz. Mainframe'deki "komik topoloji" kuralıyla (v4 §4.3) tutarlıdır.

---

## KB-09. Storage Arayüzü ve Fiyat Sözleşmesi

### Amaç

Storage veri hacmiyle büyüdüğü için ikinci bir crossover ekseni oluşturur. 10K TPS'te storage + yedek 20 TB'ta toplamın %1,6'sı, 500 TB'ta %22'si, 2.000 TB'ta %52'si (v3 §8.1.1). İki taraf aynı girdilerle ve aynı fiyat tanımıyla boyutlanmalıdır.

### Ortak girdiler (v3 §8.1.6)

`data_tb`, `data_growth`, 3 yıllık planlama ufku, iş yükü profilinden IOPS (oltp_rw'de 5,8 IOPS/işlem; F ile değişmez, çünkü I/O okuma sayısından gelir), aynı %70 IOPS tavanı, topolojinin seçtirdiği kopya sayısı.

### Mainframe tarafı

```
ham_TB = veri_TB × (1 + büyüme)^3 × 1,5 (DB ek yükü) / 1,0 (sıkıştırma) / 0,75 (RAID 6)
```

Kopya: M1 1, M2 2, M3/M4 4.

[ITJungle2022-Storage] (aktarım): 16 adet 15,36 TB flash kartı liste fiyatı $2,12M, kart başına $132.381 = $8,62/GB (kontrolcü hariç), Mayıs 2022. Etkin fiyat ~$2.590/TB ham (liste × 0,30).

### x86 tarafı (K1)

| DB mimarisi | Storage | Kopya sayısı |
|---|---|---|
| Oracle RAC | Paylaşımlı all-flash SAN | Site başına 1 + DR sitesinde Data Guard kopyası |
| PostgreSQL + Patroni | Yerel NVMe | Düğüm sayısı (X1'de 3) |

[VendorBenchmark2026-Storage] (aktarım), Q1 2026, kullanılabilir/etkin TB: Dell PowerStore $65–170, Pure //X $70–175, NetApp AFF $65–190, HPE Alletra $100–215 (indirimli); liste $140–400. Destek ilk yıl donanımın %10–20'si, yıllık %10–25.

### Fiyat sözleşmesi (`common_model.py` §6)

1. Boyutlandırma iki tarafta aynı sırayla ham TB üretir: mantıksal veri → planlama ufku → DB ek yükü → sıkıştırma/veri azaltımı → RAID/replika kullanılabilir oranı → ham TB.
2. Her teklif önce ham TB başına liste fiyatına çevrilir (`price_per_raw_tb`). İndirim yalnızca bir kez ve listeye uygulanır.
3. Veri azaltım oranı boyutlandırmada bir kez kullanılır; fiyata ikinci kez gömülmez. Kodda örnek: $200/etkin TB, DRR 2,5, RAID kullanılabilir 0,75 → $375/ham TB.

### x86'ya özgü eklemeler (Değ. #8 §3.3)

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| AFA_DATA_REDUCTION (geri çevirme) | 1,5 | 2,5 | 4,0 | [ASSUME] |
| PG_BLOAT_FACTOR (DB ek yükü, PostgreSQL) | 1,1 | 1,3 | 1,6 | [ASSUME]; MVCC şişmesi + WAL tutma |
| Patroni düğüm içi RAID | RAID 0 / JBOD + replika | | | [ASSUME], açık varsayım |

### Karar

K1 (a), Emirhan, 2026-11-02: storage tipi DB mimarisine bağlı.

---

## KB-10. Yedekleme

### Kural

Hacim kuralı iki tarafta aynıdır (v3 §8.10.2):

```
image copy (tam yedek) = D_plan × hafta × (1 tam + 6 artımlı × günlük değişim)
log                    = ort. TPS × işlem başına log baytı × 86.400 × 7 × hafta
işlem başına log baytı = yazma × 400 B + commit × 200 B         (x86'da × WAL_FPW_FACTOR)
```

Kısıtlar: 8 saatlik pencere; M1/X1'de tam geri yüklemenin RTO'nun yarısına sığması.

### Kaynaklardan

- [IBM-Db2z12-Backup]: "Make two copies of each level of image copy data sets".
- [Hendley2024-IDUG] (aktarım): tam image copy tipik olarak haftada bir; haftalık değişim %10'u aşan nesnelerde tam kopya önerilir.
- [MinIO-ObjectTCO] [VENDOR] (aktarım): 60 × 16 TB HDD'li 2U sistem $70K, 720 TB kullanılabilir.
- [Nubbo2026-S3] (aktarım): Standard-IA $0,0125/GB-ay, en kısa süre 30 gün.
- [AWS-DXPricing] (aktarım): 10 Gbps dedicated port $2,25/saat; ABD içi DX çıkış $0,02/GB.

### İki taraf

| | Mainframe | x86 |
|---|---|---|
| Hedefler | TS7770, on-prem nesne (DS8900F TCT), AWS S3 | On-prem nesne, AWS S3 (TS7770 uygulanmaz) |
| Fiyat fonksiyonu | `cm.onprem_object_store`, `cm.s3_hybrid` | Aynı fonksiyonlar |
| Yol ve verim | TCT ≤ 5.000 MB/s [ASSUME] | pgBackRest / RMAN; verim kısıtı platforma özgü |
| Yazılım | — | pgBackRest (lisans 0), RMAN (EE'ye dahil) |

### x86 parametresi

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| WAL_FPW_FACTOR | 1,5 | 2 | 3 | [ASSUME]; PostgreSQL full-page writes; K6 ile ölçülecek |

---

## KB-11. Lisans Tabanı (Yapısal Asimetri)

### Kural

Bu fark gerçek ve yapısaldır. **Eşitlenmez, modellenir** (plan v1 §6.5).

| | Mainframe | x86 |
|---|---|---|
| Fatura tabanı | Tüketilen MSU'nun aylık R4HA tepesi (AWLC, kümülatif kademeler) | Kurulu fiziksel çekirdek (Oracle, vSphere) ya da düğüm/soket çifti (OpenShift, OVE, RHEL) |
| DR sitesi | CBU: kalıcı (küçük) kapasiteden | Tam lisans (Data Guard standby, DR düğümleri) |
| Geçici kapasite | On/Off CoD, TFP | Karşılığı yok: on-prem'de alınmış çekirdeğin lisansı boşta da ödenir |
| Garanti | 1 yıl [ASSUME] | 3 yıl tipik [ASSUME] |

### Kaynaklardan

- [IBM-SC28-7025]: "Software charges for the designated CBU machine are based on its permanent configuration."
- [Oracle2026-CoreFactor] (aktarım): Intel Xeon ve AMD EPYC 9005/9004 için çekirdek faktörü 0,5 (Ocak 2026 tablosu).
- [Oracle-Partitioning] (aktarım): VMware yumuşak bölümlemedir; VM'in çalışabileceği bütün fiziksel çekirdekler lisanslanır. Model Oracle'ı adanmış düğümlerde varsayar.
- [Redress2026-OraclePL] [danışman] (aktarım; doğrulanmalı): işlemci başına liste EE $47.500, RAC $23.000, Diagnostics $7.500, Tuning $5.000; destek net lisansın yıllık %22'si.
- [AceMQ-VVFvsVCF] [iş ortağı] (aktarım): VVF $135, VCF $350 / çekirdek / yıl; CPU başına en az 16, sipariş başına en az 72 çekirdek.
- [AceMQ2026-Renewals] [iş ortağı] (aktarım, 37 teklif): VVF 1 yıl $117–196, 3 yıl $100–160; VCF 3 yıl $257–348.

### Parametreler (plan v1 §12.1)

| Parametre | low (x86 lehine) | mid | high |
|---|---|---|---|
| VSPHERE_USD_PER_CORE_YEAR | 100 | 150 | 350 |
| OCP_USD_PER_SOCKETPAIR_YEAR | 6K | 11K | 15K |
| ORACLE_DISCOUNT | 0,60 | 0,45 | 0,20 |
| PG_SUPPORT_USD_PER_CORE_YEAR | 0 | 500 | 1.500 |

---

## KB-12. Kapsam Sınırı: İşlem Yöneticisi ve Uygulama Katmanı

### Amaç

İki tarafın kapsam sınırı aynı olmalıdır. Mainframe CPU'su ve lisansı CICS'i (işlem yöneticisi) içeriyor; x86 çapasında uygulamanın yerini modelin dışındaki sysbench istemcisi tutuyor. Bu, mainframe aleyhine bir kapsam asimetrisidir (plan v1 §14.4).

### Kaynaklardan

- [Burgess2016-REDP5320]: `CPU_US_TM_BASE` = 85,9 µs (z13), CICS + 5 bellek okuması.
- [Shedletsky2008] [VENDOR] (aktarım): uygulama katmanında 4,9 kat komut farkı iddiası. Bağımsız doğrulaması yok.

### Kural (C kararı)

```
TM_payı              = CPU_US_TM_BASE / CPU(oltp_rw)        (eski bileşimde 85,9 / 786 ≈ %10,9; F ile ≈ %7,8)
uygulama_çekirdekleri = DB_çekirdekleri × TM_payı / (1 − TM_payı)
```

- Uygulama katmanı Linux VM olarak fiyatlanır: donanım, vSphere ya da OpenShift, RHEL. Açık kaynak uygulama sunucusu olduğu için ek lisans yoktur.
- HA topolojiye göre: sitede N+1, DR sitesinde kopya.
- Bu katman `ROUNDTRIPS_PER_TX` ağ terimini doğal kılar, çünkü uygulama veritabanından ayrı düğümdedir (KB-05).
- 4,9 kat yalnızca üst uç duyarlılığıdır.
- Mainframe tarafında değişiklik yok: CICS CPU'su ve lisansı modelde kalır.

### Karar

**C (b), Emirhan, 2026-11-16.**

---

## KB-13. Personel

### Amaç

10K TPS'te personel mainframe maliyetinin ~%45'i. İki tarafın personeli farklı sürücülerle ölçülürse crossover'ı teknoloji değil, ölçüm farkı belirler. Değ. #8'de bulunan tutarsızlık: 10K TPS'te mainframe 30,8 FTE, x86 Eagle sunucu saatleriyle 0,39 FTE (taban ekiple 4). Fark TPS başına aylık ~$36.

### Kaynaklardan: mainframe (kuruluş düzeyi)

- [IBM-CPO2014-Skills] [VENDOR], 17 müşteri: "5 FTE to start + 1 FTE for every 625 MIPS".
- [CA2016-MFEcosystem], ikincil aktarım (aktarım): kurulu MIPS / mainframe FTE 152 → 268 (2016, 5 yıl).
- [Jones2007-TCO] [VENDOR]: "167-625 MIPS per headcount (500 is typical)".
- [Rhoderick2007-TPFUG] [VENDOR] (aktarım): Gartner'a göre 289 personel / 5.994 MIPS (2001) → 260 personel / 13.272 MIPS (2004).

### Kaynaklardan: x86 (kuruluş düzeyi)

- [Shedletsky2008] [VENDOR], 3.917 dağıtık sunucu: "7.8 servers per headcount @ $159,800/yr/headcount".
- [Calderon2011-Labor] [VENDOR], 2011 (aktarım): adanmış Intel 30,7 sunucu/FTE; sanallaştırılmış Intel 52,5 VM/FTE; donanım işi fiziksel sunucu başına yılda 32 saat, yazılım işi imaj başına yılda 36 saat; yüklü maliyet $159.600/FTE (2.080 saat).
- [Computerworld-IDC2007], Computerworld aktarımı: "the average VM to administrator ratio, or average number of virtual images per administrator, is 200".
- [Shedletsky2008], Québec vakası: "Each administrator can manage 100 consolidated Linux images."
- [Avasant2008-Headcount] (aktarım): sistem programcıları ve yöneticiler 2008'de BT personelinin medyan %6,8'i (2006'da %6,6); sunucu/personel oranları ücretli raporda.

**Neden doğrudan oranlanamaz [DERIVED]:** mainframe ortalaması MIPS başına, x86 ortalaması sunucu başına. 10K TPS'lik iş yükü mainframe'de 11.743 PCI, yani Gartner'a göre ~44 FTE. Aynı iş x86'da bizim köprümüzle tek bir sunucuya sığıyor, yani ~1/30 FTE. Oran ~1.300 kat çıkar. Fark verimlilikten değil, iki ortalamanın farklı yoğunluktaki parkları ölçmesinden gelir.

### Kaynaklardan: aynı iş yükü karşılaştırmaları

Bulunan bütün nicel vakalar IBM ya da IBM bağlantılı. Oran = x86 / mainframe.

| # | Kaynak | Karşılaştırma (kaynaktaki sayılar) | Oran [DERIVED] | Birim ve kapsam |
|---|---|---|---|---|
| 1 | [Rhoderick2007-TPFUG], IBM SWG veri merkezi | 900 dağıtık sunucu vs 3.192 MIPS: sistem personeli 30 FTE vs 3,15 FTE; System z'de 6 FTE operasyon; toplam personel $6.690K vs $793K | 30 / 9,15 = **3,28** (maliyetle 8,4) | FTE; dağınık park |
| 2 | [Rhoderick2007-TPFUG], First National Bank of Omaha | 30+ Sun Solaris ve 560+ Intel sunucu, 24 kişi; z990'a konsolidasyon sonrası 8 kişi | **3,00** | FTE; dağınık park |
| 3 | [Calderon2011-Labor], 500 iş yükü senaryosu | Intel: 77 sunucu, 14.992 saat/yıl, 7,21 yönetici; zEnterprise: 12.147 saat/yıl, 5,84 yönetici | **1,23** | FTE, saat tabanlı; sanallaştırılmış x86; mainframe tarafı zLinux |
| 4 | [Rhoderick2007-TPFUG], Baldor | BT personeli 50 → 38 (z990'a geçiş) | **1,32** | Toplam BT personeli |
| 5 | [Jones2007-TCO], IBM Global Services | 62 Linux sunucu × $6.000 = $372.000/yıl vs bir yönetici $120.000/yıl | 3,10 | Personel maliyeti; zLinux |
| 6 | [Rhoderick2007-TPFUG], örnek veri merkezi modeli | Dağıtık $2.520.000 vs mainframe $1.680.000 | 1,50 | Personel maliyeti; varsayımsal model |
| 7 | [Shedletsky2008], Québec | System Admin $5.944.828 vs $386.518 | 15,4 | Sistem yönetimi maliyeti; zLinux |
| — | [IBM2012-TCOLessons-zEC], DR testi | 14.952 vs 2.051 kişi-saat/yıl | 7,3 | Yalnızca DR testi; dışarıda |
| — | Solitaire Interglobal 2013 ([IBM-CPO2014-Skills] aktarımı) | "as much as 13x smaller" | — | Tabansız üst sınır iddiası; dışarıda |

[DERIVED] Geometrik ortalamalar: FTE vakaları (1–4) **2,0**; konsolide/sanallaştırılmış vakalar (3–4) **~1,25**; bütün vakalar (1–7) **2,7** (medyan 3,0).

**Karşı taraf:** göç satıcılarının belgelerinde (Astadia ROI kılavuzu, AWS re:Invent 2021 Micro Focus oturumu, Infosys vakası) personel tasarrufu iddia ediliyor, ama FTE ya da personel maliyeti sayısı yok. Astadia: bir müşterisi "eliminated an overnight shift, delivering substantial savings on labor" (rakam yok). Bağımsız (Gartner, Avasant, IDC) aynı iş yükü karşılaştırması bulunamadı.

**Karşılaştırılabilirlik notları:**
- Bütün oranlar üretici kaynaklı ve büyük ihtimalle x86 aleyhine yanlı.
- Yüksek oranlar dağınık parklardan geliyor: vaka 1'de 30 FTE / 900 sunucu = sunucu başına 0,033 FTE, yani Eagle'ın 30,7 sunucu/FTE değerinin aynısı. Fark kişi başı verimlilikten değil sunucu sayısından geliyor. Bizim modelimizde sunucu sayısı KB-03 ve KB-05'ten geliyor; bu oranı almak sunucu yayılmasını ikinci kez sayar.

### Kural (P kararı, Emirhan, 2026-11-16)

```
FTE_ortak(TPS) = max( STAFF_FLOOR_FTE , FTE_1000 × (PCI_eşdeğer(TPS) / 1000)^b ) × topoloji_çarpanı
PCI_eşdeğer(TPS) = TPS × w(profil) × (1 − f) / TPS_PER_PCI / 0,90      (sürekli, kademe basamağı yok)
FTE_mainframe = FTE_ortak(TPS)
FTE_x86       = FTE_ortak(TPS) × STAFF_RATIO_X86
aylık personel = FTE × yüklü_ücret(WAGE_LEVEL) / 12                    (iki tarafta ortak ücret)
```

- **Ana senaryoda `STAFF_RATIO_X86` = 1,0.** Personel crossover için nötrdür.
- **Duyarlılık senaryoları:** 1,25 (konsolide x86 vakaları) ve 2,0 (bütün FTE vakaları). İkisi de IBM vakalarına atıfla ve üretici yanlılığı notuyla raporlanır.
- **Başabaş personel oranı başlık çıktısıdır.** İki platformu eşitleyen `STAFF_RATIO_X86` değeri. Sonuç "x86 personeli, aynı iş yükü için mainframe personelinin X katından azsa x86 kazanır" biçiminde verilir.
- **Ek görünüm: personel hariç TCO.** Her sonuç personelli ve personelsiz verilir.
- **Elenen x86 değişkenleri:** sunucu başına 32 saat, imaj başına 36 saat, h_db (DBA saati), yığın çarpanı, ayrı x86 taban ekip mantığı.
- **Mainframe'e etkisi:** personel artık kurulu kademenin PCI'sinden değil, iş yükünün sürekli PCI eşdeğerinden hesaplanır. Latency için alınan boş kapasite personeli büyütmez (v3 §7.7.5'teki "kurulu kapasite" tercihi değişir). Yıllık modda tepe TPS kullanılır. Bu değişiklik mainframe sonuçlarını biraz kaydırır ve kodlamada log'a işlenir.
- Topoloji çarpanı ortak tablo: M1/X1 1,00 · M2/X2 1,05 · M3/X3 1,15 · M4/X4 1,25 [ASSUME].

### Parametreler

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| STAFF_SCENARIO (FTE_1000; b) | 4,0; 0,60 | 5,5; 0,70 | 7,0; 0,80 | [IBM-CPO2014-Skills], [CA2016-MFEcosystem] (v3 §7.7.3) |
| STAFF_FLOOR_FTE | 3 | 4 | 5 | [ASSUME] 7/24 nöbet |
| LOADED_WAGE_USD | $122K | $162K | $215K | [BLS-OOH] × [BLS2026-ECEC]/[IDC2016-ConnectedMF] |
| STAFF_RATIO_X86 | 1,0 (ana senaryo, aralığa girmez) | | | Duyarlılık: 1,25 / 2,0 |

### Tezde nasıl yazılır

"Personel düzeyi kuruluş düzeyindeki mainframe verisinden gelir ve iki platforma aynı eğriyle uygulanır. Platformlar arası personel farkı için bağımsız bir kaynak yoktur; üretici kaynaklı vakalar 1,23–15,4 arasında dağılır. Bu yüzden ana sonuç personel açısından nötrdür ve sonucun bu varsayıma duyarlılığı başabaş oranıyla gösterilir."

---

## KB-14. Üretim Dışı Ortamlar

### Kural (`common_model.py` §9)

```
nonprod = NONPROD_FACTOR(platform) × birincil sitenin {yazılım + compute donanımı (amortisman + bakım) + enerji + birincil storage}
```

DR, site otomasyonu (GDPS / MAA), yedek ve personel hariç. Personel KB-13'te üretimle birlikte sayılır.

### Kaynaklardan

[IBM2013-TCOLessons] [VENDOR] (aktarım): üretim dışı ortamlar mainframe'de üretimin ~+%20'si, dağıtıkta çoğu zaman +%200'ü; HA için adanmış kopya üretimin 2–2,5 katı.

### Parametreler

| Platform | low | mid | high | Stres |
|---|---|---|---|---|
| Mainframe | 0 | 0,20 [IBM2013-TCOLessons] | 0,50 [ASSUME] | — |
| x86 | 0 | 0,50 [DERIVED, ASSUME] | 1,00 [ASSUME] | 2,0 [IBM2013-TCOLessons] |

**x86 orta değerinin türetmesi:** X1'de birincil site 3 düğüm. Üretimle aynı boyutta tek düğümlük bir staging ortamı ≈ 0,33. Küçük dev/test düğümleri ≈ 0,1–0,2. Toplam ≈ 0,5. Üst uç 1,0, staging'in tam bir küme kopyası olmasıdır.

**Farkın yapısal gerekçesi:** mainframe'de dev/test aynı CEC'te LPAR olarak durur ve R4HA tepesine az katkı verir. x86'da ayrı düğüm ve Oracle'da ayrı çekirdek lisansı ister. Mainframe kuralı bu avantajı saymadığı için zaten mainframe aleyhine tutucudur.

### Karar

İki tarafa ayrı çarpan: Emirhan, 2026-11-02. x86 aralığı N (b): Emirhan, 2026-11-16.

---

## KB-15. Fiyat Dönemi ve Fiyat Modları

### Amaç

2026'da bellek ve SSD fiyat şoku var. İki tarafın fiyatları farklı dönemlerden gelirse sonuç fiyat döneminin eseri olur.

### Kaynaklardan

- [PCSP2026-Server] [satıcı] (aktarım): 64 GB DDR5 RDIMM ~$255'ten ~9 ayda ~$1.000'e (Counterpoint aktarımı). Dell 1 Ocak 2026'da standart yapılandırmalara zam yaptı; HPE teklif geçerliliğini 14 güne indirdi.
- [CapCompute-RAM], [Bacloud2026-RAM] (aktarım): Ağustos–Ekim 2026 perakende 64 GB $2.245–3.400.
- [PCSP2026-SSD] [satıcı] (aktarım): 30 TB sınıfı kurumsal NVMe Q3 2025 ~$115/TB, Q3 2026 ~$753/TB (VDURA aktarımı); yeni U.2 NVMe $300–1.172/TB (Ağustos 2026).
- [TrendForce2026-DDR5] (aktarım): sunucu DRAM sözleşme fiyatlarının 2H26–2H27 boyunca artmaya devam etmesi bekleniyor.
- [Gray2005] (aktarım; `benzer_calismalar_v1` B8): fiyat/performans yılda ~%68 değişmiş. Dönem kuralının tarihsel gerekçesi.

**Mainframe fiyat yaşları** (`--price-vintages`): AWLC 2004; TS7700 tabanı 2006; z16 $/PCI, frame tabanı, DS8900F flash listesi, bakım oranları 2022; ücretler 2025; S3/DX/elektrik 2026.

### Kural (E kararı)

- **Ana senaryo `PRICE_EPOCH` = "2025-mid"** (şok öncesi; iki tarafın çapaları aynı dönemde).
- **"2026-Q3" duyarlılık senaryosudur** ve "mainframe fiyatlarının şoka tepkisi bilinmiyor" notuyla raporlanır.
- Bellek ve NVMe her dönemde kendi low/mid/high üçlüsüyle tanımlanır. Dönem anahtarı yalnızca hangi üçlünün kullanılacağını seçer. Ayrı `MEM_USD_PER_GB` / `NVME_USD_PER_TB` aralık parametresi olmaz (tornado'da çift sayım olmasın diye).
- Fiyat tabanı kuralı (KB-09 ile aynı): her bileşen fiyatı önce liste karşılığına çevrilir, indirim bir kez uygulanır. Perakende spot fiyatı OEM indirimiyle birleştirilmez.
- Bileşen fiyat fonksiyonu bir kalibrasyon kontrolüyle doğrulanır: tanımlı bir R760 yapılandırmasının bileşen toplamı, Dell yapılandırıcı liste fiyatına ±%20 içinde yaklaşmalı ([PCSP2026-Server] aktarımı: R760 amiral yapılandırması $53.250 liste; R760xs tabanı $15.957).
- 2004 nominal AWLC otomatik çevrilmez; dönüşüm `SW_PRICE_LEVEL_FACTOR` aralığının işidir.

### Dönem tablosu (değerler `common_model.PRICE_EPOCHS`'ta; üçlüler kodlamada eklenecek)

| Dönem | DRAM $/GB (mid) | NVMe $/TB (mid) | Kaynak |
|---|---|---|---|
| 2025-mid | 4 | 115 | [PCSP2026-Server], [PCSP2026-SSD] |
| 2026-Q3 | 35 | 753 | [CapCompute-RAM], [Bacloud2026-RAM], [PCSP2026-SSD] |

### İki fiyat modu (Emirhan'ın önerisi, 2026-11-02)

(a) Kaynaklı fiyat seti (varsayılan). (b) Kullanıcı fiyat dosyası (`--prices dosya.json`): `PRICE_REGISTRY`'deki adların bir kısmını ya da tamamını geçersiz kılar. Verilen fiyat artık belirsiz sayılmaz ve aralık/tornado'da sabit tutulur. x86 fiyat parametreleri de aynı kayda girer.

### Karar

**E (b), Emirhan, 2026-11-16.** İki fiyat modu: 2026-11-02.

---

## KB-16. Zaman ve Finansman (NPV)

### Kural (`common_model.py` §8; v3 §9.10)

```
NPV = Σ_y [ capex_y / (1 + r)^(y−1) + opex_y / (1 + r)^y ] − kalan değer / (1 + r)^5
seviyelendirilmiş $/TPS-ay = NPV / Σ_y [12 × TPS_y / (1 + r)^y]
```

- 5 yıl; capex yıl başında, opex yıl sonunda; kalan değer 0.
- Kapasite yalnızca yükselir. x86'da yükseltme = düğüm büyütme ya da (RAC'ta) düğüm ekleme.
- Teknoloji yenilemesi (z17 / yeni sunucu nesli) iki tarafta birlikte dışarıda.
- r köşe senaryolarına girmez; ayrı taranır. Yüksek r mainframe'i hep ucuz gösterdiği için "low = mainframe lehine" tanımını bozardı.

### Parametreler ve kaynakları

| Parametre | Değer | Aralık | Dayanak |
|---|---|---|---|
| NPV_DISCOUNT_RATE | 0,07 | tarama %5 / %7 / %10 | [Damodaran2026-WACC] (aktarım): toplam piyasa %6,96; bilgisayar hizmetleri %7,83; yazılım %9,34; bankalar %4,98 |
| NPV_TPS_GROWTH | 0,10 | 0 / 0,05 / 0,10 / 0,20 | Senaryo girdisi |
| SW_PRICE_ESCALATION | 0,03 | 0–0,06 | [Schneider2026-IBMPrice] (aktarım): IBM Z yazılımı 2026'da +%6 |
| HW_SERVICE_ESCALATION | 0,03 | 0–0,06 | [Schneider2026-IBMPrice]: TLS 2025'te +%4–6 |
| WAGE_ESCALATION | 0,033 | 0,025–0,045 | [BLS2026-ECI] (aktarım): özel sektör ücret maliyeti 12 ayda +%3,3 |
| ENERGY_ESCALATION | 0,04 | 0,015–0,056 | [EIA-EPM-5.3] (aktarım): ticari elektrik 10,59 (2020) → 13,37 cent/kWh (2025) |

Mainframe'e özgü: `TFP_GROWTH_PRICE_FACTOR` 0,5 (0,5–1,0); [IBM2021-TFP-Sensible]: "very aggressive Growth Price"; [Kyne2022-TFP]: "IBM mentions 50% discount for growth MSUs". x86 yazılım artışları aynı `SW_PRICE_ESCALATION` sınıfına girer.

---

## KB-17. Enerji ve Tesis

### Kural

- Elektrik fiyatı ortak: `ELECTRICITY_USD_PER_KWH` = 0,12 [ASSUME]; artış KB-16.
- Mainframe: frame başına 30 kW (20–40 kW aralığının ortası) [Alibaba-MFPrice]; storage ve yedek için üretici tepe güçleri.
- x86: düğüm gücü = SPECpower_ssj2008 %100 yük değeri × `X86_POWER_CONFIG_UPLIFT`. Mainframe tepe gücü kullandığı için simetri gereği %100 yük değeri alınır.
- PUE (soğutma), raf alanı ve storage ağı iki tarafta da kapsam dışıdır. AWS S3 hattı istisnadır: seçenek onsuz var olamayacağı için maliyete dahildir.

### Kaynaklardan

[SPECpower-2025Q1] (aktarım), %100 yükte / boşta: HPE DL380 Gen12 924 / 220 W; Lenovo SR650 V4 782 / 218 W; Dell R770 943–960 / 157–164 W. SPECpower sistemleri az bellek ve az diskle ölçülür.

| Parametre | low | mid | high | Dayanak |
|---|---|---|---|---|
| X86_POWER_CONFIG_UPLIFT | 1,1 | 1,25 | 1,4 | [ASSUME]; 512 GB+ bellek, 8–24 NVMe |

---

## KB-18. Belirsizlik ve Çıktı Biçimi

### Kural

- İki taraf aynı yapıda aralık çıktısı verir: her aralık parametresi low/mid/high; köşe senaryoları (hepsi low / hepsi high) ve tek-parametre salınımıyla tornado.
- Sonuç bir **crossover bölgesi** olarak verilir, nokta olarak değil. İki eksen: TPS ve veri hacmi.
- **Ek başlık çıktıları (P kararıyla):**
  1. Başabaş personel oranı (`STAFF_RATIO_X86`'nın başabaş değeri).
  2. Personel hariç TCO.
  3. Personel oranı 1,25 ve 2,0 duyarlılık senaryoları.
- **Diğer ek çıktılar** (`benzer_calismalar_v1` §8):
  - B3: her topolojide DR'ın toplam içindeki payı.
  - B4: 2.200 TPS'te iki tarafın oranı (dış tutarlılık kontrolü, doğruluk iddiası değil).
  - B5: x86 donanım avantajının hangi katmanlarda geri alındığı.
  - B6: TPS ekseni boyunca $/TPS'in testere dişi değişkenliği.
- Uzlaştırma analizi: `X86_UTIL_CEILING`'in %15–20'ye indiği "konsolide edilmemiş park" senaryosunda sonuç IBM'in iddialarına ne kadar yaklaşıyor.
- **Önerilerin yönü dengelidir.** F mainframe lehine olan bir yanlılığı düzeltiyor (mainframe pahalanır). P (eski x86 kuralına göre), C ve N x86 lehine olanları düzeltiyor. U ve E x86 aleyhine olanları düzeltiyor. Bu denge tezde yazılır.

---

## 19. Bu Dokümandan Sonra Yapılacaklar

1. **Mainframe ve ortak modülde uygulanacaklar:**
   - F: `WorkloadProfile`'a nokta/aralık ayrımı, `RANGE_READ_WEIGHT`.
   - E: `PRICE_EPOCH` varsayılanı 2025-mid, dönem başına üçlüler.
   - P: `FTE_ortak(TPS)` ortak modüle taşınır; mainframe personeli sürekli PCI eşdeğerinden hesaplanır; personel hariç TCO çıktısı.
   - Başlığın yeniden hesaplanması, testler, golden snapshot güncellemesi, v3 dokümanının güncellenmesi, log kaydı.
2. **K6 ölçüm protokolü** (KB-03 şartlarıyla); sonuçlar `data/raw/` altına CSV olarak.
3. **`x86_model.py`:** katalog → kapasite köprüsü → latency → topoloji X1–X4 → storage → maliyet → aralık ve tornado → NPV.
4. **Güncel x86 model dokümanı** ve Değerlendirme #9.
5. **Karşılaştırma katmanı:** crossover bölgesi, başabaş personel oranı.

---

## 20. Kaynaklar

> Tam künyeler, erişim tarihleri ve yerel kopyalar: [`kaynaklar/KAYNAKCA.md`](../kaynaklar/KAYNAKCA.md). Bu bölümdeki köşeli parantezli anahtarlar oradaki anahtarlardır (2026-11-24 kaynak düzeltmesi).

Mainframe ve ortak modül kaynaklarının tam listesi `mainframe_model_documentation_v3.md` §11'dedir; x86 kaynaklarının tam listesi `acik_sistem_arastirma_plani_v1.md` §15'tedir. Aşağıda bu dokümanda kullanılanlar ve bu dokümanla eklenenler var.

**Kapasite ve işlem birimi:** [Burgess2016-REDP5320] REDP-5320 · https://www.redbooks.ibm.com/redpapers/pdfs/redp5320.pdf · [Burgess2016-REDP5320] aynı raporun sayaçları, `data/raw/redp5320_workload_profile.csv` · [IBM-LSPR-ITRR] https://www.ibm.com/support/pages/ibm-z-lspr-itrrs · [IBM-LSPR-zOS22] https://www.ibm.com/support/pages/node/6953815 · [Catterall2012] https://robertsdb2blog.blogspot.com/2012/07/db2-for-zos-whats-with-ddf-cpu-time.html · [Catterall2019] https://robertsdb2blog.blogspot.com/2019/01/a-case-study-measuring-impact-of-db2.html · [AmwalAlGhad2017-z14] https://en.amwalalghad.com/?p=62475 · [Vonng-PGPerf] http://blog.vonng.com/en/pg/pg-performence/ · [Tencent-PG-TestMethods] https://tencentcloud.com/document/product/409/62415 · [Tencent-PG-TestResults] https://www.tencentcloud.com/document/product/409/62416 · [Rockdata2026] https://www.rockdata.net/blog/2026-postgres-performance-benchmark-report/ · [Alibaba-PolarDB-PG16] https://help.aliyun.com/en/polardb/polardb-for-postgresql/performance-comparison-with-open-source-postgresql · [SPEC2019-M640-8270] https://spec.org/cpu2017/results/res2019q3/cpu2017-20190708-15958.html · [SPEC2024-R760-6548Y] https://open.spec.org/cpu2017/results/res2024q2/cpu2017-20240422-43001.html · [SPEC2025-DL380G12] https://open.spec.org/cpu2017/results/res2025q1/cpu2017-20250210-46265.html · [Kapila2016-PGCon] https://www.pgcon.org/2016/schedule/attachments/399_postgresql-96-scalability-perf-improvements.pdf · [Oracle-OTNLicense] https://www.oracle.com/downloads/licenses/standard-license.html · [RedHat2025-OCPVDB] https://developers.redhat.com/blog/2025/02/25/scalable-database-performance-openshift-virtualization-out-box · [VMware2024-vSphereOCPV] https://blogs.vmware.com/cloud-foundation/2024/12/03/vmware-vsphere-8-supports-1-5-times-more-vms-and-delivers-62-more-data-transactions-than-red-hat-openshift-virtualization/ · [EDB-LocalPV] https://www.enterprisedb.com/index.php/blog/local-persistent-volumes-and-postgresql-usage-kubernetes

**Availability ve topoloji:** [IBM-SG24-8446] https://www.redbooks.ibm.com/redbooks/pdfs/sg248446.pdf · [IBM-SG24-6374] https://www.redbooks.ibm.com/redbooks/pdfs/sg246374.pdf · [Cook2026-GDPS] https://vmworkshop.org/2026/present/gdpsover.pdf · [IBM-SC28-7025] https://www.ibm.com/docs/en/module_1687296212988/pdf/SC28-7025-00.pdf · [Uptime2025-PR] https://www.datacenterknowledge.com/outages/data-center-outages-decline-for-fourth-straight-year-but-issues-persist · [DCF2022-Uptime] https://www.datacenterfrontier.com/uptime-longer-data-center-outages-are-becoming-more-common · [ITIC2023-IBMZ] https://itic-corp.com/?p=3107 · [TechChannel2024-ITIC] https://techchannel.com/industry-news/server-reliability-survey-2024/ · [Vishwanath2010] https://www.microsoft.com/en-us/research/wp-content/uploads/2010/06/socc088-vishwanath.pdf · [Patroni-ReplModes] https://patroni.readthedocs.io/en/latest/replication_modes.html · [Pigsty-RTO] https://doc.pigsty.io/docs/concept/ha/rto/ · [Oracle2024-RAC] https://oracle.com/a/otn/docs/database/the-new-generation-oracle-rac.pdf · [Oracle2026-MAA] https://oracle.com/a/tech/docs/maa-onpremises-overview.pdf · [YellowBricks2021] https://www.yellow-bricks.com/2021/01/26/how-long-does-it-take-before-a-host-is-declared-failed · [EDB-SyncRep] https://enterprisedb.com/blog/the-varying-cost-synchronous-replication · [StorageReview2022-P5520] https://storagereview.com/wp-content/uploads/2022/07/solidigm-d7-p5520-1.pdf

**Storage, yedek, lisans, fiyat:** [ITJungle2022-Storage] https://www.itjungle.com/2022/05/16/more-price-hikes-from-ibm-now-for-high-end-storage/ · [VendorBenchmark2026-Storage] https://vendorbenchmark.com/blog/enterprise-storage-per-tb-pricing-benchmark · [IBM-Db2z12-Backup] https://www.ibm.com/docs/SSEPEK_12.0.0/admin/src/tpc/db2z_actionstakebackupdata.html · [MinIO-ObjectTCO] https://blog.min.io/the-long-term-costs-of-storage-in-the-cloud · [Nubbo2026-S3] https://nubbo.app/blog/aws-s3-pricing-2026 · [AWS-DXPricing] https://aws.amazon.com/directconnect/pricing/pay-as-you-go/ · [Oracle2026-CoreFactor] https://www.oracle.com/contracts/docs/processor-core-factor-table-070634.pdf · [Oracle-Partitioning] https://oracle.com/a/ocom/docs/it-infrastructure/partitioning-070609.pdf · [Redress2026-OraclePL] https://redresscompliance.com/oracle-price-list-2026-key-changes-and-analysis.html · [AceMQ-VVFvsVCF] https://acemq.com/blogs/vmware-cloud-foundation-vs-vsphere-foundation/ · [AceMQ2026-Renewals] https://acemq.com/research/state-of-vmware-renewals-2026/ · [PCSP2026-Server] https://pcserverandparts.com/news/how-much-does-a-server-cost-2026/ · [PCSP2026-SSD] https://pcserverandparts.com/news/enterprise-ssd-prices-2026-server-storage-buying-guide/ · [CapCompute-RAM] https://capitalandcompute.net/memory-prices/server/ · [Bacloud2026-RAM] https://www.bacloud.com/en/blog/307/when-will-ram-prices-drop-still-no-good-news--august-2026-update.html · [TrendForce2026-DDR5] https://www.trendforce.com/news/2026/08/17/news-germany-ddr5-prices-near-5x-yoy-in-august-china-reportedly-sees-14-wow-jump-as-global-rally-continues/ · [SPECpower-2025Q1] https://spec.cs.miami.edu/power_ssj2008/results/res2025q1

**NPV:** [Damodaran2026-WACC] https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html · [Schneider2026-IBMPrice] https://www.schneider.im/lu/ibm-price-increases-2026/ · [BLS2026-ECI] https://www.bls.gov/news.release/archives/eci_07312026.htm · [EIA-EPM-5.3] https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_3 · [Kyne2022-TFP] https://tuningletter.planetmainframe.com/wp-content/uploads/presentations/2022-08-102-How-Should-I-Think-About-Tailored-Fit-Pricing.pdf

**Personel (bu dokümanla eklenen ya da yeniden okunanlar):**
- **[IBM-CPO2014-Skills]** [VENDOR] IBM Competitive Project Office, "Mainframe Skills – The Myth and the Reality" v3 (2014): "5 FTE to start + 1 FTE for every 625 MIPS"; Solitaire Interglobal 2013 aktarımı "as much as 13x smaller". https://public.dhe.ibm.com/software/os/systemz/pdf/Mainframe_skills_-_The_myths_and_the_reality_v3.pdf
- **[CA2016-MFEcosystem]** Gartner IT Key Metrics Data 2016, Broadcom aktarımı: 152 → 268 MIPS/FTE. https://docs.broadcom.com/doc/why-the-mainframe-should-be-part-of-your-digital-business-ecosystem
- **[Rhoderick2007-TPFUG]** [VENDOR] IBM, "A Fresh Look at the Mainframe: Mainframe Total Cost of Ownership Issues" (TPFUG 2007): SWG veri merkezi, Omaha, Baldor, örnek model. https://public.dhe.ibm.com/software/htp/tpf/tpfug/tgs07/tgs07e.pdf
- **[Calderon2011-Labor]** [VENDOR] IBM, "Reducing IT labor costs" (2011): 30,7 sunucu/FTE, 52,5 VM/FTE, 32 / 36 saat, 500 iş yükü senaryosu, $159.600/FTE. https://public.dhe.ibm.com/software/os/systemz/summit/handouts/Session_3_Reducing_IT_labor_costs_Q2.pdf
- **[Shedletsky2008]** [VENDOR] J. Shedletsky, "Mainframe versus Distributed TCO Studies and Experiences": 7,8 sunucu/headcount; Québec vakası. https://public.dhe.ibm.com/software/zseries/pdf/sandiego/Mainframe_versus_Distributed_TCO_Studies_and_Experiences_-_John_Shedletsky.pdf
- **[Jones2007-TCO]** [VENDOR] R. Jones, "Leveraging your Mainframe Investment: TCO Considerations" (2007): "167-625 MIPS per headcount (500 is typical)"; IGS Linux vakası. https://public.dhe.ibm.com/software/systemz/pdf/datacenter/10_-_Ray_Jones_-_Leveraging_your_Mainframe_Investment_-TCO_Considerations.pdf
- **[IBM2012-TCOLessons-zEC]** [VENDOR] IBM CPO, "TCO Lessons Learned From Customer Engagements": DR testi 14.952 vs 2.051 kişi-saat. https://public.dhe.ibm.com/software/os/systemz/seminars/mainframe/handouts/Session_5_-_Tales_from_the_Eagle_TCO_team.pdf
- **[IBM2013-TCOLessons]** [VENDOR] Üretim dışı +%20 / +%200. https://public.dhe.ibm.com/software/os/systemz/pdf/TCO_lessons_from_customer_engagements_v4.pdf
- **[Computerworld-IDC2007]** IDC, "Key IT and Business Benchmarks for Managing Virtual Infrastructure" (Elliot, Villars), Computerworld aktarımı (5 Aralık 2007): 200 VM/yönetici. https://www.computerworld.com/article/1567236/benchmarking-how-well-you-manage-virtualization.html
- **[Avasant2008-Headcount]** Computer Economics / Avasant, "Server Support Headcounts Hold Steady": medyan %6,8 (2008), %6,6 (2006). https://avasant.com/report/server-support-headcounts-hold-steady/
- **[Astadia2024-ROI]** [göç satıcısı] Astadia, "Mainframe Modernization: A Guide to Calculating ROI" (2024): personel sayısı vermiyor. https://www.amdocs.com/sites/default/files/2024-11/astadia-roi-calculator-11-2024.pdf
- **[BLS-OOH]**, **[BLS2026-ECEC]**, **[IDC2016-ConnectedMF]**: v3 §11.7.
