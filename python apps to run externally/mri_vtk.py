# pip install dash dash-vtk itk dash-bootstrap-components

import os
import dash
from dash import html # Correct import for html components
import dash_bootstrap_components as dbc # Imported for potential future use, or remove if not needed.
import itk # ITK is used for reading DICOM files

import dash_vtk
from dash_vtk.utils import to_volume_state

import vtk # VTK is used by ITK for visualization pipeline conversion


def dcm_to_volume(dir_path):
    """
    Converts a directory containing DICOM slices into a VTK volume state
    compatible with dash-vtk.
    """
    # Read the DICOM series from the specified directory using ITK
    # itk.imread automatically handles sorting slices and metadata.
    itk_image = itk.imread(dir_path)

    # Convert the ITK image to a VTK image data object.
    # This is necessary because dash-vtk's to_volume_state expects a VTK image.
    vtk_image = itk.vtk_image_from_image(itk_image)

    # Convert the VTK image data to a volume state object for dash-vtk.
    volume_state = to_volume_state(vtk_image)

    return volume_state


# --- Data Loading and Volume State Creation ---
# The original code used __file__ which is not defined in Jupyter/Colab.

# Define the exact path to the MRI brain DICOM directory as provided by the user.
# This assumes the 'dash-vtk' repository has been cloned and is located at /content/dash-vtk.
mri_data_dir = "dash-vtk/demos/data/mri_brain"

# Check if the directory exists before attempting to load
if not os.path.exists(mri_data_dir):
    print(f"Error: MRI data directory not found at {mri_data_dir}")
    print("Please ensure you have cloned the 'dash-vtk' repository and the 'dicom-mri-brain' data is present.")
    print("Run '!git clone https://github.com/plotly/dash-vtk.git' in a previous cell.")
    # Create a dummy volume_state to prevent app crash if data is missing
    # For a real app, you might want to display an error message in the Dash layout.
    reader = vtk.vtkConeSource() # Use a simple cone as fallback
    reader.SetResolution(64)
    reader.Update()
    volume_state = to_volume_state(reader.GetOutput())
else:
    # Convert the DICOM series to a volume state
    volume_state = dcm_to_volume(mri_data_dir)


# --- Dash Application Setup ---

# Initialize the Dash application.
app = dash.Dash(__name__)
server = app.server # This line is typically used for Gunicorn deployment, but harmless in Jupyter.

# Define the Dash VTK view component.
# This sets up a 3D rendering view with a VolumeRepresentation and VolumeController.
vtk_view = dash_vtk.View(
    dash_vtk.VolumeRepresentation(
        children=[
            # VolumeController allows interactive adjustment of volume rendering properties (e.g., opacity, colors).
            dash_vtk.VolumeController(),
            # Volume component renders the 3D medical data.
            dash_vtk.Volume(state=volume_state),
        ]
    )
)

# Define the layout of the Dash application.
app.layout = html.Div(
    style={"height": "calc(100vh - 50px)", "width": "100%", "backgroundColor": "#f0f0f0"},
    children=[
        html.Div(
            vtk_view,
            style={"height": "100%", "width": "100%", "display": "flex", "justifyContent": "center", "alignItems": "center"}
        )
    ],
)

# Run the Dash application server.
# For Jupyter/Colab, 'mode='inline'' embeds the app output directly in the notebook.
# 'debug=True' enables hot-reloading and debug tools (set to False for production).
if __name__ == "__main__":
    app.run(debug=False, mode='inline') # Corrected to app.run() for newer Dash versions