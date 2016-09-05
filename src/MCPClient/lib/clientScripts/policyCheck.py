#!/usr/bin/env python2
from __future__ import print_function
import json
import sys

from custom_handlers import get_script_logger

import django
django.setup()
from fpr.models import FPRule, FormatVersion
from main.models import File

from executeOrRunSubProcess import executeOrRun
import databaseFunctions
from dicts import replace_string_values

# Note that linkTaskManagerFiles.py will take the highest exit code it has seen
# from all tasks and will use that as the exit code of the job as a whole.
SUCCESS_CODE = 0
NOT_APPLICABLE_CODE = 0
FAIL_CODE = 1


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

    def __init__(self, file_path, file_uuid, sip_uuid, policies_dir):
        self.file_path = file_path
        self.file_uuid = file_uuid
        self.sip_uuid = sip_uuid
        self.policies_dir = policies_dir

    def check(self):
        try:
            self.file_model = File.objects.get(uuid=self.file_uuid)
        except File.DoesNotExist:
            print('Not performing a policy check because there is no file with'
                  ' UUID {}.'.format(self.file_uuid))
            return NOT_APPLICABLE_CODE
        if not self.we_check_this_type_of_file():
            return NOT_APPLICABLE_CODE
        rules = self._get_rules()
        if not rules:
            print('Not performing a policy check because there are no relevant'
                  ' FPR rules')
            return NOT_APPLICABLE_CODE
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
        if self.file_model.filegrpuse == 'access':
            return True
        return False

    purpose = 'checkingPolicy'

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
        command_to_execute, args = self._get_command_to_execute(rule)
        print('Running', rule.command.description)
        exitstatus, stdout, stderr = executeOrRun(
            rule.command.script_type, command_to_execute, arguments=args,
            printing=False)
        if exitstatus == 0:
            print('Command {} completed with output {}'.format(
                  rule.command.description, stdout))
        else:
            print('Command {} failed with exit status {}; stderr:'.format(
                  rule.command.description, exitstatus), stderr,
                  file=sys.stderr)
            return 'failed'
        # Parse output and generate an Event
        # TODO: can we assume that all policy check commands will print JSON to
        # stdout?
        output = json.loads(stdout)
        event_detail = ('program="{tool.description}";'
                        ' version="{tool.version}"'.format(
                            tool=rule.command.tool))
        mc_pc_dscr = 'Check against policy using MediaConch'
        if ('Check against policy' in rule.command.description and
                'MediaConch' in rule.command.description and
                output.get('eventOutcomeInformation') != 'pass'):
            print('Command {descr} returned a non-pass outcome for the policy'
                  ' check;\n\noutcome: {outcome}\n\ndetails: {details}.'
                  .format(
                      descr=rule.command.description,
                      outcome=output.get('eventOutcomeInformation'),
                      details=output.get('eventOutcomeDetailNote')),
                  file=sys.stderr)
            result = 'failed'
        print('Creating policy checking event for {} ({})'
              .format(self.file_path, self.file_uuid))
        # TODO/QUESTION: should this be a 'validation'-type event?
        databaseFunctions.insertIntoEvents(
            fileUUID=self.file_uuid,
            eventType='validation',  # From PREMIS controlled vocab.
            eventDetail=event_detail,
            eventOutcome=output.get('eventOutcomeInformation'),
            eventOutcomeDetailNote=output.get('eventOutcomeDetailNote'),
        )
        return result

    def _get_command_to_execute(self, rule):
        if rule.command.script_type in ('bashScript', 'command'):
            return (replace_string_values(rule.command.command,
                                          file_=self.file_uuid,
                                          sip=self.sip_uuid, type_='file'),
                    [])
        else:
            return (rule.command.command, [self.file_path, self.policies_dir])

if __name__ == '__main__':
    logger = get_script_logger(
        "archivematica.mcp.client.policyCheck")
    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    policies_dir = sys.argv[4]
    policy_checker = PolicyChecker(file_path, file_uuid, sip_uuid,
                                   policies_dir)
    sys.exit(policy_checker.check())
