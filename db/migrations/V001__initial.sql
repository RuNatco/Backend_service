CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified_seller BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS adds (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL CHECK (images_qty >= 0),
    FOREIGN KEY (seller_id) REFERENCES users(id)
);