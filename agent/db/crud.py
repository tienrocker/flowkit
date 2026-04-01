"""CRUD operations for all entities."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from agent.db.schema import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# ─── Character ──────────────────────────────────────────────

def create_character(name: str, description: str = None, reference_image_url: str = None, media_gen_id: str = None) -> dict:
    db = get_db()
    cid = _uuid()
    now = _now()
    db.execute(
        "INSERT INTO character (id, name, description, reference_image_url, media_gen_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (cid, name, description, reference_image_url, media_gen_id, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM character WHERE id=?", (cid,)).fetchone()
    db.close()
    return dict(row)


def get_character(cid: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM character WHERE id=?", (cid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_characters() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM character ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_character(cid: str, **kwargs) -> Optional[dict]:
    db = get_db()
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [cid]
    db.execute(f"UPDATE character SET {sets} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM character WHERE id=?", (cid,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_character(cid: str) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM character WHERE id=?", (cid,))
    db.commit()
    db.close()
    return cur.rowcount > 0


# ─── Project ────────────────────────────────────────────────

def create_project(name: str, description: str = None, language: str = "en") -> dict:
    db = get_db()
    pid = _uuid()
    now = _now()
    db.execute(
        "INSERT INTO project (id, name, description, language, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (pid, name, description, language, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM project WHERE id=?", (pid,)).fetchone()
    db.close()
    return dict(row)


def get_project(pid: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM project WHERE id=?", (pid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_projects(status: str = None) -> list[dict]:
    db = get_db()
    if status:
        rows = db.execute("SELECT * FROM project WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM project ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_project(pid: str, **kwargs) -> Optional[dict]:
    db = get_db()
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [pid]
    db.execute(f"UPDATE project SET {sets} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM project WHERE id=?", (pid,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_project(pid: str) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM project WHERE id=?", (pid,))
    db.commit()
    db.close()
    return cur.rowcount > 0


def link_character_to_project(project_id: str, character_id: str) -> bool:
    db = get_db()
    try:
        db.execute("INSERT INTO project_character (project_id, character_id) VALUES (?,?)", (project_id, character_id))
        db.commit()
        return True
    except Exception:
        return False
    finally:
        db.close()


def unlink_character_from_project(project_id: str, character_id: str) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM project_character WHERE project_id=? AND character_id=?", (project_id, character_id))
    db.commit()
    db.close()
    return cur.rowcount > 0


def get_project_characters(project_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT c.* FROM character c JOIN project_character pc ON c.id=pc.character_id WHERE pc.project_id=?",
        (project_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ─── Video ──────────────────────────────────────────────────

def create_video(project_id: str, title: str, description: str = None, display_order: int = 0) -> dict:
    db = get_db()
    vid = _uuid()
    now = _now()
    db.execute(
        "INSERT INTO video (id, project_id, title, description, display_order, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (vid, project_id, title, description, display_order, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM video WHERE id=?", (vid,)).fetchone()
    db.close()
    return dict(row)


def get_video(vid: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM video WHERE id=?", (vid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_videos(project_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM video WHERE project_id=? ORDER BY display_order", (project_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_video(vid: str, **kwargs) -> Optional[dict]:
    db = get_db()
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [vid]
    db.execute(f"UPDATE video SET {sets} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM video WHERE id=?", (vid,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_video(vid: str) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM video WHERE id=?", (vid,))
    db.commit()
    db.close()
    return cur.rowcount > 0


# ─── Scene ──────────────────────────────────────────────────

def create_scene(video_id: str, display_order: int, prompt: str, character_names: list[str] = None,
                 parent_scene_id: str = None, chain_type: str = "ROOT") -> dict:
    db = get_db()
    sid = _uuid()
    now = _now()
    chars_json = json.dumps(character_names) if character_names else None
    db.execute(
        """INSERT INTO scene (id, video_id, display_order, prompt, character_names, parent_scene_id, chain_type, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sid, video_id, display_order, prompt, chars_json, parent_scene_id, chain_type, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM scene WHERE id=?", (sid,)).fetchone()
    db.close()
    return dict(row)


def get_scene(sid: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM scene WHERE id=?", (sid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_scenes(video_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM scene WHERE video_id=? ORDER BY display_order", (video_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_scene(sid: str, **kwargs) -> Optional[dict]:
    db = get_db()
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [sid]
    db.execute(f"UPDATE scene SET {sets} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM scene WHERE id=?", (sid,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_scene(sid: str) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM scene WHERE id=?", (sid,))
    db.commit()
    db.close()
    return cur.rowcount > 0


# ─── Request ────────────────────────────────────────────────

def create_request(scene_id: str, req_type: str, orientation: str,
                   project_id: str = None, video_id: str = None, character_id: str = None) -> dict:
    db = get_db()
    rid = _uuid()
    now = _now()
    db.execute(
        """INSERT INTO request (id, project_id, video_id, scene_id, character_id, type, orientation, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (rid, project_id, video_id, scene_id, character_id, req_type, orientation, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM request WHERE id=?", (rid,)).fetchone()
    db.close()
    return dict(row)


def get_request(rid: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM request WHERE id=?", (rid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_requests(scene_id: str = None, status: str = None) -> list[dict]:
    db = get_db()
    q = "SELECT * FROM request WHERE 1=1"
    params = []
    if scene_id:
        q += " AND scene_id=?"
        params.append(scene_id)
    if status:
        q += " AND status=?"
        params.append(status)
    q += " ORDER BY created_at DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_request(rid: str, **kwargs) -> Optional[dict]:
    db = get_db()
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [rid]
    db.execute(f"UPDATE request SET {sets} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM request WHERE id=?", (rid,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_pending_requests() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM request WHERE status='PENDING' ORDER BY created_at").fetchall()
    db.close()
    return [dict(r) for r in rows]
