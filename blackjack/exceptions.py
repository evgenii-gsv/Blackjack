class CardNotFound(Exception):
    """Card was not found in deck or hand"""

class StopGame(Exception):
    """Player exiting the game"""

class HandSplitting(Exception):
    """Player splits the hand"""