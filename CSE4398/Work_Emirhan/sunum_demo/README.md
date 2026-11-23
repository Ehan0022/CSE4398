# Sunum Demosu ve Slayt İçeriği

*2026-11-23 · Hocaya sunum için hazırlandı. Orijinal tasarım dokümanları değiştirilmedi; bu klasör yalnızca mevcut modelleri ve dokümanları sunuma çevirir.*

## İçerik

| Dosya | Ne |
|---|---|
| `DEMO_SENARYOLARI.md` | 10 demo senaryosu: komut, çıktı özeti, neyin neden değiştiği, sunum akışı |
| `demo_calistir.py` | 10 senaryoyu (42 komut) modellere koşturan ve çıktıların birbirinden farklı olduğunu doğrulayan betik |
| `ciktilar/` | Her case'in tam model çıktısı (`case_NN_*.txt`) ve betiğin özet çıktısı (`demo_ozet.txt`) |
| `slaytlar/01_giris_ve_mainframe.md` | Giriş (3 slayt) + mainframe katmanları (14 katman × 2 = 28 slayt) |
| `slaytlar/02_acik_sistem.md` | Açık sistem katmanları ve opsiyonları (14 katman × 2 = 28 slayt) |
| `slaytlar/03_kopruler.md` | Köprü haritası + KB-01 – KB-18 (18 köprü × 2 = 36 slayt) |
| `slaytlar/04_kapanis.md` | Bulgular, geçerlilik tehditleri ve sınırlılıklar, sonraki adımlar (3 slayt) |

Toplam 98 slayt, artı isteğe bağlı bir köprü haritası slaytı (K0). Her slaytta: başlık, maddeler, kullanılan veri/kaynak, tasarım gerekçesi, konuşmacı notu.

## Çalıştırma

```
cd Work_Emirhan
python sunum_demo/demo_calistir.py          # hepsi, ~15 sn
python sunum_demo/demo_calistir.py 4 8      # yalnızca seçilen case'ler
```

Python 3.10+, yalnızca standart kütüphane ve modellerin kendi bağımlılıkları.

## Sayıların kaynağı

Bütün sayılar `main` dalındaki modellerin (PR #4 sonrası, Adım 7) varsayılanlarla koşusundan alındı: oltp_rw, %99,9, 20 TB, yılda %15 veri büyümesi, `PRICE_EPOCH` 2025-mid, `STAFF_RATIO_X86` 1,0. Model değişirse `demo_calistir.py` yeniden koşturulmalı ve dokümanlardaki sayılar `ciktilar/` ile karşılaştırılmalıdır. Dokümanlardaki bazı eski tablolar (ör. v3 §5.5, §6.6, §6.7'deki $846.187'li satırlar) Adım 7 öncesine aittir; slaytlarda güncel değerler kullanıldı.

## Kapsam dışı (slaytlarda sınırlılık olarak)

MQ / mesajlaşma (iki tarafta), z16 A02 / AGZ rack-mount modeller, Parallel Sysplex data sharing (x86'da Citus karşılığı), bare-metal Kubernetes, z17 / yeni sunucu nesli yenilemesi, PUE ve veri merkezi ağı.
