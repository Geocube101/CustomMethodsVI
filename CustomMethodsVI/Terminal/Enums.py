from ..Terminal.Struct import Color

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

KEY_LCRTL: int = 1
KEY_RCRTL: int = 2
KEY_LSHFT: int = 4
KEY_RSHFT: int = 8
KEY_LALT: int = 16
KEY_RALT: int = 32

WORDWRAP_ALL: int = 1
WORDWRAP_WORD: int = 2
WORDWRAP_NONE: int = 3

WINUPDATE_ALL: int = 0b00
WINUPDATE_MOUSEIN: int = 0b01
WINUPDATE_FOCUS: int = 0b10
