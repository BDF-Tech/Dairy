from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	if not filters: filters = {}
	conditions = get_columns(filters,"Van Collection Items")
	data = get_data(filters, conditions)

	return conditions["columns"], data

def get_columns(filters, trans):
	validate_filters(filters)

	# get conditions for based_on filter cond
	based_on_details = based_wise_columns_query(filters.get("based_on"),trans)

	# get conditions for periodic filter cond
	period_cols, period_select = period_wise_columns_query(filters, trans)
	# get conditions for grouping filter cond
	group_by_cols = group_wise_column(filters.get("group_by"))

	columns = based_on_details["based_on_cols"] + period_cols + \
			[_("Total(Cow Milk Entry)") + ":Float:120",
			 _("Total(Cow Milk Collected)") + ":Float:120",
			 _("Total(Cow Milk Cans)") + ":Float:120",
			 _("Total(Cow Milk FAt)") + ":Float:120",
			 _("Total(Cow Milk CLR)") + ":Float:120",

			 _("Total(Buffalo Milk Entry)") + ":Float:120",
			 _("Total(Buffalo Milk Collected)") + ":Float:120",
			 _("Total(Buffalo Milk Cans)") + ":Float:120",
			 _("Total(Buffalo Milk FAT)") + ":Float:120",
			 _("Total(Buffalo Milk CLR)") + ":Float:120",

			 _("Total(Mix Milk entry)") + ":Float:120",
			 _("Total(Mix Milk Collected)") + ":Float:120",
			 _("Total(Mix Milk Cans)") + ":Float:120",
			 _("Total(Mix Milk FAT)") + ":Float:120",
			 _("Total(Mix Milk CLR)") + ":Float:120"]

	if group_by_cols:
		columns = based_on_details["based_on_cols"] + group_by_cols + period_cols + \
				  [_("Total(Cow Milk Entry)") + ":Float:120",
				   _("Total(Cow Milk Collected)") + ":Float:120",
				   _("Total(Cow Milk Cans)") + ":Float:120",
				   _("Total(Cow Milk FAt)") + ":Float:120",
				   _("Total(Cow Milk CLR)") + ":Float:120",

				   _("Total(Buffalo Milk Entry)") + ":Float:120",
				   _("Total(Buffalo Milk Collected)") + ":Float:120",
				   _("Total(Buffalo Milk Cans)") + ":Float:120",
				   _("Total(Buffalo Milk FAT)") + ":Float:120",
				   _("Total(Buffalo Milk CLR)") + ":Float:120",

				   _("Total(Mix Milk entry)") + ":Float:120",
				   _("Total(Mix Milk Collected)") + ":Float:120",
				   _("Total(Mix Milk Cans)") + ":Float:120",
				   _("Total(Mix Milk FAT)") + ":Float:120",
				   _("Total(Mix Milk CLR)") + ":Float:120"]

	#
	conditions = {"based_on_select": based_on_details["based_on_select"], "period_wise_select": period_select,
			"columns": columns, "group_by": based_on_details["based_on_group_by"], "grbc": group_by_cols,
			 "trans": trans,
			"addl_tables": based_on_details["addl_tables"],
			 "addl_tables_relational_cond": based_on_details.get("addl_tables_relational_cond", "")}
	return conditions

def validate_filters(filters):
	for f in ["From Date","To Date", "Based On", "Period", "Company"]:
		if not filters.get(f.lower().replace(" ", "_")):
			frappe.throw(_("{0} is mandatory").format(f))

	# if not frappe.db.exists("Fiscal Year", filters.get("fiscal_year")):
	# 	frappe.throw(_("Fiscal Year: {0} does not exists").format(filters.get("fiscal_year")))

	if filters.get("based_on") == filters.get("group_by"):
		frappe.throw(_("'Based On' and 'Group By' can not be same"))

