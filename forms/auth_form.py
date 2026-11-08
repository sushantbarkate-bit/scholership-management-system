from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class ChangePasswordForm(FlaskForm):

    current_password = PasswordField(
        "Current password",
        validators=[DataRequired()]
    )

    new_password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, max=128)]
    )

    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match.")
        ]
    )

    submit = SubmitField("Change password")
