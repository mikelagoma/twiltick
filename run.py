#!twiltick/bin/python
from flask_script import Server, Manager

from app import app, models, db
from app.sms import get_price
from googlefinance import getQuotes
#from .models import User, Subscription
from twilio.rest import TwilioRestClient
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
import schedule
import time

manager = Manager(app)
server = Server(host="0.0.0.0", port=5400)
manager.add_command("runserver", server)#Server())

client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

#@manager.command
def job():
    users = models.User.query.all()
    #price = get_price(users[4],"GOOG")
    print(users)
    for xuser in range(len(users)):
        print(xuser)
        user = users[xuser]
        print(user)
        subs = models.Subscription.query.filter_by(subscriber=user).all()
        print(subs)
        if subs:
            symbols = list()
            for sub in subs:
                symbols.append(sub.symbol)
            stocks = getQuotes(symbols)
            print('sending test message')
            prices = ['%s: %s'%(stock['StockSymbol'],stock['LastTradePrice']) for stock in stocks]
            print(user.phone)
            print(prices)
            try:
                sms = client.messages.create(body=', '.join(prices),
                        to=user.phone,
                        from_="+16507775414")
            except:
                print('number not verified, remove from database')

schedule.every(1).minutes.do(job)

@manager.command
def subs():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    manager.run()
    #app.run(host='0.0.0.0',port=5400,debug=True)
