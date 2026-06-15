DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS theaters;
DROP TABLE IF EXISTS theater_movies;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    duration INTEGER,
    image_url TEXT
);

CREATE TABLE theaters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city_id INTEGER,
    address TEXT,
    FOREIGN KEY (city_id) REFERENCES cities (id)
);

CREATE TABLE theater_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theater_id INTEGER,
    movie_id INTEGER,
    FOREIGN KEY (theater_id) REFERENCES theaters (id),
    FOREIGN KEY (movie_id) REFERENCES movies (id)
);

CREATE TABLE bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    theater_id INTEGER,
    movie_id INTEGER,
    seat_number TEXT NOT NULL,
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (theater_id) REFERENCES theaters (id),
    FOREIGN KEY (movie_id) REFERENCES movies (id)
);