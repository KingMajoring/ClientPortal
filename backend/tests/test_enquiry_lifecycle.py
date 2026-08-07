from datetime import date, datetime, timezone

from app.models.enquiry import EnquiryStatus
from app.models.job import DocumentType
from tests.conftest import login


def test_full_lifecycle_and_loa_generation(client, two_clients, app):
    from app.models.user import User
    from app.services import enquiry_service

    with app.app_context():
        admin_a = User.query.filter_by(email=two_clients["admin_a_email"]).first()
        wgtk = User.query.filter_by(email=two_clients["wgtk_general_email"]).first()
        enquiry = enquiry_service.create_enquiry(
            admin_a, two_clients["company_a_id"], {"vehicle_registration": "A1 XYZ"}
        )
        assert enquiry.status == EnquiryStatus.NEW

        enquiry = enquiry_service.send_quote(wgtk, enquiry, date.today(), True, 99.50)
        assert enquiry.status == EnquiryStatus.QUOTED

        enquiry = enquiry_service.accept_quote(admin_a, enquiry)
        assert enquiry.status == EnquiryStatus.ACCEPTED
        loa_docs = [d for d in enquiry.documents if d.document_type == DocumentType.LETTER_OF_AUTHORITY]
        assert len(loa_docs) == 1

        enquiry = enquiry_service.schedule(wgtk, enquiry, datetime.now(timezone.utc))
        assert enquiry.status == EnquiryStatus.SCHEDULED

        enquiry = enquiry_service.complete(wgtk, enquiry, "All done")
        assert enquiry.status == EnquiryStatus.COMPLETED
        assert len(enquiry.status_history) == 5  # NEW, QUOTED, ACCEPTED, SCHEDULED, COMPLETED


def test_price_decline_reopens_enquiry_instead_of_closing(client, two_clients, app):
    from app.models.enquiry import DeclineReasonType
    from app.models.user import User
    from app.services import enquiry_service

    with app.app_context():
        admin_a = User.query.filter_by(email=two_clients["admin_a_email"]).first()
        wgtk = User.query.filter_by(email=two_clients["wgtk_general_email"]).first()
        enquiry = enquiry_service.create_enquiry(
            admin_a, two_clients["company_a_id"], {"vehicle_registration": "A1 XYZ"}
        )
        enquiry = enquiry_service.send_quote(wgtk, enquiry, date.today(), True, 200.00)
        enquiry = enquiry_service.decline_by_client(admin_a, enquiry, DeclineReasonType.PRICE, "Too expensive")
        assert enquiry.status == EnquiryStatus.NEW


def test_other_decline_closes_enquiry(client, two_clients, app):
    from app.models.enquiry import DeclineReasonType
    from app.models.user import User
    from app.services import enquiry_service

    with app.app_context():
        admin_a = User.query.filter_by(email=two_clients["admin_a_email"]).first()
        wgtk = User.query.filter_by(email=two_clients["wgtk_general_email"]).first()
        enquiry = enquiry_service.create_enquiry(
            admin_a, two_clients["company_a_id"], {"vehicle_registration": "A1 XYZ"}
        )
        enquiry = enquiry_service.send_quote(wgtk, enquiry, date.today(), True, 200.00)
        enquiry = enquiry_service.decline_by_client(admin_a, enquiry, DeclineReasonType.OTHER, "Changed our minds")
        assert enquiry.status == EnquiryStatus.DECLINED_BY_CLIENT
