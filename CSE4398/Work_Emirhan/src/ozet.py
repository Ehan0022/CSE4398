"""
Kosu sonu OZET blogu: iki tarafta en ucuz feasible yapilandirma ve maliyeti.

Her model kosusunun (mainframe_model.py, x86_model.py) en sonunda basilir.
Ayni girdilerle iki taraf cozulur; yalnizca secilen yapilandirma ve aylik
maliyet yazilir. Ayrinti (dokum, aralik, NPV, karsilastirma) kosunun
yukarisindadir. sunum_demo/demo_calistir.py bu satirlari toplayip case
dosyasinin sonuna CASE OZETI tablosu olarak yazar.

Satir bicimi (makineyle okunur; demo betigi buna dayanir):
  OZET | <taraf> | <yapilandirma> | <aylik USD veya - > | <not>
"""

OZET_BASLIK = "OZET: iki tarafta en ucuz feasible yapilandirma"


def mf_entry(res):
    """mainframe solve() sonucu (tier, topology, cost) -> (etiket, aylik)."""
    if res is None:
        return None
    tier, topo, cost = res[0], res[1], res[2]
    return (f"{topo.code} {tier.model} ({tier.cps} CP)", cost["total"])


def mf_yearly_entry(sim):
    """mainframe solve_yearly() sonucu -> (etiket, aylik ortalama)."""
    if sim is None:
        return None
    topo = sim["topology"]
    code = getattr(topo, "code", topo)
    strat = sim["strategy_label"].split("(")[0].strip()
    return (f"{code} base {sim['base_tier'].model}, {strat}",
            sim["yearly_total"] / 12.0)


def x86_entry(r):
    """x86 solve() sonucu -> (etiket, aylik)."""
    if r is None:
        return None
    nodes = r["topology"].db_nodes(r["stack"].db, r["k"])
    n = sum(nodes.values())
    return (f"{r['topology'].code} {r['stack']}, {n} x {r['sku'].code} DB dugumu", r["total"])


def parse_line(line):
    """'OZET | taraf | yapilandirma | aylik | not' -> (taraf, yapilandirma, aylik, not)."""
    parts = [x.strip() for x in line.split("|")]
    if len(parts) != 5 or parts[0] != "OZET":
        return None
    return tuple(parts[1:])


def print_ozet(tps, mainframe, x86, note=None, mf_reason=None, x86_reason=None):
    """mainframe / x86: (etiket, aylik) ya da None (kurulamaz).
    *_reason: taraf hic cozulmediyse (karsiligi yok) aciklama."""
    print("\n" + "-" * 70)
    print(f"{OZET_BASLIK} ({tps:,.0f} TPS" + (f"; {note}" if note else "") + ")")
    for side, e, reason in (("mainframe", mainframe, mf_reason), ("x86", x86, x86_reason)):
        if reason:
            print(f"OZET | {side:<9} | karsiligi yok | - | {reason}")
        elif e is None:
            print(f"OZET | {side:<9} | kurulamaz | - | girdiler bu tarafta saglanamiyor")
        else:
            label, monthly = e
            print(f"OZET | {side:<9} | {label} | ${monthly:,.0f}/ay | ${monthly / tps:,.2f}/TPS")
    print("-" * 70)
