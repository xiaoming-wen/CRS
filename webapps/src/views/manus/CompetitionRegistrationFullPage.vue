<template>
  <div :class="['competition-full-page-root', { 'is-auth': !altGateOk }]">
    <!-- ① 未登录独立账号：居中登录卡片 -->
    <div
      v-if="!altGateOk"
      id="competitionAuthLayout"
      :class="['competition-user-layout-wrapper', 'competition-auth-shell', device]"
    >
      <AuthTechBackground />
      <div class="auth-shell">
        <div class="auth-card">
          <header class="auth-card__brand">
            <div class="auth-card__logo" aria-hidden="true">
              <a-icon type="deployment-unit" />
            </div>
            <p class="auth-card__eyebrow">2026年</p>
            <h1 class="auth-card__title">安徽省AI大模型创新应用竞赛</h1>
            <p class="auth-card__subtitle">报名系统</p>
          </header>

          <div class="auth-card__body">
            <ManuAltIdentityPanel
              mode="embedded"
              @session-changed="onAltGateSessionChanged"
              @switch-to-register="goToCompetitionRegister"
            />
          </div>

          <footer class="auth-card__footer">
            <div class="auth-footer__links">
              <a href="_self">帮助</a>
              <span class="auth-footer__sep" aria-hidden="true">|</span>
              <a href="_self">隐私</a>
              <span class="auth-footer__sep" aria-hidden="true">|</span>
              <a href="_self">条款</a>
            </div>
          </footer>
        </div>
      </div>
    </div>

    <!-- ② 已登录独立账号：进入竞赛目录，默认「竞赛列表与报名」 -->
    <div v-else class="competition-registration-full">
      <div class="competition-registration-full-toolbar">
        <div v-if="catalogLogoUrl" class="toolbar-logo-wrap">
          <img :src="catalogLogoUrl" alt="竞赛 Logo" class="toolbar-logo-img">
        </div>
        <div v-else class="toolbar-logo-spacer" />
        <a-dropdown :trigger="['click']" placement="bottomRight">
          <span class="toolbar-avatar-trigger">
            <a-avatar class="toolbar-avatar">{{ altAvatarInitial }}</a-avatar>
            <span class="toolbar-username" :title="altToolbarUsername">{{ altToolbarUsername }}</span>
          </span>
          <a-menu slot="overlay" @click="onAltAvatarMenu">
            <a-menu-item key="logout">
              退出
            </a-menu-item>
          </a-menu>
        </a-dropdown>
      </div>

      <a-layout class="competition-registration-main">
        <a-layout-sider
          class="competition-catalog-sider"
          width="240"
          :style="{ background: '#fff', borderRight: '1px solid #f0f0f0' }"
        >
          <div class="catalog-header">
            <span class="catalog-title">竞赛目录</span>
          </div>
          <a-menu
            mode="inline"
            :selectedKeys="[currentSection]"
            :style="{ borderRight: 0 }"
            @click="handleCatalogClick"
          >
            <a-menu-item v-for="item in visibleCatalogItems" :key="item.key">
              <a-icon :type="item.icon" />
              <span>{{ item.title }}</span>
            </a-menu-item>
          </a-menu>
        </a-layout-sider>

        <a-layout-content class="competition-registration-body">
          <CompetitionRegistrationSystem
            v-if="currentSection === 'competition-list' && competitionBootstrapDone"
            @catalog-logo-changed="onCatalogLogoChanged"
          />
          <CompetitionExpertAssignment
            v-else-if="currentSection === 'expert-assignment' && isSuperAdmin && competitionBootstrapDone"
          />
          <CompetitionSchoolAdminApplications
            v-else-if="currentSection === 'school-admin-applications' && isSuperAdmin && competitionBootstrapDone"
          />
          <CompetitionSchoolAdminTeamReview
            v-else-if="currentSection === 'admin-team-review' && isSuperAdmin && competitionBootstrapDone"
            mode="super"
          />
          <CompetitionSchoolAdminApplication
            v-else-if="currentSection === 'school-admin-application' && isSchoolAdmin && competitionBootstrapDone"
          />
          <CompetitionSchoolAdminTeamReview
            v-else-if="currentSection === 'school-admin-review' && isSchoolAdmin && competitionBootstrapDone"
            mode="school"
          />
          <MyCompetitionEnrollments
            v-else-if="currentSection === 'my-enrollments' && isAltStudentAccount && competitionBootstrapDone"
          />
        </a-layout-content>
      </a-layout>
    </div>
  </div>
