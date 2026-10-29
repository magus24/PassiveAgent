import { useState, useEffect } from 'react';
import StatsPanel from './components/StatsPanel';
import MessagesTable from './components/MessagesTable';
import AlertsPanel from './components/AlertsPanel';
import SimilarSearch from './components/SimilarSearch';
import GraphView from './components/GraphView';
import UserProfile from './components/UserProfile';
import UserDirectory from './components/UserDirectory';
import './App.css';

const TABS = [
  { id: 'overview', label: 'Umumiy holat', icon: '📊' },
  { id: 'messages', label: 'Xabarlar', icon: '💬' },
  { id: 'alerts', label: 'Ogohlantirishlar', icon: '🚨' },
  { id: 'users', label: 'Qidiruv', icon: '👥' },
  { id: 'similar', label: 'Semantik qidiruv', icon: '🔍' },
  { id: 'graph', label: 'Graf', icon: '🕸️' },
];

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [similarMsgId, setSimilarMsgId] = useState(null);
  const [currentRoute, setCurrentRoute] = useState({ name: 'dashboard', params: {} });

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash.startsWith('#/user/')) {
        const id = hash.split('/')[2];
        setCurrentRoute({ name: 'user', params: { id } });
      } else {
        setCurrentRoute({ name: 'dashboard', params: {} });
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();

    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleFindSimilar = (messageId) => {
    setSimilarMsgId(messageId);
    setActiveTab('similar');
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header" id="app-header">
        <div className="header-brand">
          <div className="header-logo-box">
            <img src="/logo.png" alt="PassiveAgent Logo" className="header-logo-img" />
          </div>
          <div>
            <h1>PassiveAgent</h1>
          </div>
        </div>

        <nav className="header-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id && currentRoute.name === 'dashboard' ? 'active' : ''}`}
              onClick={() => {
                window.location.hash = '';
                setActiveTab(tab.id);
              }}
            >
              <span className="nav-icon">{tab.icon}</span>
              <span className="nav-label">{tab.label}</span>
            </button>
          ))}
        </nav>

        <div className="header-status">
          <span className="status-dot"></span>
          <span className="status-text">Tizim faol</span>
        </div>
      </header>

      {/* Content */}
      <main className="app-content" id="main-content">
        {currentRoute.name === 'user' ? (
          <section className="tab-panel">
            <div className="section-header" style={{ marginBottom: '20px' }}>
              <button className="btn btn-secondary" onClick={() => window.location.hash = ''}>
                ← Orqaga (Dashboard)
              </button>
            </div>
            <UserProfile userId={currentRoute.params.id} />
          </section>
        ) : (
          <>
            {activeTab === 'overview' && (
              <section className="tab-panel">
                <h2 className="section-title">Umumiy holat</h2>
                <StatsPanel />
              </section>
            )}

            {activeTab === 'messages' && (
              <section className="tab-panel">
                <h2 className="section-title">Xabarlar</h2>
                <MessagesTable onSelectMessage={handleFindSimilar} />
              </section>
            )}

            {activeTab === 'alerts' && (
              <section className="tab-panel">
                <h2 className="section-title">Ogohlantirishlarni boshqarish</h2>
                <AlertsPanel />
              </section>
            )}

            {activeTab === 'users' && (
              <section className="tab-panel">
                <h2 className="section-title">Foydalanuvchilar qidiruvi</h2>
                <UserDirectory />
              </section>
            )}

            {activeTab === 'similar' && (
              <section className="tab-panel">
                <h2 className="section-title">Semantik qidiruv</h2>
                <SimilarSearch initialMessageId={similarMsgId} />
              </section>
            )}

            {activeTab === 'graph' && (
              <section className="tab-panel">
                <h2 className="section-title">Ma'lumotlar grafi</h2>
                <GraphView />
              </section>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <span>Created by CyberBaza</span>
      </footer>
    </div>
  );
}

export default App;
