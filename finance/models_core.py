from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models_group import FinancialGroup

class AccountType(models.TextChoices):
    CASH = 'CASH', _('نقدي / صندوق')
    BANK = 'BANK', _('حساب بنكي')
    WALLET = 'WALLET', _('محفظة إلكترونية')
    OTHER = 'OTHER', _('أخرى')

class FinancialAccount(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='accounts', verbose_name=_('المجموعة المالية'))
    name = models.CharField(max_length=120, verbose_name=_('اسم الحساب'))
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CASH, verbose_name=_('نوع الحساب'))
    account_number = models.CharField(max_length=60, blank=True, null=True, verbose_name=_('رقم الحساب / الآيبان'))
    bank_name = models.CharField(max_length=120, blank=True, null=True, verbose_name=_('اسم البنك'))
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('الرصيد الافتتاحي'))
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('الرصيد الحالي'))
    currency = models.CharField(max_length=10, default='SAR', verbose_name=_('عملة الحساب'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('group', 'name')
        verbose_name = _('حساب مالي')
        verbose_name_plural = _('الحسابات المالية')

    def __str__(self):
        return f"{self.name} [{self.group.name}] - {self.current_balance:,.2f}"

class Partner(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='partners', verbose_name=_('المجموعة المالية'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='partner_profiles', verbose_name=_('المستخدم المقترن'))
    name = models.CharField(max_length=120, verbose_name=_('اسم الشريك'))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_('الهاتف'))
    email = models.EmailField(blank=True, verbose_name=_('البريد الإلكتروني'))
    initial_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('رأس المال التأسيسي'))
    total_contributions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('إجمالي المساهمات الإضافية'))
    total_withdrawals = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('إجمالي المسحوبات الشخصية'))
    current_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('رصيد رأس المال الحالي'))
    equity_share_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('نسبة ملكية رأس المال %')
    )
    profit_share_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('نسبة اقتسام الأرباح والخسائر %')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        unique_together = ('group', 'name')
        verbose_name = _('شريك')
        verbose_name_plural = _('الشركاء')

    def __str__(self):
        return f"{self.name} ({self.group.name} - حصة: {self.profit_share_pct}%)"

class ContactCategory(models.TextChoices):
    LENDER = 'LENDER', _('مقرض (دائن)')
    BORROWER = 'BORROWER', _('مقترض (مدين)')
    CUSTOMER = 'CUSTOMER', _('عميل')
    SUPPLIER = 'SUPPLIER', _('مورد')
    OTHER = 'OTHER', _('جهة أخرى')

class Contact(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='contacts', verbose_name=_('المجموعة المالية'))
    name = models.CharField(max_length=150, verbose_name=_('اسم جهة الاتصال'))
    category = models.CharField(max_length=20, choices=ContactCategory.choices, default=ContactCategory.LENDER, verbose_name=_('التصنيف الأساسي'))
    phone = models.CharField(max_length=40, blank=True, verbose_name=_('رقم الهاتف'))
    email = models.EmailField(blank=True, verbose_name=_('البريد الإلكتروني'))
    address = models.CharField(max_length=255, blank=True, verbose_name=_('العنوان'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('group', 'name')
        verbose_name = _('جهة اتصال')
        verbose_name_plural = _('جهات الاتصال')

    def __str__(self):
        return f"{self.name} ({self.group.name} - {self.get_category_display()})"

class ProjectStatus(models.TextChoices):
    PLANNED = 'PLANNED', _('مخطط له')
    ACTIVE = 'ACTIVE', _('قيد التنفيذ')
    COMPLETED = 'COMPLETED', _('مكتمل')
    CANCELLED = 'CANCELLED', _('ملغى')

class Project(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='projects', verbose_name=_('المجموعة المالية'))
    name = models.CharField(max_length=150, verbose_name=_('اسم المشروع'))
    description = models.TextField(blank=True, verbose_name=_('وصف المشروع'))
    status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.ACTIVE, verbose_name=_('الحالة'))
    start_date = models.DateField(verbose_name=_('تاريخ البدء'))
    end_date = models.DateField(blank=True, null=True, verbose_name=_('تاريخ الانتهاء المخطط/الفعلي'))
    initial_budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('الميزانية التقديرية'))
    partners = models.ManyToManyField(Partner, blank=True, related_name='projects', verbose_name=_('الشركاء المشاركون'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', 'name']
        unique_together = ('group', 'name')
        verbose_name = _('مشروع')
        verbose_name_plural = _('المشاريع')

    def __str__(self):
        return f"{self.name} ({self.group.name})"

class CategoryType(models.TextChoices):
    INCOME = 'INCOME', _('إيراد / دخل')
    EXPENSE = 'EXPENSE', _('مصروف تشغيلي')

class TransactionCategory(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='categories', verbose_name=_('المجموعة المالية'))
    name = models.CharField(max_length=100, verbose_name=_('اسم البند / التصنيف'))
    category_type = models.CharField(max_length=10, choices=CategoryType.choices, verbose_name=_('نوع البند'))
    description = models.TextField(blank=True, verbose_name=_('الوصف'))
    is_system = models.BooleanField(default=False, verbose_name=_('تصنيف نظام'))

    class Meta:
        ordering = ['category_type', 'name']
        unique_together = ('group', 'name', 'category_type')
        verbose_name = _('تصنيف معاملة')
        verbose_name_plural = _('تصنيفات المعاملات')

    def __str__(self):
        return f"{self.name} [{self.get_category_type_display()}]"
