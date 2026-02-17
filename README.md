# Multi-Tenant Invoice Reconciliation API

A multi-tenant invoice reconciliation system built with Python 3.13, FastAPI, Strawberry GraphQL, and SQLAlchemy 2.0.

## Setup and Run Instructions

### Prerequisites
- Python 3.13+
- pip

### Installation

1. **Clone and navigate to the project**
   ```bash
   git clone <repository-url>
   cd flowrms-test
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```
   
   API available at:
   - REST API: http://localhost:8000/api
   - GraphQL: http://localhost:8000/graphql
   - API Docs: http://localhost:8000/docs

4. **Database**: SQLite database is automatically created on first run at `./invoice_reconciliation.db`

## Running Tests

```bash
pytest
```

Tests cover: invoice CRUD, filtering, deletion, bank transaction import, idempotency, reconciliation, match confirmation, and AI explanations (with fallback).

## Key Design Decisions and Tradeoffs

### Architecture
**Layered Architecture**: API → Service → Persistence layers ensure testability, reusability (REST and GraphQL share services), and maintainability.

### Multi-Tenant Isolation
**Approach**: Tenant-scoped queries at the service layer. Every service method explicitly filters by `tenant_id`.

**Tradeoff**: Requires discipline in service layer, but provides explicit control and easier debugging compared to row-level security policies.

### Transaction Boundaries
**Approach**: Explicit transaction management in services. Each service method manages its own transaction with explicit commits.

**Benefit**: Clear boundaries, predictable behavior, automatic rollback on exceptions.

### AI Integration
**Design**: Well-contained AI service with graceful degradation. Falls back to deterministic explanations when AI is unavailable.

**Tradeoff**: Deterministic explanations are less insightful but always available, ensuring the system never fails due to AI issues.

## Reconciliation Scoring

The reconciliation algorithm uses a weighted scoring system:

- **Exact Amount Match**: 50 points
- **Amount Within Tolerance** (1 cent): 30 points (proportional)
- **Date Proximity** (within 3 days): 15 points (proportional)
- **Text Similarity**: 5 points (SequenceMatcher)

**Total Score**: Sum of all factors, capped at 100.

**Matching Strategy**:
- Only matches with score > 20 are considered (weak matches filtered)
- Best match per invoice is selected
- Currency must match
- Deterministic: same inputs produce same outputs

**Tradeoff**: Simple heuristic-based approach is fast and predictable, handles 90% of common cases. Could be extended with ML for complex scenarios.

## Idempotency

**Approach**: Database-backed idempotency records.

**Implementation**:
- Stores idempotency key, payload hash, and result in `idempotency_records` table
- Validates payload consistency on reuse
- Returns stored result for duplicate requests
- Returns 409 Conflict if same key used with different payload

**Benefits**:
- Survives server restarts
- Works across multiple instances
- Simple to understand and debug

**Tradeoff**: Requires database table, but provides reliable idempotency compared to in-memory solutions.

**Usage**: Include `Idempotency-Key` header or `idempotency_key` in request body when importing bank transactions.
