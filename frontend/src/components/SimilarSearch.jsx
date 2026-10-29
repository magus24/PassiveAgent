import { useState } from 'react';
import { fetchSimilar } from '../api/client';

export default function SimilarSearch({ initialMessageId }) {
  const [messageId, setMessageId] = useState(initialMessageId || '');
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!messageId) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await fetchSimilar(messageId);
      setResults(data);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const truncate = (text, maxLen = 150) => {
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
    <div className="similar-section">
      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-group">
          <label htmlFor="msg-id-input">Xabar IDsi</label>
          <input
            id="msg-id-input"
            type="number"
            min="1"
            placeholder="Xabar ID sini kiriting…"
            value={messageId}
            onChange={(e) => setMessageId(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading || !messageId}>
          {loading ? 'Izlanmoqda…' : '🔍 O\'xshashlarini topish'}
        </button>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {searched && !loading && results.length === 0 && !error && (
        <div className="empty-state">
          <span className="empty-icon">🔎</span>
          <p>O'xshash xabarlar topilmadi</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="table-wrap">
          <table className="data-table" id="similar-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>O'xshashlik</th>
                <th>Matn</th>
                <th>Xavf</th>
                <th>Kategoriya</th>
                <th>Kanal</th>
                <th>Vaqt</th>
              </tr>
            </thead>
            <tbody>
              {results.map((msg) => (
                <tr key={msg.id}>
                  <td className="cell-mono">{msg.id}</td>
                  <td>
                    <div className="similarity-bar">
                      <div
                        className="similarity-fill"
                        style={{ width: `${(msg.similarity_score * 100).toFixed(0)}%` }}
                      />
                      <span className="similarity-value">
                        {(msg.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="cell-text" title={msg.text}>
                    {truncate(msg.text)}
                  </td>
                  <td>
                    <span className={`badge risk-${(msg.risk_level || '').toLowerCase()}`}>
                      {msg.risk_level || '—'}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-class">
                      {msg.classification_label || '—'}
                    </span>
                  </td>
                  <td className="cell-mono">{msg.channel_id || '—'}</td>
                  <td className="cell-time">{formatTime(msg.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
