from pprint import pprint

import requests
import json
from Constants import customers, BLOCKED_ITEMS
from urllib.parse import quote


base_url = "https://api.xero.com/api.xro/2.0/"

def get_items(access_token, xero_tenant_id):
    def is_blocked(item_desc):
        item_desc = item_desc.lower()
        return any(blocked in item_desc for blocked in BLOCKED_ITEMS)

    headers = {
        "xero-tenant-id": xero_tenant_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.get(f'{base_url}Items', headers=headers)
    response.raise_for_status()

    items = response.json()["Items"]

    target_codes = {"92682", "88531"}  # RedHot Original 3.78L, RedHot Original 148mlx12

    items[:] = [
        {**item, "Description": item["Description"].replace("Original", "Original Cayenne Pepper")}
        if item["Code"] in target_codes else item
        for item in items
        if not is_blocked(item["Description"])
    ]

    pprint(items)
    return items

def get_customers(access_token, xero_tenant_id):
    customer_data = []
    headers = {
        "xero-tenant-id": xero_tenant_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    for customer in customers:
        search_term = quote(customer)
        response = requests.get(f"{base_url}Contacts?SearchTerm={search_term}", headers=headers)
        response.raise_for_status()
        # print(f"{base_url}Contacts?SearchTerm={customer}")

        for contact in response.json()["Contacts"]:
            if "FOODSERVICE DIVISION" not in contact["Name"]: # TODO: remove when contact is removed in Xero
                customer_data.append(contact)

    # print(customer_data)
    return customer_data

def create_invoice(invoice_data, access_token, xero_tenant_id):
    headers = {
        "xero-tenant-id": xero_tenant_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url="https://api.xero.com/api.xro/2.0/Invoices",
        headers=headers,
        data=json.dumps(invoice_data)
    )

    if response.status_code == 200 or response.status_code == 201:
        print("Invoice created successfully:")
        print(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)