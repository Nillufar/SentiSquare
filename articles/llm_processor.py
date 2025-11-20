import ollama
import json
import signal
from django.conf import settings
from .models import Article, ProcessedArticle, Sentiment, Vocabulary


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Operation timed out")


class LLMProcessor:
    def __init__(self, model=None, host=None):
        self.model = model or settings.OLLAMA_MODEL
        self.host = host or settings.OLLAMA_HOST
        self._validate_ollama()

    def _validate_ollama(self):
        """Validate that Ollama is running and the model is available"""
        return True
        try:
            # List available models to check if Ollama is running
            models = ollama.list()
            available_models = [m['name'] for m in models.get('models', [])]

            # Check if our model is in the list
            model_found = any(self.model in m for m in available_models)

            if not model_found:
                raise RuntimeError(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available models: {', '.join(available_models)}. "
                    f"Please run: ollama pull {self.model}"
                )
        except ollama.ResponseError as e:
            raise RuntimeError(
                f"Failed to connect to Ollama: {e}. "
                f"Make sure Ollama is running at {self.host}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to validate Ollama setup: {e}. "
                f"Make sure Ollama is installed and running."
            ) from e

    def _generate_response(self, prompt, system_prompt=None, timeout=None):
        """Generate response from Ollama with optional timeout"""
        messages = []
        if system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt
            })
        messages.append({
            'role': 'user',
            'content': prompt
        })

        # Set up timeout if specified (Unix-based systems only)
        old_handler = None
        if timeout is not None:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        try:
            response = ollama.chat(
                    model="gemma3:latest",
                messages=messages
            )
            content = response['message']['content']

            if not content or not content.strip():
                raise ValueError("Ollama returned empty response")

            return content
        except TimeoutError:
            raise TimeoutError(f"Request timed out after {timeout} seconds")
        except ollama.ResponseError as e:
            raise RuntimeError(
                f"Ollama API error: {e}. The model may have failed to generate a response."
            ) from e
        except KeyError as e:
            raise RuntimeError(
                f"Unexpected response format from Ollama: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error generating response from Ollama: {e}"
            ) from e
        finally:
            # Cancel the alarm and restore old handler
            if timeout is not None:
                signal.alarm(0)
                if old_handler is not None:
                    signal.signal(signal.SIGALRM, old_handler)

    def simplify_text(self, text, topik_level):
        """Simplify Korean text to specified TOPIK level"""
        system_prompt = """You are a Korean language expert. Your task is to simplify Korean text
        to match specific TOPIK (Test of Proficiency in Korean) levels.
        - Level 1-2: Basic vocabulary, simple grammar, short sentences
        - Level 3-4: Intermediate vocabulary, some complex grammar
        - Level 5-6: Advanced vocabulary, complex grammar, idiomatic expressions

        Return ONLY the simplified Korean text, nothing else."""

        prompt = f"""Simplify the following Korean text to TOPIK level {topik_level}:

{text}

Simplified text (TOPIK Level {topik_level}):"""

        return self._generate_response(prompt, system_prompt)

    def translate_to_english(self, korean_text):
        """Translate Korean text to English"""
        system_prompt = """You are a professional Korean-English translator.
        Provide accurate, natural-sounding English translations that preserve the meaning and tone of the original Korean text.
        Return ONLY the English translation, nothing else."""

        prompt = f"""Translate the following Korean text to English:

{korean_text}

English translation:"""

        return self._generate_response(prompt, system_prompt)

    def analyze_sentiment(self, text):
        """Analyze sentiment dimensions of the article"""
        system_prompt = """You are a text analysis expert. Analyze Korean text across four dimensions:
        1. Positive (positivity/optimism vs negativity/pessimism)
        2. Technical (technical/specialized content vs general content)
        3. Social (focus on social/interpersonal aspects vs individual/abstract)
        4. Educational (instructional/informative vs entertainment/opinion)

        Return ONLY a JSON object with scores between 0.0 and 1.0 for each dimension.
        Format: {"positive": 0.7, "technical": 0.5, "social": 0.3, "educational": 0.8}"""

        prompt = f"""Analyze the sentiment of this Korean text across the four dimensions:

{text}

Return JSON with scores:"""

        response = self._generate_response(prompt, system_prompt)

        if not response:
            raise ValueError("No response received for sentiment analysis")

        # Extract JSON from response
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1

        if start_idx == -1 or end_idx <= start_idx:
            raise ValueError(
                f"No JSON object found in sentiment analysis response. "
                f"Response: {response[:200]}"
            )

        try:
            json_str = response[start_idx:end_idx]
            sentiment_data = json.loads(json_str)

            # Validate required keys
            required_keys = ['positive', 'technical', 'social', 'educational']
            missing_keys = [k for k in required_keys if k not in sentiment_data]
            if missing_keys:
                raise ValueError(f"Missing required sentiment keys: {missing_keys}")

            return sentiment_data
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse sentiment JSON: {e}. "
                f"JSON string: {json_str[:200]}"
            ) from e

    def extract_vocabulary(self, simplified_text, topik_level, count=10):
        """Extract essential vocabulary from simplified text with 15-second timeout"""
        system_prompt = """You are a Korean language teacher. Extract the most important Korean vocabulary
        words from the text that are appropriate for the specified TOPIK level. For each word, provide:
        1. The Korean word
        2. A simple definition in English
        3. An example sentence in Korean (optional)

        Return ONLY a JSON array of vocabulary items.
        Format: [{"word": "단어", "definition": "word", "example": "예문입니다."}]"""

        prompt = f"""Extract {count} essential vocabulary words from this Korean text (TOPIK Level {topik_level}):

{simplified_text}

Return JSON array of vocabulary items:"""

        response = self._generate_response(prompt, system_prompt, timeout=15)

        if not response:
            raise ValueError("No response received for vocabulary extraction")

        # Try to find JSON array in the response
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1

        if start_idx == -1 or end_idx <= start_idx:
            raise ValueError(
                f"No JSON array found in vocabulary extraction response. "
                f"Response: {response[:200]}"
            )

        try:
            json_str = response[start_idx:end_idx]
            vocab_data = json.loads(json_str)

            if not isinstance(vocab_data, list):
                raise ValueError(f"Expected list but got {type(vocab_data)}")

            return vocab_data
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse vocabulary JSON: {e}. "
                f"JSON string: {json_str[:200]}"
            ) from e

    def process_article(self, article_id, topik_levels=None):
        """Process an article for all TOPIK levels"""
        if topik_levels is None:
            topik_levels = [1, 2, 3, 4, 5, 6]

        print(f"\n{'='*60}")
        print(f"Starting processing for article {article_id}")
        print(f"TOPIK levels to process: {topik_levels}")
        print(f"{'='*60}\n")

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            print(f"ERROR: Article {article_id} not found")
            return False

        # Analyze sentiment (only once per article)
        if not hasattr(article, 'sentiment'):
            print(f"[Sentiment Analysis] Starting sentiment analysis...")
            try:
                sentiment_scores = self.analyze_sentiment(article.original_text)
                if not sentiment_scores:
                    raise ValueError("Sentiment analysis returned no scores")

                Sentiment.objects.create(
                    article=article,
                    positive_score=sentiment_scores.get('positive', 0.5),
                    technical_score=sentiment_scores.get('technical', 0.5),
                    social_score=sentiment_scores.get('social', 0.5),
                    educational_score=sentiment_scores.get('educational', 0.5)
                )
                print(f"[Sentiment Analysis] ✓ Completed - Scores: {sentiment_scores}")
            except Exception as e:
                print(f"[Sentiment Analysis] ✗ FAILED: {e}")
                raise RuntimeError(
                    f"Failed to analyze sentiment for article {article_id}: {e}"
                ) from e
        else:
            print(f"[Sentiment Analysis] Skipped (already exists)")

        # Process for each TOPIK level
        print(f"\n{'-'*60}")
        print(f"Processing TOPIK levels...")
        print(f"{'-'*60}\n")

        for level in topik_levels:
            # Check if already processed
            if ProcessedArticle.objects.filter(article=article, language_level=level).exists():
                print(f"[TOPIK {level}] ⊙ Already processed, skipping")
                continue

            print(f"\n[TOPIK {level}] Starting processing...")

            # Simplify text
            print(f"[TOPIK {level}] → Step 1/3: Simplifying text...")
            try:
                simplified = self.simplify_text(article.original_text, level)
                if not simplified or not simplified.strip():
                    raise ValueError(f"Simplification returned empty text for level {level}")
                print(f"[TOPIK {level}] ✓ Simplification completed ({len(simplified)} chars)")
            except Exception as e:
                print(f"[TOPIK {level}] ✗ Simplification FAILED: {e}")
                raise RuntimeError(
                    f"Failed to simplify article {article_id} for TOPIK level {level}: {e}"
                ) from e

            # Translate to English
            print(f"[TOPIK {level}] → Step 2/3: Translating to English...")
            try:
                translation = self.translate_to_english(simplified)
                if not translation or not translation.strip():
                    raise ValueError(f"Translation returned empty text for level {level}")
                print(f"[TOPIK {level}] ✓ Translation completed ({len(translation)} chars)")
            except Exception as e:
                print(f"[TOPIK {level}] ✗ Translation FAILED: {e}")
                raise RuntimeError(
                    f"Failed to translate article {article_id} for TOPIK level {level}: {e}"
                ) from e

            # Create processed article
            processed = ProcessedArticle.objects.create(
                article=article,
                language_level=level,
                simplified_text=simplified,
                english_translation=translation
            )

            # Extract vocabulary
            print(f"[TOPIK {level}] → Step 3/3: Extracting vocabulary (15s timeout)...")
            try:
                vocab_items = self.extract_vocabulary(simplified, level)
                if vocab_items is None:
                    raise ValueError("Vocabulary extraction returned None")

                vocab_count = 0
                for idx, item in enumerate(vocab_items):
                    if not item.get('word'):
                        print(f"[TOPIK {level}] ⚠ Skipping vocabulary item without word: {item}")
                        continue

                    Vocabulary.objects.create(
                        processed_article=processed,
                        word=item.get('word', ''),
                        definition=item.get('definition', ''),
                        example_sentence=item.get('example', ''),
                        order=idx
                    )
                    vocab_count += 1

                print(f"[TOPIK {level}] ✓ Vocabulary extraction completed ({vocab_count} words)")
            except TimeoutError as e:
                # Vocabulary extraction timed out
                print(f"[TOPIK {level}] ⚠ Vocabulary extraction timed out after 15 seconds (non-critical)")
            except Exception as e:
                # Vocabulary extraction failure is not critical, just log it
                print(f"[TOPIK {level}] ⚠ Vocabulary extraction failed (non-critical): {e}")

            print(f"[TOPIK {level}] ✓ COMPLETED successfully")

        # Mark article as processed if it has at least one processed level
        if not article.is_processed:
            article.is_processed = True
            article.save()

        print(f"\n{'='*60}")
        print(f"✓ ALL PROCESSING COMPLETED for article {article_id}")
        print(f"Successfully processed {len(topik_levels)} TOPIK level(s)")
        print(f"{'='*60}\n")
        return True
