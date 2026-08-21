<template>
  <div class="competition-alt-register-root">
    <div
      id="competitionRegisterLayout"
      :class="['competition-auth-shell', device]"
    >
      <AuthTechBackground />
      <div class="auth-shell">
        <div class="auth-card">
          <header class="auth-card__brand">
            <div class="auth-card__logo" aria-hidden="true">
              <a-icon type="deployment-unit" />
            </div>
            <p class="auth-card__eyebrow">2026年</p>
            <h1 class="auth-card__title">安徽省AI大模型创新应用竞赛报名系统</h1>
            <p class="auth-card__subtitle">账号注册</p>
          </header>
          <div class="auth-card__body">
            <ManuAltIdentityRegisterPanel @register-success="registerSuccessNavigate" />
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
  </div>
</template>

<script>
import { mixinDevice } from '@/utils/mixin'
import ManuAltIdentityRegisterPanel from '@/views/manus/ManuAltIdentityRegisterPanel.vue'
import {
  sanitizeCompetitionReturnPath,
  getStudentAdvisorLandingFullPath,
  lockAuthViewport,
  unlockAuthViewport
} from '@/utils/competitionAuthFlow'
import AuthTechBackground from '@/views/manus/AuthTechBackground.vue'

export default {
  name: 'CompetitionAltRegister',
  components: { ManuAltIdentityRegisterPanel, AuthTechBackground },
  mixins: [mixinDevice],
  mounted () {
    lockAuthViewport()
  },
  beforeDestroy () {
    unlockAuthViewport()
  },
  methods: {
    registerSuccessNavigate (payload) {
      const role = payload && payload.role != null ? String(payload.role) : ''
      // 超管/专家/校管等同管理类：注册后只回登录页目录，不带详情 redirect
      if (role !== 'student' && role !== 'advisor') {
        this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
        return
      }
      const raw = this.$route.query.redirectAfterAlt
      const next = sanitizeCompetitionReturnPath(raw) || getStudentAdvisorLandingFullPath()
      this.$router.push({
        name: 'ManuVideoCompetition',
        query: { redirectAfterAlt: next }
      }).catch(() => {})
    }
  }
}
</script>

<style scoped lang="less">
.competition-alt-register-root {
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}

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
  max-height: 600px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 8px 28px rgba(26, 40, 80, 0.1),
    0 2px 8px rgba(26, 40, 80, 0.06);
  padding: 32px 28px 28px;
  box-sizing: border-box;
  overflow: hidden;
}

.auth-card__brand {
  flex-shrink: 0;
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
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  border-top: 1px solid rgba(26, 115, 232, 0.18);
  padding-top: 8px;
  -webkit-overflow-scrolling: touch;
}

.auth-card__footer {
  flex-shrink: 0;
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

    &:hover {
      color: #1a73e8;
    }
  }
}

.auth-footer__sep {
  color: #c5cad1;
}
</style>
