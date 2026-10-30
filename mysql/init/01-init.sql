-- Create database if not exists
CREATE DATABASE IF NOT EXISTS clock;
USE clock;

-- Table for ZKTeco clocks/devices
CREATE TABLE IF NOT EXISTS clocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    is_active TINYINT(1) DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip (ip_address),
    INDEX idx_active (is_active)
);

-- Table for users to administer
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- Table to log clock sync operations
CREATE TABLE IF NOT EXISTS sync_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clock_id INT,
    status ENUM('success', 'failed', 'error') NOT NULL,
    message TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clock_id) REFERENCES clocks(id) ON DELETE SET NULL,
    INDEX idx_clock (clock_id),
    INDEX idx_synced (synced_at)
);

-- Grant privileges to clock_user
GRANT ALL PRIVILEGES ON clock.* TO 'clock_user'@'%';
FLUSH PRIVILEGES;
