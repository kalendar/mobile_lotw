Here are sample Apache config and WSGI config files

/etc/apache2/sites-available/mobile-lotw-viewer-le-ssl.conf:
```
IfModule mod_ssl.c>
<VirtualHost *:443>
                ServerName mobilelotw.org
                ServerAdmin youremail@here.com
                WSGIScriptAlias / /var/www/mobile_lotw/mobile_lotw.wsgi
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

/var/www/mobile_lotw/mobile_lotw.wsgi:
```
import os
import sys
path = '/var/www/mobile_lotw'
if path not in sys.path:
   sys.path.insert(0, path)

os.environ['DB_USERNAME'] = 'your_db_username'
os.environ['DB_PASSWORD'] = 'your_db_password'
os.environ['MOBILE_LOTW_SECRET_KEY'] = 'your_flask_app_secret_key'

from mobile_lotw.app import app as application
```
