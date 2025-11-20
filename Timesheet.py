# dash_timesheet_app.py - FINAL CORRECTED VERSION (Timer Not Counting Fix)

import os
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

import requests
from openpyxl import Workbook

from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output, # cite: 2
    State, # cite: 2
    ctx, # cite: 2
    ALL, # cite: 2
    MATCH, # cite: 2
    no_update, # cite: 2
)
import dash_bootstrap_components as dbc

# ------------------ Configuration ------------------
DATA_FILE = "timesheet_data.json"
WEEK_START_FMT = "%Y-%m-%d"


# ------------------ Helper functions ------------------
def _monday_of(d: date) -> date:
    """Returns the Monday of the week for a given date."""
    return d - timedelta(days=d.weekday())


def format_hours_hhmm(hours_float: float) -> str:
    """Formats a float of hours into HH:MM string."""
    total_minutes = int(round(hours_float * 60))
    hh = total_minutes // 60
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}" # cite: 3


def load_json() -> Dict[str, Any]:
    """Loads the main data JSON file."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data: Dict[str, Any]):
    """Saves the main data JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2) # cite: 4


def now_iso() -> str:
    """Returns the current time as an ISO 8601 string."""
    # Ensure high precision for accurate tracking
    return datetime.now().isoformat(timespec='milliseconds')


def parse_iso(ts: str) -> datetime:
    """Parses an ISO 8601 string into a datetime object."""
    return datetime.fromisoformat(ts)


def running_hours(day_obj: Dict[str, Any]) -> float:
    """Calculates running hours only."""
    if day_obj.get("running_start"): # cite: 5
        start_time = parse_iso(day_obj["running_start"])
        # Use datetime.now() without tzinfo for consistent subtraction (as parse_iso does not assume tz)
        elapsed_seconds = (datetime.now() - start_time).total_seconds() 
        return elapsed_seconds / 3600.0
    return 0.0


def day_total_hours(day_obj: Dict[str, Any]) -> float:
    """Calculates the total hours for a single day object, including running timers."""
    total = 0.0
    for s, e in day_obj.get("sessions", []):
        total += (parse_iso(e) - parse_iso(s)).total_seconds() / 3600.0

    # Include running time calculated live
    # If a timer is currently running, add the elapsed time [cite: 5]
    total += running_hours(day_obj)
    return total


# ------------------ Static Data ------------------
EMPLOYEE_DATA = {
    "Dipangsu Mukherjee": "Technical", 
    "Soumya Maity": "Technical",
    "Prithish Biswas": "Development", 
    "Arya Majumdar": "Development",
    "Shahbaz Ali": "Technical", 
    "Souma Banerjee": "Sales", 
    "Shivangi Singh": "Sales", 
    "Ritu Das": "Marketing", 
    "Soumya Manna": "Development",
    "Jayant Rai": "Technical", 
    "Sayam Rozario": "Admin", 
    "Sneha Simran": "Admin", "Pompi Goswami": "Human Resource", 
    "Joydeep Chakraborty": "Sales", "Peea P Bal": "Placement", 
    "Romit Roy": "Admin", "Soumi Roy": "Admin", 
    "Subhasis Marick": "Accountant", "Subhojit Chakraborty": "Technical", 
    "Rohit Kumar Singh": "Technical", "Sujay Kumar Lodh": "Technical", 
    "Rahul Kumar Chakraborty": "Placement", "Sandipan Kundu": "Development", 
    "Sachin Kumar Giri": "Technical", "Anamika Dutta": "Sales", # cite: 7
    "Sohini Das": "Sales", "Aheli Some": "Technical", 
    "Shubham Kumar Choudhari": "Technical", "Mithun Jana": "Technical", 
    "Saikat Dutta": "Development", "Ankan Roy": "Sales", 
    "Utsav Majumdar": "Sales", "Artha Chakraborty": "Marketing", 
    "Soumen Paul": "Marketing", "Papia Biswas": "Sales", # cite: 7
}

