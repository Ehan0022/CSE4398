# kaynaklar/

Projede atıf yapılan bütün dış kaynakların kataloğu ve (indirilebilenlerin) tam kopyaları. Oluşturma: 2026-11-24.

## İçerik

| Dosya | Ne |
|---|---|
| `KAYNAKCA.md` | Akademik kaynakça: yazar, başlık, yayıncı, yıl, URL, erişim tarihi, yerel kopya, saklanamama nedeni. Türe göre gruplu. |
| `kaynaklar.bib` | Aynı liste BibTeX olarak (tez şablonuna aktarmak için). |
| `kaynak_katalogu.csv` | Makine okunur katalog: anahtar, eski etiketler, durum, dosya adları, bayt, SHA-256 (ilk 16 hane). |
| `ETIKET_ESLEME.md` | Eski kendi uydurduğumuz etiketlerden (ör. `[IBM-EAGLE-2013]`, `[REDP]`) yeni anahtarlara eşleme. |
| `dosyalar/` | Tam dokümanlar: `<Anahtar>.pdf` (orijinal PDF), `<Anahtar>.html` (sayfanın HTML'i), `<Anahtar>.snapshot.pdf` (sayfanın tarayıcıda basılmış hali). Birden çok URL'li kaynaklarda `__2`, `__3` eki. |

## Anahtar kuralı

`YazarYıl-kısaAd` (ör. `Yuan2014`, `Shedletsky2008`, `Cook2026-GDPS`); resmî form numarası olan IBM yayınlarında form numarası (ör. `IBM-SG24-8446`, `IBM-SC28-7025`). Anahtar bir kez verildikten sonra değişmez; yeni kaynak yeni anahtar alır.

## Saklama yeri

Repo **herkese açık** olduğu için telifli üçüncü taraf dokümanlar (`dosyalar/`) git'e girmez (`.gitignore`). Kopyaları:

- Proje dosyaları: `/mnt/project-files/kaynaklar/dosyalar/`
- Emirhan'ın bilgisayarı: `Desktop\CSE4398\CSE4398\Work_Emirhan\kaynaklar\dosyalar\` (yerel repo içinde, `.gitignore` ile git dışı)

Bütünlük `kaynak_katalogu.csv`'deki SHA-256 değerleriyle kontrol edilir.

## Kullanım kuralı

- Yeni bir değer bir kaynaktan alındığında önce dokümanı `dosyalar/`'a indir, katalogda satır aç, metinde anahtarla atıf yap.
- Değerlendirmeler (`evaluations/`), `PROJECT_LOG.md`, orijinal tasarım dokümanları ve kod yorumları eski etiketleri tarihsel kayıt olarak taşır; karşılıkları `ETIKET_ESLEME.md`'dedir.
- Saklanamayan kaynaklar için neden katalogda yazılıdır (bot koruması, paywall, kayıt zorunluluğu, sayfa kaldırılmış, URL hiç kaydedilmemiş).
