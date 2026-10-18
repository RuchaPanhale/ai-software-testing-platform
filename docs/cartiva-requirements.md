# Cartiva — Application Requirements and Acceptance Criteria

- Project: AI Software Testing & Regression Platform
- Application: Cartiva
- Application ID: cartiva
- Document version: 0.2
- Status: Agreed baseline scope; implementation pending
- Currency: USD

## 1. Purpose

Cartiva is a fictional premium fashion e-commerce web application
and the first Application Under Test (AUT) for the AI Software
Testing & Regression Platform.

It will provide a functional shopping experience with real backend
business logic, persistent order data, and simulated payments.

Its documented requirements will provide the expected behavior
against which automated tests evaluate application versions.

This document describes intended behavior, not completed features
or verified test results.

## 2. Baseline User Journey

A visitor can:

1. Browse clothing and accessories.
2. Search for products and filter by category and color.
3. Select a size/color variant and quantity.
4. Add items to a guest cart.
5. Update quantities or remove items.
6. Apply an optional discount code.
7. Review the calculated totals.
8. Enter a name, email, and US shipping address.
9. Complete an approved or declined simulated payment.
10. View an order confirmation after successful checkout.

No registration or login is required.

## 3. Planned Technical Architecture

- Frontend: React and TypeScript, built with Vite.
- Backend: Python and FastAPI.
- Database: PostgreSQL 18, running locally through Docker Compose, with SQLModel and planned Alembic migrations.
- Communication: JSON REST APIs.
- Backend tests: Pytest.
- Selected browser workflow tests: Playwright.
- Development environment: VS Code on macOS.
- Version control and CI: Git, GitHub, and GitHub Actions.

The backend is authoritative for prices, discounts, inventory,
validation, and order creation.

Cartiva owns its application data. The separate testing platform
owns requirements, approved test specifications, runs, results,
and defect records.

A Cartiva-specific adapter will connect the application to the
shared testing engine. Cartiva business rules must not be embedded
in the platform's central execution or analytics logic.

## 4. Scope

### Included

- Guest browsing and checkout.
- Product catalog and size/color variants.
- Basic search and category/color filtering.
- Separate guest carts.
- Variant-level inventory.
- One discount code per order.
- Shipping and order-total calculation.
- Checkout input validation.
- Simulated payment outcomes.
- Persistent order records.
- Duplicate checkout protection.
- Reproducible automated tests and controlled defective versions.

### Outside the Baseline

- Registration, login, and password reset.
- Customer account dashboards.
- Cross-device cart synchronization.
- Real card collection or payment processing.
- Tax calculation.
- International shipping.
- Address deliverability verification.
- Inventory reservation timers.
- Returns, refunds, and order cancellation.
- Admin dashboards.
- AI search, typo correction, and recommendations.
- Wishlists, reviews, and loyalty programs.

An absent out-of-scope feature is not automatically an application
defect.

## 5. Shared Definitions

### Product

A catalog item with a name, description, category, and images.

### Variant

A purchasable combination of product, size, and color with its own
unique ID, price, and inventory quantity.

Accessories without a meaningful clothing size may use "One Size".

### Guest Session

A browser session identified by an opaque, unpredictable cookie.
The backend uses this session to identify the visitor's cart.

Tabs sharing the cookie share a cart. Separate cookie stores,
such as separate browser profiles, have separate carts.

### Money

Monetary amounts are stored and calculated as integer cents.

For example:
- $5.99 = 599 cents.
- $100.00 = 10000 cents.

### Time

Stored timestamps use UTC.

### Requirement and Acceptance IDs

Requirement IDs use CART-001 through CART-013.

Acceptance examples use IDs such as AC-004-01 and reference the
corresponding requirement. These IDs remain stable as tests are added.

---

## CART-001 — Product Catalog and Variants

### Rules

- Display product names, descriptions, categories, and images.
- Each variant has a unique ID, product ID, size, color,
  nonnegative integer price in cents, and nonnegative integer stock.
