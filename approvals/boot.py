import frappe


def boot_session(bootinfo):
	bootinfo.user.can_read.append("Purchase Invoice")
