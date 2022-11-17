from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in approvals/__init__.py
from approvals import __version__ as version

setup(
	name="approvals",
	version=version,
	description="Customizable Approval Workflows",
	author="AgriTheory",
	author_email="support@agritheory.dev",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
