import { useState } from 'react'
import type { IntroVersion } from '../types'
import { MOCK_AI_INTRO } from '../mockData'

interface Props {
  content: string
  versions: IntroVersion[]
  onChange: (content: string) => void
  onSaveVersion: (label: string) => void
  onLoadVersion: (id: string) => void
}

type OverlayMode = 'generate' | 'polish' | 'guide' | null

export function IntroPage({ content, versions, onChange, onSaveVersion, onLoadVersion }: Props) {
  const [overlay, setOverlay] = useState<OverlayMode>(null)
  const [overlayStep, setOverlayStep] = useState(0)
  const [overlayInput, setOverlayInput] = useState('')

  const guideQuestions = [
    '你最想突出的 1 个能力是什么？',
    '哪段经历最能体现你和别人的不同？',
    '你期望的目标岗位是什么方向？',
  ]

  const openOverlay = (mode: OverlayMode) => {
    setOverlay(mode)
    setOverlayStep(0)
    setOverlayInput('')
  }

  const finishOverlay = (result: string) => {
    onChange(result)
    setOverlay(null)
  }

  const handleOverlayAction = () => {
    if (overlay === 'generate') {
      finishOverlay(MOCK_AI_INTRO)
    } else if (overlay === 'polish') {
      finishOverlay(content + '\n\n（AI 润色：表达更简洁，突出数据成果）')
    } else if (overlay === 'guide') {
      if (overlayStep < guideQuestions.length - 1) {
        setOverlayStep((s) => s + 1)
        setOverlayInput('')
      } else {
        finishOverlay(
          `您好，我是 CHEN。${overlayInput}\n\n基于您的回答，我帮您组织如下：我具备${overlayInput.slice(0, 20)}…（AI 组织稿）`,
        )
      }
    }
  }

  return (
    <div>
      <h1 className="page-title">自我介绍打磨</h1>

      <div className="intro-actions">
        <button className="btn btn-primary" onClick={() => openOverlay('generate')}>
          AI 生成初稿
        </button>
        <button className="btn" onClick={() => openOverlay('polish')}>
          我自己写，AI 润色
        </button>
        <button className="btn" onClick={() => openOverlay('guide')}>
          AI 引导提问再帮我组织
        </button>
      </div>

      <div className="card">
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>编辑区</label>
        <textarea value={content} onChange={(e) => onChange(e.target.value)} placeholder="在此编辑自我介绍…" />
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-primary" onClick={() => onSaveVersion('定稿')}>
            保存定稿
          </button>
        </div>
      </div>

      <div className="version-list">
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>已保存版本（最多 3 版）</h3>
        {versions.length === 0 && <p style={{ color: '#888' }}>暂无保存版本</p>}
        {versions.map((v) => (
          <div key={v.id} className="version-item" onClick={() => onLoadVersion(v.id)}>
            <span>
              {v.label} · {v.createdAt}
            </span>
            <span style={{ color: '#888', fontSize: 12 }}>点击切换</span>
          </div>
        ))}
      </div>

      {overlay && (
        <div className="overlay" onClick={() => setOverlay(null)}>
          <div className="overlay-panel" onClick={(e) => e.stopPropagation()}>
            <h3>
              {overlay === 'generate' && 'AI 生成初稿'}
              {overlay === 'polish' && 'AI 润色'}
              {overlay === 'guide' && 'AI 引导提问'}
            </h3>
            <div className="overlay-messages">
              {overlay === 'generate' && (
                <div className="msg msg-ai">正在根据您的经历库生成 1 分钟自我介绍初稿…</div>
              )}
              {overlay === 'polish' && (
                <>
                  <div className="msg msg-user">请帮我润色当前文稿，突出产品能力与数据成果。</div>
                  <div className="msg msg-ai">好的，我会保留您的核心经历，优化表达节奏与亮点排序。</div>
                </>
              )}
              {overlay === 'guide' && (
                <>
                  <div className="msg msg-ai">{guideQuestions[overlayStep]}</div>
                  {overlayStep > 0 && overlayInput && (
                    <div className="msg msg-user">{overlayInput}</div>
                  )}
                </>
              )}
            </div>
            {overlay === 'guide' && (
              <textarea
                value={overlayInput}
                onChange={(e) => setOverlayInput(e.target.value)}
                placeholder="输入您的回答…"
                style={{ minHeight: 60, marginBottom: 12 }}
              />
            )}
            <button className="btn btn-primary" onClick={handleOverlayAction}>
              {overlay === 'guide' && overlayStep < guideQuestions.length - 1 ? '下一题' : '完成并填入编辑区'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
