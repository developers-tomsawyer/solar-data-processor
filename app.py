import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(
    page_title="NASA Solar Data Processor",
    layout="wide",
    initial_sidebar_state="auto",
)

st.title("NASA Solar Data Processor")
st.markdown(
    """
    """
)

if 'df_nasa_power' not in st.session_state:
    st.session_state['df_nasa_power'] = None
if 'monthly_avg_per_year_ghi' not in st.session_state:
    st.session_state['monthly_avg_per_year_ghi'] = None
if 'df_txt_data' not in st.session_state:
    st.session_state['df_txt_data'] = None
if 'monthly_sum_all_years_ghi' not in st.session_state:
    st.session_state['monthly_sum_all_years_ghi'] = None
if 'monthly_ghi_per_year_df' not in st.session_state:
    st.session_state['monthly_ghi_per_year_df'] = None
if 'pivot_table_ghi' not in st.session_state:
    st.session_state['pivot_table_ghi'] = None
if 'hgh_avg_ghi_ratio_df' not in st.session_state:
    st.session_state['hgh_avg_ghi_ratio_df'] = None
if 'monthly_ghi_adjusted_df' not in st.session_state:
    st.session_state['monthly_ghi_adjusted_df'] = None
if 'adjusted_ghi_pivot_table' not in st.session_state:
    st.session_state['adjusted_ghi_pivot_table'] = None


st.header("Upload NASA/POWER Hourly Data (CSV)")
nasa_power_uploaded_file = st.file_uploader(
    "Upload your NASA/POWER Hourly CSV file", key="nasa_power_uploader", type=["csv"],
    help="Expected: descriptive header, then data rows starting with 'YEAR,MO,DY,HR...'"
)

if nasa_power_uploaded_file is not None:
    string_data = nasa_power_uploaded_file.getvalue().decode("utf-8")
    lines = string_data.splitlines()

    data_start_row_index = -1
    for i, line in enumerate(lines):
        if "YEAR" in line and "MO" in line and "DY" in line and "HR" in line:
            data_start_row_index = i
            break
            
    if data_start_row_index == -1:
        st.error(
            "NASA/POWER CSV: Could not find the data header (e.g., 'YEAR,MO,DY,HR'). "
            "Please ensure your CSV has this structure."
        )
        st.session_state['df_nasa_power'] = None
        st.session_state['monthly_avg_per_year_ghi'] = None
        st.session_state['monthly_sum_all_years_ghi'] = None
        st.session_state['monthly_ghi_per_year_df'] = None
        st.session_state['pivot_table_ghi'] = None
    else:
        data_string = "\n".join(lines[data_start_row_index:])
        try:
            df = pd.read_csv(io.StringIO(data_string))
            
            allsky_col = None
            for col in df.columns:
                if col.startswith("ALLSKY_SFC_"):
                    allsky_col = col
                    break

            if allsky_col and 'YEAR' in df.columns and 'MO' in df.columns:
                df[allsky_col] = pd.to_numeric(df[allsky_col], errors='coerce')
                
                df["GHI"] = df[allsky_col] / 1000
                
                df.dropna(subset=['YEAR', 'MO', 'GHI'], inplace=True) 

                if df.empty:
                    st.warning("NASA/POWER CSV: After processing and cleaning, no valid data rows remain for calculation.")
                    st.session_state['df_nasa_power'] = None
                    st.session_state['monthly_avg_per_year_ghi'] = None
                    st.session_state['monthly_sum_all_years_ghi'] = None
                    st.session_state['monthly_ghi_per_year_df'] = None
                    st.session_state['pivot_table_ghi'] = None
                else:
                    st.success("NASA/POWER CSV loaded and GHI column created. Displaying aggregations:")
                    st.dataframe(df.head())

                    st.write("---")
                    st.subheader("1. Monthly GHI Aggregations (Across All Years)")
                    
                    total_years = df['YEAR'].nunique()
                    st.info(f"Total number of years in the dataset: **{total_years}**")

                    monthly_sum_all_years_ghi = df.groupby('MO')['GHI'].sum().reset_index()
                    monthly_sum_all_years_ghi.rename(columns={'GHI': 'Total GHI Across All Years (kW/m^2)'}, inplace=True)
                    st.dataframe(monthly_sum_all_years_ghi)
                    st.session_state['monthly_sum_all_years_ghi'] = monthly_sum_all_years_ghi

                    if total_years > 0:
                        monthly_avg_per_year_ghi = monthly_sum_all_years_ghi.copy()
                        monthly_avg_per_year_ghi['Average GHI Per Month (kW/m^2/year)'] = monthly_sum_all_years_ghi['Total GHI Across All Years (kW/m^2)'] / total_years
                        monthly_avg_per_year_ghi = monthly_avg_per_year_ghi[['MO', 'Average GHI Per Month (kW/m^2/year)']]
                        monthly_avg_per_year_ghi.rename(columns={'MO': 'Month'}, inplace=True)
                        st.subheader("2. Average GHI for Each Month (Per Year)")
                        st.dataframe(monthly_avg_per_year_ghi)
                        st.session_state['monthly_avg_per_year_ghi'] = monthly_avg_per_year_ghi
                    else:
                        st.warning("No valid years found to calculate monthly average GHI.")
                        st.session_state['monthly_avg_per_year_ghi'] = None
                    
                    st.write("---")
                    st.subheader("3. Total GHI for Each Month within Each Year (Long Format)")
                    monthly_ghi_per_year_df = df.groupby(['YEAR', 'MO'])['GHI'].sum().reset_index()
                    monthly_ghi_per_year_df.columns = ['Year', 'Month', 'Total GHI (kW/m^2)']
                    st.dataframe(monthly_ghi_per_year_df)
                    st.session_state['monthly_ghi_per_year_df'] = monthly_ghi_per_year_df

                    st.subheader("4. Total GHI (kW/m^2) by Month and Year (Pivot Table View)")
                    pivot_table_ghi = monthly_ghi_per_year_df.pivot_table(index='Month', columns='Year', values='Total GHI (kW/m^2)', aggfunc='sum')
                    pivot_table_ghi.columns.name = None
                    pivot_table_ghi.index.name = None
                    st.dataframe(pivot_table_ghi)
                    st.session_state['pivot_table_ghi'] = pivot_table_ghi

                    st.session_state['df_nasa_power'] = df
            else:
                missing_cols = []
                if not allsky_col: missing_cols.append("ALLSKY_SFC_...")
                if 'YEAR' not in df.columns: missing_cols.append("YEAR")
                if 'MO' not in df.columns: missing_cols.append("MO")
                st.warning(
                    f"NASA/POWER CSV: Missing required columns: {', '.join(missing_cols)}. "
                    "Cannot calculate GHI and monthly averages."
                )
                st.session_state['df_nasa_power'] = None
                st.session_state['monthly_avg_per_year_ghi'] = None
                st.session_state['monthly_sum_all_years_ghi'] = None
                st.session_state['monthly_ghi_per_year_df'] = None
                st.session_state['pivot_table_ghi'] = None
        except Exception as e:
            st.error(f"NASA/POWER CSV: Error reading or processing data: {e}")
            st.session_state['df_nasa_power'] = None
            st.session_state['monthly_avg_per_year_ghi'] = None
            st.session_state['monthly_sum_all_years_ghi'] = None
            st.session_state['monthly_ghi_per_year_df'] = None
            st.session_state['pivot_table_ghi'] = None