DEPARTMENT_TASKS = {
    "Sales": {
        "Lead Management": [
            "New Lead Calling", "Old Lead Follow-up", # cite: 8
            "Webinar & Seminar Coordination", "CRM Management", "Lead Management & Conversion Optimization",
        ],
        "Sales Conversion Activities": [
            "Product Demonstration (Online Demo)", "Office/ College Visit Booking", # cite: 9
            "Office/College Visit Client Handling", "Active Follow-up (Post-Demo/Visit)",
        ],
        "Revenue & Financial Operations": [
            "Revenue Generation & Target Achievement", "Bajaj EMI Process Management", "EMI Collection & Due Management",  # cite: 10
            "Ex-SP EMI Collection", "Revenue Audit",
        ],
        "Client & Student Management": [
            "Client Relationship Management", "Handling Existing Students of Former Team Members", # cite: 11
            "Class Schedule Management",
        ],
        "Reporting & Strategy": [
            "Sales Strategy & Planning", "Reporting & Forecasting", # cite: 11
            "Daily Activity Report Submission",
        ],
        "Team Management & Collaboration": [
            "Daily Standups", "Daily Follow-up of Team Members’ Leads", # cite: 12
            "Sales Team Recruitment & Interviewing", "New Employee Training",
        ],
        "Cross-Functional Coordination": [
            "Coordination - Technical Team", "Coordination - Marketing Team", "Coordination - Accounts Team", # cite: 13
            "Coordination - Operations Team", "Compliance & Process Improvement",
        ],
        "Meeting": ["Meeting"],
        "Adhoc": ["Others (Please fill the comment)"],
    },
    "Technical": {
        "Curriculum Development": [
            "Training Module Development (SEO, SEM, Analytics, etc.)", "Customized Curriculum for B2B Clients", # cite: 14
            "Presentation (PPT) Preparation", "Creating Class Notes & Supplementary Resources", 
            "Integrating Case Studies & Practical Exercises", "Project & Assignment Preparation",
        ],
        "Training Delivery & Student Engagement": [
            "Conducting Sessions (Data Analytics, Cloud, Cyber Security, etc.)", # cite: 15
            "Clearing Student Doubts", "Managing Class Schedules & Batch Monitoring",
        ],
        "Student Assessment & Career Support": [
            "Conducting Student Mock Interviews", "Providing Pre-Interview Brush-up Sessions", # cite: 16
            "Assignment & Test Paper Grading", "Internship & Live Project Support",
        ],
        "Research & Development (R&D)": [
            "R&D on New Subjects & Teaching Methods", "R&D on AI Tools & Technologies", 
            "Reviewing & Revising Existing Course Content", "Developing PPT for Course Content", # cite: 17
            "Developing New Data Sources",
        ],
        "Business Development & Outreach": [
            "Conducting Demo Sessions for Admissions (B2C & B2B)", "Webinar & Seminar Planning", 
            "College Visits & Online Workshops", # cite: 18
            "Collaboration with Industry for Internships", "Collaboration with Authorized Training Centers (ATCs)", 
            "Providing Market Insights to Sales Teams",
        ],
        "Administration & Reporting": [
            "Coordination with Admin & Operations Teams", "Updating Daily Task Reports", # cite: 19
            "Automating Trackers & Internal Processes", "Managing Government Tender Processes",
        ],
        "Team & Quality Management": [
            "Trainer Development & Mentoring", "Interviewing & Selecting New Trainers", # cite: 20
            "Implementing Quality Control for Training Delivery",
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"],
    },
    "Admin": {
        "Learner Onboarding & Support": [
            "Conduct LMS Walkthrough for New Learners", "Act as Primary Point of Contact (POC) for Learners", 
            "Create and Manage Learner Cohorts & WhatsApp Groups", # cite: 21
            "Welcome New Learners (Kits / ID Cards)", "Resolve Learner Queries (WhatsApp & Tickets)", 
            "Handle Incoming Calls from Learners", "Contact Learners for Feedback",
        ],
        "Scheduling & Logistics": [
            "Schedule & Reschedule Classes/Exams", "Plan & Execute Seminars and Events", # cite: 22
            "Manage Travel and Accommodation Requests", "Monitor Training Logistics",
        ],
        "Strategic Operations & Process Management": [
            "Strategize Batch Planning with HODs", "Streamline & Improve Organizational Processes", # cite: 23
            "Handle High-Level Escalations", "Calculate Training Costs for Sales Quotations",
        ],
        "Inter-Departmental Coordination": [
            "Coordinate with Placement Team for Learner Transition", "Coordinate with HR for Policy Implementation", 
            "Coordinate with Accounts (Trainer Pay, Expenses, etc.)", # cite: 24
            "Coordinate with HODs on Performance Feedback",
        ],
        "Quality Assurance & Performance": [
            "Conduct Audits on Live Classrooms", "Enforce Standard Operating Procedure (SOP) Compliance", 
            "Monitor Student and Trainer Performance", "Implement Skill Matrix for Resource Utilization", # cite: 25
        ],
        "Certificate & Vendor Management": [
            "Ensure Digital Certificate Distribution", "Manage Vendor for Hard Copy Certificates",
        ],
        "Strategic Planning & Process Management": [
            "Strategize Batch Planning with HODs", # cite: 26
            "Streamline & Improve Organizational Processes", "Implement Skill Matrix for Resource Utilization", 
            "Enforce Standard Operating Procedure (SOP) Compliance",
        ],
        "Performance & Quality Management": [
            "Oversee Student & Trainer Performance", "Conduct Audits on Live Classrooms", # cite: 27
            "Monitor Training Logistics & Quality",
        ],
        "Inter-Departmental Coordination (Extended)": [
            "Coordinate with Sales for Pricing & Quotations", "Coordinate with Placement Team for Learner Transition", 
            "Coordinate with HR for Policy Implementation", "Coordinate with Accounts for Remuneration & Expenses", # cite: 28
        ],
        "Escalation & Issue Resolution": [
            "Handle High-Level Operational Escalations"
        ],
        "Logistics & Event Management": [
            "Plan & Execute Seminars and Events", "Manage Travel and Accommodation Requests", # cite: 29
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"],
    },
    "Development": {
        "Project Management & Scrum": [
            "Conduct Daily Scrum Meetings & Standups", "Manage Jira Boards & Sprint Progress", 
            "Conduct Sprint Planning & Backlog Grooming", "Track Blockers, Dependencies & Resources", # cite: 30
            "Prepare Project Progress Reports", "Create & Maintain Project Documentation",
        ],
        "UI/UX & Graphic Design": [
            "Create Social Media Creatives (Posts, Carousels)", "Design Print Media (Banners, Brochures)", 
            "Design UI Modules (Websites, Apps, Templates)", # cite: 31
            "Maintain UI/UX Design System", "Conduct UX Research & Brainstorming",
        ],
        "Frontend Development": [
            "Develop/Modify Frontend Modules", "Build Responsive Components", # cite: 32
            "Develop Landing Pages & Email Templates", "Manage Git & Version Control", 
            "Frontend Testing & Debugging", "Monitor & Optimize Frontend Performance",
        ],
        "Backend & Database Development": [
            "Setup Backend/DB for New Projects (APIs)", "Backend Bug Fixing & Troubleshooting", # cite: 33
            "Perform Database Maintenance & Updates",
        ],
        "Website & LMS Maintenance": [
            "General Website/LMS Maintenance & Updates", "Export Leads from LMS/Panel", 
            "Deploy Production Updates",
        ],
        "System & Server Administration": [
            "Manage Employee Email Accounts & Issues", "Monitor Server Uptime & Performance", # cite: 34
            "Manage Email Backups & Migrations", "Apply Security Patches & System Upgrades",
        ],
        "Training & Collaboration": [
            "Conduct Technical Training Sessions", "Cross-Functional Collaboration & Meetings", # cite: 35
            "Identify Team Training Needs",
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"],
    },
    "Operation": {
        "Meeting": ["Meeting"],
        "Adhoc": ["Others (Please fill the comment)"], # cite: 36
    },
    "Human Resource": {
        "Recruitment & Onboarding": [
            "Job Posting, Screening & Sourcing", "Interview Coordination & Scheduling", 
            "Issuing Offer & Appointment Letters", "New Joiner Documentation & Onboarding", 
            "Induction & System Integration", # cite: 37
        ],
        "Payroll & Compensation": [
            "Salary Sheet Preparation & Calculation", "Payslip Generation & Distribution", 
            "PF & ESIC Management (Application, Challan, etc.)", "TDS Calculation & Form 16 Distribution", 
            "Managing Reimbursements & Advances", # cite: 38
        ],
        "Employee Lifecycle & Exit Management": [
            "Performance Appraisal Coordination", "Issuing HR Letters (Confirmation, Promotion, Warning, etc.)", 
            "Handling Exit Formalities & Final Settlement", "Issuing Relieving & Experience Letters",
        ],
        "Employee Relations & Engagement": [
            "Grievance Handling & Resolution", "Planning & Executing Employee Engagement Activities", # cite: 39
            "Conducting Employee Surveys & Feedback Sessions", "Managing Disciplinary Actions & PIPs",
        ],
        "HR Administration & Compliance": [
            "Maintaining Employee Master Data & Trackers", "Managing Daily Attendance & Leave Records", # cite: 40
            "ID Card & Visiting Card Management", "Policy Documentation & Enforcement", 
            "Managing Office Hygiene & Admin Tasks",
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"], # cite: 41
    },
    "Marketing": {
        "Content Strategy & Ideation": [
            "Creative Campaign Ideation", "Social Media Content Ideation & Research", 
            "Website Content Planning", "B2B/B2C Project Content Strategy (Seminars, etc.)",
        ],
        "Content Creation & Writing": [
            "Blog & Technical Article Writing", "Social Media Copywriting (Captions & Post Content)", # cite: 42
            "Website Content Writing", "Brochure & Print Material Content", "Quora Content Creation",
        ],
        "Graphic & Video Production": [
            "Social Media Graphic Design (Static & Motion)", "Video Creation & Editing", # cite: 43
            "Brochure & Print Asset Design",
        ],
        "Social Media Management": [
            "Content Scheduling & Posting", "Community Engagement", # cite: 44
            "Social Media Performance Reporting",
        ],
        "Project & Team Management": [
            "Assigning Tasks to Content & Design Teams", "Content Editing, Proofreading & Delivery", 
            "Monitoring Quality & Deadlines", "Coordinating with Printing Vendors", # cite: 45
        ],
        "Internal Collaboration & Events": [
            "Participation in Office Event Organization", "Cross-functional Content Meetings",
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"],
    },
    "Placement": {
        "Corporate Outreach & Tie-Ups": [
            "Relationship Building & Company Tie-Ups", "B2B Support & Collaboration", # cite: 46
        ],
        "Candidate Training & Grooming": [
            "Resume Building & Correction", "Soft Skills & Personal Branding Sessions", 
            "Mock Interview Drills", "Job Placement Workshops", # cite: 47
        ],
        "Placement & Interview Management": [
            "Lining Up Interviews", "Database Management", "Tracking Placement Achievements",
        ],
        "Student Support & Onboarding": [
            "Conducting New Batch Orientation", # cite: 48
            "Grievance Handling", "B2C Support",
        ],
        "Team & Cross-Functional Coordination": [
            "Weekly Meetings (Sales, HODs)", "Support to Marketing (Testimonials, Offer Letters)", 
            "Coordination with Development Team", # cite: 49
            "Monitoring Team Performance",
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"],
    },
}


def generate_row(row_index, row):
    task = row["task"]
    sub = row["subtask"]
    days = row["days"]

    day_cols = []
    for di in range(7):
        d = days[di]
        hrs_str = format_hours_hhmm(day_total_hours(d)) # cite: 50
        running = d.get("running_start") is not None

        day_cols.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                hrs_str,
                                # FIXED: Changed to dictionary ID for live updates (Issue: Timer not counting)
                                id={"type": "hours-display", "index": f"{row_index}-{di}"},
                                style={ # cite: 52
                                    "textAlign": "center",
                                    "fontWeight": "bold", # cite: 53
                                },
                            ),
                            dbc.Button(
                                "Stop" if running else "Start", # cite: 54
                                id={"type": "toggle-btn", "index": f"{row_index}-{di}"},
                                size="sm",
                                color="danger" if running else "success", # cite: 55
                                style={"width": "100%", "marginTop": "6px"},
                            ),
                            dcc.Textarea( # cite: 56
                                id={"type": "notes", "index": f"{row_index}-{di}"},
                                value=d.get("notes", ""),
                                style={ # cite: 57
                                    "width": "100%",
                                    "height": "60px",
                                    "marginTop": "6px", # cite: 58
                                },
                            ),
                        ]
                    ), # cite: 59
                    style={"height": "170px"},
                ),
                width=1,
            ) # cite: 60
        )

    total = sum(day_total_hours(d) for d in days)

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                        [ # cite: 61
                                html.B(task),
                                html.Div(
                                    sub, # cite: 62
                                    style={"fontSize": "12px", "color": "#666"},
                                ),
                        ] # cite: 63
                        ),
                        width=2,
                    ),
                    *day_cols, # cite: 64
                    dbc.Col(
                        html.Div(
                            format_hours_hhmm(total),
                            id=f"row-total-{row_index}", # cite: 65
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold", # cite: 66
                            },
                        ),
                        width=1, # cite: 67
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Delete",
                            id={"type": "delete-row", "index": str(row_index)}, # cite: 68
                            color="danger",
                            size="sm",
                        )
                    ), # cite: 69
                ],
                className="g-1",
                align="center",
            )
        ],
        style={"padding": "6px", "borderBottom": "1px solid #ddd"},
    )


