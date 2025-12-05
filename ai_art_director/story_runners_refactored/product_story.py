# product_story.py
# v20.1.8
from base_story_runner import BaseStoryRunner
import story_runners_utils as utils
import story_assets
import slide_renderers
import story_composer

class ProductStoryRunner(BaseStoryRunner):
    """Runner for product-style stories"""
    
    def generate_story(self):
        print("🎬 Generating Product Story...")
        
        # Validate and setup
        self.validate_story_data()
        size = self.get_video_size()
        total_duration = self.get_total_duration()
        
        # Load assets
        assets = story_assets.load_story_assets(self.story_data, self.story_type)
        print("  - Assets loaded")
        
        # Calculate slide durations
        durations = utils.calculate_slide_durations(
            total_duration, 
            len(self.story_data['slides']), 
            self.story_type
        )
        
        # Render slides
        slide_clips = []
        for i, slide_info in enumerate(self.story_data['slides']):
            print(f"  - Processing slide {i+1}/{len(self.story_data['slides'])}")
            
            clip = slide_renderers.render_slide_by_type(
                slide_info,
                self.story_type,
                assets,
                self.theme,
                durations[i],
                size,
                i
            )
            slide_clips.append(clip)
        
        # Apply animations
        animated_clips = utils.create_slide_clips_with_animation(
            slide_clips, durations, size
        )
        
        # Compose final video
        output_path = story_composer.compose_story_video(
            animated_clips, durations, assets, size, self.output_path
        )
        
        print(f"✅ Product story generated: {output_path}")
        return output_path
