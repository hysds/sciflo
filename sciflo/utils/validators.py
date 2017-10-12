from datetime import datetime, timedelta
from formencode import Schema
from formencode.validators import FancyValidator, Invalid, Number

class DateCompare(FancyValidator):
    messages = {
        'invalid': "Start date must be before end date",
        'start_future': "Start date cannot be in the future",
        'stop_future': "End date cannot be in the future",
        }
    def validate_python(self, field_dict, state):
        start_date = field_dict['startdate']
        stop_date = field_dict['enddate']
        if start_date >= stop_date:
            msg = self.message('invalid', state)
            raise Invalid(msg, field_dict, state, error_dict=dict(stop_date=msg))
        if start_date > datetime.now():
            msg = self.message('start_future', state)
            raise Invalid(msg, field_dict, state, error_dict=dict(stop_date=msg))
        if stop_date > datetime.now():
            msg = self.message('stop_future', state)
            raise Invalid(msg, field_dict, state, error_dict=dict(stop_date=msg))

class LonValidator(Number):
    messages = {
        'number': "Please enter a number",
        'range': "Lon values must be between -180 and 180",
        }
    def validate_python(self, value, state):
        if value < -180 or value > 180:
            msg = self.message('range', state)
            raise Invalid(msg, value, state, error_dict=dict(stop_date=msg))

class LatValidator(Number):
    messages = {
        'number': "Please enter a number",
        'range': "Lat values must be between -90 and 90",
        }
    def validate_python(self, value, state):
        if value < -90 or value > 90:
            msg = self.message('range', state)
            raise Invalid(msg, value, state, error_dict=dict(stop_date=msg))

class LonCompare(FancyValidator):
    messages = {'invalid': "Min lon must be less than max lon",
               }
    def validate_python(self, field_dict, state):
        lonmin = field_dict['lonmin']
        lonmax = field_dict['lonmax']
        if lonmin >= lonmax:
            msg = self.message('invalid', state)
            raise Invalid(msg, field_dict, state, error_dict=dict(stop_date=msg))

class LatCompare(FancyValidator):
    messages = {'invalid': "Min lat must be less than max lat",
               }
    def validate_python(self, field_dict, state):
        latmin = field_dict['latmin']
        latmax = field_dict['latmax']
        if latmin >= latmax:
            msg = self.message('invalid', state)
            raise Invalid(msg, field_dict, state, error_dict=dict(stop_date=msg))
