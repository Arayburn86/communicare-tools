import streamlit as st
import pandas as pd
import datetime
import io

st.set_page_config(page_title="Deadline Tracker", page_icon="📅", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)

SAMPLE_DEADLINES = pd.DataFrame([
    {"grant_name":"Youth Mental Health Expansion","funder":"Rhode Island Foundation",
     "deadline":datetime.date.today()+datetime.timedelta(days=45),
     "amount":185000,"type":"Full proposal","assigned_to":"Program Dev Manager",
     "notes":"LOI approved — ready to draft"},
    {"grant_name":"CHW Initiative","funder":"Blue Cross Blue Shield Foundation",
     "deadline":datetime.date.today()+datetime.timedelta(days=14),
     "amount":75000,"type":"Letter of Inquiry","assigned_to":"Executive Director",
     "notes":"First contact needed"},
    {"grant_name":"SAMHSA MHAT","funder":"SAMHSA (Federal)",
     "deadline":datetime.date.today()+datetime.timedelta(days=60),
     "amount":500000,"type":"Full proposal","assigned_to":"Program Dev Manager",
     "notes":"Need SF-424 and logic model"},
    {"grant_name":"Family Support Renewal","funder":"Champlin Foundation",
     "deadline":datetime.date.today()+datetime.timedelta(days=7),
     "amount":50000,"type":"Full proposal","assigned_to":"Executive Director",
     "notes":"Strong relationship — renewal"},
    {"grant_name":"School-Based MH","funder":"van Beuren Charitable Foundation",
     "deadline":datetime.date.today()+datetime.timedelta(days=90),
     "amount":40000,"type":"Letter of Inquiry","assigned_to":"Program Dev Manager",
     "notes":"New prospect"},
])

st.title("📅 Grant Deadline Tracker")
st.caption("All your grant deadlines in one place with urgency flags.")

with st.sidebar:
    st.markdown("### Upload your deadlines")
    st.markdown("""Upload a CSV or Excel file with columns:
`grant_name`, `funder`, `deadline`, `amount`, `type`, `assigned_to`, `notes`""")
    uploaded = st.file_uploader("Upload deadlines file",
        type=["csv","xlsx"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Add a deadline")
    with st.form("add_deadline"):
        new_name    = st.text_input("Grant name")
        new_funder  = st.text_input("Funder")
        new_date    = st.date_input("Deadline", min_value=datetime.date.today())
        new_amount  = st.number_input("Amount ($)", min_value=0, value=50000, step=5000)
        new_type    = st.selectbox("Type", ["Full proposal","Letter of Inquiry","Report","Other"])
        new_assign  = st.text_input("Assigned to")
        new_notes   = st.text_input("Notes")
        submitted   = st.form_submit_button("Add deadline")

if "deadlines" not in st.session_state:
    st.session_state.deadlines = SAMPLE_DEADLINES.copy()

if uploaded:
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded, parse_dates=["deadline"])
        else:
            df = pd.read_excel(uploaded, parse_dates=["deadline"])
        df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
        st.session_state.deadlines = df
        st.success(f"✅ Loaded {len(df)} deadlines.")
    except Exception as e:
        st.error(f"Could not read file: {e}")

if submitted and new_name and new_funder:
    new_row = pd.DataFrame([{
        "grant_name":new_name,"funder":new_funder,"deadline":new_date,
        "amount":new_amount,"type":new_type,"assigned_to":new_assign,"notes":new_notes
    }])
    st.session_state.deadlines = pd.concat(
        [st.session_state.deadlines, new_row], ignore_index=True)
    st.rerun()

df = st.session_state.deadlines.copy()
today = datetime.date.today()
df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
df["days_until"] = df["deadline"].apply(lambda d: (d - today).days)
df = df[df["days_until"] >= 0].sort_values("days_until")

# Summary metrics
past   = (st.session_state.deadlines["deadline"].apply(
    lambda d: (pd.to_datetime(d).date() - today).days) < 0).sum()
urgent = (df["days_until"] <= 7).sum()
soon   = ((df["days_until"] > 7) & (df["days_until"] <= 30)).sum()

m1,m2,m3,m4 = st.columns(4)
m1.metric("Upcoming deadlines", len(df))
m2.metric("🚨 Due within 7 days", urgent, delta="urgent" if urgent > 0 else None,
          delta_color="inverse")
m3.metric("📅 Due within 30 days", soon)
m4.metric("Past deadlines", past)

if urgent > 0:
    names = ", ".join(df[df["days_until"]<=7]["grant_name"].tolist())
    st.error(f"🚨 **Due within 7 days:** {names}")

# Table with colour coding
st.markdown("## All upcoming deadlines")

def flag(days):
    if days <= 7:  return "🚨"
    if days <= 14: return "⚠️"
    if days <= 30: return "📅"
    return "  "

display = df.copy()
display["urgency"] = display["days_until"].apply(flag)
display["amount_fmt"] = display["amount"].apply(
    lambda x: f"${int(x):,}" if pd.notna(x) else "—")
display["deadline_fmt"] = display["deadline"].apply(
    lambda d: d.strftime("%b %d, %Y") if pd.notna(d) else "—")

show_cols = ["urgency","grant_name","funder","deadline_fmt","days_until",
             "amount_fmt","type","assigned_to","notes"]
col_names = ["","Grant","Funder","Deadline","Days Left","Amount","Type","Assigned To","Notes"]

st.dataframe(
    display[show_cols].rename(columns=dict(zip(show_cols, col_names))),
    use_container_width=True,
    hide_index=True,
    height=400,
)

# Download
out = io.BytesIO()
export = df[["grant_name","funder","deadline","days_until","amount","type","assigned_to","notes"]]
with pd.ExcelWriter(out, engine="openpyxl") as w:
    export.to_excel(w, index=False, sheet_name="Deadlines")
st.download_button("⬇ Download as Excel", data=out.getvalue(),
    file_name=f"grant_deadlines_{today}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
