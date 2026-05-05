import { useState, useRef } from 'react'

const DOCX_MSG = 'DOCX files are not implemented yet. Please upload a PDF.'

export default function AddContractModal({ onClose, onUpload }) {
  const [selectedSource, setSelectedSource] = useState(null)
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  function pickSource(src) {
    if (src !== 'local') return // others are TBD
    setSelectedSource('local')
    setFile(null)
    setError(null)
  }

  function applyFile(f) {
    setFile(f)
    setError(null)
    const ext = f.name.split('.').pop().toLowerCase()
    if (ext === 'docx' || ext === 'doc') {
      setError(DOCX_MSG)
    }
  }

  function clearFile() {
    setFile(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleFileInput(e) {
    const f = e.target.files[0]
    if (f) applyFile(f)
  }

  function handleDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }
  function handleDragLeave() { setDragOver(false) }
  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) applyFile(f)
  }

  async function doUpload() {
    if (!file || uploading) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (ext === 'docx' || ext === 'doc') { setError(DOCX_MSG); return }
    setUploading(true)
    setError(null)
    try {
      await onUpload(file)
      // onUpload calls onClose on success — nothing else needed here
    } catch (e) {
      setError(e.message || 'Upload failed')
      setUploading(false)
    }
  }

  const ext = file ? file.name.split('.').pop().toLowerCase() : null
  const isDocx = ext === 'docx' || ext === 'doc'
  const canUpload = file && !isDocx && !uploading

  return (
    <div
      className="modal-overlay"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="modal">

        {/* Header */}
        <div className="modal-head">
          <h2>Add Contract</h2>
          <button className="modal-close" onClick={onClose} disabled={uploading}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4 4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
            Choose a source to import from:
          </p>

          {/* Local file */}
          <div
            className={`source-option${selectedSource === 'local' ? ' selected' : ''}`}
            onClick={() => pickSource('local')}
          >
            <div className="source-icon icon-local">📄</div>
            <div className="source-text">
              <div className="source-title">Local File</div>
              <div className="source-desc">Upload a PDF from your computer</div>
            </div>
          </div>

          {/* Google Drive – TBD */}
          <div className="source-option disabled">
            <div className="source-icon icon-gdocs">📝</div>
            <div className="source-text">
              <div className="source-title">Google Drive</div>
              <div className="source-desc">Import directly from your Google Drive</div>
            </div>
            <span className="coming-soon">Coming soon</span>
          </div>

          {/* Git – TBD */}
          <div className="source-option disabled">
            <div className="source-icon icon-git">🔗</div>
            <div className="source-text">
              <div className="source-title">Git Repository</div>
              <div className="source-desc">Pull contracts from a Git repo path</div>
            </div>
            <span className="coming-soon">Coming soon</span>
          </div>

          {/* URL – TBD */}
          <div className="source-option disabled">
            <div className="source-icon icon-url">🌐</div>
            <div className="source-text">
              <div className="source-title">URL</div>
              <div className="source-desc">Import from a direct link</div>
            </div>
            <span className="coming-soon">Coming soon</span>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />

          {/* Drop zone — shown once "Local File" is selected and no file chosen yet */}
          {selectedSource === 'local' && !file && (
            <div
              className={`dropzone${dragOver ? ' drag-over' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="dz-icon">📂</div>
              <div className="dz-label">
                Drop your file here or{' '}
                <span className="dz-browse">browse</span>
              </div>
              <div className="dz-sub">Supported: PDF · max 50 MB</div>
            </div>
          )}

          {/* File chosen */}
          {file && (
            <div className="file-selected">
              <span className="fs-icon">{isDocx ? '📘' : '📕'}</span>
              <span className="fs-name">{file.name}</span>
              {!uploading && (
                <button className="fs-clear" title="Remove" onClick={clearFile}>✕</button>
              )}
            </div>
          )}

          {/* Error message */}
          {error && <div className="upload-error">{error}</div>}

          {/* Upload progress */}
          {uploading && (
            <div className="upload-status">
              <div className="spinner" />
              Uploading and extracting clauses…
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-cancel" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button
            className={`btn-upload${canUpload ? ' ready' : ''}`}
            onClick={doUpload}
          >
            Upload
          </button>
        </div>

      </div>
    </div>
  )
}
