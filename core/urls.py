from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("profile/", views.profile, name="profile"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("verify/", views.verify_email, name="verify"),
    path('delete-account/', views.delete_account, name='delete_account'),
    path("edit-profile/", views.edit_profile, name="edit_profile"),
    path("verify-new-email/", views.verify_new_email, name="verify_new_email"),
    path("resend-email-code/", views.resend_email_code, name="resend_email_code"),
    path("resend-code/", views.resend_verify_code, name="resend_code"),
    path("upload-pdf/", views.upload_pdf, name="upload_pdf"),
    path("lecture/<int:lecture_id>/", views.lecture_detail, name="lecture_detail"),
    path("delete-lecture/<int:lecture_id>/", views.delete_lecture, name="delete_lecture"),
    path('convert/', views.convert_to_pdf, name='convert_to_pdf'),
    path('download-pdf/', views.download_converted_pdf, name='download_pdf'),
    path("save-quiz/<int:lecture_id>/", views.save_quiz_progress, name="save_quiz"),
    path("get-quiz/<int:lecture_id>/", views.get_quiz, name="get_quiz"),
]