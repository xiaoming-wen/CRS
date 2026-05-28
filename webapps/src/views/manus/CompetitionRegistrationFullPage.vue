<template>
  <div class="competition-full-page-root">
    <!-- ① 未登录独立账号：与主站登录页同款布局，仅账号密码登录 -->
    <div
      v-if="!altGateOk"
      id="competitionAuthLayout"
      :class="['competition-user-layout-wrapper', device]"
    >
      <div class="container">
        <div class="top">
          <div class="header competition-auth-header">
            <span class="title">竞赛报名系统</span>
          </div>
        </div>

        <div class="main">
          <ManuAltIdentityPanel mode="embedded" @session-changed="onAltGateSessionChanged" />
        </div>

        <div class="footer">
          <div class="links">
            <a href="_self">帮助</a>
            <a href="_self">隐私</a>
            <a href="_self">条款</a>
          </div>
        </div>
      </div>
    </div>

    <!-- ② 已登录独立账号：进入竞赛目录，默认「竞赛列表与报名」 -->
    <div v-else class="competition-registration-full">
      <div class="competition-registration-full-toolbar">
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
          />
          <CompetitionExpertAssignment
            v-else-if="currentSection === 'expert-assignment' && isSuperAdmin && competitionBootstrapDone"
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
import MyCompetitionEnrollments from '@/views/manus/MyCompetitionEnrollments.vue'
import ManuAltIdentityPanel from '@/views/manus/ManuAltIdentityPanel.vue'
import {
  getStoredAltToken,
  clearAltIdentityStorage,
  ALT_PROFILE_KEY,
  isAltCompetitionTeacherOrAdmin,
  isAltCompetitionSuperAdmin,
  isAltCompetitionStudent,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage
} from '@/api/altIdentity'
import { sanitizeCompetitionReturnPath } from '@/utils/competitionAuthFlow'

const SECTION_LIST = 'competition-list'
const SECTION_EXPERTS = 'expert-assignment'
const SECTION_MINE = 'my-enrollments'

