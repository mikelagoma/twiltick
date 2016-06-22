from flask import jsonify, request, abort, make_response, render_template, url_for

from app import app, db
from .models import User, Message, Subscription
from datetime import datetime
import json
import requests
from googlefinance import getQuotes
from twilio import twiml
from twilio.rest import TwilioRestClient
import os, re, string

# Route used to handle Twilio POST request
@app.route('/twiltick/sms', methods=['GET', 'POST'])
def receive_sms():
    # Get message info
    r_phone = request.form['From']
    r_body = request.form['Body']

    # Add user to database if not already there
    user = User.query.filter_by(phone=r_phone).first()
    if user is None:
        user = User(phone=r_phone)
        db.session.add(user)
        db.session.commit()

    # Add message to database
    message = Message(body=r_body,
            timestamp=datetime.utcnow(),
            sender=user)
    db.session.add(message)
    db.session.commit()

    # Replace message commas with spaces, strip white space, uppercase
    r_body = re.sub(',', ' ', r_body).strip().upper()

    # Prepare response
    resp = twiml.Response()

    # Response messages

    # User texts "subscribe"
    if r_body == 'SUBSCRIBE':
        # add subscription
        message = add_subscription(user)
        resp.message(message)

    # User texts "moreinfo"
    elif r_body == 'MOREINFO' or r_body == 'MORE INFO':
        info = more_info(user)
        print(info)
        with resp.message() as message:
            message.body = info[0]
            for url in info[1]:
                message.media(url)

    # Assume message contains stock symbols
    else:
        symbols = r_body.split()
        message = get_price(user, ','.join(symbols))
        resp.message(message)
    
    #Send response
    return(str(resp))

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

    # Manual Google
    payload = {'client': 'ig', 'q': symbol}
    try:
        r = requests.get('http://finance.google.com/finance/info', params=payload)
    except requests.exceptions.RequestException as e:
        #print(e)
        return('stock not found')
    print(r.headers['content-type'])
    stock = r.content.decode('ISO-8859-1')
    print(stock)
    if stock.strip() != "httpserver.cc: Response Code 400":
        # Encoding ISO-9959-1
        stock = json.loads(stock[3:])
    else:
        return('stock not found')
    print(stock)
    #send_price(stock[0]['l'])
    return(stock[0]['l'] + ' USD')

#    # Manual Yahoo
#    url = 'http://finance.yahoo.com/webservice/v1/symbols/' + symbol + '/quote'
#    r = requests.get(url, params = {'format': 'json'})
#    # Encoding UTF-8
#    stock = json.loads(r.content.decode('UTF-8'))
#    print(stock)
#    return(stock['list']['resources'][0]['resource']['fields']['price'])
#    stock = [stock for stock in stocks[0]['list']['resources'] if stock['resource']['fields']['symbol'] == symbol]
#    if len(stock) == 0:
#        abort(404)
#    return jsonify({'stock': stock[0]})

# Responds with additional information for user's last request symbol
def more_info(user):
    message = ''
    # URL for chart
    base_media_url = 'https://www.google.com/finance/getchart?q='
    media = []
    symbols = user.lastsymbol.split(' ')
    # Twilio limits to 10 images (will change to multiple messages instead)
    count = 1
    for symbol in symbols:
        media.append(base_media_url + symbol)
        if count == 10:
            break
        count += 1
    count = 1
    stocks = getQuotes(symbols)
    for stock in stocks:
        print(stock)
        message += 'Info on %s: '%stock['StockSymbol']
        message += 'last trade price = %s '%stock['LastTradePrice']
        message += 'time = %s '%stock['LastTradeTime']
        if count == 10:
            break
        count += 1
    return (message, media)

# Adds entry to Subscription table for each of user's last requested symbols
def add_subscription(user):
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
