CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_verified_seller INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS adds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL CHECK (images_qty >= 0),
    FOREIGN KEY (seller_id) REFERENCES users(id)
);