# YouTube Learning Pipeline

> Turn YouTube videos into structured Obsidian notes, summaries, and quizzes—all running locally with privacy in mind.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/codestyle-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

**YouTube Learning Pipeline** automates the process of learning from YouTube videos. It:
- Downloads video transcripts using an MCP server (yt-dlp-mcp)
- Caches transcripts in a local SQLite database
- Extracts video metadata (title, channel, etc.)
- Builds a map of your Obsidian vault for context‑aware enrichment
- (Planned) Generates summaries, key concepts, and quizzes via local LLMs (Ollama/LM Studio)
- (Planned) Updates your Obsidian notes with new content while preserving your own writing
Everything runs locally—no API keys, no data sent to the cloud.

## Current Status
| Component               | Status   | Notes                                                                 |
|-------------------------|--------|----------------------------------------------------------------------|
| YouTube transcript fetch | ✅     | Uses @kevinwatt/yt-dlp-mcp with retry logic and cookie fallback       |
| SQLite cache            | ✅     | Stores transcripts and metadata                                       |
| Vault structure analyzer | ✅     | `build_vault_map()` scans Obsidian vault and extracts frontmatter     |
| Cookie extraction       | ⚠️     | Reads Brave cookies (encrypted, may need keyring access)              |
| LLM client              | ❌     | Needs rewrite (Phase 0)                                               |
| Enrichment planner      | ❌     | Will use vault map + LLM to decide note updates                       |
| Obsidian note writer    | ❌     | Will create/update notes via Obsidian MCP                             |

See the Roadmap below for what’s coming next.






### Features
- **Privacy-First**: Everything runs locally—no data sent to external APIs
- **Smart Summarization**: Uses local LLMs (Ollama/LM Studio) to create concise summaries
- **Obsidian Integration**: Automatically creates or updates well-formatted notes in your vault
- **Interactive Quizzes**: Generates questions to test your understanding
<!-- - **MCP Integration**: Uses Model Context Protocol for extensible tool integration
- **Test Suite**: Comprehensive tests for reliable operation -->

## Quick Start

### Prerequisites

