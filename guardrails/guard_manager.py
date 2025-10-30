import logging
import os
import platform
from typing import Dict, Any, List, Tuple

from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
code_language = ['Python', 'C#', 'C++', 'C']

# Check for PyTorch availability and device support
try:
    import torch
    HAS_TORCH = True
    logger.info(f'PyTorch {torch.__version__} detected')
except ImportError:
    HAS_TORCH = False
    logger.warning('PyTorch not available')

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
    from llm_guard import scan_prompt
    # Import model configurations for local model support
    from llm_guard.input_scanners.anonymize_helpers import DEBERTA_AI4PRIVACY_v2_CONF
    from llm_guard.input_scanners.code import DEFAULT_MODEL as INPUT_CODE_MODEL
    from llm_guard.input_scanners.prompt_injection import V2_MODEL as PROMPT_INJECTION_MODEL
    from llm_guard.input_scanners.toxicity import DEFAULT_MODEL as INPUT_TOXICITY_MODEL
    from llm_guard.output_scanners.toxicity import DEFAULT_MODEL as OUTPUT_TOXICITY_MODEL
    from llm_guard.output_scanners.code import DEFAULT_MODEL as OUTPUT_CODE_MODEL

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
    # Model configuration placeholders
    DEBERTA_AI4PRIVACY_v2_CONF = None
    INPUT_CODE_MODEL = PROMPT_INJECTION_MODEL = INPUT_TOXICITY_MODEL = None
    OUTPUT_TOXICITY_MODEL = OUTPUT_CODE_MODEL = None


