from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    CATEGORY_CHOICES = [
        ('startup_knowledge', 'Startup Knowledge'),
        ('fashion_kbeauty', 'Fashion and K-Beauty'),
        ('economics', 'Economics'),
        ('international_relations', 'International Relations'),
        ('legal_business', 'Legal Issues for Businesses'),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.display_name


class Article(models.Model):
    title = models.CharField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    original_text = models.TextField()
    source_url = models.URLField(blank=True, null=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ProcessedArticle(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='processed_versions')
    language_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="TOPIK level (1-6)"
    )
    simplified_text = models.TextField()
    english_translation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['article', 'language_level']
        ordering = ['language_level']

    def __str__(self):
        return f"{self.article.title} - Level {self.language_level}"


class Sentiment(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name='sentiment')
    positive_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    technical_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    social_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    educational_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sentiment for {self.article.title}"


class Vocabulary(models.Model):
    processed_article = models.ForeignKey(
        ProcessedArticle,
        on_delete=models.CASCADE,
        related_name='vocabulary_items'
    )
    word = models.CharField(max_length=100)
    definition = models.TextField()
    example_sentence = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Vocabulary items"
        ordering = ['order', 'word']

    def __str__(self):
        return f"{self.word} (Level {self.processed_article.language_level})"
