from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import Category, Article, ProcessedArticle, Sentiment
from .llm_processor import LLMProcessor
from bs4 import BeautifulSoup
import threading
import json


def overview(request):
    """Display overview page with categories and articles"""
    categories = Category.objects.prefetch_related('articles').all()
    return render(request, 'articles/overview.html', {
        'categories': categories
    })


def article_detail(request, article_id):
    """Display article detail with language level slider"""
    article = get_object_or_404(Article, id=article_id)

    # Get default language level from query param or use 3
    default_level = int(request.GET.get('level', 3))

    # Get processed version for this level
    processed = None
    vocabulary = []
    if article.is_processed:
        try:
            processed = ProcessedArticle.objects.get(
                article=article,
                language_level=default_level
            )
            vocabulary = processed.vocabulary_items.all()
        except ProcessedArticle.DoesNotExist:
            pass

    # Get sentiment if available
    sentiment = None
    if hasattr(article, 'sentiment'):
        sentiment = article.sentiment

    # Get all available levels for this article
    available_levels = ProcessedArticle.objects.filter(
        article=article
    ).values_list('language_level', flat=True)

    context = {
        'article': article,
        'processed': processed,
        'vocabulary': vocabulary,
        'sentiment': sentiment,
        'current_level': default_level,
        'available_levels': list(available_levels),
    }

    return render(request, 'articles/article_detail.html', context)


def get_article_level(request, article_id, level):
    """AJAX endpoint to get article content for specific level"""
    article = get_object_or_404(Article, id=article_id)

    try:
        processed = ProcessedArticle.objects.get(
            article=article,
            language_level=level
        )
        vocabulary = list(processed.vocabulary_items.values(
            'word', 'definition', 'example_sentence'
        ))

        return JsonResponse({
            'success': True,
            'simplified_text': processed.simplified_text,
            'english_translation': processed.english_translation,
            'vocabulary': vocabulary
        })
    except ProcessedArticle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Article not processed for level {level}'
        }, status=404)


@require_http_methods(["POST"])
def process_article(request, article_id):
    """Process an article through LLM"""
    article = get_object_or_404(Article, id=article_id)

    # Start processing in background thread
    def process():
        processor = LLMProcessor()
        processor.process_article(article_id)

    thread = threading.Thread(target=process)
    thread.daemon = True
    thread.start()

    messages.success(request, f'Started processing "{article.title}". This may take a few minutes.')
    return redirect('article_detail', article_id=article_id)


@require_http_methods(["POST"])
def generate_article_level(request, article_id):
    """Generate a specific TOPIK level for an article"""
    article = get_object_or_404(Article, id=article_id)

    try:
        data = json.loads(request.body)
        level = data.get('level')

        if not level or not isinstance(level, int) or level < 1 or level > 6:
            return JsonResponse({
                'success': False,
                'error': 'Invalid level. Must be between 1 and 6.'
            }, status=400)

        # Check if this level already exists
        if ProcessedArticle.objects.filter(article=article, language_level=level).exists():
            return JsonResponse({
                'success': False,
                'error': f'Level {level} has already been generated.'
            }, status=400)

        # Start processing in background thread
        def process():
            processor = LLMProcessor()
            processor.process_article(article_id, topik_levels=[level])

        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'success': True,
            'message': f'Started generating TOPIK level {level}. This may take a minute.'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET", "POST"])
def import_article(request):
    """Import article from HTML file upload"""
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        html_file = request.FILES.get('html_file')

        if not title or not category_id or not html_file:
            messages.error(request, 'Please provide title, category, and HTML file.')
            return redirect('import_article')

        # Validate file type
        if not html_file.name.endswith(('.html', '.htm')):
            messages.error(request, 'Please upload an HTML file (.html or .htm).')
            return redirect('import_article')

        try:
            # Read and parse the HTML file
            html_content = html_file.read().decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')

            # Try to extract article content
            # First try to find article or main tag
            article_body = soup.find('article') or soup.find('main')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            else:
                # Fallback: get all paragraphs from body
                body = soup.find('body')
                if body:
                    paragraphs = body.find_all('p')
                    content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                else:
                    # Last resort: get all paragraphs
                    paragraphs = soup.find_all('p')
                    content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            if not content or len(content.strip()) < 50:
                messages.error(request, 'Could not extract sufficient content from the HTML file. Please ensure it contains paragraph tags with Korean text.')
                return redirect('import_article')

            # Create article
            category = get_object_or_404(Category, id=category_id)
            article = Article.objects.create(
                title=title,
                category=category,
                original_text=content,
                source_url=''  # No URL for uploaded files
            )

            messages.success(request, f'Successfully imported article: {title}')
            return redirect('article_detail', article_id=article.id)

        except UnicodeDecodeError:
            messages.error(request, 'Error reading file. Please ensure it is a valid UTF-8 encoded HTML file.')
            return redirect('import_article')
        except Exception as e:
            messages.error(request, f'Error processing HTML file: {str(e)}')
            return redirect('import_article')

    # GET request
    categories = Category.objects.all()
    return render(request, 'articles/import_article.html', {
        'categories': categories
    })
