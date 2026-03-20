# -*- coding: utf-8 -*-
"""
/***************************************************************************
CESMapper             : Coastal and Estuarine System Mapping
                              CESMapper QGIS plugin
                              -------------------
        begin           : 2012-07-05
        copyright       : 2012-2016 G Thornhill, H Burningham, JR French,
                          and University College London (UCL) Coastal and 
                          Estuarine Research Unit
        original author : Gillian Thornhill (UCL)
        maintainer      : Helene Burningham (UCL - h.burningham@ucl.ac.uk)
        maintainer      : Jon French (UCL - j.french@ucl.ac.uk)
        version         : 1.5.2
        date            : 07-07-2016
        
        acknowledgement : This software was developed by UCL Coastal and 
                          Estuarine Research Unit as part of the NERC-funded
						  Integrating COAstal Sediment sySTems (iCOASST)
        				  project (NE/J005541/1)   
    
Purpose:
 1. CESMapper implements the Coastal and Estuarine System Mapping (CESM) method
    as a plugin for the open-source QGIS
 2. CESM is described more fully in:
    French JR, Burningham H, Thornhill G, Whitehouse R & Nicholls R.J (2016) 
    Conceptualizing and mapping coupled estuary, coast and inner shelf sediment 
    systems. Geomorphology 256, 17-35 
    http://dx.doi.org/10.1016/j.geomorph.2015.10.006
    
 Notes:
 1. This version of CESMapper is compatible with CESOML ontologies (libraries)
    at specification 1.6
 2. This version has been tested with QGIS 2.14.3 and may not function 
    correctly (or at all) with earlier builds
     
Acknowledgements:
 1.  Parts of the CESMapper code have been adapted from  the Rectangles Ovals 
     Digitizing plugin for QGIS (Copyright (C) 2011 - 2012 Pavol Kapusta)
 2.  This work has been funded by NERC as part of the Integrating COAstal 
     Sediment sySTems (iCOASST) project (NE/J005541/1) - www.icoasst.net   

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 * Copyright (c) <2012,2013,2015,2016>                                     *
 <               <G Thornhill, H Burningham, JR French, and                *
 *                UCL Coastal and Estuarine Research Unit>                 *
 *                                                                         *
 * This file is part of CESMapper                                          *
 *                                                                         *
 *  CESMapper is free software: you can redistribute it and/or modify      *
 *  it under the terms of the GNU General Public License as published by   *
 *  the Free Software Foundation, either version 3 of the License, or      *
 *  (at your option) any later version.                                    *
 *                                                                         *
 *  CESMapper is distributed in the hope that it will be useful,           *
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of         *
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
 *  GNU General Public License for more details.                           *
 *                                                                         *
 *  You should have received a copy of the GNU General Public License      *
 *  along with CESMapper.  If not, see <http://www.gnu.org/licenses/>.     *
 *                                                                         *
 ***************************************************************************/
"""

# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *

from osgeo import ogr
from osgeo import osr

from qgis import processing

import math
import re
import os


from mimetypes import guess_type
from mimetypes import add_type

# Import the code for the dialog
from .coastmapdialog import *

#Import the rectangle drawing class
from .maketool import *


class CESMtool:

# Initialise all the variables, set default values for some
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        if hasattr(self.canvas, "setCrsTransformEnabled"):
            self.canvas.setCrsTransformEnabled(True)
    
        # Create the dialogs and keep reference
        
        # Dialog to load the library file
        self.initDlg = InitialiseDialog()
        # Main dialog for tool
        self.dlg = CoastMapDialog()
        # Selection for saving files
        self.writeDlg = WriteDialog()
        # Dialog for loading files
        self.readDlg = ReadDialog()
        self.dlgList = []
        
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        # initialize locale
        localePath = ""
        locale = str(QSettings().value("locale/userLocale"))[0:2]
       
        # Initialisation for object attributes
        self.size = QgsRectangle()
        self.pluginActive = False
        self.baseLoaded = False
        self.CESMloaded = False
        self.CESMConloaded = False
        self.compsLoaded = False
        self.Group = False
        self.Link = False
        self.EditToolOn = False
        self.MoveToolOn = False
        self.rendV2 = None
        self.numLevels = 0
        self.currentDlg = None
        self.cesmlayer = None
        self.cesmconlayer = None
        self.cesm_component_layer_name = "CESMcomponents"
        self.cesm_connection_layer_name = "CESMconnections"
        self.registry = QgsProject.instance()
        self.metadata = ""      # Contains metadata for the CESM ontology used
        self.cesomlVer = ""     # Current version for CESMapper
        self.libVersion = ""    # Contains the version number for the CESM ontology
        self.libName = ""
        self.numLevels = 1
        self.levelName = {}     # Array for name of the orders
        self.levelSubMaps = {}  # Array containing a map of suborders for each order
        self.coordSystem = None
        self.initialised = False
        self.shapeMapFile = None
        self.shapeConFile = None
        self.outdir = None
        self.outPath = None
        self.allCESMFields = []
        self.allCESMConFields = []
        self.debugOn = False
        self.mapcanvas_UL = QgsPoint()
        self.windowX = 0.0
        self.windowY = 0.0
        self.windowH = 0.0
        self.windowW = 0.0
        self.maxID = 0
        
        # QgsMessageLog.logMessage("** Initialise plugin")
        # Grouping info
        self.isExists = False
        self.groupEdButton = False
        
                
        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/CESMapper_" + locale + ".qm"

        if QFileInfo(localePath).exists():
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
    
        
# *******  Set up of Gui, main plugin and buttons for different actions *****
    def initGui(self):
        settings = QSettings()
        
        self.msgBox = QMessageBox()
        
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(self.plugin_dir+"/CESMicon.png"), "CESMapper", self.iface.mainWindow())
        
        self.action.setObjectName("CESMapper")
        self.action.setWhatsThis("Plugin for Coastal and Estuarine System Mapping")
        # self.action.setStatusTip("This is status tip")
        
        self.action.triggered.connect(self.run)
        
        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&CESMapper", self.action)
        
        # Some of this needs to be done on the fly as well.
        self.iface.actionToggleEditing().setEnabled(True)
        self.legend = None
        
        # Main dialog button connections to actions
        self.initDlg.ui.loadButton.clicked.connect(self.loadComps)
        
        self.dlg.ui.groupButton.clicked.connect(self.groupComps)
        self.dlg.ui.linkButton.clicked.connect(self.linkComps)
        self.dlg.ui.editButton.clicked.connect(self.editMap)
        self.dlg.ui.analyseButton.clicked.connect(self.analyseMap)
        self.dlg.ui.displayButton.clicked.connect(self.dispOpt)
        self.dlg.ui.loadMapButton.clicked.connect(self.browse_infiles)
        self.dlg.ui.saveButton.clicked.connect(self.browse_outfiles)
        self.dlg.ui.cancelButton.clicked.connect(self.removeWindow)
        # Get the dimensions of the main window
        self.windowH = self.dlg.height()
        self.windowW = self.dlg.width()
        
        # Get the tools
        self.featuretool = FeatureTool( self.canvas)
        self.linktool = LinkTool( self.canvas)
        self.clicktool = ClickTool(self.canvas)
        self.grouptool = GroupTool(self.canvas)
        self.movetool = MoveTool(self.canvas)
        self.delcomptool = DelCompTool(self.canvas)
        
        # Connect the actions for mouseclicks to the tools
        self.featuretool.releaseBut.connect(self.makeFeature)
        self.clicktool.canvasClicked.connect(self.clicktool.makeSelectList)
        self.grouptool.canvasClicked.connect(self.grouptool.makeSelectList)
        self.linktool.canvasClicked.connect(self.linktool.makeSelectList)
        self.movetool.canvasClicked.connect(self.movetool.makeSelectList)
        self.movetool.releaseMouse.connect(self.moveComp)
        self.delcomptool.canvasClicked.connect(self.delcomptool.makeSelectList)
        self.delcomptool.releaseDel.connect(self.delComp)
    
        # Catch events where layers added or removed
        self.registry.layersAdded.connect(self.newLayerLoaded)
        self.registry.layerWillBeRemoved.connect(self.layerRemoved)

    def _set_layer_visible(self, layer, visible):
        if layer is None:
            return

        node = self.registry.layerTreeRoot().findLayer(layer.id())
        if node is not None:
            node.setItemVisibilityChecked(visible)

    def _all_layers(self):
        return list(self.registry.mapLayers().values())

    def _dialog_file_path(self, selection):
        if isinstance(selection, tuple):
            return selection[0]
        return selection

    def _set_display_field(self, layer, field_name):
        if layer is None:
            return

        if hasattr(layer, "setDisplayExpression"):
            layer.setDisplayExpression('"{0}"'.format(field_name))

    def _write_vector_layer(self, layer, output_path):
        options = QgsVectorFileWriter.SaveVectorOptions()
        if self._is_geopackage_path(output_path):
            options.driverName = "GPKG"
            options.fileEncoding = "UTF-8"
            options.layerName = layer.name()
            if hasattr(QgsVectorFileWriter, "CreateOrOverwriteFile") and layer.name() == self.cesm_component_layer_name:
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
            elif hasattr(QgsVectorFileWriter, "CreateOrOverwriteLayer"):
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        else:
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "CP1250"
            if hasattr(QgsVectorFileWriter, "CreateOrOverwriteFile"):
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

        return QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            output_path,
            self.registry.transformContext(),
            options,
        )

    def _is_geopackage_path(self, path):
        return bool(path) and path.lower().endswith(".gpkg")

    def _ensure_output_path(self, path):
        if not path:
            return path

        root, ext = os.path.splitext(path)
        if not ext:
            return path + ".gpkg"
        return path

    def _build_layer_source(self, path, layer_name):
        if self._is_geopackage_path(path):
            return "{0}|layername={1}".format(path, layer_name)
        return path

    def _layer_has_fields(self, layer, required_fields):
        if layer is None:
            return False

        field_names = {field.name() for field in layer.fields()}
        return set(required_fields).issubset(field_names)

    def _layer_source_matches_output(self, layer, output_path, layer_name=None):
        if layer is None or not output_path:
            return False

        source = layer.source() or ""
        source_path = source.split("|")[0].lower()
        if source_path != output_path.lower():
            return False

        if self._is_geopackage_path(output_path) and layer_name is not None:
            return "layername={0}".format(layer_name).lower() in source.lower()

        return True

    def _load_cesm_layer_from_source(self, output_path, layer_name, is_connection=False):
        source = self._build_layer_source(output_path, layer_name)
        layer = QgsVectorLayer(source, layer_name, "ogr")
        if not layer.isValid():
            return None

        is_valid_cesm = self.checkCESMConLayer(layer) if is_connection else self.checkCESMLayer(layer)
        if not is_valid_cesm:
            return None

        return layer

    def _ensure_save_layers(self):
        if self.cesmlayer is None and self.shapeMapFile:
            self.cesmlayer = self._load_cesm_layer_from_source(
                self.shapeMapFile,
                self.cesm_component_layer_name,
                is_connection=False,
            )
            if self.cesmlayer is not None:
                self.cesmlayerpr = self.cesmlayer.dataProvider()

        connection_path = self.shapeConFile or self.shapeMapFile
        if self.cesmconlayer is None and connection_path:
            connection_name = self.cesm_connection_layer_name if self._is_geopackage_path(connection_path) else "CESMConnect"
            self.cesmconlayer = self._load_cesm_layer_from_source(
                connection_path,
                connection_name,
                is_connection=True,
            )
            if self.cesmconlayer is not None:
                self.cesmconlayerpr = self.cesmconlayer.dataProvider()

        return self.cesmlayer is not None and self.cesmconlayer is not None

    def _commit_layer_if_editable(self, layer):
        if layer is None:
            return False

        if not layer.isEditable():
            return True

        return layer.commitChanges()

    def _apply_component_renderer(self, layer):
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "circle",
                "color": "255,170,0,255",
                "outline_color": "0,0,0,255",
                "size": "4",
            }
        )
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))

    def _clean_deleted_id_text(self, value, removed_ids):
        text = "" if value is None else str(value)
        if not text or text == "None":
            return None

        for removed_id in removed_ids:
            pattern = r"(?<!\\d){0}(?!\\d)".format(re.escape(str(removed_id)))
            text = re.sub(pattern, "", text)

        text = re.sub(r"\[,", "[", text)
        text = re.sub(r",\]", "]", text)
        text = re.sub(r",\s*,", ",", text)
        text = re.sub(r"\[\s*\]", "", text)
        text = re.sub(r"^\s*,|,\s*$", "", text)
        text = text.strip()

        return text or None

    def _clean_deleted_connect_text(self, value, removed_ids):
        text = "" if value is None else str(value)
        if not text or text == "None":
            return None

        for removed_id in removed_ids:
            pattern = r"\[[^\]]*(?<!\\d){0}L?(?!\\d)[^\]]*\]".format(re.escape(str(removed_id)))
            text = re.sub(pattern, "", text)

        text = text.strip()
        return text or None

    def _transform_map_point_to_layer(self, map_point, layer):
        source_crs = self.canvas.mapSettings().destinationCrs()
        target_crs = layer.crs()

        if not source_crs.isValid() or not target_crs.isValid() or source_crs == target_crs:
            return QgsPointXY(map_point)

        transformer = QgsCoordinateTransform(source_crs, target_crs, self.registry)
        return transformer.transform(QgsPointXY(map_point))
  
    
 # **********************************************************************

    def unload(self):
        # QgsMessageLog.logMessage("** Unload")
        # Remove the plugin menu item and icon

        self.iface.removePluginMenu(u"&CESMapper",self.action)
        self.iface.removeToolBarIcon(self.action)
    
       