- Display the price and availability of the selected variant.
- Stock belongs to a specific variant, not only to the product.
- Unknown variant IDs must be rejected by the backend.
- Sold-out variants remain visible and are labeled "Sold out".
- The interface prevents adding sold-out variants.
- The backend independently rejects unavailable purchases.

### Acceptance Examples

- AC-001-01: A shirt has green/M stock 0 and green/L stock 3.
  Green/M is labeled sold out; green/L is available.
- AC-001-02: A request containing an unknown variant ID is rejected.
- AC-001-03: Directly submitting a sold-out variant to the API is
  rejected even if the frontend control is bypassed.

## CART-002 — Shopping Cart

### Rules

- Visitors can add variants, set quantities, and remove items.
- Quantities must be positive integers.
- Zero, negative, fractional, boolean, and string quantities are
  invalid API inputs.
- Removing an item uses an explicit remove operation.
- Adding the same variant increases the existing line quantity.
- Updating a quantity replaces that line's quantity.
- The resulting quantity cannot exceed currently available stock.
- Adding to a cart does not reserve or decrease inventory.
- An empty cart has a payable total of zero and cannot check out.
- A declined payment preserves the cart.
- Successful checkout clears the purchased items after the order
  and inventory changes are committed.
- The baseline does not support editing a cart while its checkout
  is being processed. Such mutations must not silently change the
  order being placed.

### Acceptance Examples

- AC-002-01: Add quantity 1 twice for the same variant.
  One cart line has quantity 2.
- AC-002-02: Change a line from quantity 2 to quantity 3.
  Its resulting quantity is 3, not 5.
- AC-002-03: With stock 2, attempting quantity 3 is rejected.
- AC-002-04: Quantities 0, -1, 1.5, true, and "2" are rejected.
- AC-002-05: Removing the final line leaves an empty cart with
  payable total zero.
- AC-002-06: Adding quantity 1 to a cart leaves inventory unchanged.

## CART-003 — Prices and Monetary Calculations

### Rules

- The backend calculates charges using stored catalog prices.
- Checkout requests do not supply authoritative prices or totals.
- Client-supplied pricing fields cannot override backend prices.
- Subtotal equals the sum of unit price multiplied by quantity.
- Monetary calculations use integer cents.
- Cart totals are recalculated after cart or promotion changes.
- Prices are revalidated at checkout.
- If prices or payable totals changed since the customer's review,
  checkout requires review of the updated quote before creating
  an order.

### Acceptance Examples

- AC-003-01: Two units priced at 1999 cents produce a subtotal
  of 3998 cents.
- AC-003-02: A request attempting to replace a stored price of
  5000 cents with 1 cent cannot create an order at the lower price.
- AC-003-03: A catalog price changes after the customer reviews
  the cart. Checkout reports the changed quote and creates no order
  until the customer reviews and resubmits it.

## CART-004 — Promotions and Discounts

### Rules

- An order accepts at most one discount code.
- Codes are trimmed and normalized to uppercase.
- WELCOME10 provides 10% off the merchandise subtotal.
- Minimum qualifying subtotal is $50.00, inclusive.
- Maximum discount is $20.00.
- Calculate the percentage discount, round to the nearest cent
  with half cents rounded up, and apply the maximum discount cap.
- Discounts do not apply to shipping.
- Unknown, expired, and ineligible codes produce a clear error.
- Multiple codes in one request are rejected.
- Applying a replacement code does not stack it with the old code.
- Each promotion has a configured UTC expiration timestamp.
- A promotion is expired when current time is equal to or later
  than its expiration timestamp.
- Eligibility is checked again when the cart changes and at checkout.
- If an applied code becomes ineligible, show that condition and
  prevent checkout until the code is removed or the cart is corrected.

### Acceptance Examples

