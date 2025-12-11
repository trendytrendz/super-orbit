# story_runners.py

"""
Story Runner Factory
v24.1.0

- Replaces the migration gateway with a simple, clean factory pattern.
- Removes all fallback logic to 'story_runners_original.py'.
- Instantiates and returns the correct story runner class from the refactored package.
"""
from typing import Dict, Any

# Use standard package-relative imports
from .story_runners_refactored.base_story import BaseStory
from .story_runners_refactored.news_story import NewsStory
from .story_runners_refactored.deepdive_story import DeepDiveStory
from .story_runners_refactored.comparison_story import ComparisonStory
from .story_runners_refactored.spotlight_story import SpotlightStory
# NEW IMPORTS
from .story_runners_refactored.custom_news_story import CustomNewsStory
from .story_runners_refactored.news_roundup_story import NewsRoundupStory

STORY_RUNNER_MAP = {
    "news": NewsStory,
    "deepdive": DeepDiveStory,
    "comparison": ComparisonStory,
    "spotlight": SpotlightStory,
    "custom_news": CustomNewsStory,   # <--- Registered
    "news_roundup": NewsRoundupStory  # <--- Registered
}

print("✅ Story Runner Factory Initialized")
print(f"   Available Story Types: {list(STORY_RUNNER_MAP.keys())}")

def get_story_runner(story_type: str, config: Dict[str, Any]) -> BaseStory:
    """
    Factory function to get an initialized story runner instance.
    """
    runner_class = STORY_RUNNER_MAP.get(story_type)
    if not runner_class:
        raise ValueError(f"Unknown story type: '{story_type}'. Available types are: {list(STORY_RUNNER_MAP.keys())}")

    print(f"   -> Factory: Creating instance of '{runner_class.__name__}'")
    return runner_class(config)
