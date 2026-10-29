import { useState, useEffect } from 'react';
import { fetchGraph } from '../api/client';

export default function GraphView() {
  const [graphData, setGraphData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGraph()
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (error) {
    return <div className="error-banner">⚠ {error}</div>;
  }

  if (loading) {
    return <div className="loading-state">Graf ma'lumotlari yuklanmoqda…</div>;
  }

  const edges = graphData?.nodes_and_edges || [];

  if (edges.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-icon">🕸️</span>
        <p>Hozircha graf ma'lumotlari yo'q</p>
      </div>
    );
  }

  // Extract unique nodes
  const nodesMap = new Map();
  edges.forEach((edge) => {
    const srcKey = JSON.stringify(edge.source);
    const tgtKey = JSON.stringify(edge.target);
    if (!nodesMap.has(srcKey)) {
      nodesMap.set(srcKey, { ...edge.source, _key: srcKey });
    }
    if (!nodesMap.has(tgtKey)) {
      nodesMap.set(tgtKey, { ...edge.target, _key: tgtKey });
    }
  });

  const getNodeLabel = (node) => {
    return node.name || node.username || node.url || node.id || 'Noma\'lum';
  };

  const getNodeType = (node) => {
    if (node.username) return 'User';
    if (node.url) return 'Link';
    return 'Channel';
  };

  return (
    <div className="graph-section">
      <div className="graph-summary">
        <div className="stat-card compact">
          <span className="stat-value">{nodesMap.size}</span>
          <span className="stat-label">Obyektlar</span>
        </div>
        <div className="stat-card compact">
          <span className="stat-value">{edges.length}</span>
          <span className="stat-label">Bog'lanishlar</span>
        </div>
      </div>

      <div className="graph-panels">
        {/* Nodes table */}
        <div className="graph-panel">
          <h3>Obyektlar</h3>
          <div className="table-wrap">
            <table className="data-table compact-table">
              <thead>
                <tr>
                  <th>Turi</th>
                  <th>Nomi</th>
                </tr>
              </thead>
              <tbody>
                {[...nodesMap.values()].map((node, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className={`badge badge-node badge-${getNodeType(node).toLowerCase()}`}>
                        {getNodeType(node)}
                      </span>
                    </td>
                    <td className="cell-text">{getNodeLabel(node)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Edges table */}
        <div className="graph-panel">
          <h3>Munosabatlar</h3>
          <div className="table-wrap">
            <table className="data-table compact-table">
              <thead>
                <tr>
                  <th>Manba</th>
                  <th>Bog'lanish</th>
                  <th>Maqsad</th>
                </tr>
              </thead>
              <tbody>
                {edges.map((edge, idx) => (
                  <tr key={idx}>
                    <td className="cell-text">{getNodeLabel(edge.source)}</td>
                    <td>
                      <span className="badge badge-rel">{edge.relationship}</span>
                    </td>
                    <td className="cell-text">{getNodeLabel(edge.target)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
