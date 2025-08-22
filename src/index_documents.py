from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from transformers import AutoTokenizer, AutoModel
import torch
import os
from dotenv import load_dotenv

load_dotenv()

def get_document_embedding(text, model, tokenizer):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).numpy().tolist()[0]

def process_and_index_documents():
    # Initialize clients
    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    search_service_key = os.getenv("SEARCH_SERVICE_KEY")
    storage_connection_string = os.getenv("STORAGE_CONNECTION_STRING")
    container_name = os.getenv("CONTAINER_NAME")
    index_name = os.getenv("SEARCH_INDEX_NAME")
    form_recognizer_endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    form_recognizer_key = os.getenv("FORM_RECOGNIZER_KEY")

    # Initialize clients
    search_client = SearchClient(endpoint=search_service_endpoint,
                               index_name=index_name,
                               credential=AzureKeyCredential(search_service_key))
    
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    
    document_analysis_client = DocumentAnalysisClient(
        endpoint=form_recognizer_endpoint,
        credential=AzureKeyCredential(form_recognizer_key)
    )

    # Load the embedding model
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    # Process each document in the container
    blobs = container_client.list_blobs()
    documents_to_index = []

    for blob in blobs:
        # Download the blob content
        blob_client = container_client.get_blob_client(blob.name)
        blob_content = blob_client.download_blob()

        # Analyze the document using Form Recognizer
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-document", blob_content
        )
        result = poller.result()

        # Extract text content
        content = " ".join([p.content for p in result.paragraphs])

        # Generate embedding
        content_embedding = get_document_embedding(content, model, tokenizer)

        # Create document
        document = {
            "id": blob.name,
            "content": content,
            "title": blob.name,
            "language": result.languages[0] if result.languages else "en",
            "entities": [e.content for e in result.entities],
            "contentVector": content_embedding
        }
        
        documents_to_index.append(document)

        # Index in batches of 50
        if len(documents_to_index) >= 50:
            try:
                search_client.upload_documents(documents_to_index)
                print(f"Indexed {len(documents_to_index)} documents")
                documents_to_index = []
            except Exception as e:
                print(f"Error indexing documents: {str(e)}")

    # Index any remaining documents
    if documents_to_index:
        try:
            search_client.upload_documents(documents_to_index)
            print(f"Indexed {len(documents_to_index)} documents")
        except Exception as e:
            print(f"Error indexing documents: {str(e)}")

if __name__ == "__main__":
    process_and_index_documents()
