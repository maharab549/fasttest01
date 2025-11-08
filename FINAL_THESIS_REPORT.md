# Final Year Project Thesis: Multi‑Role E‑Commerce Marketplace Platform

## Abstract
This thesis presents the end‑to‑end conception, design, implementation, and operationalization of a multi‑role e‑commerce marketplace platform supporting Customers, Sellers, and Administrators. The project integrates a modern frontend stack (React 19, Vite, Tailwind CSS, Radix UI) with a scalable backend (FastAPI, PostgreSQL, SQLAlchemy, Redis, Stripe) and emphasizes usability, performance, accessibility, security, and extensibility. The work details the full lifecycle: research and inspiration gathering, information architecture, Figma design system creation, component-driven implementation, rigorous testing strategy, deployment and maintenance procedures, and a comprehensive non‑technical operations manual. It closes with evaluation metrics, limitations, and future research directions.

## 1. Introduction
Digital marketplaces require robust role separation, real‑time responsiveness, trust signals, and operational transparency. This project addresses these needs by building a modular platform where: (1) Customers discover and purchase products, (2) Sellers manage inventory, pricing, and engage via messaging, and (3) Administrators moderate content, oversee payments, and maintain system integrity.

### 1.1 Problem Statement
Existing marketplace solutions often either lack fine‑grained customization for academic experimentation or hide architectural details behind proprietary SaaS layers. This thesis aims to construct an open, inspectable implementation demonstrating best practices in modern web engineering.

### 1.2 Objectives
- Define a repeatable research methodology for UI/UX marketplace design.
- Establish a scalable architecture aligning product, variant, order, payment, and messaging domains.
- Implement a design system enabling rapid iteration and consistent frontend styling.
- Deliver secure role‑based access control (RBAC) and payment workflows using Stripe.
- Provide an accessible, documented, and maintainable codebase.
- Enable non‑technical operation through a plain‑language manual.

### 1.3 Scope
In scope: product listings, variants, cart, checkout, orders, reviews, messaging, analytics, admin moderation, payment integration, caching, and observability. Out of scope: full machine learning recommendation system (outlined as future work), multi‑currency tax automation, and cross‑border regulatory compliance.

## 2. Research & Inspiration Gathering
### 2.1 Methodology
1. Competitor Benchmark: Analyze Amazon, Etsy, Shopify Admin, StockX for navigation paradigms, trust components (ratings, badges), and variant selection UX.
2. Pattern Libraries: Mobbin, UI Patterns, Radix UI docs for interaction primitives (dialogs, dropdowns, focus management).
3. Accessibility Standards: WCAG 2.2 guidelines to ensure keyboard operability and semantic structure.
4. User Persona Development: Draft personas for Customer (“goal‑oriented discovery”), Seller (“efficiency & clarity”), Admin (“control & oversight”).
5. Gap Analysis: Identify friction (e.g., multi‑step checkout, poor inventory visibility) and propose solutions (persistent cart drawer, real‑time stock indicator, unified analytics).

### 2.2 Data Collection Instruments
- Screenshot repository annotated with success/issue tags.
- Heuristic evaluation matrix (Learnability, Efficiency, Memorability, Error Prevention, Satisfaction).
- Lightweight user interviews (3–5 participants) to validate navigation clarity and product detail priorities.

### 2.3 Insights Summary
| Insight | Implication | Design Response |
|---------|-------------|-----------------|
| Users abandon slow image galleries | Need performant, responsive media | Preload hero images + lazy load secondary |
| Sellers need variant editing clarity | Reduce cognitive load | Variant table + inline stock editor |
| Admins struggle with diffuse moderation | Need consolidated dashboard | Unified queue: pending products, flagged reviews |

## 3. Information Architecture (IA)
### 3.1 Hierarchical Structure
- Global Navigation: Home, Categories, Collections, Search, Seller Center, Account, Cart.
- Secondary: Notifications, Messages, Reviews, Help.

### 3.2 Domain Objects
- Product ↔ Variants ↔ Images ↔ Inventory Adjustments.
- User ↔ Roles (Customer, Seller, Admin).
- Order ↔ Line Items ↔ Payment Intent ↔ Shipment.
- Messaging: Thread ↔ Messages.

### 3.3 Flow Diagrams (Conceptual)
Customer: Landing → Search → Product → Variant Selection → Cart → Checkout → Order Tracking → Review.
Seller: Registration → Storefront Creation → Product + Variants → Publish → Analytics → Respond to Messages.
Admin: Login → Dashboard → Moderation Queue → User Management → System Health.

