import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd
app.config['API_KEY'] = 'pk_1099acae85d54db3bc52ceed83006303'


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    # Get user's current cash balance
    user_id = session["user_id"]
    cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
    cash = cursor.fetchone()[0]
    
    # Get user's stock holdings and current prices
    cursor.execute("SELECT stock_symbol, SUM(shares), purchase_price FROM purchases WHERE user_id = ? GROUP BY stock_symbol", (session["user_id"],))
    rows = cursor.fetchall()

    holdings = []
    total_value = 0
    
    for row in rows:
        symbol = row[0]
        shares = row[1]
        purchase_price = row[2]

        # Look up current price of stock
        stock = lookup(symbol)
        current_price = stock["price"]
        value = current_price * shares

        holdings.append({
            "symbol": symbol,
            "shares": shares,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "value": value
        })

        total_value += value

    grand_total = cash + total_value

    return render_template("index.html", holdings=holdings, cash=cash, total_value=total_value, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Retrieve stock data
        stock = lookup(symbol)
        if not stock:
            return apology("Invalid symbol")
        
        # Ensure shares is a positive integer
        try:
            shares = float(shares)
        except ValueError:
            return apology("Shares must be a positive integer")
        if shares < 0:
            return apology("Shares must be a positive integer")

        # Calculate total cost of purchase
        total_cost = shares * stock['price']

        # Retrieve user's cash balance
        cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
        row = cursor.fetchone()
        if not row:
            return apology("User not found")
        cash = row[0]

        # Check if user has sufficient funds to make purchase
        if cash < total_cost:
            return apology("Insufficient funds")

        # Update user's cash balance
        new_cash = cash - total_cost
        cursor.execute("UPDATE users SET cash = ? WHERE id = ?", (new_cash, session["user_id"]))
        conn.commit()
        
        # Log purchase in database
        cursor.execute("INSERT INTO purchases (user_id, stock_symbol, purchase_price, shares) VALUES (?, ?, ?, ?)", (session["user_id"], stock['symbol'], stock['price'], shares))
        conn.commit()

        conn.close()
        
        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        rows = cursor.fetchall()
        conn.commit()
        conn.close()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        quote_data = lookup(symbol)
        if quote_data:
            return render_template("quoted.html", quote=quote_data)
        else:
            return apology("Invalid symbol or lookup failed")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

    if request.method == "POST":
    # Get the username, password, and confirmation from the form
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

    # Check if any fields are empty
        if not username or not password or not confirmation:
            return apology("Please fill in all fields", 400)

    # Check if password and confirmation match
        if password != confirmation:
            return apology("Passwords do not match", 400)

    # Check if username is already taken
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        rows = cursor.fetchone()
        if rows is not None:
            return apology("Username already taken", 400)

        hashed_password = generate_password_hash(password)

    # Add code to create user account in database
        cursor.execute("INSERT INTO users (username, hash) VALUES(?,?)", (username, hashed_password))
        conn.commit()
        conn.close()

    # Redirect user to home page
        return redirect("/")
        
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")