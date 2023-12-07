### [⬅️ Back ](/README.md)

## Setup development environment

❗❗ Rename example.env to .env and change the default value(s) 

Either run ```setup.[bat|sh]``` or:
1. Create a virtual environment at the root named .venv 
2. Enter the virtual environment
3. Install requirements.txt with ```pip install -r requirements.txt```
4. Rename example.env to .env and update its values.

Start the development server with either 
```start_development_server.[bat|sh]``` or:
1. Enter the virtual environment
2. Run ```flask --app app --debug run``` in the root directory  

### Optional for VSC

If you are running VS Code, I recommend installing these extensions:
1. [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter)
2. [Flake8](https://marketplace.visualstudio.com/items?itemName=ms-python.flake8)
3. [isort](https://marketplace.visualstudio.com/items?itemName=ms-python.isort)

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


from mobile_lotw.app import create_app

application = create_app()
```