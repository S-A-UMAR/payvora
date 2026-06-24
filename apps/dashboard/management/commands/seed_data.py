from django.core.management.base import BaseCommand
from apps.dashboard.models import DataPlan, Badge

class Command(BaseCommand):
    help = 'Seed the database with initial data plans and badges'

    def handle(self, *args, **options):
        self.seed_data_plans()
        self.seed_badges()
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))

    def seed_data_plans(self):
        DataPlan.objects.all().delete()
        plans = [
            # MTN
            {'network': 'MTN', 'name': 'Daily 100MB', 'volume': '100MB', 'validity': '1 Day', 'price': 100, 'plan_code': 'MTN-100MB-1D'},
            {'network': 'MTN', 'name': 'Daily 200MB', 'volume': '200MB', 'validity': '1 Day', 'price': 200, 'plan_code': 'MTN-200MB-1D'},
            {'network': 'MTN', 'name': 'Weekly 1GB', 'volume': '1GB', 'validity': '7 Days', 'price': 300, 'plan_code': 'MTN-1GB-7D'},
            {'network': 'MTN', 'name': 'Monthly 2GB', 'volume': '2GB', 'validity': '30 Days', 'price': 500, 'plan_code': 'MTN-2GB-30D'},
            {'network': 'MTN', 'name': 'Monthly 5GB', 'volume': '5GB', 'validity': '30 Days', 'price': 1200, 'plan_code': 'MTN-5GB-30D'},
            {'network': 'MTN', 'name': 'Monthly 10GB', 'volume': '10GB', 'validity': '30 Days', 'price': 2000, 'plan_code': 'MTN-10GB-30D'},
            # Airtel
            {'network': 'Airtel', 'name': 'Daily 100MB', 'volume': '100MB', 'validity': '1 Day', 'price': 100, 'plan_code': 'AIR-100MB-1D'},
            {'network': 'Airtel', 'name': 'Weekly 750MB', 'volume': '750MB', 'validity': '7 Days', 'price': 300, 'plan_code': 'AIR-750MB-7D'},
            {'network': 'Airtel', 'name': 'Monthly 1.5GB', 'volume': '1.5GB', 'validity': '30 Days', 'price': 500, 'plan_code': 'AIR-1.5GB-30D'},
            {'network': 'Airtel', 'name': 'Monthly 4.5GB', 'volume': '4.5GB', 'validity': '30 Days', 'price': 1200, 'plan_code': 'AIR-4.5GB-30D'},
            {'network': 'Airtel', 'name': 'Monthly 11GB', 'volume': '11GB', 'validity': '30 Days', 'price': 2000, 'plan_code': 'AIR-11GB-30D'},
            # Glo
            {'network': 'Glo', 'name': 'Daily 200MB', 'volume': '200MB', 'validity': '1 Day', 'price': 100, 'plan_code': 'GLO-200MB-1D'},
            {'network': 'Glo', 'name': 'Weekly 1.35GB', 'volume': '1.35GB', 'validity': '7 Days', 'price': 300, 'plan_code': 'GLO-1.35GB-7D'},
            {'network': 'Glo', 'name': 'Monthly 2.5GB', 'volume': '2.5GB', 'validity': '30 Days', 'price': 500, 'plan_code': 'GLO-2.5GB-30D'},
            {'network': 'Glo', 'name': 'Monthly 7.7GB', 'volume': '7.7GB', 'validity': '30 Days', 'price': 1500, 'plan_code': 'GLO-7.7GB-30D'},
            # 9mobile
            {'network': '9mobile', 'name': 'Daily 150MB', 'volume': '150MB', 'validity': '1 Day', 'price': 100, 'plan_code': '9M-150MB-1D'},
            {'network': '9mobile', 'name': 'Weekly 1GB', 'volume': '1GB', 'validity': '7 Days', 'price': 300, 'plan_code': '9M-1GB-7D'},
            {'network': '9mobile', 'name': 'Monthly 2GB', 'volume': '2GB', 'validity': '30 Days', 'price': 500, 'plan_code': '9M-2GB-30D'},
            {'network': '9mobile', 'name': 'Monthly 5GB', 'volume': '5GB', 'validity': '30 Days', 'price': 1200, 'plan_code': '9M-5GB-30D'},
        ]
        for p in plans:
            DataPlan.objects.create(**p)
        self.stdout.write(f'  → Created {len(plans)} data plans')

    def seed_badges(self):
        Badge.objects.all().delete()
        badges = [
            {'name': 'First Top-Up', 'description': 'Completed your very first top-up', 'icon': '🚀', 'xp_required': 10},
            {'name': 'Loyal Customer', 'description': 'Made 10 purchases total', 'icon': '💎', 'xp_required': 100},
            {'name': 'Data King', 'description': 'Purchased data 5 times', 'icon': '📶', 'xp_required': 50},
            {'name': 'Bill Slayer', 'description': 'Paid 3 utility bills', 'icon': '⚡', 'xp_required': 30},
            {'name': 'Referral Master', 'description': 'Referred 5 friends to Payvora', 'icon': '🤝', 'xp_required': 150},
            {'name': 'Level 5 User', 'description': 'Reached level 5 on Payvora', 'icon': '⭐', 'xp_required': 400},
            {'name': 'Power User', 'description': 'Reached level 10 on Payvora', 'icon': '🏆', 'xp_required': 900},
            {'name': 'Wallet Funded', 'description': 'Successfully funded your wallet', 'icon': '💰', 'xp_required': 5},
        ]
        for b in badges:
            Badge.objects.create(**b)
        self.stdout.write(f'  → Created {len(badges)} badges')
