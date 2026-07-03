"""Tests for the FormValidator class."""
import datetime

import pytest

from services.form_validators import FormValidator


class TestFormValidatorInit:
    """Tests for FormValidator initialization."""

    def test_init_with_dict(self):
        """Should accept a dictionary directly."""
        form_data = {'name': 'Test', 'email': 'test@example.com'}
        validator = FormValidator(form_data)
        assert validator.form_data == form_data
        assert validator.errors == []
        assert validator.values == {}

    def test_init_with_immutable_dict(self, app):
        """Should convert ImmutableMultiDict to regular dict."""
        with app.test_request_context(method='POST', data={'field': 'value'}):
            from flask import request
            validator = FormValidator(request.form)
            assert isinstance(validator.form_data, dict)
            assert validator.form_data.get('field') == 'value'


class TestRequired:
    """Tests for the required() method."""

    def test_required_with_valid_value(self):
        """Should return value when field is present and non-empty."""
        validator = FormValidator({'name': 'Test User'})
        result = validator.required('name')
        assert result == 'Test User'
        assert validator.is_valid()
        assert validator.values['name'] == 'Test User'

    def test_required_with_empty_string(self):
        """Should add error when field is empty string."""
        validator = FormValidator({'name': ''})
        result = validator.required('name')
        assert result is None
        assert not validator.is_valid()
        assert 'Name is required.' in validator.errors

    def test_required_with_whitespace_only(self):
        """Should add error when field contains only whitespace."""
        validator = FormValidator({'name': '   '})
        result = validator.required('name')
        assert result is None
        assert not validator.is_valid()

    def test_required_with_missing_field(self):
        """Should add error when field is missing."""
        validator = FormValidator({})
        result = validator.required('name')
        assert result is None
        assert not validator.is_valid()

    def test_required_with_custom_error_message(self):
        """Should use custom error message when provided."""
        validator = FormValidator({'name': ''})
        validator.required('name', 'Please enter your name.')
        assert 'Please enter your name.' in validator.errors

    def test_required_strips_whitespace(self):
        """Should strip leading/trailing whitespace from value."""
        validator = FormValidator({'name': '  Test User  '})
        result = validator.required('name')
        assert result == 'Test User'


class TestOptional:
    """Tests for the optional() method."""

    def test_optional_with_value(self):
        """Should return value when field is present."""
        validator = FormValidator({'notes': 'Some notes'})
        result = validator.optional('notes')
        assert result == 'Some notes'
        assert validator.values['notes'] == 'Some notes'

    def test_optional_with_empty_returns_default(self):
        """Should return default when field is empty."""
        validator = FormValidator({'notes': ''})
        result = validator.optional('notes', default='No notes')
        assert result == 'No notes'

    def test_optional_with_missing_field_returns_default(self):
        """Should return default when field is missing."""
        validator = FormValidator({})
        result = validator.optional('notes', default='Default')
        assert result == 'Default'

    def test_optional_with_none_default(self):
        """Should return None when default is not specified."""
        validator = FormValidator({})
        result = validator.optional('notes')
        assert result is None

    def test_optional_with_max_length(self):
        """Should truncate value to max_length."""
        validator = FormValidator({'notes': 'This is a very long note'})
        result = validator.optional('notes', max_length=10)
        assert result == 'This is a '
        assert len(result) == 10

    def test_optional_max_length_on_short_value(self):
        """Should not truncate value shorter than max_length."""
        validator = FormValidator({'notes': 'Short'})
        result = validator.optional('notes', max_length=100)
        assert result == 'Short'

    def test_optional_never_adds_errors(self):
        """Optional fields should never add validation errors."""
        validator = FormValidator({})
        validator.optional('notes')
        assert validator.is_valid()


class TestParseFloat:
    """Tests for the parse_float() method."""

    def test_parse_float_valid_number(self):
        """Should parse valid float string."""
        validator = FormValidator({'price': '19.99'})
        result = validator.parse_float('price')
        assert result == 19.99
        assert validator.values['price'] == 19.99

    def test_parse_float_integer_string(self):
        """Should parse integer string as float."""
        validator = FormValidator({'price': '100'})
        result = validator.parse_float('price')
        assert result == 100.0

    def test_parse_float_invalid_format(self):
        """Should add error for invalid format."""
        validator = FormValidator({'price': 'not a number'})
        result = validator.parse_float('price')
        assert result is None
        assert not validator.is_valid()
        assert 'Price must be a valid number.' in validator.errors

    def test_parse_float_empty_not_required(self):
        """Should return None without error when empty and not required."""
        validator = FormValidator({'price': ''})
        result = validator.parse_float('price')
        assert result is None
        assert validator.is_valid()

    def test_parse_float_empty_required(self):
        """Should add error when empty and required."""
        validator = FormValidator({'price': ''})
        result = validator.parse_float('price', required=True)
        assert result is None
        assert not validator.is_valid()
        assert 'Price is required.' in validator.errors

    def test_parse_float_custom_error_message(self):
        """Should use custom error message."""
        validator = FormValidator({'price': 'abc'})
        validator.parse_float('price', 'Enter a valid price.')
        assert 'Enter a valid price.' in validator.errors

    def test_parse_float_with_whitespace(self):
        """Should handle whitespace around number."""
        validator = FormValidator({'price': '  29.99  '})
        result = validator.parse_float('price')
        assert result == 29.99

    def test_parse_float_negative_number(self):
        """Should parse negative numbers."""
        validator = FormValidator({'price': '-10.50'})
        result = validator.parse_float('price')
        assert result == -10.50


