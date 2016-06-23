# TwilTick

Twilio application that receives texts containing stock symbols and sends the price back with subscription option
## Usage
* Text stock symbols to your twilio number to receieve a response with the prices.

* Text "more info" to receive additional information about the last symbols requested.

* Text "notify" to add the last symbols requested to your subscriptions for daily price updates.

* Text "remove" to remove the last symbols requested or "removeall" to clear subscriptions.

## Installation
* Add environment variables to OS for Twilio information
```
TWILIO_ACCOUNT_SID = Your sid
TWILIO_AUTH_TOKEN = Your auth
TWILIO_NUMBER = Your purchased twilio phone number
```
* Create python virtual environment "twiltick"
```
$ python3 -m venv twiltick
```

* Install dependencies:
```
$ twiltick/bin/pip install --upgrade pip
$ twiltick/bin/pip install flask
$ twiltick/bin/pip install flask-sqlalchemy
$ twiltick/bin/pip install sqlalchemy-migrate
$ twiltick/bin/pip install requests
$ twiltick/bin/pip install twilio
$ twiltick/bin/pip install googlefinance
$ twiltick/bin/pip install flask_script
$ twiltick/bin/pip install schedule
```

* Create database:
```
$ twiltick/bin/python db_create.py
$ twiltick/bin/python db_migrate.py
```

* Run the server:
```
$ twiltick/bin/python run.py runserver
```

* Run subscription script:
```
$ twiltick/bin/python run.py subs
```
