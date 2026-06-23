/** 竞赛用户 ID、竞赛 ID：8 位十进制整数，各自表内唯一 */
export const EIGHT_DIGIT_ID_MIN = 10000000
export const EIGHT_DIGIT_ID_MAX = 99999999

export const EIGHT_DIGIT_ID_HINT = `须为 8 位数字（${EIGHT_DIGIT_ID_MIN}–${EIGHT_DIGIT_ID_MAX}）`

export function isEightDigitId (value) {
  const n = Number(value)
  return Number.isFinite(n) && n >= EIGHT_DIGIT_ID_MIN && n <= EIGHT_DIGIT_ID_MAX && Math.trunc(n) === n
}

export function parseEightDigitIdsFromText (text) {
  const raw = String(text || '').trim()
  if (!raw) return []
  return raw
    .split(/[,，\s]+/)
    .map(s => Number(String(s).trim()))
    .filter(n => isEightDigitId(n))
}

export function validateEightDigitUserId (value, label = '用户ID') {
  if (!isEightDigitId(value)) {
    return `${label}${EIGHT_DIGIT_ID_HINT}`
  }
  return null
}
