from flask import Flask, redirect, url_for, render_template, flash, session, g, request, make_response, render_template_string
import requests
from bs4 import BeautifulSoup, Comment
from datetime import timedelta, datetime
import re
import pandas as pd
from flask_caching import Cache
import psycopg2
import os


# # # # # # # # # # # # # # # # # # 
#
# Flask Setup
#
# # # # # # # # # # # # # # # # # # 

app = Flask(__name__)
app.secret_key = os.environ['MOBILE_LOTW_SECRET_KEY']
app.permanent_session_lifetime = timedelta(days=365)

# Cache configuration
app.config['CACHE_TYPE'] = 'simple'  # Use in-memory cache for simplicity. For production, consider 'redis' or 'memcached'.
# Defining the cache timout below now
app.config['CACHE_DEFAULT_TIMEOUT'] = 600  # Set cache timeout to 10 minutes (600 seconds)
cache = Cache(app)


# # # # # # # # # # # # # # # # # # 
#
# URLs 
#
# # # # # # # # # # # # # # # # # # 

login_url = 'https://lotw.arrl.org/lotwuser/default'
was_page_url = 'https://lotw.arrl.org/lotwuser/awardaccount?awardaccountcmd=status&awg_id=WAS&ac_acct=1'
waz_page_url = 'https://lotw.arrl.org/lotwuser/awardaccount?awardaccountcmd=status&awg_id=WAZ&ac_acct=1'
dxcc_page_url = 'https://lotw.arrl.org/lotwuser/awardaccount?awardaccountcmd=status&awg_id=DXCC&ac_acct=1'
vucc_page_url = 'https://lotw.arrl.org/lotwuser/awardaccount?awardaccountcmd=status&awg_id=VUCC&ac_acct=1'
wpx_page_url = 'https://lotw.arrl.org/lotwuser/awardaccount?awardaccountcmd=status&awg_id=WPX&ac_acct=1'
triple_page_url = 'https://lotw.arrl.org/lotwuser/accountcredits?awg_id=WAS&ac_acct=1&aw_id=WAS-TRIPLE'
qsls_page_url = "https://lotw.arrl.org/lotwuser/qsos?qso_query=1&awg_id=DXCC&ac_acct=1&qso_callsign=&qso_owncall=&qso_startdate=&qso_starttime=&qso_enddate=&qso_endtime=&qso_mode=&qso_band=&qso_qsl=yes&qso_dxcc=&qso_sort=QSL+Date&qso_descend=yes&acct_sel=DXCC%3B1"
details_page_url = "https://lotw.arrl.org/lotwuser/qsodetail?qso="
find_page_url = 'https://lotw.arrl.org/lotwuser/act'
callsign = ""


# # # # # # # # # # # # # # # # # # 
#
# Setup the LOTW session so we can pass it around between routes
#
# # # # # # # # # # # # # # # # # # 

@app.before_request
def before_request():
    if 'web_session_cookies' in session:
        g.web_session = requests.Session()
        g.web_session.cookies = requests.utils.cookiejar_from_dict(session['web_session_cookies'])
    else:
        g.web_session = None
    get_db()


@app.teardown_request
def teardown_request(exception=None):
    db = g.pop('db', None)
    if exception is None:
        if db is not None:
            db.commit()
    if db is not None:
        db.close()


# This gives a different cache key when users are logged in then when they're not
# That way people don't get got in the cached page login loop
def custom_cache_key():
    if callsign != "":
        return callsign
    else:
        return "anon"

# For debugging - lotw-login is the value in our session
@app.route('/show_session_info')
def show_session():
    items = ["<li>{}: {}</li>".format(k, v) for k, v in session.items()]
    return render_template_string("<ul>{}</ul>".format("".join(items)))


# # # # # # # # # # # # # # # # # # 
#
# Home and About and Privacy pages
#
# # # # # # # # # # # # # # # # # # 

@app.route("/")
def home():
#    if g.web_session:
#        return redirect(url_for("qsls"))
#    else:
    return render_template("home.html")


@app.route("/about")
@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/privacy")
@app.route("/privacy/")
def privacy():
    return render_template("privacy.html")



# # # # # # # # # # # # # # # # # # 
#
# Login
#
# # # # # # # # # # # # # # # # # # 

