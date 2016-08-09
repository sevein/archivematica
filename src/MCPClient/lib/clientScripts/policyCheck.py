from __future__ import print_function
import json
import sys

from custom_handlers import get_script_logger

import django
django.setup()
from fpr.models import FPRule, FormatVersion
from main.models import Derivation

from executeOrRunSubProcess import executeOrRun
import databaseFunctions
from dicts import replace_string_values

SUCCESS_CODE = 0
FAIL_CODE = 1
NO_RULES_CODE = 2


class PolicyChecker:
    """Checks that files (originals or derivatives) conform to specific
    policies.

    - policies for access
    - policies for preservation

    Initialize on a file and then call the ``check`` method to determine
    whether a given file conforms to the policies that are appropriate to it,
    given its format and its purpose, i.e., whether it is intended for access
    or preservation.
    """

    def __init__(self, file_path, file_uuid, sip_uuid):
        self.file_path = file_path
        self.file_uuid = file_uuid
        self.sip_uuid = sip_uuid

    def check(self):
        rules = self._get_rules()
        if not rules:
            return NO_RULES_CODE
        rule_outputs = []
        for rule in rules:
            rule_outputs.append(self._execute_rule_command(rule))
        if 'failed' in rule_outputs:
            return FAIL_CODE
        else:
            return SUCCESS_CODE

    def is_for_access(self):
        """Returns ``True`` if the file with UUID ``self.file_uuid`` is "for"
        access.
        """
        file_model = File.objects.get(uuid=self.file_uuid)
        if file_model.filegrpuse == 'access':
            return True
        return False

    preservation_purpose = 'checkingAgainstPreservationPolicy' # TODO: create in migration.
    access_purpose = 'checkingAgainstAccessPolicy' # TODO: create in migration.

    def set_purpose(self):
        if self.is_for_access():
            self.purpose = self.preservation_purpose
        else:
            self.purpose = self.access_purpose

    def _get_rules(self):
        self.set_purpose()
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
        output = json.loads(stdout)
        event_detail = ('program="{tool.description}";'
                        'version="{tool.version}"'.format(
                            tool=rule.command.tool))
        md_pc_dscr 'Check against policy using MediaConch'
        if (rule.command.description == md_pc_dscr and
                output.get('eventOutcomeInformation') != 'pass'):
            result = 'failed'
        print('Creating policy checking event for {} ({})'
              .format(self.file_path, self.file_uuid))
        databaseFunctions.insertIntoEvents(
            fileUUID=self.file_uuid,
            eventType='validation',  # From PREMIS controlled vocab.
            eventDetail=event_detail,
            eventOutcome=output.get('eventOutcomeInformation'),
            eventOutcomeDetailNote=output.get('eventOutcomeDetailNote'),
        )
        return result

if __name__ == '__main__':
    logger = get_script_logger(
        "archivematica.mcp.client.policyCheck")
    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    policy_checker = PolicyChecker(file_path, file_uuid, sip_uuid)
    sys.exit(policy_checker.check())
