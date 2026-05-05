import { useEffect, useRef } from 'react'

function HighlightedText({ text, clause }) {
  const highlightRef = useRef(null)

  // Scroll to highlighted clause when it changes
  useEffect(() => {
    if (highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [clause?.id])

  if (!text) return null

  const hasSpan =
    clause &&
    clause.span_start != null &&
    clause.span_end != null &&
    clause.span_end > clause.span_start

  if (!hasSpan) {
    return <div className="doc-text">{text}</div>
  }

  const before = text.slice(0, clause.span_start)
  const highlighted = text.slice(clause.span_start, clause.span_end)
  const after = text.slice(clause.span_end)

  return (
    <div className="doc-text">
      {before}
      <span className="highlight" ref={highlightRef}>
        {highlighted}
      </span>
      {after}
    </div>
  )
}

export default function DocumentViewer({ contract, selectedClause, loading }) {
  if (loading) {
    return (
      <div className="panel panel-document">
        <div className="panel-body">
          <div className="empty">
            <div className="spinner" />
            <span>Extracting clauses…</span>
          </div>
        </div>
      </div>
    )
  }

  if (!contract) {
    return (
      <div className="panel panel-document">
        <div className="panel-body">
          <div className="empty">
            <span className="icon">📄</span>
            <span>Select a contract to view</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="panel panel-document">
      <div className="doc-toolbar">
        <span className="doc-title">{contract.filename}</span>
        {contract.contract_type && (
          <span className="pill">{contract.contract_type}</span>
        )}
        {contract.contract_type_confidence != null && (
          <span className="pill">
            {Math.round(contract.contract_type_confidence * 100)}% confidence
          </span>
        )}
        <span className="pill">{contract.clauses.length} clauses</span>
      </div>

      <div className="panel-body">
        <HighlightedText text={contract.raw_text} clause={selectedClause} />
      </div>
    </div>
  )
}
