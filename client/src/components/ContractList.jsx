const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path
      d="M1.75 3.5h10.5M5.25 3.5V2.333a.583.583 0 0 1 .583-.583h2.334a.583.583 0 0 1 .583.583V3.5m1.75 0-.583 7.583a.583.583 0 0 1-.584.584H4.667a.583.583 0 0 1-.584-.584L3.5 3.5"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const PlusIcon = () => (
  <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
    <path d="M5.5 1v9M1 5.5h9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
)

function formatDate(isoString) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch {
    return ''
  }
}

export default function ContractList({ contracts, selectedId, onSelect, onAdd, onDelete }) {
  return (
    <div className="panel panel-contracts">
      <div className="panel-header">
        <span>Contracts</span>
        <button className="btn-add" onClick={onAdd}>
          <PlusIcon />
          Add
        </button>
      </div>

      <div className="panel-body">
        {contracts.length === 0 ? (
          <div className="empty">
            <span className="icon">📂</span>
            <span>No contracts yet</span>
          </div>
        ) : (
          contracts.map(c => {
            const ext = c.filename.includes('.')
              ? c.filename.split('.').pop().toUpperCase()
              : '?'
            return (
              <div
                key={c.id}
                className={`contract-item${selectedId === c.id ? ' active' : ''}`}
                onClick={() => onSelect(c.id)}
              >
                <div className="contract-info">
                  <div className="name" title={c.filename}>{c.filename}</div>
                  <div className="meta">
                    <span className="fmt">{ext}</span>
                    {formatDate(c.upload_date)}
                  </div>
                </div>
                <button
                  className="btn-delete"
                  title="Delete contract"
                  onClick={e => {
                    e.stopPropagation()
                    onDelete({ id: c.id, filename: c.filename })
                  }}
                >
                  <TrashIcon />
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
