from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticField,
    VectorSearch,
    HnswVectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex
)
import os
from dotenv import load_dotenv

load_dotenv()

def create_search_index():
    # Initialize the search index client
    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    search_service_key = os.getenv("SEARCH_SERVICE_KEY")
    index_name = os.getenv("SEARCH_INDEX_NAME")

    credential = AzureKeyCredential(search_service_key)
    index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=credential)

    # Define the index fields
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="language", type=SearchFieldDataType.String),
        SimpleField(name="entities", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
        SimpleField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                   vector_search_dimensions=1536, vector_search_profile_name="default")
    ]

    # Define vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswVectorSearchAlgorithmConfiguration(
                name="default",
                kind="hnsw",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default",
                algorithm_configuration_name="default",
            )
        ]
    )

    # Define semantic search configuration
    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticField(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")]
        )
    )

    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_settings=semantic_config
    )

    try:
        index_client.create_or_update_index(index)
        print(f"Index {index_name} created successfully.")
    except Exception as e:
        print(f"Error creating index: {str(e)}")

if __name__ == "__main__":
    create_search_index()
