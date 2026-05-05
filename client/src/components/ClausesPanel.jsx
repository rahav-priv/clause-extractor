// Maps clause type → CSS color class
const CLAUSE_COLOR = {
  // Group 1 – Identity
  Parties: 'governing',
  'Agreement Date': 'governing',
  'Effective Date': 'governing',
  'Expiration Date': 'governing',
  'Governing Law': 'governing',
  // Group 2 – Purpose & scope
  Purpose: 'governing',
  'Scope of Services': 'payment',
  'Statements of Work': 'payment',
  Delivery: 'payment',
  // Group 3 – Commercial
  'Payment Terms': 'payment',
  'Price Restrictions': 'payment',
  'Most Favored Nation': 'payment',
  // Group 4 – Duration
  'Renewal Term': 'termination',
  'Termination for Convenience': 'termination',
  'Post-Termination Services': 'termination',
  // Group 5 – Liability
  Indemnification: 'liability',
  'Cap on Liability': 'liability',
  'Uncapped Liability': 'liability',
  Warranties: 'liability',
  'Force Majeure': 'liability',
  // Group 6 – Confidentiality
  'Confidentiality / NDA': 'confidentiality',
  'Definition of Confidential Information': 'confidentiality',
  'Exclusions from Confidential Information': 'confidentiality',
  'Obligations of Receiving Party': 'confidentiality',
  'Data Privacy / GDPR': 'confidentiality',
  // Group 7 – IP
  'IP Ownership Assignment': 'ip',
  'License Grant': 'ip',
  'Source Code Escrow': 'ip',
  // Group 8 – Restrictive
  'Non-Compete': 'termination',
  'No-Solicit of Employees': 'termination',
  // Group 9 – Governance
  'Dispute Resolution': 'governing',
  'Change of Control': 'governing',
  'Audit Rights': 'governing',
  'SLA / Service Levels': 'payment',
  // Group 10 – Remedies & enforcement
  Remedies: 'liability',
  'Injunctive Relief': 'liability',
  // Group 11 – Boilerplate
  'Entire Agreement': 'governing',
  Amendment: 'governing',
  Severability: 'governing',
  Notices: 'governing',
  Assignment: 'governing',
  Waiver: 'governing',
  Other: 'governing',
}

function formatValue(val) {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'object') {
    // Pretty-print simple objects on one line
    return Object.entries(val)
      .map(([k, v]) => `${k}: ${v}`)
      .join(' · ')
  }
  return String(val)
}

export default function ClausesPanel({ contract, selectedClauseIdx, onSelectClause }) {
  const selectedClause =
    selectedClauseIdx !== null && contract
      ? contract.clauses[selectedClauseIdx]
      : null

  if (!contract) {
    return (
      <div className="panel panel-right">
        <div className="panel-header"><span>Clauses</span></div>
        <div className="panel-body">
          <div className="empty">
            <span className="icon">📋</span>
            <span>No contract selected</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="panel panel-right">
      <div className="panel-header"><span>Clauses</span></div>

      {/* Clause list */}
      <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>
        {contract.clauses.length === 0 ? (
          <div className="empty"><span>No clauses extracted</span></div>
        ) : (
          contract.clauses.map((cl, idx) => {
            const color = CLAUSE_COLOR[cl.clause_type] || 'governing'
            return (
              <div
                key={cl.id}
                className={`clause-item${selectedClauseIdx === idx ? ' active' : ''}`}
                onClick={() => onSelectClause(idx)}
              >
                <div className="clause-title">
                  {idx + 1}. {cl.clause_type}
                </div>
                <div className="clause-type">
                  <span className={`clause-type-badge type-${color}`}>
                    {cl.clause_type}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Entity metadata for selected clause */}
      {selectedClause && (
        <div className="metadata-panel">
          <div className="panel-header" style={{ background: '#f9fafb' }}>
            <span>Entities — {selectedClause.clause_type}</span>
          </div>
          <div className="metadata-body">
            {/* Confidence row */}
            {selectedClause.confidence != null && (
              <div className="entity-row">
                <span className="entity-type">Confidence</span>
                <span className="entity-value">
                  {Math.round(selectedClause.confidence * 100)}%
                </span>
              </div>
            )}

            {/* Extracted entities */}
            {selectedClause.entities.length === 0 ? (
              <div style={{ fontSize: 12, color: '#9ca3af', padding: '8px 0' }}>
                No entities extracted
              </div>
            ) : (
              selectedClause.entities.map(e => (
                <div key={e.id} className="entity-row">
                  <span className="entity-type">{e.entity_name}</span>
                  <span className="entity-value">{formatValue(e.value)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
