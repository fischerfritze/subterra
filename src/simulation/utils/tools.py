# from dataclasses import dataclass, field

# TODO: Remove unused code
# @dataclass
# class SimResults:
#     # einfache Zeitreihen
#     error_result: list = field(default_factory=list)
#     E_probe_result: list = field(default_factory=list)
#     E_flux_result: list = field(default_factory=list)
#     Delta_E_result: list = field(default_factory=list)
#     E_in_out: list = field(default_factory=list)
#     Q_probe: list = field(default_factory=list)
#     E_storage: list = field(default_factory=list)
#     days: list = field(default_factory=list)

#     # pro-EWS-Daten
#     W_el_values: dict = field(default_factory=dict)
#     Temp_values: dict = field(default_factory=dict)
#     Temp_EWS_values: dict = field(default_factory=dict)

#     # ggf. Vertex-Temperaturen / andere strukturierte Outputs
#     Temp_vertex: dict = field(default_factory=dict)


def _conductivity_model_1(lamb_g, lamb_f, porosity):
    """
    Modell 1: 
    λ_eff = λ_g * (1 - [φ (1 + 2 r) (1 - r)] / [φ (1 - r) + 3 r]), r = λ_f/λ_g
    """
    if lamb_g == 0:
        raise ValueError(
            "λ_g must be non-zero to compute conductivity model 1.")

    r = lamb_f / lamb_g
    phi = porosity
    numerator = phi * (1 + 2 * r) * (1 - r)
    denominator = phi * (1 - r) + 3 * r
    return lamb_g * (1 - numerator / denominator)


def _conductivity_model_2(lamb_g, lamb_f, porosity):
    """
    Modell 2: 
    λ_eff = λ_g * (1 - [3 φ (1 - r)] / [2 + φ + r]), r = λ_f/λ_g
    """
    if lamb_g == 0:
        raise ValueError(
            "λ_g must be non-zero to compute conductivity model 2.")
    r = lamb_f / lamb_g
    phi = porosity
    return lamb_g * (1 - (3 * phi * (1 - r)) / (2 + phi + r))


def _conductivity_model_3(lamb_g, lamb_f, porosity):
    """
    Modell 3:
    λ_eff = φ λ_f + (1 - φ) λ_g
    """
    phi = porosity
    return phi * lamb_f + (1 - phi) * lamb_g


def weighted_parameter(model, ground_parameter, fluid_parameter, porosity):

    lamb_g, rho_c_g = ground_parameter
    lamb_f, rho_c_f = fluid_parameter

    if model == 1:
        lamb_eff = _conductivity_model_1(lamb_g, lamb_f, porosity)
    elif model == 2:
        lamb_eff = _conductivity_model_2(lamb_g, lamb_f, porosity)
    elif model == 3:
        lamb_eff = _conductivity_model_3(lamb_g, lamb_f, porosity)
    else:
        raise ValueError("Invalid mode. Model parameter must be 1, 2, or 3.")

    rho_c_eff = porosity * rho_c_f + (1 - porosity) * rho_c_g

    print(f"Effective thermal conductivity (λ_eff): {lamb_eff:.2f} W/(m·K)")
    print(
        f"Effective volumetric heat capacity (ρc_eff): {rho_c_eff:.2f} J/(m³·K)")

    return lamb_eff, rho_c_eff


def P_el_values(Q: float, T: float, T_H: float, delta_t: float, gamma: float):
    """
    Berechnet den COP-Wert basierend auf der übergebenen Wärmeleistung, Temperatur und Zieltemperatur.

    Args:
        Q (float): Wärmeleistung (negativ für Heizbetrieb).
        T (float): Grundtemperatur.
        T_H (float): Zieltemperatur.

    Returns:
        float: Berechneter COP-Wert, oder 0 bei nicht validen Eingaben. 
    """
    try:
        if Q < 0 and T < T_H:
            # delta_t in s; Q in W/m --> W_el in Wh/m
            W_el = Q * delta_t * (1 - T / T_H) / gamma / 3600

            # delta_temp = round(T_H - T, 4)

            # if delta_temp <= 0:
            #     raise RuntimeWarning(f"Ground temperature is higher or equal to the target temperature. (ΔT = {delta_temp})")

            # COP = T_H / delta_temp

            return W_el

        else:
            return 0 # TODO: Bad practice; better raise Exception; Is 'invalid' input expected?

    except RuntimeWarning as e:
        print(f"COP-Error: {e}")
        return 0  # Rückgabe von 0 bei Fehlern ?????
