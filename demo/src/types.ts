export type AnswerMode = 'user_answered' | 'ai_generated' | 'framework_only'

export type PageId = 'experience' | 'intro' | 'interview' | 'notebook' | 'settings'

export interface QANode {
  nodeId: string
  question: string
  answerMode?: AnswerMode
  answer?: string
  aiFeedback?: string
  labels: string[]
  marks: ('star' | 'practice')[]
  triggerFrom?: string
  children: QANode[]
}

export interface ExperienceCard {
  id: string
  title: string
  period: string
  role: string
  summary: string
  metrics?: string
  missingHint?: string
  tags: string[]
  qaTree: QANode[]
}

export interface IntroVersion {
  id: string
  content: string
  createdAt: string
  label: string
}

export type InterviewPhase = 'idle' | 'question' | 'answering' | 'feedback' | 'next_step'

export type NextStepAction = 'deep_dive' | 'new_angle' | 'diverge' | 'switch_exp' | 'end'

export interface AppState {
  experiences: ExperienceCard[]
  introVersions: IntroVersion[]
  currentIntro: string
  activeExperienceId: string | null
  activeNodeId: string | null
}

export const ANSWER_MODE_LABEL: Record<AnswerMode, string> = {
  user_answered: '自己回答',
  ai_generated: 'AI代答',
  framework_only: '框架引导',
}

export const NEXT_STEP_OPTIONS: { id: NextStepAction; label: string }[] = [
  { id: 'deep_dive', label: '深挖当前问题' },
  { id: 'new_angle', label: '换角度问同项目' },
  { id: 'diverge', label: '发散追问' },
  { id: 'switch_exp', label: '换经历' },
  { id: 'end', label: '结束本轮' },
]
