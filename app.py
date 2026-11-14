"""Trade Competition Radar: Streamlit application."""

import pandas as pd
import plotly.express as px
import streamlit as st


# 1. Read the data and add readable country/product names.
def load_data():
    trade = pd.read_csv("trade.csv", dtype={"k": str})
    countries = pd.read_csv("countries.csv")
    products = pd.read_csv("products.csv", dtype={"code": str})

    country_names = dict(zip(countries["country_code"], countries["country_name"]))
    product_names = dict(zip(products["code"], products["description"]))

    trade["exporter"] = trade["i"].map(country_names)
    trade["importer"] = trade["j"].map(country_names)
    trade["product"] = trade["k"].map(product_names)

    # Market share = supplier exports / total imports of this product.
    trade["market_total"] = trade.groupby(["t", "j", "k"])["v"].transform("sum")
    trade["share"] = 100 * trade["v"] / trade["market_total"]
    return trade


# 2. Compare suppliers in two years.
def compare_suppliers(market, first_year, last_year):
    start = market[market["t"] == first_year]
    end = market[market["t"] == last_year]
    supplier_codes = sorted(set(start["i"]) | set(end["i"]))
    rows = []

    for code in supplier_codes:
        old = start[start["i"] == code]
        new = end[end["i"] == code]
        old_value = old["v"].sum()
        new_value = new["v"].sum()
        old_share = old["share"].sum()
        new_share = new["share"].sum()

        name = str(code)
        if len(new) > 0:
            name = new["exporter"].iloc[0]
        elif len(old) > 0:
            name = old["exporter"].iloc[0]

        rows.append({
            "code": code,
            "Exporter": name,
            "Share before (%)": old_share,
            "Share after (%)": new_share,
            "Change (pp)": new_share - old_share,
            "Value before": old_value,
            "Value after": new_value,
        })

    result = pd.DataFrame(rows)
    return result.sort_values("Change (pp)", ascending=False)


