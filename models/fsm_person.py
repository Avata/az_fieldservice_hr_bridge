# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMPerson(models.Model):
    _inherit = "fsm.person"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        index=True,
        copy=False,
        ondelete="set null",
        help=(
            "Employee linked to this Field Service worker. The employee and the "
            "worker must use the same work contact. External workers can remain "
            "without an employee."
        ),
    )

    @api.model
    def _find_employee_for_partner(self, partner):
        """Return the unique employee using ``partner`` as work contact.

        ``hr.employee`` contains private HR information, so this helper always
        searches with sudo. If more than one employee uses the same work contact,
        the relationship is ambiguous and no employee is selected automatically.
        """
        if not partner:
            return self.env["hr.employee"]
        employees = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("work_contact_id", "=", partner.id)], limit=2)
        )
        return employees if len(employees) == 1 else self.env["hr.employee"]

    @api.model
    def _ensure_employee_work_contact(self, employee):
        """Ensure an employee has a work contact and return it."""
        employee = employee.sudo()
        if not employee.work_contact_id:
            employee._create_work_contacts()
        return employee.work_contact_id

    def _sync_partner_mobile_from_worker(self):
        """Keep the OCA worker-specific mobile aligned with the shared partner."""
        for worker in self:
            if worker.partner_id.mobile != worker.mobile:
                worker.partner_id.with_context(
                    fsm_hr_bridge_skip_worker_mobile=True
                ).write({"mobile": worker.mobile})

    def _sync_worker_mobile_from_partner(self):
        """Use the partner mobile as the canonical contact mobile."""
        for worker in self:
            mobile = worker.partner_id.mobile
            if worker.mobile != mobile:
                super(FSMPerson, worker.with_context(
                    fsm_hr_bridge_skip_partner_mobile=True
                )).write({"mobile": mobile})

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        explicit_employee_ids = []

        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            employee = self.env["hr.employee"]
            employee_id = vals.get("employee_id")
            if employee_id:
                employee = self.env["hr.employee"].sudo().browse(employee_id).exists()
                if not employee:
                    raise ValidationError(_("The selected employee does not exist."))
                work_contact = self._ensure_employee_work_contact(employee)
                partner_id = vals.get("partner_id")
                if partner_id and partner_id != work_contact.id:
                    raise ValidationError(
                        _(
                            "The Field Service worker and the employee must use "
                            "the same work contact."
                        )
                    )
                vals["partner_id"] = work_contact.id
                if employee.resource_calendar_id and not vals.get("calendar_id"):
                    vals["calendar_id"] = employee.resource_calendar_id.id
                if "mobile" not in vals:
                    vals["mobile"] = work_contact.mobile

            prepared_vals_list.append(vals)
            explicit_employee_ids.append(employee.id if employee else False)

        workers = super().create(prepared_vals_list)

        for worker, explicit_employee_id in zip(workers, explicit_employee_ids):
            employee = (
                self.env["hr.employee"].sudo().browse(explicit_employee_id)
                if explicit_employee_id
                else worker._find_employee_for_partner(worker.partner_id)
            )

            if employee and not worker.employee_id:
                existing = (
                    self.sudo()
                    .with_context(active_test=False)
                    .search(
                        [
                            ("employee_id", "=", employee.id),
                            ("id", "!=", worker.id),
                        ],
                        limit=1,
                    )
                )
                if not existing:
                    sync_vals = {"employee_id": employee.id}
                    if employee.resource_calendar_id:
                        sync_vals["calendar_id"] = employee.resource_calendar_id.id
                    worker.sudo().with_context(
                        fsm_hr_bridge_skip_employee_sync=True
                    ).write(sync_vals)

            # Partner is the canonical contact record for mobile data.
            if worker.partner_id.mobile:
                worker._sync_worker_mobile_from_partner()
            elif worker.mobile:
                worker._sync_partner_mobile_from_worker()

        return workers

    def write(self, vals):
        vals = dict(vals)

        if "employee_id" in vals and vals.get("employee_id"):
            employee = self.env["hr.employee"].sudo().browse(vals["employee_id"]).exists()
            if not employee:
                raise ValidationError(_("The selected employee does not exist."))
            work_contact = self._ensure_employee_work_contact(employee)
            for worker in self:
                if worker.partner_id != work_contact:
                    raise ValidationError(
                        _(
                            "The selected employee uses a different work contact. "
                            "Link the employee to this contact first."
                        )
                    )

        result = super().write(vals)

        if "mobile" in vals and not self.env.context.get(
            "fsm_hr_bridge_skip_partner_mobile"
        ):
            self._sync_partner_mobile_from_worker()

        if "calendar_id" in vals and not self.env.context.get(
            "fsm_hr_bridge_skip_employee_sync"
        ):
            for worker in self.sudo().filtered("employee_id"):
                calendar = worker.calendar_id
                if worker.employee_id.resource_calendar_id != calendar:
                    worker.employee_id.with_context(
                        fsm_hr_bridge_skip_worker_sync=True
                    ).write({"resource_calendar_id": calendar.id or False})

        return result

    def unlink(self):
        partners = self.mapped("partner_id")
        result = super().unlink()
        for partner in partners:
            remaining = (
                self.env["fsm.person"]
                .sudo()
                .with_context(active_test=False)
                .search_count([("partner_id", "=", partner.id)])
            )
            if not remaining and partner.fsm_person:
                partner.with_context(fsm_hr_bridge_skip_worker_creation=True).write(
                    {"fsm_person": False}
                )
        return result

    @api.constrains("partner_id")
    def _check_unique_partner(self):
        for worker in self:
            if not worker.partner_id:
                continue
            duplicate = (
                self.sudo()
                .with_context(active_test=False)
                .search_count(
                    [
                        ("partner_id", "=", worker.partner_id.id),
                        ("id", "!=", worker.id),
                    ]
                )
            )
            if duplicate:
                raise ValidationError(
                    _("A Field Service worker already exists for this contact.")
                )

    @api.constrains("employee_id")
    def _check_unique_employee(self):
        for worker in self.filtered("employee_id"):
            duplicate = (
                self.sudo()
                .with_context(active_test=False)
                .search_count(
                    [
                        ("employee_id", "=", worker.employee_id.id),
                        ("id", "!=", worker.id),
                    ]
                )
            )
            if duplicate:
                raise ValidationError(
                    _("This employee is already linked to another Field Service worker.")
                )

    @api.constrains("employee_id", "partner_id")
    def _check_employee_partner(self):
        for worker in self.filtered("employee_id"):
            if worker.employee_id.sudo().work_contact_id != worker.partner_id:
                raise ValidationError(
                    _(
                        "The Field Service worker and the linked employee must "
                        "share the same work contact."
                    )
                )
