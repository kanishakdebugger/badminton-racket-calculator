"""Badminton Racket Physics & Customization Calculator

Run with:
    pip install streamlit pandas
    streamlit run app.py

This app estimates final static weight, effective balance point, net shift,
and a simple swing-weight change after strings, grips, and lead tape are added.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
import streamlit as st


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Badminton Racket DNA Calculator",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at top, #141826 0%, #0b0f17 55%, #070a0f 100%);
            color: #eef2ff;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, h4, h5, p, div, span, label {
            color: #eef2ff !important;
        }
        .sport-card {
            background: linear-gradient(180deg, rgba(18,24,36,0.98), rgba(10,14,22,0.98));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .accent {
            color: #7dd3fc;
            font-weight: 700;
        }
        .muted {
            color: #b6c2d9 !important;
        }
        .big-number {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
        }
        .small-label {
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #9fb3d9 !important;
        }
        .pill {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            border: 1px solid rgba(125,211,252,0.28);
            background: rgba(125,211,252,0.08);
            color: #d8f3ff !important;
            font-weight: 700;
        }
        .formula-box {
            background: rgba(125,211,252,0.08);
            border: 1px solid rgba(125,211,252,0.16);
            border-radius: 16px;
            padding: 0.9rem 1rem;
        }
        .report-box {
            background: linear-gradient(180deg, rgba(7,10,15,0.96), rgba(18,24,36,0.96));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 22px;
            padding: 1.2rem;
        }
        .stMetric {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 0.6rem 0.8rem;
        }
        .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input,
        .stTextInput input,
        .stSlider div[data-baseweb="slider"] {
            border-radius: 12px !important;
        }
        .footer-note {
            color: #9fb3d9 !important;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Accessory:
    name: str
    mass_g: float
    position_mm: float


# -----------------------------
# Helpers
# -----------------------------
def preset_location_mm(location: str, length_mm: float) -> float:
    """Return a logical placement point in mm from butt-cap."""
    presets = {
        "12 o'clock": 670.0,
        "3/9 o'clock": 620.0,
        "T-joint": 380.0,
        "Strings (bed center)": max(length_mm - 115.0, 0.0),
        "Grip / overgrip": 80.0,
        "Custom": 0.0,
    }
    return presets.get(location, 0.0)


def category(bp_mm: float) -> str:
    if bp_mm < 285:
        return "Head-Light"
    if bp_mm <= 295:
        return "Even-Balance"
    return "Head-Heavy"


def playstyle_sentence(bp_shift_mm: float, cat: str) -> str:
    abs_shift = abs(bp_shift_mm)
    direction = "toward the handle" if bp_shift_mm < 0 else "toward the head" if bp_shift_mm > 0 else "with no balance shift"

    if cat == "Head-Light":
        base = "more maneuverable at the net and quicker in defense"
    elif cat == "Even-Balance":
        base = "balanced for all-round play with a mix of speed and control"
    else:
        base = "more power-oriented on full swings and clears"

    if abs_shift >= 10:
        intensity = "noticeably"
    elif abs_shift >= 4:
        intensity = "moderately"
    else:
        intensity = "slightly"

    return f"This setup feels {intensity} shifted {direction}, making it {base}."


def estimate_swing_weight_change(accessories: List[Accessory], pivot_mm: float = 100.0) -> float:
    """Approximate change in swing weight relative to a pivot point.

    Output is in kg·cm². Positive numbers mean more inertia.
    """
    delta = 0.0
    for item in accessories:
        r_cm = (item.position_mm - pivot_mm) / 10.0
        delta += (item.mass_g * (r_cm ** 2)) / 1000.0
    return delta


def fmt_shift(mm: float) -> str:
    if abs(mm) < 0.05:
        return "0.0 mm"
    direction = "toward head" if mm > 0 else "toward handle"
    return f"{abs(mm):.1f} mm {direction}"


def build_accessory_rows(
    base_length_mm: float,
    strings_on: bool,
    string_mass_g: float,
    overgrip_on: bool,
    overgrip_mass_g: float,
    original_grip_removed: bool,
    original_grip_mass_g: float,
    replacement_grip_on: bool,
    replacement_grip_mass_g: float,
    lead_items: List[Tuple[bool, float, str, float]],
) -> List[Accessory]:
    items: List[Accessory] = []

    if strings_on and string_mass_g != 0:
        items.append(Accessory("Strings", string_mass_g, max(base_length_mm - 115.0, 0.0)))

    if overgrip_on and overgrip_mass_g != 0:
        items.append(Accessory("Overgrip", overgrip_mass_g, 80.0))

    if original_grip_removed and original_grip_mass_g != 0:
        items.append(Accessory("Original grip removal", -abs(original_grip_mass_g), 80.0))

    if replacement_grip_on and replacement_grip_mass_g != 0:
        items.append(Accessory("Replacement / towel grip", replacement_grip_mass_g, 80.0))

    for enabled, mass_g, loc_mode, custom_mm in lead_items:
        if not enabled or mass_g == 0:
            continue
        if loc_mode == "12 o'clock":
            pos = 670.0
        elif loc_mode == "3/9 o'clock":
            pos = 620.0
        elif loc_mode == "T-joint":
            pos = 380.0
        else:
            pos = custom_mm
        items.append(Accessory(f"Lead tape ({loc_mode})", mass_g, pos))

    return items


# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.title("🏸 Setup")
st.sidebar.caption("All distances are measured from the butt-cap in mm.")

st.sidebar.subheader("Factory specifications")
base_mass = st.sidebar.number_input(
    "Static weight (dry racket) in g",
    min_value=50.0,
    max_value=130.0,
    value=83.0,
    step=0.1,
    help="The dry factory weight of the racket before strings and custom add-ons.",
)
base_bp = st.sidebar.number_input(
    "Initial balance point in mm",
    min_value=200.0,
    max_value=380.0,
    value=295.0,
    step=0.1,
    help="Factory balance point measured from the butt-cap to the center of mass.",
)
base_length = st.sidebar.number_input(
    "Total length in mm",
    min_value=640.0,
    max_value=700.0,
    value=675.0,
    step=1.0,
    help="Standard badminton rackets are usually 675 mm, but custom lengths are allowed.",
)

st.sidebar.subheader("Strings")
strings_on = st.sidebar.toggle(
    "Strung racket",
    value=True,
    help="Strings are typically modeled near the center of the string bed, which is toward the head.",
)
string_mass = st.sidebar.number_input(
    "String mass in g",
    min_value=0.0,
    max_value=10.0,
    value=3.5,
    step=0.1,
    help="Approximate mass of a full badminton string job.",
)

st.sidebar.subheader("Grips")
overgrip_on = st.sidebar.toggle(
    "Add overgrip",
    value=False,
    help="An overgrip adds mass close to the handle, usually shifting balance toward the handle.",
)
overgrip_mass = st.sidebar.number_input(
    "Overgrip mass in g",
    min_value=0.0,
    max_value=20.0,
    value=4.5,
    step=0.1,
    help="Typical overgrips are light but they sit very close to the butt-cap, so they shift balance efficiently.",
)
original_grip_removed = st.sidebar.toggle(
    "Remove original factory grip",
    value=False,
    help="Use this when replacing the factory grip or stripping it before adding a new grip layer.",
)
original_grip_mass = st.sidebar.number_input(
    "Factory grip removed (g)",
    min_value=0.0,
    max_value=30.0,
    value=7.0,
    step=0.1,
    help="Subtract the removed grip weight from the racket. Adjust to match your actual grip.",
)
replacement_grip_on = st.sidebar.toggle(
    "Add replacement / towel grip",
    value=False,
    help="Replacement grips are usually thicker and heavier than overgrips.",
)
replacement_grip_mass = st.sidebar.number_input(
    "Replacement / towel grip mass in g",
    min_value=0.0,
    max_value=30.0,
    value=13.5,
    step=0.1,
    help="A towel grip or replacement grip usually sits around the handle, near the balance pivot.",
)

st.sidebar.subheader("Lead tape / weights")
lead_slots = st.sidebar.slider(
    "Number of lead-tape entries",
    min_value=0,
    max_value=4,
    value=2,
    help="Add multiple weight locations to model custom tuning.",
)

lead_items: List[Tuple[bool, float, str, float]] = []
for i in range(lead_slots):
    with st.sidebar.expander(f"Lead tape #{i + 1}", expanded=(i == 0)):
        enabled = st.checkbox("Enable this strip", value=True, key=f"lead_enabled_{i}")
        mass_g = st.number_input(
            "Mass in g",
            min_value=0.0,
            max_value=20.0,
            value=2.0,
            step=0.1,
            key=f"lead_mass_{i}",
            help="Weight of the lead strip or tungsten tape.",
        )
        loc = st.selectbox(
            "Location",
            ["12 o'clock", "3/9 o'clock", "T-joint", "Custom mm"],
            index=0,
            key=f"lead_loc_{i}",
            help="Preset locations use practical center-of-mass points. Custom lets you type an exact position.",
        )
        custom_mm = 670.0
        if loc == "Custom mm":
            custom_mm = st.number_input(
                "Custom position from butt-cap (mm)",
                min_value=0.0,
                max_value=base_length,
                value=620.0,
                step=1.0,
                key=f"lead_custom_{i}",
            )
        lead_items.append((enabled, mass_g, loc if loc != "Custom mm" else "Custom", custom_mm))


# -----------------------------
# Main calculation
# -----------------------------
st.title("Badminton Racket DNA Calculator")
st.caption("Live balance-point and weight prediction after stringing, gripping, and lead tape tuning.")

with st.container():
    st.markdown(
        """
        <div class="formula-box">
        <div class="small-label">Core idea</div>
        <div style="margin-top:0.35rem;">
        New balance point = <span class="accent">Σ(m × d) / Σm</span><br/>
        Weight added near the head pulls the center of mass upward much more than the same weight near the handle.
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

