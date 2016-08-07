# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def data_migration(apps, schema_editor):
    """Migrations for MediaConch integration.

    Changes workflow so that, at a high-level the following things happen:

    1. MediaConch is available for validation (in particular for validating
       .mkv files)
    2. Creates a "Validate Preservation Derivatives" micro-service (in
       particular, so that MediaConch can be used for conformance-checking of
       .mkv files created during "Normalize for preservation")
    3. Creates a "Validate Access Derivatives" micro-service (in particular, so
       that MediaConch can be used for conformance-checking of .mkv files
       created during "Normalize for access")

    Specifics:

    a. MediaConch Tool (command-line program)
    b. MediaConch Command (Python wrapper, "client script")
    c. MediaConch-against-MKV-for-validate Rule
    d. MediaConch-against-MKV-for-validatePreservationDerivative Rule
    e. MediaConch-against-MKV-for-validateAccessDerivative Rule

    f. "Validate Preservation Derivatives" chain link after "Normalize for
       Preservation" chain link.

       i.   Standard Tasks Config
            - references ``validatePreservationDerivative_v0.0`` executable
       ii.  Task Config
            - configures ``validatePreservationDerivative`` as a "for each
              file" type
       iii. Chain Link ``vldt_prsrvtn_drvtv_cl``
            - puts validate preservation derivative in the "Normalize" group
            - sets the next chain link to the link that was the next link after
              "Normalize for preservation".
       iv.  Exit Codes
            - "Validate preservation derivatives" continues on to the link that
              was previously the next link after "Normalize for preservation",
              no matter what the exit code (0, 1, or 2).

    g. "Validate Access Derivatives" chain link after "Normalize for Access"
       chain link.

       i.   Standard Tasks Config
            - references ``validateAccessDerivative_v0.0`` executable
       ii.  Task Config
            - configures ``validateAccessDerivative`` as a "for each file" type
       iii. Chain Link ``vldt_ccss_drvtv_cl``
            - puts validate access derivative in the "Normalize" group
            - sets the next chain link to the link that was the next link after
              "Normalize for access".
       iv.  Exit Codes
            - "Validate access derivatives" continues on to the link that
              was previously the next link after "Normalize for access",
              no matter what the exit code (0, 1, or 2).

    """

    ###########################################################################
    # Model Classes
    ###########################################################################

    FPTool = apps.get_model('fpr', 'FPTool')
    FPCommand = apps.get_model('fpr', 'FPCommand')
    FPRule = apps.get_model('fpr', 'FPRule')
    FormatVersion = apps.get_model('fpr', 'FormatVersion')
    TaskType = apps.get_model('main', 'TaskType')
    TaskConfig = apps.get_model('main', 'TaskConfig')
    StandardTaskConfig = apps.get_model('main', 'StandardTaskConfig')
    MicroServiceChainLink = apps.get_model('main', 'MicroServiceChainLink')
    MicroServiceChainLinkExitCode = apps.get_model(
        'main', 'MicroServiceChainLinkExitCode')

    ###########################################################################
    # Get Existing Model Instances
    ###########################################################################

    mkv_format = FormatVersion.objects.get(description='Generic MKV')
    for_each_file_type = TaskType.objects.get(description='for each file')

    # There are two chain links with the task config description 'Normalize for
    # preservation'. However, all of them exit to the same next chain link.
    nrmlz_prsrvtn_cl_1, nrmlz_prsrvtn_cl_2 = MicroServiceChainLink.objects\
        .filter(currenttask__description='Normalize for preservation').all()
    nrmlz_prsrvtn_next_link = nrmlz_prsrvtn_cl_1\
        .exit_codes.first().nextmicroservicechainlink

    # Similarly, there are two chain links with the task config description
    # 'Normalize for access'. However, in this case, they exit to different
    # next chain links.
    nrmlz_ccss_cl_1, nrmlz_ccss_cl_2 = MicroServiceChainLink.objects\
        .filter(currenttask__description='Normalize for access').all()
    nrmlz_ccss_1_next_link = nrmlz_ccss_cl_1\
        .exit_codes.first().nextmicroservicechainlink
    nrmlz_ccss_2_next_link = nrmlz_ccss_cl_2\
        .exit_codes.first().nextmicroservicechainlink

    ###########################################################################
    # Create MediaConch Tool and Command
    ###########################################################################

    # MediaConch Tool
    mediaconch_tool_uuid = 'f79c56f1-2d42-440a-8a1f-f40888e24bca'
    mediaconch_tool = FPTool.objects.create(
        uuid=mediaconch_tool_uuid,
        description='MediaConch',
        version='16.05',
        enabled=True,
        slug='mediaconch-1605'
    )

    # MediaConch Command
    mediaconch_command_uuid = '287656fb-e58f-4967-bf72-0bae3bbb5ca8'
    mediaconch_command = FPCommand.objects.create(
        uuid=mediaconch_command_uuid,
        tool=mediaconch_tool,
        description='Validate using MediaConch',
        command=mediaconch_command_script,
        script_type='pythonScript',
        command_usage='validation'
    )

    ###########################################################################
    # MediaConch Rules
    ###########################################################################

    # MediaConch-against-MKV-for-validate Rule.
    mediaconch_mkv_rule_uuid = 'a2fb0477-6cde-43f8-a1c9-49834913d588'
    FPRule.objects.create(
        uuid=mediaconch_mkv_rule_uuid,
        purpose='validation',
        command=mediaconch_command,
        format=mkv_format
    )

    # MediaConch-against-MKV-for-validatePreservationDerivative Rule.
    # Create the FPR rule that causes 'Validate using MediaConch' command to be
    # used on for-preservation-derived 'Generic MKV' files in the "Validate
    # Preservation Derivatives" micro-service.
    vldt_prsrvtn_drvtv_rule_pk = '3fcbf5d2-c908-4ec4-b618-8c7dc0f4117e'
    FPRule.objects.create(
        uuid=vldt_prsrvtn_drvtv_rule_pk,
        purpose='validatePreservationDerivative',
        command=mediaconch_command,
        format=mkv_format
    )

    # MediaConch-against-MKV-for-validateAccessDerivative Rule.
    # Create the FPR rule that causes 'Validate using MediaConch' command to be
    # used on for-access-derived 'Generic MKV' files in the "Validate
    # Access Derivatives" micro-service.
    vldt_ccss_drvtv_rule_pk = '0ada4f48-d8a6-4762-8a20-c04cb4e58676'
    FPRule.objects.create(
        uuid=vldt_ccss_drvtv_rule_pk,
        purpose='validateAccessDerivative',
        command=mediaconch_command,
        format=mkv_format
    )

    ###########################################################################
    # Validate PRESERVATION Derivatives CHAIN LINK, etc.
    ###########################################################################

    # Validate Preservation Derivatives Standard Task Config.
    vldt_prsrvtn_drvtv_stc_pk = 'f8bc7b43-8bd4-4db8-88dc-d6f55732fb63'
    StandardTaskConfig.objects.create(
        id=vldt_prsrvtn_drvtv_stc_pk,
        execute='validatePreservationDerivative_v0.0',
        arguments='"%relativeLocation%" "%fileUUID%" "%SIPUUID%"',
        filter_subdir='objects/'
    )

    # Validate Preservation Derivatives Task Config.
    vldt_prsrvtn_drvtv_tc_pk = 'b6479474-159d-47aa-a10f-40495cb0e273'
    vldt_prsrvtn_drvtv_tc = TaskConfig.objects.create(
        id=vldt_prsrvtn_drvtv_tc_pk,
        tasktype=for_each_file_type,
        tasktypepkreference=vldt_prsrvtn_drvtv_stc_pk,
        description='Validate preservation derivatives'
    )

    # Validate Preservation Derivatives Chain Link.
    vldt_prsrvtn_drvtv_cl_pk = '5b0042a2-2244-475c-85d5-41e4b11e65d6'
    vldt_prsrvtn_drvtv_cl = MicroServiceChainLink.objects.create(
        id=vldt_prsrvtn_drvtv_cl_pk,
        currenttask=vldt_prsrvtn_drvtv_tc,
        defaultnextchainlink=nrmlz_prsrvtn_next_link,
        microservicegroup=u'Normalize'
    )

    # Fix default next links for "Normalize for Preservation" links
    nrmlz_prsrvtn_cl_1.defaultnextchainlink = vldt_prsrvtn_drvtv_cl
    nrmlz_prsrvtn_cl_2.defaultnextchainlink = vldt_prsrvtn_drvtv_cl

    # Update the six chain link exit code rows for the 'Normalize for
    # preservation' chain links so that they exit to the 'Validate preservation
    # derivatives' chain link.
    MicroServiceChainLinkExitCode.objects\
        .filter(microservicechainlink__in=[nrmlz_prsrvtn_cl_1,
                                           nrmlz_prsrvtn_cl_2])\
        .update(nextmicroservicechainlink=vldt_prsrvtn_drvtv_cl)

    # Create three new chain link exit code rows that cause the Validate
    # Preservation Derivatives chain link to exit to whatever chain link that
    # Normalize for Preservation used to exit to.
    for pk, exit_code in (
            ('f574f94f-c431-4442-a554-ac0934ccac93', 0),
            ('d922a98b-2d65-4d75-bae0-9e8a446cb289', 1),
            ('ba7d93fb-64b9-4553-bed3-9738a524ff00', 2)):
        MicroServiceChainLinkExitCode.objects.create(
            id=pk,
            microservicechainlink=vldt_prsrvtn_drvtv_cl,
            exitcode=exit_code,
            nextmicroservicechainlink=nrmlz_prsrvtn_next_link
        )

    ###########################################################################
    # Validate ACCESS Derivatives CHAIN LINK, etc.
    ###########################################################################

    # Validate Access Derivatives Standard Task Config.
    vldt_ccss_drvtv_stc_pk = '52e7912e-2ce9-4192-9ba4-19a75b2a2807'
    StandardTaskConfig.objects.create(
        id=vldt_ccss_drvtv_stc_pk,
        execute='validateAccessDerivative_v0.0',
        arguments='"%relativeLocation%" "%fileUUID%" "%SIPUUID%"',
        filter_subdir='DIP/objects/'
    )

    # Validate Access Derivatives Task Config.
    vldt_ccss_drvtv_tc_pk = 'b597753f-0b36-484f-ae78-4ae95951fd90'
    vldt_ccss_drvtv_tc = TaskConfig.objects.create(
        id=vldt_ccss_drvtv_tc_pk,
        tasktype=for_each_file_type,
        tasktypepkreference=vldt_ccss_drvtv_stc_pk,
        description='Validate access derivatives'
    )

    # Validate Access Derivatives Chain Link # 1.
    vldt_ccss_drvtv_cl_1_pk = '286bbb36-6a38-41d5-bf7a-a8ba58aa71ce'
    vldt_ccss_drvtv_cl_1 = MicroServiceChainLink.objects.create(
        id=vldt_ccss_drvtv_cl_1_pk,
        currenttask=vldt_ccss_drvtv_tc,
        defaultnextchainlink=nrmlz_ccss_1_next_link,
        microservicegroup=u'Normalize'
    )

    # Validate Access Derivatives Chain Link # 2.
    vldt_ccss_drvtv_cl_2_pk = 'a7c18fee-c8c1-4713-ba74-9705c45efbce'
    vldt_ccss_drvtv_cl_2 = MicroServiceChainLink.objects.create(
        id=vldt_ccss_drvtv_cl_2_pk,
        currenttask=vldt_ccss_drvtv_tc,
        defaultnextchainlink=nrmlz_ccss_2_next_link,
        microservicegroup=u'Normalize'
    )

    # Fix default next links for "Normalize for Access" links
    nrmlz_ccss_cl_1.defaultnextchainlink = vldt_ccss_drvtv_cl_1
    nrmlz_ccss_cl_2.defaultnextchainlink = vldt_ccss_drvtv_cl_2

    # Update the three chain link exit code rows for the FIRST 'Normalize for
    # access' chain link so that they exit to the FIRST 'Validate access
    # derivatives' chain link.
    MicroServiceChainLinkExitCode.objects\
        .filter(microservicechainlink=nrmlz_ccss_cl_1)\
        .update(nextmicroservicechainlink=vldt_ccss_drvtv_cl_1)

    # Update the three chain link exit code rows for the SECOND 'Normalize for
    # access' chain link so that they exit to the SECOND 'Validate access
    # derivatives' chain link.
    MicroServiceChainLinkExitCode.objects\
        .filter(microservicechainlink=nrmlz_ccss_cl_2)\
        .update(nextmicroservicechainlink=vldt_ccss_drvtv_cl_2)

    # Create three new MSCL exit code rows that cause the Validate
    # Access Derivatives CL 1 to exit to whatever Normalize for Access 1 used
    # to exit to.
    for pk, exit_code in (
            ('9bbaafd6-9954-4f1f-972a-4f7eb0a60de7', 0),
            ('de1dabdd-93ca-4f3b-accf-b9096aa494ba', 1),
            ('70281000-e076-4505-8c4b-38ca96518f1f', 2)):
        MicroServiceChainLinkExitCode.objects.create(
            id=pk,
            microservicechainlink=vldt_ccss_drvtv_cl_1,
            exitcode=exit_code,
            nextmicroservicechainlink=nrmlz_ccss_1_next_link
        )

    # Create three new MSCL exit code rows that cause the Validate
    # Access Derivatives CL 2 to exit to whatever Normalize for Access 2 used
    # to exit to.
    for pk, exit_code in (
            ('09df34f7-31ff-4107-82e7-1db36351acd3', 0),
            ('0e92980d-2545-42f6-9d62-b506ac2ceecb', 1),
            ('41a2ab1e-6804-4228-9f6c-ae6259839348', 2)):
        MicroServiceChainLinkExitCode.objects.create(
            id=pk,
            microservicechainlink=vldt_ccss_drvtv_cl_2,
            exitcode=exit_code,
            nextmicroservicechainlink=nrmlz_ccss_2_next_link
        )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_email_report_args'),
    ]

    operations = [
        migrations.RunPython(data_migration),
    ]

