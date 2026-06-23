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
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
                { max: 100, message: '用户名最长100个字符' }
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
          <span v-show="hintFocus.username" class="register-field-hint">至少 3 个字符，最长 100 个字符。</span>
        </template>
      </a-form-item>

      <a-form-item>
        <a-input
          size="large"
          type="email"
          placeholder="请输入邮箱"
          v-decorator="[
            'email',
            { rules: [{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入正确的邮箱地址' }], validateTrigger: 'change' }
          ]"
        >
          <a-icon slot="prefix" type="mail" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item>
        <a-input
          size="large"
          type="text"
          placeholder="请输入姓名"
          v-decorator="[
            'full_name',
            { rules: [{ required: true, message: '请输入姓名' }], validateTrigger: 'change' }
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
            { rules: [{ required: true, message: '请输入学号' }], validateTrigger: 'change' }
          ]"
        >
          <a-icon slot="prefix" type="number" :style="{ color: 'rgba(0,0,0,.25)' }" />
        </a-input>
      </a-form-item>

      <a-form-item v-if="form.getFieldValue('role') === 'advisor'">
        <a-input
          size="large"
          type="text"
          placeholder="请输入指导老师编号"
          v-decorator="[
            'teacher_id',
            { rules: [{ required: true, message: '请输入指导老师编号' }], validateTrigger: 'change' }
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
            { rules: [{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }], validateTrigger: 'blur' }
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
          :to="{ name: 'ManuVideoCompetition' }"
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
import { altIdentityRegister } from '@/api/altIdentity'
import { showRegisterConflictModal, extractRegisterError } from '@/utils/registerConflict'
import {
  PROVINCE_OPTIONS,
  filterSchoolsByKeyword,
  isSchoolInProvince
} from '@/data/chinaSchoolsByProvince'

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
        registerBtn: false
      }
    }
  },
  computed: {
    schoolNotFoundContent () {
      if (!this.selectedProvince) return '请先选择省份'
      if (!this.schoolSearchKeyword) return '请输入关键字搜索学校'
      return '未找到匹配学校'
    }
  },
  methods: {
    isAdvisorRegisterRole (role) {
      return role === 'advisor' || role === 'teacher'
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
    emitRegisterSuccess (payload) {
      this.$emit('register-success', payload)
    },
    handleSubmit (e) {
      e.preventDefault()
      const { validateFields } = this.form
      this.state.registerBtn = true

      const validateFieldsKey = ['username', 'email', 'full_name', 'register_province', 'school', 'role', 'password', 'confirmPassword']
      const currentRole = this.form.getFieldValue('role')
      if (currentRole === 'student') {
        validateFieldsKey.push('student_id')
      } else if (this.isAdvisorRegisterRole(currentRole)) {
        validateFieldsKey.push('teacher_id')
      }

      validateFields(validateFieldsKey, { force: true }, (err, values) => {
        if (err) {
          setTimeout(() => {
            this.state.registerBtn = false
          }, 600)
          return
        }

        const registerParams = {
          username: values.username,
          email: values.email,
          full_name: values.full_name,
          school: (values.school || '').trim(),
          password: values.password,
          role: values.role
        }
        if (values.role === 'student') {
          registerParams.student_id = values.student_id
        }
        if (this.isAdvisorRegisterRole(values.role)) {
          registerParams.role = 'advisor'
          registerParams.teacher_id = values.teacher_id
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
          .catch(err => {
            if (!showRegisterConflictModal(this, err)) {
              this.requestFailed(err)
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

.alt-identity-register-panel--embedded {
  max-height: 62vh;
  overflow-y: auto;
  padding-right: 4px;
}

.embedded-login-link-item {
  margin-bottom: 0;
}
</style>