</template>

<script>
import { mixinDevice } from '@/utils/mixin'
import CompetitionRegistrationSystem from '@/views/manus/CompetitionRegistrationSystem.vue'
import CompetitionExpertAssignment from '@/views/manus/CompetitionExpertAssignment.vue'
import CompetitionSchoolAdminApplications from '@/views/manus/CompetitionSchoolAdminApplications.vue'
import CompetitionSchoolAdminApplication from '@/views/manus/CompetitionSchoolAdminApplication.vue'
import CompetitionSchoolAdminTeamReview from '@/views/manus/CompetitionSchoolAdminTeamReview.vue'
import MyCompetitionEnrollments from '@/views/manus/MyCompetitionEnrollments.vue'
import ManuAltIdentityPanel from '@/views/manus/ManuAltIdentityPanel.vue'
import { sanitizeCompetitionReturnPath, getStudentAdvisorLandingFullPath, getStudentAdvisorLandingRouteLocation, getStudentAdvisorLandingCompetitionId, markCompetitionShareSessionAuthed, lockAuthViewport, unlockAuthViewport } from '@/utils/competitionAuthFlow'
import {
  getStoredAltToken,
  clearAltIdentityStorage,
  markAltLoginSkipAutoOnce,
  isAltCompetitionTeacherOrAdmin,
  isAltCompetitionSuperAdmin,
  isAltCompetitionSchoolAdmin,
  isAltCompetitionStudent,
  getAltRoleNormalized,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage,
  getAltProfileFromStorage
} from '@/api/altIdentity'
import { getCompetitionLogo } from '@/api/competition'
import AuthTechBackground from '@/views/manus/AuthTechBackground.vue'

const SECTION_LIST = 'competition-list'
const SECTION_EXPERTS = 'expert-assignment'
const SECTION_SCHOOL_ADMIN_APPS = 'school-admin-applications'
const SECTION_ADMIN_TEAM_REVIEW = 'admin-team-review'
const SECTION_SCHOOL_ADMIN_APPLICATION = 'school-admin-application'
const SECTION_SCHOOL_ADMIN_REVIEW = 'school-admin-review'
const SECTION_MINE = 'my-enrollments'

