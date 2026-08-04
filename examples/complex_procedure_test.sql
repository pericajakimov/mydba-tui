-- Complex Stored Procedure for Dependency Parsing Stress Test
-- Execute this against the deptest schema created by dependency_test_schema.sql
--
-- Usage:
--   mysql -u root -p deptest < examples/complex_procedure_test.sql
--
-- Expected dependencies for process_monthly_billing:
--   Tables: orders, customers, order_items, products, audit_log, order_archive
--   Routines: get_customer_order_count (function), archive_old_orders (procedure)

USE deptest;

DELIMITER //

DROP PROCEDURE IF EXISTS process_monthly_billing //

CREATE PROCEDURE process_monthly_billing(
    IN p_billing_month DATE,
    IN p_dry_run TINYINT,
    OUT p_total_processed INT,
    OUT p_total_errors INT
)
BEGIN
    DECLARE v_done INT DEFAULT 0;
    DECLARE v_order_id INT;
    DECLARE v_customer_id INT;
    DECLARE v_order_total DECIMAL(10,2);
    DECLARE v_customer_name VARCHAR(100);
    DECLARE v_customer_email VARCHAR(255);
    DECLARE v_discount_pct DECIMAL(5,2) DEFAULT 0;
    DECLARE v_final_amount DECIMAL(10,2);
    DECLARE v_error_count INT DEFAULT 0;
    DECLARE v_processed INT DEFAULT 0;
    DECLARE v_batch_id BIGINT;

    -- Cursor over orders joined with customers
    DECLARE cur_orders CURSOR FOR
        SELECT o.id, o.customer_id, o.total, c.name, c.email
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        WHERE o.order_date >= p_billing_month
          AND o.order_date < DATE_ADD(p_billing_month, INTERVAL 1 MONTH)
          AND o.status = 'delivered';

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        INSERT INTO audit_log (action, table_name, details)
        VALUES ('ERROR', 'process_monthly_billing', 'Unhandled SQL exception');
        ROLLBACK;
    END;

    -- Initialize batch
    INSERT INTO audit_log (action, table_name, details)
    VALUES ('BATCH_START', 'billing', CONCAT('Billing for month: ', p_billing_month));
    SET v_batch_id = LAST_INSERT_ID();

    START TRANSACTION;

    OPEN cur_orders;

    order_loop: LOOP
        FETCH cur_orders INTO v_order_id, v_customer_id, v_order_total,
                              v_customer_name, v_customer_email;

        IF v_done = 1 THEN
            LEAVE order_loop;
        END IF;

        -- Determine discount based on customer order history
        IF get_customer_order_count(v_customer_id) > 100 THEN
            SET v_discount_pct = 15.0;
        ELSEIF get_customer_order_count(v_customer_id) > 50 THEN
            SET v_discount_pct = 10.0;
        ELSEIF get_customer_order_count(v_customer_id) > 10 THEN
            SET v_discount_pct = 5.0;
        ELSE
            SET v_discount_pct = 0;
        END IF;

        SET v_final_amount = v_order_total * (1 - v_discount_pct / 100);

        -- Validate the order items still exist
        IF (SELECT COUNT(*) FROM order_items WHERE order_id = v_order_id) = 0 THEN
            INSERT INTO audit_log (action, table_name, object_id, details)
            VALUES ('SKIP', 'orders', v_order_id, 'No items found for order');
            SET v_error_count = v_error_count + 1;
            ITERATE order_loop;
        END IF;

        -- Check product availability for each item in a nested block
        BEGIN
            DECLARE v_item_done INT DEFAULT 0;
            DECLARE v_product_id INT;
            DECLARE v_qty INT;
            DECLARE v_stock INT;

            DECLARE cur_items CURSOR FOR
                SELECT oi.product_id, oi.quantity
                FROM order_items oi
                WHERE oi.order_id = v_order_id;

            DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_item_done = 1;

            OPEN cur_items;

            item_check: WHILE v_item_done = 0 DO
                FETCH cur_items INTO v_product_id, v_qty;

                IF v_item_done = 1 THEN
                    LEAVE item_check;
                END IF;

                SELECT stock INTO v_stock FROM products WHERE id = v_product_id;

                CASE
                    WHEN v_stock IS NULL THEN
                        INSERT INTO audit_log (action, table_name, object_id, details)
                        VALUES ('WARN', 'products', v_product_id, 'Product not found');
                    WHEN v_stock < v_qty THEN
                        INSERT INTO audit_log (action, table_name, object_id, details)
                        VALUES ('WARN', 'products', v_product_id,
                                CONCAT('Low stock: ', v_stock, ' < ', v_qty));
                    ELSE
                        UPDATE products SET stock = stock - v_qty
                        WHERE id = v_product_id;
                END CASE;

            END WHILE;

            CLOSE cur_items;
        END;

        -- Process the billing
        IF p_dry_run = 0 THEN
            UPDATE orders SET status = 'delivered', total = v_final_amount
            WHERE id = v_order_id;

            INSERT INTO order_archive (id, customer_id, order_date, status, total)
            VALUES (v_order_id, v_customer_id, p_billing_month, 'billed', v_final_amount);
        END IF;

        SET v_processed = v_processed + 1;

        -- Log progress every 100 records
        IF MOD(v_processed, 100) = 0 THEN
            INSERT INTO audit_log (action, table_name, details)
            VALUES ('PROGRESS', 'billing',
                    CONCAT('Processed ', v_processed, ' orders'));
        END IF;

    END LOOP;

    CLOSE cur_orders;

    COMMIT;

    -- Final summary
    INSERT INTO audit_log (action, table_name, details)
    VALUES ('BATCH_END', 'billing',
            CONCAT('Processed: ', v_processed, ', Errors: ', v_error_count));

    -- Call cleanup procedure
    CALL archive_old_orders(180);

    SET p_total_processed = v_processed;
    SET p_total_errors = v_error_count;
END //

DELIMITER ;
