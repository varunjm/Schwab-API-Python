import schwabdev
from datetime import datetime, timedelta
from dotenv import load_dotenv
from time import sleep
import os
import json


def main():
    # place your app key and app secret in the .env file
    load_dotenv()  # load environment variables from .env file

    # create client
    client = schwabdev.Client(os.getenv('SCHWAB_APP_KEY'), os.getenv('SCHWAB_SECRET'), 'https://127.0.0.1', verbose=True)

    print("\n\nAccounts and Trading - Accounts.")

    # get account number and hashes for linked accounts
    print("|\n|client.account_linked().json()", end="\n|")
    linked_accounts = client.account_linked().json()
    print(json.dumps(linked_accounts, indent=4))
    # this will get the first linked account
    account_hash = linked_accounts[0].get('hashValue')
    sleep(3)

    # get positions for linked accounts
    print("|\n|client.account_details_all().json()", end="\n|")
    account_positions = client.account_details_all().json()
    print(json.dumps(account_positions, indent=4))
    sleep(3)

    # get specific account positions (uses default account, can be changed)
    print("|\n|client.account_details(account_hash, fields='positions').json()", end="\n|")
    specific_acc_position = client.account_details(account_hash, fields="positions").json()
    print(json.dumps(specific_acc_position, indent=4))
    sleep(3)

if __name__ == '__main__':
    print("Welcome to the unofficial Schwab interface!\n")
    main()  # call the user code above
