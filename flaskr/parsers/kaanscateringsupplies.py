import pdfplumber
import tabula
import re
import pandas as pd

def adjust_quantity(po_item, xero_item):

    # for items that has ' x 12 ' or ' x 4 ' in the description
    match = re.search(r"x\s*(\d+)", xero_item["Description"], re.IGNORECASE)
    if match:
        return po_item["quantity"] # default - description contains units


    match = re.search(r'(\d+(\.\d+)?)(?:\s*)(kg|g|l|ml)\b', xero_item["Description"], re.IGNORECASE)

    if match:
        weight = float(match.group(1))
        unit = match.group(3).lower()

        if (unit == 'kg' or unit == 'l')  and (weight >= 10 or weight == 2):
            return po_item["quantity"]  # default - sold by box / pail
        else:
            return float(po_item["quantity"]) * 4 # multiply by 4 because 1 CTN is 4 units

def process_pdf(pdf_path):
    def parse_flat_item_line(line):
        # Extract all float/number values (can include commas)
        numbers = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", line)

        if len(numbers) < 3:
            return None  # not a valid item line

        quantity = numbers[-3]
        unit_price = numbers[-2]
        total_price = numbers[-1]

        # Try to extract unit (comes after quantity)
        match = re.search(rf"{re.escape(quantity)}\s+([A-Z]+)", line)
        unit = match.group(1) if match else ""

        # Get the description (everything before quantity)
        qty_index = line.find(quantity)
        description = line[:qty_index].strip()

        return {
            "description": description,
            "quantity": quantity,
            "unit": unit,
            "unit_price": str(unit_price).replace(",",""),
            "total_price": str(total_price).replace(",","")
        }

    def is_price_line(line):
        # Look for 3 float-like numbers (e.g., "36.00 TUB 107.60 3,873.60")
        return len(re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", line)) >= 3

    def clean_description(text):
        words = text.split()

        words = special_handling_item(words)
        return " ".join(words[2:]) if len(words) > 2 else text

    def special_handling_item(words):
        for idx, word in enumerate(words):
            if word == "MKPKC20":
                words[idx + 1] += " 20kg"
            if word == "FRHORG38":
                words[idx + 1] += " CAYENNE"
        return words

    line_items = []
    buffer = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text().splitlines()

        start = False
        for line in text:
            if "No. Vendor Item No." in line:
                start = True
                continue
            if "Total NZD Excl. GST" in line:
                break
            if start:
                buffer.append(line)

                if is_price_line(line):
                    item = " ".join(buffer)
                    if item:
                        cleaned_line = clean_description(item)
                        line_items.append(parse_flat_item_line(cleaned_line))
                else:
                    item = " ".join(buffer)

                    line_items[-1]["description"] = item + " " + line_items[-1]["description"]
                buffer = []
    # print(line_items)
    return line_items
