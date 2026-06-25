# apps/utils/calculations.py

from decimal import Decimal

from django.db.models import Avg

from apps.core.models import AssessmentConfiguration

FINAL_STATUSES = ['approved', 'locked']


def _active_config(student):
    if not student.programme_id:
        return None
    return AssessmentConfiguration.objects.filter(
        programme=student.programme,
        is_active=True
    ).first()


def _display_formula(config):
    if not config:
        return 'Default (Simple Average)'
    return dict(AssessmentConfiguration.CALCULATION_CHOICES).get(
        config.calculation_formula,
        config.calculation_formula
    )


def _regular_slots(config):
    count = config.regular_internship_count if config else 8
    return [str(index) for index in range(1, (count or 8) + 1)]


def _latest_final_mark(internship, assessment_type):
    return internship.assessment_marks.filter(
        assessment_component__assessment_type=assessment_type,
        status__in=FINAL_STATUSES
    ).select_related('assessment_component').order_by('-assessment_date', '-created_on').first()


def _final_marks(internship):
    return internship.assessment_marks.filter(
        status__in=FINAL_STATUSES
    ).select_related('assessment_component').order_by('assessment_component__assessment_type', 'created_on')


def calculate_internship_score(internship, config=None):
    """Return the final score for one internship based on viva and config."""
    viva = _latest_final_mark(internship, 'viva')
    if not viva:
        return None

    if not config or not config.include_intermediate_marks:
        return float(viva.marks_awarded)

    marks = list(_final_marks(internship))
    weighted_total = Decimal('0')
    weight_total = Decimal('0')
    raw_scores = []

    for mark in marks:
        score = Decimal(mark.marks_awarded)
        raw_scores.append(score)
        weight = mark.weightage or mark.assessment_component.weightage or Decimal('0')
        if weight > 0:
            weighted_total += score * weight
            weight_total += weight

    if weight_total > 0:
        return float(weighted_total / weight_total)

    intermediate_avg = internship.assessment_marks.filter(
        assessment_component__assessment_type='intermediate',
        status__in=FINAL_STATUSES
    ).aggregate(avg=Avg('marks_awarded'))['avg']
    if intermediate_avg is not None:
        return (float(viva.marks_awarded) + float(intermediate_avg)) / 2

    return float(viva.marks_awarded)


def get_regular_score_details(student, config=None):
    slots = _regular_slots(config)
    regular_internships = student.internships.filter(
        internship_type='regular'
    ).prefetch_related('assessment_marks__assessment_component').select_related('organisation')

    details = []
    used_internship_ids = set()
    for slot in slots:
        internship = regular_internships.filter(internship_number=slot).order_by('-created_on').first()
        if internship:
            used_internship_ids.add(internship.id)
            score = calculate_internship_score(internship, config)
            viva = _latest_final_mark(internship, 'viva')
            details.append({
                'number': slot,
                'internship': internship,
                'organisation': internship.organisation.name if internship.organisation_id else '-',
                'score': round(score, 2) if score is not None else None,
                'viva_score': float(viva.marks_awarded) if viva else None,
                'completion_status': internship.get_completion_status_display(),
                'verification_status': internship.get_verification_status_display(),
                'missing_reason': '' if score is not None else 'Final viva marks missing',
            })
        else:
            details.append({
                'number': slot,
                'internship': None,
                'organisation': '-',
                'score': None,
                'viva_score': None,
                'completion_status': '-',
                'verification_status': '-',
                'missing_reason': 'Internship record missing',
            })

    extras = regular_internships.exclude(id__in=used_internship_ids).order_by('internship_number', 'created_on')
    for internship in extras:
        score = calculate_internship_score(internship, config)
        viva = _latest_final_mark(internship, 'viva')
        details.append({
            'number': internship.internship_number,
            'internship': internship,
            'organisation': internship.organisation.name if internship.organisation_id else '-',
            'score': round(score, 2) if score is not None else None,
            'viva_score': float(viva.marks_awarded) if viva else None,
            'completion_status': internship.get_completion_status_display(),
            'verification_status': internship.get_verification_status_display(),
            'missing_reason': '' if score is not None else 'Final viva marks missing',
        })

    return details


