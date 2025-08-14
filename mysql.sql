CREATE TABLE users (
    id INTEGER PRIMARY KEY,  -- Auto-incrementing primary key
    first_name TEXT NOT NULL,               -- User's first name (cannot be null)
    last_name TEXT NOT NULL,                -- User's last name (cannot be null)
    username TEXT UNIQUE NOT NULL,          -- User's username (must be unique and not null)
    email TEXT UNIQUE NOT NULL,             -- User's email (must be unique and not null)
    password TEXT NOT NULL,                 -- User's password (cannot be null)
);