accessories = build_accessory_rows(
    base_length_mm=base_length,
    strings_on=strings_on,
    string_mass_g=string_mass,
    overgrip_on=overgrip_on,
    overgrip_mass_g=overgrip_mass,
    original_grip_removed=original_grip_removed,
    original_grip_mass_g=original_grip_mass,
    replacement_grip_on=replacement_grip_on,
    replacement_grip_mass_g=replacement_grip_mass,
    lead_items=lead_items,
)

# Compute final mass and balance
final_mass = base_mass + sum(item.mass_g for item in accessories)
if final_mass <= 0:
    st.error("Final mass must stay above zero. Please adjust the inputs.")
    st.stop()

total_moment = base_mass * base_bp + sum(item.mass_g * item.position_mm for item in accessories)
final_bp = total_moment / final_mass
net_shift = final_bp - base_bp
final_cat = category(final_bp)

# Estimated swing weight change relative to a 100 mm pivot
sw_delta = estimate_swing_weight_change(accessories, pivot_mm=100.0)

# Build breakdown table
rows = [
    {"Item": "Factory racket", "Mass (g)": base_mass, "Position (mm)": base_bp, "Moment (g·mm)": base_mass * base_bp},
]
for item in accessories:
    rows.append(
        {
            "Item": item.name,
            "Mass (g)": item.mass_g,
            "Position (mm)": item.position_mm,
            "Moment (g·mm)": item.mass_g * item.position_mm,
        }
    )

