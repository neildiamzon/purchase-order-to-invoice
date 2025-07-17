
# 🧾 Purchase Order to Invoice Converter

A lightweight Flask web application that converts purchase orders (PDFs) into structured invoice documents. Built to streamline business workflows, especially for manual or semi-automated B2B transactions.

---

## 🚀 Features

* 🔎 Automatically extracts and parses text from scanned or digital POs
* 🧠 Uses intelligent pattern matching to detect item names, quantities, and prices
* 🧾 Generates invoice data for manual review or export

---

## 🧰 Tech Stack

* **Backend:** Flask (Python 3)
* **PDF Parsing:** pdfplumber
* **Frontend:** HTML templates
* **Logging:** Built-in Flask logger
* **Threading:** Background scanning via threading module

---

## 📦 Installation

### Prerequisites

* Python 3.9+
* pip
* Docker
* Windows

### Clone & Set Up

```bash
git clone https://github.com/neildiamzon/purchase-order-to-invoice.git
cd purchase-order-to-invoice

docker build --no-cache -t wf-automation-app .
docker run -p 5000:5000 -v C:/WatchPDFs:/WatchPDFs wf-automation-app
```

---


Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## 🔄 How It Works

1. Upon start up, this application creates a directory C:/WatchPDfs if not existing.
2. The app polls this folder for PDFs (in a separate thread)
3. PDFs are processed one at a time.
4. There are multiple parsers for each customer/distributor, the app scans the PDF to check which parser it goes.
5. Once the app scans for all line items, the data will go to a centralized Xero Inventory items matcher to match PO items with Xero Items.
6. Once items are matched with Xero items, the app will create an invoice body containing the reference, customer details, line items and total amount (incl. GST)
7. The app will send a post request to a Xero API to create an invoice (in draft).


## 🙋‍♂️ Author
🔗 [github.com/neildiamzon](https://github.com/neildiamzon)
---
