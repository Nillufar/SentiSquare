from django.contrib import admin
from .models import Category, Article, ProcessedArticle, Sentiment, Vocabulary


class VocabularyInline(admin.TabularInline):
    model = Vocabulary
    extra = 1


class ProcessedArticleInline(admin.StackedInline):
    model = ProcessedArticle
    extra = 0
    show_change_link = True


class SentimentInline(admin.StackedInline):
    model = Sentiment
    max_num = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name']
    search_fields = ['display_name', 'name']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_processed', 'created_at']
    list_filter = ['category', 'is_processed', 'created_at']
    search_fields = ['title', 'original_text']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [SentimentInline, ProcessedArticleInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'category')
        }),
        ('Content', {
            'fields': ('original_text',)
        }),
        ('Source', {
            'fields': ('source_url', 'file_path')
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'created_at', 'updated_at')
        }),
    )


@admin.register(ProcessedArticle)
class ProcessedArticleAdmin(admin.ModelAdmin):
    list_display = ['article', 'language_level', 'created_at']
    list_filter = ['language_level', 'created_at']
    search_fields = ['article__title', 'simplified_text', 'english_translation']
    readonly_fields = ['created_at']
    inlines = [VocabularyInline]


@admin.register(Sentiment)
class SentimentAdmin(admin.ModelAdmin):
    list_display = ['article', 'positive_score', 'technical_score', 'social_score', 'educational_score']
    list_filter = ['created_at']
    search_fields = ['article__title']
    readonly_fields = ['created_at']


@admin.register(Vocabulary)
class VocabularyAdmin(admin.ModelAdmin):
    list_display = ['word', 'processed_article', 'order']
    list_filter = ['processed_article__language_level']
    search_fields = ['word', 'definition']
