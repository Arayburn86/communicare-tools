import streamlit as st
import anthropic
import os
import datetime
import io
import json

st.set_page_config(page_title="Quarterly Report Writer", page_icon="📝", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
h3{color:#1F2937!important;font-size:1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.narrative-box{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
  padding:14px 18px;font-size:.9rem;line-height:1.7;color:#1F2937;margin-bottom:10px}
.section-head{font-weight:600;color:#1A6E6E;font-size:1rem;margin:16px 0 6px;
  padding-bottom:4px;border-bottom:2px solid #E1F5EE}
</style>""", unsafe_allow_html=True)


def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")


QUARTER_MONTHS = {
    1: ("January",  "March"),
    2: ("April",    "June"),
    3: ("July",     "September"),
    4: ("October",  "December"),
}


def quarter_label(q, yr):
    s, e = QUARTER_MONTHS[q]
    return f"Q{q} {yr} ({s} – {e} {yr})"


SYSTEM = """You are an expert grant writer for a nonprofit. Write clear, professional,
data-driven progress reports for foundation funders. Lead with numbers, be honest
about challenges and show how they are being addressed. Write in connected prose
paragraphs — no bullet points, no markdown, no section headings."""


def generate_section(client, prompt):
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📝 Quarterly Report Writer")
st.caption("Enter your quarter's data — Claude writes the full narrative progress report.")

api_key = get_api_key()
if not api_key:
    st.markdown(
        '<div class="warn">⚠ API key not set. Add ANTHROPIC_API_KEY in '
        'Streamlit Cloud → Settings → Secrets.</div>',
        unsafe_allow_html=True,
    )

# Initialise session state
if "qr_sections" not in st.session_state:
    st.session_state.qr_sections = {}
if "qr_generated" not in st.session_state:
    st.session_state.qr_generated = False

# ── Input form ────────────────────────────────────────────────────────────────

with st.expander("## Step 1 — Grant & program details", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        org_name     = st.text_input("Organization",   "Communicare Alliance")
        program_name = st.text_input("Program name",   "Youth Mental Health & Resilience Program")
        funder_name  = st.text_input("Funder",         "Rhode Island Foundation")
        grant_number = st.text_input("Grant number",   "RIF-2025-0847")
    with c2:
        report_quarter = st.selectbox("Report quarter", [1, 2, 3, 4], index=1)
        report_year    = st.number_input("Year", 2024, 2030, 2025)
        grant_period   = st.text_input("Grant period", "January 2025 – December 2026")
        report_author  = st.text_input("Prepared by",  "Program Development & Grants Manager")

with st.expander("## Step 2 — Service delivery data", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        youth_this_q = st.number_input("Youth enrolled this quarter", 0, 500, 14)
        youth_ytd    = st.number_input("Youth enrolled year-to-date", 0, 500, 28)
        annual_target = st.number_input("Annual enrollment target",   0, 500, 75)
    with c2:
        sessions_q   = st.number_input("Sessions this quarter",  0, 5000, 156)
        sessions_ytd = st.number_input("Sessions year-to-date",  0, 5000, 312)
        sessions_target = st.number_input("Annual sessions target", 0, 5000, 600)
    with c3:
        attendance   = st.number_input("Attendance rate (%)",  0.0, 100.0, 83.2)
        groups_done  = st.number_input("Group cohorts completed", 0, 20, 1)
        workshops    = st.number_input("Workshops held",          0, 20, 2)

with st.expander("## Step 3 — Outcomes data", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        discharged_q   = st.number_input("Discharged this quarter",  0, 200, 8)
        discharged_ytd = st.number_input("Discharged year-to-date",  0, 200, 14)
        pct_phq        = st.number_input("PHQ-A improvement rate (%)", 0.0, 100.0, 78.6)
    with c2:
        avg_phq_pre  = st.number_input("Avg PHQ-A at intake",    0.0, 27.0, 15.4)
        avg_phq_post = st.number_input("Avg PHQ-A at discharge", 0.0, 27.0, 8.2)
        pct_poc      = st.number_input("Participants of color (%)", 0.0, 100.0, 89.3)
    with c3:
        pct_cope    = st.number_input("COPE improvement rate (%)",     0.0, 100.0, 82.0)
        pct_wkshop  = st.number_input("Workshop satisfaction (%)",     0.0, 100.0, 88.3)
        staff_trained = st.number_input("School staff trained YTD",    0, 200, 18)

with st.expander("## Step 4 — Budget", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        total_budget = st.number_input("Total grant budget ($)", 0, 2000000, 185000, step=5000)
        spent_ytd    = st.number_input("Spent year-to-date ($)", 0, 2000000, 72400, step=1000)
    with c2:
        expected_ytd = st.number_input("Expected to have spent ($)", 0, 2000000, 74500, step=1000)

with st.expander("## Step 5 — Highlights, challenges & next steps", expanded=True):
    highlights_text = st.text_area(
        "Key highlights this quarter (one per line)",
        value=(
            "Completed first resilience group cohort at Woonsocket High School — 82% showed meaningful improvement\n"
            "Hired and onboarded bilingual LCSW #2 — both clinical positions now fully staffed\n"
            "Delivered trauma-informed training to 18 Hamlet Middle School staff"
        ),
        height=100,
    )
    challenges_text = st.text_area(
        "Challenges this quarter (one per line)",
        value=(
            "Family workshop attendance lower than projected due to end-of-year school events — moving to Saturday format in Q3\n"
            "EHR COPE scale configuration delayed — now resolved as of May"
        ),
        height=80,
    )
    next_q_text = st.text_area(
        "Plans for next quarter (one per line)",
        value=(
            "Launch two additional group cohorts at Villa Nova MS and Hamlet MS\n"
            "Host 2 family workshops in new Saturday morning format\n"
            "Begin peer mentor recruitment (target: 15 mentors)"
        ),
        height=80,
    )

# ── Generate ──────────────────────────────────────────────────────────────────

ql   = quarter_label(report_quarter, report_year)
base = (
    f"Organization: {org_name}, Woonsocket RI. Program: {program_name}. "
    f"Funder: {funder_name}. Reporting period: {ql}. Grant period: {grant_period}."
)
avg_phq_drop  = round(avg_phq_pre - avg_phq_post, 1)
pct_budget    = round(spent_ytd / total_budget * 100, 1) if total_budget > 0 else 0
budget_ok     = abs(spent_ytd - expected_ytd) / max(total_budget, 1) < 0.10
highlights    = [h.strip() for h in highlights_text.split("\n") if h.strip()]
challenges    = [c.strip() for c in challenges_text.split("\n") if c.strip()]
next_q        = [n.strip() for n in next_q_text.split("\n") if n.strip()]

gen_col, _ = st.columns([2, 3])
with gen_col:
    generate_btn = st.button(
        "✨ Generate report narrative",
        disabled=not api_key,
        use_container_width=True,
    )

if generate_btn:
    client   = anthropic.Anthropic(api_key=api_key)
    sections = {}
    progress = st.progress(0, text="Writing executive summary...")

    prompts = {
        "executive_summary": (
            f"{base}\n\nWrite a brief executive summary (120–150 words) starting with "
            f"'{org_name} is pleased to report...' Include: program on track, headline numbers, "
            f"1-2 standout results.\n"
            f"Key data: Youth YTD: {youth_ytd}/{annual_target} target. "
            f"Sessions YTD: {sessions_ytd}/{sessions_target}. "
            f"PHQ-A improvement: {pct_phq}% (target 75%). "
            f"Budget: {pct_budget}% utilized."
        ),
        "program_activities": (
            f"{base}\n\nWrite Program Activities (200–250 words) describing this quarter. "
            f"Youth enrolled this quarter: {youth_this_q}. YTD total: {youth_ytd}. "
            f"Sessions: {sessions_q} (attendance {attendance}%). "
            f"Groups completed: {groups_done}. Workshops: {workshops}. "
            f"Staff trained: {staff_trained}.\n"
            f"Weave in these highlights:\n" +
            "\n".join(f"- {h}" for h in highlights)
        ),
        "outcomes": (
            f"{base}\n\nWrite Participant Outcomes (200–250 words). "
            f"Discharged this quarter: {discharged_q} ({discharged_ytd} YTD). "
            f"PHQ-A meaningful improvement: {pct_phq}% (target 75%). "
            f"Avg PHQ-A intake: {avg_phq_pre}, discharge: {avg_phq_post}, drop: {avg_phq_drop} pts. "
            f"COPE improvement: {pct_cope}%. Workshop satisfaction: {pct_wkshop}%. "
            f"Participants of color: {pct_poc}%. "
            f"Emphasize the clinical significance and equity of these results."
        ),
        "objectives_progress": (
            f"{base}\n\nWrite Objectives Progress (150–200 words). "
            f"Enrollment: {youth_ytd}/{annual_target} ({round(youth_ytd/annual_target*100) if annual_target else 0}% of annual target). "
            f"Sessions: {sessions_ytd}/{sessions_target}. "
            f"PHQ-A improvement: {pct_phq}% vs 75% target. "
            f"Budget: {pct_budget}% utilized ({'on track' if budget_ok else 'slight variance'}). "
            f"Mention which objectives are on track and address any that need attention constructively."
        ),
        "challenges": (
            f"{base}\n\nWrite Challenges and Adaptations (100–150 words). "
            f"Present these honestly but frame as learning with proactive response:\n" +
            "\n".join(f"- {c}" for c in challenges)
        ),
        "next_quarter": (
            f"{base}\n\nWrite Looking Ahead (100–140 words) about next quarter plans. "
            f"Frame with confidence and connect to annual targets:\n" +
            "\n".join(f"- {n}" for n in next_q)
        ),
    }

    section_labels = {
        "executive_summary":   "Executive summary",
        "program_activities":  "Program activities",
        "outcomes":            "Participant outcomes",
        "objectives_progress": "Objectives progress",
        "challenges":          "Challenges & adaptations",
        "next_quarter":        "Looking ahead",
    }

    for i, (key, prompt) in enumerate(prompts.items()):
        progress.progress(
            (i + 1) / len(prompts),
            text=f"Writing {section_labels[key]}...",
        )
        sections[key] = generate_section(client, prompt)

    progress.empty()
    st.session_state.qr_sections = sections
    st.session_state.qr_generated = True
    st.rerun()

# ── Display results ───────────────────────────────────────────────────────────

if st.session_state.qr_generated and st.session_state.qr_sections:
    sec = st.session_state.qr_sections
    today = datetime.date.today().strftime("%B %d, %Y")

    st.markdown("---")
    st.markdown("## Generated Report")

    # Header
    st.markdown(
        f"**{program_name}** — Quarterly Progress Report — {ql}  \n"
        f"{org_name} · {funder_name} · {grant_number} · {today}"
    )

    # KPI strip
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Youth YTD",       youth_ytd)
    k2.metric("Sessions YTD",    sessions_ytd)
    k3.metric("PHQ-A outcomes",  f"{pct_phq}%")
    k4.metric("Attendance",      f"{attendance}%")
    k5.metric("Budget utilized", f"{pct_budget}%")

    section_order = [
        ("1. Executive Summary",          "executive_summary"),
        ("2. Program Activities",         "program_activities"),
        ("3. Participant Outcomes",       "outcomes"),
        ("4. Objectives Progress",        "objectives_progress"),
        ("5. Challenges & Adaptations",   "challenges"),
        ("6. Looking Ahead",              "next_quarter"),
    ]

    for title, key in section_order:
        st.markdown(f'<div class="section-head">{title}</div>', unsafe_allow_html=True)
        # Editable narrative
        edited = st.text_area(
            title,
            value=sec.get(key, ""),
            height=160,
            key=f"edit_{key}",
            label_visibility="collapsed",
        )
        st.session_state.qr_sections[key] = edited

    st.markdown(
        '<div class="warn">📝 Review every section above before sending. '
        'Edit directly in the text boxes — changes are saved automatically.</div>',
        unsafe_allow_html=True,
    )

    # Download as formatted text
    full_text = f"""{program_name}
QUARTERLY PROGRESS REPORT — {ql}
{org_name} · {funder_name} · Grant #{grant_number}
Prepared by: {report_author} · {today}

{'='*60}

KEY METRICS
Youth served YTD: {youth_ytd} | Sessions YTD: {sessions_ytd}
PHQ-A improvement: {pct_phq}% | Attendance: {attendance}%
Budget utilized: {pct_budget}%

{'='*60}

1. EXECUTIVE SUMMARY
{st.session_state.qr_sections.get('executive_summary', '')}

2. PROGRAM ACTIVITIES — {ql}
{st.session_state.qr_sections.get('program_activities', '')}

3. PARTICIPANT OUTCOMES
{st.session_state.qr_sections.get('outcomes', '')}

4. OBJECTIVES PROGRESS
{st.session_state.qr_sections.get('objectives_progress', '')}

5. CHALLENGES AND ADAPTATIONS
{st.session_state.qr_sections.get('challenges', '')}

6. LOOKING AHEAD — NEXT QUARTER
{st.session_state.qr_sections.get('next_quarter', '')}

{'='*60}
Submitted by: {report_author}
{org_name} · {org_name}
Grant: {grant_number} · {funder_name} · {today}

AI-assisted draft — review before sending to funder
"""

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇ Download as text file",
            data=full_text.encode("utf-8"),
            file_name=f"quarterly_report_Q{report_quarter}_{report_year}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        if st.button("🔄 Regenerate all sections", use_container_width=True):
            st.session_state.qr_generated = False
            st.session_state.qr_sections  = {}
            st.rerun()
