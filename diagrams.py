"""
Engineering Visualization Engine for Steel Tension Members
Generates cross-section geometry plots and connection block shear failure path diagrams.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Any, Optional


def create_cross_section_diagram(inputs: Dict[str, Any], An_mm2: Optional[float] = None) -> plt.Figure:
    """
    Renders 2D structural engineering cross-section diagram with dimensions.
    """
    section_type = inputs.get("section_type", "Flat Plate")
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    
    # Theme colors
    steel_fill = "#B0C4DE"
    steel_edge = "#0F172A"
    dim_color = "#1E3A8A"
    
    if section_type == "Flat Plate":
        width = float(inputs.get("width", 100.0))
        thickness = float(inputs.get("thickness", 10.0))
        
        # Scale for nice display
        rect = patches.Rectangle((-width/2, -thickness/2), width, thickness, 
                                 linewidth=2, edgecolor=steel_edge, facecolor=steel_fill, alpha=0.85)
        ax.add_patch(rect)
        
        # Draw bolt holes if present
        has_holes = inputs.get("has_holes", True)
        if has_holes:
            d_bolt = float(inputs.get("d_bolt", 16.0))
            dh = float(inputs.get("dh", d_bolt + 2.0))
            n_holes = int(inputs.get("n_holes_critical", 1))
            
            if n_holes == 1:
                hole = patches.Circle((0, 0), radius=dh/2, linewidth=1.5, edgecolor="red", facecolor="white", linestyle="--")
                ax.add_patch(hole)
            else:
                spacing = width / (n_holes + 1)
                for i in range(n_holes):
                    x = -width/2 + (i + 1) * spacing
                    hole = patches.Circle((x, 0), radius=dh/2, linewidth=1.5, edgecolor="red", facecolor="white", linestyle="--")
                    ax.add_patch(hole)
        
        # Dimension lines
        ax.annotate(f"b = {width:.0f} mm", xy=(0, thickness/2 + 2), xytext=(0, thickness/2 + 8),
                    ha="center", va="bottom", fontsize=10, fontweight="bold", color=dim_color)
        ax.annotate(f"t = {thickness:.0f} mm", xy=(width/2 + 3, 0), xytext=(width/2 + 10, 0),
                    ha="left", va="center", fontsize=10, fontweight="bold", color=dim_color)
        
        pad_x = width * 0.3
        pad_y = max(thickness * 3.0, 20.0)
        ax.set_xlim(-width/2 - pad_x, width/2 + pad_x)
        ax.set_ylim(-thickness/2 - pad_y, thickness/2 + pad_y)

    elif section_type in ["Single Angle", "Double Angles"]:
        b_c = float(inputs.get("b_c", 75.0))
        w = float(inputs.get("w", 75.0))
        thickness = float(inputs.get("thickness", 8.0))
        
        # Draw Single Angle L-profile
        # Connected leg horizontal [0, b_c], vertical [0, t]
        # Outstanding leg vertical [0, t], [0, w]
        verts = [
            (0, 0),
            (b_c, 0),
            (b_c, thickness),
            (thickness, thickness),
            (thickness, w),
            (0, w),
            (0, 0)
        ]
        poly = patches.Polygon(verts, closed=True, linewidth=2, edgecolor=steel_edge, facecolor=steel_fill, alpha=0.85)
        ax.add_patch(poly)
        
        if section_type == "Double Angles":
            # Gusset plate in middle
            tg = 10.0  # nominal gusset plate thickness for visualization
            gusset = patches.Rectangle((-tg, -10), tg, max(w, b_c) + 20, linewidth=1.5,
                                       edgecolor="#64748B", facecolor="#E2E8F0", linestyle=":", alpha=0.7)
            ax.add_patch(gusset)
            
            # Second mirrored angle
            verts2 = [
                (-tg, 0),
                (-tg - b_c, 0),
                (-tg - b_c, thickness),
                (-tg - thickness, thickness),
                (-tg - thickness, w),
                (-tg, w),
                (-tg, 0)
            ]
            poly2 = patches.Polygon(verts2, closed=True, linewidth=2, edgecolor=steel_edge, facecolor="#94A3B8", alpha=0.85)
            ax.add_patch(poly2)
        
        # Hole on connected leg
        has_holes = inputs.get("has_holes", True)
        if has_holes:
            w1 = float(inputs.get("w1", b_c / 2.0))
            d_bolt = float(inputs.get("d_bolt", 16.0))
            dh = float(inputs.get("dh", d_bolt + 2.0))
            hole = patches.Circle((w1, thickness / 2.0), radius=dh/2.0, linewidth=1.5,
                                  edgecolor="red", facecolor="white", linestyle="--")
            ax.add_patch(hole)
            if section_type == "Double Angles":
                hole2 = patches.Circle((-10.0 - w1, thickness / 2.0), radius=dh/2.0, linewidth=1.5,
                                       edgecolor="red", facecolor="white", linestyle="--")
                ax.add_patch(hole2)

        ax.annotate(f"Connected leg: {b_c:.0f} mm", xy=(b_c/2, -15), ha="center", fontsize=9, fontweight="bold", color=dim_color)
        ax.annotate(f"Outstand: {w:.0f} mm", xy=(-20 if section_type=="Single Angle" else 15 + b_c, w/2),
                    rotation=90, ha="center", fontsize=9, fontweight="bold", color=dim_color)
        ax.annotate(f"t = {thickness:.0f} mm", xy=(b_c + 5, thickness/2), ha="left", fontsize=9, color=dim_color)

        ax.set_xlim(-b_c - 30 if section_type=="Double Angles" else -25, b_c + 40)
        ax.set_ylim(-25, w + 30)

    ax.set_aspect("equal", "box")
    ax.axis("off")
    title = f"{section_type} Cross-Section"
    if An_mm2:
        title += f" (Net Area An = {An_mm2:.1f} mm²)"
    ax.set_title(title, fontsize=11, fontweight="bold", pad=12, color="#0F172A")
    plt.tight_layout()
    return fig


def create_connection_block_shear_diagram(inputs: Dict[str, Any], block_results: Optional[Dict[str, Any]] = None) -> plt.Figure:
    """
    Renders 2D engineering plan view showing bolt layout, dimensions,
    and the IS 800:2007 Block Shear failure path (shear and tension planes).
    """
    section_type = inputs.get("section_type", "Flat Plate")
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)
    
    n_cols = int(inputs.get("n_cols", 3))  # bolts along length
    pitch = float(inputs.get("pitch", 50.0))
    end_dist = float(inputs.get("end_dist", 35.0))
    d_bolt = float(inputs.get("d_bolt", 16.0))
    dh = float(inputs.get("dh", d_bolt + 2.0))
    
    if section_type == "Flat Plate":
        n_rows = int(inputs.get("n_rows", 2))
        gauge = float(inputs.get("gauge", 50.0))
        edge_dist = float(inputs.get("edge_dist", 35.0))
        width = float(inputs.get("width", 2.0 * edge_dist + (n_rows - 1) * gauge))
        
        total_length = end_dist + (n_cols - 1) * pitch + 70.0
        
        # Draw Plate
        plate = patches.Rectangle((0, 0), total_length, width, linewidth=2,
                                  edgecolor="#1E293B", facecolor="#E2E8F0", alpha=0.9)
        ax.add_patch(plate)
        
        # Bolt coordinates
        bolt_x_coords = [end_dist + j * pitch for j in range(n_cols)]
        bolt_y_coords = [edge_dist + i * gauge for i in range(n_rows)]
        
        # Block shear failure path
        if n_rows == 1:
            y_line = bolt_y_coords[0]
            last_x = bolt_x_coords[-1]
            
            # Shaded failure block
            block_patch = patches.Rectangle((0, 0), last_x, y_line, linewidth=0, facecolor="#FCA5A5", alpha=0.45)
            ax.add_patch(block_patch)
            
            # Shear line: (0, y_line) to (last_x, y_line)
            ax.plot([0, last_x], [y_line, y_line], color="#DC2626", linestyle="--", linewidth=2.5, label="Shear Plane (Avg, Avn)")
            # Tension line: (last_x, y_line) to (last_x, 0)
            ax.plot([last_x, last_x], [y_line, 0], color="#2563EB", linestyle="--", linewidth=2.5, label="Tension Plane (Atg, Atn)")
        else:
            y_bot = bolt_y_coords[0]
            y_top = bolt_y_coords[-1]
            last_x = bolt_x_coords[-1]
            
            # Shaded failure block between outer rows
            block_patch = patches.Rectangle((0, y_bot), last_x, y_top - y_bot, linewidth=0, facecolor="#FCA5A5", alpha=0.45)
            ax.add_patch(block_patch)
            
            # Two Shear lines
            ax.plot([0, last_x], [y_bot, y_bot], color="#DC2626", linestyle="--", linewidth=2.5, label="Shear Planes (Avg, Avn)")
            ax.plot([0, last_x], [y_top, y_top], color="#DC2626", linestyle="--", linewidth=2.5)
            # Tension line connecting the two outermost bolts at end of joint
            ax.plot([last_x, last_x], [y_bot, y_top], color="#2563EB", linestyle="--", linewidth=2.5, label="Tension Plane (Atg, Atn)")

        # Draw Bolts
        for x in bolt_x_coords:
            for y in bolt_y_coords:
                hole = patches.Circle((x, y), radius=dh/2.0, linewidth=1.5, edgecolor="#0F172A", facecolor="#F8FAFC")
                ax.add_patch(hole)
                # bolt center mark
                ax.plot(x, y, marker="+", color="#0F172A", markersize=6)

        # Dimension annotations
        ax.annotate("", xy=(0, -12), xytext=(end_dist, -12), arrowprops=dict(arrowstyle="<->", color="#1E3A8A"))
        ax.text(end_dist/2, -22, f"e = {end_dist:.0f}", ha="center", fontsize=8, color="#1E3A8A")
        
        if n_cols > 1:
            ax.annotate("", xy=(end_dist, -12), xytext=(end_dist + pitch, -12), arrowprops=dict(arrowstyle="<->", color="#1E3A8A"))
            ax.text(end_dist + pitch/2, -22, f"p = {pitch:.0f}", ha="center", fontsize=8, color="#1E3A8A")
            
        if n_rows > 1:
            ax.annotate("", xy=(-12, edge_dist), xytext=(-12, edge_dist + gauge), arrowprops=dict(arrowstyle="<->", color="#1E3A8A"))
            ax.text(-22, edge_dist + gauge/2, f"g={gauge:.0f}", va="center", ha="right", fontsize=8, color="#1E3A8A", rotation=90)
            
        # Applied tension arrow
        ax.annotate("", xy=(total_length + 25, width/2), xytext=(total_length, width/2),
                    arrowprops=dict(arrowstyle="->", lw=3.0, color="#059669"))
        ax.text(total_length + 30, width/2, "Tensile Force Tu →", va="center", fontweight="bold", color="#059669", fontsize=10)

        ax.set_xlim(-40, total_length + 100)
        ax.set_ylim(-35, width + 25)

    else:
        # Single Angle or Double Angle Connected Leg Plan View
        b_c = float(inputs.get("b_c", 75.0))
        w1 = float(inputs.get("w1", b_c / 2.0))
        total_length = end_dist + (n_cols - 1) * pitch + 70.0
        
        # Connected Leg rectangle
        leg_rect = patches.Rectangle((0, 0), total_length, b_c, linewidth=2,
                                     edgecolor="#1E293B", facecolor="#E2E8F0", alpha=0.9)
        ax.add_patch(leg_rect)
        
        # Outstand indication at bottom (toe)
        ax.plot([0, total_length], [0, 0], color="#0F172A", linewidth=3)
        ax.text(total_length/2, -12, "← Heel of Angle (Corner) →", ha="center", fontsize=8, color="#475569")
        
        bolt_x_coords = [end_dist + j * pitch for j in range(n_cols)]
        y_bolt = w1
        last_x = bolt_x_coords[-1]
        
        # Block shear failure path
        # Shear along bolt line
        ax.plot([0, last_x], [y_bolt, y_bolt], color="#DC2626", linestyle="--", linewidth=2.5, label="Shear Plane (Avg, Avn)")
        # Tension to toe/edge
        ax.plot([last_x, last_x], [y_bolt, b_c], color="#2563EB", linestyle="--", linewidth=2.5, label="Tension Plane (Atg, Atn)")
        
        # Shaded block
        block_patch = patches.Rectangle((0, y_bolt), last_x, b_c - y_bolt, linewidth=0, facecolor="#FCA5A5", alpha=0.45)
        ax.add_patch(block_patch)

        # Draw bolts
        for x in bolt_x_coords:
            hole = patches.Circle((x, y_bolt), radius=dh/2.0, linewidth=1.5, edgecolor="#0F172A", facecolor="#F8FAFC")
            ax.add_patch(hole)
            ax.plot(x, y_bolt, marker="+", color="#0F172A", markersize=6)

        # Dimension annotations
        ax.annotate("", xy=(0, b_c + 8), xytext=(end_dist, b_c + 8), arrowprops=dict(arrowstyle="<->", color="#1E3A8A"))
        ax.text(end_dist/2, b_c + 15, f"e = {end_dist:.0f}", ha="center", fontsize=8, color="#1E3A8A")
        
        if n_cols > 1:
            ax.annotate("", xy=(end_dist, b_c + 8), xytext=(end_dist + pitch, b_c + 8), arrowprops=dict(arrowstyle="<->", color="#1E3A8A"))
            ax.text(end_dist + pitch/2, b_c + 15, f"p = {pitch:.0f}", ha="center", fontsize=8, color="#1E3A8A")

        # Applied tension arrow
        ax.annotate("", xy=(total_length + 25, b_c/2), xytext=(total_length, b_c/2),
                    arrowprops=dict(arrowstyle="->", lw=3.0, color="#059669"))
        ax.text(total_length + 30, b_c/2, "Tensile Force Tu →", va="center", fontweight="bold", color="#059669", fontsize=10)

        ax.set_xlim(-30, total_length + 100)
        ax.set_ylim(-25, b_c + 30)

    ax.legend(loc="upper right", framealpha=0.9, fontsize=8)
    ax.set_aspect("equal", "box")
    ax.axis("off")
    title = f"Connection Layout & Block Shear Tear-out Path (IS 800:2007 Cl 6.4)"
    if block_results:
        title += f"\nDesign Block Shear Strength Tdb = {block_results.get('Tdb_kN', 0.0):.2f} kN"
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10, color="#0F172A")
    plt.tight_layout()
    return fig
