# MVP API 与数据模型

> 对应搭建步骤 1～2。首版只覆盖「能真练一轮并存下来」。

---

## 技术选型（务实版）

| 层 | 选型 | 原因 |
|----|------|------|
| 后端 | FastAPI | 异步友好、自带 OpenAPI 文档、Python 生态接大模型方便 |
| 数据库 | SQLite | 零运维，单机开发够用；表结构可迁到 Postgres |
| LLM | Provider 抽象 | 默认 Mock；配置 `LLM_API_KEY` 后走 OpenAI 兼容接口 |
| 前端 | 暂用 Demo / 静态联调 | 本机暂无 Node；不阻塞验 AI 质量 |
| 鉴权 | 暂无（单用户本地） | MVP 先跑通；上线再加登录 |

---

## MVP 范围（做 / 不做）

**做**
- 经历 CRUD
- 模拟面试：开局提问、作答、点评、下一步追问、树持久化
- 知识汇总：从节点加入 / 列表 / 简单更新
- 节点标记：重点 / 待练习

**暂不做**
- 简历 PDF 解析、自我介绍打磨、随机抽查精修、JD 深度报告、导出 Word

---

## 核心数据实体

### Experience（经历）
- id, type, company, title, role, period, summary, metrics, extra, tags(JSON), created_at

### QANode（追问树节点，按经历挂树）
- 存在 Experience.qa_tree(JSON) 里（MVP 用整树 JSON，避免过早拆表）
- 字段对齐产品方案：nodeId, question, answerMode, answer, aiFeedback, labels, knowledgeTags, marks, triggerFrom, children[]

### KnowledgeItem（知识汇总）
- id, source_exp_id, source_node_id, question, my_answer, reference_answer, tags(JSON), note, status, created_at

### InterviewSession（可选，MVP 可内嵌在经历树状态）
- 首版：前端/接口直接基于经历树操作，不单独建会话表；后续多轮并发再拆。

---

## API 清单（首版）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/experiences` | 经历列表 |
| POST | `/api/experiences` | 新建经历 |
| GET | `/api/experiences/{id}` | 经历详情（含树） |
| PUT | `/api/experiences/{id}` | 更新经历 |
| DELETE | `/api/experiences/{id}` | 删除经历 |
| POST | `/api/interview/{exp_id}/start` | 开始/恢复提问（返回当前题） |
| POST | `/api/interview/{exp_id}/answer` | 提交回答 → 点评 + 打标签 |
| POST | `/api/interview/{exp_id}/next` | 下一步（深挖/换角度/发散…）→ 新节点 |
| PATCH | `/api/interview/{exp_id}/nodes/{node_id}/marks` | 更新 ⭐ / 待练习 |
| GET | `/api/knowledge` | 知识列表（可按 tag 筛） |
| POST | `/api/knowledge` | 加入知识汇总 |
| PUT | `/api/knowledge/{id}` | 更新条目 |
| GET | `/api/debriefs` | 真实面经列表 |
| POST | `/api/debriefs` | 新建（粘贴转写文本） |
| POST | `/api/debriefs/{id}/extract` | AI 提取关键问答 |
| POST | `/api/debriefs/{id}/analyze` | AI 分析（弱答标红 + 优化答） |

交互文档：启动后端后打开 `http://127.0.0.1:8000/docs`

---

## LLM 调用约定

会调模型的地方（其余 CRUD/标记不调，控成本）：

1. `interview/answer` → 点评 + knowledgeTags  
2. `interview/next` → 下一问（可带 triggerFrom）  
3. `interview/start` 且树为空 → 第一问  
4. `debriefs/extract` → 从转写提取问答对  
5. `debriefs/analyze` → 判断强弱答 + 优化回答  

未配置 Key 时以上均走 Mock。

### Debrief（真实面经）条目结构

```json
{
  "id": "di_1",
  "question": "...",
  "answer": "...",
  "quality": "pending|weak|good",
  "analysis": "弱答原因…",
  "optimized_answer": "优化答法…",
  "tags": ["行为面试", "…"]
}
```
