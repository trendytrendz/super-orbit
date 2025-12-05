# story_runners_refactored/story_utils.py
# v24.3.2 - Fixed Rupee Symbol Rendering

import os
import random
import time
from typing import Dict, List, Any, Optional

from .. import config
from .. import utils

class StoryUtils:
    """Shared utilities for all story types"""
    
    @staticmethod
    def clean_company_name(company_name: str) -> str:
        """Clean company name by removing common suffixes"""
        suffixes = ['Limited', 'Ltd', 'Ltd.', 'Incorporated', 'Inc', 'Inc.', 
                   'Corporation', 'Corp', 'Corp.']
        
        clean_name = company_name
        for suffix in suffixes:
            patterns = [f" {suffix}", f" {suffix}.", f"{suffix}", f"{suffix}."]
            for pattern in patterns:
                clean_name = clean_name.replace(pattern, "")
        
        clean_name = ' '.join(clean_name.split())
        return clean_name.strip() if clean_name.strip() else company_name
    
    @staticmethod
    def format_market_cap_display(market_cap: Optional[float]) -> Optional[str]:
        """Format market cap for better display"""
        if not market_cap:
            return None
            
        # FIX: Changed '₹' to 'Rs.' to prevent font rendering issues (Square Box)
        if market_cap >= 100000:  # 1 lakh crores = 1 trillion
            return f"Rs. {market_cap/100000:.1f} Trillion"
        elif market_cap >= 1000:  # 1 thousand crores
            return f"Rs. {market_cap/1000:.1f} k Cr"  
        else:
            return f"Rs. {market_cap:,.0f} Cr"
    
    @staticmethod
    def ensure_financials_narration(english_script_parts: Dict, company_name: str) -> Dict:
        """Ensure financials narration exists, add fallback if missing"""
        if 'financials' not in english_script_parts or not english_script_parts['financials']:
            print("   ⚠️  No financials narration found, adding fallback")
            english_script_parts['financials'] = f"Now let's examine {company_name}'s financial performance and revenue trends."
        return english_script_parts
    
    @staticmethod
    def validate_slides_audio_sync(slides: List[Dict], audio_paths: Dict) -> bool:
        """Validate that all slides have corresponding audio"""
        missing_audio = []
        
        for slide in slides:
            key = slide.get('key')
            if key and key not in audio_paths:
                missing_audio.append(key)
        
        if missing_audio:
            print(f"   ⚠️  Missing audio for slides: {missing_audio}")
            return False
            
        print(f"   ✅ All {len(slides)} slides have audio files")
        return True
    
    @staticmethod
    def get_story_theme(story_type: str) -> Dict:
        """Get theme configuration for specific story type"""
        return config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])