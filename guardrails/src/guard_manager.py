import logging
import os
import platform
import asyncio
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)
code_language = ['Python', 'C#', 'C++', 'C']

# Direct imports from llm-guard
try:
    from llm_guard.input_scanners import (
        BanSubstrings as InputBanSubstrings,
        PromptInjection,
        Toxicity as InputToxicity,
        Secrets,
        Code as InputCode,
        TokenLimit,
        Anonymize,
    )
    from llm_guard.output_scanners import (
        BanSubstrings as OutputBanSubstrings,
        Toxicity as OutputToxicity,
        MaliciousURLs,
        NoRefusal,
        Code as OutputCode,
    )
    from llm_guard.vault import Vault
    from llm_guard import scan_prompt, scan_output
    
    # Import model configurations for local model support (optional - may not exist in all versions)
    # Use same models for both input and output scanners
    DEBERTA_AI4PRIVACY_v2_CONF = None
    CODE_MODEL = None
    PROMPT_INJECTION_MODEL = None
    TOXICITY_MODEL = None
    
    try:
        from llm_guard.input_scanners.anonymize_helpers import DEBERTA_AI4PRIVACY_v2_CONF
    except (ImportError, AttributeError):
        pass
    
    try:
        from llm_guard.input_scanners.code import DEFAULT_MODEL as CODE_MODEL
    except (ImportError, AttributeError):
        pass
    
    try:
        from llm_guard.input_scanners.prompt_injection import V2_MODEL as PROMPT_INJECTION_MODEL
    except (ImportError, AttributeError):
        pass
    
    try:
        from llm_guard.input_scanners.toxicity import DEFAULT_MODEL as TOXICITY_MODEL
    except (ImportError, AttributeError):
        pass

    HAS_LLM_GUARD = True
    logger.info('llm-guard modules imported successfully')
    
except ImportError as e:
    logger.warning('Failed to import llm-guard modules; guard features will be disabled: %s', e)
    HAS_LLM_GUARD = False
    # Define placeholder classes if llm-guard is not available
    InputBanSubstrings = PromptInjection = InputToxicity = Secrets = None
    InputCode = TokenLimit = Anonymize = None
    OutputBanSubstrings = OutputToxicity = MaliciousURLs = NoRefusal = OutputCode = None
    Vault = None
    scan_prompt = None
    scan_output = None
    # Model configuration placeholders
    DEBERTA_AI4PRIVACY_v2_CONF = None
    CODE_MODEL = PROMPT_INJECTION_MODEL = TOXICITY_MODEL = None
 

