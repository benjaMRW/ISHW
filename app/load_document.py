from llama_index import SimpleDirectoryReader, VectorStoreIndex
import os

def create_index():
    documents = SimpleDirectoryReader("docs").load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir="index_store")
    print("✅ Index created and saved.")



if __name__ == "__main__":
    create_index()
