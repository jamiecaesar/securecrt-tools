# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
import csv
from operator import itemgetter

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import utilities

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    | SINGLE device script
    | Morphed: Gordon Rogier grogier@cisco.com
    | Framework: Jamie Caesar jcaesar@presidio.com

    This script will capture details about the APs that are connected to the Wireless LAN Controller that this script
    is being run against and will output details for each AP into a CSV file.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["AireOS"])

    # Get additional information we'll need
    get_ap_detail(session, to_cvs=True)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


def get_ap_detail(session, to_cvs=False):
    """
    A function that captures the WLC AireOS ap details and returns an output list

    :param session: The script object that represents this script being executed
    :type session: session.Session

    :return: A list AP details
    :rtype: list of dicts
    """

    AP_Name_Key = "AP_Name"
    AP_80211A_suffix = "_80211_A"
    AP_80211B_suffix = "_80211_B"
    AP_Slot1_suffix = "_Slot_1"
    AP_Slot0_suffix = "_Slot_0"
    AP_CDP_mid = "_CDP_"

    output_raw = ''
    send_cmd = "show ap summary"
    output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_summary.template")
    ap_summ_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)

    def collect_it(in_list_of_dict, in_send_cmd, in_send_cmd_key, in_template_filename, in_key_suffix=''):
        # start with an empty output
        this_output_raw = ''
        # step across each dict entry in the list
        for this_dict_entry in in_list_of_dict:
            # send the in_send_cmd and add to it per dict entry aspect defined by the in_send_cmd_key
            this_send_cmd = in_send_cmd + format(this_dict_entry[in_send_cmd_key])
            # add this to the overall output to be processed
            this_output_raw += session.get_command_output(this_send_cmd)
        # use the template file provided & process the overall output
        processing_template_file = session.script.get_template(in_template_filename)
        processing_list_of_dict = utilities.textfsm_parse_to_dict(this_output_raw, processing_template_file)
        # start with an empty out_list_of_dict
        out_list_of_dict = []
        for this_dict_entry in processing_list_of_dict:
            # start with an empty change_dict_entry
            change_dict_entry = {}
            # step across each key
            for this_key in this_dict_entry.keys():
                # don't change the primary key name .. for the key:value entry
                if this_key == in_send_cmd_key: change_dict_entry[this_key] = this_dict_entry[this_key]
                # for the rest of the keys, add the suffix .. for the key:value entry
                else: change_dict_entry[this_key+in_key_suffix] = this_dict_entry[this_key]
            # now with key names changed, append the change_dict_entry
            out_list_of_dict.append(change_dict_entry)
        return out_list_of_dict

    def merge_it(in_base_list_of_dict, in_add_list_of_dict):
        # Now merge the various collected data
        out_list_of_dict = []
        # step across the original in_base_list_of_dict
        for base_dict_entry in in_base_list_of_dict:
            # start with what came from the base dict entry
            process_dict_entry = base_dict_entry
            # now for each of the sub command lists, find the matching dict entry and update merge it
            for in_add_entry in in_add_list_of_dict:
                if in_add_entry[AP_Name_Key] == base_dict_entry[AP_Name_Key]:
                    process_dict_entry.update(in_add_entry)
            out_list_of_dict.append(process_dict_entry)
        return(out_list_of_dict)

    dummy_dict_entry = {}
    dummy_dict_entry[AP_Name_Key] = ""
    dummy_list_of_dict = [dummy_dict_entry]

    ap_config_general_list_of_dict = collect_it(ap_summ_list_of_dict, "show ap config general ", AP_Name_Key, \
                                                "cisco_aireos_show_ap_config_general.template" )
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_config_general_list_of_dict)

    ap_config_slot_1_list_of_dict = collect_it(ap_summ_list_of_dict, "show ap config slot 1 ", AP_Name_Key, \
                                                "cisco_aireos_show_ap_config_slot.template", AP_Slot1_suffix)
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_config_slot_1_list_of_dict)

    ap_config_slot_0_list_of_dict = collect_it(ap_summ_list_of_dict, "show ap config slot 0 ", AP_Name_Key, \
                                                "cisco_aireos_show_ap_config_slot.template", AP_Slot0_suffix)
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_config_slot_0_list_of_dict)

    ap_TxPower_80211_A_list_of_dict = collect_it(dummy_list_of_dict, "show advanced 802.11a txpower", AP_Name_Key, \
                                                "cisco_aireos_show_advanced_txpower.template", AP_80211A_suffix)
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_TxPower_80211_A_list_of_dict)

    ap_TxPower_80211_B_list_of_dict = collect_it(dummy_list_of_dict, "show advanced 802.11b txpower", AP_Name_Key, \
                                                "cisco_aireos_show_advanced_txpower.template", AP_80211B_suffix)
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_TxPower_80211_B_list_of_dict)

    ap_cdp_list_of_dict = collect_it( dummy_list_of_dict, "show ap cdp neighbors detail all", AP_Name_Key, \
                                                "cisco_aireos_show_ap_cdp_neighbors_detail_all.template")
    ap_list_of_dict = merge_it(ap_summ_list_of_dict, ap_cdp_list_of_dict)

    output = ap_list_of_dict

    if to_cvs:
        ap_list_of_dict.sort(key=itemgetter(AP_Name_Key))

        # build an overall list of keys for using as header
        key_list = []
        # first collect up the unique keys by stepping across each dict
        for ap_dict_entry in ap_list_of_dict:
            for this_key in ap_dict_entry.keys():
                if this_key not in key_list: key_list.append(this_key)
        # next sort the resulting key list
        key_list.sort()
        # now resequence to group up the sorted sections
        key_list_new = [AP_Name_Key, "AP_Model", "AP_MAC_Enet", "AP_IP_Conf", "AP_IP_Addr"]
        key_list_slot_1 = []
        key_list_slot_A = []
        key_list_slot_0 = []
        key_list_slot_B = []
        key_list_cdp = []
        key_list_misc = []
        for this_key in key_list:
            if (this_key not in key_list_slot_1) and (AP_Slot1_suffix in this_key):
                key_list_slot_1.append(this_key)
            elif (this_key not in key_list_slot_A) and (AP_80211A_suffix in this_key):
                key_list_slot_A.append(this_key)
            elif (this_key not in key_list_slot_0) and (AP_Slot0_suffix in this_key):
                key_list_slot_0.append(this_key)
            elif (this_key not in key_list_slot_B) and (AP_80211B_suffix in this_key):
                key_list_slot_B.append(this_key)
            elif (this_key not in key_list_cdp) and (AP_CDP_mid in this_key):
                key_list_cdp.append(this_key)
            elif (this_key not in key_list_misc) and  (this_key not in key_list_new):
                key_list_misc.append(this_key)
        key_list = key_list_new + key_list_misc \
                    + key_list_slot_1 + key_list_slot_A \
                    + key_list_slot_0 + key_list_slot_B \
                    + key_list_cdp

        output_filename = session.create_output_filename("ap-summ", ext=".csv")
        utilities.list_of_dicts_to_csv(output, output_filename, key_list, add_header=True)

    return output


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    try:
        script_main(crt_session)
    except Exception:
        crt_session.end_cisco_session()
        raise
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
