from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import FinancialGroup, GroupMembership, GroupRole, GroupType

def get_user_personal_group(user):
    """
    Finds or automatically creates the user's private Personal Finance workspace.
    This workspace is strictly personal and private to the user.
    """
    membership = GroupMembership.objects.filter(
        user=user,
        group__created_by=user,
        group__group_type=GroupType.PERSONAL,
        group__is_archived=False
    ).select_related('group').first()

    if membership:
        return membership.group

    # Create user's private personal workspace
    personal_group = FinancialGroup.objects.create(
        name=f"حسابي الشخصي - {user.first_name or user.username}",
        description="مساحة العمل الشخصية الخاصة بي (ديوني، مستحقاتي، ومصروفاتي الخاصة)",
        group_type=GroupType.PERSONAL,
        currency="SAR",
        created_by=user
    )
    GroupMembership.objects.create(
        group=personal_group,
        user=user,
        role=GroupRole.OWNER
    )
    return personal_group

def get_current_group(request):
    """
    Resolves the active workspace for the logged-in user.
    On fresh login or when no active group is chosen, it strictly defaults
    to the user's private Personal Finance group.
    Shared groups are only entered when the user explicitly selects them.
    """
    if not request.user.is_authenticated:
        return None

    group_id = request.session.get('active_group_id')
    if group_id:
        membership = GroupMembership.objects.filter(
            user=request.user, group_id=group_id, group__is_archived=False
        ).select_related('group').first()
        if membership:
            return membership.group

    # First login or reset: strictly use Personal Group
    personal_group = get_user_personal_group(request.user)
    request.session['active_group_id'] = personal_group.id
    return personal_group

def group_required(roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('finance:login')

            group = get_current_group(request)
            if not group:
                messages.error(request, "يرجى إنشاء مساحة عمل أو الانضمام إليها أولاً.")
                return redirect('finance:group_list')

            membership = GroupMembership.objects.filter(group=group, user=request.user).first()
            if not membership:
                raise PermissionDenied("ليس لديك تصريح للوصول إلى هذه المساحة المالية.")

            if roles and membership.role not in roles:
                raise PermissionDenied("ليس لديك الصلاحية الكافية لتنفيذ هذا الإجراء.")

            return view_func(request, group, membership, *args, **kwargs)
        return _wrapped_view
    return decorator
