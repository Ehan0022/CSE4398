# CSE4398 Bitirme Projesi — Mainframe vs On-Prem Clustered x86 (OLTP, full-stack TCO)

## Klasör yapısı

| Yol | İçerik |
|---|---|
| `PROJECT_LOG.md` | Kronolojik log: aksiyon → sebep → sonuç. Her çalışma oturumundan sonra en alta eklenir. |
| `docs/` | Tasarım dokümanları: `project_justification.md` (gerekçe), `project_context_restore_v4.md` (kararlar ve gerekçeleri), `mainframe_model_documentation_v3.md` (mainframe modelinin **güncel** teknik dokümantasyonu). `mainframe_model_documentation_v2.md` tarihsel kayıt olarak duruyor. |
| `src/` | Kod: `mainframe_model.py` (model + CLI), `test_mainframe_model.py` (tutarlılık testleri), `tools/build_z16_capacity_table.py` (kademe tablosunu ham verilerden üretir), `tools/pricing_sensitivity.py` (fiyatlama varsayımlarının duyarlılık analizi), `tools/storage_sensitivity.py` (storage duyarlılık analizi), `tools/software_sensitivity.py` (yazılım yığını: AWLC + zIIP duyarlılık analizi) |
| `data/` | `z16_a01_capacity.csv` (317 z16 A01 kademesi), `ds8900f_models.csv` (DS8900F model kataloğu); `raw/` altında ham IBM verileri (kaynak ve erişim tarihi dosya başlığında) |
| `evaluations/` | Tarihli rutin akademik değerlendirmeler: `YYYY-MM-DD_degerlendirme_NN.md` |

## Çalıştırma

```
cd src
python mainframe_model.py --demo
python mainframe_model.py --yearly --preset retail_bursty --avg-tps 50000
python test_mainframe_model.py
cd ..
python src/tools/build_z16_capacity_table.py   # kademe tablosunu yeniden üretir
python src/tools/pricing_sensitivity.py        # fiyatlama duyarlılık analizi (~2 dk)
python src/tools/storage_sensitivity.py        # storage duyarlılık analizi
python src/tools/software_sensitivity.py       # yazılım yığını (AWLC + zIIP) duyarlılık analizi
```
