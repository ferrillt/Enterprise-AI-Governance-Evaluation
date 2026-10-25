SELECT o.order_id
FROM ORDERS AS o
LEFT JOIN ORDER_ITEMS AS oi
    ON oi.order_id = o.order_id
WHERE oi.order_id IS NULL;
