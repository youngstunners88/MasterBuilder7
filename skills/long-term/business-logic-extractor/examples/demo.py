#!/usr/bin/env python3
"""
Demo: Business Logic Extractor

This demo shows how to extract business rules from code.
"""

import sys
sys.path.insert(0, '..')

from src.extractor import BusinessLogicExtractor


def demo_extract_rules():
    """Demo: Extract business rules."""
    print("=" * 60)
    print("DEMO 1: Business Rule Extraction")
    print("=" * 60)
    
    code = """
def process_order(order, customer):
    if order.amount <= 0:
        raise ValueError("Amount must be positive")
    
    if not customer.is_active:
        raise ValueError("Customer not active")
    
    if order.amount > 1000:
        discount = 0.10
    else:
        discount = 0.0
    
    return order.amount * (1 - discount)
"""
    
    extractor = BusinessLogicExtractor()
    result = extractor.extract(code, "orders.py")
    
    print(f"\nExtracted {len(result.rules)} business rules:\n")
    
    for rule in result.rules:
        print(f"[{rule.rule_type.value.upper()}] {rule.name}")
        print(f"  {rule.description}")
        print()


if __name__ == "__main__":
    demo_extract_rules()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)
