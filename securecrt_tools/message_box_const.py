# #############################################  MESSAGE BOX CONSTANTS  ################################################
#
# These constants can be used for MessageBox creation.
#
# One item from each category can be OR'd ( | ) or added ( + ) together to combine a single value to represent the
# layout of a SecureCRT message box.  For example, if you want a message box that displays a question mark icon,
# prompts with a Yes and No button and No should be the default answer you can pass
# "ICON_QUESTION + BUTTON_YESNO + DEFBUTTON2" into the message_box() function as the third input parameter.
#
# NOTE:  To reference these names in your scripts, make sure to import them into your script file using:
#        "from securecrt_tools.message_box_const import *"
#
# CATEGORY 1 - DISPLAY ICON
ICON_STOP = 16                 # display the ERROR/STOP icon.
ICON_QUESTION = 32             # display the '?' icon
ICON_WARN = 48                 # display a '!' icon.
ICON_INFO = 64                  # displays "info" icon.
#
# CATEGORY 2 - BUTTON LAYOUT
BUTTON_OK = 0                  # OK button only
BUTTON_CANCEL = 1              # OK and Cancel buttons
BUTTON_ABORTRETRYIGNORE = 2    # Abort, Retry, and Ignore buttons
BUTTON_YESNOCANCEL = 3         # Yes, No, and Cancel buttons
BUTTON_YESNO = 4               # Yes and No buttons
BUTTON_RETRYCANCEL = 5         # Retry and Cancel buttons
#
# CATEGORY 3 - DEFAULT BUTTON SELECTION
DEFBUTTON1 = 0        # First button is default
DEFBUTTON2 = 256      # Second button is default
DEFBUTTON3 = 512      # Third button is default
#
#
# POSSIBLE RETURN VALUES
IDOK = 1              # OK button clicked
IDCANCEL = 2          # Cancel button clicked
IDABORT = 3           # Abort button clicked
IDRETRY = 4           # Retry button clicked
IDIGNORE = 5          # Ignore button clicked
IDYES = 6             # Yes button clicked
IDNO = 7              # No button clicked