"""
Pattern Analyzer for GitMiner v3

This module provides pattern matching and analysis capabilities
for detecting sensitive information in files.
"""

import re
from typing import List, Tuple, Dict, Optional

from colorama import Fore

from gitminer.utils import highlight


class PatternAnalyzer:
    """
    Analyzes files for sensitive patterns using regex matching.
    
    Scans file content for credentials, API keys, tokens, and other
    sensitive information using configurable regex patterns.
    """

    def __init__(
        self,
        patterns: Dict[str, re.Pattern],
        labels: Dict[str, str]
    ):
        """
        Initialize the pattern analyzer.

        Args:
            patterns: Dictionary mapping pattern names to compiled regex
            labels: Dictionary mapping regex strings to label names
        """
        self.patterns = patterns
        self.labels = labels
        
        self.compiled_labels = {
            re.compile(pattern): label
            for pattern, label in labels.items()
        }

    def scan_file(
        self,
        file_path: str,
        max_context_length: int = 500
    ) -> List[Tuple[str, str, str, Optional[int]]]:
        """
        Scan a file for sensitive patterns.

        Args:
            file_path: Path to the file to scan
            max_context_length: Maximum length of context to extract

        Returns:
            List of tuples containing:
            (label, matched_text, context, line_number)
        """
        findings = []
        
        try:
            with open(file_path, 'rb') as file:
                raw_content = file.read()
            
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                content = raw_content.decode('latin-1', errors='ignore')
            
            lines = content.splitlines()
            
            findings.extend(
                self._scan_with_patterns(lines, max_context_length)
            )
            
            findings.extend(
                self._scan_with_labels(lines, max_context_length)
            )
            
        except Exception as error:
            print(highlight(
                f"[!] Error scanning file {file_path}: {error}",
                Fore.RED
            ))
        
        return findings

    def _scan_with_patterns(
        self,
        lines: List[str],
        max_context_length: int
    ) -> List[Tuple[str, str, str, Optional[int]]]:
        """
        Scan lines using compiled regex patterns.

        Args:
            lines: List of text lines to scan
            max_context_length: Maximum context length

        Returns:
            List of findings
        """
        findings = []
        
        for pattern_name, pattern in self.patterns.items():
            for line_number, line in enumerate(lines, start=1):
                matches = pattern.finditer(line)
                
                for match in matches:
                    matched_text = match.group(0)
                    context = line.strip()[:max_context_length]
                    
                    findings.append((
                        pattern_name,
                        matched_text,
                        context,
                        line_number
                    ))
        
        return findings

    def _scan_with_labels(
        self,
        lines: List[str],
        max_context_length: int
    ) -> List[Tuple[str, str, str, Optional[int]]]:
        """
        Scan lines using label patterns for parameter detection.

        Args:
            lines: List of text lines to scan
            max_context_length: Maximum context length

        Returns:
            List of findings
        """
        findings = []
        
        for line_number, line in enumerate(lines, start=1):
            for pattern, label in self.compiled_labels.items():
                matches = pattern.finditer(line)
                
                for match in matches:
                    matched_text = match.group(0)
                    context = line.strip()[:max_context_length]
                    
                    value = self._extract_parameter_value(
                        line,
                        match.end()
                    )
                    
                    if value:
                        matched_text = f"{matched_text}={value}"
                    
                    findings.append((
                        label,
                        matched_text,
                        context,
                        line_number
                    ))
        
        return findings

    def _extract_parameter_value(
        self,
        line: str,
        start_pos: int,
        max_length: int = 100
    ) -> Optional[str]:
        """
        Extract the value assigned to a parameter.

        Attempts to extract the value following a parameter name,
        handling various assignment patterns (=, :, etc.).

        Args:
            line: The line containing the parameter
            start_pos: Position after the parameter name
            max_length: Maximum length of value to extract

        Returns:
            Extracted value or None
        """
        remaining = line[start_pos:].lstrip()
        
        if not remaining:
            return None
        
        assignment_pattern = re.match(
            r'^[\s:=]+["\']?([^"\'\s;,#]+)["\']?',
            remaining
        )
        
        if assignment_pattern:
            value = assignment_pattern.group(1)
            return value[:max_length] if value else None
        
        return None

    def classify_severity(self, label: str) -> str:
        """
        Classify the severity level of a finding based on its label.

        Args:
            label: The label/pattern name of the finding

        Returns:
            Severity level: "HIGH", "MEDIUM", or "LOW"
        """
        label_upper = (label or "").upper()
        
        high_indicators = [
            "PRIVATE", "SECRET", "AWS", "TOKEN",
            "SSH_PRIVATE_KEY", "PRIVATE_KEY", "CERTIFICATE"
        ]
        
        if any(indicator in label_upper for indicator in high_indicators):
            return "HIGH"
        
        medium_indicators = [
            "PASSWORD", "PASS", "JWT", "API",
            "GITHUB_TOKEN", "ACCESS_KEY", "OAUTH"
        ]
        
        if any(indicator in label_upper for indicator in medium_indicators):
            return "MEDIUM"
        
        return "LOW"

    def search_keyword_in_file(
        self,
        file_path: str,
        keyword: str,
        case_sensitive: bool = False
    ) -> List[Tuple[int, str]]:
        """
        Search for a specific keyword in a file.

        Args:
            file_path: Path to the file to search
            keyword: Keyword to search for
            case_sensitive: Whether the search is case-sensitive

        Returns:
            List of tuples containing (line_number, line_content)
        """
        matches = []
        
        try:
            with open(file_path, 'rb') as file:
                raw_content = file.read()
            
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                content = raw_content.decode('latin-1', errors='ignore')
            
            lines = content.splitlines()
            
            for line_number, line in enumerate(lines, start=1):
                if case_sensitive:
                    if keyword in line:
                        matches.append((line_number, line.strip()))
                else:
                    if keyword.lower() in line.lower():
                        matches.append((line_number, line.strip()))
                        
        except Exception as error:
            print(highlight(
                f"[!] Error searching file {file_path}: {error}",
                Fore.RED
            ))
        
        return matches

    def get_statistics(
        self,
        findings: List[Tuple[str, str, str, Optional[int]]]
    ) -> Dict[str, any]:
        """
        Generate statistics from a list of findings.

        Args:
            findings: List of findings from scan_file

        Returns:
            Dictionary containing statistics
        """
        from collections import Counter
        
        labels = [finding[0] for finding in findings]
        severities = [
            self.classify_severity(label)
            for label in labels
        ]
        
        return {
            "total_findings": len(findings),
            "unique_labels": len(set(labels)),
            "label_counts": dict(Counter(labels)),
            "severity_counts": dict(Counter(severities)),
            "high_severity_count": severities.count("HIGH"),
            "medium_severity_count": severities.count("MEDIUM"),
            "low_severity_count": severities.count("LOW")
        }