class TestParseInt:
    """Tests for the parse_int() method."""

    def test_parse_int_valid_number(self):
        """Should parse valid integer string."""
        validator = FormValidator({'quantity': '5'})
        result = validator.parse_int('quantity')
        assert result == 5
        assert validator.values['quantity'] == 5

    def test_parse_int_invalid_format(self):
        """Should add error for invalid format."""
        validator = FormValidator({'quantity': 'three'})
        result = validator.parse_int('quantity')
        assert result is None
        assert 'Quantity must be a valid number.' in validator.errors

    def test_parse_int_float_string_fails(self):
        """Should fail for float string."""
        validator = FormValidator({'quantity': '5.5'})
        result = validator.parse_int('quantity')
        assert result is None
        assert not validator.is_valid()

    def test_parse_int_empty_not_required(self):
        """Should return None without error when empty and not required."""
        validator = FormValidator({'quantity': ''})
        result = validator.parse_int('quantity')
        assert result is None
        assert validator.is_valid()

    def test_parse_int_empty_required(self):
        """Should add error when empty and required."""
        validator = FormValidator({'quantity': ''})
        result = validator.parse_int('quantity', required=True)
        assert result is None
        assert 'Quantity is required.' in validator.errors

    def test_parse_int_min_value_pass(self):
        """Should pass when value meets minimum."""
        validator = FormValidator({'quantity': '5'})
        result = validator.parse_int('quantity', min_value=1)
        assert result == 5
        assert validator.is_valid()

    def test_parse_int_min_value_fail(self):
        """Should fail when value below minimum."""
        validator = FormValidator({'quantity': '0'})
        result = validator.parse_int('quantity', min_value=1)
        assert result is None
        assert 'Quantity must be at least 1.' in validator.errors

    def test_parse_int_max_value_pass(self):
        """Should pass when value meets maximum."""
        validator = FormValidator({'quantity': '10'})
        result = validator.parse_int('quantity', max_value=100)
        assert result == 10
        assert validator.is_valid()

    def test_parse_int_max_value_fail(self):
        """Should fail when value exceeds maximum."""
        validator = FormValidator({'quantity': '101'})
        result = validator.parse_int('quantity', max_value=100)
        assert result is None
        assert 'Quantity must be at most 100.' in validator.errors

    def test_parse_int_range_validation(self):
        """Should validate both min and max."""
        validator = FormValidator({'quantity': '5'})
        result = validator.parse_int('quantity', min_value=1, max_value=10)
        assert result == 5
        assert validator.is_valid()

    def test_parse_int_custom_range_error(self):
        """Should use custom range error message."""
        validator = FormValidator({'quantity': '0'})
        validator.parse_int('quantity', min_value=1, range_error='Must be positive.')
        assert 'Must be positive.' in validator.errors

    def test_parse_int_negative_number(self):
        """Should parse negative integers."""
        validator = FormValidator({'quantity': '-5'})
        result = validator.parse_int('quantity')
        assert result == -5


class TestParseDate:
    """Tests for the parse_date() method."""

    def test_parse_date_valid_format(self):
        """Should parse date in YYYY-MM-DD format."""
        validator = FormValidator({'date': '2025-12-25'})
        result = validator.parse_date('date')
        assert result == datetime.date(2025, 12, 25)
        assert validator.values['date'] == result

    def test_parse_date_invalid_format(self):
        """Should add error for invalid date format."""
        validator = FormValidator({'date': '12-25-2025'})
        result = validator.parse_date('date')
        assert result is None
        assert 'Invalid date format. Please use YYYY-MM-DD.' in validator.errors

    def test_parse_date_invalid_date(self):
        """Should add error for invalid date value."""
        validator = FormValidator({'date': '2025-02-30'})
        result = validator.parse_date('date')
        assert result is None
        assert not validator.is_valid()

    def test_parse_date_empty_not_required(self):
        """Should return None without error when empty and not required."""
        validator = FormValidator({'date': ''})
        result = validator.parse_date('date')
        assert result is None
        assert validator.is_valid()

    def test_parse_date_empty_required(self):
        """Should add error when empty and required."""
        validator = FormValidator({'date': ''})
        result = validator.parse_date('date', required=True)
        assert result is None
        assert 'Date is required.' in validator.errors

    def test_parse_date_custom_format(self):
        """Should parse date with custom format."""
        validator = FormValidator({'date': '25/12/2025'})
        result = validator.parse_date('date', date_format='%d/%m/%Y')
        assert result == datetime.date(2025, 12, 25)

    def test_parse_date_custom_error_message(self):
        """Should use custom error message for required check."""
        validator = FormValidator({'date': ''})
        validator.parse_date('date', error_message='Event date is required.', required=True)
        assert 'Event date is required.' in validator.errors

    def test_parse_date_custom_format_error(self):
        """Should use custom format error message."""
        validator = FormValidator({'date': 'bad'})
        validator.parse_date('date', format_error='Use format YYYY-MM-DD.')
        assert 'Use format YYYY-MM-DD.' in validator.errors


