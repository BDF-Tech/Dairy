frappe.ui.form.on('Crate Balance Adjustment', {

    refresh: function(frm) {
        _refresh_balance(frm);

        if (frm.doc.docstatus === 0 && _is_loose(frm) && _get_party(frm)) {
            frm.add_custom_button(__('Get All Crate Types'), () => _fill_all_crate_types(frm));
        }
    },

    party_type: function(frm) {
        frm.set_value('customer', '');
        frm.set_value('driver', '');
        frm.set_value('warehouse', '');
        frm.set_value('driver_balance_type', '');
        frm.set_value('crate_type', '');
        _clear_balance(frm);
    },

    customer: function(frm) {
        _refresh_balance(frm);
    },

    driver: function(frm) {
        _on_party_change(frm);
    },

    warehouse: function(frm) {
        _on_party_change(frm);
    },

    driver_balance_type: function(frm) {
        frm.set_value('crate_type', '');
        _fill_existing_crate_types(frm);
        frm.refresh();
    },
});

// Party picked / changed: refresh balances and, for Loose Crate,
// load the crate types this party already holds.
function _on_party_change(frm) {
    frm.set_value('crate_type', '');
    _refresh_balance(frm);
    _fill_existing_crate_types(frm);
    frm.refresh();
}

// Fill the table with every crate type the driver / warehouse already
// has a balance row for, with its current count. Crates (+/-) start at 0.
async function _fill_existing_crate_types(frm) {
    frm.clear_table('crate_items');
    frm.refresh_field('crate_items');
    if (frm.doc.docstatus !== 0 || !_is_loose(frm) || !_get_party(frm)) return;

    const map = await _loose_balances(frm);
    Object.keys(map).sort().forEach(ct => {
        frm.add_child('crate_items', {
            crate_type: ct, current_balance: map[ct], crates: 0, new_balance: map[ct],
        });
    });
    frm.refresh_field('crate_items');
}

frappe.ui.form.on('Crate Balance Adjustment Item', {

    crate_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        _loose_balances(frm).then(map => {
            frappe.model.set_value(cdt, cdn, 'current_balance', map[row.crate_type] || 0);
            frappe.model.set_value(cdt, cdn, 'new_balance', (map[row.crate_type] || 0) + flt(row.crates));
        });
    },

    crates: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'new_balance', flt(row.current_balance) + flt(row.crates));
    },
});

function _is_loose(frm) {
    return ['Driver', 'Warehouse'].includes(frm.doc.party_type) &&
        frm.doc.driver_balance_type === 'Loose Crate';
}

function _loose_balances(frm) {
    return frappe.call({
        method: 'dairy.dairy.doctype.crate_balance_adjustment.crate_balance_adjustment.get_party_crate_balances',
        args: { party_type: frm.doc.party_type, party: _get_party(frm) },
    }).then(r => {
        const map = {};
        ((r.message && r.message.loose_balances) || []).forEach(b => { map[b.crate_type] = flt(b.balance); });
        return map;
    });
}

async function _fill_all_crate_types(frm) {
    const [types, map] = await Promise.all([
        frappe.db.get_list('Crate Type', { pluck: 'name', limit: 0, order_by: 'name asc' }),
        _loose_balances(frm),
    ]);
    const existing = {};
    (frm.doc.crate_items || []).forEach(r => { existing[r.crate_type] = r; });

    types.forEach(ct => {
        const row = existing[ct] || frm.add_child('crate_items', { crate_type: ct, crates: 0 });
        row.current_balance = map[ct] || 0;
        row.new_balance = flt(row.current_balance) + flt(row.crates);
    });
    frm.refresh_field('crate_items');
    frappe.show_alert({ message: __('Enter +/- only for the crate types you want to change. Rows left at 0 are ignored.'), indicator: 'blue' });
}

function _get_party(frm) {
    if (frm.doc.party_type === 'Customer') return frm.doc.customer;
    if (frm.doc.party_type === 'Driver') return frm.doc.driver;
    if (frm.doc.party_type === 'Warehouse') return frm.doc.warehouse;
    return null;
}

function _refresh_balance(frm) {
    const party = _get_party(frm);
    if (!frm.doc.party_type || !party) {
        _clear_balance(frm);
        return;
    }

    frappe.call({
        method: 'dairy.dairy.doctype.crate_balance_adjustment.crate_balance_adjustment.get_party_crate_balances',
        args: { party_type: frm.doc.party_type, party: party },
        callback: function(r) {
            if (!r.message) return;
            _render_balance(frm, r.message);
        }
    });
}

function _clear_balance(frm) {
    const $el = frm.fields_dict['current_balance_html'].$wrapper;
    $el.html('<div style="color:#aaa;font-size:12px;">Select a party to see current balance.</div>');
}

function _card(label, value, color) {
    return `
        <div style="background:#f7f7f7;border-radius:8px;padding:12px 20px;min-width:160px;">
            <div style="font-size:11px;color:#888;margin-bottom:4px;">${label}</div>
            <div style="font-size:22px;font-weight:700;color:${color};">${value}</div>
        </div>
    `;
}

function _render_balance(frm, data) {
    const $el = frm.fields_dict['current_balance_html'].$wrapper;

    // Customer — single invoice balance card only
    if (!data.supports_loose) {
        const bal = data.invoice_balance || 0;
        const color = bal > 0 ? '#e67e22' : '#27ae60';
        $el.html(`
            <div style="display:flex;gap:24px;flex-wrap:wrap;padding:8px 0;">
                ${_card('Current Crate Balance', bal + ' crates', color)}
            </div>
        `);
        return;
    }

    // Driver / Warehouse — invoice balance + loose per crate type
    const inv = data.invoice_balance || 0;
    const invColor = inv > 0 ? '#e67e22' : '#27ae60';
    const invLabel = data.type === 'warehouse' ? 'Warehouse Crates' : 'Invoice Crates';

    let html = `<div style="display:flex;gap:16px;flex-wrap:wrap;padding:8px 0;">`;
    html += _card(invLabel, inv + ' crates', invColor);

    const loose = data.loose_balances || [];
    if (loose.length === 0) {
        html += _card('Loose Crates', 'None', '#aaa');
    } else {
        loose.forEach(function(row) {
            const lbal = row.balance || 0;
            const lcolor = lbal > 0 ? '#e67e22' : '#27ae60';
            html += _card(row.crate_type, lbal + ' crates', lcolor);
        });
    }

    html += `</div>`;
    $el.html(html);
}
