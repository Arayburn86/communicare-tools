import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

st.set_page_config(page_title="Outcomes Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)

TEAL="#1A6E6E"; TEAL_L="#5DCAA5"; AMBER="#F59E0B"; RED="#C0392B"; GREEN="#1A6E3A"

# ── Sample data ───────────────────────────────────────────────────────────────

@st.cache_data
def sample_participants():
    return pd.DataFrame([
        {"id":"P001","program":"Youth Mental Health","month":"Jan","age":14,"gender":"Female","race_ethnicity":"Latino","sessions_attended":16,"sessions_scheduled":18,"phq_pre":17,"phq_post":9,"gad_pre":14,"gad_post":6,"discharged":False},
        {"id":"P002","program":"Youth Mental Health","month":"Jan","age":15,"gender":"Male","race_ethnicity":"Latino","sessions_attended":14,"sessions_scheduled":16,"phq_pre":13,"phq_post":7,"gad_pre":11,"gad_post":5,"discharged":False},
        {"id":"P003","program":"Youth Mental Health","month":"Feb","age":13,"gender":"Female","race_ethnicity":"Black","sessions_attended":10,"sessions_scheduled":14,"phq_pre":19,"phq_post":11,"gad_pre":16,"gad_post":9,"discharged":False},
        {"id":"P004","program":"Youth Mental Health","month":"Feb","age":16,"gender":"Non-binary","race_ethnicity":"White","sessions_attended":8,"sessions_scheduled":8,"phq_pre":12,"phq_post":8,"gad_pre":10,"gad_post":6,"discharged":True},
        {"id":"P005","program":"Youth Mental Health","month":"Mar","age":14,"gender":"Female","race_ethnicity":"Latino","sessions_attended":12,"sessions_scheduled":14,"phq_pre":15,"phq_post":8,"gad_pre":13,"gad_post":7,"discharged":False},
        {"id":"P006","program":"Youth Mental Health","month":"Mar","age":17,"gender":"Male","race_ethnicity":"Latino","sessions_attended":13,"sessions_scheduled":14,"phq_pre":10,"phq_post":5,"gad_pre":9,"gad_post":4,"discharged":True},
        {"id":"P007","program":"Youth Mental Health","month":"Apr","age":15,"gender":"Female","race_ethnicity":"Black","sessions_attended":9,"sessions_scheduled":12,"phq_pre":18,"phq_post":12,"gad_pre":15,"gad_post":10,"discharged":False},
        {"id":"P008","program":"Youth Mental Health","month":"Apr","age":13,"gender":"Male","race_ethnicity":"Latino","sessions_attended":8,"sessions_scheduled":8,"phq_pre":11,"phq_post":7,"gad_pre":8,"gad_post":5,"discharged":True},
        {"id":"P009","program":"Youth Mental Health","month":"May","age":16,"gender":"Female","race_ethnicity":"Asian","sessions_attended":10,"sessions_scheduled":12,"phq_pre":14,"phq_post":8,"gad_pre":12,"gad_post":6,"discharged":False},
        {"id":"P010","program":"Family Support","month":"Jan","age":35,"gender":"Female","race_ethnicity":"Latino","sessions_attended":6,"sessions_scheduled":6,"phq_pre":14,"phq_post":7,"gad_pre":12,"gad_post":5,"discharged":True},
        {"id":"P011","program":"Family Support","month":"Feb","age":42,"gender":"Female","race_ethnicity":"Black","sessions_attended":5,"sessions_scheduled":6,"phq_pre":11,"phq_post":6,"gad_pre":9,"gad_post":4,"discharged":False},
        {"id":"P012","program":"Family Support","month":"Mar","age":38,"gender":"Male","race_ethnicity":"Latino","sessions_attended":6,"sessions_scheduled":6,"phq_pre":16,"phq_post":9,"gad_pre":13,"gad_post":6,"discharged":True},
    ])

@st.cache_data
def sample_monthly():
    return pd.DataFrame([
        {"month":"Jan","program":"Youth Mental Health","sessions":28,"new_intakes":4},
        {"month":"Feb","program":"Youth Mental Health","sessions":42,"new_intakes":3},
        {"month":"Mar","program":"Youth Mental Health","sessions":48,"new_intakes":4},
        {"month":"Apr","program":"Youth Mental Health","sessions":51,"new_intakes":2},
        {"month":"May","program":"Youth Mental Health","sessions":44,"new_intakes":2},
        {"month":"Jan","program":"Family Support","sessions":12,"new_intakes":2},
        {"month":"Feb","program":"Family Support","sessions":11,"new_intakes":1},
        {"month":"Mar","program":"Family Support","sessions":10,"new_intakes":1},
        {"month":"Apr","program":"Family Support","sessions":16,"new_intakes":2},
        {"month":"May","program":"Family Support","sessions":9,"new_intakes":1},
    ])

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📊 Outcomes Dashboard")
st.caption("Interactive program outcomes, demographics, and session tracking.")

with st.sidebar:
    st.markdown("### Upload your data")
    st.markdown('<div style="background:#E1F5EE;border-radius:8px;padding:10px;font-size:.8rem;color:#085041">Upload an Excel file with two sheets:<br><strong>Participants</strong> and <strong>Monthly</strong></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload Excel", type=["xlsx"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Filters")

if uploaded:
    try:
        sheets = pd.read_excel(uploaded, sheet_name=None)
        df_p = sheets.get("Participants", pd.DataFrame())
        df_m = sheets.get("Monthly", pd.DataFrame())
        if df_p.empty:
            st.warning("Could not find 'Participants' sheet. Using sample data.")
            df_p = sample_participants(); df_m = sample_monthly()
        else:
            st.success(f"✅ Loaded {len(df_p)} participants from your file.")
    except Exception as e:
        st.error(f"Could not read file: {e}")
        df_p = sample_participants(); df_m = sample_monthly()
else:
    st.markdown('<div style="background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:12px">Showing sample data. Upload your Excel file in the sidebar to see your real data.</div>', unsafe_allow_html=True)
    df_p = sample_participants(); df_m = sample_monthly()

# Sidebar filters
with st.sidebar:
    prog_opts = ["All Programs"] + sorted(df_p["program"].unique().tolist())
    prog_sel  = st.selectbox("Program", prog_opts)
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    months_avail = [m for m in month_order if m in df_p["month"].values]
    months_sel = st.multiselect("Months", months_avail, default=months_avail)
    threshold = st.slider("PHQ-A meaningful drop threshold (pts)", 3, 10, 5)

# Filter
pdf = df_p.copy()
mdf = df_m.copy()
if prog_sel != "All Programs":
    pdf = pdf[pdf["program"] == prog_sel]
    mdf = mdf[mdf["program"] == prog_sel]
if months_sel:
    pdf = pdf[pdf["month"].isin(months_sel)]
    mdf = mdf[mdf["month"].isin(months_sel)]

# KPIs
n           = len(pdf)
total_sess  = mdf["sessions"].sum()
att_rate    = pdf["sessions_attended"].sum()/max(pdf["sessions_scheduled"].sum(),1)*100
disc        = pdf[pdf["discharged"]==True]
meaningful  = disc[(disc["phq_pre"]-disc["phq_post"])>=threshold]
pct_out     = len(meaningful)/max(len(disc),1)*100
pct_poc     = (pdf["race_ethnicity"]!="White").sum()/max(n,1)*100

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Participants", n)
k2.metric("Sessions", int(total_sess))
k3.metric("Attendance", f"{att_rate:.0f}%", delta="target: 80%")
k4.metric("Clinical outcomes", f"{pct_out:.0f}%", delta="target: 75%")
k5.metric("Participants of color", f"{pct_poc:.0f}%")

PLT = dict(paper_bgcolor="white", plot_bgcolor="white",
           font=dict(family="Segoe UI,Arial",size=12), margin=dict(l=10,r=10,t=36,b=10))

# Charts row 1
c1,c2 = st.columns([3,2])
with c1:
    mt = (mdf.groupby("month")["sessions"].sum()
          .reindex([m for m in month_order if m in months_sel]).reset_index())
    mt.columns = ["Month","Sessions"]
    fig1 = go.Figure([go.Scatter(x=mt["Month"],y=mt["Sessions"],mode="lines+markers",
        line=dict(color=TEAL,width=3),marker=dict(size=8,color=TEAL,line=dict(color="white",width=2)),
        fill="tozeroy",fillcolor="rgba(26,110,110,0.08)")])
    fig1.update_layout(title="Sessions by month",height=280,showlegend=False,**PLT)
    st.plotly_chart(fig1,use_container_width=True)

with c2:
    re = pdf["race_ethnicity"].value_counts()
    fig2 = go.Figure([go.Pie(labels=re.index,values=re.values,hole=0.55,
        marker=dict(colors=[TEAL,TEAL_L,AMBER,"#9FE1CB","#888"]),textinfo="percent+label")])
    fig2.update_layout(title="Race / ethnicity",height=280,showlegend=False,**PLT)
    st.plotly_chart(fig2,use_container_width=True)

# Charts row 2
c3,c4 = st.columns(2)
with c3:
    if len(disc) > 0:
        dc = disc.copy()
        dc["ok"] = (dc["phq_pre"]-dc["phq_post"]) >= threshold
        fig3 = go.Figure([go.Scatter(
            x=dc["phq_pre"],y=dc["phq_post"],mode="markers",
            marker=dict(size=12,color=[TEAL if m else RED for m in dc["ok"]],
                        line=dict(color="white",width=1.5)),
            text=dc["id"],hovertemplate="<b>%{text}</b> Pre:%{x} → Post:%{y}<extra></extra>")])
        mv = max(dc["phq_pre"].max(),24)
        fig3.add_shape(type="line",x0=0,y0=0,x1=mv,y1=mv,
            line=dict(color="#888",dash="dot",width=1))
        fig3.update_layout(title="PHQ-A pre vs. post (teal = meaningful improvement)",
            height=300,showlegend=False,
            xaxis=dict(title="At intake",gridcolor="#F3F4F6"),
            yaxis=dict(title="At discharge",gridcolor="#F3F4F6"),**PLT)
        st.plotly_chart(fig3,use_container_width=True)
    else:
        st.info("No discharged participants in selected filters.")

with c4:
    avg_drop = (disc["phq_pre"]-disc["phq_post"]).mean() if len(disc) else 0
    avg_gad  = (disc["gad_pre"]-disc["gad_post"]).mean() if len(disc) else 0

    st.markdown("### Clinical outcome summary")
    m1,m2 = st.columns(2)
    m1.metric("Avg PHQ-A drop", f"{avg_drop:.1f} pts", delta="threshold: 5")
    m2.metric("Avg GAD-7 drop", f"{avg_gad:.1f} pts", delta="threshold: 4")
    m1.metric("Meaningful outcomes", f"{pct_out:.0f}%", delta="target: 75%")
    m2.metric("Discharged YTD", len(disc))

    if len(disc) > 0:
        st.markdown(f"**{len(meaningful)} of {len(disc)}** discharged participants "
                    f"showed a meaningful improvement (PHQ-A drop ≥ {threshold} pts).")
