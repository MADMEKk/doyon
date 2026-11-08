from .views_main import user_login, user_logout, dashboard, user_register, user_profile
from .views_groups import (
    group_list, switch_group, group_members,
    respond_invitation, remove_member, group_settings
)
from .views_transactions import (
    transaction_list, add_income, add_expense, transfer_funds, account_list
)
from .views_modules import (
    loan_list, loan_create, loan_detail,
    project_list, project_detail, contact_list, contact_detail,
    reports_view, audit_logs_view
)

__all__ = [
    'user_login', 'user_logout', 'dashboard', 'user_register', 'user_profile',
    'group_list', 'switch_group', 'group_members', 'respond_invitation', 'remove_member', 'group_settings',
    'transaction_list', 'add_income', 'add_expense', 'transfer_funds', 'account_list',
    'loan_list', 'loan_create', 'loan_detail',
    'project_list', 'project_detail', 'contact_list', 'contact_detail',
    'reports_view', 'audit_logs_view'
]
