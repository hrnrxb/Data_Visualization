# Install necessary libraries if not already installed
# !pip install dash dash-vtk pyvista

import os
import dash
from dash import html # Correct import for html components
from dash import dcc # Correct import for core components (though not strictly used in this layout, good practice)
# dash_bootstrap_components is imported in the original snippet but not used in the layout.
# If you intend to use Bootstrap components, ensure it's installed and used.
# import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State # Standard Dash imports for callbacks

import numpy as np
import pyvista as pv # PyVista for 3D data handling
from pyvista import examples # PyVista examples for data download

import dash_vtk # Dash VTK components
from dash_vtk.utils import to_volume_state # Not used in this specific point cloud example, but kept if part of larger context

np.random.seed(42) # Set seed for reproducibility of random selection

# Get point cloud data from PyVista examples
# pyvista.examples.download_lidar() downloads a sample LiDAR point cloud.
dataset = examples.download_lidar()
subset_ratio = 0.2 # Define the ratio for subsetting the points
selection_indices = np.random.randint(
    low=0, high=dataset.n_points - 1, size=int(dataset.n_points * subset_ratio)
)
# Select a random subset of points from the dataset
points = dataset.points[selection_indices]
xyz = points.ravel() # Flatten the array of points (x, y, z coordinates)
elevation = points[:, -1].ravel() # Get the Z-coordinate (elevation) for scalar mapping
min_elevation = np.amin(elevation) # Calculate min elevation for color mapping
max_elevation = np.amax(elevation) # Calculate max elevation for color mapping
print(f"Number of points: {points.shape[0]}") # Print number of selected points
print(f"Elevation range: [{min_elevation:.2f}, {max_elevation:.2f}]") # Print elevation range


# --- Dash Application Setup ---

# Initialize the Dash application.
app = dash.Dash(__name__)
server = app.server # This line is typically used for Gunicorn deployment, but harmless in Jupyter.

# Define the Dash VTK view component.
# This sets up a 3D rendering view specifically for a PointCloudRepresentation.
vtk_view = dash_vtk.View(
    [
        dash_vtk.PointCloudRepresentation(
            xyz=xyz, # Pass the flattened XYZ coordinates
            scalars=elevation, # Pass the elevation values as scalars for coloring
            colorDataRange=[min_elevation, max_elevation], # Define the color range for scalars
            property={"pointSize": 2}, # Set the size of the rendered points
        )
    ]
)

# Define the layout of the Dash application.
app.layout = html.Div(
    style={"height": "calc(100vh - 16px)", "width": "100%", "backgroundColor": "#f0f0f0"}, # Added background for clarity
    children=[html.Div(vtk_view, style={"height": "100%", "width": "100%"})], # Main div containing the VTK view
)

# Run the Dash application server.
# For Jupyter/Colab, 'mode='inline'' embeds the app output directly in the notebook.
# 'debug=True' enables hot-reloading and debug tools (set to False for production).
if __name__ == "__main__":
    app.run(debug=False, mode='inline') # Corrected to app.run() for newer Dash versions
