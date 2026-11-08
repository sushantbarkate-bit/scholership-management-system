from datetime import date

from flask import Blueprint, Response, render_template, request

from routes.decorators import admin_required
from services import report_service as reports
from services.constants import CATEGORY_CHOICES, APPLICATION_STATUSES


report_bp = Blueprint("report", __name__, url_prefix="/admin/reports")


def _filters_from_request():
    scholarship_id = request.args.get("scholarship_id", type=int)
    category = request.args.get("category", "").strip()
    return {
        "date_from": reports.parse_date(request.args.get("date_from", "")),
        "date_to": reports.parse_date(request.args.get("date_to", "")),
        "scholarship_id": scholarship_id,
        "category": category if category in CATEGORY_CHOICES else "",
    }


@report_bp.route("/")
@admin_required
def index():
    filters = _filters_from_request()
    data = reports.application_report(filters)

    return render_template(
        "admin/reports.html",
        data=data,
        filters=filters,
        raw_filters={
            "date_from": request.args.get("date_from", ""),
            "date_to": request.args.get("date_to", ""),
        },
        scholarships=reports.scholarship_choices(),
        categories=CATEGORY_CHOICES,
        students_total=reports.student_registration_total(filters),
        course_breakdown=reports.students_by_course(),
        document_breakdown=reports.document_report(),
        statuses=APPLICATION_STATUSES,
        generated_on=date.today(),
        printable=request.args.get("print") == "1",
    )


@report_bp.route("/export.csv")
@admin_required
def export_csv():
    csv_text = reports.applications_csv(_filters_from_request())
    filename = f"applications_{date.today().isoformat()}.csv"
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
