"""
Core Tic Tac Toe game logic.
"""

WIN_COMBOS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],    # rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8],    # columns
    [0, 4, 8], [2, 4, 6],               # diagonals
]

# PUBLIC_INTERFACE
def check_winner(board: str) -> str:
    """
    Checks if there is a winner or tie.
    Return "X", "O" for winner, "T" for tie, "" for ongoing.
    """
    for a, b, c in WIN_COMBOS:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    if " " not in board:
        return "T" # Tie
    return ""

# PUBLIC_INTERFACE
def make_move(board: str, position: int, player: str) -> str:
    """Return new board after placing player's move in position (0-8)."""
    assert 0 <= position < 9
    assert board[position] == " "
    new_board = board[:position] + player + board[position+1:]
    return new_board
