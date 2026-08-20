<template>
  <div class="alt-identity-panel" :class="{ 'alt-identity-panel--embedded': mode === 'embedded' }">
    <div class="alt-identity-user-layout">
      <div class="alt-identity-card">
        <div v-if="mode !== 'embedded'" class="brand brand-competition">
          <div class="title-main">合肥大学AI竞赛报名系统</div>
          <div class="sub">
            独立账号登录；与主站 <code>/api/v1/auth</code> 隔离。访问竞赛接口时：已登录主站则优先主站 JWT；仅独立账号时使用第二套 JWT。<code>/api/alt-identity/me</code> 等仅接受第二套令牌。
          </div>
        </div>

        <a-alert
          v-if="altLoggedIn && mode !== 'embedded'"
          type="success"
          show-icon
          class="alt-profile-alert"
          :message="'已登录：' + profileDisplayName"
        >
          <template slot="description">
            <span>角色 {{ altProfile.role || '-' }}；学校 {{ altProfile.school != null ? altProfile.school : '-' }}</span>
          </template>
        </a-alert>

        <!-- 与 Login.vue 一致：仅「账号密码登录」一 Tab -->
        <a-tabs :tabBarStyle="{ textAlign: 'center', borderBottom: 'unset' }">
          <a-tab-pane key="tab1" tab="账号密码登录">
            <a-form id="formAltLogin" class="user-layout-login" @submit.prevent="handleLoginSubmit">
              <a-form-item>
                <a-input
                  v-model="loginForm.username"
                  size="large"
                  type="text"
                  autocomplete="username"
                  placeholder="请输入用户名"
                >
                  <a-icon slot="prefix" type="user" :style="{ color: 'rgba(0,0,0,.25)' }" />
                </a-input>
              </a-form-item>
              <a-form-item>
                <a-input
                  v-model="loginForm.password"
                  size="large"
                  type="password"
                  autocomplete="off"
                  placeholder="请输入密码"
                >
                  <a-icon slot="prefix" type="lock" :style="{ color: 'rgba(0,0,0,.25)' }" />
                </a-input>
              </a-form-item>
              <a-form-item>
                <a-checkbox v-model="rememberMe">自动登录</a-checkbox>
                <a-button
                  type="link"
                  html-type="button"
                  class="register-link"
                  style="float: right; height: auto; line-height: 1.5; padding: 0;"
                  @click.stop.prevent="onRegisterClick"
                >注册</a-button>
              </a-form-item>
              <a-form-item class="login-submit-item">
                <a-button
                  size="large"
                  type="primary"
                  htmlType="submit"
                  class="login-button"
                  :loading="loginLoading"
                  :disabled="loginLoading"
                >
                  确定
                </a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
        </a-tabs>

        <div v-if="altLoggedIn && mode !== 'embedded'" class="logout-row">
          <a-button type="link" @click="handleAltLogout">退出独立账号</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  altIdentitySession,
  saveAltSession,
  clearAltIdentityStorage,
  clearAltLoginRemember,
  saveAltLoginRemember,
  isAltLoginAutoEnabled,
  getAltLoginRememberUsername,
  getAltLoginRememberPassword,
  markAltLoginSkipAutoOnce,
  consumeAltLoginSkipAutoOnce,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage,
  getStoredAltToken,
  ALT_PROFILE_KEY
} from '@/api/altIdentity'

function validateUsername (raw) {
  const s = (raw || '').trim()
  if (!s) return { ok: false, msg: '请输入账号名' }
  if (s.length > 100) return { ok: false, msg: '用户名最长 100 字符' }
  return { ok: true, value: s }
}

