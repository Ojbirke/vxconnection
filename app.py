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

# Modbus RTU page layout
modbus_rtu_page = html.Div([
    html.H2("Modbus RTU Connection"),
    html.Div([
        html.Label("COM Port:"),
        dcc.Dropdown(
            id='com-port',
            options=[{'label': port, 'value': port} for port in COM_PORTS],
            placeholder="Select COM Port"
        ),
        html.Label("Baud Rate:"),
        dcc.Dropdown(
            id='baud-rate',
            options=[{'label': rate, 'value': rate} for rate in BAUD_RATES],
            placeholder="Select Baud Rate"
        ),
        html.Label("Function Code:"),
        dcc.Dropdown(
            id='rtu-function-code',
            options=[{'label': key, 'value': value} for key, value in MODBUS_FUNCTIONS.items()],
            placeholder='Select Function Code'
        ),
        html.Label("Starting Point:"),
        dcc.Input(id='rtu-start-point', type='number', placeholder='40000'),
        html.Label("Register Count:"),
        dcc.Input(id='rtu-register-count', type='number', placeholder='10'),
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
        html.Label("Function Code:"),
        dcc.Dropdown(
            id='tcp-function-code',
            options=[{'label': key, 'value': value} for key, value in MODBUS_FUNCTIONS.items()],
            placeholder='Select Function Code'
        ),
        html.Label("Starting Point:"),
        dcc.Input(id='tcp-start-point', type='number', placeholder='40000'),
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
    else:
        return home_page

# Dynamic starting point update for RTU
@app.callback(
    Output('rtu-start-point', 'value'),
    Input('rtu-function-code', 'value')
)
def update_rtu_starting_point(function_code):
    if function_code == 3:  # Holding Registers
        return 40000
    elif function_code == 4:  # Input Registers
        return 30000
    elif function_code == 1:  # Coils
        return 1
    elif function_code == 2:  # Discrete Inputs
        return 10000
    return 0

# Dynamic starting point update for TCP
@app.callback(
    Output('tcp-start-point', 'value'),
    Input('tcp-function-code', 'value')
)
def update_tcp_starting_point(function_code):
    if function_code == 3:  # Holding Registers
        return 40000
    elif function_code == 4:  # Input Registers
        return 30000
    elif function_code == 1:  # Coils
        return 1
    elif function_code == 2:  # Discrete Inputs
        return 10000
    return 0

# Callback for Modbus RTU data
@app.callback(
    Output('rtu-output', 'children'),
    Input('read-rtu-btn', 'n_clicks'),
    State('com-port', 'value'),
    State('baud-rate', 'value'),
    State('rtu-function-code', 'value'),
    State('rtu-start-point', 'value'),
    State('rtu-register-count', 'value')
)
def read_rtu_data(n_clicks, port, baudrate, function_code, start_point, count):
    if n_clicks > 0:
        try:
            client = ModbusSerialClient(method='rtu', port=port, baudrate=baudrate)
            if client.connect():
                if function_code == 3:
                    result = client.read_holding_registers(start_point - 40001, count)
                elif function_code == 4:
                    result = client.read_input_registers(start_point - 30001, count)
                else:
                    return "Function code not supported for RTU."
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
    State('tcp-function-code', 'value'),
    State('tcp-start-point', 'value'),
    State('tcp-register-count', 'value')
)
def read_tcp_data(n_clicks, host, port, function_code, start_point, count):
    if n_clicks > 0:
        try:
            client = ModbusTcpClient(host, port=port)
            if client.connect():
                if function_code == 3:
                    result = client.read_holding_registers(start_point - 40001, count)
                elif function_code == 4:
                    result = client.read_input_registers(start_point - 30001, count)
                else:
                    return "Function code not supported for TCP."
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
