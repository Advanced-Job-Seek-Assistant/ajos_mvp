import os
import logging
import argostranslate.translate
from app.common_professions import COMMON_PROFESSIONS
from app.manual_translation import MANUAL_FIX

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "services.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

MANUAL_TRANSLATIONS = {
    "plumber": "rörmokare",
    "dentist": "tandläkare",
    "doctor": "läkare",
    "driver": "förare",
    # extend if needed
}

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
        logging.info(f"Swedish translation for '{query}' found in MANUAL_FIX (exact match): {MANUAL_FIX[query]}")
        return MANUAL_FIX[query]
    # 2. Пробуем с тайтлкейсом (например, 'Accountant')
    elif query.title() in MANUAL_FIX:
        logging.info(f"Swedish translation for '{query}' found in MANUAL_FIX (title match): {MANUAL_FIX[query.title()]}")
        return MANUAL_FIX[query.title()]
    # 3. Если не нашли, используем генератор
    else:
        swedish = translate_en_to_sv(query)
        logging.info(f"Swedish translation for '{query}' generated via translate_en_to_sv: {swedish}")
        return swedish