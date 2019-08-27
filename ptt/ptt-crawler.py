# coding=utf-8
import requests
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup

rs = requests.session()

boardsFileName = 'boards.txt';

#reload(sys)
#sys.setdefaultencoding('utf8')


def over18(board):
    res = rs.get('https://www.ptt.cc/bbs/' + board + '/index.html')
    # 先檢查網址是否包含'over18'字串 ,如有則為18禁網站
    if (res.url.find('over18') > -1):
        #       print ("18禁網頁")
        load = {
            'from': '/bbs/' + board + '/index.html',
            'yes': 'yes'
        }
        res = rs.post('https://www.ptt.cc/ask/over18', data=load)
        return BeautifulSoup(res.text, 'html.parser')
    return BeautifulSoup(res.text, 'html.parser')


def getPageNumber(content):
    startIndex = content.find('index')
    endIndex = content.find('.html')
    pageNumber = content[startIndex + 5: endIndex]
    return pageNumber


def crawler(url_list, boardName):
    count = 0
    total = len(url_list)
    # 開始爬網頁
    while url_list:
        try:
            url = url_list.pop(0)
            res = rs.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
            if (soup.title.text.find('Service Temporarily') > -1):
                url_list.append(url)
                time.sleep(1)
            else:
                count += 1
                for r_ent in soup.find_all(class_="r-ent"):
                    # 先得到每篇文章的篇url
                    link = r_ent.find('a')
                    if (link):
                        # 確定得到url
                        URL = 'https://www.ptt.cc' + link['href']
                        # 避免被認為攻擊網站
                        time.sleep(0.1)
                        # 開始爬文章內容
                        parseGos(URL, boardName)
                print("download: " + boardName + " " + str(100 * count / total) + " %")
        except Exception as e:
            time.sleep(1)
            print("Exception: " + url)
            print(e)
        else:
            # 避免被	認為攻擊網站
            time.sleep(0.5)


def checkFormat(soup, class_tag, data, index, link):
    # 避免有些文章會被使用者自行刪除 標題列 時間  之類......
    try:
        content = soup.select(class_tag)[index].text
    except Exception as e:
        # print 'checkFormat error URL',link
        # print 'checkFormat:',str(e)
        content = "no " + data
    return content


def parseGos(link, boardName):
    res = rs.get(link)
    soup = BeautifulSoup(res.text, 'html.parser')

    # author 文章作者
    # author  = soup.select('.article-meta-value')[0].text
    author = checkFormat(soup, '.article-meta-value', 'author', 0, link)
    # print 'author:',author
    ArticleId = link.replace('https://www.ptt.cc/bbs/' + boardName + '/', '')
    ArticleId = ArticleId.replace('.html', '')
    # title 文章標題
    # title = soup.select('.article-meta-value')[2].text
    title = checkFormat(soup, '.article-meta-value', 'title', 2, link)
    # print 'title:',title

    # date 文章日期
    # date = soup.select('.article-meta-value')[3].text
    date = checkFormat(soup, '.article-meta-value', 'date', 3, link)
    # print 'date:',date

    # content  文章內文
    try:
        content = soup.find(id="main-content")
        [s.extract() for s in content.select('div.article-metaline')]
        [s.extract() for s in content.select('div.article-metaline-right')]
        content = content.text
        target_content = u'※ 發信站: 批踢踢實業坊(ptt.cc),'
        content = content.split(target_content)[0]
        main_content = content.replace('\n', '  ')
    # print 'content:',main_content

    except Exception as e:
        main_content = 'main_content error'
    # print 'main_content error URL',link
    # print 'main_content error:',str(e)

    # message 推文內容
    num, g, b, n, message = 0, 0, 0, 0, {}

    for tag in soup.select('div.push'):
        try:
            # push_tag  推文標籤  推  噓  註解(→)
            push_tag = tag.find("span", {'class': 'push-tag'}).text
            # print "push_tag:",push_tag

            # push_userid 推文使用者id
            push_userid = tag.find("span", {'class': 'push-userid'}).text
            # print "push_userid:",push_userid

            # push_content 推文內容
            push_content = tag.find("span", {'class': 'push-content'}).text
            push_content = push_content[1:]
            # print "push_content:",push_content

            # push-ipdatetime 推文時間
            push_ipdatetime = tag.find("span", {'class': 'push-ipdatetime'}).text
            push_ipdatetime = push_ipdatetime.rstrip()
            # print "push-ipdatetime:",push_ipdatetime

            num += 1
            message[num] = {"狀態": push_tag, "留言者": push_userid, "留言內容": push_content, "留言時間": push_ipdatetime}
            # 計算推噓文數量 g = 推 , b = 噓 , n = 註解
        except Exception as e:
            print(e)

    d = {"a_ID": ArticleId, "b_作者": author, "c_標題": title, "d_日期": date, "e_內文": main_content, "f_推文": message}
    # print  d
    json_data = json.dumps(d, ensure_ascii=False, indent=4, sort_keys=True) + ','
    store(json_data, boardName)


def store(data, boardName, encoding="utf-8"):
    with open(boardName, 'a', encoding="utf-8") as f:
        f.write(data)


def loopFile():
    fileList = open(boardsFileName, 'r', encoding="utf-8")
    boards = fileList.readlines()

    if (len(boards) > 0):
        execute(boards[0].replace('\n', ''))
        fileList.close()
        with open(boardsFileName, 'r', encoding="utf-8") as fin:
            data = fin.read().splitlines(True)
        # print(data)
        with open(boardsFileName, 'w', encoding="utf-8") as fout:
            fout.writelines(data[1:])
        time.sleep(3)
        return loopFile()
    print("done")


def execute(boardName):
    soup = over18(boardName)
    # 得到本看板全部的index數量
    ALLpageURL = soup.select('.btn.wide')[1]['href']
    ALLpage = int(getPageNumber(ALLpageURL)) + 1

    index_list = []

    for index in range(ALLpage, 0, -1):
        page_url = 'https://www.ptt.cc/bbs/' + boardName + '/index' + str(index) + '.html'
        index_list.append(page_url)
        print(page_url)

    # erase text
    open(boardName, 'w', encoding="utf-8").close()

    store('[\n', boardName)
    crawler(index_list, boardName)

    # 手動串接避免memoryError
    #	with open(fileName, 'r', encoding="utf-8") as f:
    #		content = f.read()
    #	with open(fileName, 'w', encoding="utf-8") as f:
    #		f.write( content[:-1] + "\n]" )
    print(boardName + " crawling completed")


if __name__ == "__main__":
    loopFile()
# execute('NBA')
