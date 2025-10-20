import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

import importlib


# Lazy loader for llm-guard components. Import on demand to avoid heavy imports at module import time.
_lazy_state = {
    'loaded': False,
    'has_llm_guard': False,
    'BanSubstrings': None,
    'PromptInjection': None,
    'Toxicity': None,
    'Secrets': None,
    'Code': None,
    'TokenLimit': None,
    'OutputBanSubstrings': None,
    'OutputToxicity': None,
    'MaliciousURLs': None,
    'NoRefusal': None,
    'NoCode': None,
    'Guard': None,
}


def _ensure_llm_guard_loaded():
    """Try to import llm-guard and populate _lazy_state. Returns True if available."""
    if _lazy_state['loaded']:
        return _lazy_state['has_llm_guard']
    try:
        _input_mod = importlib.import_module('llm_guard.input_scanners')
        _output_mod = importlib.import_module('llm_guard.output_scanners')
        _guard_mod = importlib.import_module('llm_guard.guard')

        _lazy_state['BanSubstrings'] = getattr(_input_mod, 'BanSubstrings')
        _lazy_state['PromptInjection'] = getattr(_input_mod, 'PromptInjection')
        _lazy_state['Toxicity'] = getattr(_input_mod, 'Toxicity')
        _lazy_state['Secrets'] = getattr(_input_mod, 'Secrets')
        _lazy_state['Code'] = getattr(_input_mod, 'Code')
        _lazy_state['TokenLimit'] = getattr(_input_mod, 'TokenLimit')

        _lazy_state['OutputBanSubstrings'] = getattr(_output_mod, 'BanSubstrings')
        _lazy_state['OutputToxicity'] = getattr(_output_mod, 'Toxicity')
        _lazy_state['MaliciousURLs'] = getattr(_output_mod, 'MaliciousURLs')
        _lazy_state['NoRefusal'] = getattr(_output_mod, 'NoRefusal')
        _lazy_state['NoCode'] = getattr(_output_mod, 'NoCode')

        _lazy_state['Guard'] = getattr(_guard_mod, 'Guard')

        _lazy_state['has_llm_guard'] = True
    except Exception as e:
        logger.exception('Failed to import llm-guard; disabling guard features: %s', e)
        _lazy_state['has_llm_guard'] = False
    finally:
        _lazy_state['loaded'] = True
    return _lazy_state['has_llm_guard']


class LLMGuardManager:
    def __init__(self, enable_input: bool = True, enable_output: bool = True):
        # Ensure llm-guard is only imported when needed
        has_llm = _ensure_llm_guard_loaded()
        self.enable_input = enable_input and has_llm
        self.enable_output = enable_output and has_llm
        self.input_guard = None
        self.output_guard = None
        if not has_llm:
            logger.warning('LLM Guard not installed; guard features disabled')
            return
        if self.enable_input:
            self._init_input_guard()
        if self.enable_output:
            self._init_output_guard()

    def _init_input_guard(self):
        try:
            input_scanners = [
                _lazy_state['BanSubstrings'](["malicious", "dangerous"]),
                _lazy_state['PromptInjection'](),
                _lazy_state['Toxicity'](threshold=0.5),
                _lazy_state['Secrets'](),
                _lazy_state['TokenLimit'](limit=4000),
            ]
            self.input_guard = _lazy_state['Guard'](input_scanners=input_scanners)
            logger.info('Input guard initialized')
        except Exception as e:
            logger.exception('Failed to init input guard: %s', e)

    def _init_output_guard(self):
        try:
            output_scanners = [
                _lazy_state['OutputBanSubstrings'](["malicious", "dangerous"]),
                _lazy_state['OutputToxicity'](threshold=0.5),
                _lazy_state['MaliciousURLs'](),
                _lazy_state['NoRefusal'](),
                _lazy_state['NoCode'](),
            ]
            self.output_guard = _lazy_state['Guard'](output_scanners=output_scanners)
            logger.info('Output guard initialized')
        except Exception as e:
            logger.exception('Failed to init output guard: %s', e)

    def scan_input(self, prompt: str, block_on_error: bool = False) -> Dict[str, Any]:
        if not self.enable_input or not self.input_guard:
            return {"allowed": True, "scanners": {}}
        try:
            result = self.input_guard.validate(prompt)
            return {"allowed": result.validation_passed, "scanners": {s.name: {"passed": s.passed, "reason": s.reason} for s in result.scanners}}
        except Exception as e:
            logger.exception('Input scan error: %s', e)
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
            logger.exception('Output scan error: %s', e)
            if block_on_error:
                return {"allowed": False, "error": str(e)}
            return {"allowed": True, "error": str(e)}
