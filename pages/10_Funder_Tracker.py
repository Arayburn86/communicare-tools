import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import io
import time

st.set_page_config(page_title="Funder Tracker", page_icon="🏦", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;
  font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.funder-card{background:white;border-radius:10px;padding:14px 18px;
  margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #1A6E6E}
.funder-card.amber{border-left-color:#BA7517}
.funder-card.red{border-left-color:#C0392B}
.funder-card.gray{border-left-color:#9CA3AF}
.badge{display:inline-block;padding:2px 9px;border-radius:99px;
  font-size:11px;font-weight:600;margin-right:4px}
.b-a{background:#D1FAE5;color:#065F46}
.b-b{background:#E1F5EE;color:#0F6E56}
.b-c{background:#FEF3C7;color:#92400E}
.b-r{background:#F1EFE8;color:#444441}
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Organisation focus — used for alignment scoring
# ─────────────────────────────────────────────────────────────────────────────

ORG_FOCUS = [
    "mental health","behavioral health","youth","adolescent","children",
    "trauma","resilience","family","community health","health equity",
    "underserved","low income","substance use","prevention","latino",
    "hispanic","bilingual","culturally responsive","social determinants",
    "wraparound","school based","community based","rhode island",
    "new england","woonsocket",
]

# ─────────────────────────────────────────────────────────────────────────────
# Pre-loaded foundation prospects
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_FUNDERS = [
    {"name":"Rhode Island Foundation",           "url":"https://rifoundation.org/grants",        "notes":"Largest RI community foundation; health & human services priority","geo":"Rhode Island"},
    {"name":"Champlin Foundation",               "url":"https://champlinfoundations.org/grant-guidelines","notes":"RI-only funder; capital + program; strong health focus","geo":"Rhode Island"},
    {"name":"van Beuren Charitable Foundation",  "url":"https://vanbeuren.org/grants",            "notes":"Newport-based; rural RI; health & human services","geo":"Rhode Island"},
    {"name":"Amica Companies Foundation",        "url":"https://www.amica.com/community",         "notes":"Providence-based corporate; education and community","geo":"Rhode Island"},
    {"name":"Robert Wood Johnson Foundation",    "url":"https://www.rwjf.org/en/grants",          "notes":"Largest US health philanthropy; health equity focus","geo":"National"},
    {"name":"Annie E. Casey Foundation",         "url":"https://www.aecf.org/work/grant-making",  "notes":"Children and families; ALICE population; evidence-based","geo":"National"},
    {"name":"Kresge Foundation",                 "url":"https://kresge.org/grants-social-investments","notes":"Health, arts, education; cities and low-income communities","geo":"National"},
    {"name":"W.K. Kellogg Foundation",           "url":"https://www.wkkf.org/grants",             "notes":"Children, families, communities; health and equity","geo":"National"},
    {"name":"Blue Cross Blue Shield Foundation of MA","url":"https://bluecrossmafoundation.org/grants","notes":"Health equity; behavioral health; New England","geo":"New England"},
    {"name":"Tufts Health Plan Foundation",      "url":"https://tuftshealthplanfoundation.org/grants","notes":"Healthy aging, health equity; New England","geo":"New England"},
    {"name":"Conrad N. Hilton Foundation",       "url":"https://www.hiltonfoundation.org/grants", "notes":"Vulnerable populations; homelessness, children","geo":"National"},
    {"name":"JPMorgan Chase Foundation",         "url":"https://www.jpmorganchase.com/impact/philanthropy","notes":"Workforce development, communities, financial health","geo":"National"},
]

STATUS_OPTIONS = [
    "Not contacted","Researching","Relationship","Applied","Funded","Declined","Not a fit"
]

STATUS_COLORS = {
    "Not contacted": "gray",
    "Researching":   "amber",
    "Relationship":  "teal",
    "Applied":       "amber",
    "Funded":        "green",
    "Declined":      "red",
    "Not a fit":     "gray",
}

TIER_META = {
    "A — Top priority":      ("b-a", "#065F46"),
    "B — Strong prospect":   ("b-b", "#0F6E56"),
    "C — Worth cultivating": ("b-c", "#92400E"),
    "Research — Low fit":    ("b-r", "#444441"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Alignment scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_alignment(text, geo=""):
    text = text.lower()
    score = 0; matched = []
    core   = ["mental health","behavioral health","youth","children","adolescent",
              "community health","health equity","trauma","family"]
    strong = ["underserved","low income","substance use","prevention","resilience",
              "culturally","bilingual","social determinants","wraparound"]
    for t in core:
        if t in text: score += 12; matched.append(t)
    for t in strong:
        if t in text: score += 7; matched.append(t)
    for loc in ["rhode island","new england","woonsocket","blackstone"]:
        if loc in text or loc in geo.lower():
            score += 15; matched.append(f"location:{loc}")
    for neg in ["higher education","university research","endowment","capital campaign"]:
        if neg in text: score -= 10
    score = max(0, min(100, score))
    return score, list(dict.fromkeys(matched))[:8]


def tier_from_score(score, geo):
    local = any(loc in geo.lower() for loc in ["rhode island","new england"])
    if score >= 70 or (score >= 55 and local): return "A — Top priority"
    elif score >= 45:                           return "B — Strong prospect"
    elif score >= 25:                           return "C — Worth cultivating"
    else:                                       return "Research — Low fit"

# ─────────────────────────────────────────────────────────────────────────────
# Web scraper
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def scrape_funder(name, url):
    result = {
        "name": name, "url": url,
        "mission": "", "focus_areas": [], "geographic_focus": "",
        "grant_range_min": None, "grant_range_max": None,
        "deadline_info": "", "contact_info": "",
        "raw_text": "", "status": "ok", "error": "",
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all(["nav","footer","script","style","header"]):
            tag.decompose()
        main = (soup.find("main") or soup.find("article") or soup.body)
        raw  = re.sub(r"\s+", " ", main.get_text(separator=" ") if main else "").strip()
        result["raw_text"] = raw[:6000]

        # Grant range
        for pat in [r'\$([0-9,]+)\s*(?:to|-|–)\s*\$([0-9,]+)',
                    r'up to\s+\$([0-9,]+)', r'maximum.*?\$([0-9,]+)']:
            m = re.search(pat, raw, re.IGNORECASE)
            if m:
                groups = m.groups()
                try:
                    if len(groups) == 2 and groups[1]:
                        result["grant_range_min"] = int(groups[0].replace(",",""))
                        result["grant_range_max"] = int(groups[1].replace(",",""))
                    else:
                        result["grant_range_max"] = int(groups[0].replace(",",""))
                except ValueError:
                    pass
                break

        # Deadline
        sentences = re.split(r"[.!?]", raw)
        dl_words  = ["deadline","due date","letter of inquiry","LOI","rolling","submit by"]
        found = [s.strip() for s in sentences if any(w.lower() in s.lower() for w in dl_words)]
        result["deadline_info"] = " | ".join(found[:2]) if found else "Check website"

        # Email
        em = re.search(r"[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}", raw)
        result["contact_info"] = em.group(0) if em else ""

        # Mission (first substantial paragraph)
        paras = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 80]
        if paras:
            result["mission"] = paras[0][:300]

    except requests.exceptions.ConnectionError:
        result["status"] = "error"
        result["error"]  = "Connection failed"
    except requests.exceptions.Timeout:
        result["status"] = "error"
        result["error"]  = "Request timed out"
    except Exception as e:
        result["status"] = "error"
        result["error"]  = str(e)[:120]
    return result

# ─────────────────────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────────────────────

def init_tracker():
    if "funders" not in st.session_state:
        # Load defaults with placeholder scores
        funders = []
        for f in DEFAULT_FUNDERS:
            score, matched = score_alignment(
                f["notes"] + " " + f.get("geo",""), f.get("geo","")
            )
            funders.append({
                "name":              f["name"],
                "url":               f["url"],
                "notes":             f["notes"],
                "geo":               f.get("geo",""),
                "mission":           "",
                "deadline_info":     "Not yet scraped",
                "contact_info":      "",
                "grant_range_min":   None,
                "grant_range_max":   None,
                "alignment_score":   score,
                "matched_terms":     ", ".join(matched),
                "priority_tier":     tier_from_score(score, f.get("geo","")),
                "relationship_status": "Not contacted",
                "last_contact_date": "",
                "last_contact_notes": "",
                "next_action":       "Research giving page",
                "next_action_date":  "",
                "scraped":           False,
            })
        st.session_state.funders = funders

def get_funders():
    return st.session_state.funders

def update_funder(name, updates):
    for f in st.session_state.funders:
        if f["name"] == name:
            f.update(updates)
            break

def add_funder(name, url, notes, geo):
    score, matched = score_alignment(notes + " " + geo, geo)
    st.session_state.funders.append({
        "name": name, "url": url, "notes": notes, "geo": geo,
        "mission": "", "deadline_info": "Not yet scraped",
        "contact_info": "", "grant_range_min": None, "grant_range_max": None,
        "alignment_score": score, "matched_terms": ", ".join(matched),
        "priority_tier": tier_from_score(score, geo),
        "relationship_status": "Not contacted",
        "last_contact_date": "", "last_contact_notes": "",
        "next_action": "Research giving page", "next_action_date": "",
        "scraped": False,
    })

def delete_funder(name):
    st.session_state.funders = [f for f in st.session_state.funders
                                 if f["name"] != name]

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

init_tracker()
funders = get_funders()

st.title("🏦 Funder Tracker")
st.caption("Track foundation prospects, scrape giving pages, and manage your funder relationships.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Summary")
    total = len(funders)
    by_tier = {}
    for f in funders:
        t = f.get("priority_tier","—")
        by_tier[t] = by_tier.get(t,0) + 1
    st.metric("Total funders tracked", total)
    for tier, count in sorted(by_tier.items()):
        badge_cls = TIER_META.get(tier, ("b-r","#444"))[0]
        st.caption(f"• {tier}: {count}")

    st.markdown("---")
    st.markdown("### Add a funder")
    with st.form("add_funder"):
        new_name  = st.text_input("Foundation name")
        new_url   = st.text_input("Giving page URL", placeholder="https://...")
        new_geo   = st.selectbox("Geographic focus",
            ["Rhode Island","New England","National","International"])
        new_notes = st.text_input("Notes")
        if st.form_submit_button("Add"):
            if new_name and new_url:
                add_funder(new_name, new_url, new_notes, new_geo)
                st.success(f"Added: {new_name}")
                st.rerun()

    st.markdown("---")
    st.markdown("### Filters")
    filter_tier   = st.multiselect("Priority tier",
        ["A — Top priority","B — Strong prospect","C — Worth cultivating","Research — Low fit"],
        default=["A — Top priority","B — Strong prospect"])
    filter_status = st.multiselect("Relationship status", STATUS_OPTIONS,
        default=[])
    filter_geo    = st.multiselect("Geography",
        ["Rhode Island","New England","National","International"], default=[])

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_prospects, tab_pipeline, tab_scrape, tab_export = st.tabs([
    "🎯 Prospects", "🔄 Pipeline", "🌐 Scrape websites", "⬇ Export"
])

# ── TAB 1: Prospects ──────────────────────────────────────────────────────────

with tab_prospects:
    # Apply filters
    filtered = funders
    if filter_tier:
        filtered = [f for f in filtered if f.get("priority_tier") in filter_tier]
    if filter_status:
        filtered = [f for f in filtered if f.get("relationship_status") in filter_status]
    if filter_geo:
        filtered = [f for f in filtered if f.get("geo") in filter_geo]

    # Sort by score
    filtered = sorted(filtered, key=lambda x: x.get("alignment_score",0), reverse=True)

    st.markdown(f"### {len(filtered)} funder(s)")

    for f in filtered:
        tier  = f.get("priority_tier","Research — Low fit")
        badge_cls = TIER_META.get(tier, ("b-r","#444"))[0]
        status = f.get("relationship_status","Not contacted")
        card_color = {"Not contacted":"","Researching":"amber",
                      "Relationship":"","Applied":"amber",
                      "Funded":"","Declined":"red","Not a fit":"gray"}.get(status,"")

        lo = f.get("grant_range_min")
        hi = f.get("grant_range_max")
        if lo and hi:   range_str = f"${lo:,}–${hi:,}"
        elif hi:        range_str = f"Up to ${hi:,}"
        else:           range_str = "Range not listed"

        with st.container():
            st.markdown(
                f'<div class="funder-card {card_color}">'
                f'<strong style="font-size:1rem">{f["name"]}</strong> '
                f'<span class="badge {badge_cls}">{tier}</span>'
                f'<span style="color:#9CA3AF;font-size:.8rem;margin-left:8px">'
                f'Score: {f.get("alignment_score",0)} · {f.get("geo","")} · {range_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                if f.get("notes"):
                    st.caption(f['notes'])
                if f.get("matched_terms"):
                    st.caption(f"Matched: {f['matched_terms']}")
                if f.get("deadline_info") and f["deadline_info"] not in ("Not yet scraped","Check website",""):
                    st.caption(f"📅 {f['deadline_info']}")

            with c2:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(status),
                    key=f"status_{f['name']}",
                    label_visibility="collapsed",
                )
                if new_status != status:
                    update_funder(f["name"], {"relationship_status": new_status})
                    st.rerun()

                new_action = st.text_input(
                    "Next action",
                    value=f.get("next_action",""),
                    key=f"action_{f['name']}",
                    placeholder="Next action...",
                    label_visibility="collapsed",
                )
                if new_action != f.get("next_action",""):
                    update_funder(f["name"], {"next_action": new_action})

            with c3:
                st.markdown(f"[Visit site]({f['url']})")
                if st.button("🗑", key=f"del_{f['name']}", help="Remove"):
                    delete_funder(f["name"])
                    st.rerun()

            st.markdown("---")

# ── TAB 2: Pipeline ───────────────────────────────────────────────────────────

with tab_pipeline:
    st.markdown("### Relationship pipeline")

    pipeline_stages = [
        ("Not contacted",  "Haven't reached out yet"),
        ("Researching",    "Learning about their priorities"),
        ("Relationship",   "Active cultivation — meetings, events"),
        ("Applied",        "Application submitted"),
        ("Funded",         "Active grant relationship"),
        ("Declined",       "Application declined"),
        ("Not a fit",      "Confirmed mismatch"),
    ]

    for stage, desc in pipeline_stages:
        stage_funders = [f for f in funders if f.get("relationship_status") == stage]
        if not stage_funders and stage in ("Funded","Declined","Not a fit"):
            continue

        color = {"Funded":"#D1FAE5","Applied":"#FEF3C7",
                 "Declined":"#FDECEA","Not contacted":"#F5F5F5"}.get(stage,"#F9FAFB")

        st.markdown(
            f'<div style="background:{color};border-radius:8px;padding:8px 14px;'
            f'margin-bottom:6px;font-weight:600;color:#1F2937">'
            f'{stage} <span style="font-weight:400;font-size:.85rem;color:#6B7280">— {desc}</span>'
            f' <span style="float:right;font-size:.85rem">{len(stage_funders)} funder(s)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if stage_funders:
            for f in sorted(stage_funders, key=lambda x: x.get("alignment_score",0), reverse=True):
                c1, c2, c3 = st.columns([3,2,2])
                c1.markdown(f"**{f['name']}** — Score: {f.get('alignment_score',0)}")
                c2.caption(f.get("next_action",""))
                c3.caption(f.get("last_contact_notes",""))
        st.markdown("")

# ── TAB 3: Scrape websites ────────────────────────────────────────────────────

with tab_scrape:
    st.markdown("### Scrape foundation websites")
    st.markdown(
        '<div class="hint">This visits each foundation\'s giving page and extracts grant ranges, '
        'deadlines, focus areas, and contact info. Takes 1-2 seconds per funder. '
        'Some sites may block scraping — results vary.</div>',
        unsafe_allow_html=True,
    )

    unscraped = [f for f in funders if not f.get("scraped")]
    scraped   = [f for f in funders if f.get("scraped")]

    c1, c2 = st.columns(2)
    c1.metric("Not yet scraped", len(unscraped))
    c2.metric("Already scraped", len(scraped))

    col1, col2 = st.columns(2)

    with col1:
        if unscraped:
            selected_to_scrape = st.multiselect(
                "Select funders to scrape",
                [f["name"] for f in unscraped],
                default=[f["name"] for f in unscraped[:3]],
            )
            if st.button("🌐 Scrape selected funders", use_container_width=True):
                to_do = [f for f in unscraped if f["name"] in selected_to_scrape]
                progress = st.progress(0, text="Starting...")
                for i, f in enumerate(to_do):
                    progress.progress(
                        (i+1)/len(to_do),
                        text=f"Scraping {f['name']}...",
                    )
                    result = scrape_funder(f["name"], f["url"])
                    if result["status"] == "ok":
                        score, matched = score_alignment(
                            result["raw_text"] + " " + result.get("mission",""),
                            f.get("geo","")
                        )
                        update_funder(f["name"], {
                            "mission":         result["mission"],
                            "deadline_info":   result["deadline_info"],
                            "contact_info":    result["contact_info"],
                            "grant_range_min": result["grant_range_min"],
                            "grant_range_max": result["grant_range_max"],
                            "alignment_score": score,
                            "matched_terms":   ", ".join(matched),
                            "priority_tier":   tier_from_score(score, f.get("geo","")),
                            "scraped":         True,
                        })
                        st.success(f"✅ {f['name']} — score: {score}")
                    else:
                        update_funder(f["name"], {"scraped": True,
                            "deadline_info": f"Error: {result['error']}"})
                        st.warning(f"⚠ {f['name']}: {result['error']}")
                    if i < len(to_do) - 1:
                        time.sleep(1)
                progress.empty()
                st.rerun()
        else:
            st.info("All funders have been scraped.")

    with col2:
        if scraped:
            st.markdown("**Scraped results:**")
            for f in sorted(scraped,
                            key=lambda x: x.get("alignment_score",0), reverse=True):
                lo = f.get("grant_range_min")
                hi = f.get("grant_range_max")
                range_str = (f"${lo:,}–${hi:,}" if lo and hi
                             else (f"Up to ${hi:,}" if hi else "—"))
                st.markdown(
                    f"**{f['name']}** — Score: {f.get('alignment_score',0)} · {range_str}"
                )
                if f.get("deadline_info"):
                    st.caption(f['deadline_info'])

# ── TAB 4: Export ─────────────────────────────────────────────────────────────

with tab_export:
    st.markdown("### Export your funder list")

    df = pd.DataFrame([{
        "Name":            f["name"],
        "URL":             f["url"],
        "Geography":       f.get("geo",""),
        "Alignment Score": f.get("alignment_score",0),
        "Priority Tier":   f.get("priority_tier",""),
        "Relationship":    f.get("relationship_status",""),
        "Grant Range":     (f"${f['grant_range_min']:,}–${f['grant_range_max']:,}"
                            if f.get("grant_range_min") and f.get("grant_range_max")
                            else (f"Up to ${f['grant_range_max']:,}"
                                  if f.get("grant_range_max") else "—")),
        "Deadline Info":   f.get("deadline_info",""),
        "Next Action":     f.get("next_action",""),
        "Notes":           f.get("notes",""),
        "Matched Terms":   f.get("matched_terms",""),
    } for f in sorted(funders,
                       key=lambda x: x.get("alignment_score",0), reverse=True)])

    st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Funder Prospects")
    st.download_button(
        "⬇ Download as Excel",
        data=out.getvalue(),
        file_name=f"funder_tracker_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )
