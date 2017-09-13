evo
===

***Python package for the evaluation of odometry and SLAM***

This packages provides executables and a small library for handling and
evaluating and the trajectory output of odometry and SLAM algorithms.

Supported trajectory formats:

-  'TUM' trajectory files
-  'KITTI' pose files
-  'EuRoC MAV' (.csv groundtruth and TUM trajectory file)
-  ROS bagfile with geometry\_msgs/PoseStamped topics

.. raw:: html

   <!---
   <img src="evo/doc/traj_demo.png" alt="evo" height="180" border="10" />
   -->

.. raw:: html

   <center>

.. raw:: html

   </center>

--------------

Installation
------------

**Python 3.4+** and **Python 2.7** are both supported. If you want to
use the ROS bagfile interface, first check which Python version is used
by your ROS installation and install the dependencies accordingly, if
required. You might also want to use a `virtual
environment <evo/doc/install_in_virtualenv.md>`__.

From PyPi
~~~~~~~~~

If you just want to use the executables of the latest release version,
the easiest way is to run:

.. code:: bash

    pip install evo --upgrade

This will download the package and its dependencies from PyPi and
install them. Tab completion for Bash terminals is supported via the
argcomplete package on most UNIX systems - open a new shell after the
installation to use it.

From Source
~~~~~~~~~~~

Run this in the repository's base folder:

.. code:: bash

    pip install . --upgrade

Dependencies
~~~~~~~~~~~~

**Python packages**

evo has the following dependencies that are ***automatically resolved***
during installation:

*numpy, matplotlib, scipy, pandas, seaborn, natsort, argcomplete,
colorama, pygments, enum34 (only Python 2.7)*

**PyQt4 (optional)**

It is optional but recommended to install PyQt4 before installation,
which will give you the enhanced editing tools for plot figures from the
"*Qt4Agg*" matplotlib backend (otherwise: "*TkAgg*"). If PyQt4 is
already installed when installing this package, it will be used as a
default. To change the plot backend afterwards, run
``evo_config set plot_backend Qt4Agg``.

**ROS (optional)**

To load or export ROS bag files, you need to install ROS - see
`here <http://www.ros.org/>`__. We tested this package with ROS Indigo
and Kinetic.

--------------

Run Executables
---------------

After installation with setup.sh, setup.py or from pip, the following
console commands can be called globally from your command-line:

**Metrics:**

-  ``evo_ape`` - absolute pose error
-  ``evo_rpe`` - relative pose error
-  ``evo_rpe-for-each`` - sub-sequence-wise averaged relative pose error

**Tools:**

-  ``evo_traj`` - tool for analyzing, plotting or exporting one or more
   trajectories
-  ``evo_res`` - tool for comparing one or multiple result files from
   ``evo_ape`` or ``evo_rpe``
-  ``evo_fig`` - (experimental) tool for re-opening serialized plots
   (saved with ``--serialize_plot``)
-  ``evo_config`` - tool for global settings and config file
   manipulation

Call the commands with ``--help`` to see the options, e.g.
``evo_ape --help``. Tab-completion of command line parameters is
available on UNIX systems.

**Configurations**

Some global settings of the package (see ``evo_config show``) can be
changed via ``evo_config set``.

Configuration JSON files can be used to store command line parameters of
an experiment and can be passed to the executables via
``--config``/``-c`` - see ``config_ape.example.json`` and
``config_rpe.example.json`` in the source folder for examples. Use
``evo_config generate`` to quickly generate such config files.

--------------

Example Workflow
----------------

There are some example trajectories in the source folder in
``evo/test/data``.

1. ***Plot multiple trajectories***

Here, we plot two KITTI pose files and the ground truth using
``evo_traj``:
``cd evo/test/data   evo_traj kitti KITTI_00_ORB.txt KITTI_00_SPTAM.txt --ref=KITTI_00_gt.txt -p --plot_mode=xz``

.. raw:: html

   <center>

.. raw:: html

   </center>

2. ***Run a metric on trajectories***

For example, here we calculate the absolute pose error for two
trajectories from ORB-SLAM and S-PTAM using ``evo_ape`` and plot and
save the individual results to .zip files:

*First trajectory (ORB Stereo):*

``mkdir results   evo_ape kitti KITTI_00_gt.txt KITTI_00_ORB.txt -va --plot --save_results results/ORB.zip``

.. raw:: html

   <center>

.. raw:: html

   </center>

*Second trajectory (S-PTAM):*

``evo_ape kitti KITTI_00_gt.txt KITTI_00_SPTAM.txt -va --plot --save_results results/SPTAM.zip``

.. raw:: html

   <center>

.. raw:: html

   </center>

3. ***Process multiple results from a metric***

``evo_res`` can be used to compare multiple result files from the
metrics, i.e.: \* print infos and statistics (default) \* plot the
results \* save the statistics in a table

Here, we use the results from above to generate a plot and a table:
``evo_res results/*.zip -p --save_table results/table.csv``

.. raw:: html

   <center>

.. raw:: html

   </center>

--------------

Jupyter Notebooks
-----------------

For an interactive source code documentation, open the `Jupyter
notebook <http://jupyter.readthedocs.io/en/latest/install.html>`__
``metrics_tutorial.ipynb``

To install Jupyter, call ``pip install jupyter`` or use the
``--with_jupyter`` flag for ``setup.sh``.

Local Jupyter notebook access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to the ``evo`` source folder in a terminal and run:
``jupyter notebook`` (starts server and opens browser window with
notebook).

Remote Jupyter notebook access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Notebook servers can also be accessed via the browser of a remote PC on
the local network without installing Jupyter.

**Do once:**

-  disable tokens on your **server** side:
-  ``jupyter notebook --generate-config``
-  go to the generated config file, uncomment and change the
   ``c.NotebookApp.token`` parameter to an empty string
-  **TODO**: enable password authentication without annoying tokens

**Anytime you want to start a server:**

-  start the notebook on the **server**:
   ``jupyter notebook --no-browser --port=8888``
-  access notebook on **remote** PC:
-  establish SSH forwarding:
   ``ssh username@remotehost -L 8889:localhost:8888``
-  this forwards remote 8888 port to local 8889 (numbers are just
   examples)
-  open the notebook in a browser: ``localhost:8889``

--------------

Trouble
-------

Append ``-h``/ ``--help`` or ``--debug`` to your command.

**Warnings from
`transformations.py <evo/algorithms/transformations.py>`__:**

``UserWarning: failed to import module _transformations``

Can be ignored, as written
`here <https://simoncblyth.bitbucket.io/env/notes/graphics/transformations/transformations/?>`__.

**Jupyter notebook errors**

``No module named 'evo'``

This can be caused if the Kernel version of Jupyter does not match the
Python version of the evo installation.

***For any other problems, feel free to open an issue on GitHub!***

--------------

License
-------

Free, modifiable open source software as covered by the GNU GPL v3 - see
the 'LICENSE' file for full information.