export default {
  name: 'CompetitionRegistrationFullPage',
  components: {
    CompetitionRegistrationSystem,
    CompetitionExpertAssignment,
    CompetitionSchoolAdminApplications,
    CompetitionSchoolAdminApplication,
    CompetitionSchoolAdminTeamReview,
    MyCompetitionEnrollments,
    ManuAltIdentityPanel,
    AuthTechBackground
  },
  mixins: [mixinDevice],
  data () {
    return {
      altGateTick: 0,
      currentSection: SECTION_LIST,
      /** 独立账号 /me 同步完成后再挂载竞赛接口子组件，避免登录瞬间无令牌或顺序竞态 */
      competitionBootstrapDone: false,
      catalogLogoUrl: null,
      catalogLogoCompetitionId: null,
      catalogLogoLoadSeq: 0
    }
  },
  computed: {
    /** 第二套独立账号已登录后才展示竞赛侧栏与列表 */
    altGateOk () {
      void this.altGateTick
      return !!getStoredAltToken()
    },
    /** 竞赛侧栏与主内容权限以「竞赛独立账号」role 为准，不用主站 JWT roles */
    isAdminTeacher () {
      void this.altGateTick
      return isAltCompetitionTeacherOrAdmin()
    },
    /** 学生账号：侧栏可多一项「我报名的竞赛」并可进入该页 */
    isAltStudentAccount () {
      void this.altGateTick
      return isAltCompetitionStudent()
    },
    isSuperAdmin () {
      void this.altGateTick
      return isAltCompetitionSuperAdmin()
    },
    isSchoolAdmin () {
      void this.altGateTick
      return isAltCompetitionSchoolAdmin()
    },
    visibleCatalogItems () {
      const all = [
        { key: SECTION_LIST, icon: 'unordered-list', title: '竞赛列表与报名', hideForSchoolAdmin: true },
        { key: SECTION_EXPERTS, icon: 'team', title: '专家指派', superAdminOnly: true },
        { key: SECTION_SCHOOL_ADMIN_APPS, icon: 'audit', title: '校管审核', superAdminOnly: true },
        { key: SECTION_ADMIN_TEAM_REVIEW, icon: 'solution', title: '队伍校审', superAdminOnly: true },
        { key: SECTION_SCHOOL_ADMIN_APPLICATION, icon: 'idcard', title: '申请校管', schoolAdminOnly: true },
        { key: SECTION_SCHOOL_ADMIN_REVIEW, icon: 'audit', title: '校审', schoolAdminOnly: true },
        { key: SECTION_MINE, icon: 'solution', title: '我报名的竞赛', studentOnly: true }
      ]
      return all.filter(row => {
        if (row.hideForSchoolAdmin && this.isSchoolAdmin) return false
        if (row.superAdminOnly && !this.isSuperAdmin) return false
        if (row.schoolAdminOnly && !this.isSchoolAdmin) return false
        if (row.studentOnly && !this.isAltStudentAccount) return false
        return true
      })
    },
    /** 随 altGateTick 刷新；兼容 localStorage / sessionStorage 中的独立账号资料 */
    altProfile () {
      void this.altGateTick
      return getAltProfileFromStorage()
    },
    altToolbarUsername () {
      const p = this.altProfile
      const u = (p.username != null && String(p.username).trim() !== '') ? String(p.username).trim() : ''
      const n = (p.full_name != null && String(p.full_name).trim() !== '') ? String(p.full_name).trim() : ''
      return u || n || '用户'
    },
    altAvatarInitial () {
      const s = this.altToolbarUsername
      if (!s || s === '用户') return '用'
      return s.charAt(0)
    }
  },
  watch: {
    altGateOk: {
      async handler (ok) {
        if (ok) {
          this.competitionBootstrapDone = false
          unlockAuthViewport()
          await this.refreshAltIdentityProfile()
          if (!getStoredAltToken()) return
          // 学生/指导老师：优先跳转默认竞赛详情，避免先闪一下列表页
          if (this.consumeRedirectAfterAltIfPresent()) return
          if (this.redirectStudentOrAdvisorToLanding()) return
          this.currentSection = this.resolveDefaultSection()
          this.competitionBootstrapDone = true
          this.$nextTick(() => {
            this.applyExpertUserIdQuerySection()
            this.syncSectionWithCatalog()
          })
        } else {
          this.competitionBootstrapDone = false
          this.clearCatalogLogo()
          lockAuthViewport()
        }
      },
      immediate: true
    },
    isAdminTeacher () {
      this.syncSectionWithCatalog()
    },
    isAltStudentAccount () {
      this.syncSectionWithCatalog()
    },
    isSchoolAdmin () {
      this.syncSectionWithCatalog()
    },
    currentSection (section) {
      if (section !== SECTION_LIST) {
        this.clearCatalogLogo()
      }
    }
  },
  mounted () {
    this.syncSectionWithCatalog()
    window.addEventListener('alt-identity-changed', this.bumpAltGateTick)
  },
  beforeDestroy () {
    this.clearCatalogLogo()
    unlockAuthViewport()
    window.removeEventListener('alt-identity-changed', this.bumpAltGateTick)
  },
  methods: {
    bumpAltGateTick () {
      this.altGateTick++
    },
    clearCatalogLogo () {
      this.catalogLogoLoadSeq += 1
      if (this.catalogLogoUrl) {
        try {
          URL.revokeObjectURL(this.catalogLogoUrl)
        } catch (e) { /* noop */ }
      }
      this.catalogLogoUrl = null
      this.catalogLogoCompetitionId = null
    },
    async onCatalogLogoChanged (competitionId) {
      const id = competitionId != null && String(competitionId).trim() !== ''
        ? Number(competitionId)
        : null
      if (!id || !Number.isFinite(id)) {
        this.clearCatalogLogo()
        return
      }
      if (String(this.catalogLogoCompetitionId) === String(id) && this.catalogLogoUrl) {
        return
      }
      const seq = ++this.catalogLogoLoadSeq
      try {
        const blob = await getCompetitionLogo(id)
        if (seq !== this.catalogLogoLoadSeq) return
        if (!blob || typeof blob.size !== 'number' || blob.size <= 0) {
          this.clearCatalogLogo()
          return
        }
        if (this.catalogLogoUrl) {
          try {
            URL.revokeObjectURL(this.catalogLogoUrl)
          } catch (e) { /* noop */ }
        }
        this.catalogLogoUrl = URL.createObjectURL(blob)
        this.catalogLogoCompetitionId = id
      } catch (e) {
        if (seq !== this.catalogLogoLoadSeq) return
        this.clearCatalogLogo()
      }
    },
    async refreshAltIdentityProfile () {
      if (!getStoredAltToken()) return
      try {
        const me = await fetchAltIdentityMe()
        applyAltIdentityMeToStorage(me)
        this.altGateTick++
      } catch (e) {
        const msg = e && e.message ? String(e.message) : ''
        if (msg) console.warn('同步独立账号资料失败:', msg)
        // 仅在令牌明确失效时清会话，避免短暂网络错误或跳转竞态误清已登录态
        const tokenDead = /invalid or expired|未授权|401|缺少第二套令牌|alt-identity token/i.test(msg)
        if (tokenDead) {
          clearAltIdentityStorage()
          this.altGateTick++
        }
      }
    },
    syncSectionWithCatalog () {
      const keys = this.visibleCatalogItems.map(i => i.key)
      if (!keys.includes(this.currentSection)) {
        this.currentSection = keys[0] || SECTION_LIST
      }
    },
    onAltGateSessionChanged () {
      this.altGateTick++
    },
    goToCompetitionRegister () {
      this.$router.push({
        name: 'ManuVideoCompetitionRegister',
        query: { redirectAfterAlt: getStudentAdvisorLandingFullPath() }
      }).catch(() => {})
    },
    /** 主站重新登录后经 redirectAfterAlt 进入本页：独立账号就绪后跳回原竞赛界面 */
    consumeRedirectAfterAltIfPresent () {
      if (!getStoredAltToken()) return false
      const raw = this.$route.query.redirectAfterAlt
      if (raw == null || String(raw).trim() === '') return false
      const next = sanitizeCompetitionReturnPath(raw)
      if (!next) return false
      if (next.indexOf('/manu/competition-detail') === 0) {
        try {
          const q = next.indexOf('?') >= 0 ? next.slice(next.indexOf('?') + 1) : ''
          const params = new URLSearchParams(q)
          const id = params.get('id') || getStudentAdvisorLandingCompetitionId()
          markCompetitionShareSessionAuthed(id, params.get('division') || '')
        } catch (e) {
          markCompetitionShareSessionAuthed(getStudentAdvisorLandingCompetitionId())
        }
      }
      this.$router.replace(next).catch(() => {})
      return true
    },
    /** 学生 / 指导老师：主页登录后进入默认竞赛详情（分享页布局） */
    redirectStudentOrAdvisorToLanding () {
      if (!getStoredAltToken()) return false
      const role = getAltRoleNormalized()
      // 仅学生、指导老师；teacher/超管/专家/校管仍留在主页目录
      if (role !== 'student' && role !== 'advisor') return false

      const landingId = String(getStudentAdvisorLandingCompetitionId())
      if (
        this.$route.path === '/manu/competition-detail' &&
        String(this.$route.query.id || '') === landingId
      ) {
        return false
      }

      markCompetitionShareSessionAuthed(landingId)
      this.$router.replace(getStudentAdvisorLandingRouteLocation()).catch(() => {})
      return true
    },
    /** 专家注册成功后若带 expertUserId 查询参数，管理员直达「专家指派」步骤 1 */
    applyExpertUserIdQuerySection () {
      if (!this.isSuperAdmin) return
      const raw = this.$route.query.expertUserId
      if (raw == null || String(raw).trim() === '') return
      if (this.visibleCatalogItems.some(i => i.key === SECTION_EXPERTS)) {
        this.currentSection = SECTION_EXPERTS
      }
    },
    /** 登录后默认展示的侧栏页（校管理员不进入竞赛列表） */
    resolveDefaultSection () {
      if (this.isSchoolAdmin && this.visibleCatalogItems.some(i => i.key === SECTION_SCHOOL_ADMIN_APPLICATION)) {
        return SECTION_SCHOOL_ADMIN_APPLICATION
      }
      const keys = this.visibleCatalogItems.map(i => i.key)
      if (keys.includes(SECTION_LIST)) return SECTION_LIST
      return keys[0] || SECTION_LIST
    },
    onAltAvatarMenu ({ key }) {
      if (key !== 'logout') return
      markAltLoginSkipAutoOnce()
      clearAltIdentityStorage()
      this.altGateTick++
      this.$message.success('已退出独立账号，请重新登录')
    },
    handleCatalogClick ({ key }) {
      this.currentSection = key
    }
  }
}
</script>

