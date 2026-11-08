from django.contrib import admin
from .models import (
    FinancialGroup, GroupMembership, GroupInvitation,
    FinancialAccount, Partner, Contact, Project,
    TransactionCategory, FinancialTransaction, Loan,
    LoanRepayment, PartnerSettlement, AuditLog
)

@admin.register(FinancialGroup)
class FinancialGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_type', 'currency', 'created_by', 'is_archived', 'created_at')
    list_filter = ('group_type', 'is_archived')
    search_fields = ('name', 'description')

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'role', 'joined_at')
    list_filter = ('role',)
    search_fields = ('group__name', 'user__username')

@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ('group', 'invited_user', 'invited_by', 'role', 'status', 'created_at')
    list_filter = ('status', 'role')

@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'account_type', 'opening_balance', 'current_balance', 'is_active')
    search_fields = ('name', 'bank_name', 'account_number', 'group__name')
    list_filter = ('group', 'account_type')

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'equity_share_pct', 'profit_share_pct', 'current_capital', 'is_active')
    search_fields = ('name', 'group__name')
    list_filter = ('group',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'category', 'phone')
    search_fields = ('name', 'group__name')
    list_filter = ('group', 'category')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'status', 'start_date', 'initial_budget')
    list_filter = ('group', 'status')

@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'category_type', 'is_system')
    list_filter = ('group', 'category_type')

@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_no', 'group', 'transaction_type', 'date', 'amount', 'account')
    list_filter = ('group', 'transaction_type', 'date')
    search_fields = ('reference_no', 'description')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'loan_type', 'contact', 'original_amount', 'remaining_balance', 'status')
    list_filter = ('group', 'loan_type', 'status')

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'loan', 'date', 'amount')
    list_filter = ('group',)

@admin.register(PartnerSettlement)
class PartnerSettlementAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'date', 'from_partner', 'to_partner', 'amount')
    list_filter = ('group',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'group', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('group',)
    readonly_fields = ('timestamp', 'group', 'user', 'action', 'model_name', 'object_id', 'summary')
