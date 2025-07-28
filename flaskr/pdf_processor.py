import re
import traceback

import fuzzywuzzy.fuzz
import pdfplumber
import importlib
import xmltodict
import Levenshtein
import constants
import fuzzywuzzy
from pprint import pprint

supported_customers = ['servicefoods', 'bidfood', 'kaanscateringsupplies', 'davis', 'gilmours']

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
    },
    "gilmours": {
        "name": "Gilmour"
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
    def customer_xero_matcher(_text, _best_ratio, best_match_customer_details):
        _customer_details = best_match_customer_details
        for cust in constants.inv_customers:
            _ratio = Levenshtein.ratio(_text, cust["Name"].lower().replace(' ', ''))
            if _ratio > _best_ratio:
                # print(f"best cust match so far: {cust["Name"]} from {_text}")
                _customer_details = cust
                _best_ratio = _ratio

        return _customer_details, _best_ratio

    def customer_parser_matcher(customer_name):
        _company_name = ''
        parser_best_ratio = 0
        for sc in supported_customers:
            ratio = Levenshtein.ratio(sc, customer_name.lower().replace(' ', ''))
            if ratio > parser_best_ratio:
                _company_name = sc
                parser_best_ratio = ratio
        return _company_name

    customer_details = ''
    company_name = ''
    if file_name.lower().endswith("pdf"):
        with pdfplumber.open(file_name) as pdf:
            po = pdf.pages[0]
            data = po.extract_text_lines()
            best_ratio = 0
            for text in data:
                temp = text['text'].lower().replace(' ', '').replace('@', '').replace('.','').replace("worldfoodsnz", '')
                customer_details, best_ratio = customer_xero_matcher(temp, best_ratio, customer_details)
            # print(f"Customer pdf found: {customer_details}")

            company_name = customer_parser_matcher(customer_details["Name"])
            reference_no = find_reference_number(company_name, data)

    elif file_name.lower().endswith("xml"): #Gilmours
        with open(file_name) as xml_file:
            dict_data = xmltodict.parse(xml_file.read())
            customer_extracted = dict_data["PURCHASE_ORDER_160"]["CUSTOMER"]["COMPANY"]["NAME"]
            customer_details, best_ratio = customer_xero_matcher(customer_extracted, 0, '')
            company_name = customer_parser_matcher(customer_details["Name"])
            reference_no = dict_data["PURCHASE_ORDER_160"]["ORDER_HEADER"]["ORDER_NUM"]

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
    print(f"CHECK IF IT MATCHES PO:{po_item["description"]} with XERO: {xero_item["Description"]}")
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
    try:
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
                        # pprint(f"po_item: {item} looking at Item: {db_item["Description"]}: final score = {final_score}")

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
    except Exception as e:
        print(traceback.format_exc())
        raise

def normalize_brand(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

def extract_weight_and_unit(description):
    match = re.search(r'(\d+(\.\d+)?)(?:\s*)(kg|g|lt|l|ml)', description, re.IGNORECASE)
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
