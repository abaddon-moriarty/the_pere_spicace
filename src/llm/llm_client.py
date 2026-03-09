import os
import sys
import json
import logging


from pathlib import Path

import ollama


from dotenv import load_dotenv

from src.obsidian.vault_structure import build_vault_map

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LLMClient:
    """
    LLMClient class for interacting with LLM models via Ollama.
    This class provides methods to load prompts from files, send chat requests,
    and extract topics from transcripts using configurable prompt templates.
    Attributes:
        model_name (str): Name of the LLM model to use for requests.
        prompt_dir (Path): Directory path containing prompt template files.
    """

    def __init__(self, model_name: str, prompt_dir: Path):
        """
        Initialize the LLMClient.
        Args:
            model_name (str):
                The name of the LLM model to use.
            prompt_dir (Path):
                Path to the directory containing prompt templates.
        """
        self.model_name = model_name
        self.prompt_dir = prompt_dir

    def _load_prompt(self, name: str, **kwargs) -> list:
        """
        Load and format a prompt template from files.
        Searches for prompt files matching the given name in the prompt
        directory.If multiple files are found, combines context/system
        and user templates. Otherwise, loads a single template file
        and returns a tuple with None as the system prompt.
        Args:
            name (str): The name/prefix of the prompt file(s) to load.
            **kwargs: Keyword arguments for formatting the prompt templates.
        Returns:
            list: A tuple containing (system_prompt, formatted_user_prompt).
                  system_prompt may be None if only one template file is found.
        Raises:
            FileNotFoundError: If the prompt file(s) do not exist.
            KeyError: If template formatting fails due to missing kwargs.
        """
        prompt_files = list(self.prompt_dir.glob(f"*{name}*"))
        if len(prompt_files) > 1:
            context_template = None
            user_template = None
            for prompt_path in prompt_files:
                if (
                    "context" in prompt_path.name
                    or "system" in prompt_path.name
                ):
                    context_template = prompt_path.read_text(encoding="utf-8")
                elif "user" in prompt_path.name:
                    user_template = prompt_path.read_text(encoding="utf-8")
            return context_template, user_template.format(**kwargs)

        prompt_path = self.prompt_dir / f"{name}.txt"
        template = prompt_path.read_text(encoding="utf-8")
        return None, template.format(**kwargs)

    def chat(self, prompt: str) -> str:
        """
        Send a chat prompt to the LLM and return the response.
        Args:
            prompt (str): The user message to send to the model.
        Returns:
            str: The LLM's response content.
        """
        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]

    def topic_extraction(self, transcript: str, prompt_name: str) -> list:
        """
        Extract main distinct concepts from a transcript.
        Loads the specified prompt template and sends it with the transcript
        to the LLM model to identify key topics and concepts.
        Args:
            transcript (str):
                The transcript text to analyze.
            prompt_name (str):
                The name of the prompt template to use for extraction.
        Returns:
            response (list):
                The extracted topics/concepts from the LLM response.
        """
        system, user = self._load_prompt(
            name=prompt_name,
            transcript=transcript,
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})
            response = ollama.chat(model=self.model_name, messages=messages)
            return json.loads(response["message"]["content"])

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": user}],
        )
        return json.loads(response["message"]["content"])

    def generate_summary(self, transcript: str) -> str:
        """Generate a summary from the transcript."""
        prompt = f"Summarize the following transcript in a few paragraphs:\
            \n\n{transcript}"

        return self.chat(prompt)

    def generate_quiz(self, summary: str) -> str:
        """Generate quiz questions based on the summary."""
        prompt = (
            f"Based on this summary, create 5 quiz questions with answers:\
            \n\n{summary}"
        )
        return self.chat(prompt)

    def vault_enhancement_mapping(
        self,
        transcript: str,
        concepts: list,
        vault_map: dict,
        prompt_name: str,
    ):
        """
        def vault_enhancement_mapping(
            transcript: str,
            concepts: list,
            vault_map: dict):

            Map transcript concepts to vault entries for enhancement.
            Args:
                transcript (str): The source transcript text.
                concepts (list): List of extracted concepts to map.
                vault_map (dict): Dictionary mapping concepts to vault entries.
        """
        system, user = self._load_prompt(
            name=prompt_name,
            transcript=transcript,
            concepts=concepts,
            vault_map=vault_map,
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})
            response = ollama.chat(model=self.model_name, messages=messages)
            return json.loads(response["message"]["content"])

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": user}],
        )
        return json.loads(response["message"]["content"])


if __name__ == "__main__":
    load_dotenv()
    model = os.getenv("OLLAMA_MODEL")
    prompts_dir = Path(os.getenv("PROMPTS_DIR"))

    if not model:
        logger.warning("OLLAMA_MODEL not set in .env")
        sys.exit(1)

    client = LLMClient(model, prompts_dir)
    logger.info(f"LLM client initialized with model: {model}")

    with Path.open("./test.txt", encoding="utf-8") as f:
        vault_map = build_vault_map()
        transcript_text = f.read()
        logger.info("Reading transcription")
        concepts = client.topic_extraction(
            transcript=transcript_text,
            prompt_name="topic_extraction",
        )
        logger.info(
            f"Concepts extracted. Found {len(concepts)} concepts\n\
                Among those: {concepts[:3]}",
        )
        mapping = client.vault_enhancement_mapping(
            transcript=transcript_text,
            concepts=concepts,
            vault_map=vault_map,
            prompt_name="vault_mapper",
        )
        logger.info(mapping)
