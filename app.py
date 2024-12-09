import os
from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
from pymodbus.client import ModbusSerialClient, ModbusTcpClient
import io
import base64
from dash import callback_context

# Initialize the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# Create the uploads directory if it doesn't exist
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Layout for the navigation menu
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        dcc.Link('Home', href='/'),
        ' | ',
        dcc.Link('Modbus RTU', href='/modbus-rtu'),
        ' | ',
        dcc.Link('Modbus TCP', href='/modbus-tcp'),
        ' | ',
        dcc.Link('CSV Import', href='/csv-import')
    ]),
    html.Div(id='page-content')
])

# Home page layout
home_page = html.Div([
    html.H1("Welcome to the VX Flowmeter App"),
    html.P("Navigate using the links above to explore different functionalities."),
])

# CSV Import page layout
csv_import_page = html.Div([
    html.H2("CSV File Import"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    html.Button("Reload Last File", id="reload-btn", n_clicks=0)
])

# Modbus RTU page layout
modbus_rtu_page = html.Div([
    html.H2("Modbus RTU Connection"),
    html.Div([
        html.Label("COM Port:"),
        dcc.Input(id='com-port', type='text', placeholder='COM1'),
        html.Label("Baud Rate:"),
        dcc.Input(id='baud-rate', type='number', placeholder='9600'),
        html.Label("Address:"),
        dcc.Input(id='rtu-address', type='number', placeholder='1'),
        html.Label("Register Count:"),
        dcc.Input(id='register-count', type='number', placeholder='10'),
        html.Button("Read Data", id='read-rtu-btn', n_clicks=0),
    ]),
    html.Div(id='rtu-output')
])

# Modbus TCP page layout
modbus_tcp_page = html.Div([
    html.H2("Modbus TCP Connection"),
    html.Div([
        html.Label("Host:"),
        dcc.Input(id='tcp-host', type='text', placeholder='192.168.1.1'),
        html.Label("Port:"),
        dcc.Input(id='tcp-port', type='number', placeholder='502'),
        html.Label("Address:"),
        dcc.Input(id='tcp-address', type='number', placeholder='1'),
        html.Label("Register Count:"),
        dcc.Input(id='tcp-register-count', type='number', placeholder='10'),
        html.Button("Read Data", id='read-tcp-btn', n_clicks=0),
    ]),
    html.Div(id='tcp-output')
])

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
                # Save the uploaded file
                df.to_csv(last_file_path, index=False)
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

# Callback for Modbus RTU data
@app.callback(
    Output('rtu-output', 'children'),
    Input('read-rtu-btn', 'n_clicks'),
    State('com-port', 'value'),
    State('baud-rate', 'value'),
    State('rtu-address', 'value'),
    State('register-count', 'value')
)
def read_rtu_data(n_clicks, port, baudrate, address, count):
    if n_clicks > 0:
        try:
            client = ModbusSerialClient(method='rtu', port=port, baudrate=baudrate)
            if client.connect():
                result = client.read_holding_registers(address, count)
                client.close()
                if result.isError():
                    return f"Error: {result}"
                return f"Data: {result.registers}"
            return "Unable to connect to RTU device."
        except Exception as e:
            return f"Error: {e}"

# Callback for Modbus TCP data
@app.callback(
    Output('tcp-output', 'children'),
    Input('read-tcp-btn', 'n_clicks'),
    State('tcp-host', 'value'),
    State('tcp-port', 'value'),
    State('tcp-address', 'value'),
    State('tcp-register-count', 'value')
)
def read_tcp_data(n_clicks, host, port, address, count):
    if n_clicks > 0:
        try:
            client = ModbusTcpClient(host, port=port)
            if client.connect():
                result = client.read_holding_registers(address, count)
                client.close()
                if result.isError():
                    return f"Error: {result}"
                return f"Data: {result.registers}"
            return "Unable to connect to TCP device."
        except Exception as e:
            return f"Error: {e}"

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
