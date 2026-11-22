-- Data check: how many rows does each main table have?
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM analytics.customers
UNION ALL SELECT 'sessions',    COUNT(*) FROM analytics.sessions
UNION ALL SELECT 'events',      COUNT(*) FROM analytics.events
UNION ALL SELECT 'orders',      COUNT(*) FROM analytics.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM analytics.order_items;