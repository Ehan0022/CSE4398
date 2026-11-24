# Kompakt demo: girdileri dosyadan okuyan model kopyası

Sunumda girdileri ve çıktıları kod üzerinde göstermek için. Model kodunun bir kopyası `kod/` altında; girdiler komut satırı yerine `inputs/` klasöründeki JSON dosyalarından okunur. `src/` altındaki orijinal kod değişmedi.

## Klasör

| Yol | Ne |
|---|---|
| `calistir.py` | `inputs/` altındaki bütün case'leri sırayla çalıştırır: her koşu için girdiyi, modelin ona karşılık gelen komutunu ve çıktıyı basar |
| `inputs/case_01_referans.json` … `case_12_maliyet_kazanan.json` | 12 case, 50 koşu (ana demodaki senaryoların aynısı; ana demodaki kazanan haritası aracı burada yok); her koşuda tam girdi seti |
| `inputs/_fiyat_parametreleri.json` | Modelin 43 kaynaklı fiyat/maliyet parametresi (senaryo girdisi değil; `prices` ile değiştirilir) |
| `kod/common_model.py`, `mainframe_model.py`, `x86_model.py` | `src/` kopyası, yalnızca girdi okuma eklendi |
| `kod/veri/` | Modelin okuduğu iki veri tablosu (z16 A01 kademeleri, DS8900F) |
| `ciktilar/` | `calistir.py`'nin yazdığı tam çıktılar |

## Çalıştırma

```
python sunum_demo/kompakt/calistir.py              # bütün case'ler, her koşunun OZET satırları
python sunum_demo/kompakt/calistir.py --ayrinti    # OZET'e ek olarak ozet_deseni satırları
python sunum_demo/kompakt/calistir.py 3 7          # yalnızca Case 3 ve 7
python sunum_demo/kompakt/calistir.py 4 --adim     # her koşudan önce Enter bekler (canlı sunum)
python sunum_demo/kompakt/calistir.py 1 --tam      # model çıktısının tamamı
python sunum_demo/kompakt/calistir.py --kisa       # girdi tablosunda yalnızca farklı alanlar
```

Modeli doğrudan da çalıştırabilirsiniz (`kod/` klasöründen):

```
python x86_model.py --input ../inputs/case_01_referans.json
python mainframe_model.py --input ../inputs/case_03_latency.json --kosu 2
python mainframe_model.py --input benim_girdim.json            # {"tps": 5000, "latency_ms": 20}
```

Birden fazla koşu içeren dosyada `--kosu N` ile biri seçilir. Koşu başka modele aitse (ör. x86 koşusu `mainframe_model.py`'ye verilirse) model hata verir.

## Girdi dosyası biçimi

Her koşuda modelin bütün senaryo girdileri açıkça yazılıdır: verilmeyen bir girdi de varsayılan değeriyle ya da `null` olarak görünür. Böylece bir koşunun tam olarak hangi girdilerle çalıştığı dosyadan okunur.

```json
{
  "case": 3,
  "baslik": "Latency hedefi: ...",
  "aciklama": "Bu case'te neyin neden değiştiği",
  "ozet_deseni": "--ayrinti ile ekrana basılacak ek çıktı satırları (regex)",
  "girdi_sozlugu": {
    "latency_ms": {"varsayilan": null, "birim": "ms", "model": "ikisi",
                   "aciklama": "Yanıt süresi hedefi. null = hedef yok"}
  },
  "kosular": [
    {"etiket": "p99 50 ms", "model": "mainframe",
     "referanstan_farkli": ["latency_ms"],
     "girdi": {"tps": 10000, "workload": "oltp_rw", "availability": 0.999,
               "latency_ms": 50, "data_tb": 20, "...": "..."}}
  ]
}
```

- `girdi_sozlugu`: o case'te kullanılan modellerin her girdisi için varsayılan, birim, hangi modele ait olduğu ve kısa açıklama.
- `girdi`: koşunun tam girdi seti. Mainframe koşusunda 25, x86 koşusunda 30 alan var (Değ #10 ile `pg_support` ve `unmasked_share` eklendi).
- `referanstan_farkli`: Case 1 referansından (10K TPS, diğer her şey varsayılan) farklı olan alanlar. `calistir.py` bunları `>>` ile işaretler.
- `null`: o girdi verilmedi; anlamı açıklamada yazılı (ör. `rpo_seconds: null` = kısıt yok, `db: null` = iki veritabanı da aday).

Her anahtar aynı adlı komut satırı seçeneğine çevrilir (`latency_ms` → `--latency-ms`). `true` bir bayraktır (`"compare": true` → `--compare`), `false` ve `null` yazılmaz.

**Senaryo girdisi olmayanlar:** Fiyat ve maliyet parametreleri (43 adet: AWLC kademeleri, sunucu, disk, lisans, personel ücreti …) senaryo girdisi değil, modelin kaynaklı parametreleridir. Hepsi değerleriyle `inputs/_fiyat_parametreleri.json`'da. Değiştirmek için dosyanın bir kopyası düzenlenip koşunun `prices` alanına yolu yazılır. `--list-prices`, `--price-vintages`, `--calibration` ve `--demo` girdi değil, ayrı yardımcı komutlar olduğu için listede yok.

Yeni bir senaryo için bir case dosyasını kopyalayıp `girdi` değerlerini değiştirmek yeterli.

**Çalıştırıcı:** Her koşuda tam girdi tablosunu basar (değer, birim, açıklama). `--kisa` verilirse yalnızca referanstan farklı alanları basar.

## Koddaki değişiklikler (`src/` ile fark)

1. `common_model.py` sonuna "13. Dışarıdan girdi dosyası" bölümü: `girdi_sozlugu_argv`, `girdi_dosyasi_oku`, `girdi_argv_genislet`.
2. `mainframe_model.py` ve `x86_model.py`: `--input` / `--kosu` seçenekleri ve `parse_args` çağrısı girdiyi dosyadan genişletir. Girdi aynı argparse yolundan geçtiği için doğrulama ve varsayılanlar komut satırıyla birebir aynıdır.
3. `mainframe_model.py`: veri klasörü `../data` yerine `kod/veri`.

Model hesabına dokunulmadı. `calistir.py` her koşunun çıktısını orijinal `src/` koduyla üretilmiş çıktıyla (`sunum_demo/ciktilar/`) SHA-256 üzerinden karşılaştırır. Son koşu (2026-11-24): 50 koşunun 50'si aynı. Bu, varsayılanların açıkça yazılmasının sonucu değiştirmediğini de gösterir.

Model `src/` altında değişirse bu kopya eskir. O durumda üç dosya yeniden kopyalanıp yukarıdaki üç değişiklik tekrar uygulanmalıdır.

## Case özeti (2026-11-24)

Her koşu, modelin OZET bloğuyla biter: iki tarafta en ucuz feasible yapılandırma ve aylık maliyet (`kod/ozet.py`, `src/ozet.py` ile aynı). `calistir.py` ekrana varsayılan olarak yalnızca bu satırları basar ve her `ciktilar/case_NN_*.txt` dosyasının sonuna bütün koşuların CASE ÖZETİ'ni yazar (biçim ana demodakiyle aynı).
