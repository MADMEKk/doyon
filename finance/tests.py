from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError, PermissionDenied

from finance.models import (
    FinancialGroup, GroupMembership, GroupRole, GroupType,
    FinancialAccount, AccountType, Partner, Contact, ContactCategory,
    Project, ProjectStatus, TransactionCategory, CategoryType,
    FinancialTransaction, TransactionType, Loan, LoanType, LoanStatus,
    LoanRepayment, PartnerSettlement, AuditLog
)
from finance.services import AccountingService
from finance.calculations import FinancialCalculator

class MultiGroupFinancialTests(TestCase):
    def setUp(self):
        # 2 Users
        self.user1 = User.objects.create_user(username='partner1', password='Password123!')
        self.user2 = User.objects.create_user(username='partner2', password='Password123!')
        self.user3_stranger = User.objects.create_user(username='stranger', password='Password123!')

        # Group A: Partnership
        self.group_a = FinancialGroup.objects.create(
            name="شراكة أ",
            group_type=GroupType.PARTNERSHIP,
            created_by=self.user1
        )
        GroupMembership.objects.create(group=self.group_a, user=self.user1, role=GroupRole.OWNER)
        GroupMembership.objects.create(group=self.group_a, user=self.user2, role=GroupRole.ADMIN)

        # Group B: Private Personal Group for User 1
        self.group_b = FinancialGroup.objects.create(
            name="مالية شخصية - شريك 1",
            group_type=GroupType.PERSONAL,
            created_by=self.user1
        )
        GroupMembership.objects.create(group=self.group_b, user=self.user1, role=GroupRole.OWNER)

        # Accounts in Group A
        self.acc_a_cash = FinancialAccount.objects.create(
            group=self.group_a,
            name="صندوق الشراكة",
            account_type=AccountType.CASH,
            opening_balance=Decimal('5000.00'),
            current_balance=Decimal('5000.00')
        )
        self.acc_a_bank = FinancialAccount.objects.create(
            group=self.group_a,
            name="بنك الشراكة",
            account_type=AccountType.BANK,
            opening_balance=Decimal('20000.00'),
            current_balance=Decimal('20000.00')
        )

        # Accounts in Group B (Personal)
        self.acc_b_wallet = FinancialAccount.objects.create(
            group=self.group_b,
            name="المحفظة الشخصية",
            account_type=AccountType.WALLET,
            opening_balance=Decimal('1000.00'),
            current_balance=Decimal('1000.00')
        )

        # Partners in Group A
        self.partner_a1 = Partner.objects.create(
            group=self.group_a,
            user=self.user1,
            name="شريك أ 1",
            initial_capital=Decimal('10000.00'),
            current_capital=Decimal('10000.00'),
            equity_share_pct=Decimal('50.00'),
            profit_share_pct=Decimal('50.00')
        )
        self.partner_a2 = Partner.objects.create(
            group=self.group_a,
            user=self.user2,
            name="شريك أ 2",
            initial_capital=Decimal('10000.00'),
            current_capital=Decimal('10000.00'),
            equity_share_pct=Decimal('50.00'),
            profit_share_pct=Decimal('50.00')
        )

        # Contact in Group A
        self.contact_a = Contact.objects.create(
            group=self.group_a,
            name="مقرض الشراكة",
            category=ContactCategory.LENDER
        )

        # Project in Group A
        self.project_a = Project.objects.create(
            group=self.group_a,
            name="مشروع تجارة أ",
            status=ProjectStatus.ACTIVE,
            start_date=date.today(),
            initial_budget=Decimal('15000.00')
        )

    def test_group_isolation_in_transactions(self):
        # Record income in Group A
        AccountingService.record_income(
            group=self.group_a,
            account=self.acc_a_cash,
            amount=Decimal('1500.00'),
            date=date.today(),
            description="مبيعات شراكة",
            project=self.project_a,
            user=self.user1
        )

        # Record expense in Group B (Personal)
        AccountingService.record_expense(
            group=self.group_b,
            account=self.acc_b_wallet,
            amount=Decimal('200.00'),
            date=date.today(),
            description="بقالة شخصية",
            user=self.user1
        )

        # Metrics for Group A
        metrics_a = FinancialCalculator.get_dashboard_metrics(self.group_a)
        self.assertEqual(metrics_a['total_income'], Decimal('1500.00'))
        self.assertEqual(metrics_a['total_expenses'], Decimal('0.00'))
        self.assertEqual(metrics_a['net_profit'], Decimal('1500.00'))
        self.assertEqual(metrics_a['total_cash_and_bank'], Decimal('26500.00'))

        # Metrics for Group B (Completely isolated)
        metrics_b = FinancialCalculator.get_dashboard_metrics(self.group_b)
        self.assertEqual(metrics_b['total_income'], Decimal('0.00'))
        self.assertEqual(metrics_b['total_expenses'], Decimal('200.00'))
        self.assertEqual(metrics_b['net_profit'], Decimal('-200.00'))
        self.assertEqual(metrics_b['total_cash_and_bank'], Decimal('800.00'))

    def test_prevent_cross_group_tampering(self):
        # Attempt to record transaction in Group A using an account from Group B
        with self.assertRaises(ValidationError):
            AccountingService.record_income(
                group=self.group_a,
                account=self.acc_b_wallet,  # Belongs to Group B!
                amount=Decimal('500.00'),
                date=date.today(),
                description="اختراق عبر المجموعات",
                user=self.user1
            )

        # Attempt to create loan in Group A with contact from another group or wrong account
        with self.assertRaises(ValidationError):
            AccountingService.create_loan(
                group=self.group_a,
                loan_type=LoanType.BORROWED,
                contact=self.contact_a,
                original_amount=Decimal('1000.00'),
                account=self.acc_b_wallet,  # Belongs to Group B!
                issue_date=date.today(),
                user=self.user1
            )

    def test_loans_and_repayments_scoped_to_group(self):
        loan = AccountingService.create_loan(
            group=self.group_a,
            loan_type=LoanType.BORROWED,
            contact=self.contact_a,
            original_amount=Decimal('6000.00'),
            account=self.acc_a_bank,
            issue_date=date.today(),
            project=self.project_a,
            user=self.user1
        )
        self.assertEqual(loan.remaining_balance, Decimal('6000.00'))
        
        # Repayment in Group A
        AccountingService.record_loan_repayment(
            group=self.group_a,
            loan=loan,
            amount=Decimal('2000.00'),
            account=self.acc_a_bank,
            date=date.today(),
            user=self.user1
        )
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal('4000.00'))
        self.assertEqual(loan.status, LoanStatus.PARTIAL)

        # Check debts scoped to Group A
        metrics_a = FinancialCalculator.get_dashboard_metrics(self.group_a)
        self.assertEqual(metrics_a['debts_owed_by_us'], Decimal('4000.00'))

        # Ensure Group B has zero debts
        metrics_b = FinancialCalculator.get_dashboard_metrics(self.group_b)
        self.assertEqual(metrics_b['debts_owed_by_us'], Decimal('0.00'))

    def test_unauthorized_cross_group_view_access(self):
        # User 3 (Stranger) has no membership in Group A
        client = Client()
        client.force_login(self.user3_stranger)

        # Should be denied or redirected away
        response = client.get(f'/loans/{self.project_a.id}/')
        self.assertNotEqual(response.status_code, 200)

    def test_partner_settlements_and_contributions(self):
        # Capital contribution in Group A
        AccountingService.record_capital_contribution(
            group=self.group_a,
            partner=self.partner_a1,
            account=self.acc_a_bank,
            amount=Decimal('3000.00'),
            date=date.today(),
            user=self.user1
        )
        self.partner_a1.refresh_from_db()
        self.assertEqual(self.partner_a1.current_capital, Decimal('13000.00'))

        # Partner settlement in Group A
        settle = AccountingService.record_partner_settlement(
            group=self.group_a,
            from_partner=self.partner_a1,
            to_partner=self.partner_a2,
            amount=Decimal('500.00'),
            date=date.today(),
            user=self.user1
        )
        self.assertEqual(settle.amount, Decimal('500.00'))
        self.assertEqual(settle.group, self.group_a)
