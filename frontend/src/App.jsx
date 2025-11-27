import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Community from './pages/Community';
import Admin from './pages/Admin';
import Rehabilitation from './pages/Rehabilitation'; // 👈 [추가 1] 파일 임포트

function App() {
  return (
    <Router>
      <div style={{ fontFamily: 'Arial, sans-serif', minHeight: '100vh', backgroundColor: '#f0f2f5' }}>
        {/* 상단 네비게이션 바 */}
        <nav style={{ padding: '1rem 2rem', background: '#20232a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#61dafb' }}>
            🏃‍♂️ Physical AI Health
          </div>
          <div style={{ display: 'flex', gap: '20px' }}>
            <Link to="/" style={{ color: 'white', textDecoration: 'none', fontWeight: '500' }}>Community</Link>
            <Link to="/rehab" style={{ color: '#4ECDC4', textDecoration: 'none', fontWeight: '500' }}>🧩 AI Rehab</Link> {/* 👈 [추가 2] 메뉴 추가 */}
            <Link to="/admin" style={{ color: '#ff6b6b', textDecoration: 'none', fontWeight: '500' }}>Infrastructure</Link>
          </div>
        </nav>

        {/* 메인 컨텐츠 영역 */}
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
          <Routes>
            <Route path="/" element={<Community />} />
            <Route path="/rehab" element={<Rehabilitation />} /> {/* 👈 [추가 3] 라우터 등록 */}
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;