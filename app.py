import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from anthropic import Anthropic
import resend
from dotenv import load_dotenv

# Load API keys
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")
client = Anthropic()

app = Flask(__name__)
CORS(app)

# File to store leads
LEADS_FILE = "leads.json"

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def generate_email(athlete_info, coach_info):
    prompt = f"""You are a recruiting expert helping high school athletes get recruited to play college sports.

Write a personalized, compelling email from this athlete to a college coach.

ATHLETE INFO:
- Name: {athlete_info['name']}
- Sport: {athlete_info['sport']}
- Position: {athlete_info['position']}
- High School: {athlete_info['school']}
- Graduation Year: {athlete_info['grad_year']}
- GPA: {athlete_info['gpa']}
- Stats: {athlete_info['stats']}
- Highlights Link: {athlete_info.get('highlights', 'Not provided')}

COACH INFO:
- Coach Name: {coach_info['coach_name']}
- College: {coach_info['college']}

Write a professional but personable email that:
1. Has a clear, attention-grabbing subject line
2. Introduces the athlete briefly
3. Highlights key stats and achievements
4. Expresses genuine interest in the specific program
5. Includes a call to action
6. Keeps it concise (under 200 words)

Format your response as JSON:
{{"subject": "your subject line", "body": "your email body"}}
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response = message.content[0].text
    
    try:
        # Try to parse as JSON
        email_data = json.loads(response)
        return email_data['subject'], email_data['body']
    except:
        # Fallback parsing
        return "Recruiting Inquiry", response

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/generate-email', methods=['POST'])
def generate_email_route():
    data = request.json
    
    athlete_info = data.get('athlete')
    coach_info = data.get('coach')
    
    if not athlete_info or not coach_info:
        return jsonify({"error": "Missing athlete or coach info"}), 400
    
    subject, body = generate_email(athlete_info, coach_info)
    
    return jsonify({
        "subject": subject,
        "body": body
    })

@app.route('/send-email', methods=['POST'])
def send_email_route():
    data = request.json
    
    to_email = data.get('to_email')
    subject = data.get('subject')
    body = data.get('body')
    reply_to = data.get('reply_to')
    athlete_info = data.get('athlete')
    coach_info = data.get('coach')
    
    try:
        params = {
            "from": "RecruitEdge <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "text": body,
            "reply_to": reply_to
        }
        email = resend.Emails.send(params)
        
        # Save lead
        leads = load_leads()
        lead = {
            "id": len(leads) + 1,
            "athlete_name": athlete_info['name'],
            "coach_name": coach_info['coach_name'],
            "college": coach_info['college'],
            "coach_email": to_email,
            "status": "sent",
            "date_sent": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "notes": ""
        }
        leads.append(lead)
        save_leads(leads)
        
        return jsonify({"success": True, "lead_id": lead['id']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/leads', methods=['GET'])
def get_leads():
    leads = load_leads()
    return jsonify(leads)

@app.route('/leads/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    data = request.json
    leads = load_leads()
    
    for lead in leads:
        if lead['id'] == lead_id:
            lead['status'] = data.get('status', lead['status'])
            lead['notes'] = data.get('notes', lead['notes'])
            save_leads(leads)
            return jsonify(lead)
    
    return jsonify({"error": "Lead not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
