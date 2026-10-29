import { useState, useEffect, useCallback } from 'react';
import { fetchUser, fetchUserMessages } from '../api/client';
import '../UserProfile.css';

export default function UserProfile({ userId }) {
  const [profile, setProfile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState('');
  const [chatFilter, setChatFilter] = useState('');

  const loadData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchUser(userId),
      fetchUserMessages(userId, { type: typeFilter, chat_id: chatFilter })
    ])
    .then(([userData, messagesData]) => {
      setProfile(userData);
      setMessages(messagesData);
      setLoading(false);
    })
    .catch(err => {
      setError(err.message);
      setLoading(false);
    });
  }, [userId, typeFilter, chatFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <div className="loading">Profil yuklanmoqda...</div>;
  if (error) return <div className="error-banner">Xato: {error}</div>;
  if (!profile) return null;

  const { user, stats, names_history } = profile;

  // Extract unique reasons from messages
  const allReasons = new Set();
  messages.forEach(m => {
    if (m.reasons) m.reasons.forEach(r => allReasons.add(r));
    if (m.ai_analysis?.reasons) m.ai_analysis.reasons.forEach(r => allReasons.add(`AI: ${r}`));
  });
  const uniqueReasons = Array.from(allReasons);
  
  // Calculate risk level based on user aggregate score
  let userRiskLevel = 'LOW';
  if (stats.risk_score >= 0.7) userRiskLevel = 'HIGH';
  else if (stats.risk_score >= 0.4) userRiskLevel = 'MEDIUM';

  const truncate = (text, maxLen = 100) => {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '…' : text;
  };

  const getRiskClass = (level) => {
    if (!level) return '';
    return `risk-${level.toLowerCase()}`;
  };
  
  const handleMessageClick = (chatId, msgId) => {
    if (!chatId || !msgId) return;
    // chat_id usually starts with -100 for supergroups
    let cleanChatId = String(chatId);
    if (cleanChatId.startsWith('-100')) {
      cleanChatId = cleanChatId.substring(4);
    }
    window.open(`https://t.me/c/${cleanChatId}/${msgId}`, '_blank');
  };

  // Get unique chats for filter
  const uniqueChats = [...new Set(messages.map(m => m.chat_id).filter(Boolean))];

  return (
    <div className="user-profile">
      <div className="profile-header-card">
        <div className="profile-info">
          <h2>{user.first_name || ''} {user.last_name || ''}</h2>
          <div className="profile-meta">
            <span className="meta-item"><strong>Username:</strong> {user.username ? `@${user.username}` : '—'}</span>
            <span className="meta-item"><strong>ID:</strong> {user.id}</span>
          </div>
        </div>
        <div className={`profile-risk badge ${getRiskClass(userRiskLevel)}`}>
          <span>Risk: {stats.risk_score.toFixed(2)}</span>
          <strong style={{marginLeft: '8px'}}>{userRiskLevel}</strong>
        </div>
      </div>

      <div className="profile-grid">
        {/* AI Analysis */}
        <div className="profile-card ai-analysis">
          <h3>AI Tahlili (AI Analysis)</h3>
          <div className="reasons-list">
            {uniqueReasons.length > 0 ? (
              <ul>
                {uniqueReasons.map((reason, idx) => <li key={idx}>⚠️ {reason}</li>)}
              </ul>
            ) : (
              <p className="text-muted">Gumonli harakatlar aniqlanmadi.</p>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="profile-card stats-card">
          <h3>Statistika</h3>
          <div className="stats-grid-inner">
            <div className="stat-item-inner">
              <span className="stat-value">{stats.total_messages}</span>
              <span className="stat-label">Xabarlar</span>
            </div>
            <div className="stat-item-inner">
              <span className="stat-value">{stats.total_chats}</span>
              <span className="stat-label">Chatlar</span>
            </div>
            <div className="stat-item-inner">
              <span className="stat-value">{(stats.media_percent * 100).toFixed(0)}%</span>
              <span className="stat-label">Media</span>
            </div>
            <div className="stat-item-inner">
              <span className="stat-value">{(stats.reply_percent * 100).toFixed(0)}%</span>
              <span className="stat-label">Javoblar</span>
            </div>
          </div>
        </div>

        {/* History */}
        <div className="profile-card history-card">
          <h3>Ismlar tarixi</h3>
          <ul className="history-list">
            {names_history.length > 0 ? (
              names_history.slice(0, 5).map((h, i) => (
                <li key={i} className="history-item">
                  <span className="history-name">{h.name}</span>
                  <span className="history-date">{h.timestamp ? new Date(h.timestamp).toLocaleDateString() : ''}</span>
                </li>
              ))
            ) : (
              <li className="text-muted">Tarix yo'q</li>
            )}
          </ul>
        </div>
      </div>

      {/* Messages Table */}
      <div className="profile-messages">
        <div className="profile-messages-header">
          <h3>Xabarlar tarixi</h3>
          <div className="filters-bar inline-filters">
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">Barcha turlar</option>
              <option value="text">Matn</option>
              <option value="link">Havola</option>
              <option value="image">Rasm</option>
              <option value="video">Video</option>
            </select>
            <select value={chatFilter} onChange={(e) => setChatFilter(e.target.value)}>
              <option value="">Barcha chatlar</option>
              {uniqueChats.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        <div className="table-wrap">
          <table className="data-table selectable-table">
            <thead>
              <tr>
                <th>Vaqt</th>
                <th>Chat ID</th>
                <th>Tur</th>
                <th>Matn</th>
                <th>Xavf</th>
                <th>Ball</th>
                <th>AI</th>
                <th>AI Ball</th>
              </tr>
            </thead>
            <tbody>
              {messages.length === 0 ? (
                <tr><td colSpan="8" className="empty-row">Xabarlar topilmadi</td></tr>
              ) : (
                messages.map(msg => (
                  <tr key={msg.id} onClick={() => handleMessageClick(msg.chat_id, msg.telegram_id)} className="clickable-row">
                    <td className="cell-time">{msg.timestamp ? new Date(msg.timestamp).toLocaleString() : '—'}</td>
                    <td className="cell-mono">{msg.chat_id || '—'}</td>
                    <td>{msg.message_type}</td>
                    <td className="cell-text">{truncate(msg.text)}</td>
                    <td><span className={`badge ${getRiskClass(msg.risk_level)}`}>{msg.risk_level}</span></td>
                    <td className="cell-mono">{msg.risk_score?.toFixed(2)}</td>
                    <td><span className="badge badge-ai">{msg.ai_label || 'вЂ”'}</span></td>
                    <td className="cell-mono">{msg.ai_score != null ? `${Number(msg.ai_score).toFixed(0)}/100` : 'вЂ”'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