@app.route("/login", defaults={'next_page': 'qsls'}, methods=["POST", "GET"])
@app.route("/login/<next_page>", methods=["POST", "GET"])
def login(next_page):

    if request.method == "POST":
        payload = {
            'login': request.form["login"],
            'password': request.form["password"],
            'acct_sel' : '',
            'thisForm' : 'login'
        }

        s = requests.Session()
        r = s.post(login_url, data=payload)

        if 'postcard' in r.text:
            flash("LOTW login unsuccessful! Please try again.", "error")
            if next_page:
                return redirect(url_for("login", next_page = next_page))
            else:
                return redirect(url_for("login"))

        else:  
            callsign = request.form["login"]
            session['web_session_cookies'] = requests.utils.dict_from_cookiejar(s.cookies)
            session['logged_in'] = True # for use in index.html template for nav
            expiration_date = datetime.now() + timedelta(days=365)           
            response = redirect(url_for(next_page))
            response.set_cookie('op', request.form["login"].lower(), expires=expiration_date)
            return response

    else:
        if g.web_session:
            return redirect(url_for("qsls"))

        else:
            login_form = '<br /><form action="#"'
            login_form = login_form + ''' method = "post">
            <p><input type="text" name="login" placeholder="Your callsign" class = "form-control-lg" /></p>
            <p><input type="password" name="password" placeholder="Your LotW password" class="form-control-lg" / ></p>
            <p><input type="submit" value="Login" /></p>
            </form></center>
            '''
            response = make_response(render_template("index.html", content=login_form, title="Login to Mobile LotW"))
            # Set headers to prevent caching of the login page
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
#            return render_template("index.html", content=login_form, title="Login to Mobile LotW")



# # # # # # # # # # # # # # # # # # # # #
# 
# QSLs
#
# # # # # # # # # # # # # # # # # # # # #


@app.route("/qsls")
@cache.memoize(timeout=600, make_name=custom_cache_key())
def qsls():
    if g.web_session:
        response = g.web_session.get(qsls_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find('form')
        table = form.find('table')

        # Parse the table to get rows
        rows = table.find_all('tr')
        rows[28].decompose()
        rows[0].decompose()
        rows[1].decompose()
        rows[2].decompose()

        current_qsls = []
        rows = table.find_all('tr')
        for row in rows:  # Skip the header row
            columns = row.find_all('td')
            current_row = {
                'op': op,
                'worked': columns[2].text,
                'band': columns[4].text,
                'mode': columns[5].text,
                'details': str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '')
            }
            current_qsls.append(current_row)

        db = get_db()
        cursor = db.cursor()
        query = "SELECT worked, band, mode, details FROM qsls WHERE op=%s"
        cursor.execute(query, (op,))
        previous_qsls = cursor.fetchall()

        cursor.execute('DELETE FROM qsls WHERE op = %s', (op,))
        cursor.executemany('INSERT INTO qsls (op, worked, band, mode, details) VALUES (%s, %s, %s, %s, %s)', [tuple(row.values()) for row in current_qsls])
        cursor.execute(query, (op,))
        current_qsls = cursor.fetchall()
        db.commit()

        new_qsls = [contact for contact in current_qsls if contact not in previous_qsls]

        return render_template("qsl.html", new_qsls = new_qsls, previous_qsls = previous_qsls, qsls_page_url = qsls_page_url, title="25 Most Recent QSLs")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "qsls"))




# # # # # # # # # # # # # # # # # # # # #
#
# DXCC 
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/dxcc")
@cache.memoize(timeout=600, make_name=custom_cache_key())
def dxcc():
    if g.web_session:
        response = g.web_session.get(dxcc_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'accountStatusTable'})

        # Parse the table to get rows
        dxcc = []

        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')

                # Remove the link to Challenge, since it's just too big to display nicely on mobile
                award_value = str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[0].find('a') else columns[0].text
                if 'Challenge' in award_value:
                    award_value = 'Challenge'

                # Change --- into "" so they'll fit into the integer 
#                if columns[1].text == "---":
#                    columns[1].text = NULL
#                if columns[2].text == "---":
#                    columns[2].text = NULL
#                if columns[3].text == "---":
#                    columns[3].text = NULL
#                if columns[5].text == "---":
#                    columns[5].text = NULL

                current_row = {
                    'op': op,
                    'award': award_value,
                    'new': columns[1].text,
                    'in_process': columns[2].text,
                    'awarded': columns[3].text,
                    'total': columns[5].text,
                }
                dxcc.append(current_row)

