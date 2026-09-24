# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Link existing FSM workers to employees when the relation is unambiguous."""
    workers = env["fsm.person"].sudo().with_context(active_test=False).search([])
    linked = 0
    ambiguous = 0
    conflicts = 0

    for worker in workers:
        if worker.employee_id or not worker.partner_id:
            continue

        employees = (
            env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("work_contact_id", "=", worker.partner_id.id)], limit=2)
        )
        if len(employees) > 1:
            ambiguous += 1
            continue
        if not employees:
            continue

        employee = employees[0]
        existing = (
            env["fsm.person"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("employee_id", "=", employee.id),
                    ("id", "!=", worker.id),
                ],
                limit=1,
            )
        )
        if existing:
            conflicts += 1
            continue

        values = {"employee_id": employee.id}
        if employee.resource_calendar_id:
            values["calendar_id"] = employee.resource_calendar_id.id
        worker.with_context(fsm_hr_bridge_skip_employee_sync=True).write(values)

        if worker.partner_id.mobile:
            worker.with_context(fsm_hr_bridge_skip_partner_mobile=True).write(
                {"mobile": worker.partner_id.mobile}
            )
        elif worker.mobile:
            worker.partner_id.with_context(
                fsm_hr_bridge_skip_worker_mobile=True
            ).write({"mobile": worker.mobile})

        linked += 1

    _logger.info(
        "Field Service HR Bridge post-init: %s linked, %s ambiguous, %s conflicts",
        linked,
        ambiguous,
        conflicts,
    )