- AC-004-01: " welcome10 " is interpreted as WELCOME10.
- AC-004-02: A $49.99 subtotal is ineligible for WELCOME10.
- AC-004-03: A $50.00 subtotal receives a $5.00 discount.
- AC-004-04: A $250.00 subtotal receives the capped $20.00 discount.
- AC-004-05: A $50.05 subtotal receives a $5.01 discount.
- AC-004-06: A code is rejected at its exact expiration timestamp.
- AC-004-07: Applying WELCOME10 repeatedly does not compound
  the discount.
- AC-004-08: Reducing an eligible cart below $50.00 flags the
  applied code as ineligible.

## CART-005 — Shipping

### Rules

- Standard shipping costs $5.99 for a nonempty eligible cart.
- Shipping is free only when the merchandise total AFTER discounts
  is strictly greater than $100.00.
- Exactly $100.00 after discounts does not qualify.
- Shipping is recalculated after cart or discount changes.

### Acceptance Examples

- AC-005-01: $99.99 after discounts incurs $5.99 shipping.
- AC-005-02: $100.00 after discounts incurs $5.99 shipping.
- AC-005-03: $100.01 after discounts receives free shipping.
- AC-005-04: A $110.00 subtotal with WELCOME10 becomes $99.00
  before shipping and incurs $5.99 shipping.

## CART-006 — Final Total and Checkout Disclosure

### Rules

- Final total = subtotal - discount + shipping.
- Display subtotal, discount, shipping, and final total separately.
- Tax calculation is excluded from this demonstration.
- Clearly identify checkout as simulated and state that no
  real payment will be charged.
- The backend's calculated total is authoritative.

### Acceptance Examples

- AC-006-01: Subtotal $110.00, discount $11.00, and shipping $5.99
  produce a final total of $104.99.
- AC-006-02: The checkout page displays the simulated-payment
  disclosure before submission.

## CART-007 — Checkout Input Validation

### Rules

Checkout requires:

- A nonempty cart.
- A nonblank customer name.
- A valid-format email address.
- A nonblank shipping address line.
- A nonblank city.
- A supported two-letter US state code.
- A five-digit ZIP code stored as text to preserve leading zeros.
- A valid simulated-payment outcome.
- A nonblank idempotency key.

Additional rules:

- Trim leading and trailing whitespace from text fields.
- Normalize state codes to uppercase.
- The baseline supports the 50 US states and Washington, DC.
- ZIP codes must contain exactly five ASCII digits.
- Only US shipping is supported.
- Email format validation does not verify mailbox ownership.
- Address deliverability and state/ZIP consistency are not verified.
- Field errors identify the invalid field and describe the issue.
- Business-rule errors clearly explain the failed rule.
- Failed validation creates no order and changes no inventory.
- Revalidate prices, promotions, and stock at checkout.

### Acceptance Examples

- AC-007-01: A whitespace-only customer name is rejected.
- AC-007-02: An email without a valid email structure is rejected.
- AC-007-03: "ny" is normalized to NY and accepted.
- AC-007-04: State code XX is rejected.
- AC-007-05: ZIP code "02108" retains its leading zero.
- AC-007-06: ZIP codes "1234" and "12345-6789" are rejected.
- AC-007-07: An empty cart cannot create an order.

## CART-008 — Simulated Payment, Inventory, and Transactions

### Rules

- Payment simulation supports approved and declined outcomes.
- Outcomes are explicit and deterministic, not randomly selected.
- No real card numbers, CVVs, or payment charges are collected.
- An approved checkout creates an order and decreases inventory
  by the purchased quantities.
- Order creation, inventory updates, successful idempotency
  recording, and purchased-cart-item clearing occur atomically.
- Either all required database changes succeed or none persist.
- Declined payment creates no order, changes no stock, and
  preserves the cart.
- Invalid checkout creates no order and changes no stock.
- Stock must never become negative.
- Competing requests cannot purchase the same remaining unit.
- Insufficient stock produces a clear error rather than a
  partially completed order.
