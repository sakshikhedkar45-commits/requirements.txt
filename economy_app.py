import streamlit as st
import pandas as pd
import pandas_datareader.wb as wb
import plotly.express as px
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Global Economic Dashboard",
    page_icon="🌍",
    layout="wide"
)

# --- Constants ---
# World Bank Indicator Codes
INDICATORS = {
    'NY.GDP.MKTP.CD': 'GDP (Current US$)',
    'FP.CPI.TOTL.ZG': 'Inflation (Annual %)'
}

# --- Data Functions ---

@st.cache_data
def get_country_list():
    """Fetches a list of all countries and their codes from the World Bank."""
    countries = wb.get_countries()
    # Filter out aggregates (like "World", "Arab World") by removing entries with numbers in 'region'
    # Real countries usually have a defined region, aggregates often have 'Aggregates' as region
    countries = countries[countries['region'] != 'Aggregates']
    return countries[['name', 'iso2c']].sort_values('name')

@st.cache_data
def fetch_data(country_codes, start_year, end_year):
    """
    Fetches GDP and Inflation data for specific countries and years.
    Returns a cleaned DataFrame.
    """
    try:
        # Fetch data from World Bank
        df = wb.download(
            indicator=list(INDICATORS.keys()),
            country=country_codes,
            start=start_year,
            end=end_year
        )
        
        # Rename columns for readability
        df = df.rename(columns=INDICATORS)
        
        # Reset index to make 'country' and 'year' regular columns
        df = df.reset_index()
        
        # Convert year to numeric
        df['year'] = pd.to_numeric(df['year'])
        
        # Sort by country and year
        df = df.sort_values(['country', 'year'])
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Interpretation Logic ---
def generate_interpretation(df, country_name, metric_col):
    """Generates a text summary of the latest available data."""
    country_data = df[df['country'] == country_name].sort_values('year')
    
    if country_data.empty:
        return "No data available for interpretation."
    
    # Get latest two years
    latest = country_data.iloc[-1]
    
    summary = f"**{country_name} Analysis:** "
    
    val = latest[metric_col]
    
    if pd.isna(val):
        return f"No recent data available for {metric_col} in {country_name}."

    if metric_col == 'GDP (Current US$)':
        formatted_val = f"${val:,.0f}"
        summary += f"In {latest['year']}, the GDP was {formatted_val}. "
        
        # Compare to previous year if available
        if len(country_data) > 1:
            prev = country_data.iloc[-2]
            prev_val = prev[metric_col]
            if not pd.isna(prev_val) and prev_val != 0:
                growth = ((val - prev_val) / prev_val) * 100
                trend = "grew" if growth > 0 else "contracted"
                summary += f"The economy {trend} by {abs(growth):.2f}% compared to {prev['year']}."
                
    elif metric_col == 'Inflation (Annual %)':
        summary += f"In {latest['year']}, inflation was recorded at {val:.2f}%. "
        
        if val > 10:
            summary += "This indicates very high inflationary pressure, significantly reducing purchasing power."
        elif val > 5:
            summary += "This is considered high inflation."
        elif 1 <= val <= 3:
            summary += "This is generally considered a healthy or stable inflation rate."
        elif val < 0:
            summary += "The economy experienced deflation (falling prices)."
        else:
            summary += "Inflation is relatively low."

    return summary

# --- Main App Layout ---

st.title("🌍 Global Economic Indicators Dashboard")
st.markdown("""
This dashboard fetches live data from the **World Bank API** to visualize GDP and Inflation trends.
Select countries from the sidebar to begin.
""")

# 1. Sidebar Controls
st.sidebar.header("Configuration")

# Fetch countries for dropdown
countries_df = get_country_list()
country_map = dict(zip(countries_df['name'], countries_df['iso2c']))

# Multi-select for countries (Default to US, China, India)
default_countries = ['United States', 'China', 'India']
selected_country_names = st.sidebar.multiselect(
    "Select Countries to Compare",
    options=countries_df['name'],
    default=default_countries
)

# Get ISO codes for selected countries
selected_iso = [country_map[name] for name in selected_country_names]

# Date Slider
current_year = datetime.date.today().year
year_range = st.sidebar.slider("Select Year Range", 1960, current_year, (2000, current_year - 1))

# 2. Fetch Data
if selected_iso:
    with st.spinner('Fetching data from World Bank...'):
        df = fetch_data(selected_iso, year_range[0], year_range[1])

    if not df.empty:
        # Create Tabs
        tab1, tab2, tab3 = st.tabs(["📈 GDP Analysis", "💸 Inflation Analysis", "📄 Raw Data"])

        # --- TAB 1: GDP ---
        with tab1:
            st.subheader("Gross Domestic Product (GDP)")
            
            # Line Chart
            fig_gdp = px.line(
                df, 
                x='year', 
                y='GDP (Current US$)', 
                color='country',
                title='GDP Trends Over Time',
                markers=True,
                template='plotly_white'
            )
            st.plotly_chart(fig_gdp, use_container_width=True)
            
            # Interpretation Section
            st.markdown("### 💡 Interpretations")
            for country in selected_country_names:
                st.info(generate_interpretation(df, country, 'GDP (Current US$)'))

        # --- TAB 2: INFLATION ---
        with tab2:
            st.subheader("Inflation (Consumer Prices)")
            
            # Line Chart
            fig_inf = px.line(
                df, 
                x='year', 
                y='Inflation (Annual %)', 
                color='country',
                title='Inflation Rate Trends',
                markers=True,
                template='plotly_white'
            )
            st.plotly_chart(fig_inf, use_container_width=True)
            
            # Interpretation Section
            st.markdown("### 💡 Interpretations")
            for country in selected_country_names:
                st.warning(generate_interpretation(df, country, 'Inflation (Annual %)'))

        # --- TAB 3: RAW DATA ---
        with tab3:
            st.subheader("Data Table")
            st.dataframe(df.sort_values(by=['country', 'year'], ascending=[True, False]), use_container_width=True)
            
            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Data as CSV",
                csv,
                "economic_data.csv",
                "text/csv",
                key='download-csv'
            )
    else:
        st.error("No data found for the selected parameters.")
else:
    st.info("Please select at least one country in the sidebar.")

# Footer
st.markdown("---")
st.caption("Data Source: World Bank Open Data via `pandas-datareader`.")
