"""
Report Generator for GitMiner v3

This module generates comprehensive threat intelligence reports
in Markdown format from scan results.
"""

import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

from colorama import Fore

from gitminer.utils import highlight, slugify


class ReportGenerator:
    """
    Generates threat intelligence reports from scan results.
    
    Creates detailed Markdown reports with executive summaries,
    technical analysis, and organized findings by severity.
    """

    def __init__(self, output_directory: str = "reports"):
        """
        Initialize the report generator.

        Args:
            output_directory: Directory for saving generated reports
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        dork: str,
        results: List[Dict[str, Any]],
        findings: List[Tuple[str, str, str, str, str, str, str, str]],
        database_manager: Any
    ) -> str:
        """
        Generate a comprehensive threat intelligence report.

        Args:
            dork: The search query used
            results: List of search results
            findings: List of findings with structure:
                (severity, label, matched_text, context, line_number,
                 repository, file_path, local_path, url)
            database_manager: DatabaseManager instance for metadata

        Returns:
            Path to the generated report file
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        dork_slug = slugify(dork)
        report_filename = f"report_{dork_slug}_{timestamp}.md"
        report_path = self.output_directory / report_filename
        
        sections = []
        sections.append(self._generate_header(dork))
        sections.append(self._generate_index())
        sections.append(
            self._generate_executive_summary(dork, results, findings)
        )
        sections.append(self._generate_severity_tables(findings))
        sections.append(self._generate_technical_analysis(findings))
        sections.append(self._generate_metadata())
        
        report_content = "\n".join(sections)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as file:
                file.write(report_content)
            
            print(highlight(
                f"[+] Threat intelligence report generated: {report_path}",
                Fore.GREEN
            ))
            
            return str(report_path)
            
        except Exception as error:
            print(highlight(
                f"[!] Error generating report: {error}",
                Fore.RED
            ))
            return ""

    def _generate_header(self, dork: str) -> str:
        """
        Generate report header section.

        Args:
            dork: The search query

        Returns:
            Markdown formatted header
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        lines = [
            f"# Threat Intelligence Report — Dork: `{dork}`",
            "",
            f"**Date:** {now_str}",
            f"**Tool:** GitMiner v3.0.0",
            f"**Query:** `{dork}`",
            "",
            "---",
            ""
        ]
        
        return "\n".join(lines)

    def _generate_index(self) -> str:
        """
        Generate table of contents.

        Returns:
            Markdown formatted index
        """
        lines = [
            "## 📖 Table of Contents",
            "",
            "- [Executive Summary](#executive-summary)",
            "- [Findings by Severity](#findings-by-severity)",
            "  - [HIGH Severity](#high-severity)",
            "  - [MEDIUM Severity](#medium-severity)",
            "  - [LOW Severity](#low-severity)",
            "- [Technical Analysis](#technical-analysis)",
            "- [Recommendations](#recommendations)",
            "- [Metadata](#metadata)",
            "",
            "---",
            ""
        ]
        
        return "\n".join(lines)

    def _generate_executive_summary(
        self,
        dork: str,
        results: List[Dict[str, Any]],
        findings: List[Tuple]
    ) -> str:
        """
        Generate executive summary section.

        Args:
            dork: The search query
            results: Search results
            findings: List of findings

        Returns:
            Markdown formatted executive summary
        """
        lines = [
            "## 🧭 Executive Summary",
            ""
        ]
        
        repositories = set()
        for finding in findings:
            if len(finding) > 5:
                repositories.add(finding[5])
        
        total_findings = len(findings)
        total_repos = len(repositories)
        
        lines.append(
            f"The search query `{dork}` identified **{total_findings} "
            f"potential exposures** across **{total_repos} public repositories**."
        )
        lines.append("")
        
        if findings:
            severity_counter = Counter([f[0] for f in findings])
            
            if severity_counter:
                lines.append("### Severity Distribution")
                lines.append("")
                
                for severity in ["HIGH", "MEDIUM", "LOW"]:
                    count = severity_counter.get(severity, 0)
                    if count > 0:
                        lines.append(f"- **{severity}**: {count} findings")
                
                lines.append("")
        
        if findings:
            label_counter = Counter([f[1] for f in findings])
            
            if label_counter:
                lines.append("### Top Finding Types")
                lines.append("")
                
                for label, count in label_counter.most_common(10):
                    lines.append(f"- **{label}**: {count} occurrences")
                
                lines.append("")
        
        if repositories:
            lines.append("### Affected Repositories")
            lines.append("")
            
            repo_findings = {}
            for finding in findings:
                if len(finding) > 5:
                    repo = finding[5]
                    repo_findings[repo] = repo_findings.get(repo, 0) + 1
            
            lines.append("| Repository | Findings |")
            lines.append("|:-----------|----------:|")
            
            for repo, count in sorted(
                repo_findings.items(),
                key=lambda x: -x[1]
            )[:20]:
                lines.append(f"| `{repo}` | {count} |")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return "\n".join(lines)

    def _generate_severity_tables(
        self,
        findings: List[Tuple]
    ) -> str:
        """
        Generate findings tables organized by severity.

        Args:
            findings: List of findings

        Returns:
            Markdown formatted severity tables
        """
        lines = [
            "## 🧨 Findings by Severity",
            ""
        ]
        
        for severity in ["HIGH", "MEDIUM", "LOW"]:
            lines.append(f"### {severity} Severity")
            lines.append("")
            
            severity_findings = [f for f in findings if f[0] == severity]
            
            if not severity_findings:
                lines.append(f"No {severity} severity findings detected.")
                lines.append("")
                continue
            
            label_counter = Counter([f[1] for f in severity_findings])
            
            lines.append("| Finding Type | Count | Sample Matches |")
            lines.append("|:-------------|------:|:---------------|")
            
            for label, count in label_counter.most_common(50):
                samples = [
                    f[2] for f in severity_findings if f[1] == label
                ][:3]
                
                clean_samples = []
                for sample in samples:
                    clean = sample.replace('`', "'").replace('|', '\\|')
                    if len(clean) > 40:
                        clean = clean[:40] + "..."
                    clean_samples.append(clean)
                
                samples_str = ", ".join(clean_samples)
                
                lines.append(f"| **{label}** | {count} | `{samples_str}` |")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return "\n".join(lines)

    def _generate_technical_analysis(
        self,
        findings: List[Tuple]
    ) -> str:
        """
        Generate detailed technical analysis section.

        Args:
            findings: List of findings

        Returns:
            Markdown formatted technical analysis
        """
        lines = [
            "## ⚙️ Technical Analysis",
            ""
        ]
        
        if not findings:
            lines.append("> No findings to analyze.")
            lines.append("")
            return "\n".join(lines)
        
        by_repo_file = {}
        
        for finding in findings:
            if len(finding) >= 8:
                severity, label, matched, context, line_no, repo, path, local = finding[:8]
                url = finding[8] if len(finding) > 8 else ""
                
                key = (repo, path, url, local)
                if key not in by_repo_file:
                    by_repo_file[key] = []
                
                by_repo_file[key].append(
                    (severity, label, matched, context, line_no)
                )
        
        sorted_files = sorted(
            by_repo_file.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for (repo, path, url, local_path), file_findings in sorted_files[:50]:
            lines.append(f"### Repository: `{repo}`")
            lines.append("")
            lines.append(f"**File:** `{path}`")
            
            if url:
                lines.append(f"**URL:** [{url}]({url})")
            
            if local_path:
                lines.append(f"**Local Path:** `{local_path}`")
            
            lines.append("")
            lines.append(f"**Total Findings:** {len(file_findings)}")
            lines.append("")
            
            for severity, label, matched, context, line_no in file_findings[:10]:
                line_display = f"Line {line_no}" if line_no else "Unknown line"
                
                matched_display = matched[:100]
                if len(matched) > 100:
                    matched_display += "..."
                
                lines.append(
                    f"- **{severity}** | `{label}` | {line_display}"
                )
                lines.append(f"  - Match: `{matched_display}`")
                
                if context:
                    context_display = context[:200]
                    if len(context) > 200:
                        context_display += "..."
                    lines.append(f"  - Context: `{context_display}`")
                
                lines.append("")
            
            if len(file_findings) > 10:
                remaining = len(file_findings) - 10
                lines.append(
                    f"*... and {remaining} more findings in this file*"
                )
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        if len(sorted_files) > 50:
            remaining_files = len(sorted_files) - 50
            lines.append(
                f"*Note: {remaining_files} additional files with findings "
                "not shown in this report.*"
            )
            lines.append("")
        
        return "\n".join(lines)

    def _generate_recommendations(self) -> str:
        """
        Generate security recommendations section.

        Returns:
            Markdown formatted recommendations
        """
        lines = [
            "## 🛡️ Recommendations",
            "",
            "### Immediate Actions",
            "",
            "1. **Rotate Exposed Credentials**: All exposed API keys, "
            "tokens, and passwords should be rotated immediately.",
            "",
            "2. **Remove Sensitive Files**: Delete or sanitize files "
            "containing sensitive information from repositories.",
            "",
            "3. **Review Access Logs**: Check for unauthorized access "
            "using the exposed credentials.",
            "",
            "### Long-term Measures",
            "",
            "1. **Enable Secret Scanning**: Activate GitHub's secret "
            "scanning feature for all repositories.",
            "",
            "2. **Implement Pre-commit Hooks**: Use tools like "
            "`git-secrets` or `detect-secrets` to prevent commits "
            "containing secrets.",
            "",
            "3. **Use Environment Variables**: Store sensitive "
            "configuration in environment variables, not in code.",
            "",
            "4. **Conduct Security Training**: Educate developers on "
            "secure coding practices and secret management.",
            "",
            "5. **Regular Audits**: Perform periodic security audits "
            "of repositories to identify potential exposures.",
            "",
            "---",
            ""
        ]
        
        return "\n".join(lines)

    def _generate_metadata(self) -> str:
        """
        Generate report metadata section.

        Returns:
            Markdown formatted metadata
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        user = os.getenv('USER', 'N/A')
        
        lines = [
            "## 🧾 Metadata",
            "",
            f"- **Generated:** {now_str}",
            f"- **Tool Version:** GitMiner v3.0.0",
            f"- **User:** {user}",
            f"- **Database:** gitminer_history.sqlite",
            "",
            "---",
            "",
            "*Report generated by GitMiner v3 - "
            "GitHub Secret Scanner and Threat Intelligence Tool*",
            ""
        ]
        
        return "\n".join(lines)
