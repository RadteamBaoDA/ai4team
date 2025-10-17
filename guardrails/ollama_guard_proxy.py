"""
Ollama Proxy with LLM Guard Integration

This proxy applies LLM Guard scanners to both input prompts and model outputs.

Features:
- Input scanning (prompt injection, toxicity, secrets, etc.)
- Output scanning (toxicity, bias, malicious URLs, code generation, etc.)
- Streaming response support
- Comprehensive logging and metrics
- Configuration via YAML or environment variables
- IP whitelist support (restrict access to nginx only)

Usage:
    pip install fastapi uvicorn requests pydantic pyyaml llm-guard
    python ollama_guard_proxy.py

Or with Uvicorn directly:
    uvicorn ollama_guard_proxy:app --host 0.0.0.0 --port 8080

IP Whitelist (Nginx Only):
    # Via environment variable (comma-separated)
    export NGINX_WHITELIST="127.0.0.1,192.168.1.10,10.0.0.5"
    
    # Via YAML configuration file
    # nginx_whitelist:
    #   - "127.0.0.1"
    #   - "192.168.1.10"
    #   - "10.0.0.5"
"""

import os
import json
import logging
import re
import ipaddress
from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import requests

try:
    from llm_guard.input_scanners import (
        BanSubstrings,
        PromptInjection,
        Toxicity,
        Secrets,
        Code,
        TokenLimit,
    )
    from llm_guard.output_scanners import (
        BanSubstrings as OutputBanSubstrings,
        Toxicity as OutputToxicity,
        MaliciousURLs,
        NoRefusal,
        NoCode,
    )
    from llm_guard.guard import Guard
    HAS_LLM_GUARD = True
except ImportError:
    HAS_LLM_GUARD = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IPWhitelist:
    """Manage IP whitelist for restricting access (e.g., nginx only)."""
    
    def __init__(self, whitelist: Optional[List[str]] = None):
        """
        Initialize IP whitelist.
        
        Args:
            whitelist: List of allowed IP addresses or CIDR ranges
                      Examples: ["127.0.0.1", "192.168.1.0/24", "10.0.0.5"]
        """
        self.enabled = False
        self.whitelist: List[ipaddress.IPv4Network | ipaddress.IPv4Address] = []
        
        if whitelist:
            self.enabled = len(whitelist) > 0
            for ip_str in whitelist:
                try:
                    # Try to parse as CIDR network first
                    if '/' in ip_str:
                        self.whitelist.append(ipaddress.IPv4Network(ip_str))
                        logger.info(f"Added CIDR network to whitelist: {ip_str}")
                    else:
                        # Parse as individual IP
                        self.whitelist.append(ipaddress.IPv4Address(ip_str))
                        logger.info(f"Added IP to whitelist: {ip_str}")
                except ValueError as e:
                    logger.warning(f"Invalid IP/CIDR '{ip_str}': {e}")
    
    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if client IP is in whitelist.
        
        Args:
            client_ip: Client IP address to check
            
        Returns:
            True if IP is whitelisted or whitelist is disabled, False otherwise
        """
        if not self.enabled:
            return True
        
        try:
            ip = ipaddress.IPv4Address(client_ip)
            
            # Check against each whitelisted entry
            for allowed in self.whitelist:
                if isinstance(allowed, ipaddress.IPv4Network):
                    # Check if IP is in network
                    if ip in allowed:
                        return True
                else:
                    # Check if IP matches exactly
                    if ip == allowed:
                        return True
            
            return False
        
        except ValueError:
            logger.warning(f"Invalid client IP format: {client_ip}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get whitelist statistics."""
        return {
            "enabled": self.enabled,
            "count": len(self.whitelist),
            "whitelist": [str(ip) for ip in self.whitelist]
        }


