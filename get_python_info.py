# $language = "python"
# $interface = "1.0"

import sys

path = sys.path
path_str = ",\n".join(path)
crt.Dialog.MessageBox("Python Version:\n{0}\n\nPython Path:\n{1}".format(str(sys.version), path_str))
