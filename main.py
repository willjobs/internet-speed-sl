from datetime import datetime, timedelta

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


def get_summary_stats(df: pd.DataFrame) -> str:
    df = df.set_index('timestamp')
    current_time = df.index.max()

    def calc_stats(start_time):
        data = df.loc[start_time:, 'download']
        return {
            'min': data.min(),
            'median': data.median(),
            'max': data.max()
        }

    hour_stats = calc_stats(current_time - pd.Timedelta(hours=1))
    day_stats = calc_stats(current_time - pd.Timedelta(days=1))
    week_stats = calc_stats(current_time - pd.Timedelta(weeks=1))

    return f"""
    <table>
        <tr><th>Timeframe</th><th>median</th><th>range</th></tr>
        <tr><td>Last 1 hour</td><td>{hour_stats['median']:.1f} Mbps</td><td>{hour_stats['min']:.1f} &ndash; {hour_stats['max']:.1f} Mbps</td></tr>
        <tr><td>Last 1 day</td><td>{day_stats['median']:.1f} Mbps</td><td>{day_stats['min']:.1f} &ndash; {day_stats['max']:.1f} Mbps</td></tr>
        <tr><td>Last 1 week</td><td>{week_stats['median']:.1f} Mbps</td><td>{week_stats['min']:.1f} &ndash; {week_stats['max']:.1f} Mbps</td></tr>
    </table>
    """


def main():
    st.set_page_config(layout="wide")
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            .stPlotlyChart {height: 75vh !important;}
            footer {visibility: hidden;}
            .block-container {
                padding-top: 3rem;
                padding-bottom: 0rem;
                padding-left: 5rem;
                padding-right: 5rem;
            }
            .modebar-container {
                margin-top: 20px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("Chappy Internet Speed")

    file_content = read_file_from_dropbox('/internet_speed/speed_tests.txt')
    if file_content is None:
        return

    df = parse_data(file_content)
    stats_str = f"{get_summary_stats(df)}\n<p>Click the 'Autoscale' button to zoom out to entire date range</p>"
    st.markdown(stats_str, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['download'], mode='lines', name='Download Speed'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upload'], mode='lines', name='Upload Speed'))

    fig.update_layout(
        yaxis_title='Speed (Mbps)',
        hovermode='closest',
        autosize=False,
        margin=dict(l=10, r=10, t=0, b=10),
        legend=dict(
            x=0.2,
            y=0.9,
            orientation="h",
            xanchor="right",
            yanchor="auto",
        ),
    )

    fig.update_traces(
        hovertemplate='<b>Timestamp</b>: %{x}<br><b>Speed</b>: %{y:.2f} Mbps'
    )

    # set the initial zoom to be the past week of data
    end_date = datetime.today()
    start_date = end_date - timedelta(days=7)
    fig.update_xaxes(type="date", range=[start_date, datetime.today().strftime("%Y-%m-%d")])

    # Display the plot
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

if __name__ == "__main__":
    main()