def based_wise_columns_query(based_on, trans):
	based_on_details = {}

	# based_on_cols, based_on_select, based_on_group_by, addl_tables
	if based_on == "dcs":
		based_on_details["based_on_cols"] = ["DCS:Link/Warehouse:120", "DCS Name:Data:120"]
		based_on_details["based_on_select"] = "t1.dcs,t1.dcs,"
		based_on_details["based_on_group_by"] = 't1.dcs'
		based_on_details["addl_tables"] = ''

	if based_on == "route":
		based_on_details["based_on_cols"] = ["Route:Link/Route Master:120", "Route Name:Data:120"]
		based_on_details["based_on_select"] = "t1.route,t1.route,"
		based_on_details["based_on_group_by"] = 't1.route'
		based_on_details["addl_tables"] = ''

	if based_on == "vehicle":
		based_on_details["based_on_cols"] = ["Vehicle:Link/Vehicle:120", "Vehicle:Data:120"]
		based_on_details["based_on_select"] = "t1.vehicle,t1.vehicle,"
		based_on_details["based_on_group_by"] = 't1.vehicle'
		based_on_details["addl_tables"] = ''

	return based_on_details

def period_wise_columns_query(filters, trans):
	query_details = ''
	pwc = []
	bet_dates = get_period_date_ranges(filters.get("period"),filters,filters.get("from_date"),filters.get("to_date"))

	if trans in ['Van Collection Items']:
		trans_date = 'date'
		if filters.period_based_on:
			trans_date = filters.period_based_on
	else:
		trans_date = 'date'

	if filters.get("period") != 'Yearly':
		for dt in bet_dates:
			get_period_wise_columns(dt, filters.get("period"), pwc)
			query_details = get_period_wise_query(dt, trans_date, query_details)
	else:
		pwc = [_(filters.get("from_date")) + " ("+ _("Cow Milk Entry") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Cow Milk Collected") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Cow Milk Cans") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Cow Milk FAT") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Cow Milk CLR") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Buffalo Milk Entry") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Buffalo Milk Collected") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Buffalo Milk Cans") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Buffalo Milk FAT") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Buffalo Milk CLR") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Mix Milk Entry") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Mix Milk Collected") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Mix Milk Cans") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Mix Milk FAT") + "):Float:120",
			_(filters.get("from_date")) + " ("+ _("Mix Milk CLR") + "):Float:120"]

		print('rom_datewc^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^',pwc)

		query_details = """SUM(t1.cow_milk_vol),SUM(t1.cow_milk_collected),SUM(t1.cow_milk_cans),SUM(t1.cow_milk_fat),SUM(t1.cow_milk_clr),
					SUM(t1.buf_milk_vol),SUM(t1.buffalow_milk_collected),SUM(t1.buf_milk_cans),SUM(t1.buf_milk_fat),SUM(t1.buf_milk_clr),
					SUM(t1.mix_milk_vol),SUM(t1.mix_milk_collected),SUM(t1.mix_milk_cans),SUM(t1.mix_milk_fat),SUM(t1.mix_milk_clr),"""

	query_details += """SUM(t1.cow_milk_vol),SUM(t1.cow_milk_collected),SUM(t1.cow_milk_cans),SUM(t1.cow_milk_fat),SUM(t1.cow_milk_clr),
					SUM(t1.buf_milk_vol),SUM(t1.buffalow_milk_collected),SUM(t1.buf_milk_cans),SUM(t1.buf_milk_fat),SUM(t1.buf_milk_clr),
					SUM(t1.mix_milk_vol),SUM(t1.mix_milk_collected),SUM(t1.mix_milk_cans),SUM(t1.mix_milk_fat),SUM(t1.mix_milk_clr)"""
	return pwc, query_details