#        db = get_db()
#        cursor = db.cursor()
#        cursor.execute('DELETE FROM dxcc WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO dxcc (op, award, new, in_process, awarded, total) VALUES (%s, %s, %s, %s, %s, %s)', [tuple(row.values()) for row in dxcc])
        
        return render_template("award.html", award=dxcc, page_url=dxcc_page_url, award_name="DXCC", title="DXCC Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "dxcc"))




# # # # # # # # # # # # # # # # # # # # #
# 
# WAS
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/was")
@cache.memoize(timeout=600, make_name=custom_cache_key())

def was():
    if g.web_session:
        response = g.web_session.get(was_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'accountStatusTable'})

        # Parse the table to get rows
        rows = table.find_all('tr')
        was = []

        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')
                # Remove the link to Challenge, since it's just too big to display nicely on mobile
                award_value = str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[0].find('a') else columns[0].text
                if 'Triple' in award_value:
                    award_value = '<a href="https://mobilelotw.org/triple">Triple Play</a>'
                if '5-Band' in award_value:
                    award_value = '5-Band'

                current_row = {
                    'op': op,
                    'award': award_value,
                    'new': columns[1].text,
                    'in_process': columns[2].text,
                    'awarded': columns[3].text,
                    'total': columns[4].text,
                }
                was.append(current_row)

#        db = get_db()
#        cursor = db.cursor()
#        cursor.execute('DELETE FROM was WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO was (op, award, new, in_process, awarded, total) VALUES (%s, %s, %s, %s, %s, %s)', [tuple(row.values()) for row in was])
        
        return render_template("award.html", award=was, page_url=was_page_url, award_name="WAS", title="WAS Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "was"))




# # # # # # # # # # # # # # # # # # # # #
# 
# Triple Play Award
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/triple")
@cache.memoize(timeout=600, make_name=custom_cache_key())
def triple():
    if g.web_session:
        response = g.web_session.get(triple_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'creditsTable'})

        # Parse the table to get rows
        rows = table.find_all('tr')
        triple = []

        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')
                current_row = {
                    'op': op,
                    'state': re.sub(r'(?s).+ \((\w+)\)', r'\1', columns[0].text), # reduce states to abbreviations
                    'cw': str(columns[1].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[1].find('a') else '-',
                    'phone': str(columns[2].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[2].find('a') else '-',
                    'digital': str(columns[3].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[3].find('a') else '-'
                }
                triple.append(current_row)

#        db = get_db()
#        cursor = db.cursor()

#        cursor.execute('DELETE FROM triple WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO triple (op, state, cw, phone, digital) VALUES (%s, %s, %s, %s, %s)', [tuple(row.values()) for row in triple])
        
        return render_template("triple.html", triple=triple, triple_page_url = triple_page_url, title="Triple Play Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "triple"))



# # # # # # # # # # # # # # # # # # # # #
# 
# WAZ
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/waz")
@cache.memoize(timeout=600, make_name=custom_cache_key())
def waz():
    if g.web_session:
        response = g.web_session.get(waz_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'accountStatusTable'})

        # Parse the table to get rows
        rows = table.find_all('tr')
        waz = []

        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')
                award_value = str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[0].find('a') else columns[0].text
                if '5-Band' in award_value:
                    award_value = '5-Band'

                current_row = {
                    'op': op,
                    'award': award_value,
                    'new': columns[1].text,
                    'in_process': columns[2].text,
                    'awarded': columns[3].text,
                    'total': columns[4].text,
                }
                waz.append(current_row)

#        db = get_db()
#        cursor = db.cursor()
#        cursor.execute('DELETE FROM waz WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO waz (op, award, new, in_process, awarded, total) VALUES (%s, %s, %s, %s, %s, %s)', [tuple(row.values()) for row in waz])
        
        return render_template("award.html", award=waz, page_url = waz_page_url, award_name="WAZ", title="WAZ Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "waz"))





# # # # # # # # # # # # # # # # # # # # #
# 
# WPX
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/wpx")
@cache.memoize(timeout=600, make_name=custom_cache_key())

def wpx():
    if g.web_session:
        response = g.web_session.get(wpx_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'accountStatusTable'})

        # Parse the table to get rows
        rows = table.find_all('tr')
        wpx = []

        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')

                current_row = {
                    'op': op,
                    'award': str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[0].find('a') else columns[0].text,
                    'new': columns[1].text,
                    'in_process': columns[2].text,
                    'awarded': columns[3].text,
                    'total': columns[4].text,
                }
                wpx.append(current_row)

#        db = get_db()
#        cursor = db.cursor()
#        cursor.execute('DELETE FROM waz WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO waz (op, award, new, in_process, awarded, total) VALUES (%s, %s, %s, %s, %s, %s)', [tuple(row.values()) for row in waz])
        
        return render_template("award.html", award=wpx, page_url = wpx_page_url, award_name="WPX", title="WPX Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "wpx"))





# # # # # # # # # # # # # # # # # # # # #
# 
# VUCC
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/vucc")
@cache.memoize(timeout=600, make_name=custom_cache_key())

def vucc():
    if g.web_session:
        response = g.web_session.get(vucc_page_url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'accountStatusTable'})

        # Parse the table to get rows
        rows = table.find_all('tr')
        vucc = []

        for row in rows[1:]:  # Skip the header row
                columns = row.find_all('td')

                current_row = {
                    'op': op,
                    'award': str(columns[0].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[0].find('a') else columns[0].text,
                    'new': columns[1].text,
                    'in_process': columns[2].text,
                    'awarded': columns[3].text,
                    'total': columns[4].text,
                }
                vucc.append(current_row)

#        db = get_db()
#        cursor = db.cursor()
#        cursor.execute('DELETE FROM waz WHERE op = %s', (op,))
#        cursor.executemany('INSERT INTO waz (op, award, new, in_process, awarded, total) VALUES (%s, %s, %s, %s, %s, %s)', [tuple(row.values()) for row in waz])
        
        return render_template("award.html", award=vucc, page_url = vucc_page_url, award_name="VUCC", title="VUCC Award Info")
    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "vucc"))





# # # # # # # # # # # # # # # # # # # # #
# 
# Find Call
#
# # # # # # # # # # # # # # # # # # # # #

@app.route("/find", methods=["POST", "GET"])
def find():
    if g.web_session:
        if request.method == "POST":
            act = request.form.get('act') 
            response = g.web_session.post('https://lotw.arrl.org/lotwuser/act', data={'act': act})
            if "Last upload" in response.text:
                match_yes = re.search(r'Last upload for <b>[^<]+</b>&#58; \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z', response.text)
                match_no = re.search(r'Last upload for <b>[^<]+</b>&#58; No log data found', response.text)
                if match_yes:
                    last_upload_info = match_yes.group(0).replace('&#58;', '&#58;<br />')
                elif match_no:
                    last_upload_info = match_no.group(0).replace('&#58;', '&#58;<br />')
                else:
                    last_upload_info = "Please enter a call sign."
                return render_template('find.html', results=last_upload_info, title="Logbook Call Sign Activity")
            else:
                return render_template('find.html', error_msg="There was an error. Please try again.", title="Logbook Call Sign Activity")
        else:
            return render_template('find.html', title="Logbook Call Sign Activity")

    else:
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "find"))






