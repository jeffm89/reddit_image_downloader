import argparse
import logging


from os.path import isdir, isfile
from os import mkdir
from re import match, findall, search
from queue import Queue
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlretrieve

logfile = 'main.log'
log_level = 0

logging.basicConfig(filename=logfile, level=log_level, filemode='w',
                    format='%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info('Logging Started.')

logger.debug('importing praw')
try:
    import praw as praw
    logger.debug('praw imported.')
    from prawcore import exceptions
    logger.debug('praw exceptions imported.')
except ModuleNotFoundError:
    logger.critical('Praw not installed.')
    print('Praw not imported.  Please import and try again.')
    exit(2)

user_string = 'Python:reddit_image_downloader:1.0 (by /u/merchantjeff'
num_dl_threads = 1
download_queue = Queue()
threads = []


def main(lookup_sub, limit, allow_i_album):
    log = logger.getChild('main')
    log.info('Main Started.')

    log.debug('Starting first_run')
    first_run()

    log.debug('Starting Reddit instance...')
    reddit = reddit_instance()
    log.debug('Starting pull_posts')
    posts = pull_posts(reddit, lookup_sub, limit)

    # Check to see if posts match any known format.
    log.debug('Starting url_sorter')
    url_sorter(posts, lookup_sub, allow_i_album)

    print(download_queue.qsize())

    log.info('threads_start Starting...')
    thread_control()
    log.warning('*** Main thread waiting.')
    download_queue.join()
    log.warning('*** Main thread resumed.')


def download_file(i, data):
    name = 'download_file.' + str(i)
    log = logger.getChild(name)
    log.info('Started.')
    root_path = 'data/Images/'
    sub = data[0]
    url = data[1]
    filename = data[2]
    file_directory = root_path + sub
    filepath = root_path + sub + '/' + filename
    if not isdir(file_directory):
        log.debug('dir doesnt exist')
        try:
            mkdir(file_directory)
        except FileExistsError:
            pass
        log.debug('dir created.')
    if not isfile(filepath):
        log.debug('File does not exists.')
        try:
            log.debug(('URL %s, save to %s' % (url, filepath)))
            urlretrieve(url, filepath)
        except FileNotFoundError as err:
            log.exception(err)
        except HTTPError as err:
            log.exception(err)
        except URLError as err:
            log.exception(err)
    else:
        log.debug('File already exists. Skipping...')
    log.info('Completed.')


def worker(i, q):
    name = 'worker.' + str(i)
    log = logger.getChild(name)
    log.info('Started.')
    while True:
        log.info('Cycling.')
        log.debug('Pull next job from queue.')
        b = q.get()
        log.debug('Retrieved from queue: %s.' % b)
        if b is None:
            log.debug('Break.')
            break
        log.info('download_file Starting...')
        download_file(i, b)
        log.debug('Finished.')
        q.task_done()
        log.info('Marked done.')


def thread_control():
    log = logger.getChild('thread_control')
    log.info('Started.')
    for t in range(num_dl_threads):
        t += 1
        log.debug('Starting thread %s.' % t)
        t_worker = Thread(target=worker, args=(t, download_queue))
        t_worker.setDaemon(True)
        t_worker.start()
        threads.append(t)
        log.debug('Started, thread %s' % t)


def url_sorter(url_list, sub, ialbum):
    log = logger.getChild('url_sorter')
    log.info('Started.')
    for url in url_list:
        log.info('Starting reg_ex_matcher')
        reg_ex_matcher(url, sub, ialbum)
    log.info('Completed.')


def reg_ex_matcher(url, sub, ialbum):
    log = logger.getChild('regex_matching')
    log.info('Started.')
    log.debug('Matching %s' % url)
    ireddit = match("(https?)\:\/\/(?:www|\w+)(?:i)?.redd.it\/(\w+.\w{2,3})", url)
    iimgur = match("(https?)\:\/\/(?:www|\w+)(?:i)?.imgur.com\/(\w+\.\w{2,3})", url)
    smugmug = match("(https?)\:\/\/(?:www|\w+).smugmug.com\/(?:\w+)\/(?:[a-zA-Z0-9\-]+)"
                       "\/\d\/(?:\w+\/)?\w+\/([a-zA-Z0-9\-\_\%]+\.\w{3,4})", url)
    imgur = match("(https?)\:\/\/(?:www|)imgur.com\/(\w+)", url)
    redditup = match("(https?)\:\/\/(?:www|)(?:i)\.reddituploads.com\/(\w+)\?.+", url)
    imgur_album = match("(https?)\:\/\/(?:www|)imgur.com\/(?:\w+)\/(\w+)", url)
    tumblr = search("([^/][\d\w\.]+)((?<=(.jpg|.gif)|.png))", url)

    if ireddit:
        log.debug('Matched ireddit.')
        filename = ireddit.group(2)
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))
        download_queue.put([sub, url, filename])

    elif smugmug:
        log.debug('Matched smugmug.')
        filename = smugmug.group(2)
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))

        download_queue.put([sub, url, filename])

    elif redditup:
        log.debug('Matched reddup.')
        ext = '.jpg'
        url = url + ext
        filename = redditup.group(2) + ext
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))
        download_queue.put([sub, url, filename])

    elif imgur_album:
        log.debug('Matched imgur album.')
        if ialbum:
            filename = None
            album_key = imgur_album.group(2)
            fullListURL = "http://imgur.com/a/" + album_key + "/layout/blog"
            try:
                response = urlopen(url=fullListURL)
            except HTTPError as err:
                log.exception(err)
            except URLError as err:
                log.exception(err)
            html = response.read().decode('utf-8')
            imageIDs = findall('.*?{"hash":"([a-zA-Z0-9]+)".*?"ext":"(\.[a-zA-Z0-9]+)".*?', html)
            for i in imageIDs:
                filename = i[0]
                ext = i[1]
                filename_dl = filename + ext
                url = 'http://imgur.com/' + filename_dl
                log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename_dl))
                download_queue.put([sub, url, filename_dl])
        else:
            log.debug('Allow Imgur album is set False.')

    elif imgur:
        log.debug('Matched imgur.')
        ext = '.jpg'
        url = url + ext
        filename = imgur.group(2) + ext
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))
        download_queue.put([sub, url, filename])

    elif iimgur:
        log.debug('Matched iimgur.')
        filename = iimgur.group(2)
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))
        download_queue.put([sub, url, filename])

    elif tumblr:
        log.debug('Matched tumblr.')
        filename = tumblr.group(1)
        log.debug('Adding Sub: %s, URL: %s, File: %s' % (sub, url, filename))
        download_queue.put([sub, url, filename])

    else:
        log.debug('No match')
    log.info('Completed.')


