"""General CSV workspace for schemas that do not describe customer deliveries."""
from hashlib import sha256
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from src.csv_workspace import infer_general, filter_general, sample_for_charts, general_bundle, CHART_ROWS
from src.visualizations import style
from src.reporting import safe_csv
from src.ui import header, context_strip

def render_general(selection, page):
    header("CSV Data Analysis")
    with st.expander("Data preparation choices"):
        a,b=st.columns(2)
        decimal=a.selectbox("Decimal mark in numeric text",[".",","],help="This does not remove thousands separators or guess currency.")
        deduplicate=b.checkbox("Remove exact duplicate rows",value=False,
                                help="Default: keep every source row. Repeated records can be valid observations.")
    profile_key=(selection.token,decimal,deduplicate)
    stored=st.session_state.get("_generic_profile")
    if stored is None or stored[0]!=profile_key:
        with st.spinner("Profiling columns and excluding detected contact fields…"):
            dataset=infer_general(selection.raw,decimal,deduplicate)
        st.session_state["_generic_profile"]=(profile_key,dataset)
    dataset=st.session_state["_generic_profile"][1]
    if dataset.frame.empty or not len(dataset.frame.columns):
        st.warning("No non-sensitive values are available for exploration. Check the source schema or choose another file.")
        return
    with st.sidebar:
        with st.expander("Explore filters",expanded=False):
            searchable=st.multiselect("Search within columns",list(dataset.frame.columns),default=list(dataset.frame.columns[:min(3,len(dataset.frame.columns))]),max_selections=5,key="generic_searchcols_"+selection.token[:8])
            search=st.text_input("Find text",help="Literal, case-insensitive search; regular expressions are not executed.")
            category_fields=st.multiselect("Categorical filters",[c for c in dataset.category_columns if dataset.frame[c].nunique()<=300],max_selections=2)
            selections={}
            for field in category_fields:
                choices=sorted(dataset.frame[field].dropna().astype(str).unique())
                selections[field]=st.multiselect(field,choices,key="generic_cat_"+field+"_"+selection.token[:8])
            numeric_fields=st.multiselect("Numeric range filters",dataset.numeric_columns,max_selections=2)
            ranges={}
            for field in numeric_fields:
                values=dataset.frame[field].dropna()
                if len(values) and values.min()!=values.max():
                    a,b=st.columns(2)
                    low=a.number_input(f"{field} minimum",value=float(values.min()),key="lo_"+field+"_"+selection.token[:8])
                    high=b.number_input(f"{field} maximum",value=float(values.max()),key="hi_"+field+"_"+selection.token[:8])
                    if low>high:
                        st.warning(f"{field}: minimum is greater than maximum; no rows will match.")
                    ranges[field]=(low,high)
    filters={"search":search,"search_columns":searchable,"categories":selections,"numeric":ranges}
    selected=filter_general(dataset.frame,search,searchable,selections,ranges)
    context_strip([f"{len(selected):,} / {len(dataset.frame):,} rows",f"{len(selected.columns)} visible columns","Unit: source row","Provenance: user supplied"])
    if page not in {"Overview","Explore Data","Business Insights"}:
        st.info("Delivery-specific analysis is not enabled for this table. Select Delivery analytics above and map verified placement, arrival, promise and status fields. Your general exploration remains available below.")
    a,b,c,d=st.columns(4)
    a.metric("Selected rows",f"{len(selected):,}")
    b.metric("Visible columns",str(len(selected.columns)))
    missing=float(selected.isna().sum().sum()/selected.size) if selected.size else None
    c.metric("Missing cells",f"{missing:.1%}" if missing is not None else "Not available")
    d.metric("Repeated visible rows",f"{int(selected.duplicated().sum()):,}")
    if dataset.hidden_columns:
        st.caption(f"{len(dataset.hidden_columns)} detected contact / location / credential columns are excluded from previews, charts and exports. Review the remaining fields before sharing.")
    if selected.empty:
        st.info("No rows match these filters. Clear the text search or widen the numeric range.")
    preview_tab,quality_tab,chart_tab,export_tab=st.tabs(["Data preview","Quality & schema","Chart studio","Export centre"])
    with preview_tab:
        a,b=st.columns([3,1])
        visible=a.multiselect("Preview columns",list(selected.columns),default=list(selected.columns[:12]),key="visible_"+selection.token[:8])
        rows=b.selectbox("Preview rows",[100,250,1000])
        st.dataframe(selected[visible].head(rows),hide_index=True,width="stretch")
        st.caption("The preview is bounded for responsiveness. Filters and exports use all selected rows.")
    with quality_tab:
        st.dataframe(dataset.profile,hide_index=True,width="stretch")
        st.caption("Column profiles describe the full prepared table. Numeric conversion requires every nonblank value to be finite and valid. Ambiguous dates and mixed numeric text remain text.")
        for action in dataset.actions:
            st.write("• "+action)
        if dataset.hidden_columns:
            with st.expander("Excluded column names"):
                st.write(", ".join(dataset.hidden_columns))
        if dataset.numeric_columns:
            st.subheader("Numeric summary · selected rows")
            st.dataframe(selected[dataset.numeric_columns].describe().T,width="stretch")
    with chart_tab:
        render_chart_studio(selected,dataset,selection.token)
    with export_tab:
        st.write("Download the selected rows with their source, filters, column profile and cleaning notes.")
        export_key=sha256((str(profile_key)+selection.source+json.dumps(filters,sort_keys=True,default=str)).encode()).hexdigest()
        if st.button("Prepare data export",type="primary",disabled=selected.empty):
            with st.spinner("Building your export bundle…"):
                st.session_state["_generic_export"]=(export_key,general_bundle(selected,dataset,selection.source,filters))
        export=st.session_state.get("_generic_export")
        if export and export[0]==export_key:
            st.download_button("Download CSV + report bundle",export[1],"csv_analysis.zip","application/zip")
        st.caption("The ZIP contains selected_data.csv, column_profile.csv, report_context.json and a short guide. Source rows are not assumed to be orders. Text cells are protected against spreadsheet formula injection.")

