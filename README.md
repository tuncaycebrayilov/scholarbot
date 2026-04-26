# ScholarBot 📚🤖

ScholarBot is an AI-powered study platform built with **Django**.
Students can upload lecture PDFs and instantly receive smart learning materials such as summaries, key points, and exam questions.

It is designed to make studying faster, easier, and more interactive.

---

## 🚀 Features

* 🔐 User Authentication
  Register, login, logout system

* 📧 Email Verification
  Real email confirmation code during registration

* 🔑 Password Reset
  Reset password through email

* 👤 Profile Management
  Change password and manage account

* 📄 PDF Upload System
  Upload lecture notes in PDF format

* 🧠 AI Analysis
  Generate:

  * Summary
  * Key Highlights
  * Exam Questions
  * Quiz Review

* 📚 Lecture History
  Previous uploaded lectures are saved

* ⚡ Instant Results
  AI results appear automatically after analysis

* 🎨 Modern UI
  Dark neon SaaS-style dashboard design

* ⏳ Loading Screen
  Better user experience during processing

---

## 🛠️ Tech Stack

* **Backend:** Django
* **Language:** Python
* **Database:** SQLite
* **PDF Processing:** PyPDF2
* **AI Integration:** OpenAI API
* **Frontend:** HTML, CSS, JavaScript

---

## 📸 Main Workflow

1. User creates account
2. Verifies email
3. Logs in
4. Uploads lecture PDF
5. AI analyzes content
6. Results shown instantly
7. Lecture saved in history

---

## 📂 Installation

```bash
git clone https://github.com/yourusername/scholarbot.git
cd scholarbot
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## ⚙️ Environment Variables

Create `.env` file:

```env
SECRET_KEY=your_secret_key
DEBUG=True
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_password
OPENAI_API_KEY=your_api_key
```

---
