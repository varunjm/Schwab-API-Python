import schwabdev
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from time import sleep
import os
import json
import csv
import argparse

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


def get_positions():
    global client
    global account_hash
    global acc_positions
    global positions

    acc_positions = client.account_details(account_hash, fields="positions").json()
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
    dividends = client.transactions(account_hash, start_date, end_date, "DIVIDEND_OR_INTEREST").json()
    divs = []
    for dividend in dividends:
        trade_date = dividend.get('tradeDate', '').split('T')[0]  # Get date part only
        symbol = dividend.get('description')
        amount = dividend.get('transferItems')[0].get('amount')
        divs.append([trade_date, symbol, amount])

    print("Dividends earned:")
    print(f"{'Date':<12} {'Symbol':<40} {'Amount':<10}")
    print("-" * 62)
    for div in divs:
        print(f"{div[0]:<12} {div[1]:<40} ${div[2]:<9.2f}")
    print("-" * 62)

    # generate a table of dividends earned by stock

def get_tds(start_date, end_date):
    journals = client.transactions(account_hash, start_date, end_date, "JOURNAL").json()
    taxes = []
    for journal in journals:
        if (journal.get('transferItems')[0].get('amount') < 0):
            trade_date = journal.get('tradeDate', '').split('T')[0]  # Get date part only
            symbol = journal.get('description')
            amount = journal.get('transferItems')[0].get('amount')
            taxes.append([trade_date, symbol, amount])

    print("Taxes deducted:")
    print(f"{'Date':<12} {'Symbol':<40} {'Amount':<10}")
    print("-" * 62)
    for t in taxes:
        print(f"{t[0]:<12} {t[1]:<40} ${t[2]:<9.2f}")
    print("-" * 62)

def try_new_feature():
    global client
    global account_hash
    
    # Set up date range for transactions
    prev_fy_start = datetime(2024, 4, 1)
    prev_fy_end = datetime(2025, 3, 31)
    
    print("=== NEW FEATURE: ALL TRANSACTION TYPES ===\n")
    print("Fetching all transaction types...")
    
    # Get all transactions (remove the "TRADE" filter to get all types)
    all_transactions = client.transactions(account_hash, prev_fy_start, prev_fy_end, "").json()
    print(json.dumps(all_transactions, indent=2))

def main():
    parser = argparse.ArgumentParser(
        description='Unofficial Schwab interface for generating investment reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python myaccount.py --assets          Generate assets table only
  python myaccount.py --sales           Generate sales report only  
  python myaccount.py --dividends       Generate dividends report only
  python myaccount.py --tds             Generate taxes deducted report only
  python myaccount.py --new             Try new feature (all transaction types)
  python myaccount.py --all             Generate all reports
  python myaccount.py -h                Show this help message
        '''
    )
    
    parser.add_argument('--assets', action='store_true', 
                       help='Generate assets table (CSV file)')
    parser.add_argument('--sales', action='store_true',
                       help='Generate stock sales report for tax filing')
    parser.add_argument('--dividends', action='store_true',
                       help='Generate dividends report')
    parser.add_argument('--tds', action='store_true',
                       help='Generate taxes deducted report')
    parser.add_argument('--new', action='store_true',
                       help='Try new feature - analyze all transaction types')
    parser.add_argument('--all', action='store_true',
                       help='Generate all reports (assets, sales, and dividends)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any([args.assets, args.sales, args.dividends, args.tds, args.new, args.all]):
        parser.print_help()
        return
    
    print("Welcome to the unofficial Schwab interface!\n")
    
    # Load client - needed for all operations
    load_client()
    
    # Set up date range for transactions
    prev_fy_start = datetime(2024, 4, 1)
    prev_fy_end = datetime(2025, 4, 1) # It seems like end date is exclusive
    
    # Determine what to run based on arguments
    run_assets = args.assets or args.all
    run_sales = args.sales or args.all
    run_dividends = args.dividends or args.all
    run_tds = args.tds or args.all
    run_new = args.new
    
    # Generate assets table if requested
    if run_assets:
        print("Generating assets table...")
        get_positions()
        generate_assets_table()
        print()
    
    # Get trades data if needed for sales or dividends
    if run_sales or run_dividends:
        print("Fetching transaction data...")
        get_trades(prev_fy_start, prev_fy_end)
        print()
    
    # Generate sales report if requested
    if run_sales:
        get_all_sales(prev_fy_start, prev_fy_end)
        print()
    
    # Generate dividends report if requested
    if run_dividends:
        get_dividends(prev_fy_start, prev_fy_end)
    
    # Generate taxes deducted report if requested
    if run_tds:
        get_tds(prev_fy_start, prev_fy_end)
    
    # Try new feature if requested
    if run_new:
        get_tds(prev_fy_start, prev_fy_end)

if __name__ == '__main__':
    main()  # call the user code above

