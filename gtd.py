#! ../.venv/bin/python
import os
import sys
import psutil
from dotenv import load_dotenv
import log
import time
import Pyro5.api
from queue import Queue
import subprocess
import multiprocessing
import threading

# Logger setup
LOGGER = log.setup_custom_logger('gtd')

# Daemon main and secondary loops variables
DAEMON_RUN_LOOP = True
pyro_server_process = multiprocessing.Process()
worker_process = multiprocessing.Process()

# Getting environment variables
QUERIES_PER_SEC = os.environ.get('QUERIES_PER_SEC')
if not QUERIES_PER_SEC:
    load_dotenv()
    QUERIES_PER_SEC = int(os.getenv('QUERIES_PER_SEC'))

DAEMON_TIMEOUT_MINUTES = int(os.getenv('DAEMON_TIMEOUT_MINUTES'))


def start_pyro_server() -> None:
    """ Function that can be used to start a pyro server """
    subprocess.run('python -m Pyro5.nameserver', shell=True, stdout=subprocess.DEVNULL)


def stop_processes(parent_pid) -> None:
    """ Function that stops the secondary processes """
    parent = psutil.Process(parent_pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()


class TranslateQueue(Queue):
    """
    This is the exposed queue class which will be used to store the translation lines and can be accessed by external
    sources and the worker
    """

    def __init__(self):
        super().__init__()
        self.translated_lines = Queue()


class GTransAPI:
    """ This object is used to handle the api calls for the worker """

    def __init__(self):
        self.calls_per_second = 0
        self.timer = Timer()

    def call(self, phrase):
        if not self.timer.is_started:
            self.timer.start()

        elapsed_time = self.timer.elapsed_time_now()
        if self.calls_per_second == QUERIES_PER_SEC and elapsed_time < 1:
            time.sleep(1 - elapsed_time)
            self.timer.restart()
            # api call for phrase translation
            self.calls_per_second = 1
        else:
            self.calls_per_second += 1
            # api call for phrase translation


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
        self.current_threads = []
        self.timer = Timer()

    def run(self):
        self.timer.start()
        while True:
            time.sleep(2)
            print(f'Looping though the worker, tqueue empty = {self.tqueue.empty()}')
            while not self.tqueue.empty():
                self.start_trans_threads()

            if self.current_threads:
                self.join_trans_threads()

            # If worker is idle for more than DAEMON_TIMEOUT_MINUTES, the daemon will be closed
            if self.timer.elapsed_minutes_now() > DAEMON_TIMEOUT_MINUTES:
                LOGGER.info('DAEMON IDLE TIMEOUT REACHED...')
                stop_daemon()
                break

    def start_trans_threads(self):
        # start thread for each queue
        phrase = self.tqueue.get()
        t = threading.Thread()
        self.tqueue.task_done()

        # append thread to current threads
        self.current_threads.append(t)

    def join_trans_threads(self):
        for thread in self.current_threads:
            thread.join()
            result = 0
            self.tqueue.translated_lines.put(result)
        # reset current threads
        self.current_threads = []
        # reset timer
        self.timer.restart()

    def threads_count(self):
        return len(self.current_threads)


def stop_daemon():
    """ This function is made to clean up when the daemon should stop """
    stop_processes(pyro_server_process.pid)
    LOGGER.info('Translation Daemon will stop...')
    global DAEMON_RUN_LOOP
    DAEMON_RUN_LOOP = False
    os._exit(1)


def daemon_loop_condition():
    print('called by main loop...')
    return DAEMON_RUN_LOOP


def main():
    # Run pyro server
    global pyro_server_process
    pyro_server_process = multiprocessing.Process(target=start_pyro_server, daemon=True)
    pyro_server_process.start()

    # Creating pyro daemon and register/expose the queue
    daemon = Pyro5.server.Daemon()
    ns = Pyro5.api.locate_ns()

    trans_queue = TranslateQueue()
    uri = daemon.register(trans_queue)
    ns.register("translate.queue", uri)

    # Create GTransAPI Translator
    translator = GTransAPI()

    # Start worker
    global worker_process
    worker = TranslateWorker(trans_queue, translator)
    worker_process = multiprocessing.Process(target=worker.run, daemon=True)
    worker_process.start()

    # Run pyro daemon
    print(f'Translation daemon started, throttling at {QUERIES_PER_SEC} queries/second.')
    daemon.requestLoop(daemon_loop_condition)


if __name__ == '__main__':
    main()
