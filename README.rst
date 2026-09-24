Field Service HR Bridge for Odoo 18
====================================

Free and open-source integration between **Odoo 18 Community HR Employees**
and **OCA Field Service Workers**.

This module connects ``hr.employee`` records with OCA Field Service
``fsm.person`` workers while using the employee's existing ``res.partner``
work contact as the shared identity.

It is designed for companies using **Odoo Community Edition 18.0** together
with the **OCA Field Service** application and needing their employees to be
available as field service technicians without maintaining duplicated contact
information.

Features
========

* Link Odoo HR employees with OCA Field Service workers.
* Create an FSM worker directly from an employee.
* Create an FSM worker from an existing contact.
* Automatically link an FSM worker to an employee when both use the same
  work contact.
* Support external Field Service workers without creating an HR employee.
* Reuse the existing ``res.partner`` contact as the common identity.
* Synchronize relevant employee and Field Service information.
* Synchronize the employee working calendar with the FSM worker calendar.
* Automatically detect existing employee/worker relationships.
* Archive Field Service workers instead of deleting historical records.
* Smart buttons for navigation between Employees, Contacts and FSM Workers.
* Prevent duplicate Field Service workers for the same employee or contact.

Architecture
============

The module keeps the standard Odoo and OCA data models instead of duplicating
employee or contact information.

::

    hr.employee
         |
         | work_contact_id
         v
    res.partner
         ^
         | partner_id
         |
    fsm.person

When an FSM worker corresponds to an Odoo employee, the module additionally
creates an explicit relationship between ``fsm.person`` and ``hr.employee``.

External Field Service Workers
==============================

An FSM worker does not need to be an Odoo employee.

This makes the module suitable for:

* Internal installation teams
* Field technicians
* Maintenance personnel
* External contractors
* Freelance technicians
* Subcontracted installation companies

Creating a Field Service worker from a contact never creates an HR employee
automatically.

Requirements
============

This module requires:

* Odoo 18.0 Community Edition
* Odoo Employees (``hr``)
* OCA Field Service 18.0 (``fieldservice``)

OCA Field Service is **not included in this repository**.

The official OCA Field Service project is available at:

::

    https://github.com/OCA/field-service

Use the ``18.0`` branch.

The minimum required OCA module is:

::

    fieldservice

Its own dependencies, such as ``base_territory``, must also be installed as
required by OCA.

Installation
============

1. Install the OCA Field Service repository for Odoo 18.0.
2. Make sure the ``fieldservice`` module and its dependencies are available
   in your Odoo ``addons_path``.
3. Copy ``az_fieldservice_hr_bridge`` into one of your Odoo addons
   directories.
4. Restart Odoo.
5. Update the Apps list.
6. Install **Field Service HR Bridge**.

Usage
=====

From Employees
--------------

Open an employee and enable the Field Service worker option.

The module will:

* reuse the employee's work contact;
* find an existing FSM worker using that contact, if available;
* otherwise create a new FSM worker;
* link the FSM worker with the employee.

From Contacts
-------------

An existing contact can be converted into an OCA Field Service worker.

If the same contact is already used as the work contact of exactly one
employee, the new FSM worker is automatically linked to that employee.

If no employee exists, the contact becomes an external Field Service worker
without creating an HR employee.

From Field Service
------------------

When an FSM worker is created directly from Field Service, the module checks
whether its contact is already associated with an Odoo employee.

If there is one unambiguous matching employee, both records are linked
automatically.

Data Synchronization
====================

The module follows Odoo's existing data model wherever possible.

``res.partner`` remains the common source for contact information such as
name, email and mobile phone.

When an FSM worker is linked to an employee, the employee working calendar is
used for the Field Service worker.

Field Service-specific information remains managed by OCA Field Service,
including:

* Field Service teams
* Territories
* Worker categories
* Field Service orders

Archiving
=========

Historical Field Service data is preserved.

Disabling Field Service for an employee archives the corresponding FSM worker
instead of deleting it.

This prevents existing Field Service orders and historical assignments from
losing their worker reference.

Compatibility
=============

* Odoo Community Edition 18.0
* OCA Field Service 18.0

This module is specifically developed for the OCA ``fieldservice`` module. It
is not intended for Odoo Enterprise ``industry_fsm`` or unrelated third-party
Field Service applications.

License
=======

This module is licensed under the **GNU Affero General Public License v3.0
or later (AGPL-3.0-or-later)**.

It is free and open-source software.

Author
======

**Rolan Benavent Talens**

Credits
=======

This module integrates with the Field Service project maintained by the
**Odoo Community Association (OCA)**.

OCA Field Service:

::

    https://github.com/OCA/field-service

OCA:

::

    https://odoo-community.org/
