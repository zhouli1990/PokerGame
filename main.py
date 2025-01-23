from module import PokerDealer,Player,PointModule,insert_game_head,insert_players
from treys import Card
import mysql.connector

# 主程序
if __name__ == "__main__":
    # 建立数据库连接
    try:
        cnx = mysql.connector.connect(
            host="localhost",
            user="root",
            password= "",
            database="poker",
            autocommit=True
        )
        # 创建游标对象，用于执行 SQL 语句
        cursor = cnx.cursor()

        # 创建初始化牌堆和玩家
        poker = PokerDealer()
        community_cards = []
        # 玩家人数
        player_num = 7
        # 玩家入局基础筹码
        player_basic_chips = 1000
        # 小盲注金额
        small_blind = 10
        # 大盲注金额
        big_blind = 20

        # 玩家列表
        playerlist = []
        # 创建玩家对象并添加到玩家列表
        for i in range(1, player_num + 1):
            player = Player(f"player{i}")
            playerlist.append(player)

        # 插入 game_head 数据并获取 game_head_id
        game_head_id = insert_game_head(cnx, cursor, player_num, small_blind, big_blind)
        if game_head_id:
            # 插入玩家数据
            insert_players(cnx, cursor, game_head_id, playerlist, player_basic_chips)

    except mysql.connector.Error as err:
        print(err)
    finally:
        # 关闭游标和连接
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()

    # 重置牌堆和玩家手牌
    poker.reset_deck()
    for i in range(1, player_num + 1):
        player.clear_hand()

    # 玩家获取底牌（Hole Cards）
    for player in playerlist:
        player.receive_cards(poker.deal_cards(2))
        print(f"{player.name}:{player.show_hand_str()}")

    players_module = PointModule(playerlist, community_cards, poker.show_remaining_cards())
    # 计算玩家胜率
    actual_win_rate = players_module.monteCarlo_model(10000)
    print(f"胜率:{actual_win_rate}")

    # 发出‌翻牌（Flop）
    community_cards.extend(poker.deal_cards(3))
    print(f"公共牌（3）: {[Card.int_to_pretty_str(card)[1:-1] for card in community_cards]}")
    flop_module = PointModule(playerlist, community_cards, poker.show_remaining_cards())
    # 计算翻牌后玩家胜率
    actual_win_rate = flop_module.monteCarlo_model(10000)
    print(f"胜率:{actual_win_rate}")

    # 发出转牌（Turn）
    community_cards.extend(poker.deal_cards(1))
    print(f"公共牌（4）:  {[Card.int_to_pretty_str(card)[1:-1] for card in community_cards]}")
    trun_module = PointModule(playerlist, community_cards, poker.show_remaining_cards())
    # 计算转牌后玩家胜率
    actual_win_rate = trun_module.monteCarlo_model(5000)
    print(f"胜率:{actual_win_rate}")

    # 发出河牌（River）
    community_cards.extend(poker.deal_cards(1))
    print(f"公共牌（5）: {[Card.int_to_pretty_str(card)[1:-1] for card in community_cards]}")
    river_module = PointModule(playerlist, community_cards, poker.show_remaining_cards())
    # 计算河牌后玩家胜率
    actual_win_rate = river_module.monteCarlo_model(2000)
    print(f"胜率:{actual_win_rate}")