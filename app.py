import os
import time

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

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


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""

    user = session["user_id"]
    print(user)
    # look up cash balance
    cash2 = db.execute("SELECT cash FROM users WHERE id IS (?)", user)
    cash_balance = int(cash2[0]['cash'])

    stocks = db.execute("SELECT stock_owned, quantity FROM portfolio WHERE user_id IS (?)", user)

    # make a list
    stocks1 = [{}]

    total_value = 0

    for i in range(len(stocks)):
        for key in stocks[i]:
            if key == 'stock_owned':
                q = int(stocks[i]['quantity'])
                lu_price = (lookup(stocks[i][key]))
                val = (lu_price['price']) * q
                x = {'symbol': (stocks[i]['stock_owned']), 'quantity': stocks[i]['quantity'], 'price': usd(lu_price['price']), 'value': usd(val)}
                stocks1.append(x)
                total_value = total_value + val

    cash_stocks_value = total_value + cash_balance
    total_value_stocks = usd(total_value)
    cash_stocks = usd(cash_stocks_value)
    cash_usd = usd(cash_balance)

    return render_template("index.html", cash_usd=cash_usd, stocks1=stocks1, total_value_stocks=total_value_stocks, cash_stocks=cash_stocks)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Stock symbol cannot be left blank")

        elif lookup(request.form.get("symbol")) == None:
            return apology("Stock does not exist")

        elif not (request.form.get("shares")).isnumeric():
            return apology("please enter a positive number")

        elif (float(request.form.get("shares")) % 1) != 0:
            return apology("please enter a positive number")

        elif int(request.form.get("shares")) < int(1):
            return apology("please enter a positive number")

        symbol = lookup(request.form.get("symbol"))
        user = session["user_id"]
        cash1 = db.execute("SELECT cash FROM users WHERE id IS (?)", user)
        price = int(symbol['price'])
        quantity = int(request.form.get("shares"))
        expend = price * quantity

        if expend > int(cash1[0]['cash']):
            return apology("You need more money, seriously... get more money")
        else:
            time_stamp = time.time()
            balance = int(cash1[0]['cash']) - expend
            time_stamp = time.time()

            # Create entry for record of transactions
            db.execute("INSERT INTO transaction_list (user_id, transaction_type, stock_symbol, price, quantity, time) VALUES (?, ?, ?, ?, ?, ?)",
                       user, "buy", (symbol['symbol']), price, quantity, time_stamp)

            # Update accounts cash balance
            db.execute(
                "UPDATE users SET cash = (?) WHERE id IS (?)", balance, user)

            # Update portfolio (must first check to see if customer owns any stock)
            stock_exists = db.execute("SELECT COUNT(*) FROM portfolio WHERE user_id IS (?) AND stock_owned IS (?)", user, (symbol['symbol']))


            if int(stock_exists[0]['COUNT(*)']) == 0:
                db.execute("INSERT INTO portfolio (user_id, stock_owned, quantity) VALUES (?, ?, ?)",
                           user, (symbol['symbol']), quantity)
            else:
                stock_owned0 = (db.execute("SELECT quantity FROM portfolio WHERE user_id IS (?) AND stock_owned IS (?)", user, (symbol['symbol'])))
                stock_owned1 = int(stock_owned0[0]['quantity']) + quantity
                db.execute("UPDATE portfolio SET quantity = (?) WHERE user_id IS (?) AND stock_owned IS (?)",
                           stock_owned1, user, (symbol['symbol']))

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    transactions_ls = []
    user = session["user_id"]
    transactions = db.execute("SELECT * FROM transaction_list WHERE user_id IS (?)", user)
    print(transactions)
    for i in range(len(transactions)):
        date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(transactions[i]['time']))
        x = {'stock_symbol': transactions[i]['stock_symbol'], 'transaction_type': transactions[i]['transaction_type'], 'price': transactions[i]['price'], 'quantity': transactions[i]['quantity'], 'time' : date}
        transactions_ls.append(x)

    return render_template("history.html", transactions_ls=transactions_ls)



