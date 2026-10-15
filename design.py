"""
IS 800:2007 Steel Tension Member Design Engine
Deterministic calculations for steel tension members as per IS 800:2007.

Clauses Implemented:
- Clause 6.2: Design Strength due to Yielding of Gross Section (Tdg)
- Clause 6.3.1: Design Strength due to Rupture of Critical Section - Plates (Tdn)
- Clause 6.3.3: Design Strength due to Rupture of Critical Section - Single Angles (Tdn)
- Clause 6.4.1: Design Strength due to Block Shear Failure (Tdb)
- Clause 10.2: Fastener Spacing & Edge Distances
- Table 5: Partial Safety Factors for Materials (gamma_m0 = 1.10, gamma_m1 = 1.25)
"""

import math
from typing import Dict, Any, Optional, Tuple, List


# Verified Standard Steel Angles (IS 800 / SP 6(1) Rolled Steel Angles)
# Format: label: {b_c (connected leg), w (outstanding leg), t (thickness), Ag (mm^2), r_min (cm)}
STANDARD_ANGLES = {
    "ISA 50x50x5": {"b_c": 50, "w": 50, "t": 5, "Ag": 479, "r_min": 0.98},
    "ISA 50x50x6": {"b_c": 50, "w": 50, "t": 6, "Ag": 568, "r_min": 0.97},
    "ISA 65x65x6": {"b_c": 65, "w": 65, "t": 6, "Ag": 744, "r_min": 1.26},
    "ISA 65x65x8": {"b_c": 65, "w": 65, "t": 8, "Ag": 976, "r_min": 1.25},
    "ISA 75x75x6": {"b_c": 75, "w": 75, "t": 6, "Ag": 866, "r_min": 1.46},
    "ISA 75x75x8": {"b_c": 75, "w": 75, "t": 8, "Ag": 1138, "r_min": 1.45},
    "ISA 90x60x6": {"b_c": 90, "w": 60, "t": 6, "Ag": 865, "r_min": 1.30},
    "ISA 90x60x8": {"b_c": 90, "w": 60, "t": 8, "Ag": 1137, "r_min": 1.29},
    "ISA 100x75x8": {"b_c": 100, "w": 75, "t": 8, "Ag": 1336, "r_min": 1.61},
    "ISA 100x75x10": {"b_c": 100, "w": 75, "t": 10, "Ag": 1650, "r_min": 1.60},
    "ISA 100x100x8": {"b_c": 100, "w": 100, "t": 8, "Ag": 1539, "r_min": 1.95},
    "ISA 100x100x10": {"b_c": 100, "w": 100, "t": 10, "Ag": 1903, "r_min": 1.94},
    "ISA 150x115x10": {"b_c": 150, "w": 115, "t": 10, "Ag": 2552, "r_min": 2.50},
    "ISA 150x150x12": {"b_c": 150, "w": 150, "t": 12, "Ag": 3459, "r_min": 2.93},
}

# Standard Steel Grades (IS 2062:2011)
STEEL_GRADES = {
    "E250 (Fe 410 W)": {"fy": 250.0, "fu": 410.0, "description": "Standard structural steel (IS 2062)"},
    "E300 (Fe 440)": {"fy": 300.0, "fu": 440.0, "description": "Higher strength structural steel"},
    "E350 (Fe 490)": {"fy": 350.0, "fu": 490.0, "description": "High yield strength structural steel"},
    "E410 (Fe 540)": {"fy": 410.0, "fu": 540.0, "description": "Extra high yield structural steel"},
    "Custom Grade": {"fy": 250.0, "fu": 410.0, "description": "User defined strength properties"},
}


def get_standard_hole_diameter(bolt_diameter: float) -> float:
    """
    Standard clearance hole diameter as per IS 800:2007 Table 19.
    d <= 14 mm: hole = d + 1.0 mm
    16 <= d <= 24 mm: hole = d + 2.0 mm
    d > 24 mm: hole = d + 3.0 mm
    """
    if bolt_diameter <= 14.0:
        return bolt_diameter + 1.0
    elif bolt_diameter <= 24.0:
        return bolt_diameter + 2.0
    else:
        return bolt_diameter + 3.0


def calc_gross_yielding(Ag: float, fy: float, gamma_m0: float = 1.10) -> Dict[str, Any]:
    """
    Calculates design tensile strength due to yielding of gross section (IS 800:2007 Cl 6.2).
    Equation: Tdg = (Ag * fy) / gamma_m0
    """
    if Ag <= 0 or fy <= 0 or gamma_m0 <= 0:
        raise ValueError("Ag, fy, and gamma_m0 must be strictly positive.")
    
    Tdg_N = (Ag * fy) / gamma_m0
    Tdg_kN = Tdg_N / 1000.0
    
    return {
        "limit_state": "Gross Section Yielding",
        "clause": "IS 800:2007 Clause 6.2",
        "formula": r"T_{dg} = \frac{A_g \cdot f_y}{\gamma_{m0}}",
        "substitution": f"({Ag:.1f} × {fy:.1f}) / {gamma_m0:.2f}",
        "Ag_mm2": Ag,
        "fy_MPa": fy,
        "gamma_m0": gamma_m0,
        "Tdg_N": Tdg_N,
        "Tdg_kN": Tdg_kN,
        "description": "Yielding of the overall gross area prevents excessive permanent elongation."
    }


