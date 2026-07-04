"""Index FAQ markdown files from data/faq into Chroma."""

from pathlib import Path

from app.agent.rag import ingest_faq

if __name__ == "__main__":
    faq_dir = Path(__file__).parent.parent / "data" / "faq"
    count = ingest_faq(faq_dir)
    print(f"Indexed {count} chunks from {faq_dir}")
