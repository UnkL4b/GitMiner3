"""
GitHub API Client for GitMiner v3

This module provides a client for interacting with the GitHub API,
including search operations, rate limit management, and content retrieval.
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import requests
from colorama import Fore
from tqdm import tqdm

from gitminer.utils import highlight


class GitHubClient:
    """
    Client for interacting with GitHub's REST API.
    
    Handles authentication, rate limiting, search operations,
    and content retrieval with automatic retry logic.
    """

    def __init__(
        self,
        token: str,
        search_url: str,
        contents_url: str,
        rate_limit_url: str,
        user_agent: str = "GitMiner-v3",
        timeout: int = 60
    ):
        """
        Initialize the GitHub API client.

        Args:
            token: GitHub personal access token
            search_url: URL for code search API endpoint
            contents_url: URL template for contents API endpoint
            rate_limit_url: URL for rate limit API endpoint
            user_agent: User agent string for API requests
            timeout: Request timeout in seconds
        """
        self.token = token
        self.search_url = search_url
        self.contents_url = contents_url
        self.rate_limit_url = rate_limit_url
        self.user_agent = user_agent
        self.timeout = timeout
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": user_agent
        }

    def get_rate_limits(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current rate limit status from GitHub API.

        Returns:
            Dictionary containing rate limit information for different
            resource types, or None if the request fails
        """
        try:
            response = requests.get(
                self.rate_limit_url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("resources", {})
            else:
                print(highlight(
                    f"[!] Error fetching rate limits: "
                    f"{response.status_code} - {response.text[:200]}",
                    Fore.YELLOW
                ))
                return None
                
        except Exception as error:
            print(highlight(
                f"[!] Exception while fetching rate limits: {error}",
                Fore.YELLOW
            ))
            return None

    def ensure_rate_limit(
        self,
        needed: int = 1,
        prefer_code_search: bool = True
    ) -> None:
        """
        Ensure sufficient rate limit quota before making API requests.
        
        This method checks the current rate limit and waits if necessary
        to avoid hitting rate limit errors.

        Args:
            needed: Number of API calls needed
            prefer_code_search: Whether to prefer code_search quota
        """
        resources = self.get_rate_limits()
        
        if not resources:
            print(highlight(
                "[i] Cannot check rate limits; applying conservative 5s wait.",
                Fore.YELLOW
            ))
            time.sleep(5)
            return
        
        candidates = []
        if prefer_code_search and "code_search" in resources:
            candidates.append(("code_search", resources["code_search"]))
        if "search" in resources:
            candidates.append(("search", resources["search"]))
        if not candidates and "core" in resources:
            candidates.append(("core", resources["core"]))
        
        for resource_name, resource_info in candidates:
            remaining = resource_info.get("remaining", 0)
            reset_timestamp = resource_info.get("reset", 0)
            
            if remaining >= needed:
                return
            else:
                wait_seconds = max(
                    0,
                    int(reset_timestamp) - int(time.time()) + 1
                )
                reset_iso = datetime.fromtimestamp(
                    int(reset_timestamp),
                    timezone.utc
                ).isoformat()
                
                print(highlight(
                    f"[!] Quota '{resource_name}' insufficient "
                    f"({remaining} < {needed}). "
                    f"Reset at {reset_iso}. Waiting {wait_seconds}s...",
                    Fore.YELLOW
                ))
                time.sleep(wait_seconds)
                return

    def search_code(
        self,
        query: str,
        per_page: int = 30,
        max_results: int = 200,
        sleep_between_pages: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Search for code on GitHub using a dork query.

        Args:
            query: GitHub search query (dork)
            per_page: Results per page (max 100)
            max_results: Maximum total results to retrieve
            sleep_between_pages: Seconds to sleep between page requests

        Returns:
            List of search result items with metadata

        Raises:
            RuntimeError: If API returns non-recoverable error
        """
        page = 1
        results = []
        
        print(highlight(
            f"[+] Executing dork: {query}",
            Fore.GREEN,
            bold=True
        ))
        
        search_headers = self.headers.copy()
        search_headers["Accept"] = "application/vnd.github.text-match+json"
        
        with tqdm(
            total=max_results,
            desc="Searching (GitHub API)",
            unit="items",
            leave=False
        ) as progress_bar:
            
            while len(results) < max_results:
                self.ensure_rate_limit(needed=1, prefer_code_search=True)
                
                params = {
                    "q": query,
                    "per_page": per_page,
                    "page": page
                }
                
                try:
                    response = requests.get(
                        self.search_url,
                        headers=search_headers,
                        params=params,
                        timeout=self.timeout
                    )
                except Exception as error:
                    print(highlight(
                        f"[!] Exception during search: {error}",
                        Fore.RED
                    ))
                    break
                
                self._display_rate_limit_info(response)
                
                if response.status_code == 403:
                    self._handle_rate_limit_error(response)
                    continue
                
                if response.status_code != 200:
                    raise RuntimeError(
                        f"GitHub API error {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                for item in items:
                    if len(results) >= max_results:
                        break
                    
                    snippet = self._extract_snippet(item)
                    
                    result_item = {
                        "repository": item["repository"]["full_name"],
                        "path": item["path"],
                        "html_url": item.get("html_url") or item.get("url"),
                        "snippet": snippet,
                        "sha": item.get("sha", ""),
                        "score": item.get("score", 0)
                    }
                    
                    results.append(result_item)
                    progress_bar.update(1)
                
                if len(items) < per_page:
                    break
                
                page += 1
                time.sleep(sleep_between_pages)
        
        print(highlight(
            f"[+] Found {len(results)} results for query",
            Fore.GREEN
        ))
        
        return results

    def _extract_snippet(self, item: Dict[str, Any]) -> str:
        """
        Extract code snippet from search result item.

        Args:
            item: Search result item from GitHub API

        Returns:
            Extracted snippet or empty string
        """
        text_matches = item.get("text_matches", [])
        if text_matches:
            fragments = text_matches[0].get("matches", [])
            if fragments:
                return fragments[0].get("text", "")
        return ""

    def _display_rate_limit_info(self, response: requests.Response) -> None:
        """
        Display rate limit information from response headers.

        Args:
            response: HTTP response object
        """
        try:
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            
            if remaining is not None and reset is not None:
                reset_iso = datetime.fromtimestamp(
                    int(reset),
                    timezone.utc
                ).isoformat()
                print(highlight(
                    f"[i] Rate limit remaining: {remaining} | "
                    f"Reset: {reset_iso}",
                    Fore.BLUE
                ))
        except Exception:
            pass

    def _handle_rate_limit_error(self, response: requests.Response) -> None:
        """
        Handle 403 rate limit errors with appropriate waiting.

        Args:
            response: HTTP response object with 403 status

        Raises:
            RuntimeError: If unable to determine reset time
        """
        reset = response.headers.get("X-RateLimit-Reset")
        
        if reset:
            reset_timestamp = int(reset)
            wait_seconds = max(10, reset_timestamp - int(time.time()) + 1)
            reset_iso = datetime.fromtimestamp(
                reset_timestamp,
                timezone.utc
            ).isoformat()
            
            print(highlight(
                f"[!] 403 - Rate limit exceeded. "
                f"Waiting {wait_seconds}s until reset ({reset_iso})...",
                Fore.YELLOW
            ))
            time.sleep(wait_seconds)
        else:
            resources = self.get_rate_limits()
            if resources and "search" in resources:
                info = resources["search"]
                reset_timestamp = info.get("reset", 0)
                wait_seconds = max(10, int(reset_timestamp) - int(time.time()) + 1)
                
                print(highlight(
                    f"[!] 403 received. Waiting {wait_seconds}s...",
                    Fore.YELLOW
                ))
                time.sleep(wait_seconds)
            else:
                raise RuntimeError(
                    "403 Forbidden - check token permissions and rate limit"
                )

    def download_file_content(
        self,
        repository: str,
        path: str
    ) -> Optional[bytes]:
        """
        Download raw file content from a GitHub repository.

        Args:
            repository: Full repository name (owner/repo)
            path: File path within the repository

        Returns:
            Raw file content as bytes, or None if download fails
        """
        url = self.contents_url.format(repo=repository, path=path)
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                download_url = data.get("download_url")
                
                if download_url:
                    content_response = requests.get(
                        download_url,
                        timeout=self.timeout
                    )
                    if content_response.status_code == 200:
                        return content_response.content
            
            print(highlight(
                f"[!] Failed to download {repository}/{path}: "
                f"Status {response.status_code}",
                Fore.YELLOW
            ))
            return None
            
        except Exception as error:
            print(highlight(
                f"[!] Exception downloading {repository}/{path}: {error}",
                Fore.RED
            ))
            return None
