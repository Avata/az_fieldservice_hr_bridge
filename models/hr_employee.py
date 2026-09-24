# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    fsm_person_ids = fields.One2many(
        "fsm.person",
        "employee_id",
        string="Field Service Workers",
        groups="hr.group_hr_user",
    )
    fsm_person_id = fields.Many2one(
        "fsm.person",
        string="Field Service Worker",
        compute="_compute_fsm_fields",
        groups="hr.group_hr_user",
    )
    fsm_person_count = fields.Integer(
        string="Field Service Workers",
        compute="_compute_fsm_fields",
        groups="hr.group_hr_user",
    )
    is_fsm_worker = fields.Boolean(
        string="Field Service Worker",
        compute="_compute_is_fsm_worker",
        inverse="_inverse_is_fsm_worker",
        groups="hr.group_hr_user",
        help=(
            "Enable this option to create or reactivate the Field Service worker "
            "linked to this employee. Disabling it archives the Field Service "
            "worker but never deletes it."
        ),
    )

    def _all_fsm_workers(self):
        self.ensure_one()
        return (
            self.env["fsm.person"]
            .sudo()
            .with_context(active_test=False)
            .search([("employee_id", "=", self.id)], order="id")
        )

    @api.depends("fsm_person_ids", "fsm_person_ids.active")
    def _compute_fsm_fields(self):
        worker_model = self.env["fsm.person"].sudo().with_context(active_test=False)
        workers = worker_model.search([("employee_id", "in", self.ids)], order="id")
        grouped = {employee_id: [] for employee_id in self.ids}
        for worker in workers:
            grouped.setdefault(worker.employee_id.id, []).append(worker)
        for employee in self:
            employee_workers = grouped.get(employee.id, [])
            employee.fsm_person_count = len(employee_workers)
            employee.fsm_person_id = employee_workers[0] if employee_workers else False

    @api.depends("fsm_person_ids", "fsm_person_ids.active")
    def _compute_is_fsm_worker(self):
        worker_model = self.env["fsm.person"].sudo().with_context(active_test=False)
        active_workers = worker_model.search(
            [("employee_id", "in", self.ids), ("active", "=", True)]
        )
        active_employee_ids = set(active_workers.mapped("employee_id").ids)
        for employee in self:
            employee.is_fsm_worker = employee.id in active_employee_ids

    def _ensure_work_contact_for_fsm(self):
        self.ensure_one()
        employee = self.sudo()
        if not employee.work_contact_id:
            employee._create_work_contacts()
        return employee.work_contact_id


    def _link_existing_fsm_worker_from_work_contact(self):
        """Link an existing external FSM worker when the match is unambiguous."""
        self.ensure_one()
        employee = self.sudo()
        if not employee.work_contact_id or employee._all_fsm_workers():
            return self.env["fsm.person"]

        employees_using_contact = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("work_contact_id", "=", employee.work_contact_id.id)], limit=2)
        )
        if len(employees_using_contact) != 1 or employees_using_contact != employee:
            return self.env["fsm.person"]

        workers = (
            self.env["fsm.person"]
            .sudo()
            .with_context(active_test=False)
            .search([("partner_id", "=", employee.work_contact_id.id)], limit=2)
        )
        if len(workers) != 1:
            return self.env["fsm.person"]

        worker = workers[0]
        if worker.employee_id and worker.employee_id != employee:
            return self.env["fsm.person"]

        values = {"employee_id": employee.id}
        if employee.resource_calendar_id:
            values["calendar_id"] = employee.resource_calendar_id.id
        worker.with_context(fsm_hr_bridge_skip_employee_sync=True).write(values)
        return worker

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if not self.env.context.get("fsm_hr_bridge_skip_worker_sync"):
            for employee in employees:
                employee._link_existing_fsm_worker_from_work_contact()
        return employees

    def _inverse_is_fsm_worker(self):
        for employee in self:
            workers = employee._all_fsm_workers()
            if employee.is_fsm_worker:
                work_contact = employee._ensure_work_contact_for_fsm()
                if workers:
                    worker = workers[0]
                    values = {}
                    if not worker.active:
                        values["active"] = True
                    if employee.resource_calendar_id != worker.calendar_id:
                        values["calendar_id"] = employee.resource_calendar_id.id or False
                    if values:
                        worker.sudo().with_context(
                            fsm_hr_bridge_skip_employee_sync=True
                        ).write(values)
                    if worker.partner_id != work_contact:
                        raise ValidationError(
                            _(
                                "The existing Field Service worker is linked to a "
                                "different contact."
                            )
                        )
                else:
                    existing_partner_worker = (
                        self.env["fsm.person"]
                        .sudo()
                        .with_context(active_test=False)
                        .search([("partner_id", "=", work_contact.id)], limit=1)
                    )
                    if existing_partner_worker:
                        if existing_partner_worker.employee_id and (
                            existing_partner_worker.employee_id != employee
                        ):
                            raise ValidationError(
                                _(
                                    "The employee work contact is already linked to "
                                    "another employee's Field Service worker."
                                )
                            )
                        existing_partner_worker.write(
                            {
                                "employee_id": employee.id,
                                "active": True,
                                "calendar_id": employee.resource_calendar_id.id
                                or False,
                            }
                        )
                    else:
                        self.env["fsm.person"].sudo().create(
                            {
                                "partner_id": work_contact.id,
                                "employee_id": employee.id,
                                "calendar_id": employee.resource_calendar_id.id
                                or False,
                                "mobile": work_contact.mobile,
                            }
                        )
            else:
                workers.filtered("active").sudo().write({"active": False})

    def action_open_fsm_person(self):
        self.ensure_one()
        worker = self._all_fsm_workers()[:1]
        if not worker:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Field Service Worker"),
            "res_model": "fsm.person",
            "view_mode": "form",
            "res_id": worker.id,
            "target": "current",
            "context": {"active_test": False},
        }

    def write(self, vals):
        result = super().write(vals)

        if self.env.context.get("fsm_hr_bridge_skip_worker_sync"):
            return result

        for employee in self:
            workers = employee._all_fsm_workers()
            if not workers and "work_contact_id" in vals:
                employee._link_existing_fsm_worker_from_work_contact()
                workers = employee._all_fsm_workers()
            if not workers:
                continue

            if "work_contact_id" in vals:
                new_contact = employee.work_contact_id
                if not new_contact:
                    raise ValidationError(
                        _(
                            "An employee linked to Field Service must have a work "
                            "contact."
                        )
                    )
                conflicting_worker = (
                    self.env["fsm.person"]
                    .sudo()
                    .with_context(active_test=False)
                    .search(
                        [
                            ("partner_id", "=", new_contact.id),
                            ("employee_id", "!=", employee.id),
                        ],
                        limit=1,
                    )
                )
                if conflicting_worker:
                    raise ValidationError(
                        _(
                            "The new work contact already belongs to another Field "
                            "Service worker."
                        )
                    )
                for worker in workers:
                    old_partner = worker.partner_id
                    worker.sudo().with_context(
                        fsm_hr_bridge_skip_employee_sync=True
                    ).write(
                        {
                            "partner_id": new_contact.id,
                            "mobile": new_contact.mobile,
                        }
                    )
                    if old_partner != new_contact:
                        remaining = (
                            self.env["fsm.person"]
                            .sudo()
                            .with_context(active_test=False)
                            .search_count([("partner_id", "=", old_partner.id)])
                        )
                        if not remaining and old_partner.fsm_person:
                            old_partner.with_context(
                                fsm_hr_bridge_skip_worker_creation=True
                            ).write({"fsm_person": False})
                    if not new_contact.fsm_person:
                        new_contact.with_context(
                            fsm_hr_bridge_skip_worker_creation=True
                        ).write({"fsm_person": True})

            if "resource_calendar_id" in vals:
                workers.sudo().with_context(
                    fsm_hr_bridge_skip_employee_sync=True
                ).write(
                    {
                        "calendar_id": employee.resource_calendar_id.id or False,
                    }
                )

            if "active" in vals:
                if employee.active:
                    # Reactivate only an already-linked worker; never create a new one.
                    workers.filtered(lambda worker: not worker.active).sudo().write(
                        {"active": True}
                    )
                else:
                    workers.filtered("active").sudo().write({"active": False})

            if "name" in vals and employee.work_contact_id:
                employee.work_contact_id.with_context(
                    fsm_hr_bridge_skip_employee_name_sync=True
                ).write({"name": employee.name})

        return result