<style scoped lang="less">
.competition-full-page-root {
  min-height: 100vh;

  &.is-auth {
    height: 100vh;
    max-height: 100vh;
    overflow: hidden;
  }
}

/* 登录壳：固定视口，禁止页面滚动 */
.competition-auth-shell {
  position: fixed;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background: #010618;
}

.auth-shell {
  position: relative;
  z-index: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 32px ~'max(24px, 6vw)' 28px ~'max(24px, 8vw)';
  box-sizing: border-box;
  overflow: hidden;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 8px 28px rgba(26, 40, 80, 0.1),
    0 2px 8px rgba(26, 40, 80, 0.06);
  padding: 32px 28px 28px;
  box-sizing: border-box;
}

.auth-card__brand {
  text-align: center;
  margin-bottom: 8px;
}

.auth-card__logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 26px;
  background: linear-gradient(135deg, #4361ee 0%, #1a73e8 55%, #3a86ff 100%);
  box-shadow: 0 6px 16px rgba(26, 115, 232, 0.35);
}

.auth-card__eyebrow {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: #6c757d;
  line-height: 1.4;
}

.auth-card__title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.35;
  letter-spacing: 0.02em;
  background: linear-gradient(100deg, #1a1a2e 10%, #1a73e8 55%, #4361ee 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.auth-card__subtitle {
  margin: 0 0 18px;
  font-size: 16px;
  font-weight: 600;
  color: #495057;
  letter-spacing: 0.2em;
}

