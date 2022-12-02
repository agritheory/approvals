## Approvals

Customizable Approval Workflows

#### License

MIT

## Install Instructions

Set up a new bench, substitute a path to the python version to use, which should 3.10 latest

```
# for linux development
bench init --frappe-branch version-14 {{ bench name }} --python ~/.pyenv/versions/3.10.4/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext app, its prerequisite Payments, and the HR module
```
bench get-app payments
bench get-app erpnext --branch version-14
bench get-app hrms
```
Download this application and install all apps
```
bench get-app approvals git@github.com:agritheory/approvals.git
bench install-app erpnext hrms approvals
```
Set developer mode in `site_config.json`
```
cd {{ site name }}
nano site_config.json

 "developer_mode": 1,
```

Update and get the site ready
```
bench start
```
In a new terminal window
```
bench update
bench migrate
bench build
```
Setup test data
```
# Enable server scripts and install test data
bench --site {{ site name }} set-config server_script_enabled true
bench execute 'approvals.approvals.test_setup.before_test'
```
