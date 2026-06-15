"""
Nonprofit Outcomes & KPI Dashboard — Communicare Alliance
===========================================================
A Streamlit dashboard for tracking program outcomes, grant metrics,
and demographic breakdowns across multiple programs.

Install:
    pip install streamlit plotly pandas

Run:
    streamlit run outcomes_dashboard.py

Then open http://localhost:8501 in your browser.

To use your real data: replace the DATA section below with
pd.read_csv() or pd.read_excel() calls pointing to your files.
The rest of the dashboard updates automatically.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Page config — must be the very first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Communicare Alliance | Outcomes Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Brand colors
# ─────────────────────────────────────────────────────────────────────────────
TEAL       = "#1A6E6E"
TEAL_LIGHT = "#5DCAA5"
TEAL_PALE  = "#E1F5EE"
AMBER      = "#F59E0B"
AMBER_PALE = "#FEF3C7"
RED        = "#C0392B"
GREEN      = "#1A6E3A"
DARK       = "#1F2937"
GRAY       = "#6B7280"
BG         = "#F8FAFB"

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
    color: {DARK};
  }}

  /* Sidebar */
  [data-testid="stSidebar"] {{
    background: {TEAL} !important;
  }}
  [data-testid="stSidebar"] * {{
    color: white !important;
  }}
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stMultiSelect label {{
    color: rgba(255,255,255,0.8) !important;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}

  /* Page background */
  .stApp {{ background: {BG}; }}

  /* KPI cards */
  .kpi-card {{
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border-left: 4px solid {TEAL};
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    height: 100%;
  }}
  .kpi-card.amber {{ border-left-color: {AMBER}; }}
  .kpi-card.green {{ border-left-color: {GREEN}; }}
  .kpi-card.red   {{ border-left-color: {RED}; }}

  .kpi-label {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {GRAY};
    margin-bottom: 4px;
  }}
  .kpi-value {{
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: {DARK};
    line-height: 1.1;
  }}
  .kpi-delta {{
    font-size: 0.78rem;
    margin-top: 6px;
    color: {GRAY};
  }}
  .kpi-delta .pos {{ color: {GREEN}; font-weight: 600; }}
  .kpi-delta .neg {{ color: {RED};   font-weight: 600; }}
  .kpi-delta .neu {{ color: {AMBER}; font-weight: 600; }}

  /* Section headers */
  .section-header {{
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: {TEAL};
    margin: 2rem 0 0.5rem;
    padding-bottom: 6px;
    border-bottom: 2px solid {TEAL_PALE};
  }}

  /* Progress bars */
  .prog-wrap {{ margin-bottom: 14px; }}
  .prog-label {{
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    margin-bottom: 4px;
    color: {DARK};
  }}
  .prog-bar-bg {{
    background: #E5E7EB;
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
  }}
  .prog-bar-fill {{
    height: 100%;
    border-radius: 99px;
    transition: width 0.6s ease;
  }}

  /* Status badges */
  .badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
  }}
  .badge-green {{ background: #D1FAE5; color: #065F46; }}
  .badge-amber {{ background: {AMBER_PALE}; color: #92400E; }}
  .badge-red   {{ background: #FEE2E2; color: #991B1B; }}

  /* Dashboard title */
  .dash-title {{
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: {DARK};
    line-height: 1.15;
  }}
  .dash-sub {{
    font-size: 0.88rem;
    color: {GRAY};
    margin-top: 2px;
  }}

  /* Hide Streamlit chrome */
  #MainMenu, footer, header {{ visibility: hidden; }}
  .block-container {{ padding-top: 1.5rem; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ✏️  DATA — replace with pd.read_csv() or pd.read_excel() for real data
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    participants = pd.DataFrame([
        {"id":"P001","program":"Youth Mental Health","intake_date":"2025-01-08","age":14,"gender":"Female","race_ethnicity":"Latino","school":"Woonsocket High","sessions_attended":16,"sessions_scheduled":18,"phq_pre":17,"phq_post":9,"gad_pre":14,"gad_post":6,"discharged":False,"month":"Jan"},
        {"id":"P002","program":"Youth Mental Health","intake_date":"2025-01-10","age":15,"gender":"Male","race_ethnicity":"Latino","school":"Woonsocket High","sessions_attended":14,"sessions_scheduled":16,"phq_pre":13,"phq_post":7,"gad_pre":11,"gad_post":5,"discharged":False,"month":"Jan"},
        {"id":"P003","program":"Youth Mental Health","intake_date":"2025-01-15","age":13,"gender":"Female","race_ethnicity":"Black","school":"Hamlet MS","sessions_attended":10,"sessions_scheduled":14,"phq_pre":19,"phq_post":11,"gad_pre":16,"gad_post":9,"discharged":False,"month":"Jan"},
        {"id":"P004","program":"Youth Mental Health","intake_date":"2025-01-22","age":16,"gender":"Non-binary","race_ethnicity":"White","school":"Woonsocket High","sessions_attended":8,"sessions_scheduled":8,"phq_pre":12,"phq_post":8,"gad_pre":10,"gad_post":6,"discharged":True,"month":"Jan"},
        {"id":"P005","program":"Youth Mental Health","intake_date":"2025-02-03","age":14,"gender":"Female","race_ethnicity":"Latino","school":"Villa Nova MS","sessions_attended":12,"sessions_scheduled":14,"phq_pre":15,"phq_post":8,"gad_pre":13,"gad_post":7,"discharged":False,"month":"Feb"},
        {"id":"P006","program":"Youth Mental Health","intake_date":"2025-02-10","age":17,"gender":"Male","race_ethnicity":"Latino","school":"Woonsocket High","sessions_attended":13,"sessions_scheduled":14,"phq_pre":10,"phq_post":5,"gad_pre":9,"gad_post":4,"discharged":False,"month":"Feb"},
        {"id":"P007","program":"Youth Mental Health","intake_date":"2025-02-14","age":15,"gender":"Female","race_ethnicity":"Black","school":"Hamlet MS","sessions_attended":9,"sessions_scheduled":12,"phq_pre":18,"phq_post":12,"gad_pre":15,"gad_post":10,"discharged":False,"month":"Feb"},
        {"id":"P008","program":"Youth Mental Health","intake_date":"2025-02-20","age":13,"gender":"Male","race_ethnicity":"Latino","school":"Villa Nova MS","sessions_attended":8,"sessions_scheduled":8,"phq_pre":11,"phq_post":7,"gad_pre":8,"gad_post":5,"discharged":True,"month":"Feb"},
        {"id":"P009","program":"Youth Mental Health","intake_date":"2025-03-05","age":16,"gender":"Female","race_ethnicity":"Asian","school":"Woonsocket High","sessions_attended":10,"sessions_scheduled":12,"phq_pre":14,"phq_post":8,"gad_pre":12,"gad_post":6,"discharged":False,"month":"Mar"},
        {"id":"P010","program":"Youth Mental Health","intake_date":"2025-03-12","age":15,"gender":"Male","race_ethnicity":"Latino","school":"Woonsocket High","sessions_attended":11,"sessions_scheduled":12,"phq_pre":16,"phq_post":9,"gad_pre":13,"gad_post":7,"discharged":False,"month":"Mar"},
        {"id":"P011","program":"Youth Mental Health","intake_date":"2025-03-18","age":14,"gender":"Female","race_ethnicity":"Latino","school":"Hamlet MS","sessions_attended":8,"sessions_scheduled":10,"phq_pre":20,"phq_post":13,"gad_pre":17,"gad_post":11,"discharged":False,"month":"Mar"},
        {"id":"P012","program":"Youth Mental Health","intake_date":"2025-04-02","age":13,"gender":"Male","race_ethnicity":"Black","school":"Villa Nova MS","sessions_attended":6,"sessions_scheduled":8,"phq_pre":9,"phq_post":6,"gad_pre":7,"gad_post":4,"discharged":False,"month":"Apr"},
        {"id":"P013","program":"Youth Mental Health","intake_date":"2025-04-09","age":17,"gender":"Female","race_ethnicity":"Latino","school":"Woonsocket High","sessions_attended":8,"sessions_scheduled":8,"phq_pre":13,"phq_post":7,"gad_pre":11,"gad_post":5,"discharged":True,"month":"Apr"},
        {"id":"P014","program":"Youth Mental Health","intake_date":"2025-04-14","age":16,"gender":"Male","race_ethnicity":"White","school":"Woonsocket High","sessions_attended":7,"sessions_scheduled":8,"phq_pre":11,"phq_post":6,"gad_pre":9,"gad_post":4,"discharged":False,"month":"Apr"},
        {"id":"P015","program":"Youth Mental Health","intake_date":"2025-04-21","age":15,"gender":"Female","race_ethnicity":"Black","school":"Hamlet MS","sessions_attended":6,"sessions_scheduled":8,"phq_pre":15,"phq_post":9,"gad_pre":14,"gad_post":8,"discharged":False,"month":"Apr"},
        {"id":"P016","program":"Youth Mental Health","intake_date":"2025-05-01","age":14,"gender":"Female","race_ethnicity":"Latino","school":"Villa Nova MS","sessions_attended":4,"sessions_scheduled":6,"phq_pre":10,"phq_post":7,"gad_pre":8,"gad_post":5,"discharged":False,"month":"May"},
        {"id":"P017","program":"Youth Mental Health","intake_date":"2025-05-08","age":13,"gender":"Male","race_ethnicity":"Latino","school":"Hamlet MS","sessions_attended":5,"sessions_scheduled":6,"phq_pre":12,"phq_post":8,"gad_pre":10,"gad_post":7,"discharged":False,"month":"May"},
        {"id":"P018","program":"Youth Mental Health","intake_date":"2025-05-15","age":16,"gender":"Female","race_ethnicity":"Asian","school":"Woonsocket High","sessions_attended":5,"sessions_scheduled":6,"phq_pre":14,"phq_post":9,"gad_pre":12,"gad_post":7,"discharged":False,"month":"May"},
        # Family Support Program participants
        {"id":"P101","program":"Family Support","intake_date":"2025-01-12","age":35,"gender":"Female","race_ethnicity":"Latino","school":"N/A","sessions_attended":6,"sessions_scheduled":6,"phq_pre":14,"phq_post":7,"gad_pre":12,"gad_post":5,"discharged":True,"month":"Jan"},
        {"id":"P102","program":"Family Support","intake_date":"2025-01-20","age":42,"gender":"Female","race_ethnicity":"Black","school":"N/A","sessions_attended":5,"sessions_scheduled":6,"phq_pre":11,"phq_post":6,"gad_pre":9,"gad_post":4,"discharged":False,"month":"Jan"},
        {"id":"P103","program":"Family Support","intake_date":"2025-02-05","age":38,"gender":"Male","race_ethnicity":"Latino","school":"N/A","sessions_attended":6,"sessions_scheduled":6,"phq_pre":16,"phq_post":9,"gad_pre":13,"gad_post":6,"discharged":True,"month":"Feb"},
        {"id":"P104","program":"Family Support","intake_date":"2025-03-10","age":29,"gender":"Female","race_ethnicity":"Latino","school":"N/A","sessions_attended":4,"sessions_scheduled":6,"phq_pre":13,"phq_post":8,"gad_pre":11,"gad_post":7,"discharged":False,"month":"Mar"},
        {"id":"P105","program":"Family Support","intake_date":"2025-04-08","age":44,"gender":"Female","race_ethnicity":"White","school":"N/A","sessions_attended":6,"sessions_scheduled":6,"phq_pre":9,"phq_post":5,"gad_pre":8,"gad_post":4,"discharged":True,"month":"Apr"},
        {"id":"P106","program":"Family Support","intake_date":"2025-05-02","age":33,"gender":"Male","race_ethnicity":"Black","school":"N/A","sessions_attended":3,"sessions_scheduled":6,"phq_pre":15,"phq_post":11,"gad_pre":12,"gad_post":9,"discharged":False,"month":"May"},
    ])

    monthly = pd.DataFrame([
        {"month":"Jan","month_num":1,"program":"Youth Mental Health","new_intakes":4,"sessions":28,"groups":2,"family_workshops":1},
        {"month":"Feb","month_num":2,"program":"Youth Mental Health","new_intakes":5,"sessions":42,"groups":4,"family_workshops":1},
        {"month":"Mar","month_num":3,"program":"Youth Mental Health","new_intakes":4,"sessions":48,"groups":4,"family_workshops":0},
        {"month":"Apr","month_num":4,"program":"Youth Mental Health","new_intakes":3,"sessions":51,"groups":4,"family_workshops":1},
        {"month":"May","month_num":5,"program":"Youth Mental Health","new_intakes":2,"sessions":44,"groups":4,"family_workshops":1},
        {"month":"Jun","month_num":6,"program":"Youth Mental Health","new_intakes":0,"sessions":38,"groups":2,"family_workshops":0},
        {"month":"Jan","month_num":1,"program":"Family Support","new_intakes":2,"sessions":12,"groups":0,"family_workshops":0},
        {"month":"Feb","month_num":2,"program":"Family Support","new_intakes":1,"sessions":11,"groups":0,"family_workshops":0},
        {"month":"Mar","month_num":3,"program":"Family Support","new_intakes":1,"sessions":10,"groups":0,"family_workshops":0},
        {"month":"Apr","month_num":4,"program":"Family Support","new_intakes":2,"sessions":16,"groups":0,"family_workshops":0},
        {"month":"May","month_num":5,"program":"Family Support","new_intakes":1,"sessions":9,"groups":0,"family_workshops":0},
        {"month":"Jun","month_num":6,"program":"Family Support","new_intakes":0,"sessions":6,"groups":0,"family_workshops":0},
    ])

    budget = pd.DataFrame([
        {"category":"Personnel – LCSW (2 FTE)","budgeted":94000,"spent":47200,"program":"Youth Mental Health"},
        {"category":"Personnel – Health Educator","budgeted":42000,"spent":21000,"program":"Youth Mental Health"},
        {"category":"Personnel – Coordinator","budgeted":24000,"spent":12000,"program":"Youth Mental Health"},
        {"category":"Fringe Benefits","budgeted":44800,"spent":22400,"program":"Youth Mental Health"},
        {"category":"Supplies & Materials","budgeted":4200,"spent":2800,"program":"Youth Mental Health"},
        {"category":"Training & Prof. Dev.","budgeted":3500,"spent":1200,"program":"Youth Mental Health"},
        {"category":"Evaluation (URI SPH)","budgeted":8000,"spent":0,"program":"Youth Mental Health"},
        {"category":"Indirect / Overhead","budgeted":14800,"spent":7400,"program":"Youth Mental Health"},
        {"category":"Personnel – Case Manager","budgeted":52000,"spent":26000,"program":"Family Support"},
        {"category":"Supplies & Materials","budgeted":2000,"spent":950,"program":"Family Support"},
        {"category":"Indirect / Overhead","budgeted":6000,"spent":3000,"program":"Family Support"},
    ])

    objectives = pd.DataFrame([
        {"objective":"Youth served","target":75,"actual":18,"program":"Youth Mental Health","unit":"youth"},
        {"objective":"Sessions delivered","target":600,"actual":251,"program":"Youth Mental Health","unit":"sessions"},
        {"objective":"Resilience groups","target":4,"actual":2,"program":"Youth Mental Health","unit":"cohorts"},
        {"objective":"Family workshops","target":6,"actual":4,"program":"Youth Mental Health","unit":"workshops"},
        {"objective":"School staff trained","target":30,"actual":24,"program":"Youth Mental Health","unit":"staff"},
        {"objective":"Families served","target":40,"actual":6,"program":"Family Support","unit":"families"},
        {"objective":"Case management sessions","target":200,"actual":64,"program":"Family Support","unit":"sessions"},
        {"objective":"Employment referrals","target":20,"actual":7,"program":"Family Support","unit":"referrals"},
    ])

    return participants, monthly, budget, objectives


participants_df, monthly_df, budget_df, objectives_df = load_data()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌿 Communicare Alliance")
    st.markdown("**Outcomes Dashboard**")
    st.markdown("---")

    programs = ["All Programs"] + sorted(participants_df["program"].unique().tolist())
    selected_program = st.selectbox("Program", programs)

    all_months = ["All Months"] + ["Jan","Feb","Mar","Apr","May","Jun"]
    selected_months = st.multiselect("Report Period", all_months[1:], default=all_months[1:])
    if not selected_months:
        selected_months = all_months[1:]

    st.markdown("---")
    st.markdown("**Outcome Thresholds**")
    phq_threshold  = st.slider("Clinically Meaningful PHQ-A Drop (pts)", 3, 10, 5)
    attend_target  = st.slider("Attendance Rate Target (%)", 50, 100, 80)

    st.markdown("---")
    st.caption(f"Data as of {datetime.date.today().strftime('%B %d, %Y')}")
    st.caption("Communicare Alliance · Woonsocket, RI")

# ─────────────────────────────────────────────────────────────────────────────
# Filter data
# ─────────────────────────────────────────────────────────────────────────────
pdf = participants_df.copy()
mdf = monthly_df.copy()
bdf = budget_df.copy()
odf = objectives_df.copy()

if selected_program != "All Programs":
    pdf = pdf[pdf["program"] == selected_program]
    mdf = mdf[mdf["program"] == selected_program]
    bdf = bdf[bdf["program"] == selected_program]
    odf = odf[odf["program"] == selected_program]

pdf = pdf[pdf["month"].isin(selected_months)]
mdf = mdf[mdf["month"].isin(selected_months)]

# ─────────────────────────────────────────────────────────────────────────────
# Computed metrics
# ─────────────────────────────────────────────────────────────────────────────
total_served      = len(pdf)
total_sessions    = mdf["sessions"].sum()
attend_rate       = (pdf["sessions_attended"].sum() / pdf["sessions_scheduled"].sum() * 100) if len(pdf) > 0 else 0
discharged        = pdf[pdf["discharged"] == True]
meaningful_drop   = discharged[(discharged["phq_pre"] - discharged["phq_post"]) >= phq_threshold]
pct_meaningful    = len(meaningful_drop) / max(len(discharged), 1) * 100
budget_spent      = bdf["spent"].sum()
budget_total      = bdf["budgeted"].sum()
pct_budget        = budget_spent / budget_total * 100 if budget_total > 0 else 0
avg_phq_drop      = (discharged["phq_pre"] - discharged["phq_post"]).mean() if len(discharged) > 0 else 0
avg_gad_drop      = (discharged["gad_pre"] - discharged["gad_post"]).mean() if len(discharged) > 0 else 0
pct_poc           = (pdf["race_ethnicity"] != "White").sum() / max(len(pdf), 1) * 100

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([3, 1])
with col_title:
    program_label = selected_program if selected_program != "All Programs" else "All Programs"
    st.markdown(f'<div class="dash-title">Outcomes & KPI Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="dash-sub">{program_label} · {", ".join(selected_months)} 2025 · Communicare Alliance</div>', unsafe_allow_html=True)
with col_badge:
    st.markdown("<br>", unsafe_allow_html=True)
    if pct_budget < 60:
        st.markdown('<span class="badge badge-green">Budget On Track</span>', unsafe_allow_html=True)
    elif pct_budget < 80:
        st.markdown('<span class="badge badge-amber">Budget Monitor</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-red">Budget Alert</span>', unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">At a Glance</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)

kpis = [
    (k1, "Participants Served", total_served, f"of 75 half-year target", "teal", total_served >= 30),
    (k2, "Sessions Delivered",  int(total_sessions), f"Avg {total_sessions/max(total_served,1):.1f}/participant", "teal", True),
    (k3, "Attendance Rate",     f"{attend_rate:.0f}%", f"Target: {attend_target}%", "green" if attend_rate >= attend_target else "amber", attend_rate >= attend_target),
    (k4, "Clinical Outcomes",   f"{pct_meaningful:.0f}%", f"{len(meaningful_drop)}/{len(discharged)} discharged", "green" if pct_meaningful >= 75 else "red", pct_meaningful >= 75),
    (k5, "Budget Utilized",     f"{pct_budget:.0f}%", f"${budget_spent:,.0f} of ${budget_total:,.0f}", "teal" if pct_budget < 70 else "amber", True),
]

for col, label, value, sub, color, on_track in kpis:
    with col:
        delta_class = "pos" if on_track else "neg"
        delta_icon  = "↑" if on_track else "↓"
        st.markdown(f"""
        <div class="kpi-card {color if color != 'teal' else ''}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-delta">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Row 2: Sessions over time + Objectives tracker
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Service Delivery</div>', unsafe_allow_html=True)
col_line, col_obj = st.columns([3, 2])

