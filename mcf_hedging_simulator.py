import random
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from tqdm import trange, tqdm

@dataclass
class MCFStage:
    name: str
    true_capital: float               # 總資產（考核基準，例如 300,000）
    trade_capital: float              # 實際下單金額（例如 276,000）
    mcf_fee_rate: float                   # MCF 手續費率
    withdrawable_ratio: float         # 可提領比例（第三階段為 0.08）
    target_profit_pct: float          # 獲利目標（10% 或 5%）
    max_loss_pct: float               # 最大虧損（10%）
    max_daily_loss_pct: float         # 單日最大虧損（4.8%）
    daily_fluctuation_range: float    # 單次波動範圍
    signup_fee: float                 # 報名費（只有第一階段收）
    bybit_capital: float              # Bybit 倉位
    bybit_fee_rate: float             # Bybit 手續費率
    bybit_leverage: float             # Bybit 槓桿
    max_days: int                     # 最多模擬幾天（第三階段為 0 表示不限）
    max_trades_per_day: int           # 每天最多開倉次數
    min_trade_threshold: float        # 最小波動才進場（避免吃手續費）
    max_bybit_loss_pct: float             # bybit止損百分比




def simulate_stage(stage: MCFStage):
    balance = stage.true_capital
    bybit_balance = stage.bybit_capital
    withdrawable = 0
    days = 0
    passed = False
    failed = False

    target_profit_usdt = stage.true_capital * stage.target_profit_pct
    max_loss_usdt = stage.true_capital * stage.max_loss_pct
    history = []

    # print(stage.name)
    while not passed and not failed:
        days += 1
        daily_loss = 0
        trades_today = 0
        day_log = []

        for _ in range(stage.max_trades_per_day):
            if daily_loss >= stage.max_daily_loss_pct:
                day_log.append((days, "當日虧損超過 4.8%，停止開倉"))
                break

            move = random.uniform(-stage.daily_fluctuation_range, stage.daily_fluctuation_range)
            if abs(move) < stage.min_trade_threshold:
                # 沒有波動但開倉 → 吃掉手續費（無損益）
                mcf_fee = stage.trade_capital * stage.mcf_fee_rate
                bybit_fee = stage.bybit_capital * stage.bybit_leverage * stage.bybit_fee_rate

                balance -= mcf_fee * 2
                # bybit_balance -= bybit_fee * 2

                # print("手續費:{}, {}".format(mcf_fee * 2, bybit_fee * 2))

                day_log.append((
                    days,
                    0.00,  # move 為 0%
                    round(balance, 2),
                    round(bybit_balance, 2),
                    "無波動，純吃手續費"
                ))

                continue

            trades_today += 1
            long_mcf = random.choice([True, False])

            # 隨機多空
            if long_mcf:
                mcf_pnl = stage.trade_capital * move
                bybit_pnl = -stage.bybit_capital * move
            else:
                mcf_pnl = -stage.trade_capital * move
                bybit_pnl = stage.bybit_capital * move

            max_bybit_loss = stage.bybit_capital * stage.max_bybit_loss_pct
            if -bybit_pnl > max_bybit_loss:
                bybit_pnl = -max_bybit_loss
                # print(f"Bybit 止損觸發：限制虧損為 {max_bybit_loss:.2f} USDT")

                # 繼續計算手續費並更新 bybit 資產
                bybit_fee = stage.bybit_capital * stage.bybit_leverage * stage.bybit_fee_rate
                bybit_balance += bybit_pnl - bybit_fee * 2

                # 同步更新 MCF（仍照 move 計算，包含手續費）
                mcf_pnl = stage.trade_capital * move if long_mcf else -stage.trade_capital * move
                mcf_fee = stage.trade_capital * stage.mcf_fee_rate
                balance += mcf_pnl - mcf_fee * 2

                # 記錄交易
                day_log.append((
                    days,
                    round(move * 100, 4),
                    round(balance, 2),
                    round(bybit_balance, 2),
                    f"Bybit 止損觸發"
                ))

                # 停止今天開倉
                break


            mcf_fee = stage.trade_capital * stage.mcf_fee_rate
            tmp_balance = balance
            balance += mcf_pnl - mcf_fee * 2

            bybit_fee = stage.bybit_capital * stage.bybit_leverage * stage.bybit_fee_rate
            tmp_bybit_balance = bybit_balance
            bybit_balance += bybit_pnl - bybit_fee * 2

            if move < 0:
                daily_loss += -move

            cumulative_pnl = balance - stage.true_capital
            day_log.append((days, round(move * 100, 2), round(balance, 2), round(bybit_balance, 2)))

            # 達到最大虧損
            if cumulative_pnl <= -max_loss_usdt:
                failed = True

            if cumulative_pnl >= target_profit_usdt:
                if stage.name == '第三階段':
                    withdraw_amount = balance - stage.true_capital
                    net_withdrawn = withdraw_amount * stage.withdrawable_ratio
                    withdrawable += net_withdrawn
                    balance -= withdraw_amount
                    stage.true_capital = balance
                    cumulative_pnl = 0

                    day_log.append((
                        days,
                        round(move * 100, 2),
                        round(balance, 2),
                        round(bybit_balance, 2),
                        f"提領 {round(net_withdrawn, 2)} USDT，帳戶重設"
                    ))
                    # print(f'第 {days} 天，提領{withdraw_amount}，實收{net_withdrawn}')
                else: # 第一、二階段
                    passed = True
                  

            # print dailt info.

            mcf_trade_pnl = mcf_pnl
            bybit_trade_pnl = bybit_pnl - bybit_fee * 2
            mcf_total_return = (balance - stage.true_capital) / stage.true_capital * 100

            # print(
            #     f"第 {days} 天，第 {trades_today} 筆交易 | Move: {move*100:.2f}%\n"
            #     f"MCF: 資產 = {balance:.2f}, 損益 = {mcf_trade_pnl:.2f}\n"
            #     f"Bybit: 資產 = {bybit_balance:.2f}, 損益 = {bybit_trade_pnl:.2f}\n"
            # )

            if failed or passed: break

        history.extend(day_log)

        if passed or failed:
            break
        if stage.max_days > 0 and days >= stage.max_days and not passed:
            failed = True
            break

    return {
        "階段": stage.name,
        "結果": "通過" if passed else "失敗",
        "天數": days,
        "最終資產(MCF)": round(balance, 2),
        "最終資產(Bybit)": round(bybit_balance, 2),
        "Bybit損益": round(bybit_balance - stage.bybit_capital, 2),
        "MCF報酬%": round((balance - stage.true_capital) / stage.true_capital * 100, 2),
        "可提領獲利": round(withdrawable, 2),
        "報名費": stage.signup_fee,
        "總合損益": round(withdrawable + (bybit_balance - stage.bybit_capital) - (stage.signup_fee if not passed else 0), 2),
        "歷史記錄": history
    }


