import os
import json
from datetime import datetime
from anthropic import Anthropic
import resend
from dotenv import load_dotenv

# Load API keys
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")
client = Anthropic()

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
- Email: {coach_info['email']}

Write a professional but personable email that:
1. Has a clear, attention-grabbing subject line
2. Introduces the athlete briefly
3. Highlights key stats and achievements
4. Expresses genuine interest in the specific program
5. Includes a call to action
6. Keeps it concise (under 200 words)

Format your response as:
SUBJECT: [subject line]
BODY:
[email body]
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response = message.content[0].text
    
    # Parse subject and body
    lines = response.strip().split("\n")
    subject = ""
    body_lines = []
    in_body = False
    
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    
    body = "\n".join(body_lines).strip()
    return subject, body

def send_email(to_email, subject, body, athlete_email):
    try:
        params = {
            "from": "RecruitEdge <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "text": body,
            "reply_to": athlete_email
        }
        email = resend.Emails.send(params)
        return True, email
    except Exception as e:
        return False, str(e)

def add_lead(athlete_info, coach_info, status="sent"):
    leads = load_leads()
    lead = {
        "id": len(leads) + 1,
        "athlete_name": athlete_info['name'],
        "coach_name": coach_info['coach_name'],
        "college": coach_info['college'],
        "coach_email": coach_info['email'],
        "status": status,
        "date_sent": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes": ""
    }
    leads.append(lead)
    save_leads(leads)
    return lead

def view_leads():
    leads = load_leads()
    if not leads:
        print("\n📭 No leads yet!\n")
        return
    
    print("\n" + "="*60)
    print("📊 YOUR LEADS")
    print("="*60)
    
    for lead in leads:
        status_emoji = {"sent": "📤", "replied": "✅", "no_response": "⏳", "rejected": "❌"}.get(lead['status'], "❓")
        print(f"\n{status_emoji} Lead #{lead['id']}")
        print(f"   Coach: {lead['coach_name']} ({lead['college']})")
        print(f"   Email: {lead['coach_email']}")
        print(f"   Status: {lead['status']}")
        print(f"   Sent: {lead['date_sent']}")
        if lead['notes']:
            print(f"   Notes: {lead['notes']}")
    print("\n" + "="*60 + "\n")

def update_lead_status():
    leads = load_leads()
    if not leads:
        print("\n📭 No leads to update!\n")
        return
    
    view_leads()
    try:
        lead_id = int(input("Enter lead # to update: "))
        lead = next((l for l in leads if l['id'] == lead_id), None)
        
        if not lead:
            print("❌ Lead not found!")
            return
        
        print("\nStatus options: sent, replied, no_response, rejected")
        new_status = input("New status: ").strip().lower()
        notes = input("Add notes (optional): ").strip()
        
        lead['status'] = new_status
        if notes:
            lead['notes'] = notes
        
        save_leads(leads)
        print("✅ Lead updated!")
    except ValueError:
        print("❌ Invalid input!")

def get_athlete_info():
    print("\n" + "="*60)
    print("🏆 ATHLETE INFORMATION")
    print("="*60 + "\n")
    
    return {
        "name": input("Athlete's Full Name: ").strip(),
        "email": input("Athlete's Email: ").strip(),
        "sport": input("Sport: ").strip(),
        "position": input("Position: ").strip(),
        "school": input("High School: ").strip(),
        "grad_year": input("Graduation Year: ").strip(),
        "gpa": input("GPA: ").strip(),
        "stats": input("Key Stats (comma separated): ").strip(),
        "highlights": input("Highlights Video Link (optional): ").strip()
    }

def get_coach_info():
    print("\n" + "="*60)
    print("🎓 COACH INFORMATION")
    print("="*60 + "\n")
    
    return {
        "coach_name": input("Coach's Name: ").strip(),
        "college": input("College/University: ").strip(),
        "email": input("Coach's Email: ").strip()
    }

def main():
    print("\n" + "="*60)
    print("⚡ RECRUITEDGE AI ⚡")
    print("College Athletic Recruiting Assistant")
    print("="*60)
    
    athlete_info = None
    
    while True:
        print("\n📋 MENU:")
        print("1. Enter/Update Athlete Info")
        print("2. Send Outreach Email to Coach")
        print("3. View All Leads")
        print("4. Update Lead Status")
        print("5. Exit")
        
        choice = input("\nChoose option (1-5): ").strip()
        
        if choice == "1":
            athlete_info = get_athlete_info()
            print("\n✅ Athlete info saved!")
            
        elif choice == "2":
            if not athlete_info:
                print("\n⚠️  Please enter athlete info first (Option 1)")
                continue
            
            coach_info = get_coach_info()
            
            print("\n⏳ Generating personalized email...")
            subject, body = generate_email(athlete_info, coach_info)
            
            print("\n" + "="*60)
            print("📧 GENERATED EMAIL")
            print("="*60)
            print(f"\nTO: {coach_info['email']}")
            print(f"SUBJECT: {subject}")
            print(f"\n{body}")
            print("\n" + "="*60)
            
            confirm = input("\nSend this email? (yes/no): ").strip().lower()
            
            if confirm == "yes":
                print("\n⏳ Sending email...")
                success, result = send_email(
                    coach_info['email'], 
                    subject, 
                    body, 
                    athlete_info['email']
                )
                
                if success:
                    add_lead(athlete_info, coach_info, "sent")
                    print("✅ Email sent successfully!")
                    print("📊 Lead added to tracker!")
                else:
                    print(f"❌ Failed to send: {result}")
            else:
                print("📧 Email cancelled.")
                
        elif choice == "3":
            view_leads()
            
        elif choice == "4":
            update_lead_status()
            
        elif choice == "5":
            print("\n👋 Good luck with recruiting!\n")
            break
        
        else:
            print("\n❌ Invalid option. Choose 1-5.")

if __name__ == "__main__":
    main()
