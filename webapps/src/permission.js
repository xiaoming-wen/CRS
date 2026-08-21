import router from './router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { setDocumentTitle, domTitle } from '@/utils/domUtil'

NProgress.configure({ showSpinner: false })

router.beforeEach((to, from, next) => {
  NProgress.start()
  setDocumentTitle(domTitle)
  next()
})

router.afterEach(() => {
  NProgress.done()
})
