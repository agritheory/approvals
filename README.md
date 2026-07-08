<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

## Approvals

Customizable Approval Workflows

#### License

MIT

## Install Instructions

Set up a new bench with Python 3.11 or later. Substitute a path to the Python interpreter to use.

```
# for linux development
bench init --frappe-branch version-16 {{ bench name }} --python ~/.pyenv/versions/3.11/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext and HR module
```
bench get-app erpnext --branch version-16
bench get-app hrms
```
Download this application and install all apps
```
bench get-app approvals git@github.com:agritheory/approvals.git
bench install-app erpnext hrms approvals
```
Set developer mode
```
bench --site {{ site name }} set-config developer_mode true
```

Update and get the site ready
```
bench start
```

Setup test data
```
# Enable server scripts and install test data
bench --site {{ site name }} set-config server_script_enabled true
bench --site {{ site name }} execute 'approvals.tests.setup.before_test'
```
