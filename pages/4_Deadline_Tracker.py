import streamlit as st
import pandas as pd
import datetime
import io

st.set_page_config(page_title="Deadline Tracker", page_icon="📅", layout="wide")
st.markdown("""<style>
h1{color:#1A6E6E!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)

SAMPLE = pd.DataFrame([
    {"grant_name":"Youth Mental Health Expansion","funder":"Rhode Island Foundation","deadline":datetime.date.today()+datetime.timedelta(days=45),"amount":185000,"type":"Full proposal","assigned_to":"Program Dev Manager","notes":"LOI approved"},
    {"grant_name":"CHW Initiative","funder":"Blue Cross Blue Shield Foundation","deadline":datetime.date.today()+datetime.timedelta(days=14),"amount":75000,"type":"Letter of Inquiry","assigned_to":"Executive Director","notes":"First contact needed"},
    {"grant_name":"SAMHSA MHAT","funder":"SAMHSA (Federal)","deadline":datetime.date.today()+datetime.timedelta(days=60),"amount":500000,"type":"Full proposal","assigned_to":"Program Dev Manager","notes":"Need SF-424"},
    {"grant_name":"Family Support Renewal","funder":"Champlin Foundation","deadline":datetime.date.today()+datetime.timedelta(days=7),"amount":50000,"type":"Full proposal","assigned_to":"Executive Director","notes":"Strong relationship"},
    {"grant_name":"School-Based MH","funder":"van Beuren Charitable Foundation","deadline":datetime.date.today()+datetime.timedelta(days=90),"amount":40000,"type":"Letter of Inquiry","assigned_to":"Program Dev Manager","notes":"New prospect"},
])

st.title("📅 Grant Deadline Tracker")
st.caption("All your grant deadlines in one place with urgency flags.")

with st.sidebar:
    st.markdown("### Upload your deadlines")
    st.markdown("Upload a CSV or Excel with columns: grant_name, funder, deadline, amount, type, assigned_to, notes")
    uploaded = st.file_uploader("Upload", type=["csv","xlsx"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Add a deadline")
    with st.form("add"):
        n_name   = st.text_input("Grant name")
        n_funder = st.text_input("Funder")
        n_date   = st.date_input("Deadline", min_value=datetime.date.today())
        n_amount = st.number_input("Amount ($)", 0, 2000000, 50000, 5000)
        n_type   = st.selectbox("Type", ["Full proposal","Letter of Inquiry","Report","Other"])
        n_assign = st.text_input("Assigned to")
        n_notes  = st.text_input("Notes")
        submitted = st.form_submit_button("Add")

if "deadlines" not in st.session_state:
    st.session_state.deadlines = SAMPLE.copy()

if uploaded:
    try:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
        st.session_state.deadlines = df
        st.success(f"✅ Loaded {len(df)} deadlines.")
    except Exception as e:
        st.error(f"Could not read file: {e}")

if submitted and n_name and n_funder:
    st.session_state.deadlines = pd.concat([st.session_state.deadlines,
        pd.DataFrame([{"grant_name":n_name,"funder":n_funder,"deadline":n_date,
            "amount":n_amount,"type":n_type,"assigned_to":n_assign,"notes":n_notes}])],
        ignore_index=True)
    st.rerun()

df = st.session_state.deadlines.copy()
today = datetime.date.today()
df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
df["days_until"] = df["deadline"].apply(lambda d: (d-today).days)
df = df[df["days_until"]>=0].sort_values("days_until")

urgent = (df["days_until"]<=7).sum()
m1,m2,m3 = st.columns(3)
m1.metric("Upcoming deadlines", len(df))
m2.metric("🚨 Due within 7 days", urgent)
m3.metric("📅 Due within 30 days", ((df["days_until"]>7)&(df["days_until"]<=30)).sum())

if urgent > 0:
    st.error(f"🚨 **Due within 7 days:** {', '.join(df[df['days_until']<=7]['grant_name'].tolist())}")

display = df.copy()
display["urgency"] = display["days_until"].apply(lambda d: "🚨" if d<=7 else ("⚠️" if d<=14 else ("📅" if d<=30 else "  ")))
display["amount_fmt"] = display["amount"].apply(lambda x: f"${int(x):,}" if pd.notna(x) else "—")
display["deadline_fmt"] = display["deadline"].apply(lambda d: d.strftime("%b %d, %Y"))

show = ["urgency","grant_name","funder","deadline_fmt","days_until","amount_fmt","type","assigned_to","notes"]
names = ["","Grant","Funder","Deadline","Days Left","Amount","Type","Assigned To","Notes"]
st.dataframe(display[show].rename(columns=dict(zip(show,names))), use_container_width=True, hide_index=True, height=400)

out = io.BytesIO()
with pd.ExcelWriter(out, engine="openpyxl") as w:
    df[["grant_name","funder","deadline","days_until","amount","type","assigned_to","notes"]].to_excel(w, index=False, sheet_name="Deadlines")
st.download_button("⬇ Download as Excel", data=out.getvalue(),
    file_name=f"grant_deadlines_{today}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
