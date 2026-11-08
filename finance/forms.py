from django import forms
from django.contrib.auth.models import User
from decimal import Decimal
from .models import (
    FinancialGroup, GroupMembership, GroupInvitation, GroupType, GroupRole,
    FinancialAccount, Partner, Contact, ContactCategory, Project,
    TransactionCategory, FinancialTransaction, Loan, LoanRepayment,
    PartnerSettlement, LoanType, AccountType
)

class FinancialGroupForm(forms.ModelForm):
    class Meta:
        model = FinancialGroup
        fields = ['name', 'description', 'group_type', 'currency', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: شراكة الأمل، تجارة العقارات...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'group_type': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SAR'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class GroupInviteForm(forms.Form):
    username_or_email = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم أو البريد الإلكتروني للمدعو'}))
    role = forms.ChoiceField(choices=[(r.value, r.label) for r in GroupRole if r != GroupRole.OWNER], widget=forms.Select(attrs={'class': 'form-select'}))


class ExternalPartnerForm(forms.ModelForm):
    """Form to add an external partner who has NO platform account."""
    class Meta:
        model = GroupMembership
        fields = ['display_name', 'phone', 'email', 'role', 'initial_capital', 'equity_share_pct', 'profit_share_pct']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الشريك الكامل (مثلاً: عبد الله بن حمد)'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الجوال'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني (اختياري)'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'initial_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equity_share_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'profit_share_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class PartnerCreateForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'phone', 'email', 'initial_capital', 'equity_share_pct', 'profit_share_pct', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الشريك الكامل'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'initial_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equity_share_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'profit_share_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class IncomeExpenseForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    amount = forms.DecimalField(min_value=Decimal('0.01'), decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}))
    currency = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رمز العملة مثلاً: USD, EUR, DZD, SAR'}))
    exchange_rate = forms.DecimalField(initial=Decimal('1.000000'), decimal_places=6, required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'سعر الصرف لعملة الأساس (افتراضي 1.0)'}))
    account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), widget=forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر الحساب المالي...'}))
    category = forms.ModelChoiceField(queryset=TransactionCategory.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر البند / التصنيف...'}))
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر المشروع...'}))
    partner = forms.ModelChoiceField(queryset=Partner.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر الشريك المعني...'}))
    contact = forms.ModelChoiceField(queryset=Contact.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'ابحث عن جهة اتصال مسجلة...'}))
    
    # Inline quick person/contact for people without an account
    external_person_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'أو اكتب اسم الشخص مباشرة (ليس لديه حساب)'}))
    
    description = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'بيان العملية'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ملاحظات إضافية'}))
    attachment = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)
        self.fields['category'].queryset = TransactionCategory.objects.filter(group=group)
        self.fields['project'].queryset = Project.objects.filter(group=group)
        self.fields['partner'].queryset = Partner.objects.filter(group=group, is_active=True)
        self.fields['contact'].queryset = Contact.objects.filter(group=group)

class TransferForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    amount = forms.DecimalField(min_value=Decimal('0.01'), decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'المبلغ المصروف من حساب المصدر'}))
    to_amount = forms.DecimalField(min_value=Decimal('0.01'), decimal_places=2, required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'المبلغ الفعلي المستلم (في حال اختلاف العملة)'}))
    exchange_rate = forms.DecimalField(decimal_places=6, required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'سعر الصرف المتفق عليه (اختياري)'}))
    from_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    to_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    description = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'سبب التحويل أو الصرف'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)
        self.fields['to_account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        from_acc = cleaned_data.get('from_account')
        to_acc = cleaned_data.get('to_account')
        if from_acc and to_acc and from_acc == to_acc:
            raise forms.ValidationError("لا يمكن أن يكون حساب المصدر وحساب الوجهة متطابقين.")
        return cleaned_data

class CapitalTransactionForm(forms.Form):
    ACTION_CHOICES = (
        ('CONTRIBUTION', 'إيداع مساهمة رأس مال جديدة'),
        ('WITHDRAWAL', 'سحب شخصي للشريك'),
    )
    action_type = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    partner = forms.ModelChoiceField(queryset=Partner.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(min_value=Decimal('0.01'), decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['partner'].queryset = Partner.objects.filter(group=group, is_active=True)
        self.fields['account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)

class LoanForm(forms.ModelForm):
    # Support inline recording with any external person who doesn't have an account
    external_person_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'أو اكتب اسم الشخص مباشرة (ليس لديه حساب في النظام)'})
    )
    external_person_phone = forms.CharField(
        max_length=40, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم هاتف الشخص (اختياري)'})
    )

    class Meta:
        model = Loan
        fields = ['loan_type', 'contact', 'original_amount', 'currency', 'exchange_rate', 'initial_account', 'issue_date', 'due_date', 'interest_amount', 'project', 'partner', 'notes']
        widgets = {
            'loan_type': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'ابحث عن جهة اتصال...'}),
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SAR'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '1.000000'}),
            'initial_account': forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر الحساب...'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'interest_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'project': forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر المشروع (اختياري)...'}),
            'partner': forms.Select(attrs={'class': 'form-select searchable-select', 'placeholder': 'اختر الشريك (اختياري)...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact'].queryset = Contact.objects.filter(group=group)
        self.fields['contact'].required = False
        self.fields['initial_account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)
        self.fields['project'].queryset = Project.objects.filter(group=group)
        self.fields['partner'].queryset = Partner.objects.filter(group=group, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get('contact')
        ext_name = cleaned_data.get('external_person_name')
        if not contact and not ext_name:
            raise forms.ValidationError("يرجى اختيار جهة اتصال مسجلة، أو كتابة اسم الشخص في خانة (اسم الشخص مباشرة).")
        return cleaned_data

class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanRepayment
        fields = ['date', 'amount', 'interest_paid', 'account', 'partner', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'partner': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)
        self.fields['partner'].queryset = Partner.objects.filter(group=group, is_active=True)

class PartnerSettlementForm(forms.ModelForm):
    class Meta:
        model = PartnerSettlement
        fields = ['from_partner', 'to_partner', 'amount', 'date', 'account', 'is_direct_cash', 'notes']
        widgets = {
            'from_partner': forms.Select(attrs={'class': 'form-select'}),
            'to_partner': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'is_direct_cash': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_partner'].queryset = Partner.objects.filter(group=group, is_active=True)
        self.fields['to_partner'].queryset = Partner.objects.filter(group=group, is_active=True)
        self.fields['account'].queryset = FinancialAccount.objects.filter(group=group, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        from_p = cleaned_data.get('from_partner')
        to_p = cleaned_data.get('to_partner')
        if from_p and to_p and from_p == to_p:
            raise forms.ValidationError("لا يمكن أن يكون الشريك الدافع والمستلم متطابقين.")
        return cleaned_data

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'category', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الشخص أو الجهة الخارجية'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'start_date', 'end_date', 'initial_budget', 'partners', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'initial_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'partners': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['partners'].queryset = Partner.objects.filter(group=group, is_active=True)

class FinancialAccountForm(forms.ModelForm):
    class Meta:
        model = FinancialAccount
        fields = ['name', 'account_type', 'currency', 'account_number', 'bank_name', 'opening_balance', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: USD, SAR, EUR, DZD'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class UserRegistrationForm(forms.ModelForm):
    """Public registration form — creates a Django User (signal auto-creates personal group)."""
    password1 = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'كلمة مرور قوية'}),
    )
    password2 = forms.CharField(
        label='تأكيد كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'أعد كتابة كلمة المرور'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم (بالأحرف اللاتينية)'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العائلة'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني (اختياري)'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('كلمتا المرور غير متطابقتين.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('كلمة المرور يجب أن تكون 8 أحرف على الأقل.')
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Lets a user update their display name, email, and personal default currency."""
    default_currency = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العملة الافتراضية لحسابك الشخصي (مثلاً: USD, DZD, EUR, SAR)'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class GroupEditForm(forms.ModelForm):
    """Lets an owner/admin edit group name, description, currency, and logo."""
    class Meta:
        model = FinancialGroup
        fields = ['name', 'description', 'currency', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SAR'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