def calc_plate_net_rupture(
    width: float,
    thickness: float,
    n_holes: int,
    dh: float,
    fu: float,
    gamma_m1: float = 1.25,
    staggered_terms: Optional[List[Tuple[float, float]]] = None
) -> Dict[str, Any]:
    """
    Calculates design tensile strength due to net-section rupture of a plate (IS 800:2007 Cl 6.3.1).
    Equation: Tdn = 0.9 * An * fu / gamma_m1
    An = [b - n * dh + sum(psi^2 / (4 * gi))] * t
    """
    if width <= 0 or thickness <= 0 or fu <= 0 or gamma_m1 <= 0:
        raise ValueError("Dimensions and material strengths must be strictly positive.")
    if dh < 0 or n_holes < 0:
        raise ValueError("Hole dimensions and count cannot be negative.")
    
    stagger_sum = 0.0
    stagger_desc = ""
    if staggered_terms and len(staggered_terms) > 0:
        for p_s, g in staggered_terms:
            if g > 0:
                stagger_sum += (p_s ** 2) / (4.0 * g)
        stagger_desc = f" + ∑(p_s² / 4g) [{stagger_sum:.2f} mm]"
        
    net_width = width - (n_holes * dh) + stagger_sum
    if net_width <= 0:
        raise ValueError(f"Net plate width is non-positive ({net_width:.2f} mm). Hole diameter or count exceeds plate width.")
    
    An = net_width * thickness
    Tdn_N = (0.9 * An * fu) / gamma_m1
    Tdn_kN = Tdn_N / 1000.0
    
    substitution = f"0.9 × {An:.1f} × {fu:.1f} / {gamma_m1:.2f}"
    
    return {
        "limit_state": "Net Section Rupture (Plate)",
        "clause": "IS 800:2007 Clause 6.3.1",
        "formula": r"T_{dn} = \frac{0.9 \cdot A_n \cdot f_u}{\gamma_{m1}}",
        "net_area_formula": r"A_n = \left( b - n \cdot d_h + \sum \frac{p_{si}^2}{4 g_i} \right) \cdot t",
        "net_area_derivation": f"({width:.1f} - {n_holes} × {dh:.1f}{stagger_desc}) × {thickness:.1f} = {An:.1f} mm²",
        "substitution": substitution,
        "width_mm": width,
        "thickness_mm": thickness,
        "n_holes": n_holes,
        "dh_mm": dh,
        "An_mm2": An,
        "fu_MPa": fu,
        "gamma_m1": gamma_m1,
        "Tdn_N": Tdn_N,
        "Tdn_kN": Tdn_kN,
        "description": "Rupture fracture across the critical net cross-section weakened by bolt holes."
    }


