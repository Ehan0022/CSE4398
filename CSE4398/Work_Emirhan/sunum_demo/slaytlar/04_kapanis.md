# Slayt İçeriği — Bölüm 4: Kapanış (3 slayt)

---

### Slayt S1 — Bulgular

- Mid varsayımlarla ve nötr personelle kümelenmiş x86 bütün hacimlerde ~2 kat ucuz (10K TPS: $53,66 vs $113,93/TPS/ay).
- **Başabaş personel oranı 2,0 – 3,6:** x86 personeli aynı iş için mainframe personelinin bu katından azsa x86 kazanır (IBM vakaları 1,23 – 3,28).
- **Personel hariç fark 8 – 42 kat;** kaynağı neredeyse bütünüyle yazılım lisans modeli (AWLC vs açık kaynak). Personelden ayrı yazılması gereken yapısal bulgu.
- Mainframe'in kazandığı bölge: (a) personel oranı ~2'yi aşarsa, ya da (b) platforma özgü bütün belirsizlikler mainframe lehine çözülür ve yük 15–36K TPS'lik Patroni tavanını aşarsa (eşleştirilmiş senaryoda 30K–50K TPS'te başabaş 0,78 / 0,68).
- İkinci eksen veri hacmi: 500 TB'ta mainframe storage + yedek toplamın %16,5'i; x86'da veritabanı seçimini değiştirir.
- Mainframe maliyet eğrisi düz değil, bükülüyor (1K → 50K TPS'te $/TPS ~4,2 kat düşer).

**Veri / kaynak:** Demo Case 1, 2, 5, 9, 10; x86 dokümanı §16; Değerlendirme #9.

**Tasarım gerekçesi:** Sonuç bir nokta değil bölge olarak ve hangi varsayıma koşullu olduğuyla birlikte verilir (KB-18).

**Konuşmacı notu:** "Tek cümleyle: mainframe pahalı değil, mainframe'in yazılım lisansı pahalı; ve personel konusunda ne varsaydığınıza göre sonuç değişebilir. Bu ikisini ayırarak gösteren bir araç kurduk."

---

### Slayt S2 — Geçerlilik tehditleri ve sınırlılıklar

| Tehdit | Etki | Durum |
|---|---|---|
| x86 kapasite çapası tek, belgelenmemiş ayarlı (Vonng) | Köprü 60–120 aralığında | K6 ölçümüyle kapanacak |
| Personel nötr; bağımsız platformlar arası personel verisi yok | Başlık personel oranına koşullu | Başabaş oranı başlık çıktısı |
| AWLC L4+ fiyatları ve SW fiyat seviyesi yayımlanmıyor | Tornado'da 2. sıra | Gerçek teklifle `--prices` |
| Okuma SQL CPU maliyeti (Db2/z16) varsayım | Tornado'da 1. sıra | SMF 101 accounting kaydı |
| Oracle verimi kalibre edilemez (OTN yasağı) | > ~36K TPS'te geniş aralık | Yapısal veri sınırı |
| Planlı kesinti sıklığı iki tarafta kaynaksız | En etkili availability varsayımı | Gerçek değişiklik kaydı |
| **Kapsam dışı:** MQ (iki taraf), **z16 A02 rack-mount**, **Parallel Sysplex** / Citus, z17 yenilemesi, PUE | Düşük TPS'te mainframe tabanı (A02); yüksek TPS'te tavanlar | Bilinçli kapsam, simetrik |
| Üretici kaynaklı veri (IBM, Oracle, Red Hat, VMware) | Yanlılık | [VENDOR] etiketi, geniş aralık |

**Veri / kaynak:** v3 §12; x86 dokümanı §18; değerlendirmeler #1–#9.

**Tasarım gerekçesi:** Her tehdit etkisi ve kapatma yoluyla yazılır; okuyucu hangi sonucun hangi varsayıma dayandığını görür.

**Konuşmacı notu:** "Bu tabloyu her değerlendirmede güncelliyoruz; dokuz değerlendirme boyunca kapanan tehditler log'da tek tek işaretli."

---

### Slayt S3 — Sonraki adımlar

1. **K6 sysbench ölçümü** (KB-03 protokolüyle): x86 çapası, `RANGE_READ_WEIGHT`, Patroni X2 RPO ve WAL fsync kalibrasyonu.
2. **`docs/kopruler_v2.md`:** kodlamadaki dört düzeltme (KB-06, 08, 11, 15) ve iki yeni kural (eşleştirilmiş senaryolar, NPV'de yol-feasibility).
3. RAC ölçeklenmesi için USL biçiminde kaynak.
4. Sunucu fiyatı için yapılandırması belli kamu ihale kaydı (KB-15 ±%20 kontrolü).
5. Mainframe: drawer maliyeti, GDPS Metro topolojisi, planlı kesinti kalibrasyonu, L4+ AWLC fiyatları.
6. Crossover haritasının grafikleri (TPS × veri hacmi × personel oranı).

**Veri / kaynak:** PROJECT_LOG.md "Açık kalanlar"; Değerlendirme #9.

**Tasarım gerekçesi:** Sıralama tornado'ya göre: sonucu en çok daraltacak veri önce.

**Konuşmacı notu:** "Model yapısal olarak tamam; kalan işler aralıkları daraltacak ölçüm ve veri toplama. Yapı değişmeyecek, sayılar netleşecek."
