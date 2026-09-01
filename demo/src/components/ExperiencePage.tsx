import type { ExperienceCard } from '../types'

interface Props {
  experiences: ExperienceCard[]
  onUpload: () => void
  onStartInterview: (expId: string) => void
}

export function ExperiencePage({ experiences, onUpload, onStartInterview }: Props) {
  return (
    <div>
      <h1 className="page-title">经历录入</h1>
      <div className="upload-zone" onClick={onUpload}>
        拖拽或点击上传 PDF / Word，或直接粘贴文本
        <br />
        <small>（Demo：点击模拟解析完成）</small>
      </div>

      {experiences.length === 0 ? (
        <div className="empty-state">
          <p>暂无经历卡片</p>
          <p>上传简历后将自动拆解为结构化经历</p>
        </div>
      ) : (
        experiences.map((exp) => (
          <div key={exp.id} className="card exp-card">
            <div className="exp-card-header">
              <div>
                <div className="exp-card-title">{exp.title}</div>
                <div className="exp-card-meta">
                  {exp.period} · {exp.role}
                </div>
              </div>
              <button className="btn btn-primary btn-sm" onClick={() => onStartInterview(exp.id)}>
                进入模拟面试
              </button>
            </div>
            <div className="exp-card-summary">{exp.summary}</div>
            {exp.metrics && <div className="exp-card-metrics">📊 {exp.metrics}</div>}
            {exp.missingHint && <div className="exp-card-hint">⚠ {exp.missingHint}</div>}
            <div style={{ marginTop: 8 }}>
              {exp.tags.map((t) => (
                <span key={t} className="tag">
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
