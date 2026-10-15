import re

from django.core.exceptions import ValidationError


def validate_mobile_number(value):
    """Allow optional blanks; supplied numbers must contain ten ASCII digits."""
    if value is None or value == '':
        return ''
    value = str(value)
    if not re.fullmatch(r'[0-9]{10}', value):
        raise ValidationError('Enter exactly 10 digits (0-9) for the mobile number.', code='invalid_mobile')
    return value