## 4. Figma Design System Development
### 4.1 Project Structure
Pages: Research, IA, Wireframes, Components, Tokens, High‑Fidelity Screens, Prototype Interactions.

### 4.2 Design Tokens
| Category | Examples | Implementation Mapping |
|----------|----------|------------------------|
| Color | Neutral Gray Scale, Brand Indigo, Semantic (Success/Error/Warning) | Tailwind config + CSS variables |
| Typography | Inter (Body), Display font (Headings) | Figma styles → tailwind text-* classes |
| Spacing | 4,8,12,16,24,32,48 | Tailwind spacing scale |
| Radius | 4px, 8px, 16px, Pill | Rounded utilities |
| Shadows | Elevation 1–5 | Tailwind box-shadow plugin/custom classes |

### 4.3 Wireframing Approach
Low‑fidelity grayscale to validate layout without visual bias. Focus on content hierarchy (primary CTA prominence, variant panel adjacency to imagery).

### 4.4 Component Library
Families: Navigation (Header, Sidebar), Product (Card, VariantSelector, ImageGallery), Feedback (Toast, Modal, Skeleton), Forms (Input, Select, Toggle), Messaging (ThreadList, MessageBubble), Analytics (ChartWidget). Each annotated with states (loading, disabled, hover, error) and variants (compact/expanded/featured).

### 4.5 Responsive Strategy
Breakpoints: 360 (base), 640, 768, 1024, 1280, 1536. Auto Layout constraints defined to collapse grids into stacked flows below 640.

### 4.6 Prototyping & Interaction
Click‑through prototypes capture: add‑to‑cart animation, variant image swap, chat typing indicator, analytics filter transitions.

### 4.7 Developer Handoff
Exports: Token map spreadsheet (Figma name → CSS variable → Tailwind alias), component prop notes, motion durations (150–500ms), accessibility annotations (aria labels, focus traps).

## 5. Mapping Design to Code
### 5.1 Frontend Technology Choices
React 19 (concurrent features, modern suspense), Vite (fast dev build), Tailwind (utility‑first, token alignment), Radix UI (accessible primitives), Framer Motion (animation orchestration), React Query (data caching and async state).

### 5.2 Folder Structure (Recommended)
```
src/
  components/
    ui/
    product/
    layout/
    messaging/
    analytics/
  hooks/
  lib/ (axiosClient, queryClient, auth helpers)
  contexts/ (Auth, Theme)
  pages/ (Home, ProductDetail, SellerDashboard, AdminPanel)
  styles/ (global.css, tokens.css)
  utils/
```

### 5.3 Coding Conventions
- Functional components + hooks.
- Collocate tests `ComponentName.test.jsx` next to components.
- Use composition over prop drilling; global context only for auth/theme.
- API abstraction via `axiosClient` with interceptors (auth token, retry, cancellation).

### 5.4 Accessibility Practices
Radix UI ensures baseline semantics; augment with descriptive alt text, sufficient contrast, keyboard navigation invariants, aria‑live regions for async updates (cart operations, chat message receipts).

### 5.5 State Management & Data Fetching
React Query for server state (caching, invalidation) + local component state for UI ephemeral interactions (modals, pickers). Prefetch product details when hovering product cards.

### 5.6 Performance Enhancements
- Code splitting per route (lazy imports).
- Image optimization (responsive `srcset` + WebP fallback).
- Debounced search queries, incremental infinite scroll.
- Redis‑backed cached product lists on the backend.

## 6. Backend Architecture
### 6.1 Layered Design
- API Layer: FastAPI routers (auth, products, variants, orders, reviews, messaging, admin, payments).
- Service Layer: Business logic (pricing, inventory adjustments, moderation decisions).
- Data Layer: SQLAlchemy ORM models + repository patterns.
- Integration Layer: Stripe client, Redis caching, WebSocket manager.
- Utilities: Logging, configuration (pydantic‑settings), security (JWT, hashing).

### 6.2 Key Technologies
FastAPI (async performance), PostgreSQL (relational integrity), Redis (cache + pub/sub), SQLAlchemy 2.0 (declarative models), Stripe (payment workflows), python‑jose/passlib (auth), Alembic (migrations).

