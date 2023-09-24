from typing import Tuple

import inquirer
from inquirer.errors import ValidationError

from .cards import Hand
from .messages import Message
from .exceptions import StopGame

class Player:
    """A class representing player"""

    STOP_WORDS = 's', 'stop', 'exit', 'quit'

    def __init__(self, chips: int) -> None:
        self._chips = chips
        self.hand = Hand()
        self.split_hand = Hand()
 
    @property
    def chips(self) -> int:
        return self._chips
    
    def add_chips(self, chips: int) -> None:
        self._chips += chips
    
    def reset_hands(self) -> None:
        self.hand.reset()
        self.split_hand.reset()

    def make_bet(self) -> int:
        bet = self.__bet_prompt()
        self._chips -= bet
        return bet
    
    def make_insurance_bet(self, possible_bet: int) -> int:
        self._possible_insurance_bet = possible_bet if possible_bet <= self.chips else self.chips
        bet = self.__insurance_bet_prompt()
        self.make_quiet_bet(bet)
        return bet
    
    def make_quiet_bet(self, bet: int) -> int:
        self._chips -= bet
        return bet
    
    def choose_action(self, actions: Tuple[str, ...], hand: Hand):
        return self.__action_prompt(actions, hand)

    def __validate_bet(self, _, bet) -> bool:
        if bet.lower().strip() in self.STOP_WORDS:
            raise StopGame
        try:
            bet = int(bet)
            if bet <= 0:
                raise ValidationError(bet, Message.BETTING_TYPE_ERROR)
            if self.chips - bet < 0:
                raise ValidationError(bet, Message.NOT_ENOUGH_CHIPS_ERROR.format(chips=self.chips))
            return True
        except ValueError:
            raise ValidationError(bet, Message.BETTING_TYPE_ERROR)
    
    def __validate_insurance_bet(self, _, bet) -> bool:
        try:
            bet = int(bet)
            if bet <= 0:
                raise ValidationError(bet, Message.BETTING_TYPE_ERROR)
            if bet > self._possible_insurance_bet:
                raise ValidationError(bet, Message.INSURANC_BET_ERROR.format(chips=self._possible_insurance_bet))
            return True
        except ValueError:
            raise ValidationError(bet, Message.BETTING_TYPE_ERROR)

    def __bet_prompt(self) -> int:
        bet = inquirer.text(
            message=Message.BETTING_INVITATION.format(chips=self.chips),
            validate=self.__validate_bet              
        )
        return int(bet)
    
    def __insurance_bet_prompt(self) -> int:
        bet = inquirer.text(
            message=Message.INSURANCE_BETTING_INVITATION.format(possible_bet=self._possible_insurance_bet),
            validate=self.__validate_insurance_bet
        )
        return int(bet)
    
    def __action_prompt(self, actions: Tuple[str, ...], hand: Hand) -> str:
        action = inquirer.list_input(
            message=Message.ACTION_PROMPT.format(score=hand.score),
            choices=actions
        )
        return str(action)


class Dealer:
    """A class representing dealer"""

    def __init__(self):
        self.hand = Hand()
    
    def reset_hands(self) -> None:
        self.hand.reset()
    