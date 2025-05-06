from flask import Flask, flash, redirect, render_template, request, url_for, session
import pandas as pd
import os

MAX_DURATION_LOW_PRIO_HOURS = 24
STATUS_CODE_OK = 0
STATUS_CODE_BUSY = 1
STATUS_CODE_BUSY_LOW_PRIO = 2

# create database tables if they doesn't exist
tables = {
    '.data/reservations.csv' : ['id', 'username', 'target', 'from', 'to', 'high_priority'],
    '.data/users.csv' : ['username']
}

for k,v in tables.items():
    if not os.path.exists(k):
        pd.DataFrame(columns=v).to_csv(k, index=False)


app = Flask(__name__)

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
    
    if s == STATUS_CODE_BUSY:
        return -1

    new_id = current_rsvp['id'].max() + 1 if len(current_rsvp) > 0 else 0
    return new_id

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
            
            print(len(rsvp_df))
            return render_template('create.html',
                                   users=users,
                                   show_rsvp=show_rsvp,
                                   reservations=rsvp_df.to_dict(orient='records'),
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
                # error, not possible to reserve
                flash('The target is not available in the selected time range. Please find a different time.', category='danger')
                return redirect(url_for('create'))
            else:
                # reserve!
                rsvp['id'] = new_id
                update_database(pd.DataFrame([rsvp]))
                return redirect(url_for('confirm'))
    
    else:   # GET (first time we load the page)
        return render_template('create.html', users=users)

@app.route('/list', methods=('GET', 'POST'))
def list():
    pass
    

@app.route('/confirm', methods=('GET', 'POST'))
def confirm():
    session.clear()
    return render_template('confirm.html')

@app.route('/about', methods=('GET', 'POST'))
def about():
    return render_template('about.html')