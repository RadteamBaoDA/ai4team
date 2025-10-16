#!/usr/bin/env python3
"""
Example client for Ollama Guard Proxy

Demonstrates how to interact with the secured Ollama proxy with LLM Guard.

Usage:
    python client_example.py
    python client_example.py --prompt "Your custom prompt here"
    python client_example.py --stream  # For streaming responses
"""

import requests
import json
import argparse
import sys
from typing import Optional, Generator

# Configuration
DEFAULT_PROXY_URL = "http://localhost:8080"
DEFAULT_MODEL = "mistral"
DEFAULT_PROMPT = "What is artificial intelligence?"


class OllamaGuardClient:
    """Client for interacting with Ollama Guard Proxy."""
    
    def __init__(self, base_url: str = DEFAULT_PROXY_URL, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def health_check(self) -> dict:
        """Check proxy health status."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unreachable"}
    
    def get_config(self) -> dict:
        """Get proxy configuration."""
        try:
            response = self.session.get(
                f"{self.base_url}/config",
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        stream: bool = False,
        **kwargs
    ) -> dict:
        """
        Generate a response using the Ollama model.
        
        Args:
            prompt: The input prompt
            model: Model name to use
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to Ollama
        
        Returns:
            Generated response or streamed chunks
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/generate",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_streaming(response)
            else:
                return response.json()
        
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}
    
    def chat_completion(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
        stream: bool = False,
        **kwargs
    ) -> dict:
        """
        Get chat completion from the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            stream: Whether to stream the response
            **kwargs: Additional parameters
        
        Returns:
            Chat completion response
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_streaming(response)
            else:
                return response.json()
        
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}
    
    def _handle_streaming(self, response):
        """Handle streaming response."""
        for line in response.iter_lines():
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main():
    parser = argparse.ArgumentParser(
        description="Ollama Guard Proxy Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation
  python client_example.py --prompt "Explain machine learning"
  
  # Streaming response
  python client_example.py --prompt "Tell me a story" --stream
  
  # Chat completion
  python client_example.py --chat "Hello, how are you?"
  
  # Check proxy health
  python client_example.py --health
  
  # View configuration
  python client_example.py --config
  
  # Custom model
  python client_example.py --model llama2 --prompt "Your prompt"
        """
    )
    
    parser.add_argument(
        "--proxy",
        default=DEFAULT_PROXY_URL,
        help=f"Proxy URL (default: {DEFAULT_PROXY_URL})"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--prompt",
        help="Input prompt for generation"
    )
    parser.add_argument(
        "--chat",
        help="User message for chat completion"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the response"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check proxy health"
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Get proxy configuration"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    client = OllamaGuardClient(args.proxy, timeout=args.timeout)
    
    # Health check
    if args.health:
        print("Checking proxy health...")
        health = client.health_check()
        print(json.dumps(health, indent=2))
        return
    
    # Get configuration
    if args.config:
        print("Retrieving proxy configuration...")
        config = client.get_config()
        print(json.dumps(config, indent=2))
        return
    
    # Generate response
    if args.prompt:
        print(f"\n{'='*60}")
        print(f"Prompt: {args.prompt}")
        print(f"Model: {args.model}")
        print(f"{'='*60}\n")
        
        if args.stream:
            print("Response (streaming):")
            for chunk in client.generate(args.prompt, model=args.model, stream=True):
                if "response" in chunk:
                    print(chunk["response"], end="", flush=True)
                elif "error" in chunk:
                    print(f"\nError: {chunk['error']}")
                    break
            print("\n")
        else:
            response = client.generate(args.prompt, model=args.model, stream=False)
            if "response" in response:
                print(f"Response:\n{response['response']}\n")
            elif "error" in response:
                print(f"Error: {json.dumps(response, indent=2)}")
            else:
                print(json.dumps(response, indent=2))
        
        return
    
    # Chat completion
    if args.chat:
        print(f"\n{'='*60}")
        print(f"User: {args.chat}")
        print(f"Model: {args.model}")
        print(f"{'='*60}\n")
        
        messages = [{"role": "user", "content": args.chat}]
        
        if args.stream:
            print("Response (streaming):")
            for chunk in client.chat_completion(messages, model=args.model, stream=True):
                if "choices" in chunk and chunk["choices"]:
                    if "delta" in chunk["choices"][0]:
                        if "content" in chunk["choices"][0]["delta"]:
                            print(chunk["choices"][0]["delta"]["content"], end="", flush=True)
                elif "error" in chunk:
                    print(f"\nError: {chunk['error']}")
                    break
            print("\n")
        else:
            response = client.chat_completion(messages, model=args.model, stream=False)
            if "choices" in response and response["choices"]:
                print(f"Assistant: {response['choices'][0]['message']['content']}\n")
            elif "error" in response:
                print(f"Error: {json.dumps(response, indent=2)}")
            else:
                print(json.dumps(response, indent=2))
        
        return
    
    # Default: show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
