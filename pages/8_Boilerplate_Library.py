import streamlit as st
import anthropic
import sqlite3
import os
import datetime
import io
import tempfile

st.set_page_config(page_title="Boilerplate Library", page_icon="📚", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;
  font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.block-card{background:white;border-radius:10px;padding:16px 18px;
  margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);
  border-left:4px solid #1A6E6E}
.block-card.amber{border-left-color:#BA7517}
.block-card.blue{border-left-color:#185FA5}
.block-card.purple{border-left-color:#534AB7}
.block-card.coral{border-left-color:#993C1D}
.block-card.green{border-left-color:#065F46}
.tag{display:inline-block;background:#E1F5EE;color:#085041;
  padding:2px 8px;border-radius:99px;font-size:11px;margin:2px}
.use-count{font-size:11px;color:#9CA3AF}
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# API key
# ─────────────────────────────────────────────────────────────────────────────

def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────────────
# Database — stored in session state as an in-memory SQLite
# (Streamlit Cloud is stateless between sessions so we use session_state
#  to persist the DB connection and data within a session)
# ─────────────────────────────────────────────────────────────────────────────

STARTER_BLOCKS = [
    {
        "category": "Org Identity",
        "title": "Mission statement — standard",
        "tags": "mission, boilerplate, identity",
        "content": (
            "Communicare Alliance's mission is to strengthen the health and well-being "
            "of individuals and families in Woonsocket and the surrounding Blackstone "
            "Valley through community-centered, culturally responsive human services."
        ),
        "notes": "Use in every grant. Can be shortened for tight page limits.",
    },
    {
        "category": "Org Identity",
        "title": "Org history and overview — full",
        "tags": "history, overview, boilerplate, capacity",
        "content": (
            "Founded in 1994, Communicare Alliance has served the Woonsocket community "
            "for over 30 years as one of Rhode Island's leading community-based human "
            "services organizations. We deliver behavioral health, family support, and "
            "community health programs to more than 2,500 individuals annually across "
            "Woonsocket and the greater Blackstone Valley. Our staff of 42 includes "
            "licensed clinical social workers, community health workers, case managers, "
            "and peer specialists, with over 60% identifying as people of color and "
            "40% speaking Spanish as a primary language. We have maintained consecutive "
            "clean financial audits since 2005 and hold active contracts with DCYF, "
            "BHDDH, and Medicaid managed care organizations. Our annual operating budget "
            "is approximately $4.2 million, of which 34% is philanthropic."
        ),
        "notes": "Update annual numbers each January. Use for capacity sections.",
    },
    {
        "category": "Org Identity",
        "title": "Org history — short (50 words)",
        "tags": "history, overview, boilerplate, short",
        "content": (
            "Founded in 1994, Communicare Alliance has served Woonsocket for over 30 years, "
            "delivering behavioral health, family support, and community health programs to "
            "more than 2,500 individuals annually. Our 42-person staff is majority people "
            "of color and 40% bilingual Spanish/English — reflecting the communities we serve."
        ),
        "notes": "Use when page limits are tight.",
    },
    {
        "category": "Org Identity",
        "title": "Financial management and audit statement",
        "tags": "financial, audit, capacity, compliance",
        "content": (
            "Communicare Alliance maintains strong financial management systems and has "
            "received clean independent audits for 19 consecutive years. We operate on an "
            "annual budget of approximately $4.2 million managed through a fully automated "
            "accounting system with real-time budget tracking and monthly financial reporting "
            "to our Board Finance Committee. We have successfully managed federal, state, "
            "and foundation grants ranging from $25,000 to $850,000 without audit findings."
        ),
        "notes": "Use in organizational capacity sections. Update audit year count annually.",
    },
    {
        "category": "Community Need",
        "title": "Woonsocket community overview",
        "tags": "community, need, woonsocket, poverty, demographics",
        "content": (
            "Woonsocket is one of Rhode Island's most economically distressed cities. "
            "With a population of approximately 43,000, the city has a median household "
            "income of $40,527 — well below the state median of $70,305 — and a poverty "
            "rate of 25.9%, compared to 11.0% statewide. Youth poverty is particularly "
            "severe, with 38% of children under 18 living below the federal poverty line. "
            "Woonsocket's population is approximately 42% Latino, 12% Black, and 8% "
            "Asian, making it one of Rhode Island's most diverse cities and one where "
            "culturally and linguistically responsive services are essential, not optional."
        ),
        "notes": "Sources: ACS 2022, RI Kids Count 2023. Update data annually in January.",
    },
    {
        "category": "Community Need",
        "title": "Youth mental health need — Woonsocket specific",
        "tags": "youth, mental health, need, community, adolescent",
        "content": (
            "Youth in Woonsocket face an extraordinary mental health burden. Rates of "
            "adolescent depression in Providence County exceed the national average by 22%, "
            "and local school counselors and pediatric providers report a sharp increase "
            "in crisis referrals since 2020. Despite this high level of need, only one in "
            "five youth in Woonsocket who require mental health services currently receives "
            "them. The shortage of culturally responsive providers is a critical driver: "
            "the city's majority-Latino population is served by a behavioral health "
            "workforce that is overwhelmingly white and English-monolingual, creating "
            "barriers of language, culture, and trust."
        ),
        "notes": "Sources: RI DOH, Landmark Medical Center ED data, SAMHSA NSDUH.",
    },
    {
        "category": "Community Need",
        "title": "Health equity and SDOH framing",
        "tags": "health equity, social determinants, SDOH, equity, disparities",
        "content": (
            "The health disparities facing Woonsocket residents are not random — they are "
            "the predictable result of disinvestment in communities of color, inadequate "
            "access to living wages and stable housing, and health systems that have "
            "historically failed to reflect the cultures and languages of the communities "
            "they serve. Addressing these disparities requires community-rooted organizations "
            "with deep trust, bilingual capacity, and a commitment to meeting people where "
            "they are. Communicare Alliance was built for exactly this purpose."
        ),
        "notes": "Good for health equity-focused funders like RWJF, Blue Cross Foundation.",
    },
    {
        "category": "Pilot Data & Outcomes",
        "title": "Youth Mental Health pilot results (2022–2024)",
        "tags": "pilot, outcomes, youth, mental health, data, evidence",
        "content": (
            "In a 2022–2024 pilot serving 60 youth ages 12–18 in Woonsocket, Communicare "
            "Alliance demonstrated strong early outcomes. Seventy-eight percent of "
            "participants showed a clinically meaningful reduction in PHQ-A depression "
            "scores (decrease of five or more points) after eight weeks of individual "
            "counseling — exceeding the 75% target. Among the 22 youth with chronic "
            "school absenteeism prior to enrollment, school attendance improved by an "
            "average of 11 days per year. Eighty-four percent of caregivers who completed "
            "the family psychoeducation workshop series reported increased confidence in "
            "supporting their child's mental health."
        ),
        "notes": "Key stats: 78% PHQ-A reduction, 11 days attendance, 84% caregiver confidence.",
    },
    {
        "category": "Pilot Data & Outcomes",
        "title": "Organization-wide outcome highlights (FY2024)",
        "tags": "outcomes, annual, data, impact, FY2024",
        "content": (
            "In fiscal year 2024, Communicare Alliance served 2,547 unduplicated individuals "
            "across all programs, delivering 18,320 units of service. Across our behavioral "
            "health programs, 71% of clients with depression screening scores in the moderate "
            "or severe range at intake showed clinically meaningful improvement by discharge. "
            "Our family support program achieved an 89% rate of families meeting their "
            "self-identified stability goals within 90 days of enrollment. Program completion "
            "rates averaged 76% across service lines."
        ),
        "notes": "Update each October after fiscal year close.",
    },
    {
        "category": "Staff Bios",
        "title": "Executive Director bio",
        "tags": "staff, bio, leadership, executive director",
        "content": (
            "Maria Santos, LICSW, has served as Executive Director of Communicare Alliance "
            "since 2016. A licensed independent clinical social worker with 22 years of "
            "experience in community behavioral health, Ms. Santos previously served as "
            "Director of Programs at Family Service of Rhode Island and as a clinical "
            "supervisor at The Providence Center. She holds an MSW from Boston University "
            "and a certificate in Nonprofit Leadership from Brown University's School of "
            "Professional Studies. Ms. Santos is a founding member of the Rhode Island "
            "Coalition for Behavioral Health Equity."
        ),
        "notes": "Update if ED changes. Use for key personnel sections.",
    },
    {
        "category": "Staff Bios",
        "title": "Director of Programs bio",
        "tags": "staff, bio, programs, director, clinical",
        "content": (
            "James Ferreira, MSW, LCSW, serves as Director of Programs at Communicare "
            "Alliance, a role he has held since 2019. With 12 years of experience in "
            "community behavioral health, Mr. Ferreira oversees all clinical programs. "
            "He previously served as a school-based clinician with Providence Public "
            "Schools and as clinical coordinator at Thundermist Health Center. "
            "Mr. Ferreira holds an MSW from Rhode Island College and is bilingual "
            "in English and Spanish."
        ),
        "notes": "This is the Project Director for most youth grants.",
    },
    {
        "category": "Program Descriptions",
        "title": "Youth Mental Health Program — standard description",
        "tags": "youth, mental health, program description, services",
        "content": (
            "The Youth Mental Health and Resilience Program delivers evidence-based "
            "behavioral health services to youth ages 12–18 in Woonsocket through "
            "schools and a community clinic. Services include weekly individual counseling "
            "using Cognitive Behavioral Therapy for Adolescents (CBT-A), bi-weekly "
            "8-week resilience skills groups using the COPE curriculum, monthly family "
            "psychoeducation workshops, peer mentorship, and annual trauma-informed "
            "practices training for school staff. All services are available in English "
            "and Spanish. The program serves 150 unduplicated youth annually."
        ),
        "notes": "Standard description for grant applications. Shorten as needed.",
    },
    {
        "category": "Partnerships",
        "title": "Key community partnerships — standard list",
        "tags": "partnerships, community, coalition, MOU",
        "content": (
            "Communicare Alliance maintains formal partnership agreements with the "
            "Woonsocket Education Department, Thundermist Health Center, the Rhode Island "
            "Department of Children Youth and Families (DCYF), Our Lady of Fatima Parish "
            "Community, and the Woonsocket Housing Authority. These partnerships are "
            "formalized through memoranda of understanding specifying data sharing, "
            "referral pathways, co-location arrangements, and shared staffing. Partnership "
            "relationships average nine years in duration."
        ),
        "notes": "Update MOU list annually.",
    },
    {
        "category": "Evaluation",
        "title": "Standard evaluation approach paragraph",
        "tags": "evaluation, data, outcomes, methods, boilerplate",
        "content": (
            "Communicare Alliance maintains a robust data infrastructure to track program "
            "outputs, outcomes, and equity indicators across all service lines. We use an "
            "electronic health record system for clinical data, validated assessment "
            "instruments including the PHQ-A, GAD-7, and COPE outcomes scale, and a "
            "quarterly data review process that brings together program staff to examine "
            "trends and make real-time program adjustments. All outcome data are "
            "disaggregated by race, ethnicity, age, gender, and income level."
        ),
        "notes": "Customize with program-specific instruments for each application.",
    },
    {
        "category": "Equity",
        "title": "Equity and inclusion commitment statement",
        "tags": "equity, inclusion, diversity, DEI, commitment",
        "content": (
            "Communicare Alliance is committed to equity as an organizational value, not "
            "a program feature. This commitment is reflected in our staff composition — "
            "over 60% staff of color, 40% bilingual — our governance — a Board with "
            "majority representation of the communities we serve — and our program design, "
            "which centers community voice through a Community Advisory Group that includes "
            "current and former program participants. We apply an equity lens to all hiring, "
            "program design, and evaluation decisions."
        ),
        "notes": "Strong for RWJF, Annie E. Casey, Blue Cross Foundation.",
    },
    {
        "category": "Sustainability",
        "title": "Standard sustainability statement",
        "tags": "sustainability, funding, medicaid, revenue, long-term",
        "content": (
            "Communicare Alliance pursues a diversified funding strategy that reduces "
            "dependence on any single revenue source. For clinically delivered behavioral "
            "health services, we actively pursue Medicaid reimbursement, which currently "
            "covers approximately 38% of program costs. State contract revenue through "
            "DCYF and BHDDH provides a stable foundation at 28% of operating revenue. "
            "Foundation grants support innovation and community health programs not covered "
            "by third-party payers. We maintain six months of operating reserves in "
            "accordance with our Board-approved reserve policy."
        ),
        "notes": "Update Medicaid and state contract percentages annually.",
    },
]

CATEGORY_COLORS = {
    "Org Identity":          "teal",
    "Community Need":        "blue",
    "Pilot Data & Outcomes": "green",
    "Staff Bios":            "amber",
    "Program Descriptions":  "purple",
    "Partnerships":          "coral",
    "Evaluation":            "blue",
    "Equity":                "green",
    "Sustainability":        "amber",
}

def get_color(category):
    return CATEGORY_COLORS.get(category, "teal")

# ─────────────────────────────────────────────────────────────────────────────
# In-memory database using session state
# ─────────────────────────────────────────────────────────────────────────────

def init_library():
    """Initialize the library in session state if not already done."""
    if "library" not in st.session_state:
        blocks = []
        for i, b in enumerate(STARTER_BLOCKS, 1):
            blocks.append({
                "id":        i,
                "category":  b["category"],
                "title":     b["title"],
                "tags":      b["tags"],
                "content":   b["content"],
                "notes":     b.get("notes", ""),
                "use_count": 0,
                "created":   datetime.date.today().isoformat(),
            })
        st.session_state.library = blocks
        st.session_state.next_id = len(blocks) + 1

def get_blocks():
    return st.session_state.library

def get_categories():
    seen = []
    for b in st.session_state.library:
        if b["category"] not in seen:
            seen.append(b["category"])
    return seen

def search_blocks(query):
    if not query.strip():
        return st.session_state.library
    terms = query.lower().split()
    results = []
    for b in st.session_state.library:
        text = (b["title"] + " " + b["content"] + " " +
                b["tags"] + " " + b["category"] + " " + b["notes"]).lower()
        if all(t in text for t in terms):
            results.append(b)
    return sorted(results, key=lambda x: x["use_count"], reverse=True)

def add_block(category, title, tags, content, notes):
    new_id = st.session_state.next_id
    st.session_state.library.append({
        "id":        new_id,
        "category":  category,
        "title":     title,
        "tags":      tags,
        "content":   content,
        "notes":     notes,
        "use_count": 0,
        "created":   datetime.date.today().isoformat(),
    })
    st.session_state.next_id += 1
    return new_id

def delete_block(block_id):
    st.session_state.library = [
        b for b in st.session_state.library if b["id"] != block_id
    ]

def increment_use(block_id):
    for b in st.session_state.library:
        if b["id"] == block_id:
            b["use_count"] += 1
            break

def polish_with_claude(content, funder, program, word_count, notes, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are helping a grant writer at Communicare Alliance in Woonsocket, RI
tailor a boilerplate text block for a specific grant application.

ORIGINAL TEXT:
{content}

TAILOR FOR:
- Funder: {funder}
- Grant/program: {program}
- Target word count: approximately {word_count} words
- Special notes: {notes or 'None'}

Rewrite the text to be optimally suited for this funder and grant.
Keep all factual content accurate — do not invent data or accomplishments.
Stay within 10% of the target word count.
Return ONLY the rewritten text, no commentary."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────────────────────

init_library()
api_key = get_api_key()

st.title("📚 Boilerplate Library")
st.caption("Searchable database of reusable text blocks — pull any block into a grant in seconds.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### How to use")
    st.markdown("""
1. **Search** for what you need
2. **Copy** the text into your grant
3. **Polish** with Claude to tailor for a specific funder
4. **Add** your own blocks as you write great paragraphs
""")
    st.markdown("---")
    st.markdown("### Library stats")
    blocks = get_blocks()
    cats   = get_categories()
    st.metric("Total blocks", len(blocks))
    st.metric("Categories",   len(cats))
    top = sorted(blocks, key=lambda x: x["use_count"], reverse=True)[:3]
    if any(b["use_count"] > 0 for b in top):
        st.markdown("**Most used:**")
        for b in top:
            if b["use_count"] > 0:
                st.caption(f"• {b['title'][:40]}... ({b['use_count']}x)")
    st.markdown("---")
    st.markdown("### Export all blocks")
    export_text = "\n\n".join(
        f"[{b['id']}] {b['category'].upper()} — {b['title']}\n"
        f"Tags: {b['tags']}\n\n{b['content']}"
        + (f"\n\nNOTES: {b['notes']}" if b['notes'] else "")
        + "\n" + "─" * 60
        for b in blocks
    )
    st.download_button(
        "⬇ Download all as text",
        data=export_text.encode("utf-8"),
        file_name=f"boilerplate_library_{datetime.date.today()}.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_search, tab_browse, tab_add, tab_polish = st.tabs([
    "🔍 Search", "📂 Browse by category", "➕ Add new block", "✨ Polish with Claude"
])

# ── TAB 1: Search ─────────────────────────────────────────────────────────────

with tab_search:
    st.markdown("### Search your library")
    st.markdown('<div class="hint">Try: mission · pilot data · equity · youth mental health · sustainability · bio</div>',
                unsafe_allow_html=True)

    query = st.text_input("Search", placeholder="Type keywords...",
                          label_visibility="collapsed")
    results = search_blocks(query)

    if query and not results:
        st.info("No results. Try different keywords or browse by category.")

    for b in results:
        wc = len(b["content"].split())
        color = get_color(b["category"])
        with st.container():
            st.markdown(
                f'<div class="block-card {color}">'
                f'<strong style="color:#1F2937">{b["title"]}</strong>'
                f'<span style="color:#9CA3AF;font-size:.8rem"> — {b["category"]} · {wc} words</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Tags
            if b["tags"]:
                tag_html = " ".join(
                    f'<span class="tag">{t.strip()}</span>'
                    for t in b["tags"].split(",")
                )
                st.markdown(tag_html, unsafe_allow_html=True)

            # Content preview + full toggle
            preview = b["content"][:200] + ("..." if len(b["content"]) > 200 else "")
            show_full = st.checkbox(f"Show full text", key=f"show_{b['id']}")

            if show_full:
                st.text_area(
                    "Full text (select all and copy)",
                    value=b["content"],
                    height=160,
                    key=f"content_{b['id']}",
                    label_visibility="collapsed",
                )
                if b["notes"]:
                    st.caption(f"📝 {b['notes']}")
                increment_use(b["id"])
            else:
                st.caption(preview)

            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.caption(f"Used {b['use_count']}x")
            with c3:
                if st.button("🗑", key=f"del_{b['id']}", help="Delete this block"):
                    delete_block(b["id"])
                    st.rerun()

            st.markdown("---")

# ── TAB 2: Browse by category ─────────────────────────────────────────────────

with tab_browse:
    st.markdown("### Browse by category")
    selected_cat = st.selectbox("Category", get_categories(),
                                label_visibility="collapsed")

    cat_blocks = [b for b in get_blocks() if b["category"] == selected_cat]
    st.caption(f"{len(cat_blocks)} block(s) in {selected_cat}")

    for b in cat_blocks:
        wc = len(b["content"].split())
        with st.expander(f"**{b['title']}** — {wc} words · used {b['use_count']}x"):
            st.text_area("Content", value=b["content"], height=140,
                         key=f"browse_{b['id']}", label_visibility="collapsed")
            if b["notes"]:
                st.caption(f"📝 {b['notes']}")
            if b["tags"]:
                tag_html = " ".join(
                    f'<span class="tag">{t.strip()}</span>'
                    for t in b["tags"].split(",")
                )
                st.markdown(tag_html, unsafe_allow_html=True)
            if st.button("Mark as used", key=f"use_{b['id']}"):
                increment_use(b["id"])
                st.success("Logged!")

# ── TAB 3: Add new block ──────────────────────────────────────────────────────

with tab_add:
    st.markdown("### Add a new block")
    st.markdown('<div class="hint">Every good paragraph you write this grant season can go '
                'in the library for next time. Build it up over time.</div>',
                unsafe_allow_html=True)

    existing_cats = get_categories()
    cat_options   = existing_cats + ["+ New category"]
    cat_choice    = st.selectbox("Category", cat_options)

    if cat_choice == "+ New category":
        new_category = st.text_input("New category name")
    else:
        new_category = cat_choice

    new_title   = st.text_input("Title (descriptive, e.g. 'Mission statement — short')")
    new_tags    = st.text_input("Tags (comma-separated)", placeholder="e.g. mission, boilerplate, identity")
    new_content = st.text_area("Text content", height=180,
                               placeholder="Paste your reusable paragraph here...")
    new_notes   = st.text_input("Internal notes (usage guidance, data source, update reminders)")

    if st.button("💾 Save to library", use_container_width=False):
        if not new_title:
            st.error("Please enter a title.")
        elif not new_content:
            st.error("Please enter some content.")
        elif not new_category or new_category == "+ New category":
            st.error("Please enter a category name.")
        else:
            new_id = add_block(new_category, new_title, new_tags,
                               new_content, new_notes)
            wc = len(new_content.split())
            st.success(f"✅ Saved as block #{new_id} ({wc} words)")
            st.rerun()

# ── TAB 4: Polish with Claude ─────────────────────────────────────────────────

with tab_polish:
    st.markdown("### Polish a block for a specific funder")
    st.markdown('<div class="hint">Pick any block from your library and Claude rewrites it '
                'tuned to a specific funder\'s priorities and word count.</div>',
                unsafe_allow_html=True)

    if not api_key:
        st.markdown(
            '<div class="warn">⚠ API key not set. Add ANTHROPIC_API_KEY in '
            'Streamlit Cloud → Settings → Secrets.</div>',
            unsafe_allow_html=True,
        )

    all_blocks    = get_blocks()
    block_options = {f"[{b['id']}] {b['title']}": b for b in all_blocks}
    selected_key  = st.selectbox("Select a block to polish", list(block_options.keys()))
    selected_block = block_options[selected_key]

    st.text_area("Original text", value=selected_block["content"],
                 height=120, disabled=True, label_visibility="collapsed")
    st.caption(f"{len(selected_block['content'].split())} words · {selected_block['category']}")

    c1, c2 = st.columns(2)
    with c1:
        polish_funder  = st.text_input("Funder name", placeholder="e.g. Rhode Island Foundation")
        polish_program = st.text_input("Grant/program", placeholder="e.g. Youth Mental Health Initiative")
    with c2:
        polish_words = st.number_input(
            "Target word count",
            min_value=20, max_value=500,
            value=len(selected_block["content"].split()),
        )
        polish_notes = st.text_input("Special emphasis for this funder",
                                     placeholder="e.g. strong equity framing, mention RI data")

    if "polished_text" not in st.session_state:
        st.session_state.polished_text = ""

    if st.button("✨ Polish with Claude", disabled=not api_key,
                 use_container_width=False):
        if not polish_funder:
            st.error("Please enter a funder name.")
        else:
            with st.spinner(f"Tailoring for {polish_funder}..."):
                try:
                    polished = polish_with_claude(
                        selected_block["content"],
                        polish_funder, polish_program,
                        polish_words, polish_notes, api_key,
                    )
                    st.session_state.polished_text = polished
                except Exception as e:
                    st.error(f"Polish failed: {e}")

    if st.session_state.polished_text:
        st.markdown("#### Polished version")
        polished_edit = st.text_area(
            "Polished text (edit as needed)",
            value=st.session_state.polished_text,
            height=180,
            label_visibility="collapsed",
        )
        wc = len(polished_edit.split())
        st.caption(f"{wc} words")

        if st.button("💾 Save polished version as new block"):
            new_title_p = f"{selected_block['title']} — tailored for {polish_funder}"
            new_id_p = add_block(
                selected_block["category"],
                new_title_p,
                selected_block["tags"],
                polished_edit,
                f"Tailored from block #{selected_block['id']} for {polish_funder} / {polish_program}",
            )
            st.success(f"✅ Saved as new block #{new_id_p}")
            st.session_state.polished_text = ""
            st.rerun()
