import random
import json
import numpy as np
import pyvista as pv
from pyvista import examples
from vtk.util.numpy_support import vtk_to_numpy

import dash
from dash import html # Correct import for html components
from dash import dcc # Correct import for core components
import dash_bootstrap_components as dbc # Dash Bootstrap Components for layout
from dash.dependencies import Input, Output, State

import dash_vtk
from dash_vtk.utils import presets # Presets for colormaps


random.seed(42) # Set random seed for reproducibility


def toDropOption(name):
    """Helper function to format options for Dash Dropdown."""
    return {"label": name, "value": name}


# Get point cloud data from PyVista
# examples.download_crater_topo() downloads a topographical dataset of a crater.
uniformGrid = examples.download_crater_topo()
# Extract a subset of the grid for more manageable visualization.
subset = uniformGrid.extract_subset((500, 900, 400, 800, 0, 0), (5, 5, 1))


def updateWarp(factor=1):
    """
    Warps the terrain by a scalar factor (elevation) and extracts PolyData.
    This simulates terrain deformation based on a scale factor.
    """
    # Warp the terrain geometry based on its scalar (elevation) data.
    terrain = subset.warp_by_scalar(factor=factor)
    # Extract the polygonal data (surface mesh) from the warped terrain.
    polydata = terrain.extract_geometry()
    # Flatten the points array (x, y, z coordinates) for dash-vtk.
    points = polydata.points.ravel()
    # Get the polygonal connectivity (faces) for dash-vtk.
    polys = vtk_to_numpy(polydata.GetPolys().GetData())
    # Get the elevation data (scalars) associated with the points.
    elevation = polydata["scalar1of1"]
    # Calculate the min and max elevation for color mapping.
    min_elevation = np.amin(elevation)
    max_elevation = np.amax(elevation)
    return [points, polys, elevation, [min_elevation, max_elevation]]


# Initial warp of the terrain with a factor of 1.
points, polys, elevation, color_range = updateWarp(1)

# --- Dash Application Setup ---

# Initialize the Dash application with Bootstrap external stylesheets for styling.
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server # Standard way to expose the Flask server for deployment.

# Define the initial Dash VTK view component.
# This sets up a 3D rendering view for a GeometryRepresentation (our terrain mesh).
vtk_view = dash_vtk.View(
    id="vtk-view", # ID for the view, used in callbacks
    pickingModes=["hover"], # Enable hover picking for tooltip
    children=[
        dash_vtk.GeometryRepresentation(
            id="vtk-representation", # ID for the geometry representation
            children=[
                dash_vtk.PolyData(
                    id="vtk-polydata", # ID for the PolyData component
                    points=points, # Initial points data
                    polys=polys, # Initial polygonal connectivity
                    children=[
                        dash_vtk.PointData( # Data associated with points
                            [
                                dash_vtk.DataArray(
                                    id="vtk-array", # ID for the DataArray
                                    registration="setScalars", # Register as scalars for coloring
                                    name="elevation", # Name of the scalar array
                                    values=elevation, # Initial elevation values
                                )
                            ]
                        )
                    ],
                )
            ],
            colorMapPreset="erdc_blue2green_muted", # Initial colormap preset
            colorDataRange=color_range, # Initial color data range
            property={"edgeVisibility": True}, # Show edges of the mesh
            showCubeAxes=True, # Show cube axes around the model
            cubeAxesStyle={"axisLabels": ["", "", "Altitude"]}, # Label the Z-axis as Altitude
        ),
        # A separate GeometryRepresentation for displaying the picked point (a sphere).
        dash_vtk.GeometryRepresentation(
            id="pick-rep",
            actor={"visibility": False}, # Initially hidden
            children=[
                dash_vtk.Algorithm(
                    id="pick-sphere", # Sphere source for the picked point
                    vtkClass="vtkSphereSource",
                    state={"radius": 100}, # Initial radius of the sphere
                )
            ],
        ),
    ],
)

