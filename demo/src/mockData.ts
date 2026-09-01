import type { ExperienceCard, IntroVersion } from './types'

export const MOCK_EXPERIENCES: ExperienceCard[] = [
  {
    id: 'exp_001',
    title: 'XX公司 · 产品实习生',
    period: '2024.06 - 2024.09',
    role: '产品实习生',
    summary: '负责用户增长模块的数据分析与需求推进，参与 0-1 功能上线。',
    metrics: 'DAU +12%，需求交付周期缩短 20%',
    tags: ['数据分析', '0-1项目'],
    qaTree: [
      {
        nodeId: 'q1',
        question: '介绍一下这个项目里你负责的部分',
        answerMode: 'user_answered',
        answer: '我主要负责增长模块的核心指标定义和跨部门需求推进，每周输出数据复盘报告。',
        aiFeedback: 'STAR 结构完整，建议补充「为什么选这些指标」的决策过程。',
        labels: ['项目介绍', '行为面试'],
        marks: ['practice'],
        children: [
          {
            nodeId: 'q1.1',
            triggerFrom: '用户提到的「跨部门协调」',
            question: '当时跨部门协调遇到的最大分歧是什么？你怎么解决的？',
            answerMode: 'ai_generated',
            answer:
              '最大分歧是研发排期与业务窗口期冲突。我先对齐共同目标（上线节点），再拆 MVP 范围，最终用数据说明优先级，获得双方认可。',
            aiFeedback: '回答有具体冲突点和解决步骤，可再补充量化结果。',
            labels: ['团队协作', '冲突解决'],
            marks: ['star'],
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: 'exp_002',
    title: '校园数据分析项目',
    period: '2023.09 - 2024.01',
    role: '项目负责人',
    summary: '搭建校园二手交易数据分析看板，支持运营决策。',
    missingHint: '建议补充数据：交易量、用户留存等量化结果',
    tags: ['Python', '可视化'],
    qaTree: [],
  },
  {
    id: 'exp_003',
    title: '某互联网大赛 · 商业策划',
    period: '2023.03',
    role: '队长',
    summary: '带队完成商业计划书与路演，获校级一等奖。',
    metrics: '团队 5 人，3 周完成从 0 到路演',
    tags: ['商业分析', '演讲'],
    qaTree: [],
  },
]

export const MOCK_INTRO_VERSIONS: IntroVersion[] = [
  {
    id: 'v1',
    label: 'AI 初稿',
    createdAt: '2026-08-20',
    content:
      '您好，我是 CHEN，目前专注于产品方向。曾在 XX 公司担任产品实习生，负责增长模块的数据分析与需求推进，期间主导指标体系建设，助力 DAU 提升 12%。我擅长用数据驱动决策，也具备跨部门协作经验。期待加入贵司，继续在产品领域深耕。',
  },
]

export const MOCK_QUESTIONS: Record<string, string[]> = {
  deep_dive: [
    '如果当时选错了核心指标，你会怎么发现并纠正？',
    '这个决策过程中，有没有考虑过但被否决的方案？为什么？',
  ],
  new_angle: [
    '从团队协作角度看，这个项目里你最大的收获是什么？',
    '如果重来一次，你会在哪个环节做得不一样？',
  ],
  diverge: [
    '你刚才提到「数据驱动」，能举一个具体用数据改变决策方向的例子吗？',
    '你提到的跨部门协调，如果对方完全不配合，你会怎么办？',
  ],
}

export const MOCK_AI_INTRO =
  '您好，我是 CHEN，产品方向求职者。我有数据分析与 0-1 项目经验，擅长用指标驱动业务决策，期待与贵司共同成长。'

export const MOCK_FRAMEWORK =
  '【框架提示】\n1. 背景：项目目标是什么\n2. 任务：你的具体职责\n3. 行动：关键步骤 2-3 条\n4. 结果：量化成果'

export const MOCK_FEEDBACK = [
  '结构清晰，建议补充 1 个量化数据支撑结论。',
  '回答偏概括，可加入「我具体做了什么」的细节。',
  'STAR 完整度较好，注意控制回答时长在 2 分钟内。',
]
