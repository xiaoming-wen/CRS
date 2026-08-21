/**
 * 竞赛报名系统独立工程路由（与原 gpt-free 中 /manu/competition-* 路径保持一致）
 */
export const constantRouterMap = [
  {
    path: '/',
    redirect: '/manu/competition-list'
  },
  {
    path: '/manu/competition-list',
    name: 'ManuVideoCompetition',
    component: () => import('@/views/manus/CompetitionRegistrationFullPage.vue'),
    meta: { title: '登录', keepAlive: false, hideHeader: true }
  },
  {
    path: '/manu/competition-register',
    name: 'ManuVideoCompetitionRegister',
    component: () => import('@/views/manus/CompetitionAltRegister.vue'),
    meta: { title: '注册', keepAlive: false, hideHeader: true }
  },
  {
    path: '/manu/competition-detail',
    name: 'ManuCompetitionDetail',
    component: () => import('@/views/manus/CompetitionDetailStandalone.vue'),
    meta: { title: '竞赛详情', keepAlive: false, hideHeader: true }
  },
  {
    path: '/manu/my-enrollments',
    name: 'ManuMyEnrollmentsPage',
    component: () => import('@/views/manus/MyCompetitionEnrollmentsFullPage.vue'),
    meta: { title: '我报名的竞赛', keepAlive: false, hideHeader: true }
  },
  {
    path: '/404',
    component: () => import('@/views/exception/404.vue')
  },
  {
    path: '*',
    redirect: '/manu/competition-list'
  }
]
