#!/usr/bin/env python2
"""If the provided file is a product of normalization, run a validation command
on it and generate an ``Event`` from the results.

If there is no rule with the purpose ``validateNormalizedFile`` that applies to
the version of the file, then no command is run.)
"""

from __future__ import print_function
import ast
import sys

import django
django.setup()
# dashboard
from fpr.models import FPRule, FormatVersion
from main.models import Derivation

# archivematicaCommon
from custom_handlers import get_script_logger
from executeOrRunSubProcess import executeOrRun
import databaseFunctions
from dicts import replace_string_values


PURPOSE = 'validateNormalizedFile'


def is_derived_from_normalization(file_uuid):
    try:
        Derivation.objects.get(derived_file__uuid=file_uuid,
                               event__event_type='normalization')
        return True
    except Derivation.DoesNotExist:
        return False


def main(file_path, file_uuid, sip_uuid):

    failed = False

    if not is_derived_from_normalization(file_uuid):
        print('File {uuid} was not derived from normalization; not'
              ' validating.'.format(uuid=file_uuid))
        return 0

    # Get file format
    try:
        fmt = FormatVersion.active.get(fileformatversion__file_uuid=file_uuid)
    except FormatVersion.DoesNotExist:
        rules = fmt = None

    if fmt:
        rules = FPRule.active.filter(format=fmt.uuid, purpose=PURPOSE)

    # Check if any default 'validateNormalizedFile' rules exists.
    if not rules:
        rules = FPRule.active.filter(purpose='default_{}'.format(PURPOSE))

    for rule in rules:
        if rule.command.script_type in ('bashScript', 'command'):
            command_to_execute = replace_string_values(
                rule.command.command, file_=file_uuid, sip=sip_uuid,
                type_='file')
            args = []
        else:
            command_to_execute = rule.command.command
            args = [file_path]

        print('Running', rule.command.description)
        exitstatus, stdout, stderr = executeOrRun(
            rule.command.script_type, command_to_execute, arguments=args)
        if exitstatus != 0:
            print('Command {} failed with exit status {}; stderr:'.format(
                rule.command.description, exitstatus), stderr, file=sys.stderr)
            failed = True
            continue

        print('Command {} completed with output {}'.format(
            rule.command.description, stdout))

        # Parse output and generate an Event
        # Output is JSON in format:
        # { "eventOutcomeInformation": "...",
        #   "eventOutcomeDetailNote": "..."}
        # where ``eventOutcomeInformation`` is "pass", "fail", etc.
        output = ast.literal_eval(stdout)
        event_detail = ('program="{tool.description}";'
                        'version="{tool.version}"'.format(
                           tool=rule.command.tool))

        if (rule.command.description == 'Validate using MediaConch' and
                output.get('eventOutcomeInformation') != 'pass'):
            failed = True

        print('Creating post-normalization validation event for {} ({})'
              .format(file_path, file_uuid))

        databaseFunctions.insertIntoEvents(
            fileUUID=file_uuid,
            eventType='validation', # From PREMIS controlled vocab.
            eventDetail=event_detail,
            eventOutcome=output.get('eventOutcomeInformation'),
            eventOutcomeDetailNote=output.get('eventOutcomeDetailNote'),
        )

    if failed:
        return -1
    else:
        return 0

if __name__ == '__main__':
    logger = get_script_logger("archivematica.mcp.client.validateFile")

    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    sys.exit(main(file_path, file_uuid, sip_uuid))