export default {
  name: 'ManuAltIdentityPanel',
  props: {
    mode: {
      type: String,
      default: 'full'
    }
  },
  data () {
    return {
      rememberMe: false,
      loginLoading: false,
      autoLoginTried: false,
      loginForm: {
        username: '',
        password: ''
      },
      altProfile: {}
    }
  },
  computed: {
    altLoggedIn () {
      return !!getStoredAltToken()
    },
    profileDisplayName () {
      const u = this.altProfile.username
      const n = this.altProfile.full_name
      if (u && n) return `${u}（${n}）`
      return u || n || '-'
    }
  },
  mounted () {
    this.restoreRememberedAccount()
    this.refreshProfile()
    void this.tryAutoLoginOnMount()
  },
  methods: {
    restoreRememberedAccount () {
      const remembered = getAltLoginRememberUsername()
      const auto = isAltLoginAutoEnabled()
      if (remembered) {
        this.loginForm.username = remembered
      }
      if (auto) {
        this.rememberMe = true
        const secret = getAltLoginRememberPassword()
        if (secret && !this.loginForm.password) {
          this.loginForm.password = secret
        }
      }
    },

    refreshProfile () {
      try {
        const raw =
          localStorage.getItem(ALT_PROFILE_KEY) ||
          sessionStorage.getItem(ALT_PROFILE_KEY)
        this.altProfile = raw ? JSON.parse(raw) : {}
      } catch (e) {
        this.altProfile = {}
      }
    },

    async tryAutoLoginOnMount () {
      if (this.autoLoginTried) return
      this.autoLoginTried = true
      if (consumeAltLoginSkipAutoOnce()) return
      if (!isAltLoginAutoEnabled()) return

      // 已有持久化令牌：校验后直接进入
      if (getStoredAltToken()) {
        try {
          const me = await fetchAltIdentityMe()
          applyAltIdentityMeToStorage(me)
          this.refreshProfile()
          this.$emit('session-changed')
          return
        } catch (e) {
          clearAltIdentityStorage()
        }
      }

      // 无令牌：用当时勾选自动登录保存的账号密码静默登录
      const username = getAltLoginRememberUsername()
      const password = getAltLoginRememberPassword()
      if (!username || !password) return
      this.loginForm.username = username
      this.loginForm.password = password
      this.rememberMe = true
      await this.handleAltLogin({ silent: true })
    },

    handleAltLogout () {
      markAltLoginSkipAutoOnce()
      clearAltIdentityStorage()
      // 保留「自动登录」凭据；下次刷新仍可自动登回（本次已跳过）
      this.refreshProfile()
      this.$message.success('已退出独立账号')
      this.$emit('session-changed')
    },

    formatAltLoginError (e) {
      const msg = (e && e.message) ? String(e.message) : '登录失败'
      if (/pending verification|待.*核验|expert_verified/i.test(msg)) {
        return '专家账号待管理员核验，核验并指派竞赛后方可登录。注册后请将用户 ID 告知管理员。'
      }
      if (/inactive|停用|禁用/i.test(msg)) {
        return '账号已停用，请联系管理员。'
      }
      return msg
    },

    handleLoginSubmit () {
      this.handleAltLogin()
    },

    onRegisterClick () {
      if (this.mode === 'embedded') {
        this.$emit('switch-to-register')
        return
      }
      this.$router.push({ name: 'ManuVideoCompetitionRegister' }).catch(() => {})
    },

    async handleAltLogin (options = {}) {
      const silent = !!(options && options.silent)
      const u = validateUsername(this.loginForm.username)
      if (!u.ok) {
        if (!silent) this.$message.warning(u.msg)
        return
      }
      if (!this.loginForm.password) {
        if (!silent) this.$message.warning('请输入密码')
        return
      }

      if (this.rememberMe) {
        saveAltLoginRemember(u.value, this.loginForm.password)
      } else {
        clearAltLoginRemember()
      }

      this.loginLoading = true
      try {
        const res = await altIdentitySession({
          username: u.value,
          password: this.loginForm.password
        })
        if (res && res.access_token) {
          saveAltSession(res, { username: u.value }, { persist: !!this.rememberMe })
          try {
            const me = await fetchAltIdentityMe()
            applyAltIdentityMeToStorage(me)
          } catch (syncErr) {
            console.warn('[ManuAltIdentityPanel] sync /me after login failed:', syncErr)
          }
          this.refreshProfile()
          if (!silent) this.$message.success('登录成功')
          this.$emit('session-changed', res)
        } else if (!silent) {
          this.$message.error('登录失败：未返回令牌')
        }
      } catch (e) {
        if (silent) {
          // 自动登录失败：清掉无效凭据，避免反复失败
          clearAltLoginRemember()
          this.rememberMe = false
          this.loginForm.password = ''
        } else {
          this.$message.warning(this.formatAltLoginError(e))
        }
      } finally {
        this.loginLoading = false
      }
    }
  }
}
</script>

<style lang="less" scoped>
.alt-identity-panel {
  width: 100%;
}

.alt-profile-alert {
  margin-bottom: 16px;
}

.alt-identity-user-layout {
  background: #f0f2f5 url(~@/assets/background.svg) no-repeat center center;
  background-size: cover;
  padding: 24px 16px 40px;
  border-radius: 2px;
  min-height: 100vh;
  box-sizing: border-box;
}

.alt-identity-card {
  max-width: 400px;
  margin: 0 auto;
  background: #fff;
  padding: 24px 28px 28px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.brand-competition {
  text-align: center;
  margin-bottom: 20px;

  .title-main {
    font-size: 20px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.85);
    font-family: Avenir, 'Helvetica Neue', Arial, Helvetica, sans-serif;
  }

  .sub {
    margin-top: 8px;
    font-size: 12px;
    color: rgba(0, 0, 0, 0.45);
    line-height: 1.5;
    max-width: 360px;
    margin-left: auto;
    margin-right: auto;
  }
}

.logout-row {
  text-align: center;
  margin-top: 8px;
}

.user-layout-login {
  label {
    font-size: 14px;
  }

  .register-link {
    font-size: 14px;
    color: #1890ff !important;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
      color: #40a9ff !important;
    }
  }

  .login-submit-item {
    margin-top: 24px;
  }

  button.login-button {
    padding: 0 15px;
    font-size: 16px;
    height: 40px;
    width: 100%;
  }
}

.alt-identity-panel--embedded {
  .alt-identity-user-layout {
    background: none;
    padding: 0;
    min-height: 0;
  }

  .alt-identity-card {
    max-width: none;
    margin: 0;
    background: transparent;
    box-shadow: none;
    padding: 0;
  }
}
</style>
