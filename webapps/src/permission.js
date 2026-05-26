import router from './router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { setDocumentTitle, domTitle } from '@/utils/domUtil'

NProgress.configure({ showSpinner: false })

router.beforeEach((to, from, next) => {
  NProgress.start()
  if (to.meta && typeof to.meta.title !== 'undefined') {
    setDocumentTitle(`${to.meta.title} - ${domTitle}`)
  }
  next()
})

router.afterEach(() => {
  NProgress.done()
})
