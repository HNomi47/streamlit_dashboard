import streamlit as st
import pandas as pd
import requests
import time

# --- 1. CONFIGURATION ---

# --- THIS IS THE NEW PART ---
# This line safely reads your secret API key from Streamlit's "Secrets" manager
# We will add this secret in the deployment step.
try:
    VERCEL_API_URL = st.secrets["VERCEL_API_URL"]
except KeyError:
    st.error("ERROR: VERCEL_API_URL secret is not set.")
    st.stop()
# --- END OF NEW PART ---

# Set the page to wide mode
st.set_page_config(layout="wide")
st.title("My Live Crypto Dashboard")

# --- 2. HELPER FUNCTION ---
@st.cache_data(ttl=60) # Cache the coin list for 60s
def get_coin_list():
    """ Fetches data *once* to populate the sidebar. """
    try:
        response = requests.get(VERCEL_API_URL)
        response.raise_for_status()
        data = response.json().get("allCoinsData", [])
        df = pd.DataFrame(data)
        coin_map = dict(zip(df['symbol'], df['name']))
        return coin_map
    except Exception as e:
        st.error(f"Could not fetch initial coin list: {e}")
        return {}

def get_live_data():
    """ Fetches the full, live data package from our API. """
    try:
        response = requests.get(VERCEL_API_URL)
        response.raise_for_status()
        data = response.json().get("allCoinsData", [])
        return {item['symbol']: item for item in data}
    except Exception as e:
        st.sidebar.error("Connection error. Retrying...")
        return None

# --- 3. THE SIDEBAR (Runs once) ---
coin_map = get_coin_list()
if coin_map:
    selected_symbol = st.sidebar.selectbox(
        "Select a Coin",
        options=coin_map.keys(), # e.g., "BTC", "ETH"
        format_func=lambda symbol: f"{coin_map[symbol]} ({symbol})" # e.g., "Bitcoin (BTC)"
    )
else:
    st.error("Could not load app. Cannot connect to API.")
    st.stop()

# --- 4. THE LIVE DASHBOARD (Runs in a loop) ---
placeholder = st.empty()

while True:
    live_data = get_live_data()

    if live_data and selected_symbol in live_data:
        coin = live_data[selected_symbol]

        with placeholder.container():

            # --- Row 1: Price Metric ---
            st.header(f"Live Data for {coin['name']}")
            col1, col2 = st.columns([1, 3])

            with col1:
                st.image(coin['image_url'], width=100)

            with col2:
                price_str = f"${coin['current_price']:,.2f}"
                pct_change = coin.get('_24h_percent_change') 

                if pct_change is not None:
                    delta_str = f"{pct_change:.2f}% (24h)"
                else:
                    delta_str = "N/A"

                st.metric(
                    label="Current Price (USD)",
                    value=price_str,
                    delta=delta_str
                )

            # --- Row 2: 7-Day History Chart ---
            st.header(f"7-Day History for {coin['name']}")

            if coin['historicalData'] and coin['historicalData'][0] is not None:
                history_df = pd.DataFrame(coin['historicalData'])
                history_df['date'] = pd.to_datetime(history_df['date'])
                history_df = history_df.set_index('date')
                st.line_chart(history_df['price'])
            else:
                st.warning("No historical data available for this coin.")

            # --- Row 3: Other Stats ---
            st.header("Market Statistics")

            stat_col1, stat_col2 = st.columns(2)
            with stat_col1:
                market_cap = coin.get('market_cap')
                if market_cap is not None:
                    st.metric("Market Cap", f"${market_cap:,.0f}")
                else:
                    st.metric("Market Cap", "N/A")

            with stat_col2:
                total_volume = coin.get('total_volume')
                if total_volume is not None:
                    st.metric("Total Volume (24h)", f"${total_volume:,.0f}")
                else:
                    st.metric("Total Volume (24h)", "N/A")

    # --- 5. THE REFRESH LOOP ---
    time.sleep(10)
