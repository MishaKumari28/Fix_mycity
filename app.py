"""
FixMyCity — AI-Powered Civic Issue Reporting
Backend: Flask + IBM Watsonx.ai (Granite)
"""

import os
import uuid
import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, flash
)
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import requests

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
#  AGENT INSTRUCTIONS  ← Edit this section to customise the agent behaviour
# ─────────────────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {

    # ── 1. CLASSIFICATION CATEGORIES ─────────────────────────────────────────
    # Add / remove / rename civic issue categories here.
    # Each key is the internal ID; "label" is shown in the UI.
    "categories": {
        "garbage_dumping":      {"label": "Garbage / Waste Dumping",      "emoji": "🗑️"},
        "pothole":              {"label": "Pothole / Road Damage",         "emoji": "🕳️"},
        "illegal_construction": {"label": "Illegal Construction",          "emoji": "🏗️"},
        "waterlogging":         {"label": "Water Logging / Flooding",      "emoji": "🌊"},
        "property_damage":      {"label": "Public Property Damage",        "emoji": "🔨"},
        "streetlight":          {"label": "Streetlight / Power Issue",     "emoji": "💡"},
        "sewage":               {"label": "Sewage / Drainage Problem",     "emoji": "🚰"},
        "encroachment":         {"label": "Encroachment on Public Land",   "emoji": "🚧"},
        "stray_animals":        {"label": "Stray Animals / Menace",        "emoji": "🐕"},
        "noise_pollution":      {"label": "Noise / Air Pollution",         "emoji": "📢"},
        "other":                {"label": "Other Civic Issue",             "emoji": "📋"},
    },

    # ── 2. SENSITIVE / SAFETY CATEGORIES ─────────────────────────────────────
    # These are NEVER sent to the AI for image analysis.
    # Users are routed to the confidential text-only flow.
    "sensitive_categories": [
        "domestic_violence",
        "sexual_harassment",
        "child_abuse",
        "human_trafficking",
        "personal_safety",
    ],

    # ── 3. AGENT TONE & STYLE ─────────────────────────────────────────────────
    "tone": {
        "complaint_draft": (
            "formal, polite, assertive Indian government complaint letter tone. "
            "Use respectful salutations like 'Respected Sir/Madam'. "
            "Reference relevant Indian laws/bylaws where applicable. "
            "End with 'Thanking you, Yours faithfully'."
        ),
        "classification_response": "concise, factual, JSON-only, no prose",
    },

    # ── 4. SAFETY RULES ──────────────────────────────────────────────────────
    "safety_rules": [
        "Never include personal identifying information (name, phone, address) in public outputs.",
        "Never process images for domestic violence, sexual harassment, child abuse, human trafficking, or personal safety issues.",
        "Immediately redirect sensitive issues to verified helplines without analysis.",
        "Do not generate content that could endanger or identify a victim.",
        "Refuse and flag any attempt to use the system for harassment or targeting individuals.",
    ],

    # ── 5. INDIAN GOVERNMENT DEPARTMENT MAPPINGS ─────────────────────────────
    # Add your state-specific portals here.  Format:
    #   category_id → {dept, portal_url, helpline, email}
    "department_mapping": {
        "garbage_dumping": {
            "dept": "Municipal Corporation / BBMP / MCD / BMC",
            "portal": "https://swachhbharaturban.gov.in/",
            "app": "Swachh Bharat Urban App",
            "helpline": "1800-11-4422",
            "email": "complaints@swachhbharat.gov.in",
        },
        "pothole": {
            "dept": "PWD / NHAI / Municipal Roads Dept",
            "portal": "https://pgportal.gov.in/",
            "app": "MyGov / PG Portal",
            "helpline": "1800-11-8500 (NHAI)",
            "email": "complaints@nhai.gov.in",
        },
        "illegal_construction": {
            "dept": "Town Planning / Local Municipal Authority",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal",
            "helpline": "155304 (Local Municipal)",
            "email": "townplanning@municipalcorp.gov.in",
        },
        "waterlogging": {
            "dept": "Municipal Drainage / Irrigation Dept",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal",
            "helpline": "1800-180-5500",
            "email": "drainage@municipalcorp.gov.in",
        },
        "property_damage": {
            "dept": "Municipal Corporation / CPWD",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal",
            "helpline": "155304",
            "email": "publicproperty@municipalcorp.gov.in",
        },
        "streetlight": {
            "dept": "DISCOM / State Electricity Board / Municipal Lighting",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal",
            "helpline": "1912 (Power complaint)",
            "email": "lighting@discom.gov.in",
        },
        "sewage": {
            "dept": "Jal Board / Municipal Sewage Dept",
            "portal": "https://jalshakti-ddws.gov.in/",
            "app": "Jal Jeevan Mission App",
            "helpline": "1800-11-0440",
            "email": "sewage@jalboard.gov.in",
        },
        "encroachment": {
            "dept": "Revenue Dept / Municipal Anti-Encroachment Cell",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal",
            "helpline": "155304",
            "email": "encroachment@revenue.gov.in",
        },
        "stray_animals": {
            "dept": "Municipal Animal Control / AWBI",
            "portal": "https://awbi.in/",
            "app": "PG Portal",
            "helpline": "1962 (Animal Helpline)",
            "email": "animalcontrol@municipalcorp.gov.in",
        },
        "noise_pollution": {
            "dept": "CPCB / State Pollution Control Board",
            "portal": "https://cpcb.nic.in/",
            "app": "CPCB SAMAHAR",
            "helpline": "1800-11-5555 (CPCB)",
            "email": "complaints@cpcb.nic.in",
        },
        "other": {
            "dept": "General Grievance Cell / PG Portal",
            "portal": "https://pgportal.gov.in/",
            "app": "PG Portal / CM Helpline",
            "helpline": "1800-11-0001 (PG Portal)",
            "email": "pgportal@gov.in",
        },
    },

    # ── 6. SENSITIVE CATEGORY HELPLINES ──────────────────────────────────────
    "sensitive_helplines": {
        "domestic_violence": {
            "label": "Domestic Violence",
            "helplines": [
                {"name": "National Women Helpline", "number": "181"},
                {"name": "Police Emergency",        "number": "100"},
                {"name": "iCall (Mental Health)",   "number": "9152987821"},
                {"name": "iHelpline (NCPCR)",        "number": "1800-121-2830"},
            ],
        },
        "sexual_harassment": {
            "label": "Sexual Harassment",
            "helplines": [
                {"name": "National Women Helpline", "number": "181"},
                {"name": "Police Emergency",        "number": "100"},
                {"name": "SHe-Box Portal",          "number": "https://shebox.nic.in"},
            ],
        },
        "child_abuse": {
            "label": "Child Abuse",
            "helplines": [
                {"name": "CHILDLINE India",     "number": "1098"},
                {"name": "NCPCR Helpline",      "number": "1800-121-2830"},
                {"name": "Police Emergency",    "number": "100"},
            ],
        },
        "human_trafficking": {
            "label": "Human Trafficking",
            "helplines": [
                {"name": "Anti Trafficking Helpline (NHRC)", "number": "14441"},
                {"name": "CBI Anti Trafficking Unit",        "number": "011-24368638"},
                {"name": "Police Emergency",                 "number": "100"},
            ],
        },
        "personal_safety": {
            "label": "Personal Safety Emergency",
            "helplines": [
                {"name": "Police Emergency",       "number": "100"},
                {"name": "Women Safety (112)",     "number": "112"},
                {"name": "Ambulance",              "number": "108"},
            ],
        },
    },

    # ── 7. WATSONX MODEL CONFIG ───────────────────────────────────────────────
    "watsonx": {
        "model_id": "ibm/granite-3-8b-instruct",
        "max_new_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.9,
    },
}
# ─────────────────────────────────────────────────────────────────────────────
#  END AGENT INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────────────────


