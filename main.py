from flask import Flask, render_template, request, flash, session, redirect, jsonify, url_for
import os
from flask_pymongo import PyMongo
import bcrypt
import matplotlib.pyplot as plt
import io
import base64
import json

wallet = Flask(__name__)
wallet.secret_key = 'your_secret_key_here'  # Required for session management

wallet.config["MONGO_DBNAME"] = 'test_db'  # Name of the database
wallet.config["MONGO_URI"] = "mongodb://localhost:27017/test_db"  # Fixed tuple issue

mongo = PyMongo(wallet)
mongo = PyMongo(wallet)

# ✅ Debugging check
with wallet.app_context():  # Ensure we are in an application context
    if mongo.db is None:
        print("MongoDB connection failed! Check your MONGO_URI.")
    else:
        print("MongoDB connected successfully!")

    # ✅ Now safely access collections inside the app context
    user = mongo.db.users  # Ensure 'users' is the correct collection name
    expenses = mongo.db.expenses  # Collection for storing expenses
@wallet.route('/') 
def home():
    if 'username' in session:
        return render_template('dashboard.html', username=session["username"])
    return render_template('index.html')


@wallet.route('/enter', methods=['POST'])
def enter():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash("Please enter both username and password.")
        return redirect(url_for('home'))  

    pre_existing = user.find_one({'name': username})

    if pre_existing:
        # Check if password is correct
        if bcrypt.checkpw(password.encode('utf-8'), pre_existing['password']):  # Correct check
            session['username'] = username
            flash("Welcome back, " + username)
            return redirect(url_for('home'))
        else:
            flash("Invalid password. Try again.")
            return render_template('login.html')
    
    flash("New user detected! Please register.")
    return render_template('register.html', name=username)

@wallet.route('/register', methods=['POST'])
def register():
    name = request.form.get('username')
    password = request.form.get('password')
    contactnumber = request.form.get('contactnumber')
    confirmpassword = request.form.get('confirmpassword')

    if not (name and password and contactnumber and confirmpassword):
        flash("All fields are required.", "error")
        return redirect(url_for('home'))  # Redirect to home if fields are missing
    
    if confirmpassword != password:
        flash('The passwords did not match. Please try again.', "error")
        return redirect(url_for('home'))

    # Hash the password
    hashpass = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())  

    # Check if user already exists
    existing_user = user.find_one({'name': name})
    if existing_user:
        flash("Username already exists. Please log in.", "error")
        return redirect(url_for('login'))

    # Insert user into the database
    user.insert_one({'name': name, 'password': hashpass, 'contact': contactnumber})  
    session['username'] = name  

    flash("Registration successful! Please log in.", "success")
    return redirect(url_for('login'))  # Redirect to login page


@wallet.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        pre_existing = user.find_one({'name': username})
        
        if pre_existing and bcrypt.checkpw(password.encode('utf-8'), pre_existing['password']):
            session['username'] = username
            return redirect('/')
        else:
            flash("Invalid credentials. Try again.")
            return render_template('login.html')
    
    return render_template('login.html')

@wallet.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect('/')

@wallet.route('/expenses')
def expenses_chart():
    if 'username' not in session:
        flash("Please log in to view expenses.")
        return redirect('/login')
    
    user_expenses = expenses.find({'username': session['username']})
    categorized_expenses = {}
    
    for expense in user_expenses:
        category = expense['category']
        amount = expense['amount']
        categorized_expenses[category] = categorized_expenses.get(category, 0) + amount
    
    categories = list(categorized_expenses.keys())
    amounts = list(categorized_expenses.values())
    
    plt.figure(figsize=(10, 5))
    plt.bar(categories, amounts, color=['blue', 'green', 'red', 'purple', 'orange'])
    plt.xlabel('Expense Category')
    plt.ylabel('Total Amount Spent')
    plt.title('Categorized Monthly Expenses')
    plt.xticks(rotation=45)
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return render_template('expenses.html', plot_url=plot_url)

@wallet.route('/add_expense', methods=['POST'])
def add_expense():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    category = data.get('category')
    amount = data.get('amount')
    
    if not category or not amount:
        return jsonify({"error": "Missing data"}), 400
    
    expenses.insert_one({
        'username': session['username'],
        'category': category,
        'amount': amount
    })
    
    return jsonify({"message": "Expense added successfully"})

if __name__ == '__main__':
    wallet.run(debug=True)
