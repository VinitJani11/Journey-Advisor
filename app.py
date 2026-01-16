from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import random
from datetime import datetime, timedelta, date
from flask_session import Session
import uuid
import re # For parsing duration strings
# import io # Removed as PDF generation is no longer needed

app = Flask(__name__)

# --- Flask Session Configuration ---
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# --- MySQL Database Configuration ---
# IMPORTANT: Replace with your actual MySQL credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'green_journey_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        flash(f"Database connection error: {err}. Please check your database server.", 'error')
        return None

def verify_password(stored_password, provided_password):
    return stored_password == provided_password

def get_unique_origins():
    origins = set()
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT origin FROM journeys")
            for (city,) in cursor.fetchall():
                origins.add(city)
        except mysql.connector.Error as err:
            print(f"Error fetching origins: {err}")
            flash(f"Error loading origins: {err}", 'error')
        finally:
            if conn:
                cursor.close()
                conn.close()
    return sorted(list(origins))

@app.route('/get_destinations/<origin_city>')
def get_destinations(origin_city):
    """API endpoint to get destinations available from a given origin city."""
    destinations = set()
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT destination FROM journeys WHERE origin = %s", (origin_city,))
            for (city,) in cursor.fetchall():
                destinations.add(city)
        except mysql.connector.Error as err:
            print(f"Error fetching destinations for {origin_city}: {err}")
        finally:
            if conn:
                cursor.close()
                conn.close()
    return jsonify(sorted(list(destinations)))


# Helper function to safely convert carbon_footprint string to float
def parse_carbon_footprint(cf_str):
    try:
        if cf_str is not None:
            # Remove 'kg CO2e' and any extra spaces, then convert to float
            return float(cf_str.replace('kg CO2e', '').strip())
        return 0.0
    except (ValueError, AttributeError):
        return 0.0

# Helper function to parse duration string (e.g., "1h 30m") into minutes for sorting
def parse_duration_to_minutes(duration_str):
    if not isinstance(duration_str, str):
        return 0 # Or raise an error, depending on expected input

    hours = 0
    minutes = 0
    
    # Extract hours
    h_match = re.search(r'(\d+)h', duration_str)
    if h_match:
        hours = int(h_match.group(1))
    
    # Extract minutes
    m_match = re.search(r'(\d+)m', duration_str)
    if m_match:
        minutes = int(m_match.group(1))
        
    return hours * 60 + minutes


# --- Routes ---

@app.route('/')
def index():
    unique_origins = get_unique_origins()
    return render_template('index.html', user_id=session.get('user_id'), username=session.get('username'), unique_origins=unique_origins)

