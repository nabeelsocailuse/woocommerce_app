// Copyright (c) 2024, Nabeel Saleem and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sync WooCommerce", {
	refresh(frm) {
	},
    sync_orders: function(frm){
        frm.set_intro('Syncing orders...', 'blue');
        // frappe.msgprint(`Syncing woocommerce orders...`)
        frm.call({
            doc: frm.doc,
            method: "fetch_woocommerce_orders",
            callback: function(r){
                frm.set_intro('');
                frm.set_intro('Orders have been synced successfully.', 'green');
                setTimeout(() => {
                    frm.set_intro('');
                }, 4000);
                // frappe.msgprint(`Synced 'WooCommerce' orders success! Against <b>${frm.doc.woo_site_name}</b>`)
            }
        })

    }
});
