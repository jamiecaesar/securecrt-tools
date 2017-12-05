Writing Your Own Scripts
========================
For those who have a need to either modify the existing scripts or write completely new ones for specific use cases (I expect that will be the majority), this section has documentation on the classes used to build the scripts in this repository.

The purpose of building the below classes is to encapsulate many of the common tasks that will be performed on any device so that those methods can simply be called, instead of requiring each person to either copy and paste a lot of blocks of code, or understand the intricate details of interacting with a remote device through SecureCRT.  While that may be required for certain use cases, the goal is that a vast majority of the interaction can be handled using the existing methods documented below.

Before creating a new script, look at the `templates/` directory, which contains boilerplate starting points for new scripts.  The sections where code is meant to be added has been marked with comments saying "ADD YOUR CODE HERE".

There are 2 categories of modules shown below:
1) The modules written to handle the interaction between these scripts and the remote devices (via SecureCRT), and
2) 3rd Party modules that are used within some of the scripts to help process our device outputs better.

The 3rd Party modules are included because someone has already done the work to create modules that perform specific funtions, so there is no reason we shouldn't take advantage of that instead of writing our own (and probably more buggy) implementations.  For better or worse, SecureCRT includes it's own Python environment within the application, which means we cannot install new modules like we can for a local installation of Python.  Instead we have to include the source code in this repository for the 3rd party modules so we can use them.

A Note on TextFSM
=================
TextFSM is a module written to simply the process of extracting information out of semi-structured outputs (such as CLI command output) that are meant for human readability.  TextFSM uses a template file to define what values we are looking for, as well as how those values get extracted from the output.  You can read some examples of using the `TextFSM Wiki <https://github.com/google/textfsm/wiki/TextFSM>`_ and the `Code Lab <https://github.com/google/textfsm/wiki/Code-Lab>`_ section for additional examples.

In addition, there is a large repository of TextFSM templates located in `Network To Code's Github Repository <https://github.com/networktocode/ntc-templates>`_.  This repository contains TextFSM templates for a variety of vendors and to process a large number of commands.  At best, they'll have the template you need that is already created, but in some cases you may need to modify the template to get what you want from it.

In the end, TextFSM still boils down to text matching with *Regular Expressions* (RegEx), although TextFSM puts some structure around it that makes it much easier than trying to write matching by-hand -- especially for more complicated outputs like a routing table.  If you are unfamiliar with RegEx, I'm sure there are plenty of primers on how they work online.  I would highly recommend that if you are trying to develop some new regular expressions or a TextFSM template that you use a site such as `regex101.com <https://regex101.com/>`_ to see real-time feedback of what your expressions will match against some sample data you've pasted into the site.

Module Documentation
====================

.. toctree::
   :maxdepth: 4

   securecrt_tools
   3rdparty
