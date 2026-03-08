import ollama


def embedder(texts: list):
    response = ollama.embed(
        model="qwen3-embedding:4b",
        input=texts,
    )
    return response.embeddings
