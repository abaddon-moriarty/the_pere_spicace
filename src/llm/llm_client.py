import os
import sys
import json
import logging


from pathlib import Path

import ollama


from dotenv import load_dotenv

from obsidian.vault_structure import build_vault_map

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

    def __init__(
        self,
        model_name: str,
        prompt_dir: Path,
    ):
        """
        Initialize the LLMClient.
        Args:
            model_name (str): The name of the LLM model to use.
            prompt_dir (Path): Path to the directory containing prompt templates.
        """
        self.model_name = model_name
        self.prompt_dir = prompt_dir

    def _load_prompt(self, name: str, **kwargs) -> list:
        """
        Load and format a prompt template from files.
        Searches for prompt files matching the given name in the prompt directory.
        If multiple files are found, combines context/system and user templates.
        Otherwise, loads a single template file and returns a tuple with None as
        the system prompt.
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
        prompt_file = self.prompt_dir.iterdir()
        prompts = [prompt for prompt in prompt_file if name in str(prompt)]
        if len(prompts) > 1:
            for prompt_path in prompts:
                if ("context" in str(prompt_path)) or (
                    "system" in str(prompt_path)
                ):
                    with Path.open(prompt_path, encoding="utf-8") as f:
                        context_template = f.read()

                elif "user" in str(prompt_path):
                    with Path.open(prompt_path, encoding="utf-8") as f:
                        user_template = f.read()

            return context_template, user_template.format(**kwargs)

        prompt_path = self.prompt_dir / f"{name}.txt"

        with open(prompt_path, encoding="utf-8") as f:
            template = f.read()

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
            transcript (str): The transcript text to analyze.
            prompt_name (str): The name of the prompt template to use for extraction.
        Returns:
            str: The extracted topics/concepts from the LLM response.
        """
        system, user = self._load_prompt(
            name=prompt_name,
            transcript=transcript,
        )
        if system:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        else:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": user}],
            )
        return json.loads(response["message"]["content"])

        # def generate_summary(self, transcript: str) -> str:
        # """Generate a summary from the transcript."""
        # prompt = f"Summarize the following transcript in a few paragraphs:\n\n{transcript}"
        # return self.chat(prompt)

        # def generate_quiz(self, summary: str) -> str:
        # """Generate quiz questions based on the summary."""
        # prompt = f"Based on this summary, create 5 quiz questions with answers:\n\n{summary}"
        # return self.chat(prompt)

    def vault_enhancement_mapping(
        self,
        transcript: str,
        concepts: list,
        vault_map: dict,
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
        return


if __name__ == "__main__":
    load_dotenv()
    model = os.getenv("OLLAMA_MODEL")
    prompts_dir = Path(os.getenv("PROMPTS_DIR"))

    if not model:
        logger.warning("OLLAMA_MODEL not set in .env")
        sys.exit(1)

    client = LLMClient(model, prompts_dir)
    logger.info(f"LLM client initialized with model: {model}")

    with open("./test.txt", encoding="utf-8") as f:
        vault_map = build_vault_map()
        f = f.readlines()
        logger.info("Reading transcription")
        concepts = (
            client.topic_extraction(
                transcript=f,
                prompt_name="topic_extraction",
            ),
        )
        logger.info(
            f"Concepts extracted. Found{len(concepts)} concepts\nAmong those: {concepts[:3]})",
        )
        client.vault_enhancement_mapping(
            transcript=f,
            concepts=concepts,
            vault_map=vault_map,
        )

    # print(
    #     client._load_prompt(
    #         "topic_extraction",
    #         transcript="test",
    #     ),
    # )

    # if len(sys.argv) > 1:
    #     prompt = " ".join(sys.argv[1:])
    #     response = client.chat(prompt)
    #     print("\nResponse:\n", response)
    # else:
    #     print("Usage: python llm_client.py: <your prompt here>")