- **Python 3.9+** and **pip**
- **Node.js** (for `npx`, used by the MCP server)
- **Obsidian** (for note-taking)
- **Local LLM**: Either [Ollama](https://ollama.ai/) or [LM Studio](https://lmstudio.ai/)
- **Brave/Firefox/Chrome** (for cookies, if you need to bypass YouTube rate limits)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/abaddon-moriarty/the_pere_spicace.git
cd the_pere_spicace
```
2. **Create and activate a virtual environment**
```bash
python -m venv {env-name}
source {env-name}/bin/activate # On Fedora
# {env-name}\Scripts\activate #On Windows: 
```
3. **Install the package**
```bash
pip install -e .
```

4. **Install the required MCP server** (it will be fetched automatically via `npx`, but you can test it with):
```bash
npx -y @kevinwatt/yt-dlp-mcp
```
5. **Set up environment variables**
Copy `.env.example` to `.env` and edit:
```bash
# Required
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Optional (for cookie‑based YouTube access)
YTDLP_COOKIES_FROM_BROWSER=brave  # or firefox, chrome
```

6. **Pull an LLM model** (for later phases)
```bash
ollama pull llama3.2
```

### Basic Usage

```bash
# Process a YouTube video
python main.py --url "https://www.youtube.com/watch?v=EXAMPLE"

# Or use the interactive mode
python main.py
# Then enter the URL when prompted
```

### Core Components
1. **MCP Client**: Connects to YouTube transcript server
2. **LLM Integration**: Summarizes content using Ollama or LM Studio
3. **Obsidian Writer**: Creates structured markdown notes
4. **Quiz Generator**: Produces retention-testing questions
5. **CLI Interface**: User-friendly command-line interaction

## Project Structure
```
youtube-learning-pipeline/
├── src/
│   ├── mcp/                    # MCP client implementation
│   ├── llm/                    # LLM integration (Ollama/LM Studio)
│   ├── obsidian/              # Obsidian vault operations
│   ├── processing/            # Summary and quiz generation
│   ├── cli/                   # Command-line interface
│   └── utils/                 # Shared utilities
├── tests/                     # Test suite
├── docker/                    # Docker configuration
├── scripts/                   # Utility scripts
├── .github/workflows/        # CI/CD pipelines
└── config/                   # Configuration files
```


## Roadmap (Development Phases)
The project follows a strict phase‑based plan. Each phase must be fully working before moving to the next.

### Phase 0 – Fix LLM client
- [ ] Rewrite `LLMClient` as a simple wrapper around Ollama (`chat`, `embed`)
- [ ] Test with a hardcoded transcript → returns readable summary/quiz

### Phase 1 – Stabilize YouTube client (✅ done)
- [x] Switch `@kevinwatt/yt-dlp-mcp` with correct tool names
- [x] Add cookie support (`YTDLP_COOKIES_FROM_BROWSER`)
- [x] Save transcripts to SQLite

### Phase 2 – Design note format (✅ done)
- [x] Add `sources` frontmatter to existing notes
- [ ] Define template with `## Summary`, `## Key Concepts`, `## Quiz`

### Phase 3 – Vault structure awareness (✅ done)
- [x] Write `build_vault_map()` to scan vault and extract metadata
- [x] Include tags, title, first 300 chars of content

### Phase 4 – Enrichment planner
- [ ] Step 1: Topic extraction from transcript (LLM)
- [ ] Step 2: Map topics to existing notes (LLM + vault map)
- [ ] Produce JSON plan (updates, new notes, skipped)

### Phase 4b – Plan execution with review
- [ ] Print human‑readable plan, ask for confirmation
- [ ] Append content wrapped in attribution comments
- [ ] Update `sources` frontmatter

### Phase 5 – RAG foundation (chunker + embedder + ChromaDB)
- [ ] Chunk markdown notes by heading
- [ ] Embed chunks with `nomic-embed-text`
- [ ] Store in ChromaDB with metadata

### Phase 6 – Vault watcher
- [ ] Watch for file changes, re‑index automatically

### Phase 7 – RAG retriever
- [ ] Answer questions from vault content
    

### Phase 8 – Query interfaces
- [ ] CLI with rich formatting
- [ ] Gradio web UI
- [ ] Obsidian plugin (TypeScript)


## Configuration

### Environment Variables

Create a `.env` file:

```env
# LLM Configuration
LLM_TYPE=ollama                 # ollama or lmstudio
OLLAMA_MODEL=llama3.2          # Model name for Ollama
LMSTUDIO_ENDPOINT=http://localhost:1234/v1

# Obsidian Configuration
OBSIDIAN_VAULT_PATH=/path/to/your/vault
<!-- OBSIDIAN_TEMPLATE_PATH=./config/templates/note_template.md --> Not covered yet

# MCP Configuration
MCP_SERVER_TYPE=docker

# Application Settings
TEMP_DIR=./temp
LOG_LEVEL=INFO
```

### LLM Setup

#### Option 1: Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh


# Pull a model
ollama pull model
```

#### Option 2: LM Studio
1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Mistral, Llama 2)
3. Start the local server (default: http://localhost:1234)

## Testing

```bash
# Quick test run
python scripts/run_tests.py

# Full CI simulation (lint + type-check + coverage)
python scripts/run_tests.py --ci

# Or via make
make ci-local

# Specific test suites
python scripts/run_tests.py --type unit --coverage
python scripts/run_tests.py --type integration -v

# With linting and type checking
python scripts/run_tests.py --lint --type-check --coverage -v
```

## Development

### Setting Up Development Environment
```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Run tests on change
pytest-watch  # Optional: pip install pytest-watch
```

### Code Style
- **Formatter**: Ruff (replaces Black)
- **Linter**: Ruff (replaces Flake8)
- **Import Sorter**: Ruff (replaces isort)
- **Type Checking**: mypy

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes

### Commit Convention
We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Test updates
- `chore:` Maintenance

## Future Improvement
- [ ] Handling playlist
- [ ] Advanced quiz generation
- [ ] Multiple question types
- [ ] Progress tracking
- [ ] Batch processing
- [ ] Web interface
- [ ] Mobile app
- [ ] Plugin system

## Contributing


1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'feat: add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup
```bash
# Fork and clone
git clone https://github.com/abaddon-moriarty/the_pere_spicace.git

# Set up upstream remote
git remote add upstream https://github.com/originalowner/youtube-learning-pipeline.git

# Create virtual environment and install dependencies
make setup
```

## Troubleshooting

### Common Issues

#### "Unable to connect to MCP server"
- Ensure the MCP server is running: `uvx mcp-youtube-transcript --help`
- Check Docker is running if using Docker mode

#### "LLM not responding"
- Verify Ollama/LM Studio is running
- Check model is downloaded: `ollama list`
- Confirm API endpoint is correct

#### "Obsidian vault not found"
- Verify the path in `.env` is correct
- Check write permissions to the vault directory

### Debug Mode
```bash
# Enable verbose logging
LOG_LEVEL=DEBUG python main.py --url "YOUTUBE_URL"

```

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support
If you find this project useful, please give it a star on GitHub!

---

<div align="center">
  <sub>Built with ❤️ and ☕ by the open-source community</sub>
</div>