- A database failure rolls back the transaction.

### Acceptance Examples

- AC-008-01: Buying quantity 2 from stock 5 with approved payment
  creates one order and leaves stock 3.
- AC-008-02: Declined payment leaves stock and cart unchanged
  and creates no order.
- AC-008-03: Two separate customers attempt to purchase the last
  unit. Exactly one succeeds; the other receives an unavailable
  stock response.
- AC-008-04: One line in a multi-item order lacks stock.
  No order is created and no line's inventory is decreased.
- AC-008-05: A simulated database failure during order creation
  leaves no partial order or inventory update.

## CART-009 — Duplicate Checkout Protection

### Rules

- Every checkout attempt requires an idempotency key.
- The key identifies one logical checkout attempt.
- A retry after a timeout reuses the original key and payload.
- The payload includes the reviewed items, quantities, quote,
  customer details, address, promotion, and simulated outcome.
- Equivalent payloads are compared using a documented canonical
  representation, not raw JSON formatting or property order.
- A successful request's order and canonical payload are stored.
- A retry with the same key and equivalent payload returns the
  original order without additional stock or cart changes.
- Check for a completed request before validating the live cart,
  because successful checkout may already have cleared that cart.
- The same key with a different payload produces a conflict.
- Concurrent requests using the same key cannot create two orders.
- An in-progress duplicate may receive a retryable conflict;
  retrying after completion returns the original order.
- Keys and stored outcomes are associated with the guest session.
  Another session cannot use a key to retrieve someone else's order.
- A deliberate new attempt after rejection or payment decline
  uses a new key.
- Successful keys remain recorded for the lifetime of the demo data.

### Acceptance Examples

- AC-009-01: Submit a successful request twice with the same key.
  Both responses identify the same order; stock decreases once.
- AC-009-02: Retry after the successful checkout cleared the cart.
  The original order is returned.
- AC-009-03: Reuse a successful key with a different quantity.
  A conflict is returned.
- AC-009-04: Submit the same key concurrently.
  At most one order is created.
- AC-009-05: A separate guest session cannot retrieve an order
  using another session's key.

## CART-010 — Persistent Order Records

### Rules

Persist:

- Unique order ID.
- Guest-session association.
- UTC creation timestamp.
- Customer and shipping details used for checkout.
- Purchased variant IDs and descriptive snapshots.
- Quantities and unit prices at purchase.
- Applied promotion, if any.
- Subtotal, discount, shipping, and final total.

Additional rules:

- Existing order prices remain unchanged when catalog prices change.
- Order confirmation displays the saved order values.
- Order retrieval is restricted to the associated guest session.
- Automated tests and demonstrations use fictional customer data.

### Acceptance Examples

- AC-010-01: After checkout, change the catalog price.
  The existing order retains its original unit price and total.
- AC-010-02: Restart the backend.
  The persisted order still exists in the database.
- AC-010-03: Another guest session cannot access the order.

## CART-011 — Guest-Cart Isolation and Persistence

### Rules

- The backend maintains separate carts for separate guest sessions.
- Identify sessions using opaque, unpredictable cookies.
- Do not use names or email addresses as cart identifiers.
- A page refresh preserves the cart while the session remains valid.
- Tabs sharing a browser session share the same cart.
- Separate browser profiles or cookie stores have separate carts.
- The backend resolves cart ownership from the session.
- A client-provided cart ID cannot grant access to another cart.
- Clearing the session cookie starts a new guest session.
- Persistence across browser closure is not guaranteed.
- Cross-device synchronization is outside scope.
- Session cookies are HttpOnly and use an appropriate SameSite
  policy. HTTPS deployments use Secure cookies.
- Responses and logs must not expose another session's cart.

### Acceptance Examples

- AC-011-01: Session A adds a shirt.
  Session B's cart remains empty.
- AC-011-02: Refresh session A's page.
  Its shirt remains in the cart.
