-- init-db.sql — Schema demo pentru aplicatie
CREATE TABLE IF NOT EXISTS users (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL
);

INSERT INTO users (name, email) VALUES
    ('Ana Ionescu',   'ana@example.com'),
    ('Mihai Popescu', 'mihai@example.com'),
    ('Elena Stan',    'elena@example.com')
ON CONFLICT DO NOTHING;