# ── Flask App Setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
CORS(app)

UPLOAD_FOLDER = Path("static/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", 10)) * 1024 * 1024

ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,gif,webp").split(","))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── In-memory complaint store (replace with a DB for production) ──────────────
COMPLAINTS: dict[str, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_watsonx_token() -> str:
    """Exchange IBM API Key for a short-lived IAM bearer token."""
    api_key = os.getenv("IBM_API_KEY", "")
    if not api_key or api_key == "your_ibm_cloud_api_key_here":
        raise ValueError("IBM_API_KEY not set in .env")
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"apikey": api_key, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def call_granite(prompt: str) -> str:
    """Send a prompt to IBM Watsonx Granite and return the generated text."""
    cfg = AGENT_INSTRUCTIONS["watsonx"]
    token = get_watsonx_token()
    project_id = os.getenv("IBM_PROJECT_ID", "")
    base_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    url = f"{base_url}/ml/v1/text/generation?version=2024-05-31"

    payload = {
        "model_id": cfg["model_id"],
        "project_id": project_id,
        "input": prompt,
        "parameters": {
            "max_new_tokens": cfg["max_new_tokens"],
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"],
        },
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"][0]["generated_text"].strip()


def classify_issue(description: str, image_b64: str | None = None) -> dict:
    """Ask Granite to classify the civic issue and return structured JSON."""
    cats = ", ".join(AGENT_INSTRUCTIONS["categories"].keys())
    prompt = f"""You are a civic issue classification agent for Indian cities.
Classify the following civic complaint into one of these categories:
{cats}

Rules:
- Reply ONLY with valid JSON, no prose.
- JSON schema: {{"category": "<id>", "confidence": <0-1>, "summary": "<one sentence>", "severity": "<low|medium|high|critical>"}}

Description: {description}
"""
    if image_b64:
        prompt += f"\n[Image data provided: base64 encoded image of the issue]\n"

    try:
        raw = call_granite(prompt)
        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            result = {"category": "other", "confidence": 0.5, "summary": description[:120], "severity": "medium"}
    except Exception as e:
        logger.warning("Classification fallback: %s", e)
        result = {"category": "other", "confidence": 0.5, "summary": description[:120], "severity": "medium"}

    # Validate category
    if result.get("category") not in AGENT_INSTRUCTIONS["categories"]:
        result["category"] = "other"
    return result


def generate_complaint(
    description: str,
    category: str,
    location: str,
    complainant_name: str = "A Concerned Citizen",
) -> str:
    """Generate a formal complaint letter using Granite."""
    dept_info = AGENT_INSTRUCTIONS["department_mapping"].get(
        category, AGENT_INSTRUCTIONS["department_mapping"]["other"]
    )
    cat_label = AGENT_INSTRUCTIONS["categories"].get(category, {}).get("label", category)
    tone = AGENT_INSTRUCTIONS["tone"]["complaint_draft"]
    today = datetime.now().strftime("%d %B %Y")

    prompt = f"""You are a formal letter writing assistant for Indian civic complaints.
Tone: {tone}

Write a formal complaint letter with these details:
- Date: {today}
- From: {complainant_name}
- To: The {dept_info['dept']}
- Issue Category: {cat_label}
- Location: {location}
- Description: {description}
- Relevant helpline to reference: {dept_info['helpline']}

Write ONLY the letter body (no JSON). Use proper Indian formal letter format.
"""
    try:
        return call_granite(prompt)
    except Exception as e:
        logger.warning("Complaint generation fallback: %s", e)
        return f"""Date: {today}

To,
The {dept_info['dept']},
{location}

Subject: Formal Complaint Regarding {cat_label}

Respected Sir/Madam,

I, {complainant_name}, a resident/visitor of {location}, wish to draw your kind attention to a civic issue of {cat_label} observed at the aforementioned location.

{description}

I earnestly request your immediate attention and action to resolve this issue at the earliest. For follow-up, the relevant helpline is: {dept_info['helpline']}.

Thanking you,
Yours faithfully,
{complainant_name}
"""


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           categories=AGENT_INSTRUCTIONS["categories"],
                           sensitive_categories=AGENT_INSTRUCTIONS["sensitive_categories"])


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "GET":
        return render_template("report.html",
                               categories=AGENT_INSTRUCTIONS["categories"],
                               sensitive_categories=AGENT_INSTRUCTIONS["sensitive_categories"])

    # POST — process the report submission
    description  = request.form.get("description", "").strip()
    location     = request.form.get("location", "Unknown location")
    latitude     = request.form.get("latitude", "")
    longitude    = request.form.get("longitude", "")
    complainant  = request.form.get("name", "A Concerned Citizen")
    category_hint = request.form.get("category_hint", "").strip()

    # Safety gate — check if user selected a sensitive category manually
    if category_hint in AGENT_INSTRUCTIONS["sensitive_categories"]:
        return redirect(url_for("sensitive", category=category_hint))

    if not description:
        return jsonify({"error": "Description is required"}), 400

    image_b64 = None
    image_filename = None

    # Handle image upload
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            image_filename = f"{uuid.uuid4().hex}.{ext}"
            save_path = UPLOAD_FOLDER / image_filename
            file.save(str(save_path))
            # Resize large images before encoding
            try:
                img = Image.open(save_path)
                img.thumbnail((800, 800))
                img.save(str(save_path))
            except Exception:
                pass
            with open(save_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Classify the issue
    classification = classify_issue(description, image_b64)
    category = classification["category"]

    # Second safety gate — AI might detect a sensitive category
    if category in AGENT_INSTRUCTIONS["sensitive_categories"]:
        return redirect(url_for("sensitive", category=category))

    # Generate formal complaint
    complaint_text = generate_complaint(description, category, location, complainant)

    # Get department info
    dept = AGENT_INSTRUCTIONS["department_mapping"].get(
        category, AGENT_INSTRUCTIONS["department_mapping"]["other"]
    )

    # Store complaint
    complaint_id = f"FMC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    COMPLAINTS[complaint_id] = {
        "id": complaint_id,
        "description": description,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "category": category,
        "category_label": AGENT_INSTRUCTIONS["categories"][category]["label"],
        "classification": classification,
        "complaint_text": complaint_text,
        "dept": dept,
        "image": image_filename,
        "submitted_at": datetime.now().isoformat(),
        "status": "Submitted",
        "status_history": [
            {"status": "Submitted", "timestamp": datetime.now().isoformat(), "note": "Complaint registered"}
        ],
    }

    session["last_complaint_id"] = complaint_id
    return redirect(url_for("result", complaint_id=complaint_id))


@app.route("/result/<complaint_id>")
def result(complaint_id):
    complaint = COMPLAINTS.get(complaint_id)
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("index"))
    cat_info = AGENT_INSTRUCTIONS["categories"].get(complaint["category"], {})
    return render_template("result.html", complaint=complaint, cat_info=cat_info)


