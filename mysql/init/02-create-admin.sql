USE clock;

-- Insert admin user with hashed password for 'Belgrano369*-'
-- Password hash generated using bcrypt
INSERT INTO users (username, password_hash, is_admin) 
VALUES ('admin', '$2b$12$YHPiO0fEEahqneH2nO3Kout/ALFG2axv6jFXTfBOEEiX0iN4qyii.', TRUE)
ON DUPLICATE KEY UPDATE password_hash = '$2b$12$YHPiO0fEEahqneH2nO3Kout/ALFG2axv6jFXTfBOEEiX0iN4qyii.';

FLUSH PRIVILEGES;