def calc_single_angle_net_rupture_is800(
    b_c: float,
    w: float,
    t: float,
    dh: float,
    fy: float,
    fu: float,
    n_bolts_along_length: int,
    pitch: float,
    end_dist: float,
    w1: float,
    gamma_m0: float = 1.10,
    gamma_m1: float = 1.25,
    n_holes_critical: int = 1
) -> Dict[str, Any]:
    """
    Calculates design tensile strength of single angle connected through one leg (IS 800:2007 Cl 6.3.3).
    Equation: Tdn = 0.9 * Anc * fu / gamma_m1 + beta * Ago * fy / gamma_m0
    where:
    beta = 1.4 - 0.076 * (w / t) * (fy / fu) * (bs / Lc)
    Limits: 0.7 <= beta <= (fu * gamma_m0) / (fy * gamma_m1)
    bs = w + w1 - t (for bolted connection)
    Lc = length of connection between first and last bolt in direction of load = (n_bolts_along_length - 1) * pitch
    Anc = net area of connected leg = (b_c - n_holes_critical * dh - t / 2) * t
    Ago = gross area of outstanding leg = (w - t / 2) * t
    """
    if b_c <= 0 or w <= 0 or t <= 0 or fy <= 0 or fu <= 0:
        raise ValueError("Dimensions and strengths must be strictly positive.")
    if t >= b_c or t >= w:
        raise ValueError("Angle thickness cannot be greater than or equal to leg dimensions.")
    
    # Connected leg net area
    Anc = (b_c - n_holes_critical * dh - t / 2.0) * t
    if Anc <= 0:
        raise ValueError(f"Net area of connected leg Anc is non-positive ({Anc:.1f} mm²). Hole diameter exceeds leg width.")
    
    # Outstanding leg gross area
    Ago = (w - t / 2.0) * t
    
    # Shear lag width bs
    bs = w + w1 - t
    if bs <= 0:
        raise ValueError("Shear lag distance bs must be positive.")
    
    # Length of connection Lc
    if n_bolts_along_length > 1 and pitch > 0:
        Lc = (n_bolts_along_length - 1) * pitch
        beta_raw = 1.4 - 0.076 * (w / t) * (fy / fu) * (bs / Lc)
        beta_upper = (fu * gamma_m0) / (fy * gamma_m1)
        beta_lower = 0.70
        beta = max(beta_lower, min(beta_raw, beta_upper))
        beta_status = f"Calculated β = {beta_raw:.3f}, constrained to [{beta_lower:.2f}, {beta_upper:.3f}] → β = {beta:.3f}"
    else:
        # Fallback for 1 bolt: Lc is effectively zero, IS 800 simplified method alpha applies
        Lc = pitch if pitch > 0 else 2.5 * (dh - 2.0)
        alpha = 0.60
        beta = 0.70
        beta_status = f"Single bolt connection: shear lag factor β defaulted to minimum {beta:.2f} (simplified α = {alpha} applies)"

    Tdn_connected_N = (0.9 * Anc * fu) / gamma_m1
    Tdn_outstanding_N = (beta * Ago * fy) / gamma_m0
    Tdn_N = Tdn_connected_N + Tdn_outstanding_N
    Tdn_kN = Tdn_N / 1000.0
    
    # Also compute simplified method for comparison (Cl 6.3.3 note):
    # Tdn = alpha * An * fu / gamma_m1
    An_total = Anc + Ago
    if n_bolts_along_length <= 2:
        alpha = 0.6
    elif n_bolts_along_length == 3:
        alpha = 0.7
    else:
        alpha = 0.8
    Tdn_simplified_N = (alpha * An_total * fu) / gamma_m1
    Tdn_simplified_kN = Tdn_simplified_N / 1000.0

    return {
        "limit_state": "Net Section Rupture (Single Angle)",
        "clause": "IS 800:2007 Clause 6.3.3",
        "formula": r"T_{dn} = \frac{0.9 \cdot A_{nc} \cdot f_u}{\gamma_{m1}} + \frac{\beta \cdot A_{go} \cdot f_y}{\gamma_{m0}}",
        "beta_formula": r"\beta = 1.4 - 0.076 \cdot \left(\frac{w}{t}\right)\left(\frac{f_y}{f_u}\right)\left(\frac{b_s}{L_c}\right)",
        "Anc_mm2": Anc,
        "Ago_mm2": Ago,
        "bs_mm": bs,
        "Lc_mm": Lc,
        "beta": beta,
        "beta_notes": beta_status,
        "Tdn_connected_kN": Tdn_connected_N / 1000.0,
        "Tdn_outstanding_kN": Tdn_outstanding_N / 1000.0,
        "Tdn_N": Tdn_N,
        "Tdn_kN": Tdn_kN,
        "simplified_alpha": alpha,
        "simplified_Tdn_kN": Tdn_simplified_kN,
        "substitution": f"(0.9 × {Anc:.1f} × {fu:.1f} / {gamma_m1:.2f}) + ({beta:.3f} × {Ago:.1f} × {fy:.1f} / {gamma_m0:.2f})",
        "description": "Accounts for shear lag where tension in the unconnected outstanding leg is transferred non-uniformly."
    }


def calc_block_shear(
    Avg: float,
    Avn: float,
    Atg: float,
    Atn: float,
    fy: float,
    fu: float,
    gamma_m0: float = 1.10,
    gamma_m1: float = 1.25
) -> Dict[str, Any]:
    """
    Calculates design strength due to block shear failure as per IS 800:2007 Cl 6.4.1.
    Tdb1 = (Avg * fy) / (sqrt(3) * gamma_m0) + (0.9 * Atn * fu) / gamma_m1
    Tdb2 = (0.9 * Avn * fu) / (sqrt(3) * gamma_m1) + (Atg * fy) / gamma_m0
    Tdb = min(Tdb1, Tdb2)
    """
    if Avg <= 0 or Avn <= 0 or Atg <= 0 or Atn <= 0:
        raise ValueError("Block shear areas (Avg, Avn, Atg, Atn) must be strictly positive.")
    if Avn > Avg or Atn > Atg:
        raise ValueError("Net areas cannot be greater than gross areas.")
    if fy <= 0 or fu <= 0:
        raise ValueError("Material strengths must be strictly positive.")

    # Tdb1: Shear yielding + Tension rupture
    term_vg_N = (Avg * fy) / (math.sqrt(3.0) * gamma_m0)
    term_tn_N = (0.9 * Atn * fu) / gamma_m1
    Tdb1_N = term_vg_N + term_tn_N
    Tdb1_kN = Tdb1_N / 1000.0

    # Tdb2: Shear rupture + Tension yielding
    term_vn_N = (0.9 * Avn * fu) / (math.sqrt(3.0) * gamma_m1)
    term_tg_N = (Atg * fy) / gamma_m0
    Tdb2_N = term_vn_N + term_tg_N
    Tdb2_kN = Tdb2_N / 1000.0

    Tdb_N = min(Tdb1_N, Tdb2_N)
    Tdb_kN = Tdb_N / 1000.0
    governing_eqn = "Tdb1 (Shear Yielding + Tension Rupture)" if Tdb1_N <= Tdb2_N else "Tdb2 (Shear Rupture + Tension Yielding)"

    return {
        "limit_state": "Block Shear Failure",
        "clause": "IS 800:2007 Clause 6.4.1",
        "formula_Tdb1": r"T_{db1} = \frac{A_{vg} \cdot f_y}{\sqrt{3}\gamma_{m0}} + \frac{0.9 A_{tn} f_u}{\gamma_{m1}}",
        "formula_Tdb2": r"T_{db2} = \frac{0.9 A_{vn} f_u}{\sqrt{3}\gamma_{m1}} + \frac{A_{tg} f_y}{\gamma_{m0}}",
        "Avg_mm2": Avg,
        "Avn_mm2": Avn,
        "Atg_mm2": Atg,
        "Atn_mm2": Atn,
        "Tdb1_kN": Tdb1_kN,
        "Tdb2_kN": Tdb2_kN,
        "Tdb_kN": Tdb_kN,
        "governing_equation": governing_eqn,
        "substitution_Tdb1": f"({Avg:.1f} × {fy:.1f} / (√3 × {gamma_m0:.2f})) + (0.9 × {Atn:.1f} × {fu:.1f} / {gamma_m1:.2f}) = {Tdb1_kN:.2f} kN",
        "substitution_Tdb2": f"(0.9 × {Avn:.1f} × {fu:.1f} / (√3 × {gamma_m1:.2f})) + ({Atg:.1f} × {fy:.1f} / {gamma_m0:.2f}) = {Tdb2_kN:.2f} kN",
        "description": "Failure mode where a block of steel tears out at the end connection along combined shear and tension planes."
    }


