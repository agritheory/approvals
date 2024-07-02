from . import __version__ as app_version

app_name = "approvals"
app_title = "Approvals"
app_publisher = "AgriTheory"
app_description = "Customizable Approval Workflows"
app_email = "support@agritheory.dev"
app_license = "MIT"
required_apps = ["erpnext", "hrms"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = ["/assets/approvals/dist/js/style.css"]
app_include_js = ["/assets/approvals/dist/js/approvals.js"]

# include js, css files in header of web template
# web_include_css = "/assets/approvals/css/approvals.css"
# web_include_js = "/assets/approvals/js/approvals.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "approvals/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "approvals.utils.jinja_methods",
# 	"filters": "approvals.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "approvals.install.before_install"
after_install = "approvals.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "approvals.uninstall.before_uninstall"
# after_uninstall = "approvals.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "approvals.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
		"30	8	*	*	*": [
			"approvals.approvals.api.send_reminder_email",
		]
	},
# 	"all": [
# 		"approvals.tasks.all"
# 	],
# 	"daily": [
# 		"approvals.tasks.daily"
# 	],
# 	"hourly": [
# 		"approvals.tasks.hourly"
# 	],
# 	"weekly": [
# 		"approvals.tasks.weekly"
# 	],
# 	"monthly": [
# 		"approvals.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "approvals.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "approvals.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "approvals.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"approvals.auth.validate"
# ]
