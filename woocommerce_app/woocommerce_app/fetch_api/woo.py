# api/method/woocommerce_app.woocommerce_app.fetch_api.woo.fetch_woocommerce_orders

import requests, ast
import frappe
from frappe.utils import flt, nowdate, add_days

@frappe.whitelist(allow_guest=True)
def fetch_woocommerce_orders_new():
    woo_site_url = "https://daon.nz/"
    consumer_key = "ck_f3de68c4862cba1358f08d67f78468754fc947ba"
    consumer_secret = "cs_610f6669fa48c21766445752f56200aa5f576574"

    orders_url = f"{woo_site_url}/wp-json/wc/v3/orders/9638"
    
    response = requests.get(orders_url, auth=(consumer_key, consumer_secret))
    if response.status_code == 200:
        orders = response.json()
        # print(orders)
        for order in [orders]:
        #     print((order))
            create_sales_order(order)
    else:
        frappe.throw(_("Failed to fetch WooCommerce orders. Please check your API credentials and URL."))

def create_sales_order(order):
    
    # order = frappe._dict(order)
     
    # customer_name = order.get('billing', {}).get('first_name') + " " + order.get('billing', {}).get('last_name')
    customer_email = order.get('billing', {}).get('email')
    order_date = order.get('date_created')
    sales_order = frappe.new_doc("Sales Order")
    # customer = customer_name

    sales_order.customer = customer_email
    sales_order.transaction_date = order_date
    sales_order.delivery_date = add_days(nowdate(), 7)
    sales_order.company = "Alkhidmat Foundation Pakistan"
    sales_order.po_no = order["id"]
    for item in order.get('line_items', []):
        
        if(frappe.db.exists("Item", item.get('name'))):
            # frappe.throw(f"{item}")
            sales_order.append("items", {
                "item_code": item.get('name'),
                "item_name": item.get('name'),
                "delivery_date": sales_order.delivery_date,
                "qty": 1,
                "rate": 10
            })
    sales_order.insert(ignore_permissions=True)
    # try:
    #     # frappe.throw(frappe.as_json(sales_order))
    #     sales_order.insert(ignore_permissions=True)
    #     # sales_order.submit()
    #     # frappe.db.commit()
    # except Exception as e:
    #     frappe.log_error(message=str(e), title="Error in creating Sales Order from WooCommerce")
