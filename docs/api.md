# Cartiva API Reference

Behavior of the implemented endpoints. All monetary values are integer
cents (e.g. $19.99 = 1999). Requirement IDs refer to
[`cartiva-requirements.md`](cartiva-requirements.md).

| Method | Endpoint | Purpose | Requirement |
|---|---|---|---|
| GET | `/` | Redirects to the storefront | — |
| GET | `/shop/` | Storefront page (static HTML, CSS, JS) | — |
| GET | `/health` | Health check | — |
| GET | `/products` | List, search, and filter the catalog | CART-001, CART-012 |
| GET | `/products/{product_id}` | Product details with all variants | CART-001 |
| POST | `/carts` | Create an empty cart | CART-002 |
| POST | `/carts/{cart_id}/items` | Add an item | CART-002, CART-003 |
| GET | `/carts/{cart_id}` | View cart with line totals and subtotal | CART-003 |
| PATCH | `/carts/{cart_id}/items/{item_id}` | Set an item's quantity | CART-002 |
| DELETE | `/carts/{cart_id}/items/{item_id}` | Remove an item | CART-002 |

## Catalog

### `GET /products`

Returns products ordered by name and ID, with their variants ordered by ID.
Each variant includes size, color, price in integer cents, stock quantity,
and an optional image URL. Sold-out variants remain visible with a stock
quantity of zero. An empty catalog returns an empty list.

Optional query parameters:
- `q`: every search word must match the product's name, its category, or a
  single variant's color.
- `category`: exact category match.
- `color`: exact variant color match.

Matching ignores capitalization and normalizes extra whitespace. Search and
filters are combined with AND. Responses include only matching variants,
including sold-out ones. No matches returns HTTP 200 with `[]`.
Search does not combine colors from different variants and does not search
descriptions. Pagination is not implemented.

Example: `/products?q=green%20shirt&category=Shirts`

### `GET /products/{product_id}`

Returns one product with all its variants ordered by variant ID, including
sold-out options. A missing product returns HTTP 404:
`{"detail": "Product not found"}`

## Carts

### `POST /carts`

Creates an empty cart and returns HTTP 201 with its UUID. Each request
creates a new cart.

### `POST /carts/{cart_id}/items`

Body: `{"variant_id": 1, "quantity": 2}`

Adding an existing variant increases its quantity. The combined quantity
must not exceed available stock. Adding items does not reserve or reduce
inventory. Client-supplied prices are rejected; the server uses catalog prices.

| Status | Meaning |
|---|---|
| 200 | Item added or quantity increased |
| 404 | Cart or variant not found |
| 409 | Requested quantity exceeds available stock, or cart already checked out |
| 422 | Invalid request data |

Adding items locks the parent cart row until the transaction ends, so
simultaneous additions to the same cart are handled one at a time.

### `GET /carts/{cart_id}`

Returns items ordered by item ID, with product details, current variant
prices, line totals, and a subtotal. Each line total equals the current unit
price multiplied by quantity. The subtotal excludes discounts, shipping, and
tax. An empty cart returns an empty items list and subtotal zero; a missing
cart returns HTTP 404.

Items with insufficient stock remain visible with `has_enough_stock: false`.
Viewing a cart never changes quantities or inventory.

### `PATCH /carts/{cart_id}/items/{item_id}`

Body: `{"quantity": 3}`

Sets the quantity (it does not add to it). Quantity must be a positive
integer and cannot exceed current stock. Repeating the same update leaves
the quantity unchanged.

### `DELETE /carts/{cart_id}/items/{item_id}`

Removes the item and returns HTTP 204 with no body. The cart remains available.

Both PATCH and DELETE verify that the item belongs to the specified cart and
lock the parent cart during changes. Missing carts or items return HTTP 404.
Neither changes inventory.

## Checked-out carts

A cart counts as checked out when an order references it (one order per
cart, enforced by a unique constraint). Adding, updating, or removing items
from such a cart returns HTTP 409 with "Cart has already been checked out".
Viewing it is still allowed.

All three modification endpoints use a shared helper that locks the cart
before checking for an existing order.

The checkout endpoint and inventory deduction are not implemented.
