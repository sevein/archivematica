#!/usr/bin/env python2
from __future__ import print_function

from main.models import Derivation

from policyCheckDerivative import DerivativePolicyChecker


class PreservationDerivativePolicyChecker(DerivativePolicyChecker):

    preservation_purpose = 'checkingPreservationDerivativePolicy'

    def we_check_this_type_of_file(self):
        if (not self.is_derivative()) or self.is_for_access():
            print('File {uuid} is not a preservation derivative; not performing'
                  ' a policy check.'.format(uuid=self.file_uuid))
            return False
        return True

if __name__ == '__main__':
    logger = get_script_logger(
        "archivematica.mcp.client.policyCheck")
    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    policies_dir = sys.argv[4]
    policy_checker = PreservationDerivativePolicyChecker(
        file_path, file_uuid, sip_uuid, policies_dir)
    sys.exit(policy_checker.check())
