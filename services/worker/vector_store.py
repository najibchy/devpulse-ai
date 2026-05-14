import logging
import os
from typing import Optional

from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devpulse:devpulse_secret@db:5432/devpulse")
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, cheap and fast

client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_embedding(text_input: str) -> list[float]:
    """Get a 1536-dim embedding vector from OpenAI."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text_input[:8000],  # Stay within token limits
    )
    return response.data[0].embedding


def build_review_text(review: dict) -> str:
    """
    Build a rich text representation of a review for embedding.
    Combining multiple fields gives better semantic search results.
    """
    parts = [
        f"Summary: {review.get('summary', '')}",
        f"Verdict: {review.get('overall_verdict', '')}",
    ]

    bugs = review.get("bugs", [])
    if bugs:
        parts.append("Bugs: " + "; ".join(bugs))

    suggestions = review.get("suggestions", [])
    if suggestions:
        parts.append("Suggestions: " + "; ".join(suggestions))

    security = review.get("security_issues", [])
    if security:
        parts.append("Security: " + "; ".join(security))

    return "\n".join(parts)


def store_review_embedding(review_id: int, review: dict) -> bool:
    """
    Generate and store the embedding for a completed review.
    Called from tasks.py after saving a review to the DB.
    """
    try:
        review_text = build_review_text(review)
        embedding = get_embedding(review_text)

        with SessionLocal() as db:
            # Delete existing embedding if re-reviewing
            db.execute(
                text("DELETE FROM core_reviewembedding WHERE review_id = :rid"),
                {"rid": review_id},
            )
            db.execute(
                text("""
                    INSERT INTO core_reviewembedding (review_id, embedding, created_at)
                    VALUES (:review_id, :embedding, NOW())
                """),
                {
                    "review_id": review_id,
                    "embedding": str(embedding),  # pgvector accepts list as string
                },
            )
            db.commit()

        logger.info(f"Stored embedding for review {review_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store embedding for review {review_id}: {e}")
        return False


def search_similar_reviews(
    query_text: str,
    limit: int = 3,
    exclude_review_id: Optional[int] = None,
) -> list[str]:
    """
    Find the most semantically similar past review summaries using cosine similarity.
    Returns a list of summary strings to inject into the LLM prompt.
    """
    try:
        query_embedding = get_embedding(query_text)

        exclude_clause = ""
        params: dict = {
            "embedding": str(query_embedding),
            "limit": limit,
        }

        if exclude_review_id:
            exclude_clause = "AND re.review_id != :exclude_id"
            params["exclude_id"] = exclude_review_id

        sql = text(f"""
            SELECT
                r.summary,
                r.overall_verdict,
                r.complexity_score,
                1 - (re.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM core_reviewembedding re
            JOIN core_review r ON r.id = re.review_id
            WHERE 1=1 {exclude_clause}
            ORDER BY re.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        with SessionLocal() as db:
            rows = db.execute(sql, params).fetchall()

        if not rows:
            return []

        results = []
        for row in rows:
            similarity_pct = round(row.similarity * 100, 1)
            results.append(
                f"[{similarity_pct}% similar | verdict: {row.overall_verdict} | "
                f"complexity: {row.complexity_score}/10] {row.summary}"
            )

        logger.info(f"Found {len(results)} similar reviews")
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []  # Fail gracefully — review still proceeds without context
