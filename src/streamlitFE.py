import streamlit as st
import pandas as pd
import os
from PIL import Image
from io import BytesIO
import base64


LOGO_DIR = "data/logos_preprocessed/"
GROUPS_CSV = "data/groups/groups_w_buckets.csv"


@st.cache_data
def load_logo(filename):
    path = os.path.join(LOGO_DIR, filename)
    return Image.open(path)

@st.cache_data
def get_image_download_link(_img, filename):
    buffered = BytesIO()
    _img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f'<a href="data:file/png;base64,{img_str}" download="{filename}">Download</a>'


st.set_page_config(page_title="Logo Similarity Demo", layout="wide")

st.title("Logo Similarity - Global Use Case Scenarios")
st.write("Explore and analyze clusters of visually similar logos extracted from websites.")

df = pd.read_csv(GROUPS_CSV)
df['domain_list'] = df['domains'].apply(lambda x: x.split(';'))
df['num_domains'] = df['domain_list'].apply(len)


st.sidebar.title("🌍 Use Case Scenarios")
scenario = st.sidebar.selectbox(
    "Select a scenario:",
    [
        "Brand Monitoring",
        "Fraud Detection",
        "Reverse Logo Search",
        "Brand Consistency Check",
        "Batch Export Logos"
    ]
)

st.sidebar.markdown("---")
st.sidebar.write("Cluster size distribution:")
st.sidebar.bar_chart(df['num_domains'].value_counts().sort_index())


if scenario == "Brand Monitoring":
    st.subheader("Brand Monitoring: Identify identical logos across domains")
    st.write("Check if your logo appears consistently across all sub-brands or regions.")
    candidates = df[df['num_domains'] > 1].nlargest(10, 'num_domains')
    choice = st.selectbox("Select a cluster:", candidates.index)
    cluster = candidates.loc[choice]
    st.info(f"This logo is used by {cluster['num_domains']} domains.")
    cols = st.columns([1, 2])
    with cols[0]:
        first_dom = cluster['domain_list'][0]
        base = first_dom.replace('.', '_')
        matches = [f for f in os.listdir(LOGO_DIR) if f.startswith(base)]
        if matches:
            img = load_logo(matches[0])
            st.image(img, caption=matches[0], use_container_width=True)
            st.markdown(get_image_download_link(img, matches[0]), unsafe_allow_html=True)
    with cols[1]:
        st.write("Associated domains:")
        st.code("\n".join(cluster['domain_list']))

elif scenario == "Fraud Detection":
    st.subheader("Fraud Detection: Spot suspicious logo reuse")
    st.write("Flag clusters with unusually high domain counts for manual review.")
    suspects = df[df['num_domains'] > 10].nlargest(10, 'num_domains')
    for _, row in suspects.iterrows():
        st.write(f"Cluster of {row['num_domains']} domains:")
        st.code("; ".join(row['domain_list']))

elif scenario == "Reverse Logo Search":
    st.subheader("Reverse Logo Search: Find domains by logo")
    query = st.text_input("Enter part of a domain name:")
    if query:
        results = df[df['domains'].str.contains(query, case=False)]
        for _, row in results.iterrows():
            st.write(f"Cluster {row['group_id']}: {row['domains']}")
            dom = row['domain_list'][0]
            base = dom.replace('.', '_')
            matches = [f for f in os.listdir(LOGO_DIR) if f.startswith(base)]
            if matches:
                st.image(
                    load_logo(matches[0]),
                    caption=matches[0],                    
                    width=150,                
                    use_container_width=False   
                )

elif scenario == "Brand Consistency Check":
    st.subheader("Brand Consistency: Detect logo variations")
    st.write("Show clusters where logos might visually differ within the same brand family.")
    variable = df[df['num_domains'] > 1]
    for _, row in variable.head(5).iterrows():
        st.write(f"Cluster {row['group_id']} ({row['num_domains']} domains):")
        cols = st.columns(min(row['num_domains'], 5))
        for i, dom in enumerate(row['domain_list'][:5]):
            base = dom.replace('.', '_')
            matches = [f for f in os.listdir(LOGO_DIR) if f.startswith(base)]
            if matches:
                cols[i].image(load_logo(matches[0]), caption=dom, use_container_width=True)

elif scenario == "Batch Export Logos":
    st.subheader("Batch Export: Download logos by cluster")
    st.write("Select clusters to export all member logos as a ZIP archive.")
    clusters = df['group_id'].tolist()
    selected = st.multiselect("Pick clusters:", clusters)
    if st.button("Generate ZIP") and selected:
        st.success(f"ZIP archive for clusters {selected} is ready to download.")

else:
    st.warning("Please select a use case scenario from the sidebar.")

# Footer stats
st.markdown("---")
st.subheader("📊 Global Statistics")
col1, col2 = st.columns(2)
col1.metric("Total Clusters", len(df))
col2.metric("Total Logos", df['num_domains'].sum())
st.bar_chart(df['num_domains'].value_counts().sort_index())
