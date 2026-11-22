-- Q: Did offering WELCOME10 on the first order get more new customers to buy?
-- Customers were randomly split 50/50 into control (no offer) and
-- treatment (offered WELCOME10). Compare the share who ever placed an order.
-- Significance: a two-proportion z-test. |z| > 1.96 means the difference is
-- statistically significant at the 5% level.
-- NOTE: the data is synthetic and includes a disclosed built-in effect
-- (docs/data-assumptions.md); this demonstrates the method.
WITH customer_outcomes AS (
    SELECT c.customer_id,
           c.experiment_group,
           EXISTS (SELECT 1 FROM analytics.orders AS o
                   WHERE o.customer_id = c.customer_id)                 AS ordered,
           EXISTS (SELECT 1 FROM analytics.orders AS o
                   WHERE o.customer_id = c.customer_id
                     AND o.promotion_code = 'WELCOME10')                AS used_welcome10
    FROM analytics.customers AS c
),
groups AS (
    SELECT experiment_group,
           COUNT(*)                                        AS customers,
           COUNT(*) FILTER (WHERE ordered)                 AS customers_who_ordered,
           COUNT(*) FILTER (WHERE used_welcome10)          AS used_welcome10
    FROM customer_outcomes
    GROUP BY experiment_group
),
rates AS (
    SELECT *,
           customers_who_ordered::numeric / customers      AS order_rate
    FROM groups
),
test AS (
    SELECT t.order_rate - c.order_rate                     AS lift,
           (t.order_rate - c.order_rate)
           / SQRT(p.pooled * (1 - p.pooled)
                  * (1.0 / t.customers + 1.0 / c.customers)) AS z_score
    FROM rates AS t
    CROSS JOIN rates AS c
    CROSS JOIN (SELECT SUM(customers_who_ordered)::numeric / SUM(customers) AS pooled
                FROM rates) AS p
    WHERE t.experiment_group = 'treatment'
      AND c.experiment_group = 'control'
)
SELECT r.experiment_group,
       r.customers,
       r.customers_who_ordered,
       ROUND(100 * r.order_rate, 2)                         AS order_rate_pct,
       r.used_welcome10,
       ROUND(100 * test.lift, 2)                            AS lift_pct_points,
       ROUND(test.z_score, 2)                               AS z_score,
       ABS(test.z_score) > 1.96                             AS significant_at_5pct
FROM rates AS r
CROSS JOIN test
ORDER BY r.experiment_group;
