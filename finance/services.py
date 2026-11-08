import uuid
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.timezone import now
from .models import (
    FinancialGroup, GroupMembership, GroupRole,
    FinancialAccount, Partner, Contact, Project,
    TransactionCategory, TransactionType, FinancialTransaction,
    LoanType, LoanStatus, Loan, LoanRepayment, PartnerSettlement, AuditLog
)

class AccountingService:
    """
    Central accounting service scoped strictly by FinancialGroup.
    Guarantees cross-group isolation and atomic financial integrity.
    """

    @staticmethod
    def _gen_ref(prefix: str = "TXN") -> str:
        date_str = now().strftime("%Y%m%d")
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{date_str}-{unique_suffix}"

    @classmethod
    def validate_same_group(cls, group: FinancialGroup, **named_objects):
        """
        Ensures all associated models belong strictly to the given group.
        Prevents IDOR and cross-group data poisoning.
        """
        for name, obj in named_objects.items():
            if obj is not None and hasattr(obj, 'group_id') and obj.group_id != group.id:
                raise ValidationError(f"عنصر '{name}' ينتمي إلى مجموعة مالية أخرى مختلفة تماماً.")

    @classmethod
    @transaction.atomic
    def record_income(cls, group: FinancialGroup, account: FinancialAccount, amount: Decimal, date, description: str,
                      category: TransactionCategory = None, project: Project = None,
                      partner: Partner = None, contact: Contact = None, notes: str = "",
                      attachment=None, user=None, currency: str = None, exchange_rate: Decimal = None) -> FinancialTransaction:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ الإيراد يجب أن يكون أكبر من صفر.")

        cls.validate_same_group(group, account=account, category=category, project=project, partner=partner, contact=contact)

        txn_currency = currency or account.currency or group.currency
        rate = exchange_rate if exchange_rate and exchange_rate > 0 else Decimal('1.000000')
        base_amt = (amount * rate).quantize(Decimal('0.01'))

        ref = cls._gen_ref("REV")
        txn = FinancialTransaction.objects.create(
            group=group,
            reference_no=ref,
            transaction_type=TransactionType.INCOME,
            date=date,
            amount=amount,
            currency=txn_currency,
            exchange_rate=rate,
            base_amount=base_amt,
            account=account,
            category=category,
            project=project,
            partner=partner,
            contact=contact,
            description=description,
            notes=notes,
            attachment=attachment,
            created_by=user,
        )
        account.current_balance += amount
        account.save(update_fields=['current_balance', 'updated_at'])

        AuditLog.objects.create(
            group=group,
            user=user, action="CREATE_INCOME", model_name="FinancialTransaction",
            object_id=str(txn.id),
            summary=f"تسجيل إيراد بمبلغ {amount:,.2f} {txn_currency} إلى الحساب {account.name}"
        )
        return txn

    @classmethod
    @transaction.atomic
    def record_expense(cls, group: FinancialGroup, account: FinancialAccount, amount: Decimal, date, description: str,
                       category: TransactionCategory = None, project: Project = None,
                       partner: Partner = None, contact: Contact = None, notes: str = "",
                       attachment=None, user=None, currency: str = None, exchange_rate: Decimal = None) -> FinancialTransaction:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ المصروف يجب أن يكون أكبر من صفر.")

        cls.validate_same_group(group, account=account, category=category, project=project, partner=partner, contact=contact)

        txn_currency = currency or account.currency or group.currency
        rate = exchange_rate if exchange_rate and exchange_rate > 0 else Decimal('1.000000')
        base_amt = (amount * rate).quantize(Decimal('0.01'))

        ref = cls._gen_ref("EXP")
        txn = FinancialTransaction.objects.create(
            group=group,
            reference_no=ref,
            transaction_type=TransactionType.EXPENSE,
            date=date,
            amount=amount,
            currency=txn_currency,
            exchange_rate=rate,
            base_amount=base_amt,
            account=account,
            category=category,
            project=project,
            partner=partner,
            contact=contact,
            description=description,
            notes=notes,
            attachment=attachment,
            created_by=user,
        )
        account.current_balance -= amount
        account.save(update_fields=['current_balance', 'updated_at'])

        AuditLog.objects.create(
            group=group,
            user=user, action="CREATE_EXPENSE", model_name="FinancialTransaction",
            object_id=str(txn.id),
            summary=f"تسجيل مصروف بمبلغ {amount:,.2f} {txn_currency} من الحساب {account.name}"
        )
        return txn

    @classmethod
    @transaction.atomic
    def record_transfer(cls, group: FinancialGroup, from_account: FinancialAccount, to_account: FinancialAccount,
                        amount: Decimal, date, description: str = "", notes: str = "",
                        user=None, to_amount: Decimal = None, exchange_rate: Decimal = None) -> FinancialTransaction:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ التحويل يجب أن يكون أكبر من صفر.")
        if from_account.id == to_account.id:
            raise ValidationError("لا يمكن التحويل لنفس الحساب المالي.")

        cls.validate_same_group(group, from_account=from_account, to_account=to_account)

        # Handle cross-currency transfer: if target amount specified, calculate rate, or vice versa
        received_amount = to_amount if to_amount and to_amount > 0 else amount
        rate = exchange_rate if exchange_rate and exchange_rate > 0 else Decimal('1.000000')
        base_amt = (amount * rate).quantize(Decimal('0.01'))

        ref = cls._gen_ref("TRF")
        desc = description or f"تحويل مالي من {from_account.name} ({amount:,.2f} {from_account.currency}) إلى {to_account.name} ({received_amount:,.2f} {to_account.currency})"
        
        txn = FinancialTransaction.objects.create(
            group=group,
            reference_no=ref,
            transaction_type=TransactionType.TRANSFER,
            date=date,
            amount=amount,
            currency=from_account.currency,
            exchange_rate=rate,
            base_amount=base_amt,
            account=from_account,
            to_account=to_account,
            description=desc,
            notes=notes,
            created_by=user,
        )
        from_account.current_balance -= amount
        from_account.save(update_fields=['current_balance', 'updated_at'])

        to_account.current_balance += received_amount
        to_account.save(update_fields=['current_balance', 'updated_at'])

        AuditLog.objects.create(
            group=group,
            user=user, action="TRANSFER_FUNDS", model_name="FinancialTransaction",
            object_id=str(txn.id),
            summary=f"تحويل {amount:,.2f} {from_account.currency} من {from_account.name} إلى {to_account.name} (استلام {received_amount:,.2f} {to_account.currency})"
        )
        return txn

    @classmethod
    @transaction.atomic
    def record_capital_contribution(cls, group: FinancialGroup, partner: Partner, account: FinancialAccount,
                                    amount: Decimal, date, notes: str = "",
                                    user=None) -> FinancialTransaction:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ المساهمة يجب أن يكون أكبر من صفر.")

        cls.validate_same_group(group, partner=partner, account=account)

        ref = cls._gen_ref("CAP-IN")
        txn = FinancialTransaction.objects.create(
            group=group,
            reference_no=ref,
            transaction_type=TransactionType.CAPITAL_IN,
            date=date,
            amount=amount,
            account=account,
            partner=partner,
            description=f"مساهمة رأس مال من الشريك {partner.name}",
            notes=notes,
            created_by=user,
        )
        account.current_balance += amount
        account.save(update_fields=['current_balance', 'updated_at'])

        partner.total_contributions += amount
        partner.current_capital += amount
        partner.save(update_fields=['total_contributions', 'current_capital'])

        AuditLog.objects.create(
            group=group,
            user=user, action="CAPITAL_CONTRIBUTION", model_name="Partner",
            object_id=str(partner.id),
            summary=f"إيداع مساهمة رأس مال بمبلغ {amount:,.2f} للشريك {partner.name}"
        )
        return txn

    @classmethod
    @transaction.atomic
    def record_partner_withdrawal(cls, group: FinancialGroup, partner: Partner, account: FinancialAccount,
                                  amount: Decimal, date, notes: str = "",
                                  user=None) -> FinancialTransaction:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ المسحوبات يجب أن يكون أكبر من صفر.")

        cls.validate_same_group(group, partner=partner, account=account)

        ref = cls._gen_ref("CAP-OUT")
        txn = FinancialTransaction.objects.create(
            group=group,
            reference_no=ref,
            transaction_type=TransactionType.CAPITAL_OUT,
            date=date,
            amount=amount,
            account=account,
            partner=partner,
            description=f"مسحوبات شخصية للشريك {partner.name}",
            notes=notes,
            created_by=user,
        )
        account.current_balance -= amount
        account.save(update_fields=['current_balance', 'updated_at'])

        partner.total_withdrawals += amount
        partner.current_capital -= amount
        partner.save(update_fields=['total_withdrawals', 'current_capital'])

        AuditLog.objects.create(
            group=group,
            user=user, action="PARTNER_WITHDRAWAL", model_name="Partner",
            object_id=str(partner.id),
            summary=f"سحب شخصي للشريك {partner.name} بمبلغ {amount:,.2f}"
        )
        return txn

    @classmethod
    @transaction.atomic
    def create_loan(cls, group: FinancialGroup, loan_type: str, contact: Contact, original_amount: Decimal,
                    account: FinancialAccount, issue_date, due_date=None, interest_amount=Decimal('0.00'),
                    project: Project = None, partner: Partner = None, notes: str = "",
                    user=None, currency: str = None, exchange_rate: Decimal = None) -> Loan:
        if original_amount <= Decimal('0.00'):
            raise ValidationError("مبلغ القرض يجب أن يكون أكبر من صفر.")

        cls.validate_same_group(group, contact=contact, account=account, project=project, partner=partner)

        loan_currency = currency or account.currency or group.currency
        rate = exchange_rate if exchange_rate and exchange_rate > 0 else Decimal('1.000000')

        loan = Loan.objects.create(
            group=group,
            loan_type=loan_type,
            contact=contact,
            original_amount=original_amount,
            remaining_balance=original_amount,
            interest_amount=interest_amount,
            currency=loan_currency,
            exchange_rate=rate,
            issue_date=issue_date,
            due_date=due_date,
            initial_account=account,
            project=project,
            partner=partner,
            notes=notes,
            created_by=user,
        )

        if loan_type == LoanType.BORROWED:
            # We borrowed money from contact => Cash increases. Not a business revenue!
            ref = cls._gen_ref("BORROW")
            FinancialTransaction.objects.create(
                group=group,
                reference_no=ref,
                transaction_type=TransactionType.LOAN_BORROW,
                date=issue_date,
                amount=original_amount,
                currency=loan_currency,
                exchange_rate=rate,
                base_amount=(original_amount * rate).quantize(Decimal('0.01')),
                account=account,
                contact=contact,
                project=project,
                partner=partner,
                description=f"اقتراض مبلغ من {contact.name} (قرض #{loan.id})",
                notes=notes,
                created_by=user,
            )
            account.current_balance += original_amount
            account.save(update_fields=['current_balance', 'updated_at'])
        else:
            # We lent money to contact => Cash decreases. Not a business expense!
            ref = cls._gen_ref("LEND")
            FinancialTransaction.objects.create(
                group=group,
                reference_no=ref,
                transaction_type=TransactionType.LOAN_LEND,
                date=issue_date,
                amount=original_amount,
                currency=loan_currency,
                exchange_rate=rate,
                base_amount=(original_amount * rate).quantize(Decimal('0.01')),
                account=account,
                contact=contact,
                project=project,
                partner=partner,
                description=f"إقراض مبلغ إلى {contact.name} (قرض ممنوح #{loan.id})",
                notes=notes,
                created_by=user,
            )
            account.current_balance -= original_amount
            account.save(update_fields=['current_balance', 'updated_at'])

        AuditLog.objects.create(
            group=group,
            user=user, action="CREATE_LOAN", model_name="Loan",
            object_id=str(loan.id),
            summary=f"إنشاء {loan.get_loan_type_display()} بقيمة {original_amount:,.2f} {loan_currency} مع {contact.name}"
        )
        return loan

    @classmethod
    @transaction.atomic
    def record_loan_repayment(cls, group: FinancialGroup, loan: Loan, amount: Decimal, account: FinancialAccount,
                              date, interest_paid: Decimal = Decimal('0.00'),
                              partner: Partner = None, notes: str = "",
                              user=None) -> LoanRepayment:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ السداد يجب أن يكون أكبر من صفر.")
        if amount > loan.remaining_balance:
            raise ValidationError(f"المبلغ المدفوع ({amount:,.2f}) يتجاوز الرصيد المتبقي للدين ({loan.remaining_balance:,.2f}).")

        cls.validate_same_group(group, loan=loan, account=account, partner=partner)

        if loan.loan_type == LoanType.BORROWED:
            # Repaying lender => Cash decreases. Not an expense!
            ref = cls._gen_ref("REPAY-OUT")
            txn = FinancialTransaction.objects.create(
                group=group,
                reference_no=ref,
                transaction_type=TransactionType.LOAN_REPAY,
                date=date,
                amount=amount,
                account=account,
                contact=loan.contact,
                project=loan.project,
                partner=partner or loan.partner,
                description=f"سداد جزء/كامل قرض الدائن {loan.contact.name} (دين #{loan.id})",
                notes=notes,
                created_by=user,
            )
            account.current_balance -= amount
            account.save(update_fields=['current_balance', 'updated_at'])
        else:
            # Borrower repays us => Cash increases. Not a revenue!
            ref = cls._gen_ref("REPAY-IN")
            txn = FinancialTransaction.objects.create(
                group=group,
                reference_no=ref,
                transaction_type=TransactionType.LOAN_RECOVER,
                date=date,
                amount=amount,
                account=account,
                contact=loan.contact,
                project=loan.project,
                partner=partner or loan.partner,
                description=f"استرداد دين من المدين {loan.contact.name} (دين #{loan.id})",
                notes=notes,
                created_by=user,
            )
            account.current_balance += amount
            account.save(update_fields=['current_balance', 'updated_at'])

        repayment = LoanRepayment.objects.create(
            group=group,
            loan=loan,
            date=date,
            amount=amount,
            interest_paid=interest_paid,
            account=account,
            partner=partner or loan.partner,
            transaction=txn,
            notes=notes,
            created_by=user,
        )

        loan.principal_repaid += amount
        loan.remaining_balance -= amount
        if loan.remaining_balance == Decimal('0.00'):
            loan.status = LoanStatus.PAID
        else:
            loan.status = LoanStatus.PARTIAL
        loan.save(update_fields=['principal_repaid', 'remaining_balance', 'status', 'updated_at'])

        AuditLog.objects.create(
            group=group,
            user=user, action="LOAN_REPAYMENT", model_name="LoanRepayment",
            object_id=str(repayment.id),
            summary=f"سداد مبلغ {amount:,.2f} للقرض #{loan.id} مع {loan.contact.name}. المتبقي: {loan.remaining_balance:,.2f}"
        )
        return repayment

    @classmethod
    @transaction.atomic
    def record_partner_settlement(cls, group: FinancialGroup, from_partner: Partner, to_partner: Partner,
                                  amount: Decimal, date, account: FinancialAccount = None,
                                  is_direct_cash: bool = True, notes: str = "",
                                  user=None) -> PartnerSettlement:
        if amount <= Decimal('0.00'):
            raise ValidationError("مبلغ التسوية يجب أن يكون أكبر من صفر.")
        if from_partner.id == to_partner.id:
            raise ValidationError("لا يمكن إجراء تسوية بين الشريك ونفسه.")

        cls.validate_same_group(group, from_partner=from_partner, to_partner=to_partner, account=account)

        settlement = PartnerSettlement.objects.create(
            group=group,
            from_partner=from_partner,
            to_partner=to_partner,
            amount=amount,
            date=date,
            account=account,
            is_direct_cash=is_direct_cash,
            notes=notes,
            created_by=user,
        )

        AuditLog.objects.create(
            group=group,
            user=user, action="PARTNER_SETTLEMENT", model_name="PartnerSettlement",
            object_id=str(settlement.id),
            summary=f"تسوية مالية بقيمة {amount:,.2f} من {from_partner.name} إلى {to_partner.name}"
        )
        return settlement