class TestChoice:
    """Tests for the choice() method."""

    def test_choice_valid_value(self):
        """Should return value when in valid choices."""
        validator = FormValidator({'priority': 'high'})
        result = validator.choice('priority', ['low', 'medium', 'high'])
        assert result == 'high'
        assert validator.values['priority'] == 'high'

    def test_choice_invalid_value_with_default(self):
        """Should return default when value not in choices."""
        validator = FormValidator({'priority': 'urgent'})
        result = validator.choice('priority', ['low', 'medium', 'high'], default='medium')
        assert result == 'medium'
        assert validator.is_valid()

    def test_choice_invalid_value_no_default(self):
        """Should return None when value not in choices and no default."""
        validator = FormValidator({'priority': 'urgent'})
        result = validator.choice('priority', ['low', 'medium', 'high'])
        assert result is None
        assert validator.is_valid()  # No error added without error_message

    def test_choice_invalid_value_with_error_message(self):
        """Should add error when value invalid and error_message provided."""
        validator = FormValidator({'priority': 'urgent'})
        result = validator.choice('priority', ['low', 'medium', 'high'],
                                  error_message='Invalid priority.')
        assert result is None
        assert 'Invalid priority.' in validator.errors

    def test_choice_empty_value(self):
        """Should treat empty value as invalid."""
        validator = FormValidator({'priority': ''})
        result = validator.choice('priority', ['low', 'medium', 'high'], default='medium')
        assert result == 'medium'

    def test_choice_missing_field(self):
        """Should treat missing field as invalid."""
        validator = FormValidator({})
        result = validator.choice('priority', ['low', 'medium', 'high'], default='low')
        assert result == 'low'

    def test_choice_with_set_of_choices(self):
        """Should work with set of valid choices."""
        validator = FormValidator({'status': 'active'})
        result = validator.choice('status', {'active', 'inactive', 'pending'})
        assert result == 'active'


class TestIsValid:
    """Tests for the is_valid() method."""

    def test_is_valid_with_no_errors(self):
        """Should return True when no errors."""
        validator = FormValidator({'name': 'Test'})
        validator.required('name')
        assert validator.is_valid() is True

    def test_is_valid_with_errors(self):
        """Should return False when there are errors."""
        validator = FormValidator({})
        validator.required('name')
        assert validator.is_valid() is False

    def test_is_valid_multiple_validations(self):
        """Should track errors from multiple validations."""
        validator = FormValidator({'name': '', 'email': ''})
        validator.required('name')
        validator.required('email')
        assert validator.is_valid() is False
        assert len(validator.errors) == 2


class TestFirstError:
    """Tests for the first_error() method."""

    def test_first_error_with_no_errors(self):
        """Should return None when no errors."""
        validator = FormValidator({})
        assert validator.first_error() is None

    def test_first_error_returns_first(self):
        """Should return the first error message."""
        validator = FormValidator({'name': '', 'email': ''})
        validator.required('name', 'Name is required.')
        validator.required('email', 'Email is required.')
        assert validator.first_error() == 'Name is required.'


class TestIntegration:
    """Integration tests combining multiple validations."""

    def test_complete_form_validation(self):
        """Should validate a complete form with multiple field types."""
        form_data = {
            'name': 'Test Item',
            'price': '29.99',
            'quantity': '5',
            'priority': 'High',
            'notes': 'Optional notes',
            'date': '2025-06-15'
        }
        validator = FormValidator(form_data)

        name = validator.required('name')
        price = validator.parse_float('price')
        quantity = validator.parse_int('quantity', min_value=1, max_value=100)
        priority = validator.choice('priority', ['High', 'Medium', 'Low'])
        notes = validator.optional('notes')
        date = validator.parse_date('date')

        assert validator.is_valid()
        assert name == 'Test Item'
        assert price == 29.99
        assert quantity == 5
        assert priority == 'High'
        assert notes == 'Optional notes'
        assert date == datetime.date(2025, 6, 15)

    def test_form_with_multiple_errors(self):
        """Should collect all validation errors."""
        form_data = {
            'name': '',
            'price': 'invalid',
            'quantity': '-1',
            'date': 'bad-date'
        }
        validator = FormValidator(form_data)

        validator.required('name', 'Name is required.')
        validator.parse_float('price', 'Price must be a number.')
        validator.parse_int('quantity', min_value=1, range_error='Quantity must be positive.')
        validator.parse_date('date', format_error='Invalid date.')

        assert not validator.is_valid()
        assert 'Name is required.' in validator.errors
        assert 'Price must be a number.' in validator.errors
        assert 'Quantity must be positive.' in validator.errors
        assert 'Invalid date.' in validator.errors
