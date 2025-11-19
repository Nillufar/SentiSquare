from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import Category, Article, ProcessedArticle, Sentiment
from .llm_processor import LLMProcessor
import requests
from bs4 import BeautifulSoup
import threading


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


@require_http_methods(["GET", "POST"])
def import_article(request):
    """Import article from URL"""
    if request.method == 'POST':
        url = request.POST.get('url')
        category_id = request.POST.get('category')

        if not url or not category_id:
            messages.error(request, 'Please provide both URL and category.')
            return redirect('import_article')

        try:
            # Fetch the article
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to extract title
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else 'Imported Article'

            # Try to extract article content
            # This is a simple approach - you may need to customize based on the website
            article_body = soup.find('article') or soup.find('main')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            else:
                # Fallback: get all paragraphs
                paragraphs = soup.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs[:10])

            if not content:
                messages.error(request, 'Could not extract content from the URL.')
                return redirect('import_article')

            # Create article
            category = get_object_or_404(Category, id=category_id)
            article = Article.objects.create(
                title=title_text,
                category=category,
                original_text=content,
                source_url=url
            )

            messages.success(request, f'Successfully imported article: {title_text}')
            return redirect('article_detail', article_id=article.id)

        except requests.RequestException as e:
            messages.error(request, f'Error fetching URL: {str(e)}')
            return redirect('import_article')

    # GET request
    categories = Category.objects.all()
    return render(request, 'articles/import_article.html', {
        'categories': categories
    })
