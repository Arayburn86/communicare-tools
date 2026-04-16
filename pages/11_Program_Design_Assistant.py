import streamlit as st
import anthropic
import os
import json
import re
import datetime
import io

st.set_page_config(page_title="Program Design Assistant", page_icon="🧩", layout="wide")

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
.chat-user{background:#E1F5EE;border-radius:0 12px 12px 12px;
  padding:12px 16px;margin:8px 0;font-size:.9rem;color:#085041;
  border-left:3px solid #1A6E6E}
.chat-claude{background:#F9FAFB;border-radius:12px 12px 12px 0;
  padding:12px 16px;margin:8px 0;font-size:.9rem;color:#1F2937;
  border-left:3px solid #9CA3AF;line-height:1.7}
.section-head{font-weight:600;color:#1A6E6E;font-size:1rem;
  margin:16px 0 6px;padding-bottom:4px;border-bottom:2px solid #E1F5EE}
.kpi-box{background:#E1F5EE;border-radius:8px;padding:10px;
  text-align:center;margin-bottom:8px}
.kpi-val{font-size:1.4rem;font-weight:700;color:#1A6E6E}
.kpi-lbl{font-size:.7rem;color:#6B7280}
</style>""", unsafe_allow_html=True)


def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")


ORG_NAME     = "Communicare Alliance"
ORG_LOCATION = "Woonsocket, RI"
ORG_MISSION  = (
    "To strengthen the health and well-being of individuals and families "
    "in Woonsocket and the surrounding Blackstone Valley through "
    "community-centered, culturally responsive human services."
)
FRINGE_RATE   = 0.28
INDIRECT_RATE = 0.08

SYSTEM = f"""You are an expert nonprofit program designer and macro social work consultant
with 20 years of experience designing community health and human services programs.
You are helping {ORG_NAME} in {ORG_LOCATION} design a new program concept.

Org mission: {ORG_MISSION}
Fringe rate: {FRINGE_RATE*100:.0f}%
Indirect rate: {INDIRECT_RATE*100:.0f}%

Your role:
- Ask thoughtful focused questions one section at a time
- Build on what the user tells you — do not repeat questions already answered
- Be specific and concrete, not generic
- When you make suggestions explain the reasoning
- Ground recommendations in evidence-based practice and funding realities
- Be honest about what is feasible vs aspirational
- Keep responses conversational but substantive
- Format responses cleanly — no markdown headers, just clear paragraphs with line breaks"""

CONVERSATION_STAGES = [
    {
        "id":    "concept",
        "label": "1. The Concept",
        "prompt": (
            "The user is describing their initial program concept. "
            "Respond warmly, reflect back what you heard, identify the strongest elements, "
            "and ask 2 focused follow-up questions about the target population and the "
            "specific problem they are trying to solve. Be conversational not clinical."
        ),
    },
    {
        "id":    "problem",
        "label": "2. Problem & Root Causes",
        "prompt": (
            "Build on what they said. Reflect the population and problem clearly. "
            "Ask about root causes — what is driving this need? "
            "And ask: has anything been tried before, and what worked or did not?"
        ),
    },
    {
        "id":    "theory",
        "label": "3. Theory of Change",
        "prompt": (
            "Transition to theory of change. Based on everything discussed, propose a "
            "draft theory in plain language: IF we do [activities] THEN [short-term changes] "
            "LEADING TO [long-term outcomes]. Make it specific. "
            "Then ask if it resonates and what they would change. "
            "Also name 2-3 relevant evidence-based models they might draw on."
        ),
    },
    {
        "id":    "activities",
        "label": "4. Activities & Service Model",
        "prompt": (
            "Propose 3-5 concrete program activities with frequency, format, and capacity. "
            "Be specific — not just 'counseling' but 'weekly 50-minute individual therapy, "
            "caseload of 25 per clinician'. "
            "Ask about delivery setting and why, and realistic Year 1 scale."
        ),
    },
    {
        "id":    "staffing",
        "label": "5. Staffing Model",
        "prompt": (
            "Propose a realistic staffing model with positions, FTE, qualifications, "
            "and Rhode Island salary estimates. Include direct service and coordination roles. "
            "Ask what positions they might already have. "
            "Also ask about supervision structure and peer/lived experience roles."
        ),
    },
    {
        "id":    "budget",
        "label": "6. Budget Estimate",
        "prompt": (
            f"Based on staffing and activities discussed, give a rough Year 1 and Year 2 budget. "
            f"Use {FRINGE_RATE*100:.0f}% fringe and {INDIRECT_RATE*100:.0f}% indirect on MTDC. "
            "List personnel by position then major non-personnel categories. "
            "Give ranges not false precision. Ask about existing funding sources."
        ),
    },
    {
        "id":    "funders",
        "label": "7. Funders & Next Steps",
        "prompt": (
            "Recommend 5-7 specific funders — local RI, national, and federal — "
            "with fit reasoning and typical award ranges. "
            "Then outline a 6-month development timeline: "
            "what needs to happen before the first application goes out? "
            "Summarize the 3 most important next actions."
        ),
    },
]


def ask_claude(client, message, stage_prompt):
    conversation = st.session_state.pd_conversation.copy()
    conversation.append({"role": "user", "content": message})

    system = SYSTEM + f"\n\nContext for this response: {stage_prompt}"
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=system,
        messages=conversation,
    )
    response = msg.content[0].text.strip()
    st.session_state.pd_conversation.append({"role": "user",    "content": message})
    st.session_state.pd_conversation.append({"role": "assistant","content": response})
    return response


def extract_design(client):
    prompt = f"""Based on our entire conversation, extract the program design into structured JSON.
Fill in everything discussed; use reasonable professional assumptions for anything not stated.
Use Rhode Island salary benchmarks.

Return ONLY valid JSON with these fields:
{{
  "program_name": "proposed program name",
  "program_tagline": "one sentence description",
  "target_population": "who is served",
  "geographic_focus": "where",
  "problem_statement": "2-3 sentences on the community need",
  "root_causes": ["cause 1", "cause 2"],
  "theory_of_change": "If we do X then Y will happen leading to Z outcome",
  "activities": [
    {{"name": "activity", "description": "what it is", "frequency": "how often", "capacity": "how many"}}
  ],
  "short_term_outcomes": ["outcome 1", "outcome 2"],
  "long_term_outcomes": ["outcome 1", "outcome 2"],
  "evidence_base": "what research supports this approach",
  "equity_approach": "how the program addresses equity",
  "staff_roles": [
    {{"title": "position", "fte": 1.0, "salary_estimate": 55000, "responsibilities": "key duties"}}
  ],
  "key_partnerships": ["partner 1", "partner 2"],
  "potential_funders": [
    {{"name": "funder", "fit_reason": "why they fit", "typical_award": "$X-$Y"}}
  ],
  "risks": ["risk 1", "risk 2"],
  "estimated_participants_year1": 50,
  "estimated_participants_year2": 100,
  "non_personnel_costs": [
    {{"category": "category", "item": "line item", "annual_cost": 5000, "justification": "why"}}
  ],
  "next_steps": ["step 1", "step 2", "step 3"]
}}"""

    conversation = st.session_state.pd_conversation.copy()
    conversation.append({"role": "user", "content": prompt})
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM,
        messages=conversation,
    )
    raw = re.sub(r"^```json\s*", "", msg.content[0].text.strip())
    raw = re.sub(r"```\s*$", "", raw)
    return json.loads(raw)


def calc_budget(design):
    staff = design.get("staff_roles", [])
    np    = design.get("non_personnel_costs", [])
    sal_y1    = sum(s.get("salary_estimate",0) * s.get("fte",1.0) for s in staff)
    sal_y2    = sal_y1 * 1.03
    fringe_y1 = sal_y1 * FRINGE_RATE
    fringe_y2 = sal_y2 * FRINGE_RATE
    np_y1     = sum(c.get("annual_cost",0) for c in np)
    np_y2     = np_y1
    tdc_y1    = sal_y1 + fringe_y1 + np_y1
    tdc_y2    = sal_y2 + fringe_y2 + np_y2
    ind_y1    = tdc_y1 * INDIRECT_RATE
    ind_y2    = tdc_y2 * INDIRECT_RATE
    return {
        "sal_y1": sal_y1, "sal_y2": sal_y2,
        "fringe_y1": fringe_y1, "fringe_y2": fringe_y2,
        "np_y1": np_y1, "np_y2": np_y2,
        "tdc_y1": tdc_y1, "tdc_y2": tdc_y2,
        "ind_y1": ind_y1, "ind_y2": ind_y2,
        "total_y1": tdc_y1 + ind_y1,
        "total_y2": tdc_y2 + ind_y2,
        "grand_total": (tdc_y1 + ind_y1) + (tdc_y2 + ind_y2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

if "pd_conversation"  not in st.session_state: st.session_state.pd_conversation  = []
if "pd_stage"         not in st.session_state: st.session_state.pd_stage          = 0
if "pd_started"       not in st.session_state: st.session_state.pd_started        = False
if "pd_design"        not in st.session_state: st.session_state.pd_design         = None
if "pd_complete"      not in st.session_state: st.session_state.pd_complete       = False
if "pd_pending_input" not in st.session_state: st.session_state.pd_pending_input  = None

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🧩 Program Design Assistant")
st.caption(
    "A conversational tool that walks you through designing a new program — "
    "theory of change, activities, staffing, budget, and funders."
)

api_key = get_api_key()
if not api_key:
    st.markdown(
        '<div class="warn">⚠ API key not set. Add ANTHROPIC_API_KEY in '
        'Streamlit Cloud → Settings → Secrets.</div>',
        unsafe_allow_html=True,
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### How it works")
    st.markdown("""
This is a **guided conversation** — Claude asks you questions and builds
your program design from your answers.

Work through 7 sections:
1. The concept
2. Problem & root causes
3. Theory of change
4. Activities & service model
5. Staffing model
6. Budget estimate
7. Funders & next steps

At the end you get a **complete program design document** with a 2-year budget estimate.

**Cost:** ~$0.20–0.40 for a full session.
""")
    st.markdown("---")

    # Progress
    if st.session_state.pd_started:
        stage = st.session_state.pd_stage
        total = len(CONVERSATION_STAGES)
        st.markdown("### Progress")
        st.progress(min(stage / total, 1.0))
        for i, s in enumerate(CONVERSATION_STAGES):
            icon = "✅" if i < stage else ("👉" if i == stage else "⭕")
            st.caption(f"{icon} {s['label']}")

    st.markdown("---")
    if st.button("🔄 Start over", use_container_width=True):
        st.session_state.pd_conversation  = []
        st.session_state.pd_stage         = 0
        st.session_state.pd_started       = False
        st.session_state.pd_design        = None
        st.session_state.pd_complete      = False
        st.session_state.pd_pending_input = None
        st.rerun()

# ── Not started yet ───────────────────────────────────────────────────────────

if not st.session_state.pd_started:
    st.markdown("---")
    st.markdown(
        '<div class="hint">Tell Claude about the program idea you have in mind. '
        'Even a rough concept is fine — a sentence or two is enough to get started. '
        'Claude will ask follow-up questions to develop it fully.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### What program idea do you want to develop?")

    initial_input = st.text_area(
        "Your idea",
        placeholder=(
            "e.g. I want to create a peer support program for parents of children "
            "with mental health challenges in Woonsocket..."
        ),
        height=100,
        label_visibility="collapsed",
    )

    if st.button("Start designing →", disabled=not (api_key and initial_input.strip())):
        client = anthropic.Anthropic(api_key=api_key)
        with st.spinner("Claude is thinking..."):
            response = ask_claude(
                client,
                initial_input,
                CONVERSATION_STAGES[0]["prompt"],
            )
        st.session_state.pd_started = True
        st.session_state.pd_stage   = 1
        st.rerun()

# ── Active conversation ───────────────────────────────────────────────────────

elif not st.session_state.pd_complete:

    # Display conversation history
    for msg in st.session_state.pd_conversation:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">🧑 <strong>You:</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # Format paragraphs
            formatted = "".join(
                f"<p style='margin:0 0 8px'>{para.strip()}</p>"
                for para in msg["content"].split("\n\n")
                if para.strip()
            )
            st.markdown(
                f'<div class="chat-claude">🤖 <strong>Claude:</strong><br>{formatted}</div>',
                unsafe_allow_html=True,
            )

    stage_idx = st.session_state.pd_stage
    is_last   = stage_idx >= len(CONVERSATION_STAGES)

    if not is_last:
        current_stage = CONVERSATION_STAGES[stage_idx]
        st.markdown("---")

        user_response = st.text_area(
            "Your response",
            key=f"input_stage_{stage_idx}",
            height=100,
            placeholder="Type your response here...",
            label_visibility="collapsed",
        )

        c1, c2, c3 = st.columns([2, 2, 1])

        with c1:
            next_label = (
                "Continue →" if stage_idx < len(CONVERSATION_STAGES) - 1
                else "Generate design document →"
            )
            continue_btn = st.button(
                next_label,
                disabled=not (api_key and user_response.strip()),
                use_container_width=True,
            )

        with c2:
            skip_btn = st.button(
                "Skip this section →",
                use_container_width=True,
            )

        with c3:
            if st.button("Finish early →", use_container_width=True):
                st.session_state.pd_stage = len(CONVERSATION_STAGES)
                st.rerun()

        if continue_btn and user_response.strip():
            client = anthropic.Anthropic(api_key=api_key)
            next_stage_idx = stage_idx + 1
            is_moving_to_last = next_stage_idx >= len(CONVERSATION_STAGES)

            with st.spinner("Claude is responding..."):
                if is_moving_to_last:
                    # Last user message — just record it, move to extraction
                    st.session_state.pd_conversation.append(
                        {"role": "user", "content": user_response}
                    )
                    st.session_state.pd_stage = next_stage_idx
                else:
                    next_stage = CONVERSATION_STAGES[next_stage_idx]
                    ask_claude(client, user_response, next_stage["prompt"])
                    st.session_state.pd_stage = next_stage_idx

            st.rerun()

        if skip_btn:
            client = anthropic.Anthropic(api_key=api_key)
            next_stage_idx = stage_idx + 1
            if next_stage_idx < len(CONVERSATION_STAGES):
                next_stage = CONVERSATION_STAGES[next_stage_idx]
                with st.spinner("Moving to next section..."):
                    ask_claude(
                        client,
                        "(The user chose to skip this section — move to the next topic.)",
                        next_stage["prompt"],
                    )
                st.session_state.pd_stage = next_stage_idx
            else:
                st.session_state.pd_stage = len(CONVERSATION_STAGES)
            st.rerun()

    else:
        # All stages done — generate document
        st.markdown("---")
        st.markdown(
            '<div class="hint">✅ Conversation complete! Click below to generate '
            'your program design document.</div>',
            unsafe_allow_html=True,
        )

        if st.button("📄 Generate program design document", use_container_width=False):
            client = anthropic.Anthropic(api_key=api_key)
            with st.spinner("Extracting your program design..."):
                try:
                    design = extract_design(client)
                    st.session_state.pd_design   = design
                    st.session_state.pd_complete = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not extract design: {e}. Try clicking again.")

# ── Complete — show design document ──────────────────────────────────────────

elif st.session_state.pd_complete and st.session_state.pd_design:
    d     = st.session_state.pd_design
    b     = calc_budget(d)
    today = datetime.date.today().strftime("%B %d, %Y")

    st.markdown("---")
    st.markdown(f"## {d.get('program_name','New Program')}")
    st.caption(f"{d.get('program_tagline','')}  ·  {ORG_NAME}  ·  {today}")

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi-box"><div class="kpi-val">{d.get("estimated_participants_year1","?")}</div><div class="kpi-lbl">Year 1 participants</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi-box"><div class="kpi-val">{d.get("estimated_participants_year2","?")}</div><div class="kpi-lbl">Year 2 participants</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-box"><div class="kpi-val">${b["total_y1"]:,.0f}</div><div class="kpi-lbl">Est. Year 1 ask</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-box"><div class="kpi-val">${b["grand_total"]:,.0f}</div><div class="kpi-lbl">Est. 2-year total</div></div>', unsafe_allow_html=True)

    # Sections
    def show_section(title, content):
        st.markdown(f'<div class="section-head">{title}</div>', unsafe_allow_html=True)
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    cols = st.columns([1,3])
                    cols[0].markdown(f"**{item.get('name') or item.get('title') or item.get('funder','—')}**")
                    cols[1].caption(
                        item.get("description") or
                        item.get("responsibilities") or
                        item.get("fit_reason","")
                    )
                else:
                    st.markdown(f"• {item}")
        else:
            st.markdown(content)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview", "Activities & Staffing", "Budget", "Funders", "Next Steps"
    ])

    with tab1:
        show_section("Problem Statement",   d.get("problem_statement",""))
        show_section("Root Causes",         d.get("root_causes",[]))
        show_section("Theory of Change",    d.get("theory_of_change",""))
        show_section("Equity Approach",     d.get("equity_approach",""))
        show_section("Evidence Base",       d.get("evidence_base",""))

    with tab2:
        show_section("Program Activities",  d.get("activities",[]))
        show_section("Short-Term Outcomes", d.get("short_term_outcomes",[]))
        show_section("Long-Term Outcomes",  d.get("long_term_outcomes",[]))
        show_section("Staffing Model",      d.get("staff_roles",[]))
        show_section("Key Partnerships",    d.get("key_partnerships",[]))

    with tab3:
        st.markdown('<div class="section-head">2-Year Budget Estimate</div>', unsafe_allow_html=True)
        budget_rows = [
            ("Personnel salaries",     b["sal_y1"],    b["sal_y2"]),
            (f"Fringe ({FRINGE_RATE*100:.0f}%)", b["fringe_y1"], b["fringe_y2"]),
            ("Non-personnel costs",    b["np_y1"],     b["np_y2"]),
            ("Total direct costs",     b["tdc_y1"],    b["tdc_y2"]),
            (f"Indirect ({INDIRECT_RATE*100:.0f}%)",   b["ind_y1"],    b["ind_y2"]),
        ]
        import pandas as pd
        df_b = pd.DataFrame(budget_rows, columns=["Category","Year 1","Year 2"])
        df_b["2-Yr Total"] = df_b["Year 1"] + df_b["Year 2"]
        for col in ["Year 1","Year 2","2-Yr Total"]:
            df_b[col] = df_b[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_b, hide_index=True, use_container_width=True)

        st.markdown(
            f"**Estimated 2-year grant request: ${b['grand_total']:,.0f}**  "
            f"(Year 1: ${b['total_y1']:,.0f} · Year 2: ${b['total_y2']:,.0f})"
        )
        st.caption("Estimates only. Year 2 includes 3% COLA. Refine with actual salary data before submitting.")

        if d.get("non_personnel_costs"):
            st.markdown('<div class="section-head">Non-Personnel Detail</div>', unsafe_allow_html=True)
            for item in d["non_personnel_costs"]:
                st.markdown(f"**{item.get('category','')}: {item.get('item','')}** — ${item.get('annual_cost',0):,}/year")
                st.caption(item.get("justification",""))

    with tab4:
        show_section("Potential Funders",   d.get("potential_funders",[]))
        show_section("Key Risks to Address", d.get("risks",[]))

    with tab5:
        show_section("Recommended Next Steps", d.get("next_steps",[]))

    # Download
    st.markdown("---")
    prog_name = d.get("program_name","new_program")
    full_text = f"""{prog_name}
PROGRAM DESIGN DOCUMENT
{ORG_NAME} · {ORG_LOCATION} · {today}

{d.get('program_tagline','')}

TARGET POPULATION: {d.get('target_population','')}
GEOGRAPHIC FOCUS: {d.get('geographic_focus','')}
ESTIMATED YEAR 1 REQUEST: ${b['total_y1']:,.0f}
ESTIMATED 2-YEAR TOTAL: ${b['grand_total']:,.0f}

{'='*60}

PROBLEM STATEMENT
{d.get('problem_statement','')}

THEORY OF CHANGE
{d.get('theory_of_change','')}

PROGRAM ACTIVITIES
{chr(10).join('- ' + (a.get('name','') + ': ' + a.get('description','')) for a in d.get('activities',[]))}

SHORT-TERM OUTCOMES
{chr(10).join('- ' + o for o in d.get('short_term_outcomes',[]))}

LONG-TERM OUTCOMES
{chr(10).join('- ' + o for o in d.get('long_term_outcomes',[]))}

EQUITY APPROACH
{d.get('equity_approach','')}

EVIDENCE BASE
{d.get('evidence_base','')}

STAFFING MODEL
{chr(10).join(f"- {s.get('title','')} ({s.get('fte','')} FTE): ${s.get('salary_estimate',0):,}/yr — {s.get('responsibilities','')}" for s in d.get('staff_roles',[]))}

BUDGET ESTIMATE
Personnel salaries: Y1 ${b['sal_y1']:,.0f} | Y2 ${b['sal_y2']:,.0f}
Fringe ({FRINGE_RATE*100:.0f}%): Y1 ${b['fringe_y1']:,.0f} | Y2 ${b['fringe_y2']:,.0f}
Non-personnel: Y1 ${b['np_y1']:,.0f} | Y2 ${b['np_y2']:,.0f}
Total direct costs: Y1 ${b['tdc_y1']:,.0f} | Y2 ${b['tdc_y2']:,.0f}
Indirect ({INDIRECT_RATE*100:.0f}%): Y1 ${b['ind_y1']:,.0f} | Y2 ${b['ind_y2']:,.0f}
ESTIMATED GRANT REQUEST: Y1 ${b['total_y1']:,.0f} | Y2 ${b['total_y2']:,.0f} | TOTAL ${b['grand_total']:,.0f}

POTENTIAL FUNDERS
{chr(10).join(f"- {f.get('name','')}: {f.get('fit_reason','')} ({f.get('typical_award','')})" for f in d.get('potential_funders',[]))}

RECOMMENDED NEXT STEPS
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(d.get('next_steps',[])))}

{'='*60}
AI-assisted program design — review and refine before sharing
{ORG_NAME} · {today}
"""

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇ Download program design (.txt)",
            data=full_text.encode("utf-8"),
            file_name=f"{prog_name.lower().replace(' ','_')[:30]}_design_{today}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        if st.button("💬 Continue the conversation", use_container_width=True):
            st.session_state.pd_complete = False
            st.session_state.pd_stage    = len(CONVERSATION_STAGES)
            st.rerun()