class LanguageDetector:
    """Detect language from text and provide localized error messages."""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'zh': {
            'patterns': [r'[\u4e00-\u9fff]'],  # Chinese characters
            'name': 'Chinese'
        },
        'vi': {
            'patterns': [r'[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0]'],  # Vietnamese diacritics
            'name': 'Vietnamese'
        },
        'ja': {
            'patterns': [r'[\u3040-\u309f\u30a0-\u30ff]'],  # Japanese hiragana/katakana
            'name': 'Japanese'
        },
        'ko': {
            'patterns': [r'[\uac00-\ud7af]'],  # Korean hangul
            'name': 'Korean'
        },
        'ru': {
            'patterns': [r'[\u0400-\u04ff]'],  # Cyrillic/Russian
            'name': 'Russian'
        },
        'ar': {
            'patterns': [r'[\u0600-\u06ff]'],  # Arabic
            'name': 'Arabic'
        },
    }
    
    # Error messages by language
    ERROR_MESSAGES = {
        'zh': {
            'prompt_blocked': '您的输入被安全扫描器阻止。原因: {reason}',
            'prompt_blocked_detail': '输入包含不安全内容，无法处理。',
            'response_blocked': '模型的输出被安全扫描器阻止。',
            'server_error': '服务器内部错误。',
            'upstream_error': '上游服务错误。',
        },
        'vi': {
            'prompt_blocked': 'Đầu vào của bạn bị chặn bởi bộ quét bảo mật. Lý do: {reason}',
            'prompt_blocked_detail': 'Đầu vào chứa nội dung không an toàn, không thể xử lý.',
            'response_blocked': 'Đầu ra của mô hình bị chặn bởi bộ quét bảo mật.',
            'server_error': 'Lỗi máy chủ nội bộ.',
            'upstream_error': 'Lỗi dịch vụ hạ nguồn.',
        },
        'ja': {
            'prompt_blocked': 'あなたの入力はセキュリティスキャナーによってブロックされました。理由: {reason}',
            'prompt_blocked_detail': '入力に安全でないコンテンツが含まれているため、処理できません。',
            'response_blocked': 'モデルの出力はセキュリティスキャナーによってブロックされました。',
            'server_error': 'サーバー内部エラー。',
            'upstream_error': 'アップストリームサービスエラー。',
        },
        'ko': {
            'prompt_blocked': '입력이 보안 스캐너에 의해 차단되었습니다. 이유: {reason}',
            'prompt_blocked_detail': '입력에 안전하지 않은 내용이 포함되어 있어 처리할 수 없습니다.',
            'response_blocked': '모델 출력이 보안 스캐너에 의해 차단되었습니다.',
            'server_error': '서버 내부 오류입니다.',
            'upstream_error': '업스트림 서비스 오류입니다.',
        },
        'ru': {
            'prompt_blocked': 'Ваши входные данные заблокированы сканером безопасности. Причина: {reason}',
            'prompt_blocked_detail': 'Входные данные содержат небезопасное содержание и не могут быть обработаны.',
            'response_blocked': 'Вывод модели заблокирован сканером безопасности.',
            'server_error': 'Ошибка внутреннего сервера.',
            'upstream_error': 'Ошибка восходящего сервиса.',
        },
        'ar': {
            'prompt_blocked': 'تم حظر مدخلاتك بواسطة ماسح الأمان. السبب: {reason}',
            'prompt_blocked_detail': 'يحتوي الإدخال على محتوى غير آمن ولا يمكن معالجته.',
            'response_blocked': 'تم حظر مخرجات النموذج بواسطة ماسح الأمان.',
            'server_error': 'خطأ في الخادم الداخلي.',
            'upstream_error': 'خطأ في الخدمة الأصلية.',
        },
        'en': {
            'prompt_blocked': 'Your input was blocked by the security scanner. Reason: {reason}',
            'prompt_blocked_detail': 'Input contains unsafe content and cannot be processed.',
            'response_blocked': 'Model output was blocked by the security scanner.',
            'server_error': 'Internal server error.',
            'upstream_error': 'Upstream service error.',
        }
    }
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language from text. Returns language code or 'en' as default."""
        if not text:
            return 'en'
        
        for lang_code, lang_info in LanguageDetector.LANGUAGE_PATTERNS.items():
            for pattern in lang_info['patterns']:
                if re.search(pattern, text):
                    logger.info(f"Detected language: {lang_info['name']}")
                    return lang_code
        
        # Check for common English words
        if re.search(r'\b(the|a|an|and|or|is|are|was|were|be|have|has|had)\b', text, re.IGNORECASE):
            return 'en'
        
        return 'en'  # Default to English
    
    @staticmethod
    def get_error_message(message_key: str, language: str, reason: str = '') -> str:
        """Get localized error message."""
        messages = LanguageDetector.ERROR_MESSAGES.get(language, LanguageDetector.ERROR_MESSAGES['en'])
        message = messages.get(message_key, '')
        
        if reason and '{reason}' in message:
            message = message.format(reason=reason)
        
        return message


class Config:
    """Configuration manager for the proxy."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = {}
        self.load_config(config_file)
        
    def load_config(self, config_file: Optional[str] = None):
        """Load configuration from YAML file or environment variables."""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}
        
        # Override with environment variables
        self.config['ollama_url'] = os.environ.get(
            'OLLAMA_URL',
            self.config.get('ollama_url', 'http://127.0.0.1:11434')
        )
        self.config['ollama_path'] = os.environ.get(
            'OLLAMA_PATH',
            self.config.get('ollama_path', '/api/generate')
        )
        self.config['proxy_port'] = int(os.environ.get(
            'PROXY_PORT',
            self.config.get('proxy_port', 8080)
        ))
        self.config['proxy_host'] = os.environ.get(
            'PROXY_HOST',
            self.config.get('proxy_host', '0.0.0.0')
        )
        
        # LLM Guard Settings
        self.config['enable_input_guard'] = os.environ.get(
            'ENABLE_INPUT_GUARD',
            self.config.get('enable_input_guard', True)
        )
        self.config['enable_output_guard'] = os.environ.get(
            'ENABLE_OUTPUT_GUARD',
            self.config.get('enable_output_guard', True)
        )
        self.config['block_on_guard_error'] = os.environ.get(
            'BLOCK_ON_GUARD_ERROR',
            self.config.get('block_on_guard_error', False)
        )
        
        # IP Whitelist Configuration (Nginx only)
        nginx_whitelist_env = os.environ.get('NGINX_WHITELIST', '')
        if nginx_whitelist_env:
            # Parse comma-separated IPs from environment variable
            self.config['nginx_whitelist'] = [ip.strip() for ip in nginx_whitelist_env.split(',') if ip.strip()]
        elif 'nginx_whitelist' not in self.config:
            self.config['nginx_whitelist'] = []
        
        logger.info(f"Configuration loaded: {self.config}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


class LLMGuardManager:
    """Manage LLM Guard initialization and scanning."""
    
    def __init__(self, enable_input: bool = True, enable_output: bool = True):
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.input_guard = None
        self.output_guard = None
        
        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Install with: pip install llm-guard")
            return
        
        try:
            if self.enable_input:
                self._init_input_guard()
            if self.enable_output:
                self._init_output_guard()
        except Exception as e:
            logger.error(f"Failed to initialize LLM Guard: {e}")
    
    def _init_input_guard(self):
        """Initialize input scanners."""
        try:
            input_scanners = [
                BanSubstrings(["malicious", "dangerous"]),
                PromptInjection(),
                Toxicity(threshold=0.5),
                Secrets(),
                TokenLimit(limit=4000),
            ]
            self.input_guard = Guard(input_scanners=input_scanners)
            logger.info("Input guard initialized with scanners")
        except Exception as e:
            logger.error(f"Failed to initialize input guard: {e}")
            self.input_guard = None
    
    def _init_output_guard(self):
        """Initialize output scanners."""
        try:
            output_scanners = [
                OutputBanSubstrings(["malicious", "dangerous"]),
                OutputToxicity(threshold=0.5),
                MaliciousURLs(),
                NoRefusal(),
                NoCode(),
            ]
            self.output_guard = Guard(output_scanners=output_scanners)
            logger.info("Output guard initialized with scanners")
        except Exception as e:
            logger.error(f"Failed to initialize output guard: {e}")
            self.output_guard = None
    
    def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
        """Scan input prompt."""
        if not self.enable_input or self.input_guard is None:
            return {"allowed": True, "scanners": {}}
        
        try:
            result = self.input_guard.validate(prompt)
            return {
                "allowed": result.validation_passed,
                "scanners": {
                    scanner.name: {
                        "passed": scanner.passed,
                        "reason": scanner.reason,
                    }
                    for scanner in result.scanners
                },
            }
        except Exception as e:
            logger.error(f"Error during input scanning: {e}")
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}
    
    def scan_output(self, text: str, block_on_error: bool = False) -> Dict[str, Any]:
        """Scan model output."""
        if not self.enable_output or self.output_guard is None:
            return {"allowed": True, "scanners": {}}
        
        try:
            result = self.output_guard.validate(text)
            return {
                "allowed": result.validation_passed,
                "scanners": {
                    scanner.name: {
                        "passed": scanner.passed,
                        "reason": scanner.reason,
                    }
                    for scanner in result.scanners
                },
            }
        except Exception as e:
            logger.error(f"Error during output scanning: {e}")
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}


