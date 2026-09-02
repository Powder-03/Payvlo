# 🌐 Payvlo — Universal Agentic Commerce Node (MCP + UAP / A2A)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20Hexagonal-orange.svg)]()
[![Protocols](https://img.shields.io/badge/Protocols-MCP%20%7C%20UAP%20A2A-purple.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Deployment](https://img.shields.io/badge/Deploy-Render%20Ready-black.svg)](https://render.com/)

A production-ready, serverless **Universal Agentic Commerce Node** built in Python adhering to **Clean Architecture (Hexagonal Architecture)**.

Payvlo acts as a dual-interface gateway for **ANY merchant** (Shopify D2C brands, Domino's Pizza, BeastLife Nutrition, Havells Tech, or custom REST APIs), enabling both tool-calling AI agents and autonomous peer-to-peer buyer agents to discover catalogs, negotiate bounded pricing, and settle transactions safely.

---

## 📑 Table of Contents
1. [Core Features & Value Proposition](#-core-features)
2. [System Architecture (Hexagonal / Clean)](#-system-architecture)
3. [Dual Protocol Gateway (MCP + UAP/A2A)](#-dual-protocol-gateway)
4. [Dynamic Merchant Onboarding & Catalog Sync](#-dynamic-merchant-onboarding--sync)
5. [Zero-Trust Security & Bounded Gatekeeper](#-zero-trust-security--guardrails)
6. [API & Tool Reference](#-api--tool-reference)
7. [Quickstart & Local Testing](#-quickstart--local-testing)
8. [Automated E2E Test Suite](#-automated-e2e-test-suite)
9. [Production Deployment (Render & Docker)](#-production-deployment)

---

## ⚡ Core Features

* **Dual-Interface Agent Gateway:**
  * **MCP (Model Context Protocol):** Connect tool-calling agents (**Claude Desktop**, **Cursor IDE**, **OpenAI Swarm**, AutoGPT) over FastMCP SSE and JSON-RPC.
  * **UAP / A2A (Universal Agent Protocol):** Peer-to-peer autonomous buyer agents discover capabilities (`/.well-known/agent.json`), negotiate intent (`/uap/v1/negotiate`), and settle orders (`/uap/v1/transact`).
* **Dynamic Merchant Onboarding:**
  * Ingest and sync catalogs dynamically from **Shopify** (`/products.json`), **Custom REST APIs** with JSON field mapping, or direct JSON payloads.
  * Multi-tenant store isolation with independent discount ceilings, transaction caps, and agent cards.
* **Deterministic Guardrails & Gatekeeper:**
  * **Deterministic Discount Clamping:** Pure mathematical constraint $\min(\text{requested}, \text{product.max}, \text{merchant.max})$ to prevent prompt injection and hallucinated discounts.
  * **Sub-ms Atomic Spend Cap Gate:** Atomic Redis Lua scripts enforcing user budget limits and 24h merchant spend caps.
  * **24-Hour Idempotency Defense:** Zero double-charge guarantee on replayed transactions.
  * **Privacy-Preserving Audit Ledger:** Masked PII (redacted phone, email, address) and SHA-256 pseudonymized buyer IDs.
  * **Financial Rails:** Integrated with Razorpay Sandbox Test Mode rails with mock fallback simulator.

---

## 🏛️ System Architecture

Payvlo strictly follows **Hexagonal / Clean Architecture**. Domain business logic has **zero external dependencies**, decoupled from web frameworks, databases, and payment gateways.

```
                              ┌──────────────────────────────────────────────┐
                              │                 AGENT CLIENTS                │
                              │   Claude Desktop / Cursor / Swarm / A2A      │
                              └───────────────┬──────────────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │                                               │
             [MCP over SSE / JSON-RPC]                      [UAP / A2A HTTP API]
             /sse, /mcp/tools, /mcp/call              /.well-known/agent.json, /uap/v1/*
                      │                                               │
    ══════════════════╪═══════════════════════════════════════════════╪══════════════════
    ADAPTERS LAYER    │                                               │
                      ▼                                               ▼
             ┌─────────────────┐                             ┌─────────────────┐
             │  MCPController  │                             │  UAPController  │
             └────────┬────────┘                             └────────┬────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
    ══════════════════════════════════════════╪══════════════════════════════════════════
    APPLICATION LAYER                         ▼
                             ┌──────────────────────────────────┐
                             │       APPLICATION USE CASES      │
                             │  • SearchCatalogUseCase          │
                             │  • RequestQuoteUseCase           │
                             │  • ExecuteCheckoutUseCase        │
                             │  • NegotiateIntentUseCase        │
                             │  • OnboardMerchantUseCase        │
                             │  • SyncMerchantCatalogUseCase    │
                             │  • InspectAuditUseCase           │
                             └────────────────┬─────────────────┘
                                              │
    ══════════════════════════════════════════╪══════════════════════════════════════════
    DOMAIN LAYER                              ▼
                             ┌──────────────────────────────────┐
                             │       DOMAIN ENTITIES & PORTS    │
                             │  • MerchantProfile, Product      │
                             │  • Quote, Order, AuditEntry      │
                             │  • ICatalogRepository            │
                             │  • IGatekeeper                   │
                             │  • IPaymentRail                  │
                             │  • ICatalogSyncProvider          │
                             └────────────────┬─────────────────┘
                                              │
    ══════════════════════════════════════════╪══════════════════════════════════════════
    INFRASTRUCTURE / EGRESS                   ▼
               ┌──────────────────────┬──────────────────────┬──────────────────────┐
               ▼                      ▼                      ▼                      ▼
     ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
     │  PostgreSQL/SQLite│  │ Redis Gatekeeper  │  │ Razorpay Rails    │  │ Catalog Sync      │
     │  SQLAlchemy ORM   │  │ Atomic Lua Caps   │  │ Test Mode Sandbox │  │ Shopify/REST APIs │
     └───────────────────┘  └───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Directory Layout (Modular Monolith)

```
payvlo/
├── src/
│   ├── domain/                         # Enterprise Domain (Bounded Contexts)
│   │   ├── auth/                       # User entities and IUserRepository port
│   │   ├── merchant/                   # MerchantProfile, CatalogSyncConfig, IMerchantRepository
│   │   ├── catalog/                    # Product, ICatalogRepository, ICatalogSyncProvider
│   │   ├── checkout/                   # Quote, Order, Address, IPaymentRail
│   │   ├── gatekeeper/                 # IGatekeeper port (Zero-Trust Spend Bounds)
│   │   ├── audit/                      # AuditEntry, IAuditRepository
│   │   ├── common/                     # Common domain timestamps & helpers
│   │   └── exceptions.py               # Domain exception hierarchy
│   │
│   ├── application/                    # Application Business Rules & Slices
│   │   ├── dto/                        # Domain-scoped DTOs (auth, catalog, checkout, etc.)
│   │   └── use_cases/                  # Single-purpose Use Case classes
│   │
│   ├── adapters/                       # Protocol & Egress Adapters
│   │   ├── db/                         # Modular database ORM models & repositories
│   │   │   ├── auth/                   # UserModel, PostgresUserRepository
│   │   │   ├── merchant/               # MerchantModel
│   │   │   ├── catalog/                # ProductModel, PostgresCatalogRepository
│   │   │   ├── checkout/               # QuoteModel, OrderModel
│   │   │   ├── audit/                  # AuditEntryModel, PostgresAuditRepository
│   │   │   └── base.py                 # SQLAlchemy Base
│   │   ├── sync_providers/             # Shopify, Custom REST, Direct, Dispatcher
│   │   ├── mcp/                        # FastMCP tool execution, JSON-RPC, SSE transport
│   │   ├── uap_controller.py           # UAP A2A protocol routes (/.well-known/agent.json, /negotiate, /transact)
│   │   ├── merchant_controller.py      # REST Ingress (/api/v1/merchants/onboard, /sync, list)
│   │   ├── auth_controller.py          # JWT authentication, signup, login
│   │   ├── webhook_controller.py       # Event-driven merchant webhooks
│   │   ├── redis_gatekeeper.py         # Upstash Redis / In-Memory adapter with atomic Lua spend scripts
│   │   └── razorpay_rails.py           # Razorpay SDK adapter with Sandbox test simulator
│   │
│   └── infrastructure/                 # Frameworks & Server Configuration
│       ├── config.py                   # Pydantic BaseSettings environment loader
│       ├── database.py                 # DB engine, sessionmaker, and schema migration
│       ├── scheduler.py                # Background auto-sync scheduler
│       └── server.py                   # FastAPI ASGI application assembler
│
├── tests/
│   ├── e2e/                            # Modularized E2E test suites (16 test steps)
│   │   ├── test_01_health_and_protocols.py
│   │   ├── test_02_discount_clamping.py
│   │   ├── test_03_spend_caps_and_checkout.py
│   │   ├── test_04_uap_a2a_protocol.py
│   │   ├── test_05_audit_ledger.py
│   │   ├── test_06_dynamic_onboarding.py
│   │   ├── test_07_merchant_saas_auth.py
│   │   └── test_08_webhooks_and_scheduler.py
│   └── test_harness.py                 # Master E2E test suite orchestrator
├── docker-compose.yml                  # PostgreSQL 15 + Redis 7 + Commerce Node container setup
├── Dockerfile                          # Multi-stage container build
├── render.yaml                         # One-click Render deployment blueprint
└── requirements.txt                    # Project dependencies
```

---

## ⚡ Dual Protocol Gateway

Payvlo provides two distinct entry points depending on the AI agent architecture:

### 1. Model Context Protocol (MCP) — Machine-to-Tool (M2T)
Used by tool-calling agents (**Claude Desktop**, **Cursor IDE**, **OpenAI Swarm**):
* **SSE Endpoint:** `GET /sse` (Real-time SSE event stream)
* **Tool Schema Discovery:** `GET /mcp/tools` (Returns standardized JSON-Schema definitions)
* **Direct JSON-RPC Execution:** `POST /mcp/call`

### 2. Universal Agent Protocol (UAP / A2A) — Agent-to-Agent (A2A)
Used by autonomous peer buyer agents communicating machine-to-machine:
* **Capability Card Discovery:** `GET /.well-known/agent.json?merchant_id=<id>`
* **Intent Negotiation:** `POST /uap/v1/negotiate` (Multi-turn intent negotiation and pricing agreements)
* **Signed Transaction Settlement:** `POST /uap/v1/transact` (Executes bounded order against Razorpay rails)

---

## 🛍️ Dynamic Merchant Onboarding & Sync

Payvlo is **not hardcoded to specific stores**. Any merchant can be onboarded on-the-fly via the API:

```
┌─────────────────────────┐     POST /api/v1/merchants/onboard     ┌─────────────────────────────┐
│  Shopify / REST API /   ├───────────────────────────────────────►│  Universal Agentic Node   │
│  Custom Brand Catalog   │                                        │  • Auto-creates Guardrails  │
└─────────────────────────┘                                        │  • Ingests & Normalizes     │
                                                                   │  • Generates Agent Card     │
                                                                   └──────────────┬──────────────┘
                                                                                  │
                                     Live for Autonomous Agents                   ▼
                            ┌────────────────────────────────────────────────────────────────────┐
                            │ • Discoverable via MCP (search_store_catalog)                      │
                            │ • Discoverable via UAP (GET /.well-known/agent.json?merchant_id=X) │
                            │ • Clamped & Bound Razorpay Checkout                                │
                            └────────────────────────────────────────────────────────────────────┘
```

Supported sync sources:
1. **Shopify Integration:** Pulls products directly from `{store_url}/products.json` or Shopify Admin API, transforming variants, inventory, tags, and prices into domain entities.
2. **Custom REST APIs:** Ingests external REST endpoints with custom bearer tokens and dynamic JSON key mappings (`title`, `price`, `sku`, `inventory`, `category`).
3. **Direct Payloads:** Bulk uploads product lists directly via JSON.

---

## 🛡️ Zero-Trust Security & Guardrails

| Guardrail | Mechanism | Guarantee |
|---|---|---|
| **Deterministic Clamping** | $\min(\text{requested}, \text{product.max}, \text{merchant.max})$ | Zero prompt-injection or hallucinated discounts |
| **Atomic Spend Gate** | Redis Lua (`LUA_SPEND_CAP_CHECK`) | Sub-ms check preventing single-tx and daily budget overruns |
| **24h Idempotency Defense** | Redis Lua (`LUA_IDEMPOTENCY_ACQUIRE`) + DB fallback | Replaying transactions returns existing orders with zero double-charge |
| **Privacy-Preserving Audit** | Masked phone (`+91-XXXXX-3210`), email (`bu***@domain`), and SHA-256 user hash | Append-only GDPR / DPDP-compliant ledger |
| **Inventory Locking** | `SELECT ... FOR UPDATE` (Pessimistic concurrency) | Prevents overselling during concurrent checkouts |

---

## 📖 API & Tool Reference

### MCP Tools (Callable via `POST /mcp/call`)

#### 1. `search_store_catalog`
Discover products across any merchant catalog:
```bash
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_store_catalog",
    "arguments": {
      "query": "Pizza",
      "merchant_id": "dominos_in"
    }
  }'
```

#### 2. `request_price_quote`
Request a bound quotation with deterministic discount clamping (e.g., requesting 50% discount on Domino's is clamped to 15%):
```bash
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "request_price_quote",
    "arguments": {
      "merchant_id": "dominos_in",
      "items": [{"product_id": "DOM-PIZ-001", "quantity": 1, "requested_discount_pct": 50.0}]
    }
  }'
```

#### 3. `execute_bounded_checkout`
Execute atomic checkout with spend cap validation and Razorpay order generation:
```bash
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "execute_bounded_checkout",
    "arguments": {
      "quote_id": "<QUOTE_ID>",
      "idempotency_key": "tx_uuid_998877",
      "user_id": "agent_claude_desktop",
      "max_spend_budget": 500.0,
      "shipping_address": {
        "line1": "Flat 402, Indiranagar",
        "city": "Bengaluru",
        "state": "KA",
        "postal_code": "560038",
        "phone": "+919876543210",
        "email": "buyer@example.com"
      },
      "merchant_id": "dominos_in"
    }
  }'
```

#### 4. `inspect_audit_trail`
Inspect masked privacy-preserving transaction history:
```bash
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "inspect_audit_trail",
    "arguments": {"merchant_id": "dominos_in", "limit": 5}
  }'
```

---

### Merchant Onboarding REST Endpoints

#### Onboard a Shopify Merchant
```bash
curl -X POST http://localhost:8000/api/v1/merchants/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "urban_threads",
    "merchant_name": "Urban Threads D2C Apparel",
    "category": "Apparel & Fashion",
    "currency": "INR",
    "max_discount_percentage": 20.0,
    "per_tx_spend_cap": 25000.0,
    "daily_merchant_spend_cap": 500000.0,
    "sync_config": {
      "provider": "shopify",
      "endpoint_url": "https://urban-threads-sample.myshopify.com",
      "access_token": "shpat_sample_token_123",
      "auto_sync": true
    }
  }'
```

#### Onboard a Custom REST API Merchant with Field Mapping
```bash
curl -X POST http://localhost:8000/api/v1/merchants/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "hyper_gear",
    "merchant_name": "HyperGear Electronics",
    "category": "Electronics",
    "currency": "INR",
    "max_discount_percentage": 10.0,
    "sync_config": {
      "provider": "custom_api",
      "endpoint_url": "https://api.hypergear.example/v2/catalog",
      "field_mapping": {
        "title": "item_title",
        "price": "mrp_inr",
        "sku": "product_code",
        "inventory": "stock_units"
      }
    }
  }'
```

---

## 🚀 Quickstart & Local Testing

### Method 1: Docker Compose (Recommended)
Spins up PostgreSQL 15, Redis 7, and the Commerce Node:

```bash
# 1. Build and start containers in the background
docker compose up --build -d

# 2. Check container health
docker compose ps

# 3. View live server logs
docker compose logs -f commerce-node
```

The node will be available at:
* **Interactive Landing Dashboard:** [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check:** [http://localhost:8000/healthz](http://localhost:8000/healthz)

---

### Method 2: Standalone Python (Local Virtualenv)
No Docker required. Uses local SQLite and in-memory Gatekeeper automatically:

```bash
# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Automated E2E Test Suite

The test suite at [`tests/test_harness.py`](file:///c:/Users/risha/Desktop/payvlo/tests/test_harness.py) autonomously validates the entire system across 11 comprehensive scenarios:

```bash
# Run inside running Docker container
docker compose exec commerce-node python tests/test_harness.py

# Or run locally via pytest
pytest tests/test_harness.py -v
```

### Verified Test Cases:
1. `[TEST 1]` System Health & Dual Protocol Registrations (`/healthz`)
2. `[TEST 2]` MCP Tool Discovery & Multi-Merchant Catalog Search
3. `[TEST 3]` Deterministic Discount Clamping Verification (50% $\to$ 15%)
4. `[TEST 4]` Zero-Trust Spend Cap Enforcement (Rejection of underfunded requests)
5. `[TEST 5]` Cart Downsizing & Validated Razorpay Checkout
6. `[TEST 6]` 24-Hour Idempotency Replay Defense (Zero double-charge guarantee)
7. `[TEST 7]` Universal Agent Protocol (UAP / A2A) Intent Negotiation & Settlement
8. `[TEST 8]` Privacy-Preserving Masked PII Audit Ledger Verification
9. `[TEST 9]` Dynamic Shopify Merchant Onboarding & Catalog Sync
10. `[TEST 10]` Custom REST API Ingestion with Custom Field Mapping
11. `[TEST 11]` Full End-to-End Commerce on Dynamically Onboarded Stores

---

## 📦 Production Deployment

### Deploying to Render (Serverless Web Service)

This repository includes a [`render.yaml`](file:///c:/Users/risha/Desktop/payvlo/render.yaml) blueprint:

1. Push your repository to GitHub / GitLab.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** $\to$ **Blueprint**.
3. Select your repository.
4. Configure your environment variables in Render:
   * `DATABASE_URL`: Your PostgreSQL connection string (e.g. Neon Serverless PostgreSQL `postgresql+psycopg2://...`)
   * `REDIS_URL`: Your Redis connection string (e.g. Upstash Redis `rediss://...`)
   * `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`: Razorpay API keys
5. Render will automatically build the `Dockerfile` and expose the node with zero-downtime health checking on `/healthz`.

---

## 🔒 License
MIT License. Built for Autonomous Agentic Commerce.
