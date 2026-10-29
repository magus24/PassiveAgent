import { useState, useEffect } from 'react';
import { fetchStats } from '../api/client';

export default function StatsPanel() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div className="stats-panel stats-error">⚠ {error}</div>;
  }

  if (!stats) {
    return <div className="stats-panel stats-loading">Yuklanmoqda…</div>;
  }

  const riskDist = stats.risk_distribution || {};
  const classDist = stats.classification_distribution || {};

  return (
    <div className="stats-panel">
      <div className="stat-card">
        <span className="stat-value">{stats.total_messages}</span>
        <span className="stat-label">Jami xabarlar</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.total_alerts}</span>
        <span className="stat-label">Ogohlantirishlar</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.unresolved_alerts}</span>
        <span className="stat-label">Yangi</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.unique_channels}</span>
        <span className="stat-label">Kanallar</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.unique_senders}</span>
        <span className="stat-label">Foydalanuvchilar</span>
      </div>

      <div className="stat-card stat-card-wide">
        <span className="stat-label">Xavf taqsimoti</span>
        <div className="stat-tags">
          {Object.entries(riskDist).map(([level, count]) => (
            <span key={level} className={`tag risk-${level.toLowerCase()}`}>
              {level}: {count}
            </span>
          ))}
          {Object.keys(riskDist).length === 0 && (
            <span className="tag tag-empty">Ma'lumot yo'q</span>
          )}
        </div>
      </div>

      <div className="stat-card stat-card-wide">
        <span className="stat-label">Kategoriyalar</span>
        <div className="stat-tags">
          {Object.entries(classDist).map(([label, count]) => (
            <span key={label} className="tag tag-class">
              {label}: {count}
            </span>
          ))}
          {Object.keys(classDist).length === 0 && (
            <span className="tag tag-empty">Ma'lumot yo'q</span>
          )}
        </div>
      </div>
    </div>
  );
}
