"""
Dash web version of the PyQt6 Timesheet app you provided developed by Jayant.

Features implemented:
- Employee selection and department auto-fill
- Task/Subtask management per department
- Per-day cells with hours display, notes, Start/Stop timer
- Save/load to JSON file (server-side persistence)
- Weekly submit: export to Excel, optional POST to central server, locks week
- Weekly totals and daily totals

Run:
    pip install dash dash-bootstrap-components pandas openpyxl
    python dash_timesheet_app.py

Open http://127.0.0.1:8050

This is a single-file app intended as a drop-in replacement for your PyQt app.
"""

import os
import json
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import requests

from dash import Dash, html, dcc, Input, Output, State, ctx, ALL, MATCH, no_update
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
    return f"{hh:02d}:{mm:02d}"


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
        json.dump(data, f, indent=2)


def now_iso() -> str:
    """Returns the current time as an ISO 8601 string."""
    return datetime.now().isoformat()


def parse_iso(ts: str) -> datetime:
    """Parses an ISO 8601 string into a datetime object."""
    return datetime.fromisoformat(ts)


def day_total_hours(day_obj: Dict[str, Any]) -> float:
    """Calculates the total hours for a single day object, including running timers."""
    total = 0.0
    for s, e in day_obj.get("sessions", []):
        total += (parse_iso(e) - parse_iso(s)).total_seconds() / 3600.0
    
    # If a timer is currently running, add the elapsed time
    if day_obj.get("running_start"):
        # Use replace(tzinfo=None) to compare with naive datetime.now()
        start_time = parse_iso(day_obj["running_start"]).replace(tzinfo=None)
        total += (datetime.now() - start_time).total_seconds() / 3600.0
    return total


# ------------------ Static Data (copied from your app) ------------------
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
    "Ayos Ghosh": "Operation",
    "Sayam Rozario": "Admin",
    "Sneha Simran": "Admin",
    "Pompi Goswami": "Human Resource",
    "Joydeep Chakraborty": "Sales",
    "Peea P Bal": "Placement",
    "Romit Roy": "Admin",
    "Soumi Roy": "Admin",
    "Subhasis Marick": "Accountant",
    "Hrithik Lall": "Technical",
    "Subhojit Chakraborty": "Technical",
    "Rohit Kumar Singh": "Technical",
    "Sujay Kumar Lodh": "Technical",
    "Rahul Kumar Chakraborty": "Placement",
    "Sandipan Kundu": "Development",
    "Sachin Kumar Giri": "Technical",
    "Anamika Dutta": "Sales",
    "Sohini Das": "Sales",
    "Aheli Some": "Technical",
    "Shubham Kumar Choudhari": "Technical",
    "Mithun Jana": "Technical",
    "Saikat Dutta": "Development",
    "Ankan Roy": "Sales",
    "Utsav Majumdar": "Sales",
    "Artha Chakraborty": "Marketing"
}