# For each row, make clear whether a stock was bought or sold and include the stock’s symbol, the (purchase or sale) price, the number of shares bought or sold, and the date and time at which the transaction occurred.
# You might need to alter the table you created for buy or supplement it with an additional table. Try to minimize redundancies.


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol")

        elif not lookup(request.form.get("symbol")):
            return apology("Invalid stock")

        else:

            quoted = lookup(request.form.get("symbol"))
            #quoted[0]['name']
            x = quoted['price']
            quoted['price'] = usd(x)
            #quoted[0]['symbol']

            return render_template("quoted.html", quoted=quoted)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Require that a user input a username (text, name should be username?)  apology if the user’s input is blank or the username already exists.
        if not request.form.get("username"):
            return apology("must enter username", 400)

        # Require that a user input a password, text field whose name is password?, and then that same password again, confirmation. apology if either input is blank or the passwords do not match.
        elif not request.form.get("password"):
            return apology("must enter password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("unlike socks passwords must match", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))
        if len(rows) > 0:
            return apology("username already taken", 400)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))

        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/change_pass", methods=["GET", "POST"])
def change_pass():
    """Change password"""
    if request.method == "POST":

        # Require that a user input a username (text, name should be username?)  apology if the user’s input is blank or the username already exists.
        if not request.form.get("username"):
            return apology("must enter username", 403)

        # Require that a user input a password, text field whose name is password?, and then that same password again, confirmation. apology if either input is blank or the passwords do not match.
        elif not request.form.get("password"):
            return apology("must enter password", 403)

        elif request.form.get("new_pass") != request.form.get("conf_new_pass"):
            return apology("unlike socks passwords must match", 403)

        else:
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                return apology("invalid username and/or password", 403)
            print((request.form.get("new_pass")))
            print(generate_password_hash(request.form.get("new_pass")))
            print(request.form.get("username"))
            db.execute("UPDATE users  SET hash = (?) WHERE username IS (?)", generate_password_hash(request.form.get("new_pass")), request.form.get("username"))

        return redirect("/login")

    else:
        return render_template("change_pass.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    user = session["user_id"]
    stock_ls = db.execute("SELECT stock_owned FROM portfolio WHERE user_id IS (?)", user)
    stock_ls0 = []

    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        user = session["user_id"]
        cash1 = db.execute("SELECT cash FROM users WHERE id IS (?)", user)

        price = int(symbol['price'])
        quantity = int(request.form.get("shares"))
        sale_proceeds = price * quantity
        new_balance = int(cash1[0]['cash']) + sale_proceeds
        time_stamp = time.time()
        owned = db.execute("SELECT COUNT(*) FROM portfolio WHERE stock_owned IS (?) AND user_id IS (?)", (symbol['symbol']), user)
        q_owned = db.execute("SELECT quantity FROM portfolio WHERE stock_owned IS (?) AND user_id IS (?)", (symbol['symbol']), user)


        # check for issues

        if not request.form.get("symbol"):
            return apology("Stock symbol cannot be left blank")

        elif lookup(request.form.get("symbol")) == None:
            return apology("Stock does not exist")

        elif int(request.form.get("shares")) < int(1):
            return apology("please enter a positive number")

        elif int(owned[0]['COUNT(*)']) == 0:
            return apology("You do not own that stock")

        elif quantity > int(q_owned[0]['quantity']):
            return apology("You do not have enough shares to sell, please enter a lower number")

        else:

        # create new transaction symbol an issue?  check out later
            db.execute("INSERT INTO transaction_list (user_id, transaction_type, stock_symbol, price, quantity, time) VALUES (?, ?, ?, ?, ?, ?)",
                       user, "sell", (symbol['symbol']), price, quantity, time_stamp)
        # amend account cash balance
            db.execute(
                "UPDATE users SET cash = (?) WHERE id IS (?)", new_balance, user)
        # amend portfolio
            stock_owned0 = (db.execute("SELECT quantity FROM portfolio WHERE user_id IS (?) AND stock_owned IS (?)", user, (symbol['symbol'])))
            stock_owned1 = int(stock_owned0[0]['quantity']) - quantity
            db.execute("UPDATE portfolio SET quantity = (?) WHERE user_id IS (?) AND stock_owned IS (?)", stock_owned1, user, (symbol['symbol']))

        return redirect("/")

    else:

        stock_ls = db.execute("SELECT stock_owned FROM portfolio WHERE user_id IS (?)", user)
        stock_ls0 = []

        for i in range (len(stock_ls)):
            x = stock_ls[i]['stock_owned']
            stock_ls0.append(x)
            print(x)

        print(stock_ls0)

        return render_template("sell.html", stock_ls0=stock_ls0)