def calc_plate_connection_block_shear_geometry(
    width: float,
    thickness: float,
    n_rows: int,
    n_cols: int,
    pitch: float,
    gauge: float,
    end_dist: float,
    edge_dist: float,
    dh: float
) -> Dict[str, float]:
    """
    Derives gross and net shear and tension areas for a flat plate end connection.
    Standard block shear path:
    - n_rows: number of bolt lines parallel to tension force (shear lines).
    - n_cols: number of bolts per line in direction of tension force.
    - If n_rows == 1:
      Shear failure path along 1 line:
      Avg = [(n_cols - 1) * pitch + end_dist] * thickness
      Avn = [(n_cols - 1) * pitch + end_dist - (n_cols - 0.5) * dh] * thickness
      Tension failure path from line to closer edge:
      Atg = edge_dist * thickness
      Atn = (edge_dist - 0.5 * dh) * thickness
    - If n_rows >= 2:
      Block tearing out between outer bolt lines or to edges:
      Two outer shear planes:
      Length of each shear plane = (n_cols - 1) * pitch + end_dist
      Avg = 2 * [(n_cols - 1) * pitch + end_dist] * thickness
      Avn = 2 * [(n_cols - 1) * pitch + end_dist - (n_cols - 0.5) * dh] * thickness
      Tension plane between the outermost bolt lines:
      Tension length = (n_rows - 1) * gauge
      Atg = (n_rows - 1) * gauge * thickness
      Atn = [(n_rows - 1) * gauge - (n_rows - 1) * dh] * thickness
    """
    if n_cols < 1 or n_rows < 1:
        raise ValueError("Must have at least 1 bolt column and 1 bolt row.")
    
    shear_len = (n_cols - 1) * pitch + end_dist
    
    if n_rows == 1:
        Avg = shear_len * thickness
        Avn = (shear_len - (n_cols - 0.5) * dh) * thickness
        Atg = edge_dist * thickness
        Atn = (edge_dist - 0.5 * dh) * thickness
    else:
        # Two shear planes on both sides of the inner block
        Avg = 2.0 * shear_len * thickness
        Avn = 2.0 * (shear_len - (n_cols - 0.5) * dh) * thickness
        tension_len = (n_rows - 1) * gauge
        Atg = tension_len * thickness
        # There are (n_rows - 1) intervals, bolt holes deducted at boundary = 2 * (0.5 * dh) + (n_rows - 2) * dh = (n_rows - 1) * dh
        Atn = (tension_len - (n_rows - 1) * dh) * thickness

    if Avn <= 0 or Atn <= 0:
        raise ValueError(f"Derived net block shear area is non-positive (Avn={Avn:.1f}, Atn={Atn:.1f}). Check bolt spacing and hole size.")

    return {
        "Avg": Avg,
        "Avn": Avn,
        "Atg": Atg,
        "Atn": Atn,
        "shear_length": shear_len,
        "tension_length": edge_dist if n_rows == 1 else (n_rows - 1) * gauge
    }


def calc_angle_connection_block_shear_geometry(
    b_c: float,
    thickness: float,
    n_cols: int,
    pitch: float,
    end_dist: float,
    w1: float,
    dh: float
) -> Dict[str, float]:
    """
    Derives gross and net shear and tension areas for a single angle connected by one leg.
    Usually 1 line of bolts along the connected leg:
    - Shear line along bolt line:
      shear_length = (n_cols - 1) * pitch + end_dist
      Avg = shear_length * thickness
      Avn = [shear_length - (n_cols - 0.5) * dh] * thickness
    - Tension line from bolt line to the outer edge of connected leg:
      tension_length = b_c - w1 (edge distance to outer toe) or w1 (edge distance to heel)
      Let e_t = min(w1, b_c - w1) or user-specified edge distance.
      Atg = e_t * thickness
      Atn = (e_t - 0.5 * dh) * thickness
    """
    shear_len = (n_cols - 1) * pitch + end_dist
    e_t = b_c - w1 if (b_c - w1) > 0 else w1
    
    Avg = shear_len * thickness
    Avn = (shear_len - (n_cols - 0.5) * dh) * thickness
    Atg = e_t * thickness
    Atn = (e_t - 0.5 * dh) * thickness

    if Avn <= 0 or Atn <= 0:
        raise ValueError(f"Angle block shear net area is non-positive (Avn={Avn:.1f}, Atn={Atn:.1f}). Check bolt arrangement.")

    return {
        "Avg": Avg,
        "Avn": Avn,
        "Atg": Atg,
        "Atn": Atn,
        "shear_length": shear_len,
        "tension_length": e_t
    }