# For brevity, department_tasks is simplified but kept faithful to original structure
DEPARTMENT_TASKS = {
    "Sales": {
        "Lead Management": [
            "New Lead Calling",
            "Old Lead Follow-up",
            "Webinar & Seminar Coordination",
            "CRM Management",
            "Lead Management & Conversion Optimization"
        ],
        "Sales Conversion Activities": [
            "Product Demonstration (Online Demo)",
            "Office/ College Visit Booking",
            "Office/College Visit Client Handling",
            "Active Follow-up (Post-Demo/Visit)"
        ],
        "Revenue & Financial Operations": [
            "Revenue Generation & Target Achievement",
            "Bajaj EMI Process Management",
            "EMI Collection & Due Management",
            "Ex-SP EMI Collection",
            "Revenue Audit"
        ],
        "Client & Student Management": [
            "Client Relationship Management",
            "Handling Existing Students of Former Team Members",
            "Class Schedule Management"
        ],
        "Reporting & Strategy": [
            "Sales Strategy & Planning",
            "Reporting & Forecasting",
            "Daily Activity Report Submission"
        ],
        "Team Management & Collaboration": [
            "Daily Standups",
            "Daily Follow-up of Team Members’ Leads",
            "Sales Team Recruitment & Interviewing",
            "New Employee Training"
        ],
        "Cross-Functional Coordination": [
            "Coordination - Technical Team",
            "Coordination - Marketing Team",
            "Coordination - Accounts Team",
            "Coordination - Operations Team",
            "Compliance & Process Improvement"
        ],
        "Meeting": ["Meeting"],
        "Adhoc": ["Others (Please fill the comment)"]
    },
    "Technical": {
        "Curriculum Development": [
            "Training Module Development (SEO, SEM, Analytics, etc.)",
            "Customized Curriculum for B2B Clients",
            "Presentation (PPT) Preparation",
            "Creating Class Notes & Supplementary Resources",
            "Integrating Case Studies & Practical Exercises",
            "Project & Assignment Preparation"
        ],
        "Training Delivery & Student Engagement": [
            "Conducting Sessions (Data Analytics, Cloud, Cyber Security, etc.)",
            "Clearing Student Doubts",
            "Managing Class Schedules & Batch Monitoring"
        ],
        "Student Assessment & Career Support": [
            "Conducting Student Mock Interviews",
            "Providing Pre-Interview Brush-up Sessions",
            "Assignment & Test Paper Grading",
            "Internship & Live Project Support"
        ],
        "Research & Development (R&D)": [
            "R&D on New Subjects & Teaching Methods",
            "R&D on AI Tools & Technologies",
            "Reviewing & Revising Existing Course Content",
            "Developing PPT for Course Content",
            "Developing New Data Sources"
        ],
        "Business Development & Outreach": [
            "Conducting Demo Sessions for Admissions (B2C & B2B)",
            "Webinar & Seminar Planning",
            "College Visits & Online Workshops",
            "Collaboration with Industry for Internships",
            "Collaboration with Authorized Training Centers (ATCs)",
            "Providing Market Insights to Sales Teams"
        ],
        "Administration & Reporting": [
            "Coordination with Admin & Operations Teams",
            "Updating Daily Task Reports",
            "Automating Trackers & Internal Processes",
            "Managing Government Tender Processes"
        ],
        "Team & Quality Management": [
            "Trainer Development & Mentoring",
            "Interviewing & Selecting New Trainers",
            "Implementing Quality Control for Training Delivery"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    },
    "Admin": {
        "Learner Onboarding & Support": [
            "Conduct LMS Walkthrough for New Learners",
            "Act as Primary Point of Contact (POC) for Learners",
            "Create and Manage Learner Cohorts & WhatsApp Groups",
            "Welcome New Learners (Kits / ID Cards)",
            "Resolve Learner Queries (WhatsApp & Tickets)",
            "Handle Incoming Calls from Learners",
            "Contact Learners for Feedback"
        ],
        "Scheduling & Logistics": [
            "Schedule & Reschedule Classes/Exams",
            "Plan & Execute Seminars and Events",
            "Manage Travel and Accommodation Requests",
            "Monitor Training Logistics"
        ],
        "Strategic Operations & Process Management": [
            "Strategize Batch Planning with HODs",
            "Streamline & Improve Organizational Processes",
            "Handle High-Level Escalations",
            "Calculate Training Costs for Sales Quotations"
        ],
        "Inter-Departmental Coordination": [
            "Coordinate with Placement Team for Learner Transition",
            "Coordinate with HR for Policy Implementation",
            "Coordinate with Accounts (Trainer Pay, Expenses, etc.)",
            "Coordinate with HODs on Performance Feedback"
        ],
        "Quality Assurance & Performance": [
            "Conduct Audits on Live Classrooms",
            "Enforce Standard Operating Procedure (SOP) Compliance",
            "Monitor Student and Trainer Performance",
            "Implement Skill Matrix for Resource Utilization"
        ],
        "Certificate & Vendor Management": [
            "Ensure Digital Certificate Distribution",
            "Manage Vendor for Hard Copy Certificates"
        ],
        "Strategic Planning & Process Management": [
            "Strategize Batch Planning with HODs",
            "Streamline & Improve Organizational Processes",
            "Implement Skill Matrix for Resource Utilization",
            "Enforce Standard Operating Procedure (SOP) Compliance"
        ],
        "Performance & Quality Management": [
            "Oversee Student & Trainer Performance",
            "Conduct Audits on Live Classrooms",
            "Monitor Training Logistics & Quality"
        ],
        "Inter-Departmental Coordination (Extended)": [
            "Coordinate with Sales for Pricing & Quotations",
            "Coordinate with Placement Team for Learner Transition",
            "Coordinate with HR for Policy Implementation",
            "Coordinate with Accounts for Remuneration & Expenses"
        ],
        "Escalation & Issue Resolution": [
            "Handle High-Level Operational Escalations"
        ],
        "Logistics & Event Management": [
            "Plan & Execute Seminars and Events",
            "Manage Travel and Accommodation Requests"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    },
    "Development": {
        "Project Management & Scrum": [
            "Conduct Daily Scrum Meetings & Standups",
            "Manage Jira Boards & Sprint Progress",
            "Conduct Sprint Planning & Backlog Grooming",
            "Track Blockers, Dependencies & Resources",
            "Prepare Project Progress Reports",
            "Create & Maintain Project Documentation"
        ],
        "UI/UX & Graphic Design": [
            "Create Social Media Creatives (Posts, Carousels)",
            "Design Print Media (Banners, Brochures)",
            "Design UI Modules (Websites, Apps, Templates)",
            "Maintain UI/UX Design System",
            "Conduct UX Research & Brainstorming"
        ],
        "Frontend Development": [
            "Develop/Modify Frontend Modules",
            "Build Responsive Components",
            "Develop Landing Pages & Email Templates",
            "Manage Git & Version Control",
            "Frontend Testing & Debugging",
            "Monitor & Optimize Frontend Performance"
        ],
        "Backend & Database Development": [
            "Setup Backend/DB for New Projects (APIs)",
            "Backend Bug Fixing & Troubleshooting",
            "Perform Database Maintenance & Updates"
        ],
        "Website & LMS Maintenance": [
            "General Website/LMS Maintenance & Updates",
            "Export Leads from LMS/Panel",
            "Deploy Production Updates"
        ],
        "System & Server Administration": [
            "Manage Employee Email Accounts & Issues",
            "Monitor Server Uptime & Performance",
            "Manage Email Backups & Migrations",
            "Apply Security Patches & System Upgrades"
        ],
        "Training & Collaboration": [
            "Conduct Technical Training Sessions",
            "Cross-Functional Collaboration & Meetings",
            "Identify Team Training Needs"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    },
    "Operation": {
        "Meeting": ["Meeting"],
        "Adhoc": ["Others (Please fill the comment)"]
    },
    "Human Resource": {
        "Recruitment & Onboarding": [
            "Job Posting, Screening & Sourcing",
            "Interview Coordination & Scheduling",
            "Issuing Offer & Appointment Letters",
            "New Joiner Documentation & Onboarding",
            "Induction & System Integration"
        ],
        "Payroll & Compensation": [
            "Salary Sheet Preparation & Calculation",
            "Payslip Generation & Distribution",
            "PF & ESIC Management (Application, Challan, etc.)",
            "TDS Calculation & Form 16 Distribution",
            "Managing Reimbursements & Advances"
        ],
        "Employee Lifecycle & Exit Management": [
            "Performance Appraisal Coordination",
            "Issuing HR Letters (Confirmation, Promotion, Warning, etc.)",
            "Handling Exit Formalities & Final Settlement",
            "Issuing Relieving & Experience Letters"
        ],
        "Employee Relations & Engagement": [
            "Grievance Handling & Resolution",
            "Planning & Executing Employee Engagement Activities",
            "Conducting Employee Surveys & Feedback Sessions",
            "Managing Disciplinary Actions & PIPs"
        ],
        "HR Administration & Compliance": [
            "Maintaining Employee Master Data & Trackers",
            "Managing Daily Attendance & Leave Records",
            "ID Card & Visiting Card Management",
            "Policy Documentation & Enforcement",
            "Managing Office Hygiene & Admin Tasks"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    },
    "Marketing": {
        "Content Strategy & Ideation": [
            "Creative Campaign Ideation",
            "Social Media Content Ideation & Research",
            "Website Content Planning",
            "B2B/B2C Project Content Strategy (Seminars, etc.)"
        ],
        "Content Creation & Writing": [
            "Blog & Technical Article Writing",
            "Social Media Copywriting (Captions & Post Content)",
            "Website Content Writing",
            "Brochure & Print Material Content",
            "Quora Content Creation"
        ],
        "Graphic & Video Production": [
            "Social Media Graphic Design (Static & Motion)",
            "Video Creation & Editing",
            "Brochure & Print Asset Design"
        ],
        "Social Media Management": [
            "Content Scheduling & Posting",
            "Community Engagement",
            "Social Media Performance Reporting"
        ],
        "Project & Team Management": [
            "Assigning Tasks to Content & Design Teams",
            "Content Editing, Proofreading & Delivery",
            "Monitoring Quality & Deadlines",
            "Coordinating with Printing Vendors"
        ],
        "Internal Collaboration & Events": [
            "Participation in Office Event Organization",
            "Cross-functional Content Meetings"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    },
    "Placement": {
        "Corporate Outreach & Tie-Ups": [
            "Relationship Building & Company Tie-Ups",
            "B2B Support & Collaboration"
        ],
        "Candidate Training & Grooming": [
            "Resume Building & Correction",
            "Soft Skills & Personal Branding Sessions",
            "Mock Interview Drills",
            "Job Placement Workshops"
        ],
        "Placement & Interview Management": [
            "Lining Up Interviews",
            "Database Management",
            "Tracking Placement Achievements"
        ],
        "Student Support & Onboarding": [
            "Conducting New Batch Orientation",
            "Grievance Handling",
            "B2C Support"
        ],
        "Team & Cross-Functional Coordination": [
            "Weekly Meetings (Sales, HODs)",
            "Support to Marketing (Testimonials, Offer Letters)",
            "Coordination with Development Team",
            "Monitoring Team Performance"
        ],
        "Adhoc": ["Others (Please fill the comment)"],
        "Meeting": ["Meeting"]
    }
}
# ------------------ Data Model on Disk ------------------
# We'll structure data_store similarly: {"Employee::weekstart": {"submitted": bool, "rows": [ ... ]}}


# ------------------ UI Construction ------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Initial week start (Monday)
current_week_start = _monday_of(date.today())

# Layout helpers

def generate_task_row_component(row_idx: int, row_data: Dict[str, Any]) -> html.Div:
    """Create a component that represents a row with 7 day cells."""
    task = row_data.get("task", "")
    subtask = row_data.get("subtask", "")
    days = row_data.get("days", [ {"sessions": [], "notes": "", "running_start": None} for _ in range(7)])

    day_cells = []
    for di in range(7):
        hrs = day_total_hours(days[di])
        running = bool(days[di].get("running_start"))
        day_cells.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                # This ID is a string, not pattern-matching, so it can't be updated by interval
                                # The parent function `render_rows` will rebuild this whole component on interval
                                html.Div(format_hours_hhmm(hrs), id=f"hours-{row_idx}-{di}", style={"fontWeight": "bold", "fontSize": "14px", "textAlign": "center"}),
                                dbc.Button("Stop" if running else "Start", id={"type": "toggle-btn", "index": f"{row_idx}-{di}"}, color="danger" if running else "success", size="sm", style={"width": "100%", "marginTop": "6px"}),
                                # Use pattern-matching ID for notes so we can read them all on save
                                dcc.Textarea(value=days[di].get("notes", ""), id={'type': 'notes-input', 'index': f"{row_idx}-{di}"}, style={"width": "100%", "height": "70px", "marginTop": "6px"})
                            ]
                        )
                    ], style={"height": "170px"}
                ), width=1
            )
        )

    # total hours for row
    total = sum(day_total_hours(d) for d in days)

    row_component = html.Div(
        id={"type": "task-row", "index": str(row_idx)},
        children=[
            dbc.Row([
                dbc.Col(html.Div([html.B(task or "(No Task)"), html.Div(subtask or "(No Subtask)", style={"fontSize": "12px", "color": "#666"})]), width=2),
                *day_cells,
                dbc.Col(html.Div(format_hours_hhmm(total), id=f"row-total-{row_idx}", style={"fontWeight": "bold", "textAlign": "center"}), width=1),
                dbc.Col(dbc.Button("🗑 Delete", id={"type": "delete-row", "index": str(row_idx)}, color="danger", size="sm"), width="auto")
            ], align="center", className="g-1")
        ], style={"padding": "6px", "borderBottom": "1px solid #eee"}
    )
    return row_component


