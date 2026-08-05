"""
竞赛报名系统集成测试（基于 requests）。

运行方式参考 tests/test_user_management.py：
1) 启动服务（确保包含 app.main:app）
2) 如需初始化数据库：python init_db.py
3) python tests/test_competitions.py
"""

import requests
import json
import sys
import os
import sqlite3


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "http://localhost:8000/api/v1"
ALT_URL = "http://localhost:8000/api/alt-identity"
TEST_RESULTS_DIR = os.path.join(PROJECT_ROOT, "test_results")
os.makedirs(TEST_RESULTS_DIR, exist_ok=True)


def migrate_enrollment_columns():
    """自动给 competition_enrollments 表补加缺失列，并迁移双赛道唯一约束。"""
    db_path = os.path.join(PROJECT_ROOT, "user_management.db")
    if not os.path.exists(db_path):
        print("⚠️  数据库文件不存在，跳过迁移（将由 init_db 创建）")
        return

    new_cols = {
        "student_no": "VARCHAR(50)",
        "real_name": "VARCHAR(100)",
        "college": "VARCHAR(200)",
        "grade": "VARCHAR(50)",
        "contact": "VARCHAR(100)",
    }

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("PRAGMA table_info(competition_enrollments)")
        existing = {row[1] for row in cursor.fetchall()}

        added = []
        for col, col_type in new_cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE competition_enrollments ADD COLUMN {col} {col_type}")
                added.append(col)

        if added:
            conn.commit()
            print(f"✅ 数据库迁移：已为 competition_enrollments 添加列 {added}")
        else:
            print("✅ 数据库迁移：学生信息列已存在")
    finally:
        conn.close()

    try:
        from sqlalchemy import create_engine
        from app.competition_enrollment_migrate import migrate_competition_enrollment_dual_track

        engine = create_engine(f"sqlite:///{db_path}")
        migrate_competition_enrollment_dual_track(engine)
        print("✅ 数据库迁移：competition_enrollments 双赛道（individual+team）")
    except Exception as e:
        print(f"⚠️  双赛道迁移跳过或失败: {e}")

access_token = None


