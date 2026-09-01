import type { PageId } from './types'

const NAV_ITEMS: { id: PageId; label: string }[] = [
  { id: 'experience', label: '我的经历库' },
  { id: 'intro', label: '自我介绍' },
  { id: 'interview', label: '模拟面试' },
  { id: 'notebook', label: '面试笔记本' },
  { id: 'settings', label: '岗位定制 (P2)' },
]

interface Props {
  current: PageId
  onNavigate: (page: PageId) => void
}

export function Sidebar({ current, onNavigate }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">简历面试助手</div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={current === item.id ? 'active' : ''}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  )
}
