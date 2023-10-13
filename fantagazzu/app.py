import os
import sqlite3
import json
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from functools import wraps


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///fantasy.db")

user = 0
ctrl = ""


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/Login")
        return f(*args, **kwargs)

    return decorated_function


@app.route("/League", methods=["GET"])
@login_required
def league():
    global ctrl

    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()

    # Execute a query and fetch all the results
    cursor.execute("SELECT nome FROM quot")
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    user = session["user_id"]

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    participants = db.execute(
        "SELECT id, username, p, d, c, a, tokens FROM users ORDER BY id != ? DESC;",
        session["user_id"],
    )
    for participant in participants:
        participant["username"] = (participant["username"])[0:9]

    buyers = db.execute('SELECT DISTINCT Bought FROM quot WHERE Bought != "None"')
    buyers = [buyer["Bought"] for buyer in buyers]

    players = db.execute(
        "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought != 'None';"
    )

    return render_template(
        "league.html",
        players=players,
        nomi=nomi,
        user=user,
        faves=faves,
        participants=participants,
        buyers=buyers,
    )


@app.route("/Transactions")
@login_required
def history():
    trans = db.execute("SELECT * FROM trans ORDER BY tist DESC")
    for tran in trans:
        # Convert string to datetime object
        tist = datetime.strptime(tran["tist"], "%Y-%m-%d %H:%M:%S")

        # Add one hour to datetime object (italian time)
        tist += timedelta(hours=2)

        # Convert datetime object back to string
        tran["tist"] = tist.strftime("%Y-%m-%d %H:%M:%S")
    return render_template("transactions.html", trans=trans)


