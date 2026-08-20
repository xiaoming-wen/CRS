<template>
  <div class="auth-tech-bg" aria-hidden="true">
    <svg
      class="auth-tech-bg__svg"
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="atb-sky" cx="50%" cy="42%" r="70%">
          <stop offset="0%" stop-color="#0a2a6e" />
          <stop offset="45%" stop-color="#04153f" />
          <stop offset="100%" stop-color="#010618" />
        </radialGradient>
        <linearGradient id="atb-floor" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stop-color="#03153a" stop-opacity="0" />
          <stop offset="35%" stop-color="#061a48" stop-opacity="0.85" />
          <stop offset="100%" stop-color="#01040f" />
        </linearGradient>
        <radialGradient id="atb-core-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#4de8ff" stop-opacity="0.85" />
          <stop offset="40%" stop-color="#1a7cff" stop-opacity="0.35" />
          <stop offset="100%" stop-color="#03103a" stop-opacity="0" />
        </radialGradient>
        <linearGradient id="atb-streak-cyan" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#00e5ff" stop-opacity="0" />
          <stop offset="50%" stop-color="#00e5ff" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#00e5ff" stop-opacity="0" />
        </linearGradient>
        <linearGradient id="atb-streak-magenta" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#ff2bd6" stop-opacity="0" />
          <stop offset="50%" stop-color="#ff2bd6" stop-opacity="0.85" />
          <stop offset="100%" stop-color="#ff2bd6" stop-opacity="0" />
        </linearGradient>
        <filter id="atb-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="atb-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="10" />
        </filter>
      </defs>

      <!-- 底色 -->
      <rect width="1600" height="900" fill="url(#atb-sky)" />

      <!-- 上方神经网络节点 -->
      <g class="auth-tech-bg__network" opacity="0.75">
        <line
          v-for="(edge, i) in networkEdges"
          :key="'e' + i"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
          stroke="#5ec8ff"
          stroke-width="0.8"
          opacity="0.35"
        />
        <circle
          v-for="(n, i) in networkNodes"
          :key="'n' + i"
          :cx="n.x"
          :cy="n.y"
          :r="n.r"
          fill="#7adfff"
          :opacity="n.o"
        />
      </g>

      <!-- 散射光斑 -->
      <g filter="url(#atb-soft)" opacity="0.45">
        <circle cx="220" cy="160" r="28" fill="#3aa0ff" />
        <circle cx="1380" cy="200" r="34" fill="#2ecfff" />
        <circle cx="980" cy="90" r="18" fill="#7ef0ff" />
        <circle cx="420" cy="70" r="14" fill="#5ab8ff" />
      </g>

      <!-- 地板透视电路 -->
      <g class="auth-tech-bg__floor">
        <rect x="0" y="480" width="1600" height="420" fill="url(#atb-floor)" />
        <g stroke="#2ea8ff" stroke-opacity="0.28" fill="none">
          <path
            v-for="(p, i) in floorRays"
            :key="'r' + i"
            :d="p"
            :stroke-width="i % 3 === 0 ? 1.6 : 0.9"
          />
        </g>
        <g stroke="#3bcfff" stroke-opacity="0.22" fill="none">
          <path
            v-for="(p, i) in floorHoriz"
            :key="'h' + i"
            :d="p"
            stroke-width="1"
          />
        </g>
        <!-- 芯片前方电路块 -->
        <g opacity="0.55">
          <rect
            v-for="(b, i) in floorBlocks"
            :key="'fb' + i"
            :x="b.x"
            :y="b.y"
            :width="b.w"
            :height="b.h"
            fill="#0a2558"
            stroke="#2ecfff"
            stroke-width="0.6"
            stroke-opacity="0.45"
          />
        </g>
      </g>

      <!-- 左右光轨 -->
      <g class="auth-tech-bg__streaks">
        <rect x="0" y="620" width="280" height="3" fill="url(#atb-streak-magenta)" opacity="0.85" />
        <rect x="0" y="655" width="220" height="2" fill="url(#atb-streak-cyan)" opacity="0.7" />
        <rect x="1320" y="610" width="280" height="3" fill="url(#atb-streak-cyan)" opacity="0.85" />
        <rect x="1380" y="645" width="220" height="2" fill="url(#atb-streak-magenta)" opacity="0.7" />
        <rect x="40" y="700" width="180" height="2" fill="url(#atb-streak-cyan)" opacity="0.45" />
        <rect x="1400" y="690" width="160" height="2" fill="url(#atb-streak-magenta)" opacity="0.5" />
      </g>

      <!-- 中心：芯片 + 大脑 + 大模型元素 -->
      <g class="auth-tech-bg__hero" transform="translate(1020 455) scale(1.48)">
        <ellipse cx="0" cy="20" rx="220" ry="90" fill="url(#atb-core-glow)" opacity="0.9" />

        <!-- Transformer / Attention 环 -->
        <g class="auth-tech-bg__rings" fill="none" filter="url(#atb-glow)">
          <ellipse cx="0" cy="-40" rx="168" ry="118" stroke="#3ad0ff" stroke-width="1.2" opacity="0.28" stroke-dasharray="6 10" />
          <ellipse cx="0" cy="-40" rx="198" ry="138" stroke="#7af7ff" stroke-width="0.9" opacity="0.18" stroke-dasharray="2 14" />
          <ellipse cx="0" cy="-40" rx="138" ry="96" stroke="#ff4de8" stroke-width="1" opacity="0.16" stroke-dasharray="4 12" />
        </g>

        <!-- Token 流粒子 -->
        <g class="auth-tech-bg__tokens" filter="url(#atb-glow)">
          <g v-for="(t, i) in tokenOrbits" :key="'tk' + i" :transform="'rotate(' + t.deg + ')'">
            <rect
              :x="t.r - 14"
              y="-8"
              width="28"
              height="16"
              rx="4"
              fill="#0a2a5c"
              stroke="#5ef0ff"
              stroke-width="0.8"
              :opacity="t.o"
            />
            <text
              :x="t.r"
              y="3"
              text-anchor="middle"
              fill="#9ef8ff"
              font-size="8"
              font-family="Consolas, monospace"
              :opacity="t.o"
            >{{ t.label }}</text>
          </g>
        </g>

        <!-- 大模型概念标签 -->
        <g class="auth-tech-bg__llm-labels" filter="url(#atb-glow)">
          <g v-for="(lab, i) in llmLabels" :key="'lb' + i" :transform="'translate(' + lab.x + ' ' + lab.y + ')'">
            <rect
              :x="-lab.w / 2"
              y="-11"
              :width="lab.w"
              height="22"
              rx="11"
              fill="rgba(6,26,64,0.72)"
              stroke="#3ad0ff"
              stroke-width="1"
              :opacity="lab.o"
            />
            <text
              x="0"
              y="5"
              text-anchor="middle"
              fill="#b8ffff"
              font-size="11"
              font-weight="600"
              font-family="Segoe UI, PingFang SC, sans-serif"
              :opacity="Math.min(1, lab.o + 0.15)"
            >{{ lab.text }}</text>
          </g>
        </g>

        <!-- 注意力连线（示意） -->
        <g stroke="#5ef0ff" stroke-width="0.9" fill="none" opacity="0.35">
          <path d="M-150 -90 Q-40 -130 0 -100" />
          <path d="M150 -90 Q40 -130 0 -100" />
          <path d="M-170 -20 Q-80 -70 0 -55" />
          <path d="M170 -20 Q80 -70 0 -55" />
          <path d="M-120 40 Q-40 -10 0 -20" />
          <path d="M120 40 Q40 -10 0 -20" />
        </g>
        <g fill="#9ef8ff" opacity="0.55">
          <circle cx="-150" cy="-90" r="2.5" />
          <circle cx="150" cy="-90" r="2.5" />
          <circle cx="-170" cy="-20" r="2.2" />
          <circle cx="170" cy="-20" r="2.2" />
          <circle cx="-120" cy="40" r="2" />
          <circle cx="120" cy="40" r="2" />
        </g>

        <!-- 芯片 -->
        <g filter="url(#atb-glow)">
          <rect x="-78" y="18" width="156" height="72" rx="6" fill="#061433" stroke="#3ad0ff" stroke-width="1.4" />
          <rect x="-68" y="28" width="136" height="52" rx="3" fill="#0a1f4a" stroke="#1e6aaa" stroke-width="0.8" />
          <g stroke="#3ad0ff" stroke-width="2" stroke-linecap="round" opacity="0.75">
            <line v-for="i in 7" :key="'pl' + i" :x1="-78" :y1="28 + i * 7" x2="-96" :y2="28 + i * 7" />
            <line v-for="i in 7" :key="'pr' + i" :x1="78" :y1="28 + i * 7" x2="96" :y2="28 + i * 7" />
          </g>
          <g stroke="#4de8ff" stroke-width="1" fill="none" opacity="0.7">
            <path d="M-50 42 H-20 V55 H10" />
            <path d="M20 40 H50 V60 H30" />
            <path d="M-40 60 H0 V48 H40" />
            <circle cx="-20" cy="42" r="2.2" fill="#7ef0ff" />
            <circle cx="10" cy="55" r="2.2" fill="#7ef0ff" />
            <circle cx="50" cy="40" r="2.2" fill="#7ef0ff" />
          </g>
          <text
            x="0"
            y="48"
            text-anchor="middle"
            fill="#8ef6ff"
            font-size="10"
            font-weight="700"
            font-family="Segoe UI, sans-serif"
            opacity="0.7"
          >LLM Core</text>
          <text
            x="0"
            y="62"
            text-anchor="middle"
            fill="#8ef6ff"
            font-size="8"
            font-family="Consolas, monospace"
            opacity="0.35"
          >params · 70B+</text>
        </g>

        <!-- 线框大脑 -->
        <g class="auth-tech-bg__brain" filter="url(#atb-glow)" transform="translate(0 -8)">
          <ellipse cx="0" cy="-52" rx="70" ry="58" fill="none" stroke="#5ef0ff" stroke-width="2.2" opacity="0.95" />
          <path
            d="M-8 -108 C-40 -105 -62 -80 -64 -52 C-66 -20 -48 4 -8 8 C-2 10 4 10 8 8 C48 4 66 -20 64 -52 C62 -80 40 -105 8 -108"
            fill="none"
            stroke="#7af7ff"
            stroke-width="1.6"
            opacity="0.85"
          />
          <path d="M-2 -100 C-28 -90 -38 -70 -36 -48 C-34 -24 -18 -8 -2 -2" fill="none" stroke="#4de8ff" stroke-width="1.3" opacity="0.8" />
          <path d="M2 -100 C28 -90 38 -70 36 -48 C34 -24 18 -8 2 -2" fill="none" stroke="#4de8ff" stroke-width="1.3" opacity="0.8" />
          <path d="M-48 -70 C-30 -62 -12 -58 0 -56 C12 -58 30 -62 48 -70" fill="none" stroke="#2ecfff" stroke-width="1.1" opacity="0.7" />
          <path d="M-52 -40 C-28 -36 -10 -34 0 -34 C10 -34 28 -36 52 -40" fill="none" stroke="#2ecfff" stroke-width="1.1" opacity="0.65" />
          <path d="M-40 -20 C-22 -14 -8 -10 0 -10 C8 -10 22 -14 40 -20" fill="none" stroke="#5ef0ff" stroke-width="1" opacity="0.65" />
          <path d="M0 -108 V8" fill="none" stroke="#7af7ff" stroke-width="1.2" opacity="0.55" />
          <circle cx="-28" cy="-62" r="2.4" fill="#b8ffff" />
          <circle cx="26" cy="-58" r="2.2" fill="#b8ffff" />
          <circle cx="-18" cy="-30" r="2" fill="#9ef8ff" />
          <circle cx="20" cy="-26" r="2" fill="#9ef8ff" />
          <circle cx="0" cy="-48" r="3" fill="#eaffff" opacity="0.9" />
        </g>

        <!-- 大脑下方光环 -->
        <ellipse cx="0" cy="12" rx="100" ry="18" fill="none" stroke="#5ef0ff" stroke-width="1" opacity="0.35" />
        <ellipse cx="0" cy="12" rx="130" ry="26" fill="none" stroke="#2ecfff" stroke-width="0.8" opacity="0.2" />

        <!-- 中心下方：大模型一行说明 -->
        <text
          x="0"
          y="118"
          text-anchor="middle"
          fill="#7adfff"
          font-size="13"
          letter-spacing="3"
          font-family="Segoe UI, PingFang SC, sans-serif"
          opacity="0.55"
        >Large Language Model · Transformer · Attention</text>
      </g>

      <!-- 角落齿轮（简化） -->
      <g class="auth-tech-bg__gears" fill="none" stroke="#3ad0ff" stroke-opacity="0.28">
        <g transform="translate(90 780)">
          <circle cx="0" cy="0" r="42" stroke-width="2" />
          <circle cx="0" cy="0" r="18" stroke-width="1.4" />
          <path
            d="M0 -42 L6 -52 L-6 -52 Z M42 0 L52 6 L52 -6 Z M0 42 L-6 52 L6 52 Z M-42 0 L-52 -6 L-52 6 Z"
            stroke-width="1.2"
          />
        </g>
        <g transform="translate(1380 820)">
          <circle cx="0" cy="0" r="28" stroke-width="1.6" />
          <circle cx="0" cy="0" r="10" stroke-width="1.2" />
        </g>
      </g>

      <!-- 右下 AI 徽章 -->
      <g class="auth-tech-bg__badge" transform="translate(1490 780)" filter="url(#atb-glow)">
        <circle cx="0" cy="0" r="38" fill="none" stroke="#3ad0ff" stroke-width="2" opacity="0.7" />
        <circle cx="0" cy="0" r="30" fill="none" stroke="#5ef0ff" stroke-width="1.2" opacity="0.45" />
        <circle cx="0" cy="0" r="22" fill="#061a40" stroke="#2ecfff" stroke-width="1" opacity="0.9" />
        <text
          x="0"
          y="6"
          text-anchor="middle"
          fill="#7af7ff"
          font-size="18"
          font-weight="700"
          font-family="Segoe UI, PingFang SC, sans-serif"
        >AI</text>
      </g>
    </svg>
  </div>
