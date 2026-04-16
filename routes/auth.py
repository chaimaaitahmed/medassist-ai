from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
# On importera mysql depuis app.py plus tard

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        from app import mysql
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        specialty = request.form['specialty']
        doc_id = request.form['doctor_id']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, password, specialty, doctor_id) VALUES(%s, %s, %s, %s, %s)", 
                    (name, email, password, specialty, doc_id))
        mysql.connection.commit()
        flash("Compte créé avec succès !")
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        from app import mysql
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        
        if user_data and check_password_hash(user_data[3], password):
            # Logique de session Flask-Login
            return redirect(url_for('main.dashboard'))
    return render_template('login.html')