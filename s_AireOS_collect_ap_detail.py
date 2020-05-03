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

    This script will

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
    info_list = get_ap_detail(session)
    info_list.sort(key=itemgetter('AP_Name'))

    # build an overall list of keys for using as header
    key_list = []
    # first collect up the unique keys by stepping across each dict
    for ap_dict_entry in info_list:
        for this_key in ap_dict_entry.keys():
            if this_key not in key_list: key_list.append(this_key)
    # next sort the resulting key list
    key_list.sort()
    # now resequence to group up the sorted sections
    key_list_new = ["AP_Name", "AP_Model", "AP_MAC_Enet", "AP_IP_Conf", "AP_IP_Addr"]
    key_list_slot_1 = []
    key_list_slot_A = []
    key_list_slot_0 = []
    key_list_slot_B = []
    key_list_cdp = []
    for this_key in key_list:
        if (this_key not in key_list_cdp) and ("_CDP_" in this_key): key_list_cdp.append(this_key)
        elif (this_key not in key_list_slot_B) and ("_80211_B" in this_key): key_list_slot_B.append(this_key)
        elif (this_key not in key_list_slot_0) and ("_Slot_0" in this_key): key_list_slot_0.append(this_key)
        elif (this_key not in key_list_slot_A) and ("_80211_A" in this_key): key_list_slot_A.append(this_key)
        elif (this_key not in key_list_slot_1) and ("_Slot_1" in this_key): key_list_slot_1.append(this_key)
        elif (this_key not in key_list_new) : key_list_new.append(this_key)
    key_list = key_list_new + key_list_slot_1 + key_list_slot_A + key_list_slot_0 + key_list_slot_B + key_list_cdp

    output_filename = session.create_output_filename("ap-summ", ext=".csv")
    utilities.list_of_dicts_to_csv(info_list, output_filename, key_list, add_header=True)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


def get_ap_detail(session):
    """
    A function that captures the WLC AireOS ap summary table and returns an output list

    :param session: The script object that represents this script being executed
    :type session: session.Session

    :return: A list of MAC information for AP summary
    :rtype: list of dicts
    """

    output_raw = ''
    send_cmd = "show ap summary"
    output_raw = session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_summary.template")
    ap_summ_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)

    AP_Name_Key = "AP_Name"
    AP_80211A_suffix = "_80211_A"
    AP_80211B_suffix = "_80211_B"
    AP_Slot1_suffix = "_Slot_1"
    AP_Slot0_suffix = "_Slot_0"

    # Collect "show ap config general "
    output_raw = ''
    for ap_dict_entry in ap_summ_list_of_dict:
        send_cmd = "show ap config general " + format(ap_dict_entry[AP_Name_Key])
        output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_config_general.template")
    ap_config_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)

    # Collect "show ap config slot 1 "
    output_raw = ''
    for ap_dict_entry in ap_summ_list_of_dict:
        send_cmd = "show ap config slot 1 " + format(ap_dict_entry[AP_Name_Key])
        output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_config_slot.template")
    ap_config_slot_X_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)
    ap_config_slot_1_list_of_dict = []
    for ap_dict_entry in ap_config_slot_X_list_of_dict:
        change_dict_entry = {}
        for this_key in ap_dict_entry.keys():
            if this_key == AP_Name_Key:
                change_dict_entry[this_key] = ap_dict_entry[this_key]
            else:
                change_dict_entry[this_key+AP_Slot1_suffix] = ap_dict_entry[this_key]
        ap_config_slot_1_list_of_dict.append(change_dict_entry)

    # Collect "show ap config slot 0 "
    output_raw = ''
    for ap_dict_entry in ap_summ_list_of_dict:
        send_cmd = "show ap config slot 0 " + format(ap_dict_entry[AP_Name_Key])
        output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_config_slot.template")
    ap_config_slot_X_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)
    ap_config_slot_0_list_of_dict = []
    for ap_dict_entry in ap_config_slot_X_list_of_dict:
        change_dict_entry = {}
        for this_key in ap_dict_entry.keys():
            if this_key == AP_Name_Key:
                change_dict_entry[this_key] = ap_dict_entry[this_key]
            else:
                change_dict_entry[this_key + AP_Slot0_suffix] = ap_dict_entry[this_key]
        ap_config_slot_0_list_of_dict.append(change_dict_entry)

    # Collect "show advanced 802.11a txpower"
    output_raw = ''
    send_cmd = "show advanced 802.11a txpower"
    output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_advanced_txpower.template")
    ap_TxPower_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)
    ap_TxPower_80211_A_list_of_dict = []
    for ap_dict_entry in ap_TxPower_list_of_dict:
        change_dict_entry = {}
        for this_key in ap_dict_entry.keys():
            if this_key == AP_Name_Key:
                change_dict_entry[this_key] = ap_dict_entry[this_key]
            else:
                change_dict_entry[this_key + AP_80211A_suffix] = ap_dict_entry[this_key]
        ap_TxPower_80211_A_list_of_dict.append(change_dict_entry)

    # Collect "show advanced 802.11b txpower"
    output_raw = ''
    send_cmd = "show advanced 802.11b txpower"
    output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_advanced_txpower.template")
    ap_TxPower_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)
    ap_TxPower_80211_B_list_of_dict = []
    for ap_dict_entry in ap_TxPower_list_of_dict:
        change_dict_entry = {}
        for this_key in ap_dict_entry.keys():
            if this_key == AP_Name_Key:
                change_dict_entry[this_key] = ap_dict_entry[this_key]
            else:
                change_dict_entry[this_key + AP_80211B_suffix] = ap_dict_entry[this_key]
        ap_TxPower_80211_B_list_of_dict.append(change_dict_entry)

    # Collect "show ap cdp neighbors detail all"
    output_raw = ''
    send_cmd = "show ap cdp neighbors detail all"
    output_raw += session.get_command_output(send_cmd)
    template_file = session.script.get_template("cisco_aireos_show_ap_cdp_neighbors_detail_all.template")
    ap_cdp_list_of_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)

    # Now merge the various collected data
    ap_list_of_dict = []
    for ap_dict_entry in ap_summ_list_of_dict:
        change_dict_entry = ap_dict_entry
        for ap_sub_dict_entry in ap_config_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)
        for ap_sub_dict_entry in ap_config_slot_0_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)
        for ap_sub_dict_entry in ap_config_slot_1_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)
        for ap_sub_dict_entry in ap_TxPower_80211_A_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)
        for ap_sub_dict_entry in ap_TxPower_80211_B_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)
        for ap_sub_dict_entry in ap_cdp_list_of_dict:
            if ap_sub_dict_entry[AP_Name_Key] == ap_dict_entry[AP_Name_Key]:
                change_dict_entry.update(ap_sub_dict_entry)

        ap_list_of_dict.append(change_dict_entry)

    output = ap_list_of_dict

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
