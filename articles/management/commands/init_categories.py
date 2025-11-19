from django.core.management.base import BaseCommand
from articles.models import Category


class Command(BaseCommand):
    help = 'Initialize categories in the database'

    def handle(self, *args, **options):
        categories_data = [
            {
                'name': 'startup_knowledge',
                'display_name': 'Startup Knowledge',
                'description': 'Articles about startups, entrepreneurship, and business innovation'
            },
            {
                'name': 'fashion_kbeauty',
                'display_name': 'Fashion and K-Beauty',
                'description': 'Korean fashion trends and beauty industry news'
            },
            {
                'name': 'economics',
                'display_name': 'Economics',
                'description': 'Economic news, market trends, and financial analysis'
            },
            {
                'name': 'international_relations',
                'display_name': 'International Relations',
                'description': 'Foreign policy, diplomacy, and global affairs'
            },
            {
                'name': 'legal_business',
                'display_name': 'Legal Issues for Businesses',
                'description': 'Business law, regulations, and legal compliance'
            },
        ]

        created_count = 0
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'display_name': cat_data['display_name'],
                    'description': cat_data['description']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.display_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nInitialized {created_count} new categories')
        )
