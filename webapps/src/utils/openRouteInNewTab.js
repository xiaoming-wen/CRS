/**
 * 在 hash 模式下生成可在新标签页打开的绝对地址。
 * @param {import('vue-router').default} router
 * @param {import('vue-router').RawLocation} location
 */
export function buildAbsoluteRouteUrl (router, location) {
  const resolved = router.resolve(location)
  const href = resolved.href
  if (/^https?:\/\//i.test(href)) return href
  const base = `${window.location.origin}${window.location.pathname}`
  if (href.startsWith('#')) return `${base}${href}`
  const path = resolved.route && resolved.route.fullPath
    ? resolved.route.fullPath
    : (href.startsWith('/') ? href : `/${href}`)
  return `${base}#${path.startsWith('/') ? path : `/${path}`}`
}

/**
 * @returns {Window|null}
 */
export function openRouteInNewTab (router, location, windowFeatures = 'noopener,noreferrer') {
  const url = buildAbsoluteRouteUrl(router, location)
  return window.open(url, '_blank', windowFeatures)
}
