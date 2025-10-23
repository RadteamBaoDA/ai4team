import logging
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
        
        self.input_scanners = []
        self.output_scanners = []
        self.vault = None
        
        if not HAS_LLM_GUARD:
            logger.warning('LLM Guard not installed; guard features disabled')
            return
        
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

    def _init_input_scanners(self):
        """Initialize input scanners (no Guard() wrapper)."""
        try:
            # Create each scanner individually
            self.input_scanners = [
                {
                    'name': 'BanSubstrings',
                    'scanner': InputBanSubstrings(["malicious", "dangerous"]),
                    'enabled': True
                },
                {
                    'name': 'PromptInjection',
                    'scanner': PromptInjection(),
                    'enabled': True
                },
                {
                    'name': 'Toxicity',
                    'scanner': InputToxicity(threshold=0.5),
                    'enabled': True
                },
                {
                    'name': 'Secrets',
                    'scanner': Secrets(),
                    'enabled': True
                },
                {
                    'name': 'TokenLimit',
                    'scanner': TokenLimit(limit=4000),
                    'enabled': True
                },
            ]
            
            # Add Anonymize scanner if vault is available
            if self.enable_anonymize and self.vault:
                try:
                    anonymize_scanner = Anonymize(
                        self.vault,
                        preamble="Insert before prompt",
                        allowed_names=["John Doe"],
                        hidden_names=["Test LLC"],
                        language="en"
                    )
                    self.input_scanners.append({
                        'name': 'Anonymize',
                        'scanner': anonymize_scanner,
                        'enabled': True
                    })
                    logger.info('Anonymize scanner added to input scanners')
                except Exception as e:
                    logger.warning('Failed to add Anonymize scanner: %s', e)
            
            logger.info('Input scanners initialized: %d scanners ready', len(self.input_scanners))
        except Exception as e:
            logger.exception('Failed to init input scanners: %s', e)
            self.input_scanners = []

    def _init_output_scanners(self):
        """Initialize output scanners (no Guard() wrapper)."""
        try:
            # Create each scanner individually
            self.output_scanners = [
                {
                    'name': 'BanSubstrings',
                    'scanner': OutputBanSubstrings(["malicious", "dangerous"]),
                    'enabled': True
                },
                {
                    'name': 'Toxicity',
                    'scanner': OutputToxicity(threshold=0.5),
                    'enabled': True
                },
                {
                    'name': 'MaliciousURLs',
                    'scanner': MaliciousURLs(),
                    'enabled': True
                },
                {
                    'name': 'NoRefusal',
                    'scanner': NoRefusal(),
                    'enabled': True
                },
                {
                    'name': 'Code',
                    'scanner': OutputCode(languages=code_language, is_blocked=True),
                    'enabled': True
                },
            ]
            
            logger.info('Output scanners initialized: %d scanners ready', len(self.output_scanners))
        except Exception as e:
            logger.exception('Failed to init output scanners: %s', e)
            self.output_scanners = []

    def _run_input_scanners(self, prompt: str) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all input scanners on the prompt.
        
        Each scanner is called with scan(text) method.
        Returns (sanitized_text, is_valid, scan_results)
        """
        sanitized_prompt = prompt
        all_valid = True
        scan_results = {}
        
        for scanner_info in self.input_scanners:
            if not scanner_info['enabled']:
                continue
                
            scanner_name = scanner_info['name']
            scanner = scanner_info['scanner']
            
            try:
                # Call scanner.scan() method directly
                # Returns: (sanitized_output, is_valid, risk_score)
                sanitized_prompt, is_valid, risk_score = scanner.scan(sanitized_prompt)
                
                scan_results[scanner_name] = {
                    'passed': is_valid,
                    'risk_score': risk_score,
                    'sanitized': sanitized_prompt != prompt
                }
                
                if not is_valid:
                    all_valid = False
                    logger.warning(f'Scanner {scanner_name} failed: risk_score={risk_score}')
                    
            except Exception as e:
                logger.exception(f'Error running input scanner {scanner_name}: %s', e)
                scan_results[scanner_name] = {
                    'passed': False,
                    'error': str(e),
                    'sanitized': False
                }
                all_valid = False
        
        return sanitized_prompt, all_valid, scan_results

    def _run_output_scanners(self, text: str) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Run all output scanners on the text.
        
        Each scanner is called with scan(text) method.
        Returns (sanitized_text, is_valid, scan_results)
        """
        sanitized_text = text
        all_valid = True
        scan_results = {}
        
        for scanner_info in self.output_scanners:
            if not scanner_info['enabled']:
                continue
                
            scanner_name = scanner_info['name']
            scanner = scanner_info['scanner']
            
            try:
                # Call scanner.scan() method directly
                # Returns: (sanitized_output, is_valid, risk_score)
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

    def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
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
            sanitized_prompt, is_valid, scan_results = self._run_input_scanners(prompt)
            
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

    def scan_output(self, text: str, block_on_error: bool = False) -> Dict[str, Any]:
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
            sanitized_text, is_valid, scan_results = self._run_output_scanners(text)
            
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