# ------------------ LAYOUT ------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

current_week_start = _monday_of(date.today())

app.layout = dbc.Container(
    [ # cite: 70
        html.H3(
            "Weekly Timesheet (Satts Cyber Tech Pvt. Ltd.)", # cite: 71
            className="my-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Employee"), # cite: 72
                        dcc.Dropdown(
                            id="emp",
                            options=[ # cite: 73
                                {"label": e, "value": e} for e in EMPLOYEE_DATA.keys()
                            ],
                            value=next(iter(EMPLOYEE_DATA.keys())),
                        ),
                    ], # cite: 74
                    width=3,
                ),
                dbc.Col(
                    [
                        html.Label("Department"), # cite: 75
                        dbc.Input(id="dept", readonly=True),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [ # cite: 76
                        html.Label("Week Start"),
                        dcc.DatePickerSingle(
                            id="week", # cite: 77
                            date=current_week_start.isoformat(),
                        ),
                    ],
                    width=3, # cite: 78
                ),
                dbc.Col(
                    [
                        html.Br(),
                        dbc.Button( # cite: 79
                            "Save",
                            id="save-btn",
                            color="primary",
                            className="me-2", # cite: 80
                        ),
                        dbc.Button("Submit", id="submit-btn", color="success"),
                    ],
                    width=3, # cite: 81
                ),
            ],
            className="my-2",
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(id="task-dd", placeholder="Select Task"), # cite: 82
                    width=4,
                ),
                dbc.Col(
                    dcc.Dropdown(id="subtask-dd", placeholder="Subtask"),
                    width=4, # cite: 83
                ),
                dbc.Col(
                    dbc.Button("Add Task", id="add-btn", color="info"),
                    width=2, # cite: 84
                ),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col("TASK", width=2),
                *[
                    dbc.Col(day, width=1) # cite: 85
                    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                ],
                dbc.Col("TOTAL", width=1),
                dbc.Col(""),
            ],
            className="fw-bold", # cite: 86
        ),
        html.Div(id="rows"),
        html.Hr(),
        html.Div(id="weekly-total", className="fw-bold"),
        dcc.Store(id="store"),
        dcc.Store(id="ui-store"),
        dcc.Interval(id="tick", interval=1000),
        # --- Toast for "Saved successfully" ---
        dbc.Toast(
            id="save-toast",
            header="Success", # cite: 87
            icon="success",
            is_open=False,
            duration=3000,
            children="Timesheet saved successfully.",
            style={
                "position": "fixed",
                "top": 10, # cite: 88
                "right": 10,
                "zIndex": 9999,
            },
        ),
    ],
    fluid=True,
)


