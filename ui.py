import tkinter as tk
from tkinter import messagebox, ttk
import traceback
from decimal import Decimal, InvalidOperation, getcontext
import logging
import os
import sys
import time
from contextlib import contextmanager
from database import *
from bill_generator import *

# Set up logging
log_dir = os.path.join(os.path.expanduser('~'), 'POS_Logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'pos_errors.log'),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Determine if running as a PyInstaller bundle
def resource_path(relative_path):
    """Get absolute path to resource for both dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("M/s Alif Seed Farm POS")
        self.root.geometry("1100x750")
        
        # Set decimal precision
        getcontext().prec = 6
        
        # Initialize database
        try:
            init_db()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
            logging.error("Database initialization failed", exc_info=True)
            self.root.destroy()
            return

        # Variables
        self.customer_phone = tk.StringVar()
        self.customer_name = tk.StringVar()
        self.customer_email = tk.StringVar()
        self.customer_address = tk.StringVar()
        self.discount = tk.StringVar(value="0.00")
        self.paid_amount = tk.StringVar(value="0.00")
        self.available_qty = tk.StringVar(value="Available: 0")
        self.cart = []
        self.current_product_id = None

        # Setup UI
        self.setup_style()
        self.build_ui()
        self.load_products()
        
    def to_decimal(self, value, default='0'):
        """Safely convert any value to Decimal"""
        try:
            return Decimal(str(value or default))
        except (ValueError, InvalidOperation):
            return Decimal(default)
    
    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", font=("Arial", 10))
        style.configure("TLabel", padding=5)
        style.configure("TButton", padding=5)
        style.configure("TEntry", padding=5)
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"), padding=[10, 5])
        style.configure("Stock.TLabel", foreground="green", font=("Arial", 16, "bold"))
        style.configure("Summary.TLabel", font=("Arial", 10, "bold"))
        style.map("Accent.TButton", 
                foreground=[('active', 'white'), ('!disabled', 'white')],
                background=[('active', '#45a049'), ('!disabled', '#4CAF50')])

    def build_ui(self):
        tab_control = ttk.Notebook(self.root)
        
        # Create tabs
        tab_pos = ttk.Frame(tab_control)
        tab_inventory = ttk.Frame(tab_control)
        tab_customers = ttk.Frame(tab_control)
        tab_payments = ttk.Frame(tab_control)
        
        tab_control.add(tab_pos, text='POS')
        tab_control.add(tab_inventory, text='Inventory')
        tab_control.add(tab_customers, text='Customers')
        tab_control.add(tab_payments, text='Payments')
        tab_control.pack(expand=1, fill='both')

        # Build each tab
        self.build_pos_tab(tab_pos)
        self.build_inventory_tab(tab_inventory)
        self.build_customers_tab(tab_customers)
        self.build_payments_tab(tab_payments)

    def build_pos_tab(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Panel - Customer and Products
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        # Customer Frame
        customer_frame = ttk.LabelFrame(left_frame, text="Customer Information")
        customer_frame.pack(fill="x", padx=5, pady=5)
        
       
        ttk.Label(customer_frame, text="Phone:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        phone_entry = ttk.Entry(customer_frame, textvariable=self.customer_phone, width=20)
        phone_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(customer_frame, text="Fetch", command=self.fetch_customer, width=8).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(customer_frame, text="Name:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(customer_frame, textvariable=self.customer_name, width=30).grid(row=1, column=1, columnspan=2, padx=5, pady=2)

        ttk.Label(customer_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(customer_frame, textvariable=self.customer_email, width=30).grid(row=2, column=1, columnspan=2, padx=5, pady=2)

        ttk.Label(customer_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(customer_frame, textvariable=self.customer_address, width=30).grid(row=3, column=1, columnspan=2, padx=5, pady=2)
        
        self.customer_due_display = ttk.Label(customer_frame, text="Due: ৳0.00", foreground="red")
        self.customer_due_display.grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # Product Frame
        product_frame = ttk.LabelFrame(left_frame, text="Product Selection")
        product_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(product_frame, text="Product:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.product_combo = ttk.Combobox(product_frame, state="readonly", width=25)
        self.product_combo.grid(row=0, column=1, padx=5, pady=2)
        self.product_combo.bind("<<ComboboxSelected>>", self.update_stock_display)

        ttk.Label(product_frame, textvariable=self.available_qty, style="Stock.TLabel").grid(
            row=1, column=1, sticky="w", padx=5)

        ttk.Label(product_frame, text="Qty:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.qty_entry = ttk.Entry(product_frame, width=5)
        self.qty_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        self.qty_entry.insert(0, "1")

        ttk.Button(product_frame, text="Add to Cart", command=self.add_to_cart).grid(
            row=3, column=0, columnspan=2, pady=5)

        # Right Panel - Cart and Checkout
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Cart Treeview with Scrollbar
        cart_frame = ttk.LabelFrame(right_frame, text="Shopping Cart")
        cart_frame.pack(fill="both", expand=True, padx=5, pady=5)

        tree_scroll = ttk.Scrollbar(cart_frame)
        tree_scroll.pack(side="right", fill="y")

        self.cart_tree = ttk.Treeview(cart_frame, columns=("Product", "Qty", "Price", "Total"), 
                                    show='headings', yscrollcommand=tree_scroll.set)
        
        tree_scroll.config(command=self.cart_tree.yview)

        self.cart_tree.heading("Product", text="Product")
        self.cart_tree.heading("Qty", text="Quantity")
        self.cart_tree.heading("Price", text="Unit Price")
        self.cart_tree.heading("Total", text="Total")
        
        self.cart_tree.column("Product", width=200)
        self.cart_tree.column("Qty", width=80, anchor="center")
        self.cart_tree.column("Price", width=100, anchor="e")
        self.cart_tree.column("Total", width=120, anchor="e")
        
        self.cart_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Cart controls
        cart_controls = ttk.Frame(cart_frame)
        cart_controls.pack(fill="x", padx=5, pady=5)

        ttk.Button(cart_controls, text="Remove Selected", command=self.remove_selected_item).pack(side="left", padx=2)
        ttk.Button(cart_controls, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=2)

        # Checkout Frame
        checkout_frame = ttk.LabelFrame(right_frame, text="Checkout Summary")
        checkout_frame.pack(fill="x", padx=5, pady=5)

        # Summary labels
        self.subtotal_var = tk.StringVar(value="Subtotal: ৳0.00")
        self.discount_var = tk.StringVar(value="Discount: ৳0.00")
        self.total_var = tk.StringVar(value="Total: ৳0.00")
        self.due_var = tk.StringVar(value="Due: ৳0.00")

        ttk.Label(checkout_frame, textvariable=self.subtotal_var).grid(
            row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(checkout_frame, textvariable=self.discount_var).grid(
            row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(checkout_frame, textvariable=self.total_var, style="Summary.TLabel").grid(
            row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(checkout_frame, textvariable=self.due_var).grid(
            row=3, column=0, sticky="w", padx=5, pady=2)

        # Payment controls
        payment_frame = ttk.Frame(checkout_frame)
        payment_frame.grid(row=4, column=0, sticky="ew", pady=5)
        ttk.Label(payment_frame, text="Discount:").pack(side="left", padx=5)
        ttk.Entry(payment_frame, textvariable=self.discount, width=10).pack(side="left", padx=5)
        ttk.Label(payment_frame, text="Paid:").pack(side="left", padx=5)
        ttk.Entry(payment_frame, textvariable=self.paid_amount, width=10).pack(side="left", padx=5)
        ttk.Button(checkout_frame, text="Complete Sale", command=self.complete_sale, 
                style="Accent.TButton").grid(row=5, column=0, pady=10)

    def build_inventory_tab(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add Product Form
        form_frame = ttk.LabelFrame(main_frame, text="Add/Update Product")
        form_frame.pack(fill="x", padx=5, pady=5)

        # Form variables
        self.inv_name = tk.StringVar()
        self.inv_desc = tk.StringVar()
        self.inv_buy = tk.DoubleVar()
        self.inv_sell = tk.DoubleVar()
        self.inv_qty = tk.IntVar()

        # Form fields
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.inv_name, width=30).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form_frame, text="Description:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.inv_desc, width=30).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form_frame, text="Buy Price:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.inv_buy, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(form_frame, text="Sell Price:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.inv_sell, width=15).grid(row=3, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(form_frame, text="Quantity:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.inv_qty, width=15).grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # Form buttons - PROPERLY DEFINED BUTTON FRAME
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Save Product", command=self.save_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_product_form).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="New Product", command=self.clear_product_form).pack(side="left", padx=5)

        # Product List with Search
        list_frame = ttk.LabelFrame(main_frame, text="Product Inventory")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Search bar
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self.search_products).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Show All", command=self.load_products).pack(side="left", padx=5)

        # Treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(list_frame)
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = ttk.Scrollbar(list_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        self.inventory_tree = ttk.Treeview(list_frame, 
                                        columns=("ID", "Name", "Description", "Buy", "Sell", "Stock"),
                                        show='headings',
                                        yscrollcommand=tree_scroll_y.set,
                                        xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.config(command=self.inventory_tree.yview)
        tree_scroll_x.config(command=self.inventory_tree.xview)

        # Configure columns
        self.inventory_tree.heading("ID", text="ID")
        self.inventory_tree.heading("Name", text="Name")
        self.inventory_tree.heading("Description", text="Description")
        self.inventory_tree.heading("Buy", text="Buy Price")
        self.inventory_tree.heading("Sell", text="Sell Price")
        self.inventory_tree.heading("Stock", text="In Stock")

        self.inventory_tree.column("ID", width=50, anchor="center", stretch=False)
        self.inventory_tree.column("Name", width=180, anchor="w", stretch=True)
        self.inventory_tree.column("Description", width=200, anchor="w", stretch=True)
        self.inventory_tree.column("Buy", width=100, anchor="e", stretch=False)
        self.inventory_tree.column("Sell", width=100, anchor="e", stretch=False)
        self.inventory_tree.column("Stock", width=100, anchor="center", stretch=False)


        self.inventory_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Bind double click to edit
        self.inventory_tree.bind("<Double-1>", self.edit_product)

        # Load initial data
        self.load_products()
    
    def build_customers_tab(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add Customer Form
        form_frame = ttk.LabelFrame(main_frame, text="Add/Update Customer")
        form_frame.pack(fill="x", padx=5, pady=5)

        # Form variables
        self.cust_phone = tk.StringVar()
        self.cust_name = tk.StringVar()
        self.cust_email = tk.StringVar()
        self.cust_address = tk.StringVar()

        # Form fields
        ttk.Label(form_frame, text="Phone:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.cust_phone, width=20).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form_frame, text="Name:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.cust_name, width=30).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.cust_email, width=30).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.cust_address, width=30).grid(row=3, column=1, padx=5, pady=2)

        # Form buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Save Customer", command=self.save_customer).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_customer_form).pack(side="left", padx=5)

        # Customer List with Search
        list_frame = ttk.LabelFrame(main_frame, text="Customer Directory")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Search bar
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=5)
        self.cust_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.cust_search_var, width=30).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self.search_customers).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Show All", command=self.load_customers).pack(side="left", padx=5)

        # Treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(list_frame)
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = ttk.Scrollbar(list_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        self.customers_tree = ttk.Treeview(list_frame, 
                                         columns=("Phone", "Name", "Due", "Email", "Address"),
                                         show='headings',
                                         yscrollcommand=tree_scroll_y.set,
                                         xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.config(command=self.customers_tree.yview)
        tree_scroll_x.config(command=self.customers_tree.xview)

        # Configure columns
        self.customers_tree.heading("Phone", text="Phone")
        self.customers_tree.heading("Name", text="Name")
        self.customers_tree.heading("Due", text="Due") # ✅ new
        self.customers_tree.heading("Email", text="Email")
        self.customers_tree.heading("Address", text="Address")

        self.customers_tree.column("Phone", width=120)
        self.customers_tree.column("Name", width=150)
        self.customers_tree.column("Due", width=100, anchor="center")  # ✅ new
        self.customers_tree.column("Email", width=150)
        self.customers_tree.column("Address", width=200)

        self.customers_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Bind double click to edit
        self.customers_tree.bind("<Double-1>", self.edit_customer)

        # Load initial data
        self.load_customers()

    def build_payments_tab(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Payment Form
        form_frame = ttk.LabelFrame(main_frame, text="Record Payment")
        form_frame.pack(fill="x", padx=5, pady=5)

        # Form variables
        self.pay_phone = tk.StringVar()
        self.pay_amount = tk.DoubleVar()
        self.pay_balance = tk.StringVar(value="Current Balance: ৳0.00")

        # Form fields
        ttk.Label(form_frame, text="Customer Phone:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.pay_phone, width=20).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(form_frame, text="Find", command=self.find_customer_balance).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(form_frame, textvariable=self.pay_balance).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        ttk.Label(form_frame, text="Amount:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(form_frame, textvariable=self.pay_amount, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Form buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5)

        ttk.Button(btn_frame, text="Record Payment", command=self.record_payment, 
                  style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_payment_form).pack(side="left", padx=5)

        # Payment History
        history_frame = ttk.LabelFrame(main_frame, text="Payment History")
        history_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(history_frame)
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = ttk.Scrollbar(history_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        self.payments_tree = ttk.Treeview(history_frame, 
                                        columns=("ID", "Date", "Customer", "Amount"),
                                        show='headings',
                                        yscrollcommand=tree_scroll_y.set,
                                        xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.config(command=self.payments_tree.yview)
        tree_scroll_x.config(command=self.payments_tree.xview)

        # Configure columns
        self.payments_tree.heading("ID", text="ID")
        self.payments_tree.heading("Date", text="Date")
        self.payments_tree.heading("Customer", text="Customer")
        self.payments_tree.heading("Amount", text="Amount")

        self.payments_tree.column("ID", width=50, anchor="center")
        self.payments_tree.column("Date", width=120)
        self.payments_tree.column("Customer", width=200)
        self.payments_tree.column("Amount", width=100, anchor="e")

        self.payments_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Load initial data
        self.load_payment_history()

    # ====================
    # Business Logic Methods
    # ====================

    def update_stock_display(self, event=None):
        """Update the available quantity label when product is selected"""
        product_name = self.product_combo.get()
        if not product_name:
            self.current_product_id = None
            self.available_qty.set("Available: 0")
            return

        try:
            product = get_product_by_name(product_name)
            if product:
                self.current_product_id = product[0]
                self.available_qty.set(f"Available: {product[5]}")
            else:
                self.current_product_id = None
                self.available_qty.set("Available: 0")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check stock: {e}")
            logging.error("Error updating stock display", exc_info=True)

    def load_products(self):
        """Load products into combobox and inventory tree"""
        try:
            products = get_all_products()
            product_names = [product[1] for product in products]
            self.product_combo['values'] = product_names
            
            # Clear existing rows
            for row in self.inventory_tree.get_children():
                self.inventory_tree.delete(row)

            # Insert directly since fields match Treeview order
            for product in products:
                self.inventory_tree.insert("", "end", values=product)

            if product_names:
                self.product_combo.current(0)
                self.update_stock_display()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {e}")
            logging.error("Error loading products", exc_info=True)


    def search_products(self):
        """Search products by name"""
        query = self.search_var.get()
        if not query:
            self.load_products()
            return
            
        try:
            results = search_products(query)
            
            for row in self.inventory_tree.get_children():
                self.inventory_tree.delete(row)
                
            for product in results:
                self.inventory_tree.insert("", "end", values=product)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search products: {e}")
            logging.error("Error searching products", exc_info=True)

    def edit_product(self, event):
        """Load selected product into form for editing"""
        selected = self.inventory_tree.selection()
        if not selected:
            return
            
        try:
            item = self.inventory_tree.item(selected[0])
            product = item['values']
            
            # Explicitly set the current product ID
            self.current_product_id = product[0]  
            self.inv_name.set(product[1])
            self.inv_desc.set(product[2])
            self.inv_buy.set(product[3])
            self.inv_sell.set(product[4])
            self.inv_qty.set(product[5])
            
            # Update the combo box to show the edited product
            self.product_combo.set(product[1])
            self.update_stock_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load product: {e}")
            logging.error("Error editing product", exc_info=True)

    def save_product(self):
        """Save or update product"""
        if not self.validate_product_form():
            return
            
        try:
            product_data = (
                self.inv_name.get(),
                self.inv_desc.get(),
                float(self.inv_buy.get()),
                float(self.inv_sell.get()),
                int(self.inv_qty.get())
            )
            
            if self.current_product_id is not None:  # Explicit check for None
                # Update existing product
                update_product(self.current_product_id, *product_data)
                messagebox.showinfo("Success", "Product updated successfully!")
            else:
                # Add new product
                add_product(*product_data)
                messagebox.showinfo("Success", "Product added successfully!")
            
            self.clear_product_form()
            self.load_products()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save product: {e}")
            logging.error("Error saving product", exc_info=True)

    def validate_product_form(self):
        """Validate product form fields"""
        if not self.inv_name.get():
            messagebox.showerror("Error", "Product name is required")
            return False
            
        try:
            float(self.inv_buy.get())
            float(self.inv_sell.get())
            int(self.inv_qty.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return False
            
        return True

    def clear_product_form(self):
        """Clear product form and reset product ID"""
        self.current_product_id = None  # Explicitly set to None
        self.inv_name.set("")
        self.inv_desc.set("")
        self.inv_buy.set(0.0)
        self.inv_sell.set(0.0)
        self.inv_qty.set(0)
        self.product_combo.set("")  # Clear the combo box selection

    def load_customers(self):
        """Load customers with due amounts into treeview"""
        try:
            customers = get_all_customers()
            
            # Clear the tree first
            for row in self.customers_tree.get_children():
                self.customers_tree.delete(row)
            
            for customer in customers:
                phone = customer[0]
                name = customer[1]
                email = customer[2]
                address = customer[3]

                # Get and format due
                due = get_customer_due(phone)
                due_display = f"৳{due:.2f}"

                self.customers_tree.insert("", "end", values=(
                    phone, name, due_display, email, address
                ))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load customers: {e}")
            logging.error("Error loading customers", exc_info=True)

    def search_customers(self):
        """Search customers by name or phone"""
        query = self.cust_search_var.get()
        if not query:
            self.load_customers()
            return

        try:
            results = search_customers(query)
            self.customers_tree.delete(*self.customers_tree.get_children())

            for customer in results:
                phone = customer[0]
                name = customer[1]
                due = get_customer_due(phone)
                due_display = f"৳{due:.2f}"
                email = customer[2]
                address = customer[3]

                

                tags = ("overdue",) if due > 0 else ()

                self.customers_tree.insert(
                    "", "end",
                    values=(phone, name, due_display,  email, address),
                    tags=tags
                )

            # Style only overdue ones
            self.customers_tree.tag_configure("overdue", foreground="#cc0000", font=("TkDefaultFont", 9, "bold"))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to search customers: {e}")
            logging.error("Error searching customers", exc_info=True)

    def edit_customer(self, event):
        """Load selected customer into form for editing"""
        selected = self.customers_tree.selection()
        if not selected:
            return

        try:
            item = self.customers_tree.item(selected[0])
            customer = item['values']

            self.cust_phone.set(customer[0])         # Phone
            self.cust_name.set(customer[2])          # Name (index 2)
            self.cust_email.set(customer[3])         # Email
            self.cust_address.set(customer[4])       # Address
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load customer: {e}")
            logging.error("Error editing customer", exc_info=True)

    def save_customer(self):
        """Save or update customer"""
        if not self.validate_customer_form():
            return
            
        try:
            add_customer(
                self.cust_phone.get(),
                self.cust_name.get(),
                self.cust_email.get(),
                self.cust_address.get()
            )
            messagebox.showinfo("Success", "Customer saved successfully!")
            self.clear_customer_form()
            self.load_customers()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save customer: {e}")
            logging.error("Error saving customer", exc_info=True)

    def validate_customer_form(self):
        """Validate customer form fields"""
        if not self.cust_phone.get():
            messagebox.showerror("Error", "Phone number is required")
            return False
            
        if not self.cust_name.get():
            messagebox.showerror("Error", "Customer name is required")
            return False
            
        return True

    def clear_customer_form(self):
        """Clear customer form"""
        self.cust_phone.set("")
        self.cust_name.set("")
        self.cust_email.set("")
        self.cust_address.set("")

    def find_customer_balance(self):
        """Find customer and display current balance"""
        phone = self.pay_phone.get()
        if not phone:
            messagebox.showerror("Error", "Please enter phone number")
            return
            
        try:
            customer = get_customer(phone)
            if not customer:
                messagebox.showerror("Error", "Customer not found")
                return
                
            balance = get_customer_due(phone)
            self.pay_balance.set(f"Current Balance: ৳{balance:.2f}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get balance: {e}")
            logging.error("Error finding customer balance", exc_info=True)

    def record_payment(self):
        """Record customer payment"""
        phone = self.pay_phone.get()
        amount = self.pay_amount.get()
        
        if not phone:
            messagebox.showerror("Error", "Customer phone is required")
            return
            
        if amount <= 0:
            messagebox.showerror("Error", "Amount must be positive")
            return
            
        try:
            record_payment(phone, amount)
            messagebox.showinfo("Success", f"Payment of ৳{amount:.2f} recorded")
            self.clear_payment_form()
            self.load_payment_history()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {e}")
            logging.error("Error recording payment", exc_info=True)

    def clear_payment_form(self):
        """Clear payment form"""
        self.pay_phone.set("")
        self.pay_amount.set(0.0)
        self.pay_balance.set("Current Balance: ৳0.00")

    def load_payment_history(self):
        """Load payment history"""
        try:
            payments = get_payment_history()
            
            for row in self.payments_tree.get_children():
                self.payments_tree.delete(row)
                
            for payment in payments:
                self.payments_tree.insert("", "end", values=payment)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load payment history: {e}")
            logging.error("Error loading payment history", exc_info=True)

    def fetch_customer(self):
        """Fetch customer details by phone"""
        phone = self.customer_phone.get()
        if not phone:
            messagebox.showwarning("Warning", "Please enter phone number")
            return

        try:
            customer = get_customer(phone)
            if customer:
                self.customer_name.set(customer[1])
                self.customer_email.set(customer[2] if len(customer) > 2 else "")
                self.customer_address.set(customer[3] if len(customer) > 3 else "")
            else:
                self.customer_name.set("")
                self.customer_email.set("")
                self.customer_address.set("")
                messagebox.showinfo("Info", "New customer. Please fill in details.")

            # 💡 Show due info here
            try:
                due = get_customer_due(phone)
                self.customer_due_display.config(text=f"Due: ৳{due:.2f}")
            except Exception as e:
                self.customer_due_display.config(text="Due: ৳0.00")
                logging.error("Failed to fetch customer due", exc_info=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch customer: {e}")
            logging.error("Error fetching customer", exc_info=True)

    def add_to_cart(self):
        """Add selected product to cart with validation and proper type conversion"""
        name = self.product_combo.get()
        if not name:
            messagebox.showerror("Error", "Please select a product")
            return

        try:
            # Convert quantity to integer
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError("Quantity must be positive")

            # Get product info and convert price to Decimal
            product = get_product_by_name(name)
            if not product:
                raise ValueError("Product not found")

            available = product[5]  # Stock quantity
            if qty > available:
                raise ValueError(f"Only {available} units available in stock")

            price = self.to_decimal(product[4])  # Convert sell price to Decimal

            # Add to cart (store price as float for compatibility)
            self.cart.append((name, qty, float(price)))
            
            # Update UI
            self.update_cart_view()
            self.update_summary()
            self.qty_entry.delete(0, tk.END)
            self.qty_entry.insert(0, "1")
            self.update_stock_display()

        except ValueError as ve:
            messagebox.showerror("Input Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add to cart: {str(e)}")
            logging.error("Error in add_to_cart", exc_info=True)

    def update_cart_view(self):
        """Update the cart treeview"""
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        
        for item in self.cart:
            name, qty, price = item
            total = qty * price
            self.cart_tree.insert("", "end", values=(name, qty, f"{price:.2f}", f"{total:.2f}"))

    def update_summary(self):
        """Update the checkout summary information with proper decimal handling"""
        try:
            # Convert all cart items to Decimal for calculation
            subtotal = Decimal('0')
            for item in self.cart:
                name, qty, price = item
                subtotal += self.to_decimal(qty) * self.to_decimal(price)
            
            # Convert discount and paid amount to Decimal
            discount = self.to_decimal(self.discount.get())
            paid = self.to_decimal(self.paid_amount.get())
            
            # Calculate totals
            total = subtotal - discount
            due = total - paid

            # Update display variables (convert to float for display only)
            self.subtotal_var.set(f"Subtotal: ৳{float(subtotal):.2f}")
            self.discount_var.set(f"Discount: ৳{float(discount):.2f}")
            self.total_var.set(f"Total: ৳{float(total):.2f}")
            self.due_var.set(f"Due: ৳{float(due):.2f}")
            
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Failed to update totals: {str(e)}")
            logging.error("Error in update_summary", exc_info=True)

    def remove_selected_item(self):
        """Remove selected item from cart"""
        selected = self.cart_tree.selection()
        if not selected:
            return
            
        try:
            item = self.cart_tree.item(selected[0])
            product_name = item['values'][0]
            
            for i, (name, qty, price) in enumerate(self.cart):
                if name == product_name:
                    del self.cart[i]
                    break
                    
            self.update_cart_view()
            self.update_summary()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove item: {e}")
            logging.error("Error removing cart item", exc_info=True)

    def clear_cart(self):
        """Clear all items from cart"""
        self.cart = []
        self.update_cart_view()
        self.update_summary()
        self.discount.set(0.0)
        self.paid_amount.set(0.0)
   
    def complete_sale(self):
        """Complete sale with robust decimal handling and error recovery"""
        try:
            # Validate customer info
            phone = self.customer_phone.get().strip()
            name = self.customer_name.get().strip()
            
            if not phone or not name:
                raise ValueError("Customer information is required")

            if not self.cart:
                raise ValueError("Cart is empty")

            # Convert all values to Decimal
            discount = self.to_decimal(self.discount.get())
            paid = self.to_decimal(self.paid_amount.get())
            previous_due = self.to_decimal(get_customer_due(phone))

            # Calculate totals using Decimal
            subtotal = Decimal('0')
            for item in self.cart:
                name, qty, price = item
                subtotal += self.to_decimal(qty) * self.to_decimal(price)
            
            total = subtotal - discount
            new_due = (previous_due + total) - paid

            # Validate amounts
            if discount < Decimal('0'):
                raise ValueError("Discount cannot be negative")
            if discount > subtotal:
                raise ValueError("Discount cannot exceed subtotal")
            if paid > (total + previous_due):
                raise ValueError("Paid amount exceeds total due")

            # Confirm sale
            confirm_msg = (
                f"Subtotal: ৳{float(subtotal):.2f}\n"
                f"Discount: ৳{float(discount):.2f}\n"
                f"Total: ৳{float(total):.2f}\n"
                f"Previous Due: ৳{float(previous_due):.2f}\n"
                f"Paid: ৳{float(paid):.2f}\n"
                f"New Due: ৳{float(new_due):.2f}\n\n"
                f"Complete the sale?"
            )
            
            if not messagebox.askyesno("Confirm Sale", confirm_msg):
                return

            # Prepare cart items for database (convert to appropriate types)
            cart_items = []
            for item in self.cart:
                name, qty, price = item
                cart_items.append((name, int(qty), float(price)))

            # Record sale (converts Decimal to float for database)
            sale_id = record_sale(
                phone,
                cart_items,
                float(discount),
                float(paid)
            )

            # Generate PDF receipt
            pdf_gen = PDFGenerator()
            pdf_gen.generate_pdf_bill(
                sale_id=sale_id,
                customer_name=name,
                customer_phone=phone,
                customer_email=self.customer_email.get().strip(),
                items=self.cart,
                subtotal=float(subtotal),
                discount=float(discount),
                total=float(total),
                previous_due=float(previous_due),
                amount_paid=float(paid),
                new_due=float(new_due)
            )

            # Update UI and clear cart
            messagebox.showinfo("Success", f"Sale #{sale_id} completed. New due: ৳{float(new_due):.2f}")
            self.customer_due_display.config(text=f"Due: ৳{float(new_due):.2f}")
            self.clear_cart()
            self.load_products()
            self.load_payment_history()

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except Exception as e:
            logging.critical("Sale failed", exc_info=True)
            messagebox.showerror("Sale Error", f"Failed to complete sale: {str(e)}")
if __name__ == '__main__':
    root = tk.Tk()
    try:
        app = POSApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")
        logging.critical("Application crash", exc_info=True)
