#!/usr/bin/env python3
"""Example: Generate architecture diagrams from code."""

import sys
sys.path.insert(0, '..')

from src.parser import CodeParser
from src.mermaid_gen import MermaidGenerator, DiagramConfig
from src.c4_gen import C4Generator
from src.renderer import DiagramRenderer

def main():
    print("=" * 60)
    print("Visual Architecture Generator - Example")
    print("=" * 60)
    
    # Parse code
    print("\n1. Parsing code...")
    parser = CodeParser()
    
    # Parse current directory
    parsed_files = parser.parse_directory("../src", pattern="*.py")
    print(f"   Parsed {len(parsed_files)} files")
    
    # Show parsed classes
    total_classes = sum(len(pf.classes) for pf in parsed_files)
    total_functions = sum(len(pf.functions) for pf in parsed_files)
    print(f"   Found {total_classes} classes and {total_functions} functions")
    
    # Generate Mermaid diagrams
    print("\n2. Generating Mermaid diagrams...")
    
    config = DiagramConfig(
        direction="TD",
        theme="dark",
        show_private=False,
        show_methods=True
    )
    
    mermaid = MermaidGenerator(config)
    
    # Class diagram
    class_diagram = mermaid.generate_class_diagram(
        parsed_files, 
        title="Skill6 Architecture"
    )
    with open("class_diagram.mmd", "w") as f:
        f.write(class_diagram)
    print("   ✓ Generated class_diagram.mmd")
    
    # Component diagram
    component_diagram = mermaid.generate_component_diagram(
        parsed_files,
        title="Module Dependencies"
    )
    with open("component_diagram.mmd", "w") as f:
        f.write(component_diagram)
    print("   ✓ Generated component_diagram.mmd")
    
    # Generate C4 Model
    print("\n3. Generating C4 Model diagrams...")
    
    c4 = C4Generator()
    c4.analyze_codebase(parsed_files, "Visual Architecture Skill")
    
    # Generate all levels
    output_dir = "./c4_diagrams"
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    c4.generate_all_levels(output_dir)
    print(f"   ✓ Generated C4 diagrams in {output_dir}/")
    
    # Render diagrams
    print("\n4. Rendering diagrams...")
    
    renderer = DiagramRenderer()
    
    # Create HTML report with all diagrams
    diagrams = {
        "Class Diagram": class_diagram,
        "Component Diagram": component_diagram,
    }
    
    renderer.render_to_html(diagrams, "architecture_report.html", 
                           "Visual Architecture Report")
    print("   ✓ Generated architecture_report.html")
    
    # Render individual SVGs (if mmdc is available)
    try:
        renderer.render(class_diagram, "class_diagram.svg")
        print("   ✓ Generated class_diagram.svg")
    except Exception as e:
        print(f"   ⚠ Could not render SVG (mmdc not installed?): {e}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()