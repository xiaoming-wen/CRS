"""竞赛试卷（按赛道）与分题提交配置的读写辅助。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

WORK_TRACKS = ("works", "software", "hardware")
QUESTION_CONFIG_TRACKS = ("works", "software", "hardware")
MAX_QUESTION_COUNT = 5


def _as_dict(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    s = str(raw).strip()
    if not s:
        return {}
    try:
        data = json.loads(s)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def dumps_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def default_track_question_config(question_count: int = 5) -> Dict[str, Any]:
    n = max(1, min(MAX_QUESTION_COUNT, int(question_count) or 5))
    questions = [
        {
            "no": i,
            "name": f"第{i}题",
            "min_score": 0.0,
            "max_score": 100.0,
        }
        for i in range(1, n + 1)
    ]
    total_max = sum(float(q["max_score"]) for q in questions)
    return {
        "question_count": n,
        "questions": questions,
        "total_min_score": 0.0,
        "total_max_score": float(total_max),
    }


def normalize_track_question_config(raw: Any) -> Dict[str, Any]:
    """规范化单赛道（software/hardware）分题配置。"""
    data = _as_dict(raw) if not isinstance(raw, dict) else dict(raw)
    if not data:
        return default_track_question_config(5)

    try:
        count = int(data.get("question_count") or 0)
    except (TypeError, ValueError):
        count = 0
    if count < 1 or count > MAX_QUESTION_COUNT:
        count = 5

    src_qs = data.get("questions")
    if not isinstance(src_qs, list):
        src_qs = []
    by_no = {}
    for item in src_qs:
        if not isinstance(item, dict):
            continue
        try:
            no = int(item.get("no"))
        except (TypeError, ValueError):
            continue
        if no < 1 or no > MAX_QUESTION_COUNT:
            continue
        name = str(item.get("name") or f"第{no}题").strip() or f"第{no}题"
        try:
            min_s = float(item.get("min_score", 0))
        except (TypeError, ValueError):
            min_s = 0.0
        try:
            max_s = float(item.get("max_score", 100))
        except (TypeError, ValueError):
            max_s = 100.0
        if max_s < min_s:
            min_s, max_s = max_s, min_s
        by_no[no] = {
            "no": no,
            "name": name[:80],
            "min_score": float(min_s),
            "max_score": float(max_s),
        }

    questions = []
    for i in range(1, count + 1):
        if i in by_no:
            questions.append(by_no[i])
        else:
            questions.append(
                {"no": i, "name": f"第{i}题", "min_score": 0.0, "max_score": 100.0}
            )

    try:
        total_min = float(data.get("total_min_score", 0))
    except (TypeError, ValueError):
        total_min = 0.0
    sum_max = sum(float(q["max_score"]) for q in questions)
    try:
        total_max = float(data.get("total_max_score", sum_max))
    except (TypeError, ValueError):
        total_max = sum_max
    if total_max < total_min:
        total_min, total_max = total_max, total_min

    return {
        "question_count": count,
        "questions": questions,
        "total_min_score": float(total_min),
        "total_max_score": float(total_max),
    }


# 兼容旧名
normalize_submission_question_config = normalize_track_question_config
default_submission_question_config = default_track_question_config


def normalize_submission_question_config_by_track(raw: Any) -> Dict[str, Dict[str, Any]]:
    """
    规范化按赛道分题配置。
    新格式：{ works: {...}, software: {...}, hardware: {...} }
    旧格式（顶层含 question_count）：应用到 software / hardware；作品赛道用默认配置。
    """
    data = _as_dict(raw) if not isinstance(raw, dict) else dict(raw)
    if not data:
        return {
            "works": default_track_question_config(5),
            "software": default_track_question_config(5),
            "hardware": default_track_question_config(5),
        }

    # 旧扁平格式（仅软件/硬件；作品赛道独立默认，避免把提交题配置误套到作品评分）
    if "question_count" in data or "questions" in data:
        shared = normalize_track_question_config(data)
        return {
            "works": default_track_question_config(5),
            "software": shared,
            "hardware": dict(shared),
        }

    out = {}
    for track in QUESTION_CONFIG_TRACKS:
        if track in data and isinstance(data[track], dict):
            out[track] = normalize_track_question_config(data[track])
        else:
            out[track] = default_track_question_config(5)
    return out


def get_competition_question_config_by_track(competition) -> Dict[str, Dict[str, Any]]:
    raw = getattr(competition, "submission_question_config", None)
    return normalize_submission_question_config_by_track(raw)


def get_competition_question_config(competition, work_track: Optional[str] = None) -> Dict[str, Any]:
    """取某一赛道配置；未指定时默认 software（兼容旧调用）。作品赛道配置仅用于专家评分。"""
    by_track = get_competition_question_config_by_track(competition)
    track = str(work_track or "").strip().lower()
    if track in QUESTION_CONFIG_TRACKS:
        return by_track[track]
    return by_track.get("software") or default_track_question_config(5)


def get_competition_question_count(competition, work_track: Optional[str] = None) -> int:
    cfg = get_competition_question_config(competition, work_track)
    return int(cfg.get("question_count") or 5)


def question_name_map(competition, work_track: Optional[str] = None) -> Dict[int, str]:
    cfg = get_competition_question_config(competition, work_track)
    out = {}
    for q in cfg.get("questions") or []:
        try:
            no = int(q.get("no"))
        except (TypeError, ValueError):
            continue
        out[no] = str(q.get("name") or f"第{no}题")
    return out


def get_exam_papers_by_track_map(competition) -> Dict[str, Dict[str, Dict[str, str]]]:
    """division -> work_track -> {path, filename}"""
    data = _as_dict(getattr(competition, "exam_papers_by_track", None))
    out: Dict[str, Dict[str, Dict[str, str]]] = {}
    for div, tracks in data.items():
        if not isinstance(tracks, dict):
            continue
        div_key = str(div).strip().lower()
        if div_key not in ("default", "undergraduate", "vocational"):
            continue
        slot: Dict[str, Dict[str, str]] = {}
        for track, meta in tracks.items():
            t = str(track).strip().lower()
            if t not in WORK_TRACKS or not isinstance(meta, dict):
                continue
            path = meta.get("path")
            if not path or not str(path).strip():
                continue
            slot[t] = {
                "path": str(path).strip(),
                "filename": str(meta.get("filename") or "").strip() or None,
            }
        if slot:
            out[div_key] = slot
    return out


def set_exam_paper_track_file(
    competition,
    division: str,
    work_track: str,
    path: str,
    filename: str,
) -> Optional[str]:
    """写入按赛道试卷，返回被覆盖的旧 path（用于删除）。"""
    div = str(division or "default").strip().lower()
    track = str(work_track or "").strip().lower()
    if track not in WORK_TRACKS:
        raise HTTPException(status_code=400, detail="work_track must be works/software/hardware")
    data = get_exam_papers_by_track_map(competition)
    old = None
    if div in data and track in data[div]:
        old = data[div][track].get("path")
    data.setdefault(div, {})[track] = {"path": path, "filename": filename}
    competition.exam_papers_by_track = dumps_json(data)
    return old if old and old != path else None


def get_exam_paper_track_file(
    competition, division: str, work_track: str
) -> Tuple[Optional[str], Optional[str]]:
    div = str(division or "default").strip().lower()
    track = str(work_track or "").strip().lower()
    data = get_exam_papers_by_track_map(competition)
    meta = (data.get(div) or {}).get(track)
    if meta:
        return meta.get("path"), meta.get("filename")
    return None, None


def validate_grade_against_config(
    competition, scores: Dict[int, float], total: float, work_track: Optional[str] = None
) -> None:
    cfg = get_competition_question_config(competition, work_track)
    count = int(cfg["question_count"])
    for q in cfg.get("questions") or []:
        no = int(q["no"])
        if no > count:
            continue
        if no not in scores:
            continue
        val = float(scores[no])
        mn = float(q["min_score"])
        mx = float(q["max_score"])
        if val < mn or val > mx:
            raise HTTPException(
                status_code=400,
                detail=f"第{no}题分数须在 {mn}～{mx} 之间（当前 {val}）",
            )
    tmin = float(cfg.get("total_min_score") or 0)
    tmax = float(cfg.get("total_max_score") or 0)
    if total < tmin or total > tmax:
        raise HTTPException(
            status_code=400,
            detail=f"总分须在 {tmin}～{tmax} 之间（当前 {total}）",
        )
