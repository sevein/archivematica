-- Database inserts/updates for issue #9478: MediaArea Tools Integration

-- Create the FPR tool, command, and rule for validating MKV files using
-- MediaConch.

SET @tool_uuid = 'f79c56f1-2d42-440a-8a1f-f40888e24bca' COLLATE utf8_unicode_ci;
SET @command_uuid = '287656fb-e58f-4967-bf72-0bae3bbb5ca8' COLLATE utf8_unicode_ci;
SET @rule_uuid = 'a2fb0477-6cde-43f8-a1c9-49834913d588' COLLATE utf8_unicode_ci;
INSERT INTO `fpr_fptool` (
    `uuid`,
    `description`,
    `version`,
    `enabled`,
    `slug`
) VALUES (
    @tool_uuid,
    'MediaConch',
    '16.05',
    1,
    'mediaconch-1605'
);
INSERT INTO `fpr_fpcommand` (
    `replaces_id`,
    `enabled`,
    `lastmodified`,
    `uuid`,
    `tool_id`,
    `description`,
    `command`,
    `script_type`,
    `output_location`,
    `output_format_id`,
    `command_usage`,
    `verification_command_id`,
    `event_detail_command_id`
) VALUES (
    NULL,
    1,
    '2016-07-04 23:39:31',
    @command_uuid,
    @tool_uuid,
    'Validate using MediaConch',
    'import json\nimport subprocess\nimport sys\nimport uuid\n\nfrom lxml import etree\n\nclass MediaConchException(Exception):\n    pass\n\nNS = \'{https://mediaarea.net/mediaconch}\'\n\ndef parse_mediaconch_data(target):\n    \"\"\"Run `mediaconch -mc -iv 4 -fx <target>` against `target` and return an\n    lxml etree parse of the output.\n\n    .. note::\n\n        At present, MediaConch (v. 16.05) will give terse output so long as you\n        provide *some* argument to the -iv option. With no -iv option, you will\n        get high verbosity. To be specific, low verbosity means that only\n        checks whose tests fail in the named \"MediaConch EBML Implementation\n        Checker\" will be displayed. If none fail, the EBML element will contain\n        no <check> elements.\n\n    \"\"\"\n\n    args = [\'mediaconch\', \'-mc\', \'-iv\', \'4\', \'-fx\', target]\n    try:\n        output = subprocess.check_output(args)\n    except subprocess.CalledProcessError:\n        raise JhoveException(\"MediaConch failed when running: %s\" % (\n            \' \'.join(args),))\n    return etree.fromstring(output)\n\n\ndef get_impl_check_name(impl_check_el):\n    name_el = impl_check_el.find(\'%sname\' % NS)\n    if name_el is not None:\n        return name_el.text\n    else:\n        return \'Unnamed Implementation Check %s\' % uuid.uuid4()\n\n\ndef get_check_name(check_el):\n    return check_el.attrib.get(\'name\',\n        check_el.attrib.get(\'icid\', \'Unnamed Check %s\' % uuid.uuid4()))\n\n\ndef get_check_tests_outcomes(check_el):\n    \"\"\"Return a list of outcome strings for the <check> element `check_el`.\"\"\"\n    outcomes = []\n    for test_el in check_el.iterfind(\'%stest\' % NS):\n        outcome = test_el.attrib.get(\'outcome\')\n        if outcome:\n            outcomes.append(outcome)\n    return outcomes\n\n\ndef get_impl_check_result(impl_check_el):\n    \"\"\"Return a dict mapping check names to lists of test outcome strings.\"\"\"\n\n    checks = {}\n    for check_el in impl_check_el.iterfind(\'%scheck\' % NS):\n        check_name = get_check_name(check_el)\n        test_outcomes = get_check_tests_outcomes(check_el)\n        if test_outcomes:\n            checks[check_name] = test_outcomes\n    return checks\n\n\ndef get_impl_checks(doc):\n    \"\"\"When not provided with a policy file, MediaConch produces a series of\n    XML <implementationChecks> elements that contain <check> sub-elements. This\n    function returns a dict mapping implementation check names to dicts that\n    map individual check names to lists of test outcomes, i.e., \'pass\' or\n    \'fail\'.\n\n    \"\"\"\n\n    impl_checks = {}\n    path = \'.%smedia/%simplementationChecks\' % (NS, NS)\n    for impl_check_el in doc.iterfind(path):\n        impl_check_name = get_impl_check_name(impl_check_el)\n        impl_check_result = get_impl_check_result(impl_check_el)\n        if impl_check_result:\n            impl_checks[impl_check_name] = impl_check_result\n    return impl_checks\n\n\ndef get_event_outcome_information_detail(impl_checks):\n    \"\"\"Return a 2-tuple of info and detail.\n\n    - info: \'pass\' or \'fail\'\n    - detail: human-readable string indicating which implementation checks\n      passed or failed. If implementation check as a whole passed, just return\n      the passed check names; if it failed, just return the failed ones.\n\n    \"\"\"\n\n    info = \'pass\'\n    failed_impl_checks = []\n    passed_impl_checks = []\n    for impl_check, checks in impl_checks.iteritems():\n        passed_checks = []\n        failed_checks = []\n        for check, outcomes in checks.iteritems():\n            for outcome in outcomes:\n                if outcome == \'pass\':\n                    passed_checks.append(check)\n                else:\n                    info = \'fail\'\n                    failed_checks.append(check)\n        if failed_checks:\n            failed_impl_checks.append(\'The implementation check %s returned\'\n                \' failure for the following check(s): %s.\' % (impl_check,\n                \', \'.join(failed_checks)))\n        else:\n            passed_impl_checks.append(\'The implementation check %s returned\'\n                \' success for the following check(s): %s.\' % (impl_check,\n                \', \'.join(passed_checks)))\n    if info == \'pass\':\n        if passed_impl_checks:\n            return info, \' \'.join(passed_impl_checks)\n        return info, \'All checks passed.\'\n    else:\n        return info, \' \'.join(failed_impl_checks)\n\n\ndef main(target):\n    \"\"\"Return 0 if MediaConch can successfully assess whether the file at\n    `target` is a valid Matroska (.mkv) file. Parse the XML output by\n    MediaConch and print a JSON representation of that output.\n\n    \"\"\"\n\n    try:\n        doc = parse_mediaconch_data(target)\n        impl_checks = get_impl_checks(doc)\n        info, detail = get_event_outcome_information_detail(impl_checks)\n        print json.dumps({\n            \'eventOutcomeInformation\': info,\n            \'eventOutcomeDetailNote\': detail\n        })\n        return 0\n    except MediaConchException as e:\n        return e\n\n\nif __name__ == \'__main__\':\n    target = sys.argv[1]\n    sys.exit(main(target))\n\n',
    'pythonScript',
    NULL,
    NULL,
    'validation',
    NULL,
    NULL
);
SELECT uuid INTO @matroska_format_uuid
    FROM fpr_formatversion
    WHERE description = 'Generic MKV';
