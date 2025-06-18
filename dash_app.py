import base64
import io
import pandas as pd
import random
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px # Not strictly needed for this app, but common in Dash

# --- Configuration ---
PASSWORD = "DITRDCSA"
GROUP_SIZE = 3

# --- Helper Functions (adapted for Dash/Pandas) ---

def get_next_group_column_name(df):
    """
    Determines the next available group column name (e.g., 'Group_1', 'Group_2').
    """
    existing_group_cols = [col for col in df.columns if col.startswith('Group_') and col[6:].isdigit()]
    if not existing_group_cols:
        return 'Group_1'
    
    # Extract numbers, find max, and increment
    group_numbers = [int(col.split('_')[1]) for col in existing_group_cols]
    next_number = max(group_numbers) + 1
    return f'Group_{next_number}'

def get_past_pairings(df):
    """
    Extracts all past pairings from 'Group_X' columns in the DataFrame.
    Returns a dictionary where keys are person A and values are a set of people
    they've been paired with.
    """
    past_pairings = {}
    group_cols = [col for col in df.columns if col.startswith('Group_') and col[6:].isdigit()]

    if not group_cols:
        return past_pairings

    for col in group_cols:
        # Group by the current group column to get members of each historical group
        grouped_data = df.groupby(col)['Name'].apply(list).to_dict()
        for group_id, members in grouped_data.items():
            if len(members) > 1:
                for i, p1 in enumerate(members):
                    if p1 not in past_pairings:
                        past_pairings[p1].add(p2)
                    for j, p2 in enumerate(members):
                        if i != j:
                            past_pairings[p1].add(p2)
    return past_pairings

def create_groups_intelligently(participants_df, past_pairings, group_size):
    """
    Creates new groups, prioritizing unique pairings based on past_pairings.
    """
    participants = participants_df['Name'].tolist()
    random.shuffle(participants) # Start with a random order

    groups = []
    available_participants = list(participants)
    
    while len(available_participants) >= group_size:
        group = []
        person1 = available_participants.pop(0)
        group.append(person1)

        candidates_for_group = []
        for p in available_participants:
            if person1 not in past_pairings or p not in past_pairings[person1]:
                candidates_for_group.append(p)
        
        if len(candidates_for_group) < group_size - 1:
            for _ in range(group_size - 1):
                if available_participants:
                    group.append(available_participants.pop(0))
        else:
            random.shuffle(candidates_for_group)
            for _ in range(group_size - 1):
                if candidates_for_group:
                    p_to_add = candidates_for_group.pop(0)
                    group.append(p_to_add)
                    available_participants.remove(p_to_add)

        groups.append(group)

    # Handle remainders
    if available_participants:
        if len(available_participants) == 1:
            if groups:
                groups[0].extend(available_participants)
            else:
                groups.append(available_participants)
        elif len(available_participants) == 2:
            groups.append(available_participants)
    
    return groups

# --- Dash Application Setup ---

app = dash.Dash(__name__, external_stylesheets=['https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css']) # Using Tailwind for styling

# Mock Data for initial load
MOCK_DATA = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy', 'Kelly'],
    'Branch': ['HR', 'IT', 'Finance', 'HR', 'IT', 'Finance', 'HR', 'IT', 'Finance', 'HR', 'IT'],
    'Group_1': ['A', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C', 'D', 'D'],
    'Group_2': ['X', 'Y', 'Z', 'X', 'Y', 'Z', 'X', 'Y', 'Z', 'X', 'Y']
}
mock_df = pd.DataFrame(MOCK_DATA)


