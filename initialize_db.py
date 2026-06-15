import sqlite3
import os

# Connect to the database
conn = sqlite3.connect('movie_booking.db')
cursor = conn.cursor()

# Insert sample cities
cities = [
    ("Bengaluru",),
    ("Hyderabad",),
    ("Chennai",),
    ("Mumbai",),
    ("Kolkata",)
]

cursor.executemany("INSERT INTO cities (name) VALUES (?)", cities)

# Insert updated movies
movies = [
    ("HIT: The Third Case", "A detective unravels a complex crime mystery.", 140, "/static/images/movies/movie1.jpg"),
    ("Odela 2", "A thrilling sequel set in a rural crime backdrop.", 145, "/static/images/movies/movie2.jpg"),
    ("Raid 2", "An intense action sequel following a fearless tax officer.", 150, "/static/images/movies/movie3.jpg"),
    ("Kesari Chapter 2", "A historical drama depicting bravery and sacrifice.", 160, "/static/images/movies/movie4.jpg"),
    ("MAD Square", "A quirky comedy about chaotic friendships.", 130, "/static/images/movies/movie5.jpg"),
    ("The Bhootnii", "A chilling supernatural horror tale.", 135, "/static/images/movies/movie6.jpg")
]

cursor.executemany("INSERT INTO movies (title, description, duration, image_url) VALUES (?, ?, ?, ?)", movies)

# Insert sample theaters (filtered and adjusted by city)
theaters = [
    ("PVR Orion", 1, "Rajajinagar, Bengaluru"),
    ("INOX Garuda", 1, "MG Road, Bengaluru"),
    ("Cinepolis Manjeera", 2, "Kukatpally, Hyderabad"),
    ("Asian M Cube", 2, "Miyapur, Hyderabad"),
    ("Sathyam Cinemas", 3, "Royapettah, Chennai"),
    ("INOX Chennai Citi Center", 3, "Mylapore, Chennai"),
    ("PVR Phoenix", 4, "Lower Parel, Mumbai"),
    ("Carnival Cinemas", 4, "Wadala, Mumbai"),
    ("INOX Quest", 5, "Park Circus, Kolkata"),
    ("SVF Cinemas", 5, "Salt Lake, Kolkata")
]

cursor.executemany("INSERT INTO theaters (name, city_id, address) VALUES (?, ?, ?)", theaters)

# Insert theater-movie relationships
theater_movies = [
    (1, 1), (1, 2), (1, 3),
    (2, 2), (2, 4), (2, 5),
    (3, 1), (3, 4), (3, 5),
    (4, 2), (4, 3), (4, 5),
    (5, 1), (5, 3), (5, 4),
    (6, 2), (6, 4), (6, 5),
    (7, 1), (7, 3), (7, 5),
    (8, 2), (8, 3), (8, 4),
    (9, 1), (9, 2), (9, 5),
    (10, 3), (10, 4), (10, 5)
]

cursor.executemany("INSERT INTO theater_movies (theater_id, movie_id) VALUES (?, ?)", theater_movies)

# Insert some sample bookings
bookings = [
    (1, 1, "A1"),
    (1, 1, "A2"),
    (2, 2, "B1"),
    (3, 1, "C1"),
    (4, 5, "D1"),
    (5, 3, "E1"),
    (6, 4, "F1")
]

cursor.executemany("INSERT INTO bookings (theater_id, movie_id, seat_number) VALUES (?, ?, ?)", bookings)

# Commit the changes and close the connection
conn.commit()
conn.close()