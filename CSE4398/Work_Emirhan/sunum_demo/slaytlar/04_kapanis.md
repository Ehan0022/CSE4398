# Slayt İçeriği — Bölüm 4: Kapanış (4 slayt)

---

### Slayt S0 — Demo case özetleri: iki tarafın en ucuz feasible yapılandırması

| Case | Girdi | Mainframe | x86 |
|---|---|---|---|
| 1 | 10K TPS, %99,9 (referans) | M1 3931-524 · $117,92 | X1 vSphere/VM/PG, 3 × 2×8c · $57,65 |
| 2 | 1K / 50K TPS | 3931-407 · $299,85 / 3931-759 · $71,35 | PG 3 × 2×8c · $126,94 / Oracle 7 × 2×8c · $37,71 |
| 3 | p99 ≤ 10 ms | M1 3931-714 · $123,02 | X1 Oracle, 8 × 2×8c · $73,54 |
| 4 | %99,999 | M3 3931-524 · $138,35 | X4 Oracle aktif-aktif, 4 × 2×8c · $79,77 |
| 5 | 500 TB veri | M1 3931-524 · $142,39 | X1 Oracle + AFA, 2 × 2×8c · $65,47 |
| 6 | oltp_heavy iş yükü | M1 3931-532 · $137,57 | X1 PG, 3 × 2×12c · $68,17 |
| 7 | 100 TB, TS7770 zorla | M1 3931-524 · $122,34 | X1 PG, 3 × 2×8c · $58,10 |
| 8 | retail_bursty (yıllık, ort. 10K) | base 3931-717, TFP (C) · $253,55 | X1 PG, 3 × 2×32c (tepeye göre) · $137,58 |
| 9 | personel oranı 3,0 | M1 3931-524 · $117,92 | X1 PG, 3 × 2×8c · $169,89 |
| 10 | NPV / aralık (mid) | M1 3931-524 · $117,92 | X1 PG, 3 × 2×8c · $57,65 |
| 11 | %99,999 + RPO 0 | M3 3931-524 · $138,35 | **kurulamaz** |
| 12 | 50K TPS, personel oranı 2,5 | M1 3931-759 · $71,35 | X1 Oracle, 7 × 2×8c · $89,66 |

Değerler aylık $/TPS. Her case çıktısı bu biçimde biter (`ciktilar/case_NN_*.txt` sonundaki CASE ÖZETİ; her koşunun son satırları `OZET | taraf | yapılandırma | aylık | $/TPS`).

**Veri / kaynak:** `python sunum_demo/demo_calistir.py` (51 komut, 2026-11-24); `src/ozet.py`.

**Tasarım gerekçesi:** Her koşu iki tarafı aynı girdiyle çözer ve yalnızca kazanan yapılandırmayı ve maliyetini özetler; ayrıntı (döküm, aralık, NPV) koşunun yukarısındadır. Yalnızca mainframe komutu olan case'lerde de x86 tarafı hesaplanır, böylece her satır bir karşılaştırmadır.

**Konuşmacı notu:** "Bu tablo bütün demonun tek sayfalık hali: hangi girdide hangi yapılandırma ve kaça. Kalın hücre, x86'nın bu hedefi hiç kuramadığı yer."

---

### Slayt S1 — Bulgular

