# 🤖 AutoJobHunter — Setup Guide

## What This Does
Automatically searches Naukri, LinkedIn, Indeed & Glassdoor every 6 hours
for Data Analyst, Data Scientist, ML Engineer & Business Analyst fresher jobs
and sends results to your email!

---

## ⚡ Quick Setup (5 Steps)

### Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 2 — Get Gemini API Key (FREE)
1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

### Step 3 — Get Gmail App Password
1. Go to your Google Account → Security
2. Enable 2-Factor Authentication
3. Go to "App Passwords"
4. Create new app password for "Mail"
5. Copy the 16-character password

### Step 4 — Fill credentials.json
Open `config/credentials.json` and replace:
- `YOUR_GEMINI_API_KEY` → your Gemini key
- `YOUR_SENDER_EMAIL` → your Gmail address
- `YOUR_GMAIL_APP_PASSWORD` → the app password from Step 3
- Fill in your portal usernames and passwords

### Step 5 — Run It!
```bash
python main.py
```

---

## 🚀 Setup 24/7 on GitHub Actions (FREE)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "AutoJobHunter setup"
git remote add origin https://github.com/YOUR_USERNAME/autojobhunter.git
git push -u origin main
```

### Step 2 — Add Secrets to GitHub
Go to: Your Repo → Settings → Secrets → Actions → New Secret

Add these secrets:
| Secret Name | Value |
|------------|-------|
| GEMINI_API_KEY | your gemini key |
| SENDER_EMAIL | your gmail |
| SENDER_APP_PASSWORD | your app password |
| NAUKRI_USERNAME | naukri email |
| NAUKRI_PASSWORD | naukri password |
| LINKEDIN_USERNAME | linkedin email |
| LINKEDIN_PASSWORD | linkedin password |
| INDEED_USERNAME | indeed email |
| INDEED_PASSWORD | indeed password |
| GLASSDOOR_USERNAME | glassdoor email |
| GLASSDOOR_PASSWORD | glassdoor password |

### Step 3 — Enable Actions
Go to: Your Repo → Actions → Enable workflows

### Done! 🎉
The bot will now run automatically at:
- 6:00 AM IST
- 12:00 PM IST  
- 6:00 PM IST
- 12:00 AM IST

Results will arrive in your email: anshumish0606@gmail.com

---

## 📁 Project Structure
```
AutoJobHunter/
├── config/
│   ├── credentials.json    ← Fill your details here
│   ├── job_roles.json      ← Your job roles & filters
│   └── portals.json        ← Portal URLs
├── agents/
│   ├── browser_agent.py    ← Controls the browser
│   ├── login_agent.py      ← Smart login
│   ├── search_agent.py     ← Smart search & filters
│   └── scraper_agent.py    ← Collects job results
├── llm/
│   └── gemini_client.py    ← AI brain (Gemini)
├── output/
│   ├── report_generator.py ← HTML + Excel reports
│   └── notifier.py         ← Email sender
├── .github/workflows/
│   └── autojobhunter.yml   ← 24/7 scheduling
├── main.py                 ← Run this!
└── requirements.txt
```

---

## ⚠️ Important Notes
- Never commit credentials.json to GitHub (use Secrets instead)
- Add credentials.json to .gitignore
- If CAPTCHA appears, the bot will skip that portal and alert you
- LinkedIn may occasionally require manual verification

---

## 💡 Customizing Job Roles
Edit `config/job_roles.json` to change:
- Job roles to search
- Experience filters
- Location preferences
- Keywords to exclude
