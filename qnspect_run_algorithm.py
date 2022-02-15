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
        email                : shan dot burkhalter at noaa dot gov
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
__date__ = "2022-02-15"
__copyright__ = "(C) 2021 by NOAA"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

import os
import sys
from pathlib import Path
from json import load

from QNSPECT.qnspect_algorithm import QNSPECTAlgorithm

from qgis.core import (
    QgsVectorLayer,
    QgsProcessingException,
)

from QNSPECT.stylers import run_alg_styler


class QNSPECTRunAlgorithm(QNSPECTAlgorithm):
    """
    Base class for QNSPECT Run Algorithms
    """

    LAND_USE_TABLES = {1: "C-CAP", 2: "NLCD"}
    LAND_USE_PATH = f"file:///{Path(__file__).parent / 'resources' / 'coefficients'}"
    with open(f"{Path(__file__).parent / 'resources' / 'style-colors.json'}") as json_f:
        STYLE_COLORS = load(json_f)

    def group(self):
        return self.tr("Analysis")

    def groupId(self):
        return "analysis"

    def extract_lookup_table(
        self,
        parameters,
        context,
    ):
        """Extract the lookup table as a vector layer."""
        if parameters["LookupTable"]:
            return self.parameterAsVectorLayer(parameters, "LookupTable", context)

        land_use_type = self.parameterAsEnum(parameters, "LandUseType", context)
        if land_use_type > 0:
            return QgsVectorLayer(
                os.path.join(
                    self.LAND_USE_PATH, f"{self.LAND_USE_TABLES[land_use_type]}.csv"
                ),
                "Land Use Lookup Table",
                "delimitedtext",
            )
        else:
            raise QgsProcessingException(
                "Land Use Lookup Table must be provided with Custom Land Use Type.\n"
            )

    def handle_post_processing(self, entity: str, layer, display_name, context) -> None:
        layer_details = context.LayerDetails(
            display_name, context.project(), display_name
        )
        context.addLayerToLoadOnCompletion(
            layer,
            layer_details,
        )

        colors = self.STYLE_COLORS.get(entity, self.STYLE_COLORS["default"])
        if context.willLoadLayerOnCompletion(layer):
            context.layerToLoadOnCompletionDetails(layer).setPostProcessor(
                run_alg_styler(display_name, colors[0], colors[1])
            )