- AC-011-03: Open another tab sharing session A's cookie.
  It displays the same cart when loaded or refreshed.
- AC-011-04: Session B attempts to reference session A's cart.
  It cannot read or modify that cart.

## CART-012 — Basic Search and Filters

### Rules

- Search product names, categories, and variant colors.
- Product descriptions are not searched in the baseline.
- Normalize queries by trimming, collapsing repeated whitespace,
  and comparing without case sensitivity.
- Split the normalized query into words.
- Every query word must occur in at least one of the candidate
  variant's product name, category, or color fields.
- Matching uses case-insensitive substring matching.
- Evaluate all query words against the same candidate variant.
  Do not combine colors from different variants to create a match.
- Support one category filter and one color filter at a time.
- Filter selections use normalized exact values.
- Combine the query, category filter, and color filter using AND.
- A product matches if at least one variant satisfies all conditions.
- An empty or whitespace-only query applies only the selected filters.
- With no query or filters, return the full catalog.
- Use a stable default order: product name, then product ID.
- No typo correction, synonyms, semantic search, or recommendations
  are required.

### Acceptance Examples

- AC-012-01: " GREEN   shirt " produces the same matches as
  "green shirt".
- AC-012-02: "green shirt" finds a shirt with a green variant.
- AC-012-03: "black jeans" finds jeans with a black variant.
- AC-012-04: A shirt has separate green and black variants.
  "green black shirt" does not match solely by combining those colors.
- AC-012-05: A description mentioning "green shirt" does not create
  a match when the searched fields do not match.
- AC-012-06: Search "shirt" with color green returns only products
  with a green variant satisfying the search.
- AC-012-07: An empty query with category Jeans returns jeans.
- AC-012-08: Clearing search and filters restores the full catalog.

## CART-013 — Search Results and Availability Display

### Rules

- Display each matching product once.
- Highlight or select a color belonging to a matching variant.
- When several variants match, choose a deterministic matching
  variant, preferring one in stock, then ordering by variant ID.
- Keep sold-out matches visible.
- Clearly label sold-out variants and disable their add-to-cart action.
- Allow customers to inspect available sizes and colors.
- Changing a selection updates its price and stock display.
- The backend still validates stock when adding and checking out.
- If nothing matches, show "No products match your search."
- Provide a way to clear search and filters.
- An empty result is a normal outcome, not a server error.

### Acceptance Examples

- AC-013-01: Search "green shirt".
  A matching product appears once with its green color highlighted.
- AC-013-02: All matching green variants are sold out.
  The result remains visible with sold-out labeling.
- AC-013-03: Green/M is sold out but green/L is available.
  M cannot be added; L can be added within its stock limit.
- AC-013-04: Search for a nonexistent product.
  Show the no-results message without a server error.

## 6. Error Response Expectations

The API will use consistent structured errors containing:

- A stable machine-readable error code.
- A human-readable message.
- Field-level details when applicable.

Expected response categories:

- Invalid input or invalid promotion: validation error.
- Unknown product or variant: not found.
- Insufficient stock, changed quote, or conflicting idempotency
  payload: conflict.
- Declined simulated payment: explicit payment-declined outcome.
- Unexpected infrastructure failure: server error without exposing
  internal implementation details.

Exact response schemas and HTTP status mappings will be finalized
in the API contract before endpoint implementation.

Tests must distinguish business-rule rejection from an unexpected
infrastructure failure.

## 7. Acceptance Criteria and Traceability

- Preserve the requirement and acceptance IDs in this document.
- Link automated tests to the requirements they verify.
- Include positive, negative, boundary, and interaction scenarios.
- Expected results must be derived from approved requirements,
  not copied from the implementation's actual output.
- When intended behavior changes, revise the requirement and
  affected test expectations together.
- A requirement revision is different from an application defect.
- The examples in this document are a starting set, not a claim
  of exhaustive coverage.

