
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi

RAG_DIR = Path(__file__).resolve().parent
POLICY_PATH = RAG_DIR / "aml_policy.md"
DB_PATH = RAG_DIR / "chroma_db"


def load_policy_sections():
    text = POLICY_PATH.read_text(encoding="utf-8")
    sections = re.split(r"(?=^## POL-\d+:)", text, flags=re.MULTILINE)

    return [
        section.strip()
        for section in sections
        if section.strip().startswith("## POL-")
    ]


def tokenize(text):
    return re.findall(r"\w+", text.lower())


def search_aml_policy(query: str, top_k: int = 3) -> dict:
    """Hybrid retrieval: BM25 + ChromaDB vectors + RRF."""

    if not isinstance(query, str) or not query.strip():
        return {"error": "Query cannot be empty."}

    if not isinstance(top_k, int) or not 1 <= top_k <= 6:
        return {"error": "top_k must be between 1 and 6."}

    sections = load_policy_sections()
    ids = [re.search(r"POL-\d+", s).group() for s in sections]

    # 1. BM25 keyword retrieval
    bm25 = BM25Okapi([tokenize(s) for s in sections])
    bm25_scores = bm25.get_scores(tokenize(query))

    bm25_ranking = sorted(
        range(len(sections)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )

    # 2. ChromaDB semantic retrieval
    client = chromadb.PersistentClient(path=str(DB_PATH))

    collection = client.get_or_create_collection(
        name="aml_policies"
    )

    # Upsert ensures documents are updated without duplication
    collection.upsert(
        ids=ids,
        documents=sections
    )

    vector_results = collection.query(
        query_texts=[query],
        n_results=len(sections)
    )

    vector_ranking = vector_results["ids"][0]
    vector_distances = vector_results["distances"][0]

    # 3. Reciprocal Rank Fusion
    k = 60
    rrf_scores = {policy_id: 0.0 for policy_id in ids}

    for rank, idx in enumerate(bm25_ranking, start=1):
        rrf_scores[ids[idx]] += 1 / (k + rank)

    for rank, policy_id in enumerate(vector_ranking, start=1):
        rrf_scores[policy_id] += 1 / (k + rank)

    ranked_ids = sorted(
        ids,
        key=lambda policy_id: rrf_scores[policy_id],
        reverse=True
    )

    section_lookup = dict(zip(ids, sections))

    return {
        "query": query,
        "retrieval_method": "BM25 + ChromaDB + RRF",
        "bm25_ranking": [
            {
                "rank": rank,
                "policy_id": ids[idx],
                "bm25_score": round(float(bm25_scores[idx]), 4)
            }
            for rank, idx in enumerate(bm25_ranking, start=1)
        ],
        "semantic_ranking": [
            {
                "rank": rank,
                "policy_id": policy_id,
                "vector_distance": round(float(vector_distances[rank - 1]), 4)
            }
            for rank, policy_id in enumerate(vector_ranking, start=1)
        ],
        "rrf_ranking": [
            {
                "rank": rank,
                "policy_id": policy_id,
                "rrf_score": round(rrf_scores[policy_id], 5)
            }
            for rank, policy_id in enumerate(ranked_ids, start=1)
        ],
        "results": [
            {
                "policy_id": policy_id,
                "rrf_score": round(rrf_scores[policy_id], 5),
                "content": section_lookup[policy_id]
            }
            for policy_id in ranked_ids[:top_k]
        ]
    }




def search_investigation_and_disposition_policies(
    investigation_query: str,
    top_k: int = 3
) -> dict:
    """Retrieve investigation and decision policies separately."""

    investigation = search_aml_policy(
        query=investigation_query,
        top_k=top_k
    )

    disposition = search_aml_policy(
        query=(
            "When should AML cases be escalated or closed? "
            "Unexplained material risk indicators, specialist investigation, "
            "customer due diligence, missing evidence, "
            "human approval and documentation requirements."
        ),
        top_k=top_k
    )

    if "error" in investigation:
        return investigation

    if "error" in disposition:
        return disposition

    # Merge and deduplicate while preserving search order.
    unique_policies = {}

    for policy in (
        investigation["results"] + disposition["results"]
    ):
        unique_policies.setdefault(
            policy["policy_id"],
            policy
        )

    return {
        "investigation_search": investigation,
        "disposition_search": disposition,
        "results": list(unique_policies.values()),
        "retrieval_method": "Dual-query hybrid RAG"
    }
