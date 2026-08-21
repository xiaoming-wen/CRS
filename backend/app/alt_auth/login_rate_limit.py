"""
登录限流（进程内内存）：
- 同 IP：滑动窗口内尝试次数上限
- 同用户名：连续失败达到阈值后临时锁定

多进程/多机部署时各进程独立计数；需要全局一致请改 Redis。
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from app.alt_auth import settings as alt_settings

_lock = threading.Lock()
_ip_hits: Dict[str, Deque[float]] = defaultdict(deque)
_user_fails: Dict[str, int] = defaultdict(int)
_user_locked_until: Dict[str, float] = {}


def _now() -> float:
    return time.time()


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
    window = max(10, int(getattr(alt_settings, "LOGIN_IP_WINDOW_SECONDS", 60) or 60))
    ip_max = max(1, int(getattr(alt_settings, "LOGIN_IP_MAX_ATTEMPTS", 20) or 20))

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

        # IP 滑动窗口
        q = _ip_hits[ip]
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()
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
