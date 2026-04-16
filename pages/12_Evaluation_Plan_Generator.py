import streamlit as st
import anthropic
import os
import json
import re
import datetime
import io

st.set_page_config(page_title="Evaluation Plan Generator", page_icon="📈", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
h3{color:#1F2937!important;font-size:1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;
  font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.section-head{font-weight:600;color:#1A6E6E;font-size:1rem;
  margin:18px 0 6px;padding-bottom:4px;border-bottom:2px solid #E1F5EE}
.outcome-card{background:white;border-radius:10px;padding:14px 16px;
  margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.badge{display:inline-block;padding:2px 9px;border-radius:99px;
  font-size:11px;font-weight:600;margin-left:6px}
.b-short{background:#D1FAE5;color:#065F46}
.b-medium{background:#FEF3C7;color:#92400E}
.b-long{background:#DBEAFE;color:#1E40AF}
.b-validated{background:#D1FAE5;color:#065F46}
.b-custom{background:#E1F5EE;color:#0F6E56}
.b-admin{background:#DBEAFE;color:#1E40AF}
</style>""", unsafe_allow_html=True)


def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")


SYSTEM = """You are an expert nonprofit program evaluator with deep experience in
community behavioral health, youth development, and participatory evaluation.
You write clear, practical, funder-ready evaluation plans grounded in evidence-based
measurement while remaining feasible for community organizations with limited
evaluation capacity. Write in plain language. No markdown headers. No bullet points
inside prose sections — write in connected paragraphs."""


def call_claude(client, prompt, max_tokens=1500):
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def parse_json(raw):
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"```\s*$", "", raw)
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Generation functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_learning_questions(client, program):
    prompt = f"""Generate 5 key evaluation learning questions for this program.

PROGRAM: {program['program_name']}
PROBLEM: {program['problem_statement']}
DESCRIPTION: {program['program_description']}
EQUITY FOCUS: {program['equity_focus']}

These should be substantive questions the evaluation is designed to answer —
about HOW, FOR WHOM, UNDER WHAT CONDITIONS, and with what unintended consequences.
Not just "did it work."

Return a JSON array of 5 question strings. Valid JSON only."""
    return parse_json(call_claude(client, prompt, 400))


def generate_smart_outcomes(client, program):
    outcomes_text = "\n".join(
        f"{i+1}. Domain: {o['domain']}\n"
        f"   Population: {o['population']}\n"
        f"   Timeframe: {o['timeframe']}\n"
        f"   Target: {o['rough_target']}\n"
        f"   Tool: {o['existing_tool']}"
        for i, o in enumerate(program["outcomes"])
    )
    prompt = f"""Generate SMART outcome statements for this program's evaluation plan.

PROGRAM: {program['program_name']}
ORG: {program['org_name']} in {program['org_location']}
TARGET POPULATION: {program['target_population']}
GRANT PERIOD: {program['grant_period']}
PILOT DATA: {program.get('pilot_data','')}

OUTCOME DOMAINS:
{outcomes_text}

For each domain, return a JSON object with:
  "domain": domain name (match exactly)
  "smart_outcome": fully SMART statement starting with "By [timeframe],"
  "indicator": specific measurable indicator
  "baseline": how baseline will be established
  "target": numeric target with rationale
  "stretch_target": more ambitious aim
  "outcome_type": "short-term" | "medium-term" | "long-term"

Return a JSON array of {len(program['outcomes'])} objects. Valid JSON only."""
    return parse_json(call_claude(client, prompt, 3000))


def generate_measurement_plan(client, program, outcomes):
    outcomes_summary = "\n".join(
        f"{i+1}. {o['domain']}: {o['smart_outcome'][:80]}..."
        for i, o in enumerate(outcomes)
    )
    prompt = f"""Create a detailed measurement plan for each outcome.

PROGRAM: {program['program_name']}
DATA SYSTEMS: {program['data_systems']}
STAFF CAPACITY: {program['staff_capacity']}
EQUITY FOCUS: {program['equity_focus']}

OUTCOMES:
{outcomes_summary}

For each outcome (same order), return a JSON object with:
  "domain": domain name (match exactly)
  "primary_tool": name of measurement instrument
  "tool_type": "validated scale" | "custom survey" | "administrative data" | "observation" | "focus group"
  "tool_description": 2-3 sentences on the tool and why it was chosen
  "administration": who administers it, when, and how
  "frequency": how often data is collected
  "secondary_tool": any secondary measure
  "data_collector": which staff role
  "disaggregation": which demographic variables to track
  "analysis_method": how results will be analyzed
  "reporting_frequency": how often and to whom

Return a JSON array of {len(outcomes)} objects. Valid JSON only."""
    return parse_json(call_claude(client, prompt, 3500))


def generate_timeline(client, program):
    prompt = f"""Write a concise evaluation timeline for a two-year grant period.

PROGRAM: {program['program_name']}
GRANT PERIOD: {program['grant_period']}
REPORT DUE: {program.get('report_due','End of grant period')}
EVALUATOR: {program['evaluator']}
BUDGET FOR EVAL: {program.get('budget_for_eval','TBD')}

Write a quarterly timeline covering setup, data collection, mid-grant review,
external evaluation (if applicable), and final reporting.
Format as quarter-by-quarter narrative paragraphs. Approximately 300 words.
No bullet points — write in connected prose."""
    return call_claude(client, prompt, 700)


def generate_equity_section(client, program):
    prompt = f"""Write an equity-focused evaluation section for this program.

PROGRAM: {program['program_name']}
TARGET POPULATION: {program['target_population']}
PROBLEM: {program['problem_statement']}
EQUITY FOCUS: {program['equity_focus']}

Cover in approximately 250 words:
1. Why disaggregated data matters for this specific program
2. Which demographic variables will be tracked and why
3. How equity findings will improve service delivery
4. How community will be involved in interpreting data
5. How findings will be shared back to participants

Write in connected paragraphs. No bullet points."""
    return call_claude(client, prompt, 600)


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("📈 Evaluation Plan Generator")
st.caption(
    "Enter your program details — Claude generates SMART outcomes, measurement tools, "
    "a data collection timeline, and an equity section."
)

api_key = get_api_key()
if not api_key:
    st.markdown(
        '<div class="warn">⚠ API key not set. Add ANTHROPIC_API_KEY in '
        'Streamlit Cloud → Settings → Secrets.</div>',
        unsafe_allow_html=True,
    )

if "eval_results"   not in st.session_state: st.session_state.eval_results   = None
if "eval_generated" not in st.session_state: st.session_state.eval_generated = False
if "eval_program"   not in st.session_state: st.session_state.eval_program   = None

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### What this generates")
    st.markdown("""
- **5 evaluation learning questions**
- **SMART outcome statements** with indicators, targets, and stretch targets
- **Measurement plan** — tool, administrator, frequency, analysis method
- **Equity section** — disaggregation variables and community voice
- **2-year evaluation timeline** — quarter by quarter
- **Reporting plan**

**Cost:** ~$0.08–0.15 per run.
""")
    st.markdown("---")
    if st.button("🔄 Clear and start over", use_container_width=True):
        st.session_state.eval_results   = None
        st.session_state.eval_generated = False
        st.session_state.eval_program   = None
        st.rerun()

# ── Input form ────────────────────────────────────────────────────────────────

with st.expander("## Program & grant details", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        org_name      = st.text_input("Organization",    "Communicare Alliance")
        org_location  = st.text_input("Location",        "Woonsocket, RI")
        program_name  = st.text_input("Program name",    "Youth Mental Health & Resilience Program")
        funder        = st.text_input("Funder",          "Rhode Island Foundation")
    with c2:
        grant_period  = st.text_input("Grant period",    "January 2025 – December 2026")
        report_due    = st.text_input("Final report due", "February 28, 2027")
        evaluator     = st.text_input("Evaluator",
            "Program Development & Grants Manager + URI School of Public Health (Year 2)")
        budget_eval   = st.text_input("Evaluation budget", "$8,000")

with st.expander("## Program description", expanded=True):
    target_pop = st.text_input("Target population",
        "150 youth ages 12–18 annually in Woonsocket, RI, "
        "with priority given to Latino and Black youth from low-income households")
    problem_stmt = st.text_area("Problem statement",
        "Youth in Woonsocket experience rates of adolescent depression 22% above "
        "the national average, with only 1 in 5 youth who need mental health services "
        "currently receiving them. Existing services lack cultural and linguistic "
        "responsiveness for the city's majority Latino and Black population.",
        height=80)
    prog_desc = st.text_area("Program description",
        "A two-year school- and community-based program delivering weekly individual "
        "counseling, bi-weekly resilience skills groups (CBT-A/COPE curriculum), "
        "monthly family psychoeducation workshops, peer mentorship, and trauma-informed "
        "staff training across three Woonsocket public schools and our community clinic.",
        height=80)
    pilot_data = st.text_area("Pilot data / baseline",
        "2022–2024 pilot (n=60): 78% showed clinically meaningful PHQ-A reduction "
        "after 8 weeks; school attendance improved avg 11 days/year among chronic absentees.",
        height=60)

with st.expander("## Outcome domains — add one per intended outcome area", expanded=True):
    st.markdown(
        '<div class="hint">Add each outcome area your program intends to affect. '
        'Claude will generate a full SMART outcome statement and measurement plan for each. '
        '3-6 domains is typical for a community behavioral health program.</div>',
        unsafe_allow_html=True,
    )

    if "outcome_domains" not in st.session_state:
        st.session_state.outcome_domains = [
            {
                "domain":      "Mental health symptom reduction",
                "population":  "Youth enrolled in individual counseling",
                "timeframe":   "At discharge (after 8+ sessions)",
                "rough_target":"75% show meaningful improvement",
                "existing_tool":"PHQ-A (depression), GAD-7 (anxiety)",
            },
            {
                "domain":      "Coping skills and emotional self-regulation",
                "population":  "Youth completing resilience groups",
                "timeframe":   "End of 8-week group cohort",
                "rough_target":"80% demonstrate improved coping",
                "existing_tool":"COPE outcomes scale",
            },
            {
                "domain":      "Caregiver knowledge and confidence",
                "population":  "Caregivers attending family workshops",
                "timeframe":   "Immediately post-workshop",
                "rough_target":"70% report increased confidence",
                "existing_tool":"Post-workshop satisfaction survey (custom)",
            },
            {
                "domain":      "School staff capacity",
                "population":  "School staff completing trauma-informed training",
                "timeframe":   "3 months post-training",
                "rough_target":"80% report greater confidence",
                "existing_tool":"Pre/post knowledge assessment (custom)",
            },
            {
                "domain":      "Service reach and equity",
                "population":  "All enrolled youth",
                "timeframe":   "Quarterly and annually",
                "rough_target":"85% participants of color; 80% attendance rate",
                "existing_tool":"EHR / program tracking data",
            },
        ]

    to_remove = []
    for i, od in enumerate(st.session_state.outcome_domains):
        with st.expander(f"Outcome {i+1}: {od.get('domain','New outcome')}", expanded=i==0):
            c1, c2 = st.columns(2)
            with c1:
                od["domain"]      = st.text_input("Outcome domain",   od["domain"],      key=f"dom_{i}")
                od["population"]  = st.text_input("Population",        od["population"],  key=f"pop_{i}")
                od["timeframe"]   = st.text_input("Timeframe",         od["timeframe"],   key=f"tf_{i}")
            with c2:
                od["rough_target"]  = st.text_input("Rough target",     od["rough_target"],   key=f"tgt_{i}")
                od["existing_tool"] = st.text_input("Existing tool(s)", od["existing_tool"],  key=f"tool_{i}")
            if st.button(f"Remove outcome {i+1}", key=f"rem_{i}"):
                to_remove.append(i)

    for idx in reversed(to_remove):
        st.session_state.outcome_domains.pop(idx)
        st.rerun()

    if st.button("+ Add outcome domain"):
        st.session_state.outcome_domains.append({
            "domain":"", "population":"", "timeframe":"",
            "rough_target":"", "existing_tool":"",
        })
        st.rerun()

with st.expander("## Evaluation infrastructure", expanded=False):
    data_systems   = st.text_area("Data systems",
        "Electronic Health Record (EHR), program tracking spreadsheet, "
        "school attendance records from Woonsocket Education Department",
        height=60)
    staff_capacity = st.text_area("Evaluation staff capacity",
        "Program Coordinator manages data entry; LCSW staff administer validated tools; "
        "Year 2 external evaluation by URI School of Public Health",
        height=60)
    equity_focus   = st.text_area("Equity focus",
        "Disaggregate all outcome data by race/ethnicity, age, gender, school, "
        "and income level to identify disparities and drive program improvements",
        height=60)

# ── Generate ──────────────────────────────────────────────────────────────────

st.markdown("---")
g1, g2 = st.columns([2, 3])
with g1:
    generate_btn = st.button(
        "✨ Generate evaluation plan",
        disabled=not api_key,
        use_container_width=True,
    )
with g2:
    st.markdown(
        '<div class="hint" style="margin:0">Takes about 60–90 seconds · '
        f'generates {len(st.session_state.outcome_domains)} outcome statements + '
        'measurement plan + timeline + equity section</div>',
        unsafe_allow_html=True,
    )

if generate_btn:
    program = {
        "org_name":          org_name,
        "org_location":      org_location,
        "program_name":      program_name,
        "funder":            funder,
        "grant_period":      grant_period,
        "report_due":        report_due,
        "evaluator":         evaluator,
        "budget_for_eval":   budget_eval,
        "target_population": target_pop,
        "problem_statement": problem_stmt,
        "program_description": prog_desc,
        "pilot_data":        pilot_data,
        "outcomes":          st.session_state.outcome_domains,
        "data_systems":      data_systems,
        "staff_capacity":    staff_capacity,
        "equity_focus":      equity_focus,
    }

    client   = anthropic.Anthropic(api_key=api_key)
    progress = st.progress(0, text="Generating learning questions...")

    try:
        questions = generate_learning_questions(client, program)
        progress.progress(0.2, text="Generating SMART outcomes...")

        outcomes = generate_smart_outcomes(client, program)
        progress.progress(0.5, text="Building measurement plan...")

        measurement = generate_measurement_plan(client, program, outcomes)
        progress.progress(0.75, text="Writing equity section...")

        equity = generate_equity_section(client, program)
        progress.progress(0.9, text="Building evaluation timeline...")

        timeline = generate_timeline(client, program)
        progress.empty()

        st.session_state.eval_results = {
            "questions":   questions,
            "outcomes":    outcomes,
            "measurement": measurement,
            "equity":      equity,
            "timeline":    timeline,
        }
        st.session_state.eval_program   = program
        st.session_state.eval_generated = True
        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"Generation failed: {e}. Try again — sometimes Claude needs a second attempt.")

# ── Display results ───────────────────────────────────────────────────────────

if st.session_state.eval_generated and st.session_state.eval_results:
    r   = st.session_state.eval_results
    p   = st.session_state.eval_program
    today = datetime.date.today().strftime("%B %d, %Y")

    st.markdown("---")
    st.markdown(f"## Evaluation Plan — {p['program_name']}")
    st.caption(
        f"{p['org_name']} · {p['funder']} · {p['grant_period']} · Generated {today}"
    )

    # Metadata strip
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Outcome domains",    len(r["outcomes"]))
    m2.metric("Measurement tools",  len(r["measurement"]))
    m3.metric("Learning questions", len(r["questions"]))
    m4.metric("Eval budget",        p["budget_for_eval"])

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "❓ Learning Questions",
        "🎯 SMART Outcomes",
        "📏 Measurement Plan",
        "⚖️ Equity",
        "📅 Timeline & Reporting",
    ])

    # ── Tab 1: Learning questions ────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="section-head">Key Evaluation Questions</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="hint">These are the substantive questions your evaluation '
            'is designed to answer — not just "did it work" but how, for whom, '
            'and under what conditions.</div>',
            unsafe_allow_html=True,
        )
        for i, q in enumerate(r["questions"], 1):
            st.markdown(f"**{i}.** {q}")
            st.markdown("")

    # ── Tab 2: SMART outcomes ────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-head">SMART Outcome Statements</div>',
                    unsafe_allow_html=True)

        TYPE_BADGE = {
            "short-term":  ("b-short",  "Short-term"),
            "medium-term": ("b-medium", "Medium-term"),
            "long-term":   ("b-long",   "Long-term"),
        }

        for o in r["outcomes"]:
            ot    = o.get("outcome_type", "short-term")
            bcls, blbl = TYPE_BADGE.get(ot, ("b-short","Short-term"))

            with st.container():
                st.markdown(
                    f'<div class="outcome-card">'
                    f'<strong style="color:#1A6E6E">{o.get("domain","")}</strong>'
                    f'<span class="badge {bcls}">{blbl}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**SMART statement:** {o.get('smart_outcome','')}")
                    st.markdown(f"**Indicator:** *{o.get('indicator','')}*")
                    st.caption(f"Baseline: {o.get('baseline','')}")
                with c2:
                    st.markdown(f"**Target:** {o.get('target','')}")
                    st.caption(f"Stretch: {o.get('stretch_target','')}")

                st.markdown("---")

    # ── Tab 3: Measurement plan ──────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-head">Measurement & Data Collection Plan</div>',
                    unsafe_allow_html=True)

        TOOL_BADGE = {
            "validated scale":     ("b-validated", "Validated scale"),
            "custom survey":       ("b-custom",    "Custom survey"),
            "administrative data": ("b-admin",     "Admin data"),
            "observation":         ("b-custom",    "Observation"),
            "focus group":         ("b-admin",     "Focus group"),
        }

        for m in r["measurement"]:
            tt    = m.get("tool_type","validated scale")
            bcls, blbl = TOOL_BADGE.get(tt, ("b-custom","Custom"))

            with st.expander(
                f"**{m.get('domain','')}** — {m.get('primary_tool','')}",
                expanded=False,
            ):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Primary tool:** {m.get('primary_tool','')}")
                    st.markdown(
                        f'<span class="badge {bcls}">{blbl}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Secondary:** {m.get('secondary_tool','—')}")
                with c2:
                    st.markdown(f"**Administration:** {m.get('administration','')}")
                    st.markdown(f"**Frequency:** {m.get('frequency','')}")
                    st.markdown(f"**Data collector:** {m.get('data_collector','')}")
                with c3:
                    st.markdown(f"**Analysis:** {m.get('analysis_method','')}")
                    st.markdown(f"**Reporting:** {m.get('reporting_frequency','')}")
                    st.markdown(f"**Disaggregate by:** {m.get('disaggregation','')}")

                st.caption(m.get("tool_description",""))

        # Summary table
        st.markdown('<div class="section-head">Summary Table</div>',
                    unsafe_allow_html=True)
        import pandas as pd
        df_m = pd.DataFrame([{
            "Outcome Domain":   m.get("domain",""),
            "Primary Tool":     m.get("primary_tool",""),
            "Tool Type":        m.get("tool_type",""),
            "Frequency":        m.get("frequency",""),
            "Data Collector":   m.get("data_collector",""),
            "Analysis":         m.get("analysis_method",""),
        } for m in r["measurement"]])
        st.dataframe(df_m, hide_index=True, use_container_width=True)

    # ── Tab 4: Equity ────────────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-head">Equity in Evaluation</div>',
                    unsafe_allow_html=True)
        for para in r["equity"].split("\n\n"):
            if para.strip():
                st.markdown(para.strip())
                st.markdown("")

    # ── Tab 5: Timeline & reporting ─────────────────────────────────────────
    with tab5:
        st.markdown('<div class="section-head">Evaluation Timeline</div>',
                    unsafe_allow_html=True)
        for para in r["timeline"].split("\n\n"):
            if para.strip():
                st.markdown(para.strip())
                st.markdown("")

        st.markdown('<div class="section-head">Reporting & Dissemination</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f"**Interim report (Year 1):** Due to {p['funder']} — service delivery data, "
            f"early outcome indicators, and equity findings."
        )
        st.markdown(
            f"**Final report (Year 2):** Due {p['report_due']} — full outcomes analysis, "
            f"external evaluation findings, lessons learned, and recommendations."
        )
        st.markdown(
            "**Community dissemination:** Plain-language summary (English & Spanish) "
            "shared with participants, families, and community partners."
        )
        st.markdown(
            "**Field dissemination:** Implementation model and outcome data shared at "
            "RIPHI, regional behavioral health conference, and SAMHSA's EBPRC."
        )

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")

    full_text = f"""{p['program_name']}
EVALUATION PLAN
{p['org_name']} · {p['funder']} · {p['grant_period']}
Evaluator: {p['evaluator']} · Eval budget: {p['budget_for_eval']}
Generated: {today}

{'='*60}

KEY EVALUATION QUESTIONS
{chr(10).join(f"{i+1}. {q}" for i,q in enumerate(r['questions']))}

{'='*60}

SMART OUTCOME STATEMENTS
"""
    for o in r["outcomes"]:
        full_text += f"""
{o.get('domain','').upper()} ({o.get('outcome_type','').upper()})
SMART Statement: {o.get('smart_outcome','')}
Indicator: {o.get('indicator','')}
Target: {o.get('target','')}
Stretch: {o.get('stretch_target','')}
Baseline: {o.get('baseline','')}
"""

    full_text += f"\n{'='*60}\n\nMEASUREMENT PLAN\n"
    for m in r["measurement"]:
        full_text += f"""
{m.get('domain','').upper()}
Primary tool: {m.get('primary_tool','')} ({m.get('tool_type','')})
Description: {m.get('tool_description','')}
Administration: {m.get('administration','')}
Frequency: {m.get('frequency','')}
Data collector: {m.get('data_collector','')}
Analysis: {m.get('analysis_method','')}
Reporting: {m.get('reporting_frequency','')}
Disaggregate by: {m.get('disaggregation','')}
"""

    full_text += f"\n{'='*60}\n\nEQUITY IN EVALUATION\n{r['equity']}"
    full_text += f"\n\n{'='*60}\n\nEVALUATION TIMELINE\n{r['timeline']}"
    full_text += f"\n\n{'='*60}\nAI-assisted draft — review before submitting to funder\n"

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇ Download evaluation plan (.txt)",
            data=full_text.encode("utf-8"),
            file_name=(
                f"evaluation_plan_"
                f"{p['program_name'].lower().replace(' ','_')[:25]}"
                f"_{today}.txt"
            ),
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        if st.button("🔄 Regenerate with new settings", use_container_width=True):
            st.session_state.eval_generated = False
            st.session_state.eval_results   = None
            st.rerun()