app.layout = html.Div(className="min-h-screen bg-gray-100 p-8 flex flex-col items-center justify-center font-inter", children=[
    html.H1("☕ Coffee Roulette Organizer", className="text-4xl font-bold text-purple-700 mb-8 text-center"),

    # --- Authentication Panel ---
    html.Div(id='auth-panel', className="bg-white p-6 rounded-lg shadow-md w-full max-w-md", children=[
        html.Label("Enter Password:", className="block text-gray-700 text-sm font-bold mb-2"),
        dcc.Input(
            id='password-input',
            type='password',
            placeholder='Password',
            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline mb-4"
        ),
        html.Button(
            'Authenticate',
            id='password-button',
            n_clicks=0,
            className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:shadow-outline w-full"
        ),
        html.Div(id='password-message', className="text-red-500 text-sm mt-2 text-center")
    ]),

    # --- Main Application Content (Initially hidden) ---
    html.Div(
        id='main-app-content',
        className="hidden w-full max-w-4xl mt-8", # Hidden by default, will be shown on auth
        children=[
            html.P(
                """
                Welcome to the Coffee Roulette Organizer!
                Upload a CSV file with 'Name' and 'Branch' columns to generate random coffee groups.
                If your CSV contains 'Group_X' columns from previous rounds, the app will try to create new pairings.
                """,
                className="text-gray-700 mb-6 text-center"
            ),
            
            # --- File Upload Section ---
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select a CSV File', className="text-purple-600 hover:underline")
                ], className="py-4 border-2 border-dashed border-gray-300 rounded-md text-center text-gray-600 cursor-pointer hover:border-purple-400 hover:text-purple-700"),
                multiple=False,
                className="mb-6 bg-white p-4 rounded-lg shadow-sm"
            ),
            html.Div(id='upload-message', className="text-sm text-gray-600 mb-4 text-center"),

            # --- Data Preview Section ---
            html.Div(id='data-preview-container', className="bg-white p-6 rounded-lg shadow-md mb-6", children=[
                html.H3("Uploaded Data Preview:", className="text-xl font-semibold text-gray-800 mb-4"),
                dash_table.DataTable(
                    id='data-table',
                    columns=[{"name": i, "id": i} for i in mock_df.columns],
                    data=mock_df.to_dict('records'),
                    style_table={'overflowX': 'auto', 'minWidth': '100%'},
                    style_cell={
                        'fontFamily': 'Inter',
                        'textAlign': 'left',
                        'padding': '8px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_header={
                        'backgroundColor': '#f3f4f6',
                        'fontWeight': 'bold',
                        'color': '#4b5563',
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9fafb'
                        }
                    ],
                    page_size=5,
                )
            ]),

            # --- Generate Groups Button ---
            html.Button(
                'Generate Coffee Groups',
                id='generate-groups-button',
                n_clicks=0,
                disabled=True, # Disabled until a valid CSV is uploaded
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:shadow-outline w-full mb-6 transition duration-200 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed"
            ),

            # --- Groups Display Section ---
            html.Div(id='groups-display-container', className="mb-6"),

            # --- Download Button (Initially hidden) ---
            html.Button(
                "Download Grouped CSV",
                id="download-button",
                n_clicks=0,
                className="hidden bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:shadow-outline w-full transition duration-200 ease-in-out",
                # The actual download trigger will be handled by dcc.Download
            ),
            dcc.Download(id="download-csv-data"),

            # --- Hidden dcc.Store components to hold data ---
            dcc.Store(id='uploaded-df-json', data=mock_df.to_json(orient='split')), # Stores the uploaded DataFrame
            dcc.Store(id='grouped-df-json'), # Stores the DataFrame after grouping
            dcc.Store(id='auth-status', data={'authenticated': False}) # Authentication status
        ]
    )
])

# --- Callbacks ---

# Callback for Password Authentication
@app.callback(
    [Output('auth-status', 'data'),
     Output('password-message', 'children'),
     Output('auth-panel', 'className'),
     Output('main-app-content', 'className')],
    [Input('password-button', 'n_clicks')],
    [State('password-input', 'value'),
     State('auth-panel', 'className'),
     State('main-app-content', 'className')]
)
def authenticate_app(n_clicks, password_value, auth_panel_class, main_app_content_class):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Initial load or no button click yet, check initial auth state
        # If no_update is returned when n_clicks is 0, it ensures the initial state is preserved
        return {'authenticated': False}, "", "bg-white p-6 rounded-lg shadow-md w-full max-w-md", "hidden w-full max-w-4xl mt-8"

    if n_clicks > 0:
        if password_value == PASSWORD:
            return {'authenticated': True}, "", "hidden", "w-full max-w-4xl mt-8" # Hide auth, show main
        else:
            return dash.no_update, "Incorrect Password. Please try again.", dash.no_update, dash.no_update
    
    return dash.no_update, "", auth_panel_class, main_app_content_class


# Callback to update UI visibility based on auth status
# This is specifically for when the page reloads and auth_status might be preserved in a session
# but the initial classNames might not reflect it.
@app.callback(
    [Output('auth-panel', 'style'),
     Output('main-app-content', 'style')],
    [Input('auth-status', 'data')]
)
def update_layout_on_auth(auth_status):
    if auth_status and auth_status.get('authenticated'):
        return {'display': 'none'}, {'display': 'block'}
    return {'display': 'block'}, {'display': 'none'}


