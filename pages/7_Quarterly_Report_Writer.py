"""
Quarterly Funder Report Generator — Communicare Alliance
=========================================================
Takes your program data and uses Claude to write a complete
formatted progress report — ready to send to a funder.

Install:  pip install anthropic pandas openpyxl python-docx
Run:      python quarterly_report_generator.py

Outputs:
  quarterly_report_Q[N]_[YEAR].docx  — Word document, send directly
  quarterly_report_Q[N]_[YEAR].html  — browser version for sharing

Set your API key first:
  set ANTHROPIC_API_KEY=sk-ant-your-key-here
"""

import anthropic
import os
import sys
import json
import re
import datetime
import subprocess
import tempfile

# ─────────────────────────────────────────────────────────────────────────────
# ✏️  GRANT DETAILS — edit once per grant, reuse every quarter
# ─────────────────────────────────────────────────────────────────────────────

GRANT = {
    "org_name":         "Communicare Alliance",
    "org_location":     "Woonsocket, RI",
    "program_name":     "Youth Mental Health & Resilience Program",
    "funder_name":      "Rhode Island Foundation",
    "funder_contact":   "Sarah Chen, Program Officer",
    "grant_number":     "RIF-2025-0847",
    "grant_period":     "January 1, 2025 – December 31, 2026",
    "grant_amount":     185000,
    "report_author":    "Program Development & Grants Manager",
    "report_quarter":   2,       # ✏️ change each quarter: 1, 2, 3, or 4
    "report_year":      2025,    # ✏️ change each year

    # Budget tracking
    "total_budget":     185000,
    "budget_year":      1,       # which year of grant (1 or 2)

    # Approved objectives — what you promised in the grant application
    "approved_objectives": [
        {
            "number": 1,
            "description": "Enroll and serve 75 unduplicated youth ages 12–18 in individual counseling in Year 1",
            "annual_target": 75,
            "unit": "youth",
        },
        {
            "number": 2,
            "description": "Deliver 600 individual counseling sessions in Year 1",
            "annual_target": 600,
            "unit": "sessions",
        },
        {
            "number": 3,
            "description": "75% of discharged youth will show clinically meaningful PHQ-A reduction (≥5 points)",
            "annual_target": 75,
            "unit": "percent",
        },
        {
            "number": 4,
            "description": "Run 4 resilience group cohorts of 10 youth each in Year 1",
            "annual_target": 4,
            "unit": "cohorts",
        },
        {
            "number": 5,
            "description": "Conduct 6 family psychoeducation workshops with ≥70% caregiver satisfaction",
            "annual_target": 6,
            "unit": "workshops",
        },
        {
            "number": 6,
            "description": "Train 30 school staff in trauma-informed practices",
            "annual_target": 30,
            "unit": "staff trained",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# ✏️  QUARTERLY DATA — update these numbers each quarter
# ─────────────────────────────────────────────────────────────────────────────

# To load from your tracking spreadsheet instead of editing here:
#   import pandas as pd
#   df = pd.read_excel("your_tracking_file.xlsx")
#   Then replace the values below with df lookups

QUARTERLY_DATA = {

    # ── Service delivery ──────────────────────────────────────────────────────
    "youth_enrolled_this_quarter":    14,
    "youth_enrolled_ytd":             28,    # year-to-date total
    "sessions_delivered_this_quarter": 156,
    "sessions_delivered_ytd":          312,
    "avg_sessions_per_youth":          11.1,
    "attendance_rate_pct":             83.2,  # % of scheduled sessions attended

    # ── Clinical outcomes (PHQ-A) ─────────────────────────────────────────────
    "youth_discharged_this_quarter":   8,
    "youth_discharged_ytd":            14,
    "pct_meaningful_phq_improvement":  78.6,  # % with ≥5 point PHQ-A drop
    "avg_phq_intake":                  15.4,
    "avg_phq_discharge":               8.2,
    "avg_phq_drop":                    7.2,
    "youth_still_enrolled":            14,

    # ── Groups & workshops ────────────────────────────────────────────────────
    "group_cohorts_completed":         1,
    "group_participants_total":        10,
    "pct_cope_improvement":            82.0,  # % with ≥4 point COPE scale increase
    "workshops_held":                  2,
    "workshop_attendees":              41,
    "pct_workshop_satisfaction":       88.3,  # % rating 4/5 or higher

    # ── School staff training ─────────────────────────────────────────────────
    "staff_trained_this_quarter":      18,
    "staff_trained_ytd":               18,
    "pct_staff_confidence_increase":   84.4,

    # ── Demographics ─────────────────────────────────────────────────────────
    "pct_latino":                      61.4,
    "pct_black":                       21.4,
    "pct_poc_total":                   89.3,
    "pct_female":                      57.1,
    "avg_age":                         14.2,
    "pct_free_reduced_lunch":          82.1,  # proxy for low income

    # ── Budget ───────────────────────────────────────────────────────────────
    "budget_spent_ytd":                72400,   # actual dollars spent year to date
    "budget_expected_ytd":             74500,   # what you should have spent by now
    "budget_line_items": [
        {"category": "Personnel — LCSW #1",       "budgeted": 68000,  "spent_ytd": 34000},
        {"category": "Personnel — LCSW #2",       "budgeted": 65000,  "spent_ytd": 32500},
        {"category": "Personnel — Health Educator","budgeted": 48000,  "spent_ytd": 24000},
        {"category": "Personnel — Coordinator",   "budgeted": 42000,  "spent_ytd": 20800},
        {"category": "Director supervision (15%)", "budgeted": 12750,  "spent_ytd":  6375},
        {"category": "Fringe (28%)",               "budgeted": 66010,  "spent_ytd": 32400},
        {"category": "Supplies & materials",       "budgeted":  3200,  "spent_ytd":  1840},
        {"category": "Training & prof. dev.",      "budgeted":  3000,  "spent_ytd":   980},
        {"category": "Technology (EHR)",           "budgeted":  3000,  "spent_ytd":  1500},
        {"category": "Indirect (8%)",              "budgeted": 14800,  "spent_ytd":  7400},
        {"category": "Evaluation (Year 2 only)",   "budgeted":  8000,  "spent_ytd":     0},
    ],

    # ── Narrative highlights ──────────────────────────────────────────────────
    # Add 2-4 bullet points of things worth highlighting this quarter.
    # Claude will weave these into the narrative sections.
    "highlights": [
        "Completed our first resilience group cohort at Woonsocket High School with 10 participants; 82% showed meaningful improvement on COPE outcomes scale",
        "Hired and onboarded bilingual LCSW #2 in April — both clinical positions now fully staffed",
        "Delivered trauma-informed practices training to 18 Hamlet Middle School staff; 84% reported increased confidence in supporting students showing signs of distress",
        "Two participating youth who had been chronically absent in Q1 returned to regular attendance after initiating counseling services",
    ],

    # ── Challenges ────────────────────────────────────────────────────────────
    # Be honest — funders respect transparency. Claude will frame these constructively.
    "challenges": [
        "Family workshop attendance lower than projected (41 vs. 50 target) due to scheduling conflicts with end-of-school-year events; adjusting to Saturday morning format in Q3",
        "EHR configuration for COPE scale data entry took longer than anticipated; now resolved and all group data being captured as of May",
    ],

    # ── Next quarter plan ─────────────────────────────────────────────────────
    "next_quarter_plans": [
        "Launch two additional resilience group cohorts at Villa Nova MS and Hamlet MS (20 more youth)",
        "Host 2 family psychoeducation workshops in Saturday morning format",
        "Begin recruitment for peer mentor cohort (target: 15 mentors)",
        "Conduct mid-year data quality review with program staff",
        "Schedule site visit with Rhode Island Foundation program officer",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Quarter label helpers
# ─────────────────────────────────────────────────────────────────────────────

QUARTER_MONTHS = {
    1: ("January", "March"),
    2: ("April",   "June"),
    3: ("July",    "September"),
    4: ("October", "December"),
}

def quarter_label(q, year):
    start, end = QUARTER_MONTHS[q]
    return f"Q{q} {year} ({start} – {end} {year})"

def ytd_label(q, year):
    _, end = QUARTER_MONTHS[q]
    return f"January – {end} {year}"

# ─────────────────────────────────────────────────────────────────────────────
# Objective progress calculator
# ─────────────────────────────────────────────────────────────────────────────

def calc_objective_progress(grant, data):
    q   = grant["report_quarter"]
    qtr_fraction = q / 4  # expected proportion of year complete

    results = []
    for obj in grant["approved_objectives"]:
        n = obj["number"]
        target = obj["annual_target"]

        # Map objective number to relevant data field
        if n == 1:
            actual = data["youth_enrolled_ytd"]
        elif n == 2:
            actual = data["sessions_delivered_ytd"]
        elif n == 3:
            actual = data["pct_meaningful_phq_improvement"]
            target = 75  # percentage target
        elif n == 4:
            actual = data["group_cohorts_completed"]
        elif n == 5:
            actual = data["workshops_held"]
        elif n == 6:
            actual = data["staff_trained_ytd"]
        else:
            actual = 0

        expected_ytd = round(target * qtr_fraction)
        if obj["unit"] == "percent":
            pct_complete = actual  # it IS a percentage
            on_track = actual >= target - 5  # within 5pp
        else:
            pct_complete = round(actual / target * 100) if target > 0 else 0
            on_track = actual >= expected_ytd * 0.85  # within 15% of expected

        results.append({
            "number":       n,
            "description":  obj["description"],
            "annual_target": target,
            "unit":         obj["unit"],
            "actual_ytd":   actual,
            "expected_ytd": expected_ytd,
            "pct_complete": pct_complete,
            "on_track":     on_track,
            "status":       "On track" if on_track else "Needs attention",
        })
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Budget summary
# ─────────────────────────────────────────────────────────────────────────────

def calc_budget(grant, data):
    total = grant["total_budget"]
    spent = data["budget_spent_ytd"]
    expected = data["budget_expected_ytd"]
    pct_spent = round(spent / total * 100, 1)
    pct_expected = round(expected / total * 100, 1)
    variance = spent - expected
    return {
        "total":        total,
        "spent_ytd":    spent,
        "expected_ytd": expected,
        "remaining":    total - spent,
        "pct_spent":    pct_spent,
        "pct_expected": pct_expected,
        "variance":     variance,
        "on_track":     abs(variance) / total < 0.10,  # within 10%
        "line_items":   data["budget_line_items"],
    }

# ─────────────────────────────────────────────────────────────────────────────
# Claude narrative generation
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM = """You are an expert grant writer for a nonprofit organization.
You write clear, professional, data-driven progress reports for foundation funders.
Your tone is warm but precise — you lead with numbers, explain context,
and are honest about challenges while showing how they are being addressed.
Write in connected prose paragraphs. No bullet points. No markdown.
No section headings — those will be added separately."""


def generate_section(client, prompt):
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def build_narrative(client, grant, data, objectives, budget):
    q    = grant["report_quarter"]
    year = grant["report_year"]
    ql   = quarter_label(q, year)
    ytd  = ytd_label(q, year)
    prog = grant["program_name"]
    org  = grant["org_name"]
    funder = grant["funder_name"]

    obj_summary = "\n".join(
        f"Objective {o['number']}: {o['description']} — "
        f"Target: {o['annual_target']} {o['unit']} | "
        f"YTD actual: {o['actual_ytd']} | "
        f"Status: {o['status']}"
        for o in objectives
    )

    highlights = "\n".join(f"- {h}" for h in data["highlights"])
    challenges = "\n".join(f"- {c}" for c in data["challenges"])
    next_q     = "\n".join(f"- {n}" for n in data["next_quarter_plans"])

    base = (
        f"Organization: {org}, Woonsocket RI. "
        f"Program: {prog}. Funder: {funder}. "
        f"Reporting period: {ql}. Grant period: {grant['grant_period']}."
    )

    sections = {}

    # Executive summary
    print("    Executive summary...")
    sections["executive_summary"] = generate_section(client, f"""{base}

Write a brief executive summary (120–150 words) for a quarterly progress report.
Include: program is on track, key headline numbers, one or two standout results.
Start with something like 'Communicare Alliance is pleased to report...'

Key data:
- Youth served YTD: {data['youth_enrolled_ytd']} (target: {grant['approved_objectives'][0]['annual_target']} for year)
- Sessions delivered YTD: {data['sessions_delivered_ytd']}
- PHQ-A meaningful improvement: {data['pct_meaningful_phq_improvement']}% of discharged youth
- School staff trained: {data['staff_trained_ytd']}
- Budget on track: {'yes' if budget['on_track'] else 'slightly behind — see budget section'}""")

    # Program activities
    print("    Program activities...")
    sections["program_activities"] = generate_section(client, f"""{base}

Write a Program Activities narrative (200–250 words) describing what happened this quarter.
Weave in these specific data points and highlights. Write in past tense.

Service delivery this quarter:
- Youth newly enrolled: {data['youth_enrolled_this_quarter']}
- Total youth enrolled YTD: {data['youth_enrolled_ytd']}
- Sessions delivered this quarter: {data['sessions_delivered_this_quarter']}
- Attendance rate: {data['attendance_rate_pct']}%
- Groups completed: {data['group_cohorts_completed']} cohort ({data['group_participants_total']} youth)
- Workshops held: {data['workshops_held']} ({data['workshop_attendees']} caregivers)
- Staff trained: {data['staff_trained_this_quarter']}

Highlights to weave in:
{highlights}""")

    # Outcomes
    print("    Outcomes section...")
    sections["outcomes"] = generate_section(client, f"""{base}

Write a Participant Outcomes narrative (200–250 words).
Emphasize the clinical significance of the results. Be specific about the numbers.

Clinical outcomes:
- Youth discharged this quarter: {data['youth_discharged_this_quarter']} ({data['youth_discharged_ytd']} YTD)
- Meaningful PHQ-A improvement (≥5 points): {data['pct_meaningful_phq_improvement']}% (target: 75%)
- Average PHQ-A at intake: {data['avg_phq_intake']} (moderate-severe range)
- Average PHQ-A at discharge: {data['avg_phq_discharge']} (mild range)
- Average score reduction: {data['avg_phq_drop']} points
- COPE scale improvement in group: {data['pct_cope_improvement']}%
- Workshop caregiver satisfaction: {data['pct_workshop_satisfaction']}%
- Youth still actively enrolled: {data['youth_still_enrolled']}

Demographics (emphasize equity):
- Participants of color: {data['pct_poc_total']}% ({data['pct_latino']}% Latino, {data['pct_black']}% Black)
- Free/reduced lunch eligible: {data['pct_free_reduced_lunch']}%""")

    # Objectives progress
    print("    Objectives progress...")
    sections["objectives_progress"] = generate_section(client, f"""{base}

Write an Objectives Progress narrative (150–200 words) summarizing progress against
grant objectives. Be specific about which are on track and which need attention.
Frame any off-track objectives with context and the plan to address them.

Objective status:
{obj_summary}

Budget status:
- Total grant: ${budget['total']:,}
- Spent YTD: ${budget['spent_ytd']:,} ({budget['pct_spent']}%)
- Expected to have spent: ${budget['expected_ytd']:,} ({budget['pct_expected']}%)
- Status: {'On track' if budget['on_track'] else 'Slightly behind — explain and project on track by year end'}""")

    # Challenges
    print("    Challenges and adaptations...")
    sections["challenges"] = generate_section(client, f"""{base}

Write a Challenges and Adaptations narrative (120–160 words).
Present challenges honestly but frame them as learning opportunities.
Show that the team identified issues and is responding proactively.

Challenges this quarter:
{challenges}

Key message: the program is healthy overall; these are normal implementation
issues being addressed with intentional course corrections.""")

    # Next quarter
    print("    Next quarter plans...")
    sections["next_quarter"] = generate_section(client, f"""{base}

Write a Looking Ahead narrative (120–150 words) about Q{q+1 if q < 4 else 1} {year if q < 4 else year+1} plans.
Be specific and connect plans back to annual targets.

Planned activities:
{next_q}

Frame with: we are on track to meet annual targets, the team is energized,
strong momentum from Q{q}.""")

    return sections

# ─────────────────────────────────────────────────────────────────────────────
# Word document via docx-js
# ─────────────────────────────────────────────────────────────────────────────

def build_docx(grant, data, objectives, budget, sections, output_path):
    q    = grant["report_quarter"]
    year = grant["report_year"]
    today = datetime.date.today().strftime("%B %d, %Y")
    ql   = quarter_label(q, year)

    payload = {
        "grant":      grant,
        "data":       {k: v for k, v in data.items()
                       if not isinstance(v, list) or k == "budget_line_items"},
        "objectives": objectives,
        "budget":     {k: v for k, v in budget.items() if k != "line_items"},
        "line_items": budget["line_items"],
        "sections":   sections,
        "quarter_label": ql,
        "ytd_label":  ytd_label(q, year),
        "today":      today,
        "output_path": output_path,
    }

    js = r"""
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType, LevelFormat,
        PageNumber, PageBreak } = require('docx');
const fs = require('fs');
const D = """ + json.dumps(payload, ensure_ascii=False) + r""";
const OUT = D.output_path;

const T = "#1A6E6E", TP = "#E1F5EE", TM = "#9FE1CB";
const W = "#FFFFFF", GL = "#F5F5F5", GM = "#D1D5DB", DK = "#1F2937";
const GN = "#065F46", GNL = "#D1FAE5", AM = "#92400E", AML = "#FEF3C7";
const RD = "#C0392B", RDL = "#FDECEA";

const bdr = (c=GM) => ({ style: BorderStyle.SINGLE, size: 4, color: c.replace('#','') });
const bdrs = c => ({ top:bdr(c),bottom:bdr(c),left:bdr(c),right:bdr(c) });
const shd = h => ({ fill: h.replace('#',''), type: ShadingType.CLEAR });
const mg = (t=80,b=80,l=120,r=120) => ({ top:t,bottom:b,left:l,right:r });

function tr(text, opts={}) {
  return new TextRun({
    text, font:"Arial",
    size: opts.size||20,
    bold: opts.bold||false,
    color: (opts.color||DK).replace('#',''),
    italics: opts.italic||false,
  });
}

function p(text_or_runs, opts={}) {
  const runs = Array.isArray(text_or_runs)
    ? text_or_runs
    : [tr(text_or_runs, opts)];
  return new Paragraph({
    children: runs,
    spacing: { before: opts.before||80, after: opts.after||80 },
    alignment: opts.align || AlignmentType.LEFT,
  });
}

function divider(color="#9FE1CB") {
  return new Paragraph({
    spacing:{before:120,after:0},
    border:{bottom:{style:BorderStyle.SINGLE,size:6,
                    color:color.replace('#',''),space:1}},
    children:[],
  });
}

function sectionHead(num, title) {
  return new Paragraph({
    spacing:{before:240,after:80},
    children:[
      tr(num+" ", {bold:true,size:22,color:TM}),
      tr(title, {bold:true,size:22,color:T}),
    ],
  });
}

function prose(text) {
  const paras = text.split(/\n\n+/).filter(Boolean);
  return paras.map(para => p(para.replace(/\n/g,' '), {size:20,before:0,after:120}));
}

// KPI card row
function kpiTable(items) {
  const w = Math.floor(9360 / items.length);
  const cols = Array(items.length).fill(w);
  // fix rounding
  cols[cols.length-1] = 9360 - w*(items.length-1);
  return new Table({
    width:{size:9360,type:WidthType.DXA},
    columnWidths:cols,
    rows:[new TableRow({children:items.map((item,i) => new TableCell({
      borders:bdrs(item.border||TM),
      width:{size:cols[i],type:WidthType.DXA},
      shading:shd(item.bg||TP),
      margins:mg(120,120,120,120),
      children:[
        new Paragraph({spacing:{before:0,after:20},alignment:AlignmentType.CENTER,
          children:[tr(item.value,{bold:true,size:32,color:item.vc||T})]}),
        new Paragraph({spacing:{before:0,after:0},alignment:AlignmentType.CENTER,
          children:[tr(item.label,{size:16,color:item.lc||"666666"})]}),
      ],
    }))})]
  });
}

// Objectives table
function objectivesTable(objectives) {
  const colW = [400,3400,1000,1000,1000,1160];
  const total = colW.reduce((a,b)=>a+b,0);
  const rows = [
    new TableRow({tableHeader:true, children:[
      "#","Objective","Annual Target","YTD Actual","Expected YTD","Status"
    ].map((h,i) => new TableCell({
      borders:bdrs(T),
      width:{size:colW[i],type:WidthType.DXA},
      shading:shd(T),
      margins:mg(80,80,100,80),
      children:[p(h,{bold:true,size:17,color:W,align:AlignmentType.CENTER})],
    }))}),
    ...objectives.map((obj,i) => {
      const alt = i%2===0 ? GL : W;
      const [bg,tc] = obj.on_track ? [GNL,GN] : [AML,AM];
      return new TableRow({children:[
        new TableCell({borders:bdrs(GM),width:{size:colW[0],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(String(obj.number),{bold:true,color:T,align:AlignmentType.CENTER,size:18})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[1],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(obj.description,{size:17,color:DK})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[2],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(String(obj.annual_target)+" "+obj.unit,{size:17,align:AlignmentType.CENTER})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[3],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(String(obj.actual_ytd),{size:18,bold:true,color:obj.on_track?GN:RD,align:AlignmentType.CENTER})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[4],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(String(obj.expected_ytd),{size:17,color:"888888",align:AlignmentType.CENTER})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[5],type:WidthType.DXA},shading:shd(bg),margins:mg(),
          children:[p(obj.status,{size:16,bold:true,color:tc,align:AlignmentType.CENTER})]}),
      ]});
    }),
  ];
  return new Table({width:{size:total,type:WidthType.DXA},columnWidths:colW,rows});
}

// Budget table
function budgetTable(items, total, spent, expected) {
  const colW = [3600,1920,1920,1920];
  const tw = colW.reduce((a,b)=>a+b,0);
  const FMT = v => "$"+Math.round(v).toLocaleString();
  const pct = (a,b) => b>0 ? Math.round(a/b*100)+"%" : "0%";

  const rows = [
    new TableRow({tableHeader:true,children:[
      "Line Item","Annual Budget","Spent YTD","% Used"
    ].map((h,i)=>new TableCell({
      borders:bdrs(T),width:{size:colW[i],type:WidthType.DXA},
      shading:shd(T),margins:mg(80,80,100,80),
      children:[p(h,{bold:true,size:17,color:W,
        align:i>0?AlignmentType.CENTER:AlignmentType.LEFT})],
    }))}),
    ...items.map((li,i) => {
      const alt = i%2===0 ? GL : W;
      const pctN = li.budgeted>0 ? li.spent_ytd/li.budgeted*100 : 0;
      const pctColor = pctN>90 ? RD : (pctN>60 ? DK : DK);
      return new TableRow({children:[
        new TableCell({borders:bdrs(GM),width:{size:colW[0],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(li.category,{size:17})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[1],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(FMT(li.budgeted),{size:17,align:AlignmentType.RIGHT})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[2],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(FMT(li.spent_ytd),{size:17,align:AlignmentType.RIGHT})]}),
        new TableCell({borders:bdrs(GM),width:{size:colW[3],type:WidthType.DXA},shading:shd(alt),margins:mg(),
          children:[p(pct(li.spent_ytd,li.budgeted),{size:17,bold:pctN>85,color:pctColor,
            align:AlignmentType.CENTER})]}),
      ]});
    }),
    // Total row
    new TableRow({children:[
      new TableCell({borders:bdrs(T),width:{size:colW[0],type:WidthType.DXA},shading:shd(T),margins:mg(),
        children:[p("TOTAL GRANT",{bold:true,size:18,color:W})]}),
      new TableCell({borders:bdrs(T),width:{size:colW[1],type:WidthType.DXA},shading:shd(T),margins:mg(),
        children:[p(FMT(total),{bold:true,size:18,color:W,align:AlignmentType.RIGHT})]}),
      new TableCell({borders:bdrs(T),width:{size:colW[2],type:WidthType.DXA},shading:shd(T),margins:mg(),
        children:[p(FMT(spent),{bold:true,size:18,color:W,align:AlignmentType.RIGHT})]}),
      new TableCell({borders:bdrs(T),width:{size:colW[3],type:WidthType.DXA},shading:shd(T),margins:mg(),
        children:[p(pct(spent,total),{bold:true,size:18,color:W,align:AlignmentType.CENTER})]}),
    ]})
  ];
  return new Table({width:{size:tw,type:WidthType.DXA},columnWidths:colW,rows});
}

// ── Build document ─────────────────────────────────────────────────────────

const g = D.grant, qd = D.data, sec = D.sections;
const obj = D.objectives, bgt = D.budget, li = D.line_items;

const FMT = v => "$"+Math.round(v).toLocaleString();

const children = [

  // Header
  p([tr(g.program_name,{bold:true,size:40,color:T})],{before:0,after:60}),
  p([tr("Quarterly Progress Report  \u2014  ",{size:22,color:"888888"}),
     tr(D.quarter_label,{size:22,bold:true,color:T})],{before:0,after:40}),
  p([
    tr(g.org_name,{size:18,color:"888888"}),
    tr("  \u00b7  Submitted to: ",{size:18,color:"AAAAAA"}),
    tr(g.funder_name,{size:18,color:"888888"}),
    tr("  \u00b7  Grant #: "+g.grant_number,{size:18,color:"AAAAAA"}),
  ],{before:0,after:40}),
  p([tr("Prepared by: "+g.report_author+"  \u00b7  "+D.today,
        {size:16,color:"AAAAAA",italic:true})],{before:0,after:0}),
  divider(),
  p(""),

  // KPI strip
  kpiTable([
    {label:"Youth served YTD",    value:String(qd.youth_enrolled_ytd),   bg:TP,  vc:T,  lc:"0F6E56"},
    {label:"Sessions YTD",        value:String(qd.sessions_delivered_ytd),bg:TP, vc:T,  lc:"0F6E56"},
    {label:"PHQ-A improvement",   value:qd.pct_meaningful_phq_improvement+"%", bg:"D1FAE5",vc:GN,lc:"065F46"},
    {label:"Attendance rate",     value:qd.attendance_rate_pct+"%",      bg:TP,  vc:T,  lc:"0F6E56"},
    {label:"Budget utilized",     value:bgt.pct_spent+"%",               bg:TP,  vc:T,  lc:"0F6E56"},
  ]),
  p(""),

  // 1. Executive Summary
  sectionHead("1.", "Executive Summary"),
  ...prose(sec.executive_summary),
  divider(),

  // 2. Program Activities
  sectionHead("2.", "Program Activities — "+D.quarter_label),
  ...prose(sec.program_activities),
  divider(),

  // 3. Participant Outcomes
  sectionHead("3.", "Participant Outcomes"),
  ...prose(sec.outcomes),

  // Outcomes mini-table
  p(""),
  new Table({
    width:{size:9360,type:WidthType.DXA},columnWidths:[3600,2880,2880],
    rows:[
      new TableRow({children:[
        "Clinical Measure","Woonsocket (This Grant)","Target"
      ].map((h,i)=>new TableCell({
        borders:bdrs(T),width:{size:[3600,2880,2880][i],type:WidthType.DXA},
        shading:shd(T),margins:mg(80,80,120,80),
        children:[p(h,{bold:true,size:17,color:W,align:i>0?AlignmentType.CENTER:AlignmentType.LEFT})],
      }))}),
      ...[
        ["PHQ-A meaningful improvement (≥5pts)", qd.pct_meaningful_phq_improvement+"%", "75%"],
        ["Average PHQ-A reduction", qd.avg_phq_drop+" points", "5+ points"],
        ["COPE scale improvement (groups)", qd.pct_cope_improvement+"%", "80%"],
        ["Caregiver workshop satisfaction", qd.pct_workshop_satisfaction+"%", "70%"],
        ["Session attendance rate", qd.attendance_rate_pct+"%", "80%"],
      ].map(([measure,val,target],i)=>new TableRow({children:[
        new TableCell({borders:bdrs(GM),width:{size:3600,type:WidthType.DXA},shading:shd(i%2===0?GL:W),margins:mg(),children:[p(measure,{size:17})]}),
        new TableCell({borders:bdrs(GM),width:{size:2880,type:WidthType.DXA},shading:shd(i%2===0?GL:W),margins:mg(),children:[p(val,{size:18,bold:true,color:GN,align:AlignmentType.CENTER})]}),
        new TableCell({borders:bdrs(GM),width:{size:2880,type:WidthType.DXA},shading:shd(i%2===0?GL:W),margins:mg(),children:[p(target,{size:17,color:"888888",align:AlignmentType.CENTER})]}),
      ]})),
    ],
  }),
  p(""),
  divider(),

  // 4. Objectives Progress
  sectionHead("4.", "Objectives Progress — Year to Date"),
  ...prose(sec.objectives_progress),
  p(""),
  objectivesTable(obj),
  p(""),
  divider(),

  // 5. Budget
  sectionHead("5.", "Budget Update"),
  p([
    tr("Total grant: ",{bold:true,size:20,color:T}),
    tr(FMT(bgt.total)+"  \u00b7  ",{size:20}),
    tr("Spent YTD: ",{bold:true,size:20,color:T}),
    tr(FMT(bgt.spent_ytd)+" ("+bgt.pct_spent+"%)  \u00b7  ",{size:20}),
    tr("Remaining: ",{bold:true,size:20,color:T}),
    tr(FMT(bgt.remaining),{size:20}),
  ],{before:0,after:120}),
  budgetTable(li, bgt.total, bgt.spent_ytd, bgt.expected_ytd),
  p(""),
  divider(),

  // 6. Challenges
  sectionHead("6.", "Challenges and Adaptations"),
  ...prose(sec.challenges),
  divider(),

  // 7. Looking Ahead
  sectionHead("7.", "Looking Ahead — Next Quarter"),
  ...prose(sec.next_quarter),
  divider(),

  // Signature block
  p(""),
  p([tr("Submitted by: ",{bold:true,size:20,color:T}),
     tr(g.report_author,{size:20})],{before:0,after:60}),
  p([tr(g.org_name+"  \u00b7  "+g.org_location,{size:18,color:"888888"})],{before:0,after:40}),
  p([tr("Grant: "+g.grant_number+"  \u00b7  "+g.funder_name,{size:16,color:"AAAAAA",italic:true})],{before:0,after:0}),
];

const doc = new Document({
  styles:{default:{document:{run:{font:"Arial",size:20}}}},
  numbering:{config:[
    {reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"\u2022",
      alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]},
  ]},
  sections:[{
    properties:{page:{
      size:{width:12240,height:15840},
      margin:{top:1080,right:1080,bottom:1080,left:1080}
    }},
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log("saved:"+OUT);
});
"""

    js_path = output_path.replace(".docx", "_build.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js)
    result = subprocess.run(["node", js_path, output_path],
                            capture_output=True, text=True, timeout=30)
    os.unlink(js_path)
    if result.returncode != 0:
        raise RuntimeError(f"Node error: {result.stderr[:400]}")
    print(f"  Saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# HTML version
# ─────────────────────────────────────────────────────────────────────────────

def build_html(grant, data, objectives, budget, sections, output_path):
    q    = grant["report_quarter"]
    year = grant["report_year"]
    today = datetime.date.today().strftime("%B %d, %Y")
    ql   = quarter_label(q, year)

    def prose_html(text):
        return "".join(
            f'<p style="font-size:13px;line-height:1.7;color:#1F2937;margin:0 0 10px">{p.strip()}</p>'
            for p in text.split("\n\n") if p.strip()
        )

    def section(title, content):
        return f"""<div style="margin-bottom:28px">
          <h2 style="font-size:15px;font-weight:600;color:#1A6E6E;margin:0 0 10px;
                     padding-bottom:6px;border-bottom:2px solid #E1F5EE">{title}</h2>
          {content}</div>"""

    # KPI bar
    kpis = [
        ("Youth served YTD",     str(data["youth_enrolled_ytd"]),     "#E1F5EE","#0F6E56"),
        ("Sessions YTD",         str(data["sessions_delivered_ytd"]), "#E1F5EE","#0F6E56"),
        ("PHQ-A improvement",    f"{data['pct_meaningful_phq_improvement']}%", "#D1FAE5","#065F46"),
        ("Attendance rate",      f"{data['attendance_rate_pct']}%",   "#E1F5EE","#0F6E56"),
        ("Budget utilized",      f"{budget['pct_spent']}%",          "#E1F5EE","#0F6E56"),
    ]
    kpi_html = "".join(
        f'<div style="background:{bg};border-radius:8px;padding:12px;text-align:center;flex:1">'
        f'<div style="font-size:24px;font-weight:700;color:{col}">{val}</div>'
        f'<div style="font-size:11px;color:#6B7280;margin-top:3px">{lbl}</div></div>'
        for lbl, val, bg, col in kpis
    )

    # Objectives table
    obj_rows = ""
    for o in objectives:
        bg, tc = ("#D1FAE5","#065F46") if o["on_track"] else ("#FEF3C7","#92400E")
        obj_rows += f"""<tr style="background:{'#F9FAFB' if objectives.index(o)%2==0 else '#fff'}">
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-weight:600;color:#1A6E6E;text-align:center">{o['number']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">{o['description']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-size:13px">{o['annual_target']} {o['unit']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-weight:700;font-size:14px;color:{'#065F46' if o['on_track'] else '#C0392B'}">{o['actual_ytd']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-size:12px;color:#888">{o['expected_ytd']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;background:{bg};color:{tc};font-weight:600;font-size:12px">{o['status']}</td>
        </tr>"""

    # Budget table
    bgt_rows = ""
    for i, li in enumerate(budget["line_items"]):
        pct = round(li["spent_ytd"] / li["budgeted"] * 100) if li["budgeted"] > 0 else 0
        bgt_rows += f"""<tr style="background:{'#F9FAFB' if i%2==0 else '#fff'}">
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">{li['category']}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:right;font-size:13px">${li['budgeted']:,}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:right;font-size:13px">${li['spent_ytd']:,}</td>
          <td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-size:13px;color:{'#C0392B' if pct>90 else '#1F2937'}">{pct}%</td>
        </tr>"""

    th = 'style="background:#1A6E6E;color:white;padding:9px 10px;text-align:left;font-size:12px;border:0.5px solid #0F6E56"'
    thc = 'style="background:#1A6E6E;color:white;padding:9px 10px;text-align:center;font-size:12px;border:0.5px solid #0F6E56"'

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quarterly Report — {grant['program_name']}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#F8FAFB;color:#1F2937}}
.page{{max-width:960px;margin:0 auto;padding:28px 24px}}
table{{width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;
       background:white;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:10px}}
.footer{{margin-top:24px;text-align:center;font-size:11px;color:#9CA3AF;
         padding-top:12px;border-top:1px solid #E5E7EB}}
@media print{{body{{background:white}}}}
</style></head>
<body><div class="page">

<div style="background:#1A6E6E;border-radius:10px;padding:22px 26px;margin-bottom:22px">
  <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">{grant['program_name']}</div>
  <div style="font-size:15px;color:#9FE1CB;margin-bottom:4px">Quarterly Progress Report — {ql}</div>
  <div style="font-size:12px;color:#9FE1CB">{grant['org_name']} &middot; Submitted to: {grant['funder_name']} &middot; Grant #: {grant['grant_number']} &middot; {today}</div>
</div>

<div style="display:flex;gap:10px;margin-bottom:22px">{kpi_html}</div>

{section("1. Executive Summary", prose_html(sections['executive_summary']))}
{section("2. Program Activities — " + ql, prose_html(sections['program_activities']))}
{section("3. Participant Outcomes", prose_html(sections['outcomes']) + f"""
<table>
  <thead><tr><th {th}>Clinical Measure</th><th {thc}>Result</th><th {thc}>Target</th></tr></thead>
  <tbody>
    <tr style="background:#F9FAFB"><td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">PHQ-A meaningful improvement (&ge;5 points)</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-weight:700;color:#065F46">{data['pct_meaningful_phq_improvement']}%</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;color:#888">75%</td></tr>
    <tr><td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">Average PHQ-A score reduction</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-weight:700;color:#065F46">{data['avg_phq_drop']} pts</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;color:#888">≥5 pts</td></tr>
    <tr style="background:#F9FAFB"><td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">COPE scale improvement (groups)</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-weight:700;color:#065F46">{data['pct_cope_improvement']}%</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;color:#888">80%</td></tr>
    <tr><td style="padding:8px 10px;border:0.5px solid #E5E7EB;font-size:13px">Session attendance rate</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;font-weight:700;color:#065F46">{data['attendance_rate_pct']}%</td><td style="padding:8px 10px;border:0.5px solid #E5E7EB;text-align:center;color:#888">80%</td></tr>
  </tbody>
</table>""")}
{section("4. Objectives Progress", prose_html(sections['objectives_progress']) + f"""
<table>
  <thead><tr>
    <th {thc} style="width:40px">#</th>
    <th {th}>Objective</th>
    <th {thc}>Annual Target</th>
    <th {thc}>YTD Actual</th>
    <th {thc}>Expected YTD</th>
    <th {thc}>Status</th>
  </tr></thead>
  <tbody>{obj_rows}</tbody>
</table>""")}
{section("5. Budget Update", f"""
<div style="display:flex;gap:10px;margin-bottom:12px">
  <div style="background:#E1F5EE;border-radius:8px;padding:10px 16px;flex:1;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#1A6E6E">${budget['total']:,}</div>
    <div style="font-size:11px;color:#6B7280">Total grant</div>
  </div>
  <div style="background:#E1F5EE;border-radius:8px;padding:10px 16px;flex:1;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#1A6E6E">${budget['spent_ytd']:,}</div>
    <div style="font-size:11px;color:#6B7280">Spent YTD ({budget['pct_spent']}%)</div>
  </div>
  <div style="background:#E1F5EE;border-radius:8px;padding:10px 16px;flex:1;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#1A6E6E">${budget['remaining']:,}</div>
    <div style="font-size:11px;color:#6B7280">Remaining</div>
  </div>
</div>
<table>
  <thead><tr><th {th}>Line Item</th><th {thc}>Annual Budget</th><th {thc}>Spent YTD</th><th {thc}>% Used</th></tr></thead>
  <tbody>{bgt_rows}</tbody>
</table>""")}
{section("6. Challenges and Adaptations", prose_html(sections['challenges']))}
{section("7. Looking Ahead — Next Quarter", prose_html(sections['next_quarter']))}

<div style="background:#F5F5F5;border-radius:8px;padding:16px 20px;margin-top:8px">
  <div style="font-size:13px;font-weight:600;color:#1A6E6E;margin-bottom:4px">Submitted by: {grant['report_author']}</div>
  <div style="font-size:12px;color:#6B7280">{grant['org_name']} &middot; {grant['org_location']}</div>
  <div style="font-size:11px;color:#9CA3AF;margin-top:2px">Grant: {grant['grant_number']} &middot; {grant['funder_name']} &middot; {today}</div>
</div>

<div class="footer">AI-assisted draft — review all narrative sections before sending to funder</div>
</div></body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  ERROR: ANTHROPIC_API_KEY not set.")
        print("  Run:  set ANTHROPIC_API_KEY=sk-ant-your-key-here")
        print("  Then run this script again.\n")
        input("  Press Enter to close...")
        return

    q    = GRANT["report_quarter"]
    year = GRANT["report_year"]
    slug = f"Q{q}_{year}"

    docx_out = f"quarterly_report_{slug}.docx"
    html_out = f"quarterly_report_{slug}.html"

    print(f"\n{'='*60}")
    print(f"  Quarterly Report Generator")
    print(f"  {GRANT['org_name']} — {GRANT['funder_name']}")
    print(f"  {quarter_label(q, year)}")
    print(f"{'='*60}\n")

    # Calculate derived data
    print("  Calculating objectives progress and budget...")
    objectives = calc_objective_progress(GRANT, QUARTERLY_DATA)
    budget     = calc_budget(GRANT, QUARTERLY_DATA)

    # Print quick summary
    on_track = sum(1 for o in objectives if o["on_track"])
    print(f"  Objectives on track: {on_track}/{len(objectives)}")
    print(f"  Budget: ${budget['spent_ytd']:,} spent of ${budget['total']:,} ({budget['pct_spent']}%)")
    print(f"  PHQ-A improvement: {QUARTERLY_DATA['pct_meaningful_phq_improvement']}% (target: 75%)\n")

    # Generate narrative with Claude
    print("  Generating narrative sections with Claude...")
    client   = anthropic.Anthropic(api_key=api_key)
    sections = build_narrative(client, GRANT, QUARTERLY_DATA, objectives, budget)

    # Build outputs
    print(f"\n  Building reports...")
    try:
        build_docx(GRANT, QUARTERLY_DATA, objectives, budget, sections, docx_out)
    except Exception as e:
        print(f"  Word doc skipped: {e}")

    build_html(GRANT, QUARTERLY_DATA, objectives, budget, sections, html_out)

    print(f"\n{'='*60}")
    print(f"  Done!\n")
    print(f"  {docx_out}")
    print(f"     Open in Word — review all narrative sections,")
    print(f"     add your signature, send to {GRANT['funder_name']}")
    print(f"\n  {html_out}")
    print(f"     Browser version — good for sharing internally")
    print(f"\n  Remember to review every AI-drafted paragraph")
    print(f"  before sending to a funder.")
    print(f"{'='*60}\n")

    input("  Press Enter to close...")


if __name__ == "__main__":
    main()
