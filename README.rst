Field Service HR Bridge
=======================

This free module links OCA Field Service workers (``fsm.person``) with Odoo
employees (``hr.employee``) through the employee work contact
(``res.partner``).

Main features
-------------

* Create a Field Service worker from a contact without creating an employee.
* Automatically link the worker when that contact is already an employee work contact.
* Enable or disable Field Service status from the employee form.
* Keep one employee linked to at most one Field Service worker.
* Keep one contact linked to at most one Field Service worker.
* Synchronize shared identity/contact data through ``res.partner``.
* Synchronize the Field Service worker mobile with the contact mobile.
* Synchronize employee and Field Service working schedules.
* Archive the Field Service worker when the employee is archived, without
  deleting historical records or archiving the contact.
* Smart navigation between Contacts, Employees and Field Service Workers.
* Link existing records automatically on installation when the match is unique.

License
-------

AGPL-3.0 or later.

Author
------

Rolan Benavent Talens