# ------------------ LOAD EMPLOYEE + WEEK DATA ------------------
@app.callback(
    Output("store", "data"),
    Output("dept", "value"),
    Output("task-dd", "options"),
    Input("emp", "value"),
    Input("week", "date"),
)
def load_user(emp, week_date): # cite: 89
    if not emp or not week_date:
        return no_update, "", []

    data = load_json()

    week = date.fromisoformat(week_date)
    key = f"{emp}::{week.isoformat()}"
    if key not in data:
        data[key] = {"rows": []}
        save_json(data)

    dept = EMPLOYEE_DATA.get(emp, "")
    task_opts = [
        {"label": t, "value": t}
        for t in sorted(DEPARTMENT_TASKS.get(dept, {}).keys()) # cite: 90
    ]

    return data, dept, task_opts


# ------------------ UPDATE SUBTASKS ------------------
@app.callback(
    Output("subtask-dd", "options"),
    Input("task-dd", "value"),
    State("dept", "value"),
)
def update_subtasks(task, dept):
    if not task or not dept:
        return []
    return [
        {"label": s, "value": s}
        for s in DEPARTMENT_TASKS.get(dept, {}).get(task, [])
    ]


# ------------------ RENDER ROWS ------------------
# FIXED: Removed Input("tick", "n_intervals"). This stops full table re-render every second.
@app.callback(
    Output("rows", "children"),
    Output("weekly-total", "children"),
    Input("store", "data"), # cite: 91
    State("emp", "value"),
    State("week", "date"),
    State("ui-store", "data"),
)
def render_rows(data, emp, week_date, ui_store):
    # This block is now redundant as 'tick' input is removed.
    # if ctx.triggered_id == "tick":
    #     running = (ui_store or {}).get("running")
    #     if not running:
    #         return no_update, no_update

    if not data or not emp or not week_date: # cite: 92
        return [], "Weekly Total: 00:00"

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])

    comps = []
    week_total = 0.0
    for i, row in enumerate(rows):
        comps.append(generate_row(i, row))
        for d in row["days"]:
            week_total += day_total_hours(d)

    return comps, f"Weekly Total: {format_hours_hhmm(week_total)}"


