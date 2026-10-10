frappe.ui.form.on('Crate Balance Adjustment', {

    refresh: function(frm) {
        _refresh_balance(frm);
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
        frm.set_value('driver_balance_type', '');
        frm.set_value('crate_type', '');
        _refresh_balance(frm);
    },

    warehouse: function(frm) {
        frm.set_value('driver_balance_type', '');
        frm.set_value('crate_type', '');
        _refresh_balance(frm);
    },

    driver_balance_type: function(frm) {
        frm.set_value('crate_type', '');
    },
});

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
