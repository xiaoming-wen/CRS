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

            <a-button
              style="margin-left: 8px"
              type="primary"
              ghost
              :disabled="!canPublishExamPaperForSelected"
              @click="openExamPaperPublishModal"
            >
              发布试卷
            </a-button>
          </template>
        </div>

        <div v-if="canManageCompetitions" class="muted" style="margin-top: 8px; font-size: 13px">
          请在表格左侧勾选一条竞赛，以便使用顶部「发布 / 修改 / 锁定 / 删除 / 发布试卷」等操作；完整管理与评阅请在「操作」列点击「查看详情」在新标签页打开。专家核验与按赛指派请使用左侧目录「专家指派」。竞赛发布后才可「发布试卷」与复制分享 URL。
        </div>
        <div v-else-if="isStudent" class="muted" style="margin-top: 8px; font-size: 13px">
          学生请在「操作」列点击「查看详情」；分本科/高职的竞赛需先选择组别，再在新标签页中报名与提交作品（不可跨组报名）。
        </div>
        <div v-else-if="showAdvisorTeamPanel" class="muted" style="margin-top: 8px; font-size: 13px">
          指导老师请在「操作」列点击「查看详情」，在详情页进行组班、邀请队员与管理队名。
        </div>
        <div v-else-if="isCompetitionExpert" class="muted" style="margin-top: 8px; font-size: 13px">
          专家请在「操作」列打开<strong>已指派</strong>的竞赛详情，进行作品评阅与评分。
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
          >
            <template slot="status" slot-scope="text">
              <a-tag
                :color="getStatusColor(text)"
                :style="text === 'draft' ? { color: '#000' } : null"
              >
                {{ getStatusText(text) }}
              </a-tag>
            </template>
            <template slot="stage" slot-scope="text">
              <a-tag v-if="text === 'preliminary'" color="blue">初赛</a-tag>
              <a-tag v-else-if="text === 'final'" color="purple">决赛</a-tag>
              <span v-else class="muted">—</span>
            </template>
            <template slot="listActions" slot-scope="text, record">
              <a @click.stop.prevent="openCompetitionDetailInNewTab(record.id)">查看详情</a>
              <template v-if="isSuperAdmin">
                <a-divider type="vertical" />
                <a
                  :class="{ 'competition-url-link--disabled': !isCompetitionShareableStatus(record && record.status) }"
                  @click.stop.prevent="openCompetitionUrlModal(record)"
                >URL</a>
              </template>
            </template>
          </a-table>
        </div>

      </template>

      <div
        v-if="showCompetitionDetailPanel && standaloneDetailMode"
        class="competition-detail-below-list competition-detail-transparent-tables"
        :class="{ 'competition-detail-below-list--solo': standaloneDetailMode }"
      >
        <!-- 详情头图：独立详情页（各角色统一展示） -->
        <div
          v-if="showStandaloneCompetitionBriefingLayout"
          class="competition-hero-banner"
          :class="{ 'competition-hero-banner--solo': standaloneDetailMode }"
        >
          <div class="competition-hero-banner__glow" aria-hidden="true" />
          <div class="competition-hero-banner__inner competition-hero-banner__inner--center">
            <div class="competition-hero-banner__copy">
              <div class="competition-hero-banner__title-wrap">
                <span
                  v-if="competitionHeroYear"
                  class="competition-hero-banner__year"
                  aria-hidden="true"
                >{{ competitionHeroYear }}</span>
                <h1 class="competition-hero-banner__title">
                  <template v-if="competitionHeroTitleParts.base">
                    <span class="competition-hero-banner__title-main">{{ competitionHeroTitleParts.base }}</span>
                    <span
                      v-if="competitionHeroTitleParts.stage"
                      class="competition-hero-banner__title-stage"
                      :class="'competition-hero-banner__title-stage--' + (activeCompetitionStage === 'final' ? 'final' : 'prelim')"
                    >{{ competitionHeroTitleParts.stage }}</span>
                  </template>
                  <template v-else>
                    {{ activeCompetition ? activeCompetition.name : `竞赛 #${activeCompetitionId}` }}
                  </template>
                </h1>
              </div>

              <div class="competition-hero-banner__capsules">
                <span
                  v-if="activeCompetition"
                  class="competition-hero-banner__capsule"
                  :class="'competition-hero-banner__capsule--status-' + (activeCompetition.status || 'unknown')"
                >
                  {{ getStatusText(activeCompetition.status) }}
                </span>
                <span
                  v-if="activeCompetitionStageLabel"
                  class="competition-hero-banner__capsule"
                  :class="activeCompetitionStage === 'final'
                    ? 'competition-hero-banner__capsule--stage-final'
                    : 'competition-hero-banner__capsule--stage-prelim'"
                >
                  {{ activeCompetitionStageLabel }}
                </span>
                <span
                  v-if="activeDivisionLabel"
                  class="competition-hero-banner__capsule competition-hero-banner__capsule--division"
                >
                  {{ activeDivisionLabel }}
                </span>
              </div>

              <a-alert
                v-if="finalStageAccessDenied"
                type="error"
                show-icon
                message="决赛仅限晋级队伍"
                description="您未在初赛晋级名单中，登录后仍无法报名、建队或提交决赛作品。"
                style="margin: 12px auto 0; text-align: left; max-width: 560px"
              />

              <p v-if="competitionHeroSubtitleEn" class="competition-hero-banner__title-en">{{ competitionHeroSubtitleEn }}</p>

              <div v-if="competitionHeroSloganParagraphs.length" class="competition-hero-banner__slogan">
                <p
                  v-for="(para, pi) in competitionHeroSloganParagraphs"
                  :key="'hs-' + pi"
                  class="competition-hero-banner__slogan-line"
                >
                  <template v-for="(seg, si) in highlightHeroSloganSegments(para)">
                    <mark
                      v-if="seg.hl"
                      :key="'hs-' + pi + '-' + si"
                      class="competition-hero-banner__kw"
                    >{{ seg.t }}</mark>
                    <span v-else :key="'hs-' + pi + '-' + si">{{ seg.t }}</span>
                  </template>
                </p>
              </div>

              <div v-if="activeCompetition" class="competition-hero-banner__dates">
                <span class="competition-hero-banner__dates-label">
                  <a-icon type="calendar" class="competition-hero-banner__dates-icon" />
                  活动时间
                </span>
                <span class="competition-hero-banner__dates-range">{{ competitionHeroDateRange }}</span>
                <span
                  v-if="competitionHeroTimeHint"
                  class="competition-hero-banner__time-hint"
                  :class="'competition-hero-banner__time-hint--' + competitionHeroTimeHint.tone"
                >
                  {{ competitionHeroTimeHint.text }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 独立详情：赛题说明（参考赛事说明页：双栏、网格底、章节编号） -->
        <a-card
          v-if="activeCompetition && showStandaloneCompetitionBriefingLayout"
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
                  <article
                    v-for="block in studentBriefingBlocks"
                    :key="block.num + block.title"
                    class="briefing-card"
                    :class="'briefing-card--' + (block.theme || 'default')"
                  >
                    <div class="briefing-card__head">
                      <span class="briefing-card__num" aria-hidden="true">{{ block.num }}</span>
                      <h3 class="briefing-card__title">{{ block.title }}</h3>
                    </div>

                    <!-- 参赛对象：导语 + 赛道分项 -->
                    <div v-if="block.kind === 'tracks' && block.tracks && block.tracks.length" class="briefing-tracks-wrap">
                      <div v-if="block.intro" class="briefing-card__text briefing-tracks__intro">{{ block.intro }}</div>
                      <div class="briefing-tracks">
                        <div
                          v-for="(track, ti) in block.tracks"
                          :key="ti"
                          class="briefing-track"
                          :class="'briefing-track--' + (ti % 3)"
                        >
                          <div class="briefing-track__name">{{ track.name }}</div>
                          <div class="briefing-track__body">{{ track.body }}</div>
                        </div>
                      </div>
                    </div>

                    <!-- 规则：图标列表 -->
                    <ul v-else-if="block.kind === 'list' && block.items && block.items.length" class="briefing-rule-list">
                      <li v-for="(item, ii) in block.items" :key="ii" class="briefing-rule-item">
                        <span class="briefing-rule-item__icon" aria-hidden="true">{{ item.icon }}</span>
                        <div class="briefing-rule-item__content">
                          <div class="briefing-rule-item__title">{{ item.title }}</div>
                          <div v-if="item.desc" class="briefing-rule-item__desc">{{ item.desc }}</div>
                        </div>
                      </li>
                    </ul>

                    <!-- 环境：表格 -->
                    <div v-else-if="block.kind === 'table' && block.table" class="briefing-env-table-wrap">
                      <table class="briefing-env-table">
                        <thead>
                          <tr>
                            <th v-for="(h, hi) in block.table.headers" :key="'h' + hi">{{ h }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, ri) in block.table.rows" :key="'r' + ri">
                            <td v-for="(cell, ci) in row" :key="'c' + ci">{{ cell }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <!-- 默认正文 -->
                    <div v-else class="briefing-card__text">{{ block.body }}</div>
                  </article>

                  <ul class="competition-briefing__footnotes">
                    <li>请勿使用未经授权的他人作品素材；提交作品即表示同意遵守主办方公布的赛事规则。</li>
                  </ul>
                </div>

                <div class="competition-briefing__col competition-briefing__col--aside">
                  <div class="briefing-aside-panel">
                    <div class="briefing-aside-panel__qr-wrap">
                      <img
                        v-if="studentBriefingQrSrc"
                        :src="studentBriefingQrSrc"
                        class="competition-briefing__qr"
                        :alt="studentBriefingQrAlt"
                      >
                      <div v-else class="competition-briefing__qr-placeholder">暂无二维码</div>
                    </div>
                    <div class="briefing-contact-card">
                      <div class="briefing-contact-card__label">联系人信息</div>
                      <template v-if="studentBriefingContactRows.length">
                        <div
                          v-for="row in studentBriefingContactRows"
                          :key="row.key"
                          class="briefing-contact-card__row"
                        >
                          <span class="briefing-contact-card__k">{{ row.label }}</span>
                          <span class="briefing-contact-card__v">{{ row.value }}</span>
                        </div>
                      </template>
                      <div v-else class="briefing-contact-card__empty">
                        联系方式请见群内公告或主办方通知
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </a-card>

        <a-card
          v-if="activeCompetition && showWorkbenchCompetitionInfoList"
          size="small"
          class="sub-card competition-info-card"
          :bordered="true"
          title="竞赛信息列表"
        >
          <a-descriptions :column="2" size="small" bordered>
            <a-descriptions-item label="竞赛ID">{{ activeCompetition.id }}</a-descriptions-item>
            <a-descriptions-item label="竞赛名称">{{ activeCompetition.name }}</a-descriptions-item>
            <a-descriptions-item label="简介" :span="2">{{ activeCompetition.description || '-' }}</a-descriptions-item>
            <a-descriptions-item label="规则说明" :span="2">{{ activeCompetition.rules_text || '-' }}</a-descriptions-item>
            <a-descriptions-item label="参赛对象" :span="2">{{ activeCompetition.target_audience || '-' }}</a-descriptions-item>
            <a-descriptions-item label="联系人">{{ activeCompetition.contact_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="联系方式">{{ activeCompetition.contact_phone || '-' }}</a-descriptions-item>
            <a-descriptions-item label="竞赛地点" :span="2">{{ activeCompetition.location || '-' }}</a-descriptions-item>
            <a-descriptions-item label="竞赛环境" :span="2">{{ activeCompetition.environment || '-' }}</a-descriptions-item>
            <a-descriptions-item label="开始时间">{{ formatDateTime(activeCompetition.start_at) }}</a-descriptions-item>
            <a-descriptions-item label="结束时间">{{ formatDateTime(activeCompetition.end_at) }}</a-descriptions-item>
            <a-descriptions-item label="状态">{{ getStatusText(activeCompetition.status) }}</a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ formatDateTime(activeCompetition.created_at) }}</a-descriptions-item>
            <a-descriptions-item label="更新时间" :span="2">{{ formatDateTime(activeCompetition.updated_at) }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-divider />

        <a-alert
          v-if="standaloneGuestMode"
          type="info"
          show-icon
          message="请先登录"
          description="登录后可报名、提交作品；指导老师登录后可在此页组班与管理队伍。请点击右上角「登录」或「注册」前往主页完成账号操作。"
          style="margin-top: 8px"
        />

        <!-- 学生区（非独立详情页：内联展示） -->
        <div v-if="isStudent && !standaloneDetailMode">
          <a-card size="small" class="sub-card" :bordered="true" title="报名">
            <a-alert
              v-if="enrollBlockedByOtherDivision"
              type="warning"
              show-icon
              message="无法在本组别报名"
              :description="enrollBlockedByOtherDivisionDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-else-if="competitionEnrollPublishBlocked || competitionEnrollmentClosed"
              type="warning"
              show-icon
              :message="competitionEnrollBlockedAlertTitle"
              :description="competitionEnrollBlockedAlertDescription"
              style="margin-bottom: 12px"
            />
            <a-form layout="vertical" class="enroll-profile-form" style="margin-top: 4px; max-width: 640px">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <a-form-item label="ID" :colon="false">
                    <a-input
                      :value="enrollProfileForm.student_no"
                      placeholder="用户 ID"
                      disabled
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

            <div class="muted" style="margin-bottom: 12px; font-size: 13px">
              {{ studentTeamEnrollFlowHint }}
            </div>

            <div class="row">
                <a-button
                  v-if="showStudentTeamCreateJoinOps"
                  type="primary"
                  :loading="enrollLoading"
                  @click="openStudentCreateTeamModal"
                  :disabled="competitionEnrollActionsDisabled || !allowTeam || studentHasTeamForCurrentCompetition || isActiveCompetitionFinal"
                  style="margin-right: 8px"
                >
                  创建队伍（自动队长）
                </a-button>
                <a-tag v-if="finalStagePromoted" color="green">已晋级 · 无需再报名</a-tag>
            </div>
            <p v-if="teamEnrollActionBlockedForMember" class="muted" style="margin: 8px 0 0; font-size: 13px">
              您已完成队伍报名且为队员，无需重复报名；创建队伍、加入队伍等操作已由队长负责。
            </p>

            <div style="margin-top: 12px">
              <a-form layout="vertical">
                <a-form-item v-if="showMultiTrackTeamSwitcher" label="当前操作赛道">
                  <a-radio-group
                    :value="activeEnrollmentWorkTrack"
                    @change="e => selectPreferredEnrollmentWorkTrack(e && e.target ? e.target.value : e)"
                  >
                    <a-radio
                      v-for="row in myTeamEnrollmentList"
                      :key="'trk-' + (row.id || row.team_id) + '-' + row.work_track"
                      :value="String(row.work_track || '').trim().toLowerCase()"
                    >
                      {{ workTrackDisplayLabel(row.work_track) }}（队伍 {{ row.team_id }}）
                    </a-radio>
                  </a-radio-group>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    切换赛道后，下方队伍 ID / 队名 / 校审 / 入队申请 / 队员与队长操作均对应该赛道队伍。
                  </div>
                </a-form-item>
                <a-form-item v-else-if="showCurrentTrackTeamContextHint" label="当前赛道">
                  <a-tag color="blue">{{ currentEnrollmentTrackLabel }}</a-tag>
                </a-form-item>
                <a-form-item :label="myTeamIdFormLabel">
                  <a-input-number
                    v-model="myTeamId"
                    :min="1"
                    placeholder="请先创建队伍或加入队伍"
                    style="width: 240px"
                    :disabled="true"
                  />
                </a-form-item>
                <a-alert
                  v-if="myTeamId && isMyTeamPendingSchoolReview"
                  type="warning"
                  show-icon
                  message="待校审"
                  description="队伍已创建，须本校校管理员在「校审」中审核通过（状态变为「已通过」）后，队员方可按题上传答案。"
                  style="margin-bottom: 12px"
                />
                <a-alert
                  v-else-if="myTeamId && isMyTeamSchoolReviewRejected"
                  type="error"
                  show-icon
                  message="校审已驳回"
                  description="该队伍未通过校审，相关组队报名已退赛。可重新「创建队伍」或「加入已有队伍」后再等待校审。"
                  style="margin-bottom: 12px"
                />
                <a-form-item v-if="showStudentTeamCreateJoinOps" label="加入已有队伍（输入队长提供的队伍ID）">
                  <div class="row">
                    <a-input-number
                      v-model="joinTeamId"
                      :min="eightDigitIdMin"
                      :max="eightDigitIdMax"
                      placeholder="8 位队伍ID"
                      style="width: 180px"
                      :disabled="competitionEnrollActionsDisabled || studentHasTeamForCurrentCompetition"
                    />
                    <a-button
                      :loading="teamLoading"
                      :disabled="competitionEnrollActionsDisabled || studentHasTeamForCurrentCompetition"
                      @click="handleJoinTeam"
                    >
                      申请加入队伍
                    </a-button>
                  </div>
                </a-form-item>
              </a-form>

              <template v-if="showStudentTeamCaptainOptionalOps">
              <a-divider />
              <a-form layout="vertical">
                <a-form-item label="队长转让（可选）">
                  <div class="row">
                    <a-input-number v-model="transferTeamId" :min="eightDigitIdMin" :max="eightDigitIdMax" placeholder="8 位队伍ID" style="width: 180px" :disabled="competitionTeamRosterLocked" />
                    <a-input
                      v-model="newCaptainRef"
                      placeholder="新队长姓名或用户 ID"
                      style="width: 200px"
                      allow-clear
                      :disabled="competitionTeamRosterLocked"
                    />
                    <a-button
                      :loading="teamLoading"
                      @click="handleTransferCaptain"
                      :disabled="competitionTeamRosterLocked || !transferTeamId || !(newCaptainRef && String(newCaptainRef).trim())"
                    >
                      转让
                    </a-button>
                  </div>
                </a-form-item>
                <a-form-item label="队长退队（可选，强制先转让）">
                  <div class="row">
                    <a-input-number v-model="leaveTeamId" :min="eightDigitIdMin" :max="eightDigitIdMax" placeholder="8 位队伍ID" style="width: 180px" :disabled="competitionTeamRosterLocked" />
                    <a-button
                      danger
                      :loading="teamLoading"
                      @click="handleLeaveTeam"
                      :disabled="competitionTeamRosterLocked || !leaveTeamId"
                    >
                      退队
                    </a-button>
                  </div>
                </a-form-item>
                <template v-if="isCurrentTeamCaptain">
                  <a-form-item label="邀请队员">
                    <div class="row">
                      <a-input
                        v-model="studentTeamInviteRef"
                        placeholder="队员姓名或用户 ID"
                        style="width: 220px"
                        allow-clear
                        :disabled="competitionTeamCreateInviteBlocked"
                      />
                      <a-button
                        type="primary"
                        :loading="teamLoading"
                        :disabled="competitionTeamCreateInviteBlocked || !(studentTeamInviteRef && String(studentTeamInviteRef).trim()) || !myTeamId"
                        @click="handleStudentTeamInviteMember"
                      >
                        邀请队员
                      </a-button>
                    </div>
                  </a-form-item>
                  <a-form-item label="移除队员">
                    <div class="row">
                      <a-input
                        v-model="studentTeamRemoveRef"
                        placeholder="队员姓名或用户 ID"
                        style="width: 220px"
                        allow-clear
                        :disabled="competitionTeamRemoveMemberBlocked"
                      />
                      <a-button
                        danger
                        :loading="teamLoading"
                        :disabled="competitionTeamRemoveMemberBlocked || !(studentTeamRemoveRef && String(studentTeamRemoveRef).trim()) || !myTeamId"
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
            v-if="hasAnyEnrollment && showZipSubmissionPanel"
            size="small"
            class="sub-card"
            :bordered="true"
            title="提交作品（压缩包）"
            style="margin-top: 16px"
          >
            <a-alert
              v-if="competitionSubmissionBlocked"
              type="warning"
              show-icon
              :message="competitionSubmissionBlockedTitle"
              :description="competitionSubmissionBlockedDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-else-if="teamSchoolReviewSubmissionBlocked"
              type="warning"
              show-icon
              :message="teamSchoolReviewBlockedTitle"
              :description="teamSchoolReviewBlockedDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-else
              type="info"
              show-icon
              message="作品赛道 · 压缩包提交"
              description="作品赛道请由队长上传作品压缩包（.zip）。软件 / 硬件赛道请使用分题答案上传。"
              style="margin-bottom: 12px"
            />
            <a-form layout="vertical" style="max-width: 640px">
              <a-form-item label="作品标题" required>
                <a-input v-model="submissionForm.title" placeholder="请输入作品标题" :disabled="submissionFormDisabled || !canSubmitZipPackage" />
              </a-form-item>
              <a-form-item label="作品说明">
                <a-textarea v-model="submissionForm.description" :rows="2" placeholder="选填" :disabled="submissionFormDisabled || !canSubmitZipPackage" />
              </a-form-item>
              <a-form-item label="作品压缩包" required>
                <input
                  type="file"
                  accept=".zip,application/zip"
                  :disabled="submissionFormDisabled || !canSubmitZipPackage"
                  @change="handleFileChange"
                />
                <div v-if="submissionForm.file" class="muted" style="margin-top: 6px">
                  已选：{{ submissionForm.file.name }}
                </div>
              </a-form-item>
              <a-button
                type="primary"
                :loading="submitLoading"
                :disabled="submissionFormDisabled || !canSubmitZipPackage"
                @click="handleSubmitSubmission"
              >
                提交作品
              </a-button>
              <p v-if="enrollModalSubmissionLocked" class="muted" style="margin-top: 8px; font-size: 13px; color: #389e0d">
                已提交作品
              </p>
              <p v-else-if="!canSubmitZipPackage && !competitionSubmissionBlocked && !teamSchoolReviewSubmissionBlocked" class="muted" style="margin-top: 8px; font-size: 13px">
                仅队长可提交队伍作品压缩包。
              </p>
            </a-form>
          </a-card>

          <a-card
            v-if="hasAnyEnrollment && showQuestionAnswerSubmissionPanel"
            size="small"
            class="sub-card"
            :bordered="true"
            :title="'题目答案上传（共' + submissionQuestionCount + '题）'"
            style="margin-top: 16px"
          >
            <a-alert
              v-if="competitionSubmissionBlocked"
              type="warning"
              show-icon
              :message="competitionSubmissionBlockedTitle"
              :description="competitionSubmissionBlockedDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-if="teamSchoolReviewSubmissionBlocked"
              type="warning"
              show-icon
              :message="teamSchoolReviewBlockedTitle"
              :description="teamSchoolReviewBlockedDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-else
              type="info"
              show-icon
              message="分题上传"
              description="每位队员可按自己负责的题目，分别向链接1～链接5上传答案文件；同题再次上传将覆盖。"
              style="margin-bottom: 12px"
            />
            <div class="row" style="margin-bottom: 12px">
              <a-button
                :loading="questionAnswersLoading"
                :disabled="!questionAnswerTeamId"
                @click="refreshQuestionAnswersBoard"
              >
                刷新上传状态
              </a-button>
            </div>
            <div class="question-answer-slots">
              <div
                v-for="slot in displayQuestionAnswerSlots"
                :key="'q-slot-' + slot.question_no"
                class="question-answer-slot"
              >
                <div class="question-answer-slot__title">
                  {{ slot.question_name || ('第' + slot.question_no + '题') }}
                  <a-tag v-if="slot.uploaded || slot.submitted" color="green" style="margin-left: 8px">提交</a-tag>
                  <a-tag v-else color="orange" style="margin-left: 8px">未提交</a-tag>
                </div>
                <div v-if="slot.answer && slot.answer.filename" class="muted" style="margin: 4px 0 8px">
                  当前文件：{{ slot.answer.filename }}
                  <span v-if="slot.answer.uploaded_at">（{{ formatDateTime(slot.answer.uploaded_at) }}）</span>
                </div>
                <div class="row" style="flex-wrap: wrap; gap: 8px; align-items: center">
                  <input
                    :ref="'inlineQFile_' + slot.question_no"
                    type="file"
                    class="question-answer-file-input"
                    :disabled="!canEditQuestionAnswerFiles || questionAnswerUploadingNo === slot.question_no"
                    @change="onQuestionAnswerFileChange($event, slot.question_no)"
                  />
                  <a-button
                    size="small"
                    :disabled="!canEditQuestionAnswerFiles || questionAnswerUploadingNo === slot.question_no"
                    :loading="questionAnswerUploadingNo === slot.question_no"
                    @click="triggerQuestionAnswerFilePick('inlineQFile_' + slot.question_no)"
                  >
                    选择文件
                  </a-button>
                  <a-button
                    v-if="slot.answer && slot.answer.id"
                    size="small"
                    @click="downloadQuestionAnswer(slot.answer.id)"
                  >
                    下载
                  </a-button>
                  <a-button
                    v-if="slot.answer && slot.answer.id"
                    size="small"
                    type="danger"
                    ghost
                    :loading="questionAnswerDeletingId === slot.answer.id"
                    :disabled="!canEditQuestionAnswerFiles"
                    @click="deleteQuestionAnswer(slot.answer.id, slot.question_no)"
                  >
                    删除
                  </a-button>
                </div>
              </div>
            </div>
            <div class="row" style="margin-top: 12px; justify-content: flex-end">
              <a-button
                type="primary"
                :loading="questionAnswersSubmitLoading"
                :disabled="!canFormalSubmitQuestionAnswers"
                @click="submitAllQuestionAnswers"
              >
                上传作品
              </a-button>
            </div>
            <p class="muted" style="margin: 8px 0 0; font-size: 12px; text-align: right">
              {{ questionAnswersSubmitHintText }}
            </p>
          </a-card>

          <a-card
            v-if="hasAnyEnrollment && showQuestionAnswerSubmissionPanel"
            size="small"
            class="sub-card"
            :bordered="true"
            title="题目答案状态"
            style="margin-top: 16px"
          >
            <a-empty v-if="!questionAnswerTeamId" description="请先完成组队报名并等待校审通过" />
            <div v-else class="question-answer-status-list">
              <div
                v-for="slot in displayQuestionAnswerSlots"
                :key="'status-q-' + slot.question_no"
                class="question-answer-status-row"
              >
                <span>{{ slot.question_name || ('第' + slot.question_no + '题') }}</span>
                <a-tag :color="(slot.uploaded || slot.submitted) ? 'green' : 'orange'" style="margin-left: 8px">
                  {{ (slot.uploaded || slot.submitted) ? '提交' : '未提交' }}
                </a-tag>
                <span v-if="slot.answer && slot.answer.filename" class="muted" style="margin-left: 8px">
                  {{ slot.answer.filename }}
                </span>
                <a-button
                  v-if="slot.answer && slot.answer.id"
                  size="small"
                  style="margin-left: 8px"
                  @click="downloadQuestionAnswer(slot.answer.id)"
                >
                  下载
                </a-button>
                <a-button
                  v-if="slot.answer && slot.answer.id"
                  size="small"
                  type="danger"
                  ghost
                  style="margin-left: 8px"
                  :loading="questionAnswerDeletingId === slot.answer.id"
                  :disabled="!canEditQuestionAnswerFiles"
                  @click="deleteQuestionAnswer(slot.answer.id, slot.question_no)"
                >
                  删除
                </a-button>
              </div>
            </div>
          </a-card>

        </div>

        <!-- 指导老师/教师：组班与队务（§8.12 / §8.12.1–§8.12.3） -->
        <div v-else-if="showAdvisorTeamPanel">
          <a-card size="small" class="sub-card" :bordered="true" title="组班与队务（指导老师）" style="margin-top: 16px">
            <a-alert
              v-if="advisorTeamBlockedByOtherDivision"
              type="warning"
              show-icon
              message="无法在本组别组班"
              :description="advisorTeamBlockedByOtherDivisionDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-else-if="competitionTeamCreateInviteBlocked"
              type="warning"
              show-icon
              :message="competitionTeamCreateInviteBlockedTitle"
              :description="competitionTeamCreateInviteBlockedDescription"
              style="margin-bottom: 12px"
            />
            <a-alert
              v-if="isActiveCompetitionDualDivision && activeViewDivision && !advisorTeamBlockedByOtherDivision"
              type="info"
              show-icon
              message="组别说明"
              :description="`当前为${activeDivisionLabel}详情页；建队与邀请队员仅限本组别学生，不可跨本科/高职混组。`"
              style="margin-bottom: 12px"
            />

            <a-alert
              type="info"
              show-icon
              message="组队校审说明"
              description="代建队成功后队伍状态为「待校审」，须本校校管理员审核通过（状态变为「已通过」）后，队员方可按题上传答案。"
              style="margin-bottom: 12px"
            />

            <a-divider orientation="left">创建队伍</a-divider>
            <a-form layout="vertical" style="max-width: 720px">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <a-form-item label="队名" required>
                    <a-input
                      v-model="advisorCreateForm.name"
                      placeholder="同竞赛内队名不可重复"
                      :maxLength="200"
                      :disabled="advisorTeamActionsDisabled || !allowTeam"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="指导老师">
                    <a-input
                      :value="altCurrentUserDisplayName"
                      disabled
                      placeholder="自动设为当前登录老师"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="赛道" required class="advisor-track-division-item">
                    <a-radio-group
                      v-model="advisorCreateForm.work_track"
                      class="advisor-form-radio-white"
                      :disabled="advisorTeamActionsDisabled"
                    >
                      <a-radio value="works">作品</a-radio>
                      <a-radio value="software">软件</a-radio>
                      <a-radio value="hardware">硬件</a-radio>
                    </a-radio-group>
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="组别" required class="advisor-track-division-item">
                    <a-radio-group
                      v-model="advisorCreateForm.division"
                      class="advisor-form-radio-white"
                      :disabled="advisorTeamActionsDisabled"
                    >
                      <a-radio value="undergraduate">本科</a-radio>
                      <a-radio value="vocational">高职</a-radio>
                    </a-radio-group>
                    <div class="division-choice-self-risk">请认真核对组别（本科 / 高职），选错后果自负。</div>
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12">
                  <a-form-item label="队长（姓名或 ID）">
                    <a-input
                      v-model="advisorCreateForm.captain_student"
                      placeholder="学生姓名或 8 位用户 ID"
                      :disabled="advisorTeamActionsDisabled || !allowTeam"
                      allow-clear
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="24">
                  <a-form-item label="初始队员（选填，姓名或 ID，逗号分隔）">
                    <a-input
                      v-model="advisorCreateForm.initial_members_text"
                      placeholder="选填；如：张三,李四 或 12345678,87654321"
                      :disabled="advisorTeamActionsDisabled || !allowTeam"
                      allow-clear
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button
                type="primary"
                :loading="advisorCreateLoading"
                :disabled="advisorTeamActionsDisabled || !allowTeam || !activeCompetitionId"
                @click="handleAdvisorCreateTeam"
              >
                创建队伍并拉入队员
              </a-button>
            </a-form>

            <a-divider orientation="left">队伍列表与队务</a-divider>
            <div class="row" style="margin-bottom: 12px">
              <a-button
                type="primary"
                :loading="advisorTeamsLoading"
                :disabled="!activeCompetitionId"
                @click="refreshAdvisorTeams"
              >
                刷新队伍列表
              </a-button>
            </div>
            <a-empty
              v-if="!advisorTeamsLoading && advisorTeamsForCurrentView.length === 0"
              :description="advisorTeamBlockedByOtherDivision ? '您已在另一组别组班，请从对应组别详情页管理队伍' : '暂无本组别队伍，请先创建或刷新'"
            />
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
                <a-descriptions-item label="队长">{{ advisorSelectedTeamCaptainLabel }}</a-descriptions-item>
                <a-descriptions-item label="状态">{{ participantTeamStatusText(advisorSelectedTeam.status) }}</a-descriptions-item>
                <a-descriptions-item label="指导老师">{{ advisorSelectedTeamAdvisorLabel }}</a-descriptions-item>
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
                  <a-form-item label="邀请学生">
                    <a-input
                      v-model="advisorInviteStudent"
                      placeholder="姓名或 8 位用户 ID"
                      style="width: 220px"
                      :disabled="!canOperateAdvisorSelectedTeam || advisorTeamActionsDisabled"
                      allow-clear
                    />
                  </a-form-item>
                  <a-form-item>
                    <a-button
                      type="primary"
                      :loading="advisorTeamOpLoading"
                      :disabled="!canOperateAdvisorSelectedTeam || advisorTeamActionsDisabled || !(advisorInviteStudent && String(advisorInviteStudent).trim())"
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
                    {{ formatTeamMemberDisplayName(m) }}
                    <span v-if="m.user_id != null" class="muted" style="margin-left: 4px">(ID {{ m.user_id }})</span>
                  </span>
                  <a-button
                    v-if="canOperateAdvisorSelectedTeam && !competitionTeamRemoveMemberBlocked"
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
                v-else-if="advisorTeamBlockedByOtherDivision"
                class="muted advisor-manage-team-hint"
                style="margin: 8px 0 0; font-size: 13px"
              >
                {{ advisorTeamBlockedByOtherDivisionDescription }}
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
            :title="adminSubmissionsPanelTitle"
            style="margin-top: 16px"
          >
            <a-button
              slot="extra"
              size="small"
              :loading="adminSubmissionsLoading"
              :disabled="!activeCompetitionId"
              @click="refreshAdminSubmissions"
            >
              {{ adminSubmissionsRefreshLabel }}
            </a-button>

            <a-empty
              v-if="isCompetitionExpert && !adminSubmissionsLoading && !adminHasAnyTrackSubmissions"
              description="暂无已指派队伍的作品提交"
              style="margin: 24px 0"
            />

            <!-- 作品赛道：压缩包作品列表 -->
            <div v-if="showAdminWorksTrackBlock" class="admin-track-block">
              <div class="admin-track-bar">
                <span class="admin-track-bar__title">作品赛道</span>
                <div class="admin-track-bar__actions">
                  <a-button
                    v-if="canExportAnswers"
                    size="small"
                    :loading="questionAnswersExportLoading === 'works:by_team'"
                    :disabled="!activeCompetitionId || !!questionAnswersExportLoading"
                    @click="exportQuestionAnswersZip('by_team', 'works')"
                  >
                    导出答案（队伍）
                  </a-button>
                </div>
              </div>
              <p
                v-if="adminSubmissionsHiddenByWithdrawCount > 0"
                class="muted"
                style="margin: 0 0 8px; font-size: 13px"
              >
                仅展示当前有效报名周期内的提交。
              </p>
              <a-empty v-if="adminWorksSubmissions.length === 0" description="暂无作品赛道压缩包提交" />
              <div v-else class="submissions-list">
                <a-card
                  v-for="s in adminWorksSubmissions"
                  :key="'works-sub-' + s.id"
                  size="small"
                  class="submission-item"
                  :bordered="false"
                >
                  <div class="submission-title-row">
                    <div class="submission-title">
                      {{ s.team_name || (s.team_id != null ? ('队伍' + s.team_id) : (s.title || '-')) }}
                    </div>
                    <a-tag :color="getSubmissionStatusColor(s.status)">
                      {{ getSubmissionStatusText(s.status) }}
                    </a-tag>
                  </div>
                  <div class="submission-meta muted" style="margin-top: 6px">
                    <a-tag
                      v-if="submissionDivisionLabel(s)"
                      color="blue"
                    >
                      {{ submissionDivisionLabel(s) }}
                    </a-tag>
                    <span :style="submissionDivisionLabel(s) ? 'margin-left: 12px' : ''">
                      队伍ID：{{ s.team_id != null ? s.team_id : '-' }}
                    </span>
                    <span style="margin-left: 12px">
                      队伍名：{{ s.team_name || (s.team_id != null ? ('队伍' + s.team_id) : '-') }}
                    </span>
                  </div>
                  <div v-if="isSubmissionGraded(s)" class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatScoreCell(s) }}
                  </div>
                  <div class="row" style="margin-top: 10px">
                    <template v-if="canReviewSubmissions">
                      <a-button
                        v-if="!isSubmissionGraded(s)"
                        size="small"
                        type="primary"
                        :disabled="s.status === 'draft'"
                        @click.stop="fillGradeForm(s.id, false)"
                      >
                        评分
                      </a-button>
                      <a-button
                        v-else
                        size="small"
                        type="primary"
                        @click.stop="fillGradeForm(s.id, true)"
                      >
                        修改评分
                      </a-button>
                    </template>
                    <a-button
                      size="small"
                      style="margin-left: 8px"
                      :disabled="!s.file_id"
                      @click="downloadSubmission(s.id, s)"
                    >
                      下载文件
                    </a-button>
                  </div>
                </a-card>
              </div>
              <div v-if="adminWorksSubmissions.length > 0 && adminSubmissionsTotal > 0" style="display: flex; justify-content: flex-end; margin-top: 12px">
                <a-pagination
                  :current="adminSubmissionsPage"
                  :page-size="adminSubmissionsPageSize"
                  :total="adminSubmissionsTotal"
                  :page-size-options="adminSubmissionsPageSizeOptions"
                  :show-size-changer="true"
                  :show-quick-jumper="true"
                  :show-total="(total) => `共 ${total} 条`"
                  size="small"
                  @change="handleAdminSubmissionsPageChange"
                  @showSizeChange="handleAdminSubmissionsPageChange"
                />
              </div>
            </div>

            <!-- 软件 / 硬件赛道：分题答案列表 -->
            <template v-if="usesQuestionAnswerSubmission">
              <div
                v-for="trackKey in adminQuestionAnswerTrackKeys"
                :key="'admin-qa-track-' + trackKey"
                class="admin-track-block"
              >
              <div class="admin-track-bar">
                <span class="admin-track-bar__title">{{ trackKey === 'software' ? '软件赛道' : '硬件赛道' }}</span>
                <div class="admin-track-bar__actions">
                  <a-button
                    v-if="canExportAnswers"
                    size="small"
                    :loading="questionAnswersExportLoading === (trackKey + ':by_team')"
                    :disabled="!activeCompetitionId || !!questionAnswersExportLoading"
                    @click="exportQuestionAnswersZip('by_team', trackKey)"
                  >
                    导出答案（队伍）
                  </a-button>
                  <a-button
                    v-if="canExportAnswers"
                    size="small"
                    :loading="questionAnswersExportLoading === (trackKey + ':by_question')"
                    :disabled="!activeCompetitionId || !!questionAnswersExportLoading"
                    @click="exportQuestionAnswersZip('by_question', trackKey)"
                  >
                    导出答案（题目）
                  </a-button>
                </div>
              </div>
              <a-empty
                v-if="!adminQuestionAnswerRowsForTrack(trackKey).length"
                :description="'暂无' + (trackKey === 'software' ? '软件' : '硬件') + '赛道题目答案'"
              />
              <a-table
                v-else
                size="small"
                bordered
                :pagination="{ pageSize: 10, showSizeChanger: true }"
                :columns="adminQuestionAnswerTableColumnsForTrack(trackKey)"
                :data-source="adminQuestionAnswerRowsForTrack(trackKey)"
                :row-key="(r) => trackKey + '-' + r.team_id"
              >
                <template slot="q1" slot-scope="text, record">
                  <a-tag :color="record.q1_uploaded ? 'green' : 'orange'">{{ record.q1_uploaded ? '已提交' : '未提交' }}</a-tag>
                  <a-button
                    v-if="record.q1_answer_id"
                    size="small"
                    type="link"
                    @click="downloadQuestionAnswer(record.q1_answer_id)"
                  >下载</a-button>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatQuestionScoreCell(record.score_q1) }}
                  </div>
                </template>
                <template slot="q2" slot-scope="text, record">
                  <a-tag :color="record.q2_uploaded ? 'green' : 'orange'">{{ record.q2_uploaded ? '已提交' : '未提交' }}</a-tag>
                  <a-button
                    v-if="record.q2_answer_id"
                    size="small"
                    type="link"
                    @click="downloadQuestionAnswer(record.q2_answer_id)"
                  >下载</a-button>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatQuestionScoreCell(record.score_q2) }}
                  </div>
                </template>
                <template slot="q3" slot-scope="text, record">
                  <a-tag :color="record.q3_uploaded ? 'green' : 'orange'">{{ record.q3_uploaded ? '已提交' : '未提交' }}</a-tag>
                  <a-button
                    v-if="record.q3_answer_id"
                    size="small"
                    type="link"
                    @click="downloadQuestionAnswer(record.q3_answer_id)"
                  >下载</a-button>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatQuestionScoreCell(record.score_q3) }}
                  </div>
                </template>
                <template slot="q4" slot-scope="text, record">
                  <a-tag :color="record.q4_uploaded ? 'green' : 'orange'">{{ record.q4_uploaded ? '已提交' : '未提交' }}</a-tag>
                  <a-button
                    v-if="record.q4_answer_id"
                    size="small"
                    type="link"
                    @click="downloadQuestionAnswer(record.q4_answer_id)"
                  >下载</a-button>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatQuestionScoreCell(record.score_q4) }}
                  </div>
                </template>
                <template slot="q5" slot-scope="text, record">
                  <a-tag :color="record.q5_uploaded ? 'green' : 'orange'">{{ record.q5_uploaded ? '已提交' : '未提交' }}</a-tag>
                  <a-button
                    v-if="record.q5_answer_id"
                    size="small"
                    type="link"
                    @click="downloadQuestionAnswer(record.q5_answer_id)"
                  >下载</a-button>
                  <div class="muted" style="margin-top: 4px; font-size: 12px">
                    分数：{{ formatQuestionScoreCell(record.score_q5) }}
                  </div>
                </template>
                <template slot="progress" slot-scope="text, record">
                  {{ record.uploaded_count }}/{{ record.question_count }}
                </template>
                <template slot="totalScore" slot-scope="text, record">
                  <strong>{{ formatQuestionScoreCell(record.total_score) }}</strong>
                </template>
                <template slot="gradeActions" slot-scope="text, record">
                  <a-button
                    v-if="canReviewSubmissions && !record.graded"
                    size="small"
                    type="primary"
                    @click.stop="fillTeamQuestionGradeForm(record, false)"
                  >
                    评分
                  </a-button>
                  <a-button
                    v-else-if="canReviewSubmissions"
                    size="small"
                    type="primary"
                    @click.stop="fillTeamQuestionGradeForm(record, true)"
                  >
                    修改评分
                  </a-button>
                </template>
              </a-table>
              </div>
            </template>
          </a-card>

          <a-card
            v-if="canManageCompetitions && isActiveCompetitionPreliminary"
            size="small"
            class="sub-card"
            :bordered="true"
            title="晋级决赛"
            style="margin-top: 16px"
          >
            <div class="muted" style="margin-bottom: 12px; font-size: 13px">
              按赛道勾选初赛中已校审通过的队伍，确认后自动带入决赛（复制队伍与报名），选手无需再报名或建队。
              <template v-if="activeCompetition && activeCompetition.paired_competition_id">
                关联决赛 ID：{{ activeCompetition.paired_competition_id }}
              </template>
            </div>
            <div class="row" style="margin-bottom: 12px; flex-wrap: wrap; gap: 8px">
              <a-button :loading="promotionListLoading" @click="refreshPromotionList">
                刷新晋级名单
              </a-button>
            </div>
            <div
              v-for="track in examPaperTrackOptions"
              :key="'promo-track-' + track.value"
              class="admin-track-block"
            >
              <div class="admin-track-bar">
                <span class="admin-track-bar__title">{{ track.label }}</span>
                <div class="admin-track-bar__actions">
                  <a-button
                    type="primary"
                    size="small"
                    :loading="promotionCandidatesLoading && promotionModalWorkTrack === track.value"
                    @click="openPromoteModal(track.value)"
                  >
                    选择队伍晋级
                  </a-button>
                  <a-upload
                    :show-upload-list="false"
                    :before-upload="(file) => beforeImportPromotionsExcel(file, track.value)"
                    accept=".xlsx,.xlsm"
                  >
                    <a-button size="small" :loading="promotionImportLoading === track.value">
                      导入 Excel 晋级
                    </a-button>
                  </a-upload>
                </div>
              </div>
              <div class="muted" style="margin-bottom: 8px; font-size: 12px">
                仅显示 {{ track.label }} 已晋级用户。Excel 须含列「队伍ID」；可选「队伍名」。仅导入本赛道初赛队伍。
              </div>
              <a-table
                size="small"
                row-key="id"
                :loading="promotionListLoading"
                :pagination="false"
                :data-source="promotionsForTrack(track.value)"
                :columns="promotionListColumns"
              >
                <template slot="promoActions" slot-scope="text, record">
                  <a @click.prevent="handleRevokePromotion(record)">撤销</a>
                </template>
              </a-table>
            </div>
            <div v-if="untrackedPromotions.length" class="admin-track-block">
              <div class="admin-track-bar">
                <span class="admin-track-bar__title">未分赛道</span>
              </div>
              <a-table
                size="small"
                row-key="id"
                :pagination="false"
                :data-source="untrackedPromotions"
                :columns="promotionListColumns"
              >
                <template slot="promoActions" slot-scope="text, record">
                  <a @click.prevent="handleRevokePromotion(record)">撤销</a>
                </template>
              </a-table>
            </div>
          </a-card>

          <a-card
            v-if="canViewParticipantsRoster"
            size="small"
            class="sub-card"
            :bordered="true"
            title="参赛者名单（竞赛维度）"
            style="margin-top: 16px"
          >
            <div class="row" style="flex-wrap: wrap; gap: 8px">
              <a-button
                type="primary"
                :loading="participantsTeamsLoading"
                @click="refreshParticipantsTeams"
                :disabled="!activeCompetitionId"
              >
                查看参赛者
              </a-button>
              <a-button
                v-if="canManageCompetitions"
                type="primary"
                :loading="participantsTeamsExportLoading"
                @click="exportTeamsExcel"
                :disabled="!activeCompetitionId"
              >
                导出参赛表格
              </a-button>
            </div>
            <p v-if="canManageCompetitions" class="muted" style="margin: 8px 0 0; font-size: 12px">
              导出为压缩包：内含作品 / 软件 / 硬件赛道各一份 Excel。表头含学校、竞赛、组别项目、队伍、队员；「队员」之后的分题列取自该赛道发布试卷时的题名配置，最后为总分。
            </p>
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
          v-if="!standaloneGuestMode && !isStudent && !showAdvisorTeamPanel && !isCompetitionWorkbench && !showExpertNotAssignedHint"
          style="margin-top: 16px"
          :description="roleNoPermissionDescription"
        />
      </div>

    </a-card>

    <!-- 独立详情页：报名弹窗（报名成功后同窗展示作品提交） -->
    <a-modal
      v-model="showStandaloneEnrollModal"
      title="报名"
      :width="760"
      :footer="null"
      :destroyOnClose="false"
      wrap-class-name="standalone-competition-modal-wrap"
      @cancel="showStandaloneEnrollModal = false"
    >
      <div class="standalone-modal-scroll">
        <a-alert
          v-if="isActiveCompetitionFinal"
          :type="finalStageAccessDenied ? 'error' : 'info'"
          show-icon
          :message="finalStageAccessDenied ? '无权参加决赛' : '决赛准入'"
          :description="finalStageAccessDenied
            ? '决赛仅限初赛晋级队伍。您当前不在晋级名单中，无法报名、建队或提交作品。'
            : '决赛沿用初赛晋级队伍，无需重新报名或创建队伍；可直接查看队伍信息并提交作品。'"
          style="margin-bottom: 12px"
        />
        <a-alert
          v-if="enrollBlockedByOtherDivision"
          type="warning"
          show-icon
          message="无法在本组别报名"
          :description="enrollBlockedByOtherDivisionDescription"
          style="margin-bottom: 12px"
        />
        <a-alert
          v-else-if="competitionEnrollPublishBlocked || competitionEnrollmentClosed"
          type="warning"
          show-icon
          :message="competitionEnrollBlockedAlertTitle"
          :description="competitionEnrollBlockedAlertDescription"
          style="margin-bottom: 12px"
        />
        <a-form layout="vertical" class="enroll-profile-form" style="margin-top: 4px; max-width: 640px">
          <a-row :gutter="12">
            <a-col :xs="24" :sm="12">
              <a-form-item label="ID" :colon="false">
                <a-input
                  :value="enrollProfileForm.student_no"
                  placeholder="用户 ID"
                  disabled
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

        <div class="muted" style="margin-bottom: 12px; font-size: 13px">
          {{ studentTeamEnrollFlowHint }}
        </div>

        <div class="row">
          <a-button
            v-if="showStudentTeamCreateJoinOps"
            type="primary"
            :loading="enrollLoading"
            @click="openStudentCreateTeamModal"
            :disabled="competitionEnrollActionsDisabled || !allowTeam || studentHasTeamForCurrentCompetition || isActiveCompetitionFinal"
            style="margin-right: 8px"
          >
            创建队伍（自动队长）
          </a-button>
          <a-tag v-if="finalStagePromoted" color="green">已晋级 · 无需再报名</a-tag>
        </div>
        <p v-if="teamEnrollActionBlockedForMember" class="muted" style="margin: 8px 0 0; font-size: 13px">
          您已完成队伍报名且为队员，无需重复报名；创建队伍、加入队伍等操作已由队长负责。
        </p>

        <a-alert
          v-if="competitionTeamRosterLocked"
          type="warning"
          show-icon
          message="作品已提交"
          :description="competitionTeamRosterLockedMessage"
          style="margin-top: 12px"
        />

        <div v-if="showPendingTeamInvitesInEnrollModal" style="margin-top: 12px">
          <a-divider orientation="left">入队邀请</a-divider>
          <a-spin :spinning="pendingTeamInvitesLoading">
            <div
              v-for="inv in pendingTeamInvitesForActiveCompetition"
              :key="'invite-' + inv.id"
              class="row"
              style="justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; padding: 8px 0; border-bottom: 1px solid #f0f0f0"
            >
              <div>
                <div>
                  队伍
                  <strong>{{ inv.team_name || ('#' + inv.team_id) }}</strong>
                  <span v-if="inv.as_captain" class="muted">（队长身份）</span>
                </div>
                <div class="muted" style="font-size: 12px; margin-top: 2px">
                  邀请人：{{ inv.inviter_name || ('#' + inv.inviter_id) }}
                </div>
              </div>
              <div class="row" style="gap: 8px">
                <a-button
                  type="primary"
                  size="small"
                  :loading="teamInviteRespondingId === inv.id"
                  @click="handleRespondTeamInvite(inv, 'accept')"
                >
                  同意入队
                </a-button>
                <a-button
                  size="small"
                  :loading="teamInviteRespondingId === inv.id"
                  @click="handleRespondTeamInvite(inv, 'reject')"
                >
                  拒绝
                </a-button>
              </div>
            </div>
          </a-spin>
        </div>

        <div style="margin-top: 12px">
          <a-form layout="vertical">
            <a-form-item v-if="showMultiTrackTeamSwitcher" label="当前操作赛道">
              <a-radio-group
                :value="activeEnrollmentWorkTrack"
                @change="e => selectPreferredEnrollmentWorkTrack(e && e.target ? e.target.value : e)"
              >
                <a-radio
                  v-for="row in myTeamEnrollmentList"
                  :key="'trk-m-' + (row.id || row.team_id) + '-' + row.work_track"
                  :value="String(row.work_track || '').trim().toLowerCase()"
                >
                  {{ workTrackDisplayLabel(row.work_track) }}（队伍 {{ row.team_id }}）
                </a-radio>
              </a-radio-group>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                切换赛道后，下方队伍 ID / 队名 / 校审 / 入队申请 / 队员与队长操作均对应该赛道队伍。
              </div>
            </a-form-item>
            <a-form-item v-else-if="showCurrentTrackTeamContextHint" label="当前赛道">
              <a-tag color="blue">{{ currentEnrollmentTrackLabel }}</a-tag>
            </a-form-item>
            <a-form-item :label="myTeamIdFormLabel">
              <a-input-number
                v-model="myTeamId"
                :min="1"
                placeholder="请先创建队伍或加入队伍"
                style="width: 240px"
                :disabled="true"
              />
            </a-form-item>
            <a-form-item v-if="myTeamId" :label="currentEnrollmentTrackLabel ? (`队伍名（${currentEnrollmentTrackLabel}）`) : '队伍名'">
              <a-input :value="myTeamNameDisplay" style="max-width: 360px" :disabled="true" />
            </a-form-item>
            <a-form-item v-if="myTeamId && myTeamAdvisorName" label="指导老师">
              <a-input :value="myTeamAdvisorName" style="max-width: 360px" :disabled="true" />
            </a-form-item>
            <a-form-item v-if="showStudentTeamCreateJoinOps" label="加入已有队伍（队伍ID 或队名二选一）">
              <div class="row" style="flex-wrap: wrap; gap: 8px">
                <a-input-number
                  v-model="joinTeamId"
                  :min="eightDigitIdMin"
                  :max="eightDigitIdMax"
                  placeholder="8 位队伍ID"
                  style="width: 160px"
                  :disabled="competitionEnrollActionsDisabled || studentHasTeamForCurrentCompetition"
                />
                <a-input
                  v-model="joinTeamName"
                  placeholder="或输入队名"
                  style="width: 180px"
                  :disabled="competitionEnrollActionsDisabled || studentHasTeamForCurrentCompetition"
                  allow-clear
                />
                <a-button
                  :loading="teamLoading"
                  :disabled="competitionEnrollActionsDisabled || studentHasTeamForCurrentCompetition"
                  @click="handleJoinTeam"
                >
                  申请加入队伍
                </a-button>
              </div>
            </a-form-item>
            <a-form-item
              v-if="showCaptainTeamJoinRequestsInEnrollModal"
              :label="enrollModalJoinRequestsLabel"
            >
              <a-spin :spinning="teamJoinRequestsLoading">
                <a-empty
                  v-if="!teamJoinRequestsLoading && teamJoinRequests.length === 0"
                  description="暂无待处理的入队申请"
                />
                <div
                  v-for="req in teamJoinRequests"
                  :key="req.id"
                  class="team-join-request-row"
                >
                  <span class="team-join-request-name">{{ formatTeamJoinRequestStudentName(req) }}</span>
                  <a-button
                    size="small"
                    type="primary"
                    :loading="teamJoinRequestReviewingId === req.id"
                    :disabled="teamJoinRequestReviewingId != null && teamJoinRequestReviewingId !== req.id"
                    @click="handleReviewTeamJoinRequest(req, 'approve')"
                  >
                    同意
                  </a-button>
                  <a-button
                    size="small"
                    :loading="teamJoinRequestReviewingId === req.id"
                    :disabled="teamJoinRequestReviewingId != null && teamJoinRequestReviewingId !== req.id"
                    @click="handleReviewTeamJoinRequest(req, 'reject')"
                  >
                    拒绝
                  </a-button>
                </div>
              </a-spin>
            </a-form-item>
            <a-form-item
              v-if="showCaptainTeamMembersInEnrollModal"
              :label="enrollModalMembersLabel"
            >
              <a-spin :spinning="myTeamMembersLoading">
                <a-empty
                  v-if="!myTeamMembersLoading && myTeamMembersNonCaptain.length === 0"
                  description="暂无队员"
                />
                <div
                  v-for="m in myTeamMembersNonCaptain"
                  :key="'my-tm-' + m.id + '-' + m.user_id"
                  class="team-member-row"
                >
                  <span class="team-member-name">
                    {{ formatTeamMemberDisplayName(m) }}
                    <span v-if="m.user_id != null" class="muted" style="margin-left: 4px">(ID {{ m.user_id }})</span>
                  </span>
                  <a-button
                    v-if="!competitionTeamRemoveMemberBlocked"
                    size="small"
                    type="link"
                    danger
                    :loading="captainRemovingUserId === m.user_id"
                    :disabled="captainRemovingUserId != null && captainRemovingUserId !== m.user_id"
                    @click="handleCaptainRemoveTeamMember(m)"
                  >
                    移除
                  </a-button>
                </div>
              </a-spin>
              <p
                v-if="competitionTeamRemoveMemberBlocked && myTeamMembers.length"
                class="muted"
                style="margin: 8px 0 0; font-size: 13px"
              >
                {{ competitionTeamRemoveMemberBlockedMessage || '当前不可移除队员' }}
              </p>
            </a-form-item>
            <div v-if="showTeamSchoolReviewStatusInEnrollModal" class="team-school-review-status-row">
              <span class="team-school-review-status-label">{{ enrollModalSchoolReviewLabel }}</span>
              <a-tag v-if="isMyTeamPendingSchoolReview" color="orange">待校审</a-tag>
              <a-tag v-else-if="isMyTeamSchoolReviewRejected" color="red">已驳回</a-tag>
              <a-tag v-else-if="isMyTeamSchoolReviewActive" color="green">已通过</a-tag>
              <a-tag v-if="isCurrentTeamCaptain" color="purple" style="margin-left: 4px">队长</a-tag>
              <a-tag v-else color="default" style="margin-left: 4px">队员</a-tag>
            </div>
            <p
              v-if="showTeamSchoolReviewStatusInEnrollModal && studentTeamEnrolledAsMember"
              class="muted team-school-review-status-hint"
            >
              当前赛道您为队员：入队申请、邀请、移除等由该队队长操作；可切换其它赛道查看对应队伍。
            </p>
            <p
              v-if="showTeamSchoolReviewStatusInEnrollModal && isMyTeamPendingSchoolReview"
              class="muted team-school-review-status-hint"
            >
              须本校校管理员审核通过后，方可进行队长转让与题目答案上传。
            </p>
            <p
              v-else-if="showTeamSchoolReviewStatusInEnrollModal && isMyTeamSchoolReviewRejected"
              class="muted team-school-review-status-hint"
            >
              校审未通过，相关组队报名已退赛；请重新建队并等待校审。
            </p>
          </a-form>

          <template v-if="showStudentTeamCaptainOpsInEnrollModal">
          <a-divider>{{ currentEnrollmentTrackLabel ? `${currentEnrollmentTrackLabel}赛道 · 队长操作` : '队长操作' }}</a-divider>
          <a-form layout="vertical">
            <a-form-item label="队长转让（可选）">
              <div class="row">
                <a-input-number
                  v-model="transferTeamId"
                  :min="eightDigitIdMin"
                  :max="eightDigitIdMax"
                  placeholder="8 位队伍ID"
                  style="width: 180px"
                  :disabled="competitionTeamRosterLocked"
                />
                <a-input
                  v-model="newCaptainRef"
                  placeholder="新队长姓名或用户 ID"
                  style="width: 200px"
                  allow-clear
                  :disabled="competitionTeamRosterLocked"
                />
                <a-button
                  :loading="teamLoading"
                  @click="handleTransferCaptain"
                  :disabled="competitionTeamRosterLocked || !transferTeamId || !(newCaptainRef && String(newCaptainRef).trim())"
                >
                  转让
                </a-button>
              </div>
            </a-form-item>
            <template v-if="isCurrentTeamCaptain">
              <a-form-item label="邀请队员">
                <div class="row">
                  <a-input
                    v-model="studentTeamInviteRef"
                    placeholder="队员姓名或用户 ID"
                    style="width: 220px"
                    allow-clear
                    :disabled="competitionTeamCreateInviteBlocked"
                  />
                  <a-button
                    type="primary"
                    :loading="teamLoading"
                    :disabled="competitionTeamCreateInviteBlocked || !(studentTeamInviteRef && String(studentTeamInviteRef).trim()) || !myTeamId"
                    @click="handleStudentTeamInviteMember"
                  >
                    邀请队员
                  </a-button>
                </div>
                <p class="muted" style="margin: 6px 0 0; font-size: 12px">发出邀请后，对方须在报名弹窗中同意才会入队。</p>
              </a-form-item>
              <a-form-item label="移除队员">
                <div class="row">
                  <a-input
                    v-model="studentTeamRemoveRef"
                    placeholder="队员姓名或用户 ID"
                    style="width: 220px"
                    allow-clear
                    :disabled="competitionTeamRemoveMemberBlocked"
                  />
                  <a-button
                    danger
                    :loading="teamLoading"
                    :disabled="competitionTeamRemoveMemberBlocked || !(studentTeamRemoveRef && String(studentTeamRemoveRef).trim()) || !myTeamId"
                    @click="handleStudentTeamRemoveMember"
                  >
                    移除队员
                  </a-button>
                </div>
              </a-form-item>
            </template>
          </a-form>
          </template>

          <template v-if="showMemberLeaveTeamInEnrollModal">
            <a-divider />
            <a-form layout="vertical">
              <a-form-item label="退出队伍">
                <a-button
                  danger
                  :loading="teamLoading"
                  :disabled="competitionTeamRosterLocked"
                  @click="handleMemberLeaveTeam"
                >
                  退队
                </a-button>
                <p v-if="competitionTeamRosterLocked" class="muted" style="margin: 6px 0 0; font-size: 12px">
                  {{ competitionTeamRosterLockedMessage }}
                </p>
              </a-form-item>
            </a-form>
          </template>
        </div>

        <div class="standalone-modal-footer-actions">
          <a-button @click="showStandaloneEnrollModal = false">关闭</a-button>
        </div>
      </div>
    </a-modal>

    <!-- 报名弹窗：创建队伍（填写队名） -->
    <a-modal
      v-model="showStudentCreateTeamModal"
      title="创建队伍"
      ok-text="确认创建"
      cancel-text="取消"
      :confirm-loading="studentCreateTeamModalLoading"
      :destroyOnClose="false"
      @ok="submitStudentCreateTeamModal"
      @cancel="closeStudentCreateTeamModal"
    >
      <a-form layout="vertical">
        <a-form-item label="队名" required>
          <a-input
            v-model="studentCreateTeamForm.name"
            placeholder="请输入队伍名称（同竞赛内不可重复）"
            :maxLength="200"
            @pressEnter="submitStudentCreateTeamModal"
          />
        </a-form-item>
        <a-form-item label="赛道" required>
          <a-radio-group v-model="studentCreateTeamForm.work_track">
            <a-radio value="works" :disabled="isWorkTrackAlreadyEnrolled('works')">作品</a-radio>
            <a-radio value="software" :disabled="isWorkTrackAlreadyEnrolled('software')">软件</a-radio>
            <a-radio value="hardware" :disabled="isWorkTrackAlreadyEnrolled('hardware')">硬件</a-radio>
          </a-radio-group>
          <div v-if="myEnrolledWorkTracks.length" class="muted" style="margin-top: 4px; font-size: 12px">
            已报名赛道不可再选：{{ myEnrolledWorkTracks.map(workTrackDisplayLabel).join('、') }}
          </div>
        </a-form-item>
        <a-form-item label="组别" required>
          <a-radio-group
            v-model="studentCreateTeamForm.division"
            :disabled="!!activeCompetitionEnrolledDivision"
          >
            <a-radio value="undergraduate">本科</a-radio>
            <a-radio value="vocational">高职</a-radio>
          </a-radio-group>
          <div class="division-choice-self-risk">请认真核对组别（本科 / 高职），选错后果自负。</div>
          <div v-if="activeCompetitionEnrolledDivision" class="muted" style="margin-top: 4px; font-size: 12px">
            本竞赛已锁定组别，不可再改。
          </div>
        </a-form-item>
        <a-form-item label="指导老师（选填）">
          <a-input
            v-model="studentCreateTeamForm.advisor_name"
            placeholder="姓名或 8 位用户 ID"
            :maxLength="100"
            allow-clear
          />
        </a-form-item>
        <p class="muted" style="margin: 0; font-size: 13px">
          您将作为队长创建队伍；创建后状态为「待校审」，须校管理员审核通过后方可提交作品。作品赛道上传压缩包，软件 / 硬件赛道按题上传答案。
        </p>
      </a-form>
    </a-modal>

    <!-- 管理员：初赛晋级决赛 -->
    <a-modal
      v-model="showPromoteModal"
      :title="promotionModalTitle"
      ok-text="确认晋级"
      cancel-text="取消"
      :confirm-loading="promotionSubmitLoading"
      :width="820"
      @ok="submitPromotions"
      @cancel="showPromoteModal = false"
    >
      <p class="muted" style="margin: 0 0 12px; font-size: 13px">
        仅显示当前赛道、且校审通过（active）的队伍可晋级；已晋级队伍不可重复勾选。
      </p>
      <a-table
        size="small"
        row-key="team_id"
        :loading="promotionCandidatesLoading"
        :pagination="false"
        :data-source="promotionCandidateRows"
        :row-selection="promotionCandidateRowSelection"
        :columns="promotionCandidateColumns"
      />
    </a-modal>

    <!-- 独立详情页：我的作品（按已报名赛道提交） -->
    <a-modal
      v-model="showStandaloneMyWorksModal"
      :title="standaloneMyWorksModalTitle"
      :width="900"
      :footer="null"
      wrap-class-name="standalone-competition-modal-wrap"
      @cancel="showStandaloneMyWorksModal = false"
    >
      <div class="standalone-modal-scroll">
        <div v-if="submitWorksAvailableTracks.length" style="margin-bottom: 16px">
          <div class="muted" style="margin-bottom: 8px; font-size: 13px">
            请选择要提交的赛道（仅显示您已报名的赛道；各赛道独立提交）
          </div>
          <a-radio-group
            :value="activeEnrollmentWorkTrack"
            button-style="solid"
            @change="e => onSubmitWorksTrackChange(e && e.target ? e.target.value : e)"
          >
            <a-radio-button
              v-for="opt in submitWorksTrackOptions"
              :key="'submit-trk-' + opt.work_track"
              :value="opt.work_track"
            >
              {{ opt.label }}
              <span v-if="opt.team_id != null" class="muted" style="margin-left: 4px; font-size: 12px">
                · 队 {{ opt.team_id }}
              </span>
            </a-radio-button>
          </a-radio-group>
        </div>

        <template v-if="activeEnrollmentWorkTrack === 'works'">
          <h4 class="standalone-modal-section-title">作品赛道 · 提交压缩包</h4>
          <a-alert
            v-if="competitionSubmissionBlocked"
            type="warning"
            show-icon
            :message="competitionSubmissionBlockedTitle"
            :description="competitionSubmissionBlockedDescription"
            style="margin-bottom: 12px"
          />
          <a-alert
            v-else-if="teamSchoolReviewSubmissionBlocked"
            type="warning"
            show-icon
            :message="teamSchoolReviewBlockedTitle"
            :description="teamSchoolReviewBlockedDescription"
            style="margin-bottom: 12px"
          />
          <a-alert
            v-else
            type="info"
            show-icon
            message="作品赛道"
            description="请由队长上传作品压缩包（.zip）。若还需提交软件/硬件赛道，请在上方切换赛道。"
            style="margin-bottom: 12px"
          />
          <a-form layout="vertical" style="max-width: 640px">
            <a-form-item label="作品标题" required>
              <a-input
                v-model="submissionForm.title"
                placeholder="请输入作品标题"
                :disabled="submissionFormDisabled || !canSubmitZipPackage"
              />
            </a-form-item>
            <a-form-item label="作品说明">
              <a-textarea
                v-model="submissionForm.description"
                :rows="2"
                placeholder="选填"
                :disabled="submissionFormDisabled || !canSubmitZipPackage"
              />
            </a-form-item>
            <a-form-item label="作品压缩包" required>
              <input
                type="file"
                accept=".zip,application/zip"
                :disabled="submissionFormDisabled || !canSubmitZipPackage"
                @change="handleFileChange"
              />
              <div v-if="submissionForm.file" class="muted" style="margin-top: 6px">
                已选：{{ submissionForm.file.name }}
              </div>
            </a-form-item>
            <a-button
              type="primary"
              :loading="submitLoading"
              :disabled="submissionFormDisabled || !canSubmitZipPackage"
              @click="handleSubmitSubmission"
            >
              提交作品
            </a-button>
            <p v-if="enrollModalSubmissionLocked" class="muted" style="margin-top: 8px; font-size: 13px; color: #389e0d">
              本赛道已提交作品
            </p>
            <p
              v-else-if="!canSubmitZipPackage && !competitionSubmissionBlocked && !teamSchoolReviewSubmissionBlocked"
              class="muted"
              style="margin-top: 8px; font-size: 13px"
            >
              仅队长可提交队伍作品压缩包。
            </p>
          </a-form>
        </template>

        <template v-else-if="activeEnrollmentWorkTrack === 'software' || activeEnrollmentWorkTrack === 'hardware'">
          <h4 class="standalone-modal-section-title">
            {{ currentEnrollmentTrackLabel }}赛道 · 按题提交（共{{ submissionQuestionCount }}题）
          </h4>
          <div class="row" style="margin-bottom: 12px; flex-wrap: wrap; gap: 8px">
            <a-button
              :loading="questionAnswersLoading"
              :disabled="!questionAnswerTeamId"
              @click="refreshQuestionAnswersBoard"
            >
              刷新上传状态
            </a-button>
          </div>
          <a-empty
            v-if="!questionAnswerTeamId"
            description="请先完成组队报名并等待校审通过"
          />
          <a-alert
            v-else-if="teamSchoolReviewSubmissionBlocked"
            type="warning"
            show-icon
            :message="teamSchoolReviewBlockedTitle"
            :description="teamSchoolReviewBlockedDescription"
            style="margin-bottom: 12px"
          />
          <div v-else class="question-answer-slots" style="margin-bottom: 16px">
            <div
              v-for="slot in displayQuestionAnswerSlots"
              :key="'works-q-slot-' + slot.question_no"
              class="question-answer-slot"
            >
              <div class="question-answer-slot__title">
                {{ slot.question_name || ('第' + slot.question_no + '题') }}
                <a-tag v-if="slot.uploaded || slot.submitted" color="green" style="margin-left: 8px">提交</a-tag>
                <a-tag v-else color="orange" style="margin-left: 8px">未提交</a-tag>
              </div>
              <div v-if="slot.answer && slot.answer.filename" class="muted" style="margin: 4px 0 8px">
                当前文件：{{ slot.answer.filename }}
              </div>
              <div class="row" style="flex-wrap: wrap; gap: 8px; align-items: center">
                <input
                  :ref="'worksQFile_' + slot.question_no"
                  type="file"
                  class="question-answer-file-input"
                  :disabled="!canEditQuestionAnswerFiles || questionAnswerUploadingNo === slot.question_no"
                  @change="onQuestionAnswerFileChange($event, slot.question_no)"
                />
                <a-button
                  size="small"
                  :disabled="!canEditQuestionAnswerFiles || questionAnswerUploadingNo === slot.question_no"
                  :loading="questionAnswerUploadingNo === slot.question_no"
                  @click="triggerQuestionAnswerFilePick('worksQFile_' + slot.question_no)"
                >
                  选择文件
                </a-button>
                <a-button
                  v-if="slot.answer && slot.answer.id"
                  size="small"
                  @click="downloadQuestionAnswer(slot.answer.id)"
                >
                  下载
                </a-button>
                <a-button
                  v-if="slot.answer && slot.answer.id"
                  size="small"
                  type="danger"
                  ghost
                  :loading="questionAnswerDeletingId === slot.answer.id"
                  :disabled="!canEditQuestionAnswerFiles"
                  @click="deleteQuestionAnswer(slot.answer.id, slot.question_no)"
                >
                  删除
                </a-button>
              </div>
            </div>
          </div>

          <div class="row" style="margin: 16px 0 8px; justify-content: flex-end">
            <a-button
              type="primary"
              :loading="questionAnswersSubmitLoading"
              :disabled="!canFormalSubmitQuestionAnswers"
              @click="submitAllQuestionAnswers"
            >
              上传作品
            </a-button>
          </div>
          <p class="muted" style="margin: 0 0 12px; font-size: 12px; text-align: right">
            {{ questionAnswersSubmitHintText }}
          </p>
        </template>

        <a-empty
          v-else
          :description="standaloneMyWorksEmptyDescription"
        />

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
        <a-form-item label="赛程类型" required>
          <a-radio-group v-model="createCompetitionForm.stage_mode">
            <a-radio value="single">单阶段</a-radio>
            <a-radio value="prelim_final">初赛 + 决赛</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item :label="createCompetitionForm.stage_mode === 'prelim_final' ? '系列名称' : '竞赛名称'" required>
          <a-input
            v-model="createCompetitionForm.name"
            :placeholder="createCompetitionForm.stage_mode === 'prelim_final' ? '如：XX杯（将生成「XX杯-初赛」「XX杯-决赛」）' : '请输入竞赛名称'"
          />
        </a-form-item>
        <a-form-item label="简介" required>
          <a-input v-model="createCompetitionForm.description" placeholder="必填" />
        </a-form-item>
        <a-form-item label="规则说明" required>
          <a-textarea v-model="createCompetitionForm.rules_text" :rows="4" placeholder="必填" />
        </a-form-item>
        <a-form-item label="参赛对象" extra="选填；将展示在竞赛详情「参赛对象」区块。">
          <a-textarea
            v-model="createCompetitionForm.target_audience"
            :rows="3"
            placeholder="如：全日制在校本科生、高职学生等"
          />
        </a-form-item>
        <a-form-item
          label="竞赛 Logo"
          extra="可选；请上传透明底 Logo（推荐 PNG），以免在深色详情页出现白底方块。亦支持 jpeg / gif / webp，单张不超过 5MB。"
        >
          <a-upload
            list-type="picture-card"
            class="create-competition-qr-upload"
            accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
            :file-list="logoFileList"
            :before-upload="beforeLogoUpload"
            :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
            @remove="handleLogoRemove"
          >
            <div v-if="logoFileList.length < 1">
              <a-icon type="plus" />
              <div class="ant-upload-text">上传 Logo</div>
            </div>
          </a-upload>
        </a-form-item>
        <a-form-item
          v-if="createCompetitionNeedsSharedQr"
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
        <template v-if="createCompetitionNeedsSeparateQr">
          <a-form-item
            label="本科组二维码"
            required
            extra="必填；png / jpeg / gif / webp，单张不超过 5MB。"
          >
            <a-upload
              list-type="picture-card"
              class="create-competition-qr-upload"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
              :file-list="qrCodeUndergraduateFileList"
              :before-upload="beforeQrCodeUndergraduateUpload"
              :disabled="qrCodeUndergraduateValidating"
              :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
              @remove="handleQrCodeUndergraduateRemove"
            >
              <div v-if="qrCodeUndergraduateFileList.length < 1">
                <a-icon :type="qrCodeUndergraduateValidating ? 'loading' : 'plus'" />
                <div class="ant-upload-text">{{ qrCodeUndergraduateValidating ? '校验中…' : '上传本科组' }}</div>
              </div>
            </a-upload>
          </a-form-item>
          <a-form-item
            label="高职组二维码"
            required
            extra="必填；png / jpeg / gif / webp，单张不超过 5MB。"
          >
            <a-upload
              list-type="picture-card"
              class="create-competition-qr-upload"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
              :file-list="qrCodeVocationalFileList"
              :before-upload="beforeQrCodeVocationalUpload"
              :disabled="qrCodeVocationalValidating"
              :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
              @remove="handleQrCodeVocationalRemove"
            >
              <div v-if="qrCodeVocationalFileList.length < 1">
                <a-icon :type="qrCodeVocationalValidating ? 'loading' : 'plus'" />
                <div class="ant-upload-text">{{ qrCodeVocationalValidating ? '校验中…' : '上传高职组' }}</div>
              </div>
            </a-upload>
          </a-form-item>
        </template>
        <a-form-item label="竞赛联系人" extra="选填；展示在竞赛详情二维码下方。">
          <a-input v-model="createCompetitionForm.contact_name" placeholder="如：张老师" />
        </a-form-item>
        <a-form-item label="联系方式" extra="选填；建议按标签填写，学生详情将自动分行，如：电话：138xxxx 邮箱：a@b.com QQ群：123456">
          <a-input v-model="createCompetitionForm.contact_phone" placeholder="如：电话：138xxxx 邮箱：a@b.com QQ群：123456" />
        </a-form-item>
        <a-form-item label="竞赛地点">
          <a-input v-model="createCompetitionForm.location" placeholder="如：合肥大学某某楼 / 线上" />
        </a-form-item>
        <a-form-item label="竞赛环境" extra="选填；软硬件环境、网络等要求说明。">
          <a-textarea
            v-model="createCompetitionForm.environment"
            :rows="3"
            placeholder="如：需自备笔记本电脑，现场提供 Wi-Fi 等"
          />
        </a-form-item>
        <template v-if="createCompetitionForm.stage_mode === 'prelim_final'">
          <a-form-item label="初赛开始时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.start_at" />
          </a-form-item>
          <a-form-item label="初赛结束时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.end_at" />
          </a-form-item>
          <a-form-item label="决赛开始时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.final_start_at" />
          </a-form-item>
          <a-form-item label="决赛结束时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.final_end_at" />
          </a-form-item>
        </template>
        <template v-else>
          <a-form-item label="开始时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.start_at" />
          </a-form-item>
          <a-form-item label="结束时间">
            <a-input type="datetime-local" v-model="createCompetitionForm.end_at" />
          </a-form-item>
        </template>
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
          message="仅提交有变化的文本字段（简介/规则/联系人等只改本场，不联动初赛或决赛）。更换二维码须在下方重新上传图片（未上传则不替换）。图片须为 png/jpeg/gif/webp，且能被识别为二维码。初赛/决赛仍会同步同一套二维码与 Logo。"
          style="margin-bottom: 16px"
        />
        <a-form-item label="竞赛ID">
          <a-input-number v-model="editCompetitionId" :disabled="true" style="width: 240px" />
        </a-form-item>

        <a-form-item label="赛程类型" required>
          <a-radio-group
            v-model="editCompetitionForm.stage_mode"
            :disabled="editCompetitionStageLocked"
          >
            <a-radio value="single">单阶段</a-radio>
            <a-radio value="prelim_final">初赛 + 决赛</a-radio>
          </a-radio-group>
          <div v-if="editCompetitionStageHint" class="muted" style="margin-top: 6px; font-size: 12px">
            {{ editCompetitionStageHint }}
          </div>
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

        <a-form-item label="参赛对象">
          <a-textarea
            v-model="editCompetitionForm.target_audience"
            :rows="3"
            placeholder="修改后保存；与当前一致则不提交"
          />
        </a-form-item>

        <a-form-item label="当前 Logo">
          <div v-if="editCurrentLogoPreviewUrl" class="edit-competition-current-qr">
            <img :src="editCurrentLogoPreviewUrl" alt="竞赛 Logo" class="edit-competition-current-qr__img" />
          </div>
          <div v-else class="muted edit-competition-qr-empty">暂无 Logo</div>
        </a-form-item>

        <a-form-item
          label="上传 Logo（选填）"
          extra="上传新图将替换当前 Logo。请使用透明底 Logo（推荐 PNG），以免在深色详情页出现白底方块。亦支持 jpeg / gif / webp，单张不超过 5MB。"
        >
          <a-upload
            list-type="picture-card"
            class="create-competition-qr-upload"
            accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
            :file-list="editLogoFileList"
            :before-upload="beforeEditLogoUpload"
            :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
            @remove="handleEditLogoRemove"
          >
            <div v-if="editLogoFileList.length < 1">
              <a-icon type="plus" />
              <div class="ant-upload-text">选择图片</div>
            </div>
          </a-upload>
        </a-form-item>

        <a-form-item label="当前二维码">
          <a-spin :spinning="editCurrentQrLoading" size="small">
            <div
              v-for="p in editCurrentQrPreviews"
              :key="p.key"
              class="edit-competition-current-qr"
            >
              <div class="edit-competition-qr-label">{{ p.label }}</div>
              <img :src="p.url" :alt="p.label" class="edit-competition-current-qr__img" />
            </div>
            <div
              v-if="!editCurrentQrLoading && editCurrentQrPreviews.length === 0"
              class="muted edit-competition-qr-empty"
            >
              暂无二维码图片
            </div>
          </a-spin>
        </a-form-item>

        <a-form-item
          v-if="editCompetitionNeedsSharedQr"
          label="上传共用二维码（选填）"
          extra="上传新图将替换当前共用二维码。png / jpeg / gif / webp，单张不超过 5MB，须包含可识别二维码。"
        >
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
        </a-form-item>
        <template v-if="editCompetitionNeedsSeparateQr">
          <a-form-item
            label="上传本科组二维码（选填）"
            extra="可只传其中一张以单独替换。png / jpeg / gif / webp，单张不超过 5MB。"
          >
            <a-upload
              list-type="picture-card"
              class="create-competition-qr-upload"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
              :file-list="editQrCodeUndergraduateFileList"
              :before-upload="beforeEditQrCodeUndergraduateUpload"
              :disabled="editQrCodeUndergraduateValidating"
              :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
              @remove="handleEditQrCodeUndergraduateRemove"
            >
              <div v-if="editQrCodeUndergraduateFileList.length < 1">
                <a-icon :type="editQrCodeUndergraduateValidating ? 'loading' : 'plus'" />
                <div class="ant-upload-text">{{ editQrCodeUndergraduateValidating ? '校验中…' : '本科组' }}</div>
              </div>
            </a-upload>
          </a-form-item>
          <a-form-item
            label="上传高职组二维码（选填）"
            extra="可只传其中一张以单独替换。png / jpeg / gif / webp，单张不超过 5MB。"
          >
            <a-upload
              list-type="picture-card"
              class="create-competition-qr-upload"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,.png,.jpg,.jpeg,.gif,.webp"
              :file-list="editQrCodeVocationalFileList"
              :before-upload="beforeEditQrCodeVocationalUpload"
              :disabled="editQrCodeVocationalValidating"
              :show-upload-list="{ showPreviewIcon: true, showRemoveIcon: true }"
              @remove="handleEditQrCodeVocationalRemove"
            >
              <div v-if="editQrCodeVocationalFileList.length < 1">
                <a-icon :type="editQrCodeVocationalValidating ? 'loading' : 'plus'" />
                <div class="ant-upload-text">{{ editQrCodeVocationalValidating ? '校验中…' : '高职组' }}</div>
              </div>
            </a-upload>
          </a-form-item>
        </template>

        <a-form-item label="竞赛联系人">
          <a-input v-model="editCompetitionForm.contact_name" placeholder="修改后保存；与当前一致则不提交" />
        </a-form-item>
        <a-form-item label="联系方式" extra="建议：电话：… 邮箱：… QQ群：…；学生详情按标签自动分行">
          <a-input v-model="editCompetitionForm.contact_phone" placeholder="如：电话：138xxxx 邮箱：a@b.com QQ群：123456" />
        </a-form-item>
        <a-form-item label="竞赛地点">
          <a-input v-model="editCompetitionForm.location" placeholder="修改后保存；与当前一致则不提交" />
        </a-form-item>
        <a-form-item label="竞赛环境">
          <a-textarea
            v-model="editCompetitionForm.environment"
            :rows="3"
            placeholder="修改后保存；与当前一致则不提交"
          />
        </a-form-item>

        <!-- 已有初赛：只改本场初赛时间 -->
        <template v-if="editCompetitionOriginalStage === 'preliminary'">
          <a-form-item label="初赛开始时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.start_at" />
          </a-form-item>
          <a-form-item label="初赛结束时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.end_at" />
          </a-form-item>
        </template>
        <!-- 单阶段升级为初赛+决赛：可同时填写初赛与决赛时间 -->
        <template v-else-if="editCompetitionForm.stage_mode === 'prelim_final' && editCompetitionOriginalStage === 'single'">
          <a-form-item label="初赛开始时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.start_at" />
          </a-form-item>
          <a-form-item label="初赛结束时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.end_at" />
          </a-form-item>
          <a-form-item label="决赛开始时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.final_start_at" />
          </a-form-item>
          <a-form-item label="决赛结束时间">
            <a-input type="datetime-local" v-model="editCompetitionForm.final_end_at" />
          </a-form-item>
        </template>
        <template v-else>
          <a-form-item :label="editCompetitionOriginalStage === 'final' ? '决赛开始时间' : '开始时间'">
            <a-input type="datetime-local" v-model="editCompetitionForm.start_at" />
          </a-form-item>
          <a-form-item :label="editCompetitionOriginalStage === 'final' ? '决赛结束时间' : '结束时间'">
            <a-input type="datetime-local" v-model="editCompetitionForm.end_at" />
          </a-form-item>
        </template>

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
        v-if="myScores == null || (!myScoresTableData.length && !myTeamGradesTableData.length)"
        description="暂无提交记录"
      />
      <div v-else>
        <div class="muted" style="margin-bottom: 10px">
          竞赛ID：{{ myScores.competition_id != null ? myScores.competition_id : '-' }}
        </div>
        <a-table
          v-if="myTeamGradesTableData.length"
          :columns="myTeamGradesTableColumns"
          :data-source="myTeamGradesTableData"
          :pagination="false"
          size="small"
          bordered
          row-key="team_id"
          style="margin-bottom: 16px"
        />
        <a-table
          v-if="myScoresTableData.length"
          :columns="myScoresTableColumns"
          :data-source="myScoresTableData"
          :pagination="{ pageSize: 10 }"
          size="small"
          bordered
          row-key="id"
        />
      </div>
    </a-modal>

    <!-- 评分汇总弹窗（按队伍；超管可改分） -->
    <a-modal
      v-model="showScoresSummaryModal"
      title="评分汇总"
      :maskClosable="false"
      :footer="null"
      width="95%"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <a-empty v-if="!summaryScoreRows.length" description="暂无评分汇总数据" />
      <a-table
        v-else
        :columns="summaryScoreTableColumns"
        :data-source="summaryScoreRows"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
        size="small"
        bordered
        :scroll="{ x: 1280 }"
        row-key="team_id"
      >
        <template slot="score_q1" slot-scope="text, record">
          <a-input
            v-if="canEditSummaryScores"
            :value="record.edit_q1"
            placeholder="0～100"
            style="width: 72px"
            @change="e => onSummaryScoreInput(record, 1, e && e.target ? e.target.value : '')"
          />
          <span v-else>{{ formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="score_q2" slot-scope="text, record">
          <a-input
            v-if="canEditSummaryScores"
            :value="record.edit_q2"
            placeholder="0～100"
            style="width: 72px"
            @change="e => onSummaryScoreInput(record, 2, e && e.target ? e.target.value : '')"
          />
          <span v-else>{{ formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="score_q3" slot-scope="text, record">
          <a-input
            v-if="canEditSummaryScores"
            :value="record.edit_q3"
            placeholder="0～100"
            style="width: 72px"
            @change="e => onSummaryScoreInput(record, 3, e && e.target ? e.target.value : '')"
          />
          <span v-else>{{ formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="score_q4" slot-scope="text, record">
          <a-input
            v-if="canEditSummaryScores"
            :value="record.edit_q4"
            placeholder="0～100"
            style="width: 72px"
            @change="e => onSummaryScoreInput(record, 4, e && e.target ? e.target.value : '')"
          />
          <span v-else>{{ formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="score_q5" slot-scope="text, record">
          <a-input
            v-if="canEditSummaryScores"
            :value="record.edit_q5"
            placeholder="0～100"
            style="width: 72px"
            @change="e => onSummaryScoreInput(record, 5, e && e.target ? e.target.value : '')"
          />
          <span v-else>{{ formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="total_score" slot-scope="text, record">
          <span>{{ canEditSummaryScores ? summaryRowAutoTotal(record) : formatQuestionScoreCell(text) }}</span>
        </template>
        <template slot="actions" slot-scope="text, record">
          <a-button
            v-if="canEditSummaryScores"
            type="link"
            size="small"
            :loading="!!record.saving"
            @click="saveSummaryTeamGrade(record)"
          >
            保存
          </a-button>
        </template>
      </a-table>
    </a-modal>

    <!-- 排行榜弹窗（表格） -->
    <a-modal
      v-model="showScoresRankingsModal"
      title="排行榜"
      :maskClosable="false"
      :footer="null"
      width="95%"
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
        :scroll="{ x: 1200 }"
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

    <!-- 参赛者弹窗（组队名单；报名默认组队） -->
    <a-modal
      v-model="showParticipantsTeamsModal"
      title="参赛者名单"
      :maskClosable="false"
      :footer="null"
      width="90%"
      wrap-class-name="competition-admin-table-modal-wrap"
    >
      <a-empty v-if="!participantsTeams || !participantsTeams.length" description="暂无参赛者数据" />
      <a-table
        v-else
        :columns="participantsTeamsTableColumnsEffective"
        :data-source="participantsTeams"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
        row-key="team_id"
        size="small"
        bordered
      />
    </a-modal>

    <!-- 超级管理员：竞赛详情页外链（dual 分本科/高职两行） -->
    <a-modal
      :visible="showCompetitionUrlModal"
      title="竞赛详情链接"
      :footer="null"
      width="620px"
      @cancel="closeCompetitionUrlModal"
    >
      <p v-if="competitionUrlModalTitle" class="competition-url-modal__name">
        {{ competitionUrlModalTitle }}
      </p>
      <div
        v-for="line in competitionUrlModalLines"
        :key="line.label + line.url"
        class="competition-url-modal__line"
      >
        <div class="competition-url-modal__label">{{ line.label }}</div>
        <div class="competition-url-modal__url-row">
          <a-input :value="line.url" readonly class="competition-url-modal__input" />
          <a-button type="link" size="small" @click="copyCompetitionDetailUrl(line.url)">复制</a-button>
        </div>
      </div>
      <p v-if="!competitionUrlModalLines.length" class="muted">暂无可用链接</p>
    </a-modal>

    <!-- 超级管理员：按组别切换上传三赛道试卷，并配置分题提交 -->
    <a-modal
      :visible="showExamPaperPublishModal"
      title="发布试卷"
      :confirmLoading="examPaperUploading"
      okText="保存发布"
      cancelText="取消"
      width="760px"
      @ok="submitExamPaperPublish"
      @cancel="closeExamPaperPublishModal"
    >
      <p v-if="examPaperModalCompetitionName" class="competition-url-modal__name">
        {{ examPaperModalCompetitionName }}
      </p>
      <a-alert
        type="info"
        show-icon
        style="margin-bottom: 12px"
        message="竞赛须已发布。请切换本科 / 高职组别，分别为作品、软件、硬件三赛道上传试卷；学生与指导老师将按本人组别+赛道下载对应试卷。"
      />

      <a-tabs
        v-model="examPaperModalActiveDivision"
        type="card"
        style="margin-bottom: 8px"
      >
        <a-tab-pane
          v-for="divKey in examPaperModalDivisionKeys"
          :key="divKey"
          :tab="examPaperDivisionLabel(divKey)"
        >
          <a-form-item
            v-for="track in examPaperTrackOptions"
            :key="'exam-' + divKey + '-' + track.value"
            :label="track.label"
            :label-col="{ span: 5 }"
            :wrapper-col="{ span: 19 }"
          >
            <div v-if="examPaperTrackPublishedMeta(divKey, track.value)" class="muted" style="margin-bottom: 6px">
              已发布：{{ examPaperTrackPublishedMeta(divKey, track.value).filename || '已有文件' }}
            </div>
            <a-upload
              :file-list="examPaperTrackFileList(divKey, track.value)"
              :before-upload="(file) => beforeExamPaperTrackUpload(divKey, track.value, file)"
              :remove="() => removeExamPaperTrack(divKey, track.value)"
              :multiple="false"
            >
              <a-button size="small"><a-icon type="upload" /> 选择文件（pdf/doc/docx/zip）</a-button>
            </a-upload>
          </a-form-item>
        </a-tab-pane>
      </a-tabs>

      <a-divider>分题配置（作品 / 软件 / 硬件分别设置）</a-divider>
      <a-alert
        type="info"
        show-icon
        style="margin-bottom: 12px"
        message="作品赛道的分题配置仅用于专家评分，学生仍上传压缩包。软件 / 硬件赛道同时用于分题提交与评分。"
      />
      <div
        v-for="trackKey in ['works', 'software', 'hardware']"
        :key="'qcfg-track-' + trackKey"
        style="margin-bottom: 20px; padding: 12px; border: 1px solid #e8e8e8; border-radius: 6px"
      >
        <h4 style="margin: 0 0 10px; font-size: 14px">
          {{ trackKey === 'works' ? '作品赛道' : (trackKey === 'software' ? '软件赛道' : '硬件赛道') }}
        </h4>
        <a-form-item :label="trackKey === 'works' ? '评分题数' : '提交题数'" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <a-select
            :value="examPaperQuestionConfigByTrack[trackKey] && examPaperQuestionConfigByTrack[trackKey].question_count"
            style="width: 120px"
            @change="(n) => onExamPaperQuestionCountChange(trackKey, n)"
          >
            <a-select-option v-for="n in 5" :key="trackKey + '-qc-' + n" :value="n">{{ n }} 题</a-select-option>
          </a-select>
        </a-form-item>
        <div
          v-for="q in (examPaperQuestionConfigByTrack[trackKey] && examPaperQuestionConfigByTrack[trackKey].questions) || []"
          :key="trackKey + '-q-' + q.no"
          style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; align-items: center"
        >
          <span style="width: 48px">第{{ q.no }}题</span>
          <a-input v-model="q.name" placeholder="题目名称" style="width: 160px" />
          <span>最低分</span>
          <a-input-number v-model="q.min_score" :min="0" :max="1000" style="width: 90px" />
          <span>最高分</span>
          <a-input-number v-model="q.max_score" :min="0" :max="1000" style="width: 90px" />
        </div>
        <a-form-item label="总分区间" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <a-input-number
            v-model="examPaperQuestionConfigByTrack[trackKey].total_min_score"
            :min="0"
            :max="5000"
            style="width: 100px"
          />
          <span style="margin: 0 8px">～</span>
          <a-input-number
            v-model="examPaperQuestionConfigByTrack[trackKey].total_max_score"
            :min="0"
            :max="5000"
            style="width: 100px"
          />
        </a-form-item>
      </div>
    </a-modal>

    <!-- 双组别竞赛：选择本科组 / 高职组后进入对应详情（§8.7 division 由详情页隐式带入报名） -->
    <a-modal
      :visible="showDivisionPickModal"
      title="选择组别查看详情"
      :footer="null"
      :maskClosable="!standaloneDetailMode"
      :closable="!standaloneDetailMode"
      :keyboard="!standaloneDetailMode"
      :get-container="divisionPickModalGetContainer"
      width="420px"
      @cancel="onDivisionPickModalCancel"
    >
      <p class="division-pick-modal__hint">
        竞赛「{{ divisionPickCompetitionName }}」分<strong>本科组</strong>与<strong>高职组</strong>，请选择要查看的组别。报名与作品提交均在该组别下进行，且不可跨组重复报名。
      </p>
      <div class="division-pick-modal__actions">
        <a-button type="primary" size="large" block @click="confirmDivisionPick('undergraduate')">
          本科组 · 查看详情
        </a-button>
        <a-button type="primary" size="large" block class="division-pick-modal__btn-second" @click="confirmDivisionPick('vocational')">
          高职组 · 查看详情
        </a-button>
      </div>
    </a-modal>

    <!-- 评分弹窗：挂到 body，避免独立详情深色布局裁切 -->
    <a-modal
      v-model="showGradeAudit"
      :title="(gradeFormIsEdit ? '修改评分（评委）' : '评分/审核（评委）') + (gradeFormTrackLabel ? (' · ' + gradeFormTrackLabel) : '')"
      :footer="null"
      :width="760"
      :zIndex="3200"
      :maskClosable="false"
      :destroyOnClose="false"
      :get-container="getGradeAuditModalContainer"
      wrap-class-name="grade-audit-modal-wrap"
      @cancel="cancelGradeAudit"
    >
      <a-spin :spinning="gradeFormLoading">
        <a-form layout="vertical" class="grade-audit-panel__form">
          <a-form-item v-if="gradeForm.team_id" label="队伍ID">
            <a-input :value="String(gradeForm.team_id)" disabled style="width: 240px" />
          </a-form-item>
          <a-form-item v-else-if="gradeForm.submission_id" label="作品提交ID">
            <a-input :value="String(gradeForm.submission_id)" disabled style="width: 240px" />
          </a-form-item>
          <template v-if="gradeFormUsesQuestionScores">
            <a-row :gutter="12" type="flex" class="grade-question-scores-row">
              <a-col
                v-for="q in gradeFormQuestionItems"
                :key="'grade-q-modal-' + q.no"
                :xs="12"
                :sm="8"
                :md="4"
              >
                <a-form-item :label="formatQuestionDisplayName(q)" required>
                  <a-input
                    :value="gradeForm['score_q' + q.no]"
                    :placeholder="gradeQuestionPlaceholder(q)"
                    style="width: 100%"
                    @input="onGradeQuestionScoreInput(q.no, $event)"
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="12" :sm="8" :md="4">
                <a-form-item label="总分">
                  <a-input :value="gradeFormAutoTotal" disabled style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
          </template>
          <a-form-item v-else label="分数" required>
            <a-input v-model="gradeForm.score" placeholder="例如：95.0" style="width: 240px" />
          </a-form-item>
          <a-form-item label="反馈">
            <a-textarea v-model="gradeForm.feedback" :rows="3" placeholder="选填" style="max-width: 520px" />
          </a-form-item>
          <div class="row">
            <a-button
              type="primary"
              :loading="gradeLoading"
              :disabled="gradeFormLoading || (gradeFormUsesQuestionScores ? false : !gradeForm.submission_id)"
              @click="handleReviewGrade"
            >
              {{ gradeFormIsEdit ? '保存修改' : '提交评分' }}
            </a-button>
            <a-button style="margin-left: 8px" :disabled="gradeLoading" @click="cancelGradeAudit">
              取消
            </a-button>
          </div>
        </a-form>
      </a-spin>
    </a-modal>
  </div>
</template>

<script>
import {
  getCompetitions,
  getCompetition,
  createCompetitionMultipart,
  publishCompetition,
  updateCompetition,
  updateCompetitionMultipart,
  deleteCompetition,
  lockCompetition,
  getCompetitionParticipantsIndividual,
  getCompetitionParticipantsTeams,
  exportCompetitionTeamsExcel,
  importCompetitionPromotionsExcel,
  getCompetitionQuestionAnswersBoard,
  getCompetitionQuestionAnswersOverview,
  uploadCompetitionQuestionAnswer,
  downloadCompetitionQuestionAnswer,
  deleteCompetitionQuestionAnswer,
  submitCompetitionQuestionAnswers,
  exportCompetitionQuestionAnswers,
  enrollCompetition,
  getCompetitionTeam,
  getCompetitionTeams,
  lookupCompetitionTeamByName,
  createCompetitionTeam,
  patchCompetitionTeam,
  inviteCompetitionTeamMember,
  listMyTeamInvites,
  respondTeamInvite,
  removeCompetitionTeamMember,
  addTeamMember,
  listTeamJoinRequests,
  reviewTeamJoinRequest,
  transferTeamCaptain,
  leaveTeam,
  submitCompetitionSubmission,
  uploadCompetitionSubmission,
  getCompetitionSubmissions,
  downloadCompetitionSubmissionFile,
  reviewCompetitionSubmissionGrade,
  patchCompetitionSubmissionReviewGrade,
  getCompetitionSubmissionReviewGrade,
  putTeamQuestionGrade,
  patchTeamQuestionGrade,
  getTeamQuestionGrade,
  getCompetitionScoresSummary,
  getCompetitionRankings,
  getMyCompetitionScores,
  getMyCompetitionEnrollments,
  getCompetitionQrCode,
  getCompetitionLogo,
  withdrawCompetition,
  uploadCompetitionExamPaper,
  getCompetitionExamPapers,
  downloadCompetitionExamPaper,
  getSubmissionQuestionConfig,
  putSubmissionQuestionConfig,
  getPromotionCandidates,
  getCompetitionPromotions,
  createCompetitionPromotions,
  revokeCompetitionPromotion
} from '@/api/competition'
import { validateImageContainsQrCode } from '@/utils/qrImageValidate'
import { parseCompetitionContactRows } from '@/utils/parseCompetitionContact'
import {
  EIGHT_DIGIT_ID_MIN,
  EIGHT_DIGIT_ID_MAX,
  EIGHT_DIGIT_ID_HINT,
  isEightDigitId,
  parseEightDigitIdsFromText,
  parseNameOrIdTokens,
  validateEightDigitUserId
} from '@/utils/eightDigitId'
import {
  markCompetitionWithdrawnForResubmit,
  saveCompetitionEnrollmentDivision,
  resolveEnrollmentDivision,
  resolveTeamDivision,
  getCompetitionEnrollmentDivision,
  saveCompetitionTeamDivision,
  getCompetitionTeamDivision,
  divisionToLabel,
  getEnrollmentScope as getEnrollmentScopeUtil,
  getCompetitionWithdrawSubmissionCutoff,
  clearCompetitionWithdrawSubmissionCutoff,
  isWithdrawnOrSupersededSubmission as isWithdrawnSubmissionRow,
  buildEnrollmentVisibilityIndex,
  splitEnrollmentsByTrack,
  filterAdminSubmissionsByActiveEnrollments,
  filterSubmissionsForEnrollmentTrack,
  keepLatestSubmissionPerTeam,
  filterSubmissionsByViewDivision,
  normalizeCompetitionApiList,
  saveSubmissionReviewGradeCache,
  getSubmissionReviewGradeCache
} from '@/utils/competitionSubmissionCycle'
import { buildAbsoluteRouteUrl } from '@/utils/openRouteInNewTab'
import {
  getStoredAltToken,
  isAltCompetitionStudent,
  isAltCompetitionSuperAdmin,
  isAltCompetitionAdvisorOrTeacher,
  isAltCompetitionExpertVerified,
  isAltCompetitionExpert,
  isAltExpertAssignedToCompetition,
  getAltAssignedCompetitionIds,
  getAltAssignedTeamIdsForCompetition,
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
    },
    /** dual 竞赛详情：undergraduate | vocational（来自路由 query，报名接口隐式携带） */
    initialViewDivision: {
      type: String,
      default: null
    },
    /** 超级管理员复制的分享链接（query share=1） */
    shareLinkMode: {
      type: Boolean,
      default: false
    },
    /** 分享链接页当前会话尚未登录，强制访客态 */
    shareGuestMode: {
      type: Boolean,
      default: false
    }
  },
  data () {
    return {
      keyword: '',
      eightDigitIdMin: EIGHT_DIGIT_ID_MIN,
      eightDigitIdMax: EIGHT_DIGIT_ID_MAX,
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

      enrollMode: 'team', // 仅组队参赛
      myTeamId: null,
      myTeamName: null,
      myTeamAdvisorName: null,
      /** 当前队伍校审状态：pending_school_review | active | rejected */
      myTeamStatus: null,
      myTeamWorkTrack: null,
      joinTeamName: '',
      showStudentCreateTeamModal: false,
      studentCreateTeamModalLoading: false,
      studentCreateTeamForm: {
        name: '',
        advisor_name: '',
        work_track: 'works',
        division: 'undergraduate'
      },

      /** POST /v1/competitions/enroll 选填扩展字段（8.7） */
      enrollProfileForm: {
        work_track: 'works',
        division: 'undergraduate',
        student_no: '',
        real_name: '',
        college: '',
        contact: ''
      },

      joinTeamId: null,
      /** 队长：待审核的入队申请 */
      teamJoinRequests: [],
      teamJoinRequestsLoading: false,
      teamJoinRequestReviewingId: null,
      myTeamMembers: [],
      myTeamMembersLoading: false,
      captainRemovingUserId: null,
      studentTeamInviteRef: '',
      studentTeamRemoveRef: '',
      transferTeamId: null,
      newCaptainRef: '',
      leaveTeamId: null,
      pendingTeamInvites: [],
      pendingTeamInvitesLoading: false,
      teamInviteRespondingId: null,

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
      /** 当前选中的作品赛道上下文（多赛道报名时切换提交/队务） */
      preferredEnrollmentWorkTrack: null,
      activeCompetitionEnrollmentRows: { individual: null, team: null, teams: [] },
      /** 本竞赛已有效报名所属的学历组别（undergraduate | vocational），跨组详情页禁止再报名 */
      activeCompetitionEnrolledDivision: null,
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
        captain_student: '',
        initial_members_text: '',
        work_track: 'works',
        division: 'undergraduate'
      },
      advisorRenameName: '',
      advisorInviteStudent: '',
      /** 本会话内由当前老师创建的队伍 ID（列表未带 created_by_advisor_id 时仍可管理） */
      advisorCreatedTeamIds: [],
      /** 本竞赛下当前老师已组班所属的学历组别（dual 时跨组禁止再建队/邀请） */
      activeCompetitionAdvisorTeamDivision: null,
      /** 参赛者 user_id → division（邀请队员时校验同组别） */
      studentDivisionByUserId: null,
      studentDivisionIndexCompetitionId: null,

      submissionMode: 'team',
      submissionForm: {
        title: '',
        description: '',
        content_text: '',
        file: null
      },
      submissionTeamId: null,
      submitLoading: false,

      /** 5 题答案上传槽位（队伍维度） */
      questionAnswerSlots: [],
      questionAnswersLoading: false,
      questionAnswerUploadingNo: null,
      questionAnswersSubmitLoading: false,
      questionAnswerDeletingId: null,
      questionAnswersExportLoading: null,

      submissionsLoading: false,
      mySubmissions: [],
      scoresLoading: false,
      myScores: null,
      showMyScoresModal: false,
      /** 竞赛详情独立页：顶部「报名」「作品」打开的弹窗 */
      showStandaloneEnrollModal: false,
      showStandaloneMyWorksModal: false,

      /** 学生独立详情「赛题说明」侧栏二维码（远程 URL 或 Blob URL） */
      studentBriefingQrRemoteUrl: '',
      studentBriefingQrObjectUrl: null,

      /** dual 竞赛：当前详情页所属组别（undergraduate | vocational） */
      activeViewDivision: null,
      showDivisionPickModal: false,
      divisionPickTarget: null,

      /** 超级管理员：竞赛详情外链弹窗 */
      showCompetitionUrlModal: false,
      competitionUrlModalTitle: '',
      competitionUrlModalLines: [],

      /** 超级管理员：发布试卷 */
      showExamPaperPublishModal: false,
      examPaperModalCompetitionId: null,
      examPaperModalCompetitionName: '',
      examPaperModalIsDual: false,
      examPaperModalActiveDivision: 'default',
      examPaperUploading: false,
      examPaperMeta: null,
      /** key: `${division}__${track}` -> File */
      examPaperTrackFiles: {},
      examPaperTrackFileLists: {},
      examPaperQuestionConfigByTrack: {
        works: {
          question_count: 5,
          questions: [
            { no: 1, name: '第1题', min_score: 0, max_score: 100 },
            { no: 2, name: '第2题', min_score: 0, max_score: 100 },
            { no: 3, name: '第3题', min_score: 0, max_score: 100 },
            { no: 4, name: '第4题', min_score: 0, max_score: 100 },
            { no: 5, name: '第5题', min_score: 0, max_score: 100 }
          ],
          total_min_score: 0,
          total_max_score: 500
        },
        software: {
          question_count: 5,
          questions: [
            { no: 1, name: '第1题', min_score: 0, max_score: 100 },
            { no: 2, name: '第2题', min_score: 0, max_score: 100 },
            { no: 3, name: '第3题', min_score: 0, max_score: 100 },
            { no: 4, name: '第4题', min_score: 0, max_score: 100 },
            { no: 5, name: '第5题', min_score: 0, max_score: 100 }
          ],
          total_min_score: 0,
          total_max_score: 500
        },
        hardware: {
          question_count: 5,
          questions: [
            { no: 1, name: '第1题', min_score: 0, max_score: 100 },
            { no: 2, name: '第2题', min_score: 0, max_score: 100 },
            { no: 3, name: '第3题', min_score: 0, max_score: 100 },
            { no: 4, name: '第4题', min_score: 0, max_score: 100 },
            { no: 5, name: '第5题', min_score: 0, max_score: 100 }
          ],
          total_min_score: 0,
          total_max_score: 500
        }
      },
      examPaperTrackOptions: [
        { value: 'works', label: '作品赛道' },
        { value: 'software', label: '软件赛道' },
        { value: 'hardware', label: '硬件赛道' }
      ],

      /** 详情页试卷下载（学生/指导老师） */
      examPapersForDetail: null,
      examPaperDownloadLoading: false,
      /** 当前竞赛分题配置（学生提交用） */
      activeSubmissionQuestionConfig: null,

      // 教师/管理员
      adminCreateLoading: false,
      showCreateCompetitionModal: false,
      createCompetitionForm: {
        name: '',
        description: '',
        rules_text: '',
        target_audience: '',
        contact_name: '',
        contact_phone: '',
        location: '',
        environment: '',
        start_at: '',
        end_at: '',
        final_start_at: '',
        final_end_at: '',
        stage_mode: 'single',
        allow_individual: false,
        allow_team: true,
        division_mode: 'single',
        qr_layout: 'shared'
      },
      createCompetitionQrFile: null,
      createCompetitionQrUndergraduateFile: null,
      createCompetitionQrVocationalFile: null,
      createCompetitionLogoFile: null,
      logoFileList: [],
      createLogoBlobUrl: null,
      qrCodeFileList: [],
      qrCodeUndergraduateFileList: [],
      qrCodeVocationalFileList: [],
      qrCodeValidating: false,
      qrCodeUndergraduateValidating: false,
      qrCodeVocationalValidating: false,
      createQrBlobUrl: null,
      createQrUndergraduateBlobUrl: null,
      createQrVocationalBlobUrl: null,
      publishCompetitionId: null,
      publishLoading: false,

      // 初赛晋级决赛
      promotionCandidatesLoading: false,
      promotionSubmitLoading: false,
      promotionImportLoading: null,
      promotionListLoading: false,
      promotionCandidates: [],
      promotionSelectedTeamIds: [],
      promotionList: [],
      showPromoteModal: false,
      promotionModalWorkTrack: null,

      // 管理员：编辑/删除/锁定竞赛
      adminEditLoading: false,
      showEditCompetitionModal: false,
      editCompetitionId: null,
      editCompetitionForm: {
        name: '',
        description: '',
        rules_text: '',
        target_audience: '',
        contact_name: '',
        contact_phone: '',
        location: '',
        environment: '',
        start_at: '',
        end_at: '',
        final_start_at: '',
        final_end_at: '',
        stage_mode: 'single',
        allow_individual: false,
        allow_team: false,
        division_mode: 'single',
        qr_layout: 'shared'
      },
      editCompetitionOriginal: null,
      /** 打开编辑弹窗时的原始 stage：single | preliminary | final */
      editCompetitionOriginalStage: 'single',
      editPairedCompetitionId: null,
      editCompetitionQrFile: null,
      editCompetitionQrUndergraduateFile: null,
      editCompetitionQrVocationalFile: null,
      editCompetitionLogoFile: null,
      editLogoFileList: [],
      editLogoBlobUrl: null,
      editCurrentLogoPreviewUrl: null,
      editCurrentLogoIsBlob: false,
      editQrCodeFileList: [],
      editQrCodeUndergraduateFileList: [],
      editQrCodeVocationalFileList: [],
      editQrCodeValidating: false,
      editQrCodeUndergraduateValidating: false,
      editQrCodeVocationalValidating: false,
      editQrBlobUrl: null,
      editQrUndergraduateBlobUrl: null,
      editQrVocationalBlobUrl: null,
      editCurrentQrPreviews: [],
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
        { title: '组别', dataIndex: 'division_label', key: 'division_label', width: 88 },
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
        { title: '组别', dataIndex: 'division_label', key: 'division_label', width: 88 },
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 90 },
        { title: '队长', dataIndex: 'captain_name', key: 'captain_name', width: 140, ellipsis: true },
        { title: '成员', dataIndex: 'members_summary', key: 'members_summary', ellipsis: true },
        { title: '队伍状态', dataIndex: 'status_text', key: 'status_text', width: 110 },
        { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
      ],
      participantsTeamsTableColumnsAnon: [
        { title: '队伍序号', dataIndex: 'sequence_no', key: 'sequence_no', width: 100 },
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 120 },
        { title: '队名', dataIndex: 'team_name_anon', key: 'team_name_anon', width: 140 },
        { title: '成员ID', dataIndex: 'member_ids_summary', key: 'member_ids_summary', ellipsis: true },
        { title: '队伍状态', dataIndex: 'status_text', key: 'status_text', width: 110 },
        { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
      ],

      gradeForm: {
        submission_id: null,
        team_id: null,
        work_track: '',
        questionGradeExists: false,
        score: '',
        score_q1: '',
        score_q2: '',
        score_q3: '',
        score_q4: '',
        score_q5: '',
        feedback: ''
      },
      /** 专家：点击「评分/修改评分」后弹出评分表单 */
      showGradeAudit: false,
      gradeFormLoading: false,
      gradeFormIsEdit: false,
      gradeLoading: false,

      adminSubmissionsLoading: false,
      adminSubmissions: [],
      adminQuestionAnswerRows: [],
      /** team_id -> works|software|hardware */
      adminTeamWorkTrackById: {},
      /** student_id -> works|software|hardware（个人报名） */
      adminIndividualWorkTrackById: {},
      adminSubmissionsPage: 1,
      adminSubmissionsPageSize: 20,
      adminSubmissionsTotal: 0,
      adminSubmissionsPageSizeOptions: ['10', '20', '50', '100'],
      /** 因退赛/非当前报名周期而从教师作品列表中隐藏的数量 */
      adminSubmissionsHiddenByWithdrawCount: 0,

      summaryLoading: false,
      scoresSummary: null,
      showScoresSummaryModal: false,
      summaryScoreRows: [],

      rankingsLimit: 50,
      rankingsLoading: false,
      scoresRankings: null,
      showScoresRankingsModal: false,

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
      if (this.shareGuestMode) return false
      return !!getStoredAltToken()
    },
    isStudent () {
      // 独立详情 / 分享页：仅第二套学生令牌，不用主站 roles 误触发报名等鉴权接口
      if (this.standaloneDetailMode || this.shareGuestMode) {
        return this.isUsingAltIdentity && isAltCompetitionStudent()
      }
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
      if (this.standaloneDetailMode || this.shareGuestMode) {
        return this.isUsingAltIdentity && isAltCompetitionAdvisorOrTeacher()
      }
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
    /** 当前登录老师姓名（组班时自动作为指导老师） */
    altCurrentUserDisplayName () {
      if (!this.isUsingAltIdentity) return ''
      const p = getAltProfileFromStorage()
      const name = String(p.full_name || p.username || '').trim()
      if (name) return name
      return this.altCurrentUserId != null ? String(this.altCurrentUserId) : ''
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
    /** 独立详情页：学生/指导老师/访客展示头图 + DIRECTIONS（与学生同款） */
    showStandaloneCompetitionBriefingLayout () {
      if (!this.standaloneDetailMode) return false
      if (this.isStudent || this.isAdvisorOrTeacher || this.standaloneGuestMode) return true
      return !this.isCompetitionWorkbench
    },
    /** 超级管理员/专家：独立详情页顶部展示表格版竞赛信息列表 */
    showWorkbenchCompetitionInfoList () {
      if (!this.standaloneDetailMode || !this.isCompetitionWorkbench) return false
      // 指导老师/学生走上方 briefing，不用工作台表格
      if (this.isStudent || this.isAdvisorOrTeacher) return false
      return true
    },
    /** 分享链接未登录访客 */
    standaloneGuestMode () {
      return this.standaloneDetailMode && (this.shareGuestMode || !this.isUsingAltIdentity)
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
        return '您未被指派到本竞赛，无法查看作品或评分。请在竞赛列表中打开已指派的竞赛详情。'
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
    selectedCompetitionRecord () {
      const id = this.selectedCompetitionId
      if (id == null || id === '') return null
      return this.competitions.find(c => String(c.id) === String(id)) || null
    },
    canPublishExamPaperForSelected () {
      if (!this.canManageCompetitions || !this.selectedCompetitionRecord) return false
      return this.isCompetitionShareableStatus(this.selectedCompetitionRecord.status)
    },
    examPaperModalDivisionKeys () {
      // 发布试卷一律按本科 / 高职分槽（不再使用「不分学历组别」）
      return ['undergraduate', 'vocational']
    },
    examPaperMetaDefault () {
      return (this.examPaperMeta && this.examPaperMeta.default) || null
    },
    examPaperMetaUndergraduate () {
      return (this.examPaperMeta && this.examPaperMeta.undergraduate) || null
    },
    examPaperMetaVocational () {
      return (this.examPaperMeta && this.examPaperMeta.vocational) || null
    },
    submissionQuestionConfigEffective () {
      const track = this.activeEnrollmentWorkTrack
      const byTrack = this.activeSubmissionQuestionConfig
      if (byTrack && (track === 'software' || track === 'hardware') && byTrack[track]) {
        return byTrack[track]
      }
      const fromComp = this.activeCompetition && this.activeCompetition.submission_question_config
      if (fromComp) {
        if ((track === 'software' || track === 'hardware') && fromComp[track]) {
          return fromComp[track]
        }
        // 兼容旧扁平结构
        if (fromComp.question_count) return fromComp
      }
      return {
        question_count: 5,
        questions: [1, 2, 3, 4, 5].map(n => ({ no: n, name: `第${n}题`, min_score: 0, max_score: 100 })),
        total_min_score: 0,
        total_max_score: 500
      }
    },
    submissionQuestionCount () {
      const n = Number(this.submissionQuestionConfigEffective.question_count)
      return Number.isFinite(n) && n >= 1 && n <= 5 ? n : 5
    },
    examPaperDownloadDivision () {
      // 下载一律按本科 / 高职（与报名/建队组别一致）
      if (this.isStudent) {
        return this.normalizeViewDivision(this.activeCompetitionEnrolledDivision)
          || this.normalizeViewDivision(this.activeViewDivision)
          || null
      }
      if (this.isAdvisorOrTeacher) {
        return this.normalizeViewDivision(this.activeCompetitionAdvisorTeamDivision)
          || this.normalizeViewDivision(this.activeViewDivision)
          || null
      }
      return this.normalizeViewDivision(this.activeViewDivision) || null
    },
    examPaperDownloadWorkTrack () {
      if (this.isStudent) {
        return this.activeEnrollmentWorkTrack || ''
      }
      if (this.isAdvisorOrTeacher) {
        const div = this.examPaperDownloadDivision
        const list = this.advisorTeamsForCurrentView || this.advisorTeams || []
        const hit = list.find((t) => {
          if (!div) return true
          return this.normalizeViewDivision(t.division) === div
        }) || list[0]
        const track = hit && hit.work_track != null ? String(hit.work_track).trim().toLowerCase() : ''
        return (track === 'works' || track === 'software' || track === 'hardware') ? track : ''
      }
      return ''
    },
    canShowExamPaperDownload () {
      if (!this.standaloneDetailMode || !this.isUsingAltIdentity) return false
      if (!this.isCompetitionShareableStatus(this.activeCompetition && this.activeCompetition.status)) {
        return false
      }
      const div = this.examPaperDownloadDivision
      if (!div || (div !== 'undergraduate' && div !== 'vocational')) return false
      const track = this.examPaperDownloadWorkTrack
      if (!track && (this.isStudent || this.isAdvisorOrTeacher)) return false
      const meta = this.examPapersForDetail
      if (!meta) return false
      const byTrack = meta.by_track || {}
      const trackSlot = byTrack[div] && byTrack[div][track]
      if (trackSlot && trackSlot.published) {
        // ok
      } else {
        const legacyDefault = byTrack.default && byTrack.default[track]
        const slot = div === 'undergraduate'
          ? meta.undergraduate
          : meta.vocational
        if (!(slot && slot.published) && !(legacyDefault && legacyDefault.published)) return false
      }

      if (this.isStudent) {
        if (!this.hasAnyEnrollment) return false
        const enrolledDiv = this.normalizeViewDivision(this.activeCompetitionEnrolledDivision)
        if (!enrolledDiv || enrolledDiv !== div) return false
        return true
      }

      if (this.isAdvisorOrTeacher) {
        const teamDiv = this.normalizeViewDivision(this.activeCompetitionAdvisorTeamDivision)
        return !!(teamDiv && teamDiv === div)
      }

      return false
    },
    createCompetitionNeedsSharedQr () {
      const mode = this.createCompetitionForm.division_mode || 'single'
      if (mode !== 'dual') return true
      return (this.createCompetitionForm.qr_layout || 'shared') === 'shared'
    },
    createCompetitionNeedsSeparateQr () {
      return (
        this.createCompetitionForm.division_mode === 'dual' &&
        this.createCompetitionForm.qr_layout === 'separate'
      )
    },
    editCompetitionNeedsSharedQr () {
      const mode = this.editCompetitionForm.division_mode || 'single'
      if (mode !== 'dual') return true
      return (this.editCompetitionForm.qr_layout || 'shared') === 'shared'
    },
    editCompetitionNeedsSeparateQr () {
      return (
        this.editCompetitionForm.division_mode === 'dual' &&
        this.editCompetitionForm.qr_layout === 'separate'
      )
    },
    editCompetitionStageLocked () {
      const s = this.editCompetitionOriginalStage
      return s === 'preliminary' || s === 'final'
    },
    editCompetitionStageHint () {
      const s = this.editCompetitionOriginalStage
      if (s === 'preliminary') {
        const paired = this.editPairedCompetitionId
        return paired
          ? `当前为初赛，已关联决赛 #${paired}；此处仅修改初赛时间。`
          : '当前为初赛；此处仅修改初赛时间。'
      }
      if (s === 'final') {
        const paired = this.editPairedCompetitionId
        return paired
          ? `当前为决赛，已关联初赛 #${paired}；请在初赛侧调整赛程类型。`
          : '当前为决赛；请在初赛侧调整赛程类型。'
      }
      if (this.editCompetitionForm.stage_mode === 'prelim_final') {
        return '保存后将把本场改为初赛，并自动创建关联决赛（名称加「-初赛」「-决赛」后缀）。'
      }
      return ''
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
      // 参赛者名单（竞赛维度）仅超管可见；专家不再开放
      if (this.isUsingAltIdentity) {
        return this.isSuperAdmin
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    canViewScoreAnalytics () {
      // 评分汇总/排行榜仅超管可见；专家不再开放
      if (this.isUsingAltIdentity) {
        return this.isSuperAdmin
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    isCompetitionWorkbench () {
      return this.canManageCompetitions || this.canViewCompetitionSubmissions || this.canViewParticipantsRoster || this.canViewScoreAnalytics
    },
    competitionListColumns () {
      return [
        { title: 'ID', dataIndex: 'id', key: 'id', width: 96 },
        { title: '竞赛名称', dataIndex: 'name', key: 'name', ellipsis: true, width: 200 },
        { title: '赛程', dataIndex: 'stage', key: 'stage', width: 80, scopedSlots: { customRender: 'stage' } },
        { title: '状态', dataIndex: 'status', key: 'status', width: 104, scopedSlots: { customRender: 'status' } },
        { title: '简介', dataIndex: 'summary', key: 'summary', ellipsis: true },
        { title: '开始时间', dataIndex: 'start_at', key: 'start_at', width: 120 },
        { title: '结束时间', dataIndex: 'end_at', key: 'end_at', width: 120 },
        { title: '操作', key: 'actions', width: this.isSuperAdmin ? 148 : 100, fixed: 'right', scopedSlots: { customRender: 'listActions' } }
      ]
    },
    competitionListTableData () {
      return this.filteredCompetitions.map(c => {
        const raw = (c.description || c.rules_text || '').trim()
        const summary = raw ? (raw.length > 80 ? raw.slice(0, 80) + '…' : raw) : '-'
        return {
          id: c.id,
          name: c.name || '-',
          stage: c.stage || 'single',
          status: c.status,
          summary,
          start_at: this.formatDate(c.start_at),
          end_at: this.formatDate(c.end_at)
        }
      })
    },
    activeCompetitionStage () {
      const c = this.activeCompetition
      return c && c.stage ? String(c.stage).toLowerCase() : 'single'
    },
    expertAnonymizedView () {
      return !!(
        this.isUsingAltIdentity &&
        this.isCompetitionExpert &&
        this.isExpertAssignedToActiveCompetition &&
        !this.isSuperAdmin
      )
    },
    participantsTeamsTableColumnsEffective () {
      return this.expertAnonymizedView
        ? this.participantsTeamsTableColumnsAnon
        : this.participantsTeamsTableColumns
    },
    rankingsTableColumns () {
      const qCols = this.buildQuestionScoreColumns(null, {
        dataIndexPrefix: 'score_q',
        width: 88
      })
      return [
        { title: '排名', dataIndex: 'rowIndex', key: 'rowIndex', width: 72 },
        { title: '队伍名称', dataIndex: 'team_name', key: 'team_name', ellipsis: true, width: 140 },
        { title: '学校', dataIndex: 'school', key: 'school', ellipsis: true, width: 140 },
        { title: '指导老师', dataIndex: 'advisor_name', key: 'advisor_name', ellipsis: true, width: 100 },
        { title: '队长', dataIndex: 'captain_name', key: 'captain_name', ellipsis: true, width: 100 },
        { title: '队员', dataIndex: 'members', key: 'members', ellipsis: true, width: 180 },
        ...qCols,
        { title: '总分', dataIndex: 'best_score', key: 'best_score', width: 80 }
      ]
    },
    myTeamGradesTableColumns () {
      const track = this.activeEnrollmentWorkTrack || 'software'
      const qCols = this.buildQuestionScoreColumns(track, {
        dataIndexPrefix: 'score_q',
        width: 80
      })
      return [
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 100 },
        ...qCols,
        { title: '总分', dataIndex: 'total_score', key: 'total_score', width: 88 }
      ]
    },
    adminQuestionAnswerTrackKeys () {
      const all = ['software', 'hardware']
      if (!this.isCompetitionExpert) return all
      return all.filter(k => (this.adminQuestionAnswerRowsForTrack(k) || []).length > 0)
    },
    showAdminWorksTrackBlock () {
      if (!this.usesZipPackageSubmission) return false
      if (this.isCompetitionExpert) return (this.adminWorksSubmissions || []).length > 0
      return true
    },
    adminHasAnyTrackSubmissions () {
      if ((this.adminWorksSubmissions || []).length > 0) return true
      return ['software', 'hardware'].some(k => (this.adminQuestionAnswerRowsForTrack(k) || []).length > 0)
    },
    canExportAnswers () {
      if (this.canManageCompetitions) return true
      return this.isExpertAssignedToActiveCompetition
    },
    adminWorksSubmissions () {
      // 压缩包提交仅作品赛道可产生；同一队伍只展示最新一条
      return keepLatestSubmissionPerTeam(this.adminSubmissions || [])
    },
    activeCompetitionStageLabel () {
      const s = this.activeCompetitionStage
      if (s === 'preliminary') return '初赛'
      if (s === 'final') return '决赛'
      return ''
    },
    isActiveCompetitionPreliminary () {
      return this.activeCompetitionStage === 'preliminary'
    },
    isActiveCompetitionFinal () {
      return this.activeCompetitionStage === 'final'
    },
    /** 当前学生报名/队伍的赛道：works | software | hardware */
    activeEnrollmentWorkTrack () {
      const normalize = (raw) => {
        const s = raw != null ? String(raw).trim().toLowerCase() : ''
        return (s === 'works' || s === 'software' || s === 'hardware') ? s : ''
      }
      const prefer = normalize(this.preferredEnrollmentWorkTrack)
      if (prefer) return prefer
      const preferTeam = this.enrollMode === 'team' || this.submissionMode === 'team' || this.myEnrolledTeam
      const teamRow = this.activeCompetitionEnrollmentRows && this.activeCompetitionEnrollmentRows.team
      const individualRow = this.activeCompetitionEnrollmentRows && this.activeCompetitionEnrollmentRows.individual
      if (preferTeam && teamRow) {
        const t = normalize(teamRow.work_track)
        if (t) return t
      }
      if (individualRow) {
        const t = normalize(individualRow.work_track)
        if (t) return t
      }
      if (teamRow) {
        const t = normalize(teamRow.work_track)
        if (t) return t
      }
      // 兼容：报名接口未带回 work_track 时，从队伍详情回退
      const teamDetailTrack = normalize(this.myTeamWorkTrack)
      if (teamDetailTrack) return teamDetailTrack
      return ''
    },
    /** 本竞赛已报名的作品赛道列表 */
    myEnrolledWorkTracks () {
      const tracks = []
      const rows = this.activeCompetitionEnrollmentRows
      const teamList = (rows && Array.isArray(rows.teams) && rows.teams.length)
        ? rows.teams
        : (rows && rows.team ? [rows.team] : [])
      for (const row of teamList) {
        const t = row && row.work_track != null ? String(row.work_track).trim().toLowerCase() : ''
        if ((t === 'works' || t === 'software' || t === 'hardware') && !tracks.includes(t)) tracks.push(t)
      }
      if (rows && rows.individual) {
        const t = rows.individual.work_track != null ? String(rows.individual.work_track).trim().toLowerCase() : ''
        if ((t === 'works' || t === 'software' || t === 'hardware') && !tracks.includes(t)) tracks.push(t)
      }
      return tracks
    },
    /** 是否还可再报其它作品赛道（最多 3） */
    canEnrollAnotherWorkTrack () {
      return this.myEnrolledWorkTracks.length < 3
    },
    myTeamEnrollmentList () {
      const rows = this.activeCompetitionEnrollmentRows
      if (rows && Array.isArray(rows.teams) && rows.teams.length) return rows.teams
      if (rows && rows.team) return [rows.team]
      return []
    },
    showMultiTrackTeamSwitcher () {
      return this.enrollMode === 'team' && this.myTeamEnrollmentList.length > 1
    },
    /** 提交作品弹窗空态说明 */
    standaloneMyWorksEmptyDescription () {
      if (this.myEnrolledTeam || this.myEnrolledIndividual) {
        if (!this.activeEnrollmentWorkTrack) {
          return '已报名，但未识别到赛道信息。请确认建队/报名时已选择作品、软件或硬件赛道；若仍无法提交，请联系管理员检查报名记录的赛道字段。'
        }
        if (this.enrollMode === 'team' && this.myTeamId && !this.isMyTeamSchoolReviewActive) {
          return '队伍须经本校校管理员校审通过后，方可提交作品。'
        }
      }
      return '请先完成组队报名并选择赛道（作品 / 软件 / 硬件），再提交作品'
    },
    standaloneMyWorksModalTitle () {
      const track = this.currentEnrollmentTrackLabel
      return track ? `提交作品（${track}赛道）` : '提交作品'
    },
    /** 已报名可提交的赛道 */
    submitWorksAvailableTracks () {
      return this.myEnrolledWorkTracks || []
    },
    submitWorksTrackOptions () {
      const teams = this.myTeamEnrollmentList || []
      const byTrack = {}
      teams.forEach((row) => {
        const t = row && row.work_track != null ? String(row.work_track).trim().toLowerCase() : ''
        if (t === 'works' || t === 'software' || t === 'hardware') {
          byTrack[t] = row
        }
      })
      const order = ['works', 'software', 'hardware']
      const tracks = this.submitWorksAvailableTracks.length
        ? this.submitWorksAvailableTracks
        : Object.keys(byTrack)
      return order
        .filter(t => tracks.includes(t) || byTrack[t])
        .map((t) => {
          const row = byTrack[t]
          return {
            work_track: t,
            label: t === 'works' ? '作品' : t === 'software' ? '软件' : '硬件',
            team_id: row && row.team_id != null ? row.team_id : null,
            is_captain: !!(row && row.is_captain)
          }
        })
    },
    /** 作品赛道：压缩包提交；软件/硬件：分题答案（现有表单） */
    usesZipPackageSubmission () {
      if (!this.activeCompetition) return false
      // 非学生（超管/专家评阅）：作品赛压缩包列表仍可查看
      if (!this.isStudent) return true
      return this.activeEnrollmentWorkTrack === 'works'
    },
    /** 软件 / 硬件赛道用分题答案；管理端始终可查看分题列表 */
    usesQuestionAnswerSubmission () {
      if (!this.activeCompetition) return false
      if (!this.isStudent) return true
      const t = this.activeEnrollmentWorkTrack
      return t === 'software' || t === 'hardware'
    },
    /** 学生侧：仅按本人赛道展示对应提交面板 */
    showZipSubmissionPanel () {
      if (!this.isStudent) return false
      return this.activeEnrollmentWorkTrack === 'works' && this.showSubmissionPanelInEnrollView
    },
    showQuestionAnswerSubmissionPanel () {
      if (!this.isStudent) return false
      const t = this.activeEnrollmentWorkTrack
      return (t === 'software' || t === 'hardware') && this.showSubmissionPanelInEnrollView
    },
    promotionListColumns () {
      return [
        { title: '晋级ID', dataIndex: 'id', key: 'id', width: 110 },
        { title: '初赛队伍ID', dataIndex: 'source_team_id', key: 'source_team_id', width: 110 },
        { title: '初赛队伍', dataIndex: 'source_team_name', key: 'source_team_name', ellipsis: true },
        { title: '指导老师', dataIndex: 'advisor_name', key: 'advisor_name', ellipsis: true, width: 110 },
        { title: '队长', dataIndex: 'captain_label', key: 'captain_label', ellipsis: true, width: 120 },
        { title: '队员', dataIndex: 'members', key: 'members', ellipsis: true },
        { title: '操作', key: 'actions', width: 72, scopedSlots: { customRender: 'promoActions' } }
      ]
    },
    promotionCandidateColumns () {
      return [
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 90 },
        { title: '队名', dataIndex: 'name', key: 'name', ellipsis: true },
        { title: '组别', dataIndex: 'division_label', key: 'division_label', width: 72 },
        { title: '队长ID', dataIndex: 'captain_id', key: 'captain_id', width: 100 },
        { title: '队员ID', dataIndex: 'member_ids_label', key: 'member_ids_label', ellipsis: true },
        { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
        { title: '已晋级', dataIndex: 'already_promoted_label', key: 'already_promoted_label', width: 72 }
      ]
    },
    promotionCandidateRows () {
      return (this.promotionCandidates || []).map(t => ({
        ...t,
        division_label: this.promotionDivisionLabel(t.division),
        member_ids_label: Array.isArray(t.member_ids) && t.member_ids.length
          ? t.member_ids.join('、')
          : '-',
        already_promoted_label: t.already_promoted ? '是' : '否'
      }))
    },
    promotionListRows () {
      return (this.promotionList || []).map(row => {
        const captainLabel = row.captain_name
          ? (row.captain_id != null ? `${row.captain_name}（${row.captain_id}）` : row.captain_name)
          : (row.captain_id != null ? String(row.captain_id) : '-')
        return {
          ...row,
          advisor_name: row.advisor_name || '-',
          captain_label: captainLabel,
          members: row.members || '-'
        }
      })
    },
    promotionModalTitle () {
      const label = this.workTrackSectionLabel(this.promotionModalWorkTrack)
      return this.promotionModalWorkTrack ? `晋级决赛 · ${label}` : '晋级决赛'
    },
    untrackedPromotions () {
      return this.promotionListRows.filter(row => {
        const t = String(row.work_track || '').trim().toLowerCase()
        return t !== 'works' && t !== 'software' && t !== 'hardware'
      })
    },
    promotionCandidateRowSelection () {
      return {
        selectedRowKeys: this.promotionSelectedTeamIds.slice(),
        getCheckboxProps: (record) => ({
          disabled: !!record.already_promoted || String(record.status) !== 'active'
        }),
        onChange: this.onPromotionCandidateSelectionChange
      }
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
      let list = this.competitions || []
      if (this.isUsingAltIdentity && this.isCompetitionExpert) {
        const assigned = new Set(
          getAltAssignedCompetitionIds()
            .map(id => Number(id))
            .filter(n => Number.isFinite(n))
        )
        list = list.filter(c => assigned.has(Number(c.id)))
      }
      const keyword = (this.keyword || '').trim().toLowerCase()
      if (!keyword) return list
      return list.filter(c => {
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
    /** 队员身份：针对当前选中赛道队伍 */
    studentTeamEnrolledAsMember () {
      return this.enrollMode === 'team' && !!this.myTeamId && !this.isCurrentTeamCaptain
    },
    teamEnrollActionBlockedForMember () {
      // 仅当已报满全部赛道且当前赛道为队员时，提示无需再报名操作
      return this.studentTeamEnrolledAsMember && !this.canEnrollAnotherWorkTrack
    },
    studentTeamEnrollFlowHint () {
      if (this.isActiveCompetitionFinal) {
        if (this.myEnrolledTeam || this.hasAnyEnrollment) {
          return '您已随初赛队伍晋级决赛，无需重新报名或创建队伍；决赛请按题号分别上传答案。'
        }
        return '决赛仅对初赛晋级队伍开放：不接受报名与新建队伍。未晋级账号登录后也无法参赛。'
      }
      if (this.myEnrolledWorkTracks.length > 1) {
        return '您已报名多个赛道：请先在上方选择当前操作赛道，下方队伍信息、校审与队长操作均对应该赛道队伍；提交作品也按所选赛道进行。'
      }
      if (this.myEnrolledWorkTracks.length > 0 && this.canEnrollAnotherWorkTrack) {
        return '同一竞赛可报名作品/软件/硬件各一次（最多 3 个赛道），每赛道对应一支队伍；提交与退赛按赛道分别进行。可继续创建或加入其它赛道的队伍。'
      }
      if (this.studentTeamEnrolledAsMember && !this.canEnrollAnotherWorkTrack) {
        return '您已完成全部可报赛道的队伍报名。当前赛道为队员身份，队伍由队长统一管理。'
      }
      if (this.myEnrolledWorkTracks.length >= 3) {
        return '您已报名作品、软件、硬件三个赛道，不可再新建或加入其它赛道队伍。'
      }
      return '队伍参赛流程：① 创建队伍或申请加入已有队伍（须队长同意）→ ② 等待本校校管理员校审通过 → ③ 队员按题上传答案。同一竞赛最多可报三个赛道（作品/软件/硬件各一次）。'
    },
    myTeamStatusNormalized () {
      const s = this.myTeamStatus
      return s != null && String(s).trim() !== '' ? String(s).trim().toLowerCase() : ''
    },
    /** 展示用校审状态：未拉取到时，有队伍 ID 则默认为待校审 */
    effectiveMyTeamStatusNormalized () {
      if (this.myTeamStatusNormalized) return this.myTeamStatusNormalized
      if (this.myTeamId) return 'pending_school_review'
      return ''
    },
    isMyTeamPendingSchoolReview () {
      return this.effectiveMyTeamStatusNormalized === 'pending_school_review'
    },
    isMyTeamSchoolReviewRejected () {
      return this.effectiveMyTeamStatusNormalized === 'rejected'
    },
    isMyTeamSchoolReviewActive () {
      return this.effectiveMyTeamStatusNormalized === 'active'
    },
    teamSchoolReviewSubmissionBlocked () {
      if (this.submissionMode !== 'team' || !this.myEnrolledTeam) return false
      const s = this.effectiveMyTeamStatusNormalized
      if (!s) return false
      return s === 'pending_school_review' || s === 'rejected'
    },
    teamSchoolReviewBlockedTitle () {
      if (this.isMyTeamSchoolReviewRejected) {
        return this.usesQuestionAnswerSubmission ? '校审已驳回，无法上传题目答案' : '校审已驳回，无法提交作品'
      }
      return this.usesQuestionAnswerSubmission ? '待校审，暂无法上传题目答案' : '待校审，暂无法提交作品'
    },
    teamSchoolReviewBlockedDescription () {
      if (this.isMyTeamSchoolReviewRejected) {
        return '该队伍未通过校管理员审核，相关组队报名已退赛。请重新建队并等待校审通过后再提交。'
      }
      if (this.usesQuestionAnswerSubmission) {
        return '队伍已创建/报名，须本校校管理员在「校审」中审核通过后，队员方可上传题目答案。'
      }
      return '队伍已创建/报名，须本校校管理员在「校审」中审核通过后，队长方可提交作品压缩包。'
    },
    /** 队员已队伍报名后：仍可报其它赛道；决赛全程不可创建/加入 */
    showStudentTeamCreateJoinOps () {
      if (this.isActiveCompetitionFinal) return false
      if (this.enrollMode !== 'team') return false
      return this.canEnrollAnotherWorkTrack
    },
    /** 决赛未晋级：拦截提示 */
    finalStageAccessDenied () {
      return this.isActiveCompetitionFinal && this.isStudent && !this.hasAnyEnrollment
    },
    /** 决赛已晋级 */
    finalStagePromoted () {
      return this.isActiveCompetitionFinal && this.hasAnyEnrollment
    },
    /** 报名弹窗：队长在「加入已有队伍」下方查看入队申请（按当前赛道队伍） */
    showCaptainTeamJoinRequestsInEnrollModal () {
      return this.enrollMode === 'team' && this.isCurrentTeamCaptain && !!this.myTeamId
    },
    showCaptainTeamMembersInEnrollModal () {
      return this.enrollMode === 'team' && this.isCurrentTeamCaptain && !!this.myTeamId
    },
    /** 当前竞赛是否已占满全部作品赛道（不可再建/加其它赛道队伍） */
    studentHasTeamForCurrentCompetition () {
      if (this.isMyTeamSchoolReviewRejected && this.myEnrolledWorkTracks.length === 0) return false
      return !this.canEnrollAnotherWorkTrack
    },
    /** 仅当前选中赛道队伍的队长可操作转让/邀请/移除 */
    showStudentTeamCaptainOptionalOps () {
      if (this.enrollMode !== 'team') return false
      return this.isCurrentTeamCaptain
    },
    /** 报名弹窗：队伍名展示（有队伍 ID 即展示，未设置时显示占位） */
    myTeamNameDisplay () {
      const name = this.myTeamName != null ? String(this.myTeamName).trim() : ''
      return name || '（未设置）'
    },
    currentEnrollmentTrackLabel () {
      const t = this.activeEnrollmentWorkTrack
      if (t === 'works') return '作品'
      if (t === 'software') return '软件'
      if (t === 'hardware') return '硬件'
      return ''
    },
    showCurrentTrackTeamContextHint () {
      return this.enrollMode === 'team' && this.myTeamEnrollmentList.length === 1 && !!this.currentEnrollmentTrackLabel
    },
    myTeamIdFormLabel () {
      const track = this.currentEnrollmentTrackLabel
      if (track) return `我的队伍ID（${track}赛道）`
      return '我的队伍ID（创建或加入成功后自动填入）'
    },
    enrollModalJoinRequestsLabel () {
      const track = this.currentEnrollmentTrackLabel
      return track ? `入队申请（待处理 · ${track}）` : '入队申请（待处理）'
    },
    enrollModalMembersLabel () {
      const track = this.currentEnrollmentTrackLabel
      return track ? `队员（${track}赛道）` : '队员'
    },
    enrollModalSchoolReviewLabel () {
      const track = this.currentEnrollmentTrackLabel
      return track ? `校审状态（${track}赛道）：` : '校审状态：'
    },
    /** 报名弹窗：校审状态行（有队伍 ID 即展示） */
    showTeamSchoolReviewStatusInEnrollModal () {
      return this.enrollMode === 'team' && !!this.myTeamId
    },
    /** 报名弹窗：校审通过后才展示队长转让/邀请等队务操作；决赛名单冻结不展示邀请 */
    showStudentTeamCaptainOpsInEnrollModal () {
      if (this.isActiveCompetitionFinal) return false
      if (!this.showStudentTeamCaptainOptionalOps) return false
      if (!this.myTeamId) return false
      return this.isMyTeamSchoolReviewActive
    },
    /** 报名弹窗：校审通过后可提交作品（分题答案） */
    showSubmissionPanelInEnrollModal () {
      if (this.enrollBlockedByOtherDivision) return false
      if (this.enrollMode === 'individual') {
        return this.myEnrolledIndividual
      }
      if (this.enrollMode === 'team') {
        if (!this.myEnrolledTeam) return false
        if (!this.myTeamId) return false
        return this.isMyTeamSchoolReviewActive
      }
      return false
    },
    showSubmissionPanelInEnrollView () {
      if (this.enrollBlockedByOtherDivision) return false
      const enrolledForCurrentMode = this.enrollMode === 'team'
        ? this.myEnrolledTeam
        : this.myEnrolledIndividual
      if (!enrolledForCurrentMode) return false
      if (this.enrollMode === 'team') {
        if (!this.myTeamId) return false
        return this.isMyTeamSchoolReviewActive
      }
      return true
    },
    canSubmitZipPackage () {
      if (this.isStudent && this.activeEnrollmentWorkTrack !== 'works') return false
      if (!this.usesZipPackageSubmission) return false
      if (!this.isStudent) return false
      if (this.competitionSubmissionBlocked || this.teamSchoolReviewSubmissionBlocked) return false
      if (this.enrollMode === 'team') {
        return !!(this.myEnrolledTeam && this.myTeamId && this.isMyTeamSchoolReviewActive && this.isCurrentTeamCaptain)
      }
      return !!this.myEnrolledIndividual
    },
    questionAnswerTeamId () {
      if (this.myTeamId) return this.myTeamId
      const row = this.activeCompetitionEnrollmentRows && this.activeCompetitionEnrollmentRows.team
      return row && row.team_id != null ? row.team_id : null
    },
    canUploadQuestionAnswers () {
      const trackOk = !this.isStudent || this.activeEnrollmentWorkTrack === 'software' || this.activeEnrollmentWorkTrack === 'hardware'
      return !!(
        trackOk &&
        this.usesQuestionAnswerSubmission &&
        this.isStudent &&
        this.questionAnswerTeamId &&
        this.isMyTeamSchoolReviewActive &&
        !this.competitionSubmissionBlocked &&
        !this.teamSchoolReviewSubmissionBlocked
      )
    },
    displayQuestionAnswerSlots () {
      const cfg = this.submissionQuestionConfigEffective
      const count = this.submissionQuestionCount
      const nameByNo = {}
      ;(cfg.questions || []).forEach((q) => {
        if (q && q.no != null) nameByNo[Number(q.no)] = q.name || `第${q.no}题`
      })
      const slots = Array.isArray(this.questionAnswerSlots) ? this.questionAnswerSlots : []
      return Array.from({ length: count }, (_, i) => {
        const n = i + 1
        const found = slots.find((s) => s && Number(s.question_no) === n)
        const base = found || { question_no: n, uploaded: false, submitted: false, answer: null }
        return {
          ...base,
          question_no: n,
          question_name: nameByNo[n] || `第${n}题`,
          submitted: !!(base.submitted || (base.answer && base.answer.status === 'submitted'))
        }
      })
    },
    canFormalSubmitQuestionAnswers () {
      if (!this.canUploadQuestionAnswers) return false
      const slots = this.displayQuestionAnswerSlots
      // 已有任一题正式提交后，不可再次提交
      if (slots.some((s) => s && s.submitted)) return false
      // 至少有一道题已选文件（草稿）
      return slots.some((s) => s && s.uploaded && !s.submitted)
    },
    hasFormalSubmittedQuestionAnswers () {
      return this.displayQuestionAnswerSlots.some((s) => s && s.submitted)
    },
    canEditQuestionAnswerFiles () {
      return !!(this.canUploadQuestionAnswers && !this.hasFormalSubmittedQuestionAnswers)
    },
    questionAnswersSubmitHintText () {
      if (this.hasFormalSubmittedQuestionAnswers) {
        return '本队作品已正式提交，全队都不能再上传、删除或再次提交。'
      }
      return '同一队伍内队员上传的题目文件彼此可见，同题后传覆盖先传。请先确认各题文件齐全，再点击「上传作品」；在弹窗中确认后正式提交，提交后全队都不能再上传、删除或再次提交。'
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
      return keepLatestSubmissionPerTeam(filterSubmissionsForEnrollmentTrack(this.mySubmissions, ctx))
    },
    /** 报名弹窗：当前提交类型（个人/队伍）在本报名周期已有作品则禁止再次提交 */
    enrollModalSubmissionLocked () {
      if (!this.hasAnyEnrollment) return false
      return this.mySubmissionsForCurrentEnrollment.length > 0
    },
    adminSubmissionsPanelTitle () {
      if (this.isActiveCompetitionDualDivision && this.activeDivisionLabel) {
        return `作品提交（${this.activeDivisionLabel} · 按赛道）`
      }
      return '作品提交（按赛道）'
    },
    adminSubmissionsRefreshLabel () {
      if (this.isActiveCompetitionDualDivision && this.activeDivisionLabel) {
        return `刷新${this.activeDivisionLabel}提交`
      }
      return '刷新'
    },
    adminSubmissionsEmptyDescription () {
      if (this.usesQuestionAnswerSubmission) {
        if (this.isActiveCompetitionDualDivision && this.activeDivisionLabel) {
          return `暂无${this.activeDivisionLabel}题目答案，请点击「${this.adminSubmissionsRefreshLabel}」`
        }
        return '暂无题目答案数据，请先选择竞赛并点击「刷新题目答案」'
      }
      if (this.adminSubmissionsHiddenByWithdrawCount > 0) {
        return `当前无有效作品（已隐藏 ${this.adminSubmissionsHiddenByWithdrawCount} 条退赛前的作品，仅展示重新报名后提交的作品）`
      }
      if (this.isActiveCompetitionDualDivision && this.activeDivisionLabel) {
        return `暂无${this.activeDivisionLabel}作品，请点击「${this.adminSubmissionsRefreshLabel}」`
      }
      return '暂无作品数据，请先选择竞赛并点击「刷新作品列表」'
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
      if (c.allow_team) parts.push('支持团队参赛')
      if (!parts.length) return '参赛方式以主办方公告为准。'
      return `${parts.join('；')}。具体资格条件见赛事要求。`
    },
    studentBriefingContactRows () {
      return parseCompetitionContactRows(this.activeCompetition || {})
    },
    /** @deprecated 兼容旧逻辑；优先使用 studentBriefingContactRows */
    studentBriefingContactParts () {
      const rows = this.studentBriefingContactRows
      const find = (keys) => {
        const hit = rows.find(r => keys.includes(r.key) || keys.some(k => String(r.key).startsWith(`${k}__`)))
        return hit ? hit.value : ''
      }
      return {
        name: find(['name']),
        phone: find(['phone']),
        email: find(['email'])
      }
    },
    studentBriefingContactLine () {
      return this.studentBriefingContactRows.map(r => `${r.label}：${r.value}`).join(' ')
    },
    studentBriefingBlocks () {
      const c = this.activeCompetition || {}
      const audience = String(c.target_audience || '').trim()
      const modeLine = this.participantModesSummary
      const rules = String(c.rules_text || '').trim()
      const location = String(c.location || '').trim()
      const environment = String(c.environment || '').trim()
      const blocks = []

      const audienceParsed = this.parseBriefingTracks(audience)
      if (audienceParsed.tracks.length >= 2) {
        blocks.push({
          num: '01',
          title: '参赛对象',
          kind: 'tracks',
          theme: 'cyan',
          intro: audienceParsed.intro,
          tracks: audienceParsed.tracks,
          body: audience
        })
      } else {
        blocks.push({
          num: '01',
          title: '参赛对象',
          kind: 'text',
          theme: 'cyan',
          body: audience || modeLine
        })
      }

      // 规则说明整块展示，不拆成多条图标列表
      blocks.push({
        num: '02',
        title: '规则说明',
        kind: 'text',
        theme: 'gold',
        body: rules || '作品格式、提交方式及截止时间等请以上方简介与主办方后续通知为准。'
      })

      if (location) {
        blocks.push({
          num: String(blocks.length + 1).padStart(2, '0'),
          title: '竞赛地点',
          kind: 'text',
          theme: 'violet',
          body: location
        })
      }

      if (environment) {
        const table = this.parseBriefingEnvironmentTable(environment)
        if (table) {
          blocks.push({
            num: String(blocks.length + 1).padStart(2, '0'),
            title: '竞赛环境',
            kind: 'table',
            theme: 'teal',
            table,
            body: environment
          })
        } else {
          blocks.push({
            num: String(blocks.length + 1).padStart(2, '0'),
            title: '竞赛环境',
            kind: 'text',
            theme: 'teal',
            body: environment
          })
        }
      }
      return blocks
    },
    divisionPickCompetitionName () {
      const c = this.divisionPickTarget || this.activeCompetition
      return (c && c.name) ? c.name : '该竞赛'
    },
    isActiveCompetitionDualDivision () {
      return this.isCompetitionDualDivision(this.activeCompetition)
    },
    activeDivisionLabel () {
      if (!this.activeViewDivision) return ''
      return this.activeViewDivision === 'vocational' ? '高职组' : '本科组'
    },
    enrollDivisionForApi () {
      const d = this.enrollProfileForm && this.enrollProfileForm.division
      if (d === 'undergraduate' || d === 'vocational') return d
      if (this.isActiveCompetitionDualDivision) return this.activeViewDivision
      return null
    },
    /** 已在另一学历组别报名，当前详情页组别下禁止报名（个人/组队均不可） */
    enrollBlockedByOtherDivision () {
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return false
      if (!this.activeCompetitionEnrolledDivision) return false
      return this.activeCompetitionEnrolledDivision !== this.activeViewDivision
    },
    enrollBlockedByOtherDivisionLabel () {
      return divisionToLabel(this.activeCompetitionEnrolledDivision) || '另一组别'
    },
    enrollBlockedByOtherDivisionDescription () {
      const enrolled = this.enrollBlockedByOtherDivisionLabel
      const current = this.activeDivisionLabel || '当前组别'
      return `您已在${enrolled}完成报名，不能跨组参加${current}。请从竞赛列表或「我报名的竞赛」进入${enrolled}详情继续操作。`
    },
    competitionEnrollActionsDisabled () {
      return (
        this.competitionEnrollPublishBlocked ||
        this.competitionEnrollmentClosed ||
        this.enrollBlockedByOtherDivision
      )
    },
    /** 老师已在另一学历组别组班，当前组别详情页禁止建队/邀请 */
    advisorTeamBlockedByOtherDivision () {
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return false
      if (!this.activeCompetitionAdvisorTeamDivision) return false
      return this.activeCompetitionAdvisorTeamDivision !== this.activeViewDivision
    },
    advisorTeamBlockedByOtherDivisionLabel () {
      return divisionToLabel(this.activeCompetitionAdvisorTeamDivision) || '另一组别'
    },
    advisorTeamBlockedByOtherDivisionDescription () {
      const enrolled = this.advisorTeamBlockedByOtherDivisionLabel
      const current = this.activeDivisionLabel || '当前组别'
      return `您已在${enrolled}完成组班，不能跨组在${current}建队或邀请队员。请从竞赛列表进入${enrolled}详情继续队务操作。`
    },
    advisorTeamActionsDisabled () {
      return this.competitionTeamCreateInviteBlocked || this.advisorTeamBlockedByOtherDivision
    },
    advisorTeamsForCurrentView () {
      const list = this.advisorTeams || []
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return list
      return list.filter(t => this.teamMatchesActiveViewDivision(t))
    },
    studentBriefingQrSrc () {
      return this.studentBriefingQrRemoteUrl || this.studentBriefingQrObjectUrl || ''
    },
    studentBriefingQrAlt () {
      const base = '赛事交流群二维码'
      return this.activeDivisionLabel ? `${base}（${this.activeDivisionLabel}）` : base
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
      if (s === 'draft') return '当前竞赛为草稿，尚未发布'
      if (this.competitionEnrollmentClosed) return '当前竞赛已停止报名'
      return '竞赛尚未发布或已停止报名'
    },
    competitionEnrollBlockedAlertDescription () {
      if (this.competitionEnrollmentClosed) {
        return '报名已关闭（竞赛被锁定，或已过结束时间）。此时无法创建队伍、加入队伍或新报名。请联系管理员延长结束时间或重新开放报名后再试。'
      }
      return '暂无法报名；主办方发布竞赛或重新开放报名后即可重新报名。'
    },
    /** §8.16：draft 不可提交；published / closed（锁定报名后）可提交 */
    competitionSubmissionBlocked () {
      const c = this.activeCompetition
      if (!c) return false
      const s = c.status != null ? String(c.status).toLowerCase() : ''
      if (s === 'draft') return true
      if (s === 'published' || s === 'closed' || s === 'open') return false
      return true
    },
    competitionSubmissionBlockedTitle () {
      const c = this.activeCompetition
      const s = c && c.status != null ? String(c.status).toLowerCase() : ''
      return s === 'draft' ? '当前竞赛为草稿，无法提交作品' : '竞赛尚未发布，无法提交作品'
    },
    competitionSubmissionBlockedDescription () {
      return '作品提交须在竞赛发布后进行；锁定报名（closed）后仍可提交作品。'
    },
    /** 报名弹窗/内联作品表单禁用（已提交锁定、竞赛不可提交或队伍待校审） */
    submissionFormDisabled () {
      return this.enrollModalSubmissionLocked || this.competitionSubmissionBlocked || this.teamSchoolReviewSubmissionBlocked
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
    /** 队伍已正式提交作品后，禁止转让/邀请/移除/退队 */
    competitionTeamRosterLocked () {
      if (this.hasFormalSubmittedQuestionAnswers) return true
      if (this.enrollModalSubmissionLocked) return true
      return false
    },
    competitionTeamRosterLockedMessage () {
      return '作品已提交，无法再变更队伍成员（转让、邀请、移除或退队）'
    },
    pendingTeamInvitesForActiveCompetition () {
      const cid = Number(this.activeCompetitionId)
      if (!Number.isFinite(cid)) return this.pendingTeamInvites || []
      return (this.pendingTeamInvites || []).filter(inv => Number(inv.competition_id) === cid)
    },
    showPendingTeamInvitesInEnrollModal () {
      return this.isStudent && this.pendingTeamInvitesForActiveCompetition.length > 0
    },
    /** 队员（非队长）可退队 */
    showMemberLeaveTeamInEnrollModal () {
      if (!this.isStudent || this.enrollMode !== 'team') return false
      if (!this.myEnrolledTeam || !this.myTeamId) return false
      if (this.isCurrentTeamCaptain) return false
      return true
    },
    /** 仅限制建队、邀请入队（含未发布、已停止报名、已提交作品） */
    competitionTeamCreateInviteBlocked () {
      return this.competitionEnrollPublishBlocked || this.competitionEnrollmentClosed || this.competitionTeamRosterLocked
    },
    competitionTeamCreateInviteBlockedDescription () {
      if (this.competitionTeamRosterLocked) {
        return this.competitionTeamRosterLockedMessage
      }
      if (this.competitionEnrollPublishBlocked) {
        return '竞赛尚未发布，暂无法建队或邀请队员；已发布且报名开放后可操作。'
      }
      if (this.competitionEnrollmentClosed) {
        return '报名已关闭（竞赛被锁定，或已过结束时间）。指导老师此时无法代建队伍或邀请队员；学生也无法创建/加入队伍。请联系管理员延长结束时间或重新开放报名后再试。'
      }
      return ''
    },
    competitionTeamCreateInviteBlockedTitle () {
      if (this.competitionTeamRosterLocked) return '作品已提交'
      if (this.competitionEnrollPublishBlocked) return '竞赛尚未发布'
      if (this.competitionEnrollmentClosed) return '当前竞赛已停止报名'
      return '当前不可新建队伍或邀请队员'
    },
    /** 已停止报名、未发布或已提交作品时不可移除队员 */
    competitionTeamRemoveMemberBlocked () {
      return this.competitionEnrollPublishBlocked || this.competitionEnrollmentClosed || this.competitionTeamRosterLocked
    },
    competitionTeamRemoveMemberBlockedMessage () {
      if (this.competitionTeamRosterLocked) {
        return this.competitionTeamRosterLockedMessage
      }
      if (this.competitionEnrollPublishBlocked) {
        return '竞赛尚未发布，暂无法移除队员'
      }
      if (this.competitionEnrollmentClosed) {
        return '竞赛已停止报名，暂无法移除队员'
      }
      return ''
    },
    advisorTeamsTableData () {
      return this.advisorTeamsForCurrentView.map(t => ({
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
      return this.advisorTeamsForCurrentView.find(t => Number(t.id) === Number(this.advisorSelectedTeamId)) || null
    },
    advisorSelectedTeamAdvisorLabel () {
      const t = this.advisorSelectedTeam
      if (!t) return '-'
      const name = t.advisor_name != null ? String(t.advisor_name).trim() : ''
      if (name) return name
      if (t.created_by_advisor_id != null) return String(t.created_by_advisor_id)
      return this.altCurrentUserDisplayName || '-'
    },
    advisorSelectedTeamMembers () {
      const t = this.advisorSelectedTeam
      if (!t || !Array.isArray(t.members)) return []
      return t.members.filter(m => m && !m.is_captain)
    },
    myTeamMembersNonCaptain () {
      return (this.myTeamMembers || []).filter(m => m && !m.is_captain)
    },
    advisorSelectedTeamCaptainLabel () {
      const t = this.advisorSelectedTeam
      if (!t) return '-'
      const captain = (t.members || []).find(m => m && m.is_captain)
      if (captain) {
        const name = this.formatTeamMemberDisplayName(captain)
        return captain.user_id != null ? `${name}（ID ${captain.user_id}）` : name
      }
      return t.captain_id != null ? `用户 #${t.captain_id}` : '-'
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
    /** 标题拆成主体 + 阶段后缀（名称含初赛/决赛时着色突出） */
    competitionHeroTitleParts () {
      const c = this.activeCompetition
      const name = c ? String(c.name || '').trim() : ''
      if (!name) return { base: '', stage: '' }
      const stageLabel = this.activeCompetitionStageLabel
      if (stageLabel && name.includes(stageLabel)) {
        const idx = name.lastIndexOf(stageLabel)
        const before = name.slice(0, idx).replace(/[-—–\s（(]+$/, '').trim()
        if (before) {
          return { base: before, stage: stageLabel }
        }
      }
      return { base: name, stage: '' }
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
      const paras = this.competitionHeroSloganParagraphs
      return paras.length ? paras.join(' ') : ''
    },
    /** 头图描述：拆成 2～3 段短句 */
    competitionHeroSloganParagraphs () {
      const c = this.activeCompetition
      const name = c ? String(c.name || '').trim() : ''
      const lines = this.competitionHeroDescLines
      const en = this.competitionHeroSubtitleEn
      const rest = (en ? lines.slice(1) : lines).filter(p => p && p !== name)
      let text = rest.join('\n').trim()
      if (!text && c && c.rules_text) {
        text = String(c.rules_text).split(/\r?\n+/).map(s => s.trim()).filter(Boolean).join('\n')
      }
      if (!text) return []
      // 已有换行则优先按行；否则按句号拆成短句
      let parts = text.split(/\r?\n+/).map(s => s.trim()).filter(Boolean)
      if (parts.length === 1) {
        const one = parts[0]
        const sentences = one.match(/[^。！？!?]+[。！？!?]?/g) || [one]
        parts = sentences.map(s => s.trim()).filter(Boolean)
      }
      return parts.slice(0, 3)
    },
    competitionHeroDateRange () {
      const c = this.activeCompetition
      if (!c) return '-'
      return this.formatHeroDateRange(c.start_at, c.end_at)
    },
    /** 活动时间状态：未开始 / 即将截止 / 已结束 */
    competitionHeroTimeHint () {
      const c = this.activeCompetition
      if (!c) return null
      const now = Date.now()
      const start = c.start_at ? new Date(c.start_at).getTime() : NaN
      const end = c.end_at ? new Date(c.end_at).getTime() : NaN
      const dayMs = 24 * 60 * 60 * 1000
      if (!Number.isNaN(end) && now > end) {
        return { text: '活动已结束', tone: 'ended' }
      }
      if (!Number.isNaN(start) && now < start) {
        const days = Math.ceil((start - now) / dayMs)
        if (days <= 1) return { text: '即将开始', tone: 'soon' }
        return { text: `距开始还有 ${days} 天`, tone: 'soon' }
      }
      if (!Number.isNaN(end) && now <= end) {
        const remain = end - now
        const days = Math.ceil(remain / dayMs)
        if (remain <= dayMs) {
          const hours = Math.max(1, Math.ceil(remain / (60 * 60 * 1000)))
          return { text: `距截止还剩 ${hours} 小时`, tone: 'urgent' }
        }
        if (days <= 7) {
          return { text: `距截止还剩 ${days} 天`, tone: 'urgent' }
        }
        return null
      }
      if (c.status === 'closed') {
        return { text: '活动已结束', tone: 'ended' }
      }
      return null
    },
    canEditSummaryScores () {
      return this.isSuperAdmin
    },
    summaryScoreTableColumns () {
      const qCols = this.buildQuestionScoreColumns(null, {
        dataIndexPrefix: 'score_q',
        width: 100,
        useScopedSlots: true
      })
      const cols = [
        { title: '队伍名称', dataIndex: 'team_name', key: 'team_name', ellipsis: true, width: 140 },
        { title: '学校', dataIndex: 'school', key: 'school', ellipsis: true, width: 140 },
        { title: '指导老师', dataIndex: 'advisor_name', key: 'advisor_name', ellipsis: true, width: 100 },
        { title: '队长', dataIndex: 'captain_name', key: 'captain_name', ellipsis: true, width: 100 },
        { title: '队员', dataIndex: 'members', key: 'members', ellipsis: true, width: 180 },
        ...qCols,
        { title: '总分', dataIndex: 'total_score', key: 'total_score', width: 80, scopedSlots: { customRender: 'total_score' } }
      ]
      if (this.canEditSummaryScores) {
        cols.push({ title: '操作', key: 'actions', width: 80, fixed: 'right', scopedSlots: { customRender: 'actions' } })
      }
      return cols
    },
    rankingsTableData () {
      const r = this.scoresRankings
      if (!r || !Array.isArray(r.items)) return []
      return (r.items || []).map((item, index) => ({
        rowIndex: item.rank != null ? item.rank : index + 1,
        team_id: item.team_id != null ? item.team_id : '-',
        team_name: item.team_name || (item.team_id != null ? `队伍${item.team_id}` : '-'),
        school: item.school || '-',
        advisor_name: item.advisor_name || '-',
        captain_name: item.captain_name || (item.captain_id != null ? String(item.captain_id) : '-'),
        members: item.members || '-',
        score_q1: this.formatQuestionScoreCell(item.score_q1),
        score_q2: this.formatQuestionScoreCell(item.score_q2),
        score_q3: this.formatQuestionScoreCell(item.score_q3),
        score_q4: this.formatQuestionScoreCell(item.score_q4),
        score_q5: this.formatQuestionScoreCell(item.score_q5),
        best_score: item.best_score != null ? item.best_score : '-',
        key: `rank-${index}`
      }))
    },
    gradeFormAutoTotal () {
      const items = this.gradeFormQuestionItems || []
      const nums = items.map(q => parseFloat(this.gradeForm['score_q' + q.no]))
      if (!nums.length || nums.some(v => Number.isNaN(v))) return '—'
      const sum = nums.reduce((a, b) => a + b, 0)
      return String(Math.round(sum * 100) / 100)
    },
    gradeFormUsesQuestionScores () {
      return !!this.gradeForm.team_id || this.gradeForm.work_track === 'works'
    },
    gradeFormTrackLabel () {
      const t = this.gradeForm && this.gradeForm.work_track
      if (t === 'works') return '作品赛道'
      if (t === 'software') return '软件赛道'
      if (t === 'hardware') return '硬件赛道'
      return ''
    },
    gradeFormQuestionItems () {
      return this.getQuestionItemsForTrack(this.gradeForm.work_track)
    },
    myTeamGradesTableData () {
      const payload = this.myScores
      const list = payload && Array.isArray(payload.team_grades) ? payload.team_grades : []
      return list.map(item => ({
        team_id: item.team_id,
        score_q1: this.formatQuestionScoreCell(item.score_q1),
        score_q2: this.formatQuestionScoreCell(item.score_q2),
        score_q3: this.formatQuestionScoreCell(item.score_q3),
        score_q4: this.formatQuestionScoreCell(item.score_q4),
        score_q5: this.formatQuestionScoreCell(item.score_q5),
        total_score: this.formatQuestionScoreCell(item.total_score)
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
    '$route.query.page' () {
      this.applyAdminSubmissionsPaginationFromRoute(false)
    },
    '$route.query.page_size' () {
      this.applyAdminSubmissionsPaginationFromRoute(false)
    },
    activeCompetitionId (newId) {
      this.advisorCreatedTeamIds = []
      this.studentCreatedTeamInCurrentCompetition = false
      this.teamEnrollmentEligible = false
      this.myTeamId = null
      this.myTeamName = null
      this.myTeamAdvisorName = null
      this.myTeamStatus = null
      this.myTeamWorkTrack = null
      this.joinTeamId = null
      this.joinTeamName = ''
      this.teamJoinRequests = []
      this.teamJoinRequestReviewingId = null
      this.studentTeamInviteRef = ''
      this.studentTeamRemoveRef = ''
      this.newCaptainRef = ''
      this.submissionTeamId = null
      this.questionAnswerSlots = []
      this.questionAnswerUploadingNo = null
      this.activeCompetitionMyEnrollKind = null
      this.activeCompetitionEnrollmentId = null
      this.myEnrolledIndividual = false
      this.myEnrolledTeam = false
      this.activeCompetitionEnrollmentRows = { individual: null, team: null, teams: [] }
      this.preferredEnrollmentWorkTrack = null
      this.activeCompetitionEnrolledDivision = null
      this.activeCompetitionAdvisorTeamDivision = null
      this.studentDivisionByUserId = null
      this.studentDivisionIndexCompetitionId = null
      this.ignoreSubmissionsBeforeReenrollAt = null
      this.enrollMode = 'team'
      this.submissionMode = 'team'

      this.publishCompetitionId = newId

      if (newId !== null && newId !== undefined && newId !== '' && this.isStudent) {
        void this.refreshMySubmissions().then(async () => {
          if (this.activeCompetitionId !== newId) return
          await this.refreshActiveCompetitionMyEnrollKind()
          this.applyStoredWithdrawSubmissionCutoff()
          await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
          await this.refreshQuestionAnswersBoard()
        })
      }

      if (newId !== null && newId !== undefined && newId !== '' && this.canViewCompetitionSubmissions) {
        this.resetAdminSubmissionsPagination()
        if (this.standaloneDetailMode) {
          this.refreshAdminSubmissions()
        } else {
          this.adminSubmissions = []
        }
      } else {
        this.adminSubmissions = []
        this.adminSubmissionsTotal = 0
      }

      if (this.standaloneDetailMode) {
        this.applyActiveViewDivisionFromRoute()
        if (newId !== null && newId !== undefined && newId !== '') {
          void this.ensureCompetitionDetail(newId).then(() => {
            if (String(this.activeCompetitionId) !== String(newId)) return
            this.syncDualDivisionContextAfterCompetitionSelect()
            this.notifyEnrollBlockChanged()
            if (this.showStandaloneCompetitionBriefingLayout) void this.fetchStudentBriefingQr()
          })
        }
      } else if (!this.isCompetitionDualDivision(this.activeCompetition)) {
        this.activeViewDivision = null
        this.$nextTick(() => this.syncDualDivisionContextAfterCompetitionSelect())
      } else {
        this.$nextTick(() => this.syncDualDivisionContextAfterCompetitionSelect())
      }

      if (newId === null || newId === undefined || newId === '') {
        this.revokeStudentBriefingQrObjectUrl()
      } else if (this.showStandaloneCompetitionBriefingLayout) {
        void this.fetchStudentBriefingQr()
      }

      if (newId !== null && newId !== undefined && newId !== '') {
        this.advisorSelectedTeamId = null
        this.advisorRenameName = ''
        this.advisorInviteStudent = ''
        if (this.showAdvisorTeamPanel) {
          void this.refreshAdvisorTeams()
        } else {
          this.advisorTeams = []
        }
      } else {
        this.advisorTeams = []
        this.advisorSelectedTeamId = null
      }

      if (newId !== null && newId !== undefined && newId !== '' && this.canManageCompetitions) {
        this.$nextTick(() => {
          if (this.isActiveCompetitionPreliminary || this.isActiveCompetitionFinal) {
            void this.refreshPromotionList()
          } else {
            this.promotionList = []
          }
        })
      } else {
        this.promotionList = []
      }

      this.emitCatalogLogoChanged()
    },
    enrollMode (newMode) {
      this.submissionMode = newMode
      if (newMode === 'team' && this.myTeamId) this.submissionTeamId = this.myTeamId
      this.applyEnrollmentContextFromRows()
    },
    myTeamId (newId, oldId) {
      if (this.submissionTeamId == null && newId) this.submissionTeamId = newId
      if (Number(newId) === Number(oldId)) return
      if (newId && this.enrollMode === 'team') {
        void this.syncEnrollModalTeamContextForCurrentTrack()
      } else if (!newId) {
        this.myTeamStatus = null
        this.myTeamName = null
        this.myTeamAdvisorName = null
        this.myTeamWorkTrack = null
        this.myTeamMembers = []
        this.teamJoinRequests = []
        this.questionAnswerSlots = []
        this.transferTeamId = null
        this.leaveTeamId = null
      }
    },
    showCreateCompetitionModal (visible) {
      if (visible) {
        this.resetCreateCompetitionForm()
      }
    },
    showStandaloneEnrollModal (visible) {
      if (visible && this.standaloneDetailMode) {
        this.$nextTick(() => {
          this.syncEnrollProfileDefaults()
          if (this.enrollMode === 'team' && this.myTeamId) {
            void this.syncEnrollModalTeamContextForCurrentTrack()
          }
        })
      }
      if (!visible) {
        this.teamJoinRequests = []
        this.myTeamMembers = []
      }
    },
    initialViewDivision (val) {
      const div = this.normalizeViewDivision(val)
      if (div === this.activeViewDivision) return
      this.activeViewDivision = div
      if (this.standaloneDetailMode && this.activeCompetitionId) {
        void this.fetchStudentBriefingQr()
        void this.refreshActiveCompetitionMyEnrollKind()
      }
      if (this.showAdvisorTeamPanel && this.activeCompetitionId) {
        this.advisorSelectedTeamId = null
        this.advisorRenameName = ''
        this.advisorInviteStudent = ''
        void this.refreshAdvisorTeams()
      }
      if (this.activeCompetitionId) {
        if (this.isStudent) void this.refreshMySubmissions()
        if (this.canViewCompetitionSubmissions) {
          this.resetAdminSubmissionsPagination()
          void this.refreshAdminSubmissions()
        }
        if (this.canViewScoreAnalytics && this.scoresSummary) {
          void this.refreshScoresSummary(false)
        }
        if (this.canViewScoreAnalytics && this.showScoresRankingsModal) {
          void this.refreshRankings()
        }
      }
    }
  },
  mounted () {
    this.applyAdminSubmissionsPaginationFromRoute(true)
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
    this.revokeCreateQrPreviewUrls()
    this.revokeEditCurrentQrPreviews()
    this.clearEditSharedQrUpload()
    this.clearEditSeparateQrUploads()
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

    normalizeViewDivision (value) {
      if (value === 'undergraduate' || value === 'vocational') return value
      return null
    },

    findCompetitionById (id) {
      if (id == null || id === '') return null
      const sid = String(id)
      return (
        (this.competitions || []).find(c => String(c.id) === sid) ||
        this.filteredCompetitions.find(c => String(c.id) === sid) ||
        null
      )
    },

    mergeCompetitionIntoList (detail) {
      if (!detail || detail.id == null) return
      const sid = String(detail.id)
      const idx = (this.competitions || []).findIndex(c => String(c.id) === sid)
      if (idx >= 0) {
        this.$set(this.competitions, idx, { ...this.competitions[idx], ...detail })
      } else {
        this.competitions = [...(this.competitions || []), detail]
      }
      this.emitCatalogLogoChanged()
    },

    /** §8.1.1：是否弹「本科/高职」选择框，以详情接口 division_mode === 'dual' 为准 */
    isCompetitionDualDivision (comp) {
      if (!comp || typeof comp !== 'object') return false
      const mode = comp.division_mode != null ? comp.division_mode : comp.divisionMode
      return String(mode).toLowerCase() === 'dual'
    },

    divisionPickModalGetContainer () {
      return document.body
    },

    /** GET /v1/competitions/{id}（§8.1.1），合并进列表缓存后返回 */
    async ensureCompetitionDetail (competitionId) {
      if (competitionId == null || competitionId === '') return null
      try {
        const detail = await getCompetition(competitionId)
        if (detail && typeof detail === 'object') {
          this.mergeCompetitionIntoList(detail)
          return this.findCompetitionById(competitionId) || detail
        }
      } catch (e) {
        /* 无权限或接口不可用时退回列表项 */
      }
      return this.findCompetitionById(competitionId)
    },

    resolveCompetitionQrAbsoluteUrl (url) {
      if (!url) return null
      const s = String(url).trim()
      if (!s) return null
      if (/^https?:\/\//i.test(s)) return s
      if (s.startsWith('/')) {
        // Vue CLI 注入；eslint 环境未声明 process
        // eslint-disable-next-line no-undef
        const base = (process.env.VUE_APP_API_BASE_URL || '/api').replace(/\/$/, '')
        return base + s
      }
      return s
    },

    getCompetitionQrUrlForView (comp, division) {
      if (!comp) return null
      const urls = this.resolveCompetitionQrUrls(comp)
      if (!this.isCompetitionDualDivision(comp)) {
        return this.resolveCompetitionQrAbsoluteUrl(urls.shared)
      }
      const layout = comp.qr_layout || 'shared'
      if (layout === 'shared' || !division) {
        return this.resolveCompetitionQrAbsoluteUrl(urls.shared)
      }
      if (division === 'undergraduate') {
        return this.resolveCompetitionQrAbsoluteUrl(urls.undergraduate) ||
          this.resolveCompetitionQrAbsoluteUrl(urls.shared)
      }
      if (division === 'vocational') {
        return this.resolveCompetitionQrAbsoluteUrl(urls.vocational) ||
          this.resolveCompetitionQrAbsoluteUrl(urls.shared)
      }
      return this.resolveCompetitionQrAbsoluteUrl(urls.shared)
    },

    enrollmentMatchesActiveViewDivision (row) {
      if (!this.activeViewDivision) return true
      if (!row || typeof row !== 'object') return false
      const d = row.division
      if (d == null || String(d).trim() === '') return true
      return String(d) === this.activeViewDivision
    },

    resolveTeamDivisionWithCache (team) {
      if (!team || typeof team !== 'object') return null
      const fromTeam = resolveTeamDivision(team)
      if (fromTeam) return fromTeam
      const cid = this.activeCompetitionId
      const tid = team.id != null ? team.id : team.team_id
      if (cid && tid != null) return getCompetitionTeamDivision(cid, tid)
      return null
    },

    teamMatchesActiveViewDivision (team) {
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return true
      const d = this.resolveTeamDivisionWithCache(team)
      if (!d) return true
      return d === this.activeViewDivision
    },

    syncActiveCompetitionAdvisorTeamDivision (teams) {
      if (!this.isActiveCompetitionDualDivision) {
        this.activeCompetitionAdvisorTeamDivision = null
        return
      }
      let division = null
      for (const team of teams || []) {
        if (!this.canAdvisorOperateTeam(team)) continue
        const d = this.resolveTeamDivisionWithCache(team)
        if (d === 'undergraduate' || d === 'vocational') {
          division = d
          break
        }
      }
      this.activeCompetitionAdvisorTeamDivision = division
    },

    assertAdvisorNotBlockedByOtherDivision (showToast = true) {
      if (!this.advisorTeamBlockedByOtherDivision) return true
      if (showToast) this.$message.warning(this.advisorTeamBlockedByOtherDivisionDescription)
      return false
    },

    assertSelectedAdvisorTeamMatchesView (showToast = true) {
      const team = this.advisorSelectedTeam
      if (!team || !this.isActiveCompetitionDualDivision || !this.activeViewDivision) return true
      if (this.teamMatchesActiveViewDivision(team)) return true
      if (showToast) {
        this.$message.warning(`当前队伍不属于${this.activeDivisionLabel || '本组别'}，请切换到对应组别详情页后再操作`)
      }
      return false
    },

    async ensureStudentDivisionIndex () {
      const cid = this.activeCompetitionId
      if (!cid || !this.isActiveCompetitionDualDivision) return
      if (!this.canViewParticipantsRoster) return
      if (!this.assertCompetitionDivisionQueryContext(false)) return
      if (
        this.studentDivisionIndexCompetitionId === cid &&
        this.studentDivisionByUserId &&
        typeof this.studentDivisionByUserId === 'object'
      ) {
        return
      }
      const map = {}
      try {
        const divOpts = this.buildCompetitionDivisionQueryOptions()
        const [indRes, teamRes] = await Promise.all([
          getCompetitionParticipantsIndividual(cid, divOpts),
          getCompetitionParticipantsTeams(cid, divOpts)
        ])
        for (const row of normalizeCompetitionApiList(indRes)) {
          const uid = row.student_id != null ? row.student_id : row.user_id
          const div = resolveEnrollmentDivision(row)
          if (uid != null && div) map[Number(uid)] = div
        }
        for (const t of normalizeCompetitionApiList(teamRes)) {
          const tdiv =
            resolveTeamDivision(t) ||
            getCompetitionTeamDivision(cid, t.id != null ? t.id : t.team_id)
          if (Array.isArray(t.members)) {
            for (const m of t.members) {
              const uid = m.user_id
              const div = resolveEnrollmentDivision(m) || tdiv
              if (uid != null && div) map[Number(uid)] = div
            }
          }
        }
      } catch (_) {
        /* 无参赛者列表权限时仅依赖后端邀请校验 */
      }
      this.studentDivisionByUserId = map
      this.studentDivisionIndexCompetitionId = cid
    },

    async assertInviteeSameDivisionAsView (studentId, showToast = true) {
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return true
      const sid = Number(studentId)
      if (!Number.isFinite(sid) || sid <= 0) return true
      await this.ensureStudentDivisionIndex()
      const map = this.studentDivisionByUserId
      const div = map && map[sid]
      if (!div) return true
      if (div === this.activeViewDivision) return true
      const label = divisionToLabel(div) || '另一组别'
      const current = this.activeDivisionLabel || '当前组别'
      if (showToast) {
        this.$message.warning(`该学生属于${label}，不能邀请至${current}队伍`)
      }
      return false
    },

    async assertStudentsSameDivisionAsView (studentIds, showToast = true) {
      if (!this.isActiveCompetitionDualDivision || !this.activeViewDivision) return true
      const ids = [...new Set((studentIds || []).map(id => Number(id)).filter(id => Number.isFinite(id) && id > 0))]
      if (!ids.length) return true
      await this.ensureStudentDivisionIndex()
      const map = this.studentDivisionByUserId || {}
      for (const sid of ids) {
        const div = map[sid]
        if (!div) continue
        if (div !== this.activeViewDivision) {
          const label = divisionToLabel(div) || '另一组别'
          const current = this.activeDivisionLabel || '当前组别'
          if (showToast) {
            this.$message.warning(`学生 ID ${sid} 属于${label}，不能加入${current}队伍`)
          }
          return false
        }
      }
      return true
    },

    mapTeamInviteDetailToUserMessage (detailText) {
      const t = (detailText || '').toLowerCase()
      if (t.includes('division must match') || t.includes('division mismatch')) {
        return '邀请学生与队伍/详情页组别不一致，请确认学生与本页面为同一组别（本科组或高职组）'
      }
      if (t.includes('already enrolled in division')) {
        return '该学生已在另一学历组别报名，不能跨组入队'
      }
      if (/同一学校|same school|学校不一致|must.*same.*school|未配置学校.*组队/i.test(detailText || '')) {
        return String(detailText || '').trim() || '仅允许同一学校的学生组队'
      }
      return null
    },

    applyActiveViewDivisionFromRoute () {
      const div = this.normalizeViewDivision(this.initialViewDivision)
      this.activeViewDivision = div
    },

    syncDualDivisionContextAfterCompetitionSelect () {
      const comp = this.activeCompetition
      if (!this.isCompetitionDualDivision(comp)) {
        this.activeViewDivision = null
        this.showDivisionPickModal = false
        this.divisionPickTarget = null
        return
      }
      if (this.activeViewDivision) {
        if (this.showStandaloneCompetitionBriefingLayout) {
          void this.fetchStudentBriefingQr()
        }
        return
      }
      if (this.standaloneDetailMode) {
        this.divisionPickTarget = comp
        this.showDivisionPickModal = true
      }
    },

    async openCompetitionDetailInNewTab (id) {
      if (id == null) return
      const hideLoading = this.$message.loading('正在加载竞赛信息…', 0)
      try {
        const comp = await this.ensureCompetitionDetail(id)
        if (this.isCompetitionDualDivision(comp)) {
          this.divisionPickTarget = comp || { id, name: `竞赛 #${id}` }
          this.showDivisionPickModal = true
          return
        }
        this.navigateCompetitionDetailInNewTab(id, null)
      } catch (e) {
        this.$message.error('加载竞赛详情失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        if (typeof hideLoading === 'function') hideLoading()
      }
    },

    navigateCompetitionDetailInNewTab (id, division) {
      if (id == null) return
      try {
        const query = { id: String(id), fromList: '1' }
        const div = this.normalizeViewDivision(division)
        if (div) query.division = div
        const location = { name: 'ManuCompetitionDetail', query }
        const url = buildAbsoluteRouteUrl(this.$router, location)
        // 勿用 openRouteInNewTab 的返回值判断成败：noopener 下常为 null，但新标签已打开
        const opened = window.open(url, '_blank')
        if (!opened) {
          this.$message.warning('无法打开新标签页，请检查浏览器是否拦截了弹窗')
        }
      } catch (e) {
        this.$message.error('无法打开竞赛详情页')
      }
    },

    /** 生成竞赛详情页完整 URL（供超级管理员复制分享；带 share=1 表示默认未登录访客页） */
    buildCompetitionDetailPageUrl (id, division) {
      if (id == null || id === '') return ''
      try {
        const query = { id: String(id), share: '1' }
        const div = this.normalizeViewDivision(division)
        if (div) query.division = div
        return buildAbsoluteRouteUrl(this.$router, {
          name: 'ManuCompetitionDetail',
          query
        })
      } catch (e) {
        return ''
      }
    },

    buildCompetitionDetailUrlEntries (comp) {
      const id = comp && comp.id
      if (id == null || id === '') return []
      if (this.isCompetitionDualDivision(comp)) {
        return [
          {
            label: '本科组',
            url: this.buildCompetitionDetailPageUrl(id, 'undergraduate')
          },
          {
            label: '高职组',
            url: this.buildCompetitionDetailPageUrl(id, 'vocational')
          }
        ]
      }
      return [
        {
          label: '竞赛详情',
          url: this.buildCompetitionDetailPageUrl(id, null)
        }
      ]
    },

    showCompetitionUrlModalWithComp (comp) {
      const id = comp && comp.id
      if (id == null || id === '') return
      if (!this.isCompetitionShareableStatus(comp && comp.status)) {
        this.$message.warning('竞赛尚未发布，暂无法生成分享链接。请先发布竞赛。')
        return
      }
      this.competitionUrlModalTitle = (comp && comp.name) ? comp.name : `竞赛 #${id}`
      this.competitionUrlModalLines = this.buildCompetitionDetailUrlEntries(comp)
      this.showCompetitionUrlModal = true
    },

    async openCompetitionUrlModal (record) {
      if (!this.isSuperAdmin || !record || record.id == null) return
      let comp = this.findCompetitionById(record.id)
      if (!comp || comp.division_mode == null || comp.status == null) {
        comp = await this.ensureCompetitionDetail(record.id) || comp
      }
      const merged = comp || { id: record.id, name: record.name, status: record.status }
      if (!this.isCompetitionShareableStatus(merged.status)) {
        this.$message.warning('竞赛尚未发布，暂无法生成分享链接。请先发布竞赛。')
        return
      }
      this.showCompetitionUrlModalWithComp(merged)
    },

    closeCompetitionUrlModal () {
      this.showCompetitionUrlModal = false
      this.competitionUrlModalTitle = ''
      this.competitionUrlModalLines = []
    },

    isCompetitionShareableStatus (status) {
      const s = String(status || '').toLowerCase()
      return s === 'published' || s === 'closed'
    },

    async openExamPaperPublishModal () {
      if (!this.canPublishExamPaperForSelected) {
        this.$message.warning('请先发布竞赛后再发布试卷')
        return
      }
      const record = this.selectedCompetitionRecord
      if (!record || record.id == null) return
      let comp = record
      if (comp.division_mode == null) {
        comp = await this.ensureCompetitionDetail(record.id) || record
      }
      this.examPaperModalCompetitionId = comp.id
      this.examPaperModalCompetitionName = comp.name || `竞赛 #${comp.id}`
      this.examPaperModalIsDual = this.isCompetitionDualDivision(comp)
      this.examPaperModalActiveDivision = 'undergraduate'
      this.examPaperTrackFiles = {}
      this.examPaperTrackFileLists = {}
      this.examPaperMeta = null
      this.resetExamPaperQuestionConfig()
      this.showExamPaperPublishModal = true
      try {
        this.examPaperMeta = await getCompetitionExamPapers(comp.id)
      } catch (e) {
        this.examPaperMeta = null
      }
      try {
        const cfg = await getSubmissionQuestionConfig(comp.id)
        this.applyExamPaperQuestionConfig(cfg)
      } catch (e) {
        /* 使用默认配置 */
      }
    },

    closeExamPaperPublishModal () {
      this.showExamPaperPublishModal = false
      this.examPaperModalCompetitionId = null
      this.examPaperModalCompetitionName = ''
      this.examPaperModalIsDual = false
      this.examPaperModalActiveDivision = 'default'
      this.examPaperMeta = null
      this.examPaperTrackFiles = {}
      this.examPaperTrackFileLists = {}
    },

    examPaperDivisionLabel (divKey) {
      if (divKey === 'undergraduate') return '本科组'
      if (divKey === 'vocational') return '高职组'
      return '未分组别'
    },

    examPaperTrackPublishedMeta (divKey, track) {
      const byTrack = this.examPaperMeta && this.examPaperMeta.by_track
      const slot = byTrack && byTrack[divKey] && byTrack[divKey][track]
      if (slot && slot.published) return slot
      return null
    },

    examPaperTrackFileList (divKey, track) {
      const key = `${divKey}__${track}`
      return (this.examPaperTrackFileLists && this.examPaperTrackFileLists[key]) || []
    },

    _examPaperUploadFileItem (file) {
      return {
        uid: `exam-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: file.name,
        status: 'done',
        originFileObj: file
      }
    },

    beforeExamPaperTrackUpload (divKey, track, file) {
      const key = `${divKey}__${track}`
      this.$set(this.examPaperTrackFiles, key, file)
      this.$set(this.examPaperTrackFileLists, key, [this._examPaperUploadFileItem(file)])
      return false
    },

    removeExamPaperTrack (divKey, track) {
      const key = `${divKey}__${track}`
      this.$set(this.examPaperTrackFiles, key, null)
      this.$set(this.examPaperTrackFileLists, key, [])
    },

    resetExamPaperQuestionConfig () {
      const make = () => ({
        question_count: 5,
        questions: [1, 2, 3, 4, 5].map(n => ({
          no: n,
          name: `第${n}题`,
          min_score: 0,
          max_score: 100
        })),
        total_min_score: 0,
        total_max_score: 500
      })
      this.examPaperQuestionConfigByTrack = {
        works: make(),
        software: make(),
        hardware: make()
      }
    },

    _normalizeOneTrackQuestionConfig (cfg) {
      if (!cfg || typeof cfg !== 'object') {
        return {
          question_count: 5,
          questions: [1, 2, 3, 4, 5].map(n => ({ no: n, name: `第${n}题`, min_score: 0, max_score: 100 })),
          total_min_score: 0,
          total_max_score: 500
        }
      }
      const count = Math.max(1, Math.min(5, Number(cfg.question_count) || 5))
      const byNo = {}
      ;(cfg.questions || []).forEach((q) => {
        if (q && q.no != null) byNo[Number(q.no)] = q
      })
      return {
        question_count: count,
        questions: Array.from({ length: count }, (_, i) => {
          const n = i + 1
          const src = byNo[n] || {}
          return {
            no: n,
            name: src.name || `第${n}题`,
            min_score: src.min_score != null ? Number(src.min_score) : 0,
            max_score: src.max_score != null ? Number(src.max_score) : 100
          }
        }),
        total_min_score: cfg.total_min_score != null ? Number(cfg.total_min_score) : 0,
        total_max_score: cfg.total_max_score != null ? Number(cfg.total_max_score) : count * 100
      }
    },

    applyExamPaperQuestionConfig (cfg) {
      if (!cfg || typeof cfg !== 'object') return
      if (cfg.works || cfg.software || cfg.hardware || (!cfg.question_count && !cfg.questions)) {
        this.examPaperQuestionConfigByTrack = {
          works: this._normalizeOneTrackQuestionConfig(cfg.works),
          software: this._normalizeOneTrackQuestionConfig(cfg.software),
          hardware: this._normalizeOneTrackQuestionConfig(cfg.hardware)
        }
        return
      }
      const shared = this._normalizeOneTrackQuestionConfig(cfg)
      this.examPaperQuestionConfigByTrack = {
        works: this._normalizeOneTrackQuestionConfig(null),
        software: JSON.parse(JSON.stringify(shared)),
        hardware: JSON.parse(JSON.stringify(shared))
      }
    },

    onExamPaperQuestionCountChange (trackKey, n) {
      const count = Math.max(1, Math.min(5, Number(n) || 5))
      if (!this.examPaperQuestionConfigByTrack[trackKey]) {
        this.$set(this.examPaperQuestionConfigByTrack, trackKey, this._normalizeOneTrackQuestionConfig(null))
      }
      const trackCfg = this.examPaperQuestionConfigByTrack[trackKey]
      if (!trackCfg) return
      const prev = trackCfg.questions || []
      const byNo = {}
      prev.forEach((q) => { if (q && q.no != null) byNo[Number(q.no)] = q })
      trackCfg.question_count = count
      trackCfg.questions = Array.from({ length: count }, (_, i) => {
        const no = i + 1
        const src = byNo[no] || {}
        return {
          no,
          name: src.name || `第${no}题`,
          min_score: src.min_score != null ? Number(src.min_score) : 0,
          max_score: src.max_score != null ? Number(src.max_score) : 100
        }
      })
      const sumMax = trackCfg.questions.reduce((s, q) => s + (Number(q.max_score) || 0), 0)
      trackCfg.total_max_score = sumMax
    },

    async submitExamPaperPublish () {
      const id = this.examPaperModalCompetitionId
      if (id == null) return
      const uploads = []
      Object.keys(this.examPaperTrackFiles || {}).forEach((key) => {
        const file = this.examPaperTrackFiles[key]
        if (!file) return
        const parts = key.split('__')
        if (parts.length !== 2) return
        uploads.push({ division: parts[0], work_track: parts[1], file })
      })
      const byTrack = this.examPaperQuestionConfigByTrack
      const pack = (trackKey) => {
        const cfg = byTrack[trackKey] || {}
        return {
          question_count: cfg.question_count,
          questions: (cfg.questions || []).map(q => ({
            no: q.no,
            name: q.name || `第${q.no}题`,
            min_score: Number(q.min_score) || 0,
            max_score: Number(q.max_score) || 100
          })),
          total_min_score: Number(cfg.total_min_score) || 0,
          total_max_score: Number(cfg.total_max_score) || 500
        }
      }
      this.examPaperUploading = true
      try {
        let lastMeta = this.examPaperMeta
        for (const item of uploads) {
          const fd = new FormData()
          fd.append('division', item.division)
          fd.append('work_track', item.work_track)
          fd.append('file', item.file)
          lastMeta = await uploadCompetitionExamPaper(id, fd)
        }
        await putSubmissionQuestionConfig(id, {
          works: pack('works'),
          software: pack('software'),
          hardware: pack('hardware')
        })
        this.examPaperMeta = lastMeta
        this.$message.success(uploads.length ? '试卷与题目配置已保存' : '题目配置已保存')
        this.closeExamPaperPublishModal()
        if (this.activeCompetitionId != null && String(this.activeCompetitionId) === String(id)) {
          void this.refreshExamPapersForDetail()
          void this.refreshActiveSubmissionQuestionConfig()
        }
      } catch (e) {
        this.$message.error('发布试卷失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.examPaperUploading = false
      }
    },

    async refreshActiveSubmissionQuestionConfig () {
      const id = this.activeCompetitionId
      if (id == null || id === '') {
        this.activeSubmissionQuestionConfig = null
        return
      }
      try {
        this.activeSubmissionQuestionConfig = await getSubmissionQuestionConfig(id)
      } catch (e) {
        this.activeSubmissionQuestionConfig = null
      }
    },

    async refreshExamPapersForDetail () {
      const id = this.activeCompetitionId
      if (id == null || id === '') {
        this.examPapersForDetail = null
        this.$emit('exam-papers-changed')
        return
      }
      if (!this.isUsingAltIdentity) {
        this.examPapersForDetail = null
        this.$emit('exam-papers-changed')
        return
      }
      try {
        this.examPapersForDetail = await getCompetitionExamPapers(id)
      } catch (e) {
        this.examPapersForDetail = null
      }
      this.$emit('exam-papers-changed')
      void this.refreshActiveSubmissionQuestionConfig()
    },

    async downloadActiveExamPaper () {
      const id = this.activeCompetitionId
      const div = this.examPaperDownloadDivision
      const track = this.examPaperDownloadWorkTrack
      if (id == null || !div) {
        this.$message.warning('无法确定试卷组别')
        return
      }
      if (!track) {
        this.$message.warning('无法确定报名赛道，请先完成报名/建队')
        return
      }
      this.examPaperDownloadLoading = true
      try {
        const blob = await downloadCompetitionExamPaper(id, { division: div, work_track: track })
        const meta = this.examPapersForDetail
        const byTrack = meta && meta.by_track
        const trackSlot = byTrack && byTrack[div] && byTrack[div][track]
        const slot = trackSlot || (
          div === 'undergraduate'
            ? (meta && meta.undergraduate)
            : (div === 'vocational' ? (meta && meta.vocational) : (meta && meta.default))
        )
        const filename = (slot && slot.filename) || `exam_paper_${id}_${div}_${track}.bin`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
        this.$message.success(
          `下载已开始（${this.examPaperDivisionLabel(div)} · ${
            track === 'works' ? '作品赛道' : (track === 'software' ? '软件赛道' : '硬件赛道')
          }）`
        )
      } catch (e) {
        this.$message.error('下载试卷失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.examPaperDownloadLoading = false
      }
    },

    async copyCompetitionDetailUrl (url) {
      const text = String(url || '').trim()
      if (!text) return
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text)
        } else {
          const ta = document.createElement('textarea')
          ta.value = text
          ta.style.position = 'fixed'
          ta.style.opacity = '0'
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
        }
        this.$message.success('已复制到剪贴板')
      } catch (e) {
        this.$message.error('复制失败，请手动选择链接复制')
      }
    },

    confirmDivisionPick (division) {
      const div = this.normalizeViewDivision(division)
      if (!div) return
      const comp = this.divisionPickTarget || this.activeCompetition
      const id = comp && comp.id != null ? comp.id : this.activeCompetitionId
      if (!id) return
      this.showDivisionPickModal = false
      this.divisionPickTarget = null
      if (this.standaloneDetailMode) {
        this.activeViewDivision = div
        try {
          this.$router.replace({
            name: 'ManuCompetitionDetail',
            query: {
              id: String(id),
              division: div,
              fromList: this.$route.query.fromList != null ? String(this.$route.query.fromList) : '1'
            }
          }).catch(() => {})
        } catch (e) { /* noop */ }
        void this.fetchStudentBriefingQr()
        void this.refreshActiveCompetitionMyEnrollKind()
        return
      }
      this.navigateCompetitionDetailInNewTab(id, div)
    },

    onDivisionPickModalCancel () {
      this.showDivisionPickModal = false
      if (!this.standaloneDetailMode) {
        this.divisionPickTarget = null
      }
    },

    onAltIdentityChanged () {
      this.syncEnrollProfileDefaults()
      this.$forceUpdate()
      if (this.standaloneDetailMode && this.initialCompetitionId != null && String(this.initialCompetitionId).trim() !== '') {
        const hasAuth = !!getStoredAltToken() && !this.shareGuestMode
        // 仅首次或登录态从无到有时全量 bootstrap；避免 /me 回写反复触发请求风暴
        if (!this._standaloneDetailBootstrapped || (hasAuth && !this._standaloneBootstrappedWithAuth)) {
          void this.bootstrapStandaloneDetail()
        }
        return
      }
      if (this.showStandaloneCompetitionBriefingLayout && this.activeCompetitionId) {
        void this.fetchStudentBriefingQr()
      }
    },
    async refreshAltExpertProfile () {
      if (!getStoredAltToken() || !isAltCompetitionExpert()) return
      try {
        const me = await fetchAltIdentityMe()
        // silent：同步资料但不广播，防止 onAltIdentityChanged → bootstrap → /me 死循环
        applyAltIdentityMeToStorage(me, { silent: true })
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
      if (this._bootstrapStandaloneInFlight) return this._bootstrapStandaloneInFlight
      this._bootstrapStandaloneInFlight = (async () => {
        try {
          this.manualCompetitionId = null
          this.applyActiveViewDivisionFromRoute()
          await this.refreshAltExpertProfile()
          const hasAlt = !!getStoredAltToken() && !this.shareGuestMode
          if (hasAlt) {
            await this.fetchCompetitions()
          } else {
            this.competitions = []
            this.competitionsError = ''
          }
          const raw = this.initialCompetitionId
          if (raw != null && String(raw).trim() !== '') {
            this.selectCompetition(raw)
            await this.ensureCompetitionDetail(raw)
          }
          if (hasAlt) {
            void this.refreshExamPapersForDetail()
          } else {
            this.examPapersForDetail = null
            this.$emit('exam-papers-changed')
          }
          this.$nextTick(() => {
            this.syncDualDivisionContextAfterCompetitionSelect()
            if (this.showStandaloneCompetitionBriefingLayout && this.activeCompetitionId) {
              void this.fetchStudentBriefingQr()
            }
            // 登录后竞赛 ID 可能未变，不会触发 activeCompetitionId watcher，需主动拉指导老师队伍列表
            if (hasAlt && this.showAdvisorTeamPanel && this.activeCompetitionId) {
              void this.refreshAdvisorTeams()
            } else if (!this.showAdvisorTeamPanel) {
              this.advisorTeams = []
              this.advisorSelectedTeamId = null
            }
          })
          this._standaloneDetailBootstrapped = true
          this._standaloneBootstrappedWithAuth = hasAlt
        } finally {
          this._bootstrapStandaloneInFlight = null
        }
      })()
      return this._bootstrapStandaloneInFlight
    },

    /** 竞赛详情独立页顶部「报名」：打开报名弹窗（供父组件 ref 调用） */
    async openStandaloneEnrollModal () {
      if (!this.standaloneDetailMode) return
      if (!this.isStudent) {
        this.$message.warning('仅学生身份可使用报名功能')
        return
      }
      if (this.isActiveCompetitionDualDivision && !this.activeViewDivision) {
        this.$message.warning('请先选择本科组或高职组后再报名')
        this.syncDualDivisionContextAfterCompetitionSelect()
        return
      }
      try {
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshPendingTeamInvites()
        this.applyStoredWithdrawSubmissionCutoff()
        await this.refreshMySubmissions()
        if (this.activeCompetitionMyEnrollKind) this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshQuestionAnswersBoard()
      } catch (_) {
        /* 仍打开弹窗，由禁用态与提示兜底 */
      }
      this.notifyEnrollBlockChanged()
      if (this.isActiveCompetitionFinal && !this.hasAnyEnrollment) {
        this.$message.warning('决赛仅限晋级队伍，您未在晋级名单中')
      }
      this.showStandaloneEnrollModal = true
    },
    /** 竞赛详情独立页顶部「提交作品」 */
    openStandaloneMyWorksModal () {
      if (!this.standaloneDetailMode) return
      if (!this.isStudent) {
        this.$message.warning('仅学生身份可提交作品')
        return
      }
      const tasks = [
        this.refreshActiveCompetitionMyEnrollKind(),
        this.refreshMySubmissions()
      ]
      void Promise.all(tasks).finally(() => {
        const opts = this.submitWorksTrackOptions
        if (opts.length) {
          const prefer = this.activeEnrollmentWorkTrack
          const hit = opts.find(o => o.work_track === prefer) || opts[0]
          if (hit && hit.work_track) {
            this.preferredEnrollmentWorkTrack = hit.work_track
            this.applyEnrollmentContextFromRows()
          }
        }
        void this.syncEnrollModalTeamContextForCurrentTrack().finally(() => {
          this.showStandaloneMyWorksModal = true
        })
      })
    },

    onSubmitWorksTrackChange (track) {
      const t = track != null ? String(track).trim().toLowerCase() : ''
      if (t !== 'works' && t !== 'software' && t !== 'hardware') return
      this.resetSubmissionFormFields()
      this.selectPreferredEnrollmentWorkTrack(t)
    },

    /** 参赛对象：拆出导语 + 赛道分项（保留首段总述） */
    parseBriefingTracks (text) {
      const raw = String(text || '').trim()
      if (!raw) return { intro: '', tracks: [] }

      // 1、作品赛道： / 作品赛道： / 【软件赛】 / 软件赛：
      const re = /(?:^|\n)\s*(?:[0-9一二三四五六七八九十]+[、.．)]\s*)?((?:作品|软件|硬件)赛道|(?:作品|软件|硬件|创新|创意)?赛|【[^】]{1,16}】)\s*[:：]\s*/g
      const hits = []
      let m
      while ((m = re.exec(raw)) !== null) {
        hits.push({
          index: m.index + (m[0].match(/^\n/) ? 1 : 0),
          name: String(m[1]).replace(/^【|】$/g, '').trim(),
          end: m.index + m[0].length
        })
      }

      if (hits.length < 2) {
        const lines = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean)
        const named = []
        const introLines = []
        let cur = null
        lines.forEach((line) => {
          const hm = line.match(/^(?:[0-9一二三四五六七八九十]+[、.．)]\s*)?((?:作品|软件|硬件)赛道|(?:作品|软件|硬件)赛)\s*[:：]?\s*(.*)$/)
          if (hm) {
            if (cur) named.push(cur)
            cur = { name: hm[1].trim(), body: (hm[2] || '').trim() }
          } else if (cur) {
            cur.body = cur.body ? `${cur.body}\n${line}` : line
          } else {
            introLines.push(line)
          }
        })
        if (cur) named.push(cur)
        const tracks = named.filter(t => t.name && t.body).slice(0, 8)
        return { intro: introLines.join('\n'), tracks }
      }

      const intro = raw.slice(0, hits[0].index).trim()
      const tracks = []
      for (let i = 0; i < hits.length; i++) {
        const start = hits[i].end
        const end = i + 1 < hits.length ? hits[i + 1].index : raw.length
        const body = raw.slice(start, end).trim()
        if (body) tracks.push({ name: hits[i].name, body })
      }
      return { intro, tracks }
    },

    /** 规则说明：拆成「短标题 + 说明」列表 */
    parseBriefingRuleItems (text) {
      const raw = String(text || '').trim()
      if (!raw) return []
      const iconByTitle = {
        报名: '📝',
        赛前准备: '📖',
        初赛: '🏅',
        初赛评审: '🏅',
        决赛: '🏆',
        提交: '📦',
        评审: '✅',
        晋级: '⬆️',
        答辩: '🎤'
      }
      const pickIcon = (title) => {
        const t = String(title || '')
        const key = Object.keys(iconByTitle).find(k => t.includes(k))
        return key ? iconByTitle[key] : '•'
      }
      const lines = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean)
      const items = []
      lines.forEach((line) => {
        const cleaned = line.replace(/^[-*•·\d]+[\.\)、]\s*/, '').trim()
        const m = cleaned.match(/^(.{1,16}?)\s*(?:→|->|：|:|——|—)\s*(.+)$/)
        if (m) {
          items.push({ icon: pickIcon(m[1]), title: m[1].trim(), desc: m[2].trim() })
          return
        }
        const m2 = cleaned.match(/^(报名|赛前准备|初赛评审|初赛|决赛|作品提交|评审|晋级|答辩)[:：]?\s*(.*)$/)
        if (m2) {
          items.push({ icon: pickIcon(m2[1]), title: m2[1], desc: (m2[2] || '').trim() })
        }
      })
      return items
    },

    /**
     * 竞赛环境：优先按「（一）作品赛 /（二）软件赛 /（三）硬件赛」分段解析表格。
     * 每段内识别 操作系统 / 大模型|硬件平台 / 编程语言。
     */
    parseBriefingEnvironmentByTracks (text) {
      const raw = String(text || '').trim()
      if (!raw) return null
      const headerRe = /(?:^|\n)\s*[（(]?\s*[一二三四五六七八九十\d]+\s*[）)]?\s*[、.．]?\s*(作品赛道?|软件赛道?|硬件赛道?)\s*[：:]?/g
      const matches = []
      let m
      while ((m = headerRe.exec(raw)) !== null) {
        matches.push({
          index: m.index,
          end: m.index + m[0].length,
          trackRaw: String(m[1] || '').trim()
        })
      }
      if (!matches.length) return null

      const normalizeTrack = (name) => {
        const s = String(name || '').replace(/赛道$/, '赛').trim()
        if (/作品/.test(s)) return '作品赛'
        if (/软件/.test(s)) return '软件赛'
        if (/硬件/.test(s)) return '硬件赛'
        return s || '—'
      }

      const pickField = (body, labels) => {
        const lines = String(body || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean)
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          for (let j = 0; j < labels.length; j++) {
            const lab = labels[j]
            const re = new RegExp('^' + lab + '\\s*[:：]\\s*(.+)$')
            const mm = line.match(re)
            if (mm) return String(mm[1] || '').trim()
          }
        }
        return ''
      }

      const rows = matches.map((h, idx) => {
        const bodyStart = h.end
        const bodyEnd = idx + 1 < matches.length ? matches[idx + 1].index : raw.length
        const body = raw.slice(bodyStart, bodyEnd).trim()
        const os = pickField(body, ['操作系统', '系统'])
        const platform = pickField(body, ['硬件平台', '大模型/平台', '大模型', '平台'])
        const lang = pickField(body, ['编程语言', '语言'])
        return [
          normalizeTrack(h.trackRaw),
          os || '—',
          platform || '—',
          lang || '—'
        ]
      })

      if (!rows.length) return null
      return {
        headers: ['赛道', '操作系统', '大模型/平台', '编程语言'],
        rows
      }
    },

    /** 竞赛环境：解析为表格（赛道分段优先；其次 | / 制表符表格） */
    parseBriefingEnvironmentTable (text) {
      const raw = String(text || '').trim()
      if (!raw) return null

      const byTracks = this.parseBriefingEnvironmentByTracks(raw)
      if (byTracks) return byTracks

      const lines = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean)
      const splitRow = (line) => {
        if (line.includes('|')) {
          return line.split('|').map(c => c.trim()).filter((c, i, arr) => !(arr.length > 2 && c === '' && (i === 0 || i === arr.length - 1)))
        }
        if (line.includes('\t')) return line.split('\t').map(c => c.trim())
        if (/\s{2,}/.test(line)) return line.split(/\s{2,}/).map(c => c.trim())
        return null
      }
      // markdown 表头分隔行跳过
      const isSep = (cells) => cells && cells.length >= 2 && cells.every(c => /^:?-{3,}:?$/.test(c.replace(/\s/g, '')))
      const rows = []
      lines.forEach((line) => {
        if (/^\|?[\s:-]+\|/.test(line) && !/[A-Za-z\u4e00-\u9fff0-9]/.test(line.replace(/[\s|:-]/g, ''))) return
        const cells = splitRow(line)
        if (!cells || cells.length < 2) return
        if (isSep(cells)) return
        rows.push(cells)
      })
      if (rows.length < 2) {
        // 回退：仅当行首不是字段名时，才按「赛道：a / b / c」解析，避免把「操作系统/大模型」当成赛道
        const fieldNames = /^(操作系统|系统|大模型\/平台|大模型|硬件平台|平台|编程语言|语言)$/
        const fallback = []
        lines.forEach((line) => {
          const m = line.match(/^(.+?)\s*[:：]\s*(.+)$/)
          if (!m) return
          const label = m[1].trim()
          if (fieldNames.test(label)) return
          const rest = m[2].split(/[\/／|]/).map(s => s.trim()).filter(Boolean)
          if (rest.length >= 2) fallback.push([label, ...rest.slice(0, 3)])
        })
        if (fallback.length < 2) return null
        const maxCols = Math.max(...fallback.map(r => r.length))
        const headers = ['赛道', '操作系统', '大模型/平台', '编程语言'].slice(0, maxCols)
        while (headers.length < maxCols) headers.push(`列${headers.length + 1}`)
        return {
          headers,
          rows: fallback.map(r => {
            const row = r.slice()
            while (row.length < headers.length) row.push('-')
            return row.slice(0, headers.length)
          })
        }
      }
      const colCount = Math.max(...rows.map(r => r.length))
      if (colCount < 2) return null
      let headers = rows[0].slice()
      while (headers.length < colCount) headers.push(`列${headers.length + 1}`)
      // 若首行不像表头，补默认表头
      const looksHeader = /赛道|系统|模型|语言|平台|环境|操作系统/.test(headers.join(''))
      let dataRows = rows.slice(1)
      if (!looksHeader) {
        headers = ['赛道', '操作系统', '大模型/平台', '编程语言'].slice(0, colCount)
        while (headers.length < colCount) headers.push(`列${headers.length + 1}`)
        dataRows = rows
      }
      return {
        headers: headers.slice(0, colCount),
        rows: dataRows.map(r => {
          const row = r.slice()
          while (row.length < colCount) row.push('-')
          return row.slice(0, colCount)
        })
      }
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
      this.studentBriefingQrRemoteUrl = ''
    },
    async fetchStudentBriefingQr () {
      if (!this.activeCompetitionId || !this.showStandaloneCompetitionBriefingLayout) return
      let comp = this.activeCompetition
      if (!comp || comp.division_mode == null) {
        comp = await this.ensureCompetitionDetail(this.activeCompetitionId) || comp
      }
      if (this.isCompetitionDualDivision(comp)) {
        const layout = String(comp.qr_layout || 'shared').toLowerCase()
        if (layout === 'separate' && !this.activeViewDivision) return
      }
      this.revokeStudentBriefingQrObjectUrl()
      const objectUrl = await this.loadCompetitionQrForCurrentView(
        this.activeCompetitionId,
        comp,
        this.activeViewDivision
      )
      if (objectUrl) this.studentBriefingQrObjectUrl = objectUrl
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
        return '当前竞赛已停止报名（已锁定或已过结束时间），无法创建队伍。请联系管理员延长结束时间或重新开放报名后再试'
      }

      if (/has not ended yet|export is available after end date |尚未结束.*导出/i.test(text)) {
        return '竞赛尚未结束，结束后才可导出答案（状态为「已结束」或已过结束时间）'
      }

      if (/individual enrollment not allowed/i.test(text)) {
        return '该竞赛不允许个人赛道，请使用队伍参赛'
      }

      if (/team enrollment not allowed/i.test(text)) {
        return '该竞赛不允许队伍赛道报名'
      }

      if (/captain must have school configured|captain account not found/i.test(text)) {
        return '建队失败：当前学生账号未填写学校。请使用已填写学校的账号，或联系管理员补全学校信息后重试'
      }

      if (/仅允许同一学校的学生组队|学校不一致|未配置学校，无法组队/i.test(text)) {
        return text.includes('未配置学校')
          ? text
          : '仅允许同一学校的学生组队，队长与队员必须属于同一学校'
      }

      if (/作品已提交，无法再添加\/修改指导老师|作品已提交，无法再变更|作品已提交，无法再添加/i.test(text)) {
        return text
      }

      if (/组别必选|division.*undergraduate|赛道必选|work_track/i.test(text) && /必选|required/i.test(text)) {
        return text.includes('赛道') || /work_track|works|software|hardware/i.test(text)
          ? '请选择赛道：作品 / 软件 / 硬件'
          : '请选择组别：本科或高职'
      }

      if (/create team failed/i.test(text)) {
        const tail = text.replace(/^Create team failed:\s*/i, '').trim()
        return tail ? `创建队伍失败：${tail}` : '创建队伍失败，请稍后重试'
      }

      if (/队名已存在|team name already exists|duplicate.*team.?name/i.test(text)) {
        return '队名已存在，请更换其他队名'
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

      if (/specify work_track=/i.test(text)) {
        return '本竞赛存在多条赛道报名，请先选择要退出的作品赛道（作品/软件/硬件）'
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
        return '当前竞赛已停止报名（已锁定或已过结束时间），无法新建队伍或邀请入队。请联系管理员延长结束时间或重新开放报名后再试'
      }

      return text || fallback
    },

    isDuplicateTeamNameError (errorOrText) {
      const text = typeof errorOrText === 'string'
        ? errorOrText
        : this.getApiErrorMessage(errorOrText, '')
      return /队名已存在|team name already exists|duplicate.*team.?name/i.test(String(text || ''))
    },

    showDuplicateTeamNameModal (errorOrText) {
      const content = this.isDuplicateTeamNameError(errorOrText)
        ? '队名已存在，请更换其他队名'
        : this.getApiErrorMessage(errorOrText, '队名已存在，请更换其他队名')
      this.$warning({
        title: '队名重复',
        content,
        okText: '知道了'
      })
    },

    /** §8.8 退赛：优先按当前作品赛道 work_track */
    resolveWithdrawTrack () {
      const wt = this.activeEnrollmentWorkTrack
      if (wt === 'works' || wt === 'software' || wt === 'hardware') {
        return { work_track: wt }
      }
      const hasIndividual = this.myEnrolledIndividual
      const hasTeam = this.myEnrolledTeam
      if (hasIndividual && hasTeam) {
        return { track: this.enrollMode === 'team' ? 'team' : 'individual' }
      }
      if (hasIndividual) return { track: 'individual' }
      if (hasTeam) return { track: 'team' }
      return null
    },

    withdrawTrackLabel (opts) {
      if (!opts) return ''
      const wt = opts.work_track
      if (wt === 'works') return '作品'
      if (wt === 'software') return '软件'
      if (wt === 'hardware') return '硬件'
      return opts.track === 'team' ? '组队' : '个人'
    },

    workTrackDisplayLabel (track) {
      if (track === 'works') return '作品'
      if (track === 'software') return '软件'
      if (track === 'hardware') return '硬件'
      return track || ''
    },

    isWorkTrackAlreadyEnrolled (track) {
      const t = track != null ? String(track).trim().toLowerCase() : ''
      return this.myEnrolledWorkTracks.includes(t)
    },

    selectPreferredEnrollmentWorkTrack (track) {
      const t = track != null ? String(track).trim().toLowerCase() : ''
      if (t !== 'works' && t !== 'software' && t !== 'hardware') return
      const prevTeamId = this.myTeamId
      this.preferredEnrollmentWorkTrack = t
      this.applyEnrollmentContextFromRows()
      // 队伍 ID 变化时由 myTeamId watcher 刷新；未变化时也要按新赛道上下文刷新
      if (Number(this.myTeamId) === Number(prevTeamId)) {
        void this.syncEnrollModalTeamContextForCurrentTrack()
      }
    },

    /** 按当前选中赛道刷新队伍详情、入队申请、队员、分题状态 */
    async syncEnrollModalTeamContextForCurrentTrack () {
      if (this.enrollMode !== 'team' || !this.myTeamId) {
        this.teamJoinRequests = []
        this.myTeamMembers = []
        this.questionAnswerSlots = []
        this.transferTeamId = null
        this.leaveTeamId = null
        return
      }
      const tid = Number(this.myTeamId)
      if (!Number.isFinite(tid) || tid <= 0) return
      this.transferTeamId = tid
      this.leaveTeamId = tid
      this.studentTeamInviteRef = ''
      this.studentTeamRemoveRef = ''
      this.newCaptainRef = ''
      await this.refreshMyTeamStatus()
      if (this.showCaptainTeamJoinRequestsInEnrollModal) {
        await this.refreshTeamJoinRequests()
      } else {
        this.teamJoinRequests = []
      }
      if (this.showCaptainTeamMembersInEnrollModal) {
        await this.refreshMyTeamMembers()
      }
      const track = this.activeEnrollmentWorkTrack
      if (track === 'software' || track === 'hardware') {
        void this.refreshActiveSubmissionQuestionConfig()
        await this.refreshQuestionAnswersBoard()
      } else {
        this.questionAnswerSlots = []
      }
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
        this.emitCatalogLogoChanged()
      }
    },

    competitionHasLogo (comp) {
      return !!(comp && (comp.logo_path || comp.logo_image_url))
    },

    /** 侧栏 Logo：优先当前选中竞赛；否则取列表中第一个已上传 Logo 的竞赛 */
    resolveCatalogLogoCompetitionId () {
      if (this.standaloneDetailMode) return null
      const active = this.activeCompetition
      if (this.competitionHasLogo(active)) return active.id
      const list = this.competitions || []
      const hit = list.find(c => this.competitionHasLogo(c))
      return hit ? hit.id : null
    },

    emitCatalogLogoChanged () {
      if (this.standaloneDetailMode) return
      this.$emit('catalog-logo-changed', this.resolveCatalogLogoCompetitionId())
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

    /** 头图简介关键词高亮分段 */
    highlightHeroSloganSegments (text) {
      const raw = text != null ? String(text) : ''
      if (!raw) return []
      const keywords = [
        '生成式大语言模型',
        '多模态大模型',
        '大模型应用系统开发',
        '知识库 RAG',
        '知识库RAG',
        'AI 智能体 Agent',
        'AI智能体 Agent',
        'AI 智能体',
        'AI智能体',
        '提示工程',
        'RAG',
        'Agent'
      ]
      const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      const re = new RegExp(`(${escaped.join('|')})`, 'g')
      const parts = raw.split(re)
      const kwSet = new Set(keywords)
      return parts.filter(p => p !== '').map(p => ({ t: p, hl: kwSet.has(p) }))
    },

    /** 从竞赛独立账号资料预填选填项（不覆盖用户已填写内容）；ID 固定为当前用户账号 ID */
    syncEnrollProfileDefaults () {
      if (!this.isStudent) return
      const p = getAltProfileFromStorage() || {}
      const accountId = this.studentAccountIdLabel ||
        (this.altCurrentUserId != null ? String(this.altCurrentUserId) : '') ||
        (p.user_id != null ? String(p.user_id) : (p.id != null ? String(p.id) : ''))
      if (accountId) {
        this.$set(this.enrollProfileForm, 'student_no', accountId)
      }
      const map = {
        real_name: p.full_name,
        college: p.college != null ? p.college : p.school,
        contact: p.email != null ? p.email : (p.contact != null ? p.contact : p.phone)
      }
      const f = this.enrollProfileForm || {}
      for (const [key, val] of Object.entries(map)) {
        if (val == null || String(val).trim() === '') continue
        const cur = f[key] != null ? String(f[key]).trim() : ''
        if (!cur) this.$set(this.enrollProfileForm, key, String(val).trim())
      }
    },

    validateEnrollTrackAndDivision () {
      const f = this.enrollProfileForm || {}
      const track = f.work_track != null ? String(f.work_track).trim() : ''
      const division = f.division != null ? String(f.division).trim() : ''
      if (track !== 'works' && track !== 'software' && track !== 'hardware') {
        this.$message.warning('请选择赛道：作品、软件或硬件')
        return false
      }
      if (division !== 'undergraduate' && division !== 'vocational') {
        this.$message.warning('请选择组别：本科或高职')
        return false
      }
      return true
    },

    buildEnrollExtraFields () {
      const f = this.enrollProfileForm || {}
      const out = {}
      const keys = ['student_no', 'real_name', 'college', 'contact']
      for (const k of keys) {
        const s = f[k] != null ? String(f[k]).trim() : ''
        if (s) out[k] = s
      }
      const division = this.enrollDivisionForApi
      if (division) out.division = division
      const track = f.work_track != null ? String(f.work_track).trim() : ''
      if (track === 'works' || track === 'software' || track === 'hardware') {
        out.work_track = track
      }
      return out
    },

    /** enrollments/me 未带 division 时，用 POST enroll 响应或详情页上下文写入本机缓存 */
    persistEnrollmentDivisionAfterSuccess (track, enrollResponse) {
      const cid = this.activeCompetitionId
      if (!cid) return
      const fromRes = resolveEnrollmentDivision(enrollResponse || {})
      const division = fromRes || this.enrollDivisionForApi
      if (division) {
        saveCompetitionEnrollmentDivision(cid, track, division)
        if (this.isActiveCompetitionDualDivision) {
          this.activeCompetitionEnrolledDivision = division
          this.notifyEnrollBlockChanged()
        }
      }
    },

    notifyEnrollBlockChanged () {
      this.$emit('enroll-block-changed', {
        blocked: this.enrollBlockedByOtherDivision,
        hasAnyEnrollment: this.hasAnyEnrollment,
        myEnrolledTeam: this.myEnrolledTeam,
        myEnrolledIndividual: this.myEnrolledIndividual,
        stage: this.activeCompetitionStage,
        isFinal: this.isActiveCompetitionFinal,
        finalAccessDenied: this.finalStageAccessDenied
      })
    },

    syncActiveCompetitionEnrolledDivision (enrolledRows) {
      if (!this.isActiveCompetitionDualDivision) {
        this.activeCompetitionEnrolledDivision = null
        return
      }
      const cid = this.activeCompetitionId
      let division = null
      for (const row of enrolledRows || []) {
        let d = resolveEnrollmentDivision(row)
        if (!d && cid) {
          const track = getEnrollmentScopeUtil(row) === 'team' ? 'team' : 'individual'
          d = getCompetitionEnrollmentDivision(cid, track)
        }
        if (d === 'undergraduate' || d === 'vocational') {
          division = d
          break
        }
      }
      this.activeCompetitionEnrolledDivision = division
    },

    assertNotEnrolledInOtherDivision (showToast = true) {
      if (!this.enrollBlockedByOtherDivision) return true
      if (showToast) this.$message.warning(this.enrollBlockedByOtherDivisionDescription)
      return false
    },

    assertEnrollDivisionContext (showToast = true) {
      if (!this.isActiveCompetitionDualDivision) return true
      if (this.activeViewDivision) return true
      if (showToast) {
        this.$message.warning('该竞赛分本科组与高职组，请从对应组别详情页进入后再报名')
        if (this.standaloneDetailMode) this.syncDualDivisionContextAfterCompetitionSelect()
      }
      return false
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

    async handleWithdrawCompetition (trackOrOpts) {
      if (!this.activeCompetitionId) return
      let opts = null
      if (trackOrOpts && typeof trackOrOpts === 'object') {
        opts = trackOrOpts
      } else if (trackOrOpts === 'individual' || trackOrOpts === 'team') {
        opts = { track: trackOrOpts }
      } else if (trackOrOpts === 'works' || trackOrOpts === 'software' || trackOrOpts === 'hardware') {
        opts = { work_track: trackOrOpts }
      } else {
        opts = this.resolveWithdrawTrack()
      }
      if (!opts) {
        this.$message.warning('当前没有可退出的有效报名')
        return
      }
      const trackLabel = this.withdrawTrackLabel(opts)
      const multi = this.myEnrolledWorkTracks.length > 1 || (this.myEnrolledIndividual && this.myEnrolledTeam)
      try {
        await this.$confirm({
          title: `确认退出${trackLabel}赛道`,
          content: multi
            ? `将取消本竞赛的${trackLabel}赛道报名；其它赛道不受影响。退赛后若再次报名，需重新提交该赛道作品。是否继续？`
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
        await withdrawCompetition(this.activeCompetitionId, opts)
        this.$message.success(`${trackLabel}赛道退赛成功`)
        const withdrawTs = Date.now()
        this.ignoreSubmissionsBeforeReenrollAt = withdrawTs
        markCompetitionWithdrawnForResubmit(this.activeCompetitionId, withdrawTs)
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
      const teams = Array.isArray(this.activeCompetitionEnrollmentRows.teams)
        ? this.activeCompetitionEnrollmentRows.teams
        : []
      const prefer = this.preferredEnrollmentWorkTrack
        ? String(this.preferredEnrollmentWorkTrack).trim().toLowerCase()
        : ''
      let teamRow = null
      if (prefer) {
        teamRow = teams.find(r => {
          const t = r && r.work_track != null ? String(r.work_track).trim().toLowerCase() : ''
          return t === prefer
        }) || null
      }
      if (!teamRow) teamRow = teams[0] || this.activeCompetitionEnrollmentRows.team || null
      this.activeCompetitionEnrollmentRows = {
        ...this.activeCompetitionEnrollmentRows,
        team: teamRow,
        teams
      }
      this.myEnrolledIndividual = !!individualRow
      this.myEnrolledTeam = teams.length > 0 || !!teamRow
      if (teamRow && teamRow.work_track) {
        const tw = String(teamRow.work_track).trim().toLowerCase()
        if (tw === 'works' || tw === 'software' || tw === 'hardware') {
          this.preferredEnrollmentWorkTrack = tw
        }
      }

      const nextTeamId = teamRow && teamRow.team_id != null ? teamRow.team_id : null
      if (
        this.myTeamId != null &&
        nextTeamId != null &&
        Number(this.myTeamId) !== Number(nextTeamId)
      ) {
        this.myTeamStatus = null
        this.myTeamName = null
        this.myTeamAdvisorName = null
        this.myTeamWorkTrack = null
        this.myTeamMembers = []
        this.teamJoinRequests = []
        this.questionAnswerSlots = []
      }

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
          this.myTeamId = null
          this.submissionTeamId = null
        }
        return
      }

      // 仅组队参赛：优先使用队伍报名上下文
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
      if (!this.activeCompetitionId || !this.isStudent || !getStoredAltToken()) {
        this.activeCompetitionMyEnrollKind = null
        this.activeCompetitionEnrollmentId = null
        this.myEnrolledIndividual = false
        this.myEnrolledTeam = false
        this.preferredEnrollmentWorkTrack = null
        this.activeCompetitionEnrollmentRows = { individual: null, team: null, teams: [] }
        this.activeCompetitionEnrolledDivision = null
        this.notifyEnrollBlockChanged()
        return
      }
      try {
        const res = await getMyCompetitionEnrollments()
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : (res && Array.isArray(res.data) ? res.data : []))
        const cid = Number(this.activeCompetitionId)
        const allEnrolledRows = list.filter(
          r => Number(r.competition_id) === cid && r.status === 'enrolled'
        )
        this.syncActiveCompetitionEnrolledDivision(allEnrolledRows)
        const enrolledRows = allEnrolledRows.filter(r => this.enrollmentMatchesActiveViewDivision(r))
        const { individual: individualRow, team: teamRow, teams } = splitEnrollmentsByTrack(enrolledRows)
        this.activeCompetitionEnrollmentRows = {
          individual: individualRow,
          team: teamRow,
          teams: Array.isArray(teams) ? teams : (teamRow ? [teamRow] : [])
        }
        this.applyEnrollmentContextFromRows()
        if (this.myTeamId) {
          await this.refreshMyTeamStatus()
        } else {
          this.myTeamStatus = null
          this.myTeamWorkTrack = null
        }
        // 须在 myEnrolled* 更新后再通知父页，否则「提交作品」会按旧状态隐藏
        this.notifyEnrollBlockChanged()
      } catch {
        this.activeCompetitionMyEnrollKind = null
        this.activeCompetitionEnrollmentId = null
        this.myEnrolledIndividual = false
        this.myEnrolledTeam = false
        this.activeCompetitionEnrollmentRows = { individual: null, team: null, teams: [] }
        this.activeCompetitionEnrolledDivision = null
        this.myTeamStatus = null
        this.myTeamWorkTrack = null
        this.notifyEnrollBlockChanged()
      }
    },

    async handleEnrollIndividual () {
      if (!this.activeCompetitionId) return
      if (!this.validateEnrollTrackAndDivision()) return
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertNotEnrolledInOtherDivision()) return
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
        const enrollRes = await enrollCompetition({
          competition_id: this.activeCompetitionId,
          team_id: null,
          ...this.buildEnrollExtraFields()
        })
        this.persistEnrollmentDivisionAfterSuccess('individual', enrollRes)
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

    mapEnrollDetailToUserMessage (detailText) {
      const t = (detailText || '').toLowerCase()
      if (t.includes('division is required')) {
        return '该竞赛分本科组与高职组，请从对应组别详情页进入后再报名'
      }
      if (t.includes('already enrolled in division')) {
        return '您已在另一学历组别报名，不可跨组报名；请返回列表选择已报名的组别查看详情'
      }
      if (t.includes('division must match team')) {
        return '队伍所属组别与当前详情页组别不一致，请切换到对应组别详情页后再报名'
      }
      return null
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
      const mapped = this.mapEnrollDetailToUserMessage(this.getEnrollDetailRaw(error))
      if (mapped) {
        this.$message.warning(mapped)
        return true
      }
      this.$message.error('报名失败：' + this.getApiErrorMessage(error, '未知错误'))
      return false
    },

    async handleEnrollWithTeam () {
      if (!this.activeCompetitionId) return
      if (this.isActiveCompetitionFinal) {
        this.$message.info('决赛沿用初赛晋级队伍，无需重新报名')
        return
      }
      if (!this.validateEnrollTrackAndDivision()) return
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertNotEnrolledInOtherDivision()) return
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
        const enrollRes = await enrollCompetition({
          competition_id: this.activeCompetitionId,
          team_id: this.myTeamId,
          ...this.buildEnrollExtraFields()
        })
        this.persistEnrollmentDivisionAfterSuccess('team', enrollRes)
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

    assertCanCreateStudentTeam () {
      if (!this.activeCompetitionId) return false
      if (!this.assertEnrollDivisionContext()) return false
      if (!this.assertNotEnrolledInOtherDivision()) return false
      if (!this.canEnrollAnotherWorkTrack) {
        this.$message.info('同一竞赛最多报名作品/软件/硬件三个赛道，已全部报满')
        return false
      }
      if (!this.assertCompetitionPublishedForEnroll()) return false
      if (this.competitionEnrollmentClosed) {
        this.$message.warning(
          '当前竞赛已停止报名（已锁定或已过结束时间），无法创建队伍。请联系管理员延长结束时间或重新开放报名后再试'
        )
        return false
      }
      if (!this.allowTeam) {
        this.$message.error('该竞赛不允许团队参赛')
        return false
      }
      return true
    },

    openStudentCreateTeamModal () {
      if (!this.assertCanCreateStudentTeam()) return
      if (this.isActiveCompetitionFinal) {
        this.$message.warning('决赛不可自行创建队伍，请等待管理员从初赛晋级')
        return
      }
      const enrolled = this.myEnrolledWorkTracks
      const defaultTrack = ['works', 'software', 'hardware'].find(t => !enrolled.includes(t)) || 'works'
      const lockedDiv = this.activeCompetitionEnrolledDivision
      this.studentCreateTeamForm = {
        name: '',
        advisor_name: '',
        work_track: defaultTrack,
        division: lockedDiv || (this.enrollProfileForm && this.enrollProfileForm.division) || 'undergraduate'
      }
      this.showStudentCreateTeamModal = true
    },

    closeStudentCreateTeamModal () {
      this.showStudentCreateTeamModal = false
      this.studentCreateTeamModalLoading = false
      this.studentCreateTeamForm = {
        name: '',
        advisor_name: '',
        work_track: 'works',
        division: 'undergraduate'
      }
    },

    async submitStudentCreateTeamModal () {
      const name = (this.studentCreateTeamForm.name || '').trim()
      const advisorName = (this.studentCreateTeamForm.advisor_name || '').trim()
      if (!name) {
        this.$message.warning('请填写队名')
        return Promise.reject(new Error('empty team name'))
      }
      this.studentCreateTeamModalLoading = true
      try {
        await this.createStudentTeamWithName(name, advisorName)
        this.closeStudentCreateTeamModal()
      } catch (e) {
        if (e && (e.message === 'empty team name' || e.message === 'missing division' || e.message === 'missing work_track')) {
          return Promise.reject(e)
        }
        if (this.isDuplicateTeamNameError(e)) {
          this.showDuplicateTeamNameModal(e)
        } else {
          this.$message.error('创建队伍失败：' + this.getApiErrorMessage(e, '未知错误'))
        }
        return Promise.reject(e)
      } finally {
        this.studentCreateTeamModalLoading = false
      }
    },

    async createStudentTeamWithName (teamName, advisorName) {
      const name = (teamName || '').trim()
      const division = (this.studentCreateTeamForm.division || this.enrollDivisionForApi || '').trim()
      const workTrack = (this.studentCreateTeamForm.work_track || '').trim()
      if (division !== 'undergraduate' && division !== 'vocational') {
        this.$message.warning('请选择组别：本科或高职')
        throw new Error('missing division')
      }
      if (workTrack !== 'works' && workTrack !== 'software' && workTrack !== 'hardware') {
        this.$message.warning('请选择赛道：作品、软件或硬件')
        throw new Error('missing work_track')
      }
      if (this.isWorkTrackAlreadyEnrolled(workTrack)) {
        this.$message.warning(`您已报名${this.workTrackDisplayLabel(workTrack)}赛道，不可重复报名同一赛道`)
        throw new Error('missing work_track')
      }
      const teamPayload = {
        competition_id: this.activeCompetitionId,
        initial_member_ids: null,
        division,
        work_track: workTrack
      }
      if (name) teamPayload.name = name
      const advisor = (advisorName != null ? String(advisorName) : (this.studentCreateTeamForm.advisor_name || '')).trim()
      if (advisor) {
        if (isEightDigitId(advisor)) {
          teamPayload.advisor_id = Number(advisor)
        } else {
          teamPayload.advisor_name = advisor
        }
      }
      const team = await createCompetitionTeam(teamPayload)
      const teamId = team && (team.id || team.team_id)
      if (!teamId) throw new Error('创建队伍返回缺少 id')
      // 同步报名资料中的赛道/组别，便于随后队伍报名
      this.enrollProfileForm.division = division
      this.enrollProfileForm.work_track = workTrack
      this.preferredEnrollmentWorkTrack = workTrack
      const teamDiv = resolveTeamDivision(team) || division
      if (teamDiv) saveCompetitionTeamDivision(this.activeCompetitionId, teamId, teamDiv)
      this.myTeamId = teamId
      this.submissionTeamId = teamId
      this.applyMyTeamInfoFromTeam(team, name)
      this.studentCreatedTeamInCurrentCompetition = true
      this.teamEnrollmentEligible = true
      await this.refreshMySubmissions()
      await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      await this.refreshMyTeamStatus()
      await this.refreshActiveCompetitionMyEnrollKind()
      if (this.myEnrolledTeam) {
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        this.$message.success('队伍创建成功并已报名。当前为「待校审」，须本校校管理员审核通过后，队员方可上传题目答案。')
      } else {
        this.$message.success('队伍创建成功，当前为「待校审」。校审通过后队员方可上传题目答案。')
      }
    },

    async handleCreateTeamOnly () {
      if (!this.assertCanCreateStudentTeam()) return
      this.enrollLoading = true
      try {
        await this.createStudentTeamWithName('')
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

    async resolveJoinTeamTargetId () {
      const rawId = this.joinTeamId
      if (rawId != null && rawId !== '') {
        const tid = Number(rawId)
        if (!isEightDigitId(tid)) {
          this.$message.warning(`队伍ID${EIGHT_DIGIT_ID_HINT}`)
          return null
        }
        return tid
      }
      const name = (this.joinTeamName || '').trim()
      if (!name) return null
      if (!this.activeCompetitionId) return null
      try {
        const team = await lookupCompetitionTeamByName(this.activeCompetitionId, name)
        const tid = team && (team.id != null ? team.id : team.team_id)
        const n = Number(tid)
        return Number.isFinite(n) && n > 0 ? n : null
      } catch (e) {
        const msg = this.getApiErrorMessage(e, '未找到该队名的队伍')
        this.$message.warning(msg)
        return null
      }
    },

    async validateJoinTeamBelongsToActiveCompetition (teamId) {
      const targetId = teamId != null ? Number(teamId) : Number(this.joinTeamId)
      if (!this.activeCompetitionId || !Number.isFinite(targetId) || targetId <= 0) return true
      // 申请入队者尚非队员：getCompetitionTeam 会 403，全局拦截器会误弹「权限不足」，
      // 且 catch 后仍放行，校验无实际作用。竞赛归属由入队接口校验。
      return true
    },

    async handleJoinTeam () {
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertNotEnrolledInOtherDivision()) return
      if (!this.canEnrollAnotherWorkTrack) {
        this.$message.info('同一竞赛最多报名作品/软件/硬件三个赛道，已全部报满')
        return
      }
      if (!this.assertCompetitionPublishedForEnroll()) return
      if (!this.activeCompetitionId) {
        this.$message.warning('请先选择竞赛')
        return
      }
      const targetTeamId = await this.resolveJoinTeamTargetId()
      if (!targetTeamId) {
        this.$message.warning('请输入要加入的队伍ID或队名')
        return
      }
      const teamBelongsCurrentCompetition = await this.validateJoinTeamBelongsToActiveCompetition(targetTeamId)
      if (!teamBelongsCurrentCompetition) return
      this.teamLoading = true
      try {
        await addTeamMember(targetTeamId)
        this.$message.success('入队申请已提交，请等待队长审核；审核通过后将自动加入队伍并完成组队赛道报名。')
      } catch (e) {
        this.$message.error('申请加入失败：' + this.getJoinTeamErrorMessage(e))
      } finally {
        this.teamLoading = false
      }
    },

    formatTeamJoinRequestStudentName (req) {
      if (!req || typeof req !== 'object') return '未知队员'
      const name = String(req.full_name || req.username || '').trim()
      if (name) return name
      return req.user_id != null ? `用户 #${req.user_id}` : '未知队员'
    },

    formatTeamMemberDisplayName (member) {
      if (!member || typeof member !== 'object') return '未知'
      const name = String(member.full_name || member.username || '').trim()
      if (name) return name
      return member.user_id != null ? `用户 #${member.user_id}` : '未知'
    },

    async refreshMyTeamMembers () {
      if (!this.showCaptainTeamMembersInEnrollModal) {
        this.myTeamMembers = []
        return
      }
      const teamId = Number(this.myTeamId)
      if (!Number.isFinite(teamId) || teamId <= 0) {
        this.myTeamMembers = []
        return
      }
      this.myTeamMembersLoading = true
      try {
        const res = await getCompetitionTeam(teamId)
        this.myTeamMembers = Array.isArray(res && res.members) ? res.members : []
        this.applyMyTeamInfoFromTeam(res)
      } catch (e) {
        this.myTeamMembers = []
        this.$message.error('获取队员列表失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.myTeamMembersLoading = false
      }
    },

    async handleCaptainRemoveTeamMember (member) {
      if (!member || member.is_captain) return
      if (!this.isCurrentTeamCaptain) {
        this.$message.warning('仅队长可移除队员')
        return
      }
      if (this.competitionTeamRemoveMemberBlocked) {
        this.$message.warning(this.competitionTeamRemoveMemberBlockedMessage || '当前不可移除队员')
        return
      }
      if (!this.myTeamId || member.user_id == null) return
      const userId = Number(member.user_id)
      if (!Number.isFinite(userId) || userId <= 0) return
      this.captainRemovingUserId = userId
      try {
        await removeCompetitionTeamMember(this.myTeamId, userId)
        this.$message.success(`已移除队员「${this.formatTeamMemberDisplayName(member)}」`)
        await this.refreshMyTeamMembers()
        await this.refreshActiveCompetitionMyEnrollKind()
      } catch (e) {
        this.$message.error('移除失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.captainRemovingUserId = null
      }
    },

    async refreshTeamJoinRequests () {
      if (!this.showCaptainTeamJoinRequestsInEnrollModal) {
        this.teamJoinRequests = []
        return
      }
      const teamId = Number(this.myTeamId)
      if (!Number.isFinite(teamId) || teamId <= 0) {
        this.teamJoinRequests = []
        return
      }
      this.teamJoinRequestsLoading = true
      try {
        const res = await listTeamJoinRequests(teamId, { status: 'pending' })
        this.teamJoinRequests = normalizeCompetitionApiList(res)
      } catch (e) {
        this.teamJoinRequests = []
        this.$message.error('获取入队申请失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamJoinRequestsLoading = false
      }
    },

    async handleReviewTeamJoinRequest (req, action) {
      if (!req || req.id == null || !this.myTeamId) return
      const teamId = Number(this.myTeamId)
      const requestId = Number(req.id)
      if (!Number.isFinite(teamId) || !Number.isFinite(requestId)) return
      this.teamJoinRequestReviewingId = requestId
      try {
        await reviewTeamJoinRequest(teamId, requestId, action)
        const studentName = this.formatTeamJoinRequestStudentName(req)
        if (action === 'approve') {
          this.$message.success(`已同意「${studentName}」加入队伍`)
        } else {
          this.$message.success(`已拒绝「${studentName}」的入队申请`)
        }
        await this.refreshTeamJoinRequests()
        await this.refreshMyTeamMembers()
      } catch (e) {
        const verb = action === 'approve' ? '同意' : '拒绝'
        this.$message.error(`${verb}入队申请失败：` + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamJoinRequestReviewingId = null
      }
    },

    async handleTransferCaptain () {
      if (!this.transferTeamId) return
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
      const captainRef = String(this.newCaptainRef || '').trim()
      if (!captainRef) {
        this.$message.warning('请填写新队长姓名或用户 ID')
        return
      }
      const payload = {
        team_id: this.transferTeamId
      }
      if (isEightDigitId(captainRef)) {
        payload.new_captain_id = Number(captainRef)
      } else {
        payload.new_captain = captainRef
      }
      this.teamLoading = true
      try {
        await transferTeamCaptain(this.transferTeamId, payload)
        this.$message.success('队长转让成功')
        this.newCaptainRef = ''
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMyScores(false)
        await this.refreshMyTeamMembers()
      } catch (e) {
        this.$message.error('转让失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    async handleLeaveTeam () {
      if (!this.leaveTeamId) return
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
      this.teamLoading = true
      try {
        await leaveTeam(this.leaveTeamId)
        this.$message.success('退队成功')
        if (this.myTeamId === this.leaveTeamId) {
          this.myTeamId = null
          this.myTeamName = null
          this.myTeamAdvisorName = null
          this.myTeamStatus = null
          this.myTeamWorkTrack = null
        }
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMySubmissions()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        this.$message.error('退队失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    async handleMemberLeaveTeam () {
      if (!this.myTeamId) return
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
      // ant-design-vue 1.x 的 $confirm 不返回 Promise，必须用 onOk/onCancel 等待用户确认
      const confirmed = await new Promise((resolve) => {
        this.$confirm({
          title: '确认退队',
          content: '退出后将取消本队组队报名，需重新接受邀请或申请入队。是否继续？',
          okText: '退队',
          cancelText: '取消',
          okType: 'danger',
          onOk: () => resolve(true),
          onCancel: () => resolve(false)
        })
      })
      if (!confirmed) return
      this.leaveTeamId = this.myTeamId
      await this.handleLeaveTeam()
    },

    async refreshPendingTeamInvites () {
      if (!this.isStudent || !getStoredAltToken()) {
        this.pendingTeamInvites = []
        return
      }
      this.pendingTeamInvitesLoading = true
      try {
        const res = await listMyTeamInvites({ status: 'pending' })
        this.pendingTeamInvites = Array.isArray(res)
          ? res
          : (res && Array.isArray(res.items) ? res.items : [])
      } catch (_) {
        this.pendingTeamInvites = []
      } finally {
        this.pendingTeamInvitesLoading = false
      }
    },

    async handleRespondTeamInvite (inv, action) {
      if (!inv || inv.id == null) return
      const act = action === 'accept' ? 'accept' : 'reject'
      this.teamInviteRespondingId = inv.id
      try {
        await respondTeamInvite(inv.id, act)
        this.$message.success(act === 'accept' ? '已同意入队' : '已拒绝邀请')
        await this.refreshPendingTeamInvites()
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMyTeamMembers()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        this.$message.error(
          (act === 'accept' ? '同意入队失败：' : '拒绝邀请失败：') +
            this.getApiErrorMessage(e, '未知错误')
        )
      } finally {
        this.teamInviteRespondingId = null
      }
    },

    async handleStudentTeamInviteMember () {
      if (!this.isCurrentTeamCaptain) {
        this.$message.warning('仅队长可邀请队员')
        return
      }
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
      if (!this.myTeamId) {
        this.$message.warning('请先确认队伍ID')
        return
      }
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertNotEnrolledInOtherDivision()) return
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      const studentRef = String(this.studentTeamInviteRef || '').trim()
      if (!studentRef) {
        this.$message.warning('请填写队员姓名或用户 ID')
        return
      }
      if (isEightDigitId(studentRef)) {
        if (!(await this.assertInviteeSameDivisionAsView(Number(studentRef)))) return
      }
      this.teamLoading = true
      try {
        const invitePayload = isEightDigitId(studentRef)
          ? { student_id: Number(studentRef) }
          : { student: studentRef }
        await inviteCompetitionTeamMember(this.myTeamId, invitePayload)
        this.$message.success('邀请已发送，对方同意后才会入队')
        this.studentTeamInviteRef = ''
        this.studentDivisionIndexCompetitionId = null
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMyTeamMembers()
        await this.refreshPendingTeamInvites()
      } catch (e) {
        const mapped = this.mapTeamInviteDetailToUserMessage(this.getEnrollDetailRaw(e))
        this.$message.error(mapped || ('邀请失败：' + this.getApiErrorMessage(e, '未知错误')))
      } finally {
        this.teamLoading = false
      }
    },

    async resolveTeamMemberUserIdByRef (ref, label = '队员') {
      const raw = String(ref || '').trim()
      if (!raw) {
        this.$message.warning(`请填写${label}姓名或用户 ID`)
        return null
      }
      if (isEightDigitId(raw)) return Number(raw)
      await this.refreshMyTeamMembers()
      const key = raw.toLowerCase()
      const matches = (this.myTeamMembers || []).filter(m => {
        if (!m) return false
        const fn = String(m.full_name || m.name || '').trim().toLowerCase()
        const un = String(m.username || '').trim().toLowerCase()
        return (fn && fn === key) || (un && un === key)
      })
      if (matches.length === 1) {
        const uid = Number(matches[0].user_id)
        return Number.isFinite(uid) ? uid : null
      }
      if (matches.length > 1) {
        this.$message.warning(`队内存在多名同名${label}，请改用 8 位用户 ID`)
        return null
      }
      this.$message.warning(`队内未找到该${label}，请确认姓名或改用用户 ID`)
      return null
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
      const userId = await this.resolveTeamMemberUserIdByRef(this.studentTeamRemoveRef, '队员')
      if (userId == null) return
      this.teamLoading = true
      try {
        await removeCompetitionTeamMember(this.myTeamId, userId)
        this.$message.success('已移除队员')
        this.studentTeamRemoveRef = ''
        await this.refreshActiveCompetitionMyEnrollKind()
        await this.refreshMyTeamMembers()
      } catch (e) {
        this.$message.error('移除失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.teamLoading = false
      }
    },

    parseAltUserIds (text) {
      return parseEightDigitIdsFromText(text)
    },

    warnInvalidEightDigitUserId (value, label = '用户ID') {
      const msg = validateEightDigitUserId(value, label)
      if (msg) {
        this.$message.warning(msg)
        return false
      }
      return true
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
      if (myId == null) return false
      const creatorId = this.getTeamCreatorAdvisorId(team)
      if (creatorId == null) return false
      return Number(creatorId) === Number(myId)
    },

    assertCompetitionOpenForTeamCreateOrInvite (showToast = true) {
      if (!this.competitionTeamCreateInviteBlocked) return true
      if (showToast) {
        const title = this.competitionTeamCreateInviteBlockedTitle || '当前不可进行该操作'
        const desc = this.competitionTeamCreateInviteBlockedDescription || ''
        this.$message.warning(desc ? `${title}：${desc}` : title)
      }
      return false
    },

    normalizeCompetitionTeamsList (res) {
      return normalizeCompetitionApiList(res)
    },

    async refreshAdvisorTeams () {
      if (!this.showAdvisorTeamPanel || !this.activeCompetitionId || !getStoredAltToken()) return
      this.advisorTeamsLoading = true
      try {
        if (!this.assertCompetitionDivisionQueryContext()) {
          this.advisorTeams = []
          return
        }
        const res = await getCompetitionTeams(
          this.activeCompetitionId,
          this.buildCompetitionDivisionQueryOptions()
        )
        this.advisorTeams = this.normalizeCompetitionTeamsList(res)
        this.syncActiveCompetitionAdvisorTeamDivision(this.advisorTeams)
        this.$emit('exam-papers-changed')
        const visible = this.advisorTeamsForCurrentView
        if (
          this.advisorSelectedTeamId != null &&
          !visible.some(t => Number(t.id) === Number(this.advisorSelectedTeamId))
        ) {
          this.advisorSelectedTeamId = null
          this.advisorRenameName = ''
          this.advisorInviteStudent = ''
        }
      } catch (e) {
        this.advisorTeams = []
        this.activeCompetitionAdvisorTeamDivision = null
        this.$emit('exam-papers-changed')
        this.$message.error('获取队伍列表失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.advisorTeamsLoading = false
      }
    },

    selectAdvisorTeam (teamId) {
      this.advisorSelectedTeamId = teamId
      const t = this.advisorSelectedTeam
      this.advisorRenameName = t && t.name != null ? String(t.name) : ''
      this.advisorInviteStudent = ''
    },

    async handleAdvisorCreateTeam () {
      if (!this.activeCompetitionId) return
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertAdvisorNotBlockedByOtherDivision()) return
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      if (!this.allowTeam) {
        this.$message.error('该竞赛不允许团队参赛')
        return
      }
      const memberRefs = parseNameOrIdTokens(this.advisorCreateForm.initial_members_text)
      const captainRef = String(this.advisorCreateForm.captain_student || '').trim()
      if (!captainRef && !memberRefs.length) {
        this.$message.warning('请填写队长（姓名或用户 ID），或至少一名初始队员')
        return
      }
      const division = (this.advisorCreateForm.division || '').trim()
      const workTrack = (this.advisorCreateForm.work_track || '').trim()
      if (division !== 'undergraduate' && division !== 'vocational') {
        this.$message.warning('请选择组别：本科或高职')
        return
      }
      if (workTrack !== 'works' && workTrack !== 'software' && workTrack !== 'hardware') {
        this.$message.warning('请选择赛道：作品、软件或硬件')
        return
      }
      const teamName = (this.advisorCreateForm.name || '').trim()
      if (!teamName) {
        this.$warning({
          title: '请填写队名',
          content: '创建队伍须填写队名，且同竞赛内队名不可重复。',
          okText: '知道了'
        })
        return
      }
      const payload = {
        competition_id: Number(this.activeCompetitionId),
        division,
        work_track: workTrack,
        name: teamName
      }
      if (captainRef) payload.captain_student = captainRef
      if (memberRefs.length) payload.initial_members = memberRefs

      this.advisorCreateLoading = true
      try {
        const team = await createCompetitionTeam(payload)
        const teamId = team && (team.id != null ? team.id : team.team_id)
        if (teamId != null) {
          const tid = Number(teamId)
          if (Number.isFinite(tid) && !this.advisorCreatedTeamIds.includes(tid)) {
            this.advisorCreatedTeamIds.push(tid)
          }
          const div =
            resolveTeamDivision(team) ||
            this.enrollDivisionForApi
          if (div) {
            saveCompetitionTeamDivision(this.activeCompetitionId, teamId, div)
            if (this.isActiveCompetitionDualDivision) {
              this.activeCompetitionAdvisorTeamDivision = div
            }
          }
        }
        this.$message.success(
          '队伍已创建并已向队长/队员发出入队邀请；对方同意后才会正式入队，队伍当前为「待校审」' +
            (teamId ? `（队伍 ID：${teamId}）` : '')
        )
        this.advisorCreateForm = {
          name: '',
          captain_student: '',
          initial_members_text: '',
          work_track: 'works',
          division: 'undergraduate'
        }
        await this.refreshAdvisorTeams()
        if (teamId) this.selectAdvisorTeam(teamId)
      } catch (e) {
        if (this.isDuplicateTeamNameError(e)) {
          this.showDuplicateTeamNameModal(e)
        } else {
          const mapped = this.mapTeamInviteDetailToUserMessage(this.getEnrollDetailRaw(e))
          this.$message.error(mapped || ('创建队伍失败：' + this.getApiErrorMessage(e, '未知错误')))
        }
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
        if (this.isDuplicateTeamNameError(e)) {
          this.showDuplicateTeamNameModal(e)
        } else {
          this.$message.error('修改队名失败：' + this.getApiErrorMessage(e, '未知错误'))
        }
      } finally {
        this.advisorTeamOpLoading = false
      }
    },

    async handleAdvisorInviteMember () {
      const team = this.advisorSelectedTeam
      if (!team || !this.canOperateAdvisorSelectedTeam) return
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertAdvisorNotBlockedByOtherDivision()) return
      if (!this.assertSelectedAdvisorTeamMatchesView()) return
      if (!this.assertCompetitionOpenForTeamCreateOrInvite()) return
      const studentRef = String(this.advisorInviteStudent || '').trim()
      if (!studentRef) {
        this.$message.warning('请填写学生姓名或用户 ID')
        return
      }
      if (isEightDigitId(studentRef)) {
        if (!(await this.assertInviteeSameDivisionAsView(Number(studentRef)))) return
      }
      this.advisorTeamOpLoading = true
      try {
        const invitePayload = isEightDigitId(studentRef)
          ? { student_id: Number(studentRef) }
          : { student: studentRef }
        await inviteCompetitionTeamMember(team.id, invitePayload)
        this.$message.success('邀请已发送，学生同意后才会入队并完成报名')
        this.advisorInviteStudent = ''
        this.studentDivisionIndexCompetitionId = null
        await this.refreshAdvisorTeams()
        this.selectAdvisorTeam(team.id)
      } catch (e) {
        const mapped = this.mapTeamInviteDetailToUserMessage(this.getEnrollDetailRaw(e))
        this.$message.error(mapped || ('邀请失败：' + this.getApiErrorMessage(e, '未知错误')))
      } finally {
        this.advisorTeamOpLoading = false
      }
    },

    async handleAdvisorRemoveMember (teamId, userId) {
      if (!teamId || userId == null) return
      if (this.competitionTeamRosterLocked) {
        this.$message.warning(this.competitionTeamRosterLockedMessage)
        return
      }
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
      if (file) {
        const name = String(file.name || '').toLowerCase()
        if (!name.endsWith('.zip')) {
          this.$message.warning('初赛作品请上传 .zip 压缩包')
          if (e && e.target) e.target.value = ''
          this.submissionForm.file = null
          return
        }
      }
      this.submissionForm.file = file || null
    },

    buildSubmissionTeamId () {
      if (this.submissionMode !== 'team') return null
      if (this.submissionTeamId) return this.submissionTeamId
      if (this.myTeamId) return this.myTeamId
      return null
    },

    /** §8.9 / §8.10–11 / §8.16.2 / §8.18–19：dual 竞赛按详情页组别传 query division */
    buildCompetitionDivisionQueryOptions () {
      const division = this.enrollDivisionForApi
      return division ? { division } : {}
    },

    buildAdminSubmissionsQueryOptions () {
      return {
        ...this.buildCompetitionDivisionQueryOptions(),
        page: this.adminSubmissionsPage,
        page_size: this.adminSubmissionsPageSize
      }
    },

    resetAdminSubmissionsPagination () {
      this.adminSubmissionsPage = 1
      this.adminSubmissionsTotal = 0
      this.syncAdminSubmissionsPaginationToRoute()
    },

    applyAdminSubmissionsPaginationFromRoute (syncWhenInvalid = false) {
      const routeQuery = (this.$route && this.$route.query) ? this.$route.query : {}
      const nextPage = Number(routeQuery.page)
      const nextPageSize = Number(routeQuery.page_size)
      const normalizedPage = Number.isFinite(nextPage) && nextPage >= 1 ? Math.floor(nextPage) : 1
      const normalizedPageSize = Number.isFinite(nextPageSize) && nextPageSize >= 1
        ? Math.min(100, Math.floor(nextPageSize))
        : 20
      const changed = normalizedPage !== this.adminSubmissionsPage || normalizedPageSize !== this.adminSubmissionsPageSize
      this.adminSubmissionsPage = normalizedPage
      this.adminSubmissionsPageSize = normalizedPageSize
      if (syncWhenInvalid && (!Number.isFinite(nextPage) || !Number.isFinite(nextPageSize) || nextPage < 1 || nextPageSize < 1)) {
        this.syncAdminSubmissionsPaginationToRoute()
      }
      if (changed && this.activeCompetitionId && this.canViewCompetitionSubmissions) {
        void this.refreshAdminSubmissions()
      }
    },

    syncAdminSubmissionsPaginationToRoute () {
      if (!this.$router || !this.$route) return
      const query = {
        ...(this.$route.query || {}),
        page: String(this.adminSubmissionsPage),
        page_size: String(this.adminSubmissionsPageSize)
      }
      const currentPage = this.$route.query && this.$route.query.page != null ? String(this.$route.query.page) : ''
      const currentPageSize = this.$route.query && this.$route.query.page_size != null ? String(this.$route.query.page_size) : ''
      if (currentPage === query.page && currentPageSize === query.page_size) return
      this.$router.replace({ query }).catch(() => {})
    },

    handleAdminSubmissionsPageChange (page, pageSize) {
      const nextPage = Number(page)
      const nextPageSize = Number(pageSize)
      this.adminSubmissionsPage = Number.isFinite(nextPage) && nextPage >= 1 ? Math.floor(nextPage) : 1
      if (Number.isFinite(nextPageSize) && nextPageSize >= 1 && nextPageSize !== this.adminSubmissionsPageSize) {
        this.adminSubmissionsPageSize = Math.floor(nextPageSize)
      }
      this.syncAdminSubmissionsPaginationToRoute()
      void this.refreshAdminSubmissions()
    },

    assertCompetitionDivisionQueryContext (showToast = true) {
      if (!this.isActiveCompetitionDualDivision) return true
      if (this.activeViewDivision) return true
      if (showToast) {
        this.$message.warning('该竞赛分本科组与高职组，请先选择组别后再查看队伍、花名册或评分统计')
        if (this.standaloneDetailMode) this.syncDualDivisionContextAfterCompetitionSelect()
      }
      return false
    },

    normalizeSubmissionsListResponse (res) {
      const list = normalizeCompetitionApiList(res)
      return filterSubmissionsByViewDivision(list, this.activeViewDivision)
    },

    submissionDivisionLabel (submission) {
      const d = resolveEnrollmentDivision(submission || {})
      return divisionToLabel(d) || ''
    },

    buildSubmissionRequestBody (title, contentText) {
      const body = {
        competition_id: Number(this.activeCompetitionId),
        title,
        description: (this.submissionForm.description || '').trim() || null,
        content_text: contentText || null
      }
      if (this.submissionMode === 'team') {
        body.team_id = Number(this.buildSubmissionTeamId())
      } else {
        body.team_id = null
      }
      const division = this.enrollDivisionForApi
      if (division) body.division = division
      return body
    },

    appendSubmissionFieldsToFormData (formData, body) {
      formData.append('competition_id', body.competition_id)
      if (body.team_id != null && body.team_id !== '') {
        formData.append('team_id', body.team_id)
      }
      if (body.division) formData.append('division', body.division)
      formData.append('title', body.title)
      if (body.description) formData.append('description', body.description)
      if (body.content_text) formData.append('content_text', body.content_text)
    },

    assertCompetitionOpenForSubmission (showToast = true) {
      if (!this.competitionSubmissionBlocked) return true
      if (showToast) {
        this.$message.warning(this.competitionSubmissionBlockedTitle)
      }
      return false
    },

    mapSubmissionDetailToUserMessage (detailText) {
      const t = (detailText || '').toLowerCase()
      if (t.includes('division is required')) {
        return '该竞赛分本科组与高职组，请从对应组别详情页进入后再提交作品'
      }
      if (t.includes('division must match your individual enrollment')) {
        return '作品组别须与个人报名组别一致，请切换到已报名的组别详情页'
      }
      if (t.includes('division must match team')) {
        return '作品组别须与队伍组别一致，请切换到对应组别详情页后再提交'
      }
      if (t.includes('only team captain may submit')) {
        return '只有队长可以提交队伍作品'
      }
      if (t.includes('approved by school admin') || t.includes('school admin')) {
        return '队伍须经本校校管理员校审通过后方可提交作品，请等待校审完成'
      }
      return null
    },

    async handleSubmitSubmission () {
      if (!this.activeCompetitionId) return
      if (!this.usesZipPackageSubmission || this.activeEnrollmentWorkTrack !== 'works') {
        this.$message.warning('仅作品赛道可上传压缩包；软件 / 硬件赛道请使用分题答案上传')
        return
      }
      if (!this.assertEnrollDivisionContext()) return
      if (!this.assertNotEnrolledInOtherDivision()) return
      if (!this.assertCompetitionOpenForSubmission()) return
      if (this.submissionMode === 'team' && this.teamSchoolReviewSubmissionBlocked) {
        this.$message.warning(this.teamSchoolReviewBlockedDescription)
        return
      }
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
      if (!file) {
        this.$message.error('请上传作品压缩包（.zip）')
        return
      }

      const teamId = this.buildSubmissionTeamId()
      if (this.submissionMode === 'team' && !teamId) {
        this.$message.error('队伍提交需要 team_id（请填写队伍ID或先创建队伍）')
        return
      }

      const requestBody = this.buildSubmissionRequestBody(title, contentText)

      this.submitLoading = true
      try {
        if (file) {
          const formData = new FormData()
          this.appendSubmissionFieldsToFormData(formData, requestBody)
          formData.append('file', file)
          await uploadCompetitionSubmission(formData)
        } else {
          await submitCompetitionSubmission(requestBody)
        }

        this.$message.success('提交成功')
        this.resetSubmissionFormFields()
        clearCompetitionWithdrawSubmissionCutoff(this.activeCompetitionId)
        this.ignoreSubmissionsBeforeReenrollAt = null
        await this.refreshMySubmissions()
        this.syncIgnoreSubmissionsAfterEnrollRefresh()
        await this.refreshMyScores(false, { skipSubmissionsRefresh: true })
      } catch (e) {
        const mapped = this.mapSubmissionDetailToUserMessage(this.getEnrollDetailRaw(e))
        this.$message.error(mapped || ('提交失败：' + this.getApiErrorMessage(e, '未知错误')))
      } finally {
        this.submitLoading = false
      }
    },

    async refreshMySubmissions () {
      if (!this.activeCompetitionId) return
      this.submissionsLoading = true
      try {
        const res = await getCompetitionSubmissions(
          this.activeCompetitionId,
          this.buildCompetitionDivisionQueryOptions()
        )
        this.mySubmissions = keepLatestSubmissionPerTeam(this.normalizeSubmissionsListResponse(res))
      } catch (e) {
        this.mySubmissions = []
        this.$message.error('获取作品列表失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.submissionsLoading = false
      }
    },

    async downloadSubmission (submissionId, row) {
      if (!submissionId) return
      try {
        const result = await downloadCompetitionSubmissionFile(submissionId)
        const blob = result && result.blob != null ? result.blob : result
        let filename = (result && result.filename) || ''
        // 兜底：优先用队伍名命名压缩包
        if (!filename || /\.bin$/i.test(filename) || /^submission_/i.test(filename)) {
          const teamName = row && (row.team_name || (row.team_id != null ? `队伍${row.team_id}` : ''))
          const safeName = String(teamName || '')
            .replace(/[<>:"/\\|?*\x00-\x1f]+/g, '_')
            .trim()
          filename = safeName ? `${safeName}.zip` : `submission_${submissionId}.zip`
        }
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
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

    formatQuestionScoreCell (v) {
      if (v == null || v === '') return '—'
      const n = typeof v === 'number' ? v : Number(v)
      return Number.isFinite(n) ? String(n) : '—'
    },

    /** 归一化 GET scores/me 响应体（含可选嵌套 data） */
    normalizeScoresMeResponse (res) {
      if (!res || typeof res !== 'object') {
        return { competition_id: null, submissions: [], team_grades: [] }
      }
      if (Array.isArray(res.submissions) || Array.isArray(res.team_grades)) {
        return {
          competition_id: res.competition_id != null ? res.competition_id : null,
          submissions: Array.isArray(res.submissions) ? res.submissions : [],
          team_grades: Array.isArray(res.team_grades) ? res.team_grades : []
        }
      }
      const inner = res.data
      if (inner && typeof inner === 'object' && (Array.isArray(inner.submissions) || Array.isArray(inner.team_grades))) {
        return {
          competition_id: inner.competition_id != null ? inner.competition_id : null,
          submissions: Array.isArray(inner.submissions) ? inner.submissions : [],
          team_grades: Array.isArray(inner.team_grades) ? inner.team_grades : []
        }
      }
      return {
        competition_id: res.competition_id != null ? res.competition_id : null,
        submissions: [],
        team_grades: []
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
        const parsed = this.normalizeScoresMeResponse(res)
        const cid = parsed.competition_id
        const submissions = parsed.submissions || []
        const teamGrades = parsed.team_grades || []
        this.myScores = {
          competition_id: cid != null ? cid : this.activeCompetitionId,
          submissions,
          team_grades: teamGrades
        }
        if (showModal) {
          this.showMyScoresModal = true
          if (submissions.length === 0 && teamGrades.length === 0) {
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

    resolveCompetitionQrUrlValue (v) {
      if (!v) return null
      if (typeof v === 'string') return v
      if (typeof v === 'object') {
        if (v.image_url != null && String(v.image_url).trim()) return String(v.image_url).trim()
        if (v.url != null && String(v.url).trim()) return String(v.url).trim()
      }
      return null
    },

    /** 竞赛二维码下载接口需鉴权，不可作为 <img src> 直连（浏览器不会带 Authorization） */
    isCompetitionQrProtectedUrl (url) {
      if (url == null || String(url).trim() === '') return false
      const s = String(url).trim().toLowerCase()
      if (s.includes('/qr-code')) return true
      if (s.includes('/competitions/') && (s.includes('qr') || s.endsWith('/qr-code'))) return true
      if (s.startsWith('/api/') || s.startsWith('/v1/competitions/')) return true
      return false
    },

    canUseQrAsDirectImgSrc (url) {
      if (!url || this.isCompetitionQrProtectedUrl(url)) return false
      return /^https?:\/\//i.test(String(url).trim())
    },

    isQrImageBlob (blob) {
      if (!blob || typeof blob.size !== 'number' || blob.size <= 0) return false
      const t = (blob.type || '').toLowerCase()
      if (t.includes('json') || t.includes('html') || t.includes('text/plain')) return false
      return (
        t.startsWith('image/') ||
        t === 'application/octet-stream' ||
        t === '' ||
        t === 'binary/octet-stream'
      )
    },

    async loadCompetitionQrObjectUrl (competitionId, options = {}) {
      if (!competitionId) return null
      try {
        const blob = await getCompetitionQrCode(competitionId, options)
        if (!this.isQrImageBlob(blob)) return null
        return URL.createObjectURL(blob)
      } catch (e) {
        return null
      }
    },

    /** 按 §8.1.1 qr_codes + 当前组别拉取可展示的二维码（走鉴权 blob，不用 image_url 直连） */
    buildCompetitionQrFetchOptions (comp, division) {
      const opts = {}
      if (!comp || !this.isCompetitionDualDivision(comp)) return opts
      const layout = String(comp.qr_layout || 'shared').toLowerCase()
      if (layout === 'separate') {
        const div = division === 'undergraduate' || division === 'vocational' ? division : null
        if (div) opts.division = div
      }
      return opts
    },

    async loadCompetitionQrForCurrentView (competitionId, comp, division) {
      const opts = this.buildCompetitionQrFetchOptions(comp, division)
      return this.loadCompetitionQrObjectUrl(competitionId, opts)
    },

    resolveCompetitionQrUrls (comp) {
      const out = { shared: null, undergraduate: null, vocational: null }
      if (!comp || typeof comp !== 'object') return out
      const codes = comp.qr_codes
      if (codes && typeof codes === 'object') {
        out.shared = this.resolveCompetitionQrUrlValue(codes.shared)
        out.undergraduate = this.resolveCompetitionQrUrlValue(codes.undergraduate)
        out.vocational = this.resolveCompetitionQrUrlValue(codes.vocational)
      }
      if (comp.qr_code_image_url) {
        out.shared = out.shared || String(comp.qr_code_image_url)
      }
      return out
    },

    appendCompetitionDivisionFields (fd, form) {
      const mode = (form && form.division_mode) || 'single'
      fd.append('division_mode', mode)
      if (mode === 'dual') {
        fd.append('qr_layout', (form && form.qr_layout) || 'shared')
      }
    },

    appendCreateCompetitionQrFiles (fd) {
      if (this.createCompetitionNeedsSharedQr && this.createCompetitionQrFile) {
        fd.append('qr_code_image', this.createCompetitionQrFile, this.createCompetitionQrFile.name)
      }
      if (this.createCompetitionNeedsSeparateQr) {
        if (this.createCompetitionQrUndergraduateFile) {
          fd.append(
            'qr_code_image_undergraduate',
            this.createCompetitionQrUndergraduateFile,
            this.createCompetitionQrUndergraduateFile.name
          )
        }
        if (this.createCompetitionQrVocationalFile) {
          fd.append(
            'qr_code_image_vocational',
            this.createCompetitionQrVocationalFile,
            this.createCompetitionQrVocationalFile.name
          )
        }
      }
      if (this.createCompetitionLogoFile) {
        fd.append('logo_image', this.createCompetitionLogoFile, this.createCompetitionLogoFile.name)
      }
    },

    appendEditCompetitionQrFiles (fd) {
      if (this.editCompetitionNeedsSharedQr && this.editCompetitionQrFile) {
        fd.append('qr_code_image', this.editCompetitionQrFile, this.editCompetitionQrFile.name)
      }
      if (this.editCompetitionNeedsSeparateQr) {
        if (this.editCompetitionQrUndergraduateFile) {
          fd.append(
            'qr_code_image_undergraduate',
            this.editCompetitionQrUndergraduateFile,
            this.editCompetitionQrUndergraduateFile.name
          )
        }
        if (this.editCompetitionQrVocationalFile) {
          fd.append(
            'qr_code_image_vocational',
            this.editCompetitionQrVocationalFile,
            this.editCompetitionQrVocationalFile.name
          )
        }
      }
      if (this.editCompetitionLogoFile) {
        fd.append('logo_image', this.editCompetitionLogoFile, this.editCompetitionLogoFile.name)
      }
    },

    hasEditCompetitionQrUploads () {
      return !!(
        this.editCompetitionQrFile ||
        this.editCompetitionQrUndergraduateFile ||
        this.editCompetitionQrVocationalFile ||
        this.editCompetitionLogoFile
      )
    },

    revokeBlobUrl (refKey) {
      const url = this[refKey]
      if (url) {
        try {
          URL.revokeObjectURL(url)
        } catch (e) { /* noop */ }
        this[refKey] = null
      }
    },

    revokeCreateQrPreviewUrls () {
      this.revokeBlobUrl('createQrBlobUrl')
      this.revokeBlobUrl('createQrUndergraduateBlobUrl')
      this.revokeBlobUrl('createQrVocationalBlobUrl')
      this.revokeBlobUrl('createLogoBlobUrl')
    },

    clearCreateSharedQrFiles () {
      this.revokeBlobUrl('createQrBlobUrl')
      this.createCompetitionQrFile = null
      this.qrCodeFileList = []
      this.qrCodeValidating = false
    },

    clearCreateSeparateQrFiles () {
      this.revokeBlobUrl('createQrUndergraduateBlobUrl')
      this.revokeBlobUrl('createQrVocationalBlobUrl')
      this.createCompetitionQrUndergraduateFile = null
      this.createCompetitionQrVocationalFile = null
      this.qrCodeUndergraduateFileList = []
      this.qrCodeVocationalFileList = []
      this.qrCodeUndergraduateValidating = false
      this.qrCodeVocationalValidating = false
    },

    onCreateDivisionModeChange (e) {
      const v = e && e.target ? e.target.value : this.createCompetitionForm.division_mode
      if (v === 'single') {
        this.createCompetitionForm.qr_layout = 'shared'
        this.clearCreateSeparateQrFiles()
      }
    },

    onCreateQrLayoutChange () {
      if (this.createCompetitionForm.qr_layout === 'shared') {
        this.clearCreateSeparateQrFiles()
      } else {
        this.clearCreateSharedQrFiles()
      }
    },

    onEditDivisionModeChange (e) {
      const v = e && e.target ? e.target.value : this.editCompetitionForm.division_mode
      if (v === 'single') {
        this.editCompetitionForm.qr_layout = 'shared'
        this.clearEditSeparateQrUploads()
      }
    },

    onEditQrLayoutChange () {
      if (this.editCompetitionForm.qr_layout === 'shared') {
        this.clearEditSeparateQrUploads()
      } else {
        this.clearEditSharedQrUpload()
      }
    },

    resetCreateCompetitionForm () {
      this.revokeCreateQrPreviewUrls()
      this.clearCreateSharedQrFiles()
      this.clearCreateSeparateQrFiles()
      this.clearCreateLogoUpload()
      this.createCompetitionForm = {
        name: '',
        description: '',
        rules_text: '',
        target_audience: '',
        contact_name: '',
        contact_phone: '',
        location: '',
        environment: '',
        start_at: '',
        end_at: '',
        final_start_at: '',
        final_end_at: '',
        stage_mode: 'single',
        allow_individual: false,
        allow_team: true,
        division_mode: 'single',
        qr_layout: 'shared'
      }
    },

    clearCreateLogoUpload () {
      this.revokeBlobUrl('createLogoBlobUrl')
      this.createCompetitionLogoFile = null
      this.logoFileList = []
    },

    handleLogoRemove () {
      this.clearCreateLogoUpload()
      return true
    },

    validateCompetitionLogoImageFile (file) {
      const MAX = 5 * 1024 * 1024
      const allowed = ['image/png', 'image/jpeg', 'image/jpg', 'image/pjpeg', 'image/gif', 'image/webp']
      if (!allowed.includes(file.type)) {
        this.$message.warning('Logo 仅支持 png、jpeg、gif、webp 格式')
        return false
      }
      if (file.size > MAX) {
        this.$message.warning('Logo 图片不能超过 5MB')
        return false
      }
      return true
    },

    beforeLogoUpload (file) {
      if (!this.validateCompetitionLogoImageFile(file)) return false
      this.revokeBlobUrl('createLogoBlobUrl')
      const url = URL.createObjectURL(file)
      this.createLogoBlobUrl = url
      this.createCompetitionLogoFile = file
      this.logoFileList = [{ uid: 'logo-1', name: file.name, status: 'done', url }]
      return false
    },

    handleQrCodeRemove () {
      this.clearCreateSharedQrFiles()
      return true
    },

    handleQrCodeUndergraduateRemove () {
      this.revokeBlobUrl('createQrUndergraduateBlobUrl')
      this.createCompetitionQrUndergraduateFile = null
      this.qrCodeUndergraduateFileList = []
      return true
    },

    handleQrCodeVocationalRemove () {
      this.revokeBlobUrl('createQrVocationalBlobUrl')
      this.createCompetitionQrVocationalFile = null
      this.qrCodeVocationalFileList = []
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
        this.revokeBlobUrl('createQrBlobUrl')
        const url = URL.createObjectURL(file)
        this.createQrBlobUrl = url
        this.createCompetitionQrFile = file
        this.qrCodeFileList = [{ uid: 'qr-1', name: file.name, status: 'done', url }]
      } finally {
        this.qrCodeValidating = false
      }
      return false
    },

    async beforeQrCodeUndergraduateUpload (file) {
      this.qrCodeUndergraduateValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeBlobUrl('createQrUndergraduateBlobUrl')
        const url = URL.createObjectURL(file)
        this.createQrUndergraduateBlobUrl = url
        this.createCompetitionQrUndergraduateFile = file
        this.qrCodeUndergraduateFileList = [{ uid: 'qr-ug', name: file.name, status: 'done', url }]
      } finally {
        this.qrCodeUndergraduateValidating = false
      }
      return false
    },

    async beforeQrCodeVocationalUpload (file) {
      this.qrCodeVocationalValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeBlobUrl('createQrVocationalBlobUrl')
        const url = URL.createObjectURL(file)
        this.createQrVocationalBlobUrl = url
        this.createCompetitionQrVocationalFile = file
        this.qrCodeVocationalFileList = [{ uid: 'qr-voc', name: file.name, status: 'done', url }]
      } finally {
        this.qrCodeVocationalValidating = false
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
      if (this.createCompetitionNeedsSharedQr && !this.createCompetitionQrFile) {
        this.$message.warning('请上传竞赛二维码图片')
        return
      }
      if (this.createCompetitionNeedsSeparateQr) {
        if (!this.createCompetitionQrUndergraduateFile) {
          this.$message.warning('请上传本科组二维码图片')
          return
        }
        if (!this.createCompetitionQrVocationalFile) {
          this.$message.warning('请上传高职组二维码图片')
          return
        }
      }

      this.adminCreateLoading = true
      try {
        const fd = new FormData()
        fd.append('name', name)
        fd.append('description', description)
        fd.append('rules_text', rulesText)
        const targetAudience = (this.createCompetitionForm.target_audience || '').trim()
        const contactName = (this.createCompetitionForm.contact_name || '').trim()
        const contactPhone = (this.createCompetitionForm.contact_phone || '').trim()
        const location = (this.createCompetitionForm.location || '').trim()
        const environment = (this.createCompetitionForm.environment || '').trim()
        if (targetAudience) fd.append('target_audience', targetAudience)
        if (contactName) fd.append('contact_name', contactName)
        if (contactPhone) fd.append('contact_phone', contactPhone)
        if (location) fd.append('location', location)
        if (environment) fd.append('environment', environment)
        const stageMode = this.createCompetitionForm.stage_mode || 'single'
        fd.append('stage_mode', stageMode)
        const startAt = toISO(this.createCompetitionForm.start_at)
        const endAt = toISO(this.createCompetitionForm.end_at)
        if (startAt) fd.append('start_at', startAt)
        if (endAt) fd.append('end_at', endAt)
        if (stageMode === 'prelim_final') {
          const finalStart = toISO(this.createCompetitionForm.final_start_at)
          const finalEnd = toISO(this.createCompetitionForm.final_end_at)
          if (finalStart) fd.append('final_start_at', finalStart)
          if (finalEnd) fd.append('final_end_at', finalEnd)
        }
        fd.append('allow_individual', 'false')
        fd.append('allow_team', 'true')
        this.appendCompetitionDivisionFields(fd, this.createCompetitionForm)
        this.appendCreateCompetitionQrFiles(fd)

        const res = await createCompetitionMultipart(fd)
        if (stageMode === 'prelim_final') {
          const paired = res && res.paired_competition_id
          this.$message.success(
            paired
              ? `已创建初赛 #${res.id} 与决赛 #${paired}`
              : '创建成功（初赛+决赛）'
          )
        } else {
          this.$message.success('创建成功，竞赛ID：' + (res && res.id ? res.id : '未知'))
        }
        this.showCreateCompetitionModal = false
        this.resetCreateCompetitionForm()
        await this.fetchCompetitions()
      } catch (e) {
        this.$message.error('创建失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminCreateLoading = false
      }
    },

    async openPromoteModal (track) {
      if (!this.activeCompetitionId || !this.isActiveCompetitionPreliminary) return
      this.promotionModalWorkTrack = track || null
      this.promotionSelectedTeamIds = []
      this.showPromoteModal = true
      this.promotionCandidatesLoading = true
      try {
        const res = await getPromotionCandidates(this.activeCompetitionId, {
          work_track: this.promotionModalWorkTrack || undefined
        })
        this.promotionCandidates = (res && res.teams) || []
      } catch (e) {
        this.promotionCandidates = []
        this.$message.error('加载可晋级队伍失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.promotionCandidatesLoading = false
      }
    },

    onPromotionCandidateSelectionChange (keys) {
      this.promotionSelectedTeamIds = (keys || []).map(k => Number(k)).filter(n => Number.isFinite(n))
    },

    async submitPromotions () {
      if (!this.activeCompetitionId) return Promise.reject(new Error('no competition'))
      const ids = (this.promotionSelectedTeamIds || []).filter(id => Number.isFinite(Number(id)))
      if (!ids.length) {
        this.$message.warning('请选择至少一支已校审通过的队伍')
        return Promise.reject(new Error('no teams selected'))
      }
      this.promotionSubmitLoading = true
      try {
        await createCompetitionPromotions(this.activeCompetitionId, {
          team_ids: ids,
          work_track: this.promotionModalWorkTrack || undefined
        })
        this.$message.success(`已晋级 ${ids.length} 支${this.workTrackSectionLabel(this.promotionModalWorkTrack)}队伍`)
        this.showPromoteModal = false
        await this.refreshPromotionList()
      } catch (e) {
        this.$message.error('晋级失败：' + this.getApiErrorMessage(e, '未知错误'))
        return Promise.reject(e)
      } finally {
        this.promotionSubmitLoading = false
      }
    },

    promotionsForTrack (track) {
      const key = String(track || '').trim().toLowerCase()
      return (this.promotionListRows || []).filter(row => {
        return String(row.work_track || '').trim().toLowerCase() === key
      })
    },

    promotionDivisionLabel (division) {
      const d = String(division || '').trim().toLowerCase()
      if (d === 'undergraduate') return '本科'
      if (d === 'vocational') return '高职'
      if (d === 'default' || !d) return '-'
      return d
    },

    async refreshPromotionList () {
      if (!this.activeCompetitionId) return
      if (!this.isActiveCompetitionPreliminary && !this.isActiveCompetitionFinal) {
        this.promotionList = []
        return
      }
      this.promotionListLoading = true
      try {
        const res = await getCompetitionPromotions(this.activeCompetitionId)
        this.promotionList = Array.isArray(res) ? res : []
      } catch (e) {
        this.promotionList = []
        this.$message.error('加载晋级名单失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.promotionListLoading = false
      }
    },

    async handleRevokePromotion (record) {
      if (!record || record.id == null || !this.activeCompetitionId) return
      const self = this
      this.$confirm({
        title: '撤销晋级',
        content: `确定撤销晋级记录 #${record.id}？将删除决赛侧对应队伍与报名（决赛开始后不可撤销）。`,
        okText: '撤销',
        okType: 'danger',
        cancelText: '取消',
        async onOk () {
          try {
            await revokeCompetitionPromotion(self.activeCompetitionId, record.id)
            self.$message.success('已撤销晋级')
            await self.refreshPromotionList()
          } catch (e) {
            self.$message.error('撤销失败：' + self.getApiErrorMessage(e, '未知错误'))
            return Promise.reject(e)
          }
        }
      })
    },

    async handlePublish () {
      if (!this.canManageCompetitions) return
      if (!this.publishCompetitionId) return
      this.publishLoading = true
      try {
        const res = await publishCompetition(this.publishCompetitionId)
        this.$message.success('发布成功')
        await this.fetchCompetitions()
        if (this.isSuperAdmin && res && res.id != null) {
          this.showCompetitionUrlModalWithComp(res)
        }
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

    revokeEditCurrentQrPreviews () {
      for (const p of this.editCurrentQrPreviews || []) {
        if (p && p.isBlob && p.url) {
          try {
            URL.revokeObjectURL(p.url)
          } catch (e) { /* noop */ }
        }
      }
      this.editCurrentQrPreviews = []
    },

    clearEditSharedQrUpload () {
      this.revokeBlobUrl('editQrBlobUrl')
      this.editCompetitionQrFile = null
      this.editQrCodeFileList = []
      this.editQrCodeValidating = false
    },

    clearEditSeparateQrUploads () {
      this.revokeBlobUrl('editQrUndergraduateBlobUrl')
      this.revokeBlobUrl('editQrVocationalBlobUrl')
      this.editCompetitionQrUndergraduateFile = null
      this.editCompetitionQrVocationalFile = null
      this.editQrCodeUndergraduateFileList = []
      this.editQrCodeVocationalFileList = []
      this.editQrCodeUndergraduateValidating = false
      this.editQrCodeVocationalValidating = false
    },

    resetEditCompetitionQrState () {
      this.clearEditSharedQrUpload()
      this.clearEditSeparateQrUploads()
      this.clearEditLogoUpload()
      this.revokeEditCurrentQrPreviews()
      this.revokeEditCurrentLogoPreview()
      this.editCurrentQrLoading = false
    },

    clearEditLogoUpload () {
      this.revokeBlobUrl('editLogoBlobUrl')
      this.editCompetitionLogoFile = null
      this.editLogoFileList = []
    },

    revokeEditCurrentLogoPreview () {
      if (this.editCurrentLogoIsBlob && this.editCurrentLogoPreviewUrl) {
        try {
          URL.revokeObjectURL(this.editCurrentLogoPreviewUrl)
        } catch (e) { /* noop */ }
      }
      this.editCurrentLogoPreviewUrl = null
      this.editCurrentLogoIsBlob = false
    },

    handleEditLogoRemove () {
      this.clearEditLogoUpload()
      return true
    },

    beforeEditLogoUpload (file) {
      if (!this.validateCompetitionLogoImageFile(file)) return false
      this.revokeBlobUrl('editLogoBlobUrl')
      const url = URL.createObjectURL(file)
      this.editLogoBlobUrl = url
      this.editCompetitionLogoFile = file
      this.editLogoFileList = [{ uid: 'edit-logo-1', name: file.name, status: 'done', url }]
      return false
    },

    handleEditQrCodeRemove () {
      this.clearEditSharedQrUpload()
      return true
    },

    handleEditQrCodeUndergraduateRemove () {
      this.revokeBlobUrl('editQrUndergraduateBlobUrl')
      this.editCompetitionQrUndergraduateFile = null
      this.editQrCodeUndergraduateFileList = []
      return true
    },

    handleEditQrCodeVocationalRemove () {
      this.revokeBlobUrl('editQrVocationalBlobUrl')
      this.editCompetitionQrVocationalFile = null
      this.editQrCodeVocationalFileList = []
      return true
    },

    async beforeEditQrCodeUpload (file) {
      this.editQrCodeValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeBlobUrl('editQrBlobUrl')
        const url = URL.createObjectURL(file)
        this.editQrBlobUrl = url
        this.editCompetitionQrFile = file
        this.editQrCodeFileList = [{ uid: 'edit-qr-1', name: file.name, status: 'done', url }]
      } finally {
        this.editQrCodeValidating = false
      }
      return false
    },

    async beforeEditQrCodeUndergraduateUpload (file) {
      this.editQrCodeUndergraduateValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeBlobUrl('editQrUndergraduateBlobUrl')
        const url = URL.createObjectURL(file)
        this.editQrUndergraduateBlobUrl = url
        this.editCompetitionQrUndergraduateFile = file
        this.editQrCodeUndergraduateFileList = [{ uid: 'edit-qr-ug', name: file.name, status: 'done', url }]
      } finally {
        this.editQrCodeUndergraduateValidating = false
      }
      return false
    },

    async beforeEditQrCodeVocationalUpload (file) {
      this.editQrCodeVocationalValidating = true
      try {
        const ok = await this.validateCompetitionQrImageFile(file)
        if (!ok) return false
        this.revokeBlobUrl('editQrVocationalBlobUrl')
        const url = URL.createObjectURL(file)
        this.editQrVocationalBlobUrl = url
        this.editCompetitionQrVocationalFile = file
        this.editQrCodeVocationalFileList = [{ uid: 'edit-qr-voc', name: file.name, status: 'done', url }]
      } finally {
        this.editQrCodeVocationalValidating = false
      }
      return false
    },

    async fetchEditCompetitionCurrentQr (competitionId, comp) {
      this.revokeEditCurrentQrPreviews()
      if (!competitionId) return
      this.editCurrentQrLoading = true
      const previews = []
      const pushBlobPreview = async (key, label, division) => {
        const objectUrl = await this.loadCompetitionQrForCurrentView(competitionId, comp, division)
        if (!objectUrl) return
        previews.push({ key, label, url: objectUrl, isBlob: true })
      }
      try {
        if (!comp || comp.division_mode == null) {
          comp = await this.ensureCompetitionDetail(competitionId) || comp
        }
        const mode = (comp && comp.division_mode) || 'single'
        const layout = (comp && comp.qr_layout) || 'shared'
        if (mode === 'dual' && layout === 'separate') {
          await pushBlobPreview('undergraduate', '当前 · 本科组', 'undergraduate')
          await pushBlobPreview('vocational', '当前 · 高职组', 'vocational')
        } else {
          await pushBlobPreview('shared', '当前 · 竞赛二维码', null)
        }
        this.editCurrentQrPreviews = previews
      } finally {
        this.editCurrentQrLoading = false
      }
    },

    async fetchEditCompetitionCurrentLogo (competitionId, comp) {
      this.revokeEditCurrentLogoPreview()
      if (!competitionId) return
      const hasLogo = !!(comp && (comp.logo_path || comp.logo_image_url))
      if (!hasLogo) return
      try {
        const blob = await getCompetitionLogo(competitionId)
        if (!blob) return
        const url = URL.createObjectURL(blob)
        this.editCurrentLogoPreviewUrl = url
        this.editCurrentLogoIsBlob = true
      } catch (e) {
        /* 无 Logo 或无权限时忽略 */
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
        if (rules !== (o.rules_text != null ? String(o.rules_text) : '')) changes.rules_text = rules || null

        const cmpText = (formKey, origKey) => {
          const next = form[formKey] != null ? String(form[formKey]).trim() : ''
          const prev = o[origKey] != null ? String(o[origKey]).trim() : ''
          if (next !== prev) changes[formKey] = next || null
        }
        cmpText('target_audience', 'target_audience')
        cmpText('contact_name', 'contact_name')
        cmpText('contact_phone', 'contact_phone')
        cmpText('location', 'location')
        cmpText('environment', 'environment')

        const startISO = this.toISOFromDateTimeLocal(form.start_at)
        if (startISO !== o.start_at) changes.start_at = startISO

        const endISO = this.toISOFromDateTimeLocal(form.end_at)
        if (endISO !== o.end_at) changes.end_at = endISO

        if (o.allow_individual !== false) changes.allow_individual = false
        if (!!form.allow_team !== o.allow_team) changes.allow_team = !!form.allow_team

        const divisionMode = form.division_mode || 'single'
        if (divisionMode !== (o.division_mode || 'single')) changes.division_mode = divisionMode
        if (divisionMode === 'dual') {
          const qrLayout = form.qr_layout || 'shared'
          if (qrLayout !== (o.qr_layout || 'shared')) changes.qr_layout = qrLayout
        }

        const stageMode = form.stage_mode || 'single'
        const originalStageMode = o.stage_mode || 'single'
        if (stageMode !== originalStageMode) changes.stage_mode = stageMode

        if (stageMode === 'prelim_final' && this.editCompetitionOriginalStage === 'single') {
          const finalStartISO = this.toISOFromDateTimeLocal(form.final_start_at)
          const finalEndISO = this.toISOFromDateTimeLocal(form.final_end_at)
          if (finalStartISO !== (o.final_start_at || null)) changes.final_start_at = finalStartISO
          if (finalEndISO !== (o.final_end_at || null)) changes.final_end_at = finalEndISO
        }
      } else {
        const name = (form.name || '').trim()
        if (name) changes.name = name
        if (form.description !== '') changes.description = form.description || null
        if (form.rules_text !== '') changes.rules_text = form.rules_text || ''

        const startISO = this.toISOFromDateTimeLocal(form.start_at)
        if (startISO !== null) changes.start_at = startISO
        const endISO = this.toISOFromDateTimeLocal(form.end_at)
        if (endISO !== null) changes.end_at = endISO

        changes.allow_individual = false
        changes.allow_team = !!form.allow_team
        changes.division_mode = form.division_mode || 'single'
        if (changes.division_mode === 'dual') {
          changes.qr_layout = form.qr_layout || 'shared'
        }
        const stageMode = form.stage_mode || 'single'
        changes.stage_mode = stageMode
        if (stageMode === 'prelim_final') {
          const finalStartISO = this.toISOFromDateTimeLocal(form.final_start_at)
          const finalEndISO = this.toISOFromDateTimeLocal(form.final_end_at)
          if (finalStartISO !== null) changes.final_start_at = finalStartISO
          if (finalEndISO !== null) changes.final_end_at = finalEndISO
        }
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

    async openEditCompetitionModal () {
      if (!this.canManageCompetitions) return
      const id = this.selectedCompetitionId || this.activeCompetitionId || this.publishCompetitionId
      if (!id) {
        this.$message.warning('请先在竞赛列表中选择要修改的竞赛')
        return
      }
      const comp =
        (await this.ensureCompetitionDetail(id)) ||
        this.activeCompetition ||
        null

      this.resetEditCompetitionQrState()
      this.editCompetitionId = id
      this.adminEditLoading = false
      this.showEditCompetitionModal = true
      void this.fetchEditCompetitionCurrentQr(id, comp)
      void this.fetchEditCompetitionCurrentLogo(id, comp)

      const stage = comp && comp.stage ? String(comp.stage).toLowerCase() : 'single'
      this.editCompetitionOriginalStage = stage
      this.editPairedCompetitionId = (comp && comp.paired_competition_id) || null

      let finalStartLocal = ''
      let finalEndLocal = ''
      let finalStartISO = null
      let finalEndISO = null
      if (stage === 'preliminary' && comp && comp.paired_competition_id) {
        try {
          const paired = await getCompetition(comp.paired_competition_id)
          if (paired) {
            finalStartLocal = this.toDateTimeLocalValue(paired.start_at) || ''
            finalEndLocal = this.toDateTimeLocalValue(paired.end_at) || ''
            finalStartISO = paired.start_at ? (new Date(paired.start_at)).toISOString() : null
            finalEndISO = paired.end_at ? (new Date(paired.end_at)).toISOString() : null
            this.mergeCompetitionIntoList(paired)
          }
        } catch (_) {
          /* 关联决赛暂不可读时仍可编辑本场 */
        }
      }

      const stageMode = stage === 'single' ? 'single' : 'prelim_final'

      const original = comp
        ? {
          name: comp.name || '',
          description: comp.description || '',
          rules_text: comp.rules_text || '',
          target_audience: comp.target_audience || '',
          contact_name: comp.contact_name || '',
          contact_phone: comp.contact_phone || '',
          location: comp.location || '',
          environment: comp.environment || '',
          start_at: comp.start_at ? (new Date(comp.start_at)).toISOString() : null,
          end_at: comp.end_at ? (new Date(comp.end_at)).toISOString() : null,
          final_start_at: finalStartISO,
          final_end_at: finalEndISO,
          stage_mode: stageMode,
          allow_individual: false,
          allow_team: !!comp.allow_team,
          division_mode: comp.division_mode || 'single',
          qr_layout: comp.qr_layout || 'shared'
        }
        : null

      this.editCompetitionOriginal = original
      this.editCompetitionForm = {
        name: (comp && comp.name) || '',
        description: (comp && (comp.description || '')) || '',
        rules_text: (comp && (comp.rules_text || '')) || '',
        target_audience: (comp && (comp.target_audience || '')) || '',
        contact_name: (comp && (comp.contact_name || '')) || '',
        contact_phone: (comp && (comp.contact_phone || '')) || '',
        location: (comp && (comp.location || '')) || '',
        environment: (comp && (comp.environment || '')) || '',
        start_at: (comp && this.toDateTimeLocalValue(comp.start_at)) || '',
        end_at: (comp && this.toDateTimeLocalValue(comp.end_at)) || '',
        final_start_at: finalStartLocal,
        final_end_at: finalEndLocal,
        stage_mode: stageMode,
        allow_individual: false,
        allow_team: comp ? !!comp.allow_team : false,
        division_mode: comp ? (comp.division_mode || 'single') : 'single',
        qr_layout: comp ? (comp.qr_layout || 'shared') : 'shared'
      }
    },

    async handleEditCompetition () {
      if (!this.canManageCompetitions) return Promise.reject(new Error('no permission'))
      if (!this.editCompetitionId) return Promise.reject(new Error('no competition'))

      const changes = this.buildEditCompetitionChanges()
      const hasQr = this.hasEditCompetitionQrUploads()

      if (changes.name !== undefined && !changes.name) {
        this.$message.warning('竞赛名称不能为空')
        return Promise.reject(new Error('empty name'))
      }

      if (!hasQr && Object.keys(changes).length === 0) {
        this.$message.info('未检测到需要修改的字段（更换二维码/Logo 请先在下方上传新图片）')
        return Promise.reject(new Error('no changes'))
      }

      this.adminEditLoading = true
      try {
        const editedId = this.editCompetitionId
        if (hasQr) {
          const fd = new FormData()
          this.appendEditCompetitionChangesToFormData(fd, changes)
          this.appendEditCompetitionQrFiles(fd)
          await updateCompetitionMultipart(editedId, fd)
        } else {
          await updateCompetition(editedId, changes)
        }
        if (changes.stage_mode === 'prelim_final' && this.editCompetitionOriginalStage === 'single') {
          this.$message.success('已升级为初赛+决赛')
        } else {
          this.$message.success(hasQr ? '修改成功（图片已更新）' : '修改成功')
        }
        this.showEditCompetitionModal = false
        this.resetEditCompetitionQrState()
        await this.fetchCompetitions()
        // 强制刷新详情缓存与页面上的二维码展示（避免仍显示旧 blob）
        await this.ensureCompetitionDetail(editedId)
        if (this.editPairedCompetitionId) {
          await this.ensureCompetitionDetail(this.editPairedCompetitionId)
        }
        if (
          String(this.activeCompetitionId) === String(editedId) ||
          String(this.activeCompetitionId) === String(this.editPairedCompetitionId)
        ) {
          void this.fetchStudentBriefingQr()
        }
      } catch (e) {
        if (e && (e.message === 'no changes' || e.message === 'empty name' || e.message === 'no permission' || e.message === 'no competition')) {
          throw e
        }
        this.$message.error('修改失败：' + this.getApiErrorMessage(e, e && e.message ? e.message : '未知错误'))
        return Promise.reject(e)
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

    emptyTeamQuestionGradeFields () {
      return {
        score_q1: '',
        score_q2: '',
        score_q3: '',
        score_q4: '',
        score_q5: ''
      }
    },

    gradeQuestionPlaceholder (q) {
      if (!q) return '请输入分数'
      const mn = q.min_score != null && Number.isFinite(Number(q.min_score)) ? Number(q.min_score) : 0
      const mx = q.max_score != null && Number.isFinite(Number(q.max_score)) ? Number(q.max_score) : 100
      return `${mn}～${mx}`
    },

    /** 发布试卷配置中的题目展示名（专家打分 / 表头共用） */
    formatQuestionDisplayName (q) {
      if (!q) return ''
      const no = q.no != null ? Number(q.no) : null
      const name = q.name != null ? String(q.name).trim() : ''
      if (name) return name
      return no != null && Number.isFinite(no) ? `第${no}题` : '题目'
    },

    getQuestionItemsForTrack (trackKey) {
      const cfg = this.getQuestionConfigForTrack(trackKey)
      const qs = (cfg && Array.isArray(cfg.questions)) ? cfg.questions : []
      const n = Number(cfg && cfg.question_count)
      const count = Number.isFinite(n) && n >= 1 && n <= 5 ? n : (qs.length || 5)
      if (qs.length) {
        return qs.slice(0, count).map((q, i) => ({
          no: q && q.no != null ? Number(q.no) : (i + 1),
          name: (q && q.name) || `第${i + 1}题`,
          min_score: q && q.min_score != null ? q.min_score : 0,
          max_score: q && q.max_score != null ? q.max_score : 100
        }))
      }
      return Array.from({ length: count }, (_, i) => ({
        no: i + 1,
        name: `第${i + 1}题`,
        min_score: 0,
        max_score: 100
      }))
    },

    /** 汇总/排行等多赛道混排时：取各赛道最大题数，题名优先用非默认名 */
    getMergedQuestionItemsForDisplay () {
      const tracks = ['works', 'software', 'hardware']
      let maxCount = 1
      const nameByNo = {}
      tracks.forEach((track) => {
        const items = this.getQuestionItemsForTrack(track)
        if (items.length > maxCount) maxCount = items.length
        items.forEach((q) => {
          const no = Number(q.no)
          if (!Number.isFinite(no)) return
          const name = String(q.name || '').trim()
          const fallback = `第${no}题`
          if (!nameByNo[no] || (name && name !== fallback && nameByNo[no] === fallback)) {
            nameByNo[no] = name || fallback
          }
        })
      })
      return Array.from({ length: maxCount }, (_, i) => {
        const no = i + 1
        return {
          no,
          name: nameByNo[no] || `第${no}题`,
          min_score: 0,
          max_score: 100
        }
      })
    },

    buildQuestionScoreColumns (trackKey, options = {}) {
      const items = trackKey
        ? this.getQuestionItemsForTrack(trackKey)
        : this.getMergedQuestionItemsForDisplay()
      const prefix = options.dataIndexPrefix || 'score_q'
      const width = options.width != null ? options.width : 88
      const useScopedSlots = !!options.useScopedSlots
      return items.map((q) => {
        const key = `${prefix}${q.no}`
        const col = {
          title: this.formatQuestionDisplayName(q),
          dataIndex: key,
          key,
          width
        }
        if (useScopedSlots) {
          col.scopedSlots = { customRender: key }
        }
        return col
      })
    },

    adminQuestionAnswerTableColumnsForTrack (trackKey) {
      const teamNameTitle = '队名'
      const qCols = this.getQuestionItemsForTrack(trackKey).map((q) => ({
        title: this.formatQuestionDisplayName(q),
        key: 'q' + q.no,
        scopedSlots: { customRender: 'q' + q.no },
        width: 150
      }))
      return [
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 100 },
        { title: teamNameTitle, dataIndex: 'team_name', key: 'team_name', ellipsis: true, width: 140 },
        ...qCols,
        { title: '上传', key: 'progress', scopedSlots: { customRender: 'progress' }, width: 72 },
        { title: '总分', key: 'totalScore', scopedSlots: { customRender: 'totalScore' }, width: 80 },
        { title: '操作', key: 'gradeActions', scopedSlots: { customRender: 'gradeActions' }, width: 100 }
      ]
    },

    onGradeQuestionScoreInput (no, e) {
      const key = 'score_q' + no
      if (!Object.prototype.hasOwnProperty.call(this.gradeForm, key)) return
      const raw = e && e.target != null ? e.target.value : e
      this.$set(this.gradeForm, key, raw != null ? String(raw) : '')
    },

    getQuestionConfigForTrack (trackKey) {
      const track = String(trackKey || '').trim().toLowerCase()
      const byTrack = this.activeSubmissionQuestionConfig
      if (byTrack && track && byTrack[track]) return byTrack[track]
      const fromComp = this.activeCompetition && this.activeCompetition.submission_question_config
      if (fromComp && track && fromComp[track]) return fromComp[track]
      return {
        question_count: 5,
        questions: [1, 2, 3, 4, 5].map(n => ({ no: n, name: `第${n}题`, min_score: 0, max_score: 100 })),
        total_min_score: 0,
        total_max_score: 500
      }
    },

    parseTeamQuestionScoreInput (raw, label, minScore, maxScore) {
      const n = parseFloat(raw)
      if (Number.isNaN(n)) {
        this.$message.error(`${label}必须是数字，例如：20`)
        return null
      }
      const mn = minScore != null && Number.isFinite(Number(minScore)) ? Number(minScore) : 0
      const mx = maxScore != null && Number.isFinite(Number(maxScore)) ? Number(maxScore) : 100
      if (n < mn || n > mx) {
        this.$message.error(`${label}须在 ${mn}～${mx} 之间`)
        return null
      }
      return n
    },

    collectGradeFormQuestionScores () {
      const items = this.gradeFormQuestionItems || []
      const scores = { score_q1: 0, score_q2: 0, score_q3: 0, score_q4: 0, score_q5: 0 }
      for (let i = 0; i < items.length; i++) {
        const q = items[i]
        const label = (q && q.name) || `第${q.no}题`
        const parsed = this.parseTeamQuestionScoreInput(
          this.gradeForm['score_q' + q.no],
          label,
          q.min_score,
          q.max_score
        )
        if (parsed == null) return null
        scores['score_q' + q.no] = parsed
      }
      const cfg = this.getQuestionConfigForTrack(this.gradeForm.work_track)
      const total = items.reduce((s, q) => s + Number(scores['score_q' + q.no] || 0), 0)
      const tmin = cfg && cfg.total_min_score != null ? Number(cfg.total_min_score) : 0
      const tmax = cfg && cfg.total_max_score != null ? Number(cfg.total_max_score) : 500
      if (Number.isFinite(tmin) && Number.isFinite(tmax) && (total < tmin || total > tmax)) {
        this.$message.error(`总分须在 ${tmin}～${tmax} 之间（当前 ${Math.round(total * 100) / 100}）`)
        return null
      }
      return scores
    },

    async fillTeamQuestionGradeForm (record, isEdit = false) {
      if (!this.canReviewSubmissions || !record) return
      this.gradeFormLoading = true
      this.gradeForm.submission_id = null
      this.gradeForm.team_id = record.team_id
      let track = record.work_track != null ? String(record.work_track).trim().toLowerCase() : ''
      if (track !== 'hardware' && track !== 'software' && track !== 'works' && record.team_id != null) {
        const mapped = (this.adminTeamWorkTrackById || {})[Number(record.team_id)]
        if (mapped) track = String(mapped).trim().toLowerCase()
      }
      this.gradeForm.work_track = (track === 'hardware' || track === 'software' || track === 'works')
        ? track
        : 'software'
      this.gradeForm.questionGradeExists = !!isEdit
      this.gradeFormIsEdit = !!isEdit
      this.gradeForm.score = ''
      if (isEdit) {
        this.gradeForm.score_q1 = record.score_q1 != null ? String(record.score_q1) : ''
        this.gradeForm.score_q2 = record.score_q2 != null ? String(record.score_q2) : ''
        this.gradeForm.score_q3 = record.score_q3 != null ? String(record.score_q3) : ''
        this.gradeForm.score_q4 = record.score_q4 != null ? String(record.score_q4) : ''
        this.gradeForm.score_q5 = record.score_q5 != null ? String(record.score_q5) : ''
        this.gradeForm.feedback = record.feedback ? String(record.feedback) : ''
      } else {
        Object.assign(this.gradeForm, this.emptyTeamQuestionGradeFields())
        this.gradeForm.feedback = ''
      }
      this.openGradeAuditModal()
      try {
        await this.refreshActiveSubmissionQuestionConfig()
      } finally {
        this.gradeFormLoading = false
      }
    },

    getGradeAuditModalContainer () {
      return document.body
    },

    openGradeAuditModal () {
      this.showGradeAudit = true
      this.$nextTick(() => {
        if (!this.showGradeAudit) this.showGradeAudit = true
      })
    },

    async fillGradeForm (submissionId, isEdit = false) {
      if (!this.canReviewSubmissions) return
      const sub = this.adminSubmissions.find(s => Number(s.id) === Number(submissionId))
      this.gradeForm.submission_id = submissionId
      this.gradeForm.team_id = sub && sub.team_id != null ? sub.team_id : null
      this.gradeForm.work_track = 'works'
      this.gradeForm.questionGradeExists = false
      this.gradeFormIsEdit = !!isEdit
      Object.assign(this.gradeForm, this.emptyTeamQuestionGradeFields())
      this.gradeForm.feedback = ''
      this.gradeForm.score = ''
      // 先弹出评分窗，再异步回填已有分数，避免接口等待时用户感觉“没反应”
      this.openGradeAuditModal()
      this.gradeFormLoading = true
      await this.refreshActiveSubmissionQuestionConfig()

      try {
        // 首次评分无需查询：后端对「未评分」固定返回 404，会在 Network 里造成误导
        if (isEdit && this.gradeForm.team_id && this.activeCompetitionId) {
          try {
            const g = await getTeamQuestionGrade(this.activeCompetitionId, this.gradeForm.team_id)
            if (g) {
              this.gradeForm.questionGradeExists = true
              this.gradeForm.score_q1 = g.score_q1 != null ? String(g.score_q1) : ''
              this.gradeForm.score_q2 = g.score_q2 != null ? String(g.score_q2) : ''
              this.gradeForm.score_q3 = g.score_q3 != null ? String(g.score_q3) : ''
              this.gradeForm.score_q4 = g.score_q4 != null ? String(g.score_q4) : ''
              this.gradeForm.score_q5 = g.score_q5 != null ? String(g.score_q5) : ''
              this.gradeForm.feedback = g.feedback ? String(g.feedback) : ''
            }
          } catch (_) {
            this.gradeForm.questionGradeExists = false
          }
        }

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

        if (!this.gradeForm.questionGradeExists) {
          if (this.gradeFormIsEdit && detail) {
            const scoreRaw = this.resolveSubmissionScoreRaw(detail)
            this.gradeForm.score = scoreRaw != null ? String(scoreRaw) : ''
            if (!this.gradeForm.feedback) {
              this.gradeForm.feedback = this.resolveSubmissionFeedback(detail)
            }
          } else {
            this.gradeForm.score = ''
            if (!this.gradeForm.feedback) this.gradeForm.feedback = ''
          }
        }
      } finally {
        this.gradeFormLoading = false
      }
    },

    cancelGradeAudit () {
      if (this.gradeLoading) return
      this.showGradeAudit = false
      this.gradeFormLoading = false
      this.gradeFormIsEdit = false
      this.gradeForm.submission_id = null
      this.gradeForm.team_id = null
      this.gradeForm.work_track = ''
      this.gradeForm.questionGradeExists = false
      this.gradeForm.score = ''
      Object.assign(this.gradeForm, this.emptyTeamQuestionGradeFields())
      this.gradeForm.feedback = ''
    },

    /** ant-design-vue 1.x：$confirm 不返回 Promise，且须高于评分弹窗 zIndex(3200) */
    confirmGradeEditSave (content) {
      return new Promise((resolve) => {
        this.$confirm({
          title: '修改评分',
          content: content || '确定保存评分修改吗？',
          okText: '确定',
          cancelText: '取消',
          zIndex: 4000,
          onOk: () => resolve(true),
          onCancel: () => resolve(false)
        })
      })
    },

    /** 保存后即时更新分题列表总分，并同步作品赛道压缩包列表分数 */
    applyTeamQuestionGradeToAdminRows (teamId, gradePayload, totalScore) {
      const tid = Number(teamId)
      if (!Number.isFinite(tid)) return
      const idx = (this.adminQuestionAnswerRows || []).findIndex(r => Number(r.team_id) === tid)
      if (idx >= 0) {
        const row = this.adminQuestionAnswerRows[idx]
        this.$set(this.adminQuestionAnswerRows, idx, {
          ...row,
          score_q1: gradePayload.score_q1,
          score_q2: gradePayload.score_q2,
          score_q3: gradePayload.score_q3,
          score_q4: gradePayload.score_q4,
          score_q5: gradePayload.score_q5,
          total_score: totalScore,
          feedback: gradePayload.feedback || '',
          graded: true
        })
      }
      const scoreNum = totalScore != null && totalScore !== '' ? Number(totalScore) : NaN
      if (!Number.isFinite(scoreNum)) return
      ;(this.adminSubmissions || []).forEach((s) => {
        if (!s || Number(s.team_id) !== tid || s.id == null) return
        this.applyReviewGradeToAdminSubmission(s.id, {
          score: scoreNum,
          feedback: gradePayload.feedback || '',
          reviewed_at: new Date().toISOString()
        })
      })
    },

    async handleReviewGrade () {
      if (!this.canReviewSubmissions) return
      if (this.gradeForm.team_id) {
        await this.handleTeamQuestionGrade()
        return
      }
      if (this.gradeForm.work_track === 'works') {
        await this.handleWorksIndividualQuestionGrade()
        return
      }
      if (!this.gradeForm.submission_id) return
      const scoreValue = parseFloat(this.gradeForm.score)
      if (Number.isNaN(scoreValue)) {
        this.$message.error('分数必须是数字，例如：95.0')
        return
      }

      const isEdit = this.gradeFormIsEdit
      if (isEdit) {
        const ok = await this.confirmGradeEditSave('确定保存对该作品评分的修改吗？')
        if (!ok) return
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

    async handleTeamQuestionGrade () {
      const teamId = this.gradeForm.team_id
      const competitionId = this.activeCompetitionId
      if (!teamId || !competitionId) return
      const scores = this.collectGradeFormQuestionScores()
      if (!scores) return
      const isEdit = !!this.gradeForm.questionGradeExists
      if (isEdit) {
        const ok = await this.confirmGradeEditSave('确定保存对该队伍评分的修改吗？总分将自动重新合计。')
        if (!ok) return
      }
      this.gradeLoading = true
      try {
        const payload = {
          ...scores,
          feedback: this.gradeForm.feedback || ''
        }
        let gradeRes = null
        if (isEdit) {
          gradeRes = await patchTeamQuestionGrade(competitionId, teamId, payload)
          this.$message.success('评分已更新，总分已自动合计')
        } else {
          gradeRes = await putTeamQuestionGrade(competitionId, teamId, payload)
          this.$message.success('评分提交成功，总分已自动合计')
        }
        const totalScore = gradeRes && gradeRes.total_score != null
          ? gradeRes.total_score
          : this.gradeFormAutoTotal
        this.applyTeamQuestionGradeToAdminRows(teamId, payload, totalScore)
        this.cancelGradeAudit()
        await this.refreshAdminSubmissions()
        this.applyTeamQuestionGradeToAdminRows(teamId, payload, totalScore)
      } catch (e) {
        const status = e && e.response && e.response.status
        const msg = (e && e.message) ? e.message : '未知错误'
        if (status === 400) {
          const notReviewed = /not graded|尚未评分|未评分/i.test(msg)
          if (notReviewed && isEdit) {
            this.$message.warning('该队伍尚未评分，请先点击「评分」完成首次评分')
            return
          }
        }
        const friendlyMsg = !isEdit && /already|已评|重复|duplicate/i.test(msg)
          ? '该队伍已评分，请刷新列表后点击「修改评分」'
          : msg
        this.$message.error((isEdit ? '修改评分失败：' : '评分失败：') + friendlyMsg)
      } finally {
        this.gradeLoading = false
      }
    },

    async handleWorksIndividualQuestionGrade () {
      if (!this.gradeForm.submission_id) return
      const scores = this.collectGradeFormQuestionScores()
      if (!scores) return
      const items = this.gradeFormQuestionItems || []
      const total = items.reduce((s, q) => s + Number(scores['score_q' + q.no] || 0), 0)
      const scoreValue = Math.round(total * 100) / 100
      const isEdit = this.gradeFormIsEdit
      if (isEdit) {
        const ok = await this.confirmGradeEditSave('确定保存对该作品分题评分的修改吗？总分将自动合计。')
        if (!ok) return
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
          this.$message.success('评分已更新，总分已自动合计')
        } else {
          reviewRes = await reviewCompetitionSubmissionGrade(gradedSubmissionId, payload)
          this.$message.success('评分提交成功，总分已自动合计')
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
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.adminSubmissionsLoading = true
      try {
        await this.refreshActiveSubmissionQuestionConfig()
        const loadQa = this.usesQuestionAnswerSubmission
        const loadZip = this.usesZipPackageSubmission
        // 管理端两者皆 true：同时拉取；学生端仅一种
        if (loadQa) {
          const res = await getCompetitionQuestionAnswersOverview(this.activeCompetitionId)
          const items = res && Array.isArray(res.items) ? res.items : []
          let rows = items.map((item) => {
            const slots = Array.isArray(item.slots) ? item.slots : []
            const byQ = {}
            slots.forEach((s) => {
              if (s && s.question_no != null) byQ[Number(s.question_no)] = s
            })
            const trackRaw = item.work_track != null ? String(item.work_track).trim().toLowerCase() : ''
            const workTrack = trackRaw === 'hardware' ? 'hardware' : (trackRaw === 'software' ? 'software' : trackRaw || '')
            const cfgCount = this.getQuestionItemsForTrack(workTrack || 'software').length
            const row = {
              team_id: item.team_id,
              team_name: item.team_name || `队伍${item.team_id}`,
              captain_id: item.captain_id,
              work_track: workTrack,
              uploaded_count: item.uploaded_count != null ? item.uploaded_count : 0,
              question_count: cfgCount || (item.question_count != null ? item.question_count : 5),
              graded: !!item.graded,
              score_q1: item.score_q1,
              score_q2: item.score_q2,
              score_q3: item.score_q3,
              score_q4: item.score_q4,
              score_q5: item.score_q5,
              total_score: item.total_score,
              feedback: item.feedback || ''
            }
            for (let q = 1; q <= 5; q++) {
              const slot = byQ[q]
              const submitted = !!(slot && (slot.submitted || (slot.answer && slot.answer.status === 'submitted')))
              row[`q${q}_uploaded`] = submitted
              row[`q${q}_answer_id`] = submitted && slot.answer && slot.answer.id != null ? slot.answer.id : null
              row[`q${q}_filename`] = submitted && slot.answer && slot.answer.filename ? slot.answer.filename : ''
            }
            return row
          })
          if (this.isCompetitionExpert && this.isExpertAssignedToActiveCompetition) {
            const allowed = new Set(getAltAssignedTeamIdsForCompetition(this.activeCompetitionId))
            rows = rows.filter(r => allowed.has(Number(r.team_id)))
          }
          this.adminQuestionAnswerRows = rows
        } else {
          this.adminQuestionAnswerRows = []
        }

        if (loadZip) {
          const cid = this.activeCompetitionId
          const divOpts = this.buildCompetitionDivisionQueryOptions()
          const submissionOpts = this.buildAdminSubmissionsQueryOptions()
          const expertView = this.expertAnonymizedView
          const [subRes, indRes, teamRes] = await Promise.all([
            getCompetitionSubmissions(cid, submissionOpts),
            expertView ? Promise.resolve([]) : getCompetitionParticipantsIndividual(cid, divOpts).catch(() => []),
            expertView ? Promise.resolve([]) : getCompetitionParticipantsTeams(cid, divOpts).catch(() => [])
          ])
          const teamTrackMap = {}
          normalizeCompetitionApiList(teamRes).forEach((t) => {
            if (!t || t.id == null) return
            const track = t.work_track != null ? String(t.work_track).trim().toLowerCase() : ''
            if (track === 'works' || track === 'software' || track === 'hardware') {
              teamTrackMap[Number(t.id)] = track
            }
          })
          const indTrackMap = {}
          normalizeCompetitionApiList(indRes).forEach((row) => {
            if (!row) return
            const sid = row.student_id != null ? row.student_id : row.user_id
            if (sid == null) return
            const track = row.work_track != null ? String(row.work_track).trim().toLowerCase() : ''
            if (track === 'works' || track === 'software' || track === 'hardware') {
              indTrackMap[Number(sid)] = track
            }
          })
          this.adminTeamWorkTrackById = teamTrackMap
          this.adminIndividualWorkTrackById = indTrackMap

          let raw = this.normalizeSubmissionsListResponse(subRes).map(item =>
            this.normalizeAdminSubmissionRow(item)
          )
          if (this.isCompetitionExpert && this.isExpertAssignedToActiveCompetition) {
            const allowed = new Set(getAltAssignedTeamIdsForCompetition(cid))
            raw = raw.filter(s => s && s.team_id != null && allowed.has(Number(s.team_id)))
          }
          let visible = raw
          if (!expertView) {
            const enrollIndex = buildEnrollmentVisibilityIndex(
              normalizeCompetitionApiList(indRes),
              normalizeCompetitionApiList(teamRes)
            )
            visible = filterAdminSubmissionsByActiveEnrollments(raw, enrollIndex)
            this.adminSubmissionsHiddenByWithdrawCount = Math.max(0, raw.length - visible.length)
          } else {
            this.adminSubmissionsHiddenByWithdrawCount = 0
          }
          this.adminSubmissions = keepLatestSubmissionPerTeam(visible)
          const total = Number(subRes && subRes.total)
          this.adminSubmissionsTotal = Number.isFinite(total) && total >= 0
            ? Math.min(total, this.adminSubmissions.length)
            : this.adminSubmissions.length
          await this.enrichAdminSubmissionsScores()
        } else {
          this.adminSubmissions = []
          this.adminTeamWorkTrackById = {}
          this.adminIndividualWorkTrackById = {}
          this.adminSubmissionsTotal = this.adminQuestionAnswerRows.length
          this.adminSubmissionsHiddenByWithdrawCount = 0
        }
        if (loadQa && !loadZip) {
          this.adminSubmissionsTotal = this.adminQuestionAnswerRows.length
          this.adminSubmissionsHiddenByWithdrawCount = 0
        }
      } catch (e) {
        this.adminQuestionAnswerRows = []
        this.adminSubmissions = []
        this.adminTeamWorkTrackById = {}
        this.adminIndividualWorkTrackById = {}
        this.adminSubmissionsTotal = 0
        this.adminSubmissionsHiddenByWithdrawCount = 0
        const label = this.usesQuestionAnswerSubmission ? '题目答案列表' : '作品列表'
        this.$message.error(`获取${label}失败：` + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.adminSubmissionsLoading = false
      }
    },

    /** @param {boolean} openModal 为 true 时打开汇总弹窗（仅用户点击「查看评分汇总」时使用） */
    async refreshScoresSummary (openModal = true) {
      if (!this.canViewScoreAnalytics) return
      if (!this.activeCompetitionId) return
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.summaryLoading = true
      try {
        const res = await getCompetitionScoresSummary(
          this.activeCompetitionId,
          this.buildCompetitionDivisionQueryOptions()
        )
        this.scoresSummary = res
        this.summaryScoreRows = this.buildSummaryScoreRows(res)
        if (openModal) this.showScoresSummaryModal = true
      } catch (e) {
        this.scoresSummary = null
        this.summaryScoreRows = []
        this.$message.error('获取汇总失败：' + (e && e.message ? e.message : '未知错误'))
        if (openModal) this.showScoresSummaryModal = false
      } finally {
        this.summaryLoading = false
      }
    },

    buildSummaryScoreRows (payload) {
      const list = payload && Array.isArray(payload.items) ? payload.items : []
      return list.map(item => {
        const q = n => (item['score_q' + n] != null && item['score_q' + n] !== '' ? String(item['score_q' + n]) : '')
        return {
          team_id: item.team_id,
          team_name: item.team_name || `队伍${item.team_id}`,
          school: item.school || '-',
          advisor_name: item.advisor_name || '-',
          captain_name: item.captain_name || (item.captain_id != null ? String(item.captain_id) : '-'),
          members: item.members || '-',
          score_q1: item.score_q1,
          score_q2: item.score_q2,
          score_q3: item.score_q3,
          score_q4: item.score_q4,
          score_q5: item.score_q5,
          total_score: item.total_score,
          graded: !!item.graded,
          feedback: item.feedback || '',
          edit_q1: q(1),
          edit_q2: q(2),
          edit_q3: q(3),
          edit_q4: q(4),
          edit_q5: q(5),
          saving: false
        }
      })
    },

    onSummaryScoreInput (record, questionNo, value) {
      if (!record) return
      this.$set(record, 'edit_q' + questionNo, value == null ? '' : String(value))
    },

    summaryRowAutoTotal (record) {
      if (!record) return '—'
      const items = this.getMergedQuestionItemsForDisplay()
      const nums = items.map(q => parseFloat(record['edit_q' + q.no]))
      if (!nums.length || nums.some(v => Number.isNaN(v))) return '—'
      const sum = nums.reduce((a, b) => a + b, 0)
      return String(Math.round(sum * 100) / 100)
    },

    async saveSummaryTeamGrade (record) {
      if (!this.canEditSummaryScores || !record || !this.activeCompetitionId) return
      const items = this.getMergedQuestionItemsForDisplay()
      const scores = { score_q1: 0, score_q2: 0, score_q3: 0, score_q4: 0, score_q5: 0 }
      for (let i = 0; i < items.length; i++) {
        const q = items[i]
        const parsed = this.parseTeamQuestionScoreInput(
          record['edit_q' + q.no],
          this.formatQuestionDisplayName(q),
          q.min_score,
          q.max_score
        )
        if (parsed == null) return
        scores['score_q' + q.no] = parsed
      }
      const payload = {
        ...scores,
        feedback: record.feedback || ''
      }
      this.$set(record, 'saving', true)
      try {
        let res
        if (record.graded) {
          res = await patchTeamQuestionGrade(this.activeCompetitionId, record.team_id, payload)
        } else {
          res = await putTeamQuestionGrade(this.activeCompetitionId, record.team_id, payload)
        }
        this.$set(record, 'graded', true)
        this.$set(record, 'score_q1', res && res.score_q1 != null ? res.score_q1 : scores.score_q1)
        this.$set(record, 'score_q2', res && res.score_q2 != null ? res.score_q2 : scores.score_q2)
        this.$set(record, 'score_q3', res && res.score_q3 != null ? res.score_q3 : scores.score_q3)
        this.$set(record, 'score_q4', res && res.score_q4 != null ? res.score_q4 : scores.score_q4)
        this.$set(record, 'score_q5', res && res.score_q5 != null ? res.score_q5 : scores.score_q5)
        this.$set(record, 'total_score', res && res.total_score != null ? res.total_score : null)
        this.$set(record, 'edit_q1', String(record.score_q1))
        this.$set(record, 'edit_q2', String(record.score_q2))
        this.$set(record, 'edit_q3', String(record.score_q3))
        this.$set(record, 'edit_q4', String(record.score_q4))
        this.$set(record, 'edit_q5', String(record.score_q5))
        this.$message.success('评分已保存')
        if (this.showScoresRankingsModal) {
          void this.refreshRankings()
        }
      } catch (e) {
        const msg = (e && e.message) ? e.message : '未知错误'
        if (/already graded|already|已评/i.test(msg) && !record.graded) {
          try {
            const res = await patchTeamQuestionGrade(this.activeCompetitionId, record.team_id, payload)
            this.$set(record, 'graded', true)
            this.$set(record, 'score_q1', res.score_q1)
            this.$set(record, 'score_q2', res.score_q2)
            this.$set(record, 'score_q3', res.score_q3)
            this.$set(record, 'score_q4', res.score_q4)
            this.$set(record, 'score_q5', res.score_q5)
            this.$set(record, 'total_score', res.total_score)
            this.$message.success('评分已更新')
            if (this.showScoresRankingsModal) void this.refreshRankings()
            return
          } catch (e2) {
            this.$message.error('保存评分失败：' + ((e2 && e2.message) ? e2.message : msg))
            return
          }
        }
        this.$message.error('保存评分失败：' + msg)
      } finally {
        this.$set(record, 'saving', false)
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
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.rankingsLoading = true
      try {
        const limit = this.rankingsLimit != null && this.rankingsLimit !== '' ? this.rankingsLimit : 50
        const res = await getCompetitionRankings(
          this.activeCompetitionId,
          limit,
          this.buildCompetitionDivisionQueryOptions()
        )
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
      const map = {
        pending_school_review: '待校审',
        active: '已通过',
        rejected: '已驳回',
        cancelled: '已取消',
        withdrawn: '已退赛',
        left: '已退队'
      }
      return map[status] || (status || '-')
    },

    applyMyTeamStatusFromTeam (team) {
      if (!team || typeof team !== 'object') return
      const st = team.status
      this.myTeamStatus = st != null && String(st).trim() !== ''
        ? String(st).trim()
        : 'pending_school_review'
    },

    applyMyTeamInfoFromTeam (team, fallbackName) {
      this.applyMyTeamStatusFromTeam(team)
      const rawTrack = team && team.work_track != null ? String(team.work_track).trim().toLowerCase() : ''
      this.myTeamWorkTrack = (rawTrack === 'works' || rawTrack === 'software' || rawTrack === 'hardware')
        ? rawTrack
        : null
      const fromTeam = team && team.name != null ? String(team.name).trim() : ''
      const fromFallback = fallbackName != null ? String(fallbackName).trim() : ''
      const name = fromTeam || fromFallback
      this.myTeamName = name || null
      const fromAdvisor = team && team.advisor_name != null ? String(team.advisor_name).trim() : ''
      this.myTeamAdvisorName = fromAdvisor || null
      if (team && Array.isArray(team.members)) {
        this.myTeamMembers = team.members
      }
    },

    async refreshMyTeamStatus () {
      if (!this.myTeamId) {
        this.myTeamStatus = null
      this.myTeamWorkTrack = null
        this.myTeamName = null
        this.myTeamAdvisorName = null
        this.myTeamMembers = []
        return
      }
      const tid = Number(this.myTeamId)
      if (!Number.isFinite(tid) || tid <= 0) {
        this.myTeamStatus = null
      this.myTeamWorkTrack = null
        this.myTeamName = null
        this.myTeamAdvisorName = null
        this.myTeamMembers = []
        return
      }
      try {
        const res = await getCompetitionTeam(tid)
        this.applyMyTeamInfoFromTeam(res)
      } catch (e) {
        /* 保留已有状态；无状态时由 effectiveMyTeamStatusNormalized 默认待校审 */
      }
    },

    async refreshParticipantsIndividual () {
      if (!this.canViewParticipantsRoster) return
      if (!this.activeCompetitionId) return
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.participantsIndividualLoading = true
      try {
        const res = await getCompetitionParticipantsIndividual(
          this.activeCompetitionId,
          this.buildCompetitionDivisionQueryOptions()
        )
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        this.participantsIndividual = list.map(item => ({
          sequence_no: item.sequence_no != null ? item.sequence_no : '-',
          division_label: divisionToLabel(resolveEnrollmentDivision(item)) || '-',
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
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.participantsTeamsLoading = true
      try {
        const res = await getCompetitionParticipantsTeams(
          this.activeCompetitionId,
          this.buildCompetitionDivisionQueryOptions()
        )
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        this.participantsTeams = list.map(item => {
          const members = Array.isArray(item.members) ? item.members : []
          const captain = members.find(m => m && m.is_captain) || null
          const nonCaptains = members.filter(m => m && !m.is_captain)
          const membersNames = nonCaptains
            .map(m => (m && (m.full_name || m.username)) ? (m.full_name || m.username) : null)
            .filter(Boolean)
          const memberIds = nonCaptains
            .map(m => (m && m.user_id != null) ? String(m.user_id) : null)
            .filter(Boolean)

          return {
            sequence_no: item.sequence_no != null ? item.sequence_no : '-',
            division_label: divisionToLabel(resolveEnrollmentDivision(item)) || '-',
            team_id: item.id,
            captain_id: item.captain_id,
            captain_name: captain ? (captain.full_name || captain.username || captain.user_id || '-') : '-',
            members_summary: membersNames.length ? membersNames.join('，') : '-',
            team_name_anon: item.name || `队伍${item.id}`,
            member_ids_summary: memberIds.length ? memberIds.join('，') : '-',
            status_text: this.participantTeamStatusText(item.status),
            created_at: this.formatDateTime(item.created_at)
          }
        })
        this.showParticipantsTeamsModal = true
      } catch (e) {
        this.participantsTeams = []
        this.showParticipantsTeamsModal = false
        this.$message.error('获取参赛者失败：' + (e && e.message ? e.message : '未知错误'))
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
      if (!this.assertCompetitionDivisionQueryContext()) return
      this.participantsTeamsExportLoading = true
      try {
        const divOpts = this.buildCompetitionDivisionQueryOptions()
        const rawBlob = await exportCompetitionTeamsExcel(this.activeCompetitionId, {
          ...divOpts,
          scope: 'current'
        })
        if (!rawBlob || (typeof rawBlob.size === 'number' && rawBlob.size <= 0)) {
          throw new Error('导出结果为空')
        }
        if (rawBlob.type && String(rawBlob.type).indexOf('application/json') >= 0) {
          const text = await rawBlob.text()
          let msg = '导出失败'
          try {
            const j = JSON.parse(text)
            msg = (j && (j.detail || j.message)) || msg
          } catch (_) {
            msg = text || msg
          }
          throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
        }
        // 强制按 zip 保存，避免浏览器缓存仍落成 .xlsx
        const blob = new Blob([rawBlob], { type: 'application/zip' })
        const filename = `competition_${this.activeCompetitionId}_roster.zip`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.setAttribute('download', filename)
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        this.$message.success('已导出参赛表格压缩包（作品/软件/硬件赛道各一份 Excel）')
      } catch (e) {
        this.$message.error('导出参赛表格失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.participantsTeamsExportLoading = false
      }
    },

    beforeImportPromotionsExcel (file, workTrack) {
      void this.handleImportPromotionsExcel(file, workTrack)
      return false
    },

    async handleImportPromotionsExcel (file, workTrack) {
      if (!this.canManageCompetitions || !this.activeCompetitionId) return
      if (!this.isActiveCompetitionPreliminary) {
        this.$message.warning('请在初赛竞赛下导入决赛名单')
        return
      }
      const track = String(workTrack || '').trim().toLowerCase()
      this.promotionImportLoading = track || true
      try {
        const res = await importCompetitionPromotionsExcel(
          this.activeCompetitionId,
          file,
          track || undefined
        )
        const imported = res && res.imported != null ? res.imported : 0
        const skipped = res && res.skipped != null ? res.skipped : 0
        const failed = res && res.failed != null ? res.failed : 0
        const trackLabel = track ? this.workTrackSectionLabel(track) : ''
        this.$message.success(
          `${trackLabel ? trackLabel + '：' : ''}导入完成：成功 ${imported}，跳过 ${skipped}，失败 ${failed}`
        )
        await this.refreshPromotionList()
      } catch (e) {
        this.$message.error('导入晋级名单失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.promotionImportLoading = null
      }
    },

    async refreshQuestionAnswersBoard () {
      const competitionId = this.activeCompetitionId
      const teamId = this.questionAnswerTeamId
      if (!competitionId || !teamId) {
        this.questionAnswerSlots = []
        return
      }
      this.questionAnswersLoading = true
      try {
        const res = await getCompetitionQuestionAnswersBoard(competitionId, teamId)
        const slots = res && Array.isArray(res.slots) ? res.slots : []
        this.questionAnswerSlots = slots
      } catch (e) {
        this.questionAnswerSlots = []
        this.$message.error('获取题目上传状态失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.questionAnswersLoading = false
      }
    },

    async onQuestionAnswerFileChange (event, questionNo) {
      const input = event && event.target
      const file = input && input.files && input.files[0]
      if (input) input.value = ''
      if (!file) return
      if (!this.canEditQuestionAnswerFiles) {
        this.$message.warning(this.hasFormalSubmittedQuestionAnswers ? '作品已正式提交，无法再上传题目文件' : '当前不可上传题目答案')
        return
      }
      const competitionId = this.activeCompetitionId
      const teamId = this.questionAnswerTeamId
      if (!competitionId || !teamId) {
        this.$message.warning('缺少竞赛或队伍信息')
        return
      }
      const qno = Number(questionNo)
      this.questionAnswerUploadingNo = qno
      try {
        const fd = new FormData()
        fd.append('team_id', String(teamId))
        fd.append('file', file)
        await uploadCompetitionQuestionAnswer(competitionId, qno, fd)
        this.$message.success(`第${qno}题答案上传成功`)
        await this.refreshQuestionAnswersBoard()
      } catch (e) {
        this.$message.error('上传失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.questionAnswerUploadingNo = null
      }
    },

    triggerQuestionAnswerFilePick (refName) {
      const el = this.$refs[refName]
      const input = Array.isArray(el) ? el[0] : el
      if (input && typeof input.click === 'function') input.click()
    },

    async downloadQuestionAnswer (answerId) {
      if (!this.activeCompetitionId || !answerId) return
      try {
        const result = await downloadCompetitionQuestionAnswer(this.activeCompetitionId, answerId)
        const blob = result && result.blob != null ? result.blob : result
        if (!blob || (typeof blob.size === 'number' && blob.size <= 0)) {
          throw new Error('文件为空')
        }
        const filename =
          (result && result.filename) ||
          `question_answer_${answerId}`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } catch (e) {
        this.$message.error('下载失败：' + this.getApiErrorMessage(e, '未知错误'))
      }
    },

    async deleteQuestionAnswer (answerId, questionNo) {
      if (!this.activeCompetitionId || !answerId) return
      if (!this.canEditQuestionAnswerFiles) {
        this.$message.warning(this.hasFormalSubmittedQuestionAnswers ? '作品已正式提交，无法再删除题目文件' : '当前不可删除题目答案')
        return
      }
      const qLabel = questionNo != null ? `第${questionNo}题` : '该题'
      try {
        await this.$confirm({
          title: '确认删除',
          content: `确定删除${qLabel}的答案吗？删除后可重新选择文件并再次上传作品。`,
          okText: '删除',
          okType: 'danger',
          cancelText: '取消'
        })
      } catch (_) {
        return
      }
      this.questionAnswerDeletingId = answerId
      try {
        await deleteCompetitionQuestionAnswer(this.activeCompetitionId, answerId)
        this.$message.success(`${qLabel}答案已删除`)
        await this.refreshQuestionAnswersBoard()
      } catch (e) {
        this.$message.error('删除失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.questionAnswerDeletingId = null
      }
    },

    async submitAllQuestionAnswers () {
      if (this.hasFormalSubmittedQuestionAnswers) {
        this.$message.warning('作品已正式提交，无法再提交')
        return
      }
      if (!this.canFormalSubmitQuestionAnswers) {
        this.$message.warning('请先为至少一道题选择答案文件')
        return
      }
      const competitionId = this.activeCompetitionId
      const teamId = this.questionAnswerTeamId
      if (!competitionId || !teamId) {
        this.$message.warning('缺少竞赛或队伍信息')
        return
      }
      // ant-design-vue 1.x 的 $confirm 不返回 Promise，必须用 onOk/onCancel 等待用户确认
      const confirmed = await new Promise((resolve) => {
        this.$confirm({
          title: '确认提交作品',
          content: '确认后将正式提交本队已选文件的题目答案。提交后全队都不能再上传、删除或再次提交，是否继续？',
          okText: '确认提交',
          cancelText: '取消',
          onOk: () => resolve(true),
          onCancel: () => resolve(false)
        })
      })
      if (!confirmed) return

      this.questionAnswersSubmitLoading = true
      try {
        await submitCompetitionQuestionAnswers(competitionId, teamId)
        this.$message.success('作品提交成功')
      } catch (e) {
        this.$message.error('提交作品失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.questionAnswersSubmitLoading = false
      }
      try {
        await this.refreshQuestionAnswersBoard()
      } catch (_) {
        /* refreshQuestionAnswersBoard 内部已提示 */
      }
    },

    adminQuestionAnswerRowsForTrack (trackKey) {
      const track = String(trackKey || '').trim().toLowerCase()
      return (this.adminQuestionAnswerRows || []).filter((r) => {
        const t = r && r.work_track != null ? String(r.work_track).trim().toLowerCase() : ''
        if (t === 'software' || t === 'hardware') return t === track
        // 兼容旧接口未返回 work_track：按队伍赛道映射
        if (r && r.team_id != null) {
          return (this.adminTeamWorkTrackById || {})[Number(r.team_id)] === track
        }
        return false
      })
    },

    workTrackSectionLabel (trackKey) {
      const t = String(trackKey || '').trim().toLowerCase()
      if (t === 'works') return '作品赛道'
      if (t === 'software') return '软件赛道'
      if (t === 'hardware') return '硬件赛道'
      return '赛道'
    },

    async exportQuestionAnswersZip (mode, workTrack) {
      if (!this.canExportAnswers) return
      if (!this.activeCompetitionId) {
        this.$message.warning('请先选择竞赛')
        return
      }
      const track = String(workTrack || '').trim().toLowerCase()
      if (!['works', 'software', 'hardware'].includes(track)) {
        this.$message.warning('请指定赛道')
        return
      }
      if (track === 'works' && mode !== 'by_team') {
        this.$message.warning('作品赛道仅支持按队伍导出')
        return
      }
      if ((track === 'software' || track === 'hardware') && !this.usesQuestionAnswerSubmission) {
        this.$message.warning('请使用分题答案上传')
        return
      }
      if (!this.competitionEnrollmentClosed) {
        this.$message.warning('竞赛尚未结束，结束后才可导出答案（状态为「已结束」或已过结束时间）')
        return
      }
      const loadingKey = `${track}:${mode}`
      this.questionAnswersExportLoading = loadingKey
      try {
        const blob = await exportCompetitionQuestionAnswers(this.activeCompetitionId, mode, track)
        if (!blob || (typeof blob.size === 'number' && blob.size <= 0)) {
          throw new Error('导出结果为空')
        }
        // 后端未结束时会返回 JSON 错误包在 blob 里
        if (blob.type && String(blob.type).indexOf('application/json') >= 0) {
          const text = await blob.text()
          let msg = '导出失败'
          try {
            const j = JSON.parse(text)
            msg = (j && (j.detail || j.message)) || msg
          } catch (_) {
            msg = text || msg
          }
          throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
        }
        const filename = `${this.workTrackSectionLabel(track)}.zip`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        this.$message.success(
          mode === 'by_team'
            ? `${this.workTrackSectionLabel(track)}按队伍导出成功`
            : `${this.workTrackSectionLabel(track)}按题目导出成功`
        )
      } catch (e) {
        this.$message.error('导出答案失败：' + this.getApiErrorMessage(e, '未知错误'))
      } finally {
        this.questionAnswersExportLoading = null
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

  ::v-deep .grade-audit-panel {
    background: #fff !important;
    border: 2px solid #1890ff !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  }

  ::v-deep .grade-audit-panel__title {
    color: rgba(0, 0, 0, 0.85) !important;
  }

  ::v-deep .grade-audit-panel .ant-form-item-label > label {
    color: rgba(0, 0, 0, 0.85) !important;
  }

  ::v-deep .sub-card .ant-form-item-label > label {
    color: rgba(255, 255, 255, 0.88);
  }

  /* 指导老师创建队伍：赛道/组别选项文字白色 */
  ::v-deep .advisor-form-radio-white.ant-radio-group .ant-radio-wrapper,
  ::v-deep .advisor-track-division-item .ant-radio-wrapper {
    color: #fff !important;
  }

  ::v-deep .advisor-form-radio-white.ant-radio-group .ant-radio-wrapper span,
  ::v-deep .advisor-track-division-item .ant-radio-wrapper > span:last-child {
    color: #fff !important;
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

  ::v-deep .sub-card .division-choice-self-risk {
    color: #ffd666;
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

/* 学生/指导老师独立详情：竞赛相关 DIRECTIONS（卡片分区 + 侧栏二维码） */
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
  margin-bottom: 22px;
}

.competition-briefing__main-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: #fff;
  text-shadow: 0 0 28px rgba(120, 200, 255, 0.4);
}

.competition-briefing__sub-en {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.42em;
  color: #f0c14b;
  text-transform: uppercase;
  text-shadow: 0 0 18px rgba(240, 193, 75, 0.45);
}

.competition-briefing__frame {
  position: relative;
  border: 1px solid rgba(120, 200, 255, 0.45);
  border-radius: 10px;
  box-shadow:
    0 0 0 1px rgba(180, 100, 255, 0.1),
    0 0 36px rgba(80, 160, 255, 0.18),
    inset 0 0 90px rgba(40, 20, 90, 0.28);
  background:
    radial-gradient(ellipse 80% 50% at 10% 0%, rgba(56, 160, 255, 0.16), transparent 55%),
    radial-gradient(ellipse 70% 45% at 90% 100%, rgba(160, 80, 255, 0.14), transparent 50%),
    linear-gradient(165deg, rgba(16, 12, 38, 0.88) 0%, rgba(10, 8, 28, 0.94) 55%, rgba(14, 10, 34, 0.9) 100%);
  overflow: hidden;
}

.competition-briefing__grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.1;
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
  gap: 18px;
  min-height: 240px;
  padding: 20px 18px 18px;
}

.competition-briefing__col--main {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.competition-briefing__col--aside {
  flex: 0 0 240px;
  max-width: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
}

.briefing-aside-panel {
  width: 100%;
  padding: 16px 14px 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(248, 250, 255, 0.96) 0%, rgba(232, 240, 255, 0.94) 100%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
  color: #1a1a2e;
}

.briefing-aside-panel__qr-wrap {
  margin-bottom: 12px;
}

.competition-briefing__qr {
  display: block;
  width: 176px;
  height: 176px;
  margin: 0 auto;
  object-fit: contain;
  border: 3px solid #fff;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(20, 40, 80, 0.18);
  background: #fff;
}

.competition-briefing__qr-placeholder {
  width: 176px;
  height: 176px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(40, 60, 100, 0.55);
  border: 1px dashed rgba(80, 120, 180, 0.45);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
}

.briefing-contact-card {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(90, 130, 200, 0.22);
}

.briefing-contact-card__label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #2f6fed;
  margin-bottom: 8px;
}

.briefing-contact-card__row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 4px;
  font-size: 13px;
  line-height: 1.55;
}

.briefing-contact-card__k {
  flex: 0 0 42px;
  color: rgba(30, 40, 70, 0.55);
  font-size: 12px;
}

.briefing-contact-card__v {
  flex: 1;
  min-width: 0;
  color: #1a1a2e;
  font-weight: 600;
  word-break: break-all;
}

.briefing-contact-card__empty {
  font-size: 12px;
  line-height: 1.55;
  color: rgba(30, 40, 70, 0.55);
}

.briefing-card {
  position: relative;
  padding: 16px 16px 14px 18px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.briefing-card--cyan {
  background: linear-gradient(135deg, rgba(40, 140, 220, 0.18), rgba(20, 40, 80, 0.28));
  border-color: rgba(90, 200, 255, 0.35);
}

.briefing-card--gold {
  background: linear-gradient(135deg, rgba(200, 150, 40, 0.16), rgba(40, 28, 20, 0.3));
  border-color: rgba(240, 193, 75, 0.32);
}

.briefing-card--violet {
  background: linear-gradient(135deg, rgba(140, 90, 220, 0.16), rgba(30, 20, 60, 0.3));
  border-color: rgba(180, 140, 255, 0.32);
}

.briefing-card--teal {
  background: linear-gradient(135deg, rgba(40, 180, 160, 0.14), rgba(16, 40, 50, 0.3));
  border-color: rgba(80, 220, 200, 0.3);
}

.briefing-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.briefing-card__num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 0.04em;
  color: #0a1628;
  background: linear-gradient(135deg, #7ad7ff, #5ecbff);
  box-shadow: 0 0 16px rgba(94, 203, 255, 0.35);
}

.briefing-card--gold .briefing-card__num {
  background: linear-gradient(135deg, #ffe08a, #f0c14b);
  box-shadow: 0 0 16px rgba(240, 193, 75, 0.35);
}

.briefing-card--violet .briefing-card__num {
  background: linear-gradient(135deg, #d2b8ff, #b388ff);
  box-shadow: 0 0 16px rgba(179, 136, 255, 0.35);
}

.briefing-card--teal .briefing-card__num {
  background: linear-gradient(135deg, #9af0e0, #5fd4c0);
  box-shadow: 0 0 16px rgba(95, 212, 192, 0.35);
}

.briefing-card__title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: #fff;
}

.briefing-card__text {
  font-size: 14px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.92);
  white-space: pre-wrap;
}

.briefing-tracks-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.briefing-tracks__intro {
  margin: 0;
  opacity: 0.95;
}

.briefing-tracks {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.briefing-track {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.18);
  border-left: 3px solid #5ecbff;
}

.briefing-track--1 {
  border-left-color: #f0c14b;
}

.briefing-track--2 {
  border-left-color: #b388ff;
}

.briefing-track__name {
  font-size: 15px;
  font-weight: 800;
  margin-bottom: 4px;
  letter-spacing: 0.04em;
}

.briefing-track--0 .briefing-track__name { color: #7ad7ff; }
.briefing-track--1 .briefing-track__name { color: #f0c14b; }
.briefing-track--2 .briefing-track__name { color: #d2b8ff; }

.briefing-track__body {
  font-size: 13px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.9);
  white-space: pre-wrap;
}

.briefing-rule-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.briefing-rule-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.16);
}

.briefing-rule-item__icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(240, 193, 75, 0.18);
  font-size: 16px;
}

.briefing-rule-item__title {
  font-size: 14px;
  font-weight: 800;
  color: #ffe08a;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}

.briefing-rule-item__desc {
  font-size: 13px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.9);
}

.briefing-env-table-wrap {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid rgba(120, 220, 200, 0.28);
}

.briefing-env-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.5;
}

.briefing-env-table th,
.briefing-env-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  vertical-align: top;
}

.briefing-env-table th {
  background: rgba(40, 180, 160, 0.22);
  color: #9af0e0;
  font-weight: 700;
  white-space: nowrap;
}

.briefing-env-table td {
  color: rgba(255, 255, 255, 0.92);
  background: rgba(0, 0, 0, 0.12);
}

.briefing-env-table tbody tr:last-child td {
  border-bottom: none;
}

.competition-briefing__footnotes {
  margin: 4px 0 0;
  padding-left: 1.1em;
  font-size: 12px;
  line-height: 1.7;
  color: rgba(230, 238, 255, 0.72);
  list-style: none;
}

.competition-briefing__footnotes li {
  position: relative;
  margin-bottom: 6px;
  padding-left: 0.5em;
}

.competition-briefing__footnotes li::before {
  content: '*';
  position: absolute;
  left: -0.85em;
  color: rgba(150, 210, 255, 0.85);
}

@media (max-width: 900px) {
  .competition-briefing__body {
    flex-direction: column;
  }

  .competition-briefing__col--aside {
    flex: 1 1 auto;
    max-width: none;
  }

  .competition-briefing__qr,
  .competition-briefing__qr-placeholder {
    width: 160px;
    height: 160px;
  }
}

/* 竞赛详情头图：无底色素块，透出独立详情页根节点背景图；文案保留浅色 + 阴影保证可读 */
.competition-hero-banner {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  margin-bottom: 20px;
  min-height: 240px;
  background: transparent;
}

.competition-hero-banner__inner--center {
  text-align: center;
}

.competition-hero-banner__copy {
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
  min-width: 0;
}

.competition-hero-banner__title-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 0 14px;
  min-height: 72px;
  padding: 12px 8px 4px;
}

.competition-hero-banner__year {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -54%);
  z-index: 0;
  margin: 0;
  font-size: ~'clamp(64px, 14vw, 112px)';
  font-weight: 200;
  line-height: 1;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.12);
  text-shadow: none;
  pointer-events: none;
  user-select: none;
  white-space: nowrap;
}

.competition-hero-banner__title {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  line-height: 1.3;
  letter-spacing: 0.02em;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.75), 0 2px 24px rgba(0, 0, 0, 0.45);
}

@media (min-width: 768px) {
  .competition-hero-banner__title {
    font-size: 36px;
  }
}

.competition-hero-banner__title-main {
  font-weight: 800;
}

.competition-hero-banner__title-stage {
  display: inline-block;
  margin-left: 0.28em;
  font-weight: 800;
}

.competition-hero-banner__title-stage--prelim {
  color: #7ad7ff;
  text-shadow: 0 0 18px rgba(122, 215, 255, 0.55), 0 1px 4px rgba(0, 0, 0, 0.65);
}

.competition-hero-banner__title-stage--final {
  color: #d2b8ff;
  text-shadow: 0 0 18px rgba(210, 184, 255, 0.55), 0 1px 4px rgba(0, 0, 0, 0.65);
}

.competition-hero-banner__capsules {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px 10px;
  margin: 0 0 16px;
}

.competition-hero-banner__capsule {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 2px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1.4;
  border: 1px solid transparent;
  backdrop-filter: blur(6px);
}

.competition-hero-banner__capsule--status-published,
.competition-hero-banner__capsule--status-open {
  color: #d8ffe8;
  background: rgba(22, 163, 74, 0.28);
  border-color: rgba(134, 239, 172, 0.45);
}

.competition-hero-banner__capsule--status-draft {
  color: #1a1a1a;
  background: rgba(255, 255, 255, 0.82);
  border-color: rgba(0, 0, 0, 0.12);
}

.competition-hero-banner__capsule--status-closed {
  color: #ffe4e4;
  background: rgba(185, 28, 28, 0.32);
  border-color: rgba(252, 165, 165, 0.45);
}

.competition-hero-banner__capsule--status-upcoming {
  color: #dbeafe;
  background: rgba(37, 99, 235, 0.28);
  border-color: rgba(147, 197, 253, 0.45);
}

.competition-hero-banner__capsule--status-unknown {
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.22);
}

.competition-hero-banner__capsule--stage-prelim {
  color: #e8f7ff;
  background: rgba(14, 116, 190, 0.42);
  border-color: rgba(125, 211, 252, 0.55);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
}

.competition-hero-banner__capsule--stage-final {
  color: #f3e8ff;
  background: rgba(126, 34, 206, 0.38);
  border-color: rgba(216, 180, 254, 0.5);
}

.competition-hero-banner__capsule--division {
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.28);
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
  letter-spacing: 0.02em;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.7);
}

.competition-hero-banner__slogan-line {
  margin: 0 0 0.55em;
}

.competition-hero-banner__slogan-line:last-child {
  margin-bottom: 0;
}

.competition-hero-banner__kw {
  display: inline;
  padding: 0 2px;
  margin: 0;
  color: #ffe566;
  background: rgba(255, 229, 102, 0.12);
  border-radius: 2px;
  font-weight: 700;
  font-style: normal;
}

.competition-hero-banner__dates {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 4px;
  padding-top: 0;
}

.competition-hero-banner__dates-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #1a0a12;
  background: linear-gradient(180deg, #ffe566 0%, #f5c400 100%);
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.competition-hero-banner__dates-icon {
  font-size: 13px;
}

.competition-hero-banner__dates-range {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.4);
}

.competition-hero-banner__time-hint {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  border: 1px solid transparent;
}

.competition-hero-banner__time-hint--ended {
  color: #ffe4e4;
  background: rgba(185, 28, 28, 0.35);
  border-color: rgba(252, 165, 165, 0.45);
}

.competition-hero-banner__time-hint--urgent {
  color: #fff7ed;
  background: rgba(234, 88, 12, 0.4);
  border-color: rgba(253, 186, 116, 0.55);
}

.competition-hero-banner__time-hint--soon {
  color: #dbeafe;
  background: rgba(37, 99, 235, 0.35);
  border-color: rgba(147, 197, 253, 0.5);
}

.competition-hero-banner__id {
  display: none;
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

.admin-track-block {
  margin-bottom: 16px;
}

.grade-audit-panel {
  margin-top: 16px;
  padding: 16px;
  background: #fff;
  border: 2px solid #1890ff;
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
}

.grade-audit-panel__title {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.grade-audit-panel__track {
  font-weight: 500;
  color: #1890ff;
}

.grade-audit-panel__form {
  max-width: 100%;
}

.admin-track-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.admin-track-bar__title {
  color: rgba(0, 0, 0, 0.85);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
}

.admin-track-bar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.team-join-request-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.team-member-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.team-member-name {
  font-size: 13px;
}
.team-join-request-name {
  min-width: 80px;
  font-weight: 500;
}
.team-school-review-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.team-school-review-status-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.65);
}

.team-school-review-status-hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
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

.division-pick-modal__hint {
  margin-bottom: 20px;
  color: rgba(0, 0, 0, 0.65);
  line-height: 1.6;
}

.division-pick-modal__actions {
  display: flex;
  flex-direction: column;
}

.division-pick-modal__btn-second {
  margin-top: 12px;
}

.competition-hero-banner__division-tag {
  margin-left: 8px;
  vertical-align: middle;
}
</style>

<style lang="less">
/* Modal 挂载在 body，需非 scoped */
.standalone-competition-modal-wrap .ant-modal-body {
  padding-top: 8px;
}

/* 专家评分弹窗：白底可读，层级高于独立详情遮罩 */
.grade-audit-modal-wrap {
  z-index: 3200 !important;

  .ant-modal {
    top: 64px;
    padding-bottom: 24px;
  }

  .ant-modal-content {
    background: #fff;
    border: 1px solid #e8e8e8;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.35);
  }

  .ant-modal-header {
    background: #fff;
    border-bottom: 1px solid #f0f0f0;
  }

  .ant-modal-title {
    color: rgba(0, 0, 0, 0.85);
    font-weight: 600;
  }

  .ant-modal-body {
    background: #fff;
    color: rgba(0, 0, 0, 0.85);
  }

  .ant-modal-close {
    color: rgba(0, 0, 0, 0.45);
  }
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

  /* 固定列（如评分汇总「操作」）默认白底，与弹窗深色底对齐 */
  .ant-table-fixed,
  .ant-table-fixed-left,
  .ant-table-fixed-right,
  .ant-table-fixed-header,
  .ant-table-fixed-body,
  .ant-table-body-outer,
  .ant-table-scroll .ant-table-header,
  .ant-table-fixed-left table,
  .ant-table-fixed-right table {
    background: transparent !important;
  }

  .ant-table-fixed-left .ant-table-thead > tr > th,
  .ant-table-fixed-left .ant-table-tbody > tr > td,
  .ant-table-fixed-right .ant-table-thead > tr > th,
  .ant-table-fixed-right .ant-table-tbody > tr > td,
  .ant-table-fixed .ant-table-thead > tr > th,
  .ant-table-fixed .ant-table-tbody > tr > td {
    background: rgba(14, 10, 30, 0.98) !important;
    color: rgba(255, 255, 255, 0.92) !important;
    border-color: rgba(255, 255, 255, 0.16) !important;
  }

  .ant-table-tbody > tr:hover > td,
  .ant-table-tbody > tr.ant-table-row-hover > td,
  .ant-table-fixed-right .ant-table-tbody > tr:hover > td,
  .ant-table-fixed-left .ant-table-tbody > tr:hover > td {
    background: rgba(255, 255, 255, 0.06) !important;
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

.competition-url-modal__name {
  margin: 0 0 12px;
  font-weight: 600;
}

.competition-url-modal__line + .competition-url-modal__line {
  margin-top: 14px;
}

.competition-url-modal__label {
  margin-bottom: 6px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
}

.competition-url-modal__url-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.competition-url-modal__input {
  flex: 1;
  min-width: 0;
}

.competition-url-link--disabled {
  color: rgba(0, 0, 0, 0.25) !important;
  cursor: not-allowed;
}

.competition-hero-banner__exam-paper-btn {
  margin-left: 8px;
  color: #fff !important;
  background: #1a1843 !important;
  border-color: #1a1843 !important;
}

.competition-hero-banner__exam-paper-btn:hover,
.competition-hero-banner__exam-paper-btn:focus {
  color: #fff !important;
  background: #24225a !important;
  border-color: #24225a !important;
}

.competition-hero-banner__exam-paper-btn:active {
  color: #fff !important;
  background: #100e2e !important;
  border-color: #100e2e !important;
}

.question-answer-file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.question-answer-slots {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-answer-slot {
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.55);
}

.question-answer-slot__title {
  font-weight: 600;
  margin-bottom: 4px;
}

.question-answer-status-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-answer-status-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.division-choice-self-risk {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #d46b08;
}
</style>
