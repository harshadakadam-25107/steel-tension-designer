# AI Application for Design of Steel Structural Members as per IS 800:2007

**Course Assignment:** Third-Year (T.Y.) Civil Engineering — FA-2 Project  
**Engineering Domain:** Structural Steel Design / Limit State Method (LSM)  
**Standard Specification:** Bureau of Indian Standards — **IS 800:2007** (General Construction in Steel — Code of Practice)

---

## 🌟 Project Overview

This web application is an educational and professional civil-engineering design portal that computes, validates, and visualizes the design of **Steel Tension Members** in strict accordance with the limit state provisions of **IS 800:2007**.

Unlike a simple calculator or static dashboard, the application features:
1. **Deterministic Calculation Engine:** Pure Python formulas without black-box approximations.
2. **IS 800:2007 Limit States Checked:**
   - **Gross Section Yielding ($T_{dg}$)** — Clause 6.2
   - **Net Section Rupture ($T_{dn}$)** — Clause 6.3.1 (Plates) & Clause 6.3.3 (Single/Double Angles with shear lag $\beta$ factor)
   - **Block Shear Failure ($T_{db}$)** — Clause 6.4.1 (with derived gross & net shear/tension areas)
   - **Fastener Spacing & Edge Distances** — Clause 10.2 & Table 19
3. **Automated Input Validation:** Prevents non-physical geometries, invalid bolt layouts, impossible net areas, and non-conforming spacing.
4. **Educational AI-Style Explanation Engine:** Translates calculated capacities and utilization ratios into plain-English civil engineering commentary with actionable design advice.
5. **Interactive 2D Schematics:** Matplotlib renderings of cross-sectional geometries and plan views of connection tear-out failure blocks.
6. **Report Export:** Full calculation sheets downloadable as CSV or printable text reports.
7. **Automated Verification:** Comprehensive Pytest suite comparing software outputs against hand-calculated benchmark problems.

---

## 🛠️ Technology Stack

- **Backend Logic & Formulas:** Pure Python 3 (`design.py`)
- **Web User Interface:** Streamlit (`app.py`)
- **Data Handling:** Pandas & NumPy
- **Visual Engineering Schematics:** Matplotlib (`diagrams.py`)
- **Automated Unit Testing:** Pytest (`test_design.py`)
- **Deployment Platform:** Streamlit Community Cloud & GitHub

---

## 📁 Project Architecture & File Organization

```text
c:\Users\harshada\Downloads\DSS/
│
├── app.py             # Streamlit web UI, multi-page routing & state management
├── design.py          # Pure Python IS 800:2007 formulas & deterministic logic
├── validation.py      # Input validation & geometric check engine
├── diagrams.py        # 2D cross-section and block-shear failure visualization
├── test_design.py     # Pytest unit tests & independent reference calculations
├── requirements.txt   # Pinned Python dependencies
├── README.md          # Comprehensive technical documentation & deployment guide
└── .gitignore         # Version control exclusion file
```

---

## ⚙️ Local Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed on your machine.
- `pip` package manager.

### Step 1: Clone or Navigate to the Repository
```bash
cd c:\Users\harshada\Downloads\DSS
```

### Step 2: Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Launching the Web Application

To start the interactive web application locally:
```bash
streamlit run app.py
```
After running this command, your default browser will open automatically to:
`http://localhost:8501`

---

## 🧪 Running Automated Unit Tests

Automated test cases compare the software results against hand calculations:
```bash
pytest -v test_design.py
```

### Expected Test Results:
```text
test_design.py::TestTensionMemberCalculations::test_case_1_flat_plate_without_bolt_holes PASSED
test_design.py::TestTensionMemberCalculations::test_case_2_flat_plate_with_bolt_holes PASSED
test_design.py::TestTensionMemberCalculations::test_case_3_invalid_or_failing_design PASSED
test_design.py::TestTensionMemberCalculations::test_case_4_block_shear_reference PASSED
test_design.py::TestTensionMemberCalculations::test_case_5_single_angle_shear_lag_beta PASSED
test_design.py::TestTensionMemberCalculations::test_case_6_is800_bolt_spacing_rules PASSED
============================== 6 passed in 0.05s ==============================
```

