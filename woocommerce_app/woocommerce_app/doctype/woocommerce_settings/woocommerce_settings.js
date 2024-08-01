// Copyright (c) 2024, Nabeel Saleem and contributors
// For license information, please see license.txt

frappe.ui.form.on("WooCommerce Settings", {
	refresh(frm) {
	},
    sync_orders: function(frm){
        frappe.msgprint(`Syncing woocommerce orders...`)
        frm.call({
            doc: frm.doc,
            method: "fetch_woocommerce_orders",
            callback: function(r){
                frappe.msgprint(`Synced 'WooCommerce' orders success! Against <b>${frm.doc.woo_site_name}</b>`)
            }
        })

    }
});
