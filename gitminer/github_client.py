"""
GitHub API Client for GitMiner v3

Implements real-time progress updates, rate-limit awareness,
and dynamic wait countdowns inside tqdm progress bar.
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import requests
from colorama import Fore, Style
from tqdm import tqdm

from gitminer.utils import highlight


class GitHubClient:
    """
    Client for interacting with GitHub's REST API.

    Handles authentication, rate limiting, search operations,
    and content retrieval with automatic retry logic.
    """

    def __init__(self, token: str, search_url: str, contents_url: str, rate_limit_url: str, user_agent: str = "GitMiner-v3", timeout: int = 60):
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

    def ensure_rate_limit(self, needed: int = 1, prefer_code_search: bool = True) -> None:
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
                wait_seconds = max(0, int(reset_timestamp) - int(time.time()) + 1)
                reset_iso = datetime.fromtimestamp(
                    int(reset_timestamp), timezone.utc
                ).isoformat()
                print(highlight(
                    f"[!] Quota '{resource_name}' insufficient "
                    f"({remaining} < {needed}). Reset at {reset_iso}. Waiting {wait_seconds}s...",
                    Fore.YELLOW
                ))
                time.sleep(wait_seconds)
                return

    def search_code(self, query: str, per_page: int = 30, max_results: int = 200, sleep_between_pages: float = 1.0) -> List[Dict[str, Any]]:
        page = 1
        results = []
        search_headers = self.headers.copy()
        search_headers["Accept"] = "application/vnd.github.text-match+json"

        with tqdm(total=max_results, desc="Searching (GitHub API)", unit="items", leave=False) as progress_bar:

            while len(results) < max_results:
                self.ensure_rate_limit(needed=1, prefer_code_search=True)
                params = {"q": query, "per_page": per_page, "page": page}

                try:
                    response = requests.get(
                        self.search_url,
                        headers=search_headers,
                        params=params,
                        timeout=self.timeout
                    )
                except Exception as error:
                    print(highlight(f"[!] Exception during search: {error}", Fore.RED))
                    break

                self._display_rate_limit_info(response, progress_bar)

                if response.status_code == 403:
                    self._handle_rate_limit_error(response, progress_bar)
                    continue

                if response.status_code != 200:
                    raise RuntimeError(
                        f"GitHub API error {response.status_code}: {response.text[:200]}"
                    )

                data = response.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    if len(results) >= max_results:
                        break
                    snippet = self._extract_snippet(item)
                    results.append({
                        "repository": item["repository"]["full_name"],
                        "path": item["path"],
                        "html_url": item.get("html_url") or item.get("url"),
                        "snippet": snippet,
                        "sha": item.get("sha", ""),
                        "score": item.get("score", 0)
                    })
                    progress_bar.update(1)

                if len(items) < per_page:
                    break

                page += 1
                time.sleep(sleep_between_pages)

        print(highlight(f"[+] Found {len(results)} results for query", Fore.GREEN))
        return results

    def _extract_snippet(self, item: Dict[str, Any]) -> str:
        text_matches = item.get("text_matches", [])
        if text_matches:
            fragments = text_matches[0].get("matches", [])
            if fragments:
                return fragments[0].get("text", "")
        return ""

    def _display_rate_limit_info(self, response: requests.Response, progress_bar: Optional[tqdm] = None) -> None:
        try:
            remaining = response.headers.get("X-RateLimit-Remaining")
            limit = response.headers.get("X-RateLimit-Limit")
            reset = response.headers.get("X-RateLimit-Reset")

            if remaining and reset:
                reset_ts = int(reset)
                now_ts = int(time.time())
                diff = max(0, reset_ts - now_ts)
                mins, secs = divmod(diff, 60)
                reset_iso = datetime.fromtimestamp(reset_ts, timezone.utc).strftime("%H:%M:%S")
                info = (
                    f"Rate limit: {Style.BRIGHT}{Fore.BLUE}{remaining}{Style.RESET_ALL}/{Style.BRIGHT}{Fore.GREEN}{limit}{Style.RESET_ALL} | Reset in: {mins}m {secs}s ({reset_iso} UTC)"
                )
                if progress_bar:
                    progress_bar.set_description(f"Searching (GitHub API) | {info}")
                else:
                    print(highlight(f"[i] {info}", Fore.BLUE))
        except Exception:
            pass

    def _handle_rate_limit_error(self, response: requests.Response, progress_bar: Optional[tqdm] = None) -> None:
        reset = response.headers.get("X-RateLimit-Reset")
        if not reset:
            print(highlight("[!] 403 Forbidden - no reset header found.", Fore.YELLOW))
            time.sleep(10)
            return

        reset_ts = int(reset)
        wait_seconds = max(10, reset_ts - int(time.time()) + 1)
        reset_iso = datetime.fromtimestamp(reset_ts, timezone.utc).strftime("%H:%M:%S")

        msg = f"Rate limit exceeded. Waiting {Fore.YELLOW}{wait_seconds}{Fore.RESET}s until reset ({reset_iso} UTC)"
        
        if progress_bar:
            for remaining in range(wait_seconds, 0, -1):
                progress_bar.set_description(
                    f"Waiting for rate limit reset ({Style.BRIGHT}{Fore.YELLOW}{remaining}{Style.RESET_ALL}s left)"
                )
                time.sleep(1)
        else:
            for remaining in range(wait_seconds, 0, -1):
                print(f"\r[Waiting] {remaining}s until reset...", end="", flush=True)
                time.sleep(1)
            print()

    def download_file_content(self, repository: str, path: str) -> Optional[bytes]:
        url = self.contents_url.format(repo=repository, path=path)
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                download_url = data.get("download_url")
                if download_url:
                    content_response = requests.get(download_url, timeout=self.timeout)
                    if content_response.status_code == 200:
                        return content_response.content

            print(highlight(
                f"[!] Failed to download {repository}/{path}: Status {response.status_code}",
                Fore.YELLOW
            ))
            return None
        except Exception as error:
            print(highlight(
                f"[!] Exception downloading {repository}/{path}: {error}",
                Fore.RED
            ))
            return None
