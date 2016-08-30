import requests
import cmd
import argparse
import json
import readline

gid = None
uuid = None
pid = None
start_key = None
server = 'http://localhost'
curr_state = None

def create():
    global gid, start_key
    resp = requests.post(server + '/create')
    gid = resp.json()['game']
    start_key = resp.json()['start']
    handle_resp(resp, False)
    print 'created game {0} with start_key {1}'.format(gid, start_key)

def join(game=None):
    global gid, uuid, pid, start_key
    if game is None:
        game = gid
    else:
        gid = game
    resp = requests.post(server + '/join/{0}'.format(gid))
    j = resp.json()
    uuid = j['uuid']
    pid = j['id']
    print 'joined as player {0}'.format(pid)
    if not start_key:
        poll()

def start():
    resp = requests.post(server + '/start/{0}/{1}'.format(gid, start_key))
    if not resp.json():
        print 'started'
        poll()
    else:
        print resp.json()

def print_state():
    if not curr_state:
        return

    print '   0  1  2  3  4  5  6  7'
    print '        ==============='
    row_i = 0
    for row in curr_state['board']:
        line = str(row_i) + ' '
        for col in row:
            if col == 'X':
                line += '   '
            elif col == 'o':
                line += '...'
            else:
                container = '( )'
                piece = curr_state['piece_map'][col]
                if piece['kind'] == 'pusher':
                    container = '[ ]'
                if curr_state['anchor']['x'] == int(piece['x']) and curr_state['anchor']['y'] == int(piece['y']):
                    container = '< >'
                if curr_state['color_map'][col] == 'white':
                    container = container[0] + 'w' + container[2]
                else:
                    container = container[0] + 'b' + container[2]
                line += container
        print line
        row_i += 1
    print '     ==============='
    for color, player in curr_state['pieces'].iteritems():
        print ''
        print color
        print '====='
        for k, v in player['pieces'].iteritems():
            print '{} :: {} <> {},{}'.format(k, v['kind'], v['x'], v['y'])

def set_state():
    global curr_state
    resp = requests.get(server + '/poll/{0}?uuid={1}&pid={2}'.format(gid, uuid, pid))
    handle_resp(resp)

def auto_place():
    resp = requests.post(server + '/game/{0}/auto?uuid={1}&pid={2}'.format(gid, uuid, pid))
    handle_resp(resp)

def poll():
    while not curr_state or curr_state['turn'] != pid:
        set_state()

def handle_resp(resp, do_poll=True):
    global curr_state

    if 'result' in resp.json():
        print resp.json()['result']
    if 'error' in resp.json():
        print resp.json()['error']
        return

    curr_state = resp.json()['state']
    print_state()
    if do_poll:
        poll()

def act(action, target, x, y):
    resp = requests.post(server + '/game/{0}/{1}/{2}/{3}/{4}?uuid={5}&pid={6}'.format(gid, action, target, x, y, uuid, pid))
    handle_resp(resp)

def list_games():
    resp = requests.get(server + '/list')
    print 'Games:'
    print '------'
    for game in resp.json()['games']:
        active = 'waiting'
        if game['in_progress']:
            active = 'in progress'
        print '{0} -> {1} player(s) | {2}'.format(game['uuid'], game['players'], active)
    print ''

class Client(cmd.Cmd):
    prompt = '> '

    def do_create(self, line):
        """Create a new game"""
        create()

    def do_start(self, line):
        """Starts the created game"""
        start()

    def do_join(self, game):
        """Joins game"""
        if game:
            join(game)
        else:
            join()

    def do_auto(self, line):
        auto_place()

    def do_place(self, line):
        """Places the piece"""
        uuid, x, y = line.split(' ')
        act('place', uuid, x, y)

    def do_move(self, line):
        """Moves the piece"""
        uuid, x, y = line.split(' ')
        act('move', uuid, x, y)

    def do_print(self, line):
        """Prints the current state of the game"""
        print_state()

    def do_EOF(self, line):
        print ''
        return True

    def do_list(self, line):
        """List active games"""
        list_games()

    def do_resume(self, line):
        """Go back into a game in case it crashes"""
        global gid, uuid, pid

        gid, uuid, pid = line.split(' ')
        pid = int(pid)

if __name__ == "__main__":
    readline.parse_and_bind("bind ^I rl_complete")

    parser = argparse.ArgumentParser(description='Client for pushfight server.')
    parser.add_argument('server', type=str, nargs='?', help='server to connect to.', default=server)
    args = parser.parse_args()
    server = args.server

    Client().cmdloop()
