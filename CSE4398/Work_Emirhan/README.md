# CSE4398 Bitirme Projesi — Mainframe vs On-Prem Clustered x86 (OLTP, full-stack TCO)

## Klasör yapısı

| Yol | İçerik |
|---|---|
| `PROJECT_LOG.md` | Kronolojik log: aksiyon → sebep → sonuç. Her çalışma oturumundan sonra en alta eklenir. |
| `docs/` | Tasarım dokümanları: `project_justification.md` (gerekçe), `project_context_restore_v4.md` (kararlar ve gerekçeleri), `mainframe_model_documentation_v3.md` (mainframe modelinin **güncel** teknik dokümantasyonu). `mainframe_model_documentation_v2.md` tarihsel kayıt olarak duruyor. |
| `src/` | Kod: `mainframe_model.py` (model + CLI), `test_mainframe_model.py` (tutarlılık testleri), `tools/build_z16_capacity_table.py` (kademe tablosunu ham verilerden üretir), `tools/pricing_sensitivity.py` (fiyatlama varsayımlarının duyarlılık analizi), `tools/storage_sensitivity.py` (storage duyarlılık analizi), `tools/software_sensitivity.py` (yazılım yığını: AWLC + zIIP duyarlılık analizi), `tools/workload_sensitivity.py` (iş yükü profili: işlem bileşimi duyarlılık analizi), `tools/range_curve.py` (maliyet/TPS aralığı, low/mid/high, CSV `data/out/`), `tools/availability_sensitivity.py` (olay tabanlı availability, hedef → topoloji → maliyet, RPO/RTO), `tools/npv_sensitivity.py` (TS7770 yedekleme ve 5 yıllık NPV duyarlılığı) |
| `data/` | `z16_a01_capacity.csv` (317 z16 A01 kademesi), `ds8900f_models.csv` (DS8900F model kataloğu); `raw/` altında ham IBM verileri (kaynak ve erişim tarihi dosya başlığında) |
| `evaluations/` | Tarihli rutin akademik değerlendirmeler: `YYYY-MM-DD_degerlendirme_NN.md` |

## Çalıştırma

```
cd src
python mainframe_model.py --demo
python mainframe_model.py --yearly --preset retail_bursty --avg-tps 10000 --workload oltp_rw
python mainframe_model.py --tps 10000 --npv --range   # 5 yıllık NPV aralığı
python test_mainframe_model.py
cd ..
python src/tools/build_z16_capacity_table.py   # kademe tablosunu yeniden üretir
python src/tools/pricing_sensitivity.py        # fiyatlama duyarlılık analizi (~2 dk)
python src/tools/storage_sensitivity.py        # storage duyarlılık analizi
python src/tools/software_sensitivity.py       # yazılım yığını (AWLC + zIIP) duyarlılık analizi
python src/tools/workload_sensitivity.py       # iş yükü profili (işlem bileşimi) duyarlılık analizi
python src/tools/range_curve.py                # maliyet/TPS aralığı (low/mid/high) + CSV
python src/tools/availability_sensitivity.py   # availability, DR maliyeti, RPO/RTO
python src/tools/npv_sensitivity.py            # yedekleme + 5 yıllık NPV (--fast: yıllık stratejiler hariç)
```