</template>

<script>
function seeded (seed) {
  let s = seed
  return () => {
    s = (s * 16807 + 7) % 2147483647
    return (s - 1) / 2147483646
  }
}

export default {
  name: 'AuthTechBackground',
  data () {
    const rand = seeded(2026)
    const networkNodes = []
    for (let i = 0; i < 56; i++) {
      networkNodes.push({
        x: 40 + rand() * 1520,
        y: 20 + rand() * 320,
        r: 1.2 + rand() * 2.4,
        o: 0.35 + rand() * 0.55
      })
    }
    const networkEdges = []
    for (let i = 0; i < networkNodes.length; i++) {
      for (let j = i + 1; j < networkNodes.length; j++) {
        const a = networkNodes[i]
        const b = networkNodes[j]
        const dx = a.x - b.x
        const dy = a.y - b.y
        const d = Math.sqrt(dx * dx + dy * dy)
        if (d < 140 && rand() > 0.55) {
          networkEdges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y })
        }
      }
    }

    const vanishX = 800
    const vanishY = 500
    const floorRays = []
    for (let i = -14; i <= 14; i++) {
      const x = 800 + i * 110
      floorRays.push(`M${vanishX} ${vanishY} L${x} 900`)
    }
    const floorHoriz = []
    for (let t = 0.18; t <= 0.95; t += 0.1) {
      const y = vanishY + (900 - vanishY) * t
      const span = 80 + 720 * t
      floorHoriz.push(`M${vanishX - span} ${y} L${vanishX + span} ${y}`)
    }
    const floorBlocks = []
    for (let i = 0; i < 18; i++) {
      const side = i % 2 === 0 ? -1 : 1
      const depth = 0.35 + (i % 6) * 0.08
      const y = vanishY + (900 - vanishY) * depth
      const span = 100 + 600 * depth
      floorBlocks.push({
        x: vanishX + side * (span * (0.35 + (i % 4) * 0.12)) - 28,
        y: y - 6,
        w: 36 + (i % 3) * 12,
        h: 10 + (i % 2) * 6
      })
    }

    const tokenLabels = ['TOK', 'Q', 'K', 'V', 'emb', 'FFN', 'softmax', 'ctx']
    const tokenOrbits = tokenLabels.map((label, i) => ({
      label,
      deg: (360 / tokenLabels.length) * i - 18,
      r: 118 + (i % 3) * 16,
      o: 0.45 + (i % 4) * 0.1
    }))

    const llmLabels = [
      { text: 'Transformer', x: -210, y: -150, w: 108, o: 0.72 },
      { text: 'Attention', x: 210, y: -145, w: 96, o: 0.7 },
      { text: 'Embedding', x: -230, y: -35, w: 102, o: 0.65 },
      { text: 'Inference', x: 235, y: -30, w: 96, o: 0.65 },
      { text: 'Prompt', x: -195, y: 70, w: 82, o: 0.6 },
      { text: 'Generation', x: 205, y: 75, w: 102, o: 0.62 },
      { text: 'LLM', x: 0, y: -165, w: 58, o: 0.8 }
    ]

    return {
      networkNodes,
      networkEdges,
      floorRays,
      floorHoriz,
      floorBlocks,
      tokenOrbits,
      llmLabels
    }
  }
}
</script>

<style scoped lang="less">
.auth-tech-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background: #010618;
  width: 100%;
  height: 100%;
}

.auth-tech-bg__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.auth-tech-bg__brain {
  animation: atb-pulse 4.5s ease-in-out infinite;
}

.auth-tech-bg__rings {
  animation: atb-spin 28s linear infinite;
  transform-origin: 0px -40px;
  transform-box: fill-box;
}

.auth-tech-bg__tokens {
  animation: atb-spin 18s linear infinite;
  transform-origin: 0 0;
}

.auth-tech-bg__llm-labels {
  animation: atb-pulse 5.5s ease-in-out infinite;
}

.auth-tech-bg__streaks rect:nth-child(odd) {
  animation: atb-streak 3.2s ease-in-out infinite;
}

.auth-tech-bg__streaks rect:nth-child(even) {
  animation: atb-streak 3.8s ease-in-out infinite reverse;
}

@keyframes atb-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes atb-pulse {
  0%,
  100% {
    opacity: 0.88;
  }
  50% {
    opacity: 1;
  }
}

@keyframes atb-streak {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}
</style>
