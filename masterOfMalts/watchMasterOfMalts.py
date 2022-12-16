import random
import ast
import os
import requests
import time
import json
import schedule
import logging
from configparser import ConfigParser
from selenium import webdriver
from dataclasses import dataclass 
from datetime import date
from datetime import datetime

HEADERS = {'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
NEW_ARRIVAL_ADDRESS = "https://www.masterofmalt.com/new-arrivals/whisky-new-arrivals/"
TRACKING_ADDRESS = "https://www.masterofmalt.com/api/data/productstracking/"
CHECKOUT_ADDRESS = "https://www.masterofmalt.com/checkout/address/"

config = ConfigParser()
config.read('masterOfMalts.ini')

logging.basicConfig(filename="masterOfMalts.log", level=logging.INFO)

m_lastNewProductIDs = ""
m_sentList = []


# ------ Error Code ------- #
INVALID_WATCH_TARGET = -100
INVALID_USER_INFO = -200


# ------ Data Structure ------ # 
@dataclass 
class userInfo: 
    id: str
    passwd: float
    lastCheckoutTime: date = datetime.now()
    checkoutAvailable: bool = True


@dataclass 
class watchItem: 
    prodId: str
    autoCheckOut: bool


# ----- Web Obect Control ----- #
def createWebObj():
    global m_watchDriver
    global m_checkoutDriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    m_watchDriver = webdriver.Chrome(config['chrome']['enginePath'], chrome_options=chrome_options)
    m_checkoutDriver = webdriver.Chrome(config['chrome']['enginePath'], chrome_options=chrome_options)


def webObjInit():
    createWebObj()
    login()
    m_watchDriver.get(NEW_ARRIVAL_ADDRESS)
    

def reCreateWebObj():
    m_watchDriver.close()
    m_checkoutDriver.close()
    sendMessage('### Sleep 10 Min to reopen webPage ###', 2, False)
    time.sleep(600)
    webObjInit()
    sendMessage('### reopen webPage ###', 2, False)
    

def login():
    m_watchDriver.get("https://www.masterofmalt.com")
    m_checkoutDriver.get("https://www.masterofmalt.com")
    time.sleep(10)
    
    m_watchDriver.execute_script('document.getElementById(\'onetrust-accept-btn-handler\').click();')
    m_watchDriver.execute_script('document.getElementById(\'InternationalPopupConfirmation\').click();')
    m_checkoutDriver.execute_script('document.getElementById(\'onetrust-accept-btn-handler\').click();')
    m_checkoutDriver.execute_script('document.getElementById(\'InternationalPopupConfirmation\').click();')
    time.sleep(5)
    
    m_watchDriver.get("https://www.masterofmalt.com/#context-login")
    m_checkoutDriver.get("https://www.masterofmalt.com/#context-login")
    time.sleep(5)
    
    m_watchDriver.execute_script('txtLoginEmail.value=\"' + m_userInfoes[0].id + '\";txtLoginPassword.value=\"' + m_userInfoes[0].passwd + '\";document.getElementById(\'MOMBuyButton\').click();')
    m_checkoutDriver.execute_script('txtLoginEmail.value=\"' + m_userInfoes[1].id + '\";txtLoginPassword.value=\"' + m_userInfoes[1].passwd + '\";document.getElementById(\'MOMBuyButton\').click();')
    time.sleep(5)


# ----- New Arrive Products Manage ----- #
def refreshAndGetNewProductIds():    
    logging.info("Refresh page\n")
    m_watchDriver.refresh()
    m_watchDriver.implicitly_wait(15)
    idString = ""
    dataLayer = m_watchDriver.execute_script('var iDs = window.dataLayer; return iDs')
    for data in dataLayer:
        if ("productIDs" in data):
            result = data['productIDs']
            idString = ','.join(map(str, result))
    logging.info("refreshed idString : " + idString)    
    return idString


def getProductInfoes(idString):
    r = requests.get(TRACKING_ADDRESS + idString, headers=HEADERS)
    try:
        ret = json.loads(r.content)
    except:
        if '403' in str(r):
            sendMessage('API Blocked', 2, False)
        else:
            sendMessage('Unknown Error occurred!\n' + str(r), 2, False)
        return
    retString = str(r.content)
    retString = retString.replace("\\","")
    retString = retString.replace("'","")
    retString = retString[1:]
    logging.info("proDuct info : " + retString)
    return retString


# ----- Data Parsing ----- #
def parseNewProductKeys():
    global m_newItmeKeys 
    m_newItmeKeys = config['newProducts']['names'].split('&')
    logging.info("watching New Product List : " + str(m_newItmeKeys))


def parseUserAuthData():
    global m_userInfoes
    m_userInfoes = []

    userIDs = ast.literal_eval(config.get("user", "ID"))
    userPWs = ast.literal_eval(config.get("user", "passwd"))
    if len(userIDs) != len(userPWs) :
        return False

    for i in range(len(userIDs)):
        userInfo(id="",passwd="",)
        m_userInfoes.append(userInfo(id=userIDs[i],passwd=userPWs[i]))
    logging.info(m_userInfoes)
    return True


def parseWachingListProducts():
    global m_watchList
    global m_watchItems
    m_watchList = ""
    m_watchItems = []

    with open(os.getcwd() + '/masterOfMalts.json', 'r', encoding='UTF8') as jsonFile:
        itemData = json.load(jsonFile)
        for item in itemData['itemList']:
            m_watchList = m_watchList + item['code'] + ','
            m_watchItems.append(watchItem(item['code'], item["autoCheckOut"]))
        m_watchList = m_watchList[:-1]
    logging.info("m_watchList : " + m_watchList)


def checkProductInfoes(jsonString):
    jsonData = json.loads(jsonString)
    products = jsonData['products']
    for item in products:
        prodId = item['productID']
        prodName = item['name'].lower()
        avab =  item['available']     
        
        if avab == True and prodId not in m_sentList:
            if str(prodId) in m_lastNewProductIDs:
                for key in m_newItmeKeys :
                    if (key in prodName):
                        sendStockAlarm(False, prodName, prodId)
            else:
                if isSwitchOn(prodId) :
                    checkOutTheItem(prodId)
                sendStockAlarm(True, prodName, prodId)


# ----- Utills  ----- #
def sendMessage(text, sendCount, personal):
    try:
        slackHeaders = {"Authorization": "Bearer "+ config['slack']['token']}
        slackDatas = {"channel": '#' + config['slack']['channel'],"text": text} if personal else {"channel": '#' + config['slack']['personalChannel'],"text": text} 
        for i in range(1,sendCount):
            requests.post("https://slack.com/api/chat.postMessage",
            headers=slackHeaders,
            data=slackDatas)
            time.sleep(0.5)
    except:
        logging.error("### error occur during sendMessage. msg : " + text)


def sendStockAlarm(reStock, name, prodId):
    m_watchDriver.execute_script('AddToBasket(' + str(prodId) + ')') 
    logging.info("checkOutTheItem item : " + str(prodId))
    if reStock:
        text = "###### Re-Stock ######\n"
    else:
        text = "###### NEW STOCK ######\n"
    text = text + name + " Arrived !!\n"
    text = text + "https://www.masterofmalt.com/s/?q=" + name + "&size=n_25_n"
    sendMessage(text, 5, False)
    logging.info(text)
    m_sentList.append(prodId)


def resetDatas():
    m_sentList.clear()
    for info in m_userInfoes:
        info.checkoutAvailable = True
    sendMessage("### Reset Datas ###", 2, False)    


def isSwitchOn(targetId) :
    for item in m_watchItems:
        if item.prodId == targetId :
            return item.autoCheckOut
    return False


def checkOutTheItem(prodId) :
    totalCount = m_checkoutDriver.execute_script('var total = getBasketQuantityTotal(); return total')
    if totalCount == 0 and m_userInfoes[1].checkoutAvailable :
        logging.info("checkOutTheItem item : " + str(prodId))
        m_checkoutDriver.execute_script('AddToBasket(' + str(prodId) + ')') 
    
        m_checkoutDriver.get(CHECKOUT_ADDRESS)
        while True:
            if m_checkoutDriver.find_element("disclaimer-checkbox") :
                break
            else:
                logging.info("Waiting checkout page... ")
                print("finding checkbox")
            time.sleep(0.5)

        m_checkoutDriver.execute_script('document.getElementsByName(\'disclaimer-checkbox\')[1].click()')
        m_checkoutDriver.execute_script('document.body.getElementsByClassName(\'mom-btn mom-btn-large mom-btn-green-alt mom-btn-full-width\')[0].click();')
        sendMessage("##### checkout tried ##### ", 5, True)
        m_userInfoes[1].checkoutAvailable = False
    else :
        text = "###### watch List re-stock, but just add to basket ######\n"
        text = text + ""
        sendMessage(text, 5, True)
    

if __name__ == "__main__":

    parseNewProductKeys()
    parseWachingListProducts()
    if len(m_watchList) == 0 and len(m_newItmeKeys) == 0 :
        print("ERROR: Threr is no item to watch!")
        exit(INVALID_WATCH_TARGET)
    
    parseUserAuthData()
    print(m_userInfoes)
    if len(m_userInfoes) == 0 :
        print("ERROR: There is no user info to use")
        exit(INVALID_USER_INFO)
    
    webObjInit()

    watchingSpan = int(config['etc']['watchingSpan'])
    watchCount = 0
    
    schedule.every().day.at(config['etc']['resetTime']).do(resetDatas)
    schedule.run_pending()
    
    while True:
        watchCount = watchCount + 1    
        if watchCount % watchingSpan == 0:
            sendMessage("### still watching ###", 2, False)
            watchCount = 0

        try:
            idString = refreshAndGetNewProductIds()
            if (m_lastNewProductIDs != idString) :
                sendMessage("### New Item Arrived, Check New List ###", 2, False)
                m_lastNewProductIDs = idString
                jsonString = getProductInfoes(idString)
                logging.info('New Product IDs : ' + idString + '\n')
                checkProductInfoes(jsonString)                
        except:
                sendMessage("### Error occur during get New Products info", 2, False)
                reCreateWebObj()

        try:
            jsonString = getProductInfoes(m_watchList)
            checkProductInfoes(jsonString)
        except:
            sendMessage("### Error occur during get watching products info", 2, False)
            reCreateWebObj()

        time.sleep(random.randrange(30,60))