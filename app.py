#!/usr/bin/env python3

import asyncio
import time
import random
import enum
import urwid
import tetromino

class AppState:
    def __init__(self, statestack):
        self.gamestatestack = statestack
        self.context = statestack.context
        self.widget = None
    
    def process(self, dt):
        pass
    
    def render(self, dt):
        pass
    
    def handle_event(self, event):
        pass
    

class StateStack:
    def __init__(self, context=None):
        self.context = context
        self._stack = []
        self._pending = []
    
    def is_empty(self):
        return not self._stack
    
    def request_push(self, statetype, *args, **kwargs):
        def push():
            state = statetype(self, *args, **kwargs)
            self._stack.append(state)
            #self.context.urwid_loop.widget = state.widget
        self._pending.append(push)
    
    def request_pop(self):
        def pop():
            self._stack.pop()
        self._pending.append(self._stack.pop)
    
    def request_clear(self):
        self._pending.append(self._stack.clear)
    
    def apply_pending(self):
        if self._pending:
            for action in self._pending:
                action()
            self._pending.clear()
            # FIXME: for now with urwid use only the top state for rendering
            if self._stack:
                self.context.urwid_loop.widget = self._stack[-1].widget
    
    def process(self, dt):
        for state in reversed(self._stack):
            if state.process(dt) is not None:
                break
        self.apply_pending()
        
        
    def render(self, dt):
        #FIXME: for now with urwid use only the top state for rendering
        #for state in self_stack:
        #    state.render(dt)
        self._stack[-1].render(dt)
        
    
    def handle_event(self, event):
        for state in reversed(self._stack):
            if state.handle_event(event) is not None:
                break

                
class Context:
    def __init__(self):
        self.loop = None
        self.urwid_loop = None


class Application:
    def __init__(self, start_state, loop=None):
        self.context = Context()
        self.events = []
        self.done = False
        self.gamestatestack = StateStack(self.context)
        
        if loop is None:
            loop = asyncio.get_event_loop()
        self.context.loop = loop
        
        self._setup_window()
        
        self.gamestatestack.request_push(start_state)
        self.gamestatestack.apply_pending()
        
        
    def _setup_window(self):
        dummy_widget = urwid.SolidFill(u'A')
        palette = [("I", "light cyan", "default"),
                   ("J", "light blue", "default"),
                   ("L", "brown", "default"),
                   ("O", "yellow", "default"),
                   ("S", "light green", "default"),
                   ("T", "dark magenta", "default"),
                   ("Z", "light red", "default"),
                   ("ghost", "dark gray", "default"),
                   ('reversed', 'standout', '')]
                   
        ml = urwid.MainLoop(dummy_widget, palette,
                            event_loop=urwid.AsyncioEventLoop(loop=self.context.loop),
                            unhandled_input=self.events.append)
        self.context.urwid_loop = ml
        ml.start()
    
    def handle_events(self, dt):
        # handle collected events
        for e in self.events:
            if e == "Q":
                self.stop()
            self.gamestatestack.handle_event(e)
        self.events.clear()
    
    def process(self, dt):
        self.gamestatestack.process(dt)

    def render(self, dt):
        self.gamestatestack.render(dt)
    
    async def run(self):
        max_frame_time = 1.0 / 5
        step_size = 1.0 / 60
        prev_time = time.perf_counter()
        while not self.done:
            self.handle_events(0)
            # get the current real time
            now = time.perf_counter()
        
            # if elapsed time since last frame is too long...
            if now - prev_time > max_frame_time:
                # slow the game down by resetting clock
                prev_time = now - step_size
                # alternatively, do nothing and frames will auto-skip, which
                # may cause the engine to never render!
        
            # this code will run only when enough time has passed, and will
            # catch up to wall time if needed.
            while now - prev_time >= step_size:
                # save old game state, update new game state based on step_size
                #update_state(now, step_size)
                self.process(step_size)
                prev_time += step_size
            #else:
            #    await asyncio.sleep(0.016) # parameter: time to wait in s
            if self.gamestatestack.is_empty():
                self.stop()
                break

            # render game state. use 1.0/(step_size/(T-now)) for interpolation
            self.render(now - prev_time)
            
            # yield to other coroutines
            await asyncio.sleep(0.005)
            
    
    def stop(self):
        self.done = True
        self.context.urwid_loop.stop()

        
