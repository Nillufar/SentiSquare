# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SentiLearn is a Korean language-learning platform that uses AI to simplify news articles for different TOPIK (Test of Proficiency in Korean) levels 1-6. It's a Django web application that integrates with Ollama for LLM processing.

## Key Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Initialize categories (one-time setup)
uv run python manage.py init_categories

# Create superuser for admin access
uv run python manage.py createsuperuser

# Load sample articles from data/ folder
uv run python manage.py load_articles
```

### Running the Server
```bash
# Start development server
uv run python manage.py runserver

# Access at http://localhost:8000
# Admin panel at http://localhost:8000/admin/
```

### Database Operations
```bash
# Create migrations after model changes
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Reset database (if needed)
rm db.sqlite3
uv run python manage.py migrate
uv run python manage.py init_categories
```

## Architecture

### Django Project Structure
- **config/**: Django project settings, URLs, WSGI/ASGI configuration
- **articles/**: Main Django app containing all application logic
- **data/**: Category folders for importing local HTML article files
- **static/**: CSS, JavaScript, images
- **extension/**: Chrome extension for browser-based article imports

### Core Application Flow

1. **Article Import**: Articles can be imported via:
   - HTML file upload through web interface (`/import/`)
   - Chrome extension (pre-fills current URL)
   - `load_articles` management command from `data/` folder

2. **LLM Processing Pipeline** (`articles/llm_processor.py`):
   - Triggered via "Process Article with AI" button in article detail view
   - Runs in background thread (daemon) to avoid blocking requests
   - For each TOPIK level (1-6):
     1. Simplifies Korean text to target proficiency level
     2. Translates simplified text to English
     3. Extracts vocabulary (15-second timeout, non-critical)
   - Sentiment analysis performed once per article (4 dimensions)
   - All operations use Ollama API with model specified in settings

3. **View Flow**:
   - Overview page shows categories with article counts
   - Article detail displays processed versions with TOPIK level slider
   - AJAX endpoint (`get_article_level`) dynamically loads content per level
   - Processing triggered via POST to `process_article` view

### Database Models

**Category**: Pre-defined learning domains (startup, fashion, economics, etc.)
- Fixed choices in `CATEGORY_CHOICES` (articles/models.py:6-12)
- To add new category: update CATEGORY_CHOICES, update init_categories command, create data/ folder

**Article**: Original Korean article
- `original_text`: Source content extracted from HTML
- `is_processed`: Flag indicating if LLM processing completed
- Related: ProcessedArticle (versions), Sentiment (analysis)

**ProcessedArticle**: Simplified version for specific TOPIK level
- `unique_together`: article + language_level (only one version per level)
- Contains simplified Korean and English translation
- Related: Vocabulary items

**Sentiment**: Four-dimensional analysis (0.0-1.0 scores)
- positive/negative, technical/general, social/individual, educational/entertainment
- OneToOne with Article (analyzed once from original_text)

**Vocabulary**: Extracted words with definitions
- Linked to ProcessedArticle (level-specific vocabulary)
- `order` field for display sequence

### LLM Integration

**LLMProcessor** (`articles/llm_processor.py`):
- Initializes with Ollama host/model from settings
- All prompts use system/user message format
- Key methods:
  - `simplify_text(text, topik_level)`: Adapts complexity to TOPIK level
  - `translate_to_english(text)`: Korean → English translation
  - `analyze_sentiment(text)`: Returns JSON with 4 scores
  - `extract_vocabulary(text, level)`: Returns JSON array (has timeout)
  - `process_article(article_id, topik_levels)`: Orchestrates full pipeline

**Important Processing Details**:
- Vocabulary extraction has 15-second timeout (non-critical failure)
- Processing runs in daemon thread spawned from view
- Model hardcoded to "gemma3:latest" in _generate_response (line 73)
- Validation disabled in _validate_ollama() (early return True on line 26)

### Configuration

**Ollama Settings** (`config/settings.py`):
- `OLLAMA_HOST`: API endpoint (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model identifier (default: gemma3:latest)
- Note: Model in settings may differ from hardcoded model in llm_processor.py

**Prerequisites**:
- Ollama must be running locally: `ollama serve`
- Required model must be pulled: `ollama pull gemma3:latest`

## Important Patterns

### Article HTML Extraction
The system extracts content from HTML in this priority:
1. `<article>` tag → find all `<p>` tags
2. `<main>` tag → find all `<p>` tags
3. `<body>` tag → find all `<p>` tags
4. Fallback: all `<p>` tags in document

Content must be at least 50 characters and UTF-8 encoded.

### URL Routing
- Root: Overview page with category list
- `/article/<id>/`: Article detail with TOPIK slider
- `/article/<id>/level/<level>/`: AJAX endpoint for level content
- `/article/<id>/process/`: POST to trigger full AI processing
- `/article/<id>/generate-level/`: POST with JSON body to generate single level
- `/import/`: GET (form) or POST (upload) for article import
- `/admin/`: Django admin panel

### Category System
Categories are database-backed but use fixed choices:
- `startup_knowledge`, `fashion_kbeauty`, `economics`, `international_relations`, `legal_business`
- Folder structure in `data/` mirrors category names
- Changes require: model update → migration → init_categories → data folder

### Static Files
- Located in `static/` directory (STATICFILES_DIRS configured)
- Served automatically in development mode
- For production: run `collectstatic` and configure web server

## Development Notes

### Adding a New Category
1. Add to `Category.CATEGORY_CHOICES` (articles/models.py)
2. Update `init_categories.py` command with display_name and description
3. Create matching folder in `data/` directory
4. Run: `uv run python manage.py makemigrations && uv run python manage.py migrate`
5. Run: `uv run python manage.py init_categories`

### Modifying LLM Processing
- Edit prompts in `LLMProcessor` methods for different output
- Adjust TOPIK level criteria in `simplify_text` system prompt
- Modify vocabulary count in `extract_vocabulary` call (default: 10)
- To process specific levels only: pass `topik_levels` list to `process_article`

### Article Content Extraction
If extraction fails from HTML:
- Ensure HTML contains `<p>` tags with Korean text
- Check UTF-8 encoding
- Verify minimum 50 character threshold
- Consider adjusting extraction logic in views.py:import_article (lines 176-191)

### Testing AI Processing
Without running the server, you can test LLM processing:
```python
from articles.llm_processor import LLMProcessor
from articles.models import Article

processor = LLMProcessor()
article = Article.objects.first()
processor.process_article(article.id, topik_levels=[3])  # Test single level
```

### Chrome Extension Usage
The extension at `extension/` assumes server runs at `http://localhost:8000`:
1. Load unpacked extension in chrome://extensions/
2. Enable Developer mode
3. Navigate to Korean article to import
4. Click extension icon → "Import current page"
5. Extension opens `/import/` with pre-filled URL

## Database Schema Notes

- SQLite used for development (db.sqlite3)
- All timestamps use Django's auto_now/auto_now_add
- ProcessedArticle uses unique_together constraint preventing duplicate levels
- Vocabulary items ordered by `order` field, then alphabetically by `word`
- Sentiment scores validated between 0.0-1.0 via MinValueValidator/MaxValueValidator

## Troubleshooting

**Ollama connection errors**: Verify Ollama is running (`ollama serve`) and model exists (`ollama list`)

**Processing hangs**: Check server logs for timeout/errors; vocabulary extraction has 15s timeout but continues processing

**Import extraction fails**: Ensure HTML has `<p>` tags with sufficient Korean text (50+ chars)

**Model mismatch**: Check both `config/settings.py` OLLAMA_MODEL and hardcoded model in `articles/llm_processor.py:73`
