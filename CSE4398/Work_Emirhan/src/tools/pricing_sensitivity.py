"""
Fiyatlama varsayimlarinin duyarlilik analizi (yillik mod, M1, 10K ort. TPS, oltp_rw).
Kalibre edilmemis [ASSUME] parametreleri tek tek tarar ve her preset icin
kazanan stratejiyi ve stratejilerin yillik toplamlarini yazdirir.
Calistirma (proje kokunden):  python src/tools/pricing_sensitivity.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mainframe_model as m  # noqa: E402

PRESETS = list(m.WORKLOAD_PRESETS)
SWEEPS = [
    ("CORRIDOR_PREMIUM", [1.0, 1.5, 2.5, 4.0]),
    ("CORRIDOR_FRACTION", [0.10, 0.20, 0.35, 0.50]),
    ("CORRIDOR_SUBSCRIPTION_RATE", [0.0, 0.10, 0.25, 0.50]),
    ("COD_DAILY_MULTIPLIER", [1.5, 2.5, 4.0]),
    ("TFP_SW_DISCOUNT", [0.0, 0.05, 0.10]),
]
SHORT = {"permanent": "A", "base_cod": "B", "tfp": "C"}


def row(preset):
    s = m.solve_yearly(preset_name=preset, yearly_avg_tps=10000, verbose=False)
    tot = {SHORT[k]: v["yearly_total"] / 1e6 for k, v in s["by_strategy"].items()}
    return SHORT[s["strategy"]], tot


def main():
    print("Yillik toplam, milyon USD (A=Permanent, B=Base+CoD, C=TFP); * = kazanan")
    print("Varsayilanlar:", ", ".join(f"{n}={getattr(m, n)}" for n, _ in SWEEPS))
    for name, values in SWEEPS:
        print(f"\n{name}")
        print("  deger   | " + " | ".join(f"{p:<26}" for p in PRESETS))
        for v in values:
            with m.use_values({name: v}):
                cells = []
                for p in PRESETS:
                    win, tot = row(p)
                    cells.append(" ".join(f"{k}{'*' if k == win else ' '}{tot[k]:.3f}"
                                          for k in "ABC" if k in tot))
            print(f"  {v:<7} | " + " | ".join(f"{c:<26}" for c in cells))


if __name__ == "__main__":
    main()
