import random
import uuid
import time

MAX_PLAYERS = 2
WIDTH = 8
HEIGHT = 4
COLORS = ['white', 'black']

class Player(object):
    def __init__(self, game, id, name=None):
        self.id = id
        self.name = name
        self.game = game
        self.uuid = uuid.uuid4().hex
        self.color = COLORS[(game.int + id) % 2]

    def dict(self):
        cards = {}
        return {
            'id': self.id,
            'name': self.name,
            'uuid': self.uuid,
            'color': self.color,
        }

class DummyPlayer(object):
    def dict(self):
        return {'reserved': []}

DUMMY_PLAYER = DummyPlayer()

def to_id(x, y):
    return 100*x + y

class Game(object):
    def __init__(self):
        self.num_players = 0
        self.uuid = uuid.uuid4()
        self.state = 'pregame'
        self.num_moves = 0
        self.players = [None] * MAX_PLAYERS
        self.pids = []
        self.logs = []
        self.anchor_point = (None, None)
        self.winner = None
        self.active_player_index = -1
        self.spectator_index = MAX_PLAYERS

        self.board = [
            ['X','X','o','o','o','o','o','X'],
            ['o','o','o','o','o','o','o','o'],
            ['o','o','o','o','o','o','o','o'],
            ['X','o','o','o','o','o','X','X'],
        ]

        self.pieces = {}
        for i in range(2):
            tmp = {'placed': 0, 'pieces': {}}
            for j in range(3):
                tmp['pieces'][uuid.uuid4().hex] = {
                    'x': None,
                    'y': None,
                    'kind': "pusher"
                }
            for j in range(2):
                tmp['pieces'][uuid.uuid4().hex] = {
                    'x': None,
                    'y': None,
                    'kind': "pushee"
                }
            self.pieces[COLORS[(self.uuid.int+i) % 2]] = tmp

        self.piece_map = {}
        self.color_map = {}
        self.player_map = {}
        for color, player in self.pieces.iteritems():
            for k, v in player['pieces'].iteritems():
                self.color_map[k] = color
                self.piece_map[k] = v
        self.updated_at = time.time()

    def log(self, msg):
        self.logs.append({
            'pid': self.active_player_index,
            'time': int(time.time()),
            'msg': msg,
        })

    def add_player(self, name):
        player = Player(self.uuid, self.num_players, name)
        self.pids.append(player.id)
        self.players[player.id] = player
        self.num_players += 1
        return (player.id, player.uuid)

    def add_spectator(self, name):
        player = Player(self.uuid, self.spectator_index, name)
        self.pids.append(player.id)
        self.players.append(player)
        self.spectator_index += 1
        return (player.id, player.uuid)

    def start_game(self):
        if self.state != 'pregame':
            return False
        if self.num_players < 2:
            return False
        self.state = 'placement'
        self.active_player_index = self.uuid.int % 2
        for player in self.players:
            self.player_map[player.color] = player
        return True

    def active_player(self):
        if self.active_player_index >= 0 and self.active_player_index < self.num_players:
            return self.pieces[self.players[self.active_player_index].color]
        return DUMMY_PLAYER

    def next_turn(self):
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        self.num_moves = 0

    def validate(self, uuid, x, y):
        try:
            x = int(x)
            y = int(y)
        except ValueError:
            return {'error': 'could not convert coordinates to integers'}, None, None
        player = self.active_player()
        if x >= HEIGHT or y >= WIDTH or x < 0 or y < 0:
            return {'error': 'dimensions out of bounds'}, None, None
        if uuid not in player['pieces']:
            return {'error': 'invalid piece'}, None, None
        return {}, x, y

    def auto_place(self):
        if self.state != 'placement':
            return {'error': 'not in placement'}

        indices = [
            (0, 3), (1, 3), (2, 3), (2, 2), (3, 3),
            (0, 4), (1, 4), (2, 4), (3, 4), (1, 5),
        ]
        i = 0
        for color, player in self.pieces.iteritems():
            for k, v in player['pieces'].iteritems():
                v['x'] = indices[i][0]
                v['y'] = indices[i][1]
                self.board[v['x']][v['y']] = k
                i += 1
        self.state = 'main'
        return {}

    def place(self, uuid, x, y):
        result, x, y = self.validate(uuid, x, y)
        if 'error' in result:
            return result
        if self.state != 'placement':
            return {'error': 'not in placement stage'}
        if self.board[x][y] != 'o':
            return {'error': 'space not empty'}

        player = self.players[self.active_player_index]
        if player.color == COLORS[0] and y >= WIDTH/2:
            return {'error': 'must place on left half of board'}
        elif player.color == COLORS[1] and y < WIDTH/2:
            return {'error': 'must place on right half of board'}

        self.board[x][y] = uuid
        player = self.active_player()
        if player['pieces'][uuid]['x'] is not None:
            self.board[player['pieces'][uuid]['x']][player['pieces'][uuid]['y']] = 'o'
        else:
            player['placed'] += 1
        player['pieces'][uuid]['x'] = x
        player['pieces'][uuid]['y'] = y
        if player['placed'] == len(player['pieces']):
            self.next_turn()
            if self.active_player()['placed'] == len(self.active_player()['pieces']):
                self.state = 'main'
        return {}

    def neighbors(self, x, y):
        tmp = []
        tmp.append((x-1, y))
        tmp.append((x, y-1))
        tmp.append((x+1, y))
        tmp.append((x, y+1))

        result = []
        for n in tmp:
            x = n[0]
            y = n[1]
            if x >= 0 and y >= 0 and x < HEIGHT and y < WIDTH and self.board[x][y] != 'X':
                result.append(n)
        return result

    def connected(self, visited, x1, y1, x2, y2):
        if self.board[x2][y2] != 'o':
            return False
        visited.append(to_id(x1, y1))
        for n in self.neighbors(x1, y1):
            if n == (x2, y2):
                return True
            if self.board[n[0]][n[1]] == 'o' and to_id(n[0], n[1]) not in visited:
                if self.connected(visited, n[0], n[1], x2, y2):
                    return True
        return False

    def push(self, piece, uuid, x, y):
        dx = x - piece['x']
        dy = y - piece['y']

        if (x, y) == self.anchor_point:
            return {'error': 'cannot push anchor'}
        if x >= HEIGHT or x < 0:
            return {'error': 'cannot push in that direction'}
        if y < 0 or y >= WIDTH or self.board[x][y] == 'X':
            self.board[piece['x']][piece['y']] = 'o'
            piece['x'] = None
            piece['y'] = None
            curr_color = self.color_map[uuid]
            self.winner = 1 - self.player_map[curr_color].id
            return {}
        if self.board[x][y] != 'o':
            next_uuid = self.board[x][y]
            result = self.push(self.piece_map[next_uuid], next_uuid, x + dx, y + dy)
            if 'error' in result:
                return result

        self.board[x][y] = uuid
        self.board[piece['x']][piece['y']] = 'o'
        piece['x'] = x
        piece['y'] = y
        return {}

    def move(self, uuid, x, y):
        result, x, y = self.validate(uuid, x, y)
        if 'error' in result:
            return result
        if self.state != 'main':
            return {'error': 'not in main stage'}
        player = self.active_player()
        pieces = player['pieces']
        piece = pieces[uuid]

        if piece['kind'] == 'pusher' and (x, y) in self.neighbors(piece['x'], piece['y']) and self.board[x][y] != 'o':
            result = self.push(piece, uuid, x, y)
            if 'error' not in result:
                self.anchor_point = (x, y)
                self.next_turn()
            return result
        
        if self.num_moves >= 2:
            return {'error': 'no moves remaining'}

        visited = []
        if self.connected(visited, piece['x'], piece['y'], x, y):
            self.board[piece['x']][piece['y']] = 'o'
            self.board[x][y] = uuid
            piece['x'] = x
            piece['y'] = y
            self.num_moves += 1
            return {}
        return {'error': 'cannot move piece there'}

    def dict(self, player_id=None):
        if player_id is None:
            player_id = self.active_player_index
        if player_id not in self.pids:
            return {}

        result = {
            'players': [],
            'log': self.logs,
            'board': self.board,
            'anchor': {
                'x': self.anchor_point[0],
                'y': self.anchor_point[1],
            },
            'pieces': self.pieces,
            'color_map': self.color_map,
            'piece_map': self.piece_map,
            'winner': self.winner,
            'turn': self.active_player_index,
        }

        for player in self.players[:self.num_players]:
            result['players'].append(player.dict())

        return result
