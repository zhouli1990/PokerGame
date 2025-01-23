import mysql.connector
from mysql.connector import errorcode
from treys import Card, Deck
from treys import Evaluator
import itertools
import random
import datetime


class PokerDealer:
    def __init__(self):
        """
        初始化一个发牌器，包含一副标准扑克牌。
        """
        self.deck = Deck()

    def deal_cards(self, n):
        """
        从牌堆中抽取 n 张牌。

        Args:
            n (int): 要发的牌数量。

        Returns:
            list: 发出的牌，使用 treys 的整数编码表示。
        """
        if n > len(self.deck.cards):
            raise ValueError("牌堆中剩余的牌不足以发出所需的数量。")
        return [self.deck.draw(1)[0] for _ in range(n)]

    def len_remaining_cards(self):
        """
        获取当前牌堆剩余的牌数量。

        Returns:
            int: 剩余的牌数量。
        """
        return len(self.deck.cards)

    def show_remaining_cards(self):
        """
        获取当前牌堆剩余的牌。

        Returns:
            int: 剩余的牌。
        """
        return self.deck.cards

    def reset_deck(self):
        """
        重置牌堆为一副完整的 52 张扑克牌。
        """
        self.deck = Deck()


class Player:
    def __init__(self, name):
        """
        初始化玩家对象。

        Args:
            name (str): 玩家名称。
        """
        self.name = name  # 玩家名称
        self.hand = []    # 玩家手牌（初始为空列表）

    def receive_cards(self, cards):
        """
        接收发到的牌，并添加到手牌中。

        Args:
            cards (list): 一组用 treys 整数编码表示的牌。
        """
        self.hand.extend(cards)

    def show_hand_str(self):
        """
        展示玩家的手牌(str)。

        Returns:
            list: 人类可读格式的手牌（str 列表）。
            ['J♠', 'Q♠']]
        """
        return [Card.int_to_pretty_str(card)[1:-1] for card in self.hand]   # 返回 str

    def show_hand(self):
        """
        展示玩家的手牌(int)。

        Returns:
            list: 玩家手牌（int 列表）。
            [67115551, 2131213]
        """
        return self.hand   # 返回 int [69634, 16783383]

    def player_info(self):
        """
        查询玩家信息。
        {
            'name': 'player1',
            'hand':
                [
                    67115551,
                    2131213
                ]
        }
        """
        return {
            "name": self.name,
            "hand": self.show_hand()
        }

    def clear_hand(self):
        """
        清空玩家的手牌，用于新一局游戏。
        """
        self.hand = []


class PointModule:
    def __init__(self, playerlist, board, remaining_cards):
        self.playerlist = playerlist
        self.board = board
        self.remaining_cards = remaining_cards
        self.evaluator = Evaluator()

    # 蒙特卡洛分析得分模型，传入循环次数
    def monteCarlo_model(self, iterations):
        """
        蒙特卡洛分析模型。

        Args:
            iterations (int): 循环次数。

        Returns:
            win_rates_list（list）: 玩家胜率。
        """
        num_board_cards_needed = 5 - len(self.board)
        if num_board_cards_needed < 0:
            raise ValueError("公共牌数量不能超过 5 张。")

        # 用于记录每个玩家的胜利次数
        player_win_counts = {player: 0 for player in self.playerlist}

        for _ in range(iterations):
            # 复制剩余牌堆，避免修改原始牌堆
            remaining_cards_copy = self.remaining_cards.copy()
            # 随机抽取公共牌至 5 张
            board_combination = self.board + random.sample(remaining_cards_copy, num_board_cards_needed)
            # print(board_combination)

            # 计算每个玩家的分数
            scores = []
            for player in self.playerlist:
                score = self.evaluator.evaluate(player.hand, board_combination)
                scores.append((player, score))
                # print(player.name,score)

            # 找出最小分数（最好的牌型）
            scores.sort(key=lambda x: x[1])
            min_score = scores[0][1]
            # print(min_score)
            winners = [player for player, score in scores if score == min_score]
            # print(winners)

            # 平局分配胜利
            for winner in winners:
                player_win_counts[winner] += 1 / len(winners)

        # 计算胜率
        player_win_rates = {player: player_win_counts[player] / iterations for player in self.playerlist}
        # 转换为包含玩家名称和胜率的列表
        win_rates_list = []
        for player, win_rate in player_win_rates.items():
            win_rates_list.append({
                "name": player.name,
                "win_rate": f"{round(win_rate * 100):.2f}%"  # 四舍五入到小数点后两位，并转换为百分比字符串
            })
        return win_rates_list


