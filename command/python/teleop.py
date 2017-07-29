import curses
import time
import queue
import threading

import pygame
from pygame.locals import *

from common import *
from listener import decodeOrder

UP = (1,0)
LEFT = (0,1)
RIGHT = (0,-1)
DOWN = (-1,0)
STOP = (0,0)
KEY_CODE_SPACE = 32

MAX_SPEED = 100
MAX_TURN = 45
STEP_SPEED = 2
STEP_TURN = 4

moveBindings = {
                curses.KEY_UP: UP,
                curses.KEY_LEFT: LEFT,
                curses.KEY_RIGHT: RIGHT,
                curses.KEY_DOWN: DOWN
                }

moveBindingsGame = {
                K_UP: UP,
                K_LEFT: LEFT,
                K_RIGHT: RIGHT,
                K_DOWN: DOWN
                }

exit_signal = False
n_received_semaphore = threading.Semaphore(4)
serial_lock = threading.Lock()
command_queue = queue.Queue()

class CommandThread(threading.Thread):
    def __init__(self, serial_file, command_queue):
        threading.Thread.__init__(self)
        self.deamon = True
        self.serial_file = serial_file
        self.command_queue = command_queue

    def run(self):
        while not exit_signal:
            n_received_semaphore.acquire()
            if exit_signal:
                break
            try:
                order, param = self.command_queue.get_nowait()
            except queue.Empty:
                time.sleep(1/30)
                n_received_semaphore.release()
                continue

            with serial_lock:
                sendOrder(self.serial_file, order.value)
                print("Sent {}".format(order))
                if order == Order.MOTOR:
                    writeOneByteInt(self.serial_file, param)
                elif order == Order.SERVO:
                    writeTwoBytesInt(self.serial_file, param)
            time.sleep(1/30)

class ListenerThread(threading.Thread):
    def __init__(self, serial_file):
        threading.Thread.__init__(self)
        self.deamon = True
        self.serial_file = serial_file

    def run(self):
        while not exit_signal:
            bytes_array = self.serial_file.read(1)
            if not bytes_array:
               time.sleep(1/30)
               continue
            byte = bytes_array[0]
            with serial_lock:
               if Order(byte) == Order.RECEIVED:
                   n_received_semaphore.release()
               decodeOrder(self.serial_file, byte)