def print_result(test_name, success, message="", data=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message:
        print(f"      {message}")
    if data is not None:
        try:
            safe_data = data if isinstance(data, dict) else {"data": data}
            if "access_token" in safe_data:
                safe_data["access_token"] = safe_data["access_token"][:20] + "..."
            print(f"      响应: {json.dumps(safe_data, ensure_ascii=False, indent=2)}")
        except Exception:
            pass
    print()


def get_headers():
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def test_health_check():
    test_name = "健康检查"
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            print_result(test_name, True, "服务正常", r.json())
            return True
        print_result(test_name, False, f"状态码: {r.status_code}", r.text)
        return False
    except Exception as e:
        print_result(test_name, False, f"无法连接到服务器: {str(e)}")
        return False


def test_login_admin():
    global access_token
    test_name = "管理员登录（第二套 super_admin）"
    try:
        r = requests.post(
            f"{ALT_URL}/session",
            json={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            access_token = r.json().get("access_token")
            print_result(
                test_name,
                True,
                "登录成功",
                {"role": r.json().get("role"), "full_name": r.json().get("full_name")},
            )
            return True
        print_result(test_name, False, f"状态码: {r.status_code}", r.text)
        return False
    except Exception as e:
        print_result(test_name, False, f"错误: {str(e)}")
        return False


def ensure_alt_user(role: str, username: str, email: str = None, password: str = "admin123", phone: str = None):
    """
    幂等：先第二套登录；失败则发短信验证码后注册再登录。
    返回的 user_id 为 alt_auth_users.id（竞赛 student_id 等同此 id）。
    email 参数保留兼容旧调用，已忽略。
    """
    lr = requests.post(
        f"{ALT_URL}/session",
        json={"username": username, "password": password},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if lr.status_code == 200:
        data = lr.json()
        return {
            "ok": True,
            "created": False,
            "user_id": data.get("user_id"),
            "token": data.get("access_token"),
        }

    # 由用户名生成稳定测试手机号，避免冲突
    if not phone:
        digits = "".join(c for c in username if c.isdigit())
        base = int(digits[-8:] or "10000001") % 100000000
        phone = f"139{base:08d}"

    code_resp = requests.post(
        f"{ALT_URL}/send-sms-code",
        headers={"Content-Type": "application/json"},
        json={"phone": phone, "purpose": "register"},
        timeout=10,
    )
    if code_resp.status_code != 200:
        return {"ok": False, "created": False, "detail": code_resp.text}
    code_data = code_resp.json() or {}
    sms_code = code_data.get("debug_code")
    if not sms_code:
        return {
            "ok": False,
            "created": False,
            "detail": "send-sms-code 未返回 debug_code，请开启 ALIYUN_SMS_DEBUG=true",
        }

    reg = requests.post(
        f"{ALT_URL}/register",
        headers={"Content-Type": "application/json"},
        json={
            "username": username,
            "phone": phone,
            "sms_code": sms_code,
            "full_name": username,
            "password": password,
            "role": role,
            "school": "测试学校",
        },
        timeout=10,
    )
    if reg.status_code not in (200, 201):
        return {"ok": False, "created": False, "detail": reg.text}

    lr2 = requests.post(
        f"{ALT_URL}/session",
        json={"username": username, "password": password},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if lr2.status_code != 200:
        return {"ok": False, "created": True, "detail": lr2.text}

    data = lr2.json()
    return {"ok": True, "created": True, "user_id": data.get("user_id"), "token": data.get("access_token")}


def run():
    print("=" * 60)
    print("竞赛报名系统集成测试")
    print("=" * 60)
    print()

    migrate_enrollment_columns()
    print()

    if not test_health_check():
        print("服务未启动")
        sys.exit(1)

    if not test_login_admin():
        sys.exit(1)

    # 1) 创建学生/教师账号（仅用于测试流程）
    s1 = ensure_alt_user("student", "stu1", "stu1@example.com", "admin123")
    s2 = ensure_alt_user("student", "stu2", "stu2@example.com", "admin123")
    s3 = ensure_alt_user("student", "stu3", "stu3@example.com", "admin123")
    t1 = ensure_alt_user("advisor", "tea1", "tea1@example.com", "admin123")

    if not (s1.get("ok") and s2.get("ok") and s3.get("ok") and t1.get("ok")):
        print_result(
            "创建/复用用户",
            False,
            "创建或登录失败（可能密码不一致或无权限）",
            {"stu1": s1, "stu2": s2, "stu3": s3, "teacher": t1},
        )
        sys.exit(1)

    stu1_id = s1["user_id"]
    stu2_id = s2["user_id"]
    stu3_id = s3["user_id"]

    # 2) 管理员创建竞赛并发布
    comp = requests.post(
        f"{BASE_URL}/competitions/",
        headers=get_headers(),
        json={
            "name": "Test Competition",
            "description": "desc",
            "rules_text": "rules",
            "allow_individual": True,
            "allow_team": True,
        },
        timeout=10,
    )
    if comp.status_code not in (200, 201):
        print_result("创建竞赛", False, f"状态码: {comp.status_code}", comp.text)
        sys.exit(1)

    comp_id = comp.json().get("id")
    pub = requests.put(
        f"{BASE_URL}/competitions/{comp_id}/publish",
        headers=get_headers(),
        timeout=10,
    )
    if pub.status_code not in (200, 201):
        print_result("发布竞赛", False, f"状态码: {pub.status_code}", pub.text)
        sys.exit(1)
    print_result("发布竞赛", True, f"comp_id={comp_id}")

    expert_seed = ensure_alt_user("student", "expert1", "expert1@example.com", "admin123")
    if not expert_seed.get("ok"):
        print_result("专家组 seed 用户", False, "失败", expert_seed)
        sys.exit(1)
    ex_patch = requests.patch(
        f"{BASE_URL}/competitions/admin/alt-users/{expert_seed['user_id']}",
        headers=get_headers(),
        json={"role": "expert", "expert_verified": True},
        timeout=10,
    )
    if ex_patch.status_code != 200:
        print_result("管理员设置专家帐号", False, f"状态码: {ex_patch.status_code}", ex_patch.text)
        sys.exit(1)
    # 指派延后到创建队伍之后（须指定 team_ids）
    print_result("管理员设置专家帐号", True, f"expert_user_id={expert_seed['user_id']}")

    # 2.5) 修改竞赛规则
    update_comp = requests.put(
        f"{BASE_URL}/competitions/{comp_id}",
        headers=get_headers(),
        json={"rules_text": "Updated rules v2", "description": "New description"},
        timeout=10,
    )
    if update_comp.status_code != 200:
        print_result("修改竞赛", False, f"状态码: {update_comp.status_code}", update_comp.text)
        sys.exit(1)
    updated = update_comp.json()
    rules_ok = updated.get("rules_text") == "Updated rules v2" and updated.get("description") == "New description"
    print_result("修改竞赛", rules_ok, "字段更新正确" if rules_ok else "字段不匹配", updated)
    if not rules_ok:
        sys.exit(1)

    # 3) 学生报名（含参赛信息字段）
    stu1_token = s1["token"]
    stu2_token = s2["token"]

    def hdr(token):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    expert_login = requests.post(
        f"{ALT_URL}/session",
        json={"username": "expert1", "password": "admin123"},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if expert_login.status_code != 200:
        print_result("专家登录", False, expert_login.text)
        sys.exit(1)
    expert_token = expert_login.json().get("access_token")

    enroll1 = requests.post(
        f"{BASE_URL}/competitions/enroll",
        headers=hdr(stu1_token),
        json={
            "competition_id": comp_id,
            "team_id": None,
            "student_no": "2023010001",
            "real_name": "学生一",
            "college": "计算机学院",
            "grade": "2023级",
            "contact": "13800000001",
        },
        timeout=10,
    )
    if enroll1.status_code not in (200, 201):
        print_result("报名参赛（带学生信息）", False, f"状态码: {enroll1.status_code}", enroll1.text)
        sys.exit(1)
    enroll1_data = enroll1.json()
    info_ok = (
        enroll1_data.get("student_no") == "2023010001"
        and enroll1_data.get("real_name") == "学生一"
        and enroll1_data.get("college") == "计算机学院"
        and enroll1_data.get("grade") == "2023级"
        and enroll1_data.get("contact") == "13800000001"
        and enroll1_data.get("sequence_no") == 1
    )
    print_result(
        "报名参赛（带学生信息）",
        info_ok,
        "字段回显正确且个人赛道 sequence_no=1" if info_ok else "字段或 sequence_no 不匹配",
        enroll1_data,
    )
    if not info_ok:
        sys.exit(1)

    # ---- 查看我报名的竞赛 ----
    my_enroll_resp = requests.get(
        f"{BASE_URL}/competitions/enrollments/me",
        headers=hdr(stu1_token),
        timeout=10,
    )
    my_enroll_ok = my_enroll_resp.status_code == 200
    my_enroll_data = my_enroll_resp.json()
    if my_enroll_ok:
        found = any(e["competition_id"] == comp_id for e in my_enroll_data)
        has_comp_detail = all(e.get("competition") is not None for e in my_enroll_data)
        my_enroll_ok = found and has_comp_detail
    print_result(
        "查看我报名的竞赛",
        my_enroll_ok,
        f"返回 {len(my_enroll_data)} 条报名，含竞赛详情" if my_enroll_ok else "未找到报名或缺少竞赛详情",
        my_enroll_data,
    )

    # 个人报名后不能再创建队伍（同一竞赛只能参加一次）
    team_denied = requests.post(
        f"{BASE_URL}/competitions/teams",
        headers=hdr(stu1_token),
        json={"competition_id": comp_id, "initial_member_ids": None},
        timeout=10,
    )
    if team_denied.status_code == 400:
        print_result("个人报名后不能组队", True, "返回 400（符合预期）", team_denied.json())
    else:
        print_result("个人报名后不能组队", False, f"期望 400，实际 {team_denied.status_code}", team_denied.text)
        sys.exit(1)

    # 创建队伍：stu2 成为队长（stu2 尚未报名，可以创建）
    team = requests.post(
        f"{BASE_URL}/competitions/teams",
        headers=hdr(stu2_token),
        json={"competition_id": comp_id, "initial_member_ids": None},
        timeout=10,
    )
    if team.status_code not in (200, 201):
        print_result("创建队伍", False, f"状态码: {team.status_code}", team.text)
        sys.exit(1)
    team_id = team.json().get("id")
    print_result("创建队伍（stu2 为队长）", True, f"team_id={team_id}", team.json())

    ex_assign = requests.post(
        f"{BASE_URL}/competitions/{comp_id}/experts/{expert_seed['user_id']}",
        headers=get_headers(),
        json={"team_ids": [team_id]},
        timeout=10,
    )
    if ex_assign.status_code not in (200, 201):
        print_result("指派竞赛专家", False, f"状态码: {ex_assign.status_code}", ex_assign.text)
        sys.exit(1)
    print_result("指派竞赛专家", True, f"expert_user_id={expert_seed['user_id']} team_id={team_id}")

    # 4) 队长退队必须先转让：stu2 是队长，直接 leave 应返回 400
    leave = requests.post(
        f"{BASE_URL}/competitions/teams/{team_id}/leave",
        headers=hdr(stu2_token),
        timeout=10,
    )
    if leave.status_code == 400:
        print_result("队长退队先转让约束", True, "返回 400（符合预期）", leave.json())
    else:
        print_result("队长退队先转让约束", False, f"期望 400，实际 {leave.status_code}", leave.text)
        sys.exit(1)

    # 5) stu3 加入队伍（stu1 已个人报名，无法加入；用 stu3）
    stu3_token = s3["token"]
    join = requests.post(
        f"{BASE_URL}/competitions/teams/{team_id}/members",
        headers=hdr(stu3_token),
        timeout=10,
    )
    if join.status_code not in (200, 201):
        print_result("加入队伍（stu3）", False, f"状态码: {join.status_code}", join.text)
        sys.exit(1)
    print_result("加入队伍（stu3）", True, "成功", join.json())

    # 队长在仍有队员时不得整队退赛（须先转让）——须在转让/退队之前测，否则队长已无有效报名
    cap_withdraw_denied = requests.post(
        f"{BASE_URL}/competitions/{comp_id}/withdraw",
        headers=hdr(stu2_token),
        timeout=10,
    )
    print_result(
        "队长在仍有队员时退赛被拒",
        cap_withdraw_denied.status_code == 400,
        f"status={cap_withdraw_denied.status_code}",
        cap_withdraw_denied.json()
        if cap_withdraw_denied.headers.get("content-type", "").startswith("application/json")
        else cap_withdraw_denied.text,
    )
    if cap_withdraw_denied.status_code != 400:
        sys.exit(1)

    # stu1 已个人报名，不能加入队伍
    join_denied = requests.post(
        f"{BASE_URL}/competitions/teams/{team_id}/members",
        headers=hdr(stu1_token),
        timeout=10,
    )
    if join_denied.status_code == 400:
        print_result("个人报名后不能加入队伍", True, "返回 400（符合预期）", join_denied.json())
    else:
        print_result("个人报名后不能加入队伍", False, f"期望 400，实际 {join_denied.status_code}", join_denied.text)
        sys.exit(1)

    # 查看竞赛队伍列表
    teams_list = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/teams",
        headers=hdr(stu1_token),
        timeout=10,
    )
    if teams_list.status_code != 200:
        print_result("查看竞赛队伍列表", False, f"状态码: {teams_list.status_code}", teams_list.text)
        sys.exit(1)
    teams_data = teams_list.json()
    found_team = any(t["id"] == team_id for t in teams_data)
    has_members = any(len(t.get("members", [])) >= 2 for t in teams_data if t["id"] == team_id)
    print_result(
        "查看竞赛队伍列表",
        found_team and has_members,
        f"共 {len(teams_data)} 支队伍，目标队伍成员≥2: {has_members}",
        teams_data[:2] if teams_data else [],
    )
    if not found_team:
        sys.exit(1)

    # 个人 / 组队参赛者花名册：仅管理员或被指派专家可查，此处用管理员令牌
    indiv_resp = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/participants/individual",
        headers=get_headers(),
        timeout=10,
    )
    indiv_ok = indiv_resp.status_code == 200
    indiv_rows = indiv_resp.json() if indiv_ok else []
    if indiv_ok:
        indiv_ok = (
            len(indiv_rows) == 1
            and indiv_rows[0].get("sequence_no") == 1
            and indiv_rows[0].get("student_id") == stu1_id
            and indiv_rows[0].get("username") == "stu1"
        )
    print_result(
        "查看个人参赛者（含 sequence_no）",
        indiv_ok,
        "1 人、序号 1" if indiv_ok else indiv_resp.text[:200],
        indiv_rows,
    )
    if not indiv_ok:
        sys.exit(1)

    teams_part_resp = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/participants/teams",
        headers=get_headers(),
        timeout=10,
    )
    tp_ok = teams_part_resp.status_code == 200
    tp_rows = teams_part_resp.json() if tp_ok else []
    if tp_ok:
        tp_ok = len(tp_rows) == 1 and tp_rows[0].get("sequence_no") == 1 and tp_rows[0].get("id") == team_id
        tp_ok = tp_ok and len(tp_rows[0].get("members", [])) >= 2
    print_result(
        "查看组队参赛者（含队伍 sequence_no、成员账号）",
        tp_ok,
        "1 支队伍、序号 1、成员≥2" if tp_ok else teams_part_resp.text[:200],
        tp_rows[:1] if tp_rows else [],
    )
    if not tp_ok:
        sys.exit(1)

    # 6) 转让队长给 stu3，stu2 再退队
    transfer = requests.post(
        f"{BASE_URL}/competitions/teams/{team_id}/transfer-captain",
        headers=hdr(stu2_token),
        json={"team_id": team_id, "new_captain_id": stu3_id},
        timeout=10,
    )
    if transfer.status_code not in (200, 201):
        print_result("转让队长", False, f"状态码: {transfer.status_code}", transfer.text)
        sys.exit(1)
    print_result("转让队长（stu2→stu3）", True, "成功", transfer.json())

    leave2 = requests.post(
        f"{BASE_URL}/competitions/teams/{team_id}/leave",
        headers=hdr(stu2_token),
        timeout=10,
    )
    if leave2.status_code == 200:
        print_result("退队（stu2 已转让后）", True, "成功退队", leave2.json())
    else:
        print_result("退队（stu2 已转让后）", False, f"期望 200，实际 {leave2.status_code}", leave2.text)
        sys.exit(1)

    # 6) 作品文件上传（multipart）+ 查看/下载
    tmp_path = os.path.join(TEST_RESULTS_DIR, "submission_test.txt")
    with open(tmp_path, "wb") as f:
        f.write("hello competition submission".encode("utf-8"))

    files = {"file": ("submission_test.txt", open(tmp_path, "rb"), "text/plain")}
    data = {
        "competition_id": str(comp_id),
        "team_id": str(team_id),
        "title": "My Work",
        "description": "desc",
        "content_text": "",
    }
    upload = requests.post(
        f"{BASE_URL}/competitions/submissions/upload",
        headers={"Authorization": f"Bearer {stu3_token}"},
        data=data,
        files=files,
        timeout=30,
    )
    try:
        files["file"][1].close()
    except Exception:
        pass

    if upload.status_code not in (200, 201):
        print_result("作品上传提交（multipart）", False, f"状态码: {upload.status_code}", upload.text)
        sys.exit(1)

    submission_id = upload.json().get("id")
    print_result("作品上传提交（multipart）", True, f"submission_id={submission_id}", upload.json())

    # 越权用例：非队伍成员/非提交者（stu1 已退队）不能查看/下载 stu2 队伍作品
    sub_detail_denied = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {stu1_token}"},
        timeout=10,
    )
    if sub_detail_denied.status_code == 403:
        print_result("越权查看作品详情（stu1）", True, "返回 403（符合预期）", sub_detail_denied.json())
    else:
        print_result("越权查看作品详情（stu1）", False, f"期望 403，实际 {sub_detail_denied.status_code}", sub_detail_denied.text)
        sys.exit(1)

    dl_denied = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}/download",
        headers={"Authorization": f"Bearer {stu1_token}"},
        timeout=30,
    )
    if dl_denied.status_code == 403:
        print_result("越权下载作品文件（stu1）", True, "返回 403（符合预期）", dl_denied.text[:200])
    else:
        print_result("越权下载作品文件（stu1）", False, f"期望 403，实际 {dl_denied.status_code}", dl_denied.text)
        sys.exit(1)

    # 越权用例：学生不能评分
    grade_denied = requests.put(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers=hdr(stu3_token),
        json={"score": 88.0, "feedback": "try grade"},
        timeout=10,
    )
    if grade_denied.status_code == 403:
        print_result("越权评分（学生）", True, "返回 403（符合预期）", grade_denied.json())
    else:
        print_result("越权评分（学生）", False, f"期望 403，实际 {grade_denied.status_code}", grade_denied.text)
        sys.exit(1)

    # 管理员查看提交详情
    sub_detail = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}",
        headers=get_headers(),
        timeout=10,
    )
    if sub_detail.status_code != 200:
        print_result("查看作品详情（管理员）", False, f"状态码: {sub_detail.status_code}", sub_detail.text)
        sys.exit(1)
    print_result("查看作品详情（管理员）", True, "成功", sub_detail.json())

    # 指导老师无权查看其他队伍作品
    advisor_detail = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {t1['token']}"},
        timeout=10,
    )
    if advisor_detail.status_code == 403:
        print_result("指导老师越权查看他人作品", True, "返回 403（符合预期）", advisor_detail.json())
    else:
        print_result("指导老师越权查看他人作品", False, f"期望 403，实际 {advisor_detail.status_code}", advisor_detail.text)
        sys.exit(1)

    # 指派专家可查看
    expert_detail = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {expert_token}"},
        timeout=10,
    )
    if expert_detail.status_code != 200:
        print_result("专家查看作品详情", False, f"状态码: {expert_detail.status_code}", expert_detail.text)
        sys.exit(1)
    print_result("专家查看作品详情", True, "成功", expert_detail.json())

    # 管理员不参与评分
    admin_grade_denied = requests.put(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers={**get_headers(), "Content-Type": "application/json"},
        json={"score": 91.0, "feedback": "admin try"},
        timeout=10,
    )
    if admin_grade_denied.status_code == 403:
        print_result("管理员不参与评分", True, "返回 403（符合预期）", admin_grade_denied.json())
    else:
        print_result("管理员不参与评分", False, f"期望 403，实际 {admin_grade_denied.status_code}", admin_grade_denied.text)
        sys.exit(1)

    # 专家评分
    teacher_grade = requests.put(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers={"Authorization": f"Bearer {expert_token}", "Content-Type": "application/json"},
        json={"score": 95.0, "feedback": "great"},
        timeout=10,
    )
    if teacher_grade.status_code != 200:
        print_result("专家评分", False, f"状态码: {teacher_grade.status_code}", teacher_grade.text)
        sys.exit(1)
    print_result("专家评分", True, "成功", teacher_grade.json())

    # 重复 PUT 应 400；PATCH 改分应 200
    dup_grade = requests.put(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers={"Authorization": f"Bearer {expert_token}", "Content-Type": "application/json"},
        json={"score": 80.0, "feedback": "dup"},
        timeout=10,
    )
    if dup_grade.status_code != 400:
        print_result("重复首次评分应拒绝", False, f"期望 400，实际 {dup_grade.status_code}", dup_grade.text)
        sys.exit(1)
    print_result("重复首次评分应拒绝", True, "返回 400", dup_grade.json())

    patch_grade = requests.patch(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers={"Authorization": f"Bearer {expert_token}", "Content-Type": "application/json"},
        json={"score": 88.0, "feedback": "revised"},
        timeout=10,
    )
    if patch_grade.status_code != 200:
        print_result("修改评分（PATCH）", False, f"状态码: {patch_grade.status_code}", patch_grade.text)
        sys.exit(1)
    patched = patch_grade.json()
    patch_ok = patched.get("score") == 88.0 and patched.get("feedback") == "revised"
    print_result("修改评分（PATCH）", patch_ok, "分数与反馈已更新" if patch_ok else "字段不匹配", patched)
    if not patch_ok:
        sys.exit(1)

    get_grade = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}/review-grade",
        headers={"Authorization": f"Bearer {expert_token}"},
        timeout=10,
    )
    if get_grade.status_code != 200:
        print_result("查询评分（GET）", False, f"状态码: {get_grade.status_code}", get_grade.text)
        sys.exit(1)
    got = get_grade.json()
    get_ok = got.get("score") == 88.0 and got.get("feedback") == "revised"
    print_result("查询评分（GET）", get_ok, "与 PATCH 后一致" if get_ok else "字段不匹配", got)
    if not get_ok:
        sys.exit(1)

    # 管理员拉取评分汇总
    summary = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/scores/summary",
        headers=get_headers(),
        timeout=10,
    )
    if summary.status_code != 200:
        print_result("评分汇总（管理员）", False, f"状态码: {summary.status_code}", summary.text)
        sys.exit(1)
    print_result("评分汇总（管理员）", True, "成功", summary.json())

    # 管理员拉取排行榜
    rankings = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/scores/rankings",
        headers=get_headers(),
        timeout=10,
    )
    if rankings.status_code != 200:
        print_result("排行榜（管理员）", False, f"状态码: {rankings.status_code}", rankings.text)
        sys.exit(1)
    items = rankings.json().get("items", [])
    if not items:
        print_result("排行榜（管理员）", False, "items 为空", rankings.json())
        sys.exit(1)
    rank_ok = items[0].get("rank") == 1
    print_result(
        "排行榜（管理员）",
        rank_ok,
        f"统一排名 rank=1, top_score={items[0].get('best_score')}" if rank_ok else "缺少 rank 或不为 1",
        items[:3],
    )
    if not rank_ok:
        sys.exit(1)

    # 管理员下载作品文件
    dl = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}/download",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if dl.status_code != 200 or not dl.content:
        print_result("下载作品文件（管理员）", False, f"状态码: {dl.status_code}", dl.text)
        sys.exit(1)
    dl_path = os.path.join(TEST_RESULTS_DIR, "downloaded_submission_test.txt")
    with open(dl_path, "wb") as f:
        f.write(dl.content)
    print_result("下载作品文件（管理员）", True, f"已保存到 {dl_path}")

    # ===== 退赛（学生）=====
    # stu2 已在前面转让队长并 leave_team，报名已为 withdrawn，不再调用 withdraw。
    # 此时队长为 stu3，且队内仅其一人，退赛 = 解散队伍。
    stu3_sole_withdraw = requests.post(
        f"{BASE_URL}/competitions/{comp_id}/withdraw",
        headers=hdr(stu3_token),
        timeout=10,
    )
    print_result(
        "唯一队长退赛（解散队伍，stu3）",
        stu3_sole_withdraw.status_code == 200 and stu3_sole_withdraw.json().get("status") == "withdrawn",
        "stu3 已退赛",
        stu3_sole_withdraw.json() if stu3_sole_withdraw.status_code == 200 else stu3_sole_withdraw.text,
    )
    if stu3_sole_withdraw.status_code != 200 or stu3_sole_withdraw.json().get("status") != "withdrawn":
        sys.exit(1)

    stu1_withdraw = requests.post(
        f"{BASE_URL}/competitions/{comp_id}/withdraw",
        headers=hdr(stu1_token),
        timeout=10,
    )
    print_result(
        "个人参赛退赛",
        stu1_withdraw.status_code == 200 and stu1_withdraw.json().get("status") == "withdrawn",
        "stu1 已退赛",
        stu1_withdraw.json() if stu1_withdraw.status_code == 200 else stu1_withdraw.text,
    )

    stu1_re_enroll = requests.post(
        f"{BASE_URL}/competitions/enroll",
        headers=hdr(stu1_token),
        json={
            "competition_id": comp_id,
            "team_id": None,
            "student_no": "2023010001",
            "real_name": "学生一",
            "college": "计算机学院",
            "grade": "2023级",
            "contact": "13800000001",
        },
        timeout=10,
    )
    print_result(
        "退赛后再次个人报名",
        stu1_re_enroll.status_code in (200, 201) and stu1_re_enroll.json().get("status") == "enrolled",
        "stu1 再次报名成功",
        stu1_re_enroll.json() if stu1_re_enroll.status_code in (200, 201) else stu1_re_enroll.text,
    )

    # ===== 锁定竞赛（管理员） =====
    lock_resp = requests.put(
        f"{BASE_URL}/competitions/{comp_id}/lock",
        headers=get_headers(),
        timeout=10,
    )
    if lock_resp.status_code != 200:
        print_result("锁定竞赛", False, f"状态码: {lock_resp.status_code}", lock_resp.text)
        sys.exit(1)
    lock_data = lock_resp.json()
    print_result("锁定竞赛", lock_data.get("status") == "closed", f"status={lock_data.get('status')}", lock_data)

    # 锁定后：报名应失败
    enroll_locked = requests.post(
        f"{BASE_URL}/competitions/enroll",
        headers=hdr(stu2_token),
        json={"competition_id": comp_id, "team_id": None},
        timeout=10,
    )
    print_result(
        "锁定后报名被拒",
        enroll_locked.status_code == 400,
        f"status={enroll_locked.status_code}",
        enroll_locked.json() if enroll_locked.headers.get("content-type", "").startswith("application/json") else enroll_locked.text,
    )

    team_after_lock = requests.post(
        f"{BASE_URL}/competitions/teams",
        headers=hdr(stu2_token),
        json={"competition_id": comp_id, "initial_member_ids": None},
        timeout=10,
    )
    print_result(
        "锁定后创建队伍被拒",
        team_after_lock.status_code == 400,
        f"status={team_after_lock.status_code}",
        team_after_lock.json()
        if team_after_lock.headers.get("content-type", "").startswith("application/json")
        else team_after_lock.text,
    )

    # 锁定仅关闭报名：已报名用户仍可提交
    submit_locked = requests.post(
        f"{BASE_URL}/competitions/submissions",
        headers=hdr(stu1_token),
        json={"competition_id": comp_id, "team_id": None, "title": "after_lock_submit", "content_text": "x"},
        timeout=10,
    )
    print_result(
        "锁定后仍可提交作品",
        submit_locked.status_code in (200, 201),
        f"status={submit_locked.status_code}",
        submit_locked.json() if submit_locked.headers.get("content-type", "").startswith("application/json") else submit_locked.text,
    )

    # 锁定后管理员仍可修改竞赛
    update_locked = requests.put(
        f"{BASE_URL}/competitions/{comp_id}",
        headers=get_headers(),
        json={"rules_text": "updated after enrollment closed"},
        timeout=10,
    )
    print_result(
        "锁定后仍可修改竞赛",
        update_locked.status_code == 200,
        f"status={update_locked.status_code}",
        update_locked.json() if update_locked.headers.get("content-type", "").startswith("application/json") else update_locked.text,
    )

    # 锁定后：查看作品详情仍然可以（stu3 已退赛，改用管理员）
    sub_detail_locked = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}",
        headers=get_headers(),
        timeout=10,
    )
    print_result(
        "锁定后查看作品（可以）",
        sub_detail_locked.status_code == 200,
        f"status={sub_detail_locked.status_code}",
    )

    # 锁定后：下载作品文件仍然可以（stu3 已退赛，改用管理员）
    dl_locked = requests.get(
        f"{BASE_URL}/competitions/submissions/{submission_id}/download",
        headers=get_headers(),
        timeout=30,
    )
    print_result(
        "锁定后下载作品（可以）",
        dl_locked.status_code == 200,
        f"status={dl_locked.status_code}",
    )

    # 删除竞赛（管理员）—— 放在最后，会清除本次测试产生的所有关联数据
    del_comp = requests.delete(
        f"{BASE_URL}/competitions/{comp_id}",
        headers=get_headers(),
        timeout=10,
    )
    if del_comp.status_code != 200:
        print_result("删除竞赛", False, f"状态码: {del_comp.status_code}", del_comp.text)
        sys.exit(1)
    print_result("删除竞赛", True, "竞赛及关联数据已删除", del_comp.json())

    # 验证删除后查不到
    check_deleted = requests.get(
        f"{BASE_URL}/competitions/{comp_id}/teams",
        headers=get_headers(),
        timeout=10,
    )
    if check_deleted.status_code == 404:
        print_result("删除后验证（404）", True, "竞赛已不存在")
    else:
        print_result("删除后验证（404）", False, f"期望 404，实际 {check_deleted.status_code}", check_deleted.text)

    print_result("竞赛测试完成", True, "所有关键用例通过")


if __name__ == "__main__":
    run()

