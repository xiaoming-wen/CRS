<template>
  <div class="alt-identity-register-panel" :class="{ 'alt-identity-register-panel--embedded': mode === 'embedded' }">
    <a-form
      id="formAltRegister"
      class="user-layout-register"
      :form="form"
      @submit="handleSubmit"
    >
      <a-form-item>
        <a-input
          size="large"
          type="text"
          placeholder="请输入用户名"
          v-decorator="[
            'username',
            {
              rules: [
                { required: true, whitespace: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
                { max: 100, message: '用户名最长100个字符' },
                { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5-]+$/, message: '用户名仅支持中文、字母、数字、下划线和连字符' }
              ],
              validateTrigger: 'change'
            }
          ]"
          @focus="hintFocus.username = true"
          @blur="hintFocus.username = false"
        >
          <a-icon slot="prefix" type="user" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
        <template slot="extra">
          <span v-show="hintFocus.username" class="register-field-hint">至少 3 个字符；支持中文、字母、数字、下划线和连字符。</span>
        </template>
      </a-form-item>

      <a-form-item>
        <a-input
          size="large"
          type="tel"
          maxlength="11"
          placeholder="请输入手机号"
          v-decorator="[
            'phone',
            {
              rules: [
                { required: true, message: '请输入手机号' },
                { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的11位手机号' }
              ],
              validateTrigger: 'change'
            }
          ]"
        >
          <a-icon slot="prefix" type="mobile" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item>
        <a-row :gutter="8">
          <a-col :span="15">
            <a-input
              size="large"
              maxlength="8"
              placeholder="请输入短信验证码"
              v-decorator="[
                'sms_code',
                {
                  rules: [
                    { required: true, message: '请输入短信验证码' },
                    { pattern: /^\d{4,8}$/, message: '验证码为4-8位数字' }
                  ],
                  validateTrigger: 'change'
                }
              ]"
            >
              <a-icon slot="prefix" type="safety-certificate" :style="{ color: 'rgba(0,0,0,.25)' }" />
            </a-input>
          </a-col>
          <a-col :span="9">
            <a-button
              size="large"
              block
              :loading="state.smsSending"
              :disabled="state.smsCountdown > 0"
              @click="handleSendSmsCode"
            >
              {{ smsCodeButtonText }}
            </a-button>
          </a-col>
        </a-row>
      </a-form-item>

      <a-form-item>
        <a-input
          size="large"
          type="text"
          placeholder="请输入姓名"
          v-decorator="[
            'full_name',
            {
              rules: [
                { required: true, whitespace: true, message: '请输入姓名' },
                { min: 2, message: '姓名至少2个字符' },
                { max: 50, message: '姓名最长50个字符' },
                { pattern: /^[\u4e00-\u9fa5a-zA-Z·\s]{2,50}$/, message: '姓名仅支持中文、英文或间隔号' }
              ],
              validateTrigger: 'change'
            }
          ]"
        >
          <a-icon slot="prefix" type="idcard" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item>
        <a-select
          size="large"
          allowClear
          placeholder="请选择省份"
          v-decorator="[
            'register_province',
            {
              rules: [{ required: true, message: '请选择省份' }],
              validateTrigger: 'change'
            }
          ]"
          @change="handleProvinceChange"
        >
          <a-select-option v-for="p in provinceOptions" :key="p" :value="p">{{ p }}</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item>
        <a-select
          size="large"
          showSearch
          allowClear
          placeholder="请先选择省份，再输入学校关键字搜索"
          :filterOption="false"
          :disabled="!selectedProvince"
          :notFoundContent="schoolNotFoundContent"
          v-decorator="[
            'school',
            {
              rules: [
                { required: true, message: '请选择学校' },
                { validator: validateSchoolSelection }
              ],
              validateTrigger: 'change'
            }
          ]"
          @search="handleSchoolSearch"
          @change="handleSchoolSelect"
          @focus="hintFocus.school = true"
          @blur="hintFocus.school = false"
        >
          <a-select-option v-for="s in schoolSuggestions" :key="s" :value="s">{{ s }}</a-select-option>
        </a-select>
        <template slot="extra">
          <span v-show="hintFocus.school" class="register-field-hint">先选省份，再输入校名前几个字搜索。</span>
        </template>
      </a-form-item>

      <a-form-item>
        <a-select
          size="large"
          placeholder="请选择角色"
          v-decorator="[
            'role',
            { rules: [{ required: true, message: '请选择角色' }], validateTrigger: 'change' }
          ]"
          @change="handleRoleChange"
        >
          <a-select-option value="student">学生</a-select-option>
          <a-select-option value="advisor">指导老师</a-select-option>
          <template v-if="mode !== 'embedded'">
            <a-select-option value="expert">专家</a-select-option>
            <a-select-option value="school_admin">校管理员</a-select-option>
          </template>
        </a-select>
      </a-form-item>

      <a-form-item v-if="form.getFieldValue('role') === 'student'">
        <a-input
          size="large"
          type="text"
          placeholder="请输入学号"
          v-decorator="[
            'student_id',
            {
              rules: [
                { required: true, whitespace: true, message: '请输入学号' },
                { max: 50, message: '学号最长50个字符' },
                { pattern: /^[A-Za-z0-9_-]{1,50}$/, message: '学号仅支持字母、数字、下划线和连字符' }
              ],
              validateTrigger: 'change'
            }
          ]"
        >
          <a-icon slot="prefix" type="number" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item v-if="isAdvisorRegisterRole(form.getFieldValue('role'))">
        <a-input
          size="large"
          type="text"
          placeholder="请输入指导老师编号"
          v-decorator="[
            'teacher_id',
            {
              rules: [
                { required: true, whitespace: true, message: '请输入指导老师编号' },
                { max: 50, message: '指导老师编号最长50个字符' }
              ],
              validateTrigger: 'change'
            }
          ]"
        >
          <a-icon slot="prefix" type="number" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item>
        <a-input-password
          size="large"
          autocomplete="false"
          placeholder="请输入密码"
          v-decorator="[
            'password',
            { rules: [
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
              { max: 128, message: '密码最长128个字符' }
            ], validateTrigger: 'blur' }
          ]"
          @focus="hintFocus.password = true"
          @blur="hintFocus.password = false"
        >
          <a-icon slot="prefix" type="lock" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input-password>
      </a-form-item>

      <a-form-item>
        <a-input-password
          size="large"
          autocomplete="false"
          placeholder="请再次输入密码"
          v-decorator="[
            'confirmPassword',
            { rules: [{ required: true, message: '请确认密码' }, { validator: compareToFirstPassword }], validateTrigger: 'blur' }
          ]"
        >
          <a-icon slot="prefix" type="lock" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input-password>
      </a-form-item>

      <a-form-item :style="{ marginTop: mode === 'embedded' ? '8px' : '24px' }">
        <a-button
          size="large"
          type="primary"
          htmlType="submit"
          class="register-button"
          :loading="state.registerBtn"
          :disabled="state.registerBtn"
        >
          注册
        </a-button>
      </a-form-item>

      <a-form-item v-if="mode === 'embedded'" class="embedded-login-link-item">
        <a class="login-link" href="#" @click.prevent="$emit('switch-to-login')">已有账号？去登录</a>
      </a-form-item>
      <a-form-item v-else>
        <router-link
          :to="loginLinkLocation"
          class="login-link"
          style="text-align: center; display: block;"
        >
          已有账号？去登录
        </router-link>
      </a-form-item>
    </a-form>
  </div>
