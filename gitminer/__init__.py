"""
GitMiner v3 - GitHub Secret Scanner and Threat Intelligence Tool

A modular, object-oriented tool for discovering sensitive information
in public GitHub repositories using advanced dork queries and pattern matching.

Author: UnkL4b 
Version: 3.0.0
"""

__version__ = "3.0.0"
__author__ = "UnkL4b"

from gitminer.config_manager import ConfigManager
from gitminer.github_client import GitHubClient
from gitminer.file_manager import FileManager
from gitminer.pattern_analyzer import PatternAnalyzer
from gitminer.database import DatabaseManager
from gitminer.report_generator import ReportGenerator

__all__ = [
    "ConfigManager",
    "GitHubClient",
    "FileManager",
    "PatternAnalyzer",
    "DatabaseManager",
    "ReportGenerator",
]
