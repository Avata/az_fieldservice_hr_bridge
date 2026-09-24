# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

{
    "name": "Field Service HR Bridge",
    "summary": "Link Field Service workers with Odoo employees and shared contacts",
    "version": "18.0.1.0.1",
    "category": "Field Service",
    "author": "Rolan Benavent Talens",
    "license": "AGPL-3",
    "depends": [
        "fieldservice",
        "hr",
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/hr_employee_views.xml",
        "views/fsm_person_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
