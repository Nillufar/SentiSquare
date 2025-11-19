from django.core.management.base import BaseCommand
from django.conf import settings
from articles.models import Category, Article
from bs4 import BeautifulSoup
import os


class Command(BaseCommand):
    help = 'Load articles from the data directory'

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        loaded_count = 0

        # Map directory names to category names
        category_mapping = {
            'startup_knowledge': 'startup_knowledge',
            'fashion_kbeauty': 'fashion_kbeauty',
            'economics': 'economics',
            'international_relations': 'international_relations',
            'legal_business': 'legal_business',
        }

        for dir_name, category_name in category_mapping.items():
            category_path = data_dir / dir_name

            if not category_path.exists():
                self.stdout.write(
                    self.style.WARNING(f'Directory not found: {category_path}')
                )
                continue

            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Category not found: {category_name}. Run init_categories first.')
                )
                continue

            # Look for HTML files in the directory
            for filename in os.listdir(category_path):
                if not filename.endswith('.html'):
                    continue

                file_path = category_path / filename
                relative_path = str(file_path.relative_to(settings.BASE_DIR))

                # Check if already loaded
                if Article.objects.filter(file_path=relative_path).exists():
                    self.stdout.write(
                        self.style.WARNING(f'Article already loaded: {filename}')
                    )
                    continue

                try:
                    # Read and parse HTML file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()

                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Extract title
                    title_tag = soup.find('title') or soup.find('h1')
                    title = title_tag.get_text(strip=True) if title_tag else filename

                    # Extract article content
                    article_tag = soup.find('article')
                    if article_tag:
                        paragraphs = article_tag.find_all('p')
                        if paragraphs:
                            # Content is in <p> tags
                            content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
                        else:
                            # Content is plain text, get all text from article tag
                            content = article_tag.get_text(strip=True)
                    else:
                        # Fallback: get all paragraphs
                        paragraphs = soup.find_all('p')
                        content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)

                    if not content:
                        self.stdout.write(
                            self.style.ERROR(f'No content found in: {filename}')
                        )
                        continue

                    # Create article
                    article = Article.objects.create(
                        title=title,
                        category=category,
                        original_text=content,
                        file_path=relative_path
                    )

                    loaded_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Loaded article: {title}')
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading {filename}: {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\nLoaded {loaded_count} new articles')
        )
