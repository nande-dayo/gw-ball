import pyxel

# 画面サイズ
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120

# 色の定義（Pyxelデフォルトパレット）
# 7: 白, 0: 黒, 1: 濃紺, 5: 濃灰, 9: オレンジ, 13: 薄灰
COLOR_BG = 7        # 液晶の背景（薄い色）
COLOR_LCD = 0       # 液晶の表示（黒）
COLOR_SHADOW = 13   # 液晶の非点灯スロット（うっすら見える跡）

# キャッチゾーン（0:左外, 1:左内, 2:右内, 3:右外）
# プレイヤーの手のポジション（0:左, 1:中, 2:右）における左右の手：
# - 位置0 (左構え): 左手=外(0), 右手=内(2) -> カバー: [0, 2]
# - 位置1 (中構え): 左手=内(1), 右手=内(2) -> カバー: [1, 2]
# - 位置2 (右構え): 左手=内(1), 右手=外(3) -> カバー: [1, 3]
PLAYER_HANDS = {
    0: {"left": 0, "right": 2},
    1: {"left": 1, "right": 2},
    2: {"left": 1, "right": 3},
}

PLAYER_COVERAGE = {
    0: (0, 2),
    1: (1, 2),
    2: (1, 3),
}

# ゾーンごとの手の座標 (x, y)
HAND_POSITIONS = {
    0: (40, 80),   # 左外
    1: (60, 82),   # 左内（胴体の左脇）
    2: (100, 82),  # 右内（胴体の右脇）
    3: (120, 80),  # 右外
}

# ボールの軌道定義（液晶セグメントの固定コマ座標）
# 軌道A: 左外(0) -> 右外(3)
TRAJECTORY_0_TO_3 = [
    (40, 80), (36, 62), (38, 44), (48, 28), (66, 18), (80, 16),
    (94, 18), (112, 28), (122, 44), (124, 62), (120, 80)
]
# 軌道B: 右外(3) -> 左外(0)
TRAJECTORY_3_TO_0 = list(reversed(TRAJECTORY_0_TO_3))

# 軌道C: 左内(1) -> 右内(2)（低めの内回り軌道）
TRAJECTORY_1_TO_2 = [
    (60, 82), (58, 66), (62, 50), (70, 36), (80, 32), (90, 36),
    (98, 50), (102, 66), (100, 82)
]
# 軌道D: 右内(2) -> 左内(1)
TRAJECTORY_2_TO_1 = list(reversed(TRAJECTORY_1_TO_2))

# 軌道E: 左外(0) -> 右内(2)
TRAJECTORY_0_TO_2 = [
    (40, 80), (38, 62), (42, 46), (54, 32), (70, 24), (86, 28),
    (96, 44), (102, 64), (100, 82)
]
# 軌道F: 右外(3) -> 左内(1)
TRAJECTORY_3_TO_1 = [
    (120, 80), (122, 62), (118, 46), (106, 32), (90, 24), (74, 28),
    (64, 44), (58, 64), (60, 82)
]


class Ball:
    def __init__(self, trajectory, start_zone, end_zone, step_delay=6):
        self.trajectory = trajectory
        self.start_zone = start_zone
        self.end_zone = end_zone
        self.step = 0
        self.max_step = len(trajectory) - 1
        self.step_delay = step_delay
        self.timer = 0
        self.is_caught = False

    def update(self):
        self.timer += 1
        if self.timer >= self.step_delay:
            self.timer = 0
            if self.step < self.max_step:
                self.step += 1
                return True  # 1コマ進んだ
        return False

    def get_pos(self):
        return self.trajectory[self.step]

    def is_at_catch_point(self):
        return self.step == self.max_step