def get_assessment_viva_score(student):
    assessment_internship = student.internships.filter(
        internship_type='assessment'
    ).prefetch_related('assessment_marks__assessment_component').order_by('-created_on').first()
    if not assessment_internship:
        return None
    viva = _latest_final_mark(assessment_internship, 'viva')
    return float(viva.marks_awarded) if viva else None


def _average(scores):
    return sum(scores) / len(scores) if scores else 0


def calculate_student_average(student):
    config = _active_config(student)
    scores = [row['score'] for row in get_regular_score_details(student, config) if row['score'] is not None]
    return _average(scores)


def get_regular_viva_scores(student):
    config = _active_config(student)
    return [row['score'] for row in get_regular_score_details(student, config) if row['score'] is not None]


def calculate_weighted_average(student, config):
    scores = [row['score'] for row in get_regular_score_details(student, config) if row['score'] is not None]
    return _average(scores)


def calculate_best_n_average(student, config, top_n=None):
    details = get_regular_score_details(student, config)
    scored = sorted(
        [row for row in details if row['score'] is not None],
        key=lambda row: row['score'],
        reverse=True
    )
    selected_count = top_n or config.best_n_value or 5
    selected = scored[:selected_count]
    return _average([row['score'] for row in selected])


def calculate_student_consolidated_marks(student, top_n=None):
    """Calculate consolidated marks and return a report-ready explanation."""
    config = _active_config(student)
    details = get_regular_score_details(student, config)
    scored_details = [row for row in details if row['score'] is not None]
    regular_scores = [row['score'] for row in scored_details]
    regular_average = _average(regular_scores)
    assessment_score = get_assessment_viva_score(student)
    formula = config.calculation_formula if config else 'simple_average'
    selected_top_n = top_n or (config.best_n_value if config else None) or 5
    top_n_details = sorted(scored_details, key=lambda row: row['score'], reverse=True)[:selected_top_n]
    top_n_average = _average([row['score'] for row in top_n_details])

    if formula == 'weighted_average':
        final_score = regular_average
    elif formula == 'best_n':
        final_score = top_n_average
    elif formula == 'all_with_assessment':
        all_scores = list(regular_scores)
        if assessment_score is not None:
            all_scores.append(assessment_score)
        final_score = _average(all_scores)
    elif formula == 'separate_components':
        final_score = regular_average
    else:
        final_score = regular_average

    missing = [row for row in details if row['score'] is None]
    missing_labels = [
        f"Internship {row['number']}: {row['missing_reason']}"
        for row in missing
    ]

    return {
        'regular_average': round(regular_average, 2),
        'assessment_score': round(assessment_score, 2) if assessment_score is not None else None,
        'final_score': round(final_score, 2),
        'formula_used': _display_formula(config),
        'formula_key': formula,
        'regular_internship_count': len(_regular_slots(config)),
        'available_regular_count': len(scored_details),
        'missing_regular_count': len(missing),
        'missing_marks': missing_labels,
        'regular_details': details,
        'top_n_value': selected_top_n,
        'top_n_details': top_n_details,
        'top_n_average': round(top_n_average, 2),
        'intermediate_included': bool(config and config.include_intermediate_marks),
        'assessment_internship_enabled': True if not config else config.assessment_internship_enabled,
        'can_calculate': bool(scored_details),
    }


def calculate_batch_averages(batch):
    students = batch.students.filter(status='active')
    results = []
    for student in students:
        consolidated = calculate_student_consolidated_marks(student)
        results.append({
            'student': student,
            'average': consolidated.get('regular_average', 0),
            'final_score': consolidated.get('final_score', 0),
        })
    return results
