from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
from django.contrib.auth.models import User

from .models import (
    FinancialGroup, GroupMembership, GroupInvitation,
    GroupRole, GroupType, InvitationStatus
)
from .forms import FinancialGroupForm, GroupInviteForm, GroupEditForm, ExternalPartnerForm
from .permissions import get_current_group

@login_required
def group_list(request):
    memberships = GroupMembership.objects.filter(user=request.user).select_related('group')
    invitations = GroupInvitation.objects.filter(invited_user=request.user, status=InvitationStatus.PENDING)
    active_group = get_current_group(request)

    if request.method == 'POST' and 'create_group' in request.POST:
        form = FinancialGroupForm(request.POST, request.FILES)
        if form.is_valid():
            grp = form.save(commit=False)
            grp.created_by = request.user
            grp.save()
            GroupMembership.objects.create(group=grp, user=request.user, role=GroupRole.OWNER)
            request.session['active_group_id'] = grp.id
            messages.success(request, f"تم إنشاء المجموعة المالية '{grp.name}' بنجاح وتعيينها كمساحة العمل الحالية.")
            return redirect('finance:dashboard')
    else:
        form = FinancialGroupForm()

    return render(request, 'finance/groups.html', {
        'memberships': memberships,
        'invitations': invitations,
        'active_group': active_group,
        'form': form,
    })

@login_required
def switch_group(request, group_id):
    membership = get_object_or_404(GroupMembership, group_id=group_id, user=request.user, group__is_archived=False)
    request.session['active_group_id'] = membership.group_id
    messages.success(request, f"تم التبديل بنجاح إلى مساحة العمل: {membership.group.name}")
    return redirect('finance:dashboard')

@login_required
def group_members(request, group_id):
    membership = get_object_or_404(GroupMembership, group_id=group_id, user=request.user)
    if not membership.can_manage_members:
        raise PermissionDenied("ليس لديك صلاحية لإدارة أعضاء هذه المجموعة.")

    group = membership.group
    members = group.memberships.select_related('user').all()
    pending_invites = group.invitations.filter(status=InvitationStatus.PENDING)

    invite_form = GroupInviteForm()
    external_form = ExternalPartnerForm()

    if request.method == 'POST':
        if 'invite_user' in request.POST:
            invite_form = GroupInviteForm(request.POST)
            if invite_form.is_valid():
                query = invite_form.cleaned_data['username_or_email'].strip()
                role = invite_form.cleaned_data['role']
                target_user = User.objects.filter(username=query).first() or User.objects.filter(email=query).first()
                if not target_user:
                    messages.error(request, f"لم يتم العثور على أي مستخدم بالاسم أو البريد: {query}")
                elif GroupMembership.objects.filter(group=group, user=target_user).exists():
                    messages.warning(request, f"المستخدم {target_user.username} عضو بالفعل في هذه المجموعة.")
                elif GroupInvitation.objects.filter(group=group, invited_user=target_user, status=InvitationStatus.PENDING).exists():
                    messages.info(request, f"توجد دعوة معلقة بالفعل للمستخدم {target_user.username}.")
                else:
                    GroupInvitation.objects.create(
                        group=group,
                        invited_user=target_user,
                        invited_by=request.user,
                        role=role
                    )
                    messages.success(request, f"تم إرسال دعوة الانضمام للمستخدم {target_user.username} بنجاح.")
                    return redirect('finance:group_members', group_id=group.id)
        elif 'add_external_partner' in request.POST:
            external_form = ExternalPartnerForm(request.POST)
            if external_form.is_valid():
                part = external_form.save(commit=False)
                part.group = group
                part.current_capital = part.initial_capital
                part.save()
                messages.success(request, f"تمت إضافة الشريك '{part.get_name()}' إلى المجموعة بنجاح وتوثيق حصته ورأس ماله.")
                return redirect('finance:group_members', group_id=group.id)

    return render(request, 'finance/group_members.html', {
        'group': group,
        'membership': membership,
        'members': members,
        'pending_invites': pending_invites,
        'form': invite_form,
        'external_form': external_form,
    })

@login_required
def respond_invitation(request, invitation_id, action):
    invite = get_object_or_404(GroupInvitation, id=invitation_id, invited_user=request.user, status=InvitationStatus.PENDING)
    if action == 'accept':
        invite.status = InvitationStatus.ACCEPTED
        invite.responded_at = now()
        invite.save(update_fields=['status', 'responded_at'])
        GroupMembership.objects.get_or_create(
            group=invite.group,
            user=request.user,
            defaults={'role': invite.role}
        )
        request.session['active_group_id'] = invite.group.id
        messages.success(request, f"تم قبول الدعوة والانضمام إلى المجموعة {invite.group.name}.")
    elif action == 'reject':
        invite.status = InvitationStatus.REJECTED
        invite.responded_at = now()
        invite.save(update_fields=['status', 'responded_at'])
        messages.info(request, f"تم رفض دعوة الانضمام للمجموعة {invite.group.name}.")
    return redirect('finance:group_list')

@login_required
def remove_member(request, group_id, member_id):
    current_membership = get_object_or_404(GroupMembership, group_id=group_id, user=request.user)
    if not current_membership.can_manage_members:
        raise PermissionDenied("ليس لديك الصلاحية لإزالة أعضاء.")

    target_membership = get_object_or_404(GroupMembership, id=member_id, group_id=group_id)
    if target_membership.role == GroupRole.OWNER:
        messages.error(request, "لا يمكن إزالة مالك المجموعة.")
    else:
        username = target_membership.user.username
        target_membership.delete()
        messages.success(request, f"تمت إزالة العضو {username} بنجاح.")
    return redirect('finance:group_members', group_id=group_id)


@login_required
def group_settings(request, group_id):
    """Edit group settings (name, description, logo, currency, archive). Only owner/admin."""
    membership = get_object_or_404(GroupMembership, group_id=group_id, user=request.user)
    if not membership.can_manage_settings:
        raise PermissionDenied("ليس لديك صلاحية لتعديل إعدادات هذه المجموعة.")
    
    group = membership.group
    if request.method == 'POST':
        if 'archive_group' in request.POST:
            if group.group_type == GroupType.PERSONAL:
                messages.error(request, "لا يمكن أرشفة مساحة العمل الشخصية الأساسية.")
            else:
                group.is_archived = not group.is_archived
                group.save(update_fields=['is_archived'])
                status_txt = "أرشفتها" if group.is_archived else "إلغاء أرشفتها"
                messages.success(request, f"تم {status_txt} بنجاح.")
                return redirect('finance:group_list')
        else:
            form = GroupEditForm(request.POST, request.FILES, instance=group)
            if form.is_valid():
                form.save()
                messages.success(request, "تم حفظ إعدادات المجموعة بنجاح.")
                return redirect('finance:group_settings', group_id=group.id)
    else:
        form = GroupEditForm(instance=group)

    return render(request, 'finance/group_settings.html', {
        'group': group,
        'membership': membership,
        'form': form,
    })


