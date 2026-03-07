#!/usr/bin/env python3
"""
Integration Tests for Long-Term Skills

Tests the interaction between all 4 advanced skills.
"""

import sys
from pathlib import Path

# Add all skill paths
sys.path.insert(0, str(Path(__file__) / "speech-to-code"))
sys.path.insert(0, str(Path(__file__) / "autonomous-refactor"))
sys.path.insert(0, str(Path(__file__) / "polyglot"))
sys.path.insert(0, str(Path(__file__) / "business-logic-extractor"))


def test_end_to_end_workflow():
    """
    Test a complete workflow using all 4 skills:
    1. Generate code with speech-to-code
    2. Validate with autonomous-refactor
    3. Translate with polyglot
    4. Extract business logic
    """
    print("=" * 70)
    print("INTEGRATION TEST: End-to-End Workflow")
    print("=" * 70)
    
    # Step 1: Generate code
    print("\n[1/4] Generating code with Speech-to-Code...")
    from speech_to_code import CodeSynthesizer, SynthesisRequest
    
    synthesizer = CodeSynthesizer()
    request = SynthesisRequest(
        description="Create an order processing API with validation rules",
        framework="fastapi",
        include_auth=True,
    )
    synthesis_result = synthesizer.synthesize(request)
    
    generated_code = synthesis_result.files.get("routes.py", "")
    print(f"✓ Generated {len(synthesis_result.files)} files")
    
    # Step 2: Detect smells
    print("\n[2/4] Analyzing code with Autonomous Refactor...")
    from autonomous_refactor import CodeSmellDetector
    
    detector = CodeSmellDetector()
    smells = detector.detect(generated_code, "routes.py")
    
    print(f"✓ Detected {len(smells)} code smells")
    
    # Step 3: Translate to another language
    print("\n[3/4] Translating with Polyglot...")
    from polyglot import PolyglotTranslator, TranslationRequest, Language
    
    translator = PolyglotTranslator()
    translation_request = TranslationRequest(
        source_code=generated_code,
        source_language=Language.PYTHON,
        target_language=Language.JAVASCRIPT,
    )
    translation_result = translator.translate(translation_request)
    
    print(f"✓ Translated to JavaScript (confidence: {translation_result.confidence:.0%})")
    
    # Step 4: Extract business logic
    print("\n[4/4] Extracting business logic...")
    from business_logic_extractor import BusinessLogicExtractor
    
    extractor = BusinessLogicExtractor()
    extraction_result = extractor.extract(generated_code, "routes.py")
    
    print(f"✓ Extracted {len(extraction_result.rules)} business rules")
    print(f"✓ Found {len(extraction_result.entities)} domain entities")
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST PASSED!")
    print("=" * 70)
    
    return True


def test_skill_imports():
    """Test that all skills can be imported."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Module Imports")
    print("=" * 70)
    
    errors = []
    
    try:
        from speech_to_code import CodeSynthesizer
        print("✓ speech-to-code")
    except Exception as e:
        errors.append(f"speech-to-code: {e}")
        print(f"✗ speech-to-code: {e}")
    
    try:
        from autonomous_refactor import CodeSmellDetector, Refactorer
        print("✓ autonomous-refactor")
    except Exception as e:
        errors.append(f"autonomous-refactor: {e}")
        print(f"✗ autonomous-refactor: {e}")
    
    try:
        from polyglot import PolyglotTranslator
        print("✓ polyglot")
    except Exception as e:
        errors.append(f"polyglot: {e}")
        print(f"✗ polyglot: {e}")
    
    try:
        from business_logic_extractor import BusinessLogicExtractor
        print("✓ business-logic-extractor")
    except Exception as e:
        errors.append(f"business-logic-extractor: {e}")
        print(f"✗ business-logic-extractor: {e}")
    
    if errors:
        print(f"\n✗ {len(errors)} import errors")
        return False
    else:
        print("\n✓ All modules imported successfully")
        return True


def test_cross_skill_data_exchange():
    """Test that data can be exchanged between skills."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Data Exchange")
    print("=" * 70)
    
    # Generate code
    from speech_to_code import CodeSynthesizer, SynthesisRequest
    synthesizer = CodeSynthesizer()
    request = SynthesisRequest(
        description="User authentication API",
        framework="fastapi",
    )
    result = synthesizer.synthesize(request)
    
    # Pass generated code to refactor detector
    from autonomous_refactor import CodeSmellDetector
    detector = CodeSmellDetector()
    smells = detector.detect(result.files.get("routes.py", ""), "routes.py")
    
    # Pass smells to refactorer
    from autonomous_refactor import Refactorer
    refactorer = Refactorer()
    
    # Generate plan
    plan = refactorer.generate_refactoring_plan(smells, max_effort_hours=2.0)
    
    print(f"✓ Generated code: {len(result.files)} files")
    print(f"✓ Detected smells: {len(smells)}")
    print(f"✓ Refactoring plan: {plan['planned_refactorings']} items")
    
    return True


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "🧪" * 35)
    print("\nRunning Long-Term Skills Integration Tests\n")
    print("🧪" * 35 + "\n")
    
    tests = [
        ("Module Imports", test_skill_imports),
        ("Data Exchange", test_cross_skill_data_exchange),
        ("End-to-End Workflow", test_end_to_end_workflow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
