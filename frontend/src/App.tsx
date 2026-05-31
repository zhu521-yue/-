import React, { useState, useRef, useEffect } from 'react'

const API_BASE = '/api/v1'

interface QuestionData {
  id: string
  knowledge_id: string
  type: 'choice' | 'fill' | 'open'
  difficulty: number
  stem: string
  options?: Record<string, string>
}

interface SubmitResult {
  is_correct: boolean
  score: number
  feedback: string
  mastery: number
  mastery_level: string
  level_changed: boolean
  session_state: string
  engagement_state: string
  report: string
}

const KNOWLEDGE_OPTIONS = [
  { id: 'arithmetic', name: '🔢 四则运算', emoji: '🧮' },
  { id: 'linear_eq_1', name: '📐 一元一次方程', emoji: '✏️' },
  { id: 'factoring', name: '🧩 因式分解', emoji: '🔍' },
  { id: 'quadratic_eq', name: '📈 一元二次方程', emoji: '🎯' },
  { id: 'probability', name: '🎲 概率初步', emoji: '🍀' },
]

const MASTERY_EMOJI: Record<string, string> = {
  not_started: '🌱',
  beginner: '🌿',
  developing: '🌳',
  proficient: '🌟',
  mastered: '👑',
}

const STATE_EMOJI: Record<string, string> = {
  FOCUSED: '😊',
  STRUGGLING: '😅',
  FRUSTRATED: '😣',
  BORED: '😴',
  NEED_BREAK: '☕',
  ONBOARDING: '👋',
  LEARNING: '📖',
  PRACTICING: '💪',
  REVIEWING: '🔄',
  BREAK: '☕',
}

