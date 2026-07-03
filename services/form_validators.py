"""Form validation utilities for reducing boilerplate validation code."""

import datetime


class FormValidator:
    """Utility class for form validation with error collection.

    Example usage:
        validator = FormValidator(request.form)
        description = validator.required('description', 'Description is required')
        price = validator.parse_float('price', 'Price must be a valid number')
        quantity = validator.parse_int('quantity', 'Quantity must be a valid number')

        if not validator.is_valid():
            for error in validator.errors:
                flash(error, 'danger')
            return render_template(...)
    """

    def __init__(self, form_data):
        """Initialize with form data (typically request.form.to_dict())."""
        self.form_data = form_data if isinstance(form_data, dict) else form_data.to_dict()
        self.errors = []
        self.values = {}

    def required(self, field, error_message=None):
        """Validate that a field is present and non-empty.

        Args:
            field: Form field name
            error_message: Custom error message (default: "{field} is required")

        Returns:
            Stripped string value or None if validation failed
        """
        value = self.form_data.get(field, '').strip()
        if not value:
            self.errors.append(error_message or f'{field.replace("_", " ").title()} is required.')
            return None
        self.values[field] = value
        return value

    def optional(self, field, default=None, max_length=None):
        """Get an optional field value.

        Args:
            field: Form field name
            default: Default value if field is empty
            max_length: Optional max length to truncate to

        Returns:
            Stripped string value, truncated if max_length specified, or default
        """
        value = self.form_data.get(field, '').strip()
        if not value:
            return default
        if max_length:
            value = value[:max_length]
        self.values[field] = value
        return value

    def parse_float(self, field, error_message=None, required=False):
        """Parse a field as a float.

        Args:
            field: Form field name
            error_message: Custom error message
            required: Whether the field is required

        Returns:
            Float value or None
        """
        value = self.form_data.get(field, '').strip()
        if not value:
            if required:
                self.errors.append(error_message or f'{field.replace("_", " ").title()} is required.')
            return None
        try:
            result = float(value)
            self.values[field] = result
            return result
        except ValueError:
            self.errors.append(error_message or f'{field.replace("_", " ").title()} must be a valid number.')
            return None

    def parse_int(self, field, error_message=None, required=False, min_value=None, max_value=None, range_error=None):
        """Parse a field as an integer with optional range validation.

        Args:
            field: Form field name
            error_message: Custom error message for parse failures
            required: Whether the field is required
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            range_error: Custom error message for out-of-range values

        Returns:
            Integer value or None
        """
        value = self.form_data.get(field, '').strip()
        if not value:
            if required:
                self.errors.append(error_message or f'{field.replace("_", " ").title()} is required.')
            return None
        try:
            result = int(value)
            if min_value is not None and result < min_value:
                self.errors.append(range_error or f'{field.replace("_", " ").title()} must be at least {min_value}.')
                return None
            if max_value is not None and result > max_value:
                self.errors.append(range_error or f'{field.replace("_", " ").title()} must be at most {max_value}.')
                return None
            self.values[field] = result
            return result
        except ValueError:
            self.errors.append(error_message or f'{field.replace("_", " ").title()} must be a valid number.')
            return None

    def choice(self, field, valid_choices, default=None, error_message=None):
        """Validate that a field value is in a set of valid choices.

        Args:
            field: Form field name
            valid_choices: List/set of valid values
            default: Default value if not in choices
            error_message: Custom error message

        Returns:
            The value if valid, default otherwise
        """
        value = self.form_data.get(field, '').strip()
        if value in valid_choices:
            self.values[field] = value
            return value
        if default is not None:
            return default
        if error_message:
            self.errors.append(error_message)
        return None

    def is_valid(self):
        """Check if validation passed with no errors."""
        return len(self.errors) == 0

    def first_error(self):
        """Get the first error message, or None if no errors."""
        return self.errors[0] if self.errors else None

    def parse_date(self, field, date_format='%Y-%m-%d', error_message=None, required=False, format_error=None):
        """Parse a field as a date.

        Args:
            field: Form field name
            date_format: Expected date format (default: YYYY-MM-DD)
            error_message: Custom error message for required check
            required: Whether the field is required
            format_error: Custom error message for invalid format

        Returns:
            datetime.date value or None
        """
        value = self.form_data.get(field, '').strip()
        if not value:
            if required:
                self.errors.append(error_message or f'{field.replace("_", " ").title()} is required.')
            return None
        try:
            result = datetime.datetime.strptime(value, date_format).date()
            self.values[field] = result
            return result
        except ValueError:
            self.errors.append(format_error or 'Invalid date format. Please use YYYY-MM-DD.')
            return None
