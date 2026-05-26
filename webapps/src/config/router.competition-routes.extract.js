/**
 * 摘自 gpt-free/webapps/src/config/router.config.js（竞赛报名全屏路由）
 * 集成到独立项目时，将下列路由加入 asyncRouterMap 或等价路由表。
 */
export const competitionRoutesExtract = [
  {
    path: '/manu/competition-list',
    name: 'ManuVideoCompetition',
    hidden: true,
    component: () => import('@/views/manus/CompetitionRegistrationFullPage.vue'),
    meta: {
      title: '竞赛列表与报名',
      keepAlive: false,
      hideHeader: true,
      permission: ['datasource']
    }
  },
  {
    path: '/manu/competition-register',
    name: 'ManuVideoCompetitionRegister',
    hidden: true,
    component: () => import('@/views/manus/CompetitionAltRegister.vue'),
    meta: {
      title: '竞赛报名系统注册',
      keepAlive: false,
      hideHeader: true,
      permission: ['datasource']
    }
  },
  {
    path: '/manu/competition-detail',
    name: 'ManuCompetitionDetail',
    hidden: true,
    component: () => import('@/views/manus/CompetitionDetailStandalone.vue'),
    meta: {
      title: '竞赛详情',
      keepAlive: false,
      hideHeader: true,
      permission: ['datasource']
    }
  },
  {
    path: '/manu/my-enrollments',
    name: 'ManuMyEnrollmentsPage',
    hidden: true,
    component: () => import('@/views/manus/MyCompetitionEnrollmentsFullPage.vue'),
    meta: {
      title: '我报名的竞赛',
      keepAlive: false,
      hideHeader: true,
      permission: ['datasource']
    }
  }
]
