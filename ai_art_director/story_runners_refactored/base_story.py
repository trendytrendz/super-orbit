# story_runners_refactored/base_story.py
# v24.1.0 - Fixed abstract method signature

import os
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from .. import config
from .. import utils

class BaseStory(ABC):
    """Base class for all story types with common functionality"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.theme = config_dict.get('theme', {})
        self.icon_svg = config_dict.get('icon_svg', {})
        self.lang = config_dict.get('lang', 'en')
        self.script_dir = utils.get_script_dir()
        
    @abstractmethod
    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        """Generate complete story - to be implemented by subclasses"""
        pass
    
    def _get_chart_size(self, video_format: str) -> tuple:
        """Get chart dimensions based on video format"""
        if video_format == 'landscape':
            return (1200, 600)
        return (680, 500)  # portrait
    
    def _log_story_generation(self, story_type: str, symbol: str, success: bool, error: str = None):
        """Log story generation metrics"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{'='*60}")
        print(f"🎬 {story_type.upper()} STORY GENERATION: {status}")
        print(f"   Company: {symbol}")
        print(f"   Language: {self.lang}")
        if error:
            print(f"   Error: {error}")
        print(f"{'='*60}")