def simulate_full_exam():
    stages = [
        # MCFStage("第一階段", 300000, 276000, 0.00055, 0.0, 0.10, 0.1, 0.048, 0.036, 378, 23000, 0.0005, 1, 30, 5, 0.005, 0.012),
        # MCFStage("第二階段", 300000, 276000, 0.00055, 0.0, 0.05, 0.1, 0.048, 0.036, 0, 65000, 0.0005, 1, 30, 5, 0.005, 0.012),
        # MCFStage("第三階段", 300000, 276000, 0.00055, 0.8, 0.10, 0.1, 0.048, 0.036, 0, 76000, 0.0005, 1, 0, 5, 0.005, 0.012)
        MCFStage("第一階段", 15000, 13800, 0.00055, 0.0, 0.10, 0.1, 0.048, 0.036, 55, 1150, 0.0005, 1, 30, 1, 0.005, 0.012),
        MCFStage("第二階段", 15000, 13800, 0.00055, 0.0, 0.05, 0.1, 0.048, 0.036, 0, 3250, 0.0005, 1, 30, 1, 0.005, 0.012),
        MCFStage("第三階段", 15000, 13800, 0.00055, 0.8, 0.10, 0.1, 0.048, 0.036, 0, 3800, 0.0005, 1, 0, 1, 0.005, 0.012)
    ]

    total_withdrawable = 0
    total_bybit_profit = 0
    total_signup_fee = 0
    total_days = 0
    
    results = []

    for stage in stages:
        result = simulate_stage(stage)
        results.append(result)
        total_withdrawable += result["可提領獲利"]
        total_bybit_profit += result["最終資產(Bybit)"] - stage.bybit_capital
        total_signup_fee += result["報名費"]
        total_days += result["天數"]
        if result["結果"] == "失敗":
            break

    print("\nMCF + Bybit 對沖模擬總結")
    for r in results:
        print(f"\n{r['階段']} - {r['結果']}")
        print(f"用時：{r['天數']} 天")
        print(f"MCF 最終資產：{r['最終資產(MCF)']}（{r['MCF報酬%']}%）")
        print(f"Bybit 最終資產：{r['最終資產(Bybit)']}（盈虧：{round(r['最終資產(Bybit)'] - stages[results.index(r)].bybit_capital, 2)} USDT）")
        print(f"可提領（MCF）：{r['可提領獲利']}  | 報名費：{r['報名費']}")
        print(f"📌 總合損益：{r['總合損益']}")

    total_result = total_withdrawable + total_bybit_profit - total_signup_fee
    print("\n總結：")
    print(f"MCF 可提領：{round(total_withdrawable, 2)}")
    print(f"Bybit 總損益：{round(total_bybit_profit, 2)}")
    print(f"報名費總額：{total_signup_fee}")
    print(f"最終總合損益：{round(total_result, 2)}")


