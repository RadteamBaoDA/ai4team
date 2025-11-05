#!/usr/bin/env python
"""
Setup script for initializing tiktoken and Hugging Face offline modes with local cache.

This script can be run independently to download and cache tiktoken encodings and
Hugging Face models for offline operation without requiring network access.

Usage:
    python setup_tiktoken.py                                    # Use defaults
    python setup_tiktoken.py /custom/cache/dir                  # Use custom cache dir
    python setup_tiktoken.py --models bert-base-uncased         # Download HF models
"""

import sys
import os
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Setup tiktoken and Hugging Face offline modes with local cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_tiktoken.py
  python setup_tiktoken.py /path/to/models
  python setup_tiktoken.py -e cl100k_base p50k_base
  python setup_tiktoken.py --models bert-base-uncased
  python setup_tiktoken.py -e cl100k_base --models bert-base-uncased
  python setup_tiktoken.py --help
        """
    )
    
    parser.add_argument(
        "cache_dir",
        nargs="?",
        default="./models",
        help="Base directory for model cache (default: ./models)"
    )
    
    parser.add_argument(
        "-e", "--encodings",
        nargs="+",
        default=["cl100k_base", "p50k_base", "p50k_edit", "r50k_base"],
        help="Tiktoken encodings to download (default: all common encodings)"
    )
    
    parser.add_argument(
        "-m", "--models",
        nargs="+",
        default=[],
        help="Hugging Face models to download (e.g., bert-base-uncased sentence-transformers/all-mpnet-base-v2)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--skip-tiktoken",
        action="store_true",
        help="Skip tiktoken setup"
    )
    
    parser.add_argument(
        "--skip-hf",
        action="store_true",
        help="Skip Hugging Face setup"
    )
    
    args = parser.parse_args()
    cache_base = os.path.abspath(args.cache_dir)
    
    print("=" * 70)
    print("Offline Mode Setup - Tiktoken + Hugging Face")
    print("=" * 70)
    print(f"\nBase Cache Directory: {cache_base}")
    print()
    
    # Add the guardrails module to path
    script_dir = Path(__file__).parent
    guardrails_src = script_dir / "src"
    if guardrails_src.exists():
        sys.path.insert(0, str(guardrails_src.parent))
    
    try:
        from ollama_guardrails.utils.tiktoken_cache import (
            setup_tiktoken_offline_mode,
            download_tiktoken_encoding,
            get_tiktoken_cache_info,
        )
        from ollama_guardrails.utils.huggingface_cache import (
            setup_huggingface_offline_mode,
            download_huggingface_model,
            get_huggingface_cache_info,
        )
    except ImportError as e:
        print(f"Error: Could not import ollama_guardrails utilities: {e}")
        print("\nMake sure you're running this script from the guardrails directory:")
        print("  cd ai4team/guardrails")
        print("  python setup_tiktoken.py")
        sys.exit(1)
    
    # Setup tiktoken
    if not args.skip_tiktoken:
        tiktoken_cache = os.path.join(cache_base, 'tiktoken')
        print("=" * 70)
        print("Setting up Tiktoken Offline Mode")
        print("=" * 70)
        print(f"Cache Directory: {tiktoken_cache}\n")
        
        print("Configuring offline mode...")
        if not setup_tiktoken_offline_mode(tiktoken_cache):
            print("Failed to setup offline mode")
            sys.exit(1)
        
        print("✓ Offline mode configured\n")
        
        print("Downloading encodings...")
        success_count = 0
        for i, encoding in enumerate(args.encodings, 1):
            print(f"  [{i}/{len(args.encodings)}] {encoding}...", end=" ", flush=True)
            if download_tiktoken_encoding(encoding, tiktoken_cache):
                print("✓")
                success_count += 1
            else:
                print("✗")
        
        print()
        
        if success_count == len(args.encodings):
            print(f"✓ Successfully downloaded {success_count}/{len(args.encodings)} encodings")
        else:
            print(f"⚠ Downloaded {success_count}/{len(args.encodings)} encodings (some failed)")
        
        # Show cache info
        info = get_tiktoken_cache_info()
        print("\nTiktoken Cache Information:")
        print(f"  Directory: {info['cache_dir']}")
        print(f"  Size: {info['cache_size_mb']:.2f} MB")
        print(f"  Files: {len(info['cached_files'])}")
        if info['cached_files']:
            for filename in sorted(info['cached_files'])[:5]:
                print(f"    - {filename}")
            if len(info['cached_files']) > 5:
                print(f"    ... and {len(info['cached_files']) - 5} more files")
    
    # Setup Hugging Face
    if not args.skip_hf:
        hf_cache = os.path.join(cache_base, 'huggingface')
        print("\n" + "=" * 70)
        print("Setting up Hugging Face Offline Mode")
        print("=" * 70)
        print(f"Cache Directory: {hf_cache}\n")
        
        print("Configuring offline mode...")
        if not setup_huggingface_offline_mode(hf_cache):
            print("Failed to setup Hugging Face offline mode")
            sys.exit(1)
        
        print("✓ Hugging Face offline mode configured\n")
        
        if args.models:
            print("Downloading models...")
            success_count = 0
            for i, model_id in enumerate(args.models, 1):
                print(f"  [{i}/{len(args.models)}] {model_id}...", end=" ", flush=True)
                if download_huggingface_model(model_id, hf_cache):
                    print("✓")
                    success_count += 1
                else:
                    print("✗")
            
            print()
            
            if success_count == len(args.models):
                print(f"✓ Successfully downloaded {success_count}/{len(args.models)} models")
            else:
                print(f"⚠ Downloaded {success_count}/{len(args.models)} models (some failed)")
        
        # Show cache info
        info = get_huggingface_cache_info()
        print("\nHugging Face Cache Information:")
        print(f"  HF_HOME: {info['hf_home']}")
        print(f"  Size: {info['hf_home_size_mb']:.2f} MB")
        print(f"  Transformers Models: {info['transformers_files']} files")
        print(f"  Datasets: {info['datasets_files']} files")
    
    print("\n" + "=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Set environment variables (optional):")
    if not args.skip_tiktoken:
        print(f"   export TIKTOKEN_CACHE_DIR={os.path.join(cache_base, 'tiktoken')}")
    if not args.skip_hf:
        print(f"   export HF_HOME={os.path.join(cache_base, 'huggingface')}")
    print("\n2. Start the application:")
    print("   python -m ollama_guardrails server")
    print("   # or")
    print("   ollama-guardrails server")
    print("\nThe application will now use cached models instead of downloading from the internet.")
    print()


if __name__ == "__main__":
    main()