@app.route('/search_results', methods=['GET', 'POST'])
def search_results():
    origin = request.values.get('origin')
    destination = request.values.get('destination')
    departure_date = request.values.get('departure_date')
    return_date = request.values.get('return_date') # Now handling return_date
    passengers = request.values.get('passengers', 1)
    journey_type = request.values.get('journey_type', 'one_way') # Get journey type

    # Validate origin and destination are different
    if origin == destination:
        flash('Origin and Destination cannot be the same. Please select different locations.', 'error')
        return redirect(url_for('index'))

    selected_modes = request.args.getlist('mode')
    sort_by = request.args.get('sort', 'cheapest')
    show_student_discounts = request.args.get('discount') == 'student'

    results = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            base_query = "SELECT * FROM journeys WHERE origin = %s AND destination = %s"
            query_params = [origin, destination]

            if selected_modes:
                mode_placeholders = ', '.join(['%s'] * len(selected_modes))
                base_query += f" AND mode IN ({mode_placeholders})"
                query_params.extend(selected_modes)

            cursor.execute(base_query, tuple(query_params))
            db_journeys = cursor.fetchall()

            processed_results = []
            for journey in db_journeys:
                mode_icon = '' # This will be replaced by Lucide icons in HTML

                current_price = float(journey['price'])
                student_discount_applied_to_journey = False
                
                # Simulate student discount logic for display
                if show_student_discounts:
                    current_price = round(current_price * 0.8, 2) # 20% discount
                    student_discount_applied_to_journey = True
                elif random.random() < 0.3: # Randomly apply discount if filter is OFF
                    current_price = round(current_price * 0.8, 2)
                    student_discount_applied_to_journey = True

                co2_value = parse_carbon_footprint(journey['carbon_footprint'])

                # For return journeys, simulate doubling cost/CO2/duration
                if journey_type == 'return': # Use journey_type from form
                    current_price *= 2 # Simple doubling for return
                    co2_value *= 2
                    # Simple duration doubling, could be more complex
                    duration_minutes = parse_duration_to_minutes(journey['duration']) * 2
                    hours = duration_minutes // 60
                    minutes = duration_minutes % 60
                    travel_time_display = f"{hours}h {minutes}m"
                else:
                    travel_time_display = journey['duration']


                processed_results.append({
                    'id': journey['id'],
                    'mode': journey['mode'],
                    'mode_icon': mode_icon, # Will be ignored by new HTML, but kept for compatibility
                    'route': f"{journey['origin']} to {journey['destination']} by {journey['mode']}",
                    'times': f"Departs: {departure_date} (Time TBD)", # Actual times from DB would be better
                    'stops': 'Direct', # Simplified for now
                    'travel_time': travel_time_display,
                    'cost': current_price,
                    'co2_emissions': co2_value,
                    'student_discount': student_discount_applied_to_journey,
                    'description': journey['description']
                })

            # Apply sorting
            if sort_by == 'cheapest':
                results = sorted(processed_results, key=lambda x: x['cost'])
            elif sort_by == 'fastest':
                # Sort by parsed minutes duration
                results = sorted(processed_results, key=lambda x: parse_duration_to_minutes(x['travel_time']))
            elif sort_by == 'lowest_co2':
                results = sorted(processed_results, key=lambda x: x['co2_emissions'])
            else:
                results = processed_results # Default or no specific sort

            if not results:
                flash(f'No journeys found from {origin} to {destination}. Please try different locations or dates.', 'info')

        except mysql.connector.Error as err:
            flash(f'Error fetching journeys: {err}', 'error')
        finally:
            if conn:
                cursor.close()
                conn.close()

    return render_template('results.html',
                           origin=origin,
                           destination=destination,
                           departure_date=departure_date,
                           return_date=return_date,
                           passengers=passengers,
                           results=results,
                           user_id=session.get('user_id'),
                           username=session.get('username'),
                           selected_modes=selected_modes,
                           sort_by=sort_by,
                           show_student_discounts=show_student_discounts,
                           journey_type=journey_type) # Pass journey_type to results.html

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
                existing_user = cursor.fetchone()
                if existing_user:
                    flash('Username or Email already exists. Please choose another.', 'error')
                else:
                    cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
                                   (username, password, email))
                    conn.commit()
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login'))
            except mysql.connector.Error as err:
                flash(f'Database error during registration: {err}', 'error')
                conn.rollback()
            finally:
                if conn:
                    cursor.close()
                    conn.close()
    return render_template('register.html', user_id=session.get('user_id'), username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()

                if user and verify_password(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Invalid username or password.', 'error')
            except mysql.connector.Error as err:
                flash(f'Database error during login: {err}', 'error')
            finally:
                if conn:
                    cursor.close()
                    conn.close()
    return render_template('login.html', user_id=session.get('user_id'), username=session.get('username'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/select_journey/<int:journey_id>', methods=['POST'])
def select_journey(journey_id):
    if 'user_id' not in session:
        flash('Please log in to book a journey.', 'info')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM journeys WHERE id = %s", (journey_id,))
            selected_journey_db = cursor.fetchone()

            if selected_journey_db:
                departure_date = request.form.get('departure_date')
                return_date = request.form.get('return_date')
                passengers = int(request.form.get('passengers'))
                journey_type = request.form.get('journey_type', 'one_way') # Get journey type from form

                # Recalculate cost, co2, and duration based on return_date for display on booking details
                current_price = float(selected_journey_db['price'])
                co2_value = parse_carbon_footprint(selected_journey_db['carbon_footprint'])
                travel_time_display = selected_journey_db['duration']

                if journey_type == 'return': # Use journey_type for calculation
                    current_price *= 2
                    co2_value *= 2
                    duration_minutes = parse_duration_to_minutes(selected_journey_db['duration']) * 2
                    hours = duration_minutes // 60
                    minutes = duration_minutes % 60
                    travel_time_display = f"{hours}h {minutes}m"

                # Calculate total_price here before storing in session
                total_price_for_booking = current_price * passengers

                session['selected_journey'] = {
                    'id': selected_journey_db['id'],
                    'origin': selected_journey_db['origin'],
                    'destination': selected_journey_db['destination'],
                    'mode': selected_journey_db['mode'],
                    'carbon_footprint': co2_value, # Store the potentially doubled CO2
                    'price': current_price, # Store the potentially doubled price (per person)
                    'total_price': total_price_for_booking, # Add total_price to session
                    'duration': travel_time_display, # Store the potentially doubled duration
                    'description': selected_journey_db['description'],
                    'departure_date': departure_date,
                    'return_date': return_date,
                    'passengers': passengers,
                    'journey_type': journey_type # Store journey_type in session
                }
                return redirect(url_for('booking_details'))
            else:
                flash('Journey not found.', 'error')
                return redirect(url_for('index'))
        except mysql.connector.Error as err:
            flash(f'Error selecting journey: {err}', 'error')
            return redirect(url_for('index'))
        finally:
            if conn:
                cursor.close()
                conn.close()
    return redirect(url_for('index'))

@app.route('/booking_details', methods=['GET', 'POST'])
def booking_details():
    if 'user_id' not in session:
        flash('Please log in to complete your booking.', 'info')
        return redirect(url_for('login'))

    selected_journey = session.get('selected_journey')
    if not selected_journey:
        flash('No journey selected. Please search and select a journey first.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # This POST is for confirming details and proceeding to payment
        return redirect(url_for('payment'))

    return render_template('booking_details.html',
                           journey=selected_journey, # Renamed 'journey' to 'booking' for consistency with confirmation/account
                           user_id=session.get('user_id'),
                           username=session.get('username'))

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        flash('Please log in to complete your payment.', 'info')
        return redirect(url_for('login'))

    selected_journey = session.get('selected_journey')
    if not selected_journey:
        flash('No journey selected for payment. Please select a journey first.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        card_number = request.form.get('card_number')
        expiry_date = request.form.get('expiry_date')
        cvv = request.form.get('cvv')
        cardholder_name = request.form.get('cardholder_name') # Added cardholder name

        if not (card_number and expiry_date and cvv and cardholder_name):
            flash('Please fill in all payment details.', 'error')
            return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))

        if not (card_number.isdigit() and len(card_number) in [13, 15, 16]):
            flash('Invalid card number. Please enter a valid 13-16 digit number.', 'error')
            return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))

        if not (expiry_date and '/' in expiry_date and len(expiry_date) == 5):
            flash('Invalid expiry date format. Please use MM/YY.', 'error')
            return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))
        else:
            try:
                month, year = map(int, expiry_date.split('/'))
                current_full_year = datetime.now().year
                full_year = 2000 + year if year < 100 else year
                
                if not (1 <= month <= 12 and full_year >= current_full_year and (full_year > current_full_year or month >= datetime.now().month)):
                    flash('Invalid expiry date. Date must be in the future.', 'error')
                    return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))
            except ValueError:
                flash('Invalid expiry date format. Please use MM/YY.', 'error')
                return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))

        if not (cvv.isdigit() and len(cvv) in [3, 4]):
            flash('Invalid CVV. Please enter a 3 or 4 digit number.', 'error')
            return render_template('payment.html', journey=selected_journey, user_id=session.get('user_id'), username=session.get('username'))


        booking_ref = str(uuid.uuid4())[:8].upper()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                # Use the departure_date from the selected_journey in session as the booking_date for the DB
                # Note: booking_date in DB is DATETIME, but we're storing just the date part from HTML input
                booking_date_for_db = selected_journey['departure_date']

                cursor.execute(
                    "INSERT INTO bookings (user_id, journey_id, passengers, total_price, booking_date, payment_method, payment_status, transaction_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (session['user_id'],
                     selected_journey['id'],
                     selected_journey['passengers'],
                     selected_journey['total_price'], # Use the total_price already calculated and stored in session
                     booking_date_for_db,
                     'simulated-card', # Payment method is hardcoded as simulated
                     'completed',
                     booking_ref)
                )
                conn.commit()
                flash('Payment successful and booking confirmed!', 'success')
                session['last_booking_ref'] = booking_ref
                session.pop('selected_journey', None) # Clear selected journey from session after successful booking
                return redirect(url_for('confirmation'))
            except mysql.connector.Error as err:
                flash(f'Database error during booking: {err}', 'error')
                conn.rollback()
            finally:
                if conn:
                    cursor.close()
                    conn.close()
        else:
            flash('Could not connect to database to complete booking.', 'error')

    return render_template('payment.html',
                           journey=selected_journey,
                           user_id=session.get('user_id'),
                           username=session.get('username'))

