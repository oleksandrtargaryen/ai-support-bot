from functools import lru_cache
from pathlib import Path

import chromadb
from langchain.embeddings import init_embeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


@lru_cache
def get_vectorstore() -> Chroma:
    settings = get_settings()
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=init_embeddings(settings.embeddings_model),
    )


def load_faq_documents(faq_dir: Path) -> list[Document]:
    documents = []
    for path in sorted(faq_dir.glob("*.md")):
        documents.append(
            Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name})
        )
    return documents


def ingest_faq(faq_dir: Path) -> int:
    """Re-index FAQ markdown files into Chroma. Returns the number of chunks."""
    documents = load_faq_documents(faq_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.reset_collection()
    if chunks:
        vectorstore.add_documents(chunks)
    return len(chunks)


@tool
def search_faq(query: str) -> str:
    """Search the workshop FAQ (location, warranty, payment, policies, general questions)."""
    results = get_vectorstore().similarity_search(query, k=4)
    if not results:
        return "Nothing relevant found in the FAQ."
    return "\n---\n".join(doc.page_content for doc in results)
