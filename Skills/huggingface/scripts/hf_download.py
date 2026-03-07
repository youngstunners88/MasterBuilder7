#!/usr/bin/env python3
"""HuggingFace download utilities"""
import argparse
import os
from huggingface_hub import snapshot_download, HfApi

def download_model(model_id: str, local_dir: str = None):
    """Download a model from Hugging Face Hub"""
    if local_dir is None:
        local_dir = f"./models/{model_id.replace('/', '_')}"
    
    print(f"Downloading {model_id} to {local_dir}...")
    snapshot_download(repo_id=model_id, local_dir=local_dir)
    print(f"Done! Model saved to {local_dir}")

def download_dataset(dataset_name: str, local_dir: str = None):
    """Download a dataset from Hugging Face Hub"""
    if local_dir is None:
        local_dir = f"./datasets/{dataset_name.replace('/', '_')}"
    
    print(f"Downloading dataset {dataset_name}...")
    snapshot_download(repo_id=dataset_name, local_dir=local_dir, repo_type="dataset")
    print(f"Done! Dataset saved to {local_dir}")

def list_models(query: str = None, limit: int = 10):
    """List popular models"""
    api = HfApi()
    models = api.list_models(search=query, limit=limit)
    for m in models:
        print(f"{m.id} - {m.downloads:,} downloads")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HuggingFace utilities")
    sub = parser.add_subparsers()
    
    m = sub.add_parser("model", help="Download model")
    m.add_argument("model_id", help="Model ID (e.g. meta-llama/Llama-2-7b)")
    m.add_argument("--dir", help="Local directory")
    m.set_defaults(func=lambda a: download_model(a.model_id, a.dir))
    
    d = sub.add_parser("dataset", help="Download dataset")
    d.add_argument("dataset_name", help="Dataset name")
    d.add_argument("--dir", help="Local directory")
    d.set_defaults(func=lambda a: download_dataset(a.dataset_name, a.dir))
    
    l = sub.add_parser("list", help="List models")
    l.add_argument("--query", "-q", help="Search query")
    l.add_argument("--limit", "-n", type=int, default=10)
    l.set_defaults(func=lambda a: list_models(a.query, a.limit))
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()