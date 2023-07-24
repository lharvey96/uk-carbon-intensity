from typing import Optional

import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from pydantic import BaseModel
from streamlit.connections import ExperimentalBaseConnection

BASE_URL = "https://api.carbonintensity.org.uk"
HEADERS = {"Accept": "application/json"}


class RestApiConnectionModel(BaseModel):
    base_url: str


class RestApiGetEndpoint(BaseModel):
    url: str
    params: Optional[dict] = {}
    headers: Optional[dict] = HEADERS


class RestApiConnection(ExperimentalBaseConnection[RestApiConnectionModel]):
    def _connect(self, base_url: str) -> RestApiConnectionModel:
        return RestApiConnectionModel(base_url=base_url)

    def get_request_cursor(self, **kwargs) -> RestApiGetEndpoint:
        if "endpoint" in kwargs:
            url = self._instance.base_url + kwargs["endpoint"]
        return RestApiGetEndpoint(url=url, **kwargs)

    def query_endpoint(self, endpoint: str, ttl: int = 60 * 30) -> str:
        @st.cache_data(ttl=ttl)
        def _query(**kwargs):
            return requests.get(**self.get_request_cursor(**kwargs).__dict__).json()

        return _query(endpoint=endpoint)


st.set_page_config(
    layout="wide",
)

st.title("UK Carbon Intensity Dashboard")
st.markdown(
    """
    A simple dashboard to expose current carbon intenisty data for the UK sourced from the National Grid Carbon Intensity
    API found [here](https://api.carbonintensity.org.uk/).
    
    Visualises the current fuel mix of the UK power generation and the carbon intensity over the last 24 hrs.
    """
)
st.info(
    """Data is cached for 30 minutes in line with the expected update frequency of API which is based on the
        settlement period length used by the UK grid.
    """
)

conn = st.experimental_connection(
    "api", type=RestApiConnection, base_url="https://api.carbonintensity.org.uk"
)
# c = conn.get_request_cursor(endpoint="/generation")
gen_data = conn.query_endpoint(endpoint="/generation")
carbon_data = conn.query_endpoint(endpoint="/intensity/date")

gen_df = pd.DataFrame(gen_data["data"]["generationmix"])
carbon_df = (
    pd.DataFrame(carbon_data["data"])
    .set_index("from")["intensity"]
    .apply(pd.Series)
    .select_dtypes(include=[int, float])
)
col1, col2 = st.columns(2)
with col1:
    fig = px.pie(
        gen_df, values="perc", names="fuel", title="Current Generation Mix of the UK"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig2 = px.line(
        carbon_df,
        title="Carbon Intensity of the UK in the last 24 hrs (gCO2/kWh)",
        labels={"from": "", "value": ""},
    )
    st.plotly_chart(fig2, use_container_width=True)
