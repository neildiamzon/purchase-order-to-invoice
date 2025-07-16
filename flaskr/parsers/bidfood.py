from pprint import pprint

import pdfplumber
import re
import tabula
import pandas as pd

def adjust_quantity(po_item, xero_item):

    # for items that has ' x 12 ' or ' x 4 ' in the description
    match = re.search(r"x\s*(\d+)", xero_item["Description"], re.IGNORECASE)
    if match:
        return po_item["quantity"] # default - description contains units

    match = re.search(r'(\d+(\.\d+)?)(kg|g|l|ml)', xero_item["Description"], re.IGNORECASE)

    if match:
        weight = float(match.group(1))
        unit = match.group(3).lower()

        if (unit == 'kg' or unit == 'l')  and (weight >= 10 or weight == 2):
            return po_item["quantity"]  # default - sold by box / pail
        else:
            return float(po_item["quantity"]) * 4 # multiply by 4 because 1 CTN is 4 units

def process_pdf(pdf_path):
    # print("Bidfood PO Detected")

    with pdfplumber.open(pdf_path) as pdf:
        line_items = []
        page = pdf.pages[0]
        lines = page.extract_text().splitlines()
        pattern = re.compile(r"^(\d+)\s+(\d+)\s+(.*?)\s+(\d+\.?)\s+(\w+)\s+([\d.]+)\s+([\d.,]+)$")

        start = False
        for line in lines:
            if "Item Supplier Code Product Description Brand Pack Qty UoM Unit Price Disc% Order Value" in line:
                start = True
                continue
            if "TOTAL VALUE" in line:
                break
            if start:
                match = pattern.match(line)
                if match:
                    item_code, supplier_code, description, qty, uom, unit_price, order_value = match.groups()
                    line_items.append({
                        "description": description,
                        "quantity": qty.rstrip('.'),
                        "uom": uom,
                        "unit_price": unit_price.replace(",",""),
                        "total_price": order_value.replace(",",""),
                    })
        print(line_items)

    return line_items


        #
        #
        # merged_items = []#merge_continuation_lines(line_items)
        # total_amount = 0
        # json_items = []
        # for item in merged_items:
        #     if len(item) == 5:
        #         json_items.append({
        #             "description": item[0],
        #             "misc": item[1],
        #             "quantity": item[2],
        #             "unit_price": item[3].replace(",",""),
        #             "total_price": item[4].replace(",",""),
        #         })
        #         total_amount += float(item[4].replace(",", ""))
        #     else:
        #         print(f"Skipping malformed line: {item}")  # Optional: handle/flag errors
        # return json_items