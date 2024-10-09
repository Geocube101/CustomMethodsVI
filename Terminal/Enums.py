from CustomMethodsVI.Terminal.Struct import Color

NORTH: int = 1
EAST: int = 2
SOUTH: int = 4
WEST: int = 8
CENTER: int = 16
NORTH_WEST: int = NORTH | WEST
NORTH_EAST: int = NORTH | EAST
SOUTH_WEST: int = SOUTH | WEST
SOUTH_EAST: int = SOUTH | EAST

Color_T = Color | tuple[int, int, int] | int | str

CURSOR_INVISIBLE: int = 0
CURSOR_VISIBLE: int = 1
CURSOR_HIGH_VISIBLE: int = 2

KEY_LCRTL = 1
KEY_RCRTL = 2
KEY_LSHFT = 4
KEY_RSHFT = 8
KEY_LALT = 16
KEY_RALT = 32

WORDWRAP_ALL = 1
WORDWRAP_WORD = 2
WORDWRAP_NONE = 3

WINUPDATE_ALL = 0
WINUPDATE_MOUSEIN = 1
WINUPDATE_FOCUS = 2
