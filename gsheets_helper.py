"""
gsheets_helper.py
=================
Shared helper for reading and writing to the Communicare Tools
Google Sheet via the Google Sheets API.

Used by:
  8_Boilerplate_Library.py
  10_Funder_Tracker.py
"""

import streamlit as st
import datetime
import json
import re

# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports — gspread only installed if available
# ─────────────────────────────────────────────────────────────────────────────

def get_client():
    """Return an authorised gspread client, cached for this session."""
    if "gsheets_client" in st.session_state:
        return st.session_state.gsheets_client
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # Load credentials from Streamlit Secrets
        raw = dict(st.secrets["gcp_service_account"])
        # Fix newlines in private key if they got escaped
        if "private_key" in raw:
            raw["private_key"] = raw["private_key"].replace("\\n", "\n")

        creds  = Credentials.from_service_account_info(raw, scopes=scopes)
        client = gspread.authorize(creds)
        st.session_state.gsheets_client = client
        return client
    except Exception as e:
        raise RuntimeError(f"Google Sheets auth failed: {e}")


def get_sheet(tab_name: str):
    """Return a worksheet object for the named tab."""
    client   = get_client()
    sheet_id = st.secrets["GSHEET_ID"]
    wb       = client.open_by_key(sheet_id)
    return wb.worksheet(tab_name)


# ─────────────────────────────────────────────────────────────────────────────
# Generic read / write
# ─────────────────────────────────────────────────────────────────────────────

def read_sheet(tab_name: str) -> list[dict]:
    """Read all rows from a tab. Returns list of dicts keyed by header row."""
    try:
        ws   = get_sheet(tab_name)
        rows = ws.get_all_records(default_blank="")
        return rows
    except Exception as e:
        st.warning(f"Could not read {tab_name} from Google Sheets: {e}")
        return []


