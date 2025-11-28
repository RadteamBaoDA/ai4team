import logging
import os
import platform
import asyncio
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)
code_language = ['Python', 'C#', 'C++', 'C']

# Initialize tiktoken offline mode BEFORE importing llm-guard
# This must happen before any llm-guard imports to ensure tiktoken uses local cache
from ..utils.tiktoken_cache import setup_tiktoken_offline_mode
setup_tiktoken_offline_mode()

# Direct imports from llm-guard
try:
    from llm_guard.input_scanners import (
        BanSubstrings as InputBanSubstrings,
        PromptInjection,
        Toxicity as InputToxicity,
        Secrets,
        Code as InputCode,
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
    MALICIOUS_URLS_MODEL = None
    NO_REFUSAL_MODEL = None
    
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
    
    try:
        from llm_guard.output_scanners.malicious_urls import DEFAULT_MODEL as MALICIOUS_URLS_MODEL
    except (ImportError, AttributeError):
        pass
    try:
        from llm_guard.output_scanners.no_refusal import DEFAULT_MODEL as NO_REFUSAL_MODEL
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
    CODE_MODEL = PROMPT_INJECTION_MODEL = TOXICITY_MODEL = MALICIOUS_URLS_MODEL = NO_REFUSAL_MODEL = None
 

class LLMGuardManager:
    def __init__(
        self,
        enable_input: bool = True,
        enable_output: bool = True,
        enable_anonymize: bool = True,
        lazy_init: bool = True,
        enable_input_code_scanner: Optional[bool] = False,
        input_scanners_config: Optional[Dict[str, Any]] = None,
        output_scanners_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize LLM Guard Manager with input and output scanning capabilities.
        
        Each scanner is called independently with its own scan() method.
        No Guard() wrapper class is used.
        
        Args:
            enable_input: Enable input scanning (default: True)
            enable_output: Enable output scanning (default: True)
            enable_anonymize: Enable PII anonymization (default: True)
            lazy_init: If True, defer scanner initialization until first use (default: True)
            enable_input_code_scanner: Enable code scanner for input (default: False)
            input_scanners_config: Individual input scanner configurations from config.yaml
            output_scanners_config: Individual output scanner configurations from config.yaml
        """
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.enable_anonymize = enable_anonymize and HAS_LLM_GUARD
        self.lazy_init = lazy_init
        
        # Store scanner configurations for individual enable/disable control
        self.input_scanners_config = input_scanners_config or {}
        self.output_scanners_config = output_scanners_config or {}
        
        if enable_input_code_scanner is None:
            env_flag = os.environ.get('LLM_GUARD_ENABLE_INPUT_CODE_SCANNER')
            if env_flag is None:
                enable_input_code_scanner = True
            else:
                enable_input_code_scanner = env_flag.lower() in ('1', 'true', 'yes', 'on')
        self.enable_input_code_scanner = bool(enable_input_code_scanner) and HAS_LLM_GUARD
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
        self._token_encoder = None
        self._token_encoder_failed = False
        self._token_encoding_name = os.environ.get('LLM_GUARD_TOKEN_ENCODING', 'cl100k_base')
        
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

    def _ensure_token_encoder(self):
        if self._token_encoder_failed:
            return None
        if self._token_encoder is not None:
            return self._token_encoder
        try:
            import tiktoken
            self._token_encoder = tiktoken.get_encoding(self._token_encoding_name)
            logger.debug('Initialized tiktoken encoder %s for token counting', self._token_encoding_name)
            return self._token_encoder
        except Exception as exc:
            self._token_encoder_failed = True
            logger.debug('Unable to initialize tiktoken encoder %s: %s', self._token_encoding_name, exc)
            return None

    def _count_tokens(self, text: str) -> Optional[int]:
        if not text:
            return 0
        encoder = self._ensure_token_encoder()
        if encoder is None:
            return None
        try:
            return len(encoder.encode(text))
        except Exception as exc:
            self._token_encoder_failed = True
            logger.debug('Token counting failed, disabling encoder: %s', exc)
            return None
    
    def _initialize_all(self):
        """Initialize all scanners (used when lazy_init is False)."""
        if self._initialized:
            return
        
        # Configure local models if enabled
        if self.use_local_models:
            self._configure_local_models_in()
            self._configure_local_models_out()
        
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
            self._configure_local_models_in()
        
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
        if self.use_local_models:
            self._configure_local_models_out()
        
        self._init_output_scanners()
        self._output_scanners_initialized = True
        logger.info('Output scanners initialized')

    def _configure_local_models_in(self):
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
            
    def _configure_local_models_out(self):
        """Configure model paths and settings for local model usage with device optimization."""
        if not HAS_LLM_GUARD:
            return
            
        try:
            # Get base path for local models
            models_base_path = os.environ.get('LLM_GUARD_MODELS_PATH', './models')
            
            device_name = 'MPS (Apple Silicon GPU)' if self.device == 'mps' else 'CPU'
            logger.info(f'Configuring models for {device_name} inference')
            
            # Configure Malicious URLs model (used for output)
            if MALICIOUS_URLS_MODEL:
                MALICIOUS_URLS_MODEL.path = os.path.join(models_base_path, "codebert-base-Malicious_URLs")
                MALICIOUS_URLS_MODEL.kwargs["local_files_only"] = True
                logger.info(f'Configured Malicious URLs model path: {MALICIOUS_URLS_MODEL.path}')
            
            # Configure Code model (used for both input and output)
            if NO_REFUSAL_MODEL:
                NO_REFUSAL_MODEL.path = os.path.join(models_base_path, "distilroberta-base-rejection-v1")
                NO_REFUSAL_MODEL.kwargs["local_files_only"] = True
                logger.info(f'Configured No Refusal model path: {NO_REFUSAL_MODEL.path}')

            logger.info(f'Local model configuration completed for device: {self.device}')
            
        except Exception as e:
            logger.exception('Failed to configure local models: %s', e)
            self.use_local_models = False
    
    def _get_env_scanner_enabled(self, env_var_name: str) -> Optional[bool]:
        """
        Check if a scanner is enabled/disabled via environment variable.
        
        Args:
            env_var_name: The environment variable name (e.g., 'LLM_GUARD_INPUT_TOXICITY')
            
        Returns:
            True/False if env var is set, None if not set
        """
        env_value = os.environ.get(env_var_name, '').lower()
        if env_value in ('1', 'true', 'yes', 'on'):
            return True
        elif env_value in ('0', 'false', 'no', 'off'):
            return False
        return None
            
    def _is_input_scanner_enabled(self, scanner_name: str, default: bool = True) -> bool:
        """
        Check if an input scanner is enabled based on environment variable or configuration.
        
        Priority:
        1. Environment variable (LLM_GUARD_INPUT_<SCANNER_NAME>)
        2. Configuration file (input_scanners.<scanner_name>.enabled)
        3. Default value
        
        Args:
            scanner_name: The scanner key name in config (e.g., 'ban_substrings', 'prompt_injection')
            default: Default value if scanner config is not found
            
        Returns:
            True if scanner is enabled, False otherwise
        """
        # Check environment variable first (highest priority)
        env_var_name = f'LLM_GUARD_INPUT_{scanner_name.upper()}'
        env_enabled = self._get_env_scanner_enabled(env_var_name)
        if env_enabled is not None:
            logger.debug(f'Input scanner {scanner_name} enabled={env_enabled} via env var {env_var_name}')
            return env_enabled
        
        # Check config file
        scanner_config = self.input_scanners_config.get(scanner_name, {})
        if isinstance(scanner_config, dict):
            return scanner_config.get('enabled', default)
        return default
    
    def _is_output_scanner_enabled(self, scanner_name: str, default: bool = True) -> bool:
        """
        Check if an output scanner is enabled based on environment variable or configuration.
        
        Priority:
        1. Environment variable (LLM_GUARD_OUTPUT_<SCANNER_NAME>)
        2. Configuration file (output_scanners.<scanner_name>.enabled)
        3. Default value
        
        Args:
            scanner_name: The scanner key name in config (e.g., 'ban_substrings', 'toxicity')
            default: Default value if scanner config is not found
            
        Returns:
            True if scanner is enabled, False otherwise
        """
        # Check environment variable first (highest priority)
        env_var_name = f'LLM_GUARD_OUTPUT_{scanner_name.upper()}'
        env_enabled = self._get_env_scanner_enabled(env_var_name)
        if env_enabled is not None:
            logger.debug(f'Output scanner {scanner_name} enabled={env_enabled} via env var {env_var_name}')
            return env_enabled
        
        # Check config file
        scanner_config = self.output_scanners_config.get(scanner_name, {})
        if isinstance(scanner_config, dict):
            return scanner_config.get('enabled', default)
        return default

    def _init_input_scanners(self):
        """
        Initialize input scanners for use with scan_prompt function.
        Uses the official scan_prompt method from llm-guard library.
        Each scanner can be individually enabled/disabled via configuration.
        """
        try:
            self.input_scanners = []
            
            # BanSubstrings scanner
            if self._is_input_scanner_enabled('ban_substrings'):
                ban_config = self.input_scanners_config.get('ban_substrings', {})
                substrings = ban_config.get('substrings', ["malicious", "dangerous"]) if isinstance(ban_config, dict) else ["malicious", "dangerous"]
                self.input_scanners.append(
                    InputBanSubstrings(substrings)
                )
                logger.info('Input BanSubstrings scanner enabled')
            else:
                logger.info('Input BanSubstrings scanner disabled via configuration')
            
            # PromptInjection scanner with local model support
            if self._is_input_scanner_enabled('prompt_injection'):
                self.input_scanners.append(
                    PromptInjection(model=PROMPT_INJECTION_MODEL if self.use_local_models else None)
                )
                logger.info('Input PromptInjection scanner enabled')
            else:
                logger.info('Input PromptInjection scanner disabled via configuration')
            
            # Toxicity scanner with local model support
            if self._is_input_scanner_enabled('toxicity'):
                toxicity_config = self.input_scanners_config.get('toxicity', {})
                threshold = toxicity_config.get('threshold', 0.5) if isinstance(toxicity_config, dict) else 0.5
                self.input_scanners.append(
                    InputToxicity(
                        threshold=threshold,
                        model=TOXICITY_MODEL if self.use_local_models else None
                    )
                )
                logger.info('Input Toxicity scanner enabled with threshold=%s', threshold)
            else:
                logger.info('Input Toxicity scanner disabled via configuration')
            
            # Secrets scanner
            if self._is_input_scanner_enabled('secrets'):
                self.input_scanners.append(Secrets())
                logger.info('Input Secrets scanner enabled')
            else:
                logger.info('Input Secrets scanner disabled via configuration')
            
            # Code scanner - check both config and enable_input_code_scanner flag
            code_enabled_in_config = self._is_input_scanner_enabled('code')
            if self.enable_input_code_scanner and code_enabled_in_config:
                self.input_scanners.append(
                    InputCode(
                        languages=code_language,
                        is_blocked=True,
                        model=CODE_MODEL if self.use_local_models else None
                    )
                )
                logger.info('Input Code scanner enabled')
            else:
                logger.info('Input Code scanner disabled via configuration')
            
            # Anonymize scanner - check both enable_anonymize flag and config
            anonymize_enabled_in_config = self._is_input_scanner_enabled('anonymize', default=self.enable_anonymize)
            if self.enable_anonymize and self.vault and anonymize_enabled_in_config:
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
                    logger.info('Input Anonymize scanner enabled')
                except Exception as e:
                    logger.warning('Failed to add Anonymize scanner: %s', e)
            else:
                logger.info('Input Anonymize scanner disabled via configuration')
            
            logger.info('Input scanners initialized: %d scanners ready for scan_prompt (local_models: %s)', 
                       len(self.input_scanners), self.use_local_models)
        except Exception as e:
            logger.exception('Failed to init input scanners: %s', e)
            self.input_scanners = []

    def _init_output_scanners(self):
        """
        Initialize output scanners for use with scan_output function.
        Each scanner can be individually enabled/disabled via configuration.
        """
        try:
            self.output_scanners = []
            
            # BanSubstrings scanner
            if self._is_output_scanner_enabled('ban_substrings'):
                ban_config = self.output_scanners_config.get('ban_substrings', {})
                substrings = ban_config.get('substrings', ["malicious", "dangerous"]) if isinstance(ban_config, dict) else ["malicious", "dangerous"]
                self.output_scanners.append(
                    OutputBanSubstrings(substrings)
                )
                logger.info('Output BanSubstrings scanner enabled')
            else:
                logger.info('Output BanSubstrings scanner disabled via configuration')
            
            # Toxicity scanner
            if self._is_output_scanner_enabled('toxicity'):
                toxicity_config = self.output_scanners_config.get('toxicity', {})
                threshold = toxicity_config.get('threshold', 0.5) if isinstance(toxicity_config, dict) else 0.5
                self.output_scanners.append(
                    OutputToxicity(
                        threshold=threshold,
                        model=TOXICITY_MODEL if self.use_local_models else None
                    )
                )
                logger.info('Output Toxicity scanner enabled with threshold=%s', threshold)
            else:
                logger.info('Output Toxicity scanner disabled via configuration')
            
            # MaliciousURLs scanner
            if self._is_output_scanner_enabled('malicious_urls'):
                self.output_scanners.append(
                    MaliciousURLs(model=MALICIOUS_URLS_MODEL if self.use_local_models else None)
                )
                logger.info('Output MaliciousURLs scanner enabled')
            else:
                logger.info('Output MaliciousURLs scanner disabled via configuration')
            
            # NoRefusal scanner
            if self._is_output_scanner_enabled('no_refusal'):
                self.output_scanners.append(
                    NoRefusal(model=NO_REFUSAL_MODEL if self.use_local_models else None)
                )
                logger.info('Output NoRefusal scanner enabled')
            else:
                logger.info('Output NoRefusal scanner disabled via configuration')
            
            # Code scanner
            if self._is_output_scanner_enabled('code'):
                self.output_scanners.append(
                    OutputCode(
                        languages=code_language,
                        is_blocked=True,
                        model=CODE_MODEL if self.use_local_models else None
                    )
                )
                logger.info('Output Code scanner enabled')
            else:
                logger.info('Output Code scanner disabled via configuration')
            
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
                raw_score = results_score.get(scanner_name, 0.0)
                risk_score = max(0.0, min(raw_score, 1.0)) * 100
                scan_results[scanner_name] = {
                    'passed': is_valid,
                    'risk_score': risk_score,
                    'sanitized': sanitized_prompt != prompt
                }
                
                if not is_valid:
                    logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score:.2f}%')
            
            all_valid = all(results_valid.values())
            return sanitized_prompt, all_valid, scan_results
            
        except Exception as e:
            logger.exception('Error running input scanners with scan_prompt: %s', e)
            return prompt, False, {'error': str(e)}

    async def _run_output_scanners(self, text: str, prompt: str = "") -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all output scanners on the text using scan_output function.
        
        Uses the official scan_output method from llm-guard library (similar to scan_prompt).
        For performance, only the assistant output is scanned; the prompt argument is ignored.
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
                "",  # Skip prompt to minimize token usage during output scans
                text,
                self.scan_fail_fast
            )
            
            # Convert results to expected format
            scan_results = {}
            for scanner_name, is_valid in results_valid.items():
                raw_score = results_score.get(scanner_name, 0.0)
                risk_score = max(0.0, min(raw_score, 1.0)) * 100
                scan_results[scanner_name] = {
                    'passed': is_valid,
                    'risk_score': risk_score,
                    'sanitized': sanitized_output != text
                }
                
                if not is_valid:
                    logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score:.2f}%')
            
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
        prompt_length = len(prompt) if isinstance(prompt, str) else 0
        if logger.isEnabledFor(logging.DEBUG):
            token_count = self._count_tokens(prompt)
            if token_count is not None:
                logger.debug('LLM Guard input scan: tokens=%d chars=%d', token_count, prompt_length)
            else:
                logger.debug('LLM Guard input scan: chars=%d (token count unavailable)', prompt_length)
        
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
            if logger.isEnabledFor(logging.DEBUG) and sanitized_prompt is not None and isinstance(sanitized_prompt, str):
                sanitized_length = len(sanitized_prompt)
                token_count = self._count_tokens(sanitized_prompt)
                if token_count is not None:
                    logger.debug('LLM Guard sanitized input: tokens=%d chars=%d', token_count, sanitized_length)
                else:
                    logger.debug('LLM Guard sanitized input: chars=%d (token count unavailable)', sanitized_length)
            
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
        
        logger.debug("LLM Guard output scan request: prompt length=%d, text length=%d", len(prompt), len(text))
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
