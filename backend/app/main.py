import time
import logging
import os
from fastapi import FastAPI, Query, HTTPException
from typing import List
from contextlib import asynccontextmanager
from app.db import get_connection
from app.services import translate_en_to_sv, translate_sv_to_en
from app.autocomplete import occupation_labels_sv, autocomplete_occupation_labels
from app.occupation_labels_loader import load_occupation_labels
from app.services import is_too_general, get_swedish_profession
from collections import defaultdict
from logging.handlers import TimedRotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_BASENAME = os.path.join(LOG_DIR, "backend.log")
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"

file_handler = TimedRotatingFileHandler(
    LOG_FILE_BASENAME,
    when='midnight',
    interval=1,
    backupCount=14,
    encoding='utf-8',
    utc=True  # or False, if you want localtime
)
file_handler.suffix = "%Y-%m-%d"
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

logger = logging.getLogger("app.backend")
logger.setLevel(logging.INFO)
logger.handlers.clear()  # Prevent duplicate logs in development
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logging with date-based filenames initialized!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load all Swedish occupation labels into memory
    occupation_labels_sv.clear()
    occupation_labels_sv.extend(load_occupation_labels())
    logging.info(f"Loaded {len(occupation_labels_sv)} occupation labels in memory at startup.")
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
        logging.error(f"DB check failed: {e}")
        return {"db_status": "error", "detail": str(e)}

@app.get("/translate")
def translate(text: str):
    try:
        result = get_swedish_profession(text)
        return {"original": text, "swedish": result}
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return {"error": str(e)}

@app.get("/search")
def search(query: str, refined: bool = False):
    """
    If refined=False (default), check if the query is too general and suggest refinement if needed.
    If refined=True, always do the search, regardless of generality.
    """
    query = query.strip()  # remove leading and trailing spaces
    logger.info(f"/search called | query='{query}' | refined={refined}")

    if not query:
        logger.warning("/search: Received empty query")
        return {"error": "Empty query."}

    try:
        swedish = get_swedish_profession(query)
        logger.debug(f"/search: Translated query to Swedish: '{swedish}'")

        if not refined:
            # For the first request: check if the query is too general
            if is_too_general(query, occupation_labels_sv):
                logger.info(f"/search: Query '{query}' is too general, returning suggestions")
                suggestions_sv = autocomplete_occupation_labels(swedish)[:10]
                suggestions = []
                for lbl in suggestions_sv:
                    en = translate_sv_to_en(lbl)
                    if en and en.lower() != lbl.lower():
                        suggestions.append(f"{en} ({lbl})")
                    else:
                        suggestions.append(lbl)
                logger.debug(f"/search: Suggestions for refinement: {suggestions}")
                return {
                    "need_refine": True,
                    "suggestions": suggestions,
                    "original_query": query,
                    "allow_raw_search": True  # allow "search as is"
                }

        # If refined or not too general — just perform the search
        logger.info(f"/search: Performing search for query '{query}' and Swedish '{swedish}'")
        result = perform_search(query, swedish)
        logger.info(f"/search: Search performed successfully for query '{query}'")
        return result

    except Exception as e:
        logger.exception(f"/search: Unexpected error for query '{query}'")
        return {"error": str(e)}


def perform_search(query: str, swedish: str):
    """
    Performs the search:
    1. Query both English and Swedish indexes in the database.
    2. Merge results by week and return dynamics.
    """
    logger.info(f"perform_search started | query='{query}', swedish='{swedish}'")
    try:
        conn = get_connection()
        cur = conn.cursor()
        english = query.strip()

        # English query
        sql_en = """
            SELECT to_char(date_trunc('week', published_at), 'IYYY-IW') AS week, COUNT(*) as count
            FROM vacancies
            WHERE language = 'en' AND tsv_en @@ plainto_tsquery('english', %s)
            GROUP BY week
        """
        sql_start = time.time()
        cur.execute(sql_en, (english,))
        data_en = cur.fetchall()
        sql_end = time.time()
        logger.info(f"perform_search: SQL EN query '{english}' time: {sql_end - sql_start:.3f} seconds | rows: {len(data_en)}")

        # Swedish query
        sql_sv = """
            SELECT to_char(date_trunc('week', published_at), 'IYYY-IW') AS week, COUNT(*) as count
            FROM vacancies
            WHERE language = 'sv' AND tsv_sv @@ plainto_tsquery('swedish', %s)
            GROUP BY week
        """
        sql_start = time.time()
        cur.execute(sql_sv, (swedish,))
        data_sv = cur.fetchall()
        sql_end = time.time()
        logger.info(f"perform_search: SQL SV query '{swedish}' time: {sql_end - sql_start:.3f} seconds | rows: {len(data_sv)}")

        cur.close()
        conn.close()

        # Merge results by week
        week_counts = defaultdict(int)
        for week, count in data_en + data_sv:
            week_counts[week] += count
        result = [{"week": week, "count": week_counts[week]} for week in sorted(week_counts)]

        logger.info(f"perform_search: finished successfully | query='{query}', total_weeks={len(result)}")
        logger.debug(f"perform_search: result sample={result[:2]}")  # log only first 2 for debug

        return {
            "query": query,
            "swedish": swedish,
            "dynamics": result
        }
    except Exception as e:
        logger.exception(f"perform_search: error for query='{query}', swedish='{swedish}'")
        return {
            "error": str(e),
            "query": query,
            "swedish": swedish
        }


