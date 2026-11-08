from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.db.models import Sum
from django.utils.timezone import now

from .models import (
    FinancialGroup, GroupMembership, FinancialAccount,
    Partner, Project, ProjectStatus, FinancialTransaction, TransactionType,
    Loan, LoanStatus, GroupType
)
from .services import AccountingService
from .calculations import FinancialCalculator
from .permissions import group_required, get_current_group, get_user_personal_group
from .forms import UserRegistrationForm, UserProfileForm

def user_register(request):
    """Public registration: creates account, signal auto-generates private personal workspace."""
    if request.user.is_authenticated:
        return redirect('finance:dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            personal_group = get_user_personal_group(user)
            request.session['active_group_id'] = personal_group.id
            messages.success(request, f"أهلاً بك {user.username}! تم إنشاء حسابك ومساحة عملك الشخصية الخاصة بنجاح.")
            return redirect('finance:dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'finance/register.html', {'form': form})

@login_required
def user_profile(request):
    """User profile page: edit name/email, change personal space default currency, and change password."""
    personal_group = get_user_personal_group(request.user)
    profile_form = UserProfileForm(instance=request.user, initial={'default_currency': personal_group.currency})
    password_form = PasswordChangeForm(user=request.user)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                new_currency = profile_form.cleaned_data.get('default_currency')
                if new_currency and new_currency.strip():
                    personal_group.currency = new_currency.strip().upper()
                    personal_group.save(update_fields=['currency'])
                messages.success(request, "تم تحديث البيانات الشخصية والعملة الافتراضية بنجاح.")
                return redirect('finance:profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "تم تغيير كلمة المرور بنجاح.")
                return redirect('finance:profile')

    return render(request, 'finance/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'personal_group': personal_group,
    })

def user_login(request):
    if request.user.is_authenticated:
        return redirect('finance:dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # CRITICAL: Always default to the user's private personal space upon login
            personal_group = get_user_personal_group(user)
            request.session['active_group_id'] = personal_group.id
            messages.success(request, f"مرحباً بك {user.username}. تم فتح ملفك وحسابك الشخصي.")
            return redirect('finance:dashboard')
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
    else:
        form = AuthenticationForm()
    return render(request, 'finance/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "تم تسجيل الخروج بنجاح.")
    return redirect('finance:login')

@group_required()
def dashboard(request, group, membership):
    metrics = FinancialCalculator.get_dashboard_metrics(group)
    recent_transactions = FinancialTransaction.objects.filter(group=group).select_related(
        'account', 'category', 'project', 'partner', 'contact'
    )[:8]
    active_loans = Loan.objects.filter(
        group=group,
        status__in=[LoanStatus.ACTIVE, LoanStatus.PARTIAL]
    ).select_related('contact').order_by('due_date', '-id')[:5]
    accounts = FinancialAccount.objects.filter(group=group, is_active=True)
    partners = [FinancialCalculator.get_member_partner_details(m) for m in group.memberships.all()]
    projects = Project.objects.filter(group=group, status=ProjectStatus.ACTIVE)[:4]

    # Chart data: monthly income vs expense for the active group
    current_year = now().year
    monthly_data = []
    for month in range(1, 13):
        m_inc = FinancialTransaction.objects.filter(
            group=group,
            transaction_type=TransactionType.INCOME,
            date__year=current_year,
            date__month=month,
            is_reversed=False,
            is_posted=True
        ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        m_exp = FinancialTransaction.objects.filter(
            group=group,
            transaction_type=TransactionType.EXPENSE,
            date__year=current_year,
            date__month=month,
            is_reversed=False,
            is_posted=True
        ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        monthly_data.append({'month': month, 'income': float(m_inc), 'expense': float(m_exp)})

    context = {
        'group': group,
        'membership': membership,
        'is_personal': group.group_type == GroupType.PERSONAL,
        'metrics': metrics,
        'recent_transactions': recent_transactions,
        'active_loans': active_loans,
        'accounts': accounts,
        'partners': partners,
        'projects': projects,
        'monthly_data': monthly_data,
        'current_year': current_year,
    }
    return render(request, 'finance/dashboard.html', context)
