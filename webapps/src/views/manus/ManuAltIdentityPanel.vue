<template>
  <div class="alt-identity-panel" :class="{ 'alt-identity-panel--embedded': mode === 'embedded' }">
    <div class="alt-identity-user-layout">
      <div class="alt-identity-card">
        <div v-if="mode !== 'embedded'" class="brand brand-competition">
          <div class="title-main">2026年安徽省AI大模型创新应用竞赛报名系统</div>
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

        <a-form id="formAltLogin" class="user-layout-login" @submit.prevent="handleLoginSubmit">
          <a-form-item>
            <a-input
              v-model="loginForm.username"
              class="auth-field-input"
              size="large"
              type="text"
              autocomplete="username"
              placeholder="请输入用户名"
            >
              <a-icon slot="prefix" type="user" class="auth-field-icon" />
            </a-input>
          </a-form-item>
          <a-form-item>
            <a-input-password
              v-model="loginForm.password"
              class="auth-field-input"
              size="large"
              autocomplete="off"
              placeholder="请输入密码"
            >
              <a-icon slot="prefix" type="lock" class="auth-field-icon" />
            </a-input-password>
          </a-form-item>
          <a-form-item class="auth-links-row">
            <a-button
              type="link"
              html-type="button"
              class="forgot-password-link"
              @click.stop.prevent="onForgotPasswordClick"
            >忘记密码</a-button>
            <a-button
              type="link"
              html-type="button"
              class="register-link"
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
              登录
            </a-button>
          </a-form-item>
        </a-form>

        <div v-if="altLoggedIn && mode !== 'embedded'" class="logout-row">
          <a-button type="link" @click="handleAltLogout">退出独立账号</a-button>
        </div>
      </div>
    </div>

    <a-modal
      v-model="showForgotPasswordModal"
      title="忘记密码"
      :confirmLoading="resetPasswordLoading"
      okText="重置密码"
      cancelText="取消"
      destroy-on-close
      @ok="handleResetPasswordSubmit"
      @cancel="closeForgotPasswordModal"
    >
      <p class="forgot-password-hint">请使用注册时绑定的手机号收取验证码，并设置新密码。</p>
      <a-form layout="vertical" class="forgot-password-form">
        <a-form-item label="手机号" required>
          <a-input
            v-model="forgotForm.phone"
            size="large"
            maxlength="11"
            placeholder="请输入注册手机号"
            autocomplete="tel"
          />
        </a-form-item>
        <a-form-item label="短信验证码" required>
          <div class="forgot-password-sms-row">
            <a-input
              v-model="forgotForm.sms_code"
              size="large"
              maxlength="8"
              placeholder="请输入验证码"
              autocomplete="one-time-code"
            />
            <a-button
              size="large"
              :loading="forgotSmsSending"
              :disabled="forgotSmsCooldown > 0 || forgotSmsSending"
              @click="handleForgotSendSms"
            >
              {{ forgotSmsCooldown > 0 ? `${forgotSmsCooldown}s` : '获取验证码' }}
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="新密码" required>
          <a-input
            v-model="forgotForm.new_password"
            size="large"
            type="password"
            placeholder="至少 6 位"
            autocomplete="new-password"
          />
        </a-form-item>
        <a-form-item label="确认新密码" required>
          <a-input
            v-model="forgotForm.confirm_password"
            size="large"
            type="password"
            placeholder="再次输入新密码"
            autocomplete="new-password"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import {
  altIdentitySession,
  altIdentitySendSmsCode,
  altIdentityResetPassword,
  saveAltSession,
  clearAltIdentityStorage,
  clearAltLoginRemember,
  markAltLoginSkipAutoOnce,
  consumeAltLoginSkipAutoOnce,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage,
  getStoredAltToken,
  getAltRoleNormalized,
  ALT_PROFILE_KEY
} from '@/api/altIdentity'
import {
  getStudentAdvisorLandingRouteLocation,
  getStudentAdvisorLandingCompetitionId,
  markCompetitionShareSessionAuthed,
  sanitizeCompetitionReturnPath
} from '@/utils/competitionAuthFlow'

