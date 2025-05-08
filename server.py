from flask import Flask, flash, redirect, render_template, request, url_for, session
import pandas as pd
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

MAX_DURATION_LOW_PRIO_HOURS = 24
STATUS_CODE_OK = 0
STATUS_CODE_BUSY = -1
STATUS_CODE_BUSY_LOW_PRIO = -2
STATUS_CODE_ALREADY_RESERVED = -3

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")  # Default password: admin123

# create database tables if they doesn't exist
tables = {
    '.data/reservations.csv' : ['id', 'username', 'target', 'from', 'to', 'high_priority'],
    '.data/users.csv' : ['username']
}

for k,v in tables.items():
    if not os.path.exists(k):
        pd.DataFrame(columns=v).to_csv(k, index=False)


from werkzeug.middleware.proxy_fix import ProxyFix
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

secret_key = os.urandom(16).hex()
app.config['SECRET_KEY'] = secret_key

# ------------ utils ------------

def get_all_reservations():
    """ 
    Read csv database and converts to proper datetime 
    """
    df = pd.read_csv('.data/reservations.csv', parse_dates=['from', 'to'])
    df['high_priority'] = df['high_priority'].astype(bool)
    
    return df


def check_conflicting(db, datefrom, dateto):
    """
    Check if the reservation overlaps with existing ones, 
    returns a dataframe with the conflicting reservations, and the status code
    """

    # reservation willing to start between start and end of existing reservation
    busy = ( (datefrom >= db['from']) & (datefrom <= db['to']) )
    # reservation willing to end after the start of exisiting reservation
    busy = busy | ( (dateto >= db['from']) & (datefrom <= db['to']) )
    
    # keep only active reservations
    db = db[busy]

    if len(db) == 0:
        # if no busy reservation, return empty dataframe
        return pd.DataFrame(), STATUS_CODE_OK

    # if all high priority, mark as busy
    if db['high_priority'].all():
        return db, STATUS_CODE_BUSY
    # if there are conflicts at low priority
    elif (db['high_priority'] == False).any():
        # check if the reservation is active for more than max time
        db_low_prio = db[(db['to'] - db['from']).dt.total_seconds() / 3600 > MAX_DURATION_LOW_PRIO_HOURS]
        if len(db_low_prio) > 0:
            # in which case we can overtake the reservation
            return db_low_prio, STATUS_CODE_BUSY_LOW_PRIO
        else:
            # if no, it is a conflict. 
            return db, STATUS_CODE_BUSY
    
    


def filter_reservations(db, target, datefrom, dateto):
    """ 
    Filter reservations by target and date range 
    """
    
    if target != 'all':
        db = db[db['target'] == target]
    
    return check_conflicting(db, datefrom, dateto)

    

def validate(rsvp):
    """ here the user wants to reserve, check if the reservation is valid. If there are conflicts and the user is 
     allowed to overtake, delete the conflicting reservation and return None."""
    
    current_rsvp = get_all_reservations()

    # if user already has a not finished reservation, return error
    if len(current_rsvp[(current_rsvp['username'] == rsvp['username']) & (current_rsvp['to'] > pd.to_datetime('now'))]) > 0:
        return STATUS_CODE_ALREADY_RESERVED
    
    df = current_rsvp[current_rsvp['target'] == rsvp['target']]
    rsvp['from'] = pd.to_datetime(rsvp['from'])
    rsvp['to'] = pd.to_datetime(rsvp['to'])

    # check if target is available in the selected time range (must meet all critieria)
    conflicts, s = check_conflicting(df, rsvp['from'], rsvp['to'])

    for _id in conflicts['id'].values:
        # delete the conflicting reservation
        print("Conflicting ID:", _id)
        current_rsvp = current_rsvp[current_rsvp['id'] != _id]
        
    update_database(current_rsvp, override=True)
    
    s = current_rsvp['id'].max() + 1 if len(current_rsvp) > 0 else 0
    return s

def update_database(df, override=False):
    df.to_csv('.data/reservations.csv', 
              columns=['id', 'username', 'target', 'from', 'to', 'high_priority'], 
              index=False,
              mode='a' if not override else 'w', 
              header=override)

