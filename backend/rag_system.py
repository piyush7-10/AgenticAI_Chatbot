from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
import os

class JioRAGSystem:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        self.setup_vectorstore()
    
    def setup_vectorstore(self):
        # Load existing data
        with open('data/jio_data.json', 'r') as f:
            data = json.load(f)
        
        # Create documents with metadata
        documents = []
        for item in data:
            documents.append({
                'content': item['content'],
                'metadata': {'source': item['url'], 'title': item.get('title', 'Jio Info')}
            })
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
        texts = []
        metadatas = []
        for doc in documents:
            chunks = text_splitter.split_text(doc['content'])
            texts.extend(chunks)
            metadatas.extend([doc['metadata']] * len(chunks))
        
        # Create or load vector store
        self.vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory="./data/chroma_db"
        )
        print(f"✅ Vector database loaded with {len(texts)} chunks")
    
    def search(self, query: str, k: int = 3):
        """Search for relevant documents"""
        results = self.vectorstore.similarity_search(query, k=k)
        return [{'content': doc.page_content, 'source': doc.metadata.get('source', '')} 
                for doc in results]
    
    def get_context(self, query: str):
        """Get context for the query"""
        results = self.search(query)
        context = "\n\n".join([f"Source: {r['source']}\n{r['content']}" for r in results])
        return context