function validateUsername (raw) {
  const s = (raw || '').trim()
  if (!s) return { ok: false, msg: '请输入账号名' }
  if (s.length > 100) return { ok: false, msg: '用户名最长 100 字符' }
  return { ok: true, value: s }
}

function validateCnMobile (raw) {
  let s = String(raw || '').trim().replace(/\s|-/g, '')
  if (s.startsWith('+86')) s = s.slice(3)
  if (s.startsWith('86') && s.length === 13) s = s.slice(2)
  if (!/^1[3-9]\d{9}$/.test(s)) {
    return { ok: false, msg: '请输入正确的11位手机号' }
  }
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
      loginLoading: false,
      autoLoginTried: false,
      loginForm: {
        username: '',
        password: ''
      },
      altProfile: {},
      showForgotPasswordModal: false,
      resetPasswordLoading: false,
      forgotSmsSending: false,
      forgotSmsCooldown: 0,
      forgotSmsTimer: null,
      forgotForm: {
        phone: '',
        sms_code: '',
        new_password: '',
        confirm_password: ''
      }
    }
  },
  computed: {
    altLoggedIn () {
      return !!(this.altProfile && (this.altProfile.username || this.altProfile.role))
    },
    profileDisplayName () {
      const p = this.altProfile || {}
      const u = p.username
      const n = p.full_name
      if (u && n) return `${u}（${n}）`
      return u || n || '用户'
    }
  },
  mounted () {
    clearAltLoginRemember()
    this.refreshProfile()
    void this.tryResumeSessionOnMount()
  },
  beforeDestroy () {
    this.clearForgotSmsTimer()
  },
  methods: {
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

    /** 仅恢复已有令牌会话；不再用记住的账号密码静默登录 */
    async tryResumeSessionOnMount () {
      if (this.autoLoginTried) return
      this.autoLoginTried = true
      if (consumeAltLoginSkipAutoOnce()) return
      if (!getStoredAltToken()) return
      try {
        const me = await fetchAltIdentityMe()
        applyAltIdentityMeToStorage(me)
        this.refreshProfile()
        this.$emit('session-changed')
      } catch (e) {
        // 恢复会话失败时勿盲目清令牌：可能是瞬时网络问题
        const msg = e && e.message ? String(e.message) : ''
        if (/invalid or expired|未授权|401|缺少第二套令牌|alt-identity token/i.test(msg)) {
          clearAltIdentityStorage()
        }
      }
    },

    handleAltLogout () {
      markAltLoginSkipAutoOnce()
      clearAltIdentityStorage()
      clearAltLoginRemember()
      this.refreshProfile()
      this.$message.success('已退出独立账号')
      this.$emit('session-changed')
    },

    formatAltLoginError (e) {
      const msg = (e && e.message) ? String(e.message) : '登录失败'
      if (/账号核验未通过/.test(msg)) {
        return msg
      }
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

    onForgotPasswordClick () {
      this.resetForgotForm()
      this.showForgotPasswordModal = true
    },

    resetForgotForm () {
      this.clearForgotSmsTimer()
      this.forgotSmsCooldown = 0
      this.forgotSmsSending = false
      this.resetPasswordLoading = false
      this.forgotForm = {
        phone: '',
        sms_code: '',
        new_password: '',
        confirm_password: ''
      }
    },

    closeForgotPasswordModal () {
      this.showForgotPasswordModal = false
      this.resetForgotForm()
    },

    clearForgotSmsTimer () {
      if (this.forgotSmsTimer) {
        clearInterval(this.forgotSmsTimer)
        this.forgotSmsTimer = null
      }
    },

    startForgotSmsCooldown (seconds) {
      const sec = Math.max(1, Number(seconds) || 60)
      this.clearForgotSmsTimer()
      this.forgotSmsCooldown = sec
      this.forgotSmsTimer = setInterval(() => {
        if (this.forgotSmsCooldown <= 1) {
          this.forgotSmsCooldown = 0
          this.clearForgotSmsTimer()
          return
        }
        this.forgotSmsCooldown -= 1
      }, 1000)
    },

    async handleForgotSendSms () {
      if (this.forgotSmsSending || this.forgotSmsCooldown > 0) return
      const phoneCheck = validateCnMobile(this.forgotForm.phone)
      if (!phoneCheck.ok) {
        this.$message.warning(phoneCheck.msg)
        return
      }
      this.forgotForm.phone = phoneCheck.value
      this.forgotSmsSending = true
      try {
        const res = await altIdentitySendSmsCode({
          phone: phoneCheck.value,
          purpose: 'reset_password'
        })
        const cooldown = (res && res.cooldown_seconds != null) ? Number(res.cooldown_seconds) : 60
        this.startForgotSmsCooldown(cooldown)
        if (res && res.debug_code) {
          this.forgotForm.sms_code = String(res.debug_code)
          this.$message.success(`验证码已发送（调试：${res.debug_code}）`)
        } else {
          this.$message.success((res && res.message) || '验证码已发送')
        }
      } catch (e) {
        this.$message.error((e && e.message) ? e.message : '发送失败')
      } finally {
        this.forgotSmsSending = false
      }
    },

    async handleResetPasswordSubmit () {
      const phoneCheck = validateCnMobile(this.forgotForm.phone)
      if (!phoneCheck.ok) {
        this.$message.warning(phoneCheck.msg)
        return Promise.reject(new Error(phoneCheck.msg))
      }
      const code = String(this.forgotForm.sms_code || '').trim()
      if (!code || !/^\d{4,8}$/.test(code)) {
        this.$message.warning('请输入正确的短信验证码')
        return Promise.reject(new Error('invalid sms'))
      }
      const pwd = String(this.forgotForm.new_password || '')
      const confirm = String(this.forgotForm.confirm_password || '')
      if (!pwd || pwd.length < 6) {
        this.$message.warning('新密码至少 6 位')
        return Promise.reject(new Error('short password'))
      }
      if (pwd !== confirm) {
        this.$message.warning('两次输入的新密码不一致')
        return Promise.reject(new Error('mismatch'))
      }

      this.resetPasswordLoading = true
      try {
        const res = await altIdentityResetPassword({
          phone: phoneCheck.value,
          sms_code: code,
          new_password: pwd
        })
        const uname = res && res.username ? String(res.username) : ''
        this.$message.success((res && res.message) || '密码已重置，请使用新密码登录')
        if (uname) this.loginForm.username = uname
        this.loginForm.password = ''
        this.closeForgotPasswordModal()
      } catch (e) {
        this.$message.error((e && e.message) ? e.message : '重置失败')
        return Promise.reject(e)
      } finally {
        this.resetPasswordLoading = false
      }
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

      clearAltLoginRemember()

      this.loginLoading = true
      try {
        const res = await altIdentitySession({
          username: u.value,
          password: this.loginForm.password
        })
        if (res && res.access_token) {
          // 登录成功后持久化令牌，刷新页面可保持登录（不再保存明文密码）
          saveAltSession(res, { username: u.value }, { persist: true })
          try {
            const me = await fetchAltIdentityMe()
            applyAltIdentityMeToStorage(me)
          } catch (syncErr) {
            console.warn('[ManuAltIdentityPanel] sync /me after login failed:', syncErr)
          }
          this.refreshProfile()
          this.$message.success('登录成功')
          this.$emit('session-changed', res)
          this.redirectStudentOrAdvisorAfterLogin()
        } else {
          this.$message.error('登录失败：未返回令牌')
        }
      } catch (e) {
        this.$message.warning(this.formatAltLoginError(e))
      } finally {
        this.loginLoading = false
      }
    },

    /** 学生/指导老师登录后进入默认竞赛详情（已登录态） */
    redirectStudentOrAdvisorAfterLogin () {
      if (this.mode !== 'embedded') return
      const role = getAltRoleNormalized()
      if (role !== 'student' && role !== 'advisor') return

      const raw = this.$route && this.$route.query ? this.$route.query.redirectAfterAlt : ''
      const next = sanitizeCompetitionReturnPath(raw)
      if (next && next.indexOf('/manu/competition-detail') === 0) {
        try {
          const q = next.indexOf('?') >= 0 ? next.slice(next.indexOf('?') + 1) : ''
          const params = new URLSearchParams(q)
          markCompetitionShareSessionAuthed(
            params.get('id') || getStudentAdvisorLandingCompetitionId(),
            params.get('division') || ''
          )
        } catch (e) {
          markCompetitionShareSessionAuthed(getStudentAdvisorLandingCompetitionId())
        }
        this.$router.replace(next).catch(() => {})
        return
      }

      markCompetitionShareSessionAuthed(getStudentAdvisorLandingCompetitionId())
      this.$router.replace(getStudentAdvisorLandingRouteLocation()).catch(() => {})
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

.forgot-password-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  line-height: 1.5;
}

.forgot-password-sms-row {
  display: flex;
  gap: 8px;
  align-items: center;

  .ant-input {
    flex: 1;
  }

  .ant-btn {
    flex-shrink: 0;
  }
}

.user-layout-login {
  label {
    font-size: 14px;
  }

  .auth-links-row {
    margin-bottom: 8px;

    ::v-deep .ant-form-item-children {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
    }
  }

  .register-link,
  .forgot-password-link {
    height: auto;
    line-height: 1.5;
    padding: 0;
    font-size: 14px;
    color: #1a73e8 !important;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
      color: #1557b0 !important;
    }
  }

  .login-submit-item {
    margin-top: 16px;
    margin-bottom: 0;
  }

  button.login-button {
    padding: 0 15px;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.28em;
    text-indent: 0.28em;
    height: 46px;
    width: 100%;
    border: none;
    border-radius: 8px;
    background: linear-gradient(90deg, #4361ee 0%, #1a73e8 55%, #3a86ff 100%);
    box-shadow: 0 6px 16px rgba(26, 115, 232, 0.28);
    transition: filter 0.2s, box-shadow 0.2s, transform 0.15s;

    &:hover,
    &:focus {
      background: linear-gradient(90deg, #3a56d4 0%, #1557b0 55%, #2f75e8 100%);
      filter: brightness(1.02);
      box-shadow: 0 8px 18px rgba(26, 115, 232, 0.36);
    }

    &:active {
      transform: translateY(1px);
    }
  }

  .auth-field-icon {
    color: #1a73e8 !important;
    font-size: 16px;
  }

  ::v-deep .auth-field-input.ant-input-affix-wrapper,
  ::v-deep .auth-field-input.ant-input-password {
    border-radius: 8px;
    border-color: #d9dce0;
    padding-top: 0;
    padding-bottom: 0;
    height: 44px;
    box-shadow: none;
    transition: border-color 0.2s, box-shadow 0.2s;

    .ant-input {
      height: 42px;
      background: transparent;
    }

    .ant-input-prefix {
      margin-right: 10px;
    }

    &:hover {
      border-color: #a8c5f0;
    }

    &.ant-input-affix-wrapper-focused,
    &:focus,
    &.ant-input-password-focused {
      border-color: #1a73e8;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.15);
    }
  }

  ::v-deep .auth-field-input.ant-input {
    height: 44px;
    border-radius: 8px;
    border-color: #d9dce0;

    &:focus {
      border-color: #1a73e8;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.15);
    }
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
