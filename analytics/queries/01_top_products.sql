-- Top 10 products by units sold (gross sales = before discounts)
SELECT
    oi.product_name,
    oi.category,
    SUM(oi.quantity)                           AS units_sold,
    COUNT(DISTINCT oi.order_id)                AS orders,
    ROUND(SUM(oi.line_total_cents) / 100.0, 2) AS gross_sales_usd
FROM analytics.order_items AS oi
GROUP BY oi.product_name, oi.category
ORDER BY units_sold DESC, gross_sales_usd DESC
LIMIT 10;