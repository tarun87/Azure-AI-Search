from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Development mode flag
DEV_MODE = True  # Set to True for local development without Azure services

if not DEV_MODE:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.storage.blob import BlobServiceClient
    
    # Azure Search configuration
    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    search_service_key = os.getenv("SEARCH_SERVICE_KEY")
    index_name = os.getenv("SEARCH_INDEX_NAME")

    # Initialize the search client
    credential = AzureKeyCredential(search_service_key)
    search_client = SearchClient(
        endpoint=search_service_endpoint,
        index_name=index_name,
        credential=credential
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query_text = data.get('query', '')
    use_semantic = data.get('semantic', False)
    use_vector = data.get('vector', False)

    try:
        if DEV_MODE:
            # Return mock data in development mode
            search_results = [{
                'id': '1',
                'content': 'This is a sample document that matches your search query: ' + query_text,
                'title': 'Sample Document',
                'score': 1.0,
                'entities': ['sample', 'test'],
                'language': 'en'
            }]
        else:
            if use_semantic:
                results = search_client.search(
                    query_text,
                    query_type="semantic",
                    semantic_configuration_name="default",
                    query_language="en-us"
                )
            elif use_vector:
                # Implement vector search here
                pass
            else:
                results = search_client.search(query_text)

            search_results = []
            for result in results:
                search_results.append({
                    'id': result['id'],
                    'content': result.get('content', ''),
                    'title': result.get('title', ''),
                    'score': result['@search.score'],
                    'entities': result.get('entities', []),
                    'language': result.get('language', '')
                })

        return jsonify({'results': search_results})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
