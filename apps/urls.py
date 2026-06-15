# urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import student_views
from . import faculty_mentor_views  # renamed from teacher_views
from . import faculty_evaluator_views  # renamed from paper_setter_views
from . import admin_views
from . import profile_views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('register/student/', views.register_student, name='register_student'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('oauth/', include('social_django.urls', namespace='social')),
    
    # Legal pages
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    
    # Dashboard redirect
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    
    # ==================== ADMIN ROUTES ====================
    path('admin/dashboard/', admin_views.dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.user_management, name='admin_users'),
    path('admin/users/add/', admin_views.add_user, name='admin_add_user'),
    path('admin/users/toggle/<int:user_id>/', admin_views.toggle_user_status, name='admin_toggle_user'),
    
    # Student Management
    path('admin/students/', admin_views.student_management, name='admin_students'),
    path('admin/students/add/', admin_views.add_student, name='admin_add_student'),
    path('admin/students/edit/<int:student_id>/', admin_views.edit_student, name='admin_edit_student'),
    path('admin/students/delete/<int:student_id>/', admin_views.delete_student, name='admin_delete_student'),
    path('admin/students/bulk-upload/', admin_views.bulk_upload_students, name='admin_bulk_upload_students'),
    path('admin/students/<int:student_id>/', admin_views.view_student_detail, name='admin_view_student'),
    
    # Organisation Management
    path('admin/organisations/', admin_views.organisation_management, name='admin_companies'),
    path('admin/organisations/add/', admin_views.add_organisation, name='admin_add_organisation'),
    path('admin/organisations/edit/<int:org_id>/', admin_views.edit_organisation, name='admin_edit_organisation'),
    path('admin/organisations/toggle/<int:org_id>/', admin_views.toggle_organisation_status, name='admin_toggle_organisation'),
    path('admin/organisations/<int:org_id>/', admin_views.organisation_detail, name='admin_view_organisation'),
    
    # Programme & Batch Management
    path('admin/programmes/', admin_views.programme_management, name='admin_programmes'),
    path('admin/programmes/add/', admin_views.add_programme, name='admin_add_programme'),
    path('admin/batches/', admin_views.batch_management, name='admin_batches'),
    path('admin/batches/add/', admin_views.add_batch, name='admin_add_batch'),
    
    # Assessment Configuration
    path('admin/assessment-config/', admin_views.assessment_config, name='admin_assessment_config'),
    path('admin/assessment-config/add/', admin_views.add_assessment_config, name='admin_add_assessment_config'),
    
    # ==================== FACULTY MENTOR ROUTES ====================
    path('faculty-mentor/dashboard/', faculty_mentor_views.dashboard, name='faculty_mentor_dashboard'),
    path('faculty-mentor/students/', faculty_mentor_views.assigned_students, name='faculty_mentor_assigned_students'),
    path('faculty-mentor/students/<int:student_id>/', faculty_mentor_views.student_internships, name='faculty_mentor_student_internships'),
    path('faculty-mentor/verify/<int:internship_id>/', faculty_mentor_views.verify_internship, name='faculty_mentor_verify_internship'),
    path('faculty-mentor/marks/<int:internship_id>/', faculty_mentor_views.enter_mentor_marks, name='faculty_mentor_enter_marks'),
    path('faculty-mentor/pending/', faculty_mentor_views.pending_verifications, name='faculty_mentor_pending'),
    path('faculty-mentor/report/<int:student_id>/', faculty_mentor_views.student_progress_report, name='faculty_mentor_student_report'),
    path('faculty-mentor/remarks/<int:internship_id>/', faculty_mentor_views.add_mentor_remarks, name='faculty_mentor_add_remarks'),
    
    # ==================== STUDENT ROUTES ====================
    path('student/dashboard/', student_views.dashboard, name='student_dashboard'),
    path('student/internships/', student_views.my_internships, name='student_internships'),
    path('student/internships/add/', student_views.add_internship, name='student_add_internship'),
    path('student/internships/edit/<int:internship_id>/', student_views.edit_internship, name='student_edit_internship'),
    path('student/internships/submit/<int:internship_id>/', student_views.submit_internship, name='student_submit_internship'),
    path('student/internships/<int:internship_id>/', student_views.internship_details, name='student_internship_details'),
    path('student/breaks/', student_views.my_breaks, name='student_breaks'),
    path('student/breaks/add/', student_views.add_break, name='student_add_break'),
    path('student/marks/', student_views.my_marks, name='student_marks'),
    path('student/documents/', student_views.my_documents, name='student_documents'),
    path('student/documents/upload/', student_views.upload_document, name='student_upload_document'),
    path('student/mentor/', student_views.view_mentor, name='student_view_mentor'),
    
    # ==================== FACULTY EVALUATOR ROUTES ====================
    path('faculty-evaluator/dashboard/', faculty_evaluator_views.dashboard, name='evaluator_dashboard'),
    path('faculty-evaluator/pending/', faculty_evaluator_views.pending_assessments, name='evaluator_pending_assessments'),
    path('faculty-evaluator/viva/<int:internship_id>/', faculty_evaluator_views.enter_viva_marks, name='evaluator_enter_viva'),
    path('faculty-evaluator/intermediate/<int:internship_id>/', faculty_evaluator_views.enter_intermediate_marks, name='evaluator_enter_intermediate'),
    path('faculty-evaluator/review/<int:assessment_id>/', faculty_evaluator_views.review_assessment, name='evaluator_review_assessment'),
    path('faculty-evaluator/lock/<int:internship_id>/', faculty_evaluator_views.lock_marks, name='evaluator_lock_marks'),
    path('faculty-evaluator/history/', faculty_evaluator_views.assessment_history, name='evaluator_history'),
    
    # ==================== PROFILE ROUTES ====================
    path('profile/', profile_views.view_profile, name='view_profile'),
    path('profile/edit/', profile_views.edit_profile, name='edit_profile'),
    path('profile/change-password/', profile_views.change_password, name='change_password'),
    path('notifications/', profile_views.notifications, name='notifications'),


    # User Management
    path('admin/pending-users/', admin_views.pending_users, name='admin_pending_users'),
    path('admin/approve-user/<int:user_id>/', admin_views.approve_user, name='admin_approve_user'),
    path('admin/reject-user/<int:user_id>/', admin_views.reject_user, name='admin_reject_user'),
    path('admin/manage-users/', admin_views.manage_user_roles, name='admin_manage_users'),
    path('admin/update-role/<int:user_id>/', admin_views.update_user_role, name='admin_update_role'),
    
    # ==================== REPORTS ====================
    path('reports/', views.reports, name='reports'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'apps.views.custom_404'
handler500 = 'apps.views.custom_500'