def write_sheet(tab_name: str, headers: list, rows: list[list]):
    """Overwrite a tab with headers + rows."""
    try:
        ws = get_sheet(tab_name)
        ws.clear()
        all_rows = [headers] + rows
        ws.update(all_rows, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.warning(f"Could not write to {tab_name}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Boilerplate helpers
# ─────────────────────────────────────────────────────────────────────────────

BOILERPLATE_HEADERS = [
    "id", "category", "title", "tags",
    "content", "notes", "use_count", "created",
]

STARTER_BLOCKS = [
    {"id":1,"category":"Org Identity","title":"Mission statement — standard",
     "tags":"mission, boilerplate, identity","use_count":0,
     "created":str(datetime.date.today()),"notes":"Use in every grant.",
     "content":"Communicare Alliance's mission is to strengthen the health and well-being of individuals and families in Woonsocket and the surrounding Blackstone Valley through community-centered, culturally responsive human services."},
    {"id":2,"category":"Org Identity","title":"Org history — full",
     "tags":"history, overview, capacity","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update annual numbers each January.",
     "content":"Founded in 1994, Communicare Alliance has served the Woonsocket community for over 30 years as one of Rhode Island's leading community-based human services organizations. We deliver behavioral health, family support, and community health programs to more than 2,500 individuals annually. Our staff of 42 includes licensed clinical social workers, community health workers, case managers, and peer specialists, with over 60% identifying as people of color and 40% speaking Spanish as a primary language."},
    {"id":3,"category":"Org Identity","title":"Org history — short",
     "tags":"history, overview, short","use_count":0,
     "created":str(datetime.date.today()),"notes":"Use when page limits are tight.",
     "content":"Founded in 1994, Communicare Alliance has served Woonsocket for over 30 years, delivering behavioral health, family support, and community health programs to more than 2,500 individuals annually. Our 42-person staff is majority people of color and 40% bilingual Spanish/English."},
    {"id":4,"category":"Org Identity","title":"Financial management and audit statement",
     "tags":"financial, audit, capacity, compliance","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update audit year count annually.",
     "content":"Communicare Alliance maintains strong financial management systems and has received clean independent audits for 19 consecutive years. We operate on an annual budget of approximately $4.2 million and have successfully managed federal, state, and foundation grants ranging from $25,000 to $850,000 without audit findings."},
    {"id":5,"category":"Community Need","title":"Woonsocket community overview",
     "tags":"community, need, woonsocket, poverty, demographics","use_count":0,
     "created":str(datetime.date.today()),"notes":"Sources: ACS 2022, RI Kids Count 2023.",
     "content":"Woonsocket is one of Rhode Island's most economically distressed cities. With a population of approximately 43,000, the city has a median household income of $40,527 — well below the state median of $70,305 — and a poverty rate of 25.9%, compared to 11.0% statewide. Youth poverty is particularly severe, with 38% of children under 18 living below the federal poverty line. Woonsocket's population is approximately 42% Latino and 12% Black."},
    {"id":6,"category":"Community Need","title":"Youth mental health need — Woonsocket specific",
     "tags":"youth, mental health, need, community, adolescent","use_count":0,
     "created":str(datetime.date.today()),"notes":"Sources: RI DOH, Landmark Medical Center ED data.",
     "content":"Youth in Woonsocket face an extraordinary mental health burden. Rates of adolescent depression in Providence County exceed the national average by 22%, and local school counselors report a sharp increase in crisis referrals since 2020. Despite this high level of need, only one in five youth in Woonsocket who require mental health services currently receives them."},
    {"id":7,"category":"Community Need","title":"Health equity and SDOH framing",
     "tags":"health equity, social determinants, SDOH, equity, disparities","use_count":0,
     "created":str(datetime.date.today()),"notes":"Good for RWJF, Blue Cross Foundation.",
     "content":"The health disparities facing Woonsocket residents are the predictable result of disinvestment in communities of color and health systems that have historically failed to reflect the cultures and languages of the communities they serve. Addressing these disparities requires community-rooted organizations with deep trust, bilingual capacity, and a commitment to meeting people where they are."},
    {"id":8,"category":"Pilot Data & Outcomes","title":"Youth Mental Health pilot results (2022–2024)",
     "tags":"pilot, outcomes, youth, mental health, data, evidence","use_count":0,
     "created":str(datetime.date.today()),"notes":"Key stats: 78% PHQ-A reduction, 11 days attendance improvement.",
     "content":"In a 2022–2024 pilot serving 60 youth ages 12–18, 78% of participants showed a clinically meaningful reduction in PHQ-A depression scores after eight weeks of individual counseling. Among youth with chronic school absenteeism, attendance improved by an average of 11 days per year. 84% of caregivers who completed the family psychoeducation workshop series reported increased confidence in supporting their child's mental health."},
    {"id":9,"category":"Pilot Data & Outcomes","title":"Organization-wide outcome highlights (FY2024)",
     "tags":"outcomes, annual, data, impact, FY2024","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update each October after fiscal year close.",
     "content":"In fiscal year 2024, Communicare Alliance served 2,547 unduplicated individuals across all programs, delivering 18,320 units of service. 71% of clients with depression screening scores in the moderate or severe range at intake showed clinically meaningful improvement by discharge. Program completion rates averaged 76% across service lines."},
    {"id":10,"category":"Staff Bios","title":"Executive Director bio",
     "tags":"staff, bio, leadership, executive director","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update if ED changes.",
     "content":"Maria Santos, LICSW, has served as Executive Director of Communicare Alliance since 2016. A licensed independent clinical social worker with 22 years of experience in community behavioral health, Ms. Santos holds an MSW from Boston University and is a founding member of the Rhode Island Coalition for Behavioral Health Equity."},
    {"id":11,"category":"Equity","title":"Equity and inclusion commitment statement",
     "tags":"equity, inclusion, diversity, DEI, commitment","use_count":0,
     "created":str(datetime.date.today()),"notes":"Strong for RWJF, Annie E. Casey, Blue Cross Foundation.",
     "content":"Communicare Alliance is committed to equity as an organizational value, not a program feature. This commitment is reflected in our staff composition — over 60% staff of color, 40% bilingual — our governance, and our program design, which centers community voice through a Community Advisory Group that includes current and former program participants."},
    {"id":12,"category":"Sustainability","title":"Standard sustainability statement",
     "tags":"sustainability, funding, medicaid, revenue, long-term","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update Medicaid percentage annually.",
     "content":"Communicare Alliance pursues a diversified funding strategy that reduces dependence on any single revenue source. Medicaid reimbursement currently covers approximately 38% of program costs. State contract revenue through DCYF and BHDDH provides a stable foundation at 28% of operating revenue. We maintain six months of operating reserves in accordance with our Board-approved reserve policy."},
    {"id":13,"category":"Evaluation","title":"Standard evaluation approach paragraph",
     "tags":"evaluation, data, outcomes, methods, boilerplate","use_count":0,
     "created":str(datetime.date.today()),"notes":"Customize with program-specific instruments.",
     "content":"Communicare Alliance maintains a robust data infrastructure to track program outputs, outcomes, and equity indicators across all service lines. We use validated assessment instruments including the PHQ-A, GAD-7, and COPE outcomes scale. All outcome data are disaggregated by race, ethnicity, age, gender, and income level to ensure equity gaps are visible and addressed."},
    {"id":14,"category":"Partnerships","title":"Key community partnerships — standard list",
     "tags":"partnerships, community, coalition, MOU","use_count":0,
     "created":str(datetime.date.today()),"notes":"Update MOU list annually.",
     "content":"Communicare Alliance maintains formal partnership agreements with the Woonsocket Education Department, Thundermist Health Center, the Rhode Island Department of Children Youth and Families (DCYF), Our Lady of Fatima Parish Community, and the Woonsocket Housing Authority. Partnership relationships average nine years in duration."},
    {"id":15,"category":"Program Descriptions","title":"Youth Mental Health Program — standard description",
     "tags":"youth, mental health, program description, services","use_count":0,
     "created":str(datetime.date.today()),"notes":"Standard description for grant applications.",
     "content":"The Youth Mental Health and Resilience Program delivers evidence-based behavioral health services to youth ages 12–18 in Woonsocket through schools and a community clinic. Services include weekly individual counseling using CBT-A, bi-weekly resilience skills groups using the COPE curriculum, monthly family psychoeducation workshops, peer mentorship, and annual trauma-informed practices training for school staff. All services are available in English and Spanish."},
    {"id":16,"category":"Program Descriptions","title":"Community health worker model description",
     "tags":"community health worker, CHW, model, description","use_count":0,
     "created":str(datetime.date.today()),"notes":"Use when describing CHW components.",
     "content":"Communicare Alliance's community health worker model deploys trained, trusted community members to provide outreach, navigation, health education, and informal counseling to residents who face barriers to accessing formal services. Our CHWs are recruited from the communities they serve, are majority bilingual, and receive 120 hours of initial training plus ongoing supervision."},
]


def load_boilerplate() -> list[dict]:
    rows = read_sheet("Boilerplate")
    if not rows:
        save_boilerplate(STARTER_BLOCKS)
        return list(STARTER_BLOCKS)
    for r in rows:
        try:    r["use_count"] = int(r.get("use_count", 0))
        except: r["use_count"] = 0
        try:    r["id"] = int(r.get("id", 0))
        except: r["id"] = 0
    return rows


def save_boilerplate(blocks: list[dict]) -> bool:
    rows = [
        [b.get("id",""), b.get("category",""), b.get("title",""),
         b.get("tags",""), b.get("content",""), b.get("notes",""),
         b.get("use_count",0), b.get("created", str(datetime.date.today()))]
        for b in blocks
    ]
    return write_sheet("Boilerplate", BOILERPLATE_HEADERS, rows)


# ─────────────────────────────────────────────────────────────────────────────
# Funder helpers
# ─────────────────────────────────────────────────────────────────────────────

FUNDER_HEADERS = [
    "name","url","geo","notes","alignment_score","matched_terms",
    "priority_tier","relationship_status","next_action",
    "last_contact_notes","grant_range_min","grant_range_max",
    "deadline_info","contact_info","scraped",
]

DEFAULT_FUNDERS = [
    {"name":"Rhode Island Foundation","url":"https://rifoundation.org/grants","geo":"Rhode Island","notes":"Largest RI community foundation; health & human services priority","alignment_score":85,"matched_terms":"mental health, youth, community health, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Champlin Foundation","url":"https://champlinfoundations.org","geo":"Rhode Island","notes":"RI-only funder; health focus; strong relationship potential","alignment_score":80,"matched_terms":"community health, youth, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"van Beuren Charitable Foundation","url":"https://vanbeuren.org","geo":"Rhode Island","notes":"Newport-based; rural RI; health & human services","alignment_score":75,"matched_terms":"community health, family, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Robert Wood Johnson Foundation","url":"https://www.rwjf.org/en/grants","geo":"National","notes":"Largest US health philanthropy; health equity focus","alignment_score":78,"matched_terms":"mental health, health equity, underserved, community health","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Annie E. Casey Foundation","url":"https://www.aecf.org","geo":"National","notes":"Children and families; evidence-based programs","alignment_score":72,"matched_terms":"youth, children, family, community health","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Blue Cross Blue Shield Foundation of MA","url":"https://bluecrossmafoundation.org","geo":"New England","notes":"Health equity; behavioral health; New England focus","alignment_score":82,"matched_terms":"mental health, behavioral health, health equity, new england","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Amica Companies Foundation","url":"https://www.amica.com/community","geo":"Rhode Island","notes":"Providence-based corporate; education and community","alignment_score":55,"matched_terms":"community health, youth, rhode island","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Kresge Foundation","url":"https://kresge.org","geo":"National","notes":"Health, cities, low-income communities","alignment_score":58,"matched_terms":"community health, underserved, low income","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"W.K. Kellogg Foundation","url":"https://www.wkkf.org","geo":"National","notes":"Children, families, health equity","alignment_score":65,"matched_terms":"youth, children, family, health equity","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Conrad N. Hilton Foundation","url":"https://www.hiltonfoundation.org","geo":"National","notes":"Vulnerable populations; homelessness, children","alignment_score":48,"matched_terms":"children, family, underserved","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
]


def load_funders() -> list[dict]:
    rows = read_sheet("Funders")
    if not rows:
        save_funders(DEFAULT_FUNDERS)
        return list(DEFAULT_FUNDERS)
    for r in rows:
        try:    r["alignment_score"] = int(r.get("alignment_score", 0))
        except: r["alignment_score"] = 0
    return rows


def save_funders(funders: list[dict]) -> bool:
    rows = [[f.get(h, "") for h in FUNDER_HEADERS] for f in funders]
    return write_sheet("Funders", FUNDER_HEADERS, rows)
