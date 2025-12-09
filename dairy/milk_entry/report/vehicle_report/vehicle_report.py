import frappe


def execute(filters=None):
    filters = frappe._dict(filters or {})

    # ---------------------------------------------------------
    # Handle default selection (None = All)
    # ---------------------------------------------------------
    entry_type_filter = filters.get("entry_type")
    if not entry_type_filter:
        entry_type_filter = "All"

    # ---------------------------------------------------------
    # Dynamic Columns
    # ---------------------------------------------------------
    columns = [
        {"label": "Vehicle No", "fieldname": "vehicle_no", "fieldtype": "Link", "options": "Vehicle", "width": 120},
        {"label": "Make / Model", "fieldname": "make_model", "fieldtype": "Data", "width": 160},
        {"label": "Entry Type", "fieldname": "entry_type", "fieldtype": "Data", "width": 140},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 120},
    ]

    # Hide these when: PUC / Fitness / Insurance selected
    hide_non_service = entry_type_filter in ("PUC", "Fitness", "Insurance")

    if not hide_non_service:
        columns += [
            {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Data", "width": 150},
            {"label": "Last Odometer", "fieldname": "last_odometer", "fieldtype": "Float", "width": 120},
            {"label": "Current Odometer", "fieldname": "current_odometer", "fieldtype": "Float", "width": 120},
            {"label": "Fuel Qty", "fieldname": "fuel_qty", "fieldtype": "Float", "width": 80},
            {"label": "Service KM", "fieldname": "service_km", "fieldtype": "Float", "width": 90},
            {"label": "Next Service KM", "fieldname": "next_service_km", "fieldtype": "Float", "width": 120},
        ]

    columns.append(
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 250}
    )

    # ---------------------------------------------------------
    # VEHICLE FILTERS
    # ---------------------------------------------------------
    vehicle_filters = {}

    if filters.get("vehicle"):
        vehicle_filters["name"] = filters.vehicle

    if filters.get("make") and filters.make != "All":
        vehicle_filters["make"] = filters.make

    # ---------------------------------------------------------
    # FETCH VEHICLES
    # ---------------------------------------------------------
    vehicles = frappe.db.get_all(
        "Vehicle",
        filters=vehicle_filters,
        fields=[
            "name", "make", "model",
            "custom_pollution_validity", "custom_fitness_validity",
            "end_date"
        ]
    )

    if not vehicles:
        return columns, []

    vehicle_names = [v.name for v in vehicles]

    # ---------------------------------------------------------
    # FETCH LOGS
    # ---------------------------------------------------------
    logs = frappe.db.get_all(
        "BDF Vehicle Log",
        filters={"vehicle": ["in", vehicle_names]},
        fields=[
            "vehicle", "type", "date", "supplier",
            "last_odometer_reading", "current_odometer_reading",
            "fuel_qty", "service_kilometer", "creation"
        ],
        order_by="creation desc"
    )

    latest_fuel = {}
    latest_service = {}
    max_odometer = {}

    for log in logs:
        veh = log.vehicle

        # Track highest odometer
        max_odometer.setdefault(veh, 0)
        curr = float(log.current_odometer_reading or 0)
        if curr > max_odometer[veh]:
            max_odometer[veh] = curr

        # Latest fuel refill
        if log.type == "Fuel Refill" and veh not in latest_fuel:
            latest_fuel[veh] = log

        # Latest service
        if log.type == "Service" and veh not in latest_service:
            latest_service[veh] = log

    data = []

    # ---------------------------------------------------------
    # BUILD ROWS
    # ---------------------------------------------------------
    for v in vehicles:
        make_model = f"{v.make} / {v.model}"

        # ----------------------------------------
        # Fuel Refill Entry
        # ----------------------------------------
        if entry_type_filter in ("All", "Fuel Refill"):
            fuel = latest_fuel.get(v.name)

            data.append({
                "vehicle_no": v.name,
                "make_model": make_model,
                "entry_type": "Fuel Refill",
                "date": fuel.date if fuel else None,
                "supplier": fuel.supplier if fuel else "—",
                "last_odometer": fuel.last_odometer_reading if fuel else "—",
                "current_odometer": fuel.current_odometer_reading if fuel else "—",
                "fuel_qty": fuel.fuel_qty if fuel else "—",
                "service_km": "—",
                "next_service_km": "—",
                "status": "—",
            })

        # ----------------------------------------
        # Service Entry
        # ----------------------------------------
        if entry_type_filter in ("All", "Service"):
            service = latest_service.get(v.name)

            if service:
                next_km = (service.current_odometer_reading or 0) + (service.service_kilometer or 0)
                curr = max_odometer.get(v.name, 0)

                if curr >= next_km:
                    status = f'<span style="color:#b00020;font-weight:700;">{next_km} — SERVICE DUE</span>'
                elif (next_km - curr) <= 500:
                    status = f'<span style="color:#e65c00;font-weight:700;">{next_km} — Upcoming</span>'
                else:
                    status = f'<span style="color:#0b7a3f;font-weight:700;">{next_km} — OK</span>'
            else:
                status = "—"
                next_km = "—"

            data.append({
                "vehicle_no": v.name,
                "make_model": make_model,
                "entry_type": "Service",
                "date": service.date if service else None,
                "supplier": service.supplier if service else "—",
                "last_odometer": service.last_odometer_reading if service else "—",
                "current_odometer": service.current_odometer_reading if service else "—",
                "fuel_qty": "—",
                "service_km": service.service_kilometer if service else "—",
                "next_service_km": next_km,
                "status": status
            })

        # ----------------------------------------
        # PUC
        # ----------------------------------------
        if entry_type_filter in ("All", "PUC"):
            data.append(compliance_row(v, make_model, "PUC Validity", v.custom_pollution_validity))

        # ----------------------------------------
        # Fitness
        # ----------------------------------------
        if entry_type_filter in ("All", "Fitness"):
            data.append(compliance_row(v, make_model, "Fitness Validity", v.custom_fitness_validity))

        # ----------------------------------------
        # Insurance
        # ----------------------------------------
        if entry_type_filter in ("All", "Insurance"):
            data.append(compliance_row(v, make_model, "Insurance Validity", v.end_date))

    return columns, data


# ---------------------------------------------------------
# Helper row generator (PUC / Fitness / Insurance)
# ---------------------------------------------------------
def compliance_row(v, make_model, label, date_value):
    today = frappe.utils.getdate()

    if isinstance(date_value, str):
        date_value = frappe.utils.getdate(date_value)

    if not date_value:
        status = '<span style="color:gray;">No Date</span>'
    elif date_value < today:
        status = f'<span style="color:#b00020;font-weight:700;">{date_value} — EXPIRED</span>'
    elif frappe.utils.date_diff(date_value, today) <= 30:
        status = f'<span style="color:#e65c00;font-weight:700;">{date_value} — Expiring Soon</span>'
    else:
        status = f'<span style="color:#0b7a3f;font-weight:700;">{date_value} — Valid</span>'

    return {
        "vehicle_no": v.name,
        "make_model": make_model,
        "entry_type": label,
        "date": None,
        "supplier": "—",
        "last_odometer": "—",
        "current_odometer": "—",
        "fuel_qty": "—",
        "service_km": "—",
        "next_service_km": "—",
        "status": status
    }
