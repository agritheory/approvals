import frappe


def add_approval_comment(
	doctype: str,
	name: str,
	content: str,
	*,
	subject: str | None = None,
	comment_type: str = "Comment",
):
	comment = frappe.new_doc("Comment")
	comment.update(
		{
			"comment_by": frappe.session.user,
			"comment_email": frappe.session.user,
			"comment_type": comment_type,
			"content": content,
			"reference_doctype": doctype,
			"reference_name": name,
			"subject": subject,
		}
	)
	comment.insert(ignore_permissions=True)
	return comment