class MainMenuState(AppState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        body = [urwid.Text(u"Baby's First Tetris"), urwid.Divider()]
        buttons = [("Play", lambda _: self.gamestatestack.request_push(PlayGameState)),
                   ("High Scores", lambda _: self.gamestatestack.request_push(HighScoreState)),
                   ("Exit", lambda _: self.gamestatestack.request_clear())]
        for name, callback in buttons:
            button = urwid.Button(name)
            urwid.connect_signal(button, "click", callback)
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        
        self.widget = urwid.Padding(listbox)
    
    def handle_event(self, event):
        # MainMenuState uses urwid for now
        pass


class PauseState(AppState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        body = [urwid.Text(u"PAUSE"), urwid.Divider()]
        buttons = [("Continue playing", lambda _: self.gamestatestack.request_pop()),
                   ("Return to Main Menu", self.menu_main_menu)]
        for name, callback in buttons:
            button = urwid.Button(name)
            urwid.connect_signal(button, "click", callback)
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        
        self.widget = urwid.Padding(listbox)
    
    def menu_main_menu(self, button):
        # TO DO: ask are you sure...
        self.gamestatestack.request_clear()
        self.gamestatestack.request_push(MainMenuState)
    
    def handle_event(self, event):
        # MainMenuState uses urwid for now
        pass
    
    def process(self, dt):
        # do not allow the lower states to update
        return True


class PlayGameState(AppState):
    FALLING = 0
    LANDED = 1
    LOCKED = 2
    CLEARING = 3
    GAMEOVER = 4
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
        self.board_width = 10
        self.board_height = 22
        self.board = tetromino.make_board(self.board_height, self.board_width)
        self.score = 0
        self.level = 1
        self.lines = 0
        self.piece = None
        self.next_piece = None
        
        self.new_tetromino()
        
        self.diag_text = [""]
        self.diag_display = urwid.Text("")

        self.board_display = urwid.Text("")
        w = urwid.LineBox(self.board_display)
        play_widget = urwid.Padding(w, width=self.board_width + 2)
        
        self.score_display = urwid.Text("")
        self.level_display = urwid.Text("")
        self.lines_display = urwid.Text("")
        
        self.next_piece_display = urwid.Text("NEXT\n\n\n", align="center")
        w = urwid.Filler(self.next_piece_display, min_height=4)
        w = urwid.BoxAdapter(w, height=4)
        w = urwid.LineBox(w)
        w = urwid.Padding(w, width=4 + 2)
        next_widget = urwid.Pile([urwid.Text("Next"), w])
        
        w = urwid.Columns([(22, play_widget), \
                          urwid.Pile([next_widget,
                                      urwid.Divider(),
                                      self.level_display,
                                      urwid.Divider(),
                                      self.lines_display,
                                      urwid.Divider(),
                                      self.score_display])])
        self.widget = urwid.Filler(w, 'top')
        #self.widget = urwid.Overlay(w,#urwid.ListBox(urwid.SimpleListWalker(listbox_content)),
                                    #urwid.SolidFill("\u2591"),
                                    #align="center", width=12,
                                    #valign="middle", height=60)


        
        self.dirty = True
        
        self.gamestate = PlayGameState.FALLING

        self.events = []
        
        self.gravity_interval = 0.5 # seconds
        self.time_since_last_gravity = 0
        
        self.lock_interval = self.gravity_interval
        self.time_since_landed = 0
        
        self.clear_effect = 1
        self.time_since_locked = 0
        self.rows_to_clear = []

    def new_tetromino(self):
        def random_tetromino():
            name = random.choice(list(tetromino.Tetromino.available_templates.keys()))
            return tetromino.Tetromino(name, 0)

        self.piece, self.next_piece = self.next_piece, random_tetromino()
        if self.piece is None:
            self.piece = random_tetromino()
        
        self.x = (self.board_width - self.piece.width()) // 2
        self.y = 0
        self.floor_kick = False
        
    
    def handle_event(self, inputevent):
        if self.gamestate is not PlayGameState.GAMEOVER:
            if inputevent == "esc":
                self.gamestatestack.request_push(PauseState)
            elif inputevent == "a":
                self.events.append("left")
            elif inputevent == "d":
                self.events.append("right")
            elif inputevent == "q":
                self.events.append("rotate_left")
            elif inputevent == "e":
                self.events.append("rotate_right")
            elif inputevent == "s":
                self.events.append("drop")
            elif inputevent == "w":
                self.events.append("harddrop")
        else:
            #self.gamestatestack.request_push(HighscoreState)
            self.gamestatestack.request_push(MainMenuState)
        return True
        
    
    def process(self, dt):
        # early exit
        if self.gamestate is PlayGameState.GAMEOVER:
            self.events.clear()
            return True
        
        # update timed events, if needed add them to the event queue
        if self.gamestate in [PlayGameState.FALLING, PlayGameState.LANDED]:
            self.time_since_last_gravity += dt
            while self.time_since_last_gravity >= self.gravity_interval:
                self.events.append("gravity") # TO DO: insert at the correct time
                self.time_since_last_gravity -= self.gravity_interval

        if self.gamestate is PlayGameState.LANDED:
            self.time_since_landed += dt
            if self.time_since_landed >= self.lock_interval:
                self.events.append("locktimeout") # TO DO: insert at the correct time
                #self.gamestate = PlayGameState.LOCKED
            
            
        # process the events and change the state of the game
        for event in self.events:
            if self.gamestate in [PlayGameState.FALLING, PlayGameState.LANDED]:
                if event == "left":
                    self.attempt_move_by(self.piece, -1, 0)
                        
                elif event == "right":
                    self.attempt_move_by(self.piece, 1, 0)
                
                elif event == "rotate_left":
                    self.attempt_rotate(-1)
                                
                elif event == "rotate_right":
                    self.attempt_rotate(1)
            
            if self.gamestate is PlayGameState.FALLING:
                if event in ["drop", "gravity"]:
                    if not self.attempt_drop(event):
                        self.gamestate = PlayGameState.LANDED
                        self.time_since_landed = 0

                elif event == "harddrop":
                    _, y = self.get_ghost_coords()
                    self.score += (y - self.y) * 2
                    self.y = y
                    self.gamestate = PlayGameState.LOCKED
            
            elif self.gamestate is PlayGameState.LANDED:
                if event in ["drop", "harddrop", "locktimeout", "gravity"]:
                    self.gamestate = PlayGameState.LOCKED
                
                elif self.test_move_by(self.piece, 0, 1): # did we move away from the obstacle?
                    self.gamestate = PlayGameState.FALLING

            
            if self.gamestate == PlayGameState.LOCKED:
                self.put_into_board()
                if self.past_top():
                    self.gamestate = PlayGameState.GAMEOVER
                    break
                else:
                    cleared = self.clear_rows()
                    self.add_score(cleared)
                    self.new_tetromino()
                    self.time_since_last_gravity = 0
                    if tetromino.check_collision(self.board, self.piece, self.x, self.y):  #FIXME
                        self.gamestate = PlayGameState.GAMEOVER
                    else:
                        self.gamestate = PlayGameState.FALLING

        self.events.clear()

        # do not allow the lower app states to update
        return True
    
    def add_score(self, cleared):
        scoring = {0:0, 1:40, 2:100, 3:300, 4:1200}
        self.score += self.level * scoring[cleared]
        self.lines += cleared


    def test_move_by(self, piece, dx, dy):
        crossed_borders = tetromino.check_in_board(self.board, piece, self.x + dx, self.y + dy)
        if crossed_borders is None:
            collisions = tetromino.check_collision(self.board, piece, self.x + dx, self.y + dy)
            if collisions is None:
                return True
        return False
    
    
    def attempt_move_by(self, piece, dx, dy):
        if self.test_move_by(self.piece, dx, dy):
            self.x += dx
            self.y += dy
            self.dirty = True
            return True
        return False
    
    
    def test_rotate(self, rot):
        rp = tetromino.Tetromino(self.piece.name, self.piece.which + rot)
        for dx, dy in rp.kicks:
            if self.test_move_by(rp, dx, dy):
                floor_kick = (dy == -1)
                return dx, dy, floor_kick
        return None
    
    
    def attempt_rotate(self, rot):
        res = self.test_rotate(rot)
        if res is not None and not self.floor_kick:
            dx, dy, self.floor_kick = res
            self.piece = tetromino.Tetromino(self.piece.name, self.piece.which -1)
            self.x += dx
            self.y += dy
            self.dirty = True
            return True
        return False
    
    
    def attempt_drop(self, event): # return True if dropped, False if landed
        self.time_since_last_gravity = 0
        if self.test_move_by(self.piece, 0, 1):
            self.y += 1
            if event == "drop":
                self.score += 1
            self.dirty = True
            return True
        else:
            return False
        
        
    def get_ghost_coords(self):
        dy = 0
        while self.test_move_by(self.piece, 0, dy + 1):
            dy += 1
        return self.x, self.y + dy
        
    
    def past_top(self):
        for row in self.board[0:2]:
            for c in row:
                if tetromino.is_block(c):
                    return True
        return False
    
    
    def put_into_board(self):
        for j, row in enumerate(self.piece.shape()):
            for i, c in enumerate(row):
                if tetromino.is_block(c):
                    try:
                        self.board[self.y + j][self.x + i] = self.piece.name
                    except:
                        pass
        self.dirty = True

    
    def clear_rows(self):
        def row_full(row):
            for c in row:
                if not tetromino.is_block(c):
                    return False
            return True
        
        rows_to_delete = []
        
        for j, row in enumerate(self.board):
            if row_full(row):
                rows_to_delete.append(j)
        
        for index in reversed(rows_to_delete):
            del self.board[index]
        
        self.board = tetromino.make_board(len(rows_to_delete), self.board_width) + self.board
        
        self.dirty = True
        
        return len(rows_to_delete)
                
    
    
    def render(self, dt):
        square = "\N{WHITE SQUARE CONTAINING BLACK SMALL SQUARE}"
        empty = ("ghost", "|")        
        def flatten_text(char_array, delimiter="\n"):
            rows = iter(char_array)
            yield from next(rows)
            for row in rows:
                yield delimiter
                yield from row
        
        def render_piece(piece, color):
            return [[(color, square) if tetromino.is_block(c) else " " for c in row] for row in piece.shape()]
        
        def render_piece_into_board(text, piece, x, y):
            for j, row in enumerate(piece):
                for i, c in enumerate(row):
                    if tetromino.is_block(c):
                        text[j + y][i + x] = c
        
        def render_chars_into_board(text, chars, x, y):
            for j, row in enumerate(chars):
                for i, c in enumerate(row):
                    text[j + y][i + x] = c


        if self.dirty:
            # update score and level
            self.level_display.set_text("Level\n{self.level}".format(self=self))
            self.score_display.set_text("Score\n{self.score}".format(self=self))
            self.lines_display.set_text("Lines\n{self.lines}".format(self=self))
            
            # render next
            if self.next_piece:
                self.next_piece_display.set_text(list(flatten_text(render_piece(self.next_piece, self.next_piece.name))))

            # render board
            out = [[(c, square) if tetromino.is_block(c) else empty for c in row] for row in self.board]
            
            if self.piece:
                # render ghost
                render_piece_into_board(out, render_piece(self.piece, "ghost"), *self.get_ghost_coords())
                
                # render piece
                render_piece_into_board(out, render_piece(self.piece, self.piece.name), self.x, self.y)
                
            # game over?
            if self.gamestate == PlayGameState.GAMEOVER:
                render_chars_into_board(out, ("      ", " GAME ", " OVER ", "      ",), \
                                        self.board_width // 2 - 3, self.board_height // 2 - 2)
            
            self.board_display.set_text(list(flatten_text(out)))
            self.diag_display.set_text(self.diag_text)
            
            self.dirty = False
        return True


# a bit of gui magic
def cols(a, b, c):
    return urwid.Columns([(20, urwid.Text(a)),
                          (10, urwid.Text(b)),
                          (10, urwid.Text(c))])
                          
class Row(urwid.WidgetWrap):
    def __init__(self, a, b, c):
        # wrap in AttrMap to highlight when selected
        super().__init__(urwid.AttrMap(cols(a, b, c), None, 'reversed'))

    def selectable(self):
        # these widgets want the focus
        return True

    def keypress(self, size, key):
        # handle keys as you will
        return key


class HighScoreState(AppState):
    def __init__(self, statestack, level=None, score=None):
        super().__init__(statestack)

        self.highscore = self.from_file(None)
        
        #if level is None or score is None:
            # just display the high score table
        #else:
            # allow editing

        title = urwid.Text(u"High Scores")
        header = cols("Name", "Level", "Score")
        rows = [cols(name, str(level), str(score)) for name, level, score in self.highscore]
        listbox = urwid.ListBox(urwid.SimpleListWalker(rows))
        
        self.widget = urwid.Frame(listbox, header=header)
    
    def handle_event(self, event):
        if event in ('enter', 'esc'):
            self.gamestatestack.request_pop()
    
    def process(self, dt):
        # do not allow the lower states to update
        return True
    
    def from_file(self, filename):
        # TO DO
        return [("Player " + str(i + 1), 10, (10 - i) * 1000) for i in range(10)]

        


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = Application(PlayGameState, loop=loop)
    print("Starting.")
    loop.run_until_complete(app.run())
