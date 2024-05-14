from flask import Flask, flash, redirect, render_template, request, url_for, session
import pandas as pd
import os

# create database tables if they doesn't exist
tables = {
    '.data/reservations.csv' : ['username', 'target', 'from', 'to'],
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
    return df


def filter_reservations(db, target, datefrom, dateto):
    """ 
    Filter reservations by target and date range 
    """
    
    if target != 'all':
        db = db[db['target'] == target]
    
    return db[((datefrom >= db['from']) & (datefrom <= db['to'])) | \
        ((dateto >= db['from']) & (dateto <= db['to']))]


def is_valid(rsvp):
    
    df = get_all_reservations()
    
    df = df[df['target'] == rsvp['target']]
    rsvp['from'] = pd.to_datetime(rsvp['from'])
    rsvp['to'] = pd.to_datetime(rsvp['to'])

    # check if target is available in the selected time range
    busy = ((df['from'] <= rsvp['from']) & (df['to'] >= rsvp['from'])) | \
        ((rsvp['to'] >= df['from']) & (rsvp['to'] <= df['to']))
    
    if busy.any():
        return 'The target is not available in the selected time range. Please find a different time.'

    return None

def save(rsvp):
    df = pd.DataFrame([rsvp])
    df.to_csv('.data/reservations.csv', 
              columns=['username', 'target', 'from', 'to'], 
              index=False,
              mode='a', header=False)

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
            
            rsvp_df = filter_reservations(
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
            if datefrom > dateto:
                flash('Invalid date range. Please select a valid date range.', category='danger')
                show_rsvp = False
            elif (len(rsvp_df)):
                flash('The target is not available in the selected time range. Please find a different time.', category='warning')
            else:
                flash('The target is available, proceed with button below.', category='success')
            return render_template('create.html',
                                   users=users,
                                   show_rsvp=show_rsvp,
                                   reservations=rsvp_df.to_dict(orient='records'))

        elif 'reserve' in request.form: # user wants to reserve
            rsvp = {
                'from' : session['from'] ,
                'username': request.form['username'],
                'to': session['to'],
                'target': session['target']
            }
            
            # return None if valid, error message otherwise
            msg = is_valid(rsvp)
            
            if msg:
                flash(msg, category='danger')
                return redirect(url_for('create'))
            else:
                save(rsvp)
                return redirect(url_for('confirm'))
    
    else:   # GET (first time we load the page)
        return render_template('create.html', users=users)

# @app.route('/list', methods=('GET', 'POST'))
# def list():
    
#     df = get_all_reservations()
#     if request.method == 'POST':
        

#     # df to list of dictionaries
#     #reservations = df.to_dict(orient='records')
#     return render_template('list.html', reservations=reservations)

@app.route('/confirm', methods=('GET', 'POST'))
def confirm():
    session.clear()
    return render_template('confirm.html')

@app.route('/about', methods=('GET', 'POST'))
def about():
    return render_template('about.html')