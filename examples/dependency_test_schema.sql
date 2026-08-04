-- Dependency Test Schema
-- Creates objects with various dependency relationships for testing
-- the Dependency Analysis Engine in mydba.
--
-- Usage:
--   mysql -u root -p < examples/dependency_test_schema.sql
--
-- After importing, connect with mydba, press R to build the dependency graph,
-- then navigate to any object and check the Dependencies tab.

DROP DATABASE IF EXISTS deptest;
CREATE DATABASE deptest;
USE deptest;

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    status ENUM('pending', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    total DECIMAL(10, 2) DEFAULT 0.00,
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_item_order FOREIGN KEY (order_id)
        REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id)
        REFERENCES products(id) ON DELETE RESTRICT
);

CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(100),
    object_id INT,
    user_name VARCHAR(100),
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_archive (
    id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20),
    total DECIMAL(10, 2),
    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- VIEWS (depend on tables and other views)
-- ============================================================

-- View depending on: customers, orders
CREATE VIEW active_customers AS
SELECT DISTINCT c.id, c.name, c.email
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status IN ('pending', 'shipped');

-- View depending on: orders, order_items, products
CREATE VIEW order_details AS
SELECT
    o.id AS order_id,
    o.order_date,
    o.status,
    oi.product_id,
    p.name AS product_name,
    oi.quantity,
    oi.unit_price,
    oi.quantity * oi.unit_price AS line_total
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id;

-- View depending on another view (order_details) + customers
CREATE VIEW customer_order_summary AS
SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    COUNT(DISTINCT od.order_id) AS total_orders,
    SUM(od.line_total) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN order_details od ON od.order_id = o.id
GROUP BY c.id, c.name;

-- View depending on: products, order_items
CREATE VIEW low_stock_products AS
SELECT
    p.id,
    p.name,
    p.stock,
    COALESCE(SUM(oi.quantity), 0) AS total_ordered
FROM products p
LEFT JOIN order_items oi ON oi.product_id = p.id
GROUP BY p.id, p.name, p.stock
HAVING p.stock < 10;

-- ============================================================
-- FUNCTIONS (depend on tables)
-- ============================================================

DELIMITER //

-- Function depending on: orders
CREATE FUNCTION get_customer_order_count(cust_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE cnt INT;
    SELECT COUNT(*) INTO cnt FROM orders WHERE customer_id = cust_id;
    RETURN cnt;
END //

-- Function depending on: order_items
CREATE FUNCTION get_order_total(ord_id INT)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE total DECIMAL(10, 2);
    SELECT COALESCE(SUM(quantity * unit_price), 0) INTO total
    FROM order_items WHERE order_id = ord_id;
    RETURN total;
END //

-- ============================================================
-- PROCEDURES (depend on tables and functions)
-- ============================================================

-- Procedure depending on: orders, order_items, products (stock update)
CREATE PROCEDURE place_order(
    IN p_customer_id INT,
    IN p_product_id INT,
    IN p_quantity INT
)
BEGIN
    DECLARE v_price DECIMAL(10, 2);
    DECLARE v_order_id INT;

    SELECT price INTO v_price FROM products WHERE id = p_product_id;

    INSERT INTO orders (customer_id, order_date, status)
    VALUES (p_customer_id, CURDATE(), 'pending');

    SET v_order_id = LAST_INSERT_ID();

    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
    VALUES (v_order_id, p_product_id, p_quantity, v_price);

    UPDATE products SET stock = stock - p_quantity WHERE id = p_product_id;

    UPDATE orders SET total = get_order_total(v_order_id) WHERE id = v_order_id;
END //

-- Procedure depending on: orders, order_archive, audit_log
CREATE PROCEDURE archive_old_orders(IN p_days_old INT)
BEGIN
    INSERT INTO order_archive (id, customer_id, order_date, status, total)
    SELECT id, customer_id, order_date, status, total
    FROM orders
    WHERE order_date < DATE_SUB(CURDATE(), INTERVAL p_days_old DAY)
      AND status = 'delivered';

    DELETE FROM orders
    WHERE order_date < DATE_SUB(CURDATE(), INTERVAL p_days_old DAY)
      AND status = 'delivered';

    INSERT INTO audit_log (action, table_name, details)
    VALUES ('archive', 'orders', CONCAT('Archived orders older than ', p_days_old, ' days'));
END //

-- Procedure depending on: customers, orders (uses function get_customer_order_count)
CREATE PROCEDURE cleanup_inactive_customers(IN p_min_orders INT)
BEGIN
    DELETE FROM customers
    WHERE get_customer_order_count(id) < p_min_orders
      AND id NOT IN (SELECT customer_id FROM orders WHERE status IN ('pending', 'shipped'));

    INSERT INTO audit_log (action, table_name, details)
    VALUES ('cleanup', 'customers', CONCAT('Removed customers with fewer than ', p_min_orders, ' orders'));
END //

-- ============================================================
-- TRIGGERS (depend on tables, may call functions)
-- ============================================================

-- Trigger on orders depending on: audit_log
CREATE TRIGGER trg_order_after_insert
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (action, table_name, object_id, details)
    VALUES ('INSERT', 'orders', NEW.id, CONCAT('New order for customer ', NEW.customer_id));
END //

-- Trigger on orders depending on: audit_log
CREATE TRIGGER trg_order_after_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO audit_log (action, table_name, object_id, details)
        VALUES ('STATUS_CHANGE', 'orders', NEW.id,
                CONCAT('Status: ', OLD.status, ' -> ', NEW.status));
    END IF;
END //

-- Trigger on order_items depending on: products (stock adjustment)
CREATE TRIGGER trg_item_after_delete
AFTER DELETE ON order_items
FOR EACH ROW
BEGIN
    UPDATE products SET stock = stock + OLD.quantity WHERE id = OLD.product_id;
END //

-- Trigger on customers depending on: audit_log
CREATE TRIGGER trg_customer_before_delete
BEFORE DELETE ON customers
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (action, table_name, object_id, details)
    VALUES ('DELETE', 'customers', OLD.id, CONCAT('Deleting customer: ', OLD.name));
END //

-- ============================================================
-- EVENTS (depend on procedures/tables)
-- ============================================================

-- Event depending on procedure: archive_old_orders
CREATE EVENT evt_nightly_archive
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
    CALL archive_old_orders(90) //

-- Event depending on: audit_log directly
CREATE EVENT evt_cleanup_audit_log
ON SCHEDULE EVERY 7 DAY
STARTS CURRENT_TIMESTAMP
DO
    DELETE FROM audit_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 365 DAY) //

