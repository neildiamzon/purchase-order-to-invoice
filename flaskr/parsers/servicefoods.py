import pdfplumber
import re

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
    # print("Service Foods PO Detected")

    with pdfplumber.open(pdf_path) as pdf:
        line_items = []
        page = pdf.pages[0]
        lines = page.extract_text().splitlines()
        date_patterns = [
            r'\d{1,2} [A-Za-z]{3,9} \d{4}',  # e.g. 29 May 2025
            r'\d{1,2}/\d{1,2}/\d{4}',  # e.g. 04/06/2025
        ]
        gst_pattern = r'GST:\s\d{2,}-\d{3,}-\d{3,}'

        def contains_dates(line, count=2):
            matches = 0
            for pattern in date_patterns:
                found = re.findall(pattern, line)
                matches += len(found)
            return matches >= count

        def process_line(line):
            match = re.match(r'^(.+?\b(?:DRY|CHIL))\s+(.*)$', line)
            if not match:
                return [line]  # fallback: return whole line as one part

            desc_part = match.group(1)  # first index
            rest_part = match.group(2).split()  # split remaining by space
            return [desc_part] + rest_part

        def is_note_line(line):
            # print(line)
            text = line[0].strip() if line else ""
            return (
                    len(line) == 1 and
                    (
                            text.startswith("*") or  # Match lines that begin with any number of asterisks
                            text.endswith("*") or  # ...or end with them (even just 1)
                            "please note" in text.lower() or  # Case-insensitive match
                            "important" in text.lower()  or # Add common flags
                            "NZD" in text
                    )
            )

        def clean_description(text):
            words = text.split()
            return " ".join(words[2:]) if len(words) > 2 else text

        def merge_continuation_lines(split_lines):
            merged = []
            for line in split_lines:
                if is_note_line(line):
                    continue  # skip non-item notes
                if len(line) == 1 and merged:
                    merged[-1][0] += f" {line[0]}"
                else:
                    merged.append(line)
            return merged

        start_scanning = False
        for line in lines:
            if re.search(gst_pattern, line):
                start_scanning = False  # details are done here supposedly
            if start_scanning:
                line_items.append(process_line(line))
            elif contains_dates(line):
                start_scanning = True

        merged_items = merge_continuation_lines(line_items)
        total_amount = 0
        json_items = []
        for item in merged_items:
            if len(item) == 5:
                json_items.append({
                    "description": clean_description(item[0]),
                    "misc": item[1],
                    "quantity": item[2],
                    "unit_price": item[3].replace(",",""),
                    "total_price": item[4].replace(",",""),
                })
                total_amount += float(item[4].replace(",", ""))
            else:
                print(f"Skipping malformed line: {item}")  # Optional: handle/flag errors
        return json_items