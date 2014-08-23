# $language = "python"
# $interface = "1.0"

# NoToggle.py
#
# Description:
#
# Port of NoToggle.vbs


# Be "tab safe" by getting a reference to the tab for which this script
# has been launched:
objTab = crt.GetScriptTab()

strLines = objTab.Screen.Selection

if not strLines.strip():
	crt.Dialog.MessageBox("No Text Selected!")


for line in strLines.splitlines():
	if line.startswith("no "):
		objTab.Screen.Send (line[3:]+'\r')
	else:	
		objTab.Screen.Send ("no "+line+ '\r')