.auth-card__body {
  border-top: 1px solid rgba(26, 115, 232, 0.18);
  padding-top: 8px;
}

.auth-card__footer {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #eef1f5;
  text-align: center;
}

.auth-footer__links {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 13px;
  color: #6c757d;

  a {
    color: #6c757d;
    text-decoration: none;
    transition: color 0.2s;

    &:hover {
      color: #1a73e8;
    }
  }
}

.auth-footer__sep {
  color: #c5cad1;
  user-select: none;
}

.competition-registration-full {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
}

.competition-registration-full-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  gap: 16px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;

  .toolbar-logo-wrap {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    margin-right: auto;
  }

  .toolbar-logo-spacer {
    flex: 1;
    min-width: 0;
  }

  .toolbar-logo-img {
    display: block;
    max-height: 36px;
    max-width: ~'min(280px, 50vw)';
    width: auto;
    height: auto;
    object-fit: contain;
  }

  .toolbar-avatar-trigger {
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    line-height: 1;
    flex-shrink: 0;
    max-width: ~'min(320px, 50vw)';
    margin-left: auto;
  }

  .toolbar-avatar {
    flex-shrink: 0;
    background: #1890ff;
  }

  .toolbar-username {
    margin-left: 10px;
    font-size: 14px;
    color: rgba(0, 0, 0, 0.85);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.competition-registration-main {
  flex: 1;
  min-height: 0;
  min-width: 0;
  background: transparent;
}

.competition-catalog-sider {
  overflow-x: hidden;
  overflow-y: auto;
  min-height: calc(100vh - 52px);

  &::v-deep .ant-layout-sider-children {
    display: flex;
    flex-direction: column;
    min-height: 100%;
  }
}

.catalog-header {
  padding: 16px 16px 8px;

  .catalog-title {
    font-size: 14px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.85);
  }
}

.competition-registration-body {
  padding: 16px;
  overflow-x: hidden;
  overflow-y: auto;
  background: #f5f5f5;
  min-height: calc(100vh - 52px);
  box-sizing: border-box;
  min-width: 0;
}
</style>
