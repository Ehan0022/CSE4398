# Değerlendirme #10 — Mainframe Neden Kazanmıyor? Availability Eşitliği ve Kazanan Bölgeler

*Tarih: 2026-11-24 · Tetikleyen: Emirhan'ın sorusu ("çıktılarda mainframe'in kazandığı bir durum yok mu? bu saçma değil mi?") ve onun devamı ("availability hedefleri yükseldikçe mainframe'in avantajlı olmasını beklemez miyiz? desteksiz açık kaynak yüksek standartlı inputları karşılayamaz mı?") · İncelenen: `src/mainframe_model.py`, `src/x86_model.py`, `src/common_model.py`, `sunum_demo/` çıktıları · Testler: mainframe 30/30, x86 29/29 (5 yeni)*

Önem dereceleri #8 ile aynıdır: **Kritik** = düzeltilmezse crossover'ın yerini tek başına belirleyebilir · **Önemli** = sonucu ölçülebilir biçimde kaydırır ya da savunmada zayıf nokta olur · **Küçük** = metin ya da tutarlılık düzeltmesi. Orijinal tasarım dokümanları düzenlenmedi.

---

## 1. Kısa Sonuç

1. **Ana senaryoda mainframe'in hiç kazanmaması bir hata değil, kurgunun sonucudur.** 10K TPS'te fark tamamen personel dışıdır: mainframe $618K, x86 $15K. Yazılım (AWLC) farkın %66'sı, üretim dışı ortamlar %16'sı, donanım + bakım %16'sı. Personel iki tarafta aynı olduğundan başabaş personel oranı kapalı biçimde `1 + ΔPersonelDışı / personel` olur ve her TPS'te ~2 civarında kalır (1K: 2,54; 10K: 2,07; 50K: 1,97).
2. **Ama üç gerçek asimetri vardı ve üçü de x86 lehineydi.** (a) M3'ün kurtarma süresi GDPS'in tek siteli iş yükü değeriydi (30 dk), karşılığı olan X3'ünki ise iki sitede etkin küme değeri (2 dk). (b) Platform (sunucu) kesintisi mainframe'de ITIC'ten geliyordu, x86'da hiç sayılmıyordu; geçişin her zaman başarılı olduğu varsayılıyordu. (c) Ortak personel eğrisinin girdisi zIIP'e kayan işi dışarıda bırakıyordu. Üçü de düzeltildi (§3).
3. **Düzeltmelerden sonra availability ekseninde gerçek bir kazanan bölge var.** %99,999 + RPO 0 ve %99,9995'te, 1K–100K TPS'in hepsinde yalnızca mainframe (M3) kurulabiliyor. RPO serbestken x86 Oracle Platinum (X4, RPO 5 sn) ile kurulur ve ucuzdur. Bu sınır geçişin maskeleyemediği pay u'ya hassastır: u = 0,05'te x86 X3 ile yeniden kurulur. Sonuç koşullu raporlanmalıdır.
4. **Maliyet ekseninde kazanan bölge zaten vardı ama demoda görünmüyordu.** Eşleştirilmiş "mainframe_lehine" senaryoda 30K TPS'ten itibaren mainframe ucuzdur (30K: oran 0,86; 50K: 0,81) ve 100K'da x86 kurulamaz. Personel oranı başabaşın üstündeyse (Case 9'da 3,0) mainframe her yerde kazanır. Demo yalnızca orta değerlerle ve `--range`'i yalnızca 10K'da koşturuyordu. Case 11 ve 12 bu bölgeleri gösterir.
5. **Desteksiz açık kaynak artık serbest değil.** %99,99 ve üstünde ya da RPO 0'da 7/24 ticari destek zorunlu ($1.600/çekirdek/yıl), %99,999'da Enterprise ($2.400). Desteksiz yığın yalnız düşük hedeflerde seçilebilir ve availability'si ITIC'in üst ucundan sayılır. Maliyet etkisi küçüktür (10K'da ayda $5–13K).
6. **Ana senaryo başlığı değişti ama yönü değişmedi:** mainframe $113,93 → $117,92/TPS/ay, x86 $53,66 → $57,65, başabaş 2,16 → 2,07 (personel 38,6 → 41,6 FTE, zIIP düzeltmesi).

---

## 2. Değerlendirme #9'dan Kapanan ve Açık Kalan Tehditler

| #9 tehdidi | Durum | Nasıl |
|---|---|---|
| §3.1 Sonucu personel oranı belirliyor (Kritik, bilinçli) | **Açık, şimdi kapalı biçimde açıklanıyor** | Başabaş formülü v3 §7.12.1; P kararı değişmedi. Kazanan haritası (§4) personel dışı eksenlerdeki kazanan bölgeleri ayrıca gösteriyor |
| §3.2 Yazılım lisans modeli yapısal farkın kaynağı | **Açık, nicelendi** | Fark ayrıştırması v3 §7.12.1 (%66 yazılım). Db2 DDF yığını denendi, eklenmedi (§5) |
| §1.5 Crossover bölgesi dar ve koşullu | **Kapandı (görünür kılındı)** | `src/tools/kazanan_haritasi.py`, demo Case 11–12 |
| #8 yeni: tavan üstünde RAC'ın kalibre edilemeyen parametreleri | **Açık** | Maliyet eksenindeki kazanan bölge tam olarak bu parametrelere bağlı (RAC verimi 0,8, Oracle verimi 0,8) |
| §2.2 Kapasite çapası (K6) | **Açık** | Etkisi küçük: x86 donanımı 10K'da ayda ~$1,2K |
| Availability: x86 düğüm arızası yalnızca donanım × failover | **Kapandı (yeni, A)** | Ortak platform kesintisi terimi (§3.2) |

---

## 3. Bulgular ve Düzeltmeler

### 3.1. M3 ile X3 arasında kurtarma süresi asimetrisi (Önemli → düzeltildi)

GDPS'in kaynağı [GDPS-2026] Metro için iki değer verir: çok siteli iş yükünde ~2 dk, tek siteli iş yükünde 1 saatin altı. Model M3'e tek siteli değeri (2 / 30 / 60 dk) vermişti. x86 X3 ise iki sitede 2 + 2 düğümlü, otomatik geçişli etkin bir kümedir ve 1 / 2 / 5 dk alıyordu. Bunun sonucu, %99,999 + RPO 0 + RTO ≤ 30 dk hedefinde x86'nın kurulabilirken mainframe'in kurulamamasıydı. Bu teknoloji farkı değil, tanım farkıdır.

**Düzeltme:** M3 çok siteli iş yükü olarak tanımlandı (sysplex iki siteye yayılır, HyperSwap): kurtarma 1 / 2 / 5 dk, planlı geçiş 0,5 / 2 / 10 dk (X3–X4 ile aynı aralık). İkinci sitedeki düşük kapasiteli etkin imajların küçük MSU faturası CBU kuralındaki gibi ihmal edilir (sınırlama). Etki: M3 availability'si %99,998'den %99,9998'e çıktı; %99,999'da mid seçim M4'ten M3'e geçti (10K'da $1,49M → $1,38M).

### 3.2. Platform kesintisi yalnız bir tarafta sayılıyordu (Kritik → düzeltildi)

Mainframe tarafı CPC kesintisini ITIC'ten alıyordu (z16: yılda 31,56 ms). x86 tarafı yalnızca donanım arızası sıklığı × failover süresini sayıyordu (yılda 0,1 olay × 35 sn ≈ 3,5 sn). Sunucunun kendi kesintisi (işletim sistemi, sürücü, yapılandırma) ve geçişin başarısız olduğu durumlar hiç yoktu. ITIC 2023'e göre x86 Linux sunucularında yıllık plansız kesinti Lenovo 31,5 sn, Dell PowerEdge 24 dk, HPE ProLiant 39 dk, white box 59 dk'dır. Kesinti nedenleri arasında güvenlik (%84) ve insan hatası (%67, yanlış yapılandırma dahil) başı çeker. Uptime 2025'e göre etkili kesintilerin %23'ü BT ve ağ kaynaklıdır ve büyük BT/yazılım kesintilerinin %62'sinde konfigürasyon ya da değişiklik yönetimi vardır. Akademik literatür, kurtarma yolunun kendisinin baskın hata kaynağı olduğunu gösterir: Yuan vd. (OSDI 2014) katastrofik hataların %92'sini hata işleme yolunda bulur; Gunawi vd. (SoCC 2016) yüzlerce bulut kesintisinde geçiş mekanizmalarının hata ürettiğini raporlar.

**Düzeltme (A kararı):** iki tarafta aynı formül ve aynı kaynak:

```
D_platform = N_kesen × ITIC_sunucu × u^katman
  tek CPC (M1): u = 1;  küme (M2, M3, X1–X3): u;  aktif-aktif iki site (M4, X4): u²
  u = PLATFORM_UNMASKED_SHARE, ortak, 0,05 / 0,10 / 0,20 [ASSUME]
  x86 ITIC_sunucu = 0,5 / 24 / 59 dk (Lenovo / Dell / white box), z16 = 0,03 / 0,3 / 3 sn
```

Geçişle maskelenen pay (1 − u) önceki gibi düğüm olayı × failover süresiyle sayılır. Etki: X3 Patroni 4,4'ten 6,7 dk/yıla çıktı ve %99,999'un (5,26 dk) altına düştü. X1 %99,98275'ten %99,98230'a indi (ana senaryoda etkisiz).

**Tehdit (Önemli, açık):** ITIC kendi seçilen katılımcılarla yapılan bir web ankettir ve bağımsız doğrulaması yoktur. u kaynakla daraltılamadı. Sınır u'ya hassastır: 10K TPS'te %99,999 + RPO 0'ı x86 u = 0 ve 0,05'te sağlar, u = 0,10 ve 0,20'de sağlayamaz. Tez sonucu "u ≥ ~0,1 ise beş dokuz + RPO 0 yalnızca mainframe'de" biçiminde yazılmalıdır. u'yu daraltacak bir kaynak (ör. otomatik failover başarı oranı üzerine bir saha çalışması) en değerli eksik veridir.

### 3.3. Desteksiz açık kaynak (Önemli → modellendi)

Emirhan'ın sorusu: desteksiz, ücretsiz bir açık kaynak yığın yüksek standartlı girdileri karşılayabilir mi? Model PostgreSQL desteğini 0 / 500 / 1.500 $/çekirdek/yıl aralığıyla taşıyordu ve SLA'dan bağımsızdı. EDB mağaza fiyatları: Community $400, Business $1.600, Enterprise $2.400; destek seviyeleri Basic 10x5 (yalnız geliştirme/test), Production 7/24, Premium 7/24 + sıkı SLO.

**Düzeltme (B kararı):** hedef ≥ %99,99 ya da RPO 0 ise en az $1.600, ≥ %99,999 ise $2.400 tabanı; desteksiz (0) yalnız altında seçilebilir ve o durumda platform kesintisi ITIC'in high ucundan sayılır (eşikler [ASSUME]). Etki küçüktür: 10K TPS'te %99,99'da ayda ~+$7K, %99,999'da (Oracle X4 seçildiği için) sıfır. Desteğin asıl rolü maliyet değil, hangi hedefe hangi yığınla çıkılabileceğidir. Düzenleyici boyut (AB DORA'nın kritik fonksiyonlarda sözleşmeli ICT tedarikçisi beklentisi gibi) nitel olarak yazılır.

### 3.4. Personel eğrisinin girdisinde zIIP (Küçük → düzeltildi)

Ortak personel eğrisinin girdisi `TPS × w × (1 − f) / TPS_PER_PCI / 0,9` idi. zIIP'e kayan iş de yönetilen iştir; (1 − f) çarpanı x86 personelini bir mainframe faturalama ayrıntısına bağlıyordu (zIIP payı artınca x86 personeli de azalıyordu). Düzeltme: girdi toplam CPU işidir. Etki: 10K TPS'te 38,6 → 41,6 FTE, iki tarafta aynı.

### 3.5. Kesinti maliyeti TCO'da yok (Küçük, sınırlama)

Availability yalnızca kısıttır. Saat başı $500K kesinti maliyetinde bile M4 ile X3 arasındaki ~4 dk/yıl fark ayda ~$3K eder; ana senaryoda X1 zaten M1'den daha erişilebilirdir. Kesinti maliyeti terimi sonucu değiştirmez ve eklenmedi.

---

## 4. Kim Nerede Kazanıyor

`python src/tools/kazanan_haritasi.py` (hücre: kazanan, MF/x86 oranı / başabaş personel oranı):

| Hedef, orta senaryo | 1K | 10K | 50K | 100K |
|---|---|---|---|---|
| %99,9 | x86 2,36 / 2,54 | x86 2,05 / 2,07 | x86 1,89 / 1,97 | x86 1,99 / 2,09 |
| %99,99 + RPO 0 | x86 2,11 / 2,33 | x86 1,93 / 2,04 | x86 1,89 / 2,00 | x86 1,98 / 2,13 |
| %99,999 | x86 1,70 / 2,17 | x86 1,73 / 1,84 | x86 1,66 / 1,76 | x86 1,72 / 1,84 |
| %99,999 + RPO 0 | yalnız MF | yalnız MF | yalnız MF | yalnız MF |
| %99,9995 | yalnız MF | yalnız MF | yalnız MF | yalnız MF |

| Hedef, mainframe_lehine | 1K | 10K | 30K | 50K | 100K |
|---|---|---|---|---|---|
| %99,9 | x86 1,20 / 1,26 | x86 1,20 / 1,22 | **MF 0,86 / 0,80** | **MF 0,81 / 0,70** | yalnız MF |
| %99,99 | x86 1,13 / 1,17 | x86 1,11 / 1,12 | **MF 0,68 / 0,44** | **MF 0,59 / 0,28** | yalnız MF |
| %99,999 | yalnız MF | yalnız MF | yalnız MF | yalnız MF | yalnız MF |

Özet: mainframe (a) %99,999 + RPO 0 ve üstünde (u ≥ ~0,1 koşuluyla), (b) ≥ 30K TPS'te platforma özgü belirsizlikler mainframe lehine çözüldüğünde, (c) x86 personeli mainframe personelinin ~2 katını aştığında kazanır. Bunların dışında, kurulabildiği her yerde x86 ~2 kat ucuzdur. Bu tablo, IBM Eagle'ın "dağıtık 2,2 kat pahalı" bulgusunun hangi koşullarda (personel, ticari kümeleme, beş dokuz + RPO 0) bu modelle uzlaştığını gösterir.

---

## 5. Yapılmayan ve Açık Kalanlar

- **Db2 DDF + dağıtık uygulama katmanı yığını** (CICS yok, zIIP %40–60): mainframe tek yığınla, x86 sekiz yığınla aranıyor. Deneme: mainframe toplamı ~%30 düşer, başabaş ~2,0'a iner (personel de birlikte düştüğü için). Emirhan'ın kararıyla eklenmedi; açık sınırlama.
- **u'nun kalibrasyonu** (§3.2): en değerli eksik veri.
- **İkinci sitedeki etkin z/OS imajlarının MSU faturası** (M3 çok siteli iş yükü): ihmal edildi.
- **Konsolidasyon, göç maliyeti, Parallel Sysplex data sharing, Linux on Z:** mainframe lehine olup kapsam dışı; tezde sınırlama olarak yazılmalı.
- **`kopruler_v2.md`:** #9'un dört düzeltmesine ek olarak KB-07/KB-08'e platform kesintisi terimi ve M3 eşitliği eklenmeli.
