# app/autocomplete.py
import logging
from app.services import translate_sv_to_en

occupation_labels_sv = []

def autocomplete_occupation_labels(query_sv: str, limit: int = 10):
    """
    Находит подсказки по подстроке для occupation_labels_sv.
    Возвращает не более limit результатов.
    """
    if not query_sv:
        return []
    query_sv_lower = query_sv.lower()
    # Фильтруем все, где query_sv — подстрока, insensitive
    matches = [label for label in occupation_labels_sv if label and query_sv_lower in label.lower()]
    # Можно сделать чуть умнее (например, startswith — сначала, потом по вхождению, сортировка по популярности и т.п.)
    return matches[:limit]