export default function App() {
  const [learnerId] = useState('student_001')
  const [knowledgeId, setKnowledgeId] = useState('quadratic_eq')
  const [message, setMessage] = useState('')
  const [question, setQuestion] = useState<QuestionData | null>(null)
  const [answer, setAnswer] = useState('')
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null)
  const [chatResponse, setChatResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)
  const [bgImage, setBgImage] = useState('')

  // 背景图轮播
  useEffect(() => {
    let images: string[] = []
    const fetchAndSet = async () => {
      if (images.length === 0) {
        const res = await fetch(`${API_BASE}/backgrounds`)
        const data = await res.json()
        images = data.images || []
      }
      if (images.length > 0) {
        const random = images[Math.floor(Math.random() * images.length)]
        setBgImage(random)
      }
    }
    fetchAndSet()
    const timer = setInterval(fetchAndSet, 30000)
    return () => clearInterval(timer)
  }, [])

  // 时间追踪
  const sessionStart = useRef(Date.now())
  const lastActivity = useRef(Date.now())

  const getTimeData = () => ({
    session_duration: (Date.now() - sessionStart.current) / 1000,
    idle_seconds: (Date.now() - lastActivity.current) / 1000,
  })
  const updateActivity = () => { lastActivity.current = Date.now() }

  // 获取题目
  const fetchQuestion = async () => {
    updateActivity()
    setSubmitResult(null)
    setAnswer('')
    const res = await fetch(`${API_BASE}/question?knowledge_id=${knowledgeId}`)
    const data = await res.json()
    if (data.error) { alert(data.error); return }
    setQuestion(data)
  }

  // 提交答案
  const handleSubmit = async () => {
    if (!question || !answer.trim()) return
    updateActivity()
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ learner_id: learnerId, question_id: question.id, answer: answer.trim() }),
      })
      const data: SubmitResult = await res.json()
      setSubmitResult(data)
    } finally { setLoading(false) }
  }

  // 发送消息
  const handleChat = async () => {
    if (!message.trim()) return
    updateActivity()
    setChatLoading(true)
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ learner_id: learnerId, message: message.trim(), ...getTimeData() }),
      })
      const data = await res.json()
      setChatResponse(String(data.response?.response || ''))
      setMessage('')
    } finally { setChatLoading(false) }
  }

  return (
    <>
      {bgImage && <div className="bg-layer" style={{ backgroundImage: `url(${bgImage})` }} />}
      <div className="bg-overlay" />
      <div className="app">
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { min-height: 100vh; }
        .app { max-width: 960px; margin: 0 auto; padding: 24px; font-family: 'Segoe UI', system-ui, sans-serif; position: relative; z-index: 1; }
        .bg-layer { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-size: cover; background-position: center; transition: opacity 1.5s ease; z-index: 0; }
        .bg-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.75); backdrop-filter: blur(2px); z-index: 0; }
        .header { text-align: center; margin-bottom: 32px; }
        .header h1 { font-size: 28px; background: linear-gradient(135deg, #7c3aed, #2563eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { color: #6b7280; margin-top: 4px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #f0f0f0; }
        .card h2 { font-size: 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        .knowledge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
        .knowledge-btn { padding: 10px; border-radius: 10px; border: 2px solid #e5e7eb; background: white; cursor: pointer; font-size: 13px; transition: all 0.2s; }
        .knowledge-btn:hover { border-color: #a78bfa; transform: translateY(-1px); }
        .knowledge-btn.active { border-color: #7c3aed; background: #f5f3ff; }
        .btn { padding: 12px 20px; border-radius: 12px; border: none; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; width: 100%; }
        .btn:hover { transform: translateY(-1px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-primary { background: linear-gradient(135deg, #7c3aed, #6366f1); color: white; }
        .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: white; }
        .btn-chat { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }
        .question-card { background: #fefce8; border: 2px solid #fde68a; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
        .question-type { font-size: 11px; color: #92400e; background: #fef3c7; padding: 2px 8px; border-radius: 20px; display: inline-block; margin-bottom: 8px; }
        .question-stem { font-size: 15px; font-weight: 600; line-height: 1.5; margin-bottom: 12px; }
        .option-label { display: block; padding: 10px 12px; margin-bottom: 6px; border-radius: 8px; border: 2px solid #e5e7eb; cursor: pointer; transition: all 0.15s; font-size: 14px; }
        .option-label:hover { border-color: #a78bfa; background: #f5f3ff; }
        .option-label.selected { border-color: #7c3aed; background: #ede9fe; }
        input[type="text"], textarea { width: 100%; padding: 10px 12px; border-radius: 8px; border: 2px solid #e5e7eb; font-size: 14px; transition: border-color 0.2s; resize: vertical; }
        input[type="text"]:focus, textarea:focus { outline: none; border-color: #7c3aed; }
        .result-card { border-radius: 12px; padding: 16px; margin-bottom: 16px; }
        .result-correct { background: #ecfdf5; border: 2px solid #6ee7b7; }
        .result-wrong { background: #fef2f2; border: 2px solid #fca5a5; }
        .result-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
        .stat-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 13px; color: #4b5563; }
        .report-box { margin-top: 12px; padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 13px; white-space: pre-wrap; line-height: 1.6; color: #374151; }
        .chat-bubble { background: #ede9fe; border-radius: 12px; padding: 16px; white-space: pre-wrap; line-height: 1.6; font-size: 14px; }
        .level-up { animation: bounce 0.6s ease; }
        @keyframes bounce { 0%,100% { transform: scale(1); } 50% { transform: scale(1.1); } }
      `}</style>

      <header className="header">
        <h1>🎓 智能学习小助手</h1>
        <p>和 AI 老师一起学数学吧~ 学习者：{learnerId}</p>
      </header>

      <div className="grid">
        {/* 左侧 */}
        <div>
          {/* 知识点选择 */}
          <div className="card">
            <h2>📚 选择知识点</h2>
            <div className="knowledge-grid">
              {KNOWLEDGE_OPTIONS.map(k => (
                <button
                  key={k.id}
                  className={`knowledge-btn ${knowledgeId === k.id ? 'active' : ''}`}
                  onClick={() => setKnowledgeId(k.id)}
                >
                  {k.name}
                </button>
              ))}
            </div>
            <button className="btn btn-primary" onClick={fetchQuestion}>
              🎲 来一道题
            </button>
          </div>

          {/* 题目展示 */}
          {question && (
            <div className="card" style={{ marginTop: 16 }}>
              <h2>✍️ 答题</h2>
              <div className="question-card">
                <span className="question-type">
                  {question.type === 'choice' ? '选择题' : question.type === 'fill' ? '填空题' : '解答题'}
                </span>
                <p className="question-stem">{question.stem}</p>

                {question.type === 'choice' && question.options && (
                  <div>
                    {Object.entries(question.options).map(([key, val]) => (
                      <label key={key} className={`option-label ${answer === key ? 'selected' : ''}`}>
                        <input type="radio" name="choice" value={key} checked={answer === key} onChange={e => setAnswer(e.target.value)} style={{ display: 'none' }} />
                        <strong>{key}.</strong> {val}
                      </label>
                    ))}
                  </div>
                )}

                {question.type === 'fill' && (
                  <input type="text" value={answer} onChange={e => setAnswer(e.target.value)} placeholder="输入你的答案..." />
                )}

                {question.type === 'open' && (
                  <textarea value={answer} onChange={e => setAnswer(e.target.value)} placeholder="写出完整解题步骤..." style={{ minHeight: 100 }} />
                )}
              </div>
              <button className="btn btn-success" onClick={handleSubmit} disabled={loading || !answer.trim()}>
                {loading ? '⏳ 判题中...' : '✅ 提交答案'}
              </button>
            </div>
          )}

          {/* 对话 */}
          <div className="card" style={{ marginTop: 16 }}>
            <h2>💬 问老师</h2>
            <textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="有什么不懂的尽管问~" style={{ minHeight: 60, marginBottom: 10 }} />
            <button className="btn btn-chat" onClick={handleChat} disabled={chatLoading || !message.trim()}>
              {chatLoading ? '🤔 思考中...' : '🚀 发送'}
            </button>
          </div>
        </div>

        {/* 右侧 */}
        <div>
          {/* 判题结果 */}
          {submitResult && (
            <div className={`card result-card ${submitResult.is_correct ? 'result-correct' : 'result-wrong'}`}>
              <div className={`result-title ${submitResult.level_changed ? 'level-up' : ''}`}>
                {submitResult.is_correct ? '🎉 答对啦！' : '😅 答错了~'}
                {submitResult.level_changed && ' 🆙 升级！'}
              </div>
              {submitResult.feedback && <p style={{ color: '#6b7280', fontSize: 13, marginBottom: 8 }}>{submitResult.feedback}</p>}
              <div className="stat-row">
                <span>{MASTERY_EMOJI[submitResult.mastery_level] || '📊'}</span>
                <span>掌握度：<strong>{(submitResult.mastery * 100).toFixed(1)}%</strong>（{submitResult.mastery_level}）</span>
              </div>
              <div className="stat-row">
                <span>{STATE_EMOJI[submitResult.session_state] || '📖'}</span>
                <span>学习阶段：{submitResult.session_state}</span>
              </div>
              <div className="stat-row">
                <span>{STATE_EMOJI[submitResult.engagement_state] || '😊'}</span>
                <span>状态：{submitResult.engagement_state}</span>
              </div>
              <div className="report-box">{submitResult.report}</div>
            </div>
          )}

          {/* 对话回复 */}
          {chatResponse && (
            <div className="card" style={{ marginTop: submitResult ? 16 : 0 }}>
              <h2>🧑‍🏫 老师说</h2>
              <div className="chat-bubble">{chatResponse}</div>
            </div>
          )}

          {/* 空状态 */}
          {!submitResult && !chatResponse && (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🌟</div>
              <p style={{ color: '#9ca3af' }}>选一个知识点，点"来一道题"开始学习吧~</p>
            </div>
          )}
        </div>
      </div>
    </div>
    </>
  )
}
