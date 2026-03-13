import sys
import logging


from pathlib import Path

from rich.live import Live
from rich.console import Console
from rich.spinner import Spinner
from rich.markdown import Markdown

from src.rag.retriever import ask
from src.obsidian.vault_indexer import index_vault

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.getLogger("src").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)


console = Console()


def run_cli():
    console.print(Markdown("# Vault Query CLI"))
    console.print(
        "Type your user_input,\
        \n[bold]exit[/bold] to quit,\
        \n[bold]reindex[/bold] to re-index vault.\n",
    )

    while True:
        try:
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            console.print("Goodbye.")
            break

        if user_input.lower() == "reindex":
            console.print("[yellow]Re-indexing vault...[/yellow]")
            index_vault(force=True)
            console.print("[green]Done.[/green]")
            continue

        # Stream the answer token by token
        console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")
        full_response = []
        with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10):
            for token in ask(user_input):
                full_response.append(token)

        # once done, render as markdown
        console.print(Markdown("".join(full_response)))


if __name__ in "__main__":
    run_cli()
