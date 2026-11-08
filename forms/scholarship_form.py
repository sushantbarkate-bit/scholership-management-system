from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    DecimalField,
    DateField,
    BooleanField,
    SelectField,
    SelectMultipleField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from wtforms.widgets import CheckboxInput, ListWidget

from services.constants import DOCUMENT_TYPES, ELIGIBILITY_FIELDS, OPERATORS


class ScholarshipForm(FlaskForm):

    name = StringField(
        "Scholarship name",
        validators=[DataRequired(), Length(min=3, max=200)]
    )

    provider = StringField(
        "Provider / authority",
        validators=[Optional(), Length(max=200)]
    )

    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=5000)]
    )

    scholarship_amount = DecimalField(
        "Scholarship amount (₹ per year)",
        places=2,
        validators=[Optional(), NumberRange(min=0, max=99999999)]
    )

    application_start_date = DateField(
        "Application start date",
        format="%Y-%m-%d",
        validators=[Optional()]
    )

    application_end_date = DateField(
        "Application deadline",
        format="%Y-%m-%d",
        validators=[Optional()]
    )

    is_active = BooleanField("Accept applications (active)", default=True)

    required_documents = SelectMultipleField(
        "Required documents",
        choices=DOCUMENT_TYPES,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )

    mandatory_documents = SelectMultipleField(
        "Mandatory among the above",
        choices=DOCUMENT_TYPES,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )

    submit = SubmitField("Save scholarship")


class EligibilityRuleForm(FlaskForm):

    criteria_key = SelectField(
        "Criterion",
        choices=[(key, meta[0]) for key, meta in ELIGIBILITY_FIELDS.items()],
        validators=[DataRequired()]
    )

    operator = SelectField(
        "Operator",
        choices=[(key, meta[0]) for key, meta in OPERATORS.items()],
        validators=[DataRequired()]
    )

    criteria_value = StringField(
        "Value",
        description="For lists, separate values with commas, e.g. OBC,SC,ST",
        validators=[DataRequired(), Length(max=255)]
    )

    submit = SubmitField("Add rule")