# Callback for CSV Upload and Validation
@app.callback(
    [Output('data-table', 'data'),
     Output('data-table', 'columns'),
     Output('uploaded-df-json', 'data'),
     Output('upload-message', 'children'),
     Output('generate-groups-button', 'disabled')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_output(contents, filename):
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            else:
                return dash.no_update, dash.no_update, dash.no_update, "Please upload a .csv file.", True

            # Validate columns
            if 'Name' not in df.columns or 'Branch' not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, "Error: CSV must contain 'Name' and 'Branch' columns.", True
            
            # Convert DataFrame to JSON for dcc.Store
            df_json = df.to_json(orient='split')

            # Prepare data for DataTable
            columns = [{"name": i, "id": i} for i in df.columns]
            data = df.to_dict('records')

            return data, columns, df_json, f"'{filename}' uploaded successfully. Ready to generate groups!", False
        except Exception as e:
            print(e)
            return dash.no_update, dash.no_update, dash.no_update, f"There was an error processing this file: {e}", True
    
    # Return mock data if no file uploaded
    columns = [{"name": i, "id": i} for i in mock_df.columns]
    data = mock_df.to_dict('records')
    mock_df_json = mock_df.to_json(orient='split')
    return data, columns, mock_df_json, "No file uploaded. Using mock data.", False


# Callback to Generate Coffee Groups
@app.callback(
    [Output('groups-display-container', 'children'),
     Output('grouped-df-json', 'data'),
     Output('download-button', 'className')],
    [Input('generate-groups-button', 'n_clicks')],
    [State('uploaded-df-json', 'data')]
)
def generate_groups(n_clicks, uploaded_df_json):
    if n_clicks > 0 and uploaded_df_json:
        df = pd.read_json(io.StringIO(uploaded_df_json), orient='split')

        participants_df = df[['Name', 'Branch']].copy()
        past_pairings = get_past_pairings(df)
        new_groups = create_groups_intelligently(participants_df, past_pairings, GROUP_SIZE)

        next_group_col = get_next_group_column_name(df)
        
        participant_to_group_id = {}
        group_id_counter = 1
        for group in new_groups:
            for person in group:
                participant_to_group_id[person] = f"Group {group_id_counter}"
            group_id_counter += 1
        
        df[next_group_col] = df['Name'].map(participant_to_group_id)

        # Store the grouped DataFrame
        grouped_df_json = df.to_json(orient='split')

        # Generate HTML for visual display of groups
        group_html_components = []
        unique_new_groups = df[next_group_col].dropna().unique()
        for group_id in sorted(unique_new_groups):
            group_members_df = df[df[next_group_col] == group_id]
            members_html = []
            for i, member in enumerate(group_members_df['Name'].tolist()):
                branch = group_members_df['Branch'].tolist()[i]
                members_html.append(html.Li(f"👤 {member} (Branch: {branch})", className="text-gray-700"))
            
            group_html_components.append(
                html.Div(
                    className="border-2 border-purple-400 rounded-xl p-4 mb-4 bg-purple-50 shadow-md",
                    children=[
                        html.H4(group_id, className="text-xl font-semibold text-purple-800 mb-2"),
                        html.Ul(members_html, className="list-none p-0")
                    ]
                )
            )
        
        # Make download button visible
        download_button_class = "bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:shadow-outline w-full transition duration-200 ease-in-out"

        return group_html_components, grouped_df_json, download_button_class
    
    return dash.no_update, dash.no_update, "hidden bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:shadow-outline w-full transition duration-200 ease-in-out" # Keep hidden


# Callback to trigger CSV download
@app.callback(
    Output("download-csv-data", "data"),
    Input("download-button", "n_clicks"),
    State("grouped-df-json", "data"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, grouped_df_json):
    if n_clicks > 0 and grouped_df_json:
        df = pd.read_json(io.StringIO(grouped_df_json), orient='split')
        
        # Get the current group column name from the DataFrame
        next_group_col = get_next_group_column_name(df) # This assumes the last group col is the current one
        # A more robust way would be to pass this as a State from the generate_groups callback.
        # For simplicity, we'll assume the helper function correctly identifies the latest one.

        return dcc.send_data_frame(df.to_csv, filename=f"coffee_roulette_groups_{next_group_col}.csv", index=False)
    return dash.no_update

# Important: Expose the Flask server instance for Gunicorn
server = app.server 

if __name__ == '__main__':
    # In production, Gunicorn will handle running the server,
    # so debug=True should be turned off.
    # The host='0.0.0.0' makes it accessible from external IPs in dev,
    # but Gunicorn will manage this in production via $PORT.
    app.run_server(debug=False, host='0.0.0.0', port=8050)
