from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional
from random import shuffle

from colored import stylize, fg


from . import config
from .graphic_patterns import FACE_CARD, HIDDEN_CARD
from .exceptions import CardNotFound


@dataclass(frozen=True, slots=True)
class RankDetails:
    symbol: str
    value: int

    def __repr__(self) -> str:
        return self.symbol


class Rank(Enum):
    TWO = RankDetails('2', 2)
    THREE = RankDetails('3', 3)
    FOUR = RankDetails('4', 4)
    FIVE = RankDetails('5', 5)
    SIX = RankDetails('6', 6)
    SEVEN = RankDetails('7', 7)
    EIGHT = RankDetails('8', 8)
    NINE = RankDetails('9', 9)
    TEN = RankDetails('10', 10)
    JACK = RankDetails('J', 10)
    QUEEN = RankDetails('Q', 10)
    KING = RankDetails('K', 10)
    ACE = RankDetails('A', 11)

    def __str__(self) -> str:
        return self.value.symbol


@dataclass(frozen=True, slots=True)
class SuitDetails:
    symbol: str
    color: int

    def __repr__(self) -> str:
        return self.symbol


class Suit(Enum):
    DIAMONDS = SuitDetails('♦', config.COLORED_RED_COLOR)
    CLUBS = SuitDetails('♣', config.COLORED_BLACK_COLOR)
    HEARTS = SuitDetails('♥', config.COLORED_RED_COLOR)
    SPADES = SuitDetails('♠', config.COLORED_BLACK_COLOR)

    def __str__(self) -> str:
        return self.value.symbol


class Card:
    """A class representing the Card object"""

    def __init__(self, rank: Rank, suit: Suit) -> None:
        self._rank = rank
        self._suit = suit
        self._value = rank.value.value
        self._color = suit.value.color
        self.hidden = False

    def detract_ace_value(self) -> None:
        """If the hand goes over 21, ace gets the value of 1"""
        if self.rank is Rank.ACE:
            self._value = 1

    def restore_high_ace(self) -> None:
        if self.rank is Rank.ACE:
            self._value = 11

    def get_ascii_lines(self) -> List[str]:
        """Returns the list of ascii lines to be able to print them"""
        if self.hidden:
            return self._get_lines_hidden()
        return self._get_lines_face()
    
    def print_card(self) -> None:
        """Prints card as ascii drawing"""
        print('\n'.join(line for line in self.get_ascii_lines()))

    @property
    def value(self) -> int:
        return self._value
    
    @property
    def rank(self) -> Rank:
        return self._rank
    
    @property
    def suit(self) -> Suit:
        return self._suit
    
    @property
    def hidden(self) -> bool:
        return self._hidden
    
    @hidden.setter
    def hidden(self, value: bool) -> None:
        self._hidden = value

    def _get_lines_face(self) -> List[str]:
        return FACE_CARD.format(
            stylize(str(self.rank).ljust(2), fg(self._color)), 
            stylize(str(self.suit).ljust(2), fg(self._color)), 
            stylize(str(self.rank).rjust(2), fg(self._color))).split('\n')

    def _get_lines_hidden(self) -> List[str]:
        return HIDDEN_CARD.split('\n')
    
    def __repr__(self) -> str:
        return f'<Card {self.rank}{self.suit}, value: {self.value}>'
    

class CardCollection:
    """A class representing card collection"""

    def __init__(self) -> None:
        self._cards: List[Card] = []

    def add_card(self, card: Card) -> None:
        """Adds one card in the cards list"""
        self._cards.append(card)

    def add_hidden_card(self, card: Card) -> None:
        """Adds one hidden card in the cards list"""
        card.hidden = True
        self._cards.append(card)

    def pop(self) -> Card:
        """Deletes and returns the first card in the collecion"""
        if self._cards:
            return self._cards.pop(0)
        raise CardNotFound
    
    def reset(self) -> None:
        """Erases all cards from the collection"""
        self._cards = []

    def __iter__(self) -> Iterable[Card]:
        return (card for card in self._cards)
    
    def __len__(self) -> int:
        return len(self._cards)
    
    def __getitem__(self, key: int) -> Card:
        try:
            return self._cards[key]
        except IndexError:
            raise CardNotFound
    
    def __delitem__(self, key: int) -> None:
        try:
            del self._cards[key]
        except IndexError:
            raise CardNotFound


class Hand(CardCollection):
    """A class representing a hand (a collection of cards that player has)"""   

    def print_all_cards(self) -> None:
        """Prints all cards as ASCII art"""
        if not self._cards:
            raise CardNotFound        
        print('\n'.join(''.join(line) for line in self.__get_ascii_lines()))

    @property
    def splitable(self):
        """Retruns True if the first 2 cards are of the same rank"""
        return len(self) == 2 and self[0].rank == self[1].rank

    @property
    def score(self) -> int:
        """Returns deck cards combined value"""
        value = self.__get_all_cards_value()
        if value > 21:
            value = self.__modify_aces_values(value)
        return value        

    def __get_ascii_lines(self) -> zip:
        return zip(*(card.get_ascii_lines() for card in self._cards))
    
    def __get_all_cards_value(self) -> int:
        return sum(card.value for card in self._cards)
    
    def __modify_aces_values(self, value: int) -> int:
        high_ace = self.__get_high_ace_or_none()
        while high_ace and value > 21:
            high_ace.detract_ace_value()
            value = self.__get_all_cards_value()
            high_ace = self.__get_high_ace_or_none()
        return value
    
    def __get_high_ace_or_none(self) -> Optional[Card]:
        for card in self._cards:
            if card.rank is Rank.ACE and card.value == 11:
                return card


class Deck(CardCollection):
    """A class representing a playing deck of cards"""

    def refill(self, decks_quantity: int=config.DECKS_QUANTITY) -> None:
        """Filling the collections with new cards using the quantity of decks of cards indicated in decks_quantity"""
        self._cards = [Card(rank, suit) for rank in Rank for suit in Suit for _ in range(decks_quantity)]
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffles the collection of cards"""
        shuffle(self._cards)
        