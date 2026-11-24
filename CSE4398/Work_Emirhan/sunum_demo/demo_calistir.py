"""Sunum demosu: 12 senaryoyu modellere gercekten kosturur ve ciktilari kaydeder.

Kullanim (Work_Emirhan klasorunden):
    python sunum_demo/demo_calistir.py            # hepsini kostur, ciktilar/ altina yaz
    python sunum_demo/demo_calistir.py 3 7        # yalnizca Case 3 ve Case 7
    python sunum_demo/demo_calistir.py --ayrinti  # ekranda case ozetine ek ayrinti satirlari

Her case birden fazla komut icerebilir (ayni eksende birkac nokta). Betik her
komutu src/ klasorunde calistirir, tam ciktiyi sunum_demo/ciktilar/ altina yazar.
Her model kosusu OZET satirlariyla biter (src/ozet.py: iki tarafta en ucuz
feasible yapilandirma ve aylik maliyet); betik bunlari toplayip case dosyasinin
sonuna CASE OZETI olarak yazar ve ekrana da yalnizca bu ozeti basar. Sonda butun
komut ciktilarinin birbirinden farkli oldugunu (SHA-256) dogrular.
"""
import hashlib
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import ozet  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(KOK, "src")
CIKTI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ciktilar")

MF = "mainframe_model.py"
X86 = "x86_model.py"

