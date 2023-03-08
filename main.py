import time
from datetime import datetime
from os import walk
import os
from flask import Flask, render_template, request, jsonify

import dateutil.parser
from dateutil import parser
import requests

from elasticsearch.client import Elasticsearch
from elasticsearch.helpers import bulk
import json

class ElasticS:
    def __init__(self, index_name="mail-search1.1", index_type="_doc", ip="localhost"):
        self.index_name = index_name
        self.index_type = index_type
        self.es = Elasticsearch(host=ip,port=9200)

    def create_index(self, index_name="mail-search", index_type="enron"):
        '''
        创建索引,创建索引名称为ott，类型为ott_type的索引
        :param ex: Elasticsearch对象
        :return:
        '''
        # 创建映射
        _index_mappings = {
            "settings": {
                "index": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "refresh_interval": -1
                }
            },
            "mappings": {
                    "properties": {
                        "Message-ID": {
                            "type": "keyword"
                        },
                        "Date": {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss"
                        },
                        "From": {
                            "type": "text"
                        },
                        "To": {
                            "type": "text"
                        },
                        "Subject": {
                            "type": "text"
                        },
                        "Mime-Version": {
                            "type": "keyword"
                        },
                        "Content-Type": {
                            "type": "text"
                        },
                        "Content-Transfer-Encoding": {
                            "type": "keyword"
                        },
                        "X-From": {
                            "type": "text"
                        },
                        "X-To": {
                            "type": "text"
                        },
                        "X-cc": {
                            "type": "keyword"
                        },
                        "X-bcc": {
                            "type": "keyword"
                        },
                        "X-Folder": {
                            "type": "text"
                        },
                        "X-Origin": {
                            "type": "keyword"
                        },
                        "X-FileName": {
                            "type": "text"
                        },
                        "Main": {
                            "type": "text"
                        },
                    }

            }
        }
        if self.es.indices.exists(index=index_name) is not True:
            res = self.es.indices.create(index_name, body=_index_mappings, request_timeout=30)
            print(res)

    def IndexData(self,dir='F:\\InfoRetrieval\\hw3\\maildir'):
        errorfile = open('F:\\InfoRetrieval\\hw3\\error.txt', 'w')
        acts=[]
        count=0
        tot=0
        for (dirpath, dirnames, filenames) in walk(dir):
            for f in filenames:
                file=os.path.join(dirpath,f)
                a=self.Index_Data_Read(file,errorfile)
                if len(a)==0:
                    continue
                acts.append(a)
                count+=1
                tot+=1
                if count==1000:
                    print(bulk(self.es, actions=acts))
                    acts=[]
                    count=0
                    print(tot)
        print('index OK')

    def Index_Data_Read(self, file,error_file):
        info = []
        prop = []
        count = 0
        main1 = ""
        jump = False
        #file = 'F:\\InfoRetrieval\\hw3\\maildir\\allen-p\\all_documents\\1'
        try:
            with open(file, encoding='UTF-8') as lines:
                for line in lines:
                    if not jump:
                        if line.find(':') != -1:
                            if line.find('X-FileName') == -1:
                                if line.find('Date:') != -1:
                                    if len(line.split(":", maxsplit=1)) <= 1:
                                        info.append('')
                                        prop.append(line.split(":", maxsplit=1)[0])
                                    else:
                                        info.append(str(parser.parse(
                                            line.split(":", maxsplit=1)[1].split("-", maxsplit=1)[0].strip())))
                                        prop.append(line.split(":", maxsplit=1)[0])
                                else:
                                    if len(line.split(":", maxsplit=1)) <= 1:
                                        info.append('')
                                        prop.append(line.split(":", maxsplit=1)[0])
                                    else:
                                        info.append(line.split(":", maxsplit=1)[1].strip())
                                        prop.append(line.split(":", maxsplit=1)[0])
                            else:
                                if len(line.split(":", maxsplit=1)) <= 1:
                                    info.append('')
                                    prop.append(line.split(":", maxsplit=1)[0])
                                else:
                                    info.append(line.split(":", maxsplit=1)[1].strip())
                                    prop.append(line.split(":", maxsplit=1)[0])
                                jump = True
                        else:
                            info[-1]=info[-1]+str(line)
                    else:
                        main1 = str(main1) + str(line)
        except UnicodeError:
            print('decode error')
            error_file.write('decode error '+file+'\n')
            return {}
        except dateutil.parser.ParserError:
            print('parser error')
            error_file.write('parser error '+file+'\n')
            return {}
        except:
            print('failed to parse')
            error_file.write('failed to parse '+file+'\n')
            return {}
        dict = {}
        prop.append('Main')
        for i in range(len(info)):
            dict[prop[i]] = info[i]
        dict['Main'] = main1
        action={
            "_op_type": "index",
            "_index": "mail-search1.2",
            "_type": "_doc",
            "_source": dict
        }
        return action
        # res = self.es.index(index=self.index_name, document=(dict))


    def Get_Data_By_Body(self, cond):
        # doc = {'query': {'match_all': {}}}
        doc = {
            "query": {
                "bool": {
                    "must": [
                    ]
                }
            },
            "highlight":{
                "fields" :{
                },
                "pre_tags": ["<font color='red'>"],
                "post_tags": ["</font>"]
            }
        }
        for i in range(4):
            if i!=3:
                if cond[i][0]:
                    doc["query"]["bool"]["must"].append({"match": {cond[i][1]: cond[i][2]}})
                    doc["highlight"]["fields"][cond[i][1]] = {}
            else:
                if cond[i][0]:
                    doc["query"]["bool"]["must"].append({"match_phrase": {cond[i][1]: cond[i][2]}})
                    doc["highlight"]["fields"][cond[i][1]] = {}
        if len(doc["query"]["bool"]["must"])==0:
            doc["query"]["bool"]["must"].append(({"match_all": {}}))


        _searched = self.es.search(index=self.index_name, doc_type=self.index_type, body=doc)
        #print(self.es.explain(index=self.index_name, doc_type=self.index_type, body=doc,id="bpRdOX0BXs6hNp5YSGZ4"))

        for hit in _searched['hits']['hits']:
            #print(hit['_score'])
            print(hit['_source']['Message-ID'])

        return _searched


