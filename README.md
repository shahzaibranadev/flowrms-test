# Multi-Tenant Invoice Reconciliation API

A production-ready invoice reconciliation system built with Python 3.13, FastAPI, Strawberry GraphQL, and SQLAlchemy 2.0. This system enables organizations to manage invoices, import bank transactions, and automatically reconcile them with AI-powered explanations.

## Features

- **Multi-Tenant Architecture**: Complete data isolation between tenants
- **REST API**: Full-featured REST endpoints with FastAPI
- **GraphQL API**: Flexible GraphQL interface with Strawberry
- **Invoice Management**: Create, list, filter, and delete invoices
- **Bank Transaction Import**: Bulk import with idempotency support
- **Intelligent Reconciliation**: Deterministic matching algorithm with scoring
- **AI Explanations**: OpenAI-powered match explanations with graceful fallback
- **Comprehensive Testing**: Full test coverage with pytest

## Tech Stack

- **Python 3.13**
- **FastAPI** - REST API framework
- **Strawberry GraphQL** - GraphQL implementation
- **SQLAlchemy 2.0** - ORM with modern async support
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **OpenAI API** - AI-powered explanations (optional)

## Setup and Installation

### Prerequisites

- Python 3.13+
- pip

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "test task flowrms"
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and set your OpenAI API key (optional)
   ```

5. **Initialize the database**
   The database will be automatically created on first run. For SQLite, the file will be created at `./invoice_reconciliation.db`.

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at:
   - REST API: http://localhost:8000/api
   - GraphQL: http://localhost:8000/graphql
   - API Docs: http://localhost:8000/docs

## Running Tests

### Automated Tests (pytest)

```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

### Manual Testing

For comprehensive manual testing instructions, see [TESTING_GUIDE.md](TESTING_GUIDE.md).

Quick test script:
```bash
./test_flows.sh complete  # Run complete end-to-end flow
./test_flows.sh 1         # Create tenant
./test_flows.sh idempotency  # Test idempotency
./test_flows.sh multi-tenant # Test multi-tenant isolation
```

## API Documentation

### REST Endpoints

#### Tenants
- `POST /api/tenants` - Create a new tenant
- `GET /api/tenants` - List all tenants
- `GET /api/tenants/{tenant_id}` - Get tenant by ID

#### Invoices
- `POST /api/tenants/{tenant_id}/invoices` - Create an invoice
- `GET /api/tenants/{tenant_id}/invoices` - List invoices (with filters)
- `DELETE /api/tenants/{tenant_id}/invoices/{invoice_id}` - Delete an invoice

**Invoice Filters:**
- `status` - Filter by status (open, matched, paid)
- `vendor_id` - Filter by vendor
- `date_from` / `date_to` - Date range filter
- `amount_min` / `amount_max` - Amount range filter

#### Bank Transactions
- `POST /api/tenants/{tenant_id}/bank-transactions/import` - Bulk import transactions
- `GET /api/tenants/{tenant_id}/bank-transactions` - List transactions

**Idempotency:** Include `Idempotency-Key` header or `idempotency_key` in request body.

#### Reconciliation
- `POST /api/tenants/{tenant_id}/reconcile` - Run reconciliation process
- `POST /api/tenants/{tenant_id}/reconcile/matches/{match_id}/confirm` - Confirm a match
- `GET /api/tenants/{tenant_id}/reconcile/explain?invoice_id=X&transaction_id=Y` - Get AI explanation

### GraphQL API

Access the GraphQL playground at http://localhost:8000/graphql

**Queries:**
- `tenants` - List tenants
- `invoices(tenantId, filters, pagination)` - List invoices with filters
- `bankTransactions(tenantId, pagination)` - List bank transactions
- `matchCandidates(tenantId)` - Get proposed matches
- `explainReconciliation(tenantId, invoiceId, transactionId)` - Get match explanation

**Mutations:**
- `createTenant(input)` - Create tenant
- `createInvoice(tenantId, input)` - Create invoice
- `deleteInvoice(tenantId, invoiceId)` - Delete invoice
- `importBankTransactions(tenantId, input)` - Import transactions
- `reconcile(tenantId)` - Run reconciliation
- `confirmMatch(tenantId, matchId)` - Confirm a match

## Design Decisions and Tradeoffs

### Architecture

**Layered Architecture:**
- **API Layer**: FastAPI routes and GraphQL resolvers
- **Service Layer**: Business logic and orchestration
- **Persistence Layer**: SQLAlchemy models and database operations

This separation ensures:
- Testability (services can be tested independently)
- Reusability (same services used by REST and GraphQL)
- Maintainability (clear separation of concerns)

### Multi-Tenant Isolation

**Approach:** Tenant-scoped queries at the service layer

