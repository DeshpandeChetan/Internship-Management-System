from django.test import TestCase
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from apps.authentication.models import UserProfile
from .forms import MentorAssignmentForm
from .models import MentorAssignment, Student


class MentorHistoryTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(register_number='TEST1', name='Student', email='student@test.com')
        self.mentors = [UserProfile.objects.create(user=User.objects.create_user(username=f'mentor{i}'), role='faculty_mentor') for i in range(2)]
        self.today = timezone.localdate()
        self.old = MentorAssignment.objects.create(student=self.student, faculty_mentor=self.mentors[0], effective_from=self.today - timedelta(days=30))

    def form(self, instance=None, **changes):
        data = dict(student=str(self.student.pk), faculty_mentor=str(self.mentors[1].pk), effective_from=self.today.isoformat(), no_end_date='on', assignment_level='student')
        data.update(changes)
        return MentorAssignmentForm(data, instance=instance)

    def test_reassignment_preserves_previous(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        new = form.save()
        self.old.refresh_from_db()
        self.assertEqual(self.old.effective_to, self.today - timedelta(days=1))
        self.assertFalse(self.old.is_active)
        self.assertEqual(self.old.faculty_mentor, self.mentors[0])
        self.assertIsNone(new.effective_to)
        self.assertTrue(new.is_current)

    def test_editing_mentor_creates_history(self):
        old_id = self.old.pk
        form = self.form(instance=self.old)
        self.assertTrue(form.is_valid(), form.errors)
        new = form.save()
        self.assertNotEqual(new.pk, old_id)
        self.assertEqual(MentorAssignment.objects.count(), 2)

    def test_end_date_required(self):
        form = self.form(no_end_date='')
        self.assertFalse(form.is_valid())
        self.assertIn('effective_to', form.errors)

    def test_co_mentor_preserves_current(self):
        form = self.form(allow_co_mentor='on')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.old.refresh_from_db()
        self.assertIsNone(self.old.effective_to)

    def test_future_assignment_not_current_early(self):
        form = self.form(effective_from=(self.today + timedelta(days=10)).isoformat())
        self.assertTrue(form.is_valid(), form.errors)
        future = form.save()
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_current)
        self.assertFalse(future.is_current)

    def test_admin_assignment_list_only_contains_current_assignments(self):
        from django.urls import reverse
        admin = User.objects.create_superuser('listadmin', 'listadmin@test.com', 'password')
        self.client.force_login(admin)
        MentorAssignment.objects.create(student=self.student, faculty_mentor=self.mentors[1],
            effective_from=self.today + timedelta(days=3))
        MentorAssignment.objects.create(student=self.student, faculty_mentor=self.mentors[1],
            effective_from=self.today - timedelta(days=10), is_active=False)
        MentorAssignment.objects.create(student=self.student, faculty_mentor=self.mentors[1],
            effective_from=self.today - timedelta(days=20), effective_to=self.today - timedelta(days=1))
        response = self.client.get(reverse('admin_mentor_assignments'))
        self.assertEqual(list(response.context['assignments']), [self.old])
        self.assertEqual(self.student.mentor_assignments.count(), 4)

    def test_reassignment_cannot_start_on_previous_start(self):
        form = self.form(effective_from=self.old.effective_from.isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn('effective_from', form.errors)

    def test_checked_option_ignores_stale_date(self):
        form = self.form(effective_to='invalid-date')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().effective_to)

    def test_end_date_before_start_rejected(self):
        form = self.form(no_end_date='', effective_to=(self.today - timedelta(days=1)).isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn('effective_to', form.errors)

    def test_exact_duplicate_rejected_even_with_co_mentoring(self):
        for co_mentor in ('', 'on'):
            with self.subTest(co_mentor=co_mentor):
                form = self.form(
                    faculty_mentor=str(self.mentors[0].pk),
                    effective_from=self.old.effective_from.isoformat(),
                    allow_co_mentor=co_mentor,
                )
                self.assertFalse(form.is_valid())
                self.assertIn('already exists', str(form.non_field_errors()))
        self.assertEqual(MentorAssignment.objects.count(), 1)

    def test_exact_duplicate_with_finite_dates_rejected(self):
        self.old.effective_to = self.today
        self.old.save()
        form = self.form(faculty_mentor=str(self.mentors[0].pk),
                         effective_from=self.old.effective_from.isoformat(),
                         effective_to=self.today.isoformat(), no_end_date='')
        self.assertFalse(form.is_valid())
        self.assertIn('already exists', str(form.non_field_errors()))

    def test_unchanged_edit_is_not_duplicate(self):
        form = self.form(instance=self.old, faculty_mentor=str(self.mentors[0].pk),
                         effective_from=self.old.effective_from.isoformat())
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(MentorAssignment.objects.count(), 1)


class InternshipAcademicPeriodTests(TestCase):
    def setUp(self):
        from datetime import date
        from .models import Organisation
        self.start = date(2026, 6, 1)
        self.end = date(2027, 5, 31)
        self.student = Student.objects.create(
            register_number='DATES1', name='Date Test', email='dates@test.com',
            degree_start_date=self.start, degree_end_date=self.end,
        )
        self.organisation = Organisation.objects.create(name='Date Organisation', organisation_type='company')

    def form(self, start, end, **changes):
        from .student_views import student_internship_form
        data = dict(organisation=str(self.organisation.pk), internship_type='additional',
                    internship_number='Extra', start_date=start.isoformat(), end_date=end.isoformat(),
                    mode='offline', completion_status='pending')
        data.update(changes)
        return student_internship_form(data, student=self.student)

    def test_both_fields_reject_dates_outside_period(self):
        for value in (self.start - timedelta(days=1), self.end + timedelta(days=1)):
            with self.subTest(value=value):
                form = self.form(value, value, date_override_approved='on', date_override_reason='Forged')
                self.assertFalse(form.is_valid())
                self.assertIn('start_date', form.errors)
                self.assertIn('end_date', form.errors)

    def test_period_boundaries_allowed_and_picker_bounds_set(self):
        form = self.form(self.start, self.end)
        self.assertTrue(form.is_valid(), form.errors)
        for name in ('start_date', 'end_date'):
            self.assertEqual(form.fields[name].widget.attrs['min'], self.start.isoformat())
            self.assertEqual(form.fields[name].widget.attrs['max'], self.end.isoformat())

class DeletedContentTests(TestCase):
    def setUp(self):
        from .models import Programme, Batch
        self.admin = User.objects.create_superuser('binadmin', 'binadmin@test.com', 'password')
        self.client.force_login(self.admin)
        self.programme = Programme.objects.create(code='BIN', name='Recycle Programme')
        self.batch = Batch.objects.create(name='Recycle Batch', programme=self.programme, start_year=2026, end_year=2031)

    def test_delete_preserves_dependencies_and_restore_restores_original_state(self):
        from django.urls import reverse
        from .models import Programme, Batch
        self.client.post(reverse('admin_programme_delete', args=[self.programme.pk]))
        self.assertFalse(Programme.objects.filter(pk=self.programme.pk).exists())
        self.assertTrue(Programme.all_objects.get(pk=self.programme.pk).is_active)
        self.assertTrue(Batch.objects.filter(pk=self.batch.pk).exists())
        self.assertContains(self.client.get(reverse('admin_deleted_content')), 'Recycle Programme')
        self.client.post(reverse('admin_deleted_restore', args=['programme', self.programme.pk]))
        self.assertTrue(Programme.objects.get(pk=self.programme.pk).is_active)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.programme_id, self.programme.pk)

    def test_permanent_delete_preserves_even_deleted_dependencies(self):
        from django.urls import reverse
        from .models import Programme, Batch
        self.programme.delete()
        self.batch.delete()
        response = self.client.post(reverse('admin_deleted_permanent', args=['programme', self.programme.pk]), follow=True)
        self.assertContains(response, 'Related historical records have been preserved')
        self.assertFalse(Programme.all_objects.filter(pk=self.programme.pk).exists())
        self.assertTrue(Batch.all_objects.filter(pk=self.batch.pk).exists())
        self.batch.refresh_from_db()
        reference = self.batch.programme
        self.assertTrue(reference.is_history_reference)
        self.assertFalse(Programme.objects.filter(pk=reference.pk).exists())
        self.assertEqual(self.client.post(reverse('admin_deleted_restore', args=['programme', reference.pk])).status_code, 404)
        self.client.post(reverse('admin_deleted_restore', args=['batch', self.batch.pk]))
        self.assertTrue(Batch.objects.filter(pk=self.batch.pk).exists())

    def test_permanent_delete_without_dependencies(self):
        from django.urls import reverse
        from .models import Batch
        self.batch.delete()
        self.client.post(reverse('admin_deleted_permanent', args=['batch', self.batch.pk]))
        self.assertFalse(Batch.all_objects.filter(pk=self.batch.pk).exists())

    def test_child_restore_requires_parent_first(self):
        from django.urls import reverse
        from .models import Batch
        self.batch.delete()
        self.programme.delete()
        self.client.post(reverse('admin_deleted_restore', args=['batch', self.batch.pk]))
        self.assertFalse(Batch.objects.filter(pk=self.batch.pk).exists())

    def test_deactivate_stays_in_list_and_outside_deleted_content(self):
        from django.urls import reverse
        from .models import Programme
        self.client.get(reverse('admin_programme_toggle', args=[self.programme.pk]))
        programme = Programme.objects.get(pk=self.programme.pk)
        self.assertFalse(programme.is_active)
        self.assertIsNone(programme.deleted_at)

    def test_delete_requires_post_and_recycle_access_requires_admin(self):
        from django.urls import reverse
        self.assertEqual(self.client.get(reverse('admin_programme_delete', args=[self.programme.pk])).status_code, 405)
        user = User.objects.create_user('binmentor', 'binmentor@test.com')
        UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        self.client.force_login(user)
        for name, args in [('admin_deleted_content', []), ('admin_deleted_restore', ['batch', self.batch.pk])]:
            self.assertEqual(self.client.post(reverse(name, args=args)).status_code, 302)

    def test_user_delete_blocks_login_without_changing_activation(self):
        from django.urls import reverse
        user = User.objects.create_user('binuser', 'binuser@test.com')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        self.client.post(reverse('admin_user_delete', args=[profile.pk]))
        archived = UserProfile.all_objects.get(pk=profile.pk)
        self.assertTrue(archived.is_active)
        self.assertFalse(archived.can_login())
        self.client.post(reverse('admin_deleted_restore', args=['userprofile', profile.pk]))
        self.assertTrue(UserProfile.objects.get(pk=profile.pk).can_login())

    def test_django_admin_bulk_delete_preserves_accounts(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.authentication.admin import CustomUserAdmin
        user = User.objects.create_user('adminbin', 'adminbin@test.com')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        request = RequestFactory().post('/admin/auth/user/')
        request.user = self.admin
        CustomUserAdmin(User, admin.site).delete_queryset(request, User.objects.filter(pk__in=[user.pk, self.admin.pk]))
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(pk=profile.pk).exists())
        self.assertTrue(UserProfile.objects.filter(user=self.admin).exists())

    def test_student_delete_preserves_login_identity_and_blocks_login(self):
        student = Student.objects.create(register_number='BIN-STUDENT', name='Archived Student', email='binstudent@test.com')
        user = student.user
        student.delete()
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.profile.can_login())
        self.assertTrue(Student.all_objects.filter(pk=student.pk).exists())

    def test_unreferenced_user_permanent_delete_removes_identity(self):
        from django.urls import reverse
        user = User.objects.create_user('removebin', 'removebin@test.com')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        profile.delete()
        self.client.post(reverse('admin_deleted_permanent', args=['userprofile', profile.pk]))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(UserProfile.all_objects.filter(pk=profile.pk).exists())

    def test_student_permanent_delete_preserves_internships_and_scores(self):
        from datetime import date
        from django.urls import reverse
        from .models import InternshipRecord, Organisation, ConsolidatedScore
        student = Student.objects.create(register_number='PERMANENT', name='Historical Student', email='permanent@test.com')
        organisation = Organisation.objects.create(name='Historical Organisation', organisation_type='company')
        internship = InternshipRecord.objects.create(student=student, organisation=organisation,
            internship_number='1', start_date=date(2026, 1, 1), end_date=date(2026, 2, 1))
        score = ConsolidatedScore.objects.create(student=student, final_consolidated_score=85, is_finalized=True)
        student.delete()
        self.client.post(reverse('admin_deleted_permanent', args=['student', student.pk]))
        self.assertFalse(Student.all_objects.filter(pk=student.pk).exists())
        internship.refresh_from_db()
        score.refresh_from_db()
        self.assertEqual(score.final_consolidated_score, 85)
        self.assertEqual(score.student_id, internship.student_id)
        self.assertTrue(internship.student.is_history_reference)
        self.assertEqual(internship.student.name, 'Historical Student')

    def test_internship_permanent_delete_preserves_marks_and_history(self):
        from datetime import date
        from django.urls import reverse
        from .models import InternshipRecord, Organisation, AssessmentComponent, AssessmentMarks, AssessmentMarksHistory
        student = Student.objects.create(register_number='MARKKEEP', name='Marks Student', email='markkeep@test.com')
        organisation = Organisation.objects.create(name='Marks Organisation', organisation_type='company')
        internship = InternshipRecord.objects.create(student=student, organisation=organisation,
            internship_number='1', start_date=date(2026, 1, 1), end_date=date(2026, 2, 1))
        component = AssessmentComponent.objects.create(name='Historical Viva', assessment_type='viva')
        marks = AssessmentMarks.objects.create(internship_record=internship, assessment_component=component,
            marks_awarded=90, maximum_marks=100, status='locked')
        history = AssessmentMarksHistory.objects.create(assessment_marks=marks, remarks='Keep this history')
        internship.delete()
        self.client.post(reverse('admin_deleted_permanent', args=['internshiprecord', internship.pk]))
        self.assertFalse(InternshipRecord.all_objects.filter(pk=internship.pk).exists())
        marks.refresh_from_db()
        self.assertEqual(marks.marks_awarded, 90)
        self.assertEqual(marks.status, 'locked')
        self.assertTrue(marks.internship_record.is_history_reference)
        self.assertTrue(AssessmentMarksHistory.objects.filter(pk=history.pk).exists())

    def test_user_permanent_delete_preserves_mentor_assignments_and_audit(self):
        from django.urls import reverse
        from .models import AuditLog
        user = User.objects.create_user('pastmentor', 'pastmentor@test.com')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        student = Student.objects.create(register_number='PAST', name='Student', email='past@test.com')
        assignment = MentorAssignment.objects.create(student=student, faculty_mentor=profile, effective_from=timezone.localdate(), assigned_by=user)
        audit = AuditLog.objects.create(user=user, action='CREATE', module='Test')
        profile.delete()
        self.client.post(reverse('admin_deleted_permanent', args=['userprofile', profile.pk]))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(UserProfile.all_objects.filter(pk=profile.pk).exists())
        assignment.refresh_from_db()
        audit.refresh_from_db()
        self.assertTrue(assignment.faculty_mentor.is_history_reference)
        self.assertFalse(assignment.faculty_mentor.can_login())
        self.assertFalse(audit.user.is_active)

    def test_role_search_by_name_and_email(self):
        from django.urls import reverse
        user = User.objects.create_user('rolesearch', 'rolesearch@test.com', first_name='Distinctive')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        for query in ('Distinctive', 'rolesearch@test.com'):
            response = self.client.get(reverse('admin_manage_users'), {'q': query})
            self.assertEqual(list(response.context['users']), [profile])

    def test_pending_users_keep_users_sidebar_selected(self):
        from django.urls import reverse
        response = self.client.get(reverse('admin_pending_users'))
        self.assertContains(response, 'class="nav-link active" href="' + reverse('admin_users') + '"')


class AdminCreationStateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('creationadmin', 'creationadmin@test.com', 'password')
        self.client.force_login(self.admin)

    def test_admin_added_user_is_approved_and_can_reach_dashboard(self):
        from django.urls import reverse
        self.client.post(reverse('admin_user_add'), dict(first_name='New', last_name='Mentor',
            email='newmentor@test.com', role='faculty_mentor', is_active='1'))
        user = User.objects.get(email='newmentor@test.com')
        self.assertTrue(user.profile.is_active)
        self.assertTrue(user.profile.is_approved)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('mentor_dashboard'))

    def test_edit_does_not_approve_existing_google_registration(self):
        from .forms import UserForm
        user = User.objects.create_user('pendingedit', 'pendingedit@test.com')
        UserProfile.objects.create(user=user, role='student', is_approved=False)
        form = UserForm(dict(first_name='Pending', last_name='Account', email=user.email,
                             role='unassigned', is_active='1'), instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.is_approved)

    def test_master_entities_default_active_without_status_input(self):
        from django.urls import reverse
        from .models import Programme, Batch, Organisation
        self.client.post(reverse('admin_programme_add'), {'name': 'Law', 'code': 'LAW', 'duration_years': '5'})
        programme = Programme.objects.get(code='LAW')
        self.assertTrue(programme.is_active)
        self.client.post(reverse('admin_batch_add'), {'name': 'Law 2026', 'programme': str(programme.pk), 'start_year': '2026', 'end_year': '2031'})
        self.assertTrue(Batch.objects.get(name='Law 2026').is_active)
        self.client.post(reverse('admin_organisation_add'), {'name': 'Active Org', 'organisation_type': 'company'})
        self.assertTrue(Organisation.objects.get(name='Active Org').is_active)

    def test_edit_preserves_existing_inactive_status(self):
        from django.urls import reverse
        from .models import Programme
        programme = Programme.objects.create(name='Inactive', code='INACTIVE', is_active=False)
        self.client.post(reverse('admin_programme_edit', args=[programme.pk]), {'name': 'Renamed', 'code': 'INACTIVE', 'duration_years': '5'})
        programme.refresh_from_db()
        self.assertFalse(programme.is_active)
        self.assertEqual(programme.name, 'Renamed')

    def test_explicit_inactive_selection_is_respected(self):
        from django.urls import reverse
        from .models import Programme
        self.client.post(reverse('admin_programme_add'), {'name': 'Disabled', 'code': 'DISABLED', 'duration_years': '5', 'is_active': 'False'})
        self.assertFalse(Programme.objects.get(code='DISABLED').is_active)

    def test_django_admin_created_user_has_approved_profile(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.authentication.admin import CustomUserAdmin
        user = User(username='admincreated', email='admincreated@test.com')
        CustomUserAdmin(User, admin.site).save_model(RequestFactory().post('/admin/'), user, None, False)
        self.assertTrue(user.profile.is_approved)
        self.assertTrue(user.profile.is_active)
        self.assertEqual(user.profile.role, 'unassigned')

    def test_new_google_registration_still_pending(self):
        from allauth.socialaccount.models import SocialAccount
        user = User.objects.create_user('googlenew', 'googlenew@test.com')
        SocialAccount.objects.create(user=user, provider='google', uid='newpendinggoogle')
        self.assertFalse(user.profile.is_approved)
        self.assertFalse(user.profile.can_login())


class FormErrorResponseTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('validationadmin', 'validationadmin@test.com', 'password')
        self.client.force_login(self.admin)
        self.headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest', 'HTTP_X_IMS_FORM': '1'}

    def test_add_user_returns_field_errors_without_messages(self):
        from django.urls import reverse
        from django.contrib.messages import get_messages
        data = {'first_name': 'Preserved', 'last_name': 'Name', 'email': 'invalid-email',
                'phone_number': '123', 'role': 'faculty_mentor', 'is_active': '1'}
        response = self.client.post(reverse('admin_user_add'), data, **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])
        self.assertIn('phone_number', response.json()['errors'])
        self.assertEqual(list(get_messages(response.wsgi_request)), [])
        self.assertFalse(User.objects.filter(first_name='Preserved').exists())

    def test_invalid_edit_does_not_modify_existing_user(self):
        from django.urls import reverse
        user = User.objects.create_user('editvalidation', 'editvalidation@test.com', first_name='Original')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        response = self.client.post(reverse('admin_user_edit', args=[profile.pk]), {
            'first_name': 'Unsaved', 'last_name': 'Name', 'email': user.email,
            'phone_number': '123', 'role': 'faculty_mentor', 'is_active': '1',
        }, **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.json()['errors'])
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Original')

    def test_non_ajax_invalid_form_remains_bound(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin_user_add'), {
            'first_name': 'Preserved', 'last_name': 'Name', 'email': 'invalid', 'role': 'faculty_mentor',
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['form'].is_bound)
        self.assertEqual(response.context['form']['first_name'].value(), 'Preserved')
        self.assertContains(response, 'value="Preserved"', status_code=400)

    def test_department_errors_use_same_response_contract(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin_department_add'), {'name': 'Retain name', 'code': ''}, **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('code', response.json()['errors'])

    def test_success_redirect_and_message_are_preserved(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin_department_add'), {'name': 'New Dept', 'code': 'NEW'}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect_url'], reverse('admin_departments'))
        page = self.client.get(response.json()['redirect_url'])
        self.assertContains(page, 'Department added successfully!')
        self.assertContains(page, 'data-ims-message')

    def test_manual_business_errors_return_to_form_without_redirect(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin_user_add'), {'role': 'student'}, **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Student Management', response.json()['errors']['__all__'][0])

    def test_role_change_toast_preserves_old_and_new_roles(self):
        from django.urls import reverse
        user = User.objects.create_user('roletoast', 'roletoast@test.com')
        UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        response = self.client.post(reverse('admin_update_user_role', args=[user.pk]), {'role': 'hod'}, **self.headers)
        self.assertEqual(response.status_code, 200)
        page = self.client.get(response.json()['redirect_url'])
        self.assertContains(page, 'from Faculty Mentor to HoD/Coordinator')
        self.assertContains(page, 'data-ims-message')
        following = self.client.get(response.json()['redirect_url'])
        self.assertNotContains(following, 'from Faculty Mentor to HoD/Coordinator')

    def test_admin_user_view_details_and_access_control(self):
        from django.urls import reverse
        user = User.objects.create_user('detailuser', 'detailuser@test.com', first_name='Selected')
        profile = UserProfile.objects.create(user=user, role='faculty_mentor', is_approved=True)
        url = reverse('admin_user_detail', args=[profile.pk])
        detail = self.client.get(url)
        self.assertEqual(detail.json()['name'], 'Selected')
        self.assertEqual(detail.json()['email'], user.email)
        self.assertNotIn('password', detail.json())
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_admin_settings_link_card_and_access(self):
        from django.urls import reverse
        response = self.client.get(reverse('admin_users'))
        self.assertContains(response, 'href="' + reverse('admin_settings') + '"')
        self.assertContains(self.client.get(reverse('admin_settings')), reverse('admin_deleted_content'))


