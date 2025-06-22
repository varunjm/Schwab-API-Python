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
trades={}
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

def get_trades(start_date, end_date):
    global client
    global account_hash
    global trades
    
    # Note: Schwab API doesn't support filtering for sales only at API level
    # We must fetch all TRADE transactions and filter client-side
    trades = client.transactions(account_hash, start_date, end_date,"TRADE").json()

def get_all_sales(start_date, end_date):
    global client
    global account_hash
    global acc_positions
    global positions
    global trades
    
    print("=== STOCK SALES FOR TAX FILING ===\n")
    
    # Print header
    print(f"{'Date':<12} {'Symbol':<6} {'Action':<6} {'Shares':<10} {'Price':<10} {'Total':<12} {'Fees':<8}")
    print("-" * 70)
    
    sales_found = False
    
    for trade in trades:
        # Extract basic trade info
        trade_date = trade.get('tradeDate', '').split('T')[0]  # Get date part only
        
        # Process each transfer item (usually just one for stock trades)
        for item in trade.get('transferItems', []):
            instrument = item.get('instrument', {})
            
            # Skip currency/fee entries, focus on actual securities
            if instrument.get('assetType') in ['EQUITY', 'COLLECTIVE_INVESTMENT']:
                position_effect = item.get('positionEffect', '')
                amount = item.get('amount', 0)
                
                # Only show sales (CLOSING positions or negative amounts)
                if position_effect == 'CLOSING' or amount < 0:
                    symbol = instrument.get('symbol', 'N/A')
                    shares = abs(amount)
                    price = item.get('price', 0)
                    total_proceeds = abs(item.get('cost', 0))
                    
                    # Calculate fees (difference between total proceeds and shares * price)
                    calculated_total = shares * price
                    fees = abs(total_proceeds - calculated_total) if calculated_total > 0 else 0
                    
                    print(f"{trade_date:<12} {symbol:<6} {'SELL':<6} {shares:<10.4f} ${price:<9.2f} ${total_proceeds:<11.2f} ${fees:<7.2f}")
                    sales_found = True
    
    if not sales_found:
        print("No stock sales found in the specified time period.")
    
    print("\n" + "=" * 70)

def get_dividends(start_date, end_date):
    global trades

    # get all trades which have position_effect == 'OPENING' and are buying fractional shares
    # this corresponds to dividends earned by the stock. For each instance of purchase record
    # the dividend amount.
    dividends = []
    for trade in trades:
        if trade.get('transferItems')[0].get('positionEffect') == 'OPENING' and trade.get('transferItems')[0].get('amount') < 1:
            trade_date = trade.get('tradeDate', '').split('T')[0]  # Get date part only
            symbol = trade.get('transferItems')[0].get('instrument').get('symbol')
            # this transaction shows -ve value, take the positive of that as dividend
            dividends.append([trade_date, symbol, abs(trade.get('netAmount'))])
    
    print("Dividends earned:")
    print(f"{'Date':<12} {'Symbol':<6} {'Amount':<10}")
    print("-" * 30)
    for div in dividends:
        print(f"{div[0]:<12} {div[1]:<6} ${div[2]:<9.2f}")
    print("-" * 30)
    total = sum(div[2] for div in dividends)  # Amount is now at index 2
    print(f"{'Total:':<19} ${total:<9.2f}")

    # generate a table of dividends earned by stock

def main():
    global client
    load_client()

    # Generate assets table
    get_positions()
    generate_assets_table()

    prev_fy_start = datetime(2024, 4, 1)
    prev_fy_end = datetime(2025, 3, 31)
    get_trades(prev_fy_start, prev_fy_end)

    # Generate sales table
    get_all_sales(prev_fy_start, prev_fy_end)

    # Generate dividends table
    get_dividends(prev_fy_start, prev_fy_end)


if __name__ == '__main__':
    print("Welcome to the unofficial Schwab interface!\n")
    main()  # call the user code above
