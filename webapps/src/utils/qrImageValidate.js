/**
 * 二维码图片校验（依赖 public/vendor/jsQR.umd.js，在 index.html 中加载为 window.jsQR）
 */
function getJsQRDecode () {
  if (typeof window === 'undefined') return null
  const lib = window.jsQR
  if (typeof lib === 'function') return lib
  if (lib && typeof lib.default === 'function') return lib.default
  return null
}

/**
 * 画布取样后尝试解码 QR，判断图片中是否包含可读二维码。
 */
export function validateImageContainsQrCode (file) {
  return new Promise((resolve, reject) => {
    const jsQR = getJsQRDecode()
    if (!jsQR) {
      reject(new Error('二维码校验脚本未加载，请刷新页面或检查网络'))
      return
    }
    if (!(file instanceof Blob)) {
      reject(new Error('无效文件'))
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        try {
          let w = img.naturalWidth || img.width
          let h = img.naturalHeight || img.height
          if (!w || !h) {
            resolve(false)
            return
          }
          const maxSide = 1200
          if (w > maxSide || h > maxSide) {
            const r = Math.min(maxSide / w, maxSide / h)
            w = Math.max(1, Math.floor(w * r))
            h = Math.max(1, Math.floor(h * r))
          }
          const canvas = document.createElement('canvas')
          canvas.width = w
          canvas.height = h
          const ctx = canvas.getContext('2d')
          ctx.drawImage(img, 0, 0, w, h)
          const imageData = ctx.getImageData(0, 0, w, h)
          const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth'
          })
          resolve(!!(code && typeof code.data === 'string' && code.data.length > 0))
        } catch (e) {
          reject(e)
        }
      }
      img.onerror = () => reject(new Error('图片加载失败'))
      img.src = reader.result
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}
