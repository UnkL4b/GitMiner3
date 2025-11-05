"""
Utility functions for GitMiner v3

This module provides common utility functions used throughout the application,
including text formatting, file sanitization, and query parsing.
"""

import re
import unicodedata
from typing import Optional

from colorama import Fore, Style


def highlight(text: str, color: str = Fore.CYAN, bold: bool = False) -> str:
    """
    Apply color and style formatting to text for terminal output.

    Args:
        text: The text to format
        color: Colorama color constant (default: Fore.CYAN)
        bold: Whether to apply bold styling (default: False)

    Returns:
        Formatted text string with ANSI color codes
    """
    if bold:
        return Style.BRIGHT + color + text + Style.RESET_ALL
    return color + text + Style.RESET_ALL


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    This function normalizes Unicode characters and replaces characters
    that are invalid in filenames across different operating systems.

    Args:
        filename: The original filename to sanitize

    Returns:
        Sanitized filename safe for use across platforms
    """
    filename = unicodedata.normalize('NFKD', filename)

    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    filename = filename.replace('..', '_')

    return filename


def extract_keyword_from_query(query: str) -> str:
    """
    Extract the primary keyword from a GitHub dork query.

    This function attempts to identify the most relevant search term
    from a dork query by checking for specific patterns like filename,
    extension, quoted strings, or significant tokens.

    Args:
        query: The GitHub dork query string

    Returns:
        Extracted keyword or the original query if no pattern matches
    """
    match = re.search(
        r'filename\s*:\s*([^\s]+)',
        query,
        flags=re.IGNORECASE
    )
    if match:
        return match.group(1).strip().strip('"\'')

    match = re.search(
        r'extension\s*:\s*([^\s]+)',
        query,
        flags=re.IGNORECASE
    )
    if match:
        return match.group(1).strip().strip('"\'')

    match = re.search(r'"([^"]{2,100})"', query)
    if match:
        return match.group(1)

    tokens = re.split(r'\s+', query)

    tokens = [
        token for token in tokens
        if not re.match(
            r'^(OR|and|AND|\||\(|\)|-)$',
            token,
            flags=re.IGNORECASE
        )
    ]
    tokens = [token for token in tokens if len(token) >= 3]

    return tokens[0] if tokens else query


def slugify(text: str, max_length: int = 50) -> str:
    """
    Convert text to a slug suitable for filenames.

    Args:
        text: The text to convert
        max_length: Maximum length of the resulting slug (default: 50)

    Returns:
        Slugified text with only alphanumeric characters, hyphens, and underscores
    """
    slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', text)
    return slug[:max_length]


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if needed.

    Args:
        text: The text to truncate
        max_length: Maximum length before truncation (default: 100)

    Returns:
        Truncated text with ellipsis if it exceeded max_length
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_bytes(size_bytes: int) -> str:
    """
    Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string with appropriate unit (B, KB, MB, GB)
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