DELIMITER ;

-- ============================================================
-- EXPECTED DEPENDENCY MAP (for verification)
-- ============================================================
--
-- TABLE customers:
--   Dependents: orders (FK), active_customers (VIEW), customer_order_summary (VIEW),
--               get_customer_order_count (FUNC), cleanup_inactive_customers (PROC),
--               trg_customer_before_delete (TRIGGER)
--
-- TABLE orders:
--   Depends on: customers (FK)
--   Dependents: order_items (FK), active_customers (VIEW), order_details (VIEW),
--               customer_order_summary (VIEW), get_customer_order_count (FUNC),
--               place_order (PROC), archive_old_orders (PROC),
--               cleanup_inactive_customers (PROC),
--               trg_order_after_insert (TRIGGER), trg_order_after_update (TRIGGER)
--
-- TABLE products:
--   Dependents: order_items (FK), order_details (VIEW), low_stock_products (VIEW),
--               place_order (PROC), trg_item_after_delete (TRIGGER)
--
-- TABLE order_items:
--   Depends on: orders (FK), products (FK)
--   Dependents: order_details (VIEW), low_stock_products (VIEW),
--               get_order_total (FUNC), place_order (PROC)
--
-- TABLE audit_log:
--   Dependents: archive_old_orders (PROC), cleanup_inactive_customers (PROC),
--               trg_order_after_insert (TRIGGER), trg_order_after_update (TRIGGER),
--               trg_customer_before_delete (TRIGGER), evt_cleanup_audit_log (EVENT)
--
-- TABLE order_archive:
--   Dependents: archive_old_orders (PROC)
--
-- VIEW order_details:
--   Depends on: orders, order_items, products
--   Dependents: customer_order_summary (VIEW)
--
-- FUNCTION get_order_total:
--   Depends on: order_items
--   Dependents: place_order (PROC) — via function call in UPDATE
--
-- PROCEDURE archive_old_orders:
--   Depends on: orders, order_archive, audit_log
--   Dependents: evt_nightly_archive (EVENT)
--


-- ============================================================
-- COMPLEX PROCEDURE FOR DEPENDENCY PARSING STRESS TEST
-- ============================================================
-- This procedure exercises all MySQL procedural constructs:
-- cursors, handlers, loops, nested IF/ELSEIF/ELSE, WHILE,
-- REPEAT, CASE, multiple DML on different tables, CALL, etc.

DELIMITER //

DROP PROCEDURE IF EXISTS deptest.process_monthly_billing //

CREATE PROCEDURE deptest.process_monthly_billing(
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

        -- Check product availability for each item
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

-- ============================================================
-- EXPECTED DEPENDENCIES FOR process_monthly_billing:
--
-- Tables referenced:
--   deptest.orders          (SELECT in cursor, UPDATE)
--   deptest.customers       (JOIN in cursor)
--   deptest.order_items     (SELECT count, cursor)
--   deptest.products        (SELECT stock, UPDATE stock)
--   deptest.audit_log       (INSERT multiple times)
--   deptest.order_archive   (INSERT)
--
-- Routines called:
--   deptest.get_customer_order_count  (function call in IF)
--   deptest.archive_old_orders        (CALL)
-- ============================================================