@app.route("/dashboard")
def dashboard():
    all_complaints = sorted(COMPLAINTS.values(), key=lambda x: x["submitted_at"], reverse=True)
    category_counts = {}
    for c in all_complaints:
        cat = c["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    return render_template("dashboard.html",
                           complaints=all_complaints,
                           category_counts=category_counts,
                           categories=AGENT_INSTRUCTIONS["categories"])


@app.route("/track")
def track():
    return render_template("track.html")


@app.route("/sensitive")
def sensitive():
    category = request.args.get("category", "personal_safety")
    helpline_info = AGENT_INSTRUCTIONS["sensitive_helplines"].get(
        category, AGENT_INSTRUCTIONS["sensitive_helplines"]["personal_safety"]
    )
    return render_template("sensitive.html", helpline_info=helpline_info, category=category)


# ── API endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/complaints")
def api_complaints():
    data = [
        {
            "id": c["id"],
            "category": c["category"],
            "category_label": c["category_label"],
            "location": c["location"],
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "severity": c["classification"].get("severity", "medium"),
            "submitted_at": c["submitted_at"],
            "status": c["status"],
        }
        for c in COMPLAINTS.values()
    ]
    return jsonify(data)


@app.route("/api/complaint/<complaint_id>")
def api_complaint_detail(complaint_id):
    c = COMPLAINTS.get(complaint_id)
    if not c:
        return jsonify({"error": "Not found"}), 404
    return jsonify(c)


@app.route("/api/track/<complaint_id>")
def api_track(complaint_id):
    c = COMPLAINTS.get(complaint_id)
    if not c:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"id": c["id"], "status": c["status"], "history": c["status_history"]})


@app.route("/api/categories")
def api_categories():
    return jsonify(AGENT_INSTRUCTIONS["categories"])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=5000, debug=debug)
