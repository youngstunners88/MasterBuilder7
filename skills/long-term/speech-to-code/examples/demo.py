#!/usr/bin/env python3
"""
Demo: Code Synthesis from Speech

This demo shows how to use the Speech-to-Code skill to generate
complete code implementations from natural language descriptions.
"""

import sys
sys.path.insert(0, '..')

from src.synthesizer import CodeSynthesizer, SynthesisRequest


def demo_fastapi_api():
    """Demo: Generate a FastAPI REST API."""
    print("=" * 60)
    print("DEMO 1: FastAPI REST API")
    print("=" * 60)
    
    synthesizer = CodeSynthesizer()
    
    request = SynthesisRequest(
        description="""
        Build a complete REST API for an e-commerce system.
        It should manage products with name, price, and stock.
        Include JWT authentication for protected endpoints.
        """,
        framework="fastapi",
        include_auth=True,
        include_tests=True,
    )
    
    result = synthesizer.synthesize(request)
    
    print(f"\nGenerated {len(result.files)} files:")
    for filename in result.files:
        print(f"  - {filename}")
    
    print(f"\nComplexity: {result.estimated_complexity}")
    print(f"\nDependencies: {', '.join(result.dependencies)}")
    
    print("\n--- main.py ---")
    print(result.files.get("main.py", "Not generated"))


def demo_react_component():
    """Demo: Generate a React component."""
    print("\n" + "=" * 60)
    print("DEMO 2: React Component")
    print("=" * 60)
    
    synthesizer = CodeSynthesizer()
    
    request = SynthesisRequest(
        description="""
        Create a user profile card component.
        It should display the user's avatar, name, email, and join date.
        Include a button to edit the profile.
        """,
        framework="react",
    )
    
    result = synthesizer.synthesize(request)
    
    print(f"\nGenerated {len(result.files)} files:")
    for filename in result.files:
        print(f"  - {filename}")
    
    print("\n--- App.jsx ---")
    print(result.files.get("App.jsx", "Not generated"))


if __name__ == "__main__":
    demo_fastapi_api()
    demo_react_component()
    
    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