class Interface:
    def __init__(self, stdscr, lines=10):
        self._screen = stdscr
        self._screen.nodelay(True)
        # Reset cursor
        curses.curs_set(0)
        self._num_lines = lines

    def readKey(self):
        keycode = self._screen.getch()
        return keycode if keycode != -1 else None

    def clear(self):
        self._screen.clear()

    def writeLine(self, line_num, message):
        if line_num < 0 or line_num >= self._num_lines:
            raise ValueError('line_num out of bounds')
        height, width = self._screen.getmaxyx()
        y = (height // self._num_lines) * line_num
        x = 10
        for text in message.split('\n'):
            text = text.ljust(width)
            self._screen.addstr(y, x, text)
            y += 1

    def refresh(self):
        self._screen.refresh()

def publish(interface, speed, turn, info):
    interface.clear()
    interface.writeLine(2, 'Linear: {:.2f}, Angular: {:.2f}'.format(speed, turn))
    interface.writeLine(3, 'Use arrow keys to move, space to stop, q or CTRL-C to exit.')
    interface.writeLine(4, 'space key, k : force stop ---  anything else : stop smoothly')
    interface.writeLine(5, info)
    interface.refresh()

def control(x, theta, control_speed, control_turn):
    target_speed = MAX_SPEED * x
    target_turn = MAX_TURN * theta
    if target_speed > control_speed:
        control_speed = min(target_speed, control_speed + STEP_SPEED)
    elif target_speed < control_speed:
        control_speed = max(target_speed, control_speed - STEP_SPEED)
    else:
        control_speed = target_speed

    if target_turn > control_turn:
        control_turn = min(target_turn, control_turn + STEP_TURN)
    elif target_turn < control_turn:
        control_turn = max(target_turn, control_turn - STEP_TURN)
    else:
        control_turn = target_turn
    return control_speed, control_turn

# stdscr: main window
def main(stdscr):
    interface = Interface(stdscr)
    x, theta, status, count = 0, 0, 0, 0
    control_speed, control_turn = 0, 0
    start_time = time.time()
    counter = 0
    while True:
        keycode = interface.readKey()
        counter += 1
        info = "{:.2f} fps".format(counter/(time.time()-start_time))

        publish(interface, control_speed, control_turn, info)
        if keycode in moveBindings.keys():
            x, theta = moveBindings[keycode]
            count = 0
        elif keycode == ord('k') or keycode == KEY_CODE_SPACE:
                x, theta = 0, 0
                control_speed, control_turn = 0, 0
        elif keycode == ord('q'):
            break
        else:
            count += 1
            if count > 4:
                x, theta = 0, 0

        # Smooth control
        control_speed, control_turn = control(x, theta, control_speed, control_turn)
        # force 30 fps
        time.sleep(1/30)

def pygameMain():
    # Pygame require a window
    pygame.init()
    window = pygame.display.set_mode((800,500), RESIZABLE)
    pygame.font.init()
    font = pygame.font.SysFont('Open Sans', 25)
    small_font = pygame.font.SysFont('Open Sans', 20)
    end = False

    def writeText(screen, text, x, y, font, color=(62, 107, 153)):
        text = str(text)
        text = font.render(text, True, color)
        screen.blit(text, (x, y))

    def clear():
        window.fill((0,0,0))

    def updateScreen(window, speed, turn):
        clear()
        writeText(window, 'Linear: {:.2f}, Angular: {:.2f}'.format(speed, turn), 20, 0, font, (255, 255, 255))
        help_str =  'Use arrow keys to move, q or ESCAPE to exit.'
        writeText(window, help_str, 20, 50, small_font)
        help_2 =  'space key, k : force stop ---  anything else : stop smoothly'
        writeText(window, help_2, 20, 100, small_font)

    x, theta, status, count = 0, 0, 0, 0
    control_speed, control_turn = 0, 0
    updateScreen(window, control_speed, control_turn)

    while not end:
        x, theta = 0, 0
        keys = pygame.key.get_pressed()
        for keycode in moveBindingsGame.keys():
            if keys[keycode]:
                x_tmp, th_tmp = moveBindingsGame[keycode]
                x += x_tmp
                theta += th_tmp

        if keys[K_k] or keys[K_SPACE]:
                x, theta = 0, 0
                control_speed, control_turn = 0, 0

        control_speed, control_turn = control(x, theta, control_speed, control_turn)
        updateScreen(window, control_speed, control_turn)

        for event in pygame.event.get():
            if event.type == QUIT or event.type == KEYDOWN and event.key in [K_ESCAPE, K_q]:
                end = True
        pygame.display.flip()
        # force 30 fps
        pygame.time.Clock().tick(30)

if __name__=="__main__":
    # Does not handle multiple key pressed
    # try:
    #     curses.wrapper(main)
    # except KeyboardInterrupt:
    #     exit()
    # pygameMain()
    serial_file_write = open("test.log", 'ab')
    serial_file_read = open("test.log", 'rb')
    threads = [CommandThread(serial_file_write, command_queue),
               ListenerThread(serial_file_read)]
    for t in threads:
        t.start()

    for _ in range(2):
        command_queue.put((Order.HELLO, 0))
        command_queue.put((Order.RECEIVED, 0))
        command_queue.put((Order.MOTOR, 100))
        command_queue.put((Order.RECEIVED, 0))
        time.sleep(1)

    exit_signal = True
    n_received_semaphore.release()

    for t in threads:
        t.join()