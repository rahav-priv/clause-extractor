import { useState, useEffect, useCallback } from 'react'
import ContractList from './components/ContractList'
import DocumentViewer from './components/DocumentViewer'
import ClausesPanel from './components/ClausesPanel'
import AddContractModal from './components/AddContractModal'
import DeleteConfirmModal from './components/DeleteConfirmModal'
import { fetchContracts, fetchContract, deleteContract, uploadContract } from './api'

export default function App() {
  const [contracts, setContracts] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selectedContract, setSelectedContract] = useState(null)
  const [selectedClauseIdx, setSelectedClauseIdx] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null) // { id, filename }
  const [loadingContract, setLoadingContract] = useState(false)

  // ── Load contract list ─────────────────────────────────────────────────────
  const loadContracts = useCallback(async () => {
    try {
      const data = await fetchContracts()
      setContracts(data)
    } catch (e) {
      console.error('Failed to load contracts:', e)
    }
  }, [])

  useEffect(() => { loadContracts() }, [loadContracts])

  // ── Load selected contract details ─────────────────────────────────────────
  useEffect(() => {
    if (!selectedId) {
      setSelectedContract(null)
      setSelectedClauseIdx(null)
      return
    }
    setLoadingContract(true)
    setSelectedContract(null)
    setSelectedClauseIdx(null)
    fetchContract(selectedId)
      .then(data => {
        setSelectedContract(data)
        setSelectedClauseIdx(data.clauses.length > 0 ? 0 : null)
      })
      .catch(e => console.error('Failed to load contract:', e))
      .finally(() => setLoadingContract(false))
  }, [selectedId])

  // ── Upload ─────────────────────────────────────────────────────────────────
  async function handleUpload(file) {
    const contract = await uploadContract(file)
    await loadContracts()
    setSelectedId(contract.id)
    setShowAddModal(false)
  }

  // ── Delete ─────────────────────────────────────────────────────────────────
  async function handleDelete() {
    if (!deleteTarget) return
    await deleteContract(deleteTarget.id)
    if (selectedId === deleteTarget.id) {
      setSelectedId(null)
      setSelectedContract(null)
    }
    setDeleteTarget(null)
    await loadContracts()
  }

  const selectedClause =
    selectedClauseIdx !== null && selectedContract
      ? selectedContract.clauses[selectedClauseIdx]
      : null

  return (
    <>
      <header>
        <h1>Contract Intelligence</h1>
        <span className="badge">AI</span>
      </header>

      <div className="layout">
        <ContractList
          contracts={contracts}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onAdd={() => setShowAddModal(true)}
          onDelete={setDeleteTarget}
        />

        <DocumentViewer
          contract={selectedContract}
          selectedClause={selectedClause}
          loading={loadingContract}
        />

        <ClausesPanel
          contract={selectedContract}
          selectedClauseIdx={selectedClauseIdx}
          onSelectClause={setSelectedClauseIdx}
        />
      </div>

      {showAddModal && (
        <AddContractModal
          onClose={() => setShowAddModal(false)}
          onUpload={handleUpload}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmModal
          filename={deleteTarget.filename}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </>
  )
}
