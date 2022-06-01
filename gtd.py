#! .venv/bin/python3
import logging
import multiprocessing
import os
import subprocess
import time
from multiprocessing import Queue
import multiprocessing.queues

import Pyro5.api
import psutil
import six
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate

import log

# Logger setup
LOGGER = log.setup_custom_logger('gtd')

# Daemon main and secondary loops variables
DAEMON_RUN_LOOP = multiprocessing.Value('i', 1)
pyro_server_process = multiprocessing.Process()

# Getting environment variables
QUERIES_PER_SEC = os.environ.get('QUERIES_PER_SEC')
load_dotenv()
if not QUERIES_PER_SEC:
    QUERIES_PER_SEC = int(os.getenv('QUERIES_PER_SEC'))

DAEMON_TIMEOUT_MINUTES = int(os.getenv('DAEMON_TIMEOUT_MINUTES'))

if not int(os.getenv('DEBUG')):
    LOGGER.setLevel(logging.INFO)


def start_pyro_server() -> None:
    """ Function that can be used to start a pyro server """
    # killing the process on the port 9090 where the pyro server will start
    subprocess.run('fuser -k 9090/tcp', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # start the pyro server
    subprocess.run('.venv/bin/python3.9 -m Pyro5.nameserver', shell=True, stdout=subprocess.DEVNULL)


def stop_processes(parent_pid) -> None:
    """ Function that stops the secondary processes """
    parent = psutil.Process(parent_pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()


@Pyro5.api.expose
class TranslateQueue(multiprocessing.queues.Queue):
    """
    This is the exposed queue class which will be used to store the translation lines and can be accessed by external,
    internal objects and different processes.
    """

    def __init__(self):
        ctx = multiprocessing.get_context()
        super().__init__(ctx=ctx)
        self.translated_lq = Queue()

    def put_task(self, item: dict):
        return self.put(item)

    def bq_size(self):
        return self.qsize

    def bq_not_empty(self):
        return not self.empty()

    def translated_lq_empty(self):
        return self.translated_lq.empty()

    def translated_lq_size(self):
        return self.translated_lq.qsize()

    def get_translated_lines(self):
        if not self.translated_lq.empty():
            send_back_results = []
            while not self.translated_lq.empty():
                send_back_results.append(self.translated_lq.get())
            return send_back_results
        return None


class GTransAPI:
    """ This object is used to handle the api calls for the worker """

    def __init__(self, translate_queue: TranslateQueue):
        self.tqueue = translate_queue
        self.translate_client = translate.Client()
        self.calls_per_second = 0
        self.timer = Timer()

    def call_trans(self, lock: multiprocessing.Lock, phrase: str, targ_lang: str):
        """ Method used to translate the given phrase within the api load restrictions """
        LOGGER.debug(f'P_obj: {phrase} is of type: {type(targ_lang)}')
        if not self.timer.is_started:
            self.timer.start()
        lock.acquire()
        elapsed_time = self.timer.elapsed_time_now()
        if self.calls_per_second == QUERIES_PER_SEC and elapsed_time < 1:
            time.sleep(1 - elapsed_time)
            self.timer.restart()
            self.calls_per_second = 1
            translated = self.translate_text(phrase, targ_lang)
        else:
            self.calls_per_second += 1
            translated = self.translate_text(phrase, targ_lang)

        self.tqueue.translated_lq.put(translated)
        lock.release()
        return translated

    def translate_text(self, text: str, targ_lang: str):
        """Translates text into the target language.
        Target must be an ISO 639-1 language code.
        See https://g.co/cloud/translate/v2/translate-reference#supported_languages
        """

        if isinstance(text, six.binary_type):
            text = text.decode("utf-8")

        # Text can also be a sequence of strings, in which case this method
        # will return a sequence of results for each text.
        result = self.translate_client.translate(text, target_language=targ_lang)
        return result["translatedText"]


class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""


class Timer:
    """ Object that works as timer to monitor the worker """

    def __init__(self):
        self._start_time = None
        self.is_started = False

    def start(self):
        if self.is_started:
            raise TimerError(f"Timer is running. Use .stop() to stop it")

        self.is_started = True
        self._start_time = time.perf_counter()

    def stop(self):
        if not self.is_started:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        self._start_time = None
        self.is_started = False
        print(f"Elapsed time: {self.elapsed_time_now():0.4f} seconds")

    def restart(self):
        self._start_time = time.perf_counter()

    def elapsed_time_now(self):
        return time.perf_counter() - self._start_time

    def elapsed_minutes_now(self):
        return self.elapsed_time_now() / 60


class TranslateWorker:
    """ This worker class will handle the threads and the load of the api """

    def __init__(self, translate_queue: TranslateQueue, translator: GTransAPI):
        self.tqueue = translate_queue
        self.translator = translator
        self.timer = Timer()
        self.current_processes = []

    def run(self):
        self.timer.start()
        while True:
            LOGGER.debug(f'Looping though the worker, tqueue empty = {self.tqueue.empty()}')
            while not self.tqueue.empty():
                t_item = self.tqueue.get()
                self.start_trans_subprocs(t_item)

            # If worker is idle for more than DAEMON_TIMEOUT_MINUTES, the daemon will be closed
            if self.timer.elapsed_minutes_now() > DAEMON_TIMEOUT_MINUTES:
                LOGGER.info('DAEMON IDLE TIMEOUT REACHED...')
                stop_daemon()
                break

    def start_trans_subprocs(self, trans_item: dict):
        texts_list = trans_item.get('text')
        language = trans_item.get('language')
        lock = multiprocessing.Lock()

        # start a subprocess for each item in text
        for phrase in texts_list:
            subp = multiprocessing.Process(target=self.translator.call_trans, args=(lock, phrase, language),
                                           daemon=True)
            self.current_processes.append(subp)
            subp.start()

        # wait to finish the execution of each process
        for p in self.current_processes:
            p.join()

        # reset variables
        self.current_processes = []
        self.timer.restart()


def stop_daemon():
    """ This function is made to clean up when the daemon should stop """
    stop_processes(pyro_server_process.pid)
    LOGGER.info('Translation Daemon will stop...')
    DAEMON_RUN_LOOP.value = 0


def daemon_loop_condition():
    """
    This function is used to control the daemon main loop.
    returns: 1 if the daemon main loop should run
    returns: 0 if the daemon main loop should stop
    """
    return DAEMON_RUN_LOOP.value


def main():
    # Run pyro server in separate process
    global pyro_server_process
    pyro_server_process = multiprocessing.Process(target=start_pyro_server, daemon=True)
    pyro_server_process.start()

    # Creating pyro daemon and register/expose the translation queue
    daemon = Pyro5.server.Daemon()
    ns = Pyro5.api.locate_ns()

    trans_queue = TranslateQueue()
    uri = daemon.register(trans_queue)
    ns.register("translate.queue", uri)

    # Creating GTransAPI Translator
    translator = GTransAPI(trans_queue)

    # Start translation worker in a separate process
    worker = TranslateWorker(trans_queue, translator)
    worker_process = multiprocessing.Process(target=worker.run)
    worker_process.start()

    # Run pyro daemon in the main thread
    print(f'Translation daemon started, throttling at {QUERIES_PER_SEC} queries/second.')
    daemon.requestLoop(daemon_loop_condition)
    worker_process.terminate()


if __name__ == '__main__':
    main()
