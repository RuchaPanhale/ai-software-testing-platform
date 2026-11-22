-- Q: How big is the business, and how did 2025 compare with 2024?
-- One row per year plus an all-time row.
-- Definitions:
--   net revenue     = subtotal - discount (what customers paid for products;
--                     shipping excluded because it is not product revenue)
--   AOV             = net revenue / orders
--   conversion rate = orders / sessions (share of visits that ended in an order)
WITH session_counts AS (
    SELECT EXTRACT(YEAR FROM started_at)::int AS year,
           COUNT(*)                           AS sessions
    FROM analytics.sessions
    GROUP BY 1
),
order_totals AS (
    SELECT EXTRACT(YEAR FROM ordered_at)::int        AS year,
           COUNT(*)                                  AS orders,
           COUNT(DISTINCT customer_id)               AS buying_customers,
           SUM(subtotal_cents - discount_cents)      AS net_revenue_cents,
           SUM(discount_cents)                       AS discount_cents
    FROM analytics.orders
    GROUP BY 1
),
by_year AS (
    SELECT s.year::text AS period, s.sessions, o.orders, o.buying_customers,
           o.net_revenue_cents, o.discount_cents
    FROM session_counts AS s
    JOIN order_totals   AS o ON o.year = s.year
),
all_time AS (
    SELECT 'All time' AS period,
           (SELECT COUNT(*) FROM analytics.sessions)           AS sessions,
           COUNT(*)                                            AS orders,
           COUNT(DISTINCT customer_id)                         AS buying_customers,
           SUM(subtotal_cents - discount_cents)                AS net_revenue_cents,
           SUM(discount_cents)                                 AS discount_cents
    FROM analytics.orders
)
SELECT period,
       sessions,
       orders,
       buying_customers,
       ROUND(net_revenue_cents / 100.0, 2)                        AS net_revenue_usd,
       ROUND(net_revenue_cents / 100.0 / orders, 2)               AS avg_order_value_usd,
       ROUND(100.0 * orders / sessions, 2)                        AS conversion_rate_pct,
       ROUND(100.0 * discount_cents
             / (net_revenue_cents + discount_cents), 2)           AS discount_share_pct
FROM (SELECT * FROM by_year UNION ALL SELECT * FROM all_time) AS combined
ORDER BY period;