class MobileValidationTests(TestCase):
    def test_shared_validator_rejects_invalid_numbers(self):
        from apps.authentication.validators import validate_mobile_number
        from django.core.exceptions import ValidationError
        for value in ('123456789', '12345678901', '12345abcde', '+123456789', '123 456789', '１２３４５６７８９０'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_mobile_number(value)
        self.assertEqual(validate_mobile_number('0123456789'), '0123456789')
        self.assertEqual(validate_mobile_number(''), '')

    def test_model_fields_used_by_admin_enforce_validator(self):
        from django.core.exceptions import ValidationError
        from .models import Organisation
        for model, name in ((Student, 'mobile'), (UserProfile, 'phone_number'), (Organisation, 'phone')):
            field = model._meta.get_field(name)
            for value in ('123', '12345678901', 'abcdefghij'):
                with self.subTest(model=model, value=value), self.assertRaises(ValidationError):
                    field.clean(value, None)
            self.assertEqual(field.clean('0123456789', None), '0123456789')

    def test_user_student_organisation_forms_validate_mobile_fields(self):
        from .forms import UserForm, StudentForm, OrganisationForm, ProfileForm
        for form_class, name in ((UserForm, 'phone_number'), (StudentForm, 'mobile'),
                                 (OrganisationForm, 'phone'), (ProfileForm, 'phone_number')):
            for value in ('123456789', '12345678901', 'abcdefghij'):
                with self.subTest(form=form_class, value=value):
                    form = form_class(data={name: value})
                    self.assertFalse(form.is_valid())
                    self.assertIn(name, form.errors)
            self.assertEqual(str(form_class().fields[name].widget.attrs['maxlength']), '10')


class StudentAndApprovalWorkflowTests(TestCase):
    def setUp(self):
        from .models import Organisation
        from datetime import date
        self.student = Student.objects.create(register_number='FLOW1', name='Flow Student', email='flow@test.com')
        self.user = self.student.user
        self.user.profile.is_approved = True
        self.user.profile.save()
        self.admin = User.objects.create_superuser('flowadmin', 'admin@test.com', 'password')
        self.organisation = Organisation.objects.create(name='Flow Org', organisation_type='company')
        from .models import InternshipRecord
        self.internship = InternshipRecord.objects.create(student=self.student, created_by=self.user,
            organisation=self.organisation, internship_type='additional', internship_number='Extra',
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 30), verification_status='verified',
            verified_by=self.admin, verified_at=timezone.now(), completion_status='completed')

    def test_student_edit_restarts_verification(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response = self.client.post(reverse('student_internship_edit', args=[self.internship.pk]), {
            'organisation': str(self.organisation.pk), 'internship_type': 'additional', 'internship_number': 'Extra',
            'start_date': '2026-06-02', 'end_date': '2026-06-30', 'mode': 'offline', 'completion_status': 'completed',
        })
        self.assertEqual(response.status_code, 302)
        self.internship.refresh_from_db()
        self.assertEqual(self.internship.verification_status, 'submitted')
        self.assertEqual(self.internship.completion_status, 'pending')
        self.assertIsNone(self.internship.verified_by)

    def test_admin_student_internship_links_include_detail_and_verification(self):
        from django.urls import reverse
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_student_detail', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['internships'][0]['id'], str(self.internship.pk))
        detail = self.client.get(reverse('admin_internship_detail', args=[self.internship.pk]))
        self.assertEqual(detail.json()['verification_status'], 'Verified')
        self.assertEqual(detail.json()['completion_status'], 'Completed')

    def test_delete_requires_post_and_ownership(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        url = reverse('student_internship_delete', args=[self.internship.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(type(self.internship).objects.filter(pk=self.internship.pk).exists())

    def test_other_student_cannot_edit_or_delete(self):
        from django.urls import reverse
        other = Student.objects.create(register_number='FLOW2', name='Other', email='other@test.com')
        other.user.profile.is_approved = True
        other.user.profile.save()
        self.client.force_login(other.user)
        for name in ('student_internship_edit', 'student_internship_delete'):
            self.assertEqual(self.client.post(reverse(name, args=[self.internship.pk])).status_code, 404)

    def test_assessment_history_blocks_delete_and_finalized_edit(self):
        from django.urls import reverse
        from .models import AssessmentComponent, AssessmentMarks
        component = AssessmentComponent.objects.create(name='Viva', assessment_type='viva')
        mark = AssessmentMarks.objects.create(internship_record=self.internship,
            assessment_component=component, maximum_marks=100, marks_awarded=80, status='locked')
        self.client.force_login(self.user)
        self.client.post(reverse('student_internship_delete', args=[self.internship.pk]))
        self.client.post(reverse('student_internship_edit', args=[self.internship.pk]), {})
        self.internship.refresh_from_db()
        self.assertEqual(self.internship.verification_status, 'verified')
        self.assertTrue(AssessmentMarks.objects.filter(pk=mark.pk).exists())

    def test_invalid_academic_dates_do_not_partially_update_profile(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        result = self.client.post(reverse('profile_update'), {
            'first_name': 'Invalid', 'degree_start_date': '2031-01-01', 'degree_end_date': '2026-01-01',
        })
        self.assertEqual(result.status_code, 400)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.first_name, 'Invalid')

    def test_invalid_mobile_profile_update_is_rejected(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        for value in ('123456789', '12345678901', 'abcdefghij'):
            response = self.client.post(reverse('profile_update'), {'phone_number': value})
            self.assertEqual(response.status_code, 400)
            self.assertIn('phone_number', response.json()['errors'])

    def test_profile_updates_academics_but_not_role_or_email(self):
        from django.urls import reverse
        from .models import Department
        department = Department.objects.create(name='Law', code='LAW')
        self.client.force_login(self.user)
        result = self.client.post(reverse('profile_update'), dict(first_name='Updated', last_name='Student',
            phone_number='9876543210', department=str(department.pk), degree_start_date='2026-01-01',
            degree_end_date='2031-01-01', role='admin', email='forged@test.com'))
        self.assertEqual(result.status_code, 302)
        self.student.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.student.department, department)
        self.assertEqual(self.user.profile.role, 'student')
        self.assertEqual(self.user.email, 'flow@test.com')

    def pending(self, suffix):
        user = User.objects.create_user(f'pending{suffix}', f'pending{suffix}@test.com')
        UserProfile.objects.create(user=user, role='student')
        return user

    def test_faculty_approval_without_student_role(self):
        from django.urls import reverse
        user = self.pending('faculty')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('admin_pending_user_decision', args=[user.pk]), {'action': 'faculty'}).status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.profile.role, 'unassigned')
        self.assertTrue(user.profile.can_login())
        self.assertFalse(Student.objects.filter(user=user).exists())
        self.assertContains(self.client.get(reverse('admin_manage_users')), user.email)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('profile'))

    def test_student_approval_creates_student_and_reject_preserves_account(self):
        from django.urls import reverse
        self.client.force_login(self.admin)
        user = self.pending('student')
        self.client.post(reverse('admin_pending_user_decision', args=[user.pk]), {'action': 'student'})
        self.assertTrue(Student.objects.filter(user=user).exists())
        rejected = self.pending('reject')
        self.client.post(reverse('admin_pending_user_decision', args=[rejected.pk]), {'action': 'reject'})
        rejected.profile.refresh_from_db()
        self.assertFalse(rejected.profile.can_login())
        self.assertTrue(User.objects.filter(pk=rejected.pk).exists())
