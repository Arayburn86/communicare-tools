"""
onedrive_helper.py
==================
Shared helper for reading and writing to the Communicare data Excel file
on OneDrive via the Microsoft Graph API.

Used by:
  8_Boilerplate_Library.py
  10_Funder_Tracker.py
"""

import requests
import streamlit as st
import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Credentials — loaded from Streamlit Secrets
# ─────────────────────────────────────────────────────────────────────────────

def get_creds():
    return {
        "tenant_id":     st.secrets["AZURE_TENANT_ID"],
        "client_id":     st.secrets["AZURE_CLIENT_ID"],
        "client_secret": st.secrets["AZURE_CLIENT_SECRET"],
        "user_email":    st.secrets["ONEDRIVE_USER_EMAIL"],
        "file_id":       st.secrets["ONEDRIVE_FILE_ID"],
    }

# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3000)  # cache token for 50 minutes (tokens last 60)
def get_token():
    """Get OAuth2 token using client credentials flow."""
    creds = get_creds()
    url = f"https://login.microsoftonline.com/{creds['tenant_id']}/oauth2/v2.0/token"
    data = {
        "grant_type":    "client_credentials",
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "scope":         "https://graph.microsoft.com/.default",
    }
    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def graph_headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type":  "application/json",
    }

# ─────────────────────────────────────────────────────────────────────────────
# Excel helpers via Graph API
# ─────────────────────────────────────────────────────────────────────────────

def sheet_base_url():
    creds  = get_creds()
    email  = creds["user_email"]
    file_id = creds["file_id"]
    return (
        f"https://graph.microsoft.com/v1.0"
        f"/users/{email}/drive/items/{file_id}/workbook/worksheets"
    )


def read_sheet(sheet_name: str) -> list[dict]:
    """
    Read all data rows from a named worksheet.
    Returns a list of dicts keyed by the header row.
    """
    url  = f"{sheet_base_url()}/{sheet_name}/usedRange"
    resp = requests.get(url, headers=graph_headers(), timeout=20)

    if resp.status_code == 404:
        return []
    resp.raise_for_status()

    data = resp.json()
    values = data.get("values", [])
    if len(values) < 2:
        return []  # only headers or empty

    headers = values[0]
    rows    = []
    for row in values[1:]:
        # Pad short rows
        while len(row) < len(headers):
            row.append("")
        rows.append(dict(zip(headers, row)))
    return rows


def write_sheet(sheet_name: str, headers: list, rows: list[list]):
    """
    Overwrite a worksheet with headers + rows.
    rows is a list of lists (values only, matching header order).
    """
    values = [headers] + rows

    # Find used range first so we can clear it
    base = sheet_base_url()
    clear_url = f"{base}/{sheet_name}/usedRange/clear"
    requests.post(clear_url, headers=graph_headers(),
                  json={"applyTo": "contents"}, timeout=15)

    # Write new data starting at A1
    update_url = f"{base}/{sheet_name}/range(address='A1')"
    body = {"values": values}

    # Calculate address range
    col_count = len(headers)
    row_count = len(values)
    col_letter = col_num_to_letter(col_count)
    address    = f"A1:{col_letter}{row_count}"
    update_url = f"{base}/{sheet_name}/range(address='{address}')"

    resp = requests.patch(update_url, headers=graph_headers(),
                          json={"values": values}, timeout=30)
    resp.raise_for_status()
    return True


def append_row(sheet_name: str, headers: list, row_values: list):
    """Append a single row to a worksheet."""
    existing = read_sheet(sheet_name)
    rows = [[r.get(h, "") for h in headers] for r in existing]
    rows.append(row_values)
    return write_sheet(sheet_name, headers, rows)