### 6.3 Async vs Sync Considerations
Adopt async endpoints for I/O heavy operations (DB queries, Stripe calls, Redis operations). Careful use of connection pooling to prevent starvation.

## 7. Role‑Based Feature Specification
### 7.1 Customer
- Registration/Login, Password Reset.
- Product Browsing (filters, search, sorting).
- Product Detail (variants, stock status, dynamic image gallery).
- Cart (persistent, merge on login) & Checkout (Stripe payment intent).
- Order Tracking (status timeline: processing → shipped → delivered).
- Reviews (post‑purchase only, rating + text + moderation status).
- Messaging with sellers (real‑time thread, typing indicator).
- Notifications (order updates, promotional events).
- Wishlist/Favorites.

### 7.2 Seller
- Storefront profile (branding, description, logo/banner uploads).
- Product CRUD + variant management (size, color, stock, price overrides).
- Bulk image upload & automated cleanup script integration.
- Inventory adjustments with audit trail.
- Orders dashboard (fulfillment status changes, packing slip generation).
- Sales analytics (time series, top products, low inventory alerts).
- Messaging (respond to customer inquiries, canned responses library).
- Review management (respond publicly, flag inappropriate content).
- Promotions (schedule discounts, feature products in store window).

### 7.3 Admin
- User management (role assignment, suspension, password reset trigger).
- Product moderation (approval queue, flag review resolution).
- Payment reconciliation (Stripe webhook log viewer, dispute triage).
- System health dashboard (DB latency, Redis hit rate, error rate, uptime checks).
- Content management (homepage banners, curated collections).
- Fraud analysis (velocity rules: excessive failed logins, suspicious order patterns).
- Global settings (tax rates, shipping rules, feature flags).
- Audit log access (admin actions immutably recorded).

### 7.4 Shared Capabilities
- Unified search across products and sellers.
- Notification center with read/unread states.
- Session management (revoke other active sessions).
- Profile personalization (avatar, locale, timezone).

### 7.5 Edge Case Handling
| Scenario | Strategy |
|----------|----------|
| Variant stock drops mid‑checkout | Revalidate inventory before payment confirm |
| Payment intent succeeds, order write fails | Idempotency key + reconciliation job |
| Race condition on inventory adjustment | DB transaction + row level locking |
| Review spam burst | Rate limiting + heuristic spam filter |
| WebSocket disconnect during message send | Automatic retry + pending queue |

## 8. Data Model Overview
Core Entities (simplified):
```
User(id, email, password_hash, role, status, created_at)
Seller(id, user_id, display_name, storefront_slug, rating, verified)
Product(id, seller_id, name, description, category_id, base_price, status, created_at, updated_at)
ProductVariant(id, product_id, sku, color, size, stock, price_override, is_default)
ProductImage(id, product_id, url, sort_order, alt_text)
Cart(id, user_id, updated_at)
CartItem(id, cart_id, product_variant_id, quantity)
Order(id, user_id, total_amount, currency, status, payment_intent_id, created_at)
OrderItem(id, order_id, product_variant_id, unit_price, quantity)
Review(id, user_id, product_id, rating, title, body, status, created_at)
MessageThread(id, customer_id, seller_id, last_message_at)
Message(id, thread_id, sender_user_id, content, created_at, delivery_status)
Notification(id, user_id, type, payload_json, read_at, created_at)
WebhookEvent(id, provider, external_id, event_type, received_at, processed_at, status)
InventoryAdjustment(id, product_variant_id, change, reason, actor_user_id, created_at)
```

### 8.1 Relationships
- User 1:1 Seller (conditional).
- Product 1:N Variants, Product 1:N Images.
- Order 1:N OrderItems.
- MessageThread 1:N Messages.
- ProductVariant stock mutated via InventoryAdjustment ledger for audit integrity.

### 8.2 Indexing Strategy
- products(name, category_id)
- product_variants(product_id, sku)
- orders(user_id, created_at)
- reviews(product_id, created_at)
- messages(thread_id, created_at)

## 9. API Design & Versioning
Base path: `/api/v1`
Pattern: Resource‑oriented, JSON responses: `{ data, meta, errors }`.

