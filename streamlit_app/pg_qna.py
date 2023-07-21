# Description: This file contains the logic for the LLM bot
import os
import openai
import pandas as pd
import pandas as pd
import numpy as np

import psycopg2
from psycopg2 import pool
from psycopg2 import Error
from pgvector.psycopg2 import register_vector

from typing import List, Optional

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from langchain.prompts import PromptTemplate

import os
from dotenv import dotenv_values

# Get the absolute path to the .env file in the streamlit_app subdirectory
env_name = os.path.join(os.path.dirname(__file__), "llm_pgvector.env")

# Load environment variables from the .env file
config = dotenv_values(env_name)

for key, value in config.items():
    os.environ[key] = value

# LOAD OpenAI configs
openai.api_type = config["OPENAI_API_TYPE"]
openai.api_key = config['OPENAI_API_KEY']
openai.api_base = config['OPENAI_API_BASE']
openai.api_version = config['OPENAI_API_VERSION']
print("ENV VARIABLES LOADED")


class TextFormatter(BaseLoader):
    """Load text files."""

    def __init__(self, text: str):
        """Initialize with file path."""
        self.text = text

    def load(self) -> List[Document]:
        """Load from file path."""
        metadata = {"source": ""}
        return [Document(page_content=self.text, metadata=metadata)]


def createEmbeddings(text):
    response = openai.Embedding.create(input=text,engine=config['OPENAI_DEPLOYMENT_EMBEDDING'])
    embeddings = response['data'][0]['embedding']
    return embeddings


def retrieve_k_chunk(retrieve_k, questionEmbedding,ClientCode):
    # LOAD DB configs
    host = config["host"]
    dbname = config["dbname"]
    user = config["user"]
    password = config["password"]
    sslmode  = config["sslmode"]

    # Build a connection string from the variables
    conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)
    connection = psycopg2.connect(conn_string)
# Create a cursor after the connection
# Register 'pgvector' type for the 'embedding' column
    register_vector(connection)
    cursor = connection.cursor()
    print("ClientCode:", ClientCode)
    
    table_name1 = 'ClientCode'
    table_name2 = 'ChunksEmbedding'
    select_docid_query = f"SELECT DocId FROM {table_name1} WHERE ClientCode = '{ClientCode}'"
    cursor.execute(select_docid_query)
    doc_id = cursor.fetchone()[0]
    print('docid:', doc_id)
    select_query = f"SELECT Id FROM {table_name2} where DocId = '{doc_id}' ORDER BY embedding <-> %s LIMIT 3"
    cursor = connection.cursor()
    cursor.execute(select_query, (np.array(questionEmbedding),))
    results = cursor.fetchall()
    top_ids = []
    for i in range(len(results)):
        top_ids.append(int(results[i][0]))

    # Rollback the current transaction
    connection.rollback()

    format_ids = ', '.join(['%s'] * len(top_ids))

    sql = f"SELECT CONCAT('PageNumber: ', PageNumber, ' ', 'LineNumber: ', LineNumber, ' ', 'Text: ', Chunk) AS concat FROM {table_name2} WHERE id IN ({format_ids})"

    # Execute the SELECT statement
    try:
        cursor.execute(sql, top_ids)    
        top_rows = cursor.fetchall()
    except (Exception, Error) as e:
        print(f"Error executing SELECT statement: {e}")
    finally:
        cursor.close()
    return top_rows


def qna_llm(msg):
    import re
    match = re.search(r"Client Code: (\w+)", msg)
    if match:
        clientcode = match.group(1)
    else:
        return "Please provide client code as Client Code: <Client Code>. Then, the question."
    questionEmbedding = createEmbeddings(msg)
    retrieve_k = 3

    print("CLIENT CODE LOADED:{clientcode}")
    top_rows = retrieve_k_chunk(retrieve_k, questionEmbedding, clientcode)
    context = ""
    for row in top_rows:
        context += row[0]
        context += "\n"
    print("Context Retrieved")
    from langchain.llms import AzureOpenAI
    llm= AzureOpenAI(deployment_name=config['OPENAI_MODEL_COMPLETION'], model_name=config['OPENAI_MODEL_EMBEDDING'], temperature=0)
    from langchain.chains.question_answering import load_qa_chain
    loader = TextFormatter(context)
    ### Question Prompt Template
    question_prompt_template = """Use the context document to find relevant text and answer the question. Use the PageNumber and LineNumber and show it as a reference to the answer. 
    {context}
    Question: {question}
    If the answer is not found, ask the user to contact Account Manager (AM). If answer is found, make sure it is close to the context."""
    
    QUESTION_PROMPT = PromptTemplate(
        template=question_prompt_template, input_variables=["context", "question"]
        )
    print("Sending prompt...")
    chain = load_qa_chain(llm, chain_type="stuff", prompt=QUESTION_PROMPT)
    ans = chain({"input_documents": loader.load(), "question": msg}, return_only_outputs=True)

    return ans['output_text'][2:]


if __name__=="__main__":
    
    ans = qna_llm("Client Code: X5447. refill policy?")
    
    print(ans)