</template>

<script>
import { altIdentityRegister, altIdentitySendSmsCode } from '@/api/altIdentity'
import { showRegisterConflictModal, extractRegisterError } from '@/utils/registerConflict'
import {
  PROVINCE_OPTIONS,
  filterSchoolsByKeyword,
  isSchoolInProvince
} from '@/data/chinaSchoolsByProvince'
import { sanitizeCompetitionReturnPath } from '@/utils/competitionAuthFlow'

export default {
  name: 'ManuAltIdentityRegisterPanel',
  props: {
    mode: {
      type: String,
      default: 'full'
    }
  },
  data () {
    return {
      provinceOptions: PROVINCE_OPTIONS,
      selectedProvince: undefined,
      schoolSuggestions: [],
      schoolSearchKeyword: '',
      hintFocus: {
        username: false,
        school: false,
        password: false,
        confirmPassword: false
      },
      form: this.$form.createForm(this),
      state: {
        registerBtn: false,
        smsSending: false,
        smsCooldown: 0
      },
      smsTimer: null
    }
  },
  computed: {
    loginLinkLocation () {
      // 仅透传已有回跳；不默认塞入学生落地详情，避免超管/专家/校管登录后被带去详情页
      const raw = this.$route && this.$route.query ? this.$route.query.redirectAfterAlt : ''
      const next = sanitizeCompetitionReturnPath(raw)
      if (next) {
        return {
          name: 'ManuVideoCompetition',
          query: { redirectAfterAlt: next }
        }
      }
      return { name: 'ManuVideoCompetition' }
    },
    schoolNotFoundContent () {
      if (!this.selectedProvince) return '请先选择省份'
      if (!this.schoolSearchKeyword) return '请输入关键字搜索学校'
      return '未找到匹配学校'
    },
    smsCodeButtonText () {
      if (this.state.smsCooldown > 0) return `${this.state.smsCooldown}s`
      return '获取验证码'
    }
  },
  beforeDestroy () {
    if (this.smsTimer) {
      clearInterval(this.smsTimer)
      this.smsTimer = null
    }
  },
  methods: {
    isAdvisorRegisterRole (role) {
      return role === 'advisor' || role === 'teacher'
    },
    startSmsCooldown (seconds) {
      const sec = Math.max(1, Number(seconds) || 60)
      if (this.smsTimer) {
        clearInterval(this.smsTimer)
        this.smsTimer = null
      }
      this.state.smsCooldown = sec
      this.smsTimer = setInterval(() => {
        if (this.state.smsCooldown <= 1) {
          this.state.smsCooldown = 0
          clearInterval(this.smsTimer)
          this.smsTimer = null
          return
        }
        this.state.smsCooldown -= 1
      }, 1000)
    },
    handleSendSmsCode () {
      if (this.state.smsSending || this.state.smsCooldown > 0) return
      this.form.validateFields(['phone'], { force: true }, (err, values) => {
        if (err) {
          this.showFormValidationModal(err, '无法获取验证码')
          return
        }
        const phone = String((values && values.phone) || '').trim()
        this.state.smsSending = true
        altIdentitySendSmsCode({ phone, purpose: 'register' })
          .then((res) => {
            const cooldown = (res && res.cooldown_seconds != null) ? Number(res.cooldown_seconds) : 60
            this.startSmsCooldown(cooldown)
            if (res && res.debug_code) {
              this.form.setFieldsValue({ sms_code: String(res.debug_code) })
              this.$message.success(`验证码已发送（调试：${res.debug_code}）`)
            } else {
              this.$message.success((res && res.message) || '验证码已发送')
            }
          })
          .catch((e) => {
            const msg = extractRegisterError(e) || (e && e.message) || '发送失败'
            this.$warning({
              title: '获取验证码失败',
              content: msg,
              okText: '知道了'
            })
          })
          .finally(() => {
            this.state.smsSending = false
          })
      })
    },
    handleRoleChange () {
      this.$nextTick(() => {
        const currentRole = this.form.getFieldValue('role')
        if (currentRole !== 'student') {
          this.form.setFieldsValue({ student_id: undefined })
        }
        if (!this.isAdvisorRegisterRole(currentRole)) {
          this.form.setFieldsValue({ teacher_id: undefined })
        }
      })
    },
    handleProvinceChange (value) {
      this.selectedProvince = value || undefined
      this.form.setFieldsValue({ school: undefined })
      this.schoolSearchKeyword = ''
      this.schoolSuggestions = []
    },
    refreshSchoolSuggestions (keyword) {
      if (!this.selectedProvince) {
        this.schoolSuggestions = []
        return
      }
      this.schoolSearchKeyword = keyword != null ? String(keyword).trim() : ''
      this.schoolSuggestions = filterSchoolsByKeyword(this.selectedProvince, this.schoolSearchKeyword)
    },
    handleSchoolSearch (value) {
      if (!this.selectedProvince) return
      this.refreshSchoolSuggestions(value)
    },
    handleSchoolSelect (value) {
      const name = value != null ? String(value).trim() : ''
      this.schoolSearchKeyword = name
      if (name) {
        this.schoolSuggestions = filterSchoolsByKeyword(this.selectedProvince, name)
      } else {
        this.schoolSuggestions = []
      }
    },
    validateSchoolSelection (rule, value, callback) {
      if (!this.selectedProvince) {
        callback(new Error('请先选择省份'))
        return
      }
      const name = (value || '').trim()
      if (!name) {
        callback(new Error('请选择学校'))
        return
      }
      if (name.length > 200) {
        callback(new Error('学校名称最长200个字符'))
        return
      }
      if (!isSchoolInProvince(this.selectedProvince, name)) {
        callback(new Error('请从列表中选择学校，或检查省份与关键字是否正确'))
        return
      }
      callback()
    },
    compareToFirstPassword (rule, value, callback) {
      const form = this.form
      if (value && value !== form.getFieldValue('password')) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    },
    /** 从 ant-design-vue 校验结果中收集可读提示 */
    collectFormErrorMessages (err) {
      if (!err || typeof err !== 'object') return []
      const fieldOrder = [
        'username',
        'phone',
        'sms_code',
        'full_name',
        'register_province',
        'school',
        'role',
        'student_id',
        'teacher_id',
        'password',
        'confirmPassword'
      ]
      const messages = []
      const pushMsg = (fieldErr) => {
        if (!fieldErr || !Array.isArray(fieldErr.errors) || !fieldErr.errors.length) return
        const msg = fieldErr.errors[0] && fieldErr.errors[0].message
        if (msg && !messages.includes(msg)) messages.push(String(msg))
      }
      fieldOrder.forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(err, key)) pushMsg(err[key])
      })
      Object.keys(err).forEach((key) => {
        if (fieldOrder.includes(key)) return
        pushMsg(err[key])
      })
      return messages
    },
    showFormValidationModal (err, title) {
      const messages = this.collectFormErrorMessages(err)
      const list = messages.length ? messages : ['请检查并完善必填项']
      this.$warning({
        title: title || '注册信息不完整或不规范',
        okText: '知道了',
        content: (h) => h('div', [
          h('p', { style: { margin: '0 0 8px' } }, '请按以下提示修改后再试：'),
          h(
            'ol',
            { style: { paddingLeft: '20px', margin: '0' } },
            list.map((msg) => h('li', { style: { marginBottom: '4px' } }, msg))
          )
        ])
      })
      this.$nextTick(() => {
        const firstKey = err && typeof err === 'object' ? Object.keys(err)[0] : ''
        if (!firstKey) return
        const el = document.querySelector(`#formAltRegister [id*="${firstKey}"], #formAltRegister input, #formAltRegister .ant-select`)
        if (el && typeof el.scrollIntoView === 'function') {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      })
    },
    emitRegisterSuccess (payload) {
      this.$emit('register-success', payload)
    },
    handleSubmit (e) {
      e.preventDefault()
      const { validateFields } = this.form
      this.state.registerBtn = true

      const validateFieldsKey = ['username', 'phone', 'sms_code', 'full_name', 'register_province', 'school', 'role', 'password', 'confirmPassword']
      const currentRole = this.form.getFieldValue('role')
      if (currentRole === 'student') {
        validateFieldsKey.push('student_id')
      } else if (this.isAdvisorRegisterRole(currentRole)) {
        validateFieldsKey.push('teacher_id')
      }

      validateFields(validateFieldsKey, { force: true }, (err, values) => {
        if (err) {
          this.showFormValidationModal(err)
          setTimeout(() => {
            this.state.registerBtn = false
          }, 600)
          return
        }

        const registerParams = {
          username: String(values.username || '').trim(),
          phone: String(values.phone || '').trim(),
          sms_code: String(values.sms_code || '').trim(),
          full_name: String(values.full_name || '').trim(),
          school: (values.school || '').trim(),
          password: values.password,
          role: values.role
        }
        if (values.role === 'student') {
          registerParams.student_id = String(values.student_id || '').trim()
        }
        if (this.isAdvisorRegisterRole(values.role)) {
          registerParams.role = 'advisor'
          registerParams.teacher_id = String(values.teacher_id || '').trim()
        }

        altIdentityRegister(registerParams)
          .then((res) => {
            if (!(res && (res.id != null || res.user_id != null || res.access_token))) {
              this.$message.error('注册失败，请重试')
              return
            }
            const registeredId = res.id != null ? res.id : res.user_id
            const payload = { role: values.role, registeredId }

            if (values.role === 'expert' && registeredId != null) {
              this.$notification.success({
                message: '专家注册成功',
                description: `您的用户 ID 为 ${registeredId}。当前待管理员核验，暂无法登录。`,
                duration: this.mode === 'embedded' ? 6 : 0
              })
              if (this.mode === 'embedded') {
                this.emitRegisterSuccess(payload)
              } else {
                setTimeout(() => this.emitRegisterSuccess(payload), 6000)
              }
              return
            }

            if (values.role === 'school_admin') {
              this.$notification.success({
                message: '校管理员注册成功',
                description: '您可立即登录。登录后请提交资料申请（含照片），待超级管理员审核通过后方可进行本校组队校审。',
                duration: 6
              })
              const delay = this.mode === 'embedded' ? 0 : 2000
              setTimeout(() => this.emitRegisterSuccess(payload), delay)
              return
            }

            this.$message.success('注册成功！')
            const delay = this.mode === 'embedded' ? 0 : 1500
            setTimeout(() => this.emitRegisterSuccess(payload), delay)
          })
          .catch((e) => {
            if (!showRegisterConflictModal(this, e)) {
              const msg = extractRegisterError(e) || (e && e.message) || '注册失败，请重试'
              this.$warning({
                title: '注册失败',
                content: msg,
                okText: '知道了'
              })
            }
          })
          .finally(() => {
            this.state.registerBtn = false
          })
      })
    },
    requestFailed (err) {
      const desc = extractRegisterError(err) || '请求出现错误，请稍后再试'
      this.$notification.error({
        message: '注册失败',
        description: desc,
        duration: 4
      })
    }
  }
}
</script>

<style lang="less" scoped>
.user-layout-register {
  button.register-button {
    padding: 0 15px;
    font-size: 16px;
    height: 40px;
    width: 100%;
  }

  .login-link {
    color: #1890ff;
    text-decoration: none;
    display: block;
    text-align: center;

    &:hover {
      text-decoration: underline;
    }
  }

  .register-field-hint {
    display: block;
    color: #f5222d;
    font-size: 13px;
    line-height: 1.5;
    margin-top: 4px;
  }
}



.embedded-login-link-item {
  margin-bottom: 0;
}
</style>