# # # # # # # # # # # # # # # # # # 
#
# Account Credit Details
#
# # # # # # # # # # # # # # # # # # 

@app.route("/accountcredits")
def accountcredits():
    if g.web_session:
        url = 'awg_id=' + request.args.get('awg_id') + '&ac_acct=' + request.args.get('ac_acct') + '&aw_id=' + request.args.get('aw_id') + '&ac_view=allc'
        response = g.web_session.get('https://lotw.arrl.org/lotwuser/accountcredits?' + url)
        op = request.cookies.get('op')
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', attrs={'id': 'creditsTable'})

        rows = table.find_all('tr')
        rows[0].decompose()

        rows = table.find_all('tr')
        if request.args.get('awg_id') == 'WAS':
            th = lookup_label(request.args.get('aw_id')) # Pass WAS to the table in the view on the next page

        elif request.args.get('awg_id') == 'WAZ':
            th = lookup_label(request.args.get('aw_id')) # Pass WAZ to the table in the view on the next page

        elif request.args.get('awg_id') == 'VUCC':
            if request.args.get('aw_id') == 'FFMA':
                th = "Fred Fish Memorial Award"
            else:
                th = lookup_label(request.args.get('aw_id'))

        elif request.args.get('awg_id') == 'WPX':
            th = lookup_label(request.args.get('aw_id')) # Pass WPX to the table in the view on the next page

        else:
            # rows[-1].decompose()  # Remove the last row because challenge is too big
            th = lookup_dxcc_label(request.args.get('aw_id')) # Pass DXCC to the table in the view on the next page

        award_details = []

        rows = table.find_all('tr')
        for row in rows: 
            columns = row.find_all('td')
            if request.args.get('awg_id') == 'WAS':
                current_row = {
                    'label': re.sub(r'(?s).+ \((\w+)\)', r'\1', columns[0].text), # reduce states to abbreviations,
                    'value': str(columns[1].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[1].find('a') else columns[1].text,
                }
            elif request.args.get('awg_id') == 'WAZ':
                current_row = {
                    'label': columns[0].text,
                    'value': str(columns[1].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[1].find('a') else columns[1].text,
                }
            else:
                current_row = {
                    'label': columns[0].text,
                    'value': str(columns[1].find('a')).replace(' target="_new"', '').replace(' target="+new"', '') if columns[1].find('a') else columns[1].text
                }
            award_details.append(current_row)

        award = request.args.get('awg_id')
        title = request.args.get('awg_id') + " All Credits"
        return render_template("award_details.html", award=award, th=th, award_details=award_details, title=title)

    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "dxcc"))




