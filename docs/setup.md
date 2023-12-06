### [⬅️ Back ](/README.md)

## Setup development environment

❗❗ Rename example.env to .env and change the default value(s) 

Either run ```setup.[bat|sh]``` or:
1. Create a virtual environment at the root named .venv 
2. Enter the virtual environment
3. Install requirements.txt with ```pip install -r requirements.txt```

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

❗❗ Rename example.env to .env and change the default value(s) 

### Example Apache config file:

```xml
<IfModule mod_ssl.c>
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

### Example mobile_lotw.wsgi file:

```py
import sys
path = '/var/www/mobile_lotw'

if path not in sys.path:
   sys.path.insert(0, path)

os.environ['MOBILE_LOTW_SECRET_KEY'] = 'your_flaskapp_secretkey'

from mobile_lotw.app import app as application
```