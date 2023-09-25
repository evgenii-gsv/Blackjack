import sys
from time import sleep
from typing import Iterable, Optional, Tuple

import inquirer

from .player import Player, Dealer
from .cards import Deck, Hand, Rank
from . import config
from .exceptions import StopGame, HandSplitting
from .messages import Message


class Game:
    ACTIONS = 'Hit', 'Stand'

    def __init__(self) -> None:
        pass

    def init(self) -> None:
        self.deck = Deck()
        self.deck.refill()
        self.player = Player(chips=config.INITIAL_CHIPS_QUANTITY)
        self.dealer = Dealer()

    def start(self) -> None:
        self.init()
        self._show_intro()
        try:
            self._play_game()
        except StopGame:
            self._stop_game()
            
    def _play_game(self) -> None:
        while True:
            self._play_round()
            if self.player.chips <= 0:
                self._lost_game()
            if len(self.deck) <= config.REMAKE_DECK_AFTER:
                self.deck.refill()
                print(Message.RESHUFFLING)
            
    def _play_round(self) -> None:
        split_score = split_blackjack = split_bet = None
        bet = self.player.make_bet()
        self._give_initial_cards_to_player_and_dealer()
        self._show_hand_cards(self.dealer.hand, dealer=True)

        if self.dealer.hand[1].rank is Rank.ACE:
            insurance_bet = self._check_for_insurance(bet)
            print(Message.CHECKING_FOR_DEALER_BLACKJACK)
            self._sleep()
            dealer_blackjack = self._check_for_dealer_blackjack()
            if dealer_blackjack:
                self._dealer_blackjack(bet, insurance_bet)
                return
            else:
                print(Message.NO_DEALER_BLACKJACK)
        
        try:
            score, bet, blackjack = self._play_player_hand(self.player.hand, bet)
            if blackjack:
                self._player_blackjack(bet)
                return
            if score is None:
                self._player_busted(bet=bet)
                return
        except HandSplitting:
            split_bet = self.player.make_quiet_bet(bet)
            self._split_hands()

            print(Message.FIRST_SPLITTED_HAND)
            split_score, split_bet, split_blackjack = self._play_player_hand(self.player.split_hand, split_bet, can_split=False)
            if split_blackjack:
                self._player_blackjack(split_bet)
            if split_score is None:
                self._player_busted(bet=split_bet)

            print(Message.SECOND_SPLITTED_HAND)
            score, bet, blackjack = self._play_player_hand(self.player.hand, bet, can_split=False)
            if blackjack:
                self._player_blackjack(bet)
            if score is None:
                self._player_busted(bet=bet)
            if (score is None and split_score is None) or (blackjack is True and split_blackjack is True):
                return
            
        player_scores_and_bets = tuple()
        if score and blackjack is False:
            player_scores_and_bets += ((score, bet),)
        if split_score and split_blackjack is False:
            player_scores_and_bets += ((split_score, split_bet),)
        
        dealer_score = self._play_dealer_hand(self.dealer.hand)
        if dealer_score is None:
            self._dealer_busted(player_scores_and_bets)
            return
        self._define_winner(player_scores_and_bets, dealer_score)

    def _play_player_hand(self, hand: Hand, bet: int, can_split: bool=True) -> Tuple[Optional[int], int, bool]:
        self._show_hand_cards(hand)
        if hand.score == 21:
            return hand.score, bet, True
            
        while hand.score < 21:
            actions = self._get_possible_actions(hand, bet, can_split)
            choice = self.player.choose_action(actions, hand)
            match choice:
                case 'Hit':
                    self._hit(hand)
                case 'Stand':
                    break
                case 'Split':
                    raise HandSplitting
                case 'Double Down':
                    bet = self._double_down(hand, bet)
                    break
                case _:
                    pass
            self._show_hand_cards(hand)
        self._sleep()
        return (hand.score, bet, False) if hand.score < 22 else (None, bet, False) 
     
    def _play_dealer_hand(self, hand: Hand) -> Optional[int]:
        hand[0].hidden = False
        self._show_hand_cards(hand, dealer=True)
        while hand.score < 17:
            self._sleep()
            self._give_card_from_deck(hand)
            self._show_hand_cards(hand, dealer=True)
        return hand.score if hand.score < 22 else None
    
    def _split_hands(self) -> None:
        for card in self.player.hand: # type: ignore
            card.restore_high_ace()
        self.player.split_hand.add_card(self.player.hand.pop())
        self._give_card_from_deck(self.player.hand)
        self._give_card_from_deck(self.player.split_hand)

    def _show_intro(self) -> None:
        print(Message.WELCOME.format(dealer_stands_on=config.DEALER_STANDS_ON))

    def _lost_game(self) -> None:
        input(Message.LOST_GAME)
        sys.exit()

    def _stop_game(self) -> None:
        message = self._get_finish_message()        
        input(message)
        sys.exit()

    def _get_finish_message(self) -> str:
        delta = abs(config.INITIAL_CHIPS_QUANTITY - self.player.chips)
        if self.player.chips < config.INITIAL_CHIPS_QUANTITY:
            message = Message.FINISH_GAME_BAD.format(chips=self.player.chips, delta=delta)
        elif self.player.chips > config.INITIAL_CHIPS_QUANTITY:
            message = Message.FINISH_GAME_GOOD.format(chips=self.player.chips, delta=delta)
        else:
            message = Message.FINISH_GAME_NEUTRAL.format(chips=self.player.chips)
        return message
    
    def _give_card_from_deck(self, hand: Hand, hidden: bool=False) -> None:
        if hidden:
            hand.add_hidden_card(self.deck.pop())
        else:
            hand.add_card(self.deck.pop())

    def _give_initial_cards_to_player_and_dealer(self) -> None:
        self._reset_all_hands()
        self._give_card_from_deck(self.dealer.hand, hidden=True)
        self._give_card_from_deck(self.player.hand)
        self._give_card_from_deck(self.dealer.hand)
        self._give_card_from_deck(self.player.hand)

    def _show_hand_cards(self, hand: Hand, dealer: bool=False) -> None:
        print(Message.DEALER_CARDS if dealer else Message.PLAYER_CARDS)
        hand.print_all_cards()
        print('\n' if any(card.hidden for card in hand) else Message.HAND_SCORE.format(score=hand.score)) # type: ignore

    def _get_possible_actions(self, hand: Hand, bet: int, can_split: bool) -> Tuple[str, ...]:
        actions = self.ACTIONS
        enough_chips = self.player.chips - bet >= 0
        if enough_chips:
            actions += 'Double Down',
        if hand.splitable and can_split and enough_chips:
            actions += 'Split',
        return actions
    
    def _check_for_insurance(self, bet: int) -> Optional[int]:
        insurance = inquirer.list_input(
            message=Message.INSURANCE_PROMPT.format(chips=self.player.chips),
            choices=('Yes', 'No')
        )
        if insurance == 'No':
            return
        insurance_bet = self.player.make_insurance_bet(possible_bet=int(bet / 2))
        return insurance_bet
    
    def _check_for_dealer_blackjack(self) -> bool:
        return self.dealer.hand.score == 21
     
    def _hit(self, hand: Hand) -> None:
        self._give_card_from_deck(hand)

    def _double_down(self, hand: Hand, bet: int) -> int:
        self._hit(hand)
        print(Message.PLAYER_DOUBLE_DOWN.format(chips=bet))
        bet += self.player.make_quiet_bet(bet)
        self._show_hand_cards(hand)
        return bet
    
    def _player_blackjack(self, bet: int) -> None:
        print(Message.PLAYER_BLACKJACK.format(chips=int(bet * 1.5)))
        self.player.add_chips(int(bet + bet*1.5))

    def _dealer_blackjack(self, bet: int, insurance_bet: Optional[int]) -> None:
        self.dealer.hand[0].hidden = False
        self._show_hand_cards(self.dealer.hand, dealer=True)
        if not insurance_bet:
            print(Message.DEALER_BLACKJACK.format(bet=bet))
        else:
            self.player.add_chips(insurance_bet * 2)
            print(Message.DEALER_BLACKJACK_WITH_INSURANCE.format(bet=bet, insurance_bet=insurance_bet))

    def _player_busted(self, bet: int) -> None:
        print(Message.PLAYER_BUSTED.format(bet=bet))

    def _dealer_busted(self, player_scores_and_bets: Iterable[Tuple[int, int]]) -> None:
        sum_of_bets = 0
        for score, bet in player_scores_and_bets:
            sum_of_bets += bet
        print(Message.DEALER_BUSTED.format(bet=sum_of_bets))
        self.player.add_chips(sum_of_bets * 2)

    def _player_won(self, player_score: int, dealer_score: int, bet: int) -> None:
        print(Message.PLAYER_WON.format(
            player_score=player_score,
            dealer_score= dealer_score,
            bet=bet
            ))
        self.player.add_chips(bet * 2)

    def _dealer_won(self, player_score: int, dealer_score: int, bet: int) -> None:
        print(Message.DEALER_WON.format(
            player_score=player_score,
            dealer_score= dealer_score,
            bet=bet
            ))
        
    def _draw(self, player_score: int, bet: int) -> None:
        print(Message.DRAW.format(
            score=player_score
        ))
        self.player.add_chips(bet)
        
    def _define_winner(self, player_scores_and_bets: Iterable[Tuple[int, int]], dealer_score: int) -> None:
        for player_score, bet in player_scores_and_bets:
            if player_score > dealer_score:
                self._player_won(player_score, dealer_score, bet)
            elif player_score < dealer_score:
                self._dealer_won(player_score, dealer_score, bet)
            else:
                self._draw(player_score, bet)

    def _reset_all_hands(self) -> None:
        self.player.reset_hands()
        self.dealer.reset_hands()

    def _sleep(self):
        sleep(1)
        