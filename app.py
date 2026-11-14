"""Export Competition Radar: Streamlit application."""

import pandas as pd
import plotly.express as px
import streamlit as st


# 1. Read the data and add readable country/product names.
def load_data():
    trade = pd.read_csv("trade.csv", dtype={"k": str})
    countries = pd.read_csv("countries.csv")
    products = pd.read_csv("products.csv", dtype={"code": str})

    # The trade file stores countries as numeric codes.
    country_names = dict(zip(countries["country_code"], countries["country_name"]))
    product_names = dict(zip(products["code"], products["description"]))

    trade["exporter"] = trade["i"].map(country_names)
    trade["importer"] = trade["j"].map(country_names)
    trade["product"] = trade["k"].map(product_names)

    # Market size = total imports for one product, country and year.
    trade["market_total"] = trade.groupby(["t", "j", "k"])["v"].transform("sum")
    trade["share"] = 100 * trade["v"] / trade["market_total"]
    return trade


# 2. Compare suppliers in two years.
def compare_suppliers(market, first_year, last_year):
    start = market[market["t"] == first_year]
    end = market[market["t"] == last_year]

    # Keep countries that appear in either year.
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


st.set_page_config(page_title="Export Competition Radar", layout="wide")
st.title("🌍 Export Competition Radar")
st.caption("CEPII BACI · HS 2017 · 2017–2024 · values in thousands of USD")
st.info("Research prototype: seven selected markets. Changes in shares do not prove their causes.")

data = load_data()

# 3. Let the user choose a product and an importing country.
market_list = data[["j", "k", "importer", "product"]].drop_duplicates()
market_labels = []
for row in market_list.itertuples():
    market_labels.append(f"{row.importer} — HS {row.k} — {row.product}")

selected_label = st.selectbox("Choose an importing country and product", market_labels)
selected_position = market_labels.index(selected_label)
selected_row = market_list.iloc[selected_position]

market = data[(data["j"] == selected_row["j"]) & (data["k"] == selected_row["k"])].copy()
years = sorted(market["t"].unique())
first_year = st.selectbox("First year", years, index=0)
last_year = st.selectbox("Last year", years, index=len(years) - 1)

if first_year >= last_year:
    st.warning("Please choose a last year later than the first year.")
    st.stop()

start_data = market[market["t"] == first_year]
end_data = market[market["t"] == last_year]
market_start = start_data["v"].sum()
market_end = end_data["v"].sum()
changes = compare_suppliers(market, first_year, last_year)

col1, col2, col3 = st.columns(3)
col1.metric("Market size, final year", f"${market_end / 1000:,.1f}M")
col2.metric("Suppliers, final year", len(end_data))
col3.metric("Market change", f"${(market_end - market_start) / 1000:+,.1f}M")

tab1, tab2, tab3, tab4 = st.tabs([
    "Competition Radar", "Supplier Rankings", "Shift Decomposer", "Evidence Trail"
])

with tab1:
    st.subheader("How did supplier market shares change?")
    number_to_show = st.slider("Number of suppliers", 3, 15, 7)
    leaders = end_data.sort_values("v", ascending=False).head(number_to_show)
    selected_suppliers = leaders["i"].tolist()
    chart_data = market[market["i"].isin(selected_suppliers)]
    chart_data = chart_data[chart_data["t"].between(first_year, last_year)]
    chart = px.line(chart_data, x="t", y="share", color="exporter", markers=True,
                    labels={"t": "Year", "share": "Market share (%)", "exporter": "Supplier"})
    st.plotly_chart(chart, use_container_width=True)
    st.caption("Suppliers are selected by their value in the final year. Shares include all suppliers.")

with tab2:
    st.subheader("Which suppliers gained or lost market share?")
    columns = ["Exporter", "Share before (%)", "Share after (%)", "Change (pp)"]
    st.dataframe(changes[columns].round(2), hide_index=True, use_container_width=True)
    st.download_button("Download ranking", changes.to_csv(index=False), "ranking.csv")

with tab3:
    st.subheader("Market size vs. market share")
    names = changes["Exporter"].tolist()
    chosen_name = st.selectbox("Choose a supplier", names)
    chosen_row = changes[changes["Exporter"] == chosen_name].iloc[0]

    share_before = chosen_row["Share before (%)"] / 100
    share_after = chosen_row["Share after (%)"] / 100
    market_effect = share_before * (market_end - market_start)
    share_effect = market_end * (share_after - share_before)
    actual_change = chosen_row["Value after"] - chosen_row["Value before"]

    st.write(f"**Total change:** ${actual_change / 1000:,.3f} million")
    st.write(f"**Market-size component:** ${market_effect / 1000:,.3f} million")
    st.write(f"**Market-share component:** ${share_effect / 1000:,.3f} million")
    st.latex(r"\Delta X = s_0(M_1-M_0) + M_1(s_1-s_0)")
    st.caption("An accounting identity, not a causal explanation. Values are nominal USD.")
    error = actual_change - market_effect - share_effect
    st.write("Calculation check (should be near zero):", round(error, 7))

with tab4:
    st.subheader("Where do these numbers come from?")
    st.write("**Source:** CEPII BACI, HS17, release V202601.")
    st.write("**Variables:** t = year, i = exporter, j = importer, k = product HS6, v = USD thousands.")
    st.write("**Market share:** supplier value divided by total import value for the product and year.")
    st.write("**Limitations:** Value is not quantity. Prices, re-exports, reporting differences and product mix can affect results. This prototype has not independently validated every market-year.")
    st.markdown("[Official BACI database](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37)")
    chosen_data = market[market["t"].between(first_year, last_year)]
    st.download_button("Download market data", chosen_data.to_csv(index=False), "market_data.csv")
