#=====================================================================
# PATTERN 4 - RAG (Retrieval Augmented Generation)
#=====================================================================
# idea      : fetch the right pieces of a document before answering
# nodes     : billing_rag_node, tech_rag_node, general_node
# reads     : clean_ticket
# writes    : retrieved_context
# graph.py  : billing_rag | tech_rag | general -> writer
#
# part 1 - build one retriever per pdf (runs once, when the app starts)
#          load -> split -> embed -> store in FAISS -> top 4 chunks
# part 2 - one node per route that searches its own pdf
#=====================================================================

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from state import SupportState

#the data folder sits next to the patterns folder
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


#---------------------------------------------------------------------
# part 1 - the retrievers
#---------------------------------------------------------------------

def build_retriever(pdf_name: str):
    loader = PyPDFLoader(os.path.join(DATA_DIR, pdf_name))
    document = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(document)

    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 4})


billing_retriever = build_retriever("billing_policy.pdf")
tech_retriever = build_retriever("tech_faq.pdf")


#---------------------------------------------------------------------
# part 2 - the nodes
#---------------------------------------------------------------------

def billing_rag_node(state: SupportState) -> dict:
    """Retrieves relevant chunks from the billing policy."""
    docs = billing_retriever.invoke(state["clean_ticket"])
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"retrieved_context": context}


def tech_rag_node(state: SupportState) -> dict:
    """Retrieves relevant chunks from the technical FAQ."""
    docs = tech_retriever.invoke(state["clean_ticket"])
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"retrieved_context": context}


def general_node(state: SupportState) -> dict:
    """No retrieval needed for greetings and small talk.
    It still fills the key so the writer always gets the same kind of input."""
    return {"retrieved_context": "NO_RETRIEVAL_NEEDED"}