# # # # # # # # # # # # # # # # # # 
#
# QSL Details
#
# # # # # # # # # # # # # # # # # # 


@app.route("/qsodetail")
def qsodetail():
    if g.web_session:
        response = g.web_session.get(details_page_url + request.args.get('qso'))
        soup = BeautifulSoup(response.content, 'html.parser')
        for element in soup(text=lambda text: isinstance(text, Comment)):
            element.extract()
        tables = soup.find_all('table')
        table = tables[6]

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            for cell in cells:
                if cell.has_attr('colspan') and cell['colspan'] == '3':
                    row.decompose()

        qsl_details = []

        rows = table.find_all('tr')
        for row in rows: 
            columns = row.find_all('td')
            current_row = {
                'label': columns[0].text,
                'value': columns[2].text
            }
            qsl_details.append(current_row)

        return render_template("qsl_details.html", qsl_details=qsl_details, title="QSL Details")

    else:  
        flash("Please login.", "info")
        return redirect(url_for("login", next_page = "qsls"))


# # # # # # # # # # # # # # # #
#
# Logout
#
# # # # # # # # # # # # # # # #

@app.route("/logout")
def logout():
    session.pop('web_session_cookies', None)
    session.pop('logged_in', None)
    if hasattr(g, 'web_session') and g.web_session:
        g.web_session.cookies.clear()
    g.web_session = None
    cache.clear()
    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie('op')
    return resp


# # # # # # # # # # # # # # # #
#
# DB connection
#
# # # # # # # # # # # # # # # #

def get_db():
    if 'db' not in g:
        g.db = conn = psycopg2.connect(
        dbname='mobile_lotw',
        user=os.environ['DB_USERNAME'],
        password=os.environ['DB_PASSWORD'],
        host='localhost',
        port='5432'
        )
    return g.db


# # # # # # # # # # # # # # # #
#
# Lookup table for awards
#
# # # # # # # # # # # # # # # #


def lookup_dxcc_label(arg):
    if arg == "DXCC-M":
        return "Mixed"
    elif arg == "DXCC-CW":
        return "CW"
    elif arg == "DXCC-PH":
        return "Phone"
    elif arg == "DXCC-RTTY":
        return "Digital"
    elif arg == "DXCC-SAT":
        return "Satellite"
    elif arg == "DXCC-160":
        return "160M"
    elif arg == "DXCC-80":
        return "80M"
    elif arg == "DXCC-40":
        return "40M"
    elif arg == "DXCC-30":
        return "30M"
    elif arg == "DXCC-20":
        return "20M"
    elif arg == "DXCC-17":
        return "17M"
    elif arg == "DXCC-15":
        return "15M"
    elif arg == "DXCC-12":
        return "12M"
    elif arg == "DXCC-10":
        return "10M"
    elif arg == "DXCC-6":
        return "6M"
    elif arg == "DXCC-2":
        return "2M"
    elif arg == "DXCC-3CM":
        return "3CM"
    elif arg == "DXCC-13CM":
        return "13CM"
    elif arg == "DXCC-70CM":
        return "70CM"
    elif arg == "DXCC-23CM":
        return "23CM"
    elif arg == "DXCC-CHAL":
        return "Challenge"
    else:
        return "Worked"


def lookup_label(arg):
    if arg.count("-") == 0:
        return "Mixed"
    elif arg.count("-") == 1:
        band = arg.split("-")[1]
        if band[-1] == "M":
            return band
        elif band[0].isdigit():
            return band + "M"
        else:
            return band
    elif arg.count("-") == 2:
        x, band, mode = arg.split("-")
        if band[0].isdigit():
            return band + "M " + mode
        else:
            return band + " " + mode
    else:
        return "Worked"




if __name__ == '__main__':
    app.run(debug=True)