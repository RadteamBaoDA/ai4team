#!/usr/bin/env python3
"""
Install dependencies for LiteLLM Proxy with LLM Guard

This script installs all required Python packages for the LiteLLM proxy
with custom guardrail security integration.

Usage:
    python install_dependencies.py
    python install_dependencies.py --upgrade
    python install_dependencies.py --requirements ./requirements.txt
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


class DependencyInstaller:
    """Install Python dependencies for LiteLLM proxy."""
    
    # Core dependencies with versions
    DEPENDENCIES = {
        'litellm': '1.41.0',
        'llm-guard': '0.3.18',
        'pyyaml': '6.0.1',
        'pydantic': '2.5.0',
        'fastapi': '0.104.1',
        'uvicorn': '0.24.0',
        'requests': '2.31.0',
        'redis': '5.0.0',
        'prometheus-client': '0.19.0',
        'python-dotenv': '1.0.0',
    }
    
    def __init__(self, upgrade=False, requirements_file=None):
        """Initialize installer."""
        self.upgrade = upgrade
        self.requirements_file = requirements_file
        self.installed_packages = []
        self.failed_packages = []
    
    def check_python_version(self):
        """Verify Python version compatibility."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python 3.8+ required. Current: {version.major}.{version.minor}")
            sys.exit(1)
        print(f"✓ Python version {version.major}.{version.minor}.{version.micro} OK")
    
    def upgrade_pip(self):
        """Upgrade pip to latest version."""
        print("\n📦 Upgrading pip...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'
            ])
            print("✓ pip upgraded")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to upgrade pip: {e}")
            # Don't exit, continue with installation
    
    def install_from_requirements(self, requirements_file):
        """Install from requirements.txt file."""
        if not os.path.exists(requirements_file):
            print(f"❌ Requirements file not found: {requirements_file}")
            sys.exit(1)
        
        print(f"\n📦 Installing from {requirements_file}...")
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', '-r', requirements_file]
            if self.upgrade:
                cmd.insert(4, '--upgrade')
            
            subprocess.check_call(cmd)
            print(f"✓ All packages installed from {requirements_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from requirements file: {e}")
            return False
    
    def install_package(self, package_name, version=None):
        """Install a single package."""
        package_spec = f"{package_name}=={version}" if version else package_name
        
        try:
            print(f"  Installing {package_spec}...", end=' ', flush=True)
            cmd = [sys.executable, '-m', 'pip', 'install', package_spec]
            if self.upgrade:
                cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', package_spec]
            
            subprocess.check_call(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✓")
            self.installed_packages.append(package_spec)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌")
            self.failed_packages.append(f"{package_spec}: {e}")
            return False
    
    def install_all(self):
        """Install all dependencies."""
        print("\n📦 Installing LiteLLM Proxy Dependencies")
        print("=" * 60)
        
        for package_name, version in self.DEPENDENCIES.items():
            self.install_package(package_name, version)
        
        return len(self.failed_packages) == 0
    
    def verify_installation(self):
        """Verify that key packages are installed."""
        print("\n✓ Verifying installation...")
        print("=" * 60)
        
        critical_packages = ['litellm', 'llm_guard', 'pydantic', 'fastapi', 'uvicorn']
        all_ok = True
        
        for package in critical_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✓ {package}")
            except ImportError:
                print(f"❌ {package} NOT installed")
                all_ok = False
        
        return all_ok
    
    def print_summary(self):
        """Print installation summary."""
        print("\n" + "=" * 60)
        print("Installation Summary")
        print("=" * 60)
        
        if self.installed_packages:
            print(f"\n✓ Successfully installed {len(self.installed_packages)} packages:")
            for pkg in self.installed_packages[:5]:
                print(f"  - {pkg}")
            if len(self.installed_packages) > 5:
                print(f"  ... and {len(self.installed_packages) - 5} more")
        
        if self.failed_packages:
            print(f"\n❌ Failed to install {len(self.failed_packages)} packages:")
            for pkg in self.failed_packages[:5]:
                print(f"  - {pkg}")
            if len(self.failed_packages) > 5:
                print(f"  ... and {len(self.failed_packages) - 5} more")
        
        print("\n" + "=" * 60)
        print("Installation Details")
        print("=" * 60)
        print(f"Installed packages: {len(self.installed_packages)}")
        print(f"Failed packages: {len(self.failed_packages)}")
        print(f"Total: {len(self.installed_packages) + len(self.failed_packages)}")
    
    def run(self):
        """Run the installation process."""
        print("=" * 60)
        print("LiteLLM Proxy Dependency Installer")
        print("=" * 60)
        
        # Check Python version
        self.check_python_version()
        
        # Upgrade pip if requested
        if self.upgrade:
            self.upgrade_pip()
        
        # Install from requirements file if provided
        if self.requirements_file:
            if not self.install_from_requirements(self.requirements_file):
                sys.exit(1)
        else:
            # Install individual packages
            if not self.install_all():
                print("\n⚠️  Some packages failed to install")
        
        # Verify installation
        if self.verify_installation():
            print("\n✅ All critical packages installed successfully!")
            self.print_summary()
            return 0
        else:
            print("\n❌ Some critical packages are missing")
            self.print_summary()
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Install LiteLLM Proxy dependencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_dependencies.py
  python install_dependencies.py --upgrade
  python install_dependencies.py --requirements ./requirements.txt
  python install_dependencies.py --upgrade --requirements ./requirements.txt
        """
    )
    
    parser.add_argument(
        '--upgrade',
        action='store_true',
        help='Upgrade packages to latest versions'
    )
    
    parser.add_argument(
        '--requirements',
        type=str,
        default=None,
        help='Path to requirements.txt file (default: use hardcoded versions)'
    )
    
    args = parser.parse_args()
    
    # Run installer
    installer = DependencyInstaller(
        upgrade=args.upgrade,
        requirements_file=args.requirements
    )
    
    exit_code = installer.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