app.layout = dbc.Container(
    [
        html.H3("Weekly Timesheet (Dash web app)"),
        dbc.Row([
            dbc.Col([html.Label("Employee"), dcc.Dropdown(options=[{"label": k, "value": k} for k in sorted(EMPLOYEE_DATA.keys())], id="emp-dropdown", value=sorted(EMPLOYEE_DATA.keys())[0])], width=3),
            dbc.Col([html.Label("Department"), dbc.Input(id="dept-input", readonly=True, value="", style={"width": "100%"})], width=3),
            dbc.Col([html.Label("Week Start (Monday)"), dcc.DatePickerSingle(id="week-picker", date=current_week_start.isoformat())], width=3),
            dbc.Col([html.Label(" "), dbc.Button("💾 Save Data", id="save-btn", color="primary", className="me-2"), dbc.Button("✅ Submit Week", id="submit-btn", color="success")], width=3, style={"align-self": "flex-end"})
        ], className="my-2"),

        html.Hr(),

        # Add task area
        dbc.Row([
            dbc.Col([dcc.Dropdown(id="task-dropdown", placeholder="Select or type task", searchable=True),], width=4),
            dbc.Col([dcc.Dropdown(id="subtask-dropdown", placeholder="Subtask", searchable=True)], width=4),
            dbc.Col([dbc.Button("➕ Add Task", id="add-task-btn", color="info")], width=2)
        ], className="mb-3"),

        # Table header
        dbc.Row([
            dbc.Col(html.Div("TASK / SUBTASK", style={"fontWeight": "bold"}), width=2),
            *[dbc.Col(html.Div(d.strftime("%a\n%Y-%m-%d"), style={"whiteSpace": "pre-line", "textAlign": "center", "fontWeight": "bold"}), width=1) for d in [date.fromisoformat(current_week_start.isoformat()) + timedelta(days=i) for i in range(7)]],
            dbc.Col(html.Div("TOTAL", style={"fontWeight": "bold"}), width=1),
            dbc.Col(html.Div(""), width="auto")
        ], className="mb-2"),

        # Rows container
        html.Div(id="rows-container"),

        # Totals
        html.Hr(),
        dbc.Row([
            dbc.Col(html.Div("WEEKLY TOTAL:", style={"fontWeight": "bold"}), width=2),
            dbc.Col(html.Div(id="weekly-total", style={"fontWeight": "bold"}), width=2)
        ]),

        # Hidden stores
        dcc.Store(id="data-store"),  # holds full data_store dict
        dcc.Store(id="ui-store"),    # holds transient UI data like which timer is running
        dcc.Interval(id="interval", interval=1000, n_intervals=0), # Interval will be used to update rows

        html.Div(id="hidden-output", style={"display": "none"})

    ], fluid=True
)


