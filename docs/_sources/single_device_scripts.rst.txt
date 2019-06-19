=====================
Single Device Scripts
=====================

Single Device Scripts are scripts that are designed to be lauched in a SecureCRT tab that is already connected to a remote device.  These scripts will make necessary terminal changes, perform their task, and return the terminal back to the original state so that the user can continue working after the script executes.

These scripts can also be imported into Multi-Device scripts to reduce the amount of copying and pasting of code that is required to make a multi-device version.

.. toctree::
   :maxdepth: 1

   s_add_global_config
   s_arp_to_csv
   s_cdp_to_csv
   s_create_sessions_from_cdp
   s_document_device
   s_eigrp_topology_summary
   s_eigrp_topology_to_csv
   s_interface_stats
   s_mac_to_csv
   s_nexthop_summary
   s_save_output
   s_save_running
   s_switchport_mapping
   s_update_dhcp_relay
   s_update_interface_desc
   s_vlan_to_csv