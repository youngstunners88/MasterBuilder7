#!/usr/bin/env python3
"""
Demo: Autonomous Refactoring Agent

This demo shows how to use the refactoring agent to detect code smells
and apply automated refactorings.
"""

import sys
sys.path.insert(0, '..')

from src.detector import CodeSmellDetector
from src.refactorer import Refactorer


def demo_detect_smells():
    """Demo: Detect code smells."""
    print("=" * 60)
    print("DEMO 1: Code Smell Detection")
    print("=" * 60)
    
    code = """
def process_order(order, customer, shipping, billing, discount, tax_rate, notes):
    if order.status == "pending":
        if customer.is_active:
            if order.amount > 100:
                if discount > 0:
                    final_amount = order.amount * (1 - discount)
                    if final_amount > 0:
                        return final_amount * (1 + tax_rate)
    return None
"""
    
    detector = CodeSmellDetector()
    smells = detector.detect(code, "orders.py")
    
    print(f"\nDetected {len(smells)} code smells:\n")
    
    for smell in smells:
        print(f"[{smell.severity.upper()}] {smell.smell_type.name}")
        print(f"  {smell.message}")
        if smell.suggestions:
            print("  Suggestions:")
            for suggestion in smell.suggestions:
                print(f"    → {suggestion}")
        print()


if __name__ == "__main__":
    demo_detect_smells()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)
