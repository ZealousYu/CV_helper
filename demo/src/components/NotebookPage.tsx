import { useState } from 'react'
import type { ExperienceCard, QANode } from '../types'

interface Props {
  experiences: ExperienceCard[]
  introContent: string
}

function collectAllLabels(nodes: QANode[]): string[] {
  return nodes.flatMap((n) => [...n.labels, ...collectAllLabels(n.children)])
}

function renderQATree(nodes: QANode[], depth = 0, search: string, tagFilter: string[]) {
  return nodes.flatMap((node) => {
    const matchSearch =
      !search ||
      node.question.includes(search) ||
      (node.answer?.includes(search) ?? false)
    const matchTag =
      tagFilter.length === 0 ||
      node.labels.some((l) => tagFilter.includes(l)) ||
      (tagFilter.includes('待练习') && node.marks.includes('practice'))

    const items = []
    if (matchSearch && matchTag) {
      items.push(
        <div key={node.nodeId} className={`notebook-qa depth-${Math.min(depth, 2)}`}>
          <strong>{node.nodeId}</strong> {node.question}
          {node.answer && (
            <div style={{ color: '#555', marginTop: 4, fontSize: 12 }}>
              答：{node.answer.slice(0, 80)}
              {node.answer.length > 80 ? '…' : ''}
            </div>
          )}
          <div style={{ marginTop: 4 }}>
            {node.labels.map((l) => (
              <span key={l} className="tag">
                {l}
              </span>
            ))}
            {node.marks.includes('star') && <span className="tag">⭐重点</span>}
            {node.marks.includes('practice') && <span className="tag">✍️待练习</span>}
          </div>
        </div>,
      )
    }
    items.push(...renderQATree(node.children, depth + 1, search, tagFilter))
    return items
  })
}

interface ReviewItem {
  expTitle: string
  node: QANode
  newAnswer: string
}

export function NotebookPage({ experiences, introContent }: Props) {
  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState<string[]>([])
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([])

  const allTags = Array.from(
    new Set(experiences.flatMap((e) => collectAllLabels(e.qaTree))),
  )

  const openReview = () => {
    const items: ReviewItem[] = []
    for (const exp of experiences) {
      const walk = (nodes: QANode[]) => {
        for (const n of nodes) {
          if (n.marks.includes('practice')) {
            items.push({ expTitle: exp.title, node: n, newAnswer: '' })
          }
          walk(n.children)
        }
      }
      walk(exp.qaTree)
    }
    setReviewItems(items)
    setReviewOpen(true)
  }

  const exportData = (format: string) => {
    alert(`Demo：已模拟导出为 ${format} 格式（实际开发时生成文件）`)
  }

  return (
    <div>
      <h1 className="page-title">面试笔记本</h1>

      <div className="notebook-toolbar">
        <input
          type="text"
          placeholder="搜索关键词…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          multiple
          value={tagFilter}
          onChange={(e) =>
            setTagFilter(Array.from(e.target.selectedOptions, (o) => o.value))
          }
          style={{ minWidth: 160, padding: 8 }}
        >
          {allTags.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
          <option value="待练习">✍️ 待练习</option>
        </select>
      </div>

      {introContent && (
        <details className="card notebook-group" open>
          <summary>【自我介绍】定稿</summary>
          <p style={{ padding: '12px 0', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{introContent}</p>
        </details>
      )}

      {experiences.map((exp) => {
        const qaItems = renderQATree(exp.qaTree, 0, search, tagFilter)
        if (qaItems.length === 0 && exp.qaTree.length > 0) return null
        return (
          <details key={exp.id} className="card notebook-group" open={exp.qaTree.length > 0}>
            <summary>
              {exp.title}
              <span style={{ color: '#888', fontWeight: 400, marginLeft: 8 }}>
                ({exp.qaTree.length} 个根节点)
              </span>
            </summary>
            {qaItems.length === 0 ? (
              <p style={{ padding: 12, color: '#888' }}>暂无问答记录</p>
            ) : (
              qaItems
            )}
          </details>
        )
      })}

      <div className="notebook-actions">
        <button className="btn" onClick={() => exportData('Word')}>
          导出 Word
        </button>
        <button className="btn" onClick={() => exportData('PDF')}>
          导出 PDF
        </button>
        <button className="btn btn-primary" onClick={openReview}>
          进入复习模式
        </button>
      </div>

      {reviewOpen && (
        <div className="modal-backdrop" onClick={() => setReviewOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>复习模式 · 待练习题目</h3>
            {reviewItems.length === 0 ? (
              <p style={{ color: '#888' }}>暂无标记「待练习」的题目。在模拟面试右栏可标记。</p>
            ) : (
              reviewItems.map((item, i) => (
                <div key={item.node.nodeId + i} className="review-item">
                  <div style={{ fontSize: 12, color: '#888' }}>{item.expTitle}</div>
                  <strong>{item.node.question}</strong>
                  <div className="original">原答案：{item.node.answer ?? '（无）'}</div>
                  <textarea
                    placeholder="重新回答（不会重新 AI 提问）…"
                    value={item.newAnswer}
                    onChange={(e) => {
                      const next = [...reviewItems]
                      next[i] = { ...item, newAnswer: e.target.value }
                      setReviewItems(next)
                    }}
                    style={{ minHeight: 60 }}
                  />
                </div>
              ))
            )}
            <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => setReviewOpen(false)}>
              完成复习
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
