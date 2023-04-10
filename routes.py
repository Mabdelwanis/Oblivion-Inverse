from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    get_flashed_messages,
    send_file,
    request,
    abort,
)
from werkzeug.security import check_password_hash
from flask_login import login_required, login_user, logout_user, current_user
from datetime import datetime as dt
import uuid
import pytz

from app import app, db
from models import TrackData, LinkHits, Users
import forms


@app.route("/", methods=["GET", "POST"])
@app.route("/index/", methods=["GET", "POST"])
@login_required
def index():
    """
    Returns Home page of the site. An authenticated user can generate new tracking links,
    Otherwise, user will be returned to /login page.
    """
    form = forms.GenerateTrackingLink()
    if form.validate_on_submit():
        utm_id = uuid.uuid4()
        generatedOn = str(dt.now().astimezone(pytz.timezone("Asia/Colombo")))
        # ----------------- change the timezone accordingly ^^
        trackingData = TrackData(
            utmId=str(utm_id),
            emailTitle=form.email_title.data,
            generatedDate=generatedOn,
        )
        db.session.add(trackingData)
        db.session.commit()
        flash("Tracking link successfully generated!")
        return redirect(url_for("tracking_data", utm_id=utm_id))
    return render_template("index.html", form=form)


@app.route("/tracklist")
@login_required
def tracklist():
    """
    Returns all the tracking links generated by an authenticated user - If there're no
    active records, redirects to /index. Otherwise, user will be returned to /login page.
    """
    trackingList = TrackData.query.all()
    if trackingList:
        return render_template("track_list.html", trackingList=trackingList)
    else:
        flash("Sorry, No tracking records found! - Let's generate a one!")
        return redirect(url_for("index"))


@app.route("/track")
def track():
    """
    Serve tracking pixel upon requested UTM ID.
     - Invalid UTM IDs >> Return [400] response
     - Authenticated user >> Return image without DB operations
     - Unauthenticated user >> Return image after DB operations
    """
    utm_id = request.args["utm_id"]
    filename = "static/OI-pixel.gif"

    if utm_id:

        trackEvent = TrackData.query.get(utm_id)

        if trackEvent:
            if current_user.is_authenticated:
                return send_file(filename, mimetype="image/gif", max_age=0)

            ip = request.headers.get("X-Forwarded-For")
            header = request.headers["User-Agent"]

            # ---- Use a geolocation API to get additional data ----
            #
            # url = f'https://ipwhois.app/json/{ip}'
            # response = requests.get(url)
            # ipData = json.loads(response.text)
            # country = ipData['country']
            #

            accessedOn = str(dt.now().astimezone(pytz.timezone("Asia/Colombo")))
            # ----------------- change the timezone accordingly ^^
            a = LinkHits(ipData=ip, browserData=header, timestamp=accessedOn)
            trackEvent.hits.append(a)
            db.session.add(a)
            db.session.commit()
        else:
            abort(400)
    else:
        abort(400)

    return send_file(filename, mimetype="image/gif", max_age=0)


@app.route("/tracking-data/<utm_id>")
@login_required
def tracking_data(utm_id):
    """Returns information related to a specific UTM ID."""
    data = TrackData.query.get(utm_id)
    if data:
        return render_template("tracking_data.html", data=data)
    else:
        flash("Sorry, Not a valid UTM id!")
        return redirect(url_for("tracklist"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        flash("You have already logged in!")
        return redirect(url_for("index"))
    form = forms.LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = Users.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=False)
                return redirect(url_for("index"))
            else:
                flash("Please check your login details and try again.")
                return redirect(url_for("login"))
        else:
            flash("Please check your login details and try again.")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash("Successfully Logged Out! - See you soon...")
    return redirect(url_for("login"))
