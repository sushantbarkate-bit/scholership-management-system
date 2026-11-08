from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

from services.constants import APPLICATION_STATUSES, DOCUMENT_STATUSES, DOCUMENT_TYPES


class DocumentUploadForm(FlaskForm):

    document_type = SelectField(
        "Document type",
        choices=DOCUMENT_TYPES,
        validators=[DataRequired()]
    )

    file = FileField(
        "File (PDF, JPG or PNG, max 5 MB)",
        validators=[FileRequired()]
    )

    submit = SubmitField("Upload")


class ApplicationReviewForm(FlaskForm):

    status = SelectField(
        "New status",
        choices=[(k, v[0]) for k, v in APPLICATION_STATUSES.items()
                 if k not in ("draft", "submitted")],
        validators=[DataRequired()]
    )

    remarks = TextAreaField(
        "Remarks (shown to the student)",
        validators=[Length(max=2000)]
    )

    submit = SubmitField("Update status")


class DocumentReviewForm(FlaskForm):

    status = SelectField(
        "Decision",
        choices=[(k, v[0]) for k, v in DOCUMENT_STATUSES.items() if k != "pending"],
        validators=[DataRequired()]
    )

    remarks = TextAreaField(
        "Remarks for the student",
        validators=[Length(max=2000)]
    )

    submit = SubmitField("Save decision")
