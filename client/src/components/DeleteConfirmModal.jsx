export default function DeleteConfirmModal({ filename, onCancel, onConfirm }) {
  return (
    <div
      className="confirm-overlay"
      onClick={e => { if (e.target === e.currentTarget) onCancel() }}
    >
      <div className="confirm-dialog">
        <div className="cd-icon">🗑️</div>
        <h3>Delete contract?</h3>
        <p>
          This will permanently remove <strong>{filename}</strong>.
          This action cannot be undone.
        </p>
        <div className="confirm-actions">
          <button className="btn-confirm-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn-confirm-delete" onClick={onConfirm}>
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
