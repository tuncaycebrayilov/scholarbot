from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import EmailVerification, LecturePDF
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseRedirect
from django.http import HttpResponse, FileResponse
import subprocess
import os
import uuid
from django.http import JsonResponse
import hashlib
from django.utils import timezone
from datetime import timedelta
from .forms import UpdateUserForm
from django.urls import reverse
import openai
from django.conf import settings
import PyPDF2
import re
import json
openai.api_key = settings.OPENAI_API_KEY

def generate_ai_content(text):

    prompt = f"""
You are an expert academic AI assistant.

Your job is to analyze a document and decide:

1. Is this a real lecture/study material?
2. Or is it something else (certificate, short document, form, unrelated content)?

---

DECISION RULES:

A document is a LECTURE if:
- It explains concepts, theories, or topics
- Contains structured educational content
- Has multiple sentences/paragraphs of explanation

A document is NOT a lecture if:
- It is a certificate, diploma, or award
- It contains mostly names, dates, signatures
- It is very short or lacks explanations
- It is a form or non-educational content

---

OUTPUT FORMAT (VERY IMPORTANT):

If NOT a lecture, return EXACTLY:

{{
"type": "invalid",
"reason": "short explanation why it is not a lecture"
}}

---

If it IS a lecture, return EXACTLY:

{{
"type": "lecture",
"summary": "A clear and well-structured academic summary (120-180 words). Explain like a good teacher.",
"highlights": [
"Key concept explained clearly",
"Key concept explained clearly",
"Key concept explained clearly",
"Key concept explained clearly",
"Key concept explained clearly"
],
"quiz": [
{{
"question": "Conceptual exam-style question",
"options": ["A realistic option","B realistic option","C realistic option","D realistic option"],
"answer": "correct option exactly as written above"
}}
]
}}

---

STRICT RULES:

- Return ONLY valid JSON (no text outside JSON)
- Summary must be clear and educational (not generic)
- Highlights must be meaningful (not repeated)
- Generate EXACTLY 5 highlights
- Generate EXACTLY 10 quiz questions
- Questions must test understanding (not simple recall)
- Options must be similar difficulty (like real exams)
- Only ONE correct answer

---

DOCUMENT:
{text[:4000]}
"""
    response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Return only valid JSON."},
        {"role": "user", "content": prompt}
    ],
    response_format={"type": "json_object"}
)

    result = response.choices[0].message.content.strip()

    try:
        data = json.loads(result)

        if data.get("type") == "invalid":
            return "INVALID", "", []

        summary = data.get("summary", "")
        highlights = "\n".join(data.get("highlights", []))
        quiz = data.get("quiz", [])

    except Exception as e:

        print("AI RESPONSE ERROR:", result)

        summary = "AI error generating summary"
        highlights = ""
        quiz = []

    return summary, highlights, quiz

def home(request):
    return render(request, 'home.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login") 

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("home")


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Check empty fields
        if not username or not email or not password1 or not password2:
            return render(request, "register.html", {"error": "All fields required"})

        # Check password match
        if password1 != password2:
            return render(request, "register.html", {"error": "Passwords do not match"})

        # Check if user exists
        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"error": "Username exists"})

        # Create inactive user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            is_active=False
        )

        # Save user id in session
        request.session["verify_user_id"] = user.id

        # Create verification code
        verification = EmailVerification.objects.create(user=user)
        verification.generate_code()

        # Send email (console for now)
        send_mail(
            "ScholarBot Verification",
            f"Your code is: {verification.code}",
            "test@gmail.com",
            [email],
            fail_silently=False,
        )

        return redirect("verify")

    return render(request, "register.html")


def verify_email(request):
    user_id = request.session.get("verify_user_id")

    if not user_id:
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
        verification = EmailVerification.objects.get(user=user)
    except:
        return redirect("register")

    if request.method == "POST":
        code = request.POST.get("code")

        # Check expiration (10 minutes)
        if timezone.now() > verification.created_at + timedelta(minutes=10):
            verification.delete()
            user.delete()
            return render(request, "verify.html", {
                "error": "Verification code expired. Please register again."
            })

        # Check wrong code
        if verification.code != code:
            return render(request, "verify.html", {
                "error": "Invalid verification code."
            })

        # If correct
        user.is_active = True
        user.save()
        verification.delete()
        del request.session["verify_user_id"]

        return redirect("login")

    return render(request, "verify.html")

@login_required
def verify_new_email(request):

    try:
        verification = EmailVerification.objects.get(user=request.user)
    except EmailVerification.DoesNotExist:
        return redirect("profile")

    if request.method == "POST":

        code = request.POST.get("code")

        
        if verification.code != code:
            return render(request, "verify_new_email.html", {
                "error": "Invalid verification code"
            })

        user = request.user
        user.email = verification.new_email
        user.save()

        verification.delete()

        return redirect("profile")

    return render(request, "verify_new_email.html")


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "change_password.html"

    def form_valid(self, form):
        # Save the new password
        form.save()

        # Logout user
        logout(self.request)

        # Success message
        messages.success(
            self.request,
            "Password changed successfully. Please login again."
        )

        # Redirect manually
        return HttpResponseRedirect(reverse("login"))

