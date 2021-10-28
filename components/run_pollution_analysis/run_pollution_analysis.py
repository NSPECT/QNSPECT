from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterString,
    QgsProcessingParameterFile,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterMatrix,
    QgsVectorLayer,
)
import processing


def filter_matrix(matrix: list) -> list:
    matrix_filtered = [
        matrix[i]
        for i in range(0, len(matrix), 2)
        if matrix[i + 1].lower() in ["y", "yes"]
    ]
    return matrix_filtered


class RunPollutionAnalysis(QgsProcessingAlgorithm):
    lookup_tables = {0: "NLCD", 1: "C-CAP"}
    default_lookup_path = r"file:///C:\Users\asiddiqui\Documents\github_repos\QNSPECT\resources\coefficients\{0}.csv"
    dual_soil_reclass = {0: [5, 9, 4], 1: [5, 5, 1, 6, 6, 2, 7, 7, 3, 8, 9, 4]}
    reference_raster = "Elevation Raster"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                "ProjectName",
                "Run Name",
                multiLine=False,
                optional=True,
                defaultValue="",
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "ProjectLocation",
                "Location for Run Output",
                optional=True,
                behavior=QgsProcessingParameterFile.Folder,
                fileFilter="All files (*.*)",
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ElevatoinRaster", "Elevation Raster", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "SoilRaster", "Soil Raster", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "DualSoils",
                "Treat Dual Category Soils as",
                optional=True,
                options=["Undrained [Default]", "Drained", "Average"],
                allowMultiple=False,
                defaultValue=[0],
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "PrecipitationRaster",
                "Precipitation Raster",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "RainUnits",
                "Rain Units",
                options=["Inches", "Millimeters"],
                optional=True,
                allowMultiple=False,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "RainyDays",
                "Number of Rainy Days in a Year",
                optional=True,
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                maxValue=366,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "LandUseRaster", "Land Use Raster", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "LandUseType",
                "Land Use Type",
                optional=True,
                options=["NLCD", "C-CAP", "Custom"],
                allowMultiple=False,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "LookupTable",
                "Land Use Lookup Table",
                optional=True,
                types=[QgsProcessing.TypeVector],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterMatrix(
                "DesiredOutputs",
                "Desired Outputs",
                optional=True,
                headers=["Name", "Output? [Y/N]"],
                defaultValue=[
                    "Runoff",
                    "Y",
                    "Lead",
                    "N",
                    "Nitrogen",
                    "N",
                    "Phosphorus",
                    "N",
                    "Zinc",
                    "N",
                    "TSS",
                    "N",
                ],
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
        results = {}
        outputs = {}

        ## Extract inputs
        land_use_type = self.parameterAsEnum(parameters, "LandUseType", context)
        desired_outputs = filter_matrix(
            self.parameterAsMatrix(parameters, "DesiredOutputs", context)
        )
        desired_pollutants = [
            pol.lower() for pol in desired_outputs if pol.lower() != "runoff"
        ]
        dual_soil_type = self.parameterAsEnum(parameters, "DualSoils", context)

        ## Extract Lookup Table
        if parameters["LookupTable"]:
            lookup_layer = self.parameterAsVectorLayer(
                parameters, "LookupTable", context
            )
        elif land_use_type in [0, 1]:  # create lookup table from default
            lookup_layer = QgsVectorLayer(
                self.default_lookup_path.format(self.lookup_tables[land_use_type]),
                "Land Use Lookup Table",
                "delimitedtext",
            )
        else:
            feedback.reportError(
                "Land Use Lookup Table must be provided with Custom Land Use Type.\n",
                True,
            )
            return {}
        lookup_fields = [f.name().lower() for f in lookup_layer.fields()]

        ## Assertions
        if not all([pol in lookup_fields for pol in desired_pollutants]):
            feedback.reportError(
                "One or more of the Pollutants is not a column in the Land Use Lookup Table. Either remove the pollutants from Desired Outputs or provide a custom lookup table with desired pollutants. \n",
                True,
            )

        # Build CN Expression
        cn_exprs = self.generate_cn_exprs(lookup_layer)

        # Preprocess Soil
        if dual_soil_type in [0, 1]:
            # replace soil type 5 to 9 per chosen option
            outputs["Soil"] = self.reclass_soil(
                self.dual_soil_reclass[dual_soil_type], parameters, context, feedback
            )

        elif dual_soil_type == 2:
            outputs["SoilUndrain"] = self.reclass_soil(
                self.dual_soil_reclass[0], parameters, context, feedback
            )
            outputs["SoilDrain"] = self.reclass_soil(
                self.dual_soil_reclass[1], parameters, context, feedback
            )

        # Generate CN Raster
        input_params = {
            "input_a": parameters["LandUseRaster"],
            "band_a": "1",
        }

        if dual_soil_type in [0, 1]:
            feedback.pushInfo(str((outputs["Soil"])))
            input_params.update(
                {
                    "input_b": outputs["Soil"]["OUTPUT"],
                    "band_b": "1",
                }
            )
            outputs["CN"] = self.perform_raster_math(
                cn_exprs, input_params, context, feedback
            )

        elif dual_soil_type == 2:
            input_params.update(
                {
                    "input_b": outputs["SoilUndrain"]["OUTPUT"],
                    "band_b": "1",
                }
            )
            outputs["CNUndrain"] = self.perform_raster_math(
                cn_exprs, input_params, context, feedback
            )
            input_params.update(
                {
                    "input_b": outputs["SoilDrain"]["OUTPUT"],
                    "band_b": "1",
                }
            )
            outputs["CNDrain"] = self.perform_raster_math(
                cn_exprs, input_params, context, feedback
            )

            # average undrain and drain CN rasters
            outputs["CN"] = self.average_rasters(
                [outputs["CNUndrain"]["OUTPUT"], outputs["CNDrain"]["OUTPUT"]],
                parameters,
                context,
                feedback,
            )

        # temp
        results["cn"] = outputs["CN"]["OUTPUT"].source()
        results["lookup"] = [f.name() for f in lookup_layer.fields()]
        results["desired_outputs"] = desired_outputs
        results["desired_pollutants"] = desired_pollutants

        return results

    def reclass_soil(self, table, parameters, context, feedback):
        alg_params = {
            "DATA_TYPE": 0,
            "INPUT_RASTER": parameters["SoilRaster"],
            "NODATA_FOR_MISSING": False,
            "NO_DATA": 255,
            "RANGE_BOUNDARIES": 2,
            "RASTER_BAND": 1,
            "TABLE": table,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        return processing.run(
            "native:reclassifybytable",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

    def generate_cn_exprs(self, lookup_layer) -> str:
        """Generate generic CN expression"""
        # Build CN Expression
        cn_calc_expr = []
        for feat in lookup_layer.getFeatures():
            lu = feat.attribute("lu_value")
            for i, hsg in enumerate(["a", "b", "c", "d"]):
                cn = feat.attribute(f"cn_{hsg}")
                cn_calc_expr.append(f"logical_and(A=={lu},B=={i+1})*{cn}")

        return " + ".join(cn_calc_expr)

    def perform_raster_math(
        self,
        exprs,
        input_dict,
        context,
        feedback,
        output=QgsProcessing.TEMPORARY_OUTPUT,
    ):
        # Raster calculator
        alg_params = {
            "BAND_A": input_dict.get("band_a", None),
            "BAND_B": input_dict.get("band_b", None),
            "BAND_C": input_dict.get("band_c", None),
            "BAND_D": input_dict.get("band_d", None),
            "BAND_E": input_dict.get("band_e", None),
            "BAND_F": input_dict.get("band_f", None),
            "EXTRA": "",
            "FORMULA": exprs,
            "INPUT_A": input_dict.get("input_a", None),
            "INPUT_B": input_dict.get("input_b", None),
            "INPUT_C": input_dict.get("input_c", None),
            "INPUT_D": input_dict.get("input_d", None),
            "INPUT_E": input_dict.get("input_e", None),
            "INPUT_F": input_dict.get("input_f", None),
            "NO_DATA": -9999,
            "OPTIONS": "",
            "RTYPE": 5,
            "OUTPUT": output,
        }
        return processing.run(
            "gdal:rastercalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

    def average_rasters(self, rasters, parameters, context, feedback):
        # Cell statistics
        alg_params = {
            "IGNORE_NODATA": True,
            "INPUT": rasters,
            "OUTPUT_NODATA_VALUE": -9999,
            "REFERENCE_LAYER": parameters[self.reference_raster],
            "STATISTIC": 2,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        return processing.run(
            "native:cellstatistics",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

    def name(self):
        return "Run Pollution Analysis"

    def displayName(self):
        return "Run Pollution Analysis"

    def group(self):
        return "QNSPECT"

    def groupId(self):
        return "QNSPECT"

    def shortHelpString(self):
        return """<html><body><h2>Algorithm description</h2>
<p></p>
<h2>Input parameters</h2>
<h3>Run Name</h3>
<p></p>
<h3>Location for Run Output</h3>
<p></p>
<h3>Elevation Raster</h3>
<p></p>
<h3>Soil Raster</h3>
<p></p>
<h3>Treat Dual Category Soils as</h3>
<p></p>
<h3>Precipitation Raster</h3>
<p></p>
<h3>Rain Units</h3>
<p></p>
<h3>Number of Rainy Days in a Year</h3>
<p></p>
<h3>Land Use Raster</h3>
<p></p>
<h3>Land Use Type</h3>
<p></p>
<h3>Land Use Lookup Table</h3>
<p></p>
<h3>Select Outputs</h3>
<p></p>
<br></body></html>"""

    def createInstance(self):
        return RunPollutionAnalysis()
