from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid

class GroupType(models.TextChoices):
    PERSONAL = 'PERSONAL', _('شخصي (خاص)')
    PARTNERSHIP = 'PARTNERSHIP', _('شراكة أعمال')
    BUSINESS = 'BUSINESS', _('شركة تجارية')
    PROJECT = 'PROJECT', _('مشروع مالي مستقل')
    OTHER = 'OTHER', _('أخرى')

from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class GroupRole(models.TextChoices):
    OWNER = 'OWNER', _('المالك / شريك رئيسي')
    ADMIN = 'ADMIN', _('مدير (إدارة الأعضاء والعمليات)')
    ACCOUNTANT = 'ACCOUNTANT', _('محاسب (إدارة المعاملات والتقارير)')
    MEMBER = 'MEMBER', _('شريك / عضو')
    VIEWER = 'VIEWER', _('مشاهد (قراءة فقط)')

class FinancialGroup(models.Model):
    name = models.CharField(max_length=150, verbose_name=_('اسم المجموعة المالية'))
    description = models.TextField(blank=True, verbose_name=_('وصف المجموعة'))
    group_type = models.CharField(max_length=20, choices=GroupType.choices, default=GroupType.PARTNERSHIP, verbose_name=_('نوع المجموعة'))
    logo = models.ImageField(upload_to='group_logos/', blank=True, null=True, verbose_name=_('شعار المجموعة'))
    currency = models.CharField(max_length=10, default='SAR', verbose_name=_('العملة الافتراضية'))
    is_archived = models.BooleanField(default=False, verbose_name=_('مؤرشف'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_groups', verbose_name=_('المنشئ'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('مجموعة مالية')
        verbose_name_plural = _('المجموعات المالية')

    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"

class GroupMembership(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='memberships', verbose_name=_('المجموعة المالية'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='group_memberships', verbose_name=_('المستخدم المقترن (اختياري)'))
    
    # Display name and contact for members/partners (required if user is null)
    display_name = models.CharField(max_length=150, blank=True, verbose_name=_('اسم الشريك / العضو'))
    phone = models.CharField(max_length=40, blank=True, verbose_name=_('رقم الهاتف'))
    email = models.EmailField(blank=True, verbose_name=_('البريد الإلكتروني'))
    
    role = models.CharField(max_length=20, choices=GroupRole.choices, default=GroupRole.MEMBER, verbose_name=_('الدور'))
    
    # Financial partnership attributes (Unifying Partner into Membership)
    initial_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('رأس المال التأسيسي'))
    current_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('رأس المال الحالي'))
    equity_share_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('نسبة ملكية رأس المال %')
    )
    profit_share_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('نسبة توزيع الأرباح %')
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['group', 'role']
        verbose_name = _('عضوية وشراكة المجموعة')
        verbose_name_plural = _('عضويات وشركاء المجموعات')

    def __str__(self):
        name = self.get_name()
        return f"{name} - {self.group.name} ({self.get_role_display()})"

    def get_name(self):
        if self.display_name:
            return self.display_name
        if self.user:
            return self.user.get_full_name() or self.user.username
        return "عضو بدون اسم"

    @property
    def can_manage_settings(self):
        return self.role in [GroupRole.OWNER, GroupRole.ADMIN]

    @property
    def can_manage_members(self):
        return self.role in [GroupRole.OWNER, GroupRole.ADMIN]

    @property
    def can_edit_finances(self):
        return self.role in [GroupRole.OWNER, GroupRole.ADMIN, GroupRole.ACCOUNTANT, GroupRole.MEMBER]

    @property
    def is_read_only(self):
        return self.role == GroupRole.VIEWER

class InvitationStatus(models.TextChoices):
    PENDING = 'PENDING', _('قيد الانتظار')
    ACCEPTED = 'ACCEPTED', _('مقبولة')
    REJECTED = 'REJECTED', _('مرفوضة')
    CANCELLED = 'CANCELLED', _('ملغاة')

class GroupInvitation(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='invitations', verbose_name=_('المجموعة المالية'))
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_group_invitations', verbose_name=_('المستخدم المدعو'))
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_invitations', verbose_name=_('تمت الدعوة بواسطة'))
    role = models.CharField(max_length=20, choices=GroupRole.choices, default=GroupRole.MEMBER, verbose_name=_('الدور المقترح'))
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING, verbose_name=_('حالة الدعوة'))
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('دعوة انضمام لمجموعة')
        verbose_name_plural = _('دعوات الانضمام للمجموعات')

    def __str__(self):
        return f"دعوة {self.invited_user.username} إلى {self.group.name} [{self.get_status_display()}]"

