const all_items_detail = []
let isValidDate = false
handle_qty = (item_code, qty) => {
    const item_obj = {
        item_code : item_code,
        qty : qty
    }

    if(all_items_detail.length > 0) {
        let item = all_items_detail.find(i => i.item_code === item_code)
        if(item) {
            item.qty = qty
        } else {
            all_items_detail.push(item_obj)
        }
    } else {
        all_items_detail.push(item_obj)
    }
}

handle_date = (date) => {
    console.log('date is:', date)
    frappe.call({
        method: 'dairy.www.bulk_order.handle_date',
        args : {
            date : date
        },
        callback: function(r) {
            if (!r.exc) {
                isValidDate = true
            }
        }
    });
}
handle_shift =(shift) => {
    frappe.call({
        method: 'dairy.www.bulk_order.handle_shift',
        args : {
            shift : shift
        },
        callback: function(r) {
            console.log('233333333333333333336666666',r.message)
           r.message

        }
    })
}


handleNext = () => { 
    // code for validation
    isValidQty = false
    all_items_detail.map(item => {
        item.qty > 0 ? isValidQty = true : null
        return true
    })
    
    if(all_items_detail.length === 0 || !isValidQty) {
        frappe.throw('Please select item first')
    }
    // if(!isValidDate){
    //     frappe.throw('Please select delivery date')
    // }
    //code to call server side code
    frappe.call({
        method: 'dairy.www.bulk_order.make_so',
        args : {
            item_list : all_items_detail
        },
        callback: function(r) {
            console.log("77777744444444444",r.message)
            if (r.message.status === true && r.message.so_name) {
                                
            }
            try {
                window.location.href = '/shipping_details';
              } catch (err) {
                console.error('Error redirecting to shipping details:', err);
              }
            if(r.message.status == false){
                frappe.throw(r.message.msg)
            }
        }
    });
}

// dissable past date
today = new Date().toISOString().split('T')[0];
$('.date').attr('min', today)
$('.date').attr('value', today)
