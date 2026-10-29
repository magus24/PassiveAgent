import { useState, useEffect, useCallback } from 'react';
import { fetchUsers } from '../api/client';

export default function UserDirectory() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const loadUsers = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchUsers({ search: searchTerm })
      .then(data => {
        setUsers(data);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, [searchTerm]);

  useEffect(() => {
    // Basic debounce for search
    const timer = setTimeout(() => {
      loadUsers();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, loadUsers]);

  const getRiskClass = (score) => {
    if (score >= 0.7) return 'risk-high';
    if (score >= 0.4) return 'risk-medium';
    return 'risk-low';
  };

  const getRiskLabel = (score) => {
    if (score >= 0.7) return 'HIGH';
    if (score >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const handleUserClick = (userId) => {
    window.location.hash = `#/user/${userId}`;
  };

  return (
    <div className="users-directory-section">
      <div className="filters-bar">
        <div className="search-input-group" style={{ flexGrow: 1, maxWidth: '400px' }}>
          <input
            type="text"
            placeholder="Ism yoki username bo'yicha qidiruv..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}
          />
        </div>
        <button className="btn btn-secondary" onClick={loadUsers} disabled={loading}>
          {loading ? 'Yuklanmoqda…' : 'Yangilash'}
        </button>
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      <div className="table-wrap">
        <table className="data-table selectable-table" id="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Ism</th>
              <th>Username</th>
              <th>Xabarlar soni</th>
              <th>Xavf darajasi</th>
              <th>Xavf balli</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && !loading ? (
              <tr>
                <td colSpan="6" className="empty-row">Foydalanuvchilar topilmadi</td>
              </tr>
            ) : (
              users.map(user => (
                <tr key={user.id} onClick={() => handleUserClick(user.id)} className="clickable-row">
                  <td className="cell-mono">{user.id}</td>
                  <td>{user.first_name || ''} {user.last_name || ''}</td>
                  <td>{user.username ? `@${user.username}` : '—'}</td>
                  <td className="cell-mono">{user.total_messages}</td>
                  <td>
                    <span className={`badge ${getRiskClass(user.risk_score)}`}>
                      {getRiskLabel(user.risk_score)}
                    </span>
                  </td>
                  <td className="cell-mono">{user.risk_score.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