def col_num_to_letter(n: int) -> str:
    """Convert column number to Excel letter (1=A, 26=Z, 27=AA)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

# ─────────────────────────────────────────────────────────────────────────────
# Boilerplate Library helpers
# ─────────────────────────────────────────────────────────────────────────────

BOILERPLATE_HEADERS = [
    "id", "category", "title", "tags",
    "content", "notes", "use_count", "created",
]

STARTER_BLOCKS = [
    {"id":1,"category":"Org Identity","title":"Mission statement — standard",
     "tags":"mission, boilerplate, identity","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Use in every grant.",
     "content":"Communicare Alliance's mission is to strengthen the health and well-being of individuals and families in Woonsocket and the surrounding Blackstone Valley through community-centered, culturally responsive human services."},
    {"id":2,"category":"Org Identity","title":"Org history — full",
     "tags":"history, overview, capacity","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Update annual numbers each January.",
     "content":"Founded in 1994, Communicare Alliance has served the Woonsocket community for over 30 years as one of Rhode Island's leading community-based human services organizations. We deliver behavioral health, family support, and community health programs to more than 2,500 individuals annually. Our staff of 42 includes licensed clinical social workers, community health workers, case managers, and peer specialists, with over 60% identifying as people of color and 40% speaking Spanish as a primary language."},
    {"id":3,"category":"Org Identity","title":"Org history — short",
     "tags":"history, overview, short","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Use when page limits are tight.",
     "content":"Founded in 1994, Communicare Alliance has served Woonsocket for over 30 years, delivering behavioral health, family support, and community health programs to more than 2,500 individuals annually. Our 42-person staff is majority people of color and 40% bilingual Spanish/English."},
    {"id":4,"category":"Community Need","title":"Woonsocket community overview",
     "tags":"community, need, woonsocket, poverty, demographics","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Sources: ACS 2022, RI Kids Count 2023.",
     "content":"Woonsocket is one of Rhode Island's most economically distressed cities. With a population of approximately 43,000, the city has a median household income of $40,527 — well below the state median of $70,305 — and a poverty rate of 25.9%, compared to 11.0% statewide. Youth poverty is particularly severe, with 38% of children under 18 living below the federal poverty line."},
    {"id":5,"category":"Community Need","title":"Youth mental health need",
     "tags":"youth, mental health, need, adolescent","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Sources: RI DOH, Landmark Medical Center ED data.",
     "content":"Youth in Woonsocket face an extraordinary mental health burden. Rates of adolescent depression in Providence County exceed the national average by 22%, and local school counselors report a sharp increase in crisis referrals since 2020. Despite this high level of need, only one in five youth in Woonsocket who require mental health services currently receives them."},
    {"id":6,"category":"Pilot Data & Outcomes","title":"Youth Mental Health pilot results (2022–2024)",
     "tags":"pilot, outcomes, youth, mental health, data","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Key stats: 78% PHQ-A reduction, 11 days attendance improvement.",
     "content":"In a 2022–2024 pilot serving 60 youth ages 12–18, 78% of participants showed a clinically meaningful reduction in PHQ-A depression scores after eight weeks of individual counseling. Among youth with chronic school absenteeism, attendance improved by an average of 11 days per year. 84% of caregivers who completed the family psychoeducation workshop series reported increased confidence in supporting their child's mental health."},
    {"id":7,"category":"Staff Bios","title":"Executive Director bio",
     "tags":"staff, bio, leadership, executive director","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Update if ED changes.",
     "content":"Maria Santos, LICSW, has served as Executive Director of Communicare Alliance since 2016. A licensed independent clinical social worker with 22 years of experience in community behavioral health, Ms. Santos holds an MSW from Boston University and is a founding member of the Rhode Island Coalition for Behavioral Health Equity."},
    {"id":8,"category":"Equity","title":"Equity and inclusion commitment statement",
     "tags":"equity, inclusion, diversity, DEI","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Strong for RWJF, Annie E. Casey, Blue Cross Foundation.",
     "content":"Communicare Alliance is committed to equity as an organizational value, not a program feature. This commitment is reflected in our staff composition — over 60% staff of color, 40% bilingual — our governance, and our program design, which centers community voice through a Community Advisory Group that includes current and former program participants."},
    {"id":9,"category":"Sustainability","title":"Standard sustainability statement",
     "tags":"sustainability, funding, medicaid, revenue","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Update Medicaid percentage annually.",
     "content":"Communicare Alliance pursues a diversified funding strategy that reduces dependence on any single revenue source. Medicaid reimbursement currently covers approximately 38% of program costs. State contract revenue through DCYF and BHDDH provides a stable foundation at 28% of operating revenue. We maintain six months of operating reserves in accordance with our Board-approved reserve policy."},
    {"id":10,"category":"Evaluation","title":"Standard evaluation approach",
     "tags":"evaluation, data, outcomes, methods","use_count":0,
     "created":str(datetime.date.today()),
     "notes":"Customize with program-specific instruments.",
     "content":"Communicare Alliance maintains a robust data infrastructure to track program outputs, outcomes, and equity indicators. We use validated assessment instruments including the PHQ-A, GAD-7, and COPE outcomes scale. All outcome data are disaggregated by race, ethnicity, age, gender, and income level to ensure equity gaps are visible and addressed."},
]

DEFAULT_FUNDERS = [
    {"name":"Rhode Island Foundation","url":"https://rifoundation.org/grants","geo":"Rhode Island","notes":"Largest RI community foundation","alignment_score":85,"matched_terms":"mental health, youth, community health, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Champlin Foundation","url":"https://champlinfoundations.org","geo":"Rhode Island","notes":"RI-only funder; health focus","alignment_score":80,"matched_terms":"community health, youth, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"van Beuren Charitable Foundation","url":"https://vanbeuren.org","geo":"Rhode Island","notes":"Newport-based; rural RI; health","alignment_score":75,"matched_terms":"community health, family, rhode island","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Robert Wood Johnson Foundation","url":"https://www.rwjf.org/en/grants","geo":"National","notes":"Largest US health philanthropy; equity focus","alignment_score":78,"matched_terms":"mental health, health equity, underserved, community health","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Annie E. Casey Foundation","url":"https://www.aecf.org","geo":"National","notes":"Children and families; evidence-based","alignment_score":72,"matched_terms":"youth, children, family, community health","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Blue Cross Blue Shield Foundation of MA","url":"https://bluecrossmafoundation.org","geo":"New England","notes":"Health equity; behavioral health; New England","alignment_score":82,"matched_terms":"mental health, behavioral health, health equity, new england","priority_tier":"A — Top priority","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Kresge Foundation","url":"https://kresge.org","geo":"National","notes":"Health, cities, low-income communities","alignment_score":58,"matched_terms":"community health, underserved, low income","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"W.K. Kellogg Foundation","url":"https://www.wkkf.org","geo":"National","notes":"Children, families, health equity","alignment_score":65,"matched_terms":"youth, children, family, health equity","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Conrad N. Hilton Foundation","url":"https://www.hiltonfoundation.org","geo":"National","notes":"Vulnerable populations; homelessness, children","alignment_score":48,"matched_terms":"children, family, underserved","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
    {"name":"Amica Companies Foundation","url":"https://www.amica.com/community","geo":"Rhode Island","notes":"Providence-based corporate; education and community","alignment_score":55,"matched_terms":"community health, youth, rhode island","priority_tier":"B — Strong prospect","relationship_status":"Not contacted","next_action":"Research giving page","last_contact_notes":"","grant_range_min":"","grant_range_max":"","deadline_info":"Not yet scraped","contact_info":"","scraped":"False"},
]

FUNDER_HEADERS = [
    "name","url","geo","notes","alignment_score","matched_terms",
    "priority_tier","relationship_status","next_action",
    "last_contact_notes","grant_range_min","grant_range_max",
    "deadline_info","contact_info","scraped",
]


def load_boilerplate() -> list[dict]:
    """Load blocks from OneDrive. Seeds defaults if empty."""
    try:
        rows = read_sheet("Boilerplate")
        if not rows:
            # Seed with starter blocks
            save_boilerplate(STARTER_BLOCKS)
            return STARTER_BLOCKS
        # Convert use_count to int
        for r in rows:
            try: r["use_count"] = int(r.get("use_count", 0))
            except (ValueError, TypeError): r["use_count"] = 0
            try: r["id"] = int(r.get("id", 0))
            except (ValueError, TypeError): r["id"] = 0
        return rows
    except Exception as e:
        st.warning(f"OneDrive read failed — using local session data. ({e})")
        return STARTER_BLOCKS


def save_boilerplate(blocks: list[dict]):
    """Save all blocks to OneDrive."""
    try:
        rows = [
            [
                b.get("id",""), b.get("category",""), b.get("title",""),
                b.get("tags",""), b.get("content",""), b.get("notes",""),
                b.get("use_count",0), b.get("created",str(datetime.date.today())),
            ]
            for b in blocks
        ]
        write_sheet("Boilerplate", BOILERPLATE_HEADERS, rows)
        return True
    except Exception as e:
        st.warning(f"OneDrive save failed. ({e})")
        return False


def load_funders() -> list[dict]:
    """Load funders from OneDrive. Seeds defaults if empty."""
    try:
        rows = read_sheet("Funders")
        if not rows:
            save_funders(DEFAULT_FUNDERS)
            return DEFAULT_FUNDERS
        for r in rows:
            try: r["alignment_score"] = int(r.get("alignment_score", 0))
            except (ValueError, TypeError): r["alignment_score"] = 0
        return rows
    except Exception as e:
        st.warning(f"OneDrive read failed — using local session data. ({e})")
        return DEFAULT_FUNDERS


def save_funders(funders: list[dict]):
    """Save all funders to OneDrive."""
    try:
        rows = [[f.get(h, "") for h in FUNDER_HEADERS] for f in funders]
        write_sheet("Funders", FUNDER_HEADERS, rows)
        return True
    except Exception as e:
        st.warning(f"OneDrive save failed. ({e})")
        return False
