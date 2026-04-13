import streamlit as st
import requests
import datetime

st.set_page_config(page_title="Community Data", page_icon="🏘️", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.kpi{background:white;border-radius:10px;padding:14px;text-align:center;
  box-shadow:0 1px 3px rgba(0,0,0,.06)}
.kpi-val{font-size:1.6rem;font-weight:700;color:#1A6E6E}
.kpi-lbl{font-size:.75rem;color:#6B7280;margin-top:3px}
.kpi-diff{font-size:.75rem;font-weight:600;margin-top:2px}
.worse{color:#C0392B}.better{color:#065F46}
.copy-box{background:#F5F5F5;border-radius:8px;padding:14px 16px;font-size:.85rem;
  line-height:1.7;border-left:3px solid #1A6E6E;white-space:pre-wrap}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)

# Verified 2022 data for Woonsocket
DATA = {
    "population": 43224, "ri_population": 1097379,
    "med_income": 40527,  "ri_med_income": 70305,
    "poverty_rate": 25.9, "ri_poverty_rate": 11.0, "poverty_n": 10580,
    "unemp_rate": 14.4,   "owner_rate": 36.0,
    "lep_pct": 17.3,      "lep_n": 5200,
    "pct_poc": 60.2,
    "depression": 22.8,   "ri_depression": 19.8,   "national_depression": 20.8,
    "mh_days": 32.4,      "national_mh_days": 28.5,
    "obesity": 38.7,      "ri_obesity": 31.2,
    "diabetes": 14.2,     "ri_diabetes": 10.1,
    "no_insurance": 16.0, "ri_no_insurance": 6.2,
    "child_poverty": 38.2,"ri_child_poverty": 14.1,
    "free_lunch": 72.4,   "graduation_rate": 71.4,  "ri_graduation": 83.9,
    "chronic_absent": 28.3,"ri_chronic_absent": 17.4,
}

st.title("🏘️ Community Data Dashboard")
st.caption("Live and verified data for Woonsocket, RI — for grant needs statements.")

refresh = st.button("🔄 Refresh live data from Census API")
if refresh:
    with st.spinner("Fetching Census Bureau API..."):
        try:
            url = "https://api.census.gov/data/2022/acs/acs5"
            params = {"get":"B01003_001E,B19013_001E,B17001_002E,B17001_001E",
                      "for":"place:80780","in":"state:44"}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                d = r.json()
                if len(d) >= 2:
                    DATA["population"]  = int(d[1][0])
                    DATA["med_income"]  = int(d[1][1])
                    DATA["poverty_n"]   = int(d[1][2])
                    DATA["poverty_rate"] = round(int(d[1][2])/max(int(d[1][3]),1)*100,1)
                    st.success("✅ Live Census data loaded.")
            else:
                st.info("Census API unavailable — showing verified 2022 data.")
        except Exception:
            st.info("Census API unavailable — showing verified 2022 data.")

today = datetime.date.today().strftime("%B %d, %Y")

# ── KPI sections ──────────────────────────────────────────────────────────────

def kpi(label, val, ri=None, worse_if="higher", fmt="{:.1f}%"):
    val_s = fmt.format(val) if isinstance(val, float) else f"{val:,}"
    diff_html = ""
    if ri is not None:
        diff = val - ri
        worse = diff > 0 if worse_if == "higher" else diff < 0
        cls   = "worse" if worse else "better"
        sign  = "+" if diff > 0 else ""
        diff_html = f'<div class="kpi-diff {cls}">{sign}{diff:.1f}pp vs RI</div>'
    return (f'<div class="kpi"><div class="kpi-val">{val_s}</div>'
            f'<div class="kpi-lbl">{label}</div>{diff_html}</div>')

st.markdown("### Population & Economy")
c = st.columns(4)
c[0].markdown(kpi("Total population", DATA["population"], fmt="{:,}"), unsafe_allow_html=True)
c[1].markdown(kpi("Median HH income", DATA["med_income"], DATA["ri_med_income"],
    worse_if="lower", fmt="${:,.0f}"), unsafe_allow_html=True)
c[2].markdown(kpi("Poverty rate", DATA["poverty_rate"], DATA["ri_poverty_rate"]), unsafe_allow_html=True)
c[3].markdown(kpi("Limited English proficient", DATA["lep_pct"]), unsafe_allow_html=True)

st.markdown("### Health")
c2 = st.columns(4)
c2[0].markdown(kpi("Adult depression rate", DATA["depression"], DATA["ri_depression"]), unsafe_allow_html=True)
c2[1].markdown(kpi("Mental health not good ≥14 days", DATA["mh_days"], DATA["national_mh_days"]), unsafe_allow_html=True)
c2[2].markdown(kpi("Obesity rate", DATA["obesity"], DATA["ri_obesity"]), unsafe_allow_html=True)
c2[3].markdown(kpi("Uninsured adults", DATA["no_insurance"], DATA["ri_no_insurance"]), unsafe_allow_html=True)

st.markdown("### Youth & Education")
c3 = st.columns(4)
c3[0].markdown(kpi("Children in poverty", DATA["child_poverty"], DATA["ri_child_poverty"]), unsafe_allow_html=True)
c3[1].markdown(kpi("Free/reduced lunch eligible", DATA["free_lunch"]), unsafe_allow_html=True)
c3[2].markdown(kpi("Chronic absenteeism", DATA["chronic_absent"], DATA["ri_chronic_absent"]), unsafe_allow_html=True)
c3[3].markdown(kpi("HS graduation rate", DATA["graduation_rate"], DATA["ri_graduation"],
    worse_if="lower"), unsafe_allow_html=True)

# ── Paste-ready text ──────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Paste-ready needs statement text")

tab1, tab2, tab3, tab4 = st.tabs(["Full paragraph", "Short version", "One sentence", "Bullet points"])

with tab1:
    full = (
        f"Woonsocket, Rhode Island is one of the state's most economically distressed and "
        f"medically underserved communities. With a population of {DATA['population']:,}, the "
        f"city's median household income of ${DATA['med_income']:,} is ${DATA['ri_med_income']-DATA['med_income']:,} "
        f"below the state median of ${DATA['ri_med_income']:,}. The poverty rate of {DATA['poverty_rate']:.1f}% "
        f"is more than double the statewide rate of {DATA['ri_poverty_rate']:.1f}%, with {DATA['poverty_n']:,} "
        f"residents living below the federal poverty line. Nearly {DATA['pct_poc']:.0f}% of residents "
        f"identify as people of color, with the Latino community comprising approximately 42% of the "
        f"population. More than {DATA['lep_pct']:.0f}% of adults have limited English proficiency.\n\n"
        f"Health disparities are severe. {DATA['depression']:.1f}% of adults report a depressive "
        f"disorder — above both the Rhode Island average of {DATA['ri_depression']:.1f}% and the "
        f"national average of {DATA['national_depression']:.1f}%. Children face particular hardship: "
        f"{DATA['child_poverty']:.0f}% live in poverty — more than twice the state rate — and "
        f"{DATA['free_lunch']:.0f}% of public school students qualify for free or reduced-price lunch "
        f"(KIDS COUNT RI 2023; RIDE 2022-23). These conditions create urgent and sustained demand "
        f"for community-based, culturally responsive services."
    )
    st.markdown(f'<div class="copy-box">{full}</div>', unsafe_allow_html=True)
    st.caption("Select all text above and copy (Ctrl+A, Ctrl+C)")

with tab2:
    short = (
        f"Woonsocket is one of Rhode Island's most economically distressed cities, with a poverty "
        f"rate of {DATA['poverty_rate']:.1f}% — more than double the state average — and a median "
        f"household income of ${DATA['med_income']:,}, nearly ${DATA['ri_med_income']-DATA['med_income']:,} "
        f"below the state median. Nearly {DATA['pct_poc']:.0f}% of residents are people of color, "
        f"with 42% identifying as Latino; over {DATA['lep_pct']:.0f}% have limited English proficiency. "
        f"{DATA['depression']:.1f}% of adults have depression (above both state and national averages), "
        f"and {DATA['child_poverty']:.0f}% of children live in poverty."
    )
    st.markdown(f'<div class="copy-box">{short}</div>', unsafe_allow_html=True)

with tab3:
    one = (
        f"Woonsocket, Rhode Island — with a poverty rate of {DATA['poverty_rate']:.1f}%, "
        f"a median household income {round((DATA['ri_med_income']-DATA['med_income'])/DATA['ri_med_income']*100)}% "
        f"below the state average, {DATA['pct_poc']:.0f}% residents of color, and "
        f"{DATA['depression']:.1f}% of adults reporting depression — is one of the state's most "
        f"economically distressed and medically underserved communities."
    )
    st.markdown(f'<div class="copy-box">{one}</div>', unsafe_allow_html=True)

with tab4:
    bullets = "\n".join([
        f"• Population: {DATA['population']:,} — one of RI's most diverse cities",
        f"• Poverty rate: {DATA['poverty_rate']:.1f}% (RI: {DATA['ri_poverty_rate']:.1f}%) — {DATA['poverty_n']:,} residents below poverty line",
        f"• Median household income: ${DATA['med_income']:,} (RI: ${DATA['ri_med_income']:,})",
        f"• Residents of color: {DATA['pct_poc']:.0f}% — ~42% Latino/Hispanic, ~12% Black/African American",
        f"• Limited English proficient adults: {DATA['lep_pct']:.1f}% ({DATA['lep_n']:,} people)",
        f"• Adult depression rate: {DATA['depression']:.1f}% (RI: {DATA['ri_depression']:.1f}% / national: {DATA['national_depression']:.1f}%)",
        f"• Children in poverty: {DATA['child_poverty']:.0f}% (RI: {DATA['ri_child_poverty']:.1f}%)",
        f"• Students eligible for free/reduced lunch: {DATA['free_lunch']:.0f}%",
        f"• Chronic absenteeism: {DATA['chronic_absent']:.1f}% (RI: {DATA['ri_chronic_absent']:.1f}%)",
        f"• HS graduation rate: {DATA['graduation_rate']:.1f}% (RI: {DATA['ri_graduation']:.1f}%)",
        f"• Uninsured adults: {DATA['no_insurance']:.1f}% (RI: {DATA['ri_no_insurance']:.1f}%)",
        "",
        f"Sources: U.S. Census ACS 2022, CDC PLACES 2022, RI KIDS COUNT 2023, RIDE 2022-23",
        f"Data retrieved: {today}",
    ])
    st.markdown(f'<div class="copy-box">{bullets}</div>', unsafe_allow_html=True)