@app.route('/confirmation')
def confirmation():
    if 'user_id' not in session:
        flash('Please log in to view your confirmation.', 'info')
        return redirect(url_for('login'))

    booking_ref = session.get('last_booking_ref')
    booking_details = None
    if booking_ref:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                query = """
                SELECT b.*, j.origin, j.destination, j.mode, j.duration, j.carbon_footprint, j.description AS journey_description
                FROM bookings b
                JOIN journeys j ON b.journey_id = j.id
                WHERE b.transaction_id = %s AND b.user_id = %s
                """
                cursor.execute(query, (booking_ref, session['user_id']))
                booking_details = cursor.fetchone()
                if booking_details:
                    # Ensure carbon_footprint is parsed to float for display
                    booking_details['carbon_footprint'] = parse_carbon_footprint(booking_details.get('carbon_footprint', '0.0kg CO2e'))
            except mysql.connector.Error as err:
                flash(f'Error fetching booking details: {err}', 'error')
            finally:
                if conn:
                    cursor.close()
                    conn.close()

    if not booking_details:
        flash('Could not find your booking details.', 'error')
        return redirect(url_for('account'))

    return render_template('confirmation.html',
                           booking=booking_details,
                           user_id=session.get('user_id'),
                           username=session.get('username'))

@app.route('/account')
def account():
    if 'user_id' not in session:
        flash('Please log in to view your account.', 'info')
        return redirect(url_for('login'))

    user_bookings = []
    total_co2_saved = 0.0
    total_money_saved = 0.0
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT b.*, j.origin, j.destination, j.mode, j.duration, j.carbon_footprint, j.price AS journey_base_price
            FROM bookings b
            JOIN journeys j ON b.journey_id = j.id
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC
            """
            cursor.execute(query, (session['user_id'],))
            user_bookings = cursor.fetchall()

            upcoming_bookings = []
            past_bookings = []
            today = date.today()

            for booking in user_bookings:
                # Ensure booked_at is a datetime object for strftime
                if isinstance(booking.get('booked_at'), date) and not isinstance(booking.get('booked_at'), datetime):
                    booking['booked_at'] = datetime.combine(booking['booked_at'], datetime.min.time())

                # Ensure booking_date is a datetime object for strftime
                if isinstance(booking.get('booking_date'), date) and not isinstance(booking.get('booking_date'), datetime):
                    booking['booking_date'] = datetime.combine(booking['booking_date'], datetime.min.time())

                booking_departure_date = booking.get('booking_date')

                if booking_departure_date is None:
                    dep_date_for_comparison = date.min
                elif isinstance(booking_departure_date, datetime):
                    dep_date_for_comparison = booking_departure_date.date()
                elif isinstance(booking_departure_date, date):
                    dep_date_for_comparison = booking_departure_date
                else:
                    try:
                        dep_date_for_comparison = datetime.strptime(str(booking_departure_date), '%Y-%m-%d').date()
                    except ValueError:
                        dep_date_for_comparison = date.min

                parsed_carbon_footprint = parse_carbon_footprint(booking.get('carbon_footprint', '0.0kg CO2e'))
                booking['carbon_footprint'] = parsed_carbon_footprint

                if dep_date_for_comparison >= today:
                    upcoming_bookings.append(booking)
                else:
                    past_bookings.append(booking)
                    total_co2_saved += parsed_carbon_footprint
                    total_money_saved += float(booking['total_price']) * 0.10 # Simulated saving

        except mysql.connector.Error as err:
            flash(f'Error fetching your bookings: {err}', 'error')
        finally:
            if conn:
                cursor.close()
                conn.close()

    return render_template('account.html',
                           user_id=session.get('user_id'),
                           username=session.get('username'),
                           upcoming_bookings=upcoming_bookings,
                           past_bookings=past_bookings,
                           total_co2_saved=round(total_co2_saved, 2),
                           total_money_saved=round(total_money_saved, 2))

# New routes for booking actions
@app.route('/view_booking_details/<string:transaction_id>')
def view_booking_details(transaction_id):
    if 'user_id' not in session:
        flash('Please log in to view booking details.', 'info')
        return redirect(url_for('login'))

    booking_details = None
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT b.*, j.origin, j.destination, j.mode, j.duration, j.carbon_footprint, j.description AS journey_description
            FROM bookings b
            JOIN journeys j ON b.journey_id = j.id
            WHERE b.transaction_id = %s AND b.user_id = %s
            """
            cursor.execute(query, (transaction_id, session['user_id']))
            booking_details = cursor.fetchone()
            if booking_details:
                booking_details['carbon_footprint'] = parse_carbon_footprint(booking_details.get('carbon_footprint', '0.0kg CO2e'))
                # Ensure booking_date is a datetime object for strftime in booking_view.html
                if isinstance(booking_details.get('booking_date'), date) and not isinstance(booking_details.get('booking_date'), datetime):
                    booking_details['booking_date'] = datetime.combine(booking_details['booking_date'], datetime.min.time())
                # Ensure booked_at is a datetime object for strftime in booking_view.html
                if isinstance(booking_details.get('booked_at'), date) and not isinstance(booking_details.get('booked_at'), datetime):
                    booking_details['booked_at'] = datetime.combine(booking_details['booked_at'], datetime.min.time())

        except mysql.connector.Error as err:
            flash(f'Error fetching booking details: {err}', 'error')
        finally:
            if conn:
                cursor.close()
                conn.close()

    if not booking_details:
        flash('Booking details not found or you do not have permission to view it.', 'error')
        return redirect(url_for('account'))

    return render_template('booking_view.html', # Changed to booking_view.html
                           booking=booking_details,
                           user_id=session.get('user_id'),
                           username=session.get('username'))