# Initialize app and components
config = Config(os.environ.get('CONFIG_FILE'))
guard_manager = LLMGuardManager(
    enable_input=config.get('enable_input_guard', True),
    enable_output=config.get('enable_output_guard', True),
)

# Initialize IP whitelist (nginx only)
ip_whitelist = IPWhitelist(config.get('nginx_whitelist', []))

app = FastAPI(
    title="Ollama Proxy with LLM Guard",
    description="Secure proxy for Ollama with LLM Guard integration",
)


def extract_client_ip(request: Request) -> str:
    """Extract client IP from request, accounting for proxies."""
    # Check X-Forwarded-For header (set by nginx)
    if 'x-forwarded-for' in request.headers:
        return request.headers['x-forwarded-for'].split(',')[0].strip()
    
    # Check X-Real-IP header (alternative nginx header)
    if 'x-real-ip' in request.headers:
        return request.headers['x-real-ip'].strip()
    
    # Fallback to direct connection
    return request.client.host if request.client else '0.0.0.0'


def extract_text_from_payload(payload: Dict[str, Any]) -> str:
    """Extract text from Ollama request payload."""
    if isinstance(payload, dict):
        if 'prompt' in payload:
            return payload['prompt']
        if 'input' in payload:
            return payload['input']
    return str(payload)