with col_line:
    month_order = ["Jan","Feb","Mar","Apr","May","Jun"]
    month_totals = (
        mdf[mdf["month"].isin(selected_months)]
        .groupby("month")["sessions"]
        .sum()
        .reindex([m for m in month_order if m in selected_months])
        .reset_index()
    )
    month_totals.columns = ["Month","Sessions"]

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=month_totals["Month"], y=month_totals["Sessions"],
        mode="lines+markers",
        line=dict(color=TEAL, width=3),
        marker=dict(size=8, color=TEAL, line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor="rgba(26,110,110,0.08)",
        name="Sessions",
    ))
    fig_line.update_layout(
        title=dict(text="Sessions Delivered by Month", font=dict(size=14, color=DARK)),
        height=260, margin=dict(l=0,r=0,t=36,b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        yaxis=dict(gridcolor="#F3F4F6", zeroline=False),
        xaxis=dict(gridcolor="#F3F4F6"),
        showlegend=False,
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col_obj:
    st.markdown("**Objectives Progress**")
    for _, row in odf.iterrows():
        pct = min(row["actual"] / row["target"] * 100, 100) if row["target"] > 0 else 0
        color = TEAL if pct >= 40 else (AMBER if pct >= 20 else RED)
        st.markdown(f"""
        <div class="prog-wrap">
          <div class="prog-label">
            <span>{row['objective']}</span>
            <span style="color:{GRAY}">{row['actual']} / {row['target']} {row['unit']}</span>
          </div>
          <div class="prog-bar-bg">
            <div class="prog-bar-fill" style="width:{pct}%; background:{color};"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Row 3: Clinical outcomes + Demographics
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Clinical Outcomes & Demographics</div>', unsafe_allow_html=True)
col_out, col_demo = st.columns([3, 2])

with col_out:
    if len(discharged) > 0:
        fig_scatter = go.Figure()
        discharged_copy = discharged.copy()
        discharged_copy["drop"] = discharged_copy["phq_pre"] - discharged_copy["phq_post"]
        discharged_copy["meaningful"] = discharged_copy["drop"] >= phq_threshold

        fig_scatter.add_trace(go.Scatter(
            x=discharged_copy["phq_pre"],
            y=discharged_copy["phq_post"],
            mode="markers",
            marker=dict(
                size=12,
                color=[TEAL if m else RED for m in discharged_copy["meaningful"]],
                line=dict(color="white", width=1.5),
                opacity=0.85,
            ),
            text=discharged_copy["id"],
            hovertemplate="<b>%{text}</b><br>Pre: %{x} → Post: %{y}<extra></extra>",
        ))
        # Diagonal reference line
        max_val = max(discharged_copy["phq_pre"].max(), 24)
        fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                              line=dict(color=GRAY, dash="dot", width=1))
        fig_scatter.add_shape(type="line", x0=phq_threshold, y0=0, x1=max_val, y1=max_val-phq_threshold,
                              line=dict(color=TEAL_LIGHT, dash="dash", width=1.5))

        fig_scatter.update_layout(
            title=dict(text=f"PHQ-A Pre vs. Post (discharged) — teal = ≥{phq_threshold}pt drop", font=dict(size=13, color=DARK)),
            xaxis_title="PHQ-A at Intake", yaxis_title="PHQ-A at Discharge",
            height=300, margin=dict(l=0,r=0,t=40,b=0),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(gridcolor="#F3F4F6"),
            xaxis=dict(gridcolor="#F3F4F6"),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg PHQ-A Drop", f"{avg_phq_drop:.1f} pts", delta="clinical threshold: 5")
        c2.metric("Avg GAD-7 Drop", f"{avg_gad_drop:.1f} pts", delta="clinical threshold: 4")
        c3.metric("% Meaningful Outcomes", f"{pct_meaningful:.0f}%", delta="target: 75%")
    else:
        st.info("No discharged participants in selected period.")

with col_demo:
    re_counts = pdf["race_ethnicity"].value_counts().reset_index()
    re_counts.columns = ["Race/Ethnicity","Count"]

    fig_donut = go.Figure(go.Pie(
        labels=re_counts["Race/Ethnicity"],
        values=re_counts["Count"],
        hole=0.55,
        marker=dict(colors=[TEAL, TEAL_LIGHT, AMBER, "#9FE1CB", "#F9CB42", "#888"]),
        textinfo="percent+label",
        textfont=dict(size=11, family="DM Sans"),
        hovertemplate="%{label}: %{value} participants<extra></extra>",
    ))
    fig_donut.add_annotation(
        text=f"<b>{len(pdf)}</b><br><span style='font-size:11px'>participants</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=DARK, family="DM Sans"),
    )
    fig_donut.update_layout(
        title=dict(text="Race / Ethnicity", font=dict(size=13, color=DARK)),
        height=300, margin=dict(l=0,r=0,t=40,b=0),
        paper_bgcolor="white",
        showlegend=False,
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown(f"**Participants of color:** {pct_poc:.0f}%")
    gender_counts = pdf["gender"].value_counts()
    for g, n in gender_counts.items():
        st.markdown(f"- {g}: **{n}** ({n/max(len(pdf),1)*100:.0f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# Row 4: Budget breakdown
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Budget Utilization</div>', unsafe_allow_html=True)

col_bbar, col_btable = st.columns([3, 2])

with col_bbar:
    bdf_sorted = bdf.sort_values("budgeted", ascending=True)
    bdf_sorted["pct"] = bdf_sorted["spent"] / bdf_sorted["budgeted"] * 100

    fig_budget = go.Figure()
    fig_budget.add_trace(go.Bar(
        y=bdf_sorted["category"], x=bdf_sorted["budgeted"],
        name="Budgeted", orientation="h",
        marker_color="#E5E7EB",
    ))
    fig_budget.add_trace(go.Bar(
        y=bdf_sorted["category"], x=bdf_sorted["spent"],
        name="Spent", orientation="h",
        marker_color=TEAL,
    ))
    fig_budget.update_layout(
        barmode="overlay",
        title=dict(text="Budget vs. Spent by Line Item", font=dict(size=13, color=DARK)),
        height=320, margin=dict(l=0,r=20,t=40,b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(tickprefix="$", tickformat=",", gridcolor="#F3F4F6"),
        yaxis=dict(gridcolor="#F3F4F6"),
        legend=dict(orientation="h", y=-0.12),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_budget, use_container_width=True)

with col_btable:
    st.markdown("**Spend Rate by Category**")
    for _, row in bdf.iterrows():
        pct = row["spent"] / row["budgeted"] * 100 if row["budgeted"] > 0 else 0
        color = RED if pct > 80 else (AMBER if pct > 60 else TEAL)
        st.markdown(f"""
        <div class="prog-wrap">
          <div class="prog-label">
            <span style="font-size:0.8rem">{row['category']}</span>
            <span style="color:{GRAY};font-size:0.78rem">{pct:.0f}%</span>
          </div>
          <div class="prog-bar-bg">
            <div class="prog-bar-fill" style="width:{min(pct,100)}%; background:{color};"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Communicare Alliance · Woonsocket, RI · "
    f"Dashboard generated {datetime.date.today().strftime('%B %d, %Y')} · "
    "Data is confidential and for internal program management use only."
)
