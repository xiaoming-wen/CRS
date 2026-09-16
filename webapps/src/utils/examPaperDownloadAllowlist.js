/**
 * 允许下载试卷的用户名（须同时已报名/已组班且校审通过）。
 * 使用 .js 而不是 .json：webapps/.gitignore 忽略 *.json，无法 git 到服务器。
 * 请与 backend/app/exam_paper_download_allowlist.txt 保持一致。
 */
export const EXAM_PAPER_DOWNLOAD_ALLOWLIST_USERNAMES = [
  'hfu_stu1',
  'hfu_advisor1'
]
