# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
from datetime import datetime

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import sessions
from securecrt_tools import utilities
# Import message box constants names for use specifying the design of message boxes
from securecrt_tools.message_box_const import *

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ##################################################

def get_manufacture_date(serial):
    """
    A function that will decode the manufacture date of a device from its serial number.

    :param serial: The serial number of a Cisco device, which should be 11 digits long.
    :type serial: str

    :return: The month and year the device was manufactured in string format. (e.g. "September 2010")
    """
    logger.debug("Received {0} as input".format(serial))
    if len(serial) == 11:
        try:
            year = str(1996 + int(serial[3:5]))
            week = int(serial[5:7])
        except ValueError:
            logger.debug("Could not convert {0} or {1} to an int".format(serial[3:5], serial[5:7]))
            return ""
        date_of_serial = datetime.strptime('{} {} 1'.format(year, week), '%Y %W %w')
        return date_of_serial.strftime('%B %Y')
    else:
        logger.debug("Received serial {0} is not the correct length".format(serial))
        return ""


def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will connect to all devices in the provided CSV file and create an output report (also CSV format)
    containing inventory data about the devices, such as hostname, model number, code version, serial number,
    manufacture date, etc.

    This script checks that it will NOT be run in a connected tab.

    :param script: A subclass of the scripts.Script object that represents the execution of this particular script
                   (either CRTScript or DirectScript)
    :type script: scripts.Script
    """
    session = script.get_main_session()

    # If this is launched on an active tab, disconnect before continuing.
    logger.debug("<M_SCRIPT> Checking if current tab is connected.")
    if session.is_connected():
        logger.debug("<M_SCRIPT> Existing tab connected.  Stopping execution.")
        raise scripts.ScriptError("This script must be launched in a not-connected tab.")

    # Load a device list
    device_list = script.import_device_list()
    if not device_list:
        return

    # Check settings if we should use a proxy/jumpbox
    use_proxy = script.settings.getboolean("Global", "use_proxy")
    default_proxy_session = script.settings.get("Global", "proxy_session")

    # ########################################  START DEVICE CONNECT LOOP  ###########################################

    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{0}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    device_data = []
    for device in device_list:
        hostname = device['Hostname']
        protocol = device['Protocol']
        username = device['Username']
        password = device['Password']
        enable = device['Enable']
        try:
            proxy = device['Proxy Session']
        except KeyError:
            proxy = None

        if not proxy and use_proxy:
            proxy = default_proxy_session

        logger.debug("<M_SCRIPT> Connecting to {0}.".format(hostname))
        try:
            script.connect(hostname, username, password, protocol=protocol, proxy=proxy)
            session = script.get_main_session()
            device_data.extend(per_device_work(session, enable))
            script.disconnect()
        except scripts.ConnectError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("<M_SCRIPT> Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()
        except sessions.InteractionError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("<M_SCRIPT> Failure on {0}: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()
        except sessions.UnsupportedOSError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("<M_SCRIPT> Unsupported OS on {0}: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()

    # #########################################  END DEVICE CONNECT LOOP  ############################################

    # Write complete output to a CSV file
    session = script.get_main_session()
    output_filename = session.create_output_filename("INVENTORY_REPORT", ext='.csv', include_hostname=False)
    header_row = ['HOSTNAME', 'MODEL', 'VERSION', 'SERIAL', 'MANUFACTURE_DATE', 'UPTIME',
                  'LAST_REBOOT_REASON', 'HARDWARE', 'IMAGE']
    utilities.list_of_dicts_to_csv(device_data, output_filename, header_row)


def per_device_work(session, enable_pass):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    You can either put your own code here, or if there is a single-device version of a script that performs the correct
    task, it can be imported and called here, essentially making this script connect to all the devices in the chosen
    CSV file and then running a single-device script on each of them.
    """
    script = session.script
    interesting_keys = ['HARDWARE', 'HOSTNAME', 'MODEL', 'VERSION', 'SERIAL', 'UPTIME', 'LAST_REBOOT_REASON', 'IMAGE']

    # Validate device is of a proper OS
    supported_os = ['IOS', 'NXOS', 'ASA']
    session.start_cisco_session(enable_pass=enable_pass)
    session.validate_os(supported_os)

    # Select the appropriate template to process show version data
    if session.os == 'IOS':
        ver_template_file = script.get_template('cisco_ios_show_version.template')
    elif session.os == 'NXOS':
        ver_template_file = script.get_template('cisco_nxos_show_version.template')
    elif session.os == 'ASA':
        ver_template_file = script.get_template('cisco_asa_show_version.template')
    else:
        raise sessions.UnsupportedOSError("{0} isn't a supported OS.".format(session.os))

    # Process Show Version data
    raw_version = session.get_command_output('show version')
    fsm_output = utilities.textfsm_parse_to_dict(raw_version, ver_template_file)

    if len(fsm_output) > 1:
        raise sessions.InteractionError("Received multiple entries from a single device, which should not happen.")
    else:
        ver_info = fsm_output[0]

    # For NXOS get parse 'show inventory' for model and serial number
    if session.os == 'NXOS':
        ver_info['HOSTNAME'] = session.hostname
        logger.debug("<M_SCRIPT> NXOS device, getting 'show inventory'.")
        raw_inv = session.get_command_output('show inventory')
        inv_template_file = script.get_template('cisco_nxos_show_inventory.template')
        inv_info = utilities.textfsm_parse_to_dict(raw_inv, inv_template_file)
        for entry in inv_info:
            if entry['NAME'] == "Chassis":
                logger.debug("<M_SCRIPT> Adding {0} as model number".format(entry['PID']))
                ver_info['MODEL'] = entry['PID']
                logger.debug("<M_SCRIPT> Adding {0} as serial number".format(entry['SN']))
                ver_info['SERIAL'] = entry['SN']
                break
    elif session.os == 'ASA':
        logger.debug("<M_SCRIPT> ASA device, writing 'N/A' for last reboot reason.")
        # For ASA put a N/A reload reason since ASA doesn't have this output
        ver_info['LAST_REBOOT_REASON'] = "N/A"
        # If we don't have a model number in older 'show ver' extract it from the hardware column.
        if not ver_info['MODEL']:
            model = ver_info['HARDWARE'].split(',')[0]
            logger.debug("<M_SCRIPT> ASA device without model, using {0}".format(model))
            ver_info['MODEL'] = model
    elif session.os == 'IOS':
        # Expand multiple serial numbers found in stacks, or just remove lists for serial and model if only 1 device
        logger.debug("<M_SCRIPT> IOS device, writing list of serials/models to separate entries")
        num_in_stack = len(ver_info['SERIAL'])
        if len(ver_info['MODEL']) != num_in_stack:
            # For older IOS, we may not get a model number, but we'll pick up the hardware.  As long as this happens
            # when only 1 serial is detected (not a switch stack), then just use the HARDWARE for the model number.
            if len(ver_info['MODEL']) == 0 and num_in_stack == 1 and ver_info['HARDWARE']:
                ver_info['MODEL'] = [ver_info['HARDWARE']]
            else:
                logger.debug("<M_SCRIPT> List of Serials & Models aren't the same length. Likely TextFSM parsing problem.")
                raise sessions.InteractionError("Received {0} serial nums and only {1} model nums in output."
                                                .format(num_in_stack, len(ver_info['MODEL'])))
        new_output = []
        for x in range(num_in_stack):
            stack_subset = dict((key, ver_info[key]) for key in interesting_keys)
            stack_subset['HOSTNAME'] = "{0}-{1}".format(ver_info['HOSTNAME'], x+1)
            stack_subset['SERIAL'] = ver_info['SERIAL'][x]
            stack_subset['MODEL'] = ver_info['MODEL'][x]
            new_output.append(stack_subset)
            logger.debug("Created an entry for {0}/{1}".format(stack_subset['MODEL'], stack_subset['SERIAL']))
        fsm_output = new_output

    # Create output data structure with only the keys that we need.
    inv_data = []
    logger.debug("Creating list of dictionaries to return, and adding manufacture dates.")
    for entry in fsm_output:
        subset = dict((key, entry[key]) for key in interesting_keys)
        subset['MANUFACTURE_DATE'] = get_manufacture_date(subset['SERIAL'])
        inv_data.append(subset)

    # End session on the Cisco device
    session.end_cisco_session()

    return inv_data


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Run script's main logic against the script object
    script_main(crt_script)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Run script's main logic against the script object
    script_main(direct_script)
    # Shutdown logging after
    logging.shutdown()