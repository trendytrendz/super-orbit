# story_runners_refactored/__init__.py
# v23.0.2 - Fixed imports

from .deepdive_story import DeepDiveStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager

# Try to import NewsStory if it exists
try:
    from .news_story import NewsStory
    NEWS_STORY_AVAILABLE = True
except ImportError:
    print("⚠️  NewsStory not available in refactored package")
    NEWS_STORY_AVAILABLE = False
    NewsStory = None

# Re-export for easy access
__all__ = ['DeepDiveStory', 'StoryUtils', 'BackgroundManager']

# Conditionally add NewsStory to exports
if NEWS_STORY_AVAILABLE:
    __all__.append('NewsStory')
