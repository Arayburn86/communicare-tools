import streamlit as st
import requests
import pandas as pd
import datetime
import io

st.set_page_config(page_title="Grants Scraper", page_icon="🔍", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
</style>""", unsafe_allow_html=True)

st.title("🔍 Federal Grants Scraper")
st.caption("Search Grants.gov for federal opportunities matching Communicare Alliance's mission.")

ORG_FOCUS = [
    "mental health","behavioral health","youth","adolescent","children","trauma","resilience",
    "family","community health","health equity","underserved","low income","substance use",
    "prevention","latino","hispanic","bilingual","culturally responsive","social determinants",
    "wraparound","school based","community based","rhode island","new england","woonsocket",
]

DEFAULT_KEYWORDS = [
    "community mental health youth",
    "adolescent behavioral health",
    "trauma-informed youth services",
    "community health equity",
    "youth resilience program",
    "school-based mental health",
    "culturally responsive behavioral health",
    "family support services",
    "substance abuse prevention youth",
]

def score_alignment(title, desc):
    text = (title + " " + desc).lower()
    core = ["mental health","behavioral health","youth","children","adolescent","community health","trauma","family"]
    strong = ["underserved","low income","substance use","prevention","resilience","culturally","bilingual"]
    score = 0; matched = []
    for t in core:
        if t in text: score += 12; matched.append(t)
    for t in strong:
        if t in text: score += 7; matched.append(t)
    for loc in ["rhode island","new england","new hampshire","massachusetts","connecticut"]:
        if loc in text: score += 10; matched.append(loc)
    return min(score, 100), matched[:6]

def search_grants(keywords, agency_code=None):
    url = "https://api.grants.gov/v1/api/search2"
    results = []
    for kw in keywords:
        try:
            params = {"keyword": kw, "rows": 20, "startRecordNum": 0,
                      "oppStatuses": "forecasted|posted"}
            if agency_code: params["agencyCode"] = agency_code
            resp = requests.post(url, json=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                opps = data.get("data", {}).get("oppHits", [])
                for opp in opps:
                    opp_id = opp.get("id","")
                    if not any(r["id"] == opp_id for r in results):
                        title = opp.get("title","")
                        agency = opp.get("agencyName","")
                        desc = opp.get("synopsis","") or ""
                        score, matched = score_alignment(title, desc)
                        close_date = opp.get("closeDate","")
                        award_floor = opp.get("awardFloor","")
                        award_ceiling = opp.get("awardCeiling","")
                        results.append({
                            "id": opp_id,
                            "title": title,
                            "agency": agency,
                            "close_date": close_date,
                            "award_floor": award_floor,
                            "award_ceiling": award_ceiling,
                            "alignment_score": score,
                            "matched_terms": ", ".join(matched),
                            "status": opp.get("oppStatus",""),
                            "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
                        })
        except Exception:
            pass
    results.sort(key=lambda x: x["alignment_score"], reverse=True)
    return results

# ── Controls ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Search settings")
    keywords_text = st.text_area("Search keywords (one per line)",
        value="\n".join(DEFAULT_KEYWORDS[:5]), height=160)
    agency_filter = st.selectbox("Agency filter", [
        "All agencies",
        "SAMHSA (SAMSA)",
        "HHS (HHS)",
        "Dept of Education (ED)",
        "HRSA (HRSA)",
        "CDC (CDC)",
    ])
    min_score = st.slider("Minimum alignment score", 0, 80, 30)
    st.markdown("---")
    st.markdown("### About alignment scoring")
    st.caption("Scores 0–100 based on how well the grant matches Communicare's focus areas: "
               "mental health, youth, equity, RI/New England, bilingual services.")

agency_map = {
    "All agencies": None,
    "SAMHSA (SAMSA)": "SAMSA",
    "HHS (HHS)": "HHS",
    "Dept of Education (ED)": "ED",
    "HRSA (HRSA)": "HRSA",
    "CDC (CDC)": "CDC",
}

c1, c2 = st.columns([3,1])
with c1:
    st.markdown('<div class="hint">Searches the live Grants.gov API. Results are scored for '
                'alignment with Communicare Alliance\'s mission. Higher score = better fit.</div>',
                unsafe_allow_html=True)
with c2:
    search_btn = st.button("🔍 Search Grants.gov", use_container_width=True)

if search_btn:
    keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]
    agency   = agency_map.get(agency_filter)

    with st.spinner(f"Searching {len(keywords)} keyword combinations..."):
        results = search_grants(keywords, agency)

    filtered = [r for r in results if r["alignment_score"] >= min_score]

    st.markdown(f"## Results — {len(filtered)} opportunities (score ≥ {min_score})")

    if not filtered:
        st.info("No results found. Try lowering the minimum score or changing keywords.")
    else:
        # Summary metrics
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total found", len(filtered))
        m2.metric("High alignment (≥60)", sum(1 for r in filtered if r["alignment_score"]>=60))
        m3.metric("Open/Posted", sum(1 for r in filtered if "posted" in r["status"].lower()))
        m4.metric("Avg score", round(sum(r["alignment_score"] for r in filtered)/len(filtered)))

        # Table
        df = pd.DataFrame(filtered)
        df = df[["title","agency","alignment_score","matched_terms","close_date",
                 "award_floor","award_ceiling","status","url"]]
        df.columns = ["Title","Agency","Score","Matched Terms",
                      "Close Date","Award Min","Award Max","Status","URL"]

        # Color-code score
        def color_score(val):
            if val >= 60: return "background-color: #D1FAE5; color: #065F46; font-weight: 600"
            elif val >= 40: return "background-color: #FEF3C7; color: #92400E"
            return ""

        st.dataframe(
            df.drop(columns=["URL"]).style.applymap(color_score, subset=["Score"]),
            use_container_width=True,
            height=400,
        )

        # Links for top results
        st.markdown("### Top matches — click to view on Grants.gov")
        for r in filtered[:5]:
            st.markdown(
                f"**[{r['title']}]({r['url']})** — {r['agency']}  "
                f"· Score: **{r['alignment_score']}**  "
                f"· {r['matched_terms']}"
            )

        # Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Grants")
        st.download_button(
            "⬇ Download results as Excel",
            data=output.getvalue(),
            file_name=f"grants_search_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