# (no, kisa ad, baslik, [(etiket, betik, argumanlar)], --ayrinti icin regex)
CASES = [
    (1, "referans", "Referans nokta: 10K TPS, oltp_rw, %99,9, 20 TB",
     [("x86 + karsilastirma", X86, "--tps 10000 --compare")],
     r"SECILEN|AYLIK|personel:|mainframe:|x86: |oran \(|basabas|personel haric"),
    (2, "tps_olcegi", "TPS olcegi: 1K / 3K / 30K / 50K (10K = Case 1)",
     [(f"{t} TPS", X86, f"--tps {t} --compare") for t in (1000, 3000, 30000, 50000)],
     r"mainframe:|x86: |oran \(|basabas"),
    (3, "latency", "Latency hedefi: yok / p99 50 ms / 20 ms / 10 ms (mainframe kademesi)",
     [("hedef yok", MF, "--tps 10000"),
      ("p99 50 ms", MF, "--tps 10000 --latency-ms 50"),
      ("p99 20 ms", MF, "--tps 10000 --latency-ms 20"),
      ("p99 10 ms", MF, "--tps 10000 --latency-ms 10"),
      ("x86, p99 20 ms", X86, "--tps 10000 --latency-ms 20")],
     r"KADEME|tavani|utilization:|tahmini p99|p99 ~|kullanim %|AYLIK"),
    (4, "availability", "Availability / RPO / RTO: (%99,9 = Case 1) -> M2-X2 -> M4-X3 ve infeasible sinir",
     [("%99,99 + RPO 0 + RTO 120 dk", X86,
       "--tps 10000 --availability 0.9999 --rpo-seconds 0 --rto-minutes 120 --compare"),
      ("%99,999", X86, "--tps 10000 --availability 0.99999 --compare"),
      ("mainframe %99,999 + RPO 0 + RTO 30 dk", MF,
       "--tps 10000 --availability 0.99999 --rpo-seconds 0 --rto-minutes 30"),
      ("mainframe %99,999 dokum", MF, "--tps 10000 --availability 0.99999")],
     r"SECILEN TOPOLOJI|SECILEN YIGIN|availability:|DR payi|GDPS:|donanim:|SONUC|mainframe:|x86: |oran \("),
    (5, "veri_hacmi", "Veri hacmi: 10 / 100 / 500 TB (storage ve yedek ekseni)",
     [(f"{d} TB, mainframe", MF, f"--tps 10000 --data-tb {d}") for d in (10, 100, 500)]
     + [(f"{d} TB, x86", X86, f"--tps 10000 --data-tb {d} --compare") for d in (10, 100, 500)],
     r"AYLIK|storage:|yedekleme:|SECILEN YIGIN|mainframe:|x86: "),
    (6, "is_yuku", "Is yuku profili: redp_light / tpcb_like / (oltp_rw = Case 1, 3) / oltp_heavy",
     [(w, MF, f"--tps 10000 --workload {w}") for w in ("redp_light", "tpcb_like", "oltp_heavy")]
     + [(f"{w}, x86", X86, f"--tps 10000 --workload {w} --compare") for w in ("tpcb_like", "oltp_heavy")],
     r"is yuku profili|islem / s / PCI|KADEME|AYLIK|yazilim:|I/O:|DUGUMU|mainframe:|x86: "),
    (7, "yedek_hedefi", "Yedek hedefi: 100 TB'ta zorlanan hedefler (auto = Case 5) ve 500 TB'ta kisit",
     [(f"100 TB, {b}", MF, f"--tps 10000 --data-tb 100 --backup-target {b}")
      for b in ("ts7770", "aws_s3")]
     + [("500 TB, cos_onprem zorla", MF, "--tps 10000 --data-tb 500 --backup-target cos_onprem")],
     r"AYLIK|yedekleme:"),
    (8, "fiyatlama_abc", "Fiyatlama stratejileri A / B / C (yillik mod, 3 preset)",
     [(p, MF, f"--yearly --preset {p} --avg-tps 10000")
      for p in ("steady_oltp", "batch_heavy", "retail_bursty")],
     r"Secilen strateji|Alternatif|Base kademe|Corridor tavani|CoD tepe|TOPLAM|ucuz"),
    (9, "personel_orani", "Personel orani (STAFF_RATIO_X86): (1,0 = Case 1) / 1,25 / 2,16 / 3,0",
     [(f"oran {s}", X86, f"--tps 10000 --staff-ratio {s} --compare") for s in (1.25, 2.16, 3.0)],
     r"personel:|mainframe:|x86: |oran \("),
    (10, "npv_ve_aralik", "NPV ufku (3 / 5 / 10 yil) ve belirsizlik araligi (--range)",
     [(f"mainframe NPV {y} yil", MF, f"--tps 10000 --npv --years {y}") for y in (3, 5, 10)]
     + [(f"x86 NPV {y} yil", X86, f"--tps 10000 --npv --years {y}") for y in (3, 5, 10)]
     + [("mainframe --range", MF, "--tps 10000 --range"),
        ("x86 --range --compare", X86, "--tps 10000 --range --compare")],
     r"NPV:|seviyelendirilmis|^\s+\d+ \|\s+[\d,]+ \| 3931|^\s+(low|mid|high)\s|x86_lehine|^\s+orta\s|mainframe_lehine|ortak_(low|high)"),
    # Degerlendirme #10: mainframe'in kazandigi bolgeler
    (11, "availability_kazanan", "Yuksek availability: %99,999 + RPO 0'da yalniz mainframe; u ve destek duyarliligi",
     [("%99,999 + RPO 0 (x86 kurulamaz)", X86, "--tps 10000 --availability 0.99999 --rpo-seconds 0 --compare"),
      ("%99,999, RPO serbest, 50K (x86 Oracle X4)", X86, "--tps 50000 --availability 0.99999 --compare"),
      ("mainframe %99,999 + RPO 0 dokum, 3K", MF, "--tps 3000 --availability 0.99999 --rpo-seconds 0"),
      ("u = 0,05 duyarliligi", X86,
       "--tps 10000 --availability 0.99999 --rpo-seconds 0 --unmasked-share 0.05 --compare"),
      ("desteksiz PostgreSQL, %99,9", X86, "--tps 10000 --pg-support 0 --compare"),
      ("kazanan haritasi (hizli)", "tools/kazanan_haritasi.py", "--hizli")],
     r"SECILEN TOPOLOJI|availability:|mainframe:|x86: |oran \(|basabas|SONUC|destegi|^\s+%99|^\s+hedef|Senaryo:|u=0"),
    (12, "maliyet_kazanan", "Maliyette kazanan bolge: 30K / 50K'da eslestirilmis senaryolar ve personel orani 2,5",
     [("30K --range --compare", X86, "--tps 30000 --range --compare"),
      ("50K --range --compare", X86, "--tps 50000 --range --compare"),
      ("50K, personel orani 2,5", X86, "--tps 50000 --staff-ratio 2.5 --compare")],
     r"mainframe:|x86: |oran \(|basabas|x86_lehine|^\s+orta\s|mainframe_lehine|ortak_(low|high)"),
]