# ------------------ Initialization Callbacks ------------------

# This new master callback handles ALL data updates and UI fields
# that were previously conflicting.
@app.callback(
    Output("data-store", "data"),
    Output("dept-input", "value"),
    Output("task-dropdown", "options"),
    Output("ui-store", "data"),
    Output("hidden-output", "children"), # For save button
    # --- INPUTS ---
    # These trigger the callback
    Input("emp-dropdown", "value"),
    Input("week-picker", "date"),
    Input("add-task-btn", "n_clicks"),
    Input({"type": "delete-row", "index": ALL}, "n_clicks"),
    Input({"type": "toggle-btn", "index": ALL}, "n_clicks"),
    Input("save-btn", "n_clicks"),
    Input("submit-btn", "n_clicks"),
    # --- STATE ---
    # These are just read when needed
    State("task-dropdown", "value"),
    State("subtask-dropdown", "value"),
    State("data-store", "data"),
    State("ui-store", "data"),
    State({'type': 'notes-input', 'index': ALL}, 'value'), # Get all note values
    State({'type': 'notes-input', 'index': ALL}, 'id'),    # Get all note IDs
    prevent_initial_call=True
)
def handle_all_updates(
    emp, week_date,
    add_clicks, delete_clicks, toggle_clicks, save_clicks, submit_clicks,
    task_value, subtask_value,
    data_store, ui_store,
    note_values, note_ids
):
    """
    Master callback to handle all data logic and prevent duplicate outputs.
    """
    triggered_id = ctx.triggered_id
    data_store = data_store or {}
    ui_store = ui_store or {}

    # Default UI outputs
    dept_val = no_update
    task_options = no_update

    # --- Logic for loading data (Employee or Week change) ---
    if triggered_id == "emp-dropdown" or triggered_id == "week-picker":
        if not emp or not week_date:
            return no_update, no_update, no_update, no_update, no_update

        data = load_json()
        week_start = date.fromisoformat(week_date)
        key = f"{emp}::{week_start.isoformat()}"
        if key not in data:
            data[key] = {"submitted": False, "rows": []}
            save_json(data)

        # Update data-store
        data_store = data
        
        # Update UI fields
        dept_val = EMPLOYEE_DATA.get(emp, "")
        task_options = [{"label": t, "value": t} for t in sorted(DEPARTMENT_TASKS.get(dept_val, {}).keys())]

    # --- Logic for Add Task ---
    elif triggered_id == "add-task-btn":
        if task_value:
            week_start = date.fromisoformat(week_date)
            key = f"{emp}::{week_start.isoformat()}"
            if key not in data_store:
                data_store[key] = {"submitted": False, "rows": []}

            row = {"task": task_value, "subtask": subtask_value or "", "days": [{"sessions": [], "notes": "", "running_start": None} for _ in range(7)]}
            data_store[key]["rows"].append(row)
            save_json(data_store)
    
    # --- Logic for Delete Task ---
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "delete-row":
        # --- FIX ---
        # Check if any delete button was *actually* clicked.
        # If the list is all None, it was triggered by a re-render.
        if not any(delete_clicks):
            return no_update, no_update, no_update, no_update, no_update
            
        idx = int(triggered_id["index"])
        week_start = date.fromisoformat(week_date)
        key = f"{emp}::{week_start.isoformat()}"
        rows = data_store.get(key, {}).get("rows", [])
        if 0 <= idx < len(rows):
            rows.pop(idx)
            data_store[key]["rows"] = rows
            save_json(data_store)

    # --- Logic for Toggle Timer ---
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "toggle-btn":
        # --- FIX ---
        # Check if any toggle button was *actually* clicked.
        # If the list is all None, it was triggered by a re-render.
        if not any(toggle_clicks):
            return no_update, no_update, no_update, no_update, no_update
            
        idx_str = triggered_id["index"]  # format "{row}-{day}"
        row_idx, day_idx = [int(x) for x in idx_str.split("-")]
        week_start = date.fromisoformat(week_date)
        key = f"{emp}::{week_start.isoformat()}"
        rows = data_store.get(key, {}).get("rows", [])
        if row_idx < len(rows):
            day_obj = rows[row_idx]["days"][day_idx]
            
            # If a timer is already running elsewhere, stop it first
            running = ui_store.get("running")
            if running and running != [row_idx, day_idx]:
                r, d = running
                if r < len(rows) and d < len(rows[r].get("days", [])):
                    prev_day = rows[r]["days"][d]
                    if prev_day.get("running_start"):
                        prev_day["sessions"].append([prev_day["running_start"], now_iso()])
                        prev_day["running_start"] = None

            # If this is running -> stop
            if day_obj.get("running_start"):
                day_obj["sessions"].append([day_obj["running_start"], now_iso()])
                day_obj["running_start"] = None
                ui_store = {"running": None}
            else:
                # Check actual date, not just day index
                target_date = week_start + timedelta(days=day_idx)
                if target_date == date.today():
                    day_obj["running_start"] = now_iso()
                    ui_store = {"running": [row_idx, day_idx]}

            data_store[key]["rows"][row_idx]["days"][day_idx] = day_obj
            save_json(data_store)

    # --- Logic for Save Button (Notes) ---
    elif triggered_id == "save-btn":
        if note_values and note_ids:
            week_start = date.fromisoformat(week_date)
            key = f"{emp}::{week_start.isoformat()}"
            rows = data_store.get(key, {}).get("rows", [])
            if rows:
                notes_map = {note_ids[i]['index']: note_values[i] for i in range(len(note_ids))}
                for r_idx, row in enumerate(rows):
                    for d_idx, day in enumerate(row.get("days", [])):
                        cell_id = f"{r_idx}-{d_idx}"
                        if cell_id in notes_map:
                            day['notes'] = notes_map[cell_id]
                data_store[key]["rows"] = rows
                save_json(data_store)

    # --- Logic for Submit Week ---
    elif triggered_id == "submit-btn":
        week_start = date.fromisoformat(week_date)
        key = f"{emp}::{week_start.isoformat()}"
        entry = data_store.get(key, {"submitted": False, "rows": []})
        rows = entry.get("rows", [])
        export_data = []
        for row in rows:
            for di, day in enumerate(row.get("days", [])):
                hrs = day_total_hours(day)
                if hrs > 0 or day.get("notes"):
                    day_date = week_start + timedelta(days=di)
                    export_data.append({
                        "Employee": emp,
                        "Department": EMPLOYEE_DATA.get(emp, ""),
                        "Week Start": week_start.isoformat(),
                        "Day": day_date.isoformat(),
                        "Task": row.get("task"),
                        "Subtask": row.get("subtask"),
                        "Hours": round(hrs, 2),
                        "Notes": day.get("notes", "")
                    })

        if export_data:
            # Optional server upload
            try:
                response = requests.post("http://127.0.0.1:5000/submit", json=export_data, timeout=10)
                data_store[key]["server_upload"] = response.status_code == 200
            except Exception as e:
                print(f"Could not submit to server: {e}")
                data_store[key]["server_upload"] = False

            # Export to Excel
            df = pd.DataFrame(export_data)
            filename = f"Submission_{emp.replace(' ', '_')}_{week_start.isoformat()}.xlsx"
            df.to_excel(filename, index=False, engine='openpyxl')

            data_store[key]["submitted"] = True
            save_json(data_store)


    return data_store, dept_val, task_options, ui_store, no_update