class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="BALL (1980) - Narukichi", fps=30)
        self.setup_sounds()
        self.reset_game(mode="A")
        pyxel.run(self.update, self.draw)

    def setup_sounds(self):
        # 0: ボールコマ送り音（ピッ）
        pyxel.sounds[0].set("a3", "t", "7", "n", 2)
        # 1: キャッチ成功音（ピピッ）
        pyxel.sounds[1].set("c4e4", "t", "7", "f", 4)
        # 2: ゲームオーバー音（ブー）
        pyxel.sounds[2].set("e2c2", "n", "7", "s", 15)

    def reset_game(self, mode="A"):
        self.mode = mode  # "A" (2 balls) or "B" (3 balls)
        self.player_pos = 1  # 0:左, 1:中, 2:右
        self.score = 0
        self.game_over = False
        self.miss_ball_pos = None

        # スピード設定（tick間隔）
        self.step_delay = 7

        # ボール初期化
        # GAME A: 2個（時間差でスタート）
        self.balls = []
        b1 = Ball(TRAJECTORY_0_TO_3, start_zone=0, end_zone=3, step_delay=self.step_delay)
        self.balls.append(b1)

        b2 = Ball(TRAJECTORY_3_TO_0, start_zone=3, end_zone=0, step_delay=self.step_delay)
        b2.step = -5  # 遅れて登場させる
        self.balls.append(b2)

        if self.mode == "B":
            b3 = Ball(TRAJECTORY_1_TO_2, start_zone=1, end_zone=2, step_delay=self.step_delay)
            b3.step = -10
            self.balls.append(b3)

    def next_trajectory(self, current_end_zone):
        """キャッチしたゾーンから次の投球軌道を決定"""
        import random
        if current_end_zone == 0:  # 左外でキャッチ -> 右外または右内へ
            return random.choice([
                (TRAJECTORY_0_TO_3, 0, 3),
                (TRAJECTORY_0_TO_2, 0, 2),
            ])
        elif current_end_zone == 1:  # 左内でキャッチ -> 右内へ
            return (TRAJECTORY_1_TO_2, 1, 2)
        elif current_end_zone == 2:  # 右内でキャッチ -> 左内へ
            return (TRAJECTORY_2_TO_1, 2, 1)
        else:  # 右外(3)でキャッチ -> 左外または左内へ
            return random.choice([
                (TRAJECTORY_3_TO_0, 3, 0),
                (TRAJECTORY_3_TO_1, 3, 1),
            ])

    def update(self):
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset_game(self.mode)
            elif pyxel.btnp(pyxel.KEY_A):
                self.reset_game("A")
            elif pyxel.btnp(pyxel.KEY_B):
                self.reset_game("B")
            return

        # プレイヤー操作（LEFT / RIGHT）
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            if self.player_pos > 0:
                self.player_pos -= 1
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            if self.player_pos < 2:
                self.player_pos += 1

        # ボールの更新
        moved_any = False
        for ball in self.balls:
            if ball.step < 0:
                # 登場待ち
                ball.timer += 1
                if ball.timer >= ball.step_delay:
                    ball.timer = 0
                    ball.step += 1
                continue

            advanced = ball.update()
            if advanced:
                moved_any = True

            # 到達判定
            if ball.is_at_catch_point():
                covered_zones = PLAYER_COVERAGE[self.player_pos]
                if ball.end_zone in covered_zones:
                    # キャッチ成功！
                    pyxel.play(0, 1)
                    if self.mode == "A":
                        self.score += 1
                    else:
                        self.score += 10

                    # 速度アップ調整（スコアに応じて少しずつ速く）
                    if self.score % 10 == 0 and self.step_delay > 3:
                        self.step_delay = max(3, self.step_delay - 1)

                    # 次の軌道へ放り投げる
                    traj, sz, ez = self.next_trajectory(ball.end_zone)
                    ball.trajectory = traj
                    ball.start_zone = sz
                    ball.end_zone = ez
                    ball.step = 0
                    ball.max_step = len(traj) - 1
                    ball.step_delay = self.step_delay
                else:
                    # 取りこぼし！ゲームオーバー
                    pyxel.play(0, 2)
                    self.game_over = True
                    self.miss_ball_pos = ball.get_pos()
                    break

        if moved_any and not self.game_over:
            pyxel.play(0, 0)

    def draw(self):
        # 液晶風の背景色
        pyxel.cls(COLOR_BG)

        # 液晶枠・デザイン
        pyxel.rectb(4, 4, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 8, COLOR_LCD)
        pyxel.text(10, 8, f"GAME {self.mode}", COLOR_LCD)
        pyxel.text(110, 8, f"SCORE {self.score:03d}", COLOR_LCD)

        # 全軌道の「液晶の跡（シャドウ）」をうっすら描画
        for traj in [TRAJECTORY_0_TO_3, TRAJECTORY_1_TO_2, TRAJECTORY_0_TO_2, TRAJECTORY_3_TO_1]:
            for x, y in traj:
                pyxel.circb(x, y, 2, COLOR_SHADOW)

        # ボールの描画（点灯しているもの）
        for ball in self.balls:
            if ball.step >= 0 and ball.step <= ball.max_step:
                bx, by = ball.get_pos()
                pyxel.circ(bx, by, 3, COLOR_LCD)

        # ジャグラー（Mr. Game & Watch）の描画
        self.draw_juggler()

        # ゲームオーバー表示
        if self.game_over:
            pyxel.rect(35, 45, 90, 30, COLOR_BG)
            pyxel.rectb(35, 45, 90, 30, COLOR_LCD)
            pyxel.text(55, 50, "GAME OVER", COLOR_LCD)
            pyxel.text(42, 62, "PRESS R TO RESTART", COLOR_LCD)

        # 操作説明
        pyxel.text(12, 108, "[<- / ->] MOVE HANDS", COLOR_LCD)

    def draw_juggler(self):
        cx = 80
        cy = 82

        # 頭部（丸顔＋尖った鼻）
        pyxel.circ(cx, cy - 22, 6, COLOR_LCD)
        pyxel.rect(cx - 1, cy - 22, 4, 3, COLOR_LCD)  # 鼻

        # 胴体
        pyxel.rect(cx - 5, cy - 15, 10, 16, COLOR_LCD)

        # 足
        pyxel.rect(cx - 6, cy + 1, 4, 12, COLOR_LCD)
        pyxel.rect(cx + 2, cy + 1, 4, 12, COLOR_LCD)
        pyxel.rect(cx - 9, cy + 10, 4, 3, COLOR_LCD)  # つま先左
        pyxel.rect(cx + 5, cy + 10, 4, 3, COLOR_LCD)  # つま先右

        # 腕の描画（player_pos: 0=左, 1=中, 2=右）
        hands = PLAYER_HANDS[self.player_pos]
        left_hand = HAND_POSITIONS[hands["left"]]
        right_hand = HAND_POSITIONS[hands["right"]]

        # 左腕（左側のみ：外0 or 内1）
        if hands["left"] == 0:
            pyxel.line(cx - 5, cy - 10, cx - 25, cy - 4, COLOR_LCD)
            pyxel.line(cx - 25, cy - 4, left_hand[0], left_hand[1], COLOR_LCD)
        else:
            pyxel.line(cx - 5, cy - 10, cx - 14, cy + 1, COLOR_LCD)
            pyxel.line(cx - 14, cy + 1, left_hand[0], left_hand[1], COLOR_LCD)
        pyxel.rect(left_hand[0] - 3, left_hand[1], 7, 3, COLOR_LCD)

        # 右腕（右側のみ：内2 or 外3）
        if hands["right"] == 3:
            pyxel.line(cx + 4, cy - 10, cx + 25, cy - 4, COLOR_LCD)
            pyxel.line(cx + 25, cy - 4, right_hand[0], right_hand[1], COLOR_LCD)
        else:
            pyxel.line(cx + 4, cy - 10, cx + 14, cy + 1, COLOR_LCD)
            pyxel.line(cx + 14, cy + 1, right_hand[0], right_hand[1], COLOR_LCD)
        pyxel.rect(right_hand[0] - 3, right_hand[1], 7, 3, COLOR_LCD)


if __name__ == "__main__":
    App()
