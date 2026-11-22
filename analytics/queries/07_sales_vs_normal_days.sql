-- Q: What happens on sale days compared with normal days?
-- Compares average daily sessions, orders and revenue, plus conversion and
-- AOV, for each sitewide sale versus all non-sale days.
-- Pattern: build one row per calendar day, aggregate sessions and orders
-- per day ONCE, then LEFT JOIN so days with no activity still count as 0.
WITH days AS (
    SELECT d::date AS day
    FROM GENERATE_SERIES('2024-01-01'::date, '2025-12-31'::date,
                         INTERVAL '1 day') AS d
),
daily_sessions AS (
    SELECT started_at::date AS day, COUNT(*) AS sessions
    FROM analytics.sessions
    GROUP BY 1
),
daily_orders AS (
    SELECT ordered_at::date                          AS day,
           COUNT(*)                                  AS orders,
           SUM(subtotal_cents - discount_cents)      AS net_revenue_cents
    FROM analytics.orders
    GROUP BY 1
),
daily AS (
    SELECT d.day,
           COALESCE(p.name, 'Normal days')           AS period,
           COALESCE(s.sessions, 0)                   AS sessions,
           COALESCE(o.orders, 0)                     AS orders,
           COALESCE(o.net_revenue_cents, 0)          AS net_revenue_cents
    FROM days AS d
    LEFT JOIN analytics.promotions AS p
           ON p.promotion_type = 'automatic'
          AND d.day BETWEEN p.starts_on AND p.ends_on
    LEFT JOIN daily_sessions AS s ON s.day = d.day
    LEFT JOIN daily_orders   AS o ON o.day = d.day
)
SELECT period,
       COUNT(*)                                                   AS days,
       ROUND(AVG(sessions), 1)                                    AS avg_daily_sessions,
       ROUND(AVG(orders), 1)                                      AS avg_daily_orders,
       ROUND(AVG(net_revenue_cents) / 100.0, 2)                   AS avg_daily_net_revenue_usd,
       ROUND(100.0 * SUM(orders) / NULLIF(SUM(sessions), 0), 2)   AS conversion_rate_pct,
       ROUND(SUM(net_revenue_cents) / 100.0
             / NULLIF(SUM(orders), 0), 2)                         AS avg_order_value_usd
FROM daily
GROUP BY period
ORDER BY period = 'Normal days', MIN(day);   -- sales first by date, normal days last
