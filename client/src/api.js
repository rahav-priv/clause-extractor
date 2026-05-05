export async function fetchContracts() {
  const res = await fetch('/api/extractions')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return data.items ?? data
}

export async function fetchContract(id) {
  const res = await fetch(`/api/extractions/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function uploadContract(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/extract', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function deleteContract(id) {
  const res = await fetch(`/api/extractions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