class LLMGuardManager:
    def __init__(self, enable_input: bool = True, enable_output: bool = True, enable_anonymize: bool = True):
        """
        Initialize LLM Guard Manager with input and output scanning capabilities.
        
        Each scanner is called independently with its own scan() method.
        No Guard() wrapper class is used.
        
        Args:
            enable_input: Enable input scanning (default: True)
            enable_output: Enable output scanning (default: True)
            enable_anonymize: Enable PII anonymization (default: True)
        """
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.enable_anonymize = enable_anonymize and HAS_LLM_GUARD
        
        # Detect and configure compute device
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

    def _detect_device(self) -> str:
        """
        Detect the best available compute device for ML models.
        
        Priority order:
        1. MPS (Apple Silicon GPU) - macOS with Apple Silicon
        2. CUDA (NVIDIA GPU) - Linux/Windows with NVIDIA GPU
        3. CPU - Fallback for all platforms
        
        Returns:
            Device string: 'mps', 'cuda', or 'cpu'
        """
        if not HAS_TORCH:
            logger.info('PyTorch not available, using CPU for computations')
            return 'cpu'
        
        # Check for explicit device override
        device_override = os.environ.get('LLM_GUARD_DEVICE', '').lower()
        if device_override in ('mps', 'cuda', 'cpu'):
            if device_override == 'mps' and torch.backends.mps.is_available():
                logger.info('MPS device explicitly set and available')
                return 'mps'
            elif device_override == 'cuda' and torch.cuda.is_available():
                logger.info('CUDA device explicitly set and available')
                return 'cuda'
            elif device_override == 'cpu':
                logger.info('CPU device explicitly set')
                return 'cpu'
            else:
                logger.warning(f'Device override "{device_override}" not available, using auto-detection')
        
        # Auto-detect best available device
        # Priority 1: Apple Silicon MPS (Metal Performance Shaders)
        if torch.backends.mps.is_available():
            system = platform.system()
            machine = platform.machine()
            logger.info(f'MPS (Apple Silicon GPU) detected - System: {system}, Machine: {machine}')
            
            # Verify MPS is actually functional
            try:
                test_tensor = torch.zeros(1, device='mps')
                del test_tensor
                logger.info('MPS device verified and functional')
                return 'mps'
            except Exception as e:
                logger.warning(f'MPS available but not functional: {e}, falling back to CPU')
        
        # Priority 2: NVIDIA CUDA
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else 'Unknown'
            logger.info(f'CUDA GPU detected - Device: {device_name}, Count: {device_count}')
            return 'cuda'
        
        # Priority 3: CPU fallback
        cpu_count = os.cpu_count() or 1
        logger.info(f'Using CPU with {cpu_count} cores')
        
        # Enable CPU optimizations if available
        if HAS_TORCH:
            try:
                # Enable MKL-DNN optimizations for Intel CPUs
                torch.set_num_threads(cpu_count)
                logger.info(f'CPU optimizations enabled: {cpu_count} threads')
            except Exception as e:
                logger.debug(f'Could not set CPU optimizations: {e}')
        
        return 'cpu'
    
    def _check_local_models_config(self) -> bool:
        """Check if local models should be used based on environment variables."""
        use_local = os.environ.get('LLM_GUARD_USE_LOCAL_MODELS', '').lower() in ('1', 'true', 'yes', 'on')
        if use_local:
            logger.info('Local models enabled via LLM_GUARD_USE_LOCAL_MODELS environment variable')
        return use_local

    def _configure_local_models(self):
        """Configure model paths and settings for local model usage with device optimization."""
        if not HAS_LLM_GUARD:
            return
            
        try:
            # Get base path for local models
            models_base_path = os.environ.get('LLM_GUARD_MODELS_PATH', './models')
            
            # Device-specific optimizations
            device_kwargs = {}
            if HAS_TORCH:
                device_kwargs['device'] = self.device
                
                # MPS-specific optimizations for Apple Silicon
                if self.device == 'mps':
                    logger.info('Applying MPS optimizations for Apple Silicon')
                    device_kwargs['device_map'] = None  # MPS doesn't support device_map
                    # Enable reduced precision for faster inference on Apple Silicon
                    if os.environ.get('MPS_ENABLE_FP16', 'true').lower() in ('1', 'true', 'yes', 'on'):
                        device_kwargs['torch_dtype'] = torch.float16
                        logger.info('Enabled FP16 (half precision) for MPS')
                
                # CUDA-specific optimizations
                elif self.device == 'cuda':
                    logger.info('Applying CUDA optimizations')
                    device_kwargs['device_map'] = 'auto'
                    # Enable TensorFloat32 for better performance on Ampere+ GPUs
                    if torch.cuda.get_device_capability()[0] >= 8:
                        torch.backends.cuda.matmul.allow_tf32 = True
                        torch.backends.cudnn.allow_tf32 = True
                        logger.info('Enabled TF32 for CUDA')
                
                # CPU-specific optimizations
                else:
                    logger.info('Applying CPU optimizations')
                    # Enable JIT compilation for CPU
                    device_kwargs['torchscript'] = True
            
            # Configure Prompt Injection model
            if PROMPT_INJECTION_MODEL:
                PROMPT_INJECTION_MODEL.kwargs["local_files_only"] = True
                PROMPT_INJECTION_MODEL.kwargs.update(device_kwargs)
                PROMPT_INJECTION_MODEL.path = os.path.join(models_base_path, "deberta-v3-base-prompt-injection-v2")
                logger.info(f'Configured PromptInjection model path: {PROMPT_INJECTION_MODEL.path}')
            
            # Configure Anonymize model
            if DEBERTA_AI4PRIVACY_v2_CONF and "DEFAULT_MODEL" in DEBERTA_AI4PRIVACY_v2_CONF:
                DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].path = os.path.join(models_base_path, "deberta-v3-base_finetuned_ai4privacy_v2")
                DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].kwargs["local_files_only"] = True
                DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].kwargs.update(device_kwargs)
                logger.info(f'Configured Anonymize model path: {DEBERTA_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].path}')
            
            # Configure Input Toxicity model
            if INPUT_TOXICITY_MODEL:
                INPUT_TOXICITY_MODEL.path = os.path.join(models_base_path, "unbiased-toxic-roberta")
                INPUT_TOXICITY_MODEL.kwargs["local_files_only"] = True
                INPUT_TOXICITY_MODEL.kwargs.update(device_kwargs)
                logger.info(f'Configured input Toxicity model path: {INPUT_TOXICITY_MODEL.path}')
            
            # Configure Output Toxicity model
            if OUTPUT_TOXICITY_MODEL:
                OUTPUT_TOXICITY_MODEL.path = os.path.join(models_base_path, "unbiased-toxic-roberta")
                OUTPUT_TOXICITY_MODEL.kwargs["local_files_only"] = True
                OUTPUT_TOXICITY_MODEL.kwargs.update(device_kwargs)
                logger.info(f'Configured output Toxicity model path: {OUTPUT_TOXICITY_MODEL.path}')
            
            # Configure Input Code model
            if INPUT_CODE_MODEL:
                INPUT_CODE_MODEL.path = os.path.join(models_base_path, "programming-language-identification")
                INPUT_CODE_MODEL.kwargs["local_files_only"] = True
                INPUT_CODE_MODEL.kwargs.update(device_kwargs)
                logger.info(f'Configured input Code model path: {INPUT_CODE_MODEL.path}')
            
            # Configure Output Code model
            if OUTPUT_CODE_MODEL:
                OUTPUT_CODE_MODEL.path = os.path.join(models_base_path, "programming-language-identification")
                OUTPUT_CODE_MODEL.kwargs["local_files_only"] = True
                OUTPUT_CODE_MODEL.kwargs.update(device_kwargs)
                logger.info(f'Configured output Code model path: {OUTPUT_CODE_MODEL.path}')
            
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
                    model=INPUT_TOXICITY_MODEL if self.use_local_models else None
                )
            )
            
            # Secrets scanner
            self.input_scanners.append(Secrets())
            
            # Code scanner with local model support
            self.input_scanners.append(
                InputCode(
                    languages=code_language,
                    is_blocked=True,
                    model=INPUT_CODE_MODEL if self.use_local_models else None
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
        """Initialize output scanners using scan_prompt."""
        try:
            # Create scanners as a simple list for use with scan function
            self.output_scanners = [
                OutputBanSubstrings(["malicious", "dangerous"]),
                OutputToxicity(
                    threshold=0.5,
                    model=OUTPUT_TOXICITY_MODEL if self.use_local_models else None
                ),
                MaliciousURLs(),
                NoRefusal(),
                OutputCode(
                    languages=code_language,
                    is_blocked=True,
                    model=OUTPUT_CODE_MODEL if self.use_local_models else None
                ),
            ]
            
            logger.info('Output scanners initialized: %d scanners ready for scan (local_models: %s)', 
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
            # Use scan_prompt with input scanners in a thread pool
            sanitized_prompt, results_valid, results_score = await run_in_threadpool(
                scan_prompt,
                self.input_scanners,
                prompt
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

    async def _run_output_scanners(self, text: str) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all output scanners on the text in a thread pool.
        
        Each scanner is called with scan(text) method.
        Returns (sanitized_text, is_valid, scan_results)
        """
        
        def sync_scan():
            sanitized_text = text
            all_valid = True
            scan_results = {}
            
            for scanner in self.output_scanners:
                scanner_name = scanner.__class__.__name__
                
                try:
                    # Call scanner.scan() method directly
                    sanitized_text, is_valid, risk_score = scanner.scan(sanitized_text)
                    
                    scan_results[scanner_name] = {
                        'passed': is_valid,
                        'risk_score': risk_score,
                        'sanitized': sanitized_text != text
                    }
                    
                    if not is_valid:
                        all_valid = False
                        logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score}')
                        
                except Exception as e:
                    logger.exception(f'Error running output scanner {scanner_name}: %s', e)
                    scan_results[scanner_name] = {
                        'passed': False,
                        'error': str(e),
                        'sanitized': False
                    }
                    all_valid = False
            
            return sanitized_text, all_valid, scan_results

        return await run_in_threadpool(sync_scan)

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

    async def scan_output(self, text: str, block_on_error: bool = False) -> Dict[str, Any]:
        """
        Scan output text using all output scanners.
        
        Returns:
            {
                'allowed': bool - True if all scanners passed,
                'sanitized': str - Sanitized output text,
                'scanners': dict - Per-scanner results with pass/fail and risk scores,
                'error': str - Error message if block_on_error is True and scan failed
            }
        """
        if not self.enable_output or not self.output_scanners:
            return {
                "allowed": True,
                "sanitized": text,
                "scanners": {},
                "scanner_count": 0
            }
        
        try:
            sanitized_text, is_valid, scan_results = await self._run_output_scanners(text)
            
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
