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

    # Temp testing text here
    #client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    #sms = client.messages.create(body='test',
    #        to=user.phone,
    #        from_="+16507775414")
    #return(str(resp))

    # Response messages
    
    # User texts "subscribe"
    if rec_text == 'SUBSCRIBE':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            # add subscription
            resp_text = add_subscription(user, symbols)

    # User texts "unsubscribe"
    elif rec_text == 'UNSUBSCRIBE':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            resp_text = delete_subscription(user, symbols)

    # User texts "moreinfo"
    elif rec_text == 'MOREINFO' or rec_text == 'MORE INFO':
        symbols = check_lastsymbol(user)
        if not symbols:
            resp_text = 'Please text some symbols first'
        else:
            # more_info handles sending messages, no response
            more_info(user, symbols)
            resp_text = ''#more_info(user, symbols)
        #resp_text = 'request more info'
        #print(info)
        #with resp.message() as message:
        #    message.body = info[0]
        #    for url in info[1]:
        #        message.media(url)

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

def more_info(user, symbols):
    client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # Manual Yahoo
    url = 'http://finance.yahoo.com/webservice/v1/symbols/' + ','.join(symbols) + '/quote'
    r = requests.get(url, params = {'format': 'json',
                                'view': 'detail'})
    # Encoding UTF-8
    yahoo = json.loads(r.content.decode('UTF-8'))
    
    # Returns stock price
    #return(stock['list']['resources'][0]['resource']['fields']['price'])
    #return
    # Extract fields for each stock
    stocks = [stock['resource']['fields'] for stock in yahoo['list']['resources']]
    print(stocks)
    # picks stock that matches symbol...old code
    #stock = [stock for stock in stocks['list']['resources'][0] if stock['resource']['fields']['symbol'] == symbol]
#    return jsonify({'stock': stock[0]})

# Responds with additional information for user's last request symbol
#def more_info(user):
    for stock in stocks:
        message = ''
        # URL for chart
        base_media_url = 'https://www.google.com/finance/getchart?q='
        media = base_media_url + stock['symbol']
    ## Twilio limits to 10 images (will change to multiple messages instead)
    #count = 1
    #for symbol in symbols:
    #    media.append(base_media_url + symbol)
    #    if count == 10:
    #        break
    #    count += 1
    #count = 1
    #stocks = getQuotes(symbols)
    #for stock in stocks:
        print(stock)
        message += 'Info on %s '%stock['issuer_name']
        message += '(%s): '%stock['symbol']
        message += 'last trade price = %s | '%str(round(float(stock['price']),2))
        message += 'time = %s | '%stock['utctime']
        message += 'day high = %s | '%str(round(float(stock['day_high']),2))
        message += 'day low = %s | '%str(round(float(stock['day_low']),2))
        message += 'change percent = %s %%'%str(round(float(stock['chg_percent']),2))
        #if count == 10:
        #    break
        #count += 1
        print('attempting to send message to: %s'%user.phone)
        print('message: %s'%message)
        print('media url: %s'%media)
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
    for symbol in user.lastsymbol.split(' '):
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
