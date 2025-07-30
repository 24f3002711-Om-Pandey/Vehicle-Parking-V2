from flask import Blueprint, render_template, request, url_for, redirect, flash, session
from models import User, Parking_lot, Parking_Spot, Reservation
from db import db_session
from datetime import datetime
from functools import wraps
from sqlalchemy import func

bp = Blueprint('main', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Admin access required.', 'error')
            return redirect(url_for('main.login'))
        user = db_session.query(User).get(user_id)
        if not user or not getattr(user, 'is_admin', False):
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def check_banned(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if user_id:
            user = db_session.query(User).get(user_id)
            if user and user.banned and not user.is_admin:
                session.pop('user_id', None)  # Clear the session
                flash('Your account has been banned. Please contact an administrator.', 'error')
                return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Home Page ---
@bp.route('/')
@bp.route('/home')
@check_banned
def index():
    """
    If not logged in, show a landing page with login/register options.
    If logged in, show the parking lots.
    If user is banned, redirect to login with error message (handled by check_banned decorator).
    """
    user_id = session.get('user_id')
    if not user_id:
        return render_template('landing.html')
    
    lots = db_session.query(Parking_lot).all()
    return render_template('index.html', lots=lots)

# --- User Authentication ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    GET: Displays the login form.
    POST: Authenticates the user.
    """
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        user = db_session.query(User).filter_by(Username=username).first()
        if user and user.check_password(password):
            # Check if user is banned
            if user.banned and not user.is_admin:
                flash('Your account has been banned. Please contact an administrator.', 'error')
                return render_template('login.html')
            
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            if user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            return redirect(url_for('main.profile'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles user registration.
    GET: Displays the registration form.
    POST: Creates a new user account.
    """
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        name = request.form['Name']
        email = request.form['Email'] # Added email field from form

        # Check if username or email already exists
        existing_user = db_session.query(User).filter((User.Username == username) | (User.Email == email)).first()
        if existing_user:
            flash('Username or Email already exists. Please choose a different one.', 'error')
            return render_template('Register.html', username=username, name=name, email=email) # Pass back data to repopulate form

        user = User(Username=username, Name=name, Email=email)
        user.set_password(password)
        db_session.add(user)
        db_session.commit()
        flash('Registered successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('Register.html')

@bp.route('/logout')
def logout():
    """
    Logs out the current user by clearing the session.
    """
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

# --- User Profile ---
@bp.route('/profile')
@check_banned
def profile():
    """
    Displays the user's profile and their reservations.
    Requires user to be logged in and not banned (handled by check_banned decorator).
    """
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'error')
        return redirect(url_for('main.login'))
    user = db_session.query(User).get(session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'error')
        session.pop('user_id', None) # Clear invalid session
        return redirect(url_for('main.login'))

    reservations = db_session.query(Reservation).filter_by(User_id=user.id).all()
    # Enrich reservations with lot and spot info
    enriched_reservations = []
    for r in reservations:
        spot = db_session.query(Parking_Spot).get(r.Spot_id)
        lot = db_session.query(Parking_lot).get(spot.Lot_id) if spot else None
        enriched_reservations.append({
            "reservation": r,
            "spot": spot,
            "lot": lot
        })
    return render_template('profile.html', user=user, reservations=enriched_reservations)

@bp.route('/history')
@check_banned
def history():
    """
    Displays the user's order history and spending graph.
    Requires user to be logged in and not banned (handled by check_banned decorator).
    """
    if 'user_id' not in session:
        flash('Please log in to view your order history.', 'error')
        return redirect(url_for('main.login'))
    
    user = db_session.query(User).get(session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'error')
        session.pop('user_id', None) # Clear invalid session
        return redirect(url_for('main.login'))
    
    # Get all reservations for the user
    reservations = db_session.query(Reservation).filter_by(User_id=user.id).all()
    
    # Enrich reservations with lot and spot info
    enriched_reservations = []
    for r in reservations:
        spot = db_session.query(Parking_Spot).get(r.Spot_id)
        lot = db_session.query(Parking_lot).get(spot.Lot_id) if spot else None
        enriched_reservations.append({
            "reservation": r,
            "spot": spot,
            "lot": lot
        })
    
    # Calculate monthly spending data for the graph
    monthly_spending = []
    
    # Use SQLAlchemy to get monthly aggregated data
    monthly_data = db_session.query(
        func.strftime('%Y-%m', Reservation.Parking_time).label('month'),
        func.sum(Reservation.Total_Cost).label('total')
    ).filter_by(User_id=user.id)\
    .group_by(func.strftime('%Y-%m', Reservation.Parking_time))\
    .order_by(func.strftime('%Y-%m', Reservation.Parking_time))\
    .all()
    
    # Format the data for Chart.js
    for month, total in monthly_data:
        monthly_spending.append({
            'month': month,
            'amount': float(total)
        })
    
    return render_template('history.html', 
                           user=user, 
                           reservations=enriched_reservations, 
                           monthly_spending=monthly_spending)

@bp.route('/reservation/cancel/<int:reservation_id>', methods=['POST'])
@check_banned
def cancel_reservation(reservation_id):
    """
    Allows a user to cancel their reservation.
    User must be logged in and not banned (handled by check_banned decorator).
    """
    if 'user_id' not in session:
        flash('Please log in to cancel reservations.', 'error')
        return redirect(url_for('main.login'))

    reservation = db_session.query(Reservation).get(reservation_id)
    if not reservation or reservation.User_id != session['user_id']:
        flash('Reservation not found or unauthorized.', 'error')
        return redirect(url_for('main.profile'))

    # Free up the spot
    spot = db_session.query(Parking_Spot).get(reservation.Spot_id)
    if spot:
        spot.Status = 'free'
    db_session.delete(reservation)
    db_session.commit()
    flash('Reservation cancelled successfully.', 'success')
    return redirect(url_for('main.profile'))

# --- Parking Lot CRUD Operations (Admin Only) ---
@bp.route('/lots')
@admin_required
def lots():
    """
    Displays a list of all parking lots.
    """
    lots = db_session.query(Parking_lot).all()
    return render_template('lots.html', lots=lots)

@bp.route('/lots/add', methods=['GET', 'POST'])
@admin_required
def add_lot():
    """
    Handles adding a new parking lot.
    GET: Displays the add lot form.
    POST: Adds the new parking lot to the database.
    """
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            address = request.form['address']
            pin = int(request.form['pin'])
            max_spots = int(request.form['max_spots'])

            # Check for existing lot with same name, address, or pin code
            existing_lot = db_session.query(Parking_lot).filter(
                (Parking_lot.Prime_location_name == name) |
                (Parking_lot.Address == address) |
                (Parking_lot.Pin_Code == pin)
            ).first()
            if existing_lot:
                flash('A parking lot with this name, address, or pin code already exists.', 'error')
                return render_template('add_lot.html', name=name, price=price, address=address, pin=pin, max_spots=max_spots)

            lot = Parking_lot(Prime_location_name=name, Price_Per_Hour=price, Address=address, Pin_Code=pin, Max_Spots=max_spots)
            db_session.add(lot)
            db_session.commit()

            # Optionally, create initial parking spots for the new lot
            for i in range(1, max_spots + 1):
                spot = Parking_Spot(Lot_id=lot.id, Status='free', Spot_number=i)
                db_session.add(spot)
            db_session.commit()

            flash('Parking lot added successfully!', 'success')
            return redirect(url_for('main.lots'))
        except ValueError:
            flash('Invalid input for price, pin code, or max spots. Please enter valid numbers.', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            db_session.rollback() # Rollback in case of error
    return render_template('add_lot.html')

# --- Admin Dashboard ---
@bp.route('/admin')
@admin_required
def admin_dashboard():
    users = db_session.query(User).all()
    reservations = db_session.query(Reservation).join(User).join(Parking_Spot).all()
    lots = db_session.query(Parking_lot).all()
    spots = db_session.query(Parking_Spot).all()
    return render_template('admin_dashboard.html', users=users, reservations=reservations, lots=lots, spots=spots)

@bp.route('/admin/ban/<int:user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    user = db_session.query(User).get(user_id)
    if user:
        if user.Username == 'admin':
            flash('Admin user cannot be banned.', 'error')
        elif not user.is_admin:
            user.banned = True
            db_session.commit()
            flash(f'User {user.Username} has been banned.', 'success')
        else:
            flash('Admins cannot be banned.', 'error')
    else:
        flash('User not found.', 'error')
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/admin/unban/<int:user_id>', methods=['POST'])
@admin_required
def unban_user(user_id):
    user = db_session.query(User).get(user_id)
    if user:
        if user.Username == 'admin':
            flash('Admin user cannot be unbanned.', 'error')
        elif not user.is_admin:
            user.banned = False
            db_session.commit()
            flash(f'User {user.Username} has been unbanned.', 'success')
        else:
            # This case should ideally not be reached if logic is correct
            # but as a safeguard:
            flash('Admins cannot be unbanned.', 'error')
    else:
        flash('User not found.', 'error')
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/admin/analytics')
@admin_required
def admin_analytics():
    total_users = db_session.query(func.count(User.id)).scalar()
    total_banned = db_session.query(func.count(User.id)).filter(User.banned == True).scalar()
    total_lots = db_session.query(func.count(Parking_lot.id)).scalar()
    total_spots = db_session.query(func.count(Parking_Spot.id)).scalar()
    total_reservations = db_session.query(func.count(Reservation.id)).scalar()
    total_revenue = db_session.query(func.coalesce(func.sum(Reservation.Total_Cost), 0)).scalar()
    lot_usage = db_session.query(
        Parking_lot.Prime_location_name,
        func.count(Reservation.id)
    ).join(Parking_Spot, Parking_Spot.Lot_id == Parking_lot.id)\
     .join(Reservation, Reservation.Spot_id == Parking_Spot.id)\
     .group_by(Parking_lot.id).all()
    return render_template(
        'admin_analytics.html',
        total_users=total_users,
        total_banned=total_banned,
        total_lots=total_lots,
        total_spots=total_spots,
        total_reservations=total_reservations,
        total_revenue=total_revenue,
        lot_usage=lot_usage
    )

@bp.route('/admin/search')
@admin_required
def admin_search():
    q = request.args.get('q', '').strip()
    users = []
    lots = []
    reservations = []
    if q:
        users = db_session.query(User).filter(
            (User.Username.ilike(f'%{q}%')) | (User.Email.ilike(f'%{q}%')) | (User.Name.ilike(f'%{q}%'))
        ).all()
        lots = db_session.query(Parking_lot).filter(
            Parking_lot.Prime_location_name.ilike(f'%{q}%')
        ).all()
        reservations = db_session.query(Reservation).join(User).filter(
            (User.Username.ilike(f'%{q}%')) | (User.Name.ilike(f'%{q}%'))
        ).all()
    return render_template('admin_search.html', q=q, users=users, lots=lots, reservations=reservations)

@bp.route('/lot_preview/<int:lot_id>')
@admin_required
def lot_preview(lot_id):
    lot = db_session.query(Parking_lot).get(lot_id)
    if not lot:
        flash('Parking lot not found.', 'error')
        return redirect(url_for('main.lots'))

    spots = db_session.query(Parking_Spot).filter_by(Lot_id=lot_id).all()
    return render_template('lot_preview.html', lot=lot, spots=spots)

# --- Reservations ---
@bp.route('/reserve/<int:lot_id>', methods=['GET', 'POST'])
@check_banned
def reserve(lot_id):
    """
    Handles making a reservation for a parking spot in a specific lot.
    GET: Displays the reservation form.
    POST: Creates new reservation(s).
    User must be logged in, not an admin, and not banned (handled by check_banned decorator).
    """
    if 'user_id' not in session:
        flash('Please log in to make a reservation.', 'error')
        return redirect(url_for('main.login'))

    user = db_session.query(User).get(session['user_id'])
    if user and user.is_admin:
        flash('Admins cannot make reservations.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    lot = db_session.query(Parking_lot).get(lot_id)
    if not lot:
        flash('Parking lot not found.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        parking_time_str = request.form.get('parking_time')
        leaving_time_str = request.form.get('leaving_time')
        num_spots = int(request.form.get('num_spots', 1))

        try:
            parking_time = datetime.fromisoformat(parking_time_str)
            leaving_time = datetime.fromisoformat(leaving_time_str)

            if parking_time >= leaving_time:
                flash('Leaving time must be after parking time.', 'error')
                return render_template('reserve.html', lot=lot, parking_time_str=parking_time_str, leaving_time_str=leaving_time_str)

            # Find free spots in the selected lot
            free_spots = db_session.query(Parking_Spot).filter_by(Lot_id=lot.id, Status='free').limit(num_spots).all()
            if len(free_spots) < num_spots:
                flash(f'Only {len(free_spots)} spot(s) available in this lot at the moment.', 'error')
                return render_template('reserve.html', lot=lot, parking_time_str=parking_time_str, leaving_time_str=leaving_time_str)

            duration_hours = (leaving_time - parking_time).total_seconds() / 3600
            if duration_hours <= 0:
                flash('Reservation duration must be positive.', 'error')
                return render_template('reserve.html', lot=lot, parking_time_str=parking_time_str, leaving_time_str=leaving_time_str)

            total_cost = duration_hours * lot.Price_Per_Hour

            # Create reservations for each spot
            for spot in free_spots:
                reservation = Reservation(
                    Spot_id=spot.id,
                    User_id=session['user_id'],
                    Parking_time=parking_time,
                    Leaving_time=leaving_time,
                    Total_Cost=total_cost
                )
                db_session.add(reservation)
                spot.Status = 'reserved'
            db_session.commit()

            flash(f'Reservation successful! {num_spots} spot(s) confirmed.', 'success')
            return redirect(url_for('main.profile'))

        except ValueError:
            flash('Invalid date/time format. Please use the provided date/time picker.', 'error')
        except Exception as e:
            flash(f'An error occurred during reservation: {e}', 'error')
            db_session.rollback()

    # For GET request or if there's an error on POST, render the form
    return render_template('reserve.html', lot=lot)
