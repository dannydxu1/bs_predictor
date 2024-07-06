class BattleLogTracker:
    def __init__(self):
        self.duplicate_battles = 0
        self.unique_battles = 0
        self.processed_battles = set()

    def update_unique_battles(self):
        self.unique_battles += 1
    
    def update_duplicate_battles(self):
        self.duplicate_battles += 1

    def get_counters(self):
        return self.duplicate_battles, self.unique_battles

    def add_processed_battle(self, battle_hash):
        self.processed_battles.add(battle_hash)

    def is_battle_processed(self, battle_hash):
        return battle_hash in self.processed_battles

class BrawlerStats:
    def __init__(self):
        self.brawler_winrates = {}
        self.brawler_pickrates = {}

    def update_brawler_stats(self, brawler_name, win_status):
        result = "victory" if win_status else "defeat"
        if brawler_name not in self.brawler_winrates:
            self.brawler_pickrates[brawler_name] = 1
            self.brawler_winrates[brawler_name] = {"win": 0, "loss": 0}
        else:
            self.brawler_pickrates[brawler_name] += 1
        if result == "victory":
            self.brawler_winrates[brawler_name]["win"] += 1
        elif result == "defeat":
            self.brawler_winrates[brawler_name]["loss"] += 1

    def calculate_win_rates(self):
        for brawler, stats in self.brawler_winrates.items():
            total_games = stats['win'] + stats['loss']
            stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0

    def get_stats(self):
        return self.brawler_winrates, self.brawler_pickrates
