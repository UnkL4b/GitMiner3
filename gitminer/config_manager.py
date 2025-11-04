"""
Configuration Manager for GitMiner v3

This module handles loading and managing all configuration settings
from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any

import yaml

from gitminer.utils import highlight
from colorama import Fore


class ConfigManager:
    """
    Manages application configuration from YAML files and environment variables.
    
    This class provides centralized access to all configuration settings,
    including paths, GitHub API settings, pattern definitions, and labels.
    """

    def __init__(
        self,
        config_dir: str = "config",
        paths_file: str = "paths.yaml",
        labels_file: Optional[str] = None,
        patterns_file: Optional[str] = None
    ):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
            paths_file: Filename for paths configuration
            labels_file: Optional filename for labels configuration
            patterns_file: Optional filename for patterns configuration
        """
        self.config_dir = Path(config_dir)
        self.paths_config: Dict[str, Any] = {}
        self.labels: Dict[str, str] = {}
        self.patterns: Dict[str, re.Pattern] = {}
        
        self._load_paths_config(paths_file)
        
        labels_path = labels_file or self.get_path('files', 'labels_config')
        patterns_path = (
            patterns_file or self.get_path('files', 'patterns_config')
        )
        
        self._load_labels(labels_path)
        self._load_patterns(patterns_path)

    def _load_yaml_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load and parse a YAML file.

        Args:
            filepath: Path to the YAML file

        Returns:
            Parsed YAML data as dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            yaml.YAMLError: If the file contains invalid YAML
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                return data if data else {}
        except yaml.YAMLError as error:
            raise yaml.YAMLError(
                f"Error parsing YAML file {filepath}: {error}"
            )

    def _load_paths_config(self, filename: str) -> None:
        """
        Load paths configuration from YAML file.

        Args:
            filename: Name of the paths configuration file
        """
        filepath = self.config_dir / filename
        
        try:
            self.paths_config = self._load_yaml_file(str(filepath))
            print(highlight(
                f"[+] Loaded paths configuration from {filepath}",
                Fore.GREEN
            ))
        except Exception as error:
            print(highlight(
                f"[!] Failed to load paths config: {error}. Using defaults.",
                Fore.YELLOW
            ))
            self._load_default_paths()

    def _load_default_paths(self) -> None:
        """Load default path configuration when YAML file is unavailable."""
        self.paths_config = {
            'directories': {
                'raw_files': 'raw',
                'reports': 'reports',
                'data': 'data'
            },
            'files': {
                'database': 'gitminer_history.sqlite',
                'output_csv': 'results.csv'
            },
            'github': {
                'search_url': 'https://api.github.com/search/code',
                'contents_url': 'https://api.github.com/repos/{repo}/contents/{path}',
                'rate_limit_url': 'https://api.github.com/rate_limit',
                'user_agent': 'GitMiner-v3',
                'timeout': 60,
                'per_page_default': 30,
                'max_results_default': 200
            }
        }

    def _load_labels(self, filepath: str) -> None:
        """
        Load label mappings from YAML file.

        Labels map regex patterns to human-readable names for
        credential detection.

        Args:
            filepath: Path to the labels YAML file
        """
        try:
            data = self._load_yaml_file(filepath)
            self.labels = {str(key): str(value) for key, value in data.items()}
            print(highlight(
                f"[+] Loaded {len(self.labels)} label patterns",
                Fore.GREEN
            ))
        except Exception as error:
            print(highlight(
                f"[!] Failed to load labels: {error}. Using defaults.",
                Fore.YELLOW
            ))
            self._load_default_labels()

    def _load_default_labels(self) -> None:
        """Load default label patterns when YAML file is unavailable."""
        self.labels = {
            r"(?i)(ftp[_\- ]?user|ftpuser|ftp_login|ftp_username)": "FTP_USER",
            r"(?i)(ftp[_\- ]?pass|ftppassword|ftp_password|ftp_pass)": "FTP_PASS",
            r"(?i)(db[_\- ]?user|dbuser|db_username|database_user)": "DB_USER",
            r"(?i)(db[_\- ]?pass|dbpassword|db_password|database_password)": "DB_PASSWORD",
            r"(?i)(api[_\- ]?key|apikey|api_key|token)": "API_KEY",
            r"(?i)(aws[_\- ]?access[_\- ]?key|aws_access_key_id)": "AWS_ACCESS_KEY",
            r"(?i)(aws[_\- ]?secret|aws_secret_access_key)": "AWS_SECRET_KEY",
            r"(?i)(password|passwd|pass)": "PASSWORD",
            r"(?i)(username|user)": "USER",
            r"(?i)(secret)": "SECRET",
            r"(?i)(private[_\- ]?key|privatekey)": "PRIVATE_KEY"
        }

    def _load_patterns(self, filepath: str) -> None:
        """
        Load regex patterns from YAML file and compile them.

        Args:
            filepath: Path to the patterns YAML file
        """
        try:
            data = self._load_yaml_file(filepath)
            self.patterns = {
                str(key): re.compile(str(value))
                for key, value in data.items()
            }
            print(highlight(
                f"[+] Loaded {len(self.patterns)} detection patterns",
                Fore.GREEN
            ))
        except Exception as error:
            print(highlight(
                f"[!] Failed to load patterns: {error}. Using defaults.",
                Fore.YELLOW
            ))
            self._load_default_patterns()

    def _load_default_patterns(self) -> None:
        """Load default regex patterns when YAML file is unavailable."""
        default_patterns = {
            "EMAIL": r"[a-zA-Z0-9.\-_+%]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,}",
            "AWS_ACCESS_KEY_ID": r"AKIA[0-9A-Z]{16}",
            "GITHUB_TOKEN": r"ghp_[A-Za-z0-9_]{36,255}",
            "JWT": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
            "SSH_PRIVATE_KEY": r"-----BEGIN (?:OPENSSH|RSA|DSA|EC|ENCRYPTED PRIVATE KEY)-----",
            "URL_WITH_CREDENTIALS": r"https?://[^/\s:@]+:[^@\s/]+@",
            "BASE64_LONG": r"\b(?:[A-Za-z0-9+/]{40,}={0,2})\b",
            "HIGH_ENTROPY": r"\b[A-Za-z0-9\-_]{30,}\b",
        }
        self.patterns = {
            key: re.compile(pattern)
            for key, pattern in default_patterns.items()
        }

    def get_path(self, category: str, key: str) -> str:
        """
        Get a path value from configuration.

        Args:
            category: Configuration category (e.g., 'directories', 'files')
            key: Specific key within the category

        Returns:
            Path value as string

        Raises:
            KeyError: If the category or key doesn't exist
        """
        return self.paths_config.get(category, {}).get(key, '')

    def get_github_config(self, key: str) -> Any:
        """
        Get a GitHub API configuration value.

        Args:
            key: Configuration key (e.g., 'search_url', 'timeout')

        Returns:
            Configuration value
        """
        return self.paths_config.get('github', {}).get(key)

    def get_github_token(self) -> Optional[str]:
        """
        Get GitHub token from environment variable.

        Returns:
            GitHub token if found, None otherwise
        """
        return os.environ.get('GITHUB_TOKEN')

    def get_labels(self) -> Dict[str, str]:
        """
        Get all label mappings.

        Returns:
            Dictionary mapping regex patterns to label names
        """
        return self.labels.copy()

    def get_patterns(self) -> Dict[str, re.Pattern]:
        """
        Get all compiled regex patterns.

        Returns:
            Dictionary mapping pattern names to compiled regex objects
        """
        return self.patterns.copy()
