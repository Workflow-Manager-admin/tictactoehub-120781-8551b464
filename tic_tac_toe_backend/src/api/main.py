"""
FastAPI app for Tic Tac Toe backend with user, auth, games, moves, and leaderboard endpoints.
"""
from fastapi import FastAPI, HTTPException, Depends, Body, Path
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .models import (
    User, Game, UserCreate, Token, GameCreate,
    GameMove, GameOut, Leaderboard, LeaderboardEntry, get_password_hash, verify_password, create_access_token
)
from .db import create_db_and_tables
from .auth import get_current_user, get_db
from .game_logic import check_winner, make_move

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description="API for user registration, authentication, game actions, and leaderboards for Tic Tac Toe.",
    version="1.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables at startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def health_check():
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.post("/api/register", response_model=Token, tags=["auth"], summary="Register new user")
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and receive access token."""
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    token = create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@app.post("/api/login", response_model=Token, tags=["auth"], summary="Login user")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and get JWT access token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@app.get("/api/games", response_model=List[GameOut], tags=["games"])
def list_games(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List current and previous games for the authenticated user."""
    games = db.query(Game).filter(
        ((Game.x_user_id == current_user.id) | (Game.o_user_id == current_user.id))
    ).order_by(Game.created_at.desc()).all()
    result = []
    for g in games:
        result.append(GameOut(
            id=g.id,
            x_user=g.user_x.username,
            o_user=g.user_o.username if g.user_o else None,
            board=g.board,
            turn=g.turn,
            is_complete=g.is_complete,
            winner=g.winner
        ))
    return result

# PUBLIC_INTERFACE
@app.post("/api/games", response_model=GameOut, tags=["games"])
def create_game(game_req: GameCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new game. Optionally specify opponent by username (creates a 2p game), or leave blank to play against yourself.
    """
    if game_req.opponent_username:
        opponent = db.query(User).filter(User.username == game_req.opponent_username).first()
        if opponent is None:
            raise HTTPException(status_code=404, detail="Opponent user not found")
        if opponent.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot play against yourself")
        game = Game(x_user_id=current_user.id, o_user_id=opponent.id)
    else:
        game = Game(x_user_id=current_user.id, o_user_id=None) # Play solo for now if no opponent
    db.add(game)
    db.commit()
    db.refresh(game)
    out = GameOut(
        id=game.id,
        x_user=game.user_x.username,
        o_user=game.user_o.username if game.user_o else None,
        board=game.board,
        turn=game.turn,
        is_complete=game.is_complete,
        winner=game.winner
    )
    return out

# PUBLIC_INTERFACE
@app.get("/api/games/{game_id}", response_model=GameOut, tags=["games"])
def get_game(game_id: int = Path(..., description="Game ID"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a single game by ID."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game or (current_user.id not in [game.x_user_id, game.o_user_id]):
        raise HTTPException(status_code=404, detail="Not found or not permitted")
    return GameOut(
        id=game.id,
        x_user=game.user_x.username,
        o_user=game.user_o.username if game.user_o else None,
        board=game.board,
        turn=game.turn,
        is_complete=game.is_complete,
        winner=game.winner
    )

# PUBLIC_INTERFACE
@app.post("/api/games/{game_id}/move", response_model=GameOut, tags=["games"])
def make_game_move(
    game_id: int = Path(..., description="Game ID"),
    move: GameMove = Body(..., description="Move details"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Make a move in a game (0-8 board index). X moves first, O second. Returns updated game.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game or (current_user.id not in [game.x_user_id, game.o_user_id]):
        raise HTTPException(status_code=404, detail="Not found or not permitted")

    if game.is_complete:
        raise HTTPException(status_code=400, detail="Game already complete")
    if game.board[move.position] != " ":
        raise HTTPException(status_code=400, detail="Cell already occupied")

    is_x_player = current_user.id == game.x_user_id
    is_o_player = game.o_user_id and (current_user.id == game.o_user_id)
    expected_player = game.turn
    if (expected_player == "X" and not is_x_player) or (expected_player == "O" and not is_o_player):
        raise HTTPException(status_code=403, detail="Not your turn")

    # Make move, check winner
    new_board = make_move(game.board, move.position, game.turn)
    winner = check_winner(new_board)
    game.board = new_board

    if winner:
        game.is_complete = True
        game.winner = winner
        # Update stats
        if winner == "X":
            db.query(User).filter(User.id == game.x_user_id).update({"games_won": User.games_won + 1})
            if game.o_user_id:
                db.query(User).filter(User.id == game.o_user_id).update({"games_lost": User.games_lost + 1})
        elif winner == "O":
            db.query(User).filter(User.id == game.o_user_id).update({"games_won": User.games_won + 1})
            db.query(User).filter(User.id == game.x_user_id).update({"games_lost": User.games_lost + 1})
        elif winner == "T":
            if game.o_user_id:
                db.query(User).filter(User.id == game.o_user_id).update({"games_tied": User.games_tied + 1})
            db.query(User).filter(User.id == game.x_user_id).update({"games_tied": User.games_tied + 1})

    else:
        game.turn = "O" if game.turn == "X" else "X"
    db.commit()
    db.refresh(game)
    # Output
    return GameOut(
        id=game.id,
        x_user=game.user_x.username,
        o_user=game.user_o.username if game.user_o else None,
        board=game.board,
        turn=game.turn,
        is_complete=game.is_complete,
        winner=game.winner
    )

# PUBLIC_INTERFACE
@app.get("/api/leaderboard", response_model=Leaderboard, tags=["leaderboard"])
def leaderboard(db: Session = Depends(get_db)):
    """
    Display the leaderboard, sorted by games_won descending.
    """
    users = db.query(User).order_by(User.games_won.desc()).limit(20).all()
    entries = [
        LeaderboardEntry(
            username=u.username,
            won=u.games_won,
            lost=u.games_lost,
            tied=u.games_tied
        )
        for u in users
    ]
    return {"entries": entries}
