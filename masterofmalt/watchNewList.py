import random
import os
import requests
import time
import json
from selenium import webdriver
import logging
from configparser import ConfigParser

HEADERS = {'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
NEW_ARRIVAL_ADDRESS = "https://www.masterofmalt.com/new-arrivals/whisky-new-arrivals/"
TRACKING_ADDRESS = "https://www.masterofmalt.com/api/data/productstracking/"

config = ConfigParser()
config.read('masterofmalt.ini')

logging.basicConfig(filename="masterofmalts.log", level=logging.INFO)

m_productIDs = ""

logging.basicConfig(filename="example.log", level=logging.INFO)
m_sentList = []

def parseWatchingNewProductList():
    global m_keys 
    m_keys = config['newProducts']['names'].split('&')
    logging.info("watching New Product List : " + str(m_keys))

def login():
    m_driver.get("https://www.masterofmalt.com")
    time.sleep(10)
    m_driver.execute_script('document.getElementById(\'onetrust-accept-btn-handler\').click();')
    m_driver.execute_script('document.getElementById(\'InternationalPopupConfirmation\').click();')
    time.sleep(5)
    m_driver.get("https://www.masterofmalt.com/#context-login")
    time.sleep(5)
    m_driver.execute_script('txtLoginEmail.value=\"' + config['user']['ID'] + '\";txtLoginPassword.value=\"' + config['user']['passwd'] + '\";document.getElementById(\'MOMBuyButton\').click();')
    time.sleep(5)

def refreshAndGetProductIds():    
    logging.info("Refresh page")
    m_driver.refresh()
    m_driver.implicitly_wait(2)
    idString = ""
    dataLayer = m_driver.execute_script('var iDs = window.dataLayer; return iDs')
    for data in dataLayer:
        if ("productIDs" in data):
            result = data['productIDs']
            idString = ','.join(map(str, result))
    logging.info("IdString : " + idString)
    return idString


def getProductInfoes(idString):
    r = requests.get(TRACKING_ADDRESS + idString, headers=HEADERS)
    try:
        ret = json.loads(r.content)
    except:
        if '403' in str(r):
            sendMessage('API Blocked', 2)
        else:
            sendMessage('Unknown Error occurred!\n' + str(r),2)
        return
    retString = str(r.content)
    retString = retString.replace("\\","")
    retString = retString.replace("'","")
    retString = retString[1:]
    return retString


def parseWachingListProducts():
    global m_watchList
    m_watchList = ""
    
    with open(os.getcwd() + '/masterofmalt.json', 'r', encoding='UTF8') as jsonFile:
        itemData = json.load(jsonFile)
        for item in itemData['itemList']:
            m_watchList = m_watchList + item['code'] + ','
        m_watchList = m_watchList[:-1]
    print(m_watchList + "\n")
    logging.info("m_watchList : " + m_watchList)
def checkProductInfoes(jsonString):
    jsonData = json.loads(jsonString)
    products = jsonData['products']
    logging.info("products info : " + str(products))
    for item in products:
        for key in m_keys :
            prodID = item['productID']
            prodName = item['name'].lower()
            avab =  item['available']
            if (avab == True and key in prodName and prodID not in m_sentList):
                text = "###### NEW STOCK ######\n"
                text = text + item['name'] + " Arrived !!\n"
                text = text + "https://www.masterofmalt.com/checkout/"
                print("send target item incomed message")
                sendMessage(text,5)
                m_driver.execute_script('AddToBasket(' + str(prodID) + ')')
                m_sentList.append(item['productID'])
                

def sendMessage(text, sendCount):
    try:
        for i in range(1,sendCount):
            requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer "+ config['slack']['token']},
            data={"channel": '#' + config['slack']['channel'],"text": text})
            time.sleep(1)
    except:
        logging.error("### error occur during sendMessage. msg : " + text)


def reCreateWebObj():
    m_driver.close()
    time.sleep(5)
    sendMessage('### Sleep 10 Min to reopen webPage ###',2)
    time.sleep(600)
    webObjInit()


def createWebObj():
    global m_driver
    m_driver = webdriver.Chrome(config['chrome']['enginePath'])


def webObjInit():
    createWebObj()
    login()
    m_driver.get(NEW_ARRIVAL_ADDRESS)
    

if __name__ == "__main__":
    parseWatchingNewProductList()
    parseWachingListProducts()
    webObjInit()
    watchingSpan = int(config['etc']['watchingSpan'])
    watchCount = 0
    while True:
        if watchCount % watchingSpan == 0:
            sendMessage("### still watching ###", 2)
        
        try:
            idString = refreshAndGetProductIds()
        except:
            sendMessage("### Error occur during get New Products", 2)
            reCreateWebObj()
        
        if (m_productIDs != idString) :
            sendMessage("### New Item Arrived, Check New List ###", 2)
            m_productIDs = idString
            try:
                jsonString = getProductInfoes(m_productIDs)
            except:
                sendMessage("### Error occur during get Product info", 2)
                reCreateWebObj()
            try:
                checkProductInfoes(jsonString)
            except:
                sendMessage("### Error occur during parsing Product info", 2)
                reCreateWebObj()
        
        watchCount = watchCount + 1
        time.sleep(random.randrange(30,60))