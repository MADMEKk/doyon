from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models_group import FinancialGroup
from .models_core import FinancialAccount, Partner, Contact, Project, TransactionCategory

class TransactionType(models.TextChoices):
    INCOME = 'INCOME', _('إيراد أعمال')
    EXPENSE = 'EXPENSE', _('مصروف أعمال')
    TRANSFER = 'TRANSFER', _('تحويل بين الحسابات')
    CAPITAL_IN = 'CAPITAL_IN', _('مساهمة رأس مال شريك')
    CAPITAL_OUT = 'CAPITAL_OUT', _('مسحوبات شريك')
    LOAN_BORROW = 'LOAN_BORROW', _('اقتراض من الغير (+نقدية)')
    LOAN_REPAY = 'LOAN_REPAY', _('سداد قرض للغير (-نقدية)')
    LOAN_LEND = 'LOAN_LEND', _('إقراض للغير (-نقدية)')
    LOAN_RECOVER = 'LOAN_RECOVER', _('استرداد قرض ممنوح للغير (+نقدية)')
    PARTNER_SETTLE = 'PARTNER_SETTLE', _('تسوية مالية بين الشركاء')

class FinancialTransaction(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='transactions', verbose_name=_('المجموعة المالية'))
    reference_no = models.CharField(max_length=50, unique=True, verbose_name=_('رقم المعاملة / السند'))
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, verbose_name=_('نوع العملية'))
    date = models.DateField(verbose_name=_('تاريخ المعاملة'))
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('المبلغ'))
    currency = models.CharField(max_length=10, default='SAR', verbose_name=_('عملة المعاملة'))
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('1.000000'), verbose_name=_('سعر الصرف لعملة الأساس'))
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('المبلغ بعملة أساس المجموعة'))
    
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name='transactions', verbose_name=_('الحساب المالي الأساسي'))
    to_account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name='inward_transfers', verbose_name=_('الحساب المحول إليه (للتحويلات)'))
    
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_('التصنيف'))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_('المشروع المرتبط'))
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_('الشريك المعني'))
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_('جهة الاتصال'))
    
    description = models.CharField(max_length=255, verbose_name=_('البيان / الوصف'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات تفصيلية'))
    attachment = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True, verbose_name=_('المرفق / الفاتورة'))
    
    is_posted = models.BooleanField(default=True, verbose_name=_('مرحل للحسابات'))
    is_reversed = models.BooleanField(default=False, verbose_name=_('معكوس / ملغي'))
    reversed_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversal_entry', verbose_name=_('قيد العكس'))
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('المستخدم المنشئ'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('معاملة مالية')
        verbose_name_plural = _('المعاملات المالية')

    def __str__(self):
        return f"{self.reference_no} | {self.get_transaction_type_display()} | {self.amount:,.2f}"

class LoanType(models.TextChoices):
    BORROWED = 'BORROWED', _('قرض مستحق علينا (اقترضنا من الغير)')
    LENT = 'LENT', _('قرض ممنوح للغير (أقرضنا شخصاً آخر)')

class LoanStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('قائم / غير مسدد')
    PARTIAL = 'PARTIAL', _('مسدد جزئياً')
    PAID = 'PAID', _('مسدد بالكامل')
    OVERDUE = 'OVERDUE', _('متأخر عن موعده')

class Loan(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='loans', verbose_name=_('المجموعة المالية'))
    loan_type = models.CharField(max_length=15, choices=LoanType.choices, verbose_name=_('نوع القرض / الدين'))
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name='loans', verbose_name=_('الطرف الآخر (دائن أو مدين)'))
    original_amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('أصل المبلغ المستحق'))
    currency = models.CharField(max_length=10, default='SAR', verbose_name=_('عملة الدين'))
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('1.000000'), verbose_name=_('سعر الصرف لعملة الأساس'))
    principal_repaid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('المبلغ المسدد حتى الآن'))
    remaining_balance = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('المتبقي للسداد'))
    interest_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('إجمالي الفائدة / الرسوم (إن وجدت)'))
    
    issue_date = models.DateField(verbose_name=_('تاريخ المعاملة'))
    due_date = models.DateField(blank=True, null=True, verbose_name=_('تاريخ الاستحقاق'))
    status = models.CharField(max_length=15, choices=LoanStatus.choices, default=LoanStatus.ACTIVE, verbose_name=_('حالة الدين'))
    
    initial_account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name='loans_initiated', verbose_name=_('الحساب المستلم/الدافع'))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans', verbose_name=_('المشروع المرتبط'))
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans_managed', verbose_name=_('الشريك المسؤول'))
    
    notes = models.TextField(blank=True, verbose_name=_('الشروط والملاحظات'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-id']
        verbose_name = _('قرض / دين')
        verbose_name_plural = _('الديون والقروض')

    def __str__(self):
        return f"{self.get_loan_type_display()} - {self.contact.name}: {self.remaining_balance:,.2f}"

class LoanRepayment(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='repayments', verbose_name=_('المجموعة المالية'))
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments', verbose_name=_('الدين المرتبط'))
    date = models.DateField(verbose_name=_('تاريخ الدفعة'))
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('المبلغ المسدد (أصل الدين)'))
    interest_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name=_('مبلغ الفائدة المضمن'))
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name='loan_repayments', verbose_name=_('الحساب المالي المستخدم'))
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('الشريك القائم بالعملية'))
    transaction = models.OneToOneField(FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_repayment_record')
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('دفعة سداد دين')
        verbose_name_plural = _('دفعات سداد الديون')

    def __str__(self):
        return f"سداد {self.amount:,.2f} لدين #{self.loan_id} ({self.date})"

class PartnerSettlement(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, related_name='settlements', verbose_name=_('المجموعة المالية'))
    from_partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='settlements_paid', verbose_name=_('الشريك الدافع / المدين'))
    to_partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='settlements_received', verbose_name=_('الشريك المستلم / الدائن'))
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('مبلغ التسوية'))
    date = models.DateField(verbose_name=_('تاريخ التسوية'))
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('الحساب المشترك (إن تم عبر الشركة)'))
    is_direct_cash = models.BooleanField(default=True, verbose_name=_('تسوية مباشرة خارج حسابات الشركة'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات وتفاصيل التوزيع'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('تسوية بين الشركاء')
        verbose_name_plural = _('تسويات الشركاء')

    def __str__(self):
        return f"تسوية من {self.from_partner.name} إلى {self.to_partner.name}: {self.amount:,.2f}"

class AuditLog(models.Model):
    group = models.ForeignKey(FinancialGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs', verbose_name=_('المجموعة المالية'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('المستخدم'))
    action = models.CharField(max_length=60, verbose_name=_('نوع الإجراء'))
    model_name = models.CharField(max_length=60, verbose_name=_('السجل المعني'))
    object_id = models.CharField(max_length=60, verbose_name=_('معرف السجل'))
    summary = models.TextField(verbose_name=_('الملخص المالي للتغيير'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('الوقت والتاريخ'))

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('سجل تدقيق مالي')
        verbose_name_plural = _('سجلات التدقيق المالي')

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user}: {self.action} on {self.model_name}"
