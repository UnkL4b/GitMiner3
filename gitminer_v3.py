#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitMiner v3 - GitHub Secret Scanner and Threat Intelligence Tool

A modular, object-oriented tool for discovering sensitive information
in public GitHub repositories using advanced dork queries and pattern matching.

Author: UnkL4b
Version: 3.0.0

Links:
    - https://unkl4b.github.io
    - https://bravul.com

Usage:
    export GITHUB_TOKEN="your_token_here"
    python3 gitminer_v3.py -d dorks.txt -m 300 --report

Requirements:
    - requests
    - colorama
    - tqdm
    - PyYAML
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from colorama import Fore, Back, init as colorama_init
from tqdm import tqdm

from gitminer import (
    ConfigManager,
    GitHubClient,
    FileManager,
    PatternAnalyzer,
    DatabaseManager,
    ReportGenerator
)
from gitminer.utils import highlight, extract_keyword_from_query

colorama_init(autoreset=True)

BANNER = r"""
   ██ ▄██ ██ ▄▄▄███ ██   ██ ██ ██   ██ ██ ▄██ ██ ▄██
   █▌     █▌   █▌   █▌▌▐▌█▌ █▌ █▌▌  █▌ █▌     █▌   █
   █  ▄▄  █    █    █ ▐▌ █  █  █ ▐▌ █  █ ▄█▌  █ ▄█▌
   ▌   ▐  ▌    ▌    ▌    ▌  ▌  ▌  ▐▌▌  ▌      ▌ ▐▌
   ▌▄▄██  ▌    ▌    ▌    ▌  ▌  ▌    ▌  ▌▄▄██  ▌  ▐
                                                    V3
   GitHub Secret Scanner & Threat Intel Tool
   by @UnkL4b | v3.0.0
"""


