from app.logging_config import logger
import argostranslate.translate
from app.common_professions import COMMON_PROFESSIONS
from app.manual_translation import MANUAL_FIX
from collections import defaultdict
import time
from app.db import get_connection


MANUAL_TRANSLATIONS = {
    "plumber": "rörmokare",
    "dentist": "tandläkare",
    "doctor": "läkare",
    "driver": "förare",
    # extend if needed
}

occupation_labels_sv = []

def autocomplete_occupation_labels(query_sv: str, limit: int = 10):
    """
    Finds substring hints for occupation_labels_sv.
    Returns no more than the limit of results.
    """
    if not query_sv:
        return []
    query_sv_lower = query_sv.lower()
    # Фильтруем все, где query_sv — подстрока, insensitive
    matches = [label for label in occupation_labels_sv if label and query_sv_lower in label.lower()]
    # Можно сделать чуть умнее (например, startswith — сначала, потом по вхождению, сортировка по популярности и т.п.)
    return matches[:limit]


def clean_translation(text: str) -> str:
    """
    Removes consecutive duplicate words in the translation result.
    """
    words = text.strip().split()
    unique_words = []
    for w in words:
        if not unique_words or w.lower() != unique_words[-1].lower():
            unique_words.append(w)
    return " ".join(unique_words)

def get_argos_lang(code: str):
    """
    Returns the argostranslate language object for the given language code.
    """
    return next((lang for lang in argostranslate.translate.get_installed_languages() if lang.code == code), None)

def translate_en_to_sv(text: str) -> str:
    manual = MANUAL_TRANSLATIONS.get(text.strip().lower())
    if manual:
        return manual

    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == "en"), None)
    to_lang = next((lang for lang in installed_languages if lang.code == "sv"), None)
    if not from_lang or not to_lang:
        logger.error("Argos packages not installed for en→sv translation")
        raise Exception("The packages are not installed for en→sv")
    translation = from_lang.get_translation(to_lang)
    try:
        translated = translation.translate(text)
        cleaned = clean_translation(translated)
        return cleaned
    except Exception as e:
        logger.error(f"Argos translation error (en→sv) for '{text}': {e}")
        return text

def translate_sv_to_en(text: str) -> str:
    installed_languages = argostranslate.translate.get_installed_languages()
    sv_lang = next((l for l in installed_languages if l.code == "sv"), None)
    en_lang = next((l for l in installed_languages if l.code == "en"), None)
    if sv_lang and en_lang:
        translation = sv_lang.get_translation(en_lang)
        if translation is not None:
            try:
                translated = translation.translate(text)
                return translated
            except Exception as e:
                logger.error(f"Translation error (sv→en) for '{text}': {e}")
                return text
    logger.warning(f"No translation found for (sv→en) '{text}', returning original")
    return text

def is_too_general(query: str, occupation_labels, max_labels=10):
    """
    Returns True if the query is too general:
    1. The query is in COMMON_PROFESSIONS (either in English or Swedish).
    2. Too many occupation_labels match the query (both in English and Swedish).
    """
    query_l = query.strip().lower()

    # Check if query matches any common profession in English or Swedish
    if query_l in COMMON_PROFESSIONS:
        return True
    for prof in COMMON_PROFESSIONS:
        # Check using translation to Swedish
        if query_l == translate_en_to_sv(prof).lower():
            return True

    # Check number of matches in occupation labels
    matched = [lbl for lbl in occupation_labels if query_l in lbl.lower()]
    if len(matched) >= max_labels:
        return True
    return False

def get_swedish_profession(query: str):
    # 1. Сначала ищем точный матч
    if query in MANUAL_FIX:
        logger.debug(f"Swedish translation for '{query}' found in MANUAL_FIX (exact match): {MANUAL_FIX[query]}")
        return MANUAL_FIX[query]
    # 2. Пробуем с тайтлкейсом (например, 'Accountant')
    elif query.title() in MANUAL_FIX:
        logger.debug(f"Swedish translation for '{query}' found in MANUAL_FIX (title match): {MANUAL_FIX[query.title()]}")
        return MANUAL_FIX[query.title()]
    # 3. Если не нашли, используем генератор
    else:
        swedish = translate_en_to_sv(query)
        logger.debug(f"Swedish translation for '{query}' generated via translate_en_to_sv: {swedish}")
        return swedish
    

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
    
def search_query(query: str, refined: bool = False):
    query = query.strip()
    logger.info(f"search_query called | query='{query}' | refined={refined}")

    if not query:
        logger.warning("search_query: Received empty query")
        return {"error": "Empty query."}

    try:
        swedish = get_swedish_profession(query)
        logger.debug(f"search_query: Translated query to Swedish: '{swedish}'")

        if not refined:
            if is_too_general(query, occupation_labels_sv):
                logger.info(f"search_query: Query '{query}' is too general, returning suggestions")
                suggestions_sv = autocomplete_occupation_labels(swedish)[:10]
                suggestions = []
                for lbl in suggestions_sv:
                    en = translate_sv_to_en(lbl)
                    if en and en.lower() != lbl.lower():
                        suggestions.append(f"{en} ({lbl})")
                    else:
                        suggestions.append(lbl)
                logger.debug(f"search_query: Suggestions for refinement: {suggestions}")
                return {
                    "need_refine": True,
                    "suggestions": suggestions,
                    "original_query": query,
                    "allow_raw_search": True
                }

        # If refined or not too general — just perform the search
        logger.info(f"search_query: Performing search for query '{query}' and Swedish '{swedish}'")
        result = perform_search(query, swedish)
        logger.info(f"search_query: Search performed successfully for query '{query}'")
        return result

    except Exception as e:
        logger.exception(f"search_query: Unexpected error for query '{query}'")
        return {"error": str(e)}