if __name__ == '__main__':
    obj=ElasticS()
    doc = {
        "query": {
            "match":{
                "X-From": "allen"
            }
        }
    }
    # print(obj.es.explain(index=obj.index_name, doc_type=obj.index_type, body=doc, id="bpRdOX0BXs6hNp5YSGZ4"))
    # obj.create_index(index_name="mail-search1.2")
    #obj.IndexData()
    obj.es.indices.refresh(index="mail-search1.2")
    #obj.es.indices.delete(index='mail-search1.1')
    s='Information Retrieval'
    doc = {
        'From': s,
        'To': 'Test for ElasticSearch'
    }
    #res=requests.get('http://127.0.0.1:81')
    #print(res.content.decode('UTF-8'))

    server=Flask(__name__)

    @server.route("/")
    def index():
        return render_template("index.html")


    @server.route("/submit",methods=["GET", "POST"])
    def submit():
        # 由于POST、GET获取数据的方式不同，需要使用if语句进行判断
        c=[]
        tag=["X-From", "X-To", "Subject", "Main"]
        if request.method == "POST":
            c.append(request.form.get(key="X-from"))
            c.append(request.form.get(key="X-to"))
            c.append(request.form.get(key="subject"))
            c.append(request.form.get(key="main"))
        elif request.method == "GET":
            c.append(request.args.get(key="X-from"))
            c.append(request.args.get(key="X-to"))
            c.append(request.args.get(key="subject"))
            c.append(request.args.get(key="main"))
        else:
            c.append("")
            c.append("")
            c.append("")
            c.append("")
        cond = []
        for i in range(4):
            cond.append([])
            if len(c[i])==0:
                cond[i].append(False)
            else:
                cond[i].append(True)
            cond[i].append(tag[i])
            cond[i].append(c[i])
        print(cond)
        ans=obj.Get_Data_By_Body(cond)
        if len(ans["hits"]["hits"])>0:
            keys=list(ans["hits"]["hits"][0]["_source"].keys())
        else:
            keys=None
        return {"message": "success!", "ans": ans, "keys": keys, "cond": cond}

    server.run(port=5000)
    #obj.Get_Data_By_Body()
    # obj.create_index(index_name="mail-search1.1")
    #obj.es.index(index=obj.index_name, doc_type=obj.index_type, document=(doc))
    #obj.es.delete(id='PS0ZKX0Bpr07QLRbAjjT',index=obj.index_name, doc_type=obj.index_type)