# 3. Page appearance: colors and spacing (CSS changes appearance only).
st.set_page_config(page_title="Trade Competition Radar", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #F7F9FC; color: #18283D; }
    .block-container { max-width: 1220px; padding-top: 2.3rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: #172C48; letter-spacing: -0.025em; }
    h1 { font-size: 2.4rem !important; font-weight: 700 !important; }
    h3 { font-size: 1.25rem !important; }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E1E7F0;
        border-radius: 10px;
        padding: 17px 20px;
    }
    [data-testid="stMetricLabel"] { color: #5C6E83; }
    [data-testid="stMetricValue"] { color: #183554; }
    div[data-testid="stSelectbox"] > label { color: #52647B; font-weight: 600; }
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF;
        border-color: #DCE4EF;
        border-radius: 8px;
    }
    button[data-baseweb="tab"] { color: #52647B; font-weight: 600; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #176C8D; }
    [data-testid="stDataFrame"] { border: 1px solid #E1E7F0; border-radius: 8px; }
    .eyebrow { font-size: 0.78rem; letter-spacing: 0.12em; color: #357A93; font-weight: 700; }
    .intro { color: #5C6E83; font-size: 1.04rem; margin-top: -0.4rem; }
    .note { color: #62738A; font-size: 0.85rem; border-left: 3px solid #A6BDCC;
            padding: 0.45rem 0.8rem; margin: 1.2rem 0 1.5rem; }
    .section-label { color: #355A75; font-size: 0.84rem; font-weight: 700;
                     letter-spacing: 0.04em; margin: 1.2rem 0 0.3rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">INTERNATIONAL TRADE / DATA EXPLORER</div>', unsafe_allow_html=True)
st.title("Trade Competition Radar")
st.markdown('<div class="intro">Explore how countries gain and lose market share in global trade.</div>', unsafe_allow_html=True)
st.markdown('<div class="note">Research prototype | Seven selected markets | CEPII BACI HS 2017 | 2017-2024. Changes in market share do not establish causes.</div>', unsafe_allow_html=True)

data = load_data()

# 4. Choose a market and years.
market_list = data[["j", "k", "importer", "product"]].drop_duplicates()
market_labels = []
for row in market_list.itertuples():
    market_labels.append(f"{row.importer} - HS {row.k} - {row.product}")

st.markdown('<div class="section-label">MARKET SELECTION</div>', unsafe_allow_html=True)
selected_label = st.selectbox("Importing country and product", market_labels)
selected_position = market_labels.index(selected_label)
selected_row = market_list.iloc[selected_position]

is_chosen_importer = data["j"] == selected_row["j"]
is_chosen_product = data["k"] == selected_row["k"]
market = data[is_chosen_importer & is_chosen_product].copy()

years = sorted(market["t"].unique())
year_col1, year_col2 = st.columns(2)
with year_col1:
    first_year = st.selectbox("From year", years, index=0)
with year_col2:
    last_year = st.selectbox("To year", years, index=len(years) - 1)

if first_year >= last_year:
    st.warning("Please choose an end year later than the start year.")
    st.stop()

start_data = market[market["t"] == first_year]
end_data = market[market["t"] == last_year]
market_start = start_data["v"].sum()
market_end = end_data["v"].sum()
market_change = market_end - market_start
changes = compare_suppliers(market, first_year, last_year)

st.markdown('<div class="section-label">MARKET OVERVIEW</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
col1.metric("Import market | final year", f"${market_end / 1000:,.1f}M")
col2.metric("Suppliers | final year", len(end_data))
col3.metric("Change in market value", f"${market_change / 1000:+,.1f}M")
st.caption("Trade values are nominal USD. BACI records values in thousands of USD; overview values are shown in millions.")

# 5. Four research sections.
tab1, tab2, tab3, tab4 = st.tabs([
    "Competition Radar", "Supplier Rankings", "Shift Decomposer", "Evidence Trail"
])

with tab1:
    st.subheader("Supplier market shares over time")
    number_to_show = st.slider("Number of suppliers", 3, 15, 7)
    leaders = end_data.sort_values("v", ascending=False).head(number_to_show)
    selected_suppliers = leaders["i"].tolist()
    chart_data = market[market["i"].isin(selected_suppliers)]
    chart_data = chart_data[chart_data["t"].between(first_year, last_year)]

    chart = px.line(
        chart_data, x="t", y="share", color="exporter", markers=True,
        labels={"t": "Year", "share": "Market share (%)", "exporter": "Supplier"},
        color_discrete_sequence=[
            "#176C8D", "#E19B42", "#4068A1", "#4C9A83", "#9A6BA7",
            "#B65E66", "#6D8498", "#9A8652", "#4F8C9A", "#B58273",
            "#5C7295", "#758B5B", "#9B7691", "#A87C4B", "#557B75"
        ],
    )
    chart.update_layout(
        template="plotly_white", paper_bgcolor="#F7F9FC", plot_bgcolor="#FFFFFF",
        font=dict(color="#314760"), hovermode="x unified",
        legend_title_text="Supplier", margin=dict(l=10, r=10, t=15, b=15),
        xaxis=dict(dtick=1, showgrid=False),
        yaxis=dict(gridcolor="#E7ECF3", rangemode="tozero"),
    )
    chart.update_traces(line=dict(width=2.5), marker=dict(size=7))
    st.plotly_chart(chart, use_container_width=True)
    st.caption("Suppliers are selected by their trade value in the final year. Market shares use all suppliers, not only those shown in the chart.")

with tab2:
    st.subheader("Who gained or lost market share?")
    columns = ["Exporter", "Share before (%)", "Share after (%)", "Change (pp)"]
    st.dataframe(changes[columns].round(2), hide_index=True, use_container_width=True)
    st.download_button("Download supplier ranking (CSV)", changes.to_csv(index=False), "ranking.csv", mime="text/csv")

with tab3:
    st.subheader("Market growth and competitive position")
    names = changes["Exporter"].tolist()
    chosen_name = st.selectbox("Supplier", names)
    chosen_row = changes[changes["Exporter"] == chosen_name].iloc[0]

    share_before = chosen_row["Share before (%)"] / 100
    share_after = chosen_row["Share after (%)"] / 100
    market_effect = share_before * market_change
    share_effect = market_end * (share_after - share_before)
    actual_change = chosen_row["Value after"] - chosen_row["Value before"]

    st.write(f"**Total change in supplier exports:** ${actual_change / 1000:,.3f} million")
    st.write(f"**Market-size component:** ${market_effect / 1000:,.3f} million")
    st.write(f"**Market-share component:** ${share_effect / 1000:,.3f} million")
    st.latex(r"\Delta X = s_0(M_1-M_0) + M_1(s_1-s_0)")
    st.caption("This is an exact accounting decomposition, not a causal explanation. All values are nominal USD.")
    error = actual_change - market_effect - share_effect
    st.write("Calculation check (should be near zero):", round(error, 7))

with tab4:
    st.subheader("Data and methodology")
    st.write("**Source:** CEPII BACI, HS17, release V202601.")
    st.write("**Variables:** t = year, i = exporter, j = importer, k = product HS6, v = trade value in thousands of USD.")
    st.write("**Market share:** supplier value divided by the total import value for the product and year.")
    st.write("**Limitations:** Value is not quantity. Prices, re-exports, reporting differences and product mix can affect results. This prototype has not independently validated every market-year.")
    st.markdown("[CEPII BACI database](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37)")
    chosen_data = market[market["t"].between(first_year, last_year)]
    st.download_button("Download selected market data (CSV)", chosen_data.to_csv(index=False), "market_data.csv", mime="text/csv")
