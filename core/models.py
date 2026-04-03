import random
from django.db import models
from django.contrib.auth.models import User


class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    new_email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_code(self):
        self.code = str(random.randint(100000, 999999))
        self.save()

class LecturePDF(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="pdfs/")
    pdf_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    highlights = models.TextField(blank=True)
    quiz = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, blank=True, null=True)
    user_answers = models.JSONField(blank=True, null=True)
    score = models.IntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)