INSERT INTO `fpr_fprule` (
    `replaces_id`,
    `enabled`,
    `lastmodified`,
    `uuid`,
    `purpose`,
    `command_id`,
    `format_id`,
    `count_attempts`,
    `count_okay`,
    `count_not_okay`
) VALUES (
    NULL,
    1,
    '2016-06-29 22:04:08',
    @rule_uuid,
    'validation',
    @command_uuid,
    @matroska_format_uuid,
    0,
    0,
    0
);

-- Create the standard task config for the Validate
-- Normalization micro-service.

SET @vldt_nrmlztn_stc_pk = 'f8bc7b43-8bd4-4db8-88dc-d6f55732fb63' COLLATE utf8_unicode_ci;
INSERT INTO StandardTasksConfigs VALUES (
    @vldt_nrmlztn_stc_pk,
    NULL,
    NULL,
    'objects/',
    0,
    NULL,
    NULL,
    'validateNormalizedFile_v0.0',
    '"%relativeLocation%" "%fileUUID%" "%SIPUUID%"',
    NULL,
    '2016-07-14 21:34:31');

-- Create the task config for the Validate
-- Normalization micro-service.

SELECT pk INTO @for_each_file_type_pk
    FROM TaskTypes
    WHERE description='for each file';
SET @vldt_nrmlztn_tc_pk = 'b6479474-159d-47aa-a10f-40495cb0e273' COLLATE utf8_unicode_ci;
INSERT INTO TasksConfigs VALUES (
    @vldt_nrmlztn_tc_pk,
    @for_each_file_type_pk,
    @vldt_nrmlztn_stc_pk,
    'Validate preservation normalization',
    NULL,
    '2016-07-14 21:34:31');

-- Create the micro-service chain link for the Validate
-- Normalization micro-service.