def render_chart_studio(frame,dataset,token):
    choices=["Category counts"]
    if dataset.numeric_columns:
        choices+=["Numeric distribution","Group comparison"]
    if len(dataset.numeric_columns)>1:
        choices+=["Scatter plot","Numeric correlations"]
    if dataset.numeric_columns and dataset.date_columns:
        choices+=["Time trend"]
    if frame.empty:
        st.info("Choose filters with at least one matching row to build a chart.")
        return
    chart=st.selectbox("Chart type",choices,key="chart_"+token[:8])
    if chart=="Category counts":
        columns=[c for c in frame if c not in dataset.numeric_columns and c not in dataset.date_columns]
        if not columns:
            st.info("No categorical/text column is available. Select a numeric chart instead.")
            return
        field=st.selectbox("Category column",columns)
        n=st.slider("Top groups",5,30,10)
        counts=frame[field].fillna("(Missing)").astype(str).value_counts().head(n).rename_axis(field).reset_index(name="Rows")
        fig=px.bar(counts,x="Rows",y=field,orientation="h",color_discrete_sequence=["#147D92"])
        fig.update_layout(yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(style(fig,f"Most frequent values · {field}"),width="stretch")
        st.caption(f"Top {n} by row count; full selected table, {len(frame):,} rows. Other groups are outside this view.")
    elif chart=="Group comparison":
        category=st.selectbox("Group by",[c for c in frame if c not in dataset.date_columns])
        numeric=st.selectbox("Numeric measure",dataset.numeric_columns)
        operation=st.selectbox("Aggregation",["mean","sum","median","count"])
        grouped_input=pd.DataFrame({"Group":frame[category].astype("string").fillna("(Missing)"),"Value":frame[numeric]})
        groups=grouped_input.groupby("Group")["Value"].agg([operation,"size"])
        groups=groups.sort_values("size",ascending=False).head(15).rename(columns={operation:"Measure","size":"Rows"}).reset_index()
        st.plotly_chart(style(px.bar(groups,x="Group",y="Measure",custom_data=["Rows"],color_discrete_sequence=["#147D92"]),f"{operation.title()} {numeric} by {category}"),width="stretch")
        st.dataframe(groups,hide_index=True,width="stretch")
        st.caption("Top 15 groups by source-row count. Confirm a measure is additive before interpreting a sum.")
    elif chart=="Time trend":
        date=st.selectbox("Date column",dataset.date_columns)
        measure=st.selectbox("Numeric measure",dataset.numeric_columns)
        frequency=st.selectbox("Period",["Month","Week","Day"])
        operation=st.selectbox("Aggregation",["mean","sum","median","count"])
        periods=frame[date].dt.to_period({"Month":"M","Week":"W","Day":"D"}[frequency]).astype("string")
        table=pd.DataFrame({"Period":periods,"Value":frame[measure]}).groupby("Period")["Value"].agg(operation).reset_index()
        st.plotly_chart(style(px.line(table,x="Period",y="Value",markers=True),f"{operation.title()} {measure} over time"),width="stretch")
        st.caption("Uses all selected rows with valid ISO dates. No timezone or day/month ordering is guessed.")
    else:
        sampled=sample_for_charts(frame)
        st.caption(f"Chart population: {len(sampled):,} / {len(frame):,} selected rows. A reproducible seed-21 sample is used above {CHART_ROWS:,} rows.")
        if chart=="Numeric distribution":
            field=st.selectbox("Numeric column",dataset.numeric_columns)
            fig=px.histogram(sampled,x=field,nbins=35,color_discrete_sequence=["#147D92"])
        elif chart=="Scatter plot":
            a,b=st.columns(2)
            x=a.selectbox("Horizontal axis",dataset.numeric_columns)
            y=b.selectbox("Vertical axis",dataset.numeric_columns,index=1)
            points=sampled.head(10000)
            fig=px.scatter(points,x=x,y=y,opacity=.45,color_discrete_sequence=["#147D92"])
            st.caption(f"Showing up to 10,000 points from the chart sample. Relationships are observational.")
        else:
            columns=st.multiselect("Correlation measures",dataset.numeric_columns,default=dataset.numeric_columns[:min(6,len(dataset.numeric_columns))],max_selections=12)
            if len(columns)<2:
                st.info("Choose at least two numeric measures.")
                return
            fig=px.imshow(sampled[columns].corr(),zmin=-1,zmax=1,text_auto=".2f",color_continuous_scale="RdBu")
            st.caption("Pearson correlation, pairwise complete values. IDs/codes are excluded from automatic numeric measures. Correlation does not establish causation.")
        st.plotly_chart(style(fig,chart),width="stretch")
