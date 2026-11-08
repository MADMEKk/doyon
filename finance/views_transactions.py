from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from .models import (
    FinancialAccount, Partner, Contact, ContactCategory, Project,
    TransactionCategory, FinancialTransaction, TransactionType
)
from .services import AccountingService
from .forms import (
    IncomeExpenseForm, TransferForm, FinancialAccountForm
)
from .exports import ExportService
from .permissions import group_required

@group_required()
def transaction_list(request, group, membership):
    txns = FinancialTransaction.objects.filter(group=group).select_related(
        'account', 'to_account', 'category', 'project', 'partner', 'contact'
    )
    
    txn_type = request.GET.get('type')
    account_id = request.GET.get('account')
    project_id = request.GET.get('project')
    partner_id = request.GET.get('partner')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    q = request.GET.get('q')

    if txn_type:
        txns = txns.filter(transaction_type=txn_type)
    if account_id:
        txns = txns.filter(Q(account_id=account_id) | Q(to_account_id=account_id))
    if project_id:
        txns = txns.filter(project_id=project_id)
    if partner_id:
        txns = txns.filter(partner_id=partner_id)
    if date_from:
        txns = txns.filter(date__gte=date_from)
    if date_to:
        txns = txns.filter(date__lte=date_to)
    if q:
        txns = txns.filter(Q(description__icontains=q) | Q(reference_no__icontains=q) | Q(notes__icontains=q))

    export = request.GET.get('export')
    if export == 'csv':
        return ExportService.export_transactions_csv(txns)
    elif export == 'excel':
        return ExportService.export_transactions_excel(txns)

    paginator = Paginator(txns, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'group': group,
        'membership': membership,
        'page_obj': page_obj,
        'types': TransactionType.choices,
        'accounts': FinancialAccount.objects.filter(group=group, is_active=True),
        'projects': Project.objects.filter(group=group),
        'partners': Partner.objects.filter(group=group, is_active=True),
    }
    return render(request, 'finance/transactions.html', context)

@group_required()
def add_income(request, group, membership):
    if not membership.can_edit_finances:
        raise PermissionDenied("ليس لديك صلاحية لتسجيل معاملات في هذه المجموعة.")

    if request.method == 'POST':
        form = IncomeExpenseForm(group, request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            contact = cd.get('contact')
            # If external person name provided on the fly
            if not contact and cd.get('external_person_name'):
                person_name = cd['external_person_name'].strip()
                contact, _ = Contact.objects.get_or_create(
                    group=group,
                    name=person_name,
                    defaults={'category': ContactCategory.CUSTOMER, 'notes': 'شخص خارجي ليس لديه حساب'}
                )

            AccountingService.record_income(
                group=group,
                account=cd['account'],
                amount=cd['amount'],
                date=cd['date'],
                description=cd['description'],
                category=cd.get('category'),
                project=cd.get('project'),
                partner=cd.get('partner'),
                contact=contact,
                notes=cd.get('notes', ''),
                attachment=request.FILES.get('attachment'),
                user=request.user,
                currency=cd.get('currency'),
                exchange_rate=cd.get('exchange_rate'),
            )
            messages.success(request, f"تم تسجيل الإيراد بنجاح ({cd['amount']:,.2f}) في {group.name}.")
            return redirect('finance:transaction_list')
    else:
        form = IncomeExpenseForm(group)
    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'تسجيل إيراد / دخل', 'group': group})

@group_required()
def add_expense(request, group, membership):
    if not membership.can_edit_finances:
        raise PermissionDenied("ليس لديك صلاحية لتسجيل معاملات في هذه المجموعة.")

    if request.method == 'POST':
        form = IncomeExpenseForm(group, request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            contact = cd.get('contact')
            # If external person name provided on the fly
            if not contact and cd.get('external_person_name'):
                person_name = cd['external_person_name'].strip()
                contact, _ = Contact.objects.get_or_create(
                    group=group,
                    name=person_name,
                    defaults={'category': ContactCategory.SUPPLIER, 'notes': 'شخص خارجي ليس لديه حساب'}
                )

            AccountingService.record_expense(
                group=group,
                account=cd['account'],
                amount=cd['amount'],
                date=cd['date'],
                description=cd['description'],
                category=cd.get('category'),
                project=cd.get('project'),
                partner=cd.get('partner'),
                contact=contact,
                notes=cd.get('notes', ''),
                attachment=request.FILES.get('attachment'),
                user=request.user,
                currency=cd.get('currency'),
                exchange_rate=cd.get('exchange_rate'),
            )
            messages.success(request, f"تم تسجيل المصروف بنجاح ({cd['amount']:,.2f}) في {group.name}.")
            return redirect('finance:transaction_list')
    else:
        form = IncomeExpenseForm(group)
    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'تسجيل مصروف', 'group': group})

@group_required()
def transfer_funds(request, group, membership):
    if not membership.can_edit_finances:
        raise PermissionDenied("ليس لديك صلاحية لإجراء تحويلات في هذه المجموعة.")

    if request.method == 'POST':
        form = TransferForm(group, request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            AccountingService.record_transfer(
                group=group,
                from_account=cd['from_account'],
                to_account=cd['to_account'],
                amount=cd['amount'],
                date=cd['date'],
                description=cd.get('description', ''),
                notes=cd.get('notes', ''),
                user=request.user,
                to_amount=cd.get('to_amount'),
                exchange_rate=cd.get('exchange_rate'),
            )
            messages.success(request, f"تم تحويل المبلغ {cd['amount']:,.2f} بنجاح.")
            return redirect('finance:account_list')
    else:
        form = TransferForm(group)
    return render(request, 'finance/form_generic.html', {'form': form, 'title': 'تحويل بين الحسابات المالية', 'group': group})

@group_required()
def account_list(request, group, membership):
    accounts = FinancialAccount.objects.filter(group=group)
    if request.method == 'POST' and membership.can_edit_finances:
        form = FinancialAccountForm(request.POST)
        if form.is_valid():
            acc = form.save(commit=False)
            acc.group = group
            acc.current_balance = acc.opening_balance
            acc.save()
            messages.success(request, f"تم إنشاء الحساب {acc.name} بنجاح في {group.name}.")
            return redirect('finance:account_list')
    else:
        form = FinancialAccountForm()
    return render(request, 'finance/accounts.html', {'accounts': accounts, 'form': form, 'group': group, 'membership': membership})