# Define the layout of the Dash application using Dash Bootstrap Components.
app.layout = dbc.Container(
    fluid=True, # Container takes full width
    style={"height": "100vh", "display": "flex", "flexDirection": "column"}, # Full viewport height, column layout
    children=[
        dbc.Row( # Row for controls (slider, dropdown, checklist)
            [
                dbc.Col( # Column for the scale factor slider
                    children=dcc.Slider(
                        id="scale-factor",
                        min=0.1, max=5, step=0.1, value=1,
                        marks={0.1: "0.1", 5: "5"},
                        className="p-2" # Add some padding
                    ),
                    width=4 # Occupy 4 columns of the 12-column grid
                ),
                dbc.Col( # Column for the colormap preset dropdown
                    children=dcc.Dropdown(
                        id="dropdown-preset",
                        options=list(map(toDropOption, presets)), # Options from dash_vtk presets
                        value="erdc_rainbow_bright", # Default colormap
                        className="p-2"
                    ),
                    width=4
                ),
                dbc.Col( # Column for the cube axes toggle checklist
                    children=dcc.Checklist(
                        id="toggle-cube-axes",
                        options=[{"label": " Show axis grid", "value": "grid"}],
                        value=[], # Initially unchecked
                        labelStyle={"display": "inline-block", "marginLeft": "10px"},
                        className="p-2"
                    ),
                    width=4
                ),
            ],
            style={"height": "12%", "alignItems": "center"}, # Align items vertically in the middle
            className="mb-3" # Margin bottom
        ),
        html.Div( # Div for the main VTK viewer
            vtk_view,
            style={"flexGrow": 1, "width": "100%", "height": "88%"} # Takes remaining height
        ),
        html.Pre( # Tooltip for picked points
            id="tooltip",
            style={
                "position": "absolute",
                "bottom": "25px",
                "left": "25px",
                "zIndex": 1,
                "color": "white",
                "backgroundColor": "rgba(0,0,0,0.7)",
                "padding": "5px",
                "borderRadius": "5px",
                "pointerEvents": "none", # Ensures tooltip doesn't block interactions
                "display": "none" # Hidden by default
            },
        ),
    ],
)


# --- Dash Callbacks ---

@app.callback(
    [
        Output("vtk-representation", "showCubeAxes"),
        Output("vtk-representation", "colorMapPreset"),
        Output("vtk-representation", "colorDataRange"),
        Output("vtk-polydata", "points"),
        Output("vtk-polydata", "polys"),
        Output("vtk-array", "values"),
        Output("vtk-view", "triggerResetCamera"), # Trigger camera reset on update
    ],
    [
        Input("dropdown-preset", "value"),
        Input("scale-factor", "value"),
        Input("toggle-cube-axes", "value"),
    ],
)
def updatePresetName(name, scale_factor, cubeAxes):
    """Callback to update terrain based on slider and dropdown selections."""
    # Re-warp the terrain based on the new scale factor
    points, polys, elevation, color_range = updateWarp(scale_factor)

    # Return updated properties for the VTK components
    return [
        "grid" in cubeAxes, # showCubeAxes is true if 'grid' is in the checklist value
        name, # New colormap preset
        color_range, # New color data range
        points, # Updated points data
        polys, # Updated polygons data
        elevation, # Updated elevation values
        random.random(), # Trigger a camera reset by providing a new random value
    ]


@app.callback(
    [
        Output("tooltip", "children"),
        Output("tooltip", "style"), # Update style to control visibility
        Output("pick-sphere", "state"), # Update sphere position
        Output("pick-rep", "actor"), # Update sphere visibility
    ],
    [
        Input("vtk-view", "clickInfo"), # Listen for click events
        Input("vtk-view", "hoverInfo"), # Listen for hover events
    ],
    [
        State("tooltip", "style") # Get current style to toggle visibility
    ]
)
def onInfo(clickData, hoverData, current_style):
    """Callback to display tooltip and sphere on hover/click."""
    info = hoverData if hoverData else clickData # Prefer hover data if available

    if info:
        # Check if the picked element is our terrain representation
        if (
            "representationId" in info
            and info["representationId"] == "vtk-representation"
        ):
            # Display detailed info in the tooltip
            tooltip_text = json.dumps(info, indent=2)

            # Update sphere position to the picked world position
            sphere_state = {"center": info["worldPosition"]}

            # Make sphere visible
            actor_visibility = {"visibility": True}

            # Make tooltip visible
            new_style = {**current_style, "display": "block"}

            return tooltip_text, new_style, sphere_state, actor_visibility

        # If picked something else or no valid pick, hide tooltip and sphere
        return "", {**current_style, "display": "none"}, {}, {"visibility": False}

    # If no hover or click data, hide tooltip and sphere
    return "", {**current_style, "display": "none"}, {}, {"visibility": False}


# Run the Dash application server.
# For Jupyter/Colab, 'mode='inline'' embeds the app output directly in the notebook.
# 'debug=True' enables hot-reloading and debug tools (set to False for production).
if __name__ == "__main__":
    app.run(debug=False, mode='inline') # Corrected to app.run() for newer Dash versions