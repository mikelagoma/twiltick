from flask import jsonify, request, abort, make_response, render_template, url_for

from app import app, db
from .models import User, Message, Subscription
from datetime import datetime
import json
import requests
from googlefinance import getQuotes
from twilio import twiml
from twilio.rest import TwilioRestClient
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
import os, re, string

# Route used to handle Twilio POST request
@app.route('/twiltick/sms', methods=['GET', 'POST'])
def receive_sms():
    # Get message info
    rec_phone = request.form['From']
    rec_text = request.form['Body']

    # Add user to database if not already there
    user = User.query.filter_by(phone=rec_phone).first()
    if user is None:
        user = User(phone=rec_phone)
        db.session.add(user)
        db.session.commit()

    # Add message to database
    message = Message(body=rec_text,
            timestamp=datetime.utcnow(),
            sender=user)
    db.session.add(message)
    db.session.commit()

    # Replace message commas with spaces, strip white space, uppercase
    rec_text = re.sub(',', ' ', rec_text).strip().upper()

    # Prepare response
    resp = twiml.Response()

    # Response messages
    
    # User texts "notify"
    if rec_text == 'NOTIFY':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            # add subscription
            resp_text = add_subscription(user, symbols)

    # User texts "remove"
    elif rec_text == 'REMOVE':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            resp_text = delete_subscription(user, symbols)

    # User texts "remove all"
    elif rec_text == 'REMOVEALL' or rec_text == 'REMOVE ALL':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            resp_text = delete_all_subscriptions(user)

    # User texts "moreinfo"
    elif rec_text == 'MOREINFO' or rec_text == 'MORE INFO':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            # more_info handles sending messages, no response
            more_info(user, symbols)
            resp_text = ''

    # Assume message contains stock symbols
    else:
        symbols = rec_text.split()
        resp_text = get_price(user, ','.join(symbols))
    
    #Send response
    resp.message(resp_text)
    return(str(resp))

def check_lastsymbol(user):
    # Check for user's lastsymbol
    if user.lastsymbol:
        symbols = user.lastsymbol.split(' ')
        print(user.lastsymbol)
        return symbols
    else:
        return 

# Get price and update user
def get_price(user, symbols):
    # Google Finance library
    try:
        stocks = getQuotes(symbols)
    except:
        return('Symbol not found')
    # Create string of symbols and update user
    symbols = ['%s'%stock['StockSymbol'] for stock in stocks]
    user.lastsymbol = ' '.join(symbols)
    db.session.add(user)
    db.session.commit()

    # Create string of symbol: price and return to message
    prices = ['%s: %s'%(stock['StockSymbol'],stock['LastTradePrice']) for stock in stocks]
    return(', '.join(prices))

#    # Manual Google
#    payload = {'client': 'ig', 'q': symbol}
#    try:
#        r = requests.get('http://finance.google.com/finance/info', params=payload)
#    except requests.exceptions.RequestException as e:
#        #print(e)
#        return('stock not found')
#    print(r.headers['content-type'])
#    stock = r.content.decode('ISO-8859-1')
#    print(stock)
#    if stock.strip() != "httpserver.cc: Response Code 400":
#        # Encoding ISO-9959-1
#        stock = json.loads(stock[3:])
#    else:
#        return('stock not found')
#    print(stock)
#    #send_price(stock[0]['l'])
#    return(stock[0]['l'] + ' USD')

# Responds with additional information for user's last request symbol
def more_info(user, symbols):
    # Establish Twilio API client
    client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # Manual Yahoo
    url = 'http://finance.yahoo.com/webservice/v1/symbols/' + ','.join(symbols) + '/quote'
    r = requests.get(url, params = {'format': 'json',
                                'view': 'detail'})
    # Encoding UTF-8
    yahoo = json.loads(r.content.decode('UTF-8'))
    
    # Extract fields for each stock
    stocks = [stock['resource']['fields'] for stock in yahoo['list']['resources']]
    for stock in stocks:
        message = ''
        # URL for chart of this stock
        base_media_url = 'https://www.google.com/finance/getchart?q='
        media = base_media_url + stock['symbol']

        # Build message for this stock
        message += 'Info on %s '%stock['issuer_name']
        message += '(%s): '%stock['symbol']
        message += 'last trade price = %s | '%str(round(float(stock['price']),2))
        message += 'time = %s | '%stock['utctime']
        message += 'day high = %s | '%str(round(float(stock['day_high']),2))
        message += 'day low = %s | '%str(round(float(stock['day_low']),2))
        message += 'change = %s %%'%str(round(float(stock['chg_percent']),2))

        # Send MMS
        try:
            sms = client.messages.create(body=message,
                                        media_url=media,
                                        to=user.phone,
                                        from_="+16507775414")
            print(sms)
        except:
            print('number not verified, remove from database')
    return

# Adds entry to Subscription table for each of user's last requested symbols
def add_subscription(user, symbols):
    message = ''
    # Iterate through user's lastsymbol entry
    print(symbols)
    for symbol in symbols:
        # Query for existing subscription entry
        s = Subscription.query.filter_by(symbol=symbol, subscriber=user).first()
        # If not, add it
        if s is None:
            s = Subscription(symbol=symbol, subscriber=user)
            db.session.add(s)
            db.session.commit()
            # Symbols added
            message += symbol + ' '
    if not message:
        return 'You are already subscribed'
    else:
        return message + 'added to your subscriptions'

def delete_subscription(user, symbols):
    for s in symbols:
        print(s, user)
        sub = Subscription.query.filter_by(symbol=s,
                                subscriber=user).first()
        print(sub)
        if not sub:
            return 'Symbols already removed'
        db.session.delete(sub)
        db.session.commit()
    return 'Removed %s from your subscriptions'%' '.join(symbols)

def delete_all_subscriptions(user):
    subs = Subscription.query.filter_by(subscriber=user)
    for s in subs:
        db.session.delete(s)
        db.session.commit()
    return 'Removed all subscriptions'
    return
