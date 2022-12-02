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
<<<<<<< HEAD

Download the ERPNext and HR module

=======
Download the ERPNext app, its prerequisite Payments, and the HR module
>>>>>>> 3979cce (feat: add detail to instructions)
```
bench get-app payments
bench get-app erpnext --branch version-14
bench get-app hrms
```
<<<<<<< HEAD

Download this application and install all apps

=======
Download this application and install all apps
>>>>>>> 3979cce (feat: add detail to instructions)
```
bench get-app approvals git@github.com:agritheory/approvals.git
bench install-app erpnext hrms approvals
```

<<<<<<< HEAD
Set developer mode

```
bench --site {{ site name }} set-config developer_mode true
=======
 "developer_mode": 1,
>>>>>>> 3979cce (feat: add detail to instructions)
```

Update and get the site ready

```
bench start
```
<<<<<<< HEAD

=======
In a new terminal window
```
bench update
bench migrate
bench build
```
>>>>>>> 3979cce (feat: add detail to instructions)
Setup test data

```
# Enable server scripts and install test data
bench --site {{ site name }} set-config server_script_enabled true
<<<<<<< HEAD
bench --site {{ site name }} execute 'approvals.tests.setup.before_test'
=======
bench execute 'approvals.approvals.test_setup.before_test'
>>>>>>> 3979cce (feat: add detail to instructions)
```
