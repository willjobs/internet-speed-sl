import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import dropbox
from dropbox.exceptions import AuthError


DROPBOX_DIR = "/internet_speed"
DATA_FILE_NAME = "speed_tests.txt"
DROPBOX_DATA_FILE = f"{DROPBOX_DIR}/{DATA_FILE_NAME}"


@st.cache_data(ttl=600, show_spinner="Fetching data")
def read_file_from_dropbox(path):
    try:
        dbx = dropbox.Dropbox(
            app_key=st.secrets["DROPBOX_APP_KEY"],
            app_secret=st.secrets["DROPBOX_APP_SECRET"],
            oauth2_refresh_token=st.secrets["DROPBOX_REFRESH_TOKEN"],
        )

        _, response = dbx.files_download(path)
        return response.content

    except AuthError as e:
        st.error(f"Error authenticating with Dropbox. Please check your access tokens. Error: {e}")
        return None


@st.cache_data(ttl=600, show_spinner="Re-structuring data")
def parse_data(content):
    lines = content.decode('utf-8').split('\n')
    data = []

    for line in lines:
        if line.strip():
            try:
                parts = line.split('|')
                timestamp = pd.to_datetime(parts[0].strip())
                download = float(parts[3].split('=')[1].split('Mbps')[0].strip())
                upload = float(parts[4].split('=')[1].split('Mbps')[0].strip())
                data.append({'timestamp': timestamp, 'download': download, 'upload': upload})

            except Exception:
                pass  # the speed tests file does include some errors in the file, so let's just ignore those

    return pd.DataFrame(data)


def main():
    st.set_page_config(layout="wide")  # Set the page to wide mode
    st.title("Chappy Internet Speed")

    file_content = read_file_from_dropbox('/internet_speed/speed_tests.txt')
    if file_content is None:
        return

    df = parse_data(file_content)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['download'], mode='lines', name='Download Speed'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upload'], mode='lines', name='Upload Speed'))

    fig.update_layout(
        yaxis_title='Speed (Mbps)',
        hovermode='closest',
        height=600,  # Increase the height of the plot
        margin=dict(l=50, r=50, t=50, b=50)  # Adjust margins
    )

    fig.update_traces(
        hovertemplate='<b>Timestamp</b>: %{x}<br><b>Speed</b>: %{y:.2f} Mbps'
    )

    # Display the plot
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