### 9.1 Sample Endpoints
- Auth: `POST /auth/login`, `POST /auth/refresh`, `POST /auth/register`
- Products: `GET /products?skip=&limit=`, `GET /products/{id}`, `POST /products` (seller), `PATCH /products/{id}`
- Variants: `POST /products/{id}/variants`, `PATCH /variants/{id}`
- Images: `POST /products/{id}/images`, `DELETE /images/{id}`
- Cart: `GET /cart`, `POST /cart/items`, `PATCH /cart/items/{id}`
- Checkout: `POST /checkout/intent`, `POST /checkout/confirm`
- Orders: `GET /orders`, `GET /orders/{id}`
- Reviews: `POST /products/{id}/reviews`, `GET /products/{id}/reviews`
- Messaging: `GET /threads`, `POST /threads/{id}/messages`; WebSocket: `/ws/chat/{thread_id}`
- Admin: `GET /admin/users`, `PATCH /admin/users/{id}/status`
- Analytics: `GET /seller/analytics/sales-summary`

### 9.2 Error Handling
Standard codes: `VALIDATION_ERROR`, `NOT_FOUND`, `PERMISSION_DENIED`, `CONFLICT`, `RATE_LIMITED`, `INTERNAL_ERROR`. HTTP mapping (400, 401, 403, 404, 409, 429, 500).

### 9.3 Pagination
Offset `skip/limit` or page `page/per_page`; `meta` includes `total`, `has_next`.

### 9.4 Caching
Redis: products list, featured sets, search suggestions. Cache keys namespaced: `prod:list:{filters_hash}` with TTL + explicit invalidation on product mutation.

## 10. Security Architecture
### 10.1 Authentication & Authorization
- JWT Access (short-lived) + Refresh (rotated). Blacklist compromised tokens (Redis set).
- RBAC: route dependencies enforce roles. Admin routes isolated.

### 10.2 Data Protection
- Password hashing: Bcrypt.
- Stripe secret isolation; webhook signature verification.
- Input validation using Pydantic; sanitize review text to remove script tags.

### 10.3 Transport & Operational Security
- Enforce HTTPS in production (reverse proxy e.g., Nginx, Caddy).
- Security headers: CSP (restrict inline scripts), HSTS, X‑Content‑Type‑Options.
- Rate limiting: login, review submissions, messaging.

### 10.4 Audit & Monitoring
- Immutable audit logs for admin actions & moderation decisions.
- Alert thresholds: failed payments, 5xx error spikes.

## 11. Performance & Scalability
### 11.1 Backend
- Use connection pooling; minimize N+1 queries via eager loading (SQLAlchemy relationships).
- Async tasks: image processing + webhook handling decoupled (background queue).

### 11.2 Frontend
- Code splitting, lazy load non‑critical routes (seller analytics, admin panel).
- Preload critical fonts & hero images. Use `IntersectionObserver` for deferred component rendering.

### 11.3 Horizontal Scaling
- Stateless app instances, shared Postgres + Redis.
- WebSocket scaling via Redis pub/sub channel broadcasting.

## 12. Observability & Logging
Structured JSON logs: `timestamp`, `level`, `request_id`, `user_id`, `path`, `duration_ms`.
Metrics: request latency histogram, cache hit ratio, message throughput, payment success/failure counts.
Tracing (optional): OpenTelemetry instrumentation for DB and external calls.

## 13. Testing Strategy
| Test Type | Tools | Scope |
|-----------|-------|-------|
| Unit | Pytest | Services (pricing, inventory) |
| Integration | FastAPI TestClient | Auth, payment, review flows |
| API Contract | Schemathesis / Pydantic | Response schema adherence |
| Frontend Component | React Testing Library | UI state, accessibility |
| E2E | Playwright / Cypress | Checkout, messaging, admin moderation |
| Load | Locust / k6 | Product listing, checkout concurrency |

CI Pipeline: Lint → Type check (if TS adopted) → Unit/Integration → E2E smoke → Build artifacts → Security scanning (pip + npm audit).

## 14. Deployment & DevOps
### 14.1 Environments
- Development: hot reload, verbose logging.
- Staging: production parity (feature flags disabled), synthetic test data.
- Production: optimized builds, structured logs.

### 14.2 Deployment Steps (Containerized)
1. Build backend image → run migrations → start app.
2. Build frontend static bundle → deploy to CDN / static host.
3. Apply environment secrets via platform (no secrets in repo).
4. Configure monitoring dashboards + alerting.

### 14.3 Rollback Strategy
Maintain previous image tag; database migrations versioned. If migration fails → revert (ensure down scripts defined).

