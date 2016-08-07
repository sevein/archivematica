from __future__ import print_function
import ast
import sys

import django
django.setup()
from fpr.models import FPRule, FormatVersion
from main.models import Derivation

from executeOrRunSubProcess import executeOrRun
import databaseFunctions
from dicts import replace_string_values

SUCCESS_CODE = 0
FAIL_CODE = 1
NOT_DERIVATIVE_CODE = 2


class DerivativeValidator:
    """Validates a preservation derivative.

    Call ``validate`` method to determine whether a given file conforms to a
    given specification (or policy).

    Sub-class in order to validate an access derivative. See
    validateAccessDerivative.py.
    """

    def __init__(self, file_path, file_uuid, sip_uuid):
        self.file_path = file_path
        self.file_uuid = file_uuid
        self.sip_uuid = sip_uuid

    def validate(self):
        if not self.is_derivative():
            print('File {uuid} {not_derivative_msg}; not validating.'.format(
                  uuid=self.file_uuid,
                  not_derivative_msg=self.not_derivative_msg))
            return NOT_DERIVATIVE_CODE
        rules = self._get_rules()
        rule_outputs = []
        for rule in rules:
            rule_outputs.append(self._execute_rule_command(rule))
        if 'failed' in rule_outputs:
            return FAIL_CODE
        else:
            return SUCCESS_CODE

    # Override the following two attributes and one method for validation of
    # access derivatives.
    purpose = 'validatePreservationDerivative'
    not_derivative_msg = 'is not a preservation derivative'

    def is_derivative(self):
        try:
            Derivation.objects.get(derived_file__uuid=self.file_uuid,
                                   event__event_type='normalization')
            return True
        except Derivation.DoesNotExist:
            return False

    def _get_rules(self):
        try:
            fmt = FormatVersion.active.get(
                fileformatversion__file_uuid=self.file_uuid)
        except FormatVersion.DoesNotExist:
            rules = fmt = None
        if fmt:
            rules = FPRule.active.filter(format=fmt.uuid, purpose=self.purpose)
        # Check default rules.
        if not rules:
            rules = FPRule.active.filter(
                purpose='default_{}'.format(self.purpose))
        return rules

    def _execute_rule_command(self, rule):
        result = 'passed'
        if rule.command.script_type in ('bashScript', 'command'):
            command_to_execute = replace_string_values(
                rule.command.command, file_=self.file_uuid, sip=self.sip_uuid,
                type_='file')
            args = []
        else:
            command_to_execute = rule.command.command
            args = [self.file_path]
        print('Running', rule.command.description)
        exitstatus, stdout, stderr = executeOrRun(
            rule.command.script_type, command_to_execute, arguments=args)
        if exitstatus != 0:
            print('Command {} failed with exit status {}; stderr:'.format(
                rule.command.description, exitstatus), stderr, file=sys.stderr)
            return 'failed'
        print('Command {} completed with output {}'.format(
              rule.command.description, stdout))
        # Parse output and generate an Event
        output = ast.literal_eval(stdout)
        event_detail = ('program="{tool.description}";'
                        'version="{tool.version}"'.format(
                            tool=rule.command.tool))
        if (rule.command.description == 'Validate using MediaConch' and
                output.get('eventOutcomeInformation') != 'pass'):
            result = 'failed'
        print('Creating post-normalization validation event for {} ({})'
              .format(self.file_path, self.file_uuid))
        databaseFunctions.insertIntoEvents(
            fileUUID=self.file_uuid,
            eventType='validation',  # From PREMIS controlled vocab.
            eventDetail=event_detail,
            eventOutcome=output.get('eventOutcomeInformation'),
            eventOutcomeDetailNote=output.get('eventOutcomeDetailNote'),
        )
        return result
