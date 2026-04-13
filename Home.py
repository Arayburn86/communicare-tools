"""
Communicare Alliance — Grant & Program Tools
Main entry point for the multi-page Streamlit app.
"""

import streamlit as st

st.set_page_config(
    page_title="Communicare Alliance Tools",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main { background: #F8FAFB; }
  .block-container { padding-top: 1.5rem; }
  h1 { color: #1A6E6E !important; }
  h2 { color: #1A6E6E !important; font-size: 1.15rem !important; }
  h3 { color: #1F2937 !important; }

  .tool-card {
    background: white;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    border-left: 4px solid #1A6E6E;
    transition: box-shadow 0.15s;
  }
  .tool-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.10); }
  .tool-card.amber  { border-left-color: #BA7517; }
  .tool-card.blue   { border-left-color: #185FA5; }
  .tool-card.purple { border-left-color: #534AB7; }
  .tool-card.coral  { border-left-color: #993C1D; }

  .badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 6px;
  }
  .badge-free   { background: #E1F5EE; color: #085041; }
  .badge-ai     { background: #EEEDFE; color: #3C3489; }
  .badge-upload { background: #DBEAFE; color: #1E40AF; }

  .section-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #6B7280;
    padding: 14px 0 6px;
    border-bottom: 1px solid #E5E7EB;
    margin-bottom: 10px;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────

st.markdown("""
<div style="background:#1A6E6E;border-radius:12px;padding:24px 28px;margin-bottom:24px">
  <div style="font-size:26px;font-weight:700;color:white;margin-bottom:4px">
    🌿 Communicare Alliance Grant & Program Tools
  </div>
  <div style="font-size:14px;color:#9FE1CB">
    Woonsocket, RI &nbsp;·&nbsp; Program Development & Grants Management Suite
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "Select a tool from the **sidebar** or click any card below to get started."
)

# ── Tool cards ──────────────────────────────────────────────────────────────

def card(title, desc, badge_label, badge_class, color=""):
    return f"""
    <div class="tool-card {color}">
      <div style="font-weight:600;font-size:15px;color:#1F2937;margin-bottom:4px">
        {title}
        <span class="badge {badge_class}">{badge_label}</span>
      </div>
      <div style="font-size:13px;color:#6B7280;line-height:1.5">{desc}</div>
    </div>"""

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-label">Grant writing</div>', unsafe_allow_html=True)
    st.markdown(card(
        "📋 Logic Model Builder",
        "Upload any document — Claude extracts your program data and builds a formatted landscape Word logic model.",
        "AI + Upload", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "✍️ Grant Narrative Generator",
        "Drafts all 6 sections of a grant narrative from your program data. Takes about 90 seconds.",
        "AI", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "✅ Compliance Checker",
        "Upload your RFP and draft narrative — Claude flags every missing or weak requirement.",
        "AI + Upload", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "💰 Budget Builder",
        "Enter your staff and costs, get a fully formatted 2-year Excel budget with live formulas.",
        "No AI needed", "badge-free", "amber"), unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-label">Program management</div>', unsafe_allow_html=True)
    st.markdown(card(
        "📊 Outcomes Dashboard",
        "Interactive charts for PHQ-A outcomes, session trends, demographics, and budget tracking.",
        "No AI needed", "badge-free", "blue"), unsafe_allow_html=True)
    st.markdown(card(
        "🔍 Grants Scraper",
        "Search Grants.gov for federal opportunities scored against Communicare's mission.",
        "No AI needed", "badge-free", "blue"), unsafe_allow_html=True)
    st.markdown(card(
        "🏦 Funder Tracker",
        "Scrape foundation websites, score alignment, track relationship status and next actions.",
        "No AI needed", "badge-free", "blue"), unsafe_allow_html=True)
    st.markdown(card(
        "📅 Deadline Tracker",
        "All your grant deadlines in one place with upcoming reminders.",
        "No AI needed", "badge-free", "purple"), unsafe_allow_html=True)

col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="section-label">Evaluation & reporting</div>', unsafe_allow_html=True)
    st.markdown(card(
        "📈 Evaluation Plan Generator",
        "Generates SMART outcomes, measurement tools, data collection timeline, and equity section.",
        "AI", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "📝 Quarterly Report Writer",
        "Enter your quarter's data — Claude writes the full narrative progress report ready to send.",
        "AI", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "🏘️ Community Data Dashboard",
        "Live Census, CDC PLACES, and RI state data for Woonsocket with paste-ready needs statements.",
        "No AI needed", "badge-free", "coral"), unsafe_allow_html=True)

with col4:
    st.markdown('<div class="section-label">Program design</div>', unsafe_allow_html=True)
    st.markdown(card(
        "🧩 Program Design Assistant",
        "Conversational tool that walks you through designing a new program — theory of change through budget.",
        "AI", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "📚 Boilerplate Library",
        "Searchable database of reusable org history, mission statements, pilot data, and staff bios.",
        "AI optional", "badge-ai"), unsafe_allow_html=True)
    st.markdown(card(
        "🎯 Needs Assessment Analyzer",
        "Upload your survey data — analyzes themes, runs statistics, produces a formatted Excel report.",
        "Upload", "badge-upload", "coral"), unsafe_allow_html=True)

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Communicare Alliance · Woonsocket, RI · "
    "Grant & Program Management Suite · "
    "AI-assisted tools — always review outputs before submitting to funders"
)
