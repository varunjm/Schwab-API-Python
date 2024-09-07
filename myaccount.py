import schwabdev
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from time import sleep
import os
import json
import csv

client=None
account_hash=None
linked_accounts=None
acc_positions=None
positions={}
metadata = {
    'NVDA': {'country': 'USA', 'Address': 'Santa Clara, California, USA', 'Zip Code': '95051', 'Nature': 'Equity'},
    'MSFT': {'country': 'USA', 'Address': 'Redmond, Washington, USA', 'Zip Code': '98052', 'Nature': 'Equity'},
    'VOO': {'country': 'USA', 'Address': 'Malvern, Pennsylvania, USA', 'Zip Code': '19355', 'Nature': 'Vanguard ETF'},
    'VOOG': {'country': 'USA', 'Address': 'Malvern, Pennsylvania, USA', 'Zip Code': '19355', 'Nature': 'Vanguard ETF'},
    'VTI': {'country': 'USA', 'Address': 'Malvern, Pennsylvania, USA', 'Zip Code': '19355', 'Nature': 'Vanguard ETF'},
    'VGT': {'country': 'USA', 'Address': 'Malvern, Pennsylvania, USA', 'Zip Code': '19355', 'Nature': 'Vanguard ETF'},
}

def load_client():
    global client
    global account_hash
    global linked_accounts
    global acc_positions

    load_dotenv()  # load environment variables from .env file
    app_key = os.getenv('SCHWAB_APP_KEY')
    app_secret = os.getenv('SCHWAB_SECRET')
    callback_url = 'https://127.0.0.1'
    client = schwabdev.Client(app_key, app_secret, callback_url, verbose=False)
    linked_accounts = client.account_linked().json()
    account_hash = linked_accounts[0].get('hashValue')
    acc_positions = client.account_details(account_hash, fields="positions").json()

def get_positions():
    global client
    global account_hash
    global acc_positions
    global positions

    # total = 0
    for position in acc_positions['securitiesAccount']['positions']:
        symbol = position['instrument']['symbol']
        qty = position['longQuantity']
        avg_price = position['averagePrice']
        ask_price = client.quotes([symbol]).json()[symbol]['quote']['askPrice']
        positions[symbol] = [qty, ask_price, avg_price]
        # total = total + qty * ask_price
    # print(json.dumps(positions, indent=4))
    # print('total : %f'%(total))

def get_all_stock_details(stock_symbol, position):
    global metadata
    stock_metadata = metadata.get(stock_symbol, {})
    Country = stock_metadata.get('country', 'N/A')
    Address = stock_metadata.get('Address', 'N/A')
    ZipCode = stock_metadata.get('Zip Code', 'N/A')
    Nature = stock_metadata.get('Nature', 'N/A')
    qty = position[0]
    askPrice = position[1]
    avgPrice = position[2]
    initialValue = round(qty*avgPrice, 2)
    closingValue = round(qty*askPrice, 2)

    return [Country, stock_symbol, Address, ZipCode, Nature, "-", initialValue, closingValue, closingValue]

def generate_assets_table():
    # Get current date and format it as YYYY-MM-DD
    today = date.today().strftime("%Y-%m-%d")
    
    # Create filename with current date
    filename = f'assets_{today}.csv'

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)

        headers = ['Country', 'Name', 'Address', 'Zip Code', 'Nature', 'Date of accruing interest', 'Initial Value', 'Peak Value', 'Closing Value']
        writer.writerow(headers)
        
        for stock_symbol, position in positions.items():
            writer.writerow(get_all_stock_details(stock_symbol, position))
    
    print(f"CSV file '{filename}' has been generated.")

def demo():
    global linked_accounts

    # get account number and hashes for linked accounts
    print("|\n|client.account_linked().json()", end="\n|")
    print(json.dumps(linked_accounts, indent=4))
    # this will get the first linked account
    sleep(1)

    # get positions for linked accounts
    print("|\n|client.account_details_all().json()", end="\n|")
    account_positions = client.account_details_all().json()
    print(json.dumps(account_positions, indent=4))
    sleep(1)

def main():
    global client
    load_client()
    get_positions()
    generate_assets_table()

if __name__ == '__main__':
    print("Welcome to the unofficial Schwab interface!\n")
    main()  # call the user code above
