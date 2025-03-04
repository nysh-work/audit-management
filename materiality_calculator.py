import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import json
import os
import socket
import platform
from datetime import datetime

# Function to check GCP deployment status
def check_gcp_deployment_status():
    """Check if the application is running on Google Cloud Platform and return deployment details."""
    is_gcp = False
    deployment_info = {}
    
    # Check for GCP environment variables
    gcp_env_vars = [
        'GOOGLE_CLOUD_PROJECT', 
        'K_SERVICE', 
        'K_REVISION', 
        'K_CONFIGURATION',
        'CLOUD_RUN_SERVICE'
    ]
    
    for var in gcp_env_vars:
        if os.environ.get(var):
            is_gcp = True
            deployment_info[var] = os.environ.get(var)
    
    # Get additional system information
    deployment_info['hostname'] = socket.gethostname()
    deployment_info['platform'] = platform.platform()
    deployment_info['python_version'] = platform.python_version()
    deployment_info['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return is_gcp, deployment_info

def create_materiality_calculator_dialog():
    """Creates a dialog for the materiality calculator."""
    st.markdown("## Materiality Calculator")
    st.markdown("### Based on SA 320 'Materiality in Planning and Performing an Audit'")
    
    # Add deployment status in sidebar
    with st.sidebar:
        with st.expander("Deployment Status", expanded=False):
            is_gcp, deployment_info = check_gcp_deployment_status()
            
            if is_gcp:
                st.success("✅ Running on Google Cloud Platform")
                
                # Display GCP-specific information
                st.markdown("### GCP Deployment Details")
                for key, value in deployment_info.items():
                    if key in ['GOOGLE_CLOUD_PROJECT', 'K_SERVICE', 'K_REVISION', 'K_CONFIGURATION', 'CLOUD_RUN_SERVICE']:
                        st.markdown(f"**{key}:** {value}")
            else:
                st.warning("⚠️ Running in local/development environment")
            
            # Display general system information
            st.markdown("### System Information")
            st.markdown(f"**Hostname:** {deployment_info['hostname']}")
            st.markdown(f"**Platform:** {deployment_info['platform']}")
            st.markdown(f"**Python Version:** {deployment_info['python_version']}")
            st.markdown(f"**Timestamp:** {deployment_info['timestamp']}")
    
    # Create tabs for the different steps
    mat_tab1, mat_tab2, mat_tab3, mat_tab4, mat_tab5 = st.tabs([
        "Step 1: Risk Assessment", 
        "Step 2: Benchmark Selection", 
        "Step 3: Percentage Determination",
        "Step 4: Documentation",
        "Misstatement Tracker (SA 450)"
    ])
    
    # Initialize session state for materiality calculation if not exists
    if 'materiality_risk_level' not in st.session_state:
        st.session_state.materiality_risk_level = "Medium"
    if 'materiality_entity_type' not in st.session_state:
        st.session_state.materiality_entity_type = "Profit Oriented"
    if 'materiality_benchmark' not in st.session_state:
        st.session_state.materiality_benchmark = "Net Profit before Tax"
    if 'materiality_percentage' not in st.session_state:
        st.session_state.materiality_percentage = 5.0
    if 'materiality_performance_percentage' not in st.session_state:
        st.session_state.materiality_performance_percentage = 75.0
    if 'materiality_clearly_trivial_percentage' not in st.session_state:
        st.session_state.materiality_clearly_trivial_percentage = 5.0
    if 'materiality_financial_data' not in st.session_state:
        st.session_state.materiality_financial_data = {
            'Total Revenue': 0.0,
            'Total Assets': 0.0,
            'Net Profit before Tax': 0.0,
            'Total Expenses': 0.0,
            'Total Equity': 0.0,
            'Gross Profit': 0.0,
            'Net Asset Value': 0.0,
            'Total Cost': 0.0,
            'Net Cost': 0.0
        }
    if 'materiality_risk_factors' not in st.session_state:
        st.session_state.materiality_risk_factors = {}
    if 'materiality_justification' not in st.session_state:
        st.session_state.materiality_justification = ""
    if 'risk_assessment_data' not in st.session_state:
        st.session_state.risk_assessment_data = {}
    
    # Initialize misstatement tracker data if not exists
    if 'known_errors' not in st.session_state:
        st.session_state.known_errors = []
    if 'likely_errors' not in st.session_state:
        st.session_state.likely_errors = []
    
    # Step 1: Risk Assessment
    with mat_tab1:
        st.markdown("### Step 1: Assessing the Risk of Material Misstatements (RoMM)")
        st.markdown("""
        The first consideration in calculating materiality is to assess the risk associated with the business.
        There is an inverse relationship between risk and materiality:
        - Higher risk → Lower materiality
        - Lower risk → Higher materiality
        """)
        
        # Entity information
        st.markdown("#### Entity Information")
        col1, col2 = st.columns(2)
        
        with col1:
            entity_name = st.text_input("Name of Entity", key="entity_name")
            financial_year = st.text_input("Financial Year", key="financial_year")
            materiality_stage = st.selectbox("Materiality Stage", ["Planning", "Execution", "Completion"], key="materiality_stage")
        
        with col2:
            engagement_type = st.selectbox("Type of Engagement", ["Statutory Audit", "Limited Review", "Tax Audit", "Internal Audit"], key="engagement_type")
            prepared_by = st.text_input("Prepared By", key="prepared_by")
            reviewed_by = st.text_input("Reviewed By", key="reviewed_by")
        
        # Display entity information in a table format
        if entity_name or financial_year or materiality_stage or engagement_type:
            entity_data = {
                "Parameter": ["Name of Entity", "Financial Year", "Materiality Stage", "Type of Engagement", "Prepared By", "Reviewed By", "Date"],
                "Value": [
                    entity_name, 
                    financial_year, 
                    materiality_stage, 
                    engagement_type, 
                    prepared_by, 
                    reviewed_by, 
                    datetime.now().strftime("%Y-%m-%d")
                ]
            }
            entity_df = pd.DataFrame(entity_data)
            st.table(entity_df)
        
        # Comprehensive Risk Assessment Matrix
        st.markdown("#### Risk Assessment Matrix")
        
        # Define risk factors with descriptions
        risk_factors = [
            {"id": 1, "factor": "New Engagement", "description": "First year audit engagement"},
            {"id": 2, "factor": "Startup Entity", "description": "Entity in early stages of operation"},
            {"id": 3, "factor": "Significant concerns identified at client acceptance/continuing", "description": "Issues noted during client acceptance procedures"},
            {"id": 4, "factor": "Doubt on integrity of Management", "description": "Concerns about management's honesty or ethical values"},
            {"id": 5, "factor": "Concerns about operating effectiveness of controls", "description": "Weaknesses in internal control environment"},
            {"id": 6, "factor": "Effectiveness of Internal Audit Function", "description": "Inadequate or ineffective internal audit function"},
            {"id": 7, "factor": "Ongoing investigations", "description": "Regulatory or legal investigations in progress"},
            {"id": 8, "factor": "Negative publicity", "description": "Adverse media coverage or public perception"},
            {"id": 9, "factor": "Complexity in operations, organization structure and products", "description": "Complex business model or organizational structure"},
            {"id": 10, "factor": "Significant changes in economic accounting or industry environment", "description": "Major changes affecting the entity's operations"},
            {"id": 11, "factor": "Going-concern and liquidity issues including debt covenants", "description": "Financial stability or liquidity concerns"},
            {"id": 12, "factor": "Operating losses making risk threat of bankruptcy", "description": "History of losses or financial difficulties"},
            {"id": 13, "factor": "Installation of significant new IT systems related to financial reporting", "description": "Recent implementation of financial systems"},
            {"id": 14, "factor": "Prior history of fraud or error", "description": "Previous instances of fraud or significant errors"},
            {"id": 15, "factor": "Increased risk of override of controls, fraud or error", "description": "Factors indicating higher risk of management override"},
            {"id": 16, "factor": "Constraints on the availability of capital and credit", "description": "Difficulties in obtaining financing"},
            {"id": 17, "factor": "Use of complex financing arrangements", "description": "Sophisticated or unusual financing structures"},
            {"id": 18, "factor": "Corporate restructurings", "description": "Recent or planned significant organizational changes"},
            {"id": 19, "factor": "Significant changes in entity from Prior Period", "description": "Major changes in operations, structure, or ownership"},
            {"id": 20, "factor": "Significant transactions with related parties", "description": "Material transactions with related entities or individuals"},
            {"id": 21, "factor": "Changes in key personnel out of key personnel", "description": "Turnover in management or key positions"},
            {"id": 22, "factor": "Weaknesses in internal control/IFCOFR qualified", "description": "Known deficiencies in internal controls"},
            {"id": 23, "factor": "Inefficient accounting systems and records", "description": "Poor record-keeping or accounting processes"},
            {"id": 24, "factor": "Previous year's audit report qualified", "description": "Modified audit opinion in prior year"},
            {"id": 25, "factor": "Changes in accounting policies", "description": "Recent changes in significant accounting policies"},
            {"id": 26, "factor": "Rapid growth or unusual profitability especially compared to that of other companies in the same industry", "description": "Exceptional growth or profitability compared to industry peers"},
            {"id": 27, "factor": "Any other which the auditor may consider significant (Note 1)", "description": "Other risk factors identified by the auditor"}
        ]
        
        # Risk level options and weightage
        risk_levels = {
            "Low_Risk": 1,
            "Medium_Risk": 4,
            "High_Risk": 8
        }
        
        # Display weightage reference table
        st.markdown("#### Risk Level Weightage Reference")
        weightage_data = {
            "Risk Level": ["Low Risk", "Medium Risk", "High Risk"],
            "Weightage": [1, 4, 8],
            "NA": [0, 0, 0],
            "High Risk": [8, 8, 8],
            "Low Risk": [1, 1, 1],
            "Medium Risk": [4, 4, 4]
        }
        weightage_df = pd.DataFrame(weightage_data)
        st.table(weightage_df.iloc[:, :3])  # Display only the first 3 columns
        
        # Initialize risk assessment data if not already in session state
        if not st.session_state.risk_assessment_data:
            for factor in risk_factors:
                st.session_state.risk_assessment_data[factor["id"]] = {
                    "factor": factor["factor"],
                    "level": "Low_Risk",
                    "weightage": risk_levels["Low_Risk"]
                }
        
        # Create a form for the risk assessment
        with st.form("risk_assessment_form"):
            st.markdown("#### Risk Assessment Factors")
            st.markdown("Select the risk level for each factor:")
            
            # Create the risk assessment table with columns
            risk_data = []
            
            for factor in risk_factors:
                factor_id = factor["id"]
                
                # Get current risk level from session state
                current_level = st.session_state.risk_assessment_data.get(factor_id, {}).get("level", "Low_Risk")
                
                # Create selectbox for risk level
                selected_level = st.selectbox(
                    f"{factor_id}. {factor['factor']}",
                    options=["Low_Risk", "Medium_Risk", "High_Risk", "NA"],
                    index=["Low_Risk", "Medium_Risk", "High_Risk", "NA"].index(current_level),
                    key=f"risk_level_{factor_id}",
                    help=factor["description"]
                )
                
                # Calculate weightage
                weightage = 0 if selected_level == "NA" else risk_levels.get(selected_level, 1)
                
                # Add to risk data
                risk_data.append({
                    "S. No.": factor_id,
                    "Particulars": factor["factor"],
                    "Level of Risk": selected_level.replace("_", " "),
                    "Weightage": weightage
                })
                
                # Update session state
                st.session_state.risk_assessment_data[factor_id] = {
                    "factor": factor["factor"],
                    "level": selected_level,
                    "weightage": weightage
                }
            
            # Submit button
            submit_risk = st.form_submit_button("Calculate Overall Risk")
        
        if submit_risk or st.session_state.risk_assessment_data:
            # Create DataFrame for display
            risk_df = pd.DataFrame(risk_data)
            st.dataframe(risk_df)
            
            # Calculate total weightage
            total_weightage = sum(item["weightage"] for item in st.session_state.risk_assessment_data.values())
            max_possible_weightage = len(risk_factors) * risk_levels["High_Risk"]
            risk_percentage = (total_weightage / max_possible_weightage) * 100
            
            # Determine overall risk level
            if risk_percentage < 15:
                overall_risk = "Low RoMM"
            elif risk_percentage < 75:
                overall_risk = "Medium RoMM"
            else:
                overall_risk = "High RoMM"
            
            # Display overall risk assessment
            st.markdown("#### Overall Risk Assessment")
            
            # Create columns for the metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Weightage", f"{total_weightage}")
            
            with col2:
                st.metric("Risk Percentage", f"{risk_percentage:.2f}%")
            
            with col3:
                st.metric("Overall Risk Level", overall_risk)
            
            # Display risk level ranges
            st.markdown("#### Risk Level Ranges")
            risk_ranges = pd.DataFrame({
                "RoMM": ["Low Risk", "Medium Risk", "High Risk"],
                "Between": ["0% - 15%", "15% - 75%", "75% - 100%"]
            })
            st.table(risk_ranges)
            
            # Save the overall risk level to session state
            st.session_state.materiality_risk_level = overall_risk.split()[0]  # Extract just "Low", "Medium", or "High"
            
            # Display summary of risk factors by level
            st.markdown("#### Risk Factors Summary")
            
            # Count factors by risk level
            high_risk_factors = [item["factor"] for item in st.session_state.risk_assessment_data.values() if item["level"] == "High_Risk"]
            medium_risk_factors = [item["factor"] for item in st.session_state.risk_assessment_data.values() if item["level"] == "Medium_Risk"]
            low_risk_factors = [item["factor"] for item in st.session_state.risk_assessment_data.values() if item["level"] == "Low_Risk"]
            
            # Display counts
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("High Risk Factors", len(high_risk_factors))
                if high_risk_factors:
                    st.markdown("**High Risk Factors:**")
                    for factor in high_risk_factors:
                        st.markdown(f"- {factor}")
            
            with col2:
                st.metric("Medium Risk Factors", len(medium_risk_factors))
                if medium_risk_factors:
                    st.markdown("**Medium Risk Factors:**")
                    for factor in medium_risk_factors:
                        st.markdown(f"- {factor}")
            
            with col3:
                st.metric("Low Risk Factors", len(low_risk_factors))
            
            st.markdown("*Note: The final risk level determination should be based on professional judgment.*")
        
        # Export risk assessment
        if st.button("Export Risk Assessment"):
            # Create Excel export
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Create header data
                header_data = {
                    "Parameter": ["Name of Entity", "Financial Year", "Materiality Stage", "Type of Engagement", "Prepared By", "Reviewed By", "Date"],
                    "Value": [entity_name, financial_year, materiality_stage, engagement_type, prepared_by, reviewed_by, datetime.now().strftime("%Y-%m-%d")]
                }
                
                header_df = pd.DataFrame(header_data)
                header_df.to_excel(writer, sheet_name='Risk Assessment', index=False, startrow=0)
                
                # Create risk assessment data
                risk_data = []
                for factor_id, data in st.session_state.risk_assessment_data.items():
                    risk_data.append({
                        "S. No.": factor_id,
                        "Particulars": data["factor"],
                        "Level of Risk (Select from Drop Down)": data["level"].replace("_", " "),
                        "Weightage (Select from table)": data["weightage"]
                    })
                
                risk_assessment_df = pd.DataFrame(risk_data)
                risk_assessment_df.to_excel(writer, sheet_name='Risk Assessment', index=False, startrow=len(header_data["Parameter"]) + 2)
                
                # Add overall assessment
                overall_data = {
                    "Parameter": ["Total Weightage", "Risk Percentage", "Overall Risk Assessment"],
                    "Value": [total_weightage, f"{risk_percentage:.2f}%", overall_risk]
                }
                
                overall_df = pd.DataFrame(overall_data)
                overall_df.to_excel(writer, sheet_name='Risk Assessment', index=False, startrow=len(risk_data) + len(header_data["Parameter"]) + 4)
                
                # Add risk ranges
                risk_ranges.to_excel(writer, sheet_name='Risk Assessment', index=False, startrow=len(risk_data) + len(header_data["Parameter"]) + len(overall_data["Parameter"]) + 6)
                
                # Format the Excel file
                workbook = writer.book
                worksheet = writer.sheets['Risk Assessment']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Apply formats
                for col_num, value in enumerate(header_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Set column widths
                worksheet.set_column('A:A', 10)
                worksheet.set_column('B:B', 50)
                worksheet.set_column('C:D', 15)
            
            # Download link
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="risk_assessment.xlsx">Download Risk Assessment Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    # Step 2: Benchmark Selection
    with mat_tab2:
        st.markdown("### Step 2: Choosing the Appropriate Benchmark")
        st.markdown("""
        Determining Materiality is based on two key aspects:
        1. Relevant benchmarks
        2. Type of entity for which materiality is required
        """)
        
        # Entity type selection
        entity_type = st.selectbox(
            "Select the type of entity:",
            [
                "Profit Oriented", 
                "Not for Profit", 
                "Debt Financed", 
                "Volatility in Profit",
                "Liquidity Issues",
                "Public Utility Project/Program"
            ],
            index=["Profit Oriented", "Not for Profit", "Debt Financed", "Volatility in Profit", "Liquidity Issues", "Public Utility Project/Program"].index(st.session_state.materiality_entity_type)
        )
        
        # Show recommended benchmarks based on entity type
        st.markdown("#### Recommended Benchmarks")
        if entity_type == "Profit Oriented":
            st.info("Recommended benchmark: Net Profit before Tax or normalized profit before tax")
            recommended_benchmarks = ["Net Profit before Tax"]
        elif entity_type == "Not for Profit":
            st.info("Recommended benchmarks: Total Revenue, Total Expenses")
            recommended_benchmarks = ["Total Revenue", "Total Expenses"]
        elif entity_type == "Debt Financed":
            st.info("Recommended benchmark: Net Asset Value")
            recommended_benchmarks = ["Net Asset Value"]
        elif entity_type == "Volatility in Profit":
            st.info("Recommended benchmarks: Total Revenue, Gross Profit")
            recommended_benchmarks = ["Total Revenue", "Gross Profit"]
        elif entity_type == "Liquidity Issues":
            st.info("Recommended benchmark: Total Equity")
            recommended_benchmarks = ["Total Equity"]
        elif entity_type == "Public Utility Project/Program":
            st.info("Recommended benchmarks: Total Cost, Net Cost, Total Assets")
            recommended_benchmarks = ["Total Cost", "Net Cost", "Total Assets"]
        
        # Benchmark selection
        benchmark = st.selectbox(
            "Select the benchmark to use:",
            [
                "Total Revenue", 
                "Total Assets", 
                "Net Profit before Tax", 
                "Total Expenses",
                "Total Equity",
                "Gross Profit",
                "Net Asset Value",
                "Total Cost",
                "Net Cost"
            ],
            index=["Total Revenue", "Total Assets", "Net Profit before Tax", "Total Expenses", "Total Equity", "Gross Profit", "Net Asset Value", "Total Cost", "Net Cost"].index(st.session_state.materiality_benchmark)
        )
        
        # Financial data input
        st.markdown("#### Financial Data")
        st.markdown("Enter the financial data for the selected benchmark:")
        
        # Create columns for better layout
        col1, col2 = st.columns(2)
        
        with col1:
            total_revenue = st.number_input(
                "Total Revenue", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Total Revenue"],
                format="%.2f"
            )
            total_assets = st.number_input(
                "Total Assets", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Total Assets"],
                format="%.2f"
            )
            net_profit = st.number_input(
                "Net Profit before Tax", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Net Profit before Tax"],
                format="%.2f"
            )
            total_expenses = st.number_input(
                "Total Expenses", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Total Expenses"],
                format="%.2f"
            )
            total_equity = st.number_input(
                "Total Equity", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Total Equity"],
                format="%.2f"
            )
        
        with col2:
            gross_profit = st.number_input(
                "Gross Profit", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Gross Profit"],
                format="%.2f"
            )
            net_asset_value = st.number_input(
                "Net Asset Value", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Net Asset Value"],
                format="%.2f"
            )
            total_cost = st.number_input(
                "Total Cost", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Total Cost"],
                format="%.2f"
            )
            net_cost = st.number_input(
                "Net Cost", 
                min_value=0.0, 
                value=st.session_state.materiality_financial_data["Net Cost"],
                format="%.2f"
            )
        
        # Highlight the selected benchmark
        st.markdown(f"**Selected Benchmark: {benchmark}**")
        
        # Save benchmark selection to session state
        if st.button("Save Benchmark Selection"):
            st.session_state.materiality_entity_type = entity_type
            st.session_state.materiality_benchmark = benchmark
            st.session_state.materiality_financial_data = {
                'Total Revenue': total_revenue,
                'Total Assets': total_assets,
                'Net Profit before Tax': net_profit,
                'Total Expenses': total_expenses,
                'Total Equity': total_equity,
                'Gross Profit': gross_profit,
                'Net Asset Value': net_asset_value,
                'Total Cost': total_cost,
                'Net Cost': net_cost
            }
            st.success(f"Benchmark saved as {benchmark}")
    
    # Step 3: Percentage Determination
    with mat_tab3:
        st.markdown("### Step 3: Determining a Percentage of the Benchmark")
        st.markdown("""
        Once the entity type and benchmark are selected, we need to determine the appropriate percentage
        to apply to the benchmark. The percentage varies based on the benchmark and risk level.
        """)
        
        # Display the Materiality Range Matrix
        st.markdown("#### Materiality Range Matrix")
        
        # Create the matrix as a DataFrame
        matrix_data = {
            "Risk Level": ["High RoMM", "Medium RoMM", "Low RoMM"],
            "Liquidity": ["2%<=3.15%", ">3.15%<=3.85%", ">3.85%<=5%"],
            "Profit": ["3%<=4%", ">4%<=5%", ">5%<=7%"],
            "Not for Profit": ["0.5%<=0.7%", ">0.7%<=0.8%", ">0.8%<=1%"],
            "Gross Profit": ["1%<=1.3%", ">1.3%<=1.6%", ">1.6%<=2%"],
            "Total Revenue": ["0.5%<=0.7%", ">0.7%<=0.8%", ">0.8%<=1%"]
        }
        
        matrix_df = pd.DataFrame(matrix_data)
        st.table(matrix_df)
        
        # Determine the appropriate range based on benchmark and risk level
        benchmark_category = ""
        if st.session_state.materiality_benchmark == "Total Revenue":
            benchmark_category = "Total Revenue"
        elif st.session_state.materiality_benchmark == "Net Profit before Tax":
            benchmark_category = "Profit"
        elif st.session_state.materiality_benchmark == "Total Expenses" or st.session_state.materiality_benchmark == "Total Cost" or st.session_state.materiality_benchmark == "Net Cost":
            benchmark_category = "Not for Profit"
        elif st.session_state.materiality_benchmark == "Gross Profit":
            benchmark_category = "Gross Profit"
        elif st.session_state.materiality_benchmark == "Total Equity" or st.session_state.materiality_benchmark == "Net Asset Value":
            benchmark_category = "Liquidity"
        elif st.session_state.materiality_benchmark == "Total Assets":
            benchmark_category = "Liquidity"
        
        # Get the range based on risk level and benchmark category
        risk_index = {"High": 0, "Medium": 1, "Low": 2}[st.session_state.materiality_risk_level]
        
        if benchmark_category in matrix_data:
            range_str = matrix_data[benchmark_category][risk_index]
            st.info(f"Recommended range for {benchmark_category} with {st.session_state.materiality_risk_level} risk: {range_str}")
            
            # Parse the range string to get min and max values
            if "<=" in range_str:
                if range_str.startswith(">"):
                    # Format: >X%<=Y%
                    parts = range_str.replace("%", "").split("<=")
                    min_pct = float(parts[0].replace(">", ""))
                    max_pct = float(parts[1])
                else:
                    # Format: X%<=Y%
                    parts = range_str.replace("%", "").split("<=")
                    min_pct = float(parts[0])
                    max_pct = float(parts[1])
            else:
                # Default range if parsing fails
                min_pct, max_pct = 1.0, 5.0
        else:
            # Default range if benchmark category not in matrix
            st.info("Use professional judgment to determine appropriate percentage")
            min_pct, max_pct = 1.0, 5.0
        
        # Percentage selection
        percentage = st.slider(
            "Select the percentage to apply to the benchmark:",
            min_value=min_pct,
            max_value=max_pct,
            value=min(max(st.session_state.materiality_percentage, min_pct), max_pct),
            step=0.1,
            format="%.1f%%"
        )
        
        # Performance materiality percentage
        st.markdown("#### Performance Materiality")
        st.markdown("""
        Performance materiality is set below overall materiality to reduce the risk of undetected misstatements.
        Typically, this is set between 50% and 90% of overall materiality.
        """)
        
        performance_percentage = st.slider(
            "Select the percentage of overall materiality to use for performance materiality:",
            min_value=50.0,
            max_value=90.0,
            value=st.session_state.materiality_performance_percentage,
            step=5.0,
            format="%.1f%%"
        )
        
        # Clearly trivial threshold
        st.markdown("#### Clearly Trivial Threshold")
        st.markdown("""
        Misstatements below this threshold are considered clearly trivial.
        Typically, this is set at up to 5% of overall materiality.
        """)
        
        clearly_trivial_percentage = st.slider(
            "Select the percentage of overall materiality to use for clearly trivial threshold:",
            min_value=1.0,
            max_value=5.0,
            value=st.session_state.materiality_clearly_trivial_percentage,
            step=0.5,
            format="%.1f%%"
        )
        
        # Calculate materiality values
        benchmark_value = st.session_state.materiality_financial_data[st.session_state.materiality_benchmark]
        overall_materiality = benchmark_value * (percentage / 100)
        performance_materiality = overall_materiality * (performance_percentage / 100)
        clearly_trivial = overall_materiality * (clearly_trivial_percentage / 100)
        
        # Display calculated values
        st.markdown("#### Calculated Materiality Values")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Overall Materiality", f"{overall_materiality:,.2f}")
        
        with col2:
            st.metric("Performance Materiality", f"{performance_materiality:,.2f}")
        
        with col3:
            st.metric("Clearly Trivial Threshold", f"{clearly_trivial:,.2f}")
        
        # Save percentage determination to session state
        if st.button("Save Percentage Determination"):
            st.session_state.materiality_percentage = percentage
            st.session_state.materiality_performance_percentage = performance_percentage
            st.session_state.materiality_clearly_trivial_percentage = clearly_trivial_percentage
            st.success("Percentage determination saved")
    
    # Step 4: Documentation
    with mat_tab4:
        st.markdown("### Step 4: Documenting the Choice with Proper Justification")
        st.markdown("""
        The auditor should document the materiality determination process, including:
        1. Materiality for the financial statements as a whole
        2. Materiality levels for specific classes of transactions, account balances, or disclosures
        3. Performance materiality
        4. Any revisions to the above as the audit progressed
        """)
        
        # Summary of materiality determination
        st.markdown("#### Summary of Materiality Determination")
        
        # Create a summary table
        summary_data = {
            "Parameter": [
                "Risk Level",
                "Entity Type",
                "Selected Benchmark",
                "Benchmark Value",
                "Percentage Applied",
                "Overall Materiality",
                "Performance Materiality",
                "Clearly Trivial Threshold"
            ],
            "Value": [
                st.session_state.materiality_risk_level,
                st.session_state.materiality_entity_type,
                st.session_state.materiality_benchmark,
                f"{st.session_state.materiality_financial_data[st.session_state.materiality_benchmark]:,.2f}",
                f"{st.session_state.materiality_percentage:.1f}%",
                f"{overall_materiality:,.2f}",
                f"{performance_materiality:,.2f}",
                f"{clearly_trivial:,.2f}"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        st.table(summary_df)
        
        # Justification for materiality determination
        st.markdown("#### Justification")
        st.markdown("Provide justification for the materiality determination:")
        
        justification = st.text_area(
            "Justification",
            value=st.session_state.materiality_justification,
            height=150
        )
        
        # Risk factors summary
        st.markdown("#### Risk Factors Considered")
        risk_factors_selected = [factor for factor, selected in st.session_state.materiality_risk_factors.items() if selected]
        
        if risk_factors_selected:
            for factor in risk_factors_selected:
                st.markdown(f"- {factor}")
        else:
            st.markdown("No specific risk factors selected.")
        
        # Save documentation to session state
        if st.button("Save Documentation"):
            st.session_state.materiality_justification = justification
            st.success("Documentation saved")
        
        # Export options
        st.markdown("#### Export Options")
        
        if st.button("Export to Excel"):
            # Create Excel export
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Summary sheet
                summary_df.to_excel(writer, sheet_name='Materiality Summary', index=False)
                
                # Risk factors sheet
                risk_df = pd.DataFrame({
                    "Risk Factor": st.session_state.materiality_risk_factors.keys(),
                    "Selected": [str(selected) for selected in st.session_state.materiality_risk_factors.values()]
                })
                risk_df.to_excel(writer, sheet_name='Risk Factors', index=False)
                
                # Financial data sheet
                financial_df = pd.DataFrame({
                    "Benchmark": st.session_state.materiality_financial_data.keys(),
                    "Value": st.session_state.materiality_financial_data.values()
                })
                financial_df.to_excel(writer, sheet_name='Financial Data', index=False)
                
                # Documentation sheet
                doc_df = pd.DataFrame({
                    "Section": ["Justification"],
                    "Content": [st.session_state.materiality_justification]
                })
                doc_df.to_excel(writer, sheet_name='Documentation', index=False)
                
                # Format the Excel file
                workbook = writer.book
                
                # Add a format for headers
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Apply the header format to all sheets
                for sheet in writer.sheets.values():
                    for col_num, value in enumerate(summary_df.columns.values):
                        sheet.write(0, col_num, value, header_format)
                    sheet.set_column('A:B', 20)
            
            # Download link
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="materiality_calculation.xlsx">Download Excel File</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Excel file generated successfully!")
        
        if st.button("Generate PDF Report"):
            st.info("PDF report generation would be implemented here")
            # This would require additional libraries like ReportLab or WeasyPrint 
    
    # Misstatement Tracker (SA 450)
    with mat_tab5:
        st.markdown("### Evaluation of Material Misstatements Identified during the Audit (SA 450)")
        st.markdown("""
        This tracker helps evaluate misstatements identified during the audit in accordance with SA 450.
        Track both known errors (Para A5) and likely errors (Para 11) to assess their impact on the financial statements.
        """)
        
        # Calculate materiality values for reference
        benchmark_value = st.session_state.materiality_financial_data[st.session_state.materiality_benchmark]
        overall_materiality = benchmark_value * (st.session_state.materiality_percentage / 100)
        performance_materiality = overall_materiality * (st.session_state.materiality_performance_percentage / 100)
        clearly_trivial = overall_materiality * (st.session_state.materiality_clearly_trivial_percentage / 100)
        
        # Display current materiality values for reference
        st.markdown("#### Current Materiality Values")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Materiality", f"{overall_materiality:,.2f}")
        with col2:
            st.metric("Performance Materiality", f"{performance_materiality:,.2f}")
        with col3:
            st.metric("Clearly Trivial Threshold", f"{clearly_trivial:,.2f}")
        
        st.markdown("---")
        
        # Known Errors Section
        st.markdown("#### Known Errors (Para A5 of SA 450)")
        st.markdown("Errors found during the audit")
        
        # Add new known error
        with st.expander("Add New Known Error", expanded=False):
            ke_col1, ke_col2 = st.columns(2)
            
            with ke_col1:
                ke_ledger = st.text_input("Ledger Account", key="ke_ledger")
                ke_description = st.text_area("Description of Error", key="ke_description", height=100)
            
            with ke_col2:
                ke_amount = st.number_input("Amount (in Crores)", key="ke_amount", min_value=0.0, format="%.2f")
                ke_corrected = st.radio("Error Corrected in Books?", ["Yes", "No"], key="ke_corrected")
            
            if st.button("Add Known Error"):
                st.session_state.known_errors.append({
                    "ledger": ke_ledger,
                    "description": ke_description,
                    "amount": ke_amount,
                    "corrected": ke_corrected == "Yes",
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("Known error added successfully!")
                st.experimental_rerun()
        
        # Display known errors table
        if st.session_state.known_errors:
            known_errors_data = []
            for i, error in enumerate(st.session_state.known_errors):
                known_errors_data.append({
                    "ID": i+1,
                    "Ledger Account": error["ledger"],
                    "Description": error["description"],
                    "Amount (Crores)": error["amount"],
                    "Corrected": "Yes" if error["corrected"] else "No",
                    "Uncorrected Amount": 0 if error["corrected"] else error["amount"]
                })
            
            known_errors_df = pd.DataFrame(known_errors_data)
            st.dataframe(known_errors_df)
            
            # Calculate totals
            total_known_errors = sum(error["amount"] for error in st.session_state.known_errors)
            total_uncorrected_known = sum(0 if error["corrected"] else error["amount"] for error in st.session_state.known_errors)
            
            st.markdown(f"**Total Known Errors: {total_known_errors:,.2f} Crores | Uncorrected: {total_uncorrected_known:,.2f} Crores**")
            
            # Option to delete errors
            if st.button("Delete All Known Errors"):
                st.session_state.known_errors = []
                st.success("All known errors deleted!")
                st.experimental_rerun()
        else:
            st.info("No known errors recorded yet.")
            total_known_errors = 0
            total_uncorrected_known = 0
        
        st.markdown("---")
        
        # Likely Errors Section
        st.markdown("#### Likely Errors (Para 11 of SA 450)")
        st.markdown("Errors on review of old balances, reconciliation differences, etc.")
        
        # Add new likely error
        with st.expander("Add New Likely Error", expanded=False):
            le_col1, le_col2 = st.columns(2)
            
            with le_col1:
                le_ledger = st.text_input("Ledger Account", key="le_ledger")
                le_description = st.text_area("Description of Error", key="le_description", height=100)
            
            with le_col2:
                le_amount = st.number_input("Amount (in Crores)", key="le_amount", min_value=0.0, format="%.2f")
                le_corrected = st.radio("Error Corrected in Books?", ["Yes", "No"], key="le_corrected")
            
            if st.button("Add Likely Error"):
                st.session_state.likely_errors.append({
                    "ledger": le_ledger,
                    "description": le_description,
                    "amount": le_amount,
                    "corrected": le_corrected == "Yes",
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("Likely error added successfully!")
                st.experimental_rerun()
        
        # Display likely errors table
        if st.session_state.likely_errors:
            likely_errors_data = []
            for i, error in enumerate(st.session_state.likely_errors):
                likely_errors_data.append({
                    "ID": i+1,
                    "Ledger Account": error["ledger"],
                    "Description": error["description"],
                    "Amount (Crores)": error["amount"],
                    "Corrected": "Yes" if error["corrected"] else "No",
                    "Uncorrected Amount": 0 if error["corrected"] else error["amount"]
                })
            
            likely_errors_df = pd.DataFrame(likely_errors_data)
            st.dataframe(likely_errors_df)
            
            # Calculate totals
            total_likely_errors = sum(error["amount"] for error in st.session_state.likely_errors)
            total_uncorrected_likely = sum(0 if error["corrected"] else error["amount"] for error in st.session_state.likely_errors)
            
            st.markdown(f"**Total Likely Errors: {total_likely_errors:,.2f} Crores | Uncorrected: {total_uncorrected_likely:,.2f} Crores**")
            
            # Option to delete errors
            if st.button("Delete All Likely Errors"):
                st.session_state.likely_errors = []
                st.success("All likely errors deleted!")
                st.experimental_rerun()
        else:
            st.info("No likely errors recorded yet.")
            total_likely_errors = 0
            total_uncorrected_likely = 0
        
        st.markdown("---")
        
        # Summary Section
        st.markdown("#### Summary of Misstatements")
        
        # Create summary table
        summary_data = {
            "Particulars": [
                "Known Errors Para A5 of SA 450 (Errors found during the Audit)",
                "Total Known Errors",
                "Likely Errors Para 11 of SA 450 (Eg.: Errors on review of Old Balances/Reconciliation Differences etc.)",
                "Total Likely Errors",
                "Total Uncorrected Misstatements Known & Likely Misstatements",
                "Materiality Determined",
                "Performance Materiality Determined"
            ],
            "Total Errors": [
                "",
                f"{total_known_errors:,.2f}",
                "",
                f"{total_likely_errors:,.2f}",
                f"{total_uncorrected_known + total_uncorrected_likely:,.2f}",
                f"{overall_materiality:,.2f}",
                f"{performance_materiality:,.2f}"
            ],
            "Errors Corrected in the Books": [
                "",
                f"{total_known_errors - total_uncorrected_known:,.2f}",
                "",
                f"{total_likely_errors - total_uncorrected_likely:,.2f}",
                "",
                "",
                ""
            ],
            "Uncorrected Errors": [
                "",
                f"{total_uncorrected_known:,.2f}",
                "",
                f"{total_uncorrected_likely:,.2f}",
                f"{total_uncorrected_known + total_uncorrected_likely:,.2f}",
                "",
                ""
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        st.table(summary_df)
        
        # Conclusion Section
        st.markdown("#### Conclusion on Adequacy of Audit Scope")
        
        # Calculate percentage of uncorrected misstatements to materiality
        total_uncorrected = total_uncorrected_known + total_uncorrected_likely
        percentage_of_materiality = (total_uncorrected / overall_materiality) * 100 if overall_materiality > 0 else 0
        
        st.markdown(f"Total uncorrected misstatements represent **{percentage_of_materiality:.2f}%** of overall materiality.")
        
        # Provide conclusion guidance based on percentage
        if percentage_of_materiality > 90:
            st.error("⚠️ The total uncorrected misstatements are approaching materiality. The auditor should consider the effect on the audit opinion.")
        elif percentage_of_materiality > 75:
            st.warning("⚠️ The total uncorrected misstatements are significant relative to materiality. The auditor should evaluate their effect carefully.")
        elif percentage_of_materiality > 50:
            st.info("The total uncorrected misstatements are moderate relative to materiality. The auditor should document their consideration of these misstatements.")
        else:
            st.success("The total uncorrected misstatements are well below materiality. They are unlikely to affect the audit opinion.")
        
        conclusion = st.text_area(
            "Conclusion on Adequacy of Audit Scope (The effect of the total uncorrected misstatements must be assessed by the auditor while forming his opinion on the financial statements.)",
            height=100
        )
        
        st.markdown("""
        **Note:** If the auditor concludes the financial statements as a whole are not free from material misstatement, 
        the auditor may modify the opinion.
        """)
        
        # Export options
        st.markdown("#### Export Options")
        
        if st.button("Export Misstatement Evaluation to Excel"):
            # Create Excel export
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Summary sheet
                summary_df.to_excel(writer, sheet_name='Misstatement Summary', index=False)
                
                # Known errors sheet
                if st.session_state.known_errors:
                    known_errors_df = pd.DataFrame(known_errors_data)
                    known_errors_df.to_excel(writer, sheet_name='Known Errors', index=False)
                else:
                    pd.DataFrame({"Note": ["No known errors recorded"]}).to_excel(writer, sheet_name='Known Errors', index=False)
                
                # Likely errors sheet
                if st.session_state.likely_errors:
                    likely_errors_df = pd.DataFrame(likely_errors_data)
                    likely_errors_df.to_excel(writer, sheet_name='Likely Errors', index=False)
                else:
                    pd.DataFrame({"Note": ["No likely errors recorded"]}).to_excel(writer, sheet_name='Likely Errors', index=False)
                
                # Conclusion sheet
                conclusion_df = pd.DataFrame({
                    "Parameter": ["Overall Materiality", "Performance Materiality", "Total Uncorrected Misstatements", 
                                 "Percentage of Materiality", "Conclusion"],
                    "Value": [f"{overall_materiality:,.2f}", f"{performance_materiality:,.2f}", 
                             f"{total_uncorrected:,.2f}", f"{percentage_of_materiality:.2f}%", conclusion]
                })
                conclusion_df.to_excel(writer, sheet_name='Conclusion', index=False)
                
                # Format the Excel file
                workbook = writer.book
                
                # Add a format for headers
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Apply the header format to all sheets
                for sheet in writer.sheets.values():
                    for col_num, value in enumerate(summary_df.columns.values):
                        sheet.write(0, col_num, value, header_format)
                    sheet.set_column('A:D', 20)
            
            # Download link
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="misstatement_evaluation.xlsx">Download Excel File</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Excel file generated successfully!") 