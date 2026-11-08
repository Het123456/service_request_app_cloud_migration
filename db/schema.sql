CREATE TABLE IF NOT EXISTS service_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    product_name  VARCHAR(100) NOT NULL,
    issue         VARCHAR(255) NOT NULL,
    status        ENUM('Pending', 'In Progress', 'Completed') NOT NULL DEFAULT 'Pending',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
