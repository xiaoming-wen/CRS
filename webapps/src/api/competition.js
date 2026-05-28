import { axios } from '@/utils/request'

/**
 * 竞赛报名系统接口封装（文档 §8：`GET|POST|PUT|DELETE /api/v1/competitions/...`）
 *
 * 鉴权：须由全局 axios 拦截器在请求头附带 **第二套 Alt JWT**（`POST /api/alt-identity/session` 签发），
 * 与主站 `access_token` **不可混用**。竞赛相关整型 ID（student_id / submitter_id / captain_id 等）
 * 语义均为 **alt_auth_users.id**，非主库 users.id。
 * URL 以 `/v1/competitions/...` 书写；开发环境经 devServer 代理到 `/api`。
 */

// 8.1 创建竞赛（仅 super_admin）JSON
export function createCompetition (payload) {
  return axios({
    url: '/v1/competitions/',
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.1 创建竞赛 multipart（含 qr_code_image 等字段，勿手动设 Content-Type）
export function createCompetitionMultipart (formData) {
  return axios({
    url: '/v1/competitions/',
    method: 'post',
    data: formData
  })
}

// 8.2 发布竞赛（仅 super_admin）
export function publishCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/publish`,
    method: 'put',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.3 修改竞赛（仅 super_admin）JSON
export function updateCompetition (competitionId, payload) {
  // payload: 只传需要修改的字段（name/description/rules_text/start_at/end_at/allow_individual/allow_team）
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.3 修改竞赛 multipart（含 qr_code_image；勿手动设 Content-Type）
export function updateCompetitionMultipart (competitionId, formData) {
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'put',
    data: formData
  })
}

// 8.4 删除竞赛（仅 super_admin）
export function deleteCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'delete'
  })
}

// 8.5 锁定竞赛（停止报名；仅 super_admin）
export function lockCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/lock`,
    method: 'put',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 列表：文档未显式列出，但前端需要竞赛列表（GET competitions）
export function getCompetitions () {
  return axios({
    url: '/v1/competitions/',
    method: 'get'
  })
}

/** 竞赛二维码图（GET，一般为 image/png） */
export function getCompetitionQrCode (competitionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/qr-code`,
    method: 'get',
    responseType: 'blob'
  })
}

// 8.6 查看我报名的竞赛（当前 Alt 主体；响应 student_id 为 alt_auth_users.id，权限 VIEW_COMPETITIONS）
export function getMyCompetitionEnrollments () {
  return axios({
    url: '/v1/competitions/enrollments/me',
    method: 'get'
  })
}

// 8.10 查看个人参赛者（含 username/full_name 来自 alt_auth_users；student_id 即 alt_auth_users.id）
export function getCompetitionParticipantsIndividual (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/participants/individual`,
    method: 'get'
  })
}

// 8.11 查看组队参赛者（captain_id / members[].user_id 均为 alt_auth_users.id）
export function getCompetitionParticipantsTeams (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/participants/teams`,
    method: 'get'
  })
}

// 8.11.1 导出队伍信息 Excel（管理员；MANAGE_COMPETITIONS）
export function exportCompetitionTeamsExcel (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams/export`,
    method: 'get',
    responseType: 'blob'
  })
}

function trimStr (v) {
  if (v == null) return ''
  return String(v).trim()
}

