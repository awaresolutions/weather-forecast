import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from pytz import timezone

# Set the page layout to 'wide' for better use of horizontal space
st.set_page_config(
    page_title="US City Weather Dashboard",
    page_icon="🗺️",
    layout="wide"
)

# --- Configuration for major US cities ---
CITIES = {
    "New York": {"latitude": 40.7128, "longitude": -74.0060},
    "Los Angeles": {"latitude": 34.0522, "longitude": -118.2437},
    "Chicago": {"latitude": 41.8781, "longitude": -87.6298},
    "Houston": {"latitude": 29.7604, "longitude": -95.3698},
    "Phoenix": {"latitude": 33.4484, "longitude": -112.0740},
    "Philadelphia": {"latitude": 39.9526, "longitude": -75.1652},
    "San Antonio": {"latitude": 29.4241, "longitude": -98.4936},
    "San Diego": {"latitude": 32.7157, "longitude": -117.1611},
    "Dallas": {"latitude": 32.7767, "longitude": -96.7970},
    "Austin": {"latitude": 30.2672, "longitude": -97.7431},
}

# --- Function to fetch data from API ---
@st.cache_data
def get_weather_data(latitude, longitude):
    """Fetches hourly temperature data from Open-Meteo API in Fahrenheit."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

# Convert cities dictionary to a DataFrame for plotting
cities_df = pd.DataFrame.from_dict(CITIES, orient='index').reset_index()
cities_df.rename(columns={'index': 'City'}, inplace=True)

# --- Main Streamlit App UI ---
st.title("US City Weather Dashboard 🗺️")
st.markdown("Select a city from the dropdown below to see its hourly temperature trend and location on the map.")

# Initialize session state flags
if 'selected_city_name' not in st.session_state:
    st.session_state.selected_city_name = list(CITIES.keys())[0]  # Default city
if 'data_fetched' not in st.session_state:
    st.session_state.data_fetched = False

# Create the dropdown menu for city selection
selected_city_from_dropdown = st.selectbox(
    "Select a city:",
    options=list(CITIES.keys()),
    index=list(CITIES.keys()).index(st.session_state.selected_city_name),
    key="city_select_box"
)

# Update session state based on dropdown selection
if st.session_state.selected_city_name != selected_city_from_dropdown:
    st.session_state.selected_city_name = selected_city_from_dropdown
    selected_city = CITIES[selected_city_from_dropdown]
    st.session_state.latitude = selected_city["latitude"]
    st.session_state.longitude = selected_city["longitude"]
    st.session_state.data_fetched = True
    st.rerun()

# Get coordinates for the currently selected city (from dropdown)
if st.session_state.data_fetched:
    latitude = st.session_state.latitude
    longitude = st.session_state.longitude
    selected_city_name = st.session_state.selected_city_name
else:
    # Use default city if no interaction has happened yet
    selected_city_name = st.session_state.selected_city_name
    selected_city = CITIES[selected_city_name]
    latitude = selected_city["latitude"]
    longitude = selected_city["longitude"]

# --- Main Layout: Two columns for Map (left) and Weather Data (right) ---
main_col1, main_col2 = st.columns([0.5, 0.5]) # Left half for map, Right half for weather data

with main_col1: # Left column for the map
    st.subheader("Interactive City Map")

    # Highlight the selected city with a different color and larger marker
    cities_df['size'] = [10] * len(cities_df)
    cities_df['color'] = [False] * len(cities_df)
    selected_city_index = cities_df[cities_df['City'] == selected_city_name].index[0]
    cities_df.loc[selected_city_index, 'size'] = 20
    cities_df.loc[selected_city_index, 'color'] = True

    fig_map = px.scatter_mapbox(
        cities_df,
        lat="latitude",
        lon="longitude",
        hover_name="City",
        hover_data={"latitude": True, "longitude": True, "size": False, "color": False},
        color="color",
        color_discrete_map={True: "green", False: "blue"}, # Selected city is green
        size="size",
        zoom=3,
        mapbox_style="carto-positron",
        center={"lat": 39.8283, "lon": -98.5795}
    )
    fig_map.update_layout(
        height=400,
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend=False # Hide the True/False legend
    )

    st.plotly_chart(fig_map, use_container_width=True) # use_container_width here means 100% of main_col1

with main_col2: # Right column for weather data
    st.subheader(f"Weather for: {selected_city_name}")
    st.write(f"**Coordinates:** Latitude {latitude}, Longitude {longitude}")

    st.header("Key Metrics")
    with st.spinner("Fetching weather data..."):
        weather_data = get_weather_data(latitude, longitude)

    if weather_data and "hourly" in weather_data:
        hourly_data = weather_data["hourly"]
        df = pd.DataFrame(hourly_data)
        df["temperature_2m"] = pd.to_numeric(df["temperature_2m"], errors='coerce')
        
        api_timezone_str = weather_data.get("timezone", "UTC") 
        try:
            tz = timezone(api_timezone_str)
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(tz)
            current_time = datetime.now(tz)
        except Exception:
            st.warning("Could not localize timezone, using UTC as a fallback.")
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize('UTC')
            current_time = datetime.now(timezone('UTC'))

        df["Type"] = df["time"].apply(lambda x: "Forecast" if x > current_time else "Historical")

        current_temp_row = df[df["Type"] == "Historical"].iloc[-1] if not df[df["Type"] == "Historical"].empty else df.iloc[0]
        current_temp = current_temp_row["temperature_2m"]
        max_temp = df["temperature_2m"].max()
        min_temp = df["temperature_2m"].min()
        
        metric1, metric2, metric3 = st.columns(3) # Metrics within the right column
        with metric1:
            st.metric("Current Temp", f"{current_temp}°F")
        with metric2:
            st.metric("Max Temp (Forecast)", f"{max_temp}°F")
        with metric3:
            st.metric("Min Temp (Forecast)", f"{min_temp}°F")
    else:
        st.warning("Weather data is not available for this city.")
        
    st.header("Hourly Temperature Trend")
    if weather_data and "hourly" in weather_data:
        # Convert datetime to a millisecond timestamp for Plotly
        current_time_ms = int(current_time.timestamp() * 1000)

        fig = px.line(df, 
                      x="time", 
                      y="temperature_2m",
                      color="Type",
                      color_discrete_map={
                          "Historical": "blue",
                          "Forecast": "red"
                      },
                      labels={"temperature_2m": "Temperature (°F)"},
                      title="Hourly Temperature Over Time (Historical vs. Forecast)")
        
        # Pass the millisecond timestamp to fig.add_vline
        fig.add_vline(x=current_time_ms, line_width=1, line_dash="dash", line_color="green", annotation_text="Current Time", annotation_position="top right")
        
        # Adjust height of the trend chart to fit on one page
        fig.update_layout(height=300) # Reduced height slightly more
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select a city to see the temperature trend.")