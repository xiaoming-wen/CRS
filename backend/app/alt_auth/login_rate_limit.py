"""
登录限流（进程内内存）：
- 同 IP：滑动窗口内尝试次数上限（默认放宽，适配校园网 NAT 集中登录）
- 同用户名：窗口内尝试上限 + 连续失败达到阈值后临时锁定

多进程/多机部署时各进程独立计数；需要全局一致请改 Redis。
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from app.alt_auth import settings as alt_settings


def _int_setting(env_name: str, attr: str, default: int) -> int:
    raw = os.getenv(env_name)
    if raw is not None and str(raw).strip() != "":
        try:
            return int(str(raw).strip())
        except ValueError:
            pass
    return int(getattr(alt_settings, attr, default) or default)

_lock = threading.Lock()
_ip_hits: Dict[str, Deque[float]] = defaultdict(deque)
_user_hits: Dict[str, Deque[float]] = defaultdict(deque)
_user_fails: Dict[str, int] = defaultdict(int)
_user_locked_until: Dict[str, float] = {}


def _now() -> float:
    return time.time()


def _prune(q: Deque[float], cutoff: float) -> None:
    while q and q[0] < cutoff:
        q.popleft()


def client_ip_from_headers(x_forwarded_for: Optional[str], fallback: Optional[str]) -> str:
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    return (fallback or "").strip() or "unknown"


def check_login_allowed(*, ip: str, username: str) -> Optional[str]:
    """
    允许登录则返回 None；否则返回应对客户端展示的错误文案（由路由抛 429）。
    """
    ip = (ip or "unknown").strip() or "unknown"
    uname = (username or "").strip().lower()
    window = max(10, _int_setting("LOGIN_IP_WINDOW_SECONDS", "LOGIN_IP_WINDOW_SECONDS", 120))
    ip_max = max(1, _int_setting("LOGIN_IP_MAX_ATTEMPTS", "LOGIN_IP_MAX_ATTEMPTS", 10000))
    user_window = max(10, _int_setting("LOGIN_USER_WINDOW_SECONDS", "LOGIN_USER_WINDOW_SECONDS", 60))
    user_max = max(1, _int_setting("LOGIN_USER_MAX_ATTEMPTS", "LOGIN_USER_MAX_ATTEMPTS", 20))

    now = _now()
    with _lock:
        # 账号锁定
        if uname:
            until = _user_locked_until.get(uname)
            if until is not None:
                if now < until:
                    remain = max(1, int(until - now))
                    return f"登录失败次数过多，请 {remain} 秒后再试"
                _user_locked_until.pop(uname, None)
                _user_fails.pop(uname, None)

            uq = _user_hits[uname]
            _prune(uq, now - user_window)
            if len(uq) >= user_max:
                return "该账号尝试过于频繁，请稍后再试"
            uq.append(now)

        # IP 滑动窗口（NAT 出口会汇总大量真实用户，阈值需明显高于单机）
        q = _ip_hits[ip]
        _prune(q, now - window)
        if len(q) >= ip_max:
            return "尝试过于频繁，请稍后再试"

        q.append(now)
    return None


def record_login_failure(*, username: str) -> None:
    uname = (username or "").strip().lower()
    if not uname:
        return
    max_fails = max(1, int(getattr(alt_settings, "LOGIN_MAX_FAILS_BEFORE_LOCK", 5) or 5))
    lock_minutes = max(1, int(getattr(alt_settings, "LOGIN_LOCK_MINUTES", 15) or 15))
    now = _now()
    with _lock:
        _user_fails[uname] = int(_user_fails.get(uname, 0)) + 1
        if _user_fails[uname] >= max_fails:
            _user_locked_until[uname] = now + lock_minutes * 60
            _user_fails[uname] = 0


def clear_login_failures(*, username: str) -> None:
    uname = (username or "").strip().lower()
    if not uname:
        return
    with _lock:
        _user_fails.pop(uname, None)
        _user_locked_until.pop(uname, None)
