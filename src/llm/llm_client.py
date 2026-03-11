import os
import re
import sys
import json
import logging


from pathlib import Path

import ollama


from dotenv import load_dotenv

from obsidian.vault_structure import note_filter, build_vault_map

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


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

    def _load_prompt(self, name: str, **kwargs) -> tuple[str | None, str]:
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
                    logger.info(f"Context prompt found at {prompt_path}")
                elif "user" in prompt_path.name:
                    user_template = prompt_path.read_text(encoding="utf-8")
                    logger.info(f"User prompt found at {prompt_path}")
            if user_template is None:
                msg = f"No user prompt found for {name}"
                raise ValueError(msg)
            return context_template, user_template.format(**kwargs)

        prompt_path = self.prompt_dir / f"{name}.txt"
        if not prompt_path.exists():
            msg = f"Prompt file {prompt_path} not found"
            raise FileNotFoundError(msg)
        template = prompt_path.read_text(encoding="utf-8")
        return None, template.format(**kwargs)

    def _parse_json_response(self, raw_content: str) -> dict | None:
        """
        Extract JSON from LLM response content.

        Handles both response wrapped in ```json``` code fences and plain JSON.
        Returns parsed JSON or None if parsing fails.
        """

        def sanitize_json_string(raw: str) -> str:
            # Replace literal newlines inside JSON strings with \n escape
            return re.sub(
                r'"(?:[^"\\]|\\.)*"',
                lambda match: match.group(0)
                .replace("\n", "\\n")
                .replace("\r", "\\r"),
                raw,
                flags=re.DOTALL,
            )

        match = re.search(
            r"```(?:json)?\s*(?P<json>.*?)\s*```",
            str(raw_content),
        )
        if match:
            json_match = (
                (match.group("json")).replace("\n", "").replace("  ", " ")
            )
        else:
            json_match = raw_content.replace("\n", "").replace("  ", " ")

        logger.info(json_match)

        start = json_match.find("{")
        if start == -1:
            start = json_match.find("[")
        if start == -1:
            logger.warning("No JSON object/array found in response")
            return None

        end = json_match.find("}")
        if end == -1 or end < start:
            end = json_match.find("]")
        if end == -1 or end < start:
            logger.warning("No matching closing bracket found")
            return None

        json_str = json_match[start : end + 1]
        json_str = sanitize_json_string(json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.exception("Failed to parse JSON")
            logger.debug(f"Raw output: {json_str}")
            return None

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
        logger.info(
            f"Prompt Generated, getting ready to ask {self.model_name}",
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        logger.info(f"{self.model_name} is extracting topics...")
        response = ollama.chat(model=self.model_name, messages=messages)
        logger.debug(str(response)[:500])
        return self._parse_json_response(
            response["message"]["content"],
        )

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
        logger.info(
            f"Prompt Generated, getting ready to ask {self.model_name}",
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        logger.info(
            f"{self.model_name} is mapping the concepts to your vault.",
        )
        response = ollama.chat(model=self.model_name, messages=messages)
        raw_content = response["message"]["content"]
        logger.info(f"Raw mapping response: {raw_content}")

        return self._parse_json_response(raw_content)

    def mapping_review(self, vault_mapping, propositions):
        vault_mapping = vault_mapping
        propositions = propositions
        return


if __name__ == "__main__":
    load_dotenv()
    model = os.getenv("OLLAMA_MODEL")
    prompts_dir_str = os.getenv("PROMPTS_DIR")
    if not model or not prompts_dir_str:
        logger.error("OLLAMA_MODEL or PROMPTS_DIR not set in .env")
        sys.exit(1)

    prompts_dir = Path(prompts_dir_str)
    client = LLMClient(model, prompts_dir)
    logger.info(f"LLM client initialized with model: {model}")

    url = "./Is RAG Still Needed? Choosing the Best Approach for LLMs.txt"
    with Path(url).open(encoding="utf-8") as f:
        transcript_text = f.read()
        vault_map = build_vault_map()
        logger.info("Reading transcription")
        concepts = client.topic_extraction(
            transcript=transcript_text,
            prompt_name="topic_extraction",
        )
        logger.info(f"Concepts extracted. Found {len(concepts)} concepts")
        if concepts:
            logger.info(f"First three: {concepts[:3]}")

        mapping = client.vault_enhancement_mapping(
            transcript=transcript_text,
            concepts=concepts,
            vault_map=vault_map,
            prompt_name="vault_mapper",
        )
        logger.info(mapping)

        # transcript → topic extraction → concepts
        # concepts → ChromaDB query → top N relevant notes (no filtering)
        # top N notes + concepts + transcript → mapping LLM → plan

        # plan → note_filter removes notes already containing the URL
        # filtered plan → execute (append content to notes)
        logger.info("Tring to apply the note filter")
        mapping = note_filter(mapping, url)