def run(script, args):
    cmd = [sys.executable, script] + args.split()
    p = subprocess.run(cmd, cwd=SRC, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def case_ozeti(no, ozetler):
    """Case sonu ozeti: her kosu icin iki tarafta en ucuz feasible yapilandirma."""
    out = ["=" * 78, f"CASE {no} OZETI: iki tarafta en ucuz feasible yapilandirma ve aylik maliyet",
           "=" * 78]
    for etiket, satirlar in ozetler:
        out.append(f"  {etiket}")
        if not satirlar:
            out.append("    (izgara araci; tek yapilandirma yok, tablo yukarida)")
            continue
        for taraf, konf, aylik, notu in satirlar:
            if aylik == "-":
                out.append(f"    {taraf + ':':<11}{konf} ({notu})")
            else:
                out.append(f"    {taraf + ':':<11}{konf:<58} {aylik:>15}  {notu}")
    return out


def main(argv):
    ayrinti = "--ayrinti" in argv
    argv = [a for a in argv if a != "--ayrinti"]
    secim = {int(a) for a in argv} if argv else None
    os.makedirs(CIKTI, exist_ok=True)
    hashes = {}
    for no, kisa, baslik, komutlar, desen in CASES:
        if secim and no not in secim:
            continue
        print("=" * 78)
        print(f"CASE {no}: {baslik}")
        print("=" * 78)
        dosya = os.path.join(CIKTI, f"case_{no:02d}_{kisa}.txt")
        ozetler = []
        with open(dosya, "w", encoding="utf-8") as f:
            for etiket, script, args in komutlar:
                rc, out = run(script, args)
                h = hashlib.sha256(out.encode()).hexdigest()[:12]
                hashes.setdefault(h, []).append(f"case {no} / {etiket}")
                baslik_satiri = f"--- {etiket}: python src/{script} {args}  (cikis kodu {rc}, sha {h})"
                f.write(baslik_satiri + "\n" + out + "\n")
                satirlar = [r for r in map(ozet.parse_line, out.splitlines()) if r]
                tps = re.search(r"--(?:avg-)?tps (\d+)", args)
                ek = tps and not re.search(r"TPS|\d+K\b", etiket)
                ozetler.append((f"{etiket}" + (f" ({int(tps.group(1)):,} TPS)" if ek else ""),
                                satirlar))
                if ayrinti:
                    print(baslik_satiri)
                    for line in out.splitlines():
                        if re.search(desen, line):
                            print("   " + line.rstrip())
            ozet_satirlari = case_ozeti(no, ozetler)
            f.write("\n".join(ozet_satirlari) + "\n")
        for line in ozet_satirlari[3:]:
            print(line)
        print(f"   -> tam cikti: sunum_demo/ciktilar/{os.path.basename(dosya)}\n")
    tekrar = {h: v for h, v in hashes.items() if len(v) > 1}
    print("=" * 78)
    if tekrar:
        print("UYARI: ayni ciktiyi veren komutlar var:")
        for h, v in tekrar.items():
            print(f"  {h}: {v}")
        return 1
    print(f"Dogrulama: {sum(len(v) for v in hashes.values())} komutun hepsi birbirinden farkli cikti verdi.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
