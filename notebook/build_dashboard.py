"""
Build the project's dashboard as a self-contained HTML file, plus static PNG
screenshots for the README.

Power BI Desktop is Windows-only and unavailable on this machine (macOS), so
this dashboard is built with Plotly instead. It covers the same three views
originally planned for Power BI: a county choropleth, a national price trend,
and a per-county drill-down.

County boundary source: click_that_hood (codeforgermany), which splits some
counties into city/county sub-areas (e.g. "Cork City" / "Cork County"). Those
are dissolved back into the 26 traditional counties used by the Property
Price Register so they match our data.
"""

import json

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RAW_GEOJSON = "data/geo/ireland-counties-raw.geojson"
CLEAN_GEOJSON = "data/geo/ireland_counties_26.geojson"
SUMMARY_CSV = "data/clean/county_year_summary.csv"
DASHBOARD_HTML = "dashboard/dashboard.html"

# Maps click_that_hood's 34 sub-areas onto the 26 traditional Irish counties
# used in the Property Price Register.
COUNTY_MAP = {
    "Limerick City": "Limerick", "Limerick County": "Limerick",
    "North Tipperary": "Tipperary", "South Tipperary": "Tipperary",
    "Waterford City": "Waterford", "Waterford County": "Waterford",
    "Galway City": "Galway", "Galway County": "Galway",
    "Leitrim County": "Leitrim",
    "Mayo County": "Mayo",
    "Roscommon County": "Roscommon",
    "Sligo County": "Sligo",
    "Cavan County": "Cavan",
    "Donegal County": "Donegal",
    "Monaghan County": "Monaghan",
    "Carlow County": "Carlow",
    "Dublin City": "Dublin", "South Dublin": "Dublin",
    "Fingal": "Dublin", "Dún Laoghaire-Rathdown": "Dublin",
    "Kildare County": "Kildare",
    "Kilkenny County": "Kilkenny",
    "Laois County": "Laois",
    "Longford County": "Longford",
    "Louth County": "Louth",
    "Meath County": "Meath",
    "Offaly County": "Offaly",
    "Westmeath County": "Westmeath",
    "Wexford County": "Wexford",
    "Wicklow County": "Wicklow",
    "Clare County": "Clare",
    "Cork City": "Cork", "Cork County": "Cork",
    "Kerry County": "Kerry",
}


def build_county_geojson() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(RAW_GEOJSON)
    gdf["county"] = gdf["name"].map(COUNTY_MAP)
    if gdf["county"].isna().any():
        missing = gdf.loc[gdf["county"].isna(), "name"].tolist()
        raise ValueError(f"Unmapped county sub-areas: {missing}")

    dissolved = gdf.dissolve(by="county").reset_index()[["county", "geometry"]]
    # Simplify geometry to keep the committed file small (tolerance in degrees)
    dissolved["geometry"] = dissolved["geometry"].simplify(0.005, preserve_topology=True)
    dissolved.to_file(CLEAN_GEOJSON, driver="GeoJSON")
    print(f"Wrote {len(dissolved)}-county boundary file -> {CLEAN_GEOJSON}")
    return dissolved


def load_summary() -> pd.DataFrame:
    df = pd.read_csv(SUMMARY_CSV)
    return df


def make_choropleth(geojson: dict, latest_year_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            featureidkey="properties.county",
            locations=latest_year_df["county"],
            z=latest_year_df["median_price"],
            colorscale="Blues",
            marker_line_color="white",
            marker_line_width=0.5,
            colorbar_title="Median price (EUR)",
            hovertemplate="<b>%{location}</b><br>Median price: EUR %{z:,.0f}<extra></extra>",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title=f"Median Residential Sale Price by County — {int(latest_year_df['year'].iloc[0])}",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )
    return fig


def make_trend(summary: pd.DataFrame) -> go.Figure:
    national = (
        summary.groupby("year")
        .apply(lambda g: (g["median_price"] * g["n_sales"]).sum() / g["n_sales"].sum())
        .reset_index(name="weighted_median_price")
    )
    top_counties = ["Dublin", "Cork", "Galway", "Limerick", "Wicklow"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=national["year"], y=national["weighted_median_price"],
            mode="lines+markers", name="National (sales-weighted)",
            line={"width": 3, "color": "black"},
        )
    )
    for county in top_counties:
        sub = summary[summary["county"] == county].sort_values("year")
        fig.add_trace(
            go.Scatter(
                x=sub["year"], y=sub["median_price"], mode="lines", name=county,
            )
        )
    fig.update_layout(
        title="Median Sale Price Trend, 2010–Present",
        xaxis_title="Year", yaxis_title="Median price (EUR)",
        margin={"t": 40},
    )
    return fig


def build_dashboard_html(choropleth: go.Figure, trend: go.Figure) -> None:
    import pathlib

    pathlib.Path("dashboard").mkdir(exist_ok=True)
    with open(DASHBOARD_HTML, "w") as f:
        f.write("<html><head><title>Irish Property Price Dashboard</title></head><body>\n")
        f.write("<h1>Irish Residential Property Price Dashboard</h1>\n")
        f.write(choropleth.to_html(full_html=False, include_plotlyjs="cdn"))
        f.write(trend.to_html(full_html=False, include_plotlyjs=False))
        f.write("</body></html>\n")
    print(f"Wrote interactive dashboard -> {DASHBOARD_HTML}")


if __name__ == "__main__":
    dissolved = build_county_geojson()
    with open(CLEAN_GEOJSON) as f:
        geojson = json.load(f)

    summary = load_summary()
    latest_year = summary["year"].max()
    latest = summary[summary["year"] == latest_year]

    choropleth = make_choropleth(geojson, latest)
    trend = make_trend(summary)

    build_dashboard_html(choropleth, trend)

    choropleth.write_image("dashboard/choropleth.png", width=900, height=1000, scale=2)
    trend.write_image("dashboard/trend.png", width=1100, height=600, scale=2)
    print("Wrote dashboard/choropleth.png and dashboard/trend.png")