## 15. Non‑Technical Operations Manual
### 15.1 Prerequisites
Install: Node.js LTS, pnpm, Python 3.11+, Postgres, Redis, Stripe test account.

### 15.2 Configuration
Backend `.env` example:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/marketplace
REDIS_URL=redis://localhost:6379/0
STRIPE_SECRET=sk_test_XXXX
JWT_SECRET=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
ENV=development
```
Frontend `.env`:
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 15.3 Start Backend
1. `pip install -r requirements.txt`
2. `alembic upgrade head` (if migrations present)
3. `uvicorn app.main:app --reload`

### 15.4 Start Frontend
1. `pnpm install`
2. `pnpm dev`

### 15.5 Basic Usage Flow
- Register a user → login → browse products → add variant to cart → checkout using Stripe test card (`4242 4242 4242 4242`).
- After delivery status simulation → submit a review.
- Seller creates product → adds variants → monitors analytics.
- Admin moderates new product & reviews.

### 15.6 Troubleshooting
| Issue | Cause | Resolution |
|-------|-------|-----------|
| DB connection error | Postgres not running | Start Postgres / verify URL |
| CORS failure | Frontend API base mismatch | Adjust `VITE_API_BASE_URL` |
| Images not showing | Incorrect path or missing storage | Verify upload directory or CDN config |
| Payment fails | Wrong Stripe key | Use test secret + test card |
| Chat not updating | WebSocket disconnected | Refresh page; ensure `/ws/chat/{thread}` reachable |

### 15.7 Maintenance
- Nightly database backups (pg_dump). Retain 7 daily & 4 weekly snapshots.
- Rotate `JWT_SECRET` if compromise suspected (forces logout).
- Update dependencies monthly; run regression tests.

### 15.8 Glossary
Product: Item for sale. Variant: Specific version (size/color). Cart: Temporary purchase list. Checkout: Payment process. Order: Confirmed purchase record. Review: Feedback left by buyer. Webhook: Automatic notification from Stripe. Cache: Faster temporary storage. API: Interface between frontend and backend. JWT: Secure token proving identity.

## 16. Evaluation Metrics
| KPI | Target |
|-----|--------|
| Median product page load | < 2.5 s |
| Checkout completion rate | > 60% of initiated |
| WebSocket message latency | < 300 ms |
| Cache hit ratio (products) | > 70% |
| Failed payment ratio | < 2% |
| Accessibility automated score | ≥ 90 (Lighthouse) |

## 17. Limitations
- Advanced recommendation engine not implemented (future vector embeddings).
- Localization limited to single language (internationalization future work).
- Real‑time inventory sync assumes single primary DB (multi‑region replication not addressed).

## 18. Future Work
1. AI semantic search + personalized recommendations.
2. Multi‑language & multi‑currency support with tax computation.
3. Event‑driven architecture (Kafka) for high‑volume analytics.
4. Fraud detection using anomaly scoring models.
5. Feature flag service for controlled rollouts.

## 19. Ethical & Privacy Considerations
- Data minimization: store only required PII (email, shipping address).
- Provide account deletion & export functionality.
- Log rotation and encryption at rest for sensitive audit data.

## 20. Conclusion
This thesis demonstrates a comprehensive approach to designing and implementing a multi‑stakeholder marketplace system balancing usability, performance, and security. The structured methodology—from research to deployment—creates a foundation extensible into advanced personalization and analytics domains. Future enhancements will focus on intelligent recommendations, internationalization, and resilient multi‑region operations.

## 21. References (Placeholder)
Populate with academic and industry sources used in your literature review. Examples:
- WCAG 2.2 Guidelines.
- Stripe API Documentation.
- FastAPI & SQLAlchemy Official Documentation.
- Nielsen Norman Group usability heuristics.
- OWASP Top Ten.

## 22. Appendices
### Appendix A: Proposed Migration Script Example (Pseudo‑Alembic)
```python
def upgrade():
    op.create_table('products', ...)
    op.create_table('product_variants', ...)
```
### Appendix B: Sample API Response
```json
{
  "data": {"id": 42, "name": "T-Shirt", "variants": [...]},
  "meta": {"cache": false},
  "errors": []
}
```
### Appendix C: Accessibility Checklist Snapshot
- Keyboard traversal (Tab/Shift+Tab) verified.
- Focus ring visible on interactive elements.
- Alt text present on decorative vs informative images.
- Color contrast ratio >= 4.5:1 for body text.

---
_End of Thesis Report_
