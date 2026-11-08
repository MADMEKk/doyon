from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.core.exceptions import PermissionDenied

from .models import (
    Loan, LoanRepayment, LoanType, LoanStatus,
    FinancialAccount, Partner, Contact, ContactCategory, Project, PartnerSettlement, AuditLog
)
from .services import AccountingService
from .calculations import FinancialCalculator
from .forms import (
    LoanForm, LoanRepaymentForm, ContactForm, ProjectForm
)
from .exports import ExportService
from .permissions import group_required

@group_required()
def loan_list(request, group, membership):
    loan_type = request.GET.get('type')
    status = request.GET.get('status')
    loans = Loan.objects.filter(group=group).select_related('contact', 'initial_account', 'project', 'partner')
    
    if loan_type:
        loans = loans.filter(loan_type=loan_type)
    if status:
        loans = loans.filter(status=status)

    borrowed_total = loans.filter(loan_type=LoanType.BORROWED).aggregate(tot=Sum('remaining_balance'))['tot'] or Decimal('0.00')
    lent_total = loans.filter(loan_type=LoanType.LENT).aggregate(tot=Sum('remaining_balance'))['tot'] or Decimal('0.00')

    context = {
        'group': group,
        'membership': membership,
        'loans': loans,
        'loan_types': LoanType.choices,
        'loan_statuses': LoanStatus.choices,
        'borrowed_total': borrowed_total,
        'lent_total': lent_total,
    }
    return render(request, 'finance/loans.html', context)

