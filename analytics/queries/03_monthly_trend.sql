-- Q: How do traffic, orders and revenue move month by month?
-- Shows growth after launch, seasonality and sale months (July, Nov/Dec).
WITH monthly_sessions AS (
    SELECT DATE_TRUNC('month', started_at)::date AS month,
           COUNT(*)                              AS sessions
    FROM analytics.sessions
    GROUP BY 1
),
monthly_orders AS (
    SELECT DATE_TRUNC('month', ordered_at)::date     AS month,
           COUNT(*)                                  AS orders,
           SUM(subtotal_cents - discount_cents)      AS net_revenue_cents
    FROM analytics.orders
    GROUP BY 1
)
SELECT s.month,
       s.sessions,
       COALESCE(o.orders, 0)                                     AS orders,
       ROUND(COALESCE(o.net_revenue_cents, 0) / 100.0, 2)        AS net_revenue_usd,
       ROUND(100.0 * COALESCE(o.orders, 0) / s.sessions, 2)      AS conversion_rate_pct
FROM monthly_sessions AS s
LEFT JOIN monthly_orders AS o ON o.month = s.month   -- keep months with no orders
ORDER BY s.month;
