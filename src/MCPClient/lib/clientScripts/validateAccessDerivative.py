import sys
from custom_handlers import get_script_logger

import django
django.setup()
from main.models import Derivation, File

from validateDerivative import DerivativeValidator


class AccessDerivativeValidator(DerivativeValidator):

    purpose = 'validateAccessDerivative'
    not_derivative_msg = 'is not an access derivative'

    def is_derivative(self):
        """Returns ``True`` if ``file_model`` encodes an access derivative."""
        file_model = File.get(uuid=self.file_uuid)
        if file_model.filegrpuse == 'access':
            try:
                Derivation.objects.get(derived_file__uuid=self.file_uuid,
                                       event__isnull=True)
                return True
            except Derivation.DoesNotExist:
                return False
        else:
            return False


if __name__ == '__main__':
    logger = get_script_logger("archivematica.mcp.client.validateFile")
    file_path = sys.argv[1]
    file_uuid = sys.argv[2]
    sip_uuid = sys.argv[3]
    validator = AccessDerivativeValidator(file_path, file_uuid, sip_uuid)
    sys.exit(validator.validate())