df = pd.DataFrame(rows)

# -----------------------------
# Results area
# -----------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total static weight", f"{final_mass:.1f} g", delta=f"{final_mass - base_mass:+.1f} g")
col2.metric("Effective balance point", f"{final_bp:.1f} mm", delta=f"{net_shift:+.1f} mm")
col3.metric("Balance label", final_cat)
col4.metric("Est. swing weight change", f"{sw_delta:.3f} kg·cm²")

st.markdown("---")

left, right = st.columns([1.1, 0.9])

with left:
    st.markdown(
        f"""
        <div class="report-box">
            <div class="small-label">Racket DNA</div>
            <div class="big-number">{final_mass:.1f} g</div>
            <div style="margin-top:0.4rem; font-size:1.05rem;">
                <span class="pill">{final_cat}</span>
                <span style="margin-left:0.55rem;">Balance point: <b>{final_bp:.1f} mm</b></span>
            </div>
            <div style="margin-top:0.8rem; font-size:1rem;">
                Net shift: <b>{fmt_shift(net_shift)}</b>
            </div>
            <div style="margin-top:0.8rem; font-size:1rem; line-height:1.6;">
                {playstyle_sentence(net_shift, final_cat)}
            </div>
            <div style="margin-top:0.9rem; color:#b6c2d9; font-size:0.95rem; line-height:1.6;">
                Swing-weight note: head-side mass increases inertia more than handle-side mass because the distance from the pivot is larger, and inertia grows with distance squared.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        """
        <div class="sport-card">
            <div class="small-label">Balance rules</div>
            <div style="margin-top:0.55rem; line-height:1.8;">
                <div>• <b>&lt; 285 mm</b>: Head-Light</div>
                <div>• <b>285–295 mm</b>: Even-Balance</div>
                <div>• <b>&gt; 295 mm</b>: Head-Heavy</div>
            </div>
            <div style="margin-top:0.9rem; color:#b6c2d9; line-height:1.6;">
                The calculator treats each added item as a point mass at a practical center-of-gravity point.
                That gives a fast and useful estimate for setup decisions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### Detailed breakdown")
st.dataframe(df.style.format({"Mass (g)": "{:.2f}", "Position (mm)": "{:.1f}", "Moment (g·mm)": "{:.1f}"}), use_container_width=True)

with st.expander("Why the balance changes when you add a grip", expanded=False):
    st.write(
        "A grip sits close to the butt-cap, so it pulls the center of mass downward more efficiently per gram than head-side weight. "
        "That is why a few grams in the handle can noticeably reduce the balance point, while the same grams near 12 o'clock can push it upward and make the racket feel more demanding to swing."
    )

with st.expander("Calculation details", expanded=False):
    st.write(
        "Formula used: new balance point = Σ(mass × distance) / Σ(mass). "
        "Strings are placed at length − 115 mm, handle materials at 80 mm, 12 o'clock lead at 670 mm, and T-joint lead at 380 mm. "
        "This is an engineering approximation intended for setup tuning, not a lab-grade measurement."
    )

st.markdown(
    "<div class='footer-note'>Tip: use the original grip removal option when you replace the factory grip with an overgrip or towel grip, so the total mass stays accurate.</div>",
    unsafe_allow_html=True,
)
