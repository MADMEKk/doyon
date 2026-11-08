from .models import FinancialGroup, GroupMembership, GroupInvitation, InvitationStatus
from .permissions import get_current_group

def system_context(request):
    if not request.user.is_authenticated:
        return {}
    
    user_memberships = GroupMembership.objects.filter(
        user=request.user, group__is_archived=False
    ).select_related('group')
    
    current_group = get_current_group(request)
    pending_invites_count = GroupInvitation.objects.filter(
        invited_user=request.user, status=InvitationStatus.PENDING
    ).count()

    return {
        'user_memberships': user_memberships,
        'current_group': current_group,
        'pending_invites_count': pending_invites_count,
        'app_name': 'نظام إدارة الشراكة والمجموعات المالية',
    }
