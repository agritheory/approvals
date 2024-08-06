## Approvals

Customizable Approval Workflows

#### License

MIT

## Install Instructions

Set up a new bench, substitute a path to the python version to use, which should 3.10 latest

```
# for linux development
bench init --frappe-branch version-14 {{ bench name }} --python ~/.pyenv/versions/3.10.10/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext and HR module
```
bench get-app erpnext --branch version-14
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
