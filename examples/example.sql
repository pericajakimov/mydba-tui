-- mydba-tui example SQL script
--
-- Purpose:
-- Demonstrates a simple SQL workflow that can be loaded and executed
-- from the SQL workspace.
--
-- This script is intentionally safe and uses a temporary table only.
-- It does not modify existing user data.


-- Create temporary example table

CREATE TEMPORARY TABLE example_users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Insert sample data

INSERT INTO example_users (
    username
)
VALUES
    ('alice'),
    ('bob'),
    ('carol');


-- Query sample data

SELECT
    id,
    username,
    created_at
FROM example_users
ORDER BY id;


-- Cleanup

DROP TEMPORARY TABLE example_users;