@frappe.whitelist(allow_guest=True)
def get_period_date_ranges(period,filters,year_start_date,year_end_date):
	from dateutil.relativedelta import relativedelta

	if not year_start_date:
		year_start_date = filters.get("from_date")
		year_end_date = filters.get("to_date")

	increment = {
		"Monthly": 1,
		"Quarterly": 3,
		"Half-Yearly": 6,
		"Yearly": 12
	}.get(period)

	period_date_ranges = []
	for i in range(1, 13, increment):
		period_end_date = getdate(year_start_date) + relativedelta(months=increment, days=-1)
		print('period_end_date************************',type(period_end_date),year_start_date,type(year_end_date),(relativedelta(days=1)))
		if period_end_date > getdate(year_end_date):
			period_end_date = year_end_date
		period_date_ranges.append([year_start_date, period_end_date])
		year_start_date = getdate(period_end_date )+ (relativedelta(days=1))
		if period_end_date == year_end_date:
			break

	return period_date_ranges

def get_period_wise_columns(bet_dates, period, pwc):
	if period == 'Monthly':
		pwc += [_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk CLR") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk CLR") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk CLR") + "):Float:120"]
	else:
		pwc += [_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Cow Milk CLR") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Buffalo Milk CLR") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Entry") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Collected") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk Cans") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk FAT") + "):Float:120",
				_(get_mon(bet_dates[0])) + " ("+ _("Mix Milk CLR") + "):Float:120"]

def get_mon(dt):
	return getdate(dt).strftime("%b")

def get_period_wise_query(bet_dates, trans_date, query_details):
	query_details += """SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.cow_milk_vol,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.cow_milk_collected,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.cow_milk_cans,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.cow_milk_fat,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.cow_milk_clr,NULL)),
							
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.buf_milk_vol,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.buffalow_milk_collected,NULL)),						
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.buf_milk_cans,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.buf_milk_fat,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.buf_milk_clr,NULL)),
						
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.mix_milk_vol,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.mix_milk_collected,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.mix_milk_cans,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.mix_milk_fat,NULL)),
						SUM(IF(t1.%(date)s BETWEEN '%(sd)s' AND '%(ed)s',t1.mix_milk_clr,NULL)),
				""" % {"date": trans_date, "sd": bet_dates[0],"ed": bet_dates[1]}

	return query_details

def group_wise_column(group_by):
	if group_by:
		if group_by == "dcs":
			return ["DCS:Link/Warehouse:120"]
		if group_by == "route":
			return ["Route:Link/Route Master:120"]
		if group_by == "vehicle":
			return ["Vehicle:Link/Vehicle:120"]
	else:
		return []