else:
    st.info("Please upload your NASA/POWER Hourly CSV file.")
    st.session_state['df_nasa_power'] = None
    st.session_state['monthly_avg_per_year_ghi'] = None
    st.session_state['monthly_sum_all_years_ghi'] = None
    st.session_state['monthly_ghi_per_year_df'] = None
    st.session_state['pivot_table_ghi'] = None


st.write("---")

st.header("Upload Monthly Aggregated Data (TXT/CSV)")
txt_uploaded_file = st.file_uploader(
    "Upload your monthly H_Gh data (TXT/CSV file)", key="txt_uploader", type=["txt", "csv"],
    help="Expected: text file with a table starting 'Month H_Gh H_Bn...' and a 'Year' total row at the end."
)

if txt_uploaded_file is not None:
    file_contents = None
    try:
        file_contents = txt_uploaded_file.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        file_contents = txt_uploaded_file.getvalue().decode("latin-1")
    except Exception as e:
        st.error(f"TXT file: An unexpected error occurred during file decoding: {e}")
        st.session_state['df_txt_data'] = None
        st.stop()
    
    table_start_marker = "Month"
    table_end_marker_pattern = r"^\s*Year\s"
    
    lines = file_contents.splitlines()
    table_lines = []
    in_table = False
    
    for line in lines:
        if line.strip().startswith(table_start_marker):
            in_table = True
            table_lines.append(line)
        elif in_table:
            if re.match(table_end_marker_pattern, line):
                break
            elif line.strip():
                table_lines.append(line)
    
    if not table_lines or len(table_lines) <= 1:
        st.error("TXT file: Could not find the expected monthly data table (starting with 'Month H_Gh...') or table is empty.")
        st.session_state['df_txt_data'] = None
    else:
        try:
            table_string = "\n".join(table_lines)
            df_txt = pd.read_csv(io.StringIO(table_string), delim_whitespace=True)
            
            df_txt_hgh = df_txt[['Month', 'H_Gh']].copy()
            
            month_mapping = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            df_txt_hgh['Month'] = df_txt_hgh['Month'].map(month_mapping)
            
            df_txt_hgh.dropna(subset=['Month', 'H_Gh'], inplace=True)
            df_txt_hgh['Month'] = df_txt_hgh['Month'].astype(int)
            df_txt_hgh['H_Gh'] = pd.to_numeric(df_txt_hgh['H_Gh'], errors='coerce')

            st.success("Monthly H_Gh data from TXT file processed.")
            st.dataframe(df_txt_hgh)
            st.session_state['df_txt_data'] = df_txt_hgh
        except Exception as e:
            st.error(f"TXT file: Error reading or processing data from extracted table: {e}")
            st.session_state['df_txt_data'] = None
