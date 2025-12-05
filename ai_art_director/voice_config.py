# voice_config.py - ENHANCED PACE
# v22.0.2 - Increased voice pace for better engagement

"""Single source of truth for voice configuration across the system"""

def get_consistent_voice_config():
    """Get consistent voice configuration for all TTS operations"""
    return {
        "en": {
            "azure_voice": "en-US-AriaNeural",  # High-quality neural voice
            "gtts_lang": "en",
            "ssml_prosody": {
                "rate": "120%",     # Slightly faster pace for better engagement (was 85%)
                "pitch": "+5%",     # Slightly higher pitch for more engaging tone
                "volume": "+5%",    # Slightly louder for clarity
                "style": "friendly" # More conversational style
            }
        },
        "hi": {
            "azure_voice": "hi-IN-SwaraNeural",  # High-quality Hindi neural voice
            "gtts_lang": "hi",
            "ssml_prosody": {
                "rate": "120%",     # Slightly faster for Hindi (was 80%)
                "pitch": "+5%",     # Higher pitch for engaging Hindi
                "volume": "+5%",
                "style": "cheerful" # More expressive for Hindi
            }
        }
    }

def get_voice_for_lang(lang='en'):
    """Get voice configuration for specific language"""
    config = get_consistent_voice_config()
    return config.get(lang, config["en"])

def get_azure_voice(lang='en'):
    """Get Azure voice for specific language"""
    return get_voice_for_lang(lang)["azure_voice"]

def get_gtts_lang(lang='en'):
    """Get gTTS language code for specific language"""
    return get_voice_for_lang(lang)["gtts_lang"]

def get_ssml_prosody(lang='en'):
    """Get SSML prosody settings for specific language"""
    return get_voice_for_lang(lang)["ssml_prosody"]

def create_ssml_wrapper(text, lang='en'):
    """Create SSML wrapper with proper prosody settings for natural speech"""
    voice_config = get_voice_for_lang(lang)
    prosody = voice_config["ssml_prosody"]
    
    # Enhanced SSML with express-as for more natural speech
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">
        <voice name="{voice_config['azure_voice']}">
            <express-as style="{prosody['style']}">
                <prosody rate="{prosody['rate']}" 
                         pitch="{prosody['pitch']}" 
                         volume="{prosody['volume']}">
                    {text}
                </prosody>
            </express-as>
        </voice>
    </speak>
    """
    return ssml.strip()

def should_use_ssml(text, lang='en'):
    """Determine if SSML should be used for this text"""
    # Use SSML for all Azure TTS calls for consistent natural speech
    return True
