from dash import Dash, dcc, html, Input, Output, State, callback_context
import pandas as pd
from pymodbus.client import ModbusSerialClient, ModbusTcpClient
import os
import io
import base64

# Initialize the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# Create the uploads directory if it doesn't exist
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Predefined COM ports and baud rates for dropdowns
COM_PORTS = [f"COM{i}" for i in range(1, 21)]
BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]

# Modbus function code options
MODBUS_FUNCTIONS = {
    "Read Coils (FC=1)": 1,
    "Read Discrete Inputs (FC=2)": 2,
    "Read Holding Registers (FC=3)": 3,
    "Read Input Registers (FC=4)": 4
}

# Define layouts for each page
home_page = html.Div([
    html.H1("Welcome to the VX Flowmeter App"),
    html.P("Navigate using the links on the sidebar to explore different functionalities."),
])

csv_import_page = html.Div([
    html.H2("CSV File Import"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px dashed', 'borderRadius': '6px',
            'textAlign': 'center', 'margin': '10px',
            'backgroundColor': '#ffffff', 'color': '#0366d6'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    html.Button("Reload Last File", id="reload-btn", n_clicks=0, className="dash-button")
])

modbus_rtu_page = html.Div([
    html.H2("Modbus RTU Connection"),
    html.Div([
        html.Label("COM Port:"),
        dcc.Dropdown(
            id='com-port',
            options=[{'label': port, 'value': port} for port in COM_PORTS],
            placeholder="Select COM Port",
            className="dropdown"
        ),
        html.Label("Baud Rate:"),
        dcc.Dropdown(
            id='baud-rate',
            options=[{'label': rate, 'value': rate} for rate in BAUD_RATES],
            placeholder="Select Baud Rate",
            className="dropdown"
        ),
        html.Label("Function Code:"),
        dcc.Dropdown(
            id='rtu-function-code',
            options=[{'label': key, 'value': value} for key, value in MODBUS_FUNCTIONS.items()],
            placeholder='Select Function Code',
            className="dropdown"
        ),
        html.Label("Starting Point:"),
        dcc.Input(id='rtu-start-point', type='number', placeholder='40000'),
        html.Label("Register Count:"),
        dcc.Input(id='rtu-register-count', type='number', placeholder='10'),
        html.Button("Read Data", id='read-rtu-btn', n_clicks=0, className="dash-button"),
    ]),
    html.Div(id='rtu-output')
])

modbus_tcp_page = html.Div([
    html.H2("Modbus TCP Connection"),
    html.Div([
        html.Label("Host:"),
        dcc.Input(id='tcp-host', type='text', placeholder='192.168.1.1'),
        html.Label("Port:"),
        dcc.Input(id='tcp-port', type='number', placeholder='502'),
        html.Label("Function Code:"),
        dcc.Dropdown(
            id='tcp-function-code',
            options=[{'label': key, 'value': value} for key, value in MODBUS_FUNCTIONS.items()],
            placeholder='Select Function Code',
            className="dropdown"
        ),
        html.Label("Starting Point:"),
        dcc.Input(id='tcp-start-point', type='number', placeholder='40000'),
        html.Label("Register Count:"),
        dcc.Input(id='tcp-register-count', type='number', placeholder='10'),
        html.Button("Read Data", id='read-tcp-btn', n_clicks=0, className="dash-button"),
    ]),
    html.Div(id='tcp-output')
])

# App layout with sidebar and main content
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.H3("Navigation"),
        html.A('Home', href='/', className='sidebar-link'),
        html.A('Modbus RTU', href='/modbus-rtu', className='sidebar-link'),
        html.A('Modbus TCP', href='/modbus-tcp', className='sidebar-link'),
        html.A('CSV Import', href='/csv-import', className='sidebar-link')
    ], className='sidebar'),
    html.Div(id='page-content', className='main-content')
], className='page-content')

# Callback for routing pages
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/modbus-rtu':
        return modbus_rtu_page
    elif pathname == '/modbus-tcp':
        return modbus_tcp_page
    elif pathname == '/csv-import':
        return csv_import_page
    else:
        return home_page

# Callback for storing uploaded data in a file
@app.callback(
    Output('output-data-upload', 'children'),
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('reload-btn', 'n_clicks')]
)
def save_and_display_file(contents, filename, reload_clicks):
    last_file_path = os.path.join(UPLOAD_FOLDER, "last_uploaded_file.csv")
    ctx = callback_context

    # Reload the last file if the button is clicked
    if ctx.triggered and "reload-btn" in ctx.triggered[0]["prop_id"]:
        if os.path.exists(last_file_path):
            df = pd.read_csv(last_file_path)
            return html.Div([
                html.H5("Reloaded Last File:"),
                html.Pre(df.head().to_string(), style={'whiteSpace': 'pre-wrap', 'wordBreak': 'break-word'})
            ])
        else:
            return html.Div(["No previous file to reload."])

    # Handle new file upload
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                df.to_csv(last_file_path, index=False)  # Save the file
            elif 'xls' in filename:
                df = pd.read_excel(io.BytesIO(decoded))
                df.to_csv(last_file_path, index=False)  # Save as CSV for consistency
            else:
                return html.Div(['Unsupported file format.'])
        except Exception as e:
            return html.Div([f"Error processing file: {e}"])
        return html.Div([
            html.H5(f"Uploaded File: {filename}"),
            html.Pre(df.head().to_string(), style={'whiteSpace': 'pre-wrap', 'wordBreak': 'break-word'})
        ])

    return html.Div(['No file uploaded.'])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
