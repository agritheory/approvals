import frappe


def after_install():
	add_pending_approval_email_template()


def add_pending_approval_email_template():
	if not frappe.db.exists("Email Template", "Pending Approval"):
		email_template = frappe.new_doc("Email Template")
		email_template.update({
            "name": "Pending Approval",
            "subject": "Documents Pending Approval",
            "use_html": 1,
            "response_html": "<p>The following documents require your approval:</p>\n<br>\n<table class=\"table table-bordered\">\n\t<tr>\n\t\t<th>Document Type</th>\n\t\t<th>Name</th>\n\t</tr>\n\t{% for document in documents %}\n\t\t<tr>\n\t\t\t<td>{{ document.doctype }}</td>\n\t\t\t<td><a href=\"{{ document.url }}\">{{ document.name }}</a></td>\n\t\t</tr>\n\t{% endfor %}\n</table>",
        })
		email_template.insert()