# Removed the /download_ticket/<string:transaction_id> route
# Removed the /generate_ticket_pdf/<string:transaction_id> route

@app.route('/cancel_booking/<string:transaction_id>', methods=['POST'])
def cancel_booking(transaction_id):
    if 'user_id' not in session:
        flash('Please log in to cancel bookings.', 'info')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Update status to 'cancelled'
            cursor.execute("UPDATE bookings SET payment_status = %s WHERE transaction_id = %s AND user_id = %s",
                           ('cancelled', transaction_id, session['user_id']))
            conn.commit()
            if cursor.rowcount > 0:
                flash(f'Booking {transaction_id} has been cancelled. (Refund simulated)', 'success')
            else:
                flash('Booking not found or already cancelled.', 'error')
        except mysql.connector.Error as err:
            flash(f'Error cancelling booking: {err}', 'error')
            conn.rollback()
        finally:
            if conn:
                cursor.close()
                conn.close()
    return redirect(url_for('account'))

@app.route('/modify_booking/<string:transaction_id>', methods=['GET', 'POST'])
def modify_booking(transaction_id):
    if 'user_id' not in session:
        flash('Please log in to modify bookings.', 'info')
        return redirect(url_for('login'))
    
    booking_details = None
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT b.*, j.origin, j.destination, j.mode, j.duration, j.carbon_footprint, j.description AS journey_description, j.price AS journey_base_price
            FROM bookings b
            JOIN journeys j ON b.journey_id = j.id
            WHERE b.transaction_id = %s AND b.user_id = %s
            """
            cursor.execute(query, (transaction_id, session['user_id']))
            booking_details = cursor.fetchone()
            
            if booking_details:
                # Ensure booking_date is a datetime object for strftime
                if isinstance(booking_details.get('booking_date'), date) and not isinstance(booking_details.get('booking_date'), datetime):
                    booking_details['booking_date'] = datetime.combine(booking_details['booking_date'], datetime.min.time())
                
                # Attempt to infer journey_type if not explicitly stored (e.g., from total_price vs base_price)
                # This is a heuristic and might not be perfectly accurate if discounts/complex pricing exist.
                is_return_journey = False
                expected_one_way_price = float(booking_details['journey_base_price']) * booking_details['passengers']
                if booking_details['total_price'] > (expected_one_way_price * 1.5): # Heuristic check
                    is_return_journey = True
                
                booking_details['journey_type'] = 'return' if is_return_journey else 'one_way'

        except mysql.connector.Error as err:
            flash(f'Error fetching booking details for modification: {err}', 'error')
            if conn: # Ensure connection is closed on early exit
                cursor.close()
                conn.close()
            return redirect(url_for('account')) # Redirect early on error

    if not booking_details:
        flash('Booking details not found for modification or you do not have permission to view it.', 'error')
        return redirect(url_for('account'))

    if request.method == 'POST':
        new_departure_date = request.form.get('departure_date')
        new_return_date = request.form.get('return_date')
        new_passengers = int(request.form.get('passengers'))
        new_journey_type = request.form.get('journey_type', 'one_way')

        # Basic validation (more robust validation should be done client-side and server-side)
        if not new_departure_date or new_passengers < 1:
            flash('Invalid input for date or passengers.', 'error')
            if conn: # Ensure connection is closed on early exit
                cursor.close()
                conn.close()
            return redirect(url_for('modify_booking', transaction_id=transaction_id))
        
        # Recalculate total_price based on new passengers and journey type
        # Convert to float for arithmetic operations to avoid TypeError
        recalculated_price_per_person = float(booking_details['journey_base_price'])
        if new_journey_type == 'return':
            recalculated_price_per_person *= 2 # Double for return journey
        
        new_total_price = recalculated_price_per_person * new_passengers

        try:
            # Re-establish connection and cursor if it was closed due to an earlier error
            if not conn or not conn.is_connected():
                conn = get_db_connection()
                if not conn:
                    flash('Database connection lost during update.', 'error')
                    return redirect(url_for('account'))

            cursor = conn.cursor() # Get a new cursor for the update
            update_query = """
            UPDATE bookings
            SET booking_date = %s, passengers = %s, total_price = %s
            WHERE transaction_id = %s AND user_id = %s
            """
            update_params = (new_departure_date, new_passengers, new_total_price, transaction_id, session['user_id'])
            
            # If return date is relevant and changed, you might need to store it.
            # Currently, return_date is not stored in the bookings table.
            # For this modification, we'll just update the main booking fields.

            cursor.execute(update_query, update_params)
            conn.commit()
            flash(f'Booking {transaction_id} updated successfully!', 'success')
            return redirect(url_for('account')) # Redirect back to account page
        except mysql.connector.Error as err:
            flash(f'Error updating booking: {err}', 'error')
            conn.rollback()
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    # For GET request, render the form with current booking details
    return render_template('modify_booking.html',
                           booking=booking_details,
                           user_id=session.get('user_id'),
                           username=session.get('username'))


@app.route('/rebook_journey/<int:journey_id>')
def rebook_journey(journey_id):
    if 'user_id' not in session:
        flash('Please log in to rebook a journey.', 'info')
        return redirect(url_for('login'))
    
    flash(f'Rebooking journey {journey_id} is not yet fully implemented. Please use the search to rebook.', 'info')
    # For a real rebook, you'd pre-populate the search form or directly go to booking details.
    return redirect(url_for('index'))


@app.route('/help')
def help():
    return render_template('help.html', user_id=session.get('user_id'), username=session.get('username'))

# New routes for About Us and Why Us
@app.route('/about')
def about():
    return render_template('about.html', user_id=session.get('user_id'), username=session.get('username'))

@app.route('/why_us')
def why_us():
    return render_template('why_us.html', user_id=session.get('user_id'), username=session.get('username'))


if __name__ == '__main__':
    app.secret_key = 'your_very_secret_key_here' # **IMPORTANT: CHANGE THIS TO A LONG, RANDOM STRING IN PRODUCTION**
    app.run(debug=True)
