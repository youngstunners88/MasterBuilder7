"""
Internationalization (i18n) service for iHhashi.
Supports English, Zulu, Xhosa, and Afrikaans.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache


class I18nService:
    """Service for managing translations."""
    
    SUPPORTED_LANGUAGES = ["en", "zu", "xh", "af"]
    DEFAULT_LANGUAGE = "en"
    
    def __init__(self):
        self.locales_dir = Path(__file__).parent / "locales"
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files into memory."""
        for lang in self.SUPPORTED_LANGUAGES:
            file_path = self.locales_dir / f"{lang}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
    
    def get_translation(self, key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """
        Get a translation by key.
        
        Args:
            key: Dot-notation key (e.g., "auth.login")
            lang: Language code (en, zu, xh, af)
            **kwargs: Variables to interpolate into the translation
            
        Returns:
            Translated string
        """
        # Fallback to default language if not supported
        if lang not in self.SUPPORTED_LANGUAGES:
            lang = self.DEFAULT_LANGUAGE
        
        # Get translations for language
        translations = self._translations.get(lang, self._translations.get(self.DEFAULT_LANGUAGE, {}))
        
        # Navigate to the key
        keys = key.split(".")
        value = translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Fallback to English if key not found
                if lang != self.DEFAULT_LANGUAGE:
                    return self.get_translation(key, self.DEFAULT_LANGUAGE, **kwargs)
                return key  # Return key itself if not found
        
        # Interpolate variables if any
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value if isinstance(value, str) else key
    
    def get_all_translations(self, lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """Get all translations for a language."""
        if lang not in self.SUPPORTED_LANGUAGES:
            lang = self.DEFAULT_LANGUAGE
        return self._translations.get(lang, self._translations.get(self.DEFAULT_LANGUAGE, {}))
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return self.SUPPORTED_LANGUAGES
    
    def get_language_name(self, lang: str) -> str:
        """Get the native name of a language."""
        names = {
            "en": "English",
            "zu": "isiZulu",
            "xh": "isiXhosa",
            "af": "Afrikaans"
        }
        return names.get(lang, lang)


# Global instance
_i18n_service: Optional[I18nService] = None


def get_i18n() -> I18nService:
    """Get the global i18n service instance."""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service


def t(key: str, lang: str = "en", **kwargs) -> str:
    """
    Shorthand for getting translations.
    
    Usage:
        from app.i18n import t
        text = t("auth.login", lang="zu")
    """
    return get_i18n().get_translation(key, lang, **kwargs)
