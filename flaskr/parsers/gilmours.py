
import re
import xmltodict
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
    else:
        return po_item["quantity"] # if the item description does not contain the weight and unit
def process_pdf(pdf_path): # Rename since we are extending to Excel and XML
    print("Gilmours PO Detected")

    with open(pdf_path) as xml_file:
        dict_data = xmltodict.parse(xml_file.read())

        line_items = dict_data["PURCHASE_ORDER_160"]["LINES"]["ORDER_LINE"]

        # Normalize to a list if it's a single dict
        if isinstance(line_items, dict):
            line_items = [line_items]

        result = []
        for line_item in line_items:
            result.append({
                "description": line_item["PRODUCT_DESC"],
                "quantity": line_item["QTY_ORDERED"],
                "uom": "N/A",
                "unit_price": line_item["PRICING_DETAIL"]["PRICE"],
                "total_price": line_item["PRICING_DETAIL"]["LINE_PRICE"],
            })
        print(result)
        return result