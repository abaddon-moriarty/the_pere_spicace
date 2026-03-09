import json


from unittest.mock import patch

import pytest

from src.llm.llm_client import LLMClient


@pytest.fixture
def llm_client(tmp_path):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    return LLMClient(model_name="test-model", prompt_dir=prompt_dir)


def test_load_prompt_single_file(llm_client, tmp_path):
    prompt_file = tmp_path / "prompts" / "test.txt"
    prompt_file.write_text("Hello {value}!")
    system, user = llm_client._load_prompt("test", value="World")
    assert system is None
    assert user == "Hello World!"


def test_load_prompt_context_and_user(llm_client, tmp_path):
    (tmp_path / "prompts" / "test_context.txt").write_text(
        "System instructions",
    )
    (tmp_path / "prompts" / "test_user.txt").write_text(
        "User prompt with {value}",
    )  # changed
    system, user = llm_client._load_prompt("test", value="123")
    assert system == "System instructions"
    assert user == "User prompt with 123"


def test_load_prompt_file_not_found(llm_client):
    with pytest.raises(FileNotFoundError):
        llm_client._load_prompt("nonexistent")


@patch("src.llm.llm_client.ollama.chat")
def test_chat(mock_ollama_chat, llm_client):
    mock_ollama_chat.return_value = {"message": {"content": "response text"}}
    result = llm_client.chat("Hello")
    mock_ollama_chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert result == "response text"


@patch("src.llm.llm_client.ollama.chat")
def test_topic_extraction(mock_ollama_chat, llm_client, tmp_path):
    # Setup prompt file
    prompt_file = tmp_path / "prompts" / "topic.txt"
    prompt_file.write_text("Extract topics from: {transcript}")
    # Mock ollama response
    mock_ollama_chat.return_value = {
        "message": {"content": json.dumps(["topic1", "topic2"])},
    }

    result = llm_client.topic_extraction("sample transcript", "topic")

    mock_ollama_chat.assert_called_once_with(
        model="test-model",
        messages=[
            {
                "role": "user",
                "content": "Extract topics from: sample transcript",
            },
        ],
    )
    assert result == ["topic1", "topic2"]


@patch("src.llm.llm_client.ollama.chat")
def test_vault_enhancement_mapping(mock_ollama_chat, llm_client, tmp_path):
    # Setup context and user prompts
    (tmp_path / "prompts" / "vault_context.txt").write_text(
        "System: map concepts",
    )
    (tmp_path / "prompts" / "vault_user.txt").write_text(
        "Transcript: {transcript}\nConcepts: {concepts}\nVault: {vault_map}",
    )
    mock_ollama_chat.return_value = {
        "message": {"content": json.dumps({"mapping": "result"})},
    }

    result = llm_client.vault_enhancement_mapping(
        transcript="t",
        concepts=["c1"],
        vault_map={"key": "value"},
        prompt_name="vault",
    )

    mock_ollama_chat.assert_called_once()
    args = mock_ollama_chat.call_args[1]
    assert args["model"] == "test-model"
    messages = args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Transcript: t" in messages[1]["content"]
    assert result == {"mapping": "result"}
