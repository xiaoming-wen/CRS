"""
将第二套帐号 role 映射为与主站一致的 Permission 可读列表。
仅依赖 app.permissions 中的 ROLE_PERMISSIONS 常量字典（不涉及 User 模型或主 JWT）。
"""
from app.permissions import ROLE_PERMISSIONS, Permission


def list_effective_permissions_for_role(role: str) -> list[str]:
    """
    返回该角色具备的权限枚举值字符串列表；
    unknown role 视作无权限。
    """
    grants = ROLE_PERMISSIONS.get(role) or ()
    return [p.value for p in grants]


def role_has_permission(role: str, required: Permission) -> bool:
    """与主站 check_permission(role, Permission.xxx) 语义一致。"""
    grants = ROLE_PERMISSIONS.get(role) or ()
    return required in grants
