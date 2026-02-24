#!/usr/bin/env python3
"""
convert_to_si.py

Liest eine JSON-Datei ein und wandelt alle Werte mit Einheiten in SI-Einheiten um.
Erkennt Einträge der Form {"value": <zahl>, "unit": "<einheit>"} rekursiv an beliebiger Stelle.

Beispiele:
  - °C/degC  -> K
  - h        -> s
  - day/d    -> s
  - year/yr  -> s (hier: 365 Tage)
  - cm/day   -> m/s
  - MJ/m^3/K -> J/m^3/K
  - kJ/m^3/K -> J/m^3/K
  - m, kg/m^3, J/kg/K, W/m/K, W/m, 1 bleiben erhalten

Nutzung:
  python convert_to_si.py input.json output.json
  # oder: python convert_to_si.py input.json  (schreibt auf STDOUT)
"""

import json
import re
import sys
import os

from typing import Any, Tuple

SUPERSCRIPT_MAP = {
    "²": "^2",
    "³": "^3",
}


def normalize_unit(u: str) -> str:
    if not isinstance(u, str):
        return u
    s = u.strip()
    # vereinheitlichen: Unicode-Superscripts -> ^
    for k, v in SUPERSCRIPT_MAP.items():
        s = s.replace(k, v)
    # Leerzeichen entfernen, mehrere Schrägstriche normalisieren
    s = re.sub(r"\s+", "", s)
    # °C / degC -> C
    s = s.replace("°C", "C")
    s = s.replace("degC", "C")
    # Klein-/Großschreibung vereinheitlichen für Worte
    # (aber Einheiten mit Großbuchstaben wie W, J, K beibehalten)
    # Wir behandeln nur Worte wie 'year', 'day', 'hour'
    s = re.sub(r"(?i)years?", "year", s)
    s = re.sub(r"(?i)yrs?", "year", s)
    s = re.sub(r"(?i)days?", "day", s)
    s = re.sub(r"(?i)d$", "day", s)  # 'd' alleine -> 'day'
    s = re.sub(r"(?i)hours?", "h", s)
    s = re.sub(r"(?i)hr?s?", "h", s)
    return s


def convert_value_unit(value: float, unit: str) -> Tuple[float, str]:
    """
    Konvertiert (value, unit) in SI.
    Gibt (value_si, unit_si) zurück.
    Unbekannte Einheiten bleiben unverändert.
    """
    u = normalize_unit(unit)

    # Temperatur
    if u == "K":
        return value, "K"
    if u == "C":
        return value + 273.15, "K"

    # Länge
    if u == "m":
        return value, "m"

    # Zeit
    if u == "s":
        return value, "s"
    if u == "h":
        return value * 3600.0, "s"
    if u == "day":
        return value * 86400.0, "s"
    if u == "year":
        # 365 Tage als Standard (konsistent mit 'day')
        return value * 365.0 * 86400.0, "s"

    # Dichte-Wärmekapazität: J/m^3/K
    if u == "J/m^3/K":
        return value, "J/m^3/K"
    if u == "kJ/m^3/K":
        return value * 1e3, "J/m^3/K"
    if u == "MJ/m^3/K":
        return value * 1e6, "J/m^3/K"

    # Wärmeleitfähigkeit
    if u == "W/m/K":
        return value, "W/m/K"

    # dimensionslos
    if u == "1":
        return value, "1"

    # Dichte
    if u in {"kg/m^3"}:
        return value, "kg/m^3"

    # spezifische Wärmekapazität
    if u in {"J/kg/K"}:
        return value, "J/kg/K"

    # Geschwindigkeit: cm/day -> m/s
    if u == "cm/day":
        return value * 0.01 / 86400.0, "m/s"
    if u == "m/day":
        return value / 86400.0, "m/s"
    if u == "cm/s":
        return value * 0.01, "m/s"

    # Linienleistung
    if u == "W/m":
        return value, "W/m"

    # Fallback: unbekannte Einheit – unverändert zurückgeben
    return value, unit


def convert_to_si(obj: Any) -> Any:
    """
    Durchläuft das Objekt rekursiv und konvertiert alle {value, unit}-Paare.
    """
    if isinstance(obj, dict):
        # Ist es ein {value, unit}-Objekt?
        if set(obj.keys()) >= {"value", "unit"} and isinstance(obj["unit"], (str, int, float)):
            val = obj.get("value")
            unit = obj.get("unit")
            
            if not val or not unit:
                return obj

            try:
                v_si, u_si = convert_value_unit(float(val), str(unit))
                return {"value": v_si, "unit": u_si}
            except Exception:
                # Wenn die Konvertierung fehlschlägt, original zurückgeben
                return obj
    
        else:
            return {k: convert_to_si(v) for k, v in obj.items()}
    
    elif isinstance(obj, list):
        return [convert_to_si(v) for v in obj]
    
    else:
        return obj


def run_conversion(in_path: str, out_path: str | None = None):
    """
    Führt die Konvertierung durch.
    Gibt das Ergebnis zurück.
    """
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"File not found: {in_path}")

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = convert_to_si(data)  

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result

if __name__ == "__main__":

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Nutzung: python convert_to_si.py input.json [output.json]")
        raise SystemExit("Isnufficient arguments.")
    
    in_path = sys.argv[1]
    if len(sys.argv) >= 3:
        out_path = sys.argv[2]
    else:
        out_path = None

    # Parse input file
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"File not found: {in_path}")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Perform conversion to SI
    result = convert_to_si(in_path)

    # Write output if a path is given, else print to STDOUT
    if out_path:
        with open(out_path, "w+", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