@app.route("/Login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("You must provide a username!")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("You must provide a password!")
            return render_template("login.html")
        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("Invalid username and / or password!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/League")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/League")


@app.route("/buy", methods=["POST"])
@login_required
def buy():
    tokens = db.execute("SELECT tokens FROM users WHERE id = ?", session["user_id"])
    tokens = tokens[0]["tokens"]
    id = request.form["buy"]
    page = request.form.get("page_id")
    name = db.execute("SELECT nome FROM quot WHERE id = ?;", id)
    return render_template("buy.html", name=name, id=id, tokens=tokens, page=page)


@app.route("/bought", methods=["post"])
@login_required
def bought():
    user = session["user_id"]
    price = request.form["price"]
    id = request.form["id"]
    name = db.execute("SELECT Nome FROM quot WHERE id = ?", id)
    name = name[0]["Nome"]

    # check if transaction has already been executed
    if "bought" not in session:
        session["bought"] = []

    if "sold" not in session:
        session["sold"] = []

    if id not in session["bought"]:
        # execute transaction and add to executed transactions in session
        db.execute(
            "UPDATE quot SET Bought = ?, Paid = ? WHERE Id = ?;", user, price, id
        )
        db.execute("UPDATE users SET tokens = tokens - ? WHERE id = ?", price, user)
        r = db.execute("SELECT r FROM quot WHERE Id = ?", id)[0]["R"]
        if r == "P":
            db.execute("UPDATE users SET p = p + 1 WHERE id = ?", user)
        elif r == "D":
            db.execute("UPDATE users SET d = d + 1 WHERE id = ?", user)
        elif r == "C":
            db.execute("UPDATE users SET c = c + 1 WHERE id = ?", user)
        elif r == "A":
            db.execute("UPDATE users SET a = a + 1 WHERE id = ?", user)

        username = (db.execute("SELECT username FROM users WHERE id = ?", user))[0][
            "username"
        ].upper()
        username = username[0:9]
        db.execute(
            "INSERT INTO trans (user,player,action,price) VALUES (?, ?, ?, ?)",
            username,
            name,
            "BOUGHT",
            price,
        )
        session["bought"].append(id)

        # flash success message
        if int(price) == 1:
            flash(
                "You have successfully added <br><strong><span style='color:black; font-size:17px;'>"
                + name
                + "</span></strong> to <a href='/MyTeam'>your team</a> for <strong><span style='color:black; font-size:17px;'>"
                + price
                + "</span></strong> token!"
            )
        else:
            flash(
                "You have successfully added <br><strong><span style='color:black; font-size:17px;'>"
                + name
                + "</span></strong> to <a href='/MyTeam'>your team</a> for <strong><span style='color:black; font-size:17px;'>"
                + price
                + "</span></strong> tokens!"
            )

    if id in session["sold"]:
        session["sold"].remove(id)

    if request.form.get("page_id") == "p":
        return redirect("/")
    else:
        return redirect("/Favourites")


@app.route("/sell", methods=["POST"])
@login_required
def sell():
    user = session["user_id"]
    sell = request.form["sell"]
    name = db.execute("SELECT Nome FROM quot WHERE id = ?", sell)
    name = name[0]["Nome"]
    price = db.execute("SELECT Paid FROM quot WHERE id = ?", sell)
    price = price[0]["Paid"]

    # check if transaction has already been executed
    if "bought" not in session:
        session["bought"] = []

    if "sold" not in session:
        session["sold"] = []

    if sell not in session["sold"]:
        # execute transaction and set flag variable in session
        db.execute("UPDATE users SET tokens = tokens + ? WHERE id = ?", price, user)
        db.execute(
            "UPDATE quot SET Bought = ?, Paid = ? WHERE Id = ?;", "None", "None", sell
        )

        r = db.execute("SELECT r FROM quot WHERE Id = ?", sell)[0]["R"]
        if r == "P":
            db.execute("UPDATE users SET p = p - 1 WHERE id = ?", user)
        elif r == "D":
            db.execute("UPDATE users SET d = d - 1 WHERE id = ?", user)
        elif r == "C":
            db.execute("UPDATE users SET c = c - 1 WHERE id = ?", user)
        elif r == "A":
            db.execute("UPDATE users SET a = a - 1 WHERE id = ?", user)

        username = (db.execute("SELECT username FROM users WHERE id = ?", user))[0][
            "username"
        ].upper()
        username = username[0:9]
        db.execute(
            "INSERT INTO trans (user,player,action,price) VALUES (?, ?, ?, ?)",
            username,
            name,
            "SOLD",
            price,
        )
        session["sold"].append(sell)

        # flash success message
        if price == 1:
            flash(
                "You have successfully removed <br><strong><span style='color:black; font-size:17px;'>"
                + name
                + "</strong> from <a href='/MyTeam'>your team</a> for <strong><span style='color:black; font-size:17px;'>"
                + str(price)
                + "</span></strong> token!"
            )
        else:
            flash(
                "You have successfully removed <br><strong><span style='color:black; font-size:17px;'>"
                + name
                + "</strong> from <a href='/MyTeam'>your team</a> for <strong><span style='color:black; font-size:17px;'>"
                + str(price)
                + "</span></strong> tokens!"
            )

    if sell in session["bought"]:
        session["bought"].remove(sell)

    if request.form.get("page_id") == "p":
        return redirect("/")
    elif request.form.get("page_id") == "t":
        return redirect("/MyTeam")
    elif request.form.get("page_id") == "l":
        return redirect("/League")
    else:
        return redirect("/Favourites")


@app.route("/star", methods=["POST"])
@login_required
def star():
    star = request.form["star"]

    if "star" not in session:
        session["star"] = []

    if "unstar" not in session:
        session["unstar"] = []

    if star not in session["star"]:
        player = star
        db.execute(
            "INSERT INTO faves (user,player) VALUES (?, ?)", session["user_id"], player
        )
        name = db.execute("SELECT nome FROM quot WHERE id = ?;", player)
        name = name[0]["Nome"]
        session["star"].append(star)

        flash(
            "You have successfully added <br><strong><span style='color:black; font-size:17px;'>"
            + name
            + "</span></strong> to your <a href='/Favourites'>favourites</a>!"
        )

    if star in session["unstar"]:
        session["unstar"].remove(star)

    if request.form.get("page_id") == "p":
        return redirect("/")
    elif request.form.get("page_id") == "l":
        return redirect("/League")
    else:
        return redirect("/MyTeam")


@app.route("/unstar", methods=["POST"])
@login_required
def unstar():
    unstar = request.form["unstar"]

    if "star" not in session:
        session["star"] = []

    if "unstar" not in session:
        session["unstar"] = []

    if unstar not in session["unstar"]:
        player = unstar
        db.execute(
            "DELETE FROM faves WHERE user = ? AND player = ?",
            session["user_id"],
            player,
        )
        name = db.execute("SELECT nome FROM quot WHERE id = ?;", player)
        name = name[0]["Nome"]
        flash(
            "You have successfully removed <br><strong><span style='color:black; font-size:17px;'>"
            + name
            + "</span></strong> from your <a href='/Favourites'>favourites</a>!"
        )
        session["unstar"].append(unstar)

    if unstar in session["star"]:
        session["star"].remove(unstar)

    if request.form.get("page_id") == "p":
        return redirect("/")
    elif request.form.get("page_id") == "t":
        return redirect("/MyTeam")
    elif request.form.get("page_id") == "l":
        return redirect("/League")
    else:
        return redirect("/Favourites")


@app.route("/search", methods=["POST"])
@login_required
def search():
    user = session["user_id"]
    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    name = request.form.get("search")
    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()
    # Execute a query and fetch all the results
    cursor.execute("SELECT nome FROM quot")
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    players = db.execute(
        "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Nome LIKE ?;",
        f"%{name}%",
    )
    return render_template(
        "players.html", players=players, nomi=nomi, user=user, faves=faves
    )


@app.route("/", methods=["GET", "POST"])
@login_required
def players():
    global ctrl

    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()

    # Execute a query and fetch all the results
    cursor.execute("SELECT nome FROM quot")
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    user = session["user_id"]

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if request.form["button"] == "r":
            if ctrl == "r":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.R DESC, quot.Ia DESC;"
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.R ASC, quot.Ia DESC;"
                )
                ctrl = "r"

        elif request.form["button"] == "squadra":
            if ctrl == "s":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.squadra DESC, quot.R DESC, quot.Ia DESC;"
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.squadra ASC, quot.R DESC, quot.Ia DESC;"
                )
                ctrl = "s"

        elif request.form["button"] == "nome":
            if ctrl == "n":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.nome DESC;"
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.nome ASC;"
                )
                ctrl = "n"

        elif request.form["button"] == "qta":
            if ctrl == "q":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.qt_a DESC, quot.Ia DESC;"
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.qt_a ASC, quot.Ia DESC;"
                )
                ctrl = "q"

        elif request.form["button"] == "ia":
            if ctrl == "i":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.ia DESC;"
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id ORDER BY quot.ia ASC;"
                )
                ctrl = "i"

        return render_template(
            "players.html", players=players, nomi=nomi, user=user, faves=faves
        )

    else:
        players = db.execute(
            "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id;"
        )

        return render_template(
            "players.html", players=players, nomi=nomi, user=user, faves=faves
        )