@group_required()
def loan_create(request, group, membership):
    if not membership.can_edit_finances:
        raise PermissionDenied("ليس لديك الصلاحية لإنشاء قروض.")

    if request.method == 'POST':
        form = LoanForm(group, request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            contact = cd.get('contact')
            # If user typed an external person name who has no account, create/get Contact on the fly
            if not contact and cd.get('external_person_name'):
                person_name = cd['external_person_name'].strip()
                cat = ContactCategory.LENDER if cd['loan_type'] == LoanType.BORROWED else ContactCategory.BORROWER
                contact, _ = Contact.objects.get_or_create(
                    group=group,
                    name=person_name,
                    defaults={
                        'category': cat,
                        'phone': cd.get('external_person_phone', ''),
                        'notes': 'شخص خارجي ليس لديه حساب في المنصة'
                    }
                )

            loan = AccountingService.create_loan(
                group=group,
                loan_type=cd['loan_type'],
                contact=contact,
                original_amount=cd['original_amount'],
                account=cd['initial_account'],
                issue_date=cd['issue_date'],
                due_date=cd.get('due_date'),
                interest_amount=cd.get('interest_amount') or Decimal('0.00'),
                project=cd.get('project'),
                partner=cd.get('partner'),
                notes=cd.get('notes', ''),
                user=request.user,
                currency=cd.get('currency'),
                exchange_rate=cd.get('exchange_rate'),
            )
            messages.success(request, f"تم تسجيل الدين #{loan.id} مع الطرف '{contact.name}' بنجاح.")
            return redirect('finance:loan_detail', loan_id=loan.id)
    else:
        form = LoanForm(group)
    return render(request, 'finance/loan_form.html', {'form': form, 'title': 'تسجيل دين / قرض جديد', 'group': group})

@group_required()
def loan_detail(request, group, membership, loan_id):
    loan = get_object_or_404(
        Loan.objects.filter(group=group).select_related('contact', 'initial_account', 'project', 'partner'),
        id=loan_id
    )
    repayments = loan.repayments.select_related('account', 'partner').all()
    
    if request.method == 'POST':
        if not membership.can_edit_finances:
            raise PermissionDenied("ليس لديك صلاحية لسداد الديون.")
        form = LoanRepaymentForm(group, request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                AccountingService.record_loan_repayment(
                    group=group,
                    loan=loan,
                    amount=cd['amount'],
                    account=cd['account'],
                    date=cd['date'],
                    interest_paid=cd.get('interest_paid') or Decimal('0.00'),
                    partner=cd.get('partner'),
                    notes=cd.get('notes', ''),
                    user=request.user
                )
                messages.success(request, f"تم تسجيل سداد مبلغ {cd['amount']:,.2f} بنجاح.")
                return redirect('finance:loan_detail', loan_id=loan.id)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = LoanRepaymentForm(group, initial={'amount': loan.remaining_balance})

    return render(request, 'finance/loan_detail.html', {'loan': loan, 'repayments': repayments, 'form': form, 'group': group, 'membership': membership})

@group_required()
def project_list(request, group, membership):
    projects = Project.objects.filter(group=group)
    project_summaries = [FinancialCalculator.get_project_summary(p) for p in projects]
    if request.method == 'POST' and membership.can_edit_finances:
        form = ProjectForm(group, request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.group = group
            p.save()
            form.save_m2m()
            messages.success(request, f"تم إنشاء المشروع '{p.name}' بنجاح.")
            return redirect('finance:project_list')
    else:
        form = ProjectForm(group)
    return render(request, 'finance/projects.html', {'project_summaries': project_summaries, 'form': form, 'group': group, 'membership': membership})

@group_required()
def project_detail(request, group, membership, project_id):
    project = get_object_or_404(Project, id=project_id, group=group)
    summary = FinancialCalculator.get_project_summary(project)
    txns = project.transactions.select_related('account', 'category', 'partner').all()
    loans = project.loans.select_related('contact').all()
    return render(request, 'finance/project_detail.html', {'project': project, 'summary': summary, 'transactions': txns, 'loans': loans, 'group': group, 'membership': membership})

@group_required()
def contact_list(request, group, membership):
    contacts = Contact.objects.filter(group=group)
    if request.method == 'POST' and membership.can_edit_finances:
        form = ContactForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.group = group
            c.save()
            messages.success(request, f"تمت إضافة جهة الاتصال {c.name} بنجاح.")
            return redirect('finance:contact_list')
    else:
        form = ContactForm()
    return render(request, 'finance/contacts.html', {'contacts': contacts, 'form': form, 'group': group, 'membership': membership})

@group_required()
def contact_detail(request, group, membership, contact_id):
    contact = get_object_or_404(Contact, id=contact_id, group=group)
    loans = contact.loans.all()
    txns = contact.transactions.all()
    
    borrowed_from_them = loans.filter(loan_type=LoanType.BORROWED).aggregate(tot=Sum('remaining_balance'))['tot'] or Decimal('0.00')
    lent_to_them = loans.filter(loan_type=LoanType.LENT).aggregate(tot=Sum('remaining_balance'))['tot'] or Decimal('0.00')

    context = {
        'group': group,
        'membership': membership,
        'contact': contact,
        'loans': loans,
        'transactions': txns,
        'borrowed_from_them': borrowed_from_them,
        'lent_to_them': lent_to_them,
    }
    return render(request, 'finance/contact_detail.html', context)

@group_required()
def reports_view(request, group, membership):
    metrics = FinancialCalculator.get_dashboard_metrics(group)
    partners_data = [FinancialCalculator.get_member_partner_details(m) for m in group.memberships.all()]
    projects_data = [FinancialCalculator.get_project_summary(p) for p in Project.objects.filter(group=group)]
    
    export_format = request.GET.get('export')
    if export_format == 'pdf':
        headers = ['البند المالي', f'المبلغ ({group.currency})']
        rows = [
            ['إجمالي السيولة والنقدية', f"{metrics['total_cash_and_bank']:,.2f}"],
            ['إجمالي إيرادات الأعمال', f"{metrics['total_income']:,.2f}"],
            ['إجمالي مصروفات الأعمال', f"{metrics['total_expenses']:,.2f}"],
            ['صافي الربح التشغيلي', f"{metrics['net_profit']:,.2f}"],
            ['إجمالي الديون المستحقة علينا', f"{metrics['debts_owed_by_us']:,.2f}"],
            ['إجمالي الديون المستحقة لنا لدى الغير', f"{metrics['debts_owed_to_us']:,.2f}"],
            ['إجمالي رؤوس أموال الشركاء', f"{metrics['total_partner_capital']:,.2f}"],
        ]
        return ExportService.export_summary_pdf(f"تقرير المركز المالي - {group.name}", rows, headers, f"{group.name}_report.pdf")

    return render(request, 'finance/reports.html', {
        'group': group,
        'membership': membership,
        'metrics': metrics,
        'partners_data': partners_data,
        'projects_data': projects_data,
    })

@group_required()
def audit_logs_view(request, group, membership):
    logs = AuditLog.objects.filter(group=group).select_related('user').all()[:100]
    return render(request, 'finance/audit_logs.html', {'logs': logs, 'group': group, 'membership': membership})