class LLMGuardManager:
    def __init__(self, enable_input: bool = True, enable_output: bool = True, enable_anonymize: bool = True, lazy_init: bool = True):
        """
        Initialize LLM Guard Manager with input and output scanning capabilities.
        
        Each scanner is called independently with its own scan() method.
        No Guard() wrapper class is used.
        
        Args:
            enable_input: Enable input scanning (default: True)
            enable_output: Enable output scanning (default: True)
            enable_anonymize: Enable PII anonymization (default: True)
            lazy_init: If True, defer scanner initialization until first use (default: True)
        """
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.enable_anonymize = enable_anonymize and HAS_LLM_GUARD
        self.lazy_init = lazy_init
        self.scan_fail_fast = os.environ.get('LLM_GUARD_FAST_FAIL', 'true').lower() in ('1', 'true', 'yes', 'on')
        logger.info(f'Fast fail enabled: {self.scan_fail_fast}')
        # Lazy initialization flags
        self._initialized = False
        self._input_scanners_initialized = False
        self._output_scanners_initialized = False
        
        # Detect and configure compute device (lightweight)
        self.device = self._detect_device()
        logger.info(f'Using compute device: {self.device}')
        
        # Check if local models should be used
        self.use_local_models = self._check_local_models_config()
        
        self.input_scanners = []
        self.output_scanners = []
        self.vault = None
        
        if not HAS_LLM_GUARD:
            logger.warning('LLM Guard not installed; guard features disabled')
            return
        
        # Immediate initialization if not lazy
        if not lazy_init:
            self._initialize_all()
        else:
            logger.info('LLM Guard Manager created in lazy mode - scanners will initialize on first use')

    def _detect_device(self) -> str:
        """
        Detect the best available compute device for ML models.
        
        Supports:
        - CPU: Universal support for all platforms
        - MPS: Apple Silicon GPU acceleration (M1/M2/M3 chips)
        
        Note: CUDA/NVIDIA GPU support removed for simplicity. Use CPU or Apple Silicon MPS.
        
        Returns:
            Device string: 'cpu' or 'mps'
        """
        # Check for explicit device override
        device_override = os.environ.get('LLM_GUARD_DEVICE', '').lower()
        if device_override in ('cpu', 'mps'):
            logger.info(f'Device override: {device_override}')
            return device_override
        elif device_override:
            logger.warning(f'Invalid device override "{device_override}" - must be "cpu" or "mps"')
        
        system = platform.system()
        machine = platform.machine()
        cpu_count = os.cpu_count() or 1
        
        # Auto-detect Apple Silicon MPS
        if machine == 'arm64' and system == 'Darwin':
            try:
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    logger.info(f'Apple Silicon detected - Using MPS GPU acceleration (System: {system}, Machine: {machine}, Cores: {cpu_count})')
                    return 'mps'
                else:
                    logger.info(f'Apple Silicon detected but MPS not available - Using CPU (System: {system}, Machine: {machine}, Cores: {cpu_count})')
                    return 'cpu'
            except (ImportError, AttributeError):
                logger.info(f'Apple Silicon detected but torch not available - Using CPU (System: {system}, Machine: {machine}, Cores: {cpu_count})')
                return 'cpu'
        
        # Default to CPU for all other platforms
        logger.info(f'Using CPU for ML inference - System: {system}, Machine: {machine}, Cores: {cpu_count}')
        return 'cpu'
    
    def _check_local_models_config(self) -> bool:
        """Check if local models should be used based on environment variables."""
        use_local = os.environ.get('LLM_GUARD_USE_LOCAL_MODELS', '').lower() in ('1', 'true', 'yes', 'on')
        if use_local:
            logger.info('Local models enabled via LLM_GUARD_USE_LOCAL_MODELS environment variable')
        return use_local
    
    def _initialize_all(self):
        """Initialize all scanners (used when lazy_init is False)."""
        if self._initialized:
            return
        
        # Configure local models if enabled
        if self.use_local_models:
            self._configure_local_models()
        
        # Initialize vault for anonymization
        if self.enable_anonymize:
            try:
                self.vault = Vault()
                logger.info('Vault initialized for anonymization')
            except Exception as e:
                logger.exception('Failed to initialize Vault: %s', e)
                self.enable_anonymize = False
        
        if self.enable_input:
            self._init_input_scanners()
        if self.enable_output:
            self._init_output_scanners()
        
        self._initialized = True
        logger.info('LLM Guard Manager fully initialized')
    
    def _ensure_input_scanners_initialized(self):
        """Ensure input scanners are initialized (lazy loading)."""
        if self._input_scanners_initialized:
            return
        
        if not self.enable_input or not HAS_LLM_GUARD:
            return
        
        logger.info('Lazy initializing input scanners...')
        
        # Configure local models if needed
        if self.use_local_models and not self._initialized:
            self._configure_local_models()
        
        # Initialize vault if needed for anonymization
        if self.enable_anonymize and self.vault is None:
            try:
                self.vault = Vault()
                logger.info('Vault initialized for anonymization')
            except Exception as e:
                logger.exception('Failed to initialize Vault: %s', e)
                self.enable_anonymize = False
        
        self._init_input_scanners()
        self._input_scanners_initialized = True
        logger.info('Input scanners initialized')
    
    def _ensure_output_scanners_initialized(self):
        """Ensure output scanners are initialized (lazy loading)."""
        if self._output_scanners_initialized:
            return
        
        if not self.enable_output or not HAS_LLM_GUARD:
            return
        
        logger.info('Lazy initializing output scanners...')
        
        # Configure local models if needed
        if self.use_local_models and not self._initialized:
            self._configure_local_models()
        
        self._init_output_scanners()
        self._output_scanners_initialized = True
        logger.info('Output scanners initialized')

    def _configure_local_models(self):
        """Configure model paths and settings for local model usage with device optimization."""
        if not HAS_LLM_GUARD:
            return
            
        try:
            # Get base path for local models
            models_base_path = os.environ.get('LLM_GUARD_MODELS_PATH', './models')
            
            device_name = 'MPS (Apple Silicon GPU)' if self.device == 'mps' else 'CPU'
            logger.info(f'Configuring models for {device_name} inference')
            
            # Configure Prompt Injection model
            if PROMPT_INJECTION_MODEL:
                PROMPT_INJECTION_MODEL.kwargs["local_files_only"] = True
                PROMPT_INJECTION_MODEL.path = os.path.join(models_base_path, "deberta-v3-base-prompt-injection-v2")
                logger.info(f'Configured PromptInjection model path: {PROMPT_INJECTION_MODEL.path}')
            
            # Configure Anonymize model
            if DEBERTA_AI4PRIVACY_v2_CONF and "DEFAULT_MODEL" in DEBERTA_AI4PRIVACY_v2_CONF:
                DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].path = os.path.join(models_base_path, "deberta-v3-base_finetuned_ai4privacy_v2")
                DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].kwargs["local_files_only"] = True
                
                logger.info(f'Configured Anonymize model path: {DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].path}')
            
            # Configure Toxicity model (used for both input and output)
            if TOXICITY_MODEL:
                TOXICITY_MODEL.path = os.path.join(models_base_path, "unbiased-toxic-roberta")
                TOXICITY_MODEL.kwargs["local_files_only"] = True
                logger.info(f'Configured Toxicity model path: {TOXICITY_MODEL.path}')
            
            # Configure Code model (used for both input and output)
            if CODE_MODEL:
                CODE_MODEL.path = os.path.join(models_base_path, "programming-language-identification")
                CODE_MODEL.kwargs["local_files_only"] = True
                logger.info(f'Configured Code model path: {CODE_MODEL.path}')
            
            logger.info(f'Local model configuration completed for device: {self.device}')
            
        except Exception as e:
            logger.exception('Failed to configure local models: %s', e)
            self.use_local_models = False

    def _init_input_scanners(self):
        """
        Initialize input scanners for use with scan_prompt function.
        Uses the official scan_prompt method from llm-guard library.
        """
        try:
            self.input_scanners = []
            
            # BanSubstrings scanner
            self.input_scanners.append(
                InputBanSubstrings(["malicious", "dangerous"])
            )
            
            # PromptInjection scanner with local model support
            self.input_scanners.append(
                PromptInjection(model=PROMPT_INJECTION_MODEL if self.use_local_models else None)
            )
            
            # Toxicity scanner with local model support
            self.input_scanners.append(
                InputToxicity(
                    threshold=0.5,
                    model=TOXICITY_MODEL if self.use_local_models else None
                )
            )
            
            # Secrets scanner
            self.input_scanners.append(Secrets())
            
            # Code scanner with local model support
            self.input_scanners.append(
                InputCode(
                    languages=code_language,
                    is_blocked=True,
                    model=CODE_MODEL if self.use_local_models else None
                )
            )
            
            # TokenLimit scanner
            self.input_scanners.append(TokenLimit(limit=4000))
            
            # Add Anonymize scanner if vault is available
            if self.enable_anonymize and self.vault:
                try:
                    # Use local model configuration if enabled
                    recognizer_conf = DEBERTA_AI4PRIVACY_v2_CONF if self.use_local_models else None
                    
                    anonymize_scanner = Anonymize(
                        self.vault,
                        preamble="Insert before prompt",
                        allowed_names=["John Doe"],
                        hidden_names=["Test LLC"],
                        language="en",
                        recognizer_conf=recognizer_conf
                    )
                    self.input_scanners.append(anonymize_scanner)
                    logger.info('Anonymize scanner added to input scanners')
                except Exception as e:
                    logger.warning('Failed to add Anonymize scanner: %s', e)
            
            logger.info('Input scanners initialized: %d scanners ready for scan_prompt (local_models: %s)', 
                       len(self.input_scanners), self.use_local_models)
        except Exception as e:
            logger.exception('Failed to init input scanners: %s', e)
            self.input_scanners = []

    def _init_output_scanners(self):
        """Initialize output scanners for use with scan_output function."""
        try:
            # Create scanners as a simple list for use with scan_output function
            self.output_scanners = [
                OutputBanSubstrings(["malicious", "dangerous"]),
                OutputToxicity(
                    threshold=0.5,
                    model=TOXICITY_MODEL if self.use_local_models else None
                ),
                MaliciousURLs(),
                NoRefusal(),
                OutputCode(
                    languages=code_language,
                    is_blocked=True,
                    model=CODE_MODEL if self.use_local_models else None
                ),
            ]
            
            logger.info('Output scanners initialized: %d scanners ready for scan_output (local_models: %s)', 
                       len(self.output_scanners), self.use_local_models)
        except Exception as e:
            logger.exception('Failed to init output scanners: %s', e)
            self.output_scanners = []

    async def _run_input_scanners(self, prompt: str) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all input scanners on the prompt using scan_prompt function.
        
        Returns (sanitized_text, is_valid, scan_results)
        """
        if not self.input_scanners or not scan_prompt:
            return prompt, True, {}
        
        try:
            # Use scan_prompt with input scanners in a thread (llm-guard best practice)
            sanitized_prompt, results_valid, results_score = await asyncio.to_thread(
                scan_prompt,
                self.input_scanners,
                prompt,
                self.scan_fail_fast
            )
            
            # Convert results to expected format
            scan_results = {}
            for scanner_name, is_valid in results_valid.items():
                risk_score = results_score.get(scanner_name, 0.0)
                scan_results[scanner_name] = {
                    'passed': is_valid,
                    'risk_score': risk_score,
                    'sanitized': sanitized_prompt != prompt
                }
                
                if not is_valid:
                    logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score}')
            
            all_valid = all(results_valid.values())
            return sanitized_prompt, all_valid, scan_results
            
        except Exception as e:
            logger.exception('Error running input scanners with scan_prompt: %s', e)
            return prompt, False, {'error': str(e)}

    async def _run_output_scanners(self, text: str, prompt: str = "") -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all output scanners on the text using scan_output function.
        
        Uses the official scan_output method from llm-guard library (similar to scan_prompt).
        Output scanners require both prompt and output text.
        Returns (sanitized_text, is_valid, scan_results)
        """
        if not self.output_scanners or not scan_output:
            return text, True, {}
        
        try:
            # Use scan_output with output scanners in a thread (llm-guard best practice)
            # Signature: scan_output(scanners, prompt, output, fail_fast)
            sanitized_output, results_valid, results_score = await asyncio.to_thread(
                scan_output,
                self.output_scanners,
                prompt,
                text,
                self.scan_fail_fast
            )
            
            # Convert results to expected format
            scan_results = {}
            for scanner_name, is_valid in results_valid.items():
                risk_score = results_score.get(scanner_name, 0.0)
                scan_results[scanner_name] = {
                    'passed': is_valid,
                    'risk_score': risk_score,
                    'sanitized': sanitized_output != text
                }
                
                if not is_valid:
                    logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score}')
            
            all_valid = all(results_valid.values())
            return sanitized_output, all_valid, scan_results
            
        except Exception as e:
            logger.exception('Error running output scanners with scan_output: %s', e)
            return text, False, {'error': str(e)}

    async def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
        """
        Scan input prompt using all input scanners.
        
        Returns:
            {
                'allowed': bool - True if all scanners passed,
                'sanitized': str - Sanitized prompt,
                'scanners': dict - Per-scanner results with pass/fail and risk scores,
                'error': str - Error message if block_on_error is True and scan failed
            }
        """
        # Lazy initialization
        if self.lazy_init:
            self._ensure_input_scanners_initialized()
        
        if not self.enable_input or not self.input_scanners:
            return {
                "allowed": True,
                "sanitized": prompt,
                "scanners": {},
                "scanner_count": 0
            }
        
        try:
            sanitized_prompt, is_valid, scan_results = await self._run_input_scanners(prompt)
            
            return {
                "allowed": is_valid,
                "sanitized": sanitized_prompt,
                "scanners": scan_results,
                "scanner_count": len(self.input_scanners)
            }
        except Exception as e:
            logger.exception('Input scan error: %s', e)
            if block_on_error:
                return {
                    "allowed": False,
                    "sanitized": prompt,
                    "error": str(e),
                    "scanners": {}
                }
            return {
                "allowed": True,
                "sanitized": prompt,
                "error": str(e),
                "scanners": {}
            }

    async def scan_output(self, text: str, prompt: str = "", block_on_error: bool = False) -> Dict[str, Any]:
        """
        Scan output text using all output scanners.
        
        Args:
            text: The output text to scan
            prompt: The original input prompt (optional, but recommended for context)
            block_on_error: Whether to block on scanner errors
        
        Returns:
            {
                'allowed': bool - True if all scanners passed,
                'sanitized': str - Sanitized output text,
                'scanners': dict - Per-scanner results with pass/fail and risk scores,
                'error': str - Error message if block_on_error is True and scan failed
            }
        """
        # Lazy initialization
        if self.lazy_init:
            self._ensure_output_scanners_initialized()
        
        if not self.enable_output or not self.output_scanners:
            return {
                "allowed": True,
                "sanitized": text,
                "scanners": {},
                "scanner_count": 0
            }
        
        try:
            sanitized_text, is_valid, scan_results = await self._run_output_scanners(text, prompt)
            
            return {
                "allowed": is_valid,
                "sanitized": sanitized_text,
                "scanners": scan_results,
                "scanner_count": len(self.output_scanners)
            }
        except Exception as e:
            logger.exception('Output scan error: %s', e)
            if block_on_error:
                return {
                    "allowed": False,
                    "sanitized": text,
                    "error": str(e),
                    "scanners": {}
                }
            return {
                "allowed": True,
                "sanitized": text,
                "error": str(e),
                "scanners": {}
            }