SET @vldt_nrmlztn_mcrsrvc_cl_pk = '5b0042a2-2244-475c-85d5-41e4b11e65d6' COLLATE utf8_unicode_ci;
SELECT exitCodes.nextMicroServiceChainLink
    INTO @set_file_perm_cl_pk
    FROM MicroServiceChainLinks as ms
    INNER JOIN TasksConfigs as task
        ON currentTask=task.pk
    INNER JOIN MicroServiceChainLinksExitCodes as exitCodes
        ON exitCodes.microServiceChainLink=ms.pk
    WHERE task.description='Normalize for preservation'
    LIMIT 1;
INSERT INTO MicroServiceChainLinks VALUES (
    @vldt_nrmlztn_mcrsrvc_cl_pk,
    @vldt_nrmlztn_tc_pk,
    @set_file_perm_cl_pk,
    'Normalize',
    1,
    'Failed',
    NULL,
    '2016-07-14 21:34:31');

-- There are two chain links with the task config description
-- 'Normalize for preservation'. Get both of their pks in MySQL
-- variables.

SELECT ms.pk
   INTO @nrmlz_prsrvtn_cl_pk_1
   FROM MicroServiceChainLinks as ms
   INNER JOIN TasksConfigs as task
       ON task.pk = ms.currentTask
   WHERE task.description='Normalize for preservation'
   LIMIT 1;
SELECT ms.pk
    INTO @nrmlz_prsrvtn_cl_pk_2
    FROM MicroServiceChainLinks as ms
    INNER JOIN TasksConfigs as task
        ON task.pk = ms.currentTask
    WHERE task.description='Normalize for preservation'
    LIMIT 1, 1;

-- Update the six MSCL exit code rows for the 'Normalize for
-- preservation' chain links so that they exit to the 'Validate
-- preservation normalization' chain link.

UPDATE MicroServiceChainLinksExitCodes
    SET nextMicroServiceChainLink = @vldt_nrmlztn_mcrsrvc_cl_pk
    WHERE microServiceChainLink
    IN (@nrmlz_prsrvtn_cl_pk_1, @nrmlz_prsrvtn_cl_pk_2);

-- Create three new MSCL exit code rows that cause the Validate
-- Normalization CL to exit to the Set File Permissions CL.

SET @exit_code_pk_1 = 'f574f94f-c431-4442-a554-ac0934ccac93' COLLATE utf8_unicode_ci;
SET @exit_code_pk_2 = 'd922a98b-2d65-4d75-bae0-9e8a446cb289' COLLATE utf8_unicode_ci;
SET @exit_code_pk_3 = 'ba7d93fb-64b9-4553-bed3-9738a524ff00' COLLATE utf8_unicode_ci;
INSERT INTO MicroServiceChainLinksExitCodes
    VALUES (
    @exit_code_pk_1,
    @vldt_nrmlztn_mcrsrvc_cl_pk,
    0,
    @set_file_perm_cl_pk,
    'Completed successfully',
    NULL,
    '2016-07-14 21:34:31');
INSERT INTO MicroServiceChainLinksExitCodes
    VALUES (
    @exit_code_pk_2,
    @vldt_nrmlztn_mcrsrvc_cl_pk,
    1,
    @set_file_perm_cl_pk,
    'Completed successfully',
    NULL,
    '2016-07-14 21:34:31');
INSERT INTO MicroServiceChainLinksExitCodes
    VALUES (
    @exit_code_pk_3,
    @vldt_nrmlztn_mcrsrvc_cl_pk,
    2,
    @set_file_perm_cl_pk,
    'Completed successfully',
    NULL,
    '2016-07-14 21:34:31');

-- Create the FPR rule that links the existing 'Validate using
-- MediaConch' to 'Generic MKV' files.

SET @vldt_nrmlztn_rule_pk = '3fcbf5d2-c908-4ec4-b618-8c7dc0f4117e' COLLATE utf8_unicode_ci;
SELECT uuid
    INTO @matroska_format_uuid
    FROM fpr_formatversion
    WHERE description = 'Generic MKV';
SELECT uuid
    INTO @mediaconch_cmd_pk
    FROM fpr_fpcommand
    WHERE description = 'Validate using MediaConch';
INSERT INTO `fpr_fprule` (
        `replaces_id`,
        `enabled`,
        `lastmodified`,
        `uuid`,
        `purpose`,
        `command_id`,
        `format_id`,
        `count_attempts`,
        `count_okay`,
        `count_not_okay`
    ) VALUES (
        NULL,
        1,
        '2016-07-14 21:34:31',
        @vldt_nrmlztn_rule_pk,
        'validateNormalizedFile',
        @mediaconch_cmd_pk,
        @matroska_format_uuid,
        0,
        0,
        0
    );

