import json
import logging
import os
from typing import Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from prompts import REVIEW_PROMPT, SIMILAR_REVIEWS_CONTEXT, SYSTEM_PROMPT
from vector_store import search_similar_reviews

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ── Agent State ───────────────────────────────────────────────────────────────

class ReviewState(TypedDict):
    pr_title: str
    pr_description: str
    diff: str
    repo_full_name: str
    pr_number: int
    similar_reviews: list[str]
    prompt: str
    raw_response: str
    review: dict
    tokens_used: int
    error: Optional[str]


# ── Node functions ────────────────────────────────────────────────────────────

def fetch_similar_reviews(state: ReviewState) -> ReviewState:
    """
    Query pgvector for the most semantically similar past reviews.
    Uses the PR title + description as the search query.
    """
    logger.info("Fetching similar past reviews from vector store...")

    query = f"{state['pr_title']}\n{state['pr_description']}"
    similar = search_similar_reviews(query_text=query, limit=3)

    state["similar_reviews"] = similar
    logger.info(f"Found {len(similar)} similar reviews")
    return state


def build_prompt(state: ReviewState) -> ReviewState:
    """Assemble the final prompt, optionally injecting similar reviews."""
    logger.info("Building review prompt...")

    similar_context = ""
    if state["similar_reviews"]:
        formatted = "\n".join(f"- {r}" for r in state["similar_reviews"])
        similar_context = SIMILAR_REVIEWS_CONTEXT.format(similar_reviews=formatted)

    prompt = REVIEW_PROMPT.format(
        repo_full_name=state["repo_full_name"],
        pr_number=state["pr_number"],
        pr_title=state["pr_title"],
        pr_description=state["pr_description"] or "No description provided.",
        diff=state["diff"],
    ) + similar_context

    state["prompt"] = prompt
    return state


def call_llm(state: ReviewState) -> ReviewState:
    """Call the LLM and store the raw response."""
    logger.info(f"Calling LLM ({LLM_MODEL})...")

    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.2,
        api_key=OPENAI_API_KEY,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["prompt"]),
    ]

    response = llm.invoke(messages)

    state["raw_response"] = response.content
    state["tokens_used"] = (
        response.usage_metadata.get("total_tokens", 0)
        if hasattr(response, "usage_metadata") and response.usage_metadata
        else 0
    )

    logger.info(f"LLM responded. Tokens used: {state['tokens_used']}")
    return state


def parse_response(state: ReviewState) -> ReviewState:
    """Parse the LLM JSON response into a structured dict."""
    logger.info("Parsing LLM response...")

    raw = state["raw_response"].strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    try:
        review = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}\nRaw: {raw[:500]}")
        review = {
            "summary": "Review could not be parsed. Please check the raw response.",
            "bugs": [],
            "suggestions": [],
            "security_issues": [],
            "complexity_score": None,
            "overall_verdict": "comment",
        }
        state["error"] = str(e)

    review.setdefault("bugs", [])
    review.setdefault("suggestions", [])
    review.setdefault("security_issues", [])
    review.setdefault("complexity_score", None)
    review.setdefault("overall_verdict", "comment")

    if review["overall_verdict"] not in ("approve", "request_changes", "comment"):
        review["overall_verdict"] = "comment"

    if review["complexity_score"] is not None:
        try:
            review["complexity_score"] = max(1, min(10, int(review["complexity_score"])))
        except (ValueError, TypeError):
            review["complexity_score"] = None

    review["model_used"] = LLM_MODEL
    review["tokens_used"] = state["tokens_used"]
    review["raw_response"] = state["raw_response"]

    state["review"] = review
    return state


def should_retry(state: ReviewState) -> str:
    if state.get("error") and not state.get("review", {}).get("summary"):
        logger.warning("Retrying due to parse error...")
        return "retry"
    return "done"


# ── Build the LangGraph ───────────────────────────────────────────────────────

def build_review_graph() -> StateGraph:
    graph = StateGraph(ReviewState)

    graph.add_node("fetch_similar", fetch_similar_reviews)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm)
    graph.add_node("parse_response", parse_response)

    graph.set_entry_point("fetch_similar")
    graph.add_edge("fetch_similar", "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", "parse_response")
    graph.add_conditional_edges(
        "parse_response",
        should_retry,
        {
            "retry": "call_llm",
            "done": END,
        }
    )

    return graph.compile()


review_graph = build_review_graph()


# ── Public interface ──────────────────────────────────────────────────────────

def run_review_agent(
    pr_title: str,
    pr_description: str,
    diff: str,
    repo_full_name: str,
    pr_number: int,
) -> dict:
    logger.info(f"Running review agent for {repo_full_name}#{pr_number}")

    initial_state: ReviewState = {
        "pr_title": pr_title,
        "pr_description": pr_description,
        "diff": diff,
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "similar_reviews": [],
        "prompt": "",
        "raw_response": "",
        "review": {},
        "tokens_used": 0,
        "error": None,
    }

    final_state = review_graph.invoke(initial_state)
    return final_state["review"]
