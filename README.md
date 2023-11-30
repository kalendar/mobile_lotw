# About Mobile LotW

Be honest - if you're using a smartphone, the ARRL Logbook of the World (LotW) website is really difficult to use. This tool gives you a clean, modern, delightful LotW experience on your mobile device.

## Technical Requirements

Mobile LotW uses Apache, WSGI, and Postgres.

Here's an example Apache config file:

```
IfModule mod_ssl.c>
<VirtualHost *:443>
                ServerName mobilelotw.org
                ServerAdmin youremail@here.com
                WSGIScriptAlias /app /var/www/mobile_lotw/mobile_lotw.wsgi
                <Directory /var/www/mobile_lotw/mobile_lotw/>
                        Order allow,deny
                        Allow from all
                </Directory>
                Alias /static /var/www/mobile_lotw/mobile_lotw/static
                <Directory /var/www/mobile_lotw/mobile_lotw/static/>
                        Order allow,deny
                        Allow from all
                </Directory>
                ErrorLog ${APACHE_LOG_DIR}/error.log
                LogLevel warn
                CustomLog ${APACHE_LOG_DIR}/access.log combined

SSLCertificateFile /etc/letsencrypt/live/mobilelotw.org/fullchain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/mobilelotw.org/privkey.pem
Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
```

and a sample mobile_lotw.wsgi file:

```
import sys
path = '/var/www/mobile_lotw'
if path not in sys.path:
   sys.path.insert(0, path)

os.environ['DB_USERNAME'] = 'your_db_username'
os.environ['DB_PASSWORD'] = 'your_db_password'
os.environ['MOBILE_LOTW_SECRET_KEY'] = 'your_flaskapp_secretkey'

from mobile_lotw.app import app as application
```
You can create the necessary Postgres tables using the init_db.py file in the repo.