def user_name_with_role(user):
    if not user:
        return '-'

    name = user.get_full_name() or user.email
    if hasattr(user, 'profile'):
        return f'{name} ({user.profile.get_role_display()})'
    return name
