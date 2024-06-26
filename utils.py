from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.core.agent import AgentRunner
from llama_index.core import SimpleDirectoryReader
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core import VectorStoreIndex,StorageContext,get_response_synthesizer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.llms.openai import OpenAI
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.postprocessor import SentenceTransformerRerank


import os

from dotenv import load_dotenv
load_dotenv()

def save_uploaded_files(uploaded_files):
    
    file_paths = []
    upload_directory = "uploaded_files"
    
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
        
    for uploaded_file in uploaded_files:
        file_path = os.path.join(upload_directory, uploaded_file.name)
        file_paths.append(file_path)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        #st.write(f"File saved: {file_path}")
        
    return file_paths


def save_file_and_store_index(files):
    reader = SimpleDirectoryReader(input_files=files)
    docs = reader.load_data()
    spilter = SentenceSplitter(chunk_size=1024)
    chunk = spilter.get_nodes_from_documents(documents=docs)
    vector_store = MilvusVectorStore(collection_name="llamacollection",dim=1536,overwrite=True,uri="")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    vector_index = VectorStoreIndex(nodes=chunk,storage_context=storage_context)
    return vector_index

def create_agent(agent_name):
    name = agent_name
    return f"Agent is created successfully {name}."

def load_agent():
    data_tool = FunctionTool.from_defaults(fn=save_file_and_store_index)
    create_agent_tool = FunctionTool.from_defaults(fn=create_agent)
    llm = OpenAI(model="gpt-3.5-turbo")
    agent_worker = FunctionCallingAgentWorker.from_tools(
        tools=[data_tool,create_agent_tool],
        llm=llm,
        verbose=True,
        system_prompt=""" 
        You are helping to construct an agent given a user-specified task. 
        You should generally use the tools in this rough order to build the agent."
        
        1. Load in user-specified data (based on files they Upload).
        2. Built an Agent.
        
        This will be a back and forth conversation with the user. You should
        continue asking users if there's anything else they want to do until
        they say they're done. To help guide them on the process, 
        you can give suggestions on parameters they can set based on the tools they
        have available (e.g. "Do you want to set the number of documents to retrieve?")
        """
        )
    load_agent = AgentRunner(agent_worker)
    return load_agent


def retrieve_data_agent(collection_name):
    vector_store = MilvusVectorStore(collection_name=collection_name, dim=1536, overwrite=False, uri="http")
    index = VectorStoreIndex.from_vector_store(vector_store)
    
    # Method 1
    vector_query_engine = index.as_query_engine(similarity_top_k = 2)
    
    # Method 2
    retriever = VectorIndexRetriever(index=index,similarity_top_k=5)
    response_synthesizer = get_response_synthesizer()
    rerank = SentenceTransformerRerank(
        model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3)
    retriever_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
         # add rerank here .
        node_postprocessors=[rerank]
    )
    
    vector_tool = QueryEngineTool.from_defaults(
        query_engine=retriever_engine,
        description= " Tool for Semantic Search using the Vector Store "
        )
    
    llm = OpenAI(model="gpt-3.5-turbo")
    
    agent_worker = FunctionCallingAgentWorker.from_tools(
        tools=[vector_tool],
        llm=llm,
        verbose=True,
        system_prompt=""" 
        You are helping to construct an agent given a user-specified task. 
        You should generally use the tools in this rough order to build the agent."
        
        1. Load in user-specified data (based on files they Upload).
        2. Built an Agent.
        3. You are an agent designed to answer queries over a set of documents.
        Please use the provided tools to answer questions and summarize relevant information.
        Do not rely on prior knowledge.
        
        This will be a back and forth conversation with the user. You should
        continue asking users if there's anything else they want to do until
        they say they're done.
        """
        )
    retrieve_agent = AgentRunner(agent_worker)
    return retrieve_agent


collection_name = os.getenv('COLLECTION_NAME')

agent = retrieve_data_agent(collection_name)
response = agent.chat(" Summarize the whole PDF 'ts-eamcet-2022-last-rank (1).pdf' ")
print(response)


