import re

import fuzzywuzzy.fuzz
import pdfplumber
import importlib
import Levenshtein
import constants
import fuzzywuzzy
from pprint import pprint

supported_customers = ['servicefoods', 'bidfood', 'kaanscateringsupplies', 'davis']

po_patterns = {
    "servicefoods": {
        "name": "Service Foods",
        "regex": r"PO\d{5,}"
    },
    "bidfood": {
        "name": "Bidfood",
        "regex": r"\b\d{8,10}\b"
    },
    "kaanscateringsupplies": {
        "name": "Kaan's Catering Supplies",
        "regex": r"\bPO\d{7}\b"
    },
    "davis": {
        "name": "Davis",
        "regex": r"\bA\d{5}\b"
    }
}
ACCOUNT_CODE = 211 # FOOD DISTRIBUTORS


def find_reference_number(company_name, data):
    if company_name not in po_patterns:
        return None
    pattern = po_patterns[company_name]["regex"]
    for line in data:
        match = re.search(pattern, line['text'])
        if match:
            return match.group()
    return None

def customer_extractor(file_name):
    customer_details = ''
    company_name = ''
    with pdfplumber.open(file_name) as pdf:
        po = pdf.pages[0]
        best_ratio = 0
        data = po.extract_text_lines()
        for text in data:
            temp = text['text'].lower().replace(' ', '').replace('@', '').replace('.','').replace("worldfoodsnz", '')

            for cust in constants.inv_customers:
                ratio = Levenshtein.ratio(temp, cust["Name"].lower().replace(' ', ''))
                if ratio > best_ratio:
                    print(f"best cust match so far: {cust['Name']} from {temp}")
                    customer_details = cust
                    best_ratio = ratio

        #print(f"Customer: {customer_details["Name"]}")

        best_ratio = 0 #reset
        for sc in supported_customers:
            ratio = Levenshtein.ratio(sc, customer_details["Name"].lower().replace(' ', ''))
            if ratio > best_ratio:
                company_name = sc
                best_ratio = ratio

        reference_no = find_reference_number(company_name, data)


        #print(f"Reference: {reference_no}")

        # pattern = po_patterns[company_name]["regex"]
        #
        # for text in data:
        #     temp = text['text'].lower().replace(' ', '')
        #     match = re.search(pattern, temp)
        #     if match:
        #         return match.group()

        print(f"Company: {company_name}")
        return customer_details, company_name, reference_no

def details_extractor(customer, file_name):
    try:
        parser_module = importlib.import_module(f"parsers.{customer}")
        return parser_module.process_pdf(file_name)
    except Exception as e:
        print(f"Error processing {file_name}: {e}")

def build_invoice(file_name):
    customer_details, company_name, reference_number = customer_extractor(file_name)
    po_items = details_extractor(company_name, file_name)
    line_items = build_line_items(po_items, company_name)

    invoice_data = {
        "Invoices":[
            {
                "Type": "ACCREC",
                "LineAmountTypes": "Exclusive",
                "Reference": reference_number,
                "Status": "DRAFT",  # ensuring that the invoice will be DRAFT
                "Contact": {
                    "ContactID": customer_details["ContactID"],
                    "Name": customer_details["Name"]
                },
                "LineItems": line_items
            }
        ]
    }

    pprint(invoice_data)
    return invoice_data


def create_line_item(po_item, xero_item, company_name):
    parser_module = importlib.import_module(f"parsers.{company_name}")
    quantity = parser_module.adjust_quantity(po_item, xero_item)
    total_price = po_item["total_price"]
    unit_price = round(float(total_price) / float(quantity), 4)
    tax_price = float(total_price) * 0.15 # GST
    line_item = {
        "ItemCode": xero_item["Code"],
        "Description": xero_item["Description"],
        "Quantity": float(quantity),
        "LineAmount": float(total_price),
        "UnitAmount": float(unit_price),
        "TaxAmount": float(tax_price),
        "AccountCode": ACCOUNT_CODE
    }
    return line_item

def build_line_items(po_items, company_name):
    line_items = []
    weight_tolerance = 100 # weight penalty
    brand_bonus_points = 30 # brand points increase
    for po_item in po_items:
        item = po_item["description"].lower()
        target_item = ''
        best_score = 0
        for db_item in constants.inv_items:
            ratio = fuzzywuzzy.fuzz.token_set_ratio(item, db_item["Description"].lower())

            if ratio > 30: ## most likely similar
                db_weight, db_unit = extract_weight_and_unit(db_item["Description"].lower())
                item_weight, item_unit = extract_weight_and_unit(item)
                if item_unit != db_unit:
                    continue

                if item_weight is not None and db_weight is not None:
                    diff = abs(item_weight - db_weight)
                    weight_penalty = (diff**2) / weight_tolerance # increased weight tolerance

                    final_score = ratio - weight_penalty
                    #pprint(f"po_item: {item} looking at Item: {db_item["Description"]}: final score = {final_score}")

                    for brand in constants.BRANDS:
                        if (normalize_brand(brand) in normalize_brand(item)
                                and normalize_brand(brand) in normalize_brand(db_item["Description"].lower())): # optimize
                            final_score += brand_bonus_points
                            break  # only add bonus once per item
                else:
                    final_score = ratio

                # print(f"po_item: {item} looking at Item: {db_item}: final score = {final_score}")
                if final_score > best_score:
                    best_score = final_score
                    target_item = db_item
        # print(f"Chosen for: {item} is == {target_item['Description']}")
        line_item = create_line_item(po_item, target_item, company_name)
        line_items.append(line_item)

    return line_items

def normalize_brand(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

def extract_weight_and_unit(description):
    match = re.search(r'(\d+(\.\d+)?)(kg|g|lt|l|ml)', description, re.IGNORECASE)
    if match:
        weight = float(match.group(1))
        unit = match.group(3).lower()
        if unit == 'kg':
            return weight * 1000, 'kg'
        elif unit == 'g':
            return weight, 'g'
        elif unit in ['l', 'lt']:
            return weight * 1000, 'l'
        elif unit == 'ml':
            return weight, 'ml'
    return None, None

def is_similar_weight(w1, w2, tolerance=0.1):
    if not w1 or not w2:
        return True  # don't block if no weights
    return abs(w1 - w2) / w2 <= tolerance
