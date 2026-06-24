# apps/utils/calculations.py

from decimal import Decimal

from django.db.models import Avg

from apps.core.models import AssessmentConfiguration

FINAL_STATUSES = ['approved', 'locked']


def calculate_internship_score(internship):
    """Calculate score for a single internship"""
    viva_marks = internship.assessment_marks.filter(
        assessment_component__assessment_type='viva',
        status__in=FINAL_STATUSES
    ).order_by('-assessment_date', '-created_on').first()
    if not viva_marks:
        return None
    
    return float(viva_marks.marks_awarded)


def calculate_student_average(student):
    """Calculate average of all regular internships for a student"""
    regular_internships = student.internships.filter(
        internship_type='regular',
        completion_status='completed'
    )
    
    total_marks = 0
    count = 0
    
    for internship in regular_internships:
        viva_marks = internship.assessment_marks.filter(
            assessment_component__assessment_type='viva',
            status__in=FINAL_STATUSES
        ).order_by('-assessment_date', '-created_on').first()
        if viva_marks:
            total_marks += float(viva_marks.marks_awarded)
            count += 1
    
    if count > 0:
        return total_marks / count
    return 0


def get_regular_viva_scores(student):
    regular_internships = student.internships.filter(
        internship_type='regular',
        completion_status='completed'
    )
    scores = []
    for internship in regular_internships:
        viva_marks = internship.assessment_marks.filter(
            assessment_component__assessment_type='viva',
            status__in=FINAL_STATUSES
        ).order_by('-assessment_date', '-created_on').first()
        if viva_marks:
            scores.append(float(viva_marks.marks_awarded))
    return scores


def get_assessment_viva_score(student):
    assessment_internship = student.internships.filter(
        internship_type='assessment'
    ).first()
    if not assessment_internship:
        return None
    viva = assessment_internship.assessment_marks.filter(
        assessment_component__assessment_type='viva',
        status__in=FINAL_STATUSES
    ).order_by('-assessment_date', '-created_on').first()
    return float(viva.marks_awarded) if viva else None


def calculate_weighted_average(student, config):
    """Calculate weighted average including intermediate marks"""
    regular_internships = student.internships.filter(
        internship_type='regular',
        completion_status='completed'
    )
    
    total_score = 0
    count = 0
    
    for internship in regular_internships:
        viva = internship.assessment_marks.filter(
            assessment_component__assessment_type='viva',
            status__in=FINAL_STATUSES
        ).order_by('-assessment_date', '-created_on').first()
        if not viva:
            continue
        
        if config.include_intermediate_marks:
            intermediate_marks = internship.assessment_marks.filter(
                assessment_component__assessment_type='intermediate',
                status__in=FINAL_STATUSES
            )
            if intermediate_marks.exists():
                avg_intermediate = intermediate_marks.aggregate(Avg('marks_awarded'))['marks_awarded__avg']
                if avg_intermediate:
                    score = (float(avg_intermediate) + float(viva.marks_awarded)) / 2
                else:
                    score = float(viva.marks_awarded)
            else:
                score = float(viva.marks_awarded)
        else:
            score = float(viva.marks_awarded)
        
        total_score += score
        count += 1
    
    if count > 0:
        return total_score / count
    return 0


def calculate_best_n_average(student, config):
    """Calculate average of best N internships"""
    regular_internships = student.internships.filter(
        internship_type='regular',
        completion_status='completed'
    )
    
    marks_list = []
    for internship in regular_internships:
        viva = internship.assessment_marks.filter(
            assessment_component__assessment_type='viva',
            status__in=FINAL_STATUSES
        ).order_by('-assessment_date', '-created_on').first()
        if viva:
            marks_list.append(float(viva.marks_awarded))
    
    if not marks_list:
        return 0
    
    marks_list.sort(reverse=True)
    best_n = config.best_n_value or 5
    best_marks = marks_list[:best_n]
    
    return sum(best_marks) / len(best_marks)


def calculate_student_consolidated_marks(student):
    """Calculate consolidated marks based on configuration"""
    
    from apps.core.models import AssessmentConfiguration
    
    # Get configuration for student's programme
    config = AssessmentConfiguration.objects.filter(
        programme=student.programme,
        is_active=True
    ).first()
    
    if not config:
        # Default calculation
        regular_average = calculate_student_average(student)
        assessment_score = get_assessment_viva_score(student)
        
        return {
            'regular_average': round(regular_average, 2),
            'assessment_score': assessment_score,
            'final_score': round(regular_average, 2) if assessment_score is None else round((regular_average + assessment_score) / 2, 2),
            'formula_used': 'Default (Simple Average)'
        }
    
    # Use configured formula
    if config.calculation_formula == 'simple_average':
        regular_average = calculate_student_average(student)
        final_score = regular_average
        
    elif config.calculation_formula == 'weighted_average':
        regular_average = calculate_weighted_average(student, config)
        final_score = regular_average
        
    elif config.calculation_formula == 'best_n':
        regular_average = calculate_best_n_average(student, config)
        final_score = regular_average
        
    elif config.calculation_formula == 'all_with_assessment':
        regular_average = calculate_student_average(student)
        assessment_score = get_assessment_viva_score(student)
        all_scores = get_regular_viva_scores(student)
        if assessment_score is not None:
            all_scores.append(assessment_score)
        if all_scores:
            final_score = sum(all_scores) / len(all_scores)
        else:
            final_score = regular_average
            
    else:  # separate_components
        regular_average = calculate_student_average(student)
        assessment_score = get_assessment_viva_score(student)
        
        return {
            'regular_average': round(regular_average, 2),
            'assessment_score': assessment_score,
            'final_score': round(regular_average, 2),
            'formula_used': dict(AssessmentConfiguration._meta.get_field('calculation_formula').choices).get(config.calculation_formula)
        }
    
    return {
        'regular_average': round(regular_average, 2) if 'regular_average' in locals() else 0,
        'assessment_score': assessment_score if 'assessment_score' in locals() else None,
        'final_score': round(final_score, 2) if 'final_score' in locals() else 0,
        'formula_used': dict(AssessmentConfiguration._meta.get_field('calculation_formula').choices).get(config.calculation_formula)
    }


def calculate_batch_averages(batch):
    """Calculate averages for all students in a batch"""
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