class GitMinerApplication:
    """
    Main application class for GitMiner v3.

    Orchestrates the workflow of searching GitHub, downloading files,
    analyzing content, and generating reports.
    """

    def __init__(self, args: argparse.Namespace):
        """
        Initialize the GitMiner application.

        Args:
            args: Parsed command-line arguments
        """
        self.args = args

        self.config = ConfigManager(
            config_dir=args.config_dir,
            labels_file=args.labels_yaml,
            patterns_file=args.patterns_yaml
        )

        self.github_token = self.config.get_github_token()
        if not self.github_token:
            print(highlight(
                "[!] GitHub token not found. Set GITHUB_TOKEN environment "
                "variable or use -t option.",
                Fore.RED
            ))
            sys.exit(1)

        self.github_client = self._initialize_github_client()
        self.file_manager = FileManager(
            base_directory=self.config.get_path('directories', 'raw_files')
        )
        self.pattern_analyzer = PatternAnalyzer(
            patterns=self.config.get_patterns(),
            labels=self.config.get_labels()
        )

        db_path = Path(
            self.config.get_path('directories', 'data')
        ) / self.config.get_path('files', 'database')
        self.database = DatabaseManager(str(db_path))

        self.report_generator = ReportGenerator(
            output_directory=self.config.get_path('directories', 'reports')
        )

        self.dorks = self._load_dorks()

    def _initialize_github_client(self) -> GitHubClient:
        """
        Initialize the GitHub API client with configuration.

        Returns:
            Configured GitHubClient instance
        """
        return GitHubClient(
            token=self.github_token,
            search_url=self.config.get_github_config('search_url'),
            contents_url=self.config.get_github_config('contents_url'),
            rate_limit_url=self.config.get_github_config('rate_limit_url'),
            user_agent=self.config.get_github_config('user_agent'),
            timeout=self.config.get_github_config('timeout')
        )

    def _load_dorks(self) -> List[str]:
        """
        Load dork queries from file or command-line argument.

        Returns:
            List of dork query strings

        Raises:
            SystemExit: If dorks file is invalid or empty
        """
        dorks = []
        dorks_input = self.args.dorks

        if Path(dorks_input).is_file():
            try:
                with open(dorks_input, 'r', encoding='utf-8') as file:
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dorks.append(line)
            except Exception as error:
                print(highlight(
                    f"[!] Error reading dorks file: {error}",
                    Fore.RED
                ))
                sys.exit(1)
        else:
            dorks.append(dorks_input)

        if not dorks:
            print(highlight(
                "[!] No valid dorks found. Check your input file or query.",
                Fore.RED
            ))
            sys.exit(1)

        return dorks

    def run(self) -> None:
        """
        Execute the main application workflow.

        This method orchestrates the entire process: searching, downloading,
        analyzing, and reporting.
        """
        print(highlight(BANNER, Fore.GREEN, bold=True))
        print(highlight(
            f"[INF] Loaded {Fore.YELLOW}{len(self.dorks)}{Fore.CYAN} dork(s)",
            Fore.CYAN, bold=True
        ))

        all_results = []

        for dork in self.dorks:
            print(highlight(
                f"\n[*] Processing dork:\n └➤ {Fore.YELLOW}{dork}{Fore.MAGENTA}\n",
                Fore.MAGENTA,
                bold=True
            ))

            search_results = self.github_client.search_code(
                query=dork,
                per_page=self.args.per_page,
                max_results=self.args.max_results,
                sleep_between_pages=1.0
            )

            searched_at = datetime.now(timezone.utc).isoformat()
            self.database.record_search(
                dork=dork,
                searched_at=searched_at,
                results_count=len(search_results),
                downloaded_count=0
            )

            dork_results = self._process_search_results(
                dork=dork,
                results=search_results,
                searched_at=searched_at
            )

            all_results.extend(dork_results)

        self._display_summary(all_results)

        if self.args.output_csv:
            self._export_csv(all_results)

        if not self.args.no_analyze and all_results:
            self._analyze_files(all_results)

        if self.args.report:
            self._generate_reports(all_results)

        print(highlight(
            "\n[+] GitMiner execution completed successfully!",
            Fore.GREEN,
            bold=True
        ))

    def _process_search_results(
        self,
        dork: str,
        results: List[Dict[str, Any]],
        searched_at: str
    ) -> List[Dict[str, Any]]:
        """
        Process search results: download files and record in database.

        Args:
            dork: The search query used
            results: List of search results
            searched_at: ISO timestamp of the search

        Returns:
            List of processed results with local file paths
        """
        processed_results = []
        keyword = extract_keyword_from_query(dork)

        print(highlight(
            f"[INF] Downloading {Fore.YELLOW}{len(results)}{Fore.RESET} files...",
            Fore.CYAN
        ))

        with tqdm(
            total=len(results),
            desc="Downloading files",
            unit="file"
        ) as progress_bar:

            for result in results:
                repository = result['repository']
                file_path = result['path']

                content = self.github_client.download_file_content(
                    repository=repository,
                    path=file_path
                )

                local_path = None

                if content:
                    local_path = self.file_manager.save_file(
                        content=content,
                        repository=repository,
                        file_path=file_path,
                        dork_keyword=keyword
                    )

                    if local_path:
                        self.database.record_downloaded_file(
                            dork=dork,
                            repository=repository,
                            file_path=file_path,
                            local_path=local_path,
                            item_url=result.get('html_url'),
                            searched_at=searched_at,
                            file_size=len(content)
                        )

                result_record = {
                    'dork': dork,
                    'repository': repository,
                    'path': file_path,
                    'local_path': local_path,
                    'url': result.get('html_url'),
                    'snippet': result.get('snippet', ''),
                    'keyword': keyword
                }

                processed_results.append(result_record)
                progress_bar.update(1)

                time.sleep(0.05)

        return processed_results

    def _display_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        Display execution summary.

        Args:
            results: List of processed results
        """
        total_files = len(results)
        downloaded_files = sum(
            1 for r in results if r.get('local_path')
        )

        print(highlight(
            f"\n[INF] Summary: \n  ├─➤ {Fore.MAGENTA}{total_files}{Fore.RESET} files processed"
            f"\n  └─➤ {Fore.GREEN}{downloaded_files}{Fore.RESET} successfully downloaded",
            Fore.CYAN,
            bold=True
        ))

    def _export_csv(self, results: List[Dict[str, Any]]) -> None:
        """
        Export results to CSV file.

        Args:
            results: List of processed results
        """
        csv_path = self.args.output_csv

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        'dork', 'repository', 'path',
                        'local_path', 'url', 'snippet'
                    ]
                )
                writer.writeheader()

                for result in results:
                    writer.writerow({
                        'dork': result.get('dork', ''),
                        'repository': result.get('repository', ''),
                        'path': result.get('path', ''),
                        'local_path': result.get('local_path', ''),
                        'url': result.get('url', ''),
                        'snippet': result.get('snippet', '')
                    })

            print(highlight(
                f"[+] Results exported to CSV: {csv_path}",
                Fore.GREEN
            ))

        except Exception as error:
            print(highlight(
                f"[!] Error exporting CSV: {error}",
                Fore.RED
            ))

    def _analyze_files(self, results: List[Dict[str, Any]]) -> None:
        """
        Analyze downloaded files for sensitive patterns.

        Args:
            results: List of processed results
        """
        

        grouped = {}
        for result in results:
            dork = result.get('dork', '')
            if dork not in grouped:
                grouped[dork] = []
            grouped[dork].append(result)

        for dork, dork_results in grouped.items():
            keyword = extract_keyword_from_query(dork)

            print(highlight(
                f"\n[+] Results",
                Fore.MAGENTA
            ))

            total_matches = 0

            for result in dork_results:
                local_path = result.get('local_path')

                if not local_path:
                    continue

                keyword_matches = self.pattern_analyzer.search_keyword_in_file(
                    file_path=local_path,
                    keyword=keyword,
                    case_sensitive=False
                )

                pattern_findings = self.pattern_analyzer.scan_file(
                    file_path=local_path
                )

                if keyword_matches or pattern_findings:
                    print(highlight(
                        f"\n[FILE] {local_path}\n",
                        Fore.CYAN,
                        bold=True
                    ))

                    if keyword_matches:
                        for line_no, line_content in keyword_matches[:10]:
                            print(
                                f"{Fore.YELLOW}  >{line_no:5d} | "
                                f"{Fore.BLACK}{Back.WHITE}{line_content}"
                            )
                        total_matches += len(keyword_matches)

                    if pattern_findings:
                        print(highlight(
                            "\n   [INF] Pattern Detection Results:\n",
                            Fore.MAGENTA
                        ))

                        for label, matched, context, line_no in pattern_findings[:10]:
                            severity = self.pattern_analyzer.classify_severity(
                                label
                            )
                            line_display = f">{line_no:5d}" if line_no else ">  ???"

                            print(
                                f"{Fore.RED}   [{severity}] [{label}] "
                                f"{line_display} | {Fore.WHITE}{matched[:80]}"
                            )

                        total_matches += len(pattern_findings)

            if total_matches == 0:
                print(highlight(
                    f"[i] No matches found for '{keyword}' in downloaded files.",
                    Fore.YELLOW
                ))

    def _generate_reports(self, results: List[Dict[str, Any]]) -> None:
        """
        Generate threat intelligence reports.

        Args:
            results: List of processed results
        """
        print(highlight(
            "\n[*] Generating threat intelligence reports...",
            Fore.CYAN,
            bold=True
        ))

        grouped = {}
        for result in results:
            dork = result.get('dork', '')
            if dork not in grouped:
                grouped[dork] = []
            grouped[dork].append(result)

        for dork, dork_results in grouped.items():
            all_findings = []

            for result in dork_results:
                local_path = result.get('local_path')

                if not local_path:
                    continue

                findings = self.pattern_analyzer.scan_file(local_path)

                for label, matched, context, line_no in findings:
                    severity = self.pattern_analyzer.classify_severity(label)

                    finding_tuple = (
                        severity,
                        label,
                        matched,
                        context,
                        line_no,
                        result.get('repository', ''),
                        result.get('path', ''),
                        local_path,
                        result.get('url', '')
                    )

                    all_findings.append(finding_tuple)

            if all_findings:
                self.report_generator.generate_report(
                    dork=dork,
                    results=dork_results,
                    findings=all_findings,
                    database_manager=self.database
                )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog='gitminer_v3',
        description='GitMiner v3 - GitHub Secret Scanner and Threat Intelligence Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search using a single dork
  python3 gitminer_v3.py -d "filename:.env DB_PASSWORD"

  # Search using multiple dorks from file
  python3 gitminer_v3.py -d dorks.txt -m 500 --report

  # Export results to CSV
  python3 gitminer_v3.py -d dorks.txt -o results.csv

  # Skip analysis and only download
  python3 gitminer_v3.py -d dorks.txt --no-analyze

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (required)
        """
    )

    parser.add_argument(
        '-d', '--dorks',
        required=True,
        help='File containing dorks (one per line) or single dork query string'
    )

    parser.add_argument(
        '-t', '--token',
        help='GitHub token (alternatively use GITHUB_TOKEN env variable)'
    )

    parser.add_argument(
        '-m', '--max-results',
        type=int,
        default=200,
        dest='max_results',
        help='Maximum results per dork (default: 200)'
    )

    parser.add_argument(
        '-p', '--per-page',
        type=int,
        default=30,
        dest='per_page',
        help='Results per page for GitHub API (default: 30, max: 100)'
    )

    parser.add_argument(
        '-o', '--output-csv',
        dest='output_csv',
        help='Export results summary to CSV file'
    )

    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate threat intelligence reports in Markdown format'
    )

    parser.add_argument(
        '--no-analyze',
        action='store_true',
        dest='no_analyze',
        help='Skip local file analysis (only download files)'
    )

    parser.add_argument(
        '--config-dir',
        default='config',
        dest='config_dir',
        help='Configuration directory (default: config)'
    )

    parser.add_argument(
        '--labels-yaml',
        dest='labels_yaml',
        help='Custom labels YAML file (overrides default)'
    )

    parser.add_argument(
        '--patterns-yaml',
        dest='patterns_yaml',
        help='Custom patterns YAML file (overrides default)'
    )

    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the application.
    """
    try:
        args = parse_arguments()
        app = GitMinerApplication(args)
        app.run()

    except KeyboardInterrupt:
        print(highlight(
            "\n[!] Execution interrupted by user.",
            Fore.YELLOW
        ))
        sys.exit(0)

    except Exception as error:
        print(highlight(
            f"\n[!] Fatal error: {error}",
            Fore.RED
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
