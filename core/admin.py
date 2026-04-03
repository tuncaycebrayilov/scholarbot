from django.contrib import admin
from .models import EmailVerification, LecturePDF

admin.site.register(EmailVerification)
class LectureAdmin(admin.ModelAdmin):
    list_display = ("user","created_at")

admin.site.register(LecturePDF, LectureAdmin)