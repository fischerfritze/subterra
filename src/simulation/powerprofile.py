import numpy as np
from src.simulation.utils.paths import RESULTS_DIR, PARAMETER_FILE, TEMP_DIR, BASE_DIR
from scipy.integrate import simps
import os


def powerprofile(A: float, B: float):
    powerprofile = {}
    days = np.arange(1, 366, dtype=int)  # 1..365
    resulting_power = A - np.cos(2 * np.pi / 365 * days) * B

    powerprofile = {int(d): float(v) for d, v in zip(days, resulting_power)}

    output_dir = RESULTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    return powerprofile


def multiple_powerprofile(years: int, A: float, B: float):
    # Basis-Jahresprofil
    dict_year = powerprofile(A, B)

    # vektorisiert über mehrere Jahre erweitern
    base_vals = np.array(list(dict_year.values()), dtype=float)  # Länge 365
    total_days = years * 365
    days = np.arange(1, total_days + 1, dtype=int)
    resulting_power = np.tile(base_vals, years)

    # geordnetes Dict
    powerprofile_multi = {int(d): float(v)
                          for d, v in zip(days, resulting_power)}

    # Positive/Negative Anteile
    positive_integral = np.clip(resulting_power, 0.0, None)
    negative_integral = np.clip(resulting_power, None, 0.0)

    # Integrale
    Q_in = float(simps(positive_integral, days))
    Q_out = float(simps(negative_integral, days))

    ratio = float(np.abs(Q_out / Q_in)) if Q_in != 0.0 else float("nan")

    # Umrechnung in kWh m⁻¹
    Q_in *= 24 / 1000
    Q_out *= 24 / 1000

    # Ergebnisse ausgeben
    print(f"Q_in  = {Q_in:.0f} kWh m⁻¹")
    print(f"Q_out = {Q_out:.0f} kWh m⁻¹")
    print(f"eta   = {ratio:.2f}")

    # Save results
    output_dir = RESULTS_DIR
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "powerprofile_multi.csv")
    with open(output_path, "w") as f:
        f.write("day,power\n")
        for day, power in powerprofile_multi.items():
            f.write(f"{day},{power}\n")

    return powerprofile_multi, ratio, Q_out, Q_in