@login_required
def upload_pdf(request):

    if request.method == "POST":

        #  CONVERTED PDF FLOW (banner)
        converted_pdf = request.POST.get("converted_pdf")

        if converted_pdf:
            pdf_path = os.path.join(settings.MEDIA_ROOT, converted_pdf)

            if not os.path.exists(pdf_path):
                messages.error(request, "File not found.",  extra_tags="upload")
                return redirect("dashboard")
            

            reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            
            if len(text.strip()) < 50:
                messages.error(request, "This PDF contains no readable text. Please upload text-based lecture slides.", extra_tags="upload")
                return redirect("dashboard")
                
            clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
            file_hash = hashlib.md5(clean_text.encode()).hexdigest()

            if LecturePDF.objects.filter(user=request.user, file_hash=file_hash).exists():
                messages.error(request, "You already uploaded this lecture.",  extra_tags="upload")
                return redirect("dashboard")

            #  Lecture vs Book detection
            lower_text = text.lower()
            
            book_keywords = ["chapter", "table of contents", "isbn", "copyright"]
            book_score = sum(1 for word in book_keywords if word in lower_text)

            if book_score >= 2 or len(text) > 100000:
                messages.error(request, "This looks like a book. Please upload lecture slides.",  extra_tags="upload")
                return redirect("dashboard")

            # AI analyze
            summary, highlights, quiz = generate_ai_content(text)
            if summary == "INVALID":
                messages.error(request, "This file is not a lecture.", extra_tags="upload")
                return redirect("dashboard")

            LecturePDF.objects.create(
                user=request.user,
                pdf_name=converted_pdf,
                summary=summary,
                highlights=highlights,
                quiz=quiz,
                file_hash=file_hash
            )

            return redirect(reverse("dashboard") + f"?analyzed=1&open={converted_pdf}")


        #  NORMAL PDF UPLOAD
        pdf_file = request.FILES.get("pdf")

        if not pdf_file:
            messages.error(request, "Please upload a PDF file.",  extra_tags="upload")
            return redirect("dashboard")

        # file size check
        if pdf_file.size > 50 * 1024 * 1024:
            messages.error(request, "PDF must be smaller than 50MB.",  extra_tags="upload")
            return redirect("dashboard")

        reader = PyPDF2.PdfReader(pdf_file)

        # extract text
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        
        if len(text.strip()) < 50:
            messages.error(
                request,
                "This PDF contains no readable text. Please upload text-based lecture slides.",
                extra_tags="upload"
            )
            return redirect("dashboard")

        clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
        file_hash = hashlib.md5(clean_text.encode()).hexdigest()

        # duplicate check
        if LecturePDF.objects.filter(user=request.user, file_hash=file_hash).exists():
            messages.error(request, "You already uploaded this lecture.", extra_tags="upload")
            return redirect("dashboard")

        # Lecture vs Book detection
        lower_text = text.lower()

        book_keywords = ["chapter", "table of contents", "isbn", "copyright"]
        book_score = sum(1 for word in book_keywords if word in lower_text)

        if book_score >= 2 or len(text) > 100000:
            messages.error(request, "This looks like a book. Please upload lecture slides.",  extra_tags="upload")
            return redirect("dashboard")

        # AI analyze
        summary, highlights, quiz = generate_ai_content(text)
        if summary == "INVALID":
            messages.error(request, "This file is not a lecture.", extra_tags="upload")
            return redirect("dashboard")

        LecturePDF.objects.create(
            user=request.user,
            pdf_name=pdf_file.name,
            summary=summary,
            highlights=highlights,
            quiz=quiz,
            file_hash=file_hash
        )

    return redirect(reverse("dashboard") + "?analyzed=1")


def convert_to_pdf(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please select a file first.", extra_tags="convert")
            return redirect("dashboard")

        #  Unique filename 
        file_ext = file.name.split('.')[-1]
        if file_ext == "pdf":
            messages.error(request, "This file is already a PDF. Please use Analyze section.", extra_tags="convert")
            return redirect("dashboard")
        
        file_name = os.path.splitext(file.name)[0]  
        unique_id = uuid.uuid4().hex[:6]
        new_name = f"{file_name}_{unique_id}.{file_ext}"

        file_path = os.path.join(settings.MEDIA_ROOT, new_name)

        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Mac LibreOffice path
        soffice_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

        try:
            subprocess.run([
                soffice_path,
                "--headless",
                "--convert-to", "pdf",
                file_path,
                "--outdir", settings.MEDIA_ROOT
            ], check=True)

        except subprocess.CalledProcessError:
            return HttpResponse("Conversion failed ❌")

        # PDF path
        base_name = os.path.splitext(new_name)[0]
        pdf_name = base_name + ".pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_name)

        if not os.path.exists(pdf_path):
            return HttpResponse("PDF not found ❌")

        # Return file
        return redirect(reverse("dashboard") + f"?converted=1&pdf={pdf_name}")

    return HttpResponse("Invalid request")


def download_converted_pdf(request):
    pdf_name = request.GET.get("pdf")

    if not pdf_name:
        return HttpResponse("No file")

    pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_name)

    if not os.path.exists(pdf_path):
        return HttpResponse("File not found")

    return FileResponse(open(pdf_path, 'rb'), as_attachment=True)

