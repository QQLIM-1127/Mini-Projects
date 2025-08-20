import random
class Card:
    def __init__(self,suit,rank):
        self.rank=rank
        self.suit=suit

    def shortened(self):
        return "{}{}".format(self.suit,self.rank)
    
    def ascii_art(self):
        return [
        "┌─────┐",
        f"|{self.rank:<2}   |",
        f"|  {self.suit}  |",
        f"|   {self.rank:>2}|",
        "└─────┘"
    ]

    def __str__(self):
        return "\n".join(self.ascii_art())



class Deck:
    def __init__(self):
        self.deck=[]
        suits=["♠", "♥", "♦", "♣"]
        ranks=["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
        for i in range(len(suits)):
            for j in range(len(ranks)):
                self.deck.append(Card(suits[i],ranks[j]))
        random.shuffle(self.deck)

    def deal(self):
        return self.deck.pop()


class Hand:
    def __init__(self):
        self.cards=[]
        self.total=0
        self.trigger=True
    
    def add_card(self,card):
        self.cards.append(card)
        self.calculate()
        if self.total>21:
            self.bust()

    def calculate(self):
        total=0
        aces=0
        for i in range(len(self.cards)):
            number=self.cards[i].rank
            if number.isdigit():
                total+=int(number)
            else:
                if number in ["K","Q","J"]:
                    total+=10
                else:
                    total+=11
                    aces+=1
        while total>21 and aces>0:
            total-=10
            aces-=1
        self.total=total

    def bust(self):
        print("BUSTED!!")
        self.trigger=False

    def display_hand(self):
        card_display=[i.ascii_art() for i in self.cards]
        for line in zip(*(card_display)):
            print(" ".join(line))

    def display_hidden_hand(self):
        if len(self.cards)>=2:
            hidden_card = [
                "┌─────┐",
                "|     |",
                "|  ?  |",
                "|     |",
                "└─────┘"
            ]
            visible_cards = [hidden_card] + [card.ascii_art() for card in self.cards[1:]]
            for line in zip(*visible_cards):
                print(" ".join(line))
        else:
            self.display_hand()

def dealer_turn(dealer_hand,deck):
    print("\n=== DEALER'S TURN ===")
    print("Dealer reveals hidden card:")
    dealer_hand.display_hand()
    print(f"Dealer's total: {dealer_hand.total}")
    
    while dealer_hand.total < 17 and dealer_hand.trigger:
        print("\nDealer hits...")
        dealer_hand.add_card(deck.deal())
        dealer_hand.display_hand()
        print(f"Dealer's total: {dealer_hand.total}")
        
        if not dealer_hand.trigger:  # Dealer busted
            return dealer_hand.total
    
    if dealer_hand.trigger:  # Dealer didn't bust
        print(f"\nDealer stands with {dealer_hand.total}")
    
    return dealer_hand.total

def determine_winner(player_hand, dealer_hand, bet_amount):
    """Determine the winner and calculate winnings"""
    player_total = player_hand.total
    dealer_total = dealer_hand.total
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Player total: {player_total}")
    print(f"Dealer total: {dealer_total}")
    print(f"Bet amount: ${bet_amount}")
    
    # Check for blackjack (21 with 2 cards) - pays 3:2
    player_blackjack = len(player_hand.cards) == 2 and player_total == 21
    dealer_blackjack = len(dealer_hand.cards) == 2 and dealer_total == 21
    
    if player_blackjack and dealer_blackjack:
        print("PUSH - Both have blackjack!")
        return 0  # No money won or lost
    elif player_blackjack:
        winnings = int(bet_amount * 1.5)  # 3:2 payout
        print(f"BLACKJACK! PLAYER WINS ${winnings}!")
        return winnings
    elif dealer_blackjack:
        print("DEALER BLACKJACK - Player loses!")
        return -bet_amount
    
    # Check for busts
    if not player_hand.trigger:  # Player busted
        print("DEALER WINS - Player busted!")
        return -bet_amount
    elif not dealer_hand.trigger:  # Dealer busted
        print("PLAYER WINS - Dealer busted!")
        return bet_amount
    
    # Both hands are valid, compare totals
    if player_total > dealer_total:
        print("PLAYER WINS!")
        return bet_amount
    elif dealer_total > player_total:
        print("DEALER WINS!")
        return -bet_amount
    else:
        print("PUSH (TIE) - No money changes hands!")
        return 0

def game_start():
    c=True
    while c:
        text=input("Type 'yes' to play: ")
        if text.lower()=="yes":
            c=False

def game():
    # Initialize player money
    player_money = 100  # Starting money
    
    while player_money > 0:
        print(f"\n=== NEW HAND ===")
        print(f"Your money: ${player_money}")
        # Get bet amount
        while True:
            try:
                bet = int(input(f"Enter your bet (1-{player_money}): $"))
                if 1 <= bet <= player_money:
                    break
                else:
                    print(f"Bet must be between $1 and ${player_money}")
            except ValueError:
                print("Please enter a valid number")
        
        deck = Deck()
        dealer = Hand()
        player = Hand()
        
        # Deal initial cards
        for i in range(2):
            dealer.add_card(deck.deal())
            player.add_card(deck.deal())
        
        # Show initial hands
        print("\n=== INITIAL DEAL ===")
        print("Dealer's hand (one card hidden):")
        dealer.display_hidden_hand()
        print(f"Dealer's visible card: {dealer.cards[1].rank if len(dealer.cards) > 1 else '?'}")
        
        print("\nYour hand:")
        player.display_hand()
        print(f"Your total: {player.total}")
        
        # Check for player blackjack
        if player.total == 21:
            print("BLACKJACK!")
        else:
            # Player's turn
            while player.trigger:
                choice = input("\nHit or Stand? ").lower()
                if choice == "hit":
                    player.add_card(deck.deal())
                    print("\nYour hand:")
                    player.display_hand()
                    print(f"Your total: {player.total}")
                elif choice == "stand":
                    break
                else:
                    print("Please enter 'hit' or 'stand'")
        
        # Dealer always plays (important for money games!)
        dealer_turn(dealer, deck)
        
        # Determine winner and update money
        winnings = determine_winner(player, dealer, bet)
        player_money += winnings
        
        if player_money <= 0:
            print("\nYou're out of money! Game over!")
            break
        
        # Ask to continue
        continue_game = input("\nContinue playing? (yes/no): ").lower()
        if continue_game != "yes":
            break
    
    print(f"\nThanks for playing! Final money: ${player_money}")

if __name__ == "__main__":
    game_start()
    game()
        





