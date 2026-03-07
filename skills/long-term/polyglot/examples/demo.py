#!/usr/bin/env python3
"""
Demo: Cross-Language Polyglot

This demo shows how to translate code between programming languages.
"""

import sys
sys.path.insert(0, '..')

from src.translator import PolyglotTranslator, TranslationRequest, Language


def demo_python_to_javascript():
    """Demo: Translate Python to JavaScript."""
    print("=" * 60)
    print("DEMO 1: Python to JavaScript")
    print("=" * 60)
    
    python_code = """
def greet(name):
    return f"Hello, {name}!"
"""
    
    translator = PolyglotTranslator()
    
    request = TranslationRequest(
        source_code=python_code,
        source_language=Language.PYTHON,
        target_language=Language.JAVASCRIPT,
    )
    
    result = translator.translate(request)
    
    print("\n--- Python ---")
    print(python_code)
    
    print("\n--- JavaScript ---")
    print(result.target_code)
    
    print(f"\nConfidence: {result.confidence:.0%}")


if __name__ == "__main__":
    demo_python_to_javascript()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)
