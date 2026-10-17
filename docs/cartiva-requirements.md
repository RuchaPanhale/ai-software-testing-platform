# Cartiva — Business Requirements

Status: Initial specification; implementation pending
Application ID: cartiva
Currency: USD

Cartiva is a fictional fashion store with simulated payments.

## CART-001 — Product catalog and variants

Customers can browse products with names, descriptions, categories,
images, and prices.

Each purchasable size/color variant has a unique ID, a product ID,
a price in integer cents, and a nonnegative stock quantity.

Unknown variants must be rejected.
Sold-out variants remain visible but cannot be purchased.

## CART-002 — Shopping cart

Customers can add variants, update quantities, and remove items.

Quantities must be positive integers.
Zero, negative, fractional, and boolean quantities are invalid.
Removing an item uses a separate remove operation.

Adding the same variant again increases its existing quantity.
The combined quantity must not exceed available stock.

Adding items to a cart does not reserve inventory.
Stock must be checked again at checkout.

## CART-003 — Prices and money

The backend calculates prices from its stored catalog.
Client-supplied prices and totals must not determine charges.

Subtotal is the sum of unit price multiplied by quantity.
All monetary amounts are stored and calculated in integer cents.

## CART-004 — Promotions

An order accepts at most one discount code.
Codes are trimmed and normalized to uppercase.

WELCOME10 provides:
- 10% off the merchandise subtotal.
- Minimum qualifying subtotal: $50.00, inclusive.
- Maximum discount: $20.00.

Round discounts to the nearest cent, with half cents rounded up.
Discounts do not apply to shipping.

Unknown, expired, or ineligible codes produce a validation error.

Each promotion has a configured UTC expiration timestamp.
It is invalid when the current time equals or exceeds that timestamp.

## CART-005 — Shipping

Standard shipping costs $5.99.

Shipping is free only when the merchandise total AFTER discounts
is strictly greater than $100.00.

Examples:
- $99.99 after discounts: $5.99 shipping.
- $100.00 after discounts: $5.99 shipping.
- $100.01 after discounts: free shipping.

## CART-006 — Final total

Final total = subtotal - discount + shipping.

Tax calculation is outside this demo's scope.
The storefront must clearly identify checkout as simulated.

## CART-007 — Checkout validation

Checkout requires:
- A nonempty cart.
- A nonblank customer name.
- A valid-format email.
- A shipping address with a nonblank address line and city.
- A supported two-letter US state code.
- A five-digit ZIP code.

Only US shipping is supported.
Address deliverability is not verified.

Prices, promotion eligibility, and stock are revalidated at checkout.

## CART-008 — Simulated payment and inventory

Payment simulation supports approved and declined outcomes.
No real card details are collected.

An approved checkout creates an order and decreases inventory.

Order creation and inventory updates occur in one database
transaction: all changes succeed together or none are saved.

Failed validation or declined payment must not create an order
or decrease inventory.

Stock must never become negative, including when checkout
requests compete for the same remaining stock.

## CART-009 — Duplicate checkout protection

Every checkout request requires an idempotency key.

Repeating a successful request with the same key and equivalent
payload returns the original order without reducing stock again.

Reusing that key with a different payload returns a conflict error.

## CART-010 — Order records

Persist:
- Order ID and UTC creation timestamp.
- Purchased variants and quantities.
- Unit prices at purchase.
- Subtotal, discount, shipping, and final total.

Existing order prices remain unchanged when catalog prices change.

## Baseline scope

Guest checkout only.
No login, real payments, refunds, or admin dashboard in the baseline.

## Reproducible testing

Tests use isolated databases and controlled seed data.
Promotion-expiration tests use a controlled clock.

Intentionally defective versions are clearly labeled and kept
separate from the correct baseline.