"""
Regresyon icin "altin" sonuc kumesi (golden snapshot).

Adim 6'da ortak parametreler ve kurallar common_model.py'ye tasindi. Tasimanin
sonuclari degistirmedigini gostermek icin, tasimadan ONCEKI kodla bu betik
calistirilip data/test/golden_step5.json uretildi. test_mainframe_model.py
ayni kumeyi yeniden hesaplar ve (NONPROD_FACTOR = 0 iken) birebir esitlik ister.

Kullanim:
  python tools/golden_snapshot.py            -> JSON'u stdout'a yazar
  python tools/golden_snapshot.py --write    -> data/test/golden_step5.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                           "data", "test", "golden_step5.json")

STATIC_CASES = [
    # (ad, tps, availability, kwargs)
    ("s1k", 1000, 0.999, {}),
    ("s10k", 10000, 0.999, {}),
    ("s10k_5n", 10000, 0.99999, {}),
    ("s10k_500tb", 10000, 0.999, {"data_tb": 500}),
    ("s10k_rpo0", 10000, 0.999, {"rpo_seconds": 0, "rto_minutes": 60}),
    ("s50k", 50000, 0.9999, {}),
    ("s150k", 150000, 0.999, {}),
]
COMPONENTS = ("software", "hardware_amort", "maintenance", "energy", "gdps", "staff",
              "storage", "backup", "total")


def snapshot():
    out = {"static": {}, "range": {}, "yearly": {}, "npv": {}}
    for name, tps, av, kw in STATIC_CASES:
        r = m.solve(tps, av, verbose=False, **kw)
        tier, topo, cost = r[0], r[1], r[2]
        out["static"][name] = {"tier": tier.model, "topology": topo.code,
                               **{k: cost[k] for k in COMPONENTS}}
    for tps in (10000, 50000):
        rng = m.solve_range(tps)
        out["range"][str(tps)] = {lv: (None if x is None else
                                       {"tier": x["tier"].model,
                                        "topology": x["topology"].code,
                                        "total": x["cost"]["total"]})
                                  for lv, x in rng.items()}
    for preset in ("steady_oltp", "retail_bursty", "batch_heavy"):
        y = m.solve_yearly(preset, 10000, verbose=False)
        out["yearly"][preset] = {k: {"total": s["yearly_total"], "base": s["base_tier"].model,
                                     "topology": s["topology"].code}
                                 for k, s in y["by_strategy"].items()}
    n = m.solve_npv(10000)
    out["npv"]["static_10k"] = {"npv": n["npv"], "levelized": n["levelized_per_tps_month"]}
    nr = m.solve_npv_range(10000)
    out["npv"]["range_10k"] = {lv: x["npv"] for lv, x in nr.items()}
    ny = m.solve_npv_yearly("steady_oltp", 10000, "tfp")
    out["npv"]["yearly_steady_tfp"] = {"npv": ny["npv"]}
    return out


if __name__ == "__main__":
    snap = snapshot()
    if "--write" in sys.argv:
        os.makedirs(os.path.dirname(GOLDEN_PATH), exist_ok=True)
        with open(GOLDEN_PATH, "w") as f:
            json.dump(snap, f, indent=1, sort_keys=True)
        print(f"yazildi: {os.path.normpath(GOLDEN_PATH)}")
    else:
        print(json.dumps(snap, indent=1, sort_keys=True))
