export function SettingsPage() {
  return (
    <div>
      <h1 className="page-title">岗位定制 (P2)</h1>
      <div className="card">
        <div className="settings-field">
          <label>目标岗位 JD</label>
          <textarea placeholder="粘贴岗位描述，AI 将据此调整追问风格…" style={{ minHeight: 160 }} />
        </div>
        <div className="settings-field">
          <label>追问风格偏好</label>
          <div>
            <label style={{ fontWeight: 400, marginRight: 16 }}>
              <input type="radio" name="style" defaultChecked /> 均衡
            </label>
            <label style={{ fontWeight: 400, marginRight: 16 }}>
              <input type="radio" name="style" /> 技术深度
            </label>
            <label style={{ fontWeight: 400 }}>
              <input type="radio" name="style" /> 行为面试
            </label>
          </div>
        </div>
        <button className="btn btn-primary">保存设置</button>
        <p style={{ marginTop: 12, color: '#888', fontSize: 13 }}>Demo 阶段此功能仅占位，不影响主流程。</p>
      </div>
    </div>
  )
}
