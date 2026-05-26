#!/usr/bin/env python3
"""
将竞赛相关表中 **旧语义** 的 ``users.id`` 整型引用，改写为 ``alt_auth_users.id``。

匹配规则（按顺序）：
1. ``users.username`` 与 ``alt_auth_users.username`` 去空白后完全一致（大小写敏感，与登录一致）；
2. 否则 ``lower(trim(users.email))`` 与 ``lower(trim(alt_auth_users.email))`` 一致。

可选 CSV 覆盖：``--mapping-csv path.csv``，两列 ``main_user_id,alt_user_id``（无表头或首行为表头均可），
后读入的映射覆盖自动推断。

用法（在项目根目录执行）::

    python scripts/migrate_competition_user_ids_to_alt.py --dry-run
    python scripts/migrate_competition_user_ids_to_alt.py

环境变量与主应用一致：``DATABASE_URL``、``ALT_AUTH_DATABASE_URL``（默认 ``sqlite:///./alt_auth.db``）。

**注意**：SQLite 下会临时 ``PRAGMA foreign_keys=OFF`` 以便在仍残留 ``REFERENCES users`` 的旧库上更新；
生产 PostgreSQL/MySQL 若已无指向 ``users`` 的外键，可忽略。迁移前请 **备份数据库**。
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _sqlite_connect_args(url: str) -> dict:
    return {"check_same_thread": False} if "sqlite" in url.lower() else {}


def _make_engine(url: str) -> Engine:
    return create_engine(url, connect_args=_sqlite_connect_args(url))


def _norm_email(v: Optional[str]) -> str:
    if v is None:
        return ""
    return str(v).strip().lower()


def _norm_username(v: Optional[str]) -> str:
    if v is None:
        return ""
    return str(v).strip()


def load_mapping_csv(path: Path) -> Dict[int, int]:
    out: Dict[int, int] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            a, b = row[0].strip(), row[1].strip()
            if a.lower() in ("main_user_id", "user_id", "users_id", "gateway_user_id", "alt_user_id"):
                continue
            try:
                out[int(a)] = int(b)
            except ValueError:
                continue
    return out


def build_auto_map(main_engine: Engine, alt_engine: Engine) -> Tuple[Dict[int, int], List[str]]:
    """
    main_user_id -> alt_user_id
    """
    warnings: List[str] = []
    by_username: Dict[str, List[int]] = {}
    by_email: Dict[str, List[int]] = {}

    with alt_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, email FROM alt_auth_users")
        ).mappings().all()
    for r in rows:
        aid = int(r["id"])
        un = _norm_username(r.get("username"))
        em = _norm_email(r.get("email"))
        if un:
            by_username.setdefault(un, []).append(aid)
        if em:
            by_email.setdefault(em, []).append(aid)

    for key, lst in list(by_username.items()) + list(by_email.items()):
        if len(lst) > 1:
            uniq = sorted(set(lst))
            if len(uniq) > 1:
                warnings.append(
                    f"Alt 帐号按键 {key!r} 对应多个 id {uniq}，自动映射时仅使用最小 id {uniq[0]}"
                )

    def pick_alt(username: str, email: str) -> Optional[int]:
        un = _norm_username(username)
        em = _norm_email(email)
        if un and un in by_username:
            return min(by_username[un])
        if em and em in by_email:
            return min(by_email[em])
        return None

    uid_to_alt: Dict[int, int] = {}
    with main_engine.connect() as conn:
        users = conn.execute(
            text("SELECT id, username, email FROM users")
        ).mappings().all()
    for u in users:
        uid = int(u["id"])
        alt_id = pick_alt(u.get("username"), u.get("email"))
        if alt_id is not None:
            uid_to_alt[uid] = alt_id

    return uid_to_alt, warnings


def collect_distinct_user_ids(main_engine: Engine) -> Set[int]:
    ids: Set[int] = set()
    stmts = [
        "SELECT DISTINCT student_id AS x FROM competition_enrollments WHERE student_id IS NOT NULL",
        "SELECT DISTINCT captain_id AS x FROM teams WHERE captain_id IS NOT NULL",
        "SELECT DISTINCT user_id AS x FROM team_members WHERE user_id IS NOT NULL",
        "SELECT DISTINCT student_id AS x FROM submissions WHERE student_id IS NOT NULL",
        "SELECT DISTINCT submitter_id AS x FROM submissions WHERE submitter_id IS NOT NULL",
        "SELECT DISTINCT reviewer_id AS x FROM reviews WHERE reviewer_id IS NOT NULL",
        "SELECT DISTINCT sender_id AS x FROM files WHERE sender_id IS NOT NULL",
        "SELECT DISTINCT receiver_id AS x FROM files WHERE receiver_id IS NOT NULL",
    ]
    with main_engine.connect() as conn:
        for sql in stmts:
            try:
                for row in conn.execute(text(sql)):
                    v = row[0]
                    if v is not None:
                        ids.add(int(v))
            except Exception:
                # 表或列不存在时跳过（极简库）
                pass
    return ids


def count_replacements(main_engine: Engine, active_map: Dict[int, int]) -> Dict[str, int]:
    """dry-run：按列统计将出现多少行匹配旧 id（逐 old_id COUNT 累加）。"""
    specs: List[Tuple[str, str]] = [
        ("competition_enrollments.student_id", "SELECT COUNT(*) FROM competition_enrollments WHERE student_id = :old"),
        ("teams.captain_id", "SELECT COUNT(*) FROM teams WHERE captain_id = :old"),
        ("team_members.user_id", "SELECT COUNT(*) FROM team_members WHERE user_id = :old"),
        ("submissions.student_id", "SELECT COUNT(*) FROM submissions WHERE student_id = :old"),
        ("submissions.submitter_id", "SELECT COUNT(*) FROM submissions WHERE submitter_id = :old"),
        ("reviews.reviewer_id", "SELECT COUNT(*) FROM reviews WHERE reviewer_id = :old"),
        ("files.sender_id", "SELECT COUNT(*) FROM files WHERE sender_id = :old"),
        ("files.receiver_id", "SELECT COUNT(*) FROM files WHERE receiver_id = :old"),
    ]
    counts: Dict[str, int] = {}
    with main_engine.connect() as conn:
        for label, sql in specs:
            n = 0
            for old_id in active_map:
                try:
                    row = conn.execute(text(sql), {"old": old_id}).scalar()
                    n += int(row or 0)
                except Exception:
                    pass
            counts[label] = n
    return counts


def apply_replacements(main_engine: Engine, active_map: Dict[int, int]) -> Dict[str, int]:
    updates: List[Tuple[str, str]] = [
        ("competition_enrollments", "UPDATE competition_enrollments SET student_id = :new WHERE student_id = :old"),
        ("teams", "UPDATE teams SET captain_id = :new WHERE captain_id = :old"),
        ("team_members", "UPDATE team_members SET user_id = :new WHERE user_id = :old"),
        ("submissions.student_id", "UPDATE submissions SET student_id = :new WHERE student_id = :old"),
        ("submissions.submitter_id", "UPDATE submissions SET submitter_id = :new WHERE submitter_id = :old"),
        ("reviews", "UPDATE reviews SET reviewer_id = :new WHERE reviewer_id = :old"),
        ("files.sender_id", "UPDATE files SET sender_id = :new WHERE sender_id = :old"),
        ("files.receiver_id", "UPDATE files SET receiver_id = :new WHERE receiver_id = :old"),
    ]
    counts: Dict[str, int] = {}
    with main_engine.begin() as conn:
        if "sqlite" in str(main_engine.url).lower():
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        for label, sql in updates:
            total = 0
            for old_id, new_id in active_map.items():
                try:
                    res = conn.execute(text(sql), {"old": old_id, "new": new_id})
                    total += res.rowcount or 0
                except Exception:
                    pass
            counts[label] = total
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印映射与统计，不写库",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=None,
        help="可选：main_user_id,alt_user_id 覆盖/补充自动映射",
    )
    args = parser.parse_args()

    from app.config import get_settings
    from app.alt_auth.settings import ALT_AUTH_DATABASE_URL

    settings = get_settings()
    main_url = settings.DATABASE_URL
    alt_url = ALT_AUTH_DATABASE_URL

    main_engine = _make_engine(main_url)
    alt_engine = _make_engine(alt_url)

    auto_map, warns = build_auto_map(main_engine, alt_engine)
    merged: Dict[int, int] = dict(auto_map)
    if args.mapping_csv and args.mapping_csv.is_file():
        csv_map = load_mapping_csv(args.mapping_csv)
        merged.update(csv_map)
        print(f"自 CSV 合并 {len(csv_map)} 条覆盖/补充映射")

    used_ids = collect_distinct_user_ids(main_engine)
    unmapped = sorted(used_ids - set(merged.keys()))

    print("=== 主库 users.id → alt_auth_users.id 映射 ===")
    print(f"自动推断: {len(auto_map)} 个用户有匹配 Alt 帐号")
    print(f"合并后可用于替换的映射条目: {len(merged)}")
    for w in warns[:20]:
        print(f"  [WARN] {w}")
    if len(warns) > 20:
        print(f"  ... 另有 {len(warns) - 20} 条警告")

    print("\n=== 竞赛相关表中出现、但未映射到的 users.id ===")
    if not unmapped:
        print("（无）所有出现过的 id 均有映射")
    else:
        print(f"共 {len(unmapped)} 个: {unmapped[:50]}{'...' if len(unmapped) > 50 else ''}")
        print("这些行不会被改写；请补全 Alt 帐号（同 username/email）或写入 --mapping-csv")

    # 仅对「实际出现在竞赛相关列中」的 old_id 执行 UPDATE，避免误伤其它业务里碰巧相同的整数
    active_map = {o: n for o, n in merged.items() if o in used_ids and o != n}
    if not active_map:
        print("\n无需写入（无待替换 id 或已全部一致）")
        return 0

    if args.dry_run:
        print("\n[dry-run] 不写库。将执行的 id 替换对（old→new）示例（最多 20 条）：")
        for i, (o, n_id) in enumerate(sorted(active_map.items())):
            print(f"  {o} → {n_id}")
            if i >= 19:
                print("  ...")
                break
        cnt = count_replacements(main_engine, active_map)
        print("\n[dry-run] 各列将匹配行数（按旧 id 逐条 COUNT 累加，非 0 才列出）：")
        for k, v in sorted(cnt.items()):
            if v:
                print(f"  {k}: {v}")
        print("\n[dry-run] 结束")
        return 0

    print(f"\n开始写库，共 {len(active_map)} 对 (old→new) …")
    counts = apply_replacements(main_engine, active_map)
    print("各表累计受影响行数（同一 old 多列会重复计数，仅供参考）：")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")

    print("\n完成。请重启应用并抽样校验竞赛报名 / 队伍 / 作品接口。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