---

## 📐 Benchmark Test Cases & Independent Verification

### Test Case 1: Flat Plate without Bolt Holes
- **Inputs:** Width $b = 100\text{ mm}$, Thickness $t = 10\text{ mm}$, $f_y = 250\text{ MPa}$, $\gamma_{m0} = 1.10$, $T_u = 150\text{ kN}$.
- **Hand Calculation:**
  $$A_g = 100 \times 10 = 1000\text{ mm}^2$$
  $$T_{dg} = \frac{1000 \times 250}{1.10 \times 1000} = 227.27\text{ kN}$$
  $$\text{Utilization Ratio} = \frac{150.0}{227.27} = 0.660 \le 1.0 \rightarrow \mathbf{PASS}$$
- **Software Result:** $227.27\text{ kN}$ ($\text{Relative Error} = 0.000\%$).

### Test Case 2: Flat Plate with Bolt Holes
- **Inputs:** Width $b = 100\text{ mm}$, Thickness $t = 10\text{ mm}$, $2 \times 18\text{ mm}$ holes ($n=2, d_h=18\text{ mm}$), $f_u = 410\text{ MPa}$, $\gamma_{m1} = 1.25$, $T_u = 150\text{ kN}$.
- **Hand Calculation:**
  $$A_n = (100 - 2 \times 18) \times 10 = 640\text{ mm}^2$$
  $$T_{dn} = \frac{0.9 \times 640 \times 410}{1.25 \times 1000} = 188.93\text{ kN}$$
  Since $T_{dn} < T_{dg}$ ($188.93\text{ kN} < 227.27\text{ kN}$), Net Section Rupture governs!
  $$\text{Utilization Ratio} = \frac{150.0}{188.93} = 0.794 \le 1.0 \rightarrow \mathbf{PASS}$$
- **Software Result:** $188.93\text{ kN}$ ($\text{Relative Error} = 0.000\%$).

### Test Case 3: Overloaded Specimen (FAIL Check)
- **Inputs:** Same plate with $T_u = 250\text{ kN}$.
- **Calculation:**
  $$\text{Utilization Ratio} = \frac{250.0}{188.93} = 1.323 > 1.0 \rightarrow \mathbf{FAIL}$$
- **Software Result:** Flagged as `🚨 UNSAFE (FAIL)`.

---

## ☁️ Deployment to Streamlit Community Cloud

Anyone worldwide can access your deployed project for free via Streamlit Community Cloud:

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: IS 800:2007 Steel Tension Member Designer"
   git branch -M main
   git remote add origin https://github.com/<your-username>/steel-tension-designer.git
   git push -u origin main
   ```
2. **Deploy on Streamlit Community Cloud:**
   - Visit [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
   - Click **"Create app"** or **"New app"**.
   - Select your repository (`steel-tension-designer`), branch (`main`), and set Main file path to `app.py`.
   - Click **"Deploy"**.
   - Within 1–2 minutes, your live public URL will be ready (e.g. `https://steel-tension-designer.streamlit.app`).

---

## 📖 Key Engineering Assumptions & Code References

1. **Axial Concentricity:** Applied tensile force is assumed concentric with the centroidal axis. Shear lag in single angles is deterministically captured via IS 800 Clause 6.3.3 $\beta$ expression.
2. **Standard Clearance Holes:** Fastener holes follow Table 19 ($d_h = d + 2\text{ mm}$ for $16 \le d \le 24\text{ mm}$).
3. **Block Shear Planes:** Assumed rectilinear tear-out paths conforming to Clause 6.4.1.
4. **Official Standard Verification:** All equations, clauses, and safety factors must be checked against the official publication of **IS 800:2007** before applying to non-educational structures.

---

## 👨‍🎓 Academic Submission Details

- **Author / Student:** Third-Year (T.Y.) Civil Engineering Student
- **Coursework:** FA-2 Assignment — Design of Steel Structures
- **Supervision / Department:** Department of Civil Engineering
- **License:** Educational Open-Source Prototype
