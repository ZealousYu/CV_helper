import { useState, useEffect } from 'react'
import type { ExperienceCard, QANode, AnswerMode, NextStepAction, InterviewPhase } from '../types'
import { ANSWER_MODE_LABEL, NEXT_STEP_OPTIONS } from '../types'
import { MOCK_QUESTIONS, MOCK_FRAMEWORK, MOCK_FEEDBACK } from '../mockData'
import { findNode, addChildNode, updateNode, generateNodeId } from '../treeUtils'

interface Props {
  experiences: ExperienceCard[]
  initialExpId?: string | null
  onUpdateExperience: (exp: ExperienceCard) => void
  onGoNotebook: () => void
}

function TreeView({
  tree,
  activeNodeId,
  onSelectNode,
}: {
  tree: QANode[]
  activeNodeId: string | null
  onSelectNode: (nodeId: string) => void
}) {
  const renderNode = (node: QANode, depth = 0) => (
    <div key={node.nodeId} style={{ marginLeft: depth * 16 }}>
      <div
        className={`tree-node ${activeNodeId === node.nodeId ? 'active' : ''}`}
        onClick={() => onSelectNode(node.nodeId)}
        title="点击跳转到该节点，可从此处分支"
      >
        <span className="tree-node-id">{node.nodeId}</span>
        {node.question.slice(0, 40)}
        {node.question.length > 40 ? '…' : ''}
        {node.answer && <span className="status-badge">已答</span>}
      </div>
      {node.children.map((c) => renderNode(c, depth + 1))}
    </div>
  )

  return <div>{tree.map((n) => renderNode(n))}</div>
}