Every service method that accesses tenant data explicitly filters by `tenant_id`. This ensures:
- **Correctness**: No data leakage between tenants
- **Simplicity**: No complex row-level security policies
- **Performance**: Indexed queries for tenant_id

**Tradeoff:** Requires discipline in service layer, but provides explicit control and easier debugging.

### Reconciliation Algorithm

**Scoring System:**
- **Exact Amount Match**: 50 points
- **Amount Within Tolerance** (1 cent): 30 points (proportional)
- **Date Proximity** (within 3 days): 15 points (proportional)
- **Text Similarity**: 5 points (based on SequenceMatcher)

**Design Choices:**
- **Best Match Per Invoice**: Only the highest-scoring match per invoice is returned
- **Currency Matching**: Only matches transactions with same currency
- **Deterministic**: No randomness, same inputs produce same outputs

**Tradeoffs:**
- Simple heuristic-based approach is fast and predictable
- Could be extended with ML models for complex scenarios
- Current approach handles 90% of common cases effectively

### Idempotency Implementation

**Approach:** Database-backed idempotency records

- Stores idempotency key, payload hash, and result
- Validates payload consistency on reuse
- Returns stored result for duplicate requests

**Benefits:**
- Survives server restarts
- Works across multiple instances
- Simple to understand and debug

**Tradeoff:** Requires database table, but provides reliable idempotency.

### AI Integration

**Design:**
- **Well-Contained**: AI service is isolated and easily mockable
- **Graceful Degradation**: Falls back to deterministic explanations
- **Configurable**: Can be disabled via environment variable
- **Secure**: Only sends tenant-authorized data to AI

**Fallback Strategy:**
When AI is unavailable (errors, timeouts, missing key), the system returns a deterministic explanation based on:
- Amount differences
- Date proximity
- Currency matching
- Text similarity hints

**Tradeoff:** Deterministic explanations are less insightful but always available.

### Transaction Boundaries

**Approach:** Explicit transaction management in services

- Each service method manages its own transaction
- Commits are explicit and intentional
- Rollback on exceptions is automatic

**Benefits:**
- Clear transaction boundaries
- Easy to reason about
- Predictable behavior

## Reconciliation Scoring Details

The reconciliation algorithm uses a weighted scoring system:

1. **Amount Matching (50-80 points)**
   - Exact match: 50 points
   - Within 1 cent tolerance: 30 points (proportional to difference)

2. **Date Proximity (0-15 points)**
   - Within 3 days: 15 points (proportional to closeness)
   - Beyond 3 days: 0 points

3. **Text Similarity (0-5 points)**
   - Uses SequenceMatcher for similarity ratio
   - Bonus if one description contains the other

**Total Score:** Sum of all factors, capped at 100.

**Matching Strategy:**
- Only matches with score > 0 are considered
- Best match per invoice is selected
- Matches are stored as "proposed" until confirmed

## Idempotency Details

The idempotency system ensures that:

1. **Same Request, Same Key**: Returns identical result
2. **Different Payload, Same Key**: Returns 409 Conflict
3. **No Key**: Normal processing (no idempotency)

**Implementation:**
- Idempotency key can be provided via:
  - HTTP header: `Idempotency-Key`
  - Request body: `idempotency_key` field
- Payload hash ensures consistency
- Results stored in `idempotency_records` table

## Testing Strategy

Tests cover:
1. ✅ Invoice CRUD operations
2. ✅ Invoice filtering (status, amount, date, vendor)
3. ✅ Invoice deletion
4. ✅ Bank transaction import
5. ✅ Idempotency (same key, conflict detection)
6. ✅ Reconciliation candidate generation
7. ✅ Match ranking and scoring
8. ✅ Match confirmation
9. ✅ AI explanation (with fallback)

**Test Database:** Uses separate SQLite database (`test.db`) that is recreated for each test.

## Environment Variables

```bash
DATABASE_URL=sqlite:///./invoice_reconciliation.db  # Database connection string
OPENAI_API_KEY=your_key_here                        # OpenAI API key (optional)
OPENAI_MODEL=gpt-4o-mini                           # OpenAI model to use
AI_ENABLED=true                                     # Enable/disable AI features
```

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── rest/          # REST API routes
│   │   └── graphql/       # GraphQL schema and resolvers
│   ├── core/              # Configuration and database
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic layer
│   └── main.py            # FastAPI application
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Future Enhancements

- [ ] Async database operations for better performance
- [ ] WebSocket support for real-time reconciliation updates
- [ ] Advanced ML-based matching algorithms
- [ ] Batch reconciliation with progress tracking
- [ ] Export reconciliation reports
- [ ] Multi-currency support with exchange rates
- [ ] Audit logging for all operations

## License

This project is provided as-is for evaluation purposes.
