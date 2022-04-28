# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QNSPECT
                                 A QGIS plugin
 QGIS Plugin for NOAA Nonpoint Source Pollution and Erosion Comparison Tool (NSPECT)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-12-29
        copyright            : (C) 2021 by NOAA
        email                : ocm dot nspect dot admins at noaa dot gov
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = "NOAA"
__date__ = "2021-12-29"
__copyright__ = "(C) 2021 by NOAA"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

import os
import inspect
from qgis.PyQt.QtGui import QIcon

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm


class QNSPECTAlgorithm(QgsProcessingAlgorithm):
    """
    Base class for QNSPECT Algorithms
    """

    _version = 0.1

    def icon(self):
        """
        Returns the algorithm's icon.
        """
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        icon = QIcon(
            os.path.join(os.path.dirname(cmd_folder), "resources/branding/icon.svg")
        )
        return icon

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)