- Mid varsayımlarla ve nötr personelle kümelenmiş x86, kurulabildiği her noktada ~2 kat ucuz (10K TPS: $57,65 vs $117,92/TPS/ay).
- **Başabaş personel oranı 1,8 – 2,5:** x86 personeli aynı iş için mainframe personelinin bu katından azsa x86 kazanır (IBM vakaları 1,23 – 3,28).
- **Personel hariç fark 8 – 41 kat;** kaynağı neredeyse bütünüyle yazılım lisans modeli (AWLC vs açık kaynak). Personelden ayrı yazılması gereken yapısal bulgu.
- Mainframe'in kazandığı üç bölge (Değ #10): (a) **%99,999 + RPO 0 ve %99,9995'te yalnızca mainframe kurulabilir** (her TPS'te; sınır maskelenemeyen platform payı u'ya duyarlı, u = 0,05'te x86 Oracle ile kurulur); (b) platforma özgü bütün belirsizlikler mainframe lehine çözülür ve yük 30K TPS'i aşarsa (oran 0,86 / 0,81); (c) personel oranı başabaşı (~2) aşarsa.
- Desteksiz açık kaynak yalnızca alt hedeflerde mümkün: %99,99 / RPO 0 üstünde zorunlu destek kademesi ($1.600 – $2.400/çekirdek/yıl, EDB) uygulanır.
- İkinci eksen veri hacmi: 500 TB'ta mainframe storage + yedek toplamın %16,1'i; x86'da veritabanı seçimini değiştirir.
- Mainframe maliyet eğrisi düz değil, bükülüyor (1K → 50K TPS'te $/TPS ~4,2 kat düşer).

**Veri / kaynak:** Demo Case 1, 2, 4, 5, 9, 10, 11, 12; x86 dokümanı §16; Değerlendirme #9, #10; `src/tools/kazanan_haritasi.py`.

**Tasarım gerekçesi:** Sonuç bir nokta değil bölge olarak ve hangi varsayıma koşullu olduğuyla birlikte verilir (KB-18).

**Konuşmacı notu:** "Tek cümleyle: mainframe pahalı değil, mainframe'in yazılım lisansı pahalı; personel konusunda ne varsaydığınıza göre sonuç değişebilir; ve availability'nin en üst ucunda kurulabilen tek platform mainframe. Bunları ayırarak gösteren bir araç kurduk."

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
| Maskelenemeyen platform payı u varsayım (0,05 – 0,20) | %99,999 + RPO 0 sınırı u'ya duyarlı | Saha kesinti kayıtları (Değ #10) |
| Db2 DDF (dağıtık erişim) yığını yok | Mainframe yalnızca CICS + Db2 ile | Değ #10'da bilinçli olarak dışarıda |
| **Kapsam dışı:** MQ (iki taraf), **z16 A02 rack-mount**, **Parallel Sysplex** / Citus, z17 yenilemesi, PUE | Düşük TPS'te mainframe tabanı (A02); yüksek TPS'te tavanlar | Bilinçli kapsam, simetrik |
| Üretici kaynaklı veri (IBM, Oracle, Red Hat, VMware) | Yanlılık | [VENDOR] etiketi, geniş aralık |

**Veri / kaynak:** v3 §12; x86 dokümanı §18; değerlendirmeler #1–#10.

**Tasarım gerekçesi:** Her tehdit etkisi ve kapatma yoluyla yazılır; okuyucu hangi sonucun hangi varsayıma dayandığını görür.

**Konuşmacı notu:** "Bu tabloyu her değerlendirmede güncelliyoruz; dokuz değerlendirme boyunca kapanan tehditler log'da tek tek işaretli."

---

### Slayt S3 — Sonraki adımlar

1. **K6 sysbench ölçümü** (KB-03 protokolüyle): x86 çapası, `RANGE_READ_WEIGHT`, Patroni X2 RPO ve WAL fsync kalibrasyonu.
2. **`docs/kopruler_v2.md`:** kodlamadaki dört düzeltme (KB-06, 08, 11, 15) ve iki yeni kural (eşleştirilmiş senaryolar, NPV'de yol-feasibility).
3. RAC ölçeklenmesi için USL biçiminde kaynak.
4. Sunucu fiyatı için yapılandırması belli kamu ihale kaydı (KB-15 ±%20 kontrolü).
5. Mainframe: drawer maliyeti, GDPS Metro topolojisi, planlı kesinti kalibrasyonu, L4+ AWLC fiyatları.
6. Crossover haritasının grafikleri (TPS × veri hacmi × personel oranı; availability ekseni `kazanan_haritasi.py` ile tablo olarak var).
7. u (maskelenemeyen platform payı) için saha verisi.

**Veri / kaynak:** PROJECT_LOG.md "Açık kalanlar"; Değerlendirme #9, #10.

**Tasarım gerekçesi:** Sıralama tornado'ya göre: sonucu en çok daraltacak veri önce.

**Konuşmacı notu:** "Model yapısal olarak tamam; kalan işler aralıkları daraltacak ölçüm ve veri toplama. Yapı değişmeyecek, sayılar netleşecek."
