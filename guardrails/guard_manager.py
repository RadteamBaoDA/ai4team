import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

import importlib

# Dynamically import llm-guard to avoid static import errors when it's not installed.
try:
    _input_mod = importlib.import_module('llm_guard.input_scanners')
    _output_mod = importlib.import_module('llm_guard.output_scanners')
    _guard_mod = importlib.import_module('llm_guard.guard')

    BanSubstrings = getattr(_input_mod, 'BanSubstrings')
    PromptInjection = getattr(_input_mod, 'PromptInjection')
    Toxicity = getattr(_input_mod, 'Toxicity')
    Secrets = getattr(_input_mod, 'Secrets')
    Code = getattr(_input_mod, 'Code')
    TokenLimit = getattr(_input_mod, 'TokenLimit')

    OutputBanSubstrings = getattr(_output_mod, 'BanSubstrings')
    OutputToxicity = getattr(_output_mod, 'Toxicity')
    MaliciousURLs = getattr(_output_mod, 'MaliciousURLs')
    NoRefusal = getattr(_output_mod, 'NoRefusal')
    NoCode = getattr(_output_mod, 'NoCode')

    Guard = getattr(_guard_mod, 'Guard')
    HAS_LLM_GUARD = True
except Exception:
    HAS_LLM_GUARD = False


class LLMGuardManager:
    def __init__(self, enable_input: bool = True, enable_output: bool = True):
        self.enable_input = enable_input and HAS_LLM_GUARD
        self.enable_output = enable_output and HAS_LLM_GUARD
        self.input_guard = None
        self.output_guard = None
        if not HAS_LLM_GUARD:
            logger.warning('LLM Guard not installed; guard features disabled')
            return
        if self.enable_input:
            self._init_input_guard()
        if self.enable_output:
            self._init_output_guard()

    def _init_input_guard(self):
        try:
            input_scanners = [
                BanSubstrings(["malicious", "dangerous"]),
                PromptInjection(),
                Toxicity(threshold=0.5),
                Secrets(),
                TokenLimit(limit=4000),
            ]
            self.input_guard = Guard(input_scanners=input_scanners)
            logger.info('Input guard initialized')
        except Exception as e:
            logger.error('Failed to init input guard: %s', e)

    def _init_output_guard(self):
        try:
            output_scanners = [
                OutputBanSubstrings(["malicious", "dangerous"]),
                OutputToxicity(threshold=0.5),
                MaliciousURLs(),
                NoRefusal(),
                NoCode(),
            ]
            self.output_guard = Guard(output_scanners=output_scanners)
            logger.info('Output guard initialized')
        except Exception as e:
            logger.error('Failed to init output guard: %s', e)

    def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
        if not self.enable_input or not self.input_guard:
            return {"allowed": True, "scanners": {}}
        try:
            result = self.input_guard.validate(prompt)
            return {"allowed": result.validation_passed, "scanners": {s.name: {"passed": s.passed, "reason": s.reason} for s in result.scanners}}
        except Exception as e:
            logger.error('Input scan error: %s', e)
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}

    def scan_output(self, text: str, block_on_error: bool = False) -> Dict[str, Any]:
        if not self.enable_output or not self.output_guard:
            return {"allowed": True, "scanners": {}}
        try:
            result = self.output_guard.validate(text)
            return {"allowed": result.validation_passed, "scanners": {s.name: {"passed": s.passed, "reason": s.reason} for s in result.scanners}}
        except Exception as e:
            logger.error('Output scan error: %s', e)
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}
