"""
Automated Unit Tests for IS 800:2007 Steel Tension Member Calculations
Independent hand-calculated reference comparisons as per assignment requirements.
"""

import math
import pytest
from design import (
    calc_gross_yielding,
    calc_plate_net_rupture,
    calc_single_angle_net_rupture_is800,
    calc_block_shear,
    perform_complete_tension_design,
    get_standard_hole_diameter
)
from validation import validate_tension_member_inputs


class TestTensionMemberCalculations:
    """Independent verification of IS 800:2007 calculation routines."""

    def test_case_1_flat_plate_without_bolt_holes(self):
        """
        Test Case 1: Flat plate without bolt holes
        Parameters:
            Width b = 100 mm
            Thickness t = 10 mm
            fy = 250 MPa, fu = 410 MPa
            gamma_m0 = 1.10
            Applied Factored Load Tu = 150 kN
            No bolt holes on critical section.
        Hand Calculation:
            Ag = 100 * 10 = 1000 mm^2
            Tdg = (Ag * fy) / (gamma_m0 * 1000)
                = (1000 * 250) / (1.10 * 1000)
                = 227.2727 kN
            Utilization = 150 / 227.2727 = 0.660 <= 1.0 -> PASS
        """
        b = 100.0
        t = 10.0
        fy = 250.0
        gamma_m0 = 1.10
        Tu_kN = 150.0

        expected_Ag = 1000.0
        expected_Tdg_kN = (1000.0 * 250.0) / (1.10 * 1000.0)  # ~227.2727 kN
        expected_utilization = Tu_kN / expected_Tdg_kN

        res = calc_gross_yielding(expected_Ag, fy, gamma_m0)
        assert res["Ag_mm2"] == expected_Ag
        assert pytest.approx(res["Tdg_kN"], rel=1e-4) == expected_Tdg_kN

        # Complete design run without holes
        full_inputs = {
            "section_type": "Flat Plate",
            "width": b,
            "thickness": t,
            "fy": fy,
            "fu": 410.0,
            "gamma_m0": gamma_m0,
            "gamma_m1": 1.25,
            "Tu_kN": Tu_kN,
            "has_holes": False,
            "check_block_shear": False
        }
        design_res = perform_complete_tension_design(full_inputs)
        assert design_res["status"] == "PASS"
        assert pytest.approx(design_res["governing_strength_kN"], rel=1e-4) == expected_Tdg_kN
        assert pytest.approx(design_res["utilization_ratio"], rel=1e-4) == expected_utilization

    def test_case_2_flat_plate_with_bolt_holes(self):
        """
        Test Case 2: Flat plate with bolt holes
        Parameters:
            Width b = 100 mm
            Thickness t = 10 mm
            fy = 250 MPa, fu = 410 MPa
            gamma_m0 = 1.10, gamma_m1 = 1.25
            Two 18 mm holes across critical section (n = 2, dh = 18 mm)
            Tu = 150 kN
        Hand Calculation:
            Ag = 100 * 10 = 1000 mm^2
            Tdg = (1000 * 250) / (1.10 * 1000) = 227.2727 kN
            An = (100 - 2 * 18) * 10 = (100 - 36) * 10 = 640 mm^2
            Tdn = (0.9 * An * fu) / (gamma_m1 * 1000)
                = (0.9 * 640 * 410) / (1.25 * 1000)
                = 236160 / 1250
                = 188.928 kN
            Since 188.928 < 227.2727, Net Section Rupture GOVERNS!
            Utilization = 150 / 188.928 = 0.79395 <= 1.0 -> PASS
        """
        b = 100.0
        t = 10.0
        n_holes = 2
        dh = 18.0
        fu = 410.0
        gamma_m1 = 1.25
        Tu_kN = 150.0

        expected_An = (100.0 - 2.0 * 18.0) * 10.0  # 640.0 mm^2
        expected_Tdn_kN = (0.9 * expected_An * fu) / (gamma_m1 * 1000.0)  # 188.928 kN

        res_rupture = calc_plate_net_rupture(b, t, n_holes, dh, fu, gamma_m1)
        assert res_rupture["An_mm2"] == expected_An
        assert pytest.approx(res_rupture["Tdn_kN"], rel=1e-4) == expected_Tdn_kN

        # Complete design run
        full_inputs = {
            "section_type": "Flat Plate",
            "width": b,
            "thickness": t,
            "fy": 250.0,
            "fu": fu,
            "gamma_m0": 1.10,
            "gamma_m1": gamma_m1,
            "Tu_kN": Tu_kN,
            "has_holes": True,
            "d_bolt": 16.0,
            "dh": dh,
            "n_holes_critical": n_holes,
            "check_block_shear": False
        }
        design_res = perform_complete_tension_design(full_inputs)
        assert "Net Section Rupture" in design_res["governing_limit_state"]
        assert pytest.approx(design_res["governing_strength_kN"], rel=1e-4) == expected_Tdn_kN
        assert pytest.approx(design_res["utilization_ratio"], rel=1e-4) == (Tu_kN / expected_Tdn_kN)
        assert design_res["status"] == "PASS"

    def test_case_3_invalid_or_failing_design(self):
        """
        Test Case 3: Invalid geometry and Overloaded failing design
        Part A: Factored load exceeds capacity -> Status = FAIL
        Part B: Impossible hole diameter exceeding plate width -> Rejected by validator
        Part C: Non-positive dimension or fu <= fy -> Rejected by validator
        """
        # Part A: Overloaded plate (Tu = 250 kN > Td = 188.928 kN)
        overloaded_inputs = {
            "section_type": "Flat Plate",
            "width": 100.0,
            "thickness": 10.0,
            "fy": 250.0,
            "fu": 410.0,
            "gamma_m0": 1.10,
            "gamma_m1": 1.25,
            "Tu_kN": 250.0,
            "has_holes": True,
            "d_bolt": 16.0,
            "dh": 18.0,
            "n_holes_critical": 2,
            "check_block_shear": False
        }
        res_overload = perform_complete_tension_design(overloaded_inputs)
        assert res_overload["status"] == "FAIL"
        assert res_overload["utilization_ratio"] > 1.0

        # Part B: Impossible hole geometry (2 holes of 60 mm in 100 mm plate -> 120 mm > 100 mm)
        impossible_geom = {
            "section_type": "Flat Plate",
            "width": 100.0,
            "thickness": 10.0,
            "fy": 250.0,
            "fu": 410.0,
            "Tu_kN": 100.0,
            "has_holes": True,
            "d_bolt": 58.0,
            "dh": 60.0,
            "n_holes_critical": 2,
            "pitch": 150.0,
            "end_dist": 90.0
        }
        val_res_geom = validate_tension_member_inputs(impossible_geom)
        assert not val_res_geom.is_valid
        assert any("exceeds or equals plate width" in err for err in val_res_geom.errors)

        # Part C: Invalid material (fu <= fy)
        invalid_mat = {
            "section_type": "Flat Plate",
            "width": 100.0,
            "thickness": 10.0,
            "fy": 300.0,
            "fu": 250.0,  # fu < fy invalid
            "Tu_kN": 100.0
        }
        val_res_mat = validate_tension_member_inputs(invalid_mat)
        assert not val_res_mat.is_valid
        assert any("strictly greater than yield stress" in err for err in val_res_mat.errors)

    def test_case_4_block_shear_reference(self):
        """
        Test Case 4: Block Shear Failure check against independent manual calculations.
        Parameters:
            Avg = 1500 mm^2, Avn = 1100 mm^2
            Atg = 500 mm^2, Atn = 350 mm^2
            fy = 250 MPa, fu = 410 MPa
            gamma_m0 = 1.10, gamma_m1 = 1.25
        Manual derivation:
            Tdb1 = (Avg * fy) / (sqrt(3) * gamma_m0) + (0.9 * Atn * fu) / gamma_m1
                 = (1500 * 250) / (sqrt(3) * 1.10 * 1000) + (0.9 * 350 * 410) / (1.25 * 1000)
                 = 375 / (1.7320508 * 1.10) + 129.15 / 1.25
                 = 196.824 + 103.320 = 300.144 kN
            Tdb2 = (0.9 * Avn * fu) / (sqrt(3) * gamma_m1) + (Atg * fy) / gamma_m0
                 = (0.9 * 1100 * 410) / (sqrt(3) * 1.25 * 1000) + (500 * 250) / (1.10 * 1000)
                 = 405.9 / (1.7320508 * 1.25) + 125 / 1.10
                 = 187.477 + 113.636 = 301.113 kN
            Tdb = min(300.144, 301.113) = 300.144 kN (Tdb1 governs)
        """
        Avg = 1500.0
        Avn = 1100.0
        Atg = 500.0
        Atn = 350.0
        fy = 250.0
        fu = 410.0
        gamma_m0 = 1.10
        gamma_m1 = 1.25

        term_vg = (Avg * fy) / (math.sqrt(3.0) * gamma_m0 * 1000.0)
        term_tn = (0.9 * Atn * fu) / (gamma_m1 * 1000.0)
        expected_Tdb1_kN = term_vg + term_tn

        term_vn = (0.9 * Avn * fu) / (math.sqrt(3.0) * gamma_m1 * 1000.0)
        term_tg = (Atg * fy) / (gamma_m0 * 1000.0)
        expected_Tdb2_kN = term_vn + term_tg

        expected_Tdb_kN = min(expected_Tdb1_kN, expected_Tdb2_kN)

        res = calc_block_shear(Avg, Avn, Atg, Atn, fy, fu, gamma_m0, gamma_m1)
        assert pytest.approx(res["Tdb1_kN"], rel=1e-4) == expected_Tdb1_kN
        assert pytest.approx(res["Tdb2_kN"], rel=1e-4) == expected_Tdb2_kN
        assert pytest.approx(res["Tdb_kN"], rel=1e-4) == expected_Tdb_kN
        assert "Tdb1" in res["governing_equation"]

    def test_case_5_single_angle_shear_lag_beta(self):
        """
        Test Case 5: Single Angle Net Rupture with Shear Lag (IS 800:2007 Cl 6.3.3)
        Parameters:
            Angle: 100 x 75 x 8 mm (b_c = 100, w = 75, t = 8)
            Bolts: 3 bolts of 16 mm (dh = 18 mm) in 1 line
            pitch = 50 mm, end_dist = 35 mm, w1 = 50 mm (gauge)
            fy = 250 MPa, fu = 410 MPa, gamma_m0 = 1.10, gamma_m1 = 1.25
        Manual derivation:
            Lc = (3 - 1) * 50 = 100 mm
            bs = w + w1 - t = 75 + 50 - 8 = 117 mm
            beta_raw = 1.4 - 0.076 * (w / t) * (fy / fu) * (bs / Lc)
                     = 1.4 - 0.076 * (75 / 8) * (250 / 410) * (117 / 100)
                     = 1.4 - 0.076 * 9.375 * 0.609756 * 1.17
                     = 1.4 - 0.5082 = 0.8918
            beta limits:
                lower = 0.7
                upper = (fu * gamma_m0) / (fy * gamma_m1) = (410 * 1.10) / (250 * 1.25) = 451 / 312.5 = 1.4432
            beta = 0.8918 (within [0.70, 1.4432])
            Anc = (b_c - dh - t/2) * t = (100 - 18 - 4) * 8 = 78 * 8 = 624 mm^2
            Ago = (w - t/2) * t = (75 - 4) * 8 = 71 * 8 = 568 mm^2
            Tdn = (0.9 * Anc * fu / gamma_m1) + (beta * Ago * fy / gamma_m0)
                = (0.9 * 624 * 410 / 1.25) + (0.8918 * 568 * 250 / 1.10)
                = 184.205 kN + 115.124 kN = 299.329 kN
        """
        b_c = 100.0
        w = 75.0
        t = 8.0
        dh = 18.0
        fy = 250.0
        fu = 410.0
        n_bolts = 3
        pitch = 50.0
        end_dist = 35.0
        w1 = 50.0
        gamma_m0 = 1.10
        gamma_m1 = 1.25

        Lc = (n_bolts - 1) * pitch  # 100.0
        bs = w + w1 - t            # 117.0
        beta_raw = 1.4 - 0.076 * (w / t) * (fy / fu) * (bs / Lc)
        expected_beta = max(0.70, min(beta_raw, (fu * gamma_m0) / (fy * gamma_m1)))
        
        expected_Anc = (b_c - dh - t / 2.0) * t
        expected_Ago = (w - t / 2.0) * t
        expected_Tdn_kN = ((0.9 * expected_Anc * fu / gamma_m1) + 
                           (expected_beta * expected_Ago * fy / gamma_m0)) / 1000.0

        res = calc_single_angle_net_rupture_is800(
            b_c=b_c, w=w, t=t, dh=dh, fy=fy, fu=fu,
            n_bolts_along_length=n_bolts, pitch=pitch, end_dist=end_dist, w1=w1,
            gamma_m0=gamma_m0, gamma_m1=gamma_m1
        )
        assert pytest.approx(res["beta"], rel=1e-3) == expected_beta
        assert pytest.approx(res["Anc_mm2"], rel=1e-3) == expected_Anc
        assert pytest.approx(res["Ago_mm2"], rel=1e-3) == expected_Ago
        assert pytest.approx(res["Tdn_kN"], rel=1e-3) == expected_Tdn_kN

    def test_case_6_is800_bolt_spacing_rules(self):
        """
        Test Case 6: Bolt spacing rules as per IS 800:2007 Cl 10.2
        p_min = 2.5 * d
        e_min = 1.5 * dh
        """
        # Pitch too small (p = 30 < 2.5 * 16 = 40)
        invalid_pitch = {
            "section_type": "Flat Plate",
            "width": 100.0,
            "thickness": 10.0,
            "fy": 250.0,
            "fu": 410.0,
            "Tu_kN": 50.0,
            "has_holes": True,
            "d_bolt": 16.0,
            "dh": 18.0,
            "pitch": 30.0,  # invalid (< 40)
            "end_dist": 30.0
        }
        res_pitch = validate_tension_member_inputs(invalid_pitch)
        assert not res_pitch.is_valid
        assert any("violates IS 800:2007 Cl 10.2.2 minimum requirement" in err for err in res_pitch.errors)

        # End distance too small (e = 20 < 1.5 * 18 = 27)
        invalid_end = {
            "section_type": "Flat Plate",
            "width": 100.0,
            "thickness": 10.0,
            "fy": 250.0,
            "fu": 410.0,
            "Tu_kN": 50.0,
            "has_holes": True,
            "d_bolt": 16.0,
            "dh": 18.0,
            "pitch": 50.0,
            "end_dist": 20.0  # invalid (< 27)
        }
        res_end = validate_tension_member_inputs(invalid_end)
        assert not res_end.is_valid
        assert any("less than IS 800:2007 Cl 10.2.4.2 minimum" in err for err in res_end.errors)