@app.get("/autocomplete")
def autocomplete(query: str):
    swedish = translate_en_to_sv(query)
    suggestions_sv = autocomplete_occupation_labels(swedish)
    suggestions = []
    for label_sv in suggestions_sv:
        label_en = translate_sv_to_en(label_sv)
        # Display as "English (Swedish)" if translation is not identical
        if label_en.lower() != label_sv.lower():
            suggestions.append(f"{label_en} ({label_sv})")
        else:
            suggestions.append(label_sv)
    return {
        "original": query,
        "swedish": swedish,
        "suggestions": suggestions
    }

@app.get("/multi_search")
def multi_search(queries: List[str] = Query(..., min_length=1, max_length=3), refined: List[bool] = Query(None)):
    """
    Returns the weekly publication dynamics for multiple search queries at once.
    If at least one query is too general (and not marked refined), returns suggestions for clarification.
    """
    start_total = time.time()
    logging.info(f"Received /multi_search with queries: {queries} | refined: {refined}")

    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required.")
    if len(queries) > 2:
        raise HTTPException(status_code=400, detail="A maximum of 2 queries is allowed.")

    # Ensure refined is the same length as queries (default to False)
    if refined is None or len(refined) != len(queries):
        refined = [False] * len(queries)
    else:
        refined = [bool(r) for r in refined]

    need_refine = False
    refine_which = []
    suggestions = []
    orig_queries = []
    allow_raw_search = []

    for idx, query in enumerate(queries):
        orig_queries.append(query)
        # Check if query needs to be refined (only if not refined)
        if not refined[idx] and is_too_general(query, occupation_labels_sv):
            need_refine = True
            refine_which.append(idx)
            # Autocomplete suggestions for this query (like in /search)
            t_autocomplete_start = time.time()
            swedish = translate_en_to_sv(query)
            suggestions_sv = autocomplete_occupation_labels(swedish)[:10]
            sugg = []
            for lbl in suggestions_sv:
                en = translate_sv_to_en(lbl)
                if en and en.lower() != lbl.lower():
                    sugg.append(f"{en} ({lbl})")
                else:
                    sugg.append(lbl)
            t_autocomplete_end = time.time()
            logging.info(f"[multi_search][{query}] Refine autocomplete time: {t_autocomplete_end - t_autocomplete_start:.3f} sec")
            suggestions.append(sugg)
            allow_raw_search.append(True)  # or False, if you don't want to allow raw search
        else:
            suggestions.append([])
            allow_raw_search.append(False)

    if need_refine:
        t_refine = time.time() - start_total
        logging.info(f"[multi_search] Refine triggered for queries {refine_which}. Time to prepare refine: {t_refine:.3f} sec")
        return {
            "need_refine": True,
            "refine_which": refine_which,
            "suggestions": suggestions,
            "original_queries": orig_queries,
            "allow_raw_search": allow_raw_search
        }

    # If no refine is needed, process as before, logging time for each stage
    results = []
    for query in queries:
        per_query_start = time.time()

        t1 = time.time()
        swedish = translate_en_to_sv(query)
        t2 = time.time()
        logging.info(f"[multi_search][{query}] Translation time: {t2 - t1:.3f} sec")

        english = query.strip()
        sql = """
            SELECT
                to_char(date_trunc('week', published_at), 'IYYY-IW') AS week,
                COUNT(*) as count
            FROM vacancies
            WHERE (
                (language = 'en' AND tsv_en @@ plainto_tsquery('english', %s))
                OR
                (language = 'sv' AND tsv_sv @@ plainto_tsquery('swedish', %s))
            )
            GROUP BY week
            ORDER BY week;
        """
        sql_start = time.time()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (english, swedish))
        data = cur.fetchall()
        cur.close()
        conn.close()
        sql_end = time.time()
        logging.info(f"[multi_search][{query}] SQL time: {sql_end - sql_start:.3f} sec")

        format_start = time.time()
        result = [{"week": row[0], "count": row[1]} for row in data]
        format_end = time.time()
        logging.info(f"[multi_search][{query}] Formatting time: {format_end - format_start:.3f} sec")

        per_query_end = time.time()
        logging.info(f"[multi_search][{query}] Total per-query time: {per_query_end - per_query_start:.3f} sec")

        results.append({
            "query": query,
            "swedish": swedish,
            "dynamics": result
        })

    end_total = time.time()
    logging.info(f"/multi_search: Processed {len(queries)} queries in {end_total - start_total:.3f} sec")
    return {"results": results}

@app.get("/refine_query")
def refine_query(query: str = Query(..., description="User search input in English")):
    """
    Refine user's query by matching it with occupation labels
    """
    # Translate the query to Swedish
    swedish = get_swedish_profession(query)
    matches = []
    for sv_label in occupation_labels_sv:
        en_label = translate_sv_to_en(sv_label)
        # Check if query is present in the English label (or in Swedish if translation is poor)
        if query.lower() in en_label.lower() or swedish.lower() in sv_label.lower():
            # Format nicely
            if en_label.lower() != sv_label.lower():
                matches.append(f"{en_label} ({sv_label})")
            else:
                matches.append(sv_label)
    # Limit to 10 suggestions
    suggestions = matches[:10]
    return {
        "original": query,
        "suggestions": suggestions,
        "allow_raw_search": True
    }