mediaconch_command_script = '''
import json
import subprocess
import sys
import uuid

from lxml import etree

NS = '{https://mediaarea.net/mediaconch}'


class MediaConchException(Exception):
    pass


def parse_mediaconch_data(target):
    """Run `mediaconch -mc -iv 4 -fx <target>` against `target` and return an
    lxml etree parse of the output.

    .. note::

        At present, MediaConch (v. 16.05) will give terse output so long as you
        provide *some* argument to the -iv option. With no -iv option, you will
        get high verbosity. To be specific, low verbosity means that only
        checks whose tests fail in the named "MediaConch EBML Implementation
        Checker" will be displayed. If none fail, the EBML element will contain
        no <check> elements.

    """

    args = ['mediaconch', '-mc', '-iv', '4', '-fx', target]
    try:
        output = subprocess.check_output(args)
    except subprocess.CalledProcessError:
        raise MediaConchException("MediaConch failed when running: %s" % (
            ' '.join(args),))
    try:
        return etree.fromstring(output)
    except etree.XMLSyntaxError:
        raise MediaConchException(
            "MediaConch failed when attempting to parse the XML output by"
            " MediaConch")


def get_impl_check_name(impl_check_el):
    name_el = impl_check_el.find('%sname' % NS)
    if name_el is not None:
        return name_el.text
    else:
        return 'Unnamed Implementation Check %s' % uuid.uuid4()


def get_check_name(check_el):
    return check_el.attrib.get(
        'name', check_el.attrib.get('icid', 'Unnamed Check %s' % uuid.uuid4()))


def get_check_tests_outcomes(check_el):
    """Return a list of outcome strings for the <check> element `check_el`."""
    outcomes = []
    for test_el in check_el.iterfind('%stest' % NS):
        outcome = test_el.attrib.get('outcome')
        if outcome:
            outcomes.append(outcome)
    return outcomes


def get_impl_check_result(impl_check_el):
    """Return a dict mapping check names to lists of test outcome strings."""
    checks = {}
    for check_el in impl_check_el.iterfind('%scheck' % NS):
        check_name = get_check_name(check_el)
        test_outcomes = get_check_tests_outcomes(check_el)
        if test_outcomes:
            checks[check_name] = test_outcomes
    return checks


def get_impl_checks(doc):
    """When not provided with a policy file, MediaConch produces a series of
    XML <implementationChecks> elements that contain <check> sub-elements. This
    function returns a dict mapping implementation check names to dicts that
    map individual check names to lists of test outcomes, i.e., 'pass' or
    'fail'.

    """

    impl_checks = {}
    path = '.%smedia/%simplementationChecks' % (NS, NS)
    for impl_check_el in doc.iterfind(path):
        impl_check_name = get_impl_check_name(impl_check_el)
        impl_check_result = get_impl_check_result(impl_check_el)
        if impl_check_result:
            impl_checks[impl_check_name] = impl_check_result
    return impl_checks


def get_event_outcome_information_detail(impl_checks):
    """Return a 2-tuple of info and detail.

    - info: 'pass' or 'fail'
    - detail: human-readable string indicating which implementation checks
      passed or failed. If implementation check as a whole passed, just return
      the passed check names; if it failed, just return the failed ones.

    """

    info = 'pass'
    failed_impl_checks = []
    passed_impl_checks = []
    for impl_check, checks in impl_checks.iteritems():
        passed_checks = []
        failed_checks = []
        for check, outcomes in checks.iteritems():
            for outcome in outcomes:
                if outcome == 'pass':
                    passed_checks.append(check)
                else:
                    info = 'fail'
                    failed_checks.append(check)
        if failed_checks:
            failed_impl_checks.append(
                'The implementation check %s returned'
                ' failure for the following check(s): %s.' % (
                    impl_check, ', '.join(failed_checks)))
        else:
            passed_impl_checks.append(
                'The implementation check %s returned'
                ' success for the following check(s): %s.' % (
                    impl_check, ', '.join(passed_checks)))
    if info == 'pass':
        if passed_impl_checks:
            return info, ' '.join(passed_impl_checks)
        return info, 'All checks passed.'
    else:
        return info, ' '.join(failed_impl_checks)


def main(target):
    """Return 0 if MediaConch can successfully assess whether the file at
    `target` is a valid Matroska (.mkv) file. Parse the XML output by
    MediaConch and print a JSON representation of that output.

    """

    try:
        doc = parse_mediaconch_data(target)
        impl_checks = get_impl_checks(doc)
        info, detail = get_event_outcome_information_detail(impl_checks)
        print json.dumps({
            'eventOutcomeInformation': info,
            'eventOutcomeDetailNote': detail
        })
        return 0
    except MediaConchException as e:
        return e


if __name__ == '__main__':
    target = sys.argv[1]
    sys.exit(main(target))
'''.strip()
