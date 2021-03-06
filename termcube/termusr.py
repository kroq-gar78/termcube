from .cube import Cube, ScrambleGenerator
from .turn import TurnSequence

from argparse import ArgumentParser, Namespace
from collections import namedtuple
from os.path import isfile
from queue import Queue
from sys import argv
from threading import Thread
from time import time


help_text = \
"""Term Cube Timer

After scrambles, type a command or just press enter to start inspection.
Once inspected, press enter again to start the solve. Hurry! Penalties apply.
Once solving, press enter again to end the solve.
If tags are enabled, enter your tags separated by space (not commas) or
type "del" to delete that solve.
Repeat.

Available commands:
-exit       - End this timer session (you will be able to export after)
-stat       - Display this session's statistics so far
-merge      - Rename one tag or merge multiple together
-export     - Export your times to a file
-del        - Delete a solve
-help       - Display this help text"""

def prompt_number(prompt = 'Enter a number: ', default = None, condition = None):
    """Print a given prompt string and return the user's input as a float.
    If invalid or no input, return a given default.
    """
    while True:
        print(prompt, end = '')
        usr = input()
        if usr:
            try:
                if not condition or condition(float(usr)):
                    return float(usr)
            except:
                continue
        elif default != None:
            return default

def prompt_int(prompt = 'Enter a number: ', default = None, condition = None):
    """Print a given prompt string and return the user's input as a float.
    If invalid or no input, return a given default.
    """
    while True:
        print(prompt, end = '')
        usr = input()
        if usr:
            try:
                if not condition or condition(int(usr)):
                    return int(usr)
            except:
                continue
        elif default != None:
            return default

class Solve(namedtuple('Solve', ['time', 'penalty', 'tags', 'scramble'])):
    def totaltime(self):
        return self.time + self.penalty

def mean(arr):
    #~ try:
        return sum(arr)/len(arr)
    #~ except:
        #~ return None
    
def count_down(inspection_time = 15.):
    """Count down a given number of seconds or until interrupted by
    the enter key, then return a penalty corresponding to the time past
    the allotted inspection time that the timer was stopped.

    Seconds over    Penalty
    0               0
    2               2
    >2              "DNF"
    """
    if inspection_time <= 0:
        return 0

    stop = []
    Thread(target=(lambda stop:stop.append(input())), args=(stop,)).start()
    start = time()
    while not stop:
        if inspection_time > time()-start:
            print('%-3.2f  ' % (inspection_time-time()+start), end='\r')
        elif inspection_time + 2 > time() - start:
            print('%-5s' % '+2', end='\r')
        else:
            print('%-5s' % 'DNF', end='\r')

    dt = time() - start - inspection_time

    return 0 if dt <= 0 else 2 if dt <= 2 else 'DNF'


def count_up():
    """Start a timer counting up until interrupted with enter key.
    Return the time of the timer.
    """
    stop = []
    Thread(target=(lambda stop:stop.append(input())), args=(stop,)).start()
    start = time()
    ret = 0
    while not stop:
        ret = time()-start
        print('%.2f    ' % ret, end='\r')
    print('%-10s' % '\r')
    return ret

def stats(arr):
    dic = {}
    for solve in arr:
        for tag in solve.tags.split():
            if tag in dic:
                dic[tag].append(solve.totaltime())
            else:
                dic[tag] = [solve.totaltime()]
    if 'Untagged' in dic:
        del dic['Untagged']
    for k in dic:
        dic[k] = mean(dic[k])

    return sum(e.totaltime() for e in arr)/len(arr), dic

def export_times(filename, ret):
    total, d = stats(ret)
    p = 'Average of %d: %.2f\n' % (len(ret), total)
    p += '\n'.join('%-10s %.2f' % (k, d[k]) for k in d)
    p += '\n'*4
    p += ('\n'.join(('Time: %.2f\t Tags: %s\t Scramble: %s' % (s.totaltime(), s.tags, s.scramble)) for s in ret))
    with open(filename, 'w' if isfile(filename) else 'a') as o:
        o.write(p)

def get_times(cube_size=3, inspection_time=15, using_tags=True, using_random_state=True, scramble_length=-1):
    print('Initializing...')
    solves = []
    cube = Cube(cube_size)
    solve_number = 1
    with ScrambleGenerator(size=cube_size, random_state=using_random_state, moves=scramble_length) as scrambler:
        while True:
            cube.reset()
            cube.apply('x')
            scramble = next(scrambler)
            cube.apply(scramble)
            print('Solve %d' % solve_number)

            print(cube)
            print(scramble, end='')

            usr = input()
            while usr:
                if usr == 'exit':
                    return solve_number-1, solves
                elif usr.startswith('stat'):
                    total, d = stats(solves)
                    print('%-10s %.2f' % ('All', total))
                    for k in d:
                        print('%-10s %.2f' % (k, d[k]))
                elif usr.startswith('merge'):
                    merge_tags, new_tag = '', ''
                    while merge_tags == '':
                        print('List of tag(s) to merge/rename: ')
                        merge_tags = input().split()
                    while new_tag == '':
                        print('New tag name: ')
                        new_tag = input()
                    for solve in solves:
                        for target in merge_tags:
                            solve.tags = solve.tags.replace(target, new_tag)
                        print('Success')
                elif usr.startswith('export'):
                    print('Name of file to export to: ', end='')
                    filename = input()
                    export_times(filename, solves)
                    print("Export successful")
                elif usr.startswith('del'):
                    delete_index = prompt_int("Delete which scramble number? (default last): ", 
                                              default=solve_number-1, 
                                              condition=lambda n: 0 < n < solve_number)-1
                    try:
                        t = solves[delete_index].totaltime()
                        del solves[delete_index]
                        print('Removed solve number %d: %.2f' % (delete_index+1, t))
                        solve_number -= 1
                    except:
                        print('Unable to remove solve %d' % (delete_index+1))
                else:
                    print(help_text)
                usr = input()

            penalty = count_down(inspection_time)
            time = count_up()
            tags = ''

            if penalty == 'DNF':
                print('DNF times are not saved')
                continue

            while using_tags and not tags:
                print("Type your tag(s) or 'del' to forget this solve: ", end='')
                tags = input()
                if tags == 'del':
                    break
                if not tags:
                    continue
            else:
                solve_number += 1
                solves.append(Solve(time, penalty, tags if using_tags else 'Untagged', scramble))
                print()
    return solve_number-1, solves
