from app.db import get_connection


def load_occupation_labels():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT occupation_label FROM vacancies WHERE occupation_label IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return sorted(set(r[0] for r in rows if r[0]))