# *********  run method that performs all the real work ***********************
                    
    def run(self):
        # QgsMessageLog.logMessage("** run")
        # Something in place in case plugin is restarted without being reloaded; 
        # not sure what we want to do in this case; save previous set-up ?
#        if not(self.initialised):
#            self.initialise()

        # Get coords for upper left of map
        self.mapcanvas_UL = self.iface.mapCanvas().mapToGlobal(QPoint(0, 0))
        
        if self.debugOn == True:
            QgsMessageLog.logMessage("START PLUGIN")
    
        self.pluginActive = True
        
        # What layers do we have loaded when the tool starts ?
        self.checkBaseLayer()
        
        # If no base layer loaded
        if self.baseLoaded:
            if self.compsLoaded == False:
                self.initDlg.show()
        # If baselayer loaded then show main dialog
            else:
                self.dlg.show()

        else:
            self.msgBox.setText("Please load a base map layer")
            result = self.msgBox.exec_()


# *********************************************************************

    def checkBaseLayer(self):
        # QgsMessageLog.logMessage("** Check base layer")
        # Return list of names of all layers in QgsMapLayerRegistry
        # (adapted from 'fTools Plugin', Copyright (C) 2009  Carson Farmer)
        
        # Check that at least one base layer is loaded
        
        listLayers = self.registry.mapLayers()
        if listLayers == None:
            self.baseLoaded = False
            return
        
        else:
    
            mapLayerName = "Null"
            
            # Also need to check if a CESM layer is already present, and if not, 
            # create a new one.
            # This does not seem to work if there are other layers loaded, or on 
            # second load (?? bug to chase)
            for name, layer in listLayers.items():
                layerType = layer.type()
                if layerType != 0:
                    self.baseLoaded = True
                    mapLayerName = "BaseMap"
                    self.coordSystem = layer.crs()
                    self.size = layer.extent()
                    w = self.size.width()
                    h = self.size.height()
                        
  
# *********************************************************************

    def checkCESMLayer(self, layer):
      
        # Check if the layer is a vector layer (point or polygon) and what 
        # attributes it contains
        # QgsMessageLog.logMessage("CESMLayer type")
        if layer.type() == 0: # Vector layer
            prov = layer.dataProvider()
            geomType = layer.geometryType()
            fields = prov.fields()  # QMap<int, QgsField>
            required_fields = ["CESMLayer", "ID", "Order", "Name", "GeoX", "GeoY"]
            
    # New version has attribute specifically for this; old versions will check 
    # for other attribute names
            if (fields):

                if self._layer_has_fields(layer, required_fields) and geomType == QgsWkbTypes.PointGeometry:
                    self.CESMloaded = True
                    return True
                else:
                    return False
                        
            else:
                return False
                    
        else:
            return False


# *********************************************************************
                        
    def checkCESMConLayer(self, layer):
   
         # Check if the layer is a vector layer, if its points/polys, and what 
         # attributes it has.
        if layer.type() == 0: # Vector layer
            prov = layer.dataProvider()
            geomType = layer.geometryType()
            fields = prov.fields()  # QMap<int, QgsField>
            required_fields = ["CESMLayer", "ID", "Link", "StartX", "StartY", "EndX", "EndY"]

             # New version has attribute specifically for this; old versions will 
             # check for other attribute names
            if fields and self._layer_has_fields(layer, required_fields) and geomType == QgsWkbTypes.LineGeometry:
                self.CESMConloaded = True
                return True
            else:
                return False
        else:
            return False


# ************* Create New layers ******************************************

    def createLayer(self):
        # Creates a new Vector layer and shapefile
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Create layer")
        
        self.createAttributeFields()

        # self.cesmlayer = QgsVectorLayer("Point", "CESMComp", "memory")
        self.cesmlayer = QgsVectorLayer("Point", self.cesm_component_layer_name, "memory")
        # self.cesmconlayer = QgsVectorLayer("LineString", "CESMConnect", "memory")
        self.cesmconlayer = QgsVectorLayer("LineString", self.cesm_connection_layer_name, "memory")
        if not self.cesmlayer.isValid():
            self.msgBox.setText("CESM Components Layer failed to load ")
            result = self.msgBox.exec_()
            return
        elif not self.cesmconlayer.isValid():
            self.msgBox.setText("CESM Connections Layer failed to load ")
            result = self.msgBox.exec_()
            return
        else:
            self.cesmlayerpr = self.cesmlayer.dataProvider()
            self.cesmconlayerpr = self.cesmconlayer.dataProvider()
            QgsMessageLog.logMessage("Layers valid")
        
        
        cesmFields = self.cesmlayer.fields()
        cesmConFields = self.cesmconlayer.fields()
    
#        QgsVectorFileWriter.writeAsVectorFormat(self.shapeMapFile, "UTF-8", cesmFields, QGis.WKBPoint, self.coordSystem, "ESRI Shapefile")
#        QgsVectorFileWriter.writeAsVectorFormat(self.shapeConFile, "UTF-8", cesmConFields, QGis.WKBLineString, self.coordSystem, "ESRI Shapefile")
    
#        self.writerCESMLayer = QgsVectorFileWriter(self.shapeMapFile, "UTF-8", cesmFields, QGis.WKBPoint, self.coordSystem, "ESRI Shapefile")
#        self.writerCESMConLayer = QgsVectorFileWriter(self.shapeConFile, "UTF-8", cesmConFields, QGis.WKBLineString, self.coordSystem, "ESRI Shapefile")
    
                
        # Set up layer characteristics
        self.cesmlayer.setCrs(self.coordSystem)
        self.cesmconlayer.setCrs(self.coordSystem)
        
        self._set_display_field(self.cesmlayer, "Name")
        # self.cesmlayer.enableLabels(True)
        # self.cesmconlayer.enableLabels(True)
        self.cesmlayer.setCustomProperty("MapComponents", "True")
        self.cesmconlayer.setCustomProperty("MapComponents", "True")
        self.cesmconlayer.setCustomProperty("MapConnections", "True")
        self.cesmconlayer.setCustomProperty("MapConnections", "False")                              


        self.cesmlayerpr.addAttributes(self.allCESMFields)
        self.cesmconlayerpr.addAttributes(self.allCESMConFields)
        self.cesmlayer.updateFields()
        self.cesmconlayer.updateFields()

        # Set layer to be editable (tho this does not set the icon on)
        if not self.cesmlayer.isEditable():            
            # self.cesmlayer.editEnabled = True
            self.cesmlayer.startEditing()
            
        if not self.cesmconlayer.isEditable():
            #  self.cesmconlayer.editEnabled = True
            self.cesmconlayer.startEditing()
    
        # Load NewStyle file - this sets the 'label' according to the level attr.
        (errorLabMsg, resLab) = self.cesmlayer.loadNamedStyle(self.plugin_dir+"/CESMComp.qml")
        if not resLab:
            QgsMessageLog.logMessage("CompStyleLoad "+errorCatMsg)
        self._apply_component_renderer(self.cesmlayer)
        
        # Load FeatureStyle file - this sets the 'symbol' according to the class attr.
        (errorCatMsg, resCats) = self.cesmconlayer.loadNamedStyle(self.plugin_dir+"/CESMConnectRule.qml")
        if not resCats:
            QgsMessageLog.logMessage("SymbolConnLoad "+errorCatMsg)

        # self.le = self.rendV2.labelingEngine()
        self.labelObj = None

        self.CESMloaded = True
        self.CESMConloaded = True
        
        self.registry.addMapLayer(self.cesmlayer)
        self.registry.addMapLayer(self.cesmconlayer)
                
        self.cesmlayer.selectionChanged.connect(self.getSelectedFeature)
        #self.cesmlayer.featureDeleted.connect(self.removeComp)
                
        self.cesmlayer.commitChanges()
        self.cesmconlayer.commitChanges()

        self.writeShapeFile()

            
