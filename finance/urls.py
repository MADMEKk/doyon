from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('register/', views.user_register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('', views.dashboard, name='dashboard'),
    
    # Financial Groups & Workspace Switching
    path('groups/', views.group_list, name='group_list'),
    path('groups/<int:group_id>/settings/', views.group_settings, name='group_settings'),
    path('groups/switch/<int:group_id>/', views.switch_group, name='switch_group'),
    path('groups/<int:group_id>/members/', views.group_members, name='group_members'),
    path('groups/<int:group_id>/members/remove/<int:member_id>/', views.remove_member, name='remove_member'),
    path('invitations/<int:invitation_id>/<str:action>/', views.respond_invitation, name='respond_invitation'),
    
    # Financial Accounts & Transfers
    path('accounts/', views.account_list, name='account_list'),
    path('transfers/add/', views.transfer_funds, name='transfer_funds'),
    
    # Income & Expense Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('income/add/', views.add_income, name='add_income'),
    path('expense/add/', views.add_expense, name='add_expense'),
    
    # Loans & Debts
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/add/', views.loan_create, name='loan_create'),
    path('loans/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    
    # Contacts
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/<int:contact_id>/', views.contact_detail, name='contact_detail'),
    
    # Reports & Audit
    path('reports/', views.reports_view, name='reports'),
    path('audit/', views.audit_logs_view, name='audit_logs'),
]