else:
    st.info("Please upload your monthly H_Gh data (TXT/CSV file).")
    st.session_state['df_txt_data'] = None

st.write("---")

st.header("Calculations")

if st.session_state['monthly_avg_per_year_ghi'] is not None and not st.session_state['monthly_avg_per_year_ghi'].empty and \
   st.session_state['df_txt_data'] is not None and not st.session_state['df_txt_data'].empty:
    st.subheader("H_Gh from TXT / Average GHI from NASA/POWER CSV")
    
    hgh_avg_ghi_ratio_df = pd.merge(
        st.session_state['df_txt_data'],
        st.session_state['monthly_avg_per_year_ghi'],
        on='Month',
        how='inner'
    )
    
    hgh_avg_ghi_ratio_df['H_Gh / Avg GHI Ratio'] = hgh_avg_ghi_ratio_df['H_Gh'] / hgh_avg_ghi_ratio_df['Average GHI Per Month (kW/m^2/year)']
    hgh_avg_ghi_ratio_df['H_Gh / Avg GHI Ratio'].replace([float('inf'), -float('inf')], pd.NA, inplace=True)
    
    st.dataframe(hgh_avg_ghi_ratio_df.sort_values(by='Month'))
    st.session_state['hgh_avg_ghi_ratio_df'] = hgh_avg_ghi_ratio_df
    

    st.write("---")
    st.subheader("Result: Adjusted Monthly GHI (Total GHI (Month & Year) * H_Gh / Avg GHI Ratio)")

    if st.session_state['monthly_ghi_per_year_df'] is not None and not st.session_state['monthly_ghi_per_year_df'].empty and \
       st.session_state['hgh_avg_ghi_ratio_df'] is not None and not st.session_state['hgh_avg_ghi_ratio_df'].empty:
        
        monthly_ghi_for_merge = st.session_state['monthly_ghi_per_year_df'][['Year', 'Month', 'Total GHI (kW/m^2)']]
        ratio_for_merge = st.session_state['hgh_avg_ghi_ratio_df'][['Month', 'H_Gh / Avg GHI Ratio']]

        monthly_ghi_adjusted_df = pd.merge(
            monthly_ghi_for_merge,
            ratio_for_merge,
            on='Month',
            how='inner'
        )
        
        monthly_ghi_adjusted_df['Adjusted GHI (kW/m^2)'] = monthly_ghi_adjusted_df['Total GHI (kW/m^2)'] * \
                                                             monthly_ghi_adjusted_df['H_Gh / Avg GHI Ratio']
        
        st.session_state['monthly_ghi_adjusted_df'] = monthly_ghi_adjusted_df

        adjusted_ghi_pivot_table = monthly_ghi_adjusted_df.pivot_table(
            index='Month', 
            columns='Year', 
            values='Adjusted GHI (kW/m^2)', 
            aggfunc='sum'
        )
        adjusted_ghi_pivot_table.columns.name = None
        adjusted_ghi_pivot_table.index.name = None
        st.dataframe(adjusted_ghi_pivot_table)
        st.session_state['adjusted_ghi_pivot_table'] = adjusted_ghi_pivot_table

    else:
        st.warning("Cannot perform the multiplication: Either 'Total GHI for Each Month within Each Year' or 'H_Gh / Avg GHI Ratio' data is not available.")
    
else:
    st.warning("Please upload and process both the NASA/POWER CSV and the Monthly Aggregated TXT/CSV files to perform calculations.")

st.write("---")

st.header("Download Processed Data & Results")

@st.cache_data
def convert_df_to_csv(dataframe, include_index=False):
    return dataframe.to_csv(index=include_index).encode('utf-8')