# ************* Create Attribute Fields ******************************************
#
#   This is where attributes can be added.
#       attsFieldCommon are attributes required in both layers
#       attsFieldComp are attributes only in the components (point) layer
#       attsFieldConn are attributes only in the connections (line) layer
#
#   Map of the attributes, with the name as the key, the int as the value.

    def createAttributeFields(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Create attribute fields")
        
        attsFieldCommon = [
                           QgsField("CESMLayer", QVariant.String),
                           QgsField("ID", QVariant.String),
                           QgsField("InGroup", QVariant.String),
                           QgsField("Connect", QVariant.String),
                           QgsField("Members", QVariant.String),
                           QgsField("Link Docs", QVariant.String),
                           QgsField("Colour", QVariant.String)]
        
        attsFieldComp = [
                         QgsField("Order", QVariant.String),
                         QgsField("OrderName", QVariant.String),
                         QgsField("Name", QVariant.String),
                         QgsField("ScreenX", QVariant.Double),
                         QgsField("ScreenY", QVariant.Double),
                         QgsField("GeoX", QVariant.Double),
                         QgsField("GeoY", QVariant.Double),
                         QgsField("Parent", QVariant.String),
                         QgsField("Children", QVariant.String),
                         QgsField("AllowChild", QVariant.String),
                         QgsField("Geog Name", QVariant.String)]
        
        
        attsFieldConn = [
                         QgsField("Link", QVariant.String),
                         QgsField("StartX", QVariant.Double),
                         QgsField("StartY", QVariant.Double),
                         QgsField("EndX", QVariant.Double),
                         QgsField("EndY", QVariant.Double),
                         QgsField("Mass Flux", QVariant.Double),
                         QgsField("Influences", QVariant.String),
                         QgsField("ConType", QVariant.String),
                         QgsField("Direct", QVariant.String)]
         
        
        self.allCESMFields = attsFieldCommon + attsFieldComp
        self.allCESMConFields = attsFieldCommon + attsFieldConn


# ***************** Set up CESM components layer ****************
# Sets up the CESM components layer and sets loaded to True
    
    def setUpCESMLayer(self, layer):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Set up CESM components layer")
        
        self.cesmlayer = layer
        self.cesmlayerpr = self.cesmlayer.dataProvider()
        # Load Style file
        (errorLabMsg, resLab) = self.cesmlayer.loadNamedStyle(self.plugin_dir+"/CESMComp.qml")
#        if not resLab:
#            QgsMessageLog.logMessage("CompStyleLoad "+errorCatMsg)
        self._apply_component_renderer(self.cesmlayer)
        
        self.rendV2 = self.cesmlayer.renderer()
#        self.le = self.rendV2.labelingEngine()
        self.CESMloaded = True
        self.cesmlayer.selectionChanged.connect(self.getSelectedFeature)
        #self.cesmlayer.featureDeleted.connect(self.removeComp)
         
        self.labelObj = None
                #self.cesmlayerpr = createSpatialIndex()
        self.registry.addMapLayer(self.cesmlayer)


# ***************** Set up CESM connections layer ****************
# Sets up the CESM connections layer and sets loaded to True
    
    def setUpCESMConLayer(self, layer):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Set up CESM connections layer")
        
        self.cesmconlayer = layer
        self.cesmconlayerpr = self.cesmconlayer.dataProvider()
        # Load style file
        (errorCatMsg, resCats) = self.cesmconlayer.loadNamedStyle(self.plugin_dir+"/CESMConnectRule.qml")
        if not resCats:
            QgsMessageLog.logMessage("SymbolConnLoad "+errorCatMsg)
        self.CESMConloaded = True
                #self.cesmconlayerpr = createSpatialIndex()
        self.registry.addMapLayer(self.cesmconlayer)
    

# ***************** Check new layer Loaded ****************
        
    def newLayerLoaded(self, layers):
        
        if self.pluginActive == True:
            for layer in layers:
                if layer.type() == 0:
                    if self.CESMloaded == False and self.checkCESMLayer(layer):
                        self.setUpCESMLayer(layer)
                    if self.CESMConloaded == False and self.checkCESMConLayer(layer):
                        self.setUpCESMConLayer(layer)
    
            
# ***************** Layers removed ****************
            
    def layerRemoved(self, id):

        if self.cesmlayer != None and self.cesmlayer.id() == id:
            self.CESMloaded = False
            self.cesmlayer = None

        if self.cesmconlayer != None and self.cesmconlayer.id() == id:
            self.CESMConloaded = False
            self.cesmconlayer = None


# ***************** Get save file name ****************
    
    def browse_outfiles(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Browse outfiles")
            QgsMessageLog.logMessage(str(self.shapeMapFile))
                
        self.shapeMapFile = self._dialog_file_path(
            QFileDialog.getSaveFileName(None, str("Save GeoPackage"), self.writeDlg.ui.output.displayText(), "GeoPackage (*.gpkg)")
        )
        self.shapeMapFile = self._ensure_output_path(self.shapeMapFile)
        
        
        if self.shapeMapFile:
            if self.debugOn == True:
                QgsMessageLog.logMessage("Shape map file browse")
            
            self.writeDlg.ui.output.setText(str(self.shapeMapFile))
            fileInfo = QFileInfo(self.shapeMapFile)
            fileString = self.writeDlg.ui.output.text()
            self.outDir = fileInfo.absolutePath()
            name = fileInfo.completeBaseName()
            if self._is_geopackage_path(self.shapeMapFile):
                self.shapeConFile = self.shapeMapFile
            else:
                self.shapeConFile = self.outDir+"/"+name+"Con.shp"
       
            if os.path.exists(self.shapeMapFile): # If file does exist - saving file, so write it out
                if self.debugOn == True:
                    QgsMessageLog.logMessage("File exists")
                
                self.writeShapeFile()
            
            elif self.CESMloaded == False:
            # If file does not exist
                if self.debugOn == True:
                    QgsMessageLog.logMessage("File doesn't exist")
                
                self.createLayer()
                    
            elif self.CESMloaded == True:
                self.writeShapeFile()
            
        else:
            if self.debugOn == True:
                QgsMessageLog.logMessage("No filename")
            
            self.msgBox.setText("No filename selected")
            result = self.msgBox.exec_()

            return

    
# ***************** Get input file name ****************

    def browse_infiles(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Browse infiles")
        
        self.shapeMapFile = self._dialog_file_path(
            QFileDialog.getOpenFileName(None, str("Select CESM Map"), self.readDlg.ui.input.displayText(), "GeoPackage (*.gpkg);;Shapefile (*.shp)")
        )
        
        # Get Filename
        if self.shapeMapFile:
            self.readDlg.ui.input.setText(str(self.shapeMapFile))
            fileInfo = QFileInfo(self.shapeMapFile)
            fileString = self.readDlg.ui.input.text()
            self.inDir = fileInfo.absolutePath()
            name = fileInfo.completeBaseName()
            if self._is_geopackage_path(self.shapeMapFile):
                self.shapeConFile = self.shapeMapFile
                component_source = self._build_layer_source(self.shapeMapFile, self.cesm_component_layer_name)
                connection_source = self._build_layer_source(self.shapeMapFile, self.cesm_connection_layer_name)
            else:
                self.shapeConFile = self.inDir+"/"+name+"Con.shp"
                component_source = self.shapeMapFile
                connection_source = self.shapeConFile
            
            # Check that file exists **********
            # Load layer and check it IS a CESM layer
            #self.cesmlayer = QgsVectorLayer(self.shapeMapFile, "CESMComp", "ogr")
            self.cesmlayer = QgsVectorLayer(component_source, self.cesm_component_layer_name, "ogr")
            if not self.cesmlayer.isValid():
                self.msgBox.setText("CESM components layer failed to load")
                result = self.msgBox.exec_()
            
            if self.checkCESMLayer(self.cesmlayer):
                self.setUpCESMLayer(self.cesmlayer)
            else:
                self.msgBox.setText("Not a valid CESM file")
                result = self.msgBox.exec_()
                return

#            self.cesmconlayer = QgsVectorLayer(self.shapeConFile, "CESMConnect", "ogr")
            self.cesmconlayer = QgsVectorLayer(connection_source, self.cesm_connection_layer_name, "ogr")
            if not self.cesmconlayer.isValid():
                self.msgBox.setText("CESM connections layer failed to load")
                result = self.msgBox.exec_()
                return
        
            if self.checkCESMConLayer(self.cesmconlayer):
                self.setUpCESMConLayer(self.cesmconlayer)
            else:
                self.msgBox.setText("Not a valid CESM file")
                result = self.msgBox.exec_()
                return     
        
        else:
            return


# ***************** Write Shape file ****************
    
    def writeShapeFile(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Write shapefile ")

        if not self._ensure_save_layers():
            self.msgBox.setText("CESM component or connection layer is not available for saving")
            self.msgBox.exec_()
            return False

        saved = self._commit_layer_if_editable(self.cesmlayer)
        savedcon = self._commit_layer_if_editable(self.cesmconlayer)
        if not saved or not savedcon:
            self.msgBox.setText("Could not commit CESM edits before saving")
            self.msgBox.exec_()
            return False

        map_target = self.shapeMapFile
        con_target = self.shapeConFile or self.shapeMapFile
        if self._layer_source_matches_output(self.cesmlayer, map_target, self.cesm_component_layer_name) and self._layer_source_matches_output(self.cesmconlayer, con_target, self.cesm_connection_layer_name):
            return True

        self.writer = self._write_vector_layer(self.cesmlayer, map_target)
        self.writer1 = self._write_vector_layer(self.cesmconlayer, con_target)
    
        
        if self.writer:
            QgsMessageLog.logMessage("First File created")

        if self.writer1:
            QgsMessageLog.logMessage("Second File created")

        return True


# **********************************************************************

    # Dummy routine for testing calls etc
    def doNothing(self, string):
        QgsMessageLog.logMessage("In Do Nothing ")
 
    
# *************** Read component files *************************************
# **********  File parser code  *********************************************

    def readFile(self):
        # QgsMessageLog.logMessage("** readFile (library)")
        metadata = []
        self.fileName = self._dialog_file_path(QFileDialog.getOpenFileName())
        if os.path.isfile(self.fileName):
            
            try:
                with open(self.fileName, 'r') as fileLib:
                # Read file  into list, each element is a line.
                    libText = fileLib.read(-1)
                    if self.debugOn == True:
                        QgsMessageLog.logMessage("File read")
                    
                    fileLib.close()
       

            except IOError as e:
                self.msgBox.setText("({})".format(e))
                self.msgBox.exec_()
                if self.debugOn == True:
                    QgsMessageLog.logMessage("Error thrown by try-except")
                return None
                
    
        else:
            self.msgBox.setText(self.fileName+" is not a file")
            self.msgBox.exec_()
            return None
                    
        return libText
             
             
    # Need to add checks for non-existent file, bad filename, etc.
        
            
# *************** Load components *************************************

    def loadComps(self):
        # QgsMessageLog.logMessage("** Load components")
        
        self.listCompChild = {} # Array containg the children for each component
        self.levelComp = []     # List containing the components at each level - index is the level
        self.intComp = []       # List containing number of components at each order
        self.compObjects = {}   # Array of component objects
        self.shapeCode = {}     # This tells us what shape to draw
        self.colourCode = {}    # Colour for component
        self.numComps = {}      # Array for number of components at each order
        self.numSuborders = {}  # Number of suborders for each order
        
    # Need to rationalise all this. Need a list of suborders for each level, with their names.
    # Could be a map keyed to the level number/name, with suborder names for each level
        
        fullText = self.readFile()
        libText = (fullText.replace("\n", "")).replace("\r", "") # remove any kind of new line/carriage return
                
        if libText == None:
            self.msgBox.setText("Unable to read file: "+self.fileName)
            self.msgBox.exec_()
            return
        
 ############################ Start of Parser code ######################################################       
        # ***********  Parser for File *********************************
        # Needs lots of addition checks for validity of file contents  *
        # **************************************************************
        if libText.startswith("<library>") and libText.endswith("</library>"):
            # Start of parsing - Main library info
            met = (re.search('<metadata>(.*)</metadata>', libText, re.MULTILINE))
            cesomlVer = (re.search('<CESOMLversion>(.*)</CESOMLversion>', libText, re.MULTILINE))
            libN = (re.search('<libraryname>(.*)</libraryname>', libText, re.MULTILINE))
            libVer = (re.search('<libraryversion>(.*)</libraryversion>', libText, re.MULTILINE))
            numLev = (re.search('<numorders>(.*)</numorders>', libText, re.MULTILINE))
           
            # Check the total number of components in file
            compExp = '<component>(.*?)</component>'
            fileCompList = re.findall(compExp, libText, re.MULTILINE)
            totalCompNum = len(fileCompList) # Total number of component tags actually found
            QgsMessageLog.logMessage("Total components "+str(totalCompNum))
            
            if met == None or libN == None or numLev == None or cesomlVer == None:
                self.msgBox.setText("Unable to parse file "+self.fileName+"\n One or more of <metadata> </metadata>, <CESOMLversion> </CESOMLversion>, <libraryname> </libraryname> or <numlevels> </numlevels> tags not found.")
                self.msgBox.exec_()
                return
                
            else:
                self.metadata = met.group(1)
                self.cesomlVer = cesomlVer.group(1)
                self.libVersion = libVer.group(1)
                self.libName = libN.group(1)
                self.numLevels = int(str(numLev.group(1)))
                
                # Parse loop for each level ****************************************************************************
                # Parse each level (in loop) to populate properties, components etc.
                # We may now have 'suborders', which will be optional
                for num in range(0, self.numLevels):
                    self.listComp = []      # List containing the component lists for each level
                    level = 'order'+str(num) # Get selection for each level
                    levelmatch = '<'+level+'>(.*)</'+level+'>'
                    leveltxt = (re.search(levelmatch, libText, re.MULTILINE))
                    if leveltxt == None:
                        self.msgBox.setText("Unable to parse file "+self.fileName+" \n <"+level+"> </"+level+"> tags not found.")
                        self.msgBox.exec_()
                        return
                    
                    levelText = leveltxt.group(1)                
                    # Get all the text for a single order
                    # levelText contains all the info for each level
                    levName = (re.search('<ordername>(.*)</ordername>', levelText, re.MULTILINE))
                    if levName == None:
                        self.msgBox.setText("Unable to parse file "+self.fileName+"\n <ordername> </ordername> tags not found for order "+str(num)+".")
                        self.msgBox.exec_()
                        return

                    self.levelName[num] = str(levName.group(1))
                    
                    # Parse property string for an order *********************
                    prop = (re.search('<property>(.*)</property>', levelText, re.MULTILINE))
                    if prop == None:
                        self.msgBox.setText("Unable to parse file "+self.fileName+" \n <property> </property> tags not found for order "+str(num)+".")
                        self.msgBox.exec_()
                        return
                
                    propertyText = str(prop.group(1))
                    props = propertyText.split(',')
                    if len(props) != 4:
                        self.msgBox.setText("Unable to parse file "+self.fileName+" \n Text defining property values must be of the form: \n numcomps=m, numsuborders=k, shape=n, colour=colourname \n in order "+str(num)+".")
                        self.msgBox.exec_()
                        return
                    self.numComps[num] = int((props[0].partition("="))[2])
                    self.numSuborders[num] = int((props[1].partition("="))[2])
                    self.shapeCode[num] = int((props[2].partition("="))[2])
                    self.colourCode[num] = (props[3].partition("="))[2]


                # If there are no components at this level we go to next level
                    if self.numComps[num] == 0:
                        self.levelComp.append(self.listComp)
                        continue


                    # No suborders, component list complete for the order
                    if self.numSuborders[num] == 0:
                        self.listComp = self.parseComp(levelText, num, 'None', self.shapeCode[num], self.colourCode[num])
                      
                    # Parse for suborders  ****************************************************************************
                    # If there are suborders these need to be parsed.
                    elif self.numSuborders[num] != 0:
                        self.subName = {}       # Suborder names
                        self.numCompsSub = {}   # Number of components at a suborder
                        self.mapCompSub = dict()
                        
                        # Find all the suborders at this level
                        subOrdExp = '<suborder>(.*?)</suborder>'
                        subOrdList = re.findall(subOrdExp, levelText, re.MULTILINE)
                        
                        # Loop thru the suborders at this level, return name and list of components
                        for nsub in range(0, len(subOrdList)):
                            mapSubs = self.parseSubOrder(subOrdList[nsub], num, nsub)
                            self.mapCompSub[mapSubs[0]] = mapSubs[1]
                            self.levelSubMaps[num] = self.mapCompSub # Contains the relevant infor for the subOrders.
                            for name in mapSubs[1]:
                                self.listComp.append(name)
                            
                            
                        
                                        
                #  End of parser for suborders  ****************************************************************************

                    # Put the list of components into the overall list
                    self.levelComp.append(self.listComp)
    
                
                #  End of parse loop for each level ****************************************************************************
              
                numSum = 0
                for nm in range(0, self.numLevels): # Loops thru each level
                    self.intComp.append(len(self.levelComp[nm])) # Gives us a list of the number of components at each level
                    numSum = numSum + int(self.intComp[nm])
                    
                # We can sum these, and check against total number found                
                if numSum != totalCompNum:
                    self.msgBox.setText("Error in file "+self.fileName+"  \n Some <component> </component> tags not contained inside <leveln> </leveln> tags")
                    self.msgBox.exec_()
                    return

                self.createLevelButtons()
                self.createMapDialogs()
                self.compsLoaded = True

                self.initDlg.close()

                self.dlg.show()
                self.windowH = self.dlg.height()
                self.windowW = self.dlg.width()
                
        else:
            self.msgBox.setText("Library file "+self.fileName+" must start and end with <library>.....</library> tags. \n Please check you have the correct file.")
            self.msgBox.exec_()


# *************** Function for parsing component text *************************************

    def parseComp(self, text, n, subName, shape, colour):
        # QgsMessageLog.logMessage("** Parse comps")
        levelText = text
        num = int(n)
        list = []
        compExp = '<component>(.*?)</component>'
        
        # Find all the components at this level
        allComps = re.findall(compExp, levelText, re.MULTILINE)
        if not allComps:
            self.msgBox.setText("Unable to parse file "+self.fileName+"\n <component> </component> tags not found for order "+str(num)+".")
            self.msgBox.exec_()
            return
        
        # Loop thru the components at this level or suborder
        for compInfo in allComps:
            name = self.buildComp(compInfo, num, subName, shape, colour)
            list.append(name)
                
        return list
            
# *************** Build Component Object *************************************

    def buildComp(self, compInfo, levNum, subName, sh, col):
        # QgsMessageLog.logMessage("** Build comps")
        num = int(levNum)
        shape = int(sh)
        colour = col
        
        
        # Can check to see if 'colour' keyword exists, and ignore if it doesn't.'
        # QgsMessageLog.logMessage("compinfo  "+str(compInfo))
        # Separate name field from colour and children field
        segment = compInfo.split(',',2)
        # QgsMessageLog.logMessage('Line '+str(len(segment)))
        # QgsMessageLog.logMessage('Segments '+str(segment[0])+"second one "+str(segment[1])+"third "+str(segment[2]))
        
        if len(segment) != 3:
            self.msgBox.setText("Unable to parse file "+self.fileName+"\n Text defining components must be of the form: \n name=Componentname, colour=#FFFFFF, children=child1, child2")
            # self.msgBox.exec_()
            return
        
        if 'name=' in segment[0].replace(" ", ""):
            namec = (segment[0].partition("=")[2]).strip('"')
            
            
            # Create object for component
            objName = namec+"Obj"
            objName = Component(namec)
            self.compObjects[namec] = objName
        else:
            # Something not right, warn user
            self.msgBox.setText("Unable to parse file "+self.fileName+"\n 'name=' not found in a <components> tag.")
            self.msgBox.exec_()
            return

                
        # Check if there are specific colours for each component, then children is in 3rd place
        if 'colour=' in segment[1].replace(" ", ""):
            colour = (segment[1].partition("=")[2]).strip('"')
            
            if 'children=' in segment[2].replace(" ", ""):
                childList = (segment[2].partition("=")[2]).strip('"')
                objName.setChildren(childList)
            else:
                self.msgBox.setText("Unable to parse file "+self.fileName+"  \n'children=' not found in a <components> tag.")
                self.msgBox.exec_()
                return
                    
        # No colour code, so just have children next
        elif 'children=' in segment[1].replace(" ", ""):
            childList = (segment[1].partition("=")[2]).strip('"')
            objName.setChildren(childList)
        else:
            # Something not right, warn user
            self.msgBox.setText("Unable to parse file "+self.fileName+"  \n'children=' not found in a <components> tag.")
            self.msgBox.exec_()
            return
        
        objName.setLevel(num)
        levName = str(self.levelName[num])
        objName.setLevelName(levName)
        objName.setShape(shape)
        objName.setColour(colour)
    
        return namec


# *************** Parse suborders *************************************
# Called once per suborder, returns the name of the suborder and the list of components
                
    def parseSubOrder(self, orderText, level, nsub):
        # QgsMessageLog.logMessage("** Parse suborder")
        subProp = (re.search('<subproperty>(.*)</subproperty>', orderText, re.MULTILINE))
        if subProp == None:
            self.msgBox.setText("Unable to parse file "+self.fileName+" \n <subproperty> </subproperty> tags not found for order "+str(num)+".")
            self.msgBox.exec_()
            return
        
        # Properties for the 'suborders'
        subPropTxt = str(subProp.group(1))
        subpropsplit = subPropTxt.split(',')
        if len(subpropsplit) != 4:
            self.msgBox.setText("Unable to parse file "+self.fileName+" \n Text defining suborder property values must be of the form: \n subordername=Name, numcomps=k, shape=n, colour=colourname \n in order "+str(num)+".")
            self.msgBox.exec_()
            return
        subNameAll = ((subpropsplit[0].partition("="))[2]).strip()
        self.subName[nsub] = subNameAll.strip('"')
        self.numCompsSub[nsub] = int((subpropsplit[1].partition("="))[2].strip())
        self.shapeCode[nsub] = int((subpropsplit[2].partition("="))[2].strip())
        self.colourCode[nsub] = (subpropsplit[3].partition("="))[2].strip()
        # List of components at suborder
        tempList = self.parseComp(orderText, level, self.subName[nsub], self.shapeCode[nsub], self.colourCode[nsub])
                
        return (self.subName[nsub], tempList)


############################ End of Parser code ######################################################

# *************** Create Main Dialogs *************************************
    
    def createLevelButtons(self):
        # QgsMessageLog.logMessage("** Create level buttons")
        for num in range(0, self.numLevels):
            if self.intComp[num] == 0: # For a level with no components, no mapping dialog
                continue
            butText = "Map "+self.levelName[num]
            self.dlg.addNewButton(butText, num)
            
        butList = self.dlg.ui.buttonGroup.buttons()
        
        for button in butList:
            button.clicked.connect(self.featSelect)


# *************** Create Map Dialogs *************************************
    
    # Then needs to create and populate the dialogs
    # Populate landform complex and landform component dialogs with what is read from files
    # need number of levels (numLevels), nameLevels(can be an array of length numLevels)
    # Then an array for each level with the components belonging to it - then parallel
    # levels possibly, for things like structures and interventions, which are at the same
    # level in the ontology as landforms, but may have different colours/labels.
    # May want a more elaborate data structure to contain all this
    
    def createMapDialogs(self):
        # QgsMessageLog.logMessage("** Create map dialogs")
        # For each level, need an array of components at that level
        # This is populated according to the number of levels read in
        
        # This loops thru the dialogs (one for each level, currently)
        for num in range(0, self.numLevels):
            if self.intComp[num] == 0: # For a level with no components, no mapping dialog
                self.dlgList.append("")
                continue
            
            dlgName = self.levelName[num]+"dlg"

            # Create the dialogs
            butName = "Map "+self.levelName[num]+"Button"
            dlgName = SelectFeature()
            dlgName.setLevelName(self.levelName[num])
        
             # dlgName.resize(292, 474)
            
            dlgName.setObjectName = self.levelName[num]
        
            if self.numSuborders[num] != 0:
                mapComp = self.levelSubMaps[num]
                for key in mapComp:
                    dlgName.addNewLabel(key)
                    listCp = mapComp[key]
                    for i in range(0, len(listCp)):
                        butName = listCp[i]
                        dlgName.addNewButton(butName)

                
            else:
                for i in range(0, self.intComp[num]):
                    compList = self.levelComp[num]
                    butName = compList[i]
                    dlgName.addNewButton(butName)
                
            butList = dlgName.ui.buttonGroup.buttons()
            if butList:
                butList[0].setChecked(True)
            self.dlgList.append(dlgName)
                
        # If successful then activates other buttons
        
        self.dlg.ui.groupButton.setEnabled(True)
        self.dlg.ui.linkButton.setEnabled(True)
        self.dlg.ui.editButton.setEnabled(True)
        self.dlg.ui.analyseButton.setEnabled(False)
        self.dlg.ui.displayButton.setEnabled(True)
        self.dlg.ui.loadMapButton.setEnabled(True)
        self.dlg.ui.saveButton.setEnabled(True)
        self.dlg.ui.cancelButton.setEnabled(True)
        
# **********************************************************************
    
    # Creates and shows the window for feature selection, processes buttons
    
    def featSelect(self):
        # Shows the dialog to select feature
        if self.debugOn == True:
            QgsMessageLog.logMessage("** featSelect")
        
        button = self.dlg.sender()
        butPressed = button.text()
        
        
        for num in range(0, self.numLevels):
            if self.intComp[num] == 0: # For a level with no components, no mapping dialog
                continue
            # Tests based on the text on the button - could be problematic
            if "Map "+self.levelName[num] == butPressed:
                self.dlgInt = num # Dialog in array is linked to its order number
                break
    
        self.featuretool.setLevelName(self.levelName[num])
        self.featuretool.setLevel(self.dlgInt)
        self.currentDlg = self.dlgList[self.dlgInt]
    
        if self.CESMloaded == False:
            self.msgBox.setText("Please load a CESM layer \n use the 'Save/Create Map' button to create a new map, or 'Load Map' button to load a pre-existing map")
            self.msgBox.exec_()
            return
                    
        self.currentDlg.setWindowModality(True)
        if self.featureMap() == "NoCESMLayer":
            if self.debugOn == True:
                QgsMessageLog.logMessage("Not a CESM Layer")
            return
                    
        # start and stop buttons
        
        self.windowX = self.dlg.pos().x()
        self.windowY = self.dlg.pos().y() + self.windowH + 20
        self.currentDlg.setGeometry(self.windowX, self.windowY, self.currentDlg.width(), self.currentDlg.height())

        self.currentDlg.ui.stopButton.clicked.connect(self.stopMap)
        self.currentDlg.ui.buttonGroup.buttonClicked.connect(self.featureMap)
        self.currentDlg.show()
    
# **********************************************************************    
    # Gets the selected button, and sets up the tool
    
    def featureMap(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** featMap")
        
        # Set the button states
        strResult = str(self.currentDlg.getSelect())
        
        mc = self.canvas
        currentTool = mc.mapTool()
        self.swapTool(self.featuretool, currentTool)
        # Sets the layer
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return "NoCESMLayer"

        layer.startEditing()
            # layer.editEnabled = True
        
        self.mapActive = True
        name = strResult
        self.featuretool.setName(name)
               
        # self.featuretool.setShape(self.shapeCode[self.dlgInt])
        self.canvas.refresh()
   
    # ***************** Sets up and draws the feature, adds attribute values *****
    
    def makeFeature(self, nameOut):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Make feature")
        
        settings = QSettings()
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
        
        shape = 0
        
        if (self.mapActive):
            layer.setReadOnly(False)
            # layer.editEnabled = True
            
            
            # Set up coordinate transform
            # mapToPix = mc.getCoordinateTransform()
            # scale = mapToPix.mapUnitsPerPixel()
            
            norm = self.size.normalize()
            width = self.size.width()
            height = self.size.height()
            
            layerCRSSrsid = self.cesmlayer.crs()
            projectCRSSrsid = rend.destinationCrs()
            
            pr = layer.dataProvider()
            
            
            # *** Note that invalid geomtry may prevent the labels from showing.
            # If we add more levels, will need to add more of these. We can take this out as an additional
            # function/routine if necessary
            drawPoint = self.featuretool.getPoint()
            
            centerx = drawPoint.x()
            centery = drawPoint.y()
            
            mapPoint = self.featuretool.getPoint()
            screenPoint = self.featuretool.getScreenPoint()
            # Could add the object ref. to this, allows more flexibility.
            namestring = self.featuretool.getName()
            
            compObj = self.compObjects[namestring]
            allowChild = str(compObj.getChildren())
            
            level = compObj.getLevel()
            levelName = compObj.getLevelName()
            shape = int(compObj.getShape())
            colour = compObj.getColour()
            
            fields=layer.fields()
            f = QgsFeature(fields)
            
            
            # Set attributes
            geoPoint = self._transform_map_point_to_layer(mapPoint, layer)
            self.geom = QgsGeometry.fromPointXY(geoPoint)
            
            f['Colour']=colour
            f['Order']= level
            f['OrderName']= levelName
            f['Name']=namestring
            f['ScreenX']= screenPoint.x()
            f['ScreenY'] = screenPoint.y()
            f['GeoX']= geoPoint.x()
            f['GeoY']= geoPoint.y()
            f['AllowChild']= allowChild
            f['InGroup']= "False"
            
            
            ID = str(self.setFeatureID(layer))
            
            f.setAttribute("ID", ID)
            f.setGeometry(self.geom)
            layer.addFeature(f)
            
            layer.updateFeature(f)
            layer.updateExtents()
            layer.triggerRepaint()
            mc.refresh()
        
        else: # Wrong layer
            # Mapping is inactive
            pass
    #  return

# ***************  Set feature ID **********************************

    def setFeatureID(self, layer):
        feature_ids = []

        for feat in layer.getFeatures():
            id_att = feat.attribute("ID")
            if id_att in (None, ""):
                continue

            try:
                feature_ids.append(int(id_att))
            except (TypeError, ValueError):
                continue

        if not feature_ids:
            return str(0)

        return str(max(feature_ids) + 1)



# ***************  Disable tools - allows user to stop having things appear *********

    def stopMap(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** stopMap")
        
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        pr = layer.dataProvider()
        self.featuretool.deactivate()
        self.mapActive = False
        saved = layer.commitChanges()

        layer.updateExtents()

        
        if self.debugOn == True:
            QgsMessageLog.logMessage("Changes committed "+str(saved))
  
        self.currentDlg.close()

    
# **********************************************************************
  
    def buttonChanged(self):
        # QgsMessageLog.logMessage("** Button changed")
        # Checks status for starting mapping - button changed, startButton clicked etc
        # Allows for any other things to be done
        self.mapActive = True

# **********************************************************************

    def swapTool(self, toolOn, toolOff):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Swap tool")
        
        self.canvas.setMapTool(toolOn)
        toolOn.activate()
        toolOff.deactivate()
    
    

############# Code for linking ##################################################################
# *************** Link components *************************************

    def linkComps(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Link components")
        
        self.Link = True
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
 
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return

        self.linktool.clearSelectList()
        layer.removeSelection()
        self.swapTool(self.linktool, mc.mapTool())
        
        self.linktool.setDir("Unidirectional")
        self.linktool.setType("Mass flux")
        if self.debugOn == True:
            QgsMessageLog.logMessage("Set: "+str(self.linktool.getDir()) +" "+str(self.linktool.getType()))

        layer.startEditing()
        
        self.mapActive = True


        self.connectDlg = ConnectFeatures()
        self.windowX = self.dlg.pos().x()
        self.windowY = self.dlg.pos().y() + self.windowH + 40
        self.connectDlg.setGeometry(self.windowX, self.windowY, self.connectDlg.width(), self.connectDlg.height())
        self.connectDlg.ui.doneButton.clicked.connect(self.buildConnect)
        self.connectDlg.ui.clearButton.clicked.connect(self.linktool.clearSelectList)
        self.connectDlg.ui.typeGroup.buttonClicked.connect(self.arrowTypeChanged)
        self.connectDlg.ui.directGroup.buttonClicked.connect(self.arrowDirectChanged)
        self.connectDlg.ui.closeButton.clicked.connect(self.closeConnect)
        self.connectDlg.show()

    
# *************** Connecting components *************************************
    # Code to deal with setting up connections between components
    
    def buildConnect(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Build connection")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        pr = layer.dataProvider()
        prconn = self.cesmconlayer.dataProvider()
        
        direc = self.linktool.getDir()
        type = self.linktool.getType()
        featList = []
        
        # Check that exactly two components are selected for connections.
        self.featIdList = self.linktool.getSelectIdList() # Specific list from clicktool, in selected order
        if len(self.featIdList) == 2:
            layer.selectByIds(self.featIdList)
     
            # Should be able to simplify this code.
            # If we want to chain links together, can loop through features.
            featList = []
            for fid in self.featIdList:
                request = QgsFeatureRequest(fid)
                for feat in layer.getFeatures(request):
                    featList.append(QgsFeature(feat))
                    break

            if len(featList) != 2:
                self.msgBox.setText("Exactly two mapped objects must be selected for linking")
                self.msgBox.exec_()
                return
            
            feat1 = featList[0]
            geom1 = feat1.geometry()
            
            feat2 = featList[1]
            geom2 = feat2.geometry()
            
            # Constructed this way to be backwards compatible
            idList = "["+ str(feat1.attribute("ID"))+"L,"+str(feat2.attribute("ID"))+"L]"
            
            for fid in self.featIdList:
                req = QgsFeatureRequest(fid)
                # set 'connections' attribute value to the list of ids
                feat = QgsFeature()
            
                for feat in layer.getFeatures(req):
                    newConn = feat.attribute('Connect')
                    if newConn != None:
                            feat.setAttribute('Connect', newConn+str(idList))
                    else:
                        feat.setAttribute('Connect', str(idList))
                    layer.updateFeature(feat)
        
    
            xs = (feat1['GeoX'])
            ys = (feat1['GeoY'])
            xe = (feat2['GeoX'])
            ye = (feat2['GeoY'])
            
            pointS = QgsPoint(xs, ys)
            pointE = QgsPoint(xe, ye)
            
            self.atVertex = 0
            self.beforeVertex = 0
            self.afterVertex = 0
            self.sqrDist = 0
            
            closestStart = geom1.closestVertex(QgsPointXY(pointE))
            closestEnd = geom2.closestVertex(QgsPointXY(pointS))
            
            dist = math.sqrt(closestStart[4])
            
            # Need to make arrow width depend on screen coords size.
            norm = self.size.normalize()
            wid = self.size.width()
            height = self.size.height()
            
            #  scale = wid/1000
            mapToPix = mc.getCoordinateTransform()
            scale = mapToPix.mapUnitsPerPixel()
            
            width = 4.0*scale
            length = 10.0*scale
            
            if not self.cesmconlayer.isEditable():
                self.cesmconlayer.startEditing()
    
            fieldsCon = self.cesmconlayer.fields()
        
            arrFeat = self.drawArrows(closestStart[0], closestEnd[0], type, direc)
            arrFeat.setFields(fieldsCon)
            
            arrFeat['Link'] = "True"
            arrFeat['StartX'] = pointS.x()
            arrFeat['StartY'] = pointS.y()
            arrFeat['EndX'] = pointE.x()
            arrFeat['EndY'] = pointE.y()
            arrFeat['Mass Flux'] = 0.0
            arrFeat['Influences'] = "False"
            arrFeat['ConType'] = str(type)
            arrFeat['Direct'] = str(direc)
            arrFeat['Connect'] = str(idList)

            conID = str(self.setFeatureID(self.cesmconlayer))
            arrFeat['ID'] = conID
            
            self.cesmconlayer.addFeature(arrFeat)
            self.cesmconlayer.updateFeature(arrFeat)
            self.cesmconlayer.commitChanges()

            # Set up the feature IDs for connections

            self.canvas.refresh()
            self.linktool.clearSelectList()
            
            self.cesmlayer.startEditing()
            
            self.canvas.setMapTool(self.linktool)
            mc.setCurrentLayer(self.cesmlayer)
            self.mapActive = True
        else:
            self.msgBox.setText("Exactly two mapped objects must be selected for linking")
            self.msgBox.exec_()


# *************** Draw Arrows *************************************

            #    Based on code from
            #    Arrows
            #    A QGIS plugin
            #    Draw polygon arrows based on polylines
            #    -------------------
            #		begin                : 2012-03-06
            #		copyright            : (C) 2012 by Gregoire Piffault
            #    email                : gregoire.piffault@gmail.com

# ***************************************************************************
    
    def drawArrows(self, pointS, pointE, type, head):
        # Could build a class for this.
        # QgsMessageLog.logMessage("** Draw arrows")
        xs = pointS.x()
        ys = pointS.y()
        xe = pointE.x()
        ye = pointE.y()
        

        allArr = QgsFeature()

        # Arrow shaft as line - line geometry
        geomShaft = QgsGeometry.fromPolylineXY([QgsPointXY(pointS), QgsPointXY(pointE)])
        
        geomShaft = QgsGeometry.fromPolylineXY([QgsPointXY(pointS), QgsPointXY(pointE)])
        allArr.setGeometry(geomShaft)
        
        return allArr
            
# *************** Type of Arrows *************************************

    def arrowTypeChanged(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** ArrowTypeChanged")
        
        self.canvas.setMapTool(self.linktool)
        type = self.connectDlg.getType()
        if self.debugOn == True:
            QgsMessageLog.logMessage("ArrowType "+str(type))
        self.linktool.setType(type)

    
# *************** Head of Arrows *************************************
        
    def arrowDirectChanged(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** arrowDirectChanged")
        self.canvas.setMapTool(self.linktool)
        dir = self.connectDlg.getDir()
        self.linktool.setDir(dir)

#
############# Code for viewing by order ##################################################################
# *************** Show only one order *************************************

    ############# Code for View Levels ##################################################################
    # ****************************************************
    def viewByOrder(self):
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        orderList = []
        
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        orderSel = self.dispDlg.getLevel()
        if self.debugOn == True:
            QgsMessageLog.logMessage("** viewByOrder "+str(orderSel))

        layerName = "Order "+orderSel
        self.viewLayer = QgsVectorLayer("Point", layerName, "memory")
        viewPR = self.viewLayer.dataProvider()
                
        if not self.allCESMFields:
            self.createAttributeFields()
                
        viewPR.addAttributes(self.allCESMFields)
        self.viewLayer.updateFields()
        self.registry.addMapLayer(self.viewLayer)
    
        self._set_display_field(self.viewLayer, "Name")
        # self.viewLayer.enableLabels(True)
        
        # Load NewStyle file - this sets the 'label' according to the level attr.
        (errorLabMsg, resLab) = self.viewLayer.loadNamedStyle(self.plugin_dir+"/CESMComp.qml")
        if not resLab:
            QgsMessageLog.logMessage("CompStyleLoad "+errorCatMsg)
        
         # self.le = self.rendV2.labelingEngine()
        self.labelObj = None


        pr = layer.dataProvider()
        ordIndex = pr.fieldNameIndex("Order")
        request = QgsFeatureRequest()

        request.setFilterExpression (u'"Order" = orderSel')
        
        # Set the selection
                
        self.viewLayer.startEditing()
        feat = QgsFeature()

        for feat in layer.getFeatures():
            order = str(feat.attribute('Order'))
            
            if order == orderSel:
                self.viewLayer.addFeature(feat)
                if self.debugOn == True:
                    QgsMessageLog.logMessage("Feature added ")
                mc.refresh()
            
        self.viewLayer.commitChanges()
        
        layers = self._all_layers()

        for layer1 in layers:
            if "Order" in layer1.name():
                self._set_layer_visible(layer1, False)
        
        self._set_layer_visible(self.cesmlayer, False)
        self._set_layer_visible(self.cesmconlayer, False)
        self._set_layer_visible(self.viewLayer, True)
#

# *************** Level changed *************************************

    def levelChanged(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Level Changed")
        
        level = self.dispDlg.getLevel()

# **********************************************************************

    def dispOpt(self):
    # QgsMessageLog.logMessage("** dispOpt")
    # Display options
    #        self.msgBox.setText("Display options not yet available")
    #        self.msgBox.exec_()
    
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Display options")
        
        
        self.dispDlg = DisplayOptions()
        self.windowX = self.dlg.pos().x()
        self.windowY = self.dlg.pos().y() + self.windowH + 40
        self.dispDlg.setGeometry(self.windowX, self.windowY, self.dispDlg.width(), self.dispDlg.height())
        
        
        for num in range(0, self.numLevels):
            if self.intComp[num] == 0: # For a level with no components, no mapping dialog
                continue
            butText = self.levelName[num]
            self.dispDlg.addNewButton(butText, num)
    
            butList = self.dlg.ui.buttonGroup.buttons()
    
        for button in butList:
            button.clicked.connect(self.levelChanged)


        self.dispDlg.ui.showButton.clicked.connect(self.viewByOrder)
        self.dispDlg.ui.buttonGroup.buttonClicked.connect(self.levelChanged)
        self.dispDlg.ui.closeButton.clicked.connect(self.closeDisp)
        self.dispDlg.show()
    


# ######################## Code for Editing #########################
# **********************************************************************
#

    def editMap(self):
        if self.debugOn:
            QgsMessageLog.logMessage("** editMap")
        # Edit the map
        
        self.EditToolOn = True
        
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return

        self.mapActive = True
           
        self.editDlg = EditFeatures()
        self.windowX = self.dlg.pos().x()
        self.windowY = self.dlg.pos().y() + self.windowH + 40
        self.editDlg.setGeometry(self.windowX, self.windowY, self.editDlg.width(), self.editDlg.height())
        self.editDlg.ui.doneButton.clicked.connect(self.doneEdit)
        self.editDlg.ui.moveButton.clicked.connect(self.moveCompStart)
        self.editDlg.ui.removeButton.clicked.connect(self.delCompStart)
        self.editDlg.ui.closeButton.clicked.connect(self.closeEdit)
        self.editDlg.show()

# self.msgBox.setText("Edit function not yet available")
# self.msgBox.exec_()


# *************** Component moved tool *************************************

    def moveCompStart(self):
    
        self.MoveToolOn = True
            
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        currentTool = mc.mapTool()
        self.swapTool(self.movetool, currentTool)
        self.mapActive = True
        layer.startEditing()


# *************** Component moved *************************************

    def moveComp(self):
     
        if self.debugOn:
            QgsMessageLog.logMessage("Test for move component")
        
        if self.MoveToolOn:
            mc = self.canvas
            rend = mc.mapSettings()
            mc.setCurrentLayer(self.cesmlayer)
            layer = mc.currentLayer()
            if not self.checkCESMLayer(layer):
                self.msgBox.setText("Please select a CESM layer")
                self.msgBox.exec_()
                return

            currentTool = mc.mapTool()
            self.swapTool(self.movetool, currentTool)
            layer.startEditing()

            pr = layer.dataProvider()
            connLayer = self.cesmconlayer
            prcon = connLayer.dataProvider()
            connectList = []

            layer.startEditing()
            self.featIdList = self.movetool.getSelectIdList() # Specific list from clicktool, in selected order
            self.featIds = layer.selectedFeatureIds() # This contains the IDs, in ID order
            fields=layer.fields()

            drawPoint = self.movetool.getPoint()
        
            centerx = drawPoint.x()
            centery = drawPoint.y()
                
            geoPoint = self.movetool.getPoint()
            screenPoint = self.movetool.getScreenPoint()
            
            self.geom = QgsGeometry.fromPointXY(QgsPointXY(geoPoint))
            featNew = QgsFeature(fields)
            featNew.setGeometry(self.geom)
            
            # Get the feature selected to move
            for fid in self.featIdList:
                req = QgsFeatureRequest(fid)
                
                feat = QgsFeature(fields)
                
                
                for feat in layer.getFeatures(req):
                    idOld = feat.id()
                    # Get all the old attributes, reset the coords
                    attr = feat.attributes()
                    connectList = str(feat.attribute("Connect"))
                    idOldPt = QgsPoint(feat.attribute('GeoX'),feat.attribute('GeoY'))
                    id = feat.attribute("ID")
                    
                    connLayer.startEditing()
                    itercon = connLayer.getFeatures()
                    featcon = QgsFeature()
                    featconNew = QgsFeature()
                    fieldsCon = self.cesmconlayer.fields()
                    moveList = []
                    for featcon in itercon:
                        st = QgsPoint(featcon.attribute('StartX'),featcon.attribute('StartY'))
                        ed = QgsPoint(featcon.attribute('EndX'),featcon.attribute('EndY'))
                        
                        # Use start and end point to avoid issues with backwards compatibility with IDs
                        if (st == idOldPt or ed == idOldPt):
                            idcon = featcon.id()  # Feature has start or end connection
 
                            idConAtt = featcon.attribute("ID")
                            moveList.append(idcon)
                        
                            attCon = featcon.attributes() # Get the attributes
                            
                            if (st == idOldPt):
                                st = geoPoint
                            if (ed == idOldPt):
                                ed = geoPoint

                            ctype = featcon.attribute('ConType')
                            dir = featcon.attribute('Direct')
                           
                            featconNew = self.drawArrows(st, ed, type, dir)
                            featconNew.setFields(fieldsCon)
                            featconNew.setAttributes(attCon)
                            featconNew.setAttribute('StartX', st.x())
                            featconNew.setAttribute('StartY', st.y())
                            featconNew.setAttribute('EndX', ed.x())
                            featconNew.setAttribute('EndY', ed.y())
            
                            # Reset start and end points appropriately.
                            connLayer.addFeature(featconNew)
                            connLayer.updateFeature(featconNew)
                            mc.refresh()
                                
                        else:
                            pass

                prcon.deleteFeatures(moveList)
                
                featNew.setAttributes(attr)
                featNew.setAttribute('ScreenX', screenPoint.x())
                featNew.setAttribute('ScreenY', screenPoint.y())
                featNew.setAttribute('GeoX', geoPoint.x())
                featNew.setAttribute('GeoY', geoPoint.y())
                layer.addFeature(featNew)
                #layer.updateFeature(featNew)
 
                pr.deleteFeatures([idOld])
                mc.refresh()

                saved = layer.commitChanges()
                saved = self.cesmconlayer.commitChanges()
                self.movetool.clearSelectList()
                self.MoveToolOn = False


# *************** Component moved tool *************************************

    def delCompStart(self):
    
        self.EditToolOn = True
        
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        currentTool = mc.mapTool()
        self.swapTool(self.delcomptool, currentTool)
        
        self.mapActive = True
        layer.startEditing()
    

# *************** Component removed *************************************
# This handles the 'Feature deleted signal' to take care of connections and cleanup

    def delComp(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** Component removed")
        
        if self.EditToolOn:
            mc = self.canvas
            rend = mc.mapSettings()
            mc.setCurrentLayer(self.cesmlayer)
            layer = mc.currentLayer()
            if not self.checkCESMLayer(layer):
                self.msgBox.setText("Please select a CESM layer")
                self.msgBox.exec_()
                return
        
            pr = layer.dataProvider()
            connLayer = self.cesmconlayer
            if connLayer is None:
                self.msgBox.setText("CESM connections layer is not available")
                self.msgBox.exec_()
                return
            prcon = connLayer.dataProvider()

            self.featIdList = self.delcomptool.getSelectIdList() # Specific list from clicktool, in selected order
            self.featIds = layer.selectedFeatureIds() # This contains the IDs, in ID order
            fields=layer.fields()
            removed_component_ids = []
            removed_points = []

            if not self.featIdList:
                self.msgBox.setText("Please select at least one mapped component")
                self.msgBox.exec_()
                return
            
            for fid in self.featIdList:
                req = QgsFeatureRequest(fid)
                feat = QgsFeature()
                
                for feat in layer.getFeatures(req):
                    idDel = feat.id()
                    idOldPt = QgsPoint(feat.attribute('GeoX'),feat.attribute('GeoY'))
                    removed_id = feat.attribute("ID")
                    removed_component_ids.append(str(removed_id))
                    removed_points.append(idOldPt)
                    pr.deleteFeatures([idDel])

    
    # Check if feature is in any list
    
            connAttIndex = pr.fieldNameIndex("Connect")
            connConAttIndex = prcon.fieldNameIndex("Connect")
            childrenAttIndex = self.cesmlayerpr.fieldNameIndex("Children")
            parentAttIndex = self.cesmlayerpr.fieldNameIndex("Parent")
            membersAttIndex = self.cesmlayerpr.fieldNameIndex("Members")
            
            feat = QgsFeature()
            iter = layer.getFeatures()
            
            for feat in iter:
                membList = self._clean_deleted_id_text(feat.attribute("Members"), removed_component_ids)
                childList = self._clean_deleted_id_text(feat.attribute("Children"), removed_component_ids)
                parentList = self._clean_deleted_id_text(feat.attribute("Parent"), removed_component_ids)
                connectList = self._clean_deleted_connect_text(feat.attribute("Connect"), removed_component_ids)

                feat.setAttribute(membersAttIndex, membList)
                feat.setAttribute(childrenAttIndex, childList)
                feat.setAttribute(parentAttIndex, parentList)
                feat.setAttribute(connAttIndex, connectList)
                layer.updateFeature(feat)
    

            remList = []
    
        # If feature in connection list, that connection is deleted
            itercon = connLayer.getFeatures()
            for featcon in itercon:
                attMap = featcon.attributes()
                st = QgsPoint(featcon.attribute('StartX'),featcon.attribute('StartY'))
                ed = QgsPoint(featcon.attribute('EndX'),featcon.attribute('EndY'))
                        
                # Use start and end point to avoid issues with backwards compatibility with IDs
                if (st in removed_points or ed in removed_points):
                    idcon = featcon.id()
                    idConAtt = featcon.attribute("ID")
                    remList.append(idcon)
           
                else:
                    pass

            prcon.deleteFeatures(remList)
            layer.updateFields()
            self.cesmconlayer.updateFields()
            saved = layer.commitChanges()
            savedcon = self.cesmconlayer.commitChanges()
            self.canvas.refresh()
            
            self.delcomptool.clearSelectList()
            self.EditToolOn = False

        else:
            if self.debugOn == True:
                QgsMessageLog.logMessage("Don't do all this")
            pass
    

# ***************  Disable Edit tools *********

    def doneEdit(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** stopEdit")
            
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return

        self.clicktool.clearSelectList
        pr = layer.dataProvider()
        self.movetool.deactivate()
        self.delcomptool.deactivate()
        self.MoveToolOn = False
        self.EditToolOn = False
        self.mapActive = False
        saved = self.cesmlayer.commitChanges()
        saved = self.cesmconlayer.commitChanges()

   
############# Code for grouping ##################################################################
# *************** Group components *************************************

    def groupComps(self):
        # This sets up the selection tool to be the active tool.
        if self.debugOn == True:
            QgsMessageLog.logMessage("** groupComps")
            
        mc = self.canvas
        rend = mc.mapSettings()
        mc.setCurrentLayer(self.cesmlayer)
        
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return

        self.Group = True
        
        currentTool = mc.mapTool()
        self.swapTool(self.grouptool, currentTool)
        
        #self.featuretool.deactivate()
        layer.startEditing()
        
        
        # This could be separated out to setUp GUI features
        self.groupDlg = GroupFeatures()
        self.windowX = self.dlg.pos().x()
        self.windowY = self.dlg.pos().y() + self.windowH + 40
        
        self.groupDlg.setGeometry(self.windowX, self.windowY, self.groupDlg.width(), self.groupDlg.height())
        self.groupDlg.ui.doneButton.clicked.connect(self.checkGroup)
        self.groupDlg.ui.clearButton.clicked.connect(self.grouptool.clearSelectList)
        self.groupDlg.ui.closeButton.clicked.connect(self.closeGroup)
        self.groupDlg.ui.selEditButton.clicked.connect(self.selectGroup)
        self.groupDlg.ui.unGroupButton.clicked.connect(self.unGroup)
        self.groupDlg.ui.grButtonGroup.buttonClicked.connect(self.groupButChanged)
        
        self.groupDlg.show()


# *************** Group Button Changed *************************************
    
    def groupButChanged(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** groupButChanged")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        button = self.groupDlg.ui.grButtonGroup.checkedButton()
        choice = button.text()
        if choice == "Edit Group":
            allGrouped = self.getAllGroups() # Returns any component in any group
            layer.selectByIds(allGrouped)
            self.groupEdButton = True
            self.groupDlg.ui.selEditButton.setEnabled(True)
            self.groupDlg.ui.unGroupButton.setEnabled(True)

            # layer.editEnabled = True
            layer.startEditing()
            self.canvas.setMapTool(self.grouptool)
            self.grouptool.activate()
                    
        else:
            self.groupEdButton = False
            #  layer.editEnabled = True
            self.groupDlg.ui.selEditButton.setEnabled(False)
            self.groupDlg.ui.unGroupButton.setEnabled(False)
            layer.startEditing()
            self.canvas.setMapTool(self.grouptool)
            self.grouptool.activate()
            self.grouptool.clearSelectList()

#  *************** Grouping features **************************************************
    # Code to check grouping attributes
            
    def checkGroup(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** checkGroup")
            QgsMessageLog.logMessage("Check the grouping")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        pr = layer.dataProvider()
        
        featIds = []
        self.oldChildList = []
        count = 0
        
        # Get the index for various attributes
        nameAttIndex = self.cesmlayerpr.fieldNameIndex("Name")
        childrenAttIndex = self.cesmlayerpr.fieldNameIndex("Children")
        parentAttIndex = self.cesmlayerpr.fieldNameIndex("Parent")
        membersAttIndex = self.cesmlayerpr.fieldNameIndex("Members")
        inGroupIndex = self.cesmlayerpr.fieldNameIndex("InGroup")
        
        # Check that we have selected at least one feature
        if layer.selectedFeatureCount() == 0:
        # No features selected
            self.msgBox.setText("Please select at least one mapped component")
            self.msgBox.exec_()

        # One or more features selected
        else:
            featIdList = []
            # Get the selected features
            featGroup = layer.selectedFeatures()
            featIdSelList = layer.selectedFeatureIds()
            
            for fid in featIdSelList:
                req = QgsFeatureRequest(fid)
                feat = QgsFeature()
                for feat in layer.getFeatures(req):
                    featIdList.append(feat.attribute("ID"))
        
            
            # Returns True if any selected feature is already part of a group
            self.isExists = self.groupExists(featGroup)

            # Return parent feature
            parentFeat = self.getParent(featGroup)
            
            # No single parent
            if parentFeat == None:
                self.msgBox.setText("Select only one component for the parent")
                self.msgBox.exec_()
                layer.startEditing()
            
            
            # Single parent selected in selection list
            else: # Identify parent and return it as feature
                
                # Get info about parent, remove it from child list, do appropriate changes to parent attributes
                parentAttMap = parentFeat.attributes()
                parentFeatName = parentFeat.attribute("Name")
                parentId = (parentFeat.attribute("ID"))
                parentObj=self.compObjects[parentFeatName]  # gets the parent object
                
                # Make a separate list of the childIDs
                childFeatId = []
                childFeatId.extend(featIdList)
                childFeatId.remove(parentId)
                
                childGroup = []
                childGroup.extend(featGroup)
                childGroup.remove(parentFeat)


# *********** Old group exists ********************************

                if self.isExists and self.groupEdButton:
                # Get the old members and children
                    self.groupDlg.ui.editButton.setChecked(True)
                    self.groupEdButton = True
                    
                    oldMembers = (parentFeat.attribute("Members"))
                    attOldChild = (parentFeat.attribute("Children"))
                    oldChild = (attOldChild) # This is the list of children of this parent
                    parentFeat[childrenAttIndex, featIdList]
                    
                    self.setSelectedGroup(oldMembers)
                    
                    for feat in featGroup:
                        # Check for duplicates before this
                        feat[membersAttIndex, oldMembers+(featIdList)]


# *********** New group ********************************

                elif self.groupEdButton == False:
                    
                    for feat in childGroup:
                        childAttMap = feat.attributes()
                        childName = str(feat.attribute("Name"))
                        allowed = parentObj.checkChild(childName)
                        
                        if not(allowed):
                            self.msgBox.setText("Child "+childName+" not allowed")
                            self.msgBox.exec_()
                            break
                        else:
                            # Add parent to attributes for children
                            feat.setAttribute(parentAttIndex, parentId)
                            # Add siblings to all child attributes and members
                            oldMembs = feat.attribute('Members')
                            if self.debugOn == True:
                                QgsMessageLog.logMessage("Members "+str(oldMembs))
                            if oldMembs != NULL:
                                feat.setAttribute(membersAttIndex, oldMembs.append(featIdList))
                            else:
                                feat.setAttribute(membersAttIndex, featIdList)
                            feat.setAttribute(inGroupIndex, "True")
                            
                            oldChild = (parentFeat.attribute('Children'))
                            if oldChild != NULL:
                                parentFeat.setAttribute(childrenAttIndex, oldChild.append(childFeatId))
                            else:
                                parentFeat.setAttribute(childrenAttIndex, childFeatId)
                                parentFeat.setAttribute(membersAttIndex, featIdList)
                            
                            parentFeat.setAttribute(inGroupIndex, "True")
                            layer.updateFeature(feat)
                
                    layer.updateFeature(parentFeat)
                    saved = layer.commitChanges()
                    self.grouptool.clearSelectList()
                
                    # layer.editEnabled = True
                    layer.startEditing()
                    self.canvas.setMapTool(self.grouptool)
                    self.grouptool.activate()
                        
                    self.canvas.refresh()
                    
                                    
# *************** Check for Existing Group ***********************************************
    
    def groupExists(self, featGroup):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** groupExists")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        pr = layer.dataProvider()
        inGroupIndex = pr.fieldNameIndex("InGroup")
    
        # Check if anything in the selection is already a member of a group
        for feat in featGroup:
            attMap = feat.attributes()
            memGroup = (feat.attribute("InGroup"))
            
            if memGroup == "True":
                return True
            else:
                return False


# *************** Get all grouped components ***********************************************

    def getAllGroups(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** getAllGroups")
        inGroup = []
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        pr = layer.dataProvider()
        inGroupIndex = pr.fieldNameIndex("InGroup")

        for featGr in layer.getFeatures():
            inGrp = featGr.attribute("InGroup")
            
            if inGrp == "True":
               inGroup.append(featGr.attribute("ID"))
    
        return inGroup


# *************** Select Existing Group ***********************************************

    def setSelectedGroup(self, oldMembers):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** setSelectedGroup")
        # Set selected features from old members
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        oldGroup = []

        for featSel in layer.getFeatures():
            fid = featSel.attribute("ID")
            if str(fid) in oldMembers:
                oldGroup.append(fid)
                layer.updateFeature(featSel)
        
        layer.selectByIds(oldGroup)
        self.canvas.refresh()

           
# *************** Check heirarchy levels ***********************************************

    def getParent(self, featSelList):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** getParent")
    # Loop thru features selected, check they have the same heirarchy level
    # and that one is the parent feature.
        featGroup = featSelList
        levelAttIndex = self.cesmlayerpr.fieldNameIndex("Order")
        levels = [] # List for level values, should have same index as feature.
        
        for feat in featGroup:
            attMap = feat.attributes()
            levelAtt = (feat.attribute("Order"))
            levels.append(levelAtt)
        
        # Need minimum for parent, first one with level = 0. Then need to check for others.
        lowest = min(levels) # gets the minimum value in the list of levels.
        n = levels.count(lowest) # Checks how many have this lowest value
        
        # Checks that only one can be the parent
        if n != 1:
            return None

        else:
            parentIndex = levels.index(lowest)
            parentFeat = featGroup[parentIndex]
            return parentFeat

# *************** Edit Group ***********************************************
    
    def selectGroup(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** SelectGroup")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = mc.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        selFeats= layer.selectedFeatures()
        selFeatsIds = layer.selectedFeatureIds()
        grExists = self.groupExists(selFeats)
        if grExists:
            if self.debugOn == True:
                QgsMessageLog.logMessage("Group exists")
            layer.selectByIds(selFeatsIds)
        else:
            if self.debugOn == True:
                QgsMessageLog.logMessage("Group doesn't exist")
                

# *************** Edit Group ***********************************************
    
    def unGroup(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** unGroup")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        if self.debugOn == True:
            QgsMessageLog.logMessage("In UnGroup routine")
        selGroup = layer.selectedFeatures()
        pr = layer.dataProvider()
        inGroupIndex = pr.fieldNameIndex("InGroup")
        childrenAttIndex = self.cesmlayerpr.fieldNameIndex("Children")
        parentAttIndex = self.cesmlayerpr.fieldNameIndex("Parent")
        membersAttIndex = self.cesmlayerpr.fieldNameIndex("Members")
        
        for feat in selGroup:
            attMap = feat.attributes()
            feat[inGroupIndex, "False"]
            feat[membersAttIndex, "NULL"]
            feat[parentAttIndex, "NULL"]
    # If there is nothing in parent, then remove any of the features from the 'children' attribute.


# **********************************************************************

    def analyseMap(self):
        # QgsMessageLog.logMessage("** analyseMap")
        # Analyse the map
        self.msgBox.setText("Analysis function not yet available")
        self.msgBox.exec_()


# **********************************************************************

    def getSelectedFeature(self):
        #if self.debugOn == True:
        #QgsMessageLog.logMessage("** getSelectedFeature")
        # This is triggered when selection is changed.
        if self.Group:
            # Then we are grouping
            if self.groupEdButton == True:
                if self.debugOn == True:
                    QgsMessageLog.logMessage("Group button is true")
                pass
        # self.editGroup()
        
        elif self.Link:
            # Then we are linking
            pass

        elif self.EditToolOn:
            # Edit button is on
            pass
        else:
            pass


# *************** Close main dialog *************************************

    def removeWindow(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** removeWindow")
        self.pluginActive = False
        self.dlg.close()
    

# *************** Close group dialog *************************************

    def closeGroup(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** closeGroup")
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        self.grouptool.deactivate()
        saved = layer.commitChanges()
        self.grouptool.clearSelectList()
        self.groupDlg.close()
    
    
# *************** Close connect dialog *************************************

    def closeConnect(self):
        if self.debugOn == True:
            QgsMessageLog.logMessage("** closeConnect")
        self.linktool.deactivate()
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return
        
        self.linktool.setDir(1)
        self.linktool.setType("Mass flux")
        savedConns = self.cesmconlayer.commitChanges()
        saved = self.cesmlayer.commitChanges()
        self.linktool.deactivate()
        self.linktool.clearSelectList()
        self.connectDlg.close()


# *************** Close Editdialog *************************************

    def closeEdit(self):
        
        if self.debugOn == True:
            QgsMessageLog.logMessage("** closeEdit")
        self.movetool.deactivate()
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        
        layer = self.canvas.currentLayer()
        if not self.checkCESMLayer(layer):
            self.msgBox.setText("Please select a CESM layer")
            self.msgBox.exec_()
            return

        savedConns = self.cesmlayer.commitChanges()
        self.movetool.deactivate()
        self.movetool.clearSelectList()
        
        self.delcomptool.deactivate()
        self.delcomptool.clearSelectList()
        self.editDlg.close()


# *************** Close Dispdialog *************************************

    def closeDisp(self):
       
        mc = self.canvas
        mc.setCurrentLayer(self.cesmlayer)
        layer = self.canvas.currentLayer()
        savedConns = self.cesmlayer.commitChanges()
        self.dispDlg.close()
                                                  

# ********************** Component class *******************************

class Component(object):
    def __init__(self, name):
        self.level = ""
        self.levName = ""
        self.suborder = ""
        self.suborderName = ""
        self.name = name
        self.colour = ""
        self.shape = ""
        self.allowedChildren = []
    
    
    def setChildren(self, childList):
        # Make them all lower case here
        self.allowedChildren = childList
            
                
    def getChildren(self):
        return self.allowedChildren
    
    
    def checkChild(self, child):
        # Check for capitalisation in childlist
        if str(child) == "all":
            return True
        if str(child) == "none":
            return False
        if (str(child)).lower() in (self.allowedChildren).lower():
            return True
        else:
            return False

    def setLevelName(self, nameLevel):
        self.levName = nameLevel
        
    def getLevelName(self):
        return self.levName
    
    def setLevel(self, inLevel):
        self.level = inLevel
    
    def getLevel(self):
        return self.level
    
    def setSuborderName(self, nameSuborder):
        self.suborderName = nameSuborder
    
    def getSuborderName(self):
        return self.suborderName
    
    def setName(self, namestr):
        self.name = namestr
    
    def getName(self):
        return self.name
    
    def setShape(self, shp):
        self.shape = shp
     
    def getShape(self):
        return self.shape
                                 
    def setColour(self, col):
        self.colour = col
     
    def getColour(self):
        return self.colour


# **********************************************************************
    # **********************************************************************
    
 
