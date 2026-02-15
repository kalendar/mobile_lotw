### [⬅️ Back ](/README.md)

## Setup development environment

❗❗ Rename example.env to .env and change the default value(s).

❗❗ **The app will not run until you complete this step.** 

Either run `setup.[bat|sh]` or:
1. Create a virtual environment at the root named `.venv`.
2. Enter the virtual environment.
3. Install requirements.txt with `pip install -r requirements.txt`.

Start the development server with either `start_development_server.[bat|sh]` or:
1. Enter the virtual environment.
2. Run `flask --app app --debug run` in the root directory  .

### Optional packages

Optional python packages for development are included in 
`opt_dev_requirements.py`.
1. Black Formatter for consistent code style.
2. isort for nice `import`/`from` styling.
3. Flake8 for code style Black doesn't catch.

### Optional for Prettier

Jinja templates are formatted by Prettier. The `.prettierrc` is configured to use 
[prettier-plugin-jinja-template](https://github.com/davidodenwald/prettier-plugin-jinja-template)
for proper Jinja support.

### Optional for VS Code

If you are running VS Code, I recommend installing these extensions:
1. [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter)
2. [isort](https://marketplace.visualstudio.com/items?itemName=ms-python.isort)
3. [Flake8](https://marketplace.visualstudio.com/items?itemName=ms-python.flake8)

And adding/changing the workspace settings with these:
```json
"isort.args":["--profile", "black", "--settings-file=pyproject.toml"],
"flake8.args":["--config=.flake8"],
"flake8.importStrategy":"fromEnvironment",
"black-formatter.args": ["--line-length", "80"],
"[python]": {
	"editor.defaultFormatter": "ms-python.black-formatter",
	"editor.formatOnSave": true,
	"editor.wordBasedSuggestions": false,
	"editor.codeActionsOnSave": {
		"source.organizeImports": true
	},
},
``` 
You can change the workspace settings by typing `ctrl+shift+p`, then
`workspace json`, and selecting "Preferences: Open Workspace 
Settings (JSON)". Then, paste the above JSON into the file.

## For production

❗❗ Make the Apache user (www-data) the owner of the directory and files.
```sh
sudo chown -R www-data:www-data /var/www/mobile_lotw/mobile_lotw
```

If you want to use the Github Actions-based depliy, you'll need to 
add a line like the following to your sudoers file using visudo:

```your_flask_user ALL=(ALL) NOPASSWD: /var/www/mobile_lotw/mobile_lotw/deploy.sh```

Creating an index on the database will greatly speed up performance 
once you have some data in there:

```CREATE INDEX idx_qso_user_id_rxqsl ON qso_reports(user_id, app_lotw_rxqsl DESC);```

### Example Apache config file:

```xml
<IfModule mod_ssl.c>
  WSGIPythonHome /var/www/mobile_lotw/mobile_lotw/.venv
	<VirtualHost *:443>
		ServerName mobilelotw.org
		ServerAdmin youremail@here.com
		WSGIDaemonProcess app python-home=/var/www/mobile_lotw/mobile_lotw/.venv python-path=/var/www/mobile_lotw/mobile_lotw
		WSGIScriptAlias /app /var/www/mobile_lotw/mobile_lotw.wsgi

		<Directory /var/www/mobile_lotw/mobile_lotw/>
			Order allow,deny
			Allow from all
		</Directory>

		Alias /static /var/www/mobile_lotw/mobile_lotw/app/static
		
		<Directory /var/www/mobile_lotw/mobile_lotw/app/static/>
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

### Example mobile_lotw.wsgi file:

```py
import os
import sys
path = '/var/www/mobile_lotw'
if path not in sys.path:
   sys.path.insert(0, path)

# Key to encode session information.
os.environ['MOBILE_LOTW_SECRET_KEY'] = 'your_secret_here'

# Name of the sqlite database.
os.environ['DB_NAME'] = 'mobile_lotw.db'

# Time in minutes before expiring cached information.
os.environ['SESSION_CACHE_EXPIRATION'] = '30'

# Timeout for requests to lotw.arrl.org in seconds.
os.environ['LOTW_REQUEST_TIMEOUT_SECONDS'] = '20'

# Use secure session cookies in production HTTPS environments.
os.environ['MOBILE_LOTW_SECURE_COOKIES'] = '1'

# Background import worker count.
os.environ['QSO_IMPORT_MAX_WORKERS'] = '2'

# Set to 1 to require active paid subscription for premium routes.
os.environ['REQUIRE_ACTIVE_SUBSCRIPTION'] = '0'

# URL to the postgresql database
os.environ['DB_URL'] = "postgresql+psycopg://david:password@localhost:5432/mobile_lotw"

# The API key for the deployment endpoint.
os.environ['API_KEY'] = "REPLACE_ME_NOW"

# Optional deploy webhook security (preferred over API key in URL/query).
os.environ['DEPLOY_WEBHOOK_SECRET'] = "REPLACE_ME_NOW"
os.environ['DEPLOY_ALLOWED_IPS'] = "127.0.0.1,10.0.0.1"

# The path to your deployment script.
os.environ['DEPLOY_SCRIPT_PATH'] = "/path/to/your/deploy/script"

# Optional Stripe settings for billing/subscriptions.
os.environ['STRIPE_SECRET_KEY'] = "REPLACE_ME_NOW"
os.environ['STRIPE_WEBHOOK_SECRET'] = "REPLACE_ME_NOW"
os.environ['STRIPE_PRICE_ID_MONTHLY'] = "price_REPLACE_ME"
os.environ['STRIPE_PRICE_ID_ANNUAL'] = "price_REPLACE_ME"
# Optional backward-compatible fallback if monthly key is not set:
os.environ['STRIPE_PRICE_ID'] = "price_REPLACE_ME"

# QSL digest notification controls.
os.environ['DIGEST_NOTIFICATIONS_ENABLED'] = "1"
os.environ['WEB_PUSH_ENABLED'] = "1"
os.environ['DIGEST_EMAIL_ENABLED'] = "1"
os.environ['DIGEST_DRY_RUN'] = "0"

# Web push VAPID settings.
os.environ['WEB_PUSH_VAPID_PUBLIC_KEY'] = "REPLACE_ME_NOW"
os.environ['WEB_PUSH_VAPID_PRIVATE_KEY'] = "REPLACE_ME_NOW"
os.environ['WEB_PUSH_VAPID_SUBJECT'] = "mailto:info@mobilelotw.org"

# Digest links and SMTP fallback.
os.environ['DIGEST_BASE_URL'] = "https://mobilelotw.org"
os.environ['DIGEST_SMTP_HOST'] = "smtp.example.com"
os.environ['DIGEST_SMTP_PORT'] = "587"
os.environ['DIGEST_SMTP_USERNAME'] = "REPLACE_ME_NOW"
os.environ['DIGEST_SMTP_PASSWORD'] = "REPLACE_ME_NOW"
os.environ['DIGEST_SMTP_FROM_EMAIL'] = "info@mobilelotw.org"
os.environ['DIGEST_SMTP_STARTTLS'] = "1"

from mobile_lotw.app import create_app

application = create_app()
```

### Database migrations

Run Alembic migrations after deployment changes that add columns or tables:

```sh
alembic upgrade head
```

### QSL digest production verification

After deployment and migration:
1. Verify `/notifications/settings` loads for a paid user.
2. Verify `/qsl/digest?date=YYYY-MM-DD` returns a digest page.
3. Verify browser push subscription API works:
   - `POST /api/v1/notifications/web-push/subscribe`
   - `POST /api/v1/notifications/web-push/unsubscribe`
4. Run one digest generation cycle and confirm rows in:
   - `qsl_digest_batches`
   - `notification_deliveries`

### Deploy endpoint hardening

The deploy endpoint now expects:
1. `POST /api/v1/deploy`
2. Either:
   - `X-MobileLoTW-Signature` header (HMAC-SHA256 of raw body using `DEPLOY_WEBHOOK_SECRET`), or
   - fallback `X-API-KEY` header if no webhook secret is configured
3. Optional source IP allowlist via `DEPLOY_ALLOWED_IPS`
