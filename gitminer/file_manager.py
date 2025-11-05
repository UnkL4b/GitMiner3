"""
File Manager for GitMiner v3

This module handles file operations including downloading, saving,
and organizing files retrieved from GitHub repositories.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from colorama import Fore

from gitminer.utils import highlight, sanitize_filename


class FileManager:
    """
    Manages file operations for downloaded content.

    Handles directory structure creation, file naming, and saving
    downloaded content with proper organization.
    """

    def __init__(self, base_directory: str = "raw"):
        """
        Initialize the file manager.

        Args:
            base_directory: Base directory for storing downloaded files
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, repository: str, file_path: str, dork_keyword: str) -> Optional[str]:
        """
        Save file content to disk with organized directory structure.

        Creates a directory structure based on the dork keyword and
        repository name to keep files organized.

        Args:
            content: Raw file content as bytes
            repository: Full repository name (owner/repo)
            file_path: Original file path in the repository
            dork_keyword: Keyword extracted from the dork query

        Returns:
            Local file path where content was saved, or None if save failed
        """
        try:
            safe_keyword = sanitize_filename(dork_keyword)
            safe_repo = sanitize_filename(repository.replace('/', '_'))

            target_dir = self.base_directory / safe_keyword / safe_repo
            target_dir.mkdir(parents=True, exist_ok=True)

            filename = Path(file_path).name
            safe_filename = sanitize_filename(filename)

            if not safe_filename or safe_filename == '_':
                safe_filename = sanitize_filename(
                    file_path.replace('/', '_')
                )

            target_path = target_dir / safe_filename

            if target_path.exists():
                counter = 1
                stem = target_path.stem
                suffix = target_path.suffix

                while target_path.exists():
                    new_name = f"{stem}_{counter}{suffix}"
                    target_path = target_dir / new_name
                    counter += 1

            with open(target_path, 'wb') as file:
                file.write(content)

            return str(target_path)

        except Exception as error:
            print(highlight(
                f"[!] Error saving file {file_path}: {error}",
                Fore.RED
            ))
            return None

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a saved file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing file metadata (size, modification time, etc.)
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return {"exists": False}

            stat = path.stat()

            return {
                "exists": True,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_file": path.is_file(),
                "absolute_path": str(path.absolute())
            }

        except Exception as error:
            return {
                "exists": False,
                "error": str(error)
            }

    def read_file(self, file_path: str, encoding: str = 'utf-8', fallback_encoding: str = 'latin-1') -> Optional[str]:
        """
        Read file content as text with encoding fallback.

        Args:
            file_path: Path to the file to read
            encoding: Primary encoding to try (default: utf-8)
            fallback_encoding: Fallback encoding if primary fails

        Returns:
            File content as string, or None if read fails
        """
        try:
            with open(file_path, 'rb') as file:
                raw_content = file.read()

            try:
                return raw_content.decode(encoding)
            except UnicodeDecodeError:
                return raw_content.decode(fallback_encoding, errors='ignore')

        except Exception as error:
            print(highlight(
                f"[!] Error reading file {file_path}: {error}",
                Fore.RED
            ))
            return None

    def list_saved_files(self, dork_keyword: Optional[str] = None) -> list:
        """
        List all saved files, optionally filtered by dork keyword.

        Args:
            dork_keyword: Optional keyword to filter results

        Returns:
            List of file paths
        """
        files = []

        try:
            if dork_keyword:
                safe_keyword = sanitize_filename(dork_keyword)
                search_dir = self.base_directory / safe_keyword
            else:
                search_dir = self.base_directory

            if search_dir.exists():
                for file_path in search_dir.rglob('*'):
                    if file_path.is_file():
                        files.append(str(file_path))

        except Exception as error:
            print(highlight(
                f"[!] Error listing files: {error}",
                Fore.RED
            ))

        return files

    def get_directory_size(self, directory: Optional[str] = None) -> int:
        """
        Calculate total size of files in a directory.

        Args:
            directory: Directory path (uses base_directory if None)

        Returns:
            Total size in bytes
        """
        target_dir = Path(directory) if directory else self.base_directory
        total_size = 0

        try:
            for file_path in target_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as error:
            print(highlight(
                f"[!] Error calculating directory size: {error}",
                Fore.RED
            ))

        return total_size

    def cleanup_empty_directories(self) -> int:
        """
        Remove empty directories from the base directory tree.

        Returns:
            Number of directories removed
        """
        removed_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(
                self.base_directory,
                topdown=False
            ):
                if not dirnames and not filenames:
                    try:
                        os.rmdir(dirpath)
                        removed_count += 1
                    except OSError:
                        pass

        except Exception as error:
            print(highlight(
                f"[!] Error during cleanup: {error}",
                Fore.RED
            ))

        return removed_count
