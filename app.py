from flask import Flask, render_template, request, jsonify, g, redirect, url_for, session, flash, send_file
import sqlite3
import os
import hashlib
import secrets
from functools import wraps
from datetime import datetime, timedelta
import time
import traceback
from pytz import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key
DATABASE = 'movie_booking.db'

# Database connection helpers
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    conn = get_db()
    conn.execute(query, args)
    conn.commit()

# Authentication helpers
def hash_password(password):
    """Hash a password for storing."""
    salt = secrets.token_hex(8)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                salt.encode('utf-8'), 100000)
    pwdhash = pwdhash.hex()
    return salt + pwdhash

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    salt = stored_password[:16]
    stored_hash = stored_password[16:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), 
                                   salt.encode('utf-8'), 100000)
    pwdhash = pwdhash.hex()
    return pwdhash == stored_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.template_filter('strftime')
def strftime_filter(value, format_str):
    """Format a datetime object using strftime."""
    if isinstance(value, datetime):
        return value.strftime(format_str)
    return value

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate input
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        
        # Check if username or email already exists
        if not error:
            user = query_db('SELECT id FROM users WHERE username = ?', [username], one=True)
            if user:
                error = 'Username already exists.'
            
            user = query_db('SELECT id FROM users WHERE email = ?', [email], one=True)
            if user:
                error = 'Email already registered.'
        
        if not error:
            # Hash the password and store the user
            password_hash = hash_password(password)
            
            try:
                modify_db(
                    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    [username, email, password_hash]
                )
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                error = f"Database error: {str(e)}"
        
        flash(error, 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)
        
        error = None
        if not user:
            error = 'Invalid username or password.'
        elif not verify_password(user['password_hash'], password):
            error = 'Invalid username or password.'
        
        if not error:
            # Store user info in session
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            next_page = request.args.get('next')
            if not next_page:
                next_page = url_for('index')
                
            flash('You have successfully logged in!', 'success')
            return redirect(next_page)
        
        flash(error, 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/my-bookings')
@login_required
def my_bookings():
    user_id = session['user_id']
    
    bookings = query_db('''
        SELECT b.id, m.title as movie_title, t.name as theater_name, b.seat_number, b.booking_time
        FROM bookings b
        JOIN movies m ON b.movie_id = m.id
        JOIN theaters t ON b.theater_id = t.id
        WHERE b.user_id = ?
        ORDER BY b.booking_time DESC
    ''', [user_id])
    
    return render_template('my_bookings.html', bookings=bookings)

# Main routes
@app.route('/')
def index():
    cities = query_db('SELECT * FROM cities ORDER BY name')
    return render_template('index.html', cities=cities)

@app.template_filter('date_modify')
def date_modify_filter(date_str, format_str='%Y-%m-%d %H:%M:%S'):
    """Custom filter to format dates in Jinja templates."""
    if isinstance(date_str, str):
        try:
            date_obj = datetime.strptime(date_str, format_str)
            return date_obj
        except ValueError:
            return date_str
    return date_str

@app.template_filter('date_format')
def date_format_filter(date, format_str='%Y-%m-%d %H:%M:%S'):
    """Format a date using the given format string."""
    if isinstance(date, datetime):
        return date.strftime(format_str)
    
    return date

@app.template_filter('date')
def date_filter(value, format_str='%Y-%m-%d'):
    """Format a date using the given format string."""
    if isinstance(value, datetime):
        return value.strftime(format_str)
    return value

@app.context_processor
def utility_processor():
    def now():
        """Return current datetime object."""
        return datetime.now()
    return {'now': now}

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    user_id = session['user_id']
    
    # Check if the booking exists and belongs to the user
    booking = query_db(
        'SELECT * FROM bookings WHERE id = ? AND user_id = ?', 
        [booking_id, user_id], 
        one=True
    )
    
    if not booking:
        return jsonify({
            'success': False, 
            'message': 'Booking not found or you do not have permission to cancel it.'
        })
    
    try:
        # Delete the booking
        modify_db('DELETE FROM bookings WHERE id = ?', [booking_id])
        return jsonify({'success': True, 'message': 'Booking cancelled successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/movie-details/<int:movie_id>')
def movie_details(movie_id):
    movie = query_db('SELECT * FROM movies WHERE id = ?', [movie_id], one=True)
    
    if not movie:
        return jsonify({'success': False, 'message': 'Movie not found'})
    
    # Convert to dict for JSON serialization
    movie_dict = dict(movie)
    
    # Add city_id if it's available in the request
    if 'city_id' in request.args:
        movie_dict['city_id'] = request.args.get('city_id')
    
    return jsonify({'success': True, 'movie': movie_dict})

@app.route('/movies/<int:city_id>')
def movies(city_id):
    movies = query_db('''
        SELECT DISTINCT m.* FROM movies m
        JOIN theater_movies tm ON m.id = tm.movie_id
        JOIN theaters t ON t.id = tm.theater_id
        WHERE t.city_id = ?
    ''', [city_id])
    city = query_db('SELECT name FROM cities WHERE id = ?', [city_id], one=True)
    return render_template('movies.html', movies=movies, city=city['name'], city_id=city_id)

@app.route('/theaters/<int:city_id>/<int:movie_id>')
def theaters(city_id, movie_id):
    # Get current date (optionally in a specific timezone)
    tz = timezone('Asia/Kolkata')  # Adjust to your timezone, e.g., 'UTC'
    current_date = datetime.now(tz)

    # Generate list of dates (today + next 6 days)
    dates = [(current_date + timedelta(days=i)).date() for i in range(7)]

    theaters = query_db('''
        SELECT t.* FROM theaters t
        JOIN theater_movies tm ON t.id = tm.theater_id
        WHERE t.city_id = ? AND tm.movie_id = ?
    ''', [city_id, movie_id])
    
    movie = query_db('SELECT title FROM movies WHERE id = ?', [movie_id], one=True)
    city = query_db('SELECT name FROM cities WHERE id = ?', [city_id], one=True)
    movie_duration = query_db('SELECT duration FROM movies WHERE id = ?', [movie_id], one=True)
    
    if not movie or not city:
        flash('Movie or city not found', 'error')
        return redirect(url_for('index'))
        
    # Convert to dictionaries for clarity
    movie_info = {'id': movie_id, 'title': movie['title']}
    city_info = {'id': city_id, 'name': city['name']}
    
    return render_template('theaters.html',
                           current_date=current_date,
                           dates=dates, 
                          theaters=theaters, 
                          movie=movie_info['title'],
                          movie_duration=movie_duration['duration'], 
                          city=city_info['name'],
                          movie_id=movie_id, 
                          city_id=city_id)

@app.route('/seats/<int:theater_id>/<int:movie_id>')
def seats(theater_id, movie_id):
    theater = query_db('SELECT name FROM theaters WHERE id = ?', [theater_id], one=True)
    movie = query_db('SELECT title FROM movies WHERE id = ?', [movie_id], one=True)
    # Get existing bookings
    bookings = query_db('''
        SELECT seat_number FROM bookings 
        WHERE theater_id = ? AND movie_id = ?
    ''', [theater_id, movie_id])
    
    booked_seats = [booking['seat_number'] for booking in bookings]
    
    return render_template('seats.html', 
                          theater=theater['name'], 
                          movie=movie['title'],
                          theater_id=theater_id,
                          movie_id=movie_id,
                          booked_seats=booked_seats)

@app.route('/book', methods=['POST'])
@login_required
def book_seats():
    # Add more robust error handling
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Request must be JSON'}), 400
            
        data = request.get_json()
        
        # Validate required parameters
        if not all(key in data for key in ['theater_id', 'movie_id', 'seats']):
            return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
            
        theater_id = data.get('theater_id')
        movie_id = data.get('movie_id')
        seats = data.get('seats')
        user_id = session['user_id']
        
        # Validate seat data
        if not isinstance(seats, list) or not seats:
            return jsonify({'success': False, 'message': 'Invalid seat data'}), 400
            
        # Check if theater and movie exist
        theater = query_db('SELECT id FROM theaters WHERE id = ?', [theater_id], one=True)
        movie = query_db('SELECT id FROM movies WHERE id = ?', [movie_id], one=True)
        
        if not theater or not movie:
            return jsonify({'success': False, 'message': 'Theater or movie not found'}), 404
        
        # Begin transaction
        conn = get_db()
        try:
            conn.execute('BEGIN TRANSACTION')
            
            for seat in seats:
                # Check if seat is already booked
                existing = query_db('''
                    SELECT id FROM bookings 
                    WHERE theater_id = ? AND movie_id = ? AND seat_number = ?
                ''', [theater_id, movie_id, seat], one=True)
                
                if existing:
                    conn.execute('ROLLBACK')
                    return jsonify({
                        'success': False, 
                        'message': f'Seat {seat} has been booked by someone else. Please refresh and try again.'
                    }), 409
                
                # Insert booking
                conn.execute('''
                    INSERT INTO bookings (user_id, theater_id, movie_id, seat_number)
                    VALUES (?, ?, ?, ?)
                ''', [user_id, theater_id, movie_id, seat])
            
            conn.execute('COMMIT')
            return jsonify({'success': True, 'message': 'Booking successful!'})
            
        except Exception as e:
            conn.execute('ROLLBACK')
            app.logger.error(f"Database error: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': 'Database error occurred'}), 500
            
    except Exception as e:
        app.logger.error(f"Server error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'An error occurred while processing your booking'}), 500
    

@app.route('/download-ticket/<int:booking_id>')
@login_required
def download_ticket(booking_id):
    user_id = session['user_id']
    
    # Fetch booking details
    booking = query_db('''
        SELECT b.id, m.title as movie_title, t.name as theater_name, b.seat_number, b.booking_time
        FROM bookings b
        JOIN movies m ON b.movie_id = m.id
        JOIN theaters t ON b.theater_id = t.id
        WHERE b.id = ? AND b.user_id = ?
    ''', [booking_id, user_id], one=True)
    
    if not booking:
        return jsonify({'success': False, 'message': 'Booking not found or you do not have permission to access it.'}), 404
    # Generate PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Draw ticket content
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "CinemaHub Movie Ticket")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Booking ID: {booking['id']}")
    c.drawString(50, height - 100, f"Movie: {booking['movie_title']}")
    c.drawString(50, height - 120, f"Theater: {booking['theater_name']}")
    c.drawString(50, height - 140, f"Date: {booking['booking_time'].strftime('%d %b %Y')}")
    c.drawString(50, height - 160, f"Time: {booking['booking_time'].strftime('%I:%M %p')}")
    c.drawString(50, height - 180, f"Seat: {booking['seat_number']}")
    c.drawString(50, height - 200, "Please arrive 15 minutes before showtime. Ticket is non-refundable.")
    
    # Add QR code placeholder (requires actual QR code generation for production)
    c.drawString(50, height - 240, "QR Code Placeholder")
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ticket-{booking['id']}.pdf",
        mimetype='application/pdf'
    )
if __name__ == '__main__':
    # Check if database exists, otherwise create it
    if not os.path.exists(DATABASE):
        with app.app_context():
            with app.open_resource('schema.sql', mode='r') as f:
                get_db().cursor().executescript(f.read())
            get_db().commit()
            
    app.run(debug=True)
