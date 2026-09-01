import { useState } from 'react'
import type { PageId, ExperienceCard, IntroVersion } from './types'
import { MOCK_EXPERIENCES, MOCK_INTRO_VERSIONS } from './mockData'
import { Sidebar } from './components/Sidebar'
import { ExperiencePage } from './components/ExperiencePage'
import { IntroPage } from './components/IntroPage'
import { InterviewPage } from './components/InterviewPage'
import { NotebookPage } from './components/NotebookPage'
import { SettingsPage } from './components/SettingsPage'

export default function App() {
  const [page, setPage] = useState<PageId>('experience')
  const [experiences, setExperiences] = useState<ExperienceCard[]>(MOCK_EXPERIENCES)
  const [introVersions, setIntroVersions] = useState<IntroVersion[]>(MOCK_INTRO_VERSIONS)
  const [introContent, setIntroContent] = useState(MOCK_INTRO_VERSIONS[0]?.content ?? '')
  const [interviewExpId, setInterviewExpId] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  const handleUpload = () => {
    showToast('模拟解析完成：已加载 3 段经历卡片')
  }

  const handleSaveIntro = (label: string) => {
    if (introVersions.length >= 3) {
      showToast('最多保留 3 个版本，请先删除旧版本（Demo 暂未实现删除）')
      return
    }
    const v: IntroVersion = {
      id: `v${Date.now()}`,
      label,
      createdAt: new Date().toISOString().slice(0, 10),
      content: introContent,
    }
    setIntroVersions((prev) => [v, ...prev].slice(0, 3))
    showToast('定稿已保存')
  }

  const handleUpdateExperience = (exp: ExperienceCard) => {
    setExperiences((prev) => prev.map((e) => (e.id === exp.id ? exp : e)))
  }

  const startInterview = (expId: string) => {
    setInterviewExpId(expId)
    setPage('interview')
  }

  return (
    <div className="app-shell">
      <Sidebar current={page} onNavigate={setPage} />
      <main className="main-content">
        {page === 'experience' && (
          <ExperiencePage experiences={experiences} onUpload={handleUpload} onStartInterview={startInterview} />
        )}
        {page === 'intro' && (
          <IntroPage
            content={introContent}
            versions={introVersions}
            onChange={setIntroContent}
            onSaveVersion={handleSaveIntro}
            onLoadVersion={(id) => {
              const v = introVersions.find((x) => x.id === id)
              if (v) setIntroContent(v.content)
            }}
          />
        )}
        {page === 'interview' && (
          <InterviewPage
            experiences={experiences}
            initialExpId={interviewExpId}
            onUpdateExperience={handleUpdateExperience}
            onGoNotebook={() => setPage('notebook')}
          />
        )}
        {page === 'notebook' && <NotebookPage experiences={experiences} introContent={introContent} />}
        {page === 'settings' && <SettingsPage />}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
