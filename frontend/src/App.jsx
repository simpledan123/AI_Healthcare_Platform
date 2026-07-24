import { useEffect, useMemo, useState } from 'react';
import { api } from './api';

const verdictLabel = {
  PASS: '기준 충족',
  RETRY: '재시도 권장',
  REVIEW: '검토 필요',
};

function App() {
  const [meta, setMeta] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [references, setReferences] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [result, setResult] = useState(null);
  const [tab, setTab] = useState('demo');
  const [severity, setSeverity] = useState(3);
  const [painDescription, setPainDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadAll = async () => {
    const [metaData, dashboardData, referenceData, taskData] = await Promise.all([
      api.meta(),
      api.dashboard(),
      api.references(),
      api.reviewTasks(),
    ]);
    setMeta(metaData);
    setDashboard(dashboardData);
    setReferences(referenceData);
    setTasks(taskData);
  };

  useEffect(() => {
    loadAll().catch((err) => setError(err.message));
  }, []);

  const run = async (action) => {
    setLoading(true);
    setError('');
    try {
      const data = await action();
      setResult(data);
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runDemo = () => run(() => api.runDemo(severity, painDescription));

  const analyzeVideo = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    return run(() => api.analyzeVideo(form));
  };

  const importReference = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    return run(async () => {
      await api.importReference(form);
      await loadAll();
      setTab('video');
      return null;
    });
  };

  const resolveTask = async (task) => {
    const note = window.prompt('검토 내용을 입력해 주세요.');
    if (!note) return;
    await api.resolveTask(task.id, 'RESOLVED', note);
    await loadAll();
  };

  const selectedReference = useMemo(
    () => references.find((item) => item.source_type === 'expert_video') || references[0],
    [references],
  );

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">AI-ASSISTED MOTION REVIEW</p>
          <h1>손목 재활 동작을<br />측정하고, 근거로 검수합니다.</h1>
          <p className="hero-copy">
            전문가 영상과 사용자 영상에서 Pose+Hands 특징을 추출하고, DTW로 속도 차이를
            정렬한 뒤 AI가 측정 근거 안에서 교정 피드백을 생성합니다.
          </p>
        </div>
        <div className="system-card">
          <span className="live-dot" />
          <strong>{meta?.ai_review_mode === 'live' ? 'Claude live review' : 'Deterministic demo review'}</strong>
          <p>{meta?.demo_notice || '시스템 정보를 불러오는 중입니다.'}</p>
        </div>
      </header>

      {error && <div className="alert error">{error}</div>}

      <section className="metrics">
        <Metric label="총 분석" value={dashboard?.total_attempts ?? 0} suffix="회" />
        <Metric label="평균 유사도" value={dashboard?.average_similarity ?? 0} suffix="점" />
        <Metric label="평균 데이터 품질" value={Math.round((dashboard?.average_quality ?? 0) * 100)} suffix="%" />
        <Metric label="검토 대기" value={dashboard?.open_review_tasks ?? 0} suffix="건" accent />
      </section>

      <nav className="tabs">
        {[
          ['demo', '데모 실행'],
          ['video', '사용자 영상'],
          ['reference', '전문가 기준 등록'],
          ['review', '검토·운영'],
        ].map(([key, label]) => (
          <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </nav>

      <main>
        {tab === 'demo' && (
          <section className="panel split">
            <div>
              <p className="section-kicker">DETERMINISTIC SAMPLE</p>
              <h2>실제 영상 없이 전체 흐름 확인</h2>
              <p className="muted">
                합성된 전문가·사용자 포즈 특징을 사용합니다. 같은 입력은 언제나 같은 결과를
                만들며, 모든 기록에는 데모 데이터임이 저장됩니다.
              </p>
              <label>
                현재 불편함 정도 <strong>{severity}/10</strong>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={severity}
                  onChange={(event) => setSeverity(Number(event.target.value))}
                />
              </label>
              <label>
                추가 설명
                <textarea
                  value={painDescription}
                  onChange={(event) => setPainDescription(event.target.value)}
                  placeholder="예: 스트레칭 중 손목이 약간 당깁니다."
                />
              </label>
              <button className="primary" onClick={runDemo} disabled={loading}>
                {loading ? '분석 중…' : '데모 분석 실행'}
              </button>
            </div>
            <WorkflowSteps />
          </section>
        )}

        {tab === 'video' && (
          <section className="panel">
            <p className="section-kicker">REAL VIDEO PATH</p>
            <h2>사용자 영상 분석</h2>
            <p className="muted">
              원본 영상은 임시 파일로만 처리한 뒤 삭제합니다. SQL에는 파생 특징과 검수 결과만
              저장됩니다. 오른손·팔꿈치·어깨가 한 화면에 보이는 영상을 사용해 주세요.
            </p>
            <form className="form-grid" onSubmit={analyzeVideo}>
              <label>
                전문가 기준
                <select name="reference_id" defaultValue={selectedReference?.id}>
                  {references.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.source_type === 'synthetic_demo' ? '데모 기준' : `v${item.version}`}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                통증 강도
                <input name="severity" type="number" min="1" max="10" defaultValue="3" />
              </label>
              <label className="wide">
                사용자 영상
                <input name="video" type="file" accept="video/*" required />
              </label>
              <label className="wide">
                추가 설명
                <input name="pain_description" placeholder="진단이 아닌 검토 분기용 정보입니다." />
              </label>
              <button className="primary" disabled={loading}>영상 분석 시작</button>
            </form>
          </section>
        )}

        {tab === 'reference' && (
          <section className="panel">
            <p className="section-kicker">REFERENCE ASSET</p>
            <h2>전문가 기준 영상 등록</h2>
            <p className="muted">
              영상에서 파생 특징을 한 번 추출해 버전이 있는 기준 데이터로 저장합니다. 전문가
              검토 여부는 별도 필드로 관리하며, 데모 데이터는 승인된 기준으로 표시하지 않습니다.
            </p>
            <form className="form-grid" onSubmit={importReference}>
              <label>기준 ID<input name="exercise_id" defaultValue="wrist_extension_v1" required /></label>
              <label>버전<input name="version" defaultValue="1.0" required /></label>
              <label>운동명<input name="name" defaultValue="손목 신전 스트레칭" required /></label>
              <label>부위<input name="body_part" defaultValue="손목" required /></label>
              <label className="wide">설명<input name="description" defaultValue="전문가 기준 손목 신전 동작" required /></label>
              <label className="wide">전문가 영상<input name="video" type="file" accept="video/*" required /></label>
              <label className="checkbox"><input name="approved" type="checkbox" value="true" /> 전문가 검토 완료</label>
              <button className="primary" disabled={loading}>기준 데이터 생성</button>
            </form>
          </section>
        )}

        {tab === 'review' && (
          <section className="operations-grid">
            <div className="panel">
              <p className="section-kicker">SQL OPERATIONS</p>
              <h2>최근 분석 기록</h2>
              <DataTable rows={dashboard?.recent_attempts || []} />
            </div>
            <div className="panel">
              <p className="section-kicker">HUMAN IN THE LOOP</p>
              <h2>검토 작업</h2>
              {tasks.length === 0 ? (
                <p className="empty">검토 작업이 없습니다. 통증 강도 8 이상으로 데모를 실행하면 분기 흐름을 확인할 수 있습니다.</p>
              ) : (
                <div className="task-list">
                  {tasks.map((task) => (
                    <article key={task.id}>
                      <div>
                        <span className={`status ${task.status.toLowerCase()}`}>{task.status}</span>
                        <strong>{task.reference_name}</strong>
                        <p>{task.reason}</p>
                        {task.reviewer_note && <small>검토 의견: {task.reviewer_note}</small>}
                      </div>
                      {task.status === 'OPEN' && (
                        <button className="secondary" onClick={() => resolveTask(task)}>처리</button>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {result && <ResultCard result={result} onClose={() => setResult(null)} />}
      </main>

      <footer>
        <p>{meta?.medical_notice}</p>
        <p>Raw video retention: off · Prompt contract: pose-review-v1.0 · Evidence validation: on</p>
      </footer>
    </div>
  );
}

function Metric({ label, value, suffix, accent }) {
  return (
    <article className={accent ? 'metric accent' : 'metric'}>
      <span>{label}</span>
      <strong>{value}<small>{suffix}</small></strong>
    </article>
  );
}

function WorkflowSteps() {
  const steps = [
    ['01', '특징 추출', 'Pose+Hands'],
    ['02', '시간 정렬', 'DTW path'],
    ['03', '근거 생성', '관절·구간 편차'],
    ['04', '검수 분기', 'AI·정책·사람'],
  ];
  return (
    <div className="workflow">
      {steps.map(([num, title, detail]) => (
        <div key={num}>
          <span>{num}</span>
          <strong>{title}</strong>
          <small>{detail}</small>
        </div>
      ))}
    </div>
  );
}

function ResultCard({ result, onClose }) {
  const review = result.review;
  return (
    <div className="result-overlay">
      <section className="result-card">
        <button className="close" onClick={onClose}>×</button>
        <p className="section-kicker">{result.mode === 'demo' ? 'DEMO RESULT' : 'VIDEO RESULT'}</p>
        <div className="score-row">
          <div className="score-ring"><strong>{Math.round(result.overall_similarity)}</strong><span>유사도</span></div>
          <div>
            <span className={`verdict ${review.verdict.toLowerCase()}`}>{verdictLabel[review.verdict]}</span>
            <h2>{review.summary}</h2>
            <p className="muted">
              {review.provider} · {review.model} · 신뢰도 {Math.round(review.confidence * 100)}%
            </p>
          </div>
        </div>
        <div className="evidence-list">
          {review.corrections.map((item, index) => (
            <article key={`${item.joint}-${index}`}>
              <span>{index + 1}</span>
              <div><strong>{item.segment} · {item.joint}</strong><p>{item.feedback}</p><small>{item.evidence}</small></div>
            </article>
          ))}
        </div>
        {review.safety_flags.length > 0 && (
          <div className="alert warning">검토 사유: {review.safety_flags.join(', ')}</div>
        )}
        <div className="result-meta">
          <span>데이터 품질 {Math.round(result.data_quality * 100)}%</span>
          <span>속도비 {result.speed_ratio}</span>
          <span>DTW 거리 {result.dtw_distance}</span>
          <span>검증 {review.validation_status}</span>
        </div>
      </section>
    </div>
  );
}

function DataTable({ rows }) {
  if (rows.length === 0) return <p className="empty">아직 분석 기록이 없습니다.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>데이터</th><th>유사도</th><th>판정</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>#{row.id}</td>
              <td>{row.mode === 'demo' ? '데모' : '영상'}</td>
              <td>{Math.round(row.similarity)}점</td>
              <td><span className={`verdict small ${row.verdict.toLowerCase()}`}>{verdictLabel[row.verdict]}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;