@app.route("/FaveSearch", methods=["POST"])
@login_required
def fsearch():
    user = session["user_id"]
    tuser = (user,)  # Convert to tuple

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    name = request.form.get("fsearch")
    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()
    # Execute a query and fetch all the results
    cursor.execute(
        "SELECT nome FROM quot JOIN faves ON quot.Id = faves.player WHERE faves.user = ?;",
        tuser,
    )
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    players = db.execute(
        "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? AND quot.Nome LIKE ?;",
        user,
        f"%{name}%",
    )
    return render_template(
        "favourites.html", players=players, nomi=nomi, user=user, faves=faves
    )


@app.route("/Favourites", methods=["GET", "POST"])
@login_required
def favourites():
    global ctrl

    user = session["user_id"]
    tuser = (user,)  # Convert to tuple
    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()

    # Execute a query and fetch all the results
    cursor.execute(
        "SELECT nome FROM quot JOIN faves ON quot.Id = faves.player WHERE faves.user = ?;",
        tuser,
    )
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if request.form["button"] == "r":
            if ctrl == "r":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.R ASC, quot.Ia DESC;",
                    user,
                )
                ctrl = "r"

        elif request.form["button"] == "squadra":
            if ctrl == "s":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.squadra DESC, quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.squadra ASC, quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = "s"

        elif request.form["button"] == "nome":
            if ctrl == "n":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.nome DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.nome ASC;",
                    user,
                )
                ctrl = "n"

        elif request.form["button"] == "qta":
            if ctrl == "q":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.qt_a DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.qt_a ASC, quot.Ia DESC;",
                    user,
                )
                ctrl = "q"

        elif request.form["button"] == "ia":
            if ctrl == "i":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ? ORDER BY quot.ia ASC;",
                    user,
                )
                ctrl = "i"
        return render_template(
            "favourites.html", players=players, nomi=nomi, user=user, faves=faves
        )

    else:
        players = db.execute(
            "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id JOIN faves ON quot.Id = faves.player WHERE faves.user = ?;",
            user,
        )

        return render_template(
            "favourites.html", players=players, nomi=nomi, user=user, faves=faves
        )