def extract_text_from_response(data: Any) -> str:
    """Extract text from Ollama response."""
    if isinstance(data, dict):
        if 'response' in data:
            return data['response']
        if 'text' in data:
            return data['text']
        if 'output' in data:
            return data['output']
        # Combine all string values
        text = ' '.join([str(v) for v in data.values() if isinstance(v, str)])
        if text:
            return text
    return str(data)


@app.middleware("http")
async def check_ip_whitelist(request: Request, call_next):
    """Middleware to check IP whitelist (nginx only)."""
    client_ip = extract_client_ip(request)
    
    # Check if client IP is whitelisted
    if not ip_whitelist.is_allowed(client_ip):
        logger.warning(f"Rejected request from non-whitelisted IP: {client_ip} {request.method} {request.url.path}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "access_denied",
                "message": "Access denied. Only requests from whitelisted IPs are allowed.",
                "client_ip": client_ip
            }
        )
    
    logger.debug(f"IP whitelist check passed for {client_ip}")
    response = await call_next(request)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests."""
    client_ip = extract_client_ip(request)
    logger.info(f"Request from {client_ip}: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


@app.post("/api/generate")
async def proxy_generate(request: Request, background_tasks: BackgroundTasks):
    """Proxy endpoint for Ollama /api/generate."""
    # Parse request payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request JSON: {e}")
        raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(e)})
    
    # Extract prompt for scanning
    prompt = extract_text_from_payload(payload)
    
    # Detect language from prompt
    detected_lang = LanguageDetector.detect_language(prompt)
    
    # Scan input
    if config.get('enable_input_guard', True):
        input_result = guard_manager.scan_input(
            prompt,
            block_on_error=config.get('block_on_guard_error', False)
        )
        if not input_result['allowed']:
            logger.warning(f"Input blocked: {input_result}")
            
            # Get scanner reason
            reason = ', '.join([
                f"{scanner_name}: {info.get('reason', 'Unknown')}"
                for scanner_name, info in input_result.get('scanners', {}).items()
                if not info.get('passed', True)
            ])
            
            # Get localized error message
            error_message = LanguageDetector.get_error_message(
                'prompt_blocked',
                detected_lang,
                reason
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "prompt_blocked",
                    "message": error_message,
                    "language": detected_lang,
                    "details": input_result
                }
            )
        logger.info(f"Input passed guards: {input_result['scanners']}")
    
    # Forward to Ollama
    ollama_url = config.get('ollama_url')
    ollama_path = config.get('ollama_path')
    url = f"{ollama_url.rstrip('/')}{ollama_path}"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=300)
    except requests.RequestException as e:
        logger.error(f"Upstream error: {e}")
        error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_error", "message": error_message, "details": str(e)}
        )
    
    if resp.status_code != 200:
        try:
            error_data = resp.json()
        except:
            error_data = {"error": resp.text}
        logger.error(f"Upstream returned {resp.status_code}: {error_data}")
        raise HTTPException(status_code=resp.status_code, detail=error_data)
    
    # Process streaming response
    if 'stream' in payload and payload['stream']:
        return StreamingResponse(
            stream_response_with_guard(resp, detected_lang),
            media_type="application/x-ndjson",
        )
    else:
        # Non-streaming response
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"Failed to parse upstream response: {e}")
            error_message = LanguageDetector.get_error_message('server_error', detected_lang)
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})
        
        # Scan output
        if config.get('enable_output_guard', True):
            output_text = extract_text_from_response(data)
            output_result = guard_manager.scan_output(
                output_text,
                block_on_error=config.get('block_on_guard_error', False)
            )
            if not output_result['allowed']:
                logger.warning(f"Output blocked: {output_result}")
                
                # Get localized error message
                error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "response_blocked",
                        "message": error_message,
                        "language": detected_lang,
                        "details": output_result
                    }
                )
            logger.info(f"Output passed guards: {output_result['scanners']}")
        
        return JSONResponse(status_code=200, content=data)


async def stream_response_with_guard(response, detected_lang: str = 'en'):
    """Stream response with output scanning."""
    accumulated_text = ""
    
    try:
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                yield line + b'\n'
                continue
            
            # Accumulate text from streaming responses
            if 'response' in data:
                accumulated_text += data['response']
            
            # Scan accumulated text periodically (every 500 chars)
            if len(accumulated_text) > 500 and config.get('enable_output_guard', True):
                output_result = guard_manager.scan_output(accumulated_text)
                if not output_result['allowed']:
                    logger.warning(f"Streaming output blocked: {output_result}")
                    
                    # Get localized error message
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    
                    # Send error as last chunk
                    error_chunk = {
                        "error": "response_blocked",
                        "message": error_message,
                        "language": detected_lang,
                        "reason": output_result.get('scanners', {})
                    }
                    yield (json.dumps(error_chunk) + '\n').encode()
                    break
                accumulated_text = ""  # Reset for next batch
            
            yield line + b'\n'
        
        # Final scan of any remaining text
        if accumulated_text and config.get('enable_output_guard', True):
            output_result = guard_manager.scan_output(accumulated_text)
            if not output_result['allowed']:
                logger.warning(f"Final streaming output blocked: {output_result}")
    
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_message = LanguageDetector.get_error_message('server_error', detected_lang)
        yield (json.dumps({"error": str(e), "message": error_message}) + '\n').encode()


@app.post("/api/chat")
async def proxy_chat(request: Request):
    """Proxy endpoint for Ollama /api/chat."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    # Extract prompt from messages
    prompt = ""
    if 'messages' in payload and isinstance(payload['messages'], list):
        for msg in payload['messages']:
            if isinstance(msg, dict) and 'content' in msg:
                prompt += msg['content'] + "\n"
    
    # Detect language from prompt
    detected_lang = LanguageDetector.detect_language(prompt)
    
    # Scan input
    if config.get('enable_input_guard', True) and prompt:
        input_result = guard_manager.scan_input(
            prompt,
            block_on_error=config.get('block_on_guard_error', False)
        )
        if not input_result['allowed']:
            logger.warning(f"Input blocked: {input_result}")
            
            # Get scanner reason
            reason = ', '.join([
                f"{scanner_name}: {info.get('reason', 'Unknown')}"
                for scanner_name, info in input_result.get('scanners', {}).items()
                if not info.get('passed', True)
            ])
            
            # Get localized error message
            error_message = LanguageDetector.get_error_message(
                'prompt_blocked',
                detected_lang,
                reason
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "prompt_blocked",
                    "message": error_message,
                    "language": detected_lang,
                    "details": input_result
                }
            )
    
    # Forward to Ollama chat endpoint
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/chat"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=300)
    except requests.RequestException as e:
        logger.error(f"Upstream error: {e}")
        error_message = LanguageDetector.get_error_message('upstream_error', detected_lang)
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": error_message})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Handle streaming or non-streaming responses
    if 'stream' in payload and payload['stream']:
        return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="text/event-stream")
    else:
        try:
            data = resp.json()
        except:
            error_message = LanguageDetector.get_error_message('server_error', detected_lang)
            raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response", "message": error_message})
        
        # Scan output - Ollama chat uses 'message' field
        if config.get('enable_output_guard', True):
            output_text = ""
            if 'message' in data and isinstance(data['message'], dict):
                output_text = data['message'].get('content', '')
            
            if output_text:
                output_result = guard_manager.scan_output(output_text)
                if not output_result['allowed']:
                    logger.warning(f"Output blocked: {output_result}")
                    
                    # Get localized error message
                    error_message = LanguageDetector.get_error_message('response_blocked', detected_lang)
                    
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "response_blocked",
                            "message": error_message,
                            "language": detected_lang,
                            "details": output_result
                        }
                    )
        
        return JSONResponse(status_code=200, content=data)