// 8.7 报名参赛（学生：个人/队伍；team_id=null 为个人赛道，非空为队伍赛道，双赛道可并存）
export function enrollCompetition (payload) {
  const raw = payload || {}
  const competitionId = Number(raw.competition_id)
  if (!Number.isFinite(competitionId) || competitionId <= 0) {
    return Promise.reject(new Error('竞赛 ID 无效'))
  }
  const body = { competition_id: competitionId }
  const teamRaw = raw.team_id
  const hasTeamIdKey = Object.prototype.hasOwnProperty.call(raw, 'team_id')
  if (teamRaw != null && teamRaw !== '') {
    const teamId = Number(teamRaw)
    if (Number.isFinite(teamId) && teamId > 0) {
      body.team_id = teamId
    }
  } else if (hasTeamIdKey && (teamRaw == null || teamRaw === '')) {
    body.team_id = null
  }
  const optionalKeys = ['student_no', 'real_name', 'college', 'grade', 'contact']
  for (const k of optionalKeys) {
    const s = trimStr(raw[k])
    if (s) body[k] = s
  }
  return axios({
    url: '/v1/competitions/enroll',
    method: 'post',
    data: body,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.8 退赛（学生；停止报名后仍可退赛，权限 ENROLL_COMPETITIONS）
// options.track: 'individual' | 'team' — 个人与组队两条报名均有效时必填
export function withdrawCompetition (competitionId, options = {}) {
  const params = {}
  const track = options && options.track
  if (track === 'individual' || track === 'team') {
    params.track = track
  }
  return axios({
    url: `/v1/competitions/${competitionId}/withdraw`,
    method: 'post',
    params
  })
}

// 8.9 查看竞赛队伍列表（学生选队 / 指导老师查看队况；权限 VIEW_COMPETITIONS）
export function getCompetitionTeams (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams`,
    method: 'get'
  })
}

// 8.12 创建队伍（学生自建队长 / 指导老师组班；权限 MANAGE_TEAMS）
// 学生：{ competition_id, initial_member_ids?: null }
// 指导老师：{ competition_id, name?, captain_student_id?, initial_member_ids: number[] }（至少一名队员）
export function createCompetitionTeam (payload) {
  return axios({
    url: '/v1/competitions/teams',
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.1 修改队名（队长或建队指导老师）
export function patchCompetitionTeam (teamId, payload) {
  return axios({
    url: `/v1/competitions/teams/${teamId}`,
    method: 'patch',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.2 邀请队员（队长或建队指导老师）
export function inviteCompetitionTeamMember (teamId, studentId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/invite`,
    method: 'post',
    data: { student_id: studentId },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.3 移除队员（队长或建队指导老师；不可踢队长）
export function removeCompetitionTeamMember (teamId, userId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/members/${userId}`,
    method: 'delete'
  })
}

// 8.13 加入队伍（学生；权限 MANAGE_TEAMS）
export function addTeamMember (teamId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/members`,
    method: 'post'
  })
}

// 8.14 队长转让（new_captain_id 须为队伍中成员的 alt_auth_users.id）
export function transferTeamCaptain (teamId, payload) {
  // payload: { team_id: int, new_captain_id: int }
  return axios({
    url: `/v1/competitions/teams/${teamId}/transfer-captain`,
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.15 队长退队 / 队员退队（队长须先转让；权限 MANAGE_TEAMS）
export function leaveTeam (teamId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/leave`,
    method: 'post',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.16 提交作品 JSON（须 application/json；支持根级或 { payload: {...} }；权限 SUBMIT_SUBMISSIONS）
export function submitCompetitionSubmission (payload) {
  // payload: { competition_id, team_id: int|null, title, description?, file_id?, content_text? }
  // 后端要求请求体必须包含根级 key "payload"，所有字段放在 payload 对象内
  return axios({
    url: '/v1/competitions/submissions',
    method: 'post',
    data: { payload: payload || {} },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.16.1 提交作品 multipart
export function uploadCompetitionSubmission (formData) {
  // formData: multipart/form-data
  return axios({
    url: '/v1/competitions/submissions/upload',
    method: 'post',
    data: formData,
    timeout: 600000
  })
}

// 8.16.2 查看作品列表
export function getCompetitionSubmissions (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/submissions`,
    method: 'get'
  })
}

// 8.16.3 查看作品详情
export function getCompetitionSubmission (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}`,
    method: 'get'
  })
}

// 8.16.4 下载作品文件
export function downloadCompetitionSubmissionFile (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/download`,
    method: 'get',
    responseType: 'blob',
    timeout: 600000
  })
}

// 8.17 评分/审核（仅已核验且已指派 expert；权限 REVIEW_SUBMISSIONS）首次评分
export function reviewCompetitionSubmissionGrade (submissionId, payload) {
  // payload: { score: number, feedback?: string }
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'put',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.17.1 修改评分（已评分作品；PATCH）
export function patchCompetitionSubmissionReviewGrade (submissionId, payload) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'patch',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.17.2 查询作品评分（ReviewResponse；与 PUT/PATCH 响应体一致，供教师端列表展示分数）
export function getCompetitionSubmissionReviewGrade (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'get'
  })
}

// 8.18 评分汇总（竞赛维度；VIEW_COMPETITIONS + REVIEW_SUBMISSIONS）
export function getCompetitionScoresSummary (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/scores/summary`,
    method: 'get'
  })
}

// 8.19 排行榜（竞赛维度）
export function getCompetitionRankings (competitionId, limit = 50) {
  return axios({
    url: `/v1/competitions/${competitionId}/scores/rankings`,
    method: 'get',
    params: { limit }
  })
}

// 8.20 我的成绩（学生）
// GET /api/v1/competitions/{competition_id}/scores/me
// 响应：{ competition_id, submissions[] }；每条含作品字段 + score | null、feedback | null、reviewed_at | null（与 §8.17 评审计分一致）
export function getMyCompetitionScores (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/scores/me`,
    method: 'get'
  })
}

// 8.0.6 管理员：调整第二套帐号（role / expert_verified；仅 super_admin）
export function patchCompetitionAltUser (targetUserId, payload) {
  return axios({
    url: `/v1/competitions/admin/alt-users/${encodeURIComponent(targetUserId)}`,
    method: 'patch',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.0.7 管理员：全局专家列表（role=expert；含 assigned_competition_ids；super_admin）
export function getAllCompetitionExperts () {
  return axios({
    url: '/v1/competitions/experts',
    method: 'get'
  })
}

// 8.0.7 管理员：列出本赛专家（单赛；已指派 + 待审核 items）
export function getCompetitionExperts (competitionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts`,
    method: 'get'
  })
}

// 8.0.7 管理员：指派专家（目标须 expert 且 expert_verified=true）
export function assignCompetitionExpert (competitionId, expertUserId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'post'
  })
}

// 8.0.7 管理员：取消指派
export function revokeCompetitionExpert (competitionId, expertUserId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'delete'
  })
}
