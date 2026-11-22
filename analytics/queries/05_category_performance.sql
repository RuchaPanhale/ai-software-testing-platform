-- Q: Which categories sell best, and which lose the most shoppers after
--    "add to cart"? (cart abandonment = added but never purchased)
-- Every add_to_cart event becomes exactly one order line if that cart is
-- purchased, so purchased lines / add-to-cart events = cart conversion.
WITH adds AS (
    SELECT p.category,
           COUNT(*) AS add_to_cart_events
    FROM analytics.events   AS e
    JOIN analytics.products AS p ON p.product_id = e.product_id
    WHERE e.event_type = 'add_to_cart'
    GROUP BY p.category
),
sales AS (
    SELECT category,
           COUNT(*)                     AS purchased_lines,
           SUM(quantity)                AS units_sold,
           SUM(line_total_cents)        AS gross_sales_cents,
           COUNT(DISTINCT order_id)     AS orders
    FROM analytics.order_items
    GROUP BY category
)
SELECT a.category,
       a.add_to_cart_events,
       s.purchased_lines,
       s.units_sold,
       s.orders,
       ROUND(s.gross_sales_cents / 100.0, 2)                              AS gross_sales_usd,
       ROUND(100.0 * s.gross_sales_cents
             / SUM(s.gross_sales_cents) OVER (), 1)                       AS share_of_sales_pct,
       ROUND(100.0 * (a.add_to_cart_events - s.purchased_lines)
             / a.add_to_cart_events, 1)                                   AS cart_abandonment_pct
FROM adds  AS a
JOIN sales AS s ON s.category = a.category
ORDER BY gross_sales_usd DESC;
