# Pos-system-Inpython-gui
Pos-system-Inpython-gui
POS System in Python with GUI
=============================

A complete Point-of-Sale (POS) system developed in Python using Tkinter for the graphical user interface and SQLite for the local database. Designed for a seed wholesaler and retailer business, it supports both retail and wholesale operations, including credit handling, product inventory, customer management, billing, and PDF invoice generation.

Overview
--------

This POS system is tailored for businesses that sell products both at retail and wholesale levels. It offers a user-friendly desktop interface for shopkeepers to:

- Add/manage products and customers
- Handle retail and credit sales
- Apply discounts
- Track customer dues
- Generate and print PDF invoices
- Manage inventory quantities

The system is built as a modular Python application with clean separation between the UI, database operations, billing logic, and main program flow.

Features
--------

- Tkinter-based desktop GUI
- SQLite-based local database
- Customer management by phone number
- Product inventory with quantity tracking
- Wholesale credit sale support
- Discounts on individual sales
- Due tracking and payment recording
- Auto-generated and printed PDF bills
- Sales report functionality

Project Structure
-----------------

main.py              # Entry point of the POS system  
database.py          # SQLite database logic and setup  
ui.py                # Tkinter GUI definitions  
bill_generator.py    # PDF invoice generation  
assets/              # Company logos or assets (optional)  
README.txt           # Project documentation  

Setup Instructions
------------------

**Prerequisites**

- Python 3.8 or higher
- 'reportlab' library for PDF generation

**Install Required Packages**

    pip install reportlab

**Run the Application**

    python build.py

    run the gui In /dist/ui.pkg

Example Use Cases
-----------------

- Retail sale to a walk-in customer
- Credit sale to a known wholesale customer (with due tracking)
- Recording due payments later
- Monitoring product stock quantities
- Generating and printing PDF bills automatically

Company Details
---------------

M/s Alif Seed Farm  
Sayed Market, Highcourtmot,  
Dhaka - Khulna Hwy, Jessore 7400  
Email: alifseedfarm@outlook.com  
Phone: +8801712087445, +8801303621895

License
-------

This project is open source and available under the MIT License

Contributing
------------

Pull requests and suggestions are welcome! If you find a bug or want to request a feature, please open an issue.
