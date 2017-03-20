import os
import sys

path = os.environ.get('OPENSHIFT_PYTHON_DIR', '~/')
sys.path.insert(0, path)

from tempest_sendmail import app as application
