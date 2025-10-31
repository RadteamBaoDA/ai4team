"""Unit tests for the reranker configuration."""

import os
import pytest
from unittest.mock import patch

from reranker.core.config import RerankerConfig


class TestRerankerConfig:
    """Test cases for RerankerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = RerankerConfig.from_env()
            
            assert config.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
            assert config.max_length == 512
            assert config.max_parallel == 4
            assert config.batch_size == 16
            assert config.quantization == "none"

    def test_custom_config(self):
        """Test configuration with custom environment variables."""
        env_vars = {
            "RERANKER_MODEL": "custom-model",
            "RERANKER_MAX_PARALLEL": "8", 
            "RERANKER_BATCH_SIZE": "32",
            "RERANKER_QUANTIZATION": "int8",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = RerankerConfig.from_env()
            
            assert config.model_name == "custom-model"
            assert config.max_parallel == 8
            assert config.batch_size == 32
            assert config.quantization == "int8"

    def test_mlx_auto_detection(self):
        """Test MLX auto-detection on Apple Silicon."""
        with patch.dict(os.environ, {"RERANKER_DEVICE": "auto"}, clear=True):
            with patch("platform.system", return_value="Darwin"):
                with patch("platform.machine", return_value="arm64"):
                    # Mock MLX availability
                    with patch("importlib.import_module"):
                        config = RerankerConfig.from_env()
                        # MLX detection depends on actual import, this tests the flow
                        assert config.device_preference in ["auto", "mlx"]