## 8. Test Data and Reproducibility

- Use synthetic products, promotions, customers, and addresses.
- Seed known variant IDs, prices, colors, sizes, and stock levels.
- Use isolated test databases rather than the browsing/demo database.
- Reset test state between independent scenarios.
- Use a controlled clock for promotion-expiration tests.
- Use deterministic approved/declined simulated-payment inputs.
- Use genuinely overlapping requests for concurrency tests.
- Preserve application version and test revision metadata.
- Do not commit local databases, session cookies, or secrets.

## 9. Controlled Regression Demonstrations

Build and verify a baseline before introducing deliberate defects.

Potential defects include:

- Free shipping incorrectly applied at exactly $100.00.
- WELCOME10 applied twice.
- A sold-out size accepted because another size is available.
- Negative quantities accepted.
- Duplicate checkout creates an additional order.
- Shipping calculated before discounts.
- Search matches colors across unrelated variants.
- One guest session receives another session's cart.

Each injected defect must have:

- A distinct application-version identifier.
- A description of the intended fault.
- Linked requirements and tests.
- Reproduction steps.
- Verified baseline and defective-version outcomes.

Keep defective versions clearly separated from the normal baseline.
Never present an intentionally defective version as production-ready.

## 10. Testing Platform Integration and Scope Handling

The following are integration expectations for the separate quality
platform, not additional storefront screens.

- Register Cartiva under application ID cartiva.
- Associate its requirements, versions, tests, runs, and defects
  with that application.
- Link AI-generated test proposals to documented requirements.
- Validate proposal structure and application-specific inputs.
- Allow human approval, rejection, and clarification.
- Mark unsupported-feature proposals as out of scope.
- A password-reset proposal is out of scope for Cartiva.
- An ambiguous expected outcome requires clarification.
- Execute only approved, applicable tests through trusted adapters.
- Do not execute arbitrary AI-generated Python code.
- Determine pass/fail from execution and assertions, not AI opinions.
- Exclude unexecuted and out-of-scope suggestions from execution
  pass/fail counts.
- Report infrastructure errors separately from application failures.
- Compare equivalent test revisions within the same application.
- Treat changed, new, or missing tests separately from regressions.

These expectations will also be recorded in the platform's own
requirements document when that component is specified.

## 11. Baseline Completion Criteria

Cartiva is ready for regression-platform integration when:

- Catalog, search, and filters operate on real application data.
- Variant selection, cart changes, and totals work end to end.
- Guest carts are isolated.
- Checkout validation follows documented rules.
- Approved and declined simulated payments behave correctly.
- Orders persist with purchase-time prices.
- Inventory and duplicate-request protections are verified.
- The React frontend communicates with the FastAPI backend.
- Critical business rules have meaningful automated tests.
- Setup and test instructions are reproducible.
- Known limitations are documented.

Passing test counts and coverage results will be recorded only after
tests have actually been implemented and executed.

## 12. Implementation Sequence

1. Backend foundation and health endpoint.
2. Database models and deterministic catalog seed data.
3. Catalog, variant, search, and filter APIs.
4. Guest sessions and cart APIs.
5. Pricing, promotion, and shipping calculations.
6. Checkout, order persistence, and duplicate-request protection.
7. React storefront connected to the APIs.
8. Integration, concurrency, and selected browser tests.
9. Verified baseline and controlled defective versions.

Write relevant tests alongside each component.
Keep Cartiva modest so the reusable quality platform remains the
main project.

## 13. Change History

### Version 0.2 — October 17, 2026

- Added guest-cart isolation.
- Added basic search and category/color filters.
- Defined search-result and sold-out behavior.
- Clarified concurrent checkout and inventory handling.
- Expanded duplicate-request protection.
- Clarified validation and simulated-payment outcomes.
- Added requirement-linked acceptance examples.
- Defined scope handling for AI-generated test proposals.
- Preserved guest checkout and simulated payments as baseline limits.