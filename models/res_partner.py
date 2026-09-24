# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    fsm_person_bridge_ids = fields.One2many(
        "fsm.person",
        "partner_id",
        string="Field Service Workers",
        readonly=True,
    )
    fsm_person_bridge_count = fields.Integer(
        string="Field Service Workers",
        compute="_compute_fsm_person_bridge_count",
    )

    @api.depends("fsm_person_bridge_ids")
    def _compute_fsm_person_bridge_count(self):
        worker_model = self.env["fsm.person"].sudo().with_context(active_test=False)
        workers = worker_model.search([("partner_id", "in", self.ids)])
        counts = {partner_id: 0 for partner_id in self.ids}
        for worker in workers:
            counts[worker.partner_id.id] = counts.get(worker.partner_id.id, 0) + 1
        for partner in self:
            partner.fsm_person_bridge_count = counts.get(partner.id, 0)

    def action_create_fsm_person_bridge(self):
        self.ensure_one()
        worker = (
            self.env["fsm.person"]
            .sudo()
            .with_context(active_test=False)
            .search([("partner_id", "=", self.id)], limit=1)
        )
        if not worker:
            worker = self.env["fsm.person"].create(
                {
                    "partner_id": self.id,
                    "mobile": self.mobile,
                }
            )
        elif not worker.active:
            worker.sudo().write({"active": True})
        return self._fsm_worker_action(worker)

    def action_open_fsm_person_bridge(self):
        self.ensure_one()
        worker = (
            self.env["fsm.person"]
            .sudo()
            .with_context(active_test=False)
            .search([("partner_id", "=", self.id)], limit=1)
        )
        if not worker:
            return False
        return self._fsm_worker_action(worker)

    def _fsm_worker_action(self, worker):
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

        if "mobile" in vals and not self.env.context.get(
            "fsm_hr_bridge_skip_worker_mobile"
        ):
            workers = (
                self.env["fsm.person"]
                .sudo()
                .with_context(active_test=False)
                .search([("partner_id", "in", self.ids)])
            )
            for worker in workers:
                mobile = worker.partner_id.mobile
                if worker.mobile != mobile:
                    worker.with_context(
                        fsm_hr_bridge_skip_partner_mobile=True
                    ).write({"mobile": mobile})

        if "name" in vals and not self.env.context.get(
            "fsm_hr_bridge_skip_employee_name_sync"
        ):
            workers = (
                self.env["fsm.person"]
                .sudo()
                .with_context(active_test=False)
                .search([("partner_id", "in", self.ids), ("employee_id", "!=", False)])
            )
            for employee in workers.mapped("employee_id"):
                if employee.name != employee.work_contact_id.name:
                    employee.with_context(
                        fsm_hr_bridge_skip_worker_sync=True
                    ).write({"name": employee.work_contact_id.name})

        return result
