"""
Input Validation and Geometric Checks as per IS 800:2007
Validates cross-section dimensions, material strengths, fastener geometry,
edge distances, pitch, and gauge as per Indian Standard provisions.
"""

import math
from typing import Dict, Any, List, Tuple


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


def validate_tension_member_inputs(inputs: Dict[str, Any]) -> ValidationResult:
    """
    Comprehensive geometric, physical, and IS 800 code-compliance validator.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Factored Tensile Force Check
    try:
        Tu = float(inputs.get("Tu_kN", 0.0))
        if math.isnan(Tu) or math.isinf(Tu):
            errors.append("Factored tensile force Tu must be a finite numerical value.")
        elif Tu <= 0:
            errors.append("Factored tensile force (Tu) must be strictly greater than 0 kN.")
        elif Tu > 100000:
            warnings.append(f"Factored tensile force Tu = {Tu} kN is unusually large. Please verify your load units.")
    except (ValueError, TypeError):
        errors.append("Factored tensile force must be a valid number.")

    # 2. Material Strength Checks
    try:
        fy = float(inputs.get("fy", 0.0))
        fu = float(inputs.get("fu", 0.0))
        gamma_m0 = float(inputs.get("gamma_m0", 1.10))
        gamma_m1 = float(inputs.get("gamma_m1", 1.25))

        if math.isnan(fy) or math.isnan(fu) or math.isinf(fy) or math.isinf(fu):
            errors.append("Material stresses (fy, fu) must be finite numerical values.")
        if fy <= 0:
            errors.append("Yield stress fy must be strictly positive (typically 250 MPa for standard structural steel).")
        if fu <= 0:
            errors.append("Ultimate tensile stress fu must be strictly positive (typically 410 MPa for standard steel).")
        if fu <= fy and fy > 0 and fu > 0:
            errors.append(f"Ultimate tensile strength fu ({fu} MPa) must be strictly greater than yield stress fy ({fy} MPa).")
        
        if gamma_m0 <= 1.0:
            warnings.append(f"Partial safety factor gamma_m0 = {gamma_m0} is less than or equal to 1.0. Standard value is 1.10 (IS 800 Table 5).")
        if gamma_m1 <= 1.0:
            warnings.append(f"Partial safety factor gamma_m1 = {gamma_m1} is less than or equal to 1.0. Standard value is 1.25 (IS 800 Table 5).")
    except (ValueError, TypeError):
        errors.append("Material properties must be valid numerical values.")

    # 3. Section Type and Dimensional Checks
    section_type = inputs.get("section_type", "Flat Plate")
    supported_sections = ["Flat Plate", "Single Angle", "Double Angles"]
    if section_type not in supported_sections:
        errors.append(f"Unsupported section type '{section_type}'. Currently supported: {', '.join(supported_sections)}.")
        return ValidationResult(False, errors, warnings)

    thickness = 0.0
    try:
        thickness = float(inputs.get("thickness", 0.0))
        if thickness <= 0 or math.isnan(thickness) or math.isinf(thickness):
            errors.append("Section thickness must be strictly positive and finite.")
        elif thickness < 2.0:
            warnings.append(f"Section thickness ({thickness} mm) is very thin (< 2 mm). Structural tension members typically use t >= 5 mm.")
    except (ValueError, TypeError):
        errors.append("Section thickness must be a valid number.")

    if section_type == "Flat Plate":
        try:
            width = float(inputs.get("width", 0.0))
            if width <= 0 or math.isnan(width) or math.isinf(width):
                errors.append("Plate width must be strictly positive and finite.")
            elif width < 10.0:
                warnings.append(f"Plate width ({width} mm) is very small for a structural tension member.")
        except (ValueError, TypeError):
            errors.append("Plate width must be a valid number.")

    elif section_type in ["Single Angle", "Double Angles"]:
        try:
            b_c = float(inputs.get("b_c", 0.0))
            w = float(inputs.get("w", 0.0))
            if b_c <= 0 or w <= 0 or math.isnan(b_c) or math.isnan(w):
                errors.append("Angle leg dimensions (connected and outstanding legs) must be strictly positive.")
            if thickness > 0:
                if thickness >= b_c or thickness >= w:
                    errors.append(f"Thickness ({thickness} mm) cannot be greater than or equal to leg dimensions ({b_c} mm, {w} mm).")
        except (ValueError, TypeError):
            errors.append("Angle leg dimensions must be valid numbers.")

    # 4. Connection Details & Bolt Spacing Checks (if member has holes)
    has_holes = inputs.get("has_holes", True)
    if has_holes:
        try:
            d_bolt = float(inputs.get("d_bolt", 16.0))
            dh = float(inputs.get("dh", d_bolt + 2.0))
            
            if d_bolt <= 0 or dh <= 0:
                errors.append("Bolt diameter and hole diameter must be strictly positive.")
            if dh < d_bolt:
                errors.append(f"Hole diameter ({dh} mm) cannot be smaller than nominal bolt diameter ({d_bolt} mm).")

            # Check hole vs section width
            if section_type == "Flat Plate" and "width" in inputs:
                width = float(inputs["width"])
                n_holes_critical = int(inputs.get("n_holes_critical", 1))
                if n_holes_critical <= 0:
                    errors.append("Number of holes on critical section must be at least 1 when holes are enabled.")
                total_hole_width = n_holes_critical * dh
                if total_hole_width >= width:
                    errors.append(f"Total hole width ({total_hole_width:.1f} mm) exceeds or equals plate width ({width:.1f} mm), resulting in non-positive net area.")
                elif total_hole_width > 0.6 * width:
                    warnings.append("Holes occupy more than 60% of the plate width. Consider a wider plate or staggered hole arrangement.")

            elif section_type in ["Single Angle", "Double Angles"] and "b_c" in inputs:
                b_c = float(inputs["b_c"])
                n_holes_critical = int(inputs.get("n_holes_critical", 1))
                if (n_holes_critical * dh) >= b_c:
                    errors.append(f"Hole diameter ({dh} mm) exceeds or equals connected leg width ({b_c} mm).")
                
                w1 = float(inputs.get("w1", b_c / 2.0))
                if w1 <= 0 or w1 >= b_c:
                    errors.append(f"Bolt line distance w1 ({w1} mm) must be between 0 and connected leg width ({b_c} mm).")

            # Fastener Spacing Validation as per IS 800:2007 Cl 10.2
            pitch = float(inputs.get("pitch", 50.0))
            end_dist = float(inputs.get("end_dist", 35.0))
            
            # Minimum pitch: IS 800 Cl 10.2.2: p_min = 2.5 * d
            min_pitch = 2.5 * d_bolt
            if pitch < min_pitch:
                errors.append(f"Pitch ({pitch:.1f} mm) violates IS 800:2007 Cl 10.2.2 minimum requirement (2.5 × d = {min_pitch:.1f} mm).")
            
            # Maximum pitch in tension member: IS 800 Cl 10.2.3.1: min(16*t, 200 mm)
            if thickness > 0:
                max_pitch = min(16.0 * thickness, 200.0)
                if pitch > max_pitch:
                    warnings.append(f"Pitch ({pitch:.1f} mm) exceeds IS 800:2007 Cl 10.2.3 recommended maximum (min(16t, 200) = {max_pitch:.1f} mm).")

            # Minimum edge/end distance: IS 800 Cl 10.2.4.2
            # 1.5 * dh for machine cut/rolled edge, 1.7 * dh for hand flame/sheared edge
            min_end_dist = 1.5 * dh
            if end_dist < min_end_dist:
                errors.append(f"End distance ({end_dist:.1f} mm) is less than IS 800:2007 Cl 10.2.4.2 minimum (1.5 × dh = {min_end_dist:.1f} mm for machine flame cut).")

            # Maximum edge/end distance: IS 800 Cl 10.2.4.3: 12 * t * epsilon, where epsilon = sqrt(250 / fy)
            if thickness > 0 and fy > 0:
                epsilon = math.sqrt(250.0 / fy)
                max_edge_dist = 12.0 * thickness * epsilon
                if end_dist > max_edge_dist:
                    warnings.append(f"End distance ({end_dist:.1f} mm) exceeds IS 800:2007 Cl 10.2.4.3 maximum (12tε = {max_edge_dist:.1f} mm) to prevent edge curling.")

            # Multi-row plate checks
            if section_type == "Flat Plate":
                n_rows = int(inputs.get("n_rows", 1))
                if n_rows > 1:
                    gauge = float(inputs.get("gauge", 50.0))
                    edge_dist = float(inputs.get("edge_dist", 35.0))
                    
                    min_gauge = 2.5 * d_bolt
                    if gauge < min_gauge:
                        errors.append(f"Gauge distance ({gauge:.1f} mm) is less than minimum 2.5 × d ({min_gauge:.1f} mm).")
                    
                    if edge_dist < 1.5 * dh:
                        errors.append(f"Edge distance ({edge_dist:.1f} mm) is less than minimum 1.5 × dh ({1.5 * dh:.1f} mm).")
                    
                    # Total width check: 2 * edge_dist + (n_rows - 1) * gauge <= plate_width
                    width = float(inputs.get("width", 0.0))
                    required_width = 2.0 * edge_dist + (n_rows - 1) * gauge
                    if required_width > width:
                        errors.append(f"Plate width ({width:.1f} mm) is insufficient for bolt layout (requires 2×edge + (rows-1)×gauge = {required_width:.1f} mm).")

        except (ValueError, TypeError) as e:
            errors.append(f"Invalid fastener parameters: {str(e)}")

    is_valid = (len(errors) == 0)
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
