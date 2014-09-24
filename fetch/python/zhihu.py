#coding: utf-8

import time, re, sys
import db
import timer

# logic

FETCH_ING = 1
FETCH_OK = 2
FETCH_FAIL = 3

from html.parser import HTMLParser

class AnswersParser(HTMLParser):
    def init(self):
        self.in_zh_pm_page_wrap = False
        self.in_zh_profile_answer_list = False
        self.question_link_list = []

    def handle_starttag(self, tag, attrs):
        # print("Encountered a start tag:", tag, attrs)
        attrs = dict(attrs)
        # print(attrs)
        if 'id' in attrs and attrs['id'] == 'zh-pm-page-wrap':
            # print('find #zh-pm-page-wrap')
            self.in_zh_pm_page_wrap = True
        if self.in_zh_pm_page_wrap and tag == 'img':
            # print("Encountered a start tag:", tag, attrs)
            if 'class' in attrs and attrs['class'] == 'zm-profile-header-img zg-avatar-big zm-avatar-editor-preview':
                # print('find img.')
                self.avatar = attrs['src']
                return False

        if 'id' in attrs and attrs['id'] == 'zh-profile-answer-list':
            self.in_zh_profile_answer_list = True
        if self.in_zh_profile_answer_list and tag == 'a':
            # print("Encountered a start tag:", tag, attrs)
            if 'class' in attrs and attrs['class'] == 'question_link':
                self.question_link_list.append(attrs['href'])
                return False

class ZhihuParser(HTMLParser):
    def init(self):
        self.in_zh_question_answer_wrap = False
        self.in_zh_question_title = False
        self.in_zh_question_detail = False
        self.in_count = False
        self.in_title = False
        self.in_detail = False
        self.in_content = False
        self.detail = ''
        self.content = ''
        self.stack = []

    def handle_starttag(self, tag, attrs):
        # print("Start tag:", tag, attrs)
        attrs = dict(attrs)

        if self.in_zh_question_answer_wrap and not self.in_content and tag == 'div':
            if 'class' in attrs and attrs['class'] == 'question_link':
                class_list = attrs['class'].split(' ')
                if 'zm-editable-content' in class_list:
                    print('we find div.zm-editable-content')
                    self.in_content = True
                    self.stack = []
                return False
        if 'id' in attrs and attrs['id'] == 'zh-question-answer-wrap':
            self.in_zh_question_answer_wrap = True
        if self.in_zh_question_answer_wrap and tag == 'span':
            # print("Encountered a start tag:", tag, attrs)
            if 'class' in attrs and attrs['class'] == 'count':
                self.in_count = True

        if self.in_zh_question_title and tag == 'a':
            # print('#zh-question-title a')
            self.in_title = True
        if 'id' in attrs and attrs['id'] == 'zh-question-title':
            self.in_zh_question_title = True
            # print('in_zh_question_title')

        if self.in_zh_question_detail and not self.in_detail and tag == 'div':
            # print('#zh-question-detail div')
            self.in_detail = True
            self.stack = []
        if 'id' in attrs and attrs['id'] == 'zh-question-detail':
            self.in_zh_question_detail = True
            # print('#zh-question-detail')

        if self.in_detail or self.in_content:
            self.stack.append(tag)
            # print('stack',self.stack)

    def handle_endtag(self, tag):
        # print("End tag :", tag)
        if self.in_detail or self.in_content:
            if len(self.stack) == 0:
                self.in_detail = False
                self.in_content = False
            else:
                while True:
                    pop_tag = self.stack.pop()
                    if pop_tag != tag:
                        if pop_tag in ['br', 'hr', 'img']:
                            continue
                        else:
                            print(self.stack)
                            raise Exception('pop '+pop_tag+', but end '+tag)
                    break
    def handle_data(self, data):
        if self.in_count:
            self.count = data
            return False
        if self.in_title:
            self.title = data
            return False
        if self.in_detail:
            self.detail += data
        if self.in_content:
            self.content += data


def slog(msg):
    pass

def get_avatar_src(content):
    parser = AnswersParser()
    parser.init()
    parser.feed(content.decode())
    return parser.avatar

data = {}
def get_average(n, tag = 'default'):
    if tag not in data:
        data[tag] = {'cnt': 0, 'sum': 0}
    data[tag]['cnt'] += 1
    data[tag]['sum'] += n
    return data[tag]['sum']/data[tag]['cnt']

def saveUser(username, nickname):
    u = get_table('user')
    update = {'name': username, 'nick_name': nickname}
    where = {'name': username}
    rs = u.update(where, {'set': update}, {'upsert': true})
    if (not rs['ok']):
        print(rs['err'])
    return rs

def getNotFetchedUserCount():
    cursor = db.connect().cursor()
    cursor.execute('SELECT COUNT(*) FROM user WHERE fetch=0')
    row = cursor.fetchone()
    return row[0]

def getNotFetchedUserName():
    cursor = db.connect().cursor()
    cursor.execute('SELECT `name` FROM `user` WHERE `fetch`=0 LIMIT 1')
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]

