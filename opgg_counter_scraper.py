import re
import json
import os
from itertools import combinations


import requests
from bs4 import BeautifulSoup as bs

BASE_URL = "http://www.op.gg/champion/ajax/statistics/counterChampion/"
MATCHUP_REGEX = r".*?(?=%)"


class OpggMatchupScraper:
    def __init__(self):
        if os.path.isfile("opgg_matchup_data.json"):
            with open("opgg_matchup_data.json", mode="r", encoding="utf-8") as f:
                self.matchup_data = json.load(f)
        else:
            self.matchup_data = {}

    def get_best_combination(self, number_of_champions):
        self.fetch_matchup_data()
        self.parse_superior_data()
        with open("opgg_superior_data.json", mode="r", encoding="utf-8") as f:
            superior_data = json.load(f)

        champions = [name for name in superior_data]
        combination = list(combinations(champions, number_of_champions))

        max_opponents = 0
        for case in combination:
            superior_opponents = []

            for champion in case:
                superior_opponents = superior_opponents + superior_data[champion]
                superior_opponents.append(champion)

            superior_opponents = list(set(superior_opponents))
            number_of_superior_opponents = len(superior_opponents)

            if number_of_superior_opponents >= max_opponents:
                print(
                    "{} 조합 : {}개 카운터 가능".format(
                        " + ".join(case), number_of_superior_opponents
                    )
                )
                if len(set(champions) - set(superior_opponents)) > 0:
                    print("{} 는 불가능\n".format(set(champions) - set(superior_opponents)))
                else:
                    print("현재 탑에 픽되는 모든 챔피언 카운터 가능\n")
                max_opponents = number_of_superior_opponents

    def fetch_matchup_data(self):
        if os.path.isfile("opgg_matchup_data.json"):
            return

        self.opgg_champion_ids = {}
        self.fetch_top_champion_ids()

        for champion_id in self.opgg_champion_ids:
            for target_champion_id in self.opgg_champion_ids:
                matchup_name = "{}-{}".format(champion_id, target_champion_id)
                print(matchup_name)

                if self.is_same_id(champion_id, target_champion_id):
                    continue

                elif self.is_data_already_fetched(target_champion_id, champion_id):
                    print("skip")
                    continue

                elif self.is_data_already_fetched(champion_id, target_champion_id):
                    print("in file.")
                    matchup_name_in_data = "{}-{}".format(
                        target_champion_id, champion_id
                    )
                    data = [
                        matchup_name,
                        self.matchup_data[matchup_name_in_data][2],
                        self.matchup_data[matchup_name_in_data][1],
                        100 - self.matchup_data[matchup_name_in_data][3],
                        100 - self.matchup_data[matchup_name_in_data][4],
                        str((-1) * int(self.matchup_data[matchup_name_in_data][5])),
                    ]
                    print(data)

                else:
                    try:
                        print("fetch.")
                        data = self.parse_matchup_data(
                            matchup_name, champion_id, target_champion_id
                        )
                    except IndexError:
                        print("no data.")
                        continue

                self.matchup_data[matchup_name] = data

        with open("opgg_matchup_data.json", encoding="utf-8", mode="w") as f:
            json.dump(self.matchup_data, f, ensure_ascii=False)

    def fetch_top_champion_ids(self):
        # picked Garen due to pick ratio.
        url = "http://www.op.gg/champion/garen/statistics/top/matchup"
        headers = {"Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"}
        response = requests.get(url, headers=headers)
        soup = bs(response.text, "html.parser")
        matchup_champion_elements = soup.select(
            "div.champion-matchup-champion-list > div"
        )

        champions_ids = [i["data-champion-id"] for i in matchup_champion_elements]
        champion_names = [i["data-champion-name"] for i in matchup_champion_elements]

        for idx, value in enumerate(champions_ids):
            self.opgg_champion_ids[value] = champion_names[idx]

    def is_same_id(self, champion_id, target_champion_id):
        return champion_id == target_champion_id

    def is_data_already_fetched(self, champion_id, target_champion_id):
        return "{}-{}".format(target_champion_id, champion_id) in self.matchup_data

    def parse_matchup_data(self, matchup_name, champion_id, target_champion_id):
        url = "{}championId={}&targetChampionId={}&position=top".format(
            BASE_URL, champion_id, target_champion_id
        )
        response = requests.get(url)
        soup = bs(response.text, "html.parser")

        matchup_data_list = soup.select("tbody > tr")

        lane_kill = float(
            re.compile(MATCHUP_REGEX).search(matchup_data_list[0].text.strip()).group()
        )

        win_rate = float(
            re.compile(MATCHUP_REGEX).search(matchup_data_list[5].text.strip()).group()
        )

        if lane_kill > 50 and win_rate > 50:
            data = [
                matchup_name,
                self.opgg_champion_ids[champion_id],
                self.opgg_champion_ids[target_champion_id],
                lane_kill,
                win_rate,
                "1",
            ]

        elif lane_kill < 50 and win_rate < 50:
            data = [
                matchup_name,
                self.opgg_champion_ids[champion_id],
                self.opgg_champion_ids[target_champion_id],
                lane_kill,
                win_rate,
                "-1",
            ]

        else:
            data = [
                matchup_name,
                self.opgg_champion_ids[champion_id],
                self.opgg_champion_ids[target_champion_id],
                lane_kill,
                win_rate,
                "0",
            ]

        print(data)

        return data

    def parse_superior_data(self):
        temp_list = []
        superior_data = {}

        for champion_id in self.matchup_data:
            if self.matchup_data[champion_id][5] == "1":
                if len(temp_list) == 0:
                    champion_name = self.matchup_data[champion_id][1]
                    temp_list.append(self.matchup_data[champion_id][2])

                elif self.matchup_data[champion_id][1] == champion_name:
                    temp_list.append(self.matchup_data[champion_id][2])

                elif self.matchup_data[champion_id][1] != champion_name:
                    superior_data[champion_name] = temp_list

                    temp_list = []
                    champion_name = self.matchup_data[champion_id][1]
                    temp_list.append(self.matchup_data[champion_id][2])

        with open("opgg_superior_data.json", encoding="utf-8", mode="w") as f:
            json.dump(superior_data, f, ensure_ascii=False)

    def parse_counter_champion(self,champion_name):
        for matchup_name in self.matchup_data:
            if self.matchup_data[matchup_name][1] == champion_name:
                if self.matchup_data[matchup_name][5] == "-1":
                    print(self.matchup_data[matchup_name])


                

if __name__ == "__main__":
    opgg_scraper = OpggMatchupScraper()
    # opgg_scraper.get_best_combination(4)
    opgg_scraper.parse_counter_champion("퀸")
