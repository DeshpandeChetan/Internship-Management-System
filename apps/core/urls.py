# Internship-Management-System\apps\core\urls.py
from django.urls import path
from . import views
from . import admin_views
from . import student_views
from . import mentor_views
from . import evaluator_views
from . import hod_views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_redirect, name='dashboard'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # ============================================
    # ADMIN URLS
    # ============================================
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
    # path('admin/users/', admin_views.user_list, name='admin_users'),
    # path('admin/users/add/', admin_views.user_add, name='admin_user_add'),
    # path('admin/users/<uuid:pk>/edit/', admin_views.user_edit, name='admin_user_edit'),
    # path('admin/users/<uuid:pk>/delete/', admin_views.user_delete, name='admin_user_delete'),
    # path('admin/users/<uuid:pk>/toggle/', admin_views.user_toggle, name='admin_user_toggle'),
    # path('admin/users/<uuid:pk>/approve/', admin_views.user_approve, name='admin_user_approve'),
    # path('admin/users/bulk-upload/', admin_views.bulk_upload_users, name='bulk_upload_users'),
    
    # User Management (already exists, verify)
    path('admin/users/', admin_views.user_list, name='admin_users'),
    path('admin/users/add/', admin_views.user_add, name='admin_user_add'),
    path('admin/users/<uuid:pk>/edit/', admin_views.user_edit, name='admin_user_edit'),
    path('admin/users/<uuid:pk>/delete/', admin_views.user_delete, name='admin_user_delete'),
    path('admin/users/<uuid:pk>/toggle/', admin_views.user_toggle, name='admin_user_toggle'),
    path('admin/users/<uuid:pk>/approve/', admin_views.user_approve, name='admin_user_approve'),
    path('admin/users/bulk-upload/', admin_views.bulk_upload_users, name='bulk_upload_users'),
    
    # Student Management
    path('admin/students/', admin_views.student_list, name='admin_students'),
    path('admin/students/add/', admin_views.student_add, name='admin_student_add'),
    path('admin/students/<uuid:pk>/', admin_views.student_detail, name='admin_student_detail'),
    path('admin/students/<uuid:pk>/edit/', admin_views.student_edit, name='admin_student_edit'),
    path('admin/students/<uuid:pk>/delete/', admin_views.student_delete, name='admin_student_delete'),
    path('admin/students/bulk-upload/', admin_views.bulk_upload_students, name='admin_bulk_upload_students'),
    
    # Organisation Management
    path('admin/organisations/', admin_views.organisation_list, name='admin_organisations'),
    path('admin/organisations/add/', admin_views.organisation_add, name='admin_organisation_add'),
    path('admin/organisations/<uuid:pk>/edit/', admin_views.organisation_edit, name='admin_organisation_edit'),
    path('admin/organisations/<uuid:pk>/delete/', admin_views.organisation_delete, name='admin_organisation_delete'),
    path('admin/organisations/<uuid:pk>/toggle/', admin_views.organisation_toggle, name='admin_organisation_toggle'),
    path('admin/organisations/<uuid:pk>/detail/', admin_views.organisation_detail, name='admin_organisation_detail'),
    
    # Programme Management
    path('admin/programmes/', admin_views.programme_list, name='admin_programmes'),
    path('admin/programmes/add/', admin_views.programme_add, name='admin_programme_add'),
    path('admin/programmes/<uuid:pk>/edit/', admin_views.programme_edit, name='admin_programme_edit'),
    path('admin/programmes/<uuid:pk>/delete/', admin_views.programme_delete, name='admin_programme_delete'),
    path('admin/programmes/<uuid:pk>/toggle/', admin_views.programme_toggle, name='admin_programme_toggle'),
    
    # Batch Management
    path('admin/batches/', admin_views.batch_list, name='admin_batches'),
    path('admin/batches/add/', admin_views.batch_add, name='admin_batch_add'),
    path('admin/batches/<uuid:pk>/edit/', admin_views.batch_edit, name='admin_batch_edit'),
    path('admin/batches/<uuid:pk>/delete/', admin_views.batch_delete, name='admin_batch_delete'),
    path('admin/batches/<uuid:pk>/toggle/', admin_views.batch_toggle, name='admin_batch_toggle'),
    
    # Internship Management
    path('admin/internships/', admin_views.internship_list, name='admin_internships'),
    path('admin/internships/<uuid:pk>/', admin_views.internship_detail, name='admin_internship_detail'),
    
    # Break Management
    path('admin/breaks/', admin_views.break_list, name='admin_breaks'),
    path('admin/breaks/add/', admin_views.break_add, name='admin_break_add'),
    path('admin/breaks/<uuid:pk>/edit/', admin_views.break_edit, name='admin_break_edit'),
    path('admin/breaks/<uuid:pk>/delete/', admin_views.break_delete, name='admin_break_delete'),
    
    # Assessment Configuration
    path('admin/assessment-config/', admin_views.assessment_config, name='admin_assessment_config'),
    path('admin/assessment-config/<uuid:pk>/delete/', admin_views.assessment_component_delete, name='admin_assessment_component_delete'),
    
    # Mentor Assignment
    path('admin/mentor-assignments/', admin_views.mentor_assignment_list, name='admin_mentor_assignments'),
    path('admin/mentor-assignments/add/', admin_views.mentor_assignment_add, name='admin_mentor_assignment_add'),
    path('admin/mentor-assignments/<uuid:pk>/delete/', admin_views.mentor_assignment_delete, name='admin_mentor_assignment_delete'),
    
    # Reports
    path('admin/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin/consolidated/', admin_views.consolidated_report, name='consolidated_report'),
    path('admin/export/<str:report_type>/', admin_views.export_report, name='export_report'),
    
    # ============================================
    # STUDENT URLS
    # ============================================
    path('student/dashboard/', student_views.student_dashboard, name='student_dashboard'),
    path('student/internships/', student_views.my_internships, name='my_internships'),
    path('student/internships/add/', student_views.internship_add, name='student_internship_add'),
    path('student/internships/<uuid:pk>/', student_views.internship_detail, name='student_internship_detail'),
    path('student/internships/<uuid:pk>/edit/', student_views.internship_edit, name='student_internship_edit'),
    path('student/internships/<uuid:pk>/delete/', student_views.internship_delete, name='student_internship_delete'),
    path('student/mentor/', student_views.my_mentor, name='my_mentor'),
    path('student/marks/', student_views.my_marks, name='my_marks'),
    
    # ============================================
    # MENTOR URLS
    # ============================================
    path('mentor/dashboard/', mentor_views.mentor_dashboard, name='mentor_dashboard'),
    path('mentor/students/', mentor_views.assigned_students, name='mentor_assigned_students'),
    path('mentor/students/<uuid:pk>/', mentor_views.student_detail, name='mentor_student_detail'),
    path('mentor/pending-verification/', mentor_views.pending_verification, name='mentor_pending_verification'),
    path('mentor/verify/<uuid:pk>/', mentor_views.verify_internship, name='mentor_verify_internship'),
    path('mentor/all-internships/', mentor_views.all_internships, name='mentor_all_internships'),
    
    # ============================================
    # EVALUATOR URLS
    # ============================================
    path('evaluator/dashboard/', evaluator_views.evaluator_dashboard, name='evaluator_dashboard'),
    path('evaluator/pending-assessments/', evaluator_views.pending_assessments, name='evaluator_pending_assessments'),
    path('evaluator/marks/enter/<uuid:pk>/', evaluator_views.enter_marks, name='evaluator_enter_marks'),
    path('evaluator/history/', evaluator_views.assessment_history, name='evaluator_history'),
    
    # ============================================
    # HOD URLS
    # ============================================
    path('hod/dashboard/', hod_views.hod_dashboard, name='hod_dashboard'),
    path('hod/students/', hod_views.student_list, name='hod_students'),
    path('hod/reports/', hod_views.reports, name='hod_reports'),
    path('hod/reports/consolidated/', hod_views.consolidated_report, name='hod_consolidated_report'),
    path('hod/approvals/', hod_views.approvals, name='hod_approvals'),
    path('hod/approve/<uuid:pk>/', hod_views.approve_record, name='hod_approve'),
    path('hod/reject/<uuid:pk>/', hod_views.reject_record, name='hod_reject'),
    
    # ============================================
    # REPORTS (Shared)
    # ============================================
    path('reports/', views.report_list, name='report_list'),
    path('reports/export/<str:report_type>/', views.export_report, name='export_report'),
]