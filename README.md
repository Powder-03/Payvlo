# 🌐 Payvlo — Universal Agentic Commerce Node (MCP + UAP / A2A)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20%7C%20Vite-61DAFB.svg)](https://vitejs.dev)
[![Protocols](https://img.shields.io/badge/Protocols-MCP%20%7C%20UAP%20A2A-purple.svg)]()
[![Backend Deploy](https://img.shields.io/badge/Render-Live-success.svg)](https://payvlo.onrender.com)
[![Frontend Deploy](https://img.shields.io/badge/Vercel-Live-success.svg)](https://frontend-nine-ashy-72.vercel.app/)

A production-ready, serverless **Universal Agentic Commerce Node & Merchant Portal** built in Python (Service-Based Modular Architecture) and React (Vite).

Payvlo acts as a dual-interface gateway for **ANY merchant** (Shopify D2C brands, Domino's Pizza, BeastLife Nutrition, MuscleBlaze, or custom REST APIs), enabling both tool-calling AI agents (Claude, Cursor, Antigravity) and autonomous peer-to-peer buyer agents to discover catalogs, negotiate bounded pricing, and settle transactions safely.

---

## 🚀 Live Deployments

| Component | Platform | URL |
| :--- | :--- | :--- |
| 🖥️ **Merchant React Portal** | **Vercel** | [https://frontend-nine-ashy-72.vercel.app/](https://frontend-nine-ashy-72.vercel.app/) |
| ⚡ **Backend API & Swagger Docs** | **Render** | [https://payvlo.onrender.com/docs#/](https://payvlo.onrender.com/docs#/) |
| 🩺 **System Healthcheck** | **Render** | [https://payvlo.onrender.com/healthz](https://payvlo.onrender.com/healthz) |
| 🤖 **FastMCP SSE Transport** | **Render** | [https://payvlo.onrender.com/sse](https://payvlo.onrender.com/sse) |
| 🪪 **UAP Agent Capability Card** | **Render** | [https://payvlo.onrender.com/.well-known/agent.json](https://payvlo.onrender.com/.well-known/agent.json) |

---

## 📑 Table of Contents
1. [Live Deployments](#-live-deployments)
2. [Core Features & Value Proposition](#-core-features)
3. [System Architecture (Service-Based)](#-system-architecture)
4. [Dual Protocol Gateway (MCP + UAP/A2A)](#-dual-protocol-gateway)
5. [Dynamic Merchant Onboarding & Catalog Sync](#-dynamic-merchant-onboarding--sync)
6. [Zero-Trust Security & Bounded Gatekeeper](#-zero-trust-security--guardrails)
7. [API & Tool Reference](#-api--tool-reference)
8. [Quickstart & Local Setup](#-quickstart--local-testing)
9. [Automated E2E Test Suite](#-automated-e2e-test-suite)
10. [Production Deployment Guide](#-production-deployment)

---

## ⚡ Core Features

* **Dual-Interface Agent Gateway:**
  * **MCP (Model Context Protocol):** Connect tool-calling agents (**Claude Desktop**, **Antigravity IDE**, **Cursor**, AutoGPT) over FastMCP SSE and JSON-RPC.
  * **UAP / A2A (Universal Agent Protocol):** Peer-to-peer autonomous buyer agents discover capabilities (`/.well-known/agent.json`), negotiate intent (`/uap/v1/negotiate`), and settle orders (`/uap/v1/transact`).
* **Dynamic Multi-Merchant Onboarding:**
  * Ingest and sync catalogs dynamically from **Shopify** (`/products.json`), **Custom REST APIs** with JSON field mapping, or direct payloads.
  * Multi-tenant store isolation with independent discount ceilings, transaction caps, and agent cards.
* **Deterministic Guardrails & Gatekeeper:**
  * **Deterministic Discount Clamping:** Pure mathematical constraint $\min(\text{requested}, \text{product.max}, \text{merchant.max})$ to prevent prompt injection and hallucinated discounts.
  * **Sub-ms Atomic Spend Cap Gate:** Atomic Redis Lua scripts enforcing user budget limits and 24h merchant spend caps.
  * **24-Hour Idempotency Defense:** Zero double-charge guarantee on replayed transactions.
  * **Privacy-Preserving Audit Ledger:** Masked PII (redacted phone, email, address) and SHA-256 pseudonymized buyer IDs.
  * **Financial Rails:** Integrated with Razorpay rails and test sandbox simulator.
* **Modern Merchant SaaS Dashboard:**
  * Clean React (Vite + Lucide) portal deployed on Vercel with live catalog exploration, address book, and 1-click Antigravity / Claude Desktop configuration generation.

---

## 🏛️ System Architecture

Payvlo utilizes a clean **Service-Based Modular Architecture** where presentation, business logic, persistence, and protocol routing are decoupled into focused, self-explanatory layers.

```
                              ┌──────────────────────────────────────────────┐
                              │                 AGENT CLIENTS                │
                              │     Antigravity / Claude Desktop / Cursor    │
                              └───────────────┬──────────────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │                                               │
             [MCP over SSE / JSON-RPC]                      [UAP / A2A HTTP API]
             /sse, /mcp/tools, /mcp/call              /.well-known/agent.json, /uap/v1/*
                      │                                               │
    ══════════════════╪═══════════════════════════════════════════════╪══════════════════
    ROUTERS LAYER     │                                               │
    (src/api/)        ▼                                               ▼
             ┌─────────────────┐                             ┌─────────────────┐
             │   mcp/sse.py    │                             │  uap/protocol.py│
             │   mcp/tools.py  │                             │  uap/discovery  │
             └────────┬────────┘                             └────────┬────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
    ══════════════════════════════════════════╪══════════════════════════════════════════
    SERVICES LAYER                            ▼
    (src/services/)          ┌──────────────────────────────────┐
                             │       BUSINESS SERVICES          │
                             │  • CheckoutService               │
                             │  • QuoteService                  │
                             │  • CatalogService                │
                             │  • AuthService                   │
                             │  • GatekeeperService             │
                             │  • PaymentService                │
                             │  • AuditService                  │
                             └────────────────┬─────────────────┘
                                              │
    ══════════════════════════════════════════╪══════════════════════════════════════════
    DATA & EGRESS                             ▼
               ┌──────────────────────┬──────────────────────┬──────────────────────┐
               ▼                      ▼                      ▼                      ▼
     ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
     │  PostgreSQL / Neon│  │ Upstash Redis     │  │ Razorpay Rails    │  │ Merchant Stores   │
     │  SQLAlchemy Models│  │ Atomic Lua Caps   │  │ Test Sandbox      │  │ Shopify / REST API│
     └───────────────────┘  └───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Directory Layout

payvlo/
├── src/
│   ├── api/                            # 🌐 All Routers & Protocols (FastAPI)
│   │   ├── v1/                         # REST Ingress (/auth, /merchants, /webhooks)
│   │   ├── mcp/                        # FastMCP SSE Transport (/sse, /messages, /mcp/tools)
│   │   ├── uap/                        # Universal Agent Protocol (/.well-known/agent.json, /uap/v1/*)
│   │   ├── health.py                   # Clean health status endpoint (/healthz, /health)
│   │   └── router.py                   # Master unified router mounting all sub-routes
│   │
│   ├── services/                       # ⚙️ Business Logic & External Integrations
│   │   ├── checkout_service.py         # Bounded checkout, 24h idempotency, spend cap checks
│   │   ├── quote_service.py            # Deterministic discount clamping & quote persistence
│   │   ├── catalog_service.py          # Product search, merchant onboarding, Shopify/REST sync
│   │   ├── auth_service.py             # JWT generation/decoding, password hashing, address book
│   │   ├── gatekeeper_service.py       # Upstash Redis atomic Lua scripts & in-memory fallback
│   │   ├── payment_service.py          # Razorpay payment rails & sandbox simulator
│   │   └── audit_service.py            # Privacy-preserving SHA-256 user hashing & PII masking
│   │
│   ├── models/                         # 🗄️ SQLAlchemy Declarative Database Models
│   │   ├── base.py                     # Base declarative metadata
│   │   ├── user.py                     # UserModel, UserAddressModel
│   │   ├── merchant.py                 # MerchantModel
│   │   ├── product.py                  # ProductModel
│   │   ├── quote.py                    # QuoteModel
│   │   ├── order.py                    # OrderModel
│   │   └── audit.py                    # AuditEntryModel
│   │
│   ├── schemas/                        # 📋 Pydantic Schemas (Request/Response DTOs)
│   │   ├── auth.py, catalog.py, quote.py, checkout.py, uap.py, audit.py, mcp.py
│   │
│   ├── core/                           # 🧱 Configuration, Database & Scheduler
│   │   ├── config.py                   # Pydantic BaseSettings loading from .env
│   │   ├── database.py                 # Engine initialization and declarative auto-sync
│   │   ├── exceptions.py               # Domain and business exceptions
│   │   └── scheduler.py                # Background periodic catalog sync worker
│   │
│   └── main.py                         # Central FastAPI application entrypoint
│
├── frontend/                           # 🖥️ Modern React Merchant Portal
│   ├── src/                            # React Components, Views, and API Client
│   ├── package.json                    # Frontend dependencies (React, Vite, Lucide)
│   ├── vite.config.js                  # Vite configuration with API proxying
│   └── vercel.json                     # Vercel SPA routing rewrites
│
├── data/                               # Seed data for local testing
├── tests/                              # Autonomous E2E Test Suite (19 Verified Scenarios)
│   ├── e2e/                            # Modularized E2E test suites
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

### Method 2: Standalone Local Setup (Backend + Frontend)

#### 1. Start Backend (FastAPI)
```bash
# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run development server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
# Portal will be live at http://localhost:3000
```

---

## 🧪 Automated E2E Test Suite

The test suite at [`tests/test_harness.py`](file:///c:/Users/risha/Desktop/payvlo/tests/test_harness.py) autonomously validates the entire system across **19 comprehensive scenarios**:

```bash
# Run master E2E test suite
python -X utf8 tests/test_harness.py
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
12. `[TEST 12]` Merchant SaaS Registration & JWT Authentication
13. `[TEST 13]` Authenticated Store Application & User-to-Store Binding
14. `[TEST 14]` Authenticated Catalog Sync & Agent Discovery
15. `[TEST 15]` Instant Event-Driven Shopify Webhook Ingestion
16. `[TEST 16]` Background Auto-Sync Scheduler Cycle
17. `[TEST 17]` Buyer User Registration & Long-Lived MCP API Key Generation
18. `[TEST 18]` Address Book Management (Saved Shortcuts & Dynamic Locations)
19. `[TEST 19]` Semantic Address Resolution during MCP Checkout (`address_label="Home"`)

---

## 📦 Production Deployment Guide

### 1. Backend on Render
* **Live Service URL:** [https://payvlo.onrender.com](https://payvlo.onrender.com)
* **API Documentation:** [https://payvlo.onrender.com/docs#/](https://payvlo.onrender.com/docs#/)
* **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
* **Environment Variables on Render:**
  * `DATABASE_URL`: PostgreSQL connection string (e.g. Neon Serverless PostgreSQL `postgresql+psycopg2://...`)
  * `REDIS_URL`: Redis connection string (e.g. Upstash Redis `rediss://...`)
  * `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`: Razorpay API keys (or `RAZORPAY_SANDBOX_MODE=True`)
  * `JWT_SECRET`: Secure random secret key for merchant & buyer JWT tokens

### 2. Frontend on Vercel
* **Live Portal URL:** [https://frontend-nine-ashy-72.vercel.app/](https://frontend-nine-ashy-72.vercel.app/)
* **Root Directory:** `frontend`
* **Framework Preset:** `Vite`
* **Build Command:** `npm run build`
* **Output Directory:** `dist`
* **Environment Variable on Vercel:**
  * `VITE_API_BASE_URL`: `https://payvlo.onrender.com`

---

## 🔒 License
MIT License. Built for Autonomous Agentic Commerce.
