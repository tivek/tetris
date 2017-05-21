import random



def make_board(num_rows, num_cols):
    def make_row(num_cols):
        return [None] * num_cols

    return [make_row(num_cols) for i in range(num_rows)]


def is_block(c):
    return (c != " ") and (c is not None)


def height(array2d):
    return len(array2d)


def width(array2d):
    return len(array2d[0])


def make_shape_template(p, N=4):
    def kicks_1d(n, sign=-1):
        yield 0
        for i in range(1, n):
            yield  sign * i
            yield -sign * i

    assert(height(p) == width(p))
    
    r = [p]
    for _ in range(N - 1):
        p = list(zip(*(p[::-1])))
        r.append(p)
    
    n = height(p) - 1
    
    kicks = [(dx, dy) for dy in kicks_1d(n) for dx in kicks_1d(n)]
            
    return r, kicks
    

    


class Tetromino:
    available_templates = {"I" : make_shape_template(["    ",
                                                      "xxxx",
                                                      "    ",
                                                      "    "]),
                           "J" : make_shape_template(["x  ",
                                                      "xxx",
                                                      "   "]),
                           "L" : make_shape_template(["  x",
                                                      "xxx",
                                                      "   "]),
                           "O" : make_shape_template(["xx",
                                                      "xx"], 1),
                           "S" : make_shape_template([" xx",
                                                      "xx ",
                                                      "   "]),
                           "T" : make_shape_template([" x ",
                                                      "xxx",
                                                      "   "]),
                           "Z" : make_shape_template(["xx ",
                                                      " xx",
                                                      "   "])}

    def __init__(self, name, which=None):
        if name not in Tetromino.available_templates:
            raise Exception("This tetromino does not exist: ", name) 
        self.name = name
        self.shapes, self.kicks = Tetromino.available_templates[name]
        if which is None:
            which = random.randrange(len(self.shapes))
        self.which = which % len(self.shapes)
    
    def __repr__(self):
        return "\n".join("".join(l) for l in self.shape())
    
    def shape(self):
        return self.shapes[self.which]
    
    def height(self):
        return height(self.shape())
    
    def width(self):
        return width(self.shape())

    

def check_collision(board, t, x, y):
    for j, line in enumerate(t.shape()):
        for i, c in enumerate(line):
            if is_block(c) and is_block(board[y + j][x + i]):
                return x, y
    return None
    

def check_in_board(board, t, x, y):
    h, w = height(board), width(board)
    for j, row in enumerate(t.shape()):
        for i, c in enumerate(row):
            if is_block(c):
                if x + i < 0:
                    return "left"
                elif x + i >= w:
                    return "right"
                elif y + j < 0:
                    return "top"
                elif y + j >= h:
                    return "bottom"
    return None

