from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    FinancialGroup, GroupMembership, GroupRole, GroupType,
    FinancialAccount, AccountType, TransactionCategory, CategoryType
)

@receiver(post_save, sender=User)
def create_user_personal_space(sender, instance, created, **kwargs):
    """
    Whenever a new user registers or is created, automatically generate
    their private personal finance space, default cash wallet, and
    essential income/expense categories.
    No other user can access this space.
    """
    if created:
        personal_group = FinancialGroup.objects.create(
            name=f"حسابي الشخصي - {instance.first_name or instance.username}",
            description="مساحة العمل الشخصية الخاصة بي (ديوني، مستحقاتي، ومصروفاتي الخاصة)",
            group_type=GroupType.PERSONAL,
            created_by=instance,
            currency="SAR"
        )
        GroupMembership.objects.create(
            group=personal_group,
            user=instance,
            role=GroupRole.OWNER
        )
        FinancialAccount.objects.create(
            group=personal_group,
            name="المحفظة النقدية الشخصية",
            account_type=AccountType.CASH,
            opening_balance=0,
            current_balance=0
        )
        
        # Default personal income categories
        for name in ["راتب شخصي", "أعمال حرة ومستقلة", "إيرادات أخرى"]:
            TransactionCategory.objects.create(
                group=personal_group,
                name=name,
                category_type=CategoryType.INCOME,
                is_system=True,
                description="بند إيراد شخصي"
            )
        
        # Default personal expense categories
        for name in ["طعام وبقالة", "سكن وفواتير", "مواصلات ووقود", "صحة وعلاج", "مصاريف عامة"]:
            TransactionCategory.objects.create(
                group=personal_group,
                name=name,
                category_type=CategoryType.EXPENSE,
                is_system=True,
                description="بند مصروف شخصي"
            )


