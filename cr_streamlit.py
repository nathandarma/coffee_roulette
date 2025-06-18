import streamlit as st
import pandas as pd
import random

# --- Configuration ---
PASSWORD = "DITRDCSA"
GROUP_SIZE = 3

# --- Helper Functions ---

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
                        past_pairings[p1] = set()
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
    current_group_members = []
    
    # Sort participants based on who has the fewest past partners or who needs new partners most
    # A simple heuristic: prioritize those with fewer past pairings or those who haven't been paired recently
    # For now, a simple random shuffle is a good starting point, and the pairing logic will try to avoid repeats.

    available_participants = list(participants)
    
    # Attempt to form groups by prioritizing new connections
    while len(available_participants) >= group_size:
        group = []
        # Try to pick members for the current group
        # This is a greedy approach and might not find the absolute best solution globally
        
        # Pick the first person from available
        person1 = available_participants.pop(0)
        group.append(person1)

        # Try to find two more people who haven't been paired with person1 recently
        candidates_for_group = []
        for p in available_participants:
            # Check if p has been paired with person1 in the past
            if person1 not in past_pairings or p not in past_pairings[person1]:
                candidates_for_group.append(p)
        
        # If not enough new candidates, just pick from available
        if len(candidates_for_group) < group_size - 1:
            # Fallback: pick any from available
            for _ in range(group_size - 1):
                if available_participants:
                    group.append(available_participants.pop(0))
        else:
            # Prioritize candidates who haven't been paired with person1
            random.shuffle(candidates_for_group)
            for _ in range(group_size - 1):
                if candidates_for_group: # Ensure candidates_for_group is not empty
                    # Find and remove from available_participants
                    p_to_add = candidates_for_group.pop(0)
                    group.append(p_to_add)
                    available_participants.remove(p_to_add)

        groups.append(group)

    # Handle remainders
    if available_participants:
        if len(available_participants) == 1:
            # Add to an existing group, preferably a smaller one if group_size allows growth
            # For simplicity, add to the first existing group. In a real scenario, you'd pick
            # the group that would still try to maintain new pairings or avoid creating huge groups.
            if groups:
                groups[0].extend(available_participants)
            else: # If no groups yet (e.g., only 1 person total), create a group of 1
                groups.append(available_participants)
        elif len(available_participants) == 2:
            groups.append(available_participants) # Form a group of 2
    
    return groups

# --- Streamlit UI ---

st.set_page_config(page_title="Coffee Roulette", layout="centered")

st.title("☕ Coffee Roulette Organizer")

# --- Password Authentication ---
if "password_entered" not in st.session_state:
    st.session_state["password_entered"] = False

if not st.session_state["password_entered"]:
    password_input = st.text_input("Enter Password", type="password")
    if password_input == PASSWORD:
        st.session_state["password_entered"] = True
        st.success("Access Granted!")
        st.rerun() # Rerun to hide password input
    elif password_input: # Only show error if something was typed
        st.error("Incorrect Password. Please try again.")
    st.stop() # Stop execution until password is correct

# --- Main Application Logic ---

st.markdown("""
Welcome to the Coffee Roulette Organizer!
Upload a CSV file with 'Name' and 'Branch' columns to generate random coffee groups.
If your CSV contains 'Group_X' columns from previous rounds, the app will try to create new pairings.
""")

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

df = None
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state['original_df'] = df.copy() # Store original for reset/re-run
        st.success("CSV uploaded successfully!")

        # Validate columns
        if 'Name' not in df.columns or 'Branch' not in df.columns:
            st.error("Error: CSV must contain 'Name' and 'Branch' columns.")
            df = None # Invalidate df if columns are missing
        else:
            st.subheader("Uploaded Data Preview:")
            st.dataframe(df.head())

    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        df = None

else:
    # Option to use mock data if no file is uploaded for demonstration
    st.info("No file uploaded. Using mock data for demonstration purposes.")
    mock_data = {
        'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy', 'Kelly'],
        'Branch': ['HR', 'IT', 'Finance', 'HR', 'IT', 'Finance', 'HR', 'IT', 'Finance', 'HR', 'IT'],
        'Group_1': ['A', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C', 'D', 'D'], # Example past group
        'Group_2': ['X', 'Y', 'Z', 'X', 'Y', 'Z', 'X', 'Y', 'Z', 'X', 'Y'] # Example past group
    }
    df = pd.DataFrame(mock_data)
    st.session_state['original_df'] = df.copy()
    st.subheader("Mock Data Preview:")
    st.dataframe(df.head())


if df is not None and not df.empty:
    if st.button("Generate Coffee Groups"):
        with st.spinner("Generating groups..."):
            participants_df = df[['Name', 'Branch']].copy() # Use only Name and Branch for current grouping

            past_pairings = get_past_pairings(df)
            new_groups = create_groups_intelligently(participants_df, past_pairings, GROUP_SIZE)

            # Assign new group IDs to the DataFrame
            next_group_col = get_next_group_column_name(df)
            
            # Create a mapping from participant name to new group ID
            participant_to_group_id = {}
            group_id_counter = 1
            for group in new_groups:
                for person in group:
                    participant_to_group_id[person] = f"Group {group_id_counter}"
                group_id_counter += 1
            
            # Initialize new column in the original DataFrame
            df[next_group_col] = df['Name'].map(participant_to_group_id)

            st.session_state['grouped_df'] = df.copy() # Store for download
            st.success("Groups created successfully!")

            st.subheader(f"Current Coffee Roulette Groups ({next_group_col}):")
            
            # Visual presentation of groups
            # Using st.expander for a "bubble" like visual effect
            unique_new_groups = df[next_group_col].dropna().unique()
            for group_id in sorted(unique_new_groups):
                group_members_df = df[df[next_group_col] == group_id]
                members = group_members_df['Name'].tolist()
                branches = group_members_df['Branch'].tolist()

                # Using a simple markdown container for visual separation
                st.markdown(
                    f"""
                    <div style="
                        border: 2px solid #6c5ce7;
                        border-radius: 15px;
                        padding: 15px;
                        margin-bottom: 10px;
                        background-color: #f0f0ff;
                        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
                    ">
                        <h4 style="color:#4a418a; margin-top:0px; margin-bottom:10px;">{group_id}</h4>
                        <ul>
                    """,
                    unsafe_allow_html=True
                )
                for i, member in enumerate(members):
                    st.markdown(f"<li>👤 **{member}** (Branch: {branches[i]})</li>", unsafe_allow_html=True)
                st.markdown("</ul></div>", unsafe_allow_html=True)
            
            # Download button
            csv_output = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Grouped CSV",
                data=csv_output,
                file_name=f"coffee_roulette_groups_{next_group_col}.csv",
                mime="text/csv",
            )
else:
    if uploaded_file is None:
        st.info("Upload a CSV or use the provided mock data to generate groups.")