# ------------------ LIVE TIMER UPDATE (FIXES TIMER FREEZING) ------------------
@app.callback(
    Output({"type": "hours-display", "index": MATCH}, "children"),
    Input("tick", "n_intervals"),
    State("store", "data"),
    State("emp", "value"),
    State("week", "date"),
    State("ui-store", "data"),
    State({"type": "hours-display", "index": MATCH}, "id"),
)
def update_live_hours(_n, data, emp, week_date, ui_store, triggered_id_dict):
    running = (ui_store or {}).get("running")

    if not running or not emp or not week_date or not data:
        return no_update

    try:
        match_row, match_day = map(int, triggered_id_dict["index"].split("-"))
    except (TypeError, ValueError):
        return no_update

    if running != [match_row, match_day]:
        return no_update # Only update the cell that is actively running

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])

    if match_row >= len(rows) or match_day >= len(rows[match_row]["days"]):
         return no_update

    day_obj = rows[match_row]["days"][match_day]

    current_total_hours = day_total_hours(day_obj)
    return format_hours_hhmm(current_total_hours)


# ------------------ ADD ROW ------------------
@app.callback(
    Output("store", "data", allow_duplicate=True),
    Output("task-dd", "value"), # cite: 93
    Output("subtask-dd", "value"), # cite: 93
    Input("add-btn", "n_clicks"),
    State("task-dd", "value"),
    State("subtask-dd", "value"),
    State("store", "data"),
    State("emp", "value"),
    State("week", "date"),
    prevent_initial_call=True,
)
def add_row(n, task, subtask, data, emp, week_date):
    if n is None or not task or not emp or not week_date:
        return data, no_update, no_update

    data = data or {}
    week_start_iso = date.fromisoformat(week_date).isoformat()
    key = f"{emp}::{week_start_iso}"

    if key not in data: # cite: 94
        data[key] = {"rows": []}

    new_row = {
        "task": task,
        "subtask": subtask or "",
        "days": [
            {"sessions": [], "notes": "", "running_start": None}
            for _ in range(7)
        ],
    }

    data[key]["rows"].append(new_row)
    save_json(data) # cite: 95

    return data, None, None