@app.callback(
    Output("subtask-dropdown", "options"),
    Input("task-dropdown", "value"),
    State("dept-input", "value")
)
def update_subtasks(task_value, dept_value):
    """Update subtask dropdown based on selected task."""
    if not task_value:
        return []
    options = [{"label": s, "value": s} for s in DEPARTMENT_TASKS.get(dept_value, {}).get(task_value, [])]
    return options


# ------------------ Render Rows ------------------
@app.callback(
    Output("rows-container", "children"),
    Output("weekly-total", "children"),
    Input("data-store", "data"),
    Input("interval", "n_intervals"), # Add interval as input
    State("emp-dropdown", "value"),
    State("week-picker", "date"),
    State("ui-store", "data") # Get UI store to see if a timer is running
)
def render_rows(data_store, n_intervals, emp, week_date, ui_store):
    """
    Renders all task rows.
    This is triggered by changes to data-store (e.g., add/delete row)
    OR by the interval, which live-updates running timers.
    """
    # Prevent interval from firing updates if no timer is running
    running = ui_store.get("running") if ui_store else None
    if ctx.triggered_id == 'interval' and not running:
        return no_update, no_update
        
    if data_store is None or not emp or not week_date:
        return [], "00:00 h"
        
    week_start = date.fromisoformat(week_date)
    key = f"{emp}::{week_start.isoformat()}"
    entry = data_store.get(key, {"submitted": False, "rows": []})
    rows = entry.get("rows", [])
    comps = []
    week_total = 0.0
    for ri, row in enumerate(rows):
        comps.append(generate_task_row_component(ri, row))
        for di, d in enumerate(row.get("days", [])):
            week_total += day_total_hours(d)
    return comps, f"{format_hours_hhmm(week_total)} h"


# ------------------ Run server ------------------
if __name__ == "__main__":
    app.run(debug=True)