---
name: hf-download
description: |
  Download models or datasets from HuggingFace Hub.
  
  Use when:
  - User wants to download AI models
  - User wants to fetch datasets
  - User mentions "huggingface" or "HF"
  - User wants to use models locally
  
  Don't use when:
  - User wants to browse/search (use hf-search)
  - User wants inference only (use hf-inference)

inputs:
  item_type: model|dataset
  item_id: "e.g., meta-llama/Llama-3-8B"
  destination: local_path

tools:
  - huggingface_hub (Python library)
  - run_bash_command

output: Downloaded files to specified path

negative_examples:
  - "Find popular models" → use hf-search
  - "Generate image" → use generate_image