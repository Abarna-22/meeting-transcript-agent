-- Run once as a MySQL admin user:
--   mysql -u root -p < backend/scripts/setup_mysql.sql
CREATE DATABASE IF NOT EXISTS meetings CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'meeting'@'localhost' IDENTIFIED BY 'meeting';
GRANT ALL PRIVILEGES ON meetings.* TO 'meeting'@'localhost';
FLUSH PRIVILEGES;
-- The app creates its own tables (meetings, participants, action_items, decisions) on first start.
