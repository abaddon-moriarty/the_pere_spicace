from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the_pere_spicace.
    All values can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently ignore unknown env vars
    )

    # --- Obsidian ---
    obsidian_vault_path: Path = Path.home() / "Documents" / "obsidian"
    obsidian_notes_folder: str = "Generated"

    # --- Ollama ---
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # --- ChromaDB ---
    chroma_persist_path: Path = Path("./chroma_db")

    # --- YouTube / cookies ---
    ytdlp_cookies_browser: str = "brave"

    # --- Prompts ---
    prompts_dir: Path = Path("./src/prompts")

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
