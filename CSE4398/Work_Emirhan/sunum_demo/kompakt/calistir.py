"""Kompakt sunum demosu: inputs/ klasorundeki case dosyalarini sira sira calistirir.

Kullanim (herhangi bir klasorden):
    python sunum_demo/kompakt/calistir.py              # butun case'ler, ozet satirlari
    python sunum_demo/kompakt/calistir.py 3 7          # yalnizca Case 3 ve Case 7
    python sunum_demo/kompakt/calistir.py 4 --adim     # her kosudan once Enter bekler
    python sunum_demo/kompakt/calistir.py 1 --tam      # model ciktisinin tamamini basar
    python sunum_demo/kompakt/calistir.py --kisa       # girdi tablosunda yalnizca farkli alanlar
    python sunum_demo/kompakt/calistir.py --ayrinti    # OZET'e ek olarak case'in ozet_deseni satirlari

Her case bir JSON dosyasidir (inputs/case_NN_*.json). Dosyadaki her kosu icin:
  1. GIRDI: modelin butun senaryo girdileri (deger, birim, aciklama; Case 1
     referansindan farkli olanlar '>>' ile isaretli) ve esdeger komut,
  2. CIKTI: modelin OZET satirlari (iki tarafta en ucuz feasible yapilandirma ve
     aylik maliyet; --ayrinti ile case'in ozet_deseni'ne uyan satirlar da),
  3. tam cikti kompakt/ciktilar/case_NN_*.txt dosyasina yazilir; dosyanin sonunda
     butun kosularin CASE OZETI vardir.

Modeller kod/ klasorundeki kopyadir ve girdiyi kendileri okur:
    python sunum_demo/kompakt/kod/x86_model.py --input sunum_demo/kompakt/inputs/case_01_referans.json

Sonda her kosunun ciktisi, orijinal src/ koduyla uretilmis ciktilarla
(sunum_demo/ciktilar/) SHA-256 uzerinden karsilastirilir: kopya kod ayni girdiye
ayni ciktiyi vermelidir.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOD = os.path.join(BURASI, "kod")
GIRDILER = os.path.join(BURASI, "inputs")
CIKTI = os.path.join(BURASI, "ciktilar")
ORIJINAL_CIKTI = os.path.join(os.path.dirname(BURASI), "ciktilar")
BETIK = {"mainframe": "mainframe_model.py", "x86": "x86_model.py"}
CIZGI = "=" * 78


def kosu_calistir(case_dosyasi, kosu_no, model):
    cmd = [sys.executable, BETIK[model], "--input", case_dosyasi, "--kosu", str(kosu_no)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, cwd=KOD, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, p.stdout + p.stderr


def deger_yaz(v):
    if v is None:
        return "-"
    if v is True:
        return "evet"
    if v is False:
        return "hayir"
    return str(v)


def girdi_tablosu(kosu, sozluk, kisa=False):
    """Kosunun butun girdilerini basar; referanstan farkli olanlar '>>' ile isaretli."""
    farkli = set(kosu.get("referanstan_farkli", []))
    print("  GIRDI  (>> = Case 1 referansindan farkli; - = verilmedi, anlami aciklamada)")
    for anahtar, deger in kosu["girdi"].items():
        if kisa and anahtar not in farkli:
            continue
        s = sozluk.get(anahtar, {})
        isaret = ">>" if anahtar in farkli else "  "
        print(f"    {isaret} {anahtar:<20} {deger_yaz(deger):>10}  {s.get('birim', ''):<11} "
              f"{s.get('aciklama', '')}")


def orijinal_hashler():
    """sunum_demo/ciktilar/ basliklarindan (case, etiket) -> sha12 eslemesi."""
    sonuc = {}
    for yol in glob.glob(os.path.join(ORIJINAL_CIKTI, "case_*.txt")):
        no = int(os.path.basename(yol)[5:7])
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                m = re.match(r"--- (.+?): python src/.*sha ([0-9a-f]{12})\)", satir)
                if m:
                    sonuc[(no, m.group(1))] = m.group(2)
    return sonuc


def case_ozeti(no, ozetler):
    """Case sonu ozeti (ana demodaki demo_calistir.case_ozeti ile ayni bicim)."""
    out = [CIZGI, f"CASE {no} OZETI: iki tarafta en ucuz feasible yapilandirma ve aylik maliyet",
           CIZGI]
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
    adim = "--adim" in argv
    tam = "--tam" in argv
    kisa = "--kisa" in argv
    ayrinti = "--ayrinti" in argv
    secim = {int(a) for a in argv if a.isdigit()}
    os.makedirs(CIKTI, exist_ok=True)
    referans = orijinal_hashler()
    sys.path.insert(0, KOD)
    import common_model as cm  # yalnizca girdi -> komut cevirisini gostermek icin
    import ozet
    ayni, farkli, kontrolsuz = [], [], []

    for yol in sorted(glob.glob(os.path.join(GIRDILER, "case_*.json"))):
        with open(yol, encoding="utf-8") as f:
            case = json.load(f)
        if secim and case["case"] not in secim:
            continue
        print(CIZGI)
        print(f"CASE {case['case']}: {case['baslik']}")
        print(CIZGI)
        print(f"Ne degisiyor: {case['aciklama']}")
        print(f"Girdi dosyasi: inputs/{os.path.basename(yol)}\n")
        desen = re.compile(case.get("ozet_deseni") or ".")
        cikti_yolu = os.path.join(CIKTI, os.path.basename(yol).replace(".json", ".txt"))
        ozetler = []
        with open(cikti_yolu, "w", encoding="utf-8") as cikti:
            for i, kosu in enumerate(case["kosular"], start=1):
                girdi_json = json.dumps(kosu["girdi"], ensure_ascii=False)
                esdeger = " ".join(cm.girdi_sozlugu_argv(kosu["girdi"]))
                print(f"--- Kosu {i}/{len(case['kosular'])}: {kosu['etiket']}  (model: {kosu['model']})")
                girdi_tablosu(kosu, case.get("girdi_sozlugu", {}), kisa)
                print(f"         esdeger komut: python {BETIK[kosu['model']]} {esdeger}")
                if adim:
                    input("  [Enter ile calistir]")
                rc, out = kosu_calistir(yol, i, kosu["model"])
                sha = hashlib.sha256(out.encode()).hexdigest()[:12]
                ref = referans.get((case["case"], kosu["etiket"]))
                etiket = f"case {case['case']} / {kosu['etiket']}"
                if ref is None:
                    kontrolsuz.append(etiket)
                    durum = "orijinal cikti yok"
                elif ref == sha:
                    ayni.append(etiket)
                    durum = "orijinal src/ ciktisiyla ayni"
                else:
                    farkli.append(etiket)
                    durum = f"ORIJINALDEN FARKLI ({ref})"
                cikti.write(f"--- {kosu['etiket']}: --input {os.path.basename(yol)} --kosu {i}"
                            f"  [{girdi_json}]  (cikis kodu {rc}, sha {sha})\n{out}\n")
                print(f"  CIKTI  (cikis kodu {rc}, sha {sha}, {durum})")
                satirlar = [r for r in map(ozet.parse_line, out.splitlines()) if r]
                ozetler.append((kosu["etiket"], satirlar))
                for satir in out.splitlines():
                    if tam or (ayrinti and desen.search(satir)) or ozet.parse_line(satir):
                        print("    " + satir.rstrip())
                print()
            cikti.write("\n".join(case_ozeti(case["case"], ozetler)) + "\n")
        print(f"  -> tam cikti: kompakt/ciktilar/{os.path.basename(cikti_yolu)}\n")

    print(CIZGI)
    print(f"Orijinal kodla karsilastirma: {len(ayni)} kosu ayni, {len(farkli)} farkli, "
          f"{len(kontrolsuz)} karsilastirilamadi.")
    for e in farkli:
        print(f"  FARKLI: {e}")
    return 1 if farkli else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))
