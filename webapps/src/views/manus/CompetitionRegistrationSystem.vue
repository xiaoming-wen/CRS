<template>
  <div class="competition-system">
    <a-card
      :bordered="false"
      class="section-card competition-main-card"
      :class="{ 'competition-main-card--standalone': standaloneDetailMode }"
    >
      <template v-if="!standaloneDetailMode">
        <div class="top-row">
          <a-input-search
            v-model="keyword"
            placeholder="搜索竞赛名称/简介（可选）"
            style="width: 360px"
            @search="fetchCompetitions"
          />
          <a-button type="primary" :loading="competitionsLoading" @click="fetchCompetitions">
            刷新竞赛
          </a-button>
          <span v-if="isStudent && studentAccountIdLabel" class="student-account-id-hint">
            学生ID：<strong>{{ studentAccountIdLabel }}</strong>
          </span>
          <template v-if="canManageCompetitions">
            <a-divider type="vertical" />
            <a-button type="primary" :loading="adminCreateLoading" @click="showCreateCompetitionModal = true">
              创建竞赛
            </a-button>
            <a-button
              :loading="publishLoading"
              @click="handlePublish"
              :disabled="!selectedCompetitionId"
              style="margin-left: 8px"
            >
              发布竞赛
            </a-button>

            <a-button
              style="margin-left: 8px"
              :disabled="!selectedCompetitionId"
              @click="openEditCompetitionModal"
            >
              修改竞赛
            </a-button>

            <a-button
              style="margin-left: 8px"
              type="primary"
              ghost
              :loading="adminLockLoading"
              @click="handleLockCompetition"
              :disabled="!selectedCompetitionId"
            >
              锁定竞赛
            </a-button>

            <a-button
              style="margin-left: 8px"
              type="danger"
              :loading="adminDeleteLoading"
              @click="handleDeleteCompetition"
              :disabled="!selectedCompetitionId"
            >
              删除竞赛
            </a-button>
          </template>
        </div>

        <div v-if="canManageCompetitions" class="muted" style="margin-top: 8px; font-size: 13px">
          请在表格左侧勾选一条竞赛，以便使用顶部「发布 / 修改 / 锁定 / 删除」等操作；完整管理与评阅请在「操作」列点击「查看详情」在新标签页打开。专家核验与按赛指派请使用左侧目录「专家指派」。
        </div>
        <div v-else-if="isStudent" class="muted" style="margin-top: 8px; font-size: 13px">
          学生请在「操作」列点击「查看详情」，在新标签页中报名与提交作品。
        </div>
        <div v-else-if="showAdvisorTeamPanel" class="muted" style="margin-top: 8px; font-size: 13px">
          指导老师请在「操作」列点击「查看详情」，在详情页进行组班、邀请队员与管理队名。
        </div>
        <div v-else-if="isCompetitionExpert" class="muted" style="margin-top: 8px; font-size: 13px">
          专家请在「操作」列打开<strong>已指派</strong>的竞赛详情，进行作品评阅、查看评分汇总与排行榜。
        </div>

        <a-alert
          v-if="competitionsError"
          type="warning"
          show-icon
          :message="competitionsError"
          style="margin-top: 16px"
        />

        <div style="margin-top: 16px">
          <a-table
            row-key="id"
            size="middle"
            :loading="competitionsLoading"
            :columns="competitionListColumns"
            :data-source="competitionListTableData"
            :pagination="competitionListPagination"
            :row-selection="competitionListRowSelection"
            :row-class-name="competitionListRowClassName"
            :scroll="{ x: 1040 }"
          >
            <template slot="status" slot-scope="text">
              <a-tag
                :color="getStatusColor(text)"
                :style="text === 'draft' ? { color: '#000' } : null"
              >
                {{ getStatusText(text) }}
              </a-tag>
            </template>
            <template slot="listActions" slot-scope="text, record">
              <a @click.stop.prevent="openCompetitionDetailInNewTab(record.id)">查看详情</a>
            </template>
          </a-table>
        </div>

      </template>

      <div
        v-if="showCompetitionDetailPanel && standaloneDetailMode"
        class="competition-detail-below-list competition-detail-transparent-tables"
        :class="{ 'competition-detail-below-list--solo': standaloneDetailMode }"
      >
        <!-- 详情头图：学生端展示；教师/管理员独立详情页不展示（直接进入竞赛信息） -->
        <div
          v-if="isStudent"
          class="competition-hero-banner"
          :class="{ 'competition-hero-banner--solo': standaloneDetailMode }"
        >
          <div class="competition-hero-banner__glow" aria-hidden="true" />
          <div class="competition-hero-banner__inner competition-hero-banner__inner--center">
            <div class="competition-hero-banner__copy">
              <div v-if="competitionHeroYear" class="competition-hero-banner__year">{{ competitionHeroYear }}</div>
              <h1 class="competition-hero-banner__title">
                {{ activeCompetition ? activeCompetition.name : `竞赛 #${activeCompetitionId}` }}
              </h1>
              <div class="competition-hero-banner__title-meta">
                <a-tag
                  v-if="activeCompetition"
                  class="competition-hero-banner__status-tag"
                  :color="getStatusColor(activeCompetition.status)"
                  :style="activeCompetition.status === 'draft' ? { color: '#1a1a1a', borderColor: 'rgba(0,0,0,0.15)' } : null"
                >
                  {{ getStatusText(activeCompetition.status) }}
                </a-tag>
                <span class="competition-hero-banner__id">ID {{ activeCompetitionId }}</span>
              </div>
              <p v-if="competitionHeroSubtitleEn" class="competition-hero-banner__title-en">{{ competitionHeroSubtitleEn }}</p>
              <p v-if="competitionHeroSlogan" class="competition-hero-banner__slogan">{{ competitionHeroSlogan }}</p>
              <div v-if="activeCompetition" class="competition-hero-banner__dates">
                <span class="competition-hero-banner__dates-label">活动时间</span>
                <span class="competition-hero-banner__dates-range">{{ competitionHeroDateRange }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 学生独立详情：赛题说明（参考赛事说明页：双栏、网格底、章节编号） -->
        <a-card
          v-if="activeCompetition && isStudent && standaloneDetailMode"
          size="small"
          class="sub-card competition-briefing-card competition-info-card"
          :bordered="false"
        >
          <div class="competition-briefing">
            <header class="competition-briefing__header">
              <h2 class="competition-briefing__main-title">竞赛相关</h2>
              <p class="competition-briefing__sub-en">DIRECTIONS</p>
            </header>
            <div class="competition-briefing__frame">
              <div class="competition-briefing__grid" aria-hidden="true" />
              <div class="competition-briefing__body">
                <div class="competition-briefing__col competition-briefing__col--main">
                  <div
                    v-for="block in studentBriefingBlocks"
                    :key="block.num + block.title"
                    class="competition-briefing__section"
                  >
                    <span class="competition-briefing__section-bg-num" aria-hidden="true">{{ block.num }}</span>
                    <h3 class="competition-briefing__section-title">{{ block.title }}</h3>
                    <div class="competition-briefing__section-text">{{ block.body }}</div>
                  </div>
                  <ul class="competition-briefing__footnotes">

                    <li>请勿使用未经授权的他人作品素材；提交作品即表示同意遵守主办方公布的赛事规则。</li>
                  </ul>
                </div>
                <div class="competition-briefing__col competition-briefing__col--aside">
                  <div class="competition-briefing__aside-inner">
                    <img
                      v-if="studentBriefingQrObjectUrl"
                      :src="studentBriefingQrObjectUrl"
                      class="competition-briefing__qr"
                      alt="赛事交流群二维码"
                    />
                    <div v-else class="competition-briefing__qr-placeholder">暂无二维码</div>

                    <div v-if="studentBriefingContactLine" class="competition-briefing__contact">
                      电话联系方式：<span class="competition-briefing__contact-num">{{ studentBriefingContactLine }}</span>
                    </div>
                    <div v-else class="competition-briefing__contact muted-soft">
                      联系电话请见群内公告或主办方通知。
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </a-card>

        <a-card
          v-else-if="activeCompetition"
          size="small"
          class="sub-card competition-info-card"
          :bordered="true"
          title="竞赛信息"
        >
          <a-descriptions :column="2" size="small" bordered>
            <a-descriptions-item label="竞赛ID">{{ activeCompetition.id }}</a-descriptions-item>
            <a-descriptions-item label="竞赛名称">{{ activeCompetition.name }}</a-descriptions-item>
            <a-descriptions-item label="简介" :span="2">{{ activeCompetition.description || '-' }}</a-descriptions-item>
            <a-descriptions-item label="规则说明" :span="2">{{ activeCompetition.rules_text || '-' }}</a-descriptions-item>
            <a-descriptions-item label="开始时间">{{ formatDateTime(activeCompetition.start_at) }}</a-descriptions-item>
            <a-descriptions-item label="结束时间">{{ formatDateTime(activeCompetition.end_at) }}</a-descriptions-item>
            <a-descriptions-item label="允许个人参赛">{{ activeCompetition.allow_individual ? '是' : '否' }}</a-descriptions-item>
            <a-descriptions-item label="允许团队参赛">{{ activeCompetition.allow_team ? '是' : '否' }}</a-descriptions-item>
            <a-descriptions-item label="状态">{{ getStatusText(activeCompetition.status) }}</a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ formatDateTime(activeCompetition.created_at) }}</a-descriptions-item>
            <a-descriptions-item label="更新时间" :span="2">{{ formatDateTime(activeCompetition.updated_at) }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-divider />

        <!-- 学生区（非独立详情页：内联展示） -->
        <div v-if="isStudent && !standaloneDetailMode">
          <a-card size="small" class="sub-card" :bordered="true" title="报名与组队">
            <a-alert
              v-if="competitionEnrollPublishBlocked"
              type="warning"
              show-icon
              :message="competitionEnrollBlockedAlertTitle"
              :description="competitionEnrollBlockedAlertDescription"
              style="margin-bottom: 12px"
            />
            <a-form layout="inline" :style="{ marginBottom: '12px' }">
              <a-form-item label="参赛方式">
                <a-radio-group v-model="enrollMode">
                  <a-radio-button value="individual" :disabled="!allowIndividual">个人参赛</a-radio-button>
                  <a-radio-button value="team" :disabled="!allowTeam">队伍参赛</a-radio-button>
                </a-radio-group>
              </a-form-item>
            </a-form>
           

            <a-form layout="vertical" class="enroll-profile-form" style="margin-top: 4px; max-width: 640px">
              
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <a-form-item label="学号" :colon="false">
                    <a-input
                      v-model="enrollProfileForm.student_no"
                      placeholder="选填"
                      :allow-clear="!enrollProfileLockedAfterSuccess"
                      :disabled="enrollProfileLockedAfterSuccess"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="姓名" :colon="false">
                    <a-input
                      v-model="enrollProfileForm.real_name"
                      placeholder="选填"
                      :allow-clear="!enrollProfileLockedAfterSuccess"
                      :disabled="enrollProfileLockedAfterSuccess"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="学院" :colon="false">
                    <a-input
                      v-model="enrollProfileForm.college"
                      placeholder="选填"
                      :allow-clear="!enrollProfileLockedAfterSuccess"
                      :disabled="enrollProfileLockedAfterSuccess"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="年级" :colon="false">
                    <a-input
                      v-model="enrollProfileForm.grade"
                      placeholder="如 2023级，选填"
                      :allow-clear="!enrollProfileLockedAfterSuccess"
                      :disabled="enrollProfileLockedAfterSuccess"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="联系方式" :colon="false">
                    <a-input
                      v-model="enrollProfileForm.contact"
                      placeholder="手机或邮箱，选填"
                      :allow-clear="!enrollProfileLockedAfterSuccess"
                      :disabled="enrollProfileLockedAfterSuccess"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
            </a-form>

            <div v-if="enrollMode === 'team'" class="muted" style="margin-bottom: 12px; font-size: 13px">
              <template v-if="studentTeamEnrolledAsMember">
                您已完成队伍赛道报名（队员身份）。队伍由队长统一管理，无需创建/加入队伍或进行队长操作。
              </template>
              <template v-else>
                队伍参赛流程：① 创建队伍 <strong>或</strong> 加入已有队伍 → ② 获得「我的队伍ID」后 → ③ 若后端未自动报名，再点击「报名（队伍）」。（部分接口在创建队伍时已自动完成竞赛报名，此时无需再点报名。）
              </template>
            </div>

            <div class="row">
              <a-button
                type="primary"
                :loading="enrollLoading"
                @click="handleEnrollIndividual"
                v-if="enrollMode === 'individual'"
                :disabled="competitionEnrollPublishBlocked || !allowIndividual || myEnrolledIndividual"
              >
                {{ myEnrolledIndividual ? '个人已报名' : '报名个人' }}
              </a-button>

              <template v-else>
                <a-button
                  v-if="showStudentTeamCreateJoinOps"
                  type="primary"
                  :loading="enrollLoading"
                  @click="handleCreateTeamOnly"
                  :disabled="competitionEnrollPublishBlocked || !allowTeam || studentHasTeamForCurrentCompetition"
                  style="margin-right: 8px"
                >
                  创建队伍（自动队长）
                </a-button>
                <a-button
                  type="primary"
                  :loading="enrollLoading"
                  @click="handleEnrollWithTeam"
                  :disabled="competitionEnrollPublishBlocked || !allowTeam || myEnrolledTeam || !teamEnrollmentEligible || !myTeamId || teamEnrollActionBlockedForMember"
                >
                  {{ myEnrolledTeam ? '队伍已报名' : '报名（队伍）' }}
                </a-button>
              </template>
            </div>
            <p v-if="enrollMode === 'team' && teamEnrollActionBlockedForMember" class="muted" style="margin: 8px 0 0; font-size: 13px">
              您已完成队伍报名且为队员，无需重复报名；创建队伍、加入队伍等操作已由队长负责。
            </p>

            <div v-if="enrollMode === 'team'" style="margin-top: 12px">
              <a-form layout="vertical">
                <a-form-item label="我的队伍ID（创建或加入成功后自动填入）">
                  <a-input-number
                    v-model="myTeamId"
                    :min="1"
                    placeholder="请先创建队伍或加入队伍"
                    style="width: 240px"
                    :disabled="true"
                  />
                </a-form-item>
                <a-form-item v-if="showStudentTeamCreateJoinOps" label="加入已有队伍（输入队长提供的队伍ID）">
                  <div class="row">
                    <a-input-number
                      v-model="joinTeamId"
                      :min="1"
                      placeholder="请输入队伍ID"
                      style="width: 180px"
                      :disabled="competitionEnrollPublishBlocked || studentHasTeamForCurrentCompetition"
                    />
                    <a-button
                      :loading="teamLoading"
                      :disabled="competitionEnrollPublishBlocked || studentHasTeamForCurrentCompetition"
                      @click="handleJoinTeam"
                    >
                      加入队伍
                    </a-button>
                  </div>
                </a-form-item>
              </a-form>

              <template v-if="showStudentTeamCaptainOptionalOps">
              <a-divider />
              <a-form layout="vertical">
                <a-form-item label="队长转让（可选）">
                  <div class="row">
                    <a-input-number v-model="transferTeamId" :min="1" placeholder="队伍ID" style="width: 180px" />
                    <a-input-number
                      v-model="newCaptainId"
                      :min="1"
                      placeholder="新队长用户ID"
                      style="width: 180px"
                    />
                    <a-button
                      :loading="teamLoading"
                      @click="handleTransferCaptain"
                      :disabled="!transferTeamId || !newCaptainId"
                    >
                      转让
                    </a-button>
                  </div>
                </a-form-item>
                <a-form-item label="队长退队（可选，强制先转让）">
                  <div class="row">
                    <a-input-number v-model="leaveTeamId" :min="1" placeholder="队伍ID" style="width: 180px" />
                    <a-button
                      danger
                      :loading="teamLoading"
                      @click="handleLeaveTeam"
                      :disabled="!leaveTeamId"
                    >
                      退队
                    </a-button>
                  </div>
                </a-form-item>
                <template v-if="isCurrentTeamCaptain">
                  <a-form-item label="邀请队员（队长）">
                    <div class="row">
                      <a-input-number
                        v-model="studentTeamInviteId"
                        :min="1"
                        placeholder="队员用户ID"
                        style="width: 220px"
                        :disabled="competitionTeamCreateInviteBlocked"
                      />
                      <a-button
                        type="primary"
                        :loading="teamLoading"
                        :disabled="competitionTeamCreateInviteBlocked || !studentTeamInviteId || !myTeamId"
                        @click="handleStudentTeamInviteMember"
                      >
                        邀请队员
                      </a-button>
                    </div>
                  </a-form-item>
                  <a-form-item label="移除队员（队长）">
                    <div class="row">
                      <a-input-number
                        v-model="studentTeamRemoveMemberId"
                        :min="1"
                        placeholder="待移除队员用户ID"
                        style="width: 220px"
                        :disabled="competitionTeamRemoveMemberBlocked"
                      />
                      <a-button
                        danger
                        :loading="teamLoading"
                        :disabled="competitionTeamRemoveMemberBlocked || !studentTeamRemoveMemberId || !myTeamId"
                        @click="handleStudentTeamRemoveMember"
                      >
                        移除队员
                      </a-button>
                    </div>
                  </a-form-item>
                </template>
              </a-form>
              </template>
            </div>
          </a-card>

          <a-card
            v-if="hasAnyEnrollment && showSubmissionPanelInEnrollView"
            size="small"
            class="sub-card"
            :bordered="true"
            title="作品提交"
            style="margin-top: 16px"
          >
            <a-form layout="vertical">
              <a-form-item label="作品标题" required>
                <a-input v-model="submissionForm.title" placeholder="请输入作品标题" style="max-width: 520px" />
              </a-form-item>
              <a-form-item label="作品描述">
                <a-textarea
                  v-model="submissionForm.description"
                  :rows="3"
                  placeholder="选填"
                  style="max-width: 520px"
                />
              </a-form-item>
              <a-form-item label="文本内容（选填，与文件二选一至少一个）">
                <a-textarea
                  v-model="submissionForm.content_text"
                  :rows="4"
                  placeholder="选填"
                  style="max-width: 520px"
                />
              </a-form-item>
              <a-form-item label="文件（选填，支持上传；与文本至少一个）">
                <input type="file" @change="handleFileChange" />
                <div v-if="submissionForm.file" class="muted" style="margin-top: 6px">
                  已选择：{{ submissionForm.file.name }}
                </div>
              </a-form-item>

              <a-form-item label="提交类型">
                <a-radio-group v-model="submissionMode" @change="onSubmissionModeChange">
                  <a-radio-button value="individual" :disabled="!myEnrolledIndividual || !allowIndividual">个人提交</a-radio-button>
                  <a-radio-button value="team" :disabled="!myEnrolledTeam || !allowTeam || !isCurrentTeamCaptain">队伍提交</a-radio-button>
                </a-radio-group>
              </a-form-item>

              <div class="row">
                <a-button type="primary" :loading="submitLoading" @click="handleSubmitSubmission">
                  提交作品
                </a-button>
                <a-button style="margin-left: 8px" @click="refreshMySubmissions" :loading="submissionsLoading">
                  刷新我的作品
                </a-button>
                <a-button style="margin-left: 8px" @click="refreshMyScores(true)" :loading="scoresLoading">
                  查看我的成绩
                </a-button>
              </div>
            </a-form>
          </a-card>
          <a-alert
            v-else-if="myEnrolledTeam && enrollMode === 'team' && !isCurrentTeamCaptain"
            type="info"
            show-icon
            message="当前账号为队员，只有队长可以提交队伍作品"
            style="margin-top: 16px"
          />

          <a-card size="small" class="sub-card" :bordered="true" title="我的作品" style="margin-top: 16px">
            <a-empty v-if="mySubmissions.length === 0" description="暂无作品，请先报名并提交" />
            <div v-else class="submissions-list">
              <a-card
                v-for="s in mySubmissions"
                :key="s.id"
                size="small"
                class="submission-item"
                :bordered="false"
              >
                <div class="submission-title-row">
                  <div class="submission-title">{{ s.title || '-' }}</div>
                  <a-tag :color="getSubmissionStatusColor(s.status)">
                    {{ getSubmissionStatusText(s.status) }}
                  </a-tag>
                </div>
                <div class="muted" style="margin-top: 6px">
                  提交时间：{{ formatDateTime(s.submitted_at) }}
                </div>
                <div class="row" style="margin-top: 10px">
                  <a-button size="small" :disabled="!s.id" @click="downloadSubmission(s.id)">
                    下载文件
                  </a-button>
                </div>
              </a-card>
            </div>
          </a-card>

        </div>

        <!-- 指导老师/教师：组班与队务（§8.12 / §8.12.1–§8.12.3） -->
        <div v-else-if="showAdvisorTeamPanel">
          <a-card size="small" class="sub-card" :bordered="true" title="组班与队务（指导老师）" style="margin-top: 16px">
            <a-alert
              v-if="competitionTeamCreateInviteBlocked"
              type="warning"
              show-icon
              message="当前不可新建队伍或邀请队员"
              :description="competitionTeamCreateInviteBlockedDescription"
              style="margin-bottom: 12px"
            />
            

            <a-divider orientation="left">创建队伍</a-divider>
            <a-form layout="vertical" style="max-width: 720px">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <a-form-item label="队名（选填）">
                    <a-input
                      v-model="advisorCreateForm.name"
                      placeholder="如：一班代表队"
                      :disabled="competitionTeamCreateInviteBlocked || !allowTeam"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="队长学生 ID">
                    <a-input-number
                      v-model="advisorCreateForm.captain_student_id"
                      :min="1"
                      placeholder="默认同队员列表首人"
                      style="width: 100%"
                      :disabled="competitionTeamCreateInviteBlocked || !allowTeam"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="24">
                  <a-form-item label="初始队员 ID（必填，逗号分隔）" required>
                    <a-input
                      v-model="advisorCreateForm.initial_member_ids_text"
                      placeholder="如：7,8,9"
                      :disabled="competitionTeamCreateInviteBlocked || !allowTeam"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button
                type="primary"
                :loading="advisorCreateLoading"
                :disabled="competitionTeamCreateInviteBlocked || !allowTeam || !activeCompetitionId"
                @click="handleAdvisorCreateTeam"
              >
                创建队伍并拉入队员
              </a-button>
            </a-form>

            <a-divider orientation="left">队伍列表与队务</a-divider>
            <div class="row" style="margin-bottom: 12px">
              <a-button
                :loading="advisorTeamsLoading"
                :disabled="!activeCompetitionId"
                @click="refreshAdvisorTeams"
              >
                刷新队伍列表
              </a-button>
            </div>
            <a-empty v-if="!advisorTeamsLoading && advisorTeams.length === 0" description="暂无队伍，请先创建或刷新" />
            <a-table
              v-else
              class="advisor-teams-table"
              row-key="id"
              size="small"
              bordered
              :loading="advisorTeamsLoading"
              :columns="advisorTeamsTableColumns"
              :data-source="advisorTeamsTableData"
              :pagination="{ pageSize: 8, showSizeChanger: true }"
              :scroll="{ x: 880 }"
            >
              <template slot="teamActions" slot-scope="text, record">
                <a-button
                  size="small"
                  type="link"
                  class="advisor-team-manage-btn"
                  @click.stop="selectAdvisorTeam(record.id)"
                >
                  管理
                </a-button>
              </template>
            </a-table>

            <a-card
              v-if="advisorSelectedTeam"
              size="small"
              class="sub-card advisor-manage-team-card"
              :bordered="true"
              :title="`管理队伍 #${advisorSelectedTeam.id}`"
              style="margin-top: 16px"
            >
              <a-descriptions size="small" bordered :column="2">
                <a-descriptions-item label="队名">{{ advisorSelectedTeam.name || '（未设置）' }}</a-descriptions-item>
                <a-descriptions-item label="队长 ID">{{ advisorSelectedTeam.captain_id }}</a-descriptions-item>
                <a-descriptions-item label="状态">{{ participantTeamStatusText(advisorSelectedTeam.status) }}</a-descriptions-item>
                <a-descriptions-item label="建队老师 ID">{{ advisorSelectedTeam.created_by_advisor_id != null ? advisorSelectedTeam.created_by_advisor_id : '-' }}</a-descriptions-item>
              </a-descriptions>

              <div class="advisor-manage-team-ops">
                <a-form layout="inline" style="margin-top: 12px">
                  <a-form-item label="新队名">
                    <a-input
                      v-model="advisorRenameName"
                      placeholder="可留空表示清空展示名"
                      style="width: 220px"
                      :disabled="!canOperateAdvisorSelectedTeam"
                    />
                  </a-form-item>
                  <a-form-item>
                    <a-button
                      type="primary"
                      :loading="advisorTeamOpLoading"
                      :disabled="!canOperateAdvisorSelectedTeam"
                      @click="handleAdvisorRenameTeam"
                    >
                      保存队名
                    </a-button>
                  </a-form-item>
                </a-form>

                <a-form layout="inline" style="margin-top: 8px">
                  <a-form-item label="邀请学生 ID">
                    <a-input-number
                      v-model="advisorInviteStudentId"
                      :min="1"
                      placeholder=""
                      style="width: 180px"
                      :disabled="!canOperateAdvisorSelectedTeam || competitionTeamCreateInviteBlocked"
                    />
                  </a-form-item>
                  <a-form-item>
                    <a-button
                      type="primary"
                      :loading="advisorTeamOpLoading"
                      :disabled="!canOperateAdvisorSelectedTeam || competitionTeamCreateInviteBlocked || !advisorInviteStudentId"
                      @click="handleAdvisorInviteMember"
                    >
                      邀请入队
                    </a-button>
                  </a-form-item>
                </a-form>
              </div>
              <div v-if="advisorSelectedTeamMembers.length" class="advisor-team-members-list" style="margin-top: 12px">
                <div class="advisor-team-members-label" style="margin-bottom: 6px; font-size: 13px">队员</div>
                <div
                  v-for="m in advisorSelectedTeamMembers"
                  :key="'tm-' + m.id + '-' + m.user_id"
                  class="row advisor-team-member-row"
                  style="justify-content: space-between; padding: 6px 0"
                >
                  <span>
                    用户 ID {{ m.user_id }}
                    <a-tag v-if="m.is_captain" color="blue" style="margin-left: 8px">队长</a-tag>
                  </span>
                  <a-button
                    v-if="canOperateAdvisorSelectedTeam && !m.is_captain && !competitionTeamRemoveMemberBlocked"
                    size="small"
                    type="link"
                    danger
                    :loading="advisorTeamOpLoading && advisorRemovingUserId === m.user_id"
                    @click="handleAdvisorRemoveMember(advisorSelectedTeam.id, m.user_id)"
                  >
                    移除
                  </a-button>
                </div>
              </div>
              <p v-if="!canOperateAdvisorSelectedTeam" class="muted" style="margin: 8px 0 0; font-size: 13px">
                当前队伍非您创建且您无队务权限，仅可查看；改队名、邀请队员需由建队老师或队长操作。
              </p>
              <p
                v-else-if="competitionTeamCreateInviteBlocked"
                class="muted advisor-manage-team-hint"
                style="margin: 8px 0 0; font-size: 13px"
              >
                {{ competitionTeamCreateInviteBlockedDescription }}
              </p>
              <p
                v-if="canOperateAdvisorSelectedTeam && competitionTeamRemoveMemberBlocked && advisorSelectedTeamMembers.length"
                class="muted advisor-manage-team-hint"
                style="margin: 8px 0 0; font-size: 13px"
              >
                {{ competitionTeamRemoveMemberBlockedMessage }}
              </p>
            </a-card>
          </a-card>
        </div>

        <a-alert
          v-if="showExpertNotAssignedHint"
          type="warning"
          show-icon
          style="margin-top: 16px"
          message="未指派到本竞赛"
          :description="roleNoPermissionDescription"
        />

        <!-- 管理员 / 已指派专家评阅区 -->
        <div v-if="isCompetitionWorkbench">
          <a-card
            v-if="canViewCompetitionSubmissions"
            size="small"
            class="sub-card"
            :bordered="true"
            title="作品列表（竞赛维度）"
            style="margin-top: 16px"
          >
            <div style="display: flex; justify-content: flex-end; margin-bottom: 8px">
              <a-button :loading="adminSubmissionsLoading" :disabled="!activeCompetitionId" @click="refreshAdminSubmissions">
                刷新该竞赛全部作品
              </a-button>
            </div>
            <p
              v-if="adminSubmissionsHiddenByWithdrawCount > 0"
              class="muted"
              style="margin: 0 0 8px; font-size: 13px"
            >
              仅展示当前有效报名周期内的提交。
            </p>
            <a-empty v-if="adminSubmissions.length === 0" :description="adminSubmissionsEmptyDescription" />
            <div v-else class="submissions-list">
              <a-card
                v-for="s in adminSubmissions"
                :key="s.id"
                size="small"
                class="submission-item"
                :bordered="false"
              >
                <div class="submission-title-row">
                  <div class="submission-title">{{ s.title || '-' }}</div>
                  <a-tag :color="getSubmissionStatusColor(s.status)">
                    {{ getSubmissionStatusText(s.status) }}
                  </a-tag>
                </div>
                <div class="submission-meta muted" style="margin-top: 6px">
                  <span>提交ID：{{ s.id }}</span>
                  <span style="margin-left: 12px">队伍ID：{{ s.team_id != null ? s.team_id : '-' }}</span>
                  <span style="margin-left: 12px">学生ID：{{ s.student_id != null ? s.student_id : '-' }}</span>
                  <span style="margin-left: 12px">提交人ID：{{ s.submitter_id != null ? s.submitter_id : '-' }}</span>
                  <span style="margin-left: 12px">提交时间：{{ formatDateTime(s.submitted_at) }}</span>
                </div>
                <div v-if="isSubmissionGraded(s)" class="muted" style="margin-top: 4px; font-size: 12px">
                  分数：{{ formatScoreCell(s) }}
                </div>
                <div v-if="s.content_text" class="muted" style="margin-top: 4px; font-size: 12px; max-height: 60px; overflow: hidden; text-overflow: ellipsis">
                  文本内容：{{ s.content_text }}
                </div>

                <div class="row" style="margin-top: 10px">
                  <template v-if="canReviewSubmissions">
                    <a-button
                      v-if="!isSubmissionGraded(s)"
                      size="small"
                      type="primary"
                      :disabled="s.status === 'draft'"
                      @click="fillGradeForm(s.id, false)"
                    >
                      评分
                    </a-button>
                    <a-button
                      v-else
                      size="small"
                      type="primary"
                      @click="fillGradeForm(s.id, true)"
                    >
                      修改评分
                    </a-button>
                  </template>
                  <a-button size="small" style="margin-left: 8px" :disabled="!s.file_id" @click="downloadSubmission(s.id)">
                    下载文件
                  </a-button>
                </div>
              </a-card>
            </div>
          </a-card>

          <a-card
            v-if="showGradeAudit && canReviewSubmissions"
            size="small"
            class="sub-card"
            :bordered="true"
            :title="gradeFormIsEdit ? '修改评分（评委）' : '评分/审核（评委）'"
            style="margin-top: 16px"
          >
            <a-form layout="vertical">
              <a-form-item label="作品提交ID" required>
                <a-input-number v-model="gradeForm.submission_id" :min="1" placeholder="请输入作品提交ID" style="width: 240px" />
              </a-form-item>
              <a-form-item label="分数" required>
                <a-input v-model="gradeForm.score" placeholder="例如：95.0" style="width: 240px" />
              </a-form-item>
              <a-form-item label="反馈">
                <a-textarea v-model="gradeForm.feedback" :rows="3" placeholder="选填" style="max-width: 520px" />
              </a-form-item>
              <div class="row">
                <a-button
                  type="primary"
                  :loading="gradeLoading"
                  @click="handleReviewGrade"
                  :disabled="!gradeForm.submission_id"
                >
                  {{ gradeFormIsEdit ? '保存修改' : '提交评分' }}
                </a-button>
                <a-button style="margin-left: 8px" @click="cancelGradeAudit" :disabled="gradeLoading">
                  取消
                </a-button>
              </div>
            </a-form>
          </a-card>

          <a-card
            v-if="canViewParticipantsRoster"
            size="small"
            class="sub-card"
            :bordered="true"
            title="参赛者名单（竞赛维度）"
            style="margin-top: 16px"
          >
            <div class="row">
              <a-button
                :loading="participantsIndividualLoading"
                @click="refreshParticipantsIndividual"
                :disabled="!activeCompetitionId"
                type="primary"
              >
                查看个人参赛者
              </a-button>
              <a-button
                style="margin-left: 8px"
                :loading="participantsTeamsLoading"
                @click="refreshParticipantsTeams"
                :disabled="!activeCompetitionId"
              >
                查看组队参赛者
              </a-button>
              <a-button
                v-if="canManageCompetitions"
                style="margin-left: 8px"
                type="primary"
                :loading="participantsTeamsExportLoading"
                @click="exportTeamsExcel"
                :disabled="!activeCompetitionId"
              >
                导出队伍 Excel
              </a-button>
            </div>
          </a-card>

          <a-card
            v-if="canViewScoreAnalytics"
            size="small"
            class="sub-card"
            :bordered="true"
            title="评分汇总/排行榜"
            style="margin-top: 16px"
          >
            <div class="row">
              <a-button :loading="summaryLoading" @click="refreshScoresSummary" :disabled="!activeCompetitionId">
                查看评分汇总
              </a-button>
              <a-button :loading="rankingsLoading" @click="openRankingsModal" :disabled="!activeCompetitionId">
                查看排行榜
              </a-button>
            </div>
          </a-card>
        </div>

        <a-empty
          v-if="!isStudent && !showAdvisorTeamPanel && !isCompetitionWorkbench && !showExpertNotAssignedHint"
          style="margin-top: 16px"
          :description="roleNoPermissionDescription"
        />
      </div>

    </a-card>

    <!-- 独立详情页：报名与组队（报名成功后同窗展示作品提交） -->
    <a-modal
      v-model="showStandaloneEnrollModal"
      title="报名与组队"
      :width="760"
      :footer="null"
      :destroyOnClose="false"
      wrap-class-name="standalone-competition-modal-wrap"
      @cancel="showStandaloneEnrollModal = false"
    >
      <div class="standalone-modal-scroll">
        <a-alert
          v-if="competitionEnrollPublishBlocked"
          type="warning"
          show-icon
          :message="competitionEnrollBlockedAlertTitle"
          :description="competitionEnrollBlockedAlertDescription"
          style="margin-bottom: 12px"
        />
        <a-form layout="inline" :style="{ marginBottom: '12px' }">
          <a-form-item label="参赛方式">
            <a-radio-group v-model="enrollMode">
              <a-radio-button value="individual" :disabled="!allowIndividual">个人参赛</a-radio-button>
              <a-radio-button value="team" :disabled="!allowTeam">队伍参赛</a-radio-button>
            </a-radio-group>
          </a-form-item>
        </a-form>
        
        <a-form layout="vertical" class="enroll-profile-form" style="margin-top: 4px; max-width: 640px">
          
          <a-row :gutter="12">
            <a-col :xs="24" :sm="12">
              <a-form-item label="学号" :colon="false">
                <a-input
                  v-model="enrollProfileForm.student_no"
                  placeholder="选填"
                  :allow-clear="!enrollProfileLockedAfterSuccess"
                  :disabled="enrollProfileLockedAfterSuccess"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12">
              <a-form-item label="姓名" :colon="false">
                <a-input
                  v-model="enrollProfileForm.real_name"
                  placeholder="选填"
                  :allow-clear="!enrollProfileLockedAfterSuccess"
                  :disabled="enrollProfileLockedAfterSuccess"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12">
              <a-form-item label="学院" :colon="false">
                <a-input
                  v-model="enrollProfileForm.college"
                  placeholder="选填"
                  :allow-clear="!enrollProfileLockedAfterSuccess"
                  :disabled="enrollProfileLockedAfterSuccess"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12">
              <a-form-item label="年级" :colon="false">
                <a-input
                  v-model="enrollProfileForm.grade"
                  placeholder="如 2023级，选填"
                  :allow-clear="!enrollProfileLockedAfterSuccess"
                  :disabled="enrollProfileLockedAfterSuccess"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12">
              <a-form-item label="联系方式" :colon="false">
                <a-input
                  v-model="enrollProfileForm.contact"
                  placeholder="手机或邮箱，选填"
                  :allow-clear="!enrollProfileLockedAfterSuccess"
                  :disabled="enrollProfileLockedAfterSuccess"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>

        <div v-if="enrollMode === 'team'" class="muted" style="margin-bottom: 12px; font-size: 13px">
          <template v-if="studentTeamEnrolledAsMember">
            您已完成队伍赛道报名（队员身份）。队伍由队长统一管理，无需创建/加入队伍或进行队长操作。
          </template>
          <template v-else>
            队伍参赛流程：① 创建队伍 <strong>或</strong> 加入已有队伍 → ② 获得「我的队伍ID」后 → ③ 若后端未自动报名，再点击「报名（队伍）」。（部分接口在创建队伍时已自动完成竞赛报名，此时无需再点报名。）
          </template>
        </div>

        <div class="row">
          <a-button
            type="primary"
            :loading="enrollLoading"
            @click="handleEnrollIndividual"
            v-if="enrollMode === 'individual'"
            :disabled="competitionEnrollPublishBlocked || !allowIndividual || myEnrolledIndividual"
          >
            {{ myEnrolledIndividual ? '个人已报名' : '报名个人' }}
          </a-button>

          <template v-else>
            <a-button
              v-if="showStudentTeamCreateJoinOps"
              type="primary"
              :loading="enrollLoading"
              @click="handleCreateTeamOnly"
              :disabled="competitionEnrollPublishBlocked || !allowTeam || studentHasTeamForCurrentCompetition"
              style="margin-right: 8px"
            >
              创建队伍（自动队长）
            </a-button>
            <a-button
              type="primary"
              :loading="enrollLoading"
              @click="handleEnrollWithTeam"
              :disabled="competitionEnrollPublishBlocked || !allowTeam || myEnrolledTeam || !teamEnrollmentEligible || !myTeamId || teamEnrollActionBlockedForMember"
            >
              {{ myEnrolledTeam ? '队伍已报名' : '报名（队伍）' }}
            </a-button>
          </template>

        </div>
        <p v-if="enrollMode === 'team' && teamEnrollActionBlockedForMember" class="muted" style="margin: 8px 0 0; font-size: 13px">
          您已完成队伍报名且为队员，无需重复报名；创建队伍、加入队伍等操作已由队长负责。
        </p>

        <div v-if="enrollMode === 'team'" style="margin-top: 12px">
          <a-form layout="vertical">
            <a-form-item label="我的队伍ID（创建或加入成功后自动填入）">
              <a-input-number
                v-model="myTeamId"
                :min="1"
                placeholder="请先创建队伍或加入队伍"
                style="width: 240px"
                :disabled="true"
              />
            </a-form-item>
            <a-form-item v-if="showStudentTeamCreateJoinOps" label="加入已有队伍（输入队长提供的队伍ID）">
              <div class="row">
                <a-input-number
                  v-model="joinTeamId"
                  :min="1"
                  placeholder="请输入队伍ID"
                  style="width: 180px"
                  :disabled="competitionEnrollPublishBlocked || studentHasTeamForCurrentCompetition"
                />
                <a-button
                  :loading="teamLoading"
                  :disabled="competitionEnrollPublishBlocked || studentHasTeamForCurrentCompetition"
                  @click="handleJoinTeam"
                >
                  加入队伍
                </a-button>
              </div>
            </a-form-item>
          </a-form>

          <template v-if="showStudentTeamCaptainOptionalOps">
          <a-divider />
          <a-form layout="vertical">
            <a-form-item label="队长转让（可选）">
              <div class="row">
                <a-input-number v-model="transferTeamId" :min="1" placeholder="队伍ID" style="width: 180px" />
                <a-input-number
                  v-model="newCaptainId"
                  :min="1"
                  placeholder="新队长用户ID"
                  style="width: 180px"
                />
                <a-button
                  :loading="teamLoading"
                  @click="handleTransferCaptain"
                  :disabled="!transferTeamId || !newCaptainId"
                >
                  转让
                </a-button>
              </div>
            </a-form-item>
            <a-form-item label="队长退队（可选，强制先转让）">
              <div class="row">
                <a-input-number v-model="leaveTeamId" :min="1" placeholder="队伍ID" style="width: 180px" />
                <a-button
                  danger
                  :loading="teamLoading"
                  @click="handleLeaveTeam"
                  :disabled="!leaveTeamId"
                >
                  退队
                </a-button>
              </div>
            </a-form-item>
            <template v-if="isCurrentTeamCaptain">
              <a-form-item label="邀请队员（队长）">
                <div class="row">
                  <a-input-number
                    v-model="studentTeamInviteId"
                    :min="1"
                    placeholder="学生用户ID（alt_auth_users.id）"
                    style="width: 220px"
                    :disabled="competitionTeamCreateInviteBlocked"
                  />
                  <a-button
                    type="primary"
                    :loading="teamLoading"
                    :disabled="competitionTeamCreateInviteBlocked || !studentTeamInviteId || !myTeamId"
                    @click="handleStudentTeamInviteMember"
                  >
                    邀请队员
                  </a-button>
                </div>
              </a-form-item>
              <a-form-item label="移除队员（队长）">
                <div class="row">
                  <a-input-number
                    v-model="studentTeamRemoveMemberId"
                    :min="1"
                    placeholder="待移除队员用户ID"
                    style="width: 220px"
                    :disabled="competitionTeamRemoveMemberBlocked"
                  />
                  <a-button
                    danger
                    :loading="teamLoading"
                    :disabled="competitionTeamRemoveMemberBlocked || !studentTeamRemoveMemberId || !myTeamId"
                    @click="handleStudentTeamRemoveMember"
                  >
                    移除队员
                  </a-button>
                </div>
              </a-form-item>
            </template>
          </a-form>
          </template>
        </div>

        <template v-if="hasAnyEnrollment && showSubmissionPanelInEnrollView">
          <a-divider />
          <h4 class="standalone-modal-section-title">作品提交</h4>
          <p v-if="enrollModalSubmissionLocked" class="muted" style="margin: 0 0 12px; font-size: 13px">
            当前{{ submissionMode === 'team' ? '队伍' : '个人' }}赛道在本报名周期已提交作品，无法再次提交。退赛后重新报名须提交新作品；可在「作品」弹窗查看历史记录。
          </p>
          <p v-else-if="ignoreSubmissionsBeforeReenrollAt" class="muted" style="margin: 0 0 12px; font-size: 13px">
            您已退赛，请完成报名后重新提交作品。
          </p>
          <a-form layout="vertical">
            <a-form-item label="作品标题" required>
              <a-input
                v-model="submissionForm.title"
                placeholder="请输入作品标题"
                style="max-width: 520px"
                :disabled="enrollModalSubmissionLocked"
              />
            </a-form-item>
            <a-form-item label="作品描述">
              <a-textarea
                v-model="submissionForm.description"
                :rows="3"
                placeholder="选填"
                style="max-width: 520px"
                :disabled="enrollModalSubmissionLocked"
              />
            </a-form-item>
            <a-form-item label="文本内容（选填，与文件二选一至少一个）">
              <a-textarea
                v-model="submissionForm.content_text"
                :rows="4"
                placeholder="选填"
                style="max-width: 520px"
                :disabled="enrollModalSubmissionLocked"
              />
            </a-form-item>
            <a-form-item label="文件（选填，支持上传；与文本至少一个）">
              <input type="file" :disabled="enrollModalSubmissionLocked" @change="handleFileChange" />
              <div v-if="submissionForm.file" class="muted" style="margin-top: 6px">
                已选择：{{ submissionForm.file.name }}
              </div>
            </a-form-item>

            <a-form-item label="提交类型">
              <a-radio-group
                v-model="submissionMode"
                :disabled="enrollModalSubmissionLocked"
                @change="onSubmissionModeChange"
              >
                <a-radio-button value="individual" :disabled="!myEnrolledIndividual || !allowIndividual">个人提交</a-radio-button>
                <a-radio-button value="team" :disabled="!myEnrolledTeam || !allowTeam || !isCurrentTeamCaptain">队伍提交</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <div class="row">
              <a-button
                type="primary"
                :loading="submitLoading"
                :disabled="enrollModalSubmissionLocked"
                @click="handleSubmitSubmission"
              >
                提交作品
              </a-button>
            </div>
          </a-form>
        </template>
        <a-alert
          v-else-if="myEnrolledTeam && enrollMode === 'team' && !isCurrentTeamCaptain"
          type="info"
          show-icon
          message="当前账号为队员，只有队长可以提交队伍作品"
          style="margin-top: 12px"
        />

        <div class="standalone-modal-footer-actions">
          <a-button @click="showStandaloneEnrollModal = false">关闭</a-button>
        </div>
      </div>
    </a-modal>

    <!-- 独立详情页：我的作品 -->
    <a-modal
      v-model="showStandaloneMyWorksModal"
      title="我的作品"
      :width="900"
      :footer="null"
      wrap-class-name="standalone-competition-modal-wrap"
      @cancel="showStandaloneMyWorksModal = false"
    >
      <div class="standalone-modal-scroll">
        <div class="row" style="margin-bottom: 12px; flex-wrap: wrap; gap: 8px">
          <a-button @click="refreshMySubmissions" :loading="submissionsLoading">
            刷新我的作品
          </a-button>
          <a-button @click="refreshMyScores(true)" :loading="scoresLoading">
            查看我的成绩
          </a-button>
        </div>
        <a-empty v-if="mySubmissions.length === 0" description="暂无作品，请先报名并提交" />
        <div v-else class="submissions-list">
          <a-card
            v-for="s in mySubmissions"
            :key="'standalone-' + s.id"
            size="small"
            class="submission-item"
            :bordered="false"
          >
            <div class="submission-title-row">
              <div class="submission-title">{{ s.title || '-' }}</div>
              <a-tag :color="getSubmissionStatusColor(s.status)">
                {{ getSubmissionStatusText(s.status) }}
              </a-tag>
            </div>
            <div class="muted" style="margin-top: 6px">
              提交时间：{{ formatDateTime(s.submitted_at) }}
            </div>
            <div class="row" style="margin-top: 10px">
              <a-button size="small" :disabled="!s.id" @click="downloadSubmission(s.id)">
                下载文件
              </a-button>
            </div>
          </a-card>
        </div>
        <div class="standalone-modal-footer-actions">
          <a-button @click="showStandaloneMyWorksModal = false">关闭</a-button>
        </div>
      </div>
    </a-modal>

    <!-- 创建竞赛弹窗（教师/管理员） -->
    <a-modal
      v-model="showCreateCompetitionModal"
      title="创建竞赛"
      :maskClosable="false"
      :confirmLoading="adminCreateLoading"
      okText="创建"
      cancelText="取消"
      @ok="handleCreateCompetition"
    >
      <a-form layout="vertical">
        <a-form-item label="竞赛名称" required>
          <a-input v-model="createCompetitionForm.name" placeholder="请输入竞赛名称" />
        </a-form-item>
        <a-form-item label="简介" required>
          <a-input v-model="createCompetitionForm.description" placeholder="必填" />
        </a-form-item>
        <a-form-item label="规则说明" required>
          <a-textarea v-model="createCompetitionForm.rules_text" :rows="4" placeholder="必填" />
        </a-form-item>
        <a-form-item
          label="竞赛二维码"
          required
          extra="必填；png / jpeg / gif / webp，单张不超过 5MB。将检测图片中是否包含可读二维码。"
        >
          <a-upload
            list-type="picture-card"
            class="create-competition-qr-upload"
            accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
            :file-list="qrCodeFileList"
            :before-upload="beforeQrCodeUpload"
            :disabled="qrCodeValidating"
            :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
            @remove="handleQrCodeRemove"
          >
            <div v-if="qrCodeFileList.length < 1">
              <a-icon :type="qrCodeValidating ? 'loading' : 'plus'" />
              <div class="ant-upload-text">{{ qrCodeValidating ? '校验中…' : '上传二维码' }}</div>
            </div>
          </a-upload>
        </a-form-item>
        <a-form-item label="开始时间">
          <a-input type="datetime-local" v-model="createCompetitionForm.start_at" />
        </a-form-item>
        <a-form-item label="结束时间">
          <a-input type="datetime-local" v-model="createCompetitionForm.end_at" />
        </a-form-item>
        <a-form-item label="参赛方式">
          <a-checkbox v-model="createCompetitionForm.allow_individual">允许个人参赛</a-checkbox>
          <a-checkbox v-model="createCompetitionForm.allow_team" style="margin-left: 12px">允许团队参赛</a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 修改竞赛弹窗（竞赛列表 §8.3） -->
    <a-modal
      v-model="showEditCompetitionModal"
      title="修改竞赛"
      :maskClosable="false"
      :confirmLoading="adminEditLoading"
      okText="保存"
      cancelText="取消"
      @ok="handleEditCompetition"
      @cancel="resetEditCompetitionQrState"
    >
      <a-form layout="vertical">
        <a-alert
          type="info"
          show-icon
          message="仅提交有变化的文本字段；不上传新二维码则保留当前二维码。"
          style="margin-bottom: 16px"
        />
        <a-form-item label="竞赛ID">
          <a-input-number v-model="editCompetitionId" :disabled="true" style="width: 240px" />
        </a-form-item>

        <a-form-item label="竞赛名称">
          <a-input v-model="editCompetitionForm.name" placeholder="修改后保存；与当前一致则不提交" />
        </a-form-item>

        <a-form-item label="简介">
          <a-input v-model="editCompetitionForm.description" placeholder="修改后保存；与当前一致则不提交" />
        </a-form-item>

        <a-form-item label="规则说明">
          <a-textarea v-model="editCompetitionForm.rules_text" :rows="4" placeholder="修改后保存；与当前一致则不提交" />
        </a-form-item>

        <a-form-item
          label="竞赛二维码"
          extra="上传新图将替换当前二维码。png / jpeg / gif / webp，单张不超过 5MB，须包含可识别二维码（与创建竞赛相同校验）。"
        >
          <a-spin :spinning="editCurrentQrLoading" size="small">
            <div v-if="editCurrentQrObjectUrl" class="edit-competition-current-qr">
              <div class="edit-competition-qr-label">当前竞赛二维码</div>
              <img :src="editCurrentQrObjectUrl" alt="当前竞赛二维码" class="edit-competition-current-qr__img" />
            </div>
            <div v-else-if="!editCurrentQrLoading" class="muted edit-competition-qr-empty">暂无二维码图片</div>
          </a-spin>
          <div class="edit-competition-qr-replace">
            <div class="edit-competition-qr-label">上传新二维码（选填）</div>
            <a-upload
              list-type="picture-card"
              class="create-competition-qr-upload"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
              :file-list="editQrCodeFileList"
              :before-upload="beforeEditQrCodeUpload"
              :disabled="editQrCodeValidating"
              :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
              @remove="handleEditQrCodeRemove"
            >
              <div v-if="editQrCodeFileList.length < 1">
                <a-icon :type="editQrCodeValidating ? 'loading' : 'plus'" />
                <div class="ant-upload-text">{{ editQrCodeValidating ? '校验中…' : '选择图片' }}</div>
              </div>
            </a-upload>
          </div>
        </a-form-item>

        <a-form-item label="开始时间">
          <a-input type="datetime-local" v-model="editCompetitionForm.start_at" />
        </a-form-item>

        <a-form-item label="结束时间">
          <a-input type="datetime-local" v-model="editCompetitionForm.end_at" />
        </a-form-item>

        <a-form-item label="参赛方式">
          <a-checkbox v-model="editCompetitionForm.allow_individual">允许个人参赛</a-checkbox>
          <a-checkbox v-model="editCompetitionForm.allow_team" style="margin-left: 12px">允许团队参赛</a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 我的成绩弹窗（学生）GET /v1/competitions/{id}/scores/me：competition_id + submissions[] -->
    <a-modal
      v-model="showMyScoresModal"
      title="我的成绩"
      :maskClosable="false"
      :footer="null"
      width="90%"
    >
      <a-empty
        v-if="myScores == null || !Array.isArray(myScores.submissions) || myScores.submissions.length === 0"
        description="暂无提交记录"
      />
      <div v-else>
        <div class="muted" style="margin-bottom: 10px">
          竞赛ID：{{ myScores.competition_id != null ? myScores.competition_id : '-' }}
          <span style="margin-left: 12px">共 {{ myScores.submissions.length }} 条提交</span>
        </div>
        <a-table
          :columns="myScoresTableColumns"
          :data-source="myScoresTableData"
          :pagination="{ pageSize: 10 }"
          size="small"
          bordered
          row-key="id"
        />
      </div>
    </a-modal>

    <!-- 评分汇总弹窗（表格） -->
    <a-modal
      v-model="showScoresSummaryModal"
      title="评分汇总"
      :maskClosable="false"
      :footer="null"
      width="560px"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <a-empty v-if="scoresSummary == null" description="暂无评分汇总数据" />
      <a-table
        v-else
        :columns="summaryTableColumns"
        :data-source="summaryTableData"
        :pagination="false"
        size="small"
        bordered
      />
    </a-modal>

    <!-- 排行榜弹窗（表格） -->
    <a-modal
      v-model="showScoresRankingsModal"
      title="排行榜"
      :maskClosable="false"
      :footer="null"
      width="90%"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <div class="row" style="margin-bottom: 16px">
        <span>显示条数：</span>
        <a-input-number v-model="rankingsLimit" :min="1" :max="200" style="width: 120px" />
        <a-button type="primary" :loading="rankingsLoading" :disabled="!activeCompetitionId" @click="refreshRankings">
          查询
        </a-button>
      </div>
      <a-empty v-if="scoresRankings == null || !rankingsTableData.length" description="暂无排行榜数据" />
      <a-table
        v-else
        :columns="rankingsTableColumns"
        :data-source="rankingsTableData"
        :pagination="{ pageSize: 10 }"
        size="small"
        bordered
        row-key="rowIndex"
      />
    </a-modal>

    <!-- 个人参赛者弹窗（管理员） -->
    <a-modal
      v-model="showParticipantsIndividualModal"
      title="个人参赛者名单"
      :maskClosable="false"
      :footer="null"
      width="90%"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <a-empty v-if="!participantsIndividual || !participantsIndividual.length" description="暂无个人参赛者数据" />
      <a-table
        v-else
        :columns="participantsIndividualTableColumns"
        :data-source="participantsIndividual"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
        row-key="enrollment_id"
        size="small"
        bordered
      />
    </a-modal>

    <!-- 组队参赛者弹窗（管理员） -->
    <a-modal
      v-model="showParticipantsTeamsModal"
      title="组队参赛者名单"
      :maskClosable="false"
      :footer="null"
      width="90%"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <a-empty v-if="!participantsTeams || !participantsTeams.length" description="暂无组队参赛者数据" />
      <a-table
        v-else
        :columns="participantsTeamsTableColumns"
        :data-source="participantsTeams"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
        row-key="team_id"
        size="small"
        bordered
      />
    </a-modal>
  </div>
</template>

<script>
import {
  getCompetitions,
  createCompetitionMultipart,
  publishCompetition,
  updateCompetition,
  updateCompetitionMultipart,
  deleteCompetition,
  lockCompetition,
  getCompetitionParticipantsIndividual,
  getCompetitionParticipantsTeams,
  exportCompetitionTeamsExcel,
  enrollCompetition,
  getCompetitionTeams,
  createCompetitionTeam,
  patchCompetitionTeam,
  inviteCompetitionTeamMember,
  removeCompetitionTeamMember,
  addTeamMember,
  transferTeamCaptain,
  leaveTeam,
  submitCompetitionSubmission,
  uploadCompetitionSubmission,
  getCompetitionSubmissions,
  getCompetitionSubmission,
  downloadCompetitionSubmissionFile,
  reviewCompetitionSubmissionGrade,
  patchCompetitionSubmissionReviewGrade,
  getCompetitionSubmissionReviewGrade,
  getCompetitionScoresSummary,
  getCompetitionRankings,
  getMyCompetitionScores,
  getMyCompetitionEnrollments,
  getCompetitionQrCode,
  withdrawCompetition
} from '@/api/competition'
import { validateImageContainsQrCode } from '@/utils/qrImageValidate'
import {
  markCompetitionWithdrawnForResubmit,
  getCompetitionWithdrawSubmissionCutoff,
  clearCompetitionWithdrawSubmissionCutoff,
  isWithdrawnOrSupersededSubmission as isWithdrawnSubmissionRow,
  buildEnrollmentVisibilityIndex,
  splitEnrollmentsByTrack,
  filterAdminSubmissionsByActiveEnrollments,
  filterSubmissionsForEnrollmentTrack,
  normalizeCompetitionApiList,
  saveSubmissionReviewGradeCache,
  getSubmissionReviewGradeCache
} from '@/utils/competitionSubmissionCycle'
import {
  getStoredAltToken,
  isAltCompetitionStudent,
  isAltCompetitionSuperAdmin,
  isAltCompetitionAdvisorOrTeacher,
  isAltCompetitionExpertVerified,
  isAltCompetitionExpert,
  isAltExpertAssignedToCompetition,
  hasAltPermission,
  getAltProfileFromStorage,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage
} from '@/api/altIdentity'

export default {
  name: 'CompetitionRegistrationSystem',
  props: {
    /** 新标签页仅展示详情：隐藏列表与顶部工具栏 */
    standaloneDetailMode: {
      type: Boolean,
      default: false
    },
    /** 与 standaloneDetailMode 配合：进入后拉列表并选中该竞赛 */
    initialCompetitionId: {
      type: [Number, String],
      default: null
    }
  },
  data () {
    return {
      keyword: '',
      competitions: [],
      competitionsLoading: false,
      competitionsError: '',

      competitionListPagination: {
        pageSize: 10,
        showSizeChanger: true,
        showQuickJumper: true,
        pageSizeOptions: ['10', '20', '50'],
        showTotal: (total) => `共 ${total} 条`
      },

      selectedCompetitionId: null,
      manualCompetitionId: null,

      enrollMode: 'individual', // 'individual' | 'team'
      myTeamId: null,

      /** POST /v1/competitions/enroll 选填扩展字段（8.7） */
      enrollProfileForm: {
        student_no: '',
        real_name: '',
        college: '',
        grade: '',
        contact: ''
      },

      joinTeamId: null,
      studentTeamInviteId: null,
      studentTeamRemoveMemberId: null,
      transferTeamId: null,
      newCaptainId: null,
      leaveTeamId: null,

      enrollLoading: false,
      teamLoading: false,
      /** 仅在本竞赛下完成「创建队伍」或「加入队伍」后为 true，才允许「报名（队伍）」 */
      teamEnrollmentEligible: false,
      /** 学生端：当前竞赛内已成功创建过队伍（用于展示队长操作区） */
      studentCreatedTeamInCurrentCompetition: false,
      /** 当前 UI 赛道（个人/队伍），与 enrollMode 一致，用于作品提交上下文 */
      activeCompetitionMyEnrollKind: null,
      /** 当前赛道对应报名记录 ID（随 enrollMode 切换） */
      activeCompetitionEnrollmentId: null,
      /** 本竞赛是否已个人报名 / 已队伍报名（可同时为 true） */
      myEnrolledIndividual: false,
      myEnrolledTeam: false,
      activeCompetitionEnrollmentRows: { individual: null, team: null },
      /** 退赛后忽略此前作品的时间戳（接口未带 enrollment_id 时用于区分旧作品） */
      ignoreSubmissionsBeforeReenrollAt: null,
      withdrawLoading: false,

      /** 指导老师：组班与队务（§8.12.x） */
      advisorTeamsLoading: false,
      advisorTeams: [],
      advisorSelectedTeamId: null,
      advisorCreateLoading: false,
      advisorTeamOpLoading: false,
      advisorRemovingUserId: null,
      advisorCreateForm: {
        name: '',
        captain_student_id: null,
        initial_member_ids_text: ''
      },
      advisorRenameName: '',
      advisorInviteStudentId: null,
      /** 本会话内由当前老师创建的队伍 ID（列表未带 created_by_advisor_id 时仍可管理） */
      advisorCreatedTeamIds: [],

      submissionMode: 'individual',
      submissionForm: {
        title: '',
        description: '',
        content_text: '',
        file: null
      },
      submissionTeamId: null,
      submitLoading: false,

      submissionsLoading: false,
      mySubmissions: [],
      scoresLoading: false,
      myScores: null,
      showMyScoresModal: false,
      /** 竞赛详情独立页：顶部「报名」「作品」打开的弹窗 */
      showStandaloneEnrollModal: false,
      showStandaloneMyWorksModal: false,

      /** 学生独立详情「赛题说明」侧栏二维码（Blob URL，须 beforeDestroy revoke） */
      studentBriefingQrObjectUrl: null,

      // 教师/管理员
      adminCreateLoading: false,
      showCreateCompetitionModal: false,
      createCompetitionForm: {
        name: '',
        description: '',
        rules_text: '',
        start_at: '',
        end_at: '',
        allow_individual: true,
        allow_team: true
      },
      createCompetitionQrFile: null,
      qrCodeFileList: [],
      qrCodeValidating: false,
      createQrBlobUrl: null,
      publishCompetitionId: null,
      publishLoading: false,

      // 管理员：编辑/删除/锁定竞赛
      adminEditLoading: false,
      showEditCompetitionModal: false,
      editCompetitionId: null,
      editCompetitionForm: {
        name: '',
        description: '',
        rules_text: '',
        start_at: '',
        end_at: '',
        allow_individual: false,
        allow_team: false
      },
      editCompetitionOriginal: null,
      editCompetitionQrFile: null,
      editQrCodeFileList: [],
      editQrCodeValidating: false,
      editQrBlobUrl: null,
      editCurrentQrObjectUrl: null,
      editCurrentQrLoading: false,

      adminDeleteLoading: false,
      adminLockLoading: false,

      // 管理员：参赛者名单（个人/队伍）
      participantsIndividualLoading: false,
      participantsIndividual: [],
      showParticipantsIndividualModal: false,

      participantsTeamsLoading: false,
      participantsTeamsExportLoading: false,
      participantsTeams: [],
      showParticipantsTeamsModal: false,

      participantsIndividualTableColumns: [
        { title: '序号', dataIndex: 'sequence_no', key: 'sequence_no', width: 80 },
        { title: '报名ID', dataIndex: 'enrollment_id', key: 'enrollment_id', width: 110 },
        { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 120 },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 110, ellipsis: true },
        { title: '学院', dataIndex: 'college', key: 'college', ellipsis: true },
        { title: '年级', dataIndex: 'grade', key: 'grade', width: 90 },
        { title: '联系方式', dataIndex: 'contact', key: 'contact', width: 120 },
        { title: '报名状态', dataIndex: 'status_text', key: 'status_text', width: 100 },
        { title: '报名时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
      ],

      participantsTeamsTableColumns: [
        { title: '队伍序号', dataIndex: 'sequence_no', key: 'sequence_no', width: 100 },
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 90 },
        { title: '队长', dataIndex: 'captain_name', key: 'captain_name', width: 140, ellipsis: true },
        { title: '成员', dataIndex: 'members_summary', key: 'members_summary', ellipsis: true },
        { title: '队伍状态', dataIndex: 'status_text', key: 'status_text', width: 110 },
        { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
      ],

      gradeForm: {
        submission_id: null,
        score: '',
        feedback: ''
      },
      /** 教师：仅在点击作品列表的“评分/修改评分”后显示表单 */
      showGradeAudit: false,
      gradeFormIsEdit: false,
      gradeLoading: false,

      adminSubmissionsLoading: false,
      adminSubmissions: [],
      /** 因退赛/非当前报名周期而从教师作品列表中隐藏的数量 */
      adminSubmissionsHiddenByWithdrawCount: 0,

      summaryLoading: false,
      scoresSummary: null,
      showScoresSummaryModal: false,

      rankingsLimit: 50,
      rankingsLoading: false,
      scoresRankings: null,
      showScoresRankingsModal: false,

      summaryTableColumns: [
        { title: '指标', dataIndex: 'label', key: 'label', width: 160 },
        { title: '数值', dataIndex: 'value', key: 'value' }
      ],
      rankingsTableColumns: [
        { title: '排名', dataIndex: 'rowIndex', key: 'rowIndex', width: 80 },
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', ellipsis: true },
        { title: '学生ID', dataIndex: 'student_id', key: 'student_id', ellipsis: true },
        { title: '分数', dataIndex: 'best_score', key: 'best_score', width: 100 },
        { title: '已评提交数', dataIndex: 'reviewed_submissions', key: 'reviewed_submissions', width: 120 }
      ],
      myScoresTableColumns: [
        { title: '竞赛ID', dataIndex: 'competition_id', key: 'competition_id', width: 80 },
        { title: '作品标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 220 },
        { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
        { title: '成绩', dataIndex: 'score', key: 'score', width: 88 },
        { title: '提交人ID', dataIndex: 'submitter_id', key: 'submitter_id', width: 96 },
        { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', width: 168 }
      ],
      advisorTeamsTableColumns: [
        { title: '队伍ID', dataIndex: 'id', key: 'id', width: 88 },
        { title: '队名', dataIndex: 'name', key: 'name', ellipsis: true },
        { title: '队长ID', dataIndex: 'captain_id', key: 'captain_id', width: 96 },
        { title: '队员数', dataIndex: 'member_count', key: 'member_count', width: 80 },
        { title: '状态', dataIndex: 'status_text', key: 'status_text', width: 96 },
        { title: '可管理', dataIndex: 'can_operate_text', key: 'can_operate_text', width: 88 },
        { title: '操作', key: 'actions', width: 88, scopedSlots: { customRender: 'teamActions' } }
      ]
    }
  },
  computed: {
    isUsingAltIdentity () {
      return !!getStoredAltToken()
    },
    isStudent () {
      if (this.isUsingAltIdentity) return isAltCompetitionStudent()
      const roles = this.$store.getters.roles || []
      return roles.includes('student')
    },
    isSuperAdmin () {
      if (this.isUsingAltIdentity) return isAltCompetitionSuperAdmin()
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    isAdvisorOrTeacher () {
      if (this.isUsingAltIdentity) return isAltCompetitionAdvisorOrTeacher()
      const roles = this.$store.getters.roles || []
      return roles.includes('advisor') || roles.includes('teacher')
    },
    altCurrentUserId () {
      if (!this.isUsingAltIdentity) return null
      const p = getAltProfileFromStorage()
      const id = p.user_id != null ? p.user_id : p.id
      return id != null && Number.isFinite(Number(id)) ? Number(id) : null
    },
    /** 竞赛列表顶栏：学生账号 ID（alt_auth_users.id） */
    studentAccountIdLabel () {
      if (!this.isStudent) return ''
      if (this.isUsingAltIdentity) {
        const id = this.altCurrentUserId
        return id != null ? String(id) : ''
      }
      const user = this.$store.getters.userInfo || {}
      const id = user.id != null ? user.id : user.user_id
      return id != null && String(id).trim() !== '' ? String(id) : ''
    },
    canManageTeams () {
      if (this.isUsingAltIdentity) return hasAltPermission('MANAGE_TEAMS')
      const roles = this.$store.getters.roles || []
      return roles.includes('student') || roles.includes('advisor') || roles.includes('teacher')
    },
    showAdvisorTeamPanel () {
      return this.isAdvisorOrTeacher && this.canManageTeams
    },
    isCompetitionExpert () {
      return this.isUsingAltIdentity && isAltCompetitionExpert()
    },
    isVerifiedExpert () {
      if (this.isUsingAltIdentity) return isAltCompetitionExpertVerified()
      return false
    },
    isExpertAssignedToActiveCompetition () {
      if (!this.isVerifiedExpert) return false
      const cid = this.activeCompetitionId
      if (cid == null || cid === undefined || cid === '') return false
      return isAltExpertAssignedToCompetition(cid)
    },
    showExpertNotAssignedHint () {
      return (
        this.isCompetitionExpert &&
        this.isVerifiedExpert &&
        this.showCompetitionDetailPanel &&
        !this.isExpertAssignedToActiveCompetition &&
        !this.isSuperAdmin
      )
    },
    roleNoPermissionDescription () {
      if (this.showExpertNotAssignedHint) {
        return '您未被指派到本竞赛，无法查看作品、评分或排行榜。请在竞赛列表中打开已指派的竞赛详情。'
      }
      if (this.isCompetitionExpert && !this.isVerifiedExpert) {
        return '专家账号待管理员核验，核验并指派竞赛后方可评阅。'
      }
      return '当前角色暂无竞赛报名/管理权限'
    },
    canManageCompetitions () {
      if (this.isUsingAltIdentity) {
        return this.isSuperAdmin || hasAltPermission('MANAGE_COMPETITIONS')
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    canViewCompetitionSubmissions () {
      if (this.isUsingAltIdentity) {
        if (this.isSuperAdmin) return true
        return this.isExpertAssignedToActiveCompetition
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    canReviewSubmissions () {
      if (this.isUsingAltIdentity) {
        return (
          this.isExpertAssignedToActiveCompetition &&
          hasAltPermission('REVIEW_SUBMISSIONS')
        )
      }
      return false
    },
    canViewParticipantsRoster () {
      if (this.isUsingAltIdentity) {
        return this.isSuperAdmin
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    canViewScoreAnalytics () {
      if (this.isUsingAltIdentity) {
        if (this.isSuperAdmin) return true
        return this.isExpertAssignedToActiveCompetition
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    isCompetitionWorkbench () {
      return this.canManageCompetitions || this.canViewCompetitionSubmissions || this.canViewParticipantsRoster || this.canViewScoreAnalytics
    },
    competitionListColumns () {
      return [
        { title: 'ID', dataIndex: 'id', key: 'id', width: 72 },
        { title: '竞赛名称', dataIndex: 'name', key: 'name', ellipsis: true, width: 200 },
        { title: '状态', dataIndex: 'status', key: 'status', width: 104, scopedSlots: { customRender: 'status' } },
        { title: '简介', dataIndex: 'summary', key: 'summary', ellipsis: true },
        { title: '开始时间', dataIndex: 'start_at', key: 'start_at', width: 120 },
        { title: '结束时间', dataIndex: 'end_at', key: 'end_at', width: 120 },
        { title: '参赛方式', dataIndex: 'modes', key: 'modes', width: 168 },
        { title: '操作', key: 'actions', width: 100, fixed: 'right', scopedSlots: { customRender: 'listActions' } }
      ]
    },
    competitionListTableData () {
      return this.filteredCompetitions.map(c => {
        const raw = (c.description || c.rules_text || '').trim()
        const summary = raw ? (raw.length > 80 ? raw.slice(0, 80) + '…' : raw) : '-'
        return {
          id: c.id,
          name: c.name || '-',
          status: c.status,
          summary,
          start_at: this.formatDate(c.start_at),
          end_at: this.formatDate(c.end_at),
          modes: `个人: ${c.allow_individual ? '是' : '否'} / 团队: ${c.allow_team ? '是' : '否'}`
        }
      })
    },
    /** 教师/管理员：selectedRowKeys 由 selectedCompetitionId 推导，避免 Table 与本地 state 双写不同步导致下方详情不刷新 */
    competitionListRowSelection () {
      if (!this.canManageCompetitions) return undefined
      const rk = this.resolveCompetitionRowKey(this.selectedCompetitionId)
      const selectedRowKeys =
        rk !== null && rk !== undefined && rk !== '' ? [rk] : []
      return {
        type: 'checkbox',
        selectedRowKeys: selectedRowKeys.slice(),
        onChange: (keys) => {
          this.onAdminCompetitionTableSelectChange(keys)
        }
      }
    },
    /** 勿用 selectedCompetitionId || manualId，避免合法 id 为 0 时被吞掉 */
    activeCompetitionId () {
      const s = this.selectedCompetitionId
      if (s !== null && s !== undefined && s !== '') return s
      const m = this.manualCompetitionId
      if (m !== null && m !== undefined && m !== '') return m
      return null
    },
    activeCompetition () {
      if (this.activeCompetitionId === null || this.activeCompetitionId === undefined || this.activeCompetitionId === '') return null
      return this.competitions.find(c => String(c.id) === String(this.activeCompetitionId)) || null
    },
    filteredCompetitions () {
      const keyword = (this.keyword || '').trim().toLowerCase()
      if (!keyword) return this.competitions
      return this.competitions.filter(c => {
        const name = (c.name || '').toLowerCase()
        const desc = (c.description || c.rules_text || '').toLowerCase()
        return name.includes(keyword) || desc.includes(keyword)
      })
    },
    showCompetitionDetailPanel () {
      const v = this.activeCompetitionId
      return v !== null && v !== undefined && v !== ''
    },
    /** 当前报名周期内、计入「已提交」的作品（退赛前的旧作品不计入） */
    hasAnyEnrollment () {
      return this.myEnrolledIndividual || this.myEnrolledTeam
    },
    currentTeamEnrollmentRow () {
      return this.activeCompetitionEnrollmentRows && this.activeCompetitionEnrollmentRows.team
        ? this.activeCompetitionEnrollmentRows.team
        : null
    },
    isCurrentTeamCaptain () {
      const row = this.currentTeamEnrollmentRow
      if (!row) return false
      if (row.is_captain != null) return !!row.is_captain
      if (row.captain_id != null && this.altCurrentUserId != null) {
        return Number(row.captain_id) === Number(this.altCurrentUserId)
      }
      return false
    },
    /** 队伍赛道已报名且当前账号为队员（非队长） */
    studentTeamEnrolledAsMember () {
      return this.enrollMode === 'team' && this.myEnrolledTeam && !this.isCurrentTeamCaptain
    },
    teamEnrollActionBlockedForMember () {
      return this.studentTeamEnrolledAsMember
    },
    /** 队员已队伍报名后：不可再创建/加入队伍 */
    showStudentTeamCreateJoinOps () {
      return this.enrollMode === 'team' && !this.studentTeamEnrolledAsMember
    },
    /** 当前竞赛已存在队伍关联（已报名队伍或已有 team_id） */
    studentHasTeamForCurrentCompetition () {
      return !!this.currentTeamEnrollmentRow || !!this.myTeamId
    },
    /** 仅队长或未队伍报名时展示转让/退队 */
    showStudentTeamCaptainOptionalOps () {
      if (this.enrollMode !== 'team') return false
      if (this.studentTeamEnrolledAsMember) return false
      return this.studentCreatedTeamInCurrentCompetition || this.isCurrentTeamCaptain
    },
    showSubmissionPanelInEnrollView () {
      const enrolledForCurrentMode = this.enrollMode === 'team'
        ? this.myEnrolledTeam
        : this.myEnrolledIndividual
      if (!enrolledForCurrentMode) return false
      if (this.enrollMode === 'team' && this.currentTeamEnrollmentRow && !this.isCurrentTeamCaptain) return false
      return true
    },
    currentSubmissionTrackContext () {
      const scope = this.submissionMode === 'team' ? 'team' : 'individual'
      const individualRow = this.activeCompetitionEnrollmentRows.individual
      const teamRow = this.activeCompetitionEnrollmentRows.team
      const row = scope === 'team' ? teamRow : individualRow
      if (scope === 'team' && !teamRow) return null
      if (scope === 'individual' && !individualRow) return null
      return {
        scope,
        enrollmentId: row && row.id != null ? row.id : null,
        teamId: scope === 'team' && row && row.team_id != null ? row.team_id : null,
        cutoffMs: this.ignoreSubmissionsBeforeReenrollAt
      }
    },
    mySubmissionsForCurrentEnrollment () {
      const ctx = this.currentSubmissionTrackContext
      if (!ctx) return []
      return filterSubmissionsForEnrollmentTrack(this.mySubmissions, ctx)
    },
    /** 报名弹窗：当前提交类型（个人/队伍）在本报名周期已有作品则禁止再次提交 */
    enrollModalSubmissionLocked () {
      if (!this.hasAnyEnrollment) return false
      return this.mySubmissionsForCurrentEnrollment.length > 0
    },
    adminSubmissionsEmptyDescription () {
      if (this.adminSubmissionsHiddenByWithdrawCount > 0) {
        return `当前无有效作品（已隐藏 ${this.adminSubmissionsHiddenByWithdrawCount} 条退赛前的作品，仅展示重新报名后提交的作品）`
      }
      return '暂无作品数据，请先选择竞赛并点击「刷新该竞赛全部作品」'
    },
    studentBriefingRulesSegments () {
      const c = this.activeCompetition
      if (!c) return []
      const t = String(c.rules_text || '').trim()
      if (!t) return []
      const byHr = t.split(/\r?\n-{3,}\r?\n/)
      if (byHr.length >= 2) return byHr.map(s => s.trim()).filter(Boolean)
      const byPara = t.split(/\r?\n\r?\n+/)
      if (byPara.length >= 2) return byPara.map(s => s.trim()).filter(Boolean)
      return [t]
    },
    participantModesSummary () {
      const c = this.activeCompetition
      if (!c) return '参赛方式以主办方公告为准。'
      const parts = []
      if (c.allow_individual) parts.push('支持个人参赛')
      if (c.allow_team) parts.push('支持团队参赛')
      if (!parts.length) return '参赛方式以主办方公告为准。'
      return `${parts.join('；')}。具体资格条件见赛事要求。`
    },
    studentBriefingBlocks () {
      const segs = this.studentBriefingRulesSegments
      const modeLine = this.participantModesSummary
      if (segs.length >= 2) {
        return [
          { num: '01', title: '参赛对象', body: segs[0] },
          { num: '02', title: '规则说明', body: segs.slice(1).join('\n\n') }
        ]
      }
      if (segs.length === 1) {
        return [
          { num: '01', title: '参赛对象', body: modeLine },
          { num: '02', title: '规则说明', body: segs[0] }
        ]
      }
      return [
        { num: '01', title: '参赛对象', body: modeLine },
        { num: '02', title: '规则说明', body: '作品格式、提交方式及截止时间等请以上方简介与主办方后续通知为准。' }
      ]
    },
    studentBriefingContactLine () {
      const c = this.activeCompetition || {}
      const p = c.contact_phone || c.contact_tel || c.phone || c.hotline || c.contact
      if (p == null || String(p).trim() === '') return ''
      return String(p).trim()
    },
    allowIndividual () {
      if (!this.activeCompetition) return true
      if (this.activeCompetition.allow_individual === false) return false
      return true
    },
    allowTeam () {
      if (!this.activeCompetition) return true
      if (this.activeCompetition.allow_team === false) return false
      return true
    },
    /** 本竞赛任一赛道报名成功后，报名信息不可再改 */
    enrollProfileLockedAfterSuccess () {
      return this.hasAnyEnrollment
    },
    /** 竞赛为草稿或未发布时，报名区域不可用 */
    competitionEnrollPublishBlocked () {
      const c = this.activeCompetition
      if (!c) return false
      const s = c.status != null ? String(c.status).toLowerCase() : ''
      if (s === 'draft') return true
      return s !== 'published' && s !== 'open'
    },
    competitionEnrollBlockedAlertTitle () {
      const c = this.activeCompetition
      if (!c) return '竞赛尚未发布或已停止报名'
      const s = c.status != null ? String(c.status).toLowerCase() : ''
      return s === 'draft' ? '当前竞赛为草稿，尚未发布' : '竞赛尚未发布或已停止报名'
    },
    competitionEnrollBlockedAlertDescription () {
      return '暂无法报名；主办方发布竞赛或重新开放报名后即可重新报名。'
    },
    /** 停止报名：closed 或已过 end_at（与 §8.5 一致；退赛等仍可进行） */
    competitionEnrollmentClosed () {
      const c = this.activeCompetition
      if (!c) return false
      const s = c.status != null ? String(c.status).toLowerCase() : ''
      if (s === 'closed') return true
      if (c.end_at) {
        const endMs = new Date(c.end_at).getTime()
        if (Number.isFinite(endMs) && Date.now() >= endMs) return true
      }
      return false
    },
    /** 仅限制建队、邀请入队（含未发布、已停止报名） */
    competitionTeamCreateInviteBlocked () {
      return this.competitionEnrollPublishBlocked || this.competitionEnrollmentClosed
    },
    competitionTeamCreateInviteBlockedDescription () {
      if (this.competitionEnrollPublishBlocked) {
        return '竞赛尚未发布，暂无法建队或邀请队员；已发布且报名开放前可改队名。'
      }
      if (this.competitionEnrollmentClosed) {
        return ''
      }
      return ''
    },
    /** 已停止报名或未发布时不可移除队员 */
    competitionTeamRemoveMemberBlocked () {
      return this.competitionEnrollPublishBlocked || this.competitionEnrollmentClosed
    },
    competitionTeamRemoveMemberBlockedMessage () {
      if (this.competitionEnrollPublishBlocked) {
        return ''
      }
      if (this.competitionEnrollmentClosed) {
        return ''
      }
      return ''
    },
    advisorTeamsTableData () {
      return (this.advisorTeams || []).map(t => ({
        id: t.id,
        name: t.name != null && String(t.name).trim() !== '' ? String(t.name) : '—',
        captain_id: t.captain_id != null ? t.captain_id : '-',
        member_count: Array.isArray(t.members) ? t.members.length : 0,
        status_text: this.participantTeamStatusText(t.status),
        can_operate: this.canAdvisorOperateTeam(t),
        can_operate_text: this.canAdvisorOperateTeam(t) ? '是' : '否'
      }))
    },
    advisorSelectedTeam () {
      if (this.advisorSelectedTeamId == null) return null
      return (this.advisorTeams || []).find(t => Number(t.id) === Number(this.advisorSelectedTeamId)) || null
    },
    advisorSelectedTeamMembers () {
      const t = this.advisorSelectedTeam
      if (!t || !Array.isArray(t.members)) return []
      return t.members
    },
    canOperateAdvisorSelectedTeam () {
      return this.canAdvisorOperateTeam(this.advisorSelectedTeam)
    },
    /** 简介按行拆分，便于首行英文副标题 + 次行中文口号等排版 */
    competitionHeroDescLines () {
      const c = this.activeCompetition
      if (!c) return []
      const raw = String(c.description || '').trim()
      if (!raw) return []
      return raw.split(/\r?\n+/).map(s => s.trim()).filter(Boolean)
    },
    competitionHeroYear () {
      const c = this.activeCompetition
      if (!c || !c.start_at) return ''
      const d = new Date(c.start_at)
      if (Number.isNaN(d.getTime())) return ''
      return String(d.getFullYear())
    },
    /** 首行且无中日韩字符时视为英文副标题（如 China AI … Competition） */
    competitionHeroSubtitleEn () {
      const lines = this.competitionHeroDescLines
      if (!lines.length) return ''
      const first = lines[0]
      if (/[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/.test(first)) return ''
      return first
    },
    /** 口号：简介中除英文首行外的首条非竞赛名文案；否则取规则首行 */
    competitionHeroSlogan () {
      const c = this.activeCompetition
      const name = c ? String(c.name || '').trim() : ''
      const lines = this.competitionHeroDescLines
      const en = this.competitionHeroSubtitleEn
      const rest = en ? lines.slice(1) : lines
      for (const p of rest) {
        if (p && p !== name) return p
      }
      if (!en && lines[0] && lines[0] !== name) return lines[0]
      if (c && c.rules_text) {
        const r0 = String(c.rules_text).split(/\r?\n+/).map(s => s.trim()).filter(Boolean)[0]
        return r0 || ''
      }
      return ''
    },
    competitionHeroDateRange () {
      const c = this.activeCompetition
      if (!c) return '-'
      return this.formatHeroDateRange(c.start_at, c.end_at)
    },
    summaryTableData () {
      const s = this.scoresSummary
      if (!s) return []
      return [
        { key: 'competition_id', label: '竞赛ID', value: s.competition_id != null ? s.competition_id : '-' },
        { key: 'submissions_total', label: '总提交数', value: s.submissions_total != null ? s.submissions_total : '-' },
        { key: 'reviewed_total', label: '已评分数', value: s.reviewed_total != null ? s.reviewed_total : '-' },
        { key: 'avg_score', label: '平均分', value: s.avg_score != null ? s.avg_score : '-' },
        { key: 'max_score', label: '最高分', value: s.max_score != null ? s.max_score : '-' },
        { key: 'min_score', label: '最低分', value: s.min_score != null ? s.min_score : '-' }
      ]
    },
    rankingsTableData () {
      const r = this.scoresRankings
      if (!r || !Array.isArray(r.items)) return []
      return (r.items || []).map((item, index) => ({
        rowIndex: index + 1,
        team_id: item.team_id != null ? item.team_id : '-',
        student_id: item.student_id != null ? item.student_id : '-',
        best_score: item.best_score != null ? item.best_score : '-',
        reviewed_submissions: item.reviewed_submissions != null ? item.reviewed_submissions : '-',
        key: `rank-${index}`
      }))
    },
    myScoresTableData () {
      const payload = this.myScores
      if (!payload || !Array.isArray(payload.submissions)) return []
      return payload.submissions.map((item, index) => {
        // 8.20：成绩列使用接口返回的 submissions[].score（未审核为 null → —）
        const scoreDisplay = this.formatScoreCell(item)
        return {
          id: item.id != null ? item.id : `row-${index}`,
          competition_id: item.competition_id != null ? item.competition_id : '-',
          title: item.title != null && String(item.title).trim() !== '' ? String(item.title) : '-',
          status: this.getSubmissionStatusText(item.status),
          score: scoreDisplay,
          submitter_id: item.submitter_id != null ? item.submitter_id : '-',
          submitted_at: item.submitted_at ? this.formatDateTime(item.submitted_at) : '-'
        }
      })
    }
  },
  watch: {
    activeCompetitionId (newId) {
      this.advisorCreatedTeamIds = []
      this.studentCreatedTeamInCurrentCompetition = false
      this.teamEnrollmentEligible = false
      this.myTeamId = null
      this.joinTeamId = null
      this.studentTeamInviteId = null
      this.studentTeamRemoveMemberId = null
      this.submissionTeamId = null
      this.activeCompetitionMyEnrollKind = null
      this.activeCompetitionEnrollmentId = null
      this.myEnrolledIndividual = false
      this.myEnrolledTeam = false
      this.activeCompetitionEnrollmentRows = { individual: null, team: null }
      this.ignoreSubmissionsBeforeReenrollAt = null
      if (this.enrollMode === 'individual') this.submissionMode = 'individual'
      if (this.enrollMode === 'team') this.submissionMode = 'team'

      this.publishCompetitionId = newId

      if (newId !== null && newId !== undefined && newId !== '' && this.isStudent) {
        void this.refreshMySubmissions().then(async () => {
          if (this.activeCompetitionId !== newId) return
          await this.refreshActiveCompetitionMyEnrollKind()
          this.applyStoredWithdrawSubmissionCutoff()
          await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
        })
      }

      if (newId !== null && newId !== undefined && newId !== '' && this.canViewCompetitionSubmissions) {
        if (this.standaloneDetailMode) {
          this.refreshAdminSubmissions()
        } else {
          this.adminSubmissions = []
        }
      } else {
        this.adminSubmissions = []
      }

      this.revokeStudentBriefingQrObjectUrl()
      if (newId !== null && newId !== undefined && newId !== '' && this.isStudent && this.standaloneDetailMode) {
        void this.fetchStudentBriefingQr()
      }

      if (newId !== null && newId !== undefined && newId !== '') {
        this.advisorSelectedTeamId = null
        this.advisorRenameName = ''
        this.advisorInviteStudentId = null
        if (this.showAdvisorTeamPanel) {
          void this.refreshAdvisorTeams()
        } else {
          this.advisorTeams = []
        }
      } else {
        this.advisorTeams = []
        this.advisorSelectedTeamId = null
      }
    },
    enrollMode (newMode) {
      this.submissionMode = newMode
      if (newMode === 'team' && this.myTeamId) this.submissionTeamId = this.myTeamId
      this.applyEnrollmentContextFromRows()
    },
    myTeamId (newId) {
      if (this.submissionTeamId == null && newId) this.submissionTeamId = newId
    },
    showCreateCompetitionModal (visible) {
      if (visible) {
        this.resetCreateCompetitionForm()
      }
    },
    showStandaloneEnrollModal (visible) {
      if (visible && this.standaloneDetailMode) {
        this.$nextTick(() => this.syncEnrollProfileDefaults())
      }
    }
  },
  mounted () {
    window.addEventListener('alt-identity-changed', this.onAltIdentityChanged)
    if (this.standaloneDetailMode && this.initialCompetitionId != null && String(this.initialCompetitionId).trim() !== '') {
      void this.bootstrapStandaloneDetail()
    } else {
      void this.initCompetitionListPage()
    }
    this.syncEnrollProfileDefaults()
  },
  beforeDestroy () {
    window.removeEventListener('alt-identity-changed', this.onAltIdentityChanged)
    this.revokeStudentBriefingQrObjectUrl()
  },
  methods: {
    /** 与表格 row-key 一致，供勾选 selectedRowKeys 使用 */
    resolveCompetitionRowKey (id) {
      if (id === null || id === undefined || id === '') return null
      const c = (this.competitions || []).find(x => String(x.id) === String(id))
      return c ? c.id : id
    },

    onAdminCompetitionTableSelectChange (selectedRowKeys) {
      const keys = selectedRowKeys || []
      const raw = keys.length ? keys[keys.length - 1] : null
      this.selectCompetition(raw === undefined || raw === null || raw === '' ? null : raw)
    },

    competitionListRowClassName (record) {
      if (this.activeCompetitionId === null || this.activeCompetitionId === undefined || this.activeCompetitionId === '') return ''
      return String(record.id) === String(this.activeCompetitionId) ? 'competition-table-row-active' : ''
    },

    openCompetitionDetailInNewTab (id) {
      if (id == null) return
      try {
        const r = this.$router.resolve({
          name: 'ManuCompetitionDetail',
          query: { id: String(id) }
        })
        if (r && r.href) window.open(r.href, '_blank')
      } catch (e) {
        this.$message.error('无法打开竞赛详情页')
      }
    },

    onAltIdentityChanged () {
      this.syncEnrollProfileDefaults()
      this.$forceUpdate()
    },
    async refreshAltExpertProfile () {
      if (!getStoredAltToken() || !isAltCompetitionExpert()) return
      try {
        const me = await fetchAltIdentityMe()
        applyAltIdentityMeToStorage(me)
      } catch (e) {
        const msg = e && e.message ? e.message : ''
        if (msg) console.warn('[CompetitionRegistrationSystem] sync expert profile failed:', msg)
      }
    },
    async initCompetitionListPage () {
      await this.refreshAltExpertProfile()
      await this.fetchCompetitions()
    },
    async bootstrapStandaloneDetail () {
      this.manualCompetitionId = null
      await this.refreshAltExpertProfile()
      await this.fetchCompetitions()
      const raw = this.initialCompetitionId
      if (raw != null && String(raw).trim() !== '') {
        this.selectCompetition(raw)
      }
    },

    /** 竞赛详情独立页顶部「报名」：打开报名与组队弹窗（供父组件 ref 调用） */
    openStandaloneEnrollModal () {
      if (!this.standaloneDetailMode) return
      if (!this.isStudent) {
        this.$message.warning('仅学生身份可使用报名功能')
        return
      }
      void this.refreshActiveCompetitionMyEnrollKind()
        .then(() => {
          this.applyStoredWithdrawSubmissionCutoff()
          return this.refreshMySubmissions()
        })
        .then(() => {
          if (this.activeCompetitionMyEnrollKind) this.syncIgnoreSubmissionsAfterEnrollRefresh()
        })
      this.showStandaloneEnrollModal = true
    },
    /** 竞赛详情独立页顶部「作品」：打开我的作品弹窗 */
    openStandaloneMyWorksModal () {
      if (!this.standaloneDetailMode) return
      if (!this.isStudent) {
        this.$message.warning('仅学生身份可查看作品')
        return
      }
      void this.refreshMySubmissions().then(() => {
        this.showStandaloneMyWorksModal = true
      })
    },

    revokeStudentBriefingQrObjectUrl () {
      if (this.studentBriefingQrObjectUrl) {
        try {
          URL.revokeObjectURL(this.studentBriefingQrObjectUrl)
        } catch (e) {
          /* ignore */
        }
        this.studentBriefingQrObjectUrl = null
      }
    },
    async fetchStudentBriefingQr () {
      this.revokeStudentBriefingQrObjectUrl()
      if (!this.activeCompetitionId || !this.isStudent || !this.standaloneDetailMode) return
      try {
        const blob = await getCompetitionQrCode(this.activeCompetitionId)
        if (blob && typeof blob.size === 'number' && blob.size > 0) {
          const t = (blob.type || '').toLowerCase()
          if (t.startsWith('image/')) {
            this.studentBriefingQrObjectUrl = URL.createObjectURL(blob)
          } else if (
            t === 'application/octet-stream' ||
            t === '' ||
            t === 'binary/octet-stream'
          ) {
            this.studentBriefingQrObjectUrl = URL.createObjectURL(blob)
          }
        }
      } catch (e) {
        /* 无二维码或未开放接口 */
      }
    },

    getApiErrorMessage (error, fallback = '操作失败') {
      const respData = error && error.response ? error.response.data : null
      let raw =
        (respData && (respData.detail || respData.message || respData.error)) ||
        (error && error.message) ||
        ''
      if (Array.isArray(raw)) {
        raw = raw
          .map((item) => {
            if (item && typeof item === 'object' && item.msg != null) {
              const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join('.') : ''
              return loc ? `${loc}: ${item.msg}` : String(item.msg)
            }
            return typeof item === 'string' ? item : JSON.stringify(item)
          })
          .filter(Boolean)
          .join('；')
      }
      const text = typeof raw === 'string' ? raw : JSON.stringify(raw || {})

      if (/competition not published/i.test(text)) {
        return '竞赛尚未发布（draft），需管理员发布后再报名'
      }

      if (/competition enrollment is closed|enrollment is closed/i.test(text)) {
        return '竞赛已停止报名（状态为 closed 或已过结束时间）'
      }

      if (/individual enrollment not allowed/i.test(text)) {
        return '该竞赛不允许个人赛道，请使用队伍参赛'
      }

      if (/team enrollment not allowed/i.test(text)) {
        return '该竞赛不允许队伍赛道报名'
      }

      if (/already enrolled in the individual track/i.test(text)) {
        return '个人赛道已报名，无需重复报名（可与队伍赛道并存）'
      }

      if (/already enrolled in the team track/i.test(text)) {
        return '队伍赛道已报名，无需重复报名（可与个人赛道并存）'
      }

      if (/only students can enroll/i.test(text)) {
        return '仅学生账号可报名，当前角色无法使用报名接口'
      }

      if (/enrollment failed:/i.test(text)) {
        const tail = text.replace(/^Enrollment failed:\s*/i, '').trim()
        return tail ? `报名失败：${tail}` : '报名提交失败，请稍后重试'
      }

      if (
        text.includes('competition_enrollments') ||
        text.includes('UNIQUE constraint failed')
      ) {
        return '报名记录冲突，请刷新后重试或联系管理员'
      }

      if (/not published yet|尚未发布/i.test(text)) {
        return '竞赛尚未发布，暂无法报名。请待主办方发布竞赛后再试。'
      }

      if (/user not found/i.test(text)) {
        return '填写的队员 ID 不存在，请核对学生账号 ID（alt_auth_users.id）后重试'
      }

      if (/target must be a student account/i.test(text)) {
        return '填写的用户 ID 不是学生账号，请填写已注册为「学生」角色的账号 ID'
      }

      if (/specify track=individual or track=team/i.test(text)) {
        return '本竞赛同时存在个人与组队报名，请指定要退出的赛道（个人或队伍）'
      }

      if (/transfer.*captain|captain.*transfer|must transfer captain/i.test(text)) {
        return '您是队长且队内仍有其他成员，请先转让队长后再退赛'
      }

      if (/enrollment is closed|competition enrollment is closed|enrollment closed|停止报名/i.test(text)) {
        if (/remove|member|队员|踢/i.test(text)) {
          return '竞赛已停止报名（已锁定或已过结束时间），无法移除队员'
        }
        return '竞赛已停止报名（已锁定或已过结束时间），无法新建队伍或邀请入队'
      }

      return text || fallback
    },

    /** §8.8 退赛 track：仅一条有效报名时省略；双赛道时按当前 UI 参赛方式 */
    resolveWithdrawTrack () {
      const hasIndividual = this.myEnrolledIndividual
      const hasTeam = this.myEnrolledTeam
      if (hasIndividual && hasTeam) {
        return this.enrollMode === 'team' ? 'team' : 'individual'
      }
      if (hasIndividual) return 'individual'
      if (hasTeam) return 'team'
      return null
    },

    withdrawTrackLabel (track) {
      return track === 'team' ? '组队' : '个人'
    },

    assertCompetitionPublishedForEnroll (showToast = true) {
      if (!this.competitionEnrollPublishBlocked) return true
      if (showToast) {
        this.$message.warning('竞赛尚未发布，暂无法报名。请待主办方发布竞赛后再试。')
      }
      return false
    },

    async fetchCompetitions () {
      this.competitionsLoading = true
      this.competitionsError = ''
      const normalizeList = (items) => {
        if (!Array.isArray(items)) return []
        return items.map(item => {
          if (!item || typeof item !== 'object') return item
          const rid = item.id != null ? item.id : item.competition_id
          return rid != null ? { ...item, id: rid } : item
        })
      }
      try {
        const res = await getCompetitions()
        if (Array.isArray(res)) this.competitions = normalizeList(res)
        else if (res && Array.isArray(res.items)) this.competitions = normalizeList(res.items)
        else this.competitions = []
      } catch (e) {
        this.competitionsError = '获取竞赛列表失败：' + (e && e.message ? e.message : '未知错误')
        this.competitions = []
      } finally {
        this.competitionsLoading = false
      }
    },
    selectCompetition (id) {
      if (id === undefined || id === null || id === '') {
        this.selectedCompetitionId = null
        return
      }
      const c = (this.competitions || []).find(x => String(x.id) === String(id))
      this.selectedCompetitionId = c ? c.id : id
    },
    useManualCompetition () {
      const m = this.manualCompetitionId
      this.selectedCompetitionId = m !== null && m !== undefined && m !== '' ? m : null
    },
    getStatusColor (status) {
      const map = { draft: 'default', published: 'green', open: 'green', closed: 'red', upcoming: 'blue' }
      return map[status] || 'default'
    },
    getStatusText (status) {
      const map = { draft: '草稿', published: '已发布', open: '报名中', closed: '已结束', upcoming: '即将开始' }
      return map[status] || (status || '未知')
    },
    getSubmissionStatusColor (status) {
      const map = { submitted: 'blue', approved: 'green', rejected: 'red', draft: 'default' }
      return map[status] || 'default'
    },
    getSubmissionStatusText (status) {
      const map = { submitted: '已提交', approved: '已通过', rejected: '已拒绝', draft: '草稿' }
      return map[status] || (status || '-')
    },
    formatDate (dateString) {
      if (!dateString) return '-'
      const d = new Date(dateString)
      if (Number.isNaN(d.getTime())) return '-'
      return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
    },
    formatDateTime (dateString) {
      if (!dateString) return '-'
      const d = new Date(dateString)
      if (Number.isNaN(d.getTime())) return '-'
      return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    },

    /** 头图活动时间：MM.DD — MM.DD（与常见赛事主视觉一致） */
    formatHeroDateRange (startAt, endAt) {
      if (!startAt || !endAt) return '-'
      const s = new Date(startAt)
      const e = new Date(endAt)
      if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return '-'
      const pad = (n) => String(n).padStart(2, '0')
      const fmt = (d) => `${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
      return `${fmt(s)} — ${fmt(e)}`
    },

    /** 从竞赛独立账号资料预填选填项（不覆盖用户已填写内容） */
    syncEnrollProfileDefaults () {
      if (!this.isStudent) return
      const p = getAltProfileFromStorage() || {}
      const map = {
        student_no: p.student_id,
        real_name: p.full_name,
        college: p.college != null ? p.college : p.school,
        grade: p.grade,
        contact: p.email != null ? p.email : (p.contact != null ? p.contact : p.phone)
      }
      const f = this.enrollProfileForm || {}
      for (const [key, val] of Object.entries(map)) {
        if (val == null || String(val).trim() === '') continue
        const cur = f[key] != null ? String(f[key]).trim() : ''
        if (!cur) this.$set(this.enrollProfileForm, key, String(val).trim())
      }
    },

    buildEnrollExtraFields () {
      const f = this.enrollProfileForm || {}
      const out = {}
      const keys = ['student_no', 'real_name', 'college', 'grade', 'contact']
      for (const k of keys) {
        const s = f[k] != null ? String(f[k]).trim() : ''
        if (s) out[k] = s
      }
      return out
    },

    filterSubmissionsForCurrentEnrollment (list) {
      const ctx = this.currentSubmissionTrackContext
      if (!ctx) return []
      return filterSubmissionsForEnrollmentTrack(list, ctx)
    },

    applyStoredWithdrawSubmissionCutoff () {
      const cid = this.activeCompetitionId
      if (cid == null || cid === '') return
      const stored = getCompetitionWithdrawSubmissionCutoff(cid)
      if (stored) this.ignoreSubmissionsBeforeReenrollAt = stored
    },

    resetSubmissionFormFields () {
      this.submissionForm.title = ''
      this.submissionForm.description = ''
      this.submissionForm.content_text = ''
      this.submissionForm.file = null
    },

    /** 报名/刷新作品后：有当前报名周期作品则锁定；仅有退赛前旧作品则用时间戳排除 */
    syncIgnoreSubmissionsAfterEnrollRefresh () {
      const cid = this.activeCompetitionId
      if (cid == null || cid === '') return
      const legacy = (this.mySubmissions || []).filter(s => s && !isWithdrawnSubmissionRow(s))
      const currentByEnrollment = this.filterSubmissionsForCurrentEnrollment(legacy)
      if (currentByEnrollment.length > 0) {
        this.ignoreSubmissionsBeforeReenrollAt = null
        clearCompetitionWithdrawSubmissionCutoff(cid)
        return
      }
      if (legacy.length > 0) {
        const ts = Date.now()
        this.ignoreSubmissionsBeforeReenrollAt = ts
        markCompetitionWithdrawnForResubmit(cid, ts)
      } else {
        this.ignoreSubmissionsBeforeReenrollAt = null
        clearCompetitionWithdrawSubmissionCutoff(cid)
      }
    },

    async handleWithdrawCompetition (track) {
      if (!this.activeCompetitionId) return
      const resolvedTrack = track === 'individual' || track === 'team' ? track : this.resolveWithdrawTrack()
      if (!resolvedTrack) {
        this.$message.warning('当前没有可退出的有效报名')
        return
      }
      const trackLabel = this.withdrawTrackLabel(resolvedTrack)
      const bothTracks = this.myEnrolledIndividual && this.myEnrolledTeam
      try {
        await this.$confirm({
          title: `确认退出${trackLabel}赛道`,
          content: bothTracks
            ? `将取消本竞赛的${trackLabel}赛道报名；另一赛道不受影响。退赛后若再次报名，需重新提交该赛道作品。是否继续？`
            : '退赛后当前报名资格将取消；若再次报名，需重新提交作品。是否继续？',
          okText: '退赛',
          cancelText: '取消',
          okType: 'danger'
        })
      } catch {
        return
      }
      this.withdrawLoading = true
      try {
        await withdrawCompetition(this.activeCompetitionId, { track: resolvedTrack })
        this.$message.success(`${trackLabel}赛道退赛成功`)
        const withdrawTs = Date.now()
        this.ignoreSubmissionsBeforeReenrollAt = withdrawTs
        markCompetitionWithdrawnForResubmit(this.activeCompetitionId, withdrawTs)
        if (resolvedTrack === 'individual') {
          this.activeCompetitionEnrollmentRows = {
            ...this.activeCompetitionEnrollmentRows,
            individual: null
          }
          this.myEnrolledIndividual = false
        } else {
          this.activeCompetitionEnrollmentRows = {
            ...this.activeCompetitionEnrollmentRows,
            team: null
          }
          this.myEnrolledTeam = false
          this.studentCreatedTeamInCurrentCompetition = false
          this.teamEnrollmentEligible = false
          this.myTeamId = null
          this.submissionTeamId = null
        }
        this.applyEnrollmentContextFromRows()
        this.resetSubmissionFormFields()
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        this.$message.error('退赛失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.withdrawLoading = false
      }
    },

    applyEnrollmentContextFromRows () {
      const individualRow = this.activeCompetitionEnrollmentRows.individual
      const teamRow = this.activeCompetitionEnrollmentRows.team
      this.myEnrolledIndividual = !!individualRow
      this.myEnrolledTeam = !!teamRow

      // 尊重用户当前选择的参赛方式，不因「已有个人报名」而强制切回个人
      if (this.enrollMode === 'team') {
        this.activeCompetitionMyEnrollKind = 'team'
        this.submissionMode = 'team'
        if (teamRow) {
          this.activeCompetitionEnrollmentId = teamRow.id != null ? teamRow.id : null
          this.myTeamId = teamRow.team_id
          this.teamEnrollmentEligible = true
          this.submissionTeamId = teamRow.team_id
        } else {
          this.activeCompetitionEnrollmentId = null
        }
        return
      }

      if (this.enrollMode === 'individual') {
        this.activeCompetitionMyEnrollKind = 'individual'
        this.submissionMode = 'individual'
        this.activeCompetitionEnrollmentId =
          individualRow && individualRow.id != null ? individualRow.id : null
        return
      }

      // 兜底：仅在 enrollMode 异常时按已有报名记录推断默认方式
      if (individualRow) {
        this.enrollMode = 'individual'
        this.activeCompetitionMyEnrollKind = 'individual'
        this.activeCompetitionEnrollmentId = individualRow.id != null ? individualRow.id : null
        this.submissionMode = 'individual'
        return
      }
      if (teamRow) {
        this.enrollMode = 'team'
        this.activeCompetitionMyEnrollKind = 'team'
        this.activeCompetitionEnrollmentId = teamRow.id != null ? teamRow.id : null
        this.submissionMode = 'team'
        this.myTeamId = teamRow.team_id
        this.teamEnrollmentEligible = true
        this.submissionTeamId = teamRow.team_id
        return
      }
      this.activeCompetitionMyEnrollKind = null
      this.activeCompetitionEnrollmentId = null
    },

    onSubmissionModeChange () {
      const individualRow = this.activeCompetitionEnrollmentRows.individual
      const teamRow = this.activeCompetitionEnrollmentRows.team
      if (this.submissionMode === 'team' && teamRow) {
        this.activeCompetitionMyEnrollKind = 'team'
        this.activeCompetitionEnrollmentId = teamRow.id != null ? teamRow.id : null
        if (teamRow.team_id != null) {
          this.myTeamId = teamRow.team_id
          this.submissionTeamId = teamRow.team_id
        }
      } else if (this.submissionMode === 'individual' && individualRow) {
        this.activeCompetitionMyEnrollKind = 'individual'
        this.activeCompetitionEnrollmentId = individualRow.id != null ? individualRow.id : null
      }
    },

    async refreshActiveCompetitionMyEnrollKind () {
      if (!this.activeCompetitionId || !this.isStudent) {
        this.activeCompetitionMyEnrollKind = null
        this.activeCompetitionEnrollmentId = null
        this.myEnrolledIndividual = false
        this.myEnrolledTeam = false
        this.activeCompetitionEnrollmentRows = { individual: null, team: null }
        return
      }
      try {
        const res = await getMyCompetitionEnrollments()
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : (res && Array.isArray(res.data) ? res.data : []))
        const cid = Number(this.activeCompetitionId)
        const enrolledRows = list.filter(r => Number(r.competition_id) === cid && r.status === 'enrolled')
        const { individual: individualRow, team: teamRow } = splitEnrollmentsByTrack(enrolledRows)
        this.activeCompetitionEnrollmentRows = { individual: individualRow, team: teamRow }
        this.applyEnrollmentContextFromRows()
      } catch {
        this.activeCompetitionMyEnrollKind = null
        this.activeCompetitionEnrollmentId = null
        this.myEnrolledIndividual = false
        this.myEnrolledTeam = false
        this.activeCompetitionEnrollmentRows = { individual: null, team: null }
      }
    },

    async handleEnrollIndividual () {
      if (!this.activeCompetitionId) return
      if (!this.assertCompetitionPublishedForEnroll()) return
      if (this.myEnrolledIndividual) {
        this.$message.info('您已完成个人报名，无需重复操作')
        return
      }
      if (!this.allowIndividual) {
        this.$message.error('该竞赛不允许个人参赛')
        return
      }
      this.enrollLoading = true
      try {
        await enrollCompetition({
          competition_id: this.activeCompetitionId,
          team_id: null,
          ...this.buildEnrollExtraFields()
        })
        this.$message.success('个人报名成功')
        this.enrollMode = 'individual'
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        await this.handleEnrollApiError(e, 'individual')
      } finally {
        this.enrollLoading = false
      }
    },

    getEnrollDetailRaw (error) {
      const respData = error && error.response ? error.response.data : null
      const raw =
        (respData && (respData.detail || respData.message || respData.error)) ||
        (error && error.message) ||
        ''
      if (typeof raw === 'string') return raw
      if (Array.isArray(raw) && raw.length && raw[0] && raw[0].msg) return String(raw[0].msg)
      return typeof raw === 'object' ? JSON.stringify(raw) : String(raw || '')
    },

    isAlreadyEnrolledInTrack (error, track) {
      const text = this.getEnrollDetailRaw(error).toLowerCase()
      if (track === 'individual') {
        return text.includes('already enrolled in the individual track')
      }
      if (track === 'team') {
        return text.includes('already enrolled in the team track')
      }
      return false
    },

    isAlreadyEnrolledError (error) {
      if (this.isAlreadyEnrolledInTrack(error, 'individual') || this.isAlreadyEnrolledInTrack(error, 'team')) {
        return true
      }
      const msg = (this.getApiErrorMessage(error, '') || '').toLowerCase()
      return /already enrolled|已报名|重复报名|赛道已报名/i.test(msg)
    },

    async handleEnrollApiError (error, track) {
      if (this.isAlreadyEnrolledInTrack(error, track)) {
        const label = track === 'team' ? '队伍' : '个人'
        this.$message.info(`${label}赛道已报名，无需重复操作`)
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
        return true
      }
      this.$message.error('报名失败：' + this.getApiErrorMessage(error, '未知错误'))
      return false
    },

    async handleEnrollWithTeam () {
      if (!this.activeCompetitionId) return
      if (!this.assertCompetitionPublishedForEnroll()) return
      if (this.myEnrolledTeam) {
        this.$message.info('您已完成队伍报名，无需重复操作')
        return
      }
      if (!this.teamEnrollmentEligible || !this.myTeamId) {
        this.$message.warning('请先创建队伍或加入已有队伍，获得队伍ID后再报名')
        return
      }
      if (!this.allowTeam) {
        this.$message.error('该竞赛不允许团队参赛')
        return
      }
      this.enrollLoading = true
      try {
        await enrollCompetition({
          competition_id: this.activeCompetitionId,
          team_id: this.myTeamId,
          ...this.buildEnrollExtraFields()
        })
        this.submissionTeamId = this.myTeamId
        this.$message.success('队伍报名成功')
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        const handled = await this.handleEnrollApiError(e, 'team')
        if (!handled && this.isAlreadyEnrolledError(e)) {
          this.$message.success('队伍赛道已报名（可能由创建/加入队伍时自动完成），无需重复操作')
          await this.refreshActiveCompetitionMyEnrollKind()
          await this.refreshMySubmissions()
          this.syncIgnoreSubmissionsAfterEnrollRefresh()
          await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
        }
      } finally {
        this.enrollLoading = false
      }
    },

    async handleCreateTeamOnly () {
      if (!this.activeCompetitionId) return
      if (this.studentTeamEnrolledAsMember) {
        this.$message.info('您已是队伍报名队员，无法创建新队伍')
        return
      }
      if (this.studentHasTeamForCurrentCompetition) {
        this.$message.info('当前竞赛已存在您的队伍，无法重复创建')
        return
      }
      if (!this.assertCompetitionPublishedForEnroll()) return
      if (!this.allowTeam) {
        this.$message.error('该竞赛不允许团队参赛')
        return
      }
      this.enrollLoading = true
      try {
        const team = await createCompetitionTeam({ competition_id: this.activeCompetitionId, initial_member_ids: null })
        const teamId = team && (team.id || team.team_id)
        if (!teamId) throw new Error('创建队伍返回缺少 id')
        this.myTeamId = teamId
        this.submissionTeamId = teamId
        this.studentCreatedTeamInCurrentCompetition = true
        this.teamEnrollmentEligible = true
        await this.refreshMySubmissions()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
        await this.refreshActiveCompetitionMyEnrollKind()
        if (this.myEnrolledTeam) {
          this.syncIgnoreSubmissionsAfterEnrollRefresh()
          this.$message.success('队伍创建成功，系统已为您完成本竞赛的队伍报名，可直接提交作品')
        } else {
          this.$message.success('队伍创建成功，请点击「报名（队伍）」完成竞赛报名')
        }
      } catch (e) {
        this.$message.error('创建队伍失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.enrollLoading = false
      }
    },

    getJoinTeamErrorMessage (error) {
      const status = error && error.response && error.response.status
      const data = error && error.response && error.response.data
      const detail = (data && (data.detail || data.message)) || ''
      const text = typeof detail === 'string' ? detail : JSON.stringify(detail || {})
      if (status === 404 || /not found|不存在|找不到|No such|invalid team/i.test(text)) {
        return '该队伍不存在或已失效，请向队长确认队伍ID'
      }
      return text || (error && error.message) || '加入失败'
    },

    async validateJoinTeamBelongsToActiveCompetition () {
      if (!this.activeCompetitionId || !this.joinTeamId) return true
      try {
        const res = await getCompetitionParticipantsTeams(this.activeCompetitionId)
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : (res && Array.isArray(res.data) ? res.data : []))
        if (!Array.isArray(list) || !list.length) return true
        const found = list.find(r => Number(r.team_id) === Number(this.joinTeamId))
        if (found) return true
        const currentName = (this.activeCompetition && this.activeCompetition.name) ? this.activeCompetition.name : '-'
        this.$message.warning(`队伍ID ${this.joinTeamId} 不属于当前竞赛（${this.activeCompetitionId} - ${currentName}），请确认后再加入`)
        return false
      } catch {
        // 校验接口失败时不阻断主流程，避免影响正常加入
        return true
      }
    },

    async handleJoinTeam () {
      if (this.studentTeamEnrolledAsMember) {
        this.$message.info('您已完成队伍报名且为队员，无法再加入其他队伍')
        return
      }
      if (this.studentHasTeamForCurrentCompetition) {
        this.$message.info('当前竞赛已存在您的队伍，无法加入其他队伍')
        return
      }
      if (!this.joinTeamId) {
        this.$message.warning('请先输入要加入的队伍ID')
        return
      }
      if (!this.assertCompetitionPublishedForEnroll()) return
      if (!this.activeCompetitionId) {
        this.$message.warning('请先选择竞赛')
        return
      }
      const teamBelongsCurrentCompetition = await this.validateJoinTeamBelongsToActiveCompetition()
      if (!teamBelongsCurrentCompetition) return
      this.teamLoading = true
      try {
        await addTeamMember(this.joinTeamId)
        this.myTeamId = this.joinTeamId
        this.submissionTeamId = this.joinTeamId
        this.studentCreatedTeamInCurrentCompetition = false
        this.teamEnrollmentEligible = true
        await this.refreshMySubmissions()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
        await this.refreshActiveCompetitionMyEnrollKind()
        if (this.myEnrolledTeam) {
          this.syncIgnoreSubmissionsAfterEnrollRefresh()
          this.$message.success('加入队伍成功，您已在该竞赛以队伍身份报名')
        } else {
          this.$message.success('加入队伍成功，请点击「报名（队伍）」完成竞赛报名')
        }
      } catch (e) {
        this.$message.error('加入队伍失败：' + this.getJoinTeamErrorMessage(e))
      } finally {
        this.teamLoading = false
      }
    },

    async handleTransferCaptain () {
      if (!this.transferTeamId || !this.newCaptainId) return
      this.teamLoading = true
      try {
        await transferTeamCaptain(this.transferTeamId, { team_id: this.transferTeamId, new_captain_id: this.newCaptainId })
        this.$message.success('队长转让成功')
        await this.refreshMyScores(false)
      } catch (e) {
        this.$message.error('转让失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    async handleLeaveTeam () {
      if (!this.leaveTeamId) return
      this.teamLoading = true
      try {
        await leaveTeam(this.leaveTeamId)
        this.$message.success('退队成功')
        if (this.myTeamId === this.leaveTeamId) this.myTeamId = null
        await this.refreshMySubmissions()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        this.$message.error('退队失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    async handleStudentTeamInviteMember () {
      if (!this.isCurrentTeamCaptain) {
        this.$message.warning('仅队长可邀请队员')
        return
      }
      if (!this.myTeamId) {
        this.$message.warning('请先确认队伍ID')
        return
      }
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      const studentId = Number(this.studentTeamInviteId)
      if (!Number.isFinite(studentId) || studentId <= 0) {
        this.$message.warning('请填写有效的学生用户ID')
        return
      }
      this.teamLoading = true
      try {
        await inviteCompetitionTeamMember(this.myTeamId, studentId)
        this.$message.success('邀请成功，学生已入队')
        this.studentTeamInviteId = null
        await this.refreshActiveCompetitionMyEnrollKind()
      } catch (e) {
        this.$message.error('邀请失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    async handleStudentTeamRemoveMember () {
      if (!this.isCurrentTeamCaptain) {
        this.$message.warning('仅队长可移除队员')
        return
      }
      if (this.competitionTeamRemoveMemberBlocked) {
        this.$message.warning(this.competitionTeamRemoveMemberBlockedMessage || '当前不可移除队员')
        return
      }
      if (!this.myTeamId) {
        this.$message.warning('请先确认队伍ID')
        return
      }
      const userId = Number(this.studentTeamRemoveMemberId)
      if (!Number.isFinite(userId) || userId <= 0) {
        this.$message.warning('请填写待移除队员的用户ID')
        return
      }
      this.teamLoading = true
      try {
        await removeCompetitionTeamMember(this.myTeamId, userId)
        this.$message.success('已移除队员')
        this.studentTeamRemoveMemberId = null
        await this.refreshActiveCompetitionMyEnrollKind()
      } catch (e) {
        this.$message.error('移除失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    parseAltUserIds (text) {
      const raw = String(text || '').trim()
      if (!raw) return []
      return raw
        .split(/[,，\s]+/)
        .map(s => Number(String(s).trim()))
        .filter(n => Number.isFinite(n) && n > 0)
    },

    getTeamCreatorAdvisorId (team) {
      if (!team || typeof team !== 'object') return null
      const raw =
        team.created_by_advisor_id != null
          ? team.created_by_advisor_id
          : (team.created_by_advisor != null
            ? team.created_by_advisor
            : (team.advisor_id != null ? team.advisor_id : team.creator_advisor_id))
      const n = Number(raw)
      return Number.isFinite(n) && n > 0 ? n : null
    },

    isAdvisorCreatedTeamInSession (teamId) {
      if (teamId == null) return false
      return (this.advisorCreatedTeamIds || []).some(id => Number(id) === Number(teamId))
    },

    canAdvisorOperateTeam (team) {
      if (!team || typeof team !== 'object') return false
      if (this.isSuperAdmin) return true
      const teamId = team.id != null ? team.id : team.team_id
      if (this.isAdvisorCreatedTeamInSession(teamId)) return true
      if (!this.isUsingAltIdentity || !this.isAdvisorOrTeacher) return false
      if (!hasAltPermission('MANAGE_TEAMS')) return false
      const myId = this.altCurrentUserId
      if (myId == null) return true
      const creatorId = this.getTeamCreatorAdvisorId(team)
      if (creatorId == null) return true
      return Number(creatorId) === Number(myId)
    },

    assertCompetitionOpenForTeamCreateOrInvite (showToast = true) {
      if (!this.competitionTeamCreateInviteBlocked) return true
      if (showToast) {
        this.$message.warning(this.competitionTeamCreateInviteBlockedDescription || '当前不可进行该操作')
      }
      return false
    },

    normalizeCompetitionTeamsList (res) {
      return normalizeCompetitionApiList(res)
    },

    async refreshAdvisorTeams () {
      if (!this.showAdvisorTeamPanel || !this.activeCompetitionId) return
      this.advisorTeamsLoading = true
      try {
        const res = await getCompetitionTeams(this.activeCompetitionId)
        this.advisorTeams = this.normalizeCompetitionTeamsList(res)
        if (
          this.advisorSelectedTeamId != null &&
          !this.advisorTeams.some(t => Number(t.id) === Number(this.advisorSelectedTeamId))
        ) {
          this.advisorSelectedTeamId = null
          this.advisorRenameName = ''
        }
      } catch (e) {
        this.advisorTeams = []
        this.$message.error('获取队伍列表失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorTeamsLoading = false
      }
    },

    selectAdvisorTeam (teamId) {
      this.advisorSelectedTeamId = teamId
      const t = this.advisorSelectedTeam
      this.advisorRenameName = t && t.name != null ? String(t.name) : ''
      this.advisorInviteStudentId = null
    },

    async handleAdvisorCreateTeam () {
      if (!this.activeCompetitionId) return
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      if (!this.allowTeam) {
        this.$message.error('该竞赛不允许团队参赛')
        return
      }
      const memberIds = this.parseAltUserIds(this.advisorCreateForm.initial_member_ids_text)
      if (!memberIds.length) {
        this.$message.warning('请填写至少一名队员的学生 ID（alt_auth_users.id）')
        return
      }
      const uniqueIds = [...new Set(memberIds)]
      let captainId = this.advisorCreateForm.captain_student_id
      if (captainId == null || captainId === '') {
        captainId = uniqueIds[0]
      } else {
        captainId = Number(captainId)
      }
      if (!uniqueIds.includes(captainId)) {
        this.$message.warning('队长 ID 必须在队员 ID 列表中')
        return
      }
      const payload = {
        competition_id: Number(this.activeCompetitionId),
        initial_member_ids: uniqueIds,
        captain_student_id: captainId
      }
      const teamName = (this.advisorCreateForm.name || '').trim()
      if (teamName) payload.name = teamName

      this.advisorCreateLoading = true
      try {
        const team = await createCompetitionTeam(payload)
        const teamId = team && (team.id != null ? team.id : team.team_id)
        if (teamId != null) {
          const tid = Number(teamId)
          if (Number.isFinite(tid) && !this.advisorCreatedTeamIds.includes(tid)) {
            this.advisorCreatedTeamIds.push(tid)
          }
        }
        this.$message.success('队伍创建成功' + (teamId ? `，队伍 ID：${teamId}` : ''))
        this.advisorCreateForm = { name: '', captain_student_id: null, initial_member_ids_text: '' }
        await this.refreshAdvisorTeams()
        if (teamId) this.selectAdvisorTeam(teamId)
      } catch (e) {
        this.$message.error('创建队伍失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorCreateLoading = false
      }
    },

    async handleAdvisorRenameTeam () {
      const team = this.advisorSelectedTeam
      if (!team || !this.canOperateAdvisorSelectedTeam) return
      this.advisorTeamOpLoading = true
      try {
        const name = this.advisorRenameName != null ? String(this.advisorRenameName) : ''
        await patchCompetitionTeam(team.id, { name })
        this.$message.success('队名已更新')
        await this.refreshAdvisorTeams()
        this.selectAdvisorTeam(team.id)
      } catch (e) {
        this.$message.error('修改队名失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorTeamOpLoading = false
      }
    },

    async handleAdvisorInviteMember () {
      const team = this.advisorSelectedTeam
      if (!team || !this.canOperateAdvisorSelectedTeam) return
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      const studentId = Number(this.advisorInviteStudentId)
      if (!Number.isFinite(studentId) || studentId <= 0) {
        this.$message.warning('请填写有效的学生 ID')
        return
      }
      this.advisorTeamOpLoading = true
      try {
        await inviteCompetitionTeamMember(team.id, studentId)
        this.$message.success('邀请成功，学生已入队并完成报名')
        this.advisorInviteStudentId = null
        await this.refreshAdvisorTeams()
        this.selectAdvisorTeam(team.id)
      } catch (e) {
        this.$message.error('邀请失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorTeamOpLoading = false
      }
    },

    async handleAdvisorRemoveMember (teamId, userId) {
      if (!teamId || userId == null) return
      if (this.competitionTeamRemoveMemberBlocked) {
        this.$message.warning(this.competitionTeamRemoveMemberBlockedMessage || '当前不可移除队员')
        return
      }
      const team = (this.advisorTeams || []).find(t => Number(t.id) === Number(teamId))
      if (!this.canAdvisorOperateTeam(team)) {
        this.$message.warning('无权管理该队伍')
        return
      }
      try {
        await this.$confirm({
          title: '确认移除队员',
          content: `确定将用户 ID ${userId} 从队伍 ${teamId} 中移除吗？其本竞赛报名将变为退赛状态。`,
          okText: '移除',
          okType: 'danger',
          cancelText: '取消'
        })
      } catch {
        return
      }
      this.advisorTeamOpLoading = true
      this.advisorRemovingUserId = userId
      try {
        await removeCompetitionTeamMember(teamId, userId)
        this.$message.success('已移除队员')
        await this.refreshAdvisorTeams()
        this.selectAdvisorTeam(teamId)
      } catch (e) {
        this.$message.error('移除失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorTeamOpLoading = false
        this.advisorRemovingUserId = null
      }
    },

    handleFileChange (e) {
      const file = e && e.target && e.target.files ? e.target.files[0] : null
      this.submissionForm.file = file || null
    },

    buildSubmissionTeamId () {
      if (this.submissionMode !== 'team') return null
      if (this.submissionTeamId) return this.submissionTeamId
      if (this.myTeamId) return this.myTeamId
      return null
    },

    async handleSubmitSubmission () {
      if (!this.activeCompetitionId) return
      if (this.enrollModalSubmissionLocked) {
        const trackLabel = this.submissionMode === 'team' ? '队伍' : '个人'
        this.$message.warning(`本报名周期${trackLabel}赛道已提交作品，无法再次提交；退赛后重新报名可提交新作品`)
        return
      }
      if (this.submissionMode === 'individual' && !this.myEnrolledIndividual) {
        this.$message.warning('请先完成个人报名后再提交个人作品')
        return
      }
      if (this.submissionMode === 'team' && !this.myEnrolledTeam) {
        this.$message.warning('请先完成队伍报名后再提交队伍作品')
        return
      }
      if (this.submissionMode === 'team' && !this.isCurrentTeamCaptain) {
        this.$message.warning('当前账号为队员，只有队长可以提交队伍作品')
        return
      }
      const title = (this.submissionForm.title || '').trim()
      if (!title) {
        this.$message.error('请填写作品标题')
        return
      }

      if (this.submissionMode === 'individual' && !this.allowIndividual) {
        this.$message.error('该竞赛不允许个人提交')
        return
      }
      if (this.submissionMode === 'team' && !this.allowTeam) {
        this.$message.error('该竞赛不允许队伍提交')
        return
      }

      const contentText = (this.submissionForm.content_text || '').trim()
      const file = this.submissionForm.file || null
      if (!contentText && !file) {
        this.$message.error('请至少提供“文本内容”或“文件”')
        return
      }

      const teamId = this.buildSubmissionTeamId()
      if (this.submissionMode === 'team' && !teamId) {
        this.$message.error('队伍提交需要 team_id（请填写队伍ID或先创建队伍）')
        return
      }

      this.submitLoading = true
      try {
        if (file) {
          const formData = new FormData()
          formData.append('competition_id', this.activeCompetitionId)
          if (teamId) formData.append('team_id', teamId)
          formData.append('title', title)
          if (this.submissionForm.description) formData.append('description', this.submissionForm.description)
          if (contentText) formData.append('content_text', contentText)
          formData.append('file', file)
          await uploadCompetitionSubmission(formData)
        } else {
          await submitCompetitionSubmission({
            competition_id: this.activeCompetitionId,
            team_id: this.submissionMode === 'team' ? teamId : null,
            title: title,
            description: this.submissionForm.description || null,
            content_text: contentText
          })
        }

        this.$message.success('提交成功')
        this.resetSubmissionFormFields()
        clearCompetitionWithdrawSubmissionCutoff(this.activeCompetitionId)
        this.ignoreSubmissionsBeforeReenrollAt = null
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        this.$message.error('提交失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.submitLoading = false
      }
    },

    async refreshMySubmissions () {
      if (!this.activeCompetitionId) return
      this.submissionsLoading = true
      try {
        const res = await getCompetitionSubmissions(this.activeCompetitionId)
        if (Array.isArray(res)) this.mySubmissions = res
        else if (res && Array.isArray(res.items)) this.mySubmissions = res.items
        else this.mySubmissions = []
      } catch (e) {
        this.mySubmissions = []
        this.$message.error('获取作品列表失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.submissionsLoading = false
      }
    },

    async downloadSubmission (submissionId) {
      if (!submissionId) return
      try {
        const blob = await downloadCompetitionSubmissionFile(submissionId)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `submission_${submissionId}.bin`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } catch (e) {
        this.$message.error('下载失败：' + (e && e.message ? e.message : '未知错误'))
      }
    },

    /** 从对象中取出分数字段（兼容多套后端命名） */
    pickScoreFromObject (obj) {
      if (!obj || typeof obj !== 'object') return null
      const keys = ['score', 'numeric_score', 'value', 'points']
      for (const k of keys) {
        if (!(k in obj)) continue
        const v = obj[k]
        if (v !== null && v !== undefined && v !== '') return v
      }
      return null
    },

    /** 作品详情接口可能包一层 data / payload */
    unwrapSubmissionApiPayload (payload) {
      if (!payload || typeof payload !== 'object') return payload
      let p = payload
      const innerData = p.data
      if (innerData != null && typeof innerData === 'object' && !Array.isArray(innerData)) {
        p = { ...p, ...innerData }
      }
      const innerPayload = p.payload
      if (innerPayload != null && typeof innerPayload === 'object' && !Array.isArray(innerPayload)) {
        p = { ...p, ...innerPayload }
      }
      return p
    },

    /** 8.20 / 8.16.2：优先顶层 score；为 null 时再读 review / reviews[]（列表常带 score:null + review.score） */
    resolveSubmissionScoreRaw (row) {
      if (!row || typeof row !== 'object') return null
      const top = row.score
      if (top !== null && top !== undefined && top !== '') return top
      const fromReview = this.pickScoreFromObject(row.review)
      if (fromReview != null) return fromReview
      for (const key of ['review_grade', 'grade', 'grading', 'review_detail']) {
        const nested = this.pickScoreFromObject(row[key])
        if (nested != null) return nested
      }
      const revs = row.reviews
      if (Array.isArray(revs)) {
        for (let i = revs.length - 1; i >= 0; i--) {
          const x = revs[i]
          const xs = this.pickScoreFromObject(x)
          if (xs != null) return xs
        }
      }
      return null
    },

    /** 归一化 §8.16.2 列表项（兼容 { submission, review }、data/payload 包裹） */
    normalizeAdminSubmissionRow (raw) {
      if (!raw || typeof raw !== 'object') return raw
      const top = this.unwrapSubmissionApiPayload(raw)
      if (!top || typeof top !== 'object') return top
      const sub = top.submission && typeof top.submission === 'object' ? top.submission : null
      if (sub) {
        const row = { ...sub }
        if (top.review) row.review = top.review
        if (top.score != null && row.score == null) row.score = top.score
        if (top.feedback != null && row.feedback == null) row.feedback = top.feedback
        if (top.reviewed_at && !row.reviewed_at) row.reviewed_at = top.reviewed_at
        return row
      }
      return top
    },

    /** 解析 §8.17 / §8.17.1 ReviewResponse（PUT/PATCH/GET review-grade） */
    normalizeReviewGradeResponse (raw) {
      const p = this.unwrapSubmissionApiPayload(raw)
      if (!p || typeof p !== 'object') return null
      const score = this.pickScoreFromObject(p)
      if (score == null) return null
      return {
        score,
        feedback: p.feedback != null && p.feedback !== '' ? String(p.feedback) : '',
        reviewed_at: p.reviewed_at != null ? p.reviewed_at : null
      }
    },

    /** 将 ReviewResponse 合并到作品列表行并写入本地缓存 */
    applyReviewGradeToAdminSubmission (submissionId, reviewRes) {
      const review = this.normalizeReviewGradeResponse(reviewRes)
      if (!review) return
      saveSubmissionReviewGradeCache(submissionId, review)
      const idx = this.adminSubmissions.findIndex(s => Number(s.id) === Number(submissionId))
      if (idx < 0) return
      const row = this.adminSubmissions[idx]
      const next = {
        ...row,
        score: review.score,
        feedback: review.feedback,
        reviewed_at: review.reviewed_at || row.reviewed_at,
        review: {
          ...(row.review && typeof row.review === 'object' ? row.review : {}),
          score: review.score,
          feedback: review.feedback,
          reviewed_at: review.reviewed_at
        }
      }
      this.$set(this.adminSubmissions, idx, next)
    },

    applyCachedReviewGradeToAdminSubmission (submissionId) {
      const cached = getSubmissionReviewGradeCache(submissionId)
      if (!cached) return false
      this.applyReviewGradeToAdminSubmission(submissionId, cached)
      return true
    },

    /** 已评分但列表无 score：GET review-grade（§8.17.2）或本地缓存；作品 GET 不含成绩 */
    async enrichAdminSubmissionsScores () {
      const list = this.adminSubmissions || []
      const needIds = list
        .filter(s => s && s.id != null && this.isSubmissionGraded(s) && this.resolveSubmissionScoreRaw(s) == null)
        .map(s => s.id)
      if (!needIds.length) return
      needIds.forEach((id) => {
        this.applyCachedReviewGradeToAdminSubmission(id)
      })
      const stillNeed = needIds.filter(id => {
        const row = this.adminSubmissions.find(s => Number(s.id) === Number(id))
        return row && this.resolveSubmissionScoreRaw(row) == null
      })
      if (!stillNeed.length) return
      await Promise.all(stillNeed.map(async (id) => {
        try {
          const res = await getCompetitionSubmissionReviewGrade(id)
          this.applyReviewGradeToAdminSubmission(id, res)
        } catch (_) {
          /* 无 GET 或 404 时依赖缓存 */
        }
      }))
    },

    /** @deprecated 使用 applyReviewGradeToAdminSubmission */
    patchAdminSubmissionScore (submissionId, score, feedback) {
      this.applyReviewGradeToAdminSubmission(submissionId, {
        score,
        feedback: feedback != null ? feedback : '',
        reviewed_at: null
      })
    },

    /** 将 8.20 的 score 格式化为表格「成绩」列展示文案 */
    formatScoreCell (row) {
      const v = this.resolveSubmissionScoreRaw(row)
      if (v == null || v === '') return '—'
      const n = typeof v === 'number' ? v : Number(v)
      return Number.isFinite(n) ? String(n) : String(v)
    },

    /** 归一化 GET scores/me 响应体（含可选嵌套 data） */
    normalizeScoresMeResponse (res) {
      if (!res || typeof res !== 'object') {
        return { competition_id: null, submissions: [] }
      }
      if (Array.isArray(res.submissions)) {
        return {
          competition_id: res.competition_id != null ? res.competition_id : null,
          submissions: res.submissions
        }
      }
      const inner = res.data
      if (inner && typeof inner === 'object' && Array.isArray(inner.submissions)) {
        return {
          competition_id: inner.competition_id != null ? inner.competition_id : null,
          submissions: inner.submissions
        }
      }
      return {
        competition_id: res.competition_id != null ? res.competition_id : null,
        submissions: []
      }
    },

    /**
     * 拉取 GET .../scores/me（8.20），以响应中的 submissions 为「我的成绩」表格数据源。
     */
    async refreshMyScores (showModal = false, options = {}) {
      const skipSubmissionsRefresh = !!(options && options.skipSubmissionsRefresh)
      if (!this.activeCompetitionId) return
      if (!this.isStudent) {
        this.myScores = null
        this.showMyScoresModal = false
        return
      }

      if (!skipSubmissionsRefresh) {
        await this.refreshMySubmissions()
      }

      this.scoresLoading = true
      try {
        const res = await getMyCompetitionScores(this.activeCompetitionId)
        const { competition_id: cid, submissions } = this.normalizeScoresMeResponse(res)
        this.myScores = {
          competition_id: cid != null ? cid : this.activeCompetitionId,
          submissions
        }
        if (showModal) {
          this.showMyScoresModal = true
          if (submissions.length === 0) {
            this.$message.info('当前竞赛暂无成绩相关提交记录，或教师尚未完成评分审核。')
          }
        }
      } catch (e) {
        this.myScores = null
        this.showMyScoresModal = false
        const status = e && e.response && e.response.status
        if (status === 403) {
          return
        }
        this.$message.error('获取成绩失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.scoresLoading = false
      }
    },

    revokeCreateQrPreviewUrl () {
      if (this.createQrBlobUrl) {
        try {
          URL.revokeObjectURL(this.createQrBlobUrl)
        } catch (e) { /* noop */ }
        this.createQrBlobUrl = null
      }
    },

    resetCreateCompetitionForm () {
      this.revokeCreateQrPreviewUrl()
      this.createCompetitionQrFile = null
      this.qrCodeFileList = []
      this.qrCodeValidating = false
      this.createCompetitionForm = {
        name: '',
        description: '',
        rules_text: '',
        start_at: '',
        end_at: '',
        allow_individual: true,
        allow_team: true
      }
    },

    handleQrCodeRemove () {
      this.revokeCreateQrPreviewUrl()
      this.createCompetitionQrFile = null
      this.qrCodeFileList = []
      return true
    },

    /** 创建/修改竞赛：格式、大小、二维码内容校验（与 §8.1 / §8.3 一致） */
    async validateCompetitionQrImageFile (file) {
      const MAX = 5 * 1024 * 1024
      const allowed = ['image/png', 'image/jpeg', 'image/jpg', 'image/pjpeg', 'image/gif', 'image/webp']
      if (!allowed.includes(file.type)) {
        this.$message.warning('仅支持 png、jpeg、gif、webp 格式的图片')
        return false
      }
      if (file.size > MAX) {
        this.$message.warning('二维码图片不能超过 5MB')
        return false
      }
      try {
        const ok = await validateImageContainsQrCode(file)
        if (!ok) {
          this.$message.warning('该图片中未识别到有效二维码，请上传包含清晰可扫的二维码图片')
          return false
        }
        return true
      } catch (e) {
        this.$message.warning('二维码校验失败：' + (e && e.message ? e.message : '未知错误'))
        return false
      }
    },

    async beforeQrCodeUpload (file) {
      this.qrCodeValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeCreateQrPreviewUrl()
        const url = URL.createObjectURL(file)
        this.createQrBlobUrl = url
        this.createCompetitionQrFile = file
        this.qrCodeFileList = [{ uid: 'qr-1', name: file.name, status: 'done', url }]
      } finally {
        this.qrCodeValidating = false
      }
      return false
    },

    async handleCreateCompetition () {
      if (!this.canManageCompetitions) return
      const toISO = (value) => {
        if (!value) return null
        const d = new Date(value)
        if (Number.isNaN(d.getTime())) return null
        return d.toISOString()
      }
      const name = (this.createCompetitionForm.name || '').trim()
      const description = (this.createCompetitionForm.description || '').trim()
      const rulesText = (this.createCompetitionForm.rules_text || '').trim()
      if (!name) {
        this.$message.warning('请填写竞赛名称')
        return
      }
      if (!description) {
        this.$message.warning('请填写简介')
        return
      }
      if (!rulesText) {
        this.$message.warning('请填写规则说明')
        return
      }
      if (!this.createCompetitionQrFile) {
        this.$message.warning('请上传竞赛二维码图片')
        return
      }

      this.adminCreateLoading = true
      try {
        const fd = new FormData()
        fd.append('name', name)
        fd.append('description', description)
        fd.append('rules_text', rulesText)
        const startAt = toISO(this.createCompetitionForm.start_at)
        const endAt = toISO(this.createCompetitionForm.end_at)
        if (startAt) fd.append('start_at', startAt)
        if (endAt) fd.append('end_at', endAt)
        fd.append('allow_individual', this.createCompetitionForm.allow_individual ? 'true' : 'false')
        fd.append('allow_team', this.createCompetitionForm.allow_team ? 'true' : 'false')
        fd.append('qr_code_image', this.createCompetitionQrFile, this.createCompetitionQrFile.name)

        const res = await createCompetitionMultipart(fd)
        this.$message.success('创建成功，竞赛ID：' + (res && res.id ? res.id : '未知'))
        this.showCreateCompetitionModal = false
        this.resetCreateCompetitionForm()
        this.fetchCompetitions()
      } catch (e) {
        this.$message.error('创建失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminCreateLoading = false
      }
    },

    async handlePublish () {
      if (!this.canManageCompetitions) return
      if (!this.publishCompetitionId) return
      this.publishLoading = true
      try {
        await publishCompetition(this.publishCompetitionId)
        this.$message.success('发布成功')
        this.fetchCompetitions()
      } catch (e) {
        this.$message.error('发布失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.publishLoading = false
      }
    },

    toISOFromDateTimeLocal (value) {
      if (!value) return null
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return null
      return d.toISOString()
    },

    toDateTimeLocalValue (iso) {
      if (!iso) return ''
      const d = new Date(iso)
      if (Number.isNaN(d.getTime())) return ''
      // datetime-local 接收：YYYY-MM-DDTHH:mm（不带时区）
      return d.toISOString().slice(0, 16)
    },

    revokeEditCurrentQrObjectUrl () {
      if (this.editCurrentQrObjectUrl) {
        try {
          URL.revokeObjectURL(this.editCurrentQrObjectUrl)
        } catch (e) { /* noop */ }
        this.editCurrentQrObjectUrl = null
      }
    },

    resetEditCompetitionQrState () {
      if (this.editQrBlobUrl) {
        try {
          URL.revokeObjectURL(this.editQrBlobUrl)
        } catch (e) { /* noop */ }
        this.editQrBlobUrl = null
      }
      this.editCompetitionQrFile = null
      this.editQrCodeFileList = []
      this.editQrCodeValidating = false
      this.revokeEditCurrentQrObjectUrl()
      this.editCurrentQrLoading = false
    },

    handleEditQrCodeRemove () {
      if (this.editQrBlobUrl) {
        try {
          URL.revokeObjectURL(this.editQrBlobUrl)
        } catch (e) { /* noop */ }
        this.editQrBlobUrl = null
      }
      this.editCompetitionQrFile = null
      this.editQrCodeFileList = []
      return true
    },

    async beforeEditQrCodeUpload (file) {
      this.editQrCodeValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        if (this.editQrBlobUrl) {
          try {
            URL.revokeObjectURL(this.editQrBlobUrl)
          } catch (e) { /* noop */ }
        }
        const url = URL.createObjectURL(file)
        this.editQrBlobUrl = url
        this.editCompetitionQrFile = file
        this.editQrCodeFileList = [{ uid: 'edit-qr-1', name: file.name, status: 'done', url }]
      } finally {
        this.editQrCodeValidating = false
      }
      return false
    },

    async fetchEditCompetitionCurrentQr (competitionId) {
      this.revokeEditCurrentQrObjectUrl()
      if (!competitionId) return
      this.editCurrentQrLoading = true
      try {
        const blob = await getCompetitionQrCode(competitionId)
        if (blob && typeof blob.size === 'number' && blob.size > 0) {
          const t = (blob.type || '').toLowerCase()
          if (
            t.startsWith('image/') ||
            t === 'application/octet-stream' ||
            t === '' ||
            t === 'binary/octet-stream'
          ) {
            this.editCurrentQrObjectUrl = URL.createObjectURL(blob)
          }
        }
      } catch (e) {
        /* 无二维码或未配置 */
      } finally {
        this.editCurrentQrLoading = false
      }
    },

    buildEditCompetitionChanges () {
      const form = this.editCompetitionForm
      const o = this.editCompetitionOriginal
      const changes = {}

      if (o) {
        const name = (form.name || '').trim()
        if (name !== (o.name || '').trim()) changes.name = name

        const desc = form.description != null ? String(form.description) : ''
        if (desc !== (o.description != null ? String(o.description) : '')) changes.description = desc || null

        const rules = form.rules_text != null ? String(form.rules_text) : ''
        if (rules !== (o.rules_text != null ? String(o.rules_text) : '')) changes.rules_text = rules

        const startISO = this.toISOFromDateTimeLocal(form.start_at)
        if (startISO !== o.start_at) changes.start_at = startISO

        const endISO = this.toISOFromDateTimeLocal(form.end_at)
        if (endISO !== o.end_at) changes.end_at = endISO

        if (!!form.allow_individual !== o.allow_individual) changes.allow_individual = !!form.allow_individual
        if (!!form.allow_team !== o.allow_team) changes.allow_team = !!form.allow_team
      } else {
        const name = (form.name || '').trim()
        if (name) changes.name = name
        if (form.description !== '') changes.description = form.description || null
        if (form.rules_text !== '') changes.rules_text = form.rules_text || ''

        const startISO = this.toISOFromDateTimeLocal(form.start_at)
        if (startISO !== null) changes.start_at = startISO
        const endISO = this.toISOFromDateTimeLocal(form.end_at)
        if (endISO !== null) changes.end_at = endISO

        changes.allow_individual = !!form.allow_individual
        changes.allow_team = !!form.allow_team
      }

      return changes
    },

    appendEditCompetitionChangesToFormData (fd, changes) {
      Object.keys(changes).forEach((key) => {
        const v = changes[key]
        if (v === null || v === undefined) {
          fd.append(key, '')
        } else if (typeof v === 'boolean') {
          fd.append(key, v ? 'true' : 'false')
        } else {
          fd.append(key, String(v))
        }
      })
    },

    openEditCompetitionModal () {
      if (!this.canManageCompetitions) return
      const id = this.selectedCompetitionId || this.activeCompetitionId || this.publishCompetitionId
      if (!id) {
        this.$message.warning('请先在竞赛列表中选择要修改的竞赛')
        return
      }
      const comp =
        (this.competitions || []).find(c => Number(c.id) === Number(id)) ||
        this.activeCompetition ||
        null

      this.resetEditCompetitionQrState()
      this.editCompetitionId = id
      this.adminEditLoading = false
      this.showEditCompetitionModal = true
      void this.fetchEditCompetitionCurrentQr(id)

      const original = comp
        ? {
          name: comp.name || '',
          description: comp.description || '',
          rules_text: comp.rules_text || '',
          start_at: comp.start_at ? (new Date(comp.start_at)).toISOString() : null,
          end_at: comp.end_at ? (new Date(comp.end_at)).toISOString() : null,
          allow_individual: !!comp.allow_individual,
          allow_team: !!comp.allow_team
        }
        : null

      this.editCompetitionOriginal = original
      this.editCompetitionForm = {
        name: (comp && comp.name) || '',
        description: (comp && (comp.description || '')) || '',
        rules_text: (comp && (comp.rules_text || '')) || '',
        start_at: (comp && this.toDateTimeLocalValue(comp.start_at)) || '',
        end_at: (comp && this.toDateTimeLocalValue(comp.end_at)) || '',
        allow_individual: comp ? !!comp.allow_individual : false,
        allow_team: comp ? !!comp.allow_team : false
      }
    },

    async handleEditCompetition () {
      if (!this.canManageCompetitions) return
      if (!this.editCompetitionId) return

      const changes = this.buildEditCompetitionChanges()
      const hasQr = !!this.editCompetitionQrFile

      if (changes.name !== undefined && !changes.name) {
        this.$message.warning('竞赛名称不能为空')
        return
      }

      if (!hasQr && Object.keys(changes).length === 0) {
        this.$message.info('未检测到需要修改的字段')
        return
      }

      this.adminEditLoading = true
      try {
        if (hasQr) {
          const fd = new FormData()
          this.appendEditCompetitionChangesToFormData(fd, changes)
          fd.append('qr_code_image', this.editCompetitionQrFile, this.editCompetitionQrFile.name)
          await updateCompetitionMultipart(this.editCompetitionId, fd)
        } else {
          await updateCompetition(this.editCompetitionId, changes)
        }
        this.$message.success('修改成功')
        this.showEditCompetitionModal = false
        this.resetEditCompetitionQrState()
        this.fetchCompetitions()
      } catch (e) {
        this.$message.error('修改失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminEditLoading = false
      }
    },

    async handleDeleteCompetition () {
      if (!this.canManageCompetitions) return
      const id = this.activeCompetitionId || this.publishCompetitionId
      if (!id) return
      this.adminDeleteLoading = true
      try {
        await this.$confirm({
          title: '确认删除',
          content: '删除竞赛后不可恢复。确定要删除该竞赛吗？',
          okText: '删除',
          okType: 'danger',
          cancelText: '取消'
        })

        await deleteCompetition(id)
        this.$message.success('删除成功')
        this.fetchCompetitions()
      } catch (e) {
        // cancel 会走 reject，这里不提示
      } finally {
        this.adminDeleteLoading = false
      }
    },

    async handleLockCompetition () {
      if (!this.canManageCompetitions) return
      const id = this.activeCompetitionId || this.publishCompetitionId
      if (!id) return
      this.adminLockLoading = true
      try {
        await lockCompetition(id)
        this.$message.success('锁定成功（停止报名）')
        this.fetchCompetitions()
      } catch (e) {
        this.$message.error('锁定失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminLockLoading = false
      }
    },

    isSubmissionGraded (row) {
      if (!row || typeof row !== 'object') return false
      if (row.status === 'approved' || row.status === 'rejected') return true
      const st = row.status != null ? String(row.status).toLowerCase() : ''
      if (st === 'reviewed' || st === 'graded') return true
      if (row.reviewed_at) return true
      if (this.resolveSubmissionScoreRaw(row) != null) return true
      const r = row.review
      if (r && typeof r === 'object' && (r.reviewed_at || this.pickScoreFromObject(r) != null)) return true
      if (row.review_completed === true || row.is_reviewed === true || row.has_review === true) return true
      return false
    },

    resolveSubmissionFeedback (row) {
      if (!row || typeof row !== 'object') return ''
      if (row.feedback != null && row.feedback !== '') return String(row.feedback)
      const r = row.review
      if (r && typeof r === 'object' && r.feedback != null && r.feedback !== '') return String(r.feedback)
      const revs = row.reviews
      if (Array.isArray(revs)) {
        for (let i = revs.length - 1; i >= 0; i--) {
          const x = revs[i]
          if (x && typeof x === 'object' && x.feedback != null && x.feedback !== '') return String(x.feedback)
        }
      }
      return ''
    },

    async fillGradeForm (submissionId, isEdit = false) {
      if (!this.canReviewSubmissions) return
      const sub = this.adminSubmissions.find(s => Number(s.id) === Number(submissionId))
      this.gradeForm.submission_id = submissionId
      this.gradeFormIsEdit = !!isEdit

      let detail = sub
      if (this.gradeFormIsEdit && sub && this.resolveSubmissionScoreRaw(sub) == null) {
        const cached = getSubmissionReviewGradeCache(submissionId)
        if (cached) {
          detail = { ...sub, score: cached.score, feedback: cached.feedback, reviewed_at: cached.reviewed_at }
        } else {
          try {
            const reviewRes = await getCompetitionSubmissionReviewGrade(submissionId)
            const review = this.normalizeReviewGradeResponse(reviewRes)
            if (review) {
              detail = {
                ...sub,
                score: review.score,
                feedback: review.feedback,
                reviewed_at: review.reviewed_at
              }
            }
          } catch (_) {
            detail = sub
          }
        }
      }

      if (this.gradeFormIsEdit && detail) {
        const scoreRaw = this.resolveSubmissionScoreRaw(detail)
        this.gradeForm.score = scoreRaw != null ? String(scoreRaw) : ''
        this.gradeForm.feedback = this.resolveSubmissionFeedback(detail)
      } else {
        this.gradeForm.score = ''
        this.gradeForm.feedback = ''
      }

      this.showGradeAudit = true
    },

    cancelGradeAudit () {
      this.showGradeAudit = false
      this.gradeFormIsEdit = false
      this.gradeForm.submission_id = null
      this.gradeForm.score = ''
      this.gradeForm.feedback = ''
    },

    async handleReviewGrade () {
      if (!this.canReviewSubmissions) return
      if (!this.gradeForm.submission_id) return
      const scoreValue = parseFloat(this.gradeForm.score)
      if (Number.isNaN(scoreValue)) {
        this.$message.error('分数必须是数字，例如：95.0')
        return
      }

      const isEdit = this.gradeFormIsEdit
      if (isEdit) {
        try {
          await this.$confirm({
            title: '修改评分',
            content: '确定保存对该作品评分的修改吗？',
            okText: '确定',
            cancelText: '取消'
          })
        } catch {
          return
        }
      }

      this.gradeLoading = true
      const gradedSubmissionId = this.gradeForm.submission_id
      try {
        const payload = {
          score: scoreValue,
          feedback: this.gradeForm.feedback || ''
        }
        let reviewRes
        if (isEdit) {
          reviewRes = await patchCompetitionSubmissionReviewGrade(gradedSubmissionId, payload)
          this.$message.success('评分已更新')
        } else {
          reviewRes = await reviewCompetitionSubmissionGrade(gradedSubmissionId, payload)
          this.$message.success('评分提交成功')
        }
        const mergedReview = this.normalizeReviewGradeResponse(reviewRes) || {
          score: scoreValue,
          feedback: payload.feedback || '',
          reviewed_at: null
        }
        saveSubmissionReviewGradeCache(gradedSubmissionId, mergedReview)
        this.cancelGradeAudit()
        await this.refreshAdminSubmissions()
        this.applyReviewGradeToAdminSubmission(gradedSubmissionId, mergedReview)
      } catch (e) {
        const status = e && e.response && e.response.status
        const msg = (e && e.message) ? e.message : '未知错误'
        if (status === 400) {
          const notReviewed = /not reviewed|尚未评分|未评分/i.test(msg)
          if (notReviewed && isEdit) {
            this.$message.warning('该作品尚未评分，请先点击「评分」完成首次评分')
          }
          return
        }
        const friendlyMsg = !isEdit && /already|已评|重复|duplicate/i.test(msg)
          ? '该作品已评分，请刷新列表后点击「修改评分」'
          : msg
        this.$message.error((isEdit ? '修改评分失败：' : '评分失败：') + friendlyMsg)
      } finally {
        this.gradeLoading = false
      }
    },

    async refreshAdminSubmissions () {
      if (!this.canViewCompetitionSubmissions) return
      if (!this.activeCompetitionId) return
      this.adminSubmissionsLoading = true
      try {
        const cid = this.activeCompetitionId
        const [subRes, indRes, teamRes] = await Promise.all([
          getCompetitionSubmissions(cid),
          getCompetitionParticipantsIndividual(cid).catch(() => []),
          getCompetitionParticipantsTeams(cid).catch(() => [])
        ])
        const raw = normalizeCompetitionApiList(subRes).map(item => this.normalizeAdminSubmissionRow(item))
        const enrollIndex = buildEnrollmentVisibilityIndex(
          normalizeCompetitionApiList(indRes),
          normalizeCompetitionApiList(teamRes)
        )
        const visible = filterAdminSubmissionsByActiveEnrollments(raw, enrollIndex)
        this.adminSubmissionsHiddenByWithdrawCount = Math.max(0, raw.length - visible.length)
        this.adminSubmissions = visible
        await this.enrichAdminSubmissionsScores()
      } catch (e) {
        this.adminSubmissions = []
        this.adminSubmissionsHiddenByWithdrawCount = 0
        this.$message.error('获取作品列表失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminSubmissionsLoading = false
      }
    },

    /** @param {boolean} openModal 为 true 时打开汇总弹窗（仅用户点击「查看评分汇总」时使用） */
    async refreshScoresSummary (openModal = true) {
      if (!this.canViewScoreAnalytics) return
      if (!this.activeCompetitionId) return
      this.summaryLoading = true
      try {
        const res = await getCompetitionScoresSummary(this.activeCompetitionId)
        this.scoresSummary = res
        if (openModal) this.showScoresSummaryModal = true
      } catch (e) {
        this.scoresSummary = null
        this.$message.error('获取汇总失败：' + (e && e.message ? e.message : '未知错误'))
        if (openModal) this.showScoresSummaryModal = false
      } finally {
        this.summaryLoading = false
      }
    },

    openRankingsModal () {
      if (!this.canViewScoreAnalytics) return
      if (!this.activeCompetitionId) return
      this.showScoresRankingsModal = true
      this.refreshRankings()
    },

    async refreshRankings () {
      if (!this.canViewScoreAnalytics) return
      if (!this.activeCompetitionId) return
      this.rankingsLoading = true
      try {
        const limit = this.rankingsLimit != null && this.rankingsLimit !== '' ? this.rankingsLimit : 50
        const res = await getCompetitionRankings(this.activeCompetitionId, limit)
        this.scoresRankings = res
      } catch (e) {
        this.scoresRankings = null
        this.$message.error('获取排行榜失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.rankingsLoading = false
      }
    },

    participantEnrollmentStatusText (status) {
      const map = { enrolled: '已报名', cancelled: '已取消', withdrawn: '已退赛' }
      return map[status] || (status || '-')
    },

    participantTeamStatusText (status) {
      const map = { active: '活跃', cancelled: '已取消', withdrawn: '已退赛', left: '已退队' }
      return map[status] || (status || '-')
    },

    async refreshParticipantsIndividual () {
      if (!this.canViewParticipantsRoster) return
      if (!this.activeCompetitionId) return
      this.participantsIndividualLoading = true
      try {
        const res = await getCompetitionParticipantsIndividual(this.activeCompetitionId)
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        this.participantsIndividual = list.map(item => ({
          sequence_no: item.sequence_no != null ? item.sequence_no : '-',
          enrollment_id: item.enrollment_id,
          student_no: item.student_no || '-',
          full_name: item.full_name || item.real_name || item.username || '-',
          college: item.college || '-',
          grade: item.grade || '-',
          contact: item.contact || '-',
          status_text: this.participantEnrollmentStatusText(item.status),
          created_at: this.formatDateTime(item.created_at)
        }))
        this.showParticipantsIndividualModal = true
      } catch (e) {
        this.participantsIndividual = []
        this.showParticipantsIndividualModal = false
        this.$message.error('获取个人参赛者失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.participantsIndividualLoading = false
      }
    },

    async refreshParticipantsTeams () {
      if (!this.canViewParticipantsRoster) return
      if (!this.activeCompetitionId) return
      this.participantsTeamsLoading = true
      try {
        const res = await getCompetitionParticipantsTeams(this.activeCompetitionId)
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        this.participantsTeams = list.map(item => {
          const members = Array.isArray(item.members) ? item.members : []
          const captain = members.find(m => m && m.is_captain) || null
          const membersNames = members
            .map(m => (m && (m.full_name || m.username)) ? (m.full_name || m.username) : null)
            .filter(Boolean)

          return {
            sequence_no: item.sequence_no != null ? item.sequence_no : '-',
            team_id: item.id,
            captain_id: item.captain_id,
            captain_name: captain ? (captain.full_name || captain.username || captain.user_id || '-') : '-',
            members_summary: membersNames.length ? membersNames.join('，') : '-',
            status_text: this.participantTeamStatusText(item.status),
            created_at: this.formatDateTime(item.created_at)
          }
        })
        this.showParticipantsTeamsModal = true
      } catch (e) {
        this.participantsTeams = []
        this.showParticipantsTeamsModal = false
        this.$message.error('获取组队参赛者失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.participantsTeamsLoading = false
      }
    },

    async exportTeamsExcel () {
      if (!this.canManageCompetitions) return
      if (!this.activeCompetitionId) {
        this.$message.warning('请先选择竞赛')
        return
      }
      this.participantsTeamsExportLoading = true
      try {
        const blob = await exportCompetitionTeamsExcel(this.activeCompetitionId)
        if (!blob || (typeof blob.size === 'number' && blob.size <= 0)) {
          throw new Error('导出结果为空')
        }
        const filename = `competition_${this.activeCompetitionId}_teams.xlsx`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        this.$message.success('导出队伍信息成功')
      } catch (e) {
        this.$message.error('导出队伍信息失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.participantsTeamsExportLoading = false
      }
    }
  }
}
</script>

<style scoped lang="less">
.competition-system {
  width: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.competition-main-card {
  overflow: visible;
  border-radius: 10px;
}

/* 竞赛列表（非独立详情）：去掉深色底与背景图，保证表格文字可读 */
.competition-main-card:not(.competition-main-card--standalone) {
  ::v-deep > .ant-card-body {
    background-color: #fff;
    background-image: none;
  }
}

/* 独立详情：最外层卡片内容区深色渐变 + 背景图（不作用于内层 sub-card 的 body） */
.competition-main-card--standalone {
  ::v-deep > .ant-card-body {
    background-color: #0a0618;
    background-image:
      linear-gradient(
        155deg,
        rgba(14, 8, 32, 0.93) 0%,
        rgba(26, 12, 48, 0.88) 42%,
        rgba(8, 6, 22, 0.94) 100%
      ),
      url('~@/assets/背景图.jpeg');
    background-repeat: no-repeat, no-repeat;
    background-size: cover, cover;
    background-position: center, center;
  }
}

.competition-detail-below-list {
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
  min-height: 360px;
}

.competition-detail-below-list--solo {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
  min-height: 400px;
}

/* 独立详情页：学生/教师 竞赛信息及管理区表格、卡片背景透明（透出外层主卡片底图） */
.competition-detail-transparent-tables {
  ::v-deep .competition-info-card.ant-card,
  ::v-deep .competition-info-card > .ant-card-head,
  ::v-deep .competition-info-card > .ant-card-body {
    background: transparent !important;
  }

  ::v-deep .competition-info-card > .ant-card-head {
    border-bottom-color: rgba(255, 255, 255, 0.22) !important;
  }

  ::v-deep .competition-info-card > .ant-card-head .ant-card-head-title {
    color: #fff !important;
  }

  ::v-deep .competition-info-card .ant-descriptions {
    color: #fff;
  }

  ::v-deep .competition-info-card .ant-descriptions-bordered .ant-descriptions-view > table,
  ::v-deep .competition-info-card .ant-descriptions-bordered .ant-descriptions-item-label,
  ::v-deep .competition-info-card .ant-descriptions-bordered .ant-descriptions-item-content {
    background: transparent !important;
    color: #fff !important;
    border-color: rgba(255, 255, 255, 0.28) !important;
  }

  ::v-deep .competition-info-card .ant-descriptions-bordered table th,
  ::v-deep .competition-info-card .ant-descriptions-bordered table td {
    background: transparent !important;
    color: #fff !important;
    border-color: rgba(255, 255, 255, 0.28) !important;
  }

  /* 教师/管理员：作品列表、参赛者、评分汇总等 sub-card 整块透明 */
  ::v-deep .sub-card.ant-card {
    background: transparent !important;
    border-color: rgba(255, 255, 255, 0.22) !important;
  }

  ::v-deep .sub-card.ant-card > .ant-card-head,
  ::v-deep .sub-card.ant-card > .ant-card-body {
    background: transparent !important;
  }

  ::v-deep .sub-card.ant-card > .ant-card-head {
    border-bottom-color: rgba(255, 255, 255, 0.22) !important;
  }

  ::v-deep .sub-card.ant-card > .ant-card-head .ant-card-head-title {
    color: rgba(255, 255, 255, 0.96) !important;
  }

  ::v-deep .sub-card .ant-form-item-label > label {
    color: rgba(255, 255, 255, 0.88);
  }

  ::v-deep .sub-card .submission-item {
    border-color: rgba(255, 255, 255, 0.22) !important;
  }

  ::v-deep .sub-card .submission-title {
    color: rgba(255, 255, 255, 0.96);
  }

  ::v-deep .sub-card .submission-meta,
  ::v-deep .sub-card .muted {
    color: rgba(255, 255, 255, 0.72) !important;
  }

  ::v-deep .submission-item.ant-card {
    background: transparent !important;
  }

  ::v-deep .ant-table,
  ::v-deep .ant-table-thead > tr > th,
  ::v-deep .ant-table-tbody > tr > td {
    background: transparent !important;
  }

  ::v-deep .ant-table-thead > tr > th,
  ::v-deep .ant-table-tbody > tr > td {
    color: rgba(255, 255, 255, 0.92);
    border-color: rgba(255, 255, 255, 0.18) !important;
  }

  ::v-deep .ant-table-placeholder {
    background: transparent !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
  }

  ::v-deep .ant-table-bordered .ant-table-body > table,
  ::v-deep .ant-table-bordered .ant-table-header > table {
    border-color: rgba(255, 255, 255, 0.12);
  }

  ::v-deep .ant-divider-horizontal {
    border-top-color: rgba(255, 255, 255, 0.18);
  }

  ::v-deep .ant-empty {
    background: transparent;
  }

  ::v-deep .ant-empty-description {
    color: rgba(255, 255, 255, 0.65);
  }

  /* 指导老师：队伍列表表格、管理队伍区 — 文字白色；队员列表背景透明 */
  ::v-deep .advisor-teams-table {
    .ant-table,
    .ant-table-thead > tr > th,
    .ant-table-tbody > tr > td,
    .ant-table-placeholder {
      background: transparent !important;
      color: rgba(255, 255, 255, 0.92) !important;
      border-color: rgba(255, 255, 255, 0.18) !important;
    }

    .ant-table-thead > tr > th {
      font-weight: 600;
      color: #fff !important;
    }

    .ant-table-tbody > tr:hover > td {
      background: rgba(255, 255, 255, 0.06) !important;
    }

    .ant-pagination-item a,
    .ant-pagination-item-ellipsis,
    .ant-pagination-total-text,
    .ant-select-selection-selected-value {
      color: rgba(255, 255, 255, 0.88) !important;
    }

    .advisor-team-manage-btn.ant-btn-link {
      color: #69c0ff !important;
      pointer-events: auto;
    }

    .advisor-team-manage-btn.ant-btn-link:hover {
      color: #91d5ff !important;
    }
  }

  ::v-deep .advisor-manage-team-card.ant-card,
  ::v-deep .advisor-manage-team-card > .ant-card-head,
  ::v-deep .advisor-manage-team-card > .ant-card-body {
    background: transparent !important;
  }

  ::v-deep .advisor-manage-team-card > .ant-card-head {
    border-bottom-color: rgba(255, 255, 255, 0.18) !important;
  }

  ::v-deep .advisor-manage-team-card > .ant-card-head .ant-card-head-title {
    color: #fff !important;
  }

  ::v-deep .advisor-manage-team-card {
    .ant-descriptions,
    .ant-descriptions-item-label,
    .ant-descriptions-item-content {
      color: rgba(255, 255, 255, 0.92) !important;
    }

    .ant-descriptions-bordered .ant-descriptions-item-label,
    .ant-descriptions-bordered .ant-descriptions-item-content,
    .ant-descriptions-bordered table th,
    .ant-descriptions-bordered table td {
      background: transparent !important;
      color: rgba(255, 255, 255, 0.92) !important;
      border-color: rgba(255, 255, 255, 0.18) !important;
    }

    .muted,
    code {
      color: rgba(255, 255, 255, 0.72) !important;
    }

    .ant-btn-link {
      color: #69c0ff !important;
    }
  }

  /* 管理队伍：新队名、邀请学生 ID 表单项 — 标签与输入内容为黑色 */
  ::v-deep .advisor-manage-team-ops {
    .ant-form-item-label > label {
      color: #fdfcfc !important;
    }

    .ant-input,
    .ant-input-number,
    .ant-input-number-input {
      color: #000 !important;
      background: #fff !important;
      border-color: #d9d9d9 !important;
    }

    .ant-input::placeholder,
    .ant-input-number-input::placeholder {
      color: rgba(0, 0, 0, 0.45) !important;
    }

    .ant-input[disabled],
    .ant-input-number-disabled,
    .ant-input-number-disabled .ant-input-number-input {
      color: rgba(0, 0, 0, 0.45) !important;
      background: #f5f5f5 !important;
    }
  }

  ::v-deep .advisor-team-members-list {
    background: transparent;
    color: rgba(255, 255, 255, 0.92);
  }

  ::v-deep .advisor-team-members-label,
  ::v-deep .advisor-team-member-row {
    color: rgba(255, 255, 255, 0.92);
  }

  ::v-deep .advisor-team-member-row {
    border-bottom: 1px solid rgba(255, 255, 255, 0.14);
    background: transparent;
  }
}

/* 学生独立详情：赛题说明（深色网格底、霓虹描边、01/02 章节号、侧栏二维码） */
.competition-briefing-card {
  ::v-deep > .ant-card-body {
    padding: 0 0 4px;
  }
}

.competition-briefing {
  color: #fff;
  padding: 4px 4px 8px;
}

.competition-briefing__header {
  text-align: center;
  margin-bottom: 18px;
}

.competition-briefing__main-title {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #fff;
  text-shadow: 0 0 28px rgba(120, 200, 255, 0.35);
}

.competition-briefing__sub-en {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.35em;
  color: #5ecbff;
  text-transform: uppercase;
}

.competition-briefing__frame {
  position: relative;
  border: 1px solid rgba(120, 200, 255, 0.55);
  border-radius: 2px;
  box-shadow:
    0 0 0 1px rgba(180, 100, 255, 0.12),
    0 0 32px rgba(80, 160, 255, 0.22),
    inset 0 0 80px rgba(40, 20, 90, 0.35);
  background: linear-gradient(
    165deg,
    rgba(18, 10, 42, 0.92) 0%,
    rgba(12, 8, 36, 0.96) 55%,
    rgba(20, 8, 40, 0.94) 100%
  );
  overflow: hidden;
  clip-path: polygon(
    0 14px,
    14px 0,
    calc(100% - 18px) 0,
    100% 18px,
    100% calc(100% - 14px),
    calc(100% - 14px) 100%,
    18px 100%,
    0 calc(100% - 18px)
  );
}

.competition-briefing__frame::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: 0;
  width: 72px;
  height: 72px;
  pointer-events: none;
  opacity: 0.55;
  background: repeating-linear-gradient(
    -35deg,
    rgba(255, 120, 200, 0.35) 0 4px,
    rgba(120, 80, 255, 0.2) 4px 8px
  );
  mask-image: linear-gradient(135deg, transparent 40%, #000 72%);
  -webkit-mask-image: linear-gradient(135deg, transparent 40%, #000 72%);
}

.competition-briefing__grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.14;
  background-image:
    linear-gradient(rgba(160, 210, 255, 0.45) 1px, transparent 1px),
    linear-gradient(90deg, rgba(160, 210, 255, 0.45) 1px, transparent 1px);
  background-size: 22px 22px;
}

.competition-briefing__body {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: stretch;
  gap: 0;
  min-height: 220px;
}

.competition-briefing__col--main {
  flex: 1 1 0;
  min-width: 0;
  padding: 22px 22px 20px 26px;
  border-right: 1px solid rgba(255, 255, 255, 0.22);
}

.competition-briefing__col--aside {
  flex: 0 0 200px;
  max-width: 240px;
  padding: 22px 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.competition-briefing__aside-inner {
  width: 100%;
  text-align: center;
}

.competition-briefing__section {
  position: relative;
  margin-bottom: 22px;
  padding-left: 4px;
}

.competition-briefing__section-bg-num {
  position: absolute;
  left: -6px;
  top: -18px;
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  color: rgba(60, 180, 255, 0.22);
  letter-spacing: 0.02em;
  user-select: none;
  pointer-events: none;
}

.competition-briefing__section-title {
  position: relative;
  margin: 0 0 10px;
  padding-top: 8px;
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.08em;
}

.competition-briefing__section-text {
  position: relative;
  font-size: 13px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.9);
  white-space: pre-wrap;
}

.competition-briefing__footnotes {
  margin: 8px 0 0;
  padding-left: 1.1em;
  font-size: 12px;
  line-height: 1.65;
  color: rgba(230, 238, 255, 0.78);
  list-style: none;
}

.competition-briefing__footnotes li {
  position: relative;
  margin-bottom: 8px;
  padding-left: 0.5em;
}

.competition-briefing__footnotes li::before {
  content: '*';
  position: absolute;
  left: -0.85em;
  color: rgba(150, 210, 255, 0.85);
}

.competition-briefing__qr {
  display: block;
  width: 148px;
  height: 148px;
  margin: 0 auto 12px;
  object-fit: contain;
  border: 3px solid rgba(255, 255, 255, 0.92);
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  background: #fff;
}

.competition-briefing__qr-placeholder {
  width: 148px;
  height: 148px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(200, 220, 255, 0.65);
  border: 1px dashed rgba(160, 200, 255, 0.45);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.2);
}

.competition-briefing__aside-caption {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: #fff;
  margin-bottom: 14px;
}

.competition-briefing__contact {
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.88);
  text-align: left;
}

.competition-briefing__contact-num {
  font-weight: 700;
  letter-spacing: 0.04em;
}

.competition-briefing .muted-soft {
  color: rgba(210, 220, 255, 0.65);
  font-size: 12px;
  text-align: left;
}

@media (max-width: 900px) {
  .competition-briefing__body {
    flex-direction: column;
  }

  .competition-briefing__col--main {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.18);
    padding-bottom: 18px;
  }

  .competition-briefing__col--aside {
    flex: 1 1 auto;
    max-width: none;
    padding-top: 18px;
  }
}

/* 竞赛详情头图：无底色素块，透出独立详情页根节点背景图；文案保留浅色 + 阴影保证可读 */
.competition-hero-banner {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  margin-bottom: 20px;
  min-height: 200px;
  color: #fff;
  background: transparent;
  box-shadow: none;
}

.competition-hero-banner--solo {
  margin-bottom: 24px;
}

.competition-hero-banner__glow {
  display: none;
}

.competition-hero-banner__inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 28px 20px 32px;
  min-height: 200px;
  background: transparent;
}

.competition-hero-banner__inner--center {
  text-align: center;
}

.competition-hero-banner__copy {
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  min-width: 0;
}

.competition-hero-banner__year {
  display: block;
  margin-bottom: 8px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 0 24px rgba(120, 200, 255, 0.45);
}

.competition-hero-banner__title {
  margin: 0 0 12px;
  font-size: 26px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: 0.02em;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.75), 0 2px 24px rgba(0, 0, 0, 0.45);
}

@media (min-width: 768px) {
  .competition-hero-banner__title {
    font-size: 30px;
  }
}

.competition-hero-banner__title-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin: 0 0 16px;
}

.competition-hero-banner__title-en {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: rgba(230, 240, 255, 0.92);
  text-transform: none;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.65);
}

.competition-hero-banner__slogan {
  margin: 0 0 22px;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.06em;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.92);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.7);
}

.competition-hero-banner__dates {
  display: inline-flex;
  align-items: baseline;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 4px;
  padding-top: 0;
}

.competition-hero-banner__dates-label {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #1a0a12;
  background: linear-gradient(180deg, #ffe566 0%, #f5c400 100%);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.competition-hero-banner__dates-range {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.4);
}

.competition-hero-banner__id {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.88);
  letter-spacing: 0.04em;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.65);
}

.competition-hero-banner__status-tag {
  margin: 0;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(0, 0, 0, 0.2) !important;
}

.top-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.student-account-id-hint {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  white-space: nowrap;

  strong {
    color: rgba(0, 0, 0, 0.85);
    font-weight: 600;
  }
}

.manual-competition {
  display: flex;
  align-items: center;
  gap: 8px;
}

.muted {
  color: #999;
}

/* 当前勾选竞赛行高亮（教师/管理员） */
::v-deep tr.competition-table-row-active > td {
  background: #e6f7ff !important;
}

.competition-info-card {
  margin-bottom: 16px;
}

.empty-competitions {
  margin-top: 16px;
}

.sub-card {
  margin-bottom: 0px;
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.submissions-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 12px;
}

.submission-item {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.submission-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.submission-title {
  font-weight: 600;
  color: #222;
}

.json-view {
  max-height: 320px;
  overflow: auto;
  background: #fafafa;
  padding: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.standalone-modal-scroll {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding-right: 4px;
}

.standalone-modal-section-title {
  margin: 8px 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.standalone-modal-footer-actions {
  text-align: right;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.edit-competition-qr-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 8px;
}

.edit-competition-qr-empty {
  font-size: 12px;
  margin-bottom: 4px;
}

.edit-competition-current-qr {
  margin-bottom: 4px;
}

.edit-competition-current-qr__img {
  display: block;
  max-width: 200px;
  max-height: 200px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  object-fit: contain;
  background: #fafafa;
}

.edit-competition-qr-replace {
  margin-top: 12px;
}
</style>

<style lang="less">
/* Modal 挂载在 body，需非 scoped */
.standalone-competition-modal-wrap .ant-modal-body {
  padding-top: 8px;
}

/* 教师/管理员：参赛者名单、评分汇总、排行榜弹窗内表格透明（与独立详情深色底一致） */
.competition-admin-table-modal-wrap {
  .ant-modal-content {
    background: rgba(14, 10, 30, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45);
  }

  .ant-modal-header {
    background: transparent;
    border-bottom-color: rgba(255, 255, 255, 0.18);
  }

  .ant-modal-title {
    color: rgba(255, 255, 255, 0.95);
  }

  .ant-modal-body {
    background: transparent;
    color: rgba(255, 255, 255, 0.88);
  }

  .ant-modal-close {
    color: rgba(255, 255, 255, 0.75);
  }

  .ant-modal-close:hover {
    color: #fff;
  }

  .ant-table,
  .ant-table-thead > tr > th,
  .ant-table-tbody > tr > td {
    background: transparent !important;
    color: rgba(255, 255, 255, 0.92) !important;
    border-color: rgba(255, 255, 255, 0.16) !important;
  }

  .ant-table-thead > tr > th {
    font-weight: 600;
  }

  .ant-table-placeholder {
    background: transparent !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
  }

  .ant-pagination-item,
  .ant-pagination-prev .ant-pagination-item-link,
  .ant-pagination-next .ant-pagination-item-link {
    background: rgba(255, 255, 255, 0.06) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
  }

  .ant-pagination-item a,
  .ant-pagination-item-ellipsis {
    color: rgba(255, 255, 255, 0.85);
  }

  .ant-pagination-item-active {
    background: rgba(120, 90, 200, 0.35) !important;
  }

  .ant-pagination-total-text {
    color: rgba(255, 255, 255, 0.7);
  }

  .ant-select-selection {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.22) !important;
    color: rgba(255, 255, 255, 0.9);
  }

  .ant-empty-description {
    color: rgba(255, 255, 255, 0.65);
  }
}
</style>
