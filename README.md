# Contract Intelligence

An AI-powered system that extracts and classifies clauses from legal contracts. Upload a PDF contract and get back a structured breakdown of the contract type, individual clauses, and their key entities — all powered by Claude.

---

## How It Works

```
PDF Upload → Text Extraction → Section Pre-parsing → Claude AI → Structured JSON → Database → UI
```

1. **PDF parsing** — `pdfplumber` extracts raw text from the uploaded PDF
2. **Section pre-parsing** — the text is split into numbered sections with exact character spans
3. **Claude extraction** — Claude classifies the contract type and each section into clause types, and extracts structured entities (amounts, dates, parties, etc.)
4. **Persistence** — results are stored in SQLite via SQLAlchemy
5. **UI** — a React frontend lets you browse contracts, view highlighted clauses, and inspect extracted entities

---

## Project Structure

```
clause_extractor/
├── server/
│   ├── main.py          # FastAPI app and route definitions
│   ├── models.py        # SQLAlchemy ORM models (Contract, Clause, Entity)
│   ├── database.py      # Database engine and session setup
│   ├── extractor.py     # Claude AI integration and prompt logic
│   ├── pdf_parser.py    # PDF text extraction
│   └── requirements.txt
├── client/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js       # API client functions
│   │   └── components/
│   └── package.json
├── Dockerfile           # Backend container
├── docker_run.ps1       # One-command Docker build + run (Windows)
└── .env.example         # Environment variable template
```

---

## Setup

### Prerequisites
- Docker Desktop
- Node.js 18+
- An Anthropic API key

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Run the backend (Docker)

```powershell
.\docker_run.ps1
```

The API will be available at `http://localhost:6363`.  
The database is stored at `./data/contracts.db` on your host machine.

### 3. Run the frontend

```powershell
cd client
npm install   # first time only
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## API Reference

Interactive Swagger docs are available at **http://localhost:6363/docs** when the server is running.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/extractions` | List all contracts (paginated) |
| `GET` | `/api/extractions/{id}` | Get a contract with all clauses and entities |
| `POST` | `/api/extract` | Upload a PDF and extract clauses |
| `DELETE` | `/api/extractions/{id}` | Delete a contract and all its data |

### POST /api/extract

- **Input**: multipart/form-data with a `file` field (PDF only, max 20 MB)
- **Output**: full contract object with contract type, clauses, and entities
- **Errors**: 400 (unsupported type), 413 (too large), 422 (unreadable PDF), 500 (extraction error)

### Example response

```json
{
  "id": 1,
  "filename": "msa_1.pdf",
  "contract_type": "MSA",
  "contract_type_confidence": 0.97,
  "clauses": [
    {
      "clause_type": "Payment Terms",
      "confidence": 0.95,
      "evidence": ["monthly fee of $15,000", "due within 30 days of invoice"],
      "entities": {
        "amount": { "value": 15000, "currency": "USD", "frequency": "monthly" }
      }
    }
  ]
}
```

---

## AI Usage

Claude was used throughout the development of this project, both as a tool embedded in the product and as a development assistant.

### In the product

- **Prompt engineering** (`server/extractor.py`): the extraction prompt was designed iteratively. Key decisions:
  - Pre-parsing the contract into numbered sections before sending to Claude, so Claude returns section indices rather than guessing character spans — this gives exact, reliable highlights in the UI
  - Splitting NDA confidentiality clauses into four distinct sub-types for more precise extraction
  - Enforcing JSON-only output via the system prompt, with a fallback regex parser for cases where Claude wraps output in markdown fences
  - Using a module-level Anthropic client singleton to avoid reconnecting on every request

### In development

- **Architecture decisions**: discussed the overall pipeline design (pre-parsing vs. raw text), database schema, and API structure with Claude
- **Code review**: Claude identified the `contracts.map is not a function` bug (paginated API response not unwrapped in the frontend), the missing file size limit, cryptic helper function names (`_j`, `_jv`), and the Anthropic client being recreated on every call
- **Docker setup**: Claude helped diagnose WSL bash issues on Windows and created the PowerShell-based `docker_run.ps1`
- **Bug fixes**: Claude found that the frontend `api.js` was passing the full paginated response object to `contracts.map()` instead of extracting `.items`

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Your Anthropic API key |
| `CLAUSE_EXTRACTOR_PORT` | No | `6363` | Port the backend listens on |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-5-20250929` | Claude model to use |
| `DATABASE_URL` | No | `/data/contracts.db` | SQLite database path |