def get_data(filters, conditions):
	data = []
	inc, cond= '',''
	base_on_name = conditions["based_on_select"].split(",")[0]
	query_details =  conditions["based_on_select"] + conditions["period_wise_select"]

	posting_date = 't1.date'
	if conditions.get('trans') in ['Van Collection Items']:
		posting_date = 't1.date'
		if filters.period_based_on:
			posting_date = 't1.'+filters.period_based_on

	year_start_date = filters.get("from_date")
	year_end_date = filters.get("to_date")
	
	if filters.get("group_by"):
		sel_col = ''
		ind = conditions["columns"].index(conditions["grbc"][0])

		if filters.get("group_by") == 'dcs':
			sel_col = 't1.dcs'
		elif filters.get("group_by") == 'route':
			sel_col = 't1.route'
		elif filters.get("group_by") == 'vehicle':
			sel_col = 't1.vehicle'

		if filters.get('based_on') in ['dcs','route','vehicle']:
			inc = 2
		else:
			inc = 1
		# data1 = frappe.db.sql(""" select %s from `tab%s` t1
		# 			where t1.company = %s and %s between %s and %s and %s is not null and
		# 			t1.docstatus = 1 %s %s
		# 			group by %s""" % (query_details,  conditions["trans"],  "%s",
		# 			posting_date, "%s", "%s",base_on_name, conditions.get("addl_tables_relational_cond"), cond, conditions["group_by"]), (filters.get("company"),
		# 			year_start_date, year_end_date),as_list=1)
		#
		data1 = frappe.db.sql(""" select %s from `tab%s` t1
					where t1.company = %s and %s between %s and %s and %s is not null
					group by %s""" % (query_details,  conditions["trans"],  "%s",
					posting_date, "%s", "%s",base_on_name, conditions["group_by"]), (filters.get("company"),
					year_start_date, year_end_date),as_list=1)


		for d in range(len(data1)):
			#to add blanck column
			dt = data1[d]
			dt.insert(ind,'')
			data.append(dt)
	#
	# 		#to get distinct value of col specified by group_by in filter
	# 		row = frappe.db.sql("""select DISTINCT(%s) from `tab%s` t1
	# 					where t1.company = %s and %s between %s and %s and %s is not null
	# 					and t1.docstatus = 1 and %s = %s %s %s
	# 				""" %
	# 				(sel_col,  conditions["trans"],
	# 					"%s", posting_date, "%s", "%s",base_on_name, conditions["group_by"], "%s", conditions.get("addl_tables_relational_cond"), cond),
	# 				(filters.get("company"), year_start_date, year_end_date, data1[d][0]), as_list=1)
	#
			row = frappe.db.sql("""select DISTINCT(%s) from `tab%s` t1
						where t1.company = %s and %s between %s and %s and %s is not null
						and %s = %s %s %s
					""" %
					(sel_col,  conditions["trans"],
						"%s", posting_date, "%s", "%s",base_on_name, conditions["group_by"], "%s", conditions.get("addl_tables_relational_cond"), cond),
					(filters.get("company"), year_start_date, year_end_date, data1[d][0]), as_list=1)

			for i in range(len(row)):
				des = ['' for q in range(len(conditions["columns"]))]
	# 			#get data for group_by filter
	# 			row1 = frappe.db.sql(""" select %s , %s from `tab%s` t1
	# 						where t1.company = %s and %s between %s and %s and %s is not null
	# 						and t1.docstatus = 1 and %s = %s and %s = %s %s %s
	# 					""" %
	# 					(sel_col, conditions["period_wise_select"], conditions["trans"],
	# 						"%s", posting_date, "%s","%s",base_on_name, sel_col,
	# 						"%s", conditions["group_by"], "%s", conditions.get("addl_tables_relational_cond"), cond),
	# 					(filters.get("company"), year_start_date, year_end_date, row[i][0],
	# 						data1[d][0]), as_list=1)

				row1 = frappe.db.sql(""" select %s , %s from `tab%s` t1
							where t1.company = %s and %s between %s and %s and %s is not null
							and %s = %s and %s = %s %s %s
						""" %
						(sel_col, conditions["period_wise_select"], conditions["trans"],
							"%s", posting_date, "%s","%s",base_on_name, sel_col,
							"%s", conditions["group_by"], "%s", conditions.get("addl_tables_relational_cond"), cond),
						(filters.get("company"), year_start_date, year_end_date, row[i][0],
							data1[d][0]), as_list=1)

				des[ind] = row[i][0]

				for j in range(1,len(conditions["columns"])-inc):
					des[j+inc] = row1[0][j]

				data.append(des)
	else:
		# data = frappe.db.sql(""" select %s from `tab%s` t1
		# 			where t1.company = %s and %s between %s and %s and  %s is not null and
		# 			t1.docstatus = 1 %s %s
		# 			group by %s
		# 			""" %
		# 		(query_details, conditions["trans"],
		# 			"%s", posting_date, "%s", "%s",base_on_name, cond, conditions.get("addl_tables_relational_cond", ""), conditions["group_by"]),
		# 		(filters.get("company"), year_start_date, year_end_date), as_list=1)

		data = frappe.db.sql(""" select %s from `tab%s` t1
					where t1.company = %s and %s between %s and %s and  %s is not null
					group by %s
					""" %
				(query_details, conditions["trans"],
					"%s", posting_date, "%s", "%s",base_on_name, conditions["group_by"]),
				(filters.get("company"), year_start_date, year_end_date), as_list=1)
	return data