#--------------- handlers --------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create', methods=('GET', 'POST'))
def create():

    df = pd.read_csv('.data/users.csv')
    users = df.to_dict(orient='records')

    if request.method == 'POST':
        if 'check' in request.form: # user asked available slots
            
            target = request.form['target']
            datefrom = pd.to_datetime(request.form['from'])
            dateto = pd.to_datetime(request.form['to'])
            
            rsvp_df, status_code = filter_reservations(
                get_all_reservations(), 
                target,
                datefrom,
                dateto
            )
            
            # store session for later confirmation
            session['target'] = request.form['target']
            session['from'] = request.form['from']
            session['to'] = request.form['to']

            show_rsvp = True
            allow = False
            if datefrom > dateto:
                flash('Invalid date range. Please select a valid date range.', category='danger')
                show_rsvp = False
            elif status_code == STATUS_CODE_BUSY:
                flash(
                    f'The target is not available in the selected time range and in use from less than {MAX_DURATION_LOW_PRIO_HOURS} hours. '
                    f'Reservation policy: low priority reservations are guaranteed for {MAX_DURATION_LOW_PRIO_HOURS} hours. '
                    'After that, they become best effort and will be released '
                    'if you requests the same slot.', 
                category='danger')

            elif status_code == STATUS_CODE_BUSY_LOW_PRIO:
                flash(f'The target is in use by more than {MAX_DURATION_LOW_PRIO_HOURS} hours. You can overtake current user', category='warning')
                allow = True
            else:
                flash('The target is available, proceed with button below.', category='success')
                allow = True
            
            return render_template('create.html',
                                   users=users,
                                   show_rsvp=show_rsvp,
                                   reservations=rsvp_df.to_dict(orient='records'),
                                   selected_username=session.get('username', None),
                                   show_rsvp_button=allow,)

        elif 'reserve' in request.form: # user wants to reserve
            rsvp = {
                'from' : session['from'],
                'username': request.form['username'],
                'to': session['to'],
                'target': session['target'],
                'high_priority': request.form.get('high_priority', False) == 'on'
            }
            
            # return None if valid, error message otherwise
            new_id = validate(rsvp)
            
            if new_id < 0:
                if new_id == STATUS_CODE_ALREADY_RESERVED:
                    flash('You already have a reservation in progress. Please finish it before making a new one.', category='danger')
                elif new_id == STATUS_CODE_BUSY:    
                    # error, not possible to reserve
                    flash('The target is not available in the selected time range. Please find a different time.', category='danger')
                return redirect(url_for('create'))
            else:
                # reserve!
                rsvp['id'] = new_id
                update_database(pd.DataFrame([rsvp]))
                return redirect(url_for('confirm'))
    
    else:   # GET (first time we load the page)
        username = session.get('username', None)
        reservations = session.get('reservations', None)
        return render_template('create.html', users=users, selected_username=username, reservations=reservations)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin login required', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Admin login successful', 'success')
            return redirect(url_for('create'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Admin logged out', 'info')
    return redirect(url_for('index'))

@app.route('/delete_reservation', methods=['POST'])
@admin_required
def delete_reservation():
    reservation_id = request.form.get('reservation_id')
    username = request.form.get('username', '')
    
    if reservation_id:
        # Get all reservations
        reservations = get_all_reservations()
        
        # Find and remove the reservation with the given ID
        if int(reservation_id) in reservations['id'].values:
            reservations = reservations[reservations['id'] != int(reservation_id)]
            reservations.to_csv('.data/reservations.csv', index=False)
            flash('Reservation deleted successfully', 'success')
        else:
            flash('Reservation not found', 'danger')
    
    # Redirect back to the list view with the same username filter
    if username:
        return redirect(url_for('list', username=username))
    else:
        return redirect(url_for('list'))
    

@app.route('/list')
def list():
    """
    Display all reservations for a specific user
    """
    # Get username from query parameters (sent from the form in create.html)
    username = request.args.get('username', None)
    
    # Get all reservations
    reservations = get_all_reservations()
    
    # Filter by username if provided
    if username:
        reservations = reservations[(reservations['username'] == username) & (reservations['to'] > pd.to_datetime('now'))]
        
    # Sort reservations by start date
    reservations = reservations.sort_values(by=['from'], ascending=True)
    
    # Get the list of users for the dropdown
    users_df = pd.read_csv('.data/users.csv')
    users = users_df.to_dict(orient='records')
    
    session['username'] = username
    session['reservations'] = reservations.to_dict(orient='records')

    return redirect(url_for('create'))
    # render_template(
    #     'create.html',
    #     reservations=reservations.to_dict(orient='records'),
    #     users=users,
    #     selected_username=username
    # )    

@app.route('/confirm', methods=('GET', 'POST'))
def confirm():
    session.clear()
    return render_template('confirm.html')

@app.route('/about', methods=('GET', 'POST'))
def about():
    return render_template('about.html')

@app.route('/toggle_priority', methods=['POST'])
@admin_required
def toggle_priority():
    reservation_id = request.form.get('reservation_id')
    username = request.form.get('username', '')
    
    if reservation_id:
        # Get all reservations
        reservations = get_all_reservations()
        
        # Find the reservation with the given ID
        if int(reservation_id) in reservations['id'].values:
            # Get the current priority status
            idx = reservations.index[reservations['id'] == int(reservation_id)][0]
            
            # Toggle the priority
            reservations.at[idx, 'high_priority'] = not reservations.at[idx, 'high_priority']
            
            # Save the changes
            reservations.to_csv('.data/reservations.csv', index=False)
            
            new_status = "high" if reservations.at[idx, 'high_priority'] else "low"
            flash(f'Reservation priority updated to {new_status}', 'success')
        else:
            flash('Reservation not found', 'danger')
    
    # Redirect back to the list view with the same username filter
    if username:
        return redirect(url_for('list', username=username))
    else:
        return redirect(url_for('list'))