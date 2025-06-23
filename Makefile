assets:
	@python3 myaccount.py --assets

sales:
	@python3 myaccount.py --sales

dividends:
	@python3 myaccount.py --dividends

all:
	@python3 myaccount.py --all

new:
	@python3 myaccount.py --new

help:
	@python3 myaccount.py -h

.PHONY: assets sales dividends all help