export default {
  name: 'CompetitionRegistrationFullPage',
  components: {
    CompetitionRegistrationSystem,
    CompetitionExpertAssignment,
    MyCompetitionEnrollments,
    ManuAltIdentityPanel
  },
  mixins: [mixinDevice],
  data () {
    return {
      altGateTick: 0,
      currentSection: SECTION_LIST,
      /** 独立账号 /me 同步完成后再挂载竞赛接口子组件，避免登录瞬间无令牌或顺序竞态 */
      competitionBootstrapDone: false
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
    visibleCatalogItems () {
      const all = [
        { key: SECTION_LIST, icon: 'unordered-list', title: '竞赛列表与报名' },
        { key: SECTION_EXPERTS, icon: 'team', title: '专家指派', superAdminOnly: true },
        { key: SECTION_MINE, icon: 'solution', title: '我报名的竞赛', studentOnly: true }
      ]
      return all.filter(row => {
        if (row.superAdminOnly && !this.isSuperAdmin) return false
        if (row.studentOnly && !this.isAltStudentAccount) return false
        return true
      })
    },
    /** 随 altGateTick 刷新，与 localStorage 中独立账号资料一致 */
    altProfile () {
      void this.altGateTick
      try {
        const raw = localStorage.getItem(ALT_PROFILE_KEY)
        return raw ? JSON.parse(raw) : {}
      } catch (e) {
        return {}
      }
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
      return s.charAt(0).toUpperCase()
    }
  },
  watch: {
    altGateOk: {
      async handler (ok) {
        if (ok) {
          this.competitionBootstrapDone = false
          document.body.classList.remove('userLayout')
          this.currentSection = SECTION_LIST
          await this.refreshAltIdentityProfile()
          this.competitionBootstrapDone = true
          this.$nextTick(() => {
            this.consumeRedirectAfterAltIfPresent()
            this.applyExpertUserIdQuerySection()
          })
        } else {
          this.competitionBootstrapDone = false
          document.body.classList.add('userLayout')
        }
      },
      immediate: true
    },
    isAdminTeacher () {
      this.syncSectionWithCatalog()
    },
    isAltStudentAccount () {
      this.syncSectionWithCatalog()
    }
  },
  mounted () {
    this.syncSectionWithCatalog()
    window.addEventListener('alt-identity-changed', this.bumpAltGateTick)
  },
  beforeDestroy () {
    document.body.classList.remove('userLayout')
    window.removeEventListener('alt-identity-changed', this.bumpAltGateTick)
  },
  methods: {
    bumpAltGateTick () {
      this.altGateTick++
    },
    async refreshAltIdentityProfile () {
      if (!getStoredAltToken()) return
      try {
        const me = await fetchAltIdentityMe()
        applyAltIdentityMeToStorage(me)
        this.altGateTick++
      } catch (e) {
        const msg = e && e.message ? e.message : ''
        if (msg) console.warn('同步独立账号资料失败:', msg)
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
      if (getStoredAltToken()) {
        this.currentSection = SECTION_LIST
        this.$nextTick(() => this.consumeRedirectAfterAltIfPresent())
      }
    },
    /** 主站重新登录后经 redirectAfterAlt 进入本页：独立账号就绪后跳回原竞赛界面 */
    consumeRedirectAfterAltIfPresent () {
      if (!getStoredAltToken() || !this.competitionBootstrapDone) return
      const raw = this.$route.query.redirectAfterAlt
      if (raw == null || String(raw).trim() === '') return
      const next = sanitizeCompetitionReturnPath(raw)
      if (!next) return
      this.$router.replace(next).catch(() => {})
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
    onAltAvatarMenu ({ key }) {
      if (key !== 'logout') return
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
}

/* 与 UserLayout.vue 对齐的全屏登录/注册壳 */
.competition-user-layout-wrapper {
  height: 100%;

  &.mobile .container .main {
    max-width: 368px;
    width: 98%;
  }

  .container {
    width: 100%;
    min-height: 100%;
    background: #f0f2f5 url(~@/assets/background.svg) no-repeat 50%;
    background-size: 100%;
    /* 与 UserLayout.vue .container 一致 */
    padding: 110px 0 144px;
    position: relative;

    a {
      text-decoration: none;
    }
  }

  .competition-auth-header .title {
    display: inline-block;
  }

  .top {
    text-align: center;

    .header {
      height: 44px;
      line-height: 44px;

      .logo {
        height: 44px;
        vertical-align: top;
        margin-right: 16px;
        border-style: none;
      }

      .title {
        font-size: 33px;
        color: rgba(0, 0, 0, 0.85);
        font-family: Avenir, 'Helvetica Neue', Arial, Helvetica, sans-serif;
        font-weight: 600;
        position: relative;
        top: 2px;
      }
    }
  }

  .main {
    min-width: 260px;
    width: 368px;
    margin: 0 auto;
  }

  .footer {
    position: absolute;
    width: 100%;
    bottom: 0;
    padding: 0 16px;
    margin: 48px 0 24px;
    text-align: center;

    .links {
      margin-bottom: 8px;
      font-size: 14px;

      a {
        color: rgba(0, 0, 0, 0.45);
        transition: all 0.3s;

        &:not(:last-child) {
          margin-right: 40px;
        }
      }
    }
  }
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
  justify-content: flex-end;
  flex-shrink: 0;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;

  .toolbar-avatar-trigger {
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    line-height: 1;
    max-width: ~'min(320px, 50vw)';
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
  overflow: auto;
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
  overflow: auto;
  background: #f5f5f5;
  min-height: calc(100vh - 52px);
  box-sizing: border-box;
  /* flex 子项默认 min-width:auto，会被子内容撑开，宽表无法在卡片内产生横向滚动 */
  min-width: 0;
}
</style>