export function InterviewPage({
  experiences,
  initialExpId,
  onUpdateExperience,
  onGoNotebook,
}: Props) {
  const [expId, setExpId] = useState(initialExpId ?? experiences[0]?.id ?? '')
  const experience = experiences.find((e) => e.id === expId)!

  const [phase, setPhase] = useState<InterviewPhase>('idle')
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [draftAnswer, setDraftAnswer] = useState('')
  const [selectedMode, setSelectedMode] = useState<AnswerMode | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [branchFromNodeId, setBranchFromNodeId] = useState<string | null>(null)

  useEffect(() => {
    if (initialExpId) setExpId(initialExpId)
  }, [initialExpId])

  const activeNode = activeNodeId ? findNode(experience.qaTree, activeNodeId) : null

  const updateTree = (newTree: QANode[]) => {
    onUpdateExperience({ ...experience, qaTree: newTree })
  }

  const startInterview = () => {
    if (experience.qaTree.length === 0) {
      const newNode: QANode = {
        nodeId: 'q1',
        question: '介绍一下这个项目里你负责的部分，以及最终取得了什么成果？',
        labels: ['项目介绍'],
        marks: [],
        children: [],
      }
      updateTree([newNode])
      setActiveNodeId('q1')
      setCurrentQuestion(newNode.question)
      setPhase('question')
      setBranchFromNodeId(null)
    } else {
      const first = experience.qaTree[0]
      setActiveNodeId(first.nodeId)
      setCurrentQuestion(first.question)
      setPhase(first.answer ? 'feedback' : 'question')
      setShowFeedback(!!first.answer)
      setDraftAnswer(first.answer ?? '')
    }
  }

  const selectNode = (nodeId: string) => {
    const node = findNode(experience.qaTree, nodeId)
    if (!node) return
    setActiveNodeId(nodeId)
    setCurrentQuestion(node.question)
    setDraftAnswer(node.answer ?? '')
    setBranchFromNodeId(nodeId)
    if (node.answer) {
      setPhase('feedback')
      setShowFeedback(true)
    } else {
      setPhase('question')
      setShowFeedback(false)
    }
    setSelectedMode(node.answerMode ?? null)
  }

  const selectAnswerMode = (mode: AnswerMode) => {
    setSelectedMode(mode)
    setPhase('answering')
    if (mode === 'ai_generated') {
      setDraftAnswer(
        '（AI 参考答案）我在项目中负责核心指标定义与跨部门推进。通过建立周度数据复盘机制，将需求交付周期缩短 20%，DAU 提升 12%。',
      )
    } else if (mode === 'framework_only') {
      setDraftAnswer(MOCK_FRAMEWORK + '\n\n（请在此填写您的回答）')
    } else {
      setDraftAnswer('')
    }
  }

  const submitAnswer = () => {
    if (!activeNodeId) return
    const feedback = MOCK_FEEDBACK[Math.floor(Math.random() * MOCK_FEEDBACK.length)]
    const updated = updateNode(experience.qaTree, activeNodeId, {
      answerMode: selectedMode ?? 'user_answered',
      answer: draftAnswer,
      aiFeedback: feedback,
    })
    updateTree(updated)
    setPhase('feedback')
    setShowFeedback(true)
    setBranchFromNodeId(activeNodeId)
  }

  const handleNextStep = (action: NextStepAction) => {
    if (action === 'end') {
      setPhase('idle')
      setActiveNodeId(null)
      return
    }
    if (action === 'switch_exp') {
      const others = experiences.filter((e) => e.id !== expId)
      if (others.length) {
        setExpId(others[0].id)
        setPhase('idle')
        setActiveNodeId(null)
      }
      return
    }

    const parentId = branchFromNodeId ?? activeNodeId
    if (!parentId) return

    const parent = findNode(experience.qaTree, parentId)
    const questions = MOCK_QUESTIONS[action] ?? MOCK_QUESTIONS.deep_dive
    const q = questions[Math.floor(Math.random() * questions.length)]

    const newNode: QANode = {
      nodeId: generateNodeId(parentId, parent?.children ?? []),
      question: q,
      triggerFrom: action === 'diverge' ? '从上一轮回答中识别到的关键词' : undefined,
      labels: action === 'deep_dive' ? ['深挖', '压力面试'] : ['行为面试'],
      marks: [],
      children: [],
    }

    const updated = addChildNode(experience.qaTree, parentId, newNode)
    updateTree(updated)
    setActiveNodeId(newNode.nodeId)
    setCurrentQuestion(newNode.question)
    setDraftAnswer('')
    setSelectedMode(null)
    setPhase('question')
    setShowFeedback(false)
    setBranchFromNodeId(parentId)
  }

  const toggleMark = (mark: 'star' | 'practice') => {
    if (!activeNodeId || !activeNode) return
    const marks = activeNode.marks.includes(mark)
      ? activeNode.marks.filter((m) => m !== mark)
      : [...activeNode.marks, mark]
    updateTree(updateNode(experience.qaTree, activeNodeId, { marks }))
  }

  const phaseLabel: Record<InterviewPhase, string> = {
    idle: '初始',
    question: '等待作答',
    answering: '作答中',
    feedback: '可追问',
    next_step: '选择下一步',
  }

  return (
    <div>
      <h1 className="page-title">
        模拟面试
        <span className="status-badge">状态: {phaseLabel[phase]}</span>
      </h1>

      <div className="interview-layout">
        <div className="interview-left">
          <div className="interview-header">
            <select value={expId} onChange={(e) => { setExpId(e.target.value); setPhase('idle'); setActiveNodeId(null) }}>
              {experiences.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.title}
                </option>
              ))}
            </select>
            {phase === 'idle' && (
              <button className="btn btn-primary" onClick={startInterview}>
                开始提问
              </button>
            )}
          </div>

          {phase === 'idle' ? (
            <div className="empty-state">
              <p>AI 准备就绪</p>
              <p>选择经历卡片后，点击「开始提问」</p>
            </div>
          ) : (
            <>
              <div className="question-display">{currentQuestion}</div>
              {activeNode?.triggerFrom && (
                <p className="phase-hint">🔗 触发点：{activeNode.triggerFrom}</p>
              )}

              <div className={`answer-modes ${phase !== 'question' ? 'disabled' : ''}`}>
                <button className={`btn ${selectedMode === 'user_answered' ? 'btn-active' : ''}`} onClick={() => selectAnswerMode('user_answered')}>
                  自己答
                </button>
                <button className={`btn ${selectedMode === 'ai_generated' ? 'btn-active' : ''}`} onClick={() => selectAnswerMode('ai_generated')}>
                  AI 代答
                </button>
                <button className={`btn ${selectedMode === 'framework_only' ? 'btn-active' : ''}`} onClick={() => selectAnswerMode('framework_only')}>
                  看框架再自己填
                </button>
              </div>

              {(phase === 'answering' || (phase === 'feedback' && draftAnswer)) && (
                <>
                  <textarea
                    value={draftAnswer}
                    onChange={(e) => setDraftAnswer(e.target.value)}
                    placeholder="输入您的回答…"
                    disabled={phase === 'feedback'}
                  />
                  {phase === 'answering' && (
                    <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={submitAnswer}>
                      提交回答
                    </button>
                  )}
                </>
              )}

              {phase === 'feedback' && activeNode?.aiFeedback && (
                <details className="feedback-section" open={showFeedback}>
                  <summary>AI 点评 {activeNode.answerMode && `(${ANSWER_MODE_LABEL[activeNode.answerMode]})`}</summary>
                  <p style={{ marginTop: 8 }}>{activeNode.aiFeedback}</p>
                </details>
              )}

              {phase === 'feedback' && (
                <div className="next-steps">
                  <h4>下一步选择（将从当前节点 {branchFromNodeId ?? activeNodeId} 分支）</h4>
                  {NEXT_STEP_OPTIONS.map((opt) => (
                    <button key={opt.id} className="btn" onClick={() => handleNextStep(opt.id)}>
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="interview-right">
          <div className="tree-panel">
            <h4>追问树（点击节点可跳转 & 分支）</h4>
            {experience.qaTree.length === 0 ? (
              <p style={{ color: '#888', fontSize: 13 }}>开始面试后，问答将在此展开</p>
            ) : (
              <TreeView tree={experience.qaTree} activeNodeId={activeNodeId} onSelectNode={selectNode} />
            )}
          </div>

          {activeNode && (
            <>
              <div className="node-tags">
                <strong style={{ fontSize: 13 }}>标签：</strong>
                {activeNode.labels.map((l) => (
                  <span key={l} className="tag">
                    {l}
                  </span>
                ))}
              </div>
              <div className="node-marks">
                <button
                  className={`btn btn-sm ${activeNode.marks.includes('star') ? 'btn-active' : ''}`}
                  onClick={() => toggleMark('star')}
                >
                  ⭐ 重点
                </button>
                <button
                  className={`btn btn-sm ${activeNode.marks.includes('practice') ? 'btn-active' : ''}`}
                  onClick={() => toggleMark('practice')}
                >
                  ✍️ 待练习
                </button>
              </div>
            </>
          )}

          <div style={{ marginTop: 16 }}>
            <button className="btn btn-sm" onClick={onGoNotebook}>
              查看全部笔记 →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
