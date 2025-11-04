[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/) [![Gitminer 3](https://img.shields.io/badge/Gitminer-3-yellow.svg)](https://unkl4b.github.io)
![Gitminer3 stars](https://img.shields.io/github/stars/UnkL4b/GitMiner3)

<img src="https://github.com/UnkL4b/unkl4b.github.io/blob/master/img/Gitminer3.png?raw=true" alt="Screenshot" width="628">



 + Autor: UnkL4b
 + Site: [bravul.com](https://bravul.com)
 + Blog: [unkl4b.github.io](https://unkl4b.github.io)
 + Github: [UnkL4b](https://github.com/unkl4b)
 + X: [@UnkL4b](https://x.com/UnkL4b)

## WARNING
```
 +---------------------------------------------------+
 | DEVELOPERS ASSUME NO LIABILITY AND ARE NOT        |
 | RESPONSIBLE FOR ANY MISUSE OR DAMAGE CAUSED BY    |
 | THIS PROGRAM                                      |
 +---------------------------------------------------+
```


### GITMINER 3

GitMiner v3 is a modular, object-oriented tool designed for discovering sensitive information in public GitHub repositories. It uses advanced dork queries, regex pattern matching, and generates comprehensive threat intelligence reports.

This project is a complete refactoring of the original [Gitminer](https://github.com/UnkL4b/GitMiner) script, focusing on maintainability, scalability, and professional software architecture principles.


---

## Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Output](#-output)
- [Extending GitMiner](#-extending-gitminer)
- [License](#-license)

---

## Features

- **Object-Oriented Design**: Fully refactored into a modular, class-based architecture for better maintainability and extensibility.
- **Multi-Dork Scanning**: Process multiple GitHub dorks from a file or a single dork from the command line.
- **Advanced Pattern Matching**: Utilizes a configurable set of regex patterns to detect a wide range of secrets, including API keys, tokens, passwords, and private keys.
- **YAML-based Configuration**: Easily manage paths, API settings, and detection patterns through simple YAML files.
- **Threat Intelligence Reports**: Automatically generates detailed Markdown reports for each dork, including an executive summary, severity analysis, and technical details.
- **SQLite History Database**: Tracks all search operations, downloaded files, and findings for historical analysis and persistence.
- **PEP 8 Compliant**: Written with clean, readable, and professional code that adheres to Python standards.
- **Robust Error Handling**: Implements proper error handling and rate limit management for stable execution.

---

## Project Structure

The project is organized into a modular structure to separate concerns and improve clarity.

```
gitminer_v3/
├── config/                 # Configuration files
│   ├── paths.yaml          # Directory, file, and API paths
│   ├── labels.yaml         # Regex-to-label mappings for parameters
│   └── patterns.yaml       # Regex patterns for secret detection
├── data/                   # Persistent data storage
│   └── gitminer_history.sqlite # SQLite database for history
├── gitminer/               # Main Python package
│   ├── __init__.py
│   ├── config_manager.py   # Loads and manages all configurations
│   ├── github_client.py    # Handles all GitHub API interactions
│   ├── file_manager.py     # Manages file downloads and storage
│   ├── pattern_analyzer.py # Scans files for secrets
│   ├── database.py         # Manages SQLite database operations
│   ├── report_generator.py # Generates Markdown reports
│   └── utils.py            # Shared utility functions
├── raw/                    # Stores downloaded files from GitHub
├── reports/                # Stores generated threat intelligence reports
├── gitminer_v3.py          # Main executable script
├── requirements.txt        # Python dependencies
└── README.md               # This file 
```

---

## Prerequisites

- Python 3.11+
- A GitHub Personal Access Token (PAT) with `public_repo` scope.

---

## Installation

1.  **Clone the repository or download the source code.**

2.  **Set up your GitHub Token:**
    GitMiner requires a GitHub token to interact with the API. You must set it as an environment variable.

    ```bash
    export GITHUB_TOKEN="your_github_personal_access_token_here"
    ```

3.  **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

GitMiner's behavior is controlled by files in the `config/` directory.

### `paths.yaml`
This file defines all important paths and API settings.

- **`directories`**: Specifies where to store raw files, reports, and data.
- **`files`**: Defines the names for the database and default CSV output.
- **`github`**: Contains settings for the GitHub API, such as URLs, timeouts, and default result limits.

### `labels.yaml`
This file maps regex patterns to human-readable labels. It is primarily used to identify parameter names (e.g., `ftp_user`, `api_key`) in code.

```yaml
# Format: "regex_pattern": "LABEL_NAME"
"(?i)(api[_\\- ]?key|apikey)": "API_KEY"
"(?i)(password|passwd)": "PASSWORD"
```

### `patterns.yaml`
This file contains the core regex patterns used to detect sensitive values like keys, tokens, and credentials.

```yaml
# Format: PATTERN_NAME: "regex_pattern"
GITHUB_TOKEN: "ghp_[A-Za-z0-9_]{36,255}"
AWS_ACCESS_KEY_ID: "AKIA[0-9A-Z]{16}"
```

---

## Usage

The main script `gitminer_v3.py` is the entry point for all operations.

### Command-Line Arguments

| Argument          | Short | Description                                                    | Required |
| ----------------- | ----- | -------------------------------------------------------------- | -------- |
| `--dorks`         | `-d`  | File with dorks (one per line) or a single dork string.        | **Yes**  |
| `--token`         | `-t`  | GitHub token (overrides `GITHUB_TOKEN` env var).               | No       |
| `--max-results`   | `-m`  | Maximum results to fetch per dork. (Default: 200)              | No       |
| `--per-page`      | `-p`  | Results per page for the API. (Default: 30, Max: 100)          | No       |
| `--output-csv`    | `-o`  | Export a summary of downloaded files to a CSV file.            | No       |
| `--report`        |       | Generate a detailed Markdown threat intelligence report.         | No       |
| `--no-analyze`    |       | Skip the local file analysis step (only downloads files).      | No       |

### Examples

1.  **Search using a single dork and generate a report:**

    ```bash
    python3 gitminer_v3.py -d "filename:.env DB_PASSWORD" --report
    ```

2.  **Search using a file containing multiple dorks:**
    Create a file named `dorks.txt`:

    ```
    filename:wp-config.php DB_PASSWORD
    filename:settings.py SECRET_KEY
    extension:pem private
    ```

    Then run the command:

    ```bash
    python3 gitminer_v3.py -d dorks.txt -m 500 --report
    ```

3.  **Export a list of all downloaded files to CSV:**

    ```bash
    python3 gitminer_v3.py -d dorks.txt -o downloaded_files.csv
    ```

4.  **Download files without performing any analysis:**

    ```bash
    python3 gitminer_v3.py -d dorks.txt --no-analyze
    ```

---

## Output

GitMiner produces several types of output, stored in the `raw/`, `reports/`, and `data/` directories.

### Raw Files
All files downloaded from GitHub are stored in the `raw/` directory, organized by dork keyword and repository name.

```
raw/
└── DB_PASSWORD/
    └── someuser_some-repo/
        └── .env
```

### Threat Intelligence Reports
If the `--report` flag is used, a detailed Markdown report is generated for each dork and saved in the `reports/` directory. These reports include:

- An **Executive Summary** with key statistics.
- **Findings by Severity** (High, Medium, Low).
- A **Technical Analysis** section with code snippets and links to the source files.
- **Recommendations** for remediation.

### SQLite Database
The `data/gitminer_history.sqlite` file contains a complete history of all operations, including:

- `search_history`: Records of every dork search performed.
- `downloaded_files`: Metadata for every file downloaded.
- `findings`: Detailed records of every secret found.

This database can be used for long-term tracking and advanced analytics.

---

## Extending GitMiner

GitMiner v3 is designed to be easily extensible.

- **To add new detection patterns:** Simply add a new entry to `config/patterns.yaml`.
- **To add new parameter labels:** Add a new regex-label pair to `config/labels.yaml`.
- **To modify behavior:** The modular, object-oriented code in the `gitminer/` package is well-documented and can be easily modified or extended.

---

## License

This project is open-source and available for personal and educational use. Please use it responsibly and ethically. The author is not responsible for any misuse of this tool.