def perform_complete_tension_design(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs full deterministic tension member design according to IS 800:2007.
    Aggregates all limit states, finds governing strength, utilization ratio, and status.
    """
    section_type = inputs.get("section_type", "Flat Plate")
    Tu_kN = float(inputs.get("Tu_kN", 100.0))
    fy = float(inputs.get("fy", 250.0))
    fu = float(inputs.get("fu", 410.0))
    gamma_m0 = float(inputs.get("gamma_m0", 1.10))
    gamma_m1 = float(inputs.get("gamma_m1", 1.25))
    has_holes = inputs.get("has_holes", True)
    
    results: Dict[str, Any] = {
        "inputs": inputs,
        "section_type": section_type,
        "Tu_kN": Tu_kN,
        "fy": fy,
        "fu": fu,
        "gamma_m0": gamma_m0,
        "gamma_m1": gamma_m1,
        "limit_states": {},
        "governing_strength_kN": 0.0,
        "governing_limit_state": "",
        "utilization_ratio": 0.0,
        "status": "INCOMPLETE",
        "calculation_steps": [],
        "warnings": [],
        "assumptions": []
    }

    # 1. Gross Area & Gross Yielding (Cl 6.2)
    if section_type == "Flat Plate":
        width = float(inputs["width"])
        thickness = float(inputs["thickness"])
        Ag = width * thickness
        results["Ag_mm2"] = Ag
        results["assumptions"].append(f"Flat plate section: {width:.1f} mm × {thickness:.1f} mm, Ag = {Ag:.1f} mm².")
    elif section_type == "Single Angle":
        b_c = float(inputs["b_c"])
        w = float(inputs["w"])
        thickness = float(inputs["thickness"])
        # If user selected standard angle or custom
        Ag_provided = inputs.get("Ag")
        Ag = float(Ag_provided) if Ag_provided else (b_c + w - thickness) * thickness
        results["Ag_mm2"] = Ag
        results["assumptions"].append(f"Single angle section: ISA {b_c:.0f}×{w:.0f}×{thickness:.0f}, Ag = {Ag:.1f} mm².")
    elif section_type == "Double Angles":
        b_c = float(inputs["b_c"])
        w = float(inputs["w"])
        thickness = float(inputs["thickness"])
        Ag_provided = inputs.get("Ag_single")
        Ag_single = float(Ag_provided) if Ag_provided else (b_c + w - thickness) * thickness
        Ag = 2.0 * Ag_single
        results["Ag_mm2"] = Ag
        results["assumptions"].append(f"Double angles back-to-back: 2 × ISA {b_c:.0f}×{w:.0f}×{thickness:.0f}, Total Ag = {Ag:.1f} mm².")
    else:
        raise ValueError(f"Unsupported section type: {section_type}")

    # Calculate Tdg
    res_yielding = calc_gross_yielding(Ag, fy, gamma_m0)
    results["limit_states"]["gross_yielding"] = res_yielding
    strengths_to_compare = [("Gross Section Yielding (Cl 6.2)", res_yielding["Tdg_kN"])]
    
    results["calculation_steps"].append({
        "parameter": "Gross Section Yielding (Tdg)",
        "clause": "IS 800:2007 Cl 6.2",
        "formula": res_yielding["formula"],
        "substitution": res_yielding["substitution"],
        "result": f"{res_yielding['Tdg_kN']:.2f}",
        "unit": "kN"
    })

    # 2. Net Section Rupture (Cl 6.3)
    if has_holes:
        d_bolt = float(inputs.get("d_bolt", 16.0))
        dh = float(inputs.get("dh", get_standard_hole_diameter(d_bolt)))
        
        if section_type == "Flat Plate":
            n_holes_critical = int(inputs.get("n_holes_critical", 1))
            staggered = inputs.get("staggered", False)
            stagger_terms = inputs.get("stagger_terms", None) if staggered else None
            
            res_rupture = calc_plate_net_rupture(
                width=width,
                thickness=thickness,
                n_holes=n_holes_critical,
                dh=dh,
                fu=fu,
                gamma_m1=gamma_m1,
                staggered_terms=stagger_terms
            )
            results["limit_states"]["net_rupture"] = res_rupture
            results["An_mm2"] = res_rupture["An_mm2"]
            strengths_to_compare.append(("Net Section Rupture (Cl 6.3.1)", res_rupture["Tdn_kN"]))
            
            results["calculation_steps"].append({
                "parameter": "Net Section Rupture (Tdn)",
                "clause": "IS 800:2007 Cl 6.3.1",
                "formula": res_rupture["formula"],
                "substitution": res_rupture["substitution"],
                "result": f"{res_rupture['Tdn_kN']:.2f}",
                "unit": "kN"
            })
            
        elif section_type == "Single Angle":
            n_bolts_along = int(inputs.get("n_cols", 2))
            pitch = float(inputs.get("pitch", 50.0))
            end_dist = float(inputs.get("end_dist", 35.0))
            w1 = float(inputs.get("w1", b_c / 2.0))
            n_holes_critical = int(inputs.get("n_holes_critical", 1))
            
            res_rupture = calc_single_angle_net_rupture_is800(
                b_c=b_c,
                w=w,
                t=thickness,
                dh=dh,
                fy=fy,
                fu=fu,
                n_bolts_along_length=n_bolts_along,
                pitch=pitch,
                end_dist=end_dist,
                w1=w1,
                gamma_m0=gamma_m0,
                gamma_m1=gamma_m1,
                n_holes_critical=n_holes_critical
            )
            results["limit_states"]["net_rupture"] = res_rupture
            results["An_mm2"] = res_rupture["Anc_mm2"] + res_rupture["Ago_mm2"]
            strengths_to_compare.append(("Net Section Rupture (Cl 6.3.3)", res_rupture["Tdn_kN"]))
            
            results["calculation_steps"].append({
                "parameter": "Net Section Rupture with Shear Lag (Tdn)",
                "clause": "IS 800:2007 Cl 6.3.3",
                "formula": res_rupture["formula"],
                "substitution": res_rupture["substitution"],
                "result": f"{res_rupture['Tdn_kN']:.2f}",
                "unit": "kN"
            })
            
        elif section_type == "Double Angles":
            # For double angles connected on opposite sides of gusset plate with tack bolts:
            # Shear lag factor applies to each angle; or when connected on opposite sides,
            # each angle resists half the load.
            n_bolts_along = int(inputs.get("n_cols", 2))
            pitch = float(inputs.get("pitch", 50.0))
            end_dist = float(inputs.get("end_dist", 35.0))
            w1 = float(inputs.get("w1", b_c / 2.0))
            n_holes_critical = int(inputs.get("n_holes_critical", 1))
            
            res_single_angle = calc_single_angle_net_rupture_is800(
                b_c=b_c,
                w=w,
                t=thickness,
                dh=dh,
                fy=fy,
                fu=fu,
                n_bolts_along_length=n_bolts_along,
                pitch=pitch,
                end_dist=end_dist,
                w1=w1,
                gamma_m0=gamma_m0,
                gamma_m1=gamma_m1,
                n_holes_critical=n_holes_critical
            )
            Tdn_total_kN = 2.0 * res_single_angle["Tdn_kN"]
            res_rupture = {
                **res_single_angle,
                "Tdn_single_kN": res_single_angle["Tdn_kN"],
                "Tdn_kN": Tdn_total_kN,
                "clause": "IS 800:2007 Cl 6.3.3 (2 Angles)",
                "substitution": f"2 × [{res_single_angle['substitution']}]"
            }
            results["limit_states"]["net_rupture"] = res_rupture
            results["An_mm2"] = 2.0 * (res_single_angle["Anc_mm2"] + res_single_angle["Ago_mm2"])
            strengths_to_compare.append(("Net Section Rupture - 2 Angles (Cl 6.3.3)", Tdn_total_kN))
            
            results["calculation_steps"].append({
                "parameter": "Double Angle Net Rupture (Tdn)",
                "clause": "IS 800:2007 Cl 6.3.3 & Cl 6.3.4",
                "formula": r"T_{dn} = 2 \times T_{dn,\text{single}}",
                "substitution": res_rupture["substitution"],
                "result": f"{Tdn_total_kN:.2f}",
                "unit": "kN"
            })
    else:
        results["assumptions"].append("Plain member without fastener holes: Rupture check not critical / An = Ag.")
        results["An_mm2"] = Ag

    # 3. Block Shear Failure (Cl 6.4.1)
    check_block_shear = inputs.get("check_block_shear", True) and has_holes
    if check_block_shear:
        d_bolt = float(inputs.get("d_bolt", 16.0))
        dh = float(inputs.get("dh", get_standard_hole_diameter(d_bolt)))
        pitch = float(inputs.get("pitch", 50.0))
        end_dist = float(inputs.get("end_dist", 35.0))
        n_cols = int(inputs.get("n_cols", 2))
        
        try:
            if section_type == "Flat Plate":
                n_rows = int(inputs.get("n_rows", 1))
                gauge = float(inputs.get("gauge", 50.0))
                edge_dist = float(inputs.get("edge_dist", 35.0))
                geo = calc_plate_connection_block_shear_geometry(
                    width=width,
                    thickness=thickness,
                    n_rows=n_rows,
                    n_cols=n_cols,
                    pitch=pitch,
                    gauge=gauge,
                    end_dist=end_dist,
                    edge_dist=edge_dist,
                    dh=dh
                )
                res_block = calc_block_shear(
                    Avg=geo["Avg"],
                    Avn=geo["Avn"],
                    Atg=geo["Atg"],
                    Atn=geo["Atn"],
                    fy=fy,
                    fu=fu,
                    gamma_m0=gamma_m0,
                    gamma_m1=gamma_m1
                )
                res_block["geometry"] = geo
                results["limit_states"]["block_shear"] = res_block
                strengths_to_compare.append(("Block Shear Strength (Cl 6.4.1)", res_block["Tdb_kN"]))
                
                results["calculation_steps"].append({
                    "parameter": "Block Shear Strength (Tdb)",
                    "clause": "IS 800:2007 Cl 6.4.1",
                    "formula": r"T_{db} = \min(T_{db1}, T_{db2})",
                    "substitution": f"min({res_block['Tdb1_kN']:.2f}, {res_block['Tdb2_kN']:.2f})",
                    "result": f"{res_block['Tdb_kN']:.2f}",
                    "unit": "kN"
                })

            elif section_type == "Single Angle":
                w1 = float(inputs.get("w1", b_c / 2.0))
                geo = calc_angle_connection_block_shear_geometry(
                    b_c=b_c,
                    thickness=thickness,
                    n_cols=n_cols,
                    pitch=pitch,
                    end_dist=end_dist,
                    w1=w1,
                    dh=dh
                )
                res_block = calc_block_shear(
                    Avg=geo["Avg"],
                    Avn=geo["Avn"],
                    Atg=geo["Atg"],
                    Atn=geo["Atn"],
                    fy=fy,
                    fu=fu,
                    gamma_m0=gamma_m0,
                    gamma_m1=gamma_m1
                )
                res_block["geometry"] = geo
                results["limit_states"]["block_shear"] = res_block
                strengths_to_compare.append(("Block Shear Strength (Cl 6.4.1)", res_block["Tdb_kN"]))
                
                results["calculation_steps"].append({
                    "parameter": "Block Shear Strength (Tdb)",
                    "clause": "IS 800:2007 Cl 6.4.1",
                    "formula": r"T_{db} = \min(T_{db1}, T_{db2})",
                    "substitution": f"min({res_block['Tdb1_kN']:.2f}, {res_block['Tdb2_kN']:.2f})",
                    "result": f"{res_block['Tdb_kN']:.2f}",
                    "unit": "kN"
                })
                
            elif section_type == "Double Angles":
                w1 = float(inputs.get("w1", b_c / 2.0))
                geo_single = calc_angle_connection_block_shear_geometry(
                    b_c=b_c,
                    thickness=thickness,
                    n_cols=n_cols,
                    pitch=pitch,
                    end_dist=end_dist,
                    w1=w1,
                    dh=dh
                )
                # Two angles: total block shear is 2x single angle connection
                res_single_block = calc_block_shear(
                    Avg=geo_single["Avg"],
                    Avn=geo_single["Avn"],
                    Atg=geo_single["Atg"],
                    Atn=geo_single["Atn"],
                    fy=fy,
                    fu=fu,
                    gamma_m0=gamma_m0,
                    gamma_m1=gamma_m1
                )
                Tdb_total_kN = 2.0 * res_single_block["Tdb_kN"]
                res_block = {
                    **res_single_block,
                    "Tdb1_kN": 2.0 * res_single_block["Tdb1_kN"],
                    "Tdb2_kN": 2.0 * res_single_block["Tdb2_kN"],
                    "Tdb_kN": Tdb_total_kN,
                    "geometry": {k: 2.0 * v if "A" in k else v for k, v in geo_single.items()}
                }
                results["limit_states"]["block_shear"] = res_block
                strengths_to_compare.append(("Block Shear Strength - 2 Angles (Cl 6.4.1)", Tdb_total_kN))
                
                results["calculation_steps"].append({
                    "parameter": "Double Angle Block Shear (Tdb)",
                    "clause": "IS 800:2007 Cl 6.4.1",
                    "formula": r"T_{db} = 2 \times \min(T_{db1}, T_{db2})",
                    "substitution": f"2 × {res_single_block['Tdb_kN']:.2f}",
                    "result": f"{Tdb_total_kN:.2f}",
                    "unit": "kN"
                })

        except Exception as e:
            results["warnings"].append(f"Block shear calculation bypassed or invalid: {str(e)}")

    # 4. Governing Strength & Utilization
    min_limit_state, min_strength = min(strengths_to_compare, key=lambda x: x[1])
    results["governing_strength_kN"] = min_strength
    results["governing_limit_state"] = min_limit_state
    
    if min_strength > 0:
        utilization = Tu_kN / min_strength
        results["utilization_ratio"] = utilization
        results["status"] = "PASS" if utilization <= 1.0 else "FAIL"
    else:
        results["utilization_ratio"] = 0.0
        results["status"] = "INCOMPLETE"

    # Add governing summary to step table
    results["calculation_steps"].append({
        "parameter": "Governing Design Tensile Strength (Td)",
        "clause": "IS 800:2007 Cl 6.1",
        "formula": r"T_d = \min(T_{dg}, T_{dn}, T_{db})",
        "substitution": f"min({', '.join([f'{s[1]:.2f}' for s in strengths_to_compare])})",
        "result": f"{min_strength:.2f}",
        "unit": "kN"
    })
    
    results["calculation_steps"].append({
        "parameter": "Utilization Ratio (UR)",
        "clause": "Demand / Capacity Check",
        "formula": r"\text{UR} = \frac{T_u}{T_d}",
        "substitution": f"{Tu_kN:.2f} / {min_strength:.2f}",
        "result": f"{results['utilization_ratio']:.3f}",
        "unit": "-"
    })

    return results


def generate_educational_explanation(design_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based educational AI-style explanation generator.
    Translates mathematical outputs into crystal-clear civil engineering reasoning.
    """
    Tu = design_result["Tu_kN"]
    Td = design_result["governing_strength_kN"]
    ur = design_result["utilization_ratio"]
    status = design_result["status"]
    governing = design_result["governing_limit_state"]
    sec_type = design_result["section_type"]
    limit_states = design_result["limit_states"]
    
    insights: List[str] = []
    recommendations: List[str] = []

    # 1. Primary governing diagnosis
    if "Gross Section Yielding" in governing:
        insights.append(
            f"The member capacity is governed by **Gross Section Yielding** ($T_{{dg}} = {Td:.2f}$ kN). "
            f"This occurs when the uniform tensile stress throughout the unreduced cross-sectional area reaches "
            f"the design yield strength ($f_y / \\gamma_{{m0}}$). Ductile yielding over the entire length would cause "
            f"excessive elongation before connection fracture occurs, which is generally a desirable ductile failure mode."
        )
    elif "Net Section Rupture" in governing:
        insights.append(
            f"The design tensile strength is governed by **Net Section Rupture** ($T_{{dn}} = {Td:.2f}$ kN). "
            f"This represents local fracture at the critical net cross-section weakened by bolt holes. "
            f"Because ultimate tensile strength ($f_u$) governs with a higher partial safety factor ($\\gamma_{{m1}} = 1.25$), "
            f"the stress concentration around holes limits the capacity before the gross section can fully yield."
        )
        if sec_type in ["Single Angle", "Double Angles"]:
            insights.append(
                "Because an angle is connected through one leg only, **shear lag** reduces the effective capacity. "
                "The outstanding leg receives tensile stress indirectly through shear transfer at the angle corner, "
                "represented by the reduction factor $\\beta$."
            )
    elif "Block Shear" in governing:
        insights.append(
            f"The connection strength is governed by **Block Shear Failure** ($T_{{db}} = {Td:.2f}$ kN). "
            f"In this mode, a polygonal 'block' of steel tears out at the end connection along simultaneous longitudinal shear planes "
            f"and a transverse tension plane. Block shear governs when bolt pitch or end distance is relatively small."
        )

    # 2. Demand vs Capacity status
    if status == "PASS":
        reserve = (1.0 - ur) * 100.0
        if ur < 0.50:
            insights.append(
                f"The member is substantially **over-designed** with a utilization ratio of only {ur:.1%} (Reserve Capacity: {reserve:.1f}%). "
                f"While completely safe under the factored load of {Tu:.1f} kN, this design is structurally inefficient and increases material weight and cost."
            )
            recommendations.append("Consider reducing the plate thickness or choosing a smaller standard angle to optimize member economy.")
        elif ur <= 0.85:
            insights.append(
                f"The design is in the **optimal engineering range** (Utilization = {ur:.1%}, Reserve = {reserve:.1f}%). "
                f"It comfortably resists the factored tensile force of {Tu:.1f} kN while maintaining good material economy and safety margin."
            )
            recommendations.append("The current cross-section and connection configuration are well-balanced.")
        else:
            insights.append(
                f"The design is **close to maximum capacity** (Utilization = {ur:.1%}, Reserve = {reserve:.1f}%). "
                f"While formally passing ($T_u \\le T_d$), ensure there are no secondary bending moments or unexpected load increases."
            )
            recommendations.append("Verify whether load combinations or wind/seismic reversals require a higher safety margin.")
    else:
        overload = (ur - 1.0) * 100.0
        insights.append(
            f"🚨 **DESIGN FAILS**: The applied factored force of {Tu:.1f} kN exceeds the design capacity of {Td:.2f} kN "
            f"by {overload:.1f}% (Utilization Ratio = {ur:.3f} > 1.000)."
        )
        if "Gross Section Yielding" in governing:
            recommendations.append("Increase the cross-sectional area (Ag) by increasing member thickness or width.")
            recommendations.append("Alternatively, upgrade to a higher steel grade with higher yield stress (e.g., E350 or E410).")
        elif "Net Section Rupture" in governing:
            recommendations.append("Increase plate width or leg thickness to enlarge the net area (An).")
            recommendations.append("Stagger the bolt layout or use fewer bolts per critical cross-section to reduce hole deductions.")
            recommendations.append("For angles, increase the connection length (Lc) to reduce the shear lag penalty (improve β).")
        elif "Block Shear" in governing:
            recommendations.append("Increase the longitudinal bolt pitch (p) to lengthen the shear resistance plane.")
            recommendations.append("Increase the end distance (e) or edge distance (e_t) to enlarge both shear and tension paths.")

    # 3. Connection geometric efficiency check
    if "gross_yielding" in limit_states and "net_rupture" in limit_states:
        Tdg = limit_states["gross_yielding"]["Tdg_kN"]
        Tdn = limit_states["net_rupture"]["Tdn_kN"]
        eff = (Tdn / Tdg) * 100.0
        insights.append(
            f"Connection Efficiency Index ($T_{{dn}} / T_{{dg}}$): **{eff:.1f}%**. "
            f"A higher percentage (ideally > 85%) indicates that bolt holes do not penalize the parent member excessively."
        )

    return {
        "summary": " ".join(insights[:2]),
        "detailed_insights": insights,
        "recommendations": recommendations,
        "governing_limit_state": governing,
        "utilization_percentage": f"{ur * 100.0:.1f}%",
        "status": status
    }
