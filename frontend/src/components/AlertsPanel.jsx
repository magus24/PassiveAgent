import { useState, useEffect, useCallback } from 'react';
import { fetchAlerts, resolveAlert } from '../api/client';

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showResolved, setShowResolved] = useState(false);
  const [resolving, setResolving] = useState(null);

  const loadAlerts = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchAlerts({ resolved: showResolved ? undefined : false })
      .then((data) => {
        setAlerts(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [showResolved]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleResolve = async (alertId) => {
    setResolving(alertId);
    try {
      await resolveAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (e) {
      setError(`${alertId}-raqamli ogohlantirishni yopishda xatolik: ${e.message}`);
    } finally {
      setResolving(null);
    }
  };

  const truncate = (text, maxLen = 100) => {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '…' : text;
  };

  const formatTime = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="alerts-section">
      <div className="filters-bar">
        <label className="toggle-label" htmlFor="show-resolved">
          <input
            type="checkbox"
            id="show-resolved"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
          />
          Yopilganlarni ko'rsatish
        </label>
        <button className="btn btn-secondary" onClick={loadAlerts} disabled={loading}>
          {loading ? 'Yuklanmoqda…' : 'Yangilash'}
        </button>
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      {alerts.length === 0 && !loading && (
        <div className="empty-state">
          <span className="empty-icon">✅</span>
          <p>{showResolved ? "Ogohlantirishlar yo'q" : "Yangi ogohlantirishlar yo'q"}</p>
        </div>
      )}

      <div className="alerts-grid">
        {alerts.map((alert) => (
          <div key={alert.id} className={`alert-card ${alert.resolved ? 'resolved' : 'active'}`}>
            <div className="alert-header">
              <span className="alert-id">#{alert.id}</span>
              <span className={`badge risk-${(alert.risk_level || '').toLowerCase()}`}>
                {alert.risk_level}
              </span>
              <span className="alert-time">{formatTime(alert.timestamp)}</span>
            </div>
            <p className="alert-text" title={alert.text_preview}>
              {truncate(alert.text_preview)}
            </p>
            <div className="alert-meta">
              <span>Kanal: <strong>{alert.channel_id || '—'}</strong></span>
              <span>Yuboruvchi: <strong>{alert.sender_id || '—'}</strong></span>
              <span>Xavf: <strong>{alert.risk_score?.toFixed(2) || '—'}</strong></span>
              <span>Kategoriya: <strong>{alert.classification_label || '—'}</strong></span>
            </div>
            {!alert.resolved && (
              <button
                className="btn btn-resolve"
                onClick={() => handleResolve(alert.id)}
                disabled={resolving === alert.id}
              >
                {resolving === alert.id ? 'Yopilmoqda…' : '✓ Yopish'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