# ------------------ DELETE ROW ------------------
@app.callback(
    Output("store", "data", allow_duplicate=True),
    Input({"type": "delete-row", "index": ALL}, "n_clicks"),
    State("store", "data"),
    State("emp", "value"),
    State("week", "date"),
    prevent_initial_call=True,
)
def delete_row(n_clicks, data, emp, week_date):
    if not ctx.triggered or not ctx.triggered_id:
        return data

    if not n_clicks or all(c is None for c in n_clicks): # cite: 96
        return data

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "delete-row":
        return data

    try:
        idx = int(triggered["index"])
    except (TypeError, ValueError):
        return data

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])

    if 0 <= idx < len(rows):
        rows.pop(idx)
        data[key]["rows"] = rows # cite: 97
        save_json(data)

    return data


# ------------------ TOGGLE TIMER ------------------
@app.callback(
    Output("store", "data", allow_duplicate=True),
    Output("ui-store", "data"),
    Input({"type": "toggle-btn", "index": ALL}, "n_clicks"),
    State("store", "data"),
    State("ui-store", "data"),
    State("emp", "value"),
    State("week", "date"),
    prevent_initial_call=True,
)
def toggle(n, data, ui_store, emp, week_date):
    if not ctx.triggered or not ctx.triggered_id:
        return data, ui_store or {}

    if not n or all(c is None for c in n): # cite: 98
        return data, ui_store or {}

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "toggle-btn":
        return data, ui_store or {}

    ui_store = ui_store or {}

    try:
        row, day = map(int, triggered["index"].split("-"))
    except (TypeError, ValueError):
        return data, ui_store

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])

    if not rows or row >= len(rows): # cite: 99
        return data, ui_store

    d = rows[row]["days"][day]
    running = ui_store.get("running")
    
    target_date = date.fromisoformat(week_date) + timedelta(days=day)
    is_currently_running = running == [row, day]

    if is_currently_running:
        d["sessions"].append([d["running_start"], now_iso()])
        d["running_start"] = None
        ui_store["running"] = None
        
    elif target_date == date.today():
        # Case 2: Toggling a new timer ON (Start button pressed, and it's today)
        
        # A. Stop old timer if any other is running
        if running:
            r, di = running
            # Check bounds and stop the previously running timer
            if r < len(rows) and di < len(rows[r]["days"]):
                old = rows[r]["days"][di]
                if old.get("running_start"):
                    old["sessions"].append([old["running_start"], now_iso()]) # cite: 100
                    old["running_start"] = None
        
        # B. Start the new timer
        d["running_start"] = now_iso()
        ui_store["running"] = [row, day]
        
    # else: Timer is already stopped, or the day is in the past/future.

    save_json(data)
    return data, ui_store


