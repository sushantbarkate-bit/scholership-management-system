from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    DateField,
    SelectField,
    DecimalField,
    TextAreaField,
    SubmitField
)

from wtforms.validators import (
    DataRequired,
    Optional,
    Length,
    NumberRange,
    Regexp
)


class StudentProfileForm(FlaskForm):

    mobile = StringField(
        "Mobile Number",
        validators=[
            DataRequired(),
            Regexp(r"^[6-9]\d{9}$",
                   message="Enter a valid 10-digit mobile number.")
        ]
    )

    date_of_birth = DateField(
        "Date of Birth",
        format="%Y-%m-%d",
        validators=[Optional()]
    )

    gender = SelectField(
        "Gender",
        choices=[
            ("", "Select Gender"),
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other")
        ],
        validators=[DataRequired()]
    )

    address = TextAreaField(
        "Address",
        validators=[DataRequired()]
    )

    city = StringField(
        "City",
        validators=[DataRequired(), Length(max=100)]
    )

    district = StringField(
        "District",
        validators=[DataRequired(), Length(max=100)]
    )

    state = StringField(
        "State",
        default="Maharashtra",
        validators=[DataRequired()]
    )

    pincode = StringField(
        "Pincode",
        validators=[
            DataRequired(),
            Regexp(r"^\d{6}$", message="Enter a valid 6-digit pincode.")
        ]
    )

    category = SelectField(
        "Category",
        choices=[
            ("", "Select Category"),
            ("OPEN", "OPEN"),
            ("OBC", "OBC"),
            ("SC", "SC"),
            ("ST", "ST"),
            ("VJNT", "VJNT"),
            ("SBC", "SBC"),
            ("EWS", "EWS")
        ],
        validators=[DataRequired()]
    )

    annual_income = DecimalField(
        "Annual Family Income",
        validators=[
            DataRequired(),
            NumberRange(min=0, max=999999999999.99)
        ],
        places=2
    )

    course = StringField(
        "Course",
        validators=[DataRequired()]
    )

    college_name = StringField(
        "College Name",
        validators=[DataRequired()]
    )

    university_name = StringField(
        "University Name",
        validators=[DataRequired()]
    )

    academic_year = StringField(
        "Academic Year",
        validators=[DataRequired()]
    )

    academic_percentage = DecimalField(
        "Academic Percentage",
        validators=[
            DataRequired(),
            NumberRange(min=0, max=100)
        ],
        places=2
    )

    submit = SubmitField("Save Profile")