@app.route("/TeamSearch", methods=["POST"])
@login_required
def teamsearch():
    user = session["user_id"]
    tuser = (user,)  # Convert to tuple

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    roles = db.execute("SELECT p,d,c,a,tokens FROM users WHERE id = ?", user)

    name = request.form.get("teamsearch")
    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()
    # Execute a query and fetch all the results
    cursor.execute("SELECT nome FROM quot WHERE Bought = ?;", tuser)
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    players = db.execute(
        "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? AND quot.Nome LIKE ?;",
        user,
        f"%{name}%",
    )
    return render_template(
        "myteam.html", players=players, nomi=nomi, user=user, faves=faves, roles=roles
    )


@app.route("/MyTeam", methods=["GET", "POST"])
@login_required
def myteam():
    global ctrl

    user = session["user_id"]
    tuser = (user,)  # Convert to tuple
    conn = sqlite3.connect("fantasy.db")
    cursor = conn.cursor()

    # Execute a query and fetch all the results
    cursor.execute("SELECT nome FROM quot WHERE Bought = ?;", tuser)
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Convert the list of tuples to a list of values
    nomi = [row[0] for row in rows]

    faves = []
    favourites = db.execute("SELECT * FROM faves WHERE user = ?", user)
    for fave in favourites:
        faves.append(fave["player"])

    roles = db.execute("SELECT p,d,c,a,tokens FROM users WHERE id = ?", user)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if request.form["button"] == "r":
            if ctrl == "r":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.R ASC, quot.Ia DESC;",
                    user,
                )
                ctrl = "r"

        elif request.form["button"] == "squadra":
            if ctrl == "s":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.squadra DESC, quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.squadra ASC, quot.R DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = "s"

        elif request.form["button"] == "nome":
            if ctrl == "n":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.nome DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.nome ASC;",
                    user,
                )
                ctrl = "n"

        elif request.form["button"] == "paid":
            if ctrl == "q":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.Paid DESC, quot.Ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.Paid ASC, quot.Ia DESC;",
                    user,
                )
                ctrl = "q"

        elif request.form["button"] == "ia":
            if ctrl == "i":
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.ia DESC;",
                    user,
                )
                ctrl = ""
            else:
                players = db.execute(
                    "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ? ORDER BY quot.ia ASC;",
                    user,
                )
                ctrl = "i"
        return render_template(
            "myteam.html",
            players=players,
            nomi=nomi,
            user=user,
            faves=faves,
            roles=roles,
        )

    else:
        players = db.execute(
            "SELECT quot.*, stat.Pv, stat.Mv, stat.Mf, stat.Gf, stat.Gs, stat.Rp, stat.Rc, stat.Rpiu, stat.Rmeno, stat.Ass, stat.Amm, stat.Esp, stat.Au FROM quot LEFT JOIN stat ON quot.Id = stat.Id WHERE quot.Bought = ?;",
            user,
        )
        return render_template(
            "myteam.html",
            players=players,
            nomi=nomi,
            user=user,
            faves=faves,
            roles=roles,
        )


@app.route("/Register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure league name was submitted
        if not request.form.get("league"):
            flash("You must provide league code!")
            return render_template("register.html")

        # Ensure username was submitted
        elif not request.form.get("username"):
            flash("You must provide a username!")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("You must provide a password!")
            return render_template("register.html")

        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            flash("You must confirm your password!")
            return render_template("register.html")

        elif request.form.get("league") != "legadelpollo":
            flash("League code doesn't exist!")
            return render_template("register.html")

        # Ensure passwords match
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        if password != confirm:
            flash("Passwords don't match!")
            return render_template("register.html")

        # Ensure username is available
        username = request.form.get("username")
        if len(db.execute("SELECT * FROM users WHERE username = ?", username)) != 0:
            flash("Username already exists!")
            return render_template("register.html")

        # Save user's details in database
        else:
            user = db.execute(
                "INSERT INTO users (username,hash) VALUES(?,?)",
                username,
                generate_password_hash(password, method="pbkdf2:sha256", salt_length=8),
            )
            logged_in = db.execute(
                "SELECT username FROM users ORDER BY id DESC LIMIT 1;"
            )
            session["user_id"] = user
            flash(
                'You have succesfully registered and are now logged in as "'
                + logged_in[0]["username"].upper()
                + '"'
            )
            return redirect("/League")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/CMG", methods=["GET", "POST"])
def cmg():
    return render_template("cmg.html")
