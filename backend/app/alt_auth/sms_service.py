"""阿里云短信验证码发送。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests

from app.alt_auth import settings as alt_settings

logger = logging.getLogger(__name__)


def _percent_encode(value: str) -> str:
    return urllib.parse.quote(str(value), safe="~")


def _sign_aliyun_rpc(params: Dict[str, str], access_key_secret: str) -> str:
    sorted_keys = sorted(params.keys())
    canonicalized = "&".join(
        f"{_percent_encode(k)}={_percent_encode(params[k])}" for k in sorted_keys
    )
    string_to_sign = f"GET&%2F&{_percent_encode(canonicalized)}"
    key = (access_key_secret + "&").encode("utf-8")
    digest = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def sms_config_ready() -> bool:
    return bool(
        (alt_settings.ALIYUN_SMS_ACCESS_KEY_ID or "").strip()
        and (alt_settings.ALIYUN_SMS_ACCESS_KEY_SECRET or "").strip()
        and (alt_settings.ALIYUN_SMS_SIGN_NAME or "").strip()
        and (alt_settings.ALIYUN_SMS_TEMPLATE_CODE or "").strip()
    )


def send_verification_sms(phone: str, code: str) -> Tuple[bool, str]:
    """
    发送注册验证码短信。
    返回 (ok, message)。
    """
    phone = (phone or "").strip()
    code = (code or "").strip()
    if not phone or not code:
        return False, "手机号或验证码为空"

    if not sms_config_ready():
        if alt_settings.ALIYUN_SMS_DEBUG:
            logger.warning(
                "ALIYUN SMS not fully configured; debug mode keeps code for phone=%s code=%s",
                phone,
                code,
            )
            return True, "debug"
        return False, "短信服务未配置（需 AccessKey、签名与模板）"

    access_key_id = alt_settings.ALIYUN_SMS_ACCESS_KEY_ID.strip()
    access_key_secret = alt_settings.ALIYUN_SMS_ACCESS_KEY_SECRET.strip()
    sign_name = alt_settings.ALIYUN_SMS_SIGN_NAME.strip()
    template_code = alt_settings.ALIYUN_SMS_TEMPLATE_CODE.strip()
    param_key = (alt_settings.ALIYUN_SMS_TEMPLATE_PARAM_KEY or "code").strip() or "code"
    region = (alt_settings.ALIYUN_SMS_REGION_ID or "cn-hangzhou").strip()

    template_param = json.dumps({param_key: code}, ensure_ascii=False)
    params: Dict[str, str] = {
        "AccessKeyId": access_key_id,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "RegionId": region,
        "SignName": sign_name,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "TemplateCode": template_code,
        "TemplateParam": template_param,
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    params["Signature"] = _sign_aliyun_rpc(params, access_key_secret)

    try:
        resp = requests.get(
            "https://dysmsapi.aliyuncs.com/",
            params=params,
            timeout=12,
        )
        data: Any = {}
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        code_out = str((data or {}).get("Code") or "")
        if resp.status_code == 200 and code_out.upper() == "OK":
            return True, "ok"
        msg = str((data or {}).get("Message") or data or resp.text)
        logger.error("Aliyun SMS send failed phone=%s status=%s body=%s", phone, resp.status_code, data)
        return False, msg or "短信发送失败"
    except Exception as e:
        logger.exception("Aliyun SMS request error: %s", e)
        return False, f"短信发送异常: {type(e).__name__}"
