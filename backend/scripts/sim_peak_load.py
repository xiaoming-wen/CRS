#!/usr/bin/env python3
"""
模拟高峰：并发登录 / 下载试卷 / 提交作品（默认打本机，不打正式站）。

在 backend 目录：
  python scripts/sim_peak_load.py
  python scripts/sim_peak_load.py --users 50 --scene login
  python scripts/sim_peak_load.py --users 20 --scene download --competition-id 58582342 --division undergraduate --work-track software
  python scripts/sim_peak_load.py --users 500 --scene peak --competition-id 58582342

环境变量 BASE 可覆盖地址，例如 http://127.0.0.1:8000
正式域名请显式传 --base，避免误压生产。
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

DEFAULT_USERS = [
    ("hfu_stu1", "Demo123456"),
    ("hfu_stu2", "Demo123456"),
]


def http_json(
    method: str,
    url: str,
    body: Optional[dict] = None,
    token: Optional[str] = None,
    timeout: float = 60.0,
) -> Tuple[int, bytes, float]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, raw, time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        raw = e.read() if e.fp else b""
        return e.code, raw, time.perf_counter() - t0
    except Exception as e:
        return 0, str(e).encode("utf-8", errors="replace"), time.perf_counter() - t0


def login(base: str, username: str, password: str) -> Tuple[int, Optional[str], float]:
    status, raw, elapsed = http_json(
        "POST",
        f"{base}/api/alt-identity/session",
        {"username": username, "password": password},
    )
    token = None
    if status == 200:
        try:
            token = json.loads(raw.decode("utf-8")).get("access_token")
        except Exception:
            token = None
    return status, token, elapsed


def submit_work(
    base: str,
    token: str,
    competition_id: int,
    team_id: int,
) -> Tuple[int, float, str]:
    """正式提交（软件/硬件赛道：标记题目答案）。无答案或赛期关闭时仍会打到校验逻辑。"""
    data = urllib.parse.urlencode({"team_id": int(team_id)}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    req = urllib.request.Request(
        f"{base}/api/v1/competitions/{competition_id}/question-answers/submit",
        data=data,
        headers=headers,
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, time.perf_counter() - t0, raw[:180].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read() if e.fp else b""
        return e.code, time.perf_counter() - t0, raw[:180].decode("utf-8", "replace")
    except Exception as e:
        return 0, time.perf_counter() - t0, str(e)


def enrollments_me(base: str, token: str) -> list:
    st, raw, _ = http_json("GET", f"{base}/api/v1/competitions/enrollments/me", token=token)
    if st != 200:
        return []
    try:
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def demo_tokens(base: str) -> List[str]:
    tokens: List[str] = []
    for username, password in DEFAULT_USERS:
        st, token, _ = login(base, username, password)
        if st == 200 and token:
            tokens.append(token)
    return tokens


def download_paper(
    base: str,
    token: str,
    competition_id: int,
    division: str,
    work_track: str,
) -> Tuple[int, int, float]:
    q = urllib.parse.urlencode({"division": division, "work_track": work_track})
    url = f"{base}/api/v1/competitions/{competition_id}/exam-papers/download?{q}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            n = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                n += len(chunk)
            return resp.status, n, time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, 0, time.perf_counter() - t0
    except Exception:
        return 0, 0, time.perf_counter() - t0


def one_vu(args, idx: int) -> dict:
    if args.account_mode == "demo":
        username, password = DEFAULT_USERS[idx % len(DEFAULT_USERS)]
    else:
        username, password = f"simu{idx:04d}", "LoadTest123"
    out = {"idx": idx, "user": username, "login_status": 0, "login_s": 0.0, "dl_status": None, "dl_s": None, "dl_bytes": None}
    st, token, elapsed = login(args.base, username, password)
    out["login_status"] = st
    out["login_s"] = round(elapsed, 3)
    if args.scene in ("download", "submit", "all") and token and args.competition_id:
        dst, nbytes, dsel = download_paper(
            args.base, token, args.competition_id, args.division, args.work_track
        )
        out["dl_status"] = dst
        out["dl_s"] = round(dsel, 3)
        out["dl_bytes"] = nbytes
    if args.scene in ("submit", "all") and token and args.competition_id and args.team_id:
        sst, ssel, sdetail = submit_work(args.base, token, args.competition_id, args.team_id)
        out["sub_status"] = sst
        out["sub_s"] = round(ssel, 3)
        out["sub_detail"] = sdetail
    return out


def run_pool(n: int, fn, *fn_args) -> List[dict]:
    rows: List[dict] = []
    workers = max(1, min(n, 1000))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fn, *fn_args, i) for i in range(n)]
        for f in as_completed(futs):
            rows.append(f.result())
    return rows


def vu_download_only(args, token: str, idx: int) -> dict:
    dst, nbytes, dsel = download_paper(
        args.base, token, args.competition_id, args.division, args.work_track
    )
    return {"idx": idx, "dl_status": dst, "dl_s": round(dsel, 3), "dl_bytes": nbytes}


ROSTER_PATH = os.path.join(os.path.dirname(__file__), "loadtest_submit_roster.json")


def load_roster(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def vu_submit_roster(args, idx: int) -> dict:
    item = args.roster_users[idx]
    username = item["username"]
    team_id = int(item["team_id"])
    out = {
        "idx": idx,
        "user": username,
        "team_id": team_id,
        "login_status": 0,
        "login_s": 0.0,
        "sub_status": None,
        "sub_s": None,
        "sub_detail": "",
    }
    st, token, elapsed = login(args.base, username, args.roster_password)
    out["login_status"] = st
    out["login_s"] = round(elapsed, 3)
    if not token:
        out["sub_status"] = 0
        out["sub_detail"] = f"login {st}"
        return out
    sst, ssel, sdetail = submit_work(args.base, token, args.competition_id, team_id)
    out["sub_status"] = sst
    out["sub_s"] = round(ssel, 3)
    out["sub_detail"] = sdetail
    return out


def summarize(rows: List[dict], key_status: str, key_s: str, label: str) -> None:
    ok = [r for r in rows if r.get(key_status) == 200]
    times = [r[key_s] for r in rows if r.get(key_s) is not None]
    codes = {}
    for r in rows:
        c = r.get(key_status)
        codes[c] = codes.get(c, 0) + 1
    print(f"\n[{label}] 总请求 {len(rows)}  成功(200) {len(ok)}")
    print(f"  状态码: {codes}")
    if times:
        times_sorted = sorted(times)
        p95 = times_sorted[min(len(times_sorted) - 1, int(len(times_sorted) * 0.95))]
        print(
            f"  耗时秒: min={min(times):.3f}  avg={statistics.mean(times):.3f}  "
            f"p95={p95:.3f}  max={max(times):.3f}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description="模拟并发登录/下载（默认本机）")
    p.add_argument("--base", default=os.getenv("BASE", "http://127.0.0.1:8000"), help="API 根，默认本机")
    p.add_argument("--users", type=int, default=30, help="并发虚拟用户数")
    p.add_argument(
        "--account-mode",
        choices=["unique", "demo"],
        default="unique",
        help="unique=每人不同用户名（模拟 500/1000 人同时登录）；demo=轮询 hfu_stu1/2",
    )
    p.add_argument(
        "--scene",
        choices=["login", "download", "submit", "all", "peak", "submit-burst"],
        default="login",
        help="peak=登录+下载+按不同队伍提交；submit-burst=只压提交",
    )
    p.add_argument("--competition-id", type=int, default=58582342)
    p.add_argument("--team-id", type=int, default=None)
    p.add_argument("--division", default="undergraduate")
    p.add_argument("--roster", default=ROSTER_PATH, help="seed_loadtest_submitters.py 生成的花名册")
    args = p.parse_args()
    args.base = args.base.rstrip("/")

    if "damoxingcr.cn" in args.base and os.getenv("ALLOW_PROD_LOADTEST") != "1":
        print("拒绝默认压测正式站。确认维护窗口后设置 ALLOW_PROD_LOADTEST=1 并显式 --base")
        return 2

    print(f"目标 {args.base}  并发 {args.users}  场景 {args.scene}  账号 {args.account_mode}")

    if args.scene == "peak":
        t0 = time.perf_counter()
        print("\n== 1/3 登录（每人不同用户名，走进校验）==")
        args.account_mode = "unique"
        args.scene = "login"
        login_rows = run_pool(args.users, one_vu, args)
        summarize(login_rows, "login_status", "login_s", "登录")

        tokens = demo_tokens(args.base)
        if not tokens:
            print("demo 账号无法登录，跳过下载/提交")
            print(f"墙钟 {time.perf_counter() - t0:.2f}s")
            return 0
        if not args.team_id:
            ens = enrollments_me(args.base, tokens[0])
            hit = next(
                (
                    e
                    for e in ens
                    if int(e.get("competition_id") or 0) == int(args.competition_id)
                    and e.get("team_id")
                ),
                ens[0] if ens else None,
            )
            if hit:
                args.competition_id = int(hit.get("competition_id") or args.competition_id)
                args.team_id = int(hit["team_id"])
                if hit.get("work_track"):
                    args.work_track = str(hit["work_track"])
                if hit.get("division"):
                    args.division = str(hit["division"])
        print(
            f"demo token {len(tokens)} 个  competition={args.competition_id}  "
            f"team={args.team_id}  track={args.work_track}"
        )

        print("\n== 2/3 下载试卷（已登录学生并发拉文件）==")
        dl_rows = run_pool(
            args.users, vu_download_only, args, tokens[0]
        )
        summarize(dl_rows, "dl_status", "dl_s", "下载试卷")
        sizes = [r["dl_bytes"] for r in dl_rows if r.get("dl_bytes")]
        if sizes:
            print(f"  单次字节约 {int(statistics.mean(sizes))}")

        print("\n== 3/3 提交作品（每人不同 team_id；本机无对应队伍则为 404）==")
        sub_rows = run_pool(args.users, vu_submit_only, args, tokens[0])
        summarize(sub_rows, "sub_status", "sub_s", "提交作品")
        details = {}
        for r in sub_rows:
            d = (r.get("sub_detail") or "")[:80]
            details[d] = details.get(d, 0) + 1
        print(f"  响应摘要: {details}")
        print(f"\n墙钟 {time.perf_counter() - t0:.2f}s")
        return 0

    if args.scene == "submit-burst":
        t0 = time.perf_counter()
        if not os.path.isfile(args.roster):
            print(f"缺少花名册 {args.roster}，请先: python scripts/seed_loadtest_submitters.py --count 1000")
            return 1
        roster = load_roster(args.roster)
        args.roster_users = roster.get("users") or []
        args.roster_password = roster.get("password") or "Demo123456"
        if roster.get("competition_id"):
            args.competition_id = int(roster["competition_id"])
        if len(args.roster_users) < args.users:
            print(f"花名册只有 {len(args.roster_users)} 人，少于并发 {args.users}")
            return 1
        print(f"花名册 {len(args.roster_users)} 人  competition={args.competition_id}")
        print("\n== 提交作品（每人独立账号/队伍，需已灌草稿答案）==")
        sub_rows = run_pool(args.users, vu_submit_roster, args)
        summarize(sub_rows, "login_status", "login_s", "登录")
        summarize(sub_rows, "sub_status", "sub_s", "提交作品")
        details = {}
        for r in sub_rows:
            d = (r.get("sub_detail") or "")[:80]
            details[d] = details.get(d, 0) + 1
        print(f"  响应摘要: {details}")
        print(f"墙钟 {time.perf_counter() - t0:.2f}s")
        return 0

    t0 = time.perf_counter()
    rows = run_pool(args.users, one_vu, args)
    print(f"墙钟 {time.perf_counter() - t0:.2f}s")
    summarize(rows, "login_status", "login_s", "登录")
    if args.scene in ("download", "submit", "all"):
        summarize(rows, "dl_status", "dl_s", "下载试卷")
    if args.scene in ("submit", "all"):
        summarize(rows, "sub_status", "sub_s", "提交作品")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
