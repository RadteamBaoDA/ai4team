"""Setup configuration for the reranker package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req for req in requirements if req and not req.startswith('#')]

setup(
    name="reranker-service",
    version="2.0.0",
    author="AI4Team",
    author_email="contact@ai4team.com",
    description="Production-ready reranking service with optimized concurrency and performance",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai4team/reranker",
    
    # Package configuration
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    
    # Dependencies
    install_requires=requirements,
    extras_require={
        "mlx": ["mlx>=0.0.5", "mlx-lm>=0.0.3"],
        "redis": ["redis>=4.6.0"],
        "monitoring": ["prometheus-client>=0.17.0"],
        "quantization": ["bitsandbytes>=0.41.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    
    # Entry points
    entry_points={
        "console_scripts": [
            "reranker=reranker.__main__:main",
        ],
    },
    
    # Metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    python_requires=">=3.8",
    zip_safe=False,
)