from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'mybudgetsecret'

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'manager'
app.config['MYSQL_DB'] = 'budget_db'

mysql = MySQL(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Class
class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if user:
        return User(user[0], user[1])
    return None

# Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))

# Register Route
@app.route('/register', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))
    return render_template('register.html')


# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        if user:
            login_user(User(user[0], username))
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# Dashboard Route
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    # Add Expense
    if request.method == 'POST' and 'amount' in request.form:
        amount = request.form['amount']
        reason = request.form['reason']
        today = datetime.today().date()
        cur.execute("INSERT INTO expenses (user_id, amount, reason, date) VALUES (%s, %s, %s, %s)",
                    (current_user.id, amount, reason, today))
        mysql.connection.commit()

    # Date filter
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    if start_date and end_date:
        cur.execute("""
            SELECT amount, reason, date FROM expenses 
            WHERE user_id = %s AND date BETWEEN %s AND %s
            ORDER BY date DESC
        """, (current_user.id, start_date, end_date))
    else:
        cur.execute("SELECT amount, reason, date FROM expenses WHERE user_id = %s ORDER BY date DESC", (current_user.id,))
    
    expenses = cur.fetchall()
    total_spent = sum(float(row[0]) for row in expenses)

    # Bar chart data: amount per day
    cur.execute("""
        SELECT date, SUM(amount) FROM expenses 
        WHERE user_id = %s
        """ + (" AND date BETWEEN %s AND %s" if start_date and end_date else "") +
        " GROUP BY date ORDER BY date",
        (current_user.id,) if not start_date else (current_user.id, start_date, end_date))
    chart_data = cur.fetchall()
    dates = [row[0].strftime('%Y-%m-%d') for row in chart_data]
    totals = [float(row[1]) for row in chart_data]

    # Pie chart data: sum by reason
    cur.execute("""
        SELECT reason, SUM(amount) FROM expenses 
        WHERE user_id = %s
        """ + (" AND date BETWEEN %s AND %s" if start_date and end_date else "") +
        " GROUP BY reason",
        (current_user.id,) if not start_date else (current_user.id, start_date, end_date))
    pie_data = cur.fetchall()
    pie_labels = [row[0] for row in pie_data]
    pie_totals = [float(row[1]) for row in pie_data]

    return render_template('dashboard.html',
                           expenses=expenses,
                           total_spent=total_spent,
                           dates=dates,
                           totals=totals,
                           pie_labels=pie_labels,
                           pie_totals=pie_totals,
                           start_date=start_date,
                           end_date=end_date)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
