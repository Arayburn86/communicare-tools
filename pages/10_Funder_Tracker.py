import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import io
import time
import re

st.set_page_config(page_title="Funder Tracker", page_icon="🏦", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.save-ok{background:#D1FAE5;border-left:3px solid #065F46;border-radius:0 8px 8px 0;
  padding:8px 14px;font-size:.85rem;color:#065F46;margin-bottom:8px}
.funder-card{background:white;border-radius:10px;padding:14px 18px;margin-bottom:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #1A6E6E}
.funder-card.amber{border-left-color:#BA7517}
.funder-card.red{border-left-color:#C0392B}
.funder-card.gray{border-left-color:#9CA3AF}
</style>""", unsafe_allow_html=True)

# ── Google Sheets helper ───────────────────────────────────────────────────────

try:
    from gsheets_helper import load_funders, save_funders, DEFAULT_FUNDERS, FUNDER_HEADERS
    SHEETS_AVAILABLE = True
except Exception as e:
    SHEETS_AVAILABLE = False
    SHEETS_ERROR = str(e)

STATUS_OPTIONS = [
    "Not contacted","Researching","Relationship","Applied","Funded","Declined","Not a fit"
]
TIER_META = {
    "A — Top priority":"#065F46","B — Strong prospect":"#0F6E56",
    "C — Worth cultivating":"#92400E","Research — Low fit":"#444441",
}

def score_alignment(text, geo=""):
    text = text.lower(); score = 0; matched = []
    core   = ["mental health","behavioral health","youth","children","adolescent","community health","health equity","trauma","family"]
    strong = ["underserved","low income","substance use","prevention","resilience","culturally","bilingual","social determinants"]
    for t in core:
        if t in text: score+=12; matched.append(t)
    for t in strong:
        if t in text: score+=7; matched.append(t)
    for loc in ["rhode island","new england","woonsocket","blackstone"]:
        if loc in text or loc in geo.lower(): score+=15; matched.append(f"location:{loc}")
    return max(0,min(100,score)), list(dict.fromkeys(matched))[:8]

def tier_from_score(score, geo):
    local = any(loc in geo.lower() for loc in ["rhode island","new england"])
    if score>=70 or (score>=55 and local): return "A — Top priority"
    elif score>=45:                         return "B — Strong prospect"
    elif score>=25:                         return "C — Worth cultivating"
    else:                                   return "Research — Low fit"

# ── Session state ──────────────────────────────────────────────────────────────

def init_tracker():
    if "funders" not in st.session_state:
        if SHEETS_AVAILABLE:
            with st.spinner("Loading funders from Google Sheets..."):
                try:
                    st.session_state.funders    = load_funders()
                    st.session_state.sheets_ok  = True
                except Exception as e:
                    st.session_state.funders    = list(DEFAULT_FUNDERS)
                    st.session_state.sheets_ok  = False
                    st.session_state.sheets_err = str(e)
        else:
            st.session_state.funders    = list(DEFAULT_FUNDERS)
            st.session_state.sheets_ok  = False
            st.session_state.sheets_err = SHEETS_ERROR if not SHEETS_AVAILABLE else ""
        st.session_state.last_saved = None

def persist():
    if st.session_state.get("sheets_ok"):
        ok = save_funders(st.session_state.funders)
        if ok:
            st.session_state.last_saved = datetime.datetime.now().strftime("%I:%M %p")

def get_funders(): return st.session_state.funders

def update_funder(name, updates):
    for f in st.session_state.funders:
        if f["name"]==name: f.update(updates); break
    persist()

def add_funder(name, url, notes, geo):
    score, matched = score_alignment(notes+" "+geo, geo)
    st.session_state.funders.append({
        "name":name,"url":url,"geo":geo,"notes":notes,
        "alignment_score":score,"matched_terms":", ".join(matched),
        "priority_tier":tier_from_score(score,geo),
        "relationship_status":"Not contacted","next_action":"Research giving page",
        "last_contact_notes":"","grant_range_min":"","grant_range_max":"",
        "deadline_info":"Not yet scraped","contact_info":"","scraped":"False",
    })
    persist()

def delete_funder(name):
    st.session_state.funders = [f for f in st.session_state.funders if f["name"]!=name]
    persist()

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

def scrape_funder(name, url):
    result={"status":"ok","error":"","deadline_info":"","contact_info":"","grant_range_min":None,"grant_range_max":None,"raw_text":""}
    try:
        resp=requests.get(url,headers=HEADERS,timeout=15); resp.raise_for_status()
        soup=BeautifulSoup(resp.text,"html.parser")
        for tag in soup.find_all(["nav","footer","script","style","header"]): tag.decompose()
        main=soup.find("main") or soup.find("article") or soup.body
        raw=re.sub(r"\s+"," ",main.get_text(separator=" ") if main else "").strip()
        result["raw_text"]=raw[:6000]
        for pat in [r'\$([0-9,]+)\s*(?:to|-|–)\s*\$([0-9,]+)',r'up to\s+\$([0-9,]+)']:
            m=re.search(pat,raw,re.IGNORECASE)
            if m:
                try:
                    g=m.groups()
                    if len(g)==2 and g[1]: result["grant_range_min"]=int(g[0].replace(",","")); result["grant_range_max"]=int(g[1].replace(",",""))
                    else: result["grant_range_max"]=int(g[0].replace(",",""))
                except: pass
                break
        sents=re.split(r"[.!?]",raw)
        dl=[s.strip() for s in sents if any(w.lower() in s.lower() for w in ["deadline","due date","LOI","rolling","submit by"])]
        result["deadline_info"]=" | ".join(dl[:2]) if dl else "Check website"
        em=re.search(r"[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}",raw)
        result["contact_info"]=em.group(0) if em else ""
    except requests.exceptions.ConnectionError: result["status"]="error"; result["error"]="Connection failed"
    except requests.exceptions.Timeout:         result["status"]="error"; result["error"]="Request timed out"
    except Exception as e:                       result["status"]="error"; result["error"]=str(e)[:120]
    return result

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

init_tracker()
funders = get_funders()

st.title("🏦 Funder Tracker")
st.caption("Track foundation prospects — saved permanently to Google Sheets.")

if st.session_state.get("sheets_ok"):
    msg = f" at {st.session_state.last_saved}" if st.session_state.last_saved else ""
    st.markdown(f'<div class="save-ok">✅ Connected to Google Sheets{msg} — changes save automatically.</div>',
                unsafe_allow_html=True)
else:
    st.markdown('<div class="warn">⚠ Google Sheets not connected — using session data only. '
                'Add credentials to Streamlit Secrets to enable persistence.</div>',
                unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Summary")
    by_tier={}
    for f in funders:
        t=f.get("priority_tier","—"); by_tier[t]=by_tier.get(t,0)+1
    st.metric("Total funders", len(funders))
    for tier,count in sorted(by_tier.items()):
        st.caption(f"• {tier}: {count}")
    st.markdown("---")
    st.markdown("### Add a funder")
    with st.form("add_funder"):
        nn=st.text_input("Foundation name")
        nu=st.text_input("Giving page URL")
        ng=st.selectbox("Geography",["Rhode Island","New England","National","International"])
        nt=st.text_input("Notes")
        if st.form_submit_button("Add"):
            if nn and nu:
                add_funder(nn,nu,nt,ng)
                st.success(f"Added: {nn}" + (" — saved to Google Sheets." if st.session_state.get("sheets_ok") else "."))
                st.rerun()
    st.markdown("---")
    st.markdown("### Filters")
    filter_tier   = st.multiselect("Priority tier",
        ["A — Top priority","B — Strong prospect","C — Worth cultivating","Research — Low fit"],
        default=["A — Top priority","B — Strong prospect"])
    filter_status = st.multiselect("Status", STATUS_OPTIONS, default=[])
    if st.button("🔄 Reload from Google Sheets", use_container_width=True,
                 disabled=not st.session_state.get("sheets_ok")):
        for k in ["funders","last_saved"]: st.session_state.pop(k,None)
        st.rerun()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_prospects, tab_pipeline, tab_scrape, tab_export = st.tabs([
    "🎯 Prospects","🔄 Pipeline","🌐 Scrape websites","⬇ Export"
])

# ── Prospects ──────────────────────────────────────────────────────────────────

with tab_prospects:
    filtered = funders
    if filter_tier:   filtered=[f for f in filtered if f.get("priority_tier") in filter_tier]
    if filter_status: filtered=[f for f in filtered if f.get("relationship_status") in filter_status]
    filtered=sorted(filtered,key=lambda x:x.get("alignment_score",0),reverse=True)
    st.markdown(f"### {len(filtered)} funder(s)")
    for f in filtered:
        tier=f.get("priority_tier","Research — Low fit")
        tc=TIER_META.get(tier,"#444")
        status=f.get("relationship_status","Not contacted")
        card_c={"Declined":"red","Not a fit":"gray","Researching":"amber"}.get(status,"")
        lo=f.get("grant_range_min",""); hi=f.get("grant_range_max","")
        try:    range_str=f"${int(lo):,}–${int(hi):,}" if lo and hi else (f"Up to ${int(hi):,}" if hi else "—")
        except: range_str="—"
        st.markdown(
            f'<div class="funder-card {card_c}"><strong style="font-size:1rem">{f["name"]}</strong>'
            f'<span style="background:#E1F5EE;color:{tc};padding:2px 9px;border-radius:99px;'
            f'font-size:11px;font-weight:600;margin-left:8px">{tier}</span>'
            f'<span style="color:#9CA3AF;font-size:.8rem;margin-left:8px">'
            f'Score: {f.get("alignment_score",0)} · {f.get("geo","")} · {range_str}</span></div>',
            unsafe_allow_html=True)
        c1,c2,c3=st.columns([3,2,1])
        with c1:
            if f.get("notes"):         st.caption(f["notes"])
            if f.get("matched_terms"): st.caption(f"Matched: {f['matched_terms']}")
            if f.get("deadline_info") and f["deadline_info"] not in ("Not yet scraped","Check website",""):
                st.caption(f"📅 {f['deadline_info']}")
        with c2:
            new_status=st.selectbox("Status",STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0,
                key=f"status_{f['name']}",label_visibility="collapsed")
            if new_status!=status:
                update_funder(f["name"],{"relationship_status":new_status}); st.rerun()
            new_action=st.text_input("Next action",value=f.get("next_action",""),
                key=f"action_{f['name']}",placeholder="Next action...",label_visibility="collapsed")
            if new_action!=f.get("next_action",""):
                update_funder(f["name"],{"next_action":new_action})
        with c3:
            st.markdown(f"[Visit site]({f['url']})")
            if st.button("🗑",key=f"del_{f['name']}"):
                delete_funder(f["name"]); st.rerun()
        st.markdown("---")

# ── Pipeline ───────────────────────────────────────────────────────────────────

with tab_pipeline:
    st.markdown("### Relationship pipeline")
    stages=[("Not contacted","Haven't reached out"),("Researching","Learning priorities"),
            ("Relationship","Active cultivation"),("Applied","Application submitted"),
            ("Funded","Active grant"),("Declined","Application declined"),("Not a fit","Confirmed mismatch")]
    for stage,desc in stages:
        sf=[f for f in funders if f.get("relationship_status")==stage]
        if not sf and stage in ("Funded","Declined","Not a fit"): continue
        color={"Funded":"#D1FAE5","Applied":"#FEF3C7","Declined":"#FDECEA","Not contacted":"#F5F5F5"}.get(stage,"#F9FAFB")
        st.markdown(f'<div style="background:{color};border-radius:8px;padding:8px 14px;margin-bottom:6px;'
                    f'font-weight:600;color:#1F2937">{stage} '
                    f'<span style="font-weight:400;font-size:.85rem;color:#6B7280">— {desc}</span>'
                    f'<span style="float:right;font-size:.85rem">{len(sf)}</span></div>',
                    unsafe_allow_html=True)
        for f in sorted(sf,key=lambda x:x.get("alignment_score",0),reverse=True):
            c1,c2,c3=st.columns([3,2,2])
            c1.markdown(f"**{f['name']}** — Score: {f.get('alignment_score',0)}")
            c2.caption(f.get("next_action",""))
            c3.caption(f.get("last_contact_notes",""))

# ── Scrape ─────────────────────────────────────────────────────────────────────

with tab_scrape:
    st.markdown("### Scrape foundation websites")
    st.markdown('<div class="hint">Visits each giving page and extracts grant ranges, deadlines, and contact info. Updates save to Google Sheets.</div>',
                unsafe_allow_html=True)
    unscraped=[f for f in funders if str(f.get("scraped","False")).lower()!="true"]
    scraped  =[f for f in funders if str(f.get("scraped","False")).lower()=="true"]
    c1,c2=st.columns(2)
    c1.metric("Not yet scraped",len(unscraped))
    c2.metric("Already scraped",len(scraped))
    if unscraped:
        selected=st.multiselect("Select funders to scrape",
            [f["name"] for f in unscraped],default=[f["name"] for f in unscraped[:3]])
        if st.button("🌐 Scrape selected"):
            to_do=[f for f in unscraped if f["name"] in selected]
            prog=st.progress(0,text="Starting...")
            for i,f in enumerate(to_do):
                prog.progress((i+1)/len(to_do),text=f"Scraping {f['name']}...")
                result=scrape_funder(f["name"],f["url"])
                if result["status"]=="ok":
                    score,matched=score_alignment(result["raw_text"],f.get("geo",""))
                    update_funder(f["name"],{
                        "deadline_info":result["deadline_info"],
                        "contact_info":result["contact_info"],
                        "grant_range_min":result["grant_range_min"] or "",
                        "grant_range_max":result["grant_range_max"] or "",
                        "alignment_score":score,"matched_terms":", ".join(matched),
                        "priority_tier":tier_from_score(score,f.get("geo","")),
                        "scraped":"True"})
                    st.success(f"✅ {f['name']} — score: {score}")
                else:
                    update_funder(f["name"],{"scraped":"True","deadline_info":f"Error: {result['error']}"})
                    st.warning(f"⚠ {f['name']}: {result['error']}")
                if i<len(to_do)-1: time.sleep(1)
            prog.empty(); st.rerun()

# ── Export ─────────────────────────────────────────────────────────────────────

with tab_export:
    st.markdown("### Export your funder list")
    df=pd.DataFrame([{
        "Name":f["name"],"URL":f["url"],"Geography":f.get("geo",""),
        "Score":f.get("alignment_score",0),"Tier":f.get("priority_tier",""),
        "Status":f.get("relationship_status",""),"Next Action":f.get("next_action",""),
        "Notes":f.get("notes",""),"Deadline":f.get("deadline_info",""),
        "Matched":f.get("matched_terms",""),
    } for f in sorted(funders,key=lambda x:x.get("alignment_score",0),reverse=True)])
    st.dataframe(df,use_container_width=True,hide_index=True,height=400)
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        df.to_excel(w,index=False,sheet_name="Funder Prospects")
    st.download_button("⬇ Download as Excel",data=out.getvalue(),
        file_name=f"funder_tracker_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
