#!/usr/bin/env python2
from __future__ import print_function

from main.models import Derivation

from policyCheck import PolicyChecker


class DerivativePolicyChecker(PolicyChecker):

    purpose = 'checkingDerivativePolicy'

    def is_derivative(self):
        try:
            Derivation.objects.get(derived_file__uuid=self.file_uuid,
                                   event__event_type='normalization')
            return True
        except Derivation.DoesNotExist:
            return False

    def is_for_access(self):
        """Returns ``True`` if the file with UUID ``self.file_uuid`` is "for"
        access.
        """
        if self.file_model.filegrpuse == 'access':
            return True
        return False

    def we_check_this_type_of_file(self):
        if not self.is_derivative():
            print('File {uuid} is not a derivative; not performing a policy'
                  ' check.'.format(uuid=self.file_uuid))
            return False
        return True

if __name__ == '__main__':
    logger = get_script_logger(
        "archivematica.mcp.client.policyCheck")
    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    policies_dir = sys.argv[4]
    policy_checker = DerivativePolicyChecker(file_path, file_uuid, sip_uuid,
                                             policies_dir)
    sys.exit(policy_checker.check())