def pull_posts(reddit, sub, limit):
    log = logger.getChild('pull_posts')
    log.info('Started.')
    log.debug('Subreddit: %s Limit: %s' % (sub, limit))
    log.debug('Loading Sub.')
    subreddit = reddit.subreddit(sub)
    log.debug('Loaded.')
    log.debug('Loading posts.')
    submissions = subreddit.top(limit=limit)
    log.debug('Loaded.')
    posts = []
    try:
        for post in submissions:
            log.debug('Pulling ID: %s URL: %s' % (post, post.url))
            posts.append(post.url)
        log.info('Completed.')
        return posts
    except exceptions.Redirect:
        log.warn('Subreddit cannot be found.')
    except exceptions.RequestException:
        log.warn('No Connection.')
        # TODO: Enable wait loop for connection.
        log.error('Exiting.')
        exit(9)


def reddit_instance():
    log = logger.getChild('reddit_instance')
    log.info('Started.')
    credentials_file = 'data/config.txt'
    log.debug('Opening credential file %s.' % credentials_file)
    with open(credentials_file, 'r', )as f:
        log.debug('Success.')
        line = f.read().splitlines()
        cred_id = line[0].split(':')[1]
        log.debug('cred_id. %s' % cred_id)
        cred_secret = line[1].split(':')[1]
        log.debug('cred_secret. %s' % cred_secret)
    log.debug('Credentails imported.')
    log.debug('Starting Reddit instance.')
    reddit = praw.Reddit(client_id=cred_id,
                         client_secret=cred_secret,
                         user_agent=user_string)
    log.info('Completed.')
    return reddit


def args_parser():
    log = logger.getChild('args_parser')
    log.info('Started.')
    parser = argparse.ArgumentParser()
    parser.add_argument('sub', help='Input subreddit for downloading.')
    parser.add_argument('limit', help='Number of submissions attempted for download.', type=int)
    parser.add_argument('-a', '--album', help='Allow Imgur albums', action='store_true')
    args = parser.parse_args()
    lookup_sub = args.sub
    limit = args.limit
    allow_i_album = args.album
    return lookup_sub, limit, allow_i_album


def first_run():
    log = logger.getChild('first_run')
    log.info('Started.')
    if not isdir('data'):
        log.debug('data folder doesn\'t exist.')
        mkdir('data')
        log.debug('data folder created.')
    if not isfile('data/config.txt'):
        log.debug('config file doesn\'t exist.')
        fields = ['cred_id:', 'cred_secret:']
        with open('data/config.txt', 'a+')as f:
            for i in fields:
                f.write(i+'\n')
        log.error('No credentials.')
        exit(9)
    if not isdir('data/Images'):
        log.debug('Images folder doesn\'t exist.')
        mkdir('data/Images')
        log.debug('Images folder created.')


if __name__ == '__main__':
    logger.debug('Starting args_parser')
    lookup_sub, limit, allow_i_album = args_parser()
    main(lookup_sub, limit, allow_i_album)
