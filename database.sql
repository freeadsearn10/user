-- IPRN SMS Monetization Platform - MySQL Schema

CREATE DATABASE IF NOT EXISTS iprn_sms
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE iprn_sms;

-- -----------------------------------------------------
-- Users
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    team_name VARCHAR(120) DEFAULT NULL,
    whatsapp VARCHAR(50) DEFAULT NULL,
    api_key VARCHAR(64) NOT NULL UNIQUE,
    role ENUM('admin','user') NOT NULL DEFAULT 'user',
    status ENUM('active','suspended') NOT NULL DEFAULT 'active',
    balance DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_earned DECIMAL(12,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Routes / Ranges
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS routes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    country VARCHAR(100) NOT NULL,
    range_code VARCHAR(32) NOT NULL,
    otp_rate DECIMAL(10,4) NOT NULL DEFAULT 0,
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Number Pool (available numbers)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS available_numbers (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    number VARCHAR(32) NOT NULL,
    country VARCHAR(100) NOT NULL,
    range_name VARCHAR(120) DEFAULT NULL,
    route_id INT UNSIGNED DEFAULT NULL,
    otp_rate DECIMAL(10,4) NOT NULL DEFAULT 0,
    status ENUM('available','assigned','disabled') NOT NULL DEFAULT 'available',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_number (number),
    INDEX idx_status (status),
    CONSTRAINT fk_available_numbers_route
        FOREIGN KEY (route_id) REFERENCES routes(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Assigned Numbers
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS assigned_numbers (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    number_id INT UNSIGNED NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_user_number (user_id, number_id),
    CONSTRAINT fk_assigned_numbers_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_assigned_numbers_number
        FOREIGN KEY (number_id) REFERENCES available_numbers(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- API Sources
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS api_sources (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    url VARCHAR(255) NOT NULL,
    poll_interval INT UNSIGNED NOT NULL DEFAULT 60,
    status ENUM('on','off') NOT NULL DEFAULT 'off',
    last_polled_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- API Logs (raw responses / status)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS api_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    api_source_id INT UNSIGNED NOT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    http_status INT DEFAULT NULL,
    success TINYINT(1) NOT NULL DEFAULT 0,
    response_time_ms INT DEFAULT NULL,
    error_message VARCHAR(255) DEFAULT NULL,
    raw_response MEDIUMTEXT,
    CONSTRAINT fk_api_logs_source
        FOREIGN KEY (api_source_id) REFERENCES api_sources(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- SMS Logs (CDR)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS sms_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    provider_log_id BIGINT NOT NULL,
    api_source_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED DEFAULT NULL,
    number VARCHAR(32) NOT NULL,
    country VARCHAR(100) DEFAULT NULL,
    range VARCHAR(32) DEFAULT NULL,
    sid VARCHAR(120) DEFAULT NULL,
    message TEXT,
    carrier VARCHAR(120) DEFAULT NULL,
    log_time DATETIME DEFAULT NULL,
    payout DECIMAL(10,4) NOT NULL DEFAULT 0,
    status ENUM('delivered','failed','unmatched') NOT NULL DEFAULT 'unmatched',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_provider_log (provider_log_id, api_source_id),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_number (number),
    CONSTRAINT fk_sms_logs_source
        FOREIGN KEY (api_source_id) REFERENCES api_sources(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_sms_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Payout Requests
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS payouts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    amount DECIMAL(12,4) NOT NULL,
    status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    method VARCHAR(60) DEFAULT NULL,
    destination VARCHAR(120) DEFAULT NULL,
    admin_note VARCHAR(255) DEFAULT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME DEFAULT NULL,
    CONSTRAINT fk_payouts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Notifications
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED DEFAULT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info','warning','success','payout','system') NOT NULL DEFAULT 'info',
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Settings (key/value)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- Seed settings (optional defaults)
-- -----------------------------------------------------
INSERT INTO settings (name, value) VALUES
    ('system_name', 'IPRN SMS Panel'),
    ('cron_interval', '60'),
    ('theme', 'dark'),
    ('api_master_key', 'change_me_master_key')
ON DUPLICATE KEY UPDATE value = VALUES(value);