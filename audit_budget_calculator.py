import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import base64

# Set page config
st.set_page_config(
    page_title="Statutory Audit Budget Calculator",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Statutory Audit Budget Calculator")
st.markdown("Calculate audit budgets based on company size, industry, and risk factors.")

# Create layout with columns for input and results
col1, col2 = st.columns([1, 2])

# Define industry sector definitions and factors
industry_sectors = {
    "MFG": {"name": "Manufacturing", "factor": 1.0},
    "TRD": {"name": "Trading", "factor": 0.9},
    "SER": {"name": "Services", "factor": 0.95},
    "FIN": {"name": "Financial Services", "factor": 1.3},
    "REC": {"name": "Real Estate and Construction", "factor": 1.2},
    "NGO": {"name": "Not for profit", "factor": 0.85}
}

# Detailed time estimates based on size and sector (same as in the original code)
detailed_time_estimates = {
    # Small category
    "SMFG": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "STRD": {"planning": 48, "fieldwork": 240, "managerReview": 48, "partnerReview": 24, "total": 360},
    "SSER": {"planning": 48, "fieldwork": 240, "managerReview": 48, "partnerReview": 24, "total": 360},
    "SREC": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    
    # Medium category
    "MMFG": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    "MTRD": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "MSER": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "MFIN": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    "MREC": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    
    # Large category
    "LMFG": {"planning": 120, "fieldwork": 528, "managerReview": 96, "partnerReview": 96, "total": 840},
    "LTRD": {"planning": 72, "fieldwork": 360, "managerReview": 72, "partnerReview": 96, "total": 600},
    "LSER": {"planning": 72, "fieldwork": 360, "managerReview": 72, "partnerReview": 96, "total": 600},
    "LFIN": {"planning": 120, "fieldwork": 480, "managerReview": 120, "partnerReview": 120, "total": 840},
    "LREC": {"planning": 120, "fieldwork": 480, "managerReview": 120, "partnerReview": 120, "total": 840},
    
    # Very Large category
    "VLMFG": {"planning": 120, "fieldwork": 600, "managerReview": 120, "partnerReview": 120, "total": 960},
    "VLSER": {"planning": 72, "fieldwork": 600, "managerReview": 72, "partnerReview": 96, "total": 840},
    "VLFIN": {"planning": 72, "fieldwork": 600, "managerReview": 144, "partnerReview": 144, "total": 960},
    "VLREC": {"planning": 120, "fieldwork": 600, "managerReview": 120, "partnerReview": 120, "total": 960}
}

# Default time for combinations not specified (using small manufacturing as default)
default_time_estimate = {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480}

# Input form in the left column
with col1:
    st.header("Audit Details")
    
    company_name = st.text_input("Company Name")
    turnover = st.number_input("Turnover (in Rs. Crore)", min_value=0.0, step=10.0)
    is_listed = st.checkbox("Listed Company")
    
    industry_sector = st.selectbox(
        "Industry Sector",
        options=list(industry_sectors.keys()),
        format_func=lambda x: industry_sectors[x]["name"]
    )
    
    # Determine audit category based on turnover
    if turnover <= 50:
        audit_category = "micro"
        audit_category_display = "Micro (≤ Rs. 50 Cr)"
    elif turnover <= 250:
        audit_category = "small"
        audit_category_display = "Small (Rs. 50-250 Cr)"
    elif turnover <= 500:
        audit_category = "medium"
        audit_category_display = "Medium (Rs. 250-500 Cr)"
    elif turnover <= 1000:
        audit_category = "large"
        audit_category_display = "Large (Rs. 500-1000 Cr)"
    else:
        audit_category = "veryLarge"
        audit_category_display = "Very Large (> Rs. 1000 Cr)"
    
    st.info(f"Audit Category: {audit_category_display}")
    
    # Risk factors with expanders
    with st.expander("Risk Factors", expanded=True):
        controls_risk = st.selectbox(
            "Controls Risk",
            options=[1, 2, 3],
            format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
        )
        
        inherent_risk = st.selectbox(
            "Inherent Risk",
            options=[1, 2, 3],
            format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
        )
        
        complexity = st.selectbox(
            "Complexity",
            options=[1, 2, 3],
            format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
        )
        
        info_delay_risk = st.selectbox(
            "Information Delay Risk",
            options=[1, 2, 3],
            format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
        )

# Calculate budget based on inputs
if company_name or turnover > 0:
    # Get the lookup key based on size and sector
    size_prefix = "S" if audit_category in ["micro", "small"] else "M" if audit_category == "medium" else "L" if audit_category == "large" else "VL"
    lookup_key = size_prefix + industry_sector
    
    # Get baseline hours from detailed estimates or fall back to default
    baseline_estimate = detailed_time_estimates.get(lookup_key, default_time_estimate)
    
    # Extract phase hours
    base_planning = baseline_estimate["planning"]
    base_fieldwork = baseline_estimate["fieldwork"]
    base_manager_review = baseline_estimate["managerReview"]
    base_partner_review = baseline_estimate["partnerReview"]
    base_total = baseline_estimate["total"]
    
    # Apply 0.8 scaling factor for Micro category
    if audit_category == "micro":
        base_planning = round(base_planning * 0.8)
        base_fieldwork = round(base_fieldwork * 0.8)
        base_manager_review = round(base_manager_review * 0.8)
        base_partner_review = round(base_partner_review * 0.8)
        base_total = round(base_total * 0.8)
    
    # Risk adjustment multipliers
    controls_risk_factor = 1 if controls_risk == 1 else (1.2 if controls_risk == 2 else 1.4)
    inherent_risk_factor = 1 if inherent_risk == 1 else (1.25 if inherent_risk == 2 else 1.5)
    complexity_factor = 1 if complexity == 1 else (1.3 if complexity == 2 else 1.6)
    info_delay_factor = 1 if info_delay_risk == 1 else (1.15 if info_delay_risk == 2 else 1.3)
    
    # Calculate adjusted phase hours
    adjusted_planning = round(base_planning * controls_risk_factor * inherent_risk_factor)
    adjusted_fieldwork = round(base_fieldwork * controls_risk_factor * inherent_risk_factor * complexity_factor * info_delay_factor)
    adjusted_manager_review = round(base_manager_review * complexity_factor)
    adjusted_partner_review = round(base_partner_review * complexity_factor)
    
    # Set phase hours
    phase_hours = {
        "planning": adjusted_planning,
        "fieldwork": adjusted_fieldwork,
        "managerReview": adjusted_manager_review,
        "partnerReview": adjusted_partner_review
    }
    
    # Calculate total adjusted hours
    total_hours = adjusted_planning + adjusted_fieldwork + adjusted_manager_review + adjusted_partner_review
    total_days = round(total_hours / 8 * 10) / 10  # Round to 1 decimal place
    
    # Staff allocation
    staff_hours = {
        "partner": phase_hours["partnerReview"],
        "manager": phase_hours["managerReview"],
        "qualifiedAssistant": 0,
        "seniorArticle": 0,
        "juniorArticle": 0,
        "eqcr": 0,
    }
    
    # Add planning hours based on audit size
    if audit_category in ["medium", "large", "veryLarge"]:
        # Partner gets 30% of planning hours for larger audits
        staff_hours["partner"] += round(phase_hours["planning"] * 0.3)
        # Manager gets 30% of planning hours for larger audits
        staff_hours["manager"] += round(phase_hours["planning"] * 0.3)
    else:
        # For small and micro, only manager is involved in planning (no partner)
        staff_hours["manager"] += round(phase_hours["planning"] * 0.4)
    
    # Qualified Assistant hours
    if audit_category in ["medium", "large", "veryLarge"]:
        # For larger audits, QA gets 40% of planning
        staff_hours["qualifiedAssistant"] = round(
            phase_hours["planning"] * 0.4 + 
            phase_hours["fieldwork"] * 0.3
        )
    else:
        # For smaller audits, QA gets 60% of planning
        staff_hours["qualifiedAssistant"] = round(
            phase_hours["planning"] * 0.6 + 
            phase_hours["fieldwork"] * 0.3
        )
    
    # Senior Article hours - not allocated for Micro audits
    if audit_category != "micro":
        staff_hours["seniorArticle"] = round(
            phase_hours["planning"] * 0.3 + 
            phase_hours["fieldwork"] * 0.4
        )
    
    # Junior Article hours
    junior_article_count = 2 if audit_category == "veryLarge" else 1
    
    if junior_article_count == 1:
        # Single junior article
        staff_hours["juniorArticle"] = round(phase_hours["fieldwork"] * 0.3)
    else:
        # Two junior articles for very large audits
        staff_hours["juniorArticle"] = round(phase_hours["fieldwork"] * 0.5)
    
    # Add EQCR hours if required
    eqcr_required = is_listed or turnover > 1000
    if eqcr_required:
        staff_hours["eqcr"] = round(staff_hours["partner"] * 0.4)
    
    # Generate risk adjustment notes
    risk_notes = [
        f"Size-Sector Baseline: {lookup_key}{' (scaled to 80% for Micro)' if audit_category == 'micro' else ''}",
        f"Base Hours: Planning: {base_planning}h, Fieldwork: {base_fieldwork}h, Manager Review: {base_manager_review}h, Partner Review: {base_partner_review}h",
        f"Controls Risk: {'Low' if controls_risk == 1 else ('Medium' if controls_risk == 2 else 'High')} (factor: {controls_risk_factor:.2f})",
        f"Inherent Risk: {'Low' if inherent_risk == 1 else ('Medium' if inherent_risk == 2 else 'High')} (factor: {inherent_risk_factor:.2f})",
        f"Complexity: {'Low' if complexity == 1 else ('Medium' if complexity == 2 else 'High')} (factor: {complexity_factor:.2f})",
        f"Information Delay Risk: {'Low' if info_delay_risk == 1 else ('Medium' if info_delay_risk == 2 else 'High')} (factor: {info_delay_factor:.2f})",
        f"Adjusted hours by phase:",
        f"- Planning: {base_planning}h → {phase_hours['planning']}h",
        f"- Fieldwork: {base_fieldwork}h → {phase_hours['fieldwork']}h",
        f"- Manager Review: {base_manager_review}h → {phase_hours['managerReview']}h",
        f"- Partner Review: {base_partner_review}h → {phase_hours['partnerReview']}h",
        f"- Total: {base_total}h → {total_hours}h",
        f"Staff allocation notes:",
        f"- {'Partner and Manager both involved in planning (30% each)' if audit_category in ['medium', 'large', 'veryLarge'] else 'Only Manager involved in planning (no Partner planning hours)'}",
        f"- {'No Senior Article allocated for Micro audits' if audit_category == 'micro' else 'Senior Article involved in planning and fieldwork'}",
        f"- {'Two Junior Articles allocated for Very Large audit with increased fieldwork allocation' if audit_category == 'veryLarge' else 'One Junior Article allocated'}",
    ]
    
    if eqcr_required:
        risk_notes.append("- EQCR required due to listing status or high turnover.")
    
    # Results display in the right column
    with col2:
        st.header("Budget Summary")
        
        # Top summary cards
        summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
        
        with summary_col1:
            st.metric("Total Hours", f"{total_hours}")
        
        with summary_col2:
            st.metric("Total Days", f"{round(total_days)}")
        
        with summary_col3:
            st.metric("Planning", f"{phase_hours['planning']}h")
        
        with summary_col4:
            st.metric("Fieldwork", f"{phase_hours['fieldwork']}h")
        
        with summary_col5:
            st.metric("EQCR Required", "Yes" if eqcr_required else "No")
        
        # Review hours
        review_col1, review_col2 = st.columns(2)
        
        with review_col1:
            st.metric("Manager Review", f"{phase_hours['managerReview']}h")
        
        with review_col2:
            st.metric("Partner Review", f"{phase_hours['partnerReview']}h")
        
        # Staff allocation
        st.subheader("Staff Allocation")
        
        # Create a DataFrame for staff allocation table
        staff_data = []
        for role, hours in staff_hours.items():
            if role == "eqcr" and hours == 0:
                continue
                
            days = round(hours / 8)
            percentage = round(hours / total_hours * 100) if total_hours else 0
            
            # Define notes for each role
            if role == "partner":
                notes = "Partner Review & Discussions + Planning Involvement" if audit_category in ["medium", "large", "veryLarge"] else "Partner Review & Discussions"
            elif role == "manager":
                notes = "Manager Review & Discussions + Planning Involvement"
            elif role == "qualifiedAssistant":
                notes = "Planning & Complex Fieldwork"
            elif role == "seniorArticle":
                notes = "Not allocated for Micro audits" if audit_category == "micro" else "Planning assistance & Standard Fieldwork"
            elif role == "juniorArticle":
                notes = "Two Junior Articles for routine fieldwork" if audit_category == "veryLarge" else "Routine Fieldwork"
            elif role == "eqcr":
                notes = "Required for listed companies or turnover > Rs. 1000 Cr"
            else:
                notes = ""
                
            # Format role name for display
            display_role = {
                "partner": "Partner",
                "manager": "Manager",
                "qualifiedAssistant": "Qualified Assistant",
                "seniorArticle": "Senior Article",
                "juniorArticle": "Junior Article(s)",
                "eqcr": "EQCR"
            }.get(role, role)
            
            staff_data.append({
                "Role": display_role,
                "Hours": hours,
                "Days": days,
                "Percentage": f"{percentage}%",
                "Notes": notes
            })
        
        # Add total row
        staff_data.append({
            "Role": "Total",
            "Hours": total_hours,
            "Days": round(total_days),
            "Percentage": "100%",
            "Notes": ""
        })
        
        # Display staff allocation table
        staff_df = pd.DataFrame(staff_data)
        st.dataframe(staff_df, hide_index=True, use_container_width=True)
        
        # Bar chart visualization
        st.subheader("Staff Hours Visualization")
        
        # Prepare chart data
        chart_data = []
        for role, hours in staff_hours.items():
            if hours > 0:  # Only include roles with allocated hours
                display_role = {
                    "partner": "Partner",
                    "manager": "Manager",
                    "qualifiedAssistant": "Qualified Assistant",
                    "seniorArticle": "Senior Article",
                    "juniorArticle": "Junior Article(s)" if audit_category == "veryLarge" else "Junior Article",
                    "eqcr": "EQCR"
                }.get(role, role)
                
                chart_data.append({"Role": display_role, "Hours": hours})
        
        chart_df = pd.DataFrame(chart_data)
        
        # Create bar chart
        fig = px.bar(
            chart_df, 
            x="Role", 
            y="Hours",
            title="Staff Hours Allocation",
            text="Hours",
            color="Role",
            color_discrete_sequence=px.colors.qualitative.Set1
        )
        
        fig.update_layout(
            xaxis_title="Staff Role",
            yaxis_title="Hours",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk notes
        st.subheader("Risk Adjustment Notes")
        for note in risk_notes:
            st.text(note)
        
        # Export functionality
        st.subheader("Export Options")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            if st.button("Export to CSV"):
                # Create CSV content
                csv_buffer = io.StringIO()
                
                # Write header information
                csv_buffer.write(f"Audit Budget Calculator - {datetime.now().strftime('%Y-%m-%d')}\n")
                csv_buffer.write(f"Company: {company_name}\n")
                csv_buffer.write(f"Turnover: Rs. {turnover} Crore\n")
                csv_buffer.write(f"Industry: {industry_sectors[industry_sector]['name']}\n")
                csv_buffer.write(f"Audit Category: {audit_category_display}\n")
                csv_buffer.write(f"Listed: {'Yes' if is_listed else 'No'}\n\n")
                
                # Write phase hours
                csv_buffer.write("Phase Hours:\n")
                csv_buffer.write(f"Planning,{phase_hours['planning']}\n")
                csv_buffer.write(f"Fieldwork,{phase_hours['fieldwork']}\n")
                csv_buffer.write(f"Manager Review,{phase_hours['managerReview']}\n")
                csv_buffer.write(f"Partner Review,{phase_hours['partnerReview']}\n")
                csv_buffer.write(f"Total Hours,{total_hours}\n\n")
                
                # Write staff allocation
                csv_buffer.write("Staff Allocation:\n")
                csv_buffer.write("Role,Hours,Days,Percentage,Notes\n")
                for row in staff_data:
                    csv_buffer.write(f"{row['Role']},{row['Hours']},{row['Days']},{row['Percentage']},{row['Notes']}\n")
                
                # Write risk notes
                csv_buffer.write("\nRisk Adjustment Notes:\n")
                for note in risk_notes:
                    csv_buffer.write(f"{note}\n")
                
                # Create download link
                csv_string = csv_buffer.getvalue()
                b64 = base64.b64encode(csv_string.encode()).decode()
                filename = f"audit_budget_{company_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.csv"
                href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col_export2:
            if st.button("Export to Excel"):
                # Create Excel content with pandas
                output = io.BytesIO()
                
                # Create a pandas Excel writer using XlsxWriter as the engine
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Create a DataFrame for summary information
                    summary_data = {
                        "Item": [
                            "Company", "Turnover (Rs. Crore)", "Industry", "Audit Category", "Listed", 
                            "Total Hours", "Total Days", "EQCR Required"
                        ],
                        "Value": [
                            company_name, turnover, industry_sectors[industry_sector]["name"], 
                            audit_category_display, "Yes" if is_listed else "No", 
                            total_hours, round(total_days, 1), "Yes" if eqcr_required else "No"
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Create a DataFrame for phase hours
                    phase_data = {
                        "Phase": ["Planning", "Fieldwork", "Manager Review", "Partner Review", "Total"],
                        "Hours": [
                            phase_hours["planning"], phase_hours["fieldwork"], 
                            phase_hours["managerReview"], phase_hours["partnerReview"], 
                            total_hours
                        ]
                    }
                    phase_df = pd.DataFrame(phase_data)
                    phase_df.to_excel(writer, sheet_name='Phase Hours', index=False)
                    
                    # Staff allocation
                    staff_df.to_excel(writer, sheet_name='Staff Allocation', index=False)
                    
                    # Risk notes
                    notes_df = pd.DataFrame({"Risk Notes": risk_notes})
                    notes_df.to_excel(writer, sheet_name='Risk Notes', index=False)
                
                # Create download link
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                filename = f"audit_budget_{company_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
else:
    # Show instructions when no data is entered
    with col2:
        st.info("Please enter company details and risk factors to generate the audit budget.")
        st.markdown("""
        ### How to use this calculator:
        1. Enter the company name and turnover
        2. Specify if the company is listed
        3. Select the industry sector
        4. Adjust risk factors as needed
        5. View the calculated budget and export options
        """)
        
# Footer
st.markdown("---")
st.caption("Statutory Audit Budget Calculator - A tool for audit planning and resource allocation")