def update_table(table, args, where):
    connect = db.connect()
    cursor = connect.cursor()
    keys = args.keys()
    key_str = ','.join(['`{}`=?'.format(key) for key in keys])
    values = [str(e) for e in list(args.values())]
    where_str = ','.join(['`{}`=?'.format(key) for key in where.keys()])
    where_values = [str(e) for e in list(where.values())]
    values.append(*where_values)
    cursor.execute('UPDATE `{0}` SET {1} WHERE {2}'.format(table, key_str, where_str), tuple(values))
    return connect.commit()


def update_user_by_name(username, args):
    return update_table('user', args, {'name': username})

def getUids():
    u = get_table('user')
    where = {
        'has_fetch': {'exists': false},
        'name': {'exists': true},
    }
    c = u.find(where).fields({'name': true})
    ret = []
    for v in c:
        ret.append(v['name'])
    return ret

def get_answer_link_list(content):
    parser = AnswersParser()
    parser.init()
    parser.feed(content.decode())
    return parser.question_link_list

def insert_table(table, args):
    connect = db.connect()
    cursor = connect.cursor()
    keys = args.keys()
    key_str = ','.join(['`{}`'.format(key) for key in keys])
    value_str = ','.join(['?' for key in keys])
    values = [str(e) for e in list(args.values())]
    sql_tpl = 'INSERT INTO `{}` ({}) VALUES ({})'
    sql = sql_tpl.format(table, key_str, value_str)
    print(sql_tpl.format(table, key_str, ','.join(["'{}'".format(e) for e in list(args.values())])))
    cursor.execute(sql, tuple(values))
    connect.commit()
    return cursor.lastrowid

def insert_user(args):
    user_id = insert_table('user', args)
    print('user_id', user_id)
    return user_id

def _saveAnswer(aid, qid, username, content, vote):
    cursor = db.connect().cursor()
    sql = 'SELECT id FROM user WHERE name=? LIMIT 1'
    print(sql, username)
    cursor.execute(sql, (username,))
    row = cursor.fetchone()
    if row is None:
        raise Exception('no user {}'.format(username))
    user_id = row[0]
    args = {'id': aid, 'q_id': qid, 'user_id': user_id, 'text': content, 'vote': vote, 'fetch_time': int(time.time())}
    return insert_table('answer', args)

def parse_answer_pure(content):
    with open('last.html', 'w') as f:
        f.write(content.decode())
    parser = ZhihuParser()
    parser.init()
    parser.feed(content.decode())
    return parser.title, parser.detail, parser.content, parser.count

def saveAnswer(conn, username, answer_link_list):
    regex = re.compile(r'^/question/(\d+)/answer/(\d+)')
    # conn = http.client.HTTPConnection('www.zhihu.com')

    success_ratio = None
    avg = None
    for url in answer_link_list:
        matches = regex.search(url)
        if matches is None:
            raise Exception('url not good')
        qid = matches.group(1)
        aid = matches.group(2)
        print("\t{}".format(url), end='')
        sys.stdout.flush()
        timer.timer('saveAnswer')
        conn.request("GET", url)
        response = conn.getresponse()
        if response is None:
            raise Exception('no response')
        code = response.status
        print("\t[{}]".format(code), end='')
        if code != 200: # fail fast
            print("\tfail\n")
            slog("url [code] error")
            success_ratio = get_average(0, 'success_ratio')
            continue
        else:
            success_ratio = get_average(1, 'success_ratio')
        content = response.read()
        t = timer.timer('saveAnswer')
        avg = int(get_average(t))
        print("\t{} ms".format(t))
        if len(content) == 0:
            print("content is empty\n")
            slog("url [code] empty")
            return False
        question, descript, content, vote = parse_answer_pure(content)
        slog("url [code] ^vote\tquestion")

        saveQuestion(qid, question, descript)

        _saveAnswer(aid, qid, username, content, vote)
    if success_ratio is not None and avg is not None:
        success_ratio = int(success_ratio*100)
        print("\tAvg: {} ms\tsuccess_ratio: {}%\n".format(avg, success_ratio))

def setFetched(qid):
    raise Exception('setFetched')
    # q = self::getTable()
    # update = array('has_fetch': true)
    # where = array('id': qid)
    # rs = q->update(where, array('set': update))
    # if (!rs['ok']) {
    #     echo basename(__FILE__).':'.__LINE__.' '.rs['err']."\n"
    # }
    return rs

def saveQuestion(qid, question, description):
    args = {'id': qid, 'title': question, 'description': description, 'fetch_time': int(time.time())}
    return insert_table('question', args)

def getIds():
    raise Exception('getIds')
    # c = self::getTable()
    # where = array('has_fetch': array('exists': false))
    # c = c->find(where)->fields(array('id': true))
    # ret = array()
    # foreach (c as v) {
    #     ret[] = v['id']
    # }
    return ret

def get_page_num(content):
    matches = re.findall(r'<a href="\?page=(\d+)', content.decode())
    if matches is None:
        return 1
    # print(matches)
    return max([int(i) for i in matches])