# ------------------ SAVE NOTES + POPUP ------------------
@app.callback(
    Output("store", "data", allow_duplicate=True),
    Output("save-toast", "is_open"),
    Input("save-btn", "n_clicks"),
    State({"type": "notes", "index": ALL}, "value"),
    State({"type": "notes", "index": ALL}, "id"),
    State("store", "data"),
    State("emp", "value"),
    State("week", "date"),
    prevent_initial_call=True, # cite: 102
)
def save_notes(n, values, ids, data, emp, week_date):
    if n is None or not data or not emp or not week_date:
        return data, False

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])

    notes_map = {}
    for idd, val in zip(ids, values):
        if idd and "index" in idd:
            notes_map[idd["index"]] = val

    for r_idx, row in enumerate(rows):
        for d_idx, day in enumerate(row.get("days", [])): # cite: 103
            cid = f"{r_idx}-{d_idx}"
            if cid in notes_map:
                day["notes"] = notes_map[cid]

    save_json(data)
    return data, True  # open toast


# ------------------ SUBMIT WEEK (EXCEL + OPTIONAL POST) ------------------
@app.callback(
    Output("store", "data", allow_duplicate=True),
    Input("submit-btn", "n_clicks"),
    State("store", "data"),
    State("emp", "value"), # cite: 104
    State("week", "date"),
    prevent_initial_call=True,
)
def submit_week(n, data, emp, week_date):
    if n is None or not data or not emp or not week_date:
        return data

    key = f"{emp}::{date.fromisoformat(week_date).isoformat()}"
    rows = data.get(key, {}).get("rows", [])
    entry = data.get(key, {})

    wb = Workbook()
    ws = wb.active or wb.create_sheet()
    ws.append(["Employee", "Department", "Date", "Task", "Subtask", "Hours", "Notes"])

    dept = EMPLOYEE_DATA.get(emp, "")
    week = date.fromisoformat(week_date)
    export_data = []

    for row in rows:
        for di, day in enumerate(row["days"]):
            hrs = day_total_hours(day)
            notes = day.get("notes", "").strip()
            if hrs > 0 or notes:
                day_date = week + timedelta(days=di)
                
                export_data.append(
                    {
                        "Employee": emp,
                        "Department": dept,
                        "Date": day_date.isoformat(),
                        "Task": row["task"], 
                        "Subtask": row["subtask"],
                        "Hours": round(hrs, 2),
                        "Notes": notes,
                    }
                ) 
                ws.append(
                    [
                        emp,
                        dept, # cite: 109
                        day_date.isoformat(),
                        row["task"],
                        row["subtask"],
                        round(hrs, 2), # cite: 110
                        notes,
                    ]
                )

    filename = f"Timesheet_{emp.replace(' ', '_')}_{week_date}.xlsx"
    wb.save(filename)

    try:
        response = requests.post( # cite: 111
            "http://127.0.0.1:5000/submit", json=export_data, timeout=3
        )
        entry["server_upload_status"] = response.status_code
    except Exception as e:
        print(f"Server submission failed: {e}")
        entry["server_upload_status"] = 0

    entry["submitted"] = True
    data[key] = entry
    save_json(data)
    return data


# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)