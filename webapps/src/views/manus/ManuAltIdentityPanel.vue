<template>
  <div class="alt-identity-panel" :class="{ 'alt-identity-panel--embedded': mode === 'embedded' }">
    <div class="alt-identity-user-layout">
      <div class="alt-identity-card">
        <div v-if="mode !== 'embedded'" class="brand brand-competition">
          <div class="title-main">竞赛报名系统</div>
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
                <router-link
                  :to="{ name: 'ManuVideoCompetitionRegister' }"
                  class="register-link"
                  style="float: right;"
                >注册</router-link>
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
  ALT_ACCESS_TOKEN_KEY,
  ALT_PROFILE_KEY
} from '@/api/altIdentity'

const REMEMBER_ALT_USER_KEY = 'alt_login_remember_username'

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
      loginForm: {
        username: '',
        password: ''
      },
      altProfile: {}
    }
  },
  computed: {
    altLoggedIn () {
      return !!localStorage.getItem(ALT_ACCESS_TOKEN_KEY)
    },
    profileDisplayName () {
      const u = this.altProfile.username
      const n = this.altProfile.full_name
      if (u && n) return `${u}（${n}）`
      return u || n || '-'
    }
  },
  mounted () {
    const remembered = localStorage.getItem(REMEMBER_ALT_USER_KEY)
    if (remembered) {
      this.loginForm.username = remembered
      this.rememberMe = true
    }
    this.refreshProfile()
  },
  methods: {
    refreshProfile () {
      try {
        const raw = localStorage.getItem(ALT_PROFILE_KEY)
        this.altProfile = raw ? JSON.parse(raw) : {}
      } catch (e) {
        this.altProfile = {}
      }
    },

    handleAltLogout () {
      clearAltIdentityStorage()
      this.refreshProfile()
      this.$message.success('已退出独立账号')
      this.$emit('session-changed')
    },

    handleLoginSubmit () {
      this.handleAltLogin()
    },

    async handleAltLogin () {
      const u = validateUsername(this.loginForm.username)
      if (!u.ok) {
        this.$message.warning(u.msg)
        return
      }
      if (!this.loginForm.password) {
        this.$message.warning('请输入密码')
        return
      }
      if (this.rememberMe) {
        localStorage.setItem(REMEMBER_ALT_USER_KEY, u.value)
      } else {
        localStorage.removeItem(REMEMBER_ALT_USER_KEY)
      }

      this.loginLoading = true
      try {
        const res = await altIdentitySession({
          username: u.value,
          password: this.loginForm.password
        })
        if (res && res.access_token) {
          saveAltSession(res, { username: u.value })
          this.refreshProfile()
          this.$message.success('登录成功')
          this.$emit('session-changed', res)
        } else {
          this.$message.error('登录失败：未返回令牌')
        }
      } catch (e) {
        const msg = (e && e.message) ? e.message : '登录失败'
        this.$message.warning(msg)
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
  background: #f0f2f5 url(~@/assets/background.svg) no-repeat 50%;
  background-size: 100%;
  padding: 24px 16px 40px;
  border-radius: 2px;
  min-height: 480px;
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
    font-size: 22px;
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
    color: #1890ff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
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
