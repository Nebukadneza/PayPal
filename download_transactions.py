#!/usr/bin/env python3
import sys, os, json

from pprint import pprint

import csv

from PaypalSDK.core import PayPalHttpClient, LiveEnvironment
from PaypalSDK import TransactionRequest

from IPython import embed

from appdirs import user_config_dir
from dateutil import tz
from datetime import datetime
from dateutil.parser import parse as parse_date
from fiscalyear import setup_fiscal_calendar, FiscalDateTime, FiscalYear

if not os.path.exists(user_config_dir("PayPal")):
    os.makedirs(user_config_dir("PayPal"))

cred_file = os.path.join(user_config_dir("PayPal"), "sdk_credentials.json")

CREDS = {}
if os.path.isfile(cred_file):
    with open(cred_file, "r") as file:
        CREDS = json.loads(file.read())

if not CREDS:
    with open(cred_file, "w") as file:
        file.write(
            json.dumps(
                {
                    "ID": "<your PayPal client ID here>",
                    "Secret": "<your PayPal secret here>",
                }
            )
        )

    print(
        "No PayPal SDK credentials available. Please add credentials details to {cred_file}",
        file=sys.stderr,
    )

else:
    # Creating an environment
    environment = LiveEnvironment(client_id=CREDS["ID"], client_secret=CREDS["Secret"])
    client = PayPalHttpClient(environment)

    #setup_fiscal_calendar(start_month=7)
    #dt_from = FiscalYear(FiscalDateTime.now().fiscal_year).start.astimezone(
    #    tz.tzlocal()
    #)
    #dt_to = FiscalDateTime.now().astimezone(tz.tzlocal())
    dt_from = datetime(2020, 1, 1).astimezone(tz.tzlocal())
    dt_to = datetime(2021, 1, 1).astimezone(tz.tzlocal())

    print("From", dt_from, "To", dt_to)
    request = TransactionRequest(dt_from, dt_to)

    transactions = request.execute(client)

    csvfile = open('out.csv', 'w', newline='')
    writer = csv.DictWriter(csvfile, delimiter=';', quotechar='"',
            quoting=csv.QUOTE_ALL, fieldnames=["date", "amount", "currency", "partner", "note", "cart"])
    writer.writeheader()
    for t in transactions:  # response.result.transaction_details:
        id = t.transaction_info.transaction_id
        note = getattr(t.transaction_info, "transaction_note", "")
        idate = (
            parse_date(t.transaction_info.transaction_initiation_date)
            .astimezone(tz.tzlocal())
            .strftime("%Y-%m-%d")
        )
        amount = float(t.transaction_info.transaction_amount.value)
        currency = t.transaction_info.transaction_amount.currency_code

        partner = ""
        if hasattr(t, "payer_info"):
            email = getattr(t.payer_info, "email_address", "")
            name = getattr(t.payer_info.payer_name, "alternate_full_name", "")
            account_id = getattr(t.payer_info, "account_id", "")

            partner = account_id
            partner += f" {name}" if name else ""
            partner += f" <{email}>" if email else ""
            partner = partner.strip()

        cart = ""
        if hasattr(t, "cart_info") and hasattr(t.cart_info, "item_details"):
            for item in t.cart_info.item_details:
                if hasattr(item, "item_name"):
                    cart += f", {item.item_name}"

        if partner == "":
            continue

        if hasattr(t.transaction_info, "bank_reference_id"):
            print("Skipping self-transaction!")
            continue

        #pprint(t.__dict__)
        writer.writerow({
                "date": str(idate),
                "amount": str(amount),
                "currency": str(currency),
                "partner": str(partner).replace(';', ' '),
                "note": str(note).replace(';', ' '),
                "cart": str(cart).replace(';', ' ')
        })
    csvfile.close()
