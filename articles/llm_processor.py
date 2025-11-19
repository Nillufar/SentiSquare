import ollama
import json
from django.conf import settings
from .models import Article, ProcessedArticle, Sentiment, Vocabulary


class LLMProcessor:
    def __init__(self, model=None, host=None):
        self.model = model or settings.OLLAMA_MODEL
        self.host = host or settings.OLLAMA_HOST

    def _generate_response(self, prompt, system_prompt=None):
        """Generate response from Ollama"""
        try:
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

            response = ollama.chat(
                model=self.model,
                messages=messages
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

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

        try:
            # Extract JSON from response
            if response:
                # Try to find JSON in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    sentiment_data = json.loads(json_str)
                    return sentiment_data
        except Exception as e:
            print(f"Error parsing sentiment: {e}")

        # Return default values if parsing fails
        return {
            "positive": 0.5,
            "technical": 0.5,
            "social": 0.5,
            "educational": 0.5
        }

    def extract_vocabulary(self, simplified_text, topik_level, count=10):
        """Extract essential vocabulary from simplified text"""
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

        response = self._generate_response(prompt, system_prompt)

        try:
            if response:
                # Try to find JSON array in the response
                start_idx = response.find('[')
                end_idx = response.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    vocab_data = json.loads(json_str)
                    return vocab_data
        except Exception as e:
            print(f"Error parsing vocabulary: {e}")

        return []

    def process_article(self, article_id, topik_levels=None):
        """Process an article for all TOPIK levels"""
        if topik_levels is None:
            topik_levels = [1, 2, 3, 4, 5, 6]

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            print(f"Article {article_id} not found")
            return False

        # Analyze sentiment (only once per article)
        if not hasattr(article, 'sentiment'):
            sentiment_scores = self.analyze_sentiment(article.original_text)
            Sentiment.objects.create(
                article=article,
                positive_score=sentiment_scores.get('positive', 0.5),
                technical_score=sentiment_scores.get('technical', 0.5),
                social_score=sentiment_scores.get('social', 0.5),
                educational_score=sentiment_scores.get('educational', 0.5)
            )

        # Process for each TOPIK level
        for level in topik_levels:
            # Check if already processed
            if ProcessedArticle.objects.filter(article=article, language_level=level).exists():
                print(f"Article {article_id} already processed for level {level}")
                continue

            print(f"Processing article {article_id} for TOPIK level {level}...")

            # Simplify text
            simplified = self.simplify_text(article.original_text, level)
            if not simplified:
                print(f"Failed to simplify for level {level}")
                continue

            # Translate to English
            translation = self.translate_to_english(simplified)
            if not translation:
                print(f"Failed to translate for level {level}")
                continue

            # Create processed article
            processed = ProcessedArticle.objects.create(
                article=article,
                language_level=level,
                simplified_text=simplified,
                english_translation=translation
            )

            # Extract vocabulary
            vocab_items = self.extract_vocabulary(simplified, level)
            for idx, item in enumerate(vocab_items):
                Vocabulary.objects.create(
                    processed_article=processed,
                    word=item.get('word', ''),
                    definition=item.get('definition', ''),
                    example_sentence=item.get('example', ''),
                    order=idx
                )

        # Mark article as processed
        article.is_processed = True
        article.save()

        print(f"Successfully processed article {article_id}")
        return True