def insert_game_head(cnx, cursor, player_num, small_blind, big_blind):
    """
    插入 game_head 表数据，并处理异常。

    Args:
        cnx (mysql.connector.connection.MySQLConnection): 数据库连接对象。
        cursor (mysql.connector.cursor.MySQLCursor): 数据库游标对象。
        player_num (int): 玩家数量。
        small_blind (int): 小盲注金额。
        big_blind (int): 大盲注金额。

    Returns:
        int: 插入的 game_head 记录的 id，如果插入失败返回 None。
    """
    try:
        # 获取当前日期，格式为 YYYYMMDD
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        # 查询当天已有的桌子数量
        query_count = ("SELECT COUNT(*) FROM game_head WHERE table_id LIKE %s")
        cursor.execute(query_count, (date_str + "%",))
        # print(cursor.statement) # 打印table_id流水查询SQL
        count = cursor.fetchone()[0]
        # 生成 4 位流水号，使用 zfill 方法补零
        serial_num = str(count + 1).zfill(2)
        # 组合成最终的 table_id
        table_id = date_str + serial_num
        # print(table_id) # 打印table_id
        # 定义插入 game_head 表的 SQL 语句，使用占位符 %s 表示参数
        add_game_head = ("INSERT INTO game_head "
                       "(table_id, player_num, small_blind, big_blind) "
                       "VALUES (%s, %s, %s, %s)")
        # 存储要插入的数据，包括 table_id、player_num、small_blind 和 big_blind
        game_head_data = (table_id, player_num, small_blind, big_blind)
        # 打印插入语句和数据，方便调试
        # print("Insert statement:", add_game_head)
        # print("Insert data:", game_head_data)
        # 执行插入操作
        cursor.execute(add_game_head, game_head_data)
        print(cursor.statement) # 打印game_heads插入SQL
        # 提交事务，将数据持久化到数据库
        cnx.commit()
        print("game_head 数据插入成功")
        # 返回插入的 game_head 记录的 id
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print(f"Error(insert_game_head):{err}")
        return None


def insert_players(cnx, cursor, game_head_id, playerlist, player_basic_chips):
    """
    插入 players 表数据，并处理异常。

    Args:
        cnx (mysql.connector.connection.MySQLConnection): 数据库连接对象。
        cursor (mysql.connector.cursor.MySQLCursor): 数据库游标对象。
        game_head_id (int): game_head 表的记录 id。
        playerlist (list): 玩家列表。
        player_basic_chips (float): 玩家的基础筹码。
    """

    # 定义插入 players 表的 SQL 语句，使用占位符 %s 表示参数
    add_players = ("INSERT INTO players "
                    "(game_head_id, number, name, seat_position, player_basic_chips) "
                    "VALUES (%s, %s, %s, %s, %s)")
    # 遍历 playerlist，为每个玩家插入数据
    for i, player in enumerate(playerlist):
        # 存储玩家的信息，包括 game_head_id、number、name、seat_position 和 player_basic_chips
        player_data = (game_head_id, i + 1, player.name, i + 1, player_basic_chips)
        # 执行插入操作
        try:
            cursor.execute(add_players, player_data)
            print(cursor.statement) # 打印players插入SQL
        except mysql.connector.Error as err:
            print(f"Error(insert_players):{err}")
            return None
    # 提交事务，将数据持久化到数据库
    cnx.commit()
    print("players 数据插入成功")
