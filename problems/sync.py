from urllib.parse import quote
import requests
from extensions import db
from models import Problem

BASE_LIST_URL = "https://leetcode-api-pied.vercel.app/problems"
BASE_ITEM_URL = "https://leetcode-api-pied.vercel.app/problem/{}"

def load_all_problems_once():
    # One-time loader: fetch full list and store id/title/link.
    resp = requests.get(BASE_LIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    added = 0
    for item in data:
        pid = item.get("id") or item.get("questionId") or item.get("problemId")
        title = item.get("title") or item.get("name")
        link = item.get("link") or item.get("url")
        if pid is None or not title:
            continue
        pid = int(pid)
        if not link:
            slug = quote(title)
            link = f"https://leetcode.com/problems/{slug}/"
        if not Problem.query.filter_by(leetcode_problem_id=pid).first():
            db.session.add(Problem(leetcode_problem_id=pid, title=title, link=link))
            added += 1
    db.session.commit()
    return added

def incremental_sync_from_current_size():
    # Weekly sync: query next ids from current local max id until failure.
    max_local = db.session.query(db.func.max(Problem.leetcode_problem_id)).scalar()
    if max_local is None:
        max_local = 0

    current = max_local + 1
    added = 0

    while True:
        try:
            resp = requests.get(BASE_ITEM_URL.format(current), timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break

            pid = data.get("id") or data.get("questionId") or current
            title = data.get("title") or data.get("name")
            link = data.get("link") or data.get("url")
            if not title:
                break
            if not link:
                slug = quote(title)
                link = f"https://leetcode.com/problems/{slug}/"

            existing = Problem.query.filter_by(leetcode_problem_id=int(pid)).first()
            if not existing:
                db.session.add(Problem(
                    leetcode_problem_id=int(pid),
                    title=title,
                    link=link
                ))
                db.session.commit()
                added += 1

            current += 1
        except Exception:
            break

    return added
