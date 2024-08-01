# Copyright (c) 2024, Nabeel Saleem and contributors
# For license information, please see license.txt
import requests
import frappe
from frappe import _
from frappe.utils import flt, nowdate, add_days
from frappe.model.document import Document

class WooCommerceSettings(Document):
	
	@frappe.whitelist()
	def fetch_woocommerce_orders(self):
		url = f"{self.woo_site_url}/{self.order_id}" if(self.order_id) else self.woo_site_url
		response = requests.get(url, auth=(self.consumer_key, self.consumer_secret))
		if response.status_code == 200:
			orders = response.json()
			if(self.order_id):
				for order in [orders]:
					self.create_order(order)
			else:
				for order in orders:
					self.create_order(order)
		else:
			frappe.throw(_("Failed to fetch WooCommerce orders. Please check your API credentials and URL."))


	def create_order(self, order: dict):
		customer = create_update_customer(order)
		# woocommerce order details
		order_id = order["id"]
		order_date = order.get('date_created')

		"""Create a sales order based on the order data."""
		sales_order = frappe.new_doc("Sales Order")
		sales_order.customer = customer.name
		sales_order.company = self.company
		sales_order.po_no = order_id

		created_date = order.get("date_created")
		sales_order.transaction_date = created_date
		sales_order.delivery_date = frappe.utils.add_days(
			created_date, 7
		)

		add_items_to_sales_order(order, sales_order)

		sales_order.flags.ignore_mandatory = True
		sales_order.insert()
		# sales_order.submit()

def add_items_to_sales_order(order: dict, sales_order: dict):
	"""Set the items in the sales order with taxes based on the order data."""
	line_items = order.get('line_items', [])
	for line_item in line_items:
		item = get_item(line_item)
		sales_order.append(
			"items",
			{
				"item_code": item.name,
				"item_name": item.item_name,
				"description": item.description,
				"delivery_date": sales_order.delivery_date,
				"uom": get_uom(line_item.get("sku"), None),
				"qty": line_item.get("quantity"),
				"rate": line_item.get("price"),
			},
		)

		# if ordered_items_tax := flt(line_item.get("total_tax")):
		# 	add_tax_details(
		# 		sales_order, ordered_items_tax, "Item Tax", setup.tax_account
		# 	)

    # add_tax_details(
    #     sales_order,
    #     flt(order.get("shipping_tax")),
    #     "Shipping Tax",
    #     setup.shipping_tax_account,
    # )
    # add_tax_details(
    #     sales_order,
    #     flt(order.get("shipping_total")),
    #     "Shipping Total",
    #     setup.shipping_tax_account,
    # )

def get_item(item_data: dict) -> dict:
    """Get item document or create it if it does not exist."""
    item_code = item_data["name"]
    if frappe.db.exists("Item", item_code):
        return frappe.db.get_values(
            "Item", item_code, ["name", "item_name", "description"], as_dict=True
        )[0]

    return create_item(item_data)

def create_item(item_data: dict):
	"""Create an item based on the item data."""
	item = frappe.new_doc("Item")
	item.item_code = item_data["name"]
	item.item_name = item_data["name"]
	item.custom_product_id = item_data["product_id"]
	item.stock_uom = get_uom(item_data.get("sku"), None)
	item.item_group = "WooCommerce Products"
	item.image = (item_data.get("image") or {}).get("src")
	item.flags.ignore_mandatory = True
	item.save()

	return item

def get_uom(sku: str | None, default_uom: str):
    """Get the SKU from WooCommerce or the default UOM for the item."""
    if sku and not frappe.db.exists("UOM", sku):
        frappe.get_doc({"doctype": "UOM", "uom_name": sku}).save()

    return sku or (default_uom or "Nos")


def add_tax_details(sales_order, price, desc, tax_account_head):
    if not price:
        return

    sales_order.append(
        "taxes",
        {
            "charge_type": "Actual",
            "account_head": tax_account_head,
            "tax_amount": price,
            "description": desc,
        },
    )

