from decimal import Decimal
from django.db.models import Sum, Q
from .models import (
    FinancialGroup, FinancialAccount, Partner, Contact, Project,
    FinancialTransaction, TransactionType, Loan, LoanType, LoanStatus,
    PartnerSettlement
)

class FinancialCalculator:
    """
    Computes accurate metrics strictly scoped to a specific FinancialGroup.
    Guarantees no data leakage between groups.
    """

    @staticmethod
    def get_dashboard_metrics(group: FinancialGroup):
        accounts = FinancialAccount.objects.filter(group=group, is_active=True)
        
        # Multi-currency breakdown per currency
        currency_breakdown = {}
        for acc in accounts:
            curr = acc.currency or group.currency
            currency_breakdown[curr] = currency_breakdown.get(curr, Decimal('0.00')) + acc.current_balance

        # Real Business Operational Revenue normalized in Base Currency
        total_income = FinancialTransaction.objects.filter(
            group=group,
            transaction_type=TransactionType.INCOME,
            is_reversed=False,
            is_posted=True
        ).aggregate(total=Sum('base_amount'))['total'] or Decimal('0.00')

        # Fallback if base_amount is 0 (for legacy seeded records before multi-currency migration)
        if total_income == Decimal('0.00'):
            total_income = FinancialTransaction.objects.filter(
                group=group,
                transaction_type=TransactionType.INCOME,
                is_reversed=False,
                is_posted=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Real Business Operational Expenses normalized in Base Currency
        total_expenses = FinancialTransaction.objects.filter(
            group=group,
            transaction_type=TransactionType.EXPENSE,
            is_reversed=False,
            is_posted=True
        ).aggregate(total=Sum('base_amount'))['total'] or Decimal('0.00')

        if total_expenses == Decimal('0.00'):
            total_expenses = FinancialTransaction.objects.filter(
                group=group,
                transaction_type=TransactionType.EXPENSE,
                is_reversed=False,
                is_posted=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_profit = total_income - total_expenses

        # Debts owed by the group (BORROWED)
        debts_owed_by_us = Loan.objects.filter(
            group=group,
            loan_type=LoanType.BORROWED,
            status__in=[LoanStatus.ACTIVE, LoanStatus.PARTIAL, LoanStatus.OVERDUE]
        ).aggregate(total=Sum('remaining_balance'))['total'] or Decimal('0.00')

        # Debts owed to the group (LENT)
        debts_owed_to_us = Loan.objects.filter(
            group=group,
            loan_type=LoanType.LENT,
            status__in=[LoanStatus.ACTIVE, LoanStatus.PARTIAL, LoanStatus.OVERDUE]
        ).aggregate(total=Sum('remaining_balance'))['total'] or Decimal('0.00')

        # Total Partner Capital in this group (from GroupMembership)
        total_partner_capital = group.memberships.aggregate(
            total=Sum('current_capital')
        )['total'] or Decimal('0.00')

        # Total cash and bank across all accounts (legacy scalar)
        total_cash_and_bank = sum(currency_breakdown.values(), Decimal('0.00'))

        return {
            'total_cash_and_bank': total_cash_and_bank,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'debts_owed_by_us': debts_owed_by_us,
            'debts_owed_to_us': debts_owed_to_us,
            'total_partner_capital': total_partner_capital,
            'currency_breakdown': currency_breakdown,
        }

    @staticmethod
    def get_project_summary(project: Project):
        group = project.group
        revenue = FinancialTransaction.objects.filter(
            group=group,
            project=project,
            transaction_type=TransactionType.INCOME,
            is_reversed=False,
            is_posted=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        expenses = FinancialTransaction.objects.filter(
            group=group,
            project=project,
            transaction_type=TransactionType.EXPENSE,
            is_reversed=False,
            is_posted=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        borrowed = Loan.objects.filter(
            group=group,
            project=project,
            loan_type=LoanType.BORROWED
        ).aggregate(total=Sum('original_amount'))['total'] or Decimal('0.00')

        loan_repaid = Loan.objects.filter(
            group=group,
            project=project,
            loan_type=LoanType.BORROWED
        ).aggregate(total=Sum('principal_repaid'))['total'] or Decimal('0.00')

        profit_or_loss = revenue - expenses

        return {
            'project': project,
            'revenue': revenue,
            'expenses': expenses,
            'net_profit': profit_or_loss,
            'borrowed': borrowed,
            'loan_repaid': loan_repaid,
            'loan_remaining': borrowed - loan_repaid,
        }

    @staticmethod
    def get_member_partner_details(membership):
        group = membership.group
        overall = FinancialCalculator.get_dashboard_metrics(group)
        profit_share = (overall['net_profit'] * membership.profit_share_pct) / Decimal('100.00')
        adjusted_position = membership.current_capital + profit_share

        return {
            'membership': membership,
            'name': membership.get_name(),
            'initial_capital': membership.initial_capital,
            'current_capital': membership.current_capital,
            'profit_share_pct': membership.profit_share_pct,
            'equity_share_pct': membership.equity_share_pct,
            'earned_profit_share': profit_share,
            'adjusted_net_position': adjusted_position,
        }

    @staticmethod
    def get_partner_details(partner: Partner):
        group = partner.group
        overall = FinancialCalculator.get_dashboard_metrics(group)
        partner_profit_share = (overall['net_profit'] * partner.profit_share_pct) / Decimal('100.00')
        adjusted_position = partner.current_capital + partner_profit_share

        settlements_paid = partner.settlements_paid.filter(group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        settlements_received = partner.settlements_received.filter(group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return {
            'partner': partner,
            'initial_capital': partner.initial_capital,
            'contributions': partner.total_contributions,
            'withdrawals': partner.total_withdrawals,
            'capital_balance': partner.current_capital,
            'profit_share_pct': partner.profit_share_pct,
            'equity_share_pct': partner.equity_share_pct,
            'earned_profit_share': partner_profit_share,
            'adjusted_net_position': adjusted_position,
            'settlements_paid': settlements_paid,
            'settlements_received': settlements_received,
        }
