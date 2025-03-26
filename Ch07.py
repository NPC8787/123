import os
import time
import random
import zipfile
import io
import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.summarize import load_summarize_chain

class PdfLoader:
    def __init__(self,openai_api_key):
        os.environ['OPENAI_API_KEY'] = openai_api_key
        
        self.llm = ChatOpenAI(temperature=0, model="gpt-4-turbo")
        self.data_prompt=ChatPromptTemplate.from_messages(messages=[("system","你的任務是對年報資訊進行摘要總結。"
                    "以下為提供的年報資訊：{text},"
                    "請給我重點數據, 如銷售增長情形、營收變化、開發項目等,"
                    "最後請使用繁體中文輸出報告")])
        self.data_chain = load_summarize_chain(llm=self.llm, chain_type='stuff', prompt=self.data_prompt)

    def annual_report(self,id,y):
        wait_time = random.uniform(2,6)
        url = 'https://doc.twse.com.tw/server-java/t57sb01'
        folder_path = '/content/drive/MyDrive/StockGPT/PDF/'
        # 建立 POST 請求的表單
        data = {
            "id":"",
            "key":"",
            "step":"1",
            "co_id":id,
            "year":y,
            "seamon":"",
            "mtype":'F',
            "dtype":'F04'
        }
        # 發送 POST 請求
        with requests.post(url, data=data) as response:
            time.sleep(wait_time)
            # 取得回應後擷取檔案名稱
            link=BeautifulSoup(response.text, 'html.parser')
            link1=link.find('a').text
            print(link1)
    
        # 建立第二個 POST 請求的表單
        data2 = {
            'step':'9',
            'kind':'F',
            'co_id':id,
            'filename':link1 # 檔案名稱
        }
        # 發送 POST 請求
        file_extension = link1.split('.')[-1]
        if  file_extension =='zip':
            with requests.post(url, data=data2) as response2:
                if response2.status_code == 200:
                    zip_data = io.BytesIO(response2.content)
                    with zipfile.ZipFile(zip_data) as myzip:
                        # 瀏覽 ZIP 檔案中的所有檔案和資料夾
                        for file_info in myzip.namelist():
                            if file_info.endswith('.pdf'):
                                # 讀取 PDF 檔案
                                with myzip.open(file_info) as myfile:
                                    # 你可以選擇如何處理 PDF 檔案，例如儲存它
                                    with open(folder_path + y + '_' + id +'.pdf', 'wb') as f:
                                        f.write(myfile.read())
                                    print('ok')
        else:
            # 發送 POST 請求
            with requests.post(url, data=data2) as response2:
                time.sleep(wait_time)
                link=BeautifulSoup(response2.text, 'html.parser')
                link1=link.find('a')['href']
                print(link1)
        
            # 發送 GET 請求
            response3 = requests.get('https://doc.twse.com.tw' + link1)
            time.sleep(wait_time)
            # 取得 PDF 資料
            
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            with open(folder_path + y + '_' + id + '.pdf', 'wb') as file:
                file.write(response3.content)
            print('OK')
            
    def pdf_loader(self,file,size,overlap):
        loader = PDFPlumberLoader(file)
        doc = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=size,
                                                chunk_overlap=overlap)
        new_doc = text_splitter.split_documents(doc)
        db = InMemoryVectorStore.from_documents(new_doc, OpenAIEmbeddings())
        file_name = file.split("/")[-1].split(".")[0]
        db_file = '/content/drive/MyDrive/StockGPT/DB/'
        if not os.path.exists(db_file):
            os.makedirs(db_file)
        db.save_local(db_file + file_name)
        return db
        
    def analyze_chain(self,db,input):
        data = db.similarity_search(input, k=2)
        
        result = self.data_chain.invoke({"input_documents": data})
        return result['output_text']
