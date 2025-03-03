import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import json
from datetime import datetime

def create_materiality_calculator_dialog():
    """Creates a dialog for the materiality calculator."""
    st.markdown("## Materiality Calculator")
    st.markdown("### Based on ISA 320 'Materiality in Planning and Performing an Audit'")
    
    # Create tabs for the different steps
    mat_tab1, mat_tab2, mat_tab3, mat_tab4, mat_tab5 = st.tabs([
        "Step 1: Risk Assessment", 
        "Step 2: Benchmark Selection", 
        "Step 3: Percentage Determination",
        "Step 4: Documentation",
        "Misstatement Tracker (ISA 450)"
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
        
        # Risk level selection
        risk_level = st.radio(
            "Select the overall risk level for this engagement:",
            ["Low", "Medium", "High"],
            index=["Low", "Medium", "High"].index(st.session_state.materiality_risk_level)
        )
        
        # Risk factors assessment
        st.markdown("#### Risk Assessment Factors")
        st.markdown("Select all factors that apply to this engagement:")
        
        risk_factors = {
            "New Engagement": st.checkbox("New Engagement", key="rf_new_engagement"),
            "Startup Entity": st.checkbox("Startup Entity", key="rf_startup"),
            "Concerns about integrity of management": st.checkbox("Concerns about integrity of management", key="rf_integrity"),
            "Concerns about operating effectiveness of controls": st.checkbox("Concerns about operating effectiveness of controls", key="rf_controls"),
            "Ongoing investigations": st.checkbox("Ongoing investigations", key="rf_investigations"),
            "Negative publicity": st.checkbox("Negative publicity", key="rf_publicity"),
            "Complexity in operations": st.checkbox("Complexity in operations", key="rf_complexity"),
            "Going-concern and liquidity issues": st.checkbox("Going-concern and liquidity issues", key="rf_liquidity"),
            "Operating losses": st.checkbox("Operating losses", key="rf_losses"),
            "Prior history of fraud or error": st.checkbox("Prior history of fraud or error", key="rf_fraud"),
            "Significant transactions with related parties": st.checkbox("Significant transactions with related parties", key="rf_related_parties"),
            "Changes in key personnel": st.checkbox("Changes in key personnel", key="rf_personnel"),
            "Weaknesses in internal control": st.checkbox("Weaknesses in internal control", key="rf_internal_control"),
            "Previous year's audit report qualified": st.checkbox("Previous year's audit report qualified", key="rf_qualified"),
            "Changes in accounting policies": st.checkbox("Changes in accounting policies", key="rf_accounting_policies")
        }
        
        # Count selected risk factors
        selected_risk_factors = sum(1 for factor, selected in risk_factors.items() if selected)
        
        # Suggest risk level based on factors
        suggested_risk_level = "Low"
        if selected_risk_factors >= 10:
            suggested_risk_level = "High"
        elif selected_risk_factors >= 5:
            suggested_risk_level = "Medium"
            
        st.markdown(f"**Suggested Risk Level based on factors: {suggested_risk_level}**")
        st.markdown("*Note: The final risk level determination should be based on professional judgment.*")
        
        # Save risk assessment to session state
        if st.button("Save Risk Assessment"):
            st.session_state.materiality_risk_level = risk_level
            st.session_state.materiality_risk_factors = risk_factors
            st.success(f"Risk level saved as {risk_level}")
    
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
    
    # Misstatement Tracker (ISA 450)
    with mat_tab5:
        st.markdown("### Evaluation of Material Misstatements Identified during the Audit (ISA 450)")
        st.markdown("""
        This tracker helps evaluate misstatements identified during the audit in accordance with ISA 450.
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
        st.markdown("#### Known Errors (Para A5 of ISA 450)")
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
        st.markdown("#### Likely Errors (Para 11 of ISA 450)")
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
                "Known Errors Para A5 of ISA 450 (Errors found during the Audit)",
                "Total Known Errors",
                "Likely Errors Para 11 of ISA 450 (Eg.: Errors on review of Old Balances/Reconciliation Differences etc.)",
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