@app.post("/api/pull")
async def proxy_pull(request: Request):
    """Proxy endpoint for Ollama model pull."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/pull"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream pull response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/push")
async def proxy_push(request: Request):
    """Proxy endpoint for Ollama model push."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/push"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream push response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.post("/api/create")
async def proxy_create(request: Request):
    """Proxy endpoint for Ollama model creation."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/create"
    
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=3600)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    # Stream create response
    return StreamingResponse(resp.iter_content(chunk_size=1024), media_type="application/x-ndjson")


@app.get("/api/tags")
async def proxy_tags():
    """Proxy endpoint for Ollama list models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/tags"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.post("/api/show")
async def proxy_show(request: Request):
    """Proxy endpoint for Ollama show model info."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/show"
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.delete("/api/delete")
async def proxy_delete(request: Request):
    """Proxy endpoint for Ollama delete model."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/delete"
    
    try:
        resp = requests.delete(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    return JSONResponse(status_code=200, content={})


@app.post("/api/copy")
async def proxy_copy(request: Request):
    """Proxy endpoint for Ollama copy model."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/copy"
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    return JSONResponse(status_code=200, content={})


@app.post("/api/embed")
async def proxy_embed(request: Request):
    """Proxy endpoint for Ollama generate embeddings."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/embed"
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/api/ps")
async def proxy_ps():
    """Proxy endpoint for Ollama list running models."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/ps"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/api/version")
async def proxy_version():
    """Proxy endpoint for Ollama version."""
    ollama_url = config.get('ollama_url')
    url = f"{ollama_url.rstrip('/')}/api/version"
    
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_error"})
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail={"error": "upstream_error"})
    
    try:
        data = resp.json()
    except:
        raise HTTPException(status_code=502, detail={"error": "invalid_upstream_response"})
    
    return JSONResponse(status_code=200, content=data)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "guards": {
            "input_guard": "enabled" if guard_manager.enable_input else "disabled",
            "output_guard": "enabled" if guard_manager.enable_output else "disabled",
        },
        "whitelist": ip_whitelist.get_stats()
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    safe_config = {k: v for k, v in config.config.items() if k not in ['secret_key']}
    # Don't expose actual whitelist IPs in config, only show if enabled
    safe_config['nginx_whitelist'] = ip_whitelist.get_stats()
    return safe_config


if __name__ == "__main__":
    host = config.get('proxy_host', '0.0.0.0')
    port = config.get('proxy_port', 8080)
    logger.info(f"Starting Ollama Guard Proxy on {host}:{port}")
    logger.info(f"Forwarding to Ollama at {config.get('ollama_url')}")
    uvicorn.run(app, host=host, port=port)
