from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from finance.models import (
    FinancialGroup, GroupMembership, GroupRole, GroupType,
    FinancialAccount, AccountType, Partner, Contact, ContactCategory,
    Project, ProjectStatus, TransactionCategory, CategoryType
)

class Command(BaseCommand):
    help = "Seeds initial financial groups, partners, and financial accounts"

    def handle(self, *args, **options):
        self.stdout.write("Initializing Multi-Group Partnership Financial System data...")

        # 1. Create 2 Users
        user1, _ = User.objects.get_or_create(
            username='partner1',
            defaults={'first_name': 'أحمد', 'last_name': 'المنصور', 'email': 'partner1@partnership.local'}
        )
        if not user1.has_usable_password():
            user1.set_password('Partner2026!')
            user1.save()

        user2, _ = User.objects.get_or_create(
            username='partner2',
            defaults={'first_name': 'خالد', 'last_name': 'العثمان', 'email': 'partner2@partnership.local'}
        )
        if not user2.has_usable_password():
            user2.set_password('Partner2026!')
            user2.save()

        # 2. Create Shared Business Partnership Group
        partnership_group, _ = FinancialGroup.objects.get_or_create(
            name="شراكة المنصور والعثمان التجارية",
            defaults={
                'description': 'المجموعة المالية المشتركة لإدارة أعمال الشراكة والمشاريع والديون',
                'group_type': GroupType.PARTNERSHIP,
                'currency': 'SAR',
                'created_by': user1,
            }
        )

        GroupMembership.objects.get_or_create(group=partnership_group, user=user1, defaults={'role': GroupRole.OWNER})
        GroupMembership.objects.get_or_create(group=partnership_group, user=user2, defaults={'role': GroupRole.ADMIN})

        # 3. Create Private Personal Finance Groups for both partners
        personal_group1, _ = FinancialGroup.objects.get_or_create(
            name="المالية الشخصية - أحمد المنصور",
            defaults={
                'description': 'المصاريف والالتزامات الشخصية الخاصة بأحمد المنصور',
                'group_type': GroupType.PERSONAL,
                'currency': 'SAR',
                'created_by': user1,
            }
        )
        GroupMembership.objects.get_or_create(group=personal_group1, user=user1, defaults={'role': GroupRole.OWNER})

        personal_group2, _ = FinancialGroup.objects.get_or_create(
            name="المالية الشخصية - خالد العثمان",
            defaults={
                'description': 'المصاريف والالتزامات الشخصية الخاصة بخالد العثمان',
                'group_type': GroupType.PERSONAL,
                'currency': 'SAR',
                'created_by': user2,
            }
        )
        GroupMembership.objects.get_or_create(group=personal_group2, user=user2, defaults={'role': GroupRole.OWNER})

        # 4. Create Standard Categories for Partnership Group
        income_cats = ["مبيعات منتجات", "عقود خدمات واستشارات", "إيرادات مشاريع", "إيرادات أخرى متنوعة"]
        for name in income_cats:
            TransactionCategory.objects.get_or_create(
                group=partnership_group,
                name=name, category_type=CategoryType.INCOME,
                defaults={'is_system': True, 'description': 'بند إيرادات نظام أساسي'}
            )

        expense_cats = ["معدات وأصول تشغيل", "إيجار ومرافق", "تسويق وإعلانات", "مشتريات وبضاعة", "رواتب ومستحقات أطراف", "استضافة وبرمجيات", "نثريات ومصروفات أخرى"]
        for name in expense_cats:
            TransactionCategory.objects.get_or_create(
                group=partnership_group,
                name=name, category_type=CategoryType.EXPENSE,
                defaults={'is_system': True, 'description': 'بند مصروفات نظام أساسي'}
            )

        # 5. Create Initial Financial Accounts inside Partnership Group
        FinancialAccount.objects.get_or_create(
            group=partnership_group,
            name="الخزينة النقدية الرئيسية (الكاش)",
            defaults={
                'account_type': AccountType.CASH,
                'opening_balance': Decimal('10000.00'),
                'current_balance': Decimal('10000.00'),
                'notes': 'صندوق النقدية للعمليات اليومية للشراكة'
            }
        )

        FinancialAccount.objects.get_or_create(
            group=partnership_group,
            name="الحساب البنكي التجاري المشترك",
            defaults={
                'account_type': AccountType.BANK,
                'bank_name': 'البنك التجاري',
                'account_number': 'SA000012345678901234',
                'opening_balance': Decimal('50000.00'),
                'current_balance': Decimal('50000.00'),
                'notes': 'الحساب المصرفي الرئيسي للشراكة'
            }
        )

        # 6. Create Partners inside Partnership Group
        Partner.objects.get_or_create(
            group=partnership_group,
            name='أحمد المنصور (الشريك الأول)',
            defaults={
                'user': user1,
                'phone': '+966500000001',
                'initial_capital': Decimal('30000.00'),
                'current_capital': Decimal('30000.00'),
                'equity_share_pct': Decimal('50.00'),
                'profit_share_pct': Decimal('50.00'),
            }
        )

        Partner.objects.get_or_create(
            group=partnership_group,
            name='خالد العثمان (الشريك الثاني)',
            defaults={
                'user': user2,
                'phone': '+966500000002',
                'initial_capital': Decimal('30000.00'),
                'current_capital': Decimal('30000.00'),
                'equity_share_pct': Decimal('50.00'),
                'profit_share_pct': Decimal('50.00'),
            }
        )

        # 7. Sample Project & Contact inside Partnership Group
        proj, _ = Project.objects.get_or_create(
            group=partnership_group,
            name="مشروع التوريدات والتجارة الرقمية 2026",
            defaults={
                'description': 'مشروع بيع المنتجات والتجارة الإلكترونية المشترك بين الشريكين',
                'status': ProjectStatus.ACTIVE,
                'start_date': date(2026, 1, 1),
                'initial_budget': Decimal('25000.00'),
            }
        )

        Contact.objects.get_or_create(
            group=partnership_group,
            name="سعيد عبد الله (مقرض تجاري)",
            defaults={
                'category': ContactCategory.LENDER,
                'phone': '+966555111222',
                'notes': 'جهة تمويل للشراكة'
            }
        )

        # 8. Create Personal Cash Account in User 1's Personal Group
        FinancialAccount.objects.get_or_create(
            group=personal_group1,
            name="المحفظة الشخصية - أحمد",
            defaults={
                'account_type': AccountType.CASH,
                'opening_balance': Decimal('2500.00'),
                'current_balance': Decimal('2500.00'),
                'notes': 'مصاريف شخصية معزولة'
            }
        )

        self.stdout.write(self.style.SUCCESS("Multi-Group Architecture seeded successfully with shared partnership and private personal groups."))
