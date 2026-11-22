-- Q: Where do shoppers drop off between browsing and buying?
-- Counts sessions that reached each step at least once, then the share
-- that continued from the previous step and from the very first step.
WITH session_steps AS (
    SELECT session_id,
           MAX(CASE WHEN event_type = 'product_view'   THEN 1 ELSE 0 END) AS viewed,
           MAX(CASE WHEN event_type = 'add_to_cart'    THEN 1 ELSE 0 END) AS added,
           MAX(CASE WHEN event_type = 'checkout_start' THEN 1 ELSE 0 END) AS checked_out,
           MAX(CASE WHEN event_type = 'purchase'       THEN 1 ELSE 0 END) AS purchased
    FROM analytics.events
    GROUP BY session_id
),
funnel AS (
    SELECT 1 AS step_order, 'Viewed a product' AS step, SUM(viewed)      AS sessions FROM session_steps
    UNION ALL
    SELECT 2, 'Added to cart',    SUM(added)       FROM session_steps
    UNION ALL
    SELECT 3, 'Started checkout', SUM(checked_out) FROM session_steps
    UNION ALL
    SELECT 4, 'Purchased',        SUM(purchased)   FROM session_steps
)
SELECT step_order,
       step,
       sessions,
       ROUND(100.0 * sessions
             / LAG(sessions) OVER (ORDER BY step_order), 1)        AS pct_of_previous_step,
       ROUND(100.0 * sessions
             / FIRST_VALUE(sessions) OVER (ORDER BY step_order), 1) AS pct_of_first_step
FROM funnel
ORDER BY step_order;
