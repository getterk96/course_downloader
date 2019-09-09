import requests
from courses import courses
import queue
import threading
import os, re, json

storage_dir = '/Users/gaojinghan/Desktop/BachelorCourses/'
threads = 8
headers = {
    'Cookie': '!Proxy!PHPSESSID=savo4dejlgd1nmla6v1q1dsk83; JSESSIONID=A74B72298E4F3F102F3F7E2285540BB3.wlxt20182',
    'Host': 'learn.tsinghua.edu.cn',
    'Referer': 'http://learn.tsinghua.edu.cn/f/wlxt/kj/wlkc_kjxxb/student/beforePageList?wlkcid=2015-2016-126ef84e7689a14e101689a74ee6f509a&sfgk=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'}


class CourseFileDownloader(threading.Thread):
    def __init__(self, queue, num):
        threading.Thread.__init__(self)
        self.queue = queue
        self.num = num

    def run(self):
        while self.queue.qsize() > 0:
            index = self.queue.get()
            print("Thread-{} working on {}".format(self.num, index['name']))
            file_id = index['id']
            r = requests.get(
                f'http://learn.tsinghua.edu.cn/b/wlxt/kj/wlkc_kjxxb/student/downloadFile?sfgk=0&wjid={file_id}',
                headers=headers)
            with open(os.path.join(index['path'],
                                   index['name'] + re.search(r'\.(.*?)\"', r.headers['Content-Disposition'],
                                                             re.I).group()[:-1]), "wb") as f:
                f.write(r.content)
            index_dir = os.path.join(os.path.curdir, f'index-{self.num - 1}.txt')
            with open(index_dir, 'r') as f:
                j = json.load(f)
            j['current_in'] += 1
            with open(index_dir, 'w') as f:
                json.dump(j, f)


def download_paper():
    file_queues = [queue.Queue() for i in range(threads)]
    if os.path.exists('index-0.txt'):
        for idx, file_queue in enumerate(file_queues):
            with open(f'index-{idx}.txt', 'r') as f:
                j = json.load(f)
                for i, item in enumerate(j['data']):
                    if i >= j['current_in']:
                        file_queue.put(item)
    else:
        indexes = [[] for i in range(threads)]
        for course in courses:
            idx = 0
            path = os.path.join(storage_dir, course['kcm'])
            if not os.path.exists(path):
                os.mkdir(path)
            course_id = course['wlkcid']
            r = requests.get(f'http://learn.tsinghua.edu.cn/b/wlxt/kj/wlkc_kjflb/student/pageList?wlkcid={course_id}',
                             headers=headers)
            course_columns = [{'name': row['bt'], 'id': row['kjflid']} for row in r.json()['object']['rows']]
            for course_column in course_columns:
                column_path = os.path.join(path, course_column['name'])
                if not os.path.exists(column_path):
                    os.mkdir(column_path)
                course_column_id = course_column['id']
                r = requests.get(
                    f'http://learn.tsinghua.edu.cn/b/wlxt/kj/wlkc_kjxxb/student/kjxxb/{course_id}/{course_column_id}',
                    headers=headers)
                for object in r.json()['object']:
                    file = {
                        'name': object[1],
                        'path': column_path,
                        'id': object[-3]
                    }
                    indexes[idx % threads].append(file)
                    file_queues[idx % threads].put(file)
                    idx += 1
        for idx, index in enumerate(indexes):
            with open(f'index-{idx}.txt', 'w') as f:
                json.dump({'current_in': 0, 'data': index}, f)

    my_downloaders = []
    for i in range(threads):
        my_downloaders.append(CourseFileDownloader(file_queues[i], i + 1))

    for downloader in my_downloaders:
        downloader.start()

    for downloader in my_downloaders:
        downloader.join()


download_paper()