@login_required
def dashboard(request):

    lectures = LecturePDF.objects.filter(user=request.user).order_by("-created_at")
    total_uploads = lectures.count()

    completed_quizzes = LecturePDF.objects.filter(
        user=request.user,
        is_completed=True
    ).count()
    
    scores = LecturePDF.objects.filter(
        user=request.user,
        is_completed=True,
        score__isnull=False
    )

    best_score = scores.order_by('-score').first().score if scores.exists() else None

    if scores.exists():
        best_score = max(l.score for l in scores)

    current = lectures.first()

    summary = None
    highlights_list = []
    quiz = []
    pdf_name = None
    saved_answers = []
    saved_score = 0
    quiz_completed = False
    current_id = None

    
    converted = request.GET.get("converted")
    converted_pdf = request.GET.get("pdf")

    show_analysis = request.GET.get("analyzed")

    if current:
        summary = current.summary
        pdf_name = current.pdf_name
        current_id = current.id
        saved_answers = current.user_answers or []
        saved_score = current.score or 0
        quiz_completed = current.is_completed

        if current.highlights:
            highlights_list = [h.strip() for h in current.highlights.split("\n") if h.strip()]

        if current.quiz:
            try:
                quiz = current.quiz
            except:
                quiz = []

    return render(request,"dashboard.html",{
        "summary": summary,
        "pdf_name": pdf_name,
        "highlights_list": highlights_list,
        "lectures": lectures,
        "show_analysis": show_analysis,
        "quiz": json.dumps(quiz),
        "total_uploads": total_uploads,
        "completed_quizzes": completed_quizzes,
        "best_score": best_score,
        "converted": converted,
        "converted_pdf": converted_pdf,
        "saved_answers": json.dumps(saved_answers),
        "saved_score": saved_score,
        "quiz_completed": quiz_completed,
        "current_id": current_id,
    })

@login_required
def profile(request):
    return render(request, "profile.html")


@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return redirect("home")
    
    return redirect("profile")

@login_required
def edit_profile(request):

    if request.method == "POST":

        user = request.user
        username = request.POST.get("username")
        new_email = request.POST.get("email")

        user.username = username
        user.save()

        if new_email != user.email:

            verification, created = EmailVerification.objects.get_or_create(user=user)

            verification.new_email = new_email
            verification.generate_code()

            send_mail(
                "ScholarBot Email Verification",
                f"Your verification code is: {verification.code}",
                "scholarbot@example.com",
                [new_email],
                fail_silently=False,
            )

            return redirect("verify_new_email")

    return redirect("profile")

# for edit profile
@login_required
def resend_email_code(request):

    try:
        verification = EmailVerification.objects.get(user=request.user)
    except EmailVerification.DoesNotExist:
        return redirect("profile")

    verification.generate_code()

    send_mail(
        "ScholarBot Email Verification",
        f"Your new verification code is: {verification.code}",
        "scholarbot@example.com",
        [verification.new_email],
        fail_silently=False,
    )

    return redirect("verify_new_email")

# for register 
def resend_verify_code(request):

    user_id = request.session.get("verify_user_id")

    if not user_id:
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
        verification = EmailVerification.objects.get(user=user)
    except:
        return redirect("register")

    verification.generate_code()

    send_mail(
        "ScholarBot Email Verification",
        f"Your new verification code is: {verification.code}",
        "scholarbot@example.com",
        [user.email],
        fail_silently=False,
    )

    return redirect("verify")

@login_required
def lecture_detail(request, lecture_id):

    lecture = LecturePDF.objects.get(id=lecture_id, user=request.user)

    highlights_list = [h.strip() for h in lecture.highlights.split("-") if h.strip()]
    questions_list = [q.strip() for q in lecture.quiz.split("\n") if q.strip()]

    lectures = LecturePDF.objects.filter(user=request.user).order_by("-created_at")

    return render(request,"dashboard.html",{
        "summary": lecture.summary,
        "pdf_name": lecture.pdf_name,
        "highlights_list": highlights_list,
        "questions_list": questions_list,
        "lectures": lectures
    })

@login_required
def delete_lecture(request, lecture_id):

    lecture = get_object_or_404(LecturePDF, id=lecture_id, user=request.user)

    lecture.delete()

    return redirect("dashboard")


@login_required
def save_quiz_progress(request, lecture_id):
    if request.method == "POST":
        try:
            lecture = LecturePDF.objects.get(id=lecture_id, user=request.user)
            data = json.loads(request.body)

            lecture.user_answers = data.get("answers", [])
            lecture.score = data.get("score", 0)
            lecture.is_completed = str(data.get("completed")).lower() == "true"
            lecture.save()

            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "invalid"})


@login_required
def get_quiz(request, lecture_id):
    lecture = LecturePDF.objects.get(id=lecture_id, user=request.user)
    return JsonResponse({
        "quiz": lecture.quiz or []
    })