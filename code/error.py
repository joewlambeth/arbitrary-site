import re
import json
import string
from code.db import Base

form_rules = dict()

json_responses = {
    "SUCCESS": None,
    "FAIL": None,
    "ERROR": "An error has occurred while processing your request. Please try again later",
    "DUPLICATE": "%s '%s' already exists. Please choose another name.",
    "INVALID": "%s '%s' is invalid. Please choose another name.",
    "INVALID_FILE": "%s '%s' is invalid. Please upload a proper file.",
}

class JsonResponseError(Exception):
    def __init__(self, name, type=None, desc=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        if json_responses.get(name) and type and desc:
            if type and desc:
                self.description = json_responses[name] % (type, desc)
            else:
                self.description = json_responses[name]
        elif not json_responses.get(name) and desc:
            self.description = desc
        else:
            self.description = None

class FormRequirementError(Exception):
    def __init__(self, description, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = description
        

def build_form_regexes():
    rules_json = open("code/rules.json")
    rules = json.load(rules_json)
    rules_json.close()

    for table, fields in rules.items():
        form_rules[table] = dict()
        for field, regex_map in fields.items():
            form_rules[table][field] = [(re.compile(rule), message) for rule, message in regex_map.items()]


def valid_form_entry(tablename, field, value):
    for rule, message in form_rules[tablename][field]:
        if rule.search(value) is None:
            raise FormRequirementError(message)


def valid_form_object(obj: Base):
    for field in form_rules[obj.__tablename__].keys():
        valid_form_entry(obj.__tablename__, field, obj[field])