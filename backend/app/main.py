import time
from fastapi import FastAPI, Query, HTTPException
from typing import List
from contextlib import asynccontextmanager
from app.db import get_connection
from app.services import occupation_labels_sv
from app.occupation_labels_loader import load_occupation_labels
from app.services import search_query

from app.logging_config import logger

logger.info("Logging with date-based filenames initialized!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load all Swedish occupation labels into memory
    occupation_labels_sv.clear()
    occupation_labels_sv.extend(load_occupation_labels())
    logger.info(f"Loaded {len(occupation_labels_sv)} occupation labels in memory at startup.")
    yield
    # Shutdown actions (if needed)

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/dbcheck")
def db_check():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"db_status": "ok", "result": result}
    except Exception as e:
        logger.error(f"DB check failed: {e}")
        return {"db_status": "error", "detail": str(e)}


@app.get("/search")
def search(query: str, refined: bool = False):
    logger.info(f"[USAGE] /search called | query='{query}' | refined={refined}")
    return search_query(query, refined)


@app.get("/multi_search")
def multi_search(queries: List[str] = Query(..., min_length=1, max_length=3), refined: List[bool] = Query(None)):
    """
    Returns the weekly publication dynamics for multiple search queries at once.
    If at least one query is too general (and not marked refined), returns suggestions for clarification.
    """
    start_total = time.time()
    logger.info(f"[USAGE] /multi_search called | queries={queries} | refined={refined}")

    if not queries:
        logger.warning("No queries provided to /multi_search")
        raise HTTPException(status_code=400, detail="At least one query is required.")
    if len(queries) > 2:
        logger.warning(f"Too many queries: received {len(queries)} (max 2 allowed)")
        raise HTTPException(status_code=400, detail="A maximum of 2 queries is allowed.")

    # Make sure 'refined' is the same length as 'queries' (default to False if not specified)
    if refined is None or len(refined) != len(queries):
        refined = [False] * len(queries)
        logger.info(f"'refined' parameter adjusted to match 'queries': {refined}")
    else:
        refined = [bool(r) for r in refined]

    # First, check if any query requires refinement
    need_refine = False
    refine_which = []
    suggestions = []
    orig_queries = []
    allow_raw_search = []

    for idx, (query, is_refined) in enumerate(zip(queries, refined)):
        logger.info(f"[multi_search][{query}] Calling search_query (refined={is_refined})")
        result = search_query(query, is_refined)
        # If at least one query requires refinement, immediately return suggestions
        if result.get("need_refine"):
            need_refine = True
            refine_which.append(idx)
            suggestions.append(result.get("suggestions", []))
            orig_queries.append(query)
            allow_raw_search.append(result.get("allow_raw_search", True))
            logger.info(f"[multi_search][{query}] Needs refinement, suggestions: {result.get('suggestions', [])}")
        else:
            suggestions.append([])
            orig_queries.append(query)
            allow_raw_search.append(False)

    if need_refine:
        t_refine = time.time() - start_total
        logger.info(f"[multi_search] Refinement triggered for queries at indices {refine_which}. Time spent: {t_refine:.3f} sec")
        return {
            "need_refine": True,
            "refine_which": refine_which,
            "suggestions": suggestions,
            "original_queries": orig_queries,
            "allow_raw_search": allow_raw_search
        }

    # If no refinement is needed, return results for all queries
    results = []
    for idx, (query, is_refined) in enumerate(zip(queries, refined)):
        logger.info(f"[multi_search][{query}] Performing final search (refined={is_refined})")
        result = search_query(query, is_refined)
        results.append(result)

    end_total = time.time()
    logger.info(f"/multi_search: Processed {len(queries)} queries in {end_total - start_total:.3f} sec")
    return {"results": results}