def simulate_multiple_runs(runs=1000):
    final_profits = []
    stage_counts = {"第一階段": 0, "第二階段": 0, "第三階段": 0}
    all_days = []

    for _ in trange(runs):
        stages = [
            # MCFStage("第一階段", 300000, 276000, 0.00055, 0.0, 0.10, 0.1, 0.048, 0.05, 378, 23000, 0.0005, 1, 30, 5, 0.005, 0.01),
            # MCFStage("第二階段", 300000, 276000, 0.00055, 0.0, 0.05, 0.1, 0.048, 0.05, 0, 65000, 0.0005, 1, 30, 5, 0.005, 0.01),
            # MCFStage("第三階段", 300000, 276000, 0.00055, 0.8, 0.10, 0.1, 0.048, 0.05, 0, 76000, 0.0005, 1, 0, 5, 0.005, 0.01)
            MCFStage("第一階段", 15000, 13800, 0.00055, 0.0, 0.10, 0.1, 0.048, 0.036, 39, 1150, 0.0005, 1, 30, 3, 0.005, 0.01),
            MCFStage("第二階段", 15000, 13800, 0.00055, 0.0, 0.05, 0.1, 0.048, 0.036, 0, 3250, 0.0005, 1, 30, 3, 0.005, 0.01),
            MCFStage("第三階段", 15000, 13800, 0.00055, 0.8, 0.10, 0.1, 0.048, 0.036, 0, 3800, 0.0005, 1, 0, 3, 0.005, 0.01)
        ]

        total_withdrawable = 0
        total_bybit_profit = 0
        total_signup_fee = 0
        total_days = 0
        success_stage = "第一階段"

        for stage in stages:
            result = simulate_stage(stage)
            total_withdrawable += result["可提領獲利"]
            total_bybit_profit += result["最終資產(Bybit)"] - stage.bybit_capital
            total_signup_fee += result["報名費"]
            total_days += result["天數"]
            success_stage = stage.name
            if result["結果"] == "失敗":
                break

        total_profit = total_withdrawable + total_bybit_profit - total_signup_fee
        final_profits.append(total_profit)
        all_days.append(total_days)

        # 統計階段通過情況
        if success_stage == "第一階段":
            stage_counts["第一階段"] += 1
        elif success_stage == "第二階段":
            stage_counts["第二階段"] += 1
        elif success_stage == "第三階段":
            stage_counts["第三階段"] += 1

    return final_profits, stage_counts, all_days


def plot(runs):
    profits, stage_results, all_days = simulate_multiple_runs(runs=runs)
    total_runs = len(profits)

    # 👉 去除右側極端值（例如前 5% ）
    profits_array = np.array(profits)
    cutoff = np.percentile(profits_array, 97)
    trimmed_profits = profits_array[profits_array <= cutoff]
    
    days_array = np.array(all_days)
    trimmed_days = days_array[days_array <= days_array]

    # 原始統計
    average_profit = np.mean(profits_array)
    median_profit = np.median(profits_array)
    avg_days = np.mean(all_days)
    median_days = np.median(all_days)

    # 截尾後統計
    trimmed_mean = np.mean(trimmed_profits)
    trimmed_median = np.median(trimmed_profits)
    trimmed_avg_days = np.mean(trimmed_days)
    trimmed_median_days = np.mean(trimmed_days)

    # 印出統計結果
    print(f"【原始】平均收益：{round(average_profit, 2)}")
    print(f"【原始】中位數收益：{round(median_profit, 2)}")
    print(f"【原始】平均總天數：{round(avg_days, 2)} 天")
    print(f"【原始】中位數總天數：{round(median_days, 2)} 天")
    print(f"【截尾後】平均收益：{round(trimmed_mean, 2)}")
    print(f"【截尾後】中位數收益：{round(trimmed_median, 2)}")
    print(f"【截尾後】平均總天數：{round(trimmed_avg_days, 2)} 天")
    print(f"【截尾後】中位數總天數：{round(trimmed_median_days, 2)} 天")
    print(f"第一階段通過率：{round(stage_results['第一階段'] / total_runs * 100, 2)}%")
    print(f"第二階段通過率：{round(stage_results['第二階段'] / total_runs * 100, 2)}%")
    print(f"第三階段通過率：{round(stage_results['第三階段'] / total_runs * 100, 2)}%")

    # 畫圖（截尾後的收益）
    plt.rcParams['font.family'] = 'Microsoft JhengHei'
    plt.figure(figsize=(10, 6))
    plt.hist(trimmed_profits, bins=50, color='skyblue', edgecolor='black')
    plt.axvline(trimmed_mean, color='red', linestyle='dashed', linewidth=2, label=f'平均：{round(trimmed_mean, 2)}')
    plt.axvline(trimmed_median, color='green', linestyle='dashed', linewidth=2, label=f'中位數：{round(trimmed_median, 2)}')
    plt.title("截尾後模擬收益分布圖")
    plt.xlabel("收益 (USDT)")
    plt.ylabel("次數")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()



if __name__ == '__main__':

    # 單次模擬
    # simulate_full_exam()

    # 執行模擬
    plot(runs=100000)


    

