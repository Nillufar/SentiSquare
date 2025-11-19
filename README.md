# SentiLearn 🇰🇷

A Korean language–learning platform that uses AI to simplify news articles for different TOPIK (Test of Proficiency in Korean) levels.

## Features

- **Multi-level Article Simplification**  
  Articles simplified for all TOPIK levels (1–6)

- **Automatic Translation**  
  English translations generated for each simplified version

- **Sentiment Analysis** across four dimensions:

  - Positive / Negative tone
  - Technical vs. General content
  - Social vs. Individual focus
  - Educational vs. Entertainment value

- **Vocabulary Lists**  
  Essential vocabulary extracted per TOPIK level

- **Category Organization**  
  Articles organized into curated learning domains:

  - Startup Knowledge
  - Fashion & K-Beauty
  - Economics
  - International Relations
  - Legal Issues for Businesses

- **URL Import**  
  Import articles directly from Korean news websites

---

## Prerequisites

- Python 3.13+
- [Ollama](https://ollama.ai) installed and running locally
- A suitable Korean-capable model installed in Ollama  
  (e.g., `llama3.2:latest` or similar)

---

## Installation

1. Clone the repository and navigate into the project directory.

2. Install dependencies:
   ```bash
   uv sync
   ```
3. Run migrations:

```bash
uv run python manage.py migrate
```

4. Initialize categories:

```bash
uv run python manage.py init_categories
```

5. (Optional) Load sample articles from the data/ folder:

```bash
uv run python manage.py load_articles
```

6. Create a superuser for the admin panel:

```bash
uv run python manage.py createsuperuser
```

## Configuration Edit config/settings.py to configure Ollama:

```python
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:latest"  # Change to your preferred model
```

## Running the Server Start the development server:

```bash
uv run python manage.py runserver
Access the application at http://localhost:8000 ## Usage ### 1. Import Articles #### From File Place HTML files in the appropriate category folder under data/: - data/startup_knowledge/ - data/fashion_kbeauty/ - data/economics/ - data/international_relations/ - data/legal_business/ Then run:
```

```bash
uv run python manage.py load_articles
```

4. Initialize categories (one-time):

   ```bash
   uv run python manage.py init_categories
   ```

5. (Optional) Load sample articles from the `data/` folder:

   ```bash
   uv run python manage.py load_articles
   ```

6. Create a superuser for the Django admin (optional but recommended):

   ```bash
   uv run python manage.py createsuperuser
   ```

## Configuration

Edit `config/settings.py` to point to your Ollama host and model:

```python
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:latest"  # Change to your preferred model
```

## Running the server

Start the development server:

```bash
uv run python manage.py runserver
```

Open the app at: http://localhost:8000

## Usage

### 1) Import articles

- From local files: place HTML files under the appropriate category folder inside `data/` (for example `data/startup_knowledge/`, `data/fashion_kbeauty/`, `data/economics/`, `data/international_relations/`, `data/legal_business/`) and run:

  ```bash
  uv run python manage.py load_articles
  ```

- From a URL: use the web interface > Import Article, paste the article URL, choose a category and click "Import Article".

### 2) Process articles with AI

After importing an article:

1. Open the article detail page.
2. Click "Process Article with AI".
3. Wait for processing to finish (may take several minutes depending on model and article length).

The processing pipeline will:

- Simplify the article for TOPIK levels 1–6
- Produce English translations for each simplified version
- Analyze sentiment across the defined dimensions
- Extract essential vocabulary for each level

### 3) View articles

- Browse articles by category on the overview page
- Click an article to open the detail view
- Use the TOPIK-level control (slider) to switch between simplified versions
- View simplified Korean and English translation side-by-side
- Inspect sentiment bars and vocabulary lists for the selected level

## Admin panel

Visit the Django admin at: http://localhost:8000/admin/

From the admin you can:

- Manage categories
- Edit articles and processed versions
- Manage extracted vocabulary items

## Project structure

Top-level layout (important files/folders):

```
articles/            # Main Django app
  ├─ models.py        # DB models
  ├─ views.py         # View functions
  ├─ admin.py         # Admin configuration
  ├─ llm_processor.py # LLM integration and pipeline
  ├─ templates/       # HTML templates
  └─ management/      # Custom management commands

config/               # Django settings & ASGI/WGSI
data/                 # Local article HTML data used for imports
templates/            # Global templates
manage.py             # Django entry point
pyproject.toml        # Project metadata
```

## LLM processing

The `LLMProcessor` (see `articles/llm_processor.py`) handles AI tasks. Key methods:

- `simplify_text(text, level)` — simplify Korean text to a target TOPIK level
- `translate_to_english(text)` — translate Korean -> English
- `analyze_sentiment(text)` — compute sentiment metrics
- `extract_vocabulary(text, level)` — extract important vocabulary for a level
- `process_article(article)` — orchestrates the full pipeline for an article

## Development

### Adding a new category

1. Add the category to `Category.CATEGORY_CHOICES` in `articles/models.py`.
2. Update `management/commands/init_categories.py` if needed.
3. Create the corresponding folder in `data/`.
4. Run migrations and then `init_categories`:

```bash
uv run python manage.py makemigrations && uv run python manage.py migrate
uv run python manage.py init_categories
```

### Customizing article extraction

Edit `articles/views.py` (the `import_article` view) to change how article content is extracted from remote URLs.

## Troubleshooting

- Ollama connection errors:

  - Ensure Ollama is running: `ollama serve`
  - Check installed models: `ollama list`
  - Verify `OLLAMA_HOST` in `config/settings.py`

- Processing is slow:

  - Try a smaller/faster model
  - Process only specific TOPIK levels (modify `process_article`)

- Import errors:
  - Ensure HTML files contain readable article markup (e.g. `<article>` or `<p>` tags)
  - Verify file encoding is UTF-8

## Contributing

Contributions are welcome. Please open issues or pull requests and follow the repo's coding style.

## License

This project is released under the MIT License.
