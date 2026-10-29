import { useState, useEffect, useCallback } from 'react';
import {
  backfillLocal,
  fetchAiStatus,
  fetchMessageDetail,
  fetchMessages,
  reanalyzeAiCandidates,
  reanalyzeMessageAi,
  updateMessageReview,
} from '../api/client';

export default function MessagesTable({ onSelectMessage }) {
  const [messages, setMessages] = useState([]);
  const [aiStatus, setAiStatus] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzingId, setReanalyzingId] = useState(null);
  const [batchRunning, setBatchRunning] = useState(false);
  const [backfillRunning, setBackfillRunning] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [riskFilter, setRiskFilter] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [aiStatusFilter, setAiStatusFilter] = useState('');
  const [localCategoryFilter, setLocalCategoryFilter] = useState('');
  const [reviewStatusFilter, setReviewStatusFilter] = useState('');
  const [needsReview, setNeedsReview] = useState(false);
  const [hasLink, setHasLink] = useState(false);

  const loadMessages = useCallback(() => {
    setLoading(true);
    setError(null);
    const params = {};
    if (riskFilter) params.risk_level = riskFilter;
    if (classFilter) params.classification = classFilter;
    if (aiStatusFilter) params.ai_status = aiStatusFilter;
    if (localCategoryFilter) params.local_category = localCategoryFilter;
    if (reviewStatusFilter) params.review_status = reviewStatusFilter;
    if (needsReview) params.needs_review = true;
    if (hasLink) params.has_link = true;

    Promise.all([
      fetchMessages(params),
      fetchAiStatus().catch(() => null),
    ])
      .then(([data, status]) => {
        setMessages(data);
        setAiStatus(status);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [riskFilter, classFilter, aiStatusFilter, localCategoryFilter, reviewStatusFilter, needsReview, hasLink]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  const getRiskClass = (level) => {
    if (!level) return '';
    return `risk-${level.toLowerCase()}`;
  };

  const truncate = (text, maxLen = 120) => {
    if (!text) return '-';
    return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text;
  };

  const formatTime = (iso) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleReanalyze = async (messageId) => {
    setReanalyzingId(messageId);
    setError(null);
    try {
      const analysis = await reanalyzeMessageAi(messageId);
      setMessages((prev) => prev.map((msg) => (
        msg.id === messageId
          ? {
              ...msg,
              ai_status: analysis.ai_status,
              ai_label: analysis.analysis?.label,
              ai_score: analysis.analysis?.risk_score,
              ai_confidence: analysis.analysis?.confidence,
              ai_summary: analysis.analysis?.summary,
              ai_risk_level: analysis.analysis?.risk_level,
            }
          : msg
      )));
    } catch (e) {
      setError(e.message);
    } finally {
      setReanalyzingId(null);
    }
  };

  const handleBatchReanalyze = async () => {
    setBatchRunning(true);
    setError(null);
    try {
      const result = await reanalyzeAiCandidates(50);
      await loadMessages();
      setError(`AI batch done: analyzed=${result.analyzed}, cached=${result.cached}, skipped=${result.skipped}, rate_limited=${result.rate_limited}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBatchRunning(false);
    }
  };

  const handleBackfill = async () => {
    setBackfillRunning(true);
    setError(null);
    try {
      const result = await backfillLocal(1000);
      await loadMessages();
      setError(`Local backfill done: updated=${result.updated}, needs_review=${result.needs_review}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBackfillRunning(false);
    }
  };

  const openDetail = async (messageId) => {
    setError(null);
    try {
      const detail = await fetchMessageDetail(messageId);
      setSelectedDetail(detail);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleReview = async (messageId, status) => {
    try {
      const updated = await updateMessageReview(messageId, status);
      setMessages((prev) => prev.map((msg) => (msg.id === messageId ? { ...msg, review_status: updated.review_status } : msg)));
      if (selectedDetail?.message?.id === messageId) {
        setSelectedDetail((prev) => ({ ...prev, message: { ...prev.message, review_status: updated.review_status } }));
      }
    } catch (e) {
      setError(e.message);
    }
  };

  const aiUnavailable = aiStatus && (!aiStatus.enabled || !aiStatus.api_key_configured);

  return (
    <div className="messages-section">
      <div className="filters-bar">
        <div className="filter-group">
          <label htmlFor="risk-filter">Xavf</label>
          <select
            id="risk-filter"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="class-filter">Kategoriya</label>
          <select
            id="class-filter"
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="scam">Scam</option>
            <option value="phishing">Phishing</option>
            <option value="spam">Spam</option>
            <option value="normal">Normal</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="local-category-filter">Local</label>
          <select
            id="local-category-filter"
            value={localCategoryFilter}
            onChange={(e) => setLocalCategoryFilter(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="service_ad">Service ad</option>
            <option value="suspicious">Suspicious</option>
            <option value="scam">Scam</option>
            <option value="phishing">Phishing</option>
            <option value="normal">Normal</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="ai-status-filter">AI status</label>
          <select
            id="ai-status-filter"
            value={aiStatusFilter}
            onChange={(e) => setAiStatusFilter(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="analyzed">Analyzed</option>
            <option value="cached">Cached</option>
            <option value="skipped_low_risk">Skipped low</option>
            <option value="skipped_too_short">Too short</option>
            <option value="rate_limited_minute">Rate minute</option>
            <option value="rate_limited_daily">Rate daily</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="review-status-filter">Review</label>
          <select
            id="review-status-filter"
            value={reviewStatusFilter}
            onChange={(e) => setReviewStatusFilter(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="new">New</option>
            <option value="needs_review">Needs review</option>
            <option value="confirmed_threat">Confirmed</option>
            <option value="false_positive">False positive</option>
            <option value="ignored">Ignored</option>
          </select>
        </div>
        <label className="toggle-label" htmlFor="needs-review">
          <input
            type="checkbox"
            id="needs-review"
            checked={needsReview}
            onChange={(e) => setNeedsReview(e.target.checked)}
          />
          Needs Review
        </label>
        <label className="toggle-label" htmlFor="has-link">
          <input
            type="checkbox"
            id="has-link"
            checked={hasLink}
            onChange={(e) => setHasLink(e.target.checked)}
          />
          Has link
        </label>
        <button className="btn btn-secondary" onClick={loadMessages} disabled={loading}>
          {loading ? 'Yuklanmoqda...' : 'Yangilash'}
        </button>
        <button className="btn btn-primary" onClick={handleBatchReanalyze} disabled={batchRunning}>
          {batchRunning ? 'AI batch...' : 'Analyze candidates'}
        </button>
        <button className="btn btn-secondary" onClick={handleBackfill} disabled={backfillRunning}>
          {backfillRunning ? 'Backfill...' : 'Backfill local'}
        </button>
        {aiStatus && (
          <span className={`ai-status ${aiUnavailable ? 'muted' : 'ready'}`}>
            AI: {aiStatus.enabled ? aiStatus.provider : 'disabled'}
            {aiStatus.api_key_configured ? '' : ' (no key)'}
          </span>
        )}
      </div>

      {aiUnavailable && (
        <div className="info-banner">
          Groq AI is disabled or GROQ_API_KEY is not configured. Existing local ML/NLP analysis still works.
        </div>
      )}

      {error && <div className="error-banner">Warning: {error}</div>}

      <div className="table-wrap">
        <table className="data-table" id="messages-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Kanal</th>
              <th>Yuboruvchi</th>
              <th>Matn</th>
              <th>Xavf</th>
              <th>Ball</th>
              <th>Kategoriya</th>
              <th>Local</th>
              <th>Reasons</th>
              <th>Review</th>
              <th>AI status</th>
              <th>AI</th>
              <th>AI ball</th>
              <th>AI summary</th>
              <th>Vaqt</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {messages.length === 0 && !loading && (
              <tr>
                <td colSpan="16" className="empty-row">Xabarlar topilmadi</td>
              </tr>
            )}
            {messages.map((msg) => (
              <tr key={msg.id} className={getRiskClass(msg.risk_level)}>
                <td className="cell-mono">{msg.id}</td>
                <td className="cell-mono">{msg.channel_id || '-'}</td>
                <td className="cell-mono">
                  {msg.sender_id ? (
                    <a href={`#/user/${msg.user_id}`} className="user-link">
                      {msg.sender_id}
                    </a>
                  ) : '-'}
                </td>
                <td className="cell-text" title={msg.text}>
                  {truncate(msg.text)}
                </td>
                <td>
                  <span className={`badge ${getRiskClass(msg.risk_level)}`}>
                    {msg.risk_level || '-'}
                  </span>
                </td>
                <td className="cell-mono">
                  {msg.risk_score != null ? msg.risk_score.toFixed(2) : '-'}
                </td>
                <td>
                  <span className="badge badge-class">
                    {msg.classification_label || '-'}
                  </span>
                </td>
                <td>
                  <span className="badge badge-local">
                    {msg.local_category || '-'}
                  </span>
                  <span className="cell-mono local-score">
                    {msg.local_score != null ? Number(msg.local_score).toFixed(2) : ''}
                  </span>
                </td>
                <td className="cell-text" title={(msg.local_reasons || []).join(', ')}>
                  {truncate((msg.local_reasons || []).join(', '), 90)}
                </td>
                <td>
                  <span className="badge badge-review">
                    {msg.review_status || 'new'}
                  </span>
                </td>
                <td>
                  <span className="badge badge-ai-status">
                    {msg.ai_status || '-'}
                  </span>
                </td>
                <td>
                  <span className="badge badge-ai">
                    {msg.ai_label || '-'}
                  </span>
                </td>
                <td className="cell-mono">
                  {msg.ai_score != null ? `${Number(msg.ai_score).toFixed(0)}/100` : '-'}
                  {msg.ai_confidence != null ? ` (${Number(msg.ai_confidence).toFixed(2)})` : ''}
                </td>
                <td className="cell-text" title={msg.ai_summary || ''}>
                  {truncate(msg.ai_summary, 90)}
                </td>
                <td className="cell-time">{formatTime(msg.timestamp)}</td>
                <td className="table-actions">
                  {onSelectMessage && (
                    <button
                      className="btn btn-small"
                      onClick={() => onSelectMessage(msg.id)}
                      title="Find similar messages"
                    >
                      Similar
                    </button>
                  )}
                  <button
                    className="btn btn-small btn-secondary"
                    onClick={() => openDetail(msg.id)}
                    title="Open message details"
                  >
                    Detail
                  </button>
                  <button
                    className="btn btn-small btn-secondary"
                    onClick={() => handleReanalyze(msg.id)}
                    disabled={reanalyzingId === msg.id}
                    title="Reanalyze with Groq AI"
                  >
                    {reanalyzingId === msg.id ? 'AI...' : 'AI'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selectedDetail && (
        <div className="detail-panel">
          <div className="detail-header">
            <h3>Message #{selectedDetail.message.id}</h3>
            <button className="btn btn-small" onClick={() => setSelectedDetail(null)}>Close</button>
          </div>
          <p className="detail-text">{selectedDetail.message.text || '-'}</p>
          <div className="detail-grid">
            <div>
              <strong>Risk</strong>
              <p>{selectedDetail.message.risk_level} / {Number(selectedDetail.message.risk_score || 0).toFixed(2)}</p>
            </div>
            <div>
              <strong>Local</strong>
              <p>{selectedDetail.message.local_category || '-'} / {Number(selectedDetail.message.local_score || 0).toFixed(2)}</p>
            </div>
            <div>
              <strong>AI</strong>
              <p>{selectedDetail.message.ai_status || '-'} / {selectedDetail.message.ai_label || '-'}</p>
            </div>
            <div>
              <strong>Campaign</strong>
              <p>{selectedDetail.message.campaign_key || '-'} ({selectedDetail.campaign_count})</p>
            </div>
          </div>
          <div className="detail-section">
            <strong>Reasons</strong>
            <p>{[...(selectedDetail.message.reasons || []), ...(selectedDetail.message.local_reasons || [])].join(', ') || '-'}</p>
          </div>
          <div className="detail-section">
            <strong>Entities</strong>
            <pre>{JSON.stringify(selectedDetail.message.extracted_entities || {}, null, 2)}</pre>
          </div>
          <div className="detail-actions">
            <button className="btn btn-secondary" onClick={() => handleReview(selectedDetail.message.id, 'ignored')}>Ignore</button>
            <button className="btn btn-secondary" onClick={() => handleReview(selectedDetail.message.id, 'false_positive')}>False positive</button>
            <button className="btn btn-primary" onClick={() => handleReview(selectedDetail.message.id, 'confirmed_threat')}>Confirm threat</button>
          </div>
        </div>
      )}
    </div>
  );
}