def create_update_customer(order_data: dict):
	"""Create or update a customer based on the order data."""
	billing_data = order_data.get("billing")
	customer_id = order_data.get("customer_id")
	customer_name = billing_data.get("first_name") + " " + billing_data.get("last_name")

	# Customer could have been created manually which may differ in naming
	# always check woocomm_customer_id
	customer = frappe.db.get_value("Customer", {"custom_woocommerce_customer_id": customer_id}, "name")
	if(customer): 
		customer = frappe.get_doc("Customer", customer)
	else:
		email = order_data.get('billing', {}).get('email')
		if(frappe.db.exists("Customer", email)):
			customer = frappe.get_doc("Customer", email)
		else:
			customer = frappe.new_doc("Customer")
			customer.name = customer_id
			customer.customer_name = customer_name
			customer.custom_woocommerce_customer_id = customer_id
			customer.flags.ignore_mandatory = True
			customer.save()

	# Create address/contact if does not exist
	create_address(billing_data, customer, "Billing")
	create_address(order_data.get("shipping"), customer, "Shipping")
	create_contact(billing_data, customer)

	return customer

def create_address(raw_data: dict, customer: dict, address_type: str):
    """Create an address for the customer if it does not exist."""
    if frappe.db.exists(
        "Address",
        {
            "pincode": raw_data.get("postcode"),
            "address_line1": raw_data.get("address_1", "Not Provided"),
            "custom_woocommerce_customer_id": customer.custom_woocommerce_customer_id,
            "address_type": address_type,
        },
    ):
        return

    address = frappe.new_doc("Address")
    address.address_title = customer.get("customer_name")
    address.address_line1 = raw_data.get("address_1", "Not Provided")
    address.address_line2 = raw_data.get("address_2")
    address.city = raw_data.get("city", "Not Provided")
    address.custom_woocommerce_customer_id = customer.custom_woocommerce_customer_id
    address.address_type = address_type
    address.state = raw_data.get("state")
    address.pincode = raw_data.get("postcode")
    address.phone = raw_data.get("phone")
    address.email_id = raw_data.get("email")

    if country := raw_data.get("country"):
        address.country = frappe.db.get_value("Country", {"code": country.lower()})
    else:
        address.country = frappe.get_system_settings("country")

    address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
    address.flags.ignore_mandatory = True
    address.save()

def create_contact(data: dict, customer: str):
	email = data.get("email")
	phone = data.get("phone")
	if not email and not phone:
		return

	if frappe.db.exists(
		"Contact",
		{
			"email_id": email,
			"custom_woocommerce_customer_id": customer.custom_woocommerce_customer_id,
		},
	):
		return

	contact = frappe.new_doc("Contact")
	contact.first_name = data.get("first_name")
	contact.last_name = data.get("last_name")
	contact.email_id = email
	contact.custom_woocommerce_customer_id = customer.custom_woocommerce_customer_id
	contact.is_primary_contact = 1
	contact.is_billing_contact = 1

	if phone:
		
		phone_no = ""
		if("/" in phone):
			phone_no = str(phone).strip().split("/")
			no_1 = phone_no[0]
			no_2 = phone_no[1]
			contact.add_phone(no_1, is_primary_mobile_no=1, is_primary_phone=1)
			contact.add_phone(no_2, is_primary_mobile_no=0, is_primary_phone=0)
		else:
			contact.add_phone(phone, is_primary_mobile_no=1, is_primary_phone=1)

	if email:
		contact.add_email(email, is_primary=1)

	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.flags.ignore_mandatory = True
	contact.save()




""" 
def create_sales_order(order):
	# customer_name = order.get('billing', {}).get('first_name') + " " + order.get('billing', {}).get('last_name')
	order_id = order["id"]
	customer = order.get('billing', {}).get('email')
	order_date = order.get('date_created')
	line_items = order.get('line_items', [])
	
	# Creating new sales order
	sales_order = frappe.new_doc("Sales Order")
	sales_order.customer = customer
	sales_order.transaction_date = order_date
	sales_order.delivery_date = add_days(nowdate(), 7)
	# sales_order.company = "World Partnership"
	sales_order.po_no = order_id
	for item in line_items:
		if(frappe.db.exists("Item", item.get('name'))):
			item_code = item.get('name')
			qty = item.get('quantity')
			rate = item.get('price')
			sales_order.append("items", {
				"item_code": item_code,
				"delivery_date": sales_order.delivery_date,
				"qty": qty,
				"rate": rate
			})
	# sales_order.insert(ignore_permissions=True)
	try:
		sales_order.insert(ignore_permissions=True)
		# sales_order.submit()
		# frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(message=str(e), title="Error in creating Sales Order from WooCommerce")

"""

