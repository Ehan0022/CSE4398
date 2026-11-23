# Kompakt demo: girdileri dosyadan okuyan model kopyası

Sunumda girdileri ve çıktıları kod üzerinde göstermek için. Model kodunun bir kopyası `kod/` altında; girdiler komut satırı yerine `inputs/` klasöründeki JSON dosyalarından okunur. `src/` altındaki orijinal kod değişmedi.

## Klasör

| Yol | Ne |
|---|---|
| `calistir.py` | `inputs/` altındaki bütün case'leri sırayla çalıştırır: her koşu için girdiyi, modelin ona karşılık gelen komutunu ve çıktıyı basar |
| `inputs/case_01_referans.json` … `case_10_npv_ve_aralik.json` | 10 case, 42 koşu (ana demodaki senaryoların aynısı) |
| `kod/common_model.py`, `mainframe_model.py`, `x86_model.py` | `src/` kopyası, yalnızca girdi okuma eklendi |
| `kod/veri/` | Modelin okuduğu iki veri tablosu (z16 A01 kademeleri, DS8900F) |
| `ciktilar/` | `calistir.py`'nin yazdığı tam çıktılar |

## Çalıştırma

```
python sunum_demo/kompakt/calistir.py              # bütün case'ler, özet satırları
python sunum_demo/kompakt/calistir.py 3 7          # yalnızca Case 3 ve 7
python sunum_demo/kompakt/calistir.py 4 --adim     # her koşudan önce Enter bekler (canlı sunum)
python sunum_demo/kompakt/calistir.py 1 --tam      # model çıktısının tamamı
```

Modeli doğrudan da çalıştırabilirsiniz (`kod/` klasöründen):

```
python x86_model.py --input ../inputs/case_01_referans.json
python mainframe_model.py --input ../inputs/case_03_latency.json --kosu 2
python mainframe_model.py --input benim_girdim.json            # {"tps": 5000, "latency_ms": 20}
```

Birden fazla koşu içeren dosyada `--kosu N` ile biri seçilir. Koşu başka modele aitse (ör. x86 koşusu `mainframe_model.py`'ye verilirse) model hata verir.

## Girdi dosyası biçimi

```json
{
  "case": 3,
  "baslik": "Latency hedefi: ...",
  "aciklama": "Bu case'te neyin neden değiştiği",
  "ozet_deseni": "calistir.py'nin ekrana basacağı satırlar (regex)",
  "kosular": [
    {"etiket": "p99 50 ms", "model": "mainframe", "girdi": {"tps": 10000, "latency_ms": 50}}
  ]
}
```

`girdi` içindeki her anahtar aynı adlı komut satırı seçeneğine çevrilir (`latency_ms` → `--latency-ms`). `true` bir bayraktır (`"compare": true` → `--compare`), `false` ve `null` yazılmaz. Kullanılabilir anahtarlar modellerin `--help` çıktısındaki seçeneklerdir (`tps`, `availability`, `workload`, `latency_ms`, `data_tb`, `rpo_seconds`, `rto_minutes`, `backup_target`, `staff_ratio`, `npv`, `years`, `range`, `yearly`, `preset`, `avg_tps`, `compare`, …).

Yeni bir senaryo için bir case dosyasını kopyalayıp `girdi` değerlerini değiştirmek yeterli.

## Koddaki değişiklikler (`src/` ile fark)

1. `common_model.py` sonuna "13. Dışarıdan girdi dosyası" bölümü: `girdi_sozlugu_argv`, `girdi_dosyasi_oku`, `girdi_argv_genislet`.
2. `mainframe_model.py` ve `x86_model.py`: `--input` / `--kosu` seçenekleri ve `parse_args` çağrısı girdiyi dosyadan genişletir. Girdi aynı argparse yolundan geçtiği için doğrulama ve varsayılanlar komut satırıyla birebir aynıdır.
3. `mainframe_model.py`: veri klasörü `../data` yerine `kod/veri`.

Model hesabına dokunulmadı. `calistir.py` her koşunun çıktısını orijinal `src/` koduyla üretilmiş çıktıyla (`sunum_demo/ciktilar/`) SHA-256 üzerinden karşılaştırır. Son koşu: 42 koşunun 42'si aynı.

Model `src/` altında değişirse bu kopya eskir. O durumda üç dosya yeniden kopyalanıp yukarıdaki üç değişiklik tekrar uygulanmalıdır.
