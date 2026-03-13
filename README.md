# YouTube Learning Pipeline

> Turn YouTube videos into structured Obsidian notes, summaries, and quizzes—all running locally with privacy in mind.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/codestyle-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-68%25-yellowgreen)]()

## Overview

**YouTube Learning Pipeline** automates the process of learning from YouTube videos. It:
- Downloads video transcripts using an MCP server (yt-dlp-mcp)
- Caches transcripts in a local SQLite database
- Extracts video metadata (title, channel, etc.)
- Builds a map of your Obsidian vault for context‑aware enrichment
- **Chunks, embeds, and indexes your vault** for semantic search (RAG)
- **Watches your vault** for changes and automatically re‑indexes files
- **Answers questions** from your notes using a RAG pipeline (local LLM)
- (Planned) Generates summaries, key concepts, and quizzes
- (Planned) Updates your Obsidian notes with new content while preserving your own writing

Everything runs locally—no API keys, no data sent to the cloud.

## Current Status
| Component                     | Status   | Notes                                                                 |
|-------------------------------|----------|----------------------------------------------------------------------|
| YouTube transcript fetch      | ✅       | Uses @kevinwatt/yt-dlp-mcp with retry logic and cookie fallback      |
| SQLite cache                  | ✅       | Stores transcripts and metadata                                      |
| Vault structure analyzer      | ✅       | `build_vault_map()` scans Obsidian vault and extracts frontmatter    |
| Cookie extraction             | ⚠️       | Reads Brave cookies (encrypted, may need keyring access)             |
| LLM client                    | ✅       | Simple wrapper for Ollama chat & embedding (rewritten)               |
| Topic extraction              | ✅       | Uses LLM to extract key concepts from transcript                     |
| Concept → note mapping        | ✅       | Maps topics to existing vault notes (LLM + vault map)                |
| Enrichment planner            | 🚧       | Produces JSON plan (updates, new notes, skipped) – WIP, awaiting RAG filtering |
| RAG foundation                | ✅       | Chunking (by headings), embedding (`nomic-embed-text`), ChromaDB store |
| Vault watcher                 | ✅       | `watchdog`‑based, debounced re‑indexing on file changes              |
| RAG retriever                 | ✅       | Answers questions from vault content using local LLM                 |
| Obsidian note writer          | ❌       | Will create/update notes via Obsidian MCP                            |
| Interactive quiz generation   | ❌       | Planned                                                              |

## Features
- **Privacy-First**: Everything runs locally—no data sent to external APIs
- **Smart Summarization**: Uses local LLMs (Ollama/LM Studio) to create concise summaries
- **Obsidian Integration**: Automatically creates or updates well-formatted notes in your vault
- **Interactive Quizzes**: Generates questions to test your understanding
- **Semantic Search**: Ask questions about your vault and get answers grounded in your notes (RAG)
- **Auto‑indexing**: The vault watcher keeps your vector database in sync as you edit notes

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
   python -m venv venv
   source venv/bin/activate  # On Linux/macOS
   # .\venv\Scripts\activate   # On Windows
   ```

3. **Install the package**
   ```bash
   pip install -e .
   ```

4. **Install the required MCP server** (it will be fetched automatically via `npx`):
   ```bash
   npx -y @kevinwatt/yt-dlp-mcp
   ```

5. **Set up environment variables**
   Copy `.env.example` to `.env` and edit:
   ```bash
   # Required
   OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
   OLLAMA_MODEL=llama3.2          # or your preferred model
   EMBEDDING_MODEL=nomic-embed-text

   # Optional (for cookie‑based YouTube access)
   YTDLP_COOKIES_FROM_BROWSER=brave  # or firefox, chrome
   ```

6. **Pull the embedding model** (used by the RAG pipeline)
  ```bash
  ollama pull llama3.2
  ```

### Basic Usage
```bash
# Process a YouTube video
python main.py --url "https://www.youtube.com/watch?v=EXAMPLE"

# Or run the interactive mode
python main.py
# Then enter the URL when prompted
```

### Query your vault (RAG)
```bash
python -m src.rag.retriever --question "What is RAG?"
```

The retriever will return an answer based on your indexed notes.

## Project Structure
```
youtube-learning-pipeline/
├── src/
│   ├── database/               # SQLite cache
│   ├── llm/                    # LLM client (Ollama)
│   ├── obsidian/                # Vault map, note filtering, indexer, watcher
│   ├── rag/                     # Chunker, embedder, ChromaDB store, retriever
│   ├── transcription_client/    # YouTube transcript fetcher
│   └── utils/                   # Cookie extraction, etc.
├── tests/                       # Comprehensive test suite (91 tests, 68% coverage)
├── scripts/                      # Utility scripts (run_tests.py, etc.)
├── .github/workflows/            # CI/CD pipelines
└── pyproject.toml                # Project configuration and dependencies
```

## Roadmap (Development Phases)
The project follows a strict phase‑based plan. Each phase must be fully working before moving to the next.

- [x] **Phase 0 – Fix LLM client**  
  Simple wrapper for Ollama (`chat`, `embed`); tested with hardcoded transcript.

- [x] **Phase 1 – Stabilize YouTube client**  
  Switch to `@kevinwatt/yt-dlp-mcp`; add cookie support; SQLite cache.

- [x] **Phase 2 – Design note format**  
  Add `sources` frontmatter; define template with `## Summary`, `## Key Concepts`, `## Quiz`.

- [x] **Phase 3 – Vault structure awareness**  
  `build_vault_map()` scans vault; extracts title, tags, summary.

- **Phase 4 – Enrichment planner**  
  - [x] Step 1: Topic extraction from transcript (LLM)  
  - [x] Step 2: Map topics to existing notes (LLM + vault map)  
  - [ ] Step 3: Produce JSON plan (updates, new notes, skipped) – **WIP**, awaiting RAG to filter relevant notes.

- [x] **Phase 5 – RAG foundation**  
  - [x] Chunk markdown notes by heading  
  - [x] Embed chunks with `nomic-embed-text`  
  - [x] Store in ChromaDB with metadata  
  - [x] Delete/re‑index files

- [x] **Phase 6 – Vault watcher**  
  Watch for file changes; debounced re‑indexing with `watchdog`.

- [x] **Phase 7 – RAG retriever**  
  Answer questions from vault content using retrieved chunks + LLM.

- **Phase 8 – Query interfaces**  
  - CLI with rich formatting  
  - Gradio web UI (planned)  
  - Obsidian plugin (TypeScript) (planned)

## Testing

```bash
# Quick test run
python scripts/run_tests.py

# Specific test suites
python scripts/run_tests.py --type unit --coverage
python scripts/run_tests.py --type integration -v

# With linting and type checking
python scripts/run_tests.py --lint --type-check --coverage -v

# Auto‑fix lint issues
ruff check --fix
```

## Development

### Setting Up Development Environment
```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Run tests on change (optional)
pip install pytest-watch
pytest-watch
```

### Code Style
- **Formatter**: Ruff
- **Linter**: Ruff
- **Import Sorter**: Ruff
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
- Ensure `npx` is available and the MCP server can be fetched.
- Check internet connection.

#### "LLM not responding"
- Verify Ollama/LM Studio is running.
- Check model is downloaded: `ollama list`
- Confirm API endpoint is correct.

#### "Obsidian vault not found"
- Verify the path in `.env` is absolute and exists.
- Check write permissions.

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
