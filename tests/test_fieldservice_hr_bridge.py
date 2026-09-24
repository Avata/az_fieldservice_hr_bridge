# Copyright 2026 Rolan Benavent Talens
# Author: Rolan Benavent Talens
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestFieldServiceHRBridge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Employee = cls.env["hr.employee"]
        cls.Worker = cls.env["fsm.person"]

    def _new_partner(self, name="FS Contact", mobile="600000001"):
        return self.Partner.create(
            {
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@example.com",
                "mobile": mobile,
            }
        )

    def _new_employee(self, partner, name="FS Employee"):
        return self.Employee.create(
            {
                "name": name,
                "company_id": self.env.company.id,
                "work_contact_id": partner.id,
            }
        )

    def test_partner_creates_external_worker_without_employee(self):
        partner = self._new_partner()
        employee_count_before = self.Employee.search_count([])
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        self.assertEqual(len(worker), 1)
        self.assertFalse(worker.employee_id)
        self.assertEqual(self.Employee.search_count([]), employee_count_before)
        self.assertTrue(partner.fsm_person)
        self.assertEqual(worker.mobile, partner.mobile)

    def test_standard_oca_conversion_auto_links_existing_employee(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        wizard = self.env["fsm.wizard"].create({"fsm_record_type": "person"})
        wizard.action_convert_person(partner)
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        self.assertEqual(worker.employee_id, employee)

    def test_partner_worker_auto_links_existing_employee(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        self.assertEqual(worker.employee_id, employee)

    def test_employee_created_after_worker_is_auto_linked(self):
        partner = self._new_partner()
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        self.assertFalse(worker.employee_id)
        employee = self._new_employee(partner)
        self.assertEqual(worker.employee_id, employee)

    def test_ambiguous_employee_contact_does_not_auto_link(self):
        partner = self._new_partner()
        self._new_employee(partner, name="Employee One")
        self._new_employee(partner, name="Employee Two")
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        self.assertFalse(worker.employee_id)

    def test_partner_name_does_not_rename_non_fsm_employee(self):
        partner = self._new_partner()
        employee = self._new_employee(partner, name="Independent Employee Name")
        partner.name = "Changed Contact Name"
        self.assertEqual(employee.name, "Independent Employee Name")

    def test_employee_toggle_creates_worker_on_same_contact(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        worker = self.Worker.with_context(active_test=False).search(
            [("employee_id", "=", employee.id)]
        )
        self.assertEqual(len(worker), 1)
        self.assertEqual(worker.partner_id, partner)
        self.assertTrue(worker.active)

    def test_employee_toggle_archives_and_reactivates_same_worker(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        worker = self.Worker.with_context(active_test=False).search(
            [("employee_id", "=", employee.id)]
        )
        employee.write({"is_fsm_worker": False})
        self.assertFalse(worker.active)
        employee.write({"is_fsm_worker": True})
        self.assertEqual(
            self.Worker.with_context(active_test=False).search_count(
                [("employee_id", "=", employee.id)]
            ),
            1,
        )
        self.assertTrue(worker.active)

    def test_partner_name_syncs_to_employee(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        partner.name = "Updated Contact Name"
        self.assertEqual(employee.name, "Updated Contact Name")

    def test_employee_name_syncs_to_partner(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        employee.name = "Updated Employee Name"
        self.assertEqual(partner.name, "Updated Employee Name")

    def test_partner_mobile_syncs_to_worker(self):
        partner = self._new_partner()
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        partner.mobile = "600999999"
        self.assertEqual(worker.mobile, "600999999")

    def test_worker_mobile_syncs_to_partner(self):
        partner = self._new_partner()
        partner.action_create_fsm_person_bridge()
        worker = self.Worker.with_context(active_test=False).search(
            [("partner_id", "=", partner.id)]
        )
        worker.mobile = "600888888"
        self.assertEqual(partner.mobile, "600888888")

    def test_employee_calendar_syncs_to_worker(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        worker = self.Worker.with_context(active_test=False).search(
            [("employee_id", "=", employee.id)]
        )
        calendar = self.env["resource.calendar"].create(
            {
                "name": "FSM Test Calendar",
                "company_id": self.env.company.id,
            }
        )
        employee.resource_calendar_id = calendar
        self.assertEqual(worker.calendar_id, calendar)

    def test_worker_calendar_syncs_to_employee(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        worker = self.Worker.with_context(active_test=False).search(
            [("employee_id", "=", employee.id)]
        )
        calendar = self.env["resource.calendar"].create(
            {
                "name": "FSM Reverse Test Calendar",
                "company_id": self.env.company.id,
            }
        )
        worker.calendar_id = calendar
        self.assertEqual(employee.resource_calendar_id, calendar)

    def test_archiving_employee_archives_worker(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        employee.write({"is_fsm_worker": True})
        worker = self.Worker.with_context(active_test=False).search(
            [("employee_id", "=", employee.id)]
        )
        employee.active = False
        self.assertFalse(worker.active)
        self.assertTrue(partner.active)

    def test_duplicate_partner_is_rejected(self):
        partner = self._new_partner()
        self.Worker.create({"partner_id": partner.id})
        with self.assertRaises(ValidationError):
            self.Worker.create({"partner_id": partner.id})

    def test_duplicate_employee_is_rejected(self):
        partner = self._new_partner()
        employee = self._new_employee(partner)
        self.Worker.create({"partner_id": partner.id, "employee_id": employee.id})
        second_partner = self._new_partner(name="Second Contact", mobile="600000002")
        employee.work_contact_id = second_partner
        with self.assertRaises(ValidationError):
            self.Worker.create(
                {"partner_id": second_partner.id, "employee_